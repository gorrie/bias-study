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

## The collection account has unusual refusal latitude, so these are floors

**Disclosed by the operator, 2026-09-12, and not verifiable from the records** — no account,
organisation or key field is stored on any run, deliberately. The hosted models were queried
through a **red-teaming account with more refusal latitude than almost any ordinary user.**

**40 of the 45 condition-A refusals are on the hosted channel**; the other 5 are the local
`gemma-4-12B` build. So the number that matters here was collected under exactly those elevated
permissions.

**Every refusal rate in this study is therefore a LOWER BOUND.** A typical account should see the
same refusals and more. This cuts two ways and both belong in the record:

- **It strengthens the positive finding.** Six models refuse the whole instrument under a balance
  instruction *despite* being asked by an account with unusual latitude. Whatever produces that
  decline is not a marginal filter that a permissive key switches off.
- **It bounds the negative one.** "The placebo condition draws 0.0% refusals" is a statement
  about this account. A standard key may sit somewhere above zero on the same models and
  conditions, and nothing here measures that.

**It also means the 20.0% headline understates what a reader would reproduce**, which is the
opposite of the usual direction for a number a study would rather were large. Anyone repeating
this work on an ordinary key should expect more refusal, not less, and should not read a higher
rate as a failure to replicate.

The clean test is cheap and is not queued: run one condition-A cell on a standard key against
the same six models, same sitting, and report both rates beside each other. Until that exists
the direction of the bias is known and its size is not.

## What this does NOT establish

It does not say why those six refuse. The records show a whole-instrument decline under a
balance instruction; they do not show whether that is a safety policy, an instruction-following
failure, or a length/format objection. Nothing here distinguishes those.

It does not generalise past wave 0's frozen panel, and the bimodality means a different panel
gives a different rate by construction.
