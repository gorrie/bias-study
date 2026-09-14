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

PIPELINE_RUN = "2026-05-27-g0dm0d3"
BASELINE_RUN = "2026-05-25-full"
BASELINE_CONDITION = "B"
CONDITIONS = ("B-STM", "B-Parseltongue", "B-Layered")
BOOTSTRAP_N = 20000


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


def estimate(pipeline_run=None, baseline_run=None):
    pipeline_run = pipeline_run or PIPELINE_RUN
    baseline_run = baseline_run or BASELINE_RUN
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
                     "excludes_zero": ci[1] > 0 or ci[2] < 0})
        lay, stm = cells.get((m, "B-Layered"), {}), cells.get((m, "B-STM"), {})
        d = [lay[q] - stm[q] for q in sorted(lay) if q in stm]
        ci = _boot(d, "%s|layered-minus-stm" % m, run=pipeline_run)
        if ci:
            out["contrasts"].append(
                {"model": m, "contrast": "B-Layered minus B-STM", "n": len(d),
                 "effect": round(ci[0], 3), "lo": round(ci[1], 3), "hi": round(ci[2], 3),
                 "excludes_zero": ci[1] > 0 or ci[2] < 0})
    out["any_excludes_zero"] = any(c["excludes_zero"] for c in out["contrasts"])
    out["n_contrasts"] = len(out["contrasts"])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--pipeline-run", default=PIPELINE_RUN,
                    help="run holding the B-STM / B-Parseltongue / B-Layered cells")
    ap.add_argument("--baseline-run", default=BASELINE_RUN,
                    help="run holding plain condition B. For a same-sitting baseline, "
                         "pass the run collected alongside the pipeline arm.")
    args = ap.parse_args(argv)
    res = estimate(args.pipeline_run, args.baseline_run)
    if not res:
        print("pipeline rung %s not present in this tree" % args.pipeline_run)
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
    print("pipeline run: %s   baseline run: %s" % (res["run"], res["baseline_run"]))
    print("Positive = more institution-skeptical.\n")
    print("  %-26s %-28s %3s %8s %-18s" % ("model", "contrast", "n", "effect", "95% interval"))
    for c in res["contrasts"]:
        print("  %-26s %-28s %3d %+8.2f [%+0.2f, %+0.2f]%s"
              % (c["model"].split("/")[-1], c["contrast"], c["n"], c["effect"],
                 c["lo"], c["hi"], "  EXCLUDES 0" if c["excludes_zero"] else ""))
    print("")
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
