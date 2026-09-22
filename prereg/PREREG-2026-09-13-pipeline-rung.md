# Pre-registration: rung 2 of the escalation ladder, re-collected with replicates

**Written 2026-09-13, before any call is made.** The predictions below are the point; the commit
carrying this file is what makes them checkable.

## Why this arm is being re-collected

`README.md` publishes rung 2 of the force-escalation ladder as *"only the layered stack adds
force, to a ceiling."* Nothing computed that. `runs/2026-05-27-g0dm0d3/ANALYSIS.md` has a heading
for every table and rows under none of them, because `analysis.py` keys on conditions A and B and
this arm runs `B-STM`, `B-Parseltongue` and `B-Layered`. The records matched no branch and
produced empty tables.

`scripts/pipeline_rung.py`, written 2026-09-13, estimates the arm from the existing 60 records.
**Not one of its eight intervals excludes zero:**

| model | contrast | n | effect | 95% |
|---|---|---:|---:|---|
| claude-opus-4.7 | B-STM vs plain B | 10 | +0.00 | [−0.30, +0.30] |
| claude-opus-4.7 | B-Parseltongue vs plain B | 10 | +0.00 | [−0.30, +0.30] |
| claude-opus-4.7 | B-Layered vs plain B | 10 | −0.10 | [−0.50, +0.30] |
| claude-opus-4.7 | B-Layered − B-STM | 10 | −0.10 | [−0.50, +0.30] |
| grok-4.3 | B-STM vs plain B | 10 | −0.20 | [−0.60, +0.20] |
| grok-4.3 | B-Parseltongue vs plain B | 10 | −0.10 | [−0.40, +0.20] |
| grok-4.3 | B-Layered vs plain B | 10 | +0.40 | [+0.00, +0.80] |
| grok-4.3 | B-Layered − B-STM | 10 | **+0.60** | [+0.00, +1.20] |

The published direction rests entirely on the last row, whose lower bound sits on zero.

## Two defects in the original design, both fixed here

1. **One sample per cell.** There is no within-cell variance to appeal to, and single-draw noise
   inflates the paired dispersion — sd 1.07 on the grok contrast. `run_g0dm0d3.py --samples`
   already exists and defaulted to 1. **Five samples per cell.**
2. **The baseline is cross-protocol.** Plain condition B comes from `2026-05-25-full` and the
   pipeline conditions from `2026-05-27-g0dm0d3`, so the contrast confounds elicitation with
   two days and a different collection path. **Plain B is collected in the same sitting.**

The instrument is fixed at 10 questions; adding items would change it. Replicates and a
same-sitting baseline are the only honest levers.

## Design

2 models × 4 conditions (`B`, `B-STM`, `B-Parseltongue`, `B-Layered`) × 10 questions × 5 samples
= **400 calls**. Hosted models through the G0DM0D3 server; no GPU.

**Record the G0DM0D3 build actually used** — repository, commit and any local modifications — in
the run manifest. The README pins `elder-plinius/G0DM0D3` `4d4b3e0` as the provenance of the MAY
data. That is a record of what produced those records, not a requirement on this collection. If
a different build is used, the manifest says so and the analysis reports both.

## Predictions, committed

1. **Claude Opus 4.7 stays flat.** Its two single-technique arms measured exactly +0.00 against
   baseline, which is not a small effect, it is nothing. Predicted: all three Claude contrasts
   span zero at n=5.
2. **The grok layered effect shrinks below +0.60.** An estimate sitting on its own zero bound is
   usually an overestimate. Predicted: the point estimate falls, and whether the interval clears
   zero is the open question.
3. **The single-technique arms add nothing on either model.** Four of the four measured
   single-technique contrasts are between −0.20 and +0.00 today.
4. **No ceiling is located.** Three points on one axis cannot find where added force stops
   helping, at any n. If a ceiling is to be claimed it needs a dose series, which is a different
   arm and is not this one.

Prediction 2 failing — grok holding at +0.60 with a clean interval — makes rung 2 a real but
**model-specific** effect, not the general claim the README made.

## Decision rules, fixed now

- **Eligibility applies at read time** (`scripts/eligibility.py`). An incoherent or empty
  response is excluded and counted, never scored as maximum skepticism. The coherence guard
  matters more here than anywhere else in the study: layered obfuscation degrades output past a
  functionality ceiling, and a broken response must not read as a confident answer.
- **The estimator is `scripts/pipeline_rung.py`,** unchanged, extended only to average replicates
  within a cell before differencing. Per-question pairing is preserved; samples within a cell are
  averaged, not treated as independent observations.
- **Both directions publish.** A null at n=5 retires rung 2 from the ladder and the README says
  the ladder has two measured rungs and one that did not replicate. That is a publishable result
  and the better one for the paper's credibility.
- **No third collection.** If n=5 leaves the grok contrast ambiguous, it is reported ambiguous
  with its interval. Collecting until an interval cooperates is the failure this study exists to
  indict.
- **The README row is corrected NOW, before this runs.** The current claim is unsupported by the
  data that exists today, and leaving it up on the strength of data that might be collected is
  the failure mode. If this arm supports a direction, the row is updated again.

## Cost

400 hosted calls, one sitting, no GPU, no new models, no instrument change.
