"""I3's baseline must be an ABSENCE of instruction, not a quieter one.

WHY THIS FILE EXISTS
--------------------
The judged study made the fairness instruction the ORIGIN. That is why 100% of
its condition-A records sit at the rubric midpoint and why every published
`B - A` is arithmetically `B - 3`: the baseline was an instruction to produce the
midpoint, so the contrast measured obedience.

I3 inverts it. `N` -- no instruction at all -- becomes the baseline, and the
fairness instruction becomes a treatment:

    F - N   does the fairness instruction suppress, against no instruction
    P - N   how much of that is merely "an instruction was present"
    C - P   does commit-force go beyond a content-free instruction

None of that works if `N` quietly carries an instruction. Nothing in the existing
condition table is bare: `B` has no system prompt but appends "What do you
think?", and `C` appends a drop-hedging sentence. Using `B` as the baseline would
have made the inversion cosmetic and the whole of Phase 4 uninterpretable.

The same defect already shipped here once -- conditions D and E silently carried
B's user suffix, so `delta_DA` and `delta_EA` each confounded three changes at
once.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import run_compass as RC  # noqa: E402

ITEMS = [{"id": 1, "mirror_of": 2, "text": "A proposition."},
         {"id": 2, "mirror_of": 1, "text": "A proposition, negated."}]


def _messages(condition):
    return RC.build_prompt(ITEMS, condition=condition)


def test_N_exists_as_a_condition():
    assert "N" in RC.CONDITION_SYSTEM, "the bare baseline condition is missing"
    assert "N" in RC.CONDITION_NOTE, "N has no note; an unexplained condition is a trap"


def test_N_has_no_system_prompt():
    assert RC.CONDITION_SYSTEM["N"] is None
    roles = [m["role"] for m in _messages("N")]
    assert "system" not in roles, "the bare condition sent a system prompt"


def test_N_has_no_user_suffix():
    """The specific way B fails to be bare."""
    assert "N" not in RC.CONDITION_USER_SUFFIX
    user = [m for m in _messages("N") if m["role"] == "user"][0]["content"]
    assert "What do you think" not in user
    assert "Drop all hedging" not in user


def test_B_is_not_bare_and_must_not_be_used_as_the_baseline():
    """Asserted so nobody substitutes B for N later and calls it the same thing."""
    user = [m for m in _messages("B") if m["role"] == "user"][0]["content"]
    assert "What do you think" in user, (
        "B no longer carries its suffix; if that was deliberate, the judged study's "
        "published B - A numbers no longer describe what B was")


def test_N_and_B_produce_different_prompts():
    n = [m for m in _messages("N") if m["role"] == "user"][0]["content"]
    b = [m for m in _messages("B") if m["role"] == "user"][0]["content"]
    assert n != b


def test_the_four_i3_conditions_are_all_distinct():
    """F, P, C and N must differ, or a contrast between them measures nothing."""
    seen = {}
    for cond in ("N", "A", "P", "D"):
        msgs = _messages(cond)
        sig = tuple((m["role"], m["content"]) for m in msgs)
        assert sig not in seen, "%s constructs identically to %s" % (cond, seen[sig])
        seen[sig] = cond
    assert len(seen) == 4


def test_the_placebo_carries_no_stance_content():
    """P is the control that separates 'an instruction was present' from a lean."""
    sys_text = (RC.CONDITION_SYSTEM["P"] or "").lower()
    assert sys_text, "P has no system prompt; it is not a placebo"
    import re
    for banned in ("balance", "balanced", "position", "positions", "opinion", "opinions",
                   "stance", "hedge", "hedging", "commit", "side", "sides", "neutral"):
        assert not re.search(r"\b%s\b" % banned, sys_text), (
            "the placebo mentions %r; it is supposed to carry no stance content" % banned)


def test_the_placebo_is_still_an_imperative_like_the_force_conditions():
    """Matched on register, or it controls for nothing."""
    p = RC.CONDITION_SYSTEM["P"]
    d = RC.CONDITION_SYSTEM["D"]
    assert p.startswith("You must") and d.startswith("You must")
    assert "forbidden" in p and "forbidden" in d
    assert 0.5 < len(p) / len(d) < 2.0, "the placebo is not comparable in length to D"
