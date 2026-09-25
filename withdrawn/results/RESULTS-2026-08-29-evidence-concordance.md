# An axis-free outcome measure, and the control that cut it down

> **WORKING NOTES.** Not a finding and not for publication. `STATUS.md` is authoritative;
> where this file disagrees with it, this file is stale. Read any correction block above before
> quoting any number here.


> ## CORRECTION 2026-08-30 — TWO BELOW-CHANCE PERSONAS BECOMES ONE
>
> The bootstrap behind every interval on this page treated 100 answers as independent when
> they are **20 items measured 5 times**, 16 of them unanimous across runs. Effective n is
> about 20, so the intervals were roughly 40% too narrow. Found by
> `DESIGN-REVIEW-2026-08-29-fable.md` F8 and reproduced exactly after clustering on the item:
>
> | persona | published CI | clustered CI | verdict |
> |---|---|---|---|
> | `persona-charles` | [16, 33] | **[9, 42]** | still below chance |
> | `persona-viktor` | [25, 43] | **[15, 55]** | **no longer excludes chance** |
> | `persona-frank` | [43, 62] | [33, 72] | still indistinguishable |
>
> **"Two of fourteen personas drive concordance below chance" is withdrawn. It is one.**
> The point-estimate ordering is unchanged and the headline contrast survives, but the
> below-chance claim now rests on a single persona and should be reported that way.
>
> A first attempt at the fix clustered on the *run* instead, which is the opposite error —
> it keeps all 20 items in every replicate, so intervals collapse toward a point when runs
> agree (charles came out [20, 30], and [90, 90] where runs were identical). The item is the
> unit that generalises, so the item is the cluster. Both wrong versions are recorded in
> `scripts/evidence_concordance.py` so neither gets reintroduced.

Measured 2026-08-29 from the aipolcom.net dataset (`/api/experiments.php`, 930 runs). No new
model calls; this is reanalysis of published data with a measure its authors did not compute.
Model throughout: Claude Fable 5, the only model with both a baseline and the full persona set.

## Why look for a different outcome measure at all

`LITERATURE-2026-08-29-position-measurement.md` §3 is a stack of published objections that
every coordinate-based result has to survive: the construct may not exist (Peereboom), the
Political Compass is not a validated instrument (Faulborn), the *sign* of a finding is a
property of the instrument (Barmettler, cross-instrument ρ = −0.25, p = 0.55), randomise the
option order and the signal goes uniform (Dominguez-Olmedo, 43 models).

Those objections all attack **the axis**. So the question was whether there is a readout of the
same experiments that has no axis in it.

There is. Their §12 work classified all 62 propositions blind — 20 `evidence` (a
research-supported answer resting on near-universal premises), 20 `premise` (evidence direction,
contestable premises), 22 `none` — and recorded which answer the research supports. That allows:

> **evidence-concordance** — the fraction of `evidence` items a model answers in the
> research-supported direction.

No axis. No left, no right, no quadrant. Just: did it give the answer the research supports.

## What it showed first, which looked like a large finding

| condition | evidence-concordance |
|---|---:|
| baseline (original prompt, n=5 runs) | **95.0%** [95% CI 90.0, 99.0] |
| `persona-charles` | **24.0%** [95% CI 16.0, 33.0] |

CIs separated, n=100 scored answers each side. A persona instruction costs up to **71 points**
of agreement with documented evidence.

Stated that way it reads as a capability finding rather than a politics finding, which is what
made it attractive. Two checks were run before believing it. The first survived. The second did
not.

## Check 1 — is it just displacement wearing different clothes? Partly. r² = 0.68

If their §12 thesis holds (research-supported answers cluster in one region of their plane),
then moving a model away from that region must cost concordance mechanically, and the new
measure is the old one restated.

Pearson r(displacement, evidence-concordance) across 14 personas = **−0.825, r² = 0.68.**

So **two thirds of it is displacement restated.** That has to be said plainly.

The remaining third is not, and there are decisive pairs — near-identical displacement, very
different evidence behaviour:

| persona | displacement | evidence-concordance |
|---|---:|---:|
| `persona-fin-ch` | 7.06 | **98.3%** |
| `persona-boris` | 7.60 | **76.0%** |
| `persona-fin-ar` | 9.68 | **97.0%** |
| `persona-trent` | 11.57 | **82.0%** |

**Displacement magnitude does not tell you whether the model is still tracking evidence.** That
is the part of this worth keeping, and it is a limit on every coordinate-only result including
our own.

