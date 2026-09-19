#!/usr/bin/env python3
"""Do models skip particular PROPOSITIONS, or particular PLACES ON THE PAGE?

WHY THIS EXISTS
---------------
`data/collection-limitations.json` and `PLAN.md` declared, in prose, that three local builds
silently omit specific items: `mistral:latest` drops 20, 21 and 31 together; `qwen2.5:14b`
drops item 4; `gemma-4-12B` drops item 2. That was going to lead the paper, on the claim that
published position scores are computed over unknown non-random subsets of the instrument.

**A read-only scan of the wave overturned it.** Every declared pattern occurs at exactly one
presentation order, at fixed slots:

    mistral:latest   items 20 and 31 are SLOTS 0 AND 1 of order 11, item 21 is SLOT 31.
                     The model starts at the line numbered "1." and stops before the last.
                     12 of 23 sheets partial at order 11; 0 of 24 at orders 22 and 33.
    qwen2.5:14b      all 9 drops at order 11, SLOT 4.
    gemma-4-12B      all 6 drops at order 33, SLOT 2 -- the line "2." right after "22.".

Hosted models: zero partial sheets in roughly a thousand. So the honest reading is a list
NUMBERING artifact in 2024-generation 7-14B local builds, not content-specific item dropping,
and the wave cannot tell the two apart because the depth-5 pass repeated order 11 -- 808 of
1,411 records sit at one order.

THE TRAP THIS TOOL EXISTS TO CLOSE
----------------------------------
**Concentration is not evidence of an item effect.** A permutation test on per-item drop counts
returns p < 1e-4 for all four affected models, and it would return exactly that for a pure slot
effect too, because an item sitting at a dropped slot is dropped every time that order is run.
The panel-wide per-item table is worse than useless: it currently ranks SLOTS OF ORDER 11
dressed up as items -- 20, 21 and 31 at 15 drops each.

So this script reports concentration and then **refuses to interpret it**. What decides the
question is whether an item's drop rate survives being moved to a different slot, which needs
the same item observed at several slots across several orders. When a pattern lives at one
order the script prints NOT SEPARABLE and says so in those words, because the alternative --
reporting a p-value that cannot distinguish the hypotheses -- is the failure this study
convicts other papers of.

    python scripts/item_omission.py                          # the wave
    python scripts/item_omission.py --run <dir> --matrix      # full drop matrix
    python scripts/item_omission.py --selftest

Exit 0 computed, 1 a declared shape the data contradicts (with --declared), 2 NOT APPLICABLE.
"""
from __future__ import annotations

import argparse
import collections
import glob
import io
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import studypaths
import run_battery

#: A cell needs this many sheets before its drop rate is quoted at all. One sheet at a slot
#: is an anecdote, and the declared shapes above were built out of anecdotes.
MIN_SHEETS = 3

#: Sheets that carry no item-level information. A whole-sheet decline is a REFUSAL and belongs
#: in the refusal table; a `transport` loss never reached the model. Folding either into a
#: per-item omission rate is how `hedge_escape_scan` pooled 1,664 whole-sheet refusals into a
#: column labelled `silent`. The strings are the collector's own (`run_battery`), and
#: `load_sheets` reports it loudly if one ever carries a partial answer set.
NOT_AN_ATTEMPT = ("transport", "refused", "budget-exhausted")

#: The pre-registration for the local separation pass fixes this at 8. Reporting uses 2 --
#: the minimum at which the question is even askable -- and prints both.
PREREG_MIN_ORDERS = 8


def load_bank(path):
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)["items"]


def slot_map(items, shuffle_seed):
    """{item_id: slot} for one presentation order, from the collector's own function."""
    ordered = run_battery.order_items(items, shuffle_seed)
    return {it["id"]: slot for slot, it in enumerate(ordered)}


