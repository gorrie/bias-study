# Per-model cards: one model of thirty-one can carry a claim

**Plan item:** `PLAN-2026-09-07-all-models.md` §A — the per-model card, zero cost, from runs
already on disk. **Rig:** `scripts/model_cards.py` (`--json` for the machine form).

Every floor in this study pools per-model behaviour away. That pooling is what hid the most
consequential fact in the corpus, and this is the file that stops hiding it.

## The result

**31 models with ≥2 valid runs in a wave cell. One carries a claim.**

| | |
|---|---|
| models analysed | 31 |
| **carry a claim** | **1** — `qwen2.5:14b`, exact permutation p = 0.0238 |
| do not | 30 |
| own run-to-run spread (p90) | min **0**, median **3**, max **18** |
| **models whose own p90 ≥ their largest measured effect** | **22 of 31 (71%)** |

The verdict is an **exact permutation test on the model's own runs**, Bonferroni-corrected over
contrasts: shuffle the condition labels among that model's runs, recompute the modal-vs-modal
distance, and ask how often shuffling alone reaches the observed value. No pooled floor is
involved — each model is judged against itself.

That correction matters, and it is recent. The verdict column previously compared a
modal-vs-modal effect against a run-vs-run p90 and took the max of up to three contrasts
uncorrected, which reported **8 of 30 carrying**. The review of 2026-09-06 (`865e7a5a`) found
that was the wrong test. Under the right one it is **1 of 31**. The earlier figure should not be
cited.

## The 71% is the finding, not the 1

Twenty-two of thirty-one models have a run-to-run spread at least as large as the biggest effect
anyone measured on them. For those models the question "does this intervention move it" has no
answer at this sample size — not "no", not "yes", *no answer* — because re-running the same
condition moves it as far as changing the condition does.

| model | own p90 | largest effect |
|---|---:|---:|
| `gemma-4-12B-it-GGUF:Q4_K_M` | 18 | 5 |
| `x-ai/grok-4.3` | 13 | 12 |
| `x-ai/grok-4.5` | 13 | 17 |
| `llama3.1:8b` | 10 | 8 |
| `moonshotai/kimi-k2.5` | 9 | 5 |
| `mistral:latest` | 6 | 7 |

`grok-4.3` is the one to sit with. Its spread is 13 items of 62 and its largest effect is 12 — and
until 2026-09-06 it was setting the reference scale for the whole paper. Removing the three x-ai
builds drops the pooled manipulation p90 from 15 to 8. **A pooled floor cannot tell you that a
single unstable family is carrying the tail.** A per-model card can, and it costs nothing,
because every number here was already in `runs/`.

## What this does and does not say

- **It does not say the models are identical.** It says that on this instrument, at this n, most
  of them cannot be distinguished from their own noise. That is a statement about measurement
  power, not about model behaviour.
- **It does not retire any published number.** The floors and the wave results stand as computed;
  what changes is that a reader can now see which models contributed stability and which
  contributed spread.
- **It does not make `qwen2.5:14b` interesting.** One model clearing a Bonferroni-corrected
  permutation test out of thirty-one is roughly what one expects to clear by chance before
  correction and is not far off after it. It is reported because the test said so, not because it
  means something.
- **It is the argument for §D of the all-models plan** — bringing the 97 partial models to n=5.
  The cards say plainly that n is the binding constraint, not model choice, and that any future
  claim about a specific model needs more runs of *that model*, not more models.

## Gates

`gen_paper.py --check` and `key_numbers.py --check` both exit 0 with this in the tree;
`test_analysis_plumbing.py` 0 failures; `release_check.py`, `check_skill_docs.py`,
`check_doc_links.py` and `gen_script_inventory.py --check` all exit 0.

`gen_paper --check` was **red** before this pass, on the floors block: the paper carried a
grammar-arm disqualification that the freshly-computed block had since qualified with the
batch-size finding (`RESULTS-2026-09-07-constrained-decoding-batch-size.md` — the arm's
instability is items-per-call, not the grammar, so the row disqualifies the whole-sheet arm
rather than constrained decoding). Regenerated; one line changed.

## Reproduce

```bash
python scripts/model_cards.py              # the table
python scripts/model_cards.py --json       # machine form
```
