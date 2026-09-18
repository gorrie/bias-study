#!/usr/bin/env python3
"""Extend the A->D manipulation floor, which the whole paper is measured against.

WHY THIS IS THE MOST LOAD-BEARING GAP IN THE CORPUS
---------------------------------------------------
`prompt condition A->D` is the paper's reference scale -- the deliberate political
manipulation that every nuisance floor is compared to. Section 2's argument is one sentence:
two factors nobody calls political (same-version variation, presentation order) reach past the
one that is.

Measured 2026-09-05, that reference rests on **7 model pairs**, all collected in a single
sitting on 2026-08-30, with a p90 of 14 and a 95% CI of **[2, 14]**. The error bar on the
reference is nearly as wide as the scale it anchors. Every "this crosses the manipulation line"
claim in the paper inherits it.

It was not frozen by refusal, which is what a first read of the frontier collection suggested.
`floor_conditions()` loads exactly one directory, `runs/2026-08-30-temp0/`, which holds 8
models. 19 further models in the wave panel answer condition A and have simply never been
collected at temperature 0.

WHY TEMPERATURE 0, AND WHY THAT IS NOT A FREE CHOICE
----------------------------------------------------
The manipulation floor has to isolate the CONDITION. At temperature 0.7 an A-vs-D pair carries
the condition change plus run-to-run noise, and this project measures that noise separately at
a median of 3 and p90 5 side-flips -- a third of the manipulation estimate. So the pair is
collected greedy, at the same seed, and the only thing that differs between the two arms is the
instruction. Same protocol as the 2026-08-30 collection: temperature 0.0, seed 20260830,
max_tokens 8192, 3 runs per cell.

    python scripts/extend_manipulation_floor.py --plan
    python scripts/extend_manipulation_floor.py --run [--limit N]
"""
from __future__ import annotations

import argparse
import collections
import glob
import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from wave import channel_for            # noqa: E402  one definition of the routing

#: Matches the 2026-08-30 collection exactly. A pair collected under different parameters is
#: not comparable to the seven already in the floor, and would widen the estimate with variance
#: this design exists to exclude.
PARAMS = {"temperature": "0.0", "seed": "20260830", "max_tokens": "8192", "runs": "3"}

OUT = os.path.join(STUDY, "runs", "2026-09-05-temp0-extend")
EXISTING = os.path.join(STUDY, "runs", "2026-08-30-temp0")


def answers_condition_a():
    """Panel models with at least one VALID condition-A run somewhere in the corpus.

    Coverage, not outcome: a model that refuses A cannot contribute an A->D pair no matter how
    many times it is asked, so collecting it would spend calls to record a hole we already know
    about. Models that refuse A are exactly the new Western flagships, and their absence from
    this floor is itself reported in RESULTS-2026-09-05-frontier-v3.md.
    """
    import refusal_table as R
    import key_numbers as K
    panel = set(json.load(io.open(os.path.join(STUDY, "data", "wave-panel.json"),
                                  encoding="utf-8"))["models"])
    ok = set()
    for r in R.load(K.REFUSAL_EXCLUDE):
        if r.get("condition") == "A" and r.get("model") in panel \
                and R.classify(r) == "valid":
            ok.add(r["model"])
    return ok


def already():
    """(model, condition) already collected at temperature 0, in either directory."""
    got = collections.Counter()
    for root in (EXISTING, OUT):
        for p in glob.glob(os.path.join(root, "**", "*.jsonl"), recursive=True):
            for line in io.open(p, encoding="utf-8", errors="replace"):
                if not line.strip():
                    continue
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if r.get("answers"):
                    got[(r.get("model"), r.get("condition"))] += 1
    return got


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--channel", default="", choices=["", "openrouter", "ollama"],
                    help="collect only one channel. Local GGUF builds run a 12B model over 62 "
                         "propositions three times and take an order of magnitude longer than "
                         "an API call, so they are worth a separate, longer pass rather than "
                         "blocking the hosted ones behind them.")
    ap.add_argument("--delay", type=float, default=2.0)
    args = ap.parse_args(argv)

    have = already()
    todo = [(m, c) for m in sorted(answers_condition_a()) for c in ("A", "D")
            if have.get((m, c), 0) < int(PARAMS["runs"])
            and (not args.channel or channel_for(m) == args.channel)]

    if args.plan or not args.run:
        models = sorted({m for m, _ in todo})
        pairs_now = len({m for (m, c) in have if c == "A"} &
                        {m for (m, c) in have if c == "D"})
        # COMPUTED. This line read "(p90 14, 95% CI [2, 14])" as literal text -- a hand-typed
        # statistic inside the tool whose purpose is removing hand-typed statistics, and it was
        # already wrong within the hour once the date-keying fix landed.
        import floor_table as F
        row = F.floor_conditions() or {}
        side = row.get("side") or (None, None, None)
        ci_lo, ci_hi = (row.get("side_ci") or (None, None))[:2]
        shape = ("p90 %s, 95%% CI [%s, %s]"
                 % (side[1], ci_lo, ci_hi)) if side[1] is not None else "not computable here"
        print("MANIPULATION FLOOR EXTENSION")
        print("  pairs in the floor now      : %d  (%s)" % (pairs_now, shape))
        print("  models to collect           : %d" % len(models))
        print("  cells to collect            : %d  (%s runs each)" % (len(todo), PARAMS["runs"]))
        print("  protocol                    : %s"
              % ", ".join("%s=%s" % kv for kv in sorted(PARAMS.items())))
        print("")
        print("  Models that REFUSE condition A are excluded on purpose: they cannot")
        print("  contribute a pair, and their absence is the finding, not a collection gap.")
        return 0

    n = 0
    for (model, cond) in todo:
        if args.limit and n >= args.limit:
            break
        cmd = [sys.executable, os.path.join(HERE, "run_battery.py"),
               "--model", model, "--condition", cond,
               "--runs", PARAMS["runs"], "--temperature", PARAMS["temperature"],
               "--seed", PARAMS["seed"], "--max-tokens", PARAMS["max_tokens"],
               "--channel", channel_for(model), "--delay", str(args.delay), "--out", OUT]
        r = subprocess.run(cmd, capture_output=True, text=True)
        line = [l for l in (r.stdout or "").splitlines() if "runs valid" in l]
        got = line[-1].split(":")[-1].strip() if line else "(no result)"
        print("  %-38s %s  %s" % (model[-38:], cond, got.split("->")[0].strip()))
        n += 1
    print("")
    print("collected %d cell(s); %d remain" % (n, len(todo) - n))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
