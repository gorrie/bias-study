# Adversarial Review — Bias Study (institutional-skepticism / force-escalation ladder)

Self-imposed hostile peer review. Each objection is the *strongest* version a
skeptical expert would raise, not a strawman. Status is one of:
**FIXED** (addressed with data/code now) · **FIX QUEUED** (concrete action scheduled) ·
**ANSWERED** (rebuttal stands, no code change needed) · **OPEN** (acknowledged limitation).

Last updated: 2026-05-30. Companion to `WRITEUP-2026-05-26.md`; the writeup's caveats
sections (§3.1, §5.2, §5.5–5.7) are the public-facing subset of this.

---

## A. The weight rung (OBLITERATUS abliteration)

### A1 — "The abliteration null is underpowered; you can't tell 'no effect' from 'an effect you can't see.'"
n=10 questions × 1 sample per cell per model. With σ≈1 on a 1–5 scale, the per-model
delta CI is roughly ±0.6. A flat mean is not proof of zero movement.
**Status: DONE.** Executed — abliteration deltas carry bootstrap CIs (`ci_analysis.py`; §4.2 reports the per-family CIs include zero at n=10), framed as *no stance movement detectable at this n*, not *proven un-ablatable*; the dissociation is stated as the defensible version (text heavily perturbed, stance flat within CI). The plan, as carried out: (a) Report every abliteration delta with a bootstrap
CI via `ci_analysis.py`; state the finding as *"no movement detectable at this n (CI
±X)"*, never "proven un-ablatable." (b) Pool across vendor families (Qwen, Mistral,
Llama, +DeepSeek) to tighten the pooled estimate. (c) The claim is downgraded from
"dissociation proven" to "dissociation candidate: text heavily perturbed, stance not."

### A2 — "Your null is uninterpretable — you never showed the ablation touched the political items at all."
The refusal-rate verification ran on the *harmful-prompt* test set. A flat political
stance could mean the ablated direction was orthogonal to the political subspace — i.e.
you ablated the wrong thing and called the lean un-ablatable.
**Status: ANSWERED with data.** `abliteration_effect_check.py` pairs stock vs abliterated
by (question_id, condition) on the *political* items. Result across all three working
vendors: word-set Jaccard **0.28–0.34**, 0/20 near-identical cells, |word-count delta|
59–128. The ablation unmistakably rewrote the political responses. So a flat stance score
is a *real* dissociation, not a dead ablation. (Pending A2b below.)

### A2b — "Temp=0.7 inflates that text-difference; some of the 0.30 Jaccard is sampling noise, not ablation."
At temperature 0.7 the *same* model resampled would already score Jaccard < 1.0, so
stock-vs-abliterated divergence is confounded with stochastic decoding.
**Status: DONE.** Ran a temp=0 (greedy, deterministic) Qwen stock-vs-abliterated pass
(`data/2026-05-27-abliteration-controls/`). §4.2: stock 3.00/2.90 vs abliterated 3.00/3.00 —
stance flat — while the text rewrite persists (Jaccard 0.306 at temp 0, essentially identical to
the temp-0.7 value). So the divergence is the ablation, not stochastic decoding, and the flat
stance is real.

### A3 — "Open 7–9B instruct models sit at ~3.0 (balanced) already — floor/ceiling. There's nowhere to move."
If the stock model is already neutral, a null post-ablation is mechanical, not meaningful.
**Status: OPEN (honest limitation) + reframes into the asymmetry.** This is *why* the
weight rung can't be the whole story and the prompt rung carries the lean finding. It also
sharpens §B: the abliteration-auditable models are precisely the low-lean ones.

### A4 — "You used the *conservative* 'advanced' method (norm-preserving, reg=0.3). You just didn't push hard enough."
A gentle ablation that barely perturbs refusal obviously won't move a subtle prior.
**Status: DONE.** Ran the ablation-strength dose-response (`data/2026-05-27-abliteration-controls/`; §4.2): a stronger SVD ablation (8 refusal directions vs 4) does not move the stance toward skepticism (stays ~3.0-3.2), and pushing further degrades coherence (token loops) before the stance relocates — the functionality ceiling arrives first, so the null is not "didn't push hard enough." Original plan: dose-response on ablation *strength*: re-ablate Qwen at
`aggressive`/`nuclear`, re-score, show whether the political null holds at max strength —
with the coherence guard (a model degraded into noise must not be scored as "max
skepticism"). The ablation-strength ceiling is itself a reportable result (mirrors the
G0DM0D3 functionality-ceiling insight, applied to weights).

