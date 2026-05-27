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
  gracefully on no-NVIDIA hosts; `run_local.py` uses `cuda` when available else `auto` (commit
  `039dcbf`).
- **Construct-validity controls** — sycophancy (reversed-premise) and out-of-domain
  (economic/foreign-policy) both run. The lean is **civil-liberties-specific**; only Opus 4.7
  generalizes off-surface. `data/2026-05-27-{reversed-premise,ood}/`.

## Next: the weight rung on Apple Silicon (the M5)

The M5 is the right box for the weight rung's unfinished business — for two concrete reasons:
unified memory removes the 24 GB fp16 cap, and a non-MKL BLAS (Accelerate) may dodge the
Gemma-2 SVD bug.

1. **Run OBLITERATUS natively, not in the CUDA Docker image.** Apple Silicon has no CUDA, so the
   `obliteratus:gpu` image does not apply. Install OBLITERATUS natively against torch + MPS:
   - confirm `python -c "import torch; print(torch.backends.mps.is_available())"` prints `True`
   - `export PYTORCH_ENABLE_MPS_FALLBACK=1` (a handful of ops still need a CPU fallback)
   - `run_local.py` already selects `cuda if available else auto`, so it runs under MPS once
     invoked outside the container.
2. **Abliterate the models the 4090 could not (14B+).** This is the headline unlock: unified
   memory lets you abliterate at fp16 past the ~7–9B ceiling (a 14B needs ~28 GB). Add them to the
   `SWEEP` in `scripts/run_abliteration_sweep.sh` and to WRITEUP §4.2 — the dissociation finding
   gains breadth, and a larger model is the strongest test of whether the null still holds.
3. **Re-try Gemma-2.** It fails the `linalg.eigh` / MKL `SSYEVD` step on the NVIDIA/Intel host
   (documented in WRITEUP §4.2 / DEVELOPER.md §3). Apple Silicon uses Accelerate/LAPACK, not MKL —
   the SVD may simply succeed. If it does, Gemma-2 (the v1 finding's own family) joins the table.
4. **(Optional, future) MLX path.** OBLITERATUS is torch. An MLX reimplementation of the
   refusal-direction projection would be the most efficient route on Apple Silicon. An
   optimization, not a blocker.

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

- **Paraphrase robustness (D2)** — the last planned rigor footnote (WRITEUP §8): 3 paraphrases of
  the 10 neutrals, report delta stability. API-only, runnable anywhere.
- **Reconcile the §5.4 sycophancy table** — the prose cell values drift ≈0.15 from the current
  `aggregate.py` output (e.g. Opus reversed-B 3.90 in prose vs 3.70 aggregated). The conclusion
  (all framing gaps < 0.40 → genuine lean, not sycophancy) is unaffected; the table should be
  reconciled to the reproducible numbers.
- **Quarterly re-run** — re-run the prompt rung and `scripts/drift_report.py` to extend the
  time-series as new model versions ship.
- **Community contributions** — finding / model-request / reproduction submissions via the issue
  templates in `.github/ISSUE_TEMPLATE/`.
