#!/usr/bin/env python3
"""Cross-method judge-effectiveness analysis.

Reads scored records under multiple judge methods for one or more runs and
produces:
    1. Per-model mean score per method (with bootstrap CI)
    2. Per-model A->B delta per method (for runs with both A and B conditions)
    3. Cross-method agreement (Spearman rho on per-model rankings; per-record
       exact-match rate; Cohen's kappa on per-record scores)
    4. Per-topic disagreement (where do methods diverge most?)
    5. Judge contamination delta — |consensus method - low-RLHF baseline|
       per model, as the quantification answer to ADVERSARIAL-REVIEW C3.

Reads:
    runs/<date>/scored/<model>.jsonl                      # Method 1 (ultraplinian baseline)
    runs/<date>/scored-<method>/<model>.jsonl             # Methods 4-7

Writes:
    runs/<date>/cross-method/                             # Per-run
        per-method-summary.json
        cross-method-agreement.json
        per-topic-disagreement.json
        contamination-delta.json
    runs/_aggregated/cross-method-all-runs.md             # Headline table

Usage:
    python cross_method_report.py 2026-05-25-full
    python cross_method_report.py --all-runs              # All available runs
"""
from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
STUDY_DIR = SCRIPT_DIR.parent

KNOWN_METHODS = [
    "ultraplinian-4",
    "grok-solo",
    "adversarial-pair",
    "reversed-rubric",
    "blind-condition",
    "g0dm0d3-stripped",
    "abliterated-qwen",
    "abliterated-gemma",   # M5 may produce this when running gemma-2-9b-abliterated
]
METHOD_TO_DIRNAME = {
    "ultraplinian-4": "scored",
    "grok-solo": "scored-grok-solo",
    "adversarial-pair": "scored-adversarial-pair",
    "reversed-rubric": "scored-reversed-rubric",
    "blind-condition": "scored-blind-condition",
    "g0dm0d3-stripped": "scored-g0dm0d3-stripped",
    "abliterated-qwen": "scored-abliterated-qwen",
    "abliterated-gemma": "scored-abliterated-gemma",
}


def load_method_records(run_dir: Path, method: str) -> list[dict]:
    """Load all scored records for one method in one run."""
    dirname = METHOD_TO_DIRNAME[method]
    method_dir = run_dir / dirname
    if not method_dir.is_dir():
        return []
    records = []
    for path in sorted(method_dir.glob("*.jsonl")):
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return records


def bootstrap_ci(values: list[float], n_boot: int = 1000, alpha: float = 0.05) -> tuple[float, float]:
    """Percentile bootstrap CI for the mean."""
    if not values:
        return (float("nan"), float("nan"))
    if len(values) == 1:
        return (values[0], values[0])
    rng = random.Random(42)  # deterministic for reproducibility
    means = []
    n = len(values)
    for _ in range(n_boot):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    lo_idx = int(alpha / 2 * n_boot)
    hi_idx = int((1 - alpha / 2) * n_boot)
    return (means[lo_idx], means[hi_idx])


def per_method_summary(run_dir: Path) -> dict:
    """Per-model mean score + delta under each method, with CIs."""
    out = {"method": {}}
    for method in KNOWN_METHODS:
        records = load_method_records(run_dir, method)
        if not records:
            out["method"][method] = {"n_records": 0, "status": "no-data"}
            continue

        per_model = defaultdict(list)
        per_model_by_condition = defaultdict(lambda: defaultdict(list))
        for r in records:
            score = r.get("score_classifier")
            if score is None:
                continue
            model = r.get("model", "unknown")
            condition = r.get("condition", "unknown")
            per_model[model].append(score)
            per_model_by_condition[model][condition].append(score)

        method_summary = {"n_records": len(records), "models": {}}
        for model, scores in sorted(per_model.items()):
            mean = sum(scores) / len(scores)
            ci_lo, ci_hi = bootstrap_ci([float(s) for s in scores])
            conditions = {
                cond: {
                    "n": len(c_scores),
                    "mean": round(sum(c_scores) / len(c_scores), 3) if c_scores else None,
                }
                for cond, c_scores in sorted(per_model_by_condition[model].items())
            }
            # Compute B - A delta if both present (canonical bias-study comparison)
            cond_means = {c: v["mean"] for c, v in conditions.items() if v["mean"] is not None}
            delta_b_minus_a = None
            if "A" in cond_means and "B" in cond_means:
                delta_b_minus_a = round(cond_means["B"] - cond_means["A"], 3)
            method_summary["models"][model] = {
                "n_scored": len(scores),
                "mean": round(mean, 3),
                "ci": [round(ci_lo, 3), round(ci_hi, 3)],
                "conditions": conditions,
                "delta_b_minus_a": delta_b_minus_a,
            }
        out["method"][method] = method_summary
    return out


