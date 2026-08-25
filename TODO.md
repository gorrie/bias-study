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
- **Method 2 judgement-tool sweep (abliterated open-weight judge) — DONE on M5 (2026-05-30).**
  All 7 pre-registered runs re-scored using abliterated Gemma-2-9B-IT as the JUDGE (refusal
  direction surgically removed via OBLITERATUS, MLX-converted for in-process Apple-Silicon
  inference). 53/53 files, 1,780 records, 1,726 classified (97.0%). Data committed in
  internal working copy master at `06a9ceb`. The direct test of ADVERSARIAL-REVIEW
  C3/E5 ("judges share alignment with systems-under-test"): if `cross_method_report.py`
  shows median |Δ vs ULTRAPLINIAN-4| ≤ 0.10, the original consensus is robust to
  judge-alignment contamination. Pre-registered rubric 4.10 — highest among implementable
  methods.
- **Methods 4–7 API sweep — DONE on 4090 (2026-05-28 → 2026-05-29).** `grok-solo`,
  `adversarial-pair`, `reversed-rubric`, `blind-condition` all scored across the 7
  pre-registered runs; 53/53 files for each method. Log:
  `runs/_aggregated/judge-methods-run.log`. The full coverage matrix is reproducible at
  any time via `scripts/sweep_status.py` (single source of truth from the data, not from
  prose).
