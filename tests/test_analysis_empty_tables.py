"""An empty analysis table must announce itself, not render as a measured null.

runs/2026-05-27-g0dm0d3/ANALYSIS.md carried a heading for every table and rows under none for
four months, and the README published a DIRECTION for that arm on the strength of it. The cause
is that every table in analysis.py keys on conditions A and B while that arm runs B-STM,
B-Parseltongue and B-Layered: the records flowed through, matched no branch, and the document
rendered as a normal analysis containing nothing.

An empty table is indistinguishable from a table whose answer is "no effect". That is how an
empty file became a published claim, and it is the same shape as the four gates that printed
failure and exited 0.
"""
import io
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "analysis.py"


def make_run(tmp_path, conditions):
    run = tmp_path / "2026-01-01-probe"
    (run / "scored").mkdir(parents=True)
    recs = []
    for i, c in enumerate(conditions * 4):
        recs.append(dict(ok=True, model="m", condition=c, question_id="T%02d-Q1" % (i % 4 + 1),
                         topic="T%02d" % (i % 4 + 1), response_text="text",
                         score_classifier=3, hedge_ratio=0.1))
    io.open(run / "scored" / "m.jsonl", "w", encoding="utf-8", newline="\n").write(
        "".join(json.dumps(r) + "\n" for r in recs))
    return run


def run_analysis(run):
    return subprocess.run([sys.executable, str(SCRIPT), run.name],
                          cwd=str(run.parent.parent) if (run.parent.parent / "scripts").exists()
                          else str(ROOT),
                          capture_output=True, text=True)


def test_the_live_pipeline_arm_is_flagged():
    """The real run that caused this. Its conditions are not A/B and three tables are empty."""
    doc = ROOT / "runs" / "2026-05-27-g0dm0d3" / "ANALYSIS.md"
    if not doc.exists():
        return
    text = io.open(doc, encoding="utf-8", errors="replace").read()
    assert "tables are EMPTY" in text, "the empty-table banner is missing from the arm it exists for"
    assert "Do not publish a direction for this arm" in text
    assert "pipeline_rung.py" in text, "the banner must name the estimator that CAN read this arm"


def test_a_healthy_run_is_not_flagged():
    """False positives would train everyone to ignore the banner."""
    doc = ROOT / "runs" / "2026-05-25-full" / "ANALYSIS.md"
    if not doc.exists():
        return
    text = io.open(doc, encoding="utf-8", errors="replace").read()
    assert "tables are EMPTY" not in text, "the main run has full tables and must not be flagged"


def test_the_banner_distinguishes_its_two_causes():
    """A/B present but an input missing is a different fault from a condition mismatch."""
    for name, expect in (("2026-05-27-g0dm0d3", "every table below keys on"),
                         ("2026-05-27-paraphrase", "not a condition mismatch")):
        doc = ROOT / "runs" / name / "ANALYSIS.md"
        if not doc.exists():
            continue
        text = io.open(doc, encoding="utf-8", errors="replace").read()
        if "tables are EMPTY" in text:
            assert expect in text, "%s got the wrong explanation for its empty tables" % name
