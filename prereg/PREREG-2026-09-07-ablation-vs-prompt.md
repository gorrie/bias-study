# Pre-registration: editing the weights against telling the model what to think

**Registered 2026-09-07, before the data is complete.** 5 of 45 cells collected at writing.
Registered because this study spends §2 convicting other papers of choices made after seeing
the numbers, and the same standard has to apply here.

---

## The question

Two ways to change what a language model says about politics:

- **Prompt-level** — instruct it. Demand balance, demand commitment, give it a content-free
  placebo. Already measured: on 2026 models this moves a median of **2 items of 62**, p90 **3**.
- **Weight-level** — remove the refusal direction from the weights (abliteration, per
  [Arditi et al. 2024](https://arxiv.org/abs/2406.11717)). **Never measured on a political
  instrument by anyone**, including us — the existing arm is n=1 per cell.

**Which intervention moves more?** Nobody has put them on one scale, on one model, in one
sitting. That is the whole design.

## Why it is interesting, stated plainly

The paper is titled *The Hedge Is the Bias*. That claim has never been tested where the hedge
actually lives. Abliteration separates two things that are always confounded in prompt work:

|  | what changes |
|---|---|
| **willingness** | does it answer at all — refusal rate on condition A |
| **position** | when it answers, what does it say — the 62 answers |

A prompt can only ever move both together. Cutting the refusal direction moves willingness
directly, so **position becomes observable independently of the willingness to state it.**

## The four outcomes, and what each would mean

Written before the data, so none of them can be chosen afterwards.

**1. Unlocks answers AND changes them.** The stock model held a position it was suppressing.
The title is literally true and demonstrated in the weights. This is the outcome everyone
assumes and nobody has shown.

**2. Unlocks answers, positions unchanged.** The constraint layer suppresses *expression only*.
**The hedge is NOT the bias** — it is a refusal to speak, sitting on top of a position that was
already there and already measurable. This would refute our own title, and it is the outcome
wave 0 quietly predicts: 2026 models are already near-immovable by prompt (`claude-opus-4.6`
is 0/0/0 with zero run-to-run spread).

**3. Breaks the model.** The Strongly-Agree-to-all-62 behaviour, or tokenizer garbage, or
inventing its own questions — all three observed once at n=1 and used to *exclude* pairs.
If it reproduces at n=5, the constraint layer is **not separable from instruction-following**,
which is the hard form of the ratchet argument and contradicts the "uncensored but otherwise
intact" claim on every abliterated model card.

**4. Ablations disagree with each other.** Then "abliteration changes political position" is a
claim about **the ablator**, not the model, and every result in outcomes 1–3 is unpublishable
without naming whose ablation produced it.

Outcome 4 is why the design carries multiple ablators, and it is checked FIRST.

## Design

**2 × 2, plus a willingness arm.**

- **Weight axis:** stock vs ablated, several independent ablations per base.
- **Prompt axis:** P (content-free placebo) vs D (commitment demanded).
- **Willingness arm:** condition A (balance demanded) — the one stock models refuse.

Wave protocol throughout: temperature 0.7, seed swept per run, **n = 5**, template T01,
matched quantisation Q4_K_M on both sides of every pair. Local GPU, no API spend.

### Bases and ablations

| base | stock | ablations | downloads |
|---|---|---|---|
| Qwen3.8-27B | `lmstudio-community/…-GGUF:Q4_K_M` | huihui-ai | 2,194,861 |
| | | 0bserverx (Heretic — different method) | 1,510,556 |
| | | OBLITERATUS | 995,160 |
| gemma-4-12B | `lmstudio-community/…-it-GGUF:Q4_K_M` | culturerevolt (Heretic) | 286,786 |
| | | OBLITERATUS | 26,675 |
| phi4-14B, qwen2.5-14B, gemma2-9B, llama3.1-8B | on disk | one each | 2024 generation |

The 2024-generation pairs collect **last** and no 2026 claim rests on them. They are here
because they are the arm's only existing pairs and because three were excluded on n=1 evidence
that needs re-testing.

## Analysis, specified now

1. **Ablator agreement first.** Side-flips between two ablations of the same base under the
   same condition. If that exceeds the stock-vs-ablated difference, stop — outcome 4, and every
   other number is a statement about the ablator.
2. **Willingness.** Refusal rate on A, stock vs each ablation. Paired per base.
3. **Position.** Side-flips stock-modal vs ablated-modal, on P and on D separately.
4. **The comparison.** Weight-level effect (stock→ablated, condition held) against prompt-level
   effect (P→D, build held), on the same base, same n, same units.
5. **Against the estimator.** Both against the modal's own sampling error, measured at
   **median 1, p90 3** (`data/modal-noise.json`). An effect that does not clear 3 is not an
   effect.

## Committed in advance

- **The unit is side-flips**, matching every other floor. Endpoint counts are reported but are
  not the headline.
- **Degenerate sheets stay classified, not deleted.** A build answering all 62 identically is
  outcome 3, not a missing cell.
- **Every build is named in every result**, with its download count, so no reader has to guess
  which abliteration produced a number.
- **If the ablations disagree, that is published as the finding** rather than resolved by
  picking the one whose behaviour is cleanest.
- **No re-quantising, no re-sampling, no dropping a build to make a comparison come out.** Three
  claims were withdrawn from this study on 2026-09-06 for versions of exactly that.

## What would make this uninteresting

Being honest about the failure mode: if all ablations break the models (outcome 3 everywhere),
the result is a negative about the tooling rather than about politics, and it belongs in one
paragraph, not a section. It is still worth knowing — the abliterated builds in this table have
**five million downloads between them** — but it would not be a finding about political
measurement.
