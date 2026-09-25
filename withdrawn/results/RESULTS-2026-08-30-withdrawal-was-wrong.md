# The 2026-08-28 withdrawal was wrong. Evidence 1 is reinstated.

Found 2026-08-30 by reading `ADVERSARIAL-REVIEW.md` — a document cited repeatedly in this
project's recent work, including by me, without ever being opened.

## What was withdrawn, and why

`RESULTS-2026-08-28-stance-survives-ablation.md` withdrew Evidence 1, the claim that
abliteration demonstrably rewrote the political responses. Its reasoning:

> *The May abliteration run sampled at temperature 0.7… two runs of the same model on the
> same prompts at that temperature produce mean word-set Jaccard 0.340 (range 0.303–0.392,
> n=10). The between-arm figure of 0.276–0.339 sits inside that band.*

The logic is sound. The baseline is wrong.

## The control it asked for already existed

`ADVERSARIAL-REVIEW.md` objection **A2b** is, word for word, the objection the August
correction raised — *"Temp=0.7 inflates that text-difference; some of the 0.30 Jaccard is
sampling noise, not ablation."* It is marked **DONE**, in May, with a greedy temperature-0
run committed to `runs/2026-05-27-abliteration-controls/`.

Recomputed from that data today, stock-greedy against abliterated-greedy:

| | value |
|---|---|
| mean word-set Jaccard | **0.306** |
| median | 0.305 |
| range | 0.261 – 0.351 |
| cells ≥ 0.97 (near-identical) | **0 of 20** |

**At temperature 0 with greedy decoding a model reproduces itself exactly** — the within-arm
floor is 1.0, not 0.340. Measured independently on 2026-08-30: seeded greedy runs on this
hardware are byte-identical, 0 of 62 items differing across five seeds.

So the correct comparison is 0.306 against a floor of ~1.0. The August correction compared
0.306 against 0.340 — **a within-model baseline measured at a temperature the control run did
not use.** It withdrew a claim on the strength of a baseline that does not apply to the data
defending it.

## What this reinstates

**Evidence 1 stands: abliteration substantially rewrites the political responses, and the
rewrite is not a sampling artifact.** ~70% of the wording changes, with zero near-identical
cells, under deterministic decoding.

And the dissociation stands with it, because both halves now hold and they hold from
independent measurements:

| half | May evidence | 2026-08-30 evidence |
|---|---|---|
| the text is rewritten | Jaccard 0.306 at temp 0, floor 1.0 | — |
| the stance does not move | Δ ≤ 0.2 on 1–5, CIs include zero | side-flips inside the quantisation null on 3 arm-matched pairs |

These agree. My own weight-rung work measured **stance** and found no movement beyond the
quantisation null; May measured **text** and found large movement. Different measures, same
conclusion: *ablating the refusal direction changes how an open model talks about a contested
institution and not where it lands.*

**The project's flagship claim is not overturned. It was never overturned. It was withdrawn on
a bad baseline and is now restored.**

## Two further things the same document settles

**Objection A4 — the dose-response I have been planning as new work was run in May.** A
stronger SVD ablation (8 refusal directions against 4) does not move the stance, and pushing
further degrades coherence before the stance relocates. The functionality ceiling arrives
first. `PLAN-2026-08-29-dose-response.md` should be rewritten as an extension of that, not as
a first attempt.

**Objection A3 is the one that indicts two days of my work.** Marked **OPEN** since May:

> *Open 7–9B instruct models sit at ~3.0 (balanced) already — floor/ceiling. There's nowhere
> to move… This is why the weight rung can't be the whole story and the prompt rung carries
> the lean finding.*

Every local model I ran on 2026-08-29/30 is in exactly that class. "Nothing moves on small
open models" is a **documented May limitation that I rediscovered as though it were news**,
and it is the reason the frontier tier was always the necessary next step rather than an
optional extension.

## How this happened

I cited `ADVERSARIAL-REVIEW.md` C3/E5 in a pre-registration, in a script docstring, and in
commit messages, having taken it secondhand from documents that quoted it. Fourteen documents
in this directory — roughly 2,000 lines — were never opened, including the one that contained
the control I spent a day concluding did not exist.

The correction-to-a-correction is the cheapest possible demonstration of the cost. Nothing was
published, so nothing external needs retracting.

## Consequence for the withdrawal count

`STATUS.md` records seven withdrawn claims. One of them — *"ablation moves stance on two of
three matched pairs"* — remains correctly withdrawn. But the August withdrawal of Evidence 1
is now itself withdrawn, so the project's position on the weight rung returns to what it was
in May, with better evidence than it had then.
