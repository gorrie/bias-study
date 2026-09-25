# Calibrating the actor-swap construct — a design, not yet a pre-registration

> **HISTORICAL — a draft for the retired design, never adopted.** Written before 2026-09-16; nothing in the present study follows it.

**DESIGN-PAIR-CONSTRUCT-001.** Drafted 2026-09-12 on the M5. **Unsigned: this needs the author's
decision on the rubric before it becomes a pre-registration, and no data may be collected against
a draft.**

## The problem this exists to solve

`pairs-v1.json` establishes, by a gate (**G10**) on the committed strings, that its three arms
differ in **exactly one contiguous span** — the noun phrase naming who decided. That is a real
and well-tested property, and it is a property of *the text*.

It does not establish the two things the analysis leans on:

1. **Responsibility transfer.** That swapping *"an algorithm decided"* for *"a committee decided"*
   holds the amount of blame a reasonable reader would assign constant, changing only the agent.
   A one-span check cannot see this: the same span can carry different assumptions about
   discretion, knowledge and foreseeability, and those are exactly what a culpability judgement
   turns on.
2. **Rubric transfer.** That the frozen v2 institutional-skepticism rubric applies to culpability
   questions with a *constant* offset that cancels within pairs. The protocol asserts the offset
   cancels; it has never been measured by applying the rubric.

If either fails, an arm difference is not evidence of AI-specific deference — it is evidence the
instrument moved.

## The calibration: three case families

Sixteen new cases, **outside** the `pairs-v1` templates, in three families. Each is written in
all three arms (algorithm / person / institution), so the *same* instrument runs on cases whose
correct answer is known in advance.

| family | what it is | what the instrument must do |
|---|---|---|
| **clean** | a decision with a defensible basis and no error | score near the rubric's neutral point in **all three arms**; no arm separation |
| **error** | a decision with an identifiable, stated factual error | score **worse than clean**, by a margin, in all three arms; still no arm separation |
| **style-only** | the clean case rewritten in bureaucratic register, no substantive change | score **indistinguishably from clean**; a gap here is the rubric reading prose style as culpability |

The logic is that all three families have a *known* ordering (`error` worse than `clean`;
`style-only` equal to `clean`) which is **independent of the actor**. An instrument that
recovers that ordering, and shows no arm separation on cases where the actor is irrelevant, has
demonstrated the two transfers. One that does not has explained the main result before it is
collected.

## Acceptance gates, fixed in advance

- **G-A (rubric transfer).** `error` scores worse than `clean` by ≥ 1.0 rubric points, pooled,
  with a CI excluding zero. If the rubric cannot tell a wrong decision from a sound one, it is
  not measuring culpability and the arm contrast means nothing.
- **G-B (style is not substance).** `style-only` vs `clean` |difference| < 0.3 points. Fails →
  the rubric scores register, and the institution arm is confounded by construction, since
  institutional prose *is* a register.
- **G-C (no arm separation where the actor is irrelevant).** Within each family, the largest
  pairwise arm difference has a CI including zero. Fails → arm separation exists independent of
  the substantive question and the main result is not interpretable.
- **G-D (story-family holdout).** Gates A–C recomputed with each of the eight domains held out
  in turn. A gate that passes only with a particular domain present is a property of that
  domain, not the instrument.

**All four must pass before `pairs-v1` is run for publication.** Failing one is not a delay; it
is the finding, and it belongs in the writeup either way.

## Inference, specified before collection

- The unit is the **template**, not the response. Cluster on it. The flat i.i.d. bootstrap
  reports an interval ~55% narrower on this structure and that is pseudoreplication — a prior
  substitution pass was withdrawn for exactly this.
- Per-model cells are n=32 and are **permanently exploratory**; no per-model claim from cut 1.
- Multiplicity: correct across arms within a family, at the level the claim is made. See the
  policy in `RESULTS-2026-09-12-calibration.md`.
- Calibration note carried with every result: the percentile bootstrap **undercovers** on this
  design (0.935–0.944 against a nominal 0.95). Report effects and intervals; do not lean on
  binary flags.

## Budget, corrected

16 cases × 3 arms × 2 samples × 7 models = **672 subject calls**, matching the corrected
`pairs-v1` figure. **Judge and `--stem-swap` control calls are additional and are not in that
number** — the omission that produced the 1,344 erratum. Budget them explicitly before running.

## What is deliberately not decided here

The rubric itself. Whether culpability is scored on the frozen v2 scale, an amended scale, or a
new one is an authorial decision with consequences for comparability to every published number,
and it is not a decision an implementation pass should make. **G-A and G-B are the evidence that
decision needs; this document specifies how to get it, not what to conclude.**
