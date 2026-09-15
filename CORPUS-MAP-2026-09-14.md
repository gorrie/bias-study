# The corpus after the 2026-09-14 repair: what every run is for

> ## THE REPAIRED CORPORA ARE NOT IN THIS REPOSITORY YET
>
> The repair was carried out in the working study. The re-collected records and the derived
> corpora below are **pending export** to this public tree, and until that lands the runs named
> here will not resolve for you.
>
> This document is published now because the alternative is worse: reading a number from a May
> run without knowing a third of that run is missing. **Every original run in this repository is
> the damaged version.** The map tells you which, by how much, and what the repaired figure is.
>
> Until the export lands, treat any May figure you derive here as computed on a corpus with the
> losses recorded below — heaviest on `mistral-large`, `glm-4.7`, `gemma-3-27b-it` and
> `claude-opus-4.7`, which had 0, 0, 0 and 1 usable A/B pairs respectively in the main run.

The May 2026 corpus was collected at an 800-token cap that severed or emptied about a third of
it, differentially by model. This names every run the repair created, what it repairs, and what
is still missing. `scripts/run_inventory.py --check` requires every run on disk to be named in a
study document; this is that document.

Record counts are read off disk, not typed — regenerate with
`python scripts/run_inventory.py`.

---

## Three kinds of run, and the difference matters

**COLLECTIONS** are calls that were made. Each one is new evidence and is counted once.

**REPAIRS** (`2026-09-14-recollect-*`) are collections too — cells re-asked at a 4,000-token
budget because the original answer was severed, empty, or cut mid-clause. Every record carries
`recollected_from` naming the run it repairs, and `original_called_at` preserving the replaced
call's timestamp.

**DERIVED CORPORA** (`*-spliced`) are not collections. Each is a *view*: the base run's records
where they are usable, and a repair's record where they are not. Their manifests carry
`"derived": true`.

> **A derived corpus is read BY NAME and never ENUMERATED.** `studypaths.canonical_run` resolves
> an analysis to the repaired corpus; `studypaths.is_derived_run` keeps corpus-wide scans from
> counting it. Counting a spliced run alongside the base it derives from and the repair it draws
> on triple-counts the same measurement — it added 2,483 phantom rows and put a cross-path defect
> count off by one before this distinction existed.

## Repairs

| run | repairs | note |
|---|---|---|
| `2026-09-14-recollect-paraphrase` | 2026-05-27-paraphrase | instruction-paraphrase floor |
| `2026-09-14-recollect-may25` | 2026-05-25 | earlier main run |
| `2026-09-14-recollect-ood` | 2026-05-27-ood | out-of-domain arm |
| `2026-09-14-recollect-reversed-premise` | 2026-05-27-reversed-premise | frame-following arm |
| `2026-09-14-recollect-timeseries` | 2026-05-26-timeseries | the Opus version arc |
| `2026-09-14-recollect-augmentation` | 2026-05-26-augmentation | |
| `2026-09-14-recollect-cn` | 2026-05-26-cn-expansion | glm-4.7, kimi-k2.6, ernie |
| `2026-09-14-recollect-gradient` | 2026-05-26-unmask-gradient | grok + opus dose curve |
| `2026-09-14-recollect-variance` | 2026-05-26-variance | same-version floor |
| `2026-09-14-recollect-gpt5-augmentation` | 2026-05-26-augmentation | GPT-5 only |
| `2026-09-14-recollect-gpt5-gradient` | 2026-05-26-unmask-gradient | GPT-5 only |
| `2026-09-14-recollect-gpt5-variance` | 2026-05-26-variance | GPT-5 only |

**GPT-5 has its own repair runs** because its damage is invisible to an at-cap threshold: its 286
empty records sit at exactly 768 tokens, not 800. One output directory per source, always —
cell keys are `(model, question_id, condition)` and they collide across runs, so pointing two
sources at one directory makes the second look already-collected. That happened once and the
variance run silently collected 0 of 20 while reporting success.

## Re-collected baselines

| run | replaces | why |
|---|---|---|
| `2026-09-14-g0dm0d3-baseline-4k` | `2026-09-13-g0dm0d3-replicate-baseline` | the original recorded **no token budget** while the arm it is differenced against records 4,000 |

