# The weight rung, measured at n=5: direction holds still, intensity belongs to the ablator

**Collected** 2026-09-07, local GPU, no API spend. **Pre-registered** in
`PREREG-2026-09-07-ablation-vs-prompt.md` before collection; analysed in the order that
document specifies, with its stopping rule enforced in code.

**Protocol.** Six base models × stock and every abliteration on disk × conditions A, P, D ×
n=5 at temperature 0.7 with a swept seed.

> **Coverage corrected 2026-09-12.** This read "45 cells planned, **28 reached n=5**", written
> while the wave was still collecting. The arm is now SPENT rather than complete: `ablation_wave.py
> --report` counts **63 cells, 39 at n=5, 0 left to collect, and 24 that had their five runs and
> came back short** — `gemma4-12b` stock returns 0 valid of 5 under condition A. Spent and complete
> are different states and only one of them is a reason to stop.

Reproduce with
`python scripts/ablation_analysis.py`.

## Why this collection existed

The weight rung is the strongest intervention this study can apply, and until today it rested
on **one run per arm**. That is how a 12-item "inversion" reached the paper, `power.py` and the
README off a sample that cannot support the word — withdrawn as
[CORRECTIONS](https://github.com/gorrie/bias-study/blob/main/CORRECTIONS.md) #8 the same
morning this ran.

## What the collection actually yielded

Three of six bases produced a usable pair. **The three failures are results, not gaps**, and
each has a named cause:

| base | outcome | cause |
|---|---|---|
| `qwen38-27b` | usable, **3 ablations** | the only base that can answer step 1 |
| `phi4-14b` | usable, 1 ablation | — |
| `qwen25-14b` | usable, 1 ablation | the pair whose n=1 "inversion" was withdrawn |
| `gemma2-9b` | **ablated arm unusable** | build emits SentencePiece word-boundary markers (`▁▁`, `[UNK_BYTE_0xe29681…]`) as literal text — it answers, the text is unreadable |
| `llama31-8b` | **ablated arm unusable** | build answers in prose and never emits an answer sheet; instruction-following is gone |
| `gemma4-12b` | **both arms unusable** | empty responses from the *stock* build too, so this is the build family, not the ablation |

That last row is the one to read twice. A failure present in the stock arm is not evidence
about abliteration, and an arm that reported only the ablated failure would have implied it was.

## Step 1 — ablator agreement, the pre-registered gate

Two abliterations of the same base, same condition, modal against modal. Only `qwen38-27b` has
more than one.

| base | condition | ablation A | ablation B | side | endpoint |
|---|---|---|---|---:|---:|
| qwen38-27b | D | OBLITERATUS | huihui-uddw | 3 | **19** |
| qwen38-27b | D | 0bserverx Heretic | huihui-uddw | 2 | 9 |
| qwen38-27b | D | OBLITERATUS | 0bserverx Heretic | 1 | 10 |
| qwen38-27b | P | OBLITERATUS | 0bserverx Heretic | 2 | 7 |
| qwen38-27b | P | 0bserverx Heretic | huihui-uddw | 2 | 2 |
| qwen38-27b | P | OBLITERATUS | huihui-uddw | 0 | 9 |
| qwen38-27b | A | OBLITERATUS | 0bserverx Heretic | 1 | 3 |

## SETTLED, later the same day: the effect was the ablator

The first pass of this arm ended on "the one base where abliteration measurably moves political
position is the one base where we cannot check whether it is the ablation or the ablator."
`qwen2.5-14b` had exactly one abliteration on disk, so step 1 could not run on it.

**So two more independent abliterations of that base were collected**, both quant-matched
Q4_K_M to the stock arm, at n=5 with a swept seed:

| ablator | abliteration author | stock → ablated, A / D / P | vs estimator floor 3 |
|---|---|---:|---|
| `huihui_ai/qwen2.5-abliterate:14b` | huihui-ai (v1) | **8 / 9 / 9** | clears |
| `Qwen2.5-14B-Instruct-abliterated-v2` | huihui-ai (v2, later separate job) | **8 / 9 / 9** | clears |
| `Josiefied-Qwen2.5-14B-Instruct-abliterated-v2` | Goekdeniz-Guelmez (**different author**) | **0 / 2 / 0** | at or under |

And the agreement between them:

| pair | side-flips, A / D / P |
|---|---:|
| huihui v1 vs huihui v2 | **0 / 0 / 0** |
| huihui v1 vs Josiefied | **8 / 9 / 9** |
| huihui v2 vs Josiefied | **8 / 9 / 9** |

**Two builds by the same author agree exactly. The build by a different author disagrees by
precisely the size of the "effect" — and shows no effect at all.**

So the ablator spread (median 8, max 9) equals the ablation effect (median 8, max 9), and the
pre-registered stopping rule fires on the direction statistic, on the one base that appeared to
show something:

> **Abliteration does not measurably move political stance on any of the three usable bases.**

**[CORRECTION 2026-09-12 — CLAIM-ABLATION-CAUSAL-001. The sentence above is narrower than it
reads, and one third of it is not supported at all. Rig: `scripts/ablation_equivalence.py`.]**

An absence claim is defensible only as a **bound**: *effects larger than X are excluded at this
n*. Reached instead by failing to find a difference, it is indistinguishable from having no
power. So the bound was computed, and it does not exist:

| base | stock → ablated (A/D/P) | 95% CI | TOST vs ±5 flips |
|---|---|---|---|
| `qwen38-27b` | 1, 2, 2 | [1.0, 2.0] | equivalent to zero within ±5 |
| `phi4-14b` | 2, 3, 3 | [2.0, 3.0] | equivalent to zero within ±5 |
| `qwen25-14b` | 8, 9, 9 | [8.0, 9.0] | **NOT equivalent to zero** |

*(An earlier cut of this correction, committed hours before this one, used 0/0/0 for the two low
bases and reported their intervals as degenerate and "not testable". That was wrong — the run
measured 1–2 and 2–3, small and at or under the modal estimator floor of 3, but not zero. The
wrong inputs produced a stronger-sounding conclusion than the data warrants, which is the
failure this whole backlog item is about, so it is corrected here rather than quietly amended.)*

**What is actually supported:**

1. *`qwen38-27b` and `phi4-14b` are equivalent to zero within a ±5 margin* — a real bound, and a
   better result than the original sentence claimed, because it is quantified. It is **not** a
   demonstration of zero effect: both move a little, and the margin is set by the replicate
   floor rather than by anything substantive.
2. *`qwen25-14b`'s 8/9/9 fails equivalence* and is **build-specific**. The ablator-spread control
   is genuinely strong: two builds by one author agree at 0/0/0 while a third author's build
   moves 0/2/0 — the spread equals the apparent effect.
3. **Build-specific is not absent.** The comparison is between three third-party artifacts whose
   layer choice, refusal set, intervention strength and quantisation are undocumented and
   differ. The design cannot separate *"ablation does nothing"* from *"these particular ablators
   disagree"* — and the second is what was observed.

**The mechanism claim is withdrawn, the observation is kept.** Do not cite this run as evidence
that abliteration has no effect on stance. Cite it as evidence that a published ablation effect
was attributable to one ablator's undocumented choices, which is a narrower and better-evidenced
result, and is the one the agreement step was designed to produce.

A causal follow-up needs what this design lacked: a pinned base, an edit we perform ourselves at
a controlled strength, matched serving and quantisation, sham edits, refusal and competence
controls, and inference specified in advance. That is the next release's "doing the abliteration
ourselves" item, and this correction is the argument for it.

> The one apparent effect is attributable to a single ablator's choices — an independent
> abliteration of the same base, by a different author, at the same quantisation, moves nothing.

That is outcome 4 as pre-registered, and it is a cleaner demonstration than the design hoped
for: same-author builds agreeing at zero while a cross-author build accounts for the entire
apparent effect is exactly the confound the agreement step was written to detect.

**It also reverses a qualification entered against Book 3 earlier today.** `quiet-autocomplete`
ch18's published prose says stripping the refusal direction "moves the institutional-skepticism
*stance* by a tenth of a point or less… The lean is not in the layer you can strip." The first
pass here read as a counter-example to that; it was not. The counter-example was one ablator.
The dissociation claim is **better supported after this collection than before it**, and the
source note in that chapter has been corrected to say so.

## The result as first reported, in the pre-registration's own terms

**On direction (side-flips), nothing on the checkable base is measurable in either direction.**

| base | ablator spread (med / max) | its own ablation effect (med / max) | reading |
|---|---:|---:|---|
| `qwen38-27b` | 2 / 3 | 2 / 2 | spread ≥ effect, and **neither clears the estimator floor of 3** |
| `qwen25-14b` | — | 9 / 9 | **clears the floor decisively** — and cannot be checked |
| `phi4-14b` | — | 2 / 3 | at or under the floor |

**The one base where abliteration measurably moves political position is the one base where we
cannot check whether it is the ablation or the ablator.** `qwen25-14b` moves 8 items under A, 9
under D, 9 under P, against a side-flip estimator floor of 3 — a real effect by this study's own
rule. It has exactly one abliteration on disk, so step 1 cannot run on it, and its effect is
unqualified by ablator variation. Meanwhile the base that *can* be checked shows 2–3 either
way, which is the estimator.

**On intensity (endpoints), the pre-registered outcome 4 arrives.** Ablator disagreement reaches
**19** endpoint-flips on `qwen38-27b` under D, against an endpoint estimator floor of **8** —
and that base's own stock-vs-ablated endpoint effect reaches **17**. Both clear the floor, and
the disagreement is the *larger of the two*. So "abliteration changes how strongly the model
commits" is not separable from "this particular ablator's choices change it". Which abliteration
you happen to download moves intensity about as much as abliterating at all does.

Direction is stable across ablators and intensity is not. Reporting only the headline statistic
would have hidden the strongest signal in the collection, which is why the pre-registration
required both.

## Step 4 — weight against prompt, same base, same units

Weight-level (stock → ablated, condition held) against prompt-level (P → D, build held):

| base | ablation | condition | weight | prompt |
|---|---|---|---:|---:|
| qwen25-14b | huihui qwen2.5-abliterate | D | **9** | 4 |
| qwen25-14b | huihui qwen2.5-abliterate | P | **9** | 4 |
| phi4-14b | huihui phi4-abliterated | D | 3 | 1 |
| phi4-14b | huihui phi4-abliterated | P | 2 | 1 |
| qwen38-27b | all three ablations | D / P | 1–2 | 0 |

The weight-level effect is larger than the prompt-level effect in **every row**. On two of three
bases both numbers are at or under the estimator floor, so that ordering is not a finding there.
On `qwen25-14b`, where the weight effect clears the floor and the prompt effect (4) sits just
above it, the ordering is real: **cutting the refusal direction out of the weights moved this
model's answers more than telling it what to think did.**

That is the comparison this arm was built to make, and it is available on exactly one model.

## The withdrawn claim, re-measured

CORRECTIONS #8 withdrew "qwen2.5-14B moves 12 items under ablation against a detection limit of
9" because the 12 came from n=1 per arm.

At n=5 with a swept seed, the same pair moves **8 / 9 / 9** items under A / D / P. So:

- **The magnitude was overstated.** 12 is not reproducible; 8–9 is what a five-run modal shows.
- **The direction of the claim survives.** 9 against a side-flip floor of 3 clears it, so
  ablation does move stance on this base, and the null "ablation does not move stance" is
  refuted *for this base*.
- **The framing "one null inverted outright" stays withdrawn.** A single base, with a single
  abliteration whose contribution cannot be separated from the ablator's choices, is not an
  inversion of a general null. It is one measured effect on one model.

## What it does to the published ablation floor

Both rows print in the floors table, because they have different scopes and choosing between
them after seeing both is the move this study has withdrawn three claims for:

| row | pairs | side med / p90 / max | endpoint med / p90 / max |
|---|---:|---|---|
| `refusal-direction ablation` (2026-08-30, cells of 1–2 runs) | 12 | **6** / 9 / 12 | **6** / 14 / 16 |
| `refusal-direction ablation, one sitting` (n=5, swept seed) | 20 | **2** / 9 / 9 | **2** / 7 / 17 |

**The median falls from 6 to 2 on both statistics.** A five-run modal averages away the
run-to-run noise a single sheet carries, so two-thirds of the older arm's typical "ablation
effect" was the estimator rather than the ablation. The p90 barely moves (9 → 8), which says
the tail — the `qwen25-14b`-shaped cases — is real while the typical case was not.

This is the same mechanism that took the manipulation floor from a pooled p90 of 15 to 7 under
the wave protocol, arriving in a second arm: **wherever this study measured an effect from
single runs, the effect was inflated by the noise it could not average away.** Two of three
arms measured that way have now been re-collected and both shrank.

## Step 2 — willingness, and one observation worth naming

Refusal rate on condition A, from the classifier the refusal table uses:

| base | arm | n | refused | valid | other |
|---|---|---:|---:|---:|---:|
| gemma4-12b | ablated-culturerevolt | 5 | **5** | 0 | 0 |
| gemma4-12b | ablated-OBLITERATUS | 5 | 2 | 0 | 3 |
| gemma4-12b | stock | 5 | 0 | 0 | 5 |
| gemma2-9b | ablated | 5 | 0 | 0 | 5 |
| llama31-8b | ablated | 5 | 0 | 0 | 5 |
| the three usable bases | stock and every ablation | 5 | **0** | 3–5 | 0–2 |

**An abliterated build refused the balance instruction 5 times out of 5.** Abliteration is
performed specifically to remove the refusal direction, so a Gemma-4 abliteration that declines
every run is at least a curiosity. It is reported as an observation and not a finding: that
base's stock arm returns empty responses, so there is no baseline to compare against, and the
whole `gemma4-12b` family is unusable here for reasons that have nothing to do with politics.

## Caveats, stated

- **Three usable bases.** Every number above is one of three models, and the checkable one is
  one of one.
- **Quantisation mismatch is declared, not discovered.** `huihui-qwen38-27b-abliterated-uddw`
  ships UD-DW-Q4_K_M (Unsloth dynamic) against the stock arm's static Q4_K_M; that repo has no
  plain Q4_K_M at all. Any difference it shows is attributable to the quantisation before it is
  attributable to the ablation, and it is named here so that ordering cannot be reversed later.
- **Every ablated build is third-party.** Layer choice, refusal set, intervention strength and
  quantisation differ between them and none documents those choices completely. Computing the
  refusal direction ourselves ([Arditi et al. 2024](https://arxiv.org/abs/2406.11717)) is what
  removes this confound at the root, and it needs ~54GB to capture activations at bf16.
- **Condition B is not collected in this arm**, so the refusal comparison here is A against
  P and D only.
- **n=5 is enough to beat n=1 and not enough for a bimodal build.** Several cells in the wider
  corpus have a median run-to-run spread of 1–2 and a maximum above 20; nothing here rules that
  out for these builds.

## Reproduce

```bash
python scripts/ablation_wave.py --report          # coverage, and which cells came back short
python scripts/ablation_analysis.py               # steps 1-5, stopping rule enforced
python scripts/ablation_analysis.py --force       # steps 2-5 even if step 1 stops the analysis
python scripts/floor_resolution.py --write        # the estimator floor these are judged against
```
