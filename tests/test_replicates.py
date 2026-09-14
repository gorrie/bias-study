"""Replicates must be averaged within a cell, never overwritten.

WHY THIS FILE EXISTS
--------------------
`cells[(model, question_id)][condition] = record` keeps only the LAST sample. It
was correct when the May wave ran one sample per cell, and it became a silent
four-in-five data loss the moment `--samples 5` arrived. Nothing errors; the
output is a complete-looking table built from single draws.

It reached the page. `WRITEUP-2026-05-26.md:350` published a vendor-class split
"under N=5 averaging" where nothing had been averaged; regenerated, the two
classes sit on opposite sides of zero and deepseek-r1's delta reverses sign.

The bug shipped in six places and was fixed one call site at a time, which is how
the last three survived. These tests cover the shared implementation and the two
statistics that depend on it most.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import replicates as R  # noqa: E402


def rec(model="m", condition="B", qid="T01-Q1", score=3, **kw):
    r = {"model": model, "condition": condition, "question_id": qid,
         "score_classifier": score}
    r.update(kw)
    return r


# ------------------------------------------------------- the defect itself

def test_five_replicates_average_rather_than_last_wins():
    rows = [rec(score=s) for s in (1, 1, 1, 1, 5)]
    means, depth = R.cell_means(rows)
    key = ("m", "B", "T01-Q1")
    assert depth[key] == 5
    assert means[key] == 1.8, "got %r -- 5 would mean last-wins" % means[key]


def test_the_old_pattern_really_did_lose_four_records():
    """Negative control. Without it this suite proves only that mean() works."""
    rows = [rec(score=s) for s in (1, 1, 1, 1, 5)]
    old = {}
    for r in rows:
        old[(r["model"], r["question_id"])] = r["score_classifier"]
    assert old[("m", "T01-Q1")] == 5
    means, _ = R.cell_means(rows)
    assert means[("m", "B", "T01-Q1")] != old[("m", "T01-Q1")]


def test_the_key_carries_the_condition():
    """Pooling conditions differences a cell against itself."""
    rows = [rec(condition="A", score=3), rec(condition="B", score=5)]
    means, _ = R.cell_means(rows)
    assert means[("m", "A", "T01-Q1")] == 3
    assert means[("m", "B", "T01-Q1")] == 5
    assert len(means) == 2, "conditions were pooled into one cell"


def test_variant_conditions_do_not_pool():
    """B-STM, B-Parseltongue and B-Layered are different cells, not one B."""
    rows = [rec(condition=c, score=s)
            for c, s in (("B-STM", 1), ("B-Parseltongue", 3), ("B-Layered", 5))]
    means, _ = R.cell_means(rows)
    assert len(means) == 3


def test_depth_counts_what_was_averaged_not_what_was_present():
    """A depth that counts unusable records is the same lie in another column."""
    rows = [rec(score=3), rec(score=None), rec(score=5)]
    means, depth = R.cell_means(rows)
    assert depth[("m", "B", "T01-Q1")] == 2
    assert means[("m", "B", "T01-Q1")] == 4


def test_a_predicate_filters_before_grouping():
    rows = [rec(score=1, ok=False), rec(score=5, ok=True)]
    means, depth = R.cell_means(rows, predicate=lambda r: r.get("ok"))
    assert depth[("m", "B", "T01-Q1")] == 1
    assert means[("m", "B", "T01-Q1")] == 5


def test_no_predicate_by_default():
    """Eligibility policy belongs to the caller, not to this module."""
    rows = [rec(score=1, ok=False), rec(score=5, ok=True)]
    _means, depth = R.cell_means(rows)
    assert depth[("m", "B", "T01-Q1")] == 2


def test_empty_input_yields_empty_not_an_exception():
    means, depth = R.cell_means([])
    assert means == {} and depth == {}


# ------------------------------------------------------- representatives

def test_representative_carries_the_mean_and_the_depth():
    rows = [rec(score=s, response_text="r%d" % s) for s in (1, 1, 1, 1, 5)]
    reps = R.representative_records(rows)
    rep = reps[("m", "B", "T01-Q1")]
    assert rep["score_classifier"] == 1.8
    assert rep["n_replicates"] == 5
    assert rep["response_text"] == "r5", "a representative must stay a real record"


def test_representative_does_not_mutate_its_input():
    rows = [rec(score=1), rec(score=5)]
    R.representative_records(rows)
    assert rows[0]["score_classifier"] == 1
    assert "n_replicates" not in rows[0]


def test_a_cell_with_no_usable_score_is_present_but_unusable():
    """Absent would hide the cell; a zero would let it be averaged in."""
    rows = [rec(score=None), rec(score=None)]
    rep = R.representative_records(rows)[("m", "B", "T01-Q1")]
    assert rep["score_classifier"] is None
    assert rep["n_replicates"] == 0


def test_representative_accepts_a_custom_key():
    rows = [rec(qid="T01-Q1", score=1), rec(qid="T01-Q1", score=5)]
    reps = R.representative_records(rows, key_fields=("question_id", "condition"))
    assert set(reps) == {("T01-Q1", "B")}
    assert reps[("T01-Q1", "B")]["score_classifier"] == 3


def test_depth_summary_reports_raggedness():
    assert R.depth_summary({"a": 5, "b": 5}) == ([5], False)
    assert R.depth_summary({"a": 5, "b": 3}) == ([3, 5], True)


# ------------------------------------------------------- the call sites

def test_analysis_topic_heatmap_averages_replicates():
    import analysis
    rows = []
    for s in (1, 1, 1, 1, 5):
        rows.append(rec(condition="B", score=s, topic="T01"))
    rows.append(rec(condition="A", score=3, topic="T01"))
    heat = analysis.topic_heatmap(rows)
    # B mean 1.8 against A 3.0 -> -1.2. Last-wins would give 5 - 3 = +2.0.
    assert heat["m"]["T01"] == -1.2, "got %r" % heat["m"]["T01"]


def test_analysis_topic_heatmap_would_have_reported_the_last_draw():
    """The same data under the old rule, to show the size of the error."""
    import analysis
    rows = [rec(condition="B", score=s, topic="T01") for s in (1, 1, 1, 1, 5)]
    rows.append(rec(condition="A", score=3, topic="T01"))
    assert analysis.topic_heatmap(rows)["m"]["T01"] != 2.0


def test_abliteration_load_averages_replicates(tmp_path):
    import json
    import abliteration_effect_check as A
    p = tmp_path / "arm.jsonl"
    with p.open("w", encoding="utf-8") as fh:
        for s in (1, 1, 1, 1, 5):
            fh.write(json.dumps(rec(score=s, response_text="text %d" % s)) + "\n")
    loaded = A.load(p)
    assert set(loaded) == {("T01-Q1", "B")}
    assert loaded[("T01-Q1", "B")]["score_classifier"] == 1.8
    assert loaded[("T01-Q1", "B")]["n_replicates"] == 5


def test_abliteration_load_on_a_missing_file_is_empty():
    import abliteration_effect_check as A
    from pathlib import Path
    assert A.load(Path("does-not-exist-9999.jsonl")) == {}
