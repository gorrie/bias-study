#!/usr/bin/env python3
"""Do the judged path and the forced-choice path agree on the SAME 32 propositions?

PREREG-2026-09-25-same-items-both-paths.md governs this; every measure, sensitivity,
interpretation rule and prediction below is its.

  forced choice  the wave's valid sheets (`runs/2026-09-16-ratchet-v3-wave`), conditions N, A,
                 read by `position_analysis.load_records`, SKEPTIC-CODED: the answer on a
                 critic-framed item, 3 minus it on a defender-framed one, so higher is more
                 institution-skeptical on both paths
  judged         `runs/2026-09-25-same-items-both-paths/scored/` (collected and scored by
                 `run_both_paths.py`), the panel median per record, `eligibility.py` at read
                 time, off-pin records excluded

  M1 direction agreement    sign(judged - 3) against the forced-choice side, item-cluster CI
  M2 commitment             share of eligible judged records at exactly 3
  M3 rank agreement         Spearman between the two paths over (model, item) cells
  M4 the instruction        compression |pos_A| < |pos_N| per model and path; per-item sign of
                            A - N across paths
  M5 own agreement          judged sample-vs-sample; forced choice order-vs-order

    python scripts/both_paths.py
    python scripts/both_paths.py --json
    python scripts/both_paths.py --selftest

Reads only. No API calls.
"""
from __future__ import annotations

import argparse
import collections
import glob
import io
import itertools
import json
import os
import random
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
import eligibility as EL           # noqa: E402

RUN = "2026-09-25-same-items-both-paths"
WAVE = "2026-09-16-ratchet-v3-wave"
CONDITIONS = ("N", "A")
BOOT = 10000
SEED = 20260925
WINDOW = 3000          # score.call_judge shows the judge response[:3000]


# ---- forced choice --------------------------------------------------------------------------

def fc_cells(sheets, bank, models):
    """{(model, cond, item): {"mean": s_fc, "side": +1/-1/0, "by_order": {order: [s...]}}}."""
    frame = {it["id"]: it["frame"] for it in bank["items"]}
    acc = collections.defaultdict(lambda: collections.defaultdict(list))
    for rec in sheets:
        m, c = rec.get("model"), rec.get("condition")
        if m not in models or c not in CONDITIONS:
            continue
        for item, pos in (rec.get("answers") or {}).items():
            if pos is None or int(item) not in frame:
                continue
            s = pos if frame[int(item)] == "critic" else 3 - pos
            acc[(m, c, int(item))][rec.get("shuffle_seed")].append(s)
    out = {}
    for key, by_order in acc.items():
        allv = [v for vs in by_order.values() for v in vs]
        skept = sum(1 for v in allv if v >= 2)
        side = 1 if skept * 2 > len(allv) else -1 if skept * 2 < len(allv) else 0
        out[key] = {"mean": st.mean(allv), "side": side, "n": len(allv),
                    "by_order": dict(by_order)}
    return out


def fc_self_agreement(cells):
    """Side agreement between per-order modal sides of one cell, over every order pair."""
    agree = total = 0
    for cell in cells.values():
        sides = {}
        for o, vals in cell["by_order"].items():
            k = sum(1 for v in vals if v >= 2)
            if k * 2 != len(vals):
                sides[o] = 1 if k * 2 > len(vals) else -1
        for a, b in itertools.combinations(sorted(sides), 2):
            total += 1
            agree += sides[a] == sides[b]
    return (agree / total if total else None), total


# ---- judged ---------------------------------------------------------------------------------

def _median(xs):
    xs = sorted(xs)
    n = len(xs)
    if not n:
        return None
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def vendor(model_id):
    return (model_id or "").split("/")[0]


def judged_records(scored_dir):
    recs = []
    for path in sorted(glob.glob(os.path.join(scored_dir, "*.jsonl"))):
        for line in io.open(path, encoding="utf-8"):
            if line.strip():
                recs.append(json.loads(line))
    return recs


