# DEVELOPER.md — Bias Study toolchain & replication guide

Operational reference for the institutional-skepticism bias study: what every script
does, the exact command to run it, and the full force-escalation-ladder pipeline end to
end. This is the doc to read **before** touching the code — it exists so the toolchain
doesn't have to be re-derived each session, and so an outside replicator can reproduce
every result.

Companion docs: `questions.md` (stimuli), `rubric.md` (scoring), `schema.md` (record
format), `run-protocol.md` (the 18-step procedure), `aggregation-rules.md` (roll-up),
`ADVERSARIAL-REVIEW.md` (objection → fix/answer map), `WRITEUP-2026-05-26.md` (the paper).

---

## 0. The mental model: a three-rung force-escalation ladder

The study's claim is that institutional-skepticism framing is **masked at the alignment
layer**, and the mask "comes off in proportion to the force you put on it — except where
it's bolted on, where force does nothing." The method *is* that ladder:

| Rung | Force applied | Tooling | Record fields | Status |
|------|---------------|---------|---------------|--------|
| **1. Prompt** | remove fairness instruction; A→B→C→D→E gradient | `run_study.py` (OpenRouter / Ollama) | `condition` | DONE (8k+ records) |
| **2. Pipeline** | hedge-strip + obfuscation (STM, Parseltongue), layered | G0DM0D3 server (WP2) | `g0dm0d3_pipeline` | NOT YET RUN |
| **3. Weights** | ablate the refusal direction | OBLITERATUS + `run_local.py` | `obliteratus_applied` | DONE (4 vendors) |

Rung 3 is the moat: it requires the weights, a GPU, and the knowledge. It is **only
possible on open-weight models** — the transparency-asymmetry finding.

---

## 1. Prerequisites & environment

