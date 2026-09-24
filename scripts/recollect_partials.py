#!/usr/bin/env python3
"""Re-collect, renumbered, every wave cell that lost a sheet to silent item omission.

PREREG-2026-09-24-partials-renumbered.md governs this and was committed before the first call.
Read it rather than this docstring for the question and the decision rule.

WHAT THIS BUYS, IN ONE PARAGRAPH
--------------------------------
The main wave dropped 104 partial sheets whole, all at the as-is numbering, and the paper
could only say that whether any floor moves "cannot be established from this corpus". This
re-issues every record of every affected (model, condition) cell with one change,
`--renumber`, so `partials_sensitivity.py` can recompute the floors with those cells swapped
and answer it.

THE ONE RULE THAT MATTERS HERE: NO TOP-UP
-----------------------------------------
`run_battery`'s resume counts VALID sheets in a cell and collects the shortfall. For this arm
that is the bias under measurement: a group resumed after a partial sheet would re-draw until
the sheet came back whole, and the cell would be conditioned on compliance exactly as the wave
was. So every group is collected in ONE invocation, and a group with any record already on disk
is skipped and reported, never resumed. A sheet lost to transport is a declared loss.

    python scripts/recollect_partials.py --plan                    # the groups, no calls
    python scripts/recollect_partials.py --run --channel ollama    # local builds, $0
    python scripts/recollect_partials.py --run --channel openrouter

Exit 0 collected (or nothing left), 1 an invocation failed, 2 nothing planned.
"""
from __future__ import annotations

import argparse
import collections
import datetime
import glob
import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import studypaths as _SP  # noqa: E402

SOURCE = "2026-09-16-ratchet-v3-wave"
RUN = "2026-09-24-partials-renumbered"
PREREG = "PREREG-2026-09-24-partials-renumbered.md"
TEMPERATURE = 0.7
TEMPLATE = "T01"
#: The protocol budget. 120 wave records carried 32768, a declared deviation (none truncated);
#: one budget per group is what lets run_battery key the group as one cell.
MAX_TOKENS = 40960


def _records(run):
    """Answer sheets only: a line counts when it carries the record schema."""
    rows = []
    for path in sorted(glob.glob(os.path.join(STUDY, "runs", run, "*.jsonl"))):
        for line in io.open(path, encoding="utf-8"):
            if line.strip():
                r = json.loads(line)
                if str(r.get("schema", "")).startswith(("battery-run", "compass-run")):
                    rows.append(r)
    return rows


def is_partial(rec):
    """Answered some but not all items. The same test the paper's count uses."""
    n = rec.get("n_answers") or 0
    return bool(rec.get("ok")) and 0 < n < rec.get("n_items", 32)


def affected_cells(rows):
    return sorted({(r["model"], r["condition"]) for r in rows if is_partial(r)})


def provider_pins(rows, cells):
    """One backend per hosted model: the one that served most of its affected-cell records."""
    served = collections.defaultdict(collections.Counter)
    wanted = set(cells)
    for r in rows:
        if (r["model"], r["condition"]) in wanted and r.get("channel") == "openrouter":
            p = r.get("provider_pinned") or r.get("provider")
            if p:
                served[r["model"]][p] += 1
    return {m: c.most_common(1)[0][0] for m, c in sorted(served.items())}


def plan(rows):
    """Groups of (model, channel, condition, order): how many records, the lowest seed."""
    cells = set(affected_cells(rows))
    groups = collections.OrderedDict()
    for r in sorted(rows, key=lambda r: (r["model"], r["condition"],
                                         str(r.get("shuffle_seed")), r.get("seed") or 0)):
        if (r["model"], r["condition"]) not in cells:
            continue
        key = (r["model"], r["channel"], r["condition"], r.get("shuffle_seed"))
        g = groups.setdefault(key, {"n": 0, "seed": r.get("seed"), "partial": 0})
        g["n"] += 1
        g["partial"] += int(is_partial(r))
        if r.get("seed") is not None and (g["seed"] is None or r["seed"] < g["seed"]):
            g["seed"] = r["seed"]
    return groups


def _outdir():
    return os.path.join(STUDY, "runs", RUN)


def _started(model, condition, shuffle_seed):
    """True if ANY record for this group is on disk. A started group is never resumed."""
    for path in glob.glob(os.path.join(_outdir(), "*.jsonl")):
        for line in io.open(path, encoding="utf-8"):
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if (r.get("model") == model and r.get("condition") == condition
                    and r.get("shuffle_seed") == shuffle_seed):
                return True
    return False


