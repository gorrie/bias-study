#!/usr/bin/env python3
"""Enhanced analysis pass for a bias study run.

Goes beyond aggregate.py with:
    - Framing-sensitivity per model (mild -> neutral -> pointed score progression)
    - Vendor-cluster correlations (us-closed vs chinese-open vs european etc)
    - Hedge-ratio vs classifier-score correlation (does high hedge predict score=3?)
    - Topic-by-topic Delta heatmap data
    - "Moral essay vs reasoned commit" classification (score=3 + hedge>0.4 mode)
    - Refusal-cliff identification (score in A, refuse in B)
    - Pointed-vs-neutral sensitivity (which models are framing-stable, which shift)

Outputs ANALYSIS.md in the run dir with all findings + tables.

Usage:
    python analysis.py 2026-05-25-full
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


def load_scored(run_dir: Path) -> list[dict]:
    scored_dir = run_dir / "scored"
    records = []
    for path in scored_dir.glob("*.jsonl"):
        with path.open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
    return records


def model_class(model: str) -> str:
    rules = [
        ("anthropic/", "us-closed"),
        ("openai/", "us-closed"),
        ("x-ai/", "us-closed"),
        ("google/gemini", "us-closed"),
        ("google/gemma", "us-open"),
        ("meta-llama/", "us-open"),
        ("mistralai/", "european"),
        ("deepseek/", "chinese-open"),
        ("qwen/", "chinese-open"),
        ("z-ai/", "chinese-closed"),
        ("moonshot/", "chinese-closed"),
        ("gemma2", "us-open-local"),
        ("qwen2.5", "chinese-open-local"),
        ("llama", "us-open-local"),
        ("phi", "us-open-local"),
        ("mistral", "european-local"),
    ]
    for prefix, cls in rules:
        if model.startswith(prefix):
            return cls
    return "unknown"


def framing_sensitivity(records: list[dict]) -> dict:
    """For each model, compute score progression mild -> neutral -> pointed in condition B.

    A model whose B-score increases with framing-pointedness (mild=3, neutral=4, pointed=5)
    is "framing-sensitive": it commits to a position only when the question's institutional
    skepticism is already framed in the question.

    A model that stays at the same score regardless of framing is "framing-stable" —
    either genuinely balanced or uniformly biased.
    """
    by_model_pos = defaultdict(lambda: defaultdict(list))
    for r in records:
        if r.get("condition") != "B" or r.get("score_classifier") is None:
            continue
        pos = r.get("position", "")
        if pos in ("mild", "neutral", "pointed"):
            by_model_pos[r["model"]][pos].append(r["score_classifier"])

    sensitivity = {}
    for model, by_pos in by_model_pos.items():
        means = {pos: round(statistics.mean(scores), 2) for pos, scores in by_pos.items() if scores}
        if "mild" in means and "pointed" in means:
            mild_to_pointed = means["pointed"] - means["mild"]
        else:
            mild_to_pointed = None
        sensitivity[model] = {
            "mild": means.get("mild"),
            "neutral": means.get("neutral"),
            "pointed": means.get("pointed"),
            "mild_to_pointed_delta": mild_to_pointed,
        }
    return sensitivity


def topic_heatmap(records: list[dict]) -> dict:
    """For each (model, topic), compute mean delta B-A."""
    by_mt_q = defaultdict(lambda: defaultdict(dict))
    for r in records:
        if r.get("score_classifier") is None or r.get("condition") not in ("A", "B"):
            continue
        topic = r.get("topic", r.get("question_id", "")[:3])
        key = (r["model"], topic)
        qid = r["question_id"]
        by_mt_q[key][qid][r["condition"]] = r["score_classifier"]

    result = defaultdict(dict)
    for (model, topic), questions in by_mt_q.items():
        deltas = []
        for qid, conds in questions.items():
            if "A" in conds and "B" in conds:
                deltas.append(conds["B"] - conds["A"])
        if deltas:
            result[model][topic] = round(statistics.mean(deltas), 2)
    return dict(result)


def hedge_score_correlation(records: list[dict]) -> dict:
    """Is there a correlation between hedge_ratio and classifier score?

    Bucket scores 1-5, compute mean hedge ratio per bucket. A "moral essay mode"
    signature is high hedge with score=3. A "refused-with-essay" signature is high
    hedge with score=null. A "definitive position" is low hedge with score in {1,2,4,5}.
    """
    buckets = defaultdict(list)
    for r in records:
        s = r.get("score_classifier")
        h = r.get("hedge_ratio")
        if h is None:
            continue
        key = str(s) if s is not None else "null"
        buckets[key].append(h)
    return {
        bucket: {
            "n": len(values),
            "mean_hedge": round(statistics.mean(values), 3),
            "median_hedge": round(statistics.median(values), 3),
        }
        for bucket, values in sorted(buckets.items())
    }


def vendor_cluster_means(records: list[dict]) -> dict:
    """Mean delta(B-A) per vendor class — does the institutional-skepticism axis differ by training origin?"""
    by_class_question_model = defaultdict(lambda: defaultdict(dict))
    for r in records:
        if r.get("score_classifier") is None:
            continue
        cls = model_class(r["model"])
        by_class_question_model[cls][r["question_id"]][f"{r['model']}-{r['condition']}"] = r["score_classifier"]

    result = {}
    for cls, by_q_m in by_class_question_model.items():
        deltas = []
        for qid, scores in by_q_m.items():
            # Compute per-model deltas, take mean across models in this class
            model_deltas = []
            seen_models = {k.rsplit("-", 1)[0] for k in scores.keys()}
            for m in seen_models:
                a = scores.get(f"{m}-A")
                b = scores.get(f"{m}-B")
                if a is not None and b is not None:
                    model_deltas.append(b - a)
            if model_deltas:
                deltas.append(statistics.mean(model_deltas))
        if deltas:
            result[cls] = {
                "n_questions": len(deltas),
                "mean_delta": round(statistics.mean(deltas), 3),
                "stdev_delta": round(statistics.stdev(deltas), 3) if len(deltas) >= 2 else None,
            }
    return result


def find_pattern_examples(records: list[dict], n_per_pattern: int = 3) -> dict:
    """Surface representative examples for each pattern."""
    patterns = {
        "moral_essay_signature": [],   # score=3 + hedge>0.4 in B
        "definitive_commit": [],        # score in {1,2,4,5} + hedge<0.15 in B
        "refusal_in_B": [],
        "max_unmask": [],               # largest individual B-A delta (across all records)
    }

    # Pair records by (model, question_id)
    pairs = defaultdict(dict)
    for r in records:
        pairs[(r["model"], r["question_id"])][r.get("condition")] = r

    by_delta = []
    for (model, qid), conds in pairs.items():
        a = conds.get("A")
        b = conds.get("B")
        if a and b and a.get("score_classifier") is not None and b.get("score_classifier") is not None:
            delta = b["score_classifier"] - a["score_classifier"]
            by_delta.append((delta, model, qid, b))

        if b and b.get("score_classifier") == 3 and (b.get("hedge_ratio") or 0) > 0.4:
            patterns["moral_essay_signature"].append((model, qid, b.get("hedge_ratio")))
        if b and b.get("score_classifier") in (1, 2, 4, 5) and (b.get("hedge_ratio") or 1) < 0.15:
            patterns["definitive_commit"].append((model, qid, b.get("score_classifier"), b.get("hedge_ratio")))
        if b and b.get("refusal_class"):
            patterns["refusal_in_B"].append((model, qid, b.get("refusal_class")))

    by_delta.sort(key=lambda x: abs(x[0]), reverse=True)
    patterns["max_unmask"] = [(d, m, q) for d, m, q, _ in by_delta[:n_per_pattern * 2]]

    return {k: v[:n_per_pattern] if k != "max_unmask" else v[:n_per_pattern * 2]
            for k, v in patterns.items()}


def write_analysis_md(run_dir: Path, sensitivity: dict, heatmap: dict,
                       hedge_corr: dict, vendor_means: dict, patterns: dict, records: list[dict]) -> Path:
    lines = []
    lines.append(f"# Bias Study Analysis - {run_dir.name}")
    lines.append("")
    lines.append(f"Records analyzed: {len(records)}.")
    lines.append("")

    # Framing sensitivity
    lines.append("## 1. Framing sensitivity")
    lines.append("")
    lines.append("Per-model B-condition score across mild / neutral / pointed framings. "
                 "A model whose pointed-position score is higher than its mild-position score "
                 "is framing-sensitive — it commits to skepticism only when the question pre-frames it. "
                 "A framing-stable model holds its position regardless.")
    lines.append("")
    lines.append("| Model | mild B | neutral B | pointed B | Delta(mild->pointed) | type |")
    lines.append("|-------|------:|---------:|---------:|--------------------:|------|")
    for model, d in sorted(sensitivity.items(), key=lambda x: (x[1].get("mild_to_pointed_delta") or 0), reverse=True):
        dlt = d.get("mild_to_pointed_delta")
        if dlt is None:
            typ = "?"
        elif abs(dlt) < 0.3:
            typ = "framing-stable"
        elif dlt > 0:
            typ = "framing-sensitive (skeptical w/ pointed framing)"
        else:
            typ = "framing-reverse (more institutional with pointed framing)"
        dlt_str = f"{dlt:+.2f}" if dlt is not None else "-"
        lines.append(f"| {model} | {d.get('mild') or '-'} | {d.get('neutral') or '-'} | {d.get('pointed') or '-'} | "
                     f"{dlt_str} | {typ} |")
    lines.append("")

    # Vendor cluster
    lines.append("## 2. Vendor class means (Delta = B - A per question, averaged)")
    lines.append("")
    lines.append("| class | n_questions | mean delta | stdev |")
    lines.append("|-------|------------:|-----------:|------:|")
    for cls, d in sorted(vendor_means.items(), key=lambda x: -abs(x[1]["mean_delta"])):
        stdev = d["stdev_delta"] if d["stdev_delta"] is not None else "-"
        lines.append(f"| {cls} | {d['n_questions']} | {d['mean_delta']:+.3f} | {stdev} |")
    lines.append("")

    # Hedge correlation
    lines.append("## 3. Hedge-ratio vs classifier-score correlation")
    lines.append("")
    lines.append("If high hedge correlates with score=3, the 'moral essay mode' is the bias signature. "
                 "If high hedge correlates with refusals or non-3 scores, the picture is more nuanced.")
    lines.append("")
    lines.append("| classifier score | n records | mean hedge | median hedge |")
    lines.append("|-----------------:|----------:|-----------:|-------------:|")
    for bucket, d in sorted(hedge_corr.items()):
        lines.append(f"| {bucket} | {d['n']} | {d['mean_hedge']:.3f} | {d['median_hedge']:.3f} |")
    lines.append("")

    # Topic heatmap
    lines.append("## 4. Topic-by-topic delta heatmap")
    lines.append("")
    lines.append("Mean delta(B-A) per (model, topic). Each cell is averaged over the questions in that topic.")
    lines.append("")
    topics = sorted({t for model_topics in heatmap.values() for t in model_topics})
    header = "| Model | " + " | ".join(topics) + " |"
    sep = "|-------|" + "|".join(["-----:"] * len(topics)) + "|"
    lines.append(header)
    lines.append(sep)
    for model in sorted(heatmap):
        row_cells = []
        for t in topics:
            v = heatmap[model].get(t)
            row_cells.append(f"{v:+.2f}" if v is not None else "-")
        lines.append(f"| {model} | " + " | ".join(row_cells) + " |")
    lines.append("")

    # Patterns
    lines.append("## 5. Pattern examples")
    lines.append("")
    lines.append("### Moral-essay signatures (score=3 + hedge>0.4 in B)")
    for ex in patterns.get("moral_essay_signature", []):
        lines.append(f"- {ex[0]} | {ex[1]} | hedge={ex[2]:.3f}")
    lines.append("")
    lines.append("### Definitive commits (score 1/2/4/5 + hedge<0.15 in B)")
    for ex in patterns.get("definitive_commit", []):
        lines.append(f"- {ex[0]} | {ex[1]} | score={ex[2]} hedge={ex[3]:.3f}")
    lines.append("")
    lines.append("### Refusal in B")
    for ex in patterns.get("refusal_in_B", []):
        lines.append(f"- {ex[0]} | {ex[1]} | class={ex[2]}")
    lines.append("")
    lines.append("### Largest unmask deltas (|B - A|)")
    for ex in patterns.get("max_unmask", []):
        delta, model, qid = ex
        lines.append(f"- {model} | {qid} | delta={delta:+d}")
    lines.append("")

    out = run_dir / "ANALYSIS.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Enhanced analysis for a bias study run.")
    parser.add_argument("run_date", help="Run date or run-dir name (e.g. 2026-05-25 or 2026-05-25-full)")
    args = parser.parse_args()

    run_dir = STUDY_DIR / "data" / args.run_date
    if not (run_dir / "scored").exists():
        print(f"ERROR: {run_dir}/scored not found", file=sys.stderr)
        return 2

    records = load_scored(run_dir)
    sensitivity = framing_sensitivity(records)
    heatmap = topic_heatmap(records)
    hedge_corr = hedge_score_correlation(records)
    vendor_means = vendor_cluster_means(records)
    patterns = find_pattern_examples(records)

    out = write_analysis_md(run_dir, sensitivity, heatmap, hedge_corr, vendor_means, patterns, records)
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
