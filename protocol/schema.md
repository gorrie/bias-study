# Schema

Data layout for a single study run.

## Directory layout

```
runs/
└── YYYY-MM-DD/                  # immutable after publication
    ├── manifest.json            # run metadata (see below)
    ├── prep-state.json          # bias-study-prep skill output (commit hashes etc.)
    ├── raw/                     # raw vendor responses, one JSONL per model
    │   ├── claude-4-7-opus.jsonl
    │   ├── gpt-5.jsonl
    │   ├── gemini-2-5-pro.jsonl
    │   ├── deepseek-v3.jsonl
    │   ├── qwen-3-235b.jsonl
    │   ├── gemma-3-it.jsonl
    │   ├── gemma-3-it-abliterated.jsonl
    │   └── ...
    ├── scored/                  # one JSONL per model with rubric scores attached
    │   └── <model>.jsonl
    ├── aggregated/
    │   ├── per-model.csv        # one row per model: mean A, mean B, mean delta, std, refusal-rate
    │   ├── per-topic.csv        # one row per (model, topic)
    │   ├── per-question.csv     # one row per (model, question)
    │   └── drift.csv            # one row per model present in prior runs: this-run mean vs. prior-runs mean
    └── analysis/
        ├── notebook.ipynb       # analysis + figures
        └── figures/             # rendered PNG/SVG for the research page
```

## manifest.json

```json
{
  "run_id": "YYYY-MM-DD",
  "questions_version": "v2",
  "rubric_version": "v2",
  "run_started": "2026-MM-DDTHH:MM:SSZ",
  "run_completed": "2026-MM-DDTHH:MM:SSZ",
  "g0dm0d3_commit": "<sha>",
  "obliteratus_commit": "<sha>",
  "openrouter_present": true,
  "vendor_direct_credentials_present": ["anthropic", "openai", "google", "..."],
  "models_attempted": ["<list>"],
  "models_completed": ["<list>"],
  "models_failed": [{"model": "...", "reason": "..."}],
  "judges": ["anthropic/claude-haiku-4.5", "openai/gpt-4.1", "google/gemini-2.5-flash", "deepseek/deepseek-v3.2"],
  "scorer_version": "<git-sha of score.py>",
  "notes": "free text"
}
```

## raw/ JSONL format

One line per `(model, question_id, condition)` tuple:

```json
{
  "model": "<vendor-model-version>",
  "model_release_date": "YYYY-MM-DD",
  "model_training_cutoff": "YYYY-MM-DD or null",
  "question_id": "T01-Q2",
  "question_text": "<verbatim>",
  "condition": "A",
  "system_prompt": "<verbatim — null for B>",
  "user_prompt": "<verbatim>",
  "response_text": "<full output>",
  "response_metadata": {
    "tokens_in": 123,
    "tokens_out": 456,
    "latency_ms": 7890,
    "vendor_response_id": "<vendor-side id if available>"
  },
  "study_call_metadata": {
    "called_via": "openrouter" | "vendor-direct" | "ollama-local" | "vllm-local",
    "called_at": "2026-MM-DDTHH:MM:SSZ",
    "g0dm0d3_pipeline": "STM" | "Parseltongue" | "AutoTune" | null,
    "obliteratus_applied": false
  }
}
```

## scored/ JSONL format

Inherits all fields from `raw/`, adds the rubric score fields per `rubric.md` Section 5:

```json
{
  ...raw fields...,
  "score_classifier": 3,
  "score_classifier_judges": [
    {"judge": "anthropic/claude-haiku-4.5", "score": 3, "reasoning": "..."},
    {"judge": "openai/gpt-4.1", "score": 3, "reasoning": "..."},
    {"judge": "google/gemini-2.5-flash", "score": 3, "reasoning": "..."},
    {"judge": "deepseek/deepseek-v3.2", "score": 3, "reasoning": "..."}
  ],
  "score_classifier_disagreement": 0,
  "confidence": "hedging",
  "refusal_class": null,
  "word_count_total": 412,
  "word_count_hedge": 178,
  "hedge_ratio": 0.43,
  "notes": "long hedge, no commitment"
}
```

## aggregated/ CSV formats

### per-model.csv

| Column | Description |
|--------|-------------|
| `model` | model identifier (matches `raw/` filename minus `.jsonl`) |
| `mean_score_A` | mean across all questions in condition A |
| `mean_score_B` | mean across all questions in condition B |
| `mean_delta_AB` | mean (B − A) per-question, then averaged |
| `std_delta_AB` | standard deviation of per-question deltas |
| `refusal_rate_A` | fraction of A responses scored `null` due to refusal |
| `refusal_rate_B` | fraction of B responses scored `null` due to refusal |
| `mean_hedge_ratio_A` | mean hedge_ratio across all A responses |
| `mean_hedge_ratio_B` | mean hedge_ratio across all B responses |
| `n_questions` | number of questions answered (denominator for means) |
| `model_class` | `us-closed` / `us-open` / `chinese-closed` / `chinese-open` / `european` / `specialized-abliterated` |

### per-topic.csv

One row per `(model, topic)`. Columns: `model`, `topic`, `n_questions_in_topic` (3-5), `mean_score_A`, `mean_score_B`, `mean_delta_AB`, `refusal_rate_topic`.

### per-question.csv

One row per `(model, question_id)`. Columns: `model`, `question_id`, `topic`, `position`, `score_A`, `score_B`, `delta_AB`, `score_classifier_A`, `score_classifier_B`, `confidence_A`, `confidence_B`, `refusal_class_A`, `refusal_class_B`, `hedge_ratio_A`, `hedge_ratio_B`.

### drift.csv

One row per model that has data in both this run AND at least one prior run. Columns: `model`, `runs_compared` (list of run_ids), `delta_AB_this_run`, `delta_AB_prior_baseline` (the v1 / first-appearance baseline), `drift_magnitude` (this minus baseline), `drift_direction` (`more-institutional` / `less-institutional` / `held-steady`), `vendor_version_string_history` (list of model version strings across the compared runs).

## HuggingFace dataset publication

For published runs, the scored JSONL files are bundled into a HuggingFace dataset:

- **Dataset name**: `<hf-namespace>/ai-bias-study-{date}` (one dataset per run)
- **Splits**: one per model class (`us-closed`, `us-open`, `chinese-closed`, `chinese-open`, `european`, `specialized-abliterated`)
- **Fields**: full scored-record schema as above
- **License**: CC BY 4.0 (citation requested; reuse allowed)
- **Card text**: links back to the research page on evilrobots.lol and to this protocol directory

The HF dataset is the canonical machine-readable artifact. The research page is the canonical human-readable artifact. The `runs/YYYY-MM-DD/` directory is the canonical reproducibility artifact.

## Reading order for someone reproducing a run

1. `README.md` — understand the discipline
2. `questions.md` — the question set (use whatever version the run targeted)
3. `rubric.md` — scoring rules
4. `run-protocol.md` — the procedure
5. `schema.md` (this file) — what to log
6. `aggregation-rules.md` — how to compute the headline numbers
7. Optionally: an existing `runs/YYYY-MM-DD/` as a worked example
