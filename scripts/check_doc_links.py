#!/usr/bin/env python3
"""Gate: every relative markdown link in this tree's documents resolves to a real file.

WHY THIS EXISTS. On 2026-09-07 `ROADMAP.md` gained a link to
`results/RESULTS-2026-09-07-constrained-decoding-batch-size.md` while that file still only
existed in the private tree, and nothing in the repo could tell. The tree already gates dead
paths *quoted inside skill documents* (`check_skill_docs.py`) and dead paths in the workspace's
publishing docs (a doc-path scanner in the publishing tooling) -- and neither looks at an ordinary
markdown link in an ordinary document, which is the form nearly every cross-reference here takes.
A checker blind to one input class is usually blind to others; that pattern has now cost this
study three separate times.

It also catches the specific failure mode this release keeps producing: a results document gets
**renamed** when its conclusion is superseded -- `grammar-decoding-does-not-replicate` became
`constrained-decoding-batch-size` when a sweep showed the arm replicating -- and every reference
to the old name silently rots. A rename that leaves dead links is how a reader arrives at a
retracted finding.

WHAT IT DOES NOT CHECK, deliberately:

    external URLs      no network calls in a gate. A gate that needs the internet is a gate
                       that fails on a plane and gets switched off.
    anchors            `#section` fragments are not resolved. Heading text drifts constantly
                       and the false-positive rate would bury the real finding.
    image alt-text     same syntax, same resolution rules, so images ARE checked -- a missing
                       chart is as bad as a missing document.

    python scripts/check_doc_links.py            # report
    python scripts/check_doc_links.py --quiet     # exit code only
"""
from __future__ import annotations

import argparse
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

#: Directories never scanned. `runs/` and `data/` hold collected records, not prose, and a
#: stray bracket in a model's answer is not a broken link.
SKIP_DIRS = {".git", "runs", "data", "node_modules", "__pycache__", ".pytest_cache"}

#: `[text](target)` and `![alt](target)`. The target stops at whitespace so a titled link --
#: `[x](path "Title")` -- yields the path alone.
LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)")

#: Link targets that are not paths. Checked as prefixes, case-insensitively.
NOT_A_PATH = ("http://", "https://", "mailto:", "ftp://", "data:", "#", "tel:")


def docs(root):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for fn in sorted(filenames):
            if fn.lower().endswith(".md"):
                out.append(os.path.join(dirpath, fn))
    return out


def targets(path):
    """Every link target in one document, with the line it sits on."""
    try:
        text = io.open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return []
    out = []
    for lineno, line in enumerate(text.splitlines(), 1):
        # Fenced code is still scanned. A link inside a fence is usually an EXAMPLE command
        # rather than a reference -- but the examples in this tree are real paths a reader is
        # told to run, and those rot exactly like references do. Two of the dead paths
        # `check_skill_docs.py` was written to catch were inside fences.
        for m in LINK.finditer(line):
            out.append((lineno, m.group(1)))
    return out


def check(root):
    dead = []
    n_links = 0
    for doc in docs(root):
        base = os.path.dirname(doc)
        for lineno, target in targets(doc):
            if target.lower().startswith(NOT_A_PATH):
                continue
            n_links += 1
            # Strip a trailing anchor: `FILE.md#heading` resolves as `FILE.md`.
            bare = target.split("#", 1)[0]
            if not bare:
                continue
            resolved = os.path.normpath(os.path.join(base, bare))
            if not os.path.exists(resolved):
                dead.append((os.path.relpath(doc, root).replace("\\", "/"),
                             lineno, target))
    return n_links, dead


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--quiet", action="store_true", help="exit code only")
    args = ap.parse_args(argv)

    n_links, dead = check(ROOT)
    if not args.quiet:
        print("checked %d relative link(s) in %d document(s)"
              % (n_links, len(docs(ROOT))))
    if not dead:
        if not args.quiet:
            print("every relative link resolves.")
        return 0
    if not args.quiet:
        print("")
        print("%d DEAD LINK(S):" % len(dead))
        for doc, lineno, target in dead:
            print("    %s:%d  ->  %s" % (doc, lineno, target))
        print("")
        print("A renamed results document is the usual cause: this tree renames a write-up when")
        print("its conclusion is superseded, and a reference to the old name sends a reader to a")
        print("retracted finding. Fix the reference, do not delete the link.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
