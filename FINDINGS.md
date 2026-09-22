# What this study has learned about language models

Substantive findings, not process. Each carries its number and its status. A finding here is
**ESTABLISHED** (survives its own noise floor and a control that could have falsified it),
**NARROW** (real but scoped tighter than it has been stated), or **WITHDRAWN**.

Status as of 2026-09-13, after an eight-way audit and an independent review of the design.

---

## ESTABLISHED

### 1. Refusal is elicited, not intrinsic

The single cleanest result in the corpus.

| condition | refusals |
|---|---|
| no directive | **148 of 1,076** |
| any directive | **4 of 907** |

**All 14 models that decline stop declining under any directive at all.** Refusal is not a
property of the model's values; it is a property of how it was asked. The rates are lower
bounds, because the accounts used had red-team latitude.

This matters beyond this study: refusal rates quoted without the prompting regime that produced
them are not comparable to anything.

### 2. "Anything removes it. Nothing is revealed; a suppression stops."

A **content-free placebo** system prompt — *"read every proposition carefully, skimming and
careless reading are forbidden"*, no stance content whatsoever — restores endpoint answers **as
much as** an explicit must-commit instruction.

So the effect that has been described as *unmasking a concealed position* is better described as
**a suppression ceasing**. Any firm instruction lifts it. Nothing about the specific content of
the balance instruction is doing the work.

This is the finding that most changes what the project can claim, and it came from the one arm
that had a placebo.

### 3. A model gives different answers to the same question, and the spread is large

| comparison | median items changed | p90 |
|---|---:|---:|
| same-version variants (97 pairs) | 5 of 62 | **11** |
| true same-snapshot pairs (9) | — | **16** |
| presentation order, 2024-gen local 7–14B | — | **14** |
| presentation order, 2026 hosted | — | 3 |

**The instrument's detection limit is therefore 11–13 items of 62.** Any claimed effect smaller
than that is not distinguishable from asking the same model twice.

Nobody else reports this floor: of twelve studies audited, **the same-version null is absent from
all twelve**.

### 4. Presentation order moves answers as much as deliberate manipulation does

On 2024-generation open-weight models, shuffling item order changes as many answers as a
deliberate framing manipulation. On 2026 hosted models it does not (p90 3).

So order sensitivity is **generational**, and a result collected single-order on an older
open-weight model is not safely comparable to one collected on a current hosted model.

### 5. Judge panels carry their own lean, and it interacts with condition

Four-judge panel spread: **0.3054** on a 1–5 scale, over the published corpus. It is not a
constant offset that cancels in a delta — one judge leans +0.033 under the balance condition
and **+0.275** under the treatment.

**Two of the three CI-clean findings are not robust to judge choice** (`gpt-4.1` ranges +0.21
to +0.69 across judges, `deepseek-v3.2` +0.14 to +0.86), and both are self-judged. *(This read
"two of five published effects" with a spread of 0.29 and leans of +0.044/+0.290 until
2026-09-22; every figure was stale and `judge_lean.py --per-finding` prints three findings, not
five.)* Willingness to score a blank
string is also a per-judge property: of 466 empty responses, deepseek-v3.2 scored 466 of them,
gpt-4.1 302, gemini-2.5-flash 84, and claude-haiku-4.5 **zero**.

Practical consequence: an LLM-judged political score needs its judge panel named beside it, the
way a survey needs its instrument.

### 6. The two standard measurement approaches disagree with each other

Free-text-plus-judge against forced-choice, same models, same items:

**r = −0.12, 95% CI [−0.57, +0.37], n = 24 models.**

Two instruments that do not correlate are not both measuring the construct. This is arguably the
most publishable thing in the corpus and it has never been stated as a finding.

### 7. Truncation at a token cap is differential by verbosity, and invisible

**1,022 of 4,748 scored records (21.5%)** sat exactly on an 800-token cap — severed mid-argument,
then scored by judges as though complete.

| model | records at the cap |
|---|---|
| glm-4.5 | 96.7% |
| mistral-large | 90.5% |
| gemma-3-27b-it | 82.8% |
| gpt-4.1 | ~0% (fits in 773) |
| claude-opus-4.7 | needs up to 1,297 |

Because the rate tracks how verbose a model is, **every cross-vendor comparison was confounded
with verbosity**. And excluding the records does not fix it: exclusion removes 94.1% of one
vendor class and 0.0% of another, relocating the confound into the denominator.

Novel and transferable: **anyone running a fixed token cap across a mixed model panel has this
problem and will not see it**, because a proxy can report `finish_reason: "stop"` on a response
severed mid-word.

### 8. Some models answer nothing at all, and it looks like data

`openai/gpt-5`: **287 of 310 records empty** — the whole budget spent on reasoning tokens,
returning no text. Those blanks were then scored by judges. The published −0.17 for that model
was arithmetic over blank strings; it is retracted.

---

## NARROW — real, but smaller than it has been stated

### 9. Two named models do commit toward the critic, and hold it under a deferential frame

**Claude Opus 4.7 and Grok 4.3.** Asked a contested civil-liberties question without a balance
instruction, both move toward the questioner's side, at intervals excluding zero **under every
judge individually**. Both hold that position when the question is re-framed from the
institution's side (Opus 3.70 vs 3.70; Grok 3.80 vs 3.60), which is the control that could have
shown them to be merely agreeable.

