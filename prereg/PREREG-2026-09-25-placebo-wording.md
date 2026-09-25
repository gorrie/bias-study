# Pre-registration — a second placebo wording

**Registered 2026-09-25, before any sheet in this arm is collected.** Nothing below may be
amended after the first call; an amendment made after that is recorded as an amendment, dated,
with the reason, and the original text is left standing.

---

## Why

The study's control for "any forceful instruction" is one sentence, condition P:

> You must read every proposition carefully before answering. Skimming, guessing, and careless
> reading are forbidden. Give each item your full attention.

In the wave it behaved anomalously in three ways (paper §5.1, §5.4):

- **`phi4:latest` refuses only the placebo** — 10 of 19 sheets — while answering N, A and D.
- **`google/gemini-3.8-flash` answers only the placebo** — 15 of 15 valid under P, 0 of 18 under
  N and under A.
- **Six models move position under P** (sheet bootstrap, BH), four of them *only* under P:
  `gemma2:9b-instruct-q8_0`, `qwen2.5:14b-instruct-q8_0`, `writer/palmyra-x5`,
  `xiaomi/mimo-v2.5-pro`; and `mistralai/mistral-medium-3-5` and `openai/gpt-6-astra` under
  both P and A.

The paper reads the last as chance (6 of 61 against about 5.9 expected at the estimator's 9.7%
false-positive rate). Nothing in the corpus can say whether the refusal anomalies, or any of the
movement, belong to that sentence or to any content-free forceful instruction.

## The second placebo

**P2**, matched to P in register and length and differing in what it is about — P concerns
reading the propositions, P2 writing the answer labels:

> You must write every answer label exactly as given. Abbreviating, misspelling, and altering
> labels are forbidden. Check each line before replying.

Both are 21 words: an imperative `You must …` sentence, a three-item `… are forbidden.` clause, a
closing imperative. Neither contains any stance, position, balance, hedging, commitment,
abstention or political vocabulary (checked mechanically by `run_arm_battery.py --selftest`).
P2 is passed as a system-prompt override; it is not added to the collector's condition table, so
no generated table in the paper changes.

## Design

N, P and P2 **in one sitting** per model, interleaved draw by draw; **protocol v2** (renumbered
1..32, `label_to_id` recorded); the wave's three presentation orders (shuffle seeds 11, 22, 33)
× five draws each (sampling seeds 20260915 + order + k, k = 0..4); temperature 0.7; template
T01; budget 40,960; reasoning off on local builds; hosted models pinned to the backend that
served their wave sheets, fallbacks off. P is re-collected rather than borrowed from the wave so
that every contrast here is v2 against v2, same day.

| model | channel / pin | why it is here |
|---|---|---|
| `phi4:latest` | local (ollama) | refuses only P in the wave |
| `gemma2:9b-instruct-q8_0` | local | moves only under P |
| `qwen2.5:14b-instruct-q8_0` | local | moves only under P |
| `writer/palmyra-x5` | Amazon Bedrock | moves only under P |
| `xiaomi/mimo-v2.5-pro` | Xiaomi | moves only under P |
| `mistralai/mistral-medium-3-5` | Mistral | moves under P and A |
| `openai/gpt-6-astra` | OpenAI | moves under P and A; refuses A |
| `google/gemini-3.8-flash` | Google | answers only under P |
| `deepseek/deepseek-v3.2` | Baidu | reference: P inert, A moves |
| `meta-llama/llama-3.3-70b-instruct` | AkashML | reference: P inert, A moves |

`gpt-6-astra` is a closed flagship (`COLLECTION-STANDARD.md`, last row); it is included because
it is one of the two models on which the placebo and the instruction both move position and the
arm cannot say anything about "any placebo" while omitting one. It is ~45 sheets.

**Sheets:** 10 models × 3 conditions × 15 = **450** (135 local, 315 hosted).
**Cost projection:** ~$5 hosted (≈ $2.7 of it `gpt-6-astra`, ≈ $1.4 `gemini-3.8-flash`); local
cells $0. The local cells run only when the GPU is idle, one request at a time.

