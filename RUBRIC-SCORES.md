# Pre-Registered Rubric Scoring of Judge Methods

Companion to [JUDGEMENT-TOOL-PLAN.md](JUDGEMENT-TOOL-PLAN.md). This file is committed BEFORE any of methods 2-8 are executed against the data. The git timestamp on this commit is the anti-HARKing proof that the anchor pick was made on method *design*, not on comparative results.

Score is 1-5 per dimension (5 = excellent, 1 = poor) on **method design alone**. Weighted total = sum(score × weight). Highest total = anchor method.

## Dimension weights (locked)

| Dim | Name | Weight |
|---|---|---|
| D1 | Circularity-reduction (escapes shared RLHF lean of judges) | 0.30 |
| D2 | Construct-validity preservation (still scores intended construct) | 0.25 |
| D3 | Reproducibility (deterministic, open, re-runnable elsewhere) | 0.20 |
| D4 | Interpretability (defensible to hostile reviewer in plain language) | 0.15 |
| D5 | Cost-economy (low burden — compute, money, recruitment) | 0.10 |

## Per-method scores

### Method 1 — ULTRAPLINIAN-4 median (baseline)
| Dim | Score | Rationale |
|---|---|---|
| D1 | 2 | Cross-vendor, but all 4 judges are RLHF-aligned. Median across shared prior = laundered consensus, not escape. |
| D2 | 4 | Well-tested rubric, this IS what the existing writeup measures. |
| D3 | 3 | API-based; vendors snapshot models without notice, temp=0 deterministic at point-in-time only. |
| D4 | 5 | Easiest to explain: "median across four cross-vendor judges." |
| D5 | 3 | Four API calls per record × 8,022 records. Already paid; not free. |
**Total: 0.30(2) + 0.25(4) + 0.20(3) + 0.15(5) + 0.10(3) = 3.25**

### Method 2 — Abliterated open-weight judge (Qwen + Gemma-2)
| Dim | Score | Rationale |
|---|---|---|
| D1 | 5 | Refusal-direction surgically removed from judge weights. This is the direct answer to "judges share RLHF lean." |
| D2 | 3 | Abliteration changes judge response distribution; rubric application must be re-validated for stability. Some loss possible. |
| D3 | 5 | Open weights, deterministic at temp=0, abliteration pipeline reproducible (OBLITERATUS toolchain documented). |
| D4 | 3 | Needs explanation: "we surgically removed the refusal direction from the judge." Non-obvious to lay audience. |
| D5 | 4 | Local inference (RTX 4090), no per-call API cost. One-time abliteration compute. |
**Total: 0.30(5) + 0.25(3) + 0.20(5) + 0.15(3) + 0.10(4) = 4.10**

### Method 3 — G0DM0D3-stripped judge
| Dim | Score | Rationale |
|---|---|---|
| D1 | 4 | Elicitation-layer alignment removal via STM hedge-strip + Parseltongue obfuscation. Lighter touch than weight surgery; meaningful effect on judge behavior. |
| D2 | 4 | Judge still produces structured rubric output; lower risk of breaking the scoring task than abliteration. |
| D3 | 4 | G0DM0D3 server pinned to commit; OpenRouter-compatible interface. |
| D4 | 3 | Needs explanation of STMs + Parseltongue. Defensible but layered. |
| D5 | 3 | API calls + server overhead. Moderate. |
**Total: 0.30(4) + 0.25(4) + 0.20(4) + 0.15(3) + 0.10(3) = 3.75**

### Method 4 — Adversarial-pair judge
| Dim | Score | Rationale |
|---|---|---|
| D1 | 4 | Opposing instructed pulls cancel shared prior at the mean — clever, but the cancellation assumes symmetric opposition (which may not hold). |
| D2 | 3 | Extreme instructions may push judges into uncalibrated regions; risk of pair-mean diverging from latent score. |
| D3 | 3 | Pair behavior less studied; reproducibility depends on prompt-sensitivity of the underlying judges. |
| D4 | 4 | Intuitive: two opposing critics, mean = arbitrated truth. |
| D5 | 2 | Doubles API calls per record — most expensive of the API-based methods. |
**Total: 0.30(4) + 0.25(3) + 0.20(3) + 0.15(4) + 0.10(2) = 3.35**

