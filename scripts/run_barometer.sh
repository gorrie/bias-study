#!/usr/bin/env bash
# run_barometer.sh — ONE-COMMAND full-ladder bias-study pass (the "model bias barometer").
#
# Runs the force-escalation ladder end to end for a dated run, then scores + reports, so a
# quarterly pass (or an outside replicator) is a single invocation. Rungs are independently
# skippable via flags — the prompt rung needs only an OpenRouter key; the weight rung needs a
# 24 GB GPU + the obliteratus:gpu image; the pipeline rung (G0DM0D3) is not yet wired (WP2).
#
# Usage:
#   bash scripts/run_barometer.sh <run-date> [--prompt] [--weights] [--all] [--models <csv>]
# Examples:
#   bash scripts/run_barometer.sh 2026-08-01 --prompt        # cross-section + dose-response + reversed
#   bash scripts/run_barometer.sh 2026-08-01 --weights       # abliteration sweep (open-weight families)
#   bash scripts/run_barometer.sh 2026-08-01 --all           # both rungs
#
# Reproducibility: immutable runs/<run-date>/, deterministic-seed analysis, 4-judge median.
# See DEVELOPER.md for the full toolchain. Secrets (OPENROUTER_API_KEY) resolve from the
# environment first, then a repo-root .env (see .env.example) — never committed.
set -u
cd "$(dirname "$0")/.."          # -> bias-study/
PY="${PYTHON:-python3}"
RUN="${1:?usage: run_barometer.sh <run-date> [--prompt|--weights|--all]}"; shift || true
DO_PROMPT=0; DO_WEIGHTS=0
MODELS="default-frontier"
JUDGES="anthropic/claude-haiku-4.5,openai/gpt-4.1,google/gemini-2.5-flash,deepseek/deepseek-v3.2"
while [ $# -gt 0 ]; do case "$1" in
  --prompt) DO_PROMPT=1;; --weights) DO_WEIGHTS=1;; --all) DO_PROMPT=1; DO_WEIGHTS=1;;
  --models) shift; MODELS="$1";; *) echo "unknown arg: $1";; esac; shift; done
[ $DO_PROMPT -eq 0 ] && [ $DO_WEIGHTS -eq 0 ] && { echo "pick --prompt, --weights, or --all"; exit 2; }

# Weight rung needs Docker + an NVIDIA GPU (CUDA). Detect up front so we skip it with a
# clear message on non-GPU hosts (e.g. macOS) instead of failing cryptically mid-run.
have_docker_gpu() {
  command -v docker >/dev/null 2>&1 || return 1
  [ -n "${DOCKER_GPU_FLAG:-}" ] && return 0
  docker info --format '{{json .Runtimes}}' 2>/dev/null | grep -q nvidia && return 0
  command -v nvidia-smi >/dev/null 2>&1
}

echo "===== BAROMETER PASS $RUN (prompt=$DO_PROMPT weights=$DO_WEIGHTS) ====="

# 0. pre-flight (known-good state)
echo "[0] prep — verify env + toolchain (bias-study-prep)"
# OPENROUTER_API_KEY must resolve from the environment or a repo-root .env (see .env.example).
[ -n "${OPENROUTER_API_KEY:-}" ] \
  || { [ -f .env ] && grep -q '^OPENROUTER_API_KEY=.\+' .env; } \
  || { echo "  MISSING OPENROUTER_API_KEY — export it or set it in a repo-root .env (see .env.example)"; exit 2; }

# 1. PROMPT RUNG — cross-section A/B + dose-response gradient + reversed-premise control
if [ $DO_PROMPT -eq 1 ]; then
  echo "[1] prompt rung: cross-section + reversed-premise"
  $PY scripts/run_study.py --positions mild,neutral,pointed,reversed --models "$MODELS" --conditions A,B --date "$RUN" \
    || echo "  prompt-rung run had failures (continuing)"
fi

# 2. WEIGHT RUNG — abliteration sweep over open-weight families (GPU + obliteratus:gpu)
if [ $DO_WEIGHTS -eq 1 ]; then
  if have_docker_gpu; then
    echo "[2] weight rung: abliteration sweep (edit SWEEP=() in run_abliteration_sweep.sh to add families)"
    OUT_DATE="$RUN" bash scripts/run_abliteration_sweep.sh || echo "  weight-rung sweep had failures (continuing)"
  else
    echo "[2] weight rung SKIPPED — needs Docker + an NVIDIA GPU (CUDA), not available here."
    echo "    It runs only on a Linux GPU host; macOS/Apple Silicon cannot abliterate locally."
    echo "    Run on a GPU box, or set DOCKER_GPU_FLAG to override the detection."
    DO_WEIGHTS=0
  fi
fi

# 3. SCORE (4-judge ULTRAPLINIAN median) — only if a rung produced raw data to score
echo "[3] score (4-judge panel)"
if ls "data/$RUN/raw/"*.jsonl >/dev/null 2>&1; then
  $PY scripts/score.py "$RUN" --judge "$JUDGES" || { echo "  scoring failed"; exit 1; }
else
  echo "  no raw data in data/$RUN/raw/ — nothing to score, skipping."
fi

# 4. REPORT — CIs, FDR, length control, agreement, abliteration effect-check (bias-study-report)
echo "[4] report: CIs / FDR / agreement / effect-check"
# Both take the run-date. They were called with none -- a usage error -- and the
# `|| echo note` swallowed it, so this step printed reassurance and computed nothing.
$PY scripts/ci_analysis.py "$RUN"       || { echo "  ci_analysis FAILED for $RUN"; exit 1; }
$PY scripts/robustness_checks.py "$RUN" || { echo "  robustness_checks FAILED for $RUN"; exit 1; }
$PY scripts/abliteration_effect_check.py --out-date "$RUN" 2>/dev/null || true

echo "===== PASS $RUN COMPLETE — review, then update WRITEUP + permalink, then gated publish ====="
echo "Next: diff per-model deltas vs the prior quarter's runs/<prev>/ (the barometer time series)."
