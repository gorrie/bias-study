"""Convergent validity: shifts, not levels, and thin cells excluded."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


def test_convergent_validity_uses_shifts_not_levels():
    """Comparing LEVELS across two instruments with different content and different scales
    measures the scales. The claim both instruments make is about a condition SHIFT."""
    import convergent_validity as CV
    judged = {"m": {"A": [1, 1], "B": [3, 3]}}
    mech = {"m": {"A": [0.0, 0.0], "B": [1.0, 1.0]}}
    rows = CV.shifts(judged, mech)
    assert len(rows) == 1
    assert rows[0]["judged_shift"] == 2 and rows[0]["mechanical_shift"] == 1


def test_a_model_missing_either_condition_is_dropped():
    import convergent_validity as CV
    judged = {"m": {"A": [1]}}
    mech = {"m": {"A": [0.0], "B": [1.0]}}
    assert CV.shifts(judged, mech) == []


def test_min_records_filter_drops_thin_cells():
    """gpt-5 has 22 eligible records of 310 and the largest judged shift in the table. The
    filter is how we showed the near-zero correlation is not that one cell."""
    import convergent_validity as CV
    judged = {"m": {"A": [1] * 5, "B": [3] * 5}}
    mech = {"m": {"A": [0.0], "B": [1.0]}}
    assert len(CV.shifts(judged, mech, min_records=5)) == 1
    assert CV.shifts(judged, mech, min_records=50) == []
