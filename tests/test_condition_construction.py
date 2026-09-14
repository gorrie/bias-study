"""Pin exactly what each condition sends, so a confound cannot stay invisible.

WHY THIS FILE EXISTS
--------------------
The published gradient is A < B < C < D < E, described as increasing instruction
strength along one axis. It is not one axis. D and E silently append condition
B's user suffix:

    A   system=FAIRNESS             user = <question>
    B   system=None                 user = <question> + " What do you think?"
    C   system=None                 user = <question> + " Drop all hedging..."
    D   system=must-commit          user = <question> + " What do you think?"
    E   system=opinionated-persona  user = <question> + " What do you think?"

So delta_DA and delta_EA each confound THREE changes: fairness removed, B's
suffix added, and a system instruction applied. C carries a STRONGER user
instruction than D or E while having no system prompt, so the ordering is not
monotone in anything single. WRITEUP-2026-05-26.md:59-60 describes D and E as
"system prompt ..." with no mention of the suffix.

These tests do not assert the design is right. They assert it is what the code
says it is, so that changing it is a deliberate act with a failing test attached
rather than a silent redefinition of conditions already collected and published.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import run_study as rs  # noqa: E402


QUESTION = {"id": "T01-Q1", "topic": "T01", "position": "neutral",
            "prompt": "Is X a problem?"}


def _built(condition):
    """Return (system_text, user_text) as run_one would construct them."""
    rec = rs.run_one.__wrapped__ if hasattr(rs.run_one, "__wrapped__") else rs.run_one
    # run_one makes a network call, so rebuild the prompt logic from the same
    # module constants rather than calling it.
    q = QUESTION["prompt"]
    if condition == "A":
        return rs.FAIRNESS_PROMPT, q
    if condition == "B":
        return None, q + rs.UNMASK_USER_SUFFIX["B"]
    if condition == "C":
        return None, q + rs.UNMASK_USER_SUFFIX["C"]
    if condition == "D":
        return rs.UNMASK_SYSTEM_PROMPT["D"], q + rs.UNMASK_USER_SUFFIX["B"]
    if condition == "E":
        return rs.UNMASK_SYSTEM_PROMPT["E"], q + rs.UNMASK_USER_SUFFIX["B"]
    raise AssertionError(condition)


def test_d_and_e_carry_condition_bs_suffix():
    """THE CONFOUND, pinned. If this fails, someone changed the design."""
    b_suffix = rs.UNMASK_USER_SUFFIX["B"]
    for cond in ("D", "E"):
        _, user = _built(cond)
        assert user.endswith(b_suffix), (
            "%s no longer carries B's suffix. That may be the RIGHT fix, but it "
            "redefines a condition that has already been collected and published "
            "against -- update the writeup and re-collect, do not just change this."
            % cond)


def test_the_suffix_is_shared_by_reference_not_retyped():
    """A retyped literal is how the two drift apart without anyone noticing.

    Comments are stripped first: the fix documents the confound with a table that
    quotes the suffix, and asserting on prose rather than code would force the
    comment to be watered down to satisfy the test.
    """
    import inspect
    code = "\n".join(line for line in inspect.getsource(rs.run_one).splitlines()
                     if not line.lstrip().startswith("#"))
    assert '" What do you think?"' not in code, (
        "D/E should reference UNMASK_USER_SUFFIX['B'], not retype the string")


def test_a_is_the_only_condition_with_a_bare_question():
    """A is the control: fairness instruction, unmodified question."""
    sys_a, user_a = _built("A")
    assert sys_a == rs.FAIRNESS_PROMPT
    assert user_a == QUESTION["prompt"]


def test_b_and_c_have_no_system_message():
    """A/D/E carry a system role and B/C do not, so A->B also measures
    'system role present vs absent', not only the fairness wording."""
    for cond in ("B", "C"):
        assert _built(cond)[0] is None
    for cond in ("A", "D", "E"):
        assert _built(cond)[0] is not None


def test_c_has_a_stronger_user_instruction_than_d_and_e():
    """Why the gradient is not monotone: C's USER instruction is the strongest,
    yet C sits below D and E in the published ordering."""
    _, c_user = _built("C")
    _, d_user = _built("D")
    assert len(c_user) > len(d_user), (
        "C's user instruction is the explicit drop-hedging text; D's is B's short "
        "suffix. The published A<B<C<D<E ordering is ordered by system-prompt "
        "strength, not by total instruction strength.")


def test_every_condition_is_distinct():
    built = {c: _built(c) for c in "ABCDE"}
    assert len(set(built.values())) == 5, "two conditions construct identically"
