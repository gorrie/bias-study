#!/usr/bin/env python3
"""Can this comparison mean anything? Ask BEFORE the spend and BEFORE the writeup.

WHY THIS EXISTS
---------------
On 2026-09-19 four adversarial reviews found three separate defects with one shape: **a
comparison that could not have meant anything, discovered after it was collected and after it
was written up.** Each was obvious once asked and invisible until then.

  1. **The arms were not comparable.** Rung 2's contrasts differed from their control by the
     system prompt AND the numbering protocol (v2 against v1) AND the token budget AND whether
     a seed was sent. The collector's own docstring said the order was "held constant". 120
     sheets.
  2. **The criterion was unsatisfiable.** Rung 2's within-rung family: 5 sheets per arm gives
     C(10,5) = 252 permutations, so the smallest reachable two-sided exact p is 2/252 =
     0.0079 -- against a BH rank-1 threshold of 0.005. **No effect of any size could pass.**
     "0 of 10 survive" was a fact about the design. Same shape as prediction 2 of
     `PREREG-2026-09-14-i3-phase4.md` and the clause-factorial floor: three instances.
  3. **The estimator was not calibrated at the n in use.** The sheet bootstrap returns 104
     surviving BH where an exact permutation returns 84 -- one in five. Before that, the pair
     bootstrap rejected 49.6% of true nulls while looking principled.

A reproducer should not have to know any of this. **This script asks the three questions.**

    python scripts/check_comparison.py --cells <run> <model> <arm_a> <arm_b>
    python scripts/check_comparison.py --satisfiable --n-a 5 --n-b 5 --family 10
    python scripts/check_comparison.py --check        # every published contrast, all three

Exit 0 usable, 1 a comparison that cannot support a claim, 2 NOT APPLICABLE.
"""
from __future__ import annotations

import argparse
import collections
import glob
import io
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, HERE)

#: Fields that must MATCH between two arms, because they are not the treatment. A difference
#: in any of them is a confound, and the list is explicit so adding a factor to the study
#: forces a decision about it rather than letting it ride.
#:
#: `renumbered` is on this list because it was the one that got through: the rung-1 wave is
#: entirely protocol v1 and the rung-2 arms entirely v2, and the numbering artifact is a
#: PUBLISHED FINDING of this study (14.0% of sheets lost as-is against 1.4% renumbered).
MUST_MATCH = ("instrument", "template", "renumbered", "shuffle_seed", "max_tokens",
              "classifier", "provider")

#: Fields allowed to differ only when they ARE the treatment; naming one as the treatment is
#: how a caller says "this difference is deliberate".
TREATMENT_FIELDS = ("condition", "system_prompt", "temperature", "presence_penalty",
                    "frequency_penalty", "seed")


def min_reachable_p(n_a, n_b):
    """Smallest two-sided p an exact permutation test can return at these arm sizes.

    A permutation test over C(n_a+n_b, n_a) relabellings cannot report a p below
    2/C(...) -- the observed split and its mirror always count. If that floor exceeds the
    threshold a criterion sets, the criterion is unsatisfiable and no effect of any size will
    pass it.
    """
    total = math.comb(n_a + n_b, n_a)
    return 2.0 / total if total else 1.0


def satisfiable(n_a, n_b, family, q=0.05):
    """Can the SMALLEST BH threshold in a family of this size ever be met at this n?"""
    floor_p = min_reachable_p(n_a, n_b)
    strictest = q / family if family else q
    return {
        "min_reachable_p": floor_p,
        "strictest_bh_threshold": strictest,
        "satisfiable": floor_p <= strictest,
        "permutations": math.comb(n_a + n_b, n_a),
        "n_needed_per_arm": _n_for(strictest),
    }


def _n_for(threshold, cap=60):
    """Smallest balanced per-arm n whose exact test can reach `threshold`."""
    for n in range(2, cap + 1):
        if 2.0 / math.comb(2 * n, n) <= threshold:
            return n
    return None


def load_cells(run_dir, model, arms):
    """Raw records per arm, keeping the fields a comparability check needs."""
    root = os.path.join(STUDY, "runs", run_dir)
    if not os.path.isdir(root):
        return None
    out = collections.defaultdict(list)
    for path in sorted(glob.glob(os.path.join(root, "*.jsonl"))):
        for line in io.open(path, encoding="utf-8", errors="replace"):
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("model") != model or not r.get("valid"):
                continue
            cond = r.get("condition")
            if cond in arms:
                out[cond].append(r)
    return out


