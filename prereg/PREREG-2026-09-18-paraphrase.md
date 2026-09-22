# Pre-registration — Röttger's statistic, run on this instrument

**Registered 2026-09-18, before any sheet in this arm is collected.** Amendments after the
first `--run` are recorded as amendments, dated, with the reason, and the original text stands.

---

## 1. What this replaces, and why the thing it replaces was cut

The paper's central claim is that the movement these instruments report is no larger than the
movement they produce when nothing changes. The planned exhibit placed other studies' reported
effect sizes beside our noise floors, converted to *share of the instrument* so two banks of
different lengths could be compared.

**An adversarial review cut it, correctly, and not for the reason expected.** It is not a
rescaling error. It is an **unlike-statistic comparison wearing a correct unit**:

- Röttger et al. (arXiv:2402.16786) count propositions with **contradicting responses across
  ten semantics-preserving paraphrases** of the prompt template. An item counts if *any* of the
  ten disagrees with any other. That is a **union over k draws**.
- Our floors count items differing between **two** administrations. That is a **pairwise
  difference**.

If per-comparison instability is *q*, a k-way union runs at roughly 1 − (1 − q)^k while a
pairwise difference runs at *q*. The union is mechanically several times larger on identical
underlying instability. Placing 22.6% beside 31% and calling them the same order of magnitude
compares P(any of ten disagree) with P(these two differ). Two further entries in the cut data
file carried denominators of 100 for instruments with no such length, which is the literal
visual shape of the unit error this study withdrew five claims over
(`CORRECTIONS-2026-09-17-power.md`).

**The fix is to stop converting and start replicating.** Hold the statistic fixed and vary the
instrument. Then no conversion is needed and every objection above disappears.

---

## 2. The design

**Administer the Ratchet battery under ten semantics-preserving paraphrases of the prompt
template and compute Röttger's statistic on the result.**

`run_battery.PARAPHRASE_TEMPLATES` holds T01–T10, written before this arm was conceived, with
an import-time guard that every template requests the same parseable output format. They vary
how the task is *asked*, never what is asked: the 32 propositions, their order constraint and
the four response options are identical across all ten.

- **Roster:** the 16 models in `runs/2026-09-18-roster-smoke/manifest.json` marked working,
  plus the frozen panel's hosted models. Fixed before collection; selection is coverage and
  liveness, never outcome.
- **Condition N only.** The comparison is about how the instrument is administered, not about
  the manipulation.
- **One presentation order per model**, held constant across all ten templates, so template
  variation is not confounded with item order. The order is recorded.
- **Numbering: renumbered (protocol v2).** Sheets are printed 1..32 in presentation order.
  Collecting this arm under v1 would mix a template effect with the item-loss artifact
  (`RESULTS-2026-09-18-omission-orders.md`), which is exactly the confound this study exists
  to report.
- **Cells:** models × 10 templates × 1 run. About 320–500 sheets.

## 3. The statistic, stated before the data

For each model, over the 32 items:

**R = the number of items on which any two of the ten templates disagree about the side.**

"Side" is agreement versus disagreement against the scale midpoint, matching Röttger's
contradicting-response definition. Reported as **R of 32** per model, and beside it:

- **R/32 as a share**, which is the only figure comparable to their 14/62 and 23/62;
- the **pairwise** rate over all 45 template pairs, so the union and the difference are both
  printed and a reader can see how far apart they are on the same data. This is the number the
  cut exhibit needed and never had.

## 4. What the result can and cannot say

**Can:** "Röttger et al. report 14 of 62 and 23 of 62 on the Political Compass. Running their
statistic on a 32-item author-written bank gives R of 32." That is one statistic, two
instruments, no conversion.

**Cannot:** anything about whether their finding is right. The comparison is of instrument
behaviour, not of their conclusions, and the paper must not imply otherwise.

**Confounds that remain, stated now:** their models are 2023–24 and ours are mostly 2026
(`data/model-vintage.json` makes the generation split reportable); their instrument is 62
items; their templates are theirs and ours are ours. A difference in R can come from any of
these. The comparison bounds the *order of magnitude* of template sensitivity on a modern
panel, and nothing finer.

## 5. Decision rule, fixed before collection

There is no hypothesis to accept or reject. This is a measurement, and the pre-commitment is
about how it is reported:

1. **Both the union R and the pairwise rate are published**, whatever they are, and neither is
   selected after seeing which better suits the argument.
2. **Per model, never pooled**, with the panel median beside the range.
3. If **R/32 is materially larger** than our presentation-order floor share, the paper says
   template sensitivity exceeds order sensitivity on this instrument.
4. If **comparable**, it says the two nuisances are the same size — which is §1's thesis
   arriving from a third direction.
5. If **materially smaller**, that is reported as a limit on the claim: our bank is less
   template-sensitive than the Political Compass, and the generalisation is weaker than the
   paper would like.

**No outcome cancels this arm.** It is a measurement whose value does not depend on which way
it lands, which is the condition under which pre-registration is worth anything.

## 6. What would make it uninformative

Fewer than 8 of the 10 templates returning a parseable sheet for a model — that model is
reported as not measured, never as a low R. `collection_check` must ACCEPT the run before any
figure is computed.

**Registered before collection. Collection has not begun as of this commit.**
