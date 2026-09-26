#!/usr/bin/env python3
"""What effect could each of OUR nulls have detected? The audit we apply to everyone else.

WHY THIS EXISTS
---------------
This study's central charge against the literature it audits is that a null is reported as an
absence without ever stating the smallest effect the design could have seen. `controls_audit`
scores twelve studies on exactly that column and most of them score `no`.

**We then reported our own nulls the same way.** The jurisdiction crossover is published as
"no interaction, permutation p = 0.79". Pre-registered prediction 3 is published as "FAIL,
39 positive and 0 negative". The same-version null is published as a floor of 0 / 1 / 1
side-flips. Not one of them carried a minimum detectable effect, and a 2026-09-18 pass deleted
the only power audit in the tree -- correctly, because it compared five WITHDRAWN claims in the
retired instrument's units -- without replacing it with one that reads the live nulls.

A null with no MDE is not a finding. It is a sample size.

WHAT AN MDE MEANS HERE
----------------------
For each null: the smallest true effect that this design, at this n, would detect **80% of the
time** at alpha = 0.05. Found by simulation -- inject an effect of size d into the observed
data, re-run the study's own test, and count rejections -- then bisect on d. The test used is
the one the paper actually ran, not a normal approximation of it.

    python scripts/null_audit.py
    python scripts/null_audit.py --draws 400 --sims 400     # faster, coarser
    python scripts/null_audit.py --selftest

Exit 0 computed, 2 NOT APPLICABLE (a null's data is not in this tree).
"""
from __future__ import annotations

import argparse
import collections
import io
import json
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import studypaths as _SP

POWER = 0.80
ALPHA = 0.05


# ---------------------------------------------------------------- prediction 3

def mde_any_negative(n_models, power=POWER):
    """Prediction 3: 'direction differs in sign across models', observed 39 positive / 0.

    The test is simply whether ANY model points the other way. With n models and a true
    proportion pi of opposite-signed models, the chance of seeing at least one is
    1 - (1 - pi)^n. So the MDE is the pi at which that reaches `power`.

    This one needs no simulation and is exact, which is worth saying out loud: the null is
    strong precisely because the test is cheap. Seeing zero negatives in 39 draws genuinely
    rules out a common opposite direction -- it does not rule out a rare one.
    """
    if n_models <= 0:
        return None
    return 1.0 - (1.0 - power) ** (1.0 / n_models)


# ---------------------------------------------------------------- crossover

def crossover_data(run, condition="N"):
    """Per-model US-minus-China position gaps and vendor jurisdiction, from the live corpus."""
    import crossover_jurisdiction as X
    run_dir = (run if os.path.isdir(run)
               else os.path.join(_SP.STUDY_DIR, "runs", run))
    if not os.path.isdir(run_dir):
        return None, None
    items = X.load_bank()
    pos = X.cell_positions(run_dir, items, condition)
    # per_model_gap returns (us_position, cn_position, gap) per model; the gap is the
    # statistic the crossover tests and is index 2, exactly as crossover_jurisdiction.main
    # reads it. Taking the whole tuple silently made every arithmetic operation a tuple
    # concatenation.
    raw = X.per_model_gap(pos, items)
    groups = {m: X.vendor_jurisdiction(m) for m in raw}
    groups = {m: g for m, g in groups.items() if g in ("US", "CN")}
    gaps = {m: raw[m][2] for m in groups}
    return gaps, groups


def crossover_reject(gaps_vec, groups, draws, rng, delta=0.0):
    """Run the study's own permutation test with an interaction of size `delta` injected.

    LOYALTY predicts CN-vendor models carry a more positive US-minus-CN gap than US-vendor
    ones. `delta` adds exactly that, so the simulation asks: if the effect the author's thesis
    predicts were real and this big, would this design have found it?
    """
    vals = {}
    for m, v in gaps_vec.items():
        vals[m] = v + (delta if groups[m] == "CN" else 0.0)
    us = [v for m, v in vals.items() if groups[m] == "US"]
    cn = [v for m, v in vals.items() if groups[m] == "CN"]
    if len(us) < 2 or len(cn) < 2:
        return None
    obs = (sum(cn) / len(cn)) - (sum(us) / len(us))
    pool = list(vals.values())
    n_cn = len(cn)
    hits = 0
    for _ in range(draws):
        rng.shuffle(pool)
        a = pool[:n_cn]
        b = pool[n_cn:]
        stat = (sum(a) / len(a)) - (sum(b) / len(b))
        if abs(stat) >= abs(obs):
            hits += 1
    return (hits + 1.0) / (draws + 1.0)


