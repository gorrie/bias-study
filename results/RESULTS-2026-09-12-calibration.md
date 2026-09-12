# Are this study's confidence intervals and FDR flags calibrated?

**STATS-BOOTSTRAP-CALIBRATION-001.** Rig: `scripts/calibration_study.py`. Run on the M5,
2026-09-12. Nothing here re-reads the study's results; it tests the study's *estimators* against
data generated from a known truth.

## Why this was asked

The existing resampling tests prove **reproducibility** — the same seed gives the same interval.
That is not calibration. Calibration is whether a "95% CI" covers the truth 95% of the time, and
whether a flag at q=0.05 keeps the false-discovery rate near 0.05. Those are different claims and
only the first had ever been checked.

It matters because this design is not the textbook case the percentile bootstrap is usually
justified against:

| feature | value in the published main run |
|---|---|
| scale | ordinal, 1–5 integers; 602 of 733 scores are the single value **3** |
| ties | **69.2%** of per-question deltas are *exactly* zero; the rest are ±1 and ±2 |
| k per model | 30 for most models, but **18** and **3** occur |
| multiplicity | 13 models tested together, corrected with Benjamini–Hochberg |

A distribution that is 69% one tied value is precisely where percentile methods are known to
struggle.

## Method

The null is the observed delta distribution, **symmetrised so the true mean is exactly zero
while preserving the 69.2% tie share**. (An earlier cut mirrored the positive tail instead and
diluted the zeros to 53%. That is a friendlier distribution and it made the estimator look
better than it is — recorded because the tie share is the entire reason this check is worth
running.) The study's own `bootstrap_ci`, `bootstrap_p_two_sided` and `benjamini_hochberg` are
imported and called; nothing is reimplemented.

## Result — the intervals are mildly anti-conservative, everywhere

12,000 trials per cell, 400 bootstrap resamples:

| k | CI coverage (nominal .95) | distance from nominal | type-I at .05 |
|---:|---:|---|---:|
| 8 | **0.938** | 5.6 SE below | 0.066 |
| 18 | **0.935** | 6.8 SE below | 0.067 |
| 30 | **0.944** | 2.8 SE below | 0.057 |

This is a **systematic** shortfall, not noise and not a quirk of one k. A nominal 95% interval is
really about 94%, and a flag at p ≤ 0.05 fires about 6% of the time when nothing is happening.
Coverage is closest to nominal at k=30, which is where most of the study lives, and worst at
intermediate k — `google/gemini-2.5-pro` sits at k=18 in the published main run.

At k=3 the procedure turns sharply **conservative** (coverage 0.984, type-I 0.022): with three
tied-heavy values the bootstrap distribution is too coarse to reject. That is the safe direction,
but it means a k=3 row cannot detect anything and should never be read as a null.

## Result — BH-FDR holds where the study operates

13 models, 4 carrying a true +0.5 shift, q = 0.05:

| k | realised FDR | power |
|---:|---:|---:|
| 3 | 0.024 | 0.61 |
| 8 | 0.056 | 0.39 |
| 18 | 0.072 | 0.69 |
| 30 | **0.047** | **0.90** |

At k=30 the realised FDR is 0.047 against a nominal 0.05 and power is 0.90. At intermediate k it
runs over q, inheriting the inflated type-I above rather than any fault in BH itself.

## What this licenses, and what it does not

**Licensed.** The k=30 results — the bulk of the published corpus — rest on a procedure whose
error rates are close to what they claim. The five significant models in `2026-05-25-full` are
not an artifact of a broken estimator.

**Not licensed.** Treating a binary flag as a validated inferential decision at small or
intermediate k. The correct reporting is the effect and its interval, with the flag as a
convenience; a result whose entire weight rests on `p = 0.04` at k=18 is standing on a procedure
that rejects 6.7% of true nulls.

**A k=3 row is not evidence of absence.** This is the statistical form of the same sentence the
eligibility correction produced: `z-ai/glm-4.7` collapses to k=3 under the rule, and at k=3 this
procedure has essentially no power. It cannot say "no effect"; it can only say "nothing seen."

## Recommended, not done here

A BCa or studentised bootstrap would recover most of the coverage shortfall, and a permutation
test on the paired A/B structure would sidestep the tie problem entirely. Both are design
changes to a frozen instrument and belong in the next cut, pre-registered, not retrofitted to
published numbers.

## Multiplicity policy for the next study

Correct **within a family, across models, at the level the claim is made**. The published runs
correct across the 13 models in a run, which matches how the headline is stated ("N models show
…"). A claim about one named model needs no correction; a claim about "models in general" needs
this one. State which is being made before collection, not after.
