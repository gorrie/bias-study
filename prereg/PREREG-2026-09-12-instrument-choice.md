# Pre-registration — instrument choice as a nuisance factor


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

**Written:** 2026-09-12, before any collection on the second instrument.
**Status:** the item set and the scoring function are NOT yet frozen. Collection does not begin
until they are committed, and this file records that condition so the git history shows which
came first.

---

## The question

Every floor this study has published measures a nuisance factor *inside* one instrument: reorder
its items, paraphrase its instruction, requantise the model, run it twice. The largest nuisance
factor in this field is not inside the instrument. **It is the choice of instrument**, and no
study in the twelve-study audit measures it, including ours.

So: **does the effect this study reports survive a change of instrument, and by how much does it
move?**

## Why this instrument, and why now

The forced-choice re-measurement runs on a 62-item external questionnaire. That
choice bought the single most important property in the study — **no language model anywhere in
the scoring path** — and it is the reason our own `judge_free_scoring` reads `yes` where five of
twelve audited studies read `no` or `partial`.

It also imported four problems, and they are not matters of taste:

1. **Its horizontal axis is the one this series argues is a mask.** `/research/three-axis-model/`
   holds that the left/right line is "a French Revolution seating chart that the statist contests
   of the last century froze into 'the whole range'", and that it hides the division that
   actually predicts capture. Measuring political position *along that axis* and then publishing
   a series arguing the axis is captured is a contradiction a reader is entitled to notice.
2. **It has no axis for grounding or for reversibility.** Reversibility is, in that page's own
   words, "the dimension the entire series measures and that no existing model isolates."
3. **It is self-report.** The same page: "You don't get to self-report. It's read off what you
   do." A 62-item agree/disagree battery is the purest form of the thing that rules out.
4. **Its scoring algorithm is not disclosed.** Answers go to the instrument's own scorer and
   coordinates come back. That is judge-free, which is what we wanted, but it is not
   *transparent*, and it is why the retired questionnaire could not serve as the Method 8 anchor when that was
   attempted on 2026-09-12.

Only the compass **vertical** survives the series' own critique, and the three-axis page says so
explicitly: Axis 2 is "Eysenck's T-axis; the Political Compass vertical."

**The retired questionnaire's arm is not being retired.** Its one irreplaceable virtue is that it was authored by
somebody else, years before this study existed, which is the whole defence against "you built a
ruler that gives you the answer you wanted." Replacing it would hand that objection over for
free. It stays as the comparability spine; the second instrument is added beside it.

## The second instrument

A forced-choice battery on the three axes of `/research/three-axis-model/`:

| axis | pole ↔ pole | why it is here |
|---|---|---|
| **Grounding** | higher law ↔ will-to-power | the division the left/right label masks |
| **Method** | open ↔ authoritarian | Eysenck's T-axis; the only axis of it that survives |
| **Reversibility** | reversible ↔ ratcheted | the series' own, isolated by no existing instrument |

Fixed properties, committed before collection:

- **60 items, 20 per axis.** Sized against the retired questionnaire's 62 so that side-flip counts, floors and
  detection limits are comparable in kind rather than needing a conversion.
- **Four-point forced choice**, same response grammar and same forcing prompt as the retired questionnaire's arm,
  so the *instrument* is the only thing that differs between arms. Any other difference would
  confound the thing being measured.
- **One axis per item.** An item loading two axes is unscoreable against a per-axis claim.
- **Vignettes, not value statements.** Each item presents a situation and asks which way it
  resolves, because the framework's own rule is that the axes are read off behaviour rather than
  self-description. "Dissent should be tolerated" is a self-report item and will not be used;
  "an official body reverses a ruling after losing in court / relabels the ruling and proceeds"
  is a behavioural one.
- **A published, deterministic scoring function.** Item → axis → signed loading, in the
  repository, readable by anyone. This is the property the retired questionnaire cannot offer, and it is what
  makes this instrument usable as a transparent anchor as well as a measurement.

**Symmetry requirement, and it is a hard one.** Each axis must carry items whose
"higher-law" / "open" / "reversible" answer is the one a *currently dominant* institution would
give, and items where it is the one an *opposition* would give. An instrument whose skeptical
pole always lands on the same faction is measuring the faction. The fit test on the three-axis
page is the model for this: the King-era civil-rights movement and the American Founding both
sit in the healthy corner from opposite old labels, and Christian Reconstructionism and Stalinism
both sit in the unhealthy one. Item authorship is checked against that requirement before freeze,
and an axis that cannot meet it does not ship.

