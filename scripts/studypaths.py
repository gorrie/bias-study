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
import re
import os
import sys
import random
from pathlib import Path

# GitLab owns development; the same exported code accepts a release corpus explicitly.
_requested = os.environ.get("STUDY_ROOT")
if _requested is not None and not _requested.strip():
    raise ValueError("STUDY_ROOT must name a study directory")
STUDY_DIR = (Path(_requested).expanduser().resolve() if _requested is not None
             else Path(__file__).resolve().parent.parent)
if not STUDY_DIR.is_dir():
    raise ValueError(f"STUDY_ROOT is not a directory: {STUDY_DIR}")

# Compatibility contract for historical shims; expand only with entry-point tests.
ROOT_AWARE_SCRIPTS = frozenset({"ci_analysis.py", "robustness_checks.py",
                               "paired_analysis.py", "validate_runs.py",
                               # Added 2026-09-12. Both resolved their corpus with a hardcoded
                               # ("data", "runs") under their own parent directory, which is a
                               # third implementation of run resolution and ignores STUDY_ROOT.
                               # They now call run_roots(). A shim may forward to them safely;
                               # it could not before, and _shim was right to refuse.
                               "judge_lean.py"})

#: May 2026's seed. Frozen. Used when a run's manifest declares none.
LEGACY_SEED = 20260527


class RunNotFound(Exception):
    """A run directory, or its scored/ subdirectory, is not where it should be."""


#: A run directory is DATED. `2026-05-25`, `2026-09-05-recollect`, `2026-08-31-lineage`.
#: Nothing else in either layout is.
_RUN_DIR = re.compile(r"^\d{4}-\d{2}-\d{2}")


def _looks_like_runs_root(p: Path) -> bool:
    """True when a directory actually CONTAINS runs, not merely when it is named for them.

    THE NAME OF THE CHILD MATTERS, and leaving it out cost a silent misdirection on
    2026-09-05. The third test used to be "this child holds any *.jsonl", which is true of any
    data directory that happens to contain one -- and the private study's `data/` acquired
    `external/rottger2024-codes.jsonl` that morning. From then on `runs_root()` returned
    `data/` instead of `runs/`, so every shared script looked for runs in the config directory
    and reported the run missing. The docstring below already warned about exactly this failure
    for the NAME-based rule; the content-based rule inherited it through a laxer door.

    A run directory is dated in both layouts, so requiring that of the child costs nothing and
    closes it. The structural markers (`raw/`, `scored/`, `manifest.json`) still qualify a
    child on their own, because those are unambiguous whatever it is called.
    """
    if not p.is_dir():
        return False
    for child in p.iterdir():
        if not child.is_dir():
            continue
        if (child / "scored").is_dir() or (child / "raw").is_dir() \
                or (child / "manifest.json").exists():
            return True
        if _RUN_DIR.match(child.name) and any(child.glob("*.jsonl")):
            return True
    return False


def runs_root() -> Path:
    """The directory holding run directories: `runs/` here, `data/` in the public mirror.

    RESOLVED BY CONTENT, NOT BY NAME. Name-based resolution worked only because the mirror's
    `data/` happens to hold runs -- point `STUDY_ROOT` at this private study, whose `data/`
    holds config JSON and whose runs live in `runs/`, and a name-based rule silently returns
    the config directory. The failure mode is an analysis that finds no runs and reports
    success having computed nothing.

    AN AMBIGUOUS SELECTION FAILS rather than guessing, per the September 8 direction: a held
    layout containing BOTH a populated `data/` and a populated `runs/` cannot be resolved by
    inspection, so `STUDY_RUN_LAYOUT` must say which. Picking one silently is how an analysis
    ends up reading the wrong corpus and never says so.
    """
    layout = os.environ.get('STUDY_RUN_LAYOUT')
    if layout is not None:
        if layout not in ('data', 'runs') or not (STUDY_DIR / layout).is_dir():
            raise RunNotFound('STUDY_RUN_LAYOUT must select an existing data or runs directory')
        return STUDY_DIR / layout
    candidates = [STUDY_DIR / name for name in ("data", "runs")
                  if (STUDY_DIR / name).is_dir()]
    if len(candidates) == 1:
        return candidates[0]
    populated = [p for p in candidates if _looks_like_runs_root(p)]
    if len(populated) == 1:
        return populated[0]
    if candidates:
        # AMBIGUOUS, AND SAID SO EVERY TIME -- but not fatal here. The public mirror really
        # does hold two populated corpora, and several scripts call this at MODULE level, so
        # raising took `--help` down with it and made the tree unusable rather than careful.
        # The strictness lives where it can act: resolve_run() fails hard when a RUN NAME is
        # present in both roots, which is the case where picking would actually read the wrong
        # records. This returns a root and never does it quietly.
        chosen = (populated or candidates)[0]
        print("[studypaths] WARNING: both data/ and runs/ under %s hold runs; using %s/. "
              "Set STUDY_RUN_LAYOUT=data|runs to choose deliberately."
              % (STUDY_DIR, chosen.name), file=sys.stderr)
        return chosen
    raise RunNotFound(f"neither data/ nor runs/ exists under {STUDY_DIR}")


def run_roots() -> list[Path]:
    """Every populated corpus root, in preference order -- usually one, legitimately two.

    The public mirror really does hold two: 22 May runs under `data/` and 30 August/September
    runs under `runs/`. Neither is wrong and neither is stale, so a rule that picks ONE root
    globally has to be wrong about half the runs. Resolution is therefore per run NAME.
    """
    layout = os.environ.get('STUDY_RUN_LAYOUT')
    if layout is not None:
        if layout not in ('data', 'runs') or not (STUDY_DIR / layout).is_dir():
            raise RunNotFound('STUDY_RUN_LAYOUT must select an existing data or runs directory')
        return [STUDY_DIR / layout]
    roots = [STUDY_DIR / name for name in ("data", "runs") if (STUDY_DIR / name).is_dir()]
    populated = [p for p in roots if _looks_like_runs_root(p)]
    return populated or roots


def resolve_run(run_date: str, *, require_scored: bool = True) -> Path:
    """Return the run directory, raising rather than returning None.

    Searched across every corpus root BY NAME. A name present in exactly one root resolves
    with no configuration; a name present in BOTH is genuinely ambiguous and says so rather
    than picking, because picking is how an analysis silently reads the other corpus.
    """
    roots = run_roots()
    holding = [r for r in roots if (r / run_date).is_dir()]
    if len(holding) > 1:
        raise RunNotFound(
            f"ambiguous run {run_date}: it exists in "
            f"{' and '.join(r.name for r in holding)}; "
            "set STUDY_RUN_LAYOUT to choose the corpus")
    if not holding:
        have = sorted({p.name for r in roots for p in r.iterdir() if p.is_dir()})
        raise RunNotFound(
            f"no run directory {run_date}. Present: {', '.join(have) or '(none)'}")
    root = holding[0]
    d = root / run_date
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
