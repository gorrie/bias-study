# Access tier as serving path: one model, two pinned backends

**2026-09-25.** `runs/2026-09-25-serving-path`, 5 models × 2 pinned backends × conditions N
and A × the wave's three orders × five draws, protocol v2, both backends interleaved draw by
draw in one sitting. Pre-registered in `PREREG-2026-09-25-serving-path.md` (commit `d8e3181a`).
Every figure below is `scripts/serving_path.py` (20,000 bootstrap draws and 20,000 permutation
relabellings per contrast).

## Collection

Four models were collected in full: 15 valid sheets per backend per condition, except
`deepseek-v3.2` on GMICloud under N (14; one transport failure). **`nvidia/nemotron-3.5-lightning`
could not be compared.** DeepInfra returned an upstream HTTP 429 ("temporarily rate-limited
upstream") on 38 of 39 attempts across the collection and a same-pin retry; it served one valid
sheet (A, order 33). Phala served 13 of 15 per condition. Under the pre-registration a backend
that stops serving leaves its cells short and is never filled from another backend, so nemotron
is reported and excluded: with no order held on both backends there is no matched pair, and with
one sheet there is no floor. The retry on the same pin was stopped once it was plainly not being
served. The motivating contrast of the arm — nemotron on DeepInfra against Phala — is therefore
**not re-measured** here.

No sheet was refused, partial, degenerate or served off its pin, on any backend, in either
condition.

## Between backends, against each model's own order floor

Side-flips and endpoint changes compare the modal sheet (five draws) on one backend with the
modal on the other at the same order, averaged over the three orders; the floor is the largest
between-order difference on either backend in the same condition.

| model | cond | backends | side-flips between (mean / max) | own side floor | endpoints between (mean / max) | own endpoint floor | position b2 − b1 [95%] | own position floor |
|---|---|---|---|---:|---|---:|---|---:|
| `deepseek-v3.2` | N | Baidu / GMICloud | 0 / 0 | 1 | 1.7 / 3 | 7 | +0.008 [−0.085, +0.100] | 0.194 |
| `deepseek-v3.2` | A | Baidu / GMICloud | 1 / 2 | 4 | 0 / 0 | 0 | +0.010 [−0.015, +0.033] | 0.050 |
| `granite-4.2-8b` | N | DeepInfra / CoreWeave | 2 / 3 | 6 | 7.7 / 19 | 19 | +0.069 [−0.096, +0.254] | 0.488 |
| `granite-4.2-8b` | A | DeepInfra / CoreWeave | 4 / 5 | 8 | 0 / 0 | 0 | −0.010 [−0.067, +0.044] | 0.031 |
| `llama-3.3-70b-instruct` | N | AkashML / DeepInfra | 0.7 / 1 | 3 | 0.3 / 1 | 11 | −0.015 [−0.106, +0.077] | 0.319 |
| `llama-3.3-70b-instruct` | A | AkashML / DeepInfra | 0.7 / 1 | 4 | 2.7 / 8 | 8 | −0.073 [−0.138, −0.013] | 0.119 |
| `minimax-m2.7` | N | GMICloud / Novita | 1.7 / 3 | 5 | 0.7 / 2 | 2 | −0.033 [−0.123, +0.035] | 0.131 |
| `minimax-m2.7` | A | GMICloud / Novita | 1 / 2 | 2 | 1.3 / 2 | 3 | +0.027 [−0.037, +0.090] | 0.094 |

**No between-backend difference exceeds the model's own order floor, in any statistic, on any
comparable model, in either condition.** The one position contrast whose interval excludes zero,
`llama-3.3-70b-instruct` under A (−0.073, permutation p = 0.040), fails BH over the arm's eight
contrasts and is below that model's 0.119 between-order spread. Reordering the items moves
these models at least as much as moving them to another data centre does.

## The instruction on each backend

| model | backend 1: A − N [95%] | backend 2: A − N [95%] |
|---|---|---|
| `deepseek-v3.2` | Baidu −0.154 [−0.235, −0.090] | GMICloud −0.152 [−0.219, −0.097] |
| `granite-4.2-8b` | DeepInfra −0.212 [−0.296, −0.135] | CoreWeave −0.292 [−0.465, −0.140] |
| `llama-3.3-70b-instruct` | AkashML −0.102 [−0.188, −0.010] | DeepInfra −0.160 [−0.225, −0.092] |
| `minimax-m2.7` | GMICloud +0.040 [−0.050, +0.117] | Novita +0.100 [+0.042, +0.160] |
| `nemotron-3.5-lightning` | DeepInfra — (no N sheet) | Phala −0.046 [−0.111, +0.026] |

The balance instruction has the same sign on both backends of every model; its size differs
across backends by at most 0.08, inside the intervals. `minimax-m2.7` is the one model on which
the instruction moves position away from the midpoint, on both backends, significantly on one.
That is a property of the model, not of its serving path, and it is noted rather than tested:
the arm registered no prediction about it.

## Verdict against the predictions

| | prediction | result | verdict |
|---|---|---|---|
| H1 | side-flips between backends within the own order floor on ≥ 4 of 5 | 4 of 4 comparable models, both conditions | **confirmed** (on 4; nemotron not comparable) |
| H2 | endpoints between backends exceed the own floor on ≥ 2 of 5 | 0 | **refuted** |
| H3 | position clears BH and floor on ≤ 1 of 5 per condition | 0 in each | **confirmed** |
| H4 | no refusal difference, no partial sheet under v2 | none of either | **confirmed** |
| H5 | A − N keeps its sign across backends | no reversal | **confirmed** |

H2 was the prediction that serving path would behave like the other same-version variants, which
hold side and move conviction (`CLAIM-REVIEW-PROTOCOL.md`, claim 8). It does not: on these four
models the backend moves neither side, nor conviction, nor position beyond what reordering the
items produces. H1 is confirmed on four comparable models rather than five, which meets the
registered threshold of four but leaves no margin.

## What this changes

The withdrawn access-tier claim stays withdrawn as stated. What the arm establishes is narrower
and in the instrument's own units: for four open-weight models on two pinned backends each, under
an identical protocol in one sitting, the serving path is not a floor the paper needs to carry
for side, conviction, position or refusal — it is inside the order floor on every statistic.
Omission is not tested by this arm: under protocol v2 neither backend of any model produced a
partial sheet, as expected, so the nemotron as-is contrast of `RESULTS-2026-09-21-omission-pinned`
(a v1 phenomenon) is neither confirmed nor challenged.

Limits. Four models, all open-weight, all small-to-mid reasoning or non-reasoning builds; the
second backend was chosen by a price rule, and quantisation was the same listed format on both
backends for all four; a pair of backends with different quantisation was not sampled.
The model chosen to carry the arm's motivating contrast was not served.

## Spend and commands

Hosted subject spend, estimated from recorded tokens at listed endpoint prices: about $0.42.

    python scripts/serving_path.py
    python scripts/serving_path.py --json
    python scripts/serving_path.py --selftest
    python scripts/run_arm_battery.py --arm serving-path --plan

`serving_path.py` gained, after collection and before this document, a rule that marks a
model × condition **insufficient** when no order is held on both backends or either backend has
fewer than two orders, and excludes it from the predictions; without it a backend that served
nothing would have counted as "within floor" for H1. The registered measures are otherwise
unchanged. The run is named in `floor_table.ORDER_EXCLUDE` and must be declared in
`refusal_table.OUT_OF_PANEL`. Transport-failure rows (45, 38 of them nemotron on DeepInfra) are
kept in the run as records of what was attempted and are excluded by every reader.
