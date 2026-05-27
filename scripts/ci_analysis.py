#!/usr/bin/env python3
"""
ci_analysis.py — Bootstrap confidence intervals + inter-judge agreement over
already-scored bias-study runs. No API calls; reads runs/<date>/scored/*.jsonl.

Addresses the audit's two statistical killshots:
  1. Report every per-model B-A delta as mean +/- 95% CI (bootstrap over the
     per-question deltas), and flag deltas whose CI crosses zero as
     "not distinguishable from zero" at the study's noise floor.
  2. Report Krippendorff's alpha (ordinal) across the LLM judges as the
     inter-judge reliability statistic.

Usage:
    python ci_analysis.py <run_date> [<run_date> ...]
    python ci_analysis.py 2026-05-25-full 2026-05-26-variance
"""
from __future__ import annotations

import json
import random
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
STUDY_DIR = SCRIPT_DIR.parent
BOOTSTRAP_N = 10000
random.seed(20260527)  # deterministic CIs


def load_scored(run_dir: Path) -> list[dict]:
    recs = []
    sdir = run_dir / "scored"
    for f in sorted(sdir.glob("*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                recs.append(json.loads(line))
    return recs


def per_model_deltas(recs: list[dict]) -> dict[str, list[float]]:
    """For each model: per-question (B - A) deltas, averaging samples if N>1."""
    # model -> qid -> condition -> [scores]
    acc: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for r in recs:
        s = r.get("score_classifier")
        if s is None:
            continue
        acc[r["model"]][r["question_id"]][r["condition"]].append(s)
    out: dict[str, list[float]] = {}
    for model, qs in acc.items():
        deltas = []
        for qid, conds in qs.items():
            if "A" in conds and "B" in conds:
                a = sum(conds["A"]) / len(conds["A"])
                b = sum(conds["B"]) / len(conds["B"])
                deltas.append(b - a)
        if deltas:
            out[model] = deltas
    return out


def bootstrap_ci(deltas: list[float], n: int = BOOTSTRAP_N, alpha: float = 0.05):
    k = len(deltas)
    mean = sum(deltas) / k
    if k < 2:
        return mean, None, None
    means = []
    for _ in range(n):
        s = 0.0
        for _ in range(k):
            s += deltas[random.randrange(k)]
        means.append(s / k)
    means.sort()
    lo = means[int((alpha / 2) * n)]
    hi = means[int((1 - alpha / 2) * n)]
    return mean, lo, hi


def krippendorff_alpha_ordinal(ratings: list[list[int]]) -> float | None:
    """Ordinal Krippendorff's alpha. `ratings` = list of items, each a list of
    judge scores (missing judges omitted). Standard coincidence-matrix method."""
    # Build value set
    values = sorted({v for item in ratings for v in item})
    if len(values) < 2:
        return None
    vidx = {v: i for i, v in enumerate(values)}
    K = len(values)
    # Coincidence matrix
    coinc = [[0.0] * K for _ in range(K)]
    for item in ratings:
        m = len(item)
        if m < 2:
            continue
        for a, b in combinations(item, 2):
            ia, ib = vidx[a], vidx[b]
            # each unordered pair counted both directions, weighted by 1/(m-1)
            coinc[ia][ib] += 1.0 / (m - 1)
            coinc[ib][ia] += 1.0 / (m - 1)
    n_c = [sum(coinc[i]) for i in range(K)]
    n_total = sum(n_c)
    if n_total == 0:
        return None
    # Ordinal distance metric
    def delta2(i, j):
        lo, hi = (i, j) if i <= j else (j, i)
        s = n_c[lo] / 2 + n_c[hi] / 2 + sum(n_c[lo + 1:hi])
        return s * s
    Do = sum(coinc[i][j] * delta2(i, j) for i in range(K) for j in range(K))
    De = sum(n_c[i] * n_c[j] * delta2(i, j) for i in range(K) for j in range(K)) / (n_total - 1)
    if De == 0:
        return None
    return 1 - (Do / De)


def judge_ratings(recs: list[dict]) -> list[list[int]]:
    out = []
    for r in recs:
        judges = r.get("score_classifier_judges") or []
        scores = [j["score"] for j in judges if j.get("score") is not None and not j.get("error")]
        if len(scores) >= 2:
            out.append(scores)
    return out


def main() -> int:
    run_dates = sys.argv[1:]
    if not run_dates:
        print("usage: ci_analysis.py <run_date> [<run_date> ...]", file=sys.stderr)
        return 1
    for rd in run_dates:
        run_dir = STUDY_DIR / "runs" / rd
        if not (run_dir / "scored").exists():
            print(f"[skip] {rd}: no scored/", file=sys.stderr)
            continue
        recs = load_scored(run_dir)
        print(f"\n=== {rd} ({len(recs)} scored records) ===")
        deltas_by_model = per_model_deltas(recs)
        print(f"  {'model':<42} {'n':>3} {'meanD':>7} {'95% CI':>18}  verdict")
        n_sig = n_null = 0
        for model in sorted(deltas_by_model):
            d = deltas_by_model[model]
            mean, lo, hi = bootstrap_ci(d)
            if lo is None:
                verdict = "n<2 (single delta)"
                ci = "  --"
            elif lo <= 0 <= hi:
                verdict = "NOT distinguishable from 0"
                ci = f"[{lo:+.2f}, {hi:+.2f}]"
                n_null += 1
            else:
                verdict = "significant"
                ci = f"[{lo:+.2f}, {hi:+.2f}]"
                n_sig += 1
            print(f"  {model:<42} {len(d):>3} {mean:>+7.2f} {ci:>18}  {verdict}")
        # Inter-judge reliability
        ratings = judge_ratings(recs)
        alpha = krippendorff_alpha_ordinal(ratings)
        print(f"  --- inter-judge reliability ---")
        print(f"  Krippendorff's alpha (ordinal, {len(ratings)} items, "
              f"{max((len(r) for r in ratings), default=0)} judges): "
              f"{alpha:.3f}" if alpha is not None else "  alpha: n/a")
        if deltas_by_model:
            print(f"  --> {n_sig} model(s) with CI excluding 0; {n_null} not distinguishable from 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
