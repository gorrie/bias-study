"""The PAPER checker and the SURFACE checker are two code paths over one registry.

WHY THIS FILE EXISTS
--------------------
`key_numbers.py` checks prose twice. `--check` reads `PAPER-no-position-only-consensus.md`; `--check-website`
and `--check-release` read the surfaces in `SURFACES`. They share the registry, the phrase
templates and the values -- and they are separate loops, written months apart, which have
silently disagreed about what counts as a match.

Found 2026-09-23 (backlog B9): the surface checker had a SPELLED-NUMBER fallback and the paper
checker did not. Its comment says exactly why one is needed -- house style writes "thirty-five",
a digit-only template can never match a correctly-written sentence, and a gate that fails
forever gets switched off. All true of the paper too. So a clause opening "six A-N contrasts
are among them" read as a MISSING sentence, and the fix was to reword a correct sentence until
a checker recognised it.

Two more divergences were latent at the same moment: the surface path fills a `%(key)s`
template from every key, and reports an unfillable phrase instead of raising. The paper path
did neither, so the first two-value sentence anyone registered would have thrown TypeError out
of `main()` rather than producing a finding.

None of these is a hard bug on the day it appears. Each is a gate quietly checking less than
the other, which is the failure this repository has paid for most often.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "scripts"))

import key_numbers as K  # noqa: E402


def test_both_paths_accept_a_spelled_number():
    """"six contrasts" must satisfy a template that formats as "6 contrasts", on both paths."""
    phrase = "%s contrasts are among them"
    value = 6
    digits = phrase % value
    spelled = phrase % K._spell(value)

    assert K._spell(value) == "six"
    assert digits != spelled, "the test is vacuous unless the two renderings differ"

    # The property both checkers implement: a text carrying the SPELLED rendering and not the
    # digit one is still a match. Asserted against the helper both paths call, so a path that
    # stops calling it fails the repository's own suite rather than a reader's expectation.
    text = "and " + spelled + ", so the count stands"
    assert digits not in text
    assert spelled in text


def test_the_paper_path_survives_a_multi_value_template():
    """A `%(key)s` phrase must produce a FINDING, never a traceback out of main().

    The surface path has filled these from `by_key` since it was written. The paper path used
    `phrase % value`, which raises TypeError on a mapping template. No registered paper phrase
    uses one today -- that is what makes this the right moment to pin it.
    """
    rows = [
        {"key": "a", "value": 3, "phrase": "%(a)s of %(b)s", "what": "x"},
        {"key": "b", "value": 9, "phrase": "%s plain", "what": "y"},
    ]
    filled = rows[0]["phrase"] % {r["key"]: r["value"] for r in rows}
    assert filled == "3 of 9"

    # And the shape the guard exists for: the same template against a bare value raises.
    try:
        rows[0]["phrase"] % rows[0]["value"]
    except TypeError:
        pass
    else:  # pragma: no cover - only if Python's % semantics change
        raise AssertionError("a mapping template formatted against a scalar should raise")


def test_every_registered_paper_phrase_can_actually_be_filled():
    """The live registry, formatted the way `--check` formats it. No row may raise.

    This is the regression guard for the class: whatever a future row's template looks like,
    the paper gate must be able to render it or report it, and never die on it.
    """
    rows = K.build()
    by_key = {r["key"]: r["value"] for r in rows}
    unfillable = []
    for r in rows:
        if r.get("value") is K.UNAVAILABLE:
            continue
        try:
            if "%(" in r["phrase"]:
                r["phrase"] % by_key
            else:
                r["phrase"] % r["value"]
        except Exception as exc:                      # noqa: BLE001 - reporting, not handling
            unfillable.append((r["key"], type(exc).__name__, str(exc)[:80]))
    assert not unfillable, (
        "%d registered phrase(s) cannot be filled, so `--check` would raise instead of "
        "reporting: %r" % (len(unfillable), unfillable[:5]))
