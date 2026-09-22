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
internal spread is **0.3007 points** — larger than the two smallest of the five published
effects (+0.2333 and +0.3000) — and it is not constant across the arms: gemini-2.5-flash sits at +0.044 under the balance instruction and
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

### 15. Every per-model delta in the variance run was computed from one replicate — corrected 2026-09-14

**Published:** since the run was first aggregated. **Corrected:** 2026-09-14.

`aggregate.py` keyed its accumulator on `(model, question_id)` and then assigned per condition,
so where a cell held several samples **only the last record survived**. The run it aggregates
carries five. Every `mean_delta_AB` in `data/2026-05-26-variance/` was therefore a single draw
wearing the name of a mean, and the tell was visible in the published file the whole time: the
deltas were all multiples of 0.1, which is what a one-sample difference of integers must be.

The same defect was found and fixed in `pipeline_rung.py` first; this is the same bug in the
older, more widely quoted path.

| model | as published | regenerated | note |
|---|---:|---:|---|
| deepseek/deepseek-r1 | +0.10 | **−1.20** | sign reversed |
| x-ai/grok-4.3 | +0.30 | **+0.58** | nearly doubled |
| anthropic/claude-opus-4.7 | +0.50 | **+0.18** | and see below |
| anthropic/claude-opus-4 | +0.10 | +0.02 | |
| qwen/qwen3-235b-a22b-thinking-2507 | +0.30 | 0.00 | and see below |

At the vendor-class level the published gap was **us-closed +0.248 against chinese-open +0.200**,
a difference of +0.048. Regenerated it is **+0.206 against −0.339**, a difference of +0.545 —
an order of magnitude larger, and with the two classes now on opposite sides of zero. The
corrected finding is *stronger* than the one it replaces, which is the uncomfortable kind: a
defect that was suppressing our own result went unexamined longer than one that inflated it.

**The regenerated numbers are not yet publishable either, and the reason is the second half of
this correction.** The eligibility rule now excludes truncated responses, and the exclusion is
severely differential:

| model | questions before | after | lost |
|---|---:|---:|---:|
| anthropic/claude-opus-4.7 | 50 | 5 | 90% |
| qwen/qwen3-235b-a22b-thinking-2507 | 50 | 3 | 94% |
| deepseek/deepseek-r1 | 49 | 28 | 43% |
| openai/gpt-5 | 2 | 0 | 100% |
| everything else | 49–50 | 48–50 | ≤4% |

So opus-4.7's +0.18 rests on four scored questions and qwen3-thinking's 0.00 on one. Excluding a
truncated response is right — it is not an answer — but excluding 90% of one model and 2% of
another **relocates the confound rather than removing it**, because what was excluded is not
missing at random. Restricting to cells with at least eight scored questions moves the class gap
again, to +0.210 against −0.508, and drops two models entirely.

**The same exclusion quietly changed a count elsewhere.** The rung-2 paragraph in the README said
the arm had **eight** intervals, none excluding zero. Enforcing the truncation rule removed Claude
Opus 4.7's two `B-Layered` cells from the eligible set, so two contrasts stopped being computable
and `pipeline_rung.py` has printed **six** ever since while the prose kept saying eight. Corrected
2026-09-14. The direction is unaffected — none of the six excludes zero — but a hand-typed count
sitting beside a generated one is exactly the pairing this project keeps finding stale, and
`key_numbers.py --check-release` is what caught it.

**Disposition.** The published per-model deltas for this run are **withdrawn**. The regenerated
ones are **provisional** and carry their sample counts wherever they are quoted. Neither number
settles the vendor-class question; only re-collection at a token cap that does not truncate can,
and that is what the re-collection plan exists for. The single number that survives both
treatments is the direction of `deepseek-r1`, which is negative under every weighting and was
published positive.

---

### 16. The obfuscation arm applied no obfuscation — corrected 2026-09-14

