#!/usr/bin/env python3
"""Arm minus control across TWO run directories, with the v2 floor and an exact test.

WHY THIS FILE EXISTS. `PREREG-2026-09-20-rung2-control-v2.md` §4 registered three commands
and then recorded, in its own correction block, that **no script in this tree reads the v2
control**: `run_rung2.CONTROL_RUN` is pinned to the v1 wave, `order_floor_position` takes one
run, and nothing differences two directories. Seventy sheets were collected against a
registered analysis that could not be run, which is the thing pre-registration exists to
prevent. The prereg says so plainly -- "Still owed ... Neither exists today." This is that.

WHAT IT ENFORCES, from the pre-registration rather than from taste:

  1. **Matched on model AND presentation order.** The arms carry shuffle seed 11; the control
     carries 11 and 22. A contrast is computed on seed 11 only, so the numbering, the sampler
     and the item order are all held and the system prompt is the one thing that differs.
  2. **The floor is that model's OWN between-order contrast at v2** -- control seed 11 against
     control seed 22 -- not the corpus p90 and not a v1 floor. Both sides of it come from the
     same seventy sheets.
  3. **An exact permutation test**, because `contrast_sheets` is a bootstrap whose p is a
     doubled resampling tail and whose false-positive rate at five sheets per arm is measured
     at about 10%, not 5% (`calibrate_estimators.py`). The bootstrap interval is printed as
     descriptive and decides nothing. With 5 v 5 the smallest attainable exact p is
     2/C(10,5) = 0.0079.
  4. **The kill rule is PER CONTRAST.** If the model's v2 between-order floor is at or above
     a given contrast, THAT contrast stays withdrawn whatever its p. Not "the largest contrast
     the model shows" -- that wording let one large arm exempt the other six on the same model.
  5. **Provider pins are checked**, because serving path is a same-version variant here. A
     model served by a backend other than its pin is reported and EXCLUDED, not compared.
  6. **The declared token-cap difference travels with every contrast.** The arms ran at
     max_tokens 8192 and the control at 40960; arm sheets within 95% of their cap are counted
     and printed beside the result.

    python scripts/rung2_contrast.py
    python scripts/rung2_contrast.py --arm 2026-09-19-rung2-elicitation --json
    python scripts/rung2_contrast.py --selftest

Reads only. No API calls.
"""
from __future__ import annotations

import argparse
import collections
import glob
import io
import itertools
import json
import math
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import studypaths as _SP           # noqa: E402
import position_analysis as PA     # noqa: E402

ARM_RUN = "2026-09-19-rung2-elicitation"
CONTROL_RUN = "2026-09-20-rung2-control-v2"

#: The arms are collected at this presentation order; the control carries it and one more.
ARM_SEED = 11
FLOOR_SEED = 22

#: PREREG §3. A model served by anything else is excluded rather than compared.
PROVIDER_PINS = {
    "anthropic/claude-fable-5.1": "Anthropic",
    "google/gemini-3.7-flash": "Google",
    "google/gemini-3.8-flash": "Google",
    "moonshotai/kimi-k2.5": "SiliconFlow",
    "openai/gpt-6-astra": "OpenAI",
    "openai/gpt-6-astra-pro": "OpenAI",
    "x-ai/grok-4.3": "xAI",
}

#: PREREG: the arms ran at 8192, the control at 40960. A sheet this close to its cap is
#: reported, because this study's own history includes truncation misread as refusal.
NEAR_CAP = 0.95

#: PREREG §4 condition 3. Exact, two-sided.
ALPHA = 0.05


def exact_permutation_p(a, b):
    """Two-sided exact p for mean(a) - mean(b) under exchangeability of the pooled sheets.

    Enumerated, not sampled: with 5 v 5 there are C(10,5) = 252 splits and the whole null is
    cheap. Returns None when the enumeration is too large to be exact, rather than quietly
    switching to a sampled approximation under a function named `exact`.
    """
    n, m = len(a), len(b)
    if n == 0 or m == 0:
        return None, 0
    total = n + m
    if math.comb(total, n) > 200000:
        return None, math.comb(total, n)
    pool = list(a) + list(b)
    observed = abs(st.mean(a) - st.mean(b))
    hits = 0
    splits = 0
    for idx in itertools.combinations(range(total), n):
        left = [pool[i] for i in idx]
        chosen = set(idx)
        right = [pool[i] for i in range(total) if i not in chosen]
        splits += 1
        if abs(st.mean(left) - st.mean(right)) >= observed - 1e-12:
            hits += 1
    return hits / splits, splits


