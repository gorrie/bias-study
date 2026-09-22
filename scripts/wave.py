#!/usr/bin/env python3
"""Repeat measurement of a FIXED panel of models, on a schedule. The barometer's time axis.

WHAT THIS EXISTS TO FIX
-----------------------
Measured 2026-09-05: the forced-choice corpus spans **2026-08-30 to 2026-09-05**. Six days.
There is no time axis in it at all.

`runs/2026-08-31-lineage` looks like the exception and is not: 1,644 records, 137 models, every
one collected on 2026-08-31. It compares claude-opus-4.1 against 4.5 against 4.6 against 4.7 --
successive *versions* measured at one instant. That is a cross-section wearing a longitudinal
name, and it answers a different question. "Do releases differ" is not "did this model change".

You cannot measure the past later. Every week without a wave is a week permanently missing, and
the subjects expire: `openai/gpt-4.1` is 509 days old and sits in the judge panel.

THE FOUR THINGS A TIME SERIES NEEDS, AND WHY EACH IS HERE
--------------------------------------------------------
**1. A fixed panel.** Re-measuring "the newest models" each wave measures cohort composition,
not change. The panel is written to `data/wave-panel.json` ONCE and then held; `--freeze-panel`
writes it, and nothing recomputes it afterwards. A panel derived fresh each wave is not a panel.

**2. Frozen parameters.** The study's own floors say what moves the number without any model
changing: presentation order p90 11, instruction paraphrase p90 6, requantisation p90 6, and
the same prompt twice p90 5. So a wave that changes seed, template, order, temperature or token
budget measures nuisance and calls it drift. `--verify` re-reads a collected wave and fails if
any of it moved.

**3. Conditions that survive refusal.** Measured across the 42 both-arm models: refusal is
**0.7%** under D and P (3 of 418) and **9.8%** under A and B (122 of 1,246). The A/B rate is
rising -- as of 2026-09-05 every US-vendor flagship refuses A, and `google/gemini-3.8-flash`
refuses B as well. So **D and P carry the position series**; A and B are collected but are not
load-bearing for it.

**4. Refusal as its own series.** A refused cell is not a hole in the data. It is the finding
this project has been reporting since the paper's first section, and it now has a time axis of
its own: what fraction of the panel declines a balance instruction, wave over wave.

    python scripts/wave.py --freeze-panel      # once: write data/wave-panel.json
    python scripts/wave.py --plan              # what the next wave would collect
    python scripts/wave.py --run               # collect it (serial, delayed, resumable)
    python scripts/wave.py --verify <wave>     # did anything drift from the frozen spec?
    python scripts/wave.py --verify            # ...every wave; sample size is DISTINCT SEEDS
    python scripts/wave.py --series            # the time series, wave over wave
"""
from __future__ import annotations

import argparse
import collections
import datetime
import glob
import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, HERE)

PANEL_FILE = os.path.join(STUDY, "data", "wave-panel.json")

#: FROZEN. Every one of these is a factor the floors table measures as moving the answer with no
#: model change at all, so a wave that varies one is measuring nuisance and reporting drift.
#: `--verify` checks a collected wave against this and fails on any difference.
WAVE_PARAMS = {
    "temperature": 0.7,
    # THE SEED SWEEPS: run k uses `seed_base + k`. A FIXED seed does not produce five runs.
    #
    # Measured on the first wave collected under the old spec (fixed 20260830, 5 runs): 17 of
    # 32 cells with three or more runs held two or fewer DISTINCT answer sheets, and several
    # held one -- claude-opus-4.6 A, gemma2 B, a gemma-4-12B GGUF P. Every local model returned
    # copies, and some hosted cells were served from cache. Those cells recorded n=5 and carry
    # the information of n=1, which inflates every count built on them and makes the
    # within-cell spread zero by construction.
    #
    # `run_battery --seed-sweep` is the flag that does this on purpose; its own help says
    # "repeating a seeded deterministic call measures nothing". The wave was doing exactly that.
    "seed_base": 20260830,
    "seed_sweep": True,
    "max_tokens": 8192,
    "template": "T01",
    "runs": 5,
}

#: This project's own harness answered the instrument as a subject and is in the corpus. It
#: cannot be re-collected by `run_battery` -- there is no endpoint to call -- so it is not a
#: panel member. Recorded rather than silently dropped, because "the harness is in the corpus"
#: is a disclosure the paper makes deliberately.
NOT_COLLECTABLE = {"claude-code-harness-agent"}


