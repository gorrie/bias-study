"""RELEASE-2026-09-07.md states how many checklist items are mechanical and how many are human.

Those two numbers were typed. They said eleven and five while `release_check.py` had grown to
eighteen and eight, so the release document under-reported its own rigour for five days and
nobody noticed -- the failure is small and it is the same shape as every other one this project
has had to correct: a count in prose that the code moved past.
"""
import io
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import release_check as R  # noqa: E402

DOC = ROOT / "RELEASE-2026-09-07.md"

# NOT APPLICABLE IN THE MIRROR. RELEASE-2026-09-07.md is a working-tree document; the
# public mirror does not carry it. Skipping is the honest outcome there, and it is
# deliberately a SKIP rather than a silent pass -- a test that reports success
# having found no subject is the defect this project keeps finding elsewhere.
pytestmark = pytest.mark.skipif(
    not DOC.exists(), reason="RELEASE-2026-09-07.md is not present in this tree (mirror)")


def text():
    return io.open(DOC, encoding="utf-8", errors="replace").read()


def test_the_split_sentence_matches_the_code():
    m = re.search(r"The split is (\d+) mechanical and (\d+) human", text())
    assert m, "RELEASE-2026-09-07.md must state the split so it can be checked"
    assert int(m.group(1)) == len(R.CHECKS), (
        "RELEASE-2026-09-07 says %s mechanical, release_check.CHECKS has %d"
        % (m.group(1), len(R.CHECKS)))
    assert int(m.group(2)) == len(R.HUMAN_CHECKS), (
        "RELEASE-2026-09-07 says %s human, release_check.HUMAN_CHECKS has %d"
        % (m.group(2), len(R.HUMAN_CHECKS)))


def test_the_all_pass_line_uses_the_same_number():
    """A stated pass-count must match the code. Stating no pass-count is allowed.

    This used to REQUIRE the sentence "all N mechanical items pass", which quietly
    forced the document to assert a green release. On 2026-09-13 that became false
    for a correct reason: the integrity pass changed the analysis, so the published
    documents no longer reproduce until they are regenerated, and release_check
    reports NOT RELEASABLE. A test that cannot express "the gate is red, correctly"
    pressures whoever hits it into restoring a claim that is not true.

    What must never happen is a STALE count -- the document saying "all 18 pass"
    while CHECKS holds 20. That is what this now guards.
    """
    m = re.search(r"all (\d+) mechanical items pass", text())
    if m is None:
        # No pass-claim made. Legitimate when the gate is red; the split-sentence
        # count is still asserted by the test above.
        return
    assert int(m.group(1)) == len(R.CHECKS), (
        "the summary line says %s mechanical items but release_check.CHECKS holds %d"
        % (m.group(1), len(R.CHECKS)))


def test_every_human_item_is_one_paragraph_not_a_run_on():
    """Implicit string concatenation without newlines renders as one mangled line."""
    for item in R.HUMAN_CHECKS:
        for line in item.split("\n"):
            assert len(line) <= 120, (
                "a HUMAN_CHECKS entry renders as an over-long line, which means its "
                "continuation strings are missing their newlines:\n  %.140s" % line)
