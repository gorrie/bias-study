"""A denial that names a path which exists must fail the gate.

The dead-path check catches a document crediting work nobody did. This is the inverse and
rarer failure: a document DENYING work somebody did. It is worse, because it reads as rigour.
An unflattering admission is self-authenticating -- nobody challenges a project for saying it
has not done something -- so a false denial can retire a finished control back into the
backlog and survive every subsequent read.

These fixtures are synthetic. The check has to fire on the SHAPE of the sentence, not on any
particular one that was once in this repository.
"""
import io
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_skill_docs as C  # noqa: E402


def tree(tmp_path, filename, body, script="widget.py"):
    """A miniature study root: one real script, one document that talks about it."""
    (tmp_path / "scripts").mkdir(exist_ok=True)
    (tmp_path / "scripts" / script).write_text("# real\n", encoding="utf-8")
    io.open(tmp_path / filename, "w", encoding="utf-8", newline="").write(body)
    return C.check_false_denials(root=str(tmp_path))


def test_denial_of_an_existing_script_fails(tmp_path):
    hits = tree(tmp_path, "RESULTS-2026-01-01-x.md",
                "The control is open.\n"
                "`scripts/widget.py` was never written and does not exist.\n")
    assert hits, "a denial naming a path that exists must be caught"
    assert hits[0][1] == "scripts/widget.py"
    assert "was never written" in hits[0][2]


def test_denial_in_a_module_docstring_fails(tmp_path):
    hits = tree(tmp_path, "scripts/other.py",
                '"""Audit.\n\nIt is NOT STARTED -- scripts/widget.py, no harness, never begun.\n"""\n')
    assert hits, "module docstrings are where these claims actually live"


def test_denial_one_line_away_still_fails(tmp_path):
    hits = tree(tmp_path, "RESULTS-2026-01-01-x.md",
                "Method 8 is the only control that can see a shared lean.\n"
                "It does not exist.\n"
                "The harness would be `scripts/widget.py`.\n")
    assert hits, "the assertion and the path are rarely on the same line"


def test_quoting_a_withdrawn_denial_is_the_fix_not_the_defect(tmp_path):
    hits = tree(tmp_path, "RESULTS-2026-01-01-x.md",
                "Corrected: this file used to say `scripts/widget.py` has never been "
                "committed. It is committed and the sheet is drawn.\n")
    assert not hits, "a correction quoting the old claim must not trip the gate"


def test_denial_of_a_path_that_really_is_absent_is_allowed(tmp_path):
    hits = tree(tmp_path, "RESULTS-2026-01-01-x.md",
                "`scripts/ghost.py` has never been committed and no sheet exists.\n")
    assert not hits, "an honest denial about an absent path is the whole point of saying it"


def test_honest_prose_about_missing_data_does_not_trip(tmp_path):
    hits = tree(tmp_path, "RESULTS-2026-01-01-x.md",
                "`scripts/widget.py` reports 466 records with missing responses; the wave-0\n"
                "cells are absent and the arm was never run to its final n.\n")
    assert not hits, "soft words about missing DATA must not be read as denying a script"


def test_the_live_tree_has_no_false_denials():
    assert C.check_false_denials() == []
