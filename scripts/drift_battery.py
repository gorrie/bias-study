#!/usr/bin/env python3
"""Version drift on the 32-item battery, scored against the same-version null. EXPLORATORY.

WHY THIS EXISTS. On the retired questionnaire the drift claim died twice: first because three
of 108 transitions cleared a same-version null, then because that null itself was a count out of
62 judged against thresholds out of 32, and "version drift does not replicate" was withdrawn
with the other four nulls rather than re-measured. The battery's same-version null is now
measured (24 pairs, side threshold 2, MDE 3), and the wave already holds version lineages. This
is the re-measurement, and it is the "placebo of the time axis" the 2026-08-30 design review
specified and nobody ran: same-version siblings as the null, a transition counting only if it
clears that null, and a directional claim only if at least three lineages from different vendors
move the same way.

It is post hoc -- computed after the data was seen, not pre-registered -- and is reported as
exploratory. Everything is imported from the study's own machinery: floor_table's pooling and
statistics, classify_lineage's successor rule, power's thresholds, position_analysis's sheet
bootstrap. The sheet bootstrap is NOT a valid test between two different models (it rejects
most same-version null pairs), so position is scored against the null's own |position| spread,
not by its p-value.

    python scripts/drift_battery.py [--json out.json]
"""
from __future__ import annotations

import collections
import json
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import floor_table as F  # noqa: E402
import classify_lineage as CL  # noqa: E402
import power as PW  # noqa: E402
import position_analysis as PA  # noqa: E402
import strong_shift as SS  # noqa: E402

WAVE = os.path.join(STUDY, "runs", "2026-09-16-ratchet-v3-wave")
BOOT = 5000


def pooled_modals(cond):
    """Exactly floor_same_version's pooling: every valid sheet of a model under `cond`."""
    cells = F.load(F.SAME_VERSION_GLOB, cond)
    by = collections.defaultdict(list)
    for (m, c, o), runs in cells.items():
        by[m].extend(runs)
    return {m: v for m, v in by.items() if len(v) >= 2}


def signed_endpoint(a, b):
    shared = [q for q in a if q in b]
    gained = sum(1 for q in shared if not F.ext(a[q]) and F.ext(b[q]))
    lost = sum(1 for q in shared if F.ext(a[q]) and not F.ext(b[q]))
    return gained - lost


def pairs_for(by):
    ids = sorted(by)
    parsed = {i: CL.parse(i) for i in ids}
    nulls, succ = [], []
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            label, is_version = CL.classify(parsed[a], parsed[b])
            if is_version:
                pa, pb = parsed[a], parsed[b]
                if CL.vkey(pa["version"]) > CL.vkey(pb["version"]):
                    a, b = b, a
                succ.append((a, b))
            elif label.endswith("(null)"):
                nulls.append((a, b, label))
    return nulls, succ


def adjacent_only(succ, all_ids):
    """Keep adjacent versions within a lineage, as classify_lineage.main does, plus the
    oldest->newest endpoint pair per lineage (the design review's decision rule)."""
    parsed = {i: CL.parse(i) for i in all_ids}
    groups = collections.defaultdict(set)
    for a, b in succ:
        p = parsed[a]
        groups[(p["vendor"], p["stem"], p["size"], p["mode"], p["tier"])].update((a, b))
    adj, ends = [], []
    for g, members in groups.items():
        ms = sorted(members, key=lambda m: CL.vkey(parsed[m]["version"]))
        for i in range(len(ms) - 1):
            adj.append((ms[i], ms[i + 1]))
        if len(ms) > 2:
            ends.append((ms[0], ms[-1]))
    return sorted(adj), sorted(ends)


def lineage_sheets():
    recs = PA.load_records(WAVE)
    index = PA.pair_index(PA.load_bank())
    return recs, PA.sheet_positions(recs, index), SS.strong_counts(recs)


