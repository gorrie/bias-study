#!/usr/bin/env python3
"""Cross-run aggregator for longitudinal drift analysis.

Pulls per-model.csv from every run dir, joins into a single drift dataset.
For each vendor with multiple versioned models tested, produces an
intra-vendor arc (mean_delta_AB by version) suitable for plotting.

Output:
    runs/_aggregated/drift_timeseries.csv  — all models flattened with version/family
    runs/_aggregated/vendor_arcs.md        — per-vendor narrative with arc data

Usage:
    python drift_timeseries.py
    python drift_timeseries.py --runs 2026-05-25-full,2026-05-26-augmentation,2026-05-26-timeseries
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
STUDY_DIR = SCRIPT_DIR.parent
RUNS_DIR = STUDY_DIR / "data"

# Family + version parsing — extracts vendor and version number from model ID
# Returns (family, version_sort_key, version_label)
VERSION_PATTERNS = [
    # anthropic/claude-opus-4.7 -> family=claude-opus, version=4.7
    (re.compile(r"^anthropic/claude-opus-(\d+(?:\.\d+)?(?:-fast)?)$"),
     "claude-opus", lambda m: (float(m.group(1).replace("-fast", "")), m.group(1))),

    # anthropic/claude-sonnet-4.6
    (re.compile(r"^anthropic/claude-sonnet-(\d+(?:\.\d+)?)$"),
     "claude-sonnet", lambda m: (float(m.group(1)), m.group(1))),

    # openai/gpt-X
    (re.compile(r"^openai/gpt-(\d+(?:\.\d+)?)$"),
     "openai-gpt", lambda m: (float(m.group(1)), m.group(1))),

    # google/gemini-X
    (re.compile(r"^google/gemini-(\d+(?:\.\d+)?)(?:-(?:pro|flash|flash-lite|pro-preview|flash-preview|pro-image-preview))?(?:-001|-preview)?$"),
     "google-gemini", lambda m: (float(m.group(1)), m.group(0).replace("google/gemini-", ""))),

    # google/gemma-X-NB-it
    (re.compile(r"^google/gemma-(\d+)-(\d+)b-it$"),
     "google-gemma", lambda m: (float(m.group(1)) + int(m.group(2)) / 1000, f"{m.group(1)}-{m.group(2)}b")),

    # gemma2:latest (local)
    (re.compile(r"^gemma2:latest$"),
     "google-gemma", lambda m: (2.009, "2-9b-local")),

    # deepseek/deepseek-chat-vX or deepseek/deepseek-chat / deepseek-vX or /r1
    (re.compile(r"^deepseek/deepseek-(chat|v3|v3\.1|v3\.2|chat-v3-0324|chat-v3\.1|v3\.1-terminus|v3\.2-exp|v3\.2-speciale|r1|r1-0528)(.*)$"),
     "deepseek", lambda m: (
         3.0 if m.group(1) == "chat" else
         3.0 if m.group(1) == "chat-v3-0324" else
         3.1 if "v3.1" in m.group(1) else
         3.2 if "v3.2" in m.group(1) else
         3.5 if m.group(1).startswith("r1") else
         3.0,
         m.group(1),
     )),

    # deepseek/deepseek-chat-v3.1 etc.
    (re.compile(r"^deepseek/deepseek-chat-v(\d+\.\d+)(?:-terminus)?$"),
     "deepseek", lambda m: (float(m.group(1)), m.group(1))),

    # x-ai/grok-X.Y
    (re.compile(r"^x-ai/grok-(\d+\.\d+)$"),
     "xai-grok", lambda m: (float(m.group(1)), m.group(1))),

    # z-ai/glm-X.Y
    (re.compile(r"^z-ai/glm-(\d+(?:\.\d+)?)(?:-air|-flash)?$"),
     "zhipuai-glm", lambda m: (float(m.group(1)), m.group(1))),

    # moonshotai/kimi-kN or kN-thinking or k2.6
    (re.compile(r"^moonshotai/kimi-(k\d+(?:\.\d+)?)(-thinking|-0905)?$"),
     "moonshot-kimi", lambda m: (float(m.group(1)[1:]) + (0.001 if m.group(2) == "-thinking" else 0), m.group(1) + (m.group(2) or ""))),

    # qwen/qwen-2.5-XB or qwen/qwen3-XB(-thinking)
    (re.compile(r"^qwen/qwen-?(2\.5|3)(?:-(\d+)b)?(?:-a\d+b)?(.*)$"),
     "qwen", lambda m: (float(m.group(1)) + (int(m.group(2)) / 1000 if m.group(2) else 0), f"{m.group(1)}-{m.group(2) or '?'}b{m.group(3) or ''}")),

    # qwen2.5:14b local
    (re.compile(r"^qwen2\.5:(\d+)b$"),
     "qwen", lambda m: (2.5 + int(m.group(1)) / 1000, f"2.5-{m.group(1)}b-local")),

    # baidu/ernie-X.Y
    (re.compile(r"^baidu/ernie-(\d+\.\d+)-"),
     "baidu-ernie", lambda m: (float(m.group(1)), m.group(0).replace("baidu/ernie-", ""))),

    # bytedance-seed/seed-X.Y
    (re.compile(r"^bytedance-seed/seed-(\d+\.\d+)(.*)$"),
     "bytedance-seed", lambda m: (float(m.group(1)), m.group(0).replace("bytedance-seed/seed-", ""))),

    # mistralai/mistral-X
    (re.compile(r"^mistralai/mistral-(\w+)$"),
     "mistral", lambda m: (0.0, m.group(1))),

    # meta-llama/llama-X-Y
    (re.compile(r"^meta-llama/llama-(\d+)-(\w+)$"),
     "meta-llama", lambda m: (float(m.group(1)), f"{m.group(1)}-{m.group(2)}")),

    # phi4 local
    (re.compile(r"^phi4:latest$"),
     "microsoft-phi", lambda m: (4.0, "4-latest-local")),
]


def parse_model(model_id: str) -> tuple[str, float, str] | None:
    """Return (family, sort_key, version_label) or None."""
    for pat, family, extract in VERSION_PATTERNS:
        m = pat.match(model_id)
        if m:
            sort_key, label = extract(m)
            return (family, sort_key, label)
    return None


def load_run_per_model(run_dir: Path) -> list[dict]:
    csv_path = run_dir / "aggregated" / "per-model.csv"
    if not csv_path.exists():
        return []
    with csv_path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def collect_all_runs(runs: list[str] | None) -> list[dict]:
    """Pull per-model rows from every run, tagged with run_date."""
    all_rows = []
    if runs:
        run_dirs = [RUNS_DIR / r for r in runs if (RUNS_DIR / r / "aggregated").exists()]
    else:
        run_dirs = sorted([d for d in RUNS_DIR.iterdir()
                          if d.is_dir() and (d / "aggregated").exists()])

    for rd in run_dirs:
        rows = load_run_per_model(rd)
        for r in rows:
            r["run_date"] = rd.name
            all_rows.append(r)
    return all_rows


def build_drift_timeseries(rows: list[dict]) -> dict:
    """Group by family, sort by version, emit arc data."""
    by_family: dict[str, list[dict]] = defaultdict(list)
    unmatched = []
    for r in rows:
        parsed = parse_model(r["model"])
        if not parsed:
            unmatched.append(r["model"])
            continue
        family, sort_key, label = parsed
        try:
            delta = float(r["mean_delta_AB"]) if r.get("mean_delta_AB") else None
        except ValueError:
            delta = None
        by_family[family].append({
            "model": r["model"],
            "version_label": label,
            "sort_key": sort_key,
            "mean_delta_AB": delta,
            "mean_score_A": float(r["mean_score_A"]) if r.get("mean_score_A") else None,
            "mean_score_B": float(r["mean_score_B"]) if r.get("mean_score_B") else None,
            "model_class": r.get("model_class"),
            "n_questions": r.get("n_questions_scored"),
            "run_date": r.get("run_date"),
        })

    # Sort each family by sort_key
    for family in by_family:
        by_family[family].sort(key=lambda x: x["sort_key"])

    return {"families": dict(by_family), "unmatched": unmatched}


def write_csv(rows: list[dict], path: Path) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_vendor_arcs_md(families: dict, path: Path) -> None:
    lines = []
    lines.append("# Vendor Drift Arcs")
    lines.append("")
    lines.append("Per-vendor intra-family version arcs from all runs combined. "
                 "Each table shows mean Delta(B-A) progression by version (sorted oldest -> newest).")
    lines.append("")

    # Sort families by number of versions descending (most data first)
    for family, versions in sorted(families.items(), key=lambda x: -len(x[1])):
        if len(versions) < 2:
            continue  # need at least 2 versions for an arc
        lines.append(f"## {family} ({len(versions)} versions)")
        lines.append("")
        lines.append("| version | model | mean A | mean B | Delta(B-A) | n questions | run |")
        lines.append("|---------|-------|-------:|-------:|----------:|------------:|-----|")
        for v in versions:
            dlt = v["mean_delta_AB"]
            a = v["mean_score_A"]
            b = v["mean_score_B"]
            a_str = f"{a:.2f}" if a is not None else "-"
            b_str = f"{b:.2f}" if b is not None else "-"
            dlt_str = f"{dlt:+.2f}" if dlt is not None else "-"
            lines.append(
                f"| {v['version_label']} | `{v['model']}` | "
                f"{a_str} | {b_str} | {dlt_str} | "
                f"{v['n_questions']} | {v['run_date']} |"
            )

        # Arc summary
        deltas = [v["mean_delta_AB"] for v in versions if v["mean_delta_AB"] is not None]
        if len(deltas) >= 2:
            arc_dir = deltas[-1] - deltas[0]
            arc_label = (
                "**unmasking increasing over versions**" if arc_dir > 0.2
                else "**unmasking decreasing over versions**" if arc_dir < -0.2
                else "**stable across versions**"
            )
            lines.append("")
            lines.append(f"Arc direction: {arc_label} (delta from oldest to newest = {arc_dir:+.2f})")
        lines.append("")

    if any(len(versions) < 2 for versions in families.values()):
        lines.append("## Single-version families (no arc)")
        lines.append("")
        singletons = sorted([f for f, vs in families.items() if len(vs) < 2])
        lines.append(", ".join(f"`{f}`" for f in singletons))
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Cross-run aggregator for drift analysis.")
    parser.add_argument("--runs", help="Comma-separated run names (default: all runs with aggregated/)")
    args = parser.parse_args()

    runs = [r.strip() for r in args.runs.split(",")] if args.runs else None
    rows = collect_all_runs(runs)
    if not rows:
        print("No runs with aggregated/ found", file=sys.stderr)
        return 2

    print(f"Collected {len(rows)} per-model rows across runs")

    out_dir = RUNS_DIR / "_aggregated"
    write_csv(rows, out_dir / "drift_timeseries.csv")

    series = build_drift_timeseries(rows)
    write_vendor_arcs_md(series["families"], out_dir / "vendor_arcs.md")

    print(f"Wrote {out_dir}/drift_timeseries.csv")
    print(f"Wrote {out_dir}/vendor_arcs.md")
    print()
    print("Family coverage (versions per family):")
    for family, versions in sorted(series["families"].items(), key=lambda x: -len(x[1])):
        print(f"  {family}: {len(versions)} versions")
    if series["unmatched"]:
        print()
        print(f"Unmatched models (need pattern): {series['unmatched']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
