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
import fnmatch
import glob
import re
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

    # ---- SPENT, NOT ORPHANED. Added 2026-09-20 when the reachability check first ran and
    # found them: real collections whose job was to answer a question BEFORE the wave, which
    # they did. They are unreachable by design, because nothing should be reading a smoke
    # test into a floor. Declared rather than deleted -- each is the evidence for a parameter
    # the wave then used.
    "2026-09-16-ratchet-v3-wave-budget-probe":
        "the 36-sheet probe that MEASURED the token budget the wave runs at, rather than "
        "assuming one. Its answer is the --max-tokens every later run carries; the sheets "
        "themselves are not a measurement of any model's position",
    "2026-09-18-bce-smoke":
        "seven sheets confirming conditions B, C and E render and parse before the panel-wide "
        "pass bought them",
    "2026-09-19-rung2-smoke":
        "three sheets confirming the rebuilt rung-2 collector reached OpenRouter directly, "
        "after the proxy design was dropped",
    # NOT LISTED, AND THAT IS THE POINT: the 2026-09-20 glm liveness probe lives in
    # `probes/`, not `runs/`. Two sheets asking whether z-ai/glm-5.2 was served at all after
    # 27 hours of 404s under its pin. It was -- from CoreWeave, not the Z.AI backend that
    # served all 20 of its wave sheets, which is why the answer changed no collection
    # decision. Declaring it a FIXTURE here would not have been enough: `runs/**` is swept by
    # the catch-all globs and those two sheets moved the paper's refusal table, z-ai 134 to
    # 136, on data collected to answer an availability question. A probe that changes a
    # published denominator is not a probe. RESEARCH-BACKLOG 22 carries the general case --
    # the declared fixtures already in `runs/` are swept the same way.
    "2026-09-13-g0dm0d3-smoke":
        "ten sheets against the G0DM0D3 proxy, before that design was dropped for going "
        "direct. Superseded by the rung-2 arm, kept as the record of what the proxy returned",
    "2026-09-13-g0dm0d3-smoke2":
        "as above, the second proxy attempt",
    "2026-09-13-truncation-proof":
        "ten sheets demonstrating that a truncated response comes back with "
        "finish_reason 'stop' through the proxy -- the evidence for LEARNINGS #4, which is "
        "the point of keeping it rather than a measurement of any model",
}


def _corpus_roots(study):
    """Every directory that holds run directories: `runs/` here, and `data/` in the mirror.

    HARDCODING `runs/` MADE THIS BLIND IN THE TREE THAT SHIPS. The public mirror keeps the
    battery under `runs/` and the 42-directory May study under `data/`, so an inventory that
    walks only `runs/` reports the mirror as holding 12 directories and no previous-instrument
    records at all -- while 31,713 of them sit one directory over. The corpus-split line added
    on 2026-09-23 would then have answered "what is old in the release" with "nothing", which
    is the opposite of true and exactly the kind of confident wrong number this file exists to
    stop.

    RESOLVED AGAINST THE `study` ARGUMENT, NOT GLOBALLY. The first version called
    `studypaths.run_roots()`, which answers for the real tree wherever it is -- so
    `scan(tmp_path)` silently inventoried the live corpus instead of the fixture and four
    tests went red carrying roles from the wrong directory. A function that takes a root and
    then ignores it is worse than one that takes none.
    """
    roots = []
    for name in ("data", "runs"):
        cand = os.path.join(study, name)
        if not os.path.isdir(cand):
            continue
        # `data/` holds config JSON in the private tree and run directories in the mirror, so
        # it counts as a corpus root only when it actually contains runs.
        #
        # THE PREDICATE IS `raw/` OR `scored/`, which is what the scope-disclosure code this
        # replaced already used and had proved against the mirror's 42. Accepting a bare
        # `*.jsonl` as well -- the first attempt -- swept in `data/external`, a third-party
        # dataset of 24,180 records that is not a run, and the study tree's inventory jumped
        # from 47,537 records to 71,717. A looser predicate does not find more runs; it finds
        # things that are not runs.
        if name == "runs" or any(
                os.path.isdir(os.path.join(cand, d))
                and (os.path.isdir(os.path.join(cand, d, "raw"))
                     or os.path.isdir(os.path.join(cand, d, "scored")))
                for d in os.listdir(cand)):
            roots.append(cand)
    return roots or [os.path.join(study, "runs")]


