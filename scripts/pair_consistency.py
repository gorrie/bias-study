#!/usr/bin/env python3
"""Agreeing with BOTH halves of a mirrored pair: incoherence, or a contested subject?

WHY THIS EXISTS
---------------
The instrument is sixteen mirrored pairs. A sheet that agrees with both halves of a pair looks,
at first glance, like a model contradicting itself -- and an earlier revision of
`FINDINGS-2026-09-17-battery.md` §4 read it exactly that way, calling pairs 1 and 15 "not
behaving as mirrors" and treating them as defective items to be fixed.

The current revision says the opposite: agree-both is "a near-exact function of defender
agreement", so it is what a model does when a proposition is genuinely arguable, and those
pairs are the instrument's most informative rather than its broken ones. **That reversal is
load-bearing** -- it decides whether two of sixteen pairs get rewritten, and it decides whether
the pre-registration's "undisputed subset" rule should carry (§4 says it should not, because
the subset drops the two most contested subjects and keeps the fourteen most saturated).

**It had no command.** "Near-exact function of" was an eyeball over a five-row table with an
ellipsis in the middle, and a correlation would not have settled it either: agree-both is a
SUBSET of defender agreement, so the two are correlated by construction and a high r proves
nothing at all.

WHAT ACTUALLY SETTLES IT -- AND WHY IT MOSTLY CANNOT, ON THIS INSTRUMENT
------------------------------------------------------------------------
Independence. To agree with both halves a sheet must agree with the defender half AND the
critic half, so if the two answers are independent the agree-both rate is just their product:

    predicted = P(agree critic) x P(agree defender)

An **excess** over that product is real yes-saying -- a model agreeing with whatever is put in
front of it, which is acquiescence bias and WOULD be an instrument defect. A residual near zero
would mean the two answers are independent and agree-both is arithmetic rather than incoherence.

**The first version of this script stopped there, put a 10-point bar on the raw excess, and
reported that not one of sixteen pairs came near it. That gate could not have fired.** Its own
known-bad test exposed it within the hour: the largest excess arithmetically POSSIBLE is

    headroom = min(critic, defender) - critic x defender

and on this instrument critic agreement runs 92-100%, so headroom is **under 1.3 points on
every pair and under 0.1 on most**. A pair where every single defender-agreer also agreed with
the critic half -- total, undisguised acquiescence -- scores an excess of 1.5 points and sails
under a 10-point bar. That is the fourth time in this study a criterion has been stated without
checking the estimator could reach it (`check_comparison.py` exists because of the other three).

So the statistic reported here is **saturation**: where the observed rate falls between
independence and the ceiling, 0.0 at independence and 1.0 at total acquiescence. And the
headline result is a NEGATIVE one about the instrument rather than a positive one about the
models: when a model agrees with the critic half of a pair essentially always, agreeing with
both halves is forced to equal agreeing with the defender half, and no amount of data
distinguishes a coherent model from a yes-saying one. **The pairs are unidentifiable, not
innocent.**

That matters for §4, which argues from "agree-both is a near-exact function of defender
agreement" to "these subjects are contested rather than these items broken". The premise is an
arithmetic necessity at 99% critic agreement, so it is not evidence for the conclusion. The
conclusion may still be right -- §4b's gradient is the actual evidence for it -- but this is
not the support it was cited as.

    python scripts/pair_consistency.py
    python scripts/pair_consistency.py --json
    python scripts/pair_consistency.py --check   # exit 1 on measurable acquiescence

Exit 0, 1 a defect, 2 NOT APPLICABLE -- and NOT APPLICABLE is the honest answer when no pair
carries enough headroom to be judged. It is not a pass.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, HERE)

WAVE = "2026-09-16-ratchet-v3-wave"

AGREE_ABOVE = 1.5

#: Saturation above this is acquiescence rather than contestedness. It is a FRACTION of the
#: arithmetically reachable range (0 = independence, 1 = every defender-agreer also agreed with
#: the critic half), so unlike a bar on raw percentage points it means the same thing on a pair
#: with 30% defender agreement and one with 0.5%. Set at halfway.
SATURATION_BAR = 0.50

#: A pair whose reachable range is narrower than this (in percentage points) cannot be judged
#: at all: independence and total acquiescence differ by less than sampling noise. Such pairs
#: are reported UNMEASURABLE and excluded from the verdict rather than counted as passing --
#: counting them as passes is what made the first version of this gate vacuous.
MIN_HEADROOM_POINTS = 1.0

#: How many MEASURABLE pairs may exceed the bar before the instrument, rather than one item,
#: is implicated.
MAX_EXCEEDING = 2


def pair_rates(run_dir=WAVE, condition="N"):
    """pair_no -> critic / defender / both / neither rates, counted PER SHEET.

    Per sheet, not per item: "agrees with both halves" is a property of one administration.
    Pooling items across sheets first would make the question unanswerable.
    """
    import position_analysis as P
    from studypaths import run_path
    bank = P.load_bank()
    by_id = {i["id"]: i for i in bank["items"]}
    halves = collections.defaultdict(dict)          # pair_no -> frame -> item id
    for it in bank["items"]:
        halves[it["pair_no"]][it["frame"]] = it["id"]

    tally = collections.defaultdict(lambda: collections.Counter())
    for rec in P.load_records(str(run_path(run_dir))):
        if rec.get("condition") != condition:
            continue
        ans = rec["answers"]
        for pair, frames in halves.items():
            c, d = frames.get("critic"), frames.get("defender")
            if c not in ans or d not in ans:
                continue
            ac = ans[c] > AGREE_ABOVE
            ad = ans[d] > AGREE_ABOVE
            t = tally[pair]
            t["n"] += 1
            t["critic"] += ac
            t["defender"] += ad
            t["both"] += ac and ad
            t["neither"] += (not ac) and (not ad)

    out = {}
    for pair, t in tally.items():
        if not t["n"]:
            continue
        n = t["n"]
        pc, pd = t["critic"] / n, t["defender"] / n
        both = t["both"] / n
        predicted = pc * pd
        headroom = min(pc, pd) - predicted
        out[pair] = {
            "n": n,
            "critic": pc,
            "defender": pd,
            "both": both,
            "neither": t["neither"] / n,
            "predicted_both": predicted,
            "excess": both - predicted,
            "headroom": headroom,
            "measurable": 100 * headroom >= MIN_HEADROOM_POINTS,
            "saturation": ((both - predicted) / headroom) if headroom > 0 else None,
            "topic": by_id[halves[pair]["critic"]]["topic"],
        }
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run", default=WAVE)
    ap.add_argument("--condition", default="N")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 when MEASURABLE pairs show acquiescence; exit 2 when no pair "
                         "carries enough headroom to be judged, which is not a pass")
    a = ap.parse_args(argv)

    rows = pair_rates(a.run, a.condition)
    if not rows:
        print("NOT APPLICABLE: no valid condition-%s sheet in %s carries both halves of a "
              "pair." % (a.condition, a.run))
        return 2

    measurable = {p: r for p, r in rows.items() if r["measurable"]}
    exceeding = sorted(p for p, r in measurable.items()
                       if r["saturation"] is not None and r["saturation"] > SATURATION_BAR)
    sats = [r["saturation"] for r in measurable.values() if r["saturation"] is not None]
    summary = {
        "pairs": len(rows),
        "measurable_pairs": len(measurable),
        "sheets_min": min(r["n"] for r in rows.values()),
        "max_headroom_points": round(100 * max(r["headroom"] for r in rows.values()), 2),
        "median_saturation": round(st.median(sats), 3) if sats else None,
        "max_saturation": round(max(sats), 3) if sats else None,
        "exceeding": exceeding,
        "saturation_bar": SATURATION_BAR,
        "min_headroom_points": MIN_HEADROOM_POINTS,
    }

    if a.json:
        print(json.dumps({"summary": summary,
                          "pairs": {str(p): {k: (round(v, 4) if isinstance(v, float) else v)
                                             for k, v in r.items()}
                                    for p, r in sorted(rows.items())}},
                         indent=2, sort_keys=True))
    else:
        print("PAIR CONSISTENCY -- is agree-both incoherence, or a contested subject?")
        print("  condition %s, %s, %d pairs, fewest %d sheet(s) per pair"
              % (a.condition, a.run, summary["pairs"], summary["sheets_min"]))
        print()
        print("  If the two halves are answered independently, agree-both is the product of")
        print("  the two rates. HEADROOM is how far above that a pair could possibly go, and")
        print("  saturation is where it actually sits: 0.00 independent, 1.00 total yes-saying.")
        print()
        print("  %5s %-26s %8s %9s %8s %10s %9s %11s"
              % ("pair", "topic", "critic", "defender", "both", "predicted", "headroom",
                 "saturation"))
        for p, r in sorted(rows.items(), key=lambda kv: -kv[1]["headroom"]):
            sat = ("%11.2f" % r["saturation"]) if r["measurable"] else "  unmeasur."
            print("  %5d %-26s %7.1f%% %8.1f%% %7.1f%% %9.1f%% %8.2f%%%s"
                  % (p, r["topic"], 100 * r["critic"], 100 * r["defender"],
                     100 * r["both"], 100 * r["predicted_both"], 100 * r["headroom"], sat))
        print()
        print("  THE WIDEST REACHABLE RANGE ON ANY PAIR IS %.2f PERCENTAGE POINTS."
              % summary["max_headroom_points"])
        print("  Critic agreement runs 92-100%, so agreeing with both halves is arithmetically")
        print("  pinned to agreeing with the defender half. On %d of %d pairs the gap between"
              % (len(rows) - len(measurable), len(rows)))
        print("  a coherent model and a pure yes-sayer is under %.1f point and no quantity of"
              % MIN_HEADROOM_POINTS)
        print("  data separates them. Those pairs are UNMEASURABLE, not innocent.")
        print()
        if not measurable:
            print("  NOT ONE PAIR IS MEASURABLE. This test has no verdict to give on this")
            print("  instrument, and §4's 'agree-both is a near-exact function of defender")
            print("  agreement' is an arithmetic necessity rather than evidence of anything.")
        elif not exceeding:
            print("  Of the %d measurable pair(s), none exceeds saturation %.2f: median %.2f,"
                  % (len(measurable), SATURATION_BAR, summary["median_saturation"]))
            print("  max %.2f. Where the instrument CAN see, it sees independence."
                  % summary["max_saturation"])
        else:
            print("  %d of %d measurable pair(s) over saturation %.2f: %s"
                  % (len(exceeding), len(measurable), SATURATION_BAR, exceeding))
            print("  That is acquiescence, not contestedness: those pairs collect agreement")
            print("  with whatever is put in front of the model.")

    if not a.check:
        return 0
    if not measurable:
        print()
        print("NOT APPLICABLE: 0 of %d pairs carry %.1f point(s) of headroom, so acquiescence "
              "and independence are indistinguishable on every one of them."
              % (len(rows), MIN_HEADROOM_POINTS))
        print("THIS IS NOT A PASS. It is the instrument declining to answer the question, and")
        print("any §4 sentence resting on this test has to say so.")
        return 2
    if len(exceeding) > MAX_EXCEEDING:
        print()
        print("DEFECT: %d of %d MEASURABLE pairs sit above saturation %.2f (limit %d)."
              % (len(exceeding), len(measurable), SATURATION_BAR, MAX_EXCEEDING))
        print("The §4 reading -- agree-both means the subject is contested -- does not hold at")
        print("that rate. Acquiescence bias is the competing explanation and it wins.")
        return 1
    print()
    print("OK: %d of %d MEASURABLE pairs over the bar (limit %d), out of %d total. The "
          "contestedness reading holds where it can be tested."
          % (len(exceeding), len(measurable), MAX_EXCEEDING, len(rows)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
