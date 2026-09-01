#!/usr/bin/env python3
"""Refuse any commit that would publish third-party instrument text.

The 62 politicalcompass.org propositions are licensed text and not the author's work. They
appear verbatim inside every run record produced by the forced-choice study, in the
`forcing_prompt` field, and this repository is public.

On 2026-09-01, 525 of those run files were copied into this working tree while staging a data
release. 460 carried the text. `.gitignore` did not cover them, so a single `git add -A` would
have published someone else's questionnaire in bulk under the author's name. They were removed
by hand. This hook is what makes that not depend on remembering.

It checks STAGED content, not the working tree, because a git history keeps what a working tree
forgets -- scrubbing after a commit does not unpublish anything.

    python scripts/check_corpus.py            # check staged files (pre-commit)
    python scripts/check_corpus.py --all      # check every tracked file
"""
from __future__ import annotations

import argparse
import io
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FINGERPRINTS = os.path.join(ROOT, ".corpus-fingerprint")

SKIP_SUFFIX = (".png", ".jpg", ".jpeg", ".pdf", ".zip", ".7z", ".gz", ".woff", ".woff2")
# The fingerprint file names the fragments on purpose and must not trip its own check.
SKIP_PATHS = {".corpus-fingerprint", "scripts/check_corpus.py"}


def load_fingerprints():
    out = []
    with io.open(FINGERPRINTS, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                out.append(line)
    return out


def staged_files():
    proc = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
                          capture_output=True, text=True, cwd=ROOT)
    return [p for p in proc.stdout.splitlines() if p.strip()]


def tracked_files():
    proc = subprocess.run(["git", "ls-files"], capture_output=True, text=True, cwd=ROOT)
    return [p for p in proc.stdout.splitlines() if p.strip()]


def staged_content(path):
    proc = subprocess.run(["git", "show", ":" + path], capture_output=True, cwd=ROOT)
    return proc.stdout.decode("utf-8", errors="replace")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--all", action="store_true",
                    help="scan every tracked file instead of the staged set")
    args = ap.parse_args(argv)

    prints = load_fingerprints()
    if not prints:
        print("check_corpus: .corpus-fingerprint is empty -- refusing to pass vacuously")
        return 1

    paths = tracked_files() if args.all else staged_files()
    hits = []
    for path in paths:
        if path in SKIP_PATHS or path.lower().endswith(SKIP_SUFFIX):
            continue
        try:
            if args.all:
                with io.open(os.path.join(ROOT, path), encoding="utf-8",
                             errors="replace") as fh:
                    text = fh.read()
            else:
                text = staged_content(path)
        except (OSError, UnicodeError):
            continue
        for fp in prints:
            if fp in text:
                hits.append((path, fp))
                break

    if not hits:
        print("check_corpus: %d file(s) checked, no third-party instrument text" % len(paths))
        return 0

    print("COMMIT REFUSED -- third-party instrument text in %d file(s)." % len(hits))
    print("The politicalcompass.org propositions are not the author's work and this")
    print("repository is public. Publish scrubbed, item-id-keyed exports instead, with a")
    print("fetcher that retrieves the items at the reader's end.")
    print()
    for path, fp in hits[:20]:
        print("  %s" % path)
        print("      matched: %s..." % fp[:56])
    if len(hits) > 20:
        print("  ... and %d more" % (len(hits) - 20))
    return 1


if __name__ == "__main__":
    sys.exit(main())
