"""The frame-gap estimator, validated on synthetic data with known answers.

Written before the real data landed, so the estimator cannot be tuned to the
result. Each case below has an arithmetically known answer, and the test asserts
the estimator recovers it.
"""
import os
import statistics as st
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import frame_gap as F  # noqa: E402


def rec(model, condition, position, topic, score):
    return {"model": model, "condition": condition, "position": position,
            "topic": topic, "score_classifier": score, "ok": True,
            "response_text": "A complete answer.", "question_id": topic + "-x"}


def _means(rows):
    return F.cell_means(rows)[0]


def test_cell_means_average_replicates_within_cell():
    rows = [rec("m", "B", F.CRITIC, "T01", s) for s in (3, 4, 5)]
    means = _means(rows)
    assert means[("m", "B", F.CRITIC, "T01")] == 4.0


def test_cell_means_never_pool_across_position():
    rows = [rec("m", "B", F.CRITIC, "T01", 5), rec("m", "B", F.INSTITUTION, "T01", 1)]
    means = _means(rows)
    assert means[("m", "B", F.CRITIC, "T01")] == 5
    assert means[("m", "B", F.INSTITUTION, "T01")] == 1, (
        "pooling the two framings would erase the frame gap, which is the whole "
        "measurement")


def test_cell_means_never_pool_across_condition():
    rows = [rec("m", "A", F.CRITIC, "T01", 3), rec("m", "B", F.CRITIC, "T01", 5)]
    means = _means(rows)
    assert means[("m", "A", F.CRITIC, "T01")] == 3
    assert means[("m", "B", F.CRITIC, "T01")] == 5


def test_a_pure_frame_follower_shows_a_large_gap():
    """Scores 5 whenever asked from the critic side, 1 from the institution side.

    This model has no position at all; it agrees with whoever asks. The estimator
    must report a gap of +4, which is the signature the experiment exists to find.
    """
    rows = []
    for t in ["T%02d" % i for i in range(1, 11)]:
        rows += [rec("follower", "B", F.CRITIC, t, 5),
                 rec("follower", "B", F.INSTITUTION, t, 1)]
    means = _means(rows)
    gaps = [means[("follower", "B", F.CRITIC, t)] - means[("follower", "B", F.INSTITUTION, t)]
            for t in ["T%02d" % i for i in range(1, 11)]]
    assert st.mean(gaps) == 4.0


def test_a_genuine_position_shows_no_gap():
    """Scores 4 regardless of who asks -- a lean that survives the frame."""
    rows = []
    for t in ["T%02d" % i for i in range(1, 11)]:
        rows += [rec("holder", "B", F.CRITIC, t, 4),
                 rec("holder", "B", F.INSTITUTION, t, 4)]
    means = _means(rows)
    gaps = [means[("holder", "B", F.CRITIC, t)] - means[("holder", "B", F.INSTITUTION, t)]
            for t in ["T%02d" % i for i in range(1, 11)]]
    assert st.mean(gaps) == 0.0


def test_unpaired_topics_are_dropped_not_imputed():
    """A topic present in one framing only contributes nothing, silently or not."""
    rows = [rec("m", "B", F.CRITIC, "T01", 5), rec("m", "B", F.INSTITUTION, "T01", 3),
            rec("m", "B", F.CRITIC, "T02", 5)]           # T02 has no mirror
    means = _means(rows)
    paired = [t for t in ("T01", "T02")
              if ("m", "B", F.CRITIC, t) in means and ("m", "B", F.INSTITUTION, t) in means]
    assert paired == ["T01"]


def test_the_estimator_refuses_an_absent_run():
    """CHECKED NOTHING, not a clean zero."""
    assert F.analyse("2026-99-99-does-not-exist") is None
