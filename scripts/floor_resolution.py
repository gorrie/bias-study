#!/usr/bin/env python3
"""What a modal-vs-modal floor can actually resolve, and which factor is bigger ON THE SAME MODELS.

TWO DEFECTS IN THE COMPARISON THIS PROJECT HAS BEEN MAKING
---------------------------------------------------------
The floor table compares factors by pairing each cell's MODAL answer sheet -- the per-item
majority across that cell's runs. Two things about that were never measured, and both bear
directly on §3's central comparison.

**1. The modal has its own sampling error, and nothing estimated it.** A five-run modal is a
statistic, not a fixed quantity: draw five more runs from the same cell and the modal moves. If
that movement is p90 6, then a measured effect of p90 7 is almost entirely the estimator, and
every floor in the table sits at or under the resolution of the instrument that produced it.
`--modal-noise` bootstraps it: resample a cell's runs with replacement twice, take the modal of
each, and count the side-flips between two modals of the SAME cell. That is the floor under the
floors.

**2. The two arms are different pools of models.** The manipulation arm has 25 models, the
one-sitting order arm 29, and 24 are common. Comparing p90s across differently-composed pools
lets composition masquerade as effect -- the exact defect this paper convicts other studies of
committing with net aggregates. `--paired` restricts to the 24 models present in both and takes
the difference WITHIN each model, which is the only form of the question that has an answer.

Neither of these replaces the floor table. They say what it can and cannot resolve.

    python scripts/floor_resolution.py --modal-noise
    python scripts/floor_resolution.py --paired
    python scripts/floor_resolution.py --json
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import random
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import floor_table as F  # noqa: E402

#: Resamples per cell. 2000 because the ENDPOINT p90 is not converged below it, and the paper
#: uses that number as a denominator.
#:
#: Measured 2026-09-07, same seed, same 110 cells, varying only this constant:
#:
#:     boot    200   300   400   800   1600   2000
#:     side     3     3     3     3     3      3
#:     endpoint 8     8   **7**   8     8      8
#:
#: So the endpoint p90 sits on a 7/8 boundary and 400 -- the old default -- is the one count in
#: that range that lands on 7. This was found because the public mirror regenerated the cache
#: from its own scrubbed runs and got 7 where the private cache said 8, which is exactly the
#: disagreement a mirror is supposed to surface. Nothing was wrong with either run; a discrete
#: percentile of a bootstrap distribution is simply not stable at 400 resamples.
#:
#: The side-flip floor (3), the max (30/39) and the ten flagged-unstable cells are IDENTICAL at
#: every count tested, so only the endpoint row was ever at risk. Do not lower this to make a
#: run faster: the endpoint floor is what the ablation arm's effect is judged against, and the
#: difference between 7 and 8 is the difference between an effect clearing its floor and not.
#: THE VENDOR OF A LOCAL BUILD IS NOT "local".
#:
#: `vendor()` returned the literal string "local" for every model name without a slash, which
#: pooled gemma2, llama3.1, phi4, qwen2.5 and mistral -- FIVE different vendors -- into one
#: pseudo-vendor. Those ten CROSS-vendor pairs then counted as SAME-vendor and became the
#: published "same vendor p90 10" figure and a table row reading "local, 2024 generation" as
#: though it were a house.
#:
#: It flattered the conclusion. With real vendors, same-vendor is D 5/9 and P 3/8 against
#: different-vendor D 5/14 and P 5/18 -- so "the medians are equal" holds under D and NOT under
#: P, and the tail gap is wider than was reported. Vendors cluster more than the bug allowed.
#:
#: MODULE LEVEL, not nested inside `between_vs_within()`. The fix was first made inside that
#: closure, where `FR.vendor` does not exist -- so the repair for a bug that had already
#: published a wrong number was itself unreachable from a test. A correction that cannot be
#: pinned is a correction that can be undone silently.
LOCAL_VENDOR = {
    "gemma2": "google", "gemma": "google",
    "llama3.1": "meta-llama", "llama3.2": "meta-llama", "llama": "meta-llama",
    "phi4": "microsoft", "phi": "microsoft",
    "qwen2.5": "qwen", "qwen3": "qwen", "qwen": "qwen",
    "mistral": "mistralai",
    "deepseek-r1": "deepseek", "deepseek": "deepseek",
}


def vendor(m):
    """The vendor family a model name belongs to.

    A slash means the name already carries its vendor (OpenRouter's `vendor/model`). A bare
    name is a local Ollama tag and has to be mapped -- longest prefix first, so `qwen2.5`
    resolves before `qwen` and `llama3.1` before `llama`.

    An unrecognised bare name returns `unmapped:<stem>` rather than a plausible-looking
    default. That is the whole lesson of the bug above: a wrong answer shaped like an answer
    survives review, and a visibly unmapped key does not.
    """
    if "/" in m:
        return m.split("/")[0]
    stem = m.split(":")[0].lower()
    for prefix in sorted(LOCAL_VENDOR, key=len, reverse=True):
        if stem.startswith(prefix):
            return LOCAL_VENDOR[prefix]
    return "unmapped:" + stem


def _cached_modal_noise():
    """The cached estimator floor, or None. Read rather than recomputed: it is 2000 resamples
    across 110 cells, and every caller here only needs the two summary numbers."""
    import json as _json
    path = os.path.join(STUDY, "data", "modal-noise.json")
    if not os.path.exists(path):
        return None
    try:
        rec = _json.load(open(path, encoding="utf-8"))
    except ValueError:
        return None
    if rec.get("median") is None or rec.get("p90") is None:
        return None
    return rec


BOOT = 2000
SEED = 20260906
WAVE = "runs/*-wave/*.jsonl"
ORDERS = "runs/*-wave-orders/*.jsonl"


def p90(v):
    """The project's nearest-rank convention, in one place.

    `floor_table.summarise` uses v[int(0.9*n)-1] and `power.pctile` uses v[int(q*n)]; at n=20
    they disagree (18 vs 19) and at n=25 the manipulation p90 is 7 under one and 8 under the
    other. Neither file said which it used. This module states its own and uses it throughout,
    so its numbers are internally comparable whatever the table does.
    """
    v = sorted(v)
    if not v:
        return None
    return v[int(0.9 * len(v)) - 1] if len(v) >= 10 else max(v)


def wave_cells(condition=None):
    """(model, condition) -> list of answer sheets, from the wave at n=5."""
    got = F.load(WAVE, condition=condition,
                 key=lambda r: (r["model"], r["condition"]), dedupe_by_seed=True)
    return {k: v for k, v in got.items() if len(v) >= 4}


def modal_noise(cells, boot=BOOT, seed=SEED):
    """Distance between two independent bootstrap modals OF THE SAME CELL, in both statistics.

    This is the estimator's own spread. Both halves come from one cell under one condition, so
    every item that differs differs because the modal moved, not because anything did.

    BOTH STATISTICS, because their floors differ by a factor of nearly three and conflating
    them was a defect this module shipped for an hour. The first version measured side-flips
    only and the floor row printed those same numbers in the endpoint column. They are not the
    same: **side-flip noise is p90 3, endpoint noise is p90 8.** An endpoint effect judged
    against 3 would be called real at values that are pure estimator -- and the first result to
    come out of the ablation arm is an endpoint effect, so the faked column would have inflated
    it in the same hour it was written.
    """
    rng = random.Random(seed)
    per_cell = {}
    allside, allend = [], []
    for key, runs in sorted(cells.items()):
        n = len(runs)
        sides, ends = [], []
        for _ in range(boot):
            a = F.modal([runs[rng.randrange(n)] for _ in range(n)])
            b = F.modal([runs[rng.randrange(n)] for _ in range(n)])
            s, e = F.both_stats(a, b)
            sides.append(s)
            ends.append(e)
        per_cell[key] = {"n_runs": n,
                         "median": int(st.median(sides)), "p90": p90(sides), "max": max(sides),
                         "endpoint_median": int(st.median(ends)), "endpoint_p90": p90(ends),
                         "endpoint_max": max(ends)}
        allside += sides
        allend += ends
    return {"cells": len(per_cell),
            "median": int(st.median(allside)), "p90": p90(allside), "max": max(allside),
            "endpoint_median": int(st.median(allend)), "endpoint_p90": p90(allend),
            "endpoint_max": max(allend),
            "per_cell": per_cell}


def between_vs_within(condition="D", min_runs=4):
    """Do models differ from each other more than they differ from themselves?

    THE MEASUREMENT THE STUDY NEEDED AND NEVER HAD. Every floor here asks how far a model moves
    when something nuisance changes. None asked whether the instrument can separate two models
    at all -- and if between-model distance were comparable to within-model noise, every
    per-model number in the paper would be measuring the questionnaire.

    It is not: between-model median is 5 side-flips against a within-model median of 1-2, and
    the between-model p90 (14-18) is three to four times the within-model p90. Model identity
    is the largest term in this study, larger than the manipulation, the item order or the
    estimator.

    Also splits same-vendor from different-vendor pairs, which answers the house-style question
    -- and the answer is that the MEDIANS ARE EQUAL. Two models from one lab differ about as
    much as two from different labs; vendors separate only in the tail. Where they do differ
    sharply is internal consistency: moonshot's line agrees with itself within 2 items, x-ai's
    disagrees by 10-11.
    """
    raw = F.load(WAVE, key=lambda r: (r["model"], r["condition"]), dedupe_by_seed=True)
    cells = {k: v for k, v in raw.items() if len(v) >= min_runs}
    models = sorted(m for (m, c) in cells if c == condition)
    modal = {m: F.modal(cells[(m, condition)]) for m in models}

    within = []
    for m in models:
        r = cells[(m, condition)]
        within += [F.both_stats(r[i], r[j])[0]
                   for i in range(len(r)) for j in range(i + 1, len(r))]

    between, same, diff = [], [], []
    per_vendor = collections.defaultdict(list)
    for i in range(len(models)):
        for j in range(i + 1, len(models)):
            d = F.both_stats(modal[models[i]], modal[models[j]])[0]
            between.append(d)
            if vendor(models[i]) == vendor(models[j]):
                same.append(d)
                per_vendor[vendor(models[i])].append(d)
            else:
                diff.append(d)

    def summ(v):
        return {"n": len(v), "median": int(st.median(v)) if v else None,
                "p90": p90(v), "max": max(v) if v else None}

    return {"condition": condition, "models": len(models),
            "within": summ(within), "between": summ(between),
            "same_vendor": summ(same), "diff_vendor": summ(diff),
            "per_vendor": {v: summ(d) for v, d in sorted(per_vendor.items()) if len(d) >= 2}}


def order_by_model():
    """model -> median side-flips across its item-order pairs, under the wave protocol."""
    cells = collections.defaultdict(list)
    for pattern in (WAVE, ORDERS):
        got = F.load(pattern, condition="D",
                     key=lambda r: (r["model"], r.get("shuffle_seed")), dedupe_by_seed=True)
        for k, runs in got.items():
            cells[k].extend(runs)
    by = collections.defaultdict(dict)
    for (m, order), runs in sorted(cells.items(),
                                   key=lambda kv: (kv[0][0], kv[0][1] is not None, kv[0][1])):
        by[m][order] = F.modal(runs)
    out = {}
    for m, orders in by.items():
        ks = sorted(orders, key=lambda k: (k is not None, k))
        vals = [F.both_stats(orders[ks[i]], orders[ks[j]])[0]
                for i in range(len(ks)) for j in range(i + 1, len(ks))]
        if vals:
            out[m] = {"pairs": len(vals), "median": int(st.median(vals)), "max": max(vals)}
    return out


def manip_by_model():
    """model -> side-flips between its condition-A modal and its condition-D modal."""
    _pairs, by, _split, _raw = F._condition_pairs(WAVE, dedupe_by_seed=True)
    return {m: F.both_stats(cs["A"], cs["D"])[0]
            for m, cs in by.items() if "A" in cs and "D" in cs}


def paired(boot=BOOT, seed=SEED):
    """The comparison WITHIN each model, on the models that have both measurements."""
    order = order_by_model()
    manip = manip_by_model()
    common = sorted(set(order) & set(manip))
    rows = [{"model": m,
             "order": order[m]["median"],
             "order_max": order[m]["max"],
             "manip": manip[m],
             "diff": order[m]["median"] - manip[m]} for m in common]

    diffs = [r["diff"] for r in rows]
    wins = sum(1 for d in diffs if d > 0)
    ties = sum(1 for d in diffs if d == 0)
    losses = sum(1 for d in diffs if d < 0)

    # Sign test on the models that actually differ. Exact two-sided binomial at p=0.5, which is
    # the right null for "is one factor bigger than the other in this model" with no assumption
    # about the size of the difference.
    k, n = wins, wins + losses
    if n:
        from math import comb
        tail = sum(comb(n, i) for i in range(min(k, n - k) + 1)) / float(2 ** n)
        pval = min(1.0, 2 * tail)
    else:
        pval = 1.0

    rng = random.Random(seed)
    meds = []
    for _ in range(boot):
        s = [diffs[rng.randrange(len(diffs))] for _ in range(len(diffs))]
        meds.append(st.median(s))
    meds.sort()
    lo, hi = meds[int(0.025 * boot)], meds[int(0.975 * boot) - 1]

    return {"models": len(rows), "rows": rows,
            "median_diff": st.median(diffs), "ci95": [lo, hi],
            "order_larger": wins, "tied": ties, "manip_larger": losses,
            "sign_test_p": round(pval, 4)}


#: Cached, because the bootstrap is 2000 resamples x 110 cells and `all_floors()` is called by
#: four gates plus the chart. A floor that costs a minute every time it is read is a floor that
#: gets dropped from the loop; the cache is regenerated by `--write` and carries the corpus
#: fingerprint it was measured over, so a stale one is visible rather than silent.
CACHE = os.path.join(STUDY, "data", "modal-noise.json")


def corpus_signature():
    """How many runs the wave holds, so a cache measured over different data is detectable."""
    cells = wave_cells()
    return {"cells": len(cells), "runs": sum(len(v) for v in cells.values())}


def write_cache(boot=BOOT, seed=SEED):
    cells = wave_cells()
    mn = modal_noise(cells, boot=boot, seed=seed)
    payload = {
        "_note": ("The sampling error of a modal answer sheet: side-flips between two "
                  "bootstrap modals OF THE SAME CELL. Every modal-vs-modal floor in the table "
                  "is measured with this much slack in the estimator alone. Derived -- "
                  "regenerate with scripts/floor_resolution.py --write."),
        "boot": boot,
        "seed": seed,
        "signature": corpus_signature(),
        "median": mn["median"],
        "p90": mn["p90"],
        "max": mn["max"],
        # The endpoint floor is nearly three times the side-flip floor. Cached separately
        # because the floor row printed the side-flip numbers in both columns for an hour.
        "endpoint_median": mn["endpoint_median"],
        "endpoint_p90": mn["endpoint_p90"],
        "endpoint_max": mn["endpoint_max"],
        "cells": mn["cells"],
        "unstable": sorted(
            ("%s %s" % k) for k, v in mn["per_cell"].items() if v["p90"] >= 7),
    }
    io_open = open(CACHE, "w", encoding="utf-8", newline="\n")
    with io_open as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return payload


def load_cache():
    if not os.path.exists(CACHE):
        return None
    try:
        with open(CACHE, encoding="utf-8") as fh:
            return json.load(fh)
    except ValueError:
        return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--modal-noise", action="store_true")
    ap.add_argument("--paired", action="store_true")
    ap.add_argument("--between", action="store_true",
                    help="between-model vs within-model distance, and vendor consistency")
    ap.add_argument("--write", action="store_true",
                    help="measure the modal noise and cache it to data/modal-noise.json")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--boot", type=int, default=BOOT)
    args = ap.parse_args(argv)

    if args.write:
        p = write_cache(boot=args.boot)
        print("wrote %s" % os.path.relpath(CACHE, STUDY))
        print("  modal sampling error: median %d, p90 %d, max %d over %d cell(s)"
              % (p["median"], p["p90"], p["max"], p["cells"]))
        print("  %d cell(s) whose modal is itself unstable at p90 >= 7" % len(p["unstable"]))
        return 0

    out = {}
    if args.between:
        for cond in ("D", "P"):
            r = between_vs_within(cond)
            out.setdefault("between", {})[cond] = r
            if args.json:
                continue
            print("CONDITION %s -- %d models at n>=4" % (cond, r["models"]))
            for lab, key in (("within  model (run vs run)", "within"),
                             ("between models (modal vs modal)", "between")):
                s = r[key]
                print("   %-34s median %2d  p90 %2d  max %2d  n=%d"
                      % (lab, s["median"], s["p90"], s["max"], s["n"]))
            # THE RATIO OF THESE TWO MEDIANS IS NOT A RATIO OF ANYTHING, AND IT WAS PUBLISHED.
            #
            # This printed `between / within` as "2.5x to 5x -- model identity is the larger
            # term". The numerator is a MODAL-vs-MODAL distance and the denominator is a
            # RUN-vs-RUN distance: two different statistics with different noise floors, so
            # their quotient has no interpretation. Those ratios were withdrawn from
            # RESULTS-2026-09-07-between-model-signal.md and this line kept printing them,
            # which is how a retraction comes undone -- the document was corrected and the tool
            # that generates the number was not.
            #
            # The like-for-like denominator for a modal-vs-modal distance is the MODAL's own
            # sampling error, from data/modal-noise.json. It is SMALLER than run-vs-run
            # (median 1, p90 3), so the conclusion survives and gets slightly stronger; the
            # run-vs-run row stays printed above, labelled as the different statistic it is.
            est = _cached_modal_noise()
            if est:
                print("   like-for-like denominator (the modal's OWN sampling error): "
                      "median %d, p90 %d" % (est["median"], est["p90"]))
                print("   between-model median %d against estimator median %d -- model "
                      "identity is the larger term" % (r["between"]["median"], est["median"]))
            else:
                print("   like-for-like denominator unavailable (no data/modal-noise.json): "
                      "run --write first. NOT falling back to the run-vs-run median, which is "
                      "a different statistic.")
            for lab, key in (("same vendor", "same_vendor"),
                             ("different vendor", "diff_vendor")):
                s = r[key]
                print("   %-34s median %2d  p90 %2d  n=%d"
                      % (lab, s["median"], s["p90"], s["n"]))
            print("   per-vendor internal spread (>=2 pairs), least to most:")
            for v, s in sorted(r["per_vendor"].items(), key=lambda kv: kv[1]["median"]):
                print("      %-12s median %2d  max %2d  (%d pairs)"
                      % (v, s["median"], s["max"], s["n"]))
            print("")
        if not args.json:
            return 0

    if args.modal_noise or not (args.paired or args.json or args.between):
        cells = wave_cells()
        mn = modal_noise(cells, boot=args.boot)
        out["modal_noise"] = mn
        if not args.json:
            print("THE MODAL'S OWN SAMPLING ERROR")
            print("  two bootstrap modals of the SAME cell, %d resamples, %d cell(s) at n>=4"
                  % (args.boot, mn["cells"]))
            print("  side-flips between them: median %d, p90 %d, max %d"
                  % (mn["median"], mn["p90"], mn["max"]))
            print("")
            print("  Every modal-vs-modal floor in the table is measured with this much slack")
            print("  in the estimator alone. A row whose p90 is not clearly above it is")
            print("  reporting the instrument, not the factor.")
            print("")

    if args.paired or not (args.modal_noise or args.json):
        pr = paired(boot=args.boot)
        out["paired"] = pr
        if not args.json:
            print("ITEM ORDER vs THE MANIPULATION, WITHIN EACH MODEL (%d models in both arms)"
                  % pr["models"])
            print("  %-40s %7s %7s %6s" % ("model", "order", "manip", "diff"))
            for r in sorted(pr["rows"], key=lambda r: -r["diff"]):
                print("  %-40s %7d %7d %+6d"
                      % (r["model"][-40:], r["order"], r["manip"], r["diff"]))
            print("")
            print("  order larger on %d model(s), manipulation larger on %d, tied on %d"
                  % (pr["order_larger"], pr["manip_larger"], pr["tied"]))
            print("  median within-model difference %+.1f items, 95%% CI [%s, %s]"
                  % (pr["median_diff"], pr["ci95"][0], pr["ci95"][1]))
            print("  sign test on the %d models that differ: p = %s"
                  % (pr["order_larger"] + pr["manip_larger"], pr["sign_test_p"]))

    if args.json:
        if not out:
            out = {"modal_noise": modal_noise(wave_cells(), boot=args.boot),
                   "paired": paired(boot=args.boot)}
        print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
