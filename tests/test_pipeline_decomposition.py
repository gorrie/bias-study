"""The rung-2 decomposition estimator, tested before its data existed.

`pipeline_decomposition.py` was written and validated against synthetic input
with a planted answer BEFORE the collection it reads was finished. That ordering
is the project's rule and the reason is in its own learnings file: an estimator
written afterwards gets shaped by the data it is first run on, and reading the
source will not tell you that happened.

These tests are that validation, kept so it runs on every change rather than
once at authoring time.
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import pipeline_decomposition as D  # noqa: E402


def _plant(instruction=0.6, sampling=0.0, stack=None, model="m/x"):
    """Records for one model with a KNOWN decomposition."""
    base = 3.0
    conds = {"B-Proxy": base,
             "B-Godmode": base + instruction,
             "B-Autotune": base + sampling,
             "B-Layered": base + (instruction + sampling if stack is None else stack)}
    return [{"model": model, "condition": c, "question_id": "Q%02d" % q,
             "sample_idx": s, "score_classifier": v}
            for c, v in conds.items() for q in range(10) for s in range(5)]


def _effects(res, model="m/x"):
    return {c["contrast"]: c["effect"]
            for c in res["contrasts"] if c["model"] == model}


def test_the_selftest_passes():
    """The estimator's own planted-answer suite, as the CLI runs it."""
    assert D.main(["--selftest"]) == 0


def test_it_separates_instruction_from_sampling():
    res = D.decompose(run="t", records=_plant(instruction=0.6, sampling=0.0))
    eff = _effects(res)
    assert eff["B-Godmode minus B-Proxy"] == pytest.approx(0.6)
    assert eff["B-Autotune minus B-Proxy"] == pytest.approx(0.0)

    res = D.decompose(run="t", records=_plant(instruction=0.0, sampling=0.5))
    eff = _effects(res)
    assert eff["B-Godmode minus B-Proxy"] == pytest.approx(0.0)
    assert eff["B-Autotune minus B-Proxy"] == pytest.approx(0.5)


def test_an_interaction_is_not_reported_as_additive():
    """A stack that under-delivers must not read as the sum of its parts.

    This is the check that stops a single-arm number being quoted as if it
    generalised to the stack.
    """
    res = D.decompose(run="t",
                      records=_plant(instruction=0.6, sampling=0.4, stack=0.2))
    add = res["additivity"][0]
    assert add["residual"] == pytest.approx(-0.8)
    assert not add["additive"]


def test_replicates_are_averaged_within_the_cell_not_pooled():
    """Five samples of one cell are n=1 with a bigger file, not n=5.

    The bug this guards against shipped in six places in this repo: keying on
    (model, question) without the condition pools the arms and differences a
    cell against itself.
    """
    res = D.decompose(run="t", records=_plant())
    assert res["samples_per_cell"] == 5
    assert not res["replicates_ragged"]
    for c in res["contrasts"]:
        assert c["n"] == 10, "n must be QUESTIONS paired, not draws"


def test_an_arm_with_no_baseline_yields_no_contrast():
    """Half a collection must produce no rows rather than rows against nothing."""
    recs = [r for r in _plant() if r["condition"] != "B-Proxy"]
    res = D.decompose(run="t", records=recs)
    assert res["contrasts"] == []
    assert res["additivity"] == []


def test_an_empty_corpus_returns_none():
    """A gate that examined nothing must never look like a result."""
    assert D.decompose(run="t", records=[]) is None


def test_the_cli_refuses_rather_than_printing_an_empty_table():
    rc = D.main(["--run", "2026-01-01-does-not-exist"])
    assert rc == 2


def _live():
    return D.decompose()


LIVE_ONLY = pytest.mark.skipif(_live() is None,
                               reason="decomposition run not in this tree")


@LIVE_ONLY
def test_the_effect_is_the_instruction_not_the_sampling():
    """Rung 2's effect is godmode, and autotune is nothing.

    B-Layered tracks B-Godmode to within a rounding error while B-Autotune spans
    zero. The sampling hypothesis gets the BETTER-POWERED test of the two --
    autotune is the larger perturbation, temperature 0.825 plus top_p and top_k,
    against godmode's bundled +0.1 -- and it comes back null. If this flips,
    section 4.3 is wrong in the other direction and needs rewriting rather than
    patching.
    """
    eff = {(c["model"].split("/")[-1], c["contrast"]): c
           for c in _live()["contrasts"]}
    god = eff[("grok-4.3", "B-Godmode minus B-Proxy")]
    auto = eff[("grok-4.3", "B-Autotune minus B-Proxy")]
    lay = eff[("grok-4.3", "B-Layered minus B-Proxy")]
    assert god["excludes_zero"], god
    assert not auto["excludes_zero"], auto
    assert abs(lay["effect"] - god["effect"]) < 0.15, (
        "the stack has drifted from its instruction arm: layered %+0.2f against "
        "godmode %+0.2f" % (lay["effect"], god["effect"]))


@LIVE_ONLY
def test_opus_is_flat_under_every_ingredient():
    """The correction this run forced.

    `B-Layered minus B-STM` read -0.31 on Opus and was published as half of a
    "two models move in opposite directions" finding. Its reference arm B-STM is
    NOT untreated: the proxy edits its scored text on 45 of 60 Opus records.
    Against an arm that received genuinely nothing, Opus is flat -- its four cell
    means span 3.44 to 3.50.
    """
    for c in _live()["contrasts"]:
        if not c["model"].endswith("claude-opus-4.7"):
            continue
        assert not c["excludes_zero"], (
            "Opus now moves under %s: %+0.2f [%+0.2f, %+0.2f]. That reverses the "
            "2026-09-15 correction and the writeup needs re-reading."
            % (c["contrast"], c["effect"], c["lo"], c["hi"]))


@LIVE_ONLY
def test_the_stack_is_additive_so_single_arms_generalise():
    for a in _live()["additivity"]:
        assert a["additive"], (
            "%s's stack no longer equals the sum of its parts (residual %+0.2f); "
            "the single-arm numbers stop generalising to B-Layered"
            % (a["model"], a["residual"]))
