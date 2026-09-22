"""The prior-work document's typed counts must match the audit data they describe.

WHY THIS FILE EXISTS
--------------------
PRIOR-WORK-CORRECTIONS.md is this study's audit of the external papers. It is the document
that says, of other people's work, that a stated number has to match the record behind it.

It said: "**All twelve are now read in full rather than from a summary**".

`data/controls-audit.json` -- the generated record, shipped in the same repository -- has
always said `sclar2024: provenance: partial`, with a note explaining that the abstract and PDF
were consulted and the full text was not read end to end. Eleven of twelve, not twelve, and the
contradiction sat two files apart with nothing reading both.

The count is small and the correction is minor. The shape is not: a hand-typed number
disagreeing with its generated source is precisely the defect this document catalogues in other
people's papers, and it shipped inside the catalogue.

REWRITTEN 2026-09-20, BECAUSE THE FIRST VERSION HAD THE SAME DEFECT IT WAS CATCHING.
It asserted `n == 12`, `n == 13`, `len(full) == 11` -- three more hand-typed copies of the very
counts under test, in the file whose job is to stop hand-typed counts. Adding two studies and a
control to the audit turned all three red while nothing was wrong, and the "fix" available was
to retype three literals. Now every count is DERIVED from the audit and the assertion is that
the PROSE agrees, which is the only direction that was ever load-bearing.
"""
import io
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(ROOT, "PRIOR-WORK-CORRECTIONS.md")
AUDIT = os.path.join(ROOT, "data", "controls-audit.json")

#: Our own study sits in the same table as the external ones and is not one of them.
OURS = "ours"

#: Number words the prose uses. The documents spell counts out, so a digit comparison would
#: never match; this is the one place a mapping is unavoidable.
WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven",
         8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve", 13: "thirteen",
         14: "fourteen", 15: "fifteen", 16: "sixteen", 17: "seventeen", 18: "eighteen",
         19: "nineteen", 20: "twenty"}


def _not_here():
    """PRIOR-WORK-CORRECTIONS.md and the audit are MIRROR artifacts.

    This file is synced to both trees, so where the documents do not exist it has to say "not
    here" rather than fail somewhere they were never meant to be. Each test returns early
    rather than asserting, and none of them reports a pass it did not earn -- the mirror, which
    holds both, runs the real checks.
    """
    return not (os.path.exists(DOC) and os.path.exists(AUDIT))


def _audit():
    return json.load(io.open(AUDIT, encoding="utf-8"))


def _external():
    return [s for s in _audit()["studies"] if s.get("id") != OURS]


def _doc():
    return io.open(DOC, encoding="utf-8").read()


def _says(text, n):
    """Does the prose state this count, as a word or a digit?"""
    forms = [str(n)]
    if n in WORDS:
        forms.append(WORDS[n])
    return any(re.search(r"(?<![\w-])%s(?![\w-])" % re.escape(f), text, re.I) for f in forms)


def test_the_external_study_count_is_stated_and_correct():
    if _not_here():
        return
    n = len(_external())
    assert n > 0, "the audit holds no external studies at all -- that is not a pass"
    assert _says(_doc(), n), (
        "the audit holds %d external studies and PRIOR-WORK-CORRECTIONS.md does not state "
        "that count anywhere. Adding a study without updating the prose is how the count "
        "drifts -- update the prose in the same commit as the record." % n)


def test_the_control_count_is_stated_and_correct():
    if _not_here():
        return
    n = len(_audit()["controls"])
    assert n > 0, "the audit declares no controls -- that is not a pass"
    assert _says(_doc(), n), (
        "the audit declares %d controls and the document does not state that count" % n)


def test_the_read_in_full_count_matches_the_records():
    """THE ORIGINAL REGRESSION. The prose claimed twelve; the records said eleven."""
    if _not_here():
        return
    external = _external()
    full = sorted(s["id"] for s in external if s.get("provenance") == "full-text")
    text = _doc()
    assert full, "no external study is recorded as read in full -- that is not a pass"
    assert _says(text, len(full)), (
        "%d of %d external studies are at provenance 'full-text' (%s) and the document does "
        "not state that number" % (len(full), len(external), full))
    # The point of the sentence is the REMAINDER: which papers a verdict rests on less than a
    # full read. A count with no named exception is the half that goes stale invisibly.
    for s in external:
        if s.get("provenance") != "full-text":
            assert s["id"] in text, (
                "%r is not read in full and the document never names it. The count can be "
                "right while the reader cannot tell which paper is the weak one."
                % s["id"])