**Published:** 2026-05-26 (`WRITEUP-2026-05-26.md` §4.3), carried into the README's rung-2 row,
`DEVELOPER.md`, `PREREG-2026-09-13-pipeline-rung.md` and `X-AMMUNITION-DRAFT.md`.
**Withdrawn:** 2026-09-14.

The claim was that rung 2 applies elicitation-layer force as **"STM hedge-strip, Parseltongue
obfuscation, or both layered"**, and that *"only the layered stack moves the needle — STM alone
(3.60) and Parseltongue alone (3.70) are ≈ prompt-B... the practitioner intuition that layered
obfuscation is the potent form."*

**No obfuscation was ever applied.** G0DM0D3's Parseltongue rewrites trigger words from a fixed
list of 53 security and jailbreak terms and returns the text **unchanged** when it finds none.
The instrument is ten neutral policy questions and not one contains a trigger, so the transform
fired on **0 of 240 requests** across both pipeline runs. `B-Parseltongue` was condition B,
collected a second time, under a different label.

Every check the study runs had passed on it: the call succeeded, the text was complete, the
judges scored it, and on Claude Opus the interval excluded zero. The evidence was in every
record from the first run — the collector stores the server's own echo of what it did, and no
analysis had ever read it. `scripts/pipeline_transform_audit.py` is that read; it takes no API
calls.

**What this does to the numbers.**

- `B-Parseltongue vs plain B` is a **null by construction** and therefore the floor every other
  contrast in the arm must clear. On Opus it reads **+0.24 [+0.02, +0.49] and excludes zero**, on
  an arm that received nothing.
- Opus's `B-STM vs plain B` of **+0.37** sits on that floor. Differenced within the run, where
  the baseline run, the date and the proxy path all cancel, STM is **+0.13 [−0.07, +0.36]** on
  Opus and **−0.02** on Grok. **Both span zero. STM does not move either model.** The published
  conclusion about STM was right; it was right by luck.
- A control collected 2026-09-14 (`2026-09-14-g0dm0d3-proxy-control`, plain B through the same
  proxy with every transform off) shows the **proxy path costs +0.06 on Opus and −0.14 on Grok,
  both spanning zero**. So the floor is not the path — it is **cross-sitting drift**, roughly
  +0.18 on Opus between collections a day apart.

**Two further facts about this arm, neither previously recorded.** `STM` is not a prompt
transform: `applySTMPost(response, …)` runs it after generation and deletes *"I think"*,
*"perhaps"*, *"In my opinion"* and eight siblings from the model's reply, which the judges then
score on a rubric where hedging separates a hedged 3 from a committed 4. Measured over all 225
scored pipeline records it removes a **median of 16 characters** from responses averaging ~3,500,
and edited records score *lower* rather than higher — so it does not manufacture the finding. It
is badly differential though, firing on 45 of 60 Opus records against 1 of 60 for Grok, so
`B-STM` is **not the same intervention on the two models**.

**Disposition.** The sentence *"layered obfuscation is the potent form"* is **withdrawn**: no
obfuscation occurred, and B-Layered's distinguishing ingredients are `godmode` (a system prompt
plus temperature +0.1) and `autotune` (adaptive sampling). Every `vs plain B` figure in this arm
is **provisional** pending a same-sitting baseline.

**What survives, and it is the finding that mattered.** `B-Layered minus B-STM` never reads the
baseline run, so it is immune to this confound *and* to the token-budget confound corrected the
same day: **Opus −0.31 [−0.64, −0.01], Grok +0.48 [+0.26, +0.70]** — two models moving in
**opposite directions** under the same intervention. Grok's result cannot be an editing artefact
either: STM touched 1 of its 55 records and removed a single character. Whether the effect
belongs to the instruction or to the sampling change is being collected now
(`B-Godmode` / `B-Autotune`); until then the attribution is open and is stated as open.

