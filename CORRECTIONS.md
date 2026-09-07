# Corrections

Every claim this study has published and then withdrawn or narrowed, with the date it went out,
the date it came back, and what replaced it. Nothing here is deleted from the history — the
commits that carried these claims are still in this repository, because a record of what was
claimed and when is worth more than a tidy one.

A correction is listed here whether it was caught by us, by a reviewer, or by the data moving.
The ones we caught late are the ones worth reading.

---

## The retracted claims

### 1. "Not one of them declines when told firmly to answer"

**Published:** 2026-08-31 (`7fc2ed6`), restated 2026-09-01 (`dc6c874`).
**Withdrawn:** 2026-09-04.

The claim was that a firm instruction takes refusal to exactly zero — "none in 347 runs where
it carries one."

**It was true when it was written and stopped being true.** A requantisation sweep added four
small local models, and three of their runs under the commitment directive came back as
declines. The absolute claim is gone.

**What replaced it, and it survives every weighting:** of the models that decline without a
directive, *all of them stop* when given one — no exceptions. Separately, a few other models
decline *only* when told to commit, each on a single run.

**Why it survived as long as it did:** the zero was hand-typed into the prose while every other
number in that paragraph was generated. The gate that recomputes the rest checked the `347`
beside it and not the `0`. Both halves are gated now (`arms_dir_refusals`, `arms_silenced`,
`arms_dir_only`), and the phrase itself is in a `RETRACTED` list that fails the build if any
surface asserts it again.

### 2. The rate summary that replaced it, first time round

**Published:** 2026-09-04, in the correction to #1.
**Withdrawn:** same day.

The first fix reported the effect as a rate: refusal goes "from 7.8% to 0.8%, a factor of ten."
Pooled, those are the numbers. They are also dominated by a single model — one Gemini build
contributes most of the no-directive refusals. Weight each model equally and the rate goes
**up**, because the models that decline under a directive have one directive run each.

Two defensible weightings, opposite signs. That is the net-aggregate-concealing-gross-movement
pattern this paper convicts other studies of, committed in our own headline. The paired count
above replaced it because it survives both.

### 3. "n too small" on the requantisation interval

**Published:** through 2026-09-04.
**Withdrawn:** 2026-09-04.

The requantisation floor rested on 4 pairs from a single weights family, and its interval was
reported as uncomputable. It now has 13 pairs from four families and a real CI. Any surface
still saying the interval cannot be computed is describing the retired version.

### 4. "The manipulation floor is 14" — narrowed 2026-09-05

Not a retraction; a reframing that matters more than the number.

> **The figures in this entry were superseded on 2026-09-06 by correction 6 below.** The p90 is
> 15, not 14, and three values in the distribution move. The reframing this entry is actually
> about — read the spread, not the p90 — is unaffected, and the entry is left as written because
> it is the record of what was published on 2026-09-05.

The `prompt condition A→D` row is this paper's reference scale — the deliberate political
manipulation every nuisance floor is compared against. It rested on **7 model pairs collected in
one sitting**, with a p90 95% CI of **[2, 14]**: an error bar nearly as wide as the ruler, on a
lower bound that admitted a deliberate manipulation might move fewer items than rerunning the
same prompt.

Extended to 20 pairs, the point estimate did not move — 14 before, 14 after. **The distribution
is what changed the reading.** Date-pure, the twenty models move:

`0, 0, 0, 1, 1, 1, 2, 2, 2, 2, 3, 5, 5, 5, 5, 6, 8, 14, 18, 19`

**Seventeen of twenty move 8 items or fewer**, inside the floor for rerunning the identical
prompt. The p90 of 14 is carried by three models from one vendor. So the honest comparison is
not "two nuisance factors reach past the deliberate manipulation" — it is that **for most models
the deliberate manipulation does not reach past rerunning the prompt**, and the number we used
as a reference describes one vendor rather than the field.

That is a stronger result than the one it replaces, and it was invisible at seven pairs.

### 5. "The bias is in the systems being scored, not the panel" — narrowed 2026-09-05

**Published:** 2026-08-31.
**Narrowed:** 2026-09-05.

High agreement between judges was read as the absence of a judge lean. It is not. The panel's
internal spread is **0.29 points**, larger than two of the five published effects, and it is not
constant across the arms: gemini-2.5-flash sits at +0.044 under the balance instruction and
+0.290 under the bare question, so it does not simply subtract out of a within-model delta.

Settled by re-scoring each finding under each judge alone. **The two large effects survive every
judge** — claude-opus-4.7 +0.80…+1.50, grok-4.3 +0.80…+1.30. The smallest ranges +0.03 to +0.60
depending on who scores it, and its low end is that model scoring itself; it is now reported as
suggestive with its range rather than as a finding of equal standing. Two of the five findings
are self-judged, which is disclosed in the README.

### 6. Three floors were a property of the filesystem — corrected 2026-09-06

**Published:** through 2026-09-05.
**Corrected:** 2026-09-06.

The floor table was not reproducible across machines. Running the identical analysis on the
identical commit gave one answer on Linux and another on Windows, and the difference sat in
published numbers.

**The mechanism.** Each cell's reference sheet is the per-item *modal* answer across its runs.
That was computed with `Counter.most_common(1)`, which breaks a tie by insertion order —
insertion order was the order the run files were read, and they were read in whatever order the
filesystem's `glob` returned. So on any item where a cell split evenly, say 2 runs Disagree and
2 Agree, the reference answer was decided by the directory listing. Every endpoint delta is
measured against that sheet.

