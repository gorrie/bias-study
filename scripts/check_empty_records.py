#!/usr/bin/env python3
"""A zero-byte record file is a STUB. It must not read as "this arm has no data".

WHY THIS EXISTS
---------------
On 2026-09-20 a careful independent reviewer read
`runs/2026-05-27-abliteration/**/gemma-2-9b-*.jsonl`, found every one of them empty, and
concluded that evilrobots.lol was publishing a fifth abliteration family with no data behind
it -- a fabricated claim on a live page, reported in a turnover document as a known-bad,
public-facing item.

**The claim is true and the data exists.** It is in a sibling directory,
`2026-05-27-abliteration-gemma2/`, which holds 20 stock and 20 abliterated scored records --
exactly the 40 the page's "39 of 40 judge cells unanimous" refers to. The empty files are
stubs left by the FIRST attempt, the one that failed the SVD step on an Intel/MKL box for three
weeks before the same code path cleared in one shot on an M5.

So nothing was fabricated and nothing was missing. What existed was **an ambiguity nothing
resolved**: an empty file and an absent measurement are the same thing to every reader, human
or scripted, and the tools here already treat them alike -- `abliteration_effect_check` reports
that family as having "no shared cells at all", which is true of the files and false of the
study.

The cost was not hypothetical. It consumed a reviewer's time, it produced a written accusation
against a correct public page, and had it gone the other way -- an arm quietly dropped and its
stubs left behind -- nothing here would have caught that either.

WHAT IT DOES
------------
Finds every zero-byte `.jsonl` under `runs/` and `data/` and requires each to be DECLARED: named in
`data/empty-records.json` with a reason and, where the data lives elsewhere, where. An
undeclared empty file is a defect. A declared one is a fact somebody decided.

    python scripts/check_empty_records.py
    python scripts/check_empty_records.py --check     # exit 1 on an undeclared empty file
    python scripts/check_empty_records.py --write     # seed the declaration file for editing

Exit 0 all declared, 1 undeclared or stale declarations, 2 NOT APPLICABLE (neither root here).
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
RUNS = os.path.join(STUDY, "runs")
DATA = os.path.join(STUDY, "data")
DECL = os.path.join(STUDY, "data", "empty-records.json")
#: Both record roots. This walked runs/ alone; the fourteen abliteration stubs that caused
#: the 2026-09-20 incident moved to data/ with the May runs, and from then on the gate
#: checked none of them while their declarations went stale under runs/ paths.
ROOTS = (RUNS, DATA)


def empty_files():
    """Every zero-byte .jsonl under runs/ and data/, as paths relative to the study root."""
    out = []
    paths = [p for root in ROOTS
             for p in glob.glob(os.path.join(root, "**", "*.jsonl"), recursive=True)]
    for path in sorted(paths):
        try:
            if os.path.getsize(path) == 0:
                out.append(os.path.relpath(path, STUDY).replace("\\", "/"))
        except OSError:
            continue
    return out


def declared():
    if not os.path.exists(DECL):
        return {}
    try:
        with io.open(DECL, encoding="utf-8") as fh:
            rec = json.load(fh)
    except ValueError:
        return {}
    return rec.get("files") or {}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="exit 1 when a zero-byte record file is not declared")
    ap.add_argument("--write", action="store_true",
                    help="seed data/empty-records.json with the undeclared files, each "
                         "carrying a TODO reason for a human to replace")
    a = ap.parse_args(argv)

    if not any(os.path.isdir(r) for r in ROOTS):
        print("NOT APPLICABLE: no runs/ or data/ tree in %s." % STUDY)
        return 2

    found = empty_files()
    known = declared()
    undeclared = [f for f in found if f not in known]
    # A declaration for a file that is no longer empty, or no longer there, is a stale
    # exemption -- and an exemption list nobody prunes eventually covers a real defect.
    stale = [f for f in known if f not in found]

    if a.write:
        rec = {"_README": (
            "Zero-byte record files under runs/ and data/, each with the reason it is empty. An empty "
            "file and an absent measurement are indistinguishable to every reader, so one "
            "that is deliberate has to say so here. See check_empty_records.py for the "
            "incident that produced this file."),
            "files": dict(known)}
        for f in undeclared:
            rec["files"][f] = {"reason": "TODO -- say why this file is empty",
                               "data_elsewhere": None}
        with io.open(DECL, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(rec, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
        print("wrote %s with %d entr(ies), %d newly seeded"
              % (DECL, len(rec["files"]), len(undeclared)))
        return 0

    print("ZERO-BYTE RECORD FILES UNDER runs/ AND data/")
    print("  An empty file and an arm that was never collected look identical. This says")
    print("  which is which, because on 2026-09-20 the difference was read the wrong way")
    print("  and a correct published claim was written up as fabricated.")
    print()
    print("  %d empty file(s), %d declared, %d undeclared"
          % (len(found), len(found) - len(undeclared), len(undeclared)))
    if known:
        print()
        by_reason = {}
        for f, info in sorted(known.items()):
            if f not in found:
                continue
            key = (info.get("reason") or "?", info.get("data_elsewhere"))
            by_reason.setdefault(key, []).append(f)
        for (reason, elsewhere), files in sorted(by_reason.items()):
            print("  %d file(s): %s" % (len(files), reason))
            if elsewhere:
                print("      the data is at: %s" % elsewhere)
            for f in files[:3]:
                print("      %s" % f)
            if len(files) > 3:
                print("      ... and %d more" % (len(files) - 3))
    if undeclared:
        print()
        print("  UNDECLARED -- an empty record file nobody has explained:")
        for f in undeclared:
            print("    %s" % f)
        print()
        print("  Declare each in data/empty-records.json (--write seeds it), saying why it is")
        print("  empty and, if the measurement exists elsewhere, where. Deleting them is also")
        print("  a fine answer; leaving them undeclared is not.")
    if stale:
        print()
        print("  STALE DECLARATION(S) -- listed here and no longer empty or no longer present:")
        for f in stale:
            print("    %s" % f)
        print("  Remove them. An exemption list nobody prunes eventually covers a real defect.")

    if not a.check:
        return 0
    return 1 if (undeclared or stale) else 0


if __name__ == "__main__":
    raise SystemExit(main())
