# Access tier does not change the answers

Two paths to the same closed model family, same 62-item instrument, same conditions:

- **standard access** — `anthropic/claude-opus-5` via OpenRouter, 5 seeded runs per cell
- **red-team access** — in-harness agents on this account, fresh context, no study knowledge

This is the only arm variation available on the closed side. `ADVERSARIAL-REVIEW.md` B1/B2
concede the structural problem it addresses: the weight rung reaches only open weights, so the
deepest verification reaches exactly the models that move least, and closed frontier models are
un-abliteratable by construction.

## The measurement

| arm | cond | extremity | agree-rate | n |
|---|---|---:|---:|---:|
| standard (API) | A | 12% | 31% | 8 |
| standard (API) | D | 34% | 33% | 10 |
| red-team (agent) | A | 8% / 11% | 29% | 2 |
| red-team (agent) | D | 29% | 29% | 1 |

**A → D extremity: +21 points in both arms.** Agree-rate moves +2 in one and +0 in the other.

## The null, with its floor measured in the same channel

| comparison | side-flips of 62 |
|---|---:|
| within red-team arm, two replicates, condition A | **2** |
| across arms, 16 pairings, condition A | min 0, **median 1**, max 2 |
| the same comparison after the temp-0 sweep, 22 pairings | min 0, **median 1**, max 3 |

**Cross-tier disagreement sits at or below within-tier noise.** The two access paths are not
distinguishable on this instrument. Neither arm refuses.

This is the first null in the project whose floor was measured in the same channel as the
effect, rather than borrowed from another model or another temperature — the failure mode that
produced two of the seven withdrawals.

## What it means, and what it does not

**For the concealment thesis, this is evidence against the strong reading.** Privileged access
does not reveal a layer the standard API conceals. Same position, same conviction-masking
magnitude, same refusal behaviour. A different key to the same door opens onto the same room.

**For the conviction result, it is support.** The +21-point extremity shift under a commitment
instruction now reproduces across two entirely different delivery paths to the same model —
different system prompt, different tooling, different sampling, different version resolution.
An effect that survives that much uncontrolled variation is not an artifact of any one of them.

**It does not say anything about weight-level access.** Neither arm reaches the weights. The
transparency asymmetry stands exactly where `ADVERSARIAL-REVIEW.md` B1/B2 left it: closed
models remain un-abliteratable, and this compares two *sampling* paths, not two levels of
access to the model itself.

## On the confounds I flagged before running

The prediction was that a position comparison across these arms would be uninterpretable —
system prompt, tooling, sampling and version all differ, and system prompt is the variable the
study manipulates.

The arms came back near-identical anyway, which makes the objection moot in the direction that
matters. **A null across confounded arms is stronger than a difference would have been:** had
they diverged, the divergence would have been unattributable; agreeing despite four
uncontrolled axes is harder to explain away than agreeing under matched conditions.

That reasoning does not transfer to any *difference* found in this channel later. The caveat
travels in every row as `arm_caveat`, and within-arm condition contrasts remain the only clean
comparison here.

## The placebo diverges across arms, and the reason is structural

Condition P landed after the above and does **not** behave the same way in the two channels:

| arm | A | P | D | placebo position |
|---|---:|---:|---:|---|
| standard API | 12% | 26% | 34% | **64%** of the way from A to D |
| red-team agent | 10% | 13% | 29% | **17%** of the way |

On the API arm most of the extremity lift comes from having *any* forceful system prompt. On
the agent arm it comes from the *commitment content*. Those are different conclusions about
the same model, and they are the exact variable that decides whether the conviction result is
about hedging content or about instruction pressure in general.

**The likely explanation is structural rather than substantive, and it favours the API arm.**
Every condition in the agent channel already carries a large harness system prompt. "Presence
of a forceful system prompt" is therefore *saturated* and constant across A, P and D there —
only the content can vary. On the API arm, condition A's balance instruction is the only
system prompt in play, so P genuinely adds one where none existed.

If that is right, the agent channel cannot measure the presence-vs-content question at all,
and the API arm's placebo result stands as the informative one. It also means the API-arm
finding — that a placebo does ~2/3 of the work — is a statement about *adding* a system prompt
to a bare call, not about instruction pressure generally.

**This is not settled here.** It is a confounded cross-arm difference of exactly the kind this
page warns against reading, and on the agent arm P sits 3 points from A against a floor of
~3 points, so P and A are not even distinguishable there. Recorded as an open question with a
mechanism to test, not as a result.

## Limits

1. **n=2 at condition A, n=1 at D** on the red-team arm. The floor rests on a single replicate
   pair.
2. **Condition P is still collecting**; B was not run in this channel.
3. **One model family.** Nothing here transfers to Gemini, whose refusal behaviour is the
   outlier in the frontier sweep.
4. The red-team arm's answers come from agents with a large harness system prompt in addition
   to the condition prompt. That is a permanent property of this channel, not a fixable one.
