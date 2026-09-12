# Plan: Build the Best-Possible Judgement Tool + Close Remaining Adversarial Coverage

> **HISTORICAL** — Predates the 2026-08-29 instrument swap, so it plans against the judge-scored
> battery that is no longer the primary instrument. Kept for the design reasoning, and published
> because [RUBRIC-SCORES.md](RUBRIC-SCORES.md) is its companion and a pre-registration nobody can
> read is not a pre-registration. Sequencing after this plan is carried in the working tree and
> is not part of this release; what survives of it publicly is the `prereg/` directory and
> `CORRECTIONS.md`.


## Status (2026-05-30)

- **Method 2 (abliterated open-weight judge) — DONE.** All 7 runs scored, 53/53 files, 1,780 records, 1,726 classified (97.0%). Data committed upstream at `06a9ceb`. Reproducible via the public `abliterated-judge-sweep` skill (gorrie/bias-study commit `9935d0a` + `ae1a40b`). See `M5-TASK-METHOD-2.md` for historical task brief, now superseded by the skill.
- **Methods 4–7 (API-based: grok-solo, adversarial-pair, reversed-rubric, blind-condition) — TODO on 4090.** Use the `api-judge-sweep` skill (or `bash scripts/run_all_judge_methods.sh` by hand). Skip-existing default; ETA 4-8 h depending on OpenRouter rate limits. Can run in parallel with anything M5-side (no resource conflict).
- **Methods 1, 3, 8, 9 — deferred.** Method 1 is the existing baseline (already in `scored/`); Method 8 needs external benchmark data acquisition; Methods 3 and 9 are de-prioritized vs the pre-registered 4.10-rubric anchor (Method 2).
- **Cross-method analysis** — pending Methods 4–7 completion. Use the `cross-method-analysis` skill once all five method directories are populated. Pre-registered rule: `median |Δ vs ULTRAPLINIAN-4| ≤ 0.10` → consensus robust to that bias-source.
- **Writeup + permalink** — pending cross-method numbers.

## Context

Current scoring uses a 4-judge ULTRAPLINIAN median across Claude / GPT-4.1 / Gemini-2.5-flash / DeepSeek-V3.2. All four carry RLHF alignment — the very thing the study claims is the source of institutional-skepticism bias in the systems-under-test. The median makes the judges *agree more often* with each other, which laundering institutional lean instead of detecting it. Adversarial-review item C3 is currently marked ANSWERED-with-mitigation, but the mitigation ("cross-vendor median is robust to one outlier judge") doesn't escape *shared* RLHF lean. The right fix is a multi-method judgement framework with **pre-registered method selection** (anti-cherry-pick) and **mechanical anchoring** rather than consensus-by-majority.

This is an improvement on existing methodology. The study has been published only on `evilrobots.lol/research/ai-bias-audit` and `github.com/gorrie/bias-study` — no external announcement made. We update those surfaces when this work lands.

## Scope

