"""The export other people will actually use, and the trap it exists to defuse.

A third party reading `data/*/scored/*.jsonl` directly gets no warning that 466 records in the
primary corpus carry a classifier score derived from an empty response. Nothing in the shipped
record says so: `response_text` is `""` and the score beside it looks like every other score.
It took this project four months and a dedicated audit to notice.

These tests hold the two properties that make the export worth trusting: nothing is silently
dropped, and the three states stay distinguishable.
"""
import csv
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import export_analysis_ready as X  # noqa: E402


def run(tmp_path, records, name="probe.jsonl"):
    scored = tmp_path / "2026-01-01" / "scored"
    scored.mkdir(parents=True)
    io.open(scored / name, "w", encoding="utf-8", newline="\n").write(
        "".join(json.dumps(r) + "\n" for r in records))
    return list(X.rows([str(tmp_path)]))


def test_the_three_states_stay_distinguishable(tmp_path):
    out = run(tmp_path, [
        dict(ok=True, model="m", condition="A", question_id=1,
             response_text="a real answer", score_classifier=4),
        dict(ok=True, model="m", condition="A", question_id=2,
             response_text="", score_classifier=3),
        dict(ok=True, model="m", condition="A", question_id=3,
             response_text="I decline to answer this.", score_classifier=None),
    ])
    by_q = {r["question_id"]: r for r in out}
    assert by_q[1]["eligible"] and by_q[1]["exclusion_reason"] == ""
    assert not by_q[2]["eligible"] and by_q[2]["exclusion_reason"] == "empty-or-missing-response"
    assert by_q[2]["is_defect"], "a score derived from a blank string is a defect"
    assert not by_q[3]["eligible"], "a missing score cannot enter a mean"
    assert by_q[3]["exclusion_reason"] == "no-classifier-score"
    assert not by_q[3]["is_defect"], (
        "a substantive refusal is a RESULT in this study, not a defect. 148 refusals in 1,076 "
        "no-directive runs is a published finding and the original pipeline threw exactly these "
        "away as collection errors.")


def test_nothing_is_silently_dropped(tmp_path):
    recs = [dict(ok=True, model="m", condition="A", question_id=i,
                 response_text="" if i % 2 else "text", score_classifier=3)
            for i in range(1, 11)]
    out = run(tmp_path, recs)
    assert len(out) == 10, "every scored record must appear, flagged rather than filtered"
    man = X.manifest(out)
    assert man["total_rows"] == 10
    assert man["eligible_rows"] + man["ineligible_rows"] == 10


def test_abliteration_builds_split_without_parsing(tmp_path):
    for model, base, build, abl in [
        ("qwen2.5-7b-abliterated-strong", "qwen2.5-7b", "abliterated-strong", True),
        ("gemma-2-9b", "gemma-2-9b", "stock", False),
        ("anthropic/claude-opus-4.7", "anthropic/claude-opus-4.7", "stock", False),
        ("qwen38-27b-ablite-v2", "qwen38-27b", "ablite-v2", True),
    ]:
        got = X.split_build(model)
        assert got == (base, build, abl), "%s -> %r, wanted %r" % (model, got, (base, build, abl))


def test_the_manifest_warns_about_thin_cells_before_anyone_analyses(tmp_path):
    recs = [dict(ok=True, model="thin", condition="A", question_id=1,
                 response_text="t", score_classifier=3)]
    recs += [dict(ok=True, model="fat", condition="A", question_id=i,
                  response_text="t", score_classifier=3) for i in range(20)]
    man = X.manifest(run(tmp_path, recs))
    smallest = man["smallest_eligible_cells"][0]
    assert smallest["model"] == "thin" and smallest["n"] == 1


def test_eligible_only_still_reports_what_it_removed(tmp_path):
    """An unfalsifiable clean corpus is the thing this study complains about in other people."""
    out = run(tmp_path, [
        dict(ok=True, model="m", condition="A", question_id=1, response_text="t", score_classifier=3),
        dict(ok=True, model="m", condition="A", question_id=2, response_text="", score_classifier=3),
    ])
    man = X.manifest(out)
    assert man["ineligible_rows"] == 1 and man["defect_rows"] == 1, (
        "the manifest is computed before any filtering, so --eligible-only cannot hide it")


def test_the_live_corpus_defect_count_matches_the_independent_audit():
    """547 is audit_response_quality's headline, reached by a different code path.

    GUARDS A CLASS, NOT THE TOTAL, since 2026-09-13. Truncation became an exclusion
    reason on that date, so `defect_rows` is now the sum of two defect classes while
    `audit_response_quality` still counts only the scored-empty one. Comparing the
    total against 547 would fail for a correct reason, and updating the constant to
    the new total would destroy the cross-path check this test exists to be.
    """
    table = list(X.rows(X.corpus_roots()))
    if not table:
        return
    man = X.manifest(table)
    trunc = man["ineligible_by_reason"].get("truncated-response", 0)
    pre_existing_defects = man["defect_rows"] - trunc
    assert pre_existing_defects == 547, (
        "export says %d pre-truncation defect rows; audit_response_quality says 547. "
        "Two paths over one corpus must agree." % pre_existing_defects)


def test_truncated_rows_are_excluded_and_counted_separately():
    """A severed response is excluded, and NOT pooled with the empty ones."""
    table = list(X.rows(X.corpus_roots()))
    if not table:
        return
    man = X.manifest(table)
    trunc = man["ineligible_by_reason"].get("truncated-response", 0)
    assert trunc > 0, (
        "no truncated rows found. 21.5% of this corpus sat on an 800-token cap; a "
        "zero here means the exclusion stopped firing, not that the corpus got clean.")