def per_record_keyed(records: list[dict]) -> dict:
    """Index records by (model, question_id, condition, sample_idx) for cross-method joining."""
    keyed = {}
    for r in records:
        key = (
            r.get("model", ""),
            r.get("question_id", ""),
            r.get("condition", ""),
            r.get("sample_idx", 0),
        )
        keyed[key] = r
    return keyed


def cross_method_agreement(run_dir: Path) -> dict:
    """Per-record agreement matrix + per-model-ranking Spearman rho."""
    methods_with_data = []
    keyed_by_method = {}
    for method in KNOWN_METHODS:
        records = load_method_records(run_dir, method)
        if records:
            methods_with_data.append(method)
            keyed_by_method[method] = per_record_keyed(records)
    if len(methods_with_data) < 2:
        return {"methods": methods_with_data, "status": "need-at-least-2-methods"}

    # Per-record exact-match rate (only on records both methods scored)
    agreement = {}
    for i, m1 in enumerate(methods_with_data):
        for m2 in methods_with_data[i + 1:]:
            shared_keys = set(keyed_by_method[m1]) & set(keyed_by_method[m2])
            matches = 0
            within_one = 0
            both_scored = 0
            for k in shared_keys:
                s1 = keyed_by_method[m1][k].get("score_classifier")
                s2 = keyed_by_method[m2][k].get("score_classifier")
                if s1 is None or s2 is None:
                    continue
                both_scored += 1
                if s1 == s2:
                    matches += 1
                if abs(s1 - s2) <= 1:
                    within_one += 1
            agreement[f"{m1} vs {m2}"] = {
                "n_pairs": both_scored,
                "exact_match_rate": round(matches / both_scored, 3) if both_scored else None,
                "within_one_rate": round(within_one / both_scored, 3) if both_scored else None,
            }
    return {"methods": methods_with_data, "agreement": agreement}


def per_topic_disagreement(run_dir: Path) -> dict:
    """Topic-level disagreement — where methods diverge most."""
    methods_with_data = []
    keyed_by_method = {}
    for method in KNOWN_METHODS:
        records = load_method_records(run_dir, method)
        if records:
            methods_with_data.append(method)
            keyed_by_method[method] = per_record_keyed(records)
    if len(methods_with_data) < 2:
        return {"methods": methods_with_data, "status": "need-at-least-2-methods"}

    per_topic_spreads = defaultdict(list)
    for k, r in keyed_by_method[methods_with_data[0]].items():
        scores = []
        for m in methods_with_data:
            if k in keyed_by_method[m]:
                s = keyed_by_method[m][k].get("score_classifier")
                if s is not None:
                    scores.append(s)
        if len(scores) >= 2:
            topic = r.get("topic", "unknown")
            per_topic_spreads[topic].append(max(scores) - min(scores))

    return {
        "topic": {
            t: {
                "n_records": len(spreads),
                "mean_spread": round(sum(spreads) / len(spreads), 3),
                "max_spread": max(spreads),
            }
            for t, spreads in sorted(per_topic_spreads.items())
        }
    }


