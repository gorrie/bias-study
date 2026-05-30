# Skills and the orchestrator agent

This directory holds the [Claude Code](https://docs.claude.com/en/docs/claude-code) **skills**
that run the bias study, plus a sibling `../agents/bias-barometer.md` **agent** that orchestrates
the whole thing. They are operating procedures — not extra code. They tell Claude Code (or a
human) how to drive the scripts in `../scripts/` against the protocol in `../protocol/`, in the
right order, with the right discipline.

You do not need any of this to reproduce the study: the `README.md` at the repo root has the
plain four-command pipeline. These files are for running the *full* multi-rung study as a
repeatable instrument, and for re-running it on a cadence.

## The five skills

| Skill | Rung / role | What it does |
|-------|-------------|--------------|
| [`bias-study-prep`](bias-study-prep/SKILL.md) | pre-flight | Pulls the repo, checks the protocol files, verifies the OpenRouter key (and the heavier toolchain if needed), and records a dated prep-state snapshot. Run before every study run. |
| [`g0dm0d3-pipeline`](g0dm0d3-pipeline/SKILL.md) | rung 2 (pipeline) | Applies elicitation-layer force (hedge-strip + obfuscation) via a G0DM0D3 server, layered up to each model's coherence ceiling. **Specified, not yet executed** in the published data. |
| [`abliteration-run`](abliteration-run/SKILL.md) | rung 3 (weights) | Ablates the refusal direction from an open-weight model via OBLITERATUS and runs stock-vs-abliterated A/B. Needs a GPU. |
| [`abliterated-judge-sweep`](abliterated-judge-sweep/SKILL.md) | judgement-tool Method 2 | Re-scores every record with an abliterated open-weight model as the JUDGE. Tests whether judge alignment (not just system-under-test alignment) carried bias into the consensus. In-process MLX on Apple Silicon, lockfile-protected, OOM-resilient. |
| [`bias-study-report`](bias-study-report/SKILL.md) | analysis | Turns scored runs into defensible numbers — bootstrap CIs, FDR, length control, inter-judge agreement, the abliteration effect-check, ladder monotonicity, and the quarter-over-quarter drift diff. |

The prompt rung (rung 1) is just `scripts/run_study.py` and needs no skill — see the root
`README.md`.

## The orchestrator agent

[`../agents/bias-barometer.md`](../agents/bias-barometer.md) ties the rungs together. It runs the
full three-rung force-escalation ladder end to end — prep -> prompt -> pipeline -> weights ->
score -> report -> drift diff -> publish — and re-runs it on a quarterly cadence, diffing each
pass against the prior quarter to maintain a longitudinal record of model-bias drift. Use it to
execute a complete pass, add a vendor or model, or run a quarterly "barometer" update.

## How to use them with Claude Code

These files follow the Claude Code skill / agent conventions. To make them invocable, copy them
into your Claude configuration (or point your project config at this directory):

```bash
# skills -> ~/.claude/skills/<name>/SKILL.md
mkdir -p ~/.claude/skills
cp -r skills/bias-study-prep skills/abliteration-run skills/g0dm0d3-pipeline \
      skills/abliterated-judge-sweep skills/bias-study-report ~/.claude/skills/

# agent -> ~/.claude/agents/<name>.md
mkdir -p ~/.claude/agents
cp agents/bias-barometer.md ~/.claude/agents/
```

Then, from a Claude Code session opened on this repo:

- Invoke a skill by name, e.g. `/bias-study-prep`, or just ask ("prep the bias study", "run the
  weight rung on Qwen2.5-7B", "report the latest run with CIs").
- Invoke the agent for a full pass ("run a quarterly bias-barometer pass").

You can also read any `SKILL.md` as a runbook and execute the steps by hand — every step maps to
a script in `../scripts/` or a documented command.

## Conventions these files assume

- **All paths are repo-relative.** Run from the repo root. Runs live under `data/<date>/`.
- **The OpenRouter key resolves from the environment, then a repo-root `.env`, then
  `~/.claude/agents/.env`** — set it whichever way you like (`cp .env.example .env`).
- **Models and abliteration outputs live wherever you point two env vars** — `$MODELS_DIR` and
  `$ABLIT_OUT` (weight rung only).
- **Cite, don't vendor.** OBLITERATUS and G0DM0D3 are external; clone them from upstream at the
  pinned commits listed in the root `README.md`.
- **Secrets never ship.** Keys and `.env` files stay local; scan before any push.
- **Cross-platform.** The pipeline is plain Python. Windows / Git-Bash–specific notes (e.g.
  `MSYS_NO_PATHCONV=1` before `docker run`) are called out as asides with their POSIX
  equivalents.
- **Doc-reality discipline.** Never describe a rung as run until the records carry its real
  field values. The pipeline rung is currently planned, not executed — the files say so.