def sheet_means(run_dir, index, seed_filter=None):
    """{(model, condition): [mean position per sheet]} plus provenance for the checks."""
    per = collections.defaultdict(list)
    provider = collections.defaultdict(set)
    near_cap = collections.Counter()
    for path in sorted(glob.glob(os.path.join(run_dir, "*.jsonl"))):
        for line in io.open(path, encoding="utf-8", errors="replace"):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if not _SP.is_run_record(rec) or not rec.get("valid"):
                continue
            if seed_filter is not None and rec.get("shuffle_seed") != seed_filter:
                continue
            sides = collections.defaultdict(dict)
            for ans in rec.get("answers") or []:
                item = ans.get("q")
                value = ans.get("position")
                if item is None or value is None:
                    continue
                item = int(item)
                if item not in index:
                    continue
                pair_id, frame = index[item]
                sides[pair_id][frame] = float(value)
            deltas = [(h[PA.CRITIC] - h[PA.DEFENDER]) / 2.0
                      for h in sides.values() if PA.CRITIC in h and PA.DEFENDER in h]
            if not deltas:
                continue
            key = (rec.get("model"), rec.get("condition"))
            per[key].append(st.mean(deltas))
            prov = rec.get("provider") or rec.get("served_by")
            if prov:
                provider[rec.get("model")].add(prov)
            cap = rec.get("max_tokens")
            used = rec.get("completion_tokens") or rec.get("output_tokens")
            if cap and used and used >= NEAR_CAP * cap:
                near_cap[rec.get("model")] += 1
    return per, provider, near_cap


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--arm", default=ARM_RUN)
    ap.add_argument("--control", default=CONTROL_RUN)
    ap.add_argument("--control-condition", default="B")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)

    if a.selftest:
        return selftest()

    index = PA.pair_index(PA.load_bank())
    arm_dir = os.path.join(_SP.STUDY_DIR, "runs", a.arm)
    ctl_dir = os.path.join(_SP.STUDY_DIR, "runs", a.control)
    for d in (arm_dir, ctl_dir):
        if not os.path.isdir(d):
            print("no such run directory: %s" % d, file=sys.stderr)
            return 2

    arm, arm_prov, arm_cap = sheet_means(arm_dir, index, seed_filter=ARM_SEED)
    ctl_11, ctl_prov, _ = sheet_means(ctl_dir, index, seed_filter=ARM_SEED)
    ctl_22, _, _ = sheet_means(ctl_dir, index, seed_filter=FLOOR_SEED)

    if not arm or not ctl_11:
        print("CHECKED NOTHING -- one side carries no usable sheet at shuffle seed %d."
              % ARM_SEED)
        print("  arm cells %d, control cells %d. NOT a pass." % (len(arm), len(ctl_11)))
        return 2

    # --- provider pins, before any contrast is computed
    violations = []
    for model, pin in PROVIDER_PINS.items():
        for label, seen in (("arm", arm_prov.get(model) or set()),
                            ("control", ctl_prov.get(model) or set())):
            other = {p for p in seen if p and p != pin}
            if other:
                violations.append((model, label, pin, sorted(other)))
    excluded = {m for m, _l, _p, _o in violations}

    ctl_by_model = collections.defaultdict(list)
    for (model, cond), vals in ctl_11.items():
        if cond == a.control_condition:
            ctl_by_model[model].extend(vals)
    floor_by_model = {}
    for model in ctl_by_model:
        seed22 = [v for (m, c), vals in ctl_22.items() if m == model
                  and c == a.control_condition for v in vals]
        if seed22 and ctl_by_model[model]:
            floor_by_model[model] = abs(st.mean(ctl_by_model[model]) - st.mean(seed22))

    # ARM SHEETS WITH NO CONTROL TO SUBTRACT. Printed, never dropped in silence: a model that
    # declines every control sheet still costs money on the arm side, and a reader counting
    # sheets will otherwise find them missing from every table with no reason given.
    # Measured 2026-09-21: gemini-3.8-flash returned 3 valid arm sheets against 10 refused
    # control sheets, so those three are collected, paid for and unusable.
    orphaned = collections.Counter()
    rows = []
    for (model, cond), vals in sorted(arm.items()):
        if model in excluded:
            continue
        control = ctl_by_model.get(model)
        if not control:
            orphaned[model] += len(vals)
            continue
        effect = st.mean(vals) - st.mean(control)
        p, splits = exact_permutation_p(vals, control)
        floor = floor_by_model.get(model)
        # PER CONTRAST. The floor kills THIS contrast, not the model's largest one.
        killed = floor is not None and floor >= abs(effect)
        rows.append({
            "model": model, "arm_condition": cond,
            "n_arm": len(vals), "n_control": len(control),
            "effect": round(effect, 3),
            "v2_between_order_floor": None if floor is None else round(floor, 3),
            "exact_p": None if p is None else round(p, 4),
            "splits": splits,
            "killed_by_floor": killed,
            "reportable": bool(not killed and p is not None and p < ALPHA),
            "near_cap_arm_sheets": arm_cap.get(model, 0),
        })

    if not rows:
        print("CHECKED NOTHING -- no model carries both an arm and a v2 control cell at")
        print("  shuffle seed %d. NOT a pass." % ARM_SEED)
        return 2

    if a.json:
        print(json.dumps({"arm": a.arm, "control": a.control,
                          "excluded_for_provider": sorted(excluded),
                          "contrasts": rows}, indent=2))
        return 0

    print("")
    print("  RUNG-2 ARM MINUS CONTROL, both at protocol v2")
    print("  arm %s (shuffle seed %d) - control %s condition %s"
          % (a.arm, ARM_SEED, a.control, a.control_condition))
    print("")
    if violations:
        print("  EXCLUDED -- provider pin not honoured (serving path is a same-version")
        print("  variant in this study, so these are reported, never compared):")
        for model, where, pin, other in violations:
            print("    %-34s %-8s pinned %s, served by %s"
                  % (model, where, pin, ", ".join(other)))
        print("")
    print("  %-34s %6s %6s %8s %8s %8s" %
          ("model / arm condition", "n arm", "n ctl", "effect", "v2 floor", "exact p"))
    for r in rows:
        print("  %-34s %6d %6d %8.3f %8s %8s%s"
              % (("%s %s" % (r["model"].split("/")[-1], r["arm_condition"]))[:34],
                 r["n_arm"], r["n_control"], r["effect"],
                 "n/a" if r["v2_between_order_floor"] is None
                 else "%.3f" % r["v2_between_order_floor"],
                 "n/a" if r["exact_p"] is None else "%.4f" % r["exact_p"],
                 "   WITHDRAWN (floor)" if r["killed_by_floor"] else ""))
    print("")
    reportable = [r for r in rows if r["reportable"]]
    print("  %d of %d contrast(s) clear BOTH the per-contrast floor rule and an exact "
          "two-sided p < %.2f." % (len(reportable), len(rows), ALPHA))
    if not reportable:
        print("  No rung-2 position claim is available from this arm. The withdrawn claims")
        print("  stay withdrawn, which is a result about the design and not a failure to")
        print("  find one.")
    smallest = min((r["splits"] for r in rows if r["splits"]), default=0)
    if smallest:
        print("  Smallest attainable exact p at this depth: %.4f (2 of %d splits)."
              % (2.0 / smallest, smallest))
    if orphaned:
        print("")
        print("  ARM SHEETS WITH NO CONTROL TO SUBTRACT -- collected, paid for, unusable:")
        for model, n in sorted(orphaned.items()):
            print("    %-34s %d valid arm sheet(s), 0 usable control sheet(s)" % (model, n))
        print("  These models answer the arm and decline the control, so no contrast exists.")
    capped = sum(r["near_cap_arm_sheets"] for r in rows)
    print("")
    print("  DECLARED DIFFERENCE, carried per the pre-registration: the arms ran at")
    print("  max_tokens 8192 and this control at 40960. %d arm sheet(s) came within %d%% of"
          % (capped, int(NEAR_CAP * 100)))
    print("  their cap; the control is the side with room to spare.")
    return 0