- **The Wash dose-series tooling landed (2026-05-30)**: `scripts/run_dose_series.py` +
  `scripts/dose_smoke_gate.py` codify the M5 Apple-Silicon abliteration path with a
  pinned `max_seq_length=512` (defeats OBLITERATUS's CLI silent-degradation on M5) and a
  two-gate metadata + generation smoke check. New skill: `abliteration-on-mps` (sibling
  to `abliteration-run` — Linux/CUDA path stays unchanged). Pre-registered for The Wash
  Experiment 1 (dose-response, n_directions ∈ {1,2,4,8} for Gemma-2-9B-IT). Reference
  n_dir=4 spine is reused as-is. See `evil-robots-series/research/the-wash/HANDOFF-M5.md`.
- **The Wash Tier-B findings landed (2026-06-10)**: all three experiments complete —
  Exp 1 (dose-response: coherence cliff at n_dir<2, usable band 2–8), Exp 2 (refusal/flinch
  decoupling), Exp 3 (per-move not per-target; documented-exposure flinch replicates across
  Gemma-2-27B + Llama-3.3-70B, spine 0.00). Writeup at `results/THE-WASH-2026-06-10.md`;
  cross-linked from the README and a §5.8 addendum in `results/WRITEUP-2026-05-26.md`. Open:
  accumulate n toward PROTOCOL ≥200/cell via the quarterly resample (Exp 2 + Exp 3 boundary
  items are samples=1/30-scale point estimates today).
- **Reproducible tooling and operator skills landed**: `scripts/score_inproc_gemma.py`
  (single-instance lockfile, Metal-OOM-resilient, empty-raw fast-path, skip-existing
  default); `scripts/score.py --rescore` flag; `scripts/judge_methods.py` extended with
  abliterated-gemma; `scripts/cross_method_report.py` + `scripts/generate_charts.py`;
  `scripts/run_all_judge_methods.sh`; `scripts/sweep_status.py` (the new ground-truth
  state-check). Four new operator skills added (`abliterated-judge-sweep`,
  `api-judge-sweep`, `cross-method-analysis`, `mlx-weight-prep`).
- Per **ADVERSARIAL-REVIEW.md**, every objection is FIXED / ANSWERED / TESTED / DONE.

## Process discipline: run `sweep_status.py` BEFORE updating this doc

This file has been wrong before — it lagged reality and told an operator to re-run a
completed sweep. The ground truth is the data, not the prose. Always run

```bash
python scripts/sweep_status.py
```

before editing this status section or planning the next step. The script reads each
`runs/<date>/scored-<method>/` directory and reports completion per method × per run,
plus the actual next step. Pre-registered run set is hard-coded to match
`scripts/run_all_judge_methods.sh`.

`scripts/sweep_status.py --json` for machine output. `--all-runs` to include auxiliary
runs (variance, timeseries, etc.) that are NOT part of the pre-registered cross-method
analysis but are useful as a separate diagnostic.

## NEXT STEP: run cross-method-analysis

All five methods (M1 baseline + M2 abliterated-gemma + M4 grok-solo + M5 adversarial-pair
+ M6 reversed-rubric + M7 blind-condition) are complete across all 7 pre-registered runs.
The contamination-delta JSON and charts have NOT yet been produced. Invoke the
`cross-method-analysis` skill (or run by hand):

1. **Cross-method analysis** — run from this repository (publication-canonical home of
   the data: `data/<run>/`). The internal working copy uses `runs/<run>/` but the
   scripts auto-detect either convention:
   ```bash
   /c/Python314/python.exe scripts/cross_method_report.py --all-runs > data/_aggregated/cross-method-report.json
   /c/Python314/python.exe scripts/generate_charts.py --all-charts
   ```
   Produces the contamination-delta JSON, the per-method comparison table, and the
   regenerated charts. The verdict-against-the-pre-registered-0.10-bound goes into
   `WRITEUP-2026-05-26.md` §5 and the `ai-bias-audit` permalink.
2. **`bias-study-report` skill** — remaining CI / FDR / agreement stats.
3. **Final publish** — gated step on the Hugo site.

**Canonical location**: this repository (`github.com/gorrie/bias-study`) is the
publication surface — data lives under `data/<run>/`, scripts under `scripts/`,
writeup at `results/WRITEUP-2026-05-26.md`, charts at `results/charts/`. The
internal working copy at `evil-robots-series/research/bias-study/` uses `runs/<run>/`
instead of `data/<run>/` and exists only for in-flight development; nothing is
published from there. `sweep_status.py` auto-detects either convention.

Don't re-run any of the six scoring methods — they're done. If sweep_status.py shows
something different, something has been deleted; investigate before re-running.

## Before the next run: the self-test gate must be green

    python scripts/selftest_analysis.py

Eight assertions over the committed May data, zero API cost, and a `pre-push` hook. No
quarter's API budget is spent until all eight pass, because the analysis half of this
pipeline could previously fail **silently**: `ci_analysis.py` and `robustness_checks.py`
read a directory this repo does not ship, printed `[skip]` to stderr and exited **0**, so
a finished study produced no confidence intervals and no FDR correction while
`run_barometer.sh` reported a complete pass. Commit `4087bb7` did that same `runs/`→`data/`
pass on two other scripts and missed these.

| Gate | Asserts |
|---|---|
| G1 | `ci_analysis 2026-05-25-full` reproduces §5.6 exactly — 13 rows, 5 significant, every bound an equality |
| G2 | `robustness_checks` reproduces the BH-FDR outcome — Opus, Grok, GPT-4.1, Mistral survive; DeepSeek drops |
| G3 | raw pairwise agreement is 0.824 / 0.700 / 0.239 over 740 items, and α is a labelled footnote |
| G4 | three argument orders give byte-identical output |
| G5 | the key resolves from the process environment, and its absence is exit 2 rather than a silent heuristic pass |
| G6 | a missing run exits non-zero in both analysis scripts and propagates through the barometer |
| G7 | every protocol file the prep gate names exists and is non-empty |
| G8 | `validate_runs.py` reports exactly the known manifest defects and nothing else |

Each gate was verified to **fail** when the thing it guards is broken, before being
shipped: reverting the RNG fails G4 at 24 of 46 cells, restoring the `runs/` hardcode fails
G1 and G6, deleting `protocol/vendor-enrollment-brief.md` fails G7, and silencing one
`validate_runs` check fails G8.

Also new: `scripts/validate_runs.py` compares every manifest against the files on disk.
It currently reports six findings — four run directories with no manifest, and
`2026-05-27-reversed-premise` claiming 3 models / 120 calls against 5 model files / 200
records on disk, because `run_study.py` wrote the manifest with mode `w` and a second
invocation replaced the first's record. `run_study.py` merges now; the old manifest is
**annotated rather than corrected**, per the anti-misuse rule that a defect stays in the
run that had it.

See `results/WRITEUP-2026-05-26.md` §10a for the erratum the seed fix produced: 12 of 46
cells move, all by ≤0.13 on one bound, no verdict changes.

## Phase 2 — the matched-pair arm cut. Three arms, approved 2026-08-25.

Everything below is built and self-tested. Nothing has been run; the only cost not yet
paid is the API spend.

    python scripts/selftest_analysis.py                              # all ten, or stop
    python scripts/run_study.py --pairs protocol/pairs-v1.json         --models default-frontier --conditions A --samples 2 --date <YYYY-MM-DD>
    python scripts/score.py <run>                                    # ULTRAPLINIAN-4
    python scripts/score.py <run> --stem-swap                        # the control
    python scripts/paired_analysis.py <run> --stem-control

**Do not analyse this run with `ci_analysis.py`.** Its flat i.i.d. bootstrap treats two
samples of one template as two independent observations, which is the pseudoreplication a
prior substitution pass was killed for in adversarial review. `paired_analysis.py` clusters
on the template; on the same data the flat estimator reports an interval **55% narrower**.

**The corpus** is `protocol/pairs-v1.json`: 16 templates (8 harm domains x 2 registers),
three arms each, 48 rendered prompts committed rather than generated at run time. The three
arms of a template differ in **exactly one contiguous span** — the noun phrase naming who
decided — and gate **G10** asserts that on the committed strings rather than trusting the
generator. 16 is the floor adjudicated in adversarial review; going below re-opens a settled
question. Nouns are Latin-square rotated across domains so the arm is not confounded with one
phrase, and a clash guard rejects a noun whose words already appear in its stem, because
"an assessor assessed" would appear in one arm only.

**Three arms, not two.** Algorithm vs person alone cannot separate "defers about AI" from
"defers about impersonal bureaucratic process". Reading the result:

| Pattern | Reading |
|---|---|
| algo != person, algo ~= institution | generic institutional deference — **thesis fails** |
| algo != person **and** algo != institution | AI-specific deference — **thesis holds** |
| algo ~= person ~= institution | agent-invariant; publishable null |

**The rubric does not change.** The frozen v2 1–5 scale is applied unaltered. The estimand is
a within-pair difference under one rubric, so a constant offset between the rubric's
institution axis and these questions' culpability axis cancels exactly. The corollary is
printed with every result and must be printed in any writeup: **matched-pair scores are not
comparable in level to the main study's scores.** Only arm differences are the product.

**The control that decides publishability.** The judge sees the question, and the question
names the agent — so a judge that reacts to the stem itself would manufacture the gap.
`--stem-swap` re-scores every response under a different arm's stem with the response text
byte-identical; whatever moves is pure judge stem effect. The **abort rule is pre-registered
in code**, not decided afterwards: if the stem-effect interval reaches a contrast's arm gap,
that contrast reports "NOT SEPARABLE AT THIS N" and makes no substantive claim. Verified to
fire — with a planted 0.36 stem effect the -0.198 contrast is killed while the larger two
survive.

**Shape and honesty about power.** 16 x 3 arms x 2 samples x 7 models = 1,344 calls, roughly
4.9 h, pooled **n=224 per (arm, condition)**, which clears the pre-registered n>=200 in cut 1.
Per-model cells are n=32 and are **permanently exploratory**: at 32 a quarter, promising they
reach 200 is seven quarters, which is not a plan. Q3 is cut 1 of a quarterly accumulation and
should be labelled that way.

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
