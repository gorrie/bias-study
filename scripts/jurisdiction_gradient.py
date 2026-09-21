#!/usr/bin/env python3
"""Is the instruction's effect the same size on every subject, or does it pick its targets?

WHY THIS MATTERS MORE THAN IT LOOKS
-----------------------------------
§1 of the paper reports that the balance instruction and the item order move measured position
by about the same amount. A reader's natural next move is to treat the instruction effect as a
nuisance to subtract: measure it once, remove it, carry on.

**That works only if the effect is a constant offset.** This measures whether it is, and it is
not. Hedging under the instruction is roughly four times heavier on china-state items than on
British, European and Indian ones, with a flat-to-opposite control arm. An effect that is four
times larger on the items with the most political content cannot be subtracted, bounded, or
controlled away -- it distorts exactly the measurements the instrument exists to take.

WHAT IS AND IS NOT CLAIMED
--------------------------
The outcome is the share of (model x item) cells that LOSE a strong answer between two
conditions. That is a property of the instrument's reactivity, NOT a claim about where any
model sits and NOT a claim about vendor allegiance.

**The loyalty reading is refuted on this corpus** and must not be implied: Chinese-vendor
models are among the most critical of china-state items at baseline, and
`crossover_jurisdiction.py` finds no vendor x item interaction, bounded by `null_audit.py` at
about +/-0.50 scale points rather than at zero.

**Two items per jurisdiction tag.** This is the most quotable number in the study and its
thinnest. Exploratory, written after the data was seen, and reported as a signal that says
what to author next -- not as a result.

    python scripts/jurisdiction_gradient.py
    python scripts/jurisdiction_gradient.py --run <dir> --arm A --control P
    python scripts/jurisdiction_gradient.py --selftest

Exit 0 computed, 2 NOT APPLICABLE (the bank carries no jurisdiction tags).
"""
from __future__ import annotations

import argparse
import collections
import io
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import studypaths as _SP
import position_analysis as PA

STRONG = (0, 3)
BASELINE = "N"

#: The reference set the china-state tag is tested against. Fixed here rather than chosen per
#: run: a comparison group selected after seeing which tags are low is not a comparison.
REFERENCE_TAGS = ("british", "european", "indian")


#: THE FIELD IS `ratchet`. It is not called `jurisdiction`, and a first version of this file
#: read `jurisdiction`/`state`, found neither, and defaulted every item to "generic" -- which
#: would have produced a single-row table showing no gradient at all. It printed NOT APPLICABLE
#: instead only because the tag set then had one distinct value, which is luck rather than a
#: guard. The names are listed so a bank that renames the field fails loudly here.
TAG_FIELDS = ("ratchet", "jurisdiction", "state")


def bank_tags(path=None):
    path = path or os.path.join(_SP.STUDY_DIR, "data", "ratchet-battery.json")
    with io.open(path, encoding="utf-8") as fh:
        items = json.load(fh)["items"]
    present = [f for f in TAG_FIELDS if any(it.get(f) for it in items)]
    if not present:
        raise KeyError(
            "no jurisdiction tag on the bank: looked for %s and found none. A silent default "
            "to 'generic' would show no gradient and look like a result."
            % ", ".join(TAG_FIELDS))
    field = present[0]
    return {it["id"]: (it.get(field) or "generic") for it in items}


def modal_strong(records, tags):
    """(model, condition, item) -> True when the MODAL answer across sheets is an endpoint."""
    acc = collections.defaultdict(list)
    for rec in records:
        for item_id, value in (rec.get("answers") or {}).items():
            if value is None:
                continue
            acc[(rec.get("model"), rec.get("condition"), int(item_id))].append(value)
    out = {}
    for key, vals in acc.items():
        # The modal answer, ties broken to the LOWER option so the rule is stated rather than
        # left to dict ordering -- a tie broken by insertion order is a figure that depends on
        # which file was read first.
        counts = collections.Counter(vals)
        best = max(counts.values())
        modal = min(v for v, c in counts.items() if c == best)
        out[key] = modal in STRONG
    return out


