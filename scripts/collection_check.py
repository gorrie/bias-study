#!/usr/bin/env python3
"""Is this collection fit to score? Run it BEFORE spending judge calls on a run.

WHY THIS EXISTS
---------------
`COLLECTION-STANDARD.md` opens with "This is a gate, not advice," and until
2026-09-13 nothing executed it: zero references from any script or CI config. Its
section 4 asks "What is the parameter that will silently ruin it?" and lists a
build that "cannot fit its answer sheet in the budget" as an example of a
collection that is not being measured.

That is exactly what had happened, unnoticed, for four months. 1,022 of 4,748
scored records sat on an 800-token cap -- 21.5% of the corpus, severed
mid-argument and handed to the judges. The rate ran from 96.7% of one model's
records to near zero for terse ones, so every cross-vendor comparison was
confounded with verbosity, and the study's central claim is about vendor
differences.

Every check below would have caught something real on the day it was written. The
point is that a collection gets a verdict BEFORE anyone spends money scoring it
and long before a number reaches a page.

WHAT IT CHECKS

  1. records exist                 a gate over zero records is not a pass
  2. collection parameters recorded  max_tokens and temperature, per record. Not
                                   recording them is HOW the truncation defect
                                   stayed invisible: you could not tell from a run
                                   directory what budget produced it
  3. truncation                    by the TEXT, never by finish_reason -- the
                                   G0DM0D3 proxy reports "stop" on responses
                                   severed mid-word
  4. truncation is not differential  a uniform rate is a limitation; a rate that
                                   varies by model is a CONFOUND, and excluding
                                   the records relocates it into the denominator
                                   rather than removing it
  5. empty responses               a completed call that returned nothing
  6. replicate distinctness        --samples 5 is worth nothing if the server
                                   serves five identical strings
  7. cell balance                  ragged cells silently drop items from paired
                                   contrasts
  8. token headroom                responses crowding the cap mean the next model
                                   will hit it

    python scripts/collection_check.py 2026-09-13-g0dm0d3-replicate
    python scripts/collection_check.py <run> --json

Reads only. No API calls. Exit 0 accept, 1 blocked, 2 nothing to check.
"""
from __future__ import annotations

import argparse
import collections
import glob
import hashlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import eligibility as E  # noqa: E402
import studypaths as _SP  # noqa: E402

#: Above this share of truncated responses the run is not scoreable as collected.
TRUNCATION_BLOCK = 0.05
#: Spread between the best and worst model's truncation rate. Differential
#: truncation is worse than uniform truncation, because exclusion cannot fix it.
TRUNCATION_SPREAD_BLOCK = 0.10
#: Responses landing within this fraction of the cap are "crowding" it.
HEADROOM_WARN = 0.95
#: Above this share of empty responses the model is not answering at all.
#: gpt-5 returned 287 empties of 310 (92.6%) in the May corpus. A stray empty is a
#: missing cell; a rate like that is a model that cannot be measured on this
#: instrument, and the difference is what this threshold encodes.
EMPTY_BLOCK = 0.05


def load_raw(run_dir):
    """Every record in a run, in EITHER collector layout.

    TWO LAYOUTS, AND THIS READ ONLY ONE OF THEM. `run_study.py` writes
    `<run>/raw/<model>.jsonl`; `run_battery.py` writes `<run>/<model>__<cond>.jsonl`
    flat at the run root. This globbed `raw/**` only, so it returned zero rows for
    EVERY forced-choice run ever collected.

    It said so honestly -- "CHECKED NOTHING ... This is NOT a pass" -- which is
    why this was never a wrong number. It is worse in a quieter way: the I3
    pre-registration makes `collection_check` ACCEPTING a run the precondition for
    spending a scoring call on it, and for the entire forced-choice arm that gate
    could not be satisfied by any run, correct or not. A gate nobody can pass is a
    gate that gets skipped, and then it is not a gate.

    Found 2026-09-15 by running it against the Phase 2 smoke -- four sheets, 60 of
    60 answers each, and the checker read none of them.

    `raw/` first so nothing changes for the judged corpus; the flat fallback only
    fires when `raw/` yields nothing, so a run cannot be counted twice.
    """
    rows = []
    for path in sorted(glob.glob(os.path.join(run_dir, "raw", "**", "*.jsonl"), recursive=True)):
        for line in io.open(path, encoding="utf-8", errors="replace"):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except ValueError:
                pass
    if rows:
        return rows
    for path in sorted(glob.glob(os.path.join(run_dir, "*.jsonl"))):
        for line in io.open(path, encoding="utf-8", errors="replace"):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except ValueError:
                pass
    return rows


def cap_of(rec):
    cap = rec.get("max_tokens")
    if cap is None:
        cap = (rec.get("study_call_metadata") or {}).get("max_tokens")
    return cap


#: Below this share of a sheet's items parsed, the sheet is not a measurement.
#: The I3 Phase 2 gate is "answers parse at >= 95%".
SHEET_PARSE_BLOCK = 0.95

#: How much of a run may be LOST to unrepairable sheets before the run is unusable.
#:
#: Two limits, because two different things go wrong. The first is volume: past some fraction
#: the floors have too few cells to mean anything. The second is CONCENTRATION, and it is the
#: one that actually invalidates a comparison -- the 4,096 wave lost 95.8% of one vendor's
#: sheets against 7.7% of another's, which is FINDINGS #7, differential exclusion by vendor.
#: A run that loses 4% evenly is smaller; a run that loses 40% of one vendor is a different
#: experiment for that vendor.
LOST_CELL_BLOCK = 0.05
LOST_CELL_VENDOR_BLOCK = 0.25


#: Where the declared limitations live, when `--declared` is not given explicitly.
DECLARED_DEFAULT = os.path.join(os.path.dirname(HERE), "data", "collection-limitations.json")


