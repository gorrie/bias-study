# Corrections — September 8, 2026

Prepared from baseline 40197d9. The original raw and scored records remain unchanged.
This correction is on a local review branch; publication of the held v2 package is separate.

## Empty responses and derived analyses

The primary `data/*/scored/*.jsonl` corpus has 5,051 records. Of 561 unusable responses,
466 have classifier scores even though their response text is empty and `ok` is true.
The [inventory](results/response-quality-2026-09-08.json) records each affected file,
line, question/model/condition and source-file SHA-256. Alternate `scored-*` directories
are outside this first audit and remain open work.

`score.py` now skips empty/whitespace responses before calling any judge. CI/FDR and
paired analyses use a shared eligibility loader, disclose exclusions on stderr and
preserve substantive refusals as a separate category. A run with no eligible A/B
analysis returns nonzero. These corrected views do not rewrite historical scores.
Other aggregate/drift/chart/cross-method readers still need the same migration.

On the main run, 33 empty records are excluded. Five models still have bootstrap CIs
excluding zero and four still survive the existing FDR calculation. The GLM result now
rests on only three eligible A/B pairs, which cannot establish equivalence or no bias.

| Judge agreement | Historical | Corrected |
|---|---:|---:|
| Items contributing judge pairs | 740 | 715 |
| Exact pairwise agreement | 0.824 | 0.827 |
| Unanimous items | 0.700 | 0.710 |
| Mean pairwise absolute difference | 0.239 | 0.236 |

G3 retains the old reference as provenance and tests the dated corrected reference.
The other main-run outcome gates remain unchanged. Across the five-run determinism
check, 44 eligible CI cells remain, versus 46 before filtering. Missingness may be
systematic; exclusion alone does not remove selection bias or validate the rubric.

Reproduce without network calls:

```text
python scripts/audit_response_quality.py
python scripts/audit_response_quality.py --check
python scripts/ci_analysis.py 2026-05-25-full
python scripts/robustness_checks.py 2026-05-25-full
python scripts/selftest_analysis.py
python -m pytest tests/ -q
```

The audit `--check` intentionally exits 1 while historical empty records retain scores.
Its inventory is a correction record, not a request to delete or rescore original evidence.

## Corpus routing and paired estimation

`STUDY_ROOT` is now respected. When both `data/` and `runs/` exist, a single populated
run container must be identifiable; ambiguity fails instead of silently choosing data/.
An invalid explicit root never falls back to the public corpus. Four entry points have
two-corpus subprocess regressions: CI, robustness, paired analysis and manifest validation.
Collectors and other v1 readers are not yet certified for private-corpus forwarding.

Paired analysis previously pooled scores across models under `(pair_id, arm)` keys.
It now rejects mixed models unless `--model` selects one. The same selection and response
eligibility apply to the stem control. This prevents accidental model pooling; it does
not validate the actor-swap construct, rubric transfer or a multi-model testing policy.

## Interpretation and current release scope

The README and writeup below retain historical interpretations. They do not establish
that hedging conceals a belief, that a change in rhetoric reveals a latent stance, or
that refusal and stance are separate mechanisms. The later private forced-choice study's
MDE-as-verdict and pooled-model-variant-null claims are being corrected separately.
Those unpublished corrections are not a new validated public bias benchmark.

The useful next direction is calibrated detection of errors in applying explicit evidence
and rules, with responsibilities held fixed across actor labels. Calibrate scorers and
missingness handling before expanding the model panel. See BACKLOG.md for remaining work.
