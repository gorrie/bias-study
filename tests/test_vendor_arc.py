"""The vendor arc must compare VERSIONS, not rows, and must refuse when there is one version."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import drift_timeseries as D


def _rows(pairs):
    """pairs: (version_label, delta). One dict per measurement row."""
    return [{"version_label": v, "model": "m", "sort_key": (i,), "mean_delta_AB": d,
             "mean_score_A": 1.0, "mean_score_B": 1.0, "model_class": "x",
             "n_questions": 62, "run_date": f"r{i}"} for i, (v, d) in enumerate(pairs)]


def _arc_line(rows, tmp_path):
    p = tmp_path / "arcs.md"
    D.write_vendor_arcs_md({"fam": rows}, p)
    return [l for l in p.read_text(encoding="utf-8").splitlines()
            if l.startswith("Arc direction")][0]


def test_one_version_measured_many_times_is_not_an_arc(tmp_path):
    """THE DEFECT. Eight runs of one model returned `deltas[-1] - deltas[0]` -- one arbitrary
    run minus another -- labelled "delta from oldest to newest". xai-grok shipped exactly this."""
    line = _arc_line(_rows([("4.3", 0.0), ("4.3", 0.9), ("4.3", 0.1)]), tmp_path)
    assert "NO ARC" in line
    assert "1 distinct version" in line
    assert "run-to-run variation, not drift" in line


def test_arc_compares_version_means_not_first_and_last_row(tmp_path):
    """Two versions, two runs each. Row order would give 0.4-0.0=+0.4; version means give
    (0.5+0.3)/2 - (0.0+0.4)/2 = +0.2. The row answer depends on which run happened to be last."""
    rows = _rows([("v1", 0.0), ("v1", 0.4), ("v2", 0.5), ("v2", 0.3)])
    line = _arc_line(rows, tmp_path)
    assert "+0.20" in line, line
    assert "across 2 versions" in line


def test_arc_narrower_than_its_own_noise_says_so(tmp_path):
    rows = _rows([("v1", 0.0), ("v1", 1.0), ("v2", 0.1)])
    line_block = (tmp_path / "arcs2.md")
    D.write_vendor_arcs_md({"fam": rows}, line_block)
    text = line_block.read_text(encoding="utf-8")
    assert "wider than the arc itself" in text
    assert "not distinguishable from run-to-run variation" in text


def test_heading_counts_versions_and_measurements_separately(tmp_path):
    p = tmp_path / "arcs3.md"
    D.write_vendor_arcs_md({"fam": _rows([("4.3", 0.0), ("4.3", 0.5)])}, p)
    # The heading used to read "(2 versions)" for one version measured twice.
    assert "1 version(s), 2 measurements" in p.read_text(encoding="utf-8")
