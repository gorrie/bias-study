# The central comparison, settled: order and manipulation are the same size

**Collected** 2026-09-06, `runs/2026-09-06-wave-orders/`, `scripts/order_floor_wave.py`.
**310 calls.** The measurement §3 of the paper was explicitly calling for.
**Answer:** neither factor can be shown larger than the other. That is the result.

## What was missing

§3 compared the deliberate manipulation against presentation order and reported the comparison
as unsettled, for a stated reason: the two rows were collected differently.

| row | how it was collected |
|---|---|
| manipulation, one sitting | temp 0.7, swept seed, 5 runs per cell, modal vs modal |
| presentation order (pooled) | mixed temperatures and dates, and **23 of its 37 shuffled cells hold ONE run** |

A single draw carries a full unit of run-to-run noise (replicate p90 5) that a five-run modal
has averaged away. Comparing them measures the collection design as much as the factors.

## What was collected

Same fixed panel, same frozen parameters, same five swept seeds, **varying only item order**:
two shuffled orders against the canonical order wave 0 already held. Three orders per model,
three pairs each.

**Condition D, not A.** The pooled order floor is measured under the balance instruction, which
is the worst condition on this instrument to measure anything — on wave 0, **A is 28.2% invalid
against D's 2.9%**, and fourteen panel models decline A outright. An order floor collected there
is computed on whichever models happen not to refuse, which is a sample selected by §1's
finding. D is what the position series already runs on, and it makes the contrast direct: the
manipulation is A→D, and this is what item order alone does *inside* D.

52 of 62 cells reached n=5. Ten had their runs and came back short — the gemma-4-12B GGUF build
returned nothing usable in 27 attempts (token budget and transport), `mistral:latest` nothing in
10, `llama3.1:8b` two of five each way. Those are properties of the models, not gaps, and the
collector does not re-queue a cell that has had its full run budget.

## The result

Like-for-like, modal against modal on both sides, one protocol:

| row | pairs | median | p90 | max | p90 95% CI | clusters |
|---|---:|---:|---:|---:|---|---:|
| presentation order, one sitting | 85 | **1** | **10** | 21 | [3, 12] | 29 |
| prompt condition A→D, one sitting | 25 | **3** | **7** | 14 | [4, 12] | 25 |

Both intervals are cluster-bootstrapped over models.

**They do not separate, and the shape of the failure is the interesting part.** Presentation
order has the *lower* median and the *higher* tail: reordering the questionnaire usually moves
almost nothing — a median of one item in 62 — and occasionally moves ten. The deliberate
manipulation moves a few items on nearly every model and rarely more than eight. One is
low-frequency and high-amplitude; the other is high-frequency and low-amplitude. Their p90
intervals overlap across nearly their whole length.

## What the paper can now say

Not "the nuisance factor is bigger" — that draft was published on 2026-09-06 and withdrawn the
same day (`CORRECTIONS.md` #7). Not the reverse either.

**A factor nobody controls for and a factor built to move the answer are the same size on this
instrument, measured the same way, and neither is demonstrably larger at this sample.** Any
published effect below about ten items of 62 sits inside the range item order alone produces,
and that holds whatever the manipulation turns out to do.

That is a weaker sentence than the one this project reached for twice, and it is the first
version of it that survives its own collection design.

## Why the pooled row stays in the table

It is not deleted and not superseded — it answers a different question. The pooled row is order
under condition A across mixed collections; this row is order under condition D in one sitting.
Both print, with their protocols named, because the difference between them is now a measured
quantity rather than an unexamined assumption: pooled p90 11 [5, 14] against one-sitting p90
10 [3, 12].

## Reproduce

```bash
python scripts/order_floor_wave.py --report     # collection state
python scripts/order_floor_wave.py --run        # resumable, skips exhausted cells
python scripts/floor_table.py --markdown        # both rows, in the table
```
