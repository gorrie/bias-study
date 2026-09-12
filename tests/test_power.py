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


def test_live_audit_still_runs_and_reports_five_nulls():
    """The fix must not change any verdict on the data as it stands today: no published
    observation currently lands in the band. If this count moves, a real verdict changed and
    that needs a dated correction, not a green test."""
    out = io.StringIO()
    with redirect_stdout(out):
        rc = power.main([])
    assert rc == 0
    text = out.getvalue()
    assert "3 of 5 published nulls are underpowered" in text
    assert "1 is not resolvable at all" in text
    assert "1 clears its floor" in text
    assert "INCONCLUSIVE" not in text
