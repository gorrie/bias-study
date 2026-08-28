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
    for name in ("cross-method-runs-index.json", "cross-method-report.json", "judge-methods-run.log"):
        (aggregated / name).write_text("{}\n", encoding="utf-8")
    (tmp_path / "results" / "charts").mkdir(parents=True)

    state = sweep_status.collect(tmp_path, "data")
    outputs = state["summary"]["cross_method_outputs"]
    assert outputs["cross-method-runs-index.json"] is True
    assert outputs["cross-method-report.json"] is True
    assert outputs["judge-methods-run.log"] is True
    assert outputs["charts_dir"].endswith("results/charts")

    rendered = io.StringIO()
    with redirect_stdout(rendered):
        sweep_status.print_table(state)
    assert "Cross-method outputs exist" in rendered.getvalue()