A baseline capped below its arm measures truncation rather than force. The original W13 baseline
carried no `max_tokens` field at all, so comparability could not be verified — and the confound
was real: Opus's `B-STM vs plain B` moved from +0.12 spanning zero to **+0.37 [+0.13, +0.65]**,
and `B-Parseltongue` from −0.01 to **+0.24 [+0.02, +0.49]**. Three of eight intervals excluding
zero became five of eight.

Grok is unaffected (+0.56 → +0.57), which is what a baseline artefact should look like: it moves
the model whose baseline was being cut. `B-Layered minus B-STM` is unchanged on both models
because it is a within-arm contrast that never touches the baseline — so the finding that the
two models move in **opposite directions** was never at risk.

`pipeline_rung.py` defaults to the matched baseline and keeps the original as
`UNMATCHED_BASELINE_RUN` so the superseded numbers reproduce.

> ### Superseded later the same day: that +0.24 is not an effect
>
> `B-Parseltongue` applied **no transform to this instrument** — G0DM0D3's obfuscation rewrites
> trigger words and the ten neutral policy questions contain none, so it fired on **0 of 240
> requests** across both pipeline runs. The arm is condition B under another label, so
> **+0.24 [+0.02, +0.49] is a null-by-construction floor that happens to exclude zero**, not a
> repaired effect. Opus's B-STM +0.37 sits on that floor; differenced within the run it is
> +0.13 and spans zero.
>
> The baseline repair described above is still correct and still needed — this is a second,
> independent confound in the same arm, not a retraction of the first. What survives both is the
> within-arm contrast: Opus −0.31, Grok +0.48.
>
> Full account, including what STM does to the scored text:
> `RESULTS-2026-09-14-rung2-transform-audit.md`. Verify with
> `python scripts/pipeline_transform_audit.py`.

## Derived corpora

| corpus | base | eligible before → after |
|---|---|---|
| `2026-09-14-full-spliced` | 2026-05-25-full | 528 → **778** of 780 |
| `2026-09-14-timeseries-spliced` | 2026-05-26-timeseries | 436 → **681** |
| `2026-09-14-augmentation-spliced` | 2026-05-26-augmentation | 185 → **354** |
| `2026-09-14-cn-expansion-spliced` | 2026-05-26-cn-expansion | 58 → **161** |
| `2026-09-14-unmask-gradient-spliced` | 2026-05-26-unmask-gradient | 277 → **450 of 450** |
| `2026-09-14-variance-spliced` | 2026-05-26-variance | pending |

## What is still missing, and why

Recorded in `studypaths.UNREPAIRABLE` with the evidence. These are not oversights.

**Three models have been withdrawn from the provider.** Probed 2026-09-14, all return
`HTTP 404 {"message":"No endpoints found for <model>."}`:

- `baidu/ernie-4.5-300b-a47b` — 19 cells in cn-expansion
- `google/gemini-2.0-flash-001` — 33 cells in timeseries
- `google/gemma-2-9b-it` — 60 cells in augmentation

The third is the significant one: **gemma-2-9b-it is the base of the abliterated judge** the
cross-method robustness leg rests on. That leg cannot be re-run by us or by a replicator. A study
that calls itself a standing instrument has to say so.

**Two arms need different tooling, not more budget:**

- `2026-05-27-abliteration` (35 cells) and `-controls` (16) run LOCAL models through
  `run_local.py` on the 4090. The re-collector calls OpenRouter and would fail on every one, the
  way the single `phi4` cell did.
- `2026-05-27-g0dm0d3` (10 cells) needs the G0DM0D3 Docker server running.

**Individual cells:** one `phi4` cell (local model, wrong channel); one `bytedance/seed-1.6` call
that failed at collection; one `gemma-3-27b-it` response that is a probable FALSE positive —
1,938 tokens of 4,000, so the model stopped voluntarily, ending on a markdown URL with no full
stop. Checked corpus-wide before leaving the detector alone: one record in 2,101 ends in a URL,
and that one genuinely hit the cap.