def scan(study=STUDY):
    _globs = analysis_globs()
    out = []
    paths = []
    for root in _corpus_roots(study):
        paths += sorted(glob.glob(os.path.join(root, "*")))
    for path in paths:
        if not os.path.isdir(path):
            continue
        name = os.path.basename(path)
        files = glob.glob(os.path.join(path, "**", "*.jsonl"), recursive=True)
        records = 0
        models, conditions, schemas = set(), set(), set()
        instruments = collections.Counter()
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
                    instruments[rec.get("instrument") or "(none)"] += 1
        other = [f for f in glob.glob(os.path.join(path, "**", "*"), recursive=True)
                 if os.path.isfile(f) and not f.endswith(".jsonl")]
        out.append({"run": name, "files": len(files), "records": records,
                    "other_files": len(other),
                    "has_manifest": any(os.path.basename(f) == "manifest.json" for f in other),
                    "models": len([m for m in models if m]),
                    "conditions": sorted(conditions), "schemas": sorted(schemas),
                    "instruments": dict(instruments),
                    "corpus": _corpus_of(instruments),
                    "read_by": readers(name, _globs)})
    return out


#: The instrument the CURRENT study is computed from. Everything else is previous work.
LIVE_INSTRUMENT_PREFIX = "ratchet-battery"


def _corpus_of(instruments):
    """CURRENT, PREVIOUS or MIXED, from the records' own `instrument` field.

    WHY THIS COLUMN EXISTS. "What is in the current study and what is old" was answered four
    different ways in one session on 2026-09-22, because it was answered from prose each time
    -- different scopes (files, records, directories), two trees, and a tree that was legitimately
    changing as material was restored and a duplicate deleted. Every one of those answers was
    typed. This one is read off the records, so the next person to ask gets the same number as
    the last, and gets it from a command rather than from somebody's recollection.

    A run is CURRENT when every record in it carries the live battery, PREVIOUS when none does,
    and MIXED when they disagree -- which is a defect worth seeing rather than a category:
    no run should straddle two instruments.
    """
    if not instruments:
        return "empty"
    live = sum(n for k, n in instruments.items()
               if str(k).startswith(LIVE_INSTRUMENT_PREFIX))
    total = sum(instruments.values())
    if live == total:
        return "current"
    if live == 0:
        return "previous"
    return "MIXED"


#: A glob so broad it cannot fail. `runs/**/*.jsonl` matches every directory there can be, so
#: counting it as a reader makes the reachability test vacuous -- the first version of this
#: check included it and nothing could ever be flagged. The order floor genuinely does sweep
#: the whole tree and filter (`floor_table._order_cells`: an include list fails open on new
#: directories, so the default is read-everything-and-name-exclusions), which means a directory
#: matched only by this is not invisible to EVERYTHING -- its condition-A T01 sheets can enter
#: that one floor. It is invisible to the arm it was collected for, which is the failure.
CATCH_ALL = ("runs/**/*.jsonl", "runs/*/*.jsonl", "runs/*", "runs/**", "runs/**/*",
             # THE SECOND TIME THIS CHECK WENT VACUOUS, an hour after the first. `runs/` is a
             # bare prefix used for path JOINING, not matching -- `os.path.join(STUDY, "runs",
             # name)` and friends -- and it reaches every directory there is. With it counted
             # as a reader, `2026-09-20-provider-pinned` came back "read_by=['runs/']" and the
             # check that exists because of that directory passed it.
             #
             # A catch-all is not a property of the string, it is a property of what the
             # string can match. Anything that matches everything is excluded, however it is
             # spelled.
             "runs/", "runs")

#: Glob literals that name a run path, READ OUT OF THE SCRIPTS THEMSELVES.
#:
#: HAND-TYPING THIS LIST WAS THE FIRST ATTEMPT AND IT WAS WRONG WITHIN A MINUTE. Typed against
#: the battery arms, it declared the entire May judged corpus unreachable -- 5,460 records in
#: `2026-05-25-full` alone -- because `ci_analysis` and `judge_lean` reach it through globs the
#: list had never heard of. A reachability check that does not know every reader reports
#: working data as dead, which is worse than the defect it was written for: the first failure
#: costs a dollar, the second costs trust in the check.
#:
#: So the readers are derived. Anything in `scripts/*.py` that spells a path under `runs/` is a
#: reader, and a glob added tomorrow is counted tomorrow -- the same rule `_order_cells` reached
#: after an include list failed it twice.
_GLOB_RE = re.compile(r"""["'](runs[/\\][^"']*)["']""")


def analysis_globs(script_dir=HERE):
    out = set()
    for path in sorted(glob.glob(os.path.join(script_dir, "*.py"))):
        if os.path.basename(path) == os.path.basename(__file__):
            continue
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                src = fh.read()
        except OSError:
            continue
        for lit in _GLOB_RE.findall(src):
            lit = lit.replace("\\", "/")
            if lit in CATCH_ALL:
                continue
            # BELT AND BRACES: a literal that matches two directories chosen to have nothing
            # in common is a catch-all whatever it is spelled, and the named list above can
            # only ever enumerate the ones already seen. Tested rather than listed.
            if all(fnmatch.fnmatch("runs/%s/x.jsonl" % probe, lit) or
                   "runs/%s" % probe == lit.rstrip("/") or
                   ("runs/%s" % probe).startswith(lit.rstrip("*").rstrip("/") + "/")
                   for probe in ("zzz-alpha", "qqq-omega")):
                continue
            out.add(lit)
    return sorted(out)