def judged_scores(recs, variant="panel"):
    """{(model, cond, item): [score per eligible sample]} plus an exclusion ledger.

    `variant`: "panel" (the stored median), "judge:<id>" (one judge alone), "no-own-vendor"
    (median of the judges not sharing the subject's vendor), "window" (panel, responses within
    the judge's 3,000-character window only).
    """
    out = collections.defaultdict(list)
    excluded = collections.Counter()
    records = collections.Counter()
    for r in recs:
        key = (r.get("model"), r.get("condition"), r.get("item_id"))
        records[(key[0], key[1])] += 1
        pin, served = r.get("provider_pinned"), r.get("provider")
        if pin and served and served != pin:
            excluded[(key[0], key[1], "off-pin")] += 1
            continue
        reason = EL.exclusion_reason(r)
        if reason:
            excluded[(key[0], key[1], reason)] += 1
            continue
        if not EL.is_eligible(r):
            excluded[(key[0], key[1], "unscored")] += 1
            continue
        score = r.get("score_classifier")
        if variant.startswith("judge:"):
            j = variant.split(":", 1)[1]
            got = [x.get("score") for x in (r.get("score_classifier_judges") or [])
                   if x.get("judge") == j and x.get("score") is not None]
            score = got[0] if got else None
        elif variant == "no-own-vendor":
            got = [x.get("score") for x in (r.get("score_classifier_judges") or [])
                   if x.get("score") is not None and vendor(x.get("judge")) != vendor(key[0])]
            score = _median(got)
        elif variant == "window" and len(r.get("response_text") or "") > WINDOW:
            excluded[(key[0], key[1], "outside-window")] += 1
            continue
        if score is None:
            continue
        out[key].append(float(score))
    return out, excluded, records


def judged_cells(scores):
    return {k: {"mean": st.mean(v), "dir": (1 if st.mean(v) > 3 else -1 if st.mean(v) < 3 else 0),
                "samples": v} for k, v in scores.items() if v}


# ---- the measures ---------------------------------------------------------------------------

def _boot_items(fn, items, seed=SEED, n=BOOT):
    rng = random.Random(seed)
    vals = []
    for _ in range(n):
        sample = [items[rng.randrange(len(items))] for _ in items]
        v = fn(sample)
        if v is not None:
            vals.append(v)
    if len(vals) < 2:
        return None, None
    vals.sort()
    return vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals))]


def _by_item(pairs):
    """[(item, value)] -> {item: [values]}, so a cluster bootstrap looks items up."""
    out = collections.defaultdict(list)
    for it, v in pairs:
        out[it].append(v)
    return out


def direction_agreement(fc, jc, cond, item_ids, boot=BOOT):
    per = _by_item((i, j["dir"] == fc[(m, c, i)]["side"])
                   for (m, c, i), j in jc.items()
                   if c == cond and j["dir"] != 0 and fc.get((m, c, i))
                   and fc[(m, c, i)]["side"] != 0)

    def cells_for(items):
        return [v for it in items for v in per.get(it, ())]

    def share(items):
        v = cells_for(items)
        return (sum(v) / len(v)) if v else None

    base = cells_for(item_ids)
    lo, hi = _boot_items(share, list(item_ids), n=boot)
    return {"share": (sum(base) / len(base)) if base else None, "n": len(base),
            "lo": lo, "hi": hi}


def _ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2.0 + 1
        i = j + 1
    return ranks


def spearman(xs, ys):
    if len(xs) < 3:
        return None
    rx, ry = _ranks(xs), _ranks(ys)
    mx, my = st.mean(rx), st.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return num / den if den else None


def rank_agreement(fc, jc, cond, item_ids, models=None, boot=BOOT):
    per = _by_item((i, (fc[(m, c, i)]["mean"], j["mean"]))
                   for (m, c, i), j in jc.items()
                   if c == cond and (models is None or m in models) and fc.get((m, c, i)))

    def pairs(items):
        vals = [v for it in items for v in per.get(it, ())]
        return [x for x, _y in vals], [y for _x, y in vals]

    xs, ys = pairs(item_ids)
    lo, hi = _boot_items(lambda s: spearman(*pairs(s)), list(item_ids), n=boot)
    return {"rho": spearman(xs, ys), "n": len(xs), "lo": lo, "hi": hi}


def commitment(scores, cond):
    recs = [s for (m, c, _i), v in scores.items() if c == cond for s in v]
    at3 = sum(1 for s in recs if s == 3)
    return {"records": len(recs), "at_3": at3, "share_at_3": (at3 / len(recs)) if recs else None}


