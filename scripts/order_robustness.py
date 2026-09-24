#!/usr/bin/env python3
"""Does the suppression effect survive presentation-order randomisation?

WRITTEN BEFORE THE DATA LANDED, deliberately. Specifying the test after seeing the numbers
is how a result gets fitted to its own noise, and this project has enough of that already.

THE QUESTION
------------
The one claim that survived a hostile read is: a forced-balance instruction (A) suppresses
endpoint answers relative to no instruction at all (B). Every cell behind it was collected
in a SINGLE presentation order.

Presentation order is the largest confound measured in this project -- reordering the same
62 items flips up to 24 of them, which is more than ablation, more than requantisation, and
more than any prompt condition. The drift null's p90 was 22, a number order alone could
manufacture. So until the effect is measured across orders, it is not defensible.

THE TEST, FIXED IN ADVANCE
--------------------------
For each model, suppression S = endpoint%(B) - endpoint%(A), computed separately in each
presentation order.

  PASSES if  sign(S) is the same in every order
        AND  min |S| across orders  >  the model's own between-order disagreement

The second clause is the important one. Between-order disagreement is measured WITHIN a
condition -- how much the same model, same condition, same seeds moves when only the item
order changes. If the effect is smaller than that, it is order noise wearing the effect's
name.

  FAILS if the sign flips in any order, or the smallest effect is inside the order band.

No other outcome is a pass. In particular a result that holds in two orders of three is a
FAIL, not a partial success -- with three orders that is one coin-flip away from noise.

Usage:
    python order_robustness.py --runs runs/2026-08-31-order-control runs/2026-08-30-temp0
"""
from __future__ import annotations

import argparse
import collections
import glob
import io
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import floor_table as F  # noqa: E402  -- the ONE instrument-selection rule
import studypaths as _SP  # noqa: E402


def ext(p):
    return p in (0, 3)


def side(p):
    return p >= 2


def load(dirs):
    """(model, condition, shuffle_seed) -> list of answer dicts."""
    cells = collections.defaultdict(list)
    for d in dirs:
        for p in glob.glob(os.path.join(d, "**", "*.jsonl"), recursive=True):
            for line in io.open(p, encoding="utf-8"):
                if not line.strip():
                    continue
                r = json.loads(line)
                if not _SP.is_run_record(r) or not r.get("valid"):
                    continue
                # SAME RUNNER, SAME SCHEMA, DIFFERENT INSTRUMENT. The project's
                # own mirrored bank (60 items, 30 pairs) is administered by
                # run_battery.py and lands in the same tree with the same
                # schema, so a schema check alone pools it with the 62-item
                # compass sheets. The full rationale is on
                # floor_table._instrument_matches; this loader is a second copy
                # of the same selection and has to answer the same way, or the
                # order floor and the floors table disagree about which corpus
                # they describe.
                if not F._instrument_matches(r):
                    continue
                vals = [a["position"] for a in r["answers"]]
                if vals and len(set(vals)) == 1:
                    continue  # degenerate sheet
                cells[(r["model"], r["condition"], r.get("shuffle_seed"))].append(
                    {a["q"]: a["position"] for a in r["answers"]})
    return cells


def modal(runs):
    acc = collections.defaultdict(list)
    for r in runs:
        for q, v in r.items():
            acc[q].append(v)
    return {q: collections.Counter(v).most_common(1)[0][0] for q, v in acc.items()}


def endpoint_pct(answers):
    return 100.0 * st.mean([int(ext(v)) for v in answers.values()])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--runs", nargs="+", required=True)
    args = ap.parse_args(argv)

    cells = load(args.runs)
    models = sorted({m for m, _, _ in cells})

    print("ORDER ROBUSTNESS -- suppression S = endpoint%(B) - endpoint%(A), per order")
    print("PASS requires: same sign in every order AND min|S| > that model's order band")
    print()
    header = "%-28s %7s %7s %7s %8s %10s %s" % (
        "model", "ord1 S", "ord2 S", "ord3 S", "min|S|", "order band", "verdict")
    print(header)
    passes = fails = skipped = 0
    for m in models:
        orders = sorted({o for mm, c, o in cells if mm == m},
                        key=lambda x: (x is not None, x))
        per = []
        for o in orders:
            a = cells.get((m, "A", o))
            b = cells.get((m, "B", o))
            if not a or not b:
                continue
            per.append((o, endpoint_pct(modal(b)) - endpoint_pct(modal(a))))
        if len(per) < 2:
            skipped += 1
            continue

        # Order band: worst within-condition disagreement between orders, in endpoint points.
        band = 0.0
        for cond in ("A", "B"):
            vals = [endpoint_pct(modal(cells[(m, cond, o)]))
                    for o in orders if cells.get((m, cond, o))]
            if len(vals) > 1:
                band = max(band, max(vals) - min(vals))

        svals = [s for _, s in per]
        same_sign = all(s > 0 for s in svals) or all(s < 0 for s in svals)
        smallest = min(abs(s) for s in svals)
        ok = same_sign and smallest > band
        passes += ok
        fails += (not ok)
        cols = [("%+7.0f" % s) for _, s in per] + ["      -"] * (3 - len(per))
        why = "PASS" if ok else ("sign flips" if not same_sign else "inside order band")
        print("%-28s %s %s %s %8.0f %10.0f %s"
              % (m.split("/")[-1][:28], cols[0], cols[1], cols[2], smallest, band, why))

    print()
    print("%d pass, %d fail, %d skipped for missing cells" % (passes, fails, skipped))
    print()
    if not passes and not fails:
        # A pre-registered test that READ NOTHING must not print its own FAIL.
        # This branch used to fall through to the `else` below and publish "The
        # effect does not survive order randomisation. It is not defensible on
        # this instrument, and neither is anything else measured single-order."
        # -- a categorical negative verdict, exit 0, from zero comparisons.
        # Pointing it at a nonexistent run produced exactly that, and so did
        # pointing it at the right run under the wrong root.
        print("CHECKED NOTHING -- 0 models yielded a usable order comparison "
              "(%d skipped for missing cells)." % skipped)
        print("This is NOT a result. It is an empty selection: wrong run name, wrong")
        print("run root, or the order cells were never collected. Nothing about order")
        print("robustness may be concluded from this output, in either direction.")
        return 2
    if passes and not fails:
        print("The suppression effect is order-robust on every model tested.")
    elif passes:
        print("MIXED. The effect is order-robust on some models and not others; the claim")
        print("must be scoped to the models that pass, named individually.")
    else:
        print("The effect does not survive order randomisation. It is not defensible on")
        print("this instrument, and neither is anything else measured single-order.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
