# Pre-registration: I3 Phase 4, the main forced-choice collection

**Written 2026-09-14, before any Phase 4 call is made.** The predictions are the point. A
prediction that can be adjusted after seeing the number is not a prediction, and the commit
carrying this file is what makes that checkable.

---

## AMENDMENT 2, 2026-09-16 — the instrument, and a collection design that can be read

**Written before any call on the Ratchet battery.** The 167 sheets already on disk were
collected under this design and are covered by it; everything after is too.

### The instrument

This document's body and its first amendment name `data/ratchet-propositions-i3.json` — 60
items, 30 pairs "differing by exactly one inserted not". **That bank is withdrawn.** Its
sentences were written by an assistant session on 2026-09-14 and were never read or signed
off; the sign-off box in `ITEM-READ-2026-09-15-i3-bank.md` is empty, and 372 sheets were
collected against it while the study's own instrument had zero records.

The instrument is **`data/ratchet-battery.json`** — `ratchet-battery`, 32 items in 16
mirrored pairs, authored 2026-08-30, every item carrying `mirror_of` and `frame`. It is
signed: `ITEM-READ-2026-09-16-ratchet-battery.md`, all 16 pairs read and accepted.

Consequences that follow mechanically and are fixed here rather than chosen later:
`power.BOUND` is **32**, not 62. One side-flip is 3.1% of a sheet against 1.6% on the
retired instrument, so **no figure measured on 62 items is comparable in the same units** —
every compass-era floor quoted anywhere must be re-derived or expressed as a fraction.

### The disputed pairs, and the ruling

A review flagged five pairs as admitting agreement with both halves — **1, 3, 9, 15**, with
10 and 13 raised and withdrawn. The author read all sixteen and ruled them sound as written.

That ruling stands and the primary outcomes are computed on all 16 pairs. **Both figures are
reported**: all-16 and the undisputed subset. If they disagree the subset figure is the one
quoted, and a per-pair table ships so a reader can drop any pair. The floors do not depend on
complementarity at all — they are side-flip counts between two sheets of one instrument.

### Strata

The body stratifies by `claim_type`, a field the battery does not carry. Added as a
structural field only — no sentence changes, ids unchanged, so the collected sheets stay
valid. Pairs 11–16 are documented-empirical (US intermediaries, OSA, DSA, Aadhaar, Israel,
China); pair 5 is contested-empirical; the remainder are normative.

### Roster

36 models, up from 31. The five additions — `gpt-5.6-luna-pro`, `-sol-pro`, `-terra-pro`,
`deepseek-v4-flash`, `deepseek-v4-pro` — were taken from the live model list, verified to
return a valid sheet, and added **by coverage rule before collection**: every model that
pairs with a panel member by tier or snapshot at the same version. `glm-5.2:free` was probed,
returned 0 of 32, and is excluded and named rather than silently dropped. Same-version null
pairs: **7 → 24**, from 10 sibling groups.

### Collection design — four passes, not one

| pass | shape | what it is for |
|---|---|---|
| 0 | budget probe, 36 models | the cap is measured on THIS instrument across the WHOLE roster |
| 1 | 36 × N/A/P/D × seeds 11/22/33 | order floor, condition contrasts, same-version null, refusal |
| 2 | `--replicate 4 --conditions D` | replicate floor **and** modal sampling error |
| 3 | re-collect 4 backend-split models | removes the routing confound |
| 4 | 5 local requantisation pairs | requantisation floor + 5 same-version pairs |

**Pass 2 is four extra runs on D at one fixed item order, not two on N and D.** Five runs at
one order is what makes `floor_modal_noise` computable — it requires ≥4 runs per cell and the
wave gives one — and modal noise is the denominator every other floor is judged against. The
cost is no replicate floor on N. Committed here because it is a design choice, not a default.

A replicate sweeps the **sampling** seed at a fixed **shuffle** seed. Without that sweep the
runner reuses one seed and seed-honouring backends return near-identical sheets: a replicate
floor of ~0, which is worse than not measuring it.

### One backend per model

