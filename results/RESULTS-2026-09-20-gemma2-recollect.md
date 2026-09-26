# The Gemma-2-9B arm: the records were never lost, the stance reproduces, and the wording claim does not

**2026-09-20, M5.** `data/2026-09-20-gemma2-recollect/` — 40 records, two arms,
`run_local.py`, items T01-Q2…T10-Q2, conditions A and B, position neutral, one sample,
`transformers-local`, seed 20260527 on both arms. Scored by the local abliterated-Gemma judge
(`score_inproc_gemma.py`, MLX in-process), output in `scored-abliterated-gemma/`.

## Why this run exists

It was collected to replace Gemma-2-9B records believed lost. They were not lost: they are in
`data/2026-05-27-abliteration-gemma2/`, and recompute to the published figure exactly —
`score_classifier` 3 on all 40, panel disagreement 0 on 39 of them. The zero-byte files that
suggested otherwise are placeholders in the four-family directory, declared in
`data/empty-records.json`. The re-collection is kept because it supplies two results the original
could not: an independent judge on the stance figure, and a same-weights control on the wording.

## 1. The stance figure reproduces under an independent judge — and that is not good news

| arm | condition A | condition B | Δ B−A |
|---|---:|---:|---:|
| `gemma-2-9b-stock` | 3.00 (n=10) | 3.00 (n=10) | **+0.00** |
| `gemma-2-9b-abliterated` | 3.00 (n=10) | 3.00 (n=10) | **+0.00** |

**All 40 records score exactly 3**, under a judge that shares nothing with the original
four-judge API panel. The published "stance holds at 3.00 in every condition" is confirmed by an
independent scorer, which is a stronger form of the claim than the original had.

**But zero variance across forty records is not a finding about stance. It is an instrument that
cannot resolve stance on this model.** The website already carries the caveat — open 7–9B models
sit at the rubric midpoint to begin with — and this makes it concrete: there is no measurement
here in which movement could have been detected. It is absence of evidence against the
dissociation, not evidence for it, and the dissociation claim for Gemma should not lean on it.

## 2. The wording-change claim is not established, and this run is what shows it

The recollection's real value: it supplies the **same-weights control** the original run never
had. Mean word-set Jaccard over the 20 shared cells:

| pairing | Jaccard |
|---|---:|
| stock vs abliterated, original run | **0.347** |
| stock vs abliterated, this run | 0.341 |
| stock vs stock, **same weights**, resampled | **0.381** |
| abliterated vs abliterated, **same weights**, resampled | **0.377** |

`scripts/gemma2_recollect_jaccard.py --check` recomputes all four rows with the study's
word tokenizer (`abliteration_effect_check.jaccard`, `[a-z]+`); an apostrophe-preserving
tokenizer gives 0.345 / 0.339 / 0.380 / 0.377 and the same verdict.

`abliteration_effect_check.py` records the same-model resample band as 0.303–0.392. The
between-arm figure sits inside it **and below Gemma's own resample noise**. Local runs sample at
temperature 0.7 with no seed; that is what temperature alone produces.

This matters beyond Gemma. `FINDINGS.md` has ruled "text change not established" for
`llama-3.1-8b` (0.339) and `mistral-7b` (0.333) since September, on a band measured on **one
other model**, which is a borrowed floor. Here the band is
confirmed **on the subject's own weights**, so for Gemma the verdict rests on nothing borrowed.
Of the five families, **only `qwen2.5-7b` (0.276) falls outside the band.**

The wording claims this bears on are withdrawn (`CORRECTIONS.md` #22). The **stance** half of the
weight-rung claim is unaffected and remains the load-bearing one.

## 3. Also corrected

"39 of 40 judge cells unanimous" was a unit error. 40 records × 4 judges is 160 cells; the 39
counts **records** on which the panel agreed. Verified: 159 of 160 cells score 3, one judge
returned a 5 on one record, and the panel median is 3 on all 40. The number was right.

## Limitations

- **One model, 10 items, 20 records per arm.** Nothing here generalises past Gemma-2-9B.
- **A different judge from the original.** The stance agreement is across scorers, which is a
  strength; the unanimity count is not comparable and is not claimed.
- **Temperature 0.7, no seed in the original.** The seed on this run is a new control, and it
  does not pair the arms — once the first sampled token differs the streams diverge.
- **The Jaccard verdict is a null.** It says the text change is not distinguishable from
  resampling on this measure, not that abliteration leaves the text unchanged.
