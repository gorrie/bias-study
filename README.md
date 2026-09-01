# The Hedge Is the Bias

**A multi-vendor, multi-generation audit of institutional-skepticism framing in large language models.**

A reproducible study of how aligned LLMs shift their framing on contested-institution
topics when the "be fair to both sides" instruction is removed — and a test of *where*
that bias lives, by escalating force from the prompt, to an elicitation pipeline, to the
model weights themselves.

Headline thesis: **the hedge is the bias signature.** A model that answers a contested
political question with heavy both-sides hedging is not neutral — it is masking a lean at
the alignment-training layer. The mask comes off in proportion to the force applied to
it, *except where it is bolted in at the weights, where force does nothing.* The study's
spine is that **force-escalation ladder**:

The result is also robust to the obvious reviewer attack on LLM-as-judge studies. The same
data was re-scored under five materially different judging procedures, including one with
the **refusal direction surgically removed from the judge's weights** (abliterated
Gemma-2-9B-IT). Median per-model contamination delta against the cross-vendor baseline is
**0.062** across 47 model-runs — inside the pre-registered 0.10 robust band. The bias is
in the systems being scored, not in the panel scoring them. Full multi-method analysis in
§5.8 of the writeup; the abliterated judge that leg relies on is characterized on its own
terms — the abliteration dose-response (and its coherence cliff), and two findings still under
remediation after adversarial review (a refusal/flinch decoupling and a single-template
"documented-exposure" flinch observation) — in
[`results/THE-WASH-2026-06-10.md`](results/THE-WASH-2026-06-10.md) (see its §F review status).

| Rung | Force | Tooling | Result |
|------|-------|---------|--------|
| **1. Prompt** | remove the fairness instruction; A→E unmask gradient | OpenRouter / Ollama | the lean unmasks, dose-responsively |
| **2. Pipeline** | hedge-strip + obfuscation, layered | G0DM0D3 server | only the layered stack adds force, to a ceiling |
| **3. Weights** | ablate the refusal direction | OBLITERATUS (fp16) | text rewrites ~70%, stance does **not** move |

## A standing instrument, not a snapshot

This repository is meant to be **re-run, not just read** — a *bias measurement observatory*.
The protocol is built to re-run on a roughly quarterly cadence so the public record tracks how
model framing **drifts** as new versions ship. The Anthropic Opus arc (+0.27 → +0.90 from 4.0 to
4.7, inside a single year) is the case in point: a one-time snapshot catches the level; only the
cadence catches the slope.

