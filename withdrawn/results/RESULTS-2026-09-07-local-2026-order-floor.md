# The hosted/local order gap is vintage, not quantisation and not the serving stack

**Collected** 2026-09-07, local GPU, 15 runs, no API spend. **Reproduce:**
`python scripts/order_floor_wave.py --report --models "hf.co/lmstudio-community/Qwen3.8-27B-GGUF:Q4_K_M" --out-suffix local2026`
then `python scripts/floor_table.py --markdown`.

## The question this closes

§3's most quotable split says item order moves **p90 3** on hosted 2025–26 models and **p90 14**
on local 2024-generation builds, and reads that as a generational effect — Röttger et al.
conjectured in 2024 that better-aligned newer models would be more stable, and nobody had
measured it.

**This corpus could not support that reading**, because three properties changed together
across the split:

| | hosted side | local side |
|---|---|---|
| serving path | someone else's API | local Ollama |
| vintage | 2025–26 | 2024 |
| quantisation | provider precision | Q4_K_M |

The requantisation floor is p90 6 — the same order of magnitude as the gap being explained — so
"it is the quantisation" was an equally good story. The frozen panel could not break the tie:
its only local 2026 build is `gemma-4-12B`, which returns empty responses.

So a 2026-generation open weight was collected **locally, at Q4**, under the same condition D,
the same two shuffled orders plus canonical, the same five swept seeds, the same temperature.

## The result

| row | pairs | side med / p90 / max |
|---|---:|---|
| presentation order, one sitting, **frontier API** (2025–26) | 75 | 1 / **3** / 20 |
| presentation order, one sitting, **local 2026 open-weight** | 3 | 3 / **3** / 3 |
| presentation order, one sitting, **local 2024 open-weight** | 10 | 10 / **14** / 21 |

**A 2026 open weight run locally at Q4 behaves like the hosted 2026 models, not like the local
2024 ones.** Serving path and quantisation are held fixed against the 2024 local row — both
sides are Ollama at Q4 — and the gap disappears anyway.

The per-pair detail, because three pairs deserve to be shown rather than summarised:

| pair | side-flips | endpoint |
|---|---:|---:|
| canonical vs shuffle 101 | 3 | 1 |
| canonical vs shuffle 202 | 3 | 2 |
| shuffle 101 vs shuffle 202 | 2 | 3 |

And the comparison that matters most: **this model's own run-to-run spread at a fixed order is
median 1–2, max 4.** The order effect of 2–3 is inside the noise of rerunning the identical
prompt. Reordering the questionnaire does nothing measurable to this model — it sits exactly at
the modal's own sampling error of p90 3, which is where the hosted 2026 models sit too.

## What this does and does not establish

**Refuted: quantisation explains the gap.** Both the 2024 local row and this row are Q4
builds served by the same local Ollama. If Q4 were the mechanism, this row would read near 14.

**Refuted: the serving stack explains the gap.** Same reasoning. Nothing about this measurement
went through anyone's API.

**Supported: vintage explains the gap.** Which is Röttger's 2024 conjecture, measured — and it
is worth being precise about what that means. The claim is not that newer models are better. It
is that a 2024-vintage 7–14B open model's answers to a forced-choice political battery move a
median of 10 items of 62 when you shuffle the questions, and a 2026-vintage one moves 2–3. A
literature built on the former is measuring an instrument artifact that the latter does not have.

**Still confounded: SIZE.** The 2024 local builds are 7–14B and this is a 27B. Vintage and
parameter count move together here, so "newer" and "bigger" are not separated. The clean
follow-up is a 2026-generation build at 7–14B — `gemma-4-12B` is the obvious candidate and it
returns empty responses on this instrument, which is why it could not serve as the tie-breaker
in the first place.

**One model, three pairs.** p90 equals max by nearest-rank below ten pairs, so the row's `†`
marker applies. Three pairs can refute "quantisation explains it" — and do, because a single
counter-example is enough to break a universal mechanism — but they cannot establish the size
of the vintage effect. What they establish is that the effect survives holding serving path and
quantisation fixed.

## Why this is a separate row and not merged

`presentation order, one sitting` is a panel row from a specific sitting. This arm is a
different sitting and an off-panel roster, collected to answer a different question, so folding
it in would change a published number with data gathered for another purpose. Its run directory
carries a `-local2026` suffix, and the panel arm's glob (`runs/*-wave-orders/*.jsonl`) cannot
match it — the separation is structural rather than a matter of remembering.

## Two defects this collection surfaced

**The class split was testing the wrong thing.** `("/" in model)` marked a model as hosted, and
a local Ollama build pulled from Hugging Face is tagged
`hf.co/lmstudio-community/Qwen3.8-27B-GGUF:Q4_K_M` — two slashes, never left the machine. This
collection would have landed on the *hosted* side of the split and answered its own question
backwards. No published number was affected, because the only `hf.co/` builds already in the
corpus have cells too thin to enter a class-split row. `served_over_api()` reads each run's own
`channel` field now, and the floors table is byte-identical before and after.

**The collector reported success over an empty cell.** The canonical-order cell was queued and
the collector built `["--shuffle-seed", str(shuffle)]`, sending the four characters `None` to a
parameter declared `type=int`. `run_battery` wrote nothing, the collector printed
"(no result line)" for that cell, and then printed **"collected 3 cell(s); 0 remain"** and
exited 0 — leaving two shuffled orders with nothing to pair against, which measures
shuffle-against-shuffle rather than order-against-canonical. That is the same failure
`ablation_wave.py` shipped the same morning, in a second collector, hours after the first was
fixed. Both now re-scan by distinct seed after a run, name every short cell, and return 1.
