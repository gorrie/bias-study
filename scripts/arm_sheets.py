#!/usr/bin/env python3
"""Shared readers and tests for the 2026-09-25 battery arms (placebo wording, serving path).

Nothing statistical is reimplemented here that already exists. Position per sheet is
`position_analysis.sheet_positions`, the sheet bootstrap is `position_analysis.contrast_sheets`,
modal sheets and side/endpoint counts are `floor_table.modal` / `floor_table.both_stats`, the
refusal label is `refusal_table.classify`, BH is `rung2_contrast.bh_survivors`, and the partial-
sheet rule follows `item_omission.load_sheets` (whose NOT_AN_ATTEMPT set it imports). What this
file adds is the grouping both arms need -- a CELL is (model, backend pin, condition) -- plus
two exact tests the tree did not have in two-sided form: Fisher's exact test and a Monte-Carlo
permutation p for a sheet-level position contrast.

    python scripts/arm_sheets.py --selftest

Reads only. No API calls.
"""
from __future__ import annotations

import collections
import glob
import io
import itertools
import json
import math
import os
import random
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import studypaths as _SP            # noqa: E402
import position_analysis as PA      # noqa: E402
import floor_table as FT            # noqa: E402
import refusal_table as RT          # noqa: E402
from item_omission import NOT_AN_ATTEMPT   # noqa: E402

N_ITEMS = 32


def read_records(run_dir):
    """Every battery record in a run directory, sorted by file then line."""
    out = []
    for path in sorted(glob.glob(os.path.join(run_dir, "*.jsonl"))):
        for line in io.open(path, encoding="utf-8", errors="replace"):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if _SP.is_run_record(rec):
                out.append(rec)
    return out


def off_pin(rec):
    """Served by a backend other than the one pinned. Excluded wherever it appears."""
    pin = rec.get("provider_pinned")
    served = rec.get("provider")
    return bool(pin and served and served != pin)


def cells(records, key):
    """Group records into {key(rec): {"labels": Counter, "sheets": [...], "partial": n,
    "attempts": n, "off_pin": n, "degenerate": n}}.

    A SHEET is a valid, non-degenerate, on-pin record: {"order": shuffle_seed,
    "answers": {item_id: position}}.
    """
    out = collections.defaultdict(lambda: {"labels": collections.Counter(), "sheets": [],
                                           "partial": 0, "attempts": 0, "off_pin": 0,
                                           "degenerate": 0})
    for rec in records:
        c = out[key(rec)]
        if off_pin(rec):
            c["off_pin"] += 1
            continue
        c["labels"][RT.classify(rec)] += 1
        answers = [a for a in (rec.get("answers") or []) if isinstance(a, dict) and "q" in a]
        mode = rec.get("failure_mode")
        # THE PARTIAL-SHEET RULE OF item_omission.load_sheets: an attempt is a sheet that
        # reached the model and was not declined whole; it is partial when it answers some but
        # not all items.
        if mode not in NOT_AN_ATTEMPT and answers and rec.get("n_items") == N_ITEMS:
            c["attempts"] += 1
            if len({a["q"] for a in answers}) < N_ITEMS:
                c["partial"] += 1
        if not rec.get("valid"):
            continue
        amap = {int(a["q"]): a.get("position") for a in answers}
        if len(set(amap.values())) == 1:
            c["degenerate"] += 1
            continue
        c["sheets"].append({"order": rec.get("shuffle_seed"), "answers": amap})
    return out


def refusal(cell):
    """(refused, refused + valid) -- the study's refusal denominator."""
    lab = cell["labels"]
    return lab["refused"], lab["refused"] + lab["valid"]


def pair_sheets(sheets, index=None):
    """[{pair_id: position}] for a list of sheets, via position_analysis.sheet_positions."""
    index = index or PA.pair_index(PA.load_bank())
    recs = [{"model": "x", "condition": "c", "answers": s["answers"]} for s in sheets]
    return PA.sheet_positions(recs, index).get(("x", "c"), [])