def mde_crossover(gaps, groups, draws, sims, rng, hi=2.0):
    """Bisect for the injected interaction detected at 80% power."""
    def power_at(delta):
        rejects = 0
        for _ in range(sims):
            # resample models with replacement, so the power estimate accounts for WHICH
            # models are in the panel, not only how many
            boot = {}
            keys = list(gaps)
            for i in range(len(keys)):
                k = rng.choice(keys)
                boot["%s#%d" % (k, i)] = gaps[k]
            bg = {kk: groups[kk.split("#")[0]] for kk in boot}
            p = crossover_reject(boot, bg, draws, rng, delta)
            if p is not None and p < ALPHA:
                rejects += 1
        return rejects / float(sims)

    lo = 0.0
    if power_at(hi) < POWER:
        return None, power_at(hi)
    for _ in range(9):
        mid = (lo + hi) / 2.0
        if power_at(mid) >= POWER:
            hi = mid
        else:
            lo = mid
    return hi, POWER


# ---------------------------------------------------------------- same-version

def mde_shift_in_pairs(values, sims, rng, hi=None):
    """Smallest constant shift in a paired side-flip distribution detected 80% of the time.

    The same-version null is published as a distribution (median / p90 / max side-flips). The
    question a reader needs answered is: how much WOULD two same-version variants have had to
    differ before this design called them different? Test: the observed p95 as the threshold,
    the study's own rule.
    """
    if not values:
        return None
    thr = sorted(values)[min(int(0.95 * len(values)), len(values) - 1)]
    hi = hi if hi is not None else max(4.0, thr * 4.0 + 4.0)

    def power_at(shift):
        hits = 0
        for _ in range(sims):
            draw = rng.choice(values) + shift
            if draw > thr:
                hits += 1
        return hits / float(sims)

    if power_at(hi) < POWER:
        return None, thr
    lo = 0.0
    for _ in range(12):
        mid = (lo + hi) / 2.0
        if power_at(mid) >= POWER:
            hi = mid
        else:
            lo = mid
    return hi, thr


def distributional_nulls():
    """Every FLOOR-shaped null, with the MDE `power.py` already computes for it.

    INTEGRATE, DO NOT FORK. `power.py` exists to turn each floor into a detection limit and
    does it correctly; recomputing that here would be a second implementation of the study's
    own threshold rule, free to drift from the first. This file's job is the nulls power.py
    CANNOT see -- a proportion test (prediction 3) and a between-group interaction (the
    crossover) -- plus a single place a reader can find all of them.

    Returns [(name, statistic, n_pairs, threshold, mde, p90_is_max)].
    """
    try:
        import power as P
        import floor_table as F
    except ImportError:
        return []
    out = []
    try:
        data = P.collect()
    except Exception:
        return []
    for name, arms in sorted(data.items()):
        # A prompt manipulation is an INTERVENTION, not a null; power.reference_kind draws
        # that line and this must respect it or the table lists effects as floors.
        if P.reference_kind(name) == "intervention":
            continue
        for stat in ("side", "endpoint"):
            vals = (arms or {}).get(stat) or []
            if not vals:
                continue
            thr = P.pctile(vals, 0.95)
            out.append((name, stat, len(vals), thr, P.mde(vals, thr),
                        P.pctile_is_max(vals, 0.95)))
    return out


# ---------------------------------------------------------------- report

