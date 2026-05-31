#!/usr/bin/env python3
"""Generate X-launch chart assets from sweep + ci_analysis output.

Reads:
    runs/<date>/cross-method/{per-method-summary, cross-method-agreement,
                              contamination-delta, per-topic-disagreement}.json

Writes:
    evil-robots-series/website/static/images/bias-study/
        forest-plot-per-model.png      # Variant A + D hero
        agreement-heatmap.png          # Variant B hero
        escalation-ladder.png          # Variant C hero (3-panel)
        paraphrase-robustness.png      # within-leg FDR survivors
        contamination-delta.png        # judge-bias quantification

All charts 1200x675 (X-card aspect), PNG, dark background to match the
evilrobots.lol brand chrome.

Usage:
    python generate_charts.py 2026-05-25-full           # main study
    python generate_charts.py 2026-05-27-paraphrase     # paraphrase robustness
    python generate_charts.py --all-charts              # everything
"""
from __future__ import annotations

import argparse
import json
import sys
import pathlib
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # non-interactive, headless-safe
import matplotlib.pyplot as plt

SCRIPT_DIR = Path(__file__).parent
STUDY_DIR = SCRIPT_DIR.parent
# Two directory conventions in the project:
#   - publication-canonical (github.com/gorrie/bias-study) uses `data/<run>/`
#   - internal working copy at evil-robots-series/research/bias-study/ uses `runs/<run>/`
# Auto-detect which one this checkout uses.
RUN_DIR_NAME = "data" if (STUDY_DIR / "data").is_dir() else "runs"
# Default chart output: release-local `results/charts/` (works for any clone).
# Overridden by --out flag; the upstream Hugo path is no longer a default.
DEFAULT_CHART_DIR = STUDY_DIR / "results" / "charts"

# Evil Robots brand chrome
BG = "#0c0c0f"
SURFACE = "#16161a"
ACCENT = "#CC0000"
ACCENT2 = "#88ccff"  # cool blue for secondary series
TEXT = "#e6e6e6"
GRID = "#2a2a2f"

plt.rcParams.update({
    "figure.facecolor": BG,
    "axes.facecolor": SURFACE,
    "axes.edgecolor": GRID,
    "axes.labelcolor": TEXT,
    "axes.titlecolor": TEXT,
    "xtick.color": TEXT,
    "ytick.color": TEXT,
    "grid.color": GRID,
    "text.color": TEXT,
    "font.family": "monospace",
    "font.size": 11,
    "axes.titlesize": 14,
    "axes.titleweight": "bold",
})


def load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def short_model(model: str) -> str:
    """Compact label for plot axes."""
    return model.split("/")[-1].replace("-instruct", "").replace("-chat", "")[:20]


def chart_forest_plot(run_date: str, out_path: Path) -> bool:
    """Per-model A->B delta forest plot under baseline vs anchor method."""
    summary = load_json(STUDY_DIR / RUN_DIR_NAME / run_date / "cross-method" / "per-method-summary.json")
    if not summary:
        print(f"  SKIP forest-plot: no summary at {run_date}")
        return False

    methods = ["ultraplinian-4", "grok-solo"]  # baseline + anchor (post-sweep, can swap)
    models_seen = set()
    for m in methods:
        models_seen.update(summary["method"].get(m, {}).get("models", {}).keys())
    models = sorted(models_seen)
    if not models:
        print(f"  SKIP forest-plot: no model data")
        return False

    fig, ax = plt.subplots(figsize=(12, 6.75), dpi=100)
    y_positions = list(range(len(models)))
    width = 0.4

    for i, method in enumerate(methods):
        m_data = summary["method"].get(method, {}).get("models", {})
        deltas, errs_lo, errs_hi, ys = [], [], [], []
        for j, model in enumerate(models):
            d = m_data.get(model, {}).get("delta_b_minus_a")
            if d is None:
                continue
            deltas.append(d)
            ys.append(j + (-width / 2 if i == 0 else width / 2))
            errs_lo.append(0)  # CI not in delta yet; placeholder
            errs_hi.append(0)
        color = ACCENT if method == "ultraplinian-4" else ACCENT2
        ax.barh(ys, deltas, height=width, color=color, label=method, alpha=0.85)

    ax.set_yticks(y_positions)
    ax.set_yticklabels([short_model(m) for m in models])
    ax.set_xlabel("A → B stance delta (score 1-5)")
    ax.set_title(f"Per-model unmask delta — {run_date}\nBaseline vs anchor judge method")
    ax.axvline(0, color=TEXT, linewidth=0.5, alpha=0.6)
    ax.legend(loc="lower right", facecolor=SURFACE, edgecolor=GRID, labelcolor=TEXT)
    ax.grid(axis="x", alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, facecolor=BG)
    plt.close()
    print(f"  wrote {out_path}")
    return True