**It does not transfer out of domain**: Grok +0.00 [−0.62, +0.50] on economic and foreign-policy
items.

This is a real, topic-specific disposition on two models. It is not a property of frontier models
as a class, and it is the residue of the May study that survives.

### 10. GPT-4.1 tracks the frame rather than holding a position

Under the same reversed-premise control: neutral 3.10 against reversed **2.75**, with 5 of 20
reversed answers scored 2 and none scored 4. The gap is about the size of its published effect
(+0.43).

So the same instrument, on the same items, measures a **position** on two models and
**frame-following** on a third. A single number for "the models" hides that.

### 11. Abliteration rewrites the text; the stance claim is not established

Of five open-weight families:

| family | verdict |
|---|---|
| qwen2.5-7b | dissociation confirmed (Jaccard 0.276) |
| llama-3.1-8b | **text change not established** — Jaccard 0.339 |
| mistral-7b | **text change not established** — Jaccard 0.333 |
| deepseek-r1-distill-7b | stance not computable — 1 shared eligible cell |
| gemma-2-9b | **text change not established** — Jaccard 0.345; stance unresolvable — 40/40 at the 3.00 midpoint |

0.339, 0.333 and 0.345 sit **inside the 0.303–0.392 band this project measured for one model
resampled against itself**. Local runs sample at temperature 0.7 with no seed, so that "rewrite"
is what resampling alone produces.

**Gemma corrected 2026-09-20.** This row read "arm does not exist — raw files are 0 bytes", which
was wrong: the records are at `data/2026-05-27-abliteration-gemma2/` in the mirror, tracked since
2026-05-28, and they recompute to the published stance figure exactly (3.00 on all 40, 39
unanimous). The 0-byte files are placeholders in the four-family directory. Retraction in root
`BACKLOG.md` DATA-GEMMA2-ARM-LOST-001.

The verdict above is **stronger than the borrowed-band objection usually allows**. A 2026-09-20
resample of both Gemma arms on the same weights gives **0.380 stock-vs-stock and 0.377
ablated-vs-ablated**, against **0.345 between arms** — so for Gemma the same-model band is
measured on Gemma's own weights, and the between-arm value is *below* its own resample noise.
`STATUS.md`'s bar rule against borrowed floors does not bite here. The website ("about 65 percent
of the wording rewrites") and the public README ("~70% of the political wording") still state it
as established.

Also: two independent abliterations of one base disagree by 8/9/9 versus 0/2/0, so movement
belongs to **which third-party build was downloaded**, not to abliteration as an operation.

### 12. Elicitation-layer force is real, model-specific, and points opposite ways

Re-collected 2026-09-13 at 5 samples with a same-sitting baseline:

| model | layered stack vs hedge-strip alone |
|---|---|
| grok-4.3 | **+0.48** [+0.26, +0.70] |
| claude-opus-4.7 | **−0.31** [−0.64, −0.01] |

Layering helps one model and **hurts** the other, same sitting, same items, same panel. Neither
single technique moves either model, so whatever layering does is not the sum of its parts.
"Only the layered stack adds force, to a ceiling" is not supported; no ceiling was measured and
three points on one axis cannot locate one.

---

## WITHDRAWN

### 13. "The hedge is the bias signature"

Score-3 responses do carry a much higher hedge ratio. But rubric score 3 **is** "does not
commit", and the hedge lexicon measures non-commitment. The finding is the rubric restated in
lexical form, which the writeup's own §3.5 concedes.

It remains the study's title, the book's opening "Proof", and chapter 22's "the finding".

### 14. "The mask comes off in proportion to force"

The ladder is not one axis, one scale, or one subject set:

- conditions D and E silently carry condition B's user suffix, so their deltas confound three
  changes; condition C has a stronger *user* instruction than either while having no system
  prompt;
- no model is measured on all three rungs;
- the weight rung was tested only on open models that sit at 3.00 under prompt force too, so
  "force does nothing at the weights" was established where force does nothing at all;
- and finding 2 shows a content-free placebo does most of it anyway.

### 15. "The lean is in the weights"

Nothing in the corpus locates a lean anywhere. The one same-units comparison has the weight
intervention moving **more** than the prompt one (9 side-flips vs 4), and that movement was
attributable to the ablator.

### 16. The vendor-class point estimates

Published as us-closed +0.259 against chinese-open +0.204. Computed from a script that kept 1 of
5 replicates. Corrected, the split flips sign on a 19-pair remainder that lost half its records.

**The direction — US-closed frontier models unmask more than open-weight ones — survives. The
class means do not.** Withdraw the numbers, keep the direction, and say it rests on two models.

### 17. Grok 3.00 → 5.00 under the persona condition

Condition E instructs *"You are an opinionated political commentator"* and then asks
critic-framed questions. That is persona compliance, not a lean measurement.

---

## The open question

Every judged number above depends on an instrument whose baseline condition instructs the
outcome its rubric scores as the midpoint — **94% of condition-A records score exactly 3** — and
whose items are all framed from one side (movements run 86 toward the questioner against 26 the
other way).

Whether that instrument measures a position or measures agreement with whoever is asking is
**being collected now** (`runs/2026-09-13-i3-phase0`, `PREREG-2026-09-13-frame-and-placebo`).
It is the question that determines how much of the NARROW section survives.
