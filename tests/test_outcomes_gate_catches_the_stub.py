"""The outcomes gate must catch each defect that actually got through.

A gate is worth what it catches, and the only way to know is to put the defect back. The
estimator for this study's primary outcomes spent four collection passes and 702 records
broken in FOUR independent ways at once, with a green selftest the whole time:

  1. `main()` was a stub printing "Phase 4 has not been collected yet" for any run directory.
  2. `pair_index` read `item["pair_id"]`; the bank's field is `pair_no`.
  3. `cell_positions` iterated `rec["answers"].items()`; the collector writes a LIST.
  4. the pre-registered contrasts named conditions `F/N/P/C`; the wave collected `N/A/P/D`,
     so the contrast loop appended nothing and returned an empty list that read as a result.

Each is replanted below against the LIVE corpus and the gate must go red. A gate tested only
on a healthy tree is a gate nobody has watched fire (LEARNINGS #2).
"""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "scripts"))

import check_outcomes_computable as G  # noqa: E402
import position_analysis as P  # noqa: E402
import pytest  # noqa: E402


def _wave():
    run = G._latest_wave()
    if not run:
        pytest.skip("no wave corpus in this tree -- NOT APPLICABLE, not a pass")
    return run


def test_the_gate_passes_on_the_live_corpus():
    """The baseline. Without this the red tests below prove nothing."""
    assert G.main([]) == 0


def test_a_stubbed_estimator_is_caught(monkeypatch):
    """Defect 1: a real-data path that returns nothing."""
    monkeypatch.setattr(P, "load_records", lambda *a, **k: [])
    assert G.main([]) == 1


def test_the_wrong_pair_field_is_caught(monkeypatch):
    """Defect 2: `pair_id` against the bank's `pair_no`.

    The original raised KeyError; the gate must report it rather than let it escape, which is
    why every outcome is called inside a try.
    """
    def broken(bank):
        return {i["id"]: (i["pair_id"], i["frame"]) for i in bank["items"]}
    monkeypatch.setattr(P, "pair_index", broken)
    assert G.main([]) == 1


def test_the_wrong_answers_shape_is_caught(monkeypatch):
    """Defect 3: a mapping expected where the collector writes a list of {q, position}."""
    real = P.load_records

    def as_written(run_dir, *a, **k):
        recs = real(run_dir, *a, **k)
        for r in recs:
            r["answers"] = [{"q": q, "position": p} for q, p in r["answers"].items()]
        return recs

    monkeypatch.setattr(P, "load_records", as_written)
    assert G.main([]) == 1


def test_condition_letters_that_do_not_match_the_collection_are_caught(monkeypatch):
    """Defect 4: the one that produced an EMPTY LIST rather than an error.

    This is the worst of the four, because nothing raised and nothing was missing -- the
    contrast list simply came back empty and looked computed. The gate names the mismatch and
    says where to fix it.
    """
    monkeypatch.setattr(P, "CONDITION_MAP", {"N": "N", "F": "F", "P": "P", "C": "C"})
    assert G.main([]) == 1


def test_a_failing_prediction_does_NOT_fail_the_gate():
    """The gate asks whether an outcome CAN be computed, never whether it was confirmed.

    Predictions 2, 3 and 5 currently fail on this corpus. A gate that went red on an unwelcome
    verdict would be a gate under pressure to be tuned until the verdict changed, which is the
    defect this whole study audits other people for.
    """
    run = _wave()
    value, why = G.outcome_predictions(run)
    assert value is not None, why
    assert "FAIL" in value, "expected some prediction to fail on this corpus: %s" % value
    assert G.main([]) == 0


def test_a_broken_floor_arm_is_caught(monkeypatch):
    """The floors are an outcome too, and a dead source glob is how one goes missing."""
    import floor_table as F
    monkeypatch.setattr(F, "uncomputed_report",
                        lambda: [("floor_planted", "path", "no file matches `runs/nope/*`")])
    assert G.main([]) == 1


def test_a_tree_with_no_corpus_is_not_applicable(monkeypatch):
    monkeypatch.setattr(G, "_latest_wave", lambda: None)
    assert G.main([]) == 2, "an absent corpus is NOT APPLICABLE, never a pass"