### Method 5 — Single-low-RLHF judge (Grok 4.3)
| Dim | Score | Rationale |
|---|---|---|
| D1 | 3 | One bias replaces four. Lower hedging, but not zero institutional lean. Pliny-cohort-friendly is not unbiased. |
| D2 | 3 | Grok may exaggerate institution-skeptical responses too readily; risk of over-scoring. |
| D3 | 2 | xAI API; Grok snapshots change between versions without clean version pinning. Worst reproducibility. |
| D4 | 4 | Easy to explain: "use the least-RLHF'd model as the judge." |
| D5 | 3 | Single-judge API cost; cheaper than panel, more expensive than local. |
**Total: 0.30(3) + 0.25(3) + 0.20(2) + 0.15(4) + 0.10(3) = 2.95**

### Method 6 — Reversed-rubric scoring
| Dim | Score | Rationale |
|---|---|---|
| D1 | 2 | Uses the SAME judges; tests anchor bias / rubric-anchor robustness, not RLHF-lean. |
| D2 | 4 | Direct probe of rubric construct validity. Strong test of an underrecognized failure mode. |
| D3 | 4 | Deterministic rubric flip; same prompts modulo label inversion. Highly reproducible. |
| D4 | 5 | Very intuitive: "flip the labels, see if judges flip." |
| D5 | 3 | Full re-run with same panel. Same cost regime as baseline. |
**Total: 0.30(2) + 0.25(4) + 0.20(4) + 0.15(5) + 0.10(3) = 3.45**

### Method 7 — Blind-condition judges
| Dim | Score | Rationale |
|---|---|---|
| D1 | 3 | Same judges; condition-aware confounding removed, but RLHF-lean of judges remains untouched. |
| D2 | 4 | Forces content-based scoring. Removes a real confound (judges-anticipating-condition). |
| D3 | 4 | Same panel; redaction pipeline deterministic. |
| D4 | 5 | Very intuitive: judge can't tell which condition produced the response. |
| D5 | 3 | Same API cost as baseline + redaction pipeline overhead. |
**Total: 0.30(3) + 0.25(4) + 0.20(4) + 0.15(5) + 0.10(3) = 3.75**

### Method 8 — External-benchmark anchoring
| Dim | Score | Rationale |
|---|---|---|
| D1 | 5 | Anchors LLM-judge outputs to a humans-labeled external dataset (Pew typology / Political Compass items). Fully escapes the LLM-judge circularity at the anchor step. |
| D2 | 4 | Maps the rubric to an established political-axis scale. Strong external construct anchor. |
| D3 | 4 | Pew + Political Compass items are public; mapping methodology can be documented in scripts. |
| D4 | 5 | Very intuitive: "the score correlates with this established public benchmark." |
| D5 | 2 | Acquiring + curating the benchmark mapping data is real effort. No external recruitment but more setup than the data-only methods. |
**Total: 0.30(5) + 0.25(4) + 0.20(4) + 0.15(5) + 0.10(2) = 4.25**

### Method 9 — Modern frontier panel (2026-generation cross-vendor median)

**Added 2026-09-05, scored BEFORE execution, on the weights locked above.** Nothing in the
dimension weights or in Methods 1–8 was touched: the anti-HARKing proof for those is their own
git timestamp, and re-scoring them now would destroy it. This is the same rubric applied to a
method proposed later, which is what a pre-registered rubric is *for* — it answers new proposals
without a new argument.

The proposal: replace or supplement ULTRAPLINIAN-4 with the current generation
(gpt-6-astra / claude-fable-5.1 / gemini-3.8-flash / qwen3.8-max or similar), median consensus,
same rubric.

