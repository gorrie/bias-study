#!/usr/bin/env python3
"""Do the wave's dropped partial sheets move any floor? The pre-registered test.

PREREG-2026-09-24-partials-renumbered.md governs this. The decision rule, verbatim in effect:
a floor row MOVES if its side-flip p90, recomputed with the 34 affected wave cells replaced by
their renumbered re-collection, falls outside the 95% CI the published row prints.

NOTHING HERE COMPUTES A FLOOR. The unmodified `floor_table.py --markdown` is run twice:

  1. in the study tree, as it is -- the published floors, and
  2. in a scratch copy of `scripts/`, `data/` and `runs/` in which every record of every
     affected (model, condition) cell of the wave is replaced by this arm's records for the
     same cell, and the arm's own directory is removed. Nothing else differs.

So any difference between the two tables is the substitution and only the substitution, and a
change to how a floor is computed reaches both sides at once. The rules for what a partial
sheet is, where a cell's sheets live and the exact test are imported from the one place each
is defined (`recollect_partials.is_partial`, `run_battery.sheet_path`,
`omission_arms.fisher_one_sided`).

    python scripts/partials_sensitivity.py            # compute and print; writes nothing
    python scripts/partials_sensitivity.py --markdown # the comparison table only
    python scripts/partials_sensitivity.py --check    # recompute; exit 1 if the cache drifted
    python scripts/partials_sensitivity.py --write    # rebuild the cache (operator only)

Read-only by default: a reader reproducing §6b must not come away with a dirty tree.

The cache is `data/partials-sensitivity.json`, provenance-carrying like
`data/placebo-control.json`, so `key_numbers` can gate its figures without a rerun.
Reads only, apart from that one file. No API calls.
"""
from __future__ import annotations

import argparse
import datetime
import glob
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import recollect_partials as RP  # noqa: E402
from omission_arms import fisher_one_sided  # noqa: E402
from run_battery import sheet_path  # noqa: E402

CACHE = os.path.join(STUDY, "data", "partials-sensitivity.json")
ROW = re.compile(r"^\|\s*(?P<factor>[^|]+?)\s*\|\s*(?P<n>\d+)\s*\|\s*(?P<med>\d+)\s*/\s*"
                 r"(?P<p90>\d+)\s*/\s*(?P<max>\d+)\s*\|\s*(?P<ci>[^|]+?)\s*\|\s*"
                 r"(?P<end>[^|]+?)\s*\|\s*$")


def parse_floor_markdown(text):
    """`floor_table --markdown` rows, keyed by factor. The CI is None for a non-pair arm."""
    rows = {}
    for line in text.splitlines():
        m = ROW.match(line.strip())
        if not m:
            continue
        ci = re.match(r"\[(\d+),\s*(\d+)\]", m.group("ci"))
        rows[m.group("factor")] = {
            "n_pairs": int(m.group("n")), "median": int(m.group("med")),
            "p90": int(m.group("p90")), "max": int(m.group("max")),
            "ci": [int(ci.group(1)), int(ci.group(2))] if ci else None,
            "endpoint": m.group("end"),
        }
    return rows


def floor_markdown(tree):
    out = subprocess.run([sys.executable, os.path.join(tree, "scripts", "floor_table.py"),
                          "--markdown"], cwd=tree, capture_output=True, text=True,
                         encoding="utf-8")
    if out.returncode != 0:
        raise SystemExit("floor_table failed in %s:\n%s" % (tree, out.stderr[-2000:]))
    return out.stdout


def _read(path):
    rows = []
    if os.path.exists(path):
        for line in io.open(path, encoding="utf-8"):
            if line.strip():
                rows.append(json.loads(line))
    return rows


