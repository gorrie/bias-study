"""The reproduction check must be baselined on HEAD, not on the tree it found.

WHY THIS FILE EXISTS
--------------------
`check_no_key_repro.py` prints "every documented no-key command runs with no key
and changes nothing." Twice, that sentence was false and the check could not tell,
and BOTH times running it a second time was enough to clear it:

  1. It compared `git status --porcelain` before and after and reported the set
     difference. `aggregate.py` wrote `run-summary.json` with no trailing newline,
     so run 1 left the file modified and failed correctly -- and run 2 found the
     file already in `before`, computed an empty delta, and passed.
  2. Replaced with sha256 before and after, in the same invocation. Run 2 digested
     the already-rewritten file as its own baseline, got the same hash back, and
     passed again.

Both compared the working tree against itself. The question is not "did anything
move in the last minute" but "does the documented reproduction return the artifact
this repository ships", and that has one baseline: HEAD.

A fourth failure mode was found while fixing the third: `WRITES` named
`data/<run>/per-model.csv` when aggregate writes `data/<run>/aggregated/per-model.csv`,
so three of four entries matched nothing, were skipped by the `exists()` test, and
the comparison covered a single file while reading as though it covered four.
"""
import io
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import check_no_key_repro as R  # noqa: E402


def test_the_declared_outputs_actually_exist():
    """A path that matches nothing is skipped silently, which shrinks the check invisibly."""
    present = R.tracked_outputs()
    assert present, (
        "no declared output names a tracked file that exists, so the reproduction comparison "
        "runs over nothing and still reports 'changes nothing': %r" % (R.output_paths(),))
    # Two, not four: the two trees use different run roots -- the mirror keeps the May study
    # under `data/` with four aggregated outputs, the working tree under `runs/` with two.
    # Asserting four made this test a mirror-only test that failed in the tree it was synced
    # to, which is how a shared gate acquires a tree it cannot run in.
    assert len(present) >= 2, (
        "only %d declared reproduction output(s) are present and tracked -- the rest are "
        "skipped by the exists() test and the comparison silently narrows: %r"
        % (len(present), present))


def test_the_tree_is_currently_reproducible():
    """The gate's real verdict, so a regression fails here rather than at release."""
    assert R.differs_from_committed() == []


def test_a_difference_is_detected_even_when_it_was_already_there():
    """THE REGRESSION, named. This is what defeated both earlier versions.

    A pre-existing modification must still be reported. If this passes only for changes
    made during the check's own run, re-running a red check turns it green.
    """
    target = R.tracked_outputs()[0]
    path = os.path.join(str(R.ROOT), target)
    original = io.open(path, "rb").read()
    try:
        io.open(path, "wb").write(original + b"\n# planted\n")
        # Note there is no "before" snapshot taken here on purpose: the file was already
        # modified when differs_from_committed() is called, exactly as it would be on the
        # second run of a check that had dirtied the tree on its first.
        assert target in R.differs_from_committed(), (
            "a modification that predates the call went unreported, so the baseline is the "
            "working tree rather than HEAD and the check can be cleared by re-running")
    finally:
        io.open(path, "wb").write(original)
    assert R.differs_from_committed() == [], "restore failed; the tree is left dirty"


def test_aggregate_writes_a_trailing_newline():
    """The specific irreproducibility: one byte, and it made the check dirty its own tree."""
    src = io.open(os.path.join(str(R.ROOT), "scripts", "aggregate.py"), encoding="utf-8").read()
    marker = 'json.dumps(summary, indent=2, sort_keys=True) + "\\n", encoding="utf-8")'
    assert marker in src, (
        "aggregate.py no longer appends a trailing newline to run-summary.json; every run "
        "will leave the committed file modified by exactly one character")


def test_git_is_available_or_the_check_would_pass_vacuously():
    """differs_from_committed() reads a returncode. No git, no comparison, silent green."""
    r = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"],
                       cwd=str(R.ROOT), capture_output=True, text=True, timeout=60)
    assert r.returncode == 0 and r.stdout.strip() == "true", r.stdout + r.stderr
