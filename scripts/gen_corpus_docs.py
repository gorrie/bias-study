#!/usr/bin/env python3
"""Fill the generated tables in the per-corpus-root READMEs. `--check` exits 1 on drift.

WHY THESE FILES ARE GENERATED IN PART AND HAND-WRITTEN IN PART

The corpus is the deliverable. Someone arriving at the release should be able to work out what
is here, what it supports, and what it does not, without reading our source or our paper. That
needs two different kinds of writing and they have opposite failure modes:

  * **Prose** -- what this root is, what a reader may conclude from it, the one loading gotcha
    that bites. Written once, by a person, because nothing can generate a caveat.
  * **Tables** -- directories, records, models, instrument, withdrawal status. Every one of
    these is already computed off the records themselves by `run_inventory.scan()`. Typed into
    prose they are correct the day they are written and silently wrong afterwards.

So the numbers live between `<!-- GEN:name -->` markers and are overwritten from the scripts
that compute them. The prose around them is ours to maintain.

WHY IT REUSES `gen_paper.fill` RATHER THAN CARRYING ITS OWN COPY

`gen_paper` has filled GEN blocks in the paper for weeks, including the trailing-whitespace
rule that stops this gate fighting the mirror's pre-commit hook in a loop, and the diff-carrying
failure message that exists because "STALE blocks: floors" cost somebody an afternoon. A second
markdown-block filler would be a fork that agrees today, which is the single failure
`check_no_fork.py` exists to catch. `gen_paper.fill` takes a `blocks` mapping now; this passes
its own.

    python scripts/gen_corpus_docs.py            # write
    python scripts/gen_corpus_docs.py --check    # exit 1 if any block has drifted
"""
from __future__ import annotations

import argparse
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import gen_paper as G  # noqa: E402

#: Which GEN block each root's README carries. Same (script, args, trim) shape as
#: `gen_paper.BLOCKS`, because it is passed straight to the same renderer.
#:
#: `corpus-scale` is on `data/` alone and deliberately: it is the comparison against the
#: fifteen audited studies, and it belongs beside the corpus that makes the comparison
#: possible rather than beside the current battery.
BLOCKS = {
    "corpus-inventory-data": ("run_inventory.py", ["--corpus-markdown", "data"], None),
    "corpus-inventory-runs": ("run_inventory.py", ["--corpus-markdown", "runs"], None),
    "corpus-scale": ("controls_audit.py", ["--scale-markdown"], None),
    # The derived-corpora table in CORPUS-MAP: eligible records in each May run against its
    # spliced view, under the eligibility rule as it stands. Hand-typed it read 779 in one tree
    # and 778 in the other, and neither was the rule's answer after the 2026-09-25 re-splice.
    "corpus-derived": ("splice_corpus.py", ["--derived-markdown"], None),
}

#: README path -> the blocks it must carry.
TARGETS = {
    os.path.join(STUDY, "data", "README.md"): ("corpus-inventory-data", "corpus-scale"),
    os.path.join(STUDY, "runs", "README.md"): ("corpus-inventory-runs",),
    os.path.join(STUDY, "CORPUS-MAP-2026-09-14.md"): ("corpus-derived",),
}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)

    # EVERY BLOCK IS UNFENCED. `gen_paper.block_body` decides fencing from a name list, and a
    # markdown table inside a code fence renders as literal pipes -- the defect that shipped
    # three of the paper's tables as raw `|` characters. These names are registered there.
    for name in BLOCKS:
        if name not in ("corpus-inventory-data", "corpus-inventory-runs", "corpus-scale",
                        "corpus-derived"):
            raise SystemExit("unregistered block %r" % name)

    missing = [p for p in TARGETS if not os.path.exists(p)]
    if missing:
        # NOT a silent skip. A generator whose target is absent has generated nothing, and
        # saying so at exit 0 is how a README stays unwritten while its gate reports clean --
        # the vacuous-pass shape this repository has paid for repeatedly.
        for p in missing:
            print("MISSING: %s" % os.path.relpath(p, STUDY).replace("\\", "/"))
        print("")
        print("A corpus root with no README is the state this script exists to end. Write the "
              "prose with its GEN markers, then re-run.")
        return 1

    stale_files, wrote = [], 0
    for path, names in sorted(TARGETS.items()):
        rel = os.path.relpath(path, STUDY).replace("\\", "/")
        blocks = {n: BLOCKS[n] for n in names}
        raw = io.open(path, encoding="utf-8", newline="").read()
        nl = "\r\n" if "\r\n" in raw else "\n"
        text = raw.replace("\r\n", "\n")
        filled, stale = G.fill(text, check=args.check, blocks=blocks)
        if args.check:
            for name, diff in stale:
                stale_files.append((rel, name, diff))
            continue
        out = filled.replace("\n", nl) if nl == "\r\n" else filled
        if out != raw:
            io.open(path, "w", encoding="utf-8", newline="").write(out)
            wrote += 1
        print("%-22s %d block(s)" % (rel, len(names)))

    if args.check:
        if stale_files:
            print("STALE -- %d block(s) disagree with the corpus:" % len(stale_files))
            for rel, name, diff in stale_files:
                print("")
                print("  %s :: %s" % (rel, name))
                for line in diff[:24]:
                    print("    %s" % line)
            print("")
            print("Run: python scripts/gen_corpus_docs.py")
            return 1
        # A COUNT, NOT A BARE "OK". A gate that checked nothing must never read as passing.
        total = sum(len(v) for v in TARGETS.values())
        print("all %d generated block(s) across %d corpus README(s) are current"
              % (total, len(TARGETS)))
        return 0

    print("")
    print("rewrote %d file(s)" % wrote)
    return 0


if __name__ == "__main__":
    sys.exit(main())
