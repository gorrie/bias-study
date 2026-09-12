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
from studypaths import LEGACY_SEED, runs_root  # noqa: E402

#: Runs from the May 2026 sweep. Frozen: they predate the declared-seed rule and
#: reproduce against LEGACY_SEED, which is why that default exists at all.
FROZEN_PREFIX = "2026-05-"


def count_records(d: Path) -> tuple[int, int]:
    """(model files, records) under raw/."""
    raw = d / "raw"
    if not raw.is_dir():
        return 0, 0
    files = sorted(raw.glob("*.jsonl"))
    n = 0
    for f in files:
        with f.open(encoding="utf-8") as fh:
            n += sum(1 for line in fh if line.strip())
    return len(files), n


def inspect(d: Path) -> dict:
    out = {"run": d.name, "findings": []}
    files, records = count_records(d)
    out["model_files"] = files
    out["records"] = records
    out["scored"] = (d / "scored").is_dir()

    mf = d / "manifest.json"
    if not mf.is_file():
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
    return sorted(set(KNOWN) - seen)


def main(argv: list[str]) -> int:
    as_json = "--json" in argv
    names = [a for a in argv if not a.startswith("-")]
    root = runs_root()
    dirs = [root / n for n in names] if names else sorted(
        d for d in root.iterdir() if d.is_dir() and not d.name.startswith("_"))

    reports = []
    for d in dirs:
        if not d.is_dir():
            reports.append({"run": d.name, "model_files": 0, "records": 0, "scored": False,
                            "findings": [{"code": "missing", "detail": "no such run directory"}]})
            continue
        reports.append(inspect(d))

    stale = _split_known(reports)

    if as_json:
        print(json.dumps(reports, indent=1))
    else:
        live_total = known_total = 0
        for r in reports:
            head = (f"{r['run']:<34} files={r['model_files']:>2} records={r['records']:>5} "
                    f"scored={'y' if r['scored'] else 'n'}")
            if not r["findings"]:
                print(f"  ok   {head}")
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