def channel_for(model):
    """openrouter or ollama, from the model id. THE CHANNEL IS PER MODEL, NOT PER WAVE.

    It was a frozen wave parameter set to "openrouter" for everything, and on the first run
    that sent `gemma2:latest` and an `hf.co/...GGUF` build to a hosted API. They came back as
    `transport` failures -- caught and classified, so nothing was corrupted, but five wasted
    cells and a lesson: a local model has no vendor prefix and a hosted one always does.
    """
    if model.startswith("hf.co/") or ":" in model.split("/")[-1] and "/" not in model:
        return "ollama"
    return "openrouter" if "/" in model else "ollama"

#: D and P carry the position series (0.7% refusal). A and B are collected for the refusal
#: series and are NOT load-bearing for position -- 9.8% refusal and rising.
SERIES_CONDITIONS = ("D", "P")
REFUSAL_CONDITIONS = ("A", "B")
ALL_WAVES = "__all__"   #: sentinel for a bare --verify: check every wave present
ALL_CONDITIONS = REFUSAL_CONDITIONS + SERIES_CONDITIONS


def wave_dirs():
    """Every collected PANEL wave, oldest first. Identified by SHAPE, not by name.

    `runs/*-wave` is a name pattern and `2026-09-07-ablation-wave` matches it while being a
    different experiment entirely -- six base models with stock and ablated arms, not the fixed
    panel. Left to the glob, `--verify` read it as a panel wave and reported **"0 cells present,
    124 panel cells missing"**, which is not a finding about anything. Gating missing cells
    under --strict would then have failed the audit on a directory that was never supposed to
    hold the panel.

    A panel wave writes its runs at the TOP level of its directory (`<wave>/<model>__<cond>.jsonl`).
    The ablation arm nests them one level per base and arm (`<wave>/<base>/<arm>/...`). So the
    shape distinguishes them, and it does so for a reason rather than by coincidence: the panel
    is flat because every cell is one model, and the ablation arm is nested because every cell
    is a model *within* a comparison.

    Resolving by content rather than by directory name is the same repair `studypaths` made for
    the two run roots, and for the same reason: a name is a convention someone else can match by
    accident, and this one was matched within two days of being adopted.
    """
    out = []
    for p in sorted(glob.glob(os.path.join(STUDY, "runs", "*-wave"))):
        if not os.path.isdir(p):
            continue
        if not glob.glob(os.path.join(p, "*.jsonl")):
            continue          # nested layout: a different experiment that shares the suffix
        out.append(p)
    return out


def load_panel():
    if not os.path.exists(PANEL_FILE):
        raise SystemExit(
            "no panel at %s -- run --freeze-panel once to write it.\n"
            "The panel is written ONCE and then held. Recomputing it each wave would mean "
            "measuring cohort composition instead of change."
            % os.path.relpath(PANEL_FILE, STUDY))
    return json.load(io.open(PANEL_FILE, encoding="utf-8"))


