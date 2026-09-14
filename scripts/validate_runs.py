#!/usr/bin/env python3
"""validate_runs.py — does each run directory say what it actually contains?

No API calls, no network. Compares every run's manifest.json against the files on disk
and reports the disagreements.

WHY. `run_study.py` wrote manifest.json with mode "w" at the end of a run, so a second
invocation into the same run-date replaced the first invocation's record outright.
data/2026-05-27-reversed-premise/manifest.json claims 3 models and 120 calls; the
directory holds 5 model files and 200 records. Four run directories carry no manifest
at all. Nothing checked, so nothing noticed.

The manifest is also where a run declares its `analysis_seed`, which the bootstrap
reads. A run without one silently inherits May's, which is correct for May's own runs
and wrong for anything new.

Under the anti-misuse rules an existing run's record is not quietly rewritten to match
the data. This reports; it does not repair.

    python validate_runs.py             # all runs
    python validate_runs.py <run> ...   # named runs
    python validate_runs.py --json      # machine-readable, for the self-test

Exit 0 when every run is consistent, 1 when any finding is raised.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from studypaths import LEGACY_SEED, resolve_run, run_roots  # noqa: E402

#: Runs from the May 2026 sweep. Frozen: they predate the declared-seed rule and
#: reproduce against LEGACY_SEED, which is why that default exists at all.
FROZEN_PREFIX = "2026-05-"


def count_records(d: Path) -> tuple[int, int, str]:
    """(model files, records, layout) -- finding records WHEREVER this run keeps them.

    This read `raw/` only and returned (0, 0) for anything else, so every run in the
    flat collector layout was reported as "0 model file(s), 0 record(s) on disk".
    `runs/2026-09-05-wave` holds 124 files. Reporting a layout it cannot read as an
    empty run is the same defect this validator exists to catch, pointed inward: a
    check that examined nothing and printed a number as though it had.

    Layouts, in the order tried:
      "raw"    raw/*.jsonl                     -- the manifest collector
      "flat"   *.jsonl at the top level        -- the Aug-Sep barometer collector
      "nested" */*.jsonl one level down        -- calibration/<model>/<model>__C.jsonl
      "none"   no records anywhere
    """
    for layout, paths in (
        ("raw", sorted((d / "raw").glob("*.jsonl")) if (d / "raw").is_dir() else []),
        ("flat", sorted(d.glob("*.jsonl"))),
        ("nested", sorted(d.glob("*/*.jsonl"))),
    ):
        if not paths:
            continue
        n = 0
        for f in paths:
            try:
                with f.open(encoding="utf-8", errors="replace") as fh:
                    n += sum(1 for line in fh if line.strip())
            except OSError:
                continue
        return len(paths), n, layout
    return 0, 0, "none"


def inspect(d: Path) -> dict:
    out = {"run": d.name, "findings": []}
    files, records, layout = count_records(d)
    out["model_files"] = files
    out["records"] = records
    out["layout"] = layout
    out["scored"] = (d / "scored").is_dir()

    mf = d / "manifest.json"
    if not mf.is_file():
        # A MISSING manifest is only a defect where a manifest was ever written.
        # The flat and nested collector layouts never had one, and the root-level
        # skip that used to spare them broke the moment `runs/` became MIXED --
        # run_study.py started writing manifests there, the root became "covered",
        # and 30 flat runs were reported as defects on a discipline they predate.
        # Classification is per directory now, because a root is not a layout.
        if not _is_manifest_layout(d):
            out["findings"].append({
                "code": "not-manifest-layout",
                "severity": "unvalidated",
                "detail": (f"{layout} collector layout: {files} file(s), {records} record(s). "
                           "No manifest discipline exists for this layout, so this run is "
                           "NOT VALIDATED rather than clean."),
            })
            return out
        out["findings"].append({
            "code": "no-manifest",
            "detail": f"no manifest.json; {files} model file(s), {records} record(s) on disk",
        })
        return out
    try:
        m = json.loads(mf.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        out["findings"].append({"code": "unreadable-manifest", "detail": str(e)})
        return out

    attempted = m.get("models_attempted") or []
    completed = m.get("models_completed") or []
    claimed_models = max(len(attempted), len(completed))
    if claimed_models and files and claimed_models != files:
        out["findings"].append({
            "code": "model-count-mismatch",
            "detail": f"manifest names {claimed_models} model(s); raw/ holds {files} file(s)",
        })

    claimed_calls = m.get("calls_completed")
    if isinstance(claimed_calls, int) and records and claimed_calls != records:
        out["findings"].append({
            "code": "call-count-mismatch",
            "detail": f"manifest claims {claimed_calls} completed call(s); "
                      f"raw/ holds {records} record(s)",
        })

    # The May 2026 runs predate the declared-seed rule and correctly inherit the frozen
    # LEGACY_SEED, so their silence is policy rather than a defect. Flagging them would
    # bury the two real findings under twelve expected ones, and a report that always
    # says FLAG is a report nobody reads.
    if "analysis_seed" not in m and not d.name.startswith(FROZEN_PREFIX):
        out["findings"].append({
            "code": "no-analysis-seed",
            "detail": f"no analysis_seed declared, and this is not a frozen "
                      f"{FROZEN_PREFIX}* run, so it would silently inherit {LEGACY_SEED}. "
                      f"run_study.py writes the seed at run start; this run predates that "
                      f"or was produced another way.",
        })
    return out


#: Findings that are established facts about the MAY 2026 collection, each with the reason it
#: is not a defect in the shipped data. Everything else still fails.
#:
#: Why this registry exists: on a clean clone `validate_runs.py` exited 1 on the published
#: corpus, and a red gate on the data is indistinguishable, to a reader, from broken data. All
#: six findings are provenance gaps in runs collected in May 2026, before the manifest
#: discipline existed. None of them affects a number: every published figure recomputes from
#: the records on disk, which are intact and are what `--json` reports.
#:
#: What was deliberately NOT done: writing the four missing manifests from the data. A manifest
#: generated out of the files it exists to check cannot detect a shortfall, which is the only
#: thing a manifest is for. Fabricating provenance to turn a gate green is the move this study
#: spends its length criticising.
KNOWN = {
    ("2026-05-27-abliteration", "no-manifest"):
        "May 2026, before run_study.py wrote manifests. 10 model files, 160 records, all "
        "scored and all readable; the collection is intact, its request record is not.",
    ("2026-05-27-abliteration-controls", "no-manifest"):
        "Same collection, same missing manifest discipline. 3 files, 60 records.",
    ("2026-05-27-abliteration-gemma2", "no-manifest"):
        "Same collection, same missing manifest discipline. 2 files, 40 records.",
    ("2026-05-27-g0dm0d3", "no-manifest"):
        "Same collection, same missing manifest discipline. 6 files, 60 records.",
    ("2026-05-27-reversed-premise", "model-count-mismatch"):
        "The manifest names 3 models; 5 are on disk. The arm was extended after the manifest "
        "was written and the manifest was not re-emitted. The extra two models are real "
        "collected data, not phantom files -- MORE landed than was recorded, which is the "
        "harmless direction, but it is still a provenance gap and is recorded as one.",
    ("2026-05-27-reversed-premise", "call-count-mismatch"):
        "Same cause: manifest claims 120 completed calls against 200 records on disk.",
}


def _split_known(reports):
    """Partition each report's findings into (known, live). Also returns stale registry keys."""
    seen = set()
    for r in reports:
        known, live = [], []
        for f in r["findings"]:
            key = (r["run"], f["code"])
            if key in KNOWN:
                seen.add(key)
                known.append((f, KNOWN[key]))
            else:
                live.append(f)
        r["_known"], r["_live"] = known, live
    # ROT IS ONLY CLAIMABLE FOR RUNS THAT WERE ACTUALLY SCANNED. "Listed as known and no
    # longer occurs" is a statement about a run we looked at and did not find the finding in.
    # Comparing against the whole registry instead made every scoped invocation -- an explicit
    # run name, or a fixture corpus under STUDY_ROOT -- report the entire registry as rotted,
    # because it had not examined those runs at all. Absence of evidence was being reported as
    # evidence of repair, in the one file whose job is to notice the difference.
    scanned = {r["run"] for r in reports}
    return sorted(k for k in set(KNOWN) - seen if k[0] in scanned)


