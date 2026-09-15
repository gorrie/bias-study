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
    `<run>/raw/<model>.jsonl`; `run_compass.py` writes `<run>/<model>__<cond>.jsonl`
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


def analyse_sheets(rows):
    """Checks that only mean anything for a WHOLE-SHEET forced-choice run.

    The judged checks above read `response_text` and ask whether it was severed.
    A forced-choice sheet fails differently: it parses partially, or the model
    answers every item identically, or the presentation order was never swept --
    and none of those show up as a truncated paragraph.

    Returns {} for a judged run, so the caller can merge unconditionally.
    """
    sheets = [r for r in rows if r.get("schema") == "compass-run/1"]
    if not sheets:
        return {}

    out = {"n_sheets": len(sheets), "problems": [], "warnings": []}
    valid = [r for r in sheets if r.get("valid")]
    out["n_valid_sheets"] = len(valid)
    out["failure_modes"] = dict(collections.Counter(
        r.get("failure_mode") or "-" for r in sheets if not r.get("valid")))

    # Parse rate per sheet. A sheet answering 44 of 60 is not a position.
    rates = []
    for r in sheets:
        n_items = r.get("n_items") or len(r.get("answers") or []) or 1
        rates.append((r.get("n_answers") or len(r.get("answers") or [])) / float(n_items))
    out["min_parse_rate"] = round(min(rates), 3)
    out["mean_parse_rate"] = round(sum(rates) / len(rates), 3)
    under = sum(1 for x in rates if x < SHEET_PARSE_BLOCK)
    if under:
        out["problems"].append(
            "%d of %d sheet(s) parsed below %.0f%% of their items (worst %.0f%%). A partially "
            "parsed sheet is not a position and must not be scored as one."
            % (under, len(sheets), 100 * SHEET_PARSE_BLOCK, 100 * min(rates)))

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

    out["instruments"] = sorted({(r.get("instrument") or "?")[:40] for r in sheets})
    if len(out["instruments"]) > 1:
        out["problems"].append(
            "this run mixes %d instruments: %s. They are never pooled."
            % (len(out["instruments"]), out["instruments"]))
    return out


def analyse(rows):
    out = {"n_records": len(rows), "problems": [], "warnings": []}
    if not rows:
        return out

    ok_rows = [r for r in rows if r.get("ok")]
    out["n_ok"] = len(ok_rows)
    out["n_failed"] = len(rows) - len(ok_rows)

    sheets = analyse_sheets(rows)
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
    prose_rows = [r for r in ok_rows if r.get("schema") != "compass-run/1"]
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
    empty_rate = n_empty / max(1, len(ok_rows))
    out["pct_empty"] = round(100.0 * empty_rate, 2)
    if n_empty and empty_rate > EMPTY_BLOCK:
        out["problems"].append(
            "%d of %d completed calls (%.1f%%) returned no text -- the whole budget went to "
            "reasoning tokens. At this rate the model is not answering, and its cells are "
            "missing rather than measured."
            % (n_empty, len(ok_rows), 100.0 * empty_rate))
    elif n_empty:
        out["warnings"].append(
            "%d completed call(s) returned no text (%.2f%%). Below the %.0f%% block "
            "threshold, and score.py + eligibility both exclude them, so they cannot reach "
            "a judge or an aggregate -- but they are missing cells, not measured ones."
            % (n_empty, 100.0 * empty_rate, 100.0 * EMPTY_BLOCK))

    # 6. replicate distinctness
    cells = collections.defaultdict(list)
    for r in ok_rows:
        cells[(r.get("model"), r.get("condition"), r.get("question_id"))].append(
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
    res = analyse(rows)
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