def positions(fc, jc, bank, models, pairs_keep=None):
    pair_of = {it["id"]: it["pair_no"] for it in bank["items"]}
    out = {}
    for m in models:
        row = {}
        for c in CONDITIONS:
            for path, cells, mid in (("fc", fc, 1.5), ("judged", jc, 3.0)):
                by_pair = collections.defaultdict(list)
                for (mm, cc, i), v in cells.items():
                    if mm == m and cc == c and (pairs_keep is None or pair_of[i] in pairs_keep):
                        by_pair[pair_of[i]].append(v["mean"])
                vals = [st.mean(v) - mid for v in by_pair.values() if len(v) == 2]
                row[(path, c)] = st.mean(vals) if vals else None
        comp = {}
        for path in ("fc", "judged"):
            n, a = row.get((path, "N")), row.get((path, "A"))
            comp[path] = None if n is None or a is None else abs(a) < abs(n)
        out[m] = {"pos": {"%s_%s" % k: v for k, v in row.items()}, "compressed": comp}
    return out


def item_instruction_agreement(fc, jc, item_ids, boot=BOOT):
    raw = []
    for (m, c, i), jn in jc.items():
        if c != "N":
            continue
        ja, fn, fa = jc.get((m, "A", i)), fc.get((m, "N", i)), fc.get((m, "A", i))
        if not (ja and fn and fa):
            continue
        dj, df = ja["mean"] - jn["mean"], fa["mean"] - fn["mean"]
        if dj == 0 or df == 0:
            continue
        raw.append((i, (dj > 0) == (df > 0)))
    per = _by_item(raw)

    def cells_for(items):
        return [v for it in items for v in per.get(it, ())]

    def share(items):
        v = cells_for(items)
        return (sum(v) / len(v)) if v else None

    base = cells_for(item_ids)
    lo, hi = _boot_items(share, list(item_ids), n=boot)
    return {"share": (sum(base) / len(base)) if base else None, "n": len(base), "lo": lo, "hi": hi}


def judged_self_agreement(jc):
    agree = total = 0
    for v in jc.values():
        s = v["samples"]
        if len(s) >= 2 and s[0] != 3 and s[1] != 3:
            total += 1
            agree += (s[0] > 3) == (s[1] > 3)
    return (agree / total if total else None), total


def entering_share(fc, jc, cond):
    cells = [k for k in jc if k[1] == cond]
    entering = [k for k in cells if jc[k]["dir"] != 0 and fc.get(k) and fc[k]["side"] != 0]
    return (len(entering) / len(cells)) if cells else None


# ---- the whole analysis ---------------------------------------------------------------------

def analyse(judged_recs, fc_sheets, bank, models, boot=BOOT):
    item_ids = [it["id"] for it in bank["items"]]
    undisputed_pairs = {it["pair_no"] for it in bank["items"]} - set(PA.DISPUTED_PAIRS)
    undisputed_items = [it["id"] for it in bank["items"] if it["pair_no"] in undisputed_pairs]
    fc = fc_cells(fc_sheets, bank, models)
    scores, excluded, records = judged_scores(judged_recs)
    jc = judged_cells(scores)

    res = {"models": models, "records": {"%s|%s" % k: v for k, v in records.items()},
           "excluded": {"%s|%s|%s" % k: v for k, v in excluded.items()},
           "fc_sheets": collections.Counter("%s|%s" % (r["model"], r["condition"])
                                            for r in fc_sheets
                                            if r["model"] in models and r["condition"] in CONDITIONS),
           "measures": {}}
    for c in CONDITIONS:
        res["measures"][c] = {
            "direction": direction_agreement(fc, jc, c, item_ids, boot),
            "rank": rank_agreement(fc, jc, c, item_ids, boot=boot),
            "commitment": commitment(scores, c),
            "entering_M1": entering_share(fc, jc, c),
            "per_model": {m: {
                "rho": rank_agreement(fc, jc, c, item_ids, models={m}, boot=0)["rho"],
                "commitment": commitment({k: v for k, v in scores.items() if k[0] == m}, c),
                "direction": direction_agreement(
                    fc, {k: v for k, v in jc.items() if k[0] == m}, c, item_ids, boot=0)}
                for m in models},
        }
    res["positions"] = positions(fc, jc, bank, models)
    res["item_instruction"] = item_instruction_agreement(fc, jc, item_ids, boot)
    js, jn = judged_self_agreement(jc)
    fs, fn = fc_self_agreement({k: v for k, v in fc.items() if k[1] == "N"})
    fsa, fna = fc_self_agreement({k: v for k, v in fc.items() if k[1] == "A"})
    res["own_agreement"] = {"judged": js, "judged_n": jn, "fc_N": fs, "fc_N_pairs": fn,
                            "fc_A": fsa, "fc_A_pairs": fna}

    # Divergent cells, in full (P5 of the 2026-09-12 file: reported, not curated).
    text = {it["id"]: it["text"] for it in bank["items"]}
    frame = {it["id"]: it["frame"] for it in bank["items"]}
    res["divergent_N"] = sorted(
        [{"model": m, "item": i, "frame": frame[i], "fc_mean": round(fc[(m, c, i)]["mean"], 2),
          "judged": round(v["mean"], 2), "text": text[i]}
         for (m, c, i), v in jc.items()
         if c == "N" and v["dir"] != 0 and fc.get((m, c, i)) and fc[(m, c, i)]["side"] != 0
         and v["dir"] != fc[(m, c, i)]["side"]], key=lambda d: (d["item"], d["model"]))

    sens = {}
    variants = ["judge:%s" % j for j in _SP.JUDGE_PANEL] + ["no-own-vendor", "window"]
    for var in variants:
        sc, _e, _r = judged_scores(judged_recs, var)
        jv = judged_cells(sc)
        sens[var] = {c: {"direction": direction_agreement(fc, jv, c, item_ids, 0)["share"],
                         "rho": rank_agreement(fc, jv, c, item_ids, boot=0)["rho"],
                         "share_at_3": commitment(sc, c)["share_at_3"]} for c in CONDITIONS}
    sens["undisputed"] = {c: {"direction": direction_agreement(fc, jc, c, undisputed_items,
                                                               0)["share"],
                              "rho": rank_agreement(fc, jc, c, undisputed_items, boot=0)["rho"]}
                          for c in CONDITIONS}
    res["sensitivity"] = sens
    res["verdicts"] = verdicts(res)
    return res


