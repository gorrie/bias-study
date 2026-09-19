#!/usr/bin/env python3
"""Can each answer be attributed to the proposition it belongs to? For 44 sheets, no.

THE PROBLEM
-----------
Sheets are presented in a shuffled order and each item keeps its own id as its printed number,
so a model that answers down the page writes its answers out of numerical sequence. Most do
exactly that. But **386 of the valid shuffled sheets came back numbered in ASCENDING ID
ORDER** -- which has two completely different explanations and the record cannot tell them
apart on its face:

  RE-SORTED   the model read the shuffled sheet, answered by item id, and printed its answers
              in id order. The answers mean what they say. This is the large majority.

  BY SLOT     the model ignored the printed numbers and answered down the page, numbering its
              output 1, 2, 3... So its "17" is the SEVENTEENTH LINE, not item 17, and reading
              it as item 17 scrambles the sheet.

THE DISCRIMINATOR
-----------------
The instrument is 16 mirrored pairs, and a model that holds any position at all answers the
two halves of a pair differently. So map each sheet BOTH ways and score pair-consistency:

  consistency under id-mapping  high, slot-mapping low   -> genuinely re-sorted, keep
  consistency under slot-mapping high, id-mapping low    -> answered by slot, REMAP or drop
  both near chance                                       -> UNATTRIBUTABLE

Measured 2026-09-18: 342 genuinely re-sorted (0.93-1.00 by id against ~0.45 by slot -- the
frontier models do this routinely), and **44 unattributable**, of which 31 are one model,
89% of its valid corpus. Those 44 sit inside a published order-floor row.

An unattributable sheet is not noise. It is unlabelled data being scored, and the honest
treatment is to exclude it from the rows that depend on item identity and say how many were
excluded -- which is what this gate makes possible.

    python scripts/check_sheet_attribution.py
    python scripts/check_sheet_attribution.py --run <dir> --list
    python scripts/check_sheet_attribution.py --selftest

Exit 0 every sheet attributable, 1 unattributable sheets present and not declared, 2 N/A.
"""
from __future__ import annotations

import argparse
import collections
import glob
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import studypaths as _SP
import run_battery as RB

#: A sheet counts as ASCENDING when its answers arrive in increasing printed-number order.
#: Only those are ambiguous: a sheet whose numbers follow the shuffled presentation order can
#: only have been read off the page as printed.
#:
#: The bar for calling an attribution CLEAR. Pair-consistency is the share of the 16 pairs
#: whose halves land on opposite sides of the midpoint. A model with any position clears 0.75
#: comfortably under the correct mapping; chance is near 0.50.
CLEAR = 0.75
CHANCE_BAND = (0.40, 0.62)


def pair_consistency(answers, index):
    """Share of pairs whose two halves land on opposite sides of the midpoint."""
    halves = collections.defaultdict(dict)
    for item_id, value in answers.items():
        if item_id not in index or value is None:
            continue
        pair_id, frame = index[item_id]
        halves[pair_id][frame] = float(value)
    ok = tot = 0
    for sides in halves.values():
        if len(sides) != 2:
            continue
        tot += 1
        a, b = sides.values()
        if (a - 1.5) * (b - 1.5) < 0:
            ok += 1
    return (ok / tot) if tot else None, tot


def classify(rec, items, index):
    """(verdict, id_consistency, slot_consistency) for one sheet."""
    raw = rec.get("answers") or []
    seq = [a.get("q") for a in raw if isinstance(a, dict) and a.get("q") is not None]
    if len(seq) < 8:
        return "too short", None, None
    ascending = all(seq[i] < seq[i + 1] for i in range(len(seq) - 1))
    if not ascending:
        return "presented order", None, None

    # Reading 1: the printed number IS the item id.
    by_id = {int(a["q"]): a.get("position") for a in raw if a.get("q") is not None}
    # Reading 2: the printed number is the SLOT, so map it through the presentation order.
    ordered = RB.order_items(items, rec.get("shuffle_seed"))
    slot_to_id = {i + 1: it["id"] for i, it in enumerate(ordered)}
    by_slot = {slot_to_id[int(a["q"])]: a.get("position")
               for a in raw if int(a.get("q", 0)) in slot_to_id}

    c_id, _n = pair_consistency(by_id, index)
    c_slot, _n = pair_consistency(by_slot, index)
    if c_id is None or c_slot is None:
        return "not scoreable", c_id, c_slot
    if c_id >= CLEAR and c_id > c_slot:
        return "re-sorted by id", c_id, c_slot
    if c_slot >= CLEAR and c_slot > c_id:
        return "answered by slot", c_id, c_slot
    if CHANCE_BAND[0] <= c_id <= CHANCE_BAND[1] and CHANCE_BAND[0] <= c_slot <= CHANCE_BAND[1]:
        return "UNATTRIBUTABLE", c_id, c_slot
    return "unclear", c_id, c_slot


