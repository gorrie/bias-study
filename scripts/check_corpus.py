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
import hashlib
import io
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FINGERPRINTS = os.path.join(ROOT, ".corpus-fingerprint")

HASHED = os.path.join(ROOT, ".corpus-fingerprint-hashed")

SKIP_SUFFIX = (".png", ".jpg", ".jpeg", ".pdf", ".zip", ".7z", ".gz", ".woff", ".woff2")
# The fingerprint file names the fragments on purpose and must not trip its own check.
SKIP_PATHS = {".corpus-fingerprint", ".corpus-fingerprint-hashed",
              "scripts/check_corpus.py"}

# Typographic folding, shared by the hash generator. Must stay identical on both sides or
# the hashes silently stop matching and the check passes on text it was built to catch.
FOLD = {
    "‘": "'", "’": "'", "‚": "'", "‛": "'",
    "“": '"', "”": '"', "„": '"',
    "–": "-", "—": "-", "−": "-",
    " ": " ", "…": "...",
}


def fold_for_hash(text):
    """Normalise away everything that is rendering rather than wording.

    WHY THE HASHED CHECK EXISTS (2026-09-01)
    ----------------------------------------
    The plaintext list above holds TEN fragments for a SIXTY-TWO proposition instrument, and
    matches case-sensitively with `fp in text`. So a leak quoting the other 52 propositions
    passed, and so did a leak that changed one capital letter or served `&#039;` instead of
    an apostrophe. That is a detector with a 52-item blind spot, guarding the one thing this
    repository must never publish.

    Hashes fix both ends at once: every one of the 62 propositions is covered, and NOTHING
    is reproduced -- a hash list cannot be read back into the questionnaire. Coverage went
    from 10 of 62 to 62 of 62 while the amount of third-party text stored went DOWN.
    """
    import html as htmllib
    text = htmllib.unescape(text)
    for src, dst in FOLD.items():
        text = text.replace(src, dst)
    # Punctuation is rendering too: a leak that swaps a comma for a semicolon is a leak.
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split()).casefold()


def window_hashes(text, window, include_short=True):
    """Hash window and window-1 spans, including short propositions embedded in prose.

    Previously a five-word proposition hashed whole only when it was the entire input;
    surrounding JSON/prose made it invisible to the six-word scan. Both widths are now
    checked. The generator uses include_short=False so long propositions retain the
    six-word specificity; only actual short propositions contribute five-word hashes.
    This is text matching, not a semantic or ownership classifier.
    """
    words = fold_for_hash(text).split()
    if not words:
        return set()
    if len(words) < window:
        return {hashlib.sha256(" ".join(words).encode("utf-8")).hexdigest()[:HASH_LEN]}
    return {hashlib.sha256(" ".join(words[i:i + width]).encode("utf-8")).hexdigest()[:HASH_LEN]
            for width in ({window, max(1, window-1)} if include_short else {window})
            for i in range(len(words) - width + 1)}


HASH_LEN = 16


def load_hashed():
    """(window, {hashes}) from .corpus-fingerprint-hashed, or (None, set()) if absent."""
    if not os.path.exists(HASHED):
        return None, set()
    window = None
    out = set()
    with io.open(HASHED, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("window "):
                window = int(line.split()[1])
                continue
            out.add(line)
    return window, out


def load_fingerprints():
    """The plaintext fragment list, or an empty list if it is not on disk.

    IT USED TO CRASH. A missing .corpus-fingerprint raised FileNotFoundError out of this
    function, so the gate did not run at all -- and a gate that crashes is a gate that gets
    commented out of CI by whoever hits it. Absence is now reported by the caller, loudly,
    and the hashed check still runs. The one thing that must never happen is a quiet pass:
    if BOTH fingerprint files are missing, main() exits non-zero, because a corpus check with
    no corpus to check against has verified nothing.
    """
    if not os.path.exists(FINGERPRINTS):
        return []
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
    """Every file git would ship: tracked, PLUS untracked-and-not-ignored.

    `git ls-files` alone was the defect. On 2026-09-12 twelve run files carrying verbatim
    instrument text were copied into this repository, `--all` was run, and it passed -- because
    the files were not yet tracked and so were not in the list. They were committed and pushed
    on the strength of that green result, and the check only went red afterwards.

    A gate asked "is the instrument about to ship" must look at what is about to ship. Anything
    untracked and unignored is one `git add -A` away from shipping, which is precisely how the
    460-file incident in this file's own docstring happened.
    """
    tracked = subprocess.run(["git", "ls-files"], capture_output=True, text=True, cwd=ROOT)
    untracked = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"],
                               capture_output=True, text=True, cwd=ROOT)
    seen, out = set(), []
    for stream in (tracked.stdout, untracked.stdout):
        for line in stream.splitlines():
            if line.strip() and line not in seen:
                seen.add(line)
                out.append(line)
    return out


