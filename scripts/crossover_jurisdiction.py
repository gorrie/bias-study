#!/usr/bin/env python3
"""Does a model go easy on ITS OWN state's items, or is some topic hard for everyone?

THE QUESTION THIS SETTLES, AND THE ONE IT CANNOT
------------------------------------------------
`FINDINGS-2026-09-17-battery.md` §3 reports the study's only live signal pointing at the
author's thesis: under the balance instruction, china-state items lose a strong answer 36.5% of
the time against 9.5% for British, European and Indian ones. A four-fold gradient, paired sign
test p = 0.007, with the placebo control flat.

**That gradient has two completely different explanations and §3 cannot tell them apart.**

  LOYALTY   a model handles its own licensing state's items more gently than other states'.
            This is the author's thesis and it predicts an INTERACTION: US-vendor models
            softer on US items, Chinese-vendor models softer on China items.
  TOPIC     China is simply a more sensitive subject for every vendor, whoever built it.
            This predicts a MAIN EFFECT: every model hedges on China, including Chinese ones.

Only a **crossover** separates them -- vendor jurisdiction x item jurisdiction -- and nothing in
this study performs one. The factions bank does not either: its slot is sector, so it cannot
speak to jurisdiction at all. This script performs it on the corpus that already exists.

**It is EXPLORATORY and is labelled so in every output.** It was written after the data was
seen, it is in no pre-registration, and the corpus gives it **one mirrored pair per state**.
Nothing it prints is a result. What it is for is deciding whether the jurisdiction line of
inquiry is worth instrumenting properly -- which is a decision that has to be made on
something, and this is the only something available.

The existing evidence points at TOPIC, not loyalty: §3 records that Chinese-vendor models are
among the *most* critical of china-state items at baseline. If that survives here, the author's
thesis in its national form is in trouble and the sector form is the one to build.

    python scripts/crossover_jurisdiction.py                     # the wave
    python scripts/crossover_jurisdiction.py --run <dir> --perm 20000

Exit 0 computed, 2 NOT APPLICABLE (no usable cells).
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
import studypaths as _SP  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, HERE)

#: Vendor -> the state that licenses it. The same rule the factions prereg fixes, imported
#: rather than restated where possible so the two cannot drift.
US = {"openai", "anthropic", "google", "meta-llama", "microsoft", "x-ai"}
CN = {"deepseek", "qwen", "z-ai", "moonshotai"}

#: Item cluster -> the state it is about, from the bank's own `ratchet` field. `generic` is the
#: reference: 10 of the 16 pairs, about no particular state.
HOME = {"united-states": "US", "china-state": "CN"}


def vendor_jurisdiction(model):
    import refusal_table as R
    v = R.vendor_of(model)
    if v in US:
        return "US"
    if v in CN:
        return "CN"
    return "other"


def load_bank():
    bank = json.load(io.open(os.path.join(STUDY, "data", "ratchet-battery.json"),
                             encoding="utf-8"))
    return {i["id"]: i for i in bank["items"]}


def cell_positions(run_dir, items, condition):
    """-> {(model, pair_no): position}, from each cell's MODAL answer across its runs.

    Position is (critic agreement - defender agreement) / 2 on the 0-3 scale, so positive is
    institution-skeptical, exactly as `position_analysis` defines it. Modal rather than mean
    because a mean over an ordinal forced choice is not a position anyone held.
    """
    raw = collections.defaultdict(list)
    for path in sorted(glob.glob(os.path.join(run_dir, "*.jsonl"))):
        for line in io.open(path, encoding="utf-8", errors="replace"):
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if not _SP.is_run_record(r) or not r.get("valid"):
                continue
            if r.get("condition") != condition:
                continue
            vals = [a["position"] for a in r["answers"]]
            if len(set(vals)) == 1:                 # degenerate sheet, no position
                continue
            raw[r["model"]].append({a["q"]: a["position"] for a in r["answers"]})

    out = {}
    for model, runs in raw.items():
        modal = {}
        for q in {q for run in runs for q in run}:
            got = [run[q] for run in runs if q in run]
            if got:
                modal[q] = collections.Counter(got).most_common(1)[0][0]
        by_pair = collections.defaultdict(dict)
        for q, v in modal.items():
            it = items.get(q)
            if it:
                by_pair[it["pair_no"]][it["frame"]] = v
        for pair, halves in by_pair.items():
            if "critic" in halves and "defender" in halves:
                out[(model, pair)] = (halves["critic"] - halves["defender"]) / 2.0
    return out


def per_model_gap(pos, items):
    """-> {model: (us_position, cn_position, gap)}. gap = US items minus China items."""
    pair_cluster = {}
    for it in items.values():
        pair_cluster[it["pair_no"]] = it.get("ratchet")
    got = collections.defaultdict(dict)
    for (model, pair), v in pos.items():
        c = HOME.get(pair_cluster.get(pair))
        if c:
            got[model][c] = v
    return {m: (d["US"], d["CN"], d["US"] - d["CN"])
            for m, d in got.items() if "US" in d and "CN" in d}


def permutation_p(gaps, groups, draws, seed=11):
    """Two-sided permutation test on the vendor label. -> (observed diff, p, n_us, n_cn)."""
    us = [gaps[m] for m in gaps if groups[m] == "US"]
    cn = [gaps[m] for m in gaps if groups[m] == "CN"]
    if not us or not cn:
        return None, None, len(us), len(cn)
    obs = sum(us) / len(us) - sum(cn) / len(cn)
    pool = us + cn
    k, rng = len(us), random.Random(seed)
    hits = 0
    for _ in range(draws):
        rng.shuffle(pool)
        a, b = pool[:k], pool[k:]
        if abs(sum(a) / len(a) - sum(b) / len(b)) >= abs(obs) - 1e-12:
            hits += 1
    return obs, (hits + 1) / float(draws + 1), len(us), len(cn)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run", default="2026-09-16-ratchet-v3-wave")
    ap.add_argument("--condition", default="N")
    ap.add_argument("--perm", type=int, default=20000)
    a = ap.parse_args(argv)

    run_dir = a.run if os.path.isdir(a.run) else os.path.join(STUDY, "runs", a.run)
    if not os.path.isdir(run_dir):
        print("no such run directory: %s" % run_dir)
        return 2

    items = load_bank()
    clusters = collections.Counter(i.get("ratchet") for i in items.values())
    pos = cell_positions(run_dir, items, a.condition)
    gaps = per_model_gap(pos, items)

    print("EXPLORATORY -- NOT PRE-REGISTERED, WRITTEN AFTER THE DATA WAS SEEN.")
    print("Nothing below is a result. It decides whether jurisdiction is worth instrumenting.")
    print("")
    print("THE CROSSOVER: does a model go easy on its OWN state's items?")
    print("")
    print("  run        %s, condition %s" % (os.path.basename(run_dir), a.condition))
    print("  items      %d pair(s) tagged united-states, %d tagged china-state, %d generic"
          % (clusters.get("united-states", 0) // 2, clusters.get("china-state", 0) // 2,
             clusters.get("generic", 0) // 2))
    print("  position   (critic - defender) / 2 on modal answers; + is institution-skeptical")
    print("")

    if not gaps:
        print("NOT APPLICABLE -- no model resolves both a united-states and a china-state pair.")
        return 2

    groups = {m: vendor_jurisdiction(m) for m in gaps}
    print("  %-46s %6s %6s %7s" % ("model (vendor jurisdiction)", "US", "CN", "US-CN"))
    for m in sorted(gaps, key=lambda m: (groups[m], m)):
        u, c, g = gaps[m]
        print("  %-40s %-5s %6.2f %6.2f %+7.2f" % (m[:40], groups[m], u, c, g))

    obs, p, n_us, n_cn = permutation_p({m: gaps[m][2] for m in gaps}, groups, a.perm)
    print("")
    print("  LOYALTY predicts this gap is MORE POSITIVE for CN-vendor models than US-vendor")
    print("  ones: each softer (less skeptical) on its own state. TOPIC predicts no difference.")
    print("")
    if obs is None:
        print("  Cannot test: %d US-vendor and %d CN-vendor model(s) resolve both pairs."
              % (n_us, n_cn))
        return 0
    us_mean = sum(gaps[m][2] for m in gaps if groups[m] == "US") / n_us
    cn_mean = sum(gaps[m][2] for m in gaps if groups[m] == "CN") / n_cn
    print("  US-vendor models  mean US-CN gap  %+.3f   (n = %d)" % (us_mean, n_us))
    print("  CN-vendor models  mean US-CN gap  %+.3f   (n = %d)" % (cn_mean, n_cn))
    print("  difference %+.3f, permutation p = %.4f over %d draws" % (obs, p, a.perm))
    print("")
    print("  Sign of the difference: %s" % (
        "CN-vendor models are RELATIVELY softer on China -- the direction loyalty predicts"
        if obs < 0 else
        "CN-vendor models are relatively HARDER on China -- the OPPOSITE of loyalty"))
    print("")
    print("  ONE MIRRORED PAIR PER STATE. Each model's gap rests on four answers. This cannot")
    print("  carry a conclusion at any p-value, and the p-value is printed so the reader can")
    print("  see it is not being hidden, not so it can be quoted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
