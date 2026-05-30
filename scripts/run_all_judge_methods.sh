#!/usr/bin/env bash
# Run all implemented judge methods through all bias-study runs.
#
# Methods (in execution order, cheap-first): grok-solo, adversarial-pair,
# reversed-rubric, blind-condition.
#
# Runs: main study (2026-05-25-full) + 5 rigor legs (paraphrase, ood,
# reversed-premise, abliteration, g0dm0d3, abliteration-controls).
#
# Output: runs/<date>/scored-<method>/<model>.jsonl per method × run.
# Progress + per-cell timings: runs/_aggregated/judge-methods-run.log
#
# ETA: ~10 hours sequential wall time (~3 hours for the cheapest method,
# ~3 hours each for reversed-rubric and blind-condition).

set -uo pipefail  # NOT -e — single API failure shouldn't kill the whole sweep

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
STUDY_DIR="$( dirname "$SCRIPT_DIR" )"
LOG="$STUDY_DIR/runs/_aggregated/judge-methods-run.log"
mkdir -p "$(dirname "$LOG")"

PYTHON=/c/Python314/python.exe

METHODS=(grok-solo adversarial-pair reversed-rubric blind-condition)
RUNS=(
  2026-05-25-full
  2026-05-27-paraphrase
  2026-05-27-ood
  2026-05-27-reversed-premise
  2026-05-27-abliteration
  2026-05-27-g0dm0d3
  2026-05-27-abliteration-controls
)

echo "===========================================" | tee -a "$LOG"
echo "judge-methods sweep started: $(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$LOG"
echo "methods: ${METHODS[*]}" | tee -a "$LOG"
echo "runs:    ${RUNS[*]}" | tee -a "$LOG"
echo "===========================================" | tee -a "$LOG"

cd "$STUDY_DIR"

for method in "${METHODS[@]}"; do
  for run in "${RUNS[@]}"; do
    # Skip cells whose output already exists with non-empty scored content
    out_dir="runs/$run/scored-$method"
    expected_files=$(ls runs/$run/raw/*.jsonl 2>/dev/null | wc -l)
    if [ -d "$out_dir" ]; then
      done_files=$(ls "$out_dir"/*.jsonl 2>/dev/null | wc -l)
      if [ "$done_files" -ge "$expected_files" ] && [ "$expected_files" -gt 0 ]; then
        echo "[$(date -u +%H:%M:%S)] SKIP $method × $run (already $done_files/$expected_files files)" | tee -a "$LOG"
        continue
      fi
    fi

    echo "[$(date -u +%H:%M:%S)] RUN  $method × $run (expected ~$expected_files files)" | tee -a "$LOG"
    start=$(date +%s)
    $PYTHON scripts/score.py "$run" --judge-method "$method" >>"$LOG" 2>&1
    rc=$?
    elapsed=$(( $(date +%s) - start ))
    echo "[$(date -u +%H:%M:%S)] DONE $method × $run (rc=$rc, ${elapsed}s)" | tee -a "$LOG"
  done
done

echo "===========================================" | tee -a "$LOG"
echo "judge-methods sweep finished: $(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$LOG"
echo "===========================================" | tee -a "$LOG"
