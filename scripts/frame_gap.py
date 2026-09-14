#!/usr/bin/env python3
"""Does the judged instrument measure a POSITION, or agreement with the FRAME?

The estimator for PREREG-2026-09-13-frame-and-placebo. Written before the data
landed, so it cannot be tuned to the result.

THE QUESTION
------------
The judged score is 1-5, deference to skepticism. Three explanations of the
published A->B effect are currently indistinguishable:

  position          a lean exists and the fairness instruction masks it
  frame-following   the model agrees with whoever is asking, and all 30
                    published items ask from the critic's side
  instruction       "do not take a position" produces the rubric's 3, and
                    asking for an opinion produces something else

The corpus cannot separate them: every main-run item is critic-framed, and 94%
of eligible condition-A records score exactly 3 (239 of 255) because condition A
instructs the answer the rubric defines as 3.

WHAT THIS COMPUTES
------------------
FRAME GAP, per model, per condition:

    frame_gap = mean(score | critic-framed) - mean(score | institution-framed)

paired by topic -- T01-Q2 against T01-Q4 and so on -- with replicates averaged
within cell before differencing, bootstrapped over the 10 topic pairs.

    LARGE POSITIVE GAP  the instrument reads the FRAME. The model looks skeptical
                        asked from the critic's side and deferential asked from
                        the institution's side, which is one behaviour, not a lean.
    GAP NEAR ZERO       and a real A->B' shift: the instrument reads a POSITION
                        that survives being asked from either direction.

CONDITION CONTRASTS
-------------------
    B  - A    the published effect. Confounds two changes.
    B' - A    the instruction removed WITHOUT asking for an opinion.
    P  - A    a forceful instruction carrying NO stance content.
    B  - B'   what asking "what do you think?" is worth on its own.

If P - A is most of B - A, the effect is instruction-following, and the judged
arm reproduces what the forced-choice arm already found: "anything removes it ...
Nothing is revealed; a suppression stops."

    python scripts/frame_gap.py 2026-09-13-frame-placebo
    python scripts/frame_gap.py <run> --json

Reads only. No API calls.
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import eligibility as E  # noqa: E402

BOOTSTRAP_N = 20000
#: Which position label is which side of the frame.
CRITIC = "neutral"        # T*-Q2, the published critic-framed set
INSTITUTION = "reversed"  # T*-Q4, the institution-framed mirror


def load(run):
    rows = []
    roots = ["runs", "data"]
    for root in roots:
        for p in sorted(glob.glob(os.path.join(root, run, "scored", "**", "*.jsonl"),
                                  recursive=True)):
            for line in open(p, encoding="utf-8", errors="replace"):
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    pass
    return rows


def _boot(values, label, run):
    """Percentile interval over the paired topic values, seeded per contrast."""
    if not values:
        return None
    try:
        from studypaths import analysis_seed, stream
        rng = stream(analysis_seed(run), run, label)
    except Exception:
        import random
        rng = random.Random(20260913)
    k = len(values)
    means = sorted(st.mean([values[rng.randrange(k)] for _ in range(k)])
                   for _ in range(BOOTSTRAP_N))
    return (st.mean(values), means[int(0.025 * BOOTSTRAP_N)],
            means[int(0.975 * BOOTSTRAP_N)])


def cell_means(rows):
    """(model, condition, position, topic) -> mean score over eligible replicates."""
    acc = collections.defaultdict(list)
    for r in rows:
        if not E.is_eligible(r):
            continue
        acc[(r.get("model"), r.get("condition"), r.get("position"),
             r.get("topic"))].append(r["score_classifier"])
    return {k: st.mean(v) for k, v in acc.items()}, {k: len(v) for k, v in acc.items()}


def analyse(run):
    rows = load(run)
    if not rows:
        return None
    means, depth = cell_means(rows)
    models = sorted({m for (m, _c, _p, _t) in means})
    conditions = sorted({c for (_m, c, _p, _t) in means})

    out = {"run": run, "models": models, "conditions": conditions,
           "n_records": len(rows), "frame_gaps": [], "condition_contrasts": [],
           "replicate_depths": sorted(set(depth.values()))}

    # --- FRAME GAP, paired by topic --------------------------------------
    for m in models:
        for c in conditions:
            topics = sorted({t for (mm, cc, pp, t) in means
                             if mm == m and cc == c and pp == CRITIC})
            pairs = []
            for t in topics:
                a = means.get((m, c, CRITIC, t))
                b = means.get((m, c, INSTITUTION, t))
                if a is not None and b is not None:
                    pairs.append(a - b)
            ci = _boot(pairs, "framegap|%s|%s" % (m, c), run)
            if ci:
                out["frame_gaps"].append(
                    {"model": m, "condition": c, "n_topics": len(pairs),
                     "gap": round(ci[0], 3), "lo": round(ci[1], 3), "hi": round(ci[2], 3),
                     "excludes_zero": ci[1] > 0 or ci[2] < 0})

    # --- CONDITION CONTRASTS, paired by (position, topic) ----------------
    for m in models:
        for lo_c, hi_c in (("A", "B"), ("A", "B-prime"), ("A", "P"), ("B-prime", "B")):
            if lo_c not in conditions or hi_c not in conditions:
                continue
            keys = sorted({(p, t) for (mm, cc, p, t) in means
                           if mm == m and cc == lo_c})
            deltas = []
            for (p, t) in keys:
                a = means.get((m, lo_c, p, t))
                b = means.get((m, hi_c, p, t))
                if a is not None and b is not None:
                    deltas.append(b - a)
            ci = _boot(deltas, "cond|%s|%s-%s" % (m, hi_c, lo_c), run)
            if ci:
                out["condition_contrasts"].append(
                    {"model": m, "contrast": "%s - %s" % (hi_c, lo_c), "n": len(deltas),
                     "effect": round(ci[0], 3), "lo": round(ci[1], 3), "hi": round(ci[2], 3),
                     "excludes_zero": ci[1] > 0 or ci[2] < 0})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("run")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    res = analyse(a.run)
    if res is None:
        print("CHECKED NOTHING -- no scored records for %r. This is NOT a result."
              % a.run, file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps(res, indent=2))
        return 0

    print("FRAME GAP -- does the instrument read a position, or the frame?")
    print("run: %s   %d scored records   replicate depth %s"
          % (res["run"], res["n_records"], res["replicate_depths"]))
    print("gap = critic-framed mean - institution-framed mean, paired by topic.")
    print("A LARGE POSITIVE GAP MEANS THE INSTRUMENT IS READING THE FRAME.")
    print("")
    print("  %-26s %-9s %3s %8s %-18s" % ("model", "condition", "n", "gap", "95% interval"))
    for g in res["frame_gaps"]:
        print("  %-26s %-9s %3d %+8.2f [%+0.2f, %+0.2f]%s"
              % (g["model"].split("/")[-1], g["condition"], g["n_topics"], g["gap"],
                 g["lo"], g["hi"], "  READS THE FRAME" if g["excludes_zero"] and g["gap"] > 0
                 else ""))
    print("")
    print("CONDITION CONTRASTS -- what is actually doing the work")
    print("  %-26s %-16s %3s %8s %-18s" % ("model", "contrast", "n", "effect", "95% interval"))
    for c in res["condition_contrasts"]:
        print("  %-26s %-16s %3d %+8.2f [%+0.2f, %+0.2f]%s"
              % (c["model"].split("/")[-1], c["contrast"], c["n"], c["effect"],
                 c["lo"], c["hi"], "  EXCLUDES 0" if c["excludes_zero"] else ""))
    print("")
    print("READ IT LIKE THIS:")
    print("  P - A close to B - A    the effect is INSTRUCTION-FOLLOWING. Any forceful")
    print("                          instruction does it, and no lean was unmasked.")
    print("  B - B' large            asking for an opinion is doing the work, not")
    print("                          removing the fairness instruction.")
    print("  frame gap large         the score tracks who is asking, not a position.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
