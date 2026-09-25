#!/usr/bin/env python3
"""How hard does a model state its answer, and what moves that? Two findings, one command.

WHY THIS EXISTS
---------------
`FINDINGS-2026-09-17-battery.md` §1 and §2 report two results that the paper states in prose
and that NOTHING in the tree recomputes:

  1. Under the balance instruction, models use the scale ENDPOINTS less. The result is the
     SIGN, not the size -- a panel-level sign test, not a per-model effect.
  2. Some models vacate both endpoints ENTIRELY -- zero strong answers on all 32 items, in
     every run -- while changing most of their answers. A pooled side-flip statistic reports
     such a model as showing no effect, which is the strongest argument in this corpus for
     never quoting one statistic alone.

This file's own rule is that every figure has a recorded command. Four body findings broke it;
this closes two of them.

WHY THIS STATISTIC AND NOT POSITION
-----------------------------------
`position_analysis` measures WHICH WAY a model answers. This measures HOW HARD. They come
apart badly: §2 of the paper reports frontier models changing about 1 of 32 sides under
reordering and about 11 of 32 intensities. Every published instrument in this class scores
side, so the quantity that moves is the one nobody reports -- and a paper that measured only
position would reproduce that error inside a study whose subject is that error.

    python scripts/strong_shift.py
    python scripts/strong_shift.py --run <dir> --vacate
    python scripts/strong_shift.py --selftest

Exit 0 computed, 2 NOT APPLICABLE.
"""
from __future__ import annotations

import argparse
import collections
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import studypaths as _SP
import position_analysis as PA

#: 0-3 forced choice. Strongly Disagree and Strongly Agree are the endpoints.
STRONG = (0, 3)

#: Conditions, in the order the paper states them.
BASELINE = "N"
ARMS = ("A", "P", "D")

#: WHAT REPLACES THE INSTRUCTION, measured against it rather than against the baseline. On the
#: retired questionnaire a content-free placebo restored endpoint answers as fully as a demand to
#: commit, and "what replaces the instruction does not matter" was the reading. On the battery the
#: three contrasts below separate the readings: the placebo returning A to baseline, the directive
#: overshooting it, and the two differing from each other.
REPLACEMENTS = (("P", "A"), ("D", "A"), ("D", "P"))


def strong_counts(records):
    """(model, condition) -> [strong answers per sheet]."""
    out = collections.defaultdict(list)
    for rec in records:
        answers = rec.get("answers") or {}
        if not answers:
            continue
        n = sum(1 for v in answers.values() if v in STRONG)
        out[(rec.get("model"), rec.get("condition"))].append(n)
    return out


def sign_test(pairs):
    """Two-sided exact sign test on (before, after). Ties dropped and COUNTED."""
    up = sum(1 for a, b in pairs if b > a)
    down = sum(1 for a, b in pairs if b < a)
    ties = len(pairs) - up - down
    n = up + down
    if n == 0:
        return up, down, ties, None
    k = min(up, down)
    # exact binomial tail at p = 0.5, doubled
    tail = sum(math.comb(n, i) for i in range(k + 1)) / float(2 ** n)
    return up, down, ties, min(1.0, 2.0 * tail)


def median(vals):
    v = sorted(vals)
    if not v:
        return None
    m = len(v) // 2
    return v[m] if len(v) % 2 else (v[m - 1] + v[m]) / 2.0


