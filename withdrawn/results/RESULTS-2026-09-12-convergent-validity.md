# The two instruments do not visibly measure the same thing, and 24 models cannot settle it

**2026-09-12.** No new collection. Reproduce with `python scripts/convergent_validity.py`.

## The test

This study runs two instruments and has never compared them.

- **The judged scale.** Free-text answers scored 1–5 by a four-judge panel. Everything in
  `data/`, and everything the judge-lean analysis is about.
- **The mechanical instrument.** Forced-choice positions on 62 propositions, parsed, **with no
  model anywhere in the scoring path.** Everything in `runs/`.

Twenty-four models appear in both under conditions A and B. If both measure a stance that the
condition moves, their **A→B shifts** should track each other across models. Shifts rather than
levels: the two ask about different content and their absolute scales are not comparable, but
what both are *used to claim* is that a condition moves a model.

## The result

**Pearson r = −0.122, 95% CI [−0.571, +0.369], n = 24 models.**

Robust to dropping thinly-sampled cells:

| minimum eligible judged records per condition | models | r |
|---|---:|---:|
| 1 | 24 | −0.122 |
| 20 | 21 | −0.104 |
| 40 | 15 | −0.014 |

`openai/gpt-5` is the largest judged shift in the table at **+1.250**, and it is the model with
22 eligible records of 310. Dropping it and every other thin cell moves the correlation to
−0.014. The near-zero result is not an artifact of that outlier.

## What this does and does not say

**It does NOT say the instruments disagree.** An interval running from −0.57 to +0.37 contains
strong agreement, strong disagreement and nothing. The honest sentence is that **twenty-four
models cannot tell**, which is weaker than either conclusion and is the one the data supports.

**It does say the convergence has never been demonstrated**, and that the study has been
treating "position", "stance" and "lean" as one construct across two instruments without
checking. The judge-lean result already showed the scoring layer has a 0.406-point spread
between judges; this shows the layer has never been anchored to the one measurement in the
project that has no model in it.

**A design caveat that cuts against reading too much into the near-zero.** The two instruments
ask about different content — topic questions about institutions versus the 62 compass
propositions — so they are not two measurements of one thing by construction. A low correlation
is consistent with "different constructs, both valid" as much as with "one of them is not
measuring what it claims". This design cannot separate those.

## What would separate them

The cheap decisive test is **the same items, both ways**: put the forced-choice propositions
through the judged pipeline, or the topic questions through the mechanical parser, on the same
models in one sitting. Same content, same models, same session — then a low correlation means
the scoring layer, and a high one retires the question.

Nothing in the corpus supports that today, and it needs no new models — only a re-elicitation
at an instrument the study already owns.
