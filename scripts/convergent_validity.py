#!/usr/bin/env python3
"""Do the judged scale and the mechanical instrument measure the same thing?

WHY. This study has two instruments and validates neither against the other. The May corpus
scores free-text answers 1-5 with a four-judge panel. The August-September corpus records
forced-choice positions on 62 propositions with no model in the scoring path at all. Twenty-four
models appear in BOTH under conditions A and B, which makes a convergent-validity check possible
with no new collection: if both instruments measure a stance that moves under the condition
change, their A->B SHIFTS should track each other across models.

Shifts, not levels. The two instruments ask about different content and their absolute scales
are not comparable; what both are used to claim is that a condition moves a model.

    python scripts/convergent_validity.py
    python scripts/convergent_validity.py --json

No API calls. Arithmetic on records already on disk.
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import random
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eligibility import is_eligible  # noqa: E402
from studypaths import run_roots  # noqa: E402

BOOTSTRAP_N = 4000


def judged_scores(roots=None):
    out = collections.defaultdict(lambda: collections.defaultdict(list))
    for root in (roots or run_roots()):
        for path in glob.glob(os.path.join(str(root), "*", "scored", "*.jsonl")):
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    if is_eligible(rec) and rec.get("score_classifier") is not None:
                        out[rec.get("model")][rec.get("condition")].append(rec["score_classifier"])
    return out


def mechanical_positions(roots=None, temps=None):
    """Mean forced-choice position per run. NO MODEL IN THE SCORING PATH -- that is the point.

    `temps`, when passed, is filled with the set of sampling temperatures behind each
    (model, condition) arm.

    WHY THAT MATTERS. This pools every run for a (model, condition) with no key for
    the experiment, the temperature or the template. Measured: `x-ai/grok-4.3`'s
    mechanical A arm carries SIX temperature-0 runs and its B arm carries NONE, so
    the reported A->B shift is partly a temperature contrast wearing a condition
    label. An arm assembled from different sampling regimes is not one arm.
    """
    out = collections.defaultdict(lambda: collections.defaultdict(list))
    for root in (roots or run_roots()):
        for path in glob.glob(os.path.join(str(root), "*", "*.jsonl")):
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    if not rec.get("valid") or not rec.get("answers"):
                        continue
                    pos = [a["position"] for a in rec["answers"] if a.get("position") is not None]
                    if pos:
                        m, c = rec.get("model"), rec.get("condition")
                        out[m][c].append(st.mean(pos))
                        if temps is not None:
                            temps.setdefault((m, c), set()).add(rec.get("temperature"))
    return out


def temperature_mismatches(temps, conditions=("A", "B")):
    """Models whose two arms were collected at DIFFERENT temperatures.

    Returns [(model, {condition: {temps}})]. A non-empty result means the
    corresponding A->B shift confounds condition with sampling temperature and
    must not be read as a condition effect.
    """
    bad = []
    for m in sorted({m for (m, _c) in temps}):
        arms = {c: temps.get((m, c), set()) for c in conditions}
        present = {c: t for c, t in arms.items() if t}
        if len(present) == len(conditions):
            sets = list(present.values())
            if any(s != sets[0] for s in sets):
                bad.append((m, present))
    return bad


def pearson(xs, ys):
    mx, my = st.mean(xs), st.mean(ys)
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    den = (sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys)) ** 0.5
    return (num / den) if den else None


def shifts(judged, mech, min_records=1):
    rows = []
    for model in sorted(set(judged) & set(mech)):
        j, k = judged[model], mech[model]
        if not all(j.get(c) for c in ("A", "B")) or not all(k.get(c) for c in ("A", "B")):
            continue
        if min(len(j["A"]), len(j["B"])) < min_records:
            continue
        rows.append({"model": model,
                     "judged_shift": st.mean(j["B"]) - st.mean(j["A"]),
                     "mechanical_shift": st.mean(k["B"]) - st.mean(k["A"]),
                     "judged_n": len(j["A"]) + len(j["B"])})
    return rows


def analyse(rows, seed=20260912, n=BOOTSTRAP_N):
    if len(rows) < 5:
        return None
    xs = [r["judged_shift"] for r in rows]
    ys = [r["mechanical_shift"] for r in rows]
    r = pearson(xs, ys)
    rng = random.Random(seed)
    draws = []
    for _ in range(n):
        sample = [rng.choice(rows) for _ in rows]
        rr = pearson([s["judged_shift"] for s in sample],
                     [s["mechanical_shift"] for s in sample])
        if rr is not None:
            draws.append(rr)
    draws.sort()
    return {"r": r, "n_models": len(rows),
            "ci": (draws[int(0.025 * len(draws))], draws[int(0.975 * len(draws)) - 1])}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    temps = {}
    judged, mech = judged_scores(), mechanical_positions(temps=temps)
    temp_bad = temperature_mismatches(temps)
    rows = shifts(judged, mech)
    res = analyse(rows)
    if res is None:
        print("too few models measured both ways", file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps({"rows": rows, "result": res}, indent=1, default=list))
        return 0

    print("CONVERGENT VALIDITY -- the A->B shift, measured two ways")
    print("")
    # ARMS ASSEMBLED FROM DIFFERENT SAMPLING REGIMES ARE NOT ONE ARM.
    # grok-4.3's mechanical A arm carries six temperature-0 runs and its B arm
    # none, so that model's "condition effect" is partly a temperature contrast.
    if temp_bad:
        print("  WARNING: %d model(s) have A and B arms collected at DIFFERENT temperatures,"
              % len(temp_bad))
        print("  so their mechanical shift confounds condition with sampling regime:")
        for m, arms in temp_bad:
            detail = "   ".join("%s=%s" % (c, sorted(t, key=str))
                                for c, t in sorted(arms.items()))
            print("    %-32s %s" % (m.split("/")[-1], detail))
        print("")
    print("%-36s %13s %13s" % ("model", "judged 1-5", "mechanical"))
    for r in rows:
        print("  %-34s %+13.3f %+13.3f" % (r["model"], r["judged_shift"], r["mechanical_shift"]))
    print("")
    print("  Pearson r = %+.3f   95%% CI [%+.3f, %+.3f]   n = %d models"
          % (res["r"], res["ci"][0], res["ci"][1], res["n_models"]))
    print("")
    print("  ROBUSTNESS -- the same correlation at stricter minimum sample sizes:")
    for m in (20, 40):
        sub = shifts(judged, mech, min_records=m)
        sr = analyse(sub)
        if sr:
            print("    >= %d eligible judged records per condition: n=%d  r=%+.3f"
                  % (m, sr["n_models"], sr["r"]))
    print("")
    print("  A CI this wide does NOT say the instruments disagree. It says twenty-four models")
    print("  cannot tell whether they agree, which is a different and weaker statement -- and")
    print("  the one this study is obliged to make about its own scoring layer.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
