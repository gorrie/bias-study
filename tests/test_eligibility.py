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
    """ARITY 4 since 2026-09-13: truncation became its own exclusion class.

    Truncated records were previously eligible, which is how 21.5% of the corpus
    entered published aggregates as measurements. The bucket is separate from
    scored_empty because the remedies differ -- an empty response needs
    re-collection or exclusion, a severed one needs a bigger token budget.
    """
    recs = [rec(3, "a"), rec(3, ""), rec(None, ""), rec(4, "b"), rec(5, "  ")]
    e, se, tr, us = E.partition(recs)
    assert len(e) + len(se) + len(tr) + len(us) == len(recs)
    assert [id(x) for x in e + se + tr + us].count(id(recs[1])) == 1


def test_partition_separates_truncated_from_empty():
    long_severed = ("The question turns on scope and remedy in ways that " * 12
                    + "the office simply did not")
    recs = [rec(3, "A complete answer."), rec(3, ""), rec(3, long_severed)]
    e, se, tr, us = E.partition(recs)
    assert len(e) == 1 and len(se) == 1 and len(tr) == 1
    assert E.exclusion_reason(recs[2]) == "truncated-response"


def test_missingness_reports_per_model_and_condition():
    recs = [rec(3, "a", "gpt", "A"), rec(3, "", "gpt", "A"),
            rec(3, "b", "gpt", "B"), rec(None, "", "claude", "A")]
    m = E.missingness(recs)
    assert m[("gpt", "A")] == {"total": 2, "eligible": 1, "scored_empty": 1, "unscored": 0}
    assert m[("gpt", "B")]["eligible"] == 1
    assert m[("claude", "A")]["unscored"] == 1


def test_a_closed_latex_box_is_an_ending_not_a_severed_clause():
    r"""`llama-4-maverick` signs off "The final answer is: $\boxed{No}$".

    That ends on '$', so the detector called it severed -- 6 of its 7 records in
    the ood repair, which tripped collection_check's DIFFERENTIAL-truncation
    blocker at 85.7% against 0.0% elsewhere and refused the whole run.

    Counted before the detector was touched, the way the markdown-URL case was:
    NINE responses in 8,429 end this way, all llama-4-maverick, all in the ood
    arm, none within 95% of its cap -- 366 to 615 tokens of 4,000.
    """
    assert not E.looks_truncated_text(
        "Free trade has mixed effects.\n\nThe final answer is: $\\boxed{No}$")


def test_a_response_severed_inside_the_box_is_still_flagged():
    """The match requires the CLOSING brace, which is what keeps this narrow."""
    assert E.looks_truncated_text("The final answer is: $\\boxed{N")
    assert E.looks_truncated_text("The final answer is: $\\boxed{")
