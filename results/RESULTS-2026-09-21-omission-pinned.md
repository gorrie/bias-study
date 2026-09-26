# The hosted numbering artifact, with the backends pinned

**2026-09-21.** `runs/2026-09-20-omission-hosted-pinned`, 382 sheets attempted, 8 models, 12
presentation orders, conditions N and P, two numbering arms. Pre-registered in
`PREREG-2026-09-18-omission-orders.md`; the re-collection and its per-model backend pins are
Amendment 1 of that file. Every figure below is `scripts/omission_arms.py`.

## What pinning the backends did

This arm existed to remove a collection defect. `collection_check` blocked the 2026-09-18
hosted arm because 16 of its 36 model-by-condition cells had their replicates served by more
than one provider — worst `qwen3.8-2.4t-a95b` across seven. Serving path is a same-version
variant in this study, so those cells confounded the numbering contrast with the routing.
Eight models were re-collected, each pinned to one backend.

| arm | as-is partial | renumbered partial | Fisher exact, one-sided |
|---|---|---|---|
| 2026-09-18, backends mixed | 9 of 427 — 2.1% | 1 of 422 — 0.2% | p = 0.011 |
| 2026-09-20, backends pinned | 9 of 190 — 4.7% | **0 of 192 — 0.0%** | **p = 0.0017** |

Sheets lost to transport, budget exhaustion or refusal are excluded from both rows; these are
sheets the model answered and answered incompletely.

**Pinning sharpened an effect that was already there; it did not create one.** Removing the
routing variance roughly doubles the measured as-is rate — 2.1% to 4.7% — and takes the
renumbered arm to exactly zero across 192 sheets. The direction is the one the pre-registration
named, in both collections.

## Per model

| model | pin | as-is | renumbered |
|---|---|---|---|
| `deepseek/deepseek-v3.2` | Baidu | 0 / 24 | 0 / 24 |
| `ibm-granite/granite-4.2-8b` | DeepInfra | 1 / 24 | 0 / 24 |
| `meta-llama/llama-3.3-70b-instruct` | AkashML | 0 / 24 | 0 / 24 |
| `minimax/minimax-m2.7` | Minimax | 0 / 24 | 0 / 24 |
| `moonshotai/kimi-k2-thinking` | Novita | 1 / 24 | 0 / 24 |
| `nvidia/nemotron-3.5-lightning` | DeepInfra | **7 / 23** | 0 / 24 |
| `qwen/qwen3.8-2.4t-a95b` | SiliconFlow | 0 / 24 | 0 / 24 |
| `xiaomi/mimo-v2.5-pro` | Xiaomi | 0 / 23 | 0 / 24 |

**Read the concentration honestly: 7 of the 9 as-is losses are one model.** The arm is not
eight models agreeing. It is one model with a strong effect, two with a single sheet each, and
five with nothing — against a renumbered arm that is clean across all eight. The direction is
consistent and the zero is striking, but a reader entitled to ask whether this is a property of
hosted models generally should be told it currently rests on `nemotron-3.5-lightning`.

**These counts and both p-values are computed by `omission_arms.py`, not typed,** with the
same sheet classifier every other omission result uses.

## What the three-way test can and cannot separate

`item_omission.py --matrix` reports **NOT SEPARABLE** for all three affected models: no item
reached three sheets at two different slots, and no slot ate two different items. With one
partial sheet each for granite and kimi there is nothing to separate, and nemotron's seven
sheets lose 12 cells spread across 11 distinct items — one item twice, ten items once each.

So this arm does **not** re-establish item-versus-slot-versus-numeral on its own. What it
establishes is narrower and is the thing the pre-registration asked: the *arms differ*, and
they differ in the direction the numbering hypothesis predicts. The mechanism finding stays
where it was settled — the 2026-09-18 local arm, 240 sheets, 12 orders, which had the depth to
separate them.

## SETTLED, same day: the serving path is a moderator, and renumbering still works

The caution below asked for `nemotron-3.5-lightning` on Phala. It was collected into
`runs/2026-09-21-omission-nemotron-phala` — 48 sheets, 12 orders, conditions N and P, same
protocol, same pre-registration, the model pinned to Phala with fallbacks off.
**The answer is both, and the split matters.**

| nemotron-3.5-lightning, as-is arm | partial | rate |
|---|---:|---:|
| pinned to **DeepInfra** | **7 / 23** | 30% |
| pinned to **Phala** | **1 / 23** | 4.3% |

**Fisher exact, one-sided: p = 0.0235.** Same model, same twelve presentation orders, same
conditions, same numbering. The only thing that differs is which backend served it, and the
loss rate moves sevenfold.

**What does NOT move is the remedy.** The renumbered arm is **0 partial sheets in 216**, across
both backends and all eight pinned models. Pooled over the whole pinned collection with Phala
included: as-is **10 of 213** against renumbered **0 of 216**, p = 8.2 × 10⁻⁴.

So the two readings are not rivals:

- **Renumbering is protective everywhere it has been measured.** Nothing has yet produced a
  partial sheet under `1..32` numbering.
- **The as-is loss rate is a property of the serving path as much as of the model.** A study
  that does not pin its backend cannot reproduce its own non-response rate, let alone anyone
  else's — which is the same class of finding as everything else in this paper, in a place
  nobody looks.

The earlier framing of this document — that the hosted result "rests on `nemotron-3.5-lightning`"
— was right to hedge and wrong about what the hedge was for. It is not that one model carries
the arm. It is that one model on *one backend* carries it, and the backend is not reported by
anybody.

## The nemotron caution, carried from Amendment 1

`nemotron-3.5-lightning` is pinned to **DeepInfra**. On the 09-18 mixed data its as-is sheets
split three ways by backend, and so does the effect: **DeepInfra 4 partial of 9 sheets, Phala 0
of 9, CoreWeave 1 of 6**. The pin was
chosen by an availability rule — most sheets served — applied without consulting outcomes, and
on this model that rule selected the backend where the effect lives. On `xiaomi` the same rule
selected the backend with none. Opposite directions is what an outcome-blind rule produces, and
it is why the per-backend split is published in the amendment rather than summarised.

But the consequence for this result has to be stated plainly: **7 of the 9 as-is losses come
from a model pinned to the backend that showed the highest omission rate for it.** A reader may
reasonably want the same arm run against Phala. That is ~48 sheets and it is the obvious next
collection if this finding is to carry weight on its own.

## What would overturn this

- The same arm on nemotron/Phala showing the as-is losses vanish. That would make the effect a
  property of a serving path rather than of the numbering, and would be a more interesting
  finding than the one reported here.
- Any renumbered partial appearing at depth. The current zero is 192 sheets, which bounds the
  renumbered rate below roughly 1.9% at 95%, not at nothing.

## Commands

    python scripts/omission_arms.py --run 2026-09-20-omission-hosted-pinned   # the table above
    python scripts/omission_arms.py --run 2026-09-21-omission-nemotron-phala  # the Phala arm
    python scripts/omission_arms.py --run 2026-09-18-omission-hosted          # the mixed row
    python scripts/omission_arms.py --selftest                                # the exact test
    python scripts/collection_check.py 2026-09-20-omission-hosted-pinned
    python scripts/item_omission.py --run 2026-09-20-omission-hosted-pinned --matrix
    python scripts/item_omission.py --run 2026-09-18-omission-orders --matrix   # the local arm