def comparable(rows_a, rows_b, treatment=()):
    """Every MUST_MATCH field that differs between two arms and is not declared treatment."""
    problems = []
    for field in MUST_MATCH:
        if field in treatment:
            continue
        va = {json.dumps(r.get(field), sort_keys=True) for r in rows_a}
        vb = {json.dumps(r.get(field), sort_keys=True) for r in rows_b}
        if len(va) > 1 or len(vb) > 1:
            problems.append("%s is NOT CONSTANT WITHIN an arm (a=%s b=%s)"
                            % (field, sorted(va)[:3], sorted(vb)[:3]))
        elif va != vb:
            problems.append("%s differs between arms: %s vs %s"
                            % (field, sorted(va)[0], sorted(vb)[0]))
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cells", nargs=4, metavar=("RUN", "MODEL", "ARM_A", "ARM_B"),
                    help="check two arms of one model for comparability")
    ap.add_argument("--treatment", nargs="*", default=["condition", "system_prompt"],
                    help="fields allowed to differ because they ARE the manipulation")
    ap.add_argument("--satisfiable", action="store_true",
                    help="can a BH criterion be met at this n? needs --n-a --n-b --family")
    ap.add_argument("--n-a", type=int, default=5)
    ap.add_argument("--n-b", type=int, default=5)
    ap.add_argument("--family", type=int, default=1)
    ap.add_argument("--q", type=float, default=0.05)
    a = ap.parse_args(argv)

    if a.satisfiable:
        s = satisfiable(a.n_a, a.n_b, a.family, a.q)
        print("CAN THIS CRITERION EVER BE MET?")
        print("  arms %d vs %d -> %d relabellings" % (a.n_a, a.n_b, s["permutations"]))
        print("  smallest exact p reachable      %.5f" % s["min_reachable_p"])
        print("  strictest BH threshold (k=%d)   %.5f" % (a.family, s["strictest_bh_threshold"]))
        print()
        if s["satisfiable"]:
            print("  SATISFIABLE. An effect large enough can pass.")
            return 0
        print("  *** UNSATISFIABLE ***  No effect of any size can clear the strictest")
        print("  threshold in this family. A null result here is a fact about the DESIGN,")
        print("  not about the models, and must never be reported as evidence of no effect.")
        if s["n_needed_per_arm"]:
            print("  Smallest balanced arm size that would work: n = %d per arm."
                  % s["n_needed_per_arm"])
        return 1

    if a.cells:
        run, model, arm_a, arm_b = a.cells
        cells = load_cells(run, model, {arm_a, arm_b})
        if cells is None:
            print("NOT APPLICABLE: no run directory %r" % run)
            return 2
        if not cells.get(arm_a) or not cells.get(arm_b):
            print("NOT APPLICABLE: %s has no valid sheets in %s"
                  % (model, arm_a if not cells.get(arm_a) else arm_b))
            return 2
        ra, rb = cells[arm_a], cells[arm_b]
        problems = comparable(ra, rb, set(a.treatment))
        s = satisfiable(len(ra), len(rb), a.family, a.q)

        print("COMPARISON: %s   %s vs %s   (%d vs %d sheets)"
              % (model, arm_a, arm_b, len(ra), len(rb)))
        print("  treatment (allowed to differ): %s" % ", ".join(a.treatment))
        print()
        if problems:
            print("  NOT COMPARABLE -- %d confound(s):" % len(problems))
            for p in problems:
                print("    %s" % p)
            print()
            print("  A difference here is the treatment PLUS these. Either match them, or")
            print("  declare the one you meant with --treatment and say so in the writeup.")
        else:
            print("  comparable: every non-treatment field matches.")
        print()
        print("  smallest exact p reachable %.5f against BH k=%d threshold %.5f -> %s"
              % (s["min_reachable_p"], a.family, s["strictest_bh_threshold"],
                 "satisfiable" if s["satisfiable"] else "*** UNSATISFIABLE ***"))
        if not s["satisfiable"] and s["n_needed_per_arm"]:
            print("  needs n = %d per arm to be decidable at this family size."
                  % s["n_needed_per_arm"])
        return 0 if (not problems and s["satisfiable"]) else 1

    ap.error("one of --cells or --satisfiable is required")


if __name__ == "__main__":
    raise SystemExit(main())
