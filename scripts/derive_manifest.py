#!/usr/bin/env python3
"""Freeze what a manifest-less run actually contains, and say what cannot be recovered.

WHY. 38 run directories holding 8,674 records were collected by tools that never wrote a
manifest, so `validate_runs.py` can report them only as NOT VALIDATED. That is honest but
terminal: nothing about them is checkable, and nothing ever becomes checkable, because the
collector that would have declared its intent is gone.

WHAT THIS IS NOT. It is not a manifest. A manifest is a declaration made BEFORE and DURING
collection -- what was planned, what was attempted, what failed -- and it is worth something
precisely because the data cannot talk back to it. Anything derived afterwards from the records
agrees with the records by construction. Writing one and calling it `manifest.json` would turn a
red gate green while verifying nothing, which is the exact failure this repository's validator
exists to catch, pointed inward. See LEARNINGS 1.

WHAT IT IS. A dated content freeze, written to `manifest.derived.json` so it can never be
mistaken for the real thing. Two parts carry real weight:

  * `files[].sha256` -- a forward-looking guarantee. From now on `--check` fails if any record
    file changes, is truncated or disappears. That is a genuine integrity property the run did
    not have a minute ago.
  * `config` -- the fields the collector WROTE INTO each record at collection time (seed,
    shuffle_seed, temperature, max_tokens, instrument, template, schema, classifier). These are
    declarations, not derivations: the collector stated what it was doing. Disagreement inside a
    run is reported rather than summarised away. Several values usually means a DESIGN AXIS
    rather than a defect -- `2026-09-05-wave` carries five seeds across five run numbers because
    that is the replicate sweep, and `2026-09-04-template-floor` carries ten templates because
    that is the floor -- so the count of distinct values is reported and left to be read against
    the run's design, never labelled a disagreement.

And one part carries no weight at all, stated so no reader mistakes it: `NOT_RECOVERABLE`. A
model that failed on every call left no file, so the attempted set is unknowable; planned call
counts, transport-layer failures and the true start time are gone with the collector.

    python scripts/derive_manifest.py            # report, write nothing
    python scripts/derive_manifest.py --write
    python scripts/derive_manifest.py --check    # exit 1 on drift or a missing freeze

No API calls. Hashing and arithmetic on records already on disk.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import studypaths  # noqa: E402
import validate_runs as V  # noqa: E402

DERIVED = "manifest.derived.json"

#: Fields the collectors wrote into records as statements of configuration.
CONFIG_FIELDS = ("seed", "shuffle_seed", "temperature", "max_tokens",
                 "instrument", "template", "schema", "classifier")

#: What no post-hoc pass can know, and why. Copied into every file written.
NOT_RECOVERABLE = {
    "models_attempted": "a model that failed on every call wrote no file, so it leaves no trace",
    "total_calls_planned": "the plan lived in the collector invocation, which was not recorded",
    "calls_failed": "transport-level failures that produced no record cannot be counted from records",
    "started_at": "only the first SUCCESSFUL call is datable; the run began some unknown time earlier",
}

#: A run still being written must not be frozen. Seconds since the newest file changed.
LIVE_WINDOW_S = 900


def _git_rev() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(HERE),
                              capture_output=True, text=True, timeout=10).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def record_paths(d: Path) -> tuple[list[Path], str]:
    """The record files and the layout name, using the validator's own layout order."""
    for layout, paths in (
        ("raw", sorted((d / "raw").glob("*.jsonl")) if (d / "raw").is_dir() else []),
        ("flat", sorted(d.glob("*.jsonl"))),
        ("nested", sorted(d.glob("*/*.jsonl"))),
        ("pairs", sorted(d.glob("*/*/*.jsonl"))),
    ):
        if paths:
            return paths, layout
    return [], "none"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def derive(d: Path) -> dict | None:
    paths, layout = record_paths(d)
    if not paths:
        return None

    files = []
    models, conditions, runnos = set(), set(), set()
    times: list[str] = []
    cfg: dict[str, collections.Counter] = {k: collections.Counter() for k in CONFIG_FIELDS}
    ok_true = ok_false = unparsable = 0
    failures: collections.Counter = collections.Counter()
    total = 0

    for p in paths:
        n = 0
        with p.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not line.strip():
                    continue
                n += 1
                total += 1
                try:
                    r = json.loads(line)
                except Exception:
                    unparsable += 1
                    continue
                if not isinstance(r, dict):
                    unparsable += 1
                    continue
                for k in CONFIG_FIELDS:
                    if k in r:
                        cfg[k][json.dumps(r[k], sort_keys=True)] += 1
                for key, sink in (("model", models), ("condition", conditions), ("run_no", runnos)):
                    if r.get(key) is not None:
                        sink.add(str(r[key]))
                if r.get("collected_at"):
                    times.append(str(r["collected_at"]))
                if "ok" in r:
                    ok_true += bool(r["ok"])
                    ok_false += not bool(r["ok"])
                if r.get("failure_mode"):
                    failures[str(r["failure_mode"])] += 1
        files.append({"path": str(p.relative_to(d)), "records": n, "sha256": sha256(p)})

    config = {}
    for k, counter in cfg.items():
        if not counter:
            continue
        vals = [json.loads(v) for v, _ in counter.most_common()]
        config[k] = {
            "values": vals if len(vals) > 1 else vals[0],
            "unanimous": len(counter) == 1,
            "distinct": len(counter),
            "records_declaring": sum(counter.values()),
        }

    out = {
        "THIS_IS_NOT_A_MANIFEST": (
            "Derived after collection from the records themselves. A real manifest declares "
            "intent BEFORE collection and can therefore disagree with the data; this cannot. "
            "Its only load-bearing parts are files[].sha256, which makes future drift "
            "detectable, and config, which the collector wrote at collection time."
        ),
        "derived_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "derived_by": f"scripts/derive_manifest.py @ {_git_rev()}",
        "run": d.name,
        "layout": layout,
        "records_total": total,
        "records_unparsable": unparsable,
        "file_count": len(files),
        "files": files,
        "models": sorted(models),
        "conditions": sorted(conditions),
        "run_numbers": sorted(runnos),
        "collected_at": ({"first": min(times), "last": max(times), "records_dated": len(times)}
                         if times else None),
        "config": config,
        "outcomes": {"ok_true": ok_true, "ok_false": ok_false,
                     "failure_modes": dict(failures.most_common())},
        "NOT_RECOVERABLE": NOT_RECOVERABLE,
    }
    return out


