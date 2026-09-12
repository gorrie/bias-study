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

  threshold   the reference distribution's empirical 95th percentile. An observation must
              EXCEED it -- strictly; at it is not above it -- to be called distinguishable.

              IT IS NOT AN ALPHA=0.05 REJECTION THRESHOLD, and this file said it was until
              2026-09-12. A rejection region is defined under a null's assumptions; these
              reference distributions pool heterogeneous model variants with shared-model
              pair dependence, so their p95 is a descriptive order statistic and nothing
              more. Clearing it does not carry a false-positive rate. The independent
              2026-09-08 correction pass reached this same conclusion separately.

  MDE         minimum detectable effect at 80% power. The smallest true effect size such
              that, if it were real, 80% of measurements of it would land above `threshold`.
              Estimated non-parametrically: shift the empirical null distribution upward by
              delta and find the smallest delta where 80% of the shifted mass clears the
              threshold. This assumes the effect adds to noise of the same shape, which is
              the standard assumption and is stated here so it can be argued with.

Then it takes each NULL RESULT this project has published and asks the only question that
matters about it: is the observed movement below the reference? If it is, the honest verdict is
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

# Every null this project has published, with the movement observed AT THE TIME and the floor
# it is judged against. Scope strings are deliberately verbatim from the documents so a reader
# can find the sentence being audited.
#
# `observed` IS FROZEN BY DESIGN and is the one hand-typed field here. The question this table
# asks is "did this claim clear its floor when it was made", so the effect size has to be the
# one the claim rested on; recomputing it would silently re-ask a different question every time
# the corpus grew. The FLOOR is live, which is the half that should move -- a null can lose its
# verdict later because the instrument got sharper, and that is the finding.
#
# Where the current value has since drifted from the published one, the drift is the subject of
# its own RESULTS document rather than an edit here: the frontier temp-0 arm's max is now 19
# against the 14 recorded below, and the local arm's is 5 against 6. Neither changes a verdict.
PUBLISHED_NULLS = [
    {"claim": "position does not move under prompt pressure (local families)",
     "observed": 6, "stat": "side", "floor": "presentation order",
     "where": "STATUS section 2; the withdrawal of the founding thesis"},
    {"claim": "position does not move under prompt pressure (frontier, temp 0)",
     "observed": 14, "stat": "side", "floor": "presentation order",
     "where": "same claim, unscoped, as published on the live page this morning"},
    {"claim": "ablation does not move stance (arm-matched pairs)",
     "observed": 12, "stat": "side", "floor": "requantisation",
     "where": "the weight-rung dissociation, worst pair qwen2.5-14B under D",
     # THE ONE ENTRY WHOSE OBSERVED EFFECT IS n=1, AND IT IS THE ONE THAT COMES BACK
     # "SUPPORTED" -- so this audit's single most quotable output, "one null inverted
     # outright", rested on the thinnest sample in the corpus.
     #
     # 12 side-flips between a stock and an ablated build, one run per arm. A one-run sheet is
     # not a modal, and the run-to-run replicate floor is p90 5, so a 12 from n=1 sits inside
     # its own noise before any ablation acts. The audit is still run on it, because dropping
     # a published null from its own audit is the move this file exists to convict -- but the
     # verdict is printed with the caveat attached, and "SUPPORTED" is not claimed.
     "caveat": "observed effect is n=1 per arm; the replicate floor is p90 5, so this "
               "verdict is not resolvable. Re-collected at n=5 in the 2026-09-07 "
               "ablation wave; until that is analysed, UNDECIDED in both directions."},
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
    # floor_table.ALL_FLOORS, not a second copy. See chart_floors.floors() for what a third
    # copy of this list cost: a floor could reach the paper with no power analysis behind it.
    for fn in F.ALL_FLOORS:
        # floor_table.summarise() discards the raw pairs, so re-derive them the same way it
        # does and keep them. Any divergence between this and floor_table is a bug in one of
        # the two, which is why both read the same loaders.
        name, pairs = _pairs_for(fn)
        if pairs:
            out[name] = {"side": [p[0] for p in pairs],
                         "endpoint": [p[1] for p in pairs]}
    return out


# `_label` used to live here: a hand-typed function-name -> display-name map, which was a
# FOURTH copy of the floor list wearing different clothes. Adding `floor_conditions_wave` to
# ALL_FLOORS raised a KeyError from it, which is the good failure -- the same omission in
# chart_floors.py failed silently by plotting one row fewer than the paper printed. The name a
# floor goes by is the name it passes to summarise(), and `spy` already receives it, so there
# is nothing here to keep in sync.


def _pairs_for(fn):
    """Call the floor function but intercept the pair list before it is summarised away."""
    captured = {}
    original = F.summarise

    def spy(name, pairs, note="", **kw):
        # **kw so this wrapper survives summarise() gaining arguments. It did on 2026-09-04
        # (`clusters=`, for the cluster bootstrap) and this spy raised TypeError, taking every
        # detection limit down with it -- a monkeypatch that mirrors a signature has to be
        # updated in lockstep or written not to care. Written not to care.
        captured["pairs"] = pairs
        captured["name"] = name
        return original(name, pairs, note, **kw)

    F.summarise = spy
    try:
        fn()
    finally:
        F.summarise = original
    return captured.get("name", fn.__name__), captured.get("pairs", [])


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
    print("threshold = reference p95, an order statistic; NOT an alpha=0.05 rejection region")
    print("MDE       = smallest shift with 80% of mass above p95; a design sensitivity,")
    print("            NOT achieved power, and NOT a cutoff for reading an observation")
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
        # TWO DIFFERENT QUESTIONS, AND THIS LINE USED TO ASK ONLY THE SECOND ONE.
        #   thr (rejection threshold) -- could this observation have come from the null?
        #                               A calibrated test of the effect that WAS observed.
        #   m   (MDE)                 -- could an effect of this size have been seen at all?
        #                               Prospective power for a specified alternative.
        # `supported = observed >= m` conflated them, and the two are not ordered: on the
        # same-version-variants floor MDE is 11 while the threshold is 13, so an observation
        # of 11 or 12 cleared the MDE, failed the test, and was still printed SUPPORTED --
        # "calling it a null was wrong in the other direction" -- off a movement that is not
        # distinguishable from the null. Feed the arithmetic the synthetic null [0..10] and it
        # returns threshold 10, MDE 9: an observed 9 is called supported without exceeding 10.
        # Clearing the threshold is what licenses the claim; clearing the MDE only says the
        # instrument was not too blunt to look.
        # STRICTLY greater. An observation EQUAL to the reference p95 does not exceed it,
        # and `>=` called it supported. No published verdict turns on this -- no observation
        # currently sits exactly at its reference -- but the boundary was anti-conservative
        # in the same direction as every other defect this file exists to fix.
        exceeds_threshold = c["observed"] > thr
        above_mde = c["observed"] >= m
        supported = exceeds_threshold
        # A CAVEAT ON THE OBSERVED EFFECT DISQUALIFIES A "SUPPORTED" VERDICT, IT DOES NOT
        # DECORATE IT. The one entry carrying a caveat is the one that came back SUPPORTED,
        # and that verdict was published as "one null inverted outright" off a single run per
        # arm. Printing the caveat under the word SUPPORTED would have changed nothing about
        # how it got quoted.
        caveat = c.get("caveat")
        verdicts.append((c, thr, m, supported and not caveat))
        print("  %s" % c["claim"])
        print("    observed %d, floor '%s' (%s): threshold %.0f, MDE %.0f"
              % (c["observed"], c["floor"], c["stat"], thr, m))
        if supported and caveat:
            print("    NOT RESOLVABLE -- the movement exceeds the threshold, but the observed "
                  "effect itself does not survive scrutiny:")
            print("      %s" % caveat)
        elif supported:
            print("    SUPPORTED -- the movement exceeds what the instrument can resolve, so "
                  "calling it a null was wrong in the other direction")
        elif above_mde:
            # The band between the two limits, which used to be printed SUPPORTED.
            print("    INCONCLUSIVE -- the instrument had the power to see an effect this "
                  "size, and this observation still does not clear the rejection threshold. "
                  "Neither the null nor its inversion is established.")
        else:
            print("    UNDERPOWERED -- 'no effect' is not established; the instrument "
                  "cannot distinguish this from an effect it is too blunt to see")
            if caveat:
                print("      caveat: %s" % caveat)
        print("    %s" % c["where"])
        print()

    # THREE CATEGORIES, NOT TWO. This printed "%d of %d published nulls are underpowered"
    # off `not supported`, which silently folded the one NOT-RESOLVABLE entry in with the
    # underpowered ones -- so the same script reported 3 underpowered nulls in its body and 4
    # in its summary, and the prose that quotes it says 3. Underpowered means the instrument
    # could not have seen the effect. Not-resolvable means the observed effect is not a
    # measurement. They call for different work and they are counted separately.
    under = sum(1 for c, _, m, _ in verdicts if c["observed"] < m)
    inconclusive = sum(1 for c, thr, m, _ in verdicts
                       if m <= c["observed"] < thr and not c.get("caveat"))
    unresolvable = sum(1 for c, thr, _, _ in verdicts
                       if c["observed"] >= thr and c.get("caveat"))
    supported = len(verdicts) - under - inconclusive - unresolvable
    print("%d of %d published nulls are underpowered -- the instrument could not have seen the"
          % (under, len(verdicts)))
    print("effect being ruled out. %d is not resolvable at all (its observed effect is n=1)."
          % unresolvable)
    if inconclusive:
        print("%d sits between the MDE and the rejection threshold: powered enough to have seen"
              % inconclusive)
        print("the effect, not large enough to be distinguished from the null. Neither verdict.")
    print("%d clears its floor, which means calling it a null was wrong in the other direction."
          % supported)
    print()
    print("This does not make the withdrawn claims true. It makes them UNDECIDED, which is a")
    print("different verdict and the honest one. Restoring any of them needs an instrument")
    print("that can resolve the effect size in question -- more seeds, more orders, or a")
    print("narrower item set -- not a re-reading of these runs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
