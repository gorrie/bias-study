# No position, only consensus: what political instruments actually measure in language models

## What a forced-choice political instrument measures when nothing has changed

> **Title set by the author, 2026-09-21.** It names the claim the rest of the paper argues:
> instruments of this class were built to locate a model on a political axis, and the
> coordinate is the part that moves — reprinting the same questions shifts it as much as the
> instruction does. What holds still is that the panel agrees, and agrees most emphatically
> where the record is thinnest.
>
> One word is not the author's. The proposed second half read *"as much as facts"*, and there
> is no facts arm — nothing here varies the truth of a proposition. The comparison the study
> actually ran is against the balance instruction, so *instruction* is what the title claims.
> The nearby true statement about facts is in §3b, where it belongs: 97.1% on contested
> politics against 98.9% on matters of record.
>
> *Same Version, Different Answers* was the previous title and is withdrawn. It named a
> same-version null this corpus measures at **0 / 1 / 1 side-flips of 32** — the finding it
> advertised is not there. `CITATION.cff` is written against the title above.

**Draft. Every table is generated from `runs/` by the scripts named in Reproduction. Nothing
between `<!-- GEN:x -->` and `<!-- /GEN:x -->` is hand-written; `scripts/gen_paper.py --check`
exits 1 when a table has drifted from the data.**

> **STATE OF THIS DRAFT, 2026-09-19. Read this before quoting any number.**
>
> **The corpus, and it has stopped moving.** Every figure in this paper is computed across
> 3,897 runs and 65 models, collected between May and 2026-09-21 and frozen when the pinned
> omission arm closed. The refusal table carries 23 vendor families as its rows, of which
> 21 rows are vendor families in the ordinary sense; the other two are a model-hosting domain
> and a community fine-tuner of other people's weights, kept as rows because their builds are
> subjects here and excluded from any claim about vendors.
>
> **That population is declared, not swept.** `refusal_table.PANEL` names the run directories
> the panel consists of and `OUT_OF_PANEL` names every other battery collection with the rule
> it falls under — smokes, budget probes, and arms collected under one or two conditions,
> whose one-sided denominators would move a refusal rate without a single new observation
> about refusal. Until 2026-09-21 the population was a glob minus a list of seven directories
> that had all been retired, so the list subtracted nothing and every arm collected after it
> was written had joined the panel unasked. Those figures read 6,286 runs and 71 models.
>
> **Four sections argued a direction the data reversed, and have been rewritten rather than
> updated.** On the retired 62-item questionnaire the same-version null was the *largest*
> nuisance in the table; on the 32-item battery it is the *smallest*, and it sits below its own
> detection limit. That inverts §7 end to end, §2's "What does not shrink", §2's reference-scale
> subsection, and §3's claim about which limit governs. Every withdrawn figure is listed in
> place, not deleted — the ledger at the foot of §7 is the largest.
>
> **The direction of those errors is not random: every one of them made this paper's case
> stronger than the data supports.** That is worth saying out loud in a paper about other
> people's unreported nuisance factors.
>
> **The estimator question is settled by measurement, not by preference.** It was an open
> author call until 2026-09-19 — sheet bootstrap or exact permutation, disagreeing on 20 of
> 241 pre-registered contrasts, all in the same direction. Rather than choose, we measured
> both against a null built by splitting real cells in half, where no treatment exists and
> every rejection is therefore false: **the bootstrap rejects 10.5% of true nulls and the
> exact test 4.5%** (`calibrate_estimators.py`, 200 splits of 136 cells). The paper reports
> the exact test. The bootstrap is retained as a sensitivity check and every figure says which
> it used.

---

## 1. The manipulation and the nuisance are the same size

Put thirty-two political propositions to a language model with no system prompt, and score the
position its answers imply. Now add the instruction this study exists to measure — *answer in
a balanced manner, present arguments on multiple sides, do not take a personal position.* The
position moves. Across **38 of 61 pairs** the movement clears a bootstrap that resamples whole
answer sheets and a Benjamini–Hochberg correction over the whole pre-registered family, whose
size is generated into §9.1 rather than stated here — this sentence previously typed it as 153
contrasts, three other documents typed it too, and the four disagreed. The median movement is **0.131**
on a scale running −1.5 to +1.5.

That is the finding every instrument of this class is built to produce, and on its own it looks
like a result.

Now change nothing at all. Print the same thirty-two propositions to the same models under the
same bare condition, in a different order.

**The position moves on 43% of pairs, with a median of 0.088.**

<!-- GEN:position -->
| measured the same way, on the same sheets, with the same estimator | pairs | median \|effect\| | p90 | max | clear BH-FDR |
|---|---:|---:|---:|---:|---:|
| the balance instruction (A − N) | 61 | **0.131** | 0.327 | 0.706 | 38 (62%) |
| **reprinting the items in a different order** (N, seed vs seed) | 108 | **0.088** | 0.281 | 0.575 | 46 (43%) |
<!-- /GEN:position -->

The instruction's median effect is **1.5 times** the median produced by a factor that carries
no information whatsoever, and it sits **below the 90th percentile** of that factor's own
distribution. Both are real; neither is large; and a study that reports the first without
measuring the second is reporting a number it cannot attribute.

This is not the claim that the effect is inside the noise. It is the sharper one: **the
nuisance is an effect too, and the same size.** Item order is not a confound that careful
design removes — the orders here were randomised, mirror halves held apart, and every sheet's
order recorded. Randomisation makes the factor unbiased. It does not make it small.

### The control arm behaves, and that is how we know the estimator does

The design carries a third condition, `P`: a forcefully worded instruction that mentions
nothing political — *read every proposition carefully; skimming, guessing and careless reading
are forbidden.* If the apparatus were manufacturing effects, this is where it would show.

The panel carrying both a placebo and a baseline arm is 61 models, and the placebo moves
position on 6 of them, with a median of 0.013 across the panel. Of those six, 2 move under
both the placebo and the balance instruction, and on 4 the placebo is the only thing that
moves it. The six do not agree on a direction: 5 point one way and 1 the other, which is
what a summary statistic near zero is reporting.

The comparison that makes those numbers mean anything is the estimator's own false-positive
rate, measured the same way the contrast is: split a real cell in half at random and contrast
one half against the other, where no treatment exists and every rejection is a false positive.
Over 200 such splits of 136 cells the sheet bootstrap rejects **10.5%** of true nulls, so on a
panel of 61 about **6.4 models are expected to clear by chance**. Six is at or below that. The
placebo arm is not merely small — **it is indistinguishable from the estimator's own noise**,
which is exactly what a working control arm should be.

> **That 10.5% replaces a 6.2% this paper published until 2026-09-19, and the 6.2% was never
> measured.** It was a docstring at `position_analysis.py:285`. The estimator's `--selftest`
> reports a third figure, 12.5%, on synthetic nulls it generates itself — a detector validated
> against input it chose. The figure above is the first one in this study derived from a
> command, against a null drawn from the corpus, carrying the corpus's own pathologies
> including the cells whose sheets are near-copies. It is worse than the number it replaces,
> and the control arm reads better for it.

> **This paragraph said the opposite for nine hours on 2026-09-18, and the correction is the
> reason to trust the rest.** An earlier estimator paired each model's sixteen items and
> resampled the pair-deltas — after the sheets had already been averaged, so a sheet-level
> disturbance appeared as sixteen closely-agreeing numbers and was read as signal. It rejected
> **49.6% of true nulls**, and under it the placebo appeared to move 16 of 37 models: a lead
> finding, published, and false. The exchangeable unit is the sheet.
> `CORRECTIONS-2026-09-18-bootstrap.md` carries the measurement, what it touched, and what it
> did not. `position_analysis.py --selftest` now fails if the estimator over-rejects data with
> a known answer, which is the check that was never run.

### What follows

§2 measures what this instrument can resolve at all, and finds the same story in the unit the
literature actually reports — side-flips — where frontier models change **1 of 32 sides** under
reordering and **11 of 32 intensities**. §6 shows a nuisance that is not merely as large as the
effect but invisible: susceptible models silently drop items from a sheet whose printed numbers
run out of sequence, and nothing in a refusal table can see it. §5 audits fourteen published
studies against their own deposits for the controls that would have caught any of this. We ran
that audit on ourselves first, and it convicted us twice — §4.

---


---

## 1b. A switch — RE-MEASURE BEFORE PUBLICATION

> **Recomputed on the Ratchet battery, 2026-09-18.** This section previously reported the
> asymmetry on the withdrawn 62-item instrument. It reproduces on the study's own instrument
> and is reported from it; the older corpus is not pooled with it and is not cited here.
> Command: `python scripts/refusal_table.py --switch`. The vendor table below is generated
> over the full corpus and is marked where its denominators differ.

Put the thirty-two propositions to `openai/gpt-6-astra` with a system prompt asking it to
answer in a balanced manner. It declines, **8 times out of 8**, across three presentation
orders. Its larger sibling `gpt-6-astra-pro` declines 8 of 8 as well.

Now replace the instruction with one that has no political content in it at all — read each
item carefully, answer precisely, use one of the four labels. Both answer, **0 refusals in 7**.
So does an explicit demand to commit to a position: 0 in 7. So does asking with no system
prompt at all: 0 in 8.

The instruction that produces the refusals is the one asking for balance, and it is the only
one of the four that mentions politics without demanding a position.

Across the panel, by condition, with transport failures excluded from both halves of every
rate:

| condition | runs | refusals | rate | equal-weighted |
|---|---:|---:|---:|---:|
| **A — answer in a balanced manner** | 650 | 79 | **12.2%** | 7.3% |
| N — no system prompt | 1622 | 70 | 4.3% | 5.6% |
| D — commit to a position | 650 | 27 | 4.2% | 3.2% |
| **P — content-free instruction** | 1163 | 29 | **2.5%** | 2.4% |

The equal-weighted column averages each model's own rate rather than pooling runs, because the
panel is unbalanced across conditions and a pooled rate lets the models with the most sheets
set it. **The ordering A > N > D > P holds under both weightings**, which is the claim; the
gap's size does not survive the choice and is quoted as a range above.

**Eighteen** models decline under some condition. **Nine of them decline the balance instruction
and never the commitment one.**

**Refusal is elicited, not intrinsic.** Across 64 models measured under both arms, there are
88 refusals in 837 runs where the prompt carries no directive, against 1284 runs where it
carries one — 55 of those runs are refusals. 9 models decline it without a directive; give
those same models a firm instruction and 8 of them stop. The ninth is
`google/gemini-3.7-flash`, which declines under every condition and is not a switch at all.
Separately, 3 other models
decline only when told to commit. What suppresses refusal is not the content
of the instruction — a placebo with no stance content works as well as a demand to commit —
but the presence of a firm instruction at all.

**Three models run the pattern backwards, and the previous version of this section had no room
for them.** `llama3.1:8b` declines only when told to commit (7 of 20), its quantised sibling
likewise (2 of 3), and **`phi4:latest` declines only the placebo** — 10 of 19 — refusing an
instruction that contains no political content whatsoever while answering the balance
instruction, the commitment directive and the bare question without complaint.

That last case is not a curiosity. The content-free arm is this study's control, and a control
that provokes refusals in one model and moves measured position in six of sixty-one (§1) is not
controlling for what it was built to control for.

One further model must be named so it is not counted as a switch: `google/gemini-3.7-flash`
declines **every** condition — 18/18, 18/18, 18/18, 18/18. It is a total refuser, and pooling
it with the switches is what makes a vendor-level rate unreadable.

**A pooled rate is the wrong summary for this, and an earlier version of this section reached
for one anyway.** Fifty-one refusals under the balance instruction come from nine models, and
**42 of the 51 come from four of them** — `gemini-3.8-flash` 13, `gemini-3.7-flash` 13,
`gpt-6-astra-pro` 8, `gpt-6-astra` 8. A rate computed over runs is therefore mostly a
statement about four models' denominators.

So it is computed both ways, and the ordering is the claim rather than either figure:

| condition | pooled over runs | each model weighted equally |
|---|---:|---:|
| A — balanced manner | 15.3% | **11.4%** |
| N — no system prompt | 8.4% | 6.0% |
| D — commit to a position | 6.6% | 5.1% |
| P — content-free | 5.2% | 3.6% |

