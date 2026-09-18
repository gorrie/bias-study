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

def test_the_preflight_checks_the_live_instrument():
    """The regression that produced this file. A pre-flight must check the LIVE instrument.

    Updated 2026-09-15: the live instrument is now the project's own authored
    bank. This asserted `compass-propositions.json`, which is the RETIRED
    third-party item set -- so the test that exists to stop the pre-flight
    drifting onto a dead instrument would itself have pinned it there.
    """
    assert R.FORCED_CHOICE_FILES, "the pre-flight checks no instrument at all"
    joined = " ".join(R.FORCED_CHOICE_FILES)
    assert R.LIVE_INSTRUMENT in joined, "the forced-choice item set is not checked"
    assert "run_battery.py" in joined, "the collection harness is not checked"
    assert "test_compass_parser.py" in joined, "the answer parser's fixtures are not gated"


def test_the_retired_instrument_is_not_a_dependency():
    """It is licensed text we do not ship. Requiring it would fail a clean clone."""
    assert R.RETIRED_INSTRUMENT not in " ".join(R.FORCED_CHOICE_FILES)


def test_legacy_and_forced_choice_lists_are_disjoint():
    """Keeping the retired battery's checks is right. Confusing them for the live one is not."""
    legacy = {Path(p).name for p in R.LEGACY_PROTOCOL_FILES}
    live = {Path(p).name for p in R.FORCED_CHOICE_FILES}
    assert not (legacy & live), legacy & live


def test_pre_run_gates_include_all_three_paper_gates():
    names = {n for n, _ in R.PRE_RUN_GATES}
    for required in ("gen_paper", "key_numbers", "controls_audit"):
        assert required in names, "%s is not gated before a run" % required


# ------------------------------------------------------------- instrument validation

def _pairs(n_pairs, start=1):
    """n mirrored pairs, each half differing by exactly one inserted 'not'.

    The shape the live instrument actually has. A fixture of standalone
    propositions would pass a check that no longer exists and say nothing about
    the one that does.
    """
    items, iid = [], start
    for p in range(n_pairs):
        a, b = iid, iid + 1
        stem = "Measure number %d is a threat to free expression." % p
        items.append({"id": a, "mirror_of": b, "frame": "critic",
                      "polarity": "affirmative", "text": stem})
        items.append({"id": b, "mirror_of": a, "frame": "defender",
                      "polarity": "negated",
                      "text": stem.replace(" is a threat", " is not a threat")})
        iid += 2
    return items


def _fake_study(tmp: Path, items, counts=None):
    (tmp / "data").mkdir(parents=True, exist_ok=True)
    (tmp / "scripts").mkdir(parents=True, exist_ok=True)
    payload = {"items": items}
    if counts is not None:
        payload["counts"] = counts
    (tmp / R.LIVE_INSTRUMENT).write_text(json.dumps(payload), encoding="utf-8")
    for rel in ("scripts/run_battery.py", "scripts/test_compass_parser.py"):
        (tmp / rel).write_text("placeholder\n", encoding="utf-8")
    return tmp


def _with_study_dir(tmp, fn):
    original = R.BIAS_STUDY_DIR
    R.BIAS_STUDY_DIR = tmp
    try:
        return fn()
    finally:
        R.BIAS_STUDY_DIR = original


def test_verify_accepts_a_well_formed_mirrored_instrument():
    with tempfile.TemporaryDirectory() as td:
        tmp = _fake_study(Path(td), _pairs(30), counts={"items": 60, "pairs": 30})
        got = _with_study_dir(tmp, R.verify_compass)
    assert got["status"] == "ok", got
    assert got["n_items"] == 60
    assert got["n_pairs"] == 30
    assert got["broken_pairs"] == []
    assert got["multi_sentence_items"] == []


def test_verify_rejects_a_pair_that_is_not_a_negation():
    """The invariant that makes a mirror a mirror, and the one a generator broke before.

    An earlier build DERIVED each negation by inserting "not" after the first
    auxiliary, and on one item that auxiliary sat in a subordinate clause -- it
    produced a DIFFERENT proposition that collected and scored cleanly. Identity
    is decidable; grammar is not.
    """
    items = _pairs(30)
    items[1] = dict(items[1], text="An entirely different proposition about something else.")
    with tempfile.TemporaryDirectory() as td:
        tmp = _fake_study(Path(td), items, counts={"items": 60, "pairs": 30})
        got = _with_study_dir(tmp, R.verify_compass)
    assert got["status"] == "failed", got
    assert got["broken_pairs"], got


def test_verify_rejects_a_bank_that_disagrees_with_its_own_declared_counts():
    """Self-consistency replaced a hard-coded 62, which is what aged into a false alarm."""
    with tempfile.TemporaryDirectory() as td:
        tmp = _fake_study(Path(td), _pairs(29), counts={"items": 60, "pairs": 30})
        got = _with_study_dir(tmp, R.verify_compass)
    assert got["status"] == "failed", got
    assert got["n_items"] == 58


def test_verify_rejects_non_contiguous_ids():
    """Answers are keyed by item id, so a gap silently misaligns every comparison."""
    items = _pairs(29)
    items.append({"id": 98, "mirror_of": 99, "frame": "critic", "text": "Item ninety-eight."})
    items.append({"id": 99, "mirror_of": 98, "frame": "defender",
                  "text": "Item not ninety-eight."})
    with tempfile.TemporaryDirectory() as td:
        tmp = _fake_study(Path(td), items)
        got = _with_study_dir(tmp, R.verify_compass)
    assert got["status"] == "failed", got
    assert got["ids_contiguous"] is False


def test_verify_flags_a_multi_sentence_proposition():
    """One sentence per proposition is what the sheet prompt and the parser both rely on."""
    items = _pairs(30)
    items[0] = dict(items[0], text="First sentence here. Second sentence here.")
    with tempfile.TemporaryDirectory() as td:
        tmp = _fake_study(Path(td), items)
        got = _with_study_dir(tmp, R.verify_compass)
    assert 1 in got["multi_sentence_items"], got.get("multi_sentence_items")


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
