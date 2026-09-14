"""Rung 2 of the escalation ladder: the README may not claim a direction the corpus lacks.

The README published "only the layered stack adds force, to a ceiling" for four months with
nothing computing it. `analysis.py` keys on conditions A and B; this arm runs B-STM,
B-Parseltongue and B-Layered, so its records matched no branch and its ANALYSIS.md is a heading
for every table and rows under none. The claim was never wrong on purpose -- it was never
checked, which on this instrument is the same thing.
"""
import io
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import pipeline_rung as P  # noqa: E402

README = ROOT / "README.md"


def _has_replicated_pair():
    """The replicated pair is private; the public mirror holds only the n=1 pair.

    Tests about the n=5 finding must SKIP there rather than fail, or the mirror
    suite goes red for holding exactly the data it is supposed to hold. They must
    not be deleted either: they are the assertions that stop the private tree
    drifting back to the null.
    """
    return P.default_pair()[2] == "replicated"


REPLICATED_ONLY = pytest.mark.skipif(
    not _has_replicated_pair(),
    reason="this tree holds only the n=1 pair; see PENDING-PUBLICATION-2026-09-14.md")


@REPLICATED_ONLY
def test_the_arm_no_longer_reads_as_a_null():
    """Replaces `test_no_contrast_in_this_arm_clears_zero`, retired 2026-09-14.

    That test asserted NO contrast cleared zero and said so with an instruction:
    "that is a real result -- update the README row and this test together,
    deliberately." W13's n=5 re-collection made three of eight clear zero, the
    test fired, and this is the deliberate update. It was right to fail; a gate
    that had been loosened instead would have buried the finding.

    What is asserted now is the shape of the replacement result, so the arm cannot
    quietly revert to a null without someone reading this line.
    """
    res = P.estimate()
    if not res:
        return  # arm absent from this tree
    clean = [c for c in res["contrasts"] if c["excludes_zero"]]
    assert clean, (
        "no rung-2 contrast excludes zero. On the n=5 pair three did. Either the "
        "default run has drifted back to the n=1 pair or the estimate has changed -- "
        "check which before touching this test.")


@REPLICATED_ONLY
def test_w13_has_landed_and_the_default_reads_it():
    """This file used to assert samples_per_cell == 1 -- a deliberate tripwire set
    to fail the moment W13's replicates arrived. They arrived on 2026-09-13, so the
    tripwire has done its job and is replaced by its successor: the default must
    now READ the replicated pair, because an estimator left pointing at the n=1
    run keeps publishing the n=1 answer while better data sits on disk unread.
    """
    assert P.PIPELINE_RUN == "2026-09-13-g0dm0d3-replicate"
    assert P.BASELINE_RUN == "2026-09-13-g0dm0d3-replicate-baseline"
    res = P.estimate()
    if not res:
        return
    assert res["samples_per_cell"] != 1, (
        "the default pair is back to one sample per cell; every contrast is then a "
        "difference of two single draws")


def test_the_superseded_pair_is_still_reproducible():
    """Reproducing a published number must not require reading a commit."""
    res = P.estimate(P.HISTORICAL_PIPELINE_RUN, P.HISTORICAL_BASELINE_RUN)
    if not res:
        return
    assert res["samples_per_cell"] == 1
    assert sum(1 for c in res["contrasts"] if c["excludes_zero"]) == 0, (
        "the historical pair no longer reproduces 'all intervals span zero', which is "
        "the sentence it was published to support")


@REPLICATED_ONLY
def test_rung_2_is_real_and_model_specific():
    """The finding that replaced the null, asserted so it cannot quietly revert.

    grok-4.3 and claude-opus-4.7 move in OPPOSITE directions on the same contrast,
    which is why a single pooled rung-2 number would be wrong in both directions.
    """
    res = P.estimate()
    if not res:
        return
    excl = [c for c in res["contrasts"] if c["excludes_zero"]]
    assert len(excl) >= 3, "expected at least 3 intervals excluding zero, got %d" % len(excl)
    signs = {}
    for c in res["contrasts"]:
        if c["excludes_zero"] and "minus" in c["contrast"]:
            signs[c["model"]] = c["effect"] > 0
    assert set(signs.values()) == {True, False}, (
        "the two models no longer disagree in direction on the layered-minus-STM "
        "contrast; the model-specific finding has changed and the write-up must follow")


def test_the_readme_does_not_claim_the_withdrawn_rung_2_direction():
    """The OLD claim stays banned. It was withdrawn on the n=1 data and the n=5 data
    does not restore it -- grok's layered stack adds force, opus's removes it.
    """
    if not README.exists():
        return
    text = io.open(README, encoding="utf-8", errors="replace").read()
    banned = "only the layered stack adds force"
    body = text.replace('"' + banned, "")  # a correction quoting the old claim is allowed
    assert banned not in body, (
        "the README asserts the withdrawn rung-2 direction again. On n=5 the two models "
        "move opposite ways, so no single direction is correct for both.")


def test_the_estimate_names_which_collection_it_came_from():
    """A number nobody can attribute is the inherited-analysis-seed defect again.

    The replicated pair is private and the public mirror holds only the n=1 pair, so
    a single hardcoded default either forks the trees or makes the estimator
    uncomputable in one. `default_pair()` resolves it and `pair` carries the answer
    into the result, so the two trees run identical code and neither can quote a
    contrast without being able to say which collection produced it.
    """
    pipeline, baseline, which = P.default_pair()
    assert which in ("replicated", "historical")
    res = P.estimate()
    if not res:
        return
    assert res["pair"] == which
    assert res["run"] == pipeline and res["baseline_run"] == baseline
    if which == "replicated":
        assert res["samples_per_cell"] != 1
    else:
        assert res["samples_per_cell"] == 1


def test_an_explicit_pair_is_labelled_explicit_not_silently_defaulted():
    res = P.estimate(P.HISTORICAL_PIPELINE_RUN, P.HISTORICAL_BASELINE_RUN)
    if not res:
        return
    assert res["pair"] == "historical"