def staged_content(path):
    proc = subprocess.run(["git", "show", ":" + path], capture_output=True, cwd=ROOT)
    return proc.stdout.decode("utf-8", errors="replace")


def _is_public_mirror():
    """True in the release mirror, False in the nested private study.

    The private study IS where the instrument lives -- 952 tracked files carry it, correctly.
    Run there, this gate printed "COMMIT REFUSED -- third-party instrument text in 952 file(s)"
    and "this repository is public", both wrong, and the obvious way to make it green is to
    delete the corpus. A gate whose failure invites destroying the data is worse than no gate.

    Discriminated by git prefix, the same way check_no_fork finds private HEAD: the private
    study sits at research/bias-study inside the book repository and reports a non-empty
    prefix; the mirror is its own repository root and reports none.
    """
    out = subprocess.run(["git", "rev-parse", "--show-prefix"],
                         capture_output=True, text=True, cwd=ROOT)
    return not out.stdout.strip()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--hashed-only", action="store_true",
                    help="run without .corpus-fingerprint, for a tree that deliberately does "
                         "not ship the ten plaintext fragments; hashes cover all 62")
    ap.add_argument("--all", action="store_true",
                    help="scan every tracked file instead of the staged set")
    args = ap.parse_args(argv)

    if not _is_public_mirror():
        print("NOT THE PUBLIC MIRROR: this is the private study, at the git prefix "
              "research/bias-study.")
        print("The instrument belongs here. This gate guards the PUBLIC export and is run "
              "against it by")
        print("release_check.py as checklist item 8. Exit 2 -- not applicable, not a failure, "
              "and NOT a")
        print("reason to delete anything.")
        return 2

    prints = load_fingerprints()
    if not prints and not args.hashed_only:
        print("check_corpus: .corpus-fingerprint is missing or empty -- refusing to pass")
        print("vacuously. The hashed list covers all 62 propositions and reproduces none, so a")
        print("tree that deliberately does not ship the ten plaintext fragments can pass")
        print("--hashed-only. That is a decision, not a default: the plaintext list is what")
        print("catches a wrongly-regenerated hash file, and a fingerprint that is only a hash")
        print("is one bad regeneration away from guarding nothing.")
        return 1
    if not prints:
        print("check_corpus: --hashed-only. Running without the plaintext fragment list.")
        print("  All 62 propositions are covered by hashes. NOT covered: a corrupted or")
        print("  wrongly-regenerated hash file, which the plaintext list exists to catch.")

    window, hashed = load_hashed()
    if hashed and not window:
        print("check_corpus: .corpus-fingerprint-hashed has no `window N` line -- refusing")
        print("to guess the n-gram size, because guessing it wrong passes silently.")
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
        matched = None
        for fp in prints:
            if fp.lower() in text.lower():
                matched = "plaintext fragment: %s..." % fp[:52]
                break
        if matched is None and hashed:
            overlap = window_hashes(text, window) & hashed
            if overlap:
                # Deliberately does not say WHICH proposition. The point of the hashed list
                # is that this repository holds no copy of the text to quote back.
                matched = ("%d hashed %d-gram(s) of the instrument"
                           % (len(overlap), window))
        if matched:
            hits.append((path, matched))

    if not hits:
        print("check_corpus: %d file(s) checked against %d plaintext fragment(s) and %d "
              "hashed %s-gram(s), no third-party instrument text"
              % (len(paths), len(prints), len(hashed), window or "?"))
        return 0

    print("COMMIT REFUSED -- third-party instrument text in %d file(s)." % len(hits))
    print("The politicalcompass.org propositions are not the author's work and this")
    print("repository is public. Publish scrubbed, item-id-keyed exports instead, with a")
    print("fetcher that retrieves the items at the reader's end.")
    print()
    for path, why in hits[:20]:
        print("  %s" % path)
        print("      matched: %s" % why)
    if len(hits) > 20:
        print("  ... and %d more" % (len(hits) - 20))
    return 1


if __name__ == "__main__":
    sys.exit(main())
