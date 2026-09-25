#!/usr/bin/env python3
"""One model, two pinned backends: does the serving path move side, conviction or position?

PREREG-2026-09-25-serving-path.md governs this; every measure and prediction below is its,
computed over `runs/2026-09-25-serving-path` (collected by `run_arm_battery.py --arm
serving-path`). The readers and tests are `arm_sheets.py`, which reuses the study's own
estimators rather than restating them.

Per model and condition:

  between backends   per order, modal(backend 1) vs modal(backend 2): side-flips, endpoints
                     (mean and max over the three orders); position, backend 2 - backend 1 over
                     all sheets, sheet bootstrap + Monte-Carlo permutation p, BH over 10
  own order floor    on each backend, modal(order a) vs modal(order b), and |position| between
                     orders; the floor is the maximum over both backends
  refusal, omission  per backend, Fisher exact two-sided
  instruction        A - N per backend (sheet bootstrap), sign agreement across backends

    python scripts/serving_path.py
    python scripts/serving_path.py --json
    python scripts/serving_path.py --selftest

Reads only. No API calls.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import studypaths as _SP           # noqa: E402
import position_analysis as PA     # noqa: E402
import floor_table as FT           # noqa: E402
import arm_sheets as AS            # noqa: E402

RUN = "2026-09-25-serving-path"
CONDITIONS = ("N", "A")
DRAWS = 20000
SEED = 20260925


def analyse(run_dir, draws=DRAWS, perm_draws=20000):
    index = PA.pair_index(PA.load_bank())
    recs = AS.read_records(run_dir)
    cells = AS.cells(recs, key=lambda r: (r.get("model"), r.get("provider_pinned"),
                                          r.get("condition")))
    models = collections.OrderedDict()
    for (m, p, _c) in sorted(cells, key=lambda k: (k[0], str(k[1]), k[2])):
        models.setdefault(m, [])
        if p not in models[m]:
            models[m].append(p)
    # Backend 1 is the wave's (the collector's first cell for the model).
    try:
        import run_arm_battery as RAB
        order = [c[2] for c in RAB.ARMS["serving-path"]["cells"]]
        for m in models:
            models[m].sort(key=lambda p: order.index(p) if p in order else 99)
    except Exception:
        pass

    rows, pvals = [], []
    for m, provs in models.items():
        if len(provs) != 2:
            rows.append({"model": m, "error": "expected two backends, found %s" % provs})
            continue
        b1, b2 = provs
        for c in CONDITIONS:
            c1, c2 = cells.get((m, b1, c)), cells.get((m, b2, c))
            if not c1 or not c2:
                continue
            m1, m2 = AS.modal_by_order(c1["sheets"]), AS.modal_by_order(c2["sheets"])
            shared = sorted(set(m1) & set(m2))
            bs = [FT.both_stats(m1[o], m2[o]) for o in shared]
            f1 = AS.order_floor(c1["sheets"], index)
            f2 = AS.order_floor(c2["sheets"], index)
            floor = {k: max([x for x in (f1[k], f2[k]) if x is not None], default=None)
                     for k in ("side_max", "end_max", "pos_max")}
            pos = AS.contrast(AS.pair_sheets(c2["sheets"], index),
                              AS.pair_sheets(c1["sheets"], index),
                              seed=SEED, draws=draws, perm_draws=perm_draws)
            r1, n1 = AS.refusal(c1)
            r2, n2 = AS.refusal(c2)
            row = {
                "model": m, "condition": c, "backend_1": b1, "backend_2": b2,
                "sheets": [len(c1["sheets"]), len(c2["sheets"])],
                "orders": shared,
                "side_between": [s for s, _e in bs], "end_between": [e for _s, e in bs],
                "side_mean": round(st.mean(s for s, _e in bs), 2) if bs else None,
                "end_mean": round(st.mean(e for _s, e in bs), 2) if bs else None,
                "floor": floor, "floor_backend_1": f1, "floor_backend_2": f2,
                "position": pos,
                "refusal": [[r1, n1], [r2, n2]],
                "refusal_p": AS.fisher_two_sided(r1, n1 - r1, r2, n2 - r2),
                "partial": [[c1["partial"], c1["attempts"]], [c2["partial"], c2["attempts"]]],
                "partial_p": AS.fisher_two_sided(c1["partial"], c1["attempts"] - c1["partial"],
                                                 c2["partial"], c2["attempts"] - c2["partial"]),
                "off_pin": [c1["off_pin"], c2["off_pin"]],
                "degenerate": [c1["degenerate"], c2["degenerate"]],
                "labels": [dict(c1["labels"]), dict(c2["labels"])],
            }
            row["side_exceeds"] = (row["side_mean"] is not None and floor["side_max"] is not None
                                   and row["side_mean"] > floor["side_max"])
            row["end_exceeds"] = (row["end_mean"] is not None and floor["end_max"] is not None
                                  and row["end_mean"] > floor["end_max"])
            # A CELL THAT CANNOT BE COMPARED IS REPORTED, NOT SCORED AS AGREEING. With no order
            # held on both backends there is no matched modal pair, and with fewer than two
            # orders on a backend there is no floor; counting such a model as "within floor"
            # would let a backend that served nothing confirm H1.
            row["insufficient"] = (not shared or f1["pairs"] == 0 or f2["pairs"] == 0)
            rows.append(row)
            pvals.append(pos["p"] if pos else None)
    live = [r for r in rows if "error" not in r and not r.get("insufficient")]
    pvals = [r["position"]["p"] if r["position"] else None for r in live]
    surv = AS.bh(pvals)
    for i, r in enumerate(live):
        pos = r["position"]
        r["position_bh"] = i in surv
        r["position_exceeds"] = bool(pos and r["position_bh"] and r["floor"]["pos_max"] is not None
                                     and abs(pos["effect"]) > r["floor"]["pos_max"])

    # The instruction per backend.
    instr = []
    ipv = []
    for m, provs in models.items():
        for p in provs:
            n, a = cells.get((m, p, "N")), cells.get((m, p, "A"))
            if not n or not a:
                continue
            r = AS.contrast(AS.pair_sheets(a["sheets"], index), AS.pair_sheets(n["sheets"], index),
                            seed=SEED, draws=draws, perm_draws=perm_draws)
            if r:
                instr.append({"model": m, "backend": p, **{k: r[k] for k in
                              ("effect", "lo", "hi", "p", "perm_p")}})
                ipv.append(r["p"])
    isurv = AS.bh(ipv)
    for i, r in enumerate(instr):
        r["bh"] = i in isurv
    return {"run": os.path.basename(run_dir.rstrip("/\\")), "rows": rows, "instruction": instr,
            "predictions": predictions(live, instr)}


def predictions(rows, instr):
    models = sorted({r["model"] for r in rows})
    out = []
    by_c = {c: [r for r in rows if r["condition"] == c] for c in CONDITIONS}
    side_bad = {c: [r["model"] for r in by_c[c] if r["side_exceeds"]] for c in CONDITIONS}
    held = [m for m in models if not any(m in side_bad[c] for c in CONDITIONS)]
    worst = max((len(v) for v in side_bad.values()), default=0)
    out.append({"id": "H1", "claim": "side holds across backends (>= 4 of 5 within floor)",
                "detail": {"within_floor_both_conditions": held,
                           "exceeding_by_condition": side_bad},
                "verdict": "REFUTED" if worst >= 2 else
                           ("CONFIRMED" if len(held) >= 4 else "NOT CONFIRMED")})
    end_models = sorted({r["model"] for r in rows if r["end_exceeds"]})
    out.append({"id": "H2", "claim": "conviction differs: endpoints exceed floor on >= 2 of 5",
                "detail": {"exceeding": end_models},
                "verdict": "CONFIRMED" if len(end_models) >= 2 else "REFUTED"})
    pos_bad = {c: [r["model"] for r in by_c[c] if r["position_exceeds"]] for c in CONDITIONS}
    out.append({"id": "H3", "claim": "position holds: <= 1 of 5 clears BH and floor per condition",
                "detail": pos_bad,
                "verdict": "REFUTED" if max(len(v) for v in pos_bad.values()) >= 2
                           else "CONFIRMED"})
    ref_diff = [(r["model"], r["condition"]) for r in rows if r["refusal_p"] < 0.05]
    refusing = [(r["model"], r["condition"]) for r in rows
                if r["refusal"][0][0] + r["refusal"][1][0] > 1]
    partials = [(r["model"], r["condition"], r["partial"]) for r in rows
                if r["partial"][0][0] or r["partial"][1][0]]
    out.append({"id": "H4", "claim": "no refusal difference, no partial sheet under v2",
                "detail": {"refusal_difference_p_lt_05": ref_diff,
                           "more_than_one_refusal": refusing, "partial_sheets": partials},
                "verdict": "REFUTED" if (ref_diff or partials) else "CONFIRMED"})
    by_m = collections.defaultdict(list)
    for r in instr:
        by_m[r["model"]].append(r)
    reversals = [m for m, rs in by_m.items() if len(rs) == 2 and any(x["bh"] for x in rs)
                 and (rs[0]["effect"] > 0) != (rs[1]["effect"] > 0)]
    out.append({"id": "H5", "claim": "A - N keeps its sign across backends",
                "detail": {"reversals": reversals},
                "verdict": "REFUTED" if reversals else "CONFIRMED"})
    return out


def render(res):
    print("serving path -- %s" % res["run"])
    print("")
    print("| model | cond | backends | sheets | side between (mean/max) | own side floor | "
          "endpoints between (mean/max) | own endpoint floor | position b2-b1 [95%] | perm p | "
          "own position floor | clears |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in res["rows"]:
        if "error" in r:
            print("| %s | ERROR %s |" % (r["model"], r["error"]))
            continue
        p = r["position"] or {}
        print("| `%s` | %s | %s / %s | %d / %d | %s / %s | %s | %s / %s | %s | %+.3f [%+.3f, %+.3f] "
              "| %.4f | %s | %s |" % (
                  r["model"], r["condition"], r["backend_1"], r["backend_2"],
                  r["sheets"][0], r["sheets"][1], r["side_mean"],
                  max(r["side_between"], default=None),
                  r["floor"]["side_max"], r["end_mean"], max(r["end_between"], default=None),
                  r["floor"]["end_max"], p.get("effect", 0), p.get("lo", 0), p.get("hi", 0),
                  p.get("perm_p", 1), r["floor"]["pos_max"],
                  "INSUFFICIENT" if r.get("insufficient") else
                  (",".join(x for x, f in (("side", r["side_exceeds"]),
                                           ("endpoint", r["end_exceeds"]),
                                           ("position", r.get("position_exceeds"))) if f)
                   or "-")))
    print("")
    print("| model | cond | refused b1 | refused b2 | Fisher p | partial b1 | partial b2 | "
          "Fisher p | off-pin | degenerate |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for r in res["rows"]:
        if "error" in r:
            continue
        print("| `%s` | %s | %d/%d | %d/%d | %.3f | %d/%d | %d/%d | %.3f | %s | %s |" % (
            r["model"], r["condition"], r["refusal"][0][0], r["refusal"][0][1],
            r["refusal"][1][0], r["refusal"][1][1], r["refusal_p"],
            r["partial"][0][0], r["partial"][0][1], r["partial"][1][0], r["partial"][1][1],
            r["partial_p"], r["off_pin"], r["degenerate"]))
    print("")
    print("| model | backend | A - N [95%] | p | perm p | BH |")
    print("|---|---|---|---|---|---|")
    for r in res["instruction"]:
        print("| `%s` | %s | %+.3f [%+.3f, %+.3f] | %.4f | %.4f | %s |" % (
            r["model"], r["backend"], r["effect"], r["lo"], r["hi"], r["p"], r["perm_p"],
            "yes" if r["bh"] else "no"))
    print("")
    for p in res["predictions"]:
        print("%s  %-9s %s  %s" % (p["id"], p["verdict"], p["claim"],
                                   json.dumps(p["detail"])))


def selftest():
    import tempfile
    import random
    fails = []

    def check(label, cond):
        print("  [%s] %s" % ("ok" if cond else "FAIL", label))
        if not cond:
            fails.append(label)

    bank = PA.load_bank()
    rng = random.Random(3)
    tmp = tempfile.mkdtemp()

    def rec(model, prov, cond, order, shift):
        ans = []
        for it in bank["items"]:
            v = (2 if it["frame"] == "critic" else 1) + (shift if it["frame"] == "critic"
                                                        else -shift)
            if rng.random() < 0.1:
                v += rng.choice((-1, 1))
            ans.append({"q": it["id"], "position": max(0, min(3, v))})
        return {"schema": "battery-run/1", "model": model, "condition": cond,
                "provider_pinned": prov, "provider": prov, "shuffle_seed": order,
                "valid": True, "failure_mode": None, "n_items": 32, "n_answers": 32,
                "problems": [], "response_text": "x", "answers": ans,
                "instrument": "ratchet-battery"}

    with open(os.path.join(tmp, "x.jsonl"), "w", encoding="utf-8") as fh:
        for prov, shift in (("P1", 0), ("P2", 0)):
            for cond, cs in (("N", 0), ("A", -1)):
                for o in (11, 22, 33):
                    for _ in range(5):
                        fh.write(json.dumps(rec("same/m", prov, cond, o, shift + cs)) + "\n")
        for prov, shift in (("P1", 0), ("P2", 1)):
            for cond, cs in (("N", 0), ("A", -1)):
                for o in (11, 22, 33):
                    for _ in range(5):
                        fh.write(json.dumps(rec("moved/m", prov, cond, o, shift + cs)) + "\n")
    res = analyse(tmp, draws=1000, perm_draws=1000)
    rows = {(r["model"], r["condition"]): r for r in res["rows"]}
    check("identical backends: position does not clear",
          not rows[("same/m", "N")]["position_exceeds"])
    check("a shifted backend: position clears BH and its floor",
          rows[("moved/m", "N")]["position_exceeds"])
    # A +1 intensity shift (Agree -> Strongly Agree, Disagree -> Strongly Disagree) changes
    # conviction and not side, so it must register as endpoints and NOT as side-flips.
    check("a shifted backend: endpoints exceed the order floor",
          rows[("moved/m", "N")]["end_exceeds"])
    check("a shifted backend: an intensity shift is not a side-flip",
          not rows[("moved/m", "N")]["side_exceeds"])
    check("identical backends: side-flips within the floor",
          not rows[("same/m", "N")]["side_exceeds"])
    check("the instruction reads about -1 on every backend",
          all(-1.2 < r["effect"] < -0.8 for r in res["instruction"]))
    check("predictions evaluate", len(res["predictions"]) == 5)
    print("")
    print("  %d check(s) failed" % len(fails))
    return 1 if fails else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", default=RUN)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--draws", type=int, default=DRAWS)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    run_dir = str(_SP.run_path(a.run))
    if not os.path.isdir(run_dir) or not AS.read_records(run_dir):
        print("no battery records in %s -- NOT APPLICABLE, nothing computed" % run_dir)
        return 2
    res = analyse(run_dir, draws=a.draws, perm_draws=a.draws)
    if a.json:
        print(json.dumps(res, indent=1, sort_keys=True, default=str))
    else:
        render(res)
    return 0


if __name__ == "__main__":
    sys.exit(main())
