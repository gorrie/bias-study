---
name: abliterated-judge-sweep
description: Run Method 2 of the judgement-tool sweep — re-score the entire bias-study dataset using an abliterated open-weight model as the JUDGE (not as a system-under-test). Tests whether judge alignment was inflating consensus scores. In-process MLX on Apple Silicon, single-instance lockfile, OOM-resilient, skip-existing by default. Use when running Method 2 cross-judge contamination check, adding a new abliterated-judge family, or recovering from a stalled Method 2 sweep.
---

# abliterated-judge-sweep

Method 2 of the bias-study judgement-tool sweep (pre-registered rubric score 4.10 — the
highest among implementable methods). Re-scores every record in every run using an
abliterated open-weight model as the JUDGE. If abliterated-judge scores diverge from the
RLHF-consensus median (ULTRAPLINIAN-4), the original consensus carried alignment-trained
bias; if they agree, the consensus is robust. This is the direct test of
ADVERSARIAL-REVIEW critique C3/E5 ("judges share alignment with systems-under-test").

The procedure here is the **reproducible, hands-off** version. The previous server-based
path (mlx_lm.server over HTTP) was abandoned because it hangs without recovery. This skill
codifies the in-process MLX path that survives OOM, refuses double-launches, and resumes
from the last-completed file.

## TRIGGER when
- Running Method 2 for the first time on a new bias-study run set.
- Adding a new abliterated-judge family (e.g. Qwen variant) — point `--model-path` at it.
- A previous Method 2 sweep stalled / was killed and needs resumption (skip-existing protects committed scored data).
- Author asks to "run the abliterated judge", "do Method 2", or "score with the open-weight judge".

## SKIP
- Method 2 against closed/API models — impossible (no weights to abliterate). Use other judgement-tool methods.
- Method 2 on a machine without unified memory > ~24 GB available — Gemma-2-9B fp16 needs the headroom.
- The 4-API-judge sweep (Methods 4/5/6/7) — those run over OpenRouter, different procedure (`run_all_judge_methods.sh`).

## Preconditions
1. Apple Silicon Mac with ≥ 32 GB unified memory, or a Linux box with a ≥ 24 GB GPU (the in-process path also works under CUDA via mlx-on-CUDA when available — otherwise use vLLM and an external judge call).
2. `mlx_lm` installed in the project venv: `pip install mlx-lm`
3. Abliterated MLX weights on disk. The reference setup uses Gemma-2-9B-IT abliterated converted to MLX fp16:
   - Source: produced by `abliteration-run` on the 4090, then converted via `python -m mlx_lm.convert --hf-path <abliterated-hf-dir> --mlx-path <out-dir>`
   - Reference location: `~/models-mlx/gemma-2-9b-it-abliterated-mlx/`
4. Raw bias-study runs present under `runs/<date>/raw/*.jsonl` (output of `run_study.py` / `run_local.py`).

## Procedure (verified before the next step — no walk-away)

### 1. Sanity-smoke the model before the sweep

A bad abliteration can degrade structured-output quality. Bail if more than ~20% of records
come back null. One quick smoke:

```bash
cd ~/bias-study
.venv/bin/python -c "
from mlx_lm import load, generate
m, t = load('~/models-mlx/gemma-2-9b-it-abliterated-mlx')
chat = t.apply_chat_template([{'role':'user','content':
  'Return ONLY {\"score\": 3, \"reasoning\": \"smoke\"} verbatim.'}],
  tokenize=False, add_generation_prompt=True)
print(generate(m, t, prompt=chat, max_tokens=50, verbose=False))
"
```

Expect: `{"score": 3, "reasoning": "smoke"}` or close. If you get refusal-text, the
abliteration didn't take — re-run `abliteration-run` for that family.

### 2. Launch the sweep (detached, lockfile-protected)

```bash
cd ~/bias-study
mkdir -p logs
nohup .venv/bin/python scripts/score_inproc_gemma.py \
  > logs/abliterated-judge-sweep.log 2>&1 &
disown
echo "PID $!"
```

The script:
- **Refuses to start** if another instance is already running (`/tmp/score_inproc_gemma.lock`).
  This is reproducible: a second `nohup .../score_inproc_gemma.py` from any shell exits with code 2 and a clear message. Two scorers sharing the GPU degrade throughput by ~20×; the lockfile makes the collision loud.
- **Skips already-scored files** by default. Resumption is automatic. To force re-scoring
  pass `--rescore` (only for judge-nondeterminism studies; usually wrong).
- **Survives Metal OOM** — catches the `Insufficient Memory` runtime_error, flushes the
  cache via `mx.clear_cache()`, retries once; on a second OOM the record gets a null score
  and the file's other records continue.
- **Survives empty raw files** — writes a zero-byte scored file and continues (matters for
  the 4090 Gemma-2 SVD-blocked rows).
