"""Regression tests for truncation detection and its enforcement in eligibility.

WHY THIS FILE EXISTS
--------------------
Until 2026-09-13 truncation was invisible end to end:

  * `run_study.py` never recorded a finish reason at all.
  * `score.py` had no truncation check, so a response severed mid-clause was
    handed to the judges and came back `score_classifier=4, eligible=True`.
  * `eligibility.is_eligible` was `has_score and not empty and not failed`, so a
    severed response was fully eligible for every aggregate, CI and chart.
  * The collector guard added earlier that same day was ADVISORY ONLY -- it set a
    `truncated` flag and exited 3, and nothing downstream ever read the flag.

Measured on the real corpus: **1,022 of 4,748 scored records (21.5%) sit exactly
on an 800-token cap**, ranging from 96.7% of glm-4.5's records to near zero for
terse models. Because the rate tracks verbosity, it confounds every cross-vendor
comparison in a study whose central claim is about vendor differences.

DO NOT trust `finish_reason`. Through the G0DM0D3 proxy, ten responses severed
mid-word were all reported `finish_reason="stop"`.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import eligibility as E  # noqa: E402

#: Long enough to have plausibly hit a token cap, and severed mid-clause.
#: The exclusion rule requires corroboration, so a severed FRAGMENT alone is
#: deliberately not enough -- see test_short_severed_text_is_NOT_excluded.
LONG_SEVERED = ("The question turns on scope and remedy in ways that " * 12
                + "the office simply did not")


SEVERED = [
    "The office simply did not",                                  # mid-clause
    "Foreign influence operations (Russian IRA, Chinese state actors)\n- Genuinely",
    "Adversarial perturbations can create false positives to harass",
    "## My Actual View\n\nThe decis",                             # mid-word
    "he specific movement targeted.\n\n## The Strongest Counterarguments\n\n- **",
    "Here are three reasons. 1. Cost. 2. Speed. 3.",              # dangling enumerator
]

COMPLETE = [
    "No, end-to-end encryption should not be weakened.",
    'He called it "a manufactured emergency."',
    "The effect is real but operates through ordinary elite sociology.",
    "It depends on scope (and on remedy).",
    "Consider the counterexample:\n\n```python\nx = 1\n```",      # closed code fence
    "The answer is **no**.",
]


@pytest.mark.parametrize("text", SEVERED)
def test_severed_text_is_detected(text):
    assert E.looks_truncated_text(text) is True, "%r should read as severed" % text[:50]


@pytest.mark.parametrize("text", COMPLETE)
def test_complete_text_is_not_flagged(text):
    assert E.looks_truncated_text(text) is False, (
        "%r is a complete answer; flagging it forces a needless re-collection" % text[:50])


def test_empty_counts_as_truncated_text():
    assert E.looks_truncated_text("") is True
    assert E.looks_truncated_text("   ") is True


def test_explicit_flag_wins_over_text():
    """The collector's recorded verdict is authoritative when present."""
    rec = {"response_text": "A complete sentence.", "truncated": True}
    assert E.is_truncated(rec) is True
    rec = {"response_text": "severed mid", "truncated": False}
    assert E.is_truncated(rec) is False


def test_tokens_out_at_the_cap_is_truncated():
    """Spending exactly the whole budget is not choosing to stop."""
    rec = {"response_text": "Looks complete.", "tokens_out": 800, "max_tokens": 800}
    assert E.is_truncated(rec) is True
    rec = {"response_text": "Looks complete.", "tokens_out": 690, "max_tokens": 4000}
    assert E.is_truncated(rec) is False


def test_short_severed_text_is_NOT_excluded_without_corroboration():
    """A terse answer missing a full stop must not be dropped as truncated.

    The bare text heuristic called the three-word string "a real answer"
    truncated. Silently dropping a good record is the same class of harm as
    admitting a severed one, so the exclusion decision needs corroboration:
    an explicit flag, a spent token budget, or enough length to have hit a cap.
    """
    rec = {"response_text": "a real answer", "score_classifier": 4, "ok": True}
    assert E.is_truncated(rec) is False
    assert E.is_eligible(rec) is True


def test_truncated_record_is_not_eligible():
    """The whole point: a severed response must not enter an aggregate."""
    rec = {"response_text": LONG_SEVERED, "score_classifier": 4, "ok": True}
    assert E.is_truncated(rec) is True
    assert E.is_eligible(rec) is False
    assert E.exclusion_reason(rec) == "truncated-response"
    assert E.is_scored_truncated(rec) is True