def loss_by_tag(modal, tags, arm, baseline=BASELINE, over_all_cells=False):
    """tag -> (cells that lost a strong answer, denominator).

    TWO DEFENSIBLE DENOMINATORS, AND THEY DISAGREE. `FINDINGS-2026-09-17-battery.md` §3
    reports "share of (item x model) cells losing a strong answer" and records NO command, so
    which denominator produced it cannot be recovered from the file:

      conditional (default)  cells that HELD a strong answer at baseline. Asks: given the
                             model was emphatic here, how often did the instruction soften it?
      over all cells         every cell with both arms. Asks: what share of the whole sheet
                             went from emphatic to hedged?

    The second is mechanically smaller and is dominated by how often a tag draws a strong
    answer at all -- which differs four-fold across these tags. Both are printed, because a
    gradient that exists under one denominator and not the other is a fact about the
    definition and the reader is owed it.
    """
    per_tag = collections.defaultdict(lambda: [0, 0])
    per_model = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))
    for (model, cond, item), strong in modal.items():
        if cond != baseline:
            continue
        other = modal.get((model, arm, item))
        if other is None:
            continue
        if not over_all_cells and not strong:
            continue
        tag = tags.get(item, "generic")
        per_tag[tag][1] += 1
        per_model[model][tag][1] += 1
        if strong and not other:
            per_tag[tag][0] += 1
            per_model[model][tag][0] += 1
    return per_tag, per_model


def sign_test(pairs):
    up = sum(1 for a, b in pairs if a > b)
    down = sum(1 for a, b in pairs if a < b)
    ties = len(pairs) - up - down
    n = up + down
    if n == 0:
        return up, down, ties, None
    k = min(up, down)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / float(2 ** n)
    return up, down, ties, min(1.0, 2.0 * tail)


def paired(per_model, focus, reference):
    """Per model: focus-tag loss rate minus the mean of the reference tags' rates."""
    out = []
    for model, tags in per_model.items():
        f = tags.get(focus)
        if not f or not f[1]:
            continue
        refs = [tags[t][0] / tags[t][1] for t in reference if tags.get(t) and tags[t][1]]
        if not refs:
            continue
        out.append((f[0] / f[1], sum(refs) / len(refs)))
    return out


