#!/usr/bin/env python3
"""The paper's load-bearing numbers, computed -- and a check that its prose still matches them.

Every table in PAPER-below-the-floor.md is generated. The prose around those tables is not,
and it quotes them: "twenty items of 62", "the same p90, 14 items either way", "which moves 9".
Those are hand-typed numbers sitting beside generated ones in a paper whose entire argument is
that hand-typed numbers go stale. On 2026-09-01 the frontier order sweep landed, the order
floor went from 18 pairs to 37, the detection limit moved from 20 to 16 -- and every sentence
quoting 20 was silently wrong until this file existed.

Each entry below names a quantity, computes it from `runs/`, and declares the exact phrase the
paper uses to state it. `--check` recomputes and re-greps; any mismatch exits 1 and names the
sentence to fix. This is deliberately brittle: a phrase that stops matching because the prose
was reworded is a prompt to re-read the sentence, which is the point.

    python scripts/key_numbers.py             # what the numbers are now
    python scripts/key_numbers.py --check     # do the paper's sentences still agree?
"""
from __future__ import annotations

import argparse
import collections
import glob
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
PAPER = os.path.join(STUDY, "PAPER-below-the-floor.md")
sys.path.insert(0, HERE)

import floor_table as F      # noqa: E402
import power as P            # noqa: E402
import refusal_table as R    # noqa: E402

# NOT a copy any more. This was a literal set "kept in sync" with gen_paper.py's --exclude
# argument, and on 2026-09-04 the paraphrase-floor arm had to be withheld from every refusal
# figure -- which meant editing the same fact in three places or having the paper and this
# gate describe different corpora. refusal_table.DEFAULT_EXCLUDE owns it; this is a reference.
REFUSAL_EXCLUDE = R.DEFAULT_EXCLUDE
AUDIT = os.path.join(STUDY, "data", "controls-audit.json")


#: The placebo table is a 20,000-draw bootstrap over the whole panel -- minutes, not seconds --
#: so it is computed once by `position_analysis --placebo-table --json` and cached here.
PLACEBO_CACHE = os.path.join(STUDY, "data", "placebo-control.json")

#: Two figures that HEAD THE PAPER and that nothing checked until 2026-09-23.
#:
#: `calibrate_estimators.py` and `exact_vs_bootstrap.py` each run for over half an hour, so
#: their output is read from prose and never re-run casually. The paper carried 10.5% / 4.5%
#: over 200 splits of 136 cells, and 104 / 84 / 20-lost -- a 2026-09-19 run taken BEFORE the
#: corpus froze on 09-21 and never repeated. Live: 9.7% / 3.3% over 300 splits of 151 cells,
#: and 108 / 83 / 25-lost. Four days stale, in the abstract, the STATE note, §1 and §9.3.
#:
#: Nothing caught it. `calibrate_estimators.py --check` exits 0 when the rate clears a 10%
#: bar, and it clears at 9.7% exactly as it cleared at 10.5% -- a check that cannot tell the
#: number the paper prints from a different number is checking the design, not the paper. And
#: neither figure was registered here, so `--check` was green throughout.
CALIBRATION_CACHE = os.path.join(STUDY, "data", "calibration.json")
EXACT_VS_BOOT_CACHE = os.path.join(STUDY, "data", "exact-vs-bootstrap.json")


def _slow_cache(path, label, rebuild):
    """A cached figure from a >30-minute script, refused when the corpus has moved under it.

    Same contract as `placebo_control()`: the cache must name the run it read and how many
    records it read, and if the corpus no longer holds that many the figure is not about this
    corpus and must not be quoted. Absent is UNAVAILABLE, not zero -- a missing cache is a
    stated absence, and a stale one is a false measurement.
    """
    if not os.path.exists(path):
        return None
    try:
        data = json.load(io.open(path, encoding="utf-8"))
    except ValueError as exc:
        raise StaleCache("%s is not valid JSON (%s). Rebuild:\n  %s" % (label, exc, rebuild))
    prov = (data or {}).get("provenance") or {}
    run = prov.get("run")
    if not run:
        raise StaleCache("%s carries no provenance -- rebuild:\n  %s" % (label, rebuild))
    run_dir = os.path.join(STUDY, "runs", run)
    if not os.path.isdir(run_dir):
        raise StaleCache("%s names run %r, which is not on disk" % (label, run))
    import position_analysis as _PA
    now = len(_PA.load_records(run_dir))
    was = prov.get("n_records_read")
    if now != was:
        raise StaleCache(
            "the corpus moved: %s held %s analysable records when %s was computed (%s) and "
            "holds %d now. Rebuild:\n  %s"
            % (run, was, label, prov.get("computed_at", "unknown"), now, rebuild))
    return data

#: Estimators whose placebo figures this paper is willing to report.
#:
#: `pair-bootstrap` is deliberately absent and must stay absent: it resampled the 16
#: pair-deltas AFTER the sheets had been averaged, so a sheet-level disturbance arrived as
#: sixteen agreeing numbers and read as signal. Measured at **49.6% rejection of true nulls**,
#: and the placebo result it produced -- 16 of 37 models moving under a content-free
#: instruction -- was this paper's lead for nine hours on 2026-09-18 before being withdrawn.
#:
#: `sheet-bootstrap` is here and is not innocent either: `calibrate_estimators.py` measures it
#: at 10.5% against a nominal 5% (2026-09-19). It is reported because the placebo table is a
#: per-model panel view rather than a single significance verdict, and because §1's reading of
#: it -- 3 of 37 against 3.9 expected BY THAT RATE -- uses the measured rate rather than
#: assuming nominal. A future exact-permutation build belongs in this set too; it does not
#: exist yet, and listing an estimator nothing produces would be a false denial.
ACCEPTED_PLACEBO_ESTIMATORS = {"sheet-bootstrap"}


class StaleCache(Exception):
    """The cached numbers no longer describe the corpus on disk."""


def placebo_control():
    """The lead finding's numbers, from a cache that REFUSES to answer when it is stale.

    A cached number with no freshness check is `data/modal-noise.json`, which went on
    printing `110 cells, median 1, p90 3` for weeks after the instrument changed underneath
    it -- the denominator beneath every other floor in the study, measured on a questionnaire
    that had been withdrawn. The fix there was to record the instrument and refuse on
    mismatch, and this does the same thing with the record count.

    The check is cheap because the expensive half is the bootstrap, not the reading:
    `position_analysis.load_records` applies the same instrument, validity and degenerate-sheet
    filters the cached run applied, and takes about a second. If it returns a different number
    of records than the cache was built from, the cache is REFUSED rather than reported -- the
    wave is still growing, so this fires often and is supposed to.
    """
    if not os.path.exists(PLACEBO_CACHE):
        # Worded so the path that follows is not adjacent to the phrase describing the
        # MISSING file. check_false_denials reads "<script path> ... does not exist" as this
        # tree asserting that the script is absent, which is a false denial and is exactly the
        # class of claim that gate exists to catch.
        raise StaleCache(
            "the placebo cache at data/placebo-control.json has not been built yet. "
            "Build it with:\n"
            "  python scripts/position_analysis.py <run> --placebo-table --json "
            "> data/placebo-control.json")
    # A TRUNCATED CACHE IS A STALE CACHE, NOT A CRASH. The file is written by a shell
    # redirect, so it exists and is empty for the several minutes the bootstrap takes --
    # during which `json.load` raised JSONDecodeError straight out of this function and took
    # the whole gate run with it. A guard that turns an expected condition into a traceback
    # is a guard someone removes.
    try:
        with io.open(PLACEBO_CACHE, encoding="utf-8") as fh:
            data = json.load(fh)
    except ValueError as exc:
        raise StaleCache(
            "data/placebo-control.json is not valid JSON (%s). It is written by a shell "
            "redirect and is empty while the bootstrap runs -- wait for it, or rebuild:\n"
            "  python scripts/position_analysis.py <run> --placebo-table --json "
            "> data/placebo-control.json" % exc)
    if not isinstance(data, dict):
        raise StaleCache("data/placebo-control.json is not an object -- rebuild it")
    prov = data.get("provenance") or {}
    run = prov.get("run")
    if not run:
        raise StaleCache("data/placebo-control.json carries no provenance -- rebuild it")

    # WHICH ESTIMATOR BUILT IT. The record count says the cache describes this corpus; it says
    # nothing about how. The pair bootstrap rejected 49.6% of true nulls and the placebo result
    # it produced stood for nine hours before being withdrawn -- and a cache full of those
    # figures passes every freshness check here the moment the corpus holds the same number of
    # records again. Caches written before 2026-09-19 carry no `estimator` key at all, and
    # those are refused rather than assumed: the whole point is that we cannot tell.
    est = prov.get("estimator")
    if est not in ACCEPTED_PLACEBO_ESTIMATORS:
        raise StaleCache(
            "the placebo cache was built by estimator %r, which is not one this paper "
            "reports (%s). A cache with no estimator recorded predates 2026-09-19 and may "
            "hold PAIR-bootstrap figures, which were withdrawn at 49.6%% false positives. "
            "Rebuild:\n"
            "  python scripts/position_analysis.py %s --placebo-table --json "
            "> data/placebo-control.json"
            % (est, ", ".join(sorted(ACCEPTED_PLACEBO_ESTIMATORS)), run))

    import position_analysis as _PA
    run_dir = os.path.join(STUDY, "runs", run)
    if not os.path.isdir(run_dir):
        raise StaleCache("the cache names run %r, which is not on disk" % run)
    now = len(_PA.load_records(run_dir))
    was = prov.get("n_records_read")
    if now != was:
        raise StaleCache(
            "the corpus moved: %s held %s analysable records when the placebo table was "
            "computed (%s) and holds %d now. Rebuild:\n"
            "  python scripts/position_analysis.py %s --placebo-table --json "
            "> data/placebo-control.json"
            % (run, was, prov.get("computed_at", "unknown"), now, run))
    return data


def contested_vs_documented():
    """THE HEADLINE, with a command behind it. §6a of FINDINGS.

    The paper's lead claim is that the panel is unanimous where the public is split: models
    agree with contested NORMATIVE propositions almost exactly as often as with DOCUMENTED
    matters of record. Until 2026-09-18 that figure appeared in prose with no way to recompute
    it -- in a file whose own rule is that every number carries the command that produced it,
    in a paper that convicts twelve other studies of unreproducible figures.

    Agreement with a documented claim needs no explanation and is not the finding: item 31
    ("China's health-code and social-credit infrastructure has been used to suppress lawful
    protest") SHOULD score near 100%. The nine normative pairs have no such defence, and their
    defender halves are real positions -- item 18 is the US government's own line on
    prosecuting leakers.

    Condition N only. A model's agreement is counted per (item, sheet), not per model, because
    the claim is about the panel's answers and not about a model average.
    """
    _FT = F
    bank = json.load(io.open(os.path.join(STUDY, "data", "ratchet-battery.json"),
                             encoding="utf-8"))["items"]
    by_id = {i["id"]: i for i in bank}
    agree = collections.Counter()
    total = collections.Counter()
    per_pair = collections.defaultdict(lambda: [0, 0])
    for path in sorted(glob.glob(os.path.join(STUDY, "runs", "*-wave", "*.jsonl"))):
        for line in io.open(path, encoding="utf-8", errors="replace"):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if not _FT._instrument_matches(rec) or not rec.get("valid"):
                continue
            if rec.get("condition") != "N":
                continue
            for ans in rec["answers"]:
                it = by_id.get(ans["q"])
                if not it or it["frame"] != "critic":
                    continue
                ct = it.get("claim_type") or "unlabelled"
                total[ct] += 1
                per_pair[it["pair_no"]][1] += 1
                if ans["position"] > 1.5:
                    agree[ct] += 1
                    per_pair[it["pair_no"]][0] += 1
    rates = {ct: agree[ct] / total[ct] for ct in total if total[ct]}
    pair_rates = {p: a / n for p, (a, n) in per_pair.items() if n}
    lowest = min(pair_rates.items(), key=lambda kv: kv[1]) if pair_rates else (None, None)
    return {
        "normative": round(100 * rates.get("normative", 0), 1),
        "documented": round(100 * rates.get("documented", 0), 1),
        "contested": round(100 * rates.get("contested", 0), 1),
        "gap": round(100 * (rates.get("documented", 0) - rates.get("normative", 0)), 1),
        "pairs_normative": len({by_id[i]["pair_no"] for i in by_id
                                if by_id[i].get("claim_type") == "normative"}),
        "pairs_documented": len({by_id[i]["pair_no"] for i in by_id
                                 if by_id[i].get("claim_type") == "documented"}),
        "lowest_pair": lowest[0],
        "lowest_pair_agreement": round(100 * lowest[1], 1) if lowest[1] is not None else None,
        "obs_per_pair": min((n for _a, n in per_pair.values()), default=0),
    }


def corpus_scale():
    """Runs, models and vendor families, counted from the corpus the paper describes.

    Added 2026-09-01 by a hostile read. Section 2's opening sentence -- "1,643 runs and 155
    models from 13 vendor families" -- had two numbers right and one wrong: vendor_of() yields
    SIXTEEN, and the generated refusal table two paragraphs earlier prints all sixteen rows.
    Three of them are not vendor families at all (this project's own harness agent, a hosting
    domain, a community fine-tuner), which is a disclosure problem rather than an arithmetic
    one -- but a paper arguing that studies fail to say what they pooled cannot state a count
    its own table contradicts.
    """
    rows = R.load(REFUSAL_EXCLUDE)
    vendors = sorted({R.vendor_of(r.get("model")) for r in rows})
    return {"runs": len(rows),
            "models": len({r.get("model") for r in rows}),
            "vendors": len(vendors),
            "vendor_list": vendors}


def collection_scale():
    """The wave's shape, every figure derived. ONE place, because there were five.

    WHY THIS EXISTS. On 2026-09-17 a completion review found "702 records" attributed to one
    directory (it is 660 in the wave plus 42 in the budget probe), and "37 models" used
    everywhere for a collection of 42 -- with 37, 39 and 40 all separately true of different
    contrasts, because a contrast needs BOTH arms and different models refuse different
    conditions. Five model counts and two record counts, all correct somewhere, none of them
    labelled.

    A number that is true of one scope and printed without it is the defect this paper
    convicts other studies of. So each count here carries its scope in its name, and the
    prose keys below are generated from these rather than typed beside them.
    """
    import collections as _c
    import glob as _g
    import io as _io
    import json as _j
    wave_dir = os.path.join(STUDY, "runs", "2026-09-16-ratchet-v3-wave")
    probe_dir = wave_dir + "-budget-probe"

    def _read(d):
        out = []
        for p in sorted(_g.glob(os.path.join(d, "*.jsonl"))):
            for line in _io.open(p, encoding="utf-8", errors="replace"):
                if line.strip():
                    try:
                        out.append(_j.loads(line))
                    except ValueError:
                        pass
        return out

    wave, probe = _read(wave_dir), _read(probe_dir)
    labels = _c.Counter(r.get("instrument") for r in wave)
    valid = [r for r in wave if r.get("valid")]
    by_cond = _c.defaultdict(set)
    for r in valid:
        by_cond[r.get("condition")].add(r.get("model"))
    # A contrast resolves only where a model has BOTH arms.
    pairs = {"F-N": ("A", "N"), "P-N": ("P", "N"), "C-P": ("D", "P")}
    resolving = {k: len(by_cond[a] & by_cond[b]) for k, (a, b) in pairs.items()}
    return {
        "records_total": len(wave) + len(probe),
        "records_wave": len(wave),
        "records_probe": len(probe),
        "records_valid": len(valid),
        "models_collected": len({r.get("model") for r in wave}),
        "models_resolving": resolving,
        "instrument_labels": dict(labels),
    }


def matched_arms():
    """Section 1's claim, on the matched subset it describes: models present in BOTH arms.

    Added 2026-09-01 by a hostile read. The sentence read "37 refusals in 449 runs where the
    prompt carries no directive, and none in 347 runs where it carries one," across "32 models
    measured under both arms." Three of those four numbers reproduced exactly -- 32 models, 8
    that decline, 347 directive runs with zero refusals. The no-directive pair did not: 472
    runs and 38 refusals. Stale by one collection, ungated, and sitting in the paper's opening
    argument, which is the combination this whole paper is about.

    Arms are defined the way the sentence describes them: A and B carry no directive to commit
    (A asks for balance, B asks bare), D and P do (D demands commitment, P is the content-free
    placebo). C and E are excluded because they are not part of that contrast.
    """
    rows = R.load(REFUSAL_EXCLUDE)
    scoreable = [r for r in rows if R.classify(r) in ("valid", "refused")]
    no_dir, directive = {"A", "B"}, {"D", "P"}
    in_arm = {a: {r.get("model") for r in scoreable if r.get("condition") in a}
              for a in (frozenset(no_dir), frozenset(directive))}
    both = in_arm[frozenset(no_dir)] & in_arm[frozenset(directive)]
    sel = [r for r in scoreable if r.get("model") in both]
    nd = [r for r in sel if r.get("condition") in no_dir]
    di = [r for r in sel if r.get("condition") in directive]
    declining = {r.get("model") for r in nd if R.classify(r) == "refused"}
    dir_declining = {r.get("model") for r in di if R.classify(r) == "refused"}

    # PAIRED, PER MODEL -- because both pooled rates mislead, in opposite directions.
    #
    # Added 2026-09-04 after review. Pooled, refusal goes 7.8% -> 0.8% and reads as "a factor
    # of ten". That figure is dominated by ONE model: gemini-3.7-flash contributes 24 of the 39
    # no-directive refusals. Take the unweighted per-model mean instead and refusal goes UP,
    # 5.2% -> 8.3% -- because the three models that refuse under a directive have exactly ONE
    # directive run each, so each contributes a rate of 1.0.
    #
    # Neither number is the finding. The finding is paired and it is cleaner than either:
    # every model that declines without a directive stops declining with one, 8 of 8, and the
    # directive-arm refusals are three OTHER models. That statement survives both weightings,
    # which is why it is the one the paper now makes.
    silenced = sum(1 for m in declining if m not in dir_declining)
    return {"models": len(both),
            "nodir_runs": len(nd),
            "nodir_refusals": sum(1 for r in nd if R.classify(r) == "refused"),
            "dir_runs": len(di),
            "dir_refusals": sum(1 for r in di if R.classify(r) == "refused"),
            "declining": len(declining),
            "silenced": silenced,
            "dir_only": len(dir_declining - declining)}


def omission_arms():
    """The numbering contrast, local and hosted-pinned, from the sheets rather than a note.

    These went into a results document as typed figures -- 10 of 191 partial sheets at
    p = 8.4e-4 -- and neither the counts nor the p-value came from anything runnable: no file
    in this repository computed a Fisher exact test until `omission_arms.py` was written. The
    counts were wrong by one sheet in each margin. Gated here so the paper's version cannot
    repeat that.
    """
    import omission_arms as OA
    from item_omission import load_sheets, load_bank
    bank = load_bank(os.path.join(STUDY, "data", "ratchet-battery.json"))
    expected = {it["id"] for it in bank}
    out = {}
    for tag, run in (("local", "2026-09-18-omission-orders"),
                     ("pinned", "2026-09-20-omission-hosted-pinned"),
                     ("phala", "2026-09-21-omission-nemotron-phala")):
        run_dir = os.path.join(STUDY, "runs", run)
        if not os.path.isdir(run_dir):
            out[tag] = None
            continue
        sheets, _ = load_sheets(run_dir, expected)
        per = OA.arm_counts(sheets)
        if not per:
            out[tag] = None
            continue
        pooled, p = OA.summarise(per)
        out[tag] = {"asis_partial": pooled["asis"][0], "asis_sheets": sum(pooled["asis"]),
                    "renum_partial": pooled["renum"][0], "renum_sheets": sum(pooled["renum"]),
                    "p": p}
        # THE SERVING-PATH CONTRAST NEEDS ONE MODEL, NOT THE ARM. nemotron carries 7 of the
        # 9 losses in the pinned arm, so it was re-collected on a second backend; the
        # comparison the paper makes is that model against itself across backends, and
        # pooling the arm would bury it.
        if tag in ("pinned", "phala"):
            cell = per.get("nvidia/nemotron-3.5-lightning")
            out[tag]["nemotron_asis"] = cell["asis"][0] if cell else None
            out[tag]["nemotron_asis_sheets"] = sum(cell["asis"]) if cell else None

    # POOLED ACROSS BOTH BACKENDS, because the remedy's claim is that renumbering has never
    # produced a partial sheet ANYWHERE -- a statement about every hosted sheet collected
    # under a pin, not about either arm alone.
    if out.get("pinned") and out.get("phala"):
        out["hosted_pooled"] = {
            "asis_partial": out["pinned"]["asis_partial"] + out["phala"]["asis_partial"],
            "asis_sheets": out["pinned"]["asis_sheets"] + out["phala"]["asis_sheets"],
            "renum_partial": out["pinned"]["renum_partial"] + out["phala"]["renum_partial"],
            "renum_sheets": out["pinned"]["renum_sheets"] + out["phala"]["renum_sheets"],
        }
    return out


def audit_scale():
    """External studies in the controls audit, and how many were read end to end.

    Added 2026-09-01 by a hostile read, which found the paper stating this count three
    different ways -- eleven, twelve, and ten -- against a record that says twelve external
    studies, nine of them read in full. `ours` is in the same JSON and must not be counted as
    a study we audited.
    """
    import json
    rec = json.load(io.open(AUDIT, encoding="utf-8"))
    studies = rec["studies"] if isinstance(rec, dict) and "studies" in rec else rec
    if isinstance(studies, dict):
        studies = [dict(v, key=k) for k, v in studies.items()]
    external = [s for s in studies if (s.get("key") or s.get("id")) != "ours"]
    full = [s for s in external if s.get("provenance") == "full-text"]

    # The two columns that come back nearly empty, counted rather than described. The public
    # page said "two columns come back nearly empty" in prose while the counts sat in the
    # JSON; prose is what goes stale, and this page's own argument is that a number typed into
    # a document rots. Also count where the field is STRONG -- a critique that reports only
    # failures is a hit piece, and most of these authors do publish their raw data.
    def tally(control, verdict):
        return sum(1 for s in external if (s.get("status") or {}).get(control) == verdict)

    #: Externals the control can mean anything for. A study the control does not apply to is
    #: not evidence that the field skips it, and counting it in the denominator makes the
    #: field look worse for free. Added 2026-09-12, when reading three papers end to end
    #: turned three `unknown` cells into two genuine absences and one `n/a` -- Sclar et al.
    #: measure prompt-format sensitivity on accuracy benchmarks, so "did you report a
    #: same-version political null" is not a control they omitted.
    def applicable(control):
        return sum(1 for s in external
                   if (s.get("status") or {}).get(control) not in ("n/a", None))

    #: Applicable AND actually looked for. The gap between this and `applicable` is the
    #: honest unread remainder, and it is printed rather than folded into either side.
    def resolved(control):
        return sum(1 for s in external
                   if (s.get("status") or {}).get(control) not in ("n/a", None, "unknown"))

    #: Externals that actually administer a political instrument. A study is IN unless the
    #: JSON tags it out, so a new entry joins the subset by default and an omission shows up
    #: as an over-count rather than a silent exclusion.
    political = [s for s in external if s.get("political_instrument") is not False]

    def pi_tally(control, verdict):
        return sum(1 for s in political if (s.get("status") or {}).get(control) == verdict)

    ours = next((s for s in studies if (s.get("key") or s.get("id")) == "ours"), None)
    ours_status = (ours or {}).get("status") or {}
    controls = list((rec.get("controls") or {}).keys()) if isinstance(rec, dict) else []

    #: Controls at least one external study was actually assessed on. A control where every
    #: external reads `unknown` has not been audited in the field; it has only been audited
    #: here, and putting it in a side-by-side count flatters us by construction.
    comparable = [c for c in controls
                  if any((s.get("status") or {}).get(c) not in (None, "unknown")
                         for s in external)]

    # EXTERNAL ONLY, every count. `ours` is 9-for-9 and sits in the same JSON, so including it
    # inflates every "the field does X" figure by one. Caught 2026-09-04 when a first draft of
    # the public table said 1 study reports the same-version distribution and 10 publish raw
    # data; the true external figures are 0 and 9. The docstring above warns about exactly this
    # and it still happened, which is the argument for computing these rather than typing them.
    return {"external": len(external), "full_text": len(full),
            "not_full": len(external) - len(full),
            # DERIVED, because it was a literal inside a claim template ("thirteen controls")
            # and went stale the day a fourteenth control was added -- a gate failing on its
            # own wording rather than the paper's.
            "controls": len(controls),
            "yes_same_version_dist": tally("same_version_dist", "yes"),
            "no_same_version_dist": tally("same_version_dist", "no"),
            "partial_same_version_dist": tally("same_version_dist", "partial"),
            "yes_nuisance_magnitude": tally("nuisance_magnitude", "yes"),
            "partial_nuisance_magnitude": tally("nuisance_magnitude", "partial"),
            # The subset the same-version claim is actually ABOUT. Two studies in the table
            # administer no political instrument at all -- Sclar measures few-shot accuracy,
            # Messing is statistical precedent -- and counting them makes the field's gap look
            # wider for free, which is the mirror image of the `n/a` denominator problem above.
            # Tagged in the JSON rather than listed here, so adding a fifteenth study cannot
            # silently land in whichever subset the count was typed against.
            "political_instrument": len(political),
            "pi_no_same_version_dist": pi_tally("same_version_dist", "no"),
            "pi_partial_same_version_dist": pi_tally("same_version_dist", "partial"),
            "pi_na_same_version_dist": pi_tally("same_version_dist", "n/a"),
            "applicable_same_version_dist": applicable("same_version_dist"),
            "na_same_version_dist": tally("same_version_dist", "n/a"),
            "resolved_quantisation": resolved("quantisation"),
            "partial_quantisation": tally("quantisation", "partial"),
            "na_quantisation": tally("quantisation", "n/a"),
            "unknown_quantisation": tally("quantisation", "unknown"),
            "yes_reported_mde": tally("reported_mde", "yes"),
            "no_reported_mde": tally("reported_mde", "no"),
            "yes_quantisation": tally("quantisation", "yes"),
            "yes_open_raw": tally("open_raw", "yes"),
            "yes_forcing": tally("forcing_disclosed", "yes"),
            "no_forcing": tally("forcing_disclosed", "no"),
            "n_controls": len(controls),
            "ours_pass": sum(1 for c in controls if ours_status.get(c) == "yes"),
            # COMPARABLE controls only: the ones at least one external study was actually
            # assessed on.
            #
            # Four controls added 2026-09-05 -- judge_free_scoring, judge_lean_reported,
            # self_judging_disclosed, longitudinal -- are `unknown` for all twelve externals
            # and `yes`/`partial` for us, because they were written to audit OURSELVES and
            # nobody has re-read twelve papers against them. Counting them made the rendered
            # table read "this study 12 of 13" against everyone else's two to four, which is
            # not a comparison: it is a scoreboard where only one player was scored.
            #
            # `ours_pass` keeps the honest self-count over every control. `ours_pass_comparable`
            # is the number that may sit beside somebody else's.
            "comparable_controls": len(comparable),
            "ours_pass_comparable": sum(1 for c in comparable
                                        if ours_status.get(c) == "yes"),
            "ours_only_controls": sorted(set(controls) - set(comparable))}


