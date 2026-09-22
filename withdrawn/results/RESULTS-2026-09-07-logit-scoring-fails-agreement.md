# Logit scoring: feasible, and it fails its own pre-registered agreement check

**Measured** 2026-09-07 on local models, no API spend.
**Reproduce:** `python scripts/logit_probe.py --separability` then
`python scripts/logit_probe.py --model qwen2.5:14b --letter-bias --agreement`.

## What was being tested

`RELEASE-v2.md` calls logit scoring **"the one thing v2 should still add, and it is free"**,
claiming it removes, for open-weight models, every one of:

- 4 models that produce no valid answer sheet under any condition
- `gemma-4-12B` budget-exhausting 12 of 15 runs
- **28.2%** of condition-A runs invalid, mostly refusals
- three ablation pairs excluded for tokenizer garbage or inventing their own questions

It also pre-registered the decision rule: *"It is a second instrument, and a second instrument
needs its own agreement check against the parsed one before any number from it is published…
prototype it now, publish it in v2 only if the agreement check is clean, otherwise v3 with the
prototype already built."*

**The agreement check is not clean. The rule resolves to v3.**

## Four findings, in the order they land

### 1. The capability is real, on a different route than recorded

`RELEASE-v2` records "ollama 0.33.1 returns `top_logprobs` at Q4 on the current card, verified"
without recording *which endpoint*. Ollama's native `/api/chat` accepts `logprobs` and
`top_logprobs` in `options` and returns **neither** — silently, with a normal response and no
error. `/v1/chat/completions` returns them properly.

That matters because `/api/chat` is the route this study's collector uses everywhere else, so
the first attempt looked like the feature was absent. A capability note without its route is a
capability note that costs the next person an hour.

### 2. The option labels are not separable at the first token

The instrument's four options, and the first token each model actually emits for them:

| option | first token |
|---|---|
| Strongly Disagree | `'Strong'` |
| Disagree | `'Dis'` |
| Agree | `'Ag'` |
| Strongly Agree | `'Strong'` |

**Three distinct tokens for four options**, identically on `qwen2.5:14b` and `phi4:latest`.
`Strongly Agree` and `Strongly Disagree` share their prefix, so a single-position logprob
comparison cannot tell agreement from disagreement *at the strong end* — which is precisely the
distinction the endpoint statistic is built on.

So scoring the four labels by their leading token is not available. That is not a tuning
problem; it is what the tokenizer does.

### 3. The letter form is separable — and it is a different instrument

Remapped to `A = Strongly Disagree … D = Strongly Agree`, all four letters are single tokens and
all four appear in the top-20 with usable logprobs on both models. 62 of 62 items scored, none
missing a letter. So logit scoring **works** — over a prompt that asks the question in a
different format.

### 4. It does not agree with the parsed instrument, and it is not invariant to its own legend

Against `qwen2.5:14b`'s parsed modal over 105 valid sheets in the corpus:

| | |
|---|---|
| exact match | **24 of 62 (38.7%)** |
| side-flips | **20–21 of 62** |

Judged against this study's own floors rather than a hoped-for number: the modal estimator's
side-flip p90 is **3** and the run-to-run replicate p90 is **5**. Twenty side-flips is four
times the replicate floor and seven times the estimator. The two instruments are measuring
materially different things, so **the logit numbers cannot inherit the parsed instrument's
published floors** — every floor, detection limit and MDR in this study would have to be
re-measured on the new format before any of its numbers meant anything.

And the reason is worse than a format difference. The position distribution is lopsided —
18 Strongly Disagree, 1 Disagree, 43 Agree, and **not once** Strongly Agree — so the obvious
suspect is letter preference, a documented artifact of multiple-choice formats. The control for
that is to reverse the legend, which changes no proposition and no option, only the order they
are listed in:

| mapping | Strongly Disagree | Disagree | Agree | Strongly Agree |
|---|---:|---:|---:|---:|
| `A = Strongly Disagree …` | 18 | 1 | 43 | 0 |
| `A = Strongly Agree …` (reversed) | 12 | 22 | 2 | 26 |

**Reversing the legend changed 48 of 62 positions.** A format reading content should be
invariant to it. This one is not.

The attribution is *undecided and does not matter*: the position held on 14 items and the letter
held on 14 — a margin of **zero**. Whether the residual is letter preference is a second-order
question, and 23% stability under an irrelevant transformation disqualifies the format either
way.

## The decision, by the rule that was written first

Logit scoring goes to **v3, with the prototype built** — which is exactly the fallback
`RELEASE-v2` specified. The prototype is `scripts/logit_probe.py` and it is the useful artifact:
the next attempt starts from a measured account of why the obvious design fails.

**And the framing in `RELEASE-v2` needs correcting.** "It is free" is true of API spend and
false of everything else: it is one call per item against one call per sheet (62× the requests),
it is a second instrument requiring its own floors, and the letter form it forces is not
legend-invariant. The four problems it would have solved are real; the solution as described
would have traded them for a format whose answers move when you reorder the answer key.

## What would make this work, if it is picked up again

Stated so the next attempt does not repeat this one:

- **Score a forced continuation, not a first token.** The labels collide only at position one.
  Scoring the full label sequence's total logprob — via prefill or an echo-style API — keeps
  the original wording and sidesteps the letter form entirely. Ollama's chat route does not
  expose that today; `llama.cpp` directly might.
- **If the letter form is kept, the legend must be randomised per item and the position
  averaged over permutations.** That is the standard remedy for option-order bias, it multiplies
  the call count again, and it must be validated by the same reversal control before use.
- **Re-measure every floor on the new format.** It cannot borrow the parsed instrument's.
- **Test more than two models.** Both models here collide identically at `'Strong'`, but the
  agreement and invariance checks were run on one.

## What this does not change

No published number moved. This is a feasibility measurement of a proposed second instrument;
the parsed instrument and all of its floors are untouched.
