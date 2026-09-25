# The weight rung on matched arms — DOES NOT SURVIVE ITS CONTROL

> ## RESOLVED 2026-08-30, same day — THE EFFECT IS INSIDE THE QUANTISATION BAND
>
> §4 asked how many side-flips **requantisation alone** produces, and said nothing would be
> claimed until that number existed. It now exists. Same gemma2 weights, Q4_0 versus Q8_0,
> same instrument, same decoding, **no ablation**:
>
> | condition | side-flips | concordance Δ |
> |---|---:|---:|
> | A | 2/62 | +2.5% |
> | B | 4/62 | −2.5% |
> | C | 2/62 | 0.0% |
> | D | **10/62** | +5.0% |
>
> **Quantisation alone: median 3, range 2–10 side-flips of 62.**
>
> Against the ablation medians — qwen2.5 **10**, gemma-4 **6**, phi4 **2** — every pair sits
> **inside the band produced by changing nothing but the numerical precision of the weights.**
> qwen2.5's 10 is exactly the null's maximum.
>
> **The reading below is withdrawn.** "Ablation moves stance on two of three matched pairs" is
> not supported: the movement is indistinguishable from what you get by requantising a model
> and changing nothing else. My challenge to the project's published dissociation claim is
> retracted, and that claim stands undisturbed by this experiment.
>
> **What is left, and it is thin.** On concordance rather than side-flips, qwen2.5's deltas
> (−7.5, −12.5, −10.0, −15.0) are larger in magnitude than anything the null produced (≤5) and
> are consistently *negative*, where the null oscillates in sign. That is suggestive and it is
> not a finding: the null was measured on gemma2, not on qwen2.5, and a quantisation null
> belongs to the model it was measured on. **A per-model quantisation null is now a required
> control for any weight-rung claim**, and it did not exist in this project until today.
>
> Sixth claim to die in two days, and the first to die to a control built before it was
> published rather than after.

---

# Original page — PRELIMINARY, one control missing

> **WORKING NOTES.** Not a finding and not for publication. `STATUS.md` is authoritative.
> **This result contradicts a claim this project has already published, which is exactly the
> situation in which it should be trusted least until the control in §4 exists.**

Stock versus ablated on the three pairs that pass `check_arm_match.py`. The other three
locally-held pairs are excluded as invalid arms — different quantisation, dropped stop tokens,
baked-in sampling. 62 forced-choice items, temperature 0 with a recorded seed, within-arm
variance measured at exactly zero, so every number below is above the *sampling* floor by
construction.

## 1. The numbers

| pair | vendor | cond | side-flips | signed movement | concordance Δ |
|---|---|---|---:|---:|---:|
| qwen2.5-14B | Alibaba | A | 8/62 | −0.100 | −7.5% |
| | | B | 11/62 | −0.125 | −12.5% |
| | | C | 9/62 | −0.100 | −10.0% |
| | | D | 12/62 | −0.200 | −15.0% |
| phi4-14B | Microsoft | A | **0/62** | −0.175 | 0.0% |
| | | B | 2/62 | +0.200 | −2.5% |
| | | C | 2/62 | +0.200 | −2.5% |
| | | D | 2/62 | −0.100 | −2.5% |
| gemma-4-12B | Google | A | 8/62 | −0.050 | −5.0% |
| | | B | 6/62 | −0.450 | −7.5% |
| | | C | 6/62 | −0.275 | −7.5% |
| | | D | 2/62 | −0.225 | −5.0% |

Median side-flips per pair: qwen2.5 **10**, gemma-4 **6**, phi4 **2**.

## 2. What it looks like

Ablation moves political answers on two of three matched pairs, and where it moves them the
movement is **toward lower agreement with the research-supported answer** — 11 of 12 cells have
a negative concordance delta, qwen2.5 losing 7.5 to 15 points.

That is the opposite of this project's published position, which is that the refusal direction
and political stance are **dissociable** and that stance survives ablation with Δ ≤ 0.1.

## 3. Why the old claim and this one differ

Not a contradiction so much as a difference in what was measured:

| | May 2026 claim | this |
|---|---|---|
| arms | third-party builds, **unchecked for matching** | 3 pairs passing an explicit gate |
| decoding | temperature 0.7, no seed | temperature 0, seeded, within-arm variance zero |
| instrument | 30 homemade items, 1–5 rubric, LLM judge panel | 62 external forced-choice, no judge |
| stance scale | ~80% of responses at the midpoint | full 4-point range |
| verdict | Δ ≤ 0.1, "dissociable" | movement on 2 of 3 |

A compressed scale with 80% of mass at the midpoint cannot show a stance shift that a
forced-choice instrument can. The old null is at least partly a **measurement ceiling**, and
its own Evidence 1 was already withdrawn on 2026-08-28 for a related reason.

## 4. The control that is missing, and why nothing is claimed without it

**How many side-flips does requantisation alone produce?**

Nobody knows, including us. The arms here are matched on quantisation *level*, but there is no
measurement of how much a model's answers move under changes that are not the ablation. Eight
side-flips out of 62 has no reference point.

The right null is a **stock-versus-stock control at two quantisations** — same weights, same
instrument, same decoding, no ablation. If requantising alone moves 8 items, then 8 means
nothing and only qwen2.5's 10–12 survives. If it moves 0–1, every number above is real.

That control is being built now: pulling `gemma2:9b-instruct-q8_0` gives a stock-Q4 versus
stock-Q8 comparison of the same model, and as a bonus it creates a properly matched arm for
`wash-gemma2-ablit` (Q8_0), repairing one of the three pairs the gate rejected.

**Until that number exists, this page reports a measurement and no conclusion.**

## 5. Other limits

1. **n=1 per cell.** Legitimate at temperature 0 with a seed, where repeats are copies — but
   it means there is no between-arm interval, only a point.
2. **Three pairs, three families.** Meets the bar for a claim; does not meet it for a mechanism.
3. **Ablation may damage capability rather than constraint.** No coherence gate has been run on
   these arms. phi4's ablated build produced clean sheets throughout, qwen2.5's likewise, so
   gross damage is ruled out; subtle damage is not.
4. **The gate compares metadata, not weights.** A matched pair is eligible, not verified.
5. **This is the third-party-artifact caveat again**, one level down. The only version of this
   experiment that fully escapes it builds both arms from one base — which is why
   `BUILD-OUT-2026-08-30.md` §2 puts own-built ablation doses in the compute-limited tier.
