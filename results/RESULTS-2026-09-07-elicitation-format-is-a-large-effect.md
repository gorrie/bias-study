# Constrained decoding works, disagrees with the parser by 17 items, and that is the finding

**Measured** 2026-09-07, local, no API spend.
**Reproduce:** `python scripts/constrained_probe.py --model qwen2.5:14b --condition D --runs 5 --temperature 0.7 --agreement`

## Where this came from

Ian pointed at Ovando, *"Constitutive Authorization at the Decoding Boundary: Grammar-Constrained
Decoding as a Positive, Generation-Time Security Control for LLM Agents"* ([OSF s9gu6](https://osf.io/s9gu6/overview),
June 2026). Its thesis is **constitutive versus corrective enforcement**: a grammar-constrained
decoder and a post-parse allowlist enforce the same policy, but the grammar never produces the
unauthorized artifact — *"emission = 0 by construction"* — while the allowlist produces it and
then rejects it.

That is this study's parsing problem in another domain. `run_compass.py` is the corrective arm:
ask for 62 answers as prose, parse, then classify what came back. **28.2% of condition-A runs
are invalid**, four models produce no valid sheet under any condition, one build exhausted its
budget on 12 of 15 runs, and three ablation pairs are excluded for tokenizer garbage. Every one
is an artifact produced and then rejected.

It also answers the objection that killed logit scoring earlier the same day
([RESULTS-2026-09-07-logit-scoring-fails-agreement.md](RESULTS-2026-09-07-logit-scoring-fails-agreement.md)):
scoring the four labels' first token is impossible because `Strongly Agree` and `Strongly
Disagree` collide at `'Strong'`, and the letter form that works is not legend-invariant. A
grammar keeps the **original wording**, so it should have been the same instrument with the
parser removed.

## It works, mechanically

Ollama accepts a JSON schema in `format`. An array of 62 enum values pins the whole sheet:

```json
{"type": "array", "minItems": 62, "maxItems": 62,
 "items": {"type": "string", "enum": ["Strongly Disagree", "Disagree", "Agree", "Strongly Agree"]}}
```

**One call, 62 answers, every one a legal label, no parser in the path.** Five runs of
`qwen2.5:14b` at temperature 0.7 with swept seeds: 62 of 62 answers on every run, zero problems.
The prompt comes from `run_compass.build_prompt` — the same function the parser arm uses — so
only the decoding changes.

Mechanically it removes, for open-weight models, every failure class the release document listed.

## And it does not agree with the parser

| | |
|---|---|
| items compared | 62 |
| exact match | **18 (29.0%)** |
| **side-flips** | **17** |

Against this study's own floors: the modal estimator's side-flip p90 is **3**, the run-to-run
replicate p90 is **5**, and the deliberate political manipulation under the wave protocol is
**7**. Seventeen is more than double the manipulation and more than three times the replicate.

**A composition error accounted for only 3 of it.** The first comparison pooled all 105 valid
parsed runs of the model — conditions A, B, D and P together — against a condition-D constrained
modal, and scored 20 side-flips. Restricting the parsed side to condition D gives 17. The tell
that something was wrong with the comparison was that the letter-form logit attempt had scored
**exactly 20** on the same flawed basis: two unrelated designs landing on an identical number is
more likely a property of the comparison than of either method. Correcting it did not rescue the
result.

## So the finding is not about the prototype

Two scoring methods that share nothing except "do not parse prose" both disagree with the parser
by 17–20 items of 62. The parsimonious reading is not that both are broken:

> **How you elicit the answer changes the answer by ~17 items of 62 — larger than the deliberate
> political manipulation (7), larger than reordering the questionnaire (3–14), larger than
> swapping model variants (11), and larger than requantising the weights (6).**

If that survives replication it is the largest nuisance factor this study has measured, and it
sits in a place nobody in this literature controls for: a model asked to *write out* 62 answers
in prose is doing something different from a model *emitting a constrained array*, even given
byte-identical instructions. Free generation lets the model condition each answer on the ones it
has already written; the grammar arm gives it the same freedom, so the difference is not simply
the absence of chain-of-thought — but the two are demonstrably not interchangeable.

**This is not yet a floor.** What it needs before it can be quoted as one:

- **More than one model.** Everything here is `qwen2.5:14b`.
- **A matched protocol on both sides.** The constrained arm is 5 swept seeds at temperature 0.7;
  the parsed condition-D side pools 33 runs across dates and temperatures. The wave protocol
  exists precisely to remove that, and this comparison has not been run under it.
- **More than one condition.** Condition D only.

Until then it is a strong signal from one cell, reported as such.

## The cost that does not go away

**A model that cannot emit prose cannot refuse.** Refusal is §1's headline finding — *"refusal
is elicited, not intrinsic"*, 14 of 42 models declining all 62 propositions with no directive and
every one of them stopping when given one — and that finding is measured **from the invalid
runs**. Constrained decoding erases its evidence by construction.

So the grammar arm is better for measuring **position** and fatal for measuring **willingness**.
Adopting it means running two arms for two questions, not replacing one with the other. That is
a real design, and it is not the "free upgrade" the release document described.

## Status

`scripts/constrained_probe.py` is committed as the prototype. Nothing published moved, and the
parser arm remains the instrument of record for every number in this study.
