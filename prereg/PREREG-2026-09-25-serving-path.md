# Pre-registration — access tier as serving path: one model, two pinned backends

**Registered 2026-09-25, before any sheet in this arm is collected.** Nothing below may be
amended after the first call; an amendment made after that is recorded as an amendment, dated,
with the reason, and the original text is left standing.

---

## Why

"Access tiers of one model are indistinguishable" was withdrawn on 2026-09-17
(`CORRECTIONS-2026-09-17-power.md`): its observations were counts out of the retired
questionnaire's 62 judged against detection limits computed on the 32-item battery, and its
two tiers (API against in-harness agent) differed in system prompt, tooling, sampling and
version resolution at once. `CLAIM-REVIEW-PROTOCOL.md` records that the claim, re-read by
statistic, was true in side-flips and false in endpoint changes, and that it stays withdrawn
as stated.

The access question can be re-measured cleanly as **serving path**: one model id, two backends
OpenRouter routes it to, pinned with fallbacks off, under an identical protocol collected in one
sitting. The study already has one such contrast, on omission only:
`nvidia/nemotron-3.5-lightning` lost 7 of 23 as-is sheets on DeepInfra against 1 of 23 on Phala
(p = 0.0235, `RESULTS-2026-09-21-omission-pinned.md`). Nothing has measured position, side,
conviction or refusal between backends.

## Design

Per model, both backends **interleaved draw by draw in one sitting**; conditions N and A;
**protocol v2** (renumbered); the wave's three presentation orders (shuffle seeds 11, 22, 33) ×
five draws each (sampling seeds 20260915 + order + k, k = 0..4, identical on both backends);
temperature 0.7; template T01; one completion budget per model, identical on both backends.

**Roster and backends.** The first backend is the one that served the model in the wave (for
nemotron, which is not in the wave, the pinned omission arm's). The second is fixed by a rule
applied to OpenRouter's endpoint list of 2026-09-25, before any sheet: *the cheapest other
endpoint (prompt + completion price) with status 0 and at least 16,384 completion tokens.*
Nemotron's second backend is instead Phala, named by the prior omission contrast rather than by
the rule, and declared as such.

| model | backend 1 | backend 2 | quantisation (listed) | budget |
|---|---|---|---|---:|
| `meta-llama/llama-3.3-70b-instruct` | AkashML (wave) | DeepInfra (rule) | fp8 / fp8 | 16,384 |
| `deepseek/deepseek-v3.2` | Baidu (wave) | GMICloud (rule) | fp8 / fp8 | 40,960 |
| `ibm-granite/granite-4.2-8b` | DeepInfra (wave) | CoreWeave (rule; the only other) | bf16 / bf16 | 40,960 |
| `minimax/minimax-m2.7` | GMICloud (wave) | Novita (rule) | fp8 / fp8 | 40,960 |
| `nvidia/nemotron-3.5-lightning` | DeepInfra (omission arm) | Phala (prior contrast) | bf16 / unlisted | 40,960 |

Llama's budget is DeepInfra's advertised completion ceiling, applied to both backends so neither
is asked for a budget the other would clamp; its sheets use about 170 tokens.

**Sheets:** 5 models × 2 backends × 2 conditions × 15 = **300**.
**Cost projection:** about $1.5 (minimax's reasoning is most of it).

Collector: `scripts/run_arm_battery.py --arm serving-path`. Run directory
`runs/2026-09-25-serving-path`. Smoke: one condition-N sheet per model × backend into `probes/`.

## Measures, fixed now

`scripts/serving_path.py`, written for this registration, reusing `refusal_table.classify`,
`position_analysis.sheet_positions` / `contrast_sheets`, `floor_table.modal` / `both_stats` and
`item_omission.load_sheets`. Per model, per condition:

- **Between backends.** For each order, the modal sheet on backend 1 against the modal on
  backend 2 (five draws each): side-flips and endpoint changes; reported as the mean and the
  maximum over the three orders. Position: backend 2 − backend 1 over all 15 v 15 sheets, sheet
  bootstrap (20,000 draws) with a Monte-Carlo permutation p beside it, BH over the arm's 10
  contrasts.
- **The model's own order floor**, inside the arm: on each backend, modal order a against modal
  order b (three pairs per backend, six per condition) in side-flips and endpoints; and the
  between-order position contrast. The floor for a statistic is the **maximum** of these.
- **Refusal** per backend (`refusal_table.classify`; refused over valid + refused), Fisher exact
  two-sided between backends.
- **Omission** — partial sheets per backend (`item_omission.load_sheets`), Fisher exact
  two-sided.
- **The instruction contrast per backend**, A − N by the sheet bootstrap, and whether the two
  backends' A − N differ by more than the between-order position floor.

A between-backend difference **exceeds the floor** when it is strictly greater than the model's
own floor for that statistic and condition; for position it must also clear BH.

## Predictions, with kill rules

- **H1 — side holds across backends.** Between-backend side-flips (mean over orders) do not
  exceed the model's own between-order side-flip floor, in both conditions, on at least 4 of 5
  models. **Refuted** if 2 or more models exceed it in the same condition.
- **H2 — conviction does not.** Between-backend endpoint changes (mean over orders) exceed the
  model's own between-order endpoint floor in at least one condition on at least 2 of 5 models,
  the pattern claim 8 of `CLAIM-REVIEW-PROTOCOL.md` records for same-version variants.
  **Refuted** if 0 or 1 models do.
- **H3 — position holds.** The between-backend position contrast clears BH and its floor on at
  most 1 of 5 models in each condition. **Refuted** if 2 or more clear in the same condition.
- **H4 — refusal and omission.** No model refuses on either backend under N or A (at most one
  refused sheet per model), and under protocol v2 no backend produces a partial sheet.
  **Refuted** by a model with a refusal difference at Fisher p < 0.05, or by any partial sheet,
  each reported.
- **H5 — the instruction survives the backend.** A − N has the same sign on both backends for
  every model on which it clears BH on either. **Refuted** by a sign reversal.

What each outcome does: H1 and H3 confirmed with H2 confirmed re-measure the withdrawn claim in
its stratified form — backends indistinguishable in side and position, not in conviction —
on data in the instrument's own units. H1 or H3 refuted would make serving path a floor this
paper does not carry, and every unpinned hosted figure a mixture of it.

## Exclusions, decided before collection

- A sheet served by a backend other than its pin is excluded and counted; a backend that stops
  serving the model (three consecutive pinned 404s) leaves its cells short, and the shortfall is
  reported, never filled from another backend.
- Degenerate sheets dropped and counted, as everywhere.
- **Outside every published arm.** The run holds condition-A sheets at T01 and temperature 0.7
  under the wave's three orders, so `floor_table`'s order floor, which reads every run not named
  in `ORDER_EXCLUDE`, would pool them into the wave's cells for `llama-3.3-70b-instruct`,
  `deepseek-v3.2`, `granite-4.2-8b` and `minimax-m2.7`. It is named in
  `floor_table.ORDER_EXCLUDE` in the same commit as this file, before the first sheet. It must be
  declared in `refusal_table.OUT_OF_PANEL` ("one model on two pinned backends, N and A only, a
  serving-path contrast"); until it is, the refusal loader raises `UnclassifiedRun`, which is the
  intended behaviour.

## Analysis command

    python scripts/serving_path.py
    python scripts/serving_path.py --json
    python scripts/serving_path.py --selftest
