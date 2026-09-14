#!/usr/bin/env python3
"""CLAIM-ABLATION-CAUSAL-001 — turn "no effect found" into a bounded claim, or admit it cannot be.

`RESULTS-2026-09-07-ablation-wave.md` concludes:

    "Abliteration does not measurably move political stance on any of the three usable bases."

That is a claim of ABSENCE, reached by failing to find a difference. Absence of a reproducible
difference is not an equivalence test: a study with no power finds no effect on every hypothesis
put to it, and this arm is n=5 per cell on three bases.

The rigorous form of an absence claim is a bound — *effects larger than X are excluded at this n*
— which requires a pre-specified margin and a two-one-sided-test. This computes the bound the
data can actually support, so the sentence can be rewritten as something defensible or withdrawn.

Units are SIDE-FLIPS out of the 62-item sheet, the same unit as the floors table.

    ablation_equivalence.py               # the bound, per base
    ablation_equivalence.py --margin 5    # TOST against a stated margin
"""
from __future__ import annotations

import argparse
import math
import os
import random
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# This report prints en-dashes and em-dashes. On a default-codepage Windows host
# those lines vanish or raise when stdout is a pipe, which is how a table can come
# back missing rows without any error. Same trap as abliteration_effect_check.py.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# Observed, from the wave at n=5 with a swept seed (RESULTS-2026-09-07-ablation-wave.md).
# side-flips between stock and ablated, per base, under A / D / P prompts.
# Stock -> ablated side-flips, from the weight-vs-prompt table of the wave (n=5, swept seed).
# CORRECTED 2026-09-12: an earlier cut of this script used 0,0,0 for the two low bases, which
# is not what the run measured. phi4-14b moves 2-3 and qwen38-27b 1-2 -- small, at or under the
# modal estimator floor of 3, but NOT zero. The difference matters: three identical zeros give a
# degenerate bootstrap, while genuine small values give a real interval, so the wrong inputs
# produced a stronger-sounding "not testable" than the data warrants on those two bases.
#: TRANSCRIBED VALUES, KEPT ONLY AS THE PUBLISHED BASELINE. Do not compute from them.
#:
#: This script used to derive its entire verdict from this dict and touched no file
#: at all -- `grep -c "open(\|glob\|json.load\|Path("` returned 0. The literals were
#: already wrong against the live wave: phi4-14b measures [2,3,2] not [2,3,3],
#: qwen38-27b's ablated arm [0,2,2] not [1,2,2], and qwen25-14b has NINE values,
#: of which the hardcode kept three and dropped the Josiefied ablator's near-zero
#: row -- the cherry-picked triple that produced the "NOT equivalent" verdict.
#:
#: The comment history records this dict being corrected once before for exactly
#: the same reason, which is the argument for not having it at all.
PUBLISHED_OBSERVED = {
    "qwen38-27b": [1, 2, 2],
    "phi4-14b":   [2, 3, 3],
    "qwen25-14b": [8, 9, 9],
}


def observed_from_runs():
    """Derive the per-base side-flip lists from the wave on disk.

    Returns (dict, note). A None dict means the wave is not readable here, and the
    caller must SAY SO rather than silently falling back to the transcription.
    """
    try:
        import ablation_analysis as AA
    except Exception as exc:                      # pragma: no cover - import guard
        return None, "ablation_analysis unavailable: %s" % exc
    try:
        per = AA.usable(AA.cells())
        rows = AA.step4_weight_vs_prompt(per)
    except Exception as exc:
        return None, "could not read the wave: %s" % exc
    if not rows:
        return None, "the wave yielded 0 weight-vs-prompt rows"
    out = {}
    for r in rows:
        side = r.get("weight_side")
        if side is not None:
            out.setdefault(r["base"], []).append(side)
    if not out:
        return None, "no base produced a usable weight-side measurement"
    return {b: sorted(v) for b, v in out.items()}, "derived from %d live row(s)" % len(rows)


OBSERVED, OBSERVED_NOTE = observed_from_runs()
if OBSERVED is None:
    OBSERVED = PUBLISHED_OBSERVED
FLOOR = 3                          # modal estimator floor, from the floors table
# The same base, two builds by ONE author vs a build by another. This is the ablator-spread
# control, and it is the whole basis for attributing qwen25-14b's 8/9/9 to the ablator.
ABLATOR_SPREAD = {
    "huihui v1 vs huihui v2":  [0, 0, 0],
    "huihui v1 vs Josiefied":  [8, 9, 9],
    "huihui v2 vs Josiefied":  [8, 9, 9],
}
N_PER_CELL = 5
SHEET = 62


