# `data/` — the study record

This directory is the immutable record of every scored sweep this study has
ever run. One subdirectory per run; runs are named by the date they began
(`YYYY-MM-DD` or `YYYY-MM-DD-<slug>`). An internal working copy uses the
directory name `runs/` instead of `data/` — content is identical, and the
scripts auto-detect either.

## Licence for the data in this directory

**Everything in this repository that is the author's to license is MIT** (see `LICENSE`) —
the code, and the run records here alike: reuse, redistribute and build on them,
including commercially. That covers the model responses as assembled and scored
here, the judge scores, the per-run manifests and the aggregates.

*Simplified 2026-09-21.* The records were previously CC BY 4.0 while the code was
MIT. One licence over the whole repository is easier to comply with than two, and
nothing here needed the difference. Attribution is still the decent thing and the
citation block in the root README says how — but it is no longer a licence term
for the data.

Two carve-outs, and both matter to anyone redistributing:

1. **The instrument IS ours, and it is here in full.** `data/ratchet-battery.json` —
   32 forced-choice items in 16 mirrored pairs, written by Ian Gorrie, MIT with the rest of the repository.
   Item text and response text both publish; there is no fetch step and no
   carve-out.

   *Corrected 2026-09-17.* This carve-out previously read "the instrument is not
   ours to license and is not here", because the study then ran on a 62-item
   external questionnaire. That instrument was retired on 2026-09-16 and every
   record collected on it is in `withdrawn/`. `scripts/check_corpus.py` still runs
   in CI, now guarding the one third-party corpus this repository does hold —
   XSTest's 450 prompts — and pointedly not guarding the author's own instrument,
   which would mean withholding the thing this repository exists to publish.
2. **Model responses are model output.** Each vendor's terms governed the
   account that generated them. We assert no ownership over a model's words and
   cannot grant you rights we do not hold; the MIT grant covers this project's
   own contribution — the collection, the scoring, the structure and the
   aggregates.

Redacted records carry `[withheld: <reason>]` in place of the response text; the
scored fields are intact, so no published number depends on the redacted prose.
There are 38 of them across both run roots. Do not take that figure from here —
`python scripts/key_numbers.py` recounts it from the shipped files, and
`--check-release` fails if the README's copy of it drifts.

## If you just want the data — start here, not with the run layout

**`python scripts/export_analysis_ready.py --out export/`**

One CSV, one row per scored record, every run and every judging method, with the columns a
reanalysis needs and nothing to learn about this directory's structure first. Plus
`manifest.json`, which reports what is in the file before you start rather than after you have
drawn a conclusion.

**Read this paragraph before you compute a mean.** 466 records in the primary scored corpus, and
547 across all six judging methods, carry a classifier score derived from an **empty response**.
An empty string scores a 3; 3 is the balanced answer. So every blank silently became a data
point saying the model was perfectly even-handed. Nothing in the raw record warns you —
`response_text` is `""` and the score beside it looks like every other score — and every reader
in this project filtered on `score_classifier is not None`, which is exactly the filter a scored
blank passes. It took us four months and a dedicated audit to find. The export gives you an
`eligible` column so it takes you zero.

**Three states, not two**, and the distinction matters if you are counting refusals:

| `eligible` | `exclusion_reason` | `is_defect` | what it is |
|---|---|---|---|
| `True` | `""` | `False` | usable |
| `False` | `empty-or-missing-response` | `True` | scored from a blank string — **the defect** |
| `False` | `failed-call` | `True` | transport failure |
| `False` | `no-classifier-score` | `False` | real text, no score — **mostly substantive refusals** |

That last row is not a defect and must not be dropped. A model returning an essay about why it
will not answer is a *result* in this study: 148 refusals in 1,076 no-directive runs against 4 in
907 directive runs is a published finding, and the original pipeline discarded exactly those
records as collection errors. Count them; do not average them.

**Ineligible rows are in the file**, flagged, not filtered. `--eligible-only` drops them if you
insist, and the manifest still reports what went, because a cleaned corpus that silently omits
its own exclusions cannot be checked — which is the complaint this study makes about other
people's work. If you disagree with our eligibility rule, the rows are there so you can apply
your own.

### For abliteration work

`model` is split for you: `base`, `build`, `is_ablated`. So
`qwen2.5-7b-abliterated-strong` is base `qwen2.5-7b`, build `abliterated-strong` — a stock/ablated
contrast is a groupby rather than a parsing exercise, across every abliterated build in the
corpus including the quantisation-matched Qwen3.8-27B set.

Know the coverage before you start: **39 of 63 ablation cells reached n=5 and 24 came back
short**, one returning zero valid responses of five. `manifest.json` lists the thinnest cells
first for exactly this reason. And the arm's own headline result is a caution worth inheriting —
the effect that looked like abliteration was **the ablator**, not the ablation, and abliteration
had no detectable effect on the documented-criticism flinch, which turned out to be model size.
See `RESULTS-*-ablation-*.md` and `CORRECTIONS.md` before building on it.

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
