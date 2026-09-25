# The estimator had no denominator, and the comparison inverts by model generation

**Measured** 2026-09-06, `scripts/floor_resolution.py`.
**Two defects in the comparison this project had been making, both structural.**
**Neither needed new data** — both are re-analyses of wave 0 and the order collection.

## 1. The modal has its own sampling error, and nothing had measured it

Every row in the floor table pairs two **modal** answer sheets: the per-item majority across a
cell's runs. A modal is a statistic. Draw five more runs from the same cell and it moves — and
until today nobody had asked how far.

Bootstrap: resample a cell's runs with replacement twice, take the modal of each, count the
side-flips between two modals of the **same cell under the same condition**. 2000 resamples, 110
cells at n≥4. Everything that differs differs because the modal moved.

**Median 1, p90 3, max 30.**

That is the floor under the floors, and it is now a row in the table (`modal sampling error`),
cached to `data/modal-noise.json` because it costs 400 × 110 modal computations and
`all_floors()` is read by four gates and the chart.

**Small enough that the real effects clear it — and not small enough to ignore.** The
one-sitting order floor on frontier models is p90 3. That is this number exactly. **That row is
not measuring item order; it is measuring the estimator.**

**Ten cells are far worse than the pooled figure suggests**, with modal p90 ≥ 7:

| cell | n | modal median | modal p90 | modal max |
|---|---:|---:|---:|---:|
| `deepseek-v4-flash-0731` P | 5 | 1 | **27** | 30 |
| `grok-4.5` D | 5 | 2 | **15** | 18 |
| `grok-4.3` D | 5 | 4 | **12** | 21 |
| `kimi-k2.5` A | 5 | 1 | **9** | 29 |
| `grok-4.5` P | 5 | 2 | **9** | 13 |

These are the bimodal cells — the ones whose runs land in two separated clusters, so the
majority sheet reports whichever cluster the sampler favoured. **No modal-based measurement of
them means anything**, which is the general form of the `grok-4.5` problem that `CORRECTIONS`
§7 records as a one-off.

## 2. Split by model generation and the comparison inverts

§2 of the paper argues that the pooled order row is a net aggregate concealing two populations,
and calls splitting it the most important line in the paper. The comparison against the
manipulation then pooled it anyway.

The two arms are also different pools — 25 models against 29, 24 in common — so comparing their
p90s lets composition masquerade as effect. Restricted to the 24 models measured in **both**:

| | models | order med / p90 | manipulation med / p90 | order larger on |
|---|---:|---|---|---|
| frontier API, 2026 | 20 | 1 / **3** | 2.5 / **5** | 4 of 20 |
| local open-weight, 2024 | 4 | 11 / **12** | 4 / **8** | 4 of 4 |

**Paired within each model**: median difference **−1 item**, 95% CI [−2, +0.5], sign test over
the 22 models that differ **p = 0.29**. Order larger on 8, manipulation larger on 14, tied on 2.

**Pooled, order looked larger (10 vs 7). Within models, the manipulation is larger on 14 of
24.** The pooled comparison was a net aggregate concealing gross movement between two
populations with opposite orderings — this paper's own charge against five other studies,
committed in its own headline, twice in one day.

The five models that drag the pooled order figure up:

| model | order | manipulation | class |
|---|---:|---:|---|
| `grok-4.5` | 18 | 2 | frontier — **and its modal is unstable at p90 15** |
| `gemma2:latest` | 12 | 5 | 2024 open-weight |
| `llama3.1:8b` | 12 | 8 | 2024 open-weight |
| `grok-4.3` | 11 | 12 | frontier — modal unstable at p90 12 |
| `qwen2.5:14b` | 10 | 1 | 2024 open-weight |

Three are 2024-generation local builds. The two frontier entries are the two models whose
modals the bootstrap flags as unreliable. **Every large order value in this corpus is either an
old model or an unstable estimate.**

## What the study now claims

Not "the nuisance factor is bigger". Not "the manipulation is bigger". By generation:

- **On 2026 frontier models, presentation order is not measurable on this instrument** — p90 3,
  equal to the modal's own sampling error.
- **On those models the deliberate manipulation is small but real** — median 2.5, p90 5, larger
  than item order on 16 of 20.
- **On 2024-generation open-weight models item order dominates** — p90 12 against 8, on 4 of 4.
  This is the population most of this literature was built on, and Röttger predicted the split
  in 2024.

So: **the answer depends on which generation you measure, the effect sizes are small enough that
the estimator matters, and a study that pools the two populations cannot tell you which factor
moved its result.** That last sentence is the paper's thesis, and it now applies to the paper.

## What this does not settle

- **n=4 in the local class.** The 2024-generation arm rests on four models. The direction is
  unambiguous (4 of 4) and the magnitude is not well estimated.
- **The bimodal cells are excluded from nothing.** They are still in every pooled row. Deciding
  whether a cell whose modal is unstable at p90 27 belongs in a floor at all is an open
  question, and the conservative reading — leave it in, disclose it — is what is done here.
- **A modal is still the wrong summary for a bimodal cell.** The right fix is probably to report
  the cell's two modes rather than a majority sheet, which is a different instrument.

## Reproduce

```bash
python scripts/floor_resolution.py --modal-noise    # the estimator's own spread
python scripts/floor_resolution.py --paired         # within-model, 24 models
python scripts/floor_resolution.py --write          # refresh data/modal-noise.json
python scripts/floor_table.py --markdown            # both class rows and the noise row
```
