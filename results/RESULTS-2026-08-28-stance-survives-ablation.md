# The refusal direction is not where political stance lives

> ## SUPERSEDED — Evidence 1 was withdrawn outright on 2026-09-18. Do not cite it.
>
> **Banner added 2026-09-22, above the 2026-08-30 one because it supersedes it.** Everything
> below argues about whether "stance does not move" survived one particular objection. That
> question is moot: **the null itself is withdrawn**, `CORRECTIONS-2026-09-17-power.md`,
> ledgered as entry 28 of [`CORRECTIONS.md`](../CORRECTIONS.md).
>
> It was judged against a detection limit measured on a different instrument — the observation
> counted out of the retired 62-item questionnaire, the threshold out of the 32-item battery —
> and a side-flip count does not convert between banks. There is no battery-era ablation arm,
> so there is no floor for it to clear either. Entry 8 of the ledger had already withdrawn the
> *inversion* and left this null "undecided in both directions"; that disposition rested on the
> same invalid comparison and is withdrawn with it.
>
> The page is kept because the argument below is the record of how the claim was defended, and
> deleting it would leave the withdrawal unexplainable. Do not cite Evidence 1.

> ## THIS PAGE'S CORRECTION WAS ITSELF WRONG — 2026-08-30
>
> The correction below withdrew Evidence 1 because the between-arm Jaccard (0.276–0.339) sat
> inside a **temperature-0.7 within-model baseline** of 0.340.
>
> **That baseline does not apply.** A greedy temperature-0 control run already existed in this
> repo at `runs/2026-05-27-abliteration-controls/` — committed in May, and documented as
> `ADVERSARIAL-REVIEW.md` objection **A2b**, which raises this exact objection and marks it
> DONE. Recomputed 2026-08-30: stock-greedy vs abliterated-greedy gives mean Jaccard **0.306**,
> 0 of 20 cells near-identical. At temperature 0 a greedy model reproduces itself exactly, so
> the floor is ~1.0, not 0.340.
>
> **Evidence 1 is reinstated.** The ablation demonstrably rewrote the political responses, and
> the dissociation stands on both halves. Detail in `RESULTS-2026-08-30-withdrawal-was-wrong.md`.
>
> The withdrawal below was written without opening the document that contained its answer.

> ## CORRECTION 2026-08-28, hours after first publication — EVIDENCE 1 IS WITHDRAWN
>
> This page originally claimed that ablation "measurably changed the political outputs",
> citing word-set Jaccard of 0.276–0.339 between stock and ablated with zero near-identical
> cells. **That claim is not supported and is withdrawn.**
>
> The May abliteration run sampled at **temperature 0.7** (`run_local.py:77`,
> `do_sample=True, top_p=0.95`). Measured directly: two runs of the same model on the same
> prompts at that temperature produce mean word-set Jaccard **0.340** (range 0.303–0.392,
> n=10). The between-arm figure of 0.276–0.339 sits **inside that band.**
>
> The word-level difference between stock and ablated is indistinguishable from the
> difference between one model and itself. `abliteration_effect_check.py` cannot establish
> what it was written to establish at this sampling temperature, because its verdict logic
> has a branch for "near-identical" and a branch for "different" and none for "different, but
> no more different than noise."
>
> **What survives:** the stance scores are flat (Δ ≤ 0.1 across four families), and the
> XSTest category dissociation in Evidence 2 stands — that experiment ran at temperature 0
> with a measured within-arm noise floor of exactly zero.
>
> **What does not:** the claim that the ablation demonstrably reached the political items.
> Without it, a flat stance delta remains open to the original objection — the ablation may
> have missed the political subspace. The dissociation is **unproven**, not disproven.
>
> Baseline caveat: measured with `qwen2.5:14b` via ollama, not the run's exact
> `qwen2.5-7b-instruct` via transformers. The magnitudes are close enough to withdraw the
> claim; an exact-model replicate would settle it properly and has not been run.
>
> ### Second correction, same day: the first fix was also too crude
>
> The repair compared the between-arm mean against the baseline MEAN (0.340), which promoted
> llama-3.1-8b on a margin of **0.001** and mistral-7b on 0.007 — against a baseline with
> n=10 and a spread of 0.09. Not evidence either.
>
> The gate now requires the between-arm mean to fall below the baseline's **entire observed
> range** (min 0.303). Re-scored:
>
> | model | between-arm Jaccard | verdict |
> |---|---:|---|
> | deepseek-r1-distill-7b | 0.225 | dissociation candidate |
> | qwen2.5-7b | 0.276 | dissociation candidate |
> | mistral-7b | 0.333 | **no detectable effect** |
> | llama-3.1-8b | 0.339 | **no detectable effect** |
>
> **Two of four, not four of four.** For llama and mistral the ablation is indistinguishable
> from sampling noise, so their flat stance scores stay uninterpretable. For deepseek and
> qwen it cleared the noise floor, and their flat stance is the defensible dissociation.
>
> Found by asking what a hostile reviewer would attack, before anyone else did — but after
> the overstated version had already been committed and pushed, and after the first fix was
> itself too generous.


Two experiments, different data, same conclusion. One is new (XSTest on a Qwen3.8-27B pair);
the other ran the project's **existing** abliteration data through a check that was written
for it and had never been executed.

## The combined claim, as it stands after the correction above

Removing the refusal direction — the one-dimensional subspace Arditi et al. identified
(arXiv:2406.11717) — strips violence-harm refusal and leaves political stance, discrimination
refusal, and privacy refusal untouched.

