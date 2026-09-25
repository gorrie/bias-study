# Wave 0: the barometer's first sitting

**Collected** 2026-09-05 into 2026-09-06, one sitting, `runs/2026-09-05-wave/`.
**Panel** 31 models x 4 conditions = 124 cells, 5 runs each = 620 runs.
**Verified** `python scripts/wave.py --verify` — no parameter drift, five distinct seeds in
every cell.

This is the first point on a time axis that did not exist. Everything before it is a
cross-section: `runs/2026-08-31-lineage` compares claude-opus-4.1 against 4.5 against 4.6 at one
instant, which answers "do releases differ", not "did this model change". You cannot measure the
past later, so the value of this file is mostly that it is dated.

## What it is

The panel was frozen on corpus coverage — a model is in it if the corpus already held it under
both surviving conditions — **before any answer in it was read**. That matters more than the
size: selecting a panel on how models answer would build a time series on a sample chosen for
its answers, which is the defect this project exists to point at.

Conditions: A (balance instruction), B (bare ask), D (commit), P (content-free placebo). D and P
carry the position series at 0.7% refusal; A and B carry the refusal series at 9.8% and rising.

Frozen parameters, gated by `--verify`: temperature 0.7, seed sweep from 20260830, max_tokens
8192, template T01, 5 runs.

## What it changed

The corpus went from 2,126 runs to 2,896 — a 36% increase, and 58% in the matched-arm subset
that §1's headline is computed over. Three published numbers moved and the claims behind them
held:

| quantity | before | after |
|---|---:|---:|
| models measured under both arms | 32 | 42 |
| no-directive refusals / runs | 91 / 732 (12.4%) | 153 / 1096 (14.0%) |
| directive refusals / runs | 3 / 541 (0.55%) | 4 / 917 (0.44%) |
| models declining in BOTH arms | 0 | **0** |
| order-effect MDE, side-flips, 80% power | 13 items | **13 items** (unchanged) |

**The paired statement survived**: of the 14 models that decline without a directive, all 14
stop when given one, no exceptions. The four that decline only under a directive are now
identifiable as a single weights family — `llama3.1:8b`, `llama3.1:8b-instruct-q8_0`,
`llama3.2:3b-instruct-q8_0`, `llama3.2:latest`, one run each. The paper had described them as
"small local builds", which was true and less useful; they are Llamas.

The order MDE did NOT move: 13 before, 13 after. An earlier version of this file said it
tightened to 12, which contradicted `RESULTS-2026-09-06-order-dependent-floors.md` and the
paper on the same day — two records of one afternoon disagreeing about a number both were
generated near. Corrected 2026-09-06 against `power.py`, which reports 13.

## Two defects this wave found in the collector

Both are the same mistake in two places — **a count that cannot tell PRESENT from FINISHED** —
and neither raised anything. Both produced data that looked complete.

**1. Resume restarted the seed sweep.** `run_battery.py` resumes correctly: it counts valid runs
on disk and asks only for the shortfall. Then the collection loop restarted at `run_no = 1`.
Under `--seed-sweep` the seed is a position in a sequence (run k carries `seed_base + k`), so a
cell interrupted after two runs re-issued `seed_base + 0` and `+ 1` — the two it already had.

At temperature 0.7 a repeated seed is not a repeated call, so nothing looked wrong: the records
differ, the cell reaches five, `valid` counts five. It is n=3. **11 of 124 cells** held five to
seven records across three or four distinct seeds, every one a cell some interrupted chunk had
resumed. Fixed by selecting the next UNUSED sweep positions rather than offsetting by a count —
offsetting is right for a clean resume and collides again while repairing a damaged cell.

**2. `wave.collected()` counted records while `--verify` counted seeds.** So the gate could name
the damage and the collector could not reach it: `--verify` called eleven cells short, `--run`
saw five records in each and skipped every one. A cell is only repairable by the thing that
decides what is left to do, so it now counts the same way.

**And the same shape a third time**, found while fixing the first two: the wave-is-a-sitting
check read `len(collected(...))`, the number of cells holding *any* data. All 124 held data
while 11 were short, so at 00:0x on 2026-09-06 it opened a second wave directory mid-repair and
billed six duplicate cells before it was caught. They were parked in a retired directory for
half a day and then deleted: every one duplicates a cell already complete in the wave, at seeds
those cells already carry, so they could not be merged and contributed to no arm. Keeping the
wreckage of a tooling bug as though it were data is how a corpus fills with directories nobody
can explain. The bug is recorded here; the six cells are not.

All three are pinned by `scripts/test_wave_seeds.py`, and the bias-study unit tests are now in
CI — they never were, which is the "gate nobody runs" failure `test_analysis_plumbing.py`'s own
docstring is a list of.

## One arithmetic error, found by deriving a number instead of retyping it

The controls audit's `ours` row describes this study's own scale, and it had gone stale again
(2,126 vs 2,896). Rather than retype three numbers this module already computes, it is now
written by `key_numbers.py --sync-ours`.

Making it derived surfaced the error. The paper said "Three of those sixteen keys are not
vendors", named them, and then said "Twelve rows are vendor families" in the next sentence.
Sixteen minus three is thirteen. The wrong subtraction had been copied into the audit row — our
own self-description, in the table that scores five other studies for not saying what they
pooled. Every other number in that paragraph was gated; that one was prose, so it drifted alone.
It is gated now (`corpus_vendor_families`).

## What this does not tell you

Nothing about change over time. One point is not a series. The first interval arrives with wave
1, which needs a month of separation to be worth anything — the floors say presentation order
moves 11 items and the same prompt twice moves 5, so a wave collected a week apart would mostly
measure those.

The panel is fixed from here. Models added later join with a shorter series and cannot
contribute to the wave 0 -> 1 interval, which is why the collection was carried to all 124 cells
rather than frozen at the 21 models that were complete when the slow half was still running:
stopping there would have dropped every x-ai and every z-ai model, including `grok-4.3`, which
carries one of the only two effects that survives every judge in the lean analysis. A smaller
panel would have been fine. A panel with two vendors missing is a differently shaped one, and
every later wave would have inherited the shape.
