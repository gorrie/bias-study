#!/usr/bin/env python3
"""Collect I3 Phase 4: the frozen panel against the authored mirrored bank.

THE SHAPE, and every part of it is pre-registered in
`PREREG-2026-09-14-i3-phase4.md` (amended 2026-09-15, before any call):

    31 models  x  4 conditions (N, A, P, D)  x  3 shuffle seeds (11, 22, 33)
    = 372 whole-sheet calls

`run_compass.py` is whole-sheet -- one call returns all 60 answers -- which is
why this is 372 calls and not the "5,760" the prereg body said before the
amendment. That figure counted item-answers.

WHY A DRIVER AND NOT A SHELL LOOP
---------------------------------
Three things have to hold across 372 invocations, and a loop that forgets any of
them collects a corpus that looks complete:

  * ONE MODEL PER SITTING. All 12 of a model's sheets go back-to-back. A
    contrast whose arms were collected two days apart manufactured two of five
    "significant" intervals in this project's own rung-2 work, and the fix was
    to stop splitting a model across days.
  * EVERY SAMPLE ITS OWN ORDER. `run_compass` defaults to id order, which puts
    each mirrored pair's halves adjacent -- the model can see a proposition and
    its negation at once and be consistent for free. The three samples are three
    SEEDS, not three draws at one order.
  * RESUMABLE WITHOUT DOUBLE-COUNTING. A wave that dies at model 19 must
    continue, not restart, and must not append a second copy of a cell it
    already holds. Cells already on disk are skipped by (model, condition,
    shuffle_seed).

    python scripts/run_i3_wave.py --plan     # what it would call, no API
    python scripts/run_i3_wave.py --run
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)

RUN_DATE = "2026-09-16-i3-phase4"
ITEMS = "data/ratchet-propositions-i3.json"
CONDITIONS = ("N", "A", "P", "D")
SEEDS = (11, 22, 33)
TEMPERATURE = 0.7
BASE_SEED = 20260915

#: SIZED FROM THE WHOLE ROSTER, after 4,096 failed exactly the way this project
#: already documents.
#:
#: The first value here was 4,096, taken from a Phase 2 smoke whose longest sheet
#: used 2,184 tokens. That smoke was ONE model, and a non-reasoning one. A
#: reasoning model spends the budget on reasoning before it emits an answer, so
#: at 4,096 the wave produced:
#:
#:     deepseek     95.8% invalid, 23 of 24 sitting exactly at the cap
#:     moonshotai   72.2% invalid, 23 at the cap
#:     openai        7.7% invalid, 0 at the cap
#:     anthropic     8.3% invalid, 1 at the cap
#:
#: That is differential exclusion by vendor, 7.7% to 95.8% -- which is FINDINGS #7,
#: this study's own established result, reproduced on its own instrument by the
#: person who had just spent the day repairing the 800-token version of it. The
#: lesson was already written down in recollect_at_cap.py's docstring: 800 was not
#: a neutral default for a 2026 line-up, and neither is 4,096.
#:
#: 32,768 is sized from the measured maximum across the roster: kimi-k2.5 emitted
#: 16,226 tokens on a sheet where it had room. Double it.
MAX_TOKENS = 32768


def panel():
    with io.open(os.path.join(STUDY, "data", "wave-panel.json"), encoding="utf-8") as fh:
        return json.load(fh)["models"]


def is_local(model):
    """Local ids have no vendor prefix, or are a pulled GGUF repo."""
    return "/" not in model or model.startswith("hf.co")


def safe(name):
    return "".join(c if c.isalnum() or c in "-._" else "_" for c in name)


def _served_provider(out_date, model, cond):
    """Which backend actually served this cell's most recent sheet, or None.

    Read from the record rather than from the request, because the request did not
    name one -- the first sheet of a cell is collected unpinned and the router
    decides. Every later sheet in that cell is then held to whatever came back, so
    the study fixes a backend without choosing one.

    Returns None on the local channel (no routing) and when the field is absent, and
    the caller simply does not pin. A missing provider must not become a pin of
    `None`, which `run_compass --provider` would reject as a literal backend name.

    MATCH ON THE RECORD, NOT ON A FILENAME. The first version built the path from this
    module's `safe()`, which maps `z-ai/glm-5.3` to `z-ai_glm-5.3` while run_compass's
    own `safe_filename` writes `z-ai__glm-5.3`. Two functions for one fact, and the
    helper silently found nothing and pinned nothing -- a second copy of a naming rule
    behaving exactly like the second copies of numbers this study keeps correcting.
    `done_cells` already reads the records rather than the names; so does this.
    """
    out_dir = os.path.join(STUDY, "runs", out_date)
    served = None
    for path in sorted(glob.glob(os.path.join(out_dir, "*.jsonl"))):
        for line in io.open(path, encoding="utf-8", errors="replace"):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get("model") == model and rec.get("condition") == cond \
                    and rec.get("provider"):
                served = rec["provider"]
    return served


def done_cells(out_dir):
    """(model, condition, shuffle_seed) already on disk."""
    got = set()
    for p in glob.glob(os.path.join(out_dir, "*.jsonl")):
        for line in io.open(p, encoding="utf-8", errors="replace"):
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            got.add((r.get("model"), r.get("condition"), r.get("shuffle_seed")))
    return got


def budget_precondition(models):
    """Refuse to collect until the budget is MEASURED across the whole roster.

    THIS EXISTS BECAUSE THE INSTRUCTION WAS NOT ENOUGH.
    ---------------------------------------------------
    The I3 plan's Phase 2 gate says the measured output length sets the budget,
    and the design review attached a per-model probe to it in as many words:
    "one model tells you nothing about the other seven ... set the token budget
    from the LONGEST model's output, not the smoke model's."

    It was read, and then not done. A one-model smoke set the cap at 4,096, 372
    sheets were launched on it, and 231 landed at 95.8% invalid for deepseek and
    7.7% for openai -- differential exclusion by vendor, which is this study's own
    FINDINGS #7, reproduced on its own instrument hours after the 800-token
    version of it had been repaired.

    The defect was not ignorance. The lesson was written in three places. The
    defect is that a gate living in prose is checked by whoever remembers it, and
    the execution path checked nothing. This project's answer to that everywhere
    else is an executable gate in front of the spend, so it fails closed:
    collection_check before scoring calls, key_numbers --check before a claim
    ships. This is the same thing in front of a collection.

    Returns a list of reasons to refuse. Empty means go.
    """
    probe = os.path.join(STUDY, "runs", "2026-09-16-i3-budget-probe")
    if not os.path.isdir(probe):
        return ["no budget probe on disk. Run: python scripts/probe_budget.py --run"]

    seen, lengths, at_ceiling = {}, [], []
    for p in glob.glob(os.path.join(probe, "*.jsonl")):
        for line in io.open(p, encoding="utf-8"):
            if not line.strip():
                continue
            r = json.loads(line)
            t = r.get("tokens_out") or 0
            seen[r["model"]] = t
            lengths.append(t)
            if t >= 65536 - 10:
                at_ceiling.append(r["model"])

    reasons = []
    missing = [m for m in models if m not in seen]
    if missing:
        reasons.append("%d roster model(s) never probed: %s"
                       % (len(missing), ", ".join(sorted(missing)[:6])))
    if at_ceiling:
        reasons.append("%d model(s) hit the probe ceiling, so their length is a floor "
                       "not a measurement: %s" % (len(at_ceiling), ", ".join(at_ceiling)))
    if lengths:
        need = 2 * max(lengths)
        if MAX_TOKENS < need:
            reasons.append("MAX_TOKENS is %d; the roster's longest sheet is %d, so the "
                           "budget must be at least %d" % (MAX_TOKENS, max(lengths), need))
    return reasons


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--plan", action="store_true", help="what would be called; no API")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--out-date", default=RUN_DATE)
    ap.add_argument("--models", default="", help="comma-separated filter")
    ap.add_argument("--delay", type=float, default=1.0)
    args = ap.parse_args(argv)

    out_dir = os.path.join(STUDY, "runs", args.out_date)
    models = panel()
    if args.models:
        want = {m.strip() for m in args.models.split(",")}
        models = [m for m in models if m in want]

    os.makedirs(out_dir, exist_ok=True)
    have = done_cells(out_dir)
    todo = [(m, c, s) for m in models for c in CONDITIONS for s in SEEDS
            if (m, c, s) not in have]

    if args.plan or not args.run:
        print("I3 PHASE 4 -- %s" % args.out_date)
        print("  models      %d (%d local, %d hosted)"
              % (len(models), sum(1 for m in models if is_local(m)),
                 sum(1 for m in models if not is_local(m))))
        print("  conditions  %s" % ", ".join(CONDITIONS))
        print("  seeds       %s" % ", ".join(str(s) for s in SEEDS))
        print("  sheets      %d planned, %d already on disk, %d to collect"
              % (len(models) * len(CONDITIONS) * len(SEEDS), len(have), len(todo)))
        print("  max_tokens  %d (2x the roster's measured maximum, probe_budget.py)" % MAX_TOKENS)
        return 0

    # THE PRECONDITION, in front of the spend. Never a warning: a wave collected
    # at an unmeasured budget is not cheaper to discard than it was to collect.
    refuse = budget_precondition(models)
    if refuse:
        print("REFUSING TO COLLECT -- the budget is not measured across this roster.")
        for r in refuse:
            print("  * %s" % r)
        print("")
        print("This is the gate the plan asked for and the last wave did not have:")
        print("372 sheets were launched on a cap taken from ONE non-reasoning model,")
        print("and deepseek came back 95.8% invalid against openai's 7.7%.")
        print("")
        print("NOTE: --models narrows this check to the models you named. That is")
        print("deliberate for a scoped re-collection and is also the way past this")
        print("gate, so do not reach for it to make this message go away.")
        print("Run: python scripts/probe_budget.py --run")
        return 2

    started = time.time()
    n_ok = n_fail = 0
    _ = _served_provider  # named here so a refactor cannot drop the helper silently
    # Grouped by model so a model's twelve sheets are contiguous in time.
    for model in models:
        cells = [(c, s) for c in CONDITIONS for s in SEEDS if (model, c, s) not in have]
        if not cells:
            continue
        print("=== %s  (%d sheet(s))" % (model, len(cells)), flush=True)
        # ONE BACKEND PER CELL, decided by the cell's first sheet and held for the rest.
        #
        # The 2026-09-16 wave returned 36 cells whose three replicates were served by
        # different providers -- worst, deepseek-v4-flash-0731/A across OpenInference,
        # Relace and Sail Research. Replicates in a cell are supposed to differ by the
        # draw and nothing else. Serving path is one of the same-version variants this
        # study MEASURES, so a cell straddling two backends confounds the condition
        # contrast with the routing, and collection_check refuses the run for it.
        #
        # The pin is not chosen in advance: it is whatever served sheet 1, so the study
        # is not picking backends, only holding one fixed within a cell. `run_compass
        # --provider` sends allow_fallbacks=False, so a pin that cannot be honoured
        # FAILS the sheet instead of quietly routing elsewhere and recording the
        # substitute -- which is the behaviour this replaces.
        pinned = {}
        for cond, seed in cells:
            cmd = [sys.executable, os.path.join(HERE, "run_compass.py"),
                   "--model", model, "--items", ITEMS, "--condition", cond,
                   "--runs", "1", "--shuffle-seed", str(seed),
                   "--temperature", str(TEMPERATURE), "--seed", str(BASE_SEED + seed),
                   "--max-tokens", str(MAX_TOKENS), "--out", os.path.join("runs", args.out_date)]
            if is_local(model):
                cmd += ["--channel", "ollama", "--no-think"]
            elif pinned.get(cond):
                cmd += ["--provider", pinned[cond]]
            r = subprocess.run(cmd, cwd=STUDY, capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
            tail = [l for l in (r.stdout or "").splitlines() if "runs valid" in l]
            if r.returncode == 0 and tail:
                n_ok += 1
                # Learn the cell's backend from the sheet that just landed, so the rest
                # of the cell is held to it. Read from the RECORD rather than guessed:
                # the served provider is the only thing that can pin the next call.
                if not is_local(model) and not pinned.get(cond):
                    served = _served_provider(args.out_date, model, cond)
                    if served:
                        pinned[cond] = served
                        print("    %s pinned to %s for the rest of this cell"
                              % (cond, served), flush=True)
                print("    %s seed %-3s %s" % (cond, seed, tail[-1].split(": ")[-1]), flush=True)
            else:
                n_fail += 1
                err = ((r.stderr or r.stdout or "").strip().splitlines() or ["?"])[-1]
                print("    %s seed %-3s FAILED  %s" % (cond, seed, err[:110]), flush=True)
            time.sleep(args.delay)

    print("")
    print("collected %d sheet(s), %d failed, in %.1f min"
          % (n_ok, n_fail, (time.time() - started) / 60.0))
    print("NOW RUN:  python scripts/collection_check.py %s" % args.out_date)
    return 0


if __name__ == "__main__":
    sys.exit(main())