def _script_text(script_dir=HERE):
    """Every script's source, concatenated. Cached on the function."""
    if getattr(_script_text, "_cache", None) is None:
        buf = []
        for path in sorted(glob.glob(os.path.join(script_dir, "*.py"))):
            # THIS FILE IS NOT A READER. Its comments name run directories as EXAMPLES of the
            # defect -- `2026-09-20-provider-pinned` is written up above precisely because
            # nothing read it -- and counting a cautionary tale as evidence of reachability
            # makes the check certify the thing it was written to catch.
            if os.path.abspath(path) == os.path.abspath(__file__):
                continue
            try:
                with open(path, encoding="utf-8", errors="replace") as fh:
                    buf.append(fh.read())
            except OSError:
                pass
        _script_text._cache = "\n".join(buf)
    return _script_text._cache


def readers(name, globs=None):
    """How this run directory is reachable, if at all.

    TWO WAYS, and the first version knew only one. A directory is read either because a GLOB
    sweeps it up, or because something names it EXPLICITLY -- `item_omission --run
    2026-09-18-omission-hosted`, the wave constant in half a dozen scripts, a run named in a
    results document. Counting only globs reported `2026-05-25-full` as unreachable, which is
    the 5,460-record May corpus that half the repository reads by name.

    Returns a list of reasons; empty means nothing reaches it by either route, which is the
    state that costs money.
    """
    globs = analysis_globs() if globs is None else globs
    probes = ("runs/%s" % name, "runs/%s/x.jsonl" % name, "runs/%s/sub/x.jsonl" % name,
              "runs/%s/sub/deeper/x.jsonl" % name)
    hits = []
    for g in globs:
        base = g if g.endswith(".jsonl") or "*" in g else g.rstrip("/")
        if any(fnmatch.fnmatch(p, base) or p.startswith(base.rstrip("*").rstrip("/") + "/")
               for p in probes):
            hits.append(g)
    if name in _script_text():
        hits.append("named in a script")
    # THE THIRD ROUTE, and the weakest: a run reachable only because a document prints the
    # command that reads it -- `item_omission.py --run 2026-09-18-omission-hosted` in PLAN.md.
    # Nothing automated walks it; a person has to type the name. That is a real route (the
    # hosted omission arm is 864 records behind a headline finding and this is how it is read)
    # and it is genuinely more fragile than a glob, so it is named differently rather than
    # folded in. A run with NONE of the three is the one that cost money.
    if name in documented():
        hits.append("named in a document")
    return hits


