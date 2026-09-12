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
