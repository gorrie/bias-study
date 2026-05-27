---
name: bias-study-prep
description: Pre-run refresh and sanity check for the LLM bias study. Pulls the repo, confirms the protocol files are present, verifies the OpenRouter key is reachable (and, if running the heavier rungs, the OBLITERATUS / G0DM0D3 toolchain and GPU image), and records a dated prep-state file. Run before every study run to guarantee reproducibility against a known-good state.
---

# bias-study-prep

A pre-flight refresh for the bias study. Run this **before every study run** — the
reproducibility guarantee starts from a recorded known-good state.

## What it does

Establishes and snapshots the state the run depends on, then writes an audit record. It does
**not** execute the study itself; it is a gate that either says "good to run" or fails loudly
so a non-reproducible run never starts.

## Prerequisites

- A clone of this repository, on a clean branch.
- Python 3.11+ and the deps in `requirements.txt` (`pip install -r requirements.txt`).
- An OpenRouter API key. The pipeline reads `OPENROUTER_API_KEY` from the environment first,
  then a repo-root `.env`, then `~/.claude/agents/.env`. Set it whichever way you prefer:
  ```bash
  export OPENROUTER_API_KEY=sk-or-...
  # or
  cp .env.example .env   # then edit OPENROUTER_API_KEY=...
  ```
- **Only if running the weight rung** (`abliteration-run`): Docker + an NVIDIA GPU (or an
  Apple-Silicon machine), a local checkout of OBLITERATUS, and a built GPU image. See the
  `abliteration-run` skill and `README.md` for upstream URLs and pinned commits.
- **Only if running the pipeline rung** (`g0dm0d3-pipeline`): a local checkout of G0DM0D3 and
  its server running. See the `g0dm0d3-pipeline` skill.

## TRIGGER when

- About to execute a new study run (any rung — prompt, pipeline, or weight).
- Someone asks to "prep for the bias study" or invokes `/bias-study-prep`.

## SKIP

- Mid-run state checks (use the per-rung recovery steps instead).
- Generic "is everything OK" questions.
- During study execution itself — this is a pre-flight, not a runtime check.

## Procedure

1. **Update the repo.** `git pull` on a clean working tree so the run records which commit it
   ran against. If you are also running the pipeline or weight rungs, update those upstream
   checkouts (OBLITERATUS / G0DM0D3) and note their commit hashes too.
2. **Sanity-check the protocol directory** (`protocol/`): confirm `questions.md`, `rubric.md`,
   `schema.md`, `run-protocol.md`, `aggregation-rules.md`, and `vendor-enrollment-brief.md` are
   all present and non-empty. These are the spec the run is validated against.
3. **Verify the OpenRouter key is reachable** (required for both running the study and scoring).
   A presence check is enough for prep — confirm the env-var resolves to a non-empty value via
   the same resolution order the scripts use (environment, then repo `.env`, then
   `~/.claude/agents/.env`). Do **not** spend budget on a live call here; the run itself will
   surface auth errors.
4. **Verify the heavier toolchain only if those rungs are in scope:**
   - Pipeline rung: the G0DM0D3 server starts and answers a health check.
   - Weight rung: the OBLITERATUS CLI imports inside the GPU image, the GPU is visible to
     Docker (`docker run --rm --gpus all ... nvidia-smi`), and configs parse.
5. **Record the state.** Write a dated prep-state file to `data/<YYYY-MM-DD>/prep-state.json`
   containing: the repo commit hash (and any upstream tool commits), protocol-file checksums,
   tool versions (Python, Docker, the GPU image tag if used), and env-var presence flags
   (presence only — **never the key value**).

## Output

On success: `data/<YYYY-MM-DD>/prep-state.json` written, a console summary of commit hashes and
env-var presence, and exit 0.

On any failure: a console error naming the failed check, exit 1 (the run MUST NOT proceed), and
`prep-state.json` either not written or written with `status: failed`.

## Notes

- **Windows / Git-Bash:** if you run Docker-based checks from Git-Bash, prefix `docker run`
  invocations with `MSYS_NO_PATHCONV=1` so MSYS doesn't rewrite `-v host:/container` volume
  paths. On macOS/Linux this prefix is unnecessary.
- The prep-state file is the audit trail. Keep it in the run dir so the run is self-describing.
