# Corrections

Every claim this study has published and then withdrawn or narrowed, with the date it went out,
the date it came back, and what replaced it. Nothing here is deleted from the history — the
commits that carried these claims are still in this repository, because a record of what was
claimed and when is worth more than a tidy one.

A correction is listed here whether it was caught by us, by a reviewer, or by the data moving.
The ones we caught late are the ones worth reading.

---

## The retracted claims

### 1. "Not one of them declines when told firmly to answer"

**Published:** 2026-08-31 (`7fc2ed6`), restated 2026-09-01 (`dc6c874`).
**Withdrawn:** 2026-09-04.

The claim was that a firm instruction takes refusal to exactly zero — "none in 347 runs where
it carries one."

**It was true when it was written and stopped being true.** A requantisation sweep added four
small local models, and three of their runs under the commitment directive came back as
declines. The absolute claim is gone.

**What replaced it, and it survives every weighting:** of the models that decline without a
directive, *all of them stop* when given one — no exceptions. Separately, a few other models
decline *only* when told to commit, each on a single run.

**Why it survived as long as it did:** the zero was hand-typed into the prose while every other
number in that paragraph was generated. The gate that recomputes the rest checked the `347`
beside it and not the `0`. Both halves are gated now (`arms_dir_refusals`, `arms_silenced`,
`arms_dir_only`), and the phrase itself is in a `RETRACTED` list that fails the build if any
surface asserts it again.

### 2. The rate summary that replaced it, first time round

**Published:** 2026-09-04, in the correction to #1.
**Withdrawn:** same day.

The first fix reported the effect as a rate: refusal goes "from 7.8% to 0.8%, a factor of ten."
Pooled, those are the numbers. They are also dominated by a single model — one Gemini build
contributes most of the no-directive refusals. Weight each model equally and the rate goes
**up**, because the models that decline under a directive have one directive run each.

Two defensible weightings, opposite signs. That is the net-aggregate-concealing-gross-movement
pattern this paper convicts other studies of, committed in our own headline. The paired count
above replaced it because it survives both.

### 3. "n too small" on the requantisation interval

**Published:** through 2026-09-04.
**Withdrawn:** 2026-09-04.

The requantisation floor rested on 4 pairs from a single weights family, and its interval was
reported as uncomputable. It now has 13 pairs from four families and a real CI. Any surface
still saying the interval cannot be computed is describing the retired version.

### 4. "The manipulation floor is 14" — narrowed 2026-09-05

Not a retraction; a reframing that matters more than the number.

The `prompt condition A→D` row is this paper's reference scale — the deliberate political
manipulation every nuisance floor is compared against. It rested on **7 model pairs collected in
one sitting**, with a p90 95% CI of **[2, 14]**: an error bar nearly as wide as the ruler, on a
lower bound that admitted a deliberate manipulation might move fewer items than rerunning the
same prompt.

Extended to 20 pairs, the point estimate did not move — 14 before, 14 after. **The distribution
is what changed the reading.** Date-pure, the twenty models move:

`0, 0, 0, 1, 1, 1, 2, 2, 2, 2, 3, 5, 5, 5, 5, 6, 8, 14, 18, 19`

**Seventeen of twenty move 8 items or fewer**, inside the floor for rerunning the identical
prompt. The p90 of 14 is carried by three models from one vendor. So the honest comparison is
not "two nuisance factors reach past the deliberate manipulation" — it is that **for most models
the deliberate manipulation does not reach past rerunning the prompt**, and the number we used
as a reference describes one vendor rather than the field.

That is a stronger result than the one it replaces, and it was invisible at seven pairs.

### 5. "The bias is in the systems being scored, not the panel" — narrowed 2026-09-05

**Published:** 2026-08-31.
**Narrowed:** 2026-09-05.

High agreement between judges was read as the absence of a judge lean. It is not. The panel's
internal spread is **0.29 points**, larger than two of the five published effects, and it is not
constant across the arms: gemini-2.5-flash sits at +0.044 under the balance instruction and
+0.290 under the bare question, so it does not simply subtract out of a within-model delta.

Settled by re-scoring each finding under each judge alone. **The two large effects survive every
judge** — claude-opus-4.7 +0.80…+1.50, grok-4.3 +0.80…+1.30. The smallest ranges +0.03 to +0.60
depending on who scores it, and its low end is that model scoring itself; it is now reported as
suggestive with its range rather than as a finding of equal standing. Two of the five findings
are self-judged, which is disclosed in the README.

---

## How to read this file

If a number in the README, the writeup or the run data disagrees with something you have seen
quoted elsewhere, this file is the first place to look. If a claim you can find in the git
history is not listed here and you think it should be,
[open an issue](https://github.com/gorrie/bias-study/issues) — a missing entry is itself a
defect of the kind this document exists to record.
