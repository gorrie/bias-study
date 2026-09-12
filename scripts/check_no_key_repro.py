#!/usr/bin/env python3
"""Checklist item 10, made mechanical: can a reader re-derive the numbers with no API key?

README promises it twice — the FAQ row "How do I re-derive a number without an API key?" and
the Reproduce section's "re-run steps 3–4 against any existing run". It was a human-read item,
which in practice means nobody runs it, and the failure it guards is silent: a script that
reaches for a key it does not need fails only for the reader who does not have one. We always
have one.

So each documented no-key command runs here in a STRIPPED environment — `env -i`, no
`OPENROUTER_API_KEY`, no vendor keys, nothing inherited but PATH and HOME. A command that passes
in this harness cannot be passing because of a key that happened to be exported.

It also asserts the working tree is unchanged afterwards. A reproduction step that silently
rewrites committed artifacts is not a reproduction; it is a regeneration, and the reader would
have no way to tell whether the numbers matched or were overwritten to match.

    check_no_key_repro.py            # run the documented no-key path
    check_no_key_repro.py --quiet    # exit code only
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUN = "2026-05-26-variance"          # the run the README names by example

# (label, argv) — every one of these is documented as needing no key.
COMMANDS = [
    ("README Reproduce step 3: aggregate", ["scripts/aggregate.py", RUN]),
    ("README Reproduce step 4: ci_analysis", ["scripts/ci_analysis.py", RUN]),
    ("README Reproduce step 4: robustness_checks", ["scripts/robustness_checks.py", RUN]),
    ("README: score.py --skip-classifier (heuristic only)",
     ["scripts/score.py", RUN, "--skip-classifier"]),
    ("floors re-derived from runs/", ["scripts/floor_table.py"]),
    ("README numbers still match the data", ["scripts/key_numbers.py", "--check"]),
]


def stripped_env():
    """Nothing inherited but PATH and HOME. Not merely unsetting the keys we can name --
    a vendor variable nobody listed is exactly the one that would keep this green by accident."""
    return {"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", ""),
            "PYTHONIOENCODING": "utf-8"}


def tree_dirty():
    r = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                       capture_output=True, text=True, timeout=120)
    return [l for l in r.stdout.splitlines() if l and not l.startswith("??")]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)

    before = tree_dirty()
    fails = []
    for label, args in COMMANDS:
        r = subprocess.run([sys.executable] + args, cwd=ROOT, env=stripped_env(),
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=2700)
        ok = r.returncode == 0
        if not a.quiet:
            print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
        if not ok:
            fails.append((label, (r.stderr or r.stdout).strip().splitlines()[-4:]))

    after = tree_dirty()
    changed = sorted(set(after) - set(before))
    if changed:
        fails.append(("the no-key path MODIFIED the working tree", changed[:6]))

    if not a.quiet:
        print("")
        if fails:
            for label, tail in fails:
                print("  %s" % label)
                for line in tail:
                    print("      %s" % line[:150])
        else:
            print("every documented no-key command runs with no key and changes nothing.")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
