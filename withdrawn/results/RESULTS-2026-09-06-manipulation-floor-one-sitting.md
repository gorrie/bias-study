# The reference scale, re-measured under one protocol

**Question:** the paper's reference scale — how far a deliberate political manipulation moves a
model — was pooled across collections. Re-collect it under one protocol, in one sitting, at
n=5, and see whether it holds.

**Answer:** it does not hold. It gets **smaller**, and the paper's central comparison gets
sharper. p90 **15 → 7**, over more pairs.

**No new collection was needed.** Wave 0 had already done it.

## The two rows

| row | pairs | side-flip med / p90 / max | p90 95% CI | protocol |
|---|---:|---|---|---|
| `prompt condition A->D` | 20 | 3 / **15** / 19 | [5, 19] | temp 0, 3 runs, several dates |
| `prompt condition A->D, one sitting` | 25 | 3 / **7** / 14 | [4, 12] | temp 0.7, swept seed, 5 runs, one sitting |

Against the nuisance floors, in the same units:

| factor | pairs | side-flip p90 |
|---|---:|---:|
| presentation order | 84 | 11 |
| same-version variants | 97 | 11 |
| **deliberate manipulation, one sitting** | **25** | **7** |
| instruction paraphrase | 1067 | 6 |
| run-to-run replicate | 63 | 5 |

**Reordering the questionnaire and swapping which variant of a model you measured each move
more items than the deliberate political manipulation does.** 23 of the 25 models move 8 items
or fewer under an instruction written to push them. The tail is `grok-4.6` at 14 and `grok-4.3`
at 12 — the same vendor that carries the tail of the pooled row.

Six panel models contribute no pair because they decline condition A outright: `claude-fable-5.1`,
`gemini-3.7-flash`, `gemini-3.8-flash`, `gpt-6-astra`, `gpt-6-astra-pro`, and the gemma-4-12B
GGUF build. That is section 1's finding, not a gap here.

## Why the two rows differ, stated rather than chosen between

At temperature 0 with a fixed seed a cell's runs are near-identical, so its "modal" sheet is
effectively a **single observation** carrying single-run noise straight into the comparison. In
the one-sitting arm the modal is a real consensus across five different seeds, so that noise
averages out and what remains is the position.

So the pooled row is an **upper bound inflated by noise it could not average away**, and the
one-sitting row is the better estimate of the quantity the paper actually compares: whether the
instruction moves the model's central position. Both rows are printed. Neither is deleted.

## The comparison is like-for-like, which had to be checked

A manipulation measured between two 5-run consensus sheets, compared against nuisance floors
measured between single runs, would be rigged in our favour — averaging shrinks the measured
movement, so the effect we are arguing is small would be small by construction.

It is not rigged, and the check is one line of each function:

- `floor_order` pairs `modal(runs)` per item order — consensus vs consensus.
- `floor_same_version` pairs `modal()` per variant — consensus vs consensus.
- `floor_conditions_wave` pairs `modal()` per condition — consensus vs consensus.
- `floor_replicate` pairs **raw runs**, correctly, because raw run-to-run noise is the thing it
  measures. It is the only row that should not be a consensus, and it is not.

## What was collected, and what was not

Nothing. The open item after wave 0 read "re-collect the manipulation floor under one protocol,
one sitting, n=5 — roughly 260 calls." Wave 0 ran all four conditions for all 31 panel models
at n=5 in one sitting, which **is** that collection; it was queued as separate work because the
task list predated the wave and nobody re-read it against what the wave contained.

Worth noticing as a pattern rather than a one-off: this project has now twice collected data and
then not read it — 27 frontier order runs that contributed nothing to the order floor for a week,
and this. Collecting and not reading is the same defect as measuring the source instead of the
artifact, one step earlier.

## Gates

`floor_conditions_wave()` is generated into the paper's floors table, and three of its numbers
are gated in `key_numbers.py`: `manip_p90_sitting`, `manip_pairs_sitting`,
`manip_refusing_sitting`, plus `wave_panel_size`.

The floor list itself was duplicated — once in `floor_table.main()` and once in
`key_numbers.floors()` — so adding this row to the table left the gate blind to it. A new row
could have appeared in the paper with nothing recomputing the prose around it, which is the one
thing that gate exists to prevent. There is now one list, `floor_table.ALL_FLOORS`, with two
readers.
