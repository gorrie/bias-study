# Skills and the orchestrator agent

This directory holds the [Claude Code](https://docs.claude.com/en/docs/claude-code) **skills**
that run the bias study, plus a sibling `../agents/bias-barometer.md` **agent**. They are
operating procedures — not extra code. They tell Claude Code (or a human) how to drive the
scripts in `../scripts/` against the protocol in `../protocol/`, in the right order, with the
right discipline.

You do not need any of this to check the study: the `README.md` at the repo root has the
Reproduce block. These files are for running the study again as a repeatable instrument.

## Which design a skill applies to

The study changed design as it went. Every skill says which design it serves:

- **Live** — the 32-item forced-choice battery (`data/ratchet-battery.json`, 16 mirrored pairs)
  and the XSTest refusal suite.
- **Historical** — the May 2026 judge-scored 1–5 panel (V1), withdrawn by the released paper
  (`PAPER-no-position-only-consensus.md`). Historical skills are kept so the withdrawn numbers
  can be reproduced and audited. Do not run them as a current measurement.

## The ten skills

| Skill | Design | What it does |
|-------|--------|--------------|
| [`bias-study-prep`](bias-study-prep/SKILL.md) | live | Pre-flight: validates the live battery, runs the pre-run gates, snapshots the noise floors, records a dated prep-state file. Run before every study run. |
| [`barometer-wave`](barometer-wave/SKILL.md) | live | Collects and verifies a battery wave end to end — fixed panel, shuffled-order arm, stock-vs-ablated arm — then the floors, model cards and publication gates. |
| [`abliteration-run`](abliteration-run/SKILL.md) | live | Builds a stock-vs-abliterated pair with OBLITERATUS (pinned at 205d28a) in the Docker/CUDA path. |
| [`abliteration-on-mps`](abliteration-on-mps/SKILL.md) | live | The same build on Apple Silicon through the Python driver. Required for Gemma-2 (the CUDA/MKL eigensolver fails). |
| [`mlx-weight-prep`](mlx-weight-prep/SKILL.md) | live | Converts HF safetensors from either abliteration skill into MLX fp16. |
| [`g0dm0d3-pipeline`](g0dm0d3-pipeline/SKILL.md) | historical procedure | Rung 2. Executed; the proxy path this skill describes was abandoned. Read its status block first. |
| [`bias-study-report`](bias-study-report/SKILL.md) | historical | Statistics for judge-scored runs: CIs, FDR, length control, the effect-check against the self-resample floor, per-rung deltas. |
| [`api-judge-sweep`](api-judge-sweep/SKILL.md) | historical | The four API judge methods of the V1 cross-judge sweep. |
| [`abliterated-judge-sweep`](abliterated-judge-sweep/SKILL.md) | historical | V1 Method 2: an abliterated model as the judge. |
| [`cross-method-analysis`](cross-method-analysis/SKILL.md) | historical | Synthesis of the V1 judge sweep. |

## The orchestrator agent

[`../agents/bias-barometer.md`](../agents/bias-barometer.md) was written for the three-rung
force-escalation ladder. The ladder-monotonicity claim is withdrawn (`CORRECTIONS.md` #21): no
model is measured on all three rungs. Use the live skills above directly.

## Installing them for Claude Code

Install by **linking**, never by copying. A copied skill stops receiving fixes the moment it is
copied, and drift between an installed copy and this directory has already cost this study
corrections that existed in no repository. Copying also breaks `bias-study-prep`: its
`scripts/refresh.py` locates the study from its own path.

```bash
# from the repo root, macOS / Linux
for d in skills/*/; do ln -s "$PWD/$d" ~/.claude/skills/"$(basename "$d")"; done
```

```bat
:: Windows (cmd), from the repo root -- directory junctions need no admin rights
for /d %d in (skills\*) do mklink /J "%USERPROFILE%\.claude\skills\%~nxd" "%CD%\%d"
```

Link only the skills you need; the historical ones are safe to leave uninstalled. Edit skills
here, never in `~/.claude/skills`.

Then, from a Claude Code session opened on this repo, invoke a skill by name (e.g.
`/bias-study-prep`) or just ask ("prep the bias study", "collect a battery wave"). Any
`SKILL.md` also reads as a runbook you can follow by hand.

## Conventions these files assume

- **All paths are repo-relative.** Run from the repo root.
- **The OpenRouter key resolves from the environment, then a repo-root `.env`** — set it
  whichever way you like (`cp .env.example .env`).
- **Models and abliteration outputs live wherever you point two env vars** — `$MODELS_DIR` and
  `$ABLIT_OUT` (weight builds only).
- **Cite, don't vendor.** OBLITERATUS and G0DM0D3 are external. OBLITERATUS is pinned at
  `205d28a` (`d6af36f` and `04b8ec6` build a destroyed model at one direction). G0DM0D3 has no pin
  yet: record the commit you ran.
- **Secrets never ship.** Keys and `.env` files stay local; scan before any push.
- **Cross-platform.** The pipeline is plain Python. Windows / Git-Bash notes (e.g.
  `MSYS_NO_PATHCONV=1` before `docker run`) are called out as asides with their POSIX
  equivalents.
- **Doc-reality discipline.** Never describe a rung or a finding as current until the records
  and the corrections ledger say so.