def selftest():
    fails = []
    # A model that drops every endpoint must show a negative shift and a significant sign test.
    pairs = [(10, 2)] * 12
    up, down, ties, p = sign_test(pairs)
    if not (down == 12 and up == 0 and p is not None and p < 0.01):
        fails.append("12 of 12 models moving down read as up=%d down=%d p=%s" % (up, down, p))
    # Ties must be dropped from the test and reported, not counted as agreement.
    up, down, ties, p = sign_test([(5, 5)] * 8 + [(5, 3)] * 2)
    if ties != 8 or up + down != 2:
        fails.append("ties miscounted: up=%d down=%d ties=%d" % (up, down, ties))
    # A perfectly split panel must not be significant.
    up, down, ties, p = sign_test([(1, 2)] * 6 + [(2, 1)] * 6)
    if p is None or p < 0.9:
        fails.append("a 6/6 split returned p=%s, should be ~1.0" % p)
    for f in fails:
        print("  FAIL  %s" % f)
    if fails:
        return 1
    print("  selftest: 3 checks passed -- direction, tie handling, and a split panel.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", default="2026-09-16-ratchet-v3-wave")
    ap.add_argument("--vacate", action="store_true",
                    help="list models reaching zero strong answers, and on how many runs")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()

    run_dir = (a.run if os.path.isdir(a.run)
               else os.path.join(_SP.STUDY_DIR, "runs", a.run))
    if not os.path.isdir(run_dir):
        print("no such run directory: %s" % run_dir)
        return 2
    records = PA.load_records(run_dir)
    if not records:
        print("CHECKED NOTHING -- no valid sheets. NOT a result.")
        return 2

    counts = strong_counts(records)
    models = sorted({m for (m, _c) in counts})
    n_items = 32

    print("")
    print("  STRONG-ANSWER USE -- endpoints of %d items, per model, modal across runs"
          % n_items)
    print("  The result is the SIGN. The size is per model and is reported beside it.")
    print("")
    print("  %-10s %7s %8s %8s %9s %10s" % ("contrast", "models", "down", "up", "unchanged",
                                            "sign test"))
    for arm, ref in [(x, BASELINE) for x in ARMS] + list(REPLACEMENTS):
        if (arm, ref) == REPLACEMENTS[0]:
            print("  -- against the balance instruction, and the two replacements against each other")
        pairs = []
        for m in models:
            base = counts.get((m, ref))
            other = counts.get((m, arm))
            if not base or not other:
                continue
            pairs.append((median(base), median(other)))
        if not pairs:
            print("  %-10s no model carries both arms" % ("%s - %s" % (arm, ref)))
            continue
        up, down, ties, p = sign_test(pairs)
        shifts = [b - a_ for a_, b in pairs]
        print("  %-10s %7d %8d %8d %9d %10s   median shift %+.0f  range %+.0f..%+.0f"
              % ("%s - %s" % (arm, ref), len(pairs), down, up, ties,
                 ("p = %.2g" % p) if p is not None else "-",
                 median(shifts), min(shifts), max(shifts)))

    # ---- the vacating models
    print("")
    print("  MODELS THAT VACATE BOTH ENDPOINTS -- zero strong answers of %d" % n_items)
    print("")
    vac_all, vac_modal = [], []
    for m in models:
        for cond in (BASELINE,) + ARMS:
            runs = counts.get((m, cond))
            if not runs:
                continue
            base = counts.get((m, BASELINE))
            if cond == BASELINE or not base:
                continue
            # A MODEL CANNOT VACATE WHAT IT NEVER OCCUPIED. The first version of this listing
            # reported `gemma-4-12B`, `gemma2:9b-instruct-q8_0` and `deepseek-v4-flash` as
            # vacating both endpoints under an arm -- all three have a BASELINE median of
            # zero. They never use the endpoints under any condition, which is a different
            # and less interesting fact, and filing it under "the instruction emptied them"
            # would attribute to the manipulation something the model does anyway.
            if median(base) <= 0:
                continue
            # n=1 IS NOT "ALL RUNS". One sheet at zero is one sheet, and printing it beside a
            # model measured over fifteen invites the reader to weigh them equally.
            if all(v == 0 for v in runs) and len(runs) >= 2:
                vac_all.append((m, cond, len(runs), median(base)))
            elif median(runs) == 0:
                vac_modal.append((m, cond, len(runs), median(base)))

    if not vac_all and not vac_modal:
        print("    none")
    for m, cond, n, base in sorted(vac_all):
        print("    %-34s %s  ZERO on ALL %d run(s)   baseline median %g"
              % (m[:34], cond, n, base))
    for m, cond, n, base in sorted(vac_modal):
        print("    %-34s %s  zero in the MODAL of %d   baseline median %g"
              % (m[:34], cond, n, base))

    print("")
    print("  A model at zero under an arm and non-zero at baseline has stopped using the")
    print("  scale's endpoints entirely while still answering every item. If it also changes")
    print("  few SIDES, a pooled side-flip statistic reports it as unaffected -- which is why")
    print("  this file exists beside position_analysis rather than inside it.")
    if a.vacate and (vac_all or vac_modal):
        print("")
        print("  Cross-check a named model with:")
        print("    python scripts/position_analysis.py %s --placebo-table"
              % os.path.basename(run_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
