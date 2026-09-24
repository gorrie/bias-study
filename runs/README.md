# `runs/` — the current study's corpus

**This directory is the study the paper is about.** Every run here was collected on the
**Ratchet battery** — 32 forced-choice items in 16 mirrored pairs, written by Ian Gorrie,
MIT-licensed and published in full at `data/ratchet-battery.json`. There is no fetch step and
no third-party item text to withhold.

Everything collected *before* this instrument is in **`data/`**, which has its own README.
**The two roots are different corpora, not two names for one thing.** That was always true of
this release; until 2026-09-23 the private working tree kept both under `runs/`, so the same
tooling meant different things in the two checkouts. It no longer does.

The inventory below is generated from the records themselves. Do not edit it by hand.

## What is here

<!-- GEN:corpus-inventory-runs -->
| run | records | models | instrument | status | read by |
|---|---:|---:|---|---|---|
| `2026-09-16-ratchet-v3-wave` | 3,897 | 65 | `ratchet-battery` | active | runs/*-wave/*.jsonl, named in a script, named in a document |
| `2026-09-16-ratchet-v3-wave-budget-probe` | 71 | 71 | `ratchet-battery` | active | named in a script |
| `2026-09-18-bce-smoke` | 7 | 2 | `ratchet-battery` | active | named in a script |
| `2026-09-18-omission-hosted` | 864 | 18 | `ratchet-battery` | active | named in a script, named in a document |
| `2026-09-18-omission-orders` | 240 | 5 | `ratchet-battery` | active | named in a script, named in a document |
| `2026-09-18-paraphrase` | 448 | 46 | `ratchet-battery` | active | named in a script, named in a document |
| `2026-09-18-roster-smoke` | 22 | 22 | `ratchet-battery` | active | named in a script, named in a document |
| `2026-09-19-rung2-elicitation` | 280 | 7 | `ratchet-battery` | active | named in a script, named in a document |
| `2026-09-19-rung2-smoke` | 3 | 1 | `ratchet-battery` | active | named in a script |
| `2026-09-20-omission-hosted-pinned` | 384 | 8 | `ratchet-battery` | active | named in a script, named in a document |
| `2026-09-20-rung2-control-v2` | 70 | 7 | `ratchet-battery` | active | named in a script, named in a document |
| `2026-09-21-omission-nemotron-phala` | 48 | 1 | `ratchet-battery` | active | named in a script, named in a document |
| **12 directories** | **6,334** | | | | |
<!-- /GEN:corpus-inventory-runs -->

`instrument` is read off each record's own `instrument` field, not inferred from the
directory's name or date. `status` comes from `data/withdrawals.json`.

## What you may conclude from it, and what you may not

**May.** The wave — `2026-09-16-ratchet-v3-wave`, 3,897 runs across 65 models — is the corpus
behind every floor in the paper: the order floor, the modal sampling floor, the same-version
floors. The smaller dated runs are targeted extensions of one factor each (omission,
paraphrase, elicitation rung), and each is named in the paper section that uses it.

**May not.** Nothing here is judge-scored. The battery is forced-choice and is read
positionally; there is no rubric, no LLM judge and no 1–5 score in this corpus. The
judge-scored study is the previous instrument's, in `data/`, and the two are not comparable —
**no figure computed from 32 items may be set beside one computed from 62.** Side-flip counts
are not linear in item count, and treating them as if they were is the specific error this
study is organised against.

Several directories here hold three to twenty-two records. They are smoke runs — a roster
check, a budget probe — and they are kept because deleting the evidence that a collection was
configured correctly is not how this project handles its own record. They are not results.
The `read by` column tells you which are reached by an analysis and which are not.

## How to load it

Records are JSON Lines, stored flat in the run directory for this corpus. Resolve a run by
NAME rather than by spelling a path — the resolver searches both corpus roots:

```python
import sys; sys.path.insert(0, "scripts")
from studypaths import run_path, all_run_dirs

d = run_path("2026-09-16-ratchet-v3-wave")   # resolves in whichever root holds it
everything = all_run_dirs()                   # every run, both roots, deduplicated
```

**The one difference that bites:** records in this corpus carry an `instrument` field and
records in `data/` mostly do not. Code that filters on `instrument == "ratchet-battery"` will
silently drop the entire previous corpus, and code that does not filter will silently pool two
instruments. `floor_table._instrument_matches` is the rule the analysis uses.

Field-by-field, see **`DATA-DICTIONARY.md`** at the repository root.

## Where the defects are written down

Read them from us first. **`CORRECTIONS.md`** is the numbered ledger — every figure this study
has had to withdraw or restate, with the record that withdrew it.
`data/withdrawals.json` is the machine-readable registry of the same thing, and
`scripts/check_withdrawals.py` is the gate that keeps each withdrawal withdrawn, including the
clause that fails if the evidence for one is ever deleted.