def load_sheets(run_dir, expected_ids):
    """Every ATTEMPTED sheet, partial or complete.

    A sheet that never reached the model (transport) or that the model declined as a whole
    (refusal) has no item-level information in it and is counted separately. Folding either
    into a per-item omission rate is how `hedge_escape_scan` ended up pooling gemini's 1,664
    whole-sheet refusals into a column labelled `silent`.
    """
    sheets, skipped = [], collections.Counter()
    for path in sorted(glob.glob(os.path.join(run_dir, "*.jsonl"))):
        with io.open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if not studypaths.is_run_record(rec):
                    continue
                answers = rec.get("answers") or []
                mode = rec.get("failure_mode")
                # THE VALUE IS `refused`, NOT `refusal`. This read ("transport", "refusal") on
                # first writing and silently matched nothing -- the 120 declined sheets were
                # excluded anyway, by the empty-answers branch below, so the result did not
                # move. It would have moved the day a model declined halfway down a sheet.
                # A filter that happens to be right for a reason other than the one it states
                # is a filter waiting to be wrong.
                if mode in NOT_AN_ATTEMPT:
                    skipped[mode] += 1
                    # A declined or dropped sheet should carry NO answers. If one carries
                    # some but not all, a model stopped partway through and the refusal
                    # table is hiding a partial sheet -- report it rather than discard it.
                    if 0 < len(answers) < len(expected_ids):
                        skipped["PARTIAL SHEET INSIDE %s -- investigate" % mode] += 1
                    continue
                if not answers:
                    skipped["no answers parsed"] += 1
                    continue
                if rec.get("n_items") != len(expected_ids):
                    skipped["different instrument size"] += 1
                    continue
                seen = {a["q"] for a in answers if isinstance(a, dict) and "q" in a}
                # THE ARM. `renumbered` sheets print the items 1..32 in presentation order,
                # so the printed label is `slot + 1` and no longer equals the item id. The
                # collector has already mapped answers back to item ids, so `dropped` is in
                # item ids either way -- but the two arms must never be pooled, because the
                # whole point of the second one is that the numeral moved.
                renumbered = bool(rec.get("renumbered"))
                label_to_id = rec.get("label_to_id") or {}
                sheets.append({
                    "model": rec.get("model"),
                    "condition": rec.get("condition"),
                    "seed": rec.get("shuffle_seed"),
                    "arm": "renum" if renumbered else "asis",
                    "id_of_label": {int(k): v for k, v in label_to_id.items()},
                    "dropped": sorted(expected_ids - seen),
                })
    return sheets, skipped


def numeral_test(sheets, slots_by_seed):
    """Does the drop follow the PRINTED NUMERAL rather than the item or the slot?

    In the as-is arm the printed label IS the item id. In the renumbered arm it is
    `slot + 1`. So for each sheet the dropped item can be expressed as the numeral that was
    printed beside it, and the three hypotheses make different predictions:

        H1  item      the same ITEM ids are dropped in both arms
        H0a slot      the same SLOTS are dropped in both arms
        H0b numeral   the same LABELS are dropped in both arms

    Returns {model: {arm: (Counter(items), Counter(slots), Counter(labels), n_sheets)}}.
    """
    out = collections.defaultdict(dict)
    by_key = collections.defaultdict(list)
    for sh in sheets:
        by_key[(sh["model"], sh["arm"])].append(sh)
    for (model, arm), group in by_key.items():
        items_c, slots_c, labels_c = (collections.Counter() for _ in range(3))
        for sh in group:
            smap = slots_by_seed.get(sh["seed"]) or {}
            for item in sh["dropped"]:
                items_c[item] += 1
                slot = smap.get(item)
                if slot is None:
                    continue
                slots_c[slot] += 1
                # The numeral actually printed beside that item on that sheet.
                labels_c[(slot + 1) if arm == "renum" else item] += 1
        out[model][arm] = (items_c, slots_c, labels_c, len(group))
    return out


def concentration_p(sheets, n_items, draws, rng):
    """p for the observed max per-item drop count, against drops placed uniformly at random.

    Keeps each sheet's NUMBER of drops and moves only which positions they land on. This
    tests 'drops are not spread evenly' and NOTHING ELSE -- a pure slot effect produces a
    tiny p here, which is exactly why the separation test below carries the verdict.
    """
    counts = collections.Counter()
    for sh in sheets:
        for item in sh["dropped"]:
            counts[item] += 1
    if not counts:
        return None, None, 0
    observed = max(counts.values())
    sizes = [len(sh["dropped"]) for sh in sheets if sh["dropped"]]
    positions = list(range(n_items))
    at_least = 0
    for _ in range(draws):
        null = collections.Counter()
        for k in sizes:
            for pos in rng.sample(positions, k):
                null[pos] += 1
        if null and max(null.values()) >= observed:
            at_least += 1
    return observed, (at_least + 1.0) / (draws + 1.0), len(counts)