**Both weightings put the balance instruction first and the content-free instruction last**,
and the gap between them is roughly three-fold either way. This is worth stating plainly
because the same comparison on the study's earlier, withdrawn corpus gave the two weightings
**opposite signs** — pooled, a directive cut refusals tenfold; equally weighted, refusals rose.
That corpus had three models contributing one directive run each, so each carried a rate of
1.0. The present ordering is not fragile in that way, and the reason it is not is that every
model here has between 7 and 17 runs per condition. A pooled rate is safe exactly when it is
boring, and the paper should not be read as saying pooling is always wrong — it is saying that
nothing tells you which case you are in except computing both.

**The paired per-model statement is cleaner than either rate**, and it is the form the finding
should be quoted in: *of the thirteen models that decline at all, eight decline the balance
instruction and never the commitment directive; three decline the commitment directive or the
placebo and never the balance instruction; one declines everything.* No weighting choice can
move that, because it counts models rather than runs.

So the mechanism is unchanged and the absolute claim is gone: a firm instruction reliably
silences the models that refuse, and separately there exist small local models that refuse only
when pushed to commit. The original overreach survived because the *zero was hardcoded into
the prose* while the gate that recomputes every other number in this paper checked only the 347
beside it — the one quantity the argument rested on was the one nothing recomputed. Both halves
are gated now (`arms_dir_refusals`, `arms_silenced`, `arms_dir_only`).

Refusal rates are published as properties of models. Vendors get ranked by them. On this
instrument the quantity is substantially a property of the sentence the researcher put in front
of the model: a prompt that says nothing about politics **cuts it by a factor of three to five**
— 12.2% under the balance instruction against 2.5% under the content-free placebo pooled, and
7.3% against 2.4% weighting each model equally.

*Read "a factor of ten" here before 2026-09-19. That figure was from the retired questionnaire
and contradicted this section's own next paragraph, which already said "roughly three-fold
either way".*

The receipt, by vendor and condition. A is the balance instruction, B a bare ask with no
system prompt, D an instruction to commit, P the content-free placebo.

**The population is declared and the table names it.** The panel is the wave; every other
battery collection — smokes, budget probes, and arms run under one or two conditions — sits
outside it under a rule recorded beside each one in `refusal_table.OUT_OF_PANEL`. The reason
the rule exists is worth one example: a targeted re-collection of the three Google models that
refuse most, run to extend the order floor, would let a sample selected *for refusing* set a
vendor's rate. Google anchors the argument in this section, so the number that argument rests
on is measured without it. An arm collected under one condition does the same damage in the
other direction — it grows a denominator on one side of a contrast without adding a single
observation about refusal.

<!-- GEN:refusal -->
```
REFUSAL RATE BY VENDOR AND CONDITION -- recomputed from runs/
refusal = declined all 32 items: prose returned, zero answers, budget intact
panel: 2026-09-16-ratchet-v3-wave
outside the panel, by rule: 14 collection(s) -- smokes, budget probes and arms collected
under one or two conditions; refusal_table.OUT_OF_PANEL names each with its rule

vendor                     N           A           B           C           D           E           P
google              61% (59)    61% (59)    67% (15)    67% (15)    32% (56)    40% (15)    32% (56)
microsoft            0% (15)     0% (15)      0% (5)     43% (7)     0% (15)      0% (5)    53% (19)
meta-llama           0% (27)     0% (28)      0% (5)     40% (5)    28% (32)     40% (5)     0% (26)
openai              0% (120)   25% (126)     0% (40)     0% (40)    0% (120)     0% (40)    0% (120)
anthropic            0% (45)     9% (47)     0% (15)     0% (15)     0% (45)     0% (15)     0% (44)
hf.co                0% (37)     8% (39)     0% (25)     0% (25)     0% (37)     0% (30)     0% (39)
deepseek             6% (63)     0% (57)     0% (17)     0% (18)     0% (59)     0% (20)     0% (59)
moonshotai           0% (48)     2% (46)     0% (15)     0% (14)     0% (45)     0% (15)     0% (47)
x-ai                 0% (45)     2% (46)     0% (15)     0% (15)     0% (45)     0% (15)     0% (45)
z-ai                 0% (55)     2% (51)     0% (15)     0% (15)     0% (51)     0% (15)     0% (51)
aion-labs             0% (5)      0% (5)           -           -      0% (5)           -      0% (5)
cohere                0% (5)      0% (5)           -           -      0% (5)           -      0% (5)
huihui_ai             0% (5)      0% (5)      0% (5)      0% (5)      0% (8)      0% (4)     0% (10)
ibm-granite           0% (5)      0% (5)           -           -      0% (5)           -      0% (5)
meituan               0% (5)      0% (5)           -           -      0% (5)           -      0% (5)
minimax               0% (5)      0% (5)           -           -      0% (5)           -      0% (5)
mistralai            0% (27)     0% (31)      0% (6)     0% (10)     0% (31)     0% (10)     0% (28)
qwen                 0% (45)     0% (47)     0% (12)     0% (10)     0% (53)     0% (15)     0% (51)
stepfun               0% (5)      0% (5)           -           -      0% (5)           -      0% (5)
tencent               0% (5)      0% (5)           -           -      0% (5)           -      0% (5)
upstage               0% (5)      0% (5)           -           -      0% (5)           -      0% (5)
writer                0% (5)      0% (5)           -           -      0% (5)           -      0% (5)
xiaomi                0% (5)      0% (5)           -           -      0% (5)           -      0% (5)

D and P pooled: 55 refusals in 1292 runs
excluded as neither refusal nor answer sheet: budget-exhausted 16, other 109, transport 85

not in this table, by design: 519 clause-factorial sheet(s) across 8 cell(s) -- run with --factorial
```
<!-- /GEN:refusal -->

That is a small result. It is first because it is the shape of the large one.

---

## 2. The same result in the unit the field reports

§1 is measured in **position**, which is this study's own construction. The literature does not
report position; it reports which side a model lands on, item by item. So the result has to
survive translation into the field's unit, or it is a fact about our estimator rather than
about the instrument.

It does, and the translation exposes something §1 cannot see.

We administer 32 forced-choice propositions in 16 mirrored pairs — four options, no neutral
answer, **no language model anywhere in the scoring path** — and then measure how far the
answers move when nothing political changes: a different item order, a different run, the same
weights requantised, one model against a variant of itself. The corpus behind every row below
is named in Reproduction and every figure regenerates from `runs/`.

Two statistics, and the gap between them is the finding:

- **side-flips** — items where a model lands on the other side of the midpoint. This is what
  every instrument in this literature scores.
- **endpoint changes** — items where a model moves between a strong and a moderate answer
  without changing side. Nobody reports this.

<!-- GEN:floors -->
| factor | n pairs | side-flip med / p90 / max | p90 95% CI | endpoint med / p90 / max |
|---|---:|---|---|---|
| prompt condition A->D, one sitting, local open-weight | 17 | 3 / 9 / 13 | [3, 13] | 8 / 14 / 16 |
| requantisation | 16 | 4 / 8 / 15 | [4, 15] | 3 / 10 / 15 |
| presentation order, one sitting, local open-weight | 23 | 3 / 6 / 11 | [3, 11] | 3 / 16 / 18 |
| presentation order | 94 | 1 / 5 / 12 | [3, 7] | 1 / 7 / 13 |
| prompt condition A->D, one sitting | 61 | 1 / 4 / 13 | [3, 9] | 9 / 18 / 27 |
| run-to-run replicate | 6240 | 0 / 3 / 16 | [2, 3] | 2 / 11 / 32 |
| presentation order, one sitting | 107 | 1 / 3 / 11 | [1, 5] | 3 / 12 / 30 |
| prompt condition A->D, one sitting, frontier API | 44 | 0 / 2 / 11 | [1, 4] | 9 / 21 / 27 |
| same-version variants | 24 | 1 / 1 / 2 | [0, 2] | 5 / 11 / 19 |
| presentation order, one sitting, frontier API | 84 | 0 / 1 / 2 | [1, 1] | 3 / 11 / 30 |
| modal sampling error | 576 | 0 / 1 / 16 | not a pair arm | 1 / 6 / 32 |

**requantisation excludes `mistral-7b`:** gated ELIGIBLE but contributed no pair -- every condition lost one arm to an invalid run
<!-- /GEN:floors -->

### Read the two right-hand columns against each other

Take the frontier row — hosted 2025–26 models, one sitting, nothing changed but the order the
items were printed in. **The side-flip column is about 1 of 32. The endpoint column is about
eleven.**

The models do not change which way they answer. They almost completely rewrite how strongly
they say it.

That is the whole literature's measurement in one line. Every published instrument of this
class scores side — agreement counts, axis coordinates, left/right placements are all functions
of which half of the scale a model lands on. **So the field reports the one quantity that is
stable and discards the one that moves.** A paper concluding "this model holds a consistent
position" has measured something true and uninformative: the position is consistent because
side is the stable statistic, not because the model is stable.

It also reframes §1. The balance instruction does not appear to relocate models on a political
axis. It compresses their conviction — which is exactly what an instruction to be balanced
asks for, and exactly what a side-scored instrument is worst at seeing.

**Local builds fail differently, and the contrast matters.** Where frontier models flip about 1
side, 2024-generation 7–14B builds at Q4 flip around ten out of thirty-two on reordering alone.
Their endpoint column is high too. They are not more opinionated; they are less reliable in
every direction at once, and pooling them with frontier models produces a floor that describes
neither.

### Two statistics, kept apart throughout

A **side-flip** is an item that crossed the agree/disagree boundary: the model changed sides.
An **endpoint** change is an item that gained or lost a "Strongly" answer: the model changed
conviction. They answer different questions, mixing them has already produced one published
error in this project, and a study that does not say which it counted has not reported a
result.

**The intervals are clustered, and they have to be.** Order pairs are not independent
observations — a handful of models contribute most of them, so a flat bootstrap counts one
model's ten draws as ten models' worth of evidence. The same-version row is worse. Every
interval in the table resamples the cluster rather than the pair, and the honest error bars are
wider than the flat ones: on the comparisons this section rests on, the order interval overlaps
the manipulation figure it is placed against. That overlap is not a defect in the table. **It
is the arithmetic form of §1's claim**, arriving here independently and in the field's own
unit.

Two rows are the deliberate manipulation, included for scale: an instruction demanding balance
against an instruction demanding commitment. They are the same contrast measured two ways, and
the difference between them is the most instructive thing in the table.

### The reference scale, and two things learned from getting it wrong

> **Rewritten 2026-09-19.** This subsection compared a *pooled* manipulation row (p90 15)
> against a *one-sitting* row (p90 7) and spent three arguments on the gap. **The pooled row
> was the retired temperature-0 arm and no longer computes at all**; the one-sitting row is now
> **p90 4** over 61 pairs. There is one manipulation row and no gap to explain. The two
> methodological findings the argument produced are real, outlived it, and are kept.

There is one manipulation row: `prompt condition A→D, one sitting`, collected under one
protocol in one sitting, five runs per cell, all conditions on the same panel. **That
one-sitting row reports p90 4.**

The panel behind it is 36 panel models, and because each contributes several seeds the row
rests on more pairs than models: 61 pairs answer both arms. The other 2 decline the balance
instruction outright, contributing no pair at all — a refusal is not a position, and a model
that will not answer one arm cannot be differenced across two.

It
sits beside the order floor in §1 and the comparison is made there, on the live corpus, with
both sides measured by the same estimator.

Two things were learned while the comparison was still being argued about, and neither depends
on the numbers that went away.

**One. A pooled p90 can be one model, and modal scoring hides it.** Removing `x-ai/grok-4.5`
from the pooled arm moved it from 15 to **8**, while the per-model median was unchanged at 3 —
one model went from 18 to 2. Its answers under the commitment instruction are
**bimodal** — within its wave cell, four of five runs land within 3–4 items of each other and
the fifth lands 15–18 away. A modal sheet cannot represent that. It reports whichever mode the
sampler favoured, which was one mode on one collection and the other on the next, and this
paper's own floor table already records the same model at 3 on one date and 18 on another.

**Two. "At temperature 0 the runs are near-identical" is false on this corpus**, and it was the
mechanism the draft offered. Measured over the temp-0 A and D cells: 263 within-cell run pairs,
median 1, **p90 5, max 32**, and only 10 of 57 cells are byte-identical. The `run-to-run
replicate` row three lines up says the same thing. There is no regime here in which averaging
five draws merely removes noise and leaves a position.

