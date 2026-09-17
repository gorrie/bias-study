#!/usr/bin/env python3
"""Refuse to collect until every pre-registered outcome can be COMPUTED from a run directory.

WHY THIS EXISTS
---------------
On 2026-09-17, after four collection passes and 702 records, the study's pre-registered
estimator had never produced a number. `position_analysis.py` is named in
`PREREG-2026-09-14-i3-phase4.md` as the estimator for position, consistency and acquiescence,
written before the data deliberately so it could not be shaped by it. Given a real run
directory its `main()` printed

    Phase 4 has not been collected yet; nothing to analyse in <dir>

and returned 2. Behind that stub sat three more breakages, any one of which would have crashed
it had it ever been called:

  * `pair_index` read `item["pair_id"]`; the bank's field is `pair_no`.
  * `cell_positions` iterated `rec["answers"].items()`, a mapping; the collector writes a LIST.
  * the four pre-registered contrasts named conditions `F/N/P/C`; the wave collected `N/A/P/D`,
    so the loop that builds them appended nothing and returned an empty list.

**Its selftest passed throughout** -- eleven checks against synthetic input the estimator
generates itself, in a shape it chooses itself. An estimator validated only against input it
defines is validated against its own assumptions, and a green selftest over a dead real-data
path is this project's signature failure (LEARNINGS #1) pointed at its own primary outcome.

WHAT WAS MISSING WAS A JOIN. Collection was gated (instrument signed, budget measured, arms
accounted for) and analysis was gated (selftests, `--check` flags), and nothing asserted that
the analysis can consume what the collection produces. This is that gate: it runs each declared
outcome against the live corpus and requires a real value out.

    python scripts/check_outcomes_computable.py            # exit 1 if an outcome cannot compute
    python scripts/check_outcomes_computable.py --list     # what is declared, and exit 0
"""
from __future__ import annotations

import argparse
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, HERE)


#: Resamples this gate uses, instead of the analysis setting of 20,000.
#:
#: IT IS CHECKING COMPUTABILITY, NOT PUBLISHING A NUMBER. The full bootstrap over 153 contrasts
#: takes minutes, and a pre-collection gate that takes minutes is a gate people skip -- which is
#: the failure mode every skipped gate in this project has had. The intervals produced here are
#: never reported; `position_analysis --prereg` computes the publishable ones at full width.
GATE_BOOTSTRAP = 200


def _fast(fn):
    """Run `fn` with the reduced bootstrap, restoring the real setting afterwards."""
    import position_analysis as P
    real = P.BOOTSTRAP_N
    P.BOOTSTRAP_N = GATE_BOOTSTRAP
    try:
        return fn()
    finally:
        P.BOOTSTRAP_N = real


#: The corpus, read ONCE per invocation.
#:
#: Each outcome used to call `load_records` itself, so a four-outcome run parsed 702 records
#: four times and ran `analyse()` twice -- 3m36s, which is long enough that a pre-collection
#: gate gets skipped, and a skipped gate is the failure this file exists to prevent.
#: Keyed on the directory so a test that swaps the corpus is not served a stale read.
_CACHE = {}


def records_for(run_dir):
    import position_analysis as P
    key = (os.path.abspath(run_dir), P.load_records)
    if key not in _CACHE:
        _CACHE.clear()
        _CACHE[key] = P.load_records(run_dir)
    return _CACHE[key]


def analysis_for(run_dir):
    import position_analysis as P
    key = (os.path.abspath(run_dir), "analyse", P.CONDITION_MAP.get("F"), P.pair_index)
    if key not in _CACHE:
        recs = records_for(run_dir)
        _CACHE[key] = _fast(lambda: P.analyse(recs)) if recs else None
    return _CACHE[key]


def _latest_wave():
    """The newest wave directory holding records, or None."""
    dirs = sorted(d for d in glob.glob(os.path.join(STUDY, "runs", "*-wave"))
                  if glob.glob(os.path.join(d, "*.jsonl")))
    return dirs[-1] if dirs else None


def outcome_position(run_dir):
    """Position, consistency and acquiescence -- the prereg's three measures."""
    import position_analysis as P
    bank = P.load_bank()
    recs = records_for(run_dir)
    if not recs:
        return None, "no valid sheets loaded from %s" % os.path.basename(run_dir)
    pos, cons = P.cell_positions(recs, P.pair_index(bank))
    if not pos:
        return None, ("%d sheets loaded but no pair positions computed -- the bank and the "
                      "records disagree about item ids or frames" % len(recs))
    acq = P.acquiescence(recs, P.pair_index(bank))
    return ("%d pair-cells over %d model(s); acquiescence on %d model(s)"
            % (len(pos), len({m for m, _c, _p in pos}), len(acq))), None


