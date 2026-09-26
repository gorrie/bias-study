"""A retraction keyed to one spelling retracts one sentence.

"rewrites ~70% of the political wording" was registered as RETRACTED on 2026-09-13. On
2026-09-20 it was still asserted on three live surfaces and the gate was green on all three:

    PAPER-no-position-only-consensus.md      "rewrites ~70% of political wording"          (no "the")
    dispatches/alignment-mask.md  "roughly 70% of the political wording changes"
    dispatches/gemma-delta.md     "roughly 70% of the political wording changes"

The README, which carried the phrase verbatim, had been corrected. The three that paraphrased
it had not, because nothing told anyone they existed. Adding those three strings to the list
would have been LEARNINGS #3 exactly -- an enumeration where a shape was needed -- since the
fourth variant is a sentence nobody has written yet.

So `_claim_pattern` makes articles optional, hedge words interchangeable and "%" equal to
"percent", and leaves everything else literal. These fixtures are the known-bad and known-good
sets for that rule, committed rather than typed once into a shell (LEARNINGS #2). The
known-good half matters as much as the other: a retraction gate that fires on honest prose is
one somebody switches off.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import key_numbers as K  # noqa: E402

#: The core as registered: the part every version of the claim shares.
PHRASE = "70% of the political wording"

VARIANTS_THAT_MUST_FIRE = [
    # The three that were live and green on 2026-09-20.
    "abliteration rewrites ~70% of political wording and moves stance by 0.2",
    "roughly 70% of the political wording changes while the stance moves a tenth of a point",
    "Abliteration rewrites about 70 percent of the political wording. It moves the stance",
    # Shapes nobody has written yet, which is the point of matching a shape.
    "rewrites   ~70%  of the  political   wording",
    "approximately 70 percent of political wording is rewritten",
    "70% of the political wording",
]

PROSE_THAT_MUST_NOT_FIRE = [
    "the wording of that field is not load-bearing",
    "abliteration rewrites the refusal direction out of the weights",
    "political wording varies with temperature and nothing else",
    "70% of the models refuse the balance instruction",
    "the political wording is unchanged in 70% of cells",  # same words, opposite claim
]


@pytest.mark.parametrize("text", VARIANTS_THAT_MUST_FIRE)
def test_a_reworded_retracted_claim_still_fires(text):
    assert K._unquoted_occurrences(text, PHRASE), (
        "a retracted claim escaped by being reworded: %r" % text)


@pytest.mark.parametrize("text", PROSE_THAT_MUST_NOT_FIRE)
def test_honest_prose_does_not_fire(text):
    assert not K._unquoted_occurrences(text, PHRASE), (
        "the matcher fired on prose that does not assert the retracted claim: %r" % text)


def test_quoting_the_retracted_claim_is_still_allowed():
    """A withdrawal has to be able to say what it withdrew."""
    quoted = 'the page said "70% of the political wording" and that claim is withdrawn'
    assert not K._unquoted_occurrences(quoted, PHRASE)


def test_striking_the_claim_out_is_still_allowed():
    """Strikethrough is the plainest retraction a markdown document can make."""
    assert not K._unquoted_occurrences("~~70% of the political wording~~", PHRASE)


def test_emphasis_inside_the_phrase_does_not_hide_it():
    """The blind spot aimed straight at the claims someone cares most about."""
    assert K._unquoted_occurrences("rewrites **70%** of the political wording", PHRASE)


#: HAND-WRAPPED PROSE IS THE COMMONEST FORM IN THIS REPOSITORY, and it was the one form the
#: scanner could not see. It read line by line while every document here wraps at ~95 columns,
#: so a retracted claim in a sentence long enough to wrap was invisible -- and one was, live,
#: in RESULTS-2026-09-19-dose-response.md, while the gate reported a single occurrence
#: elsewhere and exited on that. Found 2026-09-21 by an adversarial pass.
WRAPPED_ASSERTIONS = [
    "the study's existing result -- abliteration rewrites ~70% of political\nwording while "
    "moving stance below 0.10 -- from a different direction.",
    "we found that roughly 70% of the\npolitical wording changes under ablation.",
    "rewrites about 70 percent\nof the political wording",
]

#: Structure that must NEVER be joined across lines: fusing these would invent adjacency the
#: document does not contain and report a phrase nobody wrote. A false positive on a
#: RETRACTION gate is how the gate gets switched off.
STRUCTURE_THAT_MUST_NOT_FUSE = [
    "| model | share |\n| a | 70% of the |\n| b | political wording |",
    "- 70% of the\n- political wording",
    "# 70% of the\n## political wording",
]

#: A BLOCKQUOTE IS NOT A QUOTATION. In this repository `>` carries asserted caveats, declared
#: limitations and the corpus statement -- prose the author is standing behind, wrapped like
#: any other. The exemption for quoting a withdrawn claim is the quotation MARK, which is
#: tested separately. So a retracted claim wrapped across two `>` lines is an assertion and
#: must fire.
WRAPPED_IN_A_BLOCKQUOTE = [
    "> abliteration rewrites ~70% of the\n> political wording, which is the finding.",
    "> we measured roughly 70 percent of\n> the political wording changing.",
]


@pytest.mark.parametrize("text", WRAPPED_ASSERTIONS)
def test_a_retracted_claim_wrapped_across_lines_still_fires(text):
    assert K._unquoted_occurrences(text, PHRASE), (
        "a retracted claim survived by being hand-wrapped: %r" % text)


@pytest.mark.parametrize("text", STRUCTURE_THAT_MUST_NOT_FUSE)
def test_structural_lines_are_not_joined(text):
    assert not K._unquoted_occurrences(text, PHRASE), (
        "the unwrapper fused structural lines and invented a match: %r" % text)


@pytest.mark.parametrize("text", WRAPPED_IN_A_BLOCKQUOTE)
def test_a_claim_wrapped_inside_a_blockquote_fires(text):
    assert K._unquoted_occurrences(text, PHRASE), (
        "a retracted claim survived inside a wrapped blockquote: %r" % text)


def test_a_blockquote_does_not_fuse_with_the_prose_above_it():
    """Joining a quote block to the paragraph before it would invent adjacency."""
    joined = K._unwrap_prose("the rate was 70% of the\n> political wording elsewhere")
    assert "\n" in joined, "the quote line was absorbed into the paragraph above it"
    assert not K._unquoted_occurrences(
        "the rate was 70% of the\n> political wording elsewhere", PHRASE)


def test_a_wrapped_quotation_is_still_a_quotation():
    """Unwrapping must not turn a quoted withdrawal into an assertion."""
    wrapped_quote = 'the README said "70% of the political\nwording" and that is withdrawn'
    assert not K._unquoted_occurrences(wrapped_quote, PHRASE)


def test_the_pattern_is_not_a_wildcard():
    """Guard against a future 'fix' that broadens this into matching anything.

    If every optional element were made optional enough, the pattern would match bare prose
    and the gate would be worthless in the other direction.
    """
    assert not K._unquoted_occurrences("the wording", PHRASE)
    assert not K._unquoted_occurrences("70%", PHRASE)