**And the argument was settled by collecting the missing half, not by winning it.** Two
shuffled item orders across the same fixed panel, same frozen parameters, same swept seeds,
condition D. Condition D and not A because A is 28.2% invalid on that wave against D's 2.9%:
an order floor measured under the balance instruction is computed on whichever models happen
not to refuse it, which is a sample selected by §1's finding. That selection hazard is general
and is the reason every floor in this paper names its condition.

A third argument stood here — that a pooled-versus-one-sitting gap crossed protocols, and that
**23 of 37 shuffled-order cells held exactly one run** so the two sides of the comparison were
not fed the same thing. Both statements were about the retired corpus and neither is checkable
against the battery, where every cell is collected to depth. Removed rather than restated: the
underlying rule — *check what an estimator was fed, not that it was called* — is real, and it
belongs in `LEARNINGS.md`, not in a results section as an argument about numbers that no longer
exist.

Like-for-like, modal against modal on both sides, one protocol:

| row | pairs | median | p90 | max | p90 95% CI |
|---|---:|---:|---:|---:|---|
| presentation order, one sitting | 85 | **1** | **10** | 21 | [3, 12] |
| prompt condition A→D, one sitting | 25 | **3** | **7** | 14 | [4, 12] |

**Those pooled p90s are still the wrong comparison, and this paper had already said why.** §2
argues that the pooled order row is a net aggregate concealing two populations, and calls
splitting it the most important line here. The comparison against the manipulation then pooled
it anyway. Two corrections fix that.

**First: the estimator has its own error, and nothing had measured it.** Every row in this table
pairs two MODAL answer sheets, and a modal is a statistic — draw five more runs from the same
cell and it moves. Bootstrapped (`scripts/floor_resolution.py`, 2000 resamples, two modals of
the *same* cell under the *same* condition): **median 0, p90 1** over 576 cells. It is in the
table as `modal sampling error`, and it is the denominator every other row needed.

**Second: split by model class, and neither factor survives the split on frontier models.**
Read the four class rows of the generated table above:

| | pairs | order med / p90 | pairs | manipulation med / p90 |
|---|---:|---|---:|---|
| frontier API, 2026 | 84 | 0 / **1** | 44 | 0 / **2** |
| local open-weight, 2024 | 23 | 3 / **6** | 17 | 3 / **9** |

Paired within each model over the 36 measured in both arms, the median difference is **0 items**
and the sign balance over the 22 that differ gives **p = 0.83**: order is larger on 12 models,
the manipulation on 10, and they tie on 14. The two are indistinguishable at panel level, which
is §1's claim arriving again in the field's own unit.

**What the paper can defend, stated by class:**

- **On 2026 frontier models neither factor is measurable on this instrument.**
  Its p90 of 1 is exactly the modal's own sampling error, and the manipulation's p90 of 2 is
  barely above it. Both rows report the estimator.
- **On 2024-generation open-weight models both are large**, and the manipulation is the larger
  of the two — p90 9 against order's 6. This is the population most of this literature was
  built on, and Röttger predicted the generational split in 2024.

An earlier version of this subsection reported the opposite on both counts — a frontier
manipulation of median 2.5 / p90 5 called "small but real", and item order dominating the 2024
models at p90 12 against 8. Those were measured on 2026-09-06, on a corpus and an instrument
this paper has since replaced, and the live script gives the figures above.

So the correct sentence is neither of the two this project reached for. It is that **the answer
depends on which generation of model you measure, the effect sizes are small enough that the
estimator matters, and a study that pools the two populations cannot tell you which factor moved
its result.** Ten of the 576 cells in this corpus have a modal so unstable on their own —
`granite-4.2-8b` under both A and P, `llama3.1:8b`, `qwen2.5:14b`, `gemini-3.8-flash` — that no
modal-based measurement of those cells means anything at all.

### The order row is two numbers, not one

Splitting presentation order by model class is the single most important thing in this paper,
and we nearly missed it by reporting the pooled figure:

| presentation order | pairs | side-flip med / p90 / max |
|---|---:|---|
| 7–14B open-weight models, 2024 generation | 19 | 5 / 11 / 12 |
| frontier API models, 2026 | 75 | **1 / 3 / 6** |

**Reordering the questionnaire is a large effect on the models this literature was mostly
built on, and a small one on the models being shipped now.** Röttger et al. predicted this in
2024 — "It is plausible that future models, as a product of more comprehensive alignment, will
also exhibit fewer instabilities" — and this is that conjecture measured.

Their own paraphrase instability, 14 and 23 items of 62, is often quoted next to a number like
ours. **It should not be**, and an earlier version of this paragraph did it twice over. Those
two figures are Mistral 7b Iv0.1 and GPT-3.5 1106 *only* — Llama-2 was excluded from their
paraphrase experiment for too few valid responses, so naming it here was wrong. And their
statistic is a **union**: a proposition counts if it is contradicted anywhere across ten
paraphrases. Ours is a pairwise 90th percentile. A union over ten comparisons is larger than
any one of them by construction, so setting 14 beside our 14 compares two different
quantities that happen to agree. The like-for-like figure is their data re-scored with our
statistic — p90 9 — and that is the number to use.

A single pooled order floor would have been a net aggregate concealing gross movement between
two populations. That is a defect this project has already caught in itself once, and here it
would have been in the title.

### What does not shrink

On those same frontier models, in side-flip units:

| factor, frontier models only | p90 |
|---|---:|
| presentation order | 3 |
| two models of the same version — size, tier, snapshot or mode | 1 |
| deliberate manipulation, forced balance against forced commitment | 4 |

**This table's conclusion is reversed from the version published before 2026-09-19, and the
reversal is the honest result.** It read: presentation order 6, same-version **12**,
manipulation 15, concluding that *"the nuisance factor that matters is which variant of the
model was measured — and that one is the same size as the manipulation."* Those figures are
from the retired 62-item questionnaire. On the battery the same-version variant is the
**smallest** row here, not the largest, and it sits below its own detection limit of 3 side
flips (§3, `null_audit.py`) — so it is bounded rather than measured.

The null rests on 24 pairs of models that differ in size, tier, snapshot date or mode, and not in
version — the comparison a reader makes without noticing, every time two checkpoints of the
same model are treated as one. Half of those pairs differ by 1 or more items with no version change.
Against that, the detection limit for a directional claim is 7 items of 32, against presentation order pooled
across classes.

What the table still supports is narrower and survives: **on frontier models every one of
these factors is small, and they are all the same size as each other.** Three, one and four
side flips of thirty-two, against a detection limit of three. Nothing here separates a
deliberate manipulation from a shuffled sheet from a sibling checkpoint, which is a different
and less quotable claim than the one it replaces.

The control is still the one no study in our audit reports. That part never depended on its
magnitude.

---

## 3. What an instrument can see

A floor says what a nuisance factor produces. It does not say what the instrument can resolve.
For that the null has to become a detection limit: the smallest real effect that would clear
the noise often enough to be caught.

<!-- GEN:power -->
```
DETECTION LIMITS -- what this instrument can resolve, per null, of 32 items
threshold = reference p95, an order statistic; NOT an alpha=0.05 rejection region
MDE       = smallest shift with 80% of mass above p95; a design sensitivity,
            NOT achieved power, and NOT a cutoff for reading an observation

null                         statistic  pairs   threshold    MDE  note
presentation order           side          94           7      7
presentation order           endpoint      94          12     13
same-version variants        side          24           2      3
same-version variants        endpoint      24          13     11
run-to-run replicate         side        6240           4      5
run-to-run replicate         endpoint    6240          15     16
requantisation               side          16          15     15  p95 IS THE SAMPLE MAX (n=16)
requantisation               endpoint      16          15     16  p95 IS THE SAMPLE MAX (n=16)
presentation order, one sitting side         107           3      4
presentation order, one sitting endpoint     107          18     18
presentation order, one sitting, local open-weight side          23          11     10
presentation order, one sitting, local open-weight endpoint      23          16     16
presentation order, one sitting, frontier API side          84           1      2
presentation order, one sitting, frontier API endpoint      84          20     20
```
<!-- /GEN:power -->

**7 items of 32**, against presentation order pooled across classes. That is the threshold a
directional claim has to beat before the word "effect" is doing any work.

The previous version of this sentence named a different number as the governing one — *"the
same-version limit of 11, because on frontier models that is the floor a version-over-version
claim competes with."* **Withdrawn.** On the battery it is the same-version limit of 3 that
applies — the smallest detection limit in the table rather than the largest, and the observed
same-version distribution sits underneath it (§7). The governing limit for a study of this shape is the
pooled order limit, because that is the largest one a claim must clear — not the smallest.

Note what that withdrawal does *not* do. It does not make version-over-version comparison safe:
a limit of 3 means the instrument cannot see a same-version difference smaller than three side
flips, so a drift claim below that size is unresolvable here rather than absent. An
undetectable nuisance and an absent one are not the same finding, and this paper has argued
that about other people's work.

Two studies in our audit get close. Domínguez-Olmedo et al. (2024) state a test power of
at least 0.98 at effect size 0.1 — for the appendix chi-square tests separating positioning
from labelling bias, not for the comparisons the paper is read for. And Messing (2026) does the
central move in general form: naive standard errors in LLM evaluation are 40–60% smaller than
those corrected for variance from judge choice, temperature and prompt phrasing, and naive 95%
coverage *degrades* as sample size grows.

So the general observation is not ours and should not be dressed as ours. **9 studies report a
nuisance magnitude of some kind outright, and 3 more report something adjacent to one.** What
none of them does is convert
one into a threshold that a substantive effect must clear on the instrument in question. That
is the step that turns a caveat into a decision rule, and it is why a caveat can be published,
cited approvingly, and ignored by the next paper using the same questionnaire.

---

## 3b. There is less disagreement to measure than anyone assumes

Everything above is about the instrument. This section is about the panel, and it is the reason
the instrument problem matters less than it should: **on the questions this bank asks, the
models do not differ.**

Across the nine pairs whose critic-framed half is a contested normative proposition — arm's-length
censorship, emergency powers, biometric enrolment, punishment for unauthorised disclosure — the
panel agrees 97.1% of the time, against 99.0% for documented matters of record. A gap under two
points. Models answer arguable political questions at very nearly the confidence they bring to
facts.

That is an average, and the floor matters more: taken pair by pair, the lowest is 92.3% — pair
1, arm's-length censorship, the most contested subject in the bank. There is no pair on which
the panel is meaningfully divided.

**Forty of sixty-one models agree with every normative proposition in the bank.** The median
model's disagreement rate is zero.

### The first objection, and it does not hold

The obvious reply is that this measures shared training rather than shared belief: one alignment
consensus, propagated across a panel whose vendor count overstates its independence. That is
testable here, because the panel contains models trained outside the consensus in three
different ways — and one of them, abliteration, removes the consensus from the weights directly.

<!-- GEN:training -->
```
| how the model was trained | models | contested normative | matters of record | gap |
|---|---:|---:|---:|---:|
| abliterated / uncensored | 5 | **100.0%** | 100.0% | +0.0 |
| hosted, Chinese-jurisdiction | 20 | **99.7%** | 99.8% | -0.1 |
| hosted, US/EU-jurisdiction | 24 | **95.4%** | 99.2% | -3.8 |
| local open-weight, 2024 | 12 | **94.9%** | 96.4% | -1.4 |

41 of 61 models agree with **every** normative proposition in the bank.
```
<!-- /GEN:training -->

**The agreement does not weaken outside the consensus. It is strongest there.** Builds with the
refusal direction projected out of their weights agree with *every* normative proposition.
Chinese-jurisdiction vendors, trained under a different regulatory regime, sit at 99.6%. The
class that agrees least is US/EU frontier at 95.4% — and it is the only class with a real gap
between contested politics and matters of record, which is to say the most heavily aligned
models are the most likely to hedge, not the least.

So safety tuning is not what installed these positions. The one intervention in this corpus that
removes safety tuning leaves them exactly where they were.

### Intensity runs the wrong way

Agreement is a low bar — any position above the midpoint counts, so a model that leans and a
model that is certain score the same. The sharper test is which claims get the **top box**.
A working internal standard for what one knows predicts an obvious pattern: agree with the
arguable proposition, reserve "strongly agree" for the one with court filings and statutory
text behind it.

