#!/usr/bin/env python3
"""STATS-LINEAGE-NULL-001 — are the four same-version sub-classes exchangeable?

`floor_same_version()` pools 97 pairs into one distribution and the floor table quotes it as a
threshold. The pool is not homogeneous: 58 size variants, 24 tier siblings, 9 date snapshots,
6 mode variants. Pooling is only legitimate if those four are draws from the same distribution.
Nobody had checked, so the pooled p90 was doing inferential work on an assumption.

This tests it directly rather than arguing about it, and states the estimand first.

THE ESTIMAND. For a drift claim -- "this model changed between checkpoint t and t+1" -- the
null is *how much two measurements of THE SAME MODEL AT DIFFERENT SNAPSHOTS differ for reasons
that are not a version change*. That is the `date snapshot` class and nothing else. A size
variant answers a different question (how much do 12b and 27b differ), and so does a tier
sibling (flash-lite vs pro). Both are interesting; neither is the null for a checkpoint
transition.

    lineage_exchangeability.py           # per-class distributions and the pooling test
    lineage_exchangeability.py --check   # exit 1 if the classes are not exchangeable
"""
from __future__ import annotations

import argparse
import collections
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from classify_lineage import classify, parse           # noqa: E402
from floor_table import both_stats, load, modal        # noqa: E402


def collect():
    cells = load("runs/2026-08-31-lineage/**/*.jsonl", "A")
    by = collections.defaultdict(list)
    for (m, c, o), runs in cells.items():
        by[m].extend(runs)
    ids = [m for m, v in by.items() if len(v) >= 2]
    parsed = {i: parse(i) for i in ids}
    per_kind = collections.defaultdict(list)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            label, is_version = classify(parsed[a], parsed[b])
            if is_version or not label.endswith("(null)"):
                continue
            flips = both_stats(modal(by[a]), modal(by[b]))[0]
            per_kind[label.replace("(null)", "").strip() or "unclassified"].append(flips)
    return per_kind


def perm_test(x, y, rng, n=20000):
    """Two-sided permutation test on the difference in means. Exact-ish, no distributional
    assumption -- which matters because these are small, discrete and skewed."""
    obs = abs(st.mean(x) - st.mean(y))
    pool = list(x) + list(y)
    k = len(x)
    hits = 0
    for _ in range(n):
        rng.shuffle(pool)
        if abs(st.mean(pool[:k]) - st.mean(pool[k:])) >= obs - 1e-12:
            hits += 1
    return (hits + 1) / (n + 1)


def main(argv=None):
    import random
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--seed", type=int, default=20260912)
    a = ap.parse_args(argv)
    rng = random.Random(a.seed)

    per = collect()
    order = sorted(per, key=lambda k: -len(per[k]))
    print("SAME-VERSION NULL, BY SUB-CLASS (side-flip units)")
    print("")
    print("%-18s %4s %7s %7s %7s %7s" % ("class", "n", "median", "mean", "p90", "max"))
    for k in order:
        v = sorted(per[k])
        p90 = v[int(0.9 * len(v)) - 1] if len(v) >= 10 else max(v)
        print("%-18s %4d %7.0f %7.1f %7.0f %7.0f"
              % (k, len(v), st.median(v), st.mean(v), p90, max(v)))
    pooled = [x for v in per.values() for x in v]
    pv = sorted(pooled)
    print("%-18s %4d %7.0f %7.1f %7.0f %7.0f"
          % ("POOLED", len(pooled), st.median(pv), st.mean(pv),
             pv[int(0.9 * len(pv)) - 1], max(pv)))

    print("")
    print("PAIRWISE PERMUTATION TESTS (difference in means, two-sided)")
    print("")
    bad = []
    for i, ka in enumerate(order):
        for kb in order[i + 1:]:
            if len(per[ka]) < 3 or len(per[kb]) < 3:
                continue
            p = perm_test(per[ka], per[kb], rng)
            mark = "  <-- NOT exchangeable" if p < 0.05 else ""
            if p < 0.05:
                bad.append((ka, kb, p))
            print("  %-16s vs %-16s  p = %.4f%s" % (ka, kb, p, mark))

    snap = per.get("date snapshot", [])
    print("")
    print("THE ESTIMAND A DRIFT CLAIM NEEDS")
    print("")
    if snap:
        s = sorted(snap)
        print("  date snapshot only:  n=%d  median %.0f  p90 %.0f  max %.0f"
              % (len(s), st.median(s), s[int(0.9 * len(s)) - 1] if len(s) >= 10 else max(s), max(s)))
        print("  pooled:              n=%d  median %.0f  p90 %.0f  max %.0f"
              % (len(pv), st.median(pv), pv[int(0.9 * len(pv)) - 1], max(pv)))
        print("")
        print("  A checkpoint transition judged against the POOLED distribution is being judged")
        print("  against 58 size variants and 24 tier siblings it has nothing to do with.")
    print("")
    if bad:
        print("VERDICT: the sub-classes are NOT exchangeable. The pooled distribution is a")
        print("DESCRIPTIVE REFERENCE, not a significance threshold, and every use of it as a")
        print("threshold must be restated or narrowed to the date-snapshot subset.")
    else:
        print("VERDICT: no pairwise difference reaches p<0.05. Pooling is not contradicted by")
        print("this test -- which is weaker than being justified, at these n.")
    return (1 if bad else 0) if a.check else 0


if __name__ == "__main__":
    sys.exit(main())
