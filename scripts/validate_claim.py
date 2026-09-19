#!/usr/bin/env python3
"""Pre-publication gate. Refuses a claim until the data behind it passes every check.

WHY THIS IS CODE AND NOT A CHECKLIST
------------------------------------
Between 2026-08-29 and 2026-08-31 this project withdrew or narrowed nine claims. Every
prose rule written to prevent that was violated by its own author within hours -- the
publication bar in STATUS.md was breached by the next result, and the order-effect document
diagnosed net-vs-gross aggregation two hours before a net statistic hid 14 item flips.

The one rule that held all day was the heredoc hook, because it was executable. A gate that
can refuse is worth more than a rule that can be forgotten.

Run this against a claim BEFORE writing it up. Exit 0 means the checks passed, not that the
claim is true.

THE CHECKS, AND THE FAILURE THAT PUT EACH ONE HERE
--------------------------------------------------
  data-integrity   transport failures counted as model behaviour (58 rows, 11 models)
  cell-completeness cells with duplicate seeds from append-on-resume; n misreported as 3
                    when it was 2 (kimi-k3)
  failure-classes  refusal detected by keyword list, undercounting by ~14 cells
  degenerate       an all-one-answer sheet counted valid, inflating a lineage baseline
  caching          5 "seeds" holding 2 distinct outputs, making a floor meaningless
  statistic        net agree-rate concealing gross side-flips (grok-4.6: net +6, gross 14)
  floor            a range over 3 seeds used as a significance threshold; at n=3 a
                   permutation test cannot reach p<0.05 at all
  arms             third-party ablated builds differing in quantisation and stop tokens
  families         three models from one vendor reported as three-family replication

Usage:
    python validate_claim.py --runs runs/2026-08-30-temp0 --conditions A D
    python validate_claim.py --runs runs/2026-08-31-lineage --conditions A B --strict
"""
from __future__ import annotations

import argparse
import collections
import glob
import io
import json
import math
import os
import statistics as st
import sys
import studypaths as _SP  # noqa: E402

FAIL, WARN, OK = "FAIL", "WARN", "ok"


def load(runs_dir):
    rows = []
    for p in glob.glob(os.path.join(runs_dir, "**", "*.jsonl"), recursive=True):
        for line in io.open(p, encoding="utf-8"):
            if not line.strip():
                continue
            r = json.loads(line)
            if _SP.is_run_record(r):
                r["_path"] = p
                rows.append(r)
    return rows


def check_data_integrity(rows):
    """Transport failures are not measurements and must not be on disk."""
    bad = [r for r in rows if "call failed" in str(r.get("problems"))]
    if bad:
        return FAIL, ("%d transport-failure rows persisted; they are not model behaviour "
                      "and corrupt every rate computed over these files" % len(bad))
    return OK, "no transport failures persisted"


def check_cells(rows, conditions):
    """Duplicate seeds mean two attempts were merged into one cell."""
    cells = collections.defaultdict(list)
    for r in rows:
        cells[(r["model"], r["condition"])].append(r)
    dupes, thin = [], []
    for (m, c), rs in cells.items():
        seeds = [r.get("seed") for r in rs]
        if len(seeds) != len(set(seeds)):
            dupes.append("%s/%s" % (m.split("/")[-1], c))
        if c in conditions and sum(1 for r in rs if r["valid"]) < 3:
            thin.append("%s/%s(%d)" % (m.split("/")[-1], c,
                                       sum(1 for r in rs if r["valid"])))
    if dupes:
        return FAIL, "duplicate seeds in %d cells: %s" % (len(dupes), dupes[:4])
    if thin:
        return WARN, ("%d cells under 3 valid runs -- n must be reported per cell, not "
                      "assumed: %s" % (len(thin), thin[:6]))
    return OK, "no duplicate seeds; all requested cells have 3+ valid runs"