Full account: `RESULTS-2026-09-14-rung2-transform-audit.md`. The arms where a treatment was not
administered, or where nothing records that it was, are enumerated in
`studypaths.UNVERIFIED_TREATMENT` — including 220 abliteration records whose `obliteratus_applied`
is derived from whether the string `ablit` appears in the run **label**.

---

### 17. A baseline swap that fixed nothing and broke something — corrected 2026-09-15

**Published:** 2026-09-14, in `CORPUS-MAP-2026-09-14.md` and `pipeline_rung.py`.
**Withdrawn:** 2026-09-15, one day later.

The claim was that the rung-2 baseline had to be replaced because it recorded **no token
budget** while the arm it is differenced against records 4,000 — *"a baseline capped below its
arm measures truncation, not force"* — and that the swap proved the confound real: Opus's
`B-STM vs plain B` moved from +0.12 spanning zero to **+0.37 [+0.13, +0.65]**, and *"three of
eight intervals excluding zero became five of eight."*

**The movement was real. The attribution was wrong.** Two measurements settle it, neither
available until the transform audit (entry 16) existed:

1. **The unrecorded cap never bound.** The original baseline's longest response is **1,295
   tokens**; the replacement's is **1,307**; the arm's is **1,606** against its 4,000 cap. **Not
   one record in either baseline is truncated.** Whatever budget the original ran at, nothing
   came near it, so it cannot have confounded anything.
2. **The replacement was collected two days after the arm.** From `called_at`: the arm ran
   2026-09-13T23 and -09-14T00; the original baseline 2026-09-13T23, *the same sitting*; the
   budget-matched replacement 2026-09-15T02–03.

So an unverifiable cap was traded for a real drift confound.

**What proves it is the arm that cannot have an effect.** Entry 16 established that
`B-Parseltongue` applies no transform to this instrument — 0 of 240 requests. An untreated arm
must measure zero, which makes it a test of the *baseline* rather than of the models:

| `B-Parseltongue vs plain B` | same-sitting baseline | budget-matched, +2 days |
|---|---|---|
| claude-opus-4.7 | **−0.01 [−0.15, +0.13]** | +0.24 [+0.02, +0.49] — *excludes zero* |
| grok-4.3 | +0.09 [−0.06, +0.23] | +0.11 [−0.10, +0.29] |

An interval excluding zero on an arm with no treatment in it is not an effect. It is the
baseline being wrong, measured. **Two of the five intervals reported as excluding zero were
manufactured by drift.**

**Disposition.** `pipeline_rung.py` is back on the same-sitting baseline; the budget-matched run
is kept as `MATCHED_BUDGET_BASELINE_RUN`, being the right control for the token-cap question and
the wrong one for everything else. The corrected count is **3 of 10 intervals excluding zero**,
not 5 of 8. Neither baseline is clean — the honest fix is a same-sitting baseline *with* a
recorded cap, which `2026-09-15-g0dm0d3-decomposition` collects.

