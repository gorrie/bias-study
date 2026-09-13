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


def test_missing_plaintext_fingerprints_fails_closed_rather_than_crashing(tmp_path, monkeypatch):
    """It raised FileNotFoundError out of load_fingerprints, so the gate did not run at all.
    A gate that crashes is a gate somebody comments out of CI."""
    monkeypatch.setattr(C, "FINGERPRINTS", str(tmp_path / "absent"))
    assert C.load_fingerprints() == []


def test_hashed_only_is_opt_in(tmp_path, monkeypatch, capsys):
    """Hashes cover all 62 propositions and reproduce none, so a tree can deliberately not ship
    the ten plaintext fragments -- but only by saying so. The plaintext list is what catches a
    wrongly-regenerated hash file, and dropping it silently would be a quiet weakening."""
    # _is_public_mirror is patched True because this asserts the FINGERPRINT logic, which only
    # runs in the mirror -- in the private study main() returns 2 (not applicable) before
    # reaching it. Without this the test passes in one tree and fails in the other, which is
    # how a shared test teaches people that red is normal.
    monkeypatch.setattr(C, "_is_public_mirror", lambda: True)
    monkeypatch.setattr(C, "FINGERPRINTS", str(tmp_path / "absent"))
    assert C.main(["--all"]) == 1
    assert "refusing to pass" in capsys.readouterr().out
