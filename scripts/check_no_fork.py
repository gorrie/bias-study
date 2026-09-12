#!/usr/bin/env python3
"""Fail if any script exists in both trees with different content.

WHY
---
The working study and the public mirror drifted into a maintained pair, and on 2026-09-02 that
pair turned out to have diverged AT THE STATISTICS LAYER: the private `ci_analysis.py` still
seeded one global RNG stream, so its bootstrap intervals depended on the order run-dates were
passed. Measured, 5 of 22 CI bounds moved under reversal. No verdict flipped, which was luck.

Twenty-one same-named files had diverged. Every one is now a single implementation in the
mirror with a shim here. **Nothing prevented that happening and nothing would prevent it
recurring**, which is why this exists: the same shape as the corpus gate, one directory over.

The rule it enforces is narrow and mechanical. A file present in both trees must either be
byte-identical or be a retirement shim. Anything else is a fork, and a fork is how a fix lands
on one side only.

    python scripts/check_no_fork.py           # exit 1 on any fork
    python scripts/check_no_fork.py --list    # also list the shims and identical files
"""
from __future__ import annotations

import argparse
import io
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
PUBLIC = os.path.normpath(os.path.join(STUDY, "..", "..", "..", "bias-study-release"))
PUBLIC_SCRIPTS = os.path.join(PUBLIC, "scripts")

#: A retired script forwards to the mirror. These markers identify one.
SHIM_MARKERS = ("_shim import", "forwards to it", "RETIRED IN PLACE")

#: Files that legitimately differ and are NOT forks, each with its reason.
ALLOWED = {
    # Produces the public export; belongs on the private side and has no public counterpart
    # worth reconciling if one ever appears.
    "export_scrubbed.py": "operator tool that generates the public release",
    "build_corpus_fingerprint.py": "operator tool that generates the public gate",
    "check_no_fork.py": "this checker",
    # Runs the release checklist across BOTH trees, so it can only live on the side that can
    # see both -- the same reason this checker is here.
    "release_check.py": "operator tool that runs the release checklist over both trees",
}


def read(path):
    try:
        return io.open(path, encoding="utf-8", errors="replace").read().replace("\r\n", "\n")
    except OSError:
        return None