def boot_ci(xs, rng, n=20000, alpha=0.05):
    k = len(xs)
    means = sorted(sum(xs[rng.randrange(k)] for _ in range(k)) / k for _ in range(n))
    return st.mean(xs), means[int(alpha / 2 * n)], means[int((1 - alpha / 2) * n)]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--margin", type=float, default=None,
                    help="equivalence margin in side-flips; TOST against it")
    ap.add_argument("--seed", type=int, default=20260912)
    a = ap.parse_args(argv)
    rng = random.Random(a.seed)

    print("ABLATION EFFECT, AS A BOUNDED CLAIM (side-flips of %d)" % SHEET)
    print("n=%d per cell — each base's interval rests on its measured rows, not on"
          % N_PER_CELL)
    print("independent experiments.")
    print("")
    # SAY WHERE THE NUMBERS CAME FROM. This script used to compute entirely from
    # transcribed literals and open no file, so a reader could not tell that its
    # inputs had drifted from the wave -- and they had.
    if OBSERVED_NOTE.startswith("derived"):
        print("inputs: %s" % OBSERVED_NOTE)
        drifted = {b: (PUBLISHED_OBSERVED[b], OBSERVED[b])
                   for b in PUBLISHED_OBSERVED
                   if b in OBSERVED and PUBLISHED_OBSERVED[b] != OBSERVED[b]}
        if drifted:
            print("WARNING: the transcribed values published earlier DISAGREE with the wave:")
            for b, (was, now) in sorted(drifted.items()):
                print("  %-14s published %-16s measured %s" % (b, was, now))
            print("  The published verdict was computed from the first column.")
    else:
        print("inputs: TRANSCRIBED LITERALS — %s" % OBSERVED_NOTE)
        print("  These are a record of what was published, NOT a measurement. Any verdict")
        print("  below is a reproduction of the old number, not a check of it.")
    print("")
    print("%-14s %10s %22s %s" % ("base", "mean", "95% CI", "reading"))
    for base, xs in OBSERVED.items():
        m, lo, hi = boot_ci(xs, rng)
        if hi == lo:
            reading = "degenerate: all three identical, CI is a point"
        else:
            reading = "effects above %.1f flips not excluded" % hi
        print("%-14s %10.1f %10.1f – %-9.1f %s" % (base, m, lo, hi, reading))

    print("")
    print("THE PROBLEM WITH THE TWO LOW BASES")
    print("")
    print("  This section said 'qwen38-27b and phi4-14b measured 0, 0, 0' until 2026-09-12,")
    print("  after the OBSERVED values above had already been corrected to what the run")
    print("  actually produced. The data was fixed and the paragraph explaining it was not,")
    print("  so the script contradicted its own table three lines earlier.")
    print("")
    print("  They measure 1-2 and 2-3 side-flips of 62, not zero. Small, at or under the")
    print("  modal estimator floor of %d, and NOT zero -- which changes the argument rather" % FLOOR)
    print("  than softening it. Three identical zeros would give a degenerate bootstrap with")
    print("  an interval of zero width, an artifact that can bound nothing. Genuine small")
    print("  values give a real interval, and the real interval is the narrow one printed")
    print("  above, resting on THREE numbers from one base -- not three experiments.")
    print("")
    print("  At n=5 per cell the smallest difference this design can resolve is set by the")
    print("  run-to-run replicate floor, which the floors table puts at p90 = 5 side-flips.")
    print("  Both low bases sit under it. The defensible sentence is 'no effect larger than")
    print("  the replicate floor was detected', not 'does not measurably move stance', and")
    print("  not 'measured zero'.")

    if a.margin is not None:
        print("")
        print("TOST AGAINST A MARGIN OF %.1f SIDE-FLIPS" % a.margin)
        print("")
        for base, xs in OBSERVED.items():
            m, lo, hi = boot_ci(xs, rng)
            ok = (lo > -a.margin) and (hi < a.margin)
            if hi == lo:
                verdict = "NOT TESTABLE (degenerate interval)"
            else:
                verdict = "equivalent to zero within margin" if ok else "NOT equivalent"
            print("  %-14s CI [%.1f, %.1f] vs +/-%.1f -> %s" % (base, lo, hi, a.margin, verdict))

    print("")
    print("WHAT THE ABLATOR-SPREAD CONTROL DOES AND DOES NOT SHOW")
    print("")
    for k, v in ABLATOR_SPREAD.items():
        print("  %-26s %s" % (k, v))
    print("")
    print("  Two builds by one author agree at 0; either against a third author's build gives")
    print("  8/9/9 — the same size as the apparent ablation effect. That is strong evidence")
    print("  that qwen25-14b's effect is BUILD-SPECIFIC.")
    print("")
    print("  It is NOT evidence that ablation has no effect in general. It compares three")
    print("  third-party artifacts whose layer choice, refusal set, intervention strength and")
    print("  quantisation are undocumented and differ. The design cannot separate 'ablation")
    print("  does nothing' from 'these particular ablators disagree' — and the second is what")
    print("  was actually observed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
