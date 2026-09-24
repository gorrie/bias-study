"""The resolvers that must be right BEFORE the corpus is split across two roots.

WHY THIS FILE EXISTS
--------------------
The private study holds one populated corpus root today. The public mirror holds two, and a
planned reorganisation gives the study the same shape. `studypaths.runs_root()` returns ONE
root and, when both are populated, prefers `data/` -- so every behaviour that depends on it is
latent in the private tree and already live in the mirror.

That is not a theoretical hazard. `scripts/run_study.py:740-753` records the day a stray
`data/<date>/raw/` made `data/` satisfy `_looks_like_runs_root()`: the root flipped for the
whole repo, fourteen analyses followed it to a corpus of one run, and
`audit_response_quality.py --check` printed "no empty response carries a score" and exited 0
**having opened zero files** against a real 547.

Every test here builds a TWO-ROOT tree, because a one-root tree cannot fail any of them. That
is the whole point: these pin behaviour the current tree is structurally incapable of testing,
which is why they are written before the move rather than after it.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))


def _fresh(root: Path):
    """Import a studypaths bound to `root`, isolated from every other test's import."""
    import importlib

    os.environ["STUDY_ROOT"] = str(root)
    for name in ("studypaths",):
        sys.modules.pop(name, None)
    module = importlib.import_module("studypaths")
    return module


@pytest.fixture
def two_roots(tmp_path, monkeypatch):
    """`data/` with an old run, `runs/` with a current one -- the shape after the move."""
    for root, run in (("data", "2026-05-25-old"), ("runs", "2026-09-20-current")):
        scored = tmp_path / root / run / "scored"
        scored.mkdir(parents=True)
        (scored / "m.jsonl").write_text(
            json.dumps(dict(model="m", question_id="T01", condition="A",
                            score_classifier=3, response_text="text")) + "\n",
            encoding="utf-8")
        (scored.parent / "manifest.json").write_text(json.dumps({"analysis_seed": 17}),
                                                     encoding="utf-8")
    module = _fresh(tmp_path)
    yield tmp_path, module
    os.environ.pop("STUDY_ROOT", None)
    sys.modules.pop("studypaths", None)


def test_runs_root_really_does_prefer_the_older_corpus(two_roots):
    """The premise every other test here rests on. If this stops being true, they go vacuous.

    A test suite that pins defensive behaviour without pinning the hazard it defends against is
    how a guard survives the removal of its reason and nobody notices it is now decorative.
    """
    _, S = two_roots
    assert S.runs_root().name == "data", "runs_root() no longer prefers data/; re-read this file"


def test_all_run_dirs_sees_both_corpora(two_roots):
    tmp, S = two_roots
    names = [p.name for p in S.all_run_dirs()]
    assert names == ["2026-05-25-old", "2026-09-20-current"]
    # And the thing runs_root() cannot do: the current run is NOT under the chosen root.
    assert S.runs_root().name == "data"
    assert "2026-09-20-current" not in [p.name for p in S.runs_root().iterdir()]


def test_all_run_dirs_refuses_a_name_present_in_both_roots(two_roots):
    tmp, S = two_roots
    (tmp / "data" / "2026-09-20-current" / "scored").mkdir(parents=True)
    with pytest.raises(S.RunNotFound) as excinfo:
        S.all_run_dirs()
    assert "2026-09-20-current" in str(excinfo.value)


def test_all_run_dirs_skips_the_aggregate_output_directory(two_roots):
    tmp, S = two_roots
    (tmp / "runs" / "_aggregated").mkdir()
    assert "_aggregated" not in [p.name for p in S.all_run_dirs()]


def test_a_new_run_goes_to_the_current_corpus_not_the_one_runs_root_picks(two_roots):
    """The write-path defect, stated as an assertion.

    `run_path()` falls back to `runs_root() / name` for a name it cannot find, and a run being
    collected can never be found. So a collector using it writes the battery into the retired
    May corpus, with a correct manifest and no message.
    """
    tmp, S = two_roots
    assert S.run_path("2026-10-01-new").parent.name == "data", (
        "the reader's resolver no longer lands a new run in data/; this test is now vacuous")
    assert S.new_run_path("2026-10-01-new").parent.name == "runs"


def test_resuming_an_existing_run_never_forks_it_into_the_other_root(two_roots):
    """`new_run_path` must resolve, not place, when the run already exists.

    A collector that placed by rule rather than resolving would create a second
    `2026-05-25-old/` under `runs/` on resume and append half the records there.
    """
    tmp, S = two_roots
    assert S.new_run_path("2026-05-25-old") == tmp / "data" / "2026-05-25-old"


def test_aggregate_dir_does_not_move_when_a_second_root_is_populated(two_roots):
    """The cross-run OUTPUT directory stays where it already is.

    A read that picks the wrong root computes nothing and can be re-run. A write that picks the
    wrong root leaves two answers on disk and nothing to say which is current.
    """
    tmp, S = two_roots
    (tmp / "runs" / "_aggregated").mkdir()
    assert S.aggregate_dir() == tmp / "runs" / "_aggregated"
    assert S.runs_root().name == "data", "and runs_root() would have sent it to data/"


def test_aggregate_dir_refuses_a_split_it_cannot_resolve(two_roots):
    tmp, S = two_roots
    (tmp / "runs" / "_aggregated").mkdir()
    (tmp / "data" / "_aggregated").mkdir()
    with pytest.raises(S.RunNotFound):
        S.aggregate_dir()


def test_the_quality_audit_sweeps_both_corpora(two_roots, monkeypatch):
    """`audit_response_quality` is the script the 2026-09-13 incident is named after."""
    import importlib

    tmp, S = two_roots
    sys.modules.pop("audit_response_quality", None)
    A = importlib.import_module("audit_response_quality")
    monkeypatch.setattr(A, "all_run_dirs", S.all_run_dirs)
    runs = sorted(name for name, _ in A.scored_dirs())
    assert runs == ["2026-05-25-old", "2026-09-20-current"]
    sys.modules.pop("audit_response_quality", None)
