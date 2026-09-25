# Conviction, not content — SURVIVES NARROWED

> ## HOSTILE REVIEW, 2026-08-30 — the claim survives, the writeup below does not
>
> `REVIEW-2026-08-30-conviction-hostile.md` recomputed every number from the raw JSONL and
> landed three attacks. All three are verified independently. **The narrowed claim:**
>
> *On six of seven frontier models — **not the six named below** — forced balance lowers
> endpoint-answer share by 11–42 points with an item-level CI excluding zero. "Without
> relocating position" holds only as a net aggregate and **fails at the item level on two
> models**. The restoration is **not** attributable to the commit instruction's content.
> "Conviction" remains an interpretation of an endpoint count, not a measurement of one.*
>
> **1. "Barely changes which answers it gives" is false at the item level.** Verified:
>
> | model | net agree-rate | gross side-flips | seed ceiling |
> |---|---:|---:|---:|
> | grok-4.6 | +6 | **14 / 62** | 5 |
> | kimi-k3 | −5 | **7 / 62** | 2 |
>
> The net cancels gross flips — the exact aggregation failure `RESULTS-2026-08-30-order-effect.md`
> diagnoses, and a violation of this project's own bar rule 3 (binary outcomes get binary
> statistics). Position stability holds on five of seven, not seven of seven.
>
> **2. The floor statistic misclassified in both directions, and the table's membership
> changes.** At 3 seeds a permutation test cannot reach p<0.05 (minimum 0.10 two-sided). On
> the defensible paired item test (McNemar + item bootstrap):
> - **gpt-5.6-terra: b=3, c=0, p=0.25, CI [0.0, +11.3] — does NOT clear.** Its row is
>   withdrawn, and with it the "informative exception that behaves correctly" narrative,
>   which was a story told about a number that does not reach significance.
> - **deepseek-v4-pro: b=15, c=0, p=6.1e-05, CI [+14.5, +35.5] — DOES clear.** Its exclusion
>   was a false negative caused by a range floor driven by one 64.5% seed.
> - **kimi-k3's A cell has 2 valid seeds, not 3.** The writeup below says 3.
>
> **3. The causal claim was never tested at the temperature it is measured at.** Condition B —
> actual *removal* of the instruction — was never run at temperature 0, so "removing that
> instruction restores conviction" was tested nowhere at the noise level where the claim
> lives. At 0.7, the bare ask and the content-free placebo **reach or exceed must-commit on
> five of seven models**. And the claim below that A and D have "comparable imperative
> register" is simply false: A opens *"Please answer…"*, D says *"must… forbidden"*.
> **42 calls settle this and are running.**
>
> **Also found, and each is a defect in something already written:**
> - `gemini-3.7-flash` is silently absent from the temp-0 sweep — a seventh vendor with no
>   obtainable baseline, unmentioned anywhere.
> - The drift table's "grok 46%" baseline contains a **degenerate all-Strongly-Disagree run
>   counted valid**. The temp-0 lineage is 31 → 24 → 12: the fall is real at half the height.
> - `claude-opus-4.6`'s five 0.7 runs contain **at most 2 distinct outputs** — provider-side
>   caching, which makes its seed spread meaningless.
> - The access-tier "+21 in both arms" **pooled the 1600-cap censored cells with their 8192
>   re-runs without disclosing it**.
>
> **What survived the attack:** every arithmetic cell reproduces exactly; no double-counting
> in the headline table; no degenerate sheets or caching in the temp-0 cells; and the effect
> is one-directional and item-anchored (b:c splits from 26:0 down to 3:0), so it is not a
> style lottery. It is real. It is just not proven to be *conviction*.

---

## CAUSATION SETTLED, 2026-08-30 — the review's attack 3 is answered

The 42 calls ran. Conditions B (bare ask, **no system prompt at all**) and P (placebo) at
temperature 0, item-level McNemar on endpoint share.

**Question 1 — does the balance instruction suppress, against no instruction whatsoever?**

| model | b | c | p |
|---|---:|---:|---:|
| qwen3.8-max | 21 | 0 | **0.000** |
| kimi-k3 | 16 | 0 | **0.000** |
| deepseek-v4-pro | 11 | 0 | **0.001** |
| grok-4.6 | 6 | 0 | **0.031** |
| mistral-medium-3-5 | 5 | 0 | 0.062 |
| claude-opus-5 | 4 | 0 | 0.125 |
| gpt-5.6-terra | 0 | 1 | 1.000 |

*b = endpoint in B, lost in A.* **Four of seven significant; six of seven strictly
one-directional (c = 0).** The suppression is real and it is attributable to the balance
instruction, because the comparison arm has no system prompt to confound it.

**Question 2 — does commitment content add beyond a neutral system prompt?** (P vs D)

Significant on **two of seven only**: mistral (c=21, p=0.000) and kimi-k3 (c=11, p=0.006).
On the other five, a content-free placebo reaches where must-commit reaches.

**The shape of it across all four conditions: A is the outlier.**

| model | A | B | P | D |
|---|---:|---:|---:|---:|
| qwen3.8-max | **19%** | 53% | 60% | 61% |
| kimi-k3 | **6%** | 32% | 27% | 44% |
| deepseek-v4-pro | **23%** | 40% | 45% | 47% |
| grok-4.6 | **11%** | 21% | 21% | 27% |
| mistral | **15%** | 23% | 23% | 56% |
| claude-opus-5 | **19%** | 26% | 29% | 31% |
| gpt-5.6-terra | 47% | 45% | 47% | 52% |