In scope:
- A judgement-method catalogue of 9 alternative scoring approaches (each spec'd, each runnable on existing data)
- Pre-registered method-quality rubric (weights locked BEFORE seeing comparative results)
- Multi-method run on the entire main-study dataset + all rigor legs (paraphrase, OOD, reversed-premise, abliteration, G0DM0D3)
- Cross-method sensitivity analysis (where do methods agree / disagree on per-model deltas?)
- Mechanical anchor-method selection by rubric score
- Adversarial-review coverage updates for the few remaining hooks (within-leg FDR, judge-disagreement-by-topic, forward-looking objections section)
- Writeup + permalink + ADVERSARIAL-REVIEW.md updates after results land

Out of scope:
- Paid third-party domain expert calibration (dropped — LLM-driven methodology by design)

## The 9 judge methods

Each method scores the same response pool; deltas computed identically per `ci_analysis.py`.

| # | Method | Spec | Cost |
|---|---|---|---|
| 1 | **ULTRAPLINIAN-4 median** (baseline) | Current: Claude / GPT-4.1 / Gemini-2.5-flash / DeepSeek-V3.2, temp 0.0, median score | already run |
| 2 | **Abliterated open-weight judge** | Qwen2.5-7B abliterated (4090-PC weights at `obliteratus-output/qwen2.5-7b-abliterated/`) and/or Gemma-2-9B abliterated (M5). Inference runs on the **M5** because the 4090 PC has CPU-only torch. Score.py talks to a vLLM / mlx-server / llama-server OpenAI-compatible endpoint via `ABLITERATED_ENDPOINT` env var. Same JUDGE_PROMPT_TEMPLATE as ULTRAPLINIAN-4. | ~4-6 hr compute on M5 |
| 3 | **G0DM0D3-stripped judge** | Claude or GPT-4.1 routed through G0DM0D3 server with `hedge_reducer` + `direct_mode` STMs applied to *the judge prompt*. Tests whether elicitation-layer alignment removal moves the judge. | ~2 hr compute |
| 4 | **Adversarial-pair judge** | Two identical judges, one system-prompted "be maximally critical of institution-skeptical framing in scoring," the other "be maximally critical of institutional-deference framing." Mean of the two scores. Opposing pulls cancel shared prior; mean centers on latent score. | ~3 hr compute |
| 5 | **Single-low-RLHF judge** | Grok 4.3 as lone scorer. Known low-hedging baseline; one bias replaces four. Reported as a sensitivity check, not anchor candidate. | ~2 hr compute |
| 6 | **Reversed-rubric scoring** | Existing judges + rubric, but rubric labels inverted (1↔5, 2↔4). If judges produce inverse-magnitude scores → consistent. If not → anchor bias measurable. Tests rubric construct validity. | ~2 hr compute |
| 7 | **Blind-condition judges** | Existing judges see *only* the response text — no condition label, no question framing, no model identity. Forces scoring on content alone. | ~2 hr compute |
| 8 | **External-benchmark anchoring** | Map rubric outputs to Political Compass / Pew typology axes via a small humans-labeled benchmark set. Convert "skeptical of institutions" to a measurable empirical position. | ~half-day + benchmark data acquisition |

Methods 1-7 run automatically on existing data. Method 8 needs external benchmark items. (No paid-expert path — LLM-driven methodology is the constraint we're solving within, not bypassing.)

## Pre-registered method-quality rubric (weights LOCKED before scoring)

Each method gets scored 1-5 on each dimension. Total = weighted sum. Highest = anchor method.

| Dimension | Weight | What it measures |
|---|---|---|
| **Circularity-reduction** | 0.30 | Does the method escape the shared-RLHF-lean of the judges? Higher = less circular. |
| **Construct-validity preservation** | 0.25 | Does the method still score what we intend to measure (institutional skepticism), or does it accidentally measure something else (e.g., verbosity, polarization)? |
| **Reproducibility** | 0.20 | Can another researcher re-run this exactly? Open weights / deterministic temp / public prompts > closed APIs / temp>0 / hidden system prompts. |
| **Interpretability** | 0.15 | Can the result be defended to a hostile reviewer in plain language? |
| **Cost-to-run** | 0.10 | Negative weight on burden — methods that cost compute-hours score lower than methods that need cash + recruitment. |

**Scoring discipline:** rubric scores per method are filled in by examining the *method's design*, not its results. Pre-registration commit lands BEFORE any cross-method numbers are computed. Git timestamp is the proof.

## Execution sequence

### Phase 1 — Pre-registration (~1 day)
- Commit this file to the bias-study source repo BEFORE any new scoring runs (timestamp = anti-HARKing proof)
- Lock the 9 method specs above
- Lock the rubric weights above
- Score each method on the rubric (1-5 per dimension) based on method *design only*, not results. Document scoring rationale per cell.
- Compute the anchor pick mechanically. Document.

### Phase 2 — Implementation (~2 days)
- Parameterize `scripts/score.py` to accept `--judge-method` flag (values: `ultraplinian`, `abliterated-qwen`, `abliterated-gemma2`, `g0dm0d3-claude`, `adversarial-pair`, `grok-solo`, `reversed-rubric`, `blind-condition`)
- Implement method-specific scoring pipelines as separate functions in `scripts/judge_methods.py`
- Add an output schema field `judge_method` to scored records so downstream analysis can stratify

### Phase 3 — Multi-method run on existing data (~1-2 days compute)
- Re-score the full study (8,022 records) under each of methods 2-7 (method 1 already done)
- Output: `data/2026-05-29-judge-methods/<method>/scored/<model>.json` per method × model
- Time bounded; nothing GPU-heavy except the abliterated-judge runs (Qwen 7B local inference)

### Phase 4 — Cross-method comparison (~1 day)
- New `scripts/cross_method_report.py` produces:
  - Per-model delta table under each judge method (with CIs)
  - Agreement matrix between methods (Cohen's κ / Spearman ρ on the per-model delta rankings)
  - Disagreement-by-topic table (where do methods diverge most? — exactly the C3-promised judge-disagreement table extended cross-method)
  - The "judge contamination measurement": ULTRAPLINIAN-median vs Abliterated-judge delta — large delta = judges contaminated; small delta = bias finding survives even with judge alignment stripped
- Mechanical anchor selection: rubric-top method = anchor for headline numbers; all other methods reported in supplementary table

### Phase 5 — Adversarial coverage closure (~1 day, parallelizable with Phase 4)
- Extend `scripts/robustness_checks.py` to compute **within-leg BH-FDR**: separate families for paraphrase (30 tests/model), OOD (8 tests/model). Report which effects survive within-family q=0.05.
- Add **forward-looking objections section** to ADVERSARIAL-REVIEW.md covering:
  - Construct-validity-of-the-rubric (does scoring "institutional skepticism" 1-5 actually capture the latent construct?)
  - RLHF-dataset-contamination of judges (are the same training corpora powering both systems-under-test and judges?)
  - Temporal-drift between vendor runs (models update; runs not strictly contemporaneous)
  - Rubric anchor-bias (the reversed-rubric method directly tests this — note its result here)
- Mark ADVERSARIAL-REVIEW.md C3 as DONE with reference to the multi-method approach

### Phase 6 — Writeup + permalink updates (~1 day)
- New `WRITEUP-2026-05-29.md` or update existing in place: headline numbers anchored on rubric-selected method, all 9 method results in §5 sensitivity-analysis subsection
- Update `evilrobots.lol/content/research/ai-bias-audit.md` to match — keep the voice, swap in the updated headline numbers + a paragraph about the judge-method robustness analysis
- Update `github.com/gorrie/bias-study/README.md` + commit the new data dir

## Critical files

- NEW: `JUDGEMENT-TOOL-PLAN.md` (this file — commit FIRST)
- NEW: `scripts/judge_methods.py` (per-method scoring pipelines)
- NEW: `scripts/cross_method_report.py` (sensitivity + anchor pick)
- UPDATE: `scripts/score.py` (add `--judge-method` flag)
- UPDATE: `scripts/robustness_checks.py` (within-leg FDR)
- NEW: `data/2026-05-29-judge-methods/` (results)
- UPDATE: `ADVERSARIAL-REVIEW.md` (mark C3 fully DONE; add forward-looking section)
- UPDATE: `WRITEUP-2026-05-26.md` (sensitivity section + anchor swap)
- UPDATE: `evilrobots.lol/content/research/ai-bias-audit.md` (public-facing, voice preserved)
- UPDATE: `bias-study-release/` (mirror everything except internal-only docs)

## Verification

- Pre-registration commit is timestamped BEFORE any cross-method numbers exist in git history (`git log --follow JUDGEMENT-TOOL-PLAN.md` precedes `git log scripts/judge_methods.py` runs)
- Every method has a runnable command in DEVELOPER.md and a documented output schema
- Cross-method comparison table shows all 9 methods (or 7 if 8-9 deferred), no method silently dropped
- Anchor method ranks highest by mechanical rubric application; rubric cells defended in writing
- Within-leg FDR results land in robustness_checks.py output (paraphrase + OOD families show survivors at q=0.05)
- ADVERSARIAL-REVIEW.md updated: C3 marked DONE; forward-looking section added; every previous OPEN/PARTIAL item revisited
- Permalink content updated, voice preserved, citations to multi-method analysis added
- All commits made under the identity that owns the destination remote; the per-repo
  rule and the check that enforces it are maintainer-side and not part of this release

## Tradeoffs and risks

- **Compute cost:** Phase 3 is the heaviest — ~1-2 days bounded compute. Abliterated-Qwen judge is local (RTX 4090), fine. Closed-API judges (Claude / GPT-4.1) cost real money per scoring call, multiplied by methods. Budget: ~$50-150 across all method-2-7 runs at current pricing.
- **Time-to-publish-update:** ~6 working days end-to-end. The study's web-only publication state means no external deadline pressure, but the longer it sits with the old methodology surface-visible, the more chance a reviewer screenshots the current version before updating.
- **Method failure modes:** Adversarial-pair judge could degrade to incoherent argumentation in some cells; needs the existing coherence guard. Blind-condition judge requires careful redaction (no leakage of condition into the response text itself — some responses repeat the question stem).
- **Reviewer counter:** "Your method-quality rubric weights are themselves cherry-picked." Anti-defense: the rubric is pre-registered with rationale per cell, and weights are intuitive (circularity-reduction first, cost-to-run last). A reviewer who wants different weights can re-rank using the same per-cell scores — all data published.

## Anti-cherry-pick discipline (critical)

Phase 1 (pre-registration) commits BEFORE Phase 3 (running). The git log order is the proof.

The anchor method is mechanically determined by rubric × weights. We do NOT look at comparative bias-deltas across methods before the anchor pick is documented. After the anchor is fixed, ALL methods' results are reported in the supplementary table — no hiding.

If the anchor method turns out to support a *weaker* bias finding than the current ULTRAPLINIAN baseline, that's the result we publish. Methodology integrity > headline-result preservation.

## Locked decisions (2026-05-28)

1. **Method 8 (external benchmark anchoring):** INCLUDED. Run it.
2. **Paid experts:** DROPPED. Out of scope — we're building an LLM-driven methodology that doesn't bottleneck on human raters. No re-litigation.
3. **Anchor selection:** Single top-rubric method. (Weighted ensemble can be reported as supplementary.)
4. **Rubric weights:** Accepted as proposed (0.30 / 0.25 / 0.20 / 0.15 / 0.10).
5. **Permalink update timing:** Update immediately when Phase 6 lands.

Rubric scoring of each method is in companion file `RUBRIC-SCORES.md`, committed atomically with this lock.

## M5 abliterated serving (Method 2 prerequisite)

Method 2 (`--judge-method abliterated-qwen`) calls an OpenAI-compatible HTTP endpoint that serves the abliterated weights. The 4090 PC has CPU-only torch (verified: `torch 2.11.0+cpu`, `cuda available: False`), so abliterated inference must run elsewhere — typically the M5.

**Two viable serving paths on M5:**

1. **vLLM (Linux container or native on Mac via Docker Desktop)** — start with:
   ```
   vllm serve <path-to-abliterated-weights> --host 0.0.0.0 --port 8000 --served-model-name qwen2.5-7b-abliterated
   ```
2. **mlx-server (native Apple Silicon, MLX framework — what M5 already uses for abliteration itself)** — start with the MLX-compatible OpenAI shim from the OBLITERATUS / mlx-lm toolchain.

**Then from the 4090 PC** (where the study data lives):
```
export ABLITERATED_ENDPOINT="http://<m5-host>:8000/v1"
export ABLITERATED_MODEL="qwen2.5-7b-abliterated"   # or gemma-2-9b-abliterated
/c/Python314/python.exe scripts/score.py 2026-05-25-full --judge-method abliterated-qwen
```

Both the Qwen2.5-7B-abliterated weights (4090 PC at `obliteratus-output/`) and the Gemma-2-9B-abliterated weights (M5, per the 5-family weight-rung writeup) are candidates. Run Method 2 against both for cross-family abliteration sensitivity. Whichever survives the rubric weighting becomes the canonical anchor for the abliterated-judge result; the other reports as a supplementary row.

When the M5 endpoint is up and reachable, the existing sweep driver loop (`run_all_judge_methods.sh` or the inline bash variant) just needs `abliterated-qwen` added to the METHODS array.

## X-promotion strategy (Phase 6+, post-methodology-lock)

Once Phase 6 lands and the writeup + permalink reflect the multi-method anchor, the author goes to X (X Premium+ account, so long-form posts + edits available) to pick fights and drive traffic to the websites + books. Ammunition stack to draft when methodology is locked:

- **Image assets:** per-finding charts (per-model delta forest plot with CIs, cross-method agreement heatmap, abliteration dissociation scatter, paraphrase robustness reproducibility). Generated from existing data via matplotlib / plotly. 4-6 hero images.
- **Thread drafts:** `gorrie-write --venue social` produces variations: provocative ("Tested if frontier AI quietly takes the institution's side. It does."), understated (4-of-13-FDR-survivor receipt), educational (escalation-ladder explainer with images).
- **Pre-drafted reply templates:** for the predictable attack vectors — "your judges are biased" → link to multi-method section; "small n" → link to bootstrap CIs + FDR; "abliteration breaks the model" → link to A2b dissociation finding (text rewritten, stance flat).
- **Posting channel:** `@evilbotslol` is the natural launchpad (Evil Robots brand owns the AI-critique line). `gorrie-x` agent handles posting; `social-engage` skill drafts replies in voice.
