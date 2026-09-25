#!/usr/bin/env python3
"""Is the placebo's behaviour a property of its sentence, or of any content-free instruction?

PREREG-2026-09-25-placebo-wording.md governs this; every measure and prediction below is its,
computed over `runs/2026-09-25-placebo-wording` (collected by `run_arm_battery.py --arm
placebo-wording`): N, P and a second placebo P2 matched to P in register and length, in one
sitting, protocol v2, three orders x five draws. Readers and tests are `arm_sheets.py`.

  R  refusal per condition; P vs P2, P vs N, P2 vs N by Fisher exact, two-sided
  M  P - N, P2 - N, P2 - P, sheet bootstrap + Monte-Carlo permutation p, BH over the family
  F  the model's own between-order |position| under N; a contrast at or below it is below floor
  S  per order, modal P vs modal P2 in side-flips and endpoints, beside the N order floor
  O  partial sheets per condition

    python scripts/placebo_wording.py
    python scripts/placebo_wording.py --json
    python scripts/placebo_wording.py --selftest

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

RUN = "2026-09-25-placebo-wording"
CONDITIONS = ("N", "P", "P2")
CONTRASTS = (("P", "N"), ("P2", "N"), ("P2", "P"))
DRAWS = 20000
SEED = 20260925

#: The wave's placebo movers (data/placebo-control.json, sheet bootstrap, BH), with the sign
#: of their wave P - N. H3 asks whether they move again, in the same direction.
WAVE_MOVERS = {
    "gemma2:9b-instruct-q8_0": +1,
    "qwen2.5:14b-instruct-q8_0": -1,
    "writer/palmyra-x5": +1,
    "xiaomi/mimo-v2.5-pro": +1,
    "mistralai/mistral-medium-3-5": +1,
    "openai/gpt-6-astra": +1,
}
REFERENCES = ("deepseek/deepseek-v3.2", "meta-llama/llama-3.3-70b-instruct")


def analyse(run_dir, draws=DRAWS, perm_draws=20000):
    index = PA.pair_index(PA.load_bank())
    recs = AS.read_records(run_dir)
    cells = AS.cells(recs, key=lambda r: (r.get("model"), r.get("condition")))
    models = sorted({m for m, _c in cells})
    rows, contrasts = [], []
    for m in models:
        per = {c: cells.get((m, c)) for c in CONDITIONS}
        if any(v is None for v in per.values()):
            rows.append({"model": m, "missing": [c for c, v in per.items() if v is None]})
            continue
        ref = {c: AS.refusal(per[c]) for c in CONDITIONS}

        def fp(a, b):
            (ra, na), (rb, nb) = ref[a], ref[b]
            return AS.fisher_two_sided(ra, na - ra, rb, nb - rb)

        floor = AS.order_floor(per["N"]["sheets"], index)
        mp, mp2 = AS.modal_by_order(per["P"]["sheets"]), AS.modal_by_order(per["P2"]["sheets"])
        pp2 = [FT.both_stats(mp[o], mp2[o]) for o in sorted(set(mp) & set(mp2))]
        row = {"model": m,
               "sheets": {c: len(per[c]["sheets"]) for c in CONDITIONS},
               "refusal": {c: list(ref[c]) for c in CONDITIONS},
               "refusal_p": {"P-P2": fp("P", "P2"), "P-N": fp("P", "N"), "P2-N": fp("P2", "N")},
               "labels": {c: dict(per[c]["labels"]) for c in CONDITIONS},
               "partial": {c: [per[c]["partial"], per[c]["attempts"]] for c in CONDITIONS},
               "off_pin": {c: per[c]["off_pin"] for c in CONDITIONS},
               "degenerate": {c: per[c]["degenerate"] for c in CONDITIONS},
               "floor_N": floor,
               "p_vs_p2_side": [s for s, _e in pp2], "p_vs_p2_end": [e for _s, e in pp2]}
        rows.append(row)
        for a, b in CONTRASTS:
            r = AS.contrast(AS.pair_sheets(per[a]["sheets"], index),
                            AS.pair_sheets(per[b]["sheets"], index),
                            seed=SEED, draws=draws, perm_draws=perm_draws)
            if r:
                contrasts.append({"model": m, "contrast": "%s - %s" % (a, b),
                                  **{k: r[k] for k in ("effect", "lo", "hi", "p", "perm_p",
                                                       "n_a", "n_b")},
                                  "floor": floor["pos_max"]})
    surv = AS.bh([c["p"] for c in contrasts])
    for i, c in enumerate(contrasts):
        c["bh"] = i in surv
        c["above_floor"] = c["floor"] is not None and abs(c["effect"]) > c["floor"]
        c["clears"] = c["bh"] and c["above_floor"]
    return {"run": os.path.basename(run_dir.rstrip("/\\")), "rows": rows,
            "contrasts": contrasts, "predictions": predictions(rows, contrasts)}


def _rate(pair):
    r, n = pair
    return (r / n) if n else None


def predictions(rows, contrasts):
    by = {r["model"]: r for r in rows if "refusal" in r}
    cx = {(c["model"], c["contrast"]): c for c in contrasts}
    out = []

    phi = by.get("phi4:latest")
    if not phi:
        v, d = "NOT TESTABLE (no phi4 cells)", {}
    else:
        rp, rp2 = phi["refusal"]["P"], phi["refusal"]["P2"]
        d = {"P": rp, "P2": rp2, "fisher_p": phi["refusal_p"]["P-P2"]}
        if rp[0] < 3:
            v = "NOT TESTABLE (phi4 refused P on %d of %d; the wave's anomaly did not reproduce)" \
                % tuple(rp)
        elif rp2[0] < rp[0] and phi["refusal_p"]["P-P2"] < 0.05:
            v = "CONFIRMED"
        else:
            v = "REFUTED"
    out.append({"id": "H1", "claim": "phi4's refusal is the sentence (P2 refused less, p < .05)",
                "detail": d, "verdict": v})

    gem = by.get("google/gemini-3.8-flash")
    if not gem:
        v, d = "NOT TESTABLE (no gemini cells)", {}
    else:
        rn, rp, rp2 = (_rate(gem["refusal"][c]) for c in CONDITIONS)
        d = {c: gem["refusal"][c] for c in CONDITIONS}
        if rn is None or rn < 0.8:
            v = ("NOT TESTABLE (N refuses %d of %d, below the registered 80%% precondition)"
                 % tuple(gem["refusal"]["N"]))
        elif rp is not None and rp2 is not None and rp <= 0.2 and rp2 <= 0.2:
            v = "CONFIRMED"
        elif rp is not None and rp <= 0.2 and (rp2 is None or rp2 > 0.2):
            v = "REFUTED (the unlocking is P's wording)"
        else:
            v = "REFUTED"
    out.append({"id": "H2", "claim": "gemini-3.8-flash: N refuses >= 80%, P and P2 both <= 20%",
                "detail": d, "verdict": v})

    again = [m for m, sign in WAVE_MOVERS.items()
             if (m, "P - N") in cx and cx[(m, "P - N")]["clears"]
             and (cx[(m, "P - N")]["effect"] > 0) == (sign > 0)]
    p2p = [m for (m, k), c in cx.items() if k == "P2 - P" and c["clears"]]
    v = ("REFUTED (P's movement reproduces)" if len(again) >= 4 else
         "REFUTED (the two placebos differ)" if len(p2p) >= 3 else
         "CONFIRMED" if len(again) <= 2 and len(p2p) <= 1 else "NOT CONFIRMED")
    out.append({"id": "H3", "claim": "placebo movement is chance: P - N re-clears on <= 2 of 6 "
                "wave movers; P2 - P clears on <= 1 of 10",
                "detail": {"wave_movers_clearing_again": again, "p2_minus_p_clearing": p2p,
                           "wave_movers_collected": [m for m in WAVE_MOVERS if m in by]},
                "verdict": v})
    moved = [(m, k) for m in REFERENCES for k in ("P - N", "P2 - N")
             if (m, k) in cx and cx[(m, k)]["clears"]]
    out.append({"id": "H4", "claim": "the references stay inert under P and P2",
                "detail": {"clearing": moved,
                           "collected": [m for m in REFERENCES if m in by]},
                "verdict": "REFUTED" if moved else "CONFIRMED"})
    return out


def render(res):
    print("placebo wording -- %s" % res["run"])
    print("")
    print("| model | sheets N/P/P2 | refused N | refused P | refused P2 | Fisher P v P2 | "
          "partial N/P/P2 | off-pin | P v P2 side (per order) | P v P2 endpoints | "
          "N order floor side/end/pos |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in res["rows"]:
        if "missing" in r:
            print("| `%s` | missing %s |" % (r["model"], ",".join(r["missing"])))
            continue
        f = r["floor_N"]
        print("| `%s` | %s | %d/%d | %d/%d | %d/%d | %.4f | %s | %s | %s | %s | %s/%s/%s |" % (
            r["model"], "/".join(str(r["sheets"][c]) for c in CONDITIONS),
            *r["refusal"]["N"], *r["refusal"]["P"], *r["refusal"]["P2"],
            r["refusal_p"]["P-P2"],
            "/".join("%d" % r["partial"][c][0] for c in CONDITIONS),
            sum(r["off_pin"].values()), r["p_vs_p2_side"], r["p_vs_p2_end"],
            f["side_max"], f["end_max"], f["pos_max"]))
    print("")
    print("| model | contrast | effect [95%] | boot p | perm p | BH | own floor | clears |")
    print("|---|---|---|---|---|---|---|---|")
    for c in res["contrasts"]:
        print("| `%s` | %s | %+.3f [%+.3f, %+.3f] | %.4f | %.4f | %s | %s | %s |" % (
            c["model"], c["contrast"], c["effect"], c["lo"], c["hi"], c["p"], c["perm_p"],
            "yes" if c["bh"] else "no", c["floor"], "YES" if c["clears"] else "no"))
    print("")
    for p in res["predictions"]:
        print("%s  %s  %s  %s" % (p["id"], p["verdict"], p["claim"], json.dumps(p["detail"])))


def selftest():
    import random
    import tempfile
    fails = []

    def check(label, cond):
        print("  [%s] %s" % ("ok" if cond else "FAIL", label))
        if not cond:
            fails.append(label)

    bank = PA.load_bank()
    rng = random.Random(5)
    tmp = tempfile.mkdtemp()

    def rec(model, cond, order, shift, refuse=False):
        base = {"schema": "battery-run/1", "model": model, "condition": cond,
                "provider_pinned": None, "provider": None, "shuffle_seed": order,
                "n_items": 32, "instrument": "ratchet-battery", "max_tokens": 40960,
                "tokens_out": 300}
        if refuse:
            return dict(base, valid=False, failure_mode="refused", answers=[], n_answers=0,
                        problems=["no answers"], response_text="I will not answer these.")
        ans = []
        for it in bank["items"]:
            v = (2 if it["frame"] == "critic" else 1) + (shift if it["frame"] == "critic"
                                                        else -shift)
            if rng.random() < 0.1:
                v += rng.choice((-1, 1))
            ans.append({"q": it["id"], "position": max(0, min(3, v))})
        return dict(base, valid=True, failure_mode=None, answers=ans, n_answers=32,
                    problems=[], response_text="x")

    with open(os.path.join(tmp, "x.jsonl"), "w", encoding="utf-8") as fh:
        for o in (11, 22, 33):
            for k in range(5):
                # phi4-like: refuses P on 4 of 5 draws, never P2.
                fh.write(json.dumps(rec("phi4:latest", "N", o, 0)) + "\n")
                fh.write(json.dumps(rec("phi4:latest", "P", o, 0, refuse=k < 4)) + "\n")
                fh.write(json.dumps(rec("phi4:latest", "P2", o, 0)) + "\n")
                # a model P moves and P2 does not.
                fh.write(json.dumps(rec("writer/palmyra-x5", "N", o, 0)) + "\n")
                fh.write(json.dumps(rec("writer/palmyra-x5", "P", o, 1)) + "\n")
                fh.write(json.dumps(rec("writer/palmyra-x5", "P2", o, 0)) + "\n")
                # a reference nothing moves.
                for c in CONDITIONS:
                    fh.write(json.dumps(rec("deepseek/deepseek-v3.2", c, o, 0)) + "\n")
    res = analyse(tmp, draws=1000, perm_draws=1000)
    pred = {p["id"]: p for p in res["predictions"]}
    cx = {(c["model"], c["contrast"]): c for c in res["contrasts"]}
    check("phi4-like refusal difference is detected (H1 CONFIRMED)",
          pred["H1"]["verdict"] == "CONFIRMED")
    check("a P-only shift clears P - N", cx[("writer/palmyra-x5", "P - N")]["clears"])
    check("the same shift clears P2 - P, negatively",
          cx[("writer/palmyra-x5", "P2 - P")]["clears"]
          and cx[("writer/palmyra-x5", "P2 - P")]["effect"] < 0)
    check("P2 - N does not clear when P2 does nothing",
          not cx[("writer/palmyra-x5", "P2 - N")]["clears"])
    check("the reference stays inert (H4 CONFIRMED)", pred["H4"]["verdict"] == "CONFIRMED")
    check("gemini absent -> H2 NOT TESTABLE", pred["H2"]["verdict"].startswith("NOT TESTABLE"))
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
