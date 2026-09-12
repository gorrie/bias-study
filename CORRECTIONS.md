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
internal spread is **0.2926 points** — larger than the smallest of the five published effects
(+0.2333) and just under the second smallest (+0.3000), not larger than two of them, which is
what this file said until 2026-09-12 — and it is not constant across the arms: gemini-2.5-flash sits at +0.044 under the balance instruction and
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

**And that pooled comparison was ALSO wrong, corrected the same day.** §2 of the paper argues
the order row is two populations rather than one and calls splitting it the most important line
in the paper; the comparison against the manipulation pooled it anyway. Two measurements fix it.

**The estimator's own error, which nothing had measured.** Every floor pairs a *modal* answer
sheet — the per-item majority across a cell's runs — and a modal is a statistic that moves when
you draw again. Bootstrapped over 110 cells, two modals of the *same* cell under the *same*
condition: **median 1, p90 3.** It is now a row in the floor table, because it is the
denominator every other row needed and never had.

**Split by model generation, and the ordering inverts.** On the 24 models in both arms:

| | models | order med / p90 | manipulation med / p90 | order larger on |
|---|---:|---|---|---|
| 2026 frontier APIs | 20 | 1 / **3** | 2.5 / **5** | 4 of 20 |
| 2024 open-weight, 7–14B | 4 | 11 / **12** | 4 / **8** | 4 of 4 |

Paired within each model: median difference **−1** item, 95% CI [−2, +0.5], sign test p = 0.29
over the 22 that differ. Pooled, order looked larger; within models the manipulation is larger
on 14 of 24. **A net aggregate concealing gross movement between two populations — this paper's
own charge, in its own headline, twice in one day.**

**What the study now claims, by generation:** on current frontier models item order is not
measurable (p90 3 = the modal's own error) while the manipulation is small but real (median 2.5,
p90 5, larger on 16 of 20); on the 2024-generation open-weight models most of this literature
was built on, item order dominates (p90 12 vs 8, on every model). Röttger predicted that split
in 2024.

The sentence this project reached for twice, in both directions, was never available. The answer
depends on which generation you measure, the effects are small enough that the estimator
matters, and a study pooling the two cannot say which factor moved its result. Ten cells in this
corpus have a modal so unstable — `deepseek-v4-flash` under P reaches p90 27 — that no
modal-based measurement of them means anything.

Both manipulation rows now print in the floor table, the chart draws both reference lines, and
the sample size behind each modal is disclosed on the row.

### 8. "One null inverted outright" — withdrawn 2026-09-07

**Published:** 2026-09-05, in the paper's §4, in `power.py`'s audit output, and in the README.
**Withdrawn:** 2026-09-07.

The null-power audit reported that of five published null results, four sat below their own
detection limit and one **inverted**: an ablated model filed as showing no stance movement
moved 12 items of 62 against a detection limit of 9, so the pair showed real stance movement
after all.

**That 12 is a single run per arm.** A one-run sheet is not a modal; every other
modal-vs-modal number in this study rests on four or five swept seeds, and the run-to-run
replicate floor is **p90 5**. A 12 derived from n=1 sits inside its own noise before any
ablation acts. The "detection limit of 9" quoted beside it does not appear anywhere in the
generated numbers either.

It is the same defect the section convicts, committed one layer further in: the strongest
verdict available — an *inversion* — resting on the thinnest sample in the corpus, inside the
paragraph arguing that null results need their resolution computed before they are trusted.
And it was the audit's single most quotable line.

Two mechanical faults let it stand. `power.py` printed **SUPPORTED** for that entry, and a
caveat on the observed effect now disqualifies that verdict rather than decorating it. Its
summary line also counted "not supported" as one category, so the script reported 3
underpowered nulls in its body and 4 in its summary while the prose quoting it said 3; there
are three categories and they are counted separately now.

**Also corrected in the same passage:** "four of our five" nulls below their resolution, where
the generated figure is **three**.

**What replaces it:** nothing yet, deliberately. The 2026-09-07 ablation wave re-collects that
exact pair at n=5 with a swept seed. Until that is analysed the claim is undecided in both
directions.

### 9. The vendor comparison pooled five vendors as one — corrected 2026-09-07

**Published:** 2026-09-07. **Corrected:** 2026-09-07, hours later, by review.

