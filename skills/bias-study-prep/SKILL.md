---
name: bias-study-prep
description: Pre-run refresh and sanity check for the LLM bias study. Validates the live forced-choice instrument (62 propositions, contiguous ids, one sentence each), runs the five pre-run gates, and snapshots every noise floor's pair count so a collection that lands nowhere is detectable. Also pulls the repo, checks the legacy judge-scored protocol files, verifies the OpenRouter key is reachable and — for the heavier rungs — the OBLITERATUS / G0DM0D3 toolchain, then records a dated prep-state file. Run before every study run to guarantee reproducibility against a known-good state.
---

# bias-study-prep

A pre-flight refresh for the bias study. Run this **before every study run** — the
reproducibility guarantee starts from a recorded known-good state.

## What it does

Establishes and snapshots the state the run depends on, then writes an audit record. It does
**not** execute the study itself; it is a gate that either says "good to run" or fails loudly
so a non-reproducible run never starts.

**Read the scope note before trusting a green tick.** Steps 1–2 pre-flight the *judge-scored
battery* that was the primary instrument until 2026-08-29. Every file they check still exists,
so they pass — and they say nothing whatever about a forced-choice run. That is exactly how
this skill once ran green in front of a collection it did not check. Steps 3–5 are the ones
that speak to the current instrument. If you only have time for part of this, it is those.

## Prerequisites

- A clone of this repository, on a clean branch.
- Python 3.11+ and the deps in `requirements.txt` (`pip install -r requirements.txt`).
- An OpenRouter API key. The pipeline reads `OPENROUTER_API_KEY` from the environment first,
  then a repo-root `.env`. Set it whichever way you prefer:
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

`skills/bias-study-prep/scripts/refresh.py` runs all of this end to end and writes the audit
record. The steps are documented so a failure is diagnosable, not so they are performed by
hand.

*(Until 2026-09-07 this line gave that path without its `skills/bias-study-prep/` prefix — a
path that does not exist, and one this document contradicted twelve lines further down where
the invocation is correct. `check_skill_docs.py` gates it now. The retracted path is described
rather than quoted here on purpose: the gate reads backticked paths, so re-typing a dead one
inside its own correction would keep the gate red forever.)*

1. **Update the repo.** `git pull` on a clean working tree so the run records which commit it
   ran against. If you are also running the pipeline or weight rungs, update those upstream
   checkouts (OBLITERATUS / G0DM0D3) and note their commit hashes too.
2. **Sanity-check the legacy protocol directory** (`protocol/`): confirm `questions.md`,
   `rubric.md`, `schema.md`, `run-protocol.md`, `aggregation-rules.md`, and
   `vendor-enrollment-brief.md` are all present and non-empty. These are the spec the
   *judge-scored* runs are validated against. A pass here is not a statement about the
   forced-choice instrument — see step 3.
3. **Validate the live forced-choice instrument.** The proposition file is **not in this
   repository and never will be** — it is third-party instrument text, fetched at your end by
   `python scripts/fetch_items.py`, which writes `data/compass-propositions.json`. Run that
   first if it is absent; a fresh clone will not have it. Then confirm
   that file, `scripts/run_compass.py`,
   `scripts/test_compass_parser.py` and the live prereg are present, and that the item set is
   **62 propositions with contiguous ids 1..62** — answers are keyed by item id, so a gap
   silently misaligns every comparison. Also confirm each proposition is **exactly one
   sentence**, a measured property of this instrument that the parser bound in
   `scripts/fetch_items.py` depends on.
4. **Run the five pre-run gates.** All must *already* pass before new runs land: if the paper
   disagrees with the data now, adding runs makes the disagreement harder to attribute rather
   than easier.
   - `scripts/gen_paper.py --check` — every generated table matches `runs/`
   - `scripts/key_numbers.py --check` — the sentences quoting those tables
   - `scripts/controls_audit.py --strict` — no verdict about another study sourced from notes
   - `scripts/test_compass_parser.py` — the 13 answer-parser fixtures
   - `check_no_fork.py` — no script exists in two trees with different content. **Private
     working tree only**: it compares this mirror against the working study, so it lives on
     the side that can see both and is not shipped here. Skip it when prepping from a clone.
5. **Snapshot every noise floor's pair count, before the run.** This is the check this skill
   most needed and did not have. Twice — 27 runs on 2026-09-01 and 14 on 2026-09-02 — runs
   were collected specifically to extend a floor and contributed **nothing** to it, because
   the floor tool carried a hardcoded list of run directories and a new directory is
   invisible to an include list by construction. Both times the collection looked successful
   and the row did not move. A pair count taken beforehand makes that a subtraction.