<!-- GEN:intensity -->
```
| claim type | answers | agree | strongest answer |
|---|---:|---:|---:|
| documented — matters of record | 3594 | 99.0% | **36.6%** |
| contested normative propositions | 5391 | 97.1% | **42.5%** |

Per model rather than pooled: of **56** models carrying at least 20 answers in each class, the strongest answer is used more often on documented claims by **14** and on contested normative claims by **36** (6 tied). Median gap **-3.3** points, sign test **p = 0.0026**.

**This split is near-collinear with jurisdiction, by construction.** 9 of the 10 critic-framed generic items are normative (the rest carry a third claim type) and 6 of the 6 jurisdiction-tagged items are documented, so "has a public record behind it" and "names a specific country" are very nearly one variable with two labels. Nothing crosses the diagonal, so no quantity of data separates the readings — this is not a confound collection shrinks but one the instrument forecloses, and it is fixed by authoring items that break the alignment, not by collecting more.
```
<!-- /GEN:intensity -->

The sign is backwards. The panel commits hardest where it has least to go on, and it holds
per model rather than only in aggregate — which matters here, because §2 of this paper convicts
the project of reading a pooled aggregate as a within-unit result.

Two mechanisms produce that pattern and the bank cannot choose between them. Either confidence
tracks how **agreeable** a proposition is — the reading Törnberg and Schimmel support from a
different direction, finding audit scores that move 8.0× harder toward a conservative cue than
a progressive one — or it tracks **unfalsifiability**, the model declining the endpoint where a
specific record could catch it out. The second is not the softer finding. It says the panel is
most certain precisely where nothing can check it.

Note what this does *not* require: any claim about whether the propositions are true. The
comparison is within-model and within-instrument. A model that held every one of these
positions for excellent reasons would still be expected to know which of them it can support.

### What that does not establish

**Shared pretraining survives this test untouched.** Abliteration removes a refusal direction,
not a prior. If the field trains on overlapping web text then every model inherits the same
priors, and an intervention aimed at the refusal mechanism cannot see it. Separating belief from
corpus needs a contrast this study does not have.

**Nor does it establish that the questions are hard.** §3 already showed the bank is bimodal:
defender-framed items run 0.5–29.8%, critic-framed items 92.3–100%, and **not one of the
thirty-two falls between 30% and 70%**, where a panel would actually divide. An instrument with
no contested middle cannot tell a model that holds a position from a proposition that is not
really arguable. The three items nearest that middle — surveillance export, state funding of
flagging research, international policy forums — sit at 24–30%, which is where the next version
of this bank should be authored.

**This section is exploratory and uncorrected.** It was computed after the data was seen, in
answer to the objection above, and it is counted that way in §9.1. Independent support exists —
Barmettler (2026) reports near-uniformity across 66 models on a different instrument in a
different country — but that is a replication of the agreement, not of this explanation.

---

## 4. We ran this on ourselves first, and it convicted us twice

This paper would be worth nothing from authors who had not.

The project that produced these floors began with a thesis: a fairness instruction masks a
political position, and force applied to the model — stripping the instruction, escalating the
prompt, cutting the refusal direction out of the weights — reveals what is underneath. Ten
claims from that programme were withdrawn or narrowed in three days, once each was measured
against a floor. The founding one went with them. What an instruction controls is how strongly
a model commits, not where it lands, and even that narrower claim rests on the intensity
statistic rather than the positional one.

Then the second conviction, which is the one worth reading.

Every control we ran was aimed at a claim asserting an effect. None was aimed at a claim
asserting the absence of one. A procedure built that way can only subtract. When the detection
limit above was finally computed — after the withdrawals were published, on a live page — it
said three of our five null results sat below their own resolution. The instrument could not
have seen the effects those nulls were used to rule out. Both nulls that retired this
project's central claims are among them.

Those claims are not restored. They are undecided, which is a third verdict and the correct
one, and the distance between *refuted* and *undecided* is what this paper is about.

**And this passage claimed a fourth defect it did not have.** It read "four of our five" —
the generated figure is three — and it ended on a null that "inverted outright": an ablated
model filed as showing no stance movement moving 12 items against a detection limit of 9.
Both numbers are withdrawn. The 12 came from **a single run per arm**, and a one-run sheet is
not a modal: this study's own run-to-run replicate floor is p90 5, so a 12 derived from n=1
sits inside its own noise before any ablation acts. The detection limit of 9 appears nowhere in
the generated numbers at all.

That is the same defect as everything else convicted in this section, committed one layer
further in — a claim of an *inversion*, which is the strongest verdict available, resting on
the thinnest sample in the corpus, in the paragraph arguing that null results need their
resolution computed before they are trusted. The 2026-09-07 ablation wave re-collected that pair
at n=5 with a swept seed, and it settled it.

> **Resolved, and this paragraph said "until then" for five days after the answer existed.**
> At n=5 the same pair moves **8 / 9 / 9** items under A / D / P, not 12. The magnitude was
> overstated and is not reproducible. **The direction cannot be scored here either**, and an
> earlier version of this paragraph scored it anyway: those counts are out of the retired
> 62-item questionnaire and the side-flip floor of 3 they were placed against is out of the
> 32-item battery. That is the comparison `CORRECTIONS-2026-09-17-power.md` was written about,
> repeated inside the section that reports it. No battery-era ablation arm exists, so there is
> no floor this can clear; the claim is withdrawn rather than reversed. The framing "one null
> inverted outright" stays withdrawn regardless: one base, with one abliteration whose
> contribution cannot be separated from the ablator's choices, is a measured effect on one
> model and not an inversion of a general null. Full detail in
> [RESULTS-2026-09-07-ablation-wave.md](withdrawn/results/RESULTS-2026-09-07-ablation-wave.md); the arm is spent
> rather than complete, at 39 of 63 cells reaching n=5.

Two smaller defects, same species. A refusal table assembled by hand from a corpus snapshot
that a later collection invalidated, published at 43%, regenerating at 27%. A positional range
published without its scope, true on four local models and wrong by a factor of two on the
frontier.

Every defect found in this work **up to 2026-09-11** was a number typed into a document. Not one
was in the code.

> **That stopped being true on 2026-09-12, and the sentence is left standing because the
> correction is more useful than the aphorism.** That day's review found defects in the code
> itself: an arc statistic that subtracted one run from another and called it version drift; a
> minimum-detectable-effect that ignored the instrument's 62-item bound and returned a
> sensitivity the barometer cannot have; a collector that kept only the last row each floor
> function emitted, silently dropping a 10-pair floor behind a 75-pair one; and four gates that
> printed failure and exited zero.
>
> The document defects were all found by reading. **Not one of the code defects was**, and they
> had survived longer. They were found by running the thing and comparing its output to what it
> claimed — which is the method this paper recommends for models, applied to ourselves.
That is why every table here is generated, and why the paper refuses to build when they go
stale.

### And a third: we validated our judges five ways, none of them for lean

The scored arm of this project uses a four-model judge panel, and validates it five ways —
a solo low-RLHF judge, an adversarial pair, an inverted rubric, blind conditions, and a judge
with the refusal direction cut out of its weights. They agree with the panel on the exact score
84–91% of the time.

Read what each one tests and none of them is a test for political lean. The last is the case
that matters: the abliterated judge is the executed anchor, scored 5 of 5 on circularity-
reduction in the pre-registered rubric as "the direct answer to *judges share RLHF lean*". But
this project's own weight-rung result, across five open-weight families, is that abliteration
moves stance by **≤0.2** — refusal direction and institutional lean are *dissociable*.

> The companion claim, that abliteration also **rewrites most of the political wording**, is
> **withdrawn** and this argument does not use it. Narrowed 2026-09-13 to one family of five,
> and settled 2026-09-20 when the Gemma-2-9B arm was re-collected with the same-weights control
> the original never had: stock against abliterated gives Jaccard 0.339, while the same weights
> resampled against themselves give 0.380 and 0.377. The between-arm figure sits **inside** the
> 0.303–0.392 band a single model produces against itself, so what it measures is temperature
> 0.7 with no seed. Only `qwen2.5-7b` at 0.276 falls outside the band. The **stance** half is
> unaffected, was re-measured at temperature 0 where a greedy model reproduces itself exactly,
> and is the half carrying the sentence above.

If cutting that direction does not move a subject's
stance, it does not move a judge's. **The anchor removes a reflex we ourselves proved is not
the lean.**

Measured properly (`scripts/judge_lean.py`, 4,668 scored records, per-judge scores were retained
all along): the panel's internal spread is **0.29 points**, gemini-2.5-flash most
institution-skeptical at +0.175, deepseek-v3.2 most deferential at −0.117. That is a nuisance
factor larger than one of the five effects this project published, and it was in no floors
table.

The principle that would rescue it is real: **an instrument does not have to be unbiased, it has
to be biased CONSTANTLY across the comparison being made.** A ruler 2% short measures differences
correctly, and every finding here is a within-model, within-judge delta.

**It does not hold here, and the first version of this paragraph claimed it did.** That version
argued the judges' rank order is identical under both conditions, therefore the lean is a main
effect, therefore it cancels. Rank stability is necessary and not sufficient — cancellation needs
the lean to be the same SIZE in both arms:

| judge | lean in A | lean in B | B − A |
|---|---:|---:|---:|
| gemini-2.5-flash | +0.044 | +0.290 | **+0.246** |
| gpt-4.1 | +0.019 | +0.148 | **+0.129** |
| claude-haiku-4.5 | −0.004 | −0.038 | −0.034 |
| deepseek-v3.2 | −0.068 | −0.171 | **−0.104** |

The panel fans out between the arms and the fanning rides into the delta. (Condition A scores
92% threes, which explains *why* the lean is compressed there. It does not make it cancel; a
lean suppressed by a floor in one arm and expressed in the other is an interaction.)

So the question is settled by re-scoring rather than by argument — each finding under each judge
alone. **The two large effects are robust to any judge composition**: every single judge returns
a substantial positive delta for claude-opus-4.7 (+0.80 to +1.50) and grok-4.3 (+0.80 to +1.30).
**Two are not**: deepseek-v3.2's delta ranges +0.03 to +0.60 depending on which judge reads it,
the low end being deepseek-v3.2 scoring itself; and openai/gpt-4.1's ranges +0.21 to +0.73, a
factor of 3.5. `judge_lean.py --per-finding` computes the table and marks both. They are
reported as suggestive with their ranges, not as findings of the same standing as the two
large ones.

**Absolute scores were never safe** and are not now: "this model scores a flat 3.00" is a
statement about a model and the panel that read it.

Two further disclosures. **Two of the five published effects are self-judged** — `gpt-4.1`
(+0.433) and `deepseek-v3.2` (+0.233) sat on the panel that scored them. And **a lean shared by
all four judges is invisible to every check above**, because each is measured against the median
of the same panel; a panel that agreed and was wrong together scores a spread of zero and looks
ideal. The only method that could catch it anchors outside the panel — ranked **first** in our
own pre-registered rubric, and the one we never ran.

---

## 5. The warning was published in 2024

14 studies, 14 controls. The question is not whether a control is standard. It is
whether the study's own design already contained what the control needs, which it usually did.

Before the table, the part that goes against our interest. Röttger et al. did this work first
and said so plainly:

> "we urge that any evaluation for LLM values and opinions be accompanied by extensive
> robustness tests. Every single thing we changed about how we evaluated models in this paper
> had a clear impact on evaluation outcomes… When instabilities are this likely, estimating
> their extent is key for contextualising evaluation results."
> — Röttger et al., ACL 2024, §5.1

They measured paraphrase instability at 14 of 62 propositions for Mistral 7b and 23 of 62 for
GPT-3.5, retained and hand-annotated their invalid responses rather than discarding them, and
concluded that the instrument "may resemble spinning arrows more than reliable instruments."

They were not first either. Sclar et al. (ICLR 2024, on arXiv in October 2023) had already
shown that prompt *formatting* alone — separators, casing, spacing, all meaning-preserving —
moves few-shot accuracy by up to 76 points on LLaMA-2-13B, and that the sensitivity survives
larger models, more shots and instruction tuning. Their recommendation was to report a range
across plausible formats rather than a point. Different task, same instruction.

