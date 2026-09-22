# Pre-registration — does silent omission follow the ITEM, the SLOT, or the PRINTED NUMBER?

**Registered 2026-09-18, before any sheet in this arm is collected.** Nothing in it may be
amended after the first `--run`; an amendment made after data exists is recorded as an
amendment, dated, with the reason, and the original text is left standing.

---

## Amendment 1, 2026-09-20 — the hosted arm's backends were not pinned, and it is re-collected

**This changes no hypothesis, no item, no order and no decision rule.** It fixes a collection
defect in the hosted replication and records what was done, because the arm's result — that
the numbering artifact is not local-only — is a finding this study leads with.

`collection_check` blocks `runs/2026-09-18-omission-hosted`: **16 of its 36 model × condition
cells had their replicates served by more than one provider**, worst `qwen/qwen3.8-2.4t-a95b`
across seven backends (Alibaba, DeepInfra, Modal, Novita, SiliconFlow, Together, Venice), and
**8 of 18 models were served by more than one backend across their conditions**, worst
`deepseek/deepseek-v3.2` across seven. Serving path is a same-version variant in this study,
so for those eight models the as-is/renumbered contrast is confounded with the routing. The
collector had no way to pin a backend; it does now (`--provider`, fallbacks off).

The eight are re-collected in full — 48 sheets each, the same 12 orders, the same N and P, the
same two numbering arms, **384 sheets** — into `runs/2026-09-20-omission-hosted-pinned`, a NEW
directory rather than a top-up, per LEARNINGS #64. Each is pinned to the backend that already
served most of its sheets, which is availability evidence rather than a preference:

| model | pin | held that share before |
|---|---|---|
| `deepseek/deepseek-v3.2` | Baidu | 18 of 48, across 7 backends |
| `ibm-granite/granite-4.2-8b` | DeepInfra | 38 of 48 |
| `meta-llama/llama-3.3-70b-instruct` | AkashML | 41 of 48 |
| `minimax/minimax-m2.7` | Minimax | 27 of 48 |
| `moonshotai/kimi-k2-thinking` | Novita | 26 of 48 |
| `nvidia/nemotron-3.5-lightning` | DeepInfra | 18 of 48 |
| `qwen/qwen3.8-2.4t-a95b` | SiliconFlow | **9 of 48, across 7** |
| `xiaomi/mimo-v2.5-pro` | Xiaomi | 28 of 48 |

**The ten unaffected models are not re-collected** and their sheets stand: each was served by
one backend throughout, so nothing about them is confounded and re-buying them would spend
money to reproduce data that is already sound.

### The per-backend split, published beside the pin

**Added 2026-09-21 after an adversarial review pointed out that "the backend that served most
of its sheets" is a rule applied where the outcome was already visible.** It was not consulted,
but that is an assurance, and an assurance is not a control. The split is therefore published
so a reader can check it. Invalid (omitted-item) sheets per backend in the as-is arm, which is
the arm the finding rests on:

| model | pinned | pinned backend | the alternatives |
|---|---|---|---|
| `nvidia/nemotron-3.5-lightning` | DeepInfra | **4 invalid of 9** | Phala **0 of 9**, CoreWeave 1 of 6 |
| `xiaomi/mimo-v2.5-pro` | Xiaomi | **0 invalid of 14** | GMICloud **2 of 2**, three others 0 |
| `qwen/qwen3.8-2.4t-a95b` | SiliconFlow | 0 of 5 | every backend 0; **a three-way tie on sheet count** (SiliconFlow, Modal and DeepInfra at 9 each across both arms), broken by sort order and not by evidence |
| `meta-llama/llama-3.3-70b-instruct` | AkashML | **1 invalid of 23** | the alternative carried 0 |
| the other four | — | 0 either way | 0 either way |

**Read it honestly. On the models where the backends disagree, the rule picked the
backend carrying the omissions; on the next, it picked the one carrying none.** Opposite
directions is what an outcome-blind rule produces, and it is the reason to publish the table
rather than the reassurance. But two consequences stand regardless:

1. **`nemotron` is one of the two hosted models this arm's finding rests on**, and its omission
   rate is 4 of 9 on one backend and 0 of 9 on another. Whatever else is true, *serving path
   moves item omission on this model* — which the arm did not set out to measure and cannot
   cleanly separate from the numbering effect in the 09-18 data.
