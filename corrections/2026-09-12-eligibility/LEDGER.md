# Correction ledger — DATA-EMPTY-SCORES-002

Generated 2026-09-12 on the M5. `historical` = the readers as published; `strict` =
`STUDY_ELIGIBILITY=strict`, excluding records whose response text was empty but which
nonetheless carry a score. **Originals untouched** — this directory sits beside them, per
the acceptance criterion that a correction is never applied on top of its own evidence.

| run | records | → | excluded | significant | not-distinguishable | row(s) that vanish |
|---|---:|---:|---:|:---:|:---:|---|
| `2026-05-25-full` | 780 | 747 | 33 | 5 | 8 | — |
| `2026-05-25` | 260 | 260 | 0 | 2 | 9 | — |
| `2026-05-26-augmentation` | 420 | 357 | 63 | 2 | 4 → 3 | `openai/gpt-5` |
| `2026-05-26-cn-expansion` | 181 | 113 | 68 | 0 | 3 | — |
| `2026-05-26-timeseries` | 720 | 660 | 60 | 9 | 3 | — |
| `2026-05-26-unmask-gradient` | 450 | 320 | 130 | 2 | 1 → 0 | `openai/gpt-5` |
| `2026-05-26-variance` | 1200 | 1099 | 101 | 5 | 7 → 6 | `openai/gpt-5` |
| `2026-05-27-abliteration-controls` | 60 | 60 | 0 | 0 | 3 | — |
| `2026-05-27-abliteration-gemma2` | 40 | 40 | 0 | 0 | 2 | — |
| `2026-05-27-abliteration` | 160 | 160 | 0 | 0 | 8 | — |
| `2026-05-27-g0dm0d3` | 60 | 60 | 0 | 0 | 0 | — |
| `2026-05-27-ood` | 160 | 149 | 11 | 1 | 9 → 8 | `z-ai/glm-4.7` |
| `2026-05-27-paraphrase` | 360 | 360 | 0 | 2 | 4 | — |
| `2026-05-27-reversed-premise` | 200 | 200 | 0 | 3 | 2 | — |

**466 records excluded in total** — exactly the 466 inventoried under
DATA-EMPTY-SCORES-001 for the primary corpus, which is an independent check that this
rule reproduces the accepted correction rather than inventing its own.

## The headline: not one significance verdict flips

The `significant` column is unchanged in every run. No confidence interval that excluded
zero now includes it, and none that included zero now excludes it. **Every published
finding survives the correction.** That is a result and it is stated plainly, because
'unchanged' is evidence: the defect was real and was not load-bearing for the headline.

## What does change, and it is worth more than the headline

In four runs the `not-distinguishable` count drops by one, and in every case the cause is
the same: **a model row disappears entirely**, because every one of its records was a
score assigned to a blank string. Not a verdict that flipped — a row that was never a
measurement being removed from the table.

| run | row removed | what it used to say |
|---|---|---|
| `2026-05-26-augmentation` | `openai/gpt-5` | n=30, -0.17 [-0.43, +0.07], not distinguishable |
| `2026-05-26-unmask-gradient` | `openai/gpt-5` | n=10, -0.03 [-0.23, +0.20], not distinguishable |
| `2026-05-26-variance` | `openai/gpt-5` | n=10, +0.04 [-0.32, +0.42], not distinguishable |
| `2026-05-27-ood` | `z-ai/glm-4.7` | n=8, +0.12 [-0.50, +0.75], not distinguishable |

**`openai/gpt-5` was present in three runs entirely on the strength of judged blanks.**
It contributed 287 of the primary corpus's 561 empty responses and 286 of them carried a
score. Those rows read as null results — a model measured and found not to move — when
what actually happened is that the model returned nothing and the judges scored the
nothing. A null you did not measure is not a null.

A fifth row is not removed but is transformed: **`z-ai/glm-4.7` in `2026-05-25-full`**
collapses from n=29 to n=3 (-0.14 [-0.41, +0.10] → +0.00 [0, 0]). Same verdict, but at
n=3 the row no longer impersonates a measurement.

## Inter-judge agreement

740 → 715 items; exact 0.824 → 0.827; unanimous 0.700 → 0.710; mean |difference| 0.239 →
0.236. These land on the corrected figures already recorded under DATA-EMPTY-SCORES-001.

## Runs with nothing to correct

`2026-05-25`, all three abliteration runs plus `-controls`, `-g0dm0d3`, `-paraphrase` and
`-reversed-premise` exclude zero records and produce byte-identical output. **The
weight rung and every control arm are untouched by this defect.**

## What this ledger does NOT yet cover

- The alternate `scored-*` judge methods (81 further scored-empty records) and the
  cross-method contamination delta computed from them. That comparison is the study's
  instrument for judge contamination and the same blank strings were scored 40/35/6/0/0
  times across the five methods, so it must be re-run before the delta is defended.
