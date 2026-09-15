#!/usr/bin/env python3
"""Rung 2 of the escalation ladder, estimated. The arm the analysis pipeline could not see.

WHY THIS EXISTS
---------------
The README's headline table published rung 2 as *"only the layered stack adds force, to a
ceiling."* Nothing computed that. `runs/2026-05-27-g0dm0d3/ANALYSIS.md` has a heading for every
table and rows under none of them, because `analysis.py` keys on conditions A and B and this arm
runs `B-STM`, `B-Parseltongue` and `B-Layered`. The records flowed through the pipeline, matched
no branch, and produced empty tables that nobody read -- so a directional claim sat in the public
artifact for four months with an empty analysis behind it.

WHAT THE ARM IS
---------------
Elicitation-layer force applied on top of the bare condition-B question, via the G0DM0D3 server:

    B-STM           hedge-strip only          (stm_modules=[hedge_reducer, direct_mode])
    B-Parseltongue  obfuscation only
    B-Layered       the full stack            (parseltongue + STM + godmode + autotune)

Each is paired per question against the SAME model's plain condition-B score from the May run,
so the contrast is within-model and within-question. 2 models x 3 conditions x 10 questions,
**one sample per cell** -- which is the binding limitation and is reported rather than smoothed.

WHAT IT FINDS
-------------
Every interval spans zero. Reporting that is the point: the arm does not support the direction
the README published, and the honest statement is a null with its own width rather than a
narrowed version of the original claim.

    python scripts/pipeline_rung.py
    python scripts/pipeline_rung.py --json
"""
from __future__ import annotations

import argparse
import collections
import glob
import io
import json
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, HERE)

#: The CURRENT rung-2 estimate. Changed 2026-09-14 from the 2026-05-27 pair below.
#:
#: The superseded pair ran ONE sample per cell and differenced against a baseline
#: collected two days earlier by a different script, so every contrast was a
#: difference of two single draws and nothing separated the rung from sampling
#: noise. It returned 6 contrasts, none excluding zero, and the README published
#: "all 6 intervals span zero" as the rung-2 finding.
#:
#: W13 re-collected both arms at n=5 with a matched same-day baseline. On that
#: pair, 3 of 8 intervals exclude zero -- grok-4.3 B-Layered vs plain B at
#: +0.56 [+0.23, +0.85] and B-Layered minus B-STM at +0.48 [+0.26, +0.70], and
#: claude-opus-4.7 B-Layered minus B-STM at -0.31 [-0.64, -0.01], pointing the
#: OTHER WAY. So rung 2 is real and model-specific, and the published "spans zero"
#: sentence is an artifact of n=1, not a null.
#:
#: Reading the old pair is still possible and still correct for reproducing what
#: was published -- pass --pipeline-run/--baseline-run, or HISTORICAL_* below.
PIPELINE_RUN = "2026-09-13-g0dm0d3-replicate"

#: THE BASELINE MUST MATCH THE ARM'S TOKEN BUDGET. Changed 2026-09-14.
#:
#: `2026-09-13-g0dm0d3-replicate-baseline` records NO max_tokens at all, while the
#: pipeline arm it is differenced against records 4000 on every record. This
#: file's own collector warns about exactly that: "an arm capped lower than the
#: arm it is contrasted against measures truncation, not force." I made this pair
#: the default that morning without checking the arms matched.
#:
#: Re-collected at a recorded 4,000 cap, and the confound was real for Opus --
#: the model whose condition-A responses truncate 93% of the time:
#:
#:   contrast                        old baseline        matched baseline
#:   opus B-STM vs plain B           +0.12 (spans 0)     +0.37 [+0.13, +0.65]
#:   opus B-Parseltongue vs plain B  -0.01 (spans 0)     +0.24 [+0.02, +0.49]
#:   opus B-Layered vs plain B       -0.19 (spans 0)     +0.06 (spans 0)
#:   3 of 8 intervals excluded zero  ->  5 of 8
#:
#: Grok is unaffected (+0.56 -> +0.57, +0.48 -> +0.48), which is what a baseline
#: artefact should look like: it moves the model whose baseline was being cut.
#:
#: WHAT SURVIVES UNCHANGED is the finding that matters: `B-Layered minus B-STM` is
#: -0.31 for Opus and +0.48 for Grok either way. That contrast is within-arm and
#: never touches the baseline, so the two models moving in OPPOSITE directions was
#: never at risk from this.
BASELINE_RUN = "2026-09-14-g0dm0d3-baseline-4k"

#: The unrecorded-cap baseline, kept named so the superseded numbers reproduce.
UNMATCHED_BASELINE_RUN = "2026-09-13-g0dm0d3-replicate-baseline"