| Dim | Score | Rationale |
|---|---|---|
| D1 | 1 | **Worse than the baseline's 2, not better.** All four are RLHF-aligned and *more recently and heavily* aligned — strictly more of the prior under test. Measured 2026-09-05: every US-vendor flagship refuses the balance instruction outright, so the proposed judges now exhibit the behaviour being measured. A judge that would decline the instrument is not a neutral rater of it. |
| D2 | 4 | Same rubric, same construct, and newer models apply a written rubric at least as reliably. No reason to expect construct loss. |
| D3 | 2 | **Worse than the baseline's 3.** Hosted, snapshotted without notice, and *newer* — less settled, more likely to be re-snapshotted or retired inside the study's life. The May panel has at least held still for a year. |
| D4 | 5 | The most defensible method in plain language of any here: "we used current models as the judges." Nothing to explain to a hostile reviewer. |
| D5 | 3 | Frontier pricing across ~1,700 records × 4 judges. More expensive than the baseline it would replace. |
**Total: 0.30(1) + 0.25(4) + 0.20(2) + 0.15(5) + 0.10(3) = 2.75**

**This ranks LAST of nine** — below single-Grok (2.95) and below the current baseline (3.25).
The rubric was not written to reach that conclusion; it was written in May, weighting
circularity-reduction at 0.30, and a modern frontier panel is the most circular option
available. Newness is not independence.

**Consequence, and it is the point of having done this in advance:** Method 9 is *not* an
anchor candidate and must never be presented as a second headline alongside the anchor. It is a
sensitivity arm. Its value is one specific question — **does judge generation move the score?**
— which is a floor this study has never measured while measuring floors for presentation order,
paraphrase, requantisation and run-to-run replication. Run it for that, report it in the
cross-method table with the other seven, and if it disagrees with the anchor, the disagreement
is a measurement of judge vintage rather than a rival answer.

## Ranking (pre-result)

| Rank | Method | Total |
|---|---|---|
| 1 | 8 — External-benchmark anchoring | **4.25** ← **ANCHOR** |
| 2 | 2 — Abliterated open-weight judge | 4.10 ← fallback if 8 infeasible |
| 3 | 3 — G0DM0D3-stripped | 3.75 |
| 3 | 7 — Blind-condition | 3.75 |
| 5 | 6 — Reversed-rubric | 3.45 |
| 6 | 4 — Adversarial-pair | 3.35 |
| 7 | 1 — ULTRAPLINIAN-4 median (current baseline) | 3.25 |
| 8 | 5 — Single-Grok | 2.95 |
| 9 | 9 — Modern frontier panel *(added 2026-09-05, scored pre-execution)* | **2.75** ← last |

## Pre-result observations

1. **The current baseline (ULTRAPLINIAN-4 median) ranks 7 of 8 by methodology rubric** — second only to single-Grok. The pre-registered rubric tells us, BEFORE we see comparative results, that the current scoring approach is not the methodologically strongest available. That is exactly the kind of finding pre-registration is for.

2. **External-benchmark anchoring (Method 8) is the anchor pick** if executable. If acquisition of suitable benchmark items proves infeasible, fall back to Method 2 (Abliterated open-weight judge, score 4.10).

3. **All 8 methods get reported** in the writeup's sensitivity-analysis section. The anchor pick determines headline numbers; the other 7 are the supplementary cross-method table that lets reviewers see the full picture.

## Anti-cherry-pick declaration