def separation(sheets, slots_by_seed):
    """Can an item effect be told apart from a slot effect for this model?

    Returns (verdict, item_evidence, slot_evidence, orders).

    item_evidence: items dropped at >= MIN_SHEETS sheets at EACH of >= 2 DISTINCT SLOTS.
                   An item that keeps being skipped after it moves is about the item.
    slot_evidence: slots where >= 2 DISTINCT ITEMS were each dropped >= MIN_SHEETS times.
                   A place on the page that eats whatever is put in it is about the page.
    """
    orders = sorted({sh["seed"] for sh in sheets})
    # (item, slot) -> [drops, sheets presented in that combination]
    cell = collections.defaultdict(lambda: [0, 0])
    for sh in sheets:
        smap = slots_by_seed.get(sh["seed"])
        if smap is None:
            continue
        dropped = set(sh["dropped"])
        for item, slot in smap.items():
            cell[(item, slot)][1] += 1
            if item in dropped:
                cell[(item, slot)][0] += 1

    by_item = collections.defaultdict(list)
    by_slot = collections.defaultdict(list)
    for (item, slot), (drops, total) in cell.items():
        if drops and total >= MIN_SHEETS:
            by_item[item].append((slot, drops, total))
            by_slot[slot].append((item, drops, total))

    item_evidence = {i: v for i, v in by_item.items() if len({s for s, _, _ in v}) >= 2}
    slot_evidence = {s: v for s, v in by_slot.items() if len({i for i, _, _ in v}) >= 2}

    if len(orders) < 2:
        verdict = "NOT SEPARABLE"
    elif item_evidence and slot_evidence:
        verdict = "MIXED"
    elif item_evidence:
        verdict = "ITEM-SPECIFIC"
    elif slot_evidence:
        verdict = "SLOT/NUMBERING"
    else:
        verdict = "NOT SEPARABLE"
    return verdict, item_evidence, slot_evidence, orders


def analyse(sheets, items, draws, rng):
    n_items = len(items)
    seeds = sorted({sh["seed"] for sh in sheets if sh["seed"] is not None})
    slots_by_seed = {s: slot_map(items, s) for s in seeds}

    out = []
    by_model = collections.defaultdict(list)
    for sh in sheets:
        by_model[sh["model"]].append(sh)

    for model, msheets in sorted(by_model.items()):
        partial = [sh for sh in msheets if sh["dropped"]]
        if not partial:
            continue
        top, p, n_hit = concentration_p(msheets, n_items, draws, rng)
        verdict, item_ev, slot_ev, orders = separation(msheets, slots_by_seed)
        counts = collections.Counter()
        for sh in partial:
            for item in sh["dropped"]:
                counts[item] += 1
        out.append({
            "model": model,
            "sheets": len(msheets),
            "partial": len(partial),
            "orders": orders,
            "top_count": top,
            "conc_p": p,
            "items_hit": n_hit,
            "verdict": verdict,
            "item_evidence": item_ev,
            "slot_evidence": slot_ev,
            "counts": counts,
            "slots_by_seed": slots_by_seed,
        })
    return out, slots_by_seed


