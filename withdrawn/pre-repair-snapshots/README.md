# Pre-repair snapshots — 73 records, the before-state of two documented repairs

**Extracted 2026-09-22 by `scripts/extract_backup_uniques.py`.** These are the only records
from the gitignored working backup `runs-backup-20260917-225458/` that existed nowhere else.
That backup held 39,201 records; 39,128 were already byte-identical to a record in `runs/`
once the `compass-run/1` → `battery-run/1` schema rename was set aside. These 73 were not.
The backup was deleted once this directory was committed and verified to cover it.

| file | records | what it is |
|---|---:|---|
| `2026-09-16-ratchet-v3-wave/hf.co__lmstudio-community__gemma-4-12B-it-GGUF_Q4_K_M__{A,D,N,P}.jsonl` | 38 | sheets stored `valid: false / failure_mode: other` that re-parse as complete |
| `2026-09-16-ratchet-v3-wave/llama3.1_8b__N.jsonl` | 7 | same, plus three records still labelled `ratchet-battery-v3` |
| `2026-09-16-ratchet-v3-wave/z-ai__glm-5.2__{A,D,N,P}.jsonl` | 28 | the cell as collected 2026-09-16/18, before the single-backend re-collection replaced it |

## Why they are kept

They are the **evidence for two corrections the study has published**, and a withdrawal whose
evidence has been deleted is a claim about a claim.

1. **`CORRECTIONS-2026-09-17-labels.md`.** `run_battery.parse_answers` required an item number
   and its chosen option on one line. `llama3.1:8b` and `gemma-4-12B` answer with them on
   separate lines, so the parser read zero answers from sheets that had answered every item,
   and `classify_failure` — seeing a non-empty body, no truncation and no answers — labelled
   them refusals. The correction re-derived the labels. Against these snapshots the claim it
   makes is checkable: same `collected_at`, same seeds, only derived fields move.

2. **The `z-ai/glm-5.2` re-collection, 2026-09-20.** That cell was replaced rather than merged
   when it was re-run against one pinned backend — the routing-confound repair
   `PREREG-2026-09-14-i3-phase4.md` line 3 calls for. These are the records it replaced.

## What they are not

Not a corpus, not an arm, not comparable to anything in `runs/`, and out of every `runs/**`
glob by construction. No analysis reads them. `data/withdrawals.json` names them as evidence
and `scripts/check_withdrawals.py` fails if they go missing, which is the protection this
directory has that `withdrawn/backend-split-precollection/` did not have on the morning it
was deleted for sitting in the wrong-looking folder.
