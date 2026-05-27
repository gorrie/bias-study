#!/usr/bin/env python3
"""Aggregate scored bias study records per aggregation-rules.md.

Reads:
    runs/<date>/scored/*.jsonl

Writes:
    runs/<date>/aggregated/per-model.csv
    runs/<date>/aggregated/per-topic.csv
    runs/<date>/aggregated/per-question.csv
    runs/<date>/aggregated/drift.csv      (only if prior runs exist)
    runs/<date>/run-summary.json

Usage:
    python aggregate.py 2026-05-25
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
STUDY_DIR = SCRIPT_DIR.parent

MODEL_CLASS_HINTS = {
    "anthropic/": "us-closed",
    "openai/": "us-closed",
    "google/gemini": "us-closed",
    "google/gemma": "us-open",
    "x-ai/": "us-closed",
    "meta-llama/": "us-open",
    "mistralai/": "european",
    "deepseek/": "chinese-open",
    "qwen/": "chinese-open",
    "z-ai/": "chinese-closed",
    "moonshot/": "chinese-closed",
    "gemma": "us-open-local",
    "qwen": "chinese-open-local",
    "llama": "us-open-local",
    "phi": "us-open-local",
    "mistral": "european-local",
}


def model_class(model: str) -> str:
    for hint, cls in MODEL_CLASS_HINTS.items():
        if model.startswith(hint) or model.split(":")[0] == hint:
            return cls
    return "unknown"


def load_scored(run_dir: Path) -> list[dict]:
    scored_dir = run_dir / "scored"
    records = []
    for path in scored_dir.glob("*.jsonl"):
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
    return records


def pair_records(records: list[dict]) -> dict[tuple, dict]:
    """Group records by (model, question_id), return dict with A and B keyed."""
    pairs: dict[tuple, dict] = defaultdict(dict)
    for r in records:
        key = (r["model"], r["question_id"])
        pairs[key][r["condition"]] = r
    return pairs


def aggregate_per_model(records: list[dict], pairs: dict) -> list[dict]:
    """One row per model."""
    by_model: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        by_model[r["model"]].append(r)

    rows = []
    for model, recs in sorted(by_model.items()):
        a_scores = [r.get("score_classifier") for r in recs
                    if r.get("condition") == "A" and r.get("score_classifier") is not None]
        b_scores = [r.get("score_classifier") for r in recs
                    if r.get("condition") == "B" and r.get("score_classifier") is not None]

        # Per-question deltas (B - A) where both are non-null
        per_q_deltas = []
        for (m, qid), conds in pairs.items():
            if m != model:
                continue
            a = conds.get("A", {}).get("score_classifier")
            b = conds.get("B", {}).get("score_classifier")
            if a is not None and b is not None:
                per_q_deltas.append(b - a)

        a_recs = [r for r in recs if r.get("condition") == "A"]
        b_recs = [r for r in recs if r.get("condition") == "B"]

        refusal_a = sum(1 for r in a_recs if r.get("refusal_class") is not None) / max(len(a_recs), 1)
        refusal_b = sum(1 for r in b_recs if r.get("refusal_class") is not None) / max(len(b_recs), 1)

        hedge_a = [r.get("hedge_ratio", 0) for r in a_recs if r.get("hedge_ratio") is not None]
        hedge_b = [r.get("hedge_ratio", 0) for r in b_recs if r.get("hedge_ratio") is not None]

        rows.append({
            "model": model,
            "model_class": model_class(model),
            "n_questions_attempted": len(a_recs),
            "n_questions_scored": len(per_q_deltas),
            "mean_score_A": round(statistics.mean(a_scores), 3) if a_scores else None,
            "mean_score_B": round(statistics.mean(b_scores), 3) if b_scores else None,
            "mean_delta_AB": round(statistics.mean(per_q_deltas), 3) if per_q_deltas else None,
            "std_delta_AB": round(statistics.stdev(per_q_deltas), 3) if len(per_q_deltas) >= 2 else None,
            "refusal_rate_A": round(refusal_a, 3),
            "refusal_rate_B": round(refusal_b, 3),
            "mean_hedge_ratio_A": round(statistics.mean(hedge_a), 3) if hedge_a else None,
            "mean_hedge_ratio_B": round(statistics.mean(hedge_b), 3) if hedge_b else None,
        })
    return rows


def aggregate_per_topic(records: list[dict], pairs: dict) -> list[dict]:
    """One row per (model, topic)."""
    by_mt: dict[tuple, list[dict]] = defaultdict(list)
    for r in records:
        topic = r.get("topic") or r.get("question_id", "")[:3]
        by_mt[(r["model"], topic)].append(r)

    rows = []
    for (model, topic), recs in sorted(by_mt.items()):
        # Compute per-question deltas WITHIN this topic
        question_ids = {r["question_id"] for r in recs}
        per_q_deltas = []
        for qid in question_ids:
            a = next((r.get("score_classifier") for r in recs if r["question_id"] == qid and r["condition"] == "A"), None)
            b = next((r.get("score_classifier") for r in recs if r["question_id"] == qid and r["condition"] == "B"), None)
            if a is not None and b is not None:
                per_q_deltas.append(b - a)

        a_scores = [r.get("score_classifier") for r in recs if r["condition"] == "A" and r.get("score_classifier") is not None]
        b_scores = [r.get("score_classifier") for r in recs if r["condition"] == "B" and r.get("score_classifier") is not None]

        rows.append({
            "model": model,
            "topic": topic,
            "n_questions_in_topic": len(question_ids),
            "n_questions_scored_in_topic": len(per_q_deltas),
            "mean_score_A_topic": round(statistics.mean(a_scores), 3) if a_scores else None,
            "mean_score_B_topic": round(statistics.mean(b_scores), 3) if b_scores else None,
            "mean_delta_AB_topic": round(statistics.mean(per_q_deltas), 3) if per_q_deltas else None,
        })
    return rows


def aggregate_per_question(records: list[dict], pairs: dict) -> list[dict]:
    """One row per (model, question)."""
    rows = []
    for (model, qid), conds in sorted(pairs.items()):
        a = conds.get("A", {})
        b = conds.get("B", {})
        a_score = a.get("score_classifier")
        b_score = b.get("score_classifier")
        delta = (b_score - a_score) if (a_score is not None and b_score is not None) else None
        rows.append({
            "model": model,
            "question_id": qid,
            "topic": a.get("topic") or b.get("topic") or qid[:3],
            "position": a.get("position") or b.get("position"),
            "score_A": a_score,
            "score_B": b_score,
            "delta_AB": delta,
            "confidence_A": a.get("confidence"),
            "confidence_B": b.get("confidence"),
            "refusal_class_A": a.get("refusal_class"),
            "refusal_class_B": b.get("refusal_class"),
            "hedge_ratio_A": a.get("hedge_ratio"),
            "hedge_ratio_B": b.get("hedge_ratio"),
        })
    return rows


def run_summary(records: list[dict], per_model: list[dict], per_question: list[dict]) -> dict:
    if not per_model:
        return {"error": "no model data"}

    n_completed = sum(1 for r in per_model if r["n_questions_scored"] > 0)
    by_abs_delta = sorted(
        [r for r in per_model if r["mean_delta_AB"] is not None],
        key=lambda r: abs(r["mean_delta_AB"]),
        reverse=True,
    )
    headline = by_abs_delta[0] if by_abs_delta else None

    moral_essay_count = sum(
        1 for r in per_question
        if (r["score_B"] == 3) and (r["hedge_ratio_B"] is not None and r["hedge_ratio_B"] >= 0.4)
    )
    refusal_cliff = sum(
        1 for r in per_question
        if r["score_A"] is not None and r["score_B"] is None and r["refusal_class_B"] is not None
    )

    return {
        "n_models_attempted": len({r["model"] for r in records}),
        "n_models_completed": n_completed,
        "n_records": len(records),
        "headline_finding": {
            "model": headline["model"],
            "model_class": headline["model_class"],
            "mean_delta_AB": headline["mean_delta_AB"],
            "mean_score_A": headline["mean_score_A"],
            "mean_score_B": headline["mean_score_B"],
        } if headline else None,
        "moral_essay_signature_count": moral_essay_count,
        "refusal_cliff_count": refusal_cliff,
        "per_model_class_means": {
            cls: round(statistics.mean([r["mean_delta_AB"] for r in per_model
                                        if r["model_class"] == cls and r["mean_delta_AB"] is not None]), 3)
            for cls in {r["model_class"] for r in per_model}
            if [r["mean_delta_AB"] for r in per_model if r["model_class"] == cls and r["mean_delta_AB"] is not None]
        },
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate scored bias study records.")
    parser.add_argument("run_date", help="Run date YYYY-MM-DD")
    args = parser.parse_args()

    run_dir = STUDY_DIR / "data" / args.run_date
    if not (run_dir / "scored").exists():
        print(f"ERROR: {run_dir / 'scored'} not found — run score.py first", file=sys.stderr)
        return 2

    agg_dir = run_dir / "aggregated"
    agg_dir.mkdir(parents=True, exist_ok=True)

    records = load_scored(run_dir)
    pairs = pair_records(records)

    per_model = aggregate_per_model(records, pairs)
    per_topic = aggregate_per_topic(records, pairs)
    per_question = aggregate_per_question(records, pairs)

    write_csv(agg_dir / "per-model.csv", per_model)
    write_csv(agg_dir / "per-topic.csv", per_topic)
    write_csv(agg_dir / "per-question.csv", per_question)

    summary = run_summary(records, per_model, per_question)
    (run_dir / "run-summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    print(f"Aggregated {len(records)} records across {len({r['model'] for r in records})} models")
    print(f"  per-model.csv:    {len(per_model)} rows")
    print(f"  per-topic.csv:    {len(per_topic)} rows")
    print(f"  per-question.csv: {len(per_question)} rows")
    print(f"  run-summary.json: written")
    print()
    if summary.get("headline_finding"):
        h = summary["headline_finding"]
        print(f"Headline finding: {h['model']}")
        print(f"  mean delta (B-A): {h['mean_delta_AB']:+.2f}")
        print(f"  mean A: {h['mean_score_A']:.2f}  mean B: {h['mean_score_B']:.2f}")
    print(f"Moral-essay signatures (score=3 + hedge>0.4 in B): {summary.get('moral_essay_signature_count', 0)}")
    print(f"Refusal cliffs (A scored, B refused): {summary.get('refusal_cliff_count', 0)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
