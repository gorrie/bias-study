# Pre-registrations

Analysis plans written **before** the data they analyse was collected.

## Why these are here

A pre-registration that lives only in the author's working tree is a private note. Its entire
function is that a reader can check the plan was fixed before the numbers were seen, and that
requires the plan to be public and dated in a history nobody can quietly rewrite.

Every file here was committed before the collection it governs, or is marked as a draft that
never became one. None was published until 2026-09-07, while `ROADMAP.md` said of its own
forward-looking entries that they were "published in advance for the same reason the
pre-registrations are." That reason did not apply to the pre-registrations, because they were
not published. They are now.

There are fifteen. Nine were collected: three on the 62-proposition questionnaire the study
retired on 2026-09-16, withdrawn with it, and one on the judge-scored design, whose contrast is
withdrawn. Four were never collected: two superseded by the instrument change, one superseded
the same day by its own v2, and one a draft. The table names the run directory, or the reason
there is none, and the document that reports each. Amendments are recorded in the file they
amend, dated, with the original text left standing.

## What a pre-registration commits this study to

Each one fixes, before collection: the question, the outcomes and what each would mean, the
design, the analysis steps **in order**, and what would make the result uninteresting. The last
of those matters most — a plan that cannot describe its own boring outcome is a plan that will
find something.

The 2026-09-07 ablation plan went further, and its stopping rule was **enforced in code**:
`scripts/ablation_analysis.py` withholds steps 2–5 if step 1's ablator-agreement check fails,
and requires `--force` to print them as diagnostics. The arm it gated is withdrawn with the
retired questionnaire; the mechanism is kept as the model for the plans after it.

| plan | status | collection | result |
|---|---|---|---|
| `PREREG-2026-08-28-refusal-direction.md` | collected; the stance null it supported is withdrawn (`CORRECTIONS.md` #28) | `runs/refusal-ablation/`, `runs/mask-gradient/` (study tree; not in this release). Also binds the dose series | [`RESULTS-2026-08-28-refusal-ablation.md`](../results/RESULTS-2026-08-28-refusal-ablation.md), [`RESULTS-2026-08-28-stance-survives-ablation.md`](../results/RESULTS-2026-08-28-stance-survives-ablation.md) (superseded), [`RESULTS-2026-09-18-dose-series-preflight.md`](../results/RESULTS-2026-09-18-dose-series-preflight.md) |
| `PREREG-2026-08-29-mask-surface.md` | superseded the same day by v2; never collected | none | — |
| `PREREG-2026-08-29-mask-surface-v2.md` | collected on the retired questionnaire; withdrawn with it | deleted 2026-09-22 with the questionnaire's licensed text | [`RESULTS-2026-08-29-evidence-concordance.md`](../results/RESULTS-2026-08-29-evidence-concordance.md) (working notes) |
| `PREREG-2026-08-31-clause-factorial.md` | collected 2026-09-19 on the 32-item battery; amended before collection and after | the `F000`–`F111` cells of `runs/2026-09-16-ratchet-v3-wave/` | the file's own Amendment 2 and its correction; `scripts/refusal_table.py --factorial` |
| `PREREG-2026-09-07-ablation-vs-prompt.md` | collected on the retired questionnaire; withdrawn with it; the arm is spent, not complete | deleted 2026-09-22 with the questionnaire's licensed text | [`withdrawn/results/RESULTS-2026-09-07-ablation-wave.md`](../withdrawn/results/RESULTS-2026-09-07-ablation-wave.md) |
| `PREREG-2026-09-12-instrument-choice.md` | superseded; never collected. The second instrument it planned became the study's only instrument when the questionnaire was retired | none | — |
| `PREREG-2026-09-12-same-items-both-paths.md` | never collected; written against the retired questionnaire and not runnable as written | none | — |
| `PREREG-2026-09-13-frame-and-placebo.md` | collected as I3 Phase 0 on the judge-scored design; its B−A contrast is withdrawn | `data/2026-09-13-i3-phase0/` (3,200 records, status `withdrawn`) | [`withdrawn/results/RESULTS-2026-09-14-I3-phase0.md`](../withdrawn/results/RESULTS-2026-09-14-I3-phase0.md) |
| `PREREG-2026-09-13-pipeline-rung.md` | collected through the G0DM0D3 proxy; its obfuscation predictions were untestable (`CORRECTIONS.md` #16); the proxy design was abandoned | `data/2026-09-13-g0dm0d3-replicate/`, `data/2026-09-13-g0dm0d3-replicate-baseline/` | [`RESULTS-2026-09-14-rung2-transform-audit.md`](../RESULTS-2026-09-14-rung2-transform-audit.md), [`RESULTS-2026-09-15-rung2-decomposed.md`](../RESULTS-2026-09-15-rung2-decomposed.md) |
| `PREREG-2026-09-14-i3-phase4.md` | collected; Amendment 2 replaced the unsigned i3 bank with `data/ratchet-battery.json` before any battery call | `runs/2026-09-16-ratchet-v3-wave/`, `runs/2026-09-16-ratchet-v3-wave-budget-probe/` | the paper, §1–§3 and §7; [`ITEM-READ-2026-09-16-ratchet-battery.md`](../ITEM-READ-2026-09-16-ratchet-battery.md) |
| `PREREG-2026-09-18-omission-orders.md` | collected; Amendment 1 re-collected eight hosted models with pinned backends | `runs/2026-09-18-omission-orders/`, `runs/2026-09-18-omission-hosted/`, `runs/2026-09-20-omission-hosted-pinned/`, `runs/2026-09-21-omission-nemotron-phala/` | [`RESULTS-2026-09-18-omission-orders.md`](../results/RESULTS-2026-09-18-omission-orders.md), [`RESULTS-2026-09-21-omission-pinned.md`](../results/RESULTS-2026-09-21-omission-pinned.md); the paper, §6b |
| `PREREG-2026-09-18-paraphrase.md` | collected | `runs/2026-09-18-paraphrase/` | [`RESULTS-2026-09-21-paraphrase.md`](../results/RESULTS-2026-09-21-paraphrase.md); the paper, §5 |
| `PREREG-2026-09-20-rung2-control-v2.md` | collected; the rung-2 position claims stay withdrawn | `runs/2026-09-20-rung2-control-v2/` against `runs/2026-09-19-rung2-elicitation/` | [`RESULTS-2026-09-21-rung2-control-v2.md`](../results/RESULTS-2026-09-21-rung2-control-v2.md) |
| `PREREG-2026-09-24-partials-renumbered.md` | collected; no floor moves | `runs/2026-09-24-partials-renumbered/` | the paper, §6b; `data/partials-sensitivity.json` (`scripts/partials_sensitivity.py`) |
| `PREREG-DRAFT-factions.md` | draft, undated by design; never collected; continuing work | none | — |

## Reading them against what happened

A plan is only useful if the deviations from it are visible. Where a result departs from its
plan, the departure is stated in the result document rather than in the plan — plans are not
edited after collection, which is the only property that makes them worth anything.

Claims withdrawn from this study, pre-registered or not, are in
[`CORRECTIONS.md`](../CORRECTIONS.md).