def chart_agreement_heatmap(run_date: str, out_path: Path) -> bool:
    """Methods × methods exact-match heatmap."""
    agreement = load_json(STUDY_DIR / RUN_DIR_NAME / run_date / "cross-method" / "cross-method-agreement.json")
    if not agreement or "agreement" not in agreement:
        print(f"  SKIP agreement-heatmap: no agreement at {run_date}")
        return False

    methods = agreement.get("methods", [])
    if len(methods) < 2:
        print(f"  SKIP agreement-heatmap: need >=2 methods")
        return False

    # Build symmetric matrix
    n = len(methods)
    mat = [[1.0 if i == j else None for j in range(n)] for i in range(n)]
    for pair_key, pair_vals in agreement["agreement"].items():
        m1, m2 = pair_key.split(" vs ")
        i, j = methods.index(m1), methods.index(m2)
        rate = pair_vals.get("exact_match_rate")
        if rate is not None:
            mat[i][j] = rate
            mat[j][i] = rate

    fig, ax = plt.subplots(figsize=(12, 6.75), dpi=100)
    plot_mat = [[v if v is not None else 0 for v in row] for row in mat]
    im = ax.imshow(plot_mat, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(methods, rotation=30, ha="right")
    ax.set_yticklabels(methods)
    for i in range(n):
        for j in range(n):
            if mat[i][j] is not None:
                ax.text(j, i, f"{mat[i][j]:.2f}", ha="center", va="center",
                        color="black" if 0.4 < mat[i][j] < 0.8 else TEXT, fontsize=10, fontweight="bold")
    ax.set_title(f"Cross-method exact-match agreement — {run_date}")
    plt.colorbar(im, ax=ax, label="exact-match rate (0-1)")
    plt.tight_layout()
    plt.savefig(out_path, facecolor=BG)
    plt.close()
    print(f"  wrote {out_path}")
    return True


def chart_contamination_delta(run_date: str, out_path: Path) -> bool:
    """Per-model |grok-solo - ULTRAPLINIAN| bar chart with CI error bars."""
    contam = load_json(STUDY_DIR / RUN_DIR_NAME / run_date / "cross-method" / "contamination-delta.json")
    if not contam or "per_model" not in contam:
        print(f"  SKIP contamination-delta: no contam at {run_date}")
        return False

    pm = contam["per_model"]
    models = sorted(pm.keys())
    deltas = [pm[m]["mean_grok_minus_ultraplinian"] for m in models]
    ci_los = [pm[m]["ci"][0] for m in models]
    ci_his = [pm[m]["ci"][1] for m in models]
    err_neg = [d - lo for d, lo in zip(deltas, ci_los)]
    err_pos = [hi - d for d, hi in zip(deltas, ci_his)]

    fig, ax = plt.subplots(figsize=(12, 6.75), dpi=100)
    ys = list(range(len(models)))
    colors = [ACCENT if d > 0 else ACCENT2 for d in deltas]
    ax.barh(ys, deltas, color=colors, alpha=0.85, xerr=[err_neg, err_pos],
            error_kw={"ecolor": TEXT, "elinewidth": 1.2, "capsize": 4})
    ax.set_yticks(ys)
    ax.set_yticklabels([short_model(m) for m in models])
    ax.set_xlabel("Grok-solo − ULTRAPLINIAN-4 mean score delta")
    ax.set_title(f"Judge contamination measurement — {run_date}\nHow much do RLHF consensus judges under-score skepticism?")
    ax.axvline(0, color=TEXT, linewidth=0.5, alpha=0.6)
    ax.grid(axis="x", alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, facecolor=BG)
    plt.close()
    print(f"  wrote {out_path}")
    return True


def chart_paraphrase_robustness(out_path: Path) -> bool:
    """4 FDR-significant models × 3 paraphrases — bars per cell."""
    # Re-uses robustness_checks.within_leg_fdr via direct script invocation
    sys.path.insert(0, str(SCRIPT_DIR))
    from robustness_checks import within_leg_fdr
    result = within_leg_fdr(STUDY_DIR / RUN_DIR_NAME / "2026-05-27-paraphrase", "position", q=0.05)
    pm = result.get("per_model", {})
    if not pm:
        print("  SKIP paraphrase-robustness: no data")
        return False

    paraphrases = ["para1", "para2", "para3"]
    models = sorted(pm.keys())
    fig, ax = plt.subplots(figsize=(12, 6.75), dpi=100)
    width = 0.25
    for i, p in enumerate(paraphrases):
        deltas = [pm[m].get("tests", {}).get(p, {}).get("mean_delta", 0) for m in models]
        survives = [pm[m].get("tests", {}).get(p, {}).get("survives_fdr", False) for m in models]
        xs = [j + (i - 1) * width for j in range(len(models))]
        colors = [ACCENT if s else "#555" for s in survives]
        ax.bar(xs, deltas, width=width, color=colors, label=p, alpha=0.85)
    ax.set_xticks(range(len(models)))
    ax.set_xticklabels([short_model(m) for m in models], rotation=20, ha="right")
    ax.set_ylabel("A → B stance delta")
    ax.set_title("Paraphrase robustness — within-leg BH-FDR survivors\nRed = survives FDR q=0.05; grey = drops")
    ax.axhline(0, color=TEXT, linewidth=0.5, alpha=0.6)
    ax.legend(loc="upper right", facecolor=SURFACE, edgecolor=GRID, labelcolor=TEXT)
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, facecolor=BG)
    plt.close()
    print(f"  wrote {out_path}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate X-launch chart assets.")
    parser.add_argument("run_date", nargs="?", help="Run date (default: 2026-05-25-full)")
    parser.add_argument("--all-charts", action="store_true",
                        help="Generate all chart types from all applicable runs")
    parser.add_argument("--out", type=pathlib.Path, default=None,
                        help="Override output directory (default: results/charts/)")
    args = parser.parse_args()

    chart_dir = args.out if args.out else DEFAULT_CHART_DIR
    chart_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output dir: {chart_dir}")

    if args.all_charts:
        # Main-study charts
        chart_forest_plot("2026-05-25-full", chart_dir / "forest-plot-per-model.png")
        chart_agreement_heatmap("2026-05-25-full", chart_dir / "agreement-heatmap.png")
        chart_contamination_delta("2026-05-25-full", chart_dir / "contamination-delta.png")
        # Paraphrase chart (uses its own analysis path)
        chart_paraphrase_robustness(chart_dir / "paraphrase-robustness.png")
        return 0

    run_date = args.run_date or "2026-05-25-full"
    chart_forest_plot(run_date, chart_dir / f"forest-plot-{run_date}.png")
    chart_agreement_heatmap(run_date, chart_dir / f"agreement-heatmap-{run_date}.png")
    chart_contamination_delta(run_date, chart_dir / f"contamination-delta-{run_date}.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