def selftest():
    rng = random.Random(7)
    fails = []
    # A test with n draws must need a LARGER effect when n is smaller.
    big, small = mde_any_negative(39), mde_any_negative(8)
    if not (big < small):
        fails.append("MDE for 'any negative' must fall as the panel grows (%s vs %s)"
                     % (big, small))
    if abs(mde_any_negative(1) - 0.80) > 1e-9:
        fails.append("with one model, detecting an opposite sign 80%% of the time needs "
                     "pi = 0.80; got %s" % mde_any_negative(1))
    # A distribution with no spread must be detectable by any shift above its threshold.
    got = mde_shift_in_pairs([0, 0, 0, 0, 0, 0, 0, 0, 0, 0], 400, rng)
    if got is None or got[0] is None or got[0] > 1.5:
        fails.append("a zero-variance null should be beaten by a shift of ~1; got %s" % (got,))
    # And a wide one must need more.
    wide = mde_shift_in_pairs([0, 2, 4, 6, 8, 10, 12, 14, 16, 18], 400, rng)
    if wide is None or wide[0] is None or wide[0] <= got[0]:
        fails.append("a wide null must need a LARGER shift than a tight one (%s vs %s)"
                     % (wide, got))
    for f in fails:
        print("  FAIL  %s" % f)
    if fails:
        return 1
    print("  selftest: 4 checks passed -- MDE falls with n, is exact at n=1, and a wider")
    print("  null demands a larger effect than a tight one.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", default="2026-09-16-ratchet-v3-wave")
    ap.add_argument("--draws", type=int, default=600)
    ap.add_argument("--sims", type=int, default=300)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()

    rng = random.Random(20260918)
    print("")
    print("  THE NULLS THIS STUDY REPORTS, WITH THE EFFECT EACH COULD HAVE DETECTED")
    print("")
    print("  MDE = smallest true effect this design would find %d%% of the time at alpha %.2f,"
          % (int(POWER * 100), ALPHA))
    print("  by simulation through the same test the paper ran. A null without one is a")
    print("  sample size, not a finding -- which is the charge this study levels at others.")
    print("")

    computed = 0

    # 1. prediction 3
    gaps, groups = crossover_data(a.run)
    import position_analysis as PA
    run_dir = (a.run if os.path.isdir(a.run)
               else os.path.join(_SP.STUDY_DIR, "runs", a.run))
    n_models = 0
    if os.path.isdir(run_dir):
        recs = PA.load_records(run_dir)
        # THE MODELS THE PREDICTION IS SCORED ON: those with a valid sheet under both A and N,
        # the contrast the direction is read from. Counting every model with records gave 63
        # against the verdict's 61, so the detection limit was stated for a population the
        # verdict does not cover.
        by = {}
        for r in recs:  # load_records returns valid sheets only
            by.setdefault(r["model"], set()).add(r.get("condition"))
        n_models = sum(1 for conds in by.values() if {"A", "N"} <= conds)
    if n_models:
        pi = mde_any_negative(n_models)
        computed += 1
        print("  1. PREDICTION 3 -- 'direction differs in sign across models'")
        print("     observed: 0 negative, of the %d models with valid A and N sheets" % n_models)
        print("     MDE     : %.1f%% -- if that share of models truly pointed the other way," %
              (100 * pi))
        print("               this design would have seen at least one %d%% of the time."
              % int(POWER * 100))
        print("     reading : rules out a COMMON opposite direction. Does not rule out a rare")
        print("               one, and the paper must not be read as claiming it does.")
        print("")

    # 2. crossover
    if gaps and len(gaps) >= 4:
        obs_p = crossover_reject(gaps, groups, a.draws, rng, 0.0)
        mde, _ = mde_crossover(gaps, groups, a.draws, a.sims, rng)
        us = [v for m, v in gaps.items() if groups[m] == "US"]
        cn = [v for m, v in gaps.items() if groups[m] == "CN"]
        obs = (sum(cn) / len(cn)) - (sum(us) / len(us))
        computed += 1
        print("  2. JURISDICTION CROSSOVER -- vendor jurisdiction x item jurisdiction")
        print("     observed: %+.3f interaction, permutation p = %.3f, %d US- and %d CN-vendor"
              % (obs, obs_p, len(us), len(cn)))
        if mde is None:
            print("     MDE     : NOT REACHED even at an injected interaction of 2.00 scale")
            print("               points. This design cannot detect the effect it reports as")
            print("               absent. The null is UNINFORMATIVE and must be reported as")
            print("               'not tested', never as 'no interaction'.")
        else:
            print("     MDE     : %+.3f scale points. An interaction smaller than that is not"
                  % mde)
            print("               distinguishable from zero here, so the null bounds the")
            print("               effect at that size and no further.")
        print("     note    : one mirrored pair per state, so each model's gap rests on four")
        print("               answers. Exploratory, written after the data was seen.")
        print("")
    else:
        print("  2. JURISDICTION CROSSOVER -- NOT APPLICABLE, fewer than 4 resolvable models")
        print("")

    # 3. every floor-shaped null, from power.py
    dist = distributional_nulls()
    if dist:
        computed += len(dist)
        print("  3. THE FLOOR-SHAPED NULLS -- what 'nothing changed' looks like, and the")
        print("     smallest movement each one could have told apart from it.")
        print("")
        print("     %-46s %-9s %6s %10s %6s"
              % ("null", "statistic", "pairs", "threshold", "MDE"))
        for name, stat, n, thr, m, is_max in sorted(dist, key=lambda r: (r[4], r[0])):
            flag = "  p95 IS THE SAMPLE MAX (n=%d)" % n if is_max else ""
            print("     %-46s %-9s %6d %10.0f %6.0f%s"
                  % (name[:46], stat, n, thr, m, flag))
        print("")
        print("     A movement below its own MDE is NOT a small effect -- it is one this")
        print("     design could not have seen. Every effect the paper reports is placed")
        print("     against the row it belongs to, and the ones that sit underneath are")
        print("     reported as unresolvable rather than as absent.")
        print("")

    if not computed:
        print("  CHECKED NOTHING -- no null's data is in this tree. NOT APPLICABLE.")
        return 2
    print("  %d null(s) audited. Every null the paper states should appear above; one that" %
          computed)
    print("  does not is a null with no stated power, which is the defect this file exists to")
    print("  prevent us from committing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
