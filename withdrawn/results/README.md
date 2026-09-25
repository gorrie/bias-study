# `withdrawn/results/` — the study's earlier results, as reference

Thirty-nine results documents from the study's first two designs: the May 2026 judge-scored
study and its repair, the transition period on a retired 62-item external questionnaire, and the
pipeline and weight rungs of the escalation ladder. Each is kept with the text it was written
with, because it is the record of what was measured, how, and what was concluded at the time.
Several findings in them hold; many were narrowed or withdrawn by later work; all of them are
useful to anyone building an instrument of this kind, because they show what goes wrong and how
it was caught.

How to read them. Figures on the retired questionnaire are counts out of 62 and are not
comparable to the current battery's counts out of 32. Figures on the May corpus were computed
on the corpus as it stood that day; the repaired corpus under [`../../data/`](../../data/) is
the one to recompute from. Where a document here disagrees with
[`../../PAPER-below-the-floor.md`](../../PAPER-below-the-floor.md) or
[`../../CORRECTIONS.md`](../../CORRECTIONS.md), those are current, and
[`../../data/withdrawals.json`](../../data/withdrawals.json) is the single record of what is
withdrawn. §3 of the paper tells the story these documents record.

Paths in them are as written at the time. A May run they call `runs/<run>` is now
[`../../data/<run>`](../../data/); runs they name that are in neither directory were collected on
the retired questionnaire and are not shipped (see
[`../../prereg/README.md`](../../prereg/README.md)), and scripts they name that are not in
[`../../scripts/`](../../scripts/) were retired with that instrument.

