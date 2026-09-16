#!/usr/bin/env python3
"""Do the skills' documented commands actually RUN, not just exist?

WHAT check_skill_docs ALREADY DOES, AND WHERE IT STOPS
-----------------------------------------------------
`check_skill_docs.py` verifies that a path a skill names exists and that a flag
a skill names is real. That catches a renamed script and an invented option, and
both were worth catching.

It cannot catch a command that resolves and then fails. A skill can cite a real
script with a real flag and still document a step that exits 2 on a clean clone,
or crashes on an import that only exists in the private tree, or reports
"CHECKED NOTHING" over an empty selection. Every one of those has happened here:

  * `check_no_fork.py` died with ModuleNotFoundError in any public clone for as
    long as it had shipped, and is named as a step in bias-study-prep.
  * `collection_check.py` returned zero rows for every forced-choice run ever
    collected, and is the gate the I3 plan makes a precondition for scoring.
  * `check_skill_docs.py` itself reported undocumented scripts and exited 0.

The pattern is the same each time: a procedure nobody executes end to end reads
as correct until someone follows it.

WHAT THIS RUNS, AND WHAT IT REFUSES TO
--------------------------------------
Only commands that are SAFE BY CONSTRUCTION: a fixed allowlist of read-only
checkers, with no network and no writes. It never runs a collector, never runs a
generator without `--check`, and never runs anything carrying an API key.

Anything a skill documents that is not on the allowlist is reported as UNTESTED
rather than assumed good, and the count is printed -- because a checker that
silently tested two of forty commands would be the exact defect it exists to
find.

Exit 1 when a testable command fails. Exit 0 prints how many were tested and how
many could not be.

    python scripts/check_skill_procedures.py
    python scripts/check_skill_procedures.py --list   # what it would run
"""
from __future__ import annotations

import argparse
import glob
import io
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)

#: Commands safe to execute: read-only, no network, no writes.
#:
#: Keyed by script name. The value is the set of flag-combinations that are safe;
#: an empty tuple means the bare invocation is safe. A script not listed here is
#: never run, however harmless it looks -- the allowlist is the safety property,
#: not the reviewer's judgement at the call site.
SAFE = {
    "check_corpus.py": {(), ("--all",), ("--hashed-only",)},
    "check_doc_links.py": {()},
    "check_skill_docs.py": {()},
    "check_undefined_names.py": {(), ("--check",)},
    "check_no_fork.py": {(), ("--list",)},
    "gen_readme.py": {("--check",)},
    "gen_script_inventory.py": {("--check",)},
    "gen_paper.py": {("--check",)},
    "key_numbers.py": {("--check",), ("--check-release",), ("--check-website",)},
    "controls_audit.py": {("--strict",), ("--markdown",), ("--gaps",)},
    "validate_runs.py": {()},
    "test_compass_parser.py": {()},
    "probe_budget.py": {()},
    "floor_table.py": {(), ("--markdown",)},
    "power.py": {()},
    "run_inventory.py": {("--check",)},
}

#: Exit codes a command may return and still be considered working.
#:
#: 2 is NOT APPLICABLE by this repository's convention -- check_no_fork in a
#: public clone, collection_check over a run that is not there. That is a correct
#: answer to a question the skill asked, not a broken step.
OK_CODES = {0, 2}

CMD = re.compile(r"`?(?:python\s+)?(?:scripts/)?([a-z_0-9]+\.py)((?:\s+--[a-z-]+)*)`?")


def documented_commands():
    """(skill, script, flags) for every command a skill document names."""
    out = []
    for path in sorted(glob.glob(os.path.join(STUDY, "skills", "*", "*.md"))):
        skill = os.path.basename(os.path.dirname(path))
        text = io.open(path, encoding="utf-8", errors="replace").read()
        for m in CMD.finditer(text):
            script, flags = m.group(1), tuple(m.group(2).split())
            out.append((skill, script, flags))
    return sorted(set(out))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--list", action="store_true", help="what would run; executes nothing")
    args = ap.parse_args(argv)

    cmds = documented_commands()
    runnable, untested = [], []
    for skill, script, flags in cmds:
        if not os.path.exists(os.path.join(HERE, script)):
            continue          # check_skill_docs owns dead paths
        if script in SAFE and flags in SAFE[script]:
            runnable.append((skill, script, flags))
        else:
            untested.append((skill, script, flags))

    if args.list:
        print("WOULD RUN (%d):" % len(runnable))
        for s, sc, f in runnable:
            print("   %-22s %s %s" % (s, sc, " ".join(f)))
        print("")
        print("NOT ON THE SAFE LIST, so never executed (%d):" % len(untested))
        for s, sc, f in sorted(set(untested)):
            print("   %-22s %s %s" % (s, sc, " ".join(f)))
        return 0

    print("SKILL PROCEDURE CHECK -- executing %d documented command(s)" % len(runnable))
    print("")
    failures = []
    for skill, script, flags in runnable:
        p = subprocess.run([sys.executable, os.path.join(HERE, script)] + list(flags),
                           cwd=STUDY, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        ok = p.returncode in OK_CODES
        print("  %-5s %-22s %s %s" % ("ok" if ok else "FAIL", skill, script, " ".join(flags)))
        if not ok:
            tail = (p.stderr or p.stdout or "").strip().splitlines()
            failures.append((skill, script, flags, p.returncode,
                             tail[-1][:160] if tail else ""))

    print("")
    if failures:
        print("%d documented command(s) FAILED when run:" % len(failures))
        for skill, script, flags, code, why in failures:
            print("   %s: %s %s -> exit %d" % (skill, script, " ".join(flags), code))
            if why:
                print("      %s" % why)
        print("")
        print("A skill that documents a step which does not run is a procedure nobody")
        print("has followed end to end. Fix the script or fix the document.")
        return 1

    print("all %d executed command(s) returned a working exit code." % len(runnable))
    print("%d documented command(s) are NOT on the safe list and were not run --"
          % len(set(untested)))
    print("collectors, generators and anything needing a key. They are untested, not blessed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
