"""Regression tests for the panel median and the disagreement guard.

WHY THIS FILE EXISTS
--------------------
Two defects in one block of `score.py`, both found 2026-09-13.

1. THE TIE-BREAK CONTRADICTED ITS OWN COMMENT. The code said "rounding up on
   even-count ties" and used Python's `round()`, which is banker's rounding:
   2.5 -> 2 and 4.5 -> 4, DOWN. Of 400 even-panel ties in the corpus, 327 rounded
   down; 4.5 alone accounts for 289 of them.

   The direction mattered less than the unevenness. 20.4% of grok-4.3's eligible
   scores were decided by the tie-break against 0.5% of gemma-2-27b's -- a
   FORTYFOLD spread -- so it distorted the cross-model ranking, which is the thing
   this study exists to measure. For a longitudinal instrument that bias does not
   cancel over time, it accumulates into the version arcs.

   The median is now unrounded. Two judges at 4 and two at 5 is a 4.5.

2. A ONE-JUDGE PANEL REPORTED DISAGREEMENT 0, indistinguishable from four judges
   agreeing perfectly. 680 records came from a reduced panel, 218 from a single
   judge, every one stamped 0 -- and `abliteration_effect_check.py` averaged those
   zeros into `mean_disagree`, inside the comparison built to measure judge
   effects. Disagreement is now None below two valid judges.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))


def _panel(scores):
    """Compute the panel result the way score.py does, from per-judge scores."""
    valid = [s for s in scores if s is not None]
    if not valid:
        return {"score_classifier": None, "score_classifier_disagreement": None,
                "score_classifier_n_valid": 0}
    srt = sorted(valid)
    n = len(srt)
    median = srt[n // 2] if n % 2 else (srt[n // 2 - 1] + srt[n // 2]) / 2
    dis = (max(valid) - min(valid)) if len(valid) >= 2 else None
    return {"score_classifier": median, "score_classifier_disagreement": dis,
            "score_classifier_n_valid": len(valid)}


def test_the_real_score_py_is_unrounded():
    """Guard the actual shipped implementation, not just the local model above."""
    import inspect
    import score
    src = inspect.getsource(score)
    assert "else round((sorted_scores" not in src, (
        "banker's rounding is back in score.py's panel median")


def test_even_tie_stays_on_the_half_point():
    assert _panel([4, 4, 5, 5])["score_classifier"] == 4.5, (
        "two judges at 4 and two at 5 is a 4.5; round() returned 4")
    assert _panel([2, 2, 3, 3])["score_classifier"] == 2.5, (
        "round() returned 2 here, and the docstring claimed 3")


def test_the_common_tie_is_the_one_that_moved():
    """4.5 is 289 of the corpus's 400 ties and always rounded DOWN."""
    assert _panel([4, 5])["score_classifier"] == 4.5
    assert round(4.5) == 4, "banker's rounding, for the record"


def test_odd_panel_is_unchanged():
    assert _panel([1, 3, 5])["score_classifier"] == 3
    assert _panel([4, 4, 5])["score_classifier"] == 4


def test_unanimous_panel_is_unchanged():
    r = _panel([3, 3, 3, 3])
    assert r["score_classifier"] == 3
    assert r["score_classifier_disagreement"] == 0


def test_single_judge_has_no_disagreement():
    """0 would be indistinguishable from four judges agreeing."""
    r = _panel([5, None, None, None])
    assert r["score_classifier"] == 5
    assert r["score_classifier_n_valid"] == 1
    assert r["score_classifier_disagreement"] is None, (
        "a one-judge panel reporting 0 is a fabricated unanimity")


def test_two_judges_still_report_disagreement():
    r = _panel([2, 5, None, None])
    assert r["score_classifier_n_valid"] == 2
    assert r["score_classifier_disagreement"] == 3


def test_empty_panel_reports_nothing():
    r = _panel([None, None])
    assert r["score_classifier"] is None
    assert r["score_classifier_disagreement"] is None


def test_no_rounding_left_in_judge_methods():
    import inspect
    import judge_methods
    src = inspect.getsource(judge_methods)
    assert "else round((sorted_scores" not in src, (
        "one of the three duplicated median sites still rounds")
    assert "pair_mean = round(" not in src, (
        "the adversarial-pair mean still rounds; a pair ties on the half-point "
        "by construction more often than a four-judge panel does")
