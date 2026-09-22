#!/usr/bin/env python3
"""Does the instruction move position further than REORDERING THE ITEMS does?

WHY THIS IS THE COMPARISON THAT MATTERS
---------------------------------------
`position_analysis --prereg` now reports that the balance instruction moves position on most
of the panel, against a bootstrap that resamples sheets. That answers one question: is the
instruction effect bigger than sheet-to-sheet variation WITHIN a condition?

It does not answer the study's own question. The floors in `floor_table` are counted in
SIDE-FLIPS and ENDPOINT CHANGES; the contrasts are measured in POSITION. A claim that "the
effect exceeds the floor" cannot be made across two different units, and this study has
already withdrawn five claims for exactly that mistake
(`CORRECTIONS-2026-09-17-power.md`).

So this measures the presentation-order floor **in position units**, using the same estimator
as the contrast it is compared against:

    floor   position under condition N at one shuffle seed
            MINUS position under condition N at a different shuffle seed
            -- nothing changed but the order the items were printed in

    effect  position under the balance instruction MINUS position under N

Both through `contrast_sheets`, both BH-corrected within their own family, both reported as a
count of models. If the instruction does not beat item order, the instruction result is not a
measurement of the instruction.

    python scripts/order_floor_position.py
    python scripts/order_floor_position.py --run <dir> --draws 5000

Exit 0 computed, 2 NOT APPLICABLE (no model has two orders in one condition).
"""
from __future__ import annotations

import argparse
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import studypaths as _SP
import position_analysis as PA


#: The rendered table, cached with a signature of the corpus it was measured on.
#:
#: WHY A CACHE AT ALL. This is a 4000-draw bootstrap over every pair and takes minutes. It
#: became a generated block in the paper on 2026-09-21 -- correctly, because the hand-typed
#: version disagreed with it -- and `gen_paper --check` is run constantly. A gate that takes
#: ten minutes is a gate that gets skipped, which is how the strand gate was lost in the
#: publishing tree.
#:
#: WHY IT CANNOT ROT THE WAY `modal-noise.json` DID. That cache sat at 34 cells against a
#: corpus of 576 for two weeks: its regeneration path had been crashing since a key changed,
#: and nothing compared the signature it already carried. Here the signature is checked on
#: every read, a mismatch is a REFUSAL rather than a stale answer, and `--check-cache` exits
#: nonzero so the staleness is reachable from a test rather than only from a human reading
#: output.
CACHE = os.path.join(_SP.STUDY_DIR, "data", "position-floor.json")


def corpus_signature(run_dir, condition, draws):
    """What the cached table was measured over. Cheap: no bootstrap, just the sheets."""
    records = PA.load_records(run_dir)
    seeds = sorted({r.get("shuffle_seed") for r in records
                    if r.get("condition") == condition and r.get("shuffle_seed") is not None})
    return {"run": os.path.basename(run_dir.rstrip("/\\")),
            "condition": condition,
            "draws": draws,
            "records": len(records),
            "models": len({r.get("model") for r in records}),
            "seeds": [str(s) for s in seeds]}


def read_cache(signature):
    """The cached rows, or (None, why). A mismatch is refused, never returned."""
    import json as _json
    if not os.path.exists(CACHE):
        return None, "no cache at %s" % os.path.relpath(CACHE, _SP.STUDY_DIR)
    try:
        rec = _json.load(open(CACHE, encoding="utf-8"))
    except ValueError as exc:
        return None, "cache is unreadable (%s)" % exc
    was = rec.get("signature") or {}
    if was != signature:
        differs = sorted(k for k in set(was) | set(signature)
                         if was.get(k) != signature.get(k))
        return None, ("cache was measured over a different corpus -- %s differ(s). "
                      "Regenerate: order_floor_position.py --write" % ", ".join(differs))
    if not rec.get("rows"):
        return None, "cache holds no rows, which is not a measurement"
    return rec["rows"], None