Two documents from the same period sit at the repository root instead, because the README
lists them there:
[`../../RESULTS-2026-09-14-rung2-transform-audit.md`](../../RESULTS-2026-09-14-rung2-transform-audit.md)
(the jailbreak pipeline's obfuscation transform never fired) and
[`../../RESULTS-2026-09-15-rung2-decomposed.md`](../../RESULTS-2026-09-15-rung2-decomposed.md)
(what the pipeline applies is a system prompt, which moved one frontier model and not another).

## The weight rung and refusal

| document | what it found | where it stands |
|---|---|---|
| [`RESULTS-2026-08-28-refusal-ablation.md`](RESULTS-2026-08-28-refusal-ablation.md) | removing the refusal direction collapses XSTest discrimination on two models (0.801 to 0.486, 0.777 to 0.256); a keyword scorer finds no refusals where a judge finds half | holds on those two pairs; which refusal categories survive is model-specific. The later judge-scored dose series on Gemma-2-9B found no dose effect (paper §3.7) |
| [`RESULTS-2026-08-28-stance-survives-ablation.md`](RESULTS-2026-08-28-stance-survives-ablation.md) | on five families, judged stance moves by at most 0.2 under ablation while the wording changes | the wording change is established on one family of five; the stance result is a bound on a compressed scale |
| [`RESULTS-2026-08-30-withdrawal-was-wrong.md`](RESULTS-2026-08-30-withdrawal-was-wrong.md) | a greedy temperature-0 control reinstates the wording-change evidence | superseded: the control's own value sits inside the resampling band (paper §3.7) |
| [`RESULTS-2026-08-30-weight-rung-matched.md`](RESULTS-2026-08-30-weight-rung-matched.md) | on three arm-matched pairs, ablation moves answers | withdrawn the same day: every pair sits inside the requantisation band, which became a required control |
| [`RESULTS-2026-09-07-ablation-wave.md`](RESULTS-2026-09-07-ablation-wave.md) | the weight rung at n=5: two builds by one author move 8/9/9 sides, a third author's build 0/2/0 | the ablator is the effect; the two agreeing builds are near-copies (paper §3.7). Replaced on the battery by `runs/2026-09-25-local-gradient` |
| [`RESULTS-2026-09-12-ablation-termination.md`](RESULTS-2026-09-12-ablation-termination.md) | 24 of 63 ablation cells came back short; one family's ablated build runs to the token cap on 19 of 19 runs | holds as an observation: the builds that survive ablation are not a random sample |

## Refusal of the instrument

| document | what it found | where it stands |
|---|---|---|
| [`RESULTS-2026-08-30-instrument-refusal.md`](RESULTS-2026-08-30-instrument-refusal.md) | whole-instrument refusal depends on the condition; a 1,600-token cap was impersonating refusal | holds; the battery result is paper §5.4 |
| [`RESULTS-2026-08-31-refusal-by-vendor.md`](RESULTS-2026-08-31-refusal-by-vendor.md) | refusal is overwhelmingly a Google-family behaviour | superseded by the condition-controlled table in the next document and by the battery |
| [`RESULTS-2026-08-31-refusal-is-elicited.md`](RESULTS-2026-08-31-refusal-is-elicited.md) | refusal is elicited by the absence of a firm directive | holds, and carries to the battery (paper §5.4); its comparison with Cen et al.'s vendor ordering is withdrawn, because that paper states the ordering two ways |
| [`RESULTS-2026-09-05-frontier-v3.md`](RESULTS-2026-09-05-frontier-v3.md) | the newest Western frontier releases decline the balance instruction | holds on that design; the jurisdictional reading did not survive the corpus |
| [`RESULTS-2026-09-12-refusal-structure.md`](RESULTS-2026-09-12-refusal-structure.md) | refusal is whole-instrument and near-deterministic, so a pooled rate describes no model | holds; it is why the paper states refusal per model |

## Floors, order and drift

| document | what it found | where it stands |
|---|---|---|
| [`RESULTS-2026-08-29-pilot-gemma2.md`](RESULTS-2026-08-29-pilot-gemma2.md) | on one model, identity-free pressure sharpens answers rather than turning them | holds on Google models only; withdrawn as general |
| [`RESULTS-2026-08-30-noise-floor.md`](RESULTS-2026-08-30-noise-floor.md) | temperature 0 without a seed still varies; the floor is model- and condition-dependent | holds as method (every floor per model and condition); its directional claim reversed on a second model |
| [`RESULTS-2026-08-30-order-effect.md`](RESULTS-2026-08-30-order-effect.md) | presentation order moves more than any manipulation tested | narrowed: the order effect is generational (paper §5.2) |
| [`RESULTS-2026-08-30-access-tier.md`](RESULTS-2026-08-30-access-tier.md) | two access tiers of one model answer alike | withdrawn: its counts out of 62 were judged against detection limits computed on the battery. Re-asked as `runs/2026-09-25-serving-path` |
| [`RESULTS-2026-08-30-drift.md`](RESULTS-2026-08-30-drift.md) | newer versions suppress endpoint answers harder | withdrawn against the 97-pair same-version null a day later |
| [`RESULTS-2026-08-31-drift-does-not-replicate.md`](RESULTS-2026-08-31-drift-does-not-replicate.md) | 108 version transitions against an empirical same-version null | withdrawn: a null below its own detection limit. Re-measured on the battery, no step clears (paper §3.5) |
| [`RESULTS-2026-09-04-paraphrase-floor.md`](RESULTS-2026-09-04-paraphrase-floor.md) | the paraphrase floor on Röttger et al.'s data and on current models; run-to-run 3 / 5 / 15 of 62 | superseded with the instrument; the battery's union-against-pairwise comparison is paper §5.2 |
| [`RESULTS-2026-09-06-manipulation-floor-one-sitting.md`](RESULTS-2026-09-06-manipulation-floor-one-sitting.md) | the manipulation re-measured under one protocol | withdrawn the same day: it crossed protocols and one bimodal model set the p90 |
| [`RESULTS-2026-09-06-modal-resolution-and-the-inversion.md`](RESULTS-2026-09-06-modal-resolution-and-the-inversion.md) | the modal estimator has its own error, and the order-against-manipulation comparison inverts by model generation | holds as method; the battery version is paper §5.2 |
| [`RESULTS-2026-09-06-order-dependent-floors.md`](RESULTS-2026-09-06-order-dependent-floors.md) | three published floors changed with the filesystem's glob order | fixed: every glob is sorted |
| [`RESULTS-2026-09-06-order-floor-one-sitting.md`](RESULTS-2026-09-06-order-floor-one-sitting.md) | order and manipulation are the same size in one sitting | superseded with the instrument; the battery comparison is paper §5.1 |
| [`RESULTS-2026-09-06-wave-0.md`](RESULTS-2026-09-06-wave-0.md) | the barometer's first sitting, 31 models under four conditions | superseded by the 2026-09-16 wave on the battery |
| [`RESULTS-2026-09-07-between-model-signal.md`](RESULTS-2026-09-07-between-model-signal.md) | between-model differences exceed run-to-run noise | descriptive only; its ratio figures were withdrawn, and x-ai builds carry most floor tails |
| [`RESULTS-2026-09-07-local-2026-order-floor.md`](RESULTS-2026-09-07-local-2026-order-floor.md) | the hosted/local order gap is vintage, not quantisation or serving stack | holds on that design; the battery class split is paper §5.2 |
| [`RESULTS-2026-09-11-per-model-cards.md`](RESULTS-2026-09-11-per-model-cards.md) | per model, one of 31 carries a claim, and 22 have a run-to-run spread as large as their largest effect | holds as method |
| [`RESULTS-2026-09-12-lineage-exchangeability.md`](RESULTS-2026-09-12-lineage-exchangeability.md) | the 97-pair same-version null is four distributions, not one | superseded with the instrument; the battery's same-version null is paper §5.9 |

## Measurement and the judged design

| document | what it found | where it stands |
|---|---|---|
| [`RESULTS-2026-08-29-evidence-concordance.md`](RESULTS-2026-08-29-evidence-concordance.md) | a persona instruction cuts agreement with the documented answer from 95% to 24% | withdrawn: two-thirds of it is displacement restated (r = −0.825). The lesson kept is that a judged rubric cannot separate commitment from being pushed off the evidence |
| [`RESULTS-2026-08-30-conviction-frontier.md`](RESULTS-2026-08-30-conviction-frontier.md) | forced balance suppresses endpoint answers, and what replaces it does not matter on five of seven models | survived narrowed on that design; on the battery the placebo returns to baseline and the commitment directive overshoots it (paper §5.2) |
| [`RESULTS-2026-09-05-judge-lean.md`](RESULTS-2026-09-05-judge-lean.md) | the four-judge panel's own lean, and what five validations do not test | the argument holds; the figures are superseded by the repaired corpus (paper §3.2) |
| [`RESULTS-2026-09-05-token-cap-recollection.md`](RESULTS-2026-09-05-token-cap-recollection.md) | the May study was scored on truncated responses, and one model on empty ones | holds; it began the repair that produced `data/*-spliced` (paper §3.3) |
| [`RESULTS-2026-09-07-constrained-decoding-batch-size.md`](RESULTS-2026-09-07-constrained-decoding-batch-size.md) | constrained decoding replicates; asking for 62 answers in one array does not | a portable negative result; superseded with the instrument |
| [`RESULTS-2026-09-07-logit-scoring-fails-agreement.md`](RESULTS-2026-09-07-logit-scoring-fails-agreement.md) | logit scoring is feasible and fails its own pre-registered agreement check | a portable negative result: reversing the legend changes 48 of 62 positions |
| [`RESULTS-2026-09-12-convergent-validity.md`](RESULTS-2026-09-12-convergent-validity.md) | judged and forced-choice shifts on 24 models correlate at r = −0.12 | superseded by the same-items comparison, which finds agreement on direction only (paper §5.11) |
| [`RESULTS-2026-09-13-pipeline-rung-replicate.md`](RESULTS-2026-09-13-pipeline-rung-replicate.md) | the jailbreak-pipeline rung replicated at five samples per cell | its numbers reproduce; the reading of opposite directions was withdrawn by the decomposition at the root |
| [`RESULTS-2026-09-14-corpus-repair.md`](RESULTS-2026-09-14-corpus-repair.md) | the repaired May corpus and what it does to the published numbers | holds; the repaired corpus is the one every May figure is computed on |
| [`RESULTS-2026-09-14-I3-phase0.md`](RESULTS-2026-09-14-I3-phase0.md) | with a placebo arm, the judged B − A contrast reads instruction-following, not a lean | the record of that withdrawal for `data/2026-09-13-i3-phase0`, whose records ship |

## Process

| document | what it found | where it stands |
|---|---|---|
| [`RESULTS-2026-09-01-hostile-read.md`](RESULTS-2026-09-01-hostile-read.md) | a hostile read of the assembled paper | a review record; its findings are in [`../../CORRECTIONS.md`](../../CORRECTIONS.md) |
| [`RESULTS-2026-09-02-forked-statistics.md`](RESULTS-2026-09-02-forked-statistics.md) | a bootstrap fix reached the public copy of a script and not the private one | fixed; it is why `scripts/check_no_fork.py` exists |