def documented(study=STUDY):
    """Every study document, in EITHER tree's layout.

    This globbed `<study>/*.md` only. The private tree keeps its pre-registrations and
    results documents flat at the root, so that was complete there -- and the PUBLIC MIRROR
    files them under `prereg/` and `results/`, where the glob could not see them. Measured
    2026-09-21: five run directories holding 1,598 records read as UNACCOUNTED FOR in the
    mirror -- "has records, no collection schema, named in no document" -- while the
    documents naming every one of them sat two directories down. A reachability check that
    cannot see half the tree reports absence it did not establish.
    """
    text = ""
    for pattern in ("*.md", os.path.join("prereg", "*.md"),
                    os.path.join("results", "*.md")):
        for path in glob.glob(os.path.join(study, pattern)):
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
    # COLLECTED AND UNREACHABLE is a different failure from UNACCOUNTED, and the inventory
    # could not see it: a directory can be documented, manifested, schema-correct and still
    # sit outside every glob the analysis walks. Records with a role and no reader.
    unread = [r for r in rows
              if r["records"] and not r["read_by"]
              and r["role"] not in ("fixture", "empty", "derived output only")]
    if a.json:
        print(json.dumps(rows, indent=1))
        return 1 if (a.check and (orphans or unread)) else 0
    if not a.check:
        by_corpus = collections.Counter(r["corpus"] for r in rows)
        cur = [r for r in rows if r["corpus"] == "current"]
        prev = [r for r in rows if r["corpus"] == "previous"]
        mixed = [r for r in rows if r["corpus"] == "MIXED"]
        print("CORPUS SPLIT, read off the records' own instrument field")
        print("  CURRENT  (%s)  %2d dir(s), %6d record(s)"
              % (LIVE_INSTRUMENT_PREFIX, len(cur), sum(r["records"] for r in cur)))
        print("  PREVIOUS            %2d dir(s), %6d record(s)"
              % (len(prev), sum(r["records"] for r in prev)))
        if mixed:
            print("  MIXED               %2d dir(s) -- a run straddling two instruments is a"
                  " defect, not a category:" % len(mixed))
            for r in mixed:
                print("      %-42s %s" % (r["run"], r["instruments"]))
        print("")
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
    # A RUN STRADDLING TWO INSTRUMENTS BLOCKS, in --check and in the listing alike. It is not
    # a third corpus; it is a directory whose records disagree about what was administered,
    # and every floor and contrast that globs it averages two instruments into one number.
    # Checked here rather than only printed above, because the listing is read by a person
    # and this has to hold when nobody is reading.
    mixed_runs = [r for r in rows if r["corpus"] == "MIXED"]
    if mixed_runs:
        print("MIXED INSTRUMENT IN ONE RUN -- %d directory(ies):" % len(mixed_runs))
        for r in mixed_runs:
            print("  %-44s %s" % (r["run"], r["instruments"]))
        print("")
        print("  Records in one directory carry different instruments. A side-flip count")
        print("  does not convert between banks, so any figure computed over this directory")
        print("  is two instruments averaged together. Split the directory by instrument.")
        return 1

    if unread:
        print("COLLECTED AND UNREACHABLE -- records no analysis glob walks:")
        for r in sorted(unread, key=lambda x: -x["records"]):
            print("  %-44s %6d rec  role=%s" % (r["run"], r["records"], r["role"]))
        print("")
        print("  These directories exist, are accounted for, and are read by NOTHING. No")
        print("  floor, no contrast and no generated table reaches them; collection_check")
        print("  will score one only if pointed at it by name. That is money spent on data")
        print("  the paper cannot use, and it looks identical to data that is working.")
        print("")
        print("  Reachable means matched by a glob in scripts/, or named in one. Derived")
        print("  globs (%d):" % len(analysis_globs()))
        for g in analysis_globs()[:10]:
            print("    %s" % g)
        # `% CATCH_ALL` with a 5-tuple raised TypeError: "not all arguments converted".
        # This branch had therefore never run to completion -- the unreachable-records
        # report crashed instead of printing, on the one path that exists to tell you
        # money was spent on data nothing reads. Found 2026-09-20 by a new directory
        # landing in it. Same shape as LEARNINGS #44: the check was right and its
        # reporting was what failed.
        print("  The order floor also sweeps %s and filters, so a directory here is not"
              % (", ".join(CATCH_ALL),))
        print("  invisible to EVERYTHING -- its condition-A T01 sheets can still enter that")
        print("  one floor. It is invisible to the arm it was collected for.")
        print("")
        print("  Either rename the directory to match a named arm, add a glob to the reader")
        print("  that should see it, or move the records into a directory already read --")
        print("  the last is what the backend-split repairs do.")
        return 1
    if orphans:
        print("UNACCOUNTED FOR -- records, no schema, no mention:")
        for r in orphans:
            print("  %-44s %6d rec" % (r["run"], r["records"]))
        return 1
    if a.check:
        # SAY WHAT WAS CHECKED AND HOW MANY. In --check mode this printed a bare
        # "every directory accounted for" and exited 0 -- no WHAT, no HOW MANY --
        # so it read identically over 63 run directories and over none. Pointed at
        # an empty tree it passed.
        n_dirs = len(rows)
        n_records = sum(r.get("records", 0) for r in rows)
        if not n_dirs:
            print("run inventory: CHECKED NOTHING -- 0 run directories found under runs/.")
            print("This is NOT a pass. Wrong tree, wrong run root, or an empty corpus.")
            return 1
        print("run inventory: every directory accounted for -- %d directories, %d records"
              % (n_dirs, n_records))
        # SCOPE DISCLOSURE, and it is now a POSITIVE one.
        #
        # This block used to announce that run-shaped directories under `data/` were outside
        # the gate -- true while `scan()` globbed `runs/*` only, which meant the public
        # mirror's 42-directory May corpus was never inventoried. `scan()` now walks every
        # root `studypaths.run_roots()` returns, so the disclosure was left describing
        # behaviour the code no longer had: the third such stale comment found in this
        # repository on 2026-09-23, and the reason each of them survived is that a comment is
        # what a reviewer reads instead of the code.
        #
        # It says which roots were walked instead. A gate naming its own scope is the point;
        # naming the wrong one is worse than naming none.
        roots = _corpus_roots(STUDY)
        print("  roots walked: %s"
              % ", ".join(os.path.relpath(r, STUDY).replace(os.sep, "/") for r in roots))
    return 0


if __name__ == "__main__":
    sys.exit(main())
