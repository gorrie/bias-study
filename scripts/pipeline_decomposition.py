#!/usr/bin/env python3
"""What is rung 2's surviving effect actually made of?

WRITTEN BEFORE THE DATA EXISTS, and validated on synthetic input whose answer is
known. That ordering is the project's own rule and it is here for the reason the
rule gives: an estimator written afterwards gets shaped by the data it is first
run on, and nothing in the source shows you that happened.

    python scripts/pipeline_decomposition.py --selftest
    python scripts/pipeline_decomposition.py

THE QUESTION
------------
Rung 2 has one effect left after the 2026-09-14 audit. `B-Layered` moves Grok
up (+0.57 vs plain B) and does not move Opus, and `B-Layered minus B-STM` points
in OPPOSITE directions on the two models -- Opus -0.31, Grok +0.48. That contrast
is within-arm, so it survived both the token-budget confound and the proxy-path
confound. It is the finding that reaches the book.

But `B-Layered` bundles four things and two of them do nothing here:

    parseltongue   INERT on this instrument -- 0 of 240 requests
    stm            edits the ANSWER, a median of 16 characters
    godmode        a system prompt, plus temperature +0.1 / presence +0.15 /
                   frequency +0.1
    autotune       sampling parameters replaced outright by a context classifier

So the effect belongs to godmode and autotune, and no arm has ever run one
without the other. Until it does, the honest sentence is "a system prompt plus a
sampling change moved Grok and not Opus", which cannot say whether the models
are responding to an INSTRUCTION or to a TEMPERATURE. Those are different
findings about different things, and only one of them is about alignment.

WHAT THIS MEASURES
------------------
Against `B-Proxy` -- plain condition B through the same proxy with every
transform off, collected in the SAME SITTING, which is what makes these
contrasts clean where the older ones were not:

    B-Godmode  - B-Proxy    the instruction (plus its small parameter boost)
    B-Autotune - B-Proxy    the sampling change alone
    B-Layered  - B-Proxy    both together, plus STM's small edit

and an ADDITIVITY residual, `B-Layered - (B-Godmode + B-Autotune - B-Proxy)`,
which says whether the stack is the sum of its parts. A large residual means the
ingredients interact and neither single-arm number generalises to the stack.

The decisive limitation, stated rather than discovered later: `applyGodmodeBoost`
runs whenever godmode is set, so "system prompt with no parameter change" is not
reachable through this API. B-Godmode is the instruction PLUS a boost a quarter
the size of autotune's. If B-Godmode carries the effect and B-Autotune does not,
the instruction is the better explanation but not a proven one.
"""
from __future__ import annotations

import argparse
import collections
import glob
import io
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DECOMPOSITION_RUN = "2026-09-15-g0dm0d3-decomposition"
BASELINE_CONDITION = "B-Proxy"
ARMS = ("B-Godmode", "B-Autotune", "B-Layered")
BOOTSTRAP_N = 20000


def _load(run):
    from studypaths import run_roots
    import eligibility as E

    out = []
    for root in run_roots():
        pat = os.path.join(str(root), run, "scored", "**", "*.jsonl")
        for path in glob.glob(pat, recursive=True):
            for line in io.open(path, encoding="utf-8", errors="replace"):
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if E.is_eligible(rec):
                    out.append(rec)
    return out


def _cells(records):
    """Average replicates within (model, condition, question).

    The key MUST carry the condition. Keying on (model, question) alone pools the
    arms and differences a cell against itself -- the bug that shipped in six
    places in this repo, so it is spelled out rather than trusted to habit.
    """
    acc = collections.defaultdict(list)
    for r in records:
        acc[(r["model"], r.get("condition"), r["question_id"])].append(
            r["score_classifier"])
    return {k: st.mean(v) for k, v in acc.items()}, {k: len(v) for k, v in acc.items()}


