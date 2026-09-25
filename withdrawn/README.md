# `withdrawn/` — evidence for the withdrawals, kept where the registry can find it

`withdrawn/` means out of the panel. Nothing under it reaches a computed number: every
directory here is excluded from the `runs/**` globs by construction, and no analysis reads it.
It is kept because [`../data/withdrawals.json`](../data/withdrawals.json) cites what is here as
the evidence for withdrawals, and `scripts/check_withdrawals.py` fails if any of that evidence
goes missing. A withdrawal whose evidence has been deleted is a claim about a claim.

| directory | what it holds | why it is here |
|---|---|---|
| [`backend-split-precollection/`](backend-split-precollection/README.md) | 40 sheets, 196 records on the live battery, 10 models, collected 2026-09-16 to 2026-09-20 over OpenRouter before backends were pinned | the same model was served by two to four backends inside one arm, so a condition difference across these sheets is a difference between serving stacks. They are the confound that `PREREG-2026-09-14-i3-phase4.md` item 3 was written to remove; the re-collection is in `runs/` |
| [`pre-repair-snapshots/`](pre-repair-snapshots/README.md) | 73 wave records as they stood before two documented repairs: 45 records of Gemma-4-12B and llama3.1:8b sheets that the first parser read as unanswered, and the 28 records of the `z-ai/glm-5.2` cell as collected before its single-backend re-collection | the before-state of [`../CORRECTIONS-2026-09-17-labels.md`](../CORRECTIONS-2026-09-17-labels.md) and of the `z-ai/glm-5.2` re-collection, so both corrections can be checked against the records they changed |
| [`results/`](results/README.md) | thirty-nine results documents whose findings this study later withdrew or narrowed, kept with their original text | each is cited by the withdrawals registry or by the paper as the record of what was claimed and when |

The records here are the author's own, on the author's own instrument, and ship under the same
MIT licence as everything else. They are not a corpus, not an arm, and not comparable to
anything in `runs/`.

## What is not here

The study administered a 62-item external questionnaire between late August and 2026-09-16.
That text is a third party's licensed work, so neither it nor any record collected on it is in
this repository; the claims measured on it are withdrawn and listed in
[`../CORRECTIONS.md`](../CORRECTIONS.md), and the figures they quote cannot be recomputed here.
The private study tree also keeps superseded plans, status files and a further 36 superseded
results documents under its own `withdrawn/`; those are process records, not results, and the
paper depends on none of them.

## How to load it

The sheets in `backend-split-precollection/` and `pre-repair-snapshots/` are JSON Lines in the
battery layout (`<model>__<condition>.jsonl`, one record per sheet, schema `battery-run/1` or
the older `compass-run/1`), documented field by field in
[`../DATA-DICTIONARY.md`](../DATA-DICTIONARY.md). Read them directly; `studypaths.run_path`
does not resolve them, on purpose.
