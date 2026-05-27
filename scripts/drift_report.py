#!/usr/bin/env python3
"""Generate the human-readable drift summary for one run.

Reads:
    runs/<date>/aggregated/per-model.csv
    runs/<date>/run-summary.json

Writes:
    runs/<date>/REPORT.md

Compares per-model mean_delta_AB to the v1 baseline (Gemma 2 = +2.00
across all questions; established in The Ratchet Ch. 21). Surfaces:
    - Headline drift (largest |delta|)
    - Gemma 2 cloud + local comparison vs v1's +2.00
    - Per-model-class means (us-closed / us-open / chinese-* / etc.)
    - Refusal cliffs and moral-essay signatures

Usage:
    python drift_report.py 2026-05-25
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
STUDY_DIR = SCRIPT_DIR.parent

V1_BASELINE = {
    "gemma2": 2.00,  # the v1 finding: +2.00 delta across all 10 questions
    "v1_run_date": "(prior research, ~2024-2025)",
    "v1_source": "The Ratchet Ch. 21 — 'The Cat or the Dog'",
}


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate drift report for a bias study run.")
    parser.add_argument("run_date", help="Run date YYYY-MM-DD")
    args = parser.parse_args()

    run_dir = STUDY_DIR / "data" / args.run_date
    per_model = read_csv(run_dir / "aggregated" / "per-model.csv")
    summary_path = run_dir / "run-summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}

    if not per_model:
        print(f"ERROR: no per-model.csv at {run_dir}", file=sys.stderr)
        return 2

    def f(v: str | None) -> float | None:
        if v is None or v == "":
            return None
        try:
            return float(v)
        except ValueError:
            return None

    lines = []
    lines.append(f"# Bias Study Run — {args.run_date}")
    lines.append("")
    lines.append(f"**v1 baseline:** Gemma 2 = +{V1_BASELINE['gemma2']:.2f} delta across all 10 questions.")
    lines.append(f"*Source: {V1_BASELINE['v1_source']}.*")
    lines.append("")
    lines.append("## Headline finding")
    lines.append("")
    h = summary.get("headline_finding")
    if h:
        lines.append(f"**{h['model']}** ({h['model_class']}): mean Δ(B−A) = **{h['mean_delta_AB']:+.2f}** "
                     f"(A={h['mean_score_A']:.2f}, B={h['mean_score_B']:.2f}).")
    lines.append("")

    # Drift comparison for Gemma 2 (the v1 finding subject)
    lines.append("## Drift vs v1 baseline")
    lines.append("")
    lines.append("Gemma 2 was the v1 subject (+2.00 delta across all 10 questions).")
    lines.append("Comparing current measurements:")
    lines.append("")
    lines.append("| Model | mean Δ(B−A) | vs v1 baseline | direction |")
    lines.append("|-------|------------:|---------------:|-----------|")
    for row in per_model:
        if "gemma-2" in row["model"].lower() or row["model"].startswith("gemma2"):
            delta = f(row["mean_delta_AB"])
            if delta is not None:
                drift = delta - V1_BASELINE["gemma2"]
                direction = "less-skeptical" if drift < -0.25 else ("more-skeptical" if drift > 0.25 else "held-steady")
                lines.append(f"| {row['model']} | {delta:+.2f} | {drift:+.2f} | {direction} |")
    lines.append("")

    # All-models table sorted by |delta|
    lines.append("## All models (sorted by |Δ|)")
    lines.append("")
    lines.append("| Model | class | mean A | mean B | Δ(B−A) | refusal A | refusal B | hedge A | hedge B |")
    lines.append("|-------|-------|------:|------:|------:|---------:|---------:|--------:|--------:|")
    rows_with_delta = [(r, abs(f(r["mean_delta_AB"]) or 0.0)) for r in per_model]
    rows_with_delta.sort(key=lambda x: x[1], reverse=True)
    for r, _ in rows_with_delta:
        lines.append(
            f"| {r['model']} | {r['model_class']} | "
            f"{r['mean_score_A'] or '-':>4} | {r['mean_score_B'] or '-':>4} | "
            f"{(f(r['mean_delta_AB']) or 0.0):+.2f} | "
            f"{r['refusal_rate_A']} | {r['refusal_rate_B']} | "
            f"{r['mean_hedge_ratio_A']} | {r['mean_hedge_ratio_B']} |"
        )
    lines.append("")

    # Model class means
    lines.append("## Per-class means (Δ(B−A))")
    lines.append("")
    class_means = summary.get("per_model_class_means", {})
    for cls, mean in sorted(class_means.items(), key=lambda x: -abs(x[1])):
        lines.append(f"- **{cls}**: {mean:+.3f}")
    lines.append("")

    # Pattern findings
    lines.append("## Signal patterns")
    lines.append("")
    lines.append(f"- **Moral-essay signatures** (score=3 + hedge>0.4 in B): {summary.get('moral_essay_signature_count', 0)}")
    lines.append(f"- **Refusal cliffs** (A scored, B refused): {summary.get('refusal_cliff_count', 0)}")
    lines.append("")

    lines.append("## Run metadata")
    lines.append("")
    lines.append(f"- Records: {summary.get('n_records', 0)}")
    lines.append(f"- Models attempted: {summary.get('n_models_attempted', 0)}")
    lines.append(f"- Models completed: {summary.get('n_models_completed', 0)}")
    lines.append("")

    lines.append("## Interpretation guide")
    lines.append("")
    lines.append("- **Δ > +1.0**: the model masks heavily — institutional under fairness, skeptical when asked directly. Strong signal of bias suppression by safety/fairness layer.")
    lines.append("- **Δ ≈ 0**: model's position is stable across the unmasking. May be genuinely balanced OR uniformly biased in one direction.")
    lines.append("- **Δ < −1.0**: model becomes MORE institutional when asked for personal view (unusual — typically a sign of strong RLHF imprint).")
    lines.append("- **High refusal rate in B**: the model refuses to take a personal position when the fairness prompt is stripped — a different bias signature than +2.0 deltas.")
    lines.append("- **Hedge ratio**: words inside hedge constructions / total words. >0.4 with score=3 is the 'moral essay' mode flagged in v1.")

    out = run_dir / "REPORT.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out}")
    # Skip stdout preview — Windows console (cp1252) chokes on Delta U+0394.
    # Read the REPORT.md file directly to view.
    return 0


if __name__ == "__main__":
    sys.exit(main())
