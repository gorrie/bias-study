# Two statistics on the same sheets: the union runs 2× the pairwise rate

**2026-09-21.** `runs/2026-09-18-paraphrase`, 448 sheets, 44 models with comparable coverage,
ten semantics-preserving templates at one presentation order, condition N.
Pre-registered in `PREREG-2026-09-18-paraphrase.md`, which requires both statistics be
reported on the same data. `scripts/paraphrase_analysis.py`.

## What this settles

The paper cited Röttger et al. (ACL 2024) beside our order floor and called the two "the same
magnitude". They are not comparable, and the denominator is the shallow reason — their counts
are out of 62 propositions and ours out of 32. The real problem is the statistic:

- **Röttger counts a union.** An item counts once if ANY of ten paraphrases disagrees about
  its side.
- **We count a pairwise difference.** Items differing between TWO administrations.

A union over k draws is mechanically larger on identical instability. Until now this study
asserted that and could not say by how much, so it could neither compare the two literatures
nor convert between them.

**Measured, on the same sheets, same models, same order — the only difference being which
statistic is computed:**

| statistic | median | max |
|---|---:|---:|
| union (Röttger's) | **2.0** | 17 |
| pairwise (ours) | **1.0** | 3 |

**The union runs 2.0× the pairwise rate.** Not "several times": twice, at the median. The
maxima diverge much harder — 17 against 3 — because the union accumulates every disagreement
any template produces while a pairwise difference cannot exceed what two sheets disagree on.

## Per model, where it matters

| model | union | pairwise |
|---|---:|---:|
| `cohere/command-a` | **17** | 0.0 |
| `ibm-granite/granite-4.2-8b` | 14 | 3.0 |
| `tencent/hy4-preview` | 8 | 2.0 |
| `openai/gpt-6-astra` | 7 | 2.0 |
| `minimax/minimax-m2.7` | 5 | 1.0 |
| `openai/gpt-6-astra-pro` | 5 | 2.0 |
| … | | |
| 30 of 44 models | 0 | 0.0 |

**`cohere/command-a` is the case worth reading.** Union 17 of 32 — more than half the
instrument — against a pairwise median of **zero**. Every pair of templates agrees, and yet
across all ten, seventeen items move at some point. That is not a contradiction: it is what a
union does to instability spread thinly across many draws. A reader given only the union would
conclude this model is wildly unstable; given only the pairwise rate, that it is perfectly
stable. Both numbers are correct.

That single row is the argument for reporting the statistic alongside the number, and it is
the reason the conversion exhibit this arm replaced was cut rather than repaired.

## What this does NOT establish

- **It is not a replication of Röttger.** Their instrument, panel and year all differ. What
  is held fixed here is the statistic, not the study.
- **The reverse direction is separate.** `replicate_rottger.py` runs our statistic on their
  published completions; that is the other half and is reported separately.
- **One presentation order.** Every sheet here is order T01's, by design — the arm varies
  wording, not order, so nothing here bears on the order floor.
- **Ten templates is the k.** The ratio between a union and a pairwise rate depends on k, and
  a 20-template arm would widen it. The 2.0× figure belongs to k=10 and must be quoted with it.

## Commands

    python scripts/collection_check.py 2026-09-18-paraphrase
    python scripts/paraphrase_analysis.py
    python scripts/paraphrase_analysis.py --json
