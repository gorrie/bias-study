"""The Phase 4 estimator, validated before Phase 4 exists.

WHY THIS FILE EXISTS
--------------------
An estimator written after the data is shaped by the first numbers it sees, and
nothing in the code will tell you that. `frame_gap.py` was written and validated
against synthetic input before Phase 0 collected anything, which is why its Phase
0 output could be trusted the moment it appeared. This does the same for Phase 4.

The decisive property is the FIRST test below: a model that agrees with
everything scores exactly zero. The mirrored bank cancels acquiescence by
construction, so no frame correction is applied afterwards -- and if that ever
stops being true, every position number the design produces is contaminated by
yea-saying and nothing downstream would show it.
"""
import os
import statistics as st
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import position_analysis as PA  # noqa: E402


def _built(kind, n_pairs=30, seed=1):
    bank, answers = PA._synthetic(kind, n_pairs=n_pairs, seed=seed)
    index = PA.pair_index(bank)
    pos, cons = PA.cell_positions(answers, index)
    return bank, answers, index, pos, cons


# ------------------------------------------------- the property the design rests on

def test_a_model_that_agrees_with_everything_scores_zero():
    """The mirror cancels acquiescence. If this fails, every position is contaminated."""
    _b, _a, _i, pos, _c = _built("yea")
    assert st.mean(pos.values()) == 0.0


def test_a_model_that_disagrees_with_everything_also_scores_zero():
    _b, _a, _i, pos, _c = _built("nay")
    assert st.mean(pos.values()) == 0.0


def test_agreeing_with_both_halves_is_never_counted_as_consistent():
    _b, _a, _i, _p, cons = _built("yea")
    assert st.mean(cons.values()) == 0.0


def test_acquiescence_separates_yea_from_nay():
    """Position cannot tell them apart -- both are 0 -- so this measure must."""
    _b, a_yea, i_yea, _p, _c = _built("yea")
    _b2, a_nay, i_nay, _p2, _c2 = _built("nay")
    assert PA.acquiescence(a_yea, i_yea)["m"] == 1.0
    assert PA.acquiescence(a_nay, i_nay)["m"] == -1.0


# ------------------------------------------------- direction and scale

def test_a_consistent_skeptic_scores_the_positive_extreme():
    _b, _a, _i, pos, cons = _built("skeptic")
    assert st.mean(pos.values()) == 1.5
    assert st.mean(cons.values()) == 1.0


def test_a_consistent_deferential_scores_the_negative_extreme():
    _b, _a, _i, pos, _c = _built("deferential")
    assert st.mean(pos.values()) == -1.5


def test_the_sign_convention_is_skeptic_positive():
    """Stated once, here, so nothing downstream has to guess."""
    _b, _a, _i, skeptic, _c = _built("skeptic")
    _b2, _a2, _i2, deferential, _c2 = _built("deferential")
    assert st.mean(skeptic.values()) > 0 > st.mean(deferential.values())


def test_random_answering_lands_near_zero():
    _b, _a, _i, pos, _c = _built("random", n_pairs=400, seed=7)
    assert abs(st.mean(pos.values())) < 0.15


# ------------------------------------------------- the interval

def test_a_constant_sample_has_a_zero_width_interval():
    lo, hi = PA._boot([0.5] * 30, seed=1, n=2000)
    assert hi - lo == 0.0


def test_a_single_cluster_yields_no_interval():
    """One cluster is not a sample; it must refuse rather than invent a width."""
    assert PA._boot([0.5], seed=1) == (None, None)


def test_the_bootstrap_resamples_pairs_not_items():
    """Clustering on the item would shrink every interval for no added information."""
    import inspect
    src = inspect.getsource(PA.contrast)
    assert "pair_id" in src or "pairs" in src
    assert "deltas.append(a - b)" in src, "the contrast is not paired within pair"


def test_a_contrast_is_paired_within_the_pair():
    bank, answers = PA._synthetic("skeptic")
    answers.append({"model": "m", "condition": "F",
                    "answers": {k: 1.5 for k in answers[0]["answers"]}})
    index = PA.pair_index(bank)
    pos, _c = PA.cell_positions(answers, index)
    r = PA.contrast(pos, "m", "N", "F")
    assert r["n_pairs"] == 30
    assert r["effect"] == 1.5, "N is the skeptic arm and F is flat, so N - F should be +1.5"


# ------------------------------------------------- the selftest entry point

def test_the_module_selftest_passes():
    """The command a reader is told to run must actually pass."""
    assert PA.selftest() == 0