def print_report(rows, slots_by_seed, show_matrix):
    print("")
    print("  PER-MODEL OMISSION, and whether item can be told apart from slot")
    print("")
    print("  %-34s %6s %7s %8s %-16s %s"
          % ("model", "sheets", "partial", "orders", "concentration", "verdict"))
    print("  " + "-" * 96)
    for r in rows:
        conc = "p = %.5f" % r["conc_p"] if r["conc_p"] is not None else "-"
        print("  %-34s %6d %7d %8s %-16s %s"
              % (r["model"][:34], r["sheets"], r["partial"],
                 ",".join(str(o) for o in r["orders"]), conc, r["verdict"]))

    print("")
    print("  Concentration answers ONLY 'are the drops spread evenly'. A pure slot effect")
    print("  returns a tiny p here as well, so it decides nothing. The verdict column is what")
    print("  separates the hypotheses, and it needs the same item seen at several slots.")

    for r in rows:
        print("")
        print("  %s -- %d partial of %d sheets, orders %s"
              % (r["model"], r["partial"], r["sheets"],
                 ",".join(str(o) for o in r["orders"])))
        for item, n in r["counts"].most_common(6):
            places = []
            for seed in r["orders"]:
                smap = slots_by_seed.get(seed) or {}
                if item in smap:
                    places.append("order %s slot %d" % (seed, smap[item]))
            print("      item %-3d dropped %2d x   %s" % (item, n, "; ".join(places)))
        if r["verdict"] == "NOT SEPARABLE":
            if len(r["orders"]) < 2:
                print("      NOT SEPARABLE: one presentation order. Item identity and page")
                print("      position are the same variable in this data. No test can be run.")
            else:
                print("      NOT SEPARABLE: no item reached %d sheets at two different slots,"
                      % MIN_SHEETS)
                print("      and no slot ate two different items. Nothing to compare.")
        for item, places in sorted(r["item_evidence"].items()):
            detail = ", ".join("slot %d %d/%d" % (s, d, t) for s, d, t in sorted(places))
            print("      ITEM EVIDENCE  item %d dropped at %d distinct slots: %s"
                  % (item, len({s for s, _, _ in places}), detail))
        for slot, places in sorted(r["slot_evidence"].items()):
            detail = ", ".join("item %d %d/%d" % (i, d, t) for i, d, t in sorted(places))
            print("      SLOT EVIDENCE  slot %d ate %d distinct items: %s"
                  % (slot, len({i for i, _, _ in places}), detail))

    if show_matrix:
        print("")
        print("  FULL MATRIX  model / item / order / slot / drops / sheets")
        for r in rows:
            for item, n in sorted(r["counts"].items()):
                for seed in r["orders"]:
                    smap = slots_by_seed.get(seed) or {}
                    if item in smap:
                        print("    %-30s %3d %5s %5d %6d"
                              % (r["model"][:30], item, seed, smap[item], n))


def _synthetic(kind):
    """Sheets with a KNOWN cause, to prove the verdict is not just reading concentration."""
    items = [{"id": i, "mirror_of": (i + 1 if i % 2 else i - 1)} for i in range(1, 33)]
    seeds = [11, 22, 33]
    maps = {s: slot_map(items, s) for s in seeds}
    sheets = []
    for seed in seeds:
        inv = {slot: item for item, slot in maps[seed].items()}
        for _ in range(6):
            if kind == "slot":
                dropped = [inv[0], inv[1]]          # always the first two LINES
            elif kind == "item":
                dropped = [7, 9]                    # always the same PROPOSITIONS
            else:
                dropped = []
            sheets.append({"model": "synthetic", "condition": "N", "seed": seed,
                           "dropped": sorted(dropped)})
    return items, sheets


