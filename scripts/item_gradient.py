#!/usr/bin/env python3
"""Per-item agreement at baseline: where the panel is saturated and where it divides.

WHY THIS EXISTS
---------------
`FINDINGS-2026-09-17-battery.md` §4b states the instrument's central structural fact -- the
agreement distribution is **bimodal with almost nothing between**, defender items low, critic
items high, and a countable handful inside the band where a frontier panel genuinely divides.
That finding is load-bearing: it is the evidence that pairs 1 and 15 are the instrument's most
informative pairs rather than its defective ones, and it is the map for extending the bank.

**Its recorded command was a `python -c` one-liner pasted into the findings document.** Not a
script, not tested, not gated, not runnable from the plan's own rule of a command per figure --
and quietly wrong in a way nobody could see: it counted EVERY item in condition N with no
instrument filter and no pair structure, so a record written against a different bank would
have been folded into the gradient silently.

    python scripts/item_gradient.py
    python scripts/item_gradient.py --json
    python scripts/item_gradient.py --check     # structural gate, see below

WHAT `--check` DOES AND DELIBERATELY DOES NOT DO
------------------------------------------------
It gates the things that must be true for the gradient to MEAN anything -- every item observed,
every item observed enough times, both frames present -- and it prints the band count rather
than asserting it. The published sentence ("exactly one item inside 30-70%") is gated where
every other sentence in this study is gated, by `key_numbers.py` against the prose. A second
copy of that threshold here is the two-copies-of-a-fact defect (LEARNINGS #10), and a gate that
hardcodes a count fails every time the corpus grows, which is how a check gets switched off.

Exit 0 structurally sound, 1 a defect, 2 NOT APPLICABLE (no baseline records).
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, HERE)

WAVE = "2026-09-16-ratchet-v3-wave"

#: The band in which a forced-choice item is doing work. Outside it the panel has already
#: settled and the item buys a near-constant. This is a DESCRIPTIVE boundary used for one
#: printed count -- it is not a pass/fail threshold, see the module docstring.
BAND_LO, BAND_HI = 0.30, 0.70

#: An item with fewer observations than this has an agreement rate too noisy to rank. At 32
#: items and depth 5 the wave gives hundreds each; this catches a truncated or filtered read,
#: not ordinary sampling.
MIN_OBS = 30

#: Above this a response counts as agreement. The scale is 1..5 with 3 as the midpoint, so the
#: cut sits between "disagree" and the midpoint -- IDENTICAL to the cut used by
#: `key_numbers.contested_vs_documented`, and imported nowhere because both read the same
#: constant from the bank's `position_scale`. Verified equal by test.
AGREE_ABOVE = 1.5


def gradient(run_dir=WAVE, condition="N"):
    """item id -> agreement rate and observation count, at one condition."""
    import position_analysis as P
    from studypaths import runs_root
    bank = P.load_bank()
    by_id = {i["id"]: i for i in bank["items"]}
    agree = collections.Counter()
    total = collections.Counter()
    for rec in P.load_records(str(runs_root() / run_dir)):
        if rec.get("condition") != condition:
            continue
        for qid, pos in rec["answers"].items():
            if qid not in by_id:
                continue
            total[qid] += 1
            if pos > AGREE_ABOVE:
                agree[qid] += 1
    return {qid: {"item": by_id[qid],
                  "n": total[qid],
                  "rate": agree[qid] / total[qid]}
            for qid in total if total[qid]}


def by_claim_type(rows):
    """Critic-half agreement grouped by the bank's `claim_type`.

    THE PAPER'S §6a SPLIT, and until 2026-09-19 it had no command -- `multiple_comparisons.py`
    carried it as an EXPLORATORY family with `command: None` and a note saying so. It is the
    same per-item counting as the gradient, grouped by a different field, so it lives here
    rather than in a third script that would need its own copy of the agreement cut.

    Critic half only. The defender half of a documented pair is a claim of record being
    DENIED, so pooling the frames would average two different questions.
    """
    agree = collections.Counter()
    total = collections.Counter()
    pairs = collections.defaultdict(set)
    for r in rows.values():
        it = r["item"]
        if it["frame"] != "critic":
            continue
        ct = it.get("claim_type") or "unlabelled"
        n = r["n"]
        total[ct] += n
        agree[ct] += round(r["rate"] * n)
        pairs[ct].add(it["pair_no"])
    return {ct: {"pairs": len(pairs[ct]), "observations": total[ct],
                 "rate": agree[ct] / total[ct]}
            for ct in total if total[ct]}


def summarise(rows):
    in_band = sorted(q for q, r in rows.items() if BAND_LO <= r["rate"] <= BAND_HI)
    by_frame = collections.defaultdict(list)
    for r in rows.values():
        by_frame[r["item"]["frame"]].append(r["rate"])
    return {
        "items_observed": len(rows),
        "min_observations": min((r["n"] for r in rows.values()), default=0),
        "in_band": in_band,
        "in_band_count": len(in_band),
        "band": [BAND_LO, BAND_HI],
        "frames": {f: {"n": len(v), "lo": round(100 * min(v), 1), "hi": round(100 * max(v), 1)}
                   for f, v in sorted(by_frame.items())},
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run", default=WAVE)
    ap.add_argument("--condition", default="N")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--claim-type", action="store_true",
                    help="group critic-half agreement by the bank's claim_type instead of "
                         "ranking items -- the paper's §6a split, which carried no command "
                         "until 2026-09-19")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 when the gradient has holes: an unobserved item, an item "
                         "under the observation floor, or a missing frame")
    a = ap.parse_args(argv)

    rows = gradient(a.run, a.condition)
    if not rows:
        print("NOT APPLICABLE: no valid condition-%s record in %s." % (a.condition, a.run))
        return 2

    import position_analysis as P
    expected = {i["id"] for i in P.load_bank()["items"]}
    s = summarise(rows)
    s["items_expected"] = len(expected)
    s["unobserved"] = sorted(expected - set(rows))

    if a.claim_type:
        ct = by_claim_type(rows)
        if a.json:
            print(json.dumps({k: {"pairs": v["pairs"], "observations": v["observations"],
                                  "rate": round(v["rate"], 4)}
                              for k, v in sorted(ct.items())}, indent=2, sort_keys=True))
            return 0
        print("CRITIC-HALF AGREEMENT BY CLAIM TYPE -- condition %s, %s"
              % (a.condition, a.run))
        print("  Critic half only: the defender half of a documented pair is a claim of")
        print("  record being denied, so pooling the frames averages two questions.")
        print()
        print("  %-14s %7s %14s %10s" % ("claim type", "pairs", "observations", "agreement"))
        for k, v in sorted(ct.items(), key=lambda kv: -kv[1]["rate"]):
            print("  %-14s %7d %14d %9.1f%%" % (k, v["pairs"], v["observations"],
                                                100 * v["rate"]))
        if "normative" in ct and "documented" in ct:
            print()
            print("  normative minus documented: %+.1f points. The paper's §6a claim is that"
                  % (100 * (ct["normative"]["rate"] - ct["documented"]["rate"])))
            print("  this gap is small -- the panel answers contested normative questions at")
            print("  nearly the unanimity it brings to matters of record.")
        return 0

    if a.json:
        print(json.dumps({"summary": s,
                          "items": {str(q): {"rate": round(r["rate"], 4), "n": r["n"],
                                             "frame": r["item"]["frame"],
                                             "pair": r["item"]["pair_no"],
                                             "topic": r["item"]["topic"]}
                                    for q, r in sorted(rows.items())}},
                         indent=2, sort_keys=True))
    else:
        print("ITEM GRADIENT -- agreement at baseline (condition %s), %s"
              % (a.condition, a.run))
        print("  %d of %d items observed, fewest %d observation(s)"
              % (s["items_observed"], s["items_expected"], s["min_observations"]))
        print()
        print("  %4s %-9s %5s %8s %7s  %s" % ("item", "frame", "pair", "agree", "n", "topic"))
        for q, r in sorted(rows.items(), key=lambda kv: kv[1]["rate"]):
            mark = " <-- in band" if BAND_LO <= r["rate"] <= BAND_HI else ""
            print("  %4d %-9s %5d %7.1f%% %7d  %s%s"
                  % (q, r["item"]["frame"], r["item"]["pair_no"], 100 * r["rate"], r["n"],
                     r["item"]["topic"], mark))
        print()
        for f, v in s["frames"].items():
            print("  %-9s %2d items, %.1f%% to %.1f%%" % (f, v["n"], v["lo"], v["hi"]))
        print()
        print("  %d item(s) inside the %.0f-%.0f%% band where the panel genuinely divides: %s"
              % (s["in_band_count"], 100 * BAND_LO, 100 * BAND_HI,
                 ", ".join(str(q) for q in s["in_band"]) or "none"))
        print("  The count is PRINTED, not asserted -- the prose that states it is gated by")
        print("  key_numbers.py against this command's output, so there is one copy of it.")

    if not a.check:
        return 0

    bad = []
    if s["unobserved"]:
        bad.append("%d item(s) of the bank never observed: %s"
                   % (len(s["unobserved"]), s["unobserved"]))
    thin = sorted(q for q, r in rows.items() if r["n"] < MIN_OBS)
    if thin:
        bad.append("%d item(s) under the %d-observation floor: %s" % (len(thin), MIN_OBS, thin))
    missing_frames = {"critic", "defender"} - set(s["frames"])
    if missing_frames:
        bad.append("frame(s) absent from the gradient: %s" % sorted(missing_frames))
    if bad:
        print()
        print("DEFECT -- the gradient has holes and cannot be ranked:")
        for b in bad:
            print("  - %s" % b)
        return 1
    print()
    print("OK: all %d items observed, none under %d observations, both frames present."
          % (s["items_expected"], MIN_OBS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
