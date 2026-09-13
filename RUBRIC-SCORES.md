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

## Status, updated 2026-09-13 — the scores above are as committed before any method ran

**Where the nine methods stand.** Methods 2 and 4–7 executed; they are the cross-method table in
the writeup, five judging procedures agreeing with the panel 84–91% of the time on the exact 1–5
score. Method 9 was added 2026-09-05 and scored against these locked weights before it ran.
Methods 3 and 8 have not been executed.

**Method 8's harness exists and no human has scored it.** `scripts/judge_anchor.py` draws a
blind sheet — 120 items, question and response only, stratified 24 per panel score across 1–5
over 38 models — against a sealed key holding the panel score, the per-judge scores and the
rubric. `--check-rubric` is a release-gate item, so the human and the panel cannot drift onto
different rubrics. `--analyse` exits 1 until the sheet is filled. The gap is an afternoon, not a
tool.

**The anchor's pre-registered form is declined on principle, not on cost.** D5 = 2 blames
acquisition of the benchmark mapping. The real reason, Ian, 2026-09-12: *"the political compass
stuff is not great and doesn't align with my values, so I excluded it because the politics are
goofy."* D1's rationale names the Political Compass axes as the external ground truth. This study
administers those 62 propositions as **stimuli** while rejecting the instrument's own axes —
`README.md` argues its horizontal axis is captured, self-report and undisclosed in scoring — so
anchoring to them would import, at the most authoritative point in the design, the framework the
study exists to criticise. That is the circularity moved one level out, not escaped. The human
blind pass is the form of Method 8 that survives the objection.

**The designated fallback is contested by this project's own result.** Pre-result observation 2
names Method 2, the abliterated judge at 4.10, as the fallback if Method 8 proves infeasible.
Method 2 scores D1 = 5, *"the direct answer to judges share RLHF lean"* — but §4.2, across five
open-weight families, is that abliteration rewrites ~70% of political wording and moves stance by
**≤0.2**. Refusal direction and institutional lean are dissociable, so cutting that direction
does not move a judge's lean any more than it moves a subject's. The fallback removes a reflex
the study proved is not the lean. That is not a reason to discard Method 2, which remains a real
control on the refusal reflex; it is a reason to stop citing it as the lean control.

**So the scoring layer is bounded by a relative measure.** `judge_lean.py` reports a 0.2926
spread over 4,668 records, and that lean is an interaction rather than a main effect — it does
not subtract out of the B−A deltas. Nothing in this study bounds a lean shared by all four
judges. What is bounded is per-finding, by re-scoring rather than anchoring
(`judge_lean.py --per-finding`): the two large effects hold under every judge alone;
`deepseek/deepseek-v3.2` (+0.03 to +0.60) and `openai/gpt-4.1` (+0.21 to +0.73) do not and are
reported with their ranges.
