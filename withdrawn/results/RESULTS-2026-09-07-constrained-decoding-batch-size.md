# Constrained decoding replicates. Asking for 62 answers in one array does not.

> **CORRECTED THREE TIMES ON 2026-09-07, every time before publication. All three superseded
> readings are kept below rather than deleted, because the sequence is the finding.**
>
> **First**, this was titled *"elicitation format is a large effect"* and reported the
> prose-vs-grammar distance as the largest nuisance factor in the study — median 23 of 62
> against a deliberate manipulation of 3. Wrong: the grammar arm does not agree with *itself*
> (median 26), so its distance from the prose arm was one arm against noise.
>
> **Second**, the replacement conclusion was written as being about constrained decoding in
> general — *"grammar decoding does not replicate"*, which was this file's name. Too broad: a
> per-item run returned a distribution indistinguishable from the prose arm, so the pathology
> looked like the array rather than the grammar.
>
> **Third — this version.** "The array" was still a guess, held on the strength of two points
> at the extreme ends of a continuous parameter. Sweeping items-per-call locates it: the arm
> **replicates** at small batch sizes and fails at large ones, and part of even the whole-sheet
> failure turns out to be the *prompt* rather than the array. Constrained decoding is usable on
> this instrument. It was being used wrong.

**Measured** 2026-09-07, local, no API spend.
**Reproduce:**

```bash
python scripts/constrained_probe.py --replicate --model qwen2.5:14b --condition D \
       --mode batched --batch 8 --runs 3 --temperature 0.7
python scripts/constrained_probe.py --batch-sweep 62,31,16,8,4,2 --model qwen2.5:14b \
       --condition D --runs 3 --temperature 0.7
```

## Where this came from

