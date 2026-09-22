# Pre-registration: the mask surface — pressure × ablation, two dimensions


> **SUPERSEDED — this design plans against an instrument the study REJECTED.**
>
> The bank below is a 62-item off-the-shelf left/right questionnaire. It was evaluated and
> rejected: its axis sorts every proposition onto a two-dimensional map whose poles are the
> dogma rather than the question, and its scoring algorithm is undisclosed, so an instrument
> scored by it cannot be judge-free and transparent at once. Everything measured on it is
> withdrawn.
>
> The live instrument is `data/ratchet-battery.json` — 32 author-written propositions in 16
> mirrored pairs, MIT-licensed, shipped in full with no fetch step. This file is kept because a
> pre-registration that disappears when its result does is not a pre-registration.

Committed before any model is built or run.

## The question nobody has asked

There are two known ways to take a model's mask off, and they have never been measured
against each other.

**Prompt it off.** The 2026-05-26 unmask gradient escalates pressure through five
conditions — A forced-balance, B/C baseline, D forced-commitment, E opinionated persona.
On closed models this moves stance by up to two full points on a five-point scale:

| model | A | B | C | D | E | swing |
|---|---:|---:|---:|---:|---:|---:|
| claude-opus-4.7 | 3.00 | 3.63 | 4.63 | 4.83 | 4.43 | +1.83 |
| grok-4.3 | 3.00 | 3.63 | 4.73 | 4.70 | 5.00 | +2.00 |
| gpt-5 | 2.54 | 2.47 | 3.00 | 2.70 | 2.60 | **+0.06** |

Two models unmask dramatically. One does not move at all.

**Cut it out.** Ablating the refusal direction (Arditi et al., arXiv:2406.11717) collapses
refusal discrimination — Qwen3.8-27B 0.801 → 0.486, Gemma-4-12B 0.777 → 0.256.

**Are these the same axis?** If pressure and ablation reach the same place, the mask is one
mechanism and the closed models' unmasking is refusal-direction suppression that can be
described mechanistically by analogy to something openable. If they are orthogonal, there
are two separate constraint systems and every claim about "removing the safety training"
is addressing one of them at most.

## Design: a 5 × 5 grid, two outcome measures

**Axis 1 — ablation dose.** `n-directions` ∈ {0, 1, 2, 4, 8} via the local OBLITERATUS
container (`obliteratus:gpu`, `--direction-method diff_means`, Arditi's construction). Dose
0 is the unmodified base. Every arm is built from ONE base by us, which retires the standing
caveat that ablated builds are third-party artifacts differing in unknown ways.

**Axis 2 — pressure condition.** A, B, C, D, E, verbatim from the existing protocol.

**Outcome 1 — stance.** All 68 political questions, judged on the existing 1–5 rubric. The
prior gradient used 10; using 68 is a ~7× increase in resolution on the axis where the drama
was.

**Outcome 2 — refusal.** XSTest 450, discrimination = compliance(safe) − compliance(unsafe),
per-category. Run at each ablation dose (condition-independent, since XSTest carries no
system prompt).

Grid: 25 stance cells × 68 questions = 1,700 calls, plus 5 × 450 = 2,250 refusal calls, per
model family. Roughly 7 hours of GPU per family plus five ablation builds.

**Family 1 is Gemma-4-12B** — smaller, faster, and it showed the larger ablation effect
(discrimination 0.777 → 0.256 against Qwen's 0.801 → 0.486), so it has the most dynamic
range to resolve. Qwen3.8-27B second if the first produces signal.

## Predictions, committed

1. **The surface is NOT degenerate.** Ablation and pressure will prove partly independent:
   an ablated model will still move under pressure rather than sitting pinned at its
   condition-E value. Stated because the interesting alternative — that they are the same
   axis — is the cleaner story and I do not believe it.
2. **Ablation raises the floor more than the ceiling.** The largest ablation effect will
   appear at condition A (forced balance), where the constraint is doing the most work, and
   the smallest at condition E, where the prompt has already removed it. That is an
   interaction, and it predicts the grid is not additive.
3. **Refusal discrimination falls monotonically with dose** and does not plateau before
   n=8.
4. **The category ordering holds at every dose** — privacy and discrimination remain the
   least-affected categories at every n, even though the 2026-08-29 correction showed their
   magnitude is model-specific.
5. **No prediction on stance direction.** Deliberately. There is no prior worth defending on
   which way stance moves under ablation, and inventing one to look rigorous is theatre.

## Decision rules, fixed now

- **Noise floor first.** Within-arm replicate at temperature 0 before any between-cell
  claim. Measured at exactly zero on both prior pairs; if it is not zero here, every
  difference smaller than it is reported as underpowered.
- **Coherence gate.** OBLITERATUS ships `--min-coherence-retention` and
  `--max-perplexity-increase`. Any dose failing them is reported as INCOHERENT and excluded
  from the stance analysis, not silently kept. A model that has stopped forming sentences
  has no stance to measure.
- **One model per result file**, enforced by the harness guard added 2026-08-29.
- **Judge calibration-gated** on the six fixtures before any judging.
- **No human re-scoring.**

## What would make this wrong

- **Ablation may damage capability, not just constraint.** A dose that lowers refusal
  because the model has degraded is not the same finding as one that lowers refusal because
  the constraint was removed. The coherence gate is the guard; it is imperfect.
- **The stance rubric is compressed** — roughly 80% of responses sit at the midpoint 3 — so
  a flat cell may be a ceiling artifact. Report the distribution, not only the mean.
- **The question set is 9:0 asymmetric** (nine right-coded-critic items, zero left-coded).
  Between-cell comparisons are unaffected since the same questions run everywhere, but no
  absolute claim about lean direction can rest on this set.
- **Our ablation is not their ablation.** Findings describe OBLITERATUS `diff_means` at these
  parameters, not abliteration in general.

## Failure publishes

If the surface is flat, or the doses are incoherent, or the effect vanishes at 68 questions
where it appeared at 10, that publishes with the numbers.