def selftest():
    """Both readings, constructed so the true answer is known."""
    items = RB.load_items()["items"]
    index = {it["id"]: (it.get("pair_no", it.get("pair_id")), it["frame"]) for it in items}
    seed = 11
    ordered = RB.order_items(items, seed)
    fails = []

    # A skeptic answering BY ID, printed in id order: id-mapping must win.
    ans = [{"q": it["id"], "position": 3 if it["frame"] == "critic" else 0}
           for it in sorted(items, key=lambda i: i["id"])]
    v, ci, cs = classify({"answers": ans, "shuffle_seed": seed}, items, index)
    if v != "re-sorted by id":
        fails.append("a sheet answered by id read as %r (id %.2f slot %.2f)" % (v, ci, cs))

    # The same skeptic answering BY SLOT, numbering its output 1..32: slot-mapping must win.
    ans = [{"q": i + 1, "position": 3 if it["frame"] == "critic" else 0}
           for i, it in enumerate(ordered)]
    v, ci, cs = classify({"answers": ans, "shuffle_seed": seed}, items, index)
    if v != "answered by slot":
        fails.append("a sheet answered by slot read as %r (id %.2f slot %.2f)" % (v, ci, cs))

    # A sheet with NO STRUCTURE must not be confidently attributed either way.
    #
    # The first attempt here used positions alternating 2,1,2,1 down the page, which is not
    # positionless at all: consecutive item ids are the two halves of a pair, so alternating
    # across the midpoint gives PERFECT pair-consistency under id-mapping and reads as a
    # textbook skeptic. The classifier was right and the synthetic was wrong -- which is the
    # argument for validating against input whose answer is known, and for checking that the
    # input really has the property it is named for.
    import random as _r
    rng = _r.Random(20260918)
    ans = [{"q": i + 1, "position": rng.randrange(4)} for i in range(32)]
    v, ci, cs = classify({"answers": ans, "shuffle_seed": seed}, items, index)
    if v in ("re-sorted by id", "answered by slot"):
        fails.append("an unstructured sheet was CONFIDENTLY attributed as %r "
                     "(id %.2f slot %.2f)" % (v, ci, cs))

    for f in fails:
        print("  FAIL  %s" % f)
    if fails:
        return 1
    print("  selftest: 3 checks passed -- a sheet answered by id, one answered by slot, and")
    print("  one carrying no position at all, each read correctly.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", default=None, help="one run dir; default is every wave")
    ap.add_argument("--list", action="store_true", help="name every unattributable sheet")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()

    items = RB.load_items()["items"]
    index = {it["id"]: (it.get("pair_no", it.get("pair_id")), it["frame"]) for it in items}
    roots = ([os.path.join(_SP.STUDY_DIR, "runs", a.run)] if a.run
             else sorted(glob.glob(os.path.join(_SP.STUDY_DIR, "runs", "*"))))

    verdicts = collections.Counter()
    by_model = collections.defaultdict(collections.Counter)
    examined = 0
    for root in roots:
        if not os.path.isdir(root):
            continue
        for path in sorted(glob.glob(os.path.join(root, "*.jsonl"))):
            for line in io.open(path, encoding="utf-8", errors="replace"):
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if not _SP.is_run_record(rec) or not rec.get("valid"):
                    continue
                if rec.get("shuffle_seed") is None:
                    continue
                examined += 1
                v, _ci, _cs = classify(rec, items, index)
                verdicts[v] += 1
                by_model[rec.get("model")][v] += 1

    # CHECKED NOTHING IS NOT A PASS.
    if not examined:
        print("CHECKED NOTHING -- no valid shuffled sheets found. NOT APPLICABLE.")
        return 2

    print("")
    print("  sheets examined            %d" % examined)
    for v, n in verdicts.most_common():
        print("    %-24s %5d" % (v, n))

    bad = verdicts["UNATTRIBUTABLE"]
    print("")
    if not bad:
        print("  Every scoreable sheet can be attributed to the propositions it answers.")
        return 0

    print("  %d SHEET(S) CANNOT BE ATTRIBUTED. Pair-consistency is near chance under BOTH"
          % bad)
    print("  the id mapping and the slot mapping, so which proposition each answer belongs to")
    print("  is not recoverable from the record. That is unlabelled data, not noisy data.")
    print("")
    worst = sorted(((c["UNATTRIBUTABLE"], m) for m, c in by_model.items()
                    if c["UNATTRIBUTABLE"]), reverse=True)
    for n, model in worst:
        tot = sum(by_model[model].values())
        print("    %-44s %3d of %3d (%.0f%%)" % (model[:44], n, tot, 100.0 * n / tot))
    if a.list:
        print("")
        print("  Re-run with --run <dir> to narrow. Sheet-level ids are in the records.")
    print("")
    print("  These must be excluded from any row that depends on item identity -- the order")
    print("  and same-version floors above all -- and the exclusion COUNTED where it is used.")
    print("  A model contributing mostly unattributable sheets is not a near-random responder;")
    print("  it is a model whose sheets were read under the wrong mapping.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
