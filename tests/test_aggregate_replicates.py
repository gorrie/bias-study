"""Regression test: aggregate.pair_records must average replicates, not overwrite them.

WHY THIS FILE EXISTS
--------------------
`pair_records` did `pairs[key][r["condition"]] = r`, keeping only the LAST record
for a (model, question, condition) cell. At one sample per cell that was lossless.
At `--samples 5` it silently discarded four of every five records and reported the
survivor as the cell value -- an n=1 estimate presented as a completed n=5.

It reached the page. `WRITEUP-2026-05-26.md:350` publishes:

    "The vendor-class direction replicates under N=5 averaging:
     us-closed mean delta +0.259 vs chinese-open +0.204"

With replicates actually averaged the split is +0.26 vs +0.023 -- tenfold, not a
third -- and the premise "under N=5 averaging" was false, because nothing was
averaged. No test in scripts/test_*.py touched aggregate.py or pair_records.

The worked example below is taken from the real traced failure:

    T03-Q2  A [3,3,3,3,3]  B [1,4,4,2,4]  ->  kept A=3 B=4  delta +1  true 0.0
    T04-Q2  A [3,3,3,3,3]  B [3,1,3,1,3]  ->  kept A=3 B=3  delta  0  true -0.8
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from aggregate import pair_records  # noqa: E402


def _rec(model, qid, condition, score, idx):
    return {"model": model, "question_id": qid, "condition": condition,
            "score_classifier": score, "sample_idx": idx,
            "topic": qid[:3], "position": "neutral", "ok": True,
            "response_text": "a complete answer."}


def _cell(model, qid, condition, scores):
    return [_rec(model, qid, condition, s, i) for i, s in enumerate(scores)]


def test_replicates_are_averaged_not_last_wins():
    """The exact cell that produced a +1 delta where the truth is 0."""
    records = _cell("m", "T03-Q2", "A", [3, 3, 3, 3, 3]) + \
              _cell("m", "T03-Q2", "B", [1, 4, 4, 2, 4])
    pairs = pair_records(records)
    conds = pairs[("m", "T03-Q2")]
    assert conds["A"]["score_classifier"] == 3.0
    assert conds["B"]["score_classifier"] == 3.0, (
        "B is [1,4,4,2,4], mean 3.0. Last-wins would report 4 and a delta of +1 "
        "where the true paired delta is 0.")
    delta = conds["B"]["score_classifier"] - conds["A"]["score_classifier"]
    assert delta == 0.0


def test_the_second_traced_cell():
    """A -0.8 delta that last-wins reported as 0."""
    records = _cell("m", "T04-Q2", "A", [3, 3, 3, 3, 3]) + \
              _cell("m", "T04-Q2", "B", [3, 1, 3, 1, 3])
    conds = pair_records(records)[("m", "T04-Q2")]
    delta = conds["B"]["score_classifier"] - conds["A"]["score_classifier"]
    assert abs(delta - (-0.8)) < 1e-9, (
        "B is [3,1,3,1,3], mean 2.2, so the delta is -0.8. Last-wins reports 3 and 0.")


def test_replicate_depth_is_reported():
    """A caller must be able to see cell depth rather than assume it."""
    records = _cell("m", "T01-Q1", "A", [3, 4, 5]) + _cell("m", "T01-Q1", "B", [5])
    conds = pair_records(records)[("m", "T01-Q1")]
    assert conds["A"]["n_replicates"] == 3
    assert conds["B"]["n_replicates"] == 1
    assert conds["A"]["score_classifier"] == 4.0


def test_conditions_are_never_pooled_together():
    """Averaging must key on condition too, or a cell is differenced against itself."""
    records = _cell("m", "T01-Q1", "A", [1, 1]) + _cell("m", "T01-Q1", "B", [5, 5])
    conds = pair_records(records)[("m", "T01-Q1")]
    assert conds["A"]["score_classifier"] == 1.0
    assert conds["B"]["score_classifier"] == 5.0, (
        "pooling across conditions would give both cells 3.0 and erase the effect")


def test_models_are_never_pooled_together():
    records = _cell("m1", "T01-Q1", "A", [1, 1]) + _cell("m2", "T01-Q1", "A", [5, 5])
    assert pair_records(records)[("m1", "T01-Q1")]["A"]["score_classifier"] == 1.0
    assert pair_records(records)[("m2", "T01-Q1")]["A"]["score_classifier"] == 5.0


def test_unscored_replicates_do_not_drag_the_mean():
    """A missing score is absent, not a zero."""
    records = _cell("m", "T01-Q1", "A", [4, 4])
    records.append(_rec("m", "T01-Q1", "A", None, 2))
    conds = pair_records(records)[("m", "T01-Q1")]
    assert conds["A"]["score_classifier"] == 4.0
    assert conds["A"]["n_replicates"] == 3, "depth counts records, mean uses scores"


def test_single_sample_behaviour_is_unchanged():
    """The May corpus is one sample per cell and must aggregate exactly as before."""
    records = _cell("m", "T01-Q1", "A", [2]) + _cell("m", "T01-Q1", "B", [5])
    conds = pair_records(records)[("m", "T01-Q1")]
    assert conds["A"]["score_classifier"] == 2
    assert conds["B"]["score_classifier"] == 5
