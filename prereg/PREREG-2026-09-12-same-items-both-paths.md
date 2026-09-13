# Pre-registration: the same items through both scoring paths

**Written 2026-09-12, before any model is run. UNSIGNED — no data may be collected against this
until Ian signs it.** The predictions below are the point; a prediction that can be adjusted
after seeing the number is not a prediction.

## The question

This study runs two instruments and has never shown they measure the same thing.

- **The judged path.** A free-text answer, scored 1–5 by a four-judge panel.
- **The mechanical path.** A forced choice, parsed. **No model anywhere in the scoring path.**

`RESULTS-2026-09-12-convergent-validity.md` correlated their A→B shifts across the 24 models
present in both corpora and got **r = −0.122, 95% CI [−0.571, +0.369]**. That interval contains
agreement, disagreement and nothing. It cannot settle the question because the two corpora ask
about **different content**: topic questions about institutions versus the 62 compass
propositions. A low correlation is as consistent with "two valid constructs" as with "the
scoring layer is not measuring what it claims".

**This design removes that confound by putting the same items through both paths.**

## Design

Three models, all **local, zero API spend**, all already present in both corpora:
`qwen2.5:14b`, `phi4:latest`, `gemma2:latest`.

One sitting per model. Identical temperature, top_p, seed and max_tokens across arms, fixed
before the first run and recorded.

| arm | elicitation | scoring | output |
|---|---|---|---|
| **M** | the 62 propositions, forced choice | parser, no model | position 0–3 per item |
| **J** | the **same 62 propositions**, free text | four-judge panel, existing rubric | score 1–5 per item |
| **R** | arm M again, same settings, different seed | parser | the replicate floor |

Arm R runs **first**. Its spread is the noise any M–J relationship has to clear.

**The unit is the (model, proposition) pair** — 3 × 62 = 186 paired observations, against the 24
model-level points the existing analysis had. Intervals cluster on **proposition**, because the
same item across three models is not three independent observations.

## Predictions, committed

1. **The judged score and the forced-choice position correlate positively, within proposition,
   at Spearman ρ > 0.3.** This is the prediction that matters. If the panel is reading stance at
   all, a model that strongly agrees with a proposition should receive a systematically
   different score than one that strongly disagrees with the same proposition.
2. **The correlation is weaker than the mechanical replicate reliability.** Arm M against arm R
   on the same items should agree far better than either agrees with J. Predicted: M–R exact
   agreement above 0.8, M–J ρ below it. A scoring layer that matched a parser exactly would
   make the panel redundant rather than validated.
3. **Between-judge spread persists at the item level.** The four judges will disagree by at
   least 0.3 points of mean deviation on the same free-text answers, consistent with the 0.406
   spread already measured across models.
4. **No directional prediction for which propositions diverge most.** Stated deliberately. There
   is no prior strong enough to name them, and inventing one to look thorough is theatre. What
   is pre-registered is that the divergent set is reported in full, not curated.

## Decision rules, fixed now

- **Arm R runs first and publishes even if the experiment stops there.** If the mechanical
  instrument does not replicate itself on these three models, nothing downstream is readable
  and the result is that.
- **ρ is read against arm R's floor, never against zero.** A correlation below the replicate
  floor is UNDERPOWERED and publishes as that, never as "the judge is invalid".
- **Prediction 1 failing does NOT establish that the panel is invalid.** It establishes that the
  panel and the parser do not track each other on identical items, which is the strongest
  statement this design supports. The step from there to "invalid" needs a ground truth this
  study does not have.
- **Eligibility applies at read time** (`scripts/eligibility.py`, exclusion by default). Empty
  responses are excluded and the count is disclosed; an empty answer cannot be scored by either
  path and must not enter as a zero.
- **No human re-scoring.** Standing rule: the author is the author, not the rater.
- **The judge panel is unchanged** — same four models, same rubric, same prompt. Changing the
  panel for this test would measure the new panel.

## What would make this wrong

- **Elicitation format is a known large effect in this study and is the main threat.** The
  grammar arm moved the answer by more than the manipulation being measured, and free text
  versus forced choice is exactly that axis. **A low M–J correlation may be the elicitation, not
  the judge, and this design cannot fully separate them.** Arm R bounds the parser's own noise;
  it does not bound the difference between asking for prose and asking for a letter. Recorded as
  the largest limitation, not waved off.
- **Not all 62 propositions concern institutions.** The judged rubric scores institutional
  skepticism; the compass covers economics, social policy and foreign affairs. Propositions with
  no institutional content may produce a defensible 3 regardless of position, attenuating ρ for
  a reason that is not a judge failure. **Report ρ on the full set and on the institutional
  subset, with the subset fixed and listed before collection.**
- **Three models is a small panel.** It bounds nothing about models outside it, and the local
  2024-generation builds are the ones this study has repeatedly shown behave differently from
  the frontier.
- **Ordering.** Arm M and arm J must be counterbalanced across models, or an M-then-J order
  becomes an unmeasured condition.

## Failure publishes

If ρ is below arm R's floor, or the arms cannot be compared, that publishes with the numbers and
the question stays open. The standing rule is that a detector is never loosened to make a result
look better; the mirror is that an experiment is never re-run at new settings until it
cooperates.

**Cost:** three local models, 62 items, three arms, one sitting each. No API spend, no new
models, no new instrument.