| Need | How to provide it |
|------|------|
| Python | `python3` (3.11+; developed on 3.14) |
| OpenRouter key | `OPENROUTER_API_KEY` in your environment, or a repo-root `.env` (copy `.env.example`). Never commit the real key. Get one at <https://openrouter.ai/keys> |
| HF token (gated models) | `HF_TOKEN` env var (read scope) — only needed to download gated base models for the weight rung |
| GPU image | A Docker image with torch + transformers + CUDA and the OBLITERATUS CLI installed, built from the [OBLITERATUS repo](https://github.com/elder-plinius/OBLITERATUS); referred to below as `obliteratus:gpu`. The weight rung needs a ~24 GB GPU. |
| Base models | `$MODELS_DIR` (default `./models`) — where base-model weights are downloaded |
| Abliterated outputs | `$ABLIT_OUT` (default `./abliteration-output`) |
| OBLITERATUS | upstream <https://github.com/elder-plinius/OBLITERATUS> (CLI: `python -m obliteratus.cli`) — cited, not vendored |
| Native (Apple Silicon) install | No GPU image — install the weight-rung stack into a venv: `pip install -r requirements.txt -r requirements-weightrung.txt`, then `pip install -e <OBLITERATUS-path> --no-deps` (skips its CUDA-only `bitsandbytes` pin), then (optional) `pip install -r <OBLITERATUS-path>/requirements-apple.txt` for the MLX backend. Drive via `scripts/run_abliteration_native.sh`. |
| G0DM0D3 | upstream <https://github.com/elder-plinius/G0DM0D3> (OpenAI-compatible server) — cited, not vendored |

**Platform note (read before the weight rung):** the weight rung needs Docker **and an NVIDIA
GPU (CUDA)** — it runs on a Linux GPU host. It **cannot run on macOS/Apple Silicon**: Docker
Desktop there has no GPU passthrough, so `--gpus all` is unavailable. The driver scripts
(`run_abliteration_sweep.sh`, `run_abliteration_controls.sh`, `run_barometer.sh`) detect this
and exit/skip with a clear message rather than failing cryptically; override the detection with
`DOCKER_GPU_FLAG` (e.g. `DOCKER_GPU_FLAG=''` to force CPU, or a custom runtime string). The
prompt rung and all scoring/analysis are pure Python + API calls and run fine on any platform.
Always pass **absolute** host paths to `-v` (a relative source like `./models` makes Docker
create a *named volume* instead of bind-mounting your directory). Windows Git-Bash only: prefix
`docker run` with `MSYS_NO_PATHCONV=1` so MSYS doesn't rewrite the `-v` paths.

---

## 2. Run-data layout

Every run is immutable under `data/<date-or-label>/`:

```
data/<run>/
├── raw/<model>.jsonl       # one record per (model,question,condition,sample) — run_study/run_local output
├── scored/<model>.jsonl    # raw + score_classifier (+ per-judge) — score.py output
└── aggregated/*.csv        # per-model / per-topic / per-question — aggregate.py output
```

Run labels in play: `2026-05-2x-*` (prompt-rung cross-section), `2026-05-27-abliteration`
(weight rung, 4 vendors stock+abliterated), `2026-05-27-abliteration-controls` (A2b/A4),
`2026-05-27-reversed-premise` (C2 sycophancy control).

---

## 3. The scripts (what / how)

### Prompt rung
- **`run_study.py`** — cross-section over cloud (OpenRouter) and local models. Channels:
  `openrouter` (cloud), `ollama` (`:11434`), and `dmr` — Docker Model Runner's
  OpenAI-compatible endpoint (`:12434`), on-device on the host GPU (Metal on Apple Silicon),
  no API key or network. This is how macOS hosts run the prompt rung locally even though the
  weight rung (CUDA abliteration) can't run there. The `local-large` set runs on-device
  30-34B open-weight models (`ai/qwen3.6`, `ai/qwen3-coder`, `ai/gemma4`) — bigger locals than
  a 24 GB CUDA card holds at fp16. A local-only run needs no `OPENROUTER_API_KEY`.
  ```bash
  python3 scripts/run_study.py \
    --positions neutral,reversed \                # mild|neutral|pointed|reversed|all (csv)
    --models "openrouter:anthropic/claude-opus-4.7,openrouter:x-ai/grok-4.3" \  # channel:model csv, OR default-frontier
    --conditions A,B \                            # A..E (csv); default A,B
    --date 2026-05-27-reversed-premise \
    --samples 1 --dry-run                         # --dry-run prints plan, no API calls
  ```
  **Custom model format is `channel:model`** (split on first colon) — e.g.
  `openrouter:anthropic/claude-opus-4.7`, `ollama:qwen2.5:14b`, `dmr:ai/qwen3.6`. Bare model
  IDs fail with `not enough values to unpack`. Named sets: `default-frontier`, `local-large`. Conditions: **A** fairness baseline · **B** "what do you
  think?" · **C** drop-hedging (user) · **D** must-commit (system) · **E** opinionated
  persona (system). Default-frontier list is in `DEFAULT_FRONTIER` near the top of the file.

### Weight rung (local inference + abliteration)
- **`run_local.py`** — runs the question set against a LOCAL transformers model (stock or
  abliterated), writing raw JSONL in study schema. Runs **inside** `obliteratus:gpu`:
  ```bash
  docker run --rm --gpus all -e HF_HUB_OFFLINE=1 \
    -v "$(pwd)/models:/models" -v "$(pwd)/abliteration-output:/output" \
    -v "$(pwd):/study" obliteratus:gpu \
    python /study/scripts/run_local.py \
      --model-path /output/qwen2.5-7b-abliterated \   # or /models/<stock>
      --label qwen2.5-7b-abliterated --out-date 2026-05-27-abliteration \
      --conditions A,B --samples 1 --temperature 0.7   # --temperature 0 = greedy/deterministic
  ```
  (Linux GPU host; see the platform note in §1. Set `MODELS_DIR`/`ABLIT_OUT` to absolute paths
  to relocate the mounts. Windows Git-Bash: prefix with `MSYS_NO_PATHCONV=1`.)
- **`dl_model.py`** — robust HF downloader, **host-side** (NOT in Docker — WSL2 NAT
  strangles large LFS pulls). Range-resume + per-shard safetensors validation, looped until
  valid. `huggingface_hub`/`hf` is unreliable for big shards; this is the answer.
  ```bash
  python3 scripts/dl_model.py google/gemma-2-9b-it $MODELS_DIR/gemma-2-9b-it
  ```
- **`run_abliteration_sweep.sh`** — WP1 driver: for each vendor family, abliterate
  (advanced/SVD) → coherence smoke-test → A/B run stock + abliterated. Failure-tolerant,
  GPU-sequential. Edit the `SWEEP=(...)` array to add families.
- **`run_abliteration_controls.sh`** — the A2b (temp=0 isolation) + A4 (aggressive-strength
  dose-response, with coherence guard) robustness controls from the adversarial review.
- **`run_abliteration_native.sh`** — Apple-Silicon analog of the Docker sweep. Runs
  OBLITERATUS directly on torch+MPS (no Docker, no CUDA) with `PYTORCH_ENABLE_MPS_FALLBACK=1`
  so the SVD `eigh` routes through Accelerate/LAPACK — the path that clears Gemma-2's MKL
  `SSYEVD` failure. Same per-family loop as the Docker sweep; uses the venv built from
  `requirements-weightrung.txt` (see §1).

### Abliteration itself (OBLITERATUS)
The CLI is `python -m obliteratus.cli obliterate` (NOT `app.py`, which is the Gradio UI).
```bash
docker run --rm --gpus all -e HF_HUB_OFFLINE=1 \
  -v "$(pwd)/models:/models" -v "$(pwd)/abliteration-output:/output" \
  obliteratus:gpu \
  python -m obliteratus.cli obliterate /models/<name> \
    --output-dir /output/<name>-abliterated \
    --device auto --dtype float16 --method advanced
```
Or natively on Apple Silicon (no Docker — Apple has no GPU passthrough, so the `obliteratus:gpu` CUDA image doesn't apply):
```bash
PYTORCH_ENABLE_MPS_FALLBACK=1 python -m obliteratus.cli obliterate models/<name> \
  --output-dir abliteration-output/<name>-abliterated \
  --device auto --dtype float16 --method advanced
```
The MPS fallback routes ops MPS doesn't implement (notably `linalg.eigh` used in the SVD step) through Accelerate/LAPACK — which is what clears Gemma-2's MKL `SSYEVD` failure on the 4090.
- `--method`: `basic|advanced|aggressive|spectral_cascade|informed|surgical|optimized|inverted|nuclear`. Main sweep uses **advanced** (norm-preserving SVD, 4 directions, reg 0.3, 2 refinement passes — see any model's `abliteration_metadata.json`).
- Writes shards + `abliteration_metadata.json`. Verifies refusal-rate drop on a harmful test set.
- **Hard lessons:** (1) you **cannot abliterate a quantized** model — needs fp16; a 14B at bf16 (~28 GB) exceeds a 24 GB 4090, so use ~7–9B at fp16. (2) Gemma-2's SVD step (`linalg.eigh` / Intel oneMKL `SSYEVD`) fails on MKL — architecture-specific. **It clears on Apple Silicon's Accelerate/LAPACK** via `scripts/run_abliteration_native.sh` (`PYTORCH_ENABLE_MPS_FALLBACK=1` routes `eigh` through Accelerate, not MKL). Verified on `gemma-2-9b-it` (fp16, 32 GB M5, advanced method): `refusal_rate` 0.17, `coherence` 1.0, `spectral_certification` RED (a few layers flagged `incomplete` — refines further with the `nuclear` method). (3) A download that *starts* is not one that *finishes* — `dl_model.py` validates shards before compute.

### Scoring & analysis
- **`score.py <run> --judge "<csv>"`** — ULTRAPLINIAN. Multiple judges ⇒ parallel call,
  **median** = canonical `score_classifier`, with per-judge scores + disagreement retained.
  Reads `OPENROUTER_API_KEY` from `~/.claude/agents/.env`. **Idempotent by default**: skips
  any `raw/*.jsonl` whose `scored/*.jsonl` already exists, so re-running on a run that
  gained a new model only scores the new file (committed scored data isn't re-judged and
  can't shift from judge non-determinism). Pass `--rescore` to force re-scoring everything.
  The canonical 4-judge panel:
  ```bash
  python3 scripts/score.py 2026-05-27-abliteration \
    --judge "anthropic/claude-haiku-4.5,openai/gpt-4.1,google/gemini-2.5-flash,deepseek/deepseek-v3.2"
  ```
- **`aggregate.py <run>`** → per-model/topic/question CSVs.
- **`ci_analysis.py`** — bootstrap 95% CIs over per-question deltas + inter-judge agreement (seed 20260527). A delta is a finding only if its CI excludes zero.
- **`robustness_checks.py`** — Benjamini-Hochberg FDR + length/verbosity control.
- **`abliteration_effect_check.py [--out-date <run>]`** — answers reviewer objection A2:
  pairs stock vs abliterated by (question,condition) and measures whether the ablation
  changed the *political* outputs at all (word-set Jaccard, length/hedge deltas, refusal
  shift). High Jaccard + ~0 deltas ⇒ uninterpretable null; low Jaccard ⇒ real dissociation.

---

## 4. End-to-end replication

### Prompt rung (anyone with an OpenRouter key)
```bash
git clone https://github.com/gorrie/bias-study.git && cd bias-study
export OPENROUTER_API_KEY=...        # or put it in ~/.claude/agents/.env
python scripts/run_study.py --positions mild,neutral,pointed --date <run>
python scripts/score.py <run> --judge "anthropic/claude-haiku-4.5,openai/gpt-4.1,google/gemini-2.5-flash,deepseek/deepseek-v3.2"
python scripts/aggregate.py <run>
python scripts/ci_analysis.py        # CIs + agreement
python scripts/robustness_checks.py  # FDR + length control
```

### Weight rung (needs a 24 GB GPU + Docker + the obliteratus:gpu image)
```bash
# 1. download base model on the HOST (resume-until-valid)
python scripts/dl_model.py Qwen/Qwen2.5-7B-Instruct $MODELS_DIR/qwen2.5-7b-instruct
# 2. abliterate offline in the container (see §3) -> /output/qwen2.5-7b-abliterated
# 3. A/B run stock + abliterated (run_local.py in container, §3), out-date <run>
# 4. score, then check the ablation actually touched the political items:
python scripts/score.py <run> --judge "<4-panel>"
python scripts/abliteration_effect_check.py --out-date <run>
```
Or just run the drivers: `bash scripts/run_abliteration_sweep.sh` then
`bash scripts/run_abliteration_controls.sh`.

### Weight rung — Apple Silicon (no CUDA, native MPS)

The `obliteratus:gpu` Docker image doesn't apply on Apple Silicon (no GPU passthrough); the
native path uses the host's torch + MPS stack instead. Memory note: a 9B at fp16 (~18.5 GB)
fits a 32 GB unified-memory Mac; 14B (~28 GB) needs a 64 GB+ machine.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-weightrung.txt
git clone https://github.com/elder-plinius/OBLITERATUS.git ../OBLITERATUS
pip install -e ../OBLITERATUS --no-deps                       # skip CUDA-only bitsandbytes
pip install -r ../OBLITERATUS/requirements-apple.txt          # MLX backend (mlx, mlx-lm)

export HF_TOKEN=...              # gated base-model downloads (e.g. gemma-2)
export OPENROUTER_API_KEY=...    # judges

python scripts/dl_model.py google/gemma-2-9b-it ./models/gemma-2-9b-it
bash scripts/run_abliteration_native.sh                       # edit NATIVE_SWEEP=() to add families
python scripts/score.py <run> --judge "<4-panel>"             # idempotent by default
python scripts/aggregate.py <run>
python scripts/abliteration_effect_check.py --out-date <run>
```

### Weight rung — tuning for limited-GPU hosts

If a long A/B gets interrupted **or hangs** (we've seen MPS occasionally freeze mid-generation
on a 9B at fp16 — the output file's mtime stops advancing while the process *appears* alive),
kill the stalled process and pass `--resume` to `run_local.py`: it loads the cells already
recorded in the output JSONL, skips them, and appends new records. Difference between
restarting a 3-hour job from scratch and resuming the last 20 minutes. `run_local.py` also
flushes the MPS cache after every record, which relieves the memory-pressure pattern that's
been correlated with these hangs.

For throughput on a slow GPU host (e.g. 32 GB Apple Silicon running a 9B at fp16), the
cheapest win is `--max-new-tokens 400` (default 800). Observed mean response length is
~350–430 words ≈ 500–600 tokens, so 400 still captures the answer body while roughly halving
per-call wall time, with no change to the stance signal. Local rungs only; doesn't touch
the cloud cross-section's protocol.

`run_local.py` runs an MPS-warmup `generate()` before the main loop so first-call kernel
compilation (which we've seen as ~7 min on Apple Silicon, steady-state ~80 s) is amortized
off the recorded latencies, and logs per-record progress with the actual `generate()` time
so a stall is distinguishable from slow-but-progressing without `pgrep` + `tail` gymnastics.

---

## 5. Reviewer objections → where each is handled

See `ADVERSARIAL-REVIEW.md` for the full text. Quick map:
- **A1** underpowered null → `ci_analysis.py` (report CIs, never "proven zero").
- **A2** "ablation didn't touch political items" → `abliteration_effect_check.py`.
- **A2b** temp-0.7 sampling confound → `run_abliteration_controls.sh` (greedy isolation).
- **A4** "ablation too gentle" → `run_abliteration_controls.sh` (aggressive method + coherence guard).
- **C2** sycophancy/opinionatedness → `questions.md` `*-Q4` reversed-premise + `--positions reversed` run.
- **C3** judge contamination → cross-vendor 4-judge median; per-judge spread retained.
- **D1/D2** scope/paraphrase → WP3 out-of-domain + paraphrase positions (planned).

---

## 6. Doc-reality discipline (do not skip)

As each rung executes, the `g0dm0d3_pipeline` / `obliteratus_applied` record fields and the
protocol/rubric/schema move from "planned, null" to real. **Keep the docs matching what was
actually run.** Never describe a leg that wasn't executed as if it were. The writeup's
findings list and `rubric.md` §4 condition tags are split into *executed* vs *planned* for
exactly this reason.

---

## 7. Troubleshooting

Common errors seen during replication + their fixes — keep current as the toolchain evolves.

- **`jinja2.exceptions.TemplateError: System role not supported`** in `run_local.py`. The
  model's chat template has no system role (Gemma family). Handled automatically —
  `run_local.py` catches this and folds the system content into the first user turn. Caveat
  for the writeup: for such models, the condition-A fairness instruction is delivered in
  the user role rather than a system role.

- **MPS hang mid-generation on a long M5 run.** Output file's mtime stops advancing while
  the process appears alive (R state, low CPU, no new progress lines). Kill the stalled
  process and re-launch with `--resume` — it loads cells already recorded, skips them, and
  appends new records. `run_local.py` flushes the MPS cache after every record to relieve
  the memory-pressure pattern correlated with these hangs. See §4 "Tuning for limited-GPU
  hosts."

- **`Intel oneMKL ERROR: SSYEVD`** during the Gemma-2 SVD step on an Intel/MKL host.
  Architecture-specific to MKL. Use `scripts/run_abliteration_native.sh` on Apple Silicon
  — the MPS fallback routes `eigh` through Apple's Accelerate/LAPACK, which clears it.

- **`huggingface_hub.errors.GatedRepoError: 401`** when downloading a gated HF model
  (`google/gemma-2-9b-it`, `meta-llama/*`, etc.). Get an HF token at huggingface.co, accept
  the model's license on its page, then `export HF_TOKEN=...` or drop it in
  `~/.claude/agents/.env`. `dl_model.py` reads it transparently.

- **`fatal: could not read Password for 'https://...@gitlab.com'`** on `git fetch`/`push`.
  Wire glab as git's credential helper for gitlab.com:
  `git config --global 'credential.https://gitlab.com.helper' '!glab auth git-credential'`.
  Do **not** pin `credential.username` for gitlab — glab authenticates as `oauth2`, and a
  forced username makes its helper reject the request. (GitHub multi-account is the
  opposite — pin `credential.https://github.com.username` per-tree so the right account's
  token is fetched from the keychain.)

- **`score.py` re-judging committed families** when scoring a run that's gained a new
  model. Default is now skip-if-existing — only new raw files get scored. Pass `--rescore`
  to force re-judging everything (changing judges, reproducibility audit, etc.).

- **14B fp16 OOM on a 32 GB M5.** A 14B at fp16 is ~28 GB of weights alone; abliteration
  peaks higher than that. Doesn't fit. Gemma-2-9B (~18.5 GB) fits with care; 14B+ needs a
  64 GB+ machine.
