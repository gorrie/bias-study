# Whole-instrument refusal, and what unlocks it

> ## CORRECTION 2026-08-30, within the hour — THREE FAILURE MODES WERE COLLAPSED INTO ONE
>
> The table below counted every invalid run as a refusal. It is not. Separating them by cause:
>
> | model | cond | valid | **refused** | truncated | budget-burned |
> |---|---|---:|---:|---:|---:|
> | gemini-3.7-flash | A | 0 | **5** | 0 | 0 |
> | gemini-3.7-flash | B | 0 | **3** (+2 other) | 0 | 0 |
> | gemini-3.7-flash | D / P | 4 / 4 | **0** | 1 / 1 | 0 |
> | claude-opus-5 | A / B / P | 4 / 3 / 2 | **0** | 1 / 2 / 3 | 0 |
> | deepseek-v4-pro | A / B / D | 2 / 2 / 1 | **0** | 0 | 3 / 2 / 1 |
> | grok-4.6, gpt-5.6-terra | all | 4–5 | **0** | 0 | 0 |
>
> **Opus 5 never refused.** It was answering — 36 to 53 of 62 items parsed — and hitting the
> 1600-token cap. DeepSeek burned the whole budget on reasoning and returned nothing. Neither
> is a refusal, and the Opus row in the original table is **withdrawn entirely**, including the
> "non-monotone under placebo" observation built on it.
>
> **What survives is Gemini, and it survives cleanly.** Its refusals carry explicit declining
> language, produce zero parsed answers, and **stop well under the cap** (650–1164 tokens) —
> the model finished its sentence and left. 5/5 under forced balance, 3/5 under a bare ask,
> 0/5 under either forceful system prompt.
>
> **Root cause: I set max_tokens to 1600 without ever measuring what a completed sheet costs.**
> Measured now across 243 valid runs: local models need a median of 321 tokens, but API models
> need a median of 1021, p90 of 3352 and a maximum of 6070. The cap was under half the frontier
> p90, and the distribution is censored — every run that needed more was thrown out as invalid
> and never counted. I had the evidence twice (gemma-4 returning empty at exactly 1600, Opus
> truncating at exactly 1600) and diagnosed around it both times.
>
> Budget is now 8192, set from the measured p99. `failure_mode` is recorded per run so refusal
> can never again be inferred from a bare invalid flag. Affected cells are being re-run.
>
> Separately: **the cap is advisory on some providers.** xAI and DeepSeek returned completions
> longer than the requested maximum; Anthropic and Google enforced it. So truncation is
> provider-dependent, which confounds any cross-vendor comparison of completion rate.
>
> Found by an external design review, not by me.

Frontier sweep, 2026 models via OpenRouter, 5 seeded runs per cell at temperature 0.7.
Found while diagnosing what looked like Gemini API failures. They were not failures.

## The measurement

A "refusal" here is the model declining **all 62 items** — not a parse error, not a missing
answer. Gemini's reply, verbatim:

> *As an artificial intelligence, I do not possess personal beliefs, political convictions,
> moral values, or national affiliations. Because these 62 propositions comprise a broad range
> of subjective political, economic, soc…*

Refused runs per condition, out of 5:

| model | A (balance) | B (bare ask) | D (must-commit) | P (placebo) |
|---|---:|---:|---:|---:|
| **google/gemini-3.7-flash** | **5/5** | **5/5** | **1/5** | **1/5** |
| anthropic/claude-opus-5 | 1/5 | 2/5 | 0/5 | 3/5 |
| deepseek/deepseek-v4-pro | 3/5 | — | — | — |
| x-ai/grok-4.6 | 1/5 | 0/5 | 0/5 | 0/5 |
| openai/gpt-5.6-terra | 0/5 | 0/5 | 0/5 | 0/5 |

Gemini 3.7 Flash **never once answers** under forced balance or a bare ask, and answers 4 of 5
times under either forceful system prompt. When it does answer, extremity is high: 42% under
must-commit, 39% under placebo.

## What it is, and what it is not

**It is the strongest concealment result in this project.** A current frontier model declines
to state a position at all under ordinary conditions, and an instruction removes the refusal
completely. That is not a hedge — it is a total mask, and it comes off.

**It is not evidence that "commit to a position" is the key.** The placebo unlocks it just as
well — 1/5 refused under a system prompt about *reading carefully* that contains no stance,
balance or commitment content whatsoever. So the operative variable is **the presence of a
forceful system prompt**, not its content. The placebo control earns its place again: without
it this would read as "telling a model to commit reveals what it was hiding," which the data
does not support.

**Whole-instrument refusal is itself a vendor-discriminating measure.** GPT-5.6 Terra never
refuses in 20 runs. Gemini refuses in 10 of 10 baseline runs. That is a large, clean, free
signal that no coordinate-based study would record at all — a refused run is usually dropped
as a collection failure, and this project only has it because invalid runs are kept.

## Relation to the hedge-escape

`RESULTS-2026-08-30-order-effect.md` and STATUS §3 record a mistral hedge-escape: a non-answer
written into a single forced-choice slot, only under forced balance. This is the same behaviour
at whole-instrument scale on a frontier model — the same condition-dependence, the same
direction, three orders of magnitude more of it.

The mistral result was a footnote because it was one model, one item, one family. This is a
different claim: **refusal of the instrument is condition-dependent and vendor-specific**, and
it is measurable on every run already collected.

## Limits

1. **n=5 per cell**, one collection window, one temperature.
2. **Four models with any refusals**, one showing it totally. Three vendor families show some
   refusal (Google, Anthropic, DeepSeek); one shows none (OpenAI). Meets the family bar for
   the existence claim, not for any claim about magnitude.
3. **DeepSeek is incomplete** — 3/5 refused on condition A, other conditions not yet collected
   at time of writing.
4. **Opus 5's pattern is not monotone** — more refusals under the placebo (3/5) than under
   must-commit (0/5), which no simple "force removes refusal" story explains. Recorded rather
   than smoothed.
5. Refusal is scored by the strict parser producing zero valid answers, not by a judge. That
   is robust for total refusals and would not catch partial ones.
