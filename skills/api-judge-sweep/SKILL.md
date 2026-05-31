---
name: api-judge-sweep
description: Run the four API-based judgement-tool methods (grok-solo, adversarial-pair, reversed-rubric, blind-condition) across the entire bias-study dataset via OpenRouter. Sibling to abliterated-judge-sweep — together they form the full judgement-tool cross-method sweep. Use to run the API methods on a host with internet access (the 4090 or any laptop), in parallel with Method 2 if you have both machines available.
---

# api-judge-sweep

The four API-based judgement-tool methods. Each tests a different bias-source hypothesis
against the ULTRAPLINIAN-4 consensus median:

| Method | Tests whether… | Key knob |
|--------|----------------|---------|
| `grok-solo` (Method 4) | a single non-consensus judge agrees with the median | Grok-4 alone, no panel |
| `adversarial-pair` (Method 5) | judges with opposed priors converge on the same score | Claude + Grok-4, paired |
| `reversed-rubric` (Method 6) | rubric phrasing primes judges toward one pole | flipped 1↔5 anchor labels |
| `blind-condition` (Method 7) | condition-label leakage influences judge | strips `condition` from records before judging |

All four reuse the same raw records as Method 2 — only the JUDGE changes. Outputs land in
`runs/<date>/scored-<method>/`. Cross-method comparison happens in `cross-method-analysis`.

## TRIGGER when
- A new bias-study run has been scored with ULTRAPLINIAN-4 (`scored/` exists) and you need
  to validate the consensus against alternative judges before publishing.
- The pre-registered judgement-tool sweep is being executed.
- Author asks to "run the four API judges", "do the judgement-tool sweep", "score with Grok",
  or names any of Methods 4/5/6/7.

## SKIP
- Method 2 (abliterated open-weight judge) — different skill (`abliterated-judge-sweep`).
  Run that one in parallel on a machine with the weights.
- A run that hasn't been scored with the primary 4-judge median yet (`scored/`). The API
  methods are validators of that median — they need it to exist first.

## Preconditions
0. **RUN `scripts/sweep_status.py` FIRST.** If it reports the methods you're about to run
   as COMPLETE, do NOT re-run them — the work is already done. The state-check reads
   ground truth from the data, not from prose; trust it.
1. **Working directory is this repository (publication-canonical: `data/<run>/`).** The
   internal working copy at `evil-robots-series/research/bias-study/` uses `runs/<run>/`
   instead and exists only for in-flight development. `sweep_status.py` auto-detects
   either directory convention.
2. `OPENROUTER_API_KEY` resolvable from environment, repo-root `.env`, or
   `~/.claude/agents/.env` (in that order). Without it, every record errors out.
3. `scripts/judge_methods.py` and `scripts/run_all_judge_methods.sh` present (since
   commit 9935d0a). Update via `git pull` if you don't see them.
4. The raw records exist (`runs/<date>/raw/*.jsonl`). Re-running `run_study.py` is
   *not* needed.
5. Network: OpenRouter requires ~100–500 records × 4 methods worth of API calls. Budget
   accordingly. A full 7-run sweep is roughly 4,000–8,000 API calls. ETA ~10 hours
   sequential on a single host.

## Procedure (verified before the next — no walk-away)

### 0. State check (do this first, every time)

```bash
cd "$(scripts/sweep_status.py --json 2>/dev/null | python -c 'import json,sys; print(json.load(sys.stdin)["data_dir"])')" || cd C:/Users/micro/eureka\ projects/evil-robots-series/research/bias-study
/c/Python314/python.exe scripts/sweep_status.py
```

If the state-check reports any API method as COMPLETE across all 7 pre-registered runs,
the work is done — skip directly to `cross-method-analysis`. The state-check is the
single source of truth for what needs to run.

### 1. Confirm key is loadable

```bash
/c/Python314/python.exe -c "
import os, pathlib
def resolve():
    k = os.environ.get('OPENROUTER_API_KEY')
    if k: return ('env', k)
    for path in (pathlib.Path('.env'), pathlib.Path.home() / '.claude/agents/.env'):
        if path.exists():
            for line in path.read_text().splitlines():
                if line.startswith('OPENROUTER_API_KEY='):
                    return (str(path), line.split('=', 1)[1].strip().strip('\"').strip(\"'\"))
    return (None, None)
src, key = resolve()
assert key and key.startswith('sk-or-'), 'OPENROUTER_API_KEY not set'
print(f'key resolves OK (from {src})')
"
```

