"""DATA-EMPTY-SCORES-002: one eligibility rule, and the readers that must use it.

The defect these guard is narrow and easy to reintroduce: every reader filtered on
`score_classifier is not None`, which is exactly the filter an empty-but-scored record passes.
466 such records sit in the primary scored/ corpus and 81 more across the alternate judge
methods.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import eligibility as E  # noqa: E402


def rec(score, text, model="m", cond="A"):
    return {"score_classifier": score, "response_text": text, "model": model, "condition": cond}


def test_the_filter_every_reader_used_is_the_one_that_fails():
    scored_empty = rec(3, "")
    assert scored_empty["score_classifier"] is not None   # passes the OLD filter
    assert not E.is_eligible(scored_empty)                # fails the new one
    assert E.is_scored_empty(scored_empty)


def test_whitespace_only_is_empty():
    assert not E.is_eligible(rec(3, "   \n\t "))


def test_a_substantive_refusal_is_kept():
    """This rule removes records with nothing to read, NOT refusals. A refusal is a real
    response with real text and is one of the study's primary measurements -- dropping those
    would delete the finding rather than correct it."""
    assert E.is_eligible(rec(2, "I'm not able to help with that request."))
    assert E.is_eligible(rec(1, "No."))


def test_missing_score_is_neither_eligible_nor_the_defect():
    r = rec(None, "")
    assert not E.is_eligible(r)
    assert not E.is_scored_empty(r)


def test_partition_is_total_and_disjoint():
    recs = [rec(3, "a"), rec(3, ""), rec(None, ""), rec(4, "b"), rec(5, "  ")]
    e, se, us = E.partition(recs)
    assert len(e) + len(se) + len(us) == len(recs)
    assert [id(x) for x in e + se + us].count(id(recs[1])) == 1


def test_missingness_reports_per_model_and_condition():
    recs = [rec(3, "a", "gpt", "A"), rec(3, "", "gpt", "A"),
            rec(3, "b", "gpt", "B"), rec(None, "", "claude", "A")]
    m = E.missingness(recs)
    assert m[("gpt", "A")] == {"total": 2, "eligible": 1, "scored_empty": 1, "unscored": 0}
    assert m[("gpt", "B")]["eligible"] == 1
    assert m[("claude", "A")]["unscored"] == 1