def by_seed(records, condition):
    """Records relabelled so each shuffle seed becomes its own pseudo-condition."""
    out = []
    for r in records:
        if r.get("condition") != condition or r.get("shuffle_seed") is None:
            continue
        rec = dict(r)
        rec["condition"] = "s%s" % r["shuffle_seed"]
        out.append(rec)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", default="2026-09-16-ratchet-v3-wave")
    ap.add_argument("--draws", type=int, default=4000)
    ap.add_argument("--condition", default="N",
                    help="the condition whose seeds form the floor (default N, the bare ask)")
    ap.add_argument("--markdown", action="store_true",
                    help="the two rows as a markdown table, for the paper's GEN:position "
                         "block. Same computation, no second copy. Served from "
                         "data/position-floor.json when its signature matches the corpus.")
    ap.add_argument("--write", action="store_true",
                    help="recompute and refresh data/position-floor.json")
    ap.add_argument("--check-cache", action="store_true",
                    help="exit 1 if the cache is missing or stale, without recomputing")
    a = ap.parse_args(argv)

    run_dir = (a.run if os.path.isdir(a.run)
               else os.path.join(_SP.STUDY_DIR, "runs", a.run))
    if not os.path.isdir(run_dir):
        print("no such run directory: %s" % run_dir)
        return 2

    # THE CACHE IS CONSULTED BEFORE THE BOOTSTRAP AND ONLY FOR THE RENDERED TABLE. An
    # interactive run recomputes, because a person reading the verdict wants the measurement.
    signature = corpus_signature(run_dir, a.condition, a.draws)
    if a.check_cache:
        rows, why = read_cache(signature)
        if rows is None:
            print("POSITION-FLOOR CACHE STALE OR ABSENT -- %s" % why)
            return 1
        print("position-floor cache matches the corpus (%d record(s), %d model(s), seeds %s)"
              % (signature["records"], signature["models"], ",".join(signature["seeds"])))
        return 0
    if a.markdown and not a.write:
        rows, why = read_cache(signature)
        if rows is not None:
            for line in rows:
                print(line)
            return 0
        print("<!-- position-floor cache unusable: %s -- recomputing -->" % why,
              file=sys.stderr)

    index = PA.pair_index(PA.load_bank())
    records = PA.load_records(run_dir)
    if not records:
        print("CHECKED NOTHING -- no valid sheets. NOT a result.")
        return 2

    # ---- the floor: same condition, different presentation order
    relabelled = by_seed(records, a.condition)
    per_sheet = PA.sheet_positions(relabelled, index)
    seeds = sorted({c for (_m, c) in per_sheet})
    floor_rows = []
    for m in sorted({m for (m, _c) in per_sheet}):
        mine = [s for s in seeds if (m, s) in per_sheet]
        for i in range(len(mine)):
            for j in range(i + 1, len(mine)):
                r = PA.contrast_sheets(per_sheet, m, mine[i], mine[j], n=a.draws)
                if r:
                    r["kind"] = "order"
                    floor_rows.append(r)
    if not floor_rows:
        print("NOT APPLICABLE -- no model carries two presentation orders in condition %s."
              % a.condition)
        return 2
    PA._bh_fdr(floor_rows)

    # ---- the effect: the instruction, same estimator
    eff_sheets = PA.sheet_positions(records, index)
    eff_rows = []
    for m in sorted({m for (m, _c) in eff_sheets}):
        r = PA.contrast_sheets(eff_sheets, m, "A", a.condition, n=a.draws)
        if r:
            r["kind"] = "instruction"
            eff_rows.append(r)
    PA._bh_fdr(eff_rows)

    def stats(rows):
        eff = sorted(abs(r["effect"]) for r in rows)
        sig = [r for r in rows if r.get("significant_bh")]
        med = eff[len(eff) // 2] if eff else 0.0
        p90 = eff[min(int(0.9 * len(eff)), len(eff) - 1)] if eff else 0.0
        return med, p90, (eff[-1] if eff else 0.0), len(sig), len(rows)

    # THE PAPER'S SECTION 1 TABLE WAS TYPED, and it disagreed with this script on the two
    # rows they share: 111 order pairs against 108, and 62 significant against 46. The
    # abstract used this script's figures and section 1 used the hand table's, so the
    # document led with two versions of its own headline. It is generated now.
    if a.markdown or a.write:
        lines = ["| measured the same way, on the same sheets, with the same estimator | "
                 "pairs | median \\|effect\\| | p90 | max | clear BH-FDR |",
                 "|---|---:|---:|---:|---:|---:|"]
        for label, rows in (
                ("the balance instruction (A − %s)" % a.condition, eff_rows),
                ("**reprinting the items in a different order** (%s, seed vs seed)"
                 % a.condition, floor_rows)):
            med, p90, mx, sig, n = stats(rows)
            lines.append("| %s | %d | **%.3f** | %.3f | %.3f | %d (%.0f%%) |"
                         % (label, n, med, p90, mx, sig, 100.0 * sig / max(n, 1)))
        if a.write:
            import json as _json
            payload = {
                "_note": ("The paper's GEN:position table. A 4000-draw bootstrap over every "
                          "pair, cached so `gen_paper --check` stays fast. Derived -- "
                          "regenerate with order_floor_position.py --write, and see "
                          "--check-cache."),
                "signature": signature,
                "rows": lines,
            }
            with open(CACHE, "w", encoding="utf-8", newline="\n") as fh:
                _json.dump(payload, fh, indent=2, ensure_ascii=False)
                fh.write("\n")
            print("wrote %s" % os.path.relpath(CACHE, _SP.STUDY_DIR), file=sys.stderr)
        for line in lines:
            print(line)
        return 0

    def summarise(rows, label):
        med, p90, mx, sig, n = stats(rows)
        print("  %-38s n=%-4d  |effect| median %.3f  p90 %.3f  max %.3f   %d significant"
              % (label, n, med, p90, mx, sig))
        return med, p90, sig, n

    print("")
    print("  PRESENTATION ORDER AS A FLOOR, IN POSITION UNITS")
    print("  Both arms measured with the same estimator (contrast_sheets), %d draws." % a.draws)
    print("")
    f_med, f_p90, f_sig, f_n = summarise(
        floor_rows, "order floor (%s, seed vs seed)" % a.condition)
    e_med, e_p90, e_sig, e_n = summarise(
        eff_rows, "instruction (A - %s)" % a.condition)

    print("")
    print("  The floor is what the instrument does when ONLY the item order changes.")
    print("  %d of %d order pairs (%.0f%%) are themselves 'significant' -- that is the rate at"
          % (f_sig, f_n, 100.0 * f_sig / max(f_n, 1)))
    print("  which reordering alone produces a movement this estimator calls real.")
    print("")
    if e_med > f_p90:
        print("  VERDICT: the median instruction effect (%.3f) exceeds the p90 of the order"
              % e_med)
        print("  floor (%.3f). The instruction moves position further than reordering does."
              % f_p90)
    elif e_med > f_med:
        print("  VERDICT: the median instruction effect (%.3f) exceeds the MEDIAN order floor"
              % e_med)
        print("  (%.3f) but not its p90 (%.3f). Real on the typical model, inside the noise"
              % (f_med, f_p90))
        print("  on the noisiest ones. Report per model, never pooled.")
    else:
        print("  VERDICT: the median instruction effect (%.3f) does NOT exceed the median"
              % e_med)
        print("  order floor (%.3f). On this instrument the instruction does not move position"
              % f_med)
        print("  further than printing the items in a different sequence. That is not a small")
        print("  effect -- it is one this design cannot attribute to the instruction.")
    print("")
    print("  Neither number is a p-value and neither licenses a pooled claim. The comparison")
    print("  is between two distributions measured the same way on the same sheets.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
