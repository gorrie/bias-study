#!/usr/bin/env python3
"""Extract the records a gitignored corpus backup holds and the live tree does not.

WHY THIS EXISTS
---------------
`runs-backup-20260917-225458/` was a mid-collection snapshot: 1,742 files, 168.6 MB,
untracked and matched by `.gitignore`'s `runs-backup-*/`. Of its 39,274 records, 39,201
are byte-identical to a record in `runs/` once the `compass-run/1` -> `battery-run/1`
schema rename is set aside. **73 are not**, across 9 files, and they are the before-state
of two repairs the study has already documented:

  * `rederive_labels.py`, 2026-09-17 (`CORRECTIONS-2026-09-17-labels.md`) -- llama3.1:8b
    and gemma-4-12B sheets stored as `valid: false / failure_mode: other` that re-parse as
    complete answer sheets. Same `collected_at`, same seeds; only derived fields move.
  * the 2026-09-20 re-collection of `z-ai/glm-5.2` against a single pinned backend -- the
    2026-09-16/18 cell was replaced rather than merged, which is the routing-confound repair
    `PREREG-2026-09-14-i3-phase4.md` line 3 calls for.

NOTE ON WORDING, because it cost a test: this docstring may not contain a run-directory name
or the token a run directory is named after. `run_inventory` scans script SOURCE to decide
which directories are read by something, so a directory named only in prose here would read
as reachable and a genuinely orphaned run would go unreported. Describe; do not name.

A 168 MB duplicate sitting in the working tree is read by every `os.walk` in this
repository and is one careless glob away from being counted twice. Deleting it outright
would have destroyed those 73 records, which is the mistake this project made on
2026-09-22 with `withdrawn/backend-split-precollection/` -- deleting on the container
rather than reading the contents. So: extract the uniques into git, then drop the bulk.

    python scripts/extract_backup_uniques.py --backup runs-backup-20260917-225458 --dry-run
    python scripts/extract_backup_uniques.py --backup runs-backup-20260917-225458 --write

`--dry-run` reports and writes nothing. `--write` populates
`withdrawn/pre-repair-snapshots/` and refuses to run if the destination already holds
records, because re-running it against a tree where the live copy has moved on again
would silently change what the snapshot claims to be.

Exit 0 clean, 1 a defect, 2 NOT APPLICABLE (no backup directory here).
"""
from __future__ import annotations

import argparse
import collections
import glob
import hashlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)

#: Fields excluded from record identity. `schema` is the record SCHEMA NAME, renamed from
#: `compass-run/1` to `battery-run/1` after this snapshot was taken. It is a label on the
#: file format, not an observation, and treating a rename as 39,201 new records would bury
#: the 73 that matter.
IDENTITY_IGNORES = ("schema",)

DEST = os.path.join(STUDY, "withdrawn", "pre-repair-snapshots")


def _key(rec):
    d = {k: v for k, v in rec.items() if k not in IDENTITY_IGNORES}
    blob = json.dumps(d, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _load(path):
    out = []
    if not os.path.exists(path):
        return out
    for line in io.open(path, encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def survey(backup_root):
    """rel path -> list of records present in the backup and absent from runs/."""
    uniques = collections.OrderedDict()
    total = 0
    for path in sorted(glob.glob(os.path.join(backup_root, "**", "*.jsonl"),
                                 recursive=True)):
        rel = os.path.relpath(path, backup_root).replace(os.sep, "/")
        live = set(_key(r) for r in _load(os.path.join(STUDY, "runs", rel)))
        missing = []
        for rec in _load(path):
            total += 1
            if _key(rec) not in live:
                missing.append(rec)
        if missing:
            uniques[rel] = missing
    return uniques, total


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--backup", required=True,
                    help="the backup directory, relative to the study root")
    ap.add_argument("--write", action="store_true",
                    help="write the uniques to withdrawn/pre-repair-snapshots/")
    # NOT --check. In this repository that flag name means a gate registerable in
    # gates.GATES, and tests/test_gate_registry.py enforces that every script carrying one
    # is registered at some stage. This is a one-shot operator tool run once against a
    # backup that then goes away, so it takes the name that says what it does.
    ap.add_argument("--dry-run", action="store_true", help="report only; the default")
    args = ap.parse_args(argv)

    root = args.backup if os.path.isabs(args.backup) else os.path.join(STUDY, args.backup)
    if not os.path.isdir(root):
        print("NOT APPLICABLE: no backup directory at %s" % args.backup)
        return 2

    uniques, total = survey(root)
    n = sum(len(v) for v in uniques.values())
    print("backup %s" % args.backup)
    print("  records in the backup            : %d" % total)
    print("  already present in runs/         : %d" % (total - n))
    print("  PRESENT ONLY IN THE BACKUP       : %d in %d file(s)" % (n, len(uniques)))
    if not uniques:
        # A VACUOUS RUN MUST NOT READ AS A CLEAN ONE. Zero uniques is a real and good
        # answer, but only when the backup actually held records to compare.
        if total == 0:
            print("  and the backup held NO records at all -- nothing was compared.")
            return 1
        print("  the backup is fully redundant with runs/; nothing to extract.")
        return 0
    for rel, recs in uniques.items():
        print("     %-62s %d" % (rel, len(recs)))

    if not args.write:
        print("\ndry run; nothing written. Pass --write to extract.")
        return 0

    if os.path.isdir(DEST) and glob.glob(os.path.join(DEST, "**", "*.jsonl"),
                                         recursive=True):
        print("\nREFUSED: %s already holds records. A second extraction against a tree "
              "that has moved on would change what the snapshot claims to be. Remove it "
              "deliberately first." % os.path.relpath(DEST, STUDY))
        return 1

    written = 0
    for rel, recs in uniques.items():
        out = os.path.join(DEST, rel)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with io.open(out, "w", encoding="utf-8", newline="\n") as fh:
            for rec in recs:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        written += len(recs)
    print("\nwrote %d record(s) to %s" % (written, os.path.relpath(DEST, STUDY)))
    if written != n:
        print("DEFECT: wrote %d but surveyed %d" % (written, n))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
