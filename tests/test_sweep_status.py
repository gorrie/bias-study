import io
import json
from contextlib import redirect_stdout
from pathlib import Path

from scripts import sweep_status


def test_complete_sweep_reports_downstream_outputs(tmp_path: Path):
    run = tmp_path / "data" / "2026-05-25-full"
    raw = run / "raw"
    raw.mkdir(parents=True)
    (raw / "model.jsonl").write_text(json.dumps({"ok": True}) + "\n", encoding="utf-8")

    for method, _, _ in sweep_status.METHODS:
        method_dir = run / method
        method_dir.mkdir()
        (method_dir / "model.jsonl").write_text(
            json.dumps({"score_classifier": 3}) + "\n", encoding="utf-8"
        )

    aggregated = tmp_path / "data" / "_aggregated"
    aggregated.mkdir()
    # cross-method-report.json IS a real artifact. An earlier version of this test dropped it
    # as "a name the builder has never produced" -- wrong, and wrong in an instructive way: no
    # script writes it by name because the documented command REDIRECTS stdout into it
    # (cross_method_report.py --all-runs > _aggregated/cross-method-report.json), so grepping
    # the scripts for the filename finds nothing while the file sits committed on disk.
    # Searching for a writer is not the same as asking whether the artifact exists.
    for name in ("cross-method-report.json", "cross-method-runs-index.json",
                 "judge-methods-run.log"):
        (aggregated / name).write_text("{}\n", encoding="utf-8")
    (tmp_path / "results" / "charts").mkdir(parents=True)

    state = sweep_status.collect(tmp_path, "data")
    outputs = state["summary"]["cross_method_outputs"]
    assert set(outputs) == {"cross-method-report.json", "cross-method-runs-index.json",
                            "judge-methods-run.log", "charts_dir"}
    assert outputs["cross-method-runs-index.json"] is True
    assert outputs["judge-methods-run.log"] is True
    # Compare path PARTS, not a POSIX suffix. `endswith("results/charts")` passes on Linux and
    # fails on Windows, where collect() returns the native separator -- so this assertion made
    # the suite red on the machine the study is actually collected on.
    assert Path(outputs["charts_dir"]).parts[-2:] == ("results", "charts")

    rendered = io.StringIO()
    with redirect_stdout(rendered):
        sweep_status.print_table(state)
    assert "Cross-method outputs exist" in rendered.getvalue()


def test_print_table_survives_missing_cross_method_outputs(tmp_path: Path):
    """A clean clone has no _aggregated/ and no charts dir. print_table must still run."""
    run = tmp_path / "data" / "2026-05-25-full"
    raw = run / "raw"
    raw.mkdir(parents=True)
    (raw / "model.jsonl").write_text(json.dumps({"ok": True}) + "\n", encoding="utf-8")
    for method, _, _ in sweep_status.METHODS:
        method_dir = run / method
        method_dir.mkdir()
        (method_dir / "model.jsonl").write_text(
            json.dumps({"score_classifier": 3}) + "\n", encoding="utf-8"
        )

    state = sweep_status.collect(tmp_path, "data")
    outputs = state["summary"]["cross_method_outputs"]
    assert outputs["cross-method-report.json"] is False
    assert outputs["cross-method-runs-index.json"] is False
    assert outputs["charts_dir"] == "MISSING"

    rendered = io.StringIO()
    with redirect_stdout(rendered):
        sweep_status.print_table(state)          # must not raise
    text = rendered.getvalue()
    assert "Cross-method outputs exist" not in text
    assert "MISSING  charts_dir" in text