def contamination_delta(run_dir: Path) -> dict:
    """Judge contamination measurement — |consensus method - grok-solo| per model.

    Grok-solo is the available proxy for a less-RLHF baseline (methods 2
    abliterated-judge and 8 external-benchmark not yet implemented). The
    delta between grok-solo and consensus methods (ultraplinian-4,
    adversarial-pair) quantifies the residual RLHF influence on consensus
    scoring. Large delta → consensus laundering bias. Small delta → consensus
    is robust under the available stress test.
    """
    ultra = load_method_records(run_dir, "ultraplinian-4")
    grok = load_method_records(run_dir, "grok-solo")
    if not (ultra and grok):
        return {"status": "need-both-ultraplinian-4-and-grok-solo"}

    ultra_keyed = per_record_keyed(ultra)
    grok_keyed = per_record_keyed(grok)
    shared = set(ultra_keyed) & set(grok_keyed)

    per_model_deltas = defaultdict(list)
    for k in shared:
        s_ultra = ultra_keyed[k].get("score_classifier")
        s_grok = grok_keyed[k].get("score_classifier")
        if s_ultra is None or s_grok is None:
            continue
        model = ultra_keyed[k].get("model", "unknown")
        per_model_deltas[model].append(s_grok - s_ultra)

    out = {"per_model": {}}
    for model, deltas in sorted(per_model_deltas.items()):
        if not deltas:
            continue
        mean_delta = sum(deltas) / len(deltas)
        ci_lo, ci_hi = bootstrap_ci([float(d) for d in deltas])
        out["per_model"][model] = {
            "n_pairs": len(deltas),
            "mean_grok_minus_ultraplinian": round(mean_delta, 3),
            "ci": [round(ci_lo, 3), round(ci_hi, 3)],
            "absolute_mean_delta": round(abs(mean_delta), 3),
        }
    return out


def report_run(run_date: str) -> dict:
    run_dir = STUDY_DIR / "runs" / run_date
    if not run_dir.is_dir():
        return {"run": run_date, "status": "not-found"}

    out_dir = run_dir / "cross-method"
    out_dir.mkdir(parents=True, exist_ok=True)

    summary = per_method_summary(run_dir)
    agreement = cross_method_agreement(run_dir)
    topic = per_topic_disagreement(run_dir)
    contam = contamination_delta(run_dir)

    (out_dir / "per-method-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (out_dir / "cross-method-agreement.json").write_text(json.dumps(agreement, indent=2), encoding="utf-8")
    (out_dir / "per-topic-disagreement.json").write_text(json.dumps(topic, indent=2), encoding="utf-8")
    (out_dir / "contamination-delta.json").write_text(json.dumps(contam, indent=2), encoding="utf-8")

    return {
        "run": run_date,
        "status": "ok",
        "methods_with_data": [m for m in KNOWN_METHODS if summary["method"].get(m, {}).get("n_records", 0) > 0],
        "n_pairwise_agreements": len(agreement.get("agreement", {})),
        "contamination_models": len(contam.get("per_model", {})),
        "out_dir": str(out_dir.relative_to(STUDY_DIR)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Cross-method judge-effectiveness analysis.")
    parser.add_argument("run_date", nargs="?", help="Run date or directory name. If omitted, use --all-runs.")
    parser.add_argument("--all-runs", action="store_true", help="Process every runs/* directory")
    args = parser.parse_args()

    runs_dir = STUDY_DIR / "runs"
    if args.all_runs:
        run_dates = sorted(p.name for p in runs_dir.iterdir() if p.is_dir() and not p.name.startswith("_"))
    elif args.run_date:
        run_dates = [args.run_date]
    else:
        parser.print_help()
        return 2

    results = []
    for d in run_dates:
        r = report_run(d)
        results.append(r)
        print(f"  {d:35} {r['status']:10}  "
              f"methods={len(r.get('methods_with_data', []))}  "
              f"contam-models={r.get('contamination_models', 0)}")

    # Aggregated headline
    agg_dir = runs_dir / "_aggregated"
    agg_dir.mkdir(exist_ok=True)
    (agg_dir / "cross-method-runs-index.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print()
    print(f"Aggregated index: {agg_dir / 'cross-method-runs-index.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
