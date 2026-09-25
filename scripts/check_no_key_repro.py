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


#: Every file the documented reproduction writes, compared against HEAD afterwards.
#:
#: TAKEN FROM aggregate.py's OWN OUTPUT PATHS, not guessed. The first version of this list
#: named `data/<run>/per-model.csv`; aggregate writes `data/<run>/aggregated/per-model.csv`,
#: so three of its four entries matched nothing on disk, were skipped by the `exists()` test,
#: and the comparison ran over one file while reading as though it covered four. That is the
#: same shape as the defect this whole check exists to catch, one level up.
#: `tracked_outputs()` is what makes a shrunken list visible rather than silent.
#: Both run roots are listed because the two trees use different ones -- the mirror keeps the
#: May study under `data/`, the working tree under `runs/` -- and the same script has to cover
#: whichever is present. `tracked_outputs()` reports how many were actually compared.
WRITES = ["%s/%s/run-summary.json",
          "%s/%s/aggregated/per-model.csv",
          "%s/%s/aggregated/per-topic.csv",
          "%s/%s/aggregated/per-question.csv"]
RUN_ROOTS = ("data", "runs")


def differs_from_committed():
    """Which of the reproduction's outputs no longer match what is committed.

    THE BASELINE HAS TO BE THE COMMIT, NOT THE WORKING TREE. Two versions of this check got
    it wrong in the same direction, and both were defeated by simply running twice:

      1. `git status` before and after, reporting `after - before`. `aggregate.py` wrote
         run-summary.json without a trailing newline, so run 1 dirtied the tree and failed
         correctly -- and run 2 saw the file already dirty in `before`, computed an empty
         delta, and printed "changes nothing".
      2. sha256 before and after, same invocation. Run 2 digested the ALREADY-REWRITTEN file
         as its baseline, got an identical digest back, and passed again.

    Both compared the tree against itself, which cannot detect a difference the previous run
    already made permanent in the working copy. The question this gate is asking is not "did
    anything move in the last minute" -- it is "does the documented reproduction return the
    artifact this repository ships". That question has exactly one baseline: HEAD.

    Uses git's own comparison, ignoring CR at end of line: the reproduction writes LF, and a
    Windows checkout with core.autocrlf holds CRLF, so a byte-identical result read as changed.
    """
    out = []
    for rel in tracked_outputs():
        r = subprocess.run(["git", "diff", "--quiet", "--ignore-cr-at-eol", "HEAD", "--", rel],
                           cwd=ROOT, capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            out.append(rel)
    return out


def output_paths():
    """Every declared output path, across both run roots."""
    return [pattern % (root, RUN) for root in RUN_ROOTS for pattern in WRITES]


def tracked_outputs():
    """The reproduction outputs that exist AND are tracked, so 'checked nothing' is visible."""
    present = []
    for rel in output_paths():
        if (ROOT / rel).exists():
            r = subprocess.run(["git", "ls-files", "--error-unmatch", rel],
                               cwd=ROOT, capture_output=True, text=True, timeout=120)
            if r.returncode == 0:
                present.append(rel)
    return present


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

    # DOES THE REPRODUCTION RETURN THE COMMITTED ARTIFACT? Measured against HEAD, not
    # against the tree as this check found it -- see differs_from_committed() for the two
    # earlier versions that compared the tree to itself and could be cleared by re-running.
    checked = tracked_outputs()
    if not checked:
        # A COMPARISON OVER ZERO FILES IS NOT A CLEAN COMPARISON.
        fails.append(("no reproduction output was compared, so 'changes nothing' was not "
                      "checked -- no declared output is present and tracked in this tree",
                      output_paths()))
    else:
        rewritten = differs_from_committed()
        if rewritten:
            fails.append(("the no-key path does NOT reproduce the committed artifact -- a "
                          "reproduction that overwrites the file it reproduces cannot tell "
                          "the reader whether the numbers matched or were made to match",
                          rewritten[:6]))
        elif not a.quiet:
            print("")
            print("  %d reproduction output(s) match HEAD byte-for-byte: %s"
                  % (len(checked), ", ".join(checked)))

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