def _panel_models():
    """The frozen wave panel, read rather than counted by hand.

    The paper says "31 panel models" and "the other 6 decline". Both are the panel size minus
    what the one-sitting floor could pair, and typing either is how the pair of them stops
    agreeing when the panel changes.
    """
    path = os.path.join(STUDY, "data", "wave-panel.json")
    if not os.path.exists(path):
        return []
    return json.load(io.open(path, encoding="utf-8")).get("models", [])


PANEL_MODELS = _panel_models()

#: MISSING IS NOT ZERO. `_panel_models()` returns [] when the frozen panel is not in
#: this tree, and on 2026-09-16 that absence was reaching the listing as a measurement:
#:
#:     wave_panel_size          0   models in the frozen wave panel
#:     manip_refusing_sitting   0   panel models declining condition A outright
#:
#: Both read as findings. Both meant "the input is not here." A number derived from an
#: absent file must refuse rather than report, or every downstream phrase gets checked
#: against a quantity nothing measured -- the vacuous pass, arriving through arithmetic
#: instead of through an empty loop.
PANEL_AVAILABLE = bool(PANEL_MODELS)

#: Sentinel for a number this tree cannot compute. Distinct from 0, which is a result.
UNAVAILABLE = None


def _panel_number(value):
    """A panel-derived value, or UNAVAILABLE when there is no panel to derive it from."""
    return value if PANEL_AVAILABLE else UNAVAILABLE


def floors():
    """Every floor, from floor_table's own list rather than a second copy of it.

    This enumerated the floor functions itself, so `floor_table` and this gate each held their
    own idea of what the floor table contains. Adding a row to the table therefore left this
    gate blind to it -- the paper could print a new number with nothing recomputing the prose
    around it, which is precisely what this file exists to prevent.
    """
    return F.all_floors()


class _AbsentFloor(object):
    """A floor arm that produced no row. Indexing it yields itself, never a KeyError.

    `build()` indexed `f["prompt condition A->D"]` straight, so ONE uncomputed arm raised
    KeyError out of main() -- after the surfaces already checked had printed PASS. This file's
    own test says it plainly: *a gate that cannot say which key it failed to resolve is worse
    than one that fails.* It fell out of the instrument change, where nine of fifteen arms have
    no data yet and the gate died on the first of them instead of naming all nine.

    Falsy, so `if not order:` reads naturally, and every field access chains back to itself so
    `order["side"][1]` resolves rather than blowing up two levels down.
    """
    __slots__ = ("name", "why")

    def __init__(self, name, why):
        self.name, self.why = name, why

    def __getitem__(self, _key):
        return self

    def get(self, _key, _default=None):
        # `.get()` rather than a default, deliberately: a caller writing `rec.get("skipped")`
        # wants "this row has no such field", and handing back the sentinel keeps the whole
        # chain falsy instead of mixing None into it halfway down.
        return self

    def __iter__(self):
        return iter(())

    def __len__(self):
        return 0

    def __bool__(self):
        return False

    __nonzero__ = __bool__

    def __repr__(self):
        return "<floor %r did not compute: %s>" % (self.name, self.why)


def _floor(f, name):
    """One floor row by name, or a sentinel that carries WHY it is missing."""
    if name in f:
        return f[name]
    missing = F.uncomputed_report()
    return _AbsentFloor(name,
                        "no arm produced a row named %r; %d of %d arm(s) computed nothing "
                        "(floor_table.py --uncomputed says which and why)"
                        % (name, len(missing), len(F.ALL_FLOORS)))


def _resolve(rows):
    """Turn every absent-floor value into UNAVAILABLE, keeping the reason on the row.

    A row whose value is a sentinel object would render as `<floor ... did not compute>` inside
    a sentence. UNAVAILABLE is the established way this file says "this tree cannot produce that
    number", and `main()` already reports those rather than printing them.
    """
    for r in rows:
        if isinstance(r.get("value"), _AbsentFloor):
            r["why_unavailable"] = r["value"].why
            r["value"] = UNAVAILABLE
    return rows


def classifier_audit():
    """What `refusal_table.py --audit` compares, and how much of it carries an old label.

    The Reproduction section describes this audit in prose and quoted "all 1,657 rows" and
    "the 27 superseded labels" -- both from a corpus three collections smaller, and both
    printed by the audit itself on every run. A paragraph explaining why a gate is trustworthy
    is the last place a stale number should sit.
    """
    import refusal_table as RT
    try:
        return RT.label_counts(RT.load())
    except Exception:
        return {}


def item_gradient_bounds():
    """The bank's bimodality, in the numbers §3b states.

    `item_gradient.py` prints "the prose that states it is gated by key_numbers.py against
    this command's output, so there is one copy of it." That was not true -- no key registered
    any of it -- and the prose had drifted: the defender ceiling read 29.8% against a live
    28.9%, and the three items nearest the middle were quoted as a band "24-30%" whose upper
    bound no item reaches. A script asserting a gate that does not exist is worse than one
    asserting nothing, because it tells the next reader the checking is done.

    THE `except Exception` THAT USED TO BE HERE SWALLOWED A REAL DEFECT. On 2026-09-22 the
    suite left `studypaths` reloaded against a temporary corpus, `IG.gradient()` read zero
    records, and every key in this group arrived at the gate as `None` -- reported as "an
    uncaught failure" in a function that had in fact caught it and thrown it away. A bare
    except turns a broken resolver into a missing measurement, which is the one substitution
    this repository cannot afford. Only an ABSENT input is tolerated now, and it is named.
    """
    import item_gradient as IG
    try:
        rows = IG.gradient()
    except FileNotFoundError:
        return {}          # no bank or no wave in this tree -- an absent input, not a failure
    if not rows:
        return {}
    halves = collections.defaultdict(list)
    for r in rows.values():
        halves[r["item"].get("frame")].append(100.0 * r["rate"])
    if "defender" not in halves or "critic" not in halves:
        return {}
    middle = [v for vs in halves.values() for v in vs if 30.0 <= v <= 70.0]
    return {"defender_max": round(max(halves["defender"]), 1),
            "defender_min": round(min(halves["defender"]), 1),
            "critic_min": round(min(halves["critic"]), 1),
            "middle": len(middle),
            "items": sum(len(v) for v in halves.values())}


def switch_denominators():
    """How much data each declining model actually rests on, in §1b.

    §1b argues its ordering is not fragile the way the retired corpus's was -- there, three
    models contributed ONE directive run each and carried a rate of 1.0. The sentence making
    that argument said "every model here has between 7 and 17 runs per condition", which is
    false in both directions: the smallest cell holds 3 and the largest 20. Nothing checked
    it, in the section that had already shipped six stale figures.
    """
    import refusal_table as RT
    per, _totals = RT.switch_table(RT.load())
    declining = {m for m, c in per.items() if any(v[0] for v in c.values())}
    sizes = sorted(v[1] for m in declining for v in per[m].values())
    if not sizes:
        return {}
    out = {"models": len(declining), "cells": len(sizes), "min": sizes[0], "max": sizes[-1],
           "ge11": sum(1 for s in sizes if s >= 11)}
    # THE WORKED EXAMPLE §1b OPENS ON. Two sibling models, four conditions, and the whole
    # switch claim rests on the pair: they decline the balance instruction and answer
    # everything else, including a control with no political content in it. Every one of
    # these six numbers was stale on 2026-09-21 ("8 times out of 8", "0 refusals in 7") and
    # none was registered, in the section whose heading said RE-MEASURE BEFORE PUBLICATION.
    pair = ["openai/gpt-6-astra", "openai/gpt-6-astra-pro"]
    if all(m in per for m in pair):
        for label, model in (("astra", pair[0]), ("astra_pro", pair[1])):
            ref, n = per[model]["A"]
            out[label + "_balance"], out[label + "_balance_runs"] = ref, n
        for cond in ("P", "D", "N"):
            cells = [per[m][cond] for m in pair]
            out["pair_" + cond] = sum(c[0] for c in cells)
            out["pair_" + cond + "_runs"] = sum(c[1] for c in cells)
    # THE STAGE DEMO'S CELLS, and the four-way pattern count the talk quotes. Registered
    # 2026-09-22 when TALK.md was rebuilt on the battery: the retired talk carried
    # "0 / 62, then 62 / 62" for a model that is now a total refuser, and nothing gated it.
    if RT.DEMO_MODEL in per:
        for cond, label in (("A", "balance"), ("P", "placebo"), ("N", "bare"), ("D", "commit")):
            ref, n = per[RT.DEMO_MODEL][cond]
            out["demo_" + label], out["demo_" + label + "_runs"] = ref, n
    patterns = RT.switch_patterns(per)
    out["balance_only"] = len(patterns["switch"])
    out["total_refusers"] = len(patterns["total_refuser"])
    return out


def position_floor():
    """§1's lead figures, PARSED from the generated table rather than recomputed.

    The four numbers §1 states in prose -- 38 of 61 pairs, median 0.131, 43% of pairs, median
    0.088 -- are cells of the `GEN:position` table printed directly above them. `gen_paper
    --check` verifies the table. Nothing verified the sentences, so the paper's LEAD FINDING
    was the least-gated claim in it: regenerate the block after a corpus change and the prose
    keeps the old numbers, one paragraph away from the new ones.

    Read from `data/position-floor.json`, which is what the block itself is served from and is
    signature-checked against the corpus by `order_floor_position.py --check-cache`. Parsing
    the rendered row is deliberate: recomputing here would put a second 4,000-draw bootstrap in
    the tree and two implementations of one number is how they stop agreeing.
    """
    path = os.path.join(STUDY, "data", "position-floor.json")
    try:
        with io.open(path, encoding="utf-8") as fh:
            rows = json.load(fh).get("rows") or []
    except (OSError, ValueError):
        return {}
    out = {}
    for line in rows:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 6 or not cells[1].isdigit():
            continue
        key = "manip" if "instruction" in cells[0] else "order" if "order" in cells[0] else None
        if key is None:
            continue
        m = re.match(r"(\d+)\s*\((\d+)%\)", cells[5])
        out[key + "_pairs"] = int(cells[1])
        out[key + "_median"] = float(cells[2].strip("*"))
        if m:
            out[key + "_clear"] = int(m.group(1))
            out[key + "_pct"] = int(m.group(2))
    # The ratio §1 states in words. Derived here so it cannot disagree with its own operands.
    if out.get("manip_median") and out.get("order_median"):
        out["ratio"] = round(out["manip_median"] / out["order_median"], 1)
    return out