def pos_contrast(per_sheet, a, b, cond, seed):
    sa, sb = per_sheet.get((a, cond)), per_sheet.get((b, cond))
    if not sa or not sb:
        return None
    fake = {("x", "new"): sb, ("x", "old"): sa}
    return PA.contrast_sheets(fake, "x", "new", "old", seed=seed, n=BOOT)


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", help="also write the full result here")
    args = ap.parse_args(argv)
    res = {"note": "EXPLORATORY, POST HOC. Not pre-registered.", "conditions": {}}
    recs, per_sheet, strong = lineage_sheets()
    # order floor per model (condition D, one sitting) for the "own seed floor" rule
    order_rows = {name: pairs for name, pairs in PW._pairs_for(F.floor_order_wave)}
    order_side = [p[0] for p in order_rows["presentation order, one sitting"]]
    order_ep = [p[1] for p in order_rows["presentation order, one sitting"]]
    ord_thr_s, ord_thr_e = PW.pctile(order_side, 0.95), PW.pctile(order_ep, 0.95)
    by_class = {n: p for n, p in PW._pairs_for(F.floor_order_wave_by_class)}
    res["order_floor"] = {"n": len(order_side), "side_p95": ord_thr_s, "endpoint_p95": ord_thr_e,
                          "side_p90": sorted(order_side)[int(0.9 * len(order_side)) - 1],
                          "by_class": {n: {"n": len(p),
                                           "side_p95": PW.pctile([x[0] for x in p], 0.95),
                                           "endpoint_p95": PW.pctile([x[1] for x in p], 0.95)}
                                       for n, p in by_class.items()}}
    # per-model own order floor: max side / endpoint over that model's order pairs under D
    own = collections.defaultdict(lambda: [0, 0])
    cells = collections.defaultdict(list)
    for pattern in ("runs/*-wave/*.jsonl", "runs/*-wave-orders/*.jsonl"):
        got = F.load(pattern, condition="D", key=lambda r: (r["model"], r.get("shuffle_seed")),
                     dedupe_by_seed=True)
        for k, runs in got.items():
            cells[k].extend(runs)
    bym = collections.defaultdict(dict)
    for (m, o), runs in cells.items():
        bym[m][o] = F.modal(runs)
    for m, orders in bym.items():
        ks = list(orders)
        for i in range(len(ks)):
            for j in range(i + 1, len(ks)):
                s, e = F.both_stats(orders[ks[i]], orders[ks[j]])
                own[m][0] = max(own[m][0], s)
                own[m][1] = max(own[m][1], e)

    for cond in ("N", "D"):
        by = pooled_modals(cond)
        modals = {m: F.modal(v) for m, v in by.items()}
        nulls, succ = pairs_for(by)
        null_stats = [F.both_stats(modals[a], modals[b]) for a, b, _ in nulls]
        ns = [x[0] for x in null_stats]
        ne = [x[1] for x in null_stats]
        thr_s, thr_e = PW.pctile(ns, 0.95), PW.pctile(ne, 0.95)
        mde_s, mde_e = PW.mde(ns, thr_s), PW.mde(ne, thr_e)
        # null calibration of the cross-model sheet bootstrap
        null_pos = []
        for k, (a, b, lab) in enumerate(nulls):
            r = pos_contrast(per_sheet, a, b, cond, 7000 + k)
            if r:
                null_pos.append(r)
        adj, ends = adjacent_only(succ, list(by))
        rows = []
        for kind, lst in (("adjacent", adj), ("oldest->newest", ends)):
            for k, (a, b) in enumerate(lst):
                s, e = F.both_stats(modals[a], modals[b])
                se = signed_endpoint(modals[a], modals[b])
                pc = pos_contrast(per_sheet, a, b, cond, 9000 + k)
                sa, sb = strong.get((a, cond)), strong.get((b, cond))
                ds = (SS.median(sb) - SS.median(sa)) if sa and sb else None
                rows.append({
                    "kind": kind, "old": a, "new": b, "vendor": a.split("/")[0],
                    "n_old": len(by[a]), "n_new": len(by[b]),
                    "side": s, "endpoint": e, "endpoint_signed": se,
                    "strong_median_delta": ds,
                    "side_clears_null": s > thr_s, "endpoint_clears_null": e > thr_e,
                    "side_clears_order": s > ord_thr_s, "endpoint_clears_order": e > ord_thr_e,
                    "own_order_max_side": max(own[a][0], own[b][0]) if a in own and b in own else None,
                    "own_order_max_endpoint": max(own[a][1], own[b][1]) if a in own and b in own else None,
                    "position": pc})
        # BH over adjacent position contrasts
        adjrows = [r for r in rows if r["kind"] == "adjacent" and r["position"]]
        ps = sorted(((r["position"]["p"], i) for i, r in enumerate(adjrows)))
        m = len(ps)
        passed = set()
        for rank, (p, i) in enumerate(ps, 1):
            if p <= 0.05 * rank / m:
                passed = {j for _, j in ps[:rank]}
        for i, r in enumerate(adjrows):
            r["position_bh"] = i in passed
        res["conditions"][cond] = {
            "null": {"n": len(ns), "side_med_p90_max": (st.median(ns), sorted(ns)[int(.9 * len(ns)) - 1], max(ns)),
                     "endpoint_med_p90_max": (st.median(ne), sorted(ne)[int(.9 * len(ne)) - 1], max(ne)),
                     "side_threshold": thr_s, "side_mde": mde_s,
                     "endpoint_threshold": thr_e, "endpoint_mde": mde_e,
                     "position_null_pairs": len(null_pos),
                     "position_null_reject": sum(1 for r in null_pos if r["excludes_zero"]),
                     "position_null_abs_effects": sorted(abs(r["effect"]) for r in null_pos)},
            "models_with_sheets": len(by),
            "missing_lineage_members": sorted(
                {x for pair in [("google/gemini-3.7-flash", "google/gemini-3.8-flash")] for x in pair}
                - set(by)),
            "transitions": rows}

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(res, fh, indent=1, default=str)

    print("EXPLORATORY, POST HOC -- version drift on the battery")
    print("order floor (one sitting, D): n=%d side p95 %s endpoint p95 %s"
          % (len(order_side), ord_thr_s, ord_thr_e))
    for n, d in res["order_floor"]["by_class"].items():
        print("   %s: n=%d side p95 %s endpoint p95 %s" % (n, d["n"], d["side_p95"], d["endpoint_p95"]))
    for cond, d in res["conditions"].items():
        nd = d["null"]
        print("\n=== condition %s: same-version null n=%d side med/p90/max %s thr %s MDE %s | "
              "endpoint %s thr %s MDE %s" % (cond, nd["n"], nd["side_med_p90_max"],
                                             nd["side_threshold"], nd["side_mde"],
                                             nd["endpoint_med_p90_max"], nd["endpoint_threshold"],
                                             nd["endpoint_mde"]))
        print("    sheet-bootstrap on null pairs: %d/%d exclude zero; |effect| med %.3f max %.3f"
              % (nd["position_null_reject"], nd["position_null_pairs"],
                 st.median(nd["position_null_abs_effects"]) if nd["position_null_abs_effects"] else float("nan"),
                 max(nd["position_null_abs_effects"]) if nd["position_null_abs_effects"] else float("nan")))
        v = nd["position_null_abs_effects"]
        if v:
            print("    null |position|: p95 %.3f  max %.3f -- a transition's |position| is scored "
                  "against these" % (PW.pctile(v, 0.95), max(v)))
        print("    missing (no >=2 valid sheets): %s" % d["missing_lineage_members"])
        print("    %-15s %-30s %-30s %5s %4s %4s %5s %5s %s" % ("kind", "old", "new", "side", "ep",
                                                               "ep+-", "dStr", "own", "position"))
        for r in d["transitions"]:
            p = r["position"]
            ptxt = ("%+.3f [%+.3f,%+.3f] p=%.3f%s" % (p["effect"], p["lo"], p["hi"], p["p"],
                                                      " BH" if r.get("position_bh") else "")
                    if p else "-")
            print("    %-15s %-30s %-30s %3d%s %3d%s %+4d %+5s %5s %s"
                  % (r["kind"], r["old"][:30], r["new"][:30], r["side"],
                     "*" if r["side_clears_null"] else " ", r["endpoint"],
                     "*" if r["endpoint_clears_null"] else " ", r["endpoint_signed"],
                     r["strong_median_delta"], "%s/%s" % (r["own_order_max_side"], r["own_order_max_endpoint"]),
                     ptxt))
    return 0


if __name__ == "__main__":
    sys.exit(main())
