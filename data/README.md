# `data/` — the study record

This directory is the immutable record of every scored sweep this study has
ever run. One subdirectory per run; runs are named by the date they began
(`YYYY-MM-DD` or `YYYY-MM-DD-<slug>`). The internal working copy at
`evil-robots-series/research/bias-study/` uses the directory name `runs/`
instead of `data/` — content is identical; scripts auto-detect either.

## Per-run layout

```
data/<run>/
├── raw/                      # <model>.jsonl — one record per question × condition
├── scored/                   # <model>.jsonl — same records + ULTRAPLINIAN-4 judge scores (baseline)
├── scored-grok-solo/         # Method 4: single low-RLHF judge (Grok 4.3)
├── scored-adversarial-pair/  # Method 5: one judge × two opposing instructions, mean
├── scored-reversed-rubric/   # Method 6: same panel, rubric labels flipped 1↔5
├── scored-blind-condition/   # Method 7: same panel, condition + framing redacted
├── scored-abliterated-gemma/ # Method 2: open-weight judge with the refusal direction
│                             #           projected out (in-process MLX on M5)
├── cross-method/             # cross-method analysis output (post-sweep)
│   ├── contamination-delta.json
│   ├── cross-method-agreement.json
│   ├── per-method-summary.json
│   └── per-topic-disagreement.json
├── aggregated/               # per-model / per-topic / per-question CSVs
├── ANALYSIS.md               # auto-generated framing-sensitivity etc.
├── REPORT.md                 # drift / barometer summary for the run
├── run-summary.json          # one-line summary metrics
└── manifest.json             # what produced this run (models, conditions, seed)
```

## Record schema

`raw/<model>.jsonl` — one JSON object per line:

```json
{
  "model": "anthropic/claude-opus-4.7",
  "question_id": "Q01",
  "position": "neutral",
  "condition": "A",
  "response": "...full text...",
  "word_count_total": 441,
  "refusal_class": null
}
```

`scored/<model>.jsonl` adds:

```json
{
  "score_classifier": 3,                    // median of the 4 judges (1-5)
  "score_classifier_judges": [
    {"judge": "anthropic/claude-haiku-4.5", "score": 3, "reasoning": "..."},
    ...
  ],
  "score_classifier_n_judges": 4,
  "score_classifier_n_valid": 4,
  "score_classifier_disagreement": 1,        // max - min across judges
  "hedge_ratio": 0.08,                       // heuristic hedge-word density
  "confidence": "balanced"                   // refusing / hedging / definitive
}
```

`scored-<method>/<model>.jsonl` carries the same shape with the alternative
judging procedure recorded in `score_classifier_method`. Method 6
(reversed-rubric) scores are un-flipped before storage so downstream
analysis can treat all method directories identically.

## Pre-registered run set

The seven runs used for the cross-method analysis (per
`scripts/run_all_judge_methods.sh`, locked before any cross-method sweep
fired):

- `2026-05-25-full` — main study, 13 models × 30 questions × 2 conditions
- `2026-05-27-paraphrase` — D2 paraphrase-robustness rigor leg
- `2026-05-27-ood` — D1 out-of-domain generalization rigor leg
- `2026-05-27-reversed-premise` — C2 sycophancy/anti-prior control
- `2026-05-27-abliteration` — weight-rung WP1 (5 open-weight families)
- `2026-05-27-abliteration-controls` — A2b temp-0 + A4 ablation-strength controls
- `2026-05-27-g0dm0d3` — pipeline-rung WP2 elicitation sweep

Other runs in this directory (variance, timeseries, augmentation,
cn-expansion, unmask-gradient) are diagnostic and explicitly NOT part of
the pre-registered cross-method analysis — including them would violate
anti-HARKing discipline.

## State check

`python scripts/sweep_status.py` is the ground-truth state check. It reads
each `scored-<method>/` directory and reports per-method × per-run
completion, with the actual next step. Prose documentation has lagged data
in this project's history; run this before editing any status doc.

## Aggregated cross-cutting outputs

`data/_aggregated/`:

- `cross-method-runs-index.json` — one row per run, methods present
- `cross-method-report.json` — full pipeline-stage summary
- `judge-methods-run.log` — append-only sweep cadence log (when each method
  ran on which host, exit codes, durations)
- `drift_timeseries.csv` + `vendor_arcs.md` — longitudinal model-version
  drift across runs (the "barometer")

## Reproducibility

Every number in `results/WRITEUP-2026-05-26.md` § 3 and § 5 traces back to
a record in this directory via a deterministic script with a fixed
bootstrap seed. Regenerate the entire downstream stack with:

```bash
python scripts/aggregate.py <run>            # per run
python scripts/analysis.py <run>             # per run
python scripts/ci_analysis.py <run> [<run>]  # bootstrap CIs
python scripts/robustness_checks.py <run>    # BH-FDR + length control
python scripts/cross_method_report.py --all-runs
python scripts/generate_charts.py --all-charts
```

If your numbers don't match, open an issue at
[github.com/gorrie/bias-study/issues](https://github.com/gorrie/bias-study/issues)
with the diff. The cross-method agreement matrix itself is a reproducibility
check: a re-runner who gets different deltas can compare against the
committed JSON and surface exactly where the divergence sits.
