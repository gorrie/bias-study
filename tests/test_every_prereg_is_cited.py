"""Every pre-registration and every results document must be reachable from the paper.

WHY THIS FILE EXISTS
--------------------
On 2026-09-21 the repository held 13 pre-registrations and 6 results documents.
The paper cited exactly ONE of them. A reader who wanted to get from a claim in
the paper to the record that establishes it had no route, and two of those
documents carried findings the paper made no mention of at all -- among them the
numbering artifact, which was measured on 2026-09-18, fixed in the collector the
same day, and still unpublished three days later.

The failure is not that a citation was forgotten. It is that nothing could
notice: the paper's completeness had no gate, so an arm could be collected,
analysed, written up and then not appear, and every other check in the project
would still pass. A study that argues the field should publish what it measures
cannot leave its own arms in a drawer.

This gate is deliberately weak in one direction and strict in the other. It does
not ask that a document be DISCUSSED -- that is a judgement, and a gate that
demands judgement gets switched off. It asks only that the paper NAME the file,
so a reader can follow it. Naming something the paper then argues is irrelevant
is a fine outcome; the reader can see the file and disagree.

EXEMPTIONS are declared here, by name, with a reason. A document that is a draft
for an instrument never collected, or that is superseded by another in the same
list, does not have to appear. There is no wildcard: a new file is IN until
somebody writes down why it is not, which is the direction that fails loudly.
"""
import glob
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
PAPER = os.path.join(STUDY, "PAPER-below-the-floor.md")

#: name -> why the paper need not name it. Keep the reason specific enough that a
#: reader can tell whether it still applies.
EXEMPT = {
    "PREREG-DRAFT-factions.md":
        "A draft for an instrument that was never collected. The paper names it in "
        "the provenance table anyway; this entry exists so the gate does not force "
        "it to if that paragraph is ever cut.",
}


#: The instrument changed on this date: the 62-proposition external questionnaire was retired
#: and the 32-item battery replaced it. A results document dated before it reports an arm on
#: an instrument this paper does not use, and demanding the paper cite it would be demanding
#: it cite another study. The public mirror files that archive in `results/` beside the
#: current write-ups, which is why the rule has to be stated rather than implied by location.
#:
#: The date is in the FILENAME, so this is a structural fact rather than a judgement about
#: content -- and it fails in the safe direction: a new document is IN by default.
INSTRUMENT_CHANGE = "2026-09-16"


def _current(name):
    m = re.search(r"(20\d\d-\d\d-\d\d)", name)
    return not m or m.group(1) >= INSTRUMENT_CHANGE


def _documents():
    """Every pre-registration and results document ON THE CURRENT INSTRUMENT, either layout.

    The study tree keeps them flat at the root; the public mirror files them under
    `prereg/` and `results/`. A glob written for one layout finds nothing in the other and
    the gate reports a clean pass over an empty set -- which is what happened the first time
    this ran in the mirror.
    """
    out = set()
    for directory in (STUDY, os.path.join(STUDY, "prereg"), os.path.join(STUDY, "results")):
        if not os.path.isdir(directory):
            continue
        for pattern in ("PREREG-*.md", "RESULTS-*.md"):
            out.update(os.path.basename(p) for p in glob.glob(os.path.join(directory, pattern)))
    return sorted(n for n in out if _current(n))


def test_the_gate_has_something_to_check():
    """A glob that matches nothing reports a clean pass over an empty set."""
    docs = _documents()
    assert len(docs) >= 10, (
        "only %d pre-registration/results documents found in %s -- the glob is wrong "
        "or the tree is not the study tree, and either way this gate checked nothing"
        % (len(docs), STUDY))


def test_every_prereg_and_result_is_named_by_the_paper():
    text = open(PAPER, encoding="utf-8").read()
    missing = [d for d in _documents() if d not in EXEMPT and d not in text]
    assert not missing, (
        "%d document(s) are not named anywhere in PAPER-below-the-floor.md, so a reader "
        "cannot get from the paper to the record:\n  %s\n"
        "Cite each in the provenance table under Reproduction, or add it to EXEMPT in "
        "this file with a reason." % (len(missing), "\n  ".join(missing)))


def test_exemptions_name_real_files():
    """A stale exemption silently un-gates a document that may since have been renamed."""
    present = set(_documents())
    stale = sorted(set(EXEMPT) - present)
    assert not stale, (
        "EXEMPT names %d file(s) that no longer exist: %s. An exemption for a missing "
        "file is an exemption nobody will notice is doing nothing."
        % (len(stale), ", ".join(stale)))