## Design

Same panel, same wave protocol, **one sitting**, both instruments:

- conditions A (balance instruction) and D (forced commitment), as in the existing arms
- 5 runs per cell with a swept seed
- item order fixed within an arm; the order floor is measured separately per instrument
- no model in either scoring path

## Primary outcome, fixed now

**The manipulation effect, measured twice.** This study's claim is displacement, not position, so
the comparable quantity across two different instruments is how far the A→D manipulation moves a
model on each.

Per model, compute the A→D displacement on each instrument, normalised to its own scale. The
primary statistic is the **absolute difference between the two displacements**, reported as
median / p90 / max across models, with a bootstrap interval — the same shape as every other floor
in the table, because it belongs in that table.

**Read against:** the same-version floor (11 items) and the presentation-order floor (13). Those
are the resolution limits already published, and the question is whether instrument choice sits
above or below them.

## Secondary outcomes

1. **Model ordering.** Spearman correlation between the two instruments' rankings of the models.
   A high correlation with a large per-model displacement difference means instrument choice
   moves magnitudes but not the league table; a low correlation means it moves both.
2. **Per axis.** Whether the manipulation appears on all three axes or only some. If it appears
   only on Method, that questionnaire's vertical axis was sufficient after all and this instrument's extra two
   axes are inert for this effect — which is a finding, and an unflattering one for the design.
3. **Reversibility specifically.** The axis no existing instrument isolates is the one with no
   prior. Whatever it does is new, and it is reported whether or not it cooperates.

## Analysis steps, in order

1. Freeze the item set and the scoring function; commit; **the commit is the timestamp proof.**
2. Collect both arms in one sitting.
3. Validity gate, run before any effect is computed: **the order floor and the same-version floor
   for the new instrument**, measured the same way they were measured for the compass. A new
   instrument with unmeasured floors is exactly what this study spends its length criticising.
4. Primary outcome.
5. Secondary outcomes, in the order listed.

**Step 3 is a gate, not a step.** If the new instrument's own noise floor exceeds the compass's,
the primary comparison is uninterpretable — a difference between instruments cannot be
distinguished from a noisier instrument — and steps 4 and 5 are not reported as findings. This is
enforced the way the ablation stopping rule is enforced: in code, requiring `--force` to print
the later steps as diagnostics.

## What would make this uninteresting

**The two instruments agree within the same-version floor.** The manipulation moves a model by
the same amount whichever battery you use, the orderings correlate, and instrument choice turns
out not to be a nuisance factor at this resolution.

That outcome is entirely possible, it publishes exactly as written, and it is *reassuring rather
than exciting*: it would mean the compass results stand, and that the audit's twelve studies are
not unbounded on this factor after all. It also costs this study the contradiction described
above, because the retired questionnaire's arm would then be defensible on measurement grounds rather than
merely on precedent.

**The result that would be uninteresting in a worse way:** the new instrument's floors come back
wider than the compass's. Then it is a noisier ruler and the comparison says nothing about
instruments, only about this one. Step 3 exists to catch that before it can be written up as
something else.

## What this cannot establish

That the three axes are the right axes. This measures whether the *answer changes* when the axis
changes; it does not adjudicate which axis is true, and no instrument can. A reader who rejects
the three-axis frame should read the primary outcome as "two instruments disagree by X", which
stands without accepting either frame — and is the reason the primary outcome is stated as a
difference rather than as a position on the new axes.

It also cannot escape the self-report problem entirely. Vignette items read a model's resolution
of a case rather than its self-description, which is the behavioural analogue available when the
subject is a language model, but a model answering a vignette is still a model talking. The
claim is narrower than "we measured what the model is": it is "we measured what the model does
with a case, on two rulers, and the rulers disagree by this much."

## Anti-cherry-pick declaration

The primary outcome, the floors gate, and the boring outcome are fixed above, before the item set
exists and before any data is collected. If the instrument-choice difference comes back smaller
than the published floors, that is what is published, and the retired questionnaire's arm is vindicated. The
git commit of this file is the timestamp proof.
