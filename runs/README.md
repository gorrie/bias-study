# `runs/` — the current study's corpus

Every run here but the two described under the inventory was collected on the Ratchet battery: 32 forced-choice items in 16 mirrored
pairs, written by Ian Gorrie, MIT-licensed and published in full at
[`../data/ratchet-battery.json`](../data/ratchet-battery.json). There is no fetch step and no
third-party item text to withhold. Everything collected before this instrument is in
[`../data/`](../data/README.md), which has its own README. The two roots are different corpora,
not two names for one thing.

The inventory below is generated from the records themselves. Do not edit it by hand.

## What is here

<!-- GEN:corpus-inventory-runs -->
| run | records | models | instrument | status | read by |
|---|---:|---:|---|---|---|
| `2026-09-16-ratchet-v3-wave` | 3,897 | 65 | `ratchet-battery` | active | runs/*-wave/*.jsonl, named in a script, named in a document |
| `2026-09-16-ratchet-v3-wave-budget-probe` | 71 | 71 | `ratchet-battery` | active | named in a script, named in a document |
| `2026-09-18-bce-smoke` | 7 | 2 | `ratchet-battery` | active | named in a script |
| `2026-09-18-omission-hosted` | 864 | 18 | `ratchet-battery` | active | named in a script, named in a document |
| `2026-09-18-omission-orders` | 240 | 5 | `ratchet-battery` | active | named in a script, named in a document |
| `2026-09-18-paraphrase` | 448 | 46 | `ratchet-battery` | active | named in a script, named in a document |
| `2026-09-18-roster-smoke` | 22 | 22 | `ratchet-battery` | active | named in a script, named in a document |
| `2026-09-19-rung2-elicitation` | 280 | 7 | `ratchet-battery` | active | named in a script, named in a document |
| `2026-09-19-rung2-smoke` | 3 | 1 | `ratchet-battery` | active | named in a script, named in a document |
| `2026-09-20-omission-hosted-pinned` | 384 | 8 | `ratchet-battery` | active | named in a script, named in a document |
| `2026-09-20-rung2-control-v2` | 70 | 7 | `ratchet-battery` | active | named in a script, named in a document |
| `2026-09-21-omission-nemotron-phala` | 48 | 1 | `ratchet-battery` | active | named in a script, named in a document |
| `2026-09-24-partials-renumbered` | 369 | 13 | `ratchet-battery` | active | named in a script, named in a document |
| `2026-09-25-local-gradient` | 1,176 | 12 | `ratchet-battery` | active | named in a script, named in a document |
| `2026-09-25-local-gradient-judged` | 1,800 | 2 | previous | active | named in a script, named in a document |
| `2026-09-25-placebo-wording` | 450 | 10 | `ratchet-battery` | active | named in a script, named in a document |
| `2026-09-25-same-items-both-paths` | 1,536 | 6 | `ratchet-battery` | active | named in a script, named in a document |
| `2026-09-25-serving-path` | 311 | 5 | `ratchet-battery` | active | named in a script, named in a document |
| `2026-09-25-wave-completion` | 145 | 3 | `ratchet-battery` | active | named in a script, named in a document |
| `mask-gradient` | 226 | 4 | previous | active | named in a script, named in a document |
| **20 directories** | **12,347** | | | | |
<!-- /GEN:corpus-inventory-runs -->

`instrument` is read off each record's own `instrument` field, not inferred from the
directory's name or date. `status` comes from [`../data/withdrawals.json`](../data/withdrawals.json).
`read by` says whether an analysis glob, a script or a document reaches the directory;
[`PROVENANCE.json`](PROVENANCE.json) beside this file lists, for every run, which documents name
it and what the study classified it as.

Two directories report `previous`. `2026-09-25-local-gradient-judged` puts ten of the
earlier free-text questions (the `data/` instrument) to a stock build and its abliteration under
the battery's six conditions, so that the judge-free and the judged instruments can be compared
on the same builds. It is part of the current study and none of its records is a battery sheet.
`mask-gradient` is the superseded first attempt at the local gradient: free-text questions
T01-Q2…T10-Q2 under conditions A–E on four local builds, 226 records, sampled at temperature 0.7
with no seed. It is kept as reference, no figure in the paper reads it, and
`2026-09-25-local-gradient` replaced it.

## A guide to the directories

Runs are named by the date collection began. Pre-registrations were committed before the first
call of the arm they govern; each results document names the script that computes its figures.

| directory | what it is | pre-registration | results |
|---|---|---|---|
| `2026-09-16-ratchet-v3-wave` | the wave: 65 models, conditions N (bare), A (balance instruction), D (commitment directive), P (content-free placebo), three presentation orders, five draws per cell; a subset of models also under the further prompt arms B, C and E, and seven under the eight-cell clause factorial F000–F111, three of them at all three orders (an eighth, glm-5.2, returned nothing, see [`../data/empty-records.json`](../data/empty-records.json), and was completed in `2026-09-25-wave-completion`). Every floor in the paper is computed from it | [`PREREG-2026-09-14-i3-phase4.md`](../prereg/PREREG-2026-09-14-i3-phase4.md), Amendment 2 | [`PAPER-below-the-floor.md`](../PAPER-below-the-floor.md) |
| `2026-09-16-ratchet-v3-wave-budget-probe` | 71 single sheets that measured the token budget the wave then ran at. A fixture, not a measurement of any model | — | — |
| `2026-09-18-bce-smoke` | seven sheets confirming conditions B, C and E render and parse. A fixture | — | — |
| `2026-09-18-roster-smoke` | one sheet per hosted model, confirming the roster answered before the wave paid for it. A fixture | — | — |
| `2026-09-18-omission-orders` | silent item omission, local models: 240 sheets across presentation orders, testing whether omission follows item content or numbering | [`PREREG-2026-09-18-omission-orders.md`](../prereg/PREREG-2026-09-18-omission-orders.md) | [`RESULTS-2026-09-18-omission-orders.md`](../results/RESULTS-2026-09-18-omission-orders.md) |
| `2026-09-18-omission-hosted` | the same design on 18 hosted models, 864 sheets, as-is against renumbered sheets. Backends unpinned, which is why it was re-collected | same file | same file |
| `2026-09-20-omission-hosted-pinned` | the hosted omission arm re-collected with each model pinned to one backend, 8 models, 12 orders, conditions N and P | same file, Amendment 1 | [`RESULTS-2026-09-21-omission-pinned.md`](../results/RESULTS-2026-09-21-omission-pinned.md) |
| `2026-09-21-omission-nemotron-phala` | one model's omission cell re-collected on a second pinned backend (48 sheets) | same file | same file |
| `2026-09-18-paraphrase` | ten semantics-preserving wordings of the forcing instruction (`template` T01–T10) at one order, condition N, 46 models: the paraphrase floor | [`PREREG-2026-09-18-paraphrase.md`](../prereg/PREREG-2026-09-18-paraphrase.md) | [`RESULTS-2026-09-21-paraphrase.md`](../results/RESULTS-2026-09-21-paraphrase.md) |
| `2026-09-19-rung2-elicitation` | rung 2 of the escalation ladder: the G0DM0D3 elicitation arms (`G-*`) and sampling presets (`S-*`) over condition B, seven models, ten sheets per cell | the rung's design is [`PREREG-2026-09-13-pipeline-rung.md`](../prereg/PREREG-2026-09-13-pipeline-rung.md); the same-protocol control it is scored against is [`PREREG-2026-09-20-rung2-control-v2.md`](../prereg/PREREG-2026-09-20-rung2-control-v2.md) | [`RESULTS-2026-09-21-rung2-control-v2.md`](../results/RESULTS-2026-09-21-rung2-control-v2.md), [`RESULTS-2026-09-25-rung2-within-depth10.md`](../results/RESULTS-2026-09-25-rung2-within-depth10.md) |
| `2026-09-19-rung2-smoke` | three sheets confirming the rebuilt rung-2 collector reached OpenRouter directly. A fixture | — | — |
| `2026-09-20-rung2-control-v2` | the plain condition-B control for rung 2 at protocol v2, matched on model and order | [`PREREG-2026-09-20-rung2-control-v2.md`](../prereg/PREREG-2026-09-20-rung2-control-v2.md) | [`RESULTS-2026-09-21-rung2-control-v2.md`](../results/RESULTS-2026-09-21-rung2-control-v2.md) |
| `2026-09-24-partials-renumbered` | the wave's dropped partial sheets (0 < answers < 32) re-collected under the renumbered protocol, 13 models, to test whether any floor moves | [`PREREG-2026-09-24-partials-renumbered.md`](../prereg/PREREG-2026-09-24-partials-renumbered.md) | the paper, §5.8 |
| `2026-09-25-local-gradient` | the pressure gradient (N, A, P, D, C, E) on stock and abliterated local builds: Qwen3.8-27B, Gemma-4-12B and Qwen2.5-14B families, 12 builds, 1,080 sheets. `smoke/` and `replicate/` hold the pre-registration's smoke and replicate sheets; `analysis.json` caches the report | [`PREREG-2026-09-25-local-gradient.md`](../prereg/PREREG-2026-09-25-local-gradient.md) | [`RESULTS-2026-09-25-local-gradient.md`](../results/RESULTS-2026-09-25-local-gradient.md) |
| `2026-09-25-local-gradient-judged` | the judged half of the same arm: 600 free-text answers on ten earlier questions from two Qwen3.8-27B builds, scored by two local judges (`scores/`), with the judge calibration and the budget cut recorded before any score existed | same file | same file |
| `2026-09-25-placebo-wording` | a second content-free placebo, P2, beside P and N: 10 models, three orders, five draws | [`PREREG-2026-09-25-placebo-wording.md`](../prereg/PREREG-2026-09-25-placebo-wording.md) | [`RESULTS-2026-09-25-placebo-wording.md`](../results/RESULTS-2026-09-25-placebo-wording.md) |
| `2026-09-25-serving-path` | one model on two pinned backends, interleaved draw by draw: is access tier a serving-path effect? 5 models, conditions N and A | [`PREREG-2026-09-25-serving-path.md`](../prereg/PREREG-2026-09-25-serving-path.md) | [`RESULTS-2026-09-25-serving-path.md`](../results/RESULTS-2026-09-25-serving-path.md) |
| `2026-09-25-wave-completion` | the wave's short cells, completed after the panel froze: glm-5.2's B, C, E and clause-factorial cells, gemini-3.8-flash's second and third factorial orders, and the culturerevolt build's B and C; 145 sheets, out of the panel | [`PREREG-2026-09-25-wave-completion.md`](../prereg/PREREG-2026-09-25-wave-completion.md) | [`RESULTS-2026-09-25-wave-completion.md`](../results/RESULTS-2026-09-25-wave-completion.md) |
| `2026-09-25-same-items-both-paths` | the 32 propositions asked as free-text questions and scored by the May judge panel, 6 models, conditions N and A, against the same models' forced-choice sheets in the wave: convergent validity of the two scoring paths. `raw/` and `scored/` as in `data/` | [`PREREG-2026-09-25-same-items-both-paths.md`](../prereg/PREREG-2026-09-25-same-items-both-paths.md) | [`RESULTS-2026-09-25-same-items-both-paths.md`](../results/RESULTS-2026-09-25-same-items-both-paths.md) |
| `mask-gradient` | the superseded first attempt at the local gradient: free-text questions under conditions A–E on four local builds, 226 records, temperature 0.7 with no seed. Kept as reference; no figure in the paper reads it | [`PREREG-2026-08-28-refusal-direction.md`](../prereg/PREREG-2026-08-28-refusal-direction.md) | replaced by `2026-09-25-local-gradient` |

Two further pre-registered analyses collected nothing and read sheets already here:
[`PREREG-2026-09-25-factorial-floor-calibration.md`](../prereg/PREREG-2026-09-25-factorial-floor-calibration.md)
calibrates the clause factorial's floor rule on the wave's F cells
([results](../results/RESULTS-2026-09-25-factorial-floor-calibration.md)), and
[`PREREG-2026-09-25-rung2-within-depth10.md`](../prereg/PREREG-2026-09-25-rung2-within-depth10.md)
computes the within-rung contrasts on `2026-09-19-rung2-elicitation`
([results](../results/RESULTS-2026-09-25-rung2-within-depth10.md)).

The fixtures are kept because deleting the evidence that a collection was configured correctly
is not how this project handles its own record. They are not results.

## What you may conclude from it, and what you may not

The wave is the corpus behind every floor in the paper: the order floor, the modal sampling
floor, the same-version floors. The smaller dated runs are targeted extensions of one factor
each, and each is named in the paper section that uses it.

Nothing here is judge-scored except the two 2026-09-25 free-text arms named above. The battery
is forced-choice and is read positionally; there is no rubric, no LLM judge and no 1–5 score on
a battery sheet. The judge-scored study is the previous instrument's, in `data/`, and the two
are not comparable: no figure computed from 32 items may be set beside one computed from the
earlier question set. Side-flip counts are not linear in item count, and treating them as if
they were is the specific error this study is organised against.

The directories here remain active, and the claims computed from them that were later
withdrawn are registered in [`../data/withdrawals.json`](../data/withdrawals.json). The sheets
that were withdrawn from the wave's panel are in [`../withdrawn/`](../withdrawn/README.md), with the reason
for each, and are read by nothing here.

## How to load it

Three layouts, all JSON Lines:

- Battery sheets, flat in the run directory as `<model>__<condition>.jsonl`, one record per
  sheet, schema `battery-run/1` (older sheets say `compass-run/1`; readers accept both).
  `answers` is the parsed sheet, keyed by item id; `valid` says whether the sheet is complete.
- `2026-09-25-local-gradient-judged`: free-text records at the top level, schema
  `local-gradient-judged/1`, and one `scores/<judge>.jsonl` per judge keyed by `uid`.
- `2026-09-25-same-items-both-paths`: `raw/` and `scored/` per model, the May layout.

Each directory carries the collector's `manifest.json`, written before the first call, or, for
the four collected by a tool that wrote none, a `manifest.derived.json` content freeze that
`scripts/derive_manifest.py --check` verifies. Resolve a run by name rather than by spelling a
path; the resolver searches both corpus roots:

```python
import sys; sys.path.insert(0, "scripts")
from studypaths import run_path, all_run_dirs

d = run_path("2026-09-16-ratchet-v3-wave")   # resolves in whichever root holds it
everything = all_run_dirs()                   # every run, both roots, deduplicated
```

The one difference that bites: records in this corpus carry an `instrument` field and records
in `data/` mostly do not. Code that filters on `instrument == "ratchet-battery"` will silently
drop the entire previous corpus, and code that does not filter will silently pool two
instruments. `floor_table._instrument_matches` is the rule the analysis uses.

Field by field, see [`../DATA-DICTIONARY.md`](../DATA-DICTIONARY.md).

## Where the defects are written down

[`../CORRECTIONS.md`](../CORRECTIONS.md) is the numbered ledger: every figure this study has had
to withdraw or restate, with the record that withdrew it.
[`../data/withdrawals.json`](../data/withdrawals.json) is the machine-readable registry of the
same thing, and `scripts/check_withdrawals.py` is the gate that keeps each withdrawal withdrawn,
including the clause that fails if the evidence for one is ever deleted.

## What is not here

[`../MANIFEST.json`](../MANIFEST.json) lists every directory the export keeps back, with the
reason: the refusal-ablation series, whose prompts are XSTest's (a third party's text), and the
development fixtures of 2026-09-08.
