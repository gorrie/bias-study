# Correction, 2026-09-18 — the position estimator rejected half of all true nulls

> **WITHDRAWN: "a content-free placebo significantly moves measured position on 16 of 37
> models."** Published in `PAPER-below-the-floor.md` §1, `README.md`, `PLAN.md` and
> `FINDINGS-2026-09-17-battery.md` on 2026-09-17/18. It was the paper's lead finding for
> roughly nine hours. The correct figure under a calibrated estimator is **4 of 39**, against
> a false-positive rate of **6.2%** — which on 39 models is about 2.4 models expected by
> chance. Four is not distinguishable from that.
>
> The honest statement is **absence of evidence**: this design cannot show that the
> content-free instruction moves position. It is not evidence that the instruction is inert.

## What was wrong

`position_analysis.contrast()` paired each model's 16 items on `pair_id` and bootstrapped the
**pair-deltas**. By the time it saw them, `cell_positions()` had already averaged every sheet
in the cell into one number per (model, condition, pair).

So a sheet-level disturbance — a different sitting, a different draw at temperature 0.7 — had
been folded into an offset that **all sixteen deltas share**. A pair-bootstrap cannot separate
a shared offset from a treatment effect. It sees sixteen numbers that agree with each other and
returns a narrow interval.

**The exchangeable unit is the sheet, and nothing resampled sheets.**

## How it was measured

Condition N was split in half at random, per model, and one half relabelled. Nothing differs
between the halves: same model, same condition, same instrument, same protocol. A calibrated
test calls about 5% of models significant after BH-FDR.

```
TRUE NULL, 8 trials, 272 model-contrasts

  pair bootstrap  (as published)   135 of 272 significant   49.6%
  sheet bootstrap (corrected)       17 of 272 significant    6.2%
  nominal after BH-FDR                                       5%
```

The largest |effect| the split-half null produced was **0.309**. The largest observed placebo
effect was **0.198**. The lead finding sat inside its own noise, and nothing caught it because
the noise had never been measured in the unit that carries it.

```
PLACEBO MINUS BASELINE, the same records

  pair bootstrap    18 of 39 models MOVE (46.2%)   max |effect| 0.198
  sheet bootstrap    4 of 39 models MOVE (10.3%)   max |effect| 0.198
```

The point estimates did not move. Only the intervals did, and only because they are now built
over the thing that varies.

## What the corrected estimator says about everything else

Re-derived on the same records, 39/37/40-model families, BH-FDR within each:

| contrast | pair bootstrap (withdrawn) | **sheet bootstrap** | median effect |
|---|---:|---:|---:|
| **A − N** the balance instruction | 28 of 37 (75.7%) | **25 of 37 (67.6%)** | −0.159 |
| **A − P** instruction vs placebo | 28 of 37 (75.7%) | **27 of 37 (73.0%)** | −0.188 |
| **D − P** commitment vs placebo | 27 of 40 (67.5%) | **13 of 40 (32.5%)** | +0.112 |
| **P − N** the placebo | 19 of 39 (48.7%) | **4 of 39 (10.3%)** | +0.014 |

**The manipulation survives; only the placebo collapses.** The broken estimator was not
uniformly noisy — it was specifically manufacturing the control-arm result. The balance
instruction moves position on 25 of 37 models against ~2.3 expected by chance, and the
instruction tested directly against the placebo is the strongest contrast in the study.

### Prediction 2 does NOT flip — and a correction inside this correction

**An earlier version of this file said prediction 2 goes FAIL → PASS. That was wrong**, written
from the contrast counts before `--prereg` was re-run, and it is corrected here rather than
edited away. Re-derived on the corrected estimator, prediction 2 is still **FAIL**: the placebo
contrast excludes zero on **3 of 37** models, and the criterion fails on any model at all.

**But the criterion cannot be met by a working control arm, and that is the real finding.** It
asks that the placebo contrast exclude zero on *no* model after BH-FDR. BH controls a false
discovery *rate*; permitting some false discoveries is what it does. At the measured 6.2%
false-positive rate on a 39-model panel, about **2.4 models are expected to clear it by
chance**. Observed: 3. The prediction is written so that a perfect control arm fails it.

This is the second time this exact defect has been found in prediction 2. The first was a ratio
whose verdict flipped with the denominator cutoff — recorded in `position_analysis.py` — and
the fix was to answer it per model against each model's own interval. That fix inherited the
same flaw one level up: a per-model test with no tolerance for the error rate it runs at.

**What should be asked instead**, and what the next pre-registration must state: is the
placebo's rate of significant movement distinguishable from the estimator's own false-positive
rate, measured on a true null from the same corpus? Here: 3 of 37 (8.1%) against 6.2%. It is
not. The honest verdict is that **the placebo behaves like a control arm**, and the
pre-registered test is not capable of saying so.

The prereg's fixed consequence — *"if prediction 2 fails, the Phase 0 direction reading is
WITHDRAWN, not reinterpreted"* — therefore fires on a test that a correct result cannot pass.
The withdrawal stands as a matter of procedure. It should not be read as evidence about the
placebo.

## What else this touches

**Every contrast in the 153-member family**, because F−N, C−P and F−P are computed by the same
function. Any per-model "which models move" statement in any document predating this correction
was produced by the miscalibrated path and must be re-derived, including:

- pre-registered **prediction 2** ("the placebo does not do the work") — its FAIL verdict was
  computed this way and is under review;
- pre-registered **prediction 1** ("the fairness instruction compresses |position|");
- `FINDINGS` §6b's "**not one verdict moved when the corpus grew 40%**", which is weaker than
  it reads: a statistic that fires on half of all true nulls is *stable* under resampling for
  the same reason it is wrong.

**What it does NOT touch**, checked rather than assumed:

- **The floors.** `floor_table.summarise()` has its own cluster bootstrap and does not call
  `contrast()`.
- **The numbering-artifact result** (`RESULTS-2026-09-18-omission-orders.md`). A within-model
  randomised contrast tested by Fisher exact on sheet counts; no bootstrap anywhere in it.
- **The refusal switch** (`refusal_table.py --switch`). Counts.
- **The claim-type split** (`key_numbers.contested_vs_documented`). Proportions over answers.

## The fix

`position_analysis.contrast_sheets()` resamples **sheets** within each arm, independently, at
each arm's own size, and recomputes the pair means from the resampled sheets on every draw. It
also flags `single_sheet_arm`: a cell holding one sheet carries no variance and is now reported
as such instead of borrowing precision from the pairs.

`contrast()` is **kept**, marked MISCALIBRATED, with the measured rate in its docstring.
Deleting it would erase the evidence that the published numbers came from it, and the two have
to run side by side to show what changed.

## Why it was not caught

The check that found it costs nothing and needs no new data: split one arm in half and see how
often the machinery finds a difference that cannot exist. It was never run. `--placebo-table`
was built, written into the paper, the README and the plan, and reported to the author, all on
an estimator whose calibration had not been tested — on the same day the same tree gained a
`null_audit.py` whose opening line is *"a null with no MDE is not a finding, it is a sample
size."*

The general rule, for `LEARNINGS.md`: **an estimator that has never been run on data with a
known answer is not a measurement instrument.** Every floor in this study exists because the
same question was asked of the instrument. It was not asked of the estimator.