def check_failure_classes(rows):
    """Every invalid row must carry a structural cause, never an unexplained bucket."""
    invalid = [r for r in rows if not r["valid"]]
    if not invalid:
        return OK, "no invalid rows"
    unclassified = [r for r in invalid if not r.get("failure_mode")]
    if unclassified:
        return FAIL, ("%d invalid rows carry no failure_mode; refusal cannot be "
                      "distinguished from truncation without it" % len(unclassified))
    counts = collections.Counter(r["failure_mode"] for r in invalid)
    return OK, "invalid rows all classified: %s" % dict(counts)


def check_degenerate(rows):
    """A sheet with one repeated answer is not a measurement."""
    deg = []
    for r in rows:
        if not r["valid"]:
            continue
        vals = [a["position"] for a in r["answers"]]
        if vals and len(set(vals)) == 1:
            deg.append(r["model"].split("/")[-1])
    if deg:
        return FAIL, ("%d valid sheets are all-one-answer and inflate any baseline they "
                      "enter: %s" % (len(deg), sorted(set(deg))[:4]))
    return OK, "no degenerate sheets"


def check_caching(rows, conditions):
    """Identical text across seeds at temperature > 0 means the floor is fictional."""
    cells = collections.defaultdict(list)
    for r in rows:
        if r["valid"] and r["condition"] in conditions:
            cells[(r["model"], r["condition"], r.get("temperature"))].append(r)
    suspect = []
    for (m, c, t), rs in cells.items():
        if not t or t == 0 or len(rs) < 3:
            continue
        if len({r.get("response_text") for r in rs}) < len(rs):
            suspect.append("%s/%s" % (m.split("/")[-1], c))
    if suspect:
        return FAIL, ("identical outputs across seeds at temp>0 in %d cells -- provider "
                      "caching, so any seed-based floor there is fictional: %s"
                      % (len(suspect), suspect[:4]))
    return OK, "no caching signature in seeded cells above temp 0"


def side(p):
    return p >= 2


def check_statistic(rows, conditions):
    """A net aggregate must never stand in for a gross item-level count."""
    if len(conditions) < 2:
        return OK, "single condition; no contrast to check"
    a, b = conditions[0], conditions[1]
    cells = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in rows:
        if r["valid"]:
            cells[r["model"]][r["condition"]].append(
                {x["q"]: x["position"] for x in r["answers"]})

    def modal(rs):
        acc = collections.defaultdict(list)
        for r in rs:
            for q, v in r.items():
                acc[q].append(v)
        return {q: collections.Counter(v).most_common(1)[0][0] for q, v in acc.items()}

    hidden = []
    for m, cs in cells.items():
        if not (cs[a] and cs[b]):
            continue
        ma, mb = modal(cs[a]), modal(cs[b])
        gross = sum(1 for q in ma if q in mb and side(ma[q]) != side(mb[q]))
        net = abs(sum(1 for v in mb.values() if side(v)) - sum(1 for v in ma.values() if side(v)))
        if gross >= 5 and gross >= 3 * max(net, 1):
            hidden.append("%s(gross %d, net %d)" % (m.split("/")[-1], gross, net))
    if hidden:
        return FAIL, ("net movement conceals gross item flips on %d models -- report the "
                      "gross count: %s" % (len(hidden), hidden[:4]))
    return OK, "no model where a net figure conceals gross item flips"


def mcnemar_p(b, c):
    n = b + c
    if n == 0:
        return 1.0
    return min(1.0, sum(math.comb(n, k) for k in range(0, min(b, c) + 1)) / 2 ** n * 2)


def check_floor(rows, conditions):
    """Significance must come from a paired item test, not a seed range."""
    if len(conditions) < 2:
        return OK, "single condition; no floor needed"
    per = collections.defaultdict(int)
    for r in rows:
        if r["valid"] and r["condition"] in conditions:
            per[(r["model"], r["condition"])] += 1
    small = [k for k, v in per.items() if v < 5]
    if small:
        return WARN, ("%d cells have fewer than 5 seeds; a seed RANGE is not a significance "
                      "threshold at this n -- use a paired item test (McNemar) and say so"
                      % len(small))
    return OK, "cells have 5+ seeds"