---

## B. The transparency-asymmetry framing

### B1 — "The asymmetry is confounded with capability/training, not 'transparency.'"
Open models are 7–9B and differently trained than GPT-5/Claude/Gemini. Any lean gap could
be scale or RLHF intensity, not openness. As stated, "open models lean less" is unfalsifiable.
**Status: ANSWERED via reframe.** The defensible claim is about *auditability*, not a
capability-matched lean comparison: weight-level verification (abliteration) is *only
possible* on open weights, full stop. Whether closed models lean more is a *separate*,
prompt-rung question with its own (weaker, honestly caveated) evidence. Rewrite the
asymmetry section to assert the auditability gap, not a causal "openness → less lean."

### B2 — "'The public can only audit the models that aren't the problem' assumes your conclusion; you retracted the GPT-5 result."
Loaded rhetoric that presumes closed = high-lean, while your headline closed-model finding
was withdrawn as "not distinguishable from zero."
**Status: FIXED (softened).** Drop "aren't the problem." State it structurally: the deepest
verification tool reaches only open weights; the closed frontier models are
un-abliteratable *by construction*, so claims about their internals are unfalsifiable from
the outside — which is the accountability gap, independent of which way they lean.

---

## C. The prompt rung (the 8,022-record core)

### C1 — "4/13 survive FDR. You're burying that 9/13 are noise."
**Status: ANSWERED (already honest).** The writeup §5.6 reports 4/13 explicitly. Action:
make it the *lead* of §3, not a caveat — "4 topics show a robust unmask effect" is the
honest headline, and the Gemma-2 +2.00 single-topic result is flagged as the strongest,
not the typical, case.

### C2 — "A→B removes a fairness instruction AND adds 'what do you think?'. You're measuring opinionatedness, not institutional skepticism." ← TOP KILLSHOT
Strip a hedging instruction and any model takes more positions on *any* axis. Nothing
ties the movement to *institutional* skepticism specifically.
**Status: DONE — killshot answered (see below).** The reversed-premise /
sycophancy control (WP3) is the only thing that discriminates "genuine institutional lean"
from "general agreeableness/opinionatedness": re-ask a subset with the institutional
premise *flipped*. If the unmask delta flips with the framing → agreeableness. If it holds
→ genuine lean. **It ran** (4-judge, `data/2026-05-27-reversed-premise/`; WRITEUP §5.4):
all five neutral-vs-reversed framing gaps stay under 0.40 (largest GPT-4.1 +0.35), and Opus
holds *more* skeptical under the deferential framing (−0.10). The unmask does not track framing
— a genuine institutional lean, not agreeableness. Killshot answered.

### C3 — "Your 4 LLM judges carry the same lean they're scoring — the instrument is contaminated."
If judges share the institutional prior, they'll systematically code skepticism as
deviation and deference as neutral.
**Status: FIXED via multi-method sweep (Phase 6 landed 2026-05-30).** The original mitigation
(cross-vendor median + per-judge spread) was the structural defense; the deeper test landed
with the JUDGEMENT-TOOL-PLAN Phase 3 sweep. The full dataset was re-scored under five
materially different judging procedures: ULTRAPLINIAN-4 (baseline), abliterated-gemma (M2,
refusal-direction surgically removed at the weight level), grok-solo (M4), adversarial-pair
(M5), reversed-rubric (M6), blind-condition (M7). Pooled across all 7 pre-registered runs,
every alternative method lands within **84-91% exact-match against ULTRAPLINIAN-4** (n
records per pair = 1,650 to 1,743) and within one ordinal step at **98.4-99.2%**. The
pre-registered robustness rule (median per-model contamination delta ≤ 0.10) is met:
median across 47 model-run pairs is **0.062**. The same answer comes out under five
different judging procedures, including one with the refusal direction surgically gone.
The bias is in the systems-under-test, not in the panel scoring them. WRITEUP §5.8.

---

## D. Scope / generalization

