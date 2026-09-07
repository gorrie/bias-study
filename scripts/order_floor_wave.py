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


def attempted(d):
    """(model, shuffle_seed) -> how many records exist, valid or not.

    Needed because `collected()` counts only VALID runs, so a cell whose every run fails looks
    identical to a cell nobody has touched -- and the collector re-attempts it on every
    invocation, forever.
    """
    seen = collections.Counter()
    for p in glob.glob(os.path.join(d, "*.jsonl")):
        for line in io.open(p, encoding="utf-8", errors="replace"):
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("condition") == CONDITION:
                seen[(r.get("model"), r.get("shuffle_seed"))] += 1
    return seen


def todo(panel, have, tried=None):
    """Cells still worth collecting.

    A CELL THAT HAS HAD ITS RUNS AND CAME BACK SHORT IS NOT A GAP. The gemma-4-12B GGUF build
    has 13 records here and ZERO valid ones -- every run exhausted its token budget or failed
    in transport -- and `mistral:latest` returns nothing usable either. Re-running a model that
    cannot answer produces another failure at ~100 seconds a call, and on a local model that is
    seventeen minutes per restart spent proving the same thing.

    So a cell is done being asked once it has been given its full run budget, whatever came
    back. What it yielded is a property of the model and belongs in the disclosure beside the
    floor, not in a queue that never empties.
    """
    want = WAVE_PARAMS["runs"]
    tried = tried or {}
    out = []
    # THE CANONICAL ORDER IS NOT COLLECTED FOR PANEL MODELS AND MUST BE FOR OFF-PANEL ONES.
    #
    # A panel model already has its canonical-order sheet in the wave, so collecting it again
    # here would duplicate it. An OFF-PANEL model has no wave cell at all -- so without the
    # canonical arm it would have two shuffled orders and nothing to pair them against except
    # each other, which measures shuffle-against-shuffle rather than order-against-canonical
    # and is not the same quantity the floor reports.
    orders = SHUFFLE_SEEDS if not panel.get("off_panel") else (None,) + SHUFFLE_SEEDS
    for m in panel["models"]:
        for s in orders:
            if have.get((m, s), 0) >= want:
                continue
            if tried.get((m, s), 0) >= want:
                continue        # asked, and answered as well as it can
            out.append((m, s))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--date", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--delay", type=float, default=1.0)
    # A MODEL LIST OFF THE PANEL, FOR AN ARM THE PANEL CANNOT ANSWER.
    #
    # The frozen panel is the barometer's time axis and must not change -- recomputing it each
    # wave would measure cohort composition instead of change. But the panel's only LOCAL
    # 2026-generation build is gemma-4-12B, which returns empty responses, so the local side of
    # the one-sitting order floor is four models and every one of them is 2024 vintage.
    #
    # That is what makes "newer models are more order-stable" unfalsifiable on this corpus:
    # serving path, vintage and quantisation all change together across the split, and there is
    # no local 2026 model to break the tie. `--models` collects one into its own dated arm
    # WITHOUT touching the panel, so the tie-breaker exists and the time series stays comparable.
    #
    # `--out-suffix` keeps it in a separate directory for the same reason: it is a different
    # question from the panel's order floor and must not silently join that row.
    ap.add_argument("--models", default="",
                    help="comma-separated model tags to collect INSTEAD of the frozen panel "
                         "(for an off-panel arm; use with --out-suffix)")
    ap.add_argument("--out-suffix", default="",
                    help="suffix for the run directory, so an off-panel arm lands separately")
    args = ap.parse_args(argv)

    panel = load_panel()
    if args.models:
        # OFF-PANEL ARM. The frozen panel is left alone -- this replaces the roster for this
        # invocation only, and nothing is written back to data/wave-panel.json.
        panel = dict(panel)
        panel["models"] = [m.strip() for m in args.models.split(",") if m.strip()]
        panel["off_panel"] = True
        if not args.out_suffix:
            print("--models without --out-suffix would write an off-panel arm into the panel's "
                  "own directory, where floor_order_wave would read it as part of the frozen "
                  "roster. Pass --out-suffix.", file=sys.stderr)
            return 2
    p = WAVE_PARAMS

    # Continue the most recent collection while it is unfinished -- a sitting, not a calendar
    # day. Same rule wave.py needed after it opened a second directory at midnight.
    suffix = ("-" + args.out_suffix.strip("-")) if args.out_suffix else ""
    if args.date:
        d = outdir(args.date) + suffix
    elif suffix:
        # AN OFF-PANEL ARM DOES NOT SEARCH FOR A PRIOR SITTING TO CONTINUE.
        #
        # `existing_dirs()` globs `*-wave-orders`, and a suffixed directory does not end in
        # that -- which is the property that keeps this arm OUT of `floor_order_wave`, whose
        # glob is `runs/*-wave-orders/*.jsonl`. So an off-panel arm cannot silently join the
        # published order row, and it also cannot be found by a cross-day resume. Today's
        # dated directory is deterministic, so resuming within the sitting works anyway, and
        # resuming across days is exactly what the one-sitting rule forbids.
        d = outdir() + suffix
    else:
        prior = existing_dirs()
        d = outdir()
        if prior:
            last = prior[-1]
            if todo(panel, collected(last), attempted(last)):
                d = last
    os.makedirs(d, exist_ok=True)

    have = collected(d)
    tried = attempted(d)
    left = todo(panel, have, tried)

    if args.report or (not args.run and not args.plan):
        _orders = SHUFFLE_SEEDS if not panel.get("off_panel") else (None,) + SHUFFLE_SEEDS
        cells = [(m, s) for m in panel["models"] for s in _orders]
        want = p["runs"]
        done = [k for k in cells if have.get(k, 0) >= want]
        # COUNTED SEPARATELY, because "complete" and "asked and came back empty" are different
        # facts and folding them together would report a finished collection over cells that
        # yielded nothing.
        spent = [k for k in cells
                 if have.get(k, 0) < want and tried.get(k, 0) >= want]
        print("ORDER FLOOR UNDER THE WAVE PROTOCOL -- %s" % os.path.basename(d))
        print("  condition %s, %d shuffled order(s), %d runs each, temp %s, swept seed"
              % (CONDITION, len(SHUFFLE_SEEDS), p["runs"], p["temperature"]))
        print("  %d of %d cell(s) at n=%d; %d to collect (%d call(s))"
              % (len(done), len(cells), want, len(left), len(left) * want))
        if spent:
            print("  %d cell(s) had their runs and came back short -- not re-queued:"
                  % len(spent))
            for m, s in spent[:6]:
                print("      %-44s shuffle %-4s %d valid of %d record(s)"
                      % (m[-44:], s, have.get((m, s), 0), tried.get((m, s), 0)))
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

    n, failed = 0, []
    for (model, shuffle) in left:
        if args.limit and n >= args.limit:
            break
        cmd = [sys.executable, os.path.join(HERE, "run_compass.py"),
               "--model", model, "--condition", CONDITION,
               "--runs", str(p["runs"]), "--temperature", str(p["temperature"]),
               "--seed", str(p["seed_base"]), "--max-tokens", str(p["max_tokens"]),
               "--template", p["template"], "--channel", channel_for(model),
               "--delay", str(args.delay), "--out", d]
        # THE CANONICAL ORDER TAKES NO --shuffle-seed, AND PASSING str(None) SENT "None".
        #
        # 2026-09-07: the first off-panel arm queued the canonical order and this line passed
        # the four characters `None` where an int was expected. run_compass exited without
        # writing a record, the collector printed "(no result line)" for that cell, and then
        # printed **"collected 3 cell(s); 0 remain"** and exited 0 with the canonical arm empty.
        # Both shuffled orders were fine, so the arm looked collected and had nothing to pair
        # them against -- the exact shape of the ablation collector's "0 remain over twelve
        # empty cells", in a second collector, two hours after that one was fixed.
        if shuffle is not None:
            cmd += ["--shuffle-seed", str(shuffle)]
        if p.get("seed_sweep"):
            cmd.append("--seed-sweep")
        r = subprocess.run(cmd, capture_output=True, text=True)
        tail = [l for l in (r.stdout or "").splitlines() if "runs valid" in l]
        if not tail:
            # A cell that produced no result line is a FAILURE, not a quiet skip. Say what the
            # subprocess said, because "(no result line)" on its own sent this exact defect
            # past a review.
            err = ((r.stderr or "").strip().splitlines() or ["(no stderr)"])[-1]
            print("  %-34s shuffle %-4s FAILED rc=%s: %s"
                  % (model[-34:], shuffle, r.returncode, err[:110]))
            failed.append((model, shuffle))
        else:
            print("  %-34s shuffle %-4s %s"
                  % (model[-34:], shuffle, tail[-1].split(":")[-1].strip()))
        n += 1
    print("")
    print("collected %d cell(s); %d remain" % (n, len(left) - n))

    # "0 REMAIN" IS NOT "DONE" -- the same closing line this collector shipped over an empty
    # canonical arm. Re-scan the directory and report cells that hold no valid sheet, by
    # DISTINCT SEED, and exit non-zero so a caller cannot mistake the run for a success.
    have_now, tried_now = collected(d), attempted(d)
    orders = SHUFFLE_SEEDS if not panel.get("off_panel") else (None,) + SHUFFLE_SEEDS
    short = [(m, s) for m in panel["models"] for s in orders
             if have_now.get((m, s), 0) < p["runs"]]
    ok = [(m, s) for m in panel["models"] for s in orders
          if have_now.get((m, s), 0) >= p["runs"]]
    print("  %d of %d cell(s) at n=%d" % (len(ok), len(ok) + len(short), p["runs"]))
    if failed:
        print("  %d cell(s) FAILED TO RUN (no result line):" % len(failed))
        for m, s in failed:
            print("      %-40s shuffle %s" % (m[-40:], s))
    if short:
        print("  %d cell(s) hold fewer than %d valid seed(s):" % (len(short), p["runs"]))
        for m, s in short:
            print("      %-40s shuffle %-5s %d valid of %d record(s)"
                  % (m[-40:], s, have_now.get((m, s), 0), tried_now.get((m, s), 0)))
        print("  An order floor needs the CANONICAL arm too: two shuffled orders with nothing")
        print("  to pair against measures shuffle-against-shuffle, not order-against-canonical.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
