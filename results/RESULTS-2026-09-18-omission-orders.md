# Silent item omission is caused by NON-MONOTONIC NUMBERING, not by item content

**Collected and analysed 2026-09-18 against `PREREG-2026-09-18-omission-orders.md`, which was
committed before the first call and fixed the kill rule in advance.**

`python scripts/run_omission_orders.py --run` (240 sheets, local, $0)
`python scripts/item_omission.py --run 2026-09-18-omission-orders --matrix`

---

## The result

**H1 — omission follows the ITEM — is REJECTED.**

Two arms, identical in every respect except the numeral printed beside each proposition:

- **as-is** — items shuffled into a presentation order, each keeping its own id as its printed
  number. The sheet reads `20. … 31. … 1. … 23. … 4. …`. This is what every sheet in this
  study, and every whole-sheet administration that randomises order while preserving item
  identity for scoring, looks like.
- **renumbered** — the same items, in the same order, with the same texts, printed `1.` to
  `32.` in presentation order. The numeral is now `slot + 1` and no longer identifies the item;
  `run_battery.presentation_labels` records the map and the collector remaps answers back.

| arm | sheets attempted | partial sheets | items lost |
|---|---:|---:|---:|
| as-is (shuffled numerals) | 102 | **15 (14.7%)** | 26 |
| renumbered (1..32) | 100 | **1 (1.0%)** | 1 |

**Fisher exact, one-sided: p = 1.8 × 10⁻⁴.**

Per model, partial-sheet rate:

| model | as-is | renumbered |
|---|---:|---:|
| `mistral:7b-instruct-q8_0` | 34.8% | **0.0%** |
| `mistral:latest` | 16.7% | 4.2% |
| `gemma-4-12B` | 14.3% | 0.0% |
| `qwen2.5:14b` | 8.3% | **0.0%** |
| `llama3.1:8b` | 0.0% | 0.0% |

Twelve presentation orders per model per condition, so the earlier NOT SEPARABLE verdict no
longer applies: an item that was being skipped for its own sake would keep being skipped when
its numeral changed. It does not.

## What this means for the design that produced it

Randomising presentation order is the standard control for order effects and it is correct —
Domínguez-Olmedo et al. (arXiv:2306.07951) is the strongest statement of why. **The obvious
implementation of it is what causes the loss.** You shuffle the items and keep each one's id as
its printed number, because that is what lets you score the sheet. The result is a
non-monotonic list, and small models silently drop lines from it.

So the recommended fix for one bias introduces a second, invisible failure — invisible because
the sheet is not refused, is not truncated, uses a fraction of its token budget, and arrives
looking complete. A refusal table counting whole-sheet declines cannot see it, and the
analysis then runs on whatever survived.

**The remedy is free and it is in the collector now:** renumber the presentation, record the
map, remap the answers. Nothing about the randomisation changes.

## CORRECTION, same day: it is NOT local-only

**The first version of this file said "local 7–14B builds only… hosted models produce zero
partial sheets in roughly a thousand wave records." That was true of the wave's hosted roster
and false as a general claim, and it took four hours to falsify.**

A roster smoke test on 22 models this corpus had never measured returned partial sheets from
two hosted models on their *first* administration — `nvidia/nemotron-3.5-lightning` 30 of 32,
`amazon/nova-micro-v1` 31 of 32 — both over an API, both under as-is numbering. Running the
same two arms on them:

| arm | attempted | partial | items lost | Fisher p |
|---|---:|---:|---:|---|
| local, 5 builds | 102 | 15 (14.7%) | 26 | 1.8 × 10⁻⁴ |
| **hosted, 2 models** | 48 | **6 (12.5%)** | 14 | 0.070 |
| pooled | 150 | 21 (14.0%) | 40 | 2.7 × 10⁻⁵ |

Same direction, same magnitude. **The hosted arm alone does not reach significance** — two
models and 92 sheets — so it is reported at p = 0.070 and not leaned on, and the arm is being
re-run across all 16 models from the roster extension to give it a real denominator.

The honest statement is therefore **not** "local models do this." It is: *this is a property of
whole-sheet administration, it varies by model, and the wave's hosted roster happened to
contain no susceptible model.* Which is precisely the shape of the problem — a study whose
roster happens to miss the affected models reports a clean corpus and never learns otherwise.

## Honest limits

- **Susceptibility is per model, not per class.** Most models never drop a line. Two of 22
  previously unmeasured hosted models did, on their first sheet.
- **`gemma-4-12B` is unusable in both arms** — 6 of 24 sheets usable as-is, 5 of 24 renumbered
  — and its failures shift between `refused` (3 → 11) and `budget-exhausted` (14 → 8) across
  arms. That shift is reported rather than netted, but it is not evidence either way. Dropping
  it, the other four models go from **14 partial of 95 to 1 of 95**, which is the same result.
- **Renumbering is not a pure win overall.** Across all five models refusals rose 4 → 12 while
  partial sheets fell 15 → 1; every one of those extra refusals is `gemma-4-12B`. Valid sheets
  still rose 87 → 99.
- One arm, one instrument, one run per cell. The claim is about sheet mechanics, not about
  positions, and nothing here speaks to what any model believes.

## What it replaces

`data/collection-limitations.json` declared until 2026-09-18 that three models omit specific
**propositions** — "systematic omission of one proposition, not truncation", "item 4, the
defender half on programmable money". That reading was going to lead the paper on the claim
that published position scores are computed over unknown non-random subsets of the instrument.
It is withdrawn. The patterns were the slots those items occupied in a single presentation
order, and the numeral is what the models were losing.

Per the pre-registered kill rule, the contribution is now stated as:

1. a **format artifact with a named mechanism** — non-monotonic numbering, measured, remedied;
2. **discard that conditions on compliance** — the surviving damage claim, which holds whatever
   causes the omission: `position_analysis.load_records`, `floor_table.load` and `key_numbers`
   all read `valid` only, so a model's analysed sheets are exactly the ones it chose to
   complete;

and the **placebo result leads the paper** — the content-free control arm moving measured
position on 16 of 37 models, which is a claim about every study in the literature rather than
about five local builds.

## Commands

Every count and every p-value above:

    python scripts/omission_arms.py --run 2026-09-18-omission-orders     # the local arm
    python scripts/omission_arms.py --run 2026-09-18-omission-hosted \
        --only-models nvidia/nemotron-3.5-lightning,amazon/nova-micro-v1 # the hosted 2
    python scripts/omission_arms.py --run 2026-09-18-omission-orders \
        --also 2026-09-18-omission-hosted \
        --only-models nvidia/nemotron-3.5-lightning,amazon/nova-micro-v1,\
mistral:7b-instruct-q8_0,mistral:latest,qwen2.5:14b,llama3.1:8b,\
hf.co/lmstudio-community/gemma-4-12B-it-GGUF:Q4_K_M                      # the pooled row
    python scripts/item_omission.py --run 2026-09-18-omission-orders --matrix