def verdicts(res):
    mN, mA = res["measures"]["N"], res["measures"]["A"]
    own = res["own_agreement"]
    dN = mN["direction"]
    out = {}
    if own["judged"] is None or own["judged"] < 0.70 or (mN["entering_M1"] or 0) < 0.30:
        out["rule"] = "UNREADABLE: the judged path does not commit or replicate enough"
    elif dN["share"] is not None and dN["lo"] is not None and dN["lo"] > 0.5 \
            and dN["share"] >= 0.75:
        out["rule"] = "AGREE on direction under N"
    elif dN["lo"] is not None and dN["lo"] <= 0.5 <= dN["hi"]:
        out["rule"] = "DO NOT TRACK: the N interval contains 0.5"
    elif dN["hi"] is not None and dN["hi"] < 0.5:
        out["rule"] = "INVERTED under N"
    else:
        out["rule"] = "MIXED: direction agreement above chance but below 0.75"
    comp = [m for m, p in res["positions"].items()
            if p["compressed"]["fc"] and p["compressed"]["judged"]]
    ii = res["item_instruction"]
    out["instruction"] = ("AGREE on the instruction" if len(comp) >= 4 and ii["lo"] is not None
                          and ii["lo"] > 0.5 else "DO NOT AGREE on the instruction")
    ceiling = min(x for x in (own["judged"], own["fc_N"]) if x is not None) \
        if (own["judged"] is not None or own["fc_N"] is not None) else None
    out["ceiling"] = ceiling
    out["within_0.10_of_ceiling"] = (ceiling is not None and dN["share"] is not None
                                     and dN["share"] >= ceiling - 0.10)
    preds = []
    preds.append(("P1", "DA_N >= 0.75, CI excludes 0.5",
                  dN["share"] is not None and dN["share"] >= 0.75 and (dN["lo"] or 0) > 0.5))
    preds.append(("P2a", ">= 80% of eligible A records at exactly 3",
                  (mA["commitment"]["share_at_3"] or 0) >= 0.80))
    preds.append(("P2b", "< 60% of eligible N records at exactly 3",
                  mN["commitment"]["share_at_3"] is not None
                  and mN["commitment"]["share_at_3"] < 0.60))
    r = mN["rank"]
    preds.append(("P3", "rho_N >= 0.30, CI excludes zero",
                  r["rho"] is not None and r["rho"] >= 0.30 and (r["lo"] or 0) > 0))
    preds.append(("P4", "A compresses position in both paths on >= 4 of 6 models",
                  len(comp) >= 4))
    preds.append(("P5", "DA_N below the forced-choice path's own between-order side agreement",
                  dN["share"] is not None and own["fc_N"] is not None
                  and dN["share"] < own["fc_N"]))
    out["predictions"] = [{"id": i, "claim": c, "verdict": "CONFIRMED" if ok else "REFUTED"}
                          for i, c, ok in preds]
    out["compressed_both"] = comp
    return out


