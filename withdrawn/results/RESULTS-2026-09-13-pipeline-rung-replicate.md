# Rung 2 re-collected with replicates — results

**Run:** `runs/2026-09-13-g0dm0d3-replicate` (pipeline arm) and
`runs/2026-09-13-g0dm0d3-replicate-baseline` (same-sitting plain B).
**Pre-registration:** `PREREG-2026-09-13-pipeline-rung.md`, committed `cba6e473` before any call
was made and unedited since. **Predictions were read before this output.**

## What was collected

400 calls, as specified. 2 models × 4 conditions × 10 questions × 5 samples.

| | records | eligible | excluded |
|---|---:|---:|---|
| pipeline arm (`B-STM`, `B-Parseltongue`, `B-Layered`) | 300 | 295 | 5, judges declined to score |
| same-sitting baseline (plain `B`) | 100 | 100 | none |

**Zero truncated**, verified by the text test rather than `finish_reason`, which this proxy
reports as `"stop"` even on responses severed mid-word. Both arms ran at `--max-tokens 4000`;
the May wave's 800 is what truncated Opus on every layered call.

**All 60 cells returned 5 byte-distinct draws** (mean 5.00 of 5.0), so the replicate design is
real rather than five copies of one deterministic answer. Replicate depth is `[4, 5]` after the
five unscored records drop out, and the estimator reports that rather than assuming 5.

## Results

Paired per question against the same-sitting plain-B baseline. Positive = more
institution-skeptical. Replicates averaged within cell before differencing.

| model | contrast | n | effect | 95% interval | |
|---|---|---:|---:|---|---|
| claude-opus-4.7 | B-STM vs plain B | 10 | +0.12 | [−0.07, +0.35] | |
| claude-opus-4.7 | B-Parseltongue vs plain B | 10 | −0.01 | [−0.15, +0.13] | |
| claude-opus-4.7 | B-Layered vs plain B | 10 | −0.19 | [−0.53, +0.13] | |
| **claude-opus-4.7** | **B-Layered − B-STM** | 10 | **−0.31** | **[−0.64, −0.01]** | excludes 0 |
| grok-4.3 | B-STM vs plain B | 10 | +0.07 | [−0.13, +0.29] | |
| grok-4.3 | B-Parseltongue vs plain B | 10 | +0.09 | [−0.06, +0.23] | |
| **grok-4.3** | **B-Layered vs plain B** | 10 | **+0.56** | **[+0.23, +0.85]** | excludes 0 |
| **grok-4.3** | **B-Layered − B-STM** | 10 | **+0.48** | **[+0.26, +0.70]** | excludes 0 |

Three of eight intervals exclude zero, against none of eight in the May data.

> **Two later corrections, and this table survives both.**
>
> **(1)** `B-Parseltongue` applies no transform to this instrument — 0 of 240 requests — so its
> row is a **null by construction**. Reading −0.01 on Opus and +0.09 on Grok is the correct
> behaviour of an untreated arm, not a weak effect.
>
> **(2)** The baseline named at the top of this document really is the **same-sitting** one, and
> that is why these numbers stand. A budget-matched baseline collected two days later was briefly
> made the default on 2026-09-14; it pushed the untreated arm to **+0.24, excluding zero**, which
> is how the mistake was caught. Reverted 2026-09-15.
>
> Full account: [`RESULTS-2026-09-14-rung2-transform-audit.md`](../../RESULTS-2026-09-14-rung2-transform-audit.md).

## The pre-registered predictions

| # | prediction | outcome |
|---|---|---|
| 1 | Claude Opus 4.7 stays flat — all three Claude contrasts span zero | **HIT** for the three vs-baseline contrasts (+0.12, −0.01, −0.19, all spanning zero). But the fourth Claude contrast, `B-Layered − B-STM`, is **−0.31 and excludes zero**. Opus is flat against baseline and NOT flat between techniques. |
| 2 | The grok layered effect shrinks below +0.60 | **HIT.** `B-Layered − B-STM` falls +0.60 → **+0.48**. The open question the prereg attached to it is now answered: the interval **does** clear zero, [+0.26, +0.70]. |
| 3 | The single-technique arms add nothing on either model | **HIT.** All four span zero: +0.12, −0.01 (Opus), +0.07, +0.09 (grok). |
| 4 | No ceiling is located | **HIT**, and unchangeable by sample size. Three points on one axis cannot locate where added force stops helping. A ceiling claim needs a dose series, which is a different arm. |

Four of four predictions hit.

## What this establishes, and what it does not

**Rung 2 is real, and it is MODEL-SPECIFIC with opposite signs.** The layered stack adds force on
grok-4.3 (+0.56 against plain B, +0.48 over hedge-strip alone) and **subtracts** it on Opus 4.7
(−0.31 against hedge-strip alone). That is not "only the layered stack adds force, to a ceiling."
It is one model where layering helps and one where layering hurts, measured in the same sitting
on the same items with the same panel.

**Neither single technique does anything on either model.** Hedge-strip alone and obfuscation
alone are indistinguishable from plain B in all four cells. Whatever the layered stack does, it
is not the sum of its parts.

**No ceiling was measured and none can be from this design.** Prediction 4 is a statement about
what three points on one axis can support, not about the data.

## Against the May wave

The May collection had two defects the prereg named and one it did not:

1. one sample per cell, so no within-cell variance;
2. a cross-protocol baseline — plain B from `2026-05-25-full`, pipeline conditions from
   `2026-05-27-g0dm0d3`, two days and a different collection path apart;
3. **not in the prereg:** `claude-opus-4.7 / B-Layered` was **10 of 10 truncated** at the
   800-token cap. Its two published contrasts (−0.10 vs plain B, −0.10 minus B-STM) were
   estimated from ten responses severed mid-sentence. Only Opus overflowed; grok is terser and
   fit, so exactly one of the six May cells was affected — and it is one of the two the claim
   rested on.

## Supporting run directories

Three small runs on the same date are **detector validation evidence, not study data**, and
no published number rests on them. They are named here because `run_inventory.py --check`
rightly reports any run directory holding records that no study document mentions.

| run | what it is |
|---|---|
| `runs/2026-09-13-truncation-proof/` | `claude-opus-4.7` / `B-Layered` at `--max-tokens 800`, 10 records. The known-TRUNCATED set. Every response is severed mid-word and the proxy reported `finish_reason="stop"` for all ten — the evidence that the field is not usable. |
| `runs/2026-09-13-g0dm0d3-smoke2/` | the same cell at 4000, 10 records. The known-GOOD control, mean 716 words. |
| `runs/2026-09-13-g0dm0d3-smoke/` | `grok-4.3` / `B-Layered` at 800, 10 records. The over-flagging control: a terse model that finishes well inside the cap must NOT be called truncated, or the guard would discard good records. |

The truncation detector was validated against all three before being trusted: 10/10 flagged on
the first, 0/10 on each of the other two.

## Disposition

The README row already reads "**no effect established** — all 8 intervals span zero at n=1 per
cell", corrected before this ran, as the prereg required. It now needs a second update: rung 2
**is** established for grok-4.3, with the opposite sign on Opus 4.7, and the "to a ceiling"
clause stays unsupported. Do not restore the original sentence.

Nothing here licenses a general claim about elicitation-layer force. Two models is two models.