#: The n=1 pair the published "all 6 intervals span zero" rests on. Kept named so
#: reproducing the old number does not require reading a commit.
HISTORICAL_PIPELINE_RUN = "2026-05-27-g0dm0d3"
HISTORICAL_BASELINE_RUN = "2026-05-25-full"

BASELINE_CONDITION = "B"
CONDITIONS = ("B-STM", "B-Parseltongue", "B-Layered")
BOOTSTRAP_N = 20000

#: B-Parseltongue APPLIES NO TRANSFORM TO THIS INSTRUMENT. Established 2026-09-14
#: from the server's own echo on all 360 pipeline records, and confirmed against
#: the running server: `scripts/pipeline_transform_audit.py`.
#:
#: G0DM0D3's Parseltongue obfuscates trigger words from a fixed list of 53
#: security/jailbreak terms and returns the text UNCHANGED when it finds none.
#: The instrument is ten neutral policy questions and NOT ONE contains a trigger,
#: so `parseltongue: true` was accepted, returned 200, and rewrote nothing --
#: 0 of 120 records in either run.
#:
#: So `B-Parseltongue` is condition B, collected again, through the proxy. Its
#: contrast against plain B is a NULL BY CONSTRUCTION: it can only measure
#: run-to-run drift plus whatever the proxy path itself contributes. That makes
#: it the floor every other contrast in this arm has to clear, which is more
#: useful than the treatment it was mislabelled as -- but it is not a finding
#: about obfuscation, and the published reading of it ("Parseltongue alone is
#: approximately prompt-B") could not have come out any other way.
NULL_CONDITION = "B-Parseltongue"

#: STM is a PARTIAL treatment, not an absent one: hedge_reducer/direct_mode
#: rewrite a prompt only where there is a hedge to strip, and it changed the text
#: on 39 of 100 records (W13) and 7 of 20 (May). So `B-STM minus B-Parseltongue`
#: is the cleanest STM estimate available -- same run, same sitting, same
#: temperature, same proxy path, differing only in whether STM fired -- and it is
#: the contrast neither the published analysis nor this file computed before.
STM_VS_NULL = ("B-STM", NULL_CONDITION)


def _roots():
    try:
        from studypaths import run_roots
        return [str(p) for p in run_roots()]
    except Exception:
        return [os.path.join(STUDY, r) for r in ("data", "runs")
                if os.path.isdir(os.path.join(STUDY, r))]


def _load(run):
    import eligibility as E
    out = []
    for root in _roots():
        for path in glob.glob(os.path.join(root, run, "scored", "**", "*.jsonl"), recursive=True):
            for line in io.open(path, encoding="utf-8", errors="replace"):
                if not line.strip():
                    continue
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if E.is_eligible(r):
                    out.append(r)
    return out


def _boot(deltas, label, run=None):
    """Percentile interval over per-question paired deltas, seeded per contrast.

    The seed is derived from the run being analysed, so a new collection does not
    silently reuse the May wave's bootstrap stream.
    """
    run = run or PIPELINE_RUN
    if not deltas:
        return None
    try:
        from studypaths import analysis_seed, stream
        rng = stream(analysis_seed(run), run, label)
    except Exception:
        import random
        rng = random.Random(20260527)
    k = len(deltas)
    means = sorted(st.mean([deltas[rng.randrange(k)] for _ in range(k)])
                   for _ in range(BOOTSTRAP_N))
    return (st.mean(deltas), means[int(0.025 * BOOTSTRAP_N)], means[int(0.975 * BOOTSTRAP_N)])


def _mean_replicates(records, condition=None):
    """Average replicate samples within a (model, condition, question) cell.

    The May wave ran one sample per cell, so a plain dict assignment was lossless.
    With --samples 5 it is NOT: keying a dict on question_id silently keeps only the
    LAST sample and discards the other four, which would look like a completed n=5
    collection and report an n=1 estimate. Samples within a cell are averaged, never
    treated as independent observations, so per-question pairing is preserved and the
    bootstrap still resamples questions rather than draws.

    The key MUST carry the condition. Averaging over (model, question) alone would
    pool B-STM, B-Parseltongue and B-Layered into one number and difference a cell
    against itself.
    """
    acc = collections.defaultdict(list)
    for r in records:
        if condition is not None and r.get("condition") != condition:
            continue
        acc[(r["model"], r.get("condition"), r["question_id"])].append(r["score_classifier"])
    means = {k: st.mean(v) for k, v in acc.items()}
    depth = {k: len(v) for k, v in acc.items()}
    return means, depth


