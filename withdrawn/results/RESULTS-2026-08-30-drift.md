# Drift: newer versions suppress endpoint answers harder under a balance instruction

> ## SUPERSEDED 2026-08-31 -- THE NULL WAS UNDERPOWERED
>
> This result compared version transitions against a null built from THREE points (the
> gpt-5.6 sibling trio). The wide sweep supplies 97 same-version pairs, whose |b-c| has a
> median of 9 and a p90 of 22 -- roughly double what three points suggested.
>
> Against that null, 3 of 108 version transitions clear, two of them into the same model
> and one in the OPPOSITE direction. The claim below is withdrawn. See
> RESULTS-2026-08-31-drift-does-not-replicate.md.


Three vendor lineages plus a same-generation null. Temperature 0, seeded, 3 runs per cell
(2 for one), item-level paired test, condition A (forced balance) only.

## The result

Endpoint-answer share under forced balance, by version, with a McNemar exact test between
consecutive versions on the 62 paired items:

| lineage | version | endpoint share | vs previous | p |
|---|---|---:|---|---:|
| **Anthropic** | claude-opus-4.6 | 42% | — | — |
| | claude-opus-5 | **15%** | b=17, c=0 | **0.0000** |
| **xAI** | grok-4.3 | 31% | — | — |
| | grok-4.5 | 26% | b=8, c=5 | 0.581 |
| | grok-4.6 | **11%** | b=9, c=0 | **0.0039** |
| **Moonshot** | kimi-k2.5 | 26% | — | — |
| | kimi-k2.6 | 19% | b=5, c=1 | 0.219 |
| | kimi-k3 | **6%** | b=9, c=1 | **0.0215** |
| *OpenAI siblings (null)* | gpt-5.6-luna | 45% | — | — |
| | gpt-5.6-sol | 39% | b=6, c=2 | 0.289 |
| | gpt-5.6-terra | 45% | b=1, c=5 | 0.219 |

`b` = items that were endpoint answers in the older version and are not in the newer.
`c` = the reverse. **b > c means endpoint answers were lost across the version bump.**

## Why the null matters more than the effect

GPT-5.6 Luna, Sol and Terra are **the same generation** — sibling variants, no version
ordering between them. They are the control for "different model names produce different
numbers," and they behave correctly: neither transition is significant, and the b/c splits go
in *opposite* directions (6/2 then 1/5). Sibling variation is noise-shaped.

The three real lineages are not: **17/0, 9/0, 9/1.** Almost nothing moves the other way.

Without that null this table would be uninterpretable, because a version bump changes an
unknown amount besides version.

## What it says, stated narrowly

*Across three vendor lineages, the newest release answers with significantly fewer endpoint
answers under a forced-balance instruction than its predecessor, while same-generation
siblings show no such change.*

That is the closest thing this project has to support for the drift half of its thesis — and
it is **not** "models are becoming more biased." Position is not what moved. What moved is how
readily a model gives an unqualified answer *when instructed to be balanced*. The balance
instruction has become more effective at suppressing endpoint answers across successive
releases.

## What it is not, and the limits that matter

1. **A version bump is not a controlled variable.** "The same lineage" is a vendor naming
   convention. Parameter count, architecture, training data and serving stack can all change
   between `opus-4.6` and `opus-5`. The sibling null bounds the *naming* confound; it does not
   bound the *architecture* confound.
2. **Only the middle transitions in two lineages are significant.** grok-4.3 → 4.5 (p=0.58)
   and kimi-k2.5 → k2.6 (p=0.22) are not. The monotone-looking descent is two non-significant
   steps followed by one significant one, in both cases.
3. **Condition A only.** The *masking index* (D − A) showed no drift once read against the
   sibling null. This is a claim about the baseline, not about the size of the effect that
   instruction has.
4. **n=3 seeds**, modal answers, and kimi-k3's A cell has 2. Two cells returned identical text
   across seeds — expected at temperature 0 and not caching, but it means those cells carry no
   sampling information.
5. **Endpoint share is a proxy.** It counts Strongly Agree / Strongly Disagree on a four-point
   forced choice. The 2026-08-30 hostile review is right that calling it "conviction" is
   interpretation, and that applies here too.
6. **No hostile read yet.** Every other result in this project that went unreviewed was later
   narrowed or withdrawn. This one is fresh and should be treated accordingly.
