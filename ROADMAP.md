# Roadmap

> **HISTORICAL — written for the retired design.** The items below were planned against the
> free-text questionnaire retired on 2026-09-16, and the floors they quote are counts on that
> design, not on the present 32-item battery. What the current release measures, and what it
> does not, is stated in [`PAPER-below-the-floor.md`](PAPER-below-the-floor.md) §9. Kept because
> a plan published in advance is only worth anything if it stays published.

What is not in this repository yet, what it needs, and why it is not here. Published in advance
for the same reason the pre-registrations are: a plan stated before the data is a plan that
cannot be chosen after it.

Releases are dated, not numbered — see [VERSIONING.md](VERSIONING.md).

---

## Next release

**Doing the abliteration ourselves.** Every ablated build measured here is a third-party
artifact, and that is the weakness of the current weight-level arm: four independent
abliterations of one base model disagree about layer choice, refusal set, intervention strength
and quantisation, and none of them documents those choices completely. So "abliteration moves
political answers" is not yet separable from "this particular ablator's choices move them."
Computing the refusal direction ourselves ([Arditi et al.
2024](https://arxiv.org/abs/2406.11717)) removes the confound at the root.
**Needs:** ~54GB for a 27B at bf16. Activation capture cannot run at Q4.

**Intervention strength as a dose-response curve.** Abliteration is not binary — the method has
a scaling coefficient, and any single build is one point on a curve nobody has plotted for
political answers. The question worth answering is whether position moves *before* competence
breaks, or only along with it. **Needs:** the above.

**Scoring by logprob instead of parsing prose — PROTOTYPED 2026-09-07, AND IT FAILED ITS
AGREEMENT CHECK.** Full measurement in
[`results/RESULTS-2026-09-07-logit-scoring-fails-agreement.md`](results/RESULTS-2026-09-07-logit-scoring-fails-agreement.md);
the prototype is retired with the instrument it probed.

Three findings, because the entry below was written as though this were a small change:

- **The option labels are not separable at the first token.** `Strongly Agree` and `Strongly
  Disagree` both begin with the token `'Strong'` — three distinct tokens for four options, on
  both models tested. Scoring the four labels directly is not available; that is the tokenizer,
  not a tuning problem.
- **The letter form (`A = Strongly Disagree … D`) works and is a different instrument.** It
  scored 62 of 62 items — and matched the parsed instrument on only 24 of 62, with **20
  side-flips** against a run-to-run replicate floor of 5. It cannot inherit any of the floors
  below it.
- **The letter form is not invariant to its own legend.** Reversing which letter denotes which
  option — changing no proposition and no option, only their listed order — changed **48 of 62
  positions**.

**It is also not "free" except of API spend**: one call per item against one call per sheet.
What would make it work is listed in the results document, and starts with scoring a forced
continuation rather than a first token, so the original wording survives and the letter form is
never introduced.

*(The original entry, unedited:)* The instrument currently asks for 62 answers as
text and parses them, which costs: four models that produce no valid answer sheet under any
condition, one build exhausting its token budget on 12 of 15 runs, 28% of runs invalid under the
balance instruction, and three model pairs excluded for emitting tokenizer garbage. For an
open-weight model none of that is necessary — score the four option tokens directly and a model
that would have refused to write a sheet still has a position. It also yields a continuous
measure rather than a four-point one, which tightens every floor in the study.
**Needs:** nothing new. This is buildable on current hardware and is the next thing to be built.

**Grammar-constrained decoding instead of parsing prose — PROTOTYPED 2026-09-07, AND IT WORKS,
at the third attempt.** Full measurement in
[`results/RESULTS-2026-09-07-constrained-decoding-batch-size.md`](results/RESULTS-2026-09-07-constrained-decoding-batch-size.md);
the prototype is `scripts/constrained_probe.py`.

This is the other route to removing the parser, and unlike logit scoring it keeps the
instrument's **original wording** — a JSON schema pinning the four labels, so the model emits one
of the study's own options and nothing else is generable. Ollama's `format` takes the schema
directly: 50 runs across five models, 62 of 62 answers every time, zero parse problems. Every
failure class listed in the entry above becomes ungenerable rather than produced-and-rejected.
The framing is [Ovando 2026](https://osf.io/s9gu6/overview) on constitutive versus corrective
enforcement, one domain over.

**Three findings, in the order they were made, because the order is the point:**

- **As first built it does not agree with itself.** All 62 answers in one JSON array: two runs of
  the same cell, same prompt, same temperature, differ by a median of **26 items of 62**, while
  two prose runs differ by 3 — on every one of ten cells. The first write-up reported the
  prose-versus-grammar distance as the largest nuisance factor in the study before checking this.
  **Gate an arm's agreement with itself before reporting its distance from anything else.**
- **Two obvious mechanisms are both wrong.** Restoring a free-text field before each pinned
  answer (median 21 against the bare sheet's 22) does not help, and neither does removing
  sampling entirely — at temperature 0 the arm still sits 15 side-flips from the prose modal, so
  it is not a sampling artifact. Misalignment is separately ruled out: rotating the sheet by ±1
  or ±2 items does not reduce the distance.
- **The cause is how many answers are asked for per call, and it replicates once that is
  small.** Batch size is a continuous parameter, and both earlier arms fixed it at an extreme —
  62 answers in one array, or one per call. Sweeping it
  (`constrained_probe.py --batch-sweep`) shows the instability falling away with the chunk size,
  inside the study's own replicate floor well before the per-item end. **"Format X is broken",
  measured at one point of a continuous parameter, is a finding about that point.**

**What it cannot do, and this is not fixable.** A model that cannot emit prose cannot refuse —
and *"refusal is elicited, not intrinsic"* is measured **from** the invalid runs this arm makes
ungenerable. So it is a position instrument that runs alongside the parser arm, never instead of
it. It is also a second instruction — a chunk of eight propositions cannot use a template that
opens *"Answer every one of the 62 propositions below"* — so it earns its own floors rather than
inheriting these. The `elicitation format` row in the floors table stays disqualified until a
batched arm is collected at the wave protocol, since every run behind that row today is a
whole-sheet run.
**Needs:** nothing new. Buildable on current hardware, and cheaper than the per-item design by
the number of calls it saves.

**The quantisation ladder.** The requantisation floor rests on 13 pairs of Q4 against Q8, while
every other local measurement here is Q4 — and quantisation mismatch is already the declared
reason two ablation pairs were excluded. One base model run at bf16 / Q8 / Q6 / Q4 / Q3 would
say whether Q4 has been distorting the local arm all along. **Needs:** bf16 and Q8 resident.

**Open-weight models that do not fit in 24GB.** The large Qwen MoE, full-weight DeepSeek and
Kimi, and `gemma-4-31b-it` — which returns no valid answer sheet through a hosted endpoint, so a
local run is the only way to tell whether that is the model or the provider. Every hosted number
in this study is mediated by someone's serving stack, and this is the only way to check whether
the stack is part of what is being measured. **Needs:** 128GB+.

**Many-seed runs on the bimodal models.** Several models have a median run-to-run spread of 1–2
items and a maximum above 20. Those are two modes, not noise, and n=5 cannot characterise a
bimodal distribution — it reports whichever mode the sampler favoured, which is how one model
measured 2 on one collection and 18 on another. n=25–50 on those specific cells would settle it.
**Needs:** GPU hours for the open-weight ones; API spend for the rest.

## A later release

**Language and character set.** Models are reported to behave differently on the same task in
English versus Chinese character sets — possibly in willingness, possibly in competence,
possibly in position. If that holds on this instrument it is a large result, because it would
mean a political position is a property of the model *and the language*, and every measurement
in this literature is an English measurement presented as a fact about the model. Roughly half
the models measured here are Chinese-origin open weights, so the work is local rather than
hosted.

**Why it is not next:** a translation of the instrument is a *new instrument*, not the same one.
The instruction-paraphrase floor already shows that rewording alone moves a p90 of 6 items, so
without a back-translation control and native-language items, a language effect and a paraphrase
effect are inseparable. It needs its own design before it can produce one honest number.

## The scheduled one

**Wave 1.** The time-series panel is frozen and wave 0 is banked. A second wave needs roughly a
month of separation or it measures nuisance rather than change — the study's own floors say
presentation order moves 11 items and rerunning the same prompt moves 5. Due from October 2026.

---

## What will not be done

- **Compass coordinates.** Every claim here is computable from raw answers, and scoring a
  coordinate adds a dependency and an external scorer without answering a new question.
- **Re-truncating or re-pooling anything to make a comparison come out.** Three claims were
  withdrawn from this study for versions of that; see [CORRECTIONS.md](CORRECTIONS.md).
- **Claims about models whose own run-to-run spread exceeds their measured effect.** Those
  models are named rather than included.
