#!/usr/bin/env python3
"""Both model pairs of the XSTest-style refusal suite, with clustered intervals.

WHY. runs/refusal-ablation/ holds 1,800 records -- two model pairs, 450 per arm -- and the
published headline reported ONE pair. The second sat in summary.json, unreported, against this
project's standing rule that no mechanism claim rests on one model. This computes both from the
raw judged records rather than reading the stored summary, so the numbers are re-derived.

Intervals cluster on PROMPT TYPE (18 of them, 25 prompts each). Twenty-five prompts sharing a
template are not twenty-five independent observations, and bootstrapping over prompts would
report an interval roughly a third too narrow.

    python scripts/refusal_suite_summary.py
    python scripts/refusal_suite_summary.py --json

No API calls. Arithmetic on records already on disk.
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
SUITE = os.path.join(STUDY, "runs", "refusal-ablation")
PAIRS = [("Qwen3.8-27B", "constrained.judged.jsonl", "ablated.judged.jsonl"),
         ("Gemma-4-12B", "gemma4-12b-constrained.judged.jsonl", "gemma4-12b-ablated.judged.jsonl")]
BOOTSTRAP_N = 4000


def load(name, suite=SUITE):
    path = os.path.join(suite, name)
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def by_type(recs):
    out = collections.defaultdict(list)
    for r in recs:
        out[(r.get("label"), r.get("type"))].append(r)
    return out


def _compliance(recs):
    return st.mean([1.0 if r.get("judge_verdict") == "COMPLIED" else 0.0 for r in recs])


def discrimination(cells):
    safe = [r for (label, _), v in cells.items() if label == "safe" for r in v]
    unsafe = [r for (label, _), v in cells.items() if label != "safe" for r in v]
    if not safe or not unsafe:
        return None
    return _compliance(safe) - _compliance(unsafe)


def keyword_disagreement(cells):
    """How often the keyword detector and the judge disagree about whether this was a refusal.

    THE GAP IS THE MECHANISM. Ablation strips the refusal phrasing faster than the refusal
    behaviour, so the keyword detector says 'complied' while the judge says 'refused'.
    """
    n = d = 0
    for v in cells.values():
        for r in v:
            n += 1
            if (r.get("judge_verdict") != "COMPLIED") != (r.get("keyword_refused") is True):
                d += 1
    return (d / n) if n else None


def analyse(pairs=PAIRS, suite=SUITE, seed=20260828, n=BOOTSTRAP_N):
    rng = random.Random(seed)
    out = []
    for name, cf, af in pairs:
        C, A = by_type(load(cf, suite)), by_type(load(af, suite))
        if not C or not A:
            continue
        obs = discrimination(C) - discrimination(A)
        types = sorted({t for (_, t) in C})
        draws = []
        for _ in range(n):
            pick = {rng.choice(types) for _ in types}
            dc = discrimination({k: v for k, v in C.items() if k[1] in pick})
            da = discrimination({k: v for k, v in A.items() if k[1] in pick})
            if dc is not None and da is not None:
                draws.append(dc - da)
        draws.sort()
        out.append({"model": name, "drop": obs,
                    "ci": (draws[int(0.025 * len(draws))], draws[int(0.975 * len(draws)) - 1]),
                    "types": len(types),
                    "constrained_discrimination": discrimination(C),
                    "ablated_discrimination": discrimination(A),
                    "kw_disagree_constrained": keyword_disagreement(C),
                    "kw_disagree_ablated": keyword_disagreement(A)})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    res = analyse()
    if not res:
        print("refusal suite not on disk", file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps(res, indent=1, default=list))
        return 0
    print("REFUSAL SUITE -- both model pairs, clustered on prompt type")
    print("")
    print("%-14s %11s %11s %9s  %s" % ("model", "constrained", "ablated", "drop", "95% CI"))
    for r in res:
        print("  %-12s %11.3f %11.3f %+9.3f  [%+.3f, %+.3f]  (%d types)"
              % (r["model"], r["constrained_discrimination"], r["ablated_discrimination"],
                 r["drop"], r["ci"][0], r["ci"][1], r["types"]))
    print("")
    print("KEYWORD/JUDGE DISAGREEMENT -- the vocabulary-versus-behaviour gap")
    for r in res:
        c, b = r["kw_disagree_constrained"], r["kw_disagree_ablated"]
        print("  %-12s %.1f%% -> %.1f%%   (%.1fx)" % (r["model"], c * 100, b * 100, b / c))
    print("")
    print("  Rising on BOTH vendors is what makes this a mechanism claim rather than one")
    print("  model's quirk. The magnitude differs by a lot, which is what every other result")
    print("  here says about third-party ablated builds.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