def test_truncated_is_distinct_from_empty():
    """Different causes, different remedies, so they must not be pooled."""
    empty = {"response_text": "", "score_classifier": 3, "ok": True}
    sev = {"response_text": LONG_SEVERED, "score_classifier": 3, "ok": True}
    assert E.exclusion_reason(empty) == "empty-or-missing-response"
    assert E.exclusion_reason(sev) == "truncated-response"


def test_partition_buckets_every_record_exactly_once():
    records = [
        {"response_text": "Complete answer.", "score_classifier": 3, "ok": True},
        {"response_text": "", "score_classifier": 3, "ok": True},
        {"response_text": LONG_SEVERED, "score_classifier": 3, "ok": True},
        {"response_text": "whatever", "ok": False},
        {"response_text": "A real refusal, unscored.", "ok": True},
    ]
    eligible, empty, trunc, unscored = E.partition(records)
    assert len(eligible) == 1
    assert len(empty) == 1
    assert len(trunc) == 1
    assert len(unscored) == 2
    assert len(eligible) + len(empty) + len(trunc) + len(unscored) == len(records)


def test_a_real_refusal_is_still_not_truncated():
    """Refusals are results in this study and must survive the truncation rule."""
    rec = {"response_text": "I can't take a position on that.", "ok": True}
    assert E.is_truncated(rec) is False


def test_a_finished_chinese_sentence_is_not_severed():
    """The terminal set was ASCII, so an answer in Chinese could never end.

    `qwen3-235b-a22b-thinking` answers part of the augmentation arm in Chinese.
    One record closed on a complete question -- "...又是否接受监督？" -- and the
    detector called it severed because U+FF1F is not U+003F. It was re-collected
    twice and came back punctuated the same way both times, which is what a
    language does.

    Guards the fullwidth and ideographic terminals, and the CJK closing quote
    forms, against a future tidy-up of the character class.
    """
    for ending in ("。", "？", "！", "．"):
        assert E.looks_truncated_text("公众需持续追问" + ending) is False
    # closed inside a CJK quotation mark is still an ending
    assert E.looks_truncated_text("他说：「不行。」") is False


def test_a_sources_list_ending_in_a_link_is_not_severed():
    """A bulleted citation does not take a full stop, and two models end that way.

    Nine records in 30,089 close on a markdown link while flagged severed, none
    within 95% of its cap -- including two `gpt-4.1` records in the live
    forced-choice run, which is why this is a rule and not a registry entry.
    """
    src = ("*   **ACLU:** [https://www.aclu.org/x](https://www.aclu.org/x)\n"
           "*   **CFR:** [https://www.cfr.org/y](https://www.cfr.org/y)")
    assert E.looks_truncated_text(src) is False


def test_a_link_cut_in_half_is_still_severed():
    """The match needs the closing paren, so a severed URL does not sneak through."""
    assert E.looks_truncated_text(
        "*   **CFR:** [Council on Foreign Relations](https://www.cfr") is True
    assert E.looks_truncated_text(
        "*   **CFR:** [Council on Foreign Relations](") is True


def test_a_sources_list_that_ends_on_the_cap_is_still_truncated():
    """Clause 2 does not read the text, so a real cap hit survives the leniency."""
    rec = {
        "response_text": "*   **CFR:** [CFR](https://www.cfr.org/y)",
        "score_classifier": 3,
        "ok": True,
        "tokens_out": 4000,
        "max_tokens": 4000,
    }
    assert E.is_truncated(rec) is True


def test_cjk_leniency_does_not_admit_a_severed_clause():
    """The correction is additive. Text cut mid-clause stays severed in any script.

    A response genuinely severed does not land on terminal punctuation, and one
    that finishes a sentence exactly on the cap is still caught by `is_truncated`
    clause 2 -- tokens_out at the budget -- which does not read the text at all.
    """
    assert E.looks_truncated_text("政府与平台的合作包括") is True
    at_cap = {
        "response_text": "公众需持续追问。",
        "score_classifier": 3,
        "ok": True,
        "tokens_out": 4000,
        "max_tokens": 4000,
    }
    assert E.is_truncated(at_cap) is True