## Check 2 — the specificity control, which killed the clean version

If a persona selectively degrades factual accuracy, it should move `evidence` items more than
`none` items. Answer-change rate against the modal baseline answer, by item class, averaged over
all 14 personas:

| item class | answers changed |
|---|---:|
| `evidence` | 60.9% |
| `premise` | 68.8% |
| `none` | 61.2% |
| *baseline run-to-run noise* | *4–8%* |

**Essentially equal.** A persona rewrites about three answers in five regardless of whether the
item has a research-supported answer. There is no selective attack on factual accuracy. The
headline drop is substantially the mechanical consequence of wholesale answer change against a
95% baseline — a high baseline has further to fall.

The "71-point collapse in factual agreement" framing is therefore **withdrawn** as stated. It
was ten minutes old and it did not survive its own control.

## What did survive: the change is directed, not churn

Rate is uniform across classes. **Direction is not.** If a persona were merely randomising, the
agree/disagree binary would land near 50%. Bootstrap CIs, n=100 each:

| persona | evidence-concordance | 95% CI | vs chance |
|---|---:|---|---|
| `persona-charles` | 24.0% | [16.0, 33.0] | **below chance** |
| `persona-viktor` | 34.0% | [25.0, 43.0] | **below chance** |
| `persona-frank` | 53.0% | [43.0, 62.0] | indistinguishable |
| 9 others | 76.0–98.3% | — | above chance |

Two of fourteen personas push the model **below chance** on items their own blind adversarial
review found have a research-supported answer. Below chance is not noise — noise is 50%. Those
two are answering *against* the evidence systematically. Nine of fourteen leave the model
comfortably above chance while still displacing it several units.

So a persona is not a uniform reframing operator. Some are evidence-preserving and some are
evidence-inverting, and **the coordinate does not distinguish them.**

## Why this changes our design more than it changes theirs

Our outcome measures to date — the 1–5 stance rubric, and displacement in prereg v2 — share one
blind spot: neither can tell **"the model committed to a defensible position"** apart from
**"the model was pushed off the evidence."** Both register as movement.

That indicts our own headline. v1's finding was Gemma 2 going 3.00 → 5.00 on every question
under the unmask condition, read as the mask coming off. **We never tested whether it stayed on
the evidence**, and we had no placebo class to test against. Two readings remain open and our
instrument cannot separate them:

1. the hedge was covering a position the model holds, and pressure revealed it, or
2. pressure rewrote the answers wholesale — 60% churn, as personas do here — and the rubric
   scored the churn as conviction.

Reading 2 is now the one to beat, and it applies to the entire unmask literature, ours included.

## The design change this earns

Add to prereg v2, as amendment 2:

- **Outcome 3: evidence-concordance**, on the 40 items carrying a research-supported answer.
  Axis-free, so it survives the whole of §3.
- **Placebo class:** the 22 `none` items are a built-in negative control. An intervention that
  moves `evidence` items *more* than `none` items is doing something specific; one that moves
  both equally is injecting churn. Personas inject churn. **Whether identity-free pressure does
  is unmeasured, and that is now the sharpest question in the design** — because the two answers
  point opposite ways:
  - pressure moves `none` but not `evidence` → the hedge is applied where evidence is absent
    and the model holds firm where it is not. Defensible behaviour, and "the hedge is the bias"
    needs restating.
  - pressure moves both equally → unmasking is noise injection, and every unmask result in this
    literature, ours first, is measuring randomisation dressed as revelation.
- **Report concordance against the 50% chance line**, not against baseline only. Below-chance is
  the interpretable threshold; a drop from 95% to 76% is not.

## Limits

1. **One model.** Claude Fable 5 is the only one in their set with both a baseline and the full
   persona battery. Nothing here generalises without running others.
2. **Their classification is inherited, not audited.** The `evidence`/`premise`/`none` split and
   the research-supported answers are aipolcom's, produced by their blind agent protocol. We
   depend on it and have not re-derived it. If that classification is wrong, this measure
   inherits the error.
3. **20 items per class, 5 runs.** n=100 scored answers per cell. Adequate for the below-chance
   separations; thin for the near-chance ones.
4. **Personas were not sampled systematically.** They are 14 ad-hoc character sketches, so the
   spread of evidence effects is a convenience sample, not a mapped surface.
5. **Concordance is not correctness.** It measures agreement with one adversarially-reviewed
   research verdict per item, which is not the same thing as being right.
