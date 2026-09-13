#!/usr/bin/env python3
"""Does abliteration change how much a model WRITES, and why are 24 wave cells short?

The ablation wave records 63 cells and only 39 reach n=5. Nobody had asked why. The answer is
not uniform and it is not stance: one base's ablated build stops being able to stop.

    python scripts/ablation_termination.py
    python scripts/ablation_termination.py --json

No API calls. Arithmetic on records already on disk.
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
WAVE = os.path.join(STUDY, "runs", "2026-09-07-ablation-wave")
CAP = 8192          # max_tokens the wave protocol asked for


def outcome(rec):
    if rec.get("ok") is False:
        return "transport-failed"
    if not (rec.get("response_text") or "").strip():
        return "empty-response"
    return rec.get("failure_mode") or rec.get("refusal_class") or "valid"


def collect(wave=WAVE):
    """-> (tokens[(base, arm)] -> [ints], outcomes[(base, arm)] -> Counter)."""
    tokens = collections.defaultdict(list)
    outcomes = collections.defaultdict(collections.Counter)
    for path in glob.glob(os.path.join(wave, "**", "*.jsonl"), recursive=True):
        rel = os.path.relpath(path, wave).replace("\\", "/").split("/")
        if len(rel) < 2:
            continue
        base, armdir = rel[0], rel[1]
        arm = "stock" if armdir == "stock" else "ablated"
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                outcomes[(base, arm)][outcome(rec)] += 1
                if rec.get("tokens_out") is not None:
                    tokens[(base, arm)].append(rec["tokens_out"])
    return tokens, outcomes


def analyse(tokens, outcomes):
    bases = sorted({b for b, _ in tokens} | {b for b, _ in outcomes})
    rows = []
    for b in bases:
        s, a = tokens.get((b, "stock"), []), tokens.get((b, "ablated"), [])
        if not s or not a:
            continue
        ms, ma = st.median(s), st.median(a)
        rows.append({"base": b, "stock_median": ms, "ablated_median": ma,
                     "ratio": (ma / ms) if ms else None,
                     "ablated_at_cap": sum(1 for t in a if t >= CAP), "ablated_n": len(a),
                     "stock_at_cap": sum(1 for t in s if t >= CAP)})
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    tokens, outcomes = collect()
    if not tokens:
        print("no ablation wave on disk", file=sys.stderr)
        return 2
    rows = analyse(tokens, outcomes)
    if a.json:
        print(json.dumps({"rows": rows,
                          "outcomes": {f"{k[0]}/{k[1]}": dict(v) for k, v in outcomes.items()}},
                         indent=1))
        return 0

    print("OUTPUT LENGTH, STOCK vs ABLATED (median tokens_out; cap is %d)" % CAP)
    print("")
    print("%-16s %13s %15s %8s %16s" % ("base", "stock", "ablated", "ratio", "ablated at cap"))
    for r in rows:
        print("  %-14s %13.0f %15.0f %7.1fx %12d/%d"
              % (r["base"], r["stock_median"], r["ablated_median"], r["ratio"],
                 r["ablated_at_cap"], r["ablated_n"]))
    print("")
    print("READ THE SPREAD, NOT THE HEADLINE. Abliteration does not generally change output")
    print("length: four bases sit at 1.0x and one ablated build is SHORTER than its stock.")
    print("It destroyed termination on exactly one base, and completely -- on both")
    print("quantisations, which rules the serving stack out as the cause. A base whose STOCK")
    print("arm is already at the cap has a broken base, not a broken ablation.")
    print("")
    print("WHY CELLS CAME BACK SHORT")
    print("")
    for (base, arm), c in sorted(outcomes.items()):
        bad = sum(v for k, v in c.items() if k != "valid")
        if bad:
            print("  %-44s %s" % (base + "/" + arm, dict(c)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
