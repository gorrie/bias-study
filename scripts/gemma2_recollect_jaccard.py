#!/usr/bin/env python3
"""Recompute the Gemma-2-9B same-weights Jaccard control the paper quotes.

WHY. The weight-rung claim for Gemma-2-9B rests on four numbers: the word-set overlap between
the stock and abliterated arms, and the overlap of each arm with a resample of ITSELF on the same
weights. Without the second pair the first is uninterpretable -- an apparent "rewrite" is only a
rewrite if it exceeds what temperature alone produces. Until 2026-09-25 nothing in either tree
recomputed them, so shipping the records would not have made the figures checkable.

    python scripts/gemma2_recollect_jaccard.py
    python scripts/gemma2_recollect_jaccard.py --check   # exit 1 if any row drifts

Reads two runs already in this tree. No API calls, no network.

THE TOKENIZER, BECAUSE IT MOVES THE THIRD DECIMAL
-------------------------------------------------
This reuses `abliteration_effect_check.jaccard`, whose `words()` is `[a-z]+`. The figures first
published on 2026-09-20 (0.345 / 0.339 / 0.380 / 0.377) came from an ad-hoc `[a-z']+` instead --
apostrophes kept, so "don't" is one token rather than "don" plus "t". Three of the four move by
0.001-0.002 between the two. The canonical function is authoritative here and its values are the
EXPECTED below; the older figures are recorded beside them so the discrepancy is visible rather
than quietly resolved.

None of this touches the conclusion. Every between-arm value sits inside the 0.303-0.392
same-model band under either tokenizer, and below this model's own same-weights resample, so the
"~65-70% of wording rewrites" claim is unsupported either way. Only the digits move.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from abliteration_effect_check import jaccard  # noqa: E402  -- the single word-set measure

ORIGINAL = os.path.join(STUDY, "data", "2026-05-27-abliteration-gemma2", "raw")
RECOLLECT = os.path.join(STUDY, "data", "2026-09-20-gemma2-recollect", "raw")

#: The band `abliteration_effect_check` measured for one model resampled against itself.
SAME_MODEL_BAND = (0.303, 0.392)

#: (label, left file, right file, expected under [a-z]+, as published 2026-09-20 under [a-z']+)
ROWS = [
    ("stock vs abliterated, original run", (ORIGINAL, "gemma-2-9b-stock"),
     (ORIGINAL, "gemma-2-9b-abliterated"), 0.347, 0.345),
    ("stock vs abliterated, 2026-09-20 resample", (RECOLLECT, "gemma-2-9b-stock"),
     (RECOLLECT, "gemma-2-9b-abliterated"), 0.341, 0.339),
    ("stock vs stock, SAME weights", (ORIGINAL, "gemma-2-9b-stock"),
     (RECOLLECT, "gemma-2-9b-stock"), 0.381, 0.380),
    ("abliterated vs abliterated, SAME weights", (ORIGINAL, "gemma-2-9b-abliterated"),
     (RECOLLECT, "gemma-2-9b-abliterated"), 0.377, 0.377),
]


def load(directory: str, arm: str) -> dict:
    """Records keyed by the cell they belong to, so pairings join on the item and not on order."""
    path = os.path.join(directory, f"{arm}.jsonl")
    if not os.path.exists(path):
        return {}
    out = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            r = json.loads(line)
            out[(r["question_id"], r["condition"])] = r
    return out


def mean_jaccard(left: dict, right: dict):
    shared = sorted(set(left) & set(right))
    if not shared:
        return None, 0
    vals = [jaccard(left[k].get("response_text") or "", right[k].get("response_text") or "")
            for k in shared]
    return statistics.mean(vals), len(shared)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if any row differs from its expected value at 3dp")
    args = ap.parse_args(argv)

    for d in (ORIGINAL, RECOLLECT):
        if not os.path.isdir(d):
            print(f"missing run directory: {os.path.relpath(d, STUDY)}")
            return 1

    print("GEMMA-2-9B WORD-SET JACCARD -- the same-weights control")
    print("  Between-arm overlap means nothing without the same-weights rows beneath it:")
    print("  an apparent rewrite is only a rewrite if it exceeds what resampling alone gives.\n")
    print("  %-44s %8s %9s %6s" % ("pairing", "jaccard", "expected", "n"))

    drift = []
    computed = {}
    for label, (ld, la), (rd, ra), expected, published in ROWS:
        value, n = mean_jaccard(load(ld, la), load(rd, ra))
        if value is None:
            print("  %-44s %8s" % (label, "no shared cells"))
            drift.append((label, None, expected))
            continue
        computed[label] = value
        mark = "" if round(value, 3) == expected else "   <-- DRIFT"
        print("  %-44s %8.3f %9.3f %6d%s" % (label, value, expected, n, mark))
        if round(value, 3) != expected:
            drift.append((label, value, expected))

    lo, hi = SAME_MODEL_BAND
    between = [v for k, v in computed.items() if "vs abliterated" in k and "SAME" not in k]
    within = [v for k, v in computed.items() if "SAME weights" in k]
    if between and within:
        print(f"\n  same-model band, measured elsewhere in this study: {lo:.3f} - {hi:.3f}")
        print(f"  between-arm: {', '.join(f'{v:.3f}' for v in between)}"
              f"   within-arm, same weights: {', '.join(f'{v:.3f}' for v in within)}")
        if all(lo <= v <= hi for v in between) and all(v > max(between) for v in within):
            print("  VERDICT: the between-arm overlap is inside the band AND below this model's")
            print("  own resample noise. The text change is NOT ESTABLISHED for gemma-2-9b.")

    print("\n  The figures published 2026-09-20 used an apostrophe-preserving tokenizer:")
    print("  " + ", ".join(f"{p:.3f}" for *_ , p in [(r[0], r[4]) for r in ROWS]))
    print("  This script uses abliteration_effect_check.jaccard, which is [a-z]+ and is the")
    print("  implementation the rest of the study's Jaccard figures come from.")

    if args.check:
        if drift:
            print(f"\n{len(drift)} row(s) drifted from expected:")
            for label, got, exp in drift:
                print(f"  {label}: got {got if got is None else round(got, 3)}, expected {exp}")
            return 1
        print("\nall four rows match")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