def substituted_tree(workdir, cells, arm=None):
    """A copy of the tree with each affected wave cell's records replaced by the arm's.

    `arm` defaults to this arm's directory. The self-test passes the wave itself, which must
    reproduce the published table byte for byte -- the proof that the copy-and-substitute
    harness moves nothing on its own.
    """
    tree = os.path.join(workdir, "tree")
    for sub in ("scripts", "data", "runs"):
        shutil.copytree(os.path.join(STUDY, sub), os.path.join(tree, sub),
                        ignore=shutil.ignore_patterns("__pycache__"))
    shutil.rmtree(os.path.join(tree, "runs", RP.RUN), ignore_errors=True)
    wave = os.path.join(tree, "runs", RP.SOURCE)
    arm = arm or os.path.join(STUDY, "runs", RP.RUN)
    replaced = removed = 0
    for model, condition in cells:
        path = str(sheet_path(wave, model, condition))
        kept = [r for r in _read(path)
                if not (r.get("model") == model and r.get("condition") == condition)]
        removed += len(_read(path)) - len(kept)
        new = [r for r in _read(str(sheet_path(arm, model, condition)))
               if r.get("model") == model and r.get("condition") == condition]
        replaced += len(new)
        with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
            for r in kept + new:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return tree, removed, replaced


def partial_counts(rows):
    ok = [r for r in rows if r.get("ok")]
    return sum(RP.is_partial(r) for r in ok), len(ok), len(rows) - len(ok)


def compute():
    wave_rows = RP._records(RP.SOURCE)
    cells = RP.affected_cells(wave_rows)
    arm_rows = RP._records(RP.RUN)
    planned = sum(g["n"] for g in RP.plan(wave_rows).values())
    if not arm_rows:
        raise SystemExit("runs/%s holds no records -- nothing to compare. This refuses rather "
                         "than reporting 'no row moves' over an empty arm." % RP.RUN)
    wanted = set(cells)
    in_cells = [r for r in wave_rows if (r["model"], r["condition"]) in wanted]

    published = parse_floor_markdown(floor_markdown(STUDY))
    work = tempfile.mkdtemp(prefix="partials-sens-")
    try:
        tree, removed, replaced = substituted_tree(work, cells)
        substituted = parse_floor_markdown(floor_markdown(tree))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    if not published or not substituted:
        raise SystemExit("floor_table printed no parseable rows -- refusing a vacuous result")

    rows, moved, new = [], [], []
    for factor in list(published) + [f for f in substituted if f not in published]:
        a, b = published.get(factor), substituted.get(factor)
        verdict = "absent after substitution"
        if a is None:
            verdict = "new row"
            new.append(factor)
        elif b is not None:
            if a["ci"] is None:
                verdict = "not a pair arm"
            elif a["ci"][0] <= b["p90"] <= a["ci"][1]:
                verdict = "within CI"
            else:
                verdict = "MOVES"
                moved.append(factor)
        rows.append({"factor": factor, "published": a, "substituted": b, "verdict": verdict})

    asis_p, asis_n, asis_lost = partial_counts(in_cells)
    renum_p, renum_n, renum_lost = partial_counts(arm_rows)
    import position_analysis as _PA
    computed_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "_note": ("Cache of partials_sensitivity.py. PREREG-2026-09-24-partials-renumbered.md "
                  "states the rule; do not hand-edit -- run --check."),
        # The contract key_numbers._slow_cache enforces: the run read, and how many analysable
        # records it held, so a cache computed on a different corpus refuses to be quoted.
        "provenance": {"run": RP.RUN, "source_run": RP.SOURCE, "computed_at": computed_at,
                       "n_records_read": len(_PA.load_records(
                           os.path.join(STUDY, "runs", RP.RUN)))},
        "run": RP.RUN, "source_run": RP.SOURCE, "prereg": RP.PREREG,
        "computed_at": computed_at,
        "cells": len(cells), "records_planned": planned,
        "arm_records": len(arm_rows), "wave_records_removed": removed,
        "arm_records_substituted": replaced,
        "partials": {
            "asis": {"partial": asis_p, "answered": asis_n, "transport": asis_lost},
            "renumbered": {"partial": renum_p, "answered": renum_n, "transport": renum_lost},
            "fisher_one_sided_p": fisher_one_sided(asis_p, asis_n - asis_p,
                                                   renum_p, renum_n - renum_p),
        },
        "rows": rows, "moved": moved, "new_rows": new,
    }


def _stat(r):
    return "-" if r is None else "%d / %d / %d" % (r["median"], r["p90"], r["max"])