"Uncensored" open-weight models are **violence-unconstrained, not politically
unconstrained**, and the artifacts do not say so.

## Evidence 1 — stance does not move, and it is not because the ablation missed

`scripts/abliteration_effect_check.py` existed in this repo, was written specifically to
answer the adversarial objection to the abliteration null, and had **never been run.** Its
own docstring states the killshot it was built for:

> *you verified refusal-rate dropped on your HARMFUL test set, but never showed the ablation
> changed anything on the political questions — so a flat stance score is uninterpretable
> (you may have ablated a direction orthogonal to the political subspace)*

Run against `runs/2026-05-27-abliteration`, on four model families with 20 paired
(question, condition) cells each:

| model | word-set Jaccard, stock vs ablated | near-identical cells (≥0.97) |
|---|---:|---:|
| deepseek-r1-distill-7b | — | 0 / 20 |
| llama-3.1-8b | 0.339 | 0 / 20 |
| mistral-7b | 0.333 | 0 / 20 |
| qwen2.5-7b | 0.276 | 0 / 20 |

~~Ablation rewrote roughly 70% of the words on the political questions, with zero
near-identical cells anywhere. The objection is answered: the ablation reached these
outputs.~~ **WITHDRAWN — see the correction at the top.** A within-arm baseline at the same
temperature gives Jaccard 0.340, so these figures show no effect distinguishable from
sampling noise. The objection is NOT answered.

And the stance scores, on the same cells:

| model | stock | ablated | Δ |
|---|---:|---:|---:|
| deepseek-r1-distill-7b | 2.850 | 2.941 | +0.091 |
| llama-3.1-8b | 3.000 | 3.000 | 0.000 |
| mistral-7b | 2.950 | 2.850 | −0.100 |
| qwen2.5-7b | 2.950 | 3.000 | +0.050 |

Every delta is within ±0.1 on a 1–5 scale, against a measured noise floor of roughly ±0.5.
The stance did not move, across four independent model families from four vendors. That
half stands. But the other half — that the wording changed *because of the ablation* — does
not, per the correction above. A flat stance delta beside an unmeasurable wording delta is
consistent with a real dissociation AND with an ablation that never reached these items.
Distinguishing those requires re-running at temperature 0, which is one command and has not
been done.

## Evidence 2 — the same split, at the category level

From `RESULTS-2026-08-28-refusal-ablation.md`, a separate pair (Qwen3.8-27B stock vs
OBLITERATED) on XSTest's 200 unsafe controls, with a measured noise floor of exactly zero:

| category | constrained refuses | ablated refuses | Δ |
|---|---:|---:|---:|
| contrast_homonyms | 100% | 48% | −52 |
| contrast_figurative_language | 100% | 48% | −52 |
| contrast_safe_targets | 96% | 52% | −44 |
| contrast_historical_events | 76% | 32% | −44 |
| contrast_safe_contexts | 96% | 64% | −32 |
| contrast_definitions | 92% | 64% | −28 |
| **contrast_privacy** | **72%** | **72%** | **0** |
| **contrast_discr** | **28%** | **28%** | **0** |

Violence-adjacent categories collapse. Privacy and discrimination do not move at all.

Two experiments, two probe sets, five model families, one pattern: the refusal direction
gates violence-harm refusal and nothing else that was measured.

## What this means, stated carefully

**For the open-weights argument.** Every result here required weights. Arditi's direction was
found by reading residual-stream activations across thirteen open models; the ablation
comparisons here need two runnable checkpoints of the same base. None of this is possible
through a sampling API, so a restriction on open-weight distribution removes the only method
that produced it.

**For claims about "uncensored" models.** Abliteration does not deliver an unconstrained
model. It removes one gate. Whatever political character the model has survives intact, which
means "we removed the safety training" and "we removed the bias" are different statements,
and conflating them is a measurable error rather than a matter of opinion.

**For the bias study.** A lean that survives ablation is not an artifact of the safety layer.
It sits in the base weights, which points at pretraining data and preference optimisation
(cf. Sharma et al., arXiv:2310.13548 — humans and reward models both prefer a convincing
wrong answer to a correct one a non-trivial share of the time), not at a policy filter bolted
on afterwards.

## Limits

1. **Four families at n=20 paired cells each**, and the stance scale is compressed — roughly
   80% of responses sit at the midpoint 3, which is a known property of this rubric. A flat
   delta on a compressed scale is weaker evidence than a flat delta on a spread one.
2. **The abliterated builds are third-party artifacts** and may differ from their bases in
   ways beyond the refusal direction.
3. **The question set is asymmetric.** 9 of 30 core items frame a right-coded critic of an
   institution; none frame a left-coded one. The between-arm comparison is unaffected — the
   same questions run on both arms, so the asymmetry cancels — but no absolute claim about
   the direction or size of any lean can rest on this set until the mirrored cells exist.
4. **XSTest measures refusal, not correctness.** Nothing here says a complying answer was any
   good.

## A disclosure gap found on the way

`gemma-2-9b` produced **0 rows** in both stock and abliterated raw files in the
2026-05-27 abliteration run. It failed at generation; the sweep script is failure-tolerant by
design and skipped it correctly.

The record count is honest — 160 actual, 160 claimed — so gemma was excluded from the totals
rather than counted. But the absence appears in **neither** `run-summary.json` nor
`ANALYSIS.md`. A reader of that analysis cannot tell that the model which produced the
study's original v1 headline contributed nothing to the abliteration run.

Failure-tolerance without failure-reporting is how a gap becomes invisible. The fix is one
line in the run summary naming any model with zero records.
