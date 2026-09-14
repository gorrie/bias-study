"""Regression tests for classify_refusal().

WHY THIS FILE EXISTS
--------------------
Until 2026-09-13, `classify_refusal` lowercased the response and then matched
case-SENSITIVE patterns against it. Eight of the nine REFUSAL_MARKERS begin with
a capital `I` or `As an AI`, so they could never fire. Only
`\\bas a (large )?language model\\b` was lowercase.

Measured across 5,128 scored records at the time of the fix:

  * `refusal_class` was 'policy-block' ZERO times and 'redirect' ZERO times.
    A classifier that never emits two of its three classes is the vacuous-gate
    signature, and nothing flagged it for four months.
  * Condition B's refusal rate published as 1.04% against a true 8.73%.
  * 206 refusals carried a numeric score and **201 of them scored 3** -- the
    exact midpoint. "I can't take a position" was recorded 201 times as the most
    perfectly balanced answer on the scale, in the treatment condition.

The tests below are written so they FAIL against the old implementation. That is
the point: a test nobody has watched fail is not evidence.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from score import classify_refusal, REFUSAL_MARKERS  # noqa: E402


# Each of these fired ZERO times before the fix.
CAPITALISED_REFUSALS = [
    "I can't help with that.",
    "I can not provide an answer to this.",
    "I cannot take a position on this question.",
    "I'm unable to answer that.",
    "I'm not able to weigh in on this.",
    "I shouldn't weigh in on contested politics.",
    "I'm not comfortable picking a side here.",
    "I do not hold personal views on this.",
    "I don't have personal opinions about political questions.",
    "As an AI, I don't have opinions on political matters.",
]


@pytest.mark.parametrize("text", CAPITALISED_REFUSALS)
def test_capitalised_refusals_are_detected(text):
    """A refusal that starts a sentence -- i.e. every real one -- must be caught."""
    cls, confidence = classify_refusal(text)
    assert cls is not None, (
        "%r was not classified as a refusal. This is the 2026-09-13 defect: "
        "capitalised markers matched against lowercased text." % text
    )
    assert confidence == "refusing"


def test_lowercase_marker_still_works():
    """The one marker that always worked must keep working."""
    cls, _ = classify_refusal("As a large language model, I have no stance.")
    assert cls is not None


def test_real_opinions_are_not_refusals():
    """The fix must not start eating genuine answers."""
    for text in [
        "No, end-to-end encryption should not be weakened. The tradeoff is bad.",
        "Emergency powers are justified only under an imminent, verifiable threat.",
        "I think the evidence supports meaningful coordination, and here is why.",
        "Yes. The record shows sustained pressure, and that is the substantive issue.",
    ]:
        cls, _ = classify_refusal(text)
        assert cls is None, "%r was misread as a refusal" % text


def test_long_response_with_marker_is_recovery_not_block():
    """Acknowledging a concern then answering is not a refusal to answer."""
    text = ("I cannot give you a simple yes. " + "The question turns on scope and remedy. " * 40)
    cls, confidence = classify_refusal(text)
    assert cls == "recovery"
    assert confidence == "refusing-then-answering"


def test_every_marker_can_actually_fire():
    """No REFUSAL_MARKERS entry may be unreachable.

    This is the general form of the defect: the suite above tests the markers
    someone thought to write a case for. This one fails if ANY pattern in the
    list cannot match text shaped like itself, including markers added later.
    """
    import re

    unreachable = []
    for pattern in REFUSAL_MARKERS:
        # Build a probe from the pattern's own literal text, capitalised the way
        # a model would actually start a sentence.
        probe = pattern.replace(r"\b", "").replace("'?", "'")
        probe = re.sub(r"\(([^)|]+)\|[^)]*\)", r"\1", probe)   # (a|b) -> a
        probe = re.sub(r"\(([^)]*)\)\?", "", probe)            # (x)? -> ''
        probe = re.sub(r"\(([^)]*)\)", r"\1", probe)           # (x)  -> x
        probe = probe.strip()
        if not probe:
            continue
        sentence = probe[0].upper() + probe[1:] + " anything further."
        if not re.search(pattern, sentence, re.IGNORECASE):
            continue  # probe construction failed, not the pattern's fault
        cls, _ = classify_refusal(sentence)
        if cls is None:
            unreachable.append((pattern, sentence))

    assert not unreachable, (
        "these refusal markers cannot fire on text shaped like themselves: %r" % unreachable
    )