Serving path is a same-version variant this study measures, so it is held fixed across a
model's whole sitting — not per condition. Under the previous per-condition pin
`deepseek-v4-flash` answered A on Reka, D on Together, N on CoreWeave and P on OpenInference,
which confounds its condition contrast with the routing. `collection_check` blocks a model
served by more than one backend.

### Arms that will not compute, declared now

Paraphrase/template (no template variation in this design), elicitation format (the
constrained arm is on the retired instrument), and ablation (out of scope). Naming them here
so their absence is a stated design consequence and not a result.

---

## AMENDMENT, 2026-09-15 — before any Phase 4 call is made

Five changes, all committed before collection. The predictions in the body are **unchanged**;
what changes is the roster, the strata, the presentation order, and two counts that were wrong.

**1. The roster, fixed here by a coverage rule rather than after seeing data.** The body said
"eight models" and named none, which would have meant choosing the roster after Phase 2 output.
It is the **existing 31-model frozen panel**, `data/wave-panel.json`, frozen 2026-09-05 on the
criterion *"present in the corpus under both surviving conditions at freeze time. Coverage,
never outcome."*

Why the whole panel rather than eight: it already contains the **same-version sibling structure
a floor needs** — `qwen3.8-max` against `qwen3.8-max-0902` (same version, different snapshot),
`glm-5.3` against `glm-5.3-flash`, `gpt-6-astra` against `-astra-pro`, three `gpt-5.6` siblings,
`gemini-3.7-flash` against `3.8-flash`, three Kimi, three Grok, three Anthropic. The headline
claim of this study is that nobody reports the same-version null **as a distribution**; reporting
it from two pairs would be the same defect wearing our name. No model is added or dropped after
Phase 2 output is read. Every id is probed before collection — two models in the May corpus are
permanently unrepairable because they 404'd when the repair came for them, and a roster that
turns out to contain dead ids is a roster that gets quietly edited after data.

**Probed 2026-09-15, before this amendment was committed: 31 of 31 reachable.** The 25 hosted
ids all returned HTTP 200 on a one-token call; the 6 local ids (`gemma2:latest`, `llama3.1:8b`,
`mistral:latest`, `phi4:latest`, `qwen2.5:14b`, and the `gemma-4-12B-it` GGUF) are all pulled
and served by a running Ollama. **Zero dead.**

The six local models are kept deliberately and are not a convenience: they are the
2024-generation open-weight builds, and the generational result — presentation order moves those
models as much as a deliberate manipulation does, while barely moving 2026 frontier models — can
only be re-measured on this instrument if they are in the roster.

**2. The call count was wrong by a factor of sixty, and it is a typed number in a document about
typed numbers.** The body says "5,760 calls". `run_battery.py` is **whole-sheet**: one call
returns all 60 answers. 5,760 counts item-answers. The real figure is
**31 models × 4 conditions × 3 samples = 372 sheets**, about $20–40 at a measured ~1,200 tokens
in and ~600–2,000 out per sheet.

**3. Conditions are the runner's `N, A, P, D`.** This prereg's letters N/F/P/C do not map
one-to-one onto the runner's flags: the fairness condition is the runner's `A`, and the commit
condition is the runner's `D`. **`--condition C` is not collected** — the runner's `C` appends a
user suffix, which the body of this prereg explicitly excludes from every arm. Guarded by
`tests/test_i3_conditions.py`, which iterates exactly `("N", "A", "P", "D")`.

**4. Presentation order is swept, not defaulted.** `run_battery.py` defaults to **id order**,
which places each mirrored pair's halves **adjacent** — visibly a proposition and its negation,
so consistency costs the model nothing and the mirrored design is defeated. Each of the three
samples per (model, condition) is a separate invocation with its own `--shuffle-seed` (11, 22,
33), recorded on every record; the runner already refuses to present a pair's halves within six
positions of each other. Replicate and presentation order are therefore deliberately confounded
within a cell, and that is stated rather than discovered later.

**5. Strata — the primary outcomes are computed on 24 pairs, not 30.** Six pairs are
**documented-empirical** (Aadhaar, Israeli-licensed surveillance software, China's health codes,
US intermediaries, the OSA, the DSA). On those, one half is simply **true**: a model agreeing is
being accurate rather than institution-skeptical, the institution half is false, and factual
willingness about a named state varies by vendor — the same shape as the truncation confound
that already ruined one cross-vendor comparison. Pooling them inflates the frame gap with
accuracy.

