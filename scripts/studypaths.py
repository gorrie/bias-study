#!/usr/bin/env python3
"""Shared run-directory resolution and deterministic RNG streams.

TWO PROBLEMS THIS EXISTS TO FIX.

**The directory.** The repo ships `data/`. Four scripts hardcoded `runs/`, printed
`[skip] <run>: no scored/` and exited **0** — so a finished study produced no
confidence intervals and no FDR correction, with no error anywhere, silently voiding
the study's own rule that a delta is reportable only when its CI excludes zero.
Commit `4087bb7` fixed `score.py` and `cross_method_report.py` and missed the rest.
Three ad-hoc resolutions existed (`generate_charts.py`, `sweep_status.py`, and the
hardcodes); this is the one they all call now.

A missing run is an **operator error**, not a no-op. `resolve_run()` raises, and the
callers exit non-zero. A pipeline that returns 0 having computed nothing is how three
days of failures went unremarked.

**The RNG.** `random.seed(20260527)` at import seeded ONE global stream, and
`bootstrap_ci` drew from it sequentially — so the draws a given (run, model) cell
received depended on how many cells were processed before it. Measured: passing the
five main run-dates in reverse order moved **6 of 46 published CI cells**. No verdict
flipped at those values, but the study's gate is binary, so a bound sitting a few
hundredths from zero was decidable by argument order. `stream()` derives an
independent generator per cell from the declared seed, so a cell depends only on its
own data.

The seed itself comes from the run's `manifest.json` (`analysis_seed`) when present,
and falls back to May's `20260527` so the published table stays reproducible. A seed
chosen after seeing the intervals is a researcher degree of freedom; `run_study.py`
writes it at run start, before any response exists.
"""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

STUDY_DIR = Path(__file__).resolve().parent.parent

#: May 2026's seed. Frozen. Used when a run's manifest declares none.
LEGACY_SEED = 20260527


class RunNotFound(Exception):
    """A run directory, or its scored/ subdirectory, is not where it should be."""


def runs_root() -> Path:
    """`data/` in this repo; `runs/` in the predecessor layout."""
    for name in ("data", "runs"):
        p = STUDY_DIR / name
        if p.is_dir():
            return p
    raise RunNotFound(f"neither data/ nor runs/ exists under {STUDY_DIR}")


def resolve_run(run_date: str, *, require_scored: bool = True) -> Path:
    """Return the run directory, raising rather than returning None."""
    root = runs_root()
    d = root / run_date
    if not d.is_dir():
        have = sorted(p.name for p in root.iterdir() if p.is_dir())
        raise RunNotFound(
            f"no run directory {root.name}/{run_date}. Present: {', '.join(have) or '(none)'}")
    if require_scored and not (d / "scored").is_dir():
        raise RunNotFound(
            f"{root.name}/{run_date} exists but has no scored/ — "
            f"score the run before analysing it")
    return d


def manifest(run_date: str) -> dict:
    try:
        p = resolve_run(run_date, require_scored=False) / "manifest.json"
    except RunNotFound:
        return {}
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def analysis_seed(run_date: str) -> int:
    """The run's declared analysis seed, or May's frozen default."""
    v = manifest(run_date).get("analysis_seed")
    if isinstance(v, int):
        return v
    if isinstance(v, str) and v.strip().lstrip("-").isdigit():
        return int(v.strip())
    return LEGACY_SEED


def stream(seed: int, *parts: object) -> random.Random:
    """An independent generator for one cell, derived from the seed and the cell's key.

    Derived by digest rather than by ``hash()``, which is salted per process and would
    make a run irreproducible across invocations.
    """
    key = "\x1f".join([str(seed), *(str(p) for p in parts)])
    digest = hashlib.blake2b(key.encode("utf-8"), digest_size=8).digest()
    return random.Random(int.from_bytes(digest, "big"))
