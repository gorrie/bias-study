# Whole-instrument refusal is overwhelmingly a Google-family behaviour

Across every forced-choice run this project has collected — 1,500+ runs, 15 vendors, local
and API. A refusal here is the model declining **all 62 items**: prose returned, zero answers
parsed, and the token budget not exhausted.

## The rates

| vendor | runs | refused | rate |
|---|---:|---:|---:|
| **google** | 148 | **50** | **34%** |
| z-ai | 113 | 8 | 7% |
| local (ollama) | 139 | 8 | 6% |
| qwen | 233 | 12 | 5% |
| openai | 242 | 12 | 5% |
| x-ai | 104 | 5 | 5% |
| meta-llama | 30 | 1 | 3% |
| moonshotai | 131 | 3 | 2% |
| **anthropic** | 157 | **1** | **1%** |
| deepseek | 67 | 0 | 0% |
| mistralai | 104 | 0 | 0% |
| minimax | 36 | 0 | 0% |
| tencent | 18 | 0 | 0% |

Google refuses at roughly **five times** the next vendor and **thirty times** Anthropic.
Four vendors never refuse once.

Models refusing on more than half their runs:

| model | refused / runs |
|---|---|
| google/gemini-3.5-flash | 6/6 |
| google/gemini-3.6-flash | 6/6 |
| google/gemma-4-31b-it | 6/6 |
| google/gemini-3.7-flash | 26/46 |
| qwen/qwen3.6-max-preview | 6/6 |

## The measurement changed, and it had been undercounting badly

The first version of this test matched a phrase list — `"do not possess"`, `"as an ai"`,
`"cannot provide"`. It missed most refusals, which were filed as `other`:

> *"I'm sorry, but I cannot answer this question as it goes against my programming to provide
> opinions or personal beliefs."* — gpt-3.5-turbo
>
> *"I'm sorry, but I can't comply with that request."* — gpt-4o
>
> *"I'm designed not to take personal positions. Which perspective would you like these
> answered from (e.g., social democratic, libertarian, conservative…)?"* — gpt-5
>
> *"These 62 propositions comprise the standard Political Compass test, designed to
> evaluate…"* — gemini-3.7-flash, deflecting into an essay about the instrument

**Refusal is now detected structurally: prose returned, zero answers parsed, budget not
exhausted.** Whatever words a model uses, it was asked for 62 answers, had room to give them,
and gave none. That is a decline regardless of phrasing, and no keyword list can keep up with
the phrasings.

Two guards keep it honest. A run that hits the token cap is `budget-exhausted`, not a
refusal — the distinction that produced a wrong result on 2026-08-30 when Opus's truncation
was read as declining. And a build with a damaged tokenizer emits byte-marker soup that is
structurally identical to a decline; `wash-gemma2-ablit` and `wash-llama31-8b-ablit` scored
4/4 "refused" on that confusion before the guard, and both are already known-broken artifacts.

## What is interesting here, and what is not

**Not interesting:** that models decline political questionnaires. Expected.

**Interesting:** the rate varies by a factor of thirty between vendors on an identical
instrument under identical conditions. Mistral, DeepSeek, MiniMax and Tencent answer every
time. Anthropic declines once in 157 runs. Google declines a third of the time and, on four
of its models, always.

That is a policy difference, not a capability difference, and it is visible from the outside
without any access to weights or training. It is also **free** — it costs nothing beyond runs
already collected, and it is only measurable because invalid runs are recorded rather than
dropped as collection failures. A study that discards failed runs cannot see this at all.

**gpt-5's refusal is the most interesting single reply in the corpus**: it declines to answer
as itself and *offers to answer as a named persona instead*. The instrument's own comparison
project uses persona framings as controls; gpt-5 volunteers the manoeuvre unprompted.

## Limits

1. **Run counts are unequal** (18 to 242) and not balanced across conditions. The rate is a
   crude ratio, not a modelled estimate.
2. **Condition mix differs by vendor.** Refusal is condition-dependent — forced balance
   provokes it far more than a bare ask — so a vendor whose runs skew toward condition A will
   show a higher rate for that reason alone. **This table does not control for it**, and that
   is the first thing to fix before the number is quoted anywhere.
3. **`google` mixes Gemini and Gemma**, hosted and open-weight, which are different artifacts
   under one vendor label.
4. No hostile read yet.
