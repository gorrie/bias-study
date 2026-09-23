#!/usr/bin/env python3
"""The two-call demo: the same model, the same questions, two instructions.

WHAT THE AUDIENCE SEES
----------------------
Put the study's 32 propositions -- `data/ratchet-battery.json`, author-written, 16 mirrored
pairs -- to a frontier model with a system prompt asking it to answer in a balanced manner.
It declines all 32 and explains why, in a paragraph. Put the same 32 propositions to the same
model under an instruction with no political content in it at all -- read every proposition
carefully, careless reading is forbidden -- and it answers all 32.

The counter goes 0/32, then 32/32. That is the whole demo, and it is the paper's §1b in
twenty seconds: the refusal rate everyone publishes is substantially a property of the
sentence the researcher wrote, not of the model.

REBUILT 2026-09-22 ON THE BATTERY
---------------------------------
The previous version of this file ran the retired 62-item external questionnaire, on
`google/gemini-3.7-flash`, and read "0 / 62, then 62 / 62". Neither half survives: the
questionnaire was retired on 2026-09-17 and its corpus deleted on 2026-09-22, and on the
battery gemini-3.7-flash declines every one of the four switch conditions 18/18 -- it is a
total refuser, which is the opposite of a switch. Nothing below is rescaled from the old
figures; a count out of 62 is not a count out of 32, because the items differ
(`PREREG-2026-09-14-i3-phase4.md`, Amendment 2). Every number here is read from `runs/` by
the same loader and classifier the paper's refusal table uses.

The model is `refusal_table.DEMO_MODEL`, one name shared with the gate that checks the talk.

WHAT THIS DOES NOT DO, said plainly because the last version implied otherwise
-----------------------------------------------------------------------------
It does not make an API call. The previous version printed "[live mode -- two API calls]"
when `run_battery` was importable and then read the recorded runs anyway -- the live path was
never written. This one says what it is: a replay of the frozen wave
(`runs/2026-09-16-ratchet-v3-wave`, collection closed 2026-09-21). The corpus may not be
written to until the paper ships (PLAN.md, completion order B), so a live call from a stage
would be a protocol violation even if it worked. `--replay` is accepted for the pre-flight
block's sake and changes nothing; every run is a replay.

DESIGNED FOR A STAGE
--------------------
- No network, no key, no model that can update under you between rehearsal and the talk.
- The refusal text is printed verbatim. The model's own words do the work; nothing is
  paraphrased and nothing is scored by another model.
- Every count shown is counted from the record in front of the audience, and the closing
  block is computed from the corpus at run time rather than typed into this file.

    python scripts/demo_switch.py                    # the demo, from disk
    python scripts/demo_switch.py --replay           # identical; kept for the pre-flight
    python scripts/demo_switch.py --model openai/gpt-6-astra
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import refusal_table as R  # noqa: E402

#: The paper's own lead exhibit (§1b). Shown after the demo model so the room sees that the
#: switch is not one vendor's quirk -- and so the speaker can say out loud what its decline
#: looks like, which is not a refusal paragraph but thirty-two sentences with no label.
SECOND_EXHIBIT = "openai/gpt-6-astra"

RULE = "=" * 72


def banner(text):
    print()
    print(RULE)
    print("  " + text)
    print(RULE)


def instrument_size():
    """Item count, from the instrument file rather than a literal."""
    path = os.path.join(STUDY, "data", "ratchet-battery.json")
    with io.open(path, encoding="utf-8") as fh:
        bank = json.load(fh)
    return len(bank["items"])


def show(condition, label, prompt, n_answers, n_items, body):
    print()
    print("  CONDITION %s -- %s" % (condition, label))
    print("  system prompt:")
    for line in textwrap.wrap(prompt or "(none)", 66):
        print("    " + line)
    print()
    print("  ANSWERS PARSED:  %d / %d" % (n_answers, n_items))
    print()
    if n_answers == 0:
        print("  what it said instead, verbatim, cut for length only:")
        for line in textwrap.wrap(" ".join(body.split())[:700], 68):
            print("    | " + line)
    else:
        print("  first answers, as returned:")
        for line in textwrap.wrap(" ".join(body.split())[:300], 68):
            print("    | " + line)


def load_recorded(rows, model):
    """One condition-A refusal and one complete condition-P sheet for this model.

    Read from the refusal panel -- `refusal_table.load()` -- and classified by
    `refusal_table.classify`, so the demo's records are the paper's records and a sheet is a
    refusal here only if the paper's table counts it as one. Selected by CONDITION and by the
    classifier, not by directory: an earlier version globbed two run directories by name and
    reported no data for a model with 22 recorded refusals sitting elsewhere in `runs/`.

    A is the forced-balance instruction. P is the placebo: same register, same length, no
    political content. Those two are the demo; nothing else substitutes for them.
    """
    refusal = answered = None
    for row in rows:
        if row.get("model") != model:
            continue
        cond = row.get("condition")
        kind = R.classify(row)
        if cond == "A" and kind == "refused" and row.get("response_text") and refusal is None:
            refusal = row
        elif (cond == "P" and kind == "valid" and answered is None
              and (row.get("n_answers") or 0) == (row.get("n_items") or 0)):
            answered = row
    return refusal, answered


def cells_for(per_model, model):
    """(refused, n) under each switch condition, or None if the model is not in the table."""
    if model not in per_model:
        return None
    return {c: tuple(per_model[model][c]) for c in R.SWITCH_CONDITIONS}


def orders_under(rows, model, condition):
    """Distinct presentation orders the model was measured under in one condition."""
    return len({row.get("shuffle_seed") for row in rows
                if row.get("model") == model and row.get("condition") == condition})


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--model", default=R.DEMO_MODEL)
    ap.add_argument("--replay", action="store_true",
                    help="accepted and ignored: every run is a replay from disk")
    args = ap.parse_args(argv)

    n_items = instrument_size()
    rows = R.load()
    per_model, _totals = R.switch_table(rows)

    banner("THE SAME MODEL, THE SAME %d PROPOSITIONS, TWO INSTRUCTIONS" % n_items)
    print("  model: %s" % args.model)
    print("  instrument: %d forced-choice propositions in %d mirrored pairs, written for"
          % (n_items, n_items // 2))
    print("              this study and shipped with it (data/ratchet-battery.json)")
    print("  no language model scores anything here; answers are counted by a parser")
    print("  replayed from the frozen wave -- no API call is made")

    refusal, answered = load_recorded(rows, args.model)
    if refusal is None or answered is None:
        print()
        print("  No usable pair of records for %s in the refusal panel." % args.model)
        print("  The demo needs one condition-A refusal and one complete condition-P sheet.")
        print("  Run `refusal_table.py --switch` to see which models have both.")
        return 1

    show("A", "asked to be balanced",
         (refusal.get("system_prompt") or "").strip(),
         refusal.get("n_answers") or 0, refusal.get("n_items") or n_items,
         refusal.get("response_text") or "")

    show("P", "placebo: no political content at all",
         (answered.get("system_prompt") or "").strip(),
         answered.get("n_answers") or 0, answered.get("n_items") or n_items,
         answered.get("response_text") or json.dumps(answered.get("answers") or []))

    cells = cells_for(per_model, args.model)
    banner("EVERY RUN OF THIS MODEL IN THE WAVE, BY CONDITION")
    print()
    print("  N = no system prompt   A = answer in a balanced manner")
    print("  P = content-free instruction   D = commit to a position")
    print()
    print("  %-30s %s" % (args.model[:30],
                          "   ".join("%s %d/%d" % (c, cells[c][0], cells[c][1])
                                     for c in R.SWITCH_CONDITIONS)))
    print()
    print("  Not the item order: the balance instruction was declined %d times across %d"
          % (cells["A"][0], orders_under(rows, args.model, "A")))
    print("  presentation orders. Not the temperature, not the questions, not the model.")

    if args.model != SECOND_EXHIBIT and SECOND_EXHIBIT in per_model:
        other = cells_for(per_model, SECOND_EXHIBIT)
        banner("SECOND EXHIBIT -- THE PAPER'S LEAD CASE, ANOTHER VENDOR")
        print()
        print("  %-30s %s" % (SECOND_EXHIBIT[:30],
                              "   ".join("%s %d/%d" % (c, other[c][0], other[c][1])
                                         for c in R.SWITCH_CONDITIONS)))
        print()
        print("  Its decline looks different and is worth saying out loud: it returns a")
        print("  sentence on every proposition and a label on none of them. A refusal of")
        print("  the format, not of the topic. The parser counts zero answers either way.")

    patterns = R.switch_patterns(per_model)
    n_decline = sum(len(v) for v in patterns.values())
    try:
        import key_numbers as K
        arms = K.matched_arms()
    except Exception as exc:                        # pragma: no cover - stage safety
        arms = None
        arms_note = "  (matched-arms block unavailable: %s)" % exc

    banner("WHAT CHANGED BETWEEN THOSE TWO CALLS")
    print()
    print("  One sentence of instruction, containing no politics.")
    print()
    print("  Across the wave, %d models decline under some condition. %d of them decline"
          % (n_decline, len(patterns["switch"])))
    print("  the balance instruction and never the commitment one; %d declines every"
          % len(patterns["total_refuser"]))
    print("  condition and is not a switch at all; the rest run the pattern backwards,")
    print("  including one that declines only the placebo.")
    if arms:
        print()
        print("  %d models measured under both arms: %d refusals in %d runs where the prompt"
              % (arms["models"], arms["nodir_refusals"], arms["nodir_runs"]))
        print("  carries no directive to commit, %d in %d runs where it carries one. %d"
              % (arms["dir_refusals"], arms["dir_runs"], arms["declining"]))
        print("  models decline without a directive; give them one and %d stop."
              % arms["silenced"])
    else:
        print(arms_note)
    print()
    print("  Refusal rates get published as properties of models. Vendors get ranked by")
    print("  them. On this instrument the quantity belongs substantially to the person")
    print("  writing the prompt.")
    print()
    print("  Every figure above: refusal_table.py --switch, key_numbers.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
