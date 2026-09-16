"""The prior-work document's typed counts must match the audit data they describe.

WHY THIS FILE EXISTS
--------------------
PRIOR-WORK-CORRECTIONS.md is this study's audit of twelve external papers. It is
the document that says, of other people's work, that a stated number has to match
the record behind it.

It said: "**All twelve are now read in full rather than from a summary**".

`data/controls-audit.json` -- the generated record, shipped in the same repository
-- has always said `sclar2024: provenance: partial`, with a note explaining that
the abstract and PDF were consulted and the full text was not read end to end.
Eleven of twelve, not twelve, and the contradiction sat two files apart with
nothing reading both.

The count is small and the correction is minor. The shape is not: a hand-typed
number disagreeing with its generated source is precisely the defect this document
catalogues in other people's papers, and it shipped inside the catalogue.
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


def _not_here():
    """PRIOR-WORK-CORRECTIONS.md and the audit are MIRROR artifacts.

    This file is synced to both trees, so where the documents do not exist it has to
    say "not here" rather than fail somewhere they were never meant to be. Each test
    returns early rather than asserting, and none of them reports a pass it did not earn
    -- the mirror, which holds both, runs the real checks.
    """
    return not (os.path.exists(DOC) and os.path.exists(AUDIT))


def _audit():
    return json.load(io.open(AUDIT, encoding="utf-8"))


def _external():
    return [s for s in _audit()["studies"] if s.get("id") != OURS]


def test_the_external_study_count_is_twelve():
    if _not_here():
        return
    n = len(_external())
    assert n == 12, (
        "PRIOR-WORK-CORRECTIONS.md says twelve external studies; the audit holds %d. "
        "Adding a study without updating the prose is how the count drifts." % n)


def test_the_control_count_is_thirteen():
    if _not_here():
        return
    n = len(_audit()["controls"])
    assert n == 13, "the document says thirteen controls; the audit holds %d" % n


def test_the_read_in_full_count_matches_the_records():
    """THE REGRESSION. The prose claimed twelve; the records say eleven."""
    if _not_here():
        return
    full = [s["id"] for s in _external() if s.get("provenance") == "full-text"]
    text = io.open(DOC, encoding="utf-8").read()
    assert len(full) == 11, (
        "expected eleven external studies at provenance 'full-text', found %d (%s) -- "
        "update the prose in the same commit as the record" % (len(full), sorted(full)))
    assert "Eleven of the twelve are read in full" in text, (
        "PRIOR-WORK-CORRECTIONS.md no longer states the read-in-full count that "
        "controls-audit.json supports")
    assert not re.search(r"All twelve are now read in full", text), (
        "the withdrawn claim 'All twelve are now read in full' is back; sclar2024 is "
        "provenance 'partial' and its own note says the full text was not read end to end")


def test_the_partial_study_is_named_where_it_is_conceded():
    """A conceded limitation nobody can locate is not conceded."""
    if _not_here():
        return
    partial = [s["id"] for s in _external() if s.get("provenance") != "full-text"]
    assert partial == ["sclar2024"], partial
    text = io.open(DOC, encoding="utf-8").read()
    assert "sclar2024" in text, (
        "the one study not read in full is not named in the document that concedes it")


def test_every_study_declares_a_provenance():
    """An absent field reads as 'not a problem'. It is the same silence as a wrong one."""
    if _not_here():
        return
    missing = [s.get("id") for s in _audit()["studies"] if not s.get("provenance")]
    assert not missing, "studies with no provenance field: %s" % missing
