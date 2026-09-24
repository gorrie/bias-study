# Pre-registration — do the wave's dropped partial sheets move any floor?

**Registered 2026-09-24, before any sheet in this arm is collected.** Nothing in it may be
amended after the first call; an amendment made after data exists is recorded as an
amendment, dated, with the reason, and the original text is left standing.

**Authorised by the author 2026-09-24** ("do the recollection and we'll wait for it to
proceed"). It breaks the corpus freeze of step B for one new directory. It rewrites no
record in any existing run.

---

## Why

The main wave, `runs/2026-09-16-ratchet-v3-wave`, was collected across the 2026-09-18
renumbering. **104 of its sheets came back with some but not all 32 items answered**, from 13
models, and every one is excluded as invalid; 93 are from six local builds. All 104 carry
the as-is numbering. The paper (§6b) states the loss and states that *"whether any floor would
move under a renumbered re-collection cannot be established from this corpus, because a
dropped sheet has no value to compare."*

The drop is not random. §6b's own finding is that the as-is numbering makes a susceptible model
silently omit items, and that the renumbered protocol does not. Dropping partial sheets whole
therefore conditions each affected cell on the runs the model chose to complete. **Seven cells
lost every sheet** (`huihui_ai/qwen2.5-abliterate:14b` A, B, C, E, N; `qwen2.5:14b` C), so
those models are absent from those cells, not merely thinner.

This arm makes the unknown a measurement.

## What is collected

**Every record of every affected cell, one for one, with one change: `--renumber` (protocol
v2).** An affected cell is a (model, condition) of the wave holding at least one partial sheet
— 34 cells, 13 models, **369 records** (275 local, 94 hosted), counted from the frozen wave by
`scripts/recollect_partials.py --plan`.

The whole cell is re-collected, never only its missing sheets. Filling a cell's gaps with
renumbered sheets beside as-is ones would put two protocols in one cell and confound the
numbering change with the floor, which is the defect that withdrew the rung-2 position claims.

Held fixed, per group of (model, condition, presentation order): the model and channel, the
condition, the shuffle seed, temperature 0.7, template T01, reasoning off on local builds,
and the number of records. The completion budget is the protocol's 40,960 for every group:
120 wave records carried 32,768, a deviation already declared and none of them truncated, and
one budget per group is what lets the collector key the group as one cell. Hosted groups are **pinned** to the
backend that served the original records (`provider_pinned`, else `provider`), fallbacks off.
Seeds are a fresh consecutive sweep from the group's lowest original seed, so every sheet in a
group has a distinct seed — the wave held 34 duplicate call keys in these cells, which this
arm does not reproduce.

**No top-up.** Each group is collected in one invocation and never resumed to fill a shortfall:
`run_battery`'s resume counts valid sheets, so resuming would re-draw a partial sheet until it
came back whole, which is the selection this arm exists to measure. A sheet lost to transport
is a declared loss. The directory is `runs/2026-09-24-partials-renumbered`.

**Not inside any published arm.** Before the first call the run is named in
`floor_table.ORDER_EXCLUDE` and `refusal_table.OUT_OF_PANEL`, and the published figures are
shown unchanged by it: `floor_table --markdown`, `power --markdown`, `refusal_table`,
`key_numbers --counts` and `key_numbers --check`, diffed against a snapshot taken before the
registration.

Known and not controlled: local builds are served by the current Ollama tags, which are not
digest-pinned in the wave's records, so a tag re-pulled since 2026-09-16 is a different build
under the same name.

## The test

`scripts/partials_sensitivity.py` runs the **unmodified** `floor_table` twice:

1. on the frozen tree — the published floors, and
2. on a scratch copy of the tree in which every record of the 34 affected cells in the wave is
   replaced by this arm's records for the same cells. Nothing else differs.

**Decision rule.** A floor row **moves** if its side-flip p90 in (2) falls outside the 95% CI
that (1) prints for that row. Rows that exist only in (2) — cells that had no valid sheet
before — are reported as new rows, not as moves. Median, max, the endpoint statistic and the
pair count are reported for every row either way; only p90-outside-CI is called a move.

**Secondary, descriptive.** The partial-sheet rate in these cells under each protocol, with a
one-sided Fisher exact test in the direction §6b registered (as-is loses more). It is not the
question — these cells were selected *because* they lost sheets, so the as-is rate here is
inflated by construction and says nothing about the panel's rate.

## What each outcome does

- **No row moves.** §6b replaces "cannot be established from this corpus" with the measured
  result: re-collecting every affected cell renumbered moves no floor outside its interval.
- **Any row moves.** The paper reports the substituted row beside the published one for every
  row that moved, and §9 gains the limitation. **The published floors remain the frozen
  wave's** — this arm is a sensitivity analysis, not a replacement corpus. Whether to rebase
  the headline on it is the author's call, made after the numbers, and recorded as such.

Either way the counts are registered in `key_numbers.py` and gated.
