# Adversarial Review — Bias Study (institutional-skepticism / force-escalation ladder)

Self-imposed hostile peer review. Each objection is the *strongest* version a
skeptical expert would raise, not a strawman. Status is one of:
**FIXED** (addressed with data/code now) · **FIX QUEUED** (concrete action scheduled) ·
**ANSWERED** (rebuttal stands, no code change needed) · **OPEN** (acknowledged limitation).

Last updated: 2026-05-27. Companion to `WRITEUP-2026-05-26.md`; the writeup's caveats
sections (§3.1, §5.2, §5.5–5.7) are the public-facing subset of this.

---

## A. The weight rung (OBLITERATUS abliteration)

### A1 — "The abliteration null is underpowered; you can't tell 'no effect' from 'an effect you can't see.'"
n=10 questions × 1 sample per cell per model. With σ≈1 on a 1–5 scale, the per-model
delta CI is roughly ±0.6. A flat mean is not proof of zero movement.
**Status: FIX QUEUED + reframe.** (a) Report every abliteration delta with a bootstrap
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
**Status: FIX QUEUED.** Run a temp=0 (greedy, deterministic) stock-vs-abliterated pass on
one model (Qwen): any text difference is then *purely* the ablation. Also add a
stock-vs-stock resample baseline to quantify the sampling floor. Report the ablation
effect net of that floor.

### A3 — "Open 7–9B instruct models sit at ~3.0 (balanced) already — floor/ceiling. There's nowhere to move."
If the stock model is already neutral, a null post-ablation is mechanical, not meaningful.
**Status: OPEN (honest limitation) + reframes into the asymmetry.** This is *why* the
weight rung can't be the whole story and the prompt rung carries the lean finding. It also
sharpens §B: the abliteration-auditable models are precisely the low-lean ones.

### A4 — "You used the *conservative* 'advanced' method (norm-preserving, reg=0.3). You just didn't push hard enough."
A gentle ablation that barely perturbs refusal obviously won't move a subtle prior.
**Status: FIX QUEUED.** Dose-response on ablation *strength*: re-ablate Qwen at
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
**Status: FIX QUEUED — elevated from optional to REQUIRED.** The reversed-premise /
sycophancy control (WP3) is the only thing that discriminates "genuine institutional lean"
from "general agreeableness/opinionatedness": re-ask a subset with the institutional
premise *flipped*. If the unmask delta flips with the framing → agreeableness. If it holds
→ genuine lean. Until this runs, the prompt-rung claim is not defensible. This now gates
the writeup's main claim.

### C3 — "Your 4 LLM judges carry the same lean they're scoring — the instrument is contaminated."
If judges share the institutional prior, they'll systematically code skepticism as
deviation and deference as neutral.
**Status: ANSWERED + calibration note.** Mitigation already in design: the panel is
*cross-vendor* (Anthropic/OpenAI/Google/DeepSeek) and canonical score is the **median**,
robust to one outlier judge. For all four to share a single lean, that lean would have to
be consistent across four independent labs' RLHF — which is itself the study's thesis, not
a confound that explains it away. Honest residual: a human-labeled calibration subset would
close this; per standing constraint we do *not* hand-score, so we report per-judge spread
+ median robustness and name the residual openly. Add a judge-disagreement-by-topic table.

---

## D. Scope / generalization

### D1 — "10 questions, one civil-liberties-flavored cluster. You can't generalize to 'institutional skepticism.'"
**Status: FIX QUEUED.** WP3 out-of-domain cluster (economic / foreign-policy) tests whether
the axis generalizes. Report per-cluster deltas; if the effect is civil-liberties-only,
say so and narrow the claim.

### D2 — "Paraphrase sensitivity: you may be measuring memorized talking points keyed to exact wording."
**Status: FIX QUEUED.** WP3 paraphrase-robustness: 3 paraphrases of the 10 neutrals; report
delta stability.

---

## Reprioritization forced by this review
1. **C2 reversed-premise control** — was "optional rigor," now gates the main claim. Do first.
2. **A2b temp=0 isolation** + **A4 ablation-strength dose-response** — convert the abliteration
   finding from "candidate" to defensible.
3. **A1 CIs on every delta** — reframe all nulls as power-bounded, never as proof of zero.
4. **B1/B2 asymmetry rewrite** — auditability claim, not causal lean claim.
5. Gemma-2 abliteration retry (architecture/OOM) for a 4th vendor family — breadth, lower priority than 1–4.
