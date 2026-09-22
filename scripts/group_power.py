#!/usr/bin/env python3
"""What could a between-GROUP comparison on this panel detect? Asked BEFORE any effect.

WHY THIS EXISTS, AND WHY IT RUNS FIRST
--------------------------------------
The corpus carries several model-level attributes -- release vintage, serving path, vendor,
jurisdiction, weight modification -- and 63 models with positions. That is a garden of forking
paths: pick an attribute, pick a condition, pick a metric, and something will look
interesting. This project's own standard forbids that twice over: *"a null with no MDE is a
sample size, not a finding"* (LEARNINGS #14, `null_audit.py`), and the pre-registration
discipline exists precisely so the comparison is chosen before the answer is visible.

So this tool reports **only** group sizes and minimum detectable effects. It deliberately does
NOT compute a single group difference. Read it, decide which comparisons the panel can
actually answer, write those down, and then run them.

The MDE is computed the same way `null_audit.py` does it -- non-parametrically, by shifting
the observed between-model spread and finding the smallest shift that clears the reference at
80% power -- because a parametric MDE would assume a shape this panel does not have.

**THE UNIT IS THE MODEL.** A group of 12 models at depth 5 is 60 sheets and TWELVE
independent observations. Quoting 60 is the pseudoreplication this project killed a
substitution pass for.

    python scripts/group_power.py
    python scripts/group_power.py --condition N --json
"""
from __future__ import annotations

import argparse
import collections
import io
import json
import os
import random
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import position_analysis as P                                      # noqa: E402
from studypaths import run_path                                   # noqa: E402

WAVE = "2026-09-16-ratchet-v3-wave"
POWER = 0.80
ALPHA = 0.05
DRAWS = 2000

#: Minimum models per side. Below this a "group difference" is a handful of models and the
#: honest report is the models, not a statistic over them.
MIN_PER_SIDE = 5


def attributes(models):
    """Model-level attributes, from the recorded sources. Never inferred from a name."""
    path = os.path.join(STUDY, "data", "model-vintage.json")
    vintage = json.load(io.open(path, encoding="utf-8"))["models"]
    out = {}
    for m in models:
        e = vintage.get(m) or {}
        vendor = m.split("/")[0] if "/" in m else m.split(":")[0]
        out[m] = {
            "vintage": e.get("band"),
            "served": e.get("served"),
            "vendor": vendor,
            # Weight-modified builds announce themselves in the repo path. This is a NAME
            # test and is therefore only used for a grouping whose members are all local
            # community builds -- it is not evidence about anything else.
            "weights": ("modified" if any(t in m.lower() for t in
                                          ("ablit", "obliterat", "heretic", "uncensored"))
                        else "stock" if e.get("served") else None),
        }
    return out


def mde(values_a, values_b, seed=20260919, draws=DRAWS, power=POWER, alpha=ALPHA):
    """Smallest true difference detectable at `power`, by shifting group B and resampling.

    Non-parametric and clustered on the MODEL, which is the exchangeable unit here.
    """
    if len(values_a) < 2 or len(values_b) < 2:
        return None
    rng = random.Random(seed)
    spread = st.pstdev(values_a + values_b) or 1e-9

    # CENTRED FIRST. An MDE is "if the true difference were delta, would we see it" -- a
    # question asked UNDER THE NULL. Resampling the groups as observed smuggles the difference
    # they already have into the power calculation: if they differ, the test rejects at
    # delta=0 more than 80% of the time and the bisection collapses to ~0.
    #
    # That is not a hypothetical. The first version of this reported the vintage comparison
    # (2024-or-earlier vs 2026, n=12/40) as **MDE 0.000 position points** while a LARGER
    # comparison (hosted vs local, n=44/11) reported 0.430. An MDE that shrinks as the effect
    # grows is measuring the effect, not the detection limit, and 0.000 would have been
    # published as "this panel can detect any vintage difference at all".
    mean_a, mean_b = st.mean(values_a), st.mean(values_b)
    centred_a = [x - mean_a for x in values_a]
    centred_b = [x - mean_b for x in values_b]

    def detects(delta):
        hit = 0
        for _ in range(draws):
            a = [centred_a[rng.randrange(len(centred_a))] for _ in centred_a]
            b = [centred_b[rng.randrange(len(centred_b))] + delta for _ in centred_b]
            # Two-sided percentile test on the difference of means, at alpha.
            diff = st.mean(b) - st.mean(a)
            se = (st.pstdev(a) ** 2 / len(a) + st.pstdev(b) ** 2 / len(b)) ** 0.5 or 1e-9
            if abs(diff) / se > 1.96:
                hit += 1
        return hit / float(draws)

    lo, hi = 0.0, max(4.0 * spread, 0.5)
    if detects(hi) < power:
        return None
    for _ in range(18):
        mid = (lo + hi) / 2
        if detects(mid) >= power:
            hi = mid
        else:
            lo = mid
    return hi


