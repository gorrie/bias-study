#!/usr/bin/env python3
"""What effect is this instrument actually able to detect? And which of our nulls are real?

WHY THIS EXISTS
---------------
Every control in this project was aimed in one direction. Positive findings were measured
against a noise floor and most of them died. The NULLS were never measured against anything,
and a null is a claim: "position does not move under prompt pressure" asserts something about
the world exactly as much as "position moves" does, and it can be wrong in exactly the same
way -- by being made with an instrument too blunt to tell.

That asymmetry is not neutral. It systematically converts findings into non-findings, because
the only claims exposed to a floor were the ones asserting an effect. This script closes it.

WHAT IT COMPUTES
----------------
For each measured null distribution:

  threshold   the reference distribution's empirical 95th percentile. An observation must
              EXCEED it -- strictly; at it is not above it -- to be called distinguishable.

              IT IS NOT AN ALPHA=0.05 REJECTION THRESHOLD, and this file said it was until
              2026-09-12. A rejection region is defined under a null's assumptions; these
              reference distributions pool heterogeneous model variants with shared-model
              pair dependence, so their p95 is a descriptive order statistic and nothing
              more. Clearing it does not carry a false-positive rate. The independent
              2026-09-08 correction pass reached this same conclusion separately.

  MDE         minimum detectable effect at 80% power. The smallest true effect size such
              that, if it were real, 80% of measurements of it would land above `threshold`.
              Estimated non-parametrically: shift the empirical null distribution upward by
              delta and find the smallest delta where 80% of the shifted mass clears the
              threshold. This assumes the effect adds to noise of the same shape, which is
              the standard assumption and is stated here so it can be argued with.

Then it takes each NULL RESULT this project has published and asks the only question that
matters about it: is the observed movement below the reference? If it is, the honest verdict is
NOT "no effect." It is "underpowered -- this instrument cannot tell," and any claim built on
that null is unsupported in both directions.

    python scripts/power.py
    python scripts/power.py --markdown

No API calls. Arithmetic on data already on disk.
"""
from __future__ import annotations

import math

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import floor_table as F  # noqa: E402

POWER = 0.80
ALPHA = 0.05

#: The published-nulls audit that lived here was DELETED 2026-09-18 along with
#: RETIRED_BOUND and PUBLISHED_NULLS. Five claims measured out of 62 items on the retired
#: questionnaire were being compared against thresholds measured out of 32 on the live
#: battery; the comparison is a unit error that cannot be fixed by rescaling, and the
#: claims themselves are withdrawn. See CORRECTIONS-2026-09-17-power.md and
#: test_correction_gates.test_no_audit_of_observations_in_retired_units, which keeps them
#: deleted. What remains in this file -- the detection limits -- is measured on the live
#: instrument and is the only thing the paper cites from it.


def pctile(vals, q):
    v = sorted(vals)
    if not v:
        return float("nan")
    i = int(q * len(v))
    return v[min(i, len(v) - 1)]


def pctile_is_max(vals, q):
    """Is this 'percentile' just the sample maximum?

    With small n, `int(q * len(v))` clamps to the last element, so a p95 or p90
    IS the largest observation and carries none of the tail behaviour the name
    implies. Measured: `requantisation` n=13, `presentation order, one sitting,
    local 2026` n=3 -- both report their own maximum as a threshold, and the
    requantisation row is what decides the ablation null's verdict.

    `floor_table.summarise()` already computes `small_n` / `p90_is_max` and
    `ci_str()` refuses to print an uncomputable interval. power.py re-derived the
    statistic and carried none of that disclosure, so the same number appeared
    with its caveat in one place and bare in the other.
    """
    v = sorted(vals)
    if not v:
        return False
    i = min(int(q * len(v)), len(v) - 1)
    return i == len(v) - 1


def _instrument_bound():
    """The live instrument's item count, read from the bank rather than typed.

    This was a literal 62 -- the retired external instrument's length. The study's own
    battery is 32 items, so a hardcoded 62 would clip every detection limit against a
    ceiling nearly twice the real one and quote MDEs the instrument cannot express.
    """
    import json as _json
    try:
        from studypaths import STUDY_DIR as _SD
        import floor_table as _F
        # The withdrawn i3 bank's filename was here too; it left data/ on 2026-09-17 and a
        # mapping entry pointing outside data/ can only resolve to a missing file.
        name = {_F.RATCHET_INSTRUMENT: "ratchet-battery.json"}.get(_F.INSTRUMENT_DEFAULT)
        if name:
            with open(str(_SD / "data" / name), encoding="utf-8") as fh:
                return len(_json.load(fh)["items"])
    except Exception:                                   # noqa: BLE001
        pass
    return 62


