# TODO / Roadmap

This repository is a standing instrument — a *bias measurement observatory* re-run on a
roughly quarterly cadence (see `README.md`). This file is the live handoff: where the work
stands and what to pick up next. Keep it current as legs complete.

## Current state (2026-05-30)

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
- **Method 2 judgement-tool sweep (abliterated open-weight judge) — DONE on M5.** All 7 runs
  re-scored using abliterated Gemma-2-9B-IT as the JUDGE (refusal direction surgically removed
  via OBLITERATUS, MLX-converted for in-process Apple-Silicon inference). 53/53 files, 1,780
  records, 1,726 classified (97.0%). Data committed in upstream `evil-robots-series` master
  at `06a9ceb`. The direct test of ADVERSARIAL-REVIEW C3/E5 ("judges share alignment with
  systems-under-test"): if `cross_method_report.py` shows median |Δ vs ULTRAPLINIAN-4| ≤ 0.10,
  the original consensus is robust to judge-alignment contamination. Pre-registered rubric
  4.10 — highest among implementable methods.
- **Reproducible tooling and operator skills landed**: `scripts/score_inproc_gemma.py`
  (single-instance lockfile, Metal-OOM-resilient, empty-raw fast-path, skip-existing
  default); `scripts/score.py --rescore` flag; `scripts/judge_methods.py` extended with
  abliterated-gemma; `scripts/cross_method_report.py` + `scripts/generate_charts.py`;
  `scripts/run_all_judge_methods.sh`. Four new operator skills added (`abliterated-judge-sweep`,
  `api-judge-sweep`, `cross-method-analysis`, `mlx-weight-prep`) so the procedure is
  reproducible without rediscovering the bear traps. Commits 9935d0a and ae1a40b on this
  repo's `main`.
- Per **ADVERSARIAL-REVIEW.md**, every objection is FIXED / ANSWERED / TESTED / DONE.

## To resume the judgement-tool sweep (in-progress, single-machine handoff)

The five-method judgement-tool sweep is half done. Method 2 (M5/MLX) is complete and
committed; Methods 4–7 (API-based, OpenRouter) still need to run on the 4090 (or any host
with network + an OpenRouter key — Method 2 used local GPU, no conflict). To resume:

1. **On the 4090 (or any API host)**: pull both repos, then invoke the `api-judge-sweep`
   skill (or run it by hand via `bash scripts/run_all_judge_methods.sh`). Skip-existing is
   on by default; an interrupted sweep can be re-launched with the same command and will
   pick up where it stopped. ETA on the 4090: 4-8 hours depending on OpenRouter rate
   limits.
2. **When Methods 4–7 finish** on the 4090, sync the `scored-{grok-solo,adversarial-pair,
   reversed-rubric,blind-condition}/` directories under `runs/<date>/` back to this repo
   and the upstream `evil-robots-series` book repo.
3. **Then on either host**: invoke the `cross-method-analysis` skill (or run
   `scripts/cross_method_report.py --all-runs` followed by `scripts/generate_charts.py
   --all-charts`). Produces the contamination-delta JSON, the per-method comparison table,
   and the regenerated charts. The verdict-against-the-pre-registered-0.10-bound goes into
   `WRITEUP-2026-05-26.md` §5 and the `ai-bias-audit` permalink.
4. **Final publish**: `bias-study-report` skill for the remaining CI / FDR / agreement
   stats, then the gated publish step on the Hugo site.

Don't re-run Method 2 on the 4090 — its `transformers` install is CPU-only and the M5 MLX
path is the only one that survives. The data is already committed (06a9ceb on upstream).

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