def selftest():
    fails = []
    up, down, ties, p = sign_test([(0.9, 0.1)] * 10)
    if not (up == 10 and p is not None and p < 0.01):
        fails.append("10 of 10 in one direction read as up=%d p=%s" % (up, p))
    up, down, ties, p = sign_test([(0.5, 0.5)] * 6 + [(0.9, 0.1)] * 2)
    if ties != 6:
        fails.append("ties miscounted: %d" % ties)
    # A tie in the modal must break to the LOWER option, deterministically.
    recs = [{"model": "m", "condition": "N", "answers": {1: 3}},
            {"model": "m", "condition": "N", "answers": {1: 0}}]
    got = modal_strong(recs, {1: "generic"})
    if got.get(("m", "N", 1)) is not True:
        fails.append("a 3/0 tie should break to 0, which is still an endpoint")
    for f in fails:
        print("  FAIL  %s" % f)
    if fails:
        return 1
    print("  selftest: 3 checks passed -- direction, ties, and a deterministic modal rule.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", default="2026-09-16-ratchet-v3-wave")
    ap.add_argument("--arm", default="A", help="the instruction under test")
    ap.add_argument("--control", default="P", help="the content-free control arm")
    ap.add_argument("--focus", default="china-state")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()

    run_dir = (a.run if os.path.isdir(a.run)
               else os.path.join(_SP.STUDY_DIR, "runs", a.run))
    if not os.path.isdir(run_dir):
        print("no such run directory: %s" % run_dir)
        return 2
    tags = bank_tags()
    distinct = sorted(set(tags.values()))
    if len(distinct) < 2:
        print("NOT APPLICABLE -- the bank carries no jurisdiction tags to compare.")
        return 2

    records = PA.load_records(run_dir)
    if not records:
        print("CHECKED NOTHING -- no valid sheets. NOT a result.")
        return 2
    modal = modal_strong(records, tags)

    print("")
    print("  SHARE OF CELLS LOSING A STRONG ANSWER, by the item's jurisdiction tag")
    print("  A cell is one model x one item. Modal answer across sheets; ties to the lower.")
    print("")
    print("  %-16s %6s %22s %22s" % ("tag", "items",
                                     "%s - %s (instruction)" % (a.arm, BASELINE),
                                     "%s - %s (control)" % (a.control, BASELINE)))
    inst_tag, inst_model = loss_by_tag(modal, tags, a.arm)
    ctrl_tag, ctrl_model = loss_by_tag(modal, tags, a.control)
    n_items = collections.Counter(tags.values())
    for tag in sorted(distinct, key=lambda t: -(inst_tag[t][0] / inst_tag[t][1]
                                                if inst_tag.get(t) and inst_tag[t][1] else 0)):
        i_lost, i_tot = inst_tag.get(tag, (0, 0))
        c_lost, c_tot = ctrl_tag.get(tag, (0, 0))
        print("  %-16s %6d %21s %22s"
              % (tag, n_items[tag],
                 ("%5.1f%%  (%d/%d)" % (100.0 * i_lost / i_tot, i_lost, i_tot)) if i_tot else "-",
                 ("%5.1f%%  (%d/%d)" % (100.0 * c_lost / c_tot, c_lost, c_tot)) if c_tot else "-"))

    # The same table over ALL cells, which is the other reading of §3's sentence.
    alt_tag, alt_model = loss_by_tag(modal, tags, a.arm, over_all_cells=True)
    altc_tag, _altc_model = loss_by_tag(modal, tags, a.control, over_all_cells=True)
    print("")
    print("  THE SAME FIGURE OVER ALL CELLS, not only those strong at baseline")
    print("")
    print("  %-16s %6s %22s %22s" % ("tag", "items", "instruction", "control"))
    for tag in sorted(distinct, key=lambda t: -(alt_tag[t][0] / alt_tag[t][1]
                                                if alt_tag.get(t) and alt_tag[t][1] else 0)):
        i_lost, i_tot = alt_tag.get(tag, (0, 0))
        c_lost, c_tot = altc_tag.get(tag, (0, 0))
        print("  %-16s %6d %21s %22s"
              % (tag, n_items[tag],
                 ("%5.1f%%  (%d/%d)" % (100.0 * i_lost / i_tot, i_lost, i_tot)) if i_tot else "-",
                 ("%5.1f%%  (%d/%d)" % (100.0 * c_lost / c_tot, c_lost, c_tot)) if c_tot else "-"))

    print("")
    print("  PAIRED PER MODEL: %s minus the mean of %s"
          % (a.focus, ", ".join(REFERENCE_TAGS)))
    for label, per_model in (("instruction, conditional", inst_model),
                             ("control, conditional", ctrl_model),
                             ("instruction, all cells", alt_model)):
        pairs = paired(per_model, a.focus, REFERENCE_TAGS)
        up, down, ties, p = sign_test(pairs)
        print("    %-26s %3d models  %3d higher  %3d lower  %3d tied   %s"
              % (label, len(pairs), up, down, ties,
                 ("sign test p = %.4f" % p) if p is not None else "not testable"))

    print("")
    print("  WHICH DENOMINATOR CARRIES THE CLAIM, and the reason is structural, not the")
    print("  result. **Over all cells.** Every tag gets the same denominator by construction")
    print("  -- 2 items x the panel -- so the comparison is balanced. Conditioning on a strong")
    print("  baseline answer does not: the tags draw strong answers at very different rates,")
    print("  which leaves the reference tags on single-digit cell counts and drops two thirds")
    print("  of the models for want of a strong answer on every tag. A comparison of 40 cells")
    print("  against 8 is not the comparison it looks like.")
    print("")
    print("  Both are printed above, always, and the conditional figure is not hidden because")
    print("  it disagrees. A reader who prefers it can see exactly what it rests on.")
    print("")
    print("  A CONSTANT offset could be subtracted. A selective one cannot, which is why this")
    print("  sits under §1 rather than beside it.")
    print("")
    print("  LIMITS, and they travel with the number: %d items carry the %s tag. Exploratory,"
          % (n_items.get(a.focus, 0), a.focus))
    print("  written after the data was seen. The LOYALTY reading is refuted -- see")
    print("  crossover_jurisdiction.py, and null_audit.py for the bound on that null.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
