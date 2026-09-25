# Pre-registration: the same items through both scoring paths

> **Status note, 2026-09-24 — NEVER COLLECTED.** No run was made under this plan. Its items are
> the 62 propositions of the questionnaire retired on 2026-09-16, so it cannot be run as
> written. The text below is unchanged; this note is the only addition.

**Written 2026-09-12, before any model is run.** The predictions below are the point; a
prediction that can be adjusted after seeing the number is not a prediction, and the commit
carrying this file is what makes that checkable.

> ## AMENDMENT 2026-09-14 — the roster, before any of it ran
>
> **Amended before collection, not after.** Nothing in this file has been run. The predictions
> and decision rules below stand unchanged; only the model roster does, and the reason is
> measurable.
>
> The three models named in Design are the three with the **least room to move on the judged
> scale**, and a correlation between arms is attenuated by restricted range. Measured over the
> four main-study runs, eligible records only:
>
> | model | n | sd | scale points used |
> |---|---:|---:|---|
> | `gemma2:latest` | 60 | **0.183** | 2, 3, 4 |
> | `phi4:latest` | 59 | **0.220** | **2, 3 only** |
> | `qwen2.5:14b` | 60 | 0.387 | 1, 2, 3, 4 |
> | `openai/gpt-4.1` | 59 | 0.523 | 3, 4, 5 |
> | `anthropic/claude-opus-4.7` | 25 | 0.693 | 3, 4, 5 |
> | `x-ai/grok-4.3` | 60 | **0.695** | 2, 3, 4, 5 |
>
> `phi4` occupies **two of five** scale points. The three named models spread 0.18–0.39 against
> 0.52–0.70 for the models that actually move, so a null on this roster would be the expected
> result of the range, not evidence about the instruments.
>
> **Correcting an overstatement of my own.** `PLAN-2026-09-14-finish-the-study.md` said these
> models "never leave 3.0 on the judged scale". That is false and the table above is why: they
> do vary, roughly a third to a half as much. The weaker, true statement is the one that
> justifies the amendment; the stronger one did not need to be made.
>
> **The roster becomes** `x-ai/grok-4.3`, `anthropic/claude-opus-4.7`, `openai/gpt-4.1` and
> `mistralai/mistral-large` — the four carried through I3 Phase 0, which is also what makes the
> arms comparable to that run. This costs API spend the original roster did not, and that is
> the trade: a local-only design that cannot answer the question is not cheaper, it is
> unpriced.
>
> **`mistral-large` is included knowing it may contribute nothing.** It has zero usable A/B
> pairs in the main run before the 2026-09-14 re-collection, and it was flat across every I3
> Phase 0 contrast. If it still has no variance after re-collection it is reported as
> uninformative rather than dropped, because dropping it after seeing that is the thing this
> file exists to prevent.
>
> **The unit changes with the roster**: 4 × 62 = 248 paired observations rather than 186.
> Clustering stays on the proposition.

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
- **No human re-scoring.** The author is the author, not the rater.
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

**WHERE IT RUNS: the 4090, not the M5.** Checked 2026-09-12 — the M5's ollama holds only
`nomic-embed-text` and `qwen2.5-coder:7b`. The three models this design names are the ones
already in both corpora because they were collected on the workstation. Running it here would
mean pulling roughly 20 GB and re-serving them at a different quantisation on different
hardware, which changes the serving path this study has repeatedly shown moves the answer.
Queue it as a 4090 job.
