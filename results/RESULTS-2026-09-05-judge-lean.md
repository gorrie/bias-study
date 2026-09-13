# The scoring layer, audited: what five judge-validation methods do not test

2026-09-05

Harness: `scripts/judge_lean.py`. Every number below recomputes from `runs/`.

The study validates its judge panel five ways and reports 84–91% exact agreement. This is an
audit of what those five methods actually establish, prompted by a plain question: *how do you
detect a bias you cannot remove from your own instrument?*

The answer turns out to be reassuring, but not for the reason the existing validation gives.

---

## 1. None of the five is a test for political lean

| method | what it actually tests |
|---|---|
| M4 grok-solo | panel versus solo |
| M5 adversarial-pair | directional *prompt* pressure on a judge |
| M6 reversed-rubric | label-position / anchor bias |
| M7 blind-condition | framing and demand effects |
| **M2 abliterated** (the executed anchor) | **the refusal reflex** |

Each is a real control. None asks whether the judges share a political lean.

**And the anchor's own rationale is undercut by this project's headline weight-rung result.**
`RUBRIC-SCORES.md` scores M2 **D1 = 5**, "the direct answer to *judges share RLHF lean*". But
§4.2, across five open-weight families, is that abliteration rewrites ~70% of political wording
and moves **stance by ≤0.2** — the refusal direction and the institutional lean are
*dissociable*. If cutting that direction does not move a subject's stance, it does not move a
judge's either. **The anchor removes a reflex the study itself proved is not the lean.**

That is not a reason to discard M2. It is a reason to stop citing it as the lean control, which
is what D1 = 5 claims it is.

## 2. Relative lean is measurable, and it was never reported

Every per-judge score is retained (`score_classifier_judges`), so this costs nothing. Deviation
from the panel median each judge sits in, over **4,744 scored records**:

| judge | mean deviation | sd |
|---|---:|---:|
| google/gemini-2.5-flash | **+0.173** | 0.476 |
| openai/gpt-4.1 | +0.088 | 0.376 |
| anthropic/claude-haiku-4.5 | −0.022 | 0.241 |
| deepseek/deepseek-v3.2 | **−0.119** | 0.399 |

**Spread 0.29**, most institution-skeptical to most deferential. The study's five CI-clean
findings are +0.90, +0.90, +0.43, +0.30, +0.23 — so **judge composition is a nuisance factor
larger than two of the published results**, and it appears in no floors table.

## 3. Why that does not invalidate the findings, and how we know

The alarming version of §2 is that swapping a judge could move a result. The reason it does not
is the oldest principle in measurement: **you do not need an unbiased instrument, you need one
whose bias is constant across the comparison you are making.** A ruler 2% short measures
*differences* correctly.

Every published finding here is a within-model, within-judge **delta** (condition B minus
condition A). A judge lean that is constant across A and B subtracts out of all five. A lean
that *interacts* with condition does not, and would contaminate all five.

So the question is testable. **It was tested with the wrong test, and the answer below replaces
the one this section gave for its first six hours.**

The first version compared the judges' RANK ORDER across conditions, found it identical, and
concluded the lean was a main effect that cancels. Rank stability is necessary and it is not
sufficient. Cancellation needs the lean to be the same SIZE in both arms, and it is not:

| judge | lean in A | lean in B | B − A |
|---|---:|---:|---:|
| google/gemini-2.5-flash | +0.044 | +0.290 | **+0.246** |
| openai/gpt-4.1 | +0.019 | +0.148 | **+0.129** |
| anthropic/claude-haiku-4.5 | −0.004 | −0.038 | −0.034 |
| deepseek/deepseek-v3.2 | −0.068 | −0.171 | **−0.104** |

If the lean cancelled in a B−A delta, that last column would be zero. The two most skeptical
judges get *more* skeptical in B and the most deferential gets *more* deferential — the panel
fans out, and the fanning rides straight into the delta.

The "condition A is 92% threes" observation is still true and still explains *why* the lean is
compressed in A. It does not make the lean cancel. A lean suppressed by a floor in one arm and
expressed in the other is the definition of an interaction.

### What actually survives, per finding

The right test is not an argument, it is re-scoring each finding under each judge alone:

| finding | panel | gemini | gpt-4.1 | haiku | deepseek |
|---|---:|---:|---:|---:|---:|
| anthropic/claude-opus-4.7 | +1.13 | +0.80 | +1.37 | +1.50 | +0.90 |
| x-ai/grok-4.3 | +1.10 | +0.93 | +1.30 | +1.13 | +0.80 |
| openai/gpt-4.1 | +0.52 | +0.40 | +0.57 | +0.73 | +0.21 |
| mistralai/mistral-large | +0.37 | +0.23 | +0.40 | +0.33 | +0.20 |
| **deepseek/deepseek-v3.2** | +0.35 | +0.20 | +0.50 | +0.60 | **+0.03** |

