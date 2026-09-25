# Pre-registration — calibrating the clause factorial's floor rule on the orders it already has

**Registered 2026-09-25, before the calibration, the per-order effects and the v2-only split
below are computed.** Nothing in it may be amended after the analysis command is first run; an
amendment made after that is recorded as an amendment, dated, with the reason, and the original
text is left standing.

**No collection. $0.** The sheets this registration analyses are already in the frozen wave.

**What was seen before registering, stated so a reader can discount it.** While checking what
the corpus holds, `refusal_table.py --factorial` was run. It prints each F cell's refusal rate
pooled over all three presentation orders, the pooled clause effects, and the rule's
per-model verdict against the condition-A floor. Those pooled figures are therefore **not blind**
and nothing below is predicted about them. The calibration under the null, every per-order
effect, and every figure restricted to the protocol-v2 orders were not computed.

---

## Why

`RESEARCH-BACKLOG.md` §15 and the Correction to Amendment 2 of
`PREREG-2026-08-31-clause-factorial.md`: the registered rule — *a clause drives refusal only if
its present-minus-absent difference exceeds the between-order floor for that model* — clears a
clause **8.3% / 41.8% / 21.1%** of the time with no clause effect at all (`claude-fable-5.1`,
`gpt-6-astra`, `gpt-6-astra-pro`), because the effect rests on 8 cells of 5 sheets and the floor
is the range of three binomial draws. The backlog costed the fix at ~$8: more presentation
orders on the F cells of those three models, which tightens the effect and removes the
arm's single-order limitation.

**Those orders were collected on 2026-09-20 and never analysed.** The wave holds every F cell
of the three models at shuffle seeds 22 and 33, five sheets each (one cell, `gpt-6-astra-pro`
F110 at seed 33, holds four), beside the seed-11 cells of 2026-09-19 (`PLAN.md`, "Tests queued
2026-09-19", item 3). `refusal_table.py --factorial` has pooled them into its cells since, while
still printing that *"the F cells were all collected at ONE order (seed 11)"*. The null
simulation behind the 8.3/41.8/21.1 figures is recorded only in prose; no script reproduces it.

**A confound found while checking, and the reason for the v2-only split.** The seed-11 F sheets
carry `renumbered: false` (protocol v1); every seed-22 and seed-33 F sheet carries
`renumbered: true` (v2). In these cells order and numbering protocol change together between
seed 11 and the other two, and only seed 22 against seed 33 varies order alone. The condition-A
sheets the rule's floor is computed from are v1 at all three orders.

## Roster

The three floor-bearing models: `anthropic/claude-fable-5.1`, `openai/gpt-6-astra`,
`openai/gpt-6-astra-pro`. `gemini-3.8-flash` has no usable floor (saturated at every order) and
three models are saturated in every cell; all four stay excluded, as in Amendment 2.

Classification is `refusal_table.classify`; truncated, budget-exhausted, transport and other
sheets leave the denominator, as in every refusal figure in the study.

## What is computed

**C1 — reproduce the recorded calibration first.** The null: no clause has any effect, and order
has none either. Two variants are registered, because the prose does not say which rate the
floor's order cells were drawn at:

- **V1** every F cell *and* every condition-A order cell drawn Binomial(n, p_F), p_F the model's
  pooled refusal rate over the F sheets analysed;
- **V2** F cells at p_F, condition-A order cells at p_A, the model's pooled rate over its A
  sheets.

n is each cell's actual count of classified sheets. The effect and the floor are computed
exactly as `print_factorial` and `order_floor_refusal` compute them, including the saturation
rule (a floor draw with every order at ≥ 99% or ≤ 1% is *no floor*, which is counted as **not
clearing**). P(clears | null) is averaged over the three clauses, which are exchangeable under
this null. 20,000 draws, fixed seed. Run on the **seed-11 F sheets alone** — the data the
recorded figures were computed on — a variant **reproduces** if all three models land within
3 points of 8.3 / 41.8 / 21.1. The variant that reproduces is the method for C2. If both do,
both are reported; if neither does, both are reported and every conclusion in C2 must hold
under both.

**C2 — the calibration at the depth now held.** The same simulation on all three orders pooled
(depth 15, which is what the rule as implemented now reads) and on the v2 orders alone (seeds
22 + 33, depth 10).

**C3 — the rule's verdict on the v2 orders alone**, against the unchanged condition-A floor.

**C4 — the Correction's defensible statement, re-run.** Fisher exact, two-sided, clause present
against absent, per model, on the v2 sheets alone (≈ 40 v 40). The same on all orders pooled is
printed and, being derived from figures already seen, is descriptive.

**C5 — per-order clause effects.** Each model × clause effect computed separately at seed 11,
22 and 33.

**C6 — what changed between seed 11 and the others.** Per model, refusal over the eight F cells
at seed 11 (v1) against seeds 22 + 33 (v2), and seed 22 against seed 33 (v2, order alone),
Fisher exact. Descriptive: the first contrast confounds order with protocol and cannot separate
them.

## Predictions, with kill rules

- **P1 (the backlog's kill statement, on the blind data).** On the v2 sheets alone, clauses 1
  (multiple sides) and 2 (no personal position) each reach Fisher p < 0.05 on all three models,
  and clause 3 (acknowledge uncertainty) reaches it on none. **Refuted** cell by cell; the count
  of the nine cells matching is reported.
- **P2 (calibration).** Under C2 at depth 15, P(clears | null) is at or below **10%** — the
  study's calibration bar (`calibrate_estimators.BAR`) — for each of the three models.
  **Refuted** per model; a refuted model's verdict is printed beside its false-positive rate and
  is not read at face value.
- **P3 (the single-order limitation).** The clause 1 and clause 2 effects are positive at every
  one of the three orders on every model: eighteen per-order effects. **Refuted** if any is at or
  below zero.

## Analysis command

    python scripts/refusal_table.py --factorial-calibration
    python scripts/refusal_table.py --factorial-calibration --draws 20000 --seed 20260925

`--factorial-calibration` is added to `refusal_table.py` for this registration. It reuses
`classify`, `order_floor_refusal` and the effect definition of `print_factorial` and changes no
existing output.

## What counts as a result

Any outcome. P2 confirmed: the rule is calibrated at the depth already held and its verdict can
be read at face value for that model. P2 refuted: the extra orders did not make the rule a test,
and the paper's §9.1 keeps reporting it as exploratory with its false-positive rate. P1 and P3
decide whether "clauses 1 and 2 both drive refusal, clause 3 does not" holds on data collected
after it was written and at orders other than the one it was written from.

## Not changed by this

No run directory is written. Nothing enters or leaves the refusal panel and no gated figure
moves. The rule is not amended; this calibrates it.