`vendor()` returned the literal string `"local"` for every model name without a slash. So
`gemma2`, `llama3.1`, `phi4`, `qwen2.5` and `mistral` — **five different vendors** — were
pooled into one pseudo-vendor, and their ten *cross*-vendor pairs were counted as
**same-vendor**.

It flattered the conclusion it was used for. Corrected, same-vendor is median 5 / p90 9 under D
and median 3 / p90 8 under P, against different-vendor 5/14 and 5/18. So the published claim
that there is **"no house political position detectable at the median"** is withdrawn: it holds
under the commitment instruction and is false under the placebo, where within-vendor is
genuinely tighter (median 3 against 5) and the tail gap is wide (8 against 18). Vendors cluster
*more* than the bug allowed. The table row reading "local, 2024 generation" as though it were a
house is gone.

**Withdrawn with it: the "2.5× to 5×" between-model ratios.** The numerator was a
modal-vs-modal distance and the denominator a run-vs-run distance — two statistics with
different noise floors, so the quotient has no interpretation. The like-for-like denominator is
the modal's own sampling error, which is *smaller*, so the underlying conclusion survives and
strengthens. `floor_resolution.py` printed those ratios for a further two commits after the
document was corrected, which is how a retraction comes undone: the prose was fixed and the
tool that generates the number was not.

### 10. A band drawn partly out of measurement noise — corrected 2026-09-07

The intervention-budget chart's whole argument is that an intervention must beat the spread
between two off-the-shelf models. That band took its upper bound from a between-model p90 that
included the ten cells `data/modal-noise.json` flags as having an unstable modal — one of which
bootstraps to p90 27 on its own.

Excluding them: p90 **14 → 9** under D and **18 → 14** under P. The band is median 4 to p90 14,
published as 5 to 18, so roughly a third of its width was the estimator. Every intervention
still lands inside it, so the chart's conclusion survives a narrower band.

### 11. The per-model verdict used the wrong null — corrected 2026-09-07

`model_cards.py` asks whether a model's largest measured effect can carry a claim. Two rules
were wrong before the third was right:

| rule | verdict | why it was wrong |
|---|---|---|
| effect vs the model's WORST within-cell pair | 29 of 30 "failed" | an extreme value is not a null |
| effect vs the p90 of its run-vs-run spread | 8 of 30 "carried" | modal-vs-modal effect against a run-vs-run null, and the max of up to three contrasts uncorrected |
| exact permutation on its own runs, Bonferroni | **1 of 30 carries** | the null is built from the same statistic as the effect |

The middle rule was not merely loose, it was **inverted on the case the card exists to catch**:
`grok-4.6` "carried" on an A→D effect of 14 and comes out at **p = 1.0** under permutation,
because its runs are bimodal enough that shuffling reproduces 14 routinely. Only 2 of its 8
survive at all.

The multiplicity correction does almost all the remaining work — 5 models reach p < 0.05 on
their best contrast, 1 survives correcting for having tested up to three — and that is reported
rather than buried. A `no` verdict means "not resolvable at this n", not "no effect": the
permutation null on a five-run modal is coarse, and perfect separation at n=4 gives p = 0.486,
because a 3-1 reshuffle still flips the modal.

### 12. The model-class split did not measure the axis it named — corrected 2026-09-07

**Published:** 2026-09-07. **Corrected:** the same day, by the author.

The split that carries §3's central finding was published with its two sides headed **"2026
frontier API"** and **"2024-generation open-weight"**. The test in the code is `"/" in model`
— hosted against local. It asserts an open-versus-closed axis this study does not test, and
gets it backwards: **12 of the 20 hosted models ARE open weights** served by someone else
(DeepSeek V4, Qwen3.8-Max, GLM-5.x, Kimi K2.5/K2.6/K3, Mistral Medium), all 2025–26 releases.
Only 8 of the 20 are closed.

Three properties move together across that line and this corpus cannot separate them: serving
path, vintage, and quantisation. So **"newer models are more order-stable" is consistent with
these rows and not established by them** — Q4 quantisation of a 7B model is an equally good
explanation, and the requantisation floor is p90 6, the same order of magnitude as the gap
being explained. The Röttger-predicted generational reading is a conjecture here, not a finding.

The measurement that separates them is cheap and now possible: 2026-generation open weights run
*locally* at Q4 put a 2026 model on the local side of the split.