**Contributions and challenges are the whole point.** If you find a number you can't
reproduce, a model whose lean changed since the run shipped, a topic the study should be
testing, a methodological objection it doesn't already address — open an issue:
[github.com/gorrie/bias-study/issues](https://github.com/gorrie/bias-study/issues). The
adversarial-review file ([`ADVERSARIAL-REVIEW.md`](ADVERSARIAL-REVIEW.md)) is structured
exactly so a new objection can land as a tracked item and either get FIXED with a re-run
or get rebutted in writing. The cross-method agreement matrix is the reproducibility check:
a re-runner who gets different numbers can compare against the committed JSON and surface
exactly where the divergence sits. See [`CONTRIBUTING.md`](CONTRIBUTING.md) and the
[issue templates](.github/ISSUE_TEMPLATE/). The `agents/` + `skills/` directories hold the
orchestration for running the full ladder as a repeatable instrument.

## Scope

This measures one axis — **institutional skepticism**: on a topic where an institution's
framing is contested, does the model side with the institution (low) or with the
questioner of it (high), and how does that shift when a fairness instruction is removed?
That is a narrower, more defensible construct than "political lean" in general; the
question set is drawn from a civil-liberties / institutional-power surface and is not a
full left–right battery. Read every finding as a claim about institutional-skepticism
framing, not global political ideology.

The corpus: 36+ frontier models from 13 vendor families, scored 1–5 by a four-judge
cross-vendor median-consensus panel ("ULTRAPLINIAN"). Every per-model delta is reported
with a bootstrap 95% CI; **a delta is a finding only if its CI excludes zero.**

## Update, 2026-08-31 — re-measured on a forced-choice instrument

The findings below are the May 2026 study and stand as recorded. A second measurement pass
put the same subject matter to a **forced-choice instrument** — 62 externally authored
propositions, four options, no neutral answer, **no LLM judge anywhere in the scoring
path** — across 1,643 runs, 155 models and thirteen vendor families. It confirmed one headline, narrowed
another, withdrew the framing of a third, and produced the thing the original study lacked:
**the noise floors a measurement on this instrument has to clear.**

**The floors.** Each is movement produced by a factor nobody claims is political — same
instrument, same model, same settings, in items moved of 62:

| factor | side-flip p90 | endpoint p90 |
|---|---:|---:|
| presentation order — 7–14B open-weight, 2024 generation | 14 | 9 |
| presentation order — frontier API, 2026 | **4** | 9 |
| same-version variants (size / mode / snapshot / tier), 97 pairs | 12 | 22 |
| requantisation, same weights Q4→Q8 | 10 | 3 |
| refusal-direction ablation, arm-matched | 9 | 14 |
| *deliberate manipulation (balance → commit)* | *14* | *26* |

**Splitting the order row by model class is the most important line in this table, and an
earlier version of this section pooled it.** Reordering the questionnaire is a large effect on
the models this literature was mostly built on and a small one on the models shipping now —
Röttger et al. predicted exactly that in 2024 and nobody had measured it.

**What does not shrink is the same-version null.** On those same frontier models: order p90 4,
two models of one version p90 12, deliberate manipulation p90 14. The nuisance factor that
matters on a current model is not how the sheet was shuffled. It is which variant of the model
was measured, and that one is the size of the manipulation.

**Confirmed — the weight-rung dissociation.** It holds and strengthens. At temperature 0,
where a greedy model reproduces itself exactly, stock and abliterated builds share ~30% of
their political wording while stance does not move. Two independent measurements agree.

**Narrowed — "the hedge is a layer over a position."** Against a control arm with **no
system prompt at all**, a forced-balance instruction suppresses how strongly a model
commits: six of seven frontier models strictly one-directional, four of them significantly. But removal restores
commitment without relocating position, and *anything* removes it — a bare question, a
commitment instruction, or a placebo about reading carefully with no stance content.
Nothing is revealed; a suppression stops.

**Undecided, and previously published here as withdrawn — that force reveals a concealed
position.** Position moves 0–6 items of 62 under prompt pressure on the four local families
and up to 14 at temperature 0 on the frontier. Those were read as nulls. They are not:
`scripts/power.py` puts this instrument's minimum detectable effect at **16 items of 62**
against the pooled presentation-order floor, and 11 against the same-version floor — the second
being the one that governs a modern study. Four of five
published nulls fall below their own detection limit, version drift among them. The claims
are undecided rather than refuted, which is a different verdict and not a restoration.

The fifth null inverted: qwen2.5-14B moves 12 items under ablation against a detection limit
of 9, so that pair shows real stance movement. The dissociation holds on the other two
arm-matched pairs and on the temperature-0 measurement, not across all three.

**New — refusal is elicited, not intrinsic.** Across the 32 models measured under both arms, eight decline all 62 propositions when the prompt carries no directive — 37 refusals in 449 runs, Google highest at 27% — and **not one of them declines even once** under a directive prompt: 347 runs, zero refusals. What abolishes it is not the content of the instruction, since a placebo with no stance content works as well as a demand to commit. It is the presence of a firm instruction at all. Measurable only because invalid runs are retained rather than
discarded as collection errors. The decline survives reordering: three Google models across three presentation orders refuse 24 of 27 runs, so it is not an artifact of the sequence the propositions arrive in.

### What ten published studies do and don't control for

We read them — main text, appendices, and deposited data and code where it exists — and
recorded which controls each one runs with the sentence proving it. `data/controls-audit.json`
holds the record; `scripts/controls_audit.py --strict` refuses to render a verdict about
someone else's paper that rests on our notes rather than on the paper.

Reading them cost us four claims, every one in the same direction:

| we had claimed | the paper actually says |
|---|---|
| nothing in this literature computes a floor | Röttger reported paraphrase instability at 14 and 23 items of 62, in 2024 |
| no study reports a detection limit | Domínguez-Olmedo report power ≥ 0.98 at effect size 0.1 |
| we complement Kamal on quantisation | their appendix reverses sign between precisions; we are the only measurement |
| we invert Cen's vendor refusal ordering | their introduction and their results section disagree with each other |

Two columns survive at zero across all ten: **no detection limit reported**, and **no
same-version null reported as a distribution** — though most of them have the pairs sitting in
their own model tables, and one paper removes them deliberately, "to ensure a more varied
sample."

The sharpest specific: Liu et al. (2025) report a rightward drift between GPT snapshots. Their
rule deletes an entire 62-item test if any single answer is unusable. We counted from their own
deposited files — 11.18% of items unevaluable in the treatment arm, 0.00% in the control, with
the refusals concentrated on the most charged propositions — and the surviving test counts
reproduce their published table exactly. Their own non-bootstrapped rows show no significant
shift. Details, including the three lines of their code that carry it, are in the companion
research directory. We can see any of this only because they published their raw data.

### And the corrections to us

Ten claims withdrawn or narrowed, the founding thesis among them. Then the correction to the
correction: every control we ran was aimed at claims asserting an effect and none at claims
asserting absence, so four of five of our own nulls turned out to sit below what the instrument
can detect. Undecided is not refuted, and it is not a restoration either.

Every defect found in this project was a number typed into a document. Not one was in the code.
Three gates now exist because of that: `gen_paper.py --check` (tables regenerate),
`key_numbers.py --check` (the sentences quoting them still match), and `controls_audit.py
--strict` (no claim about another study from a note).

**New — a same-version null.** 97 pairs of models differing in size, mode, snapshot or tier
but not version. Median 5 side-flips, p90 12. Any version-over-version comparison is a
single draw from that distribution, and no study in this literature reports such a control.

**Also withdrawn — the drift claim.** Against that null, 3 of 108 version transitions clear
both p<0.05 and the null p90; two are into the same model and the third runs the opposite
direction. An earlier three-lineage version of this result held only against a three-point
null.

Detail, data and the pre-publication gate that enforces these controls are in the
companion research directory. Ten claims were withdrawn or narrowed during this pass,
including the study's own founding thesis; the corrections are recorded in place rather
than removed.

## Headline findings

- **Vendor-class differential (prompt rung).** US-closed frontier models (Anthropic,
  OpenAI, Google Gemini, xAI Grok) unmask far more than European, Chinese, or open-weight
  classes (us-closed mean Δ +0.572 vs open-weight ≈ 0). At the per-model level, **4 of 13
  effects survive a Benjamini-Hochberg FDR correction** (Opus 4.7, Grok 4.3, GPT-4.1,
  Mistral Large); DeepSeek V3.2 is suggestive but not confirmed. The class *direction*
  replicates under N=5 averaging.
- **Anthropic Opus arc.** Claude Opus trends upward across five versions, every version's
  unmask CI-significant, **+0.27 → +0.90** from 4.0 to 4.7 (~3× the baseline; an upward
  trend, not strict monotonicity — 4.5 wobbles within noise). *(2026-08-31: a same-version null of 97 pairs, median 5 side-flips and p90 12, was not available when this was measured. Version-arc claims on this instrument should be read against it -- see the update above.)*
- **Grok dose-response.** Under the five-step gradient Grok 4.3 reaches the full v1
  magnitude (3.00 → **5.00** across the ten neutral questions) at the opinionated-persona
  condition; the simple "what do you think?" unmask already moves it to 3.63, and the
  layered G0DM0D3 pipeline lifts it further to **4.20**.
- **GPT-5 retracted / indeterminate.** GPT-5's delta is not distinguishable from zero and
  it is the study's noisiest model (σ = 1.14, 2× any other). The earlier "GPT-4.1 → GPT-5
  reversal" is **not supported** — GPT-5 is indeterminate, not reversed.
- **Weight-rung dissociation.** Abliterating the refusal direction from five open-weight
  families (fp16, OBLITERATUS `advanced` SVD — Qwen2.5-7B, Mistral-7B-v0.3, Llama-3.1-8B,
  DeepSeek-R1-Distill-Qwen-7B on a 24 GB CUDA GPU; Gemma-2-9B-it added natively on Apple
  Silicon's Accelerate/LAPACK, which cleared the MKL `SSYEVD` SVD failure that blocked
  Gemma-2 on the 4090) removes refusals and rewrites **~70% of the political wording**
  (word-set Jaccard ≈ 0.3, confirmed deterministic at temperature 0) yet moves the
  institutional-skepticism **stance ≤ 0.10**. The refusal direction and the institutional
  lean are **dissociable.** *(Confirmed and strengthened 2026-08-31 -- see the update above.)*
- **Sycophancy control.** A reversed-premise pass (topics reframed to *invite* deference)
  shows **all five tested models hold within ≤ 0.40** of their neutral-framing stance —
  the unmask measures a genuine institutional lean, not generic agreeableness.
- **Judge-method robustness.** Re-scoring the entire study under five alternative judging
  procedures — abliterated open-weight judge (M2), grok-solo (M4), adversarial-pair (M5),
  reversed-rubric (M6), blind-condition (M7) — produces 84–91% exact-match against the
  ULTRAPLINIAN-4 baseline across 1,650–1,743 paired records each. Median per-model
  contamination delta is **0.062** across 47 model-run pairs, inside the pre-registered
  ≤ 0.10 robust band. The judges are not laundering the result; the bias is in the
  systems-under-test, not the panel scoring them.
- **Transparency-asymmetry.** Weight-level verification is *only possible on open weights.*
  The closed frontier models that show the largest prompt-rung unmask are
  un-abliteratable by construction — an accountability gap independent of which way any
  closed model leans.

Full analysis with tables and caveats: [`results/WRITEUP-2026-05-26.md`](results/WRITEUP-2026-05-26.md).

## Reproduce it

### Prompt rung (anyone with an OpenRouter key)

Requires Python 3.11+ and an [OpenRouter](https://openrouter.ai/) API key — all models,
including the judges, are called through OpenRouter, so no per-vendor keys are needed.

```bash
pip install -r requirements.txt
cp .env.example .env          # put your key in OPENROUTER_API_KEY

# 1. Generate raw responses (model × question × A/B condition)
python scripts/run_study.py --positions mild,neutral,pointed --date $(date +%F)

# 2. Score with the 4-judge cross-vendor median consensus
python scripts/score.py $(date +%F) \
  --judge "anthropic/claude-haiku-4.5,openai/gpt-4.1,google/gemini-2.5-flash,deepseek/deepseek-v3.2"

# 3. Aggregate → per-model / per-topic / per-question CSVs + manifest
python scripts/aggregate.py $(date +%F)

# 4. Statistics: bootstrap CIs + inter-judge agreement, then FDR + length control
python scripts/ci_analysis.py
python scripts/robustness_checks.py
```

To re-derive the published numbers without spending any API budget, the full scored data
ships in `data/` — re-run steps 3–4 against any existing run, e.g.
`python scripts/aggregate.py 2026-05-26-variance`.
`score.py --skip-classifier` runs heuristic-only scoring (hedge ratio, refusal class) with
zero API calls.

### Full toolchain (weight + pipeline rungs)

The weight rung (OBLITERATUS abliteration) needs the fp16 base weights and either (a) a
24 GB CUDA GPU + Docker (`obliteratus:gpu`, driven by `scripts/run_abliteration_sweep.sh`)
or (b) a 32 GB+ Apple Silicon Mac running OBLITERATUS natively (`scripts/run_abliteration_native.sh`,
which routes the SVD `eigh` through Accelerate/LAPACK via `PYTORCH_ENABLE_MPS_FALLBACK=1`).
The pipeline rung needs the G0DM0D3 server. **`scripts/run_barometer.sh`** drives the full
escalation ladder end to end, and **`DEVELOPER.md`** documents every script, the exact
commands, and the hard constraints (you cannot abliterate a quantized model; a 24 GB GPU
caps abliteration at ~7–9B at fp16; a 32 GB M5 fits up to ~9B but not 14B+). Hostile peer
review and the objection→fix map are in **`ADVERSARIAL-REVIEW.md`**.

## Repository layout

```
protocol/   Study spec — question set, scoring rubric, record schema,
            run protocol, aggregation rules.
scripts/    Pipeline: run → score → aggregate → analyze, bootstrap CIs + FDR,
            and the weight-rung / pipeline-rung drivers.
data/       Every run in full: raw model responses, 4-judge scored records,
            aggregated CSVs, and manifests.
results/    The writeup.
skills/     Operator runbooks for re-running the study (the quarterly barometer).
```

## Tools cited (referenced, not vendored)

Clone these from upstream at the pinned commits to reproduce the pipeline and weight rungs:

- **OBLITERATUS** — refusal-direction abliteration. <https://github.com/elder-plinius/OBLITERATUS> (pinned [`d6af36f`](https://github.com/elder-plinius/OBLITERATUS/commit/d6af36f), 2026-04-01).
- **G0DM0D3** — elicitation / jailbreak reference (STM hedge-strip, Parseltongue). <https://github.com/elder-plinius/G0DM0D3> (pinned [`4d4b3e0`](https://github.com/elder-plinius/G0DM0D3/commit/4d4b3e0), 2026-03-25).
- **Arditi et al. (2024)**, *Refusal in Language Models Is Mediated by a Single Direction*, arXiv:[2406.11717](https://arxiv.org/abs/2406.11717) — the refusal-direction method the weight rung ablates.
- **OpenRouter** — multi-vendor API gateway, <https://openrouter.ai/>.

## Companion projects

- **[ratchet-mcp](https://github.com/gorrie/ratchet-mcp)** — MCP server + curated dataset of named persons & institutions across the US legal / regulatory / financial / multilateral control grid (454 persons / 388 institutions / 948 edges at v0.2; every record cites ≥ 2 primary sources; CI-gated). The institutional-infrastructure side of the same argument this bias study makes at the model layer — the people, the pipelines, and the documented adjacencies the closed-vocabulary plays system makes queryable. Companion to *The Ratchet: How Safety Infrastructure Became the Control Grid*. Re-sampled periodically as a longitudinal bias-drift instrument.
- **The Wash** ([`results/THE-WASH-2026-06-10.md`](results/THE-WASH-2026-06-10.md)) — the symmetric framing-detector built on this study's abliterated-judge spine (the §5.8 Method-2 anchor). Characterizes the abliterated judge directly: the abliteration dose-response and its coherence cliff, the refusal/flinch decoupling, and a documented-register flinch **confirmed** by the 2026-06-11 multi-template re-run (CI-backed: aligned judges over-flag documented institutional criticism the spine passes — gap +0.16 on plain sourced facts, +0.24 on juxtaposed, Wilson CIs disjoint from the spine; spine validated as a discriminator; magnitude corrected down from the single-template run — see §F). Same instrument, turned on the judge.

## License

Code: MIT (see [`LICENSE`](LICENSE)). Data and writeup are released for open reproduction and review.

## Citation

> Gorrie, I. (2026). *The Hedge Is the Bias: A Multi-Vendor, Multi-Generation Audit of
> Institutional-Skepticism Framing in Large Language Models.*

---

**Related work:** these findings are also presented in narrative form for a general audience — [evilrobots.lol](https://evilrobots.lol).
