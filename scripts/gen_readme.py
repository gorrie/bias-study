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

BLOCKS = {
    "floors": [sys.executable, os.path.join(HERE, "floor_table.py"), "--markdown"],
}


def rendered(name):
    """Run the emitter and return its output. One generator, not a reimplementation."""
    out = subprocess.run(BLOCKS[name], capture_output=True, text=True,
                         encoding="utf-8", errors="replace", cwd=ROOT)
    if out.returncode != 0:
        raise SystemExit("emitter for %s failed:\n%s" % (name, out.stderr[-800:]))
    return out.stdout.strip()


def fill(text, name, body):
    begin = "<!-- GEN:%s" % name
    end = "<!-- /GEN:%s -->" % name
    a = text.find(begin)
    if a < 0:
        raise SystemExit("README has no %s marker" % begin)
    a = text.find("-->", a) + 3
    b = text.find(end)
    if b < 0:
        raise SystemExit("README has no %s marker" % end)
    return text[:a] + "\n" + body + "\n" + text[b:]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)

    have = io.open(README, encoding="utf-8").read()
    want = have
    for name in BLOCKS:
        want = fill(want, name, rendered(name))

    if args.check:
        if have.replace("\r\n", "\n").strip() != want.replace("\r\n", "\n").strip():
            print("README generated block(s) are STALE. Run: python scripts/gen_readme.py")
            return 1
        print("README generated block(s) match the run data.")
        return 0

    io.open(README, "w", encoding="utf-8", newline="\n").write(want)
    print("filled %d block(s) in README.md" % len(BLOCKS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