### D1 — "10 questions, one civil-liberties-flavored cluster. You can't generalize to 'institutional skepticism.'"
**Status: TESTED — objection largely conceded, and the claim is scoped accordingly.** We ran
an 8-question out-of-domain cluster (`questions.md` `T11–T18`, position `ood`: economic policy —
Fed independence, WTO, IMF, 2008 bailouts; foreign policy — intervention, NATO, sanctions, the
rules-based order) under the same A→B unmask and 4-judge panel, on the same ten cloud models
(`data/2026-05-27-ood/`). **The lean does not generalize.** Of the four FDR-significant
civil-liberties unmaskers, only **Opus 4.7 retains a significant out-of-domain unmask** (+0.50
[+0.12, +0.88]); Grok 4.3 (the +0.90 civil-liberties champion) goes flat (+0.00 [−0.62, +0.50]),
as do GPT-4.1 (−0.12) and Mistral (+0.00). Nine of ten models are not distinguishable from zero
out of domain; the us-closed class mean falls +0.572 → +0.250. **Conclusion:** the construct is
substantially civil-liberties-specific, exactly as the abstract/§5.4 scope note claims — the
reviewer is right that the broad label would overreach, and the study does not make the broad
claim. Opus is the lone cross-domain exception. Reported as an exploratory probe (n=8, one
framing/sample; wide CIs) under the CI-excludes-zero rule. Full treatment in WRITEUP §5.4.

### D2 — "Paraphrase sensitivity: you may be measuring memorized talking points keyed to exact wording."
**Status: DONE.** Rewrote each of the ten neutrals three independent ways (`questions.md`
`para1`/`para2`/`para3`), same A→B unmask + 4-judge panel, on the four FDR unmaskers plus two
flat controls (`data/2026-05-27-paraphrase/`). The large unmasks reproduce across all three
rewordings — Grok +0.90/+0.60/+0.70 (orig-neutral +0.80), Opus +0.70/+0.80/+0.90 (orig +0.60) —
and the flat controls (Mistral, Gemma-2-27b) stay flat. GPT-4.1's small neutral-subset effect
(+0.10) scatters near zero across paraphrases, consistent with a small effect, not a wording
artifact of a large one. Conclusion: the load-bearing unmask is a stable disposition, not
memorized phrasing keyed to exact wording. WRITEUP §5.4.

---

## E. Methodological / measurement objections (forward-looking, 2026-05-28 update)

Section added when the multi-method judgement tool work was scoped (see
`JUDGEMENT-TOOL-PLAN.md` + `RUBRIC-SCORES.md`). These are objections the
study had not yet faced from a real reviewer, written defensively in advance.

### E1 — "C3 cross-vendor median doesn't escape *shared* RLHF lean. Four-way consensus among aligned judges launders the bias it claims to measure."
The previous C3 mitigation ("median is robust to one outlier judge") doesn't help when all four judges share a direction. Asked another way: if the institutional-skepticism prior is the very thing four cross-vendor RLHF judges all carry, the median bakes it in.
**Status: FIXED (2026-05-30).** Multi-method sweep completed across all 7 pre-registered
runs. The five alternative methods (M2 abliterated-gemma, M4 grok-solo, M5 adversarial-pair,
M6 reversed-rubric, M7 blind-condition) agree with the ULTRAPLINIAN-4 baseline at 84-91%
exact-match and 98.4-99.2% within-one ordinal step. Median per-model contamination delta
0.062 across 47 model-runs — inside the pre-registered 0.10 robust band. The early
60-record g0dm0d3 pilot's apparent grok-solo divergence did not survive in the full sample:
the pooled grok-solo signal is 87.7% exact-match with baseline. The four-way RLHF consensus
hypothesis does not explain the data; the bias lives in the systems-under-test. WRITEUP §5.8.

### E2 — "Your judge-method selection is itself cherry-picked. You ran 4 methods and reported the one whose results you liked."
**Status: FIXED via pre-registration.** Method-quality rubric and per-method scoring committed to git BEFORE the sweep ran (`RUBRIC-SCORES.md`, commit `e195493` timestamped 2026-05-28). Anchor method = highest weighted-total on the pre-registered rubric, selected mechanically. All methods reported in the supplementary sensitivity table regardless of headline-friendliness. Pre-result observation, also pre-registered: the current ULTRAPLINIAN-4 baseline ranks 7/8 by methodology rubric — that's exactly the kind of finding pre-registration is built for. If the anchor method yields a *weaker* bias signal than the baseline, that result publishes — methodology integrity > headline preservation.

### E3 — "Rubric anchor-bias: judges may be scoring by label position (1=deference, 5=skeptical) instead of by content. The score is an artifact of where the labels sit on the scale."
A common failure mode in Likert-style scoring.
**Status: FIXED (2026-05-30).** Method 6 (`reversed-rubric`) completed across all 7
pre-registered runs. Pooled exact-match against ULTRAPLINIAN-4: **90.7% (1,743 paired
records, within-one 99.1%)** — the highest exact-match rate of any alternative method.
If judges were scoring by label anchor rather than by content, label-inversion should have
produced systematic divergence; instead it produced the strongest agreement. Content-bias,
not anchor-bias, drives the score. WRITEUP §5.8.

