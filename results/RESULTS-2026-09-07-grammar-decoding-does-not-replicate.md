# Grammar-constrained decoding removes every parse failure and does not replicate

> **CORRECTED 2026-09-07, before publication, by the validity check this document originally
> did not run.** An earlier version of this file was titled *"elicitation format is a large
> effect"* and reported the prose-vs-grammar distance as the largest nuisance factor in the
> study — median 23 of 62 against a deliberate manipulation of 3. **That reading was wrong.**
> The grammar arm does not agree with *itself*, so its distance from the prose arm is not a
> comparison between two instruments. The superseded reading is described below rather than
> deleted.

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

## The likely mechanism, and why it matters for the proposal

Free generation lets a model condition each answer on the ones it has already written. A bare
array of 62 enum values gives it no such anchor, so each position looks close to an independent
draw from a wide posterior. **The prose arm's verbosity was doing work that looked like
overhead.**

That is a real cost of the constitutive approach in this setting, and it is not the cost the
release document anticipated. `RELEASE-v2` expected the trade to be *"a second instrument needs
its own agreement check"*. The actual trade is worse: the grammar arm cannot support a
measurement at all on this instrument, because it fails the most basic test — run it twice, get
the same answer.

**It also does not touch the refusal problem**, for the reason already recorded: a model that
cannot emit prose cannot refuse, and refusal is §1's headline finding measured *from* the
invalid runs.

## What would make it work

Stated so the next attempt starts here:

- **Constrain per item, not per sheet.** One call per proposition with a four-way enum gives the
  model the whole context for a single decision instead of 62 decisions in one array. It is 62×
  the calls, and it is the version that might replicate.
- **Or constrain a reasoned field plus the answer.** A schema of `{"reasoning": string, "answer":
  enum}` per item keeps the anchor free generation provides while still making an invalid answer
  ungenerable. This is the design Ovando's framing actually supports — the grammar constrains the
  *authorized surface*, not the whole utterance.
- **Re-run the replicate test first, before any comparison.** That is the test this arm failed,
  and it costs five runs of one cell.

## Status

The floors table carries the row as **`elicitation format -- ARM UNSTABLE, NOT A FLOOR`**, with
the stability numbers in its note, so it cannot be quoted as a nuisance factor. Its columns hold
the real across-arm distribution rather than three different quantities — an earlier version put
`(prose_self, grammar_self, across)` into slots headed *med / p90 / max*, which is a worse defect
than the one it was disclosing.

Nothing published moved. The parser arm remains the instrument of record for every number in
this study, and its own stability — median 3 side-flips between repeat runs — is now measured
across five models rather than assumed.
