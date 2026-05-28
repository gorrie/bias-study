# TODO / Roadmap

This repository is a standing instrument — a *bias measurement observatory* re-run on a
roughly quarterly cadence (see `README.md`). This file is the live handoff: where the work
stands and what to pick up next. Keep it current as legs complete.

## Current state (2026-05-28)

- **Prompt rung + all analysis + pipeline-rung client** — runs on any platform (Python 3.11+
  and an OpenRouter key). `run_study` → `score` → `aggregate` → `ci_analysis` →
  `robustness_checks`. Every committed run under `data/` reproduces its aggregated CSVs via
  `scripts/aggregate.py`.
- **Pipeline rung (G0DM0D3)** — executed: layered STM + Parseltongue lift Grok 3.63 → 4.20;
  Claude flat (the in-loop guard refuses the manipulation). `data/2026-05-27-g0dm0d3/`.
- **Weight rung (OBLITERATUS abliteration) — five open-weight families** abliterated at fp16
  and scored stock-vs-abliterated: Qwen2.5-7B, Mistral-7B-v0.3, Llama-3.1-8B,
  DeepSeek-R1-Distill-Qwen-7B (24 GB NVIDIA GPU; `data/2026-05-27-abliteration{,-controls}/`)
  plus Gemma-2-9B-it (added natively on Apple Silicon via Accelerate/LAPACK, which cleared
  the MKL `SSYEVD` failure that blocked Gemma-2 on the 4090;
  `data/2026-05-27-abliteration-gemma2/`). Finding: refusal direction and institutional lean
  are **dissociable** — ~70% of wording rewritten, stance ≤ 0.10 across all five.
  WRITEUP §4.2.
- **Construct-validity controls** — sycophancy / reversed-premise (C2), out-of-domain (D1),
  and paraphrase-robustness (D2) all run. The lean is **civil-liberties-specific** (only
  Opus 4.7 generalizes off-surface) and **wording-robust** (the unmask reproduces across
  three paraphrases per neutral). `data/2026-05-27-{reversed-premise,ood,paraphrase}/`.
- **Cross-platform tooling** — weight-rung Docker drivers auto-detect the GPU runtime and
  skip cleanly on no-NVIDIA hosts; `scripts/run_abliteration_native.sh` drives the
  Apple-Silicon path; `run_local.py` places models explicitly on MPS, warms shaders, supports
  `--resume` for hang/interrupt recovery, and flushes the MPS cache between records.
  `requirements-weightrung.txt` captures the native install recipe.
- **On-device eval channel (macOS)** — a `dmr` channel (Docker Model Runner, Metal-backed,
  `localhost:12434`) runs the prompt rung against large *quantized* local models with no
  key or network. Prompt-rung only — the weight rung still needs fp16 base weights.
- Per **ADVERSARIAL-REVIEW.md**, every objection is FIXED / ANSWERED / TESTED / DONE.

## Open items (next quarterly cycle, ~3 months out)

- **Quarterly re-run.** Re-run the prompt rung and `scripts/drift_report.py` to extend the
  time-series as new model versions ship. The point of the observatory — the Opus arc is
  why (4.0 → 4.7: +0.27 → +0.90 inside a single year). A snapshot catches the level; only
  the cadence catches the slope.
- **Local-model repeatability.** Cloud variance is documented (§5.1, N=5, noise floor ≈±0.5);
  no local subject has a repeatability check yet — neither the Ollama prompt-rung models
  (`gemma2`, `qwen2.5:14b`, `phi4` in `data/2026-05-25`) nor the `transformers-local`
  weight-rung models. On the M5 (ungated → no `HF_TOKEN`, generation is free): (a) a
  determinism check — re-run a stock model at `--temperature 0` twice on MPS, expect
  identical greedy output; (b) variance — `run_study --samples 5 --conditions A,B` on the
  three Ollama locals → score → aggregate → `ci_analysis`, then compare the local per-model
  B−A σ to the cloud floor and the committed `2026-05-25` deltas. Reuses existing tooling.
- **14B+ vendor family abliteration (weight-rung breadth).** Currently 5 families at ~7-9B.
  A 14B+ family would test the dissociation null where the model has more headroom above
  the 3.0 neutral floor (A3). Doesn't fit a 32 GB M5 (~28 GB at fp16 + ablation overhead
  doesn't fit); needs a 64 GB+ Mac or a >24 GB CUDA host.
- **Community contributions** — finding / model-request / reproduction submissions via the
  issue templates in `.github/ISSUE_TEMPLATE/`.