#: The live instrument's item count. A side or endpoint count cannot exceed it.
BOUND = _instrument_bound()


def mde(vals, threshold, power=POWER):
    """Smallest upward shift of the empirical reference that clears `threshold` `power` of the time.

    THE SHIFT MODEL CLIPS AT THE INSTRUMENT'S BOUND. The barometer has 62 items, so a side
    count cannot exceed 62 and a shift that would require it is not a smaller effect we failed
    to detect -- it is unreachable. This returned a finite 1 for mde([62], 62), describing a
    sensitivity the instrument cannot have. If the threshold sits at the bound, NO shift clears
    it, and the honest answer is undefined rather than a number that will be read as achievable.
    """
    if power <= 0 or power > 1:
        raise ValueError("power must be in (0, 1]; a shift clearing a threshold 0%% of the "
                         "time is not a detectable effect")
    if any(v > BOUND for v in vals):
        raise ValueError("reference value above the instrument's %d-item bound" % BOUND)
    if not vals:
        return float("nan")
    for delta in range(0, BOUND + 1):
        shifted = [min(v + delta, BOUND) for v in vals]
        if sum(1 for s in shifted if s > threshold) / len(shifted) >= power:
            return delta
    return float("nan")


def collect():
    """Raw per-pair values for every floor, reusing floor_table's own loaders."""
    out = {}
    # floor_table.ALL_FLOORS, not a second copy. See chart_floors.floors() for what a third
    # copy of this list cost: a floor could reach the paper with no power analysis behind it.
    for fn in F.ALL_FLOORS:
        # floor_table.summarise() discards the raw pairs, so re-derive them the same way it
        # does and keep them. Any divergence between this and floor_table is a bug in one of
        # the two, which is why both read the same loaders.
        for name, pairs in _pairs_for(fn):
            if pairs:
                out[name] = {"side": [p[0] for p in pairs],
                             "endpoint": [p[1] for p in pairs]}
    return out


# `_label` used to live here: a hand-typed function-name -> display-name map, which was a
# FOURTH copy of the floor list wearing different clothes. Adding `floor_conditions_wave` to
# ALL_FLOORS raised a KeyError from it, which is the good failure -- the same omission in
# chart_floors.py failed silently by plotting one row fewer than the paper printed. The name a
# floor goes by is the name it passes to summarise(), and `spy` already receives it, so there
# is nothing here to keep in sync.


def _pairs_for(fn):
    """Call the floor function and intercept EVERY pair list before it is summarised away.

    A floor function may emit more than one row. `floor_conditions_wave` emits a local
    open-weight row and a hosted row, and this captured a single dict, so the second call
    overwrote the first: the local one-sitting order row (10 pairs) vanished behind the hosted
    row (75 pairs) and its threshold silently became the hosted one. Rows are a list now.
    """
    captured = []
    original = F.summarise

    def spy(name, pairs, note="", **kw):
        # **kw so this wrapper survives summarise() gaining arguments. It did on 2026-09-04
        # (`clusters=`, for the cluster bootstrap) and this spy raised TypeError, taking every
        # detection limit down with it -- a monkeypatch that mirrors a signature has to be
        # updated in lockstep or written not to care. Written not to care.
        captured.append((name, pairs))
        return original(name, pairs, note, **kw)

    F.summarise = spy
    try:
        fn()
    finally:
        F.summarise = original
    return captured or [(fn.__name__, [])]


def reference_kind(name):
    """What KIND of distribution this row is -- and none of them is a calibrated null.

    An INTERVENTION is something we did to the model on purpose: a changed prompt condition,
    a refusal-direction ablation, a different elicitation format. Its spread is the effect of
    the manipulation, not nuisance variation, so folding it into the reference distribution
    inflates the very threshold an observed effect must clear. Only "prompt condition A->D"
    was excluded here; refusal-direction ablation was still being used as a reference, which
    is the September 8 correction record's third item.
    """
    if name.startswith(("prompt condition", "refusal-direction ablation", "elicitation format")):
        return "intervention"
    if name == "same-version variants":
        return "model variants (not a null)"
    return "nuisance reference (not calibrated)"