def write_manifest(rows, groups, pins):
    path = os.path.join(_outdir(), "manifest.json")
    if os.path.exists(path):
        return path
    os.makedirs(_outdir(), exist_ok=True)
    cells = affected_cells(rows)
    manifest = {
        "_note": ("Written by recollect_partials.py BEFORE the first call. The cells, groups, "
                  "record counts, seeds, orders and backend pins are derived from the frozen "
                  "source run, so none of them can be chosen to suit a result."),
        "run": "runs/" + RUN,
        "source_run": "runs/" + SOURCE,
        "prereg": PREREG,
        "analysis": "scripts/partials_sensitivity.py",
        "analysis_seed": _SP.LEGACY_SEED,
        "instrument": "ratchet-battery",
        "items": "data/ratchet-battery.json",
        "protocol": "v2 (--renumber)",
        "temperature": TEMPERATURE,
        "template": TEMPLATE,
        "max_tokens": MAX_TOKENS,
        "cells": ["%s %s" % c for c in cells],
        "models": sorted({c[0] for c in cells}),
        "provider_pins": pins,
        "groups": [{"model": k[0], "channel": k[1], "condition": k[2], "shuffle_seed": k[3],
                    "runs": g["n"], "seed_base": g["seed"], "source_partials": g["partial"]}
                   for k, g in groups.items()],
        "records_planned": sum(g["n"] for g in groups.values()),
        "written_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(manifest, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    return path


def command(key, g, pins):
    model, channel, condition, shuffle_seed = key
    cmd = [sys.executable, os.path.join(HERE, "run_battery.py"),
           "--model", model, "--channel", channel, "--condition", condition,
           "--runs", str(g["n"]), "--temperature", str(TEMPERATURE),
           "--seed", str(g["seed"]), "--seed-sweep", "--template", TEMPLATE,
           "--renumber", "--max-tokens", str(MAX_TOKENS), "--out", _outdir()]
    if shuffle_seed is not None:
        cmd += ["--shuffle-seed", str(shuffle_seed)]
    if channel == "ollama":
        cmd += ["--no-think"]
    elif model in pins:
        cmd += ["--provider", pins[model]]
    return cmd


#: NOT `.jsonl`. Every enumerator in this tree globs `runs/**/*.jsonl` as answer sheets, and
#: this log was first written under that extension -- its entries reached this file's own
#: `_records()` as seedless, `ok`-less "records" on the first collection, 2026-09-24.
LOG = "collection-log.ndjson"


def _log(entry):
    with io.open(os.path.join(_outdir(), LOG), "a", encoding="utf-8",
                 newline="\n") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--plan", action="store_true", help="print the groups; make no calls")
    ap.add_argument("--run", action="store_true", help="collect every group not yet started")
    ap.add_argument("--channel", choices=("ollama", "openrouter"),
                    help="only this channel, so local and hosted can run side by side")
    args = ap.parse_args(argv)

    rows = _records(SOURCE)
    groups = plan(rows)
    if not groups:
        print("no affected cells in %s -- nothing planned" % SOURCE)
        return 2
    pins = provider_pins(rows, affected_cells(rows))
    todo = [(k, g) for k, g in groups.items() if not args.channel or k[1] == args.channel]

    cells = affected_cells(rows)
    print("%s: %d partial sheets, %d affected cells, %d groups, %d records to re-issue"
          % (SOURCE, sum(is_partial(r) for r in rows), len(cells), len(groups),
             sum(g["n"] for g in groups.values())))
    by_ch = collections.Counter()
    for k, g in groups.items():
        by_ch[k[1]] += g["n"]
    print("  by channel: %s" % ", ".join("%s %d" % kv for kv in sorted(by_ch.items())))
    print("  backend pins: %s" % (", ".join("%s=%s" % kv for kv in pins.items()) or "none"))

    if args.plan or not args.run:
        for k, g in todo:
            print("  %-52s %-10s %-5s order %-4s runs %2d  seed %s  (source partials %d)"
                  % (k[0][:52], k[1], k[2], k[3], g["n"], g["seed"], g["partial"]))
        return 0

    print("manifest: %s" % write_manifest(rows, groups, pins))
    failed = 0
    for i, (k, g) in enumerate(todo, 1):
        model, channel, condition, shuffle_seed = k
        if _started(model, condition, shuffle_seed):
            print("[%d/%d] %s %s order %s: already started -- NOT topped up"
                  % (i, len(todo), model, condition, shuffle_seed))
            continue
        cmd = command(k, g, pins)
        print("[%d/%d] %s %s order %s: %d runs" % (i, len(todo), model, condition,
                                                   shuffle_seed, g["n"]), flush=True)
        started = datetime.datetime.now(datetime.timezone.utc).isoformat()
        rc = subprocess.call(cmd, cwd=STUDY)
        _log({"model": model, "channel": channel, "condition": condition,
              "shuffle_seed": shuffle_seed, "runs": g["n"], "rc": rc, "started": started,
              "finished": datetime.datetime.now(datetime.timezone.utc).isoformat()})
        if rc != 0:
            failed += 1
            print("  run_battery exited %d -- logged, continuing" % rc)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
