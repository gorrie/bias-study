#!/usr/bin/env python3
"""Measure the token budget the WHOLE roster needs, before collecting a wave.

WHY THIS EXISTS
---------------
The I3 plan's Phase 2 gate says the measured output length sets `--max-tokens`,
and the design review attached a per-model probe to it in as many words: "one
model tells you nothing about the other seven ... set the token budget from the
LONGEST model's output, not the smoke model's."

That was skipped. The smoke ran on `x-ai/grok-4.3` alone, whose longest sheet was
2,184 tokens, the cap was set to 4,096 from it, and 372 sheets were launched.
Measured over the 231 that landed:

    deepseek     95.8% invalid, 23 of 24 sitting exactly at the cap
    moonshotai   72.2% invalid, 23 at the cap
    google       79.2% invalid
    openai        7.7% invalid, 0 at the cap
    anthropic     8.3% invalid, 1 at the cap

Differential exclusion by vendor, 7.7% to 95.8%. That is FINDINGS #7 -- this
study's own established result -- reproduced on its own instrument, hours after
the 800-token version of it was repaired.

A reasoning model spends the budget on reasoning before emitting an answer, so
its sheet length is not predictable from a non-reasoning model's. The only way to
know is to ask every model on the roster once.

WHAT IT DOES
------------
One sheet per model at a deliberately generous ceiling, so nothing is at the cap
and the number measured is what the model actually WANTS. Reports the maximum and
the budget to use (double it), and names any model that still hit the ceiling --
because a model that hits even this is one the wave cannot collect at any budget
worth paying for, and that is worth knowing before the wave, not during it.

    python scripts/probe_budget.py --run
"""
from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)

#: Generous on purpose. This is a measurement, not a collection: if a sheet lands
#: at this ceiling the number is a floor rather than a length, and the report says so.
PROBE_CEILING = 65536
#: THE INSTRUMENT AND THE OUT-DIR COME FROM THE WAVE DRIVER, not from literals here.
#: Both were hardcoded to the WITHDRAWN 60-item bank and its run directory. Running this
#: as the refusal message instructs would have administered 36 sheets of a retired
#: instrument into runs/ -- the probe that gates the collection, collecting on the wrong
#: instrument, with no check that it had.
import run_i3_wave as _W
ITEMS = _W.ITEMS
OUT = "runs/" + _W.RUN_DATE + "-budget-probe"


PANEL_FILE = os.path.join(STUDY, "data", "wave-panel.json")


def panel():
    with io.open(PANEL_FILE, encoding="utf-8") as fh:
        return json.load(fh)["models"]


def is_local(m):
    return "/" not in m or m.startswith("hf.co")


def collected():
    """model -> (tokens_out, valid, n_answers) for sheets already probed."""
    got = {}
    import glob
    for p in glob.glob(os.path.join(STUDY, OUT, "*.jsonl")):
        for line in io.open(p, encoding="utf-8"):
            if not line.strip():
                continue
            r = json.loads(line)
            got[r["model"]] = (r.get("tokens_out") or 0, bool(r.get("valid")),
                               r.get("n_answers") or 0)
    return got


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--condition", default="N",
                    help="N is the bare baseline and the longest answer in practice")
    args = ap.parse_args(argv)

    # NO PANEL, NO QUESTION TO ANSWER.
    #
    # This is a pre-run gate in bias-study-prep, and the prep skill runs from
    # whichever tree you are in. The public mirror has no `data/wave-panel.json`
    # -- the frozen panel is a collection artifact of the working study -- so
    # this crashed with FileNotFoundError on a clean clone.
    #
    # Found 2026-09-15 by check_skill_procedures.py, on the same day this script
    # was written, and it is the SAME defect check_no_fork had had for its whole
    # life: a private-tree gate shipped into the public one, dying on an input
    # that was never going to be there. Exit 2 = NOT APPLICABLE, never 0.
    if not os.path.exists(PANEL_FILE):
        print("NOT APPLICABLE -- no frozen panel at %s."
              % os.path.relpath(PANEL_FILE, STUDY))
        print("The panel is a collection artifact of the working study tree, so there")
        print("is no roster here whose budget could be measured.")
        print("")
        print("This is NOT a pass. A gate that cannot run has not run.")
        return 2

    models = panel()
    have = collected()
    todo = [m for m in models if m not in have]

    if not args.run:
        print("BUDGET PROBE -- %d model(s), %d already probed, %d to go"
              % (len(models), len(have), len(todo)))
        print("  ceiling %d tokens (a measurement, not a collection)" % PROBE_CEILING)
        if todo:
            # NON-ZERO, because this is a PRE-RUN GATE and not a status line.
            # bias-study-prep runs it before every study run; a gate that reports
            # incomplete coverage and exits 0 is the vacuous pass this project
            # has now found in five separate tools.
            print("")
            print("INCOMPLETE -- %d model(s) on the frozen panel have never been probed:"
                  % len(todo))
            for m in sorted(todo)[:8]:
                print("    %s" % m)
            if len(todo) > 8:
                print("    ... and %d more" % (len(todo) - 8))
            print("")
            print("A budget set from a subset is how the 4,096 wave happened: one")
            print("non-reasoning model measured, 372 sheets collected, deepseek 95.8%")
            print("invalid against openai's 7.7%. Run: probe_budget.py --run")
            return 1
        lengths = [t for t, _, _ in have.values()]
        print("")
        print("  longest sheet on the roster : %d tokens" % max(lengths))
        print("  minimum safe budget         : %d" % (2 * max(lengths)))
        return 0

    for m in todo:
        cmd = [sys.executable, os.path.join(HERE, "run_compass.py"),
               "--model", m, "--items", ITEMS,
               "--condition", args.condition, "--runs", "1", "--shuffle-seed", "11",
               "--temperature", "0.7", "--seed", "20260926",
               "--max-tokens", str(PROBE_CEILING), "--out", OUT]
        if is_local(m):
            cmd += ["--channel", "ollama", "--no-think"]
        r = subprocess.run(cmd, cwd=STUDY, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        print("  %-46s %s" % (m, "ok" if r.returncode == 0 else "FAILED"), flush=True)

    have = collected()
    print("")
    print("%-46s %9s %7s %s" % ("model", "tokens", "answers", "valid"))
    for m in sorted(have, key=lambda k: -have[k][0]):
        t, ok, n = have[m]
        flag = "  <-- AT CEILING, this is a floor not a length" if t >= PROBE_CEILING - 10 else ""
        print("%-46s %9d %7d %s%s" % (m, t, n, ok, flag))

    lengths = [t for t, _, _ in have.values()]
    if lengths:
        hi = max(lengths)
        print("")
        print("longest sheet on the roster : %d tokens" % hi)
        print("BUDGET TO USE               : %d  (double the measured maximum)" % (2 * hi))
        at = [m for m, (t, _, _) in have.items() if t >= PROBE_CEILING - 10]
        if at:
            print("STILL AT THE CEILING        : %s" % ", ".join(at))
            print("  Those are not measured. Do not set a budget from this number.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
