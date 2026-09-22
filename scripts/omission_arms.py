#!/usr/bin/env python3
"""The as-is vs renumbered arm contrast, with the exact test that decides it.

WHY THIS FILE EXISTS. Two results documents reported this contrast with a Fisher exact
p-value -- 1.8e-4 for the local arm, 8.4e-4 for the pinned hosted arm -- and NOTHING IN THIS
REPOSITORY COMPUTED EITHER ONE. `grep -ril fisher scripts/` returned no file. The counts had
also drifted: `RESULTS-2026-09-21-omission-pinned.md` said 10 of 191 as-is partial sheets
where `item_omission.py` reads 9 of 190, because a sheet moved into the excluded set after
the document was written. A headline p-value with no command behind it is the defect this
study is about, sitting in this study.

The sheet classification is NOT reimplemented here. `item_omission.load_sheets` owns it --
which sheets are attempts, which are transport, refusal or budget -- so the two tools cannot
drift apart on what a partial sheet is. This file adds only the 2x2 and the test.

The test is one-sided by pre-registration (`PREREG-2026-09-18-omission-orders.md`): the
hypothesis names a direction, that non-monotonic numbering loses cells and renumbering does
not. It is computed exactly from the hypergeometric distribution with integer arithmetic --
no scipy, no normal approximation, nothing that changes answer with a library version.

    python scripts/omission_arms.py --run 2026-09-18-omission-orders
    python scripts/omission_arms.py --run 2026-09-20-omission-hosted-pinned --json
    python scripts/omission_arms.py --selftest

Reads only. No API calls.
"""
from __future__ import annotations

import argparse
import collections
import io
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import studypaths  # noqa: E402
from item_omission import load_sheets, load_bank  # noqa: E402

ARMS = ("asis", "renum")


def fisher_one_sided(a, b, c, d):
    """P(X >= a) for the 2x2 [[a, b], [c, d]], hypergeometric, exact in integers.

    `a` is the cell the directional hypothesis predicts is LARGE: as-is partial sheets. The
    tail is therefore the upper one. Returned as a float only at the last step, so the
    accumulation itself never loses a digit.
    """
    row1, row2 = a + b, c + d
    col1 = a + c
    total = row1 + row2
    if total == 0:
        return None
    num = 0
    lo = max(0, col1 - row2)
    hi = min(row1, col1)
    for k in range(a, hi + 1):
        num += (math.comb(row1, k) * math.comb(row2, col1 - k))
    den = math.comb(total, col1)
    # Guard the degenerate table: when one margin is zero every k gives the same table and
    # the p-value is 1, which is a true statement about no information rather than a result.
    if lo == hi:
        return 1.0
    return num / den


def arm_counts(sheets):
    """{model: {arm: [partial, complete]}} plus a pooled row."""
    per = collections.defaultdict(lambda: {a: [0, 0] for a in ARMS})
    for sh in sheets:
        if sh["arm"] not in ARMS:
            continue
        cell = per[sh["model"]][sh["arm"]]
        cell[0 if sh["dropped"] else 1] += 1
    return per


def summarise(per):
    pooled = {a: [0, 0] for a in ARMS}
    for model in per:
        for arm in ARMS:
            pooled[arm][0] += per[model][arm][0]
            pooled[arm][1] += per[model][arm][1]
    a, b = pooled["asis"]
    c, d = pooled["renum"]
    return pooled, fisher_one_sided(a, b, c, d)