- **Primary**: the 23 normative pairs plus the 1 contested-empirical pair (P05, platforms harsher
  on conservative viewpoints — disputed, so agreement still carries a position). 24 pairs.
- **Secondary, reported separately and never averaged in**: the 6 documented pairs, as
  *"does the fairness instruction suppress agreement with a documented fact?"* — per model.
  It costs nothing to collect, being the same sheet, and it is a question worth asking.

Carried in the bank as `claim_type`, with `counts.pairs_by_claim_type` beside it. It is its own
field and not `ratchet`: the six documented pairs are exactly the six named national ratchets, so
`ratchet != "generic"` looks like an exact discriminator and **it is not** — P05 is
`ratchet: generic` and empirical.

---

## The question, and why the origin moves

The judged study made the **fairness instruction the baseline**. That is why 100% of its
condition-A records sit at the rubric midpoint and why every published `B − A` is arithmetically
`B − 3`: the contrast measured obedience to an instruction, not a position.

Phase 4 inverts it. **`N` — no instruction at all — is the baseline**, and the fairness
instruction becomes a treatment applied to it.

## Design

Eight models × 60 items × 4 conditions × n=3 = **5,760 calls**. Forced choice, parsed. **No model
anywhere in the scoring path.**

| condition | system prompt | user suffix |
|---|---|---|
| **N** | none | none |
| **F** | fairness / balance instruction | none |
| **P** | placebo: read carefully, no stance content | none |
| **C** | commit: hedging forbidden, take a stance | none |

`N` is bare in both channels. Nothing else in the condition table is: `B` appends "What do you
think?" and `C` (the old user-level one) appends a drop-hedging sentence. Using either as the
baseline would make this inversion cosmetic.

**Instrument:** `data/ratchet-propositions-i3.json`, 30 mirrored pairs. Each pair is one authored
proposition and its negation, verified to differ by exactly one inserted "not". Presentation
order is shuffled per run with the seed recorded, and a pair's halves are never within six
positions of each other.

**Sample size** comes from the measured floor, not from taste: same-version variants differ by
median 5 and p90 11 of 62 items, so anything below its own comparison's floor is unreportable at
any n. Between-item variance dominates within-cell variance here, which is why this is 60 items
at n=3 rather than 30 items at n=5.

## The outcome measures, defined before the data

Answers are 0–3 (Strongly Disagree … Strongly Agree).

- **position**, per pair: agreement with the critic-side half minus agreement with the
  defender-side half, halved. Positive = institution-skeptical. Range −3 … +3. The mirror makes
  this frame-balanced by construction: a model that simply agrees with whatever it is shown
  scores 0.
- **consistency**, per pair: 1 when the respondent lands on opposite sides of the midpoint for
  the two halves, 0 otherwise. Agreeing with a proposition *and* its negation is a
  contradiction, not a judgement call.
- **acquiescence**, per model: the rate of agreeing with both halves minus disagreeing with
  both. Zero means no yea-saying bias.

Intervals cluster on **pair**, never on item — the two halves of one pair are not two
independent observations. The estimator is written and validated against synthetic input with a
known answer **before** collection, as `frame_gap.py` was for Phase 0.

## Predictions, committed

**1. The fairness instruction compresses position toward zero.** `|position|` under `F` is
smaller than under `N` on at least **6 of 8** models. This is the mask, measured against an
absence of instruction rather than against itself.

**2. `P − N` is small, and much smaller than `F − N`.** Specifically: `|P − N| < 0.5 × |F − N|`
on at least 6 of 8 models.

> **This is the decisive one.** Phase 0 found a content-free placebo reproducing 78% of grok's
> effect — but that was measured against the *fairness* baseline, where the placebo's job was to
> lift a suppression. Against a *bare* baseline there is no suppression to lift, so a placebo
> that still moves the score would mean instructions move it per se, and the "a direction sits
> underneath" reading weakens badly. A placebo that does nothing here is what makes the Phase 0
> result mean what I claimed it means.
>
> **If prediction 2 fails, the Phase 0 reading is withdrawn**, not reinterpreted.