On the same class of model our order floor is p90 11, max 12 — a different factor and a
different laboratory, pointing the same way. And their forecast that newer models would be
steadier is confirmed: the same measurement on 2026 frontier models gives p90 3.

> **The two numbers are not commensurable, and the denominator is the shallow reason.** Their
> 14 and 23 are counts on their own 62-proposition instrument; ours are out of 32. More
> importantly, Röttger
> counts propositions on which ANY of ten paraphrases disagree — a union over ten draws — and
> we count items differing between TWO administrations, a pairwise difference. A k-way union
> is mechanically larger on identical instability, so no rescaling converts one into the other.
>
> **How much larger is now measured rather than asserted.** The paraphrase arm runs their
> statistic and ours on the same 448 sheets, 44 models, ten templates, one order: the union
> gives a median of 2.0 and the pairwise rate 1.0, so **the union runs 2.0× the pairwise rate**
> at k=10. The maxima diverge far harder, 17 against 3. `cohere/command-a` is the instructive
> row — union 17 of 32 against a pairwise median of zero, every template pair agreeing while
> seventeen items move somewhere across all ten. Both numbers are correct and they support
> opposite readings of the same model, which is why the statistic has to be quoted with the
> number. `RESULTS-2026-09-21-paraphrase.md`.
>
> The other direction is `replicate_rottger.py`, which runs our floor statistic on their
> published completions. What this section claims is corroboration in direction, not in size.

The uptake is the finding. Two years later, two 2026 studies on the same instrument bound
their error with repeated sampling at temperature zero and report neither a nuisance magnitude
nor a detection limit.

The field was told three times. Sclar in October 2023, for benchmark tasks. Röttger in
February 2024, on this exact instrument, with the magnitudes. Messing in April 2026, for
evaluation pipelines generally, with the correction factor. Naser was published in June 2026
and Carnegie issued its reliability standard in August 2026, both after all three, and both
bound uncertainty with repeated sampling at a temperature where repetition returns the same
answer.

That is not a claim about anyone's diligence. It is the observation that a caveat without a
threshold does not survive contact with the next paper, and it is the whole reason this one
contributes a decision rule rather than a warning.

<!-- GEN:controls -->
| study | year | order | magnitude | sv-point | sv-dist | quant | failures | MDE | forcing | raw | no-judge | judge-lean | self-judged | over-time | item-NR | provenance |
|---|---:|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| naser2026 | 2026 | -- | part | yes | NO | NO | NO | NO | yes | yes | part | NO | NO | NO | ? | full-text |
| sakhawat2026 | 2026 | NO | NO | part | NO | NO | NO | part | yes | NO | yes | -- | -- | NO | NO | full-text |
| rottger2024 | 2024 | NO | yes | NO | NO | NO | yes | NO | yes | yes | part | NO | part | NO | part | full-text |
| motoki2024 | 2024 | part | yes | -- | -- | -- | NO | NO | part | yes | yes | -- | -- | NO | ? | full-text |
| liu2025 | 2025 | part | yes | NO | NO | -- | NO | NO | part | yes | yes | -- | -- | NO | ? | full-text |
| rozado2024 | 2024 | -- | part | NO | NO | NO | part | NO | yes | yes | NO | NO | part | NO | part | full-text |
| dominguezolmedo2024 | 2024 | -- | yes | NO | NO | NO | -- | yes | yes | yes | yes | -- | -- | NO | NO | full-text |
| kamal2025 | 2025 | NO | part | part | NO | part | NO | NO | part | NO | yes | -- | -- | NO | NO | full-text |
| cen | 2025 | -- | yes | part | NO | part | part | NO | yes | yes | NO | NO | part | yes | part | full-text |
| aipolcom | 2026 | yes | yes | NO | NO | NO | part | NO | yes | yes | yes | -- | -- | part | -- | full-text |
| sclar2024 | 2024 | -- | yes | -- | -- | ? | ? | ? | yes | yes | yes | -- | -- | NO | part | partial |
| messing2026 | 2026 | part | yes | NO | NO | NO | NO | yes | yes | ? | NO | part | yes | NO | NO | full-text |
| barmettler2026 | 2026 | NO | NO | NO | NO | NO | yes | part | yes | yes | yes | -- | -- | NO | part | full-text |
| tornberg2026 | 2026 | NO | yes | yes | part | NO | NO | NO | yes | yes | yes | -- | -- | NO | NO | full-text |
| **this study** | 2026 | yes | yes | yes | yes | yes | yes | yes | yes | yes | yes | yes | yes | part | part | full-text |
<!-- /GEN:controls -->

<!-- GEN:gaps -->
```
PER-CONTROL TALLY, excluding this study (n=14)

  item_order             yes 1, partial 3, no 5, n/a 5
      Item-order variation WITH a reported change rate. Not randomisation used as a prevention device and pooled away -- the magnitude has to be reported.
  nuisance_magnitude     yes 9, partial 3, no 2
      ANY non-political factor's effect reported as an item-level magnitude -- paraphrase, format, ordering, serving stack. Broader than item_order and the question that actually matters: did the study tell the reader how much its instrument moves on its own?
  same_version_point     yes 2, partial 3, no 7, n/a 2
      Any same-version or non-transition pair used as a negative control, even one.
  same_version_dist      partial 1, no 11, n/a 2
      A same-version null as a DISTRIBUTION: median and upper percentile over many pairs, so a single observed transition can be scored against it.
  quantisation           partial 2, no 9, n/a 2, unknown 1
      Serving-stack variation (quantisation, precision) held or measured.
  retained_failures      yes 2, partial 3, no 7, n/a 1, unknown 1
      Unparseable or declined runs retained and classified by cause rather than discarded as collection error.
  reported_mde           yes 2, partial 2, no 9, unknown 1
      A minimum detectable effect, power analysis, or explicit resolution limit reported alongside the effects.
  forcing_disclosed      yes 11, partial 3
      The forcing mechanism that turns free text into a scoreable answer is stated and its influence acknowledged.
  open_raw               yes 11, no 2, unknown 1
      Raw per-item responses published, not just aggregates.
  judge_free_scoring     yes 9, partial 2, no 3
      No language model anywhere in the scoring path -- answers are recorded mechanically (forced choice, item id + position) rather than read and rated by a model. A judged score inherits the judge's lean; a mechanical one cannot.
  judge_lean_reported    partial 1, no 4, n/a 9
      If a model DOES score the responses, the study reports that scoring layer's own lean as a magnitude -- per-judge deviation, or an equivalent -- rather than asserting agreement and stopping.
  self_judging_disclosed yes 1, partial 3, no 1, n/a 9
      No subject of the study also sits on the panel that scores it, or if one does, the study says so. n/a where scoring is judge-free.
  longitudinal           yes 1, partial 1, no 12
      The same subject re-measured over CALENDAR TIME under held parameters. A cross-section of successive versions measured on one date is not this, however many versions it spans.
  item_completeness      partial 5, no 5, n/a 1, unknown 3
      Per-item non-response reported, and tested for item-dependence. An aggregate parse-failure rate does not answer it: exclusions that concentrate on the most contested items are differential on the axis being measured, which relocates a confound rather than removing it.

STUDIES WHOSE OWN DESIGN CONTAINS THE PAIRS FOR A SAME-VERSION NULL
but which do not report one as a distribution: 9 of 14
  naser2026 -- Same-version pairs exist inside their own tier ladder (mini vs flagship at one generation, dated snapshots of one name) and are read as drift transitions carrying d values rather than as a baseline.
  sakhawat2026 -- Re-read 2026-09-11 (arXiv HTML full text). No same-version distribution is reported. The cohort does contain size siblings presented side by side -- gpt-4.1-nano, gpt-4.1-mini and gpt-4.1 in Table 7, and the gpt-5 family likewise -- but they are entries in a ranking, never a null.
  rottger2024 -- GPT-3.5 0613 vs 1106 and GPT-4 0613 vs 1106 are snapshot pairs of one version, and Llama2 7b/13b/70b are size variants. All four are in the model list as separate subjects rather than as a baseline.
  liu2025 -- The same-version snapshot pair IS the treatment, not a control. Nothing in the paper establishes what a zero-difference comparison looks like on this instrument. Their only null varies the API account, which bounds nothing about model identity. Two same-date cross-tier pairs are also in hand -- 3.5-turbo-0613 against gpt-4-0613, and the two 1106 models -- and neither is estimated.
  rozado2024 -- The pairs are excluded ON PURPOSE, and he says so -- the strongest single quote in the audit. Same-version siblings are left out of the sample in favour of variety across model families, which is a stated sampling rationale and not a hidden one; the consequence is that the comparison capable of bounding model-to-model difference is the one the analysis leaves out. Note what this does NOT say: his published data does contain same-version pairs -- Grok in fun mode against Grok in regular mode among them -- so the pairs are not absent from the corpus, only from the reasoning. The comparison point offered instead is what the paper calls a reference fake model data point, a synthetic random-answer respondent. His negative control is instead a synthetic random-answer respondent, which bounds nothing about model-to-model comparison. (Reworded 2026-09-06: an earlier version said the pairs were designed out 'to make the sample look more varied', which imputes a motive to a rationale he gives openly. The methodological point does not need it.)
  kamal2025 -- The pair exists and is clean -- Llama3.2-1B-Instruct at full precision against the same model 4-bit, same version, same size, precision only -- and it is used as a generalisability check rather than a null. They never compute the difference or ask whether it is zero.
  cen -- Three online/offline pairs of one model each -- gpt-4o, claude-3.5-sonnet, gemini-1.0-pro with and without Google Search. The difference is the finding rather than a null, and the pair is not clean: online runs at temperature 0.1 against 0 offline.
  barmettler2026 -- Read 2026-09-20. No same-version pair is used as a control. The cohort of 66 necessarily contains size and generation siblings, but they are rows in a ranking, never a null.
  tornberg2026 -- Read 2026-09-20. It goes further than any other study here short of ours and stops just short of a distribution: "mean within-cell standard deviation in WD(Dem) is 0.021; the median is 0.000." That is a centre and a spread over many cells, which is most of a null -- but no upper percentile is given, so a single observed shift still cannot be scored against it. `partial`.

NOT ESTABLISHED either way (3) -- absent from the count above, and said
so rather than dropped:
  dominguezolmedo2024 -- NOT ESTABLISHED. Scored `no` on reporting a same-version null, which says nothing about whether the pairs are in their design, and nobody has checked. Recorded as unknown rather than dropped silently: this study was absent from the remedy list for no reason but a missing note.
  aipolcom -- NOT ESTABLISHED, and this one is ours to answer rather than anyone else's -- it is this project's own observatory. Same clerical exclusion as dominguezolmedo2024.
  sclar2024 -- Its subjects do include size siblings (Llama-2-7b against Llama-2-13b), so the structure is present -- but the study measures few-shot accuracy, not political position, and counting it among studies that could fix the political same-version gap would pad the numerator the same way scoring it `no` padded the denominator.
```
<!-- /GEN:gaps -->

One column has no "yes" in it across every study but this one: **not one reports a same-version
null as a distribution.** One comes close enough to name. Törnberg and Schimmel (2026) collect
the pairs and report their centre and spread — mean within-cell standard deviation 0.021,
median 0.000 — and stop before an upper percentile, which is the one number that would let a
reader score an observed shift against it. That is scored `partial`, and it is the nearest any
study in this table gets.

The tally is narrower than a previous draft said, and the narrowing was ours. That draft read
"twelve of twelve — eleven 'no' and one not applicable", which counted three studies we had
read as a **method-and-results retrieval rather than end to end**. A retrieval can show a
control is absent from what we saw; it cannot establish it is absent from the work. Those three
were re-read, and the column stands at **11 "no", 1 partial, 2 not applicable** over fourteen
studies — the column is empty of "yes" because it was read that way, not because eleven were
assumed.

Sakhawat carried five of those downgrades and had the most to complain about. Two of the
fourteen are also not political-instrument studies at all — Sclar is a prompt-format paper and
Messing is methodological precedent — which their own notes here say, and which makes any
"n of n" a count over a set assembled to be as large as possible. Among the 12
political-instrument studies, **10 are scored `no` on it**, one is partial and one does not
apply, and that is the number worth quoting.

