# Pilot: identity-free pressure sharpens, it does not turn

> **WORKING NOTES.** Not a finding and not for publication. `STATUS.md` is authoritative;
> where this file disagrees with it, this file is stale. Read any correction block above before
> quoting any number here.


First collection under the new instrument. **One model, gemma2:latest, local, 5 runs per
condition at temperature 0.** A pilot, not a finding — every number here needs a second model
before it means anything. Reported now because it corrects two things I asserted earlier the
same day, and because it converges with an independent design review on the same defect.

Data: `runs/2026-08-29-noisefloor/gemma2_latest__{A,B,C,D}.jsonl`, 20 runs, all valid
(62/62 items parsed, no run discarded).

## The harness works

62 forced-choice items, batched, strict parser, output shaped to the comparison dataset.
20/20 runs yielded exactly 62 clean answers. No fills, no midpoints, no discards.

## Correction 1 — the noise floor is not uniformly zero

I stated earlier today that the temperature-0 noise floor was "exactly zero, so every
difference from here is above the floor by construction." That is true for two conditions and
false for the other two:

| condition | run 1 vs run 2, text identical | answers differing | of which side-flips |
|---|---|---:|---:|
| A (forced balance) | yes | 0 / 62 | 0 |
| B (bare ask) | yes | 0 / 62 | 0 |
| C (drop-hedging) | **no** | 4 / 62 | 0 |
| D (must-commit) | **no** | 3 / 62 | **1** |

D's within-condition floor is one side-flip. I was about to report six side-flips for D as a
result against an assumed floor of zero. Six against a floor of one, at n=5, is thin.

Cause not established. Temperature 0 should be greedy; near-tied logits under GPU
floating-point reduction are the obvious suspect and are not confirmed here. Recorded as
measured behaviour, not explained.

## Correction 2 — my change metric conflated two different things

The first analysis counted any change in exact position (SD/D/A/SA) as a change, and produced a
**negative** specificity index (−26.8, −22.3, −12.7), i.e. pressure moving `evidence` items more
than `none` items — the opposite of prediction 9.

That metric is wrong. Decomposed:

| condition | items changed | side-flips | intensity-only |
|---|---:|---:|---:|
| B | 17 / 62 | 0 | 17 |
| C | 19 / 62 | 2 | 17 |
| D | 22 / 62 | 6 | 16 |

**Across B/C/D, 50 of 58 changes — 86% — are intensity, not direction.** The model does not
change its mind when told to stop hedging. It says the same thing more strongly.

An independent design review (`DESIGN-REVIEW-2026-08-29-fable.md`, F1) found the identical
defect in the persona analysis behind Amendment 2, from the other direction: recomputed at the
binary level, persona change rates are 21.7 / 37.1 / 43.7 rather than the 60.9 / 68.8 / 61.2
exact-position rates that amendment quoted. **Two independent routes to the same conclusion:
exact-position change is the wrong statistic for a binary outcome.**

## Correction 3 — the item classes are not exchangeable, and prediction 9 is unusable as written

The review's sharper point, verified here against this pilot's own baseline:

| class | n | at scale extremes | boundary-adjacent |
|---|---:|---:|---:|
| `evidence` | 20 | 4 (20.0%) | 16 |
| `premise` | 20 | 2 (10.0%) | 18 |
| `none` | 22 | **0 (0.0%)** | 22 |

An extreme answer needs two steps to cross the agree/disagree boundary; a boundary-adjacent one
needs a single notch. **Every `none` item in this baseline is one notch from flipping and no
`evidence` item at an extreme is.** So pure ±1 jitter mechanically produces "moves `none` more
than `evidence`" — which is prediction 9's success condition.

**Prediction 9 as committed can be satisfied by exactly the churn it exists to detect.** It is
withdrawn as worded and must be restated with the metric level and the stratification named
before any further collection. This is a design defect, not a result.

## What survives, stratified

Side-flips against condition A, restricted to boundary-adjacent items so the classes are
comparable:

| condition | evidence (n=16) | premise (n=18) | none (n=22) |
|---|---:|---:|---:|
| B | 0.0% | 0.0% | 0.0% |
| C | 0.0% | 5.6% | 4.5% |
| D | 6.2% | 11.1% | 9.1% |

Small everywhere, and the ordering the amendment predicted is not clean. The load-bearing
observation is not the ordering — it is the **magnitude**. Even stratified, identity-free
pressure flips at most one item in nine.

And on the review's preferred statistic — signed per-item movement toward the
research-supported answer, where churn expects 0:

| condition | evidence items | premise items |
|---|---:|---:|
| B | **+0.350** | +0.200 |
| C | +0.100 | +0.000 |
| D | +0.200 | +0.050 |

**Positive.** Removing the hedge moved this model *toward* the research-supported answer, not
away from it.

## The contrast worth having

| manipulation | what it does |
|---|---|
| identity-free pressure (B/C/D) | 86% intensity change, ≤1 side-flip in 9, signed movement **toward** the key |
| identity assignment (their persona data) | large change, and 2 of 14 personas drive concordance **below the 50% chance line** |

Stated as a hypothesis for the next model, not as a finding from one: **pressure sharpens;
identity distorts.** Those are different operations on a model, and the 1–5 stance rubric used
in v1 cannot tell them apart — a more forceful statement of an unchanged position scores higher
on it.

That is now the leading explanation for v1's Gemma 3.00 → 5.00 headline, and this pilot is on
the same model family. **It is not confirmed** — v1 used different items, a judge, and
temperature 0.7 — but the mechanism is present in gemma2 under this instrument, and the burden
has shifted.

## Manipulation check (review F4) — passes

The review warned that forced choice may already forbid hedging, leaving C/D nothing to remove
and making a null uninterpretable. Measured: extremity (share of SD/SA) moves 9.7% at A → 33.9%
at B, 21.0% at C, 29.0% at D. **The manipulation reaches the model**, so a small displacement
here is a real null rather than format saturation.

## Limits

1. **One model, 9B, local, quantised.** Nothing generalises.
2. **Modal-answer analysis over 5 runs**, with a non-zero within-condition floor on C and D.
3. **Baseline is condition A**, which is itself a manipulation. A no-system-prompt origin cell
   is not yet collected.
4. **No placebo instruction** (review F3). Displacement under C/D is not yet attributable to
   *anti-hedging* content rather than to any forceful system prompt.
5. The `evidence`/`none` classification remains inherited and unaudited.