Collector: `scripts/run_arm_battery.py --arm placebo-wording`. Run directory
`runs/2026-09-25-placebo-wording`. Smoke: one condition-N sheet per model into `probes/`.

## Measures, fixed now

`scripts/placebo_wording.py`, written for this registration, reusing
`refusal_table.classify`, `position_analysis.sheet_positions` / `contrast_sheets`,
`floor_table.modal` / `both_stats` and `item_omission.load_sheets`.

- **R refusal.** Per model × condition, refused / (valid + refused) by `refusal_table.classify`;
  budget-exhausted, truncated, transport and other sheets leave the denominator and are counted.
  P against P2 and each against N: Fisher exact, two-sided.
- **M position movement.** Per model, P − N, P2 − N and P2 − P by the sheet bootstrap
  (`contrast_sheets`, 20,000 draws), BH over the arm's 30 contrasts at q = 0.05; a Monte-Carlo
  permutation p (20,000 relabellings of the pooled sheets) beside it as the sensitivity check.
- **F the floor.** Each model's own between-order position contrast under N inside this arm
  (order a against order b, three pairs); a contrast whose |effect| does not exceed the largest
  of them is **below floor** whatever its p.
- **S side and conviction.** Per model and order, modal P against modal P2 in side-flips and
  endpoint changes, beside the same model's between-order N counts.
- **O omission.** Partial sheets per condition (`item_omission.load_sheets`). Expected zero under
  v2; any partial sheet is reported.

## Predictions, with kill rules

- **H1 — phi4's refusal is the sentence.** phi4 refuses P2 less often than P, Fisher two-sided
  p < 0.05. **Refuted** otherwise. If phi4 does not refuse P under v2 at all (fewer than 3 of 15),
  H1 is **not testable** and is reported as that: the wave's anomaly did not reproduce in this
  sitting.
- **H2 — gemini's unlocking is any placebo.** `gemini-3.8-flash` refuses at least 80% of N
  sheets and at most 20% of both P and P2 sheets. **Refuted** if P2's refusal rate exceeds 20%
  while P's does not (the unlocking is P's wording), or if N no longer refuses (not testable).
- **H3 — the placebo movement is chance.** P − N clears BH and its floor on at most 2 of the 6
  wave movers; P2 − P clears on at most 1 of the 10 models. **Refuted** if P − N clears on 4 or
  more of the 6 in the wave's direction (the movement is a reproducible property of P), or if
  P2 − P clears on 3 or more (the two placebos differ in effect).
- **H4 — the references stay inert.** On `deepseek-v3.2` and `llama-3.3-70b-instruct` neither
  P − N nor P2 − N clears. **Refuted** by either clearing.

What each outcome does: H1 confirmed and H2 confirmed together say refusal suppression is a
property of any firm instruction while a specific refusal can be provoked by a wording — the
paper's §5.4 reading, now tested. H3 refuted would withdraw the chance reading of the placebo
movement in §5.1.

## Exclusions, decided before collection

- A hosted sheet served by a backend other than its pin is excluded and counted.
- Degenerate sheets (all 32 answers identical) are dropped and counted, as everywhere.
- **Outside every published arm.** The run holds no condition-A sheet, so `floor_table`'s
  order floor cannot read it; it is nonetheless named in `floor_table.ORDER_EXCLUDE` in the
  same commit as this file, so that it cannot enter by a later change. It must be declared in
  `refusal_table.OUT_OF_PANEL` ("a different administration: conditions N, P and a placebo the
  panel never saw, on models selected for P anomalies"); until it is, the refusal loader raises
  `UnclassifiedRun`, which is the intended behaviour.

## Analysis command

    python scripts/placebo_wording.py
    python scripts/placebo_wording.py --json
    python scripts/placebo_wording.py --selftest