Two earlier drafts of this paper claimed more than that, and each was corrected by reading a
paper rather than a note about it. The `magnitude` column is not empty — Röttger, Domínguez-
Olmedo and the aipolcom observatory all report one. The `MDE` column is not empty either.
Every correction has run in the same direction, which is a fact about how this audit was
first assembled and not a coincidence.

A cell reading "does not run this control" is a claim about someone else's work.
`controls_audit.py --strict` refuses to render any such verdict sourced from our own notes
rather than from the paper itself. It failed on 22 verdicts across 7 studies when this section
was drafted, and it passes now. **13 of them read in full — main text, appendices, and
deposited data and code where it exists.** The fourteenth is Sclar, marked `partial` in the
provenance column above: consulted for the prompt-format result it is cited for, not read end
to end, and its political-instrument columns are scored `n/a` rather than guessed.

That sentence has been wrong twice in the other direction, both times by asserting a reading
that had not happened. It is a generated count now, not a typed one.

Reading them cost us four claims. "Nothing computes a floor" was false: Röttger reported one
in 2024. "No study reports a detection limit" was false: Domínguez-Olmedo report power ≥ 0.98
at effect size 0.1. Our complement to Kamal on quantisation was backwards — their own appendix
does not support the invariance we were complementing. And a vendor refusal ordering we
claimed to invert turned out to be a sentence from an introduction that the same paper's
results section contradicts, so it is withdrawn rather than argued with.

Every one of those corrections came from opening a paper instead of a note about it. That is
the same defect this study found in itself four times in three days, and it is the reason the
gate exists.

---

### The sequence, which is the argument

A year column shows that one paper is 2024 and another is 2026. A date column shows that the
warning was readable on arXiv in February 2024, with item-level magnitudes on this exact
instrument and an explicit plea to estimate the extent of instabilities -- and that every
study in this audit first published after that date still does not run the control.

<!-- GEN:timeline -->
| first public | study | mag | null | MDE | what it is |
|---|---|:-:|:-:|:-:|---|
| 2023-06-13 | **dominguezolmedo2024** | Y | - | Y | Survey responses are dominated by answer ordering and labelling artifacts; adjust for them and m |
| 2023-08-17 | **motoki2024** | Y | . | - | Default answers correlate 0.96 with the model's own average-Democrat impersonation and -0.12 wit |
| 2023-10-17 | **sclar2024** | Y | . | ? | Prompt formatting alone -- separators, casing, spacing -- moves few-shot accuracy by up to 76 po |
| 2024-02-26 | **rottger2024** | Y | - | - | Models give different answers when not forced, different answers depending on HOW they are force |
| 2024-07-31 | **rozado2024** | ~ | - | - | Conversational LLMs are diagnosed left-of-centre across models and across instruments, while bas |
| 2025-02-10 | **liu2025** | Y | - | - | Both model families shift right between the 0613 and 1106 snapshots on both axes, with coefficie |
| 2025-06-27 | **kamal2025** | ~ | - | - | Decoding parameters barely move PCT scores; prompt phrasing and fine-tuning move them a lot -- a |
| 2025-09-22 | **cen** | Y | - | - | Election-related responses drift over time even offline at temperature 0, are steerable by demog |
| 2026-01-08 | **sakhawat2026** | - | - | ~ | Model identity explains >90% of score variance (eta-squared > 0.90, p<1e-90); normalized drift b |
| 2026-04-13 | **messing2026** | Y | - | Y | LLM evaluations systematically underestimate uncertainty because variance from judge choice, tem |
| 2026-05-26 | — |  |  |  | This project publishes its May 2026 judge-scored study on evilrobots.lol -- no nuisance magnitud |
| 2026-06-11 | **naser2026** | ~ | - | - | Mean stance drift Cohen's d = 0.35 (OpenAI) vs 0.02 (Anthropic); 14-fold provider asymmetry |
| 2026-07-29 | **aipolcom** | Y | - | - | Rolling collection with prompt-variation, access-method, run-to-run stability and question-order |
| 2026-08-20 | — |  |  |  | Carnegie Endowment (Metaxa and Engler) calls for longitudinal monitoring infrastructure and name |
| 2026-08-29 | — |  |  |  | This project swaps its instrument to the 62 politicalcompass propositions and begins the forced- |
| 2026-08-30 | — |  |  |  | First noise floors measured; seven claims withdrawn |
| 2026-08-31 | — |  |  |  | Same-version null (97 pairs) measured; drift withdrawn; refusal found to be elicited by directiv |
| 2026-08-31 | **ours** | Y | Y | Y | Presentation order and same-version variation each move as many items as any deliberate manipula |
| 2026-09-01 | — |  |  |  | Detection limit computed: three of our own nulls are underpowered, including both used to retire |
| 2026-09-01 | — |  |  |  | Priority search: the OpenReview paper feared to contain a same-version null DOES NOT EXIST -- a  |
<!-- /GEN:timeline -->

That is not a claim about anyone diligence. It is a fact about uptake, and it is why this
paper contributes a decision rule rather than a discovery. The discovery was already made.

---

## 6. The standard being recommended right now is the wrong one

In August 2026 the Carnegie Endowment argued that one-off audits are insufficient and that the
field needs standing infrastructure for longitudinal monitoring of language models and
political information. That is correct and overdue. The piece names one methodological
standard:

> "the same prompt should be repeated fifteen to twenty-five times to get a reliable result"
> — Metaxa and Engler, Carnegie Endowment, 20 August 2026

Repeating one prompt measures sampling variability and nothing else, and on this instrument
that is the smallest term in the table: the run-to-run replicate floor is a median of 0 side
flips over 6,240 pairs, p90 3. It is *not* zero — at temperature 0 only 10 of 57 within-cell
groups come back byte-identical (§2) — but it is the one nuisance a study of this shape can
already see. A 2026
study of moral drift reports the same thing from the other direction — 82.2% of its
model-probe cells were byte-identical across ten trials — and concludes from it that
within-model noise is negligible and the differences it measures are therefore real.

Both are measuring the one factor they held constant and certifying against the ones they did
not. Twenty-five repetitions buy a tight interval around a number that was not moving, and
nothing at all about the factors that were.

The same call budget, spent differently:

| instead of | spend it on | what it buys |
|---|---|---|
| repetitions 3–5 of one prompt | three presentation orders | the largest missing variance term |
| repetitions 6–8 | one same-version pair per family per wave | a baseline the drift number can be scored against |
| discarding unparseable runs | retaining and classifying them by cause | refusal as a signal instead of a hole |
| a confidence interval | a confidence interval and a detection limit | whether the effect was resolvable at all |

None of this costs more. It is the same calls, allocated to factors that are free to vary in
deployment. A monitoring programme built to the fifteen-to-twenty-five standard will report
narrow intervals around drift estimates it cannot distinguish from reshuffling its own
questionnaire, and it will report them on a schedule.

### The standard control for order effects silently deletes data

The first row of that table — spend the repetitions on presentation orders — is the right
advice, and it is not ours: Domínguez-Olmedo et al. (2024) make the case for randomising
presentation better than we could. But the obvious way to implement it damages the collection,
and we found this in our own corpus rather than in anyone else's.

You shuffle the items and keep each item's id as its printed number, because the printed number
is what lets you score the sheet afterwards. The sheet then reads `20. … 31. … 1. … 23. …`. Ask
a model to answer a non-monotonically numbered list and some models silently skip lines.

Five local builds, twelve presentation orders, two conditions, two arms differing in nothing
but the numeral printed beside each proposition. Across 102 as-is sheets, **15 come back
incomplete**; across 100 renumbered sheets, printed `1.` to `32.` in presentation order, **the
count is 1**. Fisher exact, one-sided: **p = 1.8 × 10⁻⁴**. Repeated on eight hosted models with
each pinned to a single backend, so that the serving path cannot carry the contrast: **9
incomplete of 190 as-is sheets**, against **0 of 192 renumbered, p = 0.0017**.

**The loss is invisible from every direction a collection normally checks.** The sheet is not
refused. It is not truncated — it ends with a well-formed final answer and uses a fraction of
its token budget. It arrives looking complete, and a refusal table counting whole-sheet
declines cannot see it. What it produces is a **discard that conditions on compliance**: every
analysis in this study reads valid sheets only, so a susceptible model's analysed sample is
exactly the subset of items it chose to answer. That is a non-random subset of the instrument,
selected by the model, on the axis being measured.

The remedy costs nothing and is in the collector: renumber the presentation `1..32`, record the
map from printed label to item id, remap the answers back. The randomisation is unchanged.

**And the serving path moderates it, which nobody reports.** `nemotron-3.5-lightning` carries 7
of the 9 losses in the pinned hosted arm, so the same model was re-collected on a second
backend under an identical protocol. Each backend served 23 as-is sheets. **On DeepInfra 7 come
back incomplete; on Phala, 1.** Fisher one-sided **p = 0.0235**. Same weights, same twelve
orders, same numbering — a sevenfold difference in the loss rate from the serving path alone. A
study that does not pin its backend cannot reproduce its own non-response rate.

**What does not move is the remedy.** Pooled across both backends and all eight pinned models,
the as-is arm loses 10 sheets of 213 collected, and the renumbered arm loses 0 sheets of 216
collected there — p = 8.2 × 10⁻⁴.

Two honest limits remain. **Susceptibility is per model, not per class** — most models never
drop a line. And the three-way test that separates the item from its slot from its
printed numeral resolves only on the local arm, which had the depth for it; the hosted arm
establishes that the arms differ, not why. Full record in
`RESULTS-2026-09-18-omission-orders.md` and `RESULTS-2026-09-21-omission-pinned.md`,
pre-registered in `PREREG-2026-09-18-omission-orders.md`, counts and both p-values from
`scripts/omission_arms.py`.

---

## 7. The control the field already owns

Pairs of models that differ in size, tier, snapshot date or mode, and **not in version**. Same
instrument, same condition. If two checkpoints of the same model disagree, a version-over-version
claim has to clear that disagreement before it means anything.

> **This section was rewritten on 2026-09-19 and its central magnitude claim is WITHDRAWN.**
> On the retired 62-item questionnaire the same-version null was the *largest* nuisance in the
> table — median 5, p90 11, "nearly twice the order effect". On the 32-item battery it is the
> *smallest*. The argument for the control survives; the number that made it dramatic does not.
> Every withdrawn figure is named at the foot of this section rather than deleted.

<!-- GEN:null -->
```
factor                        pairs   side med/p90/max     p90 95% CI endpoint med/p90/max
same-version variants            24          1 / 1 / 2         [0, 2]        5 / 11 / 19
  same-version variants        same version, by kind: tier sibling 21, date snapshot 3; the same-name-later-SNAPSHOT subset -- the null a drift claim actually needs -- is n=3, median 0, p90 1, max 1, and the rest of this row is size and tier siblings
```
<!-- /GEN:null -->

**The null is small here, and it is below what this design can see.** Twenty-four pairs, side
statistic: median 1, p90 1, max 2. The detection threshold for that row is 2 and its minimum
detectable effect is **3** (`null_audit.py`). The entire observed distribution sits at or under
the threshold. So the honest reading is not "same-version variation is small" — it is
**"this instrument cannot resolve same-version variation from zero"**, which is a bound and not
a measurement.

That bound is still worth having, and it is the useful half of this section. A drift claim on
this instrument has to clear something; what it has to clear is now known and small, where
before it was unknown. Twenty-one of the twenty-four pairs are tier siblings and three are
date snapshots — the snapshot subset, which is the comparison a drift claim actually sits on,
is n=3 at median 0, p90 1, max 1. **Three pairs is not a distribution** and it is quoted as a
count, not a floor.

**What changed, and why the old version of this section said the opposite.** On the retired
62-item questionnaire this row was median 5, p90 11, over 97 pairs. Those 97 were mostly size
variants — 58 of them — against 24 tier siblings and 9 snapshots. The battery's 24 pairs are a
different and narrower population on a shorter instrument, and the two are not comparable in
the same units: a count out of 62 is not a count out of 32, and this project published a
correction for making exactly that comparison (`CORRECTIONS-2026-09-17-power.md`).

So the claim that same-version variation "does not fall with model progress" is withdrawn. It
was measured on one instrument and asserted about the phenomenon.

### What survives the withdrawal, in the other statistic

