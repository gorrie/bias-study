#!/usr/bin/env python3
"""Every run directory, what is in it, and what reads it.

WHY. A 2026-09-12 audit asked which collected data had never been analysed and could not answer
it: sixteen run directories holding 1,460 records were named in no document. Working out whether
that meant "unanalysed" or "an input rather than a finding" took a manual triage that nobody
should have to repeat, and a hand-maintained answer would rot the way every other hand-maintained
list in this project has.

This generates it. A directory is ACCOUNTED FOR when it is either named in a markdown document
or carries the collection schema the floor tools read; anything else is reported, so a genuinely
orphaned collection cannot hide among the inputs.

    python scripts/run_inventory.py
    python scripts/run_inventory.py --check    # exit 1 if any run is unaccounted for
    python scripts/run_inventory.py --json

No API calls. Arithmetic on records already on disk.
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)

#: Directories that are development fixtures, not measurements. Each says why.
FIXTURES = {
    "2026-09-08-evidence-collector-fake":
        "fake backend, for the collector's interruption/retry tests -- W10",
    "2026-09-08-evidence-qwen-pilot":
        "evidence-use-v1 pilot against the development case pack -- W05/W06",
    "2026-09-08-evidence-review-export-01":
        "offline exporter output, for pack review -- not a model measurement",
}


def scan(study=STUDY):
    out = []
    for path in sorted(glob.glob(os.path.join(study, "runs", "*"))):
        if not os.path.isdir(path):
            continue
        name = os.path.basename(path)
        files = glob.glob(os.path.join(path, "**", "*.jsonl"), recursive=True)
        records = 0
        models, conditions, schemas = set(), set(), set()
        for f in files:
            with open(f, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    records += 1
                    try:
                        rec = json.loads(line)
                    except ValueError:
                        continue
                    models.add(rec.get("model"))
                    if rec.get("condition"):
                        conditions.add(rec.get("condition"))
                    if rec.get("schema"):
                        schemas.add(rec.get("schema"))
        other = [f for f in glob.glob(os.path.join(path, "**", "*"), recursive=True)
                 if os.path.isfile(f) and not f.endswith(".jsonl")]
        out.append({"run": name, "files": len(files), "records": records,
                    "other_files": len(other),
                    "has_manifest": any(os.path.basename(f) == "manifest.json" for f in other),
                    "models": len([m for m in models if m]),
                    "conditions": sorted(conditions), "schemas": sorted(schemas)})
    return out


def documented(study=STUDY):
    text = ""
    for path in glob.glob(os.path.join(study, "*.md")):
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                text += fh.read()
        except OSError:
            pass
    return text


def classify(rows, doc_text):
    for r in rows:
        if r["run"] in FIXTURES:
            r["role"] = "fixture"
            r["why"] = FIXTURES[r["run"]]
        elif r["records"] == 0 and r["has_manifest"]:
            # NOT the same as empty. A manifest means the run was registered and then produced
            # nothing -- which is the W04 residency-probe story and is evidence, not absence.
            r["role"] = "registered, no records"
            r["why"] = ("manifest written, zero records collected -- an attempted run, which is "
                        "a fact about the attempt rather than an empty directory")
        elif r["records"] == 0 and r["other_files"]:
            r["role"] = "derived output only"
            r["why"] = "no run records; holds derived artifacts such as cross-method output"
        elif r["records"] == 0:
            r["role"] = "empty"
            r["why"] = "nothing on disk at all"
        elif r["run"] in doc_text:
            r["role"] = "documented"
            r["why"] = "named in a study document"
        elif any(s.startswith("compass-run/") for s in r["schemas"]):
            r["role"] = "collection input"
            r["why"] = ("carries the collection schema the floor tools read; an input to the "
                        "floors rather than a finding of its own")
        else:
            r["role"] = "UNACCOUNTED"
            r["why"] = "has records, no collection schema, named in no document"
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    rows = classify(scan(), documented())
    orphans = [r for r in rows if r["role"] == "UNACCOUNTED"]
    if a.json:
        print(json.dumps(rows, indent=1))
        return 1 if (a.check and orphans) else 0
    if not a.check:
        by_role = collections.Counter(r["role"] for r in rows)
        print("RUN INVENTORY -- %d directories, %d records"
              % (len(rows), sum(r["records"] for r in rows)))
        print("")
        for role in ("documented", "collection input", "fixture", "registered, no records",
                     "derived output only", "empty", "UNACCOUNTED"):
            group = [r for r in rows if r["role"] == role]
            if not group:
                continue
            print("%s (%d, %d records)"
                  % (role.upper(), len(group), sum(r["records"] for r in group)))
            for r in sorted(group, key=lambda x: -x["records"]):
                print("  %-44s %6d rec  %2d model(s)  %s"
                      % (r["run"], r["records"], r["models"],
                         ",".join(r["conditions"]) or "-"))
            print("")
        print("Roles: DOCUMENTED is named in a study document. COLLECTION INPUT carries the")
        print("collection schema and feeds the floor tools without a write-up of its own --")
        print("not the same as unanalysed. FIXTURE is development data, never a measurement.")
    if orphans:
        print("UNACCOUNTED FOR -- records, no schema, no mention:")
        for r in orphans:
            print("  %-44s %6d rec" % (r["run"], r["records"]))
        return 1
    if a.check:
        print("run inventory: every directory accounted for")
    return 0


if __name__ == "__main__":
    sys.exit(main())
