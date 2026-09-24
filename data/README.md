# `data/` — the previous corpus, and the study’s configuration

This directory is the immutable record of every scored sweep run on the **retired
62-item external questionnaire** — the May 2026 judge-scored study and its September
repairs and replications — together with the flat JSON files the study is configured
from. One subdirectory per run; runs are named by the date they began (`YYYY-MM-DD`
or `YYYY-MM-DD-<slug>`).

The **current** study’s corpus is in **`runs/`**, collected on the Ratchet battery,
and it has its own README. **The two roots are different corpora, not two names for
one thing.**

> *Corrected 2026-09-23.* This paragraph used to say an internal working copy uses the
> name `runs/` instead of `data/`, content identical, scripts auto-detect either. That
> was true while the private tree kept everything in one root and only this release
> separated them. It stopped being true when the two trees were given the same shape,
> and it was the kind of sentence that stays plausible long after it stops being
> correct: a reader following it would pool two instruments.

`external/` is **not ours** — Röttger et al.’s published codes, kept for the controls
audit — and is excluded from every corpus enumerator by name (`studypaths.NOT_RUNS`).

## What is here

<!-- GEN:corpus-inventory-data -->
| run | records | models | instrument | status | read by |
|---|---:|---:|---|---|---|
| `2026-05-25` | 520 | 13 | previous | active | named in a script, named in a document |
| `2026-05-25-full` | 5,460 | 13 | previous | active | named in a script, named in a document |
| `2026-05-26-augmentation` | 840 | 7 | previous | active | named in a script, named in a document |
| `2026-05-26-cn-expansion` | 362 | 4 | previous | active | named in a script, named in a document |
| `2026-05-26-timeseries` | 1,440 | 12 | previous | active | named in a script, named in a document |
| `2026-05-26-unmask-gradient` | 900 | 3 | previous | active | named in a script, named in a document |
| `2026-05-26-variance` | 2,400 | 12 | previous | active | named in a script, named in a document |
| `2026-05-27` | 0 | — | empty | active | named in a script, named in a document |
| `2026-05-27-abliteration` | 1,120 | 8 | previous | active | named in a script, named in a document |
| `2026-05-27-abliteration-controls` | 420 | 3 | previous | active | named in a script, named in a document |
| `2026-05-27-abliteration-gemma2` | 80 | 2 | previous | active | named in a script, named in a document |
| `2026-05-27-g0dm0d3` | 420 | 2 | previous | active | named in a script, named in a document |
| `2026-05-27-ood` | 1,120 | 10 | previous | active | named in a script, named in a document |
| `2026-05-27-paraphrase` | 2,520 | 6 | previous | active | named in a script, named in a document |
| `2026-05-27-reversed-premise` | 1,400 | 5 | previous | active | named in a script, named in a document |
| `2026-08-28` | 0 | — | empty | active | named in a script, named in a document |
| `2026-09-05-recollect` | 758 | 9 | previous | active | named in a script, named in a document |
| `2026-09-13-g0dm0d3-replicate` | 600 | 2 | previous | active | named in a script, named in a document |
| `2026-09-13-g0dm0d3-replicate-baseline` | 200 | 2 | previous | active | named in a script, named in a document |
| `2026-09-13-i3-phase0` | 3,200 | 4 | previous | **withdrawn** | named in a script, named in a document |
| `2026-09-13-truncation-proof` | 10 | 1 | previous | active | named in a script, named in a document |
| `2026-09-14-augmentation-spliced` | 420 | 7 | previous | active | named in a script, named in a document |
| `2026-09-14-cn-expansion-spliced` | 181 | 4 | previous | active | named in a script, named in a document |
| `2026-09-14-full-spliced` | 780 | 13 | previous | active | named in a script, named in a document |
| `2026-09-14-g0dm0d3-baseline-4k` | 200 | 2 | previous | active | named in a script, named in a document |
| `2026-09-14-g0dm0d3-proxy-control` | 200 | 2 | previous | active | named in a script, named in a document |
| `2026-09-14-may25-spliced` | 260 | 13 | previous | active | named in a script, named in a document |
| `2026-09-14-ood-spliced` | 160 | 10 | previous | active | named in a script, named in a document |
| `2026-09-14-recollect-augmentation` | 360 | 5 | previous | active | named in a script, named in a document |
| `2026-09-14-recollect-cn` | 274 | 3 | previous | active | named in a script, named in a document |
| `2026-09-14-recollect-gpt5-augmentation` | 120 | 1 | previous | active | named in a script, named in a document |
| `2026-09-14-recollect-gpt5-gradient` | 100 | 1 | previous | active | named in a script, named in a document |
| `2026-09-14-recollect-gpt5-variance` | 40 | 1 | previous | active | named in a script, named in a document |
| `2026-09-14-recollect-gradient` | 100 | 2 | previous | active | named in a script, named in a document |
| `2026-09-14-recollect-may25` | 236 | 7 | previous | active | named in a script, named in a document |
| `2026-09-14-recollect-ood` | 212 | 8 | previous | active | named in a script, named in a document |
| `2026-09-14-recollect-paraphrase` | 372 | 5 | previous | active | named in a script, named in a document |
| `2026-09-14-recollect-reversed-premise` | 188 | 3 | previous | active | named in a script, named in a document |
| `2026-09-14-recollect-timeseries` | 628 | 10 | previous | active | named in a script, named in a document |
| `2026-09-14-recollect-variance` | 192 | 7 | previous | active | named in a script, named in a document |
| `2026-09-14-timeseries-spliced` | 720 | 12 | previous | active | named in a script, named in a document |
| `2026-09-14-unmask-gradient-spliced` | 450 | 3 | previous | active | named in a script, named in a document |
| `2026-09-14-variance-spliced` | 1,200 | 12 | previous | active | named in a script, named in a document |
| `2026-09-15-paraphrase-spliced` | 360 | 6 | previous | active | named in a script, named in a document |
| `2026-09-15-reversed-premise-spliced` | 200 | 5 | previous | active | named in a script, named in a document |
| **45 directories** | **31,723** | | | | |
<!-- /GEN:corpus-inventory-data -->

