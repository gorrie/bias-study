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


def _boot(deltas, label):
    """Percentile interval over per-question paired deltas, seeded per contrast."""
    if not deltas:
        return None
    try:
        from studypaths import analysis_seed, stream
        rng = stream(analysis_seed(PIPELINE_RUN), PIPELINE_RUN, label)
    except Exception:
        import random
        rng = random.Random(20260527)
    k = len(deltas)
    means = sorted(st.mean([deltas[rng.randrange(k)] for _ in range(k)])
                   for _ in range(BOOTSTRAP_N))
    return (st.mean(deltas), means[int(0.025 * BOOTSTRAP_N)], means[int(0.975 * BOOTSTRAP_N)])


def estimate():
    pipe = _load(PIPELINE_RUN)
    base_recs = _load(BASELINE_RUN)
    if not pipe:
        return None
    base = {(r["model"], r["question_id"]): r["score_classifier"]
            for r in base_recs if r.get("condition") == BASELINE_CONDITION}
    cells = collections.defaultdict(dict)
    for r in pipe:
        cells[(r["model"], r["condition"])][r["question_id"]] = r["score_classifier"]
    models = sorted({m for m, _ in cells})

    out = {"run": PIPELINE_RUN, "baseline_run": BASELINE_RUN, "models": models,
           "samples_per_cell": 1, "contrasts": []}
    for m in models:
        for c in CONDITIONS:
            got = cells.get((m, c), {})
            d = [got[q] - base[(m, q)] for q in sorted(got) if (m, q) in base]
            ci = _boot(d, "%s|%s|vs-base" % (m, c))
            if ci:
                out["contrasts"].append(
                    {"model": m, "contrast": "%s vs plain %s" % (c, BASELINE_CONDITION),
                     "n": len(d), "effect": round(ci[0], 3),
                     "lo": round(ci[1], 3), "hi": round(ci[2], 3),
                     "excludes_zero": ci[1] > 0 or ci[2] < 0})
        lay, stm = cells.get((m, "B-Layered"), {}), cells.get((m, "B-STM"), {})
        d = [lay[q] - stm[q] for q in sorted(lay) if q in stm]
        ci = _boot(d, "%s|layered-minus-stm" % m)
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
    args = ap.parse_args(argv)
    res = estimate()
    if not res:
        print("pipeline rung %s not present in this tree" % PIPELINE_RUN)
        return 2
    if args.json:
        print(json.dumps(res, indent=2))
        return 0
    print("RUNG 2 -- elicitation-layer force, paired per question against plain condition B")
    print("%d models, one sample per cell. Positive = more institution-skeptical.\n" % len(res["models"]))
    print("  %-26s %-28s %3s %8s %-18s" % ("model", "contrast", "n", "effect", "95% interval"))
    for c in res["contrasts"]:
        print("  %-26s %-28s %3d %+8.2f [%+0.2f, %+0.2f]%s"
              % (c["model"].split("/")[-1], c["contrast"], c["n"], c["effect"],
                 c["lo"], c["hi"], "  EXCLUDES 0" if c["excludes_zero"] else ""))
    print("")
    if not res["any_excludes_zero"]:
        print("  NOT ONE of the %d intervals excludes zero." % res["n_contrasts"])
        print("  The arm does not support a direction. One sample per cell, so there is no")
        print("  within-cell variance to appeal to either, and 'to a ceiling' was never")
        print("  measured -- locating a ceiling needs more than three points on one axis.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
