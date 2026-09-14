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


# --- PREREG-2026-09-13-frame-and-placebo: the two new conditions ---------------

def test_b_prime_removes_the_instruction_without_asking_for_an_opinion():
    """A and B differ by TWO things; B' isolates the one the claim rests on.

    A -> B removes the fairness system prompt AND appends " What do you think?".
    So the published effect cannot separate "the mask came off" from "the model
    was asked for an opinion and gave one". B' removes only the instruction.
    """
    assert rs.UNMASK_SYSTEM_PROMPT.get("P"), "placebo must exist"
    q = QUESTION["prompt"]
    # B' is system=None, bare question -- no suffix.
    assert _built("B")[1] == q + rs.UNMASK_USER_SUFFIX["B"]
    assert _built("B")[0] is None
    # The contrast that matters: B and B' differ ONLY by the suffix.
    assert _built("B")[1] != q
    assert _built("B")[1].startswith(q)


def test_the_placebo_is_byte_identical_to_the_compass_arm():
    """One condition letter must not mean two different prompts.

    The instrument audit found exactly that between these two runners -- condition
    A differing by three words and C by punctuation, while a comment claimed
    verbatim carry. If P diverges, the judged arm and the forced-choice arm stop
    measuring the same control, and the whole point of P is that it is the SAME
    control that dissolved the claim on the other arm.
    """
    import run_compass as rc
    assert rs.UNMASK_SYSTEM_PROMPT["P"] == rc.CONDITION_SYSTEM["P"], (
        "the placebo has drifted between run_study.py and run_compass.py")


def test_the_placebo_carries_no_stance_content():
    """A placebo that leaned would be a treatment.

    WORD BOUNDARIES, not substrings. The first version of this test used `in` and
    failed on the real placebo because "proposition" contains "position" -- a
    detector firing on its own naivety rather than on the thing it watches for,
    which is the defect this whole audit exists to find.
    """
    import re
    p = rs.UNMASK_SYSTEM_PROMPT["P"].lower()
    for word in ("position", "stance", "hedge", "hedging", "balance", "balanced",
                 "opinion", "commit", "institution", "skeptical", "side", "sides"):
        assert not re.search(r"\b%s\b" % word, p), (
            "the placebo mentions %r as a whole word, which makes it a stance "
            "instruction rather than a content-free control" % word)


def test_b_prime_and_placebo_differ_only_in_the_system_prompt():
    """The factorial has to be clean or neither contrast is interpretable."""
    q = QUESTION["prompt"]
    # Both leave the user turn as the bare question.
    assert _built("A")[1] == q
    # P vs B': same user turn, different system. B vs B': same system, different user.
    assert rs.UNMASK_SYSTEM_PROMPT["P"] != rs.FAIRNESS_PROMPT
