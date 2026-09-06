#!/usr/bin/env python3
"""Collect a presentation-order floor UNDER THE WAVE PROTOCOL, so the paper's central
comparison stops being cross-protocol.

WHAT THIS EXISTS TO SETTLE
--------------------------
`PAPER-below-the-floor.md` §3 compares the deliberate manipulation against presentation order
and then says the comparison is unsettled. It is unsettled for a specific, fixable reason: the
two rows were collected differently.

    manipulation, one sitting   temp 0.7, swept seed, 5 runs per cell, modal vs modal
    presentation order          mixed temperatures and dates, and 23 of its 37 shuffled-order
                                cells hold exactly ONE run -- a single draw against a consensus

A single run carries a full unit of run-to-run noise (replicate p90 5) that a five-run modal
has averaged away, so the order row is inflated relative to the manipulation row by an amount
nobody has measured. Any comparison between them is an artifact of collection design until
both are collected the same way.

This collects the missing half: the same fixed panel, the same frozen parameters, the same
five swept seeds, varying ONLY the item order.

WHY CONDITION D AND NOT A
-------------------------
The existing order floor is measured under condition A -- the balance instruction -- which is
the single worst condition to measure anything on. Measured on wave 0: **A is 28.2% invalid and
D is 2.9%**. Fourteen panel models decline A outright, so an order floor collected there is
computed on whichever models happen not to refuse, which is a sample selected by the behaviour
the paper's §1 is about.

D is the condition the position series already runs on for exactly this reason. Collecting the
order floor there also makes the comparison direct: the manipulation contrast is A->D, and this
is what item order alone does *within* D.

    python scripts/order_floor_wave.py --plan
    python scripts/order_floor_wave.py --run --limit 6
    python scripts/order_floor_wave.py --report
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

from wave import WAVE_PARAMS, channel_for, load_panel  # noqa: E402

#: The item orders to collect. `None` is the canonical order, which wave 0 already holds for
#: every panel model under D -- so only the shuffled ones are collected here and the canonical
#: arm comes free. Two shuffled orders give three orders per model and three pairs each.
SHUFFLE_SEEDS = (101, 202)

CONDITION = "D"


def outdir(date=None):
    date = date or datetime.date.today().isoformat()
    return os.path.join(STUDY, "runs", "%s-wave-orders" % date)


def existing_dirs():
    return sorted(p for p in glob.glob(os.path.join(STUDY, "runs", "*-wave-orders"))
                  if os.path.isdir(p))


def collected(d):
    """(model, shuffle_seed) -> distinct seeds among VALID runs.

    Sample size is distinct seeds among valid runs -- the rule wave.py had to learn twice.
    """
    seeds = collections.defaultdict(set)
    for p in glob.glob(os.path.join(d, "*.jsonl")):
        for line in io.open(p, encoding="utf-8", errors="replace"):
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if not r.get("valid") or r.get("condition") != CONDITION:
                continue
            if r.get("seed") is not None:
                seeds[(r.get("model"), r.get("shuffle_seed"))].add(r["seed"])
    return {k: len(v) for k, v in seeds.items()}


def todo(panel, have):
    want = WAVE_PARAMS["runs"]
    return [(m, s) for m in panel["models"] for s in SHUFFLE_SEEDS
            if have.get((m, s), 0) < want]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--date", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--delay", type=float, default=1.0)
    args = ap.parse_args(argv)

    panel = load_panel()
    p = WAVE_PARAMS

    # Continue the most recent collection while it is unfinished -- a sitting, not a calendar
    # day. Same rule wave.py needed after it opened a second directory at midnight.
    if args.date:
        d = outdir(args.date)
    else:
        prior = existing_dirs()
        d = outdir()
        if prior:
            last = prior[-1]
            if todo(panel, collected(last)):
                d = last
    os.makedirs(d, exist_ok=True)

    have = collected(d)
    left = todo(panel, have)

    if args.report or (not args.run and not args.plan):
        done = len(panel["models"]) * len(SHUFFLE_SEEDS) - len(left)
        print("ORDER FLOOR UNDER THE WAVE PROTOCOL -- %s" % os.path.basename(d))
        print("  condition %s, %d shuffled order(s), %d runs each, temp %s, swept seed"
              % (CONDITION, len(SHUFFLE_SEEDS), p["runs"], p["temperature"]))
        print("  %d of %d cell(s) complete; %d to collect (%d call(s))"
              % (done, len(panel["models"]) * len(SHUFFLE_SEEDS), len(left),
                 len(left) * p["runs"]))
        print("")
        print("  The canonical order comes free: wave 0 already holds condition %s at the"
              % CONDITION)
        print("  unshuffled order for every panel model, so two shuffled orders give three")
        print("  orders per model and three pairs each.")
        return 0

    if args.plan:
        for m, s in left[:20]:
            print("  %-44s shuffle %s" % (m, s))
        return 0

    n = 0
    for (model, shuffle) in left:
        if args.limit and n >= args.limit:
            break
        cmd = [sys.executable, os.path.join(HERE, "run_compass.py"),
               "--model", model, "--condition", CONDITION,
               "--runs", str(p["runs"]), "--temperature", str(p["temperature"]),
               "--seed", str(p["seed_base"]), "--max-tokens", str(p["max_tokens"]),
               "--template", p["template"], "--channel", channel_for(model),
               "--shuffle-seed", str(shuffle),
               "--delay", str(args.delay), "--out", d]
        if p.get("seed_sweep"):
            cmd.append("--seed-sweep")
        r = subprocess.run(cmd, capture_output=True, text=True)
        tail = [l for l in (r.stdout or "").splitlines() if "runs valid" in l]
        print("  %-34s shuffle %-4s %s"
              % (model[-34:], shuffle,
                 tail[-1].split(":")[-1].strip() if tail else "(no result line)"))
        n += 1
    print("")
    print("collected %d cell(s); %d remain" % (n, len(left) - n))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