The withdrawn claims were all in **side flips**. Measured in **endpoints** — gaining or losing
a *Strongly* answer — the same-version row is not small at all. Ranked against every other
nuisance factor this study measures, on the same pairs and the same sheets:

Read the right-hand column of §2's generated floors table rather than a copy of it. Ranked by
endpoint median, `same-version variants` is **5**; nothing else in the table reaches 4. The
three-way tie beneath it at 3 is requantisation, one-sitting presentation order and the local
open-weight order arm; run-to-run replication is 2 and pooled presentation order is 1.

A hand-typed copy of that ranking stood here until 2026-09-21 and had drifted on five of its
six rows — 28 pairs against 23, 115 against 107, 5,998 against 6,240, 106 against 94, and
requantisation's side median 3 against 4. The conclusion was unaffected, which is why nobody
re-read it.

**Two checkpoints of the same model mostly agree on which side to take, and disagree more than
any other nuisance factor about how strongly to take it.** Median 5 endpoint changes of 32 —
the largest in the table — against a median of 1 side flip.

This is §2's finding turned on the null itself. The field scores side, side is the stable
statistic, and the moving one is discarded. That is exactly why the same-version control looked
negligible when this paper first measured it on the battery and looked enormous on the retired
instrument: **the two instruments were being read in different units.**

The comparison above is a ranking of rows measured identically on the same corpus, so it does
not require any row to clear a detection limit. The **absolute** endpoint figure does, and it
is marginal: the same-version endpoint MDE is 11 and its p90 is 11, so the upper tail sits at
the limit and the median sits below it. Stated as the ranking, which is what the data supports,
and not as a magnitude.

**This rescue is the reason the withdrawn figures above are listed rather than deleted.** A
claim measured in the wrong unit is not a claim that was wrong about the world.

The control is not merely overlooked. In at least one case it is removed on purpose. Rozado,
selecting 24 models for an eleven-instrument study, writes:

> "Specifically, I avoid including different versions of similar models, such as GPT-3.5-1106
> and GPT-3.5-0613, to ensure a more varied sample."
> — Rozado (2024), PLOS ONE, Methods

Those two snapshots are the null. Excluding them makes the model sample look more varied and
makes the resulting spread look more like a property of models. The same paper does carry one
perfect same-version pair without remarking on it — `grok-fun-mode` and `grok-regular-mode`,
identical weights, identical snapshot, differing only in mode, both fully scored in the
published data, neither mentioned in the text.

Every pair was checked by hand for one that crosses a version boundary; none does. Rows failing
the project's own data-integrity gate were verified to contribute nothing, both by the filter's
logic and by deleting them and recomputing to an identical pair set.

Stated precisely, because precision here cuts against us: a single-pair negative control is
not unprecedented. Naser (2026) reports one in a refereed venue, before this work. What no
audited study reports is the null as a distribution, with a median and an upper percentile,
against which one observed transition can be scored.

Most of them had the pairs. Röttger tested Llama2 7b, 13b and 70b, and both GPT-3.5 and GPT-4
at two snapshot dates each — four same-version comparisons in one paper, all of them present
as separate subjects rather than as a baseline. Naser's tier ladder is built from them by
design. Sakhawat's Table 7 lists gpt-4.1-nano, gpt-4.1-mini and gpt-4.1 in a row. The control
costs nothing to run because the runs already exist; it is a re-analysis, not a sweep.

**Withdrawn from this section on 2026-09-19, listed rather than deleted.** Each was true of the
retired questionnaire and is false of the battery:

| withdrawn | was | now |
|---|---|---|
| "half of all same-version pairs differ by 5 items or more" | median 5 of 62 | median **1** of 32 |
| "the p90 is 11 — nearly twice the order effect" | p90 11 | p90 **1**, and *below* the frontier order floor |
| "97 pairs — 58 size, 24 tier, 6 mode, 9 snapshot" | 97 | **24** — 21 tier siblings, 3 snapshots |
| "the snapshot subset is median 5, p90 16, max 16 — *higher* than the pooled row" | n=9 | **n=3**, median 0, p90 1, max 1 — *lower* |
| "the narrower and more apposite null is the harsher one" | — | reversed; it is the milder one |
| "same-version variation did not fall at all" with model progress | — | withdrawn: measured on one instrument, asserted of the phenomenon |
| "remove all 62 qwen pairs and the median stays at 5" | — | that pair population no longer exists |

The direction of the error is worth stating plainly: **every withdrawn figure made this
paper's case stronger than the data now supports.** They were not neutral slips.

---

## 8. Who this is a problem for

Not the authors of these studies, most of whom document their methods well enough that this
audit was possible at all. The floors do not show their effects are absent. They show the
studies cannot distinguish their effects from factors they held fixed, and the remedy is a
re-run rather than a retraction.

It is a problem downstream. These audits are cited in policy writing, in regulatory comment
and in journalism as evidence about what models believe and how that is changing. A coordinate
shift between two model versions, reported without a same-version baseline, gets read as a
fact about training when the field has never published what a non-transition produces. On our
measurement it produces a median of 1 side flip of 32 and up to 2 — and in the other statistic,
a median of 5 intensity changes and up to 19.

The fix is cheap, available to everyone already collecting this data, and for most of them it
is a re-analysis rather than a new sweep.

---

## 9. Limitations

1. **One instrument, one surface.** These floors are properties of **32** forced-choice items
   in 16 mirrored pairs, author-written, administered as a whole sheet in a single context.
   *(This read "62 items" until 2026-09-18 — the retired questionnaire's length, in a sentence
   describing floors measured on the current bank. A count out of 62 is not a count out of 32
   and the confusion has cost this study five withdrawn claims; see
   `CORRECTIONS-2026-09-17-power.md`.)* They are not a general fact about evaluating language
   models, which our own largest floor demonstrates: presentation order **does not apply** to
   designs that administer one item per call with the context cleared. Naser (2026) is such a
   design and the order critique is void against it.
2. **The order floor rests on 94 pairs.** That is enough to establish the split between
   classes and not enough to characterise either one precisely; the frontier arm is seven
   models from seven vendors across four shuffled orders plus the canonical one. Per-class
   pair counts are in the generated floors table (§3), not restated here.
