# The rung-2 contrast at protocol v2: no position claim survives

**2026-09-21.** `runs/2026-09-19-rung2-elicitation` differenced against
`runs/2026-09-20-rung2-control-v2`, both at protocol v2, matched on model and presentation
order (shuffle seed 11). Pre-registered in `PREREG-2026-09-20-rung2-control-v2.md`.
`scripts/rung2_contrast.py`.

## What this arm was for, and what it settles

The rung-2 position claims were withdrawn on 2026-09-19, the day they were made, because every
arm was differenced against a **v1** control: the contrast carried the system prompt *and* the
numbering change, and the numbering change is a published finding of this study. Seventy sheets
of v2 control were collected to buy the missing half.

**With the confound removed, the claims stay withdrawn.** That is the result.

| | |
|---|---|
| contrasts computed | **35** (seven models' arms; two more refuse the sheet entirely) |
| withdrawn by the per-contrast floor rule | **28 of 35** |
| nominal exact p < 0.05 | **4** |
| expected by chance at 35 tests | **1.75** |
| surviving Benjamini–Hochberg at 5% | **0** |

The smallest exact p in the arm is 0.0113 against a BH critical value of 0.0014. Nothing is
close. Four nominal hits out of thirty-five is what thirty-five tests produce.

## The floor rule is what does most of the work

Each contrast is scored against **that model's own between-order difference measured at v2** —
control seed 11 against control seed 22, both sides from the same seventy sheets — and not
against a corpus percentile or a v1 floor. Twenty-eight contrasts are at or under their own
model's floor:

| model | v2 between-order floor | contrasts | withdrawn by floor |
|---|---:|---:|---:|
| `x-ai/grok-4.3` | 0.131 | 7 | 7 |
| `openai/gpt-6-astra-pro` | 0.125 | 7 | 7 |
| `anthropic/claude-fable-5.1` | 0.075 | 7 | 7 |
| `openai/gpt-6-astra` | 0.075 | 7 | 7 |
| `moonshotai/kimi-k2.5` | 0.019 | 7 | 0 |

`grok-4.3` is the case the withdrawal was about. Its largest contrast is **+0.113** (S-Balanced)
against a floor of **0.131** — reordering that model's own control sheets moves it further than
any system prompt in the arm does. Its previously published −0.206 was judged against a
between-order floor measured on **v1** sheets.

`kimi-k2.5` is the opposite and is the only model whose contrasts clear their floor, because its
floor is 0.019 — the smallest in the arm. Two of its seven reach nominal significance
(S-Balanced −0.106 at p = 0.0317; S-Chaotic +0.350 at p = 0.0179), and **neither is reportable**:
they do not survive correction over the family, they point in opposite directions, and the
S-Chaotic cell holds **three** arm sheets.

## The test is exact, and that matters at this depth

`contrast_sheets` is a bootstrap whose two-sided p is a doubled resampling tail, and
`calibrate_estimators.py` measures its false-positive rate at five sheets per arm at about
**10%**, not 5%. Every p above is instead an **enumerated two-sided permutation test** over all
C(n+m, n) splits of the pooled sheets. At 5 v 5 that is 252 splits and the smallest attainable
p is 2/252 = 0.0079; most cells here are 5 v 5 or 10 v 5, and the arm's smallest attainable p
is 0.0357. A depth that cannot reach the threshold it is judged against is a design fact, not a
finding, and it is printed with the table.

## What this does NOT establish

- **It is not evidence that rung 2 does nothing.** Twenty-eight contrasts sit under their own
  model's order floor, which bounds them rather than zeroing them. An undetectable effect and
  an absent one are not the same finding — this paper argues that about other people's work.
- **It does not migrate the corpus.** Seventy sheets of v2 sit beside a v1 corpus; this is not
  `RESEARCH-BACKLOG` §17.
- **The declared token-cap difference stands.** The arms ran at `max_tokens` 8192 and the
  control at 40960. Measured: **0 arm sheets came within 95% of their cap**, so the difference
  is declared and, on this data, not doing anything.
- **Both gemini models are absent from the contrast table, and not for the same reason.**
  Each declines all ten of its control sheets, under the changed numbering exactly as under
  the old — a refusal that reproduces is a manipulation check, and it reproduced. But
  `gemini-3.8-flash` also returned **three valid arm sheets**, which are collected, paid for
  and unusable: there is nothing to subtract them from. The script prints them rather than
  dropping them, because a sheet missing from every table with no reason given is a sheet
  nobody knows exists.

## Commands

    python scripts/rung2_contrast.py
    python scripts/rung2_contrast.py --json
    python scripts/rung2_contrast.py --selftest
