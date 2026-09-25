"""A checker that exists and is declared nowhere is indistinguishable from a gap.

WHY THIS FILE EXISTS
--------------------
On 2026-09-16 this repository held 13 scripts named `check_*` / `validate_*` /
`audit_*` / `selftest_*`, 16 more carrying a `--check` flag, and a release
checklist that invoked 17 of them. Nothing recorded where the rest belonged.

Two of those were genuine oversights -- `check_arm_match.py` and
`check_undefined_names.py` were written, tested, and run by nothing. The others
were deliberate. From outside there was no way to tell which was which, and that
is the actual defect: not a missing check, but a repository that could not answer
"what do we verify, and what do we not."

`scripts/gates.py` is the one registry. This file makes it complete:

  - every checker on disk is declared, so a new one cannot be added without
    saying which stage runs it (or why none does);
  - every declared gate exists, so the registry cannot describe a check that was
    deleted;
  - a gate at stage "manual" carries a written reason, because "nothing runs this"
    without a reason is the pile this replaced;
  - the release checklist is DERIVED from the registry rather than typed beside
    it, so the two cannot disagree.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

import gates as G  # noqa: E402
import release_check as R  # noqa: E402

#: Scripts whose NAME says they check something. The prefix convention is the
#: repository's own, so a checker named outside it is caught by the --check sweep below.
CHECKER_PREFIXES = ("check_", "validate_", "audit_", "selftest_")

#: Declared here, with the reason, rather than silently skipped.
NOT_GATES = {
    "release_check.py": "the runner -- it executes the registry, so declaring it as one of "
                        "its own entries would make it run itself",
    "gates.py": "the registry itself",
    "check_no_key_repro.py": None,   # IS a gate; present in the registry
}


def _declared():
    return {g.script for g in G.GATES}


def _on_disk():
    out = set()
    for fn in sorted(os.listdir(SCRIPTS)):
        if not fn.endswith(".py") or fn.startswith("test_"):
            continue
        if fn.startswith(CHECKER_PREFIXES):
            out.add(fn)
    return out


def _with_check_flag():
    out = set()
    for fn in sorted(os.listdir(SCRIPTS)):
        if not fn.endswith(".py") or fn.startswith("test_"):
            continue
        try:
            src = open(os.path.join(SCRIPTS, fn), encoding="utf-8").read()
        except (IOError, OSError, UnicodeDecodeError):
            continue
        if re.search(r'add_argument\(\s*"--check"', src):
            out.add(fn)
    return out


def test_the_registry_is_not_empty():
    """A completeness check over an empty registry passes while saying nothing."""
    assert len(G.GATES) >= 20


def test_every_checker_on_disk_is_declared():
    undeclared = sorted(_on_disk() - _declared()
                        - {k for k, v in NOT_GATES.items() if v})
    assert not undeclared, (
        "these scripts are named like checkers and appear in no stage of gates.GATES, "
        "so nothing says whether their absence from the release gate is a decision or an "
        "oversight: %s" % undeclared)


def test_every_check_flag_is_declared():
    """A `--check` mode is a gate whatever the script is called."""
    undeclared = sorted(_with_check_flag() - _declared()
                        - {k for k, v in NOT_GATES.items() if v})
    assert not undeclared, (
        "these scripts carry a --check flag and are in no stage of gates.GATES: %s"
        % undeclared)


def test_every_declared_gate_exists():
    """A gate the registry names must exist in a tree that can run it.

    TREE-AWARE IN BOTH DIRECTIONS. `check_release_table.py` gates RELEASE-2026-09-07.md's arm
    inventory, and neither that gate nor the document it reads ships to the mirror;
    `calibration_study.py` and `three_axis_score.py` exist only in the mirror. Requiring
    every declared script to be present HERE would force one tree's gates to be deleted
    from a shared registry to make the other tree's test pass, which is how the registry
    would start lying about what the study verifies.

    So a gate is exempt exactly where its declared tree is not the one running.
    """
    def elsewhere(g):
        return (G.THIS_IS_MIRROR and g.tree == "study") or \
               (not G.THIS_IS_MIRROR and g.tree == "mirror")

    missing = sorted(g.script for g in G.GATES
                     if g.script != "pytest" and not elsewhere(g)
                     and not os.path.exists(os.path.join(SCRIPTS, g.script)))
    assert not missing, "declared in gates.GATES and not on disk: %s" % missing


def test_a_gate_declared_for_the_other_tree_really_exists_there():
    """The exemption above must not become a way to declare a script nobody wrote.

    Only the private tree can check this: it can see the mirror, and the mirror has no
    pointer back. It SKIPS in the mirror rather than passing, so "cannot check" never
    reads as "checked".
    """
    import pytest
    if G.THIS_IS_MIRROR:
        pytest.skip("the mirror cannot see the study tree; the working study verifies this")
    if G.MIRROR is None:
        pytest.skip("no mirror checked out beside this study tree (CI); the author's "
                    "workstation, which holds both, verifies this")
    sibling_scripts = os.path.join(G.MIRROR, "scripts")
    ghosts = sorted(g.script for g in G.GATES
                    if g.tree == "mirror" and g.script != "pytest"
                    and not os.path.exists(os.path.join(sibling_scripts, g.script)))
    assert not ghosts, (
        "declared as mirror gates and present in neither tree: %s" % ghosts)


def test_a_gate_nothing_runs_says_why():
    silent = [g.label for g in G.for_stage("manual") if not g.why.strip()]
    assert not silent, (
        "these gates are run by no stage and give no reason, which is the pile this "
        "registry replaced: %s" % silent)


def test_every_gate_declares_a_known_tree_and_stage():
    bad = [(g.label, g.tree, g.stage) for g in G.GATES
           if g.tree not in G.TREES or g.stage not in G.STAGES]
    assert not bad, bad


def test_every_gate_says_what_it_covers():
    silent = [g.label for g in G.GATES if not g.covers.strip()]
    assert not silent, "gates declaring no coverage: %s" % silent


def test_the_release_checklist_is_derived_from_the_registry():
    """Not a second copy. This is the invariant the derivation exists to hold."""
    labels = [label for label, _, _ in R.CHECKS]
    assert labels == [g.label for g in G.for_stage("release")], (
        "release_check.CHECKS has drifted from gates.for_stage('release')")


def test_a_gate_needing_an_absent_tree_reports_rather_than_runs():
    """The defect this replaced: study-side checks silently re-running in the mirror.

    A None cwd must come back as 2 (NOT APPLICABLE) without executing anything.
    """
    rc, out = R.run(None, "scripts/does_not_exist.py")
    assert rc == 2, rc
    assert "NOT APPLICABLE" in out


def test_no_release_gate_is_declared_for_a_tree_and_then_run_in_another():
    """Every release entry's cwd is the one its declared tree resolves to."""
    wrong = []
    for (label, cwd, _), g in zip(R.CHECKS, G.for_stage("release")):
        if cwd != g.cwd():
            wrong.append((label, cwd, g.cwd()))
    assert not wrong, wrong
