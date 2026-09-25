# The bug fix went into the mirror and not the working copy

**2026-09-02.** Found by a Fable audit of the public/private duplication, verified here, and it
is the most serious thing in this directory's recent history — not because a published number
is wrong, but because of what kind of divergence it was.

## What diverged

`studypaths.py` was written in the public mirror to kill two documented bugs:

1. **A missing run printed `[skip]` and exited 0** — a finished study producing no confidence
   intervals and no FDR correction, with no error anywhere, silently voiding the study's own
   rule that a delta is reportable only when its CI excludes zero.
2. **One global RNG stream.** `random.seed(20260527)` at module scope meant `bootstrap_ci`
   drew sequentially, so the draws a given (run, model) cell received depended on how many
   cells had been processed before it. The public docstring records the measurement: passing
   the five main run-dates in reverse order moved **6 of 46 published CI cells**.

**Both fixes existed only in the public copy.** The private working copies of `ci_analysis.py`
and `robustness_checks.py` — the ones in this directory, the ones an operator reaches for —
still had `random.seed(20260527)` at module scope and did not import `studypaths` at all.

Twenty same-named scripts differ between the two trees this way. Two of them are statistics.

## Measured here, not inferred

Ran the private `ci_analysis.py` over `2026-05-25-full` + `2026-05-26-variance`, forward and
reversed:

| | private copy | public implementation |
|---|---:|---:|
| cells present in both orders | 22 | 22 |
| **CI bounds that moved** | **5** | **0** |
| largest movement | 0.04 | — |
| verdicts flipped | 0 | 0 |

The five: `gemma-3-27b-it` `[-0.07,+0.13] → [-0.07,+0.17]`, `glm-4.7` `[-0.41,+0.14] →
[-0.41,+0.10]`, `grok-4.3` 0.02, `gemini-3.1-pro-preview` 0.01, `deepseek-r1` 0.01.

**No published verdict is wrong.** That is the correct and the lucky answer at once: this
study's gate is binary, so a bound sitting a few hundredths from zero is decidable by argument
order, and `glm-4.7`'s upper bound moved from +0.14 to +0.10 — still the same side of zero, on
this pair of runs, this time.

## Why this is the worst shape a fork can take

Prose that has rotted looks wrong when you read it. **A bootstrap that has rotted looks exactly
like a bootstrap.** Nobody reviewing output would have caught this; it took diffing two trees
nobody thought to diff.

And the direction is the wrong way round from what you would guess. The *mirror* had the fix
and the *working copy* had the bug — active development had moved to the public repo without
anyone deciding that, so the private tree quietly became the stale one while still looking like
the source of truth.

## The repair: one implementation, not a ported patch

Porting the fix would have left two copies that agree today. Instead:

- **`studypaths.py` takes a `STUDY_ROOT` override**, so one copy of these scripts can serve
  more than one study tree.
- **`runs_root()` now resolves by CONTENT, not by name.** It looked for a directory *called*
  `data` then one called `runs`; that works only because the mirror's `data/` happens to hold
  runs. Pointed at this directory — whose `data/` holds config JSON and whose runs are in
  `runs/` — a name-based rule silently returns the config directory, and the failure mode is
  precisely the exit-0-having-computed-nothing that `studypaths` exists to prevent.
- **The two private copies are retired in place**: each is now a short shim that sets
  `STUDY_ROOT` to this directory and forwards to the public implementation. The logic exists
  once. The documented invocation still works.

Verified end to end: through the shim, against this study's data, `ci_analysis` moves **0 of 22
cells** between argument orders and produces output byte-identical to running the public script
directly; `robustness_checks` reports the same 4-of-13 FDR survival and +0.220 length
correlation it always did. All three paper gates green, `pytest scripts/` 10 passed.

## Still open, and deliberately not bulk-actioned

**Eighteen more same-named scripts differ** between the trees. They need per-file review, not a
sweep — the first question for each being whether the private side carries an unfixed bug the
public side already repaired. `run_study.py`, `score.py`, `aggregate.py` and
`cross_method_report.py` are the ones whose output feeds published figures, so they go first.

Twelve scripts are public-only, including the whole dose-series and supervisor tooling: active
development really has moved to the mirror. Eighteen are private-only, and `export_scrubbed.py`
is properly among them — it *generates* the public export and belongs on this side.

The lesson for the pitch, since this repo is meant to be the open one: **an open mirror that is
ahead of its own working copy is not a mirror.** Whatever arrangement we land on, the thing to
guarantee is that a fix cannot land on one side only.
