# `withdrawn/results/` — results documents whose findings were withdrawn or narrowed

Six results documents from before the current instrument, kept with the text they were
published with. Each is here because [`../../data/withdrawals.json`](../../data/withdrawals.json)
or the paper cites it as the record of what was claimed and when. Nothing in them is measured
on the Ratchet battery, and where a document here disagrees with
[`../../PAPER-below-the-floor.md`](../../PAPER-below-the-floor.md) or
[`../../CORRECTIONS.md`](../../CORRECTIONS.md), those are right.

| document | what it found | status |
|---|---|---|
| [`RESULTS-2026-08-30-access-tier.md`](RESULTS-2026-08-30-access-tier.md) | access tiers of one model are indistinguishable | withdrawn 2026-09-17 (`CORRECTIONS-2026-09-17-power.md`): counts out of the retired questionnaire judged against detection limits computed on the battery. Re-asked as a pre-registered serving-path arm, `runs/2026-09-25-serving-path` |
| [`RESULTS-2026-08-31-drift-does-not-replicate.md`](RESULTS-2026-08-31-drift-does-not-replicate.md) | 108 version transitions across 30 lineages against an empirical same-version null: version drift does not replicate | withdrawn 2026-09-17: a null below its own detection limit, undecided rather than refuted |
| [`RESULTS-2026-09-07-ablation-wave.md`](RESULTS-2026-09-07-ablation-wave.md) | the weight rung at n=5 on the retired questionnaire: direction holds under ablation, intensity belongs to the ablator | superseded with the instrument; the copy in `results/` points here. The pre-registered replacement on the battery is `runs/2026-09-25-local-gradient` |
| [`RESULTS-2026-09-07-constrained-decoding-batch-size.md`](RESULTS-2026-09-07-constrained-decoding-batch-size.md) | constrained decoding replicates; asking for 62 answers in one array does not | superseded with the instrument; the copy in `results/` points here |
| [`RESULTS-2026-09-07-logit-scoring-fails-agreement.md`](RESULTS-2026-09-07-logit-scoring-fails-agreement.md) | logit scoring is feasible and fails its own pre-registered agreement check against sampled answers | superseded with the instrument; the copy in `results/` points here |
| [`RESULTS-2026-09-14-I3-phase0.md`](RESULTS-2026-09-14-I3-phase0.md) | I3 Phase 0: the B−A contrast reads instruction-following, not a lean | the withdrawal record itself for `data/2026-09-13-i3-phase0`; its records ship so the finding can be checked |

The private study tree keeps a further 36 superseded results documents from the same period
under its own `withdrawn/results/`. Every figure in them was measured on either the retired
62-item external questionnaire or the May judged corpus; the ones that describe the May corpus
are summarised in [`../../results/WRITEUP-2026-05-26.md`](../../results/WRITEUP-2026-05-26.md),
and the ones that measured the retired questionnaire cannot be recomputed from this repository.
