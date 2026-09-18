"""The pre-registered Phase 4 estimator must actually read the corpus.

WHY THIS FILE EXISTS
--------------------
`scripts/position_analysis.py` is the estimator the instrument was designed for: position,
consistency and acquiescence over 16 mirrored pairs, written before the data deliberately so
it could not be shaped by the first numbers it saw. Its selftest passed eleven checks against
synthetic input from the day it was written.

Its `main()`, given any real run directory, printed:

    Phase 4 has not been collected yet; nothing to analyse in <dir>

and returned 2. There was no code path that read a record. The sentence was true when it was
written and stayed in place through four collection passes and 580 valid sheets.

Behind that stub sat two defects the selftest could never find, because the selftest supplies
its own input in its own shape:

  * `pair_index` read `item["pair_id"]`. The author's bank has `pair_no`. KeyError on the
    first item of the instrument this file is named for.
  * `cell_positions` and `acquiescence` iterate `rec["answers"].items()`, a mapping. The
    collector writes a LIST of `{"q": id, "position": value}`.

An estimator validated only against input it defines itself is validated against its own
assumptions. These tests use the real bank and the collector's real record shape.
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "scripts"))

import position_analysis as P  # noqa: E402


def _bank_ids():
    bank = P.load_bank()
    return bank, P.pair_index(bank)


def _sheet(model, condition, answers, seed=11):
    """A record in the shape run_battery actually writes."""
    return {
        "schema": "compass-run/1",
        "instrument": "ratchet-battery",
        "n_items": len(answers),
        "model": model,
        "condition": condition,
        "shuffle_seed": seed,
        "valid": True,
        "answers": [{"q": q, "position": p} for q, p in sorted(answers.items())],
    }


def _write(tmp_path, records):
    run = tmp_path / "runs" / "2026-09-16-planted"
    run.mkdir(parents=True)
    with io.open(str(run / "planted.jsonl"), "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")
    return run


def test_pair_index_reads_the_real_bank():
    """The field is pair_no. This raised KeyError on the live instrument."""
    bank, index = _bank_ids()
    assert len(index) == len(bank["items"]) == 32
    frames = {f for _p, f in index.values()}
    assert frames == {"critic", "defender"}, frames
    # 16 pairs, each with both halves -- the property every measure here depends on.
    import collections
    per_pair = collections.Counter(p for p, _f in index.values())
    assert len(per_pair) == 16, per_pair
    assert set(per_pair.values()) == {2}, "a pair does not have exactly two halves"


def test_records_are_read_in_the_collector_s_shape(tmp_path):
    """`answers` is a LIST of {q, position} on disk and a MAPPING in the estimator."""
    _bank, index = _bank_ids()
    ids = sorted(index)
    run = _write(tmp_path, [_sheet("v/m", "N", {q: (i % 4) for i, q in enumerate(ids)})])
    recs = P.load_records(str(run))
    assert len(recs) == 1, "the collector's record shape did not load"
    assert isinstance(recs[0]["answers"], dict)
    assert len(recs[0]["answers"]) == 32


def test_a_populated_run_directory_produces_a_result(tmp_path, capsys):
    """The stub's exact failure: a directory full of sheets reported as uncollected."""
    _bank, index = _bank_ids()
    ids = sorted(index)
    # A consistent skeptic: agrees with critic halves, disagrees with defender halves.
    answers = {q: (3 if index[q][1] == "critic" else 0) for q in ids}
    run = _write(tmp_path, [_sheet("v/m", c, answers) for c in ("N", "A", "P", "D")])
    rc = P.main([str(run)])
    out = capsys.readouterr().out
    assert rc == 0, out
    assert "Phase 4 has not been collected yet" not in out
    assert "CHECKED NOTHING" not in out
    # The selftest's own definition: a consistent skeptic scores +1.5 at 100% consistency.
    assert "+1.50 / 100%" in out, out


def test_an_empty_directory_is_not_a_result(tmp_path, capsys):
    run = tmp_path / "runs" / "empty"
    run.mkdir(parents=True)
    rc = P.main([str(run)])
    out = capsys.readouterr().out
    assert rc == 2
    assert "CHECKED NOTHING" in out, out


def test_a_degenerate_sheet_is_dropped_and_named(tmp_path, capsys):
    """Every item answered identically is position 0 and consistency 0 BY CONSTRUCTION.

    Left in, such a model enters the median as a confident perfect centrist that never made a
    discrimination. `mistral:7b-instruct-q8_0` answers Agree to all 32 items and was doing
    exactly that until 2026-09-17; floor_table had always dropped these, so the two analyses
    disagreed about which sheets are measurements.
    """
    _bank, index = _bank_ids()
    ids = sorted(index)
    flat = {q: 2 for q in ids}
    varied = {q: (3 if index[q][1] == "critic" else 0) for q in ids}
    run = _write(tmp_path, [_sheet("v/yeasayer", "N", flat),
                            _sheet("v/real", "N", varied)])
    recs = P.load_records(str(run))
    assert len(recs) == 1, "the degenerate sheet was not dropped"
    assert recs[0]["model"] == "v/real"
    assert P.load_records.dropped == {"v/yeasayer": 1}, P.load_records.dropped

    P.main([str(run)])
    out = capsys.readouterr().out
    assert "degenerate" in out and "yeasayer" in out, (
        "a dropped sheet must be named, not silently removed")


def test_the_mirror_cancels_a_pure_frame_follower(tmp_path):
    """The design's central claim: agree with whatever you are shown and you score zero.

    If this stops holding, the position measure is reporting frame agreement as a position and
    every number derived from it is describing the instrument rather than the model.
    """
    _bank, index = _bank_ids()
    ids = sorted(index)
    run = _write(tmp_path, [_sheet("v/agreeall", "N",
                                   {q: (3 if i % 2 else 2) for i, q in enumerate(ids)})])
    recs = P.load_records(str(run))
    pos, _cons = P.cell_positions(recs, index)
    # Every answer is on the agree side, so critic and defender agreement are equal per pair
    # only if the alternation lines up with frame; assert the weaker, always-true property.
    assert pos, "no pair positions computed"
    flat = _sheet("v/x", "N", {q: 3 for q in ids})
    flat_pos, flat_cons = P.cell_positions([{"model": "v/x", "condition": "N",
                                             "answers": {q: 3 for q in ids}}], index)
    assert all(abs(v) < 1e-9 for v in flat_pos.values()), (
        "a model agreeing equally with both halves must score exactly 0")
    assert all(v == 0 for v in flat_cons.values()), (
        "agreeing with a proposition and its negation is not consistency")