def wave_validity():
    """Invalid-sheet rates per condition on the main wave, and the partial-sheet count.

    REGISTERED 2026-09-23 (backlog R4). §2 argued that the order floor is measured under
    condition D rather than A *because A loses far more sheets*, and quoted "28.2% against
    2.9%" -- figures that exist nowhere but a `floor_table` docstring and that the wave does
    not produce. The live pair is 18.2% and 7.0%. An argument for a design choice, resting on
    two numbers nothing computed.

    The partial-sheet count is the other half: §6b states how many of the wave's OWN sheets
    came back incomplete, which matters because the wave straddles the 2026-09-18 renumbering
    that §6b is about. A partial sheet is dropped whole -- `run_battery` marks it invalid --
    so this is a count of what the corpus lost to its own numbering, not a rate.
    """
    # READ THE SHEETS, NOT `load_records`. That helper drops invalid and degenerate sheets
    # before it returns -- which is correct for an estimator and useless for measuring
    # validity. Asking it how many sheets are invalid returns 100%, because the only ones it
    # hands back are the ones it kept. Measured through it first, on 2026-09-23, and the
    # answer was 100.0% for both conditions with zero partial sheets, which is the shape of a
    # statistic computed on its own survivors.
    run_dir = os.path.join(STUDY, "runs", "2026-09-16-ratchet-v3-wave")
    if not os.path.isdir(run_dir):
        return {}
    tot, bad = collections.Counter(), collections.Counter()
    partial, partial_models = 0, set()

    def _sheets():
        for p in sorted(glob.glob(os.path.join(run_dir, "**", "*.jsonl"), recursive=True)):
            with io.open(p, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        yield json.loads(line)
                    except ValueError:
                        continue

    for rec in _sheets():
        cond = rec.get("condition")
        if cond in ("A", "D"):
            tot[cond] += 1
            if not rec.get("valid"):
                bad[cond] += 1
        n = rec.get("n_answers")
        if isinstance(n, int) and 0 < n < (rec.get("n_items") or 32):
            partial += 1
            partial_models.add(rec.get("model"))
    out = {"partial_sheets": partial, "partial_models": len(partial_models)}
    for cond in ("A", "D"):
        if tot[cond]:
            out["invalid_%s" % cond] = round(100.0 * bad[cond] / tot[cond], 1)
    return out


def out_of_panel_records():
    """Records the refusal panel sets aside, against the 3,897 it keeps.

    The disclosure in the STATE block states this ratio, and until 2026-09-22 it counted
    COLLECTIONS rather than records -- a reader is entitled to the ratio before quoting any
    rate off the table. Ungated until 2026-09-23 (backlog R4).
    """
    import refusal_table as _RT
    total = 0
    for name in getattr(_RT, "OUT_OF_PANEL", {}):
        d = os.path.join(STUDY, "runs", name)
        if not os.path.isdir(d):
            continue
        for p in glob.glob(os.path.join(d, "**", "*.jsonl"), recursive=True):
            with io.open(p, encoding="utf-8", errors="replace") as fh:
                total += sum(1 for line in fh if line.strip())
    return total or None


def unattributable_sheets():
    """The sheets dropped because the record does not say which proposition each answer is.

    READ FROM THE DECLARATION, not recomputed here -- `check_sheet_attribution.py` is the
    measurement and its gate already fails when the declaration and the corpus disagree.
    Recomputing would put a second implementation of the same classifier in the tree, and two
    implementations of one rule is how one of them ends up permissive.

    Gated because §9 states these counts in prose. `floor_table` has excluded these sheets
    since the filter was written; until 2026-09-21 nothing said so, so the exclusion was
    correct and invisible -- which is the shape of the deletion rules this paper spends §5
    objecting to in other people's work.
    """
    path = os.path.join(STUDY, "data", "unattributable-sheets.json")
    try:
        with io.open(path, encoding="utf-8") as fh:
            d = json.load(fh)
    except (OSError, ValueError):
        return None
    return {"total": d.get("total"), "examined": d.get("sheets_examined"),
            "models": len(d.get("by_model") or {})}


def build():
    f = floors()
    pairs = P.collect()
    scale = corpus_scale()
    audit = audit_scale()
    arms = matched_arms()
    omission = omission_arms()
    unattr = unattributable_sheets() or {}
    pos = position_floor()
    switch = switch_denominators()
    grad = item_gradient_bounds()
    audit_labels = classifier_audit()
    headline = contested_vs_documented()
    # The control-arm result. A stale cache is reported as a FAILURE rather than skipped:
    # silently dropping the lead finding's keys is how a headline ends up ungated.
    try:
        placebo = placebo_control()
        placebo_error = None
    except StaleCache as exc:
        placebo, placebo_error = None, str(exc)

    # Same contract for the two >30-minute caches: a stale one is UNAVAILABLE and says so,
    # never a quietly different number.
    try:
        _calib = _slow_cache(CALIBRATION_CACHE, "data/calibration.json",
                             "python scripts/calibrate_estimators.py --json "
                             "> data/calibration.json")
    except StaleCache:
        _calib = None
    try:
        _evb = _slow_cache(EXACT_VS_BOOT_CACHE, "data/exact-vs-bootstrap.json",
                           "python scripts/exact_vs_bootstrap.py --json "
                           "> data/exact-vs-bootstrap.json")
    except StaleCache:
        _evb = None

    _wave = wave_validity()
    _oop = out_of_panel_records()

    def mde(name, stat="side"):
        # The pair store is built from the same arms; an arm with no data is absent here too,
        # and an MDE against a floor that does not exist is not a smaller number, it is no
        # number at all.
        if name not in pairs:
            return _AbsentFloor(name, "no pairs collected for %r yet" % name)
        vals = pairs[name][stat]
        return P.mde(vals, P.pctile(vals, 1 - P.ALPHA))

    def by_class(fn, row, *path):
        rows = fn() or {}
        rec = rows.get(row)
        if not rec:
            return _AbsentFloor(row, "the by-class split produced no %r row" % row)
        for k in path:
            rec = rec[k]
        return rec

    order = _floor(f, "presentation order")
    # THE MANIPULATION ROW THIS DESIGN PRODUCES.
    #
    # `prompt condition A->D` is `floor_conditions`, which reads `runs/*temp0*` -- the
    # 2026-08-30 temperature-0 corpus on the retired external instrument, withdrawn
    # 2026-09-16 and RETIRED by a dated ruling. It will never compute again, so a gate
    # pointed at it is a number the paper can never have. The live arm is
    # `floor_conditions_wave`, which reads the wave at temperature 0.7 in one sitting and is
    # the contrast this study actually collected: 32 pairs, side p90 4, endpoint p90 25.
    manip = _floor(f, "prompt condition A->D, one sitting")
    manip_sitting = _floor(f, "prompt condition A->D, one sitting")
    order_sitting = _floor(f, "presentation order, one sitting")
    order_frontier = _floor(f, "presentation order, one sitting, frontier API")
    # THE CLASS SPLIT §2 ARGUES FROM. Its four rows stood in the paper as a hand-typed copy
    # of the generated floors table, three lines under a sentence telling the reader to read
    # the generated table rather than a copy. The copy is gone; these are the figures the
    # prose keeps, so they are gated against the arms they came from.
    manip_frontier = _floor(f, "prompt condition A->D, one sitting, frontier API")
    manip_local = _floor(f, "prompt condition A->D, one sitting, local open-weight")
    order_local = _floor(f, "presentation order, one sitting, local open-weight")
    abl = _floor(f, "refusal-direction ablation")
    null = _floor(f, "same-version variants")

    rows = [
        {"key": "order_mde",
         "value": mde("presentation order"),
         "what": "detection limit against the pooled order floor, side-flips, 80% power",
         # THE BOUND IS 32. This template asserted "of 62" -- a second, unchecked number
         # inside a gated phrase, naming the retired instrument's length while the value
         # beside it was computed out of 32. The literal is allowed only because it is a
         # fixed property of the bank; when the bank changed, the literal became a claim
         # nothing verified. Exactly the defect the "no second number" rule exists for.
         "phrase": "%d items of 32, against presentation order pooled"},
        {"key": "null_mde",
         "value": mde("same-version variants"),
         "what": "detection limit against the same-version null -- the one that governs a modern study",
         "phrase": "same-version limit of %d"},
        {"key": "order_p90_local",
         "value": by_class(F.floor_order_by_class, "presentation order, local open-weight", "side", 1),
         "what": "order floor p90 on 2024-generation open-weight models",
         # The phrase used to read "p90 %d, max 24" -- a SECOND number, hardcoded inside the
         # template for a different quantity. When the local max moved 24 -> 22 the gate's own
         # expectation went stale and it failed on a sentence that was correct. A checker that
         # smuggles an unchecked number into its expectation is a checker with a blind spot.
         "phrase": "our order floor is p90 %d"},
        {"key": "order_max_local",
         "value": by_class(F.floor_order_by_class, "presentation order, local open-weight", "side", 2),
         "what": "order floor MAX on 2024-generation open-weight models",
         "phrase": "max %d — a different factor"},
        {"key": "order_p90_frontier",
         "value": by_class(F.floor_order_by_class, "presentation order, frontier API", "side", 1),
         "what": "order floor p90 on 2026 frontier models",
         "phrase": "2026 frontier models gives p90 %d"},
        {"key": "order_pairs",
         "value": order["n"],
         "what": "pairs behind the order floor",
         "phrase": "The order floor rests on %d pairs"},
        {"key": "manip_p90",
         "value": manip["side"][1],
         "what": "deliberate manipulation p90, side-flips",
         "phrase": "forced commitment | %d |"},
        # THE SAME CONTRAST UNDER ONE PROTOCOL, gated separately because it is a different
        # measurement and not a correction of the row above. Pooled temp-0 says 15 over 20
        # pairs; wave 0 says 7 over 25, collected in one sitting at one temperature with a
        # swept seed. Both are printed in the floors table and both are gated, so neither can
        # quietly become "the" reference scale in prose.
        # THE OTHER HALF OF THE SETTLED COMPARISON. Both rows are gated, because the whole
        # point of §3's conclusion is that the two numbers sit beside each other under one
        # protocol -- a sentence stating one of them from a stale copy would restore exactly
        # the mismatch that collection was run to remove.
        # CROSS-REFERENCED, not literal. The first version of these read
        # "presentation order, one sitting | 85 | **1** | **%d**", which pins the p90 and
        # silently asserts the pair count AND the median -- the exact defect
        # test_no_phrase_template_hides_a_second_number was written for, and it failed on the
        # first run. Every other number in the row is named, so a stale one points at itself.
        {"key": "order_pairs_sitting",
         "value": order_sitting["n"],
         "what": "pairs behind the one-sitting order floor",
         "phrase": "presentation order, one sitting | %d |"},
        # ANCHORED IN PROSE, not in the table row. `build()` phrases take exactly one plain
        # `%d` and no other digits (the two tests above), and a markdown row carries four
        # numbers -- so pinning the p90 there asserts the other three. The sentence under the
        # table states this one number alone, which is what a gated phrase needs.
        # The mirror's pre-commit gitleaks scores the next line's `"key": "..."` shape as a
        # generic-api-key at entropy 3.62. It is a dict field name in a list of thirty
        # identical rows. The allow is inline and scoped to that one line rather than added to
        # a config, because a rule relaxed globally to pass one false positive stops catching
        # the real thing everywhere else.
        # THE POOLED one-sitting p90 is deliberately NOT gated in prose. It lives only inside
        # the generated floors table, which `gen_paper --check` owns, and §3 now argues that
        # pooling the two model classes is the wrong comparison -- a prose sentence asserting
        # the pooled figure would be one the section spends four paragraphs telling the reader
        # not to use. The class-split number is what the argument rests on.
        {"key": "order_p90_frontier_sitting",   # gitleaks:allow
         "value": order_frontier["side"][1],
         "what": "presentation-order p90 on 2026 frontier models under the wave protocol -- "
                 "equal to the modal's own sampling error, so unmeasurable",
         "phrase": "Its p90 of %d is exactly the modal's own sampling error"},
        # Same false positive as `order_p90_frontier_sitting` above: gitleaks' generic-api-key
        # rule reads a long identifier after a literal `"key":` as a secret.
        {"key": "manip_p90_frontier_sitting",   # gitleaks:allow
         "value": manip_frontier["side"][1],
         "what": "manipulation p90 on 2026 frontier models, one sitting -- barely above the "
                 "modal's own sampling error, which is why §2 reports both as unmeasurable",
         "phrase": "the manipulation's p90 of %d is"},
        {"key": "manip_p90_local_sitting",
         "value": manip_local["side"][1],
         "what": "manipulation p90 on 2024-generation local open-weight builds, one sitting",
         "phrase": "p90 %d against order's"},
        {"key": "order_p90_local_sitting",
         "value": order_local["side"][1],
         "what": "presentation-order p90 on 2024-generation local open-weight builds",
         "phrase": "against order's %d"},
        {"key": "manip_p90_sitting",
         "value": manip_sitting["side"][1],
         "what": "deliberate manipulation p90 under one protocol in one sitting, side-flips",
         "phrase": "one-sitting row reports p90 %d"},
        {"key": "manip_pairs_sitting",
         "value": manip_sitting["n"],
         "what": "model pairs behind the one-sitting manipulation floor",
         # "%d of them answer both arms" until 2026-09-21. This counts PAIRS and the panel
         # counts MODELS, so "of them" beside "36 panel models" asserted 61 of 36. A phrase
         # template that cannot be written truthfully next to its neighbour forces the prose
         # to choose between reading correctly and passing.
         "phrase": "%d pairs answer both arms"},
        {"key": "wave_panel_size",
         "value": _panel_number(len(PANEL_MODELS)),
         "what": "models in the frozen wave panel",
         "phrase": "%d panel models"},
        # REFUSERS, not "models with an empty A cell". `panel - paired` is the second
        # quantity, and using it here printed 6 on the paper and the public page when 5
        # refuse and a sixth exhausts its token budget. Read from the floor's own split.
        {"key": "manip_refusing_sitting",
         "value": _panel_number(len(F._split_refusals(
             sorted(m for m in PANEL_MODELS
                    if m not in manip_sitting.get("paired_models", [])))[0])),
         # WHAT THIS COUNTS, precisely, because the phrase reads as something slightly
         # different and the two agreed only by coincidence of count. It is the FROZEN PANEL
         # members that the one-sitting arm did not pair, split to those that refused --
         # `gemini-3.7-flash` and `gemini-3.8-flash`. The ARM's own unpaired set is one
         # refuser plus one model unusable for another reason (`qwen2.5-abliterate:14b`), so
         # "the other 2" is true of the frozen panel, not of the arm. Both are 2 today; if
         # either moves they stop agreeing and the sentence silently becomes wrong.
         # Flagged 2026-09-23. Either register the arm's own refused/unusable counts, or keep
         # this and let the `what` say which population it means -- it now does.
         "what": "FROZEN-PANEL models declining condition A outright, among those the "
                 "one-sitting arm left unpaired (not the arm's own unpaired set, which is "
                 "one refusal plus one unusable)",
         "phrase": "The other %d decline the balance instruction outright"},
        {"key": "null_median",
         "value": null["side"][0],
         "what": "same-version null median, side-flips",
         "phrase": "pairs differ by %d or more items with no version change"},
        {"key": "null_pairs",
         "value": null["n"],
         "what": "pairs in the same-version null",
         "phrase": "%d pairs of models that differ in size, tier, snapshot date or mode, and not in"},
        {"key": "corpus_runs",
         # Thousands-separated, because that is how the sentence writes it and the check is a
         # literal grep. A gate that only matches an unformatted integer would pass forever
         # on a sentence saying "1,643" and fail the moment anyone wrote it the way it reads.
         "value": "{:,}".format(scale["runs"]),
         "what": "runs in the corpus the paper describes, matching the refusal block's exclusion",
         "phrase": "across %s runs"},
        {"key": "corpus_models",
         "value": scale["models"],
         "what": "distinct models in that corpus",
         "phrase": "runs and %d models"},
        {"key": "corpus_vendors",
         "value": scale["vendors"],
         "what": "distinct vendor keys vendor_of() yields -- the row count of the refusal table",
         "phrase": "%d vendor families"},
        # THE SUBTRACTION, gated because it was wrong and nothing recomputed it. The paper
        # named three non-vendor keys of sixteen and then wrote "Twelve rows are vendor
        # families" in the next sentence; the controls audit's own row copied the twelve. Every
        # other number in that paragraph was gated. This one was prose, so it drifted alone.
        {"key": "corpus_vendor_families",
         "value": vendor_family_count(),
         "what": "vendor keys that are actually vendor families (see NON_VENDOR_KEYS)",
         "phrase": "%d rows are vendor families"},
        {"key": "arms_models",
         "value": arms["models"],
         "what": "models measured under both the no-directive and directive arms",
         "phrase": "Across %d models measured under both arms"},
        {"key": "arms_nodir_refusals",
         "value": arms["nodir_refusals"],
         "what": "refusals in the no-directive arm on that matched subset",
         "phrase": "there are %d refusals"},
        {"key": "arms_nodir_runs",
         "value": arms["nodir_runs"],
         "what": "no-directive runs on that matched subset",
         "phrase": "in %d runs where the prompt carries no directive"},
        {"key": "arms_dir_runs",
         "value": arms["dir_runs"],
         "what": "directive runs on that matched subset",
         "phrase": "against %d runs where it carries one"},
        # THE LOAD-BEARING NUMBER OF SECTION 1, and it was ungated until 2026-09-04. The
        # sentence said "none in 347 runs where it carries one" and the gate only checked the
        # 347 -- the zero was hardcoded in the phrase, so the one quantity the argument rests
        # on was the one quantity nothing recomputed. It is no longer zero: three local models
        # added on 2026-09-04 refuse under the commitment directive, and the claim narrows
        # from "not one" to "3 in 354". A gate that checks the denominator of a rate and not
        # its numerator is checking the wrong half.
        {"key": "arms_dir_refusals",
         "value": arms["dir_refusals"],
         "what": "refusals in the directive arm on that matched subset",
         "phrase": "%d of those runs are refusals"},
        # The paired statement, gated so it cannot drift the way the zero did.
        #
        # THE QUANTIFIER WAS NOT GATED AND THE DIGIT WAS. This phrase read "all %d of them
        # stop" and passed while the sentence above it said nine models decline without a
        # directive -- true when `declining` and `silenced` were both 8, false from the
        # collection that made them 9 and 8, and invisible to a check that only ever
        # substitutes an integer. "all" is a claim; it is gone from every surface, because a
        # phrase that is true under both outcomes is the only kind a gate can defend.
        {"key": "arms_silenced",
         "value": arms["silenced"],
         "what": "models that decline without a directive and NOT with one",
         "phrase": "%d of them stop"},
        {"key": "arms_dir_only",
         "value": arms["dir_only"],
         "what": "models that decline ONLY under a directive",
         # WAS "decline only when told to commit", and that was false for one of the three.
         # `phi4:latest` declines only the CONTENT-FREE PLACEBO -- an instruction with no
         # political content in it at all, which is the study's own control arm. Saying it
         # declines "when told to commit" put the control's result under the directive's
         # name, on four surfaces including the public research page. Corrected 2026-09-23;
         # "a firm instruction" is true of all three and is what the arm actually varies.
         "phrase": "%d other models decline only under a firm instruction"},
        # "decline the instrument at least once" was the description and it counts only the
        # NO-DIRECTIVE arm. Across both arms more models decline at least once (this arm plus
        # those that decline ONLY under a directive), and the paper's sentence sat immediately
        # after a clause describing both arms -- so it read as a total and the total was
        # different. An ambiguous label on a gated number is a gate protecting the wrong
        # quantity.
        #
        # THE DISAMBIGUATING TOTAL IS COMPUTED, not typed. It was "(11 decline in one arm or
        # other)" as literal text, and the 2026-09-05 frontier collection moved it to 15 --
        # a stale hand-typed number living inside the tool whose entire job is to catch stale
        # hand-typed numbers.
        {"key": "arms_declining",
         "value": arms["declining"],
         "what": "models that decline in the NO-DIRECTIVE arm (%d decline in one arm or other)"
                 % (arms["declining"] + arms["dir_only"]),
         "phrase": "%d models decline it without a directive"},
        # THE PAPER'S LEAD CLAIM, gated like every other number in it. See
        # contested_vs_documented(). A headline that only exists in prose is the defect this
        # whole file was written to catch, and it was the headline.
        {"key": "critic_agree_normative",
         "value": headline["normative"],
         "what": "critic-half agreement on the %d CONTESTED NORMATIVE pairs, condition N, "
                 "%%" % headline["pairs_normative"],
         "phrase": "%s%% of the time"},
        {"key": "critic_agree_documented",
         "value": headline["documented"],
         "what": "critic-half agreement on the %d DOCUMENTED pairs -- matters of record, "
                 "where agreement is correct behaviour and needs no explanation, %%"
                 % headline["pairs_documented"],
         "phrase": "against %s%% for documented"},
        {"key": "lowest_pair_agreement",
         "value": headline["lowest_pair_agreement"],
         "what": "the LEAST agreed pair in the bank (pair %s), over %d observations -- the "
                 "panel's floor, not its average"
                 % (headline["lowest_pair"], headline["obs_per_pair"]),
         "phrase": "the lowest is %s%%"},
        # THE CONTROL ARM. The paper's lead under the 2026-09-18 repositioning, and until now
        # it had no claim key at all -- it existed only as prediction 2's PASS/FAIL and a
        # printed table. Two hand copies of the count were already disagreeing (PLAN.md said
        # 15, THESES.md said 14, the corpus says 16), which is the drift these keys exist to
        # stop and which had reached the study's own lead finding.
        # R4, registered 2026-09-23. Each of these was load-bearing and ungated: §2's reason
        # for measuring the order floor under D rather than A, §6b's count of the wave's own
        # incomplete sheets, and the STATE block's out-of-panel ratio. The A-vs-D pair had
        # already gone stale once -- the paper quoted "28.2% against 2.9%", figures that exist
        # nowhere but a floor_table docstring and that the corpus does not produce.
        {"key": "wave_invalid_a",
         "value": _wave.get("invalid_A", UNAVAILABLE),
         "what": "share of condition-A sheets on the main wave that fail validity -- the "
                 "reason §2 measures the order floor under D instead",
         "phrase": "%s%% of A runs are invalid"},
        {"key": "wave_invalid_d",
         "value": _wave.get("invalid_D", UNAVAILABLE),
         "what": "the same for condition D",
         "phrase": "against %s%% of D's"},
        {"key": "wave_partial_sheets",
         "value": _wave.get("partial_sheets", UNAVAILABLE),
         "what": "sheets on the main wave answering some items but not all; each is dropped "
                 "WHOLE by run_battery rather than analysed on the part it answered",
         "phrase": "In it, %d"},
        {"key": "wave_partial_models",
         "value": _wave.get("partial_models", UNAVAILABLE),
         "what": "distinct models contributing those partial sheets",
         "phrase": "items answered, from %d models"},
        {"key": "out_of_panel_records",
         # Thousands-separated in the VALUE, not the phrase -- the same convention as
         # `corpus_runs` above, and for the same reason: the check is a literal grep and the
         # sentence writes "5,647".
         "value": "{:,}".format(_oop) if _oop else UNAVAILABLE,
         "what": "records the refusal panel sets aside, against the 3,897 it keeps -- the "
                 "ratio a reader is entitled to before quoting any rate off the table",
         "phrase": "sets aside %s records"},
        # THE ESTIMATOR CALIBRATION, registered 2026-09-23 after four days of a stale figure
        # heading the paper with every gate green. See CALIBRATION_CACHE above.
        {"key": "calib_boot_fpr",
         "value": None if not _calib else round(100 * _calib["sheet_bootstrap"]["rate"], 1),
         "what": "false-positive rate of the SHEET BOOTSTRAP, measured on split halves of "
                 "real cells -- the estimator §1's per-model counts are computed with",
         "phrase": "rejects **%s%%** of true nulls"},
        {"key": "calib_exact_fpr",
         "value": None if not _calib else round(100 * _calib["exact_permutation"]["rate"], 1),
         "what": "the same, for the exact permutation test used as the sensitivity check",
         "phrase": "the exact test %s%%"},
        {"key": "calib_cells",
         "value": None if not _calib else _calib["cells_eligible"],
         "what": "cells with enough sheets to split in half; the calibration's population",
         "phrase": "splits of %s cells"},
        {"key": "evb_boot_survive",
         "value": None if not _evb else _evb["boot_survive"],
         "what": "contrasts surviving BH-FDR under the bootstrap, of the compared family",
         "phrase": "bootstrap returns %s surviving BH-FDR"},
        {"key": "evb_exact_survive",
         "value": None if not _evb else _evb["exact_survive"],
         "what": "the same under the exact test",
         "phrase": "exact permutation test returns **%s**"},
        {"key": "evb_lost",
         "value": None if not _evb else _evb["lost"],
         "what": "contrasts the bootstrap calls significant and the exact test does not; "
                 "none are gained in the other direction",
         "phrase": "%s lost"},
        {"key": "evb_an_lost",
         "value": None if not _evb else _evb["an_lost"],
         "what": "of those, A-N contrasts -- the lead's own comparison",
         "phrase": "%s A−N contrasts are among them"},
        {"key": "placebo_panel",
         "value": None if not placebo else placebo["panel"],
         "what": "models with BOTH a placebo and a baseline arm -- the panel this rests on",
         "phrase": "%s models"},
        {"key": "placebo_moves_models",
         "value": None if not placebo else placebo["moves"],
         "what": "models whose position moves significantly under a CONTENT-FREE placebo, "
                 "per model against its own pair-clustered interval after BH-FDR",
         "phrase": "moves position on %s of them"},
        {"key": "placebo_both_move",
         "value": None if not placebo else placebo["both_move"],
         "what": "of those, models the instruction ALSO moves",
         "phrase": "%s move under both"},
        {"key": "placebo_only",
         "value": None if not placebo else placebo["placebo_only"],
         "what": "models the placebo moves and the instruction does NOT -- the control arm "
                 "outperforming the manipulation",
         "phrase": "on %s the placebo is the only thing that moves it"},
        # THE NUMBER THAT MAKES THE FINDING INVISIBLE, gated so no draft can quote it alone.
        {"key": "placebo_median_effect",
         "value": None if not placebo else placebo["median_effect"],
         "what": "median placebo effect across the panel -- near zero, and near zero is what "
                 "a summary statistic reports when real effects cancel",
         "phrase": "a median of %s"},
        {"key": "placebo_sig_positive",
         "value": None if not placebo else placebo["sig_positive"],
         "what": "significant placebo effects pointing POSITIVE",
         "phrase": "%s point one way"},
        {"key": "placebo_sig_negative",
         "value": None if not placebo else placebo["sig_negative"],
         "what": "significant placebo effects pointing NEGATIVE -- these are what the median "
                 "cancels against",
         "phrase": "%s the other"},
        {"key": "audit_external",
         "value": audit["external"],
         "what": "external studies in the controls audit, excluding ours",
         # THE CONTROL COUNT WAS A LITERAL HERE ("thirteen controls") AND WENT STALE THE DAY A
         # FOURTEENTH CONTROL WAS ADDED -- a gate failing on its own wording rather than the
         # paper's. The first repair substituted the live count INTO the template, which
         # `test_no_phrase_template_hides_a_second_number` rejected and was right to: a value
         # baked into a phrase looks checked and is not. It is its own claim key now.
         "phrase": "%d studies"},
        {"key": "audit_controls",
         "value": audit["controls"],
         "what": "controls in the audit matrix -- the columns every study is scored on",
         "phrase": "%d controls"},
        {"key": "audit_full_text",
         "value": audit["full_text"],
         "what": "of those, read in full rather than retrieved as a summary",
         # "12 of the twelve read in full" is what the plain template produced once the last
         # three were re-read on 2026-09-11, and it is clumsy enough that a writer would
         # quietly reword it -- which is how a gated sentence stops being gated.
         # "all %d read in full" is the prose a person would actually write AND still carries
         # the digit. A first attempt dropped the number entirely ("all twelve read in full"),
         # which reads better and silently stops the gate checking the count -- the phrase is
         # matched literally, so a phrase without the value verifies nothing.
         # "the twelve" was a literal here too and broke at fourteen. The denominator is NOT
         # substituted back in -- that was the same defect in the other direction. It is
         # carried by `audit_external` in the adjacent sentence, where it is checked.
         "phrase": ("all %d read in full" if audit["full_text"] == audit["external"]
                    else "%d of them read in full")},
        {"key": "audit_yes_nuisance_magnitude",
         "value": audit["yes_nuisance_magnitude"],
         "what": "external studies reporting a nuisance magnitude outright",
         "phrase": "%d studies report a nuisance magnitude"},
        {"key": "audit_partial_nuisance_magnitude",
         "value": audit["partial_nuisance_magnitude"],
         "what": "external studies reporting something adjacent to a nuisance magnitude",
         "phrase": "%d more report something adjacent"},
        {"key": "audit_pi_no_same_version_dist",
         "value": audit["pi_no_same_version_dist"],
         "what": "political-instrument studies scored `no` on the same-version distribution",
         "phrase": "%d are scored `no` on it"},
        {"key": "audit_political_instrument",
         "value": audit["political_instrument"],
         "what": "external studies that actually administer a political instrument",
         "phrase": "%d political-instrument studies"},
        # §1b's OWN DENOMINATORS. The section argues from them and stated them wrongly.
        # THE REPRODUCTION SECTION'S OWN FIGURES. It explains why the classifier audit is
        # trustworthy and quoted a corpus three collections old while doing it.
        {"key": "audit_rows",
         # Rendered with the thousands separator the prose uses. A phrase carrying a newline
         # never matches -- the surface is flattened before comparison -- so the anchor stops
         # at the line break rather than spanning it.
         "value": (UNAVAILABLE if audit_labels.get("rows") is None
                   else "{:,}".format(audit_labels["rows"])),
         "what": "rows the classifier mirror-check compares, both implementations",
         "phrase": "over all %s"},
        {"key": "audit_superseded",
         "value": audit_labels.get("superseded", UNAVAILABLE),
         "what": "audited rows carrying a superseded classifier label",
         "phrase": "the %d rows carrying a"},
        # §4'S JUDGE PARAGRAPH, gated against the PUBLISHED corpus. `surface_numbers()`
        # already gates these three for the website; the paper needed its own registration
        # because `--check` reads the paper and `--check-website` does not, and §4 had been
        # quoting the WORKING tree: 4,668 records against a published 3,809, a spread of 0.29
        # against 0.3054, and twelve stale cells in the fan-out table beneath it. The paper
        # ships inside the mirror, so a figure its own released corpus cannot produce is a
        # claim about a machine nobody else has -- which is the same rule
        # `_mirror_judge_records` states for the website, applied to the document.
        {"key": "paper_judge_records",
         "value": (None if _mirror_judge_records() is None
                   else "{:,}".format(_mirror_judge_records())),
         "what": "scored records carrying a per-judge breakdown, in the PUBLISHED corpus",
         "phrase": "over the %s scored records carrying"},
        {"key": "paper_judge_spread", "value": _judge_spread(),
         "what": "the panel's internal spread, as §4 states it",
         "phrase": "internal spread is **%.4f points**"},
        {"key": "paper_judge_top", "value": _mirror_judge_lean_extremes()[0],
         "what": "mean deviation of the most institution-skeptical judge, as §4 states it",
         "phrase": "institution-skeptical at +%.3f"},
        # §3b'S BIMODALITY. item_gradient.py said these were gated here; they were not.
        {"key": "gradient_defender_min",
         "value": grad.get("defender_min", UNAVAILABLE),
         "what": "lowest agreement rate among defender-framed items",
         "phrase": "defender-framed items run %.1f–"},
        {"key": "gradient_defender_max",
         "value": grad.get("defender_max", UNAVAILABLE),
         "what": "highest agreement rate among defender-framed items -- the bank's ceiling "
                 "below the contested middle. The paper read 29.8% here until 2026-09-22",
         "phrase": "%.1f%%, critic-framed items"},
        {"key": "gradient_critic_min",
         "value": grad.get("critic_min", UNAVAILABLE),
         "what": "lowest agreement rate among critic-framed items",
         "phrase": "critic-framed items %.1f–"},
        {"key": "gradient_middle",
         "value": grad.get("middle", UNAVAILABLE),
         "what": "items whose agreement falls between 30% and 70%, where a panel would divide",
         "phrase": "%d of the 32 sit in that band"},
        {"key": "astra_balance",
         "value": switch.get("astra_balance", UNAVAILABLE),
         "what": "gpt-6-astra refusals under the balance instruction",
         "phrase": "It declines, **%d times out of"},
        {"key": "astra_balance_runs",
         "value": switch.get("astra_balance_runs", UNAVAILABLE),
         "what": "gpt-6-astra runs under the balance instruction",
         "phrase": "%d**, across three presentation orders"},
        {"key": "astra_pro_balance",
         "value": switch.get("astra_pro_balance", UNAVAILABLE),
         "what": "gpt-6-astra-pro refusals under the balance instruction",
         "phrase": "sibling `gpt-6-astra-pro` declines %d of"},
        {"key": "astra_pro_balance_runs",
         "value": switch.get("astra_pro_balance_runs", UNAVAILABLE),
         "what": "gpt-6-astra-pro runs under the balance instruction",
         "phrase": "of the same %d"},
        {"key": "astra_pair_placebo",
         "value": switch.get("pair_P", UNAVAILABLE),
         "what": "refusals by the two astra models under the content-free instruction",
         "phrase": "Both answer, **%d refusals in"},
        {"key": "astra_pair_placebo_runs",
         "value": switch.get("pair_P_runs", UNAVAILABLE),
         "what": "runs by the two astra models under the content-free instruction",
         "phrase": "refusals in %d**. So does an explicit"},
        {"key": "astra_pair_commit_runs",
         "value": switch.get("pair_D_runs", UNAVAILABLE),
         "what": "runs by the two astra models under the commitment directive",
         "phrase": "refusals in %d runs. So does asking"},
        {"key": "astra_pair_bare_runs",
         "value": switch.get("pair_N_runs", UNAVAILABLE),
         "what": "runs by the two astra models with no system prompt",
         "phrase": "in %d sheets"},
        {"key": "switch_declining_models",
         "value": switch.get("models", UNAVAILABLE),
         "what": "models declining under at least one condition -- the switch table's rows. "
                 "The paper read `Eighteen` here until 2026-09-22",
         "phrase": "**%d models decline under some condition**"},
        {"key": "switch_min_cell",
         "value": switch.get("min", UNAVAILABLE),
         "what": "smallest per-condition run count among the declining models",
         "phrase": "smallest holds %d runs"},
        {"key": "switch_cells_ge11",
         "value": switch.get("ge11", UNAVAILABLE),
         "what": "their per-condition cells holding 11 runs or more",
         "phrase": "and %d of their"},
        {"key": "switch_cells",
         "value": switch.get("cells", UNAVAILABLE),
         "what": "their per-condition cells in total",
         "phrase": "of their %d cells hold"},
        # §1's LEAD, in prose. The table above it is generated and checked; these sentences
        # repeat four of its cells and were checked by nothing.
        {"key": "position_manip_clear",
         "value": pos.get("manip_clear", UNAVAILABLE),
         "what": "pairs where the balance instruction's movement clears the bootstrap and BH",
         "phrase": "Across **%d of"},
        {"key": "position_manip_pairs",
         "value": pos.get("manip_pairs", UNAVAILABLE),
         "what": "pairs answering both the bare and the balance-instruction arm",
         "phrase": "%d pairs** the movement clears"},
        {"key": "position_manip_median",
         "value": pos.get("manip_median", UNAVAILABLE),
         "what": "median |effect| of the balance instruction, position units",
         "phrase": "The median movement is **%.3f**"},
        {"key": "position_order_pct",
         "value": pos.get("order_pct", UNAVAILABLE),
         "what": "percentage of order pairs clearing the same bootstrap and correction",
         "phrase": "The position moves on %d%% of pairs"},
        {"key": "position_order_median",
         "value": pos.get("order_median", UNAVAILABLE),
         "what": "median |effect| of reprinting the same items in a different order",
         "phrase": "with a median of %.3f"},
        {"key": "position_ratio",
         "value": pos.get("ratio", UNAVAILABLE),
         "what": "how many times the instruction's median effect exceeds the order median",
         "phrase": "is **%.1f times** the median produced by"},
        # THE ABSTRACT. It summarises figures stated with their denominators in the body, so
        # each key here anchors on the abstract's own wording rather than the section's. An
        # abstract is the most-quoted part of a paper and was the least-checked part of this
        # one: it did not exist until 2026-09-22, and the first draft of it carried three
        # numbers no gate could see.
        {"key": "abstract_omission_local_asis",
         "value": (omission["local"] or {}).get("asis_partial", UNAVAILABLE),
         "what": "as-is partial sheets, local arm, as the abstract states it",
         # ANCHOR ON ONE LINE. The surface is flattened before comparison, so a phrase carrying
         # a newline never matches -- the same trap that caught `audit_rows` an hour earlier.
         "phrase": "loses %d sheets where the renumbered"},
        {"key": "abstract_omission_local_renum",
         "value": (omission["local"] or {}).get("renum_partial", UNAVAILABLE),
         "what": "renumbered partial sheets, local arm, as the abstract states it",
         "phrase": "renumbered arm loses %d"},
        {"key": "abstract_nemotron_deepinfra",
         "value": (omission["pinned"] or {}).get("nemotron_asis", UNAVAILABLE),
         "what": "nemotron as-is partial sheets on DeepInfra, as the abstract states it",
         "phrase": "the as-is loss runs %d sheets"},
        {"key": "abstract_nemotron_phala",
         "value": (omission["phala"] or {}).get("nemotron_asis", UNAVAILABLE),
         "what": "nemotron as-is partial sheets on Phala, as the abstract states it",
         "phrase": "sheets against %d."},
        {"key": "abstract_order_mde",
         "value": mde("presentation order"),
         "what": "the detection limit, as the abstract states it",
         "phrase": "a minimum detectable effect of %d"},
        # THE EXCLUSION THE PAPER MAKES AND DID NOT STATE. Each denominator is its own key,
        # for the same reason as the omission block below.
        {"key": "unattributable_sheets",
         "value": unattr.get("total", UNAVAILABLE),
         "what": "valid shuffled sheets that cannot be attributed to the propositions they "
                 "answer, and are therefore dropped from every row depending on item identity",
         "phrase": "%d sheets"},
        {"key": "unattributable_examined",
         "value": unattr.get("examined", UNAVAILABLE),
         "what": "valid shuffled sheets examined by the attribution classifier",
         "phrase": "of %d valid shuffled sheets"},
        {"key": "unattributable_models",
         "value": unattr.get("models", UNAVAILABLE),
         "what": "models contributing at least one unattributable sheet",
         "phrase": "across %d models"},
        # THE NUMBERING ARTIFACT. Absent from the paper until 2026-09-21 and present in the
        # collector since 2026-09-18, which is the wrong way round: a fix shipped and the
        # finding that motivated it unpublished.
        # Every denominator is its own key. Baking one into a phrase ("%d of 102 sheets") is
        # the defect `test_no_phrase_template_hides_a_second_number` exists to catch: the
        # second number looks checked and is not.
        {"key": "omission_local_asis_sheets",
         "value": (omission["local"] or {}).get("asis_sheets", UNAVAILABLE),
         "what": "as-is sheets attempted, local arm",
         "phrase": "%d as-is sheets"},
        {"key": "omission_local_asis",
         "value": (omission["local"] or {}).get("asis_partial", UNAVAILABLE),
         "what": "partial sheets in the as-is (non-monotonic numbering) local arm",
         "phrase": "%d come back incomplete"},
        {"key": "omission_local_renum_sheets",
         "value": (omission["local"] or {}).get("renum_sheets", UNAVAILABLE),
         "what": "renumbered sheets attempted, local arm",
         "phrase": "%d renumbered sheets"},
        {"key": "omission_local_renum",
         "value": (omission["local"] or {}).get("renum_partial", UNAVAILABLE),
         "what": "partial sheets in the renumbered local arm",
         "phrase": "the count is %d"},
        {"key": "omission_pinned_asis",
         "value": (omission["pinned"] or {}).get("asis_partial", UNAVAILABLE),
         "what": "partial sheets in the as-is hosted arm, backends pinned",
         "phrase": "%d incomplete of"},
        {"key": "omission_pinned_asis_sheets",
         "value": (omission["pinned"] or {}).get("asis_sheets", UNAVAILABLE),
         "what": "as-is sheets attempted, hosted arm with backends pinned",
         "phrase": "of %d as-is sheets"},
        {"key": "omission_pinned_renum",
         "value": (omission["pinned"] or {}).get("renum_partial", UNAVAILABLE),
         "what": "partial sheets in the renumbered hosted arm, backends pinned",
         "phrase": "against %d of"},
        {"key": "omission_pinned_renum_sheets",
         "value": (omission["pinned"] or {}).get("renum_sheets", UNAVAILABLE),
         "what": "renumbered sheets attempted, hosted arm with backends pinned",
         "phrase": "%d renumbered, p ="},
        # THE SERVING PATH. Same model, same protocol, two backends -- the contrast that
        # decides whether the hosted finding is about numbering or about routing.
        # THE DENOMINATOR IS ITS OWN KEY, and it is ONE key because both backends served the
        # same number of as-is sheets. Writing "%d of 23" baked a literal that nothing
        # checked -- `test_no_phrase_template_hides_a_second_number` caught it, correctly,
        # in claims added to fix exactly that class of defect elsewhere.
        {"key": "omission_nemotron_sheets",
         "value": ((omission["pinned"] or {}).get("nemotron_asis_sheets", UNAVAILABLE)
                   if ((omission["pinned"] or {}).get("nemotron_asis_sheets")
                       == (omission["phala"] or {}).get("nemotron_asis_sheets"))
                   else UNAVAILABLE),
         "what": "as-is sheets this model contributed on EACH backend (equal, or the "
                 "sentence below cannot be written as one denominator)",
         "phrase": "served %d as-is sheets"},
        {"key": "omission_nemotron_deepinfra",
         "value": (omission["pinned"] or {}).get("nemotron_asis", UNAVAILABLE),
         "what": "nemotron as-is partial sheets on DeepInfra",
         "phrase": "On DeepInfra %d come back incomplete"},
        {"key": "omission_nemotron_phala",
         "value": (omission["phala"] or {}).get("nemotron_asis", UNAVAILABLE),
         "what": "nemotron as-is partial sheets on Phala, same protocol",
         "phrase": "on Phala, %d."},
        {"key": "omission_hosted_pooled_asis",
         "value": (omission.get("hosted_pooled") or {}).get("asis_partial", UNAVAILABLE),
         "what": "partial sheets in the as-is arm across BOTH hosted backends",
         "phrase": "as-is arm loses %d sheets"},
        {"key": "omission_hosted_pooled_asis_sheets",
         "value": (omission.get("hosted_pooled") or {}).get("asis_sheets", UNAVAILABLE),
         "what": "as-is sheets attempted across BOTH hosted backends",
         "phrase": "%d collected, and the renumbered"},
        {"key": "omission_hosted_pooled_renum",
         "value": (omission.get("hosted_pooled") or {}).get("renum_partial", UNAVAILABLE),
         "what": "partial sheets in the renumbered arm across BOTH hosted backends",
         "phrase": "renumbered arm loses %d sheets"},
        {"key": "omission_hosted_pooled_renum_sheets",
         "value": (omission.get("hosted_pooled") or {}).get("renum_sheets", UNAVAILABLE),
         "what": "renumbered sheets attempted across BOTH hosted backends",
         "phrase": "%d collected there"},
    ]
    # SAY WHY, not just that. Every placebo row above reads `None if not placebo else ...`, so
    # a refused cache made seven numbers uncomputable and the report said only "no value
    # produced in this tree" -- while `placebo_error` held the exact reason, naming the run,
    # the record counts, the estimator and the rebuild command. A check that knows what drifted
    # and prints a shrug is the one somebody stops reading.
    if placebo_error:
        for r in rows:
            if r["key"].startswith("placebo_"):
                r["why_unavailable"] = placebo_error
    return _resolve(rows)


#: W3.2 -- the SAME numbers, on the OTHER surfaces that state them.
#:
#: The paper is not the only place these quantities appear in prose. The public research page
#: and the release repository's README both narrate them, in their own words, and neither is
#: regenerated from `runs/`. That is three hand-typed copies of one fact, which is the exact
#: defect this file exists to catch inside the paper -- just spread across repositories, where
#: nobody re-reads them together.
#:
#: It found one on its first run. The website says "across 1,657 runs, 155 models and sixteen
#: vendor keys"; the release README says "across 1,692 runs, 155 models and sixteen vendor
#: keys" -- the same sentence, a different corpus size, because the release copy predates the
#: exclusion the paper applies (REFUSAL_EXCLUDE, the google-orderfloor run dir).
#:
#: Keys absent from a surface are simply not checked there: a page is allowed to omit a number.
#: What it may not do is state a DIFFERENT one in the same words.
#: Surfaces are located by SEARCHING rather than by counting directory levels up from STUDY.
#:
#: This file lives in two trees -- the private study and the public mirror -- and
#: `check_no_fork.py` requires those copies to be byte-identical, because a fork is how a fix
#: lands on one side only (it caught this very edit). A hardcoded `dirname(dirname(STUDY))`
#: resolves to different places in the two trees, so it would either break in the mirror or
#: force a fork. Candidate paths, with a missing surface simply not checked, work in both.
def _find_surface(*relative_parts):
    """Locate a surface that lives in a SIBLING tree, falling back to this one.

    THE WALK LOOKS FOR A DIRECTORY BY NAME, and the public mirror's name is only its name on
    this machine. `git clone <url> <dir>` and an unpacked Zenodo archive both land it under
    something else, and then `_find_surface("bias-study-release", "LESSONS.md")` walked six
    levels, found no directory of that name, and returned a path that does not exist -- so
    `LESSONS.md` and `README.md`, sitting in the reader's own checkout, were reported as
    surfaces "not in this tree" and went unchecked. Measured 2026-09-23 in a copy of the
    mirror placed outside the workspace: 2 surfaces resolved where this tree resolves 10.

    So when the named sibling is not found, try the same path WITHIN this tree before giving
    up. If we are the mirror, `bias-study-release/LESSONS.md` is just `LESSONS.md` from here.
    """
    here = os.path.abspath(STUDY)
    for _ in range(6):
        here = os.path.dirname(here)
        if not here:
            break
        candidate = os.path.join(here, *relative_parts)
        if os.path.exists(candidate):
            return candidate
    if len(relative_parts) > 1:
        local = os.path.join(STUDY, *relative_parts[1:])
        if os.path.exists(local):
            return local
    return os.path.join(STUDY, *relative_parts)      # non-existent; reported, not crashed


SURFACES = {
    # THE BOOKS WERE THE LEAST-GATED SURFACE IN THE PROJECT, which is the same
    # thing the public README was before 2026-09-07 and the same fix. A printed
    # number cannot be corrected after the fact, so it is the surface where drift
    # costs most, and it was the one nothing checked.
    #
    # AUDIT-2026-09-14-book-numbers.md verified every figure in this chapter
    # against the corpus. The four phrases below are the ones that moved and are
    # mechanically checkable; they are expected to FAIL until the correction pass,
    # and that failure is the point.
    "book-ratchet-ch22": {
        "path": _find_surface("books", "the-ratchet", "chapters",
                              "22-the-cat-or-the-dog.md"),
        "phrases": {
            # "thirty-six frontier AI models" -- 36 sums the per-run counts and
            # double-counts z-ai/glm-4.7, which appears in two of the four runs.
            # %s, not %d: the spelled alternative is a string, and %d rejects one.
            "may_models_distinct": "to %s frontier AI models",
            # "across nineteen hundred scored responses" sits directly above a
            # table whose cells total 780.
            "may_records_main": "Across %s scored responses",
            # "seven times the rhetorical hedge ratio" -- 7.2x is score-3 against
            # score-1 ALONE on 19 records. The sentence says "a 1 or a 5", which
            # is the pooled figure. Stored in tenths.
            "hedge_multiple_pooled": "carried %s times the rhetorical hedge ratio",
            # "five open-weight models" -- one clears the resample noise floor.
            # The noun is left out of the template so the count can go singular
            # without the gate demanding "one open-weight models".
            "ablation_families_confirmed": "We did the abliteration. %s open-weight",
        },
    },
    # THE TALK. What gets said to a room is a shipping surface with no errata page, and the
    # previous TALK.md was written end to end on the retired 62-item questionnaire -- "16 items
    # of 62", a demo model that is now a total refuser -- while every gate stayed green,
    # because no gate read it. Rebuilt 2026-09-22 on the battery; every phrase below is a
    # sentence in the talk, so `--check-talk` fails the morning a slide goes stale, which is
    # the promise the talk's own pre-flight block makes.
    "talk": {
        "path": os.path.join(STUDY, "TALK.md"),
        "phrases": {
            # §1, the demo and the switch
            "demo_balance": "declines %(demo_balance)d of %(demo_balance_runs)d under the "
                            "balance instruction",
            "demo_placebo": "%(demo_placebo)d refusals in %(demo_placebo_runs)d runs under "
                            "the placebo",
            "demo_bare": "declines the bare question %(demo_bare)d of %(demo_bare_runs)d",
            "demo_commit": "under the commitment directive it produces %(demo_commit)d "
                           "refusals in %(demo_commit_runs)d runs",
            "astra_balance": "%(astra_balance)d of %(astra_balance_runs)d under the balance "
                             "instruction",
            "astra_pair_placebo": "%(astra_pair_placebo)d refusals in "
                                  "%(astra_pair_placebo_runs)d placebo runs",
            "switch_declining_models": "%(switch_declining_models)d models decline under "
                                       "some condition",
            "balance_only": "%(balance_only)d of them decline the balance instruction and "
                            "never the commitment one",
            # THE FOUR `arms_*` PHRASES ARE DELIBERATELY NOT HERE. They were registered on
            # this surface when it was added on 2026-09-22 and the rebuilt talk states none
            # of them: §1 reaches the same fact through the switch table
            # (`switch_declining_models`, `balance_only`) rather than through the panel-level
            # arms paragraph. A gate that demands a surface say something it does not say is
            # permanently red, and a permanently red gate gets switched off or read past:
            # `check_arm_match.py` sat in the registry with no arguments until 2026-09-17,
            # exited 2 on its own usage message, and the preflight counted that as NOT
            # APPLICABLE -- a gate that had never once run, reported as one that did not
            # need to.
            #
            # They remain gated where they ARE stated: the website, both dispatches and the
            # release README. Dropping them here costs no coverage; verify with
            # `key_numbers.SURFACES` before removing any other phrase this way.
            # §2, the manipulation against the nuisance, and the control arm
            "position_manip_clear": "moves position on %(position_manip_clear)d of "
                                    "%(position_manip_pairs)d pairs with a median of "
                                    "%(position_manip_median).3f",
            "position_order_pct": "moves it on %(position_order_pct)d%% of pairs with a "
                                  "median of %(position_order_median).3f",
            "placebo_moves_models": "moves position on %(placebo_moves_models)d of "
                                    "%(placebo_panel)d",
            # §3, the detection limits
            "order_mde": "%(order_mde)d items of %(instrument_items)d",
            "null_mde": "same-version limit is %(null_mde)d",
            "audit_yes_nuisance_magnitude": "%(audit_yes_nuisance_magnitude)d report a "
                                            "nuisance magnitude",
            # §4, the ledger and the null
            "corrections_entries": "%(corrections_entries)d claims withdrawn or narrowed",
            "null_pairs": "%(null_pairs)d pairs, median %(null_median)d",
            # §5, the audit
            "audit_external": "%(audit_external)d studies, %(audit_full_text)d of them read "
                              "in full",
            "audit_yes_same_version_dist": "%(audit_yes_same_version_dist)d report a "
                                           "same-version null as a distribution",
            # §7, order by model class, and the manipulation for scale
            "order_p90_local": "p90 %(order_p90_local)d on the 2024-generation open-weight "
                               "builds and %(order_p90_frontier)d on the 2026 frontier",
            "order_p90_local_sitting": "one sitting, %(order_p90_local_sitting)d against "
                                       "%(order_p90_frontier_sitting)d",
            "manip_p90_sitting": "manipulation in one sitting sits at p90 "
                                 "%(manip_p90_sitting)d",
            # §8, the numbering artifact
            "omission_local_asis": "%(omission_local_asis)d of %(omission_local_asis_sheets)d "
                                   "local sheets come back incomplete against "
                                   "%(omission_local_renum)d of "
                                   "%(omission_local_renum_sheets)d renumbered",
            # questions
            "corpus_runs": "%(corpus_runs)s runs and %(corpus_models)d models",
            "gradient_middle": "%(gradient_middle)d items of %(instrument_items)d sit in the "
                               "band",
            "critic_agree_normative": "agree %(critic_agree_normative).1f%% of the time",
        },
    },
    "website": {
        "path": _find_surface("website", "content", "research", "ai-bias-audit.md"),
        "phrases": {
            "corpus_runs": "across %s runs",
            "corpus_models": "runs, %d models",
            # The page's own wording, bold markers and line wrap included -- the phrase is a
            # literal grep, so it has to be the sentence as written rather than as summarised.
            # "of 62" WAS BAKED INTO THIS TEMPLATE -- the retired external questionnaire,
            # inside the gate that exists to stop the website quoting retired figures. It
            # would have held the page to a denominator the instrument has not had since
            # 2026-09-16. The live count is its own claim key, checked in the same sentence.
            "order_mde": "of %(order_mde)d items of %(instrument_items)d** at 80%% power",
            "arms_models": "Across the %d models measured under both arms",
            "arms_nodir_refusals": "%(arms_nodir_refusals)d refusals in %(arms_nodir_runs)d runs",
            "arms_nodir_runs": "%(arms_nodir_refusals)d refusals in %(arms_nodir_runs)d runs",
            # Gated on the public page too, for the same reason it is gated in the paper: this
            # page carried "not one of them declines even once ... 347 runs, zero refusals"
            # until 2026-09-04, and the zero was the only figure on it that was typed rather
            # than generated.
            "arms_silenced": "**%d of them stop**",
            "arms_dir_only": "**%d other models decline only under a firm instruction**",
            # Conclusion five. Gated because it is the most quotable paragraph on the page,
            # and because its own argument is that a typed number goes stale.
            "replicate_med": "A median of %d answers move",
            "replicate_max": "and up to %d.**",
            "order_max_all": "Reorder the questions and up to %d move",
            # The floors table on the research page, cell by cell.
            # THE ROW NOW CARRIES ITS PAIR COUNT. A floor with no n beside it cannot be read
            # -- the same-version row rests on 24 pairs and the replicate row on 6,240, and a
            # reader comparing their maxima without that is comparing two different kinds of
            # claim. The anchors follow the table rather than the table following the anchors.
            "order_max_pooled":
                "| presentation order of the items, pooled | %(order_pairs)d | "
                "%(order_med_pooled)d | %(order_p90_pooled)d | **%(order_max_pooled)d** |",
            "null_max_sideflips":
                "| two models of the same version (size, tier, snapshot or mode) | "
                "%(null_pairs)d | %(null_median)d | %(null_p90_sideflips)d | "
                "**%(null_max_sideflips)d** |",
            "same_version_max": "two variants of one release and up to %d move",
            "manipulation_p90": "moves %d at its 90th percentile",
            # The audit block, added 2026-09-04. These were prose ("two columns come back
            # nearly empty") while the counts sat in the JSON, on a page whose own argument is
            # that a typed number rots -- and the page still said "ten studies" after the
            # paper had been corrected to twelve.
            # A NUMERAL, not a spelled-out word. The page said "ten studies" in prose long
            # after the paper was corrected to twelve, and a spelled word cannot be gated by
            # a numeric grep -- which is precisely how it survived.
            # Every phrase here carries its ROW LABEL. A bare "| **%d of 12** |" matched three
            # different rows of the same table, so the gate reported the same-version row's
            # figure as drift against the raw-data row's -- a guard that cannot tell two
            # numbers apart is not guarding either.
            "audit_external": "Of the %d external studies",
            "audit_controls": "scored against %d controls",
            # The denominators are GENERATED now, not the literal 12. They were frozen at 12
            # while every count above them came from the JSON, so when three papers were read
            # end to end on 2026-09-12 and two cells became `n/a`, the true row was "0 of 10"
            # and the gate demanded "0 of 12" -- the gate holding the page to a number the
            # data no longer supported. A hardcoded denominator is a typed number wearing a
            # generated number's coat.
            "audit_yes_same_version_dist":
                "the null a drift claim needs | **%(audit_yes_same_version_dist)d of "
                "%(audit_applicable_same_version_dist)d** (%(audit_na_same_version_dist)d n/a) |",
            # NO LITERAL NEWLINE IN A PHRASE. Surface text is unwrapped before matching now
            # -- a gated phrase that straddled a hand-wrapped line break was invisible, and
            # that cost four statements on the mirror README. So a template carrying its own
            # line break can never match anything. Where the author wraps is the author's
            # business; the phrase is one line.
            "audit_no_same_version_dist":
                "**%(audit_no_same_version_dist)d of the %(audit_external)d external "
                "studies are scored `no` on it",
            "audit_yes_quantisation":
                "controls for quantisation | **%(audit_yes_quantisation)d of "
                "%(audit_resolved_quantisation)d** fully, %(audit_partial_quantisation)d "
                "partial (%(audit_na_quantisation)d n/a, %(audit_unknown_quantisation)d "
                "unresolved) |",
            "audit_yes_reported_mde":
                "minimum detectable effect at all | %(audit_yes_reported_mde)d of "
                "%(audit_external)d",
            "audit_no_reported_mde":
                "of %(audit_external)d (**%(audit_no_reported_mde)d say no**)",
            "audit_yes_open_raw":
                "publishes its raw data** | **%(audit_yes_open_raw)d of "
                "%(audit_external)d** |",
            "audit_yes_forcing":
                "discloses its forcing prompt** | %(audit_yes_forcing)d of %(audit_external)d",
            "audit_ours_pass_comparable":
                "passes %(audit_ours_pass_comparable)d of the %(audit_comparable_controls)d "
                "controls anyone else was scored on",
            "audit_ours_pass": "passes %(audit_ours_pass)d of all %(audit_controls)d",
        },
    },
    # THE DISPATCH, added 2026-09-05, and the reason is the whole argument for this file.
    #
    # `ai-bias-audit.md` was gated and correct. This dispatch says the same things in the same
    # numbers and was NOT gated, so on 2026-09-05 it still carried "not one refusal in 347 runs
    # with one. Eight models refuse without a directive. None refuses with one" -- the exact
    # sentence the audit page had been corrected out of on 2026-09-04, plus "roughly 1,600 runs
    # across 155 models" and a reordering max of 24 where the floor table measures 22.
    #
    # One page gated and its twin ungated is not half-protected; it is a page that is right and
    # a page that is wrong, published together, under the same argument.
    "dispatch-gemma": {
        "path": _find_surface("website", "content", "dispatches", "gemma-delta.md"),
        "phrases": {
            "corpus_runs": "%(corpus_runs)s runs across %(corpus_models)d models",
            "corpus_models": "runs across %d models",
            "arms_models": "Across the %d models measured under both arms",
            "arms_nodir_refusals": "%(arms_nodir_refusals)d refusals in %(arms_nodir_runs)d runs",
            "arms_nodir_runs": "%(arms_nodir_refusals)d refusals in %(arms_nodir_runs)d runs",
            "arms_dir_refusals": "against %(arms_dir_refusals)d refusals in %(arms_dir_runs)d runs",
            "arms_dir_runs": "against %(arms_dir_refusals)d refusals in %(arms_dir_runs)d runs",
            "arms_silenced": "%d of them stop",
            "order_max_all": "moves up to %d answers",
        },
    },
    #: Same drift, same day, same numbers -- two dispatches saying what the audit page says,
    #: neither of them gated, both a correction behind it.
    "dispatch-mask": {
        "path": _find_surface("website", "content", "dispatches", "alignment-mask.md"),
        "phrases": {
            "corpus_runs": "across %(corpus_runs)s runs and %(corpus_models)d models",
            "corpus_models": "runs and %d models",
            "arms_models": "Across the %d models measured under both arms",
            "arms_nodir_refusals": "%(arms_nodir_refusals)d refusals in %(arms_nodir_runs)d runs",
            "arms_nodir_runs": "%(arms_nodir_refusals)d refusals in %(arms_nodir_runs)d runs",
            "arms_dir_refusals": "against %(arms_dir_refusals)d refusals in %(arms_dir_runs)d runs",
            "arms_dir_runs": "against %(arms_dir_refusals)d refusals in %(arms_dir_runs)d runs",
            "arms_silenced": "%d of them stop",
            "order_max_all": "moves up to %d answers",
            # "median of five" WAS A LITERAL, and a retired one: the same-version median is
            # 1 on the battery and was 5 on the 62-item questionnaire. The template held a
            # figure from the old instrument while checking the max against the new corpus,
            # so a correct sentence could not satisfy it. The median is its own claim key.
            "same_version_max": "a median of %(null_median)d and up to %(same_version_max)d",
        },
    },
    # THE CORRECTED DISPATCH AND THE DISCOVERY PAGE, added 2026-09-12, for the reason stated
    # above dispatch-gemma and proved again since: deception-delta.md was publishing three
    # per-model deltas that its own sibling had withdrawn four days earlier, because the sibling
    # was gated and it was not. One page gated and its twin ungated is not half-protected.
    #
    # These two carry the JUDGE-LAYER numbers, which had no gate at all until now -- the panel
    # spread, its denominator and the empty-response counts were typed on every surface that
    # used them, and the denominator had already gone stale once.
    "dispatch-delta": {
        "path": _find_surface("website", "content", "dispatches", "deception-delta.md"),
        "phrases": {
            "judge_records": "Over %s scored records",
            "judge_lean_top": "from +%.3f (Gemini 2.5 Flash",
            "judge_lean_bottom": "to %s (DeepSeek v3.2",
        },
    },
    #: The barometer's own demo page (2026-09-07). Every figure in its layout is rendered from
    #: static/tech/barometer/barometer.json, which tools/gen-barometer.py reads through build()
    #: and floors() -- so the layout cannot drift. The PROSE above the layout types three numbers
    #: (panel size, the two MDEs), and those are gated here like every other typed copy.
    "website-barometer": {
        "path": _find_surface("website", "content", "tech", "barometer.md"),
        "phrases": {
            "wave_panel_size": "A frozen panel of %d models answers",
            # THE PAGE NO LONGER CLAIMS THE FLOOR "RESOLVES" ANYTHING. "Resolves N items"
            # states an achieved detection limit; the quantity is a hypothetical shift under
            # a clipped model, so the page now says "hypothetical variant shift is N items"
            # and the gate follows it. Leaving the old phrase here would have failed the gate
            # against the corrected page and invited someone to restore the wrong sentence to
            # make it green.
            "null_mde": "hypothetical variant shift is %d items",
            "order_mde": "hypothetical order shift is %d.",
        },
    },
    # VERSIONING.md was never gated, and it drifted exactly where you would expect a file
    # about release discipline to drift: it named a tag `release-2026-09` that was never
    # created, and said CORRECTIONS.md held "seven entries" for as long as it held fourteen.
    # It is checked by --check-release along with the README.
    "versioning": {
        "path": os.path.join(STUDY, "VERSIONING.md"),
        "phrases": {
            "corrections_entries": "**%d entries**",
        },
    },
    # THE DOCUMENT THAT SAYS WHY THE OBJECTIONS FAIL, which is a reviewer's first
    # stop and was the last surface any retraction reached.
    #
    # ADVERSARIAL-REVIEW.md answered seven objections USING claims this study
    # later withdrew -- the abliteration Jaccard as proof of a text rewrite, and
    # cross-method judge agreement as proof of no judge lean. It was last edited
    # 2026-05-30 and carried no banner, so from 2026-09-13 it stood as the reason
    # an objection was closed while FINDINGS.md had already reopened it.
    #
    # It gates NO numbers on purpose: every figure in it is quoted from a result
    # document that has its own gate, and duplicating those here would be the
    # second copy this file exists to prevent. What it gets is the RETRACTED
    # scan, which runs per surface -- so a withdrawn claim cannot stand in the
    # file whose whole job is saying which claims survived.
    "adversarial_review": {
        "path": os.path.join(STUDY, "ADVERSARIAL-REVIEW.md"),
        "phrases": {},
    },
    # THE MIRROR'S LESSONS FILE, UNGATED UNTIL 2026-09-22 AND PUBLIC THE WHOLE TIME.
    #
    # It carries a section headed "Drift did not replicate at scale" -- published null 5,
    # withdrawn 2026-09-18 -- and it carries it at BOTH `origin/main` and `main`, so the
    # withdrawal never reached it in either the pushed or the unpushed tree. No gate read
    # the file, so nothing said so. It states no numbers of its own, which is why it was
    # never added as a numeric surface; a retraction scan does not care about numbers.
    "lessons": {
        "path": _find_surface("bias-study-release", "LESSONS.md"),
        "phrases": {},
    },
    "release": {
        "path": _find_surface("bias-study-release", "README.md"),
        # THIS SURFACE GATED TWO PHRASES WHILE THE WEBSITE GATED FIFTEEN, AND IT SHOWED.
        #
        # Review 2026-09-07 read the README against runs/ and found seven hand-typed numbers
        # stale in one paragraph -- 36 models where there were 42, eight decliners where there
        # were 14, "39 refusals in 499 runs" against 148 in 1076 -- plus a same-version p90 of
        # 12 stated 19 lines under a generated table printing 11, and a detection limit given
        # as 16 where power.py computes 13.
        #
        # Every one of those numbers was ALREADY gated on the website surface. The public
        # mirror, the artifact whose entire purpose is that a stranger can check the claims,
        # was the least-guarded surface in the project. The paragraph even asserted its own
        # figures were generated, which is what stopped anyone checking them.
        #
        # So: the same phrase set, on the repository that matters most.
        "phrases": {
            "corpus_runs": "across %s runs",
            "corpus_models": "runs, %d models",
            # Four decimals, deliberately. At two this number reads 0.29 against a smallest
            # unbeaten effect of 0.30, and "larger than two of them" survived five documents
            # because nobody could see the gap.
            "judge_spread": "our judges spanned %.4f points",
            # HISTORICAL pair: the mirror's README documents the rung-2 result its
            # own repository can reproduce. Gating this on the default pair made
            # the same check compute 8 in the working tree and 6 here.
            "pipeline_contrasts_historical": "all %d intervals span zero",
            "withheld_records": "%d run records had their",
            "arms_models": "Across %d models measured under both arms",
            "arms_declining": "arms, %d decline all",
            "arms_nodir_refusals": "there are %(arms_nodir_refusals)d refusals in %(arms_nodir_runs)d runs",
            "arms_nodir_runs": "there are %(arms_nodir_refusals)d refusals in %(arms_nodir_runs)d runs",
            "arms_silenced": "**%d of them stop**",
            "arms_dir_only": "**%d other models decline only under a firm instruction**",
            "arms_dir_refusals": "%d of those runs are refusals",
            "arms_dir_runs": "against %d runs where it carries one",
            "order_mde": "minimum detectable effect at **%d items",
            "null_mde": "and **%d** against the same-version floor",
            "null_p90": "differ by **p90 %d**",
            "null_pairs_prose": "over %d pairs",
            # THE COUNT THE README STATED FIVE DIFFERENT WAYS. Gated 2026-09-15
            # after an audit found "**18** claims", "Fourteen claims", "Fourteen
            # claims", "15 entries" and "14 claims" in one file -- and a reader
            # who followed the link from the 15 counted 23. Only the VERSIONING.md
            # copy was gated, so `--check-release` passed over all five.
            #
            # The same twin problem as the judge spread: a number is gated on one
            # surface and its prose restatements are not. All five now use this
            # phrase, so one key holds every copy.
            "corrections_entries": "corrected **%d** claims of its own",
        },
    },
}


#: Numbers a SURFACE states that the paper does not. Same guard, different text: the public
#: page reports the audit's control gaps and our own row, which the paper covers in a generated
#: table rather than in a sentence, so there is no paper phrase to grep. Keyed the same way and
#: checked the same way -- the point is that no hand-typed number on any surface is unguarded.
#: Floor rows this checkout could not compute, filled in by surface_numbers() and reported by
#: the gate. A set rather than a flag because the caller has to NAME them: "3 numbers were not
#: verifiable here" is a usable sentence, "some checks were skipped" is not.
MISSING_FLOORS = set()


#: The four runs WRITEUP-2026-05-26 names as the main judged study. Book prose
#: quotes counts pooled across exactly these.
MAY_MAIN_RUNS = ("2026-05-25-full", "2026-05-26-cn-expansion",
                 "2026-05-26-augmentation", "2026-05-26-timeseries")


def _may_runs_present():
    """The main-study run directories, REPAIRED where a repair exists.

    These read the corpus the study actually stands on. The May runs were
    collected at an 800-token cap that severed or emptied about a third of the
    records, so reporting a book number from the original run means reporting it
    from a corpus with three models at zero usable pairs. `canonical_run` returns
    the spliced corpus wherever one has been built.
    """
    from studypaths import run_roots, canonical_run
    out = []
    for root in run_roots():
        for name in MAY_MAIN_RUNS:
            d = root / canonical_run(name) / "scored"
            if d.is_dir():
                out.append(d)
    return out


def _may_scored_rows():
    rows = []
    for d in _may_runs_present():
        for p in sorted(d.glob("*.jsonl")):
            try:
                with p.open(encoding="utf-8") as fh:
                    for line in fh:
                        if line.strip():
                            rows.append(json.loads(line))
            except (OSError, ValueError):
                continue
    return rows


def _may_models_distinct():
    """DISTINCT models across the main study.

    The book says "thirty-six frontier AI models". 36 is the SUM of per-run model
    counts, which double-counts z-ai/glm-4.7 -- it appears in both 2026-05-25-full
    and 2026-05-26-cn-expansion. The distinct count is 35. No script computed
    either figure until now, which is how the wrong one survived in print and in
    two backlog files that disagree with each other about it.
    """
    rows = _may_scored_rows()
    if not rows:
        return None
    return len({r.get("model") for r in rows if r.get("model")})


def _may_records_main():
    """Records in 2026-05-25-full -- the run the hedge-ratio table is computed over.

    The book says "across nineteen hundred scored responses" immediately above a
    table whose cells total this number instead.
    """
    from studypaths import run_roots, canonical_run
    n = 0
    for root in run_roots():
        d = root / canonical_run("2026-05-25-full") / "scored"
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.jsonl")):
            with p.open(encoding="utf-8") as fh:
                n += sum(1 for line in fh if line.strip())
    return n or None


def _hedge_multiple_pooled():
    """Hedge ratio of score-3 answers against scores 1 OR 5 pooled, x10 for a tenth.

    The book says "seven times". 7.2x is score-3 against score-1 ALONE, standing on
    19 records; the book's own phrasing is "a 1 *or* a 5", which is the pooled
    statistic. Returned as tenths so the gated phrase can be an integer.
    """
    rows = _may_scored_rows()
    mid, ends = [], []
    for r in rows:
        s = r.get("score_classifier")
        h = r.get("hedge_ratio")
        if s is None or h is None:
            continue
        if s == 3:
            mid.append(h)
        elif s in (1, 5):
            ends.append(h)
    if not mid or not ends or not sum(ends):
        return None
    # A one-decimal STRING, because that is how a ratio is printed. Returning
    # tenths as an integer made the gated phrase read "37 times", which no
    # corrected chapter would ever contain -- a gate that cannot be satisfied by
    # correct prose is a gate that gets switched off.
    return "%.1f" % ((sum(mid) / len(mid)) / (sum(ends) / len(ends)))


#: Memo for the abliteration count. Computing it runs the whole dissociation
#: report, and surface_numbers() is called by every surface check -- uncached, one
#: `--check-website` ran that report five times and the test suite went from 50
#: seconds to over two minutes. A gate slow enough to skip is a gate that gets
#: skipped.
_ABLATION_CONFIRMED_MEMO = {}


def _ablation_families_confirmed():
    """Model families where the abliteration dissociation is ESTABLISHED.

    The book says "five open-weight models". Three of five sit inside the measured
    same-model resample band (Jaccard 0.303-0.392) or have too few shared cells to
    compute a stance contrast at all, so the rewrite half is not established and a
    stance null against it is uninterpretable.
    """
    if "v" in _ABLATION_CONFIRMED_MEMO:
        return _ABLATION_CONFIRMED_MEMO["v"]
    value = None
    try:
        import abliteration_effect_check as A
        fn = getattr(A, "confirmed_family_count", None)
        if fn is not None:
            value = fn()
    except Exception:
        value = None
    _ABLATION_CONFIRMED_MEMO["v"] = value
    return value


def _pipeline_rung_historical():
    """(n_contrasts, n_excluding_zero) on the n=1 pair, whichever tree runs this.

    `_pipeline_rung()` resolves to the best pair PRESENT, which is correct for an
    estimate and wrong for a GATE: the working study holds the n=5 re-collection
    and the public mirror does not, so the same check computed 8 in one tree and 6
    in the other and the mirror's README could only ever satisfy one of them.

    A surface documents the data its own repository can reproduce. The mirror's
    rung-2 paragraph is about the n=1 pair, so it is gated against the n=1 pair.
    """
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from pipeline_rung import estimate, HISTORICAL_PIPELINE_RUN, HISTORICAL_BASELINE_RUN
        res = estimate(HISTORICAL_PIPELINE_RUN, HISTORICAL_BASELINE_RUN)
        if not res:
            return None, None
        return res["n_contrasts"], sum(1 for c in res["contrasts"] if c["excludes_zero"])
    except Exception:
        return None, None


def _corrections_entries():
    """Numbered entries in CORRECTIONS.md, counted from its own headings.

    LOOKED IN THE WRONG TREE. `CORRECTIONS.md` is a PUBLIC-facing document and lives in the
    mirror; the private tree carries dated `CORRECTIONS-*.md` files instead. This looked only
    under STUDY, returned None from the tree the release check is run FROM, and the key
    rendered as `<uncomputable: %d format: a real number is required, not NoneType>` -- a
    gate key that could never pass as written, for a number that exists and is countable.
    Found 2026-09-21. `_mirror_root()` exists for precisely this.
    """
    candidates = [os.path.join(STUDY, "CORRECTIONS.md")]
    mirror = _mirror_root()
    if mirror:
        candidates.append(os.path.join(mirror, "CORRECTIONS.md"))
    for path in candidates:
        if not os.path.exists(path):
            continue
        text = io.open(path, encoding="utf-8", errors="replace").read()
        return sum(1 for line in text.splitlines() if line.startswith("### "))
    return None


def _mirror_root():
    """The PUBLIC tree, wherever this is run from.

    From the private study that is the `bias-study-release` symlink; run from the mirror there
    is no such path above it and the mirror is simply here. Getting this wrong is not a crash,
    it is a wrong number, which is worse.
    """
    m = _find_surface("bias-study-release")
    return m if os.path.isdir(m) else STUDY


def _withheld_records():
    """Records carrying a `[withheld: ...]` marker in the PUBLIC MIRROR.

    THE MIRROR, DELIBERATELY. Withholding is a property of the published corpus: the private
    tree holds the full response text and withholds nothing, so counting here returns 0 while
    the README correctly says 38. The `release` surface gates the PUBLIC README, so its numbers
    have to come from the tree that README describes.

    Run from the private study this gate used to compare the mirror's prose against the private
    tree's numbers and fail; run from the mirror, `_find_surface` could not resolve the README
    and the gate skipped entirely and printed a pass. Two verdicts for one question, and the
    reassuring one was the one that checked nothing.
    """
    import glob as _glob
    n = 0
    root_dir = _mirror_root()
    for root in ("data", "runs"):
        for p in sorted(_glob.glob(os.path.join(root_dir, root, "**", "*.jsonl"), recursive=True)):
            try:
                for line in io.open(p, encoding="utf-8", errors="replace"):
                    if "[withheld" in line:
                        n += 1
            except OSError:
                continue
    return n


def _judge_spread():
    """Per-judge spread, recomputed from the records this repository actually ships.

    Returns the value rounded to 4dp. Two decimals is what hid the error: 0.29 against a
    0.30 effect reads as "larger" and is not.
    """
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        # THE MIRROR, for the same reason _withheld_records uses it: this number is quoted in
        # the PUBLIC README, so it must be the one a reader of that README can reproduce. The
        # the two trees hold different corpora, so the figures differ by construction; the
        # mirror's are the published ones. Counts move whenever a repair is exported -- see
        # studypaths.scored_corpus_paths(), which drops superseded base runs.
        return _mirror_judge_stats()[3]
    except Exception:
        return None


def _mirror_judge_records():
    """Every scored record in the PUBLIC MIRROR carrying a per-judge breakdown.

    THE MIRROR, DELIBERATELY, and this is the one place in this file where that distinction
    bites. The counts differ between trees and move when a repair lands -- the mirror is
    the scrubbed, published corpus and it is what a reader actually re-runs. A public page must
    state a number the public artifact reproduces. Gating these against the private tree would
    fail a correct page, and "fixing" the page to make the gate green would publish a figure
    nobody outside this machine can get.

    Every other website number in this file happens to be identical in both trees, so the
    distinction never came up until the judge layer was published.
    """
    return _mirror_judge_stats()[0]


def _mirror_judge_lean_extremes():
    """(most institution-skeptical, most deferential) mean deviation in the mirror, 3dp."""
    st = _mirror_judge_stats()
    return st[1], st[2]


_MIRROR_JUDGE_CACHE = []


def _mirror_judge_stats():
    """(n_records, top_lean, bottom_lean) over the mirror, computed once."""
    if _MIRROR_JUDGE_CACHE:
        return _MIRROR_JUDGE_CACHE[0]
    out = (None, None, None, None)
    try:
        import glob as _glob
        import json as _json
        import statistics as _st
        import collections as _c
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from eligibility import is_eligible as _eligible
        # WHICH TREE IS THE MIRROR depends on which tree this is running in. From the private
        # study the mirror is the `bias-study-release` symlink; run FROM the mirror there is no
        # such path above it and the mirror is simply here. Resolving that wrong returned
        # (None, None, None), which made every judge-layer phrase uncomputable in exactly the
        # tree that owns the numbers.
        mirror = _find_surface("bias-study-release")
        if not os.path.isdir(mirror):
            mirror = STUDY
        # THE SAME SELECTION judge_lean uses, including dropping superseded base runs.
        # This globbed both layouts directly and so counted every repaired corpus twice once
        # the mirror held the splices as well as their sources -- 2,967 of 6,651 records were
        # the same records again, and the inflated spread reached a published page.
        #
        # The supersession list is studypaths.REPAIRS, applied to the MIRROR's directories
        # rather than this tree's, because that is the corpus being described. A base run is
        # dropped only where its replacement is actually present.
        from studypaths import REPAIRS as _REPAIRS
        present = set()
        for layout in ("data", "runs"):
            d = os.path.join(mirror, layout)
            if os.path.isdir(d):
                present |= {n for n in os.listdir(d) if os.path.isdir(os.path.join(d, n))}
        superseded = {b for b, rep in _REPAIRS.items() if rep in present and b in present}
        paths = []
        for layout in ("data", "runs"):
            for path in _glob.glob(os.path.join(mirror, layout, "*", "scored", "**", "*.jsonl"),
                                   recursive=True):
                run = os.path.relpath(path, os.path.join(mirror, layout)).split(os.sep)[0]
                if run not in superseded:
                    paths.append(path)
        per = _c.defaultdict(list)
        n = 0
        for path in sorted(paths):
            for line in io.open(path, encoding="utf-8", errors="replace"):
                if not line.strip():
                    continue
                try:
                    r = _json.loads(line)
                except ValueError:
                    continue
                # THE ELIGIBILITY RULE, NOT A SECOND COPY OF IT. This read
                # `score_classifier is not None`, which judge_lean.py:166 names as
                # EXACTLY the filter a scored-blank record passes -- it admits all 466
                # scored-empty records and their 852 per-judge deviations, and they are
                # not distributed evenly across judges (deepseek-v3.2 scored 466 of 466,
                # claude-haiku-4.5 zero), so they move the lean they are averaged into.
                # That made this gate compute the mirror's judge lean over 8,295 records
                # where judge_lean.py computes it over 6,651, and the gate is what the
                # published website phrases are checked against. A forked eligibility
                # rule is DATA-EMPTY-SCORES-002 surviving inside the thing that guards it.
                if not _eligible(r) or not r.get("score_classifier_judges"):
                    continue
                n += 1
                med = r["score_classifier"]
                for j in r["score_classifier_judges"]:
                    if isinstance(j.get("score"), (int, float)):
                        per[j["judge"]].append(j["score"] - med)
        if n and per:
            means = sorted(_st.mean(v) for v in per.values())
            # Fourth element is the UNROUNDED spread. Subtracting 3dp-rounded endpoints loses
            # the last digit -- on the 2026-09-05 corpus it gave 0.2920 against a true 0.2926 --
            # and a margin hidden in a rounding is the exact error ci_clean_effects() documents.
            # The example is historical; the corpus has moved twice since. Do not read it as
            # the current spread.
            out = (n, round(means[-1], 3), round(means[0], 3), round(means[-1] - means[0], 4))
    except Exception:
        out = (None, None, None, None)
    _MIRROR_JUDGE_CACHE.append(out)
    return out


def _scored_empty(scope):
    """Records carrying a score derived from an EMPTY response.

    scope "main" is the primary scored/ corpus; scope "all" is every judge method. This is the
    defect DATA-EMPTY-SCORES-002 exists for -- an empty string scores a 3, three is the balanced
    answer, so every blank became a data point saying the model was perfectly even-handed.
    """
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import eligibility as E
        import glob as _glob
        import json as _json
        from studypaths import run_roots
        n = 0
        for root in run_roots():
            for path in _glob.glob(os.path.join(str(root), "*", "scored*", "**", "*.jsonl"),
                                   recursive=True):
                if scope == "main" and os.path.basename(os.path.dirname(
                        os.path.dirname(path))) not in ("", None):
                    pass
                leaf = path.split(os.sep)
                method = next((x for x in leaf if x.startswith("scored")), "")
                if scope == "main" and method != "scored":
                    continue
                for line in io.open(path, encoding="utf-8", errors="replace"):
                    if not line.strip():
                        continue
                    try:
                        r = _json.loads(line)
                    except ValueError:
                        continue
                    if E.is_scored_empty(r):
                        n += 1
        return n or None
    except Exception:
        return None


def _pipeline_rung():
    """(n_contrasts, n_excluding_zero) for the elicitation rung, from pipeline_rung.py.

    The README published a DIRECTION for this rung with nothing computing it, for four months,
    because analysis.py keys on conditions A/B and the arm runs B-STM / B-Parseltongue /
    B-Layered -- so its records matched no branch and its ANALYSIS.md is empty headings. Gating
    the corrected sentence means the row cannot drift back to a claim the corpus contradicts.
    """
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from pipeline_rung import estimate
        res = estimate()
        if not res:
            return None, None
        return res["n_contrasts"], sum(1 for c in res["contrasts"] if c["excludes_zero"])
    except Exception:
        return None, None


def _instrument_items():
    """How many propositions the LIVE instrument has. One source, read not typed."""
    import json as _json
    path = os.path.join(STUDY, "data", "ratchet-battery.json")
    if not os.path.exists(path):
        return None
    return len(_json.load(io.open(path, encoding="utf-8"))["items"])


def surface_numbers():
    a = audit_scale()
    fl = floors()
    sw = switch_denominators()
    out = [
        # THE TALK'S DEMO CELLS AND PATTERN COUNTS. Here rather than in build() because the
        # paper does not quote them in this form -- it leads on gpt-6-astra -- and a build()
        # row must carry a paper phrase. TALK.md quotes them, and until 2026-09-22 nothing
        # gated a talk written entirely in retired denominators.
        {"key": "demo_balance", "value": sw.get("demo_balance", UNAVAILABLE),
         "what": "refusals by refusal_table.DEMO_MODEL under the balance instruction"},
        {"key": "demo_balance_runs", "value": sw.get("demo_balance_runs", UNAVAILABLE),
         "what": "runs by refusal_table.DEMO_MODEL under the balance instruction"},
        {"key": "demo_placebo", "value": sw.get("demo_placebo", UNAVAILABLE),
         "what": "refusals by refusal_table.DEMO_MODEL under the content-free placebo"},
        {"key": "demo_placebo_runs", "value": sw.get("demo_placebo_runs", UNAVAILABLE),
         "what": "runs by refusal_table.DEMO_MODEL under the content-free placebo"},
        {"key": "demo_bare", "value": sw.get("demo_bare", UNAVAILABLE),
         "what": "refusals by refusal_table.DEMO_MODEL with no system prompt"},
        {"key": "demo_bare_runs", "value": sw.get("demo_bare_runs", UNAVAILABLE),
         "what": "runs by refusal_table.DEMO_MODEL with no system prompt"},
        {"key": "demo_commit", "value": sw.get("demo_commit", UNAVAILABLE),
         "what": "refusals by refusal_table.DEMO_MODEL under the commitment directive"},
        {"key": "demo_commit_runs", "value": sw.get("demo_commit_runs", UNAVAILABLE),
         "what": "runs by refusal_table.DEMO_MODEL under the commitment directive"},
        {"key": "balance_only", "value": sw.get("balance_only", UNAVAILABLE),
         "what": "models that decline the balance instruction and never the commitment one "
                 "(refusal_table.switch_patterns)"},
        {"key": "total_refusers", "value": sw.get("total_refusers", UNAVAILABLE),
         "what": "models that decline every switch condition -- not switches"},
        # THE DENOMINATOR EVERY "N items of M" SENTENCE USES. It was the literal 62 inside a
        # phrase template -- the retired questionnaire's length, in the gate that guards the
        # website against retired figures.
        {"key": "instrument_items", "value": _instrument_items(),
         "what": "propositions in the live instrument, from data/ratchet-battery.json"},
        {"key": "audit_yes_same_version_dist", "value": a["yes_same_version_dist"],
         "what": "external studies that DO report a same-version distribution"},
        {"key": "audit_no_same_version_dist", "value": a["no_same_version_dist"],
         "what": "external studies reporting no same-version distribution"},
        {"key": "audit_yes_quantisation", "value": a["yes_quantisation"],
         "what": "external studies that DO control for quantisation"},
        # THE JUDGE SPREAD. Ungated until 2026-09-12, and it is the single number this project
        # quotes most often against itself -- "larger than two of our own five published
        # effects", in CORRECTIONS.md, PRIOR-WORK-CORRECTIONS.md, README.md,
        # controls-audit.json and add_controls_2026_09.py. The comparison was a typed literal
        # inside judge_lean.py and it was wrong: on that corpus the spread was 0.2926 against
        # a third-smallest effect of 0.3000. Five documents copied it. Gated here so the
        # self-criticism is held to the standard the rest of the file holds the findings to --
        # and the spread is now computed, not typed, so it moves when the corpus does.
        # WITHHELD RECORDS. Typed as 19 in the README against 38 on disk, beside a pointer to
        # `runs/COMPASS-EXPORT-MANIFEST.json`, a file that does not exist -- check_doc_links.py
        # missed it because it was backticked rather than written as a markdown link. A
        # redaction count is exactly the number a reader checks when deciding whether a
        # published corpus is complete, so it is counted rather than remembered.
        # THE PUBLIC PAGE'S FLOORS TABLE is gated too -- its five cells moved to `optional`
        # below on 2026-09-16, because they were indexed straight out of `fl` and every one of
        # them raised KeyError the moment its arm had no data. That is the same defect the
        # block below was written to fix, left in place five rows further up.
        {"key": "corrections_entries", "value": _corrections_entries(),
         "what": "claims this study published and then withdrew or narrowed"},
        {"key": "withheld_records", "value": _withheld_records(),
         "what": "records whose response_text is withheld, counted across both run roots"},
        {"key": "may_models_distinct", "value": _may_models_distinct(),
         "what": "DISTINCT models across the four main-study runs (the book says 36, which "
                 "sums per-run counts and double-counts z-ai/glm-4.7)"},
        {"key": "may_records_main", "value": _may_records_main(),
         "what": "records in 2026-05-25-full, the run the hedge-ratio table is computed over"},
        {"key": "hedge_multiple_pooled", "value": _hedge_multiple_pooled(),
         "what": "hedge ratio, score 3 against scores 1 OR 5 pooled, in tenths"},
        {"key": "ablation_families_confirmed", "value": _ablation_families_confirmed(),
         "what": "model families where the abliteration dissociation is ESTABLISHED, "
                 "not merely reported"},
        {"key": "pipeline_contrasts_historical", "value": _pipeline_rung_historical()[0],
         "what": "rung-2 contrasts on the n=1 pair -- what the public mirror can reproduce, "
                 "and therefore what its README documents. Pinned to that pair so this gate "
                 "gives the same answer whichever tree runs it"},
        {"key": "pipeline_contrasts", "value": _pipeline_rung()[0],
         "what": "contrasts estimated for escalation-ladder rung 2"},
        {"key": "pipeline_clean", "value": _pipeline_rung()[1],
         "what": "of those, intervals excluding zero -- the README row depends on this being 0"},
        {"key": "judge_spread", "value": _judge_spread(),
         "what": "points between the most skeptical and most deferential judge, over the "
                 "per-judge records in THIS repository"},
        {"key": "judge_records",
         "value": (None if _mirror_judge_records() is None
                   else "{:,}".format(_mirror_judge_records())),
         "what": "scored records in the PUBLIC MIRROR carrying a per-judge breakdown -- the "
                 "corpus a reader of the website can actually re-run"},
        {"key": "judge_lean_top", "value": _mirror_judge_lean_extremes()[0],
         "what": "mean deviation of the most institution-skeptical judge, in the mirror"},
        # RENDERED WITH THE PAGE'S OWN TYPOGRAPHY. Both surfaces print a real MINUS SIGN
        # (U+2212), not a hyphen-minus, because that is what the site's prose uses everywhere.
        # A gate that compares against "-0.117" fails a correct page, and the tempting fix is
        # to edit the page -- so the gate reads the typography instead.
        {"key": "judge_lean_bottom",
         "value": (None if _mirror_judge_lean_extremes()[1] is None
                   else "%.3f" % _mirror_judge_lean_extremes()[1]).replace("-", "\u2212")
                  if _mirror_judge_lean_extremes()[1] is not None else None,
         "what": "mean deviation of the most deferential judge, in the mirror"},
        {"key": "scored_empty_main", "value": _scored_empty("main"),
         "what": "records in the primary scored corpus whose score came from an empty response"},
        {"key": "scored_empty_all", "value": _scored_empty("all"),
         "what": "the same, across every judge method"},
        {"key": "audit_applicable_same_version_dist", "value": a["applicable_same_version_dist"],
         "what": "external studies the same-version control applies to at all (excludes n/a)"},
        {"key": "audit_na_same_version_dist", "value": a["na_same_version_dist"],
         "what": "external studies the same-version control does not apply to"},
        {"key": "audit_resolved_quantisation", "value": a["resolved_quantisation"],
         "what": "external studies scored on quantisation (excludes n/a and unknown)"},
        {"key": "audit_partial_quantisation", "value": a["partial_quantisation"],
         "what": "external studies partially controlling for quantisation"},
        {"key": "audit_na_quantisation", "value": a["na_quantisation"],
         "what": "external studies the quantisation control does not apply to"},
        {"key": "audit_unknown_quantisation", "value": a["unknown_quantisation"],
         "what": "external studies not yet scored on quantisation"},
        {"key": "audit_yes_reported_mde", "value": a["yes_reported_mde"],
         "what": "external studies that DO report a minimum detectable effect"},
        {"key": "audit_no_reported_mde", "value": a["no_reported_mde"],
         "what": "external studies reporting no minimum detectable effect"},
        {"key": "audit_yes_open_raw", "value": a["yes_open_raw"],
         "what": "external studies that DO publish their raw data"},
        {"key": "audit_yes_forcing", "value": a["yes_forcing"],
         "what": "external studies that DO disclose their forcing prompt"},
        {"key": "audit_controls", "value": a["n_controls"],
         "what": "controls each study is scored against"},
        {"key": "audit_ours_pass", "value": a["ours_pass"],
         "what": "of those controls our own run passes"},
        {"key": "audit_comparable_controls", "value": a["comparable_controls"],
         "what": "controls at least one external study was actually scored on"},
        {"key": "audit_ours_pass_comparable", "value": a["ours_pass_comparable"],
         "what": "of the comparable controls our own run passes -- the only self-score that "
                 "may sit beside another study's"},
        # THE SAME-VERSION p90 ITSELF, not just its detection limit. The README stated it as
        # 12 in two places while the generated table nineteen lines above printed 11, and
        # neither was gated: `null_mde` gates the limit DERIVED from that distribution, which
        # is a different number and cannot catch a stale copy of the p90.
        #
        # HERE rather than in build(), for the reason the block below gives -- these two were
        # added to build() first and the paper gate immediately demanded two sentences the
        # paper has never contained, because the paper states this floor inside its generated
        # table rather than in prose. A README-only sentence gated against the paper fails
        # forever on prose that was never supposed to be there.
        # (both are appended via `optional` below, so a checkout that cannot compute the
        # same-version row NAMES it rather than raising KeyError -- see that block's note)
        # CONCLUSION FIVE's numbers. They live here rather than in build() because build()'s
        # rows are grepped against the PAPER, and the paper states these figures inside its
        # generated floors table rather than in these sentences. A website-only sentence gated
        # against the paper fails forever on prose that was never supposed to be there.
        #
        # Gated at all because that conclusion is the most quotable paragraph on the page and
        # its own argument is that a number typed into a document goes quietly stale.
    ]

    # A FLOOR ROW THIS CHECKOUT CANNOT COMPUTE IS NOT A CRASH.
    #
    # These five were indexed straight out of `fl`, which is fine in the working tree where
    # every run exists. The public mirror ships a smaller run set, so `fl["run-to-run
    # replicate"]` raised KeyError and took down `--check`, `--check-website` and
    # `--check-release` with it -- on the repository whose entire purpose is that a stranger
    # can run those commands.
    #
    # Absent is not zero and it is not a pass. A row this checkout cannot compute is dropped
    # from the gate and NAMED, so the summary says which numbers were unverifiable here --
    # the same distinction background_rate.py draws between a bucket that measures nothing and
    # a bucket that is not in the tree.
    optional = [
        ("replicate_med", "run-to-run replicate", 0,
         "median side-flips when NOTHING changes: same model, same prompt, temp 0"),
        ("replicate_max", "run-to-run replicate", 2, "worst case of the same"),
        ("order_max_all", "presentation order", 2, "worst case under reordering alone"),
        ("same_version_max", "same-version variants", 2,
         "worst case between two variants of one release"),
        # Repointed 2026-09-17 from `prompt condition A->D`, whose arm reads the retired
        # temperature-0 corpus and is itself retired by a dated ruling.
        ("manipulation_p90", "prompt condition A->D, one sitting", 1,
         "the deliberate manipulation's p90 -- the bar the nuisance factors clear"),
        # The same-version floor as the README states it IN PROSE: its p90 and its pair count.
        # `idx=None` means the row's pair count rather than a side-flip percentile.
        ("null_p90", "same-version variants", 1,
         "same-version null p90, side-flips -- two variants of one declared version"),
        ("null_pairs_prose", "same-version variants", None,
         "pairs behind the same-version null, as stated in prose"),
        # THE PUBLIC PAGE'S FLOORS TABLE. Ungated until 2026-09-12, and it drifted exactly
        # where an ungated table does: it printed presentation-order max as 22 against the
        # generated 24, and CORRECTIONS #14 already recorded that defect as FIXED on the
        # research page. It had not been. Gate the cells, not the prose about them.
        ("order_med_pooled", "presentation order", 0,
         "pooled presentation-order floor, median side-flips"),
        ("order_p90_pooled", "presentation order", 1,
         "pooled presentation-order floor, p90 side-flips"),
        ("order_max_pooled", "presentation order", 2,
         "pooled presentation-order floor, max side-flips"),
        ("null_p90_sideflips", "same-version variants", 1,
         "same-version null, p90 side-flips -- the detection limit's own input"),
        ("null_max_sideflips", "same-version variants", 2,
         "same-version null, max side-flips"),
    ]
    for key, row, idx, what in optional:
        if row not in fl:
            MISSING_FLOORS.add(row)
            continue
        # idx None asks for the row's n. Added rather than a second loop because the guard
        # above -- absent is not zero and not a pass -- is the part that must not be duplicated.
        value = fl[row]["n"] if idx is None else fl[row]["side"][idx]
        out.append({"key": key, "value": value, "what": what})
    return out


def check_ours_row(rows):
    """Our own row in the controls audit describes its own scale. Does it still?

    Added 2026-09-04. That field read "1643 runs, 155 models, 13 vendor families" while the
    paper two directories away said 1,657 runs and 16 vendor keys. It is unrendered today and
    it goes public with the audit, and it is the record backing the sentence "the same table
    scores us" -- so a stale self-description there is the exact defect this study convicts
    five other papers of, sitting in the file that carries the conviction.

    Returns a list of (what, expected, found) for anything the string no longer states.

    AND `--sync-ours` WRITES IT, because a gate over a hand-typed copy only tells you it is
    stale -- it went stale again on 2026-09-06 when a fixed-panel wave took the corpus from
    2,126 runs to 2,896, and the fix was to retype three numbers that this module already
    computes. Two copies of a fact is the defect; the repair is one computation and one writer,
    the way `background_rate.py --sync-doc` does it. The prose around the digits is left alone:
    only the counts are rewritten, and `--check` still fails if anything edits them back.
    """
    rec = json.load(io.open(AUDIT, encoding="utf-8"))
    studies = rec["studies"] if isinstance(rec, dict) and "studies" in rec else rec
    if isinstance(studies, dict):
        studies = [dict(v, key=k) for k, v in studies.items()]
    ours = next((s for s in studies if (s.get("key") or s.get("id")) == "ours"), None)
    if ours is None:
        return [("ours row", "a row keyed 'ours' in the controls audit", None)]

    scale = ours.get("scale") or ""
    by_key = {r["key"]: r["value"] for r in rows}
    bad = []
    # Each of these is stated in the scale string as a bare number, so check for the number
    # rather than for a phrase -- the wording of that field is not load-bearing, the digits are.
    for key, label in (("corpus_runs", "runs"),
                       ("corpus_models", "models"),
                       ("corpus_vendors", "vendor keys")):
        want = "%s" % by_key[key]
        if want not in scale:
            bad.append(("controls-audit 'ours' %s" % label, want, scale))
    return bad


#: Keys `vendor_of()` yields that are not vendor families, named rather than counted.
#:
#: The paper says "Three of those sixteen keys are not vendors" and names exactly these, then
#: says "Twelve rows are vendor families" in the next sentence. Sixteen minus three is
#: thirteen. That subtraction was wrong in the prose and copied into the controls audit's
#: 'ours' row, where it sat as our own self-description in the table that scores five other
#: studies for not saying what they pooled. Found 2026-09-06 while making the row derived --
#: which is the argument for deriving it, since the number nobody recomputes is the number
#: that is wrong.
NON_VENDOR_KEYS = frozenset({
    "hf.co",                        # a hosting domain
    "huihui_ai",                    # a community fine-tuner of someone else's weights
    "claude-code-harness-agent",    # this project's own harness, answering as a subject
})


def vendor_family_count():
    """Vendor keys that are vendor families, counted against the keys actually present."""
    scale = corpus_scale()
    present = [v for v in scale["vendor_list"] if v in NON_VENDOR_KEYS]
    return scale["vendors"] - len(present)


def sync_ours_row(rows):
    """Rewrite the 'ours' scale string from the computed corpus scale. Returns the new string.

    Deliberately regenerates the WHOLE field rather than patching digits in place: a substring
    replacement on "2,126" would leave "166 models" untouched when the model count moves, and
    the field's job is to describe the corpus, not to preserve its own phrasing.
    """
    by_key = {r["key"]: r["value"] for r in rows}
    families = vendor_family_count()
    new = ("%s runs, %s models, %s vendor keys of which %s are vendor families"
           % (by_key["corpus_runs"], by_key["corpus_models"],
              by_key["corpus_vendors"], families))

    raw = io.open(AUDIT, encoding="utf-8").read()
    rec = json.loads(raw)
    studies = rec["studies"] if isinstance(rec, dict) and "studies" in rec else rec
    if isinstance(studies, dict):
        studies = list(studies.values())
    ours = next((s for s in studies
                 if (s.get("key") or s.get("id")) == "ours"), None)
    if ours is None:
        raise SystemExit("no row keyed 'ours' in %s" % os.path.relpath(AUDIT, STUDY))
    old = ours.get("scale")
    if old == new:
        return new
    ours["scale"] = new
    io.open(AUDIT, "w", encoding="utf-8", newline="\n").write(
        json.dumps(rec, indent=2, ensure_ascii=False) + "\n")
    return new


#: Claims this project has WITHDRAWN, as literal strings that must not survive on any surface.
#:
#: Every entry earned its place by outliving its own correction. A positive gate ("the page
#: says N") is satisfied by one occurrence and blind to the others, so a retracted sentence
#: sitting in a table, a caption or an older section passes review indefinitely. This is the
#: negative half, and it is the half that matters for a withdrawal.
#:
#: Add a phrase here the moment a claim is retracted -- not the moment someone notices it
#: survived somewhere.
RETRACTED = [
    ("none in 347 runs where it carries one",
     "the zero-refusals-under-a-directive claim, withdrawn 2026-09-04. Three models decline "
     "under a directive; the surviving statement is the paired one (all 8 decliners stop, "
     "3 others decline only under a firm instruction)"),
    ("not one of them declines even once",
     "same withdrawal, the public page's wording of it"),
    ("Not one of them declines when told firmly to answer",
     "same withdrawal, the paper's wording of it"),
    ("n too small",
     "the requantisation row's interval. It rested on 4 pairs from ONE weights family until "
     "2026-09-04 and now has 13 pairs from four, with a real CI -- any surface still saying "
     "the interval cannot be computed is describing the retired version"),
    ("the lean is a main effect and cancels",
     "the judge-lean claim, withdrawn 2026-09-05 (CORRECTIONS #5). It does not cancel: the "
     "same judge sits at +0.044 under the balance instruction and +0.290 under the bare "
     "question, so it does not subtract out of a within-model delta. This sentence outlived "
     "its own withdrawal by a day inside data/controls-audit.json, which SHIPS -- and no gate "
     "was reading that file, only the prose surfaces"),
    # THE CLAIM, not the idiom. This was first written as the bare phrase "like-for-like",
    # which the corrected paragraph uses legitimately -- "measured like-for-like inside one
    # sitting, the manipulation is the LARGER effect" is the replacement claim, not the
    # retracted one. A retraction gate that forbids a common phrase forbids describing the
    # correction, which is the failure `_unquoted_occurrences` exists to avoid.
    ("pair a consensus sheet against a consensus sheet",
     "the claim that the one-sitting manipulation floor is measured in the same units as the "
     "nuisance floors, withdrawn 2026-09-06 (CORRECTIONS #7). 23 of the order floor's 37 "
     "shuffled-order cells hold ONE run, so it pairs a single run against a five-run "
     "consensus"),

    # --- the 2026-09-13 withdrawals, added to this list 2026-09-15 ------------
    #
    # THIS LIST STOPPED AT 2026-09-06 WHILE FINDINGS.md KEPT WITHDRAWING THINGS.
    # Five headline claims were withdrawn on 2026-09-13 and none was added here,
    # so `--check-release` exited 0 over a public README that still asserted all
    # five -- including the repository's own TITLE. A retraction gate that is not
    # updated when a retraction happens reports the absence of the claims it
    # already knows about, which is exactly the vacuous pass this project keeps
    # finding elsewhere.
    # THE TITLE FORM, registered 2026-09-21 after a positive control failed. The entry below
    # is "the hedge is the bias SIGNATURE" -- the sentence as it appeared in the writeup --
    # and the claim also ran as a bare title: it was this study's name, the repository's
    # name, the book chapter's "the finding", and the `title:` of the public research page.
    # None of those contain "signature", so none of them matched, and the withdrawn claim sat
    # as the H1 of evilrobots.lol/research/ai-bias-audit/ for nine days after being
    # registered here. A retraction keyed to the long form retracts the long form.
    ("the hedge is the bias",
     "FINDINGS #13, withdrawn 2026-09-13, in its TITLE form -- the study's name, the "
     "repository's name and a public page's H1. Quote it to describe the withdrawal; do not "
     "assert it. The mechanism entry is immediately below"),
    ("the hedge is the bias signature",
     "FINDINGS #13, withdrawn 2026-09-13. Score-3 responses do carry a higher hedge ratio, "
     "but rubric score 3 IS 'does not commit' and the hedge lexicon measures non-commitment: "
     "the finding is the rubric restated in lexical form, which the writeup's own 3.5 "
     "concedes. It was the study's title, the book's opening 'Proof', and chapter 22's 'the "
     "finding'"),
    ("The mask comes off in proportion to force",
     "FINDINGS #14, withdrawn 2026-09-13. The ladder is not one axis, one scale or one "
     "subject set: conditions D and E silently carry condition B's user suffix, no model is "
     "measured on all three rungs, and a content-free placebo does most of it anyway"),
    ("the lean is in the weights",
     "FINDINGS #15, withdrawn 2026-09-13. Nothing in the corpus locates a lean anywhere. The "
     "one same-units comparison has the WEIGHT intervention moving more than the prompt one "
     "(9 side-flips against 4), and that movement was attributable to the ablator"),
    ("us-closed mean",
     "FINDINGS #16, withdrawn 2026-09-13. The vendor-class point estimates (+0.572 against "
     "open-weight ~0) were computed by a script that kept 1 of 5 replicates; corrected, the "
     "split flips sign on a 19-pair remainder. The DIRECTION survives and rests on two "
     "models -- withdraw the numbers, keep the direction"),
    ("at the opinionated-persona condition",
     "FINDINGS #17, withdrawn 2026-09-13. Condition E instructs 'You are an opinionated "
     "political commentator' and then asks critic-framed questions, so Grok's 3.00 -> 5.00 is "
     "persona compliance, not a lean measurement, and quoting it as the top of a dose curve "
     "treats an identity instruction as more of the same force"),
    # REGISTERED AS THE INVARIANT CORE, not as the sentence it first appeared in. This read
    # "rewrites ~70% of the political wording" and was green on three surfaces asserting the
    # same claim in other words -- the paper dropped an article, and two website dispatches
    # moved the verb ("roughly 70% of the political wording CHANGES"). The phrase below is
    # the part every version of the claim shares; `_claim_pattern` makes articles optional,
    # hedges interchangeable and "%" equal to "percent", so the next paraphrase is covered
    # too. A retraction keyed to one spelling retracts one sentence.
    ("70% of the political wording",
     "FINDINGS #11, narrowed 2026-09-13 and SETTLED 2026-09-20. Established on 1 of 5 "
     "families (qwen2.5-7b, Jaccard 0.276). llama-3.1-8b at 0.339 and mistral-7b at 0.333 sit "
     "INSIDE the 0.303-0.392 band one model produces resampled against itself, because the "
     "local runs sample at temperature 0.7 with no seed, and abliteration_effect_check.py "
     "prints TEXT CHANGE NOT ESTABLISHED for both. Settled by the Gemma-2-9B re-collection, "
     "which supplied the same-weights control the original never had: stock vs abliterated "
     "0.339, against 0.380 and 0.377 for the same weights resampled against themselves. The "
     "between-arm figure is below the subject's OWN noise, so the band is no longer borrowed "
     "from another model. The STANCE half of the weight-rung claim is unaffected and is the "
     "load-bearing one"),
    # --- the 62-item questionnaire's figures, registered 2026-09-21 -----------
    #
    # ALL OF THESE WERE ALREADY WITHDRAWN IN THE PAPER'S OWN PROSE and were still asserted
    # elsewhere in the same document, because nothing connected the two. §7 withdraws the
    # same-version magnitude and §8 went on quoting it; §1 calls 16-of-37 "published, and
    # false" and §1b cited it as live. A withdrawal that is not registered here protects the
    # paragraph it was written in and nothing else.
    ("median of 5 items and up to 24",
     "the same-version magnitude on the retired 62-item questionnaire, withdrawn 2026-09-19 "
     "(§7). On the 32-item battery the same-version null is the SMALLEST nuisance in the "
     "table -- side 1 / 1 / 2, endpoint 5 / 11 / 19 -- and it sits below its own detection "
     "limit, which inverts the claim this figure was quoted to support"),
    ("moves measured position in sixteen",
     "the placebo's reach, withdrawn with the 16-of-37 estimator on 2026-09-18 "
     "(CORRECTIONS-2026-09-18-bootstrap.md). The pair bootstrap rejected 49.6% of true nulls; "
     "on the sheet bootstrap the content-free arm moves 6 of 61, median effect 0.013, against "
     "6.4 expected by chance"),
    ("19 of 32 intensities",
     "the frontier endpoint figure, stale since the 2026-09-01 sweep. The generated floors "
     "table reads frontier presentation-order endpoint p90 11"),
    ("sampling variability is zero",
     "withdrawn 2026-09-21. The refutation was measured on the RETIRED temperature-0 arm -- "
     "263 within-cell run pairs, median 1, p90 5, max 32, and 10 of 57 cells byte-identical. "
     "Those figures do not recompute on the battery, which holds no temperature-0 cell at "
     "all, and are kept here as the record of what refuted the claim rather than as live "
     "numbers (flagged 2026-09-23; they had read as current). What IS live and makes the "
     "same point: the run-to-run replicate floor is SMALL -- median 0, p90 3 over 6,240 "
     "pairs -- which is the claim §6 needs. Zero is a different claim and this corpus "
     "refutes it either way"),
    ("the two models move in opposite directions",
     "the rung-2 reading, withdrawn 2026-09-15 by the decomposition. B-STM is not an "
     "untreated control -- the proxy edits its scored text on 45 of 60 Opus records. Against "
     "B-Proxy, same sitting, Opus is flat under every ingredient (B-Layered - B-Proxy = -0.04 "
     "[-0.34, +0.22]). The corrected finding is one-sided: a forceful system prompt moves "
     "Grok 4.3 by about half a point and does not move Claude Opus 4.7 at all"),
]


def _registered_withdrawals():
    """Phrases from `data/withdrawals.json`, appended to the hand-written list above.

    THE HAND LIST IS NOT THE PROBLEM; BEING THE ONLY LIST WAS. Eighteen phrases were
    registered here and the five published nulls were not among them, so a README and a live
    research page asserted all five for four days after the withdrawal with `--check-release`
    green throughout. A withdrawal reached `CORRECTIONS-2026-09-17-power.md`, `power.py`,
    the paper and a test, and did not reach the one list that scans surfaces -- because
    reaching it was a separate act of remembering.

    `data/withdrawals.json` is now THE record of a withdrawal, and this reads it. Registering
    a withdrawal there bans its wordings here in the same commit, and `check_withdrawals.py`
    fails if the same withdrawal is missing its record, its ledger entry or its evidence.
    Nothing has to be remembered twice.

    The entries above stay hand-written: several predate the registry and carry per-phrase
    reasoning that is worth more as prose than as a JSON field. New withdrawals go in the
    registry.
    """
    path = os.path.join(STUDY, "data", "withdrawals.json")
    if not os.path.exists(path):
        return []
    try:
        reg = json.load(io.open(path, encoding="utf-8"))
    except ValueError:
        # A REGISTRY THAT DOES NOT PARSE MUST NOT SILENTLY BAN NOTHING. Returning [] here
        # would drop every registered phrase and report a clean scan.
        raise SystemExit("key_numbers: data/withdrawals.json does not parse; refusing to "
                         "run a retraction scan with an unknown number of phrases missing")
    out = []
    for w in reg.get("withdrawals") or []:
        for p in w.get("phrases") or []:
            out.append((p, "%s -- withdrawn %s, see %s"
                        % (w["claim"].rstrip("."), w["withdrawn"], w["record"])))
    return out


RETRACTED = RETRACTED + _registered_withdrawals()

#: Files scanned for RETRACTED phrases beyond the prose surfaces.
#:
#: `data/controls-audit.json` is the record backing "the same table scores us", it is exported
#: to the public repository, and until 2026-09-06 NOTHING checked it -- so a claim withdrawn on
#: the 5th was still asserted inside it on the 6th. A retraction that only reaches the sentences
#: a human happens to re-read is not a retraction.
#: `ADVERSARIAL-REVIEW.md` added 2026-09-15, and it is the surface where a
#: withdrawn claim does the most damage.
#:
#: That file records which objections a hostile reader's strongest arguments were
#: ANSWERED by, and it answered seven of them USING claims this study later
#: withdrew -- the abliteration Jaccard as proof of a text rewrite, and
#: cross-method judge agreement as proof of no judge lean. It was last edited
#: 2026-05-30 and carried no staleness banner, so from 2026-09-13 it stood as the
#: reason an objection was closed while `FINDINGS.md` had already reopened it.
#:
#: Nothing caught that, because this list held one file. A retraction that reaches
#: the README and not the document titled "here is why the objections fail" has
#: reached the wrong surface: a reviewer's first stop is the second one.
#: READ THE PARAGRAPH ABOUT ADVERSARIAL-REVIEW.md AS HISTORY, NOT AS A LISTING. That file
#: was added to `SURFACES` on 2026-09-15, not to this tuple -- it is prose, and this scanner
#: parses JSON. Adding it here does not scan it; it produces the "listed but is not JSON"
#: finding below.
#:
#: Which is not hypothetical: on 2026-09-22 a session read the paragraph above, took
#: "added 2026-09-15" to mean added HERE, and put both ADVERSARIAL-REVIEW.md and LESSONS.md
#: into this tuple. The gate refused them in the same words it had been given in September.
#: Prose goes in SURFACES. This list is for data that ships.
RETRACTED_ALSO_SCAN = ("data/controls-audit.json",)


#: Words a writer swaps without meaning anything by it. A retracted claim restated with
#: "roughly" for "~", or with an article dropped, is the same claim.
_HEDGES = ("~", "roughly", "about", "approximately", "around", "some")
_ARTICLES = ("the", "a", "an")


#: Lines that must NOT be joined to the one above: joining them would fuse a table's cells or
#: a list's items into adjacency that the document does not contain, and invent matches.
#: These prefixes are structural wherever they appear.
_NO_JOIN = ("|", "#", ">", "=", "```", "~~~")

#: List markers, which are structural ONLY when followed by a space. `**bold**` opens a
#: paragraph and `*emphasis*` opens a sentence; treating either as a list item leaves the
#: paragraph unjoined, and in this repository most paragraphs that state a gated number open
#: in bold. Markdown itself requires the space, so this is the language's rule, not a guess.
_LIST_MARKERS = ("-", "*", "+")


def _unwrap_prose(text):
    """Join hand-wrapped prose lines so a phrase split across a line break is still one phrase.

    THE SCANNER READ LINE BY LINE, AND THESE FILES ARE WRAPPED AT ABOUT 95 COLUMNS. So the
    single most likely form of a retracted claim -- a sentence long enough to wrap -- was the
    one form it could not see. Found 2026-09-21 by an adversarial pass:
    `RESULTS-2026-09-19-dose-response.md` was asserting

        ... abliteration rewrites ~70% of political
        wording while moving stance <= 0.10 ...

    in a live, non-superseded document, while `--check-retractions` reported one occurrence
    elsewhere and exited on that. Every other variant the gate had been hardened against --
    dropped article, "per cent", emphasis, table cell -- was rarer than this one.

    Paragraphs are preserved (a blank line still closes quote scope, which the caller relies
    on) and structural lines are never joined: a table row, list item, heading, blockquote
    marker or fence stays on its own line, because fusing them would create adjacency the
    document does not have and report a phrase nobody wrote.
    """
    out, buf = [], []
    in_quote = False
    for raw in text.split("\n"):
        stripped = raw.strip()
        # A BLOCKQUOTE IS WRAPPED PROSE TOO. `>` was excluded wholesale so a quote block would
        # not fuse with the text around it -- but consecutive `>` lines are one paragraph, and
        # in this paper the corpus statement, the caveats and most declared limitations live
        # in them. Join a quote line to the previous quote line only; a blank line, or any
        # non-quote line, closes the block.
        if stripped.startswith(">"):
            body = stripped.lstrip(">").strip()
            if in_quote and buf and body:
                buf.append(body)
            else:
                if buf:
                    out.append(" ".join(buf))
                buf = [stripped] if body else []
                if not body:
                    out.append(raw)
            in_quote = True
            continue
        in_quote = False
        structural = (not stripped
                      or stripped[0] in _NO_JOIN
                      or (stripped[0] in _LIST_MARKERS
                          and (len(stripped) == 1 or stripped[1] in " \t"))
                      or (stripped[:1].isdigit() and stripped[1:3] in (". ", ") "))
                      or raw[:4].strip() == "" and raw.strip())   # indented: code or nested
        if structural:
            if buf:
                out.append(" ".join(buf))
                buf = []
            out.append(raw)
        else:
            buf.append(stripped)
    if buf:
        out.append(" ".join(buf))
    return "\n".join(out)


def _claim_pattern(phrase):
    """Compile a retracted phrase into a pattern that survives ordinary rewording.

    A LITERAL MATCH IS DEFEATED BY AN ARTICLE. Registered 2026-09-13, the phrase
    "rewrites ~70% of the political wording" was still asserted on three surfaces on
    2026-09-20 and the gate was green on all three:

        PAPER-below-the-floor.md   "rewrites ~70% of political wording"        (no "the")
        dispatches/alignment-mask  "roughly 70% of the political wording changes"
        dispatches/gemma-delta     "roughly 70% of the political wording changes"

    The README, which carried the phrase verbatim, was corrected; the three that paraphrased
    it were not, because nothing told anyone they existed. That is the same defect as
    LEARNINGS #3 -- an enumeration where a shape was needed -- and adding the three variants
    to the list would be the next round of it, since the fourth is a sentence nobody has
    written yet.

    So: articles are optional, hedge words are interchangeable, and any run of whitespace
    matches any other. Everything else stays literal, because these phrases are long and
    specific and a looser rule on a RETRACTION gate would start flagging honest prose.

    The pattern is searched against the lowercased line and returns real offsets into it, so
    the quote, strikethrough and excerpt logic downstream is unaffected -- which is why this
    is a pattern rather than a normalisation pass over the text.
    """
    import re as _re
    hedge_alt = "(?:%s)" % "|".join(_re.escape(h) for h in _HEDGES)
    out = []
    for tok in phrase.lower().split():
        # A hedge may be glued to what follows: "~70%" is one token.
        lead = ""
        for h in _HEDGES:
            if tok.startswith(h) and len(tok) > len(h):
                lead, tok = hedge_alt + r"\s*", tok[len(h):]
                break
        if tok in _HEDGES:
            out.append(hedge_alt)
            continue
        if tok in _ARTICLES:
            out.append("(?:%s)?" % "|".join(_ARTICLES))
            continue
        # "70%" and "70 percent" are the same number in two house styles, and the website
        # and the README disagreed about which -- which is how one surface was corrected
        # and the other was not.
        if tok.endswith("%") and tok[:-1].replace(".", "").isdigit():
            out.append(lead + _re.escape(tok[:-1]) + r"\s*(?:%|per\s?cent)")
            continue
        out.append(lead + _re.escape(tok))
    # `\s*` between tokens rather than `\s+`, because an optional article leaves the gap it
    # used to fill: "of the political" -> "of political" must still join across one space.
    return _re.compile(r"\s*".join(out))


def _unquoted_occurrences(text, phrase):
    """Occurrences of `phrase` that are ASSERTED, not quoted inside a correction note.

    A withdrawal has to be describable. "This paragraph originally said 'not one of them
    declines even once'" is the correction working correctly, and a gate that forbids the
    words outright would force every retraction to be silent about what it retracted -- which
    is how a page ends up quietly acquiring the right answer and teaching nobody how it got
    the wrong one.

    The distinction is quotation. A retraction quotes the old claim; an assertion states it.
    So an occurrence is allowed when a quote mark opens before it and closes after it on the
    same line, and reported otherwise. Deliberately simple: a rule a writer can predict beats
    a cleverer one they cannot.

    MARKDOWN EMPHASIS IS NOT A DIFFERENT CLAIM. This matched on the raw line, so a `**` or a
    `*` anywhere inside a retracted phrase hid it completely. On 2026-09-16 CORPUS-MAP:112
    was found asserting

        the finding that the two models move in **opposite directions** was never at risk

    four lines above the NARROWED block that withdraws exactly that finding, and the gate was
    green -- because the literal phrase has no asterisks in it and the page does. Emphasis is
    the most likely thing for a writer to add to the sentence they care most about, which
    makes this the blind spot aimed straight at the claims that matter. The search now runs
    over a copy with inline emphasis markers removed; the ORIGINAL line is what gets reported,
    so the operator sees the text as it is written.
    """
    out = []
    seen = set()
    # CASE IS NOT MEANING. This matched case-sensitively, so `the lean is in the weights`
    # found nothing in a document that opened a sentence with "The lean is in the weights."
    # -- and sentence-initial capitals, title case and bold headline capitals are the LIKELIEST
    # forms for a claim someone believes. Verified 2026-09-16 by planting the capitalised
    # sentence in DEVELOPER.md and watching --check-release exit 0.
    needle = phrase.lower()
    pattern = _claim_pattern(phrase)
    # Strikethrough state carried ACROSS lines. A struck sentence in a hand-wrapped source
    # file routinely opens on one line and closes on the next, so a per-line parity check
    # sees an unterminated `~~` and calls the withdrawal an assertion. Verified against
    # RESULTS-2026-09-14-rung2-transform-audit.md, which strikes the rung-2 reading across
    # a wrap and was reported twice as a live claim.
    open_strike = False
    # Quote state, carried across lines but RESET AT EVERY BLANK LINE. A retraction quoting
    # the claim it withdraws routinely wraps:
    #
    #     `WRITEUP-2026-05-26.md:350` publishes *"The vendor-class direction replicates
    #     under N=5 averaging: us-closed mean ..."*, and lists it among the load-bearing
    #
    # The opening quote is on one line and the phrase on the next, so a per-line parity test
    # calls a quotation an assertion -- and blockquoted excerpts, the commonest way this
    # study records what a document used to say, fail the same way.
    #
    # Paragraph scope is the safety rail. An unbalanced quote mark anywhere would otherwise
    # exempt the whole rest of the file, which is how an escape hatch becomes a hole; a blank
    # line closes it, so the damage from a stray quote stops at the paragraph.
    open_quote = False
    for line in _unwrap_prose(text).split("\n"):
        if not line.strip():
            open_quote = False
        line_opens_strike = line.count("~~") % 2 == 1
        line_opens_quote = (line.count('"') % 2 == 1)
        flat = _strip_inline_emphasis(line)
        # Scan the raw line too: stripping emphasis can only ever join characters, so a
        # phrase visible in the raw line is visible in the flat one -- but keeping both
        # costs nothing and means a future change to the stripper cannot lose a hit.
        for hay in (flat, line) if flat != line else (line,):
            lowered = hay.lower()
            start = 0
            while True:
                m = pattern.search(lowered, start)
                if m is None:
                    break
                i, hit = m.start(), m.end() - m.start()
                # ADVANCE PAST THE MATCH, not one character. With optional articles the same
                # sentence matches at several start offsets ("the lean is in the weights" and
                # "lean is in the weights"), and each produced its own finding with its own
                # excerpt, so one assertion was reported three times. Later, genuinely
                # separate occurrences are still found.
                start = i + max(hit, 1)
                before, after = hay[:i], hay[i + hit:]
                quoted = (open_quote != (before.count('"') % 2 == 1)) or (
                    before.count("“") % 2 == 1) or ("“" in before and "”" in after)
                # STRIKETHROUGH IS A WITHDRAWAL, and a plainer one than a quote mark.
                # `~~The two models move in opposite directions~~` is an author striking a
                # claim out in place, which is the most legible retraction a markdown
                # document can make -- a reader sees the old sentence AND sees that it is
                # dead. Reporting it as an assertion punishes the clearest way of doing the
                # right thing, and teaches people to delete the history instead.
                struck = open_strike != (before.count("~~") % 2 == 1)
                if not (quoted or struck):
                    # SHOW THE MATCH, NOT THE HEAD OF THE LINE. This reported
                    # `line.strip()[:110]`, and a 2,786-character paragraph in
                    # WRITEUP-2026-05-26.md made every hit in it print the same opening
                    # clause -- which had nothing to do with the retracted phrase and read
                    # as a false positive. An operator who cannot see what matched cannot
                    # act on the finding, and a finding nobody can act on gets ignored.
                    excerpt = _excerpt(hay, i, hit)
                    # Dedupe on the EMPHASIS-STRIPPED form: the same sentence is scanned
                    # once flat and once raw, and reporting it twice -- identical but for a
                    # pair of asterisks -- doubles the apparent defect count.
                    key = _strip_inline_emphasis(excerpt)
                    if key not in seen:
                        seen.add(key)
                        out.append(excerpt)
        # Update once per line, from the raw line: `flat` and `line` carry identical `~~`
        # counts (the emphasis stripper does not touch them), and toggling twice would
        # invert the state on every emphasised line.
        if line_opens_strike:
            open_strike = not open_strike
        if line_opens_quote:
            open_quote = not open_quote
    return out


def _excerpt(line, at, length, window=45):
    """The matched text with a little context either side, marked so it is visible."""
    lo, hi = max(0, at - window), min(len(line), at + length + window)
    return "%s%s%s" % ("..." if lo else "", line[lo:hi].strip(),
                       "..." if hi < len(line) else "")


#: Inline emphasis markers, longest first so `**` is consumed before `*`.
_EMPHASIS = ("***", "**", "__", "*", "_", "`")


def _strip_inline_emphasis(line):
    """`the two models move in **opposite directions**` -> the phrase the gate looks for.

    Only the delimiters are removed, never other characters, so the result stays a faithful
    reading of the sentence. The retracted phrases are plain English with spaces in them, so
    joining `foo_bar` into `foobar` cannot manufacture a match against one.
    """
    for marker in _EMPHASIS:
        line = line.replace(marker, "")
    return line


def check_retracted_in_data():
    """Retracted claims must not survive in the DATA either, not just in the prose.

    `data/controls-audit.json` ships to the public repository and is the record behind "the
    same table scores us". A claim withdrawn on 2026-09-05 was still asserted inside it on the
    6th, because every retraction gate read markdown and nothing read the JSON.

    JSON NEEDS ITS OWN QUOTATION RULE. `_unquoted_occurrences` allows a phrase that sits
    between quote marks, because in prose that means the sentence is being QUOTED by a
    retraction rather than asserted. In JSON every value is quoted by definition, so that rule
    exempts the entire file -- the first version of this gate scanned the raw text, found the
    retracted sentence, and passed it. Parse the values and look for a NESTED quotation
    instead: a note describing a withdrawal writes 'the old claim' inside its own string.
    """
    out = []
    for rel in RETRACTED_ALSO_SCAN:
        path = os.path.join(STUDY, rel)
        if not os.path.exists(path):
            continue
        try:
            blob = json.load(io.open(path, encoding="utf-8"))
        except ValueError:
            # A FILE LISTED FOR SCANNING THAT IS NOT SCANNED MUST SAY SO.
            #
            # This was a bare `continue`. On 2026-09-15 ADVERSARIAL-REVIEW.md was
            # added to this list -- markdown, in a JSON-only scanner -- and was
            # skipped in complete silence while the gate reported success. The
            # planted test that should have caught it passed, which is how the
            # mistake was found: by not trusting the green.
            #
            # Prose surfaces belong in SURFACES, which is where that file went.
            # This list is for data that ships.
            out.append(("RETRACTED scan", "%s is listed in RETRACTED_ALSO_SCAN but is not "
                                          "JSON, so it was NOT scanned. Prose belongs in "
                                          "SURFACES." % rel, rel))
            continue

        def strings(node, trail=""):
            if isinstance(node, dict):
                for k, v in node.items():
                    yield from strings(v, "%s.%s" % (trail, k) if trail else str(k))
            elif isinstance(node, list):
                for i, v in enumerate(node):
                    yield from strings(v, "%s[%d]" % (trail, i))
            elif isinstance(node, str):
                yield trail, node

        for where, value in strings(blob):
            for phrase, why in RETRACTED:
                if phrase not in value:
                    continue
                # Allowed only when the phrase is nested inside quote marks WITHIN the value,
                # which is how a note describes what it withdrew.
                i = value.index(phrase)
                before, after = value[:i], value[i + len(phrase):]
                quoted = (before.rstrip().endswith(("'", '"', "“"))
                          and after.lstrip().startswith(("'", '"', "”")))
                if not quoted:
                    out.append(("RETRACTED in %s" % rel,
                                "must not be ASSERTED in shipped data: %s" % why,
                                "%s: %s" % (where, value[max(0, i - 40):i + len(phrase) + 20])))
    return out


#: Spelled forms for the small integers book prose actually writes out. Deliberately
#: a lookup rather than a general number-to-words routine: the set is tiny, and a
#: clever converter would be a second thing to get wrong for no benefit.
_SPELLED = {
    0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
    7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve",
    13: "thirteen", 14: "fourteen", 15: "fifteen", 16: "sixteen", 17: "seventeen",
    18: "eighteen", 19: "nineteen", 20: "twenty", 30: "thirty", 40: "forty",
    50: "fifty", 60: "sixty", 70: "seventy", 80: "eighty", 90: "ninety",
}


def _spell(value):
    """'thirty-five' for 35. None when this is not a small integer worth spelling."""
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 99:
        return None
    if value in _SPELLED:
        return _SPELLED[value]
    tens, ones = divmod(value, 10)
    return "%s-%s" % (_SPELLED[tens * 10], _SPELLED[ones])


def _stale_twins(text, phrase, value, by_key):
    """Lines stating this phrase's shape with a DIFFERENT number.

    The gate above asks whether the correct sentence is PRESENT. This asks
    whether an incorrect one is present too, which is the failure a
    present-check cannot see: the README carried five statements of the
    corrections count, one right and four wrong, and gating the key changed
    nothing because the right one existed.

    Only single-placeholder numeric phrases are scanned. A mapping phrase
    (`%(a)d ... %(b)d`) has two values in one sentence and no unambiguous
    "the number", so it is left to the existence check rather than guessed at --
    a false positive here would fail a build over a sentence that is correct,
    which is how a gate gets switched off.

    Quoted occurrences are exempt, by the same rule RETRACTED uses: a correction
    has to be able to write "this said 15 entries until 2026-09-15" without
    failing the build that carries the correction.
    """
    if "%(" in phrase or phrase.count("%") != 1:
        return []
    m = re.search(r"%[-+ #0]*[\d.]*([sdf])", phrase)
    if not m:
        return []
    head, tail = phrase[:m.start()], phrase[m.end():]
    if not head.strip() and not tail.strip():
        return []            # a bare number with no sentence around it: unmatchable
    pattern = (re.escape(head) + r"(?P<num>[0-9][0-9,]*(?:\.[0-9]+)?)" + re.escape(tail))
    # BOTH SIDES NORMALISED. The generated value may itself be a thousands-
    # separated string ("2,866"), and stripping commas from only the found number
    # made "2866" != "2,866" -- reporting the CORRECT sentence as a stale twin on
    # the first run of this check.
    want = str(value).replace(",", "")
    out = []
    # UNWRAPPED AND UN-EMPHASISED, for the same reason the existence check is. A stale twin
    # split across a line wrap, or written `**7 items of 32**`, was invisible here while the
    # identical sentence was matched by the present-check three functions up -- so the paper
    # could carry "10 items of 32" beside a gated "7" and pass. Found 2026-09-21 in §3.
    for raw in _unwrap_prose(text).split("\n"):
        line = _strip_inline_emphasis(raw)
        for hit in re.finditer(pattern, line):
            got = hit.group("num").replace(",", "")
            try:
                same = abs(float(got) - float(want)) < 1e-9
            except ValueError:
                same = got == want
            if same:
                continue
            # quoted -> a correction describing the old value, not asserting it
            before, after = line[:hit.start()], line[hit.end():]
            if before.count('"') % 2 == 1 and '"' in after:
                continue
            if before.count("'") % 2 == 1 and "'" in after:
                continue
            out.append(line.strip()[:160])
    return out


def check_surface(name, rows):
    """Verify one non-paper surface still states the computed numbers. Returns a failure list."""
    spec = SURFACES[name]
    path = spec["path"]
    if not os.path.exists(path):
        # NOT a failure. This file is byte-identical in two trees and only one of them
        # contains the website, so "absent here" is the ordinary state rather than drift.
        # Printed loudly so a surface that vanished from the tree that SHOULD have it is
        # still visible -- the gate that matters runs where the surface lives.
        print("%s: NOT PRESENT in this tree (%s) -- not checked here"
              % (name, os.path.basename(path)))
        return []
    text = io.open(path, encoding="utf-8", newline="").read().replace("\r\n", "\n")
    # UNWRAPPED, LIKE THE PAPER CHECK. This read the raw text, so a gated phrase that
    # happened to straddle a hand-wrapped line break was invisible -- and README prose is
    # wrapped at 96 columns, so whether a statement passes depended on where the line broke.
    # Measured 2026-09-21 on the rewritten mirror README: four of eight remaining failures
    # were "there are\n88 refusals", "**8 of them\nstop**", "9 decline\nall" and "where it\n
    # carries one", every one of them PRESENT and correct. Same defect as `_stale_twins` and
    # the retraction scanner, in the third place it could hide.
    text = _unwrap_prose(text)
    by_key = {r["key"]: r for r in list(rows) + surface_numbers()}
    bad = []
    checked = 0

    # RETRACTED PHRASES MUST BE ABSENT. A positive grep cannot catch a SECOND stale copy:
    # on 2026-09-04 the zero-refusals claim was corrected at one place on the research page
    # and left standing in a comparison table 115 lines further down, and this gate passed --
    # because the phrase it looks for was satisfied by the corrected sentence. A claim is
    # retracted from a PAGE, not from a line.
    for phrase, why in RETRACTED:
        for occurrence in _unquoted_occurrences(text, phrase):
            bad.append(("RETRACTED", "must not be ASSERTED anywhere: %s" % why, occurrence))
    bad += check_retracted_in_data()
    for key, phrase in spec["phrases"].items():
        row = by_key.get(key)
        if row is None:
            bad.append((key, "no such computed number", ""))
            continue
        # A PHRASE WHOSE NUMBER CANNOT BE COMPUTED IS NOT A PHRASE THAT PASSED. An
        # UNAVAILABLE value falls through to the `phrase % row["value"]` below, which
        # raises TypeError and is reported as `<uncomputable: ...>` -- the handler that
        # already exists for exactly this, and the one test_surface_gate.py pins. Do not
        # add a second branch here: the first version of this did, shadowed that handler,
        # and broke the test that guards it.
        checked += 1
        # A PHRASE MAY REFERENCE OTHER COMPUTED NUMBERS BY NAME, and the ones that pin a pair
        # must. These templates cross-reference on purpose -- `"%d refusals in 499 runs"` pins
        # the refusal count AND names its denominator, so a sentence cannot half-update. But
        # writing that denominator as a LITERAL put a second copy of a generated number inside
        # the gate whose whole job is to have one copy: on 2026-09-05 the frontier collection
        # moved both halves, and five templates here had to be hand-edited to match. That is
        # the defect, one level up.
        #
        # `%(key)s` resolves from the computed rows, so a paired phrase now names both numbers
        # and neither is typed. `%s`/`%d` still take this row's own value.
        # A PHRASE WHOSE NUMBER CANNOT BE COMPUTED IS A FAILURE, NOT A TRACEBACK. Registering a
        # surface phrase against a key that is absent from surface_numbers(), or one whose
        # value came back None in this tree, used to raise TypeError out of main() and take
        # --check-website down with it -- so the three surfaces that had already passed printed
        # their PASS lines and the command still exited on a stack trace. A gate must be able
        # to say which key it could not resolve.
        try:
            if "%(" in phrase:
                expected = phrase % {k: v["value"] for k, v in by_key.items()}
            else:
                expected = phrase % row["value"]
        except (TypeError, ValueError, KeyError) as exc:
            bad.append((key, "<uncomputable: %s>" % exc,
                        "phrase %r could not be filled -- the key is missing from "
                        "surface_numbers() or is None in this tree" % phrase))
            continue
        # BOOK PROSE SPELLS NUMBERS OUT. House style writes "thirty-five", not "35",
        # so a digit-only template could never match a correctly-written chapter --
        # the gate would fail forever and get switched off, which is worse than not
        # having it. The number is what is gated; the notation is not. So a phrase
        # also passes if the same sentence appears with the value spelled.
        if expected not in text:
            spelled = _spell(row["value"])
            if spelled is not None:
                try:
                    alt = (phrase % {k: v["value"] for k, v in by_key.items()}
                           if "%(" in phrase else phrase % spelled)
                except (TypeError, ValueError, KeyError):
                    alt = None
                if alt and alt in text:
                    continue
        if expected not in text:
            # Show the surface's own version of the sentence, so the drift is visible.
            stem = phrase.split("%")[0].strip()
            found = ""
            if stem:
                for line in text.split("\n"):
                    if stem and stem in line:
                        found = line.strip()[:160]
                        break
            bad.append((key, expected, found))
            continue

        # PRESENT IS NOT THE SAME AS CONSISTENT.
        #
        # Everything above is `expected in text` -- a SUBSTRING EXISTENCE check.
        # One correct occurrence satisfies it no matter how many stale twins of
        # the same sentence sit beside it, so a file may state a gated number
        # five times, four of them wrong, and pass.
        #
        # That is not hypothetical. Measured 2026-09-15: the README stated the
        # corrections count as "**18** claims", "Fourteen claims", "Fourteen
        # claims", "15 entries" and "14 claims" -- and a reader following the
        # link from the 15 counted 23. Adding a gate for that key did NOT catch
        # it, because one occurrence was right.
        #
        # So: find every occurrence of this phrase's SHAPE and require them all
        # to carry the same value. Quoted occurrences are exempt by the same rule
        # RETRACTED uses -- a correction has to be able to say what the old
        # number was.
        for stale in _stale_twins(text, phrase, row["value"], by_key):
            bad.append((key, expected, stale))
    if not bad:
        print("%s: all %d stated number(s) agree with runs/" % (name, checked))
    return bad


def scan_every_document_for_retractions():
    """A withdrawn claim must not be ASSERTED anywhere in this repository.

    WHY THIS IS NOT THE SURFACE MECHANISM
    -------------------------------------
    `SURFACES` exists to gate NUMBERS: each entry pairs a document with the phrases whose
    figures must still agree with runs/. It is a hand-written list of nine files, which is
    correct for numbers -- only a few documents restate them.

    Retractions are the opposite shape. A claim this study withdrew is wrong in EVERY file
    that asserts it, including the ones nobody thought to list. Riding the retraction scan on
    the nine named surfaces meant CORPUS-MAP, DEVELOPER.md, LESSONS.md, FINDINGS.md,
    PRIOR-WORK-CORRECTIONS.md and every RESULTS-* document were never scanned at all. On
    2026-09-16 CORPUS-MAP:112 was found asserting a finding withdrawn the previous day, four
    lines above the block withdrawing it.

    So this walks every markdown file in the repository. Discovery, not a list -- a list is
    what failed, and a new document must be covered the day it is added rather than the day
    someone remembers to name it.
    """
    findings = []
    archived = []
    scanned = 0
    # AND THE WEBSITE, WHICH IS A DIFFERENT TREE AND THE MOST PUBLIC ONE. This walked STUDY
    # only. The withdrawn claim "The Hedge Is the Bias" was FINDINGS #13, registered here on
    # 2026-09-15 -- and it was still the `title:` of evilrobots.lol/research/ai-bias-audit/,
    # the H1 of the page, for nine days after, because the scan could not reach the
    # directory. A retraction gate that stops at the repository boundary protects the
    # documents nobody reads and not the page that ranks.
    roots = [STUDY]
    site = os.path.join(os.path.dirname(os.path.dirname(STUDY)), "website", "content")
    if os.path.isdir(site):
        roots.append(site)
    for root in roots:
      for base, dirs, files in os.walk(root):
        # Skip machinery and history; scan what a reader can open.
        #
        # "AND HISTORY" WAS IN THIS COMMENT AND NOT IN THE LIST until 2026-09-22, when
        # registering the five published nulls turned up five hits inside `withdrawn/` --
        # `STATUS-through-2026-09-12.md`, `RESULTS-2026-08-28-stance-survives-ablation.md`
        # and `RESULTS-2026-08-30-withdrawal-was-wrong.md`, all of them archived records of
        # what was claimed at the time. Banning a withdrawn sentence there does not correct
        # anything; it falsifies the archive, which is the same offence as rewriting a
        # third-party title to clear a grep.
        #
        # `withdrawn/` is the one directory whose PURPOSE is to hold retired text, and
        # `check_retired_instrument.SKIP_DIRS` already excludes it for exactly this reason.
        # The two gates now agree. The consequence is deliberate and worth stating: moving a
        # document into `withdrawn/` stops its claims being scanned, which is what
        # withdrawing a document means.
        dirs[:] = [d for d in sorted(dirs)
                   if d not in (".git", "__pycache__", ".pytest_cache", "node_modules",
                                ".venv", "venv", "htmlcov", ".mypy_cache", "withdrawn")]
        for fn in sorted(files):
            if not fn.lower().endswith(".md"):
                continue
            path = os.path.join(base, fn)
            rel = os.path.relpath(path, root).replace("\\", "/")
            if root is not STUDY:
                rel = "website/content/" + rel
            try:
                text = io.open(path, encoding="utf-8", newline="").read().replace("\r\n", "\n")
            except (IOError, OSError, UnicodeDecodeError) as exc:
                # A FILE LISTED FOR SCANNING THAT IS NOT SCANNED MUST SAY SO. The silent
                # `continue` is the exact bug that let a markdown file sit in a JSON-only
                # scanner for a day reporting success.
                findings.append((rel, "COULD NOT BE READ, so it was not scanned: %s" % exc, ""))
                continue
            scanned += 1
            # A DATED PRE-REGISTRATION IS A FIXED RECORD, like a document marked superseded.
            # It states what was believed on the day it was committed, before the data
            # existed, and this study's own rule is that it may not be edited afterwards --
            # an amendment is dated and appended, never a silent rewrite. So a withdrawn
            # claim inside one is history by construction, and the only way to "fix" it would
            # be to break the thing that makes a pre-registration worth anything.
            # `check_retired_instrument` already reasons this way about the same files.
            # Routed to `archived`, which is PRINTED rather than dropped, so it stays visible.
            fixed_record = (_is_marked_superseded(text)
                            or re.match(r"^PREREG-\d{4}-\d{2}-\d{2}-", os.path.basename(rel)))
            bucket = archived if fixed_record else findings
            for phrase, why in RETRACTED:
                for occurrence in _unquoted_occurrences(text, phrase):
                    bucket.append((rel, why, occurrence))
    return scanned, findings, archived


#: How far into a document the supersession notice has to appear. A banner below the fold is
#: a banner the reader meets after the withdrawn claim, which is no banner at all.
_SUPERSEDED_WITHIN_LINES = 30


def _is_marked_superseded(text):
    """Is this document declared a historical record at the top of itself?

    AN ARCHIVE IS ALLOWED TO CONTAIN ITS OWN WITHDRAWN CLAIMS -- that is what makes it an
    archive. `results/WRITEUP-2026-05-26.md` opens with "SUPERSEDED -- this is the May 2026
    record, kept as history. Do not cite it." and is then preserved unedited on purpose,
    because rewriting it would destroy the evidence of what was claimed and when.

    What is NOT allowed is a live document asserting a withdrawn claim, and the difference
    between the two is a notice the reader meets FIRST. So the marker must sit in the opening
    lines, not anywhere in the file: a "superseded" mentioned in passing on line 400 would
    otherwise exempt the whole document.
    """
    head = "\n".join(text.split("\n")[:_SUPERSEDED_WITHIN_LINES]).upper()
    return "SUPERSEDED" in head


def check_retractions_everywhere():
    """Print the repo-wide retraction scan. Returns an exit code: 0 clean, 1 defect."""
    scanned, findings, archived = scan_every_document_for_retractions()
    if not scanned:
        # A SCAN THAT OPENED NOTHING MUST NEVER REPORT CLEAN.
        print("RETRACTION SCAN EXAMINED 0 FILES -- this is a defect in the scan, not a pass")
        return 1
    if archived:
        # Reported, never silent: an operator should be able to see that the exemption is
        # doing work and on which files, so a wrongly-bannered live document is visible.
        by_file = sorted({rel for rel, _, _ in archived})
        print("%d occurrence(s) in %d document(s) marked SUPERSEDED at the top, which is what "
              "an archive is for: %s" % (len(archived), len(by_file), ", ".join(by_file)))
    if not findings:
        print("retractions: no withdrawn claim is asserted in any of %d markdown files"
              % scanned)
        return 0
    print("WITHDRAWN CLAIMS ASSERTED -- %d occurrence(s) across %d markdown files"
          % (len(findings), scanned))
    print("A claim this study withdrew is wrong in every file that states it, not just the")
    print("gated ones. Quote it if you are describing the withdrawal; do not assert it.")
    print()
    last = None
    for rel, why, occurrence in findings:
        if rel != last:
            print("  %s" % rel)
            last = rel
        print("    %s" % occurrence)
        print("      WHY: %s" % why)
    return 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check-retractions", action="store_true",
                    help="scan EVERY markdown file for withdrawn claims, not just the nine "
                         "named surfaces. A retraction is repo-wide by nature.")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--check-website", action="store_true",
                    help="do the public research page's numbers still match runs/?")
    ap.add_argument("--check-release", action="store_true",
                    help="does the release repository's README still match runs/?")
    ap.add_argument("--check-books", action="store_true",
                    help="do the printed book numbers still match runs/? A printed number "
                         "cannot be corrected after the fact, so this is the surface where "
                         "drift costs most -- and it was the one nothing checked.")
    ap.add_argument("--check-talk", action="store_true",
                    help="do TALK.md's sentences still match runs/? The talk is what gets "
                         "said to a room; its previous version was written entirely in "
                         "retired denominators and no gate read it.")
    ap.add_argument("--counts", action="store_true",
                    help="the collection's shape, every figure derived and scoped. Quote THIS "
                         "rather than retyping: five model counts and two record counts were "
                         "in circulation across the paper, FINDINGS and the README, each true "
                         "of a scope none of them named.")
    ap.add_argument("--sync-ours", action="store_true",
                    help="rewrite the controls audit's 'ours' scale from runs/ instead of "
                         "retyping it. --check still gates the result.")
    args = ap.parse_args(argv)

    if args.check_retractions:
        # Deliberately before build(): this scan reads prose, not runs/, so it stays usable
        # in a tree where the run data is absent or mid-collection.
        return check_retractions_everywhere()

    rows = build()

    if args.counts:
        c = collection_scale()
        lab = ", ".join("%d %s" % (n, k) for k, n in sorted(c["instrument_labels"].items(),
                                                            key=lambda kv: -kv[1]))
        res = ", ".join("%s on %d" % (k, v) for k, v in sorted(c["models_resolving"].items()))
        print("THE COLLECTION, every figure derived and scoped")
        print("")
        print("  %d records on this instrument: %d in the wave (%d valid, %.0f%%) and %d in"
              % (c["records_total"], c["records_wave"], c["records_valid"],
                 100.0 * c["records_valid"] / max(c["records_wave"], 1), c["records_probe"]))
        print("  the budget probe. %d models were COLLECTED -- the 36-model frozen panel plus"
              % c["models_collected"])
        print("  6 declared requantisation siblings. Contrasts resolve on fewer, because a")
        print("  contrast needs both arms and models refuse different conditions: %s." % res)
        print("  Two instrument labels are present and are one instrument: %s." % lab)
        print("")
        print("  Every number above moves when more data lands. Quote the command, not the")
        print("  digits: `key_numbers.py --counts`.")
        return 0

    if args.sync_ours:
        print(sync_ours_row(rows))
        return 0

    if args.check_release:
        # A RELEASE GATE OVER AN EMPTY CORPUS MUST NOT BE ABLE TO PASS.
        #
        # The mirror's runs/ is empty until a scrubbed export lands, so every corpus-derived
        # number computes as 0 and the gate compares "0 refusals in 0 runs" against the prose.
        # Today that FAILS, because the prose says something else -- but it fails for the wrong
        # reason, and the failure is one edit away from becoming a pass: reconcile the prose to
        # the zeros and the gate goes green having examined nothing.
        #
        # That is this project's signature defect (`feedback_vacuous_pass_gates.md`: print the
        # count, exit 1 on zero), and it was sitting in the gate that decides whether the
        # repository may be published. Refuse explicitly instead, and say what is missing.
        import floor_table as _FT_empty
        if not _FT_empty._tree_has_run_data():
            print("REFUSED -- --check-release ran in a tree with NO runs/ corpus.")
            print("")
            print("  Every corpus-derived number here computes as 0 from an empty directory.")
            print("  Checking those zeros against the prose is not a check: if the prose ever")
            print("  agreed with them, this gate would report the release as verified having")
            print("  read nothing at all.")
            print("")
            print("  Export the scrubbed corpus into runs/ and re-run. A release cannot be")
            print("  verified against a corpus that is not present.")
            return 1

    if args.check_website or args.check_release or args.check_books or args.check_talk:
        failures = []
        # --check-website covers EVERY website surface, not the one page it was written for.
        # Adding a surface to SURFACES and forgetting to add it here would leave it declared and
        # unchecked, which is the same silence as not declaring it -- and is how the dispatch
        # ran a day behind a corrected page.
        asked = present = 0
        for name, wanted in ([(n, args.check_website) for n in SURFACES
                              if n.startswith("website") or n.startswith("dispatch-")]
                             + [("release", args.check_release),
                                ("versioning", args.check_release),
                                # Declared 2026-09-15 and immediately demonstrated the
                                # hazard the comment above describes: the surface was
                                # added to SURFACES, a withdrawn claim was planted in
                                # it to check the gate, and the gate passed -- because
                                # nothing listed it here. Declared and unchecked is the
                                # same silence as not declared.
                                ("adversarial_review", args.check_release),
                                ("talk", args.check_talk)]
                             + [(n, args.check_books) for n in SURFACES
                                if n.startswith("book-")]):
            if wanted:
                asked += 1
                present += os.path.exists(SURFACES[name]["path"])
                failures += [(name,) + f for f in check_surface(name, rows)]

        # THE RELEASE GATE OWNS THE REPO-WIDE RETRACTION SCAN.
        #
        # The per-surface scan above covers nine hand-named documents. A withdrawn claim is
        # wrong in all 93, and on 2026-09-16 one stood in CORPUS-MAP -- not a surface, so
        # never scanned -- four lines above the block withdrawing it. Hanging the sweep off
        # --check-release means the gate that decides whether this repository may be pushed
        # is the gate that reads every document in it, instead of a flag someone has to
        # remember. --check-website does not run it: the website lives in another repository
        # and this walk would examine the wrong tree.
        retraction_code = 0
        if args.check_release:
            print("")
            retraction_code = check_retractions_everywhere()

        # Absent surfaces are the ordinary state in whichever tree does not hold them, and
        # check_surface says so rather than failing. But ALL of them absent means this ran
        # somewhere it cannot check anything, and a green there is the vacuous pass this file
        # already calls worse than a failure forty lines below. It was reachable: the wave
        # skill says to run --check-website, and run from the release mirror it printed four
        # NOT PRESENT lines and exited 0, which reads exactly like "every surface agrees".
        if asked and not present:
            print("")
            print("CHECKED NOTHING -- all %d requested surface(s) are absent from this tree."
                  % asked)
            print("This is not a pass. Run it from the tree that holds the website and")
            print("dispatch sources; the numbers live in a different repository from the")
            print("paper, which is the whole reason this gate exists.")
            # 2 = NOT APPLICABLE, not 1 = FAILED. Both are non-zero, so nothing
            # is being waved through, and the distinction is what stops an
            # operator learning to ignore the exit code: "this tree has no
            # website surfaces" is a correct answer to the question, whereas "a
            # number disagrees with runs/" is a defect. check_no_fork and
            # probe_budget use 2 for the same situation, and a repository whose
            # gates disagree about what a code means teaches nobody anything.
            return 2
        if not failures:
            return retraction_code
        if retraction_code:
            # Both kinds of defect are reported; the exit code says "defect" either way.
            pass
        print("")
        print("CROSS-SURFACE DRIFT -- %d statement(s) disagree with runs/" % len(failures))
        print("These are hand-typed copies of generated numbers, living in a different repo")
        print("from the paper, which is why nobody re-reads them together.")
        print("")
        for surface, key, expected, found in failures:
            print("  [%s] %s" % (surface, key))
            print("    expected: %r" % expected)
            if found:
                print("    surface says: %r" % found)
        return 1

    if not args.check:
        print("KEY NUMBERS -- computed from runs/, and the phrase the paper uses for each")
        print()
        for r in rows:
            # %s, not %d: one entry carries a thousands-formatted string ("1,657"), and %d
            # crashed on it -- so the file's own documented no-argument usage was broken while
            # --check kept working, because --check formats through each entry's own phrase.
            if r["value"] is UNAVAILABLE:
                # Printing the phrase here would render "0 panel models" and read as a
                # measurement of an empty panel. Say what is actually true instead.
                print("  %-14s %5s   %s" % (r["key"], "n/a", r["what"]))
                print("  %-14s       NOT COMPUTABLE IN THIS TREE -- "
                      "data/wave-panel.json is absent" % "")
                continue
            print("  %-14s %5s   %s" % (r["key"], r["value"], r["what"]))
            print("  %-14s       \"%s\"" % ("", r["phrase"] % r["value"]))
        print()
        print("Run --check to verify the paper's prose still says these.")
        return 0

    if not os.path.exists(PAPER):
        # THE PAPER IS NOT DISTRIBUTED IN THE PUBLIC MIRROR, AND THIS USED TO BE A TRACEBACK.
        #
        # `--check` gates the paper's hand-typed sentences against the generated tables. This is
        # one file serving two trees; the paper lives in only one of them, and in the other this
        # crashed with FileNotFoundError on the first command a reader of a reproduction repo
        # would type.
        #
        # Absent is not stale and it is not a pass either. So: say what cannot be checked, run
        # what can -- that repository's own README carries some of the same numbers -- and fail
        # if THAT drifts. Returning 0 having checked nothing would be the vacuous pass this
        # project holds to be worse than a failure.
        print("The paper (%s) is not distributed in this repository, so its prose"
              % os.path.basename(PAPER))
        print("cannot be gated here. Checking this repository's own surfaces instead.")
        print("")
        failures = check_surface("release", rows)
        if failures:
            print("CROSS-SURFACE DRIFT -- %d statement(s) disagree with the run data"
                  % len(failures))
            for f in failures:
                print("  [release] %s" % (" | ".join(str(x) for x in f if x != "")))
            return 1
        print("RELEASE SURFACE: every stated number in README.md agrees with the run data.")
        print("%d generated numbers available; run with no flags to print them all." % len(rows))
        if MISSING_FLOORS:
            # NAMED, not swallowed. A smaller run set means some floor rows have nothing to
            # compute from -- say which, or a reader cannot tell a gate that verified
            # everything from one that verified less.
            print("Not computable in this checkout, so not gated here: %s"
                  % ", ".join(sorted(MISSING_FLOORS)))
        return 0

    text = io.open(PAPER, encoding="utf-8", newline="").read().replace("\r\n", "\n")
    # A CLAIM PHRASE MUST SURVIVE THE LINE WRAP IT WILL BE WRITTEN IN. The paper is
    # hand-wrapped at ~95 columns; a gated phrase longer than the gap to the margin lands
    # across a break and reads as absent. That drives the prose towards satisfying the
    # matcher rather than the reader, which is how sentences end up broken mid-clause. Same
    # unwrap the retraction scan uses, and structural lines are still never joined.
    text = _unwrap_prose(text)
    bad = []
    # A NUMBER THIS TREE CANNOT COMPUTE IS NAMED, NOT FORMATTED INTO A CRASH.
    #
    # This did `r["phrase"] % r["value"]` over every row, and a row whose value is
    # UNAVAILABLE (None) raised `TypeError: %d format: a real number is required` out of
    # main() -- so `--check`, the gate on the paper's prose, DIED rather than reporting.
    # It died on `order_p90_frontier_sitting`, whose sentence quotes the modal sampling
    # error, because `floor_modal_noise` correctly refuses a cache measured on the retired
    # instrument. The right behaviour when an input is absent is to say which input, the
    # way MISSING_FLOORS already does above -- a gate that cannot name what it failed to
    # resolve is worse than one that fails.
    unresolved = []
    for r in rows:
        if r.get("value") is UNAVAILABLE:
            unresolved.append(r)
            continue
        expected = r["phrase"] % r["value"]
        # THE SPELLED ALTERNATIVE, which the SURFACE checker has had since it was written and
        # this one never did. House style spells small numbers, and a paper that opens a
        # clause with "six A-N contrasts" is correctly written -- but a digit-only template
        # can never match it, so the gate reports a sentence that is right as a sentence that
        # is missing. Found 2026-09-23 while registering `evb_an_lost`, whose value is 6.
        #
        # The NUMBER is what is gated; the notation is not. Same rule, same helper, as the
        # surface path -- the two checkers disagreeing about that was the defect.
        if expected not in text:
            spelled = _spell(r["value"])
            alt = (r["phrase"] % spelled) if spelled is not None else None
            if not (alt and alt in text):
                bad.append(r)
    if unresolved:
        print("NOT GATED -- %d number(s) this checkout cannot compute:" % len(unresolved))
        for r in unresolved:
            why = r.get("why_unavailable") or "no value produced in this tree"
            print("  %-28s %s" % (r["key"], why[:96]))
        print("")

    ours_bad = check_ours_row(rows)

    if not bad and not ours_bad:
        print("PROSE CHECK: all %d load-bearing numbers match the paper's sentences," % len(rows))
        print("and the controls audit's own row still describes the corpus it was run on")
        return 0

    if ours_bad:
        print("THE AUDIT'S OWN ROW IS STALE -- %d figure(s)" % len(ours_bad))
        print("This is the defect the paper convicts five other studies of, in our record of it.")
        for what, want, found in ours_bad:
            print("  %s: expected to state %s" % (what, want))
            print("    field says: %r" % found)
        print()
        if not bad:
            return 1

    print("PROSE CHECK FAILED -- %d of %d sentences disagree with the data" % (len(bad), len(rows)))
    print("Either the corpus grew and the prose is stale, or the prose was reworded.")
    print("Both need a human to re-read the sentence; neither is fixed by a find-and-replace.")
    print()
    for r in bad:
        print("  %s (%s)" % (r["key"], r["what"]))
        print("    expected in the paper: \"%s\"" % (r["phrase"] % r["value"]))
        # Show what the paper says instead, if the phrase skeleton is recognisable.
        stem = r["phrase"].split("%d")[0].strip()
        if stem and stem in text:
            i = text.index(stem)
            print("    paper currently says: ...%s..."
                  % " ".join(text[i:i + 90].split()))
        else:
            print("    (phrase not found at all -- the sentence may have been rewritten)")
        print()
    return 1


if __name__ == "__main__":
    sys.exit(main())