- `drift_report`, `drift_timeseries` and the chart builders, not yet migrated.
- Flipping the default. The rule stays opt-in until the above is done and this ledger is
  read; the flip is itself a dated correction.

---

## Cross-method contamination, re-run under the rule (2026-09-12)

`cross_method_report.py` is now wired to the same rule. This loader matters more than the
others: the cross-method comparison **is** the study's instrument for judge contamination, and
the same blank strings were scored 40 / 35 / 6 / 0 / 0 times by the five alternate methods. Left
in, it measures the judges' *willingness to score nothing* and reports it as a difference in how
they score something.

Regenerated into `cross-method-strict/` and diffed against the published artifacts, which were
restored untouched. Six of fourteen runs' `contamination-delta.json` change. Most changes are
bootstrap-boundary shifts of a hundredth. **One is not.**

| run | model | \|Δ\| was | now | CI was | CI now | n pairs |
|---|---|---:|---:|---|---|---|
| `2026-05-25-full` | `z-ai/glm-4.7` | **0.129** | **0.038** | [0.032, 0.258] | [0.0, 0.115] | 31 → 26 |
| `2026-05-27-ood` | `z-ai/glm-4.7` | 0.333 | 0.0 | [0.0, 1.0] | [0.0, 0.0] | 6 → 5 |

### What this means, stated carefully because it favours us

The pre-registered robustness criterion is **median |Δ vs ULTRAPLINIAN-4| ≤ 0.10**: clear it and
the original consensus is robust to judge-alignment contamination. In the main run,
`z-ai/glm-4.7` was the model **failing** that bound at 0.129, with a confidence interval
**excluding zero** — a positive contamination signal, the single strongest piece of evidence
against the study's own robustness claim.

Under the eligibility rule it falls to 0.038, comfortably under the bound, with a CI that
includes zero. The contamination signal was **judges scoring blank strings and disagreeing
about what score a blank string deserves** — which is exactly what the audit predicted when it
found the same 50 blanks scored 40 times by one method and 0 by two others.

**This correction makes the study's central claim stronger, which is precisely why it should be
treated with more suspicion than a correction that hurt us, not less.** Three guards on it:

1. The rule was written and tested against the primary corpus *before* the cross-method report
   was re-run, and it reproduces the independently-recorded -001 agreement figures exactly
   (715 / 0.827 / 0.710 / 0.236). It was not tuned to this result.
2. It is one model in two runs. Every other model's delta is unchanged or moves by ≤ 0.02.
3. The direction is mechanically forced: removing records on which judges disagreed *about
   nothing* can only reduce measured disagreement. The honest framing is not "contamination is
   lower than we thought" but **"one model's contamination figure was never a measurement"** —
   the same sentence as the vanished `openai/gpt-5` rows, arriving in a different table.

Whoever writes this up should state the before-and-after, not just the after. A robustness
criterion that is only cleared after a correction is a weaker claim than one cleared outright,
and the reader is entitled to see which one this is.

---

## Aggregates regenerated out-of-place, and a reproducibility defect found on the way

`aggregate.py` now takes `--out DIR`, so a correction can be generated beside its evidence
instead of on top of it. Before this, comparing before-and-after meant running the script,
copying the output, and `git checkout`-ing the originals back -- which works exactly until
someone forgets the third step. All 14 runs regenerated under the rule into
`aggregates-strict/`; not one published artifact touched.

**The defect found while doing it.** `write_csv` opened with `newline=""` and let
`csv.DictWriter` use its default `\r\n`, so every aggregate was written CRLF while every
committed aggregate is LF. Running the documented pipeline on *unchanged* data therefore
produced a modified working tree, and the README's claim that "every committed run under
`data/` reproduces its aggregated CSVs via `scripts/aggregate.py`" was false byte-for-byte.

That is worse than untidy. The one signal that says *your correction moved something* was
buried in a diff that always fired. Fixed with `lineterminator="\n"`; verified across five
runs that re-running now leaves `git status` clean.

### Per-model rows whose n changes under the rule

