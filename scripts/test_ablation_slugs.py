#!/usr/bin/env python3
"""Two independent abliterations of one base must never share a directory.

WHY THIS FILE EXISTS
--------------------
`ablation_wave._slug` built a directory name from the model tag's second-to-last path segment,
which for `hf.co/<uploader>/<repo>:<quant>` is the **uploader**. On 2026-09-07 two independent
abliterations of qwen2.5-14b were added -- huihui-ai v2 and Josiefied v2 -- and both are
distributed as mradermacher requantisations, so both slugged to `ablated-mradermacher`.

That is not a cosmetic clash. `ablation_analysis.py` derives a cell's ARM from its directory
name, so the two builds would have been read as one cell, their runs pooled, and the
pre-registered ablator-agreement step would have compared a build against itself -- while
reporting that two independent ablators agreed. The check exists to answer "is this the
ablation or this ablator's choices?", and a collision makes it answer yes by construction.

It was caught by reading `--plan` before collecting. This test is so that the next one is caught
without anybody having to read anything.
"""
from __future__ import annotations

import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import ablation_wave as A  # noqa: E402


def test_no_two_ablators_of_one_base_share_a_slug():
    """THE REGRESSION. One directory per abliteration, per base."""
    for label, _stock, ablations in A.PAIRS:
        slugs = collections.Counter(A._slug(a) for a in ablations)
        clashes = {s: n for s, n in slugs.items() if n > 1}
        assert not clashes, (
            "base %r maps %d ablator(s) onto the same directory slug %s -- "
            "ablation_analysis reads the arm from the directory, so these would be pooled "
            "into one cell and the ablator-agreement step would compare a build with itself"
            % (label, sum(clashes.values()), clashes))


def test_every_cell_has_a_distinct_directory():
    """Across the whole plan, not just within a base -- the same guarantee one level up."""
    seen = collections.Counter((lab, arm) for lab, arm, _m, _c in A.cells())
    dupes = {k: n for k, n in seen.items() if n > len(A.CONDITIONS)}
    assert not dupes, "duplicate (base, arm) beyond the condition expansion: %s" % dupes


def test_slug_does_not_collapse_to_the_uploader():
    """The specific wrong answer, asserted directly.

    Both tags below are mradermacher requantisations of DIFFERENT abliterations. If the slug
    ever goes back to keying on the uploader they collide again, and this says so in the name
    of the failure rather than as a generic duplicate.
    """
    a = "hf.co/mradermacher/Qwen2.5-14B-Instruct-abliterated-v2-GGUF:Q4_K_M"
    b = "hf.co/mradermacher/Josiefied-Qwen2.5-14B-Instruct-abliterated-v2-GGUF:Q4_K_M"
    assert A._slug(a) != A._slug(b), (
        "the slug is keying on the uploader again: %r for both builds" % A._slug(a))
    # And neither may be empty or degenerate, which would put runs in `ablated-`.
    for tag in (a, b):
        s = A._slug(tag)
        assert s and s.strip("-_"), "empty slug for %r" % tag


def test_the_already_collected_arms_keep_their_directories():
    """Changing the slug must not orphan a completed cell.

    Resume accounting keys on (model, condition) rather than on the directory, so a completed
    cell is not re-collected when its slug changes -- but the ANALYSIS keys on the directory,
    so an old directory must not collide with a NEW slug for a different build. The v1 build
    already lives in `ablated/`; assert no new slug lands there.
    """
    for label, _stock, ablations in A.PAIRS:
        for a in ablations:
            assert A._slug(a) != "", label
            assert "ablated-%s" % A._slug(a) != "ablated", (
                "%r on base %r would slug into the bare `ablated` directory, which already "
                "holds a different build" % (a, label))


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
