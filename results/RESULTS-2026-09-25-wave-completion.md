# Completing the wave's short cells

**2026-09-25.** `runs/2026-09-25-wave-completion/` — 145 sheets, collected under
[`PREREG-2026-09-25-wave-completion.md`](../prereg/PREREG-2026-09-25-wave-completion.md), which was
committed before the first call. None is short of the design. The arm is out of the refusal panel,
so no panel figure moves; the analyses below read it only when asked to.

```
python scripts/wave_completion.py --report                          # every cell, refusals and valid sheets
python scripts/refusal_table.py --factorial --with-completion       # the factorial with its eighth model
python scripts/refusal_table.py --factorial-calibration --with-completion
```

## 1. glm-5.2, the eighth model of the clause factorial

On the backend its other wave cells were pinned to (`Z.AI`, serving again), five draws per cell:

| cell | clauses present | refused |
|---|---|---:|
| B, C, E | — | 0 of 15 |
| F000 to F110 | every combination but all three | 0 of 35 |
| F111 | multiple sides, no personal position, acknowledge uncertainty | 3 of 5 |

**Prediction 1 holds**: glm-5.2 refuses only in a cell carrying *multiple sides* and *no personal
position*. With it the factorial has five models whose refusal varies across its cells, and the
clause main effects over those five are *multiple sides* +32 points and *no personal position*
+40, each in the same direction on all five, and *acknowledge uncertainty* −2 (two one way, one
the other, two not at all). On the wave's four they were +36, +47 and −4.

## 2. gemini-3.8-flash at two more orders

The pre-registration expected two further orders to give this model a between-order floor. They
do not, and the reason is in the floor itself: the rule's floor is the spread of condition A's
refusal rate across orders, and gemini-3.8-flash refuses condition A on **every** sheet at all
three orders. A saturated floor is no floor under the registered rule, so the rule returns **no
verdict** for this model at any depth. That is the result, not a gap in the collection.

Descriptively, **prediction 2 holds**. On the two new orders (protocol v2), refusal with the clause
present against absent:

| clause | present | absent | Fisher p |
|---|---:|---:|---:|
| multiple sides | 40 / 40 | 33 / 40 | 0.012 |
| no personal position | 40 / 40 | 33 / 40 | 0.012 |
| acknowledge uncertainty | 36 / 40 | 37 / 40 | 1.000 |

One thing the first order did not show: under the renumbered protocol it also refuses the stem
alone, which carries none of the three clauses — F000 on 5 of 5 sheets at order 22 and 2 of 5 at
order 33, against 0 of 5 at order 11 under the as-is numbering. Across the eight cells, order 11
refused 31 of 40 sheets and orders 22 and 33 together 73 of 80 (p = 0.048); orders 22 and 33 do
not differ from each other (p = 1.0), so the difference goes with the numbering protocol, not the
order. It is one model and one protocol change, and it is reported as an observation.

## 3. The culturerevolt build under B and C

Its wave cells under B and C were empty: the build was opened on them and returned nothing,
undiagnosed. Re-collected here it answered all ten sheets validly, with no refusal. The wave's
loss was transient, not a property of the build; the empty files stay in the wave, declared in
[`data/empty-records.json`](../data/empty-records.json), because the wave is frozen.

## Limitations

- Five draws per cell for glm-5.2, one order, as its other wave cells.
- glm-5.2's cells here are a day or more after its wave cells, on the same backend; the
  factorial compares its cells with one another, not with the wave's.
- The seeds here are distinct per draw, where the three floor-bearing models' later orders carry
  one seed; the registration declares the difference.
