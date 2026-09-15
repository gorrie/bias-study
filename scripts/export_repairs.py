#!/usr/bin/env python3
"""Copy the repaired corpus into the public mirror, deriving the list rather than typing it.

WHY THIS EXISTS
---------------
`CORPUS-MAP-2026-09-14.md` has carried a banner since the day it was written:

    THE REPAIRED CORPORA ARE NOT IN THIS REPOSITORY YET ... every original run in
    this repository is the damaged version.

Which is honest and is not a resting place. The mirror's analysis gates read a corpus a third
of which was destroyed by an 800-token cap, so they cannot go green, and a reader who recomputes
a May number there gets the damaged answer with a note explaining why.

WHAT IT COPIES, AND WHY IT IS NOT A HAND-TYPED LIST
---------------------------------------------------
Three groups, all resolved from the registries that already exist:

  * every DERIVED corpus in `studypaths.REPAIRS` -- the spliced views the analysis reads;
  * every REPAIR RUN those views draw on, from `splice_corpus.CORPUS_REPAIRS` -- because a
    derived corpus without its sources is unauditable: a reader cannot check the splice;
  * the rung-2 runs in `RUNG2_RUNS` below, which are a collection rather than a repair and so
    appear in no registry.

A repair added later is therefore exported without editing this file, which is the only way a
list like this stays true. The one hand-maintained entry is the rung-2 group, and it is named
rather than globbed so adding a run to the public tree stays a decision.

WHAT IT REFUSES
---------------
A run that is still collecting. A half-copied collection in a public tree is worse than an
absent one: it looks complete, `collection_check` will score it, and nobody re-reads a directory
that is already there. Completion is judged by the manifest, and a run with no manifest is
treated as in-flight -- which is exactly the state `recollect_at_cap.py` used to leave behind
when it crashed after its last call.

    python scripts/export_repairs.py                 # plan; writes nothing
    python scripts/export_repairs.py --write
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from studypaths import REPAIRS, run_roots  # noqa: E402

#: Default destination: the public mirror's May-study run root. The mirror has TWO
#: (`data/` for the May study, `runs/` for the barometer) and putting a May repair
#: in the wrong one makes it invisible to every analysis that reads the other.
DEFAULT_DEST = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(HERE)))), "bias-study-release", "data")

#: Rung 2, which is a collection rather than a repair and appears in no registry.
#: The decomposition run is deliberately absent while it is still collecting; add
#: it when it lands, with its result, not before.
RUNG2_RUNS = (
    "2026-09-13-g0dm0d3-replicate",
    "2026-09-13-g0dm0d3-replicate-baseline",
    "2026-09-14-g0dm0d3-baseline-4k",
    "2026-09-14-g0dm0d3-proxy-control",
)

SKIP_SUFFIXES = (".log",)

#: RUNS THAT ARE COMPLETE AND HAVE NO MANIFEST, with the evidence for each.
#:
#: "No manifest" is the right default for "still collecting" and the wrong answer
#: for a run whose collector never wrote one. `run_g0dm0d3.py` wrote no manifest
#: at all until 2026-09-14, so the arm every rung-2 number comes from has none.
#:
#: The tempting fix is to generate one from the files. This project has refused
#: that before and refuses it here: a manifest derived from the data it exists to
#: check cannot detect a shortfall, which is the only thing a manifest is for.
#: `validate_runs.KNOWN` says the same about four May runs. So the gap is NAMED,
#: with the independent evidence of completeness, and travels with the export.
COMPLETE_WITHOUT_MANIFEST = {
    "2026-09-13-g0dm0d3-replicate":
        "run_g0dm0d3.py wrote no manifest until the day after this run. Complete "
        "on independent evidence: 300 records for 2 models x 3 conditions x 10 "
        "questions x 5 samples, all 60 cells at 5 byte-distinct draws, zero "
        "truncated, and collection_check ACCEPTED. Recorded in "
        "RESULTS-2026-09-13-pipeline-rung-replicate.md, written before the "
        "manifest gap was known.",
}


def _find(run):
    for root in run_roots():
        d = os.path.join(str(root), run)
        if os.path.isdir(d):
            return d
    return None


def _complete(path):
    """Is this run finished? A missing manifest means in-flight, not fine."""
    run = os.path.basename(path.rstrip("/\\"))
    mpath = os.path.join(path, "manifest.json")
    if not os.path.isfile(mpath):
        if run in COMPLETE_WITHOUT_MANIFEST:
            return True, "no manifest, complete on independent evidence"
        return False, "no manifest -- treated as still collecting"
    try:
        with open(mpath, encoding="utf-8") as fh:
            m = json.load(fh)
    except Exception as exc:
        return False, "unreadable manifest: %s" % exc
    if m.get("derived"):
        return True, "derived corpus"
    failed = m.get("calls_failed")
    if isinstance(failed, int) and failed:
        return True, "%d failed call(s), recorded" % failed
    return True, "manifest present"


def _sources():
    """The repair runs each derived corpus splices in."""
    try:
        from splice_corpus import CORPUS_REPAIRS
    except Exception:
        return []
    out = []
    for spec in CORPUS_REPAIRS.values():
        out.extend(spec["sources"])
    return out


def plan():
    wanted = []
    for base, derived in sorted(REPAIRS.items()):
        wanted.append((derived, "derived corpus for %s" % base))
    for src in sorted(set(_sources())):
        wanted.append((src, "repair run spliced into a derived corpus"))
    for r in RUNG2_RUNS:
        wanted.append((r, "rung-2 collection"))

    seen, rows = set(), []
    for run, why in wanted:
        if run in seen:
            continue
        seen.add(run)
        path = _find(run)
        if path is None:
            rows.append({"run": run, "why": why, "status": "MISSING in this tree"})
            continue
        ok, note = _complete(path)
        size = sum(os.path.getsize(os.path.join(dp, f))
                   for dp, _dn, fn in os.walk(path) for f in fn
                   if not f.endswith(SKIP_SUFFIXES))
        rows.append({"run": run, "why": why, "src": path, "bytes": size,
                     "status": "ready" if ok else "HELD: " + note})
    return rows


def copy_run(src, dest_root):
    dest = os.path.join(dest_root, os.path.basename(src))
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    shutil.copytree(src, dest,
                    ignore=shutil.ignore_patterns("*.log", "__pycache__"))
    return dest


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--write", action="store_true", help="copy; without it, plan only")
    ap.add_argument("--dest", default=DEFAULT_DEST)
    args = ap.parse_args(argv)

    rows = plan()
    if not rows:
        print("CHECKED NOTHING -- no runs resolved from the registries. This is not "
              "a pass.", file=sys.stderr)
        return 1

    ready = [r for r in rows if r["status"] == "ready"]
    held = [r for r in rows if r["status"] != "ready"]
    total = sum(r.get("bytes", 0) for r in ready)

    print("EXPORT PLAN -> %s" % args.dest)
    for r in rows:
        mb = ("%6.1f MB" % (r["bytes"] / 1e6)) if r.get("bytes") else "        "
        print("  %-44s %s  %-10s %s"
              % (r["run"], mb, r["status"] if r["status"] != "ready" else "", r["why"]))
    print("\n  %d ready, %d held, %.1f MB" % (len(ready), len(held), total / 1e6))
    if held:
        print("  HELD runs are not copied. A half-copied collection in a public tree is")
        print("  worse than an absent one: it looks complete and nobody re-reads it.")

    if not args.write:
        print("\nNothing written. Re-run with --write.")
        return 0

    if not os.path.isdir(args.dest):
        print("destination does not exist: %s" % args.dest, file=sys.stderr)
        return 2
    for r in ready:
        dest = copy_run(r["src"], args.dest)
        print("  wrote %s" % dest)
    print("\ncopied %d run(s). The mirror's pre-commit corpus gate is the oracle for"
          "\nwhether any of it carries licensed instrument text -- it runs on commit."
          % len(ready))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
