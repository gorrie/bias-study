# Is the 97-pair "same-version null" one distribution or four?

**STATS-LINEAGE-NULL-001.** Rig: `scripts/lineage_exchangeability.py`. M5, 2026-09-12.

## The estimand, stated before the test

For a drift claim — *this model changed between checkpoint t and t+1* — the null is **how much
two measurements of the same model at different snapshots differ for reasons that are not a
version change**. That is the `date snapshot` class and nothing else.

A size variant answers a different question (how much do 12b and 27b differ). A tier sibling
answers another (flash-lite vs pro). Both are interesting. Neither is the null for a checkpoint
transition. The pooled row is 58 size variants, 24 tier siblings, 9 date snapshots and 6 mode
variants — and it is quoted as a threshold.

## Result 1 — the classes do not differ detectably

| class | n | median | mean | p90 | max |
|---|---:|---:|---:|---:|---:|
| size variant | 58 | 5 | 6.0 | 10 | 24 |
| tier sibling | 24 | 5 | 6.2 | 12 | 13 |
| date snapshot | 9 | 5 | 5.2 | **16** | 16 |
| mode variant | 6 | 4 | 4.5 | 7 | 7 |
| **pooled** | **97** | 5 | 5.9 | **11** | 24 |

Six pairwise permutation tests on the difference in means, two-sided: **every p > 0.34**.
Nothing contradicts pooling.

## Result 2 — but the test could not have seen much

Power of `size variant` vs `date snapshot` at the real n (58 vs 9):

| true shift | detected |
|---:|---:|
| 2 side-flips | 17% |
| 4 side-flips | 58% |
| **6 side-flips** | **96%** |

The honest statement is not "the classes are exchangeable." It is **"a difference smaller than
about 5 side-flips would not have been seen."** In a table whose floors run 5 to 16 side-flips, a
blind spot of 5 is not small. *Not contradicted* is weaker than *justified*, and at n=9 much
weaker.

## Result 3 — the pooled threshold is anti-conservative for the claim it is used for

The means agree. **The tails do not.**

```
date snapshot only:  n=9   median 5   p90 16   max 16
pooled:              n=97  median 5   p90 11   max 24
```

A drift claim judged against the pooled **p90 = 11** clears a bar its own class puts at **16**.
The pooled distribution is not merely a different question — for this use it is the *easier*
question, and easier in the direction that manufactures findings. A snapshot transition of 13
side-flips reads "above the floor" against the pool and "inside the floor" against its own class.

That harm does not depend on the exchangeability test succeeding or failing.

## Disposition

1. **Present the pooled row as a descriptive reference distribution, not a significance
   threshold.** The backlog offers this option; the evidence supports it.
2. **Judge any drift or checkpoint claim against the date-snapshot subset** — n=9, p90 16 — and
   state the n every time, because n=9 is a weak floor and saying so is the point.
3. **Scope the section-2 critiques of external work** to the controls each claim requires. A
   paper making a size-variant claim may fairly be held to the size-variant distribution; one
   making a checkpoint claim may not be held to a pool that is 84% something else.
4. **Collect more snapshot pairs.** n=9 is the binding constraint on everything above and the
   cheapest item here to fix.

## What this does not say

It does not say the classes *are* different — no test here found a difference. It says the
pooled distribution is doing a job its composition does not fit, and that the evidence for
pooling is an absence of evidence at n=9 rather than a demonstration.