- Writes per-record progress every 5 records and a `DONE <run>/<file>` line at completion.
  Grepping `^DONE |^=== complete|Traceback` from the log is the recommended Monitor filter.

### 3. Watch (without polling)

```bash
# One-shot wait until done:
until grep -q "^=== complete" logs/abliterated-judge-sweep.log; do sleep 30; done

# Or stream completions as they happen:
tail -F logs/abliterated-judge-sweep.log | grep -E --line-buffered "^DONE |^\[file [0-9]+/|^=== complete|Traceback"
```

### 4. Verify integrity before reporting

After `=== complete`:

```bash
# Every raw file should have a scored counterpart with the same line count
# (or be empty for the 2 known empty raw files in 2026-05-27-abliteration/).
for run in runs/*/; do
  for raw in $run/raw/*.jsonl; do
    scored="${run}/scored-abliterated-gemma/$(basename $raw)"
    rc=$(wc -l < "$raw" | tr -d ' ')
    sc=$(wc -l < "$scored" 2>/dev/null | tr -d ' ')
    [ "$rc" = "$sc" ] || echo "MISMATCH: $scored ($sc vs $rc)"
  done
done

# Classification rate (records with a non-null score). Should be > 80%.
python -c "
import json, glob
n=cls=0
for fn in glob.glob('runs/*/scored-abliterated-gemma/*.jsonl'):
    with open(fn) as f:
        for line in f:
            r=json.loads(line); n+=1
            if r.get('score_classifier') is not None: cls+=1
print(f'{cls}/{n} classified ({100*cls/max(n,1):.1f}%)')"
```

If the classification rate falls below ~80%, the judge is unreliable — re-check the model
(coherence smoke from step 1) before trusting the deltas.

### 5. Hand off to cross-method reporting

```bash
.venv/bin/python scripts/cross_method_report.py --all-runs
.venv/bin/python scripts/generate_charts.py --all-charts
```

`cross_method_report.py` already has `abliterated-gemma` registered in `KNOWN_METHODS` and
emits the contamination-delta JSON (Method 2 vs ULTRAPLINIAN-4 median per record). That
JSON is what the writeup section consumes.

## Recovery from a stalled sweep

The lockfile makes recovery deterministic. Three states:

1. **Process alive, log advancing**: leave it alone. Look at the latest `DONE` line; if a
   new one has landed in the last 5 minutes the sweep is fine.
2. **Process alive, log stuck for > 10 minutes** (no new per-record line): almost always
   a Metal OOM that didn't get caught. Kill the scorer (`pkill -KILL -f score_inproc_gemma`),
   remove the lockfile (`rm /tmp/score_inproc_gemma.lock`), restart per step 2. Skip-existing
   resumes at the file that was mid-flight.
3. **Process dead, log shows a `Traceback`**: read the traceback. Empty-file and OOM cases
   are already handled in code; anything else is a real bug — fix the script before
   restarting, or you'll lose another hour to the same crash.

## Hard lessons (do not relearn)
- **Never run two scorers concurrently.** They fight for Metal/GPU and slow each other to
  ~0.01 rec/s (down from 0.20). The lockfile prevents this; do not pass `--no-lock` outside
  debugging.
- **Server-based MLX (`mlx_lm.server`) hangs unrecoverably** under sustained load on M5.
  This skill uses the in-process path on purpose. Do not "simplify" back to a server.
- **`response[:N]` truncation must stay ≤ 1500 chars.** Longer prompts blow the Metal
  working set on 32 GB machines. Increasing it requires also bumping `--max-tokens` down,
  testing OOM resilience, and re-measuring throughput.
- **The two empty raw files in `2026-05-27-abliteration/`** (`gemma-2-9b-{stock,abliterated}.jsonl`)
  are real — the 4090's MKL SSYEVD bug prevented Gemma-2 from running. The empty-file
  fast-path in `score_inproc_gemma.py` is load-bearing; don't remove it without
  re-acquiring those records on Apple Silicon first (which is itself the headline result —
  see `abliteration-run` lessons).
- **`question_text` and `response_text` are the canonical raw record field names** (not
  `question` / `response`). The judge prompt template references question and response
  positionally; the field-name lookup must match `score.py`'s.

## Cross-references
- The orchestrator: `bias-barometer` agent — invoke this skill from there once the prompt
  rung has scored data.
- The per-method comparison: `cross_method_report.py` consumes `scored-abliterated-gemma/`
  and produces the contamination delta.
- The pre-registration: `RUBRIC-SCORES.md` (committed before any sweep ran — git timestamp
  is the anti-HARKing proof).
- Other judgement-tool methods (grok-solo, adversarial-pair, reversed-rubric,
  blind-condition) — `run_all_judge_methods.sh`, OpenRouter-based, can run in parallel with
  this one (no resource conflict).