def _is_manifest_layout(d) -> bool:
    """Does this run dir use the manifest+scored layout this validator checks?"""
    return ((d / "manifest.json").is_file() or (d / "scored").is_dir() or (d / "raw").is_dir())


def main(argv: list[str]) -> int:
    as_json = "--json" in argv
    skipped = []
    not_runs = []
    names = [a for a in argv if not a.startswith("-")]
    # EVERY corpus root, not one. This validator's job is "are all runs well-formed", and the
    # mirror holds two populated corpora (May under data/, Aug-Sep under runs/). Asking
    # runs_root() for a single root made it raise on the ambiguity and validate nothing.
    roots = run_roots()
    if names:
        dirs = [resolve_run(n, require_scored=False) for n in names]
    else:
        dirs = sorted((d for r in roots for d in r.iterdir()
                       if d.is_dir() and not d.name.startswith("_")),
                      key=lambda d: d.name)
        # ONLY roots that use the manifest discipline this validator checks. The
        # August-September corpus under runs/ stores flat `model__CONDITION.jsonl` files and
        # has no manifests at all, so scanning it answers "no manifest" for all 30 of its runs
        # -- a layout mismatch, not 30 defects, and it would bury the six real known findings.
        # A whole root is in or out; individual dirs are not filtered, because a MISSING
        # manifest inside the manifest corpus is exactly the defect KNOWN enumerates.
        covered = [r for r in roots if any(r.glob("*/manifest.json"))]
        skipped[:] = [r for r in roots if r not in covered]
        dirs = [d for d in dirs if d.parent in covered]
        # A directory holding no records ANYWHERE is not a run. data/2026-05-27 and
        # data/2026-08-28 are cross-method OUTPUT directories -- four derived JSON files and
        # an empty raw/ -- and were reported as two runs missing their manifests. That is a
        # misclassification, not a defect, and it is fixed here rather than waved through by
        # adding the pair to KNOWN, which would have taught the gate to ignore a real shape.
        # A run whose collection genuinely failed still has raw/ or scored/ jsonl and still flags.
        not_runs[:] = [d for d in dirs if not any(d.rglob("*.jsonl"))]
        dirs = [d for d in dirs if any(d.rglob("*.jsonl"))]

    reports = []
    for d in dirs:
        if not d.is_dir():
            reports.append({"run": d.name, "model_files": 0, "records": 0, "scored": False,
                            "findings": [{"code": "missing", "detail": "no such run directory"}]})
            continue
        reports.append(inspect(d))

    stale = _split_known(reports)
    if not_runs and not as_json:
        print("not run directories (no records at all, derived output only): %s"
              % ", ".join(sorted(d.name for d in not_runs)))
    if skipped and not as_json:
        print("NOT COVERED: %s/ uses the flat collector layout and carries no manifests, so "
              "no manifest validation exists for that corpus at all."
              % ", ".join(sorted(r.name for r in skipped)))

    if as_json:
        print(json.dumps(reports, indent=1))
    else:
        live_total = known_total = 0
        unvalidated = []
        for r in reports:
            head = (f"{r['run']:<34} files={r['model_files']:>2} records={r['records']:>5} "
                    f"scored={'y' if r['scored'] else 'n'}")
            if not r["findings"]:
                print(f"  ok   {head}")
                continue
            # An unvalidated layout is not a defect and not a pass. Counting it as
            # either is how 38 layout mismatches buried 5 real findings.
            if all(f.get("severity") == "unvalidated" for f in r["findings"]):
                unvalidated.append(r)
                print(f"  --   {head}   [{r.get('layout')} layout, not validated]")
                continue
            print(f"  {'FLAG' if r['_live'] else 'known'}  {head}")
            for f in r["_live"]:
                print(f"         {f['code']}: {f['detail']}")
                live_total += 1
            for f, why in r["_known"]:
                print(f"         [known] {f['code']}: {f['detail']}")
                print(f"                 {why}")
                known_total += 1
        print(f"\n{live_total} live finding(s) and {known_total} known one(s) "
              f"across {len(reports)} run(s)")
        if unvalidated:
            recs = sum(r["records"] for r in unvalidated)
            print(f"{len(unvalidated)} run(s) holding {recs} record(s) use a collector layout "
                  f"with NO manifest discipline, so they are NOT VALIDATED -- not clean. "
                  f"Building manifests for them is the only way this number goes down.")
        if known_total:
            print("Known findings are enumerated in validate_runs.KNOWN with the reason each "
                  "is not a defect in the data.")

    # A registry entry whose finding has stopped occurring is a lie the next reader inherits,
    # so its disappearance FAILS rather than passing quietly. Same shape as the NOT_IN_REPO
    # rot check in check_skill_docs.py, and for the same reason: a whitelist nobody re-checks
    # is how a real defect gets waved through later.
    if stale:
        print("\nREGISTRY ROT -- these are listed as known and no longer occur:")
        for run, code in stale:
            print(f"   {run}: {code}")
        print("Remove them from validate_runs.KNOWN. A stale exemption hides the next defect.")
        return 1

    return 1 if any(r["_live"] for r in reports) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