5b. **Name the parameter that will silently ruin this collection, and say how you checked it.**
   `COLLECTION-STANDARD.md` §4 asks exactly this, and for four months nothing executed it. The
   answer in May was the token budget: `run_study.py`'s default of 800 truncated 21.5% of the
   corpus, differentially by model — 96.7% of one model's records against near zero for terse
   ones — and nothing recorded the cap, so it could not even be detected after the fact.

   Concretely, before a wave:
   - **Smoke one cell and measure the OUTPUT LENGTH, not just the exit code.** If the longest
     response lands near the cap, the cap is the parameter, and the next model is more verbose
     than this one.
   - **Never trust `finish_reason`.** Through the G0DM0D3 proxy it reports `"stop"` on responses
     severed mid-word, because the proxy rewrites the body and drops the upstream reason. Check
     the text.
   - **Record the parameters on every record** (`max_tokens`, `temperature`). A run directory
     that cannot say what produced it cannot be audited later.
   - Then run `scripts/collection_check.py <run>` on the smoke output. It is §4 made
     executable, and it refuses rather than warning.

6. **Verify the heavier toolchain only if those rungs are in scope:**
   - Pipeline rung: the G0DM0D3 server starts and answers a health check.
   - Weight rung: the OBLITERATUS CLI imports inside the GPU image, the GPU is visible to
     Docker (`docker run --rm --gpus all ... nvidia-smi`), and configs parse.
7. **Record the state.** Write a dated prep-state file containing: the repo commit hash (and
   any upstream tool commits), protocol-file checksums, the instrument's checksums and item
   count, each gate's exit code, `floors_before`, tool versions, and env-var presence flags
   (presence only — **never the key value**).

## How to invoke

```bash
python skills/bias-study-prep/scripts/refresh.py

# check-only, no pull or build:
python skills/bias-study-prep/scripts/verify-state.py

# the skill's own tests:
python skills/bias-study-prep/scripts/test_refresh.py
```

`refresh.py` reads `BIAS_STUDY_WORKSPACE` to locate the workspace it is prepping, and defaults
to the home directory.

## Output

On success: `<runs>/<YYYY-MM-DD>/prep-state.json` written, a console summary of commit hashes,
instrument item count, each gate's verdict and every floor's pair count, and exit 0.

On any failure: a console error naming the failed check, exit 1 (the run MUST NOT proceed), and
`prep-state.json` either not written or written with `status: failed`.

## Repairing a corpus a token cap destroyed

The May 2026 runs used an 800-token budget and lost about a third of their records, severed or
empty, **differentially by model**. Full procedure and the reasoning behind each step:
`learnings.md`, 2026-09-14. Map of what was repaired: `CORPUS-MAP-2026-09-14.md`.

```bash
python scripts/recollect_at_cap.py --plan  --source <damaged> --out-date <repair>
python scripts/recollect_at_cap.py --run   --source <damaged> --out-date <repair>
python scripts/collection_check.py <repair>            # must say ACCEPTED
python scripts/score.py <repair> --fill-missing
python scripts/splice_corpus.py --write --base <damaged>
```

- `scripts/splice_holes.py` reports what a repair would recover before you run it.
- `scripts/splice_corpus.py` writes the derived corpus the analysis reads; without it the
  repaired records sit in their own run and nothing reads them.
- `scripts/repair_recollect_provenance.py` fixes records written before the collector stamped
  its own call time, and `--manifests` backfills a manifest for any repair run lacking one.
- `scripts/position_analysis.py --selftest` validates the mirrored-bank estimator against
  synthetic input with known answers. Its decisive check: a model that agrees with everything
  scores exactly 0, because the mirror cancels acquiescence by construction.

Then register the pair in `studypaths.REPAIRS` so `canonical_run` resolves analyses to the
repaired corpus, and read `studypaths.UNREPAIRABLE` for the holes no budget fixes.

## Notes

- **Windows / Git-Bash:** if you run Docker-based checks from Git-Bash, prefix `docker run`
  invocations with `MSYS_NO_PATHCONV=1` so MSYS doesn't rewrite `-v host:/container` volume
  paths. On macOS/Linux this prefix is unnecessary.
- The prep-state file is the audit trail. Keep it in the run dir so the run is self-describing.
- **After a collection, compare against `floors_before`.** If a floor's pair count did not
  move, the runs did not land where the floor reads — see step 5.

## Files

```
skills/bias-study-prep/
├── SKILL.md            (this file)
├── learnings.md        accumulated run notes
└── scripts/
    ├── refresh.py          end-to-end pre-flight
    ├── verify-state.py     sanity checks only, no pull or build
    ├── log-prep-state.py   writes the audit-trail file
    └── test_refresh.py     10 tests: instrument validation and the floor snapshot
```
