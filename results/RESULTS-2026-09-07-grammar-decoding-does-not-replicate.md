# Whole-sheet constrained decoding does not replicate. Per-item may.

> **CORRECTED TWICE ON 2026-09-07, both times before publication. Both superseded readings are
> described below rather than deleted.**
>
> **First**, this file was titled *"elicitation format is a large effect"* and reported the
> prose-vs-grammar distance as the largest nuisance factor in the study — median 23 of 62
> against a deliberate manipulation of 3. Wrong: the grammar arm does not agree with *itself*
> (median 26), so its distance from the prose arm is one arm against noise, not a comparison
> between two instruments.
>
> **Second**, the replacement conclusion was written as being about constrained decoding in
> general. Also too broad: a per-item run returned a distribution indistinguishable from the
> prose arm (3% of answers in the "Strongly" band against prose's 5%, while both whole-sheet
> variants sit at 68–71%). The pathology belongs to **62 decisions in one array**, not to the
> grammar. Whether per-item *replicates* is still being measured.

**Measured** 2026-09-07, local, no API spend. 5 local panel models × conditions D and P × 5
swept seeds, at the wave protocol.
**Reproduce:** `python scripts/constrained_probe.py --collect --all-local --conditions D,P`
then `python scripts/floor_table.py --markdown`.

## Where this came from

