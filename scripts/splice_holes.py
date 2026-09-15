#!/usr/bin/env python3
"""Which cells are STILL missing after splicing existing re-collections in?

WHY THIS EXISTS
---------------
`2026-05-25-full` lost records to the 800-token cap. A re-collection at 4000 was
already run on 2026-09-05 and covers part of the damage. Before commissioning any
new collection, the question is not "how much was destroyed" but "how much is
still missing once what already exists is used."

A $259 re-collection was proposed on 2026-09-13 without asking that question. The
answer turned out to be a few hundred calls.

    python scripts/splice_holes.py                      # report
    python scripts/splice_holes.py --models             # the --models list to collect
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import eligibility as E  # noqa: E402

BASE = "2026-05-25-full"
#: Runs that re-collected part of BASE at a larger cap, newest last.
SPLICE_SOURCES = ("2026-09-05-recollect",)


def load(run, sub="scored"):
    """Records for one run, found through the run roots rather than a fixed path.

    This globbed `runs/<run>/<sub>` -- hardcoded to one root name AND relative to
    the working directory. In the public mirror the May corpus lives under
    `data/`, so it matched nothing and returned an empty list: every count came
    back zero and the report read like a clean corpus. `splice_corpus` resolves
    through `run_roots()` and the two disagreed by 252 cells, which is how this
    was found.

    A tool that cannot find the corpus should not be able to report on it.
    """
    from studypaths import run_roots
    paths = []
    for root in run_roots():
        d = root / run / sub
        if d.is_dir():
            paths.extend(sorted(glob.glob(os.path.join(str(d), "**", "*.jsonl"),
                                          recursive=True)))
    rows = []
    for p in paths:
        for line in open(p, encoding="utf-8", errors="replace"):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except ValueError:
                pass
    return rows


def key(r):
    return (r.get("model"), r.get("question_id"), r.get("condition"))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--models", action="store_true",
                    help="print the comma-separated model list with holes")
    a = ap.parse_args(argv)

    base = load(BASE)
    if not base:
        print("CHECKED NOTHING -- %s has no scored records. This is NOT a pass." % BASE,
              file=sys.stderr)
        return 2

    # Every cell the base run ATTEMPTED, eligible or not.
    attempted = {key(r) for r in base}
    eligible = {key(r) for r in base if E.is_eligible(r)}

    spliced = set()
    for src in SPLICE_SOURCES:
        rows = load(src)
        for r in rows:
            if E.is_eligible(r) and key(r) in attempted and key(r) not in eligible:
                spliced.add(key(r))

    have = eligible | spliced
    holes = attempted - have

    print("SPLICE REPORT -- %s" % BASE)
    print("  cells attempted            %d" % len(attempted))
    print("  eligible in the base run   %d" % len(eligible))
    print("  recovered by splicing %-4s %d" % (",".join(SPLICE_SOURCES), len(spliced)))
    print("  STILL MISSING              %d" % len(holes))
    print()

    by_model = collections.Counter(m for (m, _q, _c) in holes)
    have_by_model = collections.Counter(m for (m, _q, _c) in have)
    print("  %-36s %8s %8s" % ("model", "have", "missing"))
    for m in sorted(set(list(by_model) + list(have_by_model))):
        print("  %-36s %8d %8d" % (m.split("/")[-1], have_by_model.get(m, 0), by_model.get(m, 0)))

    if a.models and by_model:
        chan = {}
        for r in base:
            chan.setdefault(r.get("model"), r.get("channel", "openrouter"))
        print()
        print(",".join("%s:%s" % (chan.get(m, "openrouter"), m) for m in sorted(by_model)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
