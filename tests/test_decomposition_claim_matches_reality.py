"""The README's claim about what ships must match what ships.

WHY THIS FILE EXISTS
--------------------
Until 2026-09-16 the rung-2 section of README.md said, of the decomposition arm:

    "as of 2026-09-15 **its runs are in this repository**, so the numbers below
     recompute here rather than being asserted from a tree you cannot see"

and then published `B-Godmode +0.45 [+0.10, +0.78]`. The run
`2026-09-15-g0dm0d3-decomposition` was never in this repository. In a clone
`pipeline_decomposition.py` exits 2, no `B-Godmode` record exists under `data/`
or `runs/`, and the two tests covering the arm SKIP rather than fail.

The paragraph promising reproducibility was the one paragraph a reader could not
check, and nothing noticed, because the claim lived in prose and the absence
lived in the filesystem. Two copies of one fact, and only one of them was true.

This test holds them together in both directions. It is deliberately not a
one-way "the disclaimer is present" assertion: that would pass forever once the
run is exported and would quietly turn into a lie of the opposite sign.
"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README = os.path.join(ROOT, "README.md")

#: The decomposition run, named once. Both halves of the check read this.
DECOMP_RUN = "2026-09-15-g0dm0d3-decomposition"

#: The sentence the README must carry while the run is absent, and must NOT
#: carry once it is present. Short enough to survive rewording around it.
DISCLAIMER = "The decomposition run is not in this repository."

#: The claim that was wrong. It must never come back while the run is absent.
WITHDRAWN = "its runs are in this repository"


def _run_present():
    """True when the decomposition run is actually in this tree.

    Presence means a directory under either run root -- the repository has two
    (`data/` for the May study, `runs/` for the barometer), and a check that
    looked in only one would report absence for a run that shipped.
    """
    return any(os.path.isdir(os.path.join(ROOT, root, DECOMP_RUN))
               for root in ("data", "runs"))


def _readme():
    return io.open(README, encoding="utf-8").read()


def test_readme_discloses_the_absence_while_the_run_is_absent():
    if _run_present():
        return  # the other direction is asserted below
    text = _readme()
    assert DISCLAIMER in text, (
        "%s is not in this tree, so pipeline_decomposition.py exits 2 and the "
        "B-Godmode / B-Autotune figures cannot be recomputed from shipped data. "
        "README.md must say so where it states them. Expected to find: %r"
        % (DECOMP_RUN, DISCLAIMER))


def test_readme_drops_the_disclaimer_once_the_run_ships():
    if not _run_present():
        return
    text = _readme()
    assert DISCLAIMER not in text, (
        "%s IS in this tree now, so the README's 'NOT in this repository' "
        "disclaimer is false and understates what a replicator can check. "
        "Remove it and restore the reproducibility claim." % DECOMP_RUN)


def test_the_withdrawn_sentence_does_not_return():
    """The specific wording that shipped, named so it cannot come back by accident."""
    if _run_present():
        return
    text = _readme()
    assert WITHDRAWN not in text, (
        "README.md claims the decomposition runs are in this repository; they "
        "are not. This is ledger entry 24 and it shipped once already.")


def test_the_claim_is_recorded_in_the_corrections_ledger():
    """A correction that is not in the ledger is a correction a reader cannot find.

    CORRECTIONS.md is a MIRROR document -- the public ledger, which the private study tree
    does not carry. This file is synced to both trees, so the check has to say "not here"
    rather than fail somewhere the document was never meant to exist.
    """
    path = os.path.join(ROOT, "CORRECTIONS.md")
    if not os.path.exists(path):
        return  # not the tree that publishes the ledger
    ledger = io.open(path, encoding="utf-8").read()
    assert DECOMP_RUN in ledger, (
        "the decomposition-claim correction (entry 24) is missing from "
        "CORRECTIONS.md, which is where a reader looks for exactly this")
