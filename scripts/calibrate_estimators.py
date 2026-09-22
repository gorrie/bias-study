#!/usr/bin/env python3
"""What is each estimator's false-positive rate AT THE n IT IS ACTUALLY USED AT?

WHY THIS EXISTS
---------------
Three times in one day (2026-09-19) a decision procedure was trusted because it was
principled, and each time its real error rate at the real sample size was something nobody had
measured:

| procedure | assumed | measured |
|---|---|---|
| pair bootstrap | nominal 5% | **49.6%** -- withdrawn |
| clause-factorial order floor | a threshold | **8.3 / 41.8 / 21.1%** under the null |
| sheet bootstrap | "6.2%" | disagrees with an exact test on 20 of 241 |

And the 6.2% was never a measurement: it is a docstring at `position_analysis.py:285`.
`--selftest` reports 12.5%, on SYNTHETIC nulls it generates itself -- which is the failure
`LEARNINGS` #2 warns about, a detector validated against input it chose.

**This builds the null out of the corpus.** A cell is split in half at random and the two
halves are contrasted: there is no treatment, so every rejection is a false positive. The
halves carry the corpus's own pathologies -- including the 45 cells of 393 whose sheets are
nearly identical, which is exactly the population a synthetic null never generates.

    python scripts/calibrate_estimators.py
    python scripts/calibrate_estimators.py --draws 400 --json
    python scripts/calibrate_estimators.py --check    # exit 1 if any estimator exceeds BAR

Exit 0 all calibrated, 1 an estimator is anti-conservative, 2 NOT APPLICABLE.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import random
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, HERE)

WAVE = "2026-09-16-ratchet-v3-wave"

#: An estimator whose measured false-positive rate exceeds this is ANTI-CONSERVATIVE and its
#: intervals cannot be read at face value. Set at 2x nominal rather than at nominal, because a
#: split-half null on real cells is itself noisy and a bar at exactly 0.05 would fail on
#: sampling error. The pair bootstrap scored 49.6% against this; it is not a tight bar.
BAR = 0.10
NOMINAL = 0.05

#: Cells below this are not split -- fewer than three per half leaves nothing to resample.
MIN_SHEETS = 6


def _cells(run_dir=WAVE, min_sheets=MIN_SHEETS):
    import position_analysis as P
    from studypaths import run_path
    bank = P.load_bank()
    per = P.sheet_positions(P.load_records(str(run_path(run_dir))), P.pair_index(bank))
    return {k: v for k, v in per.items() if len(v) >= min_sheets}


def _split(sheets, rng):
    idx = list(range(len(sheets)))
    rng.shuffle(idx)
    half = len(idx) // 2
    return [sheets[i] for i in idx[:half]], [sheets[i] for i in idx[half:]]


def calibrate_bootstrap(cells, draws, seed):
    """Split-half on real cells. No treatment exists, so every rejection is a false positive."""
    import position_analysis as P
    rng = random.Random(seed)
    keys = sorted(cells)
    hits = n = 0
    degen_hits = degen_n = 0
    for i in range(draws):
        k = keys[rng.randrange(len(keys))]
        a, b = _split(cells[k], rng)
        if len(a) < 2 or len(b) < 2:
            continue
        per = {("x", "A"): a, ("x", "B"): b}
        r = P.contrast_sheets(per, "x", "A", "B", seed=rng.randrange(10 ** 6))
        if not r:
            continue
        n += 1
        means = [st.mean(s.values()) for s in cells[k]]
        degenerate = st.pstdev(means) < 0.02
        if degenerate:
            degen_n += 1
        if r["excludes_zero"]:
            hits += 1
            if degenerate:
                degen_hits += 1
    return {"tested": n, "false_positives": hits,
            "rate": (hits / n) if n else None,
            "degenerate_tested": degen_n,
            "degenerate_rate": (degen_hits / degen_n) if degen_n else None}


def calibrate_exact(cells, draws, seed):
    """The same null, judged by an exact permutation test, as the comparison point."""
    rng = random.Random(seed)
    keys = sorted(cells)
    hits = n = 0
    for _ in range(draws):
        k = keys[rng.randrange(len(keys))]
        a, b = _split(cells[k], rng)
        if len(a) < 2 or len(b) < 2:
            continue
        ma = [st.mean(s.values()) for s in a]
        mb = [st.mean(s.values()) for s in b]
        obs = abs(st.mean(ma) - st.mean(mb))
        pool = ma + mb
        if math.comb(len(pool), len(ma)) > 20000:
            continue
        hit = tot = 0
        for c in itertools.combinations(range(len(pool)), len(ma)):
            g = [pool[j] for j in c]
            h = [pool[j] for j in range(len(pool)) if j not in c]
            tot += 1
            if abs(st.mean(g) - st.mean(h)) >= obs - 1e-12:
                hit += 1
        n += 1
        if (hit / tot) <= NOMINAL:
            hits += 1
    return {"tested": n, "false_positives": hits, "rate": (hits / n) if n else None}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run", default=WAVE)
    ap.add_argument("--draws", type=int, default=300)
    ap.add_argument("--seed", type=int, default=20260919)
    ap.add_argument("--json", action="store_true")
    # argparse re-formats help strings, so a literal % must survive its own pass too.
    ap.add_argument("--check", action="store_true",
                    help="exit 1 when an estimator's measured false-positive rate exceeds "
                         "the bar (%d percent)" % int(100 * BAR))
    a = ap.parse_args(argv)

    cells = _cells(a.run)
    if not cells:
        print("NOT APPLICABLE: no cell in %s has >= %d sheets to split." % (a.run, MIN_SHEETS))
        return 2

    boot = calibrate_bootstrap(cells, a.draws, a.seed)
    exact = calibrate_exact(cells, a.draws, a.seed)
    res = {"run": a.run, "cells_eligible": len(cells), "draws": a.draws,
           "bar": BAR, "nominal": NOMINAL, "sheet_bootstrap": boot, "exact_permutation": exact}

    if a.json:
        print(json.dumps(res, indent=2, sort_keys=True))
        return 1 if (a.check and (boot["rate"] or 0) > BAR) else 0

    print("ESTIMATOR CALIBRATION -- the null is built FROM THE CORPUS, not generated")
    print("  A cell with >= %d sheets is split in half at random and the halves contrasted."
          % MIN_SHEETS)
    print("  No treatment exists, so every rejection is a false positive. The halves carry")
    print("  the corpus's own pathologies, including the cells whose sheets barely differ --")
    print("  the population a synthetic null never produces.")
    print()
    print("  %d eligible cell(s) in %s, %d split(s)" % (len(cells), a.run, a.draws))
    print()
    print("  %-26s %8s %10s %s" % ("estimator", "tested", "false +", "rate"))
    for label, r in (("sheet bootstrap", boot), ("exact permutation", exact)):
        rate = r["rate"]
        print("  %-26s %8d %10d %s" % (label, r["tested"], r["false_positives"],
                                       "n/a" if rate is None else "%.1f%%" % (100 * rate)))
    if boot.get("degenerate_rate") is not None:
        print()
        print("  sheet bootstrap on the near-identical cells only: %.1f%% over %d split(s)"
              % (100 * boot["degenerate_rate"], boot["degenerate_tested"]))
    print()
    print("  nominal %.0f%%, bar %.0f%%" % (100 * NOMINAL, 100 * BAR))

    bad = (boot["rate"] or 0) > BAR
    if bad:
        print()
        print("  *** THE SHEET BOOTSTRAP IS ANTI-CONSERVATIVE ON THIS CORPUS ***")
        print("  Its intervals cannot be read at face value and its p-values understate.")
        print("  This is the shape that made the pair bootstrap reject 49.6%% of true nulls")
        print("  while looking principled. Report the exact test, or report both.")
    else:
        print()
        print("  within the bar. Note what that does and does not license: the rate is")
        print("  measured over cells of the sizes this corpus actually has, so it does not")
        print("  transfer to an arm collected at a different depth. Re-run per arm.")
    return 1 if (a.check and bad) else 0


if __name__ == "__main__":
    raise SystemExit(main())
