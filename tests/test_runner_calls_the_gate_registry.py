"""The collection runner must EXECUTE the pre-collection gate registry, not describe it.

WHY THIS FILE EXISTS
--------------------
`scripts/gates.py` has carried a `prerun` stage since it was written, and nothing executed it.
`release_check.py` was its only importer and it runs the RELEASE stage. `run_i3_wave.main()`
hand-wired exactly two of the prerun gates into itself -- the instrument sign-off and the
budget probe, each added the day after the defect it catches -- and the other eight sat in the
registry, named, described, and never called in front of a spend.

Two collection passes ran that way. When the registry was executed for the first time on
2026-09-17 it returned THREE RED, two of them red because they still pointed at the retired
external questionnaire, one of those being the leak gate that guards the public repository.

`gates.py` meanwhile told the reader, in its own `--run` help text, "this is what run_i3_wave
--run calls before it spends anything". That was false the day it was written. An independent
review found it by grepping for `gates` in the runner and getting nothing.

So this test asserts THE CALL SITE, not the behaviour -- the same shape as
`test_recollect_dedup_runs`, which exists because `recollect_at_cap.dedup` carried "called
automatically after a collection run" from the day it was written with no caller anywhere.
A correct, dead function is worse than an absent one, because it answers the question for
whoever greps.
"""
import ast
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "scripts"))

RUNNER = os.path.join(HERE, "scripts", "run_i3_wave.py")


def _tree():
    with open(RUNNER, encoding="utf-8") as fh:
        return ast.parse(fh.read(), filename=RUNNER)


def test_the_runner_calls_preflight():
    """A literal call to gates.preflight must exist in run_i3_wave."""
    calls = []
    for node in ast.walk(_tree()):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "preflight":
                calls.append(node)
    assert calls, (
        "run_i3_wave.py never calls preflight(). The gate registry has a `prerun` stage; if "
        "the runner does not execute it, the stage is a list and the list is checked by "
        "whoever remembers it -- which is how two collection passes ran with three gates red.")


def test_preflight_is_called_on_the_prerun_stage():
    for node in ast.walk(_tree()):
        if isinstance(node, ast.Call) and getattr(node.func, "attr", None) == "preflight":
            args = [a for a in node.args if isinstance(a, ast.Constant)]
            kw = {k.arg: k.value for k in node.keywords if isinstance(k.value, ast.Constant)}
            stage = (args[0].value if args else None) or (
                kw["stage"].value if "stage" in kw else None)
            assert stage == "prerun", ("preflight called on stage %r; the pre-collection "
                                       "gates are the `prerun` stage" % stage)
            return
    raise AssertionError("no preflight() call found")


def test_a_failed_gate_refuses_the_collection():
    """The result of preflight must be branched on, not printed and ignored.

    A gate whose verdict is displayed and then walked past is a gate that has been turned
    into a log line.
    """
    src = open(RUNNER, encoding="utf-8").read()
    idx = src.find("preflight(")
    assert idx > 0
    after = src[idx:idx + 1200]
    assert "REFUSING TO COLLECT" in after, (
        "preflight()'s result is not followed by a refusal path -- the runner must return "
        "non-zero when a pre-collection gate fails, the way it does for the instrument "
        "sign-off and the budget probe")
    assert "return 2" in after, "a failed preflight must exit non-zero"


def test_the_registry_still_has_a_prerun_stage_with_gates_in_it():
    """And the stage must not be emptied to make the wiring vacuous."""
    import gates as G
    rows = G.for_stage("prerun")
    assert len(rows) >= 4, (
        "only %d gate(s) at stage prerun -- wiring the runner to an empty stage is a "
        "preflight that checks nothing and reports success" % len(rows))
    # Every prerun gate must be invocable: a gate registered with a command line its script
    # rejects exits 2 on its usage message, which this project's convention reads as NOT
    # APPLICABLE. `check_arm_match.py` sat registered with no arguments and read as n/a from
    # the day the registry was written until 2026-09-17.
    for g in rows:
        assert g.label, g
        assert g.covers, "gate %r says nothing about what it covers" % g.label
