#!/usr/bin/env python3
"""Fail if any script or test exists in both trees with different content.

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
import ast
import io
import os
import subprocess
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)

# THIS GATE COMPARES TWO TREES AND ONLY ONE OF THEM EXISTS HERE.
#
# It is a PRIVATE-tree check: it walks the working study's scripts and diffs each
# against the mirror's copy. It is also shipped INTO the mirror, where `_shim`
# does not exist and there is no second tree to compare against -- so on a public
# clone it died with `ModuleNotFoundError: No module named '_shim'`.
#
# A reviewer's reasonable move on a repository that advertises its own gates is
# to run all of them. Handing them a traceback on a file whose docstring promises
# to catch divergence says the checks are decorative, which is the opposite of
# what this repository is for.
#
# Exit 2 = NOT APPLICABLE, the same code collection_check uses for "this examined
# nothing". Never 0: a gate that cannot run has not passed.
try:
    from _shim import public_scripts
except ModuleNotFoundError:
    public_scripts = None

if public_scripts is None:
    PUBLIC = PUBLIC_SCRIPTS = None
else:
    PUBLIC = str(public_scripts(__file__).parent)
    PUBLIC_SCRIPTS = os.path.join(PUBLIC, "scripts")

#: A retired script forwards to the mirror. These markers identify one.
SHIM_MARKERS = ("_shim import", "forwards to it", "RETIRED IN PLACE")


def is_shim(text):
    """Identify imports, not mentions inside a regression fixture or docstring."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return False
    return any(isinstance(node, ast.ImportFrom) and node.module == "_shim"
               and any(alias.name in ("forward", "reexport") for alias in node.names)
               for node in ast.walk(tree))

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