def selftest():
    """The two pieces that can be checked against answers known without this code."""
    bad = 0

    # An exact two-sided permutation p on identical arms is 1.0 by construction.
    p, splits = exact_permutation_p([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])
    ok = p == 1.0 and splits == 20
    print("  %-46s p=%s splits=%s %s" % ("identical arms", p, splits,
                                         "OK" if ok else "FAIL"))
    bad += 0 if ok else 1

    # Complete separation at 5 v 5: only the observed split and its mirror are as extreme,
    # so p = 2/252 -- the floor the pre-registration names.
    p, splits = exact_permutation_p([10.0] * 5, [0.0] * 5)
    ok = splits == 252 and abs(p - 2.0 / 252) < 1e-12
    print("  %-46s p=%.6f splits=%d %s" % ("complete separation 5 v 5", p, splits,
                                           "OK" if ok else "FAIL want %.6f" % (2.0 / 252)))
    bad += 0 if ok else 1

    # An enumeration too large returns None rather than silently sampling.
    p, splits = exact_permutation_p(list(range(30)), list(range(30)))
    ok = p is None
    print("  %-46s %s %s" % ("refuses an enumeration it cannot do exactly",
                             "None" if ok else p, "OK" if ok else "FAIL"))
    bad += 0 if ok else 1

    # THE KILL RULE IS PER CONTRAST. A model with one large arm must not exempt its others.
    floor = 0.20
    effects = [0.60, 0.05]
    killed = [floor >= abs(e) for e in effects]
    ok = killed == [False, True]
    print("  %-46s %s %s" % ("per-contrast kill rule", killed, "OK" if ok else "FAIL"))
    bad += 0 if ok else 1

    # And the loader must read a real run rather than assert against its own assumptions.
    ctl = os.path.join(_SP.STUDY_DIR, "runs", CONTROL_RUN)
    if os.path.isdir(ctl):
        index = PA.pair_index(PA.load_bank())
        per, _prov, _cap = sheet_means(ctl, index, seed_filter=ARM_SEED)
        n = sum(len(v) for v in per.values())
        print("  %-46s %d cell(s), %d sheet(s)" % ("real control reads", len(per), n))
        if not per:
            print("    FAIL -- the loader returned nothing to test on")
            bad += 1
    else:
        print("  %-46s ABSENT, NOT checked" % "real control reads")
        bad += 1
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