def delta(sa, sb):
    """mean over shared pairs of (pair-mean under a) - (pair-mean under b); contrast_sheets'."""
    pa, pb = PA._mean_positions(sa), PA._mean_positions(sb)
    shared = sorted(set(pa) & set(pb))
    if not shared:
        return None
    return st.mean(pa[p] - pb[p] for p in shared)


def contrast(sa, sb, seed=20260925, draws=None, perm_draws=20000):
    """a minus b over pair-position sheets: the sheet bootstrap and a permutation p.

    The bootstrap is `position_analysis.contrast_sheets` itself. The permutation p relabels
    the pooled sheets at random `perm_draws` times (Monte-Carlo, not enumerated -- 15 v 15 has
    1.55e8 splits) and counts relabellings at least as extreme; the +1 in numerator and
    denominator keeps it from ever reading 0.
    """
    if not sa or not sb:
        return None
    per = {("m", "a"): sa, ("m", "b"): sb}
    r = PA.contrast_sheets(per, "m", "a", "b", seed=seed, n=draws)
    if r is None:
        return None
    obs = delta(sa, sb)
    pool = list(sa) + list(sb)
    rng = random.Random(seed + 1)
    hits = 0
    for _ in range(perm_draws):
        rng.shuffle(pool)
        d = delta(pool[:len(sa)], pool[len(sa):])
        if d is not None and abs(d) >= abs(obs) - 1e-12:
            hits += 1
    r["perm_p"] = (hits + 1.0) / (perm_draws + 1.0)
    r["n_a"], r["n_b"] = len(sa), len(sb)
    return r


def modal_by_order(sheets):
    """{order: modal answer sheet} via floor_table.modal."""
    by = collections.defaultdict(list)
    for s in sheets:
        by[s["order"]].append(s["answers"])
    return {o: FT.modal(v) for o, v in by.items() if v}


def order_floor(sheets, index=None):
    """The model's own between-order spread in one cell: max side-flips, max endpoint
    changes, and max |position contrast| over every pair of orders."""
    mods = modal_by_order(sheets)
    orders = sorted(mods)
    sides, ends, pos = [], [], []
    by = collections.defaultdict(list)
    for s in sheets:
        by[s["order"]].append(s)
    for a, b in itertools.combinations(orders, 2):
        sf, ep = FT.both_stats(mods[a], mods[b])
        sides.append(sf)
        ends.append(ep)
        d = delta(pair_sheets(by[a], index), pair_sheets(by[b], index))
        if d is not None:
            pos.append(abs(d))
    return {"pairs": len(sides), "side_max": max(sides) if sides else None,
            "end_max": max(ends) if ends else None,
            "pos_max": round(max(pos), 4) if pos else None,
            "sides": sides, "ends": ends}


def fisher_two_sided(a, b, c, d):
    """Two-sided Fisher exact p for [[a, b], [c, d]]: the summed probability of every table
    with the same margins no more probable than the observed one. Exact, integer arithmetic."""
    row1, row2, col1 = a + b, c + d, a + c
    total = row1 + row2
    if total == 0 or row1 == 0 or row2 == 0 or col1 == 0 or col1 == total:
        return 1.0
    den = math.comb(total, col1)

    def prob(k):
        return math.comb(row1, k) * math.comb(row2, col1 - k)

    obs = prob(a)
    lo, hi = max(0, col1 - row2), min(row1, col1)
    num = sum(prob(k) for k in range(lo, hi + 1) if prob(k) <= obs * (1 + 1e-9))
    return min(1.0, num / den)


def bh(pvals, q=0.05):
    import rung2_contrast as R2
    return R2.bh_survivors(pvals, q)[0]


