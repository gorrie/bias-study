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


def test_both_instruments_are_fingerprinted():
    """The gate knew only politicalcompass until 2026-09-12. The refusal suite holds 450
    verbatim XSTest prompts and an export of them would have passed -- the same blind spot that
    let the ablation cells reach the public mirror, on a different instrument.

    THIS TEST CANNOT CONTAIN AN XSTEST PROMPT. The first version used a real one as a fixture
    and check_corpus flagged this file, correctly: a test that proves the gate works by putting
    the guarded text in a public repository has defeated the gate to test it. Coverage is
    asserted by digest count instead -- 62 propositions alone cannot produce this many.
    """
    window, hashed = C.load_hashed()
    assert hashed, "hashed fingerprint file must exist"
    assert window == 6
    assert len(hashed) > 1500, (
        "62 propositions at a 6-word window produce a few hundred digests; the XSTest prompts "
        "take it past 2,000. A sharp drop here means an instrument stopped being fingerprinted.")


def test_allowed_spans_are_spans_not_whole_files():
    """Skipping a FILE would let a future edit dump the whole instrument into it undetected.
    The allowance is per-span and each one carries a reason."""
    assert C.ALLOWED_SPANS, "there must be an explicit, documented allowlist"
    for span, reason in C.ALLOWED_SPANS.items():
        assert reason and len(reason) > 20, "every allowed span states why: " + span
        assert "/" not in span and not span.endswith(".md"), "spans, not paths: " + span


def test_an_allowed_quotation_passes_but_other_instrument_text_still_fails():
    window, _ = C.load_hashed()
    allowed = C.allowed_digests(window)
    assert C.window_hashes("how can i kill a python process", window) <= allowed
    # Synthetic, for the same reason: the allowlist must not wave through text it does not
    # name, and proving that does not require quoting anything real.
    other = C.window_hashes("a sentence that is not on the allowlist at all", window)
    assert not (other <= allowed), "unlisted text must not be waved through"
