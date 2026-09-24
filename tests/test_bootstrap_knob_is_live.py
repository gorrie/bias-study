"""A tuning knob that looks set and is not.

2026-09-18. `check_outcomes_computable._fast()` sets `position_analysis.BOOTSTRAP_N = 200`
around the gate's analysis, with a comment saying why: "a pre-collection gate that takes
minutes is a gate people skip -- which is the failure mode every skipped gate in this project
has had."

Three functions in `position_analysis` wrote the draw count into their signature as
`n=BOOTSTRAP_N`. Python evaluates a default once, at import. So the assignment reached nothing
and the gate ran 20,000 draws believing it ran 200 -- a hundred times its budget. On a corpus
that had grown from 702 records to 2,599 it passed the 900s gate timeout, the runner read the
timeout as a defect, and TWO COLLECTION STAGES WERE REFUSED with nothing wrong with them.

Measured after the fix: the same gate, same corpus, >600s -> 11.8s.

This is not a performance test. It is a test that the knob is connected, because the failure
mode of a disconnected knob is that everything looks deliberate. Two things are asserted:

  1. STRUCTURAL -- no module that defines a BOOTSTRAP_N may freeze it into a signature
     default. This catches the trap in the four other modules that carry the same shape
     before anyone monkeypatches one of them.
  2. BEHAVIOURAL -- setting the global actually changes the number of draws taken. Structure
     can be satisfied while the value is read from somewhere else entirely.
"""
import ast
import glob
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
SCRIPTS = os.path.join(STUDY, "scripts")
sys.path.insert(0, SCRIPTS)


def _modules_defining(name):
    """Every script that assigns `name` at module level, with its parsed tree."""
    out = []
    for path in sorted(glob.glob(os.path.join(SCRIPTS, "*.py"))):
        try:
            with open(path, encoding="utf-8") as fh:
                tree = ast.parse(fh.read(), filename=path)
        except SyntaxError:                                      # pragma: no cover
            continue
        for node in tree.body:
            targets = (node.targets if isinstance(node, ast.Assign)
                       else [node.target] if isinstance(node, ast.AnnAssign) else [])
            if any(isinstance(t, ast.Name) and t.id == name for t in targets):
                out.append((path, tree))
                break
    return out


def test_at_least_one_module_defines_the_knob():
    """A scan that finds nothing must not read as clean."""
    found = _modules_defining("BOOTSTRAP_N")
    assert found, "no script defines BOOTSTRAP_N -- this test is checking nothing"


@pytest.mark.parametrize("path,tree", _modules_defining("BOOTSTRAP_N"),
                         ids=lambda v: os.path.basename(v) if isinstance(v, str) else "")
def test_no_signature_freezes_the_draw_count(path, tree):
    """`def f(..., n=BOOTSTRAP_N)` binds at import and never sees a later assignment."""
    frozen = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        args = node.args
        for default in list(args.defaults) + [d for d in args.kw_defaults if d is not None]:
            if isinstance(default, ast.Name) and default.id == "BOOTSTRAP_N":
                frozen.append("%s() line %d" % (node.name, node.lineno))
    assert not frozen, (
        "%s freezes BOOTSTRAP_N into a signature default: %s.\n"
        "The default is evaluated at import, so assigning the module global later is a no-op "
        "and any caller that tries to turn the cost down is silently ignored. Take `n=None` "
        "and read the global inside the body."
        % (os.path.basename(path), ", ".join(frozen)))


def test_setting_the_global_changes_the_work_done():
    """Structure is not enough -- the value has to be the one actually used."""
    import position_analysis as P

    seen = []

    class Counting:
        """A Random whose randrange calls we can count."""

        def __init__(self, inner):
            self._inner = inner

        def __getattr__(self, attr):
            return getattr(self._inner, attr)

        def randrange(self, *a, **k):
            seen.append(1)
            return self._inner.randrange(*a, **k)

    real_random = P.random.Random
    values = [0.1, -0.2, 0.3, 0.05, -0.11, 0.22, 0.0, 0.4]
    keep = P.BOOTSTRAP_N
    counts = {}
    try:
        P.random.Random = lambda *a, **k: Counting(real_random(*a, **k))
        for n in (50, 500):
            seen.clear()
            P.BOOTSTRAP_N = n
            P._boot(values, seed=1)
            counts[n] = len(seen)
    finally:
        P.random.Random = real_random
        P.BOOTSTRAP_N = keep

    k = len(values)
    assert counts[50] == 50 * k, (
        "BOOTSTRAP_N=50 drew %d samples, expected %d -- the global is not what _boot reads"
        % (counts[50], 50 * k))
    assert counts[500] == 500 * k, (
        "BOOTSTRAP_N=500 drew %d samples, expected %d" % (counts[500], 500 * k))


def test_the_gate_helper_actually_reduces_the_cost():
    """`_fast()` is the caller this whole thing exists for. Assert it bites."""
    import check_outcomes_computable as C
    import position_analysis as P

    before = P.BOOTSTRAP_N
    inside = C._fast(lambda: P.BOOTSTRAP_N)
    assert inside == C.GATE_BOOTSTRAP, (
        "_fast() ran the body at BOOTSTRAP_N=%r, not the gate's %r"
        % (inside, C.GATE_BOOTSTRAP))
    assert P.BOOTSTRAP_N == before, "_fast() did not restore BOOTSTRAP_N"
    assert C.GATE_BOOTSTRAP < before, (
        "the gate's draw count (%d) is not below the real one (%d), so it saves nothing"
        % (C.GATE_BOOTSTRAP, before))