def is_live(d: Path, paths: list[Path]) -> bool:
    if not paths:
        return False
    newest = max(p.stat().st_mtime for p in paths)
    return (dt.datetime.now().timestamp() - newest) < LIVE_WINDOW_S


def candidates() -> list[Path]:
    """Runs the validator cannot check: no manifest discipline, but records on disk."""
    out = []
    for root in V.run_roots():
        for d in sorted(root.iterdir()):
            if not d.is_dir() or d.name.startswith("_"):
                continue
            if V._is_manifest_layout(d):
                continue
            paths, _ = record_paths(d)
            if paths:
                out.append(d)
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true", help="write manifest.derived.json")
    ap.add_argument("--check", action="store_true",
                    help="verify every freeze against disk; exit 1 on drift or absence")
    ap.add_argument("--refreeze", action="store_true",
                    help="replace an existing freeze that disagrees with the records. "
                         "Without it --write refuses, because re-freezing drifted data "
                         "erases the only record that it drifted.")
    args = ap.parse_args(argv)

    runs = candidates()
    if not runs:
        print("no manifest-less runs with records found -- nothing to freeze, and that is "
              "suspicious rather than clean; check run_roots()")
        return 1

    drift, wrote, fresh, live = [], 0, 0, []
    print(f"{len(runs)} run(s) with records and no manifest discipline\n")
    for d in runs:
        paths, layout = record_paths(d)
        if is_live(d, paths):
            live.append(d.name)
            print(f"  {d.name:38s} {layout:7s} SKIPPED -- written to within "
                  f"{LIVE_WINDOW_S}s, still collecting")
            continue
        new = derive(d)
        target = d / DERIVED
        if args.check:
            if not target.is_file():
                drift.append((d.name, "no manifest.derived.json"))
                print(f"  {d.name:38s} {layout:7s} NO FREEZE")
                continue
            old = json.loads(target.read_text(encoding="utf-8"))
            o = {f["path"]: (f["sha256"], f["records"]) for f in old.get("files", [])}
            n = {f["path"]: (f["sha256"], f["records"]) for f in new["files"]}
            bad = ([f"{k}: GONE" for k in o if k not in n]
                   + [f"{k}: NEW" for k in n if k not in o]
                   + [f"{k}: CHANGED" for k in set(o) & set(n) if o[k] != n[k]])
            if bad:
                drift.append((d.name, "; ".join(bad[:4])))
                print(f"  {d.name:38s} {layout:7s} DRIFT: {'; '.join(bad[:3])}")
            else:
                fresh += 1
                print(f"  {d.name:38s} {layout:7s} ok  {new['records_total']:5d} rec, "
                      f"{new['file_count']:3d} file(s) verified")
            continue
        varies = [f"{k}x{v['distinct']}" for k, v in new["config"].items() if not v["unanimous"]]
        note = f"  varies: {' '.join(varies)}" if varies else ""
        print(f"  {d.name:38s} {layout:7s} {new['records_total']:5d} rec, "
              f"{new['file_count']:3d} file(s), cfg={len(new['config'])}/{len(CONFIG_FIELDS)}{note}")
        if args.write:
            # THE REMEDY MUST NOT DESTROY THE EVIDENCE. `--write` overwrote any existing
            # freeze unconditionally, so the command this tool and validate_runs both print
            # as the fix -- `derive_manifest.py --write` -- would re-freeze a run whose
            # records had CHANGED and report it as a clean write. The freeze's entire purpose
            # is that a later `--check` can say a record file moved; a writer that silently
            # agrees with whatever is on disk is the vacuous pass with a hash attached.
            #
            # An existing freeze is now compared first and a disagreement REFUSES. Clearing
            # it takes `--refreeze`, which is deliberate and leaves a flag in the shell
            # history saying a freeze was replaced rather than written.
            if target.is_file() and not args.refreeze:
                old = json.loads(target.read_text(encoding="utf-8"))
                o = {f["path"]: (f["sha256"], f["records"]) for f in old.get("files", [])}
                n = {f["path"]: (f["sha256"], f["records"]) for f in new["files"]}
                bad = ([f"{k}: GONE" for k in o if k not in n]
                       + [f"{k}: NEW" for k in n if k not in o]
                       + [f"{k}: CHANGED" for k in set(o) & set(n) if o[k] != n[k]])
                if bad:
                    drift.append((d.name, "; ".join(bad[:4])))
                    print(f"  {d.name:38s} {layout:7s} REFUSED -- an existing freeze "
                          f"disagrees with the records: {'; '.join(bad[:3])}. Find out why "
                          f"the data moved; pass --refreeze only once you know.")
                    continue
            target.write_text(json.dumps(new, indent=2, sort_keys=False) + "\n", encoding="utf-8")
            wrote += 1

    if live:
        print(f"\n{len(live)} run(s) skipped as live: {', '.join(live)}")
    if args.check:
        print(f"\n{fresh} verified, {len(drift)} problem(s)")
        for name, why in drift:
            print(f"  {name}: {why}")
        if drift:
            return 1
        # A FREEZE GATE THAT VERIFIED NOTHING MUST NOT REPORT CLEAN. The liveness skip is
        # mtime-based, and mtime is not a property of the data: on 2026-09-20 the working
        # tree was re-checked-out to fix line endings, every record file got a new mtime,
        # and this gate printed "0 verified, 0 problem(s)" and exited 0 -- green, having
        # checked not one hash. A fresh `git clone` does the same thing, which means the
        # gate was weakest on exactly the tree a reader would have.
        #
        # Skipping a live run is still right; reporting the skip as a pass is not.
        if fresh == 0 and live:
            print("\nCHECKED NOTHING -- every run was skipped as live, so not one frozen "
                  "hash was compared. This is NOT a pass. mtime is not a property of the "
                  "data: a re-checkout or a fresh clone makes every run look live. Re-run "
                  f"once {LIVE_WINDOW_S}s have passed with nothing writing to runs/.")
            return 2
        return 0
    if args.write:
        print(f"\nwrote {wrote} × {DERIVED}")
        if drift:
            # A refused write is not a quiet skip. It exits 1 so a caller that chained this
            # after a failing gate does not read "wrote N" as "the problem is handled".
            print(f"{len(drift)} run(s) REFUSED -- their records disagree with a freeze "
                  f"already on disk:")
            for name, why in drift:
                print(f"  {name}: {why}")
            return 1
    else:
        print("\nreport only; pass --write to freeze, --check to verify")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