| run | model | attempted | scored | delta A→B |
|---|---|---|---|---|
| `2026-05-25-full` | `z-ai/glm-4.7` | 30 → 13 | 29 → 3 | -0.138 → 0 |
| `2026-05-26-augmentation` | `deepseek/deepseek-r1` | 30 → 27 | 29 → 26 | 0.138 → 0.154 |
| `2026-05-26-augmentation` | `openai/gpt-5` | **row removed** | | |
| `2026-05-26-cn-expansion` | `moonshotai/kimi-k2.6` | 30 → 16 | 30 → 11 | 0.167 → 0.364 |
| `2026-05-26-cn-expansion` | `z-ai/glm-4.7` | 30 → 7 | 30 → 4 | 0.267 → -0.25 |
| `2026-05-26-timeseries` | `moonshotai/kimi-k2` | 30 → 29 | 28 → 27 | 0.464 → 0.444 |
| `2026-05-26-timeseries` | `moonshotai/kimi-k2-thinking` | 30 → 28 | 30 → 25 | 0.5 → 0.48 |
| `2026-05-26-timeseries` | `qwen/qwen-2.5-72b-instruct` | 30 → 22 | 25 → 12 | 0.08 → 0.083 |
| `2026-05-26-timeseries` | `z-ai/glm-4.5` | 30 → 25 | 30 → 24 | 0.567 → 0.333 |
| `2026-05-26-timeseries` | `z-ai/glm-4.6` | 30 → 15 | 30 → 8 | -0.067 → 0.125 |
| `2026-05-26-unmask-gradient` | `openai/gpt-5` | 30 → 3 | 9 → 0 | 0 →  |
| `2026-05-26-variance` | `deepseek/deepseek-r1` | 50 → 50 | 9 → 8 | 0.111 → 0.125 |
| `2026-05-26-variance` | `google/gemini-3.1-pro-preview` | 50 → 50 | 7 → 3 | 0.429 → 0.333 |
| `2026-05-26-variance` | `openai/gpt-5` | 50 → 2 | 10 → 0 | 0.2 →  |
| `2026-05-27-ood` | `z-ai/glm-4.7` | 8 → 2 | 8 → 1 | 0.125 → 0 |

---

## The book citations, checked (CLAIM-PUBLIC-SCOPE-001, first pass)

A correction that stops at the repository is half a correction. `the-ratchet` ch00 prints the
judge-independence result in prose, so it was recomputed from the data both ways.

**As published — every figure verifies exactly:**

| the book says | measured |
|---|---|
| "re-scored roughly seventeen hundred records each" | 1,652 – 1,743 ✓ |
| "agreed … in eighty-four to ninety-one percent of cases" | 84.3% – 90.6% ✓ |
| "the label-inversion test cleared at ninety-one" | reversed-rubric **90.6%** ✓ |
| "the abliterated open-weight judge … cleared at eighty-seven" | abliterated-gemma **86.8%** ✓ |

**Under the eligibility rule, agreement rises — and only rises:**

| method | as published | under the rule | n |
|---|---:|---:|---|
| adversarial-pair | 84.3% | 84.3% | 1652 → 1652 |
| abliterated-gemma | 86.8% | **87.4%** | 1717 → 1688 |
| grok-solo | 87.7% | 87.9% | 1690 → 1684 |
| blind-condition | 88.5% | 88.5% | 1713 → 1713 |
| reversed-rubric | 90.6% | **91.7%** | 1743 → 1703 |

The two unchanged methods are exactly the two that scored **zero** empty responses. The three
that move are the three that scored some. The direction is not a coincidence and it is not a
finding about judges: **a disagreement about a blank string is not a disagreement about
content**, so removing them raises measured agreement mechanically. Same mechanism as the
cross-method contamination result, in a different statistic.

### Disposition for the book

ch00's prose survives as written, with one edge: the range's **upper bound rounds to
ninety-two, not ninety-one**. "Eighty-four to ninety-one percent" becomes "eighty-four to
ninety-two" if the rule becomes the default. The two named figures — ninety-one for the
label inversion, eighty-seven for the abliterated judge — still round correctly at 91.7% and
87.4%.

**No rewrite is needed now**, because the rule is opt-in and the published numbers are the
as-published column. If the default flips, one word in ch00 changes. Recorded here so that
decision carries its consequence with it rather than being discovered later by a reader.

---

## the-ratchet ch22: the GPT-5 delta is not a measurement

The sharpest result of the book sweep, and the one that changes a printed sentence.

ch22 says:

> GPT-5 did not move in any direction we can defend: its delta sits at **−0.17** with a
> confidence interval straddling zero, and it is **the noisiest model in the entire study**,
> run-to-run variance roughly double anyone else's.

**93% of GPT-5's records in the primary corpus are empty responses.** 287 of 310. Twenty-three
records carry actual text. The model spent its budget reasoning and returned nothing; the judges
scored the nothing; the aggregates counted the scores.

Traced across every run it appears in:

| run | as published | under the rule |
|---|---|---|
| `2026-05-26-augmentation` | delta **−0.167**, n=30 | **row does not exist** |
| `2026-05-26-unmask-gradient` | delta 0, n=9 | n=0 |
| `2026-05-26-variance` | delta +0.2, n=10 | n=0 |

The **−0.17 the book prints is the augmentation row**, and that row is built entirely on scored
blanks.

