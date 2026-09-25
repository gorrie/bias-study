# The within-rung rung-2 contrasts at depth 10: two survive correction, none clears its floor

**2026-09-25.** `runs/2026-09-19-rung2-elicitation`, shuffle seed 11, protocol v2, the five
models that answer the arm sheets. Pre-registered in `PREREG-2026-09-25-rung2-within-depth10.md`
(committed `361cae6d` before the contrast was computed). No collection; the depth-10 sheets were
collected on 2026-09-19 (runs 1–5) and 2026-09-20 (runs 6–10). `scripts/rung2_contrast.py
--within`.

## Result

| | |
|---|---|
| contrasts in the family | **10** (two per model) |
| smallest attainable exact p at this depth | 2.2 × 10⁻⁵ (9 v 10), against a BH rank-1 threshold of 0.005 |
| surviving Benjamini–Hochberg at q = 0.05 | **2** |
| of those, exceeding the model's own v2 between-order floor | **0** |
| sign in runs 6–10 matching runs 1–5 | 6 of 10 |
| reportable under all three registered conditions | **0** |

| model | contrast | n | effect | exact p | runs 1–5 | runs 6–10 | v2 floor |
|---|---|---:|---:|---:|---:|---:|---:|
| `claude-fable-5.1` | G-Directive − G-Boost | 10 / 10 | +0.034 | 0.0602 | +0.006 | +0.062 | 0.075 |
| `claude-fable-5.1` | G-Persona − G-Directive | 9 / 10 | −0.027 | 0.0998 | +0.012 | −0.062 | 0.075 |
| `kimi-k2.5` | G-Directive − G-Boost | 10 / 10 | −0.059 | 0.4890 | −0.088 | −0.031 | 0.019 |
| `kimi-k2.5` | G-Persona − G-Directive | 10 / 10 | +0.050 | 0.5059 | +0.094 | +0.006 | 0.019 |
| `gpt-6-astra` | G-Directive − G-Boost | 10 / 10 | **+0.062** | **0.0023** | +0.081 | +0.044 | 0.075 |
| `gpt-6-astra` | G-Persona − G-Directive | 10 / 10 | −0.013 | 0.5789 | −0.038 | +0.013 | 0.075 |
| `gpt-6-astra-pro` | G-Directive − G-Boost | 10 / 10 | **+0.066** | **0.0006** | +0.069 | +0.062 | 0.125 |
| `gpt-6-astra-pro` | G-Persona − G-Directive | 10 / 10 | −0.028 | 0.0766 | −0.019 | −0.038 | 0.125 |
| `grok-4.3` | G-Directive − G-Boost | 10 / 10 | +0.125 | 0.1292 | +0.256 | −0.006 | 0.131 |
| `grok-4.3` | G-Persona − G-Directive | 10 / 10 | −0.034 | 0.7229 | −0.225 | +0.156 | 0.131 |

Effect is the difference in mean sheet position, where a sheet's position is the mean over
mirrored pairs of (critic − defender)/2. Bold: survives BH.

## Against the predictions

**Manipulation check: passed.** Restricted to runs 1–5, the computation reproduces the
`RESEARCH-BACKLOG.md` §16 depth-5 table. Eight of ten values match to the printed digit; the
other two are the same number rounded the other way (−0.0875 printed −0.087 there and −0.088
here; +0.0125 printed +0.013 and +0.012).

**P1 (direction) — killed by its own rule.** Of the four depth-5 cells that carried the lead,
two keep their sign in runs 6–10 and two do not: the directive's effect on `gpt-6-astra`
(+0.044) and `gpt-6-astra-pro` (+0.062) recurs; the two `grok-4.3` cells, which were the largest
in the backlog table (+0.256 and −0.225), fall to −0.006 and reverse to +0.156. Fewer than three
of four kept their sign. The "directive up, persona back down" pattern was mostly the first five
`grok-4.3` sheets.

**P2 (decidability) — refuted, at a depth where it could have been confirmed.** The criterion
is now satisfiable: the smallest attainable exact p is four orders of magnitude below the BH
threshold, and two contrasts do survive — DEPTH_DIRECTIVE moves `gpt-6-astra` by +0.062
(p = 0.0023) and `gpt-6-astra-pro` by +0.066 (p = 0.0006), in the same direction on both halves
of the collection. Neither exceeds its model's own v2 between-order floor (0.075 and 0.125), so
under the registered rule neither is reportable: reordering the same model's control sheets
moves its mean position further than the directive does.

## What this establishes and what it does not

- **The within-rung null is now a bounded null, not a design fact.** At depth 5 no outcome was
  possible. At depth 10 the family is decidable and the answer is that no prompt-content effect
  inside rung 2 is larger than the presentation-order nuisance on the same model. That is the
  paper's lead finding — the manipulation and the nuisance are the same size — recurring inside
  the elicitation rung.
- **The directive effect on the two OpenAI models is real in the ordinary statistical sense and
  small in the study's sense.** It survives correction and recurs on the second day's sheets. It
  is below the order floor. Both statements are true and the paper should not report one without
  the other.
- **The floor is itself estimated from five v five control sheets** (seed 11 against seed 22 in
  `runs/2026-09-20-rung2-control-v2`). It is one draw, as the clause factorial's floors were, and
  a different pair of orders would give a different floor. The kill rule was registered with
  that floor and is applied as registered.
- **`kimi-k2.5` is the reverse case.** Its floor is 0.019, so all four of its contrasts clear it,
  and none is anywhere near significance (p ≥ 0.49).
- **The two G-arms instruct against measured outcomes** (`run_rung2.INSTRUCTS_AGAINST_OUTCOME`),
  so these are prompt-content interventions, not elicitation results. Nothing here bears on
  G-Boost against the control, which `RESULTS-2026-09-21-rung2-control-v2.md` covers.

## What did not work

Nothing was collected. The task as briefed was to collect the G-arms to depth 10; the records
show that depth was collected on 2026-09-20, homogeneous with the first five sheets in protocol,
seed, cap, provider pin and system-prompt digest (`check_comparison.py --cells` reports every
non-treatment field matched for all ten pairs). What was missing was the analysis.

## Commands

    python scripts/rung2_contrast.py --within
    python scripts/rung2_contrast.py --within --json
    python scripts/rung2_contrast.py --selftest
    python scripts/check_comparison.py --cells 2026-09-19-rung2-elicitation <model> G-Boost G-Directive --treatment condition system_prompt --family 10