def _f(x, d=3):
    return "-" if x is None else ("%.*f" % (d, x))


def render(res):
    print("same items, both paths -- %d models" % len(res["models"]))
    print("")
    print("| condition | direction agreement [95%] (cells) | Spearman [95%] (cells) | "
          "judged at 3 | cells entering M1 |")
    print("|---|---|---|---|---|")
    for c in CONDITIONS:
        m = res["measures"][c]
        d, r, k = m["direction"], m["rank"], m["commitment"]
        print("| %s | %s [%s, %s] (%d) | %s [%s, %s] (%d) | %d of %d (%s) | %s |" % (
            c, _f(d["share"]), _f(d["lo"]), _f(d["hi"]), d["n"], _f(r["rho"]), _f(r["lo"]),
            _f(r["hi"]), r["n"], k["at_3"], k["records"], _f(k["share_at_3"]),
            _f(m["entering_M1"])))
    print("")
    print("| model | FC sheets N/A | judged records N/A | at 3 N | at 3 A | DA N | rho N | "
          "pos FC N -> A | pos judged N -> A | compressed FC / judged |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for mdl in res["models"]:
        pn, pa = res["measures"]["N"]["per_model"][mdl], res["measures"]["A"]["per_model"][mdl]
        p = res["positions"][mdl]
        print("| `%s` | %s/%s | %s/%s | %s | %s | %s | %s | %s -> %s | %s -> %s | %s / %s |" % (
            mdl, res["fc_sheets"].get(mdl + "|N", 0), res["fc_sheets"].get(mdl + "|A", 0),
            pn["commitment"]["records"], pa["commitment"]["records"],
            _f(pn["commitment"]["share_at_3"], 2), _f(pa["commitment"]["share_at_3"], 2),
            _f(pn["direction"]["share"], 2), _f(pn["rho"], 2),
            _f(p["pos"]["fc_N"]), _f(p["pos"]["fc_A"]),
            _f(p["pos"]["judged_N"]), _f(p["pos"]["judged_A"]),
            p["compressed"]["fc"], p["compressed"]["judged"]))
    ii = res["item_instruction"]
    own = res["own_agreement"]
    print("")
    print("per-item A - N sign agreement across paths: %s [%s, %s] over %d cells"
          % (_f(ii["share"]), _f(ii["lo"]), _f(ii["hi"]), ii["n"]))
    print("own agreement: judged sample-vs-sample %s (%d cells); forced choice order-vs-order "
          "N %s (%d pairs), A %s (%d pairs)" % (_f(own["judged"]), own["judged_n"],
                                               _f(own["fc_N"]), own["fc_N_pairs"],
                                               _f(own["fc_A"]), own["fc_A_pairs"]))
    print("")
    print("exclusions: %s" % (json.dumps(res["excluded"], sort_keys=True) or "none"))
    print("")
    print("| sensitivity | DA N | rho N | at 3 N | DA A | rho A | at 3 A |")
    print("|---|---|---|---|---|---|---|")
    for var, v in res["sensitivity"].items():
        print("| %s | %s | %s | %s | %s | %s | %s |" % (
            var, _f(v["N"]["direction"]), _f(v["N"]["rho"]), _f(v["N"].get("share_at_3")),
            _f(v["A"]["direction"]), _f(v["A"]["rho"]), _f(v["A"].get("share_at_3"))))
    print("")
    print("divergent cells under N (%d), in full:" % len(res["divergent_N"]))
    for d in res["divergent_N"]:
        print("  item %2d %-8s %-32s fc %.2f  judged %.2f  %s" % (
            d["item"], d["frame"], d["model"], d["fc_mean"], d["judged"], d["text"][:70]))
    v = res["verdicts"]
    print("")
    print("interpretation rule: %s; %s" % (v["rule"], v["instruction"]))
    print("ceiling (lower own agreement) %s; DA_N within 0.10 of it: %s"
          % (_f(v["ceiling"]), v["within_0.10_of_ceiling"]))
    for p in v["predictions"]:
        print("%-4s %-9s %s" % (p["id"], p["verdict"], p["claim"]))


def load_inputs(run=RUN, wave=WAVE, models=None):
    import run_both_paths as RBP
    models = models or [m for m, _p in RBP.ROSTER]
    bank = PA.load_bank()
    wave_dir = str(_SP.run_path(wave))
    sheets = PA.load_records(wave_dir)
    scored = os.path.join(str(_SP.run_path(run)), "scored")
    return judged_records(scored), sheets, bank, models


def selftest():
    fails = []

    def check(label, cond):
        print("  [%s] %s" % ("ok" if cond else "FAIL", label))
        if not cond:
            fails.append(label)

    bank = PA.load_bank()
    rng = random.Random(11)
    models = ["a/one", "b/two", "c/three"]
    # A world where each model has a skeptic score per item; FC answers track it, judged
    # scores track it under N and collapse to 3 under A.
    truth = {(m, it["id"]): rng.choice((0.5, 1, 2, 2.5)) for m in models for it in bank["items"]}
    sheets, judged = [], []
    for m in models:
        for c in CONDITIONS:
            for o in (11, 22, 33):
                for _ in range(5):
                    ans = {}
                    for it in bank["items"]:
                        s = truth[(m, it["id"])]
                        if c == "A":
                            s = 1.5 + (s - 1.5) * 0.5
                        s = max(0, min(3, round(s + rng.choice((-0.5, 0, 0, 0.5)))))
                        ans[it["id"]] = s if it["frame"] == "critic" else 3 - s
                    sheets.append({"model": m, "condition": c, "shuffle_seed": o,
                                   "answers": ans})
            for it in bank["items"]:
                for k in range(2):
                    s = truth[(m, it["id"])]
                    j = 3 if c == "A" else (4.5 if s > 1.5 else 1.5)
                    judged.append({"model": m, "condition": c, "item_id": it["id"],
                                   "sample_idx": k, "ok": True, "response_text": "An answer.",
                                   "score_classifier": j, "provider_pinned": "X",
                                   "provider": "X", "tokens_out": 100, "max_tokens": 16384,
                                   "score_classifier_judges": [
                                       {"judge": jj, "score": j} for jj in _SP.JUDGE_PANEL]})
    res = analyse(judged, sheets, bank, models, boot=300)
    mN, mA = res["measures"]["N"], res["measures"]["A"]
    check("direction agreement is perfect when the judge reads the same stance",
          mN["direction"]["share"] == 1.0)
    check("Spearman is high under N", mN["rank"]["rho"] > 0.7)
    check("A pinned at 3: commitment share 1.0", mA["commitment"]["share_at_3"] == 1.0)
    check("A pinned at 3: no A cell enters M1", mA["direction"]["n"] == 0)
    check("compression detected in both paths on every model",
          len(res["verdicts"]["compressed_both"]) == 3)
    check("judged self-agreement 1.0", res["own_agreement"]["judged"] == 1.0)
    check("the rule reads AGREE", res["verdicts"]["rule"].startswith("AGREE"))
    # Inversion: flip the judged direction under N.
    flipped = [dict(r, score_classifier=6 - r["score_classifier"]) if r["condition"] == "N"
               else r for r in judged]
    res2 = analyse(flipped, sheets, bank, models, boot=300)
    check("an inverted judge reads INVERTED", res2["verdicts"]["rule"].startswith("INVERTED"))
    # Eligibility: an empty scored record is excluded, not averaged.
    bad = judged + [{"model": "a/one", "condition": "N", "item_id": 1, "sample_idx": 9,
                     "ok": True, "response_text": "", "score_classifier": 1.0,
                     "provider_pinned": "X", "provider": "X"}]
    sc, ex, _r = judged_scores(bad)
    check("an empty-but-scored record is excluded and counted",
          len(sc[("a/one", "N", 1)]) == 2 and ex[("a/one", "N", "empty-or-missing-response")] == 1)
    offpin = [dict(judged[0], provider="Y")]
    sc2, ex2, _r2 = judged_scores(offpin)
    check("an off-pin record is excluded", not sc2 and sum(ex2.values()) == 1)
    check("spearman of a monotone pair is 1", abs(spearman([1, 2, 3, 4], [2, 4, 6, 9]) - 1) < 1e-9)
    check("spearman handles ties", spearman([1, 1, 2, 3], [1, 2, 2, 3]) is not None)
    print("")
    print("  %d check(s) failed" % len(fails))
    return 1 if fails else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", default=RUN)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--boot", type=int, default=BOOT)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    judged, sheets, bank, models = load_inputs(a.run)
    if not judged:
        print("no scored free-text records for %s -- NOT APPLICABLE, nothing computed" % a.run)
        return 2
    res = analyse(judged, sheets, bank, models, boot=a.boot)
    if a.json:
        print(json.dumps(res, indent=1, sort_keys=True, default=str))
    else:
        render(res)
    return 0


if __name__ == "__main__":
    sys.exit(main())
