"""Every declared surface must be reachable by a flag, or it is silently unchecked.

WHY THIS FILE EXISTS
--------------------
`key_numbers.SURFACES` declares which documents carry generated numbers, and
`main()` decides which of them each `--check-*` flag actually visits. Those are
two lists, and the second is partly hardcoded: website and book surfaces are
picked up by name prefix, but `release` and `versioning` are named individually.

The code already warned about the gap in a comment:

    "Adding a surface to SURFACES and forgetting to add it here would leave it
     declared and unchecked, which is the same silence as not declaring it."

On 2026-09-15 that is exactly what happened, in the same session as the comment
was read. `ADVERSARIAL-REVIEW.md` was added to SURFACES so the RETRACTED scan
would cover it -- that file had answered seven objections using claims the study
later withdrew, and nothing gated it. A withdrawn claim was then planted in it to
verify the gate, and **the gate passed**, because no flag listed the new surface.

The mistake is cheap to make and invisible once made: the surface is declared,
the file exists, the scan is implemented, and nothing runs it. A comment cannot
fail a build. This can.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import key_numbers as K  # noqa: E402


def _reachable():
    """Surfaces some --check-* flag would visit, mirroring main()'s selection."""
    by_prefix = {n for n in K.SURFACES
                 if n.startswith("website") or n.startswith("dispatch-")
                 or n.startswith("book-")}
    # The individually-named ones. Kept as a literal on purpose: if main() gains
    # another, this list has to gain it too, and the test below is what says so.
    named = {"release", "versioning", "adversarial_review"}
    return by_prefix | named


def test_every_declared_surface_is_visited_by_some_flag():
    orphans = sorted(set(K.SURFACES) - _reachable())
    assert not orphans, (
        "declared in SURFACES and visited by no --check-* flag, so its numbers and "
        "its RETRACTED scan never run: %s" % orphans)


def test_every_visited_surface_is_actually_declared():
    """The other direction: a flag naming a surface that does not exist checks nothing."""
    ghosts = sorted(_reachable() - set(K.SURFACES))
    assert not ghosts, "named for checking but absent from SURFACES: %s" % ghosts


def test_the_adversarial_review_is_one_of_them():
    """The specific regression, named so it cannot be quietly dropped again.

    That document records which hostile objections were answered and why. Seven
    of its answers rested on claims withdrawn between 2026-09-04 and 2026-09-15,
    and a reviewer's first stop is the file that says the objections fail.
    """
    assert "adversarial_review" in K.SURFACES
    assert "adversarial_review" in _reachable()
    path = K.SURFACES["adversarial_review"]["path"]
    assert os.path.exists(path), path


def test_a_surface_may_gate_no_numbers_and_still_be_scanned():
    """An empty `phrases` dict is legitimate -- the RETRACTED scan is the point.

    Every figure in ADVERSARIAL-REVIEW.md is quoted from a result document that
    has its own gate. Restating them here would be the second copy this gate
    exists to prevent, so it declares no phrases and is still visited.
    """
    assert K.SURFACES["adversarial_review"]["phrases"] == {}