Ian pointed at Ovando, *"Constitutive Authorization at the Decoding Boundary: Grammar-Constrained
Decoding as a Positive, Generation-Time Security Control for LLM Agents"*
([OSF s9gu6](https://osf.io/s9gu6/overview), June 2026). Its thesis is **constitutive versus
corrective enforcement**: a grammar-constrained decoder and a post-parse allowlist enforce the
same policy, but the grammar never produces the unauthorized artifact — *"emission = 0 by
construction"* — while the allowlist produces it and then rejects it.

That is this study's parsing problem in another domain, and it answers the objection that killed
logit scoring the same morning: a grammar keeps the **original wording**, so it should be the
same instrument with the parser removed rather than a second instrument needing its own floors.

## What works

Ollama accepts a JSON schema in `format`. An array of 62 enum values pins the whole sheet:

```json
{"type": "array", "minItems": 62, "maxItems": 62,
 "items": {"type": "string", "enum": ["Strongly Disagree", "Disagree", "Agree", "Strongly Agree"]}}
```

**50 runs across 5 models, 62 of 62 answers every time, zero problems.** The prompt comes from
`run_compass.build_prompt` — the same function the parser arm uses — so only the decoding
changes. Records are written in the `compass-run/1` schema with `decoding: "grammar"`, so the
existing floors machinery reads them without a parallel analysis.

Mechanically it removes every failure class the release document listed: the 28.2% invalid
condition-A runs, the budget exhaustion, the tokenizer garbage, the refusals-as-parse-failures.
They become ungenerable.

## What fails: it does not replicate

The across-arm distance is median **24**, p90 **34** of 62 — which would be seven times the
deliberate manipulation and by far the largest factor in the study. It is not a factor, because
of the column that matters:

| arm | its own run-to-run spread, median across the 10 cells |
|---|---:|
| prose (parser) | **3** |
| **grammar** | **26** |
| across arms | 24 |

Per cell:

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

**Two grammar runs of the same cell, same prompt, same temperature, differing seeds, disagree by
a median of 26 items of 62 — while two prose runs disagree by 3.** On every one of the ten
cells. An instrument whose repeat measurements differ that much is not measuring a position, so
its distance from the prose arm is one arm against noise, not a format effect.

**Misalignment was ruled out separately.** If the model emitted the 62 labels in some order
other than the item order, `zip` would assign every answer to the wrong item and produce exactly
this. Rotating the grammar sheet by ±1 and ±2 items does not reduce the distance (24 at k=0, 24
at k=+1, 28 at k=+2), so these are not correctly-ordered answers attached to the wrong items.

## Two candidate mechanisms, both tested, both refuted

**Hypothesis 1 — the missing anchor.** Free generation lets a model condition each answer on the
ones it has already written; a bare array of enums gives it no such anchor, so each position
looks like an independent draw. Testable by restoring the anchor and changing nothing else:
a schema of `{"reasoning": string, "answer": enum}` per item, so the model may write before
committing to a still-pinned answer. This is also what Ovando's framing actually supports — a
grammar constrains the *authorized surface*, not the whole utterance.

**Refuted.** `qwen2.5:14b` / D, five swept seeds, `reasoned` mode: own run-to-run spread median
**21**, against the bare sheet's **22** on the same cell. Restoring free text before each answer
changed nothing.

**Hypothesis 2 — renormalised sampling.** Constraining the sampler to four tokens renormalises
the distribution over them, so temperature 0.7 samples from something much flatter than free
generation does, inflating variance. Testable at temperature 0, where there is no sampling
variance at all.

**Refuted.** At temperature 0 the grammar arm still sits **15** side-flips (sheet) and **17**
(reasoned) from the prose modal over 38 valid condition-D runs. A deterministic decode that
lands 16 items away from the prose consensus is not a sampling artifact.

## The array is the culprit, not the grammar

One per-item run landed after the above was written — 62 of 62 answers, 1,366 seconds — and it
reframes everything. Distributions on `qwen2.5:14b` / condition D:

| arm | SD | D | A | SA | extreme share |
|---|---:|---:|---:|---:|---:|
| **prose (parser)**, modal of 38 valid runs | 3 | 32 | 27 | 0 | **5%** |
| grammar, whole sheet, temp 0 | 44 | 4 | 14 | 0 | **71%** |
| grammar, reasoned array, temp 0 | 39 | 5 | 15 | 3 | **68%** |
| **grammar, per item**, temp 0.7 | 2 | 35 | 25 | 0 | **3%** |

**Per-item tracks the prose arm; both whole-sheet variants do not.** Asking a model to emit a
62-element array pushes it to the extremes — 68–71% of answers in the "Strongly" band against
the prose arm's 5% — while asking it one proposition at a time under the same grammar returns
a distribution indistinguishable from prose at this resolution.

So the conclusion below is **narrower than it was written**: the pathology belongs to
*whole-sheet* constrained decoding, and specifically to 62 decisions in one array. Constrained
decoding as such is not implicated — the per-item arm is as constrained as the others.

**Two limits on that, stated plainly.** A shared distribution is not agreement: two sheets can
match on the histogram and differ on every item, and the item-level number is the one that
matters. It cannot be computed from this run, because the smoke test printed the distribution
and **discarded the sheet** — 23 minutes of GPU for a statistic that cannot answer the question.
`--replicate` now persists every sheet as it lands, incrementally, so an interrupted run keeps
what it finished. And the per-item replicate test has not returned yet; until it does, per-item
is a promising distribution and not a working arm.

## What the evidence supports about the whole-sheet arms

Both facts together — unstable under temperature, *and* systematically shifted when
deterministic — say the constraint is not a neutral change of clothes:

> **Grammar-constrained decoding changes both the central tendency and the reliability of the
> answer. It is not a formatting choice.**

The remaining explanation this data is consistent with, and does not establish, is that a JSON
array of enum labels is far off-distribution for a chat model answering a political
questionnaire. Off-distribution inputs give flatter, less reliable next-token distributions,
which would produce exactly this pair of symptoms — a shifted mode and a wide one. The
`reasoned` mode does not escape it because its reasoning field is *also* inside the JSON
grammar, and a constrained string is not free prose.

**That is a useful negative result for anyone treating constrained decoding as a free win for
evaluation harnesses.** It buys guaranteed-parseable output and it changes what you measured.

That is a real cost of the constitutive approach in this setting, and it is not the cost the
release document anticipated. `RELEASE-v2` expected the trade to be *"a second instrument needs
its own agreement check"*. The actual trade is worse: the grammar arm cannot support a
measurement at all on this instrument, because it fails the most basic test — run it twice, get
the same answer.

**It also does not touch the refusal problem**, for the reason already recorded: a model that
cannot emit prose cannot refuse, and refusal is §1's headline finding measured *from* the
invalid runs.

## What would make it work

The second bullet below was tried and refuted (above). What is left, stated so the next attempt
starts from here rather than from the top:

- **Constrain per item, not per sheet.** One call per proposition with a four-way enum gives the
  model the whole context for a single decision instead of 62 decisions in one array, and keeps
  the request shape much closer to ordinary chat. **Implemented** as
  `constrained_probe.py --mode peritem`, and **not yet run**, for a reason worth recording
  separately (below). Note it is not the same instrument either: the battery's T01 template
  opens *"Answer every one of the {n} propositions below"*, which a per-item prompt cannot use,
  so the single-item instruction is a deviation and cannot inherit the study's floors. What it
  can still answer is the question the other two arms failed — does a constrained arm replicate
  at all?

  **Why it is not run yet: on this machine ollama reloads the model on every request.**
  Measured 2026-09-07 across five consecutive calls, with and without the grammar, with
  `keep_alive` set: `load_duration` 17–21s against `eval_duration` **0.0–0.1s**. An explicit
  preload with `keep_alive: 15m` took 15.4s and left `ollama ps` empty. No `OLLAMA_*` variable
  is set at process, user or machine scope, and no stale process holds VRAM — the 10.8 GB
  reading that first looked like a leak was the model mid-load, and settles to 2.6 GB.

  So a per-item sheet is 62 model loads: ~22 min per run, ~108 min for a five-seed replicate
  test, of which under two seconds is inference. That is not a reason the design is wrong; it is
  a reason to fix model residency first, after which the same job is about two minutes.

  **This taxes every local arm, not just this one** — the ablation wave, the local-2026 order arm
  and the grammar arm each paid a full load per run, which is why 27B cells ran near 100s each.
  Worth fixing before the next local collection of any size.
- ~~Constrain a reasoned field plus the answer.~~ **Tried, refuted**: median 21 against the bare
  sheet's 22.
- **Run the replicate test FIRST, on one cell, before collecting anything.** Five runs. The
  previous attempt collected 50 runs across five models and computed a cross-arm distance before
  ever asking whether the arm agreed with itself, and nearly published the answer as the largest
  factor in the study. `constrained_probe.py --replicate` is that check.
- **If a variant does replicate, it still needs the agreement check**, and it still cannot
  measure refusal.

## Status

The floors table carries the row as **`elicitation format -- ARM UNSTABLE, NOT A FLOOR`**, with
the stability numbers in its note, so it cannot be quoted as a nuisance factor. Its columns hold
the real across-arm distribution rather than three different quantities — an earlier version put
`(prose_self, grammar_self, across)` into slots headed *med / p90 / max*, which is a worse defect
than the one it was disclosing.

Nothing published moved. The parser arm remains the instrument of record for every number in
this study, and its own stability — median 3 side-flips between repeat runs — is now measured
across five models rather than assumed.