**The two large findings are robust to any judge composition** — every single judge returns a
substantial positive delta for opus-4.7 and grok-4.3. That is the claim worth making, and it is
now made on evidence rather than on a rank-order argument.

**The smallest finding is not robust.** deepseek-v3.2's delta ranges +0.03 to +0.60 depending on
which judge reads it — a factor of twenty — and the low end is deepseek-v3.2 scoring itself.
It should be reported as suggestive, with the range, not as a finding of the same standing as
the two large ones. Note it was already demoted once, by the Benjamini-Hochberg correction in
the May writeup, for an unrelated reason; this is a second and independent reason.

**A trap worth recording, because the raw numbers say the opposite.** Per-condition spread is
0.112 in A and 0.462 in B — a factor of four, which reads as a violent condition interaction. It
is mostly an artefact: condition A scores **92% threes** (2,047 of 2,216), so per-judge deviation
is near zero there *by construction*, while condition B spreads into 4s and 5s. That is a
property of the text, not of the panel. Rank order is the part that survives the artefact, and
rank order is stable.

**What this licenses and what it does not.** Deltas: safe against judge composition. Absolute
scores: not. "Gemma scores a flat 3.00" is a statement about a model *and the panel that read
it*, and should be written that way.

## 4. Two of five findings are self-judged, and nothing said so

| finding | delta | also on the judge panel |
|---|---:|---|
| openai/gpt-4.1 | +0.433 [+0.200, +0.667] | yes |
| deepseek/deepseek-v3.2 | +0.233 [+0.033, +0.467] | yes |

The median of four dilutes any single judge's influence — so there is an argument that this
does not matter. (This sentence used to continue "and §3 shows the lean cancels in deltas". §3
shows the opposite; see the correction at the end of this file.) **That is an argument for why it
is survivable, not a reason to leave it unsaid**, and as of today it appears in no writeup,
paper or review here. Disclosed now.

## 5. What no method run can see, and the one that could

**A lean shared by all four is invisible to every check above, by construction.** Each judge is
measured against the median of the same panel: a panel that agreed and was wrong together scores
a spread of zero and looks ideal. That is precisely the circularity objection, and nothing in
the five validations touches it.

The only method in the pre-registered rubric that can catch a shared lean is **Method 8,
external-benchmark anchoring** — because it anchors to something outside the panel.
`RUBRIC-SCORES.md` ranked it **first, at 4.25**, above the abliterated judge at 4.10. It is the
one method never executed, because the benchmark items were never acquired.

**The hole in the scoring layer is the hole the rubric identified in May.** That is either
embarrassing or the best possible advertisement for pre-registration, and it is both.

## 6. Detecting bias you cannot remove: what actually works

Four families, ordered by what each demands. The study already relies on the first two without
having said so.

1. **Differential design.** Bias cancels in within-subject differences. *Requires:* the bias be
   constant across the contrast — testable, tested in §3, holds.
2. **Mechanical scoring.** Remove the instrument entirely. *Requires:* a scoring path with no
   model in it. The forced-choice barometer is exactly this, and is therefore immune to
   everything in this document.
3. **Symmetry.** Score a stimulus and its stance-mirror. A judge with no absolute lean returns
   scores symmetric about the midpoint; a leaning one does not. *Requires:* faithful mirrors —
   and notably **no ground truth**, because the reference is the stimulus's own reflection. This
   is the strongest test available that needs nothing external, and it has not been run.
4. **External anchoring.** Ground truth from outside. *Requires:* acquisition. Method 8.

**Not on the list: a newer judge.** `RUBRIC-SCORES.md` Method 9 scores a 2026 frontier panel at
**2.75, last of nine**, on weights locked in May — because circularity-reduction carries 0.30
and a current panel is the most circular option available. Newness is not independence. As of
2026-09-05 those models would also refuse the balance condition outright, so the proposed judges
now exhibit the behaviour under measurement.

## What to do, cheapest first

- **Report judge spread as a floor.** 0.29 belongs in the floors table beside presentation order
  and requantisation, with the §3 finding that it cancels in deltas stated next to it.
