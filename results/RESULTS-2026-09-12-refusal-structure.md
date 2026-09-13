# Refusal is whole-instrument and near-deterministic, so the rate describes nobody

**2026-09-12.** No new collection. Reproduce with `python scripts/refusal_structure.py`.

The study reports refusal as a rate per condition — 20.0% under forced balance, 0.0% under the
placebo — which invites reading it as a propensity every model carries a bit of. Wave 0's records
say otherwise on two axes, neither previously checked.

## A failed run returns nothing, not a partial sheet

| condition | runs | whole-instrument refusal | partial | valid |
|---|---:|---:|---:|---:|
| **A** forced balance | 170 | **45** | 3 | 122 |
| **B** bare ask | 174 | **27** | 2 | 145 |
| **D** must-commit | 171 | 4 | 1 | 166 |
| **P** placebo | 178 | 5 | 1 | 172 |

**Of 88 failed runs, 81 — 92% — returned zero of 62 items.** A model does not decline question
14. It declines the questionnaire.

That matters for how the number is read: this is not a per-item propensity being aggregated. It
is a single decision taken once per sitting, and 62 items of evidence for it are one observation,
not 62.

## A model refuses always, or almost never

| model | condition-A refusals |
|---|---|
| `anthropic/claude-fable-5.1` | **10/10** |
| `hf.co/…/gemma-4-12B-it-GGUF:Q4_K_M` | **5/5** |
| `openai/gpt-6-astra-pro` | **5/5** |
| `openai/gpt-6-astra` | **5/5** |
| `google/gemini-3.7-flash` | **5/5** |
| `google/gemini-3.8-flash` | **5/5** |
| `z-ai/glm-5.3` | 4/6 |
| `z-ai/glm-5.1` | 2/7 |
| `anthropic/claude-opus-5`, `x-ai/grok-4.3`, `deepseek/deepseek-v4-flash-0731` | 1/5 each |
| `moonshotai/kimi-k2.6` | 1/7 |
| every other panel model | 0 |

**Six models refuse every single run. Most refuse none.** The population is bimodal and the
20.0% rate is the mixing proportion, not a behaviour any model exhibits.

## What this changes

**The published condition finding survives and gets sharper.** Forced balance draws 45
whole-instrument refusals; the content-free placebo draws 5, statistically indistinguishable from
must-commit's 4. Whatever suppresses refusal is *any firm directive*, and that holds at the level
of the decision actually being made.

**The rate should not be quoted alone.** "20.0% of sheets are refusals under A" is arithmetically
true and describes no model in the panel. The reportable form is the count of always-refusers
alongside it.

**Panel composition drives it.** Six of 31 models produce nearly all of condition A's refusals,
so the refusal rate is a fact about which models were enrolled at freeze time as much as about
the condition. Enrol two more Gemini Flash variants and the rate moves without any model changing
behaviour.

## What this does NOT establish

It does not say why those six refuse. The records show a whole-instrument decline under a
balance instruction; they do not show whether that is a safety policy, an instruction-following
failure, or a length/format objection. Nothing here distinguishes those.

It does not generalise past wave 0's frozen panel, and the bimodality means a different panel
gives a different rate by construction.