def _boot(deltas, label, run):
    if not deltas:
        return None
    try:
        from studypaths import analysis_seed, stream
        rng = stream(analysis_seed(run), run, label)
    except Exception:
        import random
        rng = random.Random(20260915)
    k = len(deltas)
    means = sorted(st.mean([deltas[rng.randrange(k)] for _ in range(k)])
                   for _ in range(BOOTSTRAP_N))
    return (st.mean(deltas), means[int(0.025 * BOOTSTRAP_N)],
            means[int(0.975 * BOOTSTRAP_N)])


def decompose(run=DECOMPOSITION_RUN, records=None):
    recs = records if records is not None else _load(run)
    if not recs:
        return None
    means, depth = _cells(recs)
    by = collections.defaultdict(dict)
    for (model, cond, q), v in means.items():
        by[(model, cond)][q] = v

    models = sorted({m for m, _ in by})
    reps = sorted(set(depth.values()))
    out = {"run": run, "models": models, "baseline": BASELINE_CONDITION,
           "samples_per_cell": reps[0] if len(reps) == 1 else reps,
           "replicates_ragged": len(reps) > 1,
           "contrasts": [], "additivity": []}

    for m in models:
        base = by.get((m, BASELINE_CONDITION), {})
        if not base:
            continue
        for arm in ARMS:
            got = by.get((m, arm), {})
            d = [got[q] - base[q] for q in sorted(got) if q in base]
            ci = _boot(d, "%s|%s-vs-proxy" % (m, arm), run)
            if ci:
                out["contrasts"].append(
                    {"model": m, "contrast": "%s minus %s" % (arm, BASELINE_CONDITION),
                     "n": len(d), "effect": round(ci[0], 3), "lo": round(ci[1], 3),
                     "hi": round(ci[2], 3),
                     "excludes_zero": ci[1] > 0 or ci[2] < 0})

        # Additivity: does the stack equal the sum of its ingredients?
        g, a, l = (by.get((m, "B-Godmode"), {}), by.get((m, "B-Autotune"), {}),
                   by.get((m, "B-Layered"), {}))
        qs = [q for q in sorted(l) if q in g and q in a and q in base]
        d = [l[q] - ((g[q] - base[q]) + (a[q] - base[q]) + base[q]) for q in qs]
        ci = _boot(d, "%s|additivity" % m, run)
        if ci:
            out["additivity"].append(
                {"model": m, "n": len(qs), "residual": round(ci[0], 3),
                 "lo": round(ci[1], 3), "hi": round(ci[2], 3),
                 "additive": not (ci[1] > 0 or ci[2] < 0)})
    return out


