---
name: cross-method-analysis
description: Consume the outputs of all judgement-tool methods (the 4 API-based ones from api-judge-sweep + Method 2 from abliterated-judge-sweep) and produce the cross-method contamination-delta tables, per-record disagreement plots, and the headline "consensus is/isn't robust" verdict. Use after both sweep skills have completed; this is what feeds the writeup section and the public permalink.
---

# cross-method-analysis

The pre-registered comparison. For each record, we have up to 5 scored versions (the
ULTRAPLINIAN-4 primary + four/five judgement-tool methods). The deltas between them
quantify how much of the headline numbers depend on the choice of judge.

The pre-registered rule (`RUBRIC-SCORES.md`, locked before any sweep ran):

> If the median absolute delta between Method M and ULTRAPLINIAN-4 across all records is
> ≤ 0.10 (on the 1–5 scale), the original consensus is robust to that bias-source.
> If it exceeds 0.10, the original consensus carried that bias.

The anchor method is selected mechanically by the rubric (highest implementable score),
not by post-hoc choice. Currently Method 2 (`abliterated-gemma`, rubric 4.10) is the anchor.

## TRIGGER when
- All five judgement-tool methods have scored data on the same run set (verify with the
  integrity check in step 1).
- Time to produce the contamination-delta table for the writeup section.
- Re-running the analysis after a re-score or after adding a new method.
- Author asks to "run the cross-method report", "generate the contamination delta", "make
  the charts", or "fill in the writeup numbers".

## SKIP
- A single method is incomplete — the cross-method table will have gaps and mislead.
  Re-run the missing sweep first (see `abliterated-judge-sweep` / `api-judge-sweep`
  recovery sections).
- The primary `scored/` directory doesn't exist — there's nothing to compare against.
  Run `score.py` (ULTRAPLINIAN-4) first.

## Preconditions
1. `scripts/cross_method_report.py` and `scripts/generate_charts.py` present (since commit
   9935d0a). Update via `git pull` if not.
2. For each run you care about, `runs/<date>/` has:
   - `scored/` (the ULTRAPLINIAN-4 primary)
   - `scored-abliterated-gemma/` (Method 2)
   - `scored-grok-solo/`, `scored-adversarial-pair/`, `scored-reversed-rubric/`, `scored-blind-condition/` (Methods 4–7)
3. Pre-registration file (`RUBRIC-SCORES.md`) exists and predates the first sweep
   (`git log -1 RUBRIC-SCORES.md` should show a commit before `runs/<date>/raw/`'s mtime).

## Procedure

### 1. Verify all five methods are complete for every run

```bash
cd ~/bias-study
for run in runs/*/; do
  raw_n=$(ls $run/raw/*.jsonl 2>/dev/null | wc -l | tr -d ' ')
  [ "$raw_n" = "0" ] && continue
  for d in scored scored-abliterated-gemma scored-grok-solo scored-adversarial-pair scored-reversed-rubric scored-blind-condition; do
    n=$(ls $run/$d/*.jsonl 2>/dev/null | wc -l | tr -d ' ')
    [ "$n" = "$raw_n" ] || echo "GAP: $run$d: $n / $raw_n"
  done
done
```

No `GAP:` lines means every method scored every run completely. **Fix gaps before
proceeding** — partial coverage produces misleading deltas.

### 2. Produce the cross-method contamination-delta JSON

```bash
.venv/bin/python scripts/cross_method_report.py --all-runs > /tmp/cross-method.json
```

This writes a JSON document with, per method × run:
- `n_records`
- `n_paired` (records present in both primary and this method)
- `median_abs_delta`
- `mean_delta_signed`
- `pct_records_within_0.5` (concordance rate)
- `pct_records_within_0.10` (the pre-registered bound)
- bootstrap-CI on the median delta

Read it back to confirm shape:

```bash
.venv/bin/python -c "
import json
d = json.load(open('/tmp/cross-method.json'))
for m, runs in d.items():
    for run, stats in runs.items():
        print(f'{m:25} {run:35} median_abs_delta={stats[\"median_abs_delta\"]:.2f}')
"
```

### 3. Generate the charts

```bash
.venv/bin/python scripts/generate_charts.py --all-charts --out results/charts/
```

Each chart is regenerated from the JSON, not hand-edited. If a number in the writeup
disagrees with the chart, the JSON is the source of truth — re-run step 2 to refresh.

### 4. Apply the pre-registered rule

For each method, compare `median_abs_delta` against the 0.10 bound:

| `median_abs_delta` | Verdict |
|---|---|
| ≤ 0.10 | Consensus is robust to this bias-source |
| 0.10 < d ≤ 0.30 | Bias-source contributes; report the magnitude |
| > 0.30 | Bias-source materially carried the headline numbers; the original consensus needs an asterisk |

The deltas, NOT the verbal verdicts, are what go in the writeup. The verdict is what
goes in the executive-summary callout box on the permalink page.

### 5. Update the writeup

The writeup template (`results/WRITEUP-2026-05-26.md` for the 2026Q2 cycle) has
placeholders for:

- The contamination-delta table (one row per method × run).
- The anchor method's headline (currently Method 2 — abliterated-gemma).
- The "five families" / "≤ 0.10 stance bound" prose.

The bias-study-report skill handles the rest of the writeup statistics (CIs, FDR, length
control). This skill just lands the cross-method numbers.

## Hard lessons (do not relearn)
- **Reversed-rubric scores are 1↔5 flipped at the judge layer.** `cross_method_report.py`
  un-flips them automatically; do not also flip them by hand or you'll get garbage.
- **The pre-registration is the science.** Never pick the anchor method *after* seeing the
  results. If you're tempted, you've abandoned anti-HARKing discipline — re-read
  `RUBRIC-SCORES.md` and the writeup's pre-registration section.
- **Per-record pairing is critical.** Some methods may produce `score_classifier: null`
  on records where the primary succeeded (rate-limit timeout, unparseable judge output).
  The report restricts to records where BOTH methods returned a 1–5 score. `n_paired` <
  `n_records` is normal; `n_paired` ≪ `n_records` indicates a problem with that method's
  judge.
- **Bootstrap CIs use 1,000 resamples by default.** That's what's documented in the
  writeup; do not change it without updating the writeup too.
- **The contamination delta is not the same as inter-judge disagreement.** Inter-judge
  disagreement is captured per record in `score_classifier_disagreement` (max − min within
  a single method's panel). The contamination delta is across-method, paired by record.
  Don't conflate them in the writeup.

## Cross-references
- Producers: `abliterated-judge-sweep` (Method 2) and `api-judge-sweep` (Methods 4–7).
- Consumer: `bias-study-report` for the rest of the statistical writeup, then publication.
- Pre-registration: `RUBRIC-SCORES.md` (upstream research dir; commit timestamp = anti-HARKing proof).
- Orchestrator: `bias-barometer` agent step 7.
