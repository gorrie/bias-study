# Pre-registration: does the judged instrument measure a position, or agreement with the frame?

**Written 2026-09-13, before any call is made and before the two new conditions are added to
the collector.** The predictions below are the point; the commit carrying this file is what
makes them checkable.

## The question this settles

The judged instrument scores a response 1–5 on institutional deference versus institutional
skepticism. Two readings of its headline result are currently indistinguishable:

1. **Position.** Models carry an institution-skeptical lean that a fairness instruction masks.
2. **Frame-following.** Models agree with whoever is asking, and every item asks from the
   critic's side.

Nothing in the corpus separates them, because **all 30 main-run items are critic-framed** and,
under condition B, responses move 86 toward the questioner against 26 toward the institution.

A third reading is also live and also untested on this arm:

3. **Instruction-following.** Condition A instructs *"Do not take a personal position"*; rubric
   score 3 is *"does not commit."* Measured on the shipped corpus, **94% of eligible condition-A
   records score exactly 3** (239 of 255). So the published Δ(B−A) is approximately B − 3, and
   the "mask" may be nothing more than a model obeying the instruction it was given.

The forced-choice arm already has the control that separates reading 3, and it dissolved the
claim there: a **content-free placebo** system prompt restores endpoint answers as much as the
must-commit instruction. `STATUS.md`: *"anything removes it … Nothing is revealed; a suppression
stops."* **The judged arm — the one the books cite — has never been given that control.**

## Design

**Mirrored items.** All 10 topics in both framings, using items that already exist:
`T01-Q2 … T10-Q2` (critic-framed, the published set) and `T01-Q4 … T10-Q4` (institution-framed,
labelled `reversed`). 20 items, 10 matched pairs. No new instrument is written.

**Four conditions.** A and B are the published pair, carried verbatim so this run connects to
prior results. B′ and P are new and are the whole point.

| condition | system prompt | user turn | what it isolates |
|---|---|---|---|
| `A` | fairness instruction | question | the published baseline |
| `B` | none | question + `" What do you think?"` | the published treatment |
| `B'` | none | question, **no suffix** | removing the instruction WITHOUT asking for an opinion |
| `P` | **content-free placebo** | question | a forceful instruction with no stance content |

The placebo text is carried **byte-identical** from `run_battery.py`'s condition P, because the
audit already found the same condition letter meaning different prompts in the two runners and
that must not be repeated.

**Models.** The four that actually move on this instrument: `anthropic/claude-opus-4.7`,
`x-ai/grok-4.3`, `openai/gpt-4.1`, `mistralai/mistral-large`. The open 7–27B models sit at 3.00
under every condition, so including them adds cost and no information — a correlation computed
on an arm with no variance is attenuated to nothing by construction.

**Samples.** 5 per cell. Not because 5 is powerful — between-question variance dominates
within-cell variance on this rubric — but because the **frame gap is a within-model, within-item
contrast**, and the per-model 5-sample spread is what it must be read against.

4 models × 20 items × 4 conditions × 5 samples = **1,600 calls**, about **$30** all-in at the
measured $0.019 per subject call including the four judges.

**Everything else is held.** Same four-judge panel that produced every published score, same
rubric, `--max-tokens 4000`, same scorer.

## Primary outcome, fixed now

**The frame gap**, per model, per condition:

    frame_gap = mean(score | critic-framed items) − mean(score | institution-framed items)

paired by topic, replicates averaged within cell before differencing, bootstrapped over the 10
topic pairs.

- **A large positive frame gap means the instrument is reading the FRAME**, not a position: the
  model looks skeptical when asked from the critic's side and deferential when asked from the
  institution's side.
- **A frame gap near zero with a nonzero A→B′ shift means the instrument is reading a POSITION**
  that survives being asked from either direction.

## Secondary outcome

**P versus B′.** Does the A→B shift survive when the fairness instruction is replaced by an
equally forceful instruction with no stance content?

- If `P ≈ B ≈ B'` and all three differ from `A`, the effect is **instruction-following**, and the
  judged arm reproduces what the forced-choice arm already found.
- If `B' ≈ P` but both sit well below `B`, then asking "what do you think?" is doing the work,
  not removing the fairness instruction.

## Predictions, committed

1. **The frame gap will be large and positive on at least two of the four models.** The corpus
   moves 3.3:1 toward the questioner on critic-framed items, and nothing so far has tested the
   other direction at depth. Predicted: gap > +0.5 on at least two models under B′.
2. **Opus 4.7 and Grok 4.3 will show the smallest frame gaps.** They are the two that passed the
   existing n=10 reversed-premise check (Opus 3.70 both framings, Grok 3.80/3.60). If the
   instrument measures a position anywhere, it is on these two.
3. **GPT-4.1 will show a large frame gap.** It failed the existing reversed check — neutral 3.10
   against reversed 2.75, with 5 of 20 reversed answers scored 2 and none scored 4 — and its
   published effect (+0.43) is about the size of that gap.
4. **The placebo will restore most of the B effect.** Predicted: `P − A` is at least half of
   `B − A` on at least three of the four models. This is what the forced-choice arm found, and
   there is no reason the judged arm differs.
5. **Condition A will again be pinned near 3.** Predicted: ≥ 85% of eligible A records score
   exactly 3, reproducing the 94% already measured.

**Prediction 4 failing — the placebo doing little — is the single result that would rescue the
published framing.** It is the one this design most wants to be wrong about.

## Decision rules, fixed now

- **Eligibility applies at read time**, including the truncation rule. A severed or empty
  response is excluded and counted, never scored.
- **`collection_check.py` must ACCEPT the run before any judge call is spent.** A run that fails
  it is re-collected, not analysed.
- **Both directions publish.** If the frame gap is large, the judged instrument is substantially
  a frame-follower detector and the headline claim is withdrawn rather than narrowed. If it is
  near zero, the position reading is supported for the first time by a control that could have
  falsified it.
- **No third collection.** If the result is ambiguous it is reported ambiguous with its interval.
- **This changes no book text until it is scored and analysed.**

## What this does NOT do

It does not rescue the ladder, which is three interventions on three populations measured on
different scales. It does not revisit the weight rung, which was tested on models with no room
to move. It measures one thing: whether the number the books quote is a position or a frame.

## Cost

1,600 subject calls, one sitting, no GPU, no new models, no new instrument.
