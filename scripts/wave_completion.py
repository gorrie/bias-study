#!/usr/bin/env python3
"""Collect the wave's short cells: PREREG-2026-09-25-wave-completion.md.

Three sets of wave cells came back short and the paper disclosed each: glm-5.2's B, C, E and
clause-factorial cells, gemini-3.8-flash's second and third factorial orders, and one local
build's B and C. This drives `run_battery.py` over exactly the cells the pre-registration
fixes, into `runs/2026-09-25-wave-completion/`, never into the frozen wave.

    python scripts/wave_completion.py --plan      # the cells, nothing called
    python scripts/wave_completion.py --smoke     # one sheet per model into probes/, then stop
    python scripts/wave_completion.py --run       # the arm; resumes cell by cell

The manifest is written before the first call and never rewritten. `run_battery.py` resumes a
cell by the seeds already on disk, so an interrupted run is re-issued, not duplicated.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
RUN = "2026-09-25-wave-completion"
OUT = os.path.join(STUDY, "runs", RUN)
SMOKE = os.path.join(STUDY, "probes", RUN + "-smoke")
FACTORIAL = ["F000", "F001", "F010", "F011", "F100", "F101", "F110", "F111"]

#: The design, reproduced from the pre-registration's table. Each entry is one cell family:
#: model, channel, pin, conditions, shuffle seeds, protocol v2 or not, the seed base.
DESIGN = [
    {"model": "z-ai/glm-5.2", "channel": "openrouter", "provider": "Z.AI",
     "conditions": ["B", "C", "E"] + FACTORIAL, "orders": [11], "renumber": False,
     "seed": 20260926},
    {"model": "google/gemini-3.8-flash", "channel": "openrouter", "provider": "Google",
     "conditions": FACTORIAL, "orders": [22, 33], "renumber": True, "seed": 20260953},
    {"model": "hf.co/culturerevolt/gemma-4-12b-heretic-abliterated-GGUF:Q4_K_M",
     "channel": "ollama", "provider": None,
     "conditions": ["B", "C"], "orders": [11], "renumber": False, "seed": 20260926},
]
RUNS, TEMPERATURE, MAX_TOKENS, TEMPLATE = 5, 0.7, 40960, "T01"


def cells():
    for d in DESIGN:
        for order in d["orders"]:
            for cond in d["conditions"]:
                yield d, order, cond


def argv_for(d, order, cond, out, runs):
    a = [sys.executable, os.path.join(HERE, "run_battery.py"),
         "--model", d["model"], "--channel", d["channel"], "--condition", cond,
         "--runs", str(runs), "--temperature", str(TEMPERATURE), "--seed", str(d["seed"]),
         "--seed-sweep", "--max-tokens", str(MAX_TOKENS), "--template", TEMPLATE,
         "--shuffle-seed", str(order), "--out", out]
    if d["provider"]:
        a += ["--provider", d["provider"]]
    if d["renumber"]:
        a.append("--renumber")
    if d["channel"] == "ollama":
        a.append("--no-think")
    return a


def write_manifest():
    path = os.path.join(OUT, "manifest.json")
    if os.path.exists(path):
        return
    os.makedirs(OUT, exist_ok=True)
    man = {
        "_note": "Written BEFORE the first call, from this collector's DESIGN, which reproduces "
                 "PREREG-2026-09-25-wave-completion.md. Not rewritten after collection.",
        "run": RUN, "prereg": "PREREG-2026-09-25-wave-completion.md",
        "collector": "scripts/wave_completion.py --run (driving scripts/run_battery.py)",
        "schema": "battery-run/1", "instrument": "ratchet-battery",
        "models": [d["model"] for d in DESIGN],
        "cells": [{"model": d["model"], "channel": d["channel"], "provider_pinned": d["provider"],
                   "conditions": d["conditions"], "shuffle_seeds": d["orders"],
                   "renumbered": d["renumber"], "seed_base": d["seed"]} for d in DESIGN],
        "runs_per_cell": RUNS, "seeds_note": "--seed-sweep: run k of a cell carries seed_base + k",
        "temperature": TEMPERATURE, "max_tokens": MAX_TOKENS, "template": TEMPLATE,
        "planned_sheets": sum(RUNS for _ in cells()),
        "analysis": "scripts/refusal_table.py --factorial; the factorial floor calibration",
        "analysis_seed": 20260925,
        "panel": "OUT_OF_PANEL: the wave is frozen as the refusal panel; nothing here enters it",
    }
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(man, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("wrote %s" % path)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--plan", action="store_true")
    g.add_argument("--smoke", action="store_true")
    g.add_argument("--run", action="store_true")
    g.add_argument("--report", action="store_true",
                   help="per cell: sheets, refusals and valid sheets, classified by "
                        "refusal_table.classify")
    a = ap.parse_args(argv)

    if a.report:
        sys.path.insert(0, HERE)
        from refusal_table import classify       # noqa: PLC0415 -- the one failure rule
        print("WAVE COMPLETION -- %s" % RUN)
        print("%-58s %-5s %5s %6s %8s %6s" % ("model", "cell", "order", "sheets", "refused",
                                               "valid"))
        missing = 0
        for d, order, cond in cells():
            recs = []
            path = os.path.join(OUT, "%s__%s.jsonl" % (d["model"].replace("/", "__")
                                                        .replace(":", "_"), cond))
            if os.path.exists(path):
                recs = [json.loads(l) for l in io.open(path, encoding="utf-8") if l.strip()]
            recs = [r for r in recs if r.get("shuffle_seed") == order]
            missing += RUNS - len(recs)
            print("%-58s %-5s %5d %6d %8d %6d" % (
                d["model"][:58], cond, order, len(recs),
                sum(1 for r in recs if classify(r) == "refused"),
                sum(1 for r in recs if r.get("valid"))))
        print("sheets short of the design: %d" % missing)
        return 1 if missing else 0

    if a.plan:
        for d, order, cond in cells():
            print("%-66s %-5s order %-2d %s" % (d["model"], cond, order,
                                                "v2" if d["renumber"] else "v1"))
        print("%d cells, %d sheets" % (sum(1 for _ in cells()), sum(RUNS for _ in cells())))
        return 0
    if a.smoke:
        # One sheet per model family, first cell of each, into probes/ -- never into the arm.
        rc = 0
        for d in DESIGN:
            r = subprocess.run(argv_for(d, d["orders"][0], d["conditions"][0], SMOKE, 1))
            rc = rc or r.returncode
        return rc
    write_manifest()
    failed = 0
    for d, order, cond in cells():
        r = subprocess.run(argv_for(d, order, cond, OUT, RUNS))
        if r.returncode != 0:
            failed += 1
            # run_battery exits 1 when a cell holds INVALID sheets -- refusals included, and in
            # this arm refusals are the measurement. Reported, not treated as a failure.
            print("cell has invalid sheets (rc=%d): %s %s order %d" % (r.returncode, d["model"], cond, order),
                  flush=True)
    print("done: %d cell(s) hold invalid sheets (refusals count here)" % failed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