Ian pointed at Ovando, *"Constitutive Authorization at the Decoding Boundary: Grammar-Constrained
Decoding as a Positive, Generation-Time Security Control for LLM Agents"*
([OSF s9gu6](https://osf.io/s9gu6/overview), June 2026). Its thesis is **constitutive versus
corrective enforcement**: a grammar-constrained decoder and a post-parse allowlist enforce the
same policy, but the grammar never produces the unauthorized artifact — *"emission = 0 by
construction"* — while the allowlist produces it and then rejects it.

That is this study's parsing problem in another domain. `run_battery.py` is the corrective arm:
ask for 62 answers as prose, parse, then classify what came back as refusal / budget-exhausted /
tokenizer garbage / truncated. **28.2% of condition-A runs are invalid**, four models produce no
valid sheet under any condition, one build exhausted its budget on 12 of 15 runs, and three
ablation pairs are excluded for emitting tokenizer garbage. Every one of those is an artifact
produced and then rejected.

It also answered the objection that killed logit scoring the same morning: a grammar keeps the
**original wording**, so it is the same instrument with the parser removed rather than a second
instrument needing its own floors.

## What works mechanically

Ollama accepts a JSON schema in `format`. An array of enum values pins the answers:

```json
{"type": "array", "minItems": 62, "maxItems": 62,
 "items": {"type": "string", "enum": ["Strongly Disagree", "Disagree", "Agree", "Strongly Agree"]}}
```

**50 runs across 5 models, 62 of 62 answers every time, zero problems.** Every failure class the
release document lists becomes ungenerable. Records are written in the `compass-run/1` schema
with `decoding: "grammar"`, so the existing floors machinery reads them without a parallel
analysis.

That was never the question. The question is whether what comes back is a measurement.

## The gate that should have run first

An arm has to agree with itself before its distance from another arm means anything. The
whole-sheet arm does not:

| arm | its own run-to-run spread, median across the 10 collected cells |
|---|---:|
| prose (parser) | **3** |
| grammar, whole sheet via `build_prompt` | **26** |
| across arms | 24 |

**Two grammar runs of the same cell — same prompt, same temperature, differing seeds — disagree
by a median of 26 items of 62, while two prose runs disagree by 3.** On every one of the ten
cells. So the across-arm 24 was never a format effect, and the version of this file that
published it as the study's largest factor was measuring one arm against its own noise.

Per cell, for the record:

| model | cond | grammar self (med / max) | prose self (med / max) | across |
|---|---|---:|---:|---:|
| gemma2 | D | 23 / 30 | 5 / 8 | 24 |
| gemma2 | P | 25 / 35 | 1 / 2 | 16 |
| llama3.1:8b | D | 26 / 33 | 8 / 10 | 32 |
| llama3.1:8b | P | 30 / 43 | 6 / 9 | 32 |
| mistral | D | 30 / 38 | 5 / 7 | 39 |
| mistral | P | 32 / 41 | 3 / 6 | 34 |
| phi4 | D | 17 / 21 | 2 / 2 | 13 |
| phi4 | P | 32 / 42 | 1 / 2 | 17 |
| qwen2.5:14b | D | 24 / 26 | 3 / 5 | 20 |
| qwen2.5:14b | P | 23 / 26 | 1 / 2 | 22 |

**Misalignment was ruled out separately.** If the model emitted the 62 labels in an order other
than the item order, `zip` would attach every answer to the wrong item and produce exactly this.
Rotating the sheet by ±1 and ±2 items does not reduce the distance (24 at k=0, 24 at k=+1, 28 at
k=+2), so these are not correctly-ordered answers on the wrong items.

## Two mechanisms proposed, tested, and refuted

**Hypothesis 1 — the missing anchor.** Free generation lets a model condition each answer on the
ones it has written; a bare array of enums gives it no such anchor, so each position looks like an
independent draw. Tested by restoring the anchor and changing nothing else: a schema of
`{"reasoning": string, "answer": enum}` per item. This is also what Ovando's framing actually
supports — a grammar constrains the *authorized surface*, not the whole utterance.

**Refuted.** `qwen2.5:14b` / D, five swept seeds, `reasoned` mode: self-spread median **21**
against the bare sheet's **22** on the same cell.

**Hypothesis 2 — renormalised sampling.** Constraining the sampler to four tokens renormalises
the distribution over them, so temperature 0.7 samples from something much flatter than free
generation does. Tested at temperature 0, where there is no sampling variance at all.

**Refuted.** At temperature 0 the grammar arm still sits **15** side-flips (sheet) and **17**
(reasoned) from the prose modal over 38 valid condition-D runs. A deterministic decode landing 16
items from the prose consensus is not a sampling artifact.

## Items per call is the dial, and nobody had turned it

Both refuted mechanisms are about *how* the answer is generated. The thing neither touched is
**how many decisions are packed into one completion** — and both constrained arms built before
this one fixed that at an extreme. The whole-sheet arm asks for 62 answers in one array. The
per-item arm asks for one. Each was then argued about as though its result were a property of
constrained decoding.

Batch size is a continuous parameter. Going straight from 62 to 1 answered *which end is broken*
without ever asking *where* it breaks.

<!-- SWEEP TABLE INSERTED HERE -->

## Why this was the cheap experiment as well as the right one

Because on this machine **a call costs about 21 seconds almost regardless of what is in it.**

Measured 2026-09-07 across five consecutive requests, with and without a grammar, with
`keep_alive` set every way the API offers: `load_duration` **17–21s** against `eval_duration`
**0.0–0.1s**. Ollama 0.33.1 here reloads the model on every single request. An explicit preload
with `keep_alive: 15m` took 15.4s and left `ollama ps` **empty**; `keep_alive: -1` behaves the
same. No `OLLAMA_*` variable is set at process, user or machine scope, and no stale process holds
VRAM — the 10.8 GB reading that first looked like a leak was the model mid-load, settling to
2.6 GB.

So wall-clock is set by request count, not tokens:

| arm | calls per run | wall-clock per run |
|---|---:|---:|
| prose sheet, whole battery in one call | 1 | ~21s |
| grammar, batched at 8 | 8 | ~3 min |
| grammar, one call per proposition | 62 | **~23 min** |

That is why the per-item arm looked unaffordable: 108 minutes for a five-seed replicate test, of
which **under two seconds is inference**. Per-item inference is not expensive. Per-item pays the
residency bug 62 times.

**This taxes every local arm.** The ablation wave, the local-2026 order arm and the grammar arm
each paid a full load per run, which is why 27B cells clocked near 100s each. Fixing it needs a
host-side restart with `OLLAMA_KEEP_ALIVE` set — not reachable from the API, so it is the
operator's call. The finding is recorded in `skills/barometer-wave/SKILL.md` so the next local
collection budgets in calls rather than discovering this again.

The reason it is recorded as a *design* constraint and not just an annoyance: it is what makes
batch size the only lever. Under working residency, per-item and whole-sheet cost roughly the
same and the choice is free. Under this bug, the design that happens to be correct is also the
one that is 8× cheaper than the obvious clean alternative — which is luck, and would not have
been discovered by optimising for either goal alone.

## What this does not fix, and cannot

**A model that cannot emit prose cannot refuse.** Refusal is §1's headline finding — *"refusal is
elicited, not intrinsic"*, 14 of 42 models declining all 62 propositions with no directive and
every one of them stopping when given one — and it is measured **from the invalid runs**.
Constrained decoding erases the evidence for it by construction.

So this is not a drop-in upgrade to the collector. It is a **position instrument**, and the two
arms have to run separately: the parser arm for willingness, a batched grammar arm for position.

**And it does not inherit the study's floors.** A chunk of 8 propositions cannot use the
battery's T01 template, which opens *"Answer every one of the 62 propositions below"* and numbers
all 62, so the batched arm writes a chunk-shaped instruction of its own. That makes it a
different instruction from the instrument of record — exactly as the per-item arm is — and any
floor it needs, it has to earn.

## Status

Nothing published moved. The parser arm remains the instrument of record for every number in this
study, and its own stability — median 3 side-flips between repeat runs — is now measured across
five models rather than assumed.

The floors table still carries the row as **`elicitation format — ARM UNSTABLE, NOT A FLOOR`**,
correctly: every run behind that row is a whole-sheet run. Its note now says *why* the arm was
unstable and points here, so a reader does not carry away "constrained decoding does not work
here" when the measured claim is narrower.

**What would make the row a floor:** a batched arm collected at the wave protocol — five models,
conditions D and P, five swept seeds — at a batch size the sweep clears, plus the agreement check
against the parser arm on the same cells. That is a real arm now rather than a rejected
prototype, which is why `constrained_probe.py` came out of `check_skill_docs.py`'s
`NOT_A_PROCEDURE` list and into the skill's Files section.
