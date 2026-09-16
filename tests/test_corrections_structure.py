"""Every numbered correction must sit under the heading that says what it is.

WHY THIS FILE EXISTS
--------------------
CORRECTIONS.md files its withdrawn claims as `### N.` entries under a `## The
retracted claims` heading. On 2026-09-16 six of them -- entries 19 through 24,
including the one withdrawing the study's own title -- were found sitting under
`## How to read this file`, a closing explainer that had drifted above them.

Nothing was missing and no text was wrong. A reader scanning headings for
withdrawn claims would simply have stopped at entry 18, because the section
appeared to end there. Misfiling is quieter than deleting and reads the same way
from outside.

The entries are also numbered by hand, so this checks they run 1..N without a gap
or a repeat: a skipped number reads as a correction that was removed.
"""
import io
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(ROOT, "CORRECTIONS.md")

ENTRIES_HEADING = "## The retracted claims"


def _not_here():
    """CORRECTIONS.md is a MIRROR document; the private study tree keeps none.

    This file is synced to both trees, so it has to say "not here" rather than fail
    where the ledger was never meant to exist. The mirror, which holds it, runs the
    real checks.
    """
    return not os.path.exists(DOC)


def _lines():
    return io.open(DOC, encoding="utf-8").read().split("\n")


def _entry_numbers_and_sections():
    """[(entry_number, the `## ` section it sits under)], in file order."""
    out, section = [], None
    for line in _lines():
        if line.startswith("## ") and not line.startswith("###"):
            section = line.strip()
        m = re.match(r"^###\s+(\d+)\.", line)
        if m:
            out.append((int(m.group(1)), section))
    return out


def test_there_are_entries_to_check():
    """A structural check over zero entries would pass while saying nothing."""
    if _not_here():
        return
    assert len(_entry_numbers_and_sections()) >= 20


def test_every_entry_sits_under_the_retracted_claims_heading():
    if _not_here():
        return
    misfiled = [(n, s) for n, s in _entry_numbers_and_sections() if s != ENTRIES_HEADING]
    assert not misfiled, (
        "correction entries filed under the wrong heading, so a reader scanning for "
        "withdrawn claims stops before them: %s" % misfiled)


def test_the_entries_are_numbered_without_a_gap_or_a_repeat():
    if _not_here():
        return
    numbers = [n for n, _ in _entry_numbers_and_sections()]
    assert numbers == sorted(numbers), "entries are out of order: %s" % numbers
    assert numbers == list(range(1, len(numbers) + 1)), (
        "entry numbers should run 1..%d with no gap or repeat; a gap reads as a correction "
        "that was removed. Got: %s" % (len(numbers), numbers))


def test_the_closing_explainer_comes_after_the_entries():
    if _not_here():
        return
    text = io.open(DOC, encoding="utf-8").read()
    how_to = text.index("## How to read this file")
    last_entry = max(m.start() for m in re.finditer(r"^###\s+\d+\.", text, re.M))
    assert how_to > last_entry, (
        "'How to read this file' sits above the last numbered entry, which is what put six "
        "corrections under it in the first place")