2. The qwen tie was broken silently. It changes no outcome here, but a tie broken by sort
   order and reported as "the backend that served most of its sheets" is a rule described more
   firmly than it was applied.

**The 2026-09-18 sheets are KEPT, not deleted, and are superseded for these eight models
only.** A re-collection that erases what it replaces destroys the evidence that the defect was
real (LEARNINGS #62). Both directories are declared, and the analysis reads the pinned one for
the eight.

**What would make this arm worse rather than better:** a pin that cannot serve all 48. If any
model's pinned backend fails partway, that model ends with a short cell under one pin instead
of a full cell under several, and the honest report is the shortfall — not a quiet fallback,
which is the thing `--provider` turns off.

## 1. What this exists to settle

Six local builds in `runs/2026-09-16-ratchet-v3-wave/` return sheets that answer 29–31 of 32
items with the budget untouched — 160–210 tokens against caps of 32,768 and higher — no refusal
text, and the missing item's number absent from the response entirely. Nothing was written and
lost: the model simply never emitted that line. Whole-sheet refusal counting cannot see this,
and every published position score is computed after dropping such sheets.

`data/collection-limitations.json` declared, until 2026-09-18, that three of those models omit
specific **propositions** — `mistral:latest` items 20, 21 and 31; `qwen2.5:14b` item 4;
`gemma-4-12B` item 2. That claim was about to lead the paper.

**`scripts/item_omission.py` shows the corpus cannot support it.** Every declared pattern sits
at the slot that item occupies in ONE presentation order:

| model | declared item(s) | where they actually sit | verdict |
|---|---|---|---|
| `mistral:latest` | 20, 21, 31 | slots 0, 1 and 31 of order 11 | NOT SEPARABLE |
| `qwen2.5:14b` | 4 | slot 4 of order 11 | NOT SEPARABLE |
| `gemma-4-12B` | 2 | slot 2 of order 33, the line "2." after "22." | NOT SEPARABLE |
| `qwen2.5:14b-q8_0` | 4, 13 | same order-11 slots as its sibling | NOT SEPARABLE |
| `mistral:7b-q8_0` | 21 | two slots, but slot 31 also eats item 12; n = 4 per cell | MIXED |
| `llama3.1:8b` | **14, undeclared** | 10/23 at slot 12, 1/19 at slot 17; slot 12 loses item 19 on 1/19 | **MIXED — interaction** |

Item identity and page position are the same variable in this data, because the depth-5 pass
repeated one order: **808 of 1,411 records sit at order 11**, and only three orders exist.
A concentration statistic does not help — the permutation p on per-item drop counts is below
0.001 for four of these models, and `item_omission.py --selftest` demonstrates on synthetic
data that a *pure slot effect* produces exactly that p. Concentration cannot discriminate, and
reporting it as though it could is the failure this study convicts other papers of.

**Hosted models: zero partial sheets in roughly a thousand.** Whatever this is, it is a
property of 2024-generation 7–14B local builds under whole-sheet administration, and any
sentence about the wider literature must say so.

---

## 2. The three hypotheses, and the design that separates them

In the wave, an item's **id** and its **printed number** are the same integer, so only two
hypotheses are even nameable. This arm adds a third by breaking that identity.

| | hypothesis | what the drop follows |
|---|---|---|
| **H1** | **item** | the proposition itself, wherever it appears and whatever it is numbered |
| **H0a** | **slot** | the position on the page — first line, last line, a given depth |
| **H0b** | **printed number** | the literal numeral, e.g. a one-digit label after a two-digit one |

**Two arms.**

- **Arm S (shuffled, renumbered = off).** Items presented in shuffled order, each keeping its
  own id as its printed number. This is the wave's design, with many more orders.
- **Arm R (renumbered).** The same shuffled orders, but items printed **1..32 in presentation
  order**, so the printed number equals `slot + 1` and no longer equals the item id. The
  manifest records the id at every slot. H0b predicts the drop follows the numeral into its new
  position; H1 predicts it follows the proposition; H0a predicts it does not move at all.

**Roster, fixed now:** `mistral:latest`, `qwen2.5:14b`,
`hf.co/lmstudio-community/gemma-4-12B-it-GGUF:Q4_K_M`, `llama3.1:8b`, `mistral:7b-instruct-q8_0`.
Five builds, chosen because they are the only models in the corpus that produce partial sheets.
No model is added or removed after collection begins. All are local; **API spend is zero**.

**Cells:** 5 models × 12 shuffle seeds × 2 conditions (N, P) × 2 arms × 1 run = **240 sheets**.
Shuffle seeds are the first twelve values of `random.Random(20260918).sample(range(1, 1000), 12)`,
written into the manifest before the first call so they cannot be chosen to suit a result.
Condition D is not collected: the question is about sheet mechanics, not about the manipulation.

**Why twelve.** An item claim needs the same item observed at several distinct slots with enough
sheets at each. Twelve orders puts every item at twelve positions and gives each (item, slot)
cell a denominator the wave never had. `item_omission.py` treats a pattern confined to one
order as NOT SEPARABLE and will keep doing so; twelve is the number at which it stops firing
for a real effect.

---

## 3. Decision rule, fixed before collection

The analysis is `scripts/item_omission.py`, which exists, is selftested against synthetic slot
effects and item effects, and will not be modified after the first sheet lands except to fix a
defect — which would be recorded here with its commit.

**H1 is accepted for a model** when `item_omission.py` returns `ITEM-SPECIFIC` for it: some item
is dropped on at least `MIN_SHEETS` sheets at each of **two or more distinct slots**, and no slot
accounts for the drops across two or more distinct items. Reported per model, never pooled.

**H0b is accepted** when the drop rate in Arm R follows the printed numeral rather than the id —
i.e. the items dropped in Arm R are those whose *slot + 1* matches the numeral dropped in Arm S.

**H0a is the default** and needs no evidence: it is what the wave already shows.

### The kill rule

**If H1 is not accepted for any model, the item-omission finding does not lead the paper.** It
becomes, in this order and this wording:

1. a **format artifact** — silent partial non-response in small local builds, invisible to
   whole-sheet refusal counting, with the numbering mechanism named; and
2. **discard that conditions on compliance** — the surviving fact that damages the literature.
   `position_analysis.load_records`, `floor_table.load` and `key_numbers` all read `valid` only,
   so for `qwen2.5:14b` at order 11 the analysed sheets are exactly those on which it chose to
   answer slot 4. That is selection on the outcome by the subject, and it holds whatever causes
   the omission.

and the **placebo result leads instead** — the content-free control arm moving position on a
large minority of the panel, which is a claim about every study in the literature rather than
about six local builds.

This is written down now so the lead is not chosen after the answer is known. The paper has
already had one lead withdrawn for exactly that reason.

### What would make this arm uninformative

If fewer than 8 of the 12 orders return usable sheets for a model, that model is reported as
**not tested**, not as a null. `mistral:7b-instruct-q8_0` answers *Agree* to all 32 items on
most sheets and may fail this; its degenerate sheets are excluded from the drop denominator by
the same rule `floor_table` already applies, and the exclusion count is printed.

---

## 4. What is NOT being claimed

- Nothing here speaks to **hosted** models. They produce no partial sheets and this arm does
  not collect any.
- Nothing here is a claim about **positions, direction or politics**. The outcome is whether a
  line appears on a page.
- A positive H1 result on one model is **one model**. It would make item-specific omission a
  documented phenomenon in small open-weight builds, not a correction to the published
  literature's means.
- The `llama3.1:8b` item-14 interaction is the pre-identified case of interest. It is named
  here **before** the arm runs precisely so that a positive result on it cannot be presented as
  a discovery and a negative result cannot be quietly dropped.

---

## 5. Provenance

- Instrument: `data/ratchet-battery.json`, 32 items in 16 mirrored pairs, author-written
  2026-08-30, unchanged by this arm.
- Presentation order: `run_battery.order_items`, the collector's own function, with the mirror
  separation constraint it already applies.
- Temperature 0.7, matching the wave, so the sheets are comparable to it.
- Run directory: `runs/2026-09-18-omission-orders/`, a new directory; the wave is not written to.
- Conditions N and P carry their wave definitions verbatim.

**Registered before collection. Collection has not begun as of this commit.**