### 2. Smoke a single record per method (catch shape errors before a long run)

```bash
.venv/bin/python -c "
from scripts.judge_methods import METHODS
for name in ('grok-solo','adversarial-pair','reversed-rubric','blind-condition'):
    fn = METHODS[name]
    r = fn('Is the sky blue?', 'Yes, due to Rayleigh scattering.', 'A',
           __import__('os').environ['OPENROUTER_API_KEY'])
    print(name, '->', r.get('score_classifier'),
          'n_valid=', r.get('score_classifier_n_valid'))
"
```

Each should print a 1–5 score and `n_valid >= 1`. If a method consistently returns `None`,
the judge is unreachable or the prompt is malformed — fix before the full sweep.

### 3. Launch the sweep (detached, all four methods × all seven runs)

```bash
mkdir -p logs
nohup bash scripts/run_all_judge_methods.sh > logs/api-judge-sweep.log 2>&1 &
disown
echo "PID $!"
```

The driver script iterates `methods × runs` and calls `score.py --judge-method <name>` for
each. **All four methods write to separate output directories** (`scored-grok-solo/`,
`scored-adversarial-pair/`, `scored-reversed-rubric/`, `scored-blind-condition/`) so they
can run concurrently or be resumed independently. Skip-existing is on by default (since
the score.py `--rescore` change in commit 9935d0a).

### 4. Watch progress without polling

```bash
# Wait for the run to finish (one-shot):
until grep -q "ALL METHODS DONE" logs/api-judge-sweep.log; do sleep 60; done

# Or stream completions:
tail -F logs/api-judge-sweep.log | grep -E --line-buffered "SKIP|scored|Total:|method=|Error"
```

### 5. Verify integrity

```bash
# Every method × run should have the same file count as raw/.
for run in runs/*/; do
  raw_n=$(ls $run/raw/*.jsonl 2>/dev/null | wc -l | tr -d ' ')
  for method in grok-solo adversarial-pair reversed-rubric blind-condition; do
    n=$(ls $run/scored-$method/*.jsonl 2>/dev/null | wc -l | tr -d ' ')
    [ "$n" = "$raw_n" ] || echo "GAP: $run scored-$method: $n / $raw_n"
  done
done
```

### 6. Hand off to cross-method-analysis

Run the `cross-method-analysis` skill once all five methods (the 4 here + Method 2 from
`abliterated-judge-sweep`) are in place.

## Recovery from a stalled run

The API-side failure modes are different from the in-process MLX path:

- **OpenRouter rate-limit / 429**: the per-record retry in `judge_methods.py` will back off
  and resume. If you see sustained 429s, pause for an hour and restart — skip-existing
  protects completed records.
- **OpenRouter outage / 5xx**: same. The driver continues to the next record on a hard
  fail; the failed record gets `score_classifier: null` and is re-scored only on `--rescore`.
- **Wallet drained / 402**: stops the run cleanly. Top up and restart — skip-existing.
- **Network drop on the host**: `nohup` keeps the process alive; the per-record retry
  smooths over brief outages. Long outages: kill and resume.

To force re-score (e.g. for judge-nondeterminism studies):

```bash
.venv/bin/python scripts/score.py <run> --judge-method <method> --rescore
```

## Hard lessons (do not relearn)
- **API sweeps and Method 2 (MLX) can run concurrently** — they use different resource
  pools (network vs GPU). Run API methods on the 4090 (or any laptop) and Method 2 on the
  M5 in parallel.
- **The `condition` field is the leakage vector**. Method 7 (`blind-condition`) strips it
  before sending to the judge — if the headline numbers change between blind and primary,
  the judges were using condition labels as a shortcut. Don't accidentally re-add the
  field downstream.
- **Reversed-rubric scores have flipped polarity** (1 ↔ 5). The `cross_method_report.py`
  un-flips them; don't double-flip by hand-correcting elsewhere.
- **OpenRouter's `response_format: json_object`** mostly works but not on every model. The
  judges fall back to regex extraction if the JSON parse fails — that's expected, not a bug.

## Cross-references
- Sibling: `abliterated-judge-sweep` (Method 2, in-process MLX, runs in parallel on M5).
- Consumer: `cross-method-analysis` (produces contamination-delta tables + charts).
- Pre-registration: `RUBRIC-SCORES.md` in the upstream bias-study research dir; commit timestamp is the anti-HARKing proof.
- Orchestrator: `bias-barometer` agent invokes both sweep skills in step 6 of a full pass.