def _declared_models(path=None):
    """Models declared as behavioural losses. -> set of model ids.

    An absent file declares nothing, which is the safe direction: every behavioural loser then
    blocks. A model listed under `not_declared_and_still_blocking` is deliberately NOT returned
    -- that section exists to record why something was left blocking, and reading it as a
    declaration would invert its meaning.
    """
    path = path or DECLARED_DEFAULT
    if not os.path.exists(path):
        return set()
    try:
        doc = json.load(io.open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    return {m.get("model") for m in (doc.get("models") or []) if m.get("model")}


def _outcome_is_partial_sheets(run_dir):
    """Does this run MEASURE partial sheets rather than lose them?

    Read from the run's own manifest, so it is a property of the arm rather than a flag
    somebody has to remember at the command line. `run_omission_orders` records
    `analysis: scripts/item_omission.py`, and that analysis counts sheets returned with items
    missing -- the dependent variable of the whole arm.
    """
    try:
        with io.open(os.path.join(run_dir, "manifest.json"), encoding="utf-8") as fh:
            m = json.load(fh)
    except (OSError, ValueError):
        return False
    return "item_omission" in str(m.get("analysis") or "")


def analyse_sheets(rows, declared_path=None, outcome_is_partial_sheets=False):
    """Checks that only mean anything for a WHOLE-SHEET forced-choice run.

    The judged checks above read `response_text` and ask whether it was severed.
    A forced-choice sheet fails differently: it parses partially, or the model
    answers every item identically, or the presentation order was never swept --
    and none of those show up as a truncated paragraph.

    Returns {} for a judged run, so the caller can merge unconditionally.
    """
    sheets = [r for r in rows if _SP.is_run_record(r)]
    if not sheets:
        return {}

    out = {"n_sheets": len(sheets), "problems": [], "warnings": [],
           "_outcome_is_partial_sheets": outcome_is_partial_sheets}
    valid = [r for r in sheets if r.get("valid")]
    out["n_valid_sheets"] = len(valid)
    out["failure_modes"] = dict(collections.Counter(
        r.get("failure_mode") or "-" for r in sheets if not r.get("valid")))

    # Parse rate per sheet. A sheet answering 44 of 60 is not a position.
    #
    # A REFUSAL IS NOT A PARSE FAILURE. This counted every sheet, so a model that declined
    # the instrument -- answering nothing, on purpose, which this study REPORTS as a result --
    # landed in a blocker reading "parsed below 95% of their items". On the first battery wave
    # that was 35 of 37: the gate was refusing the collection over its own refusal finding,
    # and the two real format failures were invisible inside it.
    #
    # Refusals are counted and reported on their own line. The blocker is about sheets that
    # tried to answer and produced a fragment.
    attempted = [r for r in sheets if (r.get("failure_mode") or "") != "refused"]
    refused = len(sheets) - len(attempted)
    out["refused_sheets"] = refused
    # COUNT ITEMS ANSWERED, NOT ANSWERS RETURNED.
    #
    # This was `n_answers / n_items`, so a sheet returning 32 answers all carrying q=1..12 with
    # repeats scored 1.0 and was fine by this gate -- while `floor_table.load` dropped it as
    # invalid, because there is no position for the twenty items it never reached. The gate
    # blocked the wave over `mistral:latest` at 37% and said nothing about
    # `gemma-4-12B`, whose 33 of 39 sheets were invalid and 26 of those for exactly this
    # reason. The acceptance criterion has to measure what the analysis keeps.
    rates = []
    for r in attempted:
        answers = r.get("answers") or []
        n_items = r.get("n_items") or len(answers) or 1
        distinct = len({a.get("q") for a in answers if isinstance(a, dict)})
        rates.append(min(distinct, n_items) / float(n_items))
    if not rates:
        # EVERY SHEET WAS A REFUSAL. Not a parse problem, and not a pass either.
        out["problems"].append(
            "every sheet in this run is a refusal (%d). There is no position data here."
            % refused)
        rates = [0.0]
    out["min_parse_rate"] = round(min(rates), 3)
    out["mean_parse_rate"] = round(sum(rates) / len(rates), 3)
    under = sum(1 for x in rates if x < SHEET_PARSE_BLOCK)
    # A LOST CELL IS REPORTED; A LOSS *RATE* IS WHAT BLOCKS.
    #
    # This appended a `problem` for any under-parsed sheet at all, and a problem makes the run
    # NOT FIT TO SCORE. But an under-parsed sheet is exactly what `floor_table.load()` already
    # drops, and once `RETRY_CAP` is exhausted the record cannot be repaired -- the standing
    # rule forbids deleting it. So the run could never be ACCEPTED by any action available,
    # and a gate that cannot be satisfied is a gate that gets routed around. That is the
    # failure mode, not the six sheets.
    #
    # What matters for whether the corpus is usable is HOW MANY cells were lost, because the
    # floors need cells, and whether the loss is CONCENTRATED, because differential exclusion
    # by vendor is this study's own FINDINGS #7 and is the thing that makes a comparison
    # invalid rather than merely smaller.
    if under:
        lost_rate = under / float(len(attempted))
        worst_vendor, worst_share = None, 0.0
        by_vendor = collections.Counter()
        vendor_total = collections.Counter()
        for r, x in zip(attempted, rates):
            v = (r.get("model") or "?").split("/")[0]
            vendor_total[v] += 1
            if x < SHEET_PARSE_BLOCK:
                by_vendor[v] += 1
        for v, n in by_vendor.items():
            share = n / float(vendor_total[v] or 1)
            if share > worst_share:
                worst_vendor, worst_share = v, share
        detail = ("%d of %d sheet(s) that ATTEMPTED an answer parsed below %.0f%% of their "
                  "items (worst %.0f%%); %d further sheet(s) are refusals and are counted "
                  "separately. A partially parsed sheet is not a position and every floor "
                  "drops it -- these are LOST CELLS, not scored ones."
                  % (under, len(attempted), 100 * SHEET_PARSE_BLOCK, 100 * min(rates),
                     refused))
        if worst_vendor:
            detail += (" Worst-hit vendor: %s at %.0f%% of its attempted sheets."
                       % (worst_vendor, 100 * worst_share))
        out["lost_cells"] = under
        out["lost_rate"] = round(lost_rate, 4)
        # THE SAME DECLARATION COVERS BOTH METRICS, or the two disagree about one model.
        #
        # This check names the worst vendor by PARSE RATE and the check below names the worst
        # models by INVALIDITY, and on this corpus they are the same models -- `mistral:latest`
        # is the worst on both. Declaring a behavioural loss on one metric and not the other
        # would leave the run blocked by a restatement of the fact just declared.
        #
        # The volume limit is NOT waivable this way. A run that loses 5% of everything is a
        # smaller run whoever it lost it from, and no declaration makes it bigger.
        declared_here = _declared_models(declared_path)
        worst_is_declared = bool(worst_vendor) and any(
            m.split("/")[-1].startswith(worst_vendor) or m == worst_vendor
            for m in declared_here)
        if lost_rate > LOST_CELL_BLOCK and out.get("_outcome_is_partial_sheets"):
            # THE PARTIAL SHEET IS THE MEASUREMENT IN THIS ARM, NOT A LOSS OF IT.
            #
            # `run_omission_orders` exists to count sheets that come back with items missing:
            # that rate IS the dependent variable, and the whole finding is that it differs
            # between two numbering arms. Scoring it as lost cells reads the outcome as a
            # collection defect and returns NOT FIT TO SCORE for an arm behaving exactly as
            # designed -- while the paper cites it for the mechanism.
            #
            # Declared from the run's own manifest (`analysis: scripts/item_omission.py`), not
            # from a flag an operator remembers, and reported rather than hidden. A run whose
            # outcome is partial sheets is also never sent to a judge, which is what "fit to
            # score" is asking about.
            out["warnings"].append(
                detail + (" NOT BLOCKING: this arm's own outcome IS the partial-sheet rate "
                          "(%.1f%%), declared by its manifest's analysis field. Counting the "
                          "measurement as loss would refuse the arm for working."
                          % (100 * lost_rate)))
        elif lost_rate > LOST_CELL_BLOCK:
            out["problems"].append(
                detail + (" BLOCKING: the loss rate is %.1f%% against a %.0f%% limit. Volume, "
                          "not concentration -- a declaration cannot make a smaller run bigger."
                          % (100 * lost_rate, 100 * LOST_CELL_BLOCK)))
        elif worst_share > LOST_CELL_VENDOR_BLOCK and not worst_is_declared:
            out["problems"].append(
                detail + (" BLOCKING: %s loses %.0f%% of its attempted sheets (limit %.0f%%), "
                          "which is differential exclusion and makes the comparison invalid "
                          "rather than merely smaller. Re-collect it, or declare it in "
                          "data/collection-limitations.json with its failure shape."
                          % (worst_vendor, 100 * worst_share, 100 * LOST_CELL_VENDOR_BLOCK)))
        else:
            if worst_share > LOST_CELL_VENDOR_BLOCK:
                detail += (" %s is above the per-vendor limit and is DECLARED."
                           % worst_vendor)
            out["warnings"].append(detail)

    # WHAT THE ANALYSIS ACTUALLY DROPS, not just what parsed short.
    #
    # The parse-rate check above measures one way a sheet fails. `floor_table.load()` drops a
    # sheet for ANY invalidity, and a model can lose almost everything without a single short
    # parse: `gemma-4-12B` returned 33 invalid sheets of 39 -- full-length, fully parsed,
    # alternating 2,1,2,1 down the page, caught by the structural classifier -- and the gate
    # above reported its parse rate as 100% and named a different vendor as worst-hit. It
    # blocked the wave over the smaller problem while the larger one was invisible.
    #
    # Refusals stay out of the denominator; a refusal is a measurement and is reported on its
    # own line.
    # A TRANSPORT FAILURE IS NOT A SHEET THE MODEL ANSWERED BADLY. It is a sheet the model
    # NEVER SAW, and this file says so twelve lines down: "the model never answered".
    # Counting it in a denominator named ATTEMPTED made an availability problem read as a
    # model problem, and the difference decides the remedy.
    #
    # Measured 2026-09-19: `z-ai/glm-5.2` -- 27 valid, 1 refused, 25 transport, every one of
    # them HTTP 404 "No endpoints found" from a pinned backend that had already served it 28
    # times. It was reported as losing 48% of its sheets to invalidity and blocked the run.
    # Its invalidity among sheets it actually answered is ZERO. The same artifact inflated
    # glm-5.3-flash and deepseek-v4-flash.
    #
    # The availability hole is real and is NOT dropped -- it is reported on its own line
    # below, because a model that cannot be reached has thinner cells than one that can, and
    # that is differential too. It is just a different problem with a different fix.
    answered = [r for r in attempted if (r.get("failure_mode") or "") != "transport"]
    model_total, model_bad = collections.Counter(), collections.Counter()
    for r in answered:
        model_total[r.get("model") or "?"] += 1
        if not r.get("valid"):
            model_bad[r.get("model") or "?"] += 1
    # WHY A MODEL LOST ITS SHEETS DECIDES WHAT TO DO ABOUT IT, so the two are separated.
    #
    # `transport` is the network or the provider: the model never answered, re-collecting is
    # cheap and costs nothing analytically. Everything else -- a degenerate sheet, a
    # structural parse failure, an unusable answer -- is the model's own behaviour, and
    # re-collecting reproduces it. Reported as one number, the two invite the same remedy and
    # only one of them works.
    infra = collections.Counter()
    for r in attempted:
        if not r.get("valid") and (r.get("failure_mode") or "") == "transport":
            infra[r.get("model") or "?"] += 1

    # THE AVAILABILITY HOLE, ON ITS OWN LINE AND STILL A BLOCKER.
    #
    # It left the invalidity ratio above because a sheet the model never saw is not a sheet it
    # answered badly -- that relabelling is correct. It was then DOWNGRADED TO A WARNING on
    # 2026-09-19 and that was wrong, caught the same day by an adversarial review.
    #
    # MEASURED: 101 of the 104 transport losses in this wave fall on Chinese-jurisdiction
    # vendors and ZERO on US ones -- 8.4% against 0.0%. That is perfectly differential along
    # the exact axis of this study's jurisdiction gradient (p = 0.0004), its
    # "US flagships 100% / Chinese vendors 0%" refusal result, and its hosted-vs-local and
    # vintage groupings.
    #
    # LEARNINGS #6, in this project's own words: *"Differential exclusion relocates a confound;
    # it does not remove it. Before excluding bad records, check whether the exclusion rate
    # varies by the thing you are comparing."* A warning has no enforcement -- once the other
    # blockers clear, the run reads FIT TO SCORE with those cells thin on one side of the
    # comparison. So the ratio is relabelled and the hole still blocks.
    if infra:
        out["infrastructure_losses"] = dict(infra)
        reach = sorted(((infra[m] / float(infra[m] + model_total.get(m, 0)), m, infra[m],
                         infra[m] + model_total.get(m, 0))
                        for m in infra), reverse=True)
        worst = [r for r in reach if r[0] > LOST_CELL_VENDOR_BLOCK]
        # WHY A MODEL NEVER ANSWERED DECIDES WHAT TO DO ABOUT IT, and the three cases have
        # three different remedies. Measured on this wave 2026-09-19, all three present:
        #
        #   RECOVERED  its last success POSTDATES its last failure -- deepseek-v4-flash
        #              404ed on 09-18 and has been serving since 09-19T13:51. The rows are
        #              history; nothing is owed.
        #   RETRYABLE  HTTP 429, and still succeeding -- glm-5.3-flash, 39 rate-limit refusals
        #              with a success at 09-19T06:13. A backoff pass fixes it.
        #   GONE       HTTP 404 under a pin with NO success after the first one -- glm-5.2,
        #              zero in twenty-seven hours. The backend has stopped serving the model.
        #              Retrying forever is not a remedy and a permanent blocker with no exit
        #              is one somebody eventually routes around by reverting the check.
        #
        # A GONE model is declarable in `collection-limitations.json` exactly as a behavioural
        # loser is. The declaration is the report; the blocker stands until it exists.
        state = {}
        for _s, m, _b, _t in worst:
            rows = [r for r in sheets if r.get("model") == m]
            fails = [r for r in rows if (r.get("failure_mode") or "") == "transport"]
            oks = [r.get("collected_at") or "" for r in rows if r.get("valid")]
            last_ok = max(oks) if oks else ""
            last_fail = max((r.get("collected_at") or "") for r in fails) if fails else ""
            errs = " ".join(str(r.get("error") or "") for r in fails)
            if last_ok and last_ok > last_fail:
                state[m] = "recovered"
            elif "429" in errs:
                state[m] = "retryable"
            else:
                state[m] = "gone"
        out["availability_state"] = dict(state)
        _declared = _declared_models(declared_path)
        worst = [row for row in worst if state.get(row[1]) != "recovered"
                 and row[1] not in _declared]

        if worst:
            # A BLOCKER, not a warning. See the note above: these losses are differential on
            # the axis the study compares, and a warning carries no enforcement.
            out["problems"].append(
                 "%d model(s) never received more than %.0f%% of their requested sheets. The "
                 "model never answered, so this is NOT its invalidity and is not counted as "
                 "such -- but it is a hole in a cell, the floors are computed per cell, and "
                 "in this corpus the holes are DIFFERENTIAL: 101 of 104 fall on "
                 "Chinese-jurisdiction vendors and 0 on US ones, which is the axis the "
                 "jurisdiction gradient compares. Excluding them from the ratio without "
                 "retrying them relocates that confound rather than removing it "
                 "(LEARNINGS #6). Retry the provider: %s"
                 % (len(worst), 100 * LOST_CELL_VENDOR_BLOCK,
                    "; ".join("%s %d/%d requested" % (m.split("/")[-1], b, t)
                              for _s, m, b, t in worst)))

    losers = sorted(((model_bad[m] / float(model_total[m]), m, model_bad[m], model_total[m])
                     for m in model_total if model_total[m]),
                    reverse=True)
    concentrated = [row for row in losers if row[0] > LOST_CELL_VENDOR_BLOCK]
    if concentrated:
        out["invalid_by_model"] = {m: [b, t] for _s, m, b, t in losers if b}
        out["infrastructure_losses"] = dict(infra)
        recollectable = [row for row in concentrated if infra.get(row[1], 0) >= 0.5 * row[2]]
        behavioural = [row for row in concentrated if row not in recollectable]
        detail = (
            "%d model(s) lose more than %.0f%% of their ATTEMPTED sheets to invalidity: %s. "
            "Every floor drops these, so the comparison is run on a different number of "
            "sheets per model -- differential exclusion, which is this study's own FINDINGS #7."
            % (len(concentrated), 100 * LOST_CELL_VENDOR_BLOCK,
               "; ".join("%s %d/%d (%.0f%%)" % (m.split("/")[-1], b, t, 100 * s)
                         for s, m, b, t in concentrated)))
        if recollectable:
            detail += (" RE-COLLECTABLE -- mostly `transport`, the provider or the network "
                       "rather than the model, so a retry pass fixes these at no analytic "
                       "cost: %s." % ", ".join("%s (%d transport)" % (m.split("/")[-1],
                                                                      infra.get(m, 0))
                                               for _s, m, _b, _t in recollectable))
        if behavioural:
            detail += (" NOT re-collectable -- the model's own output is unusable and a retry "
                       "reproduces it; these are a limitation to report, not a pass to redo: "
                       "%s." % ", ".join(m.split("/")[-1] for _s, m, _b, _t in behavioural))
        # A DECLARED LOSS IS A STATED LIMITATION; AN UNDECLARED ONE IS A HOLE.
        #
        # The prereg fixed this rule before collection: a run that does not parse at >=95% is
        # "re-collected or reported as unparseable". Re-collection reproduces a model's own
        # output, so `reported` is the remaining branch -- and a report that exists only in
        # someone's head is not a report. `data/collection-limitations.json` is the report, and
        # this is the check that the two agree.
        #
        # It does not loosen anything. An undeclared behavioural loser still blocks; a
        # `transport` loser may never be declared and blocks until retried; and exit 0 requires
        # the declared set to COVER the behavioural set, so a file declaring nothing passes
        # nothing.
        declared = _declared_models(declared_path)
        undeclared = [row for row in behavioural if row[1] not in declared]
        covered = [row for row in behavioural if row[1] in declared]
        if covered:
            out["declared_losses"] = {m: [b, t] for _s, m, b, t in covered}
            detail += (" DECLARED as a stated limitation in %s: %s."
                       % (os.path.basename(declared_path or "collection-limitations.json"),
                          ", ".join(m.split("/")[-1] for _s, m, _b, _t in covered)))
        if undeclared or recollectable:
            out["problems"].append(detail)
        else:
            out["warnings"].append(detail)

    # A sheet answering every item identically has no position to compare, and
    # scoring it against a normal sheet reports a huge side-flip count that reads
    # as an effect. floor_table drops these; a collection check should say so.
    degenerate = [r.get("model") for r in valid
                  if len({a.get("position") for a in (r.get("answers") or [])}) == 1
                  and (r.get("answers") or [])]
    out["degenerate_sheets"] = degenerate
    if degenerate:
        out["warnings"].append(
            "%d sheet(s) answer every item identically (%s). They carry no position and every "
            "floor drops them." % (len(degenerate), ", ".join(sorted(set(degenerate))[:4])))

    # Presentation order. A MIRRORED instrument administered in id order puts each
    # pair's halves adjacent, which is visibly a proposition and its negation --
    # consistency then costs the model nothing. The runner DEFAULTS to id order,
    # so this is an easy and silent way to collect a defeated design.
    unseeded = [r.get("model") for r in sheets if r.get("shuffle_seed") is None]
    out["sheets_without_shuffle_seed"] = len(unseeded)
    if unseeded:
        out["problems"].append(
            "%d of %d sheet(s) carry NO shuffle_seed, so they were administered in id order. "
            "On a mirrored instrument that places every pair's halves adjacent and the design "
            "defeats itself." % (len(unseeded), len(sheets)))
    else:
        out["shuffle_seeds"] = sorted({r.get("shuffle_seed") for r in sheets})

    # CANONICAL IDS, NOT RAW STRINGS. This compared the recorded `instrument` verbatim, so a
    # bank whose id changed mid-collection read as TWO instruments and blocked the run -- the
    # acceptance gate rejecting a collection for a rename rather than for a defect. The 167
    # sheets collected before the 2026-09-16 rename carry `ratchet-battery-v3` and every sheet
    # after carries `ratchet-battery`; `floor_table._canonical` resolves both to one id and
    # pools them correctly, so the gate and the analysis disagreed about the same corpus.
    #
    # The RAW strings are still reported, because "which spellings are present" is a fact an
    # operator wants; the BLOCK is on canonical identity.
    raw = sorted({(r.get("instrument") or "?")[:40] for r in sheets})
    out["instruments"] = raw
    try:
        import floor_table as _F
        canon = sorted({_F._canonical(r.get("instrument") or "?") for r in sheets})
    except ImportError:
        canon = raw
    out["instruments_canonical"] = canon
    if len(canon) > 1:
        out["problems"].append(
            "this run mixes %d instruments: %s. They are never pooled."
            % (len(canon), canon))

    # ONE PROVIDER PER CELL, or a replicate is not a replicate.
    #
    # OpenRouter routes one model id across several backends and can route two
    # calls in the same sitting differently. Measured 2026-09-15 on the first I3
    # wave: SIX of sixteen hosted models were served by more than one provider,
    # kimi-k2.6 by EIGHT (Baidu, Chutes, Decart, DeepInfra, DigitalOcean, Novita,
    # Parasail, StreamLake).
    #
    # It is not cosmetic. The backends do not honour the requested ceiling the
    # same way, so the same model at the same cap splits clean:
    #     kimi-k2.5  SiliconFlow  6/7 valid, median 7,942 tokens
    #                AtlasCloud   0/4 valid, median 4,096 -- exactly the cap
    #
    # This study counts serving mode as a SAME-VERSION VARIANT, so a cell whose
    # replicates crossed backends measured the backend as well as the model.
    by_cell = collections.defaultdict(set)
    for r in sheets:
        if r.get("provider"):
            by_cell[(r.get("model"), r.get("condition"))].add(r["provider"])
    split = {k: sorted(v) for k, v in by_cell.items() if len(v) > 1}
    out["cells_split_across_providers"] = len(split)
    if split:
        worst = max(split.items(), key=lambda kv: len(kv[1]))
        out["problems"].append(
            "%d cell(s) had their replicates served by MORE THAN ONE provider -- worst "
            "%s/%s across %d backends (%s). Serving path is a same-version variant in this "
            "study, so those replicates differ by backend as well as by draw."
            % (len(split), worst[0][0], worst[0][1], len(worst[1]), ", ".join(worst[1])))

    # A PIN THAT DID NOT HOLD IS WORSE THAN NO PIN, because the run looks controlled.
    #
    # `run_battery --provider` sends `allow_fallbacks: false`, so OpenRouter should fail
    # the call rather than route past the pin. Should is not did: this compares what was
    # REQUESTED against what SERVED on every sheet that asked for one, so a reroute is a
    # blocker instead of a row that merely records a different backend than intended.
    #
    # Sheets with no `provider_pinned` are the unpinned ones -- the first sheet of each
    # cell, which is what the pin is learned FROM -- and are not evidence either way.
    # ONE BACKEND PER MODEL, across all four conditions -- not merely within a cell.
    #
    # The check above is per (model, condition), which is the scope the pin used to have, so
    # a model whose arms each sat on a different backend passed cleanly. Verified in the 167
    # sheets: deepseek-v4-flash answered A on Reka, D on Together, N on CoreWeave, P on
    # OpenInference. Its A->D contrast is then one backend against another, and serving path
    # is a same-version variant this study measures -- so the condition contrast and the
    # routing are confounded, and the gate said nothing because it was not looking that wide.
    by_model = collections.defaultdict(set)
    for r in sheets:
        if r.get("provider"):
            by_model[r.get("model")].add(r["provider"])
    split_models = {m: sorted(v) for m, v in by_model.items() if len(v) > 1}
    out["models_split_across_providers"] = len(split_models)
    if split_models:
        worst = max(split_models.items(), key=lambda kv: len(kv[1]))
        out["problems"].append(
            "%d model(s) were served by MORE THAN ONE backend across their conditions -- "
            "worst %s across %d (%s). The condition contrast for those models is confounded "
            "with the routing, because serving path is a same-version variant here."
            % (len(split_models), worst[0], len(worst[1]), ", ".join(worst[1])))

    broken = [(r.get("model"), r.get("condition"), r.get("provider_pinned"),
               r.get("provider"))
              for r in sheets
              if r.get("provider_pinned") and r.get("provider")
              and r["provider_pinned"] != r["provider"]]
    out["provider_pin_broken"] = len(broken)
    if broken:
        m, c, want, got = broken[0]
        out["problems"].append(
            "%d sheet(s) were PINNED to one backend and served by another -- e.g. %s/%s "
            "asked for %s and got %s. allow_fallbacks is false, so this should be "
            "impossible; until it is explained the cell is not a controlled replicate set."
            % (len(broken), m, c, want, got))
    return out


def analyse(rows, declared_path=None, run_dir=None):
    out = {"n_records": len(rows), "problems": [], "warnings": []}
    if not rows:
        return out

    ok_rows = [r for r in rows if r.get("ok")]
    out["n_ok"] = len(ok_rows)
    out["n_failed"] = len(rows) - len(ok_rows)

    sheets = analyse_sheets(rows, declared_path=declared_path,
                            outcome_is_partial_sheets=(_outcome_is_partial_sheets(run_dir) if run_dir else False))
    if sheets:
        out["problems"].extend(sheets.pop("problems", []))
        out["warnings"].extend(sheets.pop("warnings", []))
        out["sheets"] = sheets

    # 2. collection parameters
    with_cap = sum(1 for r in rows if cap_of(r) is not None)
    with_temp = sum(1 for r in rows if r.get("temperature") is not None)
    out["pct_with_max_tokens"] = round(100.0 * with_cap / len(rows), 1)
    out["pct_with_temperature"] = round(100.0 * with_temp / len(rows), 1)
    if with_cap == 0:
        out["problems"].append(
            "NO max_tokens RECORDED on any record. The parameter most able to ruin a "
            "collection is unrecoverable from this run: you cannot tell what budget "
            "produced it, so truncation can only be guessed at from the text.")
    if with_temp == 0:
        out["warnings"].append(
            "no temperature recorded; replicate behaviour is not reconstructable")

    # 3/4. truncation, by the text
    #
    # PROSE ONLY. A forced-choice answer sheet ends "60. Agree" -- no terminal
    # punctuation, by format -- so this test calls every valid sheet severed.
    # Measured 2026-09-15 on the Phase 2 smoke: 4 of 4 sheets flagged at 100%,
    # raising a BLOCKER, while the longest sheet used 2,184 tokens of a 4,096 cap
    # and every one parsed 60 of 60 items.
    #
    # A sheet's completeness is its PARSE RATE, which `analyse_sheets` measures
    # directly. Applying a prose heuristic to a structured answer list is the same
    # category error as reading a CSV for full stops, and it would have blocked
    # every forced-choice collection the moment the loader could finally see one.
    prose_rows = [r for r in ok_rows if not _SP.is_run_record(r)]
    trunc_by_model = collections.Counter()
    total_by_model = collections.Counter()
    n_trunc = 0
    for r in prose_rows:
        m = r.get("model") or "?"
        total_by_model[m] += 1
        if E.looks_truncated_text(r.get("response_text") or ""):
            trunc_by_model[m] += 1
            n_trunc += 1
    # Denominator is the PROSE rows, not every ok row: a rate of "4 of 4" over a
    # population the test cannot read is not a rate.
    out["n_prose_records"] = len(prose_rows)
    out["n_truncated"] = n_trunc
    out["pct_truncated"] = round(100.0 * n_trunc / max(1, len(prose_rows)), 1)
    rates = {m: trunc_by_model.get(m, 0) / t for m, t in total_by_model.items() if t >= 5}
    out["truncation_by_model"] = {m: round(100 * v, 1) for m, v in sorted(rates.items())}
    if n_trunc and n_trunc / max(1, len(prose_rows)) > TRUNCATION_BLOCK:
        out["problems"].append(
            "%d of %d prose responses (%.1f%%) end mid-sentence. A severed response is not a "
            "measurement and must not be scored. Re-collect at a larger --max-tokens."
            % (n_trunc, len(prose_rows), 100.0 * n_trunc / len(prose_rows)))
    if rates:
        spread = max(rates.values()) - min(rates.values())
        out["truncation_spread"] = round(100 * spread, 1)
        if spread > TRUNCATION_SPREAD_BLOCK:
            hi = max(rates, key=rates.get)
            lo = min(rates, key=rates.get)
            out["problems"].append(
                "truncation is DIFFERENTIAL across models: %.1f%% (%s) against %.1f%% (%s). "
                "This is a confound, not a limitation -- excluding the records moves it into "
                "the denominator instead of removing it, so any cross-model comparison from "
                "this run is unsafe even after filtering."
                % (100 * rates[hi], hi.split("/")[-1], 100 * rates[lo], lo.split("/")[-1]))

    # 5. empty
    #
    # THRESHOLDED, not absolute, and the reasoning matters because relaxing a gate
    # is how gates die.
    #
    # An empty response CANNOT reach a judge: score.py returns
    # `scoring_status: skipped-empty-response` without calling one, and
    # eligibility.is_eligible excludes it at read time. Both were verified before
    # this threshold was added. So this check is a THIRD layer, and its job is to
    # catch a SYSTEMIC failure -- gpt-5 returned 287 empties of 310, spending its
    # whole budget on reasoning tokens -- not to refuse a run over one record that
    # two later layers already discard.
    #
    # Blocking on a single stray empty in 1,600 would train the operator to bypass
    # the gate, which costs more than the record does.
    n_empty = sum(1 for r in ok_rows if not (r.get("response_text") or "").strip())
    out["n_empty"] = n_empty
    # A DECLARED LOSER'S EMPTIES ARE ALREADY ACCOUNTED FOR. This rate was computed over the
    # whole run, so a model whose own output is unusable -- declared, and explicitly NOT
    # re-collectable, because a retry reproduces it -- kept blocking through a check that has
    # no declaration path of its own. On 2026-09-18-omission-orders every one of the 22
    # empties is `gemma-4-12B`, already declared as losing 68% of its attempted sheets, and
    # the run read 9.2% corpus-wide against a 5% threshold. The declaration is the mechanism
    # for exactly this, and one check ignoring it re-blocks what another has released.
    #
    # The empties are still counted, still printed, and the declared models are named. What
    # changes is only which denominator decides a BLOCKER: the models that can still be
    # fixed by collecting again.
    _declared_here = _declared_models(declared_path)
    undeclared_rows = [r for r in ok_rows if r.get("model") not in _declared_here]
    n_empty_undeclared = sum(1 for r in undeclared_rows
                             if not (r.get("response_text") or "").strip())
    if _declared_here and n_empty_undeclared < n_empty:
        out["warnings"].append(
            "%d of the %d empty response(s) belong to declared, non-re-collectable model(s): "
            "%s. They are excluded from the blocking rate and remain a stated limitation."
            % (n_empty - n_empty_undeclared, n_empty,
               ", ".join(sorted(m for m in _declared_here
                                if any(r.get("model") == m and
                                       not (r.get("response_text") or "").strip()
                                       for r in ok_rows)))))
    n_empty, ok_rows_for_rate = n_empty_undeclared, undeclared_rows
    empty_rate = n_empty / max(1, len(ok_rows_for_rate))
    out["pct_empty"] = round(100.0 * empty_rate, 2)
    if n_empty and empty_rate > EMPTY_BLOCK:
        out["problems"].append(
            "%d of %d completed calls (%.1f%%) returned no text -- the whole budget went to "
            "reasoning tokens. At this rate the model is not answering, and its cells are "
            "missing rather than measured."
            % (n_empty, len(ok_rows_for_rate), 100.0 * empty_rate))
    elif n_empty:
        out["warnings"].append(
            "%d completed call(s) returned no text (%.2f%%). Below the %.0f%% block "
            "threshold, and score.py + eligibility both exclude them, so they cannot reach "
            "a judge or an aggregate -- but they are missing cells, not measured ones."
            % (n_empty, 100.0 * empty_rate, 100.0 * EMPTY_BLOCK))

    # 6. replicate distinctness
    #
    # THE ITEM ORDER IS PART OF THE CELL, on a whole-sheet instrument.
    #
    # This keyed on (model, condition, question_id). On the per-question corpus that WAS the
    # cell. On a whole-sheet run the record is one sheet, `question_id` is absent, and the
    # three shuffle seeds of one (model, condition) collapsed into a single key -- so the
    # check called three DIFFERENT ITEM ORDERS "replicates", and "mean 2.98 distinct per
    # cell" measured that the three orders produced different text. Of course they did. The
    # question this section asks is whether repeated draws at ONE order come back distinct,
    # and it could not ask it.
    # VALID SHEETS ONLY. A RETRY OF A FAILURE IS NOT A REPLICATE DRAW.
    #
    # Built from `ok_rows` -- every call that returned -- this compared the two attempts of a
    # cell that failed twice. Two empty responses hash identically, and so do two copies of
    # the same deterministic malformed sheet, so the check reported "EVERY replicate cell
    # returned identical text -- the replicate design is buying nothing" as a BLOCKER over
    # eight cells that hold no draws at all: four deepseek sheets that spent the whole budget
    # emitting nothing, and gemma-4-12B's repeated duplicate-answer failure. The replicate
    # design was not buying nothing; it had not been run yet.
    #
    # The question this section asks -- do repeated draws at one order come back distinct --
    # is only answerable about draws that produced an answer.
    cells = collections.defaultdict(list)
    # `analyse()` works on ok_rows; the sheet-level validity flag is what distinguishes a draw
    # from a failed attempt. A per-question corpus has no `valid` field, and there every ok row
    # IS a draw -- hence the fallback, which keeps the original behaviour for that corpus.
    drawn = [r for r in ok_rows if r.get("valid", True)]
    for r in drawn:
        key = (r.get("model"), r.get("condition"),
               r.get("question_id") if r.get("question_id") is not None
               else r.get("shuffle_seed"))
        cells[key].append(
            hashlib.sha256(((r.get("response_text") or "")).encode("utf-8")).hexdigest())
    multi = {k: v for k, v in cells.items() if len(v) > 1}
    out["n_cells"] = len(cells)
    out["n_cells_with_replicates"] = len(multi)
    if multi:
        identical = [k for k, v in multi.items() if len(set(v)) == 1]
        out["n_cells_all_identical"] = len(identical)
        distinct = sum(len(set(v)) for v in multi.values()) / len(multi)
        out["mean_distinct_per_cell"] = round(distinct, 2)
        if len(identical) == len(multi):
            out["problems"].append(
                "EVERY replicate cell returned identical text. The replicate design is "
                "buying nothing -- the server is serving one deterministic answer per cell "
                "and the run costs N times a single draw.")
        elif len(identical) > 0.2 * len(multi):
            out["warnings"].append(
                "%d of %d replicate cells returned identical text"
                % (len(identical), len(multi)))

    # 7. cell balance
    depths = collections.Counter(len(v) for v in cells.values())
    out["cell_depths"] = dict(sorted(depths.items()))
    if len(depths) > 1:
        out["warnings"].append(
            "ragged cell depth %s -- paired contrasts silently drop unmatched items, so "
            "report the pair count with any delta" % sorted(depths))

    # 8. headroom
    caps = [cap_of(r) for r in ok_rows if cap_of(r) is not None]
    outs = [r.get("tokens_out") for r in ok_rows if isinstance(r.get("tokens_out"), int)]
    if caps and outs:
        cap = max(caps)
        crowding = sum(1 for t in outs if t >= HEADROOM_WARN * cap)
        out["cap"] = cap
        out["max_tokens_out"] = max(outs)
        out["n_crowding_cap"] = crowding
        if crowding:
            out["warnings"].append(
                "%d response(s) came within %d%% of the %d-token cap; the next, more "
                "verbose model will hit it" % (crowding, int(HEADROOM_WARN * 100), cap))

    # 9. ARE THE CONDITIONS DISTINGUISHABLE IN THE RECORDS THEMSELVES?
    #
    # `tests/test_condition_construction.py` checks what the code WOULD build. It
    # passes, and it passed throughout: the flags were right in the source and the
    # collection was still wrong. B-STM, B-Parseltongue and B-Layered were written
    # with byte-identical `system_prompt` and `user_prompt` on all 10 questions in
    # both pipeline runs, because the transforms those conditions name are applied
    # SERVER-SIDE by the proxy and the record stores the PRE-transform text.
    #
    # Two conditions that a run's own records cannot tell apart is the shape of
    # the defect either way: an arm that was never treated, or one whose treatment
    # nothing recorded. Both publish a condition's name over an unattributable
    # measurement, so this is a warning on every run rather than a fact about one.
    by_q = collections.defaultdict(dict)
    for r in ok_rows:
        c, q = r.get("condition"), r.get("question_id")
        if c is None or q is None:
            continue
        by_q[q][c] = ((r.get("system_prompt") or "").strip(),
                      (r.get("user_prompt") or "").strip())
    collisions = collections.Counter()
    for q, byc in by_q.items():
        inv = collections.defaultdict(list)
        for c, pr in byc.items():
            inv[pr].append(c)
        for cs in inv.values():
            if len(cs) > 1:
                collisions[tuple(sorted(cs))] += 1
    out["condition_prompt_collisions"] = {",".join(k): v for k, v in collisions.items()}
    for conds, n_q in collisions.items():
        out["warnings"].append(
            "conditions %s carry IDENTICAL prompts on %d question(s). Either the "
            "distinction is applied downstream of the record -- server-side by a "
            "proxy, say -- in which case NOTHING ON DISK says what the model "
            "received; or the arms are the same experiment under different labels. "
            "Verify with scripts/pipeline_transform_audit.py before scoring."
            % (", ".join(conds), n_q))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("run", help="run date/name, e.g. 2026-09-13-g0dm0d3-replicate")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--declared", default=None,
                    help="JSON of declared behavioural losses (default: "
                         "data/collection-limitations.json). A declared loser is a stated "
                         "limitation; an undeclared one still blocks.")
    a = ap.parse_args(argv)

    try:
        from studypaths import run_roots
        roots = [str(p) for p in run_roots()]
    except Exception:
        study = os.path.dirname(HERE)
        roots = [os.path.join(study, r) for r in ("runs", "data")]

    run_dir = None
    for root in roots:
        cand = os.path.join(root, a.run)
        if os.path.isdir(cand):
            run_dir = cand
            break
    if run_dir is None:
        print("CHECKED NOTHING -- no run directory named %r under: %s"
              % (a.run, ", ".join(roots)), file=sys.stderr)
        print("This is NOT a pass.", file=sys.stderr)
        return 2

    rows = load_raw(run_dir)
    res = analyse(rows, declared_path=a.declared, run_dir=run_dir)
    res["run"] = a.run
    res["run_dir"] = run_dir

    if a.json:
        print(json.dumps(res, indent=2, default=str))
        return 1 if res["problems"] else 0

    print("COLLECTION CHECK -- %s" % a.run)
    print(run_dir)
    print("")
    if not rows:
        print("CHECKED NOTHING -- 0 raw records in this run directory. This is NOT a pass.")
        return 2

    print("  records                %d (%d ok, %d failed)"
          % (res["n_records"], res.get("n_ok", 0), res.get("n_failed", 0)))
    if res.get("sheets"):
        s = res["sheets"]
        print("  sheets                 %d (%d valid)%s"
              % (s["n_sheets"], s["n_valid_sheets"],
                 ("  failures: %s" % s["failure_modes"]) if s.get("failure_modes") else ""))
        print("  parse rate             min %.0f%%, mean %.0f%%"
              % (100 * s["min_parse_rate"], 100 * s["mean_parse_rate"]))
        print("  shuffle seeds          %s"
              % (s.get("shuffle_seeds")
                 if not s.get("sheets_without_shuffle_seed")
                 else "MISSING on %d sheet(s) -- id order"
                      % s["sheets_without_shuffle_seed"]))
        print("  instrument             %s" % ", ".join(s.get("instruments", [])))
    print("  cells                  %d (%d with replicates, mean %s distinct)"
          % (res.get("n_cells", 0), res.get("n_cells_with_replicates", 0),
             res.get("mean_distinct_per_cell", "n/a")))
    print("  cell depths            %s" % res.get("cell_depths"))
    print("  max_tokens recorded    %s%%" % res.get("pct_with_max_tokens"))
    print("  temperature recorded   %s%%" % res.get("pct_with_temperature"))
    print("  truncated (text test)  %d  (%.1f%%)"
          % (res.get("n_truncated", 0), res.get("pct_truncated", 0.0)))
    if res.get("truncation_by_model"):
        for m, v in res["truncation_by_model"].items():
            print("      %-40s %5.1f%%" % (m.split("/")[-1], v))
    print("  empty responses        %d" % res.get("n_empty", 0))
    if "cap" in res:
        print("  token cap / max out    %d / %d  (%d crowding)"
              % (res["cap"], res["max_tokens_out"], res.get("n_crowding_cap", 0)))
    print("")

    for w in res["warnings"]:
        print("  WARNING: %s" % w)
    for p in res["problems"]:
        print("  BLOCKER: %s" % p)
    print("")
    if res["problems"]:
        print("NOT FIT TO SCORE -- %d blocker(s). Spending judge calls on this run buys "
              "numbers that are not measurements." % len(res["problems"]))
        return 1
    print("ACCEPTED -- fit to score.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
