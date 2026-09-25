# The noise floor, measured properly — and what it does to v1

> **WORKING NOTES.** Not a finding and not for publication. `STATUS.md` is authoritative;
> where this file disagrees with it, this file is stale. Read any correction block above before
> quoting any number here.


> ## CORRECTION, same day — "FORCING COMMITMENT MULTIPLIES INSTABILITY BY SEVEN" DOES NOT REPLICATE
>
> §3 below reported that condition D side-flips 7 items to condition A's 1, and read that as
> forced commitment destabilising the model. A second model was run. **It reverses.**
>
> | model | A (forced balance) | D (must-commit) |
> |---|---:|---:|
> | gemma2 (9B) | 1 / 62 | **7 / 62** |
> | gemma-4-12B | **11 / 62** | 4 / 62 |
>
> On gemma-4-12B the *balance* condition is the unstable one, by roughly three to one. The
> directional claim in §3 is **withdrawn**. It was one model's property, reported as a
> mechanism.
>
> This is the third time in this project that a clean single-model effect has reversed on the
> second vendor — see the 2026-08-28 correction, which closes with *"one model produced a
> cleaner, stronger, and partly wrong result."* The lesson is not being learned by writing it
> down, so it is now a rule: **no mechanism claim from one model, ever, including one that
> arrives as a control rather than a finding.**
>
> **What survives is stronger than what was withdrawn.** The floor is condition-dependent
> *and* model-dependent, and **which condition is noisier is not predictable from the model or
> the condition.** That is a direct argument for the decision rule in §5 — measure the floor
> per condition per model, never pool it, never borrow it — which was proposed before this
> data existed and is now supported by it rather than by assumption.
>
> One observation held loosely, on one model: gemma-4-12B's condition-A instability
> concentrates in the `none` class (9 of 11 side-flipping items have no research-supported
> answer). A model told to be balanced is least stable exactly where there is no evidence to
> anchor to. Suggestive, unreplicated, and recorded here so it can be tested rather than
> quietly believed.

gemma2:latest, local, 62 forced-choice items. Data:
`runs/2026-08-30-seedsweep/t{0,0.7}/gemma2_latest__{A,D}.jsonl`.

Resolves review finding F2 (`DESIGN-REVIEW-2026-08-29-fable.md`), which pointed out that the
prereg's two noise rules contradict each other: 5 runs per cell *and* temperature-0 replication
cannot both do work, because at temperature 0 the five runs are five copies.

They were five copies. The review was right, and the fix changes what the study can claim.

## 1. The non-determinism was the seed, not the hardware

The 2026-08-29 pilot found conditions C and D varying run-to-run at temperature 0 while A and B
replicated byte-identically. I suspected GPU floating-point reduction on near-tied logits. Wrong.

| options | replies |
|---|---|
| `temperature 0`, no seed | **varies** |
| `temperature 0` + `seed` | identical |
| `temperature 0` + `seed` + `top_k 1` | identical |

Passing *any* seed makes it deterministic. The value does not matter — a sweep of five different
seeds at temperature 0 produced **one distinct reply across all five**. So temperature 0 is
genuinely greedy here; ollama's unseeded path was introducing the variation on its own.

`run_battery.py` now sends a seed by default and records it in every row, so a run is
reproducible from its own record rather than from an assumption about the runtime.

## 2. The real noise floor is sampling variance, and it is condition-dependent

With determinism settled, repeating a seeded call measures nothing. Sampling variance has to come
from sweeping the seed at the temperature you actually deploy at. Five seeds each:

| temperature | condition | distinct replies | items side-flipping across seeds |
|---|---|---:|---|
| 0 | A (forced balance) | 1 / 5 | **0 / 62** |
| 0 | D (must-commit) | 1 / 5 | **0 / 62** |
| 0.7 | A (forced balance) | 5 / 5 | 1 / 62 (ev 0, pr 0, no 1) |
| 0.7 | D (must-commit) | 5 / 5 | **7 / 62** (ev 2, pr 2, no 3) |

A seeded call is deterministic at 0.7 as well — the condition-D file holds 10 runs over 5 seeds
and yields exactly 5 distinct replies, each seed reproducing itself.

## 3. Forcing commitment multiplies the model's own instability by seven

This is a result, not just a control. At the same temperature, on the same model and items, the
forced-balance condition side-flips **1** item across seeds and the must-commit condition
side-flips **7**.

Telling a model it may not hedge does not only move its answers. **It makes them less stable.**
A model under forced commitment is picking among options it is closer to indifferent between,
which is what an unstable forced choice looks like from the outside — and it is the opposite of
what "revealing the model's real position" would predict. A revealed position should be *more*
stable than a hedged one, not seven times less.

Independent support from the same pilot: 86% of what condition pressure changes is intensity
rather than direction (`RESULTS-2026-08-29-pilot-gemma2.md`). Pressure is moving the model around
inside a side, not across sides.

## 4. What this does to v1

**The v1 protocol ran at temperature 0.7** (`WRITEUP-2026-05-26.md` §2.6, and `run_local.py:77`
sampled at 0.7 with `do_sample=True`). Its headline was Gemma 2 moving 3.00 → 5.00 under an
unmask condition.

On this model, at that temperature, **sampling noise alone produces 7 side-flips in 62 items
under the commitment condition.** The v1 measurement did not have a seed-swept noise floor to
compare against, because none was computed — the variance run that exists (2026-05-26-variance,
σ ≈ 0.53) measured score variance on a 1–5 rubric, not answer stability, and it did not separate
seed from sampling.

That does not falsify v1. It does mean **v1's effect and v1's noise were never separated**, and
the burden is now on the effect. Combined with the intensity/direction finding, two independent
routes now point at the same reading: the v1 delta may be a more forceful restatement of an
unchanged position, measured without a floor.

## 5. Decision rules this replaces

Prereg §7 said: *"any displacement under 2.03 units is reported as inside typical run-to-run
variation, regardless of what our own five runs say."* That borrowed number came from another
lab's harness at provider defaults, and the review showed it is also the wrong construct
(p90 of single-run-from-centroid, where our claims are centroid-to-centroid).

Replace with, and commit before further collection:

1. **Collection is at temperature 0 with a fixed, recorded seed.** The deterministic answer is
   the measurement. n=1 per cell is then correct and honest; five copies were never data.
2. **The noise floor is measured separately by seed sweep at 0.7**, per condition, because it is
   condition-dependent by a factor of seven and a single pooled floor would be wrong for both.
3. **Any claim about deployed behaviour must clear its own condition's 0.7 band**, not condition
   A's. A six-side-flip effect under D does not clear D's seven-side-flip floor.
4. The 2.03 figure is retained only as an attributed external reference, never as our gate.

## Limits

1. **One model.** gemma2:latest, 9B, quantised, local. The seven-fold condition asymmetry is one
   model's property until a second is run.
2. **Two conditions.** A and D only; B and C are not swept.
3. **Five seeds.** Enough to establish that the floor is non-zero and condition-dependent, not
   enough to put a confidence interval on it.
4. **ollama-specific.** The unseeded non-determinism is a property of this runtime. Nothing here
   describes API providers, which mostly do not honour a seed at all — for those, the floor
   cannot be eliminated and must be measured.