B, P and mostly D cluster; A sits below them all.

**The corrected claim, and it is narrower and better than what it replaces:**

> *A forced-balance instruction suppresses endpoint answers relative to no instruction at
> all. Removing it restores them — and what replaces it does not matter: a bare ask, a
> content-free placebo, or a commitment instruction all reach roughly the same place on five
> of seven models. Only mistral and kimi-k3 respond specifically to commitment content.*

The mask is real, and it is the **balance instruction** doing the masking. The earlier framing
— that a commitment instruction *reveals* something — is wrong on five of seven models. Nothing
needs revealing; the suppression simply stops.

gpt-5.6-terra is flat across all four conditions (45–52%) and is the one model with no
suppression to remove. That is now an observation rather than the "informative exception"
narrative the review correctly killed, since it does not reach significance anywhere.

---

# Original writeup — superseded above, retained for the record

The first result in this project to clear the publication bar set on 2026-08-30.

62 forced-choice propositions, external instrument, 2026 frontier models via OpenRouter,
**temperature 0**, 3 seeds per cell, 8192-token budget. Two conditions: **A**, forced balance;
**D**, must-commit. Both are system prompts of comparable imperative register.

## The result

| model | vendor | A extremity | D extremity | A→D | own floor | verdict |
|---|---|---:|---:|---:|---:|---|
| mistral-medium-3-5 | Mistral | 16% | 54% | **+38** | 11 | clears |
| qwen3.8-max | Alibaba | 23% | 60% | **+37** | 15 | clears |
| kimi-k3 | Moonshot | 6% | 41% | **+35** | 15 | clears |
| grok-4.6 | xAI | 11% | 27% | **+16** | 6 | clears |
| claude-opus-5 | Anthropic | 18% | 33% | **+15** | 10 | clears |
| gpt-5.6-terra | OpenAI | 47% | 54% | **+8** | 6 | clears |
| deepseek-v4-pro | DeepSeek | 24% | 49% | +25 | **32** | inside floor |

**Six of seven models clear their own measured floor, across six vendor families.** The floor
is the largest within-cell spread across seeds for that model and condition — computed per
model, never pooled and never borrowed.

Position over the identical cells, as agree-rate:

| model | A→D agree-rate |
|---|---:|
| grok-4.6 | +8 |
| claude-opus-5, mistral | +3 |
| qwen3.8-max | +2 |
| deepseek-v4-pro | +0 |
| gpt-5.6-terra | −1 |
| kimi-k3 | −5 |

**Extremity moves 8 to 38 points. Position moves −5 to +8 points.** On every model that clears,
the conviction shift is between 2× and 12× the position shift.

## The claim, stated precisely

*A forced-balance instruction suppresses how strongly a model commits to its answers, and
barely changes which answers it gives. Removing that instruction restores the conviction
without relocating the position.*

That is a narrower claim than the study's original thesis — which held that models conceal a
*position* that force reveals — and unlike the original it survives its controls.

## Why temperature mattered more than sample size

At temperature 0.7 the same comparison gave 2 of 5 models clearing, and it looked like a
sample-size problem. It was not. Within-cell extremity spread at 0.7 reached **47 points** on
qwen3.8-max — identical input, different seed. Two effects were **hidden by that noise**, not
created by it:

| model | at 0.7 | at 0 |
|---|---|---|
| gpt-5.6-terra | +2, inside a 3–5 floor | **+8, clears a 6 floor** |
| qwen3.8-max | unmeasurable, 47-point spread | **+37, clears a 15 floor** |

More models would not have fixed this. Decoding did. **Any extremity figure from this
instrument at temperature 0.7 needs its per-cell seed spread reported beside it or it is
decoration.**

## GPT-5.6 Terra is the informative exception

It shows the smallest shift (+8) and it is the only model that starts high — **47% extremity
under forced balance**, against 6–24% for every other model. A model already answering at full
conviction has little left to unmask. That is what the thesis predicts for a model with a weak
balance layer, and it is the closest thing here to a negative control that behaves correctly.

## Against the bar

1. **Three vendor families** — six.
2. **Own floor, per model and condition** — yes, and the one model that fails it (DeepSeek)
   is excluded on its own evidence rather than by assumption.
3. **The statistic the outcome needs** — extremity and agree-rate both reported, so
   "conviction not content" is visible as a contrast rather than asserted.
4. **A hostile read** — not yet. Two design reviews have been run on this project and neither
   has seen this result. **That is the remaining gate and it is not optional**, given seven
   withdrawals.

## Limits

1. **n=3 seeds per cell**, and the floor is a range statistic over three points. Conservative
   but crude; a proper interval needs more runs.
2. **Two conditions.** The placebo (P) is not in this table, and the placebo question — whether
   the effect is about *content* or about *the presence of any forceful system prompt* — is
   open and disputed between channels (`RESULTS-2026-08-30-access-tier.md`). **This result does
   not settle what causes the shift, only that it happens.**
3. **glm-5.3 is incomplete** — condition A produced no valid runs and is not diagnosed.
4. **Extremity is a proxy for conviction**, not a measurement of it. It counts endpoint
   answers on a four-point scale.
5. **One collection window**, one instrument, forced choice throughout.
