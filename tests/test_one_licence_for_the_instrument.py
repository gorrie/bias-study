"""The instrument's licence is stated in one way everywhere, or it is not stated.

WHY THIS FILE EXISTS
--------------------
On 2026-09-21 the author settled the licence: **MIT for everything in this study that is his
to license**, replacing a split (MIT for code, CC BY 4.0 for data and prose) that meant three
licences to comply with. `LICENSE` and both READMEs were updated.

Five other places still said CC BY 4.0 about the same 32 propositions:

    data/ratchet-battery.json        the instrument's own `source` field
    data/controls-audit.json         our row in the table that audits everyone else
    scripts/export_scrubbed.py       three times, in the script that produces the public data
    skills/study-operations/refresh.py
    bias-study-release/MANIFEST.json the shipped manifest

A licence stated in seven places drifts like any other fact stated in seven places
(LEARNINGS #10), and this one drifts into a legal claim about what a reader may do with the
work. The difference from a stale number is that nothing downstream recomputes it: there is
no generator, so the only thing that can hold these together is a check.

WHAT THIS DOES NOT DO. It does not police the two carve-outs, which are matters of ownership
rather than preference and are *correctly* not MIT: the retired 62-proposition questionnaire
is a third party's licensed work and is absent from the repository (`check_corpus.py` gates
that), and a vendor's terms govern the words their model emitted. Nor does it touch citations
of other people's CC BY work -- `rederive_liu.py` describes Liu et al.'s licence and is right
to.
"""
import io
import os
import re

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)

#: Files that describe THIS study's instrument, corpus or prose. A CC BY claim in one of
#: these is a claim about the author's own work and contradicts LICENSE.
SCOPED = (
    "data/ratchet-battery.json",
    "data/controls-audit.json",
    "scripts/export_scrubbed.py",
    "skills/study-operations/refresh.py",
    "README.md",
    "PAPER-no-position-only-consensus.md",
    "CITATION.cff",
)

#: Describing somebody else's licence is not a claim about ours.
ALLOWED_CONTEXT = re.compile(
    r"(Liu|Roettger|Röttger|Röttger|their|upstream|third[- ]party|external|"
    r"someone else|a third party's|completions \(CC-BY)", re.I)

CC_BY = re.compile(r"CC[- ]BY(?:[- ]SA)?(?:\s*4\.0)?", re.I)


def test_the_scoped_files_exist_so_this_gate_is_not_vacuous():
    present = [p for p in SCOPED if os.path.exists(os.path.join(STUDY, p))]
    assert len(present) >= 4, (
        "only %d of %d scoped files are present; this gate would pass having read almost "
        "nothing" % (len(present), len(SCOPED)))


def test_no_scoped_file_licenses_our_own_work_as_cc_by():
    offenders = []
    for rel in SCOPED:
        path = os.path.join(STUDY, rel)
        if not os.path.exists(path):
            continue
        text = io.open(path, encoding="utf-8", errors="replace").read()
        for m in CC_BY.finditer(text):
            line_no = text.count("\n", 0, m.start()) + 1
            line_start = text.rfind("\n", 0, m.start()) + 1
            line_end = text.find("\n", m.end())
            line = text[line_start:line_end if line_end > 0 else len(text)]
            if ALLOWED_CONTEXT.search(line):
                continue
            offenders.append("%s:%d  %s" % (rel, line_no, line.strip()[:120]))
    assert not offenders, (
        "%d place(s) license this study's own work as CC BY, against MIT in LICENSE:\n  %s\n"
        "Either correct them, or -- if the licence has genuinely changed -- change LICENSE "
        "and this test together, deliberately." % (len(offenders), "\n  ".join(offenders)))


def test_the_license_file_says_mit():
    path = os.path.join(STUDY, "LICENSE")
    if not os.path.exists(path):
        pytest.skip("no LICENSE in this tree")
    head = io.open(path, encoding="utf-8").read(400)
    assert "MIT License" in head, (
        "LICENSE no longer says MIT, so the check above is now asserting the wrong thing. "
        "Update both together.")