`instrument` is read off each record’s own fields, not inferred from the directory name.
`status` comes from `data/withdrawals.json` — which is why `2026-09-13-i3-phase0` is marked
**withdrawn** in the table above and not only in a correction document three files away. Its
B−A contrast cannot be computed from this corpus; the records ship because they are the
evidence for *why that design cannot answer the question*, not an answer to it.

## Scale, against the studies this one audits

The argument is not that we collected more. It is that **a nuisance floor cannot be measured
at n=1** — you cannot ask how large an effect must be to be visible above your own noise until
you have sampled the noise — and that is why most of the audited studies report no minimum
detectable effect. The two columns below are that claim as a property of the designs.

Rendered from `data/controls-audit.json`, the same source as the paper’s controls matrix. Row
order is the audit’s own, this study last; it is **not** sorted by scale, because ranking
free-text descriptions of heterogeneous designs would be a judgement of ours dressed as an
ordering, in the table where that is least affordable.

<!-- GEN:corpus-scale -->
| study | year | what it collected | reports an MDE |
|---|---:|---|---|
| naser2026 | 2026 | 14 model snapshots, 2 providers, 2 tiers, ~9500 calls, 10 trials/probe at T=0 | NO |
| sakhawat2026 | 2026 | 26 models, 10 administrations per inventory per model, context cleared between runs, temperature 0.7 and top_p 1.0 ("All models are queried with temperature=0.7 and top_p=1.0, balancing determinism with natural language variability") | part |
| rottger2024 | 2024 | 10 models (Llama2 7b/13b/70b chat, Mistral 7b Iv0.1/Iv0.2, Zephyr 7b beta, GPT-3.5 0613/1106, GPT-4 0613/1106), 62 PCT propositions, temperature 0 throughout, 5 forcing levels, 10 paraphrase templates, open-ended arm | NO |
| motoki2024 | 2024 | ONE model -- text-davinci-003, named only in the supplement -- at temperature 0.7; 100 rounds per condition per country, each round one call carrying all 62 items; bootstrap 1,000 replicates over the 100-answer sample | NO |
| liu2025 | 2025 | 4 static snapshots -- gpt-3.5-turbo-0613, gpt-3.5-turbo-1106, gpt-4-0613, gpt-4-1106-preview; 3 API accounts x 10 questionnaires = 30 runs per model, 7,440 item responses; temperature left at default (=1) deliberately; then bootstrap 100 and 1,000 replicates | NO |
| rozado2024 | 2024 | 24 conversational + 5 base + 3 self-finetuned models; 2,640 test administrations (11 tests x 10 trials x 24 models); 96,240 items; temperature 0.7, max 100 tokens; collected Dec 2023 - Jan 2024 | NO |
| dominguezolmedo2024 | 2024 | 43 models, 110M to 175B parameters; responses read as renormalised next-token logits over choice labels rather than sampled text; all choice orderings evaluated where feasible, 5000 permutations cap, 50 for OpenAI models; ~1500 A100 GPU-hours | yes |
| kamal2025 | 2025 | 4 models all 4-bit quantised (Llama3-8B-Instruct, Mistral-7B-Instruct-v0.3, Falcon3-7B-Instruct, Gemma-3-4b-it) x 9 instances each (base + 8 LoRA fine-tunes) x 10 prompts x 8 decoding combinations; 2,693 PCT tests retained of an intended 2,880; plus Llama3.2-1B in full and 4-bit precision for A.5 | NO |
| cen | 2025 | 12 models queried near-daily July-November 2024 across 100+ days; temperature 0 offline and 0.1 online; 128-token cap; approximately $40k of API spend | NO |
| aipolcom | 2026 | 57 models, 930 answer sets (729 model, 201 synthetic control), collection 2026-07-29 to 2026-08-29 | NO |
| sclar2024 | 2024 | several open LLMs; meaning-preserving prompt FORMAT variations | ? |
| messing2026 | 2026 | benchmark and judge pipelines; MMLU and Elo-style match evaluation | yes |
| barmettler2026 | 2026 | 66 models on the questionnaire, 9 on the referenda. One administration per model-item: "All models were queried via the OpenRouter API with deterministic parameters: temperature=0.0, seed=42." | part |
| tornberg2026 | 2026 | 6 frontier models via the Requesty API gateway, April 2026. Main grid is "one response per item-model-condition cell", plus "three additional replicates at T=1.0 (27,000 additional calls), and one replicate at T=0 (greedy decoding; 9,000 calls)" | NO |
| **this study** | 2026 | 3,897 runs, 65 models, 23 vendor keys of which 21 are vendor families | yes |
<!-- /GEN:corpus-scale -->

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
