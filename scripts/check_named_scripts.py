#!/usr/bin/env python3
"""Every script named in a shipped document must exist in this repository.

`check_doc_links.py` resolves markdown links -- `[text](path)` -- and reports 94 of
them clean. It cannot see a script named in backticks, which is how this repository
actually refers to its tooling: "run `scripts/floor_table.py`", "`target_asymmetry.py`
collapses the 5 samples". Those are instructions to a reader, and four of them pointed
at nothing:

    target_asymmetry.py        ADVERSARIAL-REVIEW.md   never committed to either tree
    single_vs_juxtaposed.py    ADVERSARIAL-REVIEW.md   never committed to either tree
    build_item_bank.py         skills/.../learnings.md private tree only
    validate_claim.py          prereg/...              private tree only

The last two are the worse kind. They exist, so anyone checking from inside the working
tree finds them and concludes the reference is fine; only a reader of the PUBLIC
repository -- the one the document is written for -- hits the hole. A gate that runs in
the mirror is the only one that can see it.

    check_named_scripts.py           # report
    check_named_scripts.py --quiet   # exit code only

Exit 0 clean, 1 defect. (No 2: every tree has documents and scripts, so there is always
a question to answer here.)
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: A backticked bare python filename, optionally with directories in front of it.
NAMED = re.compile(r"`([A-Za-z0-9_./-]*?([A-Za-z0-9_-]+\.py))`")

#: Names that are deliberately NOT ours. A document may legitimately name another
#: project's file -- DEVELOPER.md says the OBLITERATUS CLI is `python -m obliteratus.cli`
#: and "NOT `app.py`, which is the Gradio UI". Each entry needs the reason, because an
#: allowlist with no reasons is where a real defect goes to hide.
FOREIGN = {
    "app.py": "OBLITERATUS's own Gradio UI, named in DEVELOPER.md to say do NOT use it",
}


def tracked_markdown():
    r = subprocess.run(["git", "ls-files", "*.md"], cwd=ROOT,
                       capture_output=True, text=True, timeout=120)
    out = []
    for p in r.stdout.splitlines():
        if not p.strip():
            continue
        # `withdrawn/` IS AN ARCHIVE AND ITS SCRIPTS WERE RETIRED WITH IT. This gate's
        # remedy -- "ship the script, or say in the document that it does not ship" -- cannot
        # apply to a frozen record: shipping the script would un-retire it, and editing the
        # document would rewrite history that is kept precisely so a reader can see what was
        # believed. 16 of this gate's 24 hits were withdrawn plans and results naming tools
        # that went to withdrawn/ in the same commit. The 8 that remain are LIVE documents
        # and are real dead references.
        if p.startswith("withdrawn/"):
            continue
        out.append(p)
    return out


#: A document may declare that a script it names is not in the repository, in the document
#: itself, with a reason:
#:
#:     <!-- NAMED-SCRIPTS-ABSENT: foo.py, bar.py -- retired with the May pipeline; the
#:          analysis they produced is reported below and is not re-runnable here -->
#:
#: THIS EXISTS BECAUSE THE GATE PROMISED IT AND COULD NOT SEE IT. The failure message has
#: always read "Ship the script, or say in the document that it does not ship and what that
#: costs them" -- and saying so cleared nothing, because nothing parsed it. A remedy a gate
#: names and cannot honour is a remedy that gets ignored, and then the gate does.
#:
#: The reason is REQUIRED. A bare list is an exemption; a list with a reason is a disclosure
#: a reader of that document actually sees, which is the point.
ABSENT_DECL = re.compile(
    r"<!--\s*NAMED-SCRIPTS-ABSENT:\s*(?P<names>[^-]+?)\s*--\s*(?P<why>.+?)-->",
    re.IGNORECASE | re.DOTALL)


def declared_absent(text):
    """{basename: reason} for scripts this document says do not ship."""
    out = {}
    for m in ABSENT_DECL.finditer(text):
        why = " ".join(m.group("why").split())
        if not why:
            continue
        for name in m.group("names").split(","):
            name = name.strip().strip("`")
            if name:
                out[os.path.basename(name)] = why
    return out


def scan():
    """[(document, named_script, basename)] for every backticked .py that does not exist."""
    dead, checked = [], 0
    for rel in tracked_markdown():
        path = os.path.join(ROOT, rel)
        try:
            text = open(path, encoding="utf-8").read()
        except (IOError, OSError, UnicodeDecodeError) as exc:
            dead.append((rel, "<unreadable>", str(exc)))
            continue
        absent = declared_absent(text)
        for full, base in set(NAMED.findall(text)):
            if base in FOREIGN or base in absent:
                continue
            checked += 1
            # Named with a path, or by basename anywhere in the tree -- a document may
            # reasonably say `floor_table.py` without spelling out `scripts/`.
            if os.path.exists(os.path.join(ROOT, full)):
                continue
            if _find_basename(base):
                continue
            dead.append((rel, full, base))
    return checked, dead


def _find_basename(base):
    for where, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", ".pytest_cache")]
        if base in files:
            return os.path.join(where, base)
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    checked, dead = scan()
    if not checked:
        # A SCAN THAT EXAMINED NOTHING MUST NEVER REPORT CLEAN.
        print("no backticked script name was examined -- this is a defect in the scan")
        return 1
    if not dead:
        if not args.quiet:
            print("every one of %d backticked script name(s) resolves in this tree." % checked)
        return 0
    print("SCRIPT NAMED IN A SHIPPED DOCUMENT DOES NOT EXIST HERE -- %d reference(s) of %d"
          % (len(dead), checked))
    print("A reader following the instruction gets nothing. Ship the script, or say in the")
    print("document that it does not ship and what that costs them.")
    print("")
    for rel, full, base in sorted(dead):
        print("  %s" % rel)
        print("      `%s`" % full)
    return 1


if __name__ == "__main__":
    sys.exit(main())