def _selftest():
    """Synthetic records whose decomposition is known before the estimator runs.

    Model "pure/instruction": godmode adds exactly +0.60, autotune adds exactly
    0, and the stack is their sum. Model "pure/sampling" is the mirror image.
    An estimator that cannot recover a planted answer cannot be trusted with a
    real one.
    """
    PLANT = {"pure/instruction": {"B-Proxy": 3.0, "B-Godmode": 3.6,
                                  "B-Autotune": 3.0, "B-Layered": 3.6},
             "pure/sampling":    {"B-Proxy": 3.0, "B-Godmode": 3.0,
                                  "B-Autotune": 3.5, "B-Layered": 3.5}}
    recs = []
    for model, conds in PLANT.items():
        for cond, score in conds.items():
            for qi in range(10):
                for s in range(5):
                    recs.append({"model": model, "condition": cond,
                                 "question_id": "Q%02d" % qi, "sample_idx": s,
                                 "score_classifier": score})
    res = decompose(run="selftest", records=recs)
    checks = []

    def check(name, ok, detail=""):
        checks.append((name, ok, detail))

    by = {(c["model"], c["contrast"]): c for c in res["contrasts"]}
    check("replicates averaged, not pooled", res["samples_per_cell"] == 5,
          "got %r" % (res["samples_per_cell"],))
    check("instruction model: godmode recovers +0.60",
          abs(by[("pure/instruction", "B-Godmode minus B-Proxy")]["effect"] - 0.6) < 1e-9)
    check("instruction model: autotune recovers 0.00",
          abs(by[("pure/instruction", "B-Autotune minus B-Proxy")]["effect"]) < 1e-9)
    check("sampling model: godmode recovers 0.00",
          abs(by[("pure/sampling", "B-Godmode minus B-Proxy")]["effect"]) < 1e-9)
    check("sampling model: autotune recovers +0.50",
          abs(by[("pure/sampling", "B-Autotune minus B-Proxy")]["effect"] - 0.5) < 1e-9)
    check("stack recovers its single live ingredient",
          abs(by[("pure/instruction", "B-Layered minus B-Proxy")]["effect"] - 0.6) < 1e-9
          and abs(by[("pure/sampling", "B-Layered minus B-Proxy")]["effect"] - 0.5) < 1e-9)
    add = {a["model"]: a for a in res["additivity"]}
    check("a planted additive stack reads as additive",
          all(abs(a["residual"]) < 1e-9 and a["additive"] for a in add.values()),
          repr(add))
    # A non-additive plant must NOT read as additive: the stack under-delivers.
    for r in recs:
        if r["model"] == "pure/instruction" and r["condition"] == "B-Layered":
            r["score_classifier"] = 3.2
    res2 = decompose(run="selftest", records=recs)
    add2 = {a["model"]: a for a in res2["additivity"]}
    check("a planted INTERACTION does not read as additive",
          abs(add2["pure/instruction"]["residual"] + 0.4) < 1e-9
          and not add2["pure/instruction"]["additive"],
          repr(add2["pure/instruction"]))
    check("an empty corpus returns None, never an empty table",
          decompose(run="selftest", records=[]) is None)

    ok = all(c[1] for c in checks)
    for name, passed, detail in checks:
        print("  %s  %s%s" % ("PASS" if passed else "FAIL", name,
                              ("  -- " + detail) if detail and not passed else ""))
    print("%d/%d checks passed" % (sum(1 for c in checks if c[1]), len(checks)))
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--selftest", action="store_true",
                    help="validate the estimator against synthetic input with a "
                         "known answer; touches no corpus")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--run", default=DECOMPOSITION_RUN)
    args = ap.parse_args(argv)

    if args.selftest:
        return _selftest()

    res = decompose(args.run)
    if not res:
        print("decomposition run %s is not present (or not yet scored) in this tree."
              % args.run)
        print("This is not a pass -- the arm has not been collected here.")
        return 2
    if args.json:
        print(json.dumps(res, indent=2))
        return 0

    print("RUNG 2 DECOMPOSED -- what the layered stack's effect is made of")
    print("run: %s   baseline: %s (same sitting)" % (res["run"], res["baseline"]))
    spc = res["samples_per_cell"]
    print("%d models, %s per cell.\n"
          % (len(res["models"]),
             "RAGGED %r" % (spc,) if res["replicates_ragged"] else "%s sample(s)" % spc))
    print("  %-24s %-28s %3s %8s %-18s" % ("model", "contrast", "n", "effect", "95% interval"))
    for c in res["contrasts"]:
        print("  %-24s %-28s %3d %+8.2f [%+0.2f, %+0.2f]%s"
              % (c["model"].split("/")[-1], c["contrast"], c["n"], c["effect"],
                 c["lo"], c["hi"], "  EXCLUDES 0" if c["excludes_zero"] else ""))
    if res["additivity"]:
        print("\n  Additivity -- is the stack the sum of its ingredients?")
        for a in res["additivity"]:
            print("  %-24s residual %+0.2f [%+0.2f, %+0.2f]  %s"
                  % (a["model"].split("/")[-1], a["residual"], a["lo"], a["hi"],
                     "additive" if a["additive"] else "INTERACTS -- single-arm "
                     "numbers do not generalise to the stack"))
    print("\n  godmode is the instruction PLUS temperature +0.1 / presence +0.15 /")
    print("  frequency +0.1: applyGodmodeBoost runs whenever godmode is set, so an")
    print("  instruction with no parameter change is not reachable through this API.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