def markdown(res):
    out = ["| factor | pairs, published → substituted | side-flip med / p90 / max, published "
           "| substituted | published p90 CI | verdict |",
           "|---|---|---|---|---|---|"]
    for row in res["rows"]:
        a, b = row["published"], row["substituted"]
        out.append("| %s | %s → %s | %s | %s | %s | %s |" % (
            row["factor"], a["n_pairs"] if a else "-", b["n_pairs"] if b else "-",
            _stat(a), _stat(b), ("[%d, %d]" % tuple(a["ci"])) if a and a["ci"] else "-",
            "**MOVES**" if row["verdict"] == "MOVES" else row["verdict"]))
    return "\n".join(out)


def report(res):
    p = res["partials"]
    print("arm: %d of %d planned records; %d wave records replaced by %d"
          % (res["arm_records"], res["records_planned"], res["wave_records_removed"],
             res["arm_records_substituted"]))
    print("partial sheets in the %d affected cells: as-is %d of %d answered, renumbered %d of "
          "%d (one-sided Fisher p = %s); transport losses %d / %d"
          % (res["cells"], p["asis"]["partial"], p["asis"]["answered"],
             p["renumbered"]["partial"], p["renumbered"]["answered"],
             "%.3g" % p["fisher_one_sided_p"] if p["fisher_one_sided_p"] is not None else "n/a",
             p["asis"]["transport"], p["renumbered"]["transport"]))
    print()
    print(markdown(res))
    print()
    if res["moved"]:
        print("VERDICT: %d floor row(s) MOVE outside their published p90 CI: %s"
              % (len(res["moved"]), "; ".join(res["moved"])))
    else:
        print("VERDICT: no floor row moves outside its published p90 CI (%d rows compared)"
              % sum(1 for r in res["rows"] if r["verdict"] in ("within CI", "MOVES")))
    if res["new_rows"]:
        print("new rows (no published counterpart): %s" % "; ".join(res["new_rows"]))


def selftest():
    """Substitute every affected cell with ITS OWN wave records: the table must not change."""
    cells = RP.affected_cells(RP._records(RP.SOURCE))
    published = floor_markdown(STUDY)
    work = tempfile.mkdtemp(prefix="partials-selftest-")
    try:
        tree, removed, replaced = substituted_tree(
            work, cells, arm=os.path.join(STUDY, "runs", RP.SOURCE))
        again = floor_markdown(tree)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    if removed != replaced or not removed:
        print("SELFTEST FAIL: removed %d, replaced %d" % (removed, replaced))
        return 1
    if again != published:
        print("SELFTEST FAIL: identity substitution changed floor_table's output")
        return 1
    print("selftest: identity substitution of %d cells (%d records) reproduces the published "
          "floor table byte for byte" % (len(cells), removed))
    return 0


def _comparable(res):
    out = {k: v for k, v in res.items() if k != "computed_at"}
    out["provenance"] = {k: v for k, v in (res.get("provenance") or {}).items()
                         if k != "computed_at"}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--markdown", action="store_true", help="the comparison table only")
    ap.add_argument("--check", action="store_true",
                    help="recompute and exit 1 if data/partials-sensitivity.json has drifted")
    ap.add_argument("--selftest", action="store_true",
                    help="prove the harness is a no-op: identity substitution, same table")
    ap.add_argument("--write", action="store_true",
                    help="write data/partials-sensitivity.json (otherwise nothing is written)")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    res = compute()
    if args.check:
        if not os.path.exists(CACHE):
            print("no cache at %s -- run without --check first" % CACHE)
            return 1
        with io.open(CACHE, encoding="utf-8") as fh:
            cached = json.load(fh)
        if _comparable(cached) != _comparable(res):
            print("partials-sensitivity cache is STALE against runs/ -- rerun without --check")
            return 1
        print("partials-sensitivity cache matches runs/ (%d rows, %d moved)"
              % (len(res["rows"]), len(res["moved"])))
        return 0
    if args.markdown:
        print(markdown(res))
        return 0
    report(res)
    if args.write:
        with io.open(CACHE, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(res, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
        print("\ncache written: %s" % CACHE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
