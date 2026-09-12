#!/usr/bin/env python3
"""Fill the README's generated blocks from the run data. Nothing in them is hand-written.

WHY
---
The README is the paper for anyone who clones this repository -- the academic writeup is not
distributed here. It carried a hand-typed floors table, and on 2026-09-05 four of its numbers
were stale and none of them was gated:

    requantisation side-flip p90        said 10, measured 6   (10 is the MAX, not the p90)
    deliberate manipulation endpoint    said 26, measured 21  (26 is the endpoint MAX)
    instruction paraphrase              missing entirely
    run-to-run replicate                missing entirely

The two missing rows are the ones added on 2026-09-04 that make the paper's point hardest --
rewording the wrapper, and running the identical prompt twice. A reader of this repository could
not see either.

`key_numbers.py --check-release` gates two sentences in this file. It cannot gate a table, so
the table is generated instead.

    python scripts/gen_readme.py           # fill the blocks
    python scripts/gen_readme.py --check   # exit 1 if stale (gate)
"""
from __future__ import annotations

import argparse
import io
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
README = os.path.join(ROOT, "README.md")

PRIOR_WORK = os.path.join(ROOT, "PRIOR-WORK-CORRECTIONS.md")

BLOCKS = {
    "floors": [sys.executable, os.path.join(HERE, "floor_table.py"), "--markdown"],
    # The class-split 2x2. Generated for the reason the floors table is: it was hand-typed
    # once and two of its four cells came from the wrong computation.
    "class_split": [sys.executable, os.path.join(HERE, "floor_table.py"), "--class-split"],
}

# PRIOR-WORK-CORRECTIONS.md restated the controls tallies in hand-typed markdown, in the
# document whose whole subject is other people's numbers going stale. On 2026-09-12 its
# same-version row still said "8 no, 1 n/a, 3 unknown" after those three unknowns had been
# resolved by reading the papers, and the sentence beneath it -- "Not one of the twelve" --
# was reasoning off the stale row. Generated now, from the same JSON the matrix renders from.
PRIOR_WORK_BLOCKS = {
    "tally_samever": [sys.executable, os.path.join(HERE, "controls_audit.py"),
                      "--tally-markdown", "--controls",
                      "same_version_dist,same_version_point,reported_mde"],
    "tally_scoring": [sys.executable, os.path.join(HERE, "controls_audit.py"),
                      "--tally-markdown", "--controls",
                      "judge_free_scoring,judge_lean_reported,self_judging_disclosed,longitudinal"],
}
BLOCKS.update(PRIOR_WORK_BLOCKS)

#: Which file each block lives in.
TARGETS = {name: (PRIOR_WORK if name in PRIOR_WORK_BLOCKS else README) for name in BLOCKS}


def rendered(name):
    """Run the emitter and return its output. One generator, not a reimplementation.

    The child is forced to UTF-8 and the decode is STRICT, both deliberately. On Windows a
    Python child writing to a pipe uses the console codepage (cp1252), so the daggers and
    em-dashes in the floors table arrived as undecodable bytes; with the previous
    errors="replace" they were silently rewritten as U+FFFD and written into the README as
    mojibake, by the generator whose entire job is to keep that file correct. A generator
    that quietly corrupts its own output is worse than one that fails, so this fails.
    """
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    out = subprocess.run(BLOCKS[name], capture_output=True, text=True,
                         encoding="utf-8", errors="strict", cwd=ROOT, env=env)
    if out.returncode != 0:
        raise SystemExit("emitter for %s failed:\n%s" % (name, out.stderr[-800:]))
    if "�" in out.stdout:
        raise SystemExit("emitter for %s produced U+FFFD -- refusing to write mojibake into "
                         "the README" % name)
    return out.stdout.strip()


def fill(text, name, body, where="README.md"):
    begin = "<!-- GEN:%s" % name
    end = "<!-- /GEN:%s -->" % name
    a = text.find(begin)
    if a < 0:
        raise SystemExit("%s has no %s marker" % (where, begin))
    a = text.find("-->", a) + 3
    b = text.find(end)
    if b < 0:
        raise SystemExit("%s has no %s marker" % (where, end))
    return text[:a] + "\n" + body + "\n" + text[b:]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)

    by_file = {}
    for name in BLOCKS:
        by_file.setdefault(TARGETS[name], []).append(name)

    stale, filled = [], 0
    for path, names in sorted(by_file.items()):
        have = io.open(path, encoding="utf-8").read()
        want = have
        for name in names:
            want = fill(want, name, rendered(name), os.path.basename(path))
        if args.check:
            if have.replace("\r\n", "\n").strip() != want.replace("\r\n", "\n").strip():
                stale.append(os.path.basename(path))
        else:
            io.open(path, "w", encoding="utf-8", newline="\n").write(want)
            filled += len(names)

    if args.check:
        if stale:
            print("Generated block(s) are STALE in: %s" % ", ".join(stale))
            print("Run: python scripts/gen_readme.py")
            return 1
        print("Generated block(s) in %d file(s) match the run data."
              % len(by_file))
        return 0

    print("filled %d block(s) across %d file(s)" % (filled, len(by_file)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
