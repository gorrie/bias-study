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


def test_pairs_layout_two_levels_deep_is_counted(tmp_path):
    """A third layout the counter could not see, found 2026-09-19.

    `runs/2026-08-30-ablation-pairs` and `runs/2026-09-07-ablation-wave` store records at
    <pair>/<arm>/<model>__<condition>.jsonl. count_records tried raw/, *.jsonl and */*.jsonl
    and returned "none, 0 records" for 111 files holding 364 records, while run_inventory.py
    counted them correctly -- two tools in one tree disagreeing about whether the data existed.
    """
    d = tmp_path / "2026-01-01-pairs"
    (d / "gemma4-12b" / "stock").mkdir(parents=True)
    (d / "gemma4-12b" / "ablated").mkdir(parents=True)
    (d / "gemma4-12b" / "stock" / "m__A.jsonl").write_text('{"a":1}\n{"a":2}\n', encoding="utf-8")
    (d / "gemma4-12b" / "ablated" / "m__A.jsonl").write_text('{"a":3}\n', encoding="utf-8")
    files, records, layout = V.count_records(d)
    assert layout == "pairs", layout
    assert files == 2
    assert records == 3


def test_a_shallower_layout_still_wins_over_pairs(tmp_path):
    """Layout detection is ordered; pairs must not capture a run that is really flat."""
    d = tmp_path / "2026-01-01-flat-plus-junk"
    (d / "sub" / "deeper").mkdir(parents=True)
    (d / "top.jsonl").write_text('{"a":1}\n', encoding="utf-8")
    (d / "sub" / "deeper" / "x.jsonl").write_text('{"a":2}\n', encoding="utf-8")
    files, records, layout = V.count_records(d)
    assert layout == "flat", layout


# ------------------------------------- whose data is this, actually

def test_the_studys_own_schema_is_never_read_as_another_workstream(tmp_path):
    """THE PANEL RUN WAS EXEMPT FROM EVERY RULE HERE FOR FIVE DAYS.

    The foreign-schema escape hatch is keyed on a prefix allowlist. It named the retired
    instrument (`compass-run`) and nothing else, so when the bank was replaced on 2026-09-17
    and the collector began stamping `battery-run/1`, the wave every published figure in the
    paper is computed from -- 3,897 records -- was classified as ANOTHER WORKSTREAM and
    skipped, with the printed reason "no published number depends on it".

    An exemption prints as a tidy dash, not a failure, which is why nobody read it. Once the
    allowlist was corrected the run failed on a real finding immediately: it declared no
    analysis_seed, so every bootstrap over it had been inheriting the May study's frozen seed
    by silent fallback.
    """
    d = tmp_path / "2026-09-16-ratchet-v3-wave"
    _jsonl(d / "m__A.jsonl", 3)
    (d / "manifest.json").write_text(
        json.dumps({"schema": "battery-run/1", "analysis_seed": 20260527}), encoding="utf-8")
    codes = [f["code"] for f in V.inspect(d)["findings"]]
    assert "other-workstream" not in codes, (
        "battery-run IS this study; exempting it hides every collection rule below")
    assert codes == []


def test_a_genuinely_foreign_schema_is_still_exempt(tmp_path):
    """The escape hatch is still needed -- the evidence and residency workstreams share the
    root and were never written to these rules."""
    d = tmp_path / "2026-09-08-residency-smoke-01"
    _jsonl(d / "m__A.jsonl", 3)
    (d / "manifest.json").write_text(
        json.dumps({"schema": "bias-residency-probe/1"}), encoding="utf-8")
    codes = [f["code"] for f in V.inspect(d)["findings"]]
    assert codes == ["other-workstream"]


def test_an_unrecognised_schema_blocks_instead_of_exempting_itself(tmp_path):
    """The exemption needs an owner, or it un-checks a run silently.

    The allowlist failure above was only possible because anything OUTSIDE it was waved
    through. A schema nobody has claimed is now a live finding: under this rule the panel
    wave would have failed on the day the collector started stamping `battery-run/1`, rather
    than printing a dash for five days.
    """
    d = tmp_path / "2026-09-30-whatever"
    _jsonl(d / "m__A.jsonl", 3)
    (d / "manifest.json").write_text(json.dumps({"schema": "some-new-collector/1"}),
                                     encoding="utf-8")
    r = V.inspect(d)
    assert [f["code"] for f in r["findings"]] == ["unknown-schema"]
    assert all(f.get("severity") != "unvalidated" for f in r["findings"]), (
        "an unclaimed schema must BLOCK, not be waved through as a layout classification")


def test_every_foreign_schema_in_the_tree_is_claimed_by_name():
    """A run in this repository declaring a schema nobody owns is the defect above, live."""
    import glob
    import os as _os
    unowned = []
    # ANCHORED ON THIS FILE, not on `run_roots()`. Resolving the corpus through the ambient
    # resolver made this test depend on whatever the rest of the suite had last pointed it
    # at: it passed alone and failed in the full run with "no manifests found", which its own
    # vacuity guard caught. A test about what is in THIS repository should find it the same
    # way every time.
    study = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    paths = sorted(glob.glob(_os.path.join(study, "runs", "*", "manifest.json"))
                   + glob.glob(_os.path.join(study, "data", "*", "manifest.json")))
    assert paths, "no manifests found -- this test would check nothing"
    for p in paths:
        m = json.loads(io.open(p, encoding="utf-8").read())
        s = m.get("schema") or m.get("kind")
        if not s or str(s).startswith(V.OURS):
            continue
        if not any(str(s).startswith(k) for k in V.FOREIGN_SCHEMAS):
            unowned.append((_os.path.basename(_os.path.dirname(p)), s))
    assert not unowned, "unclaimed schema(s): %r" % (unowned,)