def freeze_panel(force=False):
    """Write the panel once, from models that currently answer the surviving conditions.

    The criterion is coverage, not outcome: a model is in the panel if the corpus already holds
    it under both D and P. Selecting on how a model ANSWERS would build the series on a sample
    chosen for its answers, which is the defect this project exists to point at.
    """
    if os.path.exists(PANEL_FILE) and not force:
        raise SystemExit("%s already exists. The panel is frozen on purpose; pass --force only "
                         "if you intend to redefine the series."
                         % os.path.relpath(PANEL_FILE, STUDY))
    import refusal_table as R
    import key_numbers as K
    rows = [r for r in R.load(K.REFUSAL_EXCLUDE) if R.classify(r) in ("valid", "refused")]
    cov = collections.defaultdict(set)
    for r in rows:
        if r.get("condition") in ALL_CONDITIONS:
            cov[r.get("model")].add(r["condition"])
    panel = sorted(m for m, cs in cov.items()
                   if set(SERIES_CONDITIONS) <= cs and m and m not in NOT_COLLECTABLE)
    rec = {
        "frozen": datetime.date.today().isoformat(),
        "criterion": "present in the corpus under both surviving conditions (D and P) at "
                     "freeze time. Coverage, never outcome.",
        "series_conditions": list(SERIES_CONDITIONS),
        "refusal_conditions": list(REFUSAL_CONDITIONS),
        "params": WAVE_PARAMS,
        "note": "Held constant across waves. Adding a model starts a SHORTER series for it; it "
                "does not retroactively join the existing one. Removing one because it was "
                "retired is a fact about the vendor and must be recorded, not deleted.",
        "models": panel,
    }
    os.makedirs(os.path.dirname(PANEL_FILE), exist_ok=True)
    with io.open(PANEL_FILE, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rec, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print("froze a panel of %d model(s) -> %s" % (len(panel), os.path.relpath(PANEL_FILE, STUDY)))
    return rec


BASELINE_FILE = os.path.join(STUDY, "data", "wave-baseline.json")


def spec_matching_corpus(panel):
    """Corpus records that already satisfy the frozen spec, by (model, condition).

    WAVE 0 IS MOSTLY ALREADY COLLECTED, and re-running it would be waste dressed as rigour.
    Measured 2026-09-05: 101 of the panel's 128 cells already sit in the corpus at exactly the
    frozen parameters. The 27 that do not are there at temperature 0 or under the seed sweep --
    runs collected ON PURPOSE with a parameter varied, to measure a floor. Those are not wave
    data and must not be counted as if they were, which is the whole reason the spec is checked
    per record rather than per run directory.
    """
    import refusal_table as R
    import key_numbers as K
    hits = collections.defaultdict(list)
    for r in R.load(K.REFUSAL_EXCLUDE):
        if r.get("model") not in set(panel["models"]):
            continue
        if r.get("condition") not in ALL_CONDITIONS:
            continue
        ok = True
        for key, want in panel["params"].items():
            if key in ("runs", "channel"):
                continue
            got = r.get(key)
            if got is not None and got != want:
                ok = False
                break
        if ok:
            hits[(r["model"], r["condition"])].append(r.get("_bucket") or "?")

    # A CELL IS NOT COLLECTED UNTIL IT HAS THE RUNS THE SPEC DEMANDS.
    #
    # This returned every cell with at least ONE spec-matching record, and 56 of the 124
    # adopted cells held exactly one against a frozen spec of five. Wave 0 would then have
    # been compared against a wave 1 collected at five, and the difference would carry the run
    # count as well as the time -- confounding the only variable the series exists to isolate.
    #
    # Under-filled cells are returned separately rather than silently dropped, because "we hold
    # 2 of 5 runs for this cell" is a collection instruction and "this cell is missing" is not.
    need = panel["params"]["runs"]
    short = {k: v for k, v in hits.items() if len(v) < need}
    return {k: v for k, v in hits.items() if len(v) >= need}, short


def distinct_seeds(records):
    """How many DIFFERENT seeds a cell's runs carry.

    Run count is not sample size when the seed is fixed: under the old spec a cell could hold
    five runs and one answer sheet. Counting seeds is the cheap structural check -- it does not
    need the sheets, and it catches the defect at collection time rather than in analysis.
    """
    return len({r.get("seed") for r in records if r.get("seed") is not None})


def adopt_baseline(panel, force=False):
    """Record the already-collected, spec-matching records as wave 0. Copies nothing."""
    if os.path.exists(BASELINE_FILE) and not force:
        raise SystemExit("%s exists; wave 0 is already declared."
                         % os.path.relpath(BASELINE_FILE, STUDY))
    hits, short = spec_matching_corpus(panel)
    buckets = collections.Counter(b for v in hits.values() for b in v)
    missing = [(m, c) for m in panel["models"] for c in ALL_CONDITIONS if (m, c) not in hits]
    rec = {
        "wave": "0-adopted",
        "declared": datetime.date.today().isoformat(),
        "what": "Records already in the corpus that satisfy the frozen wave spec exactly. "
                "Adopted rather than re-collected; nothing was copied and no run directory "
                "was modified.",
        "honest_caveat": "These were collected across a six-day window (2026-08-30 to "
                         "2026-09-05) rather than in one sitting, and not for this purpose. "
                         "That is acceptable for a BASELINE against wave intervals measured in "
                         "months, and it would not be acceptable between two later waves.",
        "params": panel["params"],
        "cells_adopted": len(hits),
        "cells_missing": len(missing),
        "cells_underfilled": len(short),
        "underfilled_note": "Cells holding fewer than the spec's %d runs. They are counted as "
                            "MISSING, not adopted: comparing a 1-run wave 0 against a 5-run "
                            "wave 1 would confound run count with time, which is the one "
                            "variable this series exists to isolate. The runs already held are "
                            "not wasted -- the collector resumes and tops them up."
                            % panel["params"]["runs"],
        "underfilled": ["%s|%s (%d of %d)" % (k[0], k[1], len(v), panel["params"]["runs"])
                        for k, v in sorted(short.items())],
        "source_runs": dict(buckets.most_common()),
        "missing": ["%s|%s" % m for m in missing],
    }
    with io.open(BASELINE_FILE, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rec, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print("wave 0 declared: %d cell(s) adopted, %d still to collect -> %s"
          % (len(hits), len(missing), os.path.relpath(BASELINE_FILE, STUDY)))
    return rec


def collected(outdir, by_seed=True):
    """(model, condition) -> SAMPLE SIZE already in this wave.

    Sample size is distinct seeds, not records. Under the seed sweep a record is one position
    in a sequence, and two records at the same seed are one sample -- `distinct_seeds()` says
    so, and `--verify` has always reported it that way. This function did not, so the two
    disagreed about whether a cell was finished: `--verify` called eleven cells short while
    `--run` saw five records and skipped every one of them. A cell can only be repaired by the
    thing that decides what is left to do, so it counts the same way.

    Records with no seed at all (temperature-0 collections, pre-sweep runs) fall back to the
    record count, which is the right answer there.
    """
    seeds = collections.defaultdict(set)
    rows = collections.Counter()
    for p in glob.glob(os.path.join(outdir, "*.jsonl")):
        for line in io.open(p, encoding="utf-8", errors="replace"):
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            key = (r.get("model"), r.get("condition"))
            rows[key] += 1
            if r.get("seed") is not None:
                seeds[key].add(r["seed"])
    if not by_seed:
        return rows
    got = collections.Counter()
    for key, n in rows.items():
        got[key] = len(seeds[key]) if seeds.get(key) else n
    return got


def verify(outdir, panel, strict=False):
    """Did anything drift from the frozen spec? Reports, and returns a failure count."""
    bad, seen = [], collections.Counter()
    cell_runs = collections.defaultdict(list)
    # THE FROZEN SPEC BINDS THE FROZEN PANEL. `wave-panel.json` carries two rosters: 36
    # models frozen 2026-09-05 under `params`, and a `breadth` extension of 22 declared
    # 2026-09-18 and collected afterwards, deliberately at its own parameters. Both land in
    # this directory. Checking the extension against the wave's frozen spec produced twelve
    # PARAMETER DRIFT lines for `aion-labs/aion-3.0-mini` -- max_tokens and seed window --
    # describing a model that was never collected under that spec and was never meant to be.
    # A gate that reports a declared extension as drift is a gate that gets read as noise,
    # and the frozen panel's own conformance is still checked in full below.
    extension = {m for m in (panel.get("breadth") or []) if m not in (panel.get("models") or [])}
    declared = []
    for p in glob.glob(os.path.join(outdir, "*.jsonl")):
        for line in io.open(p, encoding="utf-8", errors="replace"):
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            seen[(r.get("model"), r.get("condition"))] += 1
            cell_runs[(r.get("model"), r.get("condition"))].append(r)
            if r.get("model") in extension:
                declared.append((r.get("model"), r.get("condition")))
                continue
            for key, want in panel["params"].items():
                if key in ("runs", "seed_sweep"):
                    continue          # a count and a rule, not per-record fields
                if key == "seed_base":
                    # THE RULE IS "SWEEP", NOT "SWEEP FROM THIS ONE NUMBER". A single global
                    # `seed_base` cannot describe a wave collected in passes, and this one
                    # was: 361 records at 20260830, then four later passes each sweeping
                    # consecutive seeds from its own base (20260926-29, 20260930+20260937-39,
                    # 20260940-41+20260948-49, 20260950-52). Checked against one window, 3,536
                    # of 3,897 records read as PARAMETER DRIFT -- 91% of the corpus flagged as
                    # incomparable when what actually happened is that collection took more
                    # than one day.
                    #
                    # What the design fixes, and what is checked instead, is per CELL: five
                    # runs at DISTINCT seeds, so no cell is five copies of one draw. That is
                    # the property the sweep exists for and the one the duplicate-runs bug
                    # violated. The bases observed are reported below rather than gated.
                    continue
                got = r.get(key)
                # A DECLARED DEVIATION IS NOT DRIFT. `params_accepted` lists the other
                # values a parameter may carry, each one declared in PROTOCOL-DEVIATIONS.md
                # with the evidence that it cost nothing -- for max_tokens, the 120 records
                # of the pass run_battery refused partway, measured not truncated. Anything
                # NOT listed still fails, so this accepts a specific declared value rather
                # than switching the check off.
                accepted = (panel.get("params_accepted") or {}).get(key) or []
                if got is not None and got != want and got not in accepted:
                    bad.append("%s %s: %s=%r, frozen spec says %r"
                               % (r.get("model"), r.get("condition"), key, got, want))
    # ADOPTED CELLS ARE COLLECTED, and --verify has to know that or it reports 98 of 124
    # "missing" for a wave that is complete. Same blind spot as --run had: the wave directory
    # is not the whole wave when part of it was adopted from the corpus.
    adopted = set()
    if os.path.exists(BASELINE_FILE):
        base = json.load(io.open(BASELINE_FILE, encoding="utf-8"))
        still = {tuple(x.split("|", 1)) for x in base.get("missing", [])}
        adopted = {(m, c) for m in panel["models"] for c in ALL_CONDITIONS
                   if (m, c) not in still}
    missing = [(m, c) for m in panel["models"] for c in ALL_CONDITIONS
               if not seen.get((m, c)) and (m, c) not in adopted]

    # A CELL WHOSE RUNS SHARE ONE SEED IS NOT n RUNS. Under the pre-2026-09-05 spec, 17 of 32
    # cells with three or more runs held two or fewer distinct answer sheets. Verification has
    # to catch that structurally, or the spec change that fixed the collector leaves the old
    # data looking valid: every one of those records carries seed 20260830, which sits inside
    # the swept window and passes a range check.
    #
    # AND IT COUNTS *VALID* RUNS, which it did not until 2026-09-06.
    #
    # Two holes, both found by review. (a) The test was `n < min(len(rs), runs)`, so a cell
    # holding 10 records across 5 seeds passed on `5 < 5` -- duplicates were invisible whenever
    # the record count exceeded the target. (b) It never read `valid`, so a cell could reach
    # five distinct seeds on records that carry no answer sheet. Measured on wave 0: 22 cells
    # carried a duplicate seed among their VALID runs while this reported the wave clean.
    #
    # An invalid run is not a sample. Sample size is DISTINCT SEEDS AMONG VALID RUNS, and that
    # is what a cell has to reach.
    # DRIFT vs SAMPLE SIZE -- two findings, and only one of them can be fixed by collecting.
    #
    # Drift (a fixed seed, a changed parameter) makes the wave incomparable and is a blocker.
    # A short cell mostly is not: 9 cells produced NO valid run because the model declined the
    # balance instruction, which is section 1's headline rather than a collection failure, and
    # re-running a model that refuses gets another refusal. Gating on that is how you end up
    # with a permanently red pipeline that everyone learns to ignore -- the thing this repo
    # already fixed once by refusing to wire the truncation scan until it could pass.
    #
    # So shortfalls and duplicate draws print, and `--strict` gates them for an audit pass.
    # THREE OUTCOMES, NOT TWO, AND ONLY ONE OF THEM IS A SHORTFALL.
    #
    # `short` used to carry both "fewer distinct seeds than wanted" and "the target number of
    # distinct seeds, plus duplicate draws". The second is NOT SHORT: a cell with 10 valid runs
    # across 5 distinct seeds has sample size 5 and meets its target exactly. It was being
    # counted as a shortfall and would have failed --strict on cells that are fine, which is
    # the mirror image of a gate that passes by not looking -- a gate that fails by
    # miscounting. 31 cells were reported "not n=5" in wave 0 and a large share of them were
    # this.
    #
    # The duplicate draws are real and worth disclosing: they come from repairing the
    # seed-restart defect, which ADDED the missing positions without removing the duplicated
    # ones. The floors dedupe by seed (`load(dedupe_by_seed=True)`), so they change no number.
    # Disclosure, not a failure.
    empty, short, dupes = [], [], []
    if panel["params"].get("seed_sweep"):
        want = panel["params"]["runs"]
        for (m, c), rs in sorted(cell_runs.items()):
            valid = [r for r in rs if r.get("valid")]
            if not valid:
                # Every run refused or failed. That is the refusal series' finding, not drift.
                empty.append("%s %s" % (m, c))
                continue
            n = distinct_seeds(valid)
            if n < want:
                short.append("%s %s: %d valid run(s) over %d distinct seed(s) -- sample size "
                             "is %d, not %d" % (m, c, len(valid), n, n, want))
            elif len(valid) > n:
                dupes.append("%s %s: %d valid run(s) at %d seed(s) -- %d duplicate draw(s); "
                             "sample size IS %d, and the floors dedupe by seed"
                             % (m, c, len(valid), n, len(valid) - n, n))
    print("%s" % os.path.basename(outdir))
    print("  %d cell(s) present, %d panel cell(s) missing" % (len(seen), len(missing)))
    if empty:
        print("  %d cell(s) produced no valid run (refusal or failure, not drift): %s"
              % (len(empty), ", ".join(empty[:5]) + (" ..." if len(empty) > 5 else "")))
    if short:
        print("  SAMPLE SIZE -- %d cell(s) are SHORT of n=%d (prints; --strict gates):"
              % (len(short), panel["params"]["runs"]))
        for s in short[:8]:
            print("    %s" % s)
        if len(short) > 8:
            print("    ...and %d more" % (len(short) - 8))
    if dupes:
        print("  %d cell(s) MEET n=%d and also hold duplicate draws (disclosure, not a "
              "failure): the floors dedupe by seed, so no number moves"
              % (len(dupes), panel["params"]["runs"]))
        for s in dupes[:4]:
            print("    %s" % s)
        if len(dupes) > 4:
            print("    ...and %d more" % (len(dupes) - 4))
    # THE SWEEP, CHECKED AS A RULE AND REPORTED AS A STRUCTURE. A cell whose runs share one
    # seed is five copies of a single draw presented as n=5 -- the defect the sweep exists to
    # prevent -- and that IS gated. The bases themselves are printed so a reader can see the
    # collection ran in passes rather than wondering why the spec names one number.
    bases = collections.Counter()
    for (model, cond), recs in sorted(cell_runs.items()):
        cell_seeds = {r.get("seed") for r in recs if r.get("seed") is not None}
        for s in cell_seeds:
            bases[s] += 1
        # NOT GATED HERE, deliberately, and this comment is the reason rather than an
        # omission. A first version of this failed every cell whose runs shared one seed --
        # "one draw reported as five" -- which is a real defect in general and is ALREADY
        # reported, twenty lines down, as a disclosure: "the floors dedupe by seed, so no
        # number moves". The sample size those cells contribute is the count of DISTINCT
        # seeds, not the count of records, and `floor_table` enforces that. Gating it here
        # would have overturned a policy decision somebody made on purpose, by adding a
        # second check that looked like a new finding.
    if bases:
        shown = sorted(bases)
        print("  SEED SWEEP -- %d distinct seed(s) across the wave, collected in passes:"
              % len(shown))
        print("    %s" % ", ".join(str(s) for s in shown[:12])
              + (" ...and %d more" % (len(shown) - 12) if len(shown) > 12 else ""))
        print("    the frozen spec names one `seed_base`; a multi-pass collection has "
              "several, and what is gated is that no cell repeats a single seed.")

    if declared:
        # PRINTED, NOT DROPPED. An extension excused from the frozen spec has to be visible,
        # or "no drift" would quietly mean "drift not looked for".
        models = sorted({m for m, _c in declared})
        print("  DECLARED EXTENSION -- %d model(s), %d record(s), collected after the panel "
              "was frozen" % (len(models), len(declared)))
        print("  and not bound by its parameters (data/wave-panel.json `breadth`, declared "
              "2026-09-18):")
        for m in models[:6]:
            print("    %s" % m)
        if len(models) > 6:
            print("    ...and %d more" % (len(models) - 6))
    if bad:
        print("  PARAMETER DRIFT -- this wave is not comparable to the others:")
        for b in sorted(set(bad))[:12]:
            print("    %s" % b)
    if missing[:6]:
        print("  missing e.g.: %s" % ", ".join("%s/%s" % m for m in missing[:6]))

    # MISSING CELLS PRINTED AND NEVER GATED. The return was
    # `len(set(bad)) + (len(short) if strict else 0)` -- so a wave with panel cells that were
    # never collected at all exited 0, including under --strict, while the line above said how
    # many were missing. Printing a defect and returning success is the shape this project
    # keeps finding: `collected()` counting records against a verifier counting seeds, the
    # ablation collector's "0 remain" over twelve empty cells, and `check_no_fork` comparing
    # working trees while HEAD carried the divergence.
    #
    # A missing cell is not a refusal -- refusals land in `empty`, which stays ungated because
    # a cell whose runs all declined cannot be repaired by collecting more of them, and that
    # distinction is section 1's finding rather than a hole. A MISSING cell is work that did
    # not happen.
    #
    # Gated under --strict, alongside the sample-size shortfalls it belongs with. And the
    # verify output now SAYS which of its checks gate and which only print, because "verified"
    # over an unstated scope is how the default came to be read as a completeness check.
    failures = len(set(bad)) + (len(short) + len(missing) if strict else 0)
    print("  checks: parameter drift GATES%s"
          % ("; sample size and missing cells GATE (--strict)" if strict
             else "; sample size and missing cells PRINT ONLY -- pass --strict to gate them"))
    return failures


def series():
    """The two tracked quantities, wave over wave."""
    waves = wave_dirs()
    if not waves:
        print("no waves collected yet. There is no time axis until there are two.")
        return 1
    print("%-22s %8s %10s %14s %14s" % ("wave", "models", "records",
                                        "refusal A+B", "strong D (mean)"))
    for w in waves:
        rows = []
        for p in glob.glob(os.path.join(w, "*.jsonl")):
            for line in io.open(p, encoding="utf-8", errors="replace"):
                if line.strip():
                    try:
                        rows.append(json.loads(line))
                    except ValueError:
                        pass
        if not rows:
            continue
        ab = [r for r in rows if r.get("condition") in REFUSAL_CONDITIONS]
        ref = sum(1 for r in ab if r.get("failure_mode") == "refused")
        d = [r for r in rows if r.get("condition") == "D" and r.get("answers")]
        # STRONG is position 0 or 3 (Strongly Disagree / Strongly Agree). The scale is
        # 0=SD 1=D 2=A 3=SA, so  -- which this was -- counts AGREE and
        # calls it strong. It also produced a published finding that said the exact opposite
        # of the data: on the 2026-09-05 frontier set it gave qwen -2.2 and glm -1.9
        # ("the intensity claim inverts") where the correct definition gives +14.2 and +12.9.
        strong = [sum(1 for a in r["answers"] if a.get("position") in (0, 3)) for r in d]
        print("%-22s %8d %10d %13s %14s"
              % (os.path.basename(w), len({r.get("model") for r in rows}), len(rows),
                 ("%d/%d" % (ref, len(ab))) if ab else "-",
                 ("%.1f" % (sum(strong) / float(len(strong)))) if strong else "-"))
    if len(waves) < 2:
        print("")
        print("One wave is a baseline, not a series. The second one is what makes the first")
        print("mean anything, and the interval between them is the resolution.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--freeze-panel", action="store_true")
    ap.add_argument("--adopt-baseline", action="store_true",
                    help="declare wave 0 from corpus records that already match the spec")
    ap.add_argument("--force", action="store_true", help="with --freeze-panel, redefine it")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--verify", nargs="?", default="", const=ALL_WAVES,
                    help="wave directory name to verify; bare --verify checks EVERY wave")
    ap.add_argument("--strict", action="store_true",
                    help="also gate on sample size: cells short of n runs, or holding "
                         "duplicate draws. Off by default because a cell whose runs all "
                         "REFUSED cannot be repaired by collecting more of them.")
    ap.add_argument("--series", action="store_true")
    ap.add_argument("--date", default="", help="wave date (default: today)")
    ap.add_argument("--delay", type=float, default=2.0)
    ap.add_argument("--limit", type=int, default=0, help="stop after N cells")
    args = ap.parse_args(argv)

    # THIS COLLECTOR IS SUPERSEDED. Its verification, panel and series helpers are imported by
    # four other scripts and stay; its COLLECTION path must not run.
    #
    # It writes to `runs/<date>-wave/`, which is the live `runs/*-wave/*.jsonl` glob that every
    # floor arm reads, under the 2026-09-05 protocol: 5 runs per cell, an 8,192 token cap, one
    # item order. The current design is 4 conditions x 3 shuffle seeds at 40,960, collected by
    # `run_i3_wave.py`. Invoking this would drop sheets of a DIFFERENT PROTOCOL, on the same
    # instrument, into the same directory the arms pool from -- and nothing downstream carries
    # a protocol column, so the two would be indistinguishable once written.
    #
    # It also predates every pre-collection gate: no instrument sign-off, no budget
    # precondition, no gate registry.
    if args.run:
        print("REFUSING TO COLLECT -- wave.py's collector is superseded.")
        print("")
        print("It writes the 2026-09-05 protocol (5 runs/cell, 8,192 tokens, one item order)")
        print("into runs/<date>-wave/, which is the glob every floor arm reads. The current")
        print("design is N/A/P/D x shuffle seeds 11/22/33 at 40,960 tokens, and the two are")
        print("indistinguishable once they are in the same directory.")
        print("")
        print("Collect with:  python scripts/run_i3_wave.py --run")
        print("This file's panel, series and verification helpers are unaffected.")
        return 2

    if args.freeze_panel:
        freeze_panel(force=args.force)
        return 0
    if args.series:
        return series()

    panel = load_panel()
    if args.adopt_baseline:
        adopt_baseline(panel, force=args.force)
        return 0
    if args.verify:
        # Bare `--verify` checks every wave present. A CI line that names one wave id goes
        # stale the moment wave 1 lands, and stops checking the thing it was added for --
        # the hardcoded-include-list defect this project has already paid for twice (see
        # test_analysis_plumbing.py, `floor_table`'s run directories).
        if args.verify == ALL_WAVES:
            waves = wave_dirs()
            if not waves:
                print("no waves collected yet")
                return 0
            bad = 0
            for d in waves:
                bad += 1 if verify(d, panel, args.strict) else 0
            print("")
            print("%d wave(s) checked, %d with findings" % (len(waves), bad))
            return 1 if bad else 0
        d = args.verify if os.path.isdir(args.verify) else os.path.join(STUDY, "runs", args.verify)
        if not os.path.isdir(d):
            raise SystemExit("no such wave: %s" % args.verify)
        return 1 if verify(d, panel, args.strict) else 0

    # A WAVE IS A SITTING, NOT A CALENDAR DAY, and this defaulted to today().
    #
    # A full wave is 124 cells and takes hours. On 2026-09-06 at 00:25 the collection crossed
    # midnight mid-run and the next invocation opened `2026-09-06-wave` alongside the
    # `2026-09-05-wave` it had been filling -- 17 cells in one directory, 4 in the other.
    # `wave_dirs()` globs `*-wave`, so the series would have read those as TWO waves 25 minutes
    # apart: a fabricated first interval, in the one structure whose whole purpose is a clean
    # time axis. It is the same failure that put a phantom value in the manipulation floor.
    #
    # So: continue the most recent wave while it is unfinished, and only start a new one when
    # the last is complete or `--date` says so explicitly.
    if args.date:
        date = args.date
    else:
        date = datetime.date.today().isoformat()
        existing = wave_dirs()
        if existing:
            last = os.path.basename(existing[-1])[: -len("-wave")]
            # COMPLETE cells, not cells with anything in them. This read
            # `len(collected(...))`, which is the number of cells that hold ANY data -- so on
            # 2026-09-06 the previous sitting had all 124 cells touched, 11 of them short of
            # their five seeds, and this returned 124 < 124 == False and opened a second wave
            # directory mid-repair. The same shape as the seed-vs-record count it was called
            # to fix: a number that cannot distinguish present from finished.
            prior = collected(existing[-1])
            done = sum(1 for m in panel["models"] for c in ALL_CONDITIONS
                       if prior.get((m, c), 0) >= panel["params"]["runs"])
            if prior and done < len(panel["models"]) * len(ALL_CONDITIONS):
                date = last
    outdir = os.path.join(STUDY, "runs", "%s-wave" % date)
    have = collected(outdir) if os.path.isdir(outdir) else collections.Counter()

    # CELLS ADOPTED INTO WAVE 0 ARE ALREADY COLLECTED, and re-running them would be waste
    # dressed as rigour -- 101 of 128 on 2026-09-05. `--adopt-baseline` records which; without
    # consulting it, `--run` would recollect the whole panel and the tool's own first act would
    # be to violate the reason it exists.
    adopted = set()
    if os.path.exists(BASELINE_FILE):
        base = json.load(io.open(BASELINE_FILE, encoding="utf-8"))
        missing = {tuple(x.split("|", 1)) for x in base.get("missing", [])}
        adopted = {(m, c) for m in panel["models"] for c in ALL_CONDITIONS
                   if (m, c) not in missing}

    todo = [(m, c) for m in panel["models"] for c in ALL_CONDITIONS
            if (m, c) not in adopted and have.get((m, c), 0) < panel["params"]["runs"]]

    if args.plan or not args.run:
        print("WAVE %s -- panel frozen %s" % (date, panel["frozen"]))
        print("  %d model(s) x %d condition(s) = %d cell(s); %d already collected, %d to do"
              % (len(panel["models"]), len(ALL_CONDITIONS),
                 len(panel["models"]) * len(ALL_CONDITIONS), len(have), len(todo)))
        print("  frozen parameters: %s"
              % ", ".join("%s=%s" % kv for kv in sorted(panel["params"].items())))
        print("  ~%.0f min at %d runs/cell" % (len(todo) * panel["params"]["runs"] * 20 / 60.0,
                                               panel["params"]["runs"]))
        print("")
        print("  D and P carry the position series; A and B carry the refusal series.")
        return 0

    p = panel["params"]
    n = 0
    for (model, cond) in todo:
        if args.limit and n >= args.limit:
            break
        cmd = [sys.executable, os.path.join(HERE, "run_battery.py"),
               "--model", model, "--condition", cond,
               "--runs", str(p["runs"]), "--temperature", str(p["temperature"]),
               "--seed", str(p["seed_base"]), "--max-tokens", str(p["max_tokens"]),
               "--template", p["template"], "--channel", channel_for(model),
               "--delay", str(args.delay), "--out", outdir]
        if p.get("seed_sweep"):
            cmd.append("--seed-sweep")
        # The COLLECTOR is run_battery, not a reimplementation of it. Two collectors would be
        # two definitions of what a run is, and the wave would stop being comparable to every
        # other collection in this corpus.
        r = subprocess.run(cmd, capture_output=True, text=True)
        tail = [l for l in (r.stdout or "").splitlines() if "runs valid" in l]
        print("  %-34s %s %s" % (model[-34:], cond, tail[-1].split(":")[-1].strip()
                                 if tail else "(no result line)"))
        n += 1
    print("")
    print("collected %d cell(s); %d remain" % (n, len(todo) - n))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
