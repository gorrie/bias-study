"""An untracked file carrying instrument text must be caught before it is committed."""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_corpus as C


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo)] + list(args), capture_output=True, check=False)


def test_untracked_files_are_scanned(tmp_path, monkeypatch):
    """THE 2026-09-12 DEFECT. Twelve files with verbatim instrument text were copied in,
    `--all` was run and passed because `git ls-files` does not list untracked files, and they
    were committed and pushed on that green result. The check only went red afterwards."""
    repo = tmp_path / "r"
    (repo / "sub").mkdir(parents=True)
    _git(repo, "init", "-q")
    (repo / "tracked.txt").write_text("nothing here\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "-c", "user.name=F", "-c", "user.email=f@x.invalid", "commit", "-qm", "f")
    (repo / "sub" / "untracked.jsonl").write_text("leaked\n", encoding="utf-8")

    monkeypatch.setattr(C, "ROOT", str(repo))
    listed = C.tracked_files()
    assert "tracked.txt" in listed
    assert "sub/untracked.jsonl" in listed, "an untracked file is one `git add -A` from shipping"


def test_ignored_files_are_not_scanned(tmp_path, monkeypatch):
    """--exclude-standard: a gitignored file is not about to ship, and flagging it would train
    people to ignore this gate."""
    repo = tmp_path / "r2"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / ".gitignore").write_text("secret/\n", encoding="utf-8")
    (repo / "secret").mkdir()
    (repo / "secret" / "x.jsonl").write_text("private\n", encoding="utf-8")
    _git(repo, "add", ".gitignore")
    _git(repo, "-c", "user.name=F", "-c", "user.email=f@x.invalid", "commit", "-qm", "f")

    monkeypatch.setattr(C, "ROOT", str(repo))
    assert "secret/x.jsonl" not in C.tracked_files()