def selftest():
    fails = []

    def check(label, cond):
        print("  [%s] %s" % ("ok" if cond else "FAIL", label))
        if not cond:
            fails.append(label)

    # Fisher against textbook values.
    check("fisher: tea-tasting 3/1 v 1/3 two-sided = 0.4857",
          abs(fisher_two_sided(3, 1, 1, 3) - 0.485714) < 1e-4)
    check("fisher: 10/0 v 0/10 = 1.08e-5", abs(fisher_two_sided(10, 0, 0, 10) - 1.0825e-5) < 1e-7)
    check("fisher: equal tables = 1", fisher_two_sided(5, 5, 5, 5) == 1.0)
    check("fisher: 10/9 v 0/15 < 0.001", fisher_two_sided(10, 9, 0, 15) < 0.001)

    # A synthetic serving contrast with a known answer, through the real estimators.
    bank = PA.load_bank()
    index = PA.pair_index(bank)
    rng = random.Random(7)

    def sheet(shift, order):
        ans = {}
        for it in bank["items"]:
            base = 2 if it["frame"] == "critic" else 1
            v = base + (shift if it["frame"] == "critic" else -shift)
            if rng.random() < 0.15:
                v += rng.choice((-1, 1))
            ans[it["id"]] = max(0, min(3, v))
        return {"order": order, "answers": ans}

    same_a = [sheet(0, o) for o in (11, 22, 33) for _ in range(5)]
    same_b = [sheet(0, o) for o in (11, 22, 33) for _ in range(5)]
    moved = [sheet(1, o) for o in (11, 22, 33) for _ in range(5)]
    null = contrast(pair_sheets(same_a, index), pair_sheets(same_b, index), draws=2000,
                    perm_draws=2000)
    real = contrast(pair_sheets(moved, index), pair_sheets(same_a, index), draws=2000,
                    perm_draws=2000)
    check("contrast: no shift reads near zero", abs(null["effect"]) < 0.1)
    check("contrast: a +1 shift on both halves reads about +1", 0.8 < real["effect"] < 1.1)
    check("contrast: the shift is significant by both tests",
          real["p"] < 0.01 and real["perm_p"] < 0.01)
    fl = order_floor(same_a, index)
    check("order floor: three order pairs", fl["pairs"] == 3)
    check("order floor: modal sheets of one distribution flip few sides",
          fl["side_max"] is not None and fl["side_max"] <= 8)
    recs = [{"schema": "battery-run/1", "valid": True, "failure_mode": None, "n_items": 32,
             "answers": [{"q": i, "position": 2} for i in range(1, 33)], "shuffle_seed": 11,
             "provider_pinned": "X", "provider": "X", "response_text": "x", "n_answers": 32,
             "problems": []},
            {"schema": "battery-run/1", "valid": False, "failure_mode": "other", "n_items": 32,
             "answers": [{"q": i, "position": 1} for i in range(1, 31)], "shuffle_seed": 11,
             "provider_pinned": "X", "provider": "X", "response_text": "x", "n_answers": 30,
             "problems": ["missing"]},
            {"schema": "battery-run/1", "valid": True, "failure_mode": None, "n_items": 32,
             "answers": [{"q": i, "position": 1} for i in range(1, 33)], "shuffle_seed": 11,
             "provider_pinned": "X", "provider": "Y", "response_text": "x", "n_answers": 32,
             "problems": []}]
    c = cells(recs, key=lambda r: "k")["k"]
    check("cells: an all-identical sheet is degenerate, not a sheet", c["degenerate"] == 1
          and not c["sheets"])
    check("cells: a 30-of-32 sheet is a partial attempt", c["partial"] == 1
          and c["attempts"] == 2)
    check("cells: an off-pin sheet is excluded before anything else", c["off_pin"] == 1)
    check("bh: one tiny p survives among large ones", bh([0.001, 0.5, 0.9]) == {0})
    print("")
    print("  %d check(s) failed" % len(fails))
    return 1 if fails else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    print(__doc__)
    sys.exit(0)