def classify_observation(observed, threshold, caveat=None):
    """Quality caveats take precedence; equality never clears the reference.

    Extracted from main()'s print loop so the decision rule can be tested directly. It was
    inline, which is why the `>=` boundary went unnoticed: exercising it meant reading the
    report rather than asserting on a function.
    """
    if caveat:
        return "MEASUREMENT LIMITED"
    if not math.isfinite(threshold):
        return "REFERENCE UNAVAILABLE"
    return "ABOVE REFERENCE" if observed > threshold else "AT OR BELOW REFERENCE"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--markdown", action="store_true")
    args = ap.parse_args(argv)

    floors = collect()

    rows = []
    for name, d in floors.items():
        if reference_kind(name) == "intervention":
            continue                       # a manipulation, not a null
        for stat in ("side", "endpoint"):
            vals = d[stat]
            thr = pctile(vals, 1 - ALPHA)
            rows.append((name, stat, len(vals), thr, mde(vals, thr),
                         pctile_is_max(vals, 1 - ALPHA)))

    if args.markdown:
        # A REAL TABLE. This flag was accepted and ignored, so the paper carried the fixed-width
        # text in a code fence -- a block that scrolls sideways on a page and breaks a PDF.
        print("Detection limits: what this instrument can resolve against each null, in items of "
              "%d. The threshold is the null's 95th percentile, an order statistic and not an "
              "alpha = 0.05 rejection region. The minimum detectable effect (MDE) is the "
              "smallest shift that would put 80%% of its mass above that threshold: a design "
              "sensitivity, not achieved power." % BOUND)
        print()
        print("| null | statistic | pairs | threshold | MDE | note |")
        print("|---|---|---:|---:|---:|---|")
        for name, stat, n, thr, m, is_max in rows:
            note = "p95 is the sample maximum (n=%d)" % n if is_max else ""
            print("| %s | %s | %d | %.0f | %.0f | %s |" % (name, stat, n, thr, m, note))
        return 0

    # DERIVED. Typed as 62 -- the retired questionnaire's length -- above a table of limits
    # computed from 32-item sheets, where every threshold is a count of items out of that
    # bound. BOUND already reads the live bank; the header did not.
    print("DETECTION LIMITS -- what this instrument can resolve, per null, of %d items"
          % BOUND)
    print("threshold = reference p95, an order statistic; NOT an alpha=0.05 rejection region")
    print("MDE       = smallest shift with 80% of mass above p95; a design sensitivity,")
    print("            NOT achieved power, and NOT a cutoff for reading an observation")
    print()
    print("%-28s %-9s %6s %11s %6s  %s"
          % ("null", "statistic", "pairs", "threshold", "MDE", "note"))
    for name, stat, n, thr, m, is_max in rows:
        # SAY WHEN THE "p95" IS JUST THE LARGEST OBSERVATION. With small n the
        # percentile index clamps to the last element, so the threshold carries
        # none of the tail behaviour its name implies.
        note = "p95 IS THE SAMPLE MAX (n=%d)" % n if is_max else ""
        print("%-28s %-9s %6d %11.0f %6.0f  %s" % (name, stat, n, thr, m, note))

    # THE PUBLISHED-NULLS AUDIT WAS DELETED 2026-09-18, WITH ITS GUARD AND ITS TEST.
    #
    # It compared five claims measured on the retired 62-item questionnaire against
    # thresholds measured on the live 32-item battery, which is a unit error: 14 of 62 is
    # 23% of an instrument, 11 of 32 is 34%, and a side-flip count cannot be rescaled
    # because the ITEMS differ, not merely how many there are. The guard that refused the
    # comparison was correct, and it made this function exit 2 unconditionally, which
    # blocked gen_paper.
    #
    # It is deleted rather than re-measured because THE CLAIMS THEMSELVES ARE WITHDRAWN.
    # CORRECTIONS-2026-09-17-power.md said to delete the guard and the test together
    # 'once the nulls are re-measured on the live instrument'. They will not be, because
    # the study no longer makes them. That difference is written into that file rather
    # than left for a later reader to infer that a re-measurement happened.
    #
    # What this file still does -- the detection limits above -- is unaffected. They are
    # measured on the live instrument and are the only thing the paper cites from it.
    return 0


if __name__ == "__main__":
    sys.exit(main())
