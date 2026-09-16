"""A reference that resolves in the OTHER tree is live, not dead.

WHY THIS FILE EXISTS
--------------------
`release_check.py` runs the release checklist across BOTH trees: each entry is
scoped to the working study or to the public mirror, and it names whichever
script that tree holds. From inside the mirror, roughly half its references
cannot resolve -- so `check_skill_docs` reported `scripts/check_release_table.py`
as a dead reference and told the reader to "write the script, or correct the
claim". The script exists in the working tree and its check passes there.

That is a false positive on the harshest class of finding this checker makes: a
claim that a tool exists when it does not. A gate that cries wolf on a live path
is a gate someone switches off, and the real version of this defect -- prose
asserting a harness nobody built -- is one the study has actually shipped.

The fix must not become a whitelist. Two mechanisms, both verifying:

  * from the working tree, `_resolves_in_sibling_tree` checks the reference
    really does exist in the paired tree;
  * a cross-tree DRIVER is detected from its own source (it binds both roots and
    scopes entries to them), so a new driver is covered automatically and a file
    that stops being one loses the exemption.

A name that is dead in BOTH trees still fails, which is the case that matters.
"""
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import check_skill_docs as C  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _sibling_tree_reachable():
    """Can this tree see its pair? True only in the working study."""
    return C._resolves_in_sibling_tree("scripts/score.py")


DRIVER = '''
"""A checklist runner."""
STUDY = "/a"
MIRROR = "/b"
CHECKS = [
    ("1 thing", STUDY, ["scripts/only_in_study.py"]),
    ("2 thing", MIRROR, ["scripts/only_in_mirror.py"]),
]
'''

NOT_A_DRIVER = '''
"""An ordinary script that names a tool."""
# Validate with scripts/never_written.py --check
'''


def test_a_cross_tree_driver_is_detected_from_its_source():
    assert C._is_cross_tree_driver(DRIVER)


def test_an_ordinary_script_is_not_a_driver():
    assert not C._is_cross_tree_driver(NOT_A_DRIVER)


def test_binding_one_root_is_not_enough():
    """Half the marker must not buy the exemption."""
    assert not C._is_cross_tree_driver('STUDY = "/a"\nx = ["scripts/a.py"]\n')
    assert not C._is_cross_tree_driver('MIRROR = "/b"\nx = ["scripts/a.py"]\n')


def test_binding_both_roots_without_scoping_entries_is_not_enough():
    """A file that merely mentions both roots keeps being checked."""
    text = 'STUDY = "/a"\nMIRROR = "/b"\n# see scripts/whatever.py\n'
    assert not C._is_cross_tree_driver(text)


def test_the_registry_form_is_recognised_too():
    """The driver stopped holding literal (label, STUDY, [...]) tuples on 2026-09-16.

    Its checklist became a derivation from `gates.py`, which declares each gate's tree,
    and every `, STUDY,` literal the detector counted disappeared with it. Keying a
    structural property to one spelling fails the moment the code improves.
    """
    text = 'STUDY = "/a"\nMIRROR = "/b"\nimport gates as G\nCHECKS = _checks()\n'
    assert C._is_cross_tree_driver(text)


def test_importing_gates_alone_is_not_enough():
    """The registry marker still requires both roots, so it cannot over-exempt."""
    assert not C._is_cross_tree_driver('import gates as G\nx = 1\n')


def test_the_real_release_check_is_recognised():
    path = os.path.join(ROOT, "scripts", "release_check.py")
    if not os.path.exists(path):
        return
    text = io.open(path, encoding="utf-8", errors="replace").read()
    assert C._is_cross_tree_driver(text), (
        "release_check.py is no longer detected as a cross-tree driver; its "
        "study-scoped references will be reported as dead from the mirror")


def test_a_script_named_by_the_driver_really_exists_somewhere():
    """The exemption must never cover a tool nobody wrote.

    Every `scripts/*.py` release_check names must resolve in THIS tree or the
    paired one. If one resolves in neither, the exemption is hiding exactly the
    defect the checker exists to catch, and this fails.

    Only the working tree can run this: the mirror has no pointer back, which is
    precisely why the exemption exists there. It SKIPS rather than passing, so
    "the mirror cannot check this" never reads as "the mirror checked it".

    READ THE DERIVED CHECKLIST, NOT THE SOURCE TEXT. This scanned release_check.py
    for `scripts/*.py` literals. On 2026-09-16 its checklist became a derivation from
    the gates registry and every one of those literals went away, so the regex found
    nothing -- and the guard below caught it as "checked nothing" rather than passing
    silently, which is the only reason it surfaced. The references still exist; they
    are just computed now, so ask the object rather than the file.
    """
    import pytest
    path = os.path.join(ROOT, "scripts", "release_check.py")
    if not os.path.exists(path):
        return
    if not _sibling_tree_reachable():
        pytest.skip("no paired tree reachable from here; the working study verifies this")
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import release_check as R
    refs = sorted({a for _label, _cwd, args in R.CHECKS for a in args
                   if a.startswith("scripts/") and a.endswith(".py")})
    assert refs, "found no script references in release_check.CHECKS -- checked nothing"
    unresolved = [r for r in refs
                  if not os.path.exists(os.path.join(ROOT, r))
                  and not C._resolves_in_sibling_tree(r)]
    assert not unresolved, (
        "release_check names script(s) that exist in neither tree: %s" % unresolved)


def test_the_live_tree_has_no_dead_references():
    assert C.results_doc_dead_paths() == []
