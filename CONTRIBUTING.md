# Contributing to the Bias Measurement Observatory

This repository is a **re-runnable instrument**, not a frozen paper. The headline
findings are a snapshot; the value compounds when the study is re-run on new models,
new vendors, and new topics over time, and when independent replicators confirm (or
refute) the numbers. Contributions are welcome via GitHub issues and pull requests.

Everything here runs on **Linux, macOS, and Windows**. The pipeline is plain Python
3.11+; only the optional weight rung needs Docker + a 24 GB GPU. See
[`DEVELOPER.md`](DEVELOPER.md) for per-OS setup.

## Ground rules

- **A delta is a finding only if its 95% CI excludes zero.** Bootstrap CIs are
  computed by `scripts/ci_analysis.py`. Do not report a point estimate as a result
  without its interval.
- **Doc-reality discipline.** Never describe a rung as "run" until the records carry
  its real field values (`g0dm0d3_pipeline`, `obliteratus_applied`). The pipeline rung
  is currently *specified, not executed* — keep it labelled that way.
- **Cite, don't vendor.** OBLITERATUS and G0DM0D3 are external; clone them from upstream
  at the pinned commits in [`README.md`](README.md). Never copy their source in here.
- **Secrets never ship.** Keys and `.env` files stay local. Copy `.env.example` to
  `.env`; the real `.env` is gitignored. Scan before any push.
- **Scripts stay LF.** `.gitattributes` enforces LF on `*.sh` and `*.py` so the
  shebangs work on every platform — do not commit CRLF scripts.

## How to reproduce a run

The prompt rung is reproducible by anyone with an OpenRouter key, with no GPU:

```bash
pip install -r requirements.txt
cp .env.example .env          # put your key in OPENROUTER_API_KEY
python scripts/run_study.py --positions mild,neutral,pointed --date $(date +%F)
python scripts/score.py $(date +%F) \
  --judge "anthropic/claude-haiku-4.5,openai/gpt-4.1,google/gemini-2.5-flash,deepseek/deepseek-v3.2"
python scripts/aggregate.py $(date +%F)
python scripts/ci_analysis.py
python scripts/robustness_checks.py
```

To re-derive the published numbers **without spending any API budget**, every scored run
ships under `data/`. Re-run the analysis steps against an existing run, e.g.
`python scripts/aggregate.py 2026-05-26-variance`. `score.py --skip-classifier` runs
heuristic-only (zero API calls).

The full toolchain (weight + pipeline rungs) and the one-command driver
`scripts/run_barometer.sh` are documented in [`DEVELOPER.md`](DEVELOPER.md).

## Submitting a reproduction report

Independent replication is the single most valuable contribution. Re-run the prompt rung
(or any rung you can), then **open a [reproduction report issue](.github/ISSUE_TEMPLATE/reproduction-report.md)**
with: the run date, the models and judges you used, your per-model deltas with CIs, and
whether the **vendor-class direction** and any FDR-surviving effects replicated. Confirmations
*and* failures-to-replicate are both wanted — null replications are findings.

## Proposing a new model, vendor, or topic

- **New model / vendor family** — open a
  [new-model request](.github/ISSUE_TEMPLATE/new-model-request.md). For OpenRouter-reachable
  models, adding it is usually a one-line entry in the `DEFAULT_FRONTIER` list in
  `scripts/run_study.py` and a class hint in `aggregate.py` / `analysis.py`. For a whole new
  open-weight family on the abliteration leg, see the `abliteration-run` skill.
- **New topic / question** — the question set is `protocol/questions.md` (v2 format, with
  `mild` / `neutral` / `pointed` / `reversed` positions per topic). Keep new items on the
  **institutional-skepticism** axis the study measures; propose them in a
  [finding submission](.github/ISSUE_TEMPLATE/finding-submission.md) or PR with the rationale
  and the four position variants.

## Submitting a finding

Surfaced a pattern in the data (a drift, a sign flip, a new vendor-class signal)? Open a
[finding submission](.github/ISSUE_TEMPLATE/finding-submission.md) with the run(s), the
script output that supports it, and the CI. Findings that survive FDR correction and whose
CI excludes zero are candidates for the writeup.

## The quarterly "barometer" cadence

The observatory re-runs on a **quarterly cadence, or on any major frontier release**. Each
pass is an immutable `data/<date>/` directory, diffed against the prior quarter with
`scripts/drift_report.py` and `scripts/drift_timeseries.py`. That longitudinal diff *is* the
barometer — it tracks how model bias drifts across vendor generations over time. The
`agents/bias-barometer.md` orchestrator and the `bias-study-prep` / `bias-study-report` skills
codify the full cadence. If you want to drive a quarterly pass, start there.

## Pull requests

- Run `python -m py_compile scripts/*.py` and `bash -n scripts/*.sh` before opening a PR.
- Keep scripts cross-platform: `python3`, `#!/usr/bin/env` shebangs, no hardcoded absolute
  paths, env-var resolution for keys and model dirs.
- New runs go in their own `data/<date>/` directory — never mutate an existing run.

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). By participating you
agree to uphold it.
