# Pre-registrations

Analysis plans written **before** the data they analyse was collected.

## Why these are here

A pre-registration that lives only in the author's working tree is a private note. Its entire
function is that a reader can check the plan was fixed before the numbers were seen, and that
requires the plan to be public and dated in a history nobody can quietly rewrite.

These five were written before their collections and were **not published until 2026-09-07** —
while `ROADMAP.md` said, of its own forward-looking entries, that they were "published in
advance for the same reason the pre-registrations are." That reason did not apply to the
pre-registrations, because they were not published. They are now.

## What a pre-registration commits this study to

Each one fixes, before collection: the question, the outcomes and what each would mean, the
design, the analysis steps **in order**, and what would make the result uninteresting. The last
of those matters most — a plan that cannot describe its own boring outcome is a plan that will
find something.

The 2026-09-07 ablation plan goes further and its stopping rule is **enforced in code**:
`scripts/ablation_analysis.py` withholds steps 2–5 if step 1's ablator-agreement check fails,
and requires `--force` to print them as diagnostics. Running the steps in a different order, or
reporting a later step while an earlier one fails, is precisely the researcher degree of freedom
a pre-registration exists to remove — so it is removed mechanically rather than by intention.

| plan | collection | result |
|---|---|---|
| `PREREG-2026-08-28-refusal-direction.md` | refusal-direction arm | — |
| `PREREG-2026-08-29-mask-surface.md` | mask-surface arm | — |
| `PREREG-2026-08-29-mask-surface-v2.md` | mask-surface, revised design | — |
| `PREREG-2026-08-31-clause-factorial.md` | clause factorial | — |
| `PREREG-2026-09-07-ablation-vs-prompt.md` | `runs/2026-09-07-ablation-wave/` | [`results/RESULTS-2026-09-07-ablation-wave.md`](../results/RESULTS-2026-09-07-ablation-wave.md) |
| `PREREG-2026-09-12-instrument-choice.md` | **not yet collected** — item set not frozen | — |
| `PREREG-2026-09-12-same-items-both-paths.md` | **UNSIGNED, not collected** — needs Ian's signature before any run | — |

The last one is written earlier in its own lifecycle than the others: before the instrument it
describes exists. That is deliberate. Four of the five plans above this study published were
written before their collections but **after** the instrument was chosen, so the one degree of
freedom they could not remove was the one that matters most here — which ruler to use. This plan
fixes the primary outcome, the floors gate and the boring outcome while the item set is still
unwritten, and the collection does not begin until the items and the scoring function are
committed.

## Reading them against what happened

A plan is only useful if the deviations from it are visible. Where a result departs from its
plan, the departure is stated in the result document rather than in the plan — plans are not
edited after collection, which is the only property that makes them worth anything.

Claims withdrawn from this study, pre-registered or not, are in
[`CORRECTIONS.md`](../CORRECTIONS.md).
