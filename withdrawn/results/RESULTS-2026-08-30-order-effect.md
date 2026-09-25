# Presentation order moves more than any manipulation we have tested

> **WORKING NOTES.** Not for publication yet. `STATUS.md` is authoritative. Four models,
> all 2024-vintage open weights. A frontier replication is running and will decide whether
> this is a property of the instrument or of small old models.

## The measurement

Same model, same condition (A), temperature 0 with a fixed sampling seed, identical items
with identical ids. **The only thing that differs between cells is the order the propositions
were printed in.** Four presentation orders: the canonical 1–62, plus three seeded shuffles.

Pairwise disagreement, in items answered on the opposite side:

| model | vendor | worst pair | all pairs |
|---|---|---:|---|
| llama3.1-8B | Meta | **24 / 62** | 24, 12, 17, 14, 13, 7 |
| phi4-14B | Microsoft | 11 / 62 | 5, 5, 10, 6, 11, 5 |
| qwen2.5-14B | Alibaba | 11 / 62 | 11, 7, 8 |
| gemma2-9B | Google | 5 / 62 | 5, 5, 4 |

## Why it matters more than anything else here

Every effect this project has measured, set against reordering the same questions:

| intervention | items flipped |
|---|---:|
| pressure conditions B/C/D vs forced balance | 0–6 |
| placebo instruction | 0–3 |
| requantising the weights Q4→Q8 | 2–10 |
| ablating the refusal direction (matched arms) | 0–12 |
| **presentation order alone** | **4–24** |

**Order dominates.** On llama3.1 it moves twice what the largest ablation moved. On every
model tested it is at or above the band we have been treating as signal.

The direct consequence for our own work: **any result from a fixed-order administration is
confounded with order**, and until 2026-08-30 every run this project ever did used the
canonical order. That includes the pressure conditions, the placebo comparison, the weight
rung, and the quantisation null. None of them is *wrong* — order was held constant, so
between-condition comparisons remain internally valid — but none of them can claim the
measured position is a property of the model rather than of the questionnaire as printed.

The consequence for the field is larger, and it is not ours to assert on four old models:
Dominguez-Olmedo et al. (arXiv:2306.07951, 43 models, NeurIPS 2024) argued exactly this and
were largely ignored by the compass-on-LLM literature. This is a second instrument agreeing
with them.

## The discrepancy that has to be resolved before any of it is said out loud

**The comparison project ran an ordering experiment and found the opposite.** aipolcom report
108 whole-questionnaire runs on ordering and describe the systematic effects as negligible —
only one model-axis comparison surviving multiple-testing correction, at −0.31 social units.

Two candidate explanations, and they point in very different directions:

1. **Model vintage and size.** Their set is 2026 frontier models. Ours is four 2024-vintage
   open-weight models of 8–14B. Kamal (arXiv:2506.22493) and Röttger (ACL 2024) both find
   small open models markedly more prompt-brittle. If order sensitivity is a small-model
   property, our number describes obsolete models and theirs describes the ones anyone uses.
2. **Metric.** They measure movement of a two-dimensional coordinate; we count items answered
   on the opposite side. A coordinate can be stable while many items churn underneath it, if
   the flips cancel. **These two results are not necessarily in conflict at all** — and if
   both are right, that is itself the interesting finding: *the aggregate is stable while the
   answers are not.*

Explanation 2 is testable directly from data already in hand and costs nothing. **It was
tested, and it is half right — which is more interesting than either explanation alone.**

If flips cancel, the aggregate stays put while individual answers churn. Comparing mean flips
against the spread in each model's overall agree-rate across orders:

| model | mean flips | agree-rate spread across orders |
|---|---:|---|
| gemma2-9B | 4.7 | **1.6 pts** (39–40%) — flips cancel |
| qwen2.5-14B | 8.7 | 6.5 pts (35–42%) — mostly cancel |
| phi4-14B | 7.0 | 11.3 pts (35–47%) — partly |
| llama3.1-8B | 14.5 | **22.6 pts** (55–77%) — **do not cancel at all** |

So on gemma2 and qwen2.5 the churn is genuinely invisible to a summary statistic, exactly as
a coordinate-based ordering experiment would report. **On llama3.1 it is not: reordering the
same questionnaire moves the model's overall agreement rate by 22 points, from 55% to 77%.**
That is the summary itself moving, not churn underneath a stable summary.

Two things follow. First, "order effects are negligible" and "order effects are large" can
both be true reports of the same phenomenon measured at different levels of aggregation, and
which one you get depends on the model. Second, **a coordinate-level ordering control is not
sufficient** — it can pass while the answer set underneath is unstable, and only an item-level
check catches that.

Worth noting separately: llama3.1 is also the most agreeable model in the set at 55–77%
agree-rate, and acquiescence interacting with presentation order is a documented effect in
human survey methodology. The mirrored ratchet battery measures acquiescence directly and
would test that link; the compass cannot.

## Status

**Not a finding.** Four models, one vendor-family each, all 2024-vintage, one condition, one
run per order. What it is: a large effect, cleanly isolated, that outranks everything else
measured here and that has a live disagreement with the only comparable published result.

A nine-vendor 2026 frontier sweep is running. If order effects are small there, this is a
result about obsolete models and the honest headline is "small open models are unusable for
this instrument." If order effects are large there, it is a result about the instrument, and
about every fixed-order study that used it.