def read_committed(repo, relpath):
    """The file as HEAD has it, not as the working tree has it.

    THIS GATE REPORTED "0 FORKS" WHILE THE MIRROR'S HEAD SHIPPED A FABRICATED COMMENT.
    On 2026-09-05 a fix was copied into the mirror's working tree and never committed. Both
    working trees matched, so this checker passed all evening -- while `git show HEAD` on the
    public side still carried the false justification and the rule it defended. A fix that
    exists only as an uncommitted edit is exactly the divergence this exists to catch, and the
    working-tree comparison is blind to it by construction.

    What gets PUBLISHED is HEAD. That is what has to match.

    THE PATH IS RESOLVED AGAINST THE REPOSITORY ROOT, not against `repo`. `git show HEAD:X`
    always reads X from the root, and the private study is NESTED -- it lives at
    research/bias-study inside the book repository -- so "scripts/power.py" named nothing
    and this returned None for every private file. The caller then fell back to the working
    tree for the private side, which is precisely the comparison the docstring above says
    this function exists to stop making. The public mirror is its own repository with an
    empty prefix, so the bug was invisible there and only ever weakened the private half.
    """
    prefix = subprocess.run(["git", "-C", repo, "rev-parse", "--show-prefix"],
                            capture_output=True, text=True, encoding="utf-8").stdout.strip()
    relpath = prefix + relpath
    try:
        out = subprocess.run(["git", "-C", repo, "show", "HEAD:" + relpath],
                             capture_output=True, text=True, encoding="utf-8",
                             errors="replace")
    except OSError:
        return None
    if out.returncode != 0:
        return None
    return out.stdout.replace("\r\n", "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--list", action="store_true", help="also list shims and identical files")
    ap.add_argument("--source-only", action="store_true",
                    help="development mode: check this tree alone, with no mirror present")
    args = ap.parse_args(argv)

    if not os.path.isdir(PUBLIC_SCRIPTS):
        # A MISSING MIRROR IS A FAILURE, not a skip. This printed "nothing to compare,
        # skipping" and returned 0, so the release gate's "check_no_fork == 0 forks" line
        # reported PASS on a machine where the comparison had not run at all -- a gate that
        # is green precisely when it is blind. --source-only is the honest way to work
        # without a mirror, and it says so in its own output rather than in this one's.
        if args.source_only:
            print("--source-only: mirror at %s not compared; this is a development check "
                  "and NOT the publication gate" % PUBLIC)
            return 0
        print("public mirror not on disk at %s -- cannot verify one implementation per name. "
              "Use --source-only to check this tree alone during development." % PUBLIC,
              file=sys.stderr)
        return 1

    forks, shims, identical, allowed = [], [], [], []
    broken_shims = []
    for name in sorted(os.listdir(HERE)):
        if not (name.endswith(".py") or name.endswith(".sh")):
            continue
        mine = os.path.join(HERE, name)
        theirs = os.path.join(PUBLIC_SCRIPTS, name)
        if not os.path.isfile(theirs):
            # A SHIM WITH NO TARGET IS BROKEN, not a private-only script. A retirement shim
            # exists only to forward to the mirror, so if the mirror has no such file the
            # shim raises ImportError the first time anyone runs it. Skipping it here meant
            # the gate stayed green over a script that could not execute at all.
            body = read(mine)
            if body is not None and any(m in body for m in SHIM_MARKERS):
                broken_shims.append(name)
            continue
        if name in ALLOWED:
            allowed.append(name)
            continue
        # COMMITTED content, falling back to the working tree only when a file is not yet
        # tracked (a genuinely new script, which is not a fork). An uncommitted fix on either
        # side is now a FORK, because what ships is HEAD.
        a = read_committed(STUDY, "scripts/" + name)
        b = read_committed(PUBLIC, "scripts/" + name)
        a = read(mine) if a is None else a
        b = read(theirs) if b is None else b
        if a is None or b is None:
            continue
        if a == b:
            identical.append(name)
        elif any(m in a for m in SHIM_MARKERS):
            shims.append(name)
        else:
            forks.append(name)

    # UNCOMMITTED WORK ON A SHARED SCRIPT MAKES THIS COMPARISON MEANINGLESS, in the other
    # direction. HEAD-vs-HEAD is the right question -- what ships is HEAD -- but if either side
    # is holding edits to a shared script, then the thing just compared is not the thing anyone
    # is about to run. Both failures happened on 2026-09-05, hours apart: the fix existed only
    # in the mirror's working tree, and this checker was reading working trees.
    dirty = []
    for repo, label in ((STUDY, "working tree"), (PUBLIC, "mirror")):
        out = subprocess.run(["git", "-C", repo, "status", "--porcelain", "--", "scripts"],
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
        for line in (out.stdout or "").splitlines():
            f = line[3:].strip()
            if f.endswith(".py") and os.path.basename(f) not in ALLOWED:
                dirty.append("%s: %s" % (label, os.path.basename(f)))

    print("compared %d file(s) present in both trees, AS COMMITTED"
          % (len(forks) + len(shims) + len(identical) + len(allowed)))
    if dirty:
        print("  NOTE: %d shared script(s) have uncommitted edits, so what was compared is not"
              % len(dirty))
        print("        what would ship. Commit them, then re-run:")
        for d in sorted(set(dirty))[:8]:
            print("          %s" % d)
    print("  %3d retirement shim(s)" % len(shims))
    print("  %3d byte-identical" % len(identical))
    print("  %3d allowed to differ" % len(allowed))
    print("  %3d FORK(S)" % len(forks))

    if args.list:
        for label, group in (("shim", shims), ("identical", identical),
                             ("allowed", allowed)):
            for n in group:
                extra = (" -- " + ALLOWED[n]) if n in ALLOWED else ""
                print("    %-12s %s%s" % (label, n, extra))

    if dirty:
        print()
        print("UNCOMMITTED EDITS TO SHARED SCRIPT(S) -- exit 1. What was compared is HEAD, and")
        print("HEAD is not what is on disk, so a green result here would describe neither the")
        print("code you are running nor the code that would ship. Commit, then re-run.")
        return 1

    if broken_shims:
        print()
        print("BROKEN SHIM(S) -- forwarding to a mirror file that does not exist:")
        for n in broken_shims:
            print("    %s" % n)
        print("A retirement shim exists only to forward. With no target it raises ImportError")
        print("the first time it is run, so this is a dead script, not a retired one.")
        return 1

    if forks:
        print()
        print("FORKED -- the same name, different content, in both trees:")
        for n in forks:
            print("    %s" % n)
        print()
        print("A fork is how a fix lands on one side only. On 2026-09-02 the private copy of")
        print("ci_analysis.py had an order-dependent bootstrap the mirror had already fixed,")
        print("and nobody noticed because a rotted statistic looks exactly like a statistic.")
        print("Resolve it: merge the union into the mirror and leave a shim here, or add the")
        print("file to ALLOWED above with the reason it must differ.")
        return 1

    print()
    print("No forks. Every shared file is one implementation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
