"""The run validator must not report a layout it cannot read as an empty run.

WHY THIS FILE EXISTS
--------------------
`count_records` read `raw/*.jsonl` and nothing else. Every run in the flat
collector layout therefore came back as

    no-manifest: no manifest.json; 0 model file(s), 0 record(s) on disk

while `runs/2026-09-05-wave` held 124 files and `runs/refusal-ablation` held
4,500 records. The validator was printing a count it had not taken, which is the
exact failure it exists to catch, pointed inward.

The effect on the gate was worse than the wrong number. 38 layout mismatches were
reported as defects alongside 5 real ones, so the real ones were unreadable, and
`release_check` recorded "43 live findings" as a single unactionable total.

A root-level skip used to spare that corpus. It broke silently when `runs/`
became MIXED: `run_study.py` began writing manifests there, the root matched
"has manifests", and 30 runs that predate the discipline were judged against it.
Classification is per directory now, because a root is not a layout.
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import validate_runs as V  # noqa: E402
from pathlib import Path  # noqa: E402


def _jsonl(path, n):
    path.parent.mkdir(parents=True, exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        for i in range(n):
            fh.write(json.dumps({"i": i}) + "\n")


# ------------------------------------------------------- counting

def test_raw_layout_is_counted(tmp_path):
    _jsonl(tmp_path / "raw" / "m.jsonl", 7)
    assert V.count_records(tmp_path) == (1, 7, "raw")


def test_flat_layout_is_counted_not_reported_empty(tmp_path):
    """The 2026-09-05-wave case: 124 files reported as 0."""
    _jsonl(tmp_path / "model__A.jsonl", 5)
    _jsonl(tmp_path / "model__B.jsonl", 6)
    files, records, layout = V.count_records(tmp_path)
    assert (files, records, layout) == (2, 11, "flat")


def test_nested_layout_is_counted(tmp_path):
    """calibration/<model>/<model>__C.jsonl."""
    _jsonl(tmp_path / "gemma2" / "gemma2__A.jsonl", 4)
    _jsonl(tmp_path / "gemma2" / "gemma2__B.jsonl", 6)
    assert V.count_records(tmp_path) == (2, 10, "nested")


def test_raw_wins_over_flat_when_both_exist(tmp_path):
    """A manifest-layout run must be read as one, not silently re-classified."""
    _jsonl(tmp_path / "raw" / "m.jsonl", 3)
    _jsonl(tmp_path / "stray.jsonl", 99)
    assert V.count_records(tmp_path)[2] == "raw"


def test_a_genuinely_empty_directory_reports_none(tmp_path):
    assert V.count_records(tmp_path) == (0, 0, "none")


def test_an_unreadable_file_does_not_crash_the_count(tmp_path):
    _jsonl(tmp_path / "a.jsonl", 2)
    (tmp_path / "b.jsonl").mkdir()  # a directory named like a file
    files, records, layout = V.count_records(tmp_path)
    assert layout == "flat" and records >= 2


# ------------------------------------------------------- classification

def test_flat_layout_is_unvalidated_rather_than_a_missing_manifest(tmp_path):
    _jsonl(tmp_path / "model__A.jsonl", 5)
    out = V.inspect(tmp_path)
    codes = [f["code"] for f in out["findings"]]
    assert codes == ["not-manifest-layout"]
    assert out["findings"][0]["severity"] == "unvalidated"
    assert out["records"] == 5


def test_unvalidated_is_not_reported_as_clean(tmp_path):
    """The other way to get this wrong is to whitelist it into silence."""
    _jsonl(tmp_path / "model__A.jsonl", 5)
    out = V.inspect(tmp_path)
    assert out["findings"], "an unvalidated run must not come back with no findings"
    assert "NOT VALIDATED" in out["findings"][0]["detail"]


def test_a_manifest_layout_run_missing_its_manifest_still_flags(tmp_path):
    """The real defect must survive the fix. raw/ present, manifest absent."""
    _jsonl(tmp_path / "raw" / "m.jsonl", 5)
    out = V.inspect(tmp_path)
    assert [f["code"] for f in out["findings"]] == ["no-manifest"]
    assert "5 record(s)" in out["findings"][0]["detail"]


def test_a_scored_dir_also_means_manifest_layout(tmp_path):
    _jsonl(tmp_path / "scored" / "m.jsonl", 2)
    out = V.inspect(tmp_path)
    assert [f["code"] for f in out["findings"]] == ["no-manifest"]


def test_the_no_manifest_detail_never_claims_zero_when_records_exist(tmp_path):
    """The sentence that was false for 38 runs."""
    _jsonl(tmp_path / "raw" / "m.jsonl", 12)
    out = V.inspect(tmp_path)
    detail = out["findings"][0]["detail"]
    assert "0 record(s)" not in detail
    assert "12 record(s)" in detail


# ------------------------------------------------------- the live tree

def test_the_live_tree_reports_far_fewer_live_findings_than_runs():
    """Regression on the number that made the gate unreadable.

    A report whose every line says FLAG is a report nobody reads; 43 findings
    across 58 runs was that. This asserts the signal-to-noise, not a magic number.
    """
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        V.main([])
    out = buf.getvalue()
    assert "live finding(s)" in out
    live = int(out.split("live finding(s)")[0].strip().split("\n")[-1].strip())
    assert live < 20, "live findings back above 20 (%d); check for a layout regression" % live


def test_unvalidated_runs_are_announced_with_their_record_count():
    """Silence about what was NOT checked is how the gap survives."""
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        V.main([])
    out = buf.getvalue()
    if "not validated" in out:
        assert "NOT VALIDATED -- not clean" in out
        assert "record(s) use a collector layout" in out
