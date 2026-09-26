#!/usr/bin/env python3
"""Re-run every number the study publishes, and say WHAT MOVED.

WHY THIS EXISTS
---------------
`PLAN.md` Phase 1 item 2 is "re-run every number against the deepened corpus" followed by a
list of five commands. A list of commands in a document is not a procedure: it can be run
partially, in the wrong order, or against the wrong run directory, and nothing afterwards can
tell you which. More to the point, running them tells you the numbers -- it does not tell you
**which ones changed**, which is the only question a re-run is asked to answer.

This study has twice published a figure that had silently moved underneath it. The defence is
not care; it is a snapshot you can diff.

HOW IT DIFFS
------------
It stores each command's **full stdout** rather than parsing figures out of it. Every parser
this project has written to scrape its own output has eventually scraped the wrong line, and a
regex that silently matches nothing reports "no change" -- the exact failure it was added to
catch. Whole-output diffing cannot do that: if a byte moves, it shows the line.

Volatile lines -- timings, paths, record counts that move with an in-flight collection -- are
normalised away by `_stable`, and what it normalises is listed there rather than being a quiet
`re.sub` nobody can audit.

    refresh_numbers.py --snapshot     # record the current numbers as the baseline
    refresh_numbers.py                # re-run and diff against the baseline
    refresh_numbers.py --list         # what it would run, no execution

Exit 0 nothing moved, 1 a command failed, 3 numbers moved (not an error -- the point),
2 NOT APPLICABLE (no baseline yet).
"""
from __future__ import annotations

import argparse
import difflib
import io
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
SNAPSHOT = os.path.join(STUDY, "data", "numbers-snapshot.json")
PY = sys.executable

#: Every number-bearing command in PLAN.md Phase 1 item 2, plus the gate that decides whether
#: the analysis can read the corpus at all. Order matters only for readability.
#:
#: NOT INCLUDED, deliberately: anything that WRITES. `floor_resolution.py --write` re-measures
#: the modal-noise cache and is a collection step, not a reporting one -- running it from here
#: would mean a "re-run the numbers" command that changes an input to the numbers.
WAVE = "2026-09-16-ratchet-v3-wave"

#: Commands that genuinely take longer than the default, with the measurement behind each.
#: DECLARED RATHER THAN DISCOVERED: on 2026-09-19 both of these hit the 900s default, and
#: their TIMEOUT MESSAGE was written into the snapshot as their recorded output -- so the next
#: run would have diffed "TIMED OUT after 900s" against itself and reported that nothing
#: moved, on the two most load-bearing commands in the file.
#:
#: The cost is real, not a defect: one sheet-bootstrap contrast is 2.85s at 20,000 draws
#: (measured on the 2026-09-16 wave, 297 model-condition cells), and the prereg scorecard runs
#: 246 of them -- about 12 minutes before the predictions and the placebo arm are added. The
#: draw count is not reduced to fit a timeout: these intervals are published.
SLOW = {
    "prereg scorecard": 2400,
    "placebo table": 2400,
    "undisputed subset": 1200,
    "order floor in position units": 1200,
}

DEFAULT_TIMEOUT = 900

COMMANDS = [
    ("outcomes computable", ["scripts/check_outcomes_computable.py"]),
    ("floors", ["scripts/floor_table.py"]),
    ("uncomputed arms", ["scripts/floor_table.py", "--uncomputed"]),
    ("prereg scorecard", ["scripts/position_analysis.py", WAVE, "--prereg"]),
    ("undisputed subset", ["scripts/position_analysis.py", WAVE, "--undisputed"]),
    ("placebo table", ["scripts/position_analysis.py", WAVE, "--placebo-table"]),
    ("refusal by vendor", ["scripts/refusal_table.py"]),
    ("refusal by model", ["scripts/refusal_table.py", "--switch"]),
    ("refusal by condition", ["scripts/refusal_table.py", "--by-condition"]),
    # ADDED 2026-09-19 WITH THE ARMS THEMSELVES. An arm collected but absent from this list
    # is an arm whose numbers can move without the snapshot diff noticing -- the same defect
    # as `refusal_table` silently dropping the conditions it did not know about, one layer
    # up. `test_refresh_covers_every_reporting_surface` is the check.
    ("clause factorial", ["scripts/refusal_table.py", "--factorial"]),
    # PREREG-2026-09-25-factorial-floor-calibration. Seeded, so its stdout is reproducible
    # and the snapshot diff reports a real change rather than Monte Carlo noise.
    ("clause factorial floor calibration",
     ["scripts/refusal_table.py", "--factorial-calibration"]),
    ("elicitation rung", ["scripts/refusal_table.py", "--rung2"]),
    ("elicitation rung contrasts", ["scripts/rung2_contrast.py"]),
    ("sampling ladder", ["scripts/refusal_table.py", "--sampling"]),
    ("order floor in position units", ["scripts/order_floor_position.py"]),
    ("item vs slot vs numeral", ["scripts/item_omission.py", "--matrix"]),
    ("jurisdiction gradient", ["scripts/jurisdiction_gradient.py"]),
    ("scale-usage shift", ["scripts/strong_shift.py", "--vacate"]),
    ("MDE behind every null", ["scripts/null_audit.py"]),
    ("power and MDE", ["scripts/power.py"]),
    ("collection check", ["scripts/collection_check.py", WAVE]),
]