def selftest():
    rng = random.Random(20260918)
    failures = []

    items, sheets = _synthetic("slot")
    rows, _ = analyse(sheets, items, 400, rng)
    got = rows[0]["verdict"] if rows else "none"
    if got != "SLOT/NUMBERING":
        failures.append("pure slot effect read as %s, not SLOT/NUMBERING" % got)

    items, sheets = _synthetic("item")
    rows, _ = analyse(sheets, items, 400, rng)
    got = rows[0]["verdict"] if rows else "none"
    if got != "ITEM-SPECIFIC":
        failures.append("pure item effect read as %s, not ITEM-SPECIFIC" % got)

    # The one that matters: the same item effect seen at ONE order must not be claimed.
    items, sheets = _synthetic("item")
    one = [sh for sh in sheets if sh["seed"] == 11]
    rows, _ = analyse(one, items, 400, rng)
    got = rows[0]["verdict"] if rows else "none"
    if got != "NOT SEPARABLE":
        failures.append("single-order data read as %s, not NOT SEPARABLE" % got)

    # And concentration must be small in BOTH cases, proving it cannot be the discriminator.
    items, slot_sheets = _synthetic("slot")
    _, p_slot, _ = concentration_p(slot_sheets, 32, 800, rng)
    items, item_sheets = _synthetic("item")
    _, p_item, _ = concentration_p(item_sheets, 32, 800, rng)
    if p_slot is None or p_item is None or p_slot > 0.05 or p_item > 0.05:
        failures.append("concentration p did not fire on both causes (slot %s, item %s)"
                        % (p_slot, p_item))

    for f in failures:
        print("  FAIL  %s" % f)
    if failures:
        return 1
    print("  selftest: 4 checks passed -- slot, item, single-order refusal, and the proof")
    print("  that concentration alone cannot tell the first two apart.")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", default="2026-09-16-ratchet-v3-wave")
    ap.add_argument("--items", default="data/ratchet-battery.json")
    ap.add_argument("--perm", type=int, default=20000)
    ap.add_argument("--matrix", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    # Same resolution `position_analysis` uses. NOT `studypaths.resolve_run`, which demands a
    # `scored/` subdirectory: the battery is whole-sheet forced choice with no judging step,
    # so its runs never have one and every battery analysis reads the raw sheets.
    run_dir = (a.run if os.path.isdir(a.run)
               else os.path.join(studypaths.STUDY_DIR, "runs", a.run))
    if not os.path.isdir(run_dir):
        print("no such run directory: %s" % run_dir)
        return 2
    items = load_bank(os.path.join(studypaths.STUDY_DIR, a.items))
    expected = {it["id"] for it in items}

    sheets, skipped = load_sheets(run_dir, expected)
    print("")
    print("  run        %s" % run_dir)
    print("  instrument %s, %d items" % (a.items, len(items)))
    print("  sheets     %d attempted" % len(sheets))
    for reason, n in sorted(skipped.items()):
        print("             %-28s %d not counted" % (reason, n))
    if not sheets:
        print("  NOT APPLICABLE: no attempted sheets.")
        return 2

    orders = sorted({sh["seed"] for sh in sheets if sh["seed"] is not None})
    by_order = collections.Counter(sh["seed"] for sh in sheets)
    print("  orders     %s" % ", ".join("%s (%d sheets)" % (o, by_order[o]) for o in orders))
    if len(orders) < PREREG_MIN_ORDERS:
        print("")
        print("  %d presentation orders. The pre-registration fixes %d as the number at which"
              % (len(orders), PREREG_MIN_ORDERS))
        print("  an item claim becomes testable. Below that, a single-order pattern is")
        print("  reported as NOT SEPARABLE rather than as a finding.")

    arms = collections.Counter(sh["arm"] for sh in sheets)
    if len(arms) > 1:
        print("  arms       %s" % ", ".join("%s (%d)" % kv for kv in sorted(arms.items())))
        seeds_all = sorted({sh["seed"] for sh in sheets if sh["seed"] is not None})
        slots_all = {s: slot_map(items, s) for s in seeds_all}
        print("")
        print("  THREE-WAY TEST -- does the drop follow the ITEM, the SLOT, or the NUMERAL?")
        print("")
        print("  In the as-is arm the printed number IS the item id. In the renumbered arm it")
        print("  is slot+1. Whichever column keeps its top value ACROSS BOTH ARMS is the one")
        print("  the behaviour tracks.")
        print("")
        nt = numeral_test(sheets, slots_all)
        print("  %-30s %-6s %6s  %-14s %-14s %s"
              % ("model", "arm", "sheets", "top ITEM", "top SLOT", "top NUMERAL"))
        for model in sorted(nt):
            for arm in ("asis", "renum"):
                if arm not in nt[model]:
                    continue
                items_c, slots_c, labels_c, n = nt[model][arm]

                def _top(counter):
                    if not counter:
                        return "-"
                    k, v = counter.most_common(1)[0]
                    return "%s (%dx)" % (k, v)

                print("  %-30s %-6s %6d  %-14s %-14s %s"
                      % (model.split("/")[-1][:30], arm, n,
                         _top(items_c), _top(slots_c), _top(labels_c)))
        print("")
        print("  A top value that is the SAME in both arms is the variable the drop follows.")
        print("  A model with no drops in the renumbered arm did not lose the item -- it lost")
        print("  the numeral, and renumbering removed whatever the numeral was doing.")
        print("")

    rng = random.Random(20260918)
    rows, slots_by_seed = analyse(sheets, items, a.perm, rng)
    if not rows:
        print("")
        print("  No partial sheets. NOT APPLICABLE.")
        return 2
    print_report(rows, slots_by_seed, a.matrix)

    sep = [r for r in rows if r["verdict"] == "ITEM-SPECIFIC"]
    print("")
    print("  %d of %d model(s) with omissions show item-specific evidence; %d are not"
          % (len(sep), len(rows),
             len([r for r in rows if r["verdict"] == "NOT SEPARABLE"])))
    print("  separable in this corpus.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