**A second fault in the same table.** Its manipulation column was published with the frontier
cell holding the *pooled* figure and the local cell holding a number copied from a script
docstring that had measured it on a different subset. A two-by-two is a claim that its four
cells are commensurable; those four were not. `floor_conditions_wave_by_class()` computes the
per-class manipulation now, on the same cells and in the same units as the order split, and the
table is generated rather than typed.

### 13. The public README was the least-gated surface in the project — corrected 2026-09-07

Not a claim about models, and it belongs here anyway: it is the mechanism behind several
entries above.

An audit of the README against the run data found **seven hand-typed numbers stale in a single
paragraph** — 36 models where there were 42, eight decliners where there were 14, "39 refusals
in 499 runs" against 148 in 1076 — plus a same-version p90 stated as 12 nineteen lines below a
generated table printing 11, a detection limit given as 16 where `power.py` computes 13, and a
sentence saying a nuisance floor "has not been collected" directly beneath the table reporting
it.

Every one of those numbers was **already gated on the website surface**. `--check-release`
covered *two* phrases on the repository whose entire purpose is that a stranger can check the
claims. Worse, the paragraph asserted its own figures were generated, which is precisely what
stopped anyone checking them.

Fourteen numbers are gated there now, the class-split table is generated, and six scripts the
v2 headline claims depend on — absent from the mirror entirely — are present, so the claims can
be recomputed here rather than taken on trust. Regenerating the estimator floor from this
repository's independently scrubbed runs reproduces the private cache byte for byte, which is
the reproducibility claim demonstrated instead of asserted.

### 14. The order floor pooled two temperatures — corrected 2026-09-07

**Published:** from 2026-09-04 (when the same defect was fixed for a different factor).
**Corrected:** 2026-09-07.

The presentation-order floor's row reads "same model, same condition, item order only". Its
cell key was `(model, condition, shuffle_seed)` plus a template filter — and **temperature was
never in it**. So **28 of 186 canonical-order cells pooled temperature-0 and temperature-0.7
runs**, and for those models the canonical modal was a majority vote across two temperatures.

**This is the third time that key has failed open, on a different factor each time, and the
function's own docstring predicted it.** On 2026-09-04, ten instruction templates all hashed to
the canonical cell and 107 non-T01 runs made a modal a vote across paraphrases; the fix was to
filter templates. The note written at the time said: *"An include list fails open on new
directories; a read-everything default fails open on new FACTORS."* Then the next new factor
walked in. Fixing the factor that just broke something is not the same as fixing the class of
defect, and this file now contains two entries proving it.

What makes the scale legible is that the contaminating runs **contributed nothing**. Every
shuffled-order sheet in this floor is condition A at temperature 0 — the one-sitting order arm
is condition D, because A is 28.2% invalid on that panel — so at temperature 0.7 there are no
shuffled sheets to pair against. The temp-0.7 canonical runs could only ever dilute a modal
they could not contribute a pair to.

Measured before and after, because "the fix is safe" is a claim:

| | pairs | median | p90 | max | endpoint p90 |
|---|---:|---:|---:|---:|---:|
| as published, temperature ignored | 84 | 3 | **11** | 22–23 | 10 |
| temperature part of the key | 84 | 3 | **11** | **24** | **9** |

Identical pair count, identical median, **identical p90** — so the headline figure the paper
and the detection limits rest on is unaffected. What moved is the max, which is exactly the
statistic a diluted modal would be expected to move, and it moved *up*: the pooling was
suppressing the true worst case, not inflating it. Four surfaces quoted the old max and are
updated (the research page, two dispatches, and the paper).

**A side effect worth recording.** The private tree and the public mirror had disagreed by one
on this max, because the private tree holds the 2026-09-07 ablation wave whose stock arm ran at
temperature 0.7 and was landing in canonical cells. With temperature in the key the two trees
produce **byte-identical floor tables**. The parity is now structural rather than a coincidence
of which collections each tree happens to hold — which is the better fix, and it was reached by
asking why the two disagreed instead of copying data across to make them agree.

---

## How to read this file

If a number in the README, the writeup or the run data disagrees with something you have seen
quoted elsewhere, this file is the first place to look. If a claim you can find in the git
history is not listed here and you think it should be,
[open an issue](https://github.com/gorrie/bias-study/issues) — a missing entry is itself a
defect of the kind this document exists to record.
