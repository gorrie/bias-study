#!/usr/bin/env python3
"""Single source of truth for judgement-tool sweep state.

Reads the data directly. Prints a coverage matrix per method × run. Use this
BEFORE re-running any sweep skill and BEFORE updating any prose status doc —
the data is the ground truth, not the doc.

Designed to run from either:
  - The bias-study-release mirror (github.com/gorrie/bias-study)
  - The upstream evil-robots-series/research/bias-study/ directory

Auto-locates the data directory by walking up from the script's location and
looking for the first `runs/` containing `*/raw/` files. If that fails it tries
the upstream canonical path as a fallback.

Usage:
    python scripts/sweep_status.py
    python scripts/sweep_status.py --gaps-only
    python scripts/sweep_status.py --json
    python scripts/sweep_status.py --data-dir /path/to/bias-study
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable

# Methods checked. ULTRAPLINIAN-4 baseline scores live in scored/.
# Column labels are ASCII-only — pipe-friendly, no unicode.
METHODS = [
    ("scored",                    "ULTRAPLINIAN-4 baseline (M1)", 1),
    ("scored-abliterated-gemma",  "abliterated-gemma (M2)",       2),
    ("scored-grok-solo",          "grok-solo (M4)",                4),
    ("scored-adversarial-pair",   "adversarial-pair (M5)",         5),
    ("scored-reversed-rubric",    "reversed-rubric (M6)",          6),
    ("scored-blind-condition",    "blind-condition (M7)",          7),
]

# Pre-registered run set — must match RUNS in scripts/run_all_judge_methods.sh.
# Auxiliary runs (variance, timeseries, augmentation, cn-expansion, unmask-gradient)
# are intentionally excluded — they are NOT part of the cross-method pre-registration,
# and including them would violate anti-HARKing discipline.
PRE_REGISTERED_RUNS = [
    "2026-05-25-full",
    "2026-05-27-paraphrase",
    "2026-05-27-ood",
    "2026-05-27-reversed-premise",
    "2026-05-27-abliteration",
    "2026-05-27-g0dm0d3",
    "2026-05-27-abliteration-controls",
]

# Two directory conventions exist in this project:
#   - bias-study-release (github.com/gorrie/bias-study) uses `data/`
#   - the internal evil-robots-series working copy uses `runs/`
# Probe in publication-first order: release convention before working-copy convention.
RUN_DIR_CANDIDATES = ("data", "runs")


def _has_runs(root: Path) -> str | None:
    """Return the run-dir name (data or runs) if root contains pre-registered raw data."""
    for name in RUN_DIR_CANDIDATES:
        if (root / name).is_dir() and any((root / name).glob("*/raw/*.jsonl")):
            return name
    return None


def locate_data_dir(explicit: Path | None) -> tuple[Path, str]:
    """Return (study_root, run_dir_name) — e.g. (bias-study-release, 'data')."""
    if explicit:
        root = explicit.resolve()
        name = _has_runs(root)
        if name:
            return root, name
        raise FileNotFoundError(f"{root} has no data/<run>/raw/ or runs/<run>/raw/ children")
    here = Path(__file__).resolve().parent
    # Walk up from the script's location.
    for candidate in (here.parent, *here.parents):
        name = _has_runs(candidate)
        if name:
            return candidate, name
    raise FileNotFoundError(
        "Could not locate bias-study data. Pass --data-dir or run from a directory "
        "whose ancestor contains data/<date>/raw/*.jsonl (release convention) or "
        "runs/<date>/raw/*.jsonl (upstream convention)."
    )


def count_jsonl(d: Path) -> int:
    return len(list(d.glob("*.jsonl"))) if d.is_dir() else 0


def count_classified(d: Path) -> int:
    """Count records where score_classifier is not None across all jsonl in d."""
    if not d.is_dir():
        return 0
    total = 0
    for f in d.glob("*.jsonl"):
        try:
            with f.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        r = json.loads(line)
                        if r.get("score_classifier") is not None:
                            total += 1
                    except json.JSONDecodeError:
                        pass
        except OSError:
            pass
    return total


def gather_runs(data_dir: Path, run_dir_name: str, all_runs: bool = False) -> list[Path]:
    base = data_dir / run_dir_name
    if all_runs:
        return sorted([
            p for p in base.iterdir()
            if p.is_dir() and (p / "raw").is_dir() and not p.name.startswith("_")
        ])
    return [base / name for name in PRE_REGISTERED_RUNS if (base / name / "raw").is_dir()]


def collect(data_dir: Path, run_dir_name: str, all_runs: bool = False) -> dict:
    runs = gather_runs(data_dir, run_dir_name, all_runs=all_runs)
    out: dict = {"data_dir": str(data_dir), "run_dir": run_dir_name,
                 "runs": {}, "summary": {},
                 "scope": "all-runs" if all_runs else "pre-registered"}
    for run in runs:
        raw_n = count_jsonl(run / "raw")
        scored_n = count_jsonl(run / "scored")
        # Records in the primary scored/ — used as the "expected records" benchmark
        primary_records = sum(
            sum(1 for line in f.open(encoding="utf-8") if line.strip())
            for f in (run / "scored").glob("*.jsonl")
        ) if (run / "scored").is_dir() else 0
        entry: dict = {"raw_files": raw_n, "primary_records": primary_records, "methods": {}}
        for dir_name, label, _ in METHODS:
            n_files = count_jsonl(run / dir_name)
            n_classified = count_classified(run / dir_name)
            complete = n_files == raw_n and n_files > 0
            entry["methods"][dir_name] = {
                "label": label,
                "files": n_files,
                "files_expected": raw_n,
                "records_classified": n_classified,
                "complete": complete,
            }
        out["runs"][run.name] = entry

    # Cross-cutting summary
    method_complete: dict[str, dict] = {}
    for dir_name, label, num in METHODS:
        runs_complete = 0
        runs_total = 0
        files_complete = 0
        files_expected = 0
        for r in out["runs"].values():
            runs_total += 1
            m = r["methods"][dir_name]
            if m["complete"]:
                runs_complete += 1
            files_complete += m["files"]
            files_expected += m["files_expected"]
        method_complete[dir_name] = {
            "label": label,
            "method_number": num,
            "runs_complete": runs_complete,
            "runs_total": runs_total,
            "files_complete": files_complete,
            "files_expected": files_expected,
            "complete_all_runs": runs_complete == runs_total and runs_total > 0,
        }
    out["summary"]["methods"] = method_complete

    # Cross-method analysis output check — probe both naming conventions for charts dir
    aggregated = data_dir / run_dir_name / "_aggregated"
    charts_candidates = [
        data_dir / "results" / "charts",
        data_dir / "charts",
        data_dir / "website" / "static" / "images" / "bias-study",  # upstream Hugo path
    ]
    out["summary"]["cross_method_outputs"] = {
        "cross-method-runs-index.json": (aggregated / "cross-method-runs-index.json").exists(),
        "judge-methods-run.log": (aggregated / "judge-methods-run.log").exists(),
        "charts_dir": next((str(p) for p in charts_candidates if p.is_dir()), "MISSING"),
    }

    return out


def print_table(state: dict, gaps_only: bool = False) -> None:
    method_dirs = [m[0] for m in METHODS]
    short_label = {m[0]: m[1] for m in METHODS}

    scope_note = ("PRE-REGISTERED RUN SET (7 runs)"
                  if state["scope"] == "pre-registered"
                  else "ALL RUNS (includes auxiliary; not pre-registered)")
    print(f"# Sweep state ({scope_note})")
    print(f"# Data dir: {state['data_dir']} (run subdir: {state['run_dir']}/)")
    print()
    print("## Per-method per-run coverage")
    print()
    # Header
    hdr = f"{'run':40s}  {'raw':>5s}  " + "  ".join(f"{short_label[m][:24]:>24s}" for m in method_dirs)
    print(hdr)
    print("-" * len(hdr))
    for run_name, run_info in state["runs"].items():
        raw_n = run_info["raw_files"]
        if gaps_only and all(run_info["methods"][m]["complete"] for m in method_dirs):
            continue
        cells = []
        for m in method_dirs:
            info = run_info["methods"][m]
            mark = "OK" if info["complete"] else ("GAP" if info["files"] < info["files_expected"] else "?")
            cells.append(f"{info['files']:>3d}/{info['files_expected']:<3d} {mark:>5s}")
        print(f"{run_name:40s}  {raw_n:>5d}  " + "  ".join(f"{c:>24s}" for c in cells))
    print()
    print("## Method totals (across the runs above)")
    print()
    print(f"{'method':32s}  {'runs':>10s}  {'files':>14s}  {'status':>14s}")
    print("-" * 76)
    for m_dir, info in state["summary"]["methods"].items():
        runs = f"{info['runs_complete']}/{info['runs_total']}"
        files = f"{info['files_complete']}/{info['files_expected']}"
        status = "COMPLETE" if info["complete_all_runs"] else "INCOMPLETE"
        print(f"{short_label[m_dir]:32s}  {runs:>10s}  {files:>14s}  {status:>14s}")
    print()
    print("## Downstream-analysis outputs")
    print()
    for name, present in state["summary"]["cross_method_outputs"].items():
        mark = "OK" if present else "MISSING"
        print(f"  {mark:>8s}  {name}")
    print()

    # Next-step recommendation
    methods_complete = all(
        info["complete_all_runs"]
        for info in state["summary"]["methods"].values()
    )
    cross_method_done = state["summary"]["cross_method_outputs"]["cross_method_report.json"]
    if not methods_complete:
        incomplete = [
            (info["method_number"], info["label"])
            for info in state["summary"]["methods"].values()
            if not info["complete_all_runs"]
        ]
        print("## NEXT STEP")
        print(f"  Run the missing sweep(s): {incomplete}")
        print("  Skills: api-judge-sweep (Methods 4-7) / abliterated-judge-sweep (Method 2)")
    elif not cross_method_done:
        print("## NEXT STEP")
        print("  All five methods complete. Run cross-method-analysis:")
        print("    python scripts/cross_method_report.py --all-runs > runs/_aggregated/cross-method-report.json")
        print("    python scripts/generate_charts.py --all-charts --out results/charts/")
    else:
        print("## NEXT STEP")
        print("  Cross-method outputs exist. Verify dates, then proceed to bias-study-report skill")
        print("  for CI/FDR/agreement stats and final publish gate.")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--data-dir", type=Path, default=None,
                   help="Override data directory. Defaults to auto-locate.")
    p.add_argument("--gaps-only", action="store_true",
                   help="Print only runs that have one or more incomplete methods.")
    p.add_argument("--all-runs", action="store_true",
                   help="Include auxiliary runs (variance, timeseries, augmentation, etc.). "
                        "Default is the pre-registered set only — anti-HARKing discipline "
                        "means cross-method analysis must be scoped to the pre-registration.")
    p.add_argument("--json", action="store_true",
                   help="Emit machine-readable JSON instead of the table.")
    args = p.parse_args()

    try:
        data_dir, run_dir_name = locate_data_dir(args.data_dir)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 2

    state = collect(data_dir, run_dir_name, all_runs=args.all_runs)
    if args.json:
        print(json.dumps(state, indent=2))
    else:
        print_table(state, gaps_only=args.gaps_only)
    return 0


if __name__ == "__main__":
    sys.exit(main())
