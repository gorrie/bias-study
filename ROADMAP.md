# Roadmap

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

**Scoring by logprob instead of parsing prose.** The instrument currently asks for 62 answers as
text and parses them, which costs: four models that produce no valid answer sheet under any
condition, one build exhausting its token budget on 12 of 15 runs, 28% of runs invalid under the
balance instruction, and three model pairs excluded for emitting tokenizer garbage. For an
open-weight model none of that is necessary — score the four option tokens directly and a model
that would have refused to write a sheet still has a position. It also yields a continuous
measure rather than a four-point one, which tightens every floor in the study.
**Needs:** nothing new. This is buildable on current hardware and is the next thing to be built.

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