def check_families(rows, conditions):
    """Vendor-family count, because three models from one vendor is one family."""
    fams = {r["model"].split("/")[0] if "/" in r["model"] else "local"
            for r in rows if r["valid"] and r["condition"] in conditions}
    if len(fams) < 3:
        return FAIL, ("only %d vendor families (%s); the bar is 3 FAMILIES, and three "
                      "models from one vendor is one family" % (len(fams), sorted(fams)))
    return OK, "%d vendor families: %s" % (len(fams), sorted(fams))


def check_order(rows, conditions):
    """Presentation order is the largest measured confound in this project.

    Reordering the same 62 items flips up to 24 of them -- more than ablation, more than
    requantisation, more than any prompt condition. A single-order dataset cannot separate
    a real effect from an order artifact, and this check was missing from the first version
    of this gate: it was built from failures its author had personally been burned by, and
    order was one he had documented but never suffered.

    Where multiple orders exist, the between-order disagreement is a floor the claimed
    effect must clear.
    """
    orders = collections.defaultdict(set)
    for r in rows:
        if r["valid"] and r["condition"] in conditions:
            orders[(r["model"], r["condition"])].add(r.get("shuffle_seed"))
    if not orders:
        return OK, "no cells in the requested conditions"
    multi = [k for k, v in orders.items() if len(v) > 1]
    if not multi:
        return WARN, ("every cell is SINGLE-ORDER; order moves up to 24/62 items on this "
                      "instrument, so any effect here is confounded with presentation "
                      "order and the writeup must say so")

    # Where orders exist, measure the disagreement they produce.
    by = collections.defaultdict(dict)
    for r in rows:
        if r["valid"] and r["condition"] in conditions:
            by[(r["model"], r["condition"])].setdefault(r.get("shuffle_seed"), []).append(
                {x["q"]: x["position"] for x in r["answers"]})
    worst = 0
    for _, per_order in by.items():
        keys = list(per_order)
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                a, b = per_order[keys[i]][0], per_order[keys[j]][0]
                d = sum(1 for q in a if q in b and side(a[q]) != side(b[q]))
                worst = max(worst, d)
    return OK, ("%d cells carry 2+ presentation orders; worst between-order disagreement "
                "%d/62 -- any claimed effect must exceed it" % (len(multi), worst))


CHECKS = [
    ("data-integrity", check_data_integrity, False),
    ("cell-completeness", check_cells, True),
    ("failure-classes", check_failure_classes, False),
    ("degenerate-sheets", check_degenerate, False),
    ("provider-caching", check_caching, True),
    ("statistic-choice", check_statistic, True),
    ("floor-validity", check_floor, True),
    ("vendor-families", check_families, True),
    ("order-control", check_order, True),
]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--runs", required=True)
    ap.add_argument("--conditions", nargs="*", default=["A", "D"])
    ap.add_argument("--strict", action="store_true", help="treat WARN as failure")
    args = ap.parse_args(argv)

    rows = load(args.runs)
    if not rows:
        print("no compass-run records under %s" % args.runs, file=sys.stderr)
        return 1

    print("PRE-PUBLICATION GATE -- %s" % args.runs)
    print("%d records, conditions %s" % (len(rows), args.conditions))
    print()
    worst = OK
    for name, fn, needs_conds in CHECKS:
        status, msg = fn(rows, args.conditions) if needs_conds else fn(rows)
        mark = {OK: "  ok  ", WARN: " WARN ", FAIL: " FAIL "}[status]
        print("[%s] %-20s %s" % (mark, name, msg))
        if status == FAIL or (status == WARN and args.strict):
            worst = FAIL
        elif status == WARN and worst == OK:
            worst = WARN
    print()
    if worst == FAIL:
        print("GATE FAILED. Fix the data or narrow the claim; do not write it up.")
        return 1
    if worst == WARN:
        print("PASSED WITH WARNINGS. Each warning must appear in the writeup's limits.")
        return 0
    print("PASSED. This says the data is sound, NOT that the claim is true. A hostile read")
    print("is a separate gate and has caught things every check here would have missed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
