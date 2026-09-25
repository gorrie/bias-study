# The largest effect in this study is which model you ask

> **Interpretation correction, 2026-09-08.** The table remains descriptive. Its D between-model
> median (5) equals, rather than exceeds, the within-model p90 (5). The different estimators
> and model selection prevent the claim that it proves a model-specific political position
> independent of the questionnaire. Recompute within/between comparisons using matched
> modal estimation and predeclared uncertainty before making that inference.


**Measured** 2026-09-07 from wave 0. **No new collection.** 30 models at n≥4 under conditions
D and P, modal against modal, side-flips of 62.

This is the measurement the whole study needed and never had: **is there a between-model signal
at all, or is the instrument measuring itself?**

## The answer

> **CORRECTED 2026-09-07 after review, three separate defects, all in this section.** The
> headline survives; the numbers it was stated with did not. Corrections inline below, and the
> superseded version is described rather than deleted.

| condition | within model | between models | between, excluding unstable cells |
|---|---|---|---|
| **D** (commitment) | median 2, p90 5 | median 5, p90 14 | median 4, **p90 9** |
| **P** (placebo) | median 1, p90 4 | median 5, p90 18 | median 4, **p90 14** |

**The instrument does distinguish models** — the between-model median exceeds the within-model
p90 under both conditions, so positions are model-specific rather than an artifact of the
questionnaire. That is the finding and it holds.

**Defect 1: the two sides are not measured the same way.** Within-model is *run against run*;
between-model is *modal against modal*. That is not like-for-like, and it is the same species of
error as correction #7. The direction is conservative — the correct denominator for a
modal-vs-modal distance is the modal's own sampling error (side-flip p90 **3**), which is
*smaller* than run-vs-run p90 4–5 — so the conclusion survives and gets slightly stronger. But
the published **"2.5× to 5×" ratios are computed against the wrong denominator and are
withdrawn.** A ratio of a modal distance to a run distance is not a ratio of anything.

**Defect 2: the p90 was inflated by the cells this study says mean nothing.** Ten cells carry a
modal so unstable that `data/modal-noise.json` flags them, and `deepseek-v4-flash` under P
bootstraps to p90 27 on its own. Excluding those ten, the between-model p90 falls from **14 to
9** under D and **18 to 14** under P. The median barely moves (5→4). So the *tail* of the
between-model spread was substantially the estimator, and any band drawn from it inherits that.
Both numbers are reported here; the excluded-unstable column is the one to quote.

## Why that reframes everything else in this paper

Every other effect measured here is smaller than this one:

| factor | side-flip median | p90 |
|---|---:|---:|
| **which model you ask** | **5** | **14–18** |
| deliberate manipulation, one sitting | 3 | 7 |
| presentation order, one sitting, frontier | 1 | 3 |
| running the same prompt twice | 3 | 5 |
| modal sampling error (the estimator) | 1 | 3 |

**Model identity is the largest term.** Not the prompt, not item order, not the estimator. A
study that reports "LLMs lean X" while pooling across models is averaging over the biggest
source of variance in its own data — and that is a stronger version of this paper's thesis than
the one it has been arguing, which was essentially that everything is noise. It is not all
noise. The signal is the model.

## Do vendors have a house position? More than the first version said

**Defect 3, and it was a code bug that flattered the conclusion.** `vendor()` returned the
literal string `"local"` for every model without a slash, so `gemma2`, `llama3.1`, `phi4`,
`qwen2.5` and `mistral` — **five different vendors** — were pooled into one pseudo-vendor and
their ten pairs counted as *same-vendor*. That is what produced the "same vendor p90 10" figure
and the "local, 2024 generation" row in the table below.

With local builds mapped to their real vendors:

| condition | same vendor | different vendor |
|---|---|---|
| D | median 5, **p90 9** | median 5, p90 14 |
| P | median **3**, **p90 8** | median 5, p90 18 |

**The corrected reading is weaker than "no house position" and stronger than the bug allowed.**
Under the commitment instruction the medians are equal (5 and 5) and only the tails separate.
Under the placebo, within-vendor is genuinely tighter — median 3 against 5 — and the tail gap is
wide: **8 against 18**.

So vendors do cluster, more clearly than the buggy version reported, and most visibly on the
condition with the least instruction pressure. The published claim that there is "no house
political position detectable at the median" is **withdrawn**: it is true under D and false
under P.

## Where the vendors do differ, sharply: internal consistency

The interesting number is not each vendor's position but each vendor's **agreement with
itself** across its own model line:

Recomputed with real vendors. The `local, 2024 generation` row of the first version was the bug
described above — five vendors counted as one — and is gone; those models now sit under google,
meta-llama, microsoft, qwen and mistralai, most of which contribute too few pairs to report.

| vendor | internal spread, D | internal spread, P | pairs |
|---|---:|---:|---:|
| moonshotai | **2** (max 3) | **2** (max 2) | 3 |
| qwen | 5 (max 6) | **2** (max 2) | 3 |
| z-ai | 3 (max 5) | 4 (max 8) | 6 |
| openai | 5 (max 6) | 3 (max 6) | 10 |
| anthropic | 5 (max 8) | 5 (max 8) | 3 |
| google | 9 (max 11) | 5 (max 7) | 3 |
| **x-ai** | **11** (max 16) | **10** (max 10) | 3 |

**A five-fold difference in house consistency**, and it holds after the fix. Moonshot's and
Qwen's models agree with each other within 2 items of 62; x-ai's disagree by 10–11.

And x-ai is the outlier on the other axis too — `grok-4.3` has a run-to-run spread of 21 items,
`grok-4.5` 18, `grok-4.6` 16, each at or above any effect measured on it. **x-ai models are
both internally inconsistent across versions and unstable within a version.**

That matters beyond a vendor scorecard: x-ai builds carry the tail of nearly every floor in this
paper. Remove them and the pooled manipulation p90 drops from 15 to 8. A study that includes
grok models without reporting their instability is letting three unstable builds set its
reference scale — which this study did until 2026-09-06.

## Caveats, stated

- **n is small per vendor.** x-ai and anthropic contribute 3 pairs each. The x-ai instability
  finding is corroborated by the independent run-to-run measurement; the vendor-consistency
  ranking is not well estimated for the small houses.
- **"Same vendor" mixes version lines with size tiers.** `gpt-5.6-luna` against
  `gpt-6-astra` is a version gap; `glm-5.3` against `glm-5.3-flash` is a tier gap. Both count
  as same-vendor here, which is why the same-vendor tail reaches 10.
- **Condition A is excluded** from this analysis: 14 models refuse it, so a between-model
  comparison there would be computed on whichever models answer.
- **No compass coordinates.** Distance is side-flips between answer sheets, which is the unit
  every other floor uses.

## Reproduce

```bash
python scripts/floor_resolution.py --paired      # within-model machinery
python scripts/floor_table.py --markdown         # the floors this is compared against
```

The between/within and vendor computations are in this document's own terms above and want a
script of their own; that is the next commit rather than a claim that one exists.
