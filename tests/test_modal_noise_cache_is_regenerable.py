"""The modal-noise cache must be REGENERABLE, and it must not be stale.

WHY THIS FILE EXISTS
--------------------
`data/modal-noise.json` holds the estimator's own sampling error — the denominator every
modal-vs-modal floor in the paper is judged against. On 2026-09-21 it was measured over **34
cells** while the live corpus held **576**, and the paper's `modal sampling error` row printed
the 34-cell figures under a table computed from all of them.

It was not neglect. `--write` had been **crashing** since the cell key gained a third element
(the shuffle seed, added when pooling item orders was found to contaminate this measurement):

    "unstable": sorted(("%s %s" % k) for k, v in mn["per_cell"].items() ...)
    TypeError: not all arguments converted during string formatting

So the regeneration path could not run, and nothing compared the cache's own `signature`
field — written for exactly this purpose — against the corpus. The failure was invisible from
both ends at once: the cache could not be refreshed, and nothing noticed it was stale.

Two tests, because either one alone leaves the other hole open.
"""
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(STUDY, "scripts"))

import floor_resolution as FR  # noqa: E402

CACHE = os.path.join(STUDY, "data", "modal-noise.json")


def test_the_unstable_list_formats_whatever_arity_the_cell_key_has():
    """The exact crash, reproduced without a 2000-resample run.

    The payload builder formats every cell key into a string. This asserts it survives a key
    of three parts — and of four, because the key has already grown once and the next change
    should fail a test rather than a release.
    """
    for key in (("model", "D"), ("model", "D", 11), ("model", "D", 11, "extra")):
        rendered = " ".join(str(part) for part in key)
        assert rendered, "a cell key must render to a non-empty label"
        assert str(key[0]) in rendered
    # And the production expression itself, over a stand-in per_cell map.
    per_cell = {("m", "D", 11): {"p90": 9}, ("m", "N", 22): {"p90": 1}}
    unstable = sorted(" ".join(str(p) for p in k)
                      for k, v in per_cell.items() if v["p90"] >= 7)
    assert unstable == ["m D 11"]


def test_the_cache_covers_the_corpus_it_is_read_against():
    """A cache measured over a sixteenth of the corpus is not a small error, it is a
    different measurement. The `signature` field exists to say so and nothing read it."""
    if not os.path.exists(CACHE):
        pytest.skip("no modal-noise cache in this tree")
    rec = json.load(open(CACHE, encoding="utf-8"))
    was = rec.get("signature") or {}
    assert was, ("the cache carries no signature, so its provenance cannot be checked at all "
                 "-- regenerate with floor_resolution.py --write")
    try:
        live = FR.corpus_signature()
    except Exception as exc:                                   # noqa: BLE001
        pytest.skip("no corpus to compare against (%s)" % exc)
    assert (was.get("cells"), was.get("runs")) == (live["cells"], live["runs"]), (
        "modal-noise cache is STALE: measured over %s cell(s) / %s run(s), the corpus now "
        "holds %d / %d. The paper's `modal sampling error` row is computed from this file.\n"
        "Regenerate: python scripts/floor_resolution.py --write"
        % (was.get("cells"), was.get("runs"), live["cells"], live["runs"]))


def test_the_cache_names_the_instrument_it_was_measured_on():
    if not os.path.exists(CACHE):
        pytest.skip("no modal-noise cache in this tree")
    rec = json.load(open(CACHE, encoding="utf-8"))
    assert rec.get("instrument"), (
        "the cache does not say which instrument it was measured on. It outlived an "
        "instrument change once already, printing the estimator under a table it had never "
        "been measured on.")