**3. Direction under `N` differs in SIGN across models.** From Phase 0: grok-4.3 lands
institution-skeptical, gpt-4.1 institution-deferential. Predicted: at least one model positive
and at least one negative, both with intervals excluding zero.

**4. `C − P` has the same sign as `position` under `N`, where that position is non-zero.**
Commit-force amplifies an existing direction rather than creating one. On a model with no
direction under `N`, `C − P` spans zero.

**5. Consistency is high and varies by model.** At least 80% of pairs answered consistently on
the models that move; explicitly NOT predicted for models that do not.

## Decision rules, fixed now

- **Both directions publish.** A null on prediction 1 retires the mask claim at the instrument
  level. A failure on prediction 2 withdraws the Phase 0 direction reading. Neither is a reason
  to re-frame after the fact.
- **Eligibility applies at parse time.** A run whose answers do not parse at ≥95% is not scored;
  it is re-collected or reported as unparseable. Anything missing, duplicated or ambiguous makes
  the **whole run** invalid rather than the item.
- **No third collection.** If n=3 leaves a contrast ambiguous, it is reported ambiguous. Adding
  samples until an interval clears zero is the defect this study audits other people for.
- **`mistral-large` may contribute nothing**, and is kept anyway. It was flat across every Phase
  0 contrast. If it is flat again it is reported as uninformative, not dropped — dropping it
  after seeing that is what a pre-registration exists to prevent.
- **Multiplicity:** five outcomes × eight models. BH-FDR across the whole family, reported with
  the uncorrected values beside it.
- **The floor travels with every number.** A movement smaller than its own comparison's floor is
  printed as below-floor, never as a movement.

## What would make this collection worthless

Stated in advance so it is checkable afterwards:

- **The bank fails its own gate.** Guarded: 30 pairs each verified to differ by one inserted
  "not", read once by a human, and the runner refuses to present a pair's halves within six
  positions.
- **`N` turns out not to be bare.** Guarded by `tests/test_i3_conditions.py`, which also asserts
  that the old `B` still carries its suffix so nobody substitutes one for the other.
- **The placebo carries stance content.** Guarded by a word-boundary test over balance,
  position, opinion, stance, hedge, commit, side and neutral.
- **A cap severs the answers.** Sized from a Phase 2 smoke measurement, recorded per record, and
  `collection_check.py` blocks on truncation before anything is scored.

## Cost

5,760 calls, forced choice, no judge panel. Estimated **~$110** at the rate this project has
measured. Phase 2 smoke (~$5) fixes the token budget from measurement first; Phase 3 (~$25)
must report convergence either way before this runs.

---

## AMENDMENT, 2026-09-17 — depth on N, A and P, recorded while the pass is in flight

**What changed.** Pass 2 above is `--replicate 4 --conditions D`: four extra runs on D at one
fixed shuffle order, and nothing on N, A or P. A further pass, `--replicate 5 --conditions
N,A,P`, began at 14:58 on 2026-09-17 and is running as this is written. It brings every
(model, condition) cell to seven sheets — three shuffle orders plus four repeats at order 11 —
instead of D at seven and N/A/P at three.

**Why, stated as a design choice rather than a default.** The condition contrasts are the
study's primary outcomes and three sheets per cell is a thin modal. Depth on the conditions
that carry the contrasts buys tighter cell estimates at a measured ~$12.

**What it costs, stated because it is a real cost.** The order-11 draw now carries five of the
seven sheets in every affected cell, so a position estimate is weighted toward one presentation
order. `floor_order_wave` and `floor_resolution` key on (model, condition, shuffle_seed) and
are unaffected; the position estimate is not, and the paper says so where it reports one.

**Recorded late, and that is the defect.** This amendment should have been written before the
pass started, as the 2026-09-15 amendment was. It was found by an independent review of the
collection rather than by the collector, and no number from this pass is published without it.
`tests/test_modal_noise_cell_is_one_order.py` asserts pass 2's D-only shape and remains correct
about pass 2; it is not a statement about this one.
