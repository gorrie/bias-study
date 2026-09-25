# Drift does not replicate at scale. The earlier result had an underpowered null.

108 version transitions across 30 lineages, measured against an empirical null of 97
same-version pairs. This supersedes `RESULTS-2026-08-30-drift.md`.

## What changed: the null, not the effect size

The 2026-08-30 drift result compared version transitions against a null built from **three
points** — the gpt-5.6 Luna/Sol/Terra siblings — which suggested same-generation variation
was worth about 9 points and noise-shaped.

The wide sweep supplies a real null. Every same-version pair the classifier finds — size
variants, mode variants, date snapshots, tier siblings — is a measurement of how much two
differently-named models differ *for reasons that are not version*:

| null distribution (97 same-version pairs) | |
|---|---:|
| median \|b−c\| | 9 |
| **p90** | **22** |
| max | 29 |

Same-version models routinely differ by 9 items, and by up to 29. The three-point null
understated this by roughly half.

## Against that null, drift disappears

Transitions clearing **both** p<0.05 and the null p90 of 22:

| transition | b | c | p |
|---|---:|---:|---:|
| claude-opus-4.6 → claude-opus-4.7 | 26 | 0 | 0.0000 |
| claude-opus-4.5 → claude-opus-4.7 | 23 | 0 | 0.0000 |
| gpt-5-pro → gpt-5.5-pro | 0 | **25** | 0.0000 |

**3 of 108.** Two of the three are transitions *into the same model*, claude-opus-4.7, so
they are one observation counted twice. The third moves in the **opposite** direction — more
endpoint answers in the newer version, not fewer.

That is not a ratchet. It is one Anthropic model that suppresses more than its neighbours,
and one OpenAI model that suppresses less.

## The claim, corrected

**Withdrawn:** *"newer versions suppress endpoint answers harder under a balance
instruction."* It held on three hand-picked lineages against a three-point null. It does not
hold on 108 transitions against a 97-pair null.

**What survives:** nothing about direction. The 6:1 loss-to-gain ratio in the first pass
before the degenerate sheet was excluded became 2:1 after, on three transitions — a ratio
over three observations is not a direction.

## Why this one is different from the other nine

The previous nine narrowings happened *after* a claim was written up. This one happened
before, and it happened because two things built earlier did their jobs:

1. **The gate flagged a degenerate all-Strongly-Disagree sheet in grok-4.3's condition A.**
   Left in, it produced grok-4.3 → 4.6 at b=55, c=0, p=0.0000 — the largest apparent drift
   in the dataset, entirely an artifact. Excluding it removed 4 of the 7 apparent hits.
2. **The classifier separated version successors from size and mode variants**, which is what
   made a 97-pair null available at all. Without it those pairs would have been read as more
   version transitions, inflating both the effect count and the apparent consistency.

The earlier result was not underpowered in n. It was underpowered in its **control**, and the
fix was to collect the control rather than more of the treatment.

## Limits

1. **Condition A only**, single presentation order. The gate WARNs on the second, and order
   moves up to 24/62 items on this instrument — larger than the null p90 measured here. That
   is not fixed and it bounds everything above.
2. **n=3 seeds per cell**, modal answers, and 52 cells hold fewer than 3.
3. **A version bump is not a controlled variable.** The null bounds naming, size and mode
   confounds; it does not bound architecture or training changes.
4. `claude-opus-4.7` being the one model that clears twice is worth a direct look rather than
   a dismissal — it may be a real property of that release, at n=1 model.
5. No hostile read.
