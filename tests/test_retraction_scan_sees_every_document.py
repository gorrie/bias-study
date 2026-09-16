"""The retraction scan must read every document, and must not be evadable by formatting.

WHY THIS FILE EXISTS
--------------------
Until 2026-09-16 the RETRACTED scan ran only over the nine documents named in
`key_numbers.SURFACES`. That list exists to gate NUMBERS -- a handful of files
restate figures, so a hand-written list is right for them. Retractions are the
opposite shape: a claim this study withdrew is wrong in every file that asserts
it, and 84 of the repository's 93 markdown files were never scanned at all.

CORPUS-MAP-2026-09-14.md:112 was found asserting the rung-2 "two models move in
opposite directions" reading FOUR LINES above the block withdrawing it.

Three separate evasions were then found by planting claims and watching the gate
pass, which is the only way any of them surfaced:

  1. **Markdown emphasis.** `the two models move in **opposite directions**` does
     not contain the literal phrase. Emphasis is what a writer adds to the
     sentence they care most about, so the blind spot pointed straight at the
     claims that matter most.
  2. **Capitalisation.** The match was case-sensitive, so a phrase stored
     lowercase missed every sentence-initial "The ...". That is the ordinary form
     of a headline claim.
  3. **A 2,786-character paragraph.** The report printed `line[:110]`, so every
     hit inside one long paragraph displayed the same opening clause -- text with
     nothing to do with the retracted phrase, which read as a false positive and
     would have trained an operator to ignore the gate.

Two exemptions are deliberate and are tested here too, because an over-strict gate
gets switched off: a document marked SUPERSEDED at the top may contain its own
withdrawn claims (that is what an archive IS), and a claim struck through with
`~~` is being withdrawn in place, which is the clearest retraction markdown has.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import key_numbers as K  # noqa: E402

#: A real withdrawn claim, used verbatim so the test cannot pass against a phrase
#: the gate no longer carries.
CLAIM = "the lean is in the weights"


def _hits(text):
    return K._unquoted_occurrences(text, CLAIM)


def test_the_scan_walks_more_than_the_declared_surfaces():
    scanned, _, _ = K.scan_every_document_for_retractions()
    assert scanned > len(K.SURFACES), (
        "the retraction scan opened %d file(s) but the repository declares %d surfaces -- "
        "if those numbers are close the sweep has collapsed back onto the hand-written list"
        % (scanned, len(K.SURFACES)))


def test_a_scan_that_opened_nothing_is_not_a_pass():
    """The vacuous pass, guarded explicitly: 0 files examined must never exit 0."""
    real = K.scan_every_document_for_retractions
    K.scan_every_document_for_retractions = lambda: (0, [], [])
    try:
        assert K.check_retractions_everywhere() == 1
    finally:
        K.scan_every_document_for_retractions = real


def test_plain_assertion_is_caught():
    assert _hits("We show that the lean is in the weights, as predicted.")


def test_capitalised_assertion_is_caught():
    """Evasion 2. A sentence-initial capital is the normal way to state a headline claim."""
    assert _hits("The lean is in the weights.")


def test_emphasised_assertion_is_caught():
    """Evasion 1. Bold inside the phrase split it into something the gate could not see."""
    assert _hits("The lean is **in the weights**.")
    assert _hits("*The lean is in the weights.*")
    assert _hits("The lean is `in the weights`.")


def test_the_excerpt_shows_the_match_not_the_start_of_the_line():
    """Evasion 3. A finding an operator cannot read is a finding an operator ignores."""
    filler = "x" * 2000
    hit, = _hits(filler + " The lean is in the weights. " + filler)
    assert CLAIM in hit.lower(), hit
    assert len(hit) < 200, "excerpt should be a window around the match, got %d chars" % len(hit)


def test_a_quoted_claim_is_a_retraction_describing_itself():
    assert not _hits('This page used to say "the lean is in the weights", which was withdrawn.')


def test_a_struck_claim_is_a_withdrawal_in_place():
    assert not _hits("~~The lean is in the weights.~~ Withdrawn 2026-09-13.")


def test_strikethrough_is_honoured_across_a_wrapped_line():
    """The markers routinely land on different lines in a hand-wrapped source file."""
    assert not _hits("~~The lean is in the weights, and that is\nrung 3's whole claim.~~")


def test_a_quote_is_honoured_across_a_wrapped_line():
    """The commonest shape in this repository: a retraction quoting what a file used to say.

    Three findings in the study tree were this and nothing else -- a blockquoted excerpt or a
    wrapped citation, reported as live assertions because the opening quote sat on the line
    above the phrase.
    """
    assert not _hits('WRITEUP-2026-05-26.md:350 publishes "the direction replicates and\n'
                     'the lean is in the weights", and lists it among the findings.')


def test_a_stray_quote_does_not_exempt_the_rest_of_the_file():
    """The safety rail on the rule above. A blank line closes the quote.

    Without paragraph scope, one unbalanced quote mark anywhere would silence every
    withdrawn claim below it -- an escape hatch turning into a hole.
    """
    assert _hits('He said "something unterminated here\n'
                 '\n'
                 'The lean is in the weights.')


def test_a_superseded_document_may_keep_its_own_withdrawn_claims():
    banner = "# Old writeup\n\n> ## SUPERSEDED -- kept as history. Do not cite it.\n\n"
    assert K._is_marked_superseded(banner + "The lean is in the weights.")


def test_a_supersession_notice_below_the_fold_does_not_exempt_the_document():
    """A banner the reader meets after the claim is not a banner."""
    buried = "\n".join(["filler"] * 60) + "\nSUPERSEDED\n"
    assert not K._is_marked_superseded(buried)


def test_the_repository_is_clean_right_now():
    """The gate's actual verdict on the tree, so a regression fails here and not at release."""
    _, findings, _ = K.scan_every_document_for_retractions()
    assert not findings, "withdrawn claims asserted: %s" % (
        "; ".join("%s: %s" % (rel, occ) for rel, _, occ in findings[:5]))
