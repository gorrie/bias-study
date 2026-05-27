# TODO / Roadmap

This repository is a standing instrument — a *bias measurement observatory* re-run on a
roughly quarterly cadence (see `README.md`). This file is the live handoff: where the work
stands and what to pick up next. Keep it current as legs complete.

## Current state (2026-05-27)

- **Prompt rung + all analysis + pipeline-rung client** — run on any platform (Python 3.11+ and
  an OpenRouter key). `run_study` → `score` → `aggregate` → `ci_analysis` → `robustness_checks`.
  Every committed run under `data/` reproduces its aggregated CSVs via `scripts/aggregate.py`.
- **Pipeline rung (G0DM0D3)** — executed: layered STM + Parseltongue lift Grok 3.63 → 4.20;
  Claude flat (the in-loop guard refuses the manipulation). `data/2026-05-27-g0dm0d3/`.
- **Weight rung (OBLITERATUS abliteration)** — four open-weight families abliterated at fp16 on a
  24 GB NVIDIA GPU and scored stock-vs-abliterated: Qwen2.5-7B, Mistral-7B-v0.3, Llama-3.1-8B,
  DeepSeek-R1-Distill-Qwen-7B. Finding: refusal direction and institutional lean are **dissociable**
  (≈70% of wording rewritten, stance ≤0.2). `data/2026-05-27-abliteration{,-controls}/`.
- **Cross-platform tooling** — weight-rung Docker drivers auto-detect the GPU runtime and skip
  gracefully on no-NVIDIA hosts (`039dcbf`); `run_local.py` places models explicitly on MPS on
  Apple Silicon (`cuda`→`mps`→`cpu/fp32`, `85817a6`).
- **On-device eval channel (macOS)** — a `dmr` channel (Docker Model Runner, Metal-backed,
  `localhost:12434`) runs the prompt rung against large *quantized* local models (`ai/qwen3.6`
  ~34B, `ai/qwen3-coder` ~30B, `ai/gemma4`) with no key or network (commit `44d7198`). This is a
  prompt-rung capability only — see the note below.
- **Construct-validity controls** — sycophancy (reversed-premise), out-of-domain
  (economic/foreign-policy), and paraphrase-robustness (D2) all run. The lean is
  **civil-liberties-specific** (only Opus 4.7 generalizes off-surface) and **wording-robust**
  (the unmask reproduces across three paraphrases per neutral).
  `data/2026-05-27-{reversed-premise,ood,paraphrase}/`.

## Next: the weight rung on Apple Silicon (the M5)

The M5 is the right box for the weight rung's unfinished business — for two concrete reasons:
unified memory removes the 24 GB fp16 cap, and a non-MKL BLAS (Accelerate) may dodge the
Gemma-2 SVD bug.

> **Note — the `dmr` channel does not cover the weight rung.** Docker Model Runner serves
> *quantized* (Q4) models for on-device prompt-rung eval. Abliteration needs **fp16** base weights
> (you cannot abliterate a quantized model — a hard lesson, WRITEUP §5.5), so the steps below
> download fp16 and run OBLITERATUS natively. The 14B+ unlock is specifically *fp16 abliteration*,
> not the Q4 locals the `dmr` channel already runs.

1. **Run OBLITERATUS natively, not in the CUDA Docker image.** Apple Silicon has no CUDA, so the
   `obliteratus:gpu` image does not apply. Install OBLITERATUS natively against torch + MPS:
   - confirm `python -c "import torch; print(torch.backends.mps.is_available())"` prints `True`
   - `export PYTORCH_ENABLE_MPS_FALLBACK=1` (a handful of ops still need a CPU fallback)
   - `run_local.py` selects MPS explicitly on Apple Silicon (`85817a6`), so it runs on the GPU
     once invoked outside the container.
2. **Abliterate a larger / 4th+ family the 4090 couldn't.** Reality check: this M5 is **32 GB**,
   so 14B at fp16 (~28 GB) does NOT fit — that needs a 64 GB+ Mac. The feasible breadth target
   here is **Gemma-2-9B** (~18.5 GB; see item 3). Add it to the `SWEEP` in
   `scripts/run_abliteration_sweep.sh` and to WRITEUP §4.2 — a model with more headroom above the
   ~3.0 neutral floor is the strongest test of whether the dissociation null holds (review A3).
3. **Re-try Gemma-2.** It fails the `linalg.eigh` / MKL `SSYEVD` step on the NVIDIA/Intel host
   (documented in WRITEUP §4.2 / DEVELOPER.md §3). Apple Silicon uses Accelerate/LAPACK, not MKL —
   the SVD may simply succeed. If it does, Gemma-2 (the v1 finding's own family) joins the table.
4. **(Optional) MLX path — already upstream.** OBLITERATUS ships an MLX backend
   (`obliteratus/mlx_backend.py`; `requirements-apple.txt` pulls `mlx`+`mlx-lm`), so the efficient
   Apple-Silicon route exists without a reimplementation. Optimization, not a blocker.

### Resume commands (M5)

```bash
git clone https://github.com/gorrie/bias-study.git && cd bias-study
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export OPENROUTER_API_KEY=...        # judges + cloud models
export HF_TOKEN=...                  # gated base-model downloads
export MODELS_DIR=./models ABLIT_OUT=./abliteration-output
export PYTORCH_ENABLE_MPS_FALLBACK=1

python scripts/dl_model.py <hf/model> "$MODELS_DIR/<model>"   # host download (cross-platform)
# abliterate natively per DEVELOPER.md §3 "Abliteration itself": --device auto --dtype float16 --method advanced
python scripts/run_local.py --model-path "$ABLIT_OUT/<model>-abliterated" \
  --label <model>-abliterated --out-date <run> --conditions A,B --samples 1
python scripts/score.py <run> --judge "anthropic/claude-haiku-4.5,openai/gpt-4.1,google/gemini-2.5-flash,deepseek/deepseek-v3.2"
python scripts/aggregate.py <run>
python scripts/abliteration_effect_check.py --out-date <run>
```

## Other open items (not M5-specific)

- **Quarterly re-run** — re-run the prompt rung and `scripts/drift_report.py` to extend the
  time-series as new model versions ship.
- **Community contributions** — finding / model-request / reproduction submissions via the issue
  templates in `.github/ISSUE_TEMPLATE/`.