The rubric scores above were determined BEFORE running methods 2-8 against the data. The anchor method (#8) was selected mechanically from the rubric totals. If running the anchor method against the data yields a *weaker* bias finding than the current ULTRAPLINIAN baseline, that result is what the writeup publishes. Methodology integrity supersedes headline-result preservation.

This file's git commit is the timestamp proof.

---

## Status appended 2026-09-12 — nothing above this line has been edited

The scores, weights and rationales above are exactly as committed before methods 2–8 ran.
Editing them now would destroy the only thing this document is for, so this note is appended
rather than woven in.

**Where the eight methods stand.** Methods 2 and 4–7 were executed and are the cross-method
table in the writeup: five judging procedures agreeing with the panel 84–91% of the time on the
exact 1–5 score. Method 9 was added on 2026-09-05 and scored against these same locked weights
before it ran, which is what a pre-registered rubric is for.

**Method 8, the anchor pick at 4.25, was the one never executed** — the reason given here was
acquisition cost, and it stayed true for four months while every scoring-layer claim in the
study rested on the assumption it was meant to test. `judge_lean.py` can only measure each
judge against its own panel's median, so a lean shared by all four is invisible to it by
construction.

It has a harness as of 2026-09-12: **`scripts/judge_anchor.py`**. The anchor is a human scoring
the same responses on the same rubric, blind. That satisfies D1's operative requirement — no
language model in the anchor step — without acquiring and mapping a third-party benchmark,
which is the cost D5 scored a 2 for. `--sample` draws a seeded, blind, rubric-stratified sheet
(120 items, 24 at each of the five levels, 38 models) and seals the key; `--analyse` reports the
mean signed deviation of panel from human with a bootstrap interval.

**It is not done.** The sheet is drawn and unscored, `--analyse` exits 1 saying so, and this
note will keep saying so until it returns a number. Reporting Method 8 as executed because the
tooling exists would be the same move as scoring an unread paper's control as absent — which is
a thing this project has done once already and corrected in `PRIOR-WORK-CORRECTIONS.md`.

---

## Amendment, 2026-09-12b — why Method 8's pre-registered FORM is declined, and why its fallback is contested

The status note above records where the eight methods stand. Two things it does not say have
since been settled, and both change what "the anchor" means rather than when it will run.

### The anchor's stated obstacle was the wrong obstacle

D5 = 2 reads *"Acquiring + curating the benchmark mapping data is real effort."* That is a
logistical excuse, and it is not why Method 8 went unexecuted for four months.

The reason, stated by Ian on 2026-09-12: *"the political compass stuff is not great and doesn't
align with my values, so I excluded it because the politics are goofy. I had hoped that we could
learn something from it, but apparently not."*

That is a **principled exclusion and should be published as one.** D1's rationale names "Pew
typology / Political Compass items" as the external ground truth. This study administers the 62
Political Compass propositions as **stimuli** while explicitly rejecting the instrument's own
axes — `README.md` argues the horizontal axis is captured, self-report and undisclosed in
scoring. Anchoring our scale to those axes would import, at the single most authoritative point
in the design, the framework the study exists to criticise. An anchor that inherits the
instrument's politics is not an external anchor; it is the circularity moved one level out.

D5 = 2 stands as pre-registered. The rationale behind it was wrong, and saying so is cheaper
than pretending this file anticipated it. The human blind pass described above is not a
second-best substitute forced by cost — it is the form of Method 8 that survives the objection.

### The designated fallback is contested by this project's own result

Pre-result observation 2 names Method 2, the abliterated open-weight judge at 4.10, as the
fallback *"if acquisition of suitable benchmark items proves infeasible."* Acquisition is not
the blocker, so the clause has not fired — but it should be marked contested before it ever
does.

Method 2 scores **D1 = 5**, "the direct answer to *judges share RLHF lean*". §4.2 of the study,
across five open-weight families, is that abliteration rewrites ~70% of political wording and
moves stance by **≤0.2**: the refusal direction and the institutional lean are *dissociable*. If
cutting that direction does not move a subject's stance, it does not move a judge's either.
**The fallback removes a reflex the study itself proved is not the lean.**

Not a reason to discard Method 2 — it remains a real control on the refusal reflex. A reason to
stop citing it as the lean control, which D1 = 5 claims it is.

### What this bounds, until the sheet is scored

`judge_lean.py` measures a **relative** lean: 0.29 spread over 4,668 records, and an interaction
rather than a main effect, so it does **not** subtract out of the B−A deltas the way the first
version of that analysis claimed. Nothing in this study bounds a lean shared by all four judges.
The ranked anchor's pre-registered form is declined on principle, its designated fallback is
contested by our own weight-rung result, and the scoring layer is therefore bounded by a
relative measure. Every scoring-layer claim in the paper carries that limit, including the ones
we make about other people's work.

The part that matters most is bounded by re-scoring rather than by anchoring
(`judge_lean.py --per-finding`): the two large effects hold under every judge alone;
`deepseek/deepseek-v3.2` (+0.03 to +0.60) and `openai/gpt-4.1` (+0.21 to +0.73) do not, and are
reported with their ranges.