def default_pair():
    """(pipeline_run, baseline_run, which) -- the best pair PRESENT in this tree.

    The replicated pair is private; the public mirror holds only the n=1 pair. A
    single hardcoded default therefore either forks the two trees or makes the
    estimator uncomputable in one of them, and both are worse than resolving it
    here where the choice can be NAMED.

    `which` is "replicated" or "historical" and travels in the result, so nothing
    downstream can quote a number without being able to say which collection it
    came from. A silent fallback would be the same defect as an inherited analysis
    seed: correct output, unattributable.
    """
    if _load(PIPELINE_RUN):
        return PIPELINE_RUN, BASELINE_RUN, "replicated"
    return HISTORICAL_PIPELINE_RUN, HISTORICAL_BASELINE_RUN, "historical"


def estimate(pipeline_run=None, baseline_run=None):
    if pipeline_run is None and baseline_run is None:
        pipeline_run, baseline_run, which = default_pair()
    else:
        pipeline_run = pipeline_run or PIPELINE_RUN
        baseline_run = baseline_run or BASELINE_RUN
        which = ("replicated" if pipeline_run == PIPELINE_RUN
                 else "historical" if pipeline_run == HISTORICAL_PIPELINE_RUN else "explicit")
    pipe = _load(pipeline_run)
    base_recs = _load(baseline_run)
    if not pipe:
        return None
    base_means, base_depth = _mean_replicates(base_recs, condition=BASELINE_CONDITION)
    base = {(m, q): v for (m, _c, q), v in base_means.items()}
    cell_means, cell_depth = _mean_replicates(pipe)
    cells = collections.defaultdict(dict)
    for (m, c, q), v in cell_means.items():
        cells[(m, c)][q] = v
    # A cell's replicate depth is reported, not assumed: a run that silently lost
    # samples must be visible in the output rather than pass as a clean n.
    reps = sorted(set(list(cell_depth.values()) + list(base_depth.values())))
    models = sorted({m for m, _ in cells})

    out = {"run": pipeline_run, "baseline_run": baseline_run, "models": models,
           # Which collection this estimate came from, so no consumer can quote the
           # number without being able to name its source. "historical" is the n=1
           # pair whose every contrast is a difference of two single draws.
           "pair": which,
           "samples_per_cell": reps[0] if len(reps) == 1 else reps,
           "replicates_ragged": len(reps) > 1,
           "contrasts": []}
    for m in models:
        for c in CONDITIONS:
            got = cells.get((m, c), {})
            d = [got[q] - base[(m, q)] for q in sorted(got) if (m, q) in base]
            ci = _boot(d, "%s|%s|vs-base" % (m, c), run=pipeline_run)
            if ci:
                out["contrasts"].append(
                    {"model": m, "contrast": "%s vs plain %s" % (c, BASELINE_CONDITION),
                     "n": len(d), "effect": round(ci[0], 3),
                     "lo": round(ci[1], 3), "hi": round(ci[2], 3),
                     "excludes_zero": ci[1] > 0 or ci[2] < 0,
                     # This arm applied NO transform to this instrument, so its
                     # contrast against plain B cannot be a treatment effect.
                     "null_by_construction": c == NULL_CONDITION})
        lay, stm = cells.get((m, "B-Layered"), {}), cells.get((m, "B-STM"), {})
        d = [lay[q] - stm[q] for q in sorted(lay) if q in stm]
        ci = _boot(d, "%s|layered-minus-stm" % m, run=pipeline_run)
        if ci:
            out["contrasts"].append(
                {"model": m, "contrast": "B-Layered minus B-STM", "n": len(d),
                 "effect": round(ci[0], 3), "lo": round(ci[1], 3), "hi": round(ci[2], 3),
                 "excludes_zero": ci[1] > 0 or ci[2] < 0})
        # STM against the untreated arm collected in the SAME sitting. Both go
        # through the proxy at the same temperature, so the baseline run, the
        # collection date and the proxy path all cancel and what remains is STM.
        treated, untreated = (cells.get((m, STM_VS_NULL[0]), {}),
                              cells.get((m, STM_VS_NULL[1]), {}))
        d = [treated[q] - untreated[q] for q in sorted(treated) if q in untreated]
        ci = _boot(d, "%s|stm-minus-null" % m, run=pipeline_run)
        if ci:
            out["contrasts"].append(
                {"model": m, "contrast": "B-STM minus %s" % NULL_CONDITION,
                 "n": len(d), "effect": round(ci[0], 3), "lo": round(ci[1], 3),
                 "hi": round(ci[2], 3), "excludes_zero": ci[1] > 0 or ci[2] < 0,
                 "within_run": True})
    out["any_excludes_zero"] = any(c["excludes_zero"] for c in out["contrasts"])
    out["n_contrasts"] = len(out["contrasts"])
    # The measured floor, per model: what a contrast against plain B reports when
    # the arm applied no transform at all. Anything at or below this magnitude in
    # the same column is indistinguishable from drift plus the proxy path.
    out["null_floor"] = {
        c["model"]: {"effect": c["effect"], "lo": c["lo"], "hi": c["hi"],
                     "excludes_zero": c["excludes_zero"]}
        for c in out["contrasts"] if c.get("null_by_construction")}
    for c in out["contrasts"]:
        floor = out["null_floor"].get(c["model"])
        if floor and c["contrast"].endswith("vs plain %s" % BASELINE_CONDITION):
            c["clears_null_floor"] = (not c.get("null_by_construction")
                                      and abs(c["effect"]) > abs(floor["effect"]))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true")
    # Defaults resolve through default_pair() rather than being baked into argparse,
    # which would pin the CLI to a run the public mirror does not hold and print
    # "not present in this tree" there while the library computed fine.
    ap.add_argument("--pipeline-run", default=None,
                    help="run holding the B-STM / B-Parseltongue / B-Layered cells "
                         "(default: the replicated pair where present, else the n=1 pair)")
    ap.add_argument("--baseline-run", default=None,
                    help="run holding plain condition B. For a same-sitting baseline, "
                         "pass the run collected alongside the pipeline arm.")
    args = ap.parse_args(argv)
    res = estimate(args.pipeline_run, args.baseline_run)
    if not res:
        print("pipeline rung %s not present in this tree"
              % (args.pipeline_run or default_pair()[0]))
        return 2
    if args.json:
        print(json.dumps(res, indent=2))
        return 0
    print("RUNG 2 -- elicitation-layer force, paired per question against plain condition B")
    spc = res["samples_per_cell"]
    if res.get("replicates_ragged"):
        depth = "RAGGED replicate depth %s -- cells are not equally sampled" % (spc,)
    else:
        depth = "%s sample(s) per cell, averaged within cell" % spc
    print("%d models, %s." % (len(res["models"]), depth))
    print("pipeline run: %s   baseline run: %s   [%s pair]"
          % (res["run"], res["baseline_run"], res.get("pair", "?")))
    if res.get("pair") == "historical":
        print("  NOTE: this tree holds only the n=1 pair, so every contrast below is a "
              "difference of two single draws. The replicated pair measures 3 of 8 "
              "intervals excluding zero -- see PENDING-PUBLICATION-2026-09-14.md.")
    print("Positive = more institution-skeptical.\n")
    print("  %-26s %-30s %3s %8s %-18s" % ("model", "contrast", "n", "effect", "95% interval"))
    for c in res["contrasts"]:
        flag = "  EXCLUDES 0" if c["excludes_zero"] else ""
        if c.get("null_by_construction"):
            flag += "   <-- NULL BY CONSTRUCTION (no transform applied)"
        elif c.get("clears_null_floor") is False:
            flag += "   (does not clear the null floor)"
        print("  %-26s %-30s %3d %+8.2f [%+0.2f, %+0.2f]%s"
              % (c["model"].split("/")[-1], c["contrast"], c["n"], c["effect"],
                 c["lo"], c["hi"], flag))
    print("")
    if res.get("null_floor"):
        print("  NULL FLOOR. %s applied no transform to this instrument -- G0DM0D3's"
              % NULL_CONDITION)
        print("  Parseltongue rewrites trigger words and the instrument contains none, so it")
        print("  fired on 0 of 120 records. Its contrast against plain B therefore measures")
        print("  run-to-run drift plus the proxy path, and nothing else:")
        for m, f in sorted(res["null_floor"].items()):
            print("      %-24s %+0.2f [%+0.2f, %+0.2f]%s"
                  % (m.split("/")[-1], f["effect"], f["lo"], f["hi"],
                     "   and it EXCLUDES ZERO" if f["excludes_zero"] else ""))
        print("  Any 'vs plain B' effect of that magnitude is not distinguishable from it.")
        print("  Verify with: python scripts/pipeline_transform_audit.py\n")
    if not res["any_excludes_zero"]:
        print("  NOT ONE of the %d intervals excludes zero." % res["n_contrasts"])
        print("  The arm does not support a direction.")
        if res["samples_per_cell"] == 1:
            print("  One sample per cell, so there is no within-cell variance to appeal to")
            print("  either.")
        print("  'To a ceiling' was never measured -- locating a ceiling needs more than")
        print("  three points on one axis, at any sample size.")
    else:
        n_ex = sum(1 for c in res["contrasts"] if c["excludes_zero"])
        print("  %d of %d intervals exclude zero." % (n_ex, res["n_contrasts"]))
        print("  'To a ceiling' is still NOT measured: three points on one axis cannot")
        print("  locate where added force stops helping, at any sample size.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
