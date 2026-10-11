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

    python skills/bias-study-prep/scripts/test_refresh.py      # from the repo root
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
    assert "test_sheet_parser.py" in joined, "the answer parser's fixtures are not gated"


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
    """n mirrored pairs in the live bank's shape: a claim and its opposing framing.

    Corrected 2026-10-10. This built each defender half by inserting "not" into the critic
    half -- the shape of the 60-item bank withdrawn on 2026-09-16 -- so every test passed while
    the gate rejected all 16 pairs of the real instrument. The halves here are deliberately
    different sentences, as they are in data/ratchet-battery.json.
    """
    items, iid = [], start
    for p in range(n_pairs):
        a, b = iid, iid + 1
        topic = "topic-%d" % p
        items.append({"id": a, "mirror_of": b, "pair_no": p + 1, "topic": topic,
                      "frame": "critic",
                      "text": "Measure number %d is a threat to free expression." % p})
        items.append({"id": b, "mirror_of": a, "pair_no": p + 1, "topic": topic,
                      "frame": "defender",
                      "text": "Measure number %d protects the public from real harm." % p})
        iid += 2
    return items


def _fake_study(tmp: Path, items, counts=None):
    (tmp / "data").mkdir(parents=True, exist_ok=True)
    (tmp / "scripts").mkdir(parents=True, exist_ok=True)
    payload = {"items": items}
    if counts is not None:
        payload["counts"] = counts
    (tmp / R.LIVE_INSTRUMENT).write_text(json.dumps(payload), encoding="utf-8")
    for rel in ("scripts/run_battery.py", "scripts/test_sheet_parser.py"):
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
        tmp = _fake_study(Path(td), _pairs(16), counts={"items": 32, "pairs": 16})
        got = _with_study_dir(tmp, R.verify_compass)
    assert got["status"] == "ok", got
    assert got["n_items"] == 32
    assert got["n_pairs"] == 16
    assert got["broken_pairs"] == []
    assert got["multi_sentence_items"] == []


def test_verify_rejects_a_pair_that_is_not_a_mirror():
    """A mirror is decidable from what the bank declares: reciprocal ids, one pair number, one
    topic, opposite frames. Each way of breaking that must fail the gate."""
    breaks = [
        lambda it: dict(it, frame="critic"),            # two critic halves
        lambda it: dict(it, topic="somewhere-else"),     # the halves are about different things
        lambda it: dict(it, pair_no=99),                 # filed under another pair
        lambda it: dict(it, mirror_of=3),                # points at a third item
    ]
    for brk in breaks:
        items = _pairs(16)
        items[1] = brk(items[1])
        with tempfile.TemporaryDirectory() as td:
            tmp = _fake_study(Path(td), items, counts={"items": 32, "pairs": 16})
            got = _with_study_dir(tmp, R.verify_compass)
        assert got["status"] == "failed", got
        assert got["broken_pairs"], got


def test_verify_accepts_the_real_live_instrument():
    """The test whose absence let the gate reject the live bank for three weeks.

    Every other instrument test runs on a fixture; a fixture shaped like the wrong bank passes
    while the real file fails. This one reads data/ratchet-battery.json from the repository.
    """
    repo = Path(__file__).resolve().parents[3]
    if not (repo / R.LIVE_INSTRUMENT).exists():
        return
    got = _with_study_dir(repo, R.verify_compass)
    assert got["broken_pairs"] == [], got["broken_pairs"]
    assert got["n_pairs"] * 2 == got["n_items"], got
    assert got["ids_contiguous"] is True


def test_verify_rejects_a_bank_that_disagrees_with_its_own_declared_counts():
    """Self-consistency replaced a hard-coded 62, which is what aged into a false alarm."""
    with tempfile.TemporaryDirectory() as td:
        tmp = _fake_study(Path(td), _pairs(15), counts={"items": 32, "pairs": 16})
        got = _with_study_dir(tmp, R.verify_compass)
    assert got["status"] == "failed", got
    assert got["n_items"] == 30


