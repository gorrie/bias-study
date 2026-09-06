"""Regression tests for the two counting defects that corrupted wave 2026-09-05.

WHY THIS FILE EXISTS
--------------------
Both defects are the same mistake in two places: a count that cannot tell PRESENT from
FINISHED. Neither raised anything. Both produced data that looked complete.

  1. RESUME RESTARTED THE SEED SWEEP.
     `run_compass.py` resumes correctly -- it counts valid runs on disk and asks only for the
     shortfall -- and then the collection loop restarted at `run_no = 1`. Under `--seed-sweep`
     the seed is a POSITION IN A SEQUENCE (run k carries seed_base + k), not a loop counter, so
     a cell interrupted after two runs re-issued seed_base + 0 and + 1: the two it already had.

     At temperature 0.7 a repeated seed is not a repeated call. The records differ, the cell
     reaches five, `valid` counts five. It is n=3. Measured on wave 2026-09-05: 11 of 124 cells
     held five to seven records across three or four distinct seeds, every one a cell some
     killed chunk had interrupted.

  2. `wave.collected()` COUNTED RECORDS, `--verify` COUNTED SEEDS.
     So the two disagreed about what was finished. `--verify` called eleven cells short while
     `--run` saw five records in each and skipped every one -- the gate could name the damage
     and the collector could not repair it. A cell is only repairable by the thing that decides
     what is left to do, so it has to count the same way.

  3. AND THE SITTING CHECK COUNTED TOUCHED CELLS.
     `wave.py` keeps a wave to one sitting by continuing yesterday's directory when it is
     unfinished. That test read `len(collected(...))` -- the number of cells holding ANY data.
     All 124 held data while 11 were short, so at 00:0x on 2026-09-06 it opened a second wave
     directory mid-repair and billed six duplicate cells before it was caught.

The rule these share, and the reason they are pinned together: SAMPLE SIZE IS DISTINCT SEEDS.
Any code path that answers "how much of this cell do I have" and counts rows instead is wrong,
and wrong in the direction that manufactures sample size.

    python scripts/test_wave_seeds.py
"""
from __future__ import annotations

import io
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import wave as W             # noqa: E402

SEED_BASE = 20260830


def _rec(model, cond, seed, **kw):
    r = {"model": model, "condition": cond, "seed": seed, "valid": True,
         "temperature": 0.7, "template": "T01", "shuffle_seed": None,
         "positions": [1] * 62}
    r.update(kw)
    return r


def _cell(outdir, model, cond, seeds):
    stem = model.replace("/", "__").replace(":", "_")
    path = os.path.join(outdir, "%s__%s.jsonl" % (stem, cond))
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        for s in seeds:
            fh.write(json.dumps(_rec(model, cond, s)) + "\n")
    return path


# ------------------------------------------------------- 1. collected() counts seeds

def test_collected_counts_distinct_seeds_not_records():
    """Five records over three seeds is n=3. This is the whole defect."""
    d = tempfile.mkdtemp()
    try:
        _cell(d, "acme/m1", "D", [SEED_BASE, SEED_BASE + 1, SEED_BASE + 2,
                                  SEED_BASE, SEED_BASE + 1])
        got = W.collected(d)
        assert got[("acme/m1", "D")] == 3, got[("acme/m1", "D")]
        # ...and the raw row count is still available, because the billing question
        # ("how many calls did this cost") is a different question from sample size.
        assert W.collected(d, by_seed=False)[("acme/m1", "D")] == 5
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_collected_falls_back_to_rows_when_no_seed_recorded():
    """Temperature-0 and pre-sweep collections carry no seed. Counting rows is right there,
    and returning 0 would make every one of them look uncollected."""
    d = tempfile.mkdtemp()
    try:
        path = _cell(d, "acme/m2", "A", [SEED_BASE])
        with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
            for _ in range(4):
                r = _rec("acme/m2", "A", None)
                r.pop("seed")
                fh.write(json.dumps(r) + "\n")
        assert W.collected(d)[("acme/m2", "A")] == 4
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_collected_and_verify_agree_about_what_is_short():
    """The gate and the collector must name the same cells. When they disagreed, --verify could
    report the damage and --run could not reach it."""
    d = tempfile.mkdtemp()
    try:
        _cell(d, "acme/m3", "D", [SEED_BASE, SEED_BASE + 1, SEED_BASE, SEED_BASE + 1,
                                  SEED_BASE + 2])
        by_collected = W.collected(d)[("acme/m3", "D")]
        recs = [json.loads(l) for l in io.open(
            os.path.join(d, "acme__m3__D.jsonl"), encoding="utf-8") if l.strip()]
        assert by_collected == W.distinct_seeds(recs) == 3
    finally:
        shutil.rmtree(d, ignore_errors=True)


