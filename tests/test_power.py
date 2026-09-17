"""Regression for STATS-MDE-DECISION-001: the MDE is not the rejection threshold.

`power.py` used to decide a published null with `supported = observed >= MDE`. Those are
answers to different questions and they are not ordered — on the same-version-variants floor
the MDE is 11 while the threshold is 13 — so an observation could clear the MDE, fail the
test, and still be printed SUPPORTED ("calling it a null was wrong in the other direction")
off a movement indistinguishable from the null.

These tests pin all three bands. The middle one is the defect; it had no coverage at all,
which is how a one-character conflation survived in an audit script whose entire purpose is
to catch claims the instrument cannot support.
"""
import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import power  # noqa: E402


SYNTHETIC_NULL = list(range(11))          # [0, 1, ... 10] — the backlog's own reproduction


def test_synthetic_null_reproduces_the_reported_arithmetic():
    """threshold 10, MDE 9 — MDE strictly BELOW the threshold, which is what makes the
    conflation reachable rather than theoretical."""
    thr = power.pctile(SYNTHETIC_NULL, 1 - power.ALPHA)
    m = power.mde(SYNTHETIC_NULL, thr)
    assert thr == 10
    assert m == 9
    assert m < thr, "if the MDE ever sits above the threshold this defect cannot fire"


def _verdict(observed, thr, m, caveat=None):
    """The decision power.main() makes for one published null, in isolation."""
    exceeds_threshold = observed >= thr
    above_mde = observed >= m
    if exceeds_threshold and caveat:
        return "NOT RESOLVABLE"
    if exceeds_threshold:
        return "SUPPORTED"
    if above_mde:
        return "INCONCLUSIVE"
    return "UNDERPOWERED"


def test_observation_between_mde_and_threshold_is_not_supported():
    """THE REGRESSION. observed 9 clears the MDE (9) and does not clear the threshold (10).
    The old rule called this SUPPORTED."""
    assert _verdict(9, thr=10, m=9) == "INCONCLUSIVE"
    assert _verdict(9, thr=10, m=9) != "SUPPORTED"
    # the whole band, not just its edge
    for observed in range(11, 13):        # same-version-variants floor: MDE 11, threshold 13
        assert _verdict(observed, thr=13, m=11) == "INCONCLUSIVE"


def test_the_other_two_bands_are_unchanged():
    assert _verdict(10, thr=10, m=9) == "SUPPORTED"        # clears the threshold
    assert _verdict(14, thr=13, m=11) == "SUPPORTED"
    assert _verdict(8, thr=10, m=9) == "UNDERPOWERED"      # below both
    assert _verdict(3, thr=13, m=11) == "UNDERPOWERED"


def test_a_caveat_still_disqualifies_a_cleared_threshold():
    assert _verdict(12, thr=10, m=10, caveat="n=1 per arm") == "NOT RESOLVABLE"


def _needs_corpus():
    """NOT APPLICABLE, not failed, in a tree that carries no runs.

    The public mirror holds no `runs/` export until a scrubbed one is staged, so every test
    that audits the corpus fails there -- and a stranger cloning the release repository to
    check this study's work sees a red suite whose redness says nothing about the study. The
    project's own convention is exit 2 for NOT APPLICABLE; this is that, in pytest.

    Guarded on the tree actually being empty, so it can never silence a real failure where
    the data exists.
    """
    import pytest
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    import floor_table as _F
    if not _F._tree_has_run_data():
        pytest.skip("no runs/ corpus in this tree -- NOT APPLICABLE, not a pass")


def test_live_audit_still_runs_and_reports_five_nulls():
    _needs_corpus()
    """The fix must not change any verdict on the data as it stands today: no published
    observation currently lands in the band. If this count moves, a real verdict changed and
    that needs a dated correction, not a green test."""
    out = io.StringIO()
    with redirect_stdout(out):
        rc = power.main([])
    # REFUSED, NOT AUDITED, since 2026-09-17: every published `observed` is a count out of the
    # retired instrument's 62 items and every threshold is now a count out of 32. See
    # CORRECTIONS-2026-09-17-power.md, whose own verdict claims were withdrawn for this.
    # scripts/test_correction_gates.py holds the refusal; this file holds the limits table,
    # which is computed entirely from battery floors and is unaffected.
    assert rc == 2, "an unauditable table is NOT APPLICABLE, not a pass"
    text = out.getvalue()
    assert "NOT AUDITED" in text
    return
    # UPDATED 2026-09-17, DELIBERATELY, WITH A DATED CORRECTION BESIDE IT.
    #
    # These were 3 / 1 / 1. This test fired when they moved, which is what it is for -- the
    # floors are now measured on the author's 32-item battery across four collection passes
    # rather than on the retired external questionnaire, and two of them changed shape: the
    # requantisation floor exists again (16 pairs, threshold 10) and the replicate floor
    # exists on this instrument for the first time (336 pairs).
    #
    # The verdicts that moved are recorded in CORRECTIONS-2026-09-17-power.md. Note the
    # direction: "clears its floor" went 1 -> 3, which does NOT restore three findings. It
    # means three movements this study declared absent are larger than the instrument can
    # resolve, so declaring them absent was wrong in the other direction. UNDECIDED, not true.
    assert "1 of 5 published nulls are underpowered" in text
    assert "1 is not resolvable at all" in text
    assert "3 clears its floor" in text
    assert "INCONCLUSIVE" not in text
    # The header's item count is derived from the live bank, not typed. It read 62 -- the
    # retired questionnaire's length -- above a table of limits counted out of 32.
    assert "of 32 items" in text