def outcome_contrasts(run_dir):
    """The four pre-registered contrasts, with intervals, on the collected conditions."""
    import position_analysis as P
    full = analysis_for(run_dir)
    if not full:
        return None, "no valid sheets loaded"
    if not full["contrasts"]:
        got = ", ".join(full["conditions"]) or "none"
        want = ", ".join(sorted({c for pair in P.CONTRASTS for c in pair}))
        return None, ("ZERO contrasts computed. The prereg names conditions %s; the records "
                      "carry %s. Check position_analysis.CONDITION_MAP." % (want, got))
    kinds = {r.get("prereg_contrast") for r in full["contrasts"]}
    missing = [("%s - %s" % c) for c in P.CONTRASTS if ("%s - %s" % c) not in kinds]
    if missing:
        return None, "no model has both arms of: %s" % ", ".join(missing)
    return "%d contrast(s) across %d kind(s)" % (len(full["contrasts"]), len(kinds)), None


def outcome_predictions(run_dir):
    """Every numbered prediction returns a verdict, and none of them is unevaluated."""
    full = analysis_for(run_dir)
    if not full:
        return None, "no valid sheets loaded"
    preds = full.get("predictions") or []
    if not preds:
        return None, "no predictions evaluated"
    blank = [p["n"] for p in preds if not p.get("verdict")]
    if blank:
        return None, "prediction(s) %s produced no verdict" % blank
    # A verdict of FAIL is a RESULT and must never fail this gate. The gate asks whether the
    # prediction could be evaluated, never whether it was confirmed -- a check that goes red on
    # an unwelcome answer is a check that gets tuned until the answer changes.
    return ("%d prediction(s): %s"
            % (len(preds), ", ".join("%d=%s" % (p["n"], p["verdict"]) for p in preds))), None


def outcome_floors(run_dir):
    """At least one floor arm computes, and none is BROKEN."""
    import floor_table as F
    rows = F.all_floors()
    broken = [a for a, kind, _w in F.uncomputed_report() if kind == "path"]
    if broken:
        return None, "floor arm(s) read a path matching no file: %s" % ", ".join(broken)
    if not rows:
        return None, "no floor arm produced a row"
    return "%d floor row(s), 0 broken arm(s)" % len(rows), None


#: Every outcome the pre-registration names, and the function that must produce it.
OUTCOMES = (
    ("position / consistency / acquiescence", outcome_position),
    ("the four pre-registered contrasts", outcome_contrasts),
    ("the five committed predictions", outcome_predictions),
    ("the measured floors", outcome_floors),
)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("run", nargs="?", help="run directory (default: the newest wave)")
    ap.add_argument("--list", action="store_true", help="what is declared, then exit 0")
    a = ap.parse_args(argv)

    if a.list:
        print("PRE-REGISTERED OUTCOMES THIS GATE REQUIRES (%d):" % len(OUTCOMES))
        for name, fn in OUTCOMES:
            print("  %-42s %s" % (name, fn.__name__))
        return 0

    run_dir = a.run
    if run_dir and not os.path.isdir(run_dir):
        run_dir = os.path.join(STUDY, "runs", run_dir)
    run_dir = run_dir or _latest_wave()
    if not run_dir or not os.path.isdir(run_dir):
        # NOT APPLICABLE, not a pass: a tree with no corpus cannot answer this, and the public
        # mirror is in that state until a scrubbed export lands.
        print("NOT APPLICABLE -- no wave directory with records under runs/.")
        print("This gate asks whether the analysis can read a collection. There is none here.")
        return 2

    print("OUTCOMES COMPUTABLE FROM %s" % os.path.basename(run_dir))
    failures = []
    for name, fn in OUTCOMES:
        try:
            value, why = fn(run_dir)
        except Exception as exc:                                  # noqa: BLE001
            value, why = None, "raised %s: %s" % (type(exc).__name__, exc)
        if value is None:
            print("  FAIL  %-42s %s" % (name, why))
            failures.append((name, why))
        else:
            print("  ok    %-42s %s" % (name, value))

    if failures:
        print("")
        print("REFUSED -- %d pre-registered outcome(s) cannot be computed from the corpus."
              % len(failures))
        print("Collecting more data does not fix an analysis that cannot read it. This gate")
        print("exists because the primary estimator spent four collection passes as a stub")
        print("whose selftest was green: it validated itself against input it generated in a")
        print("shape it chose, and no test asked it to read a real record.")
        return 1
    print("")
    print("every declared outcome produces a value from the live corpus.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