#: The directories whose shared files must be one implementation. `tests/` joined 2026-09-24.
SHARED_DIRS = ("scripts", "tests")


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
    """
    try:
        prefix = subprocess.run(["git", "-C", repo, "rev-parse", "--show-prefix"],
                                capture_output=True, text=True, encoding="utf-8")
        if prefix.returncode:
            return None
        out = subprocess.run(["git", "-C", repo, "show", "HEAD:" + prefix.stdout.strip() + relpath],
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
                    help="development check: no entry point may forward into a release checkout")
    args = ap.parse_args(argv)

    # --source-only reads this tree alone, so it runs where the mirror is absent (CI). It sat
    # behind the mirror check and returned NOT APPLICABLE on every CI run.
    if args.source_only:
        shims = [p.name for p in Path(HERE).glob('*.py') if is_shim(read(p) or '')]
        shims += [p.name for p in Path(HERE).glob('*.sh')
                  if 'RETIRED IN PLACE' in (read(p) or '')]
        if shims:
            print('FAIL: development depends on release implementations: ' + ', '.join(sorted(shims)))
            return 1
        print('GitLab implementation check passes: no entry point forwards into a release checkout.')
        print('Release parity is a separate gate; run without --source-only against the staged export.')
        return 0

    if PUBLIC_SCRIPTS is None or not os.path.isdir(PUBLIC_SCRIPTS):
        print("NOT APPLICABLE -- this check compares the working study tree against the")
        print("public mirror, and only one tree is present here. Run it from the study")
        print("tree; in a public clone there is nothing to diff against.")
        print("")
        print("This is NOT a pass. A gate that cannot run has not run.")
        return 2

    if not os.path.isdir(PUBLIC_SCRIPTS):
        print("FAIL: public mirror absent at %s; set BIAS_STUDY_PUBLIC_ROOT" % PUBLIC)
        return 1

    forks, shims, identical, allowed, unavailable = [], [], [], [], []
    shared = []
    # `tests/` AS WELL AS `scripts/`, since 2026-09-24. This compared scripts only, and the
    # regression tests are the other half of every gate: the mirror's `test_release_counts.py`
    # still looked for `RELEASE-v2.md` after the file was renamed, so all three of its tests
    # SKIPPED in the tree that ships while the count they guard went stale -- and three more
    # shared tests had fallen 31 to 108 lines behind the study's. A test has no retirement
    # shim: present in both trees, it is either the same test or a fork.
    for sub in SHARED_DIRS:
        here = os.path.join(STUDY, sub)
        there = os.path.join(PUBLIC, sub)
        if not os.path.isdir(here) and not os.path.isdir(there):
            continue
        if not os.path.isdir(here) or not os.path.isdir(there):
            unavailable.append(sub + "/ (directory missing in one tree)")
            continue
        for name in sorted(os.listdir(here)):
            if not (name.endswith(".py") or name.endswith(".sh")):
                continue
            rel = sub + "/" + name
            label = name if sub == "scripts" else rel
            mine = os.path.join(here, name)
            theirs = os.path.join(there, name)
            if not os.path.isfile(theirs):
                if sub == "scripts" and is_shim(read(mine) or ""):
                    unavailable.append(label + " (shim target missing)")
                continue
            if sub == "scripts" and name in ALLOWED:
                allowed.append(name)
                continue
            shared.append(rel)
            # COMMITTED content, falling back to the working tree only when a file is not yet
            # tracked (a genuinely new script, which is not a fork). An uncommitted fix on
            # either side is now a FORK, because what ships is HEAD.
            a = read_committed(STUDY, rel)
            b = read_committed(PUBLIC, rel)
            if a is None or b is None:
                unavailable.append(label + " (committed content unavailable)")
                continue
            if a == b:
                identical.append(label)
            elif sub == "scripts" and is_shim(a):
                shims.append(label)
            else:
                forks.append(label)

    # UNCOMMITTED WORK ON A SHARED SCRIPT MAKES THIS COMPARISON MEANINGLESS, in the other
    # direction. HEAD-vs-HEAD is the right question -- what ships is HEAD -- but if either side
    # is holding edits to a shared script, then the thing just compared is not the thing anyone
    # is about to run. Both failures happened on 2026-09-05, hours apart: the fix existed only
    # in the mirror's working tree, and this checker was reading working trees.
    dirty = []
    for repo, label in ((STUDY, "working tree"), (PUBLIC, "mirror")):
        if not shared:
            continue
        paths = [str(Path(repo) / rel) for rel in shared]
        out = subprocess.run(["git", "-C", repo, "diff", "--name-only", "HEAD", "--", *paths],
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
        if out.returncode:
            unavailable.append(label + " (Git comparison failed)")
        for line in (out.stdout or "").splitlines():
            dirty.append("%s: %s" % (label, os.path.basename(line)))

    print("compared %d file(s) present in both trees, AS COMMITTED"
          % (len(forks) + len(shims) + len(identical) + len(allowed)))
    if dirty:
        print("  FAIL: %d shared script(s) have uncommitted edits, so what was compared is not"
              % len(dirty))
        print("        what would ship. Commit them, then re-run:")
        for d in sorted(set(dirty))[:8]:
            print("          %s" % d)
    print("  %3d retirement shim(s)" % len(shims))
    print("  %3d byte-identical" % len(identical))
    print("  %3d allowed to differ" % len(allowed))
    print("  %3d FORK(S)" % len(forks))
    for problem in unavailable:
        print("  FAIL: " + problem)

    if args.list:
        for label, group in (("shim", shims), ("identical", identical),
                             ("allowed", allowed)):
            for n in group:
                extra = (" -- " + ALLOWED[n]) if n in ALLOWED else ""
                print("    %-12s %s%s" % (label, n, extra))

    if forks:
        print()
        print("FORKED -- the same name, different content, in both trees:")
        for n in forks:
            print("    %s" % n)
        print()
        print("A fork is how a fix lands on one side only. On 2026-09-02 the private copy of")
        print("ci_analysis.py had an order-dependent bootstrap the mirror had already fixed,")
        print("and nobody noticed because a rotted statistic looks exactly like a statistic.")
        print("Resolve in the GitLab implementation, then stage a reviewed export for GitHub.")
        print("Do not move development into the release mirror to satisfy this publication gate.")
        return 1

    if dirty or unavailable or not (shims or identical):
        print("FAIL: comparison incomplete or differs from the working scripts.")
        return 1

    print()
    print("No forks. Every shared file is one implementation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
