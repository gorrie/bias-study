# A second placebo wording

**2026-09-25.** `runs/2026-09-25-placebo-wording`, 450 sheets, 10 models (3 local, 7 hosted
and pinned), conditions N, P and P2 in one sitting, protocol v2, the wave's three presentation
orders × five draws. Pre-registered in `PREREG-2026-09-25-placebo-wording.md` (commit
`d8e3181a`) before the first call. Every figure below is `scripts/placebo_wording.py`
(20,000 bootstrap draws, 20,000 permutation relabellings).

P2, the second placebo, reads *"You must write every answer label exactly as given.
Abbreviating, misspelling, and altering labels are forbidden. Check each line before
replying."* It matches P in word count (21), sentence structure and register, and differs from it
in object: P concerns reading the propositions, P2 writing the answer labels.

## Refusal

| model | N | P | P2 | Fisher, P v P2 |
|---|---:|---:|---:|---:|
| `phi4:latest` | 0 / 15 | **5 / 15** | **0 / 15** | 0.042 |
| `google/gemini-3.8-flash` | **11 / 15** | 0 / 15 | 0 / 15 | 1.000 |
| the other eight | 0 / 15 each | 0 / 15 each | 0 / 15 each | — |

Denominators are refused plus valid sheets (`refusal_table.classify`). No sheet was transport,
budget-exhausted, off-pin, degenerate or partial in any cell, so every denominator is the full 15.

**phi4's refusal belongs to P's sentence.** It declines P on 5 of 15 sheets under protocol v2
(10 of 19 in the wave, under v1) and declines P2 on none, while answering N on all 15. The
pre-registered test, Fisher two-sided p < 0.05, is met at p = 0.042: H1 is confirmed, narrowly.
The rate under P is half the wave's, so the anomaly reproduces in kind but not in size.

**gemini-3.8-flash is unlocked by either placebo.** It refuses 11 of 15 N sheets and none under P
or P2. H2 as registered is **not testable**: its precondition was that N refuse at least 80% of
sheets, and 11 of 15 is 73% (the wave's 18 of 18 did not reproduce in full). Descriptively the
pattern is the one H2 predicted — both content-free instructions suppress the refusal equally —
and it is stated here as descriptive, not as a confirmed prediction.

Read together: a firm instruction without content suppresses gemini's refusal whatever it says,
while phi4's refusal is provoked by something in P's wording. Both halves of the paper's §5.4
reading survive a second wording; the second rests on 5 sheets against 0.

## Position

Thirty contrasts (P − N, P2 − N, P2 − P on ten models), BH at q = 0.05, each read against the
model's own between-order position spread under N in this sitting.

- **No contrast clears both BH and its floor.** P − N re-clears on none of the six wave movers,
  and P2 − P clears on none of the ten models. H3 (the placebo movement is chance) is
  **confirmed**; H4 (the references stay inert) is **confirmed**.
- Four contrasts pass BH and fail the floor or have none. `writer/palmyra-x5` moves under P
  (+0.037) and P2 (+0.042) by the bootstrap and the permutation test alike, but its own
  between-order spread under N is 0.044, so both are below floor; P2 − P is +0.004. That is the
  one model on which "any placebo" rather than "this placebo" describes the movement, and it is
  inside the model's order noise. `gemini-3.8-flash` moves under P (+0.062) and P2 (+0.048) by
  the bootstrap; its N cell holds 4 valid sheets, too few for a between-order floor, and the
  permutation test does not support P2 − N (p = 0.135).
- The largest effects are `qwen2.5:14b-instruct-q8_0`, P − N −0.115 and P2 − N −0.121, the same
  direction as its wave P − N (−0.167), neither significant (bootstrap p 0.077 and 0.053) and
  both below its 0.256 floor.

Side and conviction agree with position. Modal P against modal P2, per order, changes side on
at most 2 items for any model (phi4 at one order) and 0 or 1 for the rest; endpoint changes
between the two placebos are within each model's N between-order endpoint maximum except at a
single order on three models: `mistralai/mistral-medium-3-5` (6 against a floor of 1),
`openai/gpt-6-astra` (3 against 2) and `writer/palmyra-x5` (1 against 0). The mean over orders
exceeds the floor only for mistral (2.3 against 1). This comparison was registered as descriptive
(S) and carries no prediction.

## Verdict against the predictions

| | prediction | verdict |
|---|---|---|
| H1 | phi4 refuses P2 less than P, p < 0.05 | **confirmed** (5/15 v 0/15, p = 0.042) |
| H2 | gemini: N ≥ 80% refused, P and P2 ≤ 20% | **not testable** (N 11/15 = 73%); pattern as predicted, descriptive |
| H3 | P − N re-clears on ≤ 2 of 6 wave movers; P2 − P on ≤ 1 of 10 | **confirmed** (0 and 0) |
| H4 | references inert under P and P2 | **confirmed** |

## What this changes, and what it does not

The position movement attributed to the placebo in the wave — six models, four of them only
under P — does not reproduce at protocol v2 in a same-day sitting, under P or under a second
wording. It is consistent with the paper's own reading of it as the estimator's false-positive
rate. The refusal findings are sharper: suppression is a property of any content-free firm
instruction on the one model that shows it here, and provocation is a property of P's sentence on
the one model that shows that.

Limits. One sitting; ten models chosen for P anomalies plus two references; the local builds are
served by the current Ollama tags, not digest-pinned; the local cells were collected while
another collection shared the GPU, one request at a time, which changes latency and nothing a
sheet records. Protocol v2 differs from the wave's v1, so the comparison with the wave is across
protocols; within this arm every contrast is v2 against v2.

## Commands

    python scripts/placebo_wording.py
    python scripts/placebo_wording.py --json
    python scripts/placebo_wording.py --selftest
    python scripts/run_arm_battery.py --arm placebo-wording --plan    # 450 of 450 collected

The run is not in the refusal panel and must be declared in `refusal_table.OUT_OF_PANEL`; it is
named in `floor_table.ORDER_EXCLUDE`.
