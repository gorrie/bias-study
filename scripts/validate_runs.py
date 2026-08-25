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

    if as_json:
        print(json.dumps(reports, indent=1))
    else:
        total = 0
        for r in reports:
            head = (f"{r['run']:<34} files={r['model_files']:>2} records={r['records']:>5} "
                    f"scored={'y' if r['scored'] else 'n'}")
            if not r["findings"]:
                print(f"  ok   {head}")
                continue
            print(f"  FLAG {head}")
            for f in r["findings"]:
                print(f"         {f['code']}: {f['detail']}")
                total += 1
        print(f"\n{total} finding(s) across {len(reports)} run(s)")
    return 1 if any(r["findings"] for r in reports) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