Pinned precisely, because "no measurement" is a strong claim and the aggregates alone could be
read as a rounding artifact. Paired A/B observations per run:

| run | published pairs | eligible pairs | eligible records |
|---|---:|---:|---:|
| `augmentation` | 30 | **0** | 0 |
| `unmask-gradient` | 10 | **0** | 18 |
| `variance` | 10 | **0** | 4 |

The model *did* produce text sometimes — 18 eligible records in one run, 4 in another. It never
produced text for **both conditions of the same question**, which is what a delta requires. So
GPT-5 has zero eligible paired observations in every run it appears in, and no delta can be
computed from real responses anywhere in the corpus. The 22 records that carry text are real and
unpaired; the 30 pairs that carry a delta are pairs of blanks.

### This makes the book's argument stronger, not weaker

ch22 already retracts an earlier "reversal" reading of GPT-5 and says so explicitly — *"We
retract the reversal rather than bury it."* That retraction was right, and it was right for a
weaker reason than the true one. The chapter concludes GPT-5 is **indeterminate because its
interval straddles zero**. It is indeterminate because **there was nothing to measure**.

The "noisiest model in the study, variance roughly double anyone else's" observation is the same
fact seen from the other side: **variance among scores assigned to empty strings.** Four judges
handed a blank string do not converge, and they have no reason to — which is exactly what the
cross-method audit found when the same 50 blanks were scored 40 / 35 / 6 / 0 / 0 times by five
methods.

### Disposition

The prose needs one change, and only if the default flips: **−0.17 should not be printed as a
delta.** The honest sentence is that GPT-5 returned empty responses on 93% of its records and
therefore has no defensible delta in either direction — which supports the chapter's existing
conclusion better than the number does.

Recorded rather than edited. The rule is opt-in, the published figure is the as-published
column, and changing a book's printed number is an authorial act.

---

## quiet-autocomplete ch18: the ≤0.1 dissociation claim, now bounded

ch18 rests on the weight-rung dissociation: abliteration *"rewrites ~70% of political wording
(Jaccard 0.23–0.34) but moves institutional-skepticism stance ≤0.1 — refusal and lean
dissociable."* The abliteration runs lose **zero** records to the eligibility rule, so nothing
there is touched by tonight's correction. But the ≤0.1 had never been stated with an interval,
which is the same defect `CLAIM-ABLATION-CAUSAL-001` caught in the forced-choice arm.

Computed paired by question, stock vs abliterated, May judge-scored 1–5 instrument:

| family | pairs | mean Δ | 95% CI |
|---|---:|---:|---|
| deepseek-r1-distill-7b | 10 | +0.100 | [−0.500, +0.700] |
| gemma-2-9b | 10 | 0.000 | [0.000, 0.000] *(degenerate)* |
| llama-3.1-8b | 10 | 0.000 | [0.000, 0.000] *(degenerate)* |
| mistral-7b | 10 | −0.100 | [−0.300, 0.000] |
| qwen2.5-7b | 10 | +0.100 | [0.000, +0.300] |
| **pooled** | **50** | **+0.020** | **[−0.100, +0.140]** |

**The claim holds, and it is now a bound rather than an assertion.** Every per-family point
estimate is ≤0.1 in magnitude, exactly as ch18 says. The pooled estimate is +0.02 with a 95%
interval of **[−0.10, +0.14]** — against this study's own documented noise floor of ±0.5 on the
same scale. A stance effect large enough to matter is excluded.

**Two precisions the prose should carry.**

1. *"No more than a tenth of a point"* describes the **point estimates**. The pooled upper bound
   is **+0.14**, not +0.10. The defensible sentence is "the movement is bounded at about
   ±0.14, and no family's estimate exceeds a tenth of a point" — stronger, because it is a
   bound, and a bound is what an absence claim needs.
2. Two of the five families return **degenerate intervals** — every delta exactly zero, so the
   bootstrap has nothing to resample. They cannot bound anything individually; the pooled
   estimate is what carries the claim. Same artifact as the ablation wave's zero bases, and it
   is why the pooled row matters rather than the per-family table.

### On ch18's "CONFIRMED AND STRENGTHENED" note

The 2026-09-07 note in ch18's source block says the forced-choice wave *confirmed and
strengthened* this, and that *"the prose below is BETTER supported after this collection than
before it."* That is too strong after `CLAIM-ABLATION-CAUSAL-001`. What the wave established is
narrower: `qwen25-14b`'s apparent effect is **build-specific**, two other bases are equivalent to
zero within ±5 side-flips, and the general mechanism claim was withdrawn.

The ≤0.1 figure is a **different instrument** — May, judge-scored, 1–5 — and it stands on its own
evidence, which is the interval above. It is not strengthened by the wave; it is **independently
supported**, which is a better thing to be and should be said that way.
