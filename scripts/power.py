#!/usr/bin/env python3
"""What effect is this instrument actually able to detect? And which of our nulls are real?

WHY THIS EXISTS
---------------
Every control in this project was aimed in one direction. Positive findings were measured
against a noise floor and most of them died. The NULLS were never measured against anything,
and a null is a claim: "position does not move under prompt pressure" asserts something about
the world exactly as much as "position moves" does, and it can be wrong in exactly the same
way -- by being made with an instrument too blunt to tell.

That asymmetry is not neutral. It systematically converts findings into non-findings, because
the only claims exposed to a floor were the ones asserting an effect. This script closes it.

WHAT IT COMPUTES
----------------
For each measured null distribution:

  threshold   the value an observation must EXCEED to be distinguishable from that null at
              alpha=0.05 -- the null's 95th percentile. Anything at or below is inside noise.

  MDE         minimum detectable effect at 80% power. The smallest true effect size such
              that, if it were real, 80% of measurements of it would land above `threshold`.
              Estimated non-parametrically: shift the empirical null distribution upward by
              delta and find the smallest delta where 80% of the shifted mass clears the
              threshold. This assumes the effect adds to noise of the same shape, which is
              the standard assumption and is stated here so it can be argued with.

Then it takes each NULL RESULT this project has published and asks the only question that
matters about it: is the observed movement below the MDE? If it is, the honest verdict is
NOT "no effect." It is "underpowered -- this instrument cannot tell," and any claim built on
that null is unsupported in both directions.

    python scripts/power.py
    python scripts/power.py --markdown

No API calls. Arithmetic on data already on disk.
"""
from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import floor_table as F  # noqa: E402

POWER = 0.80
ALPHA = 0.05

# Every null this project has published, with the movement actually observed and the floor
# it was judged against. Scope strings are deliberately verbatim from the documents so a
# reader can find the sentence being audited.
PUBLISHED_NULLS = [
    {"claim": "position does not move under prompt pressure (local families)",
     "observed": 6, "stat": "side", "floor": "presentation order",
     "where": "STATUS section 2; the withdrawal of the founding thesis"},
    {"claim": "position does not move under prompt pressure (frontier, temp 0)",
     "observed": 14, "stat": "side", "floor": "presentation order",
     "where": "same claim, unscoped, as published on the live page this morning"},
    {"claim": "ablation does not move stance (arm-matched pairs)",
     "observed": 12, "stat": "side", "floor": "requantisation",
     "where": "the weight-rung dissociation, worst pair qwen2.5-14B under D"},
    {"claim": "access tiers of one model are indistinguishable",
     "observed": 3, "stat": "side", "floor": "same-version variants",
     "where": "RESULTS-2026-08-30-access-tier, max after the temp-0 sweep"},
    {"claim": "version drift does not replicate",
     "observed": 5, "stat": "side", "floor": "same-version variants",
     "where": "RESULTS-2026-08-31-drift-does-not-replicate, median transition"},
]


def pctile(vals, q):
    v = sorted(vals)
    if not v:
        return float("nan")
    i = int(q * len(v))
    return v[min(i, len(v) - 1)]


def mde(vals, threshold, power=POWER):
    """Smallest upward shift of the empirical null that clears `threshold` `power` of the time."""
    if not vals:
        return float("nan")
    for delta in range(0, 63):
        shifted = [v + delta for v in vals]
        if sum(1 for s in shifted if s > threshold) / len(shifted) >= power:
            return delta
    return float("nan")


def collect():
    """Raw per-pair values for every floor, reusing floor_table's own loaders."""
    out = {}
    for fn in (F.floor_order, F.floor_same_version, F.floor_quant,
               F.floor_ablation, F.floor_conditions):
        # floor_table.summarise() discards the raw pairs, so re-derive them the same way it
        # does and keep them. Any divergence between this and floor_table is a bug in one of
        # the two, which is why both read the same loaders.
        name = fn.__name__
        pairs = _pairs_for(fn)
        if pairs:
            out[_label(name)] = {"side": [p[0] for p in pairs],
                                 "endpoint": [p[1] for p in pairs]}
    return out


def _label(fn_name):
    return {"floor_order": "presentation order",
            "floor_same_version": "same-version variants",
            "floor_quant": "requantisation",
            "floor_ablation": "refusal-direction ablation",
            "floor_conditions": "prompt condition A->D"}[fn_name]


def _pairs_for(fn):
    """Call the floor function but intercept the pair list before it is summarised away."""
    captured = {}
    original = F.summarise

    def spy(name, pairs, note=""):
        captured["pairs"] = pairs
        return original(name, pairs, note)

    F.summarise = spy
    try:
        fn()
    finally:
        F.summarise = original
    return captured.get("pairs", [])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--markdown", action="store_true")
    args = ap.parse_args(argv)

    floors = collect()

    rows = []
    for name, d in floors.items():
        if name == "prompt condition A->D":
            continue                       # a manipulation, not a null
        for stat in ("side", "endpoint"):
            vals = d[stat]
            thr = pctile(vals, 1 - ALPHA)
            rows.append((name, stat, len(vals), thr, mde(vals, thr)))

    print("DETECTION LIMITS -- what this instrument can resolve, per null, of 62 items")
    print("threshold = must exceed to clear the null at alpha=0.05 (null p95)")
    print("MDE       = smallest true effect detectable 80% of the time")
    print()
    print("%-28s %-9s %6s %11s %6s" % ("null", "statistic", "pairs", "threshold", "MDE"))
    for name, stat, n, thr, m in rows:
        print("%-28s %-9s %6d %11.0f %6.0f" % (name, stat, n, thr, m))

    print()
    print("PUBLISHED NULLS, AUDITED AGAINST THE LIMIT ABOVE")
    print()
    verdicts = []
    for c in PUBLISHED_NULLS:
        key = (c["floor"], c["stat"])
        match = [r for r in rows if r[0] == c["floor"] and r[1] == c["stat"]]
        if not match:
            continue
        _, _, n, thr, m = match[0]
        # A null is only safe if the instrument could have SEEN an effect of the size being
        # ruled out. Observed movement below the MDE means the measurement had no power to
        # distinguish "nothing happened" from "something happened and we could not see it".
        supported = c["observed"] >= m
        verdicts.append((c, thr, m, supported))
        print("  %s" % c["claim"])
        print("    observed %d, floor '%s' (%s): threshold %.0f, MDE %.0f"
              % (c["observed"], c["floor"], c["stat"], thr, m))
        print("    %s" % ("SUPPORTED -- the movement exceeds what the instrument can resolve, "
                          "so calling it a null was wrong in the other direction"
                          if supported else
                          "UNDERPOWERED -- 'no effect' is not established; the instrument "
                          "cannot distinguish this from an effect it is too blunt to see"))
        print("    %s" % c["where"])
        print()

    bad = sum(1 for _, _, _, s in verdicts if not s)
    print("%d of %d published nulls are underpowered." % (bad, len(verdicts)))
    print()
    print("This does not make the withdrawn claims true. It makes them UNDECIDED, which is a")
    print("different verdict and the honest one. Restoring any of them needs an instrument")
    print("that can resolve the effect size in question -- more seeds, more orders, or a")
    print("narrower item set -- not a re-reading of these runs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
