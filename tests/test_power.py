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


def test_detection_limits_compute_on_the_live_instrument():
    """The limits table must compute, exit 0, and count in the LIVE bank's units.

    REPLACES test_live_audit_still_runs_and_reports_five_nulls, 2026-09-18. That test
    asserted `power.main()` returns 2 with NOT AUDITED in its output -- the state of a
    guard that refused to compare five published observations counted out of 62 items
    against thresholds counted out of 32. The audit and the guard are deleted, because
    those five claims are WITHDRAWN and will not be re-measured
    (CORRECTIONS-2026-09-17-power.md; the constants are kept deleted by
    scripts/test_correction_gates.py::test_no_audit_of_observations_in_retired_units).

    What is left is the part that was always valid: what the live instrument can
    resolve. This guards that it still computes rather than quietly returning an empty
    table -- a report that examines nothing and exits 0 is this project's signature
    defect and the reason the file it replaces existed.
    """
    _needs_corpus()
    out = io.StringIO()
    with redirect_stdout(out):
        rc = power.main([])
    text = out.getvalue()
    assert rc == 0, 'the limits table computes on its own and is not NOT APPLICABLE'

    # The header's item count is DERIVED from the live bank, not typed. It read 62 --
    # the retired questionnaire's length -- above a table of limits counted out of 32.
    assert 'of %d items' % power.BOUND in text
    assert power.BOUND == 32, 'the live battery is 32 items; a change here is a new bank'

    # CHECKED NOTHING IS NOT A PASS. Every null this study rests on must appear with a
    # threshold, or the table is green over an empty computation.
    for null in ('presentation order', 'run-to-run replicate', 'same-version variants'):
        assert null in text, '%r is missing from the limits table' % null
    rows = [ln for ln in text.split(chr(10))
            if ln.strip() and ('side' in ln or 'endpoint' in ln) and 'statistic' not in ln]
    assert len(rows) >= 8, (
        'only %d limit row(s) computed; the table exists to report floors and a nearly '
        'empty one is the vacuous pass this suite is here to catch' % len(rows))

    # And the audit must NOT have come back by another route.
    assert 'NOT AUDITED' not in text
    assert 'published nulls' not in text