# --------------------------------------------- 2. resume continues the sweep, not restarts it

def _next_offsets(seen, runs, base=SEED_BASE):
    """The selection rule from run_compass's collection loop, extracted so the test exercises
    the rule rather than a copy of it. Kept deliberately small; if it drifts from the caller,
    test_resume_offsets_match_run_compass below fails."""
    offsets, k = [], 0
    while len(offsets) < runs:
        if base + k not in seen:
            offsets.append(k)
        k += 1
        if k > runs + len(seen) + 16:
            break
    return offsets


def test_fresh_cell_sweeps_from_zero():
    assert _next_offsets(set(), 5) == [0, 1, 2, 3, 4]


def test_clean_resume_continues_the_sequence():
    """Two runs on disk, three to go: positions 2, 3, 4 -- NOT 0, 1, 2, which is what the loop
    did and which is what produced eleven short cells."""
    seen = {SEED_BASE, SEED_BASE + 1}
    assert _next_offsets(seen, 3) == [2, 3, 4]


def test_repair_of_a_damaged_cell_does_not_collide_again():
    """A cell already carrying duplicates holds a NON-CONTIGUOUS seed set. Offsetting by the
    record count would collide a second time while repairing; taking the next unused positions
    does not."""
    seen = {SEED_BASE, SEED_BASE + 1, SEED_BASE + 2}   # 5 records, 3 distinct
    assert _next_offsets(seen, 2) == [3, 4]


def test_resume_offsets_match_run_compass():
    """The rule above is a restatement. Assert the real collector agrees with it, so this file
    cannot pass while the shipped path regresses."""
    src = io.open(os.path.join(HERE, "run_compass.py"), encoding="utf-8").read()
    assert "if args.seed + k not in seen_seeds:" in src, \
        "run_compass no longer selects unused sweep positions -- resume may be restarting the sweep"
    assert "offsets[run_no - 1]" in src, \
        "run_compass's collection loop no longer uses the computed sweep offsets"
    assert "seen_seeds.add(rec[\"seed\"])" in src, \
        "run_compass no longer records which seeds are already on disk"


# ------------------------------------------------- 3. a wave is a sitting, measured correctly

def test_sitting_check_counts_complete_cells_not_touched_ones():
    """124 cells touched with 11 short is an UNFINISHED sitting. Counting keys said finished."""
    d = tempfile.mkdtemp()
    try:
        models = ["acme/m1", "acme/m2"]
        for m in models:
            for c in W.ALL_CONDITIONS:
                seeds = [SEED_BASE + i for i in range(5)]
                if (m, c) == ("acme/m2", "P"):
                    seeds = [SEED_BASE, SEED_BASE + 1, SEED_BASE, SEED_BASE + 1, SEED_BASE]
                _cell(d, m, c, seeds)
        prior = W.collected(d)
        # every cell is present...
        assert len(prior) == len(models) * len(W.ALL_CONDITIONS)
        # ...and the sitting is NOT finished.
        done = sum(1 for m in models for c in W.ALL_CONDITIONS if prior.get((m, c), 0) >= 5)
        assert done == len(models) * len(W.ALL_CONDITIONS) - 1, done
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_wave_py_uses_the_complete_count():
    src = io.open(os.path.join(HERE, "wave.py"), encoding="utf-8").read()
    assert "len(collected(existing[-1])) <" not in src, \
        "wave.py is back to counting cells that hold ANY data as a finished sitting"
    assert "done < len(panel[\"models\"]) * len(ALL_CONDITIONS)" in src, \
        "wave.py's sitting check no longer counts COMPLETE cells"


# ------------------------------------------------------------------ 4. the shipped wave

def test_wave_0_holds_five_distinct_seeds_everywhere():
    """The artifact, not the source. Skips when the wave is not present (a fresh clone)."""
    outdir = os.path.join(STUDY, "runs", "2026-09-05-wave")
    if not os.path.isdir(outdir):
        return
    got = W.collected(outdir)
    short = {k: v for k, v in got.items() if v < 5}
    assert not short, "cells below five distinct seeds: %s" % sorted(short.items())[:8]


if __name__ == "__main__":
    import traceback
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("ok    %s" % name)
            except Exception:
                failures += 1
                print("FAIL  %s" % name)
                traceback.print_exc()
    print()
    print("%d failure(s)" % failures)
    raise SystemExit(1 if failures else 0)
