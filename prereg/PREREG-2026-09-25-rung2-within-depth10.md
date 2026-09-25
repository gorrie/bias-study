# Pre-registration — the within-rung rung-2 contrasts at depth 10

**Registered 2026-09-25, before the within-rung contrast is computed on the depth-10 sheets.**
Nothing in it may be amended after the analysis command below is first run; an amendment made
after that is recorded as an amendment, dated, with the reason, and the original text is left
standing.

**No collection. $0.** This registers an analysis of sheets already on disk. It is registered
anyway, because the study registers a decision rule before it sees the number the rule decides.

---

## Why

`RESEARCH-BACKLOG.md` §16 ("The within-rung comparison is confound-free, and underpowered BY
CONSTRUCTION") and §21 found that the two within-rung contrasts of rung 2,

    G-Directive − G-Boost     = DEPTH_DIRECTIVE                 (prompt content)
    G-Persona   − G-Directive = the jailbreak persona on top    (prompt content)

compare arms collected by the same script, at the same shuffle seed, protocol, token cap and
provider pin, so none of the objections that withdrew the arm-minus-control contrast applies to
them. At five sheets per arm the smallest attainable two-sided exact p is 2/252 = 0.0079,
above the BH rank-1 threshold of 0.005 for a family of ten, so "0 of 10 survive" was a fact
about the design. The backlog costed depth 10 at ~$6 and named its kill rule.

**The depth was bought and the question was never asked.** The five non-gemini models carry
ten G-Boost, ten G-Directive and ten G-Persona sheets each in
`runs/2026-09-19-rung2-elicitation` — runs 1–5 collected 2026-09-19, runs 6–10 on 2026-09-20
(the `PLAN.md` "Tests queued 2026-09-19" item 1). No script and no document in this tree
computes the within-rung contrast on them: `rung2_contrast.py` differences arm against control
only, and the backlog's table is the depth-5 one. Re-collecting would buy sheets that exist.

Checked before registration, from the records, not the manifest: all 150 G-arm records of the
five models carry `renumbered: true`, `shuffle_seed` 11, `max_tokens` 8192, no sampling seed,
the arm's own system-prompt digest, and a single provider equal to their `provider_pinned`
(Anthropic, SiliconFlow, OpenAI, OpenAI, xAI), identically in runs 1–5 and 6–10.
`check_comparison.py --cells` reports every non-treatment field matched. One sheet is invalid
(`claude-fable-5.1` G-Persona, one refusal), so that cell is 9.

## Roster and cells

`anthropic/claude-fable-5.1`, `moonshotai/kimi-k2.5`, `openai/gpt-6-astra`,
`openai/gpt-6-astra-pro`, `x-ai/grok-4.3`. The two gemini models are excluded as in every
rung-2 analysis: they decline the arm sheets (0, 0, 0 and 0, 3, 0 valid of 5), so no contrast
exists for them.

**Family: 10 contrasts** — two per model.

## The statistic

Per sheet, the mean over mirrored pairs of (critic − defender)/2, exactly as
`rung2_contrast.sheet_means` computes it; per contrast, the difference of the two arms' mean
sheet values; the p-value is the **enumerated two-sided exact permutation test**
(`rung2_contrast.exact_permutation_p`) over all C(n+m, n) relabellings — 184,756 at 10 v 10.

**Manipulation check on the statistic.** Restricted to runs 1–5, the computation must reproduce
the backlog §16 depth-5 table to the printed precision (e.g. `grok-4.3` G-Directive − G-Boost
+0.256). If it does not, the analysis is not the one the backlog ran, and this registration is
void until that is explained.

## Decision rule

A within-rung position contrast is **reportable** only if all three hold:

1. its exact p survives **Benjamini–Hochberg at q = 0.05 over the family of 10**;
2. |effect| **exceeds that model's own v2 between-order floor** (control seed 11 against seed
   22 in `runs/2026-09-20-rung2-control-v2`, as `rung2_contrast.py` computes it) — the
   per-contrast kill rule of `PREREG-2026-09-20-rung2-control-v2.md` §4, carried over so that a
   within-rung effect is never reported as larger than what reordering the same model's
   control does;
3. its sign in **runs 6–10 alone** (5 v 5, collected the second day) matches its sign in runs
   1–5. The depth-10 cell contains the depth-5 cell, so the pooled test is not a replication;
   this is the only part of the data that did not produce the lead.

## Predictions, with kill rules

- **P1 (direction, from the backlog).** At depth 10, G-Directive − G-Boost is positive on
  `gpt-6-astra`, `gpt-6-astra-pro` and `grok-4.3`, and G-Persona − G-Directive is negative on
  `grok-4.3`. **Killed** — the backlog's own kill rule, "the direction consistency vanishing at
  depth" — if fewer than three of these four cells keep their depth-5 sign in runs 6–10 alone.
- **P2 (decidability).** At least one of the ten contrasts is reportable under all three
  conditions. **Refuted** if none is. A refutation is reported as a bounded null with the
  smallest attainable p printed, not as "rung 2 does nothing".

## Analysis command

    python scripts/rung2_contrast.py --within
    python scripts/rung2_contrast.py --within --json
    python scripts/check_comparison.py --cells 2026-09-19-rung2-elicitation <model> G-Boost G-Directive --treatment condition system_prompt

`--within` is added to `rung2_contrast.py` for this registration; it reuses the script's loader,
exact test and floor, and adds BH and the half-split.

## What counts as a result

Either outcome. P2 confirmed: the within-rung contrast is the first rung-2 position result that
survives a correction the design can satisfy. P2 refuted at a depth where the criterion is
satisfiable: the within-rung effects are bounded by this depth, which is a result the paper can
state and could not state before, because at depth 5 no outcome was possible.

## Not changed by this

No run directory is written, so nothing enters or leaves the refusal panel, and no gated figure
moves. The arm-minus-control verdict in `RESULTS-2026-09-21-rung2-control-v2.md` is a different
contrast and is untouched.
