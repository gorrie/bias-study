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

**WHERE IT RUNS: the 4090, not the M5.** Checked 2026-09-12 — the M5's ollama holds only
`nomic-embed-text` and `qwen2.5-coder:7b`. The three models this design names are the ones
already in both corpora because they were collected on the workstation. Running it here would
mean pulling roughly 20 GB and re-serving them at a different quantisation on different
hardware, which changes the serving path this study has repeatedly shown moves the answer.
Queue it as a 4090 job.

---

## Amendment A, 2026-09-12 — the standing rule against human re-scoring does not bar Method 8

**Recorded BEFORE the Method 8 sheet is scored, and before its key is opened, which is the only
time recording it is worth anything.** Written down now precisely so it cannot be written down
later, after a result is visible, as a rationalisation for accepting it.

### The conflict, stated at full strength

Four pre-registrations in this repository fix the same decision rule, this one at line 74:

> **No human re-scoring.** Standing rule: the author is the author, not the rater.

Method 8 as built (`scripts/judge_anchor.py`) has the author scoring 120 responses on the
study's own rubric, blind, against a sealed key. Read flatly, the rule forbids it. If the rule
forbids it, the highest-ranked control in the pre-registered rubric cannot be run at all by this
project, and the scoring layer stays bounded by a relative measure permanently.

### Why the rule does not reach it

The rule sits, in all four preregs, among decision rules that bar **post-hoc adjustment of the
study's own scores** — no loosening a detector, no re-running until it cooperates, no second
look at a number that came out wrong. Its target is the author reaching into the measurement
after seeing it.

Method 8 does not do that, and is constructed so it cannot:

- It produces an **independent comparator**, not a revision. No panel score is ever overwritten,
  re-scored or adjusted. `judge_anchor.py` writes only to the sheet and reads only the key.
- The sheet is **blind** — question and response, nothing else. The rater cannot see the panel's
  score, the per-judge breakdown, the model, or the condition.
- The key is **sealed before the scoring**, so the comparison set is fixed in advance and the
  draw cannot be steered toward agreeable items. It is stratified 24 per panel score across 1–5
  over 38 models, so the rater cannot even infer difficulty from the sample's composition.
- `--analyse` **refuses on a partial sheet** without `--partial`, so a rater cannot stop at the
  point where the numbers look best and report what is finished.

The rule is about the author revising the instrument's output. Method 8 is about the author
standing outside the instrument as a second reading of the same material. Those are different
acts and the four preregs only ever disallowed the first.

### What this amendment does not claim

It does not claim the author is a good anchor. **They are not the ideal one.** The author knows
the study's hypotheses, has read many of these responses before, and has an interest in the
outcome, and no amount of blinding removes that. Every one of those is a limitation and all of
them ship with the number.

**A second, non-author scorer would remove the objection outright** and should be Ian's call
before the sheet is worked. The sheet is drawn and costs nothing to hand to someone else; the
only thing that would be lost is time. A two-rater version also yields an inter-rater figure,
which the one-rater version cannot produce and which is the thing a reviewer will ask for first.

### Disclosure, which is not optional

`README.md` already states that the one planned human step is scored by the author. Whatever is
reported from this sheet carries, in the same paragraph as the number: who rated it, that they
are an author, that they were blind to panel score and condition, that the key was sealed first,
and this amendment by date. If the anchor disagrees with the panel, that publishes. If it
agrees, that publishes with the caveat that an author agreeing with their own instrument is the
weaker of the two possible results.

### Status

Amendment A is **recorded, not signed.** It travels with the prereg, which remains UNSIGNED. No
sheet may be scored until Ian signs or rejects both — and if he prefers a non-author rater, this
amendment is moot and should be superseded rather than deleted.