#: Lines that differ between two runs of the SAME corpus and mean nothing. Each is here with
#: its reason; a blanket "strip anything numeric" would hide the movement this exists to find.
VOLATILE = [
    (re.compile(r"\b\d+\.\d+s\b"), "<secs>"),                 # wall-clock timings
    (re.compile(r"[A-Za-z]:\\[^\s]+"), "<path>"),             # absolute Windows paths
    (re.compile(r"\b20\d\d-\d\d-\d\dT[\d:.]+"), "<ts>"),      # ISO timestamps
]


def _stable(text):
    for pattern, repl in VOLATILE:
        text = pattern.sub(repl, text)
    return text.replace("\r\n", "\n").rstrip() + "\n"


def run(argv, timeout=DEFAULT_TIMEOUT):
    """-> (exit code, normalised stdout+stderr)."""
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    try:
        proc = subprocess.run([PY] + argv, cwd=STUDY, env=env, timeout=timeout,
                              capture_output=True, text=True, errors="replace")
    except subprocess.TimeoutExpired:
        return 124, "TIMED OUT after %ds\n" % timeout
    return proc.returncode, _stable((proc.stdout or "") + (proc.stderr or ""))


def collect(only=None):
    out = {}
    for label, argv in COMMANDS:
        if only and label not in only:
            continue
        started = time.time()
        budget = SLOW.get(label, DEFAULT_TIMEOUT)
        print("  running %-30s ..." % label, end="", flush=True)
        code, text = run(argv, timeout=budget)
        elapsed = time.time() - started
        note = ""
        if code == 124:
            note = "  TIMED OUT at %ds -- NO ANSWER, not a defect" % budget
        elif elapsed > 0.8 * budget:
            # A command inside 20% of its budget is one timeout away from silently becoming a
            # hole in the next baseline. Say so while it still passes.
            note = "  (within 20%% of its %ds budget -- raise it in SLOW)" % budget
        print(" %s  (%.0fs)%s" % ("ok" if code in (0, 2, 3) else "EXIT %d" % code,
                                  elapsed, note), flush=True)
        out[label] = {"argv": argv, "exit": code, "output": text}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--snapshot", action="store_true",
                    help="record the current numbers as the baseline to diff against")
    ap.add_argument("--list", action="store_true", help="what would run; no execution")
    ap.add_argument("--only", nargs="*", help="labels to run (default: all)")
    a = ap.parse_args(argv)

    if a.list:
        print("REFRESH would run %d command(s), none of which write:" % len(COMMANDS))
        for label, cmd in COMMANDS:
            print("  %-22s python %s" % (label, " ".join(cmd)))
        return 0

    have = None
    if os.path.exists(SNAPSHOT):
        have = json.load(io.open(SNAPSHOT, encoding="utf-8"))

    print("RE-RUNNING EVERY PUBLISHED NUMBER%s"
          % (" -- recording a new baseline" if a.snapshot else ""))
    print("")
    got = collect(set(a.only) if a.only else None)
    print("")

    # A COMMAND THAT REPORTED A DEFECT IS NOT A COMMAND THAT BROKE.
    #
    # This tree's convention is 0 pass, 1 defect, 2 NOT APPLICABLE, and `collection_check`
    # returns 1 right now because the corpus really does have two blockers. Calling that a
    # failed command would make every refresh read as broken tooling and train the reader to
    # skip the line -- while a genuinely crashed script, which also exits 1, hid inside it.
    #
    # The discriminator is a traceback. A script that ran and judged prints a verdict; a script
    # that died prints a stack.
    failed = [k for k, v in got.items()
              if v["exit"] not in (0, 2, 3)
              and ("Traceback (most recent call last)" in v["output"]
                   or v["exit"] in (124, -1) or v["exit"] > 3)]
    reported = [k for k, v in got.items() if v["exit"] not in (0, 2, 3) and k not in failed]

    if a.snapshot or have is None:
        # A COMMAND THAT DID NOT PRODUCE NUMBERS MUST NOT BECOME A BASELINE.
        #
        # 2026-09-19: `--prereg` and `--placebo-table` both hit the 900s limit, and their
        # timeout MESSAGE was written into the snapshot as their recorded output. The next
        # run would then diff "TIMED OUT after 900s" against "TIMED OUT after 900s" and
        # report that nothing moved -- a vacuous pass on the two most load-bearing commands
        # in the file, in the tool whose entire job is noticing movement.
        #
        # Recorded as an explicit hole instead. The diff reports a hole as a hole.
        keep = dict(got)
        holes = []
        for label in sorted(failed):
            holes.append(label)
            keep[label] = {"argv": got[label]["argv"], "exit": got[label]["exit"],
                           "output": None,
                           "no_baseline": "this command did not produce numbers when the "
                                          "baseline was taken (exit %d); there is nothing to "
                                          "diff against" % got[label]["exit"]}
        payload = {
            "_what": ("A BASELINE, NOT CURRENT NUMBERS. This is the recorded stdout of each "
                      "command AT THE MOMENT IT WAS TAKEN, kept so a later run can be diffed "
                      "against it. Every figure in here is as stale as its `recorded` date by "
                      "design -- staleness is the point, and re-recording it is a deliberate "
                      "act. Never quote a number from this file; run the command."),
            "recorded": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "commands": keep,
        }
        with io.open(SNAPSHOT, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
        if have is None and not a.snapshot:
            print("NOT APPLICABLE -- no baseline existed, so nothing could be compared.")
            print("One is recorded now at %s; re-run after the next collection."
                  % os.path.relpath(SNAPSHOT, STUDY))
            return 2
        print("Baseline recorded: %d command(s) at %s."
              % (len(keep) - len(holes), os.path.relpath(SNAPSHOT, STUDY)))
        if holes:
            print("")
            print("  %d command(s) produced NO BASELINE and are recorded as holes:" % len(holes))
            for label in holes:
                print("    %-24s exit %d" % (label, got[label]["exit"]))
            print("  A later run has nothing to diff these against. They are not passing and")
            print("  they are not failing -- they did not answer. Fix them before the")
            print("  regeneration pass, or that pass reports 'nothing moved' for them.")
        return 1 if failed else 0

    moved = []
    for label in sorted(got):
        prior = have["commands"].get(label) or {}
        before = prior.get("output")
        if before is None:
            # Two different holes, and they must not read the same. A command absent from
            # the baseline is new; one present with a null output DID NOT ANSWER when the
            # baseline was taken, and calling that "NEW" would hide that it is still unfixed.
            moved.append((label,
                          "NO BASELINE -- %s" % prior["no_baseline"] if prior.get("no_baseline")
                          else "NEW -- not in the baseline", []))
            continue
        after = got[label]["output"]
        if before == after:
            continue
        diff = [ln for ln in difflib.unified_diff(
            before.splitlines(), after.splitlines(), lineterm="", n=1)
            if ln.startswith(("+", "-")) and not ln.startswith(("+++", "---"))]
        moved.append((label, "%d line(s) changed" % len(diff), diff))

    print("Baseline recorded %s." % have.get("recorded", "?"))
    if reported:
        print("")
        print("COMMAND(S) REPORTING A DEFECT -- they ran; the corpus or the tree is red:")
        for k in reported:
            print("  %-22s exit %d" % (k, got[k]["exit"]))
    if failed:
        print("")
        print("COMMAND(S) CRASHED -- the comparison below is incomplete:")
        for k in failed:
            print("  %-22s exit %d" % (k, got[k]["exit"]))
    if not moved:
        print("")
        print("NOTHING MOVED. Every published number is what the baseline recorded.")
        return 1 if failed else 0

    print("")
    print("%d of %d command(s) produced different output:" % (len(moved), len(got)))
    for label, summary, diff in moved:
        print("")
        print("  %s -- %s" % (label, summary))
        for line in diff[:24]:
            print("      %s" % line[:150])
        if len(diff) > 24:
            print("      ... and %d more line(s)" % (len(diff) - 24))
    print("")
    print("Numbers moving after a collection is expected. What is NOT expected is a number")
    print("moving when nothing was collected -- and that is what this exists to show.")
    print("Re-record with --snapshot once the movement is understood and written down.")
    return 1 if failed else 3


if __name__ == "__main__":
    sys.exit(main())