3. **The estimator behind every interval here is anti-conservative at these sample sizes, and
   we can now say by how much.** Against a null built by splitting real cells in half
   (`calibrate_estimators.py`, 200 splits, 136 eligible cells), the sheet bootstrap rejects
   **10.5%** of true nulls where an exact permutation test rejects **4.5%** — nominal is 5%.
   That is a factor of two, not an order of magnitude, and it is measured on cells of the
   sizes this corpus has rather than at an asymptotic n; it does not transfer to an arm
   collected at a different depth.
   Measured 2026-09-19 against a family that at the time held 241 pre-registered contrasts
   (`exact_vs_bootstrap.py`; §9.1 carries the current size, which has grown since): the
   sheet bootstrap returns 104 surviving BH-FDR where an exact permutation test returns **84**
   — 20 lost, none gained, so **about one in five of its significant findings does not hold
   up**. Seven of the twenty involve a cell whose sheets barely differ from each other; the
   other thirteen are ordinary. The losses concentrate at small n and this study's cells are
   depth 5. Four A−N contrasts are among them, so §1's count is about 34 of 61 rather than 38.
   The *comparison* in §1 is unaffected — the order floor is computed by the same estimator and
   moves with it — but any single per-model claim in this paper should be read as bootstrap,
   not exact.
   *Replaces a limitation about the retired corpus ("23 of 37 shuffled-order cells hold one
   run"), which described a collection this paper no longer uses; every battery cell is
   collected to depth.*
4. **The controls audit covers fourteen external studies, 13 of them read in full**, main
   text and appendices and deposited code where it exists, and `controls_audit.py --strict`
   passes. **The twelfth, Sclar, was consulted rather than read end to end** and its row
   carries `partial` in the provenance column. Sakhawat and Messing were in that category
   until 2026-09-12 and are not any more; reading them resolved fifteen `unknown` cells, two
   of which had been read aloud in prose as absences. Sclar and Messing are cited for general findings rather than audited for controls,
   which is the lighter use, but the distinction was not previously stated. The Cen citation
   was confirmed only after being carried for days with no author list or venue.
5. **The external replication is half-internal.** One of the two corpora we would replicate on
   is this project's own public observatory, disclosed wherever it is used.
6. **No hostile read of this document.** Two have been run on individual results, none on the
   assembly.
7. **The detection limit uses one estimator.** The null is shifted upward until 80% of its mass
   clears the 95th percentile, which assumes an effect adds to noise of the same shape. That
   assumption is standard and it is still an assumption.
8. **Most of the tests in this paper are not in the corrected family**, and until 2026-09-19
   the paper did not say how many tests it ran at all. §9.1 below is the full accounting. One
   family is pre-registered and BH-corrected; the rest are exploratory, and each is now marked
   as exploratory where it appears rather than only here — a figure a reader meets in §3 and
   discovers is uncorrected in §9 has already done its work.

### 9.1 How many tests this paper runs

This table is **generated**, which is the point of it. The pre-registered family size was
hand-typed in four documents and those four said 153, 241 and 246 simultaneously — every stale
copy understating the correction burden, which is the direction that flatters. It is now read
from the analysis at build time and nothing in the prose holds a second copy.

<!-- GEN:comparisons -->
```
| family | tests | correction | command |
|---|---:|---|---|
| pre-registered condition contrasts | 246 | **BH-FDR across the family** | `position_analysis.py <run> --prereg` |
| jurisdiction gradient | — | **none — exploratory** | `scripts/jurisdiction_gradient.py` |
| claim-type split (normative / documented) | — | **none — exploratory** | `scripts/item_gradient.py --claim-type` |
| agreement by training class (the shared-RLHF objection) | — | **none — exploratory** | `scripts/agreement_by_training.py` |
| intensity by claim type (top-box rate, documented vs normative) | — | **none — exploratory** | `scripts/intensity_by_claim.py` |
| item omission -- item vs slot vs numeral | — | **none — exploratory** | `scripts/item_omission.py --matrix` |
| refusal switch by condition | — | **none — exploratory** | `scripts/refusal_table.py --switch` |
| clause factorial | — | **none — exploratory** | `scripts/refusal_table.py --factorial` |
| elicitation rung (rung 2) | — | BH within itself | `scripts/refusal_table.py --rung2` |
| group-attribute comparisons | 0 | n/a | `scripts/group_power.py` |

Every row below the first is **uncorrected and exploratory**. They are not thereby wrong, and they are not a second family that a correction was forgotten on: they were not pre-registered, and the requirement this study holds other papers to is that each is marked as exploratory *at its point of use* rather than only in Limitations. The `multiple_comparisons` column of the controls audit scores twelve other studies on exactly this.
```
<!-- /GEN:comparisons -->

The corrected family covers the condition contrasts and nothing else. **We are not claiming the
exploratory families need no correction** — we are declining to pool tests from different
designs into one family after the fact, which would change the threshold on the pre-registered
results according to how much exploratory work happened to be done. The honest version is to
report both counts and let a reader discount the exploratory rows as they see fit, which the
`multiple_comparisons` column of §6's audit asks of fourteen other papers and which none of them
does.

---

<!-- GEN:references -->
## References

Generated by `scripts/references.py` from `data/controls-audit.json`, the same record that supplies each study's row in the controls table. The provenance note on each entry says how we know what we claim about it.

- **barmettler2026** — Barmettler, Progressive in Principle, Centrist in Practice: LLM Political Bias Is Instrument-Dependent, arXiv:2606.00048
  *Instrument:* Smartvote questionnaire (75 policy questions) on 66 models; 48 real Swiss federal referenda on 9 flagship models, four languages, three information conditions  *Scale:* 66 models on the questionnaire, 9 on the referenda. One administration per model-item: "All models were queried via the OpenRouter API with deterministic parameters: temperature=0.0, seed=42."
  *Provenance:* read in full.
- **cen** — Cen S H, Ilyas A, Driss H, Park C, Hopkins A, Podimata C, Madry A, Large-Scale, Longitudinal Study of Large Language Models During the 2024 US Election Season, arXiv:2509.18446 [cs.CY], 22 September 2025
  *Instrument:* bespoke structured survey, 12,638 questions -- 12,606 election questions across nine categories plus 32 non-election baseline questions from TriviaQA and MedQA; each non-baseline question x 21 prompt variations  *Scale:* 12 models queried near-daily July-November 2024 across 100+ days; temperature 0 offline and 0.1 online; 128-token cap; approximately $40k of API spend
  *Provenance:* read in full.
- **dominguezolmedo2024** — Dominguez-Olmedo R, Hardt M, Mendler-Dunner C, Questioning the Survey Responses of Large Language Models, NeurIPS 2024 (arXiv:2306.07951)
  *Instrument:* 25 multiple-choice questions from the 2019 American Community Survey; replicated on ATP, GAS/WVS and ANES  *Scale:* 43 models, 110M to 175B parameters; responses read as renormalised next-token logits over choice labels rather than sampled text; all choice orderings evaluated where feasible, 5000 permutations cap, 50 for OpenAI models; ~1500 A100 GPU-hours
  *Provenance:* read in full.
- **kamal2025** — Kamal S, Prakash L P Y, Rafiuddin S M, Rakib M, Sen A, Ray Choudhury S, A Detailed Factor Analysis for the Political Compass Test: Navigating Ideologies of Large Language Models, IJCNLP-AACL 2025 (short), pp. 284-303, anthology 2025.ijcnlp-short.25; preprint arXiv:2506.22493
  *Instrument:* Political Compass Test (62 items, 4-point), plus 8 Values as a check  *Scale:* 4 models all 4-bit quantised (Llama3-8B-Instruct, Mistral-7B-Instruct-v0.3, Falcon3-7B-Instruct, Gemma-3-4b-it) x 9 instances each (base + 8 LoRA fine-tunes) x 10 prompts x 8 decoding combinations; 2,693 PCT tests retained of an intended 2,880; plus Llama3.2-1B in full and 4-bit precision for A.5
  *Provenance:* read in full.
- **liu2025** — Liu Y, Panwang Y, Gu C, 'Turning right'? An experimental study on the political value shift in large language models, Humanities and Social Sciences Communications 12:179, 2025, doi:10.1057/s41599-025-04465-z
  *Instrument:* Political Compass, 62 items, forced 4-point numeric scale, scored onto economic and social axes on [-10, 10]  *Scale:* 4 static snapshots -- gpt-3.5-turbo-0613, gpt-3.5-turbo-1106, gpt-4-0613, gpt-4-1106-preview; 3 API accounts x 10 questionnaires = 30 runs per model, 7,440 item responses; temperature left at default (=1) deliberately; then bootstrap 100 and 1,000 replicates
  *Provenance:* read in full.
- **naser2026** — M.Z. Naser, Tracing moral value drift across large language model generations and their societal implications, Technology in Society 87 (2026) 103431
  *Instrument:* 107 moral probes (63 MFQ-adapted, 26 ethical dilemma, 7 value priority, 11 meta-ethical), 6-point Likert  *Scale:* 14 model snapshots, 2 providers, 2 tiers, ~9500 calls, 10 trials/probe at T=0
  *Provenance:* read in full.
- **messing2026** — Messing S, Hidden Measurement Error in LLM Pipelines Distorts Annotation, Evaluation, and Benchmarking, arXiv:2604.11581, April 2026 (rev. May 2026)
  *Instrument:* LLM evaluation and annotation pipelines generally  *Scale:* benchmark and judge pipelines; MMLU and Elo-style match evaluation
  *Provenance:* read in full.
- **motoki2024** — Motoki F, Pinho Neto V, Rodrigues V, More human than human: measuring ChatGPT political bias, Public Choice 198(1), 3-23, 2024, doi:10.1007/s11127-023-01097-2
  *Instrument:* Political Compass, 62 items, forced 4-point scale coded 0-3, no neutral option; plus an author-written 62-item placebo battery and the IDRLabs Political Coordinates Test as robustness  *Scale:* ONE model -- text-davinci-003, named only in the supplement -- at temperature 0.7; 100 rounds per condition per country, each round one call carrying all 62 items; bootstrap 1,000 replicates over the 100-answer sample
  *Provenance:* read in full.
- **rottger2024** — Rottger, Hofmann, Pyatkin, Hinck, Kirk, Schutze, Hovy, Political Compass or Spinning Arrow? Towards More Meaningful Evaluations for Values and Opinions in Large Language Models, ACL 2024, pp. 15295-15311
  *Instrument:* Political Compass Test  *Scale:* 10 models (Llama2 7b/13b/70b chat, Mistral 7b Iv0.1/Iv0.2, Zephyr 7b beta, GPT-3.5 0613/1106, GPT-4 0613/1106), 62 PCT propositions, temperature 0 throughout, 5 forcing levels, 10 paraphrase templates, open-ended arm
  *Provenance:* read in full.
- **rozado2024** — Rozado D, The political preferences of LLMs, PLoS ONE 19(7): e0306621, 2024, https://doi.org/10.1371/journal.pone.0306621
  *Instrument:* 11 political orientation tests (Political Compass, Political Spectrum Quiz, World's Smallest Political Quiz, Political Typology, Political Coordinates, Eysenck, Ideologies, 8 Values, Nolan, iSideWith US and UK), 401 items total  *Scale:* 24 conversational + 5 base + 3 self-finetuned models; 2,640 test administrations (11 tests x 10 trials x 24 models); 96,240 items; temperature 0.7, max 100 tokens; collected Dec 2023 - Jan 2024
  *Provenance:* read in full.
- **sakhawat2026** — Sakhawat, Islam, Farhin, Raiyan, Mahmud, Hasan, Political Alignment in Large Language Models: A Multidimensional Audit of Psychometric Identity and Behavioral Bias, arXiv:2601.06194v1
  *Instrument:* Political Compass (62 items), SapplyValues (46), 8 Values (70)  *Scale:* 26 models, 10 administrations per inventory per model, context cleared between runs, temperature 0.7 and top_p 1.0 ("All models are queried with temperature=0.7 and top_p=1.0, balancing determinism with natural language variability")
  *Provenance:* read in full.
- **sclar2024** — Sclar M, Choi Y, Tsvetkov Y, Suhr A, Quantifying Language Models' Sensitivity to Spurious Features in Prompt Design, or: How I learned to start worrying about prompt formatting, ICLR 2024 (arXiv:2310.11324)
  *Instrument:* few-shot benchmark tasks, not a values or political instrument  *Scale:* several open LLMs; meaning-preserving prompt FORMAT variations
  *Provenance:* partial.
- **tornberg2026** — Toernberg, Schimmel, Political Bias Audits of LLMs Capture Sycophancy to the Inferred Auditor, arXiv:2604.27633
  *Instrument:* Political Compass Test, Pew Political Typology, and 1,540 partisan-benchmarked Pew American Trends Panel items; 30,990 responses  *Scale:* 6 frontier models via the Requesty API gateway, April 2026. Main grid is "one response per item-model-condition cell", plus "three additional replicates at T=1.0 (27,000 additional calls), and one replicate at T=0 (greedy decoding; 9,000 calls)"
  *Provenance:* read in full.
- **aipolcom** — aipolcom.net, rolling public observatory
  *Instrument:* politicalcompass.org 62 propositions, forced choice  *Scale:* 57 models, 930 answer sets (729 model, 201 synthetic control), collection 2026-07-29 to 2026-08-29
  *Provenance:* read in full.

Thirteen of the 14 are read in full. The remainder — sclar2024 — was consulted as abstract and PDF without the full text being read end to end, and no verdict in the controls table rests on more than that.
<!-- /GEN:references -->

## Reproduction

```
python scripts/gen_paper.py --check        # every table current?
python scripts/floor_table.py              # section 2
python scripts/power.py                    # section 3
python scripts/controls_audit.py --strict  # section 5, and the publication gate
python scripts/refusal_table.py --audit    # section 1
python scripts/validate_claim.py --runs <dir>
python scripts/key_numbers.py --check      # do the SENTENCES still match the tables?
python scripts/references.py               # the reference list below
```

**One of those exits 1 by design and a reader should not read it as a broken build.**
`validate_claim.py` fails on the lineage sweep over 12 persisted transport rows and one
all-one-answer sheet from grok-4.3, both of which every analysis already excludes — verified by
the filter's logic and by deleting them and recomputing to an identical pair set. It is not
fixed by loosening the check.

`refusal_table.py --audit` **passed as of 2026-09-04, and it had been failing for a bad
reason.** It was comparing today's derivation against 27 stored labels written by rules this
project deliberately replaced — 5ecf8a1 swapped lexical refusal detection for the structural
test because the lexical one undercounted, 96e5fa5 stopped truncation being read as refusal —
so a gate whose job is to catch the recomputed rule *drifting* from the collector's could not
tell drift from an improvement, and had been permanently red and consequently unread.

Run records now carry a `classifier` version, so the audit partitions: rows labelled by the
current rule are held to exact agreement, rows labelled by a superseded one are reported by
transition as history. That partition alone would have been a way around the failure rather
than a fix, and it made the strict half **vacuous** — no row carried the new version yet, so
it reported agreement over zero rows. So the collector's rule is now a callable
(`run_battery.classify_failure`) and the audit runs both implementations of it over all 1,657
rows and compares them to each other, needing no stored label and no re-collection. That is
what the gate always claimed to test. The two agree on every row; the 27 superseded labels are
printed, and if that count grows someone changed a rule without bumping the version.

Three gates must pass before this is circulated: `gen_paper.py --check` that the tables are
current, `key_numbers.py --check` that the prose quoting them is current, and
`controls_audit.py --strict` that no claim about another study rests on our own notes rather
than on the paper. All three pass as of this build. The second exists because the frontier
sweep on 2026-09-01 moved the order floor and six sentences quoting it went stale in the same
minute; nothing caught that until the check did.

### Where each arm is pre-registered and reported

Every collection in this paper has a pre-registration committed before its first call and a
results document written against it. They are the record a reader should check the paper
against, and several report things the paper does not lean on.

| arm | pre-registered | reported |
|---|---|---|
| refusal direction, ablation vs prompt | `PREREG-2026-08-28-refusal-direction.md`, `PREREG-2026-09-07-ablation-vs-prompt.md` | §1, §1b |
| the mask surface — pressure × ablation | `PREREG-2026-08-29-mask-surface.md`, `PREREG-2026-08-29-mask-surface-v2.md` | §1b |
| which clause of the balance instruction causes refusal | `PREREG-2026-08-31-clause-factorial.md` | §1 |
| the same items through both scoring paths | `PREREG-2026-09-12-same-items-both-paths.md` | §4 |
| frame, and the content-free placebo | `PREREG-2026-09-13-frame-and-placebo.md` | §1 |
| rung 2 of the escalation ladder | `PREREG-2026-09-13-pipeline-rung.md`, `PREREG-2026-09-20-rung2-control-v2.md` | §4 · `RESULTS-2026-09-21-rung2-control-v2.md` |
| the main forced-choice collection | `PREREG-2026-09-14-i3-phase4.md` | §2, §3, §7 |
| silent omission: item, slot or printed number | `PREREG-2026-09-18-omission-orders.md` | §6 · `RESULTS-2026-09-18-omission-orders.md`, `RESULTS-2026-09-21-omission-pinned.md` |
| Röttger's statistic on this instrument | `PREREG-2026-09-18-paraphrase.md` | §2 · `RESULTS-2026-09-21-paraphrase.md` |
| the dose series | — | `RESULTS-2026-09-18-dose-series-preflight.md`, `RESULTS-2026-09-19-dose-response.md` |
| the Gemma-2-9B re-collection | — | `RESULTS-2026-09-20-gemma2-recollect.md` |

`PREREG-DRAFT-factions.md` is a draft for an instrument that was never collected, kept because
a pre-registration that did not become a study is part of the record of what was tried.

Raw runs, every script, and the full record of what was withdrawn are in the repository. The
instrument is `data/ratchet-battery.json` — 32 forced-choice items in 16 mirrored pairs,
written by the author and MIT-licensed with the rest of the repository. It ships here in full: there is no fetch step,
no carve-out, and the item text and the response text both publish.

This paragraph said the instrument was externally authored until 2026-09-17. It was, until
2026-09-16 — and that change is the whole reason every floor in this paper was re-measured;
see `CORRECTIONS-2026-09-17-*.md`. A study whose argument is that a field should publish what
it measures could not be built on an instrument it was not permitted to show you.
