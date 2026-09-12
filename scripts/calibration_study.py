#!/usr/bin/env python3
"""STATS-BOOTSTRAP-CALIBRATION-001 — does this study's inference actually control its errors?

The existing resampling tests prove REPRODUCIBILITY: the same seed gives the same interval.
That is not calibration. Calibration is whether a "95% CI" covers the truth 95% of the time and
whether a flag at q=0.05 keeps the false-discovery rate near 0.05 — under THIS design, which is

    ordinal      scores are 1-5 integers, and 602 of 733 are the single value 3
    tied         69.2% of per-question deltas are EXACTLY zero; the rest are +/-1 and +/-2
    small-k      k is 30 for most models, but 18 and 3 occur in the published main run
    multiple     13 models tested at once, corrected with Benjamini-Hochberg

None of that is the textbook case the percentile bootstrap is usually justified against, and a
distribution that is 69% a single tied value is exactly where it is known to struggle. So this
does not argue from theory: it runs the study's OWN estimator functions against data generated
from a known truth and counts how often they are right.

    calibration_study.py                 # coverage, type-I and FDR at the real k values
    calibration_study.py --trials 20000  # tighter Monte-Carlo error
    calibration_study.py --check         # exit 1 if coverage or FDR is out of tolerance
"""
from __future__ import annotations

import argparse
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ci_analysis import bootstrap_ci                       # noqa: E402
from robustness_checks import benjamini_hochberg, bootstrap_p_two_sided  # noqa: E402

# The empirical delta distribution, measured from data/2026-05-25-full under the eligibility
# rule (351 deltas). Symmetrised so the TRUE mean is exactly zero while the tie structure and
# the discreteness are preserved -- the two features that make this design non-standard.
# Observed (n=351): -2:2  -1:18  0:243  +1:71  +2:17  -- mean +0.236, 69.2% exact zeros.
# Symmetrised by averaging each magnitude's two tails, which sets the true mean to 0 while
# PRESERVING THE 69.2% TIE SHARE. An earlier cut mirrored the positive tail instead and
# diluted the zeros to 53%, which is a different and much friendlier distribution -- the tie
# share is the whole reason this design is worth checking, so getting it wrong quietly makes
# the estimator look better than it is.
NULL_DELTAS = [-2.0] * 10 + [-1.0] * 44 + [0.0] * 243 + [1.0] * 44 + [2.0] * 10
K_VALUES = (3, 8, 18, 30)
NOMINAL = 0.95
Q = 0.05


def draw(rng, k, shift=0.0):
    return [rng.choice(NULL_DELTAS) + shift for _ in range(k)]


def coverage_and_typeI(rng, k, trials, boot):
    covered = rejected = usable = 0
    for _ in range(trials):
        d = draw(rng, k)
        _, lo, hi = bootstrap_ci(d, rng, n=boot)
        if lo is None:
            continue
        usable += 1
        if lo <= 0.0 <= hi:
            covered += 1
        if bootstrap_p_two_sided(d, rng, n=boot) <= 0.05:
            rejected += 1
    return covered / usable, rejected / usable, usable


def fdr_realised(rng, k, trials, boot, m_models=13, n_true=4, shift=0.5):
    """m models tested together; n_true of them really do move. BH at q, then count the share
    of DISCOVERIES that were nulls -- the realised FDR, which is what q claims to bound."""
    fdrs, powers = [], []
    for _ in range(trials):
        pv, truth = {}, {}
        for i in range(m_models):
            real = i < n_true
            d = draw(rng, k, shift if real else 0.0)
            name = "m%02d" % i
            pv[name] = bootstrap_p_two_sided(d, rng, n=boot)
            truth[name] = real
        surv = benjamini_hochberg(pv, q=Q)
        disc = [k_ for k_, v in surv.items() if v]
        if disc:
            fdrs.append(sum(1 for k_ in disc if not truth[k_]) / len(disc))
        else:
            fdrs.append(0.0)
        powers.append(sum(1 for k_ in disc if truth[k_]) / n_true)
    return sum(fdrs) / len(fdrs), sum(powers) / len(powers)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=4000)
    ap.add_argument("--boot", type=int, default=400)
    ap.add_argument("--seed", type=int, default=20260912)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)

    rng = random.Random(a.seed)
    print("CALIBRATION OF THIS STUDY'S OWN ESTIMATORS")
    print("null: the empirical delta distribution, symmetrised to a true mean of 0")
    print("      %.1f%% exact zeros, values in {-2,-1,0,1,2}" % (100 * NULL_DELTAS.count(0.0) / len(NULL_DELTAS)))
    print("trials=%d bootstrap=%d seed=%d" % (a.trials, a.boot, a.seed))
    print("")
    print("%4s %12s %14s %10s" % ("k", "CI coverage", "type-I @ .05", "usable"))
    bad = []
    for k in K_VALUES:
        cov, t1, n = coverage_and_typeI(rng, k, a.trials, a.boot)
        flag = ""
        if cov < 0.93:
            flag = "  <-- UNDERCOVERS"; bad.append(("coverage", k, cov))
        elif cov > 0.985:
            flag = "  <-- overcovers (conservative)"
        if t1 > 0.07:
            flag += "  type-I INFLATED"; bad.append(("typeI", k, t1))
        print("%4d %11.3f %13.3f %10d%s" % (k, cov, t1, n, flag))

    print("")
    print("BH-FDR at q=%.2f, 13 models, 4 with a true +0.5 shift" % Q)
    print("%4s %14s %10s" % ("k", "realised FDR", "power"))
    for k in K_VALUES:
        f, p = fdr_realised(rng, k, max(300, a.trials // 8), a.boot)
        flag = "  <-- EXCEEDS q" if f > Q * 1.5 else ""
        if f > Q * 1.5:
            bad.append(("fdr", k, f))
        print("%4d %13.3f %9.2f%s" % (k, f, p, flag))

    print("")
    if bad:
        print("MISCALIBRATED:")
        for what, k, v in bad:
            print("  %-9s at k=%-3d %.3f" % (what, k, v))
        print("")
        print("A binary flag from a miscalibrated procedure is not a validated inferential")
        print("decision. Report the effect and its interval; do not lean on the flag.")
    else:
        print("Within tolerance at every k tested. The flags are usable as flags -- which is")
        print("not the same as the effects being large or important.")
    return (1 if bad else 0) if a.check else 0


if __name__ == "__main__":
    sys.exit(main())