### E4 — "Temporal drift: your vendor models were snapshotted on different days; comparing them at all is unsound."
Vendor models update silently. Apparent inter-vendor differences could be timing artifacts.
**Status: ANSWERED via bound.** All runs span 2026-05-25 through 2026-05-28 (4-day window). Vendor snapshot changes within that window are individually small (typically < 0.1 mean delta in our own variance run, `2026-05-26-variance/`). The largest reported main-study deltas (+0.60 to +0.90) are an order of magnitude larger than plausible snapshot drift over 4 days. Honest residual: runs are not strictly contemporaneous; the snapshot-drift bound is the only defense. Listed as an explicit limitation in the writeup.

### E5 — "Judges share training data with systems-under-test. The four ULTRAPLINIAN judges likely trained on overlapping RLHF corpora to the systems they score — bias of the testbed equals bias of the test."
Stronger version of C3 / E1: it's not just *aligned* judges, it's possibly identically-aligned judges.
**Status: FIXED (2026-05-30).** Method 2 (abliterated open-weight judge) completed.
The Gemma-2-9B-IT judge had its refusal direction surgically removed via OBLITERATUS
and was MLX-converted for in-process Apple-Silicon inference; it bypasses the
training-data confound mechanically. Pooled across all 7 pre-registered runs, abliterated
Gemma-2 lands at **86.8% exact-match (1,717 paired records, within-one 99.2%)** against
the four-judge ULTRAPLINIAN-4 baseline — between blind-condition and grok-solo. If the
ULTRAPLINIAN panel were laundering shared RLHF training data, the abliterated judge —
the one judge known to NOT carry the RLHF refusal direction — would systematically
disagree. It does not. The bias is upstream of any RLHF judging artifact. WRITEUP §5.8.

### E6 — "Without paid expert calibration, the study is unreproducible by outside groups."
**Status: OPEN with mitigation.** Paid-expert calibration was explicitly dropped (`JUDGEMENT-TOOL-PLAN.md`: LLM-driven methodology is the constraint we're solving within, not bypassing). Mitigation: every script, every prompt template, every scored record, and the pre-registered methodology rubric is published at `github.com/gorrie/bias-study`. Another team can re-run the entire pipeline with the same code and recover the same numbers; the cross-method agreement matrix itself becomes the reproducibility check (a re-runner who gets different numbers can compare against ours and surface where the divergence sits). Honest residual: this is reproducibility-of-the-method, not external construct validation. Listed as a future-work item.

---

## Reprioritization forced by this review — status

All five original construct/rigor priorities (sections A–D) are resolved; the multi-method judgement-tool work (section E) is mid-execution.

1. **C2 reversed-premise control** — DONE (sycophancy control; §5.4).
2. **A2b temp=0 isolation** + **A4 ablation-strength dose-response** — DONE (§4.2; the abliteration finding is defensible, not a candidate).
3. **A1 CIs on every delta** — DONE (`ci_analysis.py`; nulls reported as power-bounded, never proof of zero).
4. **B1/B2 asymmetry rewrite** — DONE (auditability claim, not a causal lean claim).
5. Gemma-2 abliteration retry for a 4th+ vendor family — DONE (Apple-Silicon BLAS cleared the SVD bug; 5-family weight rung now in writeup).
6. **D1** (out-of-domain generalization) — TESTED + tightened (within-leg FDR shows 0/10 models survive q=0.05 on OOD; Claude raw p=0.0088 drops at the BH threshold; writeup needs to relabel Opus as "lone CI-excluding-zero exception, not FDR-significant").
7. **D2** (paraphrase robustness) — TESTED + tightened (within-leg FDR shows Claude + Grok are 3/3 paraphrase-survivors, deepseek/gpt-4.1/mistral/gemma are 0/3 each — the "effect holds where it is large" framing is now a measured claim, not qualitative).
8. **E1–E6** (forward-looking methodology objections) — Phase 6 of JUDGEMENT-TOOL-PLAN
   landed 2026-05-30. E1, E3, E5 all FIXED via the multi-method sweep (5 alternative
   methods × 7 pre-registered runs; 84-91% exact-match with baseline; median
   contamination delta 0.062). E2 and E4 were FIXED earlier (pre-registration +
   temporal-drift bound). E6 (no paid expert calibration) remains documented as open
   with mitigation by design — LLM-driven methodology is the constraint solved within,
   not bypassed.