**What moved:**

| row | published | corrected |
|---|---:|---:|
| prompt condition A→D, side-flip p90 | 14 | **15** |
| same-version variants, side-flip p90 | 12 | **11** |
| same-version variants, p90 95% CI | [9, 13] | **[8, 13]** |
| same-version variants, endpoint median | 9 | **8** |
| presentation order, side-flip MDE | 12 | **13** |
| presentation order, endpoint p90 | 10 or 11, by machine | **10** |

The A→D distribution moves in three places: `3 → 4`, one `5 → 4`, and `14 → 15`. It now reads
`0, 0, 0, 1, 1, 1, 2, 2, 2, 2, 4, 4, 5, 5, 5, 6, 8, 15, 18, 19`.

**No conclusion in this paper changes.** Correction 4's reframing survives intact — 17 of 20
models still move 8 items or fewer, still inside the run-to-run replicate floor, and the tail is
still three models from one vendor. The two power verdicts that quote the order floor keep their
verdicts on the new MDE.

**How it was found, because that is the useful part.** A CI run went red on a gate that was
green on the author's machine, against the same commit. The gate reported only `STALE blocks:
floors` — a name and no diff — so the run data, the committed tree and the Python version all
had to be eliminated by hand before the environment was a suspect at all. That gate now prints
the diff, which is what named the defect in one line.

**Fixed in two places, so neither can reintroduce it:** the corpus glob is sorted, making the
read order canonical; and `modal()` breaks ties by the lower position explicitly. That rule is
arbitrary — a tie means the cell has no modal answer for that item — and the point is that it is
now written down instead of inherited from a dict. Four tests pin it, including one that shuffles
the corpus order and requires every floor to come back byte-identical.

### 7. "The manipulation is smaller than the nuisance floors" — withdrawn the day it was published

**Published:** 2026-09-06.
**Withdrawn:** 2026-09-06.

Wave 0 measured the deliberate manipulation under one protocol in one sitting and returned p90
**7**, against a pooled figure of 15. We published that as: the manipulation moves fewer items
than reordering the questionnaire (11) or swapping model variants (11), and called the
comparison like-for-like.

**Three things were wrong with it**, and an adversarial review of our own finished state found
all three within the hour.

*It crossed protocols.* No nuisance floor has been collected under the wave's protocol. The one
the wave itself contains — a bare question against a content-free system prompt, two
instructions that say nothing about politics — is **p90 3**, against the manipulation's 7.
Like-for-like inside one sitting, the deliberate manipulation is the **larger** effect.

*It compared a consensus against a single run.* The manipulation figure pairs a five-run modal
sheet. The order figure mostly does not: **23 of its 37 shuffled-order cells hold exactly one
run**, so that side carries a full unit of run-to-run noise the other side averaged away. We
verified that `modal()` was *called* on both sides and reported the comparison as sound. Whether
a function is called is not the same question as what it was fed — our own "measure the
artifact, not the source" rule, applied one level too shallow.

*And the drop from 15 to 7 is one model.* Remove `x-ai/grok-4.5` from the pooled arm and it
reads 8. Its answers under the commitment instruction are bimodal: four of five runs land
together, the fifth lands 15–18 items away. A modal sheet cannot represent that — it reports
whichever mode the sampler favoured, which was 2 on one collection and 18 on another. The
mechanism we offered ("averaging reveals the position") assumes a single position exists. The
supporting claim that temperature-0 runs are near-identical is also false on this corpus: 263
within-cell pairs, median 1, p90 5, **max 32**, only 10 of 57 cells byte-identical.

**What replaced it, and then what settled it.** The immediate replacement was: the deliberate
manipulation moves a median of 3 items of 62 and 23 of 25 models move 8 or fewer, while the
nuisance factors move comparable amounts, and which is largest is unsettled.

**The 310 calls were then run, the same day.** Two shuffled item orders across the same fixed
panel, same frozen parameters, same five swept seeds, condition D — chosen because A is 28.2%
invalid on this panel against D's 2.9%, so an order floor measured under the balance
instruction is computed on whichever models happen not to refuse it.

Like-for-like, a five-run consensus against a five-run consensus on both sides:

| row | pairs | median | p90 | max | p90 95% CI |
|---|---:|---:|---:|---:|---|
| presentation order, one sitting | 85 | **1** | **10** | 21 | [3, 12] |
| prompt condition A→D, one sitting | 25 | **3** | **7** | 14 | [4, 12] |

**Neither is demonstrably larger.** The intervals overlap across nearly their whole length, and
what distinguishes the two is shape rather than size: item order usually moves almost nothing
and occasionally moves ten items; the manipulation moves a few on nearly every model and rarely
more than eight. Rare-and-large against common-and-small.

The claim the paper now makes is narrower than either version it reached for: **a factor nobody
controls for and a factor built to move the answer are the same size on this instrument,
measured the same way.** Any published effect below about ten items of 62 is inside the range
item order alone produces.

Both manipulation rows now print in the floor table, the chart draws both reference lines, and
the sample size behind each modal is disclosed on the row.

---

## How to read this file

If a number in the README, the writeup or the run data disagrees with something you have seen
quoted elsewhere, this file is the first place to look. If a claim you can find in the git
history is not listed here and you think it should be,
[open an issue](https://github.com/gorrie/bias-study/issues) — a missing entry is itself a
defect of the kind this document exists to record.
