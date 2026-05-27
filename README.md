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
cadence catches the slope. Contributions are welcome and expected — reproduce a run, add a model
or topic, or submit a finding. See [`CONTRIBUTING.md`](CONTRIBUTING.md) and the
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

## Headline findings

- **Vendor-class differential (prompt rung).** US-closed frontier models (Anthropic,
  OpenAI, Google Gemini, xAI Grok) unmask far more than European, Chinese, or open-weight
  classes (us-closed mean Δ +0.572 vs open-weight ≈ 0). At the per-model level, **4 of 13
  effects survive a Benjamini-Hochberg FDR correction** (Opus 4.7, Grok 4.3, GPT-4.1,
  Mistral Large); DeepSeek V3.2 is suggestive but not confirmed. The class *direction*
  replicates under N=5 averaging.
- **Anthropic Opus arc.** Claude Opus trends upward across five versions, every version's
  unmask CI-significant, **+0.27 → +0.90** from 4.0 to 4.7 (~3× the baseline; an upward
  trend, not strict monotonicity — 4.5 wobbles within noise).
- **Grok dose-response.** Under the five-step gradient Grok 4.3 reaches the full v1
  magnitude (3.00 → **5.00** across the ten neutral questions) at the opinionated-persona
  condition; the simple "what do you think?" unmask already moves it to 3.63, and the
  layered G0DM0D3 pipeline lifts it further to **4.20**.
- **GPT-5 retracted / indeterminate.** GPT-5's delta is not distinguishable from zero and
  it is the study's noisiest model (σ = 1.14, 2× any other). The earlier "GPT-4.1 → GPT-5
  reversal" is **not supported** — GPT-5 is indeterminate, not reversed.
- **Weight-rung dissociation.** Abliterating the refusal direction from four open-weight
  families (fp16, OBLITERATUS `advanced` SVD) removes refusals and rewrites **~70% of the
  political wording** (word-set Jaccard ≈ 0.3, confirmed deterministic at temperature 0)
  yet moves the institutional-skepticism **stance ≤ 0.10**. The refusal direction and the
  institutional lean are **dissociable.**
- **Sycophancy control.** A reversed-premise pass (topics reframed to *invite* deference)
  shows **all five tested models hold within ≤ 0.40** of their neutral-framing stance —
  the unmask measures a genuine institutional lean, not generic agreeableness.
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

The weight rung (OBLITERATUS abliteration) needs a 24 GB GPU, Docker, and the fp16 base
weights; the pipeline rung needs the G0DM0D3 server. **`scripts/run_barometer.sh`** drives
the full escalation ladder end to end, and **`DEVELOPER.md`** documents every script, the
exact commands, and the hard constraints (you cannot abliterate a quantized model; a 24 GB
GPU caps abliteration at ~7–9B at fp16). Hostile peer review and the
objection→fix map are in **`ADVERSARIAL-REVIEW.md`**.

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

- **OBLITERATUS** — refusal-direction abliteration. <https://github.com/elder-plinius/OBLITERATUS> (pinned `d6af36f`, 2026-04-01).
- **G0DM0D3** — elicitation / jailbreak reference (STM hedge-strip, Parseltongue). <https://github.com/elder-plinius/G0DM0D3> (pinned `4d4b3e0`, 2026-03-25).
- **Arditi et al. (2024)**, *Refusal in Language Models Is Mediated by a Single Direction*, arXiv:[2406.11717](https://arxiv.org/abs/2406.11717) — the refusal-direction method the weight rung ablates.
- **OpenRouter** — multi-vendor API gateway, <https://openrouter.ai/>.

## License

Code: MIT (see [`LICENSE`](LICENSE)). Data and writeup are released for open reproduction and review.

## Citation

> Gorrie, I. (2026). *The Hedge Is the Bias: A Multi-Vendor, Multi-Generation Audit of
> Institutional-Skepticism Framing in Large Language Models.*

---

**Related work:** these findings are also presented in narrative form for a general audience — [evilrobots.lol](https://evilrobots.lol).
