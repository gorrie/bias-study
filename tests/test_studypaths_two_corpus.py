"""SYNC-STUDY-SHIM-002: the two-corpus regression.

`studypaths.py` exists to stop one thing — a script silently reading the WRONG study corpus and
reporting success having computed nothing. It had no tests. That is the wrong module to leave
uncovered, and it has already failed in production: on 2026-09-05 the private study's `data/`
acquired `external/rottger2024-codes.jsonl`, a content-based rule decided `data/` therefore held
runs, and every shared script started looking for runs in the config directory.

Both real layouts are built here as temp dirs and asserted against:

    public mirror     data/<run>/{raw,scored}          runs live in data/
    private study     data/<config>.json               data/ is CONFIG
                      runs/<run>/{raw,scored}          runs live in runs/

`STUDY_ROOT` is process-global, so every test sets it and reloads the module rather than
importing once — otherwise the first test to run wins and the rest assert against its cache.
"""
import importlib
import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))


def _load(root, monkeypatch):
    monkeypatch.setenv("STUDY_ROOT", str(root))
    import studypaths
    return importlib.reload(studypaths)


def _run_dir(parent, name="2026-05-25-full", scored=True):
    d = parent / name
    (d / "raw").mkdir(parents=True)
    (d / "raw" / "model.jsonl").write_text('{"ok": true}\n', encoding="utf-8")
    if scored:
        (d / "scored").mkdir()
        (d / "scored" / "model.jsonl").write_text('{"score_classifier": 3}\n', encoding="utf-8")
    return d


@pytest.fixture
def public_layout(tmp_path):
    """Runs live in data/. This is the published mirror."""
    root = tmp_path / "mirror"
    _run_dir(root / "data")
    return root


@pytest.fixture
def private_layout(tmp_path):
    """data/ holds CONFIG; runs live in runs/. This is the private working study."""
    root = tmp_path / "study"
    (root / "data").mkdir(parents=True)
    (root / "data" / "questions.json").write_text('{"q": []}', encoding="utf-8")
    _run_dir(root / "runs")
    return root


def test_public_layout_resolves_to_data(public_layout, monkeypatch):
    sp = _load(public_layout, monkeypatch)
    assert sp.runs_root().name == "data"


def test_private_layout_resolves_to_runs_not_the_config_dir(private_layout, monkeypatch):
    sp = _load(private_layout, monkeypatch)
    assert sp.runs_root().name == "runs", \
        "data/ holds config, not runs — resolving to it is the silent-wrong-corpus failure"


def test_the_2026_09_05_regression_a_stray_jsonl_must_not_flip_resolution(private_layout,
                                                                         monkeypatch):
    """The real incident. An undated child of data/ holding a .jsonl is a data file, not a run,
    and must not convince the resolver that data/ is the run root."""
    ext = private_layout / "data" / "external"
    ext.mkdir()
    (ext / "rottger2024-codes.jsonl").write_text('{"code": 1}\n', encoding="utf-8")
    sp = _load(private_layout, monkeypatch)
    assert sp.runs_root().name == "runs"


def test_a_dated_child_with_structure_does_qualify(tmp_path, monkeypatch):
    """The other direction: a genuine run must still be recognised, or the guard above would
    just break resolution instead of tightening it."""
    root = tmp_path / "either"
    _run_dir(root / "runs", name="2026-07-01")
    (root / "data").mkdir(parents=True)
    sp = _load(root, monkeypatch)
    assert sp.runs_root().name == "runs"


def test_a_run_present_only_in_the_other_corpus_raises_rather_than_resolving(private_layout,
                                                                            monkeypatch):
    """The failure this module exists to prevent: asking for a run that lives in the OTHER
    corpus must be an operator error, not a quiet empty result."""
    sp = _load(private_layout, monkeypatch)
    (private_layout / "data" / "2026-01-01").mkdir()
    with pytest.raises(sp.RunNotFound):
        sp.resolve_run("2026-01-01")


def test_an_unscored_run_raises_instead_of_being_analysed(tmp_path, monkeypatch):
    root = tmp_path / "s"
    _run_dir(root / "data", name="2026-06-06", scored=False)
    sp = _load(root, monkeypatch)
    with pytest.raises(sp.RunNotFound):
        sp.resolve_run("2026-06-06")
    assert sp.resolve_run("2026-06-06", require_scored=False).name == "2026-06-06"


def test_neither_directory_present_raises_and_invents_nothing(tmp_path, monkeypatch):
    """An EXISTING study directory with neither data/ nor runs/ in it.

    The directory is created on purpose. A STUDY_ROOT that does not exist at all is a
    different error, raised at import with a message naming the bad path -- see the test
    below. Conflating the two is what this test used to do, and it passed only because the
    module tolerated a missing root long enough to reach runs_root()."""
    study = tmp_path / "empty"
    study.mkdir()
    sp = _load(study, monkeypatch)
    with pytest.raises(sp.RunNotFound):
        sp.runs_root()


def test_a_study_root_that_does_not_exist_fails_at_load(tmp_path, monkeypatch):
    """Fail fast, naming the path. A bad STUDY_ROOT that resolves lazily surfaces later as
    'no such run', which sends you looking for a missing run instead of a missing root."""
    with pytest.raises(ValueError, match="STUDY_ROOT is not a directory"):
        _load(tmp_path / "does-not-exist", monkeypatch)


def test_the_same_run_name_in_both_layouts_is_read_from_the_right_one(public_layout,
                                                                     private_layout,
                                                                     monkeypatch):
    """The regression the acceptance actually asks for: identical run names in two corpora,
    and each root must read its own."""
    (public_layout / "data" / "2026-05-25-full" / "scored" / "model.jsonl").write_text(
        '{"score_classifier": 1}\n', encoding="utf-8")
    (private_layout / "runs" / "2026-05-25-full" / "scored" / "model.jsonl").write_text(
        '{"score_classifier": 5}\n', encoding="utf-8")

    sp = _load(public_layout, monkeypatch)
    pub = sp.resolve_run("2026-05-25-full") / "scored" / "model.jsonl"
    assert json.loads(pub.read_text())["score_classifier"] == 1

    sp = _load(private_layout, monkeypatch)
    priv = sp.resolve_run("2026-05-25-full") / "scored" / "model.jsonl"
    assert json.loads(priv.read_text())["score_classifier"] == 5
    assert priv.parent.parent.parent.name != "data"