def rate(cell):
    n = cell[0] + cell[1]
    return (cell[0], n, (100.0 * cell[0] / n) if n else 0.0)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", default="2026-09-18-omission-orders")
    ap.add_argument("--also", action="append", default=[],
                    help="another run to POOL with --run. The published pooled figure "
                         "(local 5 builds + 2 hosted models, p = 2.7e-5) was reproducible "
                         "only by hand until this existed.")
    ap.add_argument("--only-models", default=None,
                    help="comma-separated model ids; restrict the pool to these. Used for "
                         "the 2-model hosted slice, which is a SUBSET of a run that has "
                         "since grown a full roster.")
    ap.add_argument("--items", default="data/ratchet-battery.json")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)

    if a.selftest:
        return selftest()

    items = load_bank(os.path.join(studypaths.STUDY_DIR, a.items))
    expected = {it["id"] for it in items}
    sheets, skipped = [], collections.Counter()
    for name in [a.run] + a.also:
        run_dir = (name if os.path.isdir(name)
                   else os.path.join(studypaths.STUDY_DIR, "runs", name))
        if not os.path.isdir(run_dir):
            print("no such run directory: %s" % run_dir, file=sys.stderr)
            return 2
        got, skip = load_sheets(run_dir, expected)
        sheets.extend(got)
        skipped.update(skip)

    if a.only_models:
        wanted = {m.strip() for m in a.only_models.split(",") if m.strip()}
        # A filter that matches nothing is the vacuous pass in its usual disguise: it would
        # print a clean empty table and exit 0.
        sheets = [s for s in sheets if s["model"] in wanted]
        missing = wanted - {s["model"] for s in sheets}
        if missing:
            print("NAMED MODELS ABSENT from the pool: %s" % ", ".join(sorted(missing)),
                  file=sys.stderr)
            return 2

    per = arm_counts(sheets)
    if not per:
        print("CHECKED NOTHING -- no sheet in %s carries an arm label. NOT a pass." % a.run)
        return 2
    pooled, p = summarise(per)
    if pooled["asis"][0] + pooled["asis"][1] == 0 or pooled["renum"][0] + pooled["renum"][1] == 0:
        print("CHECKED NOTHING -- one arm is empty, so there is no contrast. NOT a pass.")
        return 2

    if a.json:
        print(json.dumps({
            "run": a.run,
            "pooled": {arm: {"partial": pooled[arm][0], "sheets": sum(pooled[arm])}
                       for arm in ARMS},
            "fisher_one_sided": p,
            "excluded": dict(skipped),
            "models": {m: {arm: {"partial": per[m][arm][0], "sheets": sum(per[m][arm])}
                           for arm in ARMS} for m in sorted(per)},
        }, indent=2))
        return 0

    print("")
    print("  ARM CONTRAST -- as-is numbering against renumbered: %s" % a.run)
    print("  A partial sheet is one the model ANSWERED and answered incompletely. Sheets lost")
    print("  to transport, refusal or budget are excluded from both arms and printed below.")
    print("")
    print("  %-40s %14s %14s" % ("model", "as-is", "renumbered"))
    for m in sorted(per):
        cells = [rate(per[m][arm]) for arm in ARMS]
        print("  %-40s %6d / %-5d %6d / %-5d"
              % (m[:40], cells[0][0], cells[0][1], cells[1][0], cells[1][1]))
    print("  %-40s %s" % ("", "-" * 29))
    ca, cr = rate(pooled["asis"]), rate(pooled["renum"])
    print("  %-40s %6d / %-5d %6d / %-5d" % ("ALL", ca[0], ca[1], cr[0], cr[1]))
    print("  %-40s %11.1f%% %13.1f%%" % ("", ca[2], cr[2]))
    print("")
    print("  Fisher exact, one-sided (as-is > renumbered): p = %.3g" % p)
    print("  One-sided by pre-registration -- the hypothesis names a direction.")
    if skipped:
        print("")
        print("  excluded, and why:")
        for reason, n in sorted(skipped.items()):
            print("    %-34s %d" % (reason, n))

    # The concentration is the caveat a reader needs beside the p-value, so it is printed
    # here rather than left to prose. One model carrying the arm is a different finding from
    # eight models agreeing, and the p-value cannot tell them apart.
    losses = sorted(((per[m]["asis"][0], m) for m in per), reverse=True)
    top_n, top_m = losses[0]
    total = pooled["asis"][0]
    if total:
        print("")
        print("  CONCENTRATION: %d of %d as-is partial sheets are %s (%.0f%%)."
              % (top_n, total, top_m, 100.0 * top_n / total))
        if top_n * 2 > total:
            print("  More than half the arm is one model. Do not read this as agreement")
            print("  across models; it is one model with an effect and the rest near zero.")
    return 0


def selftest():
    """The test against tables whose answer is known independently of this code."""
    checks = []

    # A 2x2 with a closed form: all of one row in one column.
    # [[2,0],[0,2]] -- P = C(2,2)C(2,0)/C(4,2) = 1/6.
    checks.append(("clean separation 2x2", fisher_one_sided(2, 0, 0, 2), 1.0 / 6.0))
    # Textbook Fisher tea-tasting: [[3,1],[1,3]], one-sided P(X>=3) = (16+1)/70.
    checks.append(("tea tasting", fisher_one_sided(3, 1, 1, 3), 17.0 / 70.0))
    # No information: one margin zero.
    checks.append(("empty margin", fisher_one_sided(0, 5, 0, 5), 1.0))
    # Symmetry: a table with equal rates must be far from significant.
    got = fisher_one_sided(5, 45, 5, 45)
    checks.append(("equal rates are not significant", got > 0.5, True))

    bad = 0
    for name, got, want in checks:
        ok = (abs(got - want) < 1e-12) if isinstance(want, float) else (got == want)
        print("  %-34s %-22s %s" % (name, got, "OK" if ok else "FAIL want %s" % (want,)))
        bad += 0 if ok else 1

    # The loader is the other half, and a selftest that never opens a record is the vacuous
    # pass this project keeps finding. Read the pre-registered run and assert its shape.
    run_dir = os.path.join(studypaths.STUDY_DIR, "runs", "2026-09-18-omission-orders")
    if os.path.isdir(run_dir):
        items = load_bank(os.path.join(studypaths.STUDY_DIR, "data/ratchet-battery.json"))
        sheets, _ = load_sheets(run_dir, {it["id"] for it in items})
        per = arm_counts(sheets)
        pooled, p = summarise(per)
        n = sum(pooled["asis"]) + sum(pooled["renum"])
        print("  %-34s %d sheets, both arms present, p = %.3g"
              % ("real run reads", n, p))
        if n == 0 or min(sum(pooled[arm]) for arm in ARMS) == 0:
            print("    FAIL -- the loader returned nothing to test on")
            bad += 1
    else:
        print("  %-34s run absent, NOT checked" % "real run reads")
        bad += 1
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