**What survives, again unchanged.** `B-Layered minus B-STM` is −0.31 on Opus and +0.48 on Grok
under *both* baselines, because it is within-arm and never touches one. Grok's `B-Layered vs
plain B` is +0.56 against +0.57. This is the third correction in two days that the same contrast
has walked through untouched, which is the argument for preferring a within-arm contrast when one
is available.

**The generalisable rule, now a gate.** An arm known to receive no treatment is the best test of
a baseline you will ever get: whichever baseline drives it closest to zero is the defensible one,
and that is a property of the data rather than an argument about collection parameters.
`tests/test_pipeline_rung.py::test_the_untreated_arm_reads_zero_which_is_how_a_baseline_is_judged`.

---

### 18. "Two models move in opposite directions" — narrowed 2026-09-15

**Published:** 2026-09-14, in `RESULTS-2026-09-13-pipeline-rung-replicate.md` and carried through
entries 16 and 17 above as the claim that survived them.
**Narrowed:** 2026-09-15, one day later, by the arm that was collected to answer a different
question.

The claim was that `B-Layered minus B-STM` reads **−0.31 [−0.64, −0.01]** on Claude Opus 4.7 and
**+0.48 [+0.26, +0.70]** on Grok 4.3 — *"the two models move in opposite directions under the
same intervention"* — and that this was rung 2's result, immune to every confound because it is
within-arm and never reads a baseline run.

**Both numbers are unchanged and still reproduce.** What does not survive is the reading.

Its reference arm is `B-STM`, and **`B-STM` is not an untreated control.** Entry 16 established
that the proxy edits `B-STM`'s scored text after generation — deleting hedging phrases — on **45
of 60** Opus records. A contrast whose reference has been treated is not a measurement of the
other arm alone.

Measured against an arm that received *genuinely nothing* — `B-Proxy`, plain condition B through
the same proxy with every transform explicitly off, collected in the **same sitting** as the
arms it is differenced against:

| claude-opus-4.7 | B-Proxy | B-Godmode | B-Autotune | B-Layered |
|---|---:|---:|---:|---:|
| cell mean | 3.48 | 3.50 | 3.44 | 3.44 |

**Opus is flat under every ingredient of rung 2.** `B-Layered minus B-Proxy` reads −0.04
[−0.34, +0.22]. The negative half of "opposite directions" was a contrast against a treated
reference, not a direction.

**Disposition.** The phrase *"two models move in opposite directions"* is **withdrawn**. The
corrected finding is one-sided and smaller:

> **A forceful system prompt moves Grok 4.3 by about half a point on this rubric and does not
> move Claude Opus 4.7 at all.**

**What the same run also settles, in the study's favour.** The attribution left open by entry 16
is now closed: the effect is the **instruction**, not the sampling change.

| grok-4.3 | effect | 95% interval |
|---|---:|---|
| B-Godmode minus B-Proxy | **+0.45** | [+0.10, +0.78] · excludes 0 |
| B-Autotune minus B-Proxy | −0.08 | [−0.26, +0.09] |
| B-Layered minus B-Proxy | **+0.44** | [+0.07, +0.79] · excludes 0 |

`B-Layered` is `B-Godmode` to within a rounding error, and additivity holds on both models
(residuals −0.02 and +0.06). The sampling hypothesis got the **better-powered** test of the two —
`autotune` is the larger perturbation, temperature 0.825 plus top_p and top_k, against godmode's
bundled +0.1 — and came back null. A bigger sampling change moved nothing; a smaller one carrying
an instruction moved +0.45.

Full account: `RESULTS-2026-09-15-rung2-decomposed.md`. Regressions:
`tests/test_pipeline_decomposition.py`, which fires if Opus ever moves or if the stack drifts
from its instruction arm.

---

### 19. The study's title was a withdrawn finding — withdrawn 2026-09-13, corrected on this surface 2026-09-15

**Published:** 26 May 2026, as the title of the writeup, of this repository, of the
`CITATION.cff` record, of the book's opening "Proof", and of *The Ratchet* chapter 22's "the
finding".
**Withdrawn:** 2026-09-13, in the private `FINDINGS.md` (#13).
**Still asserted publicly until:** 2026-09-15. Two days.

The claim was **"the hedge is the bias signature"**: that a model answering a contested political
question with heavy both-sides hedging is masking a lean, and that hedge density therefore detects
the mask.

Score-3 responses do carry a much higher hedge ratio. But **rubric score 3 *is* "does not
commit"**, and the hedge lexicon measures non-commitment. The finding is the rubric restated in
lexical form — as the writeup's own §3.5 conceded in the same document that led with it.

**Why it outlived its own withdrawal.** `key_numbers.RETRACTED` is the gate that fails a build
when a withdrawn phrase is asserted on a public surface. It held six phrases, all dated
2026-09-04 to 2026-09-06. The five withdrawals of 2026-09-13 were never added, so
`--check-release` kept exiting 0 over a README that asserted every one of them. A retraction gate
that is not updated when a retraction happens reports the absence of the claims it already knows
about — which is the vacuous-pass failure this project has now found in four separate tools.

**What replaced it.** The repository is now *Same Version, Different Answers*: two models
differing only in snapshot date, size or serving mode disagree on a median of 5 of 62
propositions, p90 11, and of twelve audited studies not one reports that null as a distribution.
That claim survives every control this study owns and is the one no other study reports at all.

`CITATION.cff` still carries the old title as of this entry, because it is copied verbatim into
the Zenodo record and is permanent once a release fires. It is changed before any tag, not after.

---

### 20. The vendor-class point estimates — withdrawn 2026-09-13

**Published:** 26 May 2026. **Withdrawn:** 2026-09-13 (`FINDINGS.md` #16). **Corrected here:**
2026-09-15.

The claim was a class differential in point estimates — "us-closed mean Δ +0.572" against an
open-weight mean of ≈ 0 — with the direction said to "replicate under N=5 averaging".

Both halves fail, for the same reason. The script computing them keyed its records on
`(model, question_id)` — which is not unique when a cell holds five replicates — so it **kept one
of five** and silently discarded the rest. Nothing was averaged; the phrase "replicates under N=5
averaging" describes an operation that did not occur. Corrected, the split **flips sign** on a
19-pair remainder that had lost half its records.

**The direction survives**: US-closed frontier models unmask more than open-weight ones. It rests
on **two models**, and it is reported that way now. Withdraw the numbers, keep the direction.

---

### 21. "The mask comes off in proportion to force", and "the lean is in the weights" — withdrawn 2026-09-13

**Published:** 26 May 2026, as the study's spine. **Withdrawn:** 2026-09-13 (`FINDINGS.md` #14,
#15). **Corrected here:** 2026-09-15.

The escalation ladder was presented as one axis with three rungs — prompt, pipeline, weights —
along which force increases and the mask comes off in proportion, *"except where it is bolted in
at the weights, where force does nothing."*

It is not one axis, and the rungs are not in the same units:

- conditions D and E silently carry condition B's user suffix, so their deltas confound three
  changes at once, while condition C has a stronger *user* instruction than either and no system
  prompt;
- **no model is measured on all three rungs**;
- the weight rung was tested only on open models that sit at 3.00 under prompt force too, so
  "force does nothing at the weights" was established where force does nothing at all;
- and a **content-free placebo** — an instruction with no stance content whatsoever — restores
  endpoint answers as much as an explicit must-commit instruction does, so most of what the
  ladder attributed to increasing force is instruction-following.

"The lean is in the weights" fails separately: nothing in the corpus locates a lean anywhere. The
one same-units comparison has the **weight** intervention moving *more* than the prompt one (9
side-flips against 4), and that movement was attributable to which third-party build was
downloaded — see entry 22.

The three rungs are real measurements and are now reported **separately**, which loses no finding.

---

### 22. Grok 3.00 → 5.00, and "abliteration rewrites ~70% of the political wording" — withdrawn and narrowed 2026-09-13

**Published:** 26 May 2026. **Withdrawn / narrowed:** 2026-09-13 (`FINDINGS.md` #17, #11).
**Corrected here:** 2026-09-15.

**The dose-response endpoint.** Grok 4.3 reaching 5.00 across the ten neutral questions was
quoted as the top of the gradient. The condition that produces it instructs *"You are an
opinionated political commentator"* and then asks critic-framed questions. That is **persona
compliance, not a lean measurement**, and placing it at the top of a dose curve treats an identity
instruction as more of the same force. The rest of the gradient stands: 3.00 bare → **3.63** under
"what do you think?", → **4.20** under the layered pipeline, neither assigning an identity.

**The weight-rung dissociation.** The claim was that abliterating the refusal direction from five
open-weight families "rewrites ~70% of the political wording" while moving stance ≤ 0.10,
proving the refusal direction and the institutional lean dissociable.

The text-rewrite half is established on **one family of five**. Run this repository's own
`scripts/abliteration_effect_check.py`: it prints **TEXT CHANGE NOT ESTABLISHED** for
llama-3.1-8b (between-arm Jaccard 0.339) and mistral-7b (0.333), because both sit **inside the
0.303–0.392 band one model produces resampled against itself** — the local runs sample at
temperature 0.7 with no seed, so that "rewrite" is what resampling alone produces. Only qwen2.5-7b
(0.276) is confirmed. DeepSeek-R1-distill has one shared eligible cell; Gemma-2-9B's raw files are
0 bytes.

And where stance did move, **two independent abliterations of the same base disagree 8/9/9 against
0/2/0** — the movement belongs to which GGUF was downloaded, not to abliteration as an operation.
A stance null measured against an unestablished rewrite is uninterpretable in either direction.

---

### 23. "4 of 13 effects survive FDR", and the sycophancy control — corrected 2026-09-15

**Published:** 26 May 2026. **Corrected:** 2026-09-15, by the corpus repair rather than by an
argument.

**FDR survivors: 4 → 5.** DeepSeek V3.2 was reported as "suggestive but not confirmed". It had
**23 of its 30 A/B pairs destroyed by the 800-token cap**; the 2026-09-14 repair returned them and
it now survives Benjamini-Hochberg at p=0.0034. `scripts/robustness_checks.py
2026-09-14-full-spliced` has printed 5/13 since the splice landed, and `selftest_analysis.py` G2
asserts the five-model set — so the repository's own tooling and its README disagreed for a day.
This one is worth stating plainly: a published null was an artifact of a token budget.

**The sycophancy control holds for two models, not five.** A reversed-premise pass was read as
showing all five tested models holding within ≤ 0.40 of their neutral-framing stance, and
therefore as evidence that the unmask measures a genuine institutional lean rather than
agreeableness. On the same control, **GPT-4.1 tracks the frame**: neutral 3.10 against reversed
**2.75**, with 5 of 20 reversed answers scored 2 and none scored 4 — a gap about the size of its
own published effect (+0.43). Claude Opus 4.7 (3.70/3.70) and Grok 4.3 (3.80/3.60) do hold.

The same instrument, on the same items, measures a **position** on two models and
**frame-following** on a third. A single sentence about "the models" hides that, and the control
is now reported per model.

---

### 24. "Its runs are in this repository" — the decomposition arm was never here, corrected 2026-09-16

The rung-2 section of this README asserted that, **as of 2026-09-15, the decomposition run's
"runs are in this repository, so the numbers below recompute here rather than being asserted from
a tree you cannot see."** Immediately below that sentence it published `B-Godmode` **+0.45
[+0.10, +0.78]** and `B-Autotune` **−0.08 [−0.26, +0.09]**.

`2026-09-15-g0dm0d3-decomposition` has never been in this repository. In a clone
`scripts/pipeline_decomposition.py` exits **2 — not applicable**, zero `B-Godmode` or
`B-Autotune` records are present under `data/` or `runs/`, and the two tests covering the arm
SKIP. So the one paragraph in the README that made a promise about reproducibility was the one
paragraph making a claim a reader could not check, and it made that promise *about itself*.

Both figures are **asserted, not reproducible from the shipped data**, and the README now says
so in the same breath as it states them. Neither number is withdrawn — nothing here challenges
them; they are held in the private study tree and the honest description of their status is
"you are taking our word for this one." Whether the run is exported to this repository is a
publication decision and is not settled by this entry.

`tests/test_decomposition_claim_matches_reality.py` now ties the two together: if the run is
absent the README must carry the disclaimer, and if the run is ever exported the disclaimer must
go. A sentence about what ships cannot drift from what ships when a test reads both.

### 25. Judge scores on responses that were empty — corrected 2026-09-08, ledgered 2026-09-12

**Published:** from the May collection onward, in every reader over the judge-scored corpus.
**Corrected:** 2026-09-08. **Per-run ledger:** 2026-09-12.

The primary `data/*/scored/*.jsonl` corpus holds 5,051 records. Of the 561 unusable responses
in it, **466 carry classifier scores although their response text is empty and `ok` is true** —
a judge scoring a blank. Every aggregate, confidence interval and paired estimate computed
before the correction included them.

`score.py` now skips empty and whitespace-only responses before calling any judge, and the
CI, FDR and paired readers share one eligibility loader that discloses its exclusions on
stderr and keeps substantive refusals as their own category rather than folding them in with
blanks. A run with no eligible A/B pairs returns nonzero instead of reporting on nothing.
Historical scores are **not** rewritten: the corrected views sit beside the originals, because
a correction applied on top of its own evidence destroys the evidence.

**What moved, and it is less than the defect's size suggests.** On the main run 33 empty
records drop out; five models still have bootstrap intervals excluding zero and four still
survive FDR. Judge agreement moves from 0.824 to 0.827 exact-pairwise over 715 contributing
items rather than 740. Across all fourteen judge-scored runs — 466 records excluded, the same
466 the 2026-09-08 audit inventoried independently — **not one significance verdict flips.**
No interval that excluded zero now includes it, and none that included zero now excludes it.
That "unchanged" is itself the result: the defect was real and was not load-bearing.

**What it did break.** The GLM result on the main run now rests on **three** eligible A/B
pairs, which cannot establish equivalence or the absence of bias, and four `not-distinguishable`
rows vanish outright when their model loses its last eligible cell — `openai/gpt-5` in the
augmentation, unmask-gradient and variance runs, `z-ai/glm-4.7` in the OOD run. Missingness may
be systematic; excluding it removes a scoring artefact, not selection bias.

**The receipts ship.** `results/response-quality-2026-09-08.json` names every affected file,
line, question, model, condition and source SHA-256.
`corrections/2026-09-12-eligibility/LEDGER.md` carries the per-run table with historical and
strict columns side by side. `scripts/audit_response_quality.py --check` **intentionally exits
1** while historical empty records retain their scores — that inventory is a correction record,
not a request to delete or rescore original evidence.

This entry exists because the narrative correction that first reported the defect,
`CORRECTIONS-2026-09-08.md`, was deleted from this repository on 2026-09-22 in a pass removing
the retired questionnaire — which it was not about. That file had already been published, so
the deletion would have removed a public correction record; it was restored the same day with a
banner saying so. The ledger and the inventory it pointed at had survived either way, unlinked
from anything, and this file claims to list every withdrawn or narrowed claim. It does now.

### 26. Thirteen vendor "version arcs", ten of which were not arcs — corrected 2026-09-12

**Published:** `data/_aggregated/vendor_arcs.md`, "Per-vendor intra-family version arcs".
**Corrected:** 2026-09-12, into `corrections/2026-09-12-vendor-arc/`.

`drift_timeseries.py` computed each family's arc as `deltas[-1] - deltas[0]` and printed it as
"delta from oldest to newest". `deltas` was a list of measurement **rows**, and a row is a
`(version, run)` pair. On any family measured more than once at a single version, the statistic
subtracted one arbitrary run of a model from another arbitrary run of **the same model** and
published the difference as version drift.

The headings said so in plain sight and nobody read them as a count of rows: `xai-grok`
"8 versions" is `grok-4.3` measured eight times. **Four families had exactly one version and
every one of them published an arc direction** — `xai-grok`, `mistral`, `meta-llama` and
`microsoft-phi`, joined by `openai-gpt` at two versions with six measurements of `4.1`.

**Withdrawn:** five families' arcs, which do not exist — the corrected reader prints **NO ARC**
and refuses to report a direction on one version. `moonshot-kimi` reverses from a published
**decreasing (−0.30)** to **stable (−0.08)**; that direction is withdrawn.

**Narrowed:** the corrected reader also prints the within-version spread, the run-to-run
variation an arc has to clear to mean anything, and says so when the arc is narrower than its
own noise. `google-gemini`'s increasing 0.35 sits inside a 0.62 spread and is noise-dominated.
`xai-grok` is the clean illustration of the original defect: one version whose repeat
measurements span 0.90, while arcs of ±0.2 were being labelled directional — a threshold an
order of magnitude below the noise, with nothing in the output saying so.

**What survives: three of thirteen.** `claude-opus` (0.47 against 0.40), `qwen` (0.35 against
0.13) and `zhipuai-glm` (0.40 against 0.25) remain directional claims. The rest were stable
already or were never arcs.

The correction was generated with `--out` into its own directory.
`data/_aggregated/vendor_arcs.md` is **unchanged** and remains the record of what was
published; no run record was touched and no model was called.

### 27. "The repaired corpora are not in this repository yet" — false for a week, corrected 2026-09-22

**Committed:** 2026-09-14 (`7e027a3`), as the opening banner of `CORPUS-MAP-2026-09-14.md`.
**False from:** 2026-09-15. **Corrected:** 2026-09-22.

**This one never reached a reader, and the entry says so rather than letting the file imply
otherwise.** `origin/main` is at 2026-09-13; `7e027a3` and the repair export `4d734dd` are both
in the unpushed history, so no published version of this repository has ever carried the
banner. It is recorded here because the defect is identical whether or not the push happened —
the record of what this repository asserted is the git history, not the push log — and because
an entry that quietly omits its own reach is the kind of shading this file exists to refuse.

The banner told readers that the 2026-09-14 repair was "pending export", that the runs named
below it "will not resolve for you", and — in bold — that **"every original run in this
repository is the damaged version."** It instructed anyone deriving a May figure to treat it as
computed on a corpus missing about a third of its responses.

The export landed on **2026-09-15** in `4d734dd`. Thirteen `2026-09-14-recollect-*` repair runs
and ten `*-spliced` derived corpora have been in this tree since, `2026-09-14-full-spliced`
among them — the repaired main run, thirteen scored files, exactly matching
`2026-05-25-full`. The map was edited the following day, 2026-09-16, and the banner survived
the edit. For a week this document discounted figures the repository was already shipping
the repair for.

**What was wrong was the availability claim, not the damage.** The May runs really are the
damaged version and they really do remain here unmodified, because a repair written over its
own evidence destroys the evidence. The corrected banner says which run to read — the
`-spliced` view for figures, the bare May run when you mean to see what was originally
collected — instead of telling readers the fix is somewhere they cannot reach.

**Genuinely absent, and separately disclosed:** the three rung-2 and decomposition runs named
in the map are not in this tree. That is entry 24, gated by
`tests/test_decomposition_claim_matches_reality.py`.

This is the defect the map itself is about — a stated corpus that is not the corpus on disk —
appearing in the banner of the document written to prevent it. A disclosure is a claim, and it
expires like any other.

---


## How to read this file

If a number in the README, the writeup or the run data disagrees with something you have seen
quoted elsewhere, this file is the first place to look. If a claim you can find in the git
history is not listed here and you think it should be,
[open an issue](https://github.com/gorrie/bias-study/issues) — a missing entry is itself a
defect of the kind this document exists to record.

Where a correction has its own worked ledger — the per-run table, the historical and corrected
columns side by side — it is in [`corrections/`](corrections/), one directory per defect, and
the entry above names it. Those directories are generated **beside** the artifact they correct
and never over it, so what was published stays readable next to what replaced it. Entries 25
and 26 were added on 2026-09-22 because their ledgers were shipping and nothing in this file
pointed at them, which made this file's own opening claim false.

Every numbered entry above sits under **The retracted claims**. This heading used to sit
*before* entry 19, which filed six corrections — the study's own title among them — under a
section called "How to read this file". A reader scanning the headings for withdrawn claims
would have stopped at entry 18.
