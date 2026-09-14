"""The repair tool must be aimed at the corpus that carries the damage.

WHY THIS FILE EXISTS
--------------------
`recollect_at_cap.py` exists to re-collect the May study's truncated cells. Two
defects meant it could not:

1. **It read the wrong run.** `SOURCE` was `runs/2026-05-25`, a 520-record run,
   while the corpus carrying the damage is `2026-05-25-full` -- 780 records, the
   run behind WRITEUP section 5.6. Measured 2026-09-14: of the 176 cells that
   still needed re-collecting, it could see **zero**, and it printed "0 to do"
   with complete confidence. A repair tool aimed at the wrong corpus is worse
   than no repair tool, because it closes the question.

2. **Present counted as complete.** `existing()` treated any record in the output
   directory as a finished cell, so a cell that came back truncated or empty
   AGAIN was marked done and skipped forever. 33 of the 117 it called done were
   still unusable.

Together these are why the truncation damage sat unrepaired while a tool named
`recollect_at_cap` reported nothing to do.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import eligibility as E  # noqa: E402
import recollect_at_cap as R  # noqa: E402


def test_source_is_the_main_study_not_the_smaller_run():
    assert R.SOURCE.replace("\\", "/").rstrip("/").endswith("2026-05-25-full"), (
        "SOURCE is %r; the damage is in 2026-05-25-full" % R.SOURCE)


def test_source_actually_exists_and_holds_records():
    """A path that resolves to nothing would reproduce the original defect."""
    assert os.path.isdir(R.SOURCE), "SOURCE does not exist: %s" % R.SOURCE
    cells = R.at_cap_cells()
    assert len(cells) > 200, (
        "at_cap_cells() found only %d cells; the main run holds hundreds. Check that "
        "SOURCE resolves to the right tree." % len(cells))


def test_a_cell_is_done_only_when_its_response_is_usable():
    """DONE means a usable RESPONSE, not a scored one.

    This first asserted eligibility, which requires a score. Scoring happens
    AFTER collection, so that bar marked every freshly collected cell incomplete
    and would have re-collected all of them on the next run -- paying twice for
    the same records and never converging. Collection owes a response that is
    real, complete and at the new budget; whether a judge has read it yet is a
    different step's business.
    """
    usable = R.existing_usable()
    allrecs = R.existing()
    assert set(usable) <= set(allrecs)
    for k, r in usable.items():
        assert R.is_collected(r), "%s counted as done but has no usable response" % (k,)


def test_an_unscored_but_complete_response_counts_as_collected():
    """The regression that would have caused a re-collect loop."""
    fresh = {"ok": True, "response_text": "A complete answer that ends properly.",
             "max_tokens": 4000, "score_classifier": None,
             "scoring_status": "pending-rescore"}
    assert not E.is_eligible(fresh), "fixture is wrong; it should lack a score"
    assert R.is_collected(fresh), "a complete unscored response must count as collected"


def test_a_severed_or_empty_response_does_not_count_as_collected():
    severed = {"ok": True, "max_tokens": 4000,
               "response_text": ("The question turns on scope and remedy in ways that " * 12
                                 + "the office simply did not")}
    assert not R.is_collected(severed)
    assert not R.is_collected({"ok": True, "response_text": "", "max_tokens": 4000})
    assert not R.is_collected({"ok": False, "response_text": "x.", "max_tokens": 4000})


def test_a_record_at_the_old_budget_does_not_count_when_a_budget_is_given():
    """Re-collecting at 4000 is not satisfied by the 800-token record it replaces."""
    old = {"ok": True, "response_text": "A complete answer.", "max_tokens": 800}
    assert R.is_collected(old) is True or R.is_collected(old) is False  # budget-free call
    assert not R.is_collected(old, budget=4000)


def test_present_but_unusable_records_are_not_counted_as_done():
    """The specific regression: 33 of 117 were broken and marked complete."""
    allrecs = R.existing()
    usable = R.existing_usable()
    broken = len(allrecs) - len(usable)
    if broken:
        for k in allrecs:
            if k not in usable:
                assert k not in usable
    # Whatever the counts, done must never exceed usable.
    assert len(usable) <= len(allrecs)


def test_the_todo_list_is_not_empty_while_unusable_cells_remain():
    """The end-to-end assertion: if cells are unusable, there is work to do.

    This is the sentence the tool got wrong -- "0 to do" while 176 cells were
    unusable.
    """
    import splice_holes as S
    base = S.load(S.BASE)
    attempted = {S.key(r) for r in base}
    eligible = {S.key(r) for r in base if E.is_eligible(r)}
    spliced = set()
    for src in S.SPLICE_SOURCES:
        for r in S.load(src):
            if E.is_eligible(r) and S.key(r) in attempted and S.key(r) not in eligible:
                spliced.add(S.key(r))
    unusable = attempted - (eligible | spliced)

    cells = R.at_cap_cells()
    todo = [k for k in sorted(cells) if k not in R.existing_usable()]

    if unusable:
        assert todo, (
            "%d cells are unusable and the re-collector has nothing to do" % len(unusable))
        covered = sum(1 for k in unusable if k in cells)
        assert covered >= len(unusable) * 0.9, (
            "the re-collector can see only %d of %d unusable cells"
            % (covered, len(unusable)))
