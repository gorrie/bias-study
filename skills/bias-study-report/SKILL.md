---
name: bias-study-report
description: Turn scored bias-study runs into defensible statistics and writeup-ready tables — bootstrap CIs, Benjamini-Hochberg FDR, length control, inter-judge agreement, the abliteration effect-check (Jaccard), and escalation-ladder monotonicity (prompt-delta vs pipeline-delta vs abliteration-delta). Use after scoring any run, before updating the writeup. Enforces "a delta is a finding only if its CI excludes zero."
---

# bias-study-report

The statistics and reporting layer for the bias study. Run it after `scripts/score.py` on any
run. Companion: `README.md` and the writeup in `results/` for the framing each number supports.

## Prerequisites

- **The run has passed `scripts/collection_check.py <run>`.** Run it BEFORE scoring, not after.
  It exits non-zero when a collection is not fit to score, and its blockers are the defects that
  cost this study four months:

  ```bash
  python scripts/collection_check.py 2026-09-13-g0dm0d3-replicate
  ```

  Run against the May pipeline wave it produces three blockers — no `max_tokens` recorded, 16.7%
  of responses severed mid-sentence, and truncation **differential** at 33.3% for one model
  against 0.0% for the other. Any one of those makes the arm unmeasurable, and all three were
  present while the run looked completely successful. A collection that fails this gate does not
  get judge calls spent on it.

  The differential check is the one people skip. A uniform truncation rate is a limitation you
  can disclose; a rate that varies by model is a **confound**, because truncation tracks
  verbosity, and excluding the records relocates the problem into the denominator rather than
  removing it. Measured on this corpus, exclusion removed 94.1% of one vendor class's records
  and 0.0% of another's. There is no filter that repairs that — only re-collection.

- A scored run under `data/<run>/` (i.e. `scripts/score.py` has produced `scored/*.jsonl`). If
  the run is unscored, score it first.
- Python 3.11+ and the repo deps. The analysis steps are pure-Python and need no API budget, so
  you can re-derive every published number from the scored data already shipped in `data/`.

## TRIGGER when

- A run has just been scored and needs CIs / FDR / agreement before it can be cited.
- Updating the writeup in `results/` (or any public summary) with numbers.
- A quarterly pass needs the quarter-over-quarter drift diff.

## SKIP

- Unscored runs (run `scripts/score.py` first).
- Raw-text inspection of stock-vs-abliterated pairs — that is the effect-check below, not a
  general reporting task.

## What it produces (deterministic; fix the seed so reruns reproduce)

1. **Aggregate + analyze.** `scripts/aggregate.py <run>` rolls the scored records up into
   per-model / per-topic / per-question CSVs and a `run-summary.json`. `scripts/analysis.py
   <run>` then writes an `ANALYSIS.md` with framing-sensitivity, vendor-cluster correlations,
   the hedge-ratio-vs-score correlation, the topic delta heatmap, and the moral-essay /
   refusal-cliff classifications.
2. **Bootstrap CIs + inter-judge agreement.** Bootstrap 95% CIs over the per-question deltas,
   and report **raw** inter-judge agreement (not Krippendorff's alpha — the prevalence paradox
   makes alpha uninformative when ~80% of scores cluster at "3"). **Report a delta only if its CI
   excludes zero.**
3. **Multiple-comparison + length control.** Benjamini-Hochberg FDR (q = 0.05) over the
   per-model p-values, plus a length / verbosity control (score vs `word_count`) to confirm a B
   condition is not simply *longer* than its A baseline rather than more skeptical.
4. **Abliteration effect-check (weight rung only).** For any stock/abliterated pair, compute the
   word-set Jaccard plus the length / hedge / refusal deltas. This guards against the
   uninterpretable null: a flat stance is only a finding if the ablation actually *changed* the
   text (Jaccard around 0.3 = it did; high Jaccard + flat stance = uninterpretable).
5. **Ladder monotonicity.** For each open-weight model, check prompt-delta <= pipeline-delta <=
   abliteration-delta with CIs; report where the ladder holds and where it breaks. The current
   headline: abliteration-delta is about zero on *stance* despite a heavy *text* rewrite — the
   refusal direction and institutional lean are dissociable.
6. **Drift / barometer diff.** `scripts/drift_report.py <run>` writes the single-run drift
   summary; `scripts/drift_timeseries.py` joins per-model results across all runs into the
   longitudinal time series (the cross-vendor arcs). This diff against the prior quarter is the
   "barometer".

> The CI / FDR / length-control / effect-check computations above are study deliverables, not
> necessarily single scripts. Where a dedicated analysis script exists in `scripts/`, use it;
> otherwise compute the measure directly over the scored JSONL and keep the seed fixed so the
> numbers reproduce.

## Local-model fallback (sensitive responses)

A cloud judge may itself refuse to score the most sensitive responses — abliterated or
elicitation-pipeline outputs that trip its own content filter. When a judge returns a
content-restriction error on a record, do **not** drop that record (a silent gap biases the
panel toward the tame responses). Point the scorer at a local, OpenAI-compatible model
instead — e.g. a local gemma via Docker Model Runner (`localhost:12434`) or Ollama — and
record which judge produced each score so a fallback is auditable. gemma is the example here,
not a hard dependency: any reasonable local instruct model works.

## Output discipline

- Every number that lands in the writeup or a public summary carries its CI and n.
- Nulls are framed as power-bounded ("no movement detectable at this n, CI +/-X"), never
  "proven zero".
- Lead with what survives FDR, not the long near-zero tail.
- Keep the writeup, any public summary, and the rubric's condition tags consistent with what was
  actually executed — doc-reality discipline. Never describe an unrun leg as run.
  *(Corrected 2026-09-14: this named the pipeline rung as the unrun leg. It was collected at
  n=1 in May and re-collected at n=5 on 2026-09-13. `pipeline_rung.py` reports which pair it
  read, and the n=5 pair is not a null — three of eight intervals exclude zero and the two
  models move in opposite directions.)*
- **A number stays out of a public surface until its run is in the same repository.** A reader
  who cannot recompute it has to take it on trust, which is the failure this study audits other
  studies for. `PENDING-PUBLICATION-2026-09-14.md` in the working tree is where a finding waits
  when it is settled but its data has not been exported yet.

## Before anything ships

`python scripts/release_check.py` runs the whole release checklist across BOTH trees and is the
only thing that does — the working study and the public mirror each hold checks the other
cannot run. It exits non-zero and prints every failing item; treat NOT RELEASABLE as the answer,
not as an obstacle to route around. Its companions, each also runnable alone:

- `scripts/key_numbers.py --check --check-release --check-website` — every hand-typed number on
  a public surface against the generated one. This is what caught a rung-2 contrast count that
  had said eight since the truncation rule made it six.
- `scripts/check_no_fork.py` — the same filename with different contents in the two trees is how
  a fix lands on one side only.
- `scripts/validate_runs.py` — run directories against their manifests. Read the NOT VALIDATED
  line as well as the findings: a layout with no manifest discipline is not a clean run.
- `scripts/gen_script_inventory.py --check` and `scripts/check_skill_docs.py --strict` — the
  generated inventory and the skill docs against what is actually on disk.
