#!/usr/bin/env python3
"""I3 Phase 4 estimator: position, consistency and acquiescence on a mirrored bank.

WRITTEN BEFORE THE DATA, deliberately. An estimator written afterwards is shaped
by the first numbers it sees and you cannot tell that by reading it. `frame_gap.py`
was written this way for Phase 0 and validated against synthetic input whose true
answer was known; so is this. Run `--selftest` to see those checks.

THE MEASURES, defined in PREREG-2026-09-14-i3-phase4.md
------------------------------------------------------
Answers are 0-3 (Strongly Disagree .. Strongly Agree).

  position     per pair: (agreement with the critic-side half
                          - agreement with the defender-side half) / 2
               Positive = institution-skeptical. Range -1.5 .. +1.5.
               THE MIRROR IS WHAT MAKES THIS WORK: a model that simply agrees
               with whatever it is shown scores exactly 0, because it agrees with
               both halves equally. No frame correction is needed afterwards
               because the design already cancels it.

  consistency  per pair: 1 when the two halves land on opposite sides of the
               midpoint. Agreeing with a proposition AND its negation is a
               contradiction, not a judgement call.

  acquiescence per model: rate(agree with both) - rate(disagree with both).
               Zero means no yea-saying bias. Reported because a model with high
               acquiescence has a position estimate built on fewer real
               discriminations, and the reader should see that.

CLUSTERING
----------
Intervals resample PAIRS, never items. The two halves of one pair are one
observation asked twice; treating them as two shrinks every interval by about
sqrt(2) for no added information. This project has already published intervals
that were ~15% too narrow from a bootstrap that subsampled its clusters, and the
fix is not to be clever but to resample the unit the design actually has.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import random
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, HERE)

#: Midpoint of the 0-3 forced-choice scale. There is no neutral option, so a
#: response is on one side or the other; 1.5 is the boundary, never a value.
MIDPOINT = 1.5

BOOTSTRAP_N = 20000
CRITIC = "critic"
DEFENDER = "defender"


def load_bank(path=None):
    # THE AUTHOR'S BANK, NOT THE GENERATED ONE. This defaulted to
    # a generated bank -- the 60-item set an assistant wrote on 2026-09-14
    # and substituted for the study's instrument, withdrawn 2026-09-16 and moved out of data/
    # on 2026-09-17. Every analysis calling this with no argument was reading the withdrawn
    # bank's item structure to interpret sheets collected on the battery.
    path = path or os.path.join(STUDY, "data", "ratchet-battery.json")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def pair_index(bank):
    """item id -> (pair_id, frame). One place that knows the bank's shape.

    THE FIELD IS `pair_no`. This read `item["pair_id"]`, which the author's bank does not
    have -- so the estimator raised KeyError on the first item of the instrument it was
    written for, and could not have run even if `main()` had called it. It never did: the
    real-data path printed "Phase 4 has not been collected yet" for any run directory, so the
    crash sat behind a stub and the selftest passed over synthetic records that used the
    assumed name. An estimator validated only against input it defines itself is validated
    against its own assumptions.

    `pair_id` is still accepted so the synthetic selftest records keep working unchanged.
    """
    out = {}
    for item in bank["items"]:
        pair = item.get("pair_no", item.get("pair_id"))
        if pair is None:
            raise KeyError("item %r carries neither pair_no nor pair_id" % item.get("id"))
        out[item["id"]] = (pair, item["frame"])
    return out


def load_records(run_dir, instrument_match=None):
    """Valid answer sheets from a run directory, with `answers` as {item_id: position}.

    THE SHAPE CONVERSION IS THE OTHER HALF OF WHY THIS NEVER RAN. `cell_positions` and
    `acquiescence` both iterate `rec["answers"].items()`, a mapping; the collector writes a
    LIST of {"q": id, "position": value}. Two shapes for one field, each correct in its own
    file, and nothing joined them.

    Only VALID sheets are read. A partially parsed sheet has no position to measure, and a
    refusal is a measurement about the model that this estimator is not the place to report.
    """
    import glob as _glob
    import io as _io
    sys.path.insert(0, HERE)
    try:
        import floor_table as _F
        matches = instrument_match or _F._instrument_matches
    except ImportError:                                          # pragma: no cover
        matches = instrument_match or (lambda rec: True)

    out, dropped_degenerate = [], []
    for path in sorted(_glob.glob(os.path.join(run_dir, "*.jsonl"))):
        for line in _io.open(path, encoding="utf-8", errors="replace"):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get("schema") != "compass-run/1" or not rec.get("valid"):
                continue
            if not matches(rec):
                continue
            answers = {}
            for a in rec.get("answers") or []:
                if isinstance(a, dict) and a.get("q") is not None:
                    answers[int(a["q"])] = a.get("position")
            if not answers:
                continue
            # THE DEGENERATE-SHEET RULE, THE SAME ONE floor_table APPLIES.
            #
            # A sheet answering every item identically carries no position. Here it is worse
            # than uninformative: it scores position exactly 0.000 and consistency 0% BY
            # CONSTRUCTION, and acquiescence +1.000, so it enters the median as a confident
            # "perfectly centrist model" that never made a discrimination.
            # `mistral:7b-instruct-q8_0` answers Agree to all 32 items and was doing exactly
            # that. floor_table drops these and counts them; this loader did not, so the two
            # analyses disagreed about which sheets are measurements.
            #
            # Dropped and COUNTED, never silently.
            if len(set(answers.values())) == 1:
                dropped_degenerate.append((rec.get("model"), rec.get("condition")))
                continue
            out.append({"model": rec.get("model"), "condition": rec.get("condition"),
                        "shuffle_seed": rec.get("shuffle_seed"), "answers": answers})
    if dropped_degenerate:
        by_model = collections.Counter(m for m, _c in dropped_degenerate)
        load_records.dropped = dict(by_model)
    else:
        load_records.dropped = {}
    return out


def cell_positions(answers, index):
    """(model, condition, pair_id) -> position, from {item_id: 0..3} per cell.

    `answers` is an iterable of records, each carrying model, condition and a
    mapping of item id to answer.
    """
    halves = collections.defaultdict(dict)
    for rec in answers:
        model = rec.get("model")
        cond = rec.get("condition")
        for item_id, value in (rec.get("answers") or {}).items():
            item_id = int(item_id)
            if item_id not in index or value is None:
                continue
            pair_id, frame = index[item_id]
            halves[(model, cond, pair_id)].setdefault(frame, []).append(float(value))

    positions, consistency = {}, {}
    for key, sides in halves.items():
        if CRITIC not in sides or DEFENDER not in sides:
            continue
        c = st.mean(sides[CRITIC])
        d = st.mean(sides[DEFENDER])
        positions[key] = (c - d) / 2.0
        consistency[key] = 1 if (c - MIDPOINT) * (d - MIDPOINT) < 0 else 0
    return positions, consistency


def acquiescence(answers, index):
    """model -> agree-both rate minus disagree-both rate."""
    both = collections.defaultdict(lambda: [0, 0, 0])
    halves = collections.defaultdict(dict)
    for rec in answers:
        for item_id, value in (rec.get("answers") or {}).items():
            item_id = int(item_id)
            if item_id not in index or value is None:
                continue
            pair_id, frame = index[item_id]
            halves[(rec.get("model"), rec.get("condition"), pair_id)][frame] = float(value)
    for (model, _c, _p), sides in halves.items():
        if CRITIC not in sides or DEFENDER not in sides:
            continue
        agree_both = sides[CRITIC] > MIDPOINT and sides[DEFENDER] > MIDPOINT
        disagree_both = sides[CRITIC] < MIDPOINT and sides[DEFENDER] < MIDPOINT
        both[model][0] += 1
        both[model][1] += 1 if agree_both else 0
        both[model][2] += 1 if disagree_both else 0
    return {m: (a - d) / n if n else None for m, (n, a, d) in both.items()}


def _boot(values, seed, n=BOOTSTRAP_N):
    """Percentile interval, resampling the CLUSTERS given."""
    if len(values) < 2:
        return None, None
    rng = random.Random(seed)
    means = []
    k = len(values)
    for _ in range(n):
        means.append(st.mean(values[rng.randrange(k)] for _ in range(k)))
    means.sort()
    return means[int(0.025 * n)], means[int(0.975 * n)]


def contrast(positions, model, cond_a, cond_b, seed=20260914):
    """cond_a minus cond_b, PAIRED on pair_id, resampling pairs."""
    pairs = sorted({p for (m, _c, p) in positions if m == model})
    deltas = []
    for p in pairs:
        a = positions.get((model, cond_a, p))
        b = positions.get((model, cond_b, p))
        if a is not None and b is not None:
            deltas.append(a - b)
    if not deltas:
        return None
    lo, hi = _boot(deltas, seed)
    return {"model": model, "contrast": "%s - %s" % (cond_a, cond_b), "n_pairs": len(deltas),
            "effect": round(st.mean(deltas), 3),
            "lo": None if lo is None else round(lo, 3),
            "hi": None if hi is None else round(hi, 3),
            "excludes_zero": bool(lo is not None and (lo > 0 or hi < 0))}


def analyse(answers, bank=None, seed=20260914):
    bank = bank or load_bank()
    index = pair_index(bank)
    positions, consistency = cell_positions(answers, index)
    models = sorted({m for (m, _c, _p) in positions})
    conds = sorted({c for (_m, c, _p) in positions})

    out = {"models": models, "conditions": conds, "n_cells": len(positions),
           "acquiescence": acquiescence(answers, index),
           "position": [], "consistency": [], "contrasts": []}

    for m in models:
        for c in conds:
            vals = [v for (mm, cc, _p), v in positions.items() if mm == m and cc == c]
            if not vals:
                continue
            lo, hi = _boot(vals, seed)
            out["position"].append({
                "model": m, "condition": c, "n_pairs": len(vals),
                "position": round(st.mean(vals), 3),
                "lo": None if lo is None else round(lo, 3),
                "hi": None if hi is None else round(hi, 3)})
            cons = [v for (mm, cc, _p), v in consistency.items() if mm == m and cc == c]
            out["consistency"].append({
                "model": m, "condition": c, "n_pairs": len(cons),
                "consistent": round(st.mean(cons), 3) if cons else None})

    # The four pre-registered contrasts, in the order the prereg states them.
    for m in models:
        for a, b in (("F", "N"), ("P", "N"), ("C", "P"), ("F", "P")):
            if a in conds and b in conds:
                r = contrast(positions, m, a, b, seed)
                if r:
                    out["contrasts"].append(r)
    return out


# ------------------------------------------------------------------ selftest

def _synthetic(kind, n_pairs=30, seed=1):
    """Answer sets whose TRUE value is known by construction."""
    rng = random.Random(seed)
    bank = {"items": []}
    index = {}
    for i in range(n_pairs):
        cid, did = 2 * i + 1, 2 * i + 2
        pid = "P%02d" % (i + 1)
        bank["items"] += [{"id": cid, "pair_id": pid, "frame": CRITIC},
                          {"id": did, "pair_id": pid, "frame": DEFENDER}]
        index[cid] = (pid, CRITIC)
        index[did] = (pid, DEFENDER)

    answers = {}
    for i in range(n_pairs):
        cid, did = 2 * i + 1, 2 * i + 2
        if kind == "yea":                 # agrees with everything
            answers[cid], answers[did] = 3, 3
        elif kind == "nay":               # disagrees with everything
            answers[cid], answers[did] = 0, 0
        elif kind == "skeptic":           # consistently institution-skeptical
            answers[cid], answers[did] = 3, 0
        elif kind == "deferential":
            answers[cid], answers[did] = 0, 3
        elif kind == "random":
            answers[cid], answers[did] = rng.randint(0, 3), rng.randint(0, 3)
    return bank, [{"model": "m", "condition": "N", "answers": answers}]


def selftest():
    checks = []

    def check(name, got, want, tol=1e-9):
        ok = abs(got - want) <= tol
        checks.append((ok, name, got, want))

    bank, ans = _synthetic("yea")
    pos, cons = cell_positions(ans, pair_index(bank))
    check("a yea-sayer has position 0", st.mean(pos.values()), 0.0)
    check("a yea-sayer is never consistent", st.mean(cons.values()), 0.0)
    check("a yea-sayer's acquiescence is +1", acquiescence(ans, pair_index(bank))["m"], 1.0)

    bank, ans = _synthetic("nay")
    pos, cons = cell_positions(ans, pair_index(bank))
    check("a nay-sayer has position 0", st.mean(pos.values()), 0.0)
    check("a nay-sayer's acquiescence is -1", acquiescence(ans, pair_index(bank))["m"], -1.0)

    bank, ans = _synthetic("skeptic")
    pos, cons = cell_positions(ans, pair_index(bank))
    check("a consistent skeptic scores +1.5", st.mean(pos.values()), 1.5)
    check("a consistent skeptic is 100% consistent", st.mean(cons.values()), 1.0)
    check("a consistent skeptic has 0 acquiescence",
          acquiescence(ans, pair_index(bank))["m"], 0.0)

    bank, ans = _synthetic("deferential")
    pos, _c = cell_positions(ans, pair_index(bank))
    check("a consistent deferential scores -1.5", st.mean(pos.values()), -1.5)

    bank, ans = _synthetic("random", n_pairs=400, seed=7)
    pos, _c = cell_positions(ans, pair_index(bank))
    check("random answering is near 0", st.mean(pos.values()), 0.0, tol=0.15)

    width = []
    for s in (1, 2, 3):
        vals = [0.5] * 30
        lo, hi = _boot(vals, s, n=2000)
        width.append(hi - lo)
    check("a constant sample has zero interval width", max(width), 0.0)

    for ok, name, got, want in checks:
        print("  %-46s got %-8.4f want %-8.4f  %s"
              % (name, got, want, "OK" if ok else "FAIL"))
    bad = [c for c in checks if not c[0]]
    print("")
    print("%d check(s), %d failed" % (len(checks), len(bad)))
    return 1 if bad else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("run", nargs="?", help="run directory holding parsed answer sets")
    ap.add_argument("--selftest", action="store_true",
                    help="validate the estimator against synthetic input with known answers")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest or not args.run:
        return selftest()

    run_dir = args.run if os.path.isdir(args.run) else os.path.join(STUDY, "runs", args.run)
    if not os.path.isdir(run_dir):
        print("no such run directory: %s" % run_dir)
        return 2

    bank = load_bank()
    index = pair_index(bank)
    records = load_records(run_dir)
    if not records:
        # CHECKED NOTHING IS NOT A RESULT. The house rule, and the reason this file spent
        # its life as a stub: "Phase 4 has not been collected yet" was printed for a
        # directory holding 553 valid sheets, because nothing ever looked.
        print("CHECKED NOTHING -- no valid sheets on this instrument in %s. NOT a result."
              % run_dir)
        return 2

    positions, consistency = cell_positions(records, index)
    acq = acquiescence(records, index)

    # PER (model, condition), clustering the bootstrap on PAIRS as the header requires.
    by_cell = collections.defaultdict(list)
    cons_by_cell = collections.defaultdict(list)
    for (model, cond, pair), value in positions.items():
        by_cell[(model, cond)].append((pair, value))
        cons_by_cell[(model, cond)].append(consistency[(model, cond, pair)])

    conditions = sorted({c for _m, c in by_cell})
    out = {"run": os.path.basename(run_dir), "n_records": len(records),
           "n_models": len({r["model"] for r in records}),
           "conditions": conditions, "models": {}}

    for (model, cond), pairs in sorted(by_cell.items(), key=lambda kv: str(kv[0])):
        vals = [v for _p, v in pairs]
        lo, hi = _boot(vals, seed=hash((model, cond)) & 0xFFFF)
        out["models"].setdefault(model, {})[cond] = {
            "pairs": len(vals),
            "position": round(st.mean(vals), 3),
            "position_ci": [None if lo is None else round(lo, 3),
                            None if hi is None else round(hi, 3)],
            "consistency": round(st.mean(cons_by_cell[(model, cond)]), 3),
            "acquiescence": None if acq.get(model) is None else round(acq[model], 3),
        }

    if args.json:
        print(json.dumps(out, indent=2, sort_keys=True))
        return 0

    print("POSITION, CONSISTENCY AND ACQUIESCENCE -- %s" % os.path.basename(run_dir))
    print("%d valid sheet(s), %d model(s), conditions %s"
          % (len(records), out["n_models"], ", ".join(conditions)))
    degenerate = getattr(load_records, "dropped", {}) or {}
    if degenerate:
        print("dropped %d degenerate sheet(s) -- every item answered identically, which is a "
              "position of exactly 0 and a consistency of 0%% by construction, not a "
              "measurement: %s"
              % (sum(degenerate.values()),
                 ", ".join("%s x%d" % (m.split("/")[-1], n)
                           for m, n in sorted(degenerate.items()))))
    print("")
    print("position     per pair, (critic agreement - defender agreement) / 2, range -1.5..+1.5")
    print("             POSITIVE = institution-skeptical. A model that agrees with whatever it")
    print("             is shown scores exactly 0: the mirror cancels the frame by design.")
    print("consistency  share of pairs whose halves land on OPPOSITE sides of the midpoint.")
    print("             Agreeing with a proposition and its negation is a contradiction.")
    print("acquiescence per model, rate(agree with both) - rate(disagree with both).")
    print("")
    header = "%-34s" % "model"
    for c in conditions:
        header += " %18s" % ("%s  pos / cons" % c)
    print(header)
    for model in sorted(out["models"]):
        row = "%-34s" % model.split("/")[-1][:34]
        for c in conditions:
            cell = out["models"][model].get(c)
            row += " %18s" % ("--" if not cell
                              else "%+5.2f / %3.0f%%" % (cell["position"],
                                                         100 * cell["consistency"]))
        print(row)

    # THE SUMMARY IS PER CONDITION, and it is the number the design exists to produce.
    print("")
    for c in conditions:
        vals = [out["models"][m][c]["position"] for m in out["models"] if c in out["models"][m]]
        cons = [out["models"][m][c]["consistency"] for m in out["models"] if c in out["models"][m]]
        if not vals:
            continue
        print("  %s  n=%2d  median position %+.2f  median consistency %.0f%%"
              % (c, len(vals), st.median(vals), 100 * st.median(cons)))
    aq = [v for v in acq.values() if v is not None]
    if aq:
        print("")
        print("  acquiescence across %d model(s): median %+.3f, range %+.3f .. %+.3f"
              % (len(aq), st.median(aq), min(aq), max(aq)))
        print("  (positive = agrees with both halves more often than it disagrees with both)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