def survey(condition="N", run_dir=WAVE):
    bank = P.load_bank()
    idx = P.pair_index(bank)
    recs = [r for r in P.load_records(str(run_path(run_dir)))
            if r.get("condition") == condition]
    pos, _cons = P.cell_positions(recs, idx)

    # One position per MODEL: the mean over its pairs. The model is the unit.
    per_model = collections.defaultdict(list)
    for (m, _c, _p), v in pos.items():
        per_model[m].append(v)
    per_model = {m: st.mean(v) for m, v in per_model.items() if v}

    attrs = attributes(list(per_model))
    out = {"condition": condition, "models_with_position": len(per_model), "groupings": []}

    for key in ("vintage", "served", "weights", "vendor"):
        buckets = collections.defaultdict(list)
        missing = 0
        for m, val in per_model.items():
            g = attrs[m].get(key)
            if g is None:
                missing += 1
                continue
            buckets[g].append(val)
        usable = {g: v for g, v in buckets.items() if len(v) >= MIN_PER_SIDE}
        rows = []
        names = sorted(usable)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                rows.append({
                    "a": a, "b": b, "n_a": len(usable[a]), "n_b": len(usable[b]),
                    "mde": mde(usable[a], usable[b]),
                })
        out["groupings"].append({
            "attribute": key,
            "buckets": {g: len(v) for g, v in sorted(buckets.items())},
            "too_small": sorted(g for g in buckets if len(buckets[g]) < MIN_PER_SIDE),
            "missing": missing,
            "comparisons": rows,
        })
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--condition", default="N",
                    help="condition to measure on (default N, the bare baseline)")
    ap.add_argument("--run", default=WAVE)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    res = survey(a.condition, a.run)
    if a.json:
        print(json.dumps(res, indent=2, sort_keys=True))
        return 0

    print("WHAT A BETWEEN-GROUP COMPARISON COULD DETECT -- condition %s, %d model(s)"
          % (res["condition"], res["models_with_position"]))
    print("NO GROUP DIFFERENCE IS COMPUTED HERE, DELIBERATELY. Sizes and detection limits")
    print("only, so the comparisons worth running are chosen before any answer is visible.")
    print("The unit is the MODEL: a group of 12 at depth 5 is 60 sheets and 12 observations.")
    print()
    for g in res["groupings"]:
        print("  %s" % g["attribute"].upper())
        print("    buckets: %s" % ", ".join("%s=%d" % kv for kv in g["buckets"].items()))
        if g["too_small"]:
            print("    below the %d-model floor, not comparable: %s"
                  % (MIN_PER_SIDE, ", ".join(g["too_small"])))
        if g["missing"]:
            print("    %d model(s) carry no value for this attribute" % g["missing"])
        for row in g["comparisons"]:
            m = row["mde"]
            print("    %-18s vs %-18s n=%d/%d   MDE %s"
                  % (row["a"], row["b"], row["n_a"], row["n_b"],
                     "not reachable at any effect size" if m is None
                     else "%.3f position points" % m))
        if not g["comparisons"]:
            print("    no comparison has %d models on both sides" % MIN_PER_SIDE)
        print()
    print("  For scale: the balance instruction moves the median model 0.159, and reprinting")
    print("  the same items in a different order moves it 0.094. A grouping whose MDE is")
    print("  above those cannot speak to either.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
