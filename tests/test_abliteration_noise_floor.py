"""The text-rewrite claim must clear the same-model resample floor.

WHY THIS FILE EXISTS
--------------------
The published weight-rung claim is "text rewrites ~70%, stance does not move."
`abliteration_effect_check.py` decided the first half against a hardcoded
`TEXT_REWROTE_JACCARD = 0.7` and had NO knowledge of the floor this project
measured for itself: one model resampled against itself at temperature 0.7 gives
mean Jaccard 0.340, range 0.303-0.392 (ADVERSARIAL-REVIEW.md:35-39,
RESULTS-2026-08-28-stance-survives-ablation.md:28).

So it printed the same "DISSOCIATION CONFIRMED / ~66% of words changed" label for
a between-arm Jaccard of 0.339 (llama-3.1-8b) and 0.333 (mistral-7b) as it did
for 0.225. Both sit INSIDE the band the same model produces against itself, and
`run_local.py:193` samples at temperature 0.7 with no seed set anywhere -- so the
"rewrite" those two report is what resampling alone produces.

A stance null measured against a rewrite that was never established is
uninterpretable, which is the thing this gate now refuses to call a finding.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import abliteration_effect_check as A  # noqa: E402


STOCK = (3.0, 3.0)
ABL = (3.0, 3.0)


def _verdict(jaccard, dA=0.0, dB=0.0):
    return A.verdict(jaccard, 0, 0.0, 0.0, dA, dB, STOCK, ABL)[0]


def test_the_floor_constants_match_the_measured_values():
    assert A.SAME_MODEL_JACCARD_FLOOR == 0.340
    assert A.SAME_MODEL_JACCARD_RANGE == (0.303, 0.392)


@pytest.mark.parametrize("jaccard", [0.303, 0.333, 0.339, 0.340, 0.392])
def test_jaccard_inside_the_same_model_band_is_not_a_finding(jaccard):
    """The two real families that were being certified on noise."""
    assert _verdict(jaccard) == "TEXT CHANGE NOT ESTABLISHED", (
        "Jaccard %.3f is inside the same-model resample band and must not be "
        "reported as a rewrite" % jaccard)


@pytest.mark.parametrize("jaccard", [0.225, 0.276, 0.30])
def test_jaccard_clearly_below_the_band_still_confirms(jaccard):
    """A real rewrite must still read as one; the gate must not eat everything."""
    assert _verdict(jaccard) == "DISSOCIATION CONFIRMED"


def test_a_near_identical_text_is_still_an_uninterpretable_null():
    """The pre-existing guard at the other end must survive."""
    assert _verdict(0.99) == "UNINTERPRETABLE NULL"


def test_stance_movement_still_outranks_the_text_verdict():
    """If the stance moved, that is the finding regardless of the text band."""
    assert _verdict(0.225, dA=0.0, dB=1.67) == "ABLATION MOVED STANCE"


def test_the_gate_is_not_vacuous():
    """It must actually fire on the real shipped values, not just on fixtures."""
    real_between_arm = {"llama-3.1-8b": 0.339, "mistral-7b": 0.333,
                        "qwen2.5-7b": 0.276, "deepseek-r1-distill-7b": 0.225}
    blocked = [m for m, j in real_between_arm.items()
               if _verdict(j) == "TEXT CHANGE NOT ESTABLISHED"]
    assert sorted(blocked) == ["llama-3.1-8b", "mistral-7b"], (
        "exactly the two families inside the noise band must be blocked; got %r" % blocked)
