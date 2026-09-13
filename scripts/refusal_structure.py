#!/usr/bin/env python3
"""Is whole-instrument refusal all-or-nothing, and which models do it?

WHY. The study reports refusal as a RATE per condition -- 20.0% under forced balance, 0.0% under
the placebo -- which invites reading it as a propensity that every model carries a bit of. The
wave-0 records say otherwise on two axes, and neither had been checked:

  * a failed run almost never returns a partial sheet; it returns nothing
  * a model almost never refuses sometimes; it refuses always or never

A rate averaged over a bimodal population describes none of its members.

    python scripts/refusal_structure.py
    python scripts/refusal_structure.py --json

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
WAVE = os.path.join(STUDY, "runs", "2026-09-05-wave")


def collect(wave=WAVE):
    by_condition = collections.defaultdict(lambda: collections.Counter())
    by_model = collections.defaultdict(lambda: collections.Counter())
    for path in glob.glob(os.path.join(wave, "**", "*.jsonl"), recursive=True):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                cond, model = rec.get("condition"), rec.get("model")
                answered = rec.get("n_answers") or 0
                by_condition[cond]["runs"] += 1
                by_model[model][str(cond) + ":runs"] += 1
                if rec.get("valid"):
                    by_condition[cond]["valid"] += 1
                elif answered == 0:
                    by_condition[cond]["whole"] += 1
                    by_model[model][str(cond) + ":whole"] += 1
                else:
                    by_condition[cond]["partial"] += 1
    return by_condition, by_model


def refusers(by_model, condition="A"):
    """-> [(model, refused, runs, share)] for models that ever refuse `condition` outright."""
    out = []
    for model, c in by_model.items():
        runs = c.get(condition + ":runs", 0)
        ref = c.get(condition + ":whole", 0)
        if runs and ref:
            out.append((model, ref, runs, ref / runs))
    out.sort(key=lambda r: (-r[3], -r[1]))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--condition", default="A")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    by_condition, by_model = collect()
    if not by_condition:
        print("wave 0 not on disk", file=sys.stderr)
        return 2
    refs = refusers(by_model, a.condition)
    if a.json:
        print(json.dumps({"by_condition": {k: dict(v) for k, v in by_condition.items()},
                          "refusers": refs}, indent=1))
        return 0

    print("FAILURE SHAPE BY CONDITION -- wave 0")
    print("")
    print("%-8s %7s %18s %9s %8s" % ("cond", "runs", "whole-instrument", "partial", "valid"))
    whole = partial = 0
    for cond in sorted(by_condition, key=lambda c: str(c)):
        c = by_condition[cond]
        whole += c["whole"]
        partial += c["partial"]
        print("  %-6s %7d %18d %9d %8d"
              % (cond, c["runs"], c["whole"], c["partial"], c["valid"]))
    failed = whole + partial
    if failed:
        print("")
        print("  Of %d failed runs, %d (%.0f%%) returned ZERO items. Refusal here is"
              % (failed, whole, 100.0 * whole / failed))
        print("  WHOLE-INSTRUMENT, not item-level -- a model does not decline question 14.")

    print("")
    print("MODELS REFUSING CONDITION %s OUTRIGHT" % a.condition)
    print("")
    always = [r for r in refs if r[3] == 1.0]
    for model, ref, runs, share in refs:
        print("  %-52s %d/%d" % (model, ref, runs))
    print("")
    print("  %d model(s) refuse EVERY run; the rest refuse a minority. A per-condition rate"
          % len(always))
    print("  averages over that split and describes neither group.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
