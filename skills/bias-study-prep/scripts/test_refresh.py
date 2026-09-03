"""Tests for bias-study-prep: does the pre-flight check the instrument a run will use?

WHY
---
This skill had three scripts, 414 lines, and no tests. On 2026-09-02 it was found scoped
entirely to the JUDGE-SCORED battery retired on 2026-08-29: it verified `questions.md`,
`rubric.md`, G0DM0D3 and OBLITERATUS health, and rebuilt reference EPUBs -- none of which a
forced-choice compass run touches. Every one of those files still exists, so the check PASSED
and said nothing about the instrument a collection was about to use.

The test that matters most here is `test_compass_files_are_not_the_retired_battery`: a future
edit that quietly drops the forced-choice checks fails it. Everything else is scaffolding
around that.

    python scripts/test_refresh.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

os.environ.setdefault("BIAS_STUDY_WORKSPACE", str(Path(__file__).resolve().parents[5]))

import refresh as R  # noqa: E402


# --------------------------------------------------------- what the pre-flight covers

def test_compass_files_are_not_the_retired_battery():
    """The regression that produced this file. A pre-flight must check the LIVE instrument."""
    assert R.COMPASS_FILES, "COMPASS_FILES is empty -- the pre-flight checks no instrument"
    joined = " ".join(R.COMPASS_FILES)
    assert "compass-propositions.json" in joined, (
        "the forced-choice item set is not checked; this is the 2026-09-02 defect returning")
    assert "run_compass.py" in joined, "the collection harness is not checked"
    assert "test_compass_parser.py" in joined, "the answer parser's fixtures are not gated"


def test_legacy_and_compass_lists_are_disjoint():
    """Keeping the retired battery's checks is right. Confusing them for the live one is not."""
    legacy = {Path(p).name for p in R.LEGACY_PROTOCOL_FILES}
    compass = {Path(p).name for p in R.COMPASS_FILES}
    assert not (legacy & compass), legacy & compass


def test_pre_run_gates_include_all_three_paper_gates():
    names = {n for n, _ in R.PRE_RUN_GATES}
    for required in ("gen_paper", "key_numbers", "controls_audit"):
        assert required in names, "%s is not gated before a run" % required


# ------------------------------------------------------------- instrument validation

def _fake_study(tmp: Path, items):
    (tmp / "data").mkdir(parents=True, exist_ok=True)
    (tmp / "scripts").mkdir(parents=True, exist_ok=True)
    (tmp / "data" / "compass-propositions.json").write_text(
        json.dumps({"items": items}), encoding="utf-8")
    for rel in ("scripts/run_compass.py", "scripts/test_compass_parser.py",
                "PREREG-2026-08-29-mask-surface-v2.md"):
        (tmp / rel).write_text("placeholder\n", encoding="utf-8")
    return tmp


def _with_study_dir(tmp, fn):
    original = R.BIAS_STUDY_DIR
    R.BIAS_STUDY_DIR = tmp
    try:
        return fn()
    finally:
        R.BIAS_STUDY_DIR = original


def test_verify_compass_accepts_a_well_formed_instrument():
    with tempfile.TemporaryDirectory() as td:
        tmp = _fake_study(Path(td), [{"id": i, "text": "A proposition number %d." % i}
                                     for i in range(1, 63)])
        got = _with_study_dir(tmp, R.verify_compass)
    assert got["status"] == "ok", got
    assert got["n_items"] == 62
    assert got["multi_sentence_items"] == []


def test_verify_compass_rejects_a_short_instrument():
    """61 items is not this instrument, and a run against it is not comparable."""
    with tempfile.TemporaryDirectory() as td:
        tmp = _fake_study(Path(td), [{"id": i, "text": "Item %d." % i}
                                     for i in range(1, 62)])
        got = _with_study_dir(tmp, R.verify_compass)
    assert got["status"] == "failed", got
    assert got["n_items"] == 61


def test_verify_compass_rejects_non_contiguous_ids():
    """Answers are keyed by item id, so a gap silently misaligns every comparison."""
    items = [{"id": i, "text": "Item %d." % i} for i in range(1, 62)]
    items.append({"id": 99, "text": "Item ninety-nine."})
    with tempfile.TemporaryDirectory() as td:
        tmp = _fake_study(Path(td), items)
        got = _with_study_dir(tmp, R.verify_compass)
    assert got["status"] == "failed", got
    assert got["ids_contiguous"] is False


def test_verify_compass_flags_a_multi_sentence_proposition():
    """One sentence per proposition is a measured property fetch_items.py's bound relies on."""
    items = [{"id": i, "text": "Item %d." % i} for i in range(1, 62)]
    items.append({"id": 62, "text": "First sentence here. Second sentence here."})
    with tempfile.TemporaryDirectory() as td:
        tmp = _fake_study(Path(td), items)
        got = _with_study_dir(tmp, R.verify_compass)
    assert got["multi_sentence_items"] == [62], got.get("multi_sentence_items")


def test_verify_compass_reports_missing_dependencies():
    with tempfile.TemporaryDirectory() as td:
        got = _with_study_dir(Path(td), R.verify_compass)
    assert got["status"] == "failed"
    assert all(v["status"] == "missing" for v in got["files"].values())


# ------------------------------------------------------------------ floor snapshot

def test_snapshot_floors_records_pair_counts_or_says_it_cannot():
    """The check that would have caught two collections landing nowhere.

    Runs against the real study directory, because the point is the real floor arms. It is
    allowed to be unavailable (a checkout without the scripts); it is not allowed to claim
    success with no arms.
    """
    got = R.snapshot_floors()
    assert got["status"] in ("ok", "unavailable", "failed"), got
    if got["status"] == "ok":
        assert got["arms"], "reported ok with no floor arms recorded"
        for name, row in got["arms"].items():
            assert isinstance(row.get("n_pairs"), int), (name, row)
            assert row["n_pairs"] >= 0, (name, row)


def test_snapshot_floors_covers_the_class_split_arms():
    """The frontier arm is the one that twice failed to grow. It has to be in the snapshot."""
    got = R.snapshot_floors()
    if got["status"] != "ok":
        return
    names = " ".join(got["arms"])
    assert "frontier" in names, "the frontier order arm is not snapshotted"
    assert "local open-weight" in names, "the local order arm is not snapshotted"


if __name__ == "__main__":
    import traceback
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("ok    %s" % name)
            except Exception:
                failures += 1
                print("FAIL  %s" % name)
                traceback.print_exc()
    print()
    print("%d failure(s)" % failures)
    raise SystemExit(1 if failures else 0)