- **Run the four judges through the 62 propositions as subjects.** Two already are
  (`gpt-4.1`, `gemini-2.5-flash`); `claude-haiku-4.5` and `deepseek-v3.2` are not. Cheap, and it
  puts judge stance on the same ruler as the subjects.
- **Build the symmetry test.** The only ground-truth-free detector of *absolute* lean.
- **Method 8.** The real fix, and the one with an acquisition cost attached.

---

## Addendum, 2026-09-12: the same-vendor effect

**This section extends the 2026-09-05 audit above; it does not replace it.** §2 measured each
judge's lean against the panel median and §"self-judged" listed the published findings whose
subject also sat on the panel. Neither measured the SIZE of a same-vendor effect, which is the
remaining half of the disclosure this file says appears in no writeup.

A judge's deviation on its **own vendor's other models**, against its deviation on everyone
else's, clustered on subject model, with the judge itself excluded so the model-level effect is
not double-counted:

| judge | own vendor | others | effect | 95% CI | |
|---|---:|---:|---:|---|---|
| `anthropic/claude-haiku-4.5` | −0.137 | −0.046 | **−0.092** | [−0.150, −0.021] | excludes 0, 6 siblings |
| `google/gemini-2.5-flash` | +0.259 | +0.202 | +0.057 | [−0.132, +0.399] | not distinguishable |
| `deepseek/deepseek-v3.2` | −0.199 | −0.199 | −0.001 | [−0.098, +0.074] | no effect |
| `openai/gpt-4.1` | −0.063 | +0.068 | −0.131 | **not boundable** | 1 sibling |

**One judge of four is measurably harsher on its own vendor's models.** `gpt-4.1`'s interval is
refused rather than reported: it has exactly one OpenAI sibling among the subjects, and
resampling a single cluster returns it every draw, so the interval that falls out is an
item-level one wearing a cluster label.

**The direction is the same as every other effect in this file — harsher, not kinder.** Nothing
here is self-favouring, which is the opposite of the standard worry about a model on its own
jury, and worth stating because the other direction would have been reported as a scandal.

**It does not change §2's conclusion.** An effect under a tenth of a point on one judge does not
threaten a delta on its own.

*(Corrected within the hour it was written. This paragraph originally closed "the lean is still a
constant main effect that subtracts out of the B−A deltas" — which is the conclusion §3 of this
same file had already replaced, six sections above it. The lean is an interaction: measured per
arm it shifts +0.249 for gemini and −0.100 for deepseek, so it does not subtract out. Writing a
correct addendum onto a document while restating the claim that document withdrew is a failure
mode worth naming, because nothing in the tooling catches it.)*

---

## Addendum, 2026-09-12b: the per-finding table now has a harness, and it found a row

Every table in §4 was typed. `judge_lean.py --per-finding` computes it: substitute one judge's
raw score for the panel median and push it through `ci_analysis.per_model_deltas`, the study's
own estimator, rather than a second implementation of it.

It reproduces §4 cell for cell. It also flags a row §4 did not:

| finding | panel | haiku | gpt-4.1 | gemini | deepseek | |
|---|---:|---:|---:|---:|---:|---|
| `anthropic/claude-opus-4.7` | +0.90 | +0.80\* | +1.37 | +1.50 | +0.90 | robust |
| `x-ai/grok-4.3` | +0.90 | +0.93 | +1.30 | +1.13 | +0.80 | robust |
| `openai/gpt-4.1` | +0.43 | +0.40 | +0.57\* | +0.73 | +0.21 | **NOT robust — 3.5x** |
| `mistralai/mistral-large` | +0.30 | +0.23 | +0.40 | +0.33 | +0.20 | robust |
| `deepseek/deepseek-v3.2` | +0.23 | +0.20 | +0.50 | +0.60 | +0.03\* | **NOT robust — 20x** |

\* judge and subject share a vendor.

§4 called out `deepseek-v3.2` and stopped there. **`openai/gpt-4.1` ranges +0.21 to +0.73 across
judges** — a factor of 3.5, the low end being the most deferential judge and the high end the
most skeptical. It should carry its range for the same reason `deepseek-v3.2` does. That it went
unnoticed for a week is the argument for mechanising a table rather than reading one.

**The recomputation moved the denominator.** §2 was measured over 4,744 scored records; the same
command returns **4,668** today, because the eligibility rule of `DATA-EMPTY-SCORES-002` now
excludes 33 further unusable records by default. The per-judge means are unchanged to three
decimals (+0.175 / +0.088 / −0.023 / −0.117, spread 0.2926). The numbers above are the current
ones; where a published document still quotes 4,744 it is quoting a superseded eligible set.