def test_verify_rejects_non_contiguous_ids():
    """Answers are keyed by item id, so a gap silently misaligns every comparison."""
    items = _pairs(15)
    items.append({"id": 98, "mirror_of": 99, "pair_no": 16, "topic": "t", "frame": "critic",
                  "text": "Item ninety-eight."})
    items.append({"id": 99, "mirror_of": 98, "pair_no": 16, "topic": "t", "frame": "defender",
                  "text": "Item ninety-nine."})
    with tempfile.TemporaryDirectory() as td:
        tmp = _fake_study(Path(td), items)
        got = _with_study_dir(tmp, R.verify_compass)
    assert got["status"] == "failed", got
    assert got["ids_contiguous"] is False


def test_verify_flags_a_multi_sentence_proposition():
    """One sentence per proposition is what the sheet prompt and the parser both rely on."""
    items = _pairs(16)
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


# ------------------------------------------------------------- gates and protocol files

def _gate_study(tmp: Path, exit_code: int) -> Path:
    (tmp / "scripts").mkdir(parents=True, exist_ok=True)
    (tmp / "scripts" / "g.py").write_text("raise SystemExit(%d)\n" % exit_code, encoding="utf-8")
    return tmp


def _run_gate(tmp: Path):
    original = R.PRE_RUN_GATES
    R.PRE_RUN_GATES = [("g", ["scripts/g.py"])]
    try:
        return _with_study_dir(tmp, R.run_pre_run_gates)
    finally:
        R.PRE_RUN_GATES = original


def test_gate_exit_2_is_not_applicable_not_a_failure():
    """check_no_fork.py exits 2 on any clone. Counting that as failure blocked every clone."""
    with tempfile.TemporaryDirectory() as td:
        got = _run_gate(_gate_study(Path(td), 2))
    assert got["status"] == "ok", got
    assert got["gates"]["g"].get("not_applicable") is True


def test_gate_exit_1_still_fails():
    with tempfile.TemporaryDirectory() as td:
        got = _run_gate(_gate_study(Path(td), 1))
    assert got["status"] == "failed", got


def test_protocol_files_are_found_in_protocol_subdir():
    """The public repository keeps them in protocol/; checking only the root failed every clone."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        (tmp / "protocol").mkdir()
        for fn in R.LEGACY_PROTOCOL_FILES:
            (tmp / "protocol" / fn).write_text("x" * 200, encoding="utf-8")
        got = _with_study_dir(tmp, R.verify_protocol_dir)
    assert got["status"] == "ok", got


def test_no_external_tool_is_required_without_a_rung():
    """G0DM0D3 and OBLITERATUS are checked only for the rung that uses them, and recorded."""
    assert set(R.TOOLS) == {"pipeline", "weights"}
    assert not hasattr(R, "REPOS"), "workspace repos are back in the verdict"
    assert not hasattr(R, "build_epub"), "book builds are back in the pre-flight"


def test_installed_skill_copy_is_flagged_and_link_is_not():
    """Copies drifted for weeks unnoticed. A copy must warn; a link must not."""
    here = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory() as td:
        inst = Path(td)
        (inst / here.name).mkdir()
        (inst / here.name / "SKILL.md").write_text("stale copy", encoding="utf-8")
        os.environ["CLAUDE_SKILLS_DIR"] = str(inst)
        try:
            got = R.check_installed_skills()
        finally:
            del os.environ["CLAUDE_SKILLS_DIR"]
    assert got["status"] == "warn", got
    assert got["skills"][here.name] == "copy"
    with tempfile.TemporaryDirectory() as td:
        os.environ["CLAUDE_SKILLS_DIR"] = td
        try:
            got = R.check_installed_skills()
        finally:
            del os.environ["CLAUDE_SKILLS_DIR"]
    assert got["status"] == "ok" and got["skills"] == {}, got


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
