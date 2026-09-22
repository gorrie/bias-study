#!/usr/bin/env python3
"""Roettger's union statistic and our pairwise rate, on the same sheets.

WHY BOTH, ON ONE ARM. Roettger et al. (ACL 2024) count propositions on which ANY of ten
paraphrases disagree about the side -- a union over k draws. This study's floors count items
differing between TWO administrations -- a pairwise difference. A k-way union is mechanically
several times larger on identical instability, so the two numbers are not comparable and no
rescaling makes them so. The paper cited them side by side as "the same magnitude" until
2026-09-21; that comparison was never available.

The fix is to hold the statistic fixed and vary the instrument, in both directions.
`replicate_rottger.py` runs OUR statistic on THEIR published completions. This runs THEIR
statistic on OURS, and reports our own beside it on exactly the same sheets, which is what
makes the ratio between them a measurement rather than an argument.

    python scripts/paraphrase_analysis.py
    python scripts/paraphrase_analysis.py --run 2026-09-18-paraphrase --json

Reads only. No API calls.
"""
from __future__ import annotations

import argparse
import collections
import glob
import io
import itertools
import json
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import studypaths as _SP  # noqa: E402

RUN = "2026-09-18-paraphrase"

#: Scale points are recorded 0..3 -- Strongly Disagree, Disagree, Agree, Strongly Agree. The
#: instrument is forced-choice with no neutral, so every answered item has a side and
#: "disagree about the side" is well defined: 0,1 are one side and 2,3 the other. Both
#: statistics below count SIDE changes, never intensity changes, because that is the unit
#: Roettger reports and the unit every instrument of this class scores.
SIDE_SPLIT = 2


def side_of(position):
    try:
        p = int(position)
    except (TypeError, ValueError):
        return None
    return 1 if p >= SIDE_SPLIT else 0


def sheets(run_dir):
    """{model: {template: {item_id: side}}} over valid sheets only."""
    out = collections.defaultdict(dict)
    for path in sorted(glob.glob(os.path.join(run_dir, "*.jsonl"))):
        with io.open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not line.strip():
                    continue
                rec = json.loads(line)
                if not rec.get("valid"):
                    continue
                sides = {}
                for ans in rec.get("answers") or []:
                    item, side = ans.get("q"), side_of(ans.get("position"))
                    if item is not None and side is not None:
                        sides[str(item)] = side
                if sides:
                    out[rec["model"]][rec.get("template")] = sides
    return out


def statistics_for(per_template):
    """(union, pairwise_median, n_templates, n_shared_items) for one model."""
    templates = sorted(per_template)
    if len(templates) < 2:
        return None
    shared = set(per_template[templates[0]])
    for t in templates[1:]:
        shared &= set(per_template[t])
    if not shared:
        return None

    # ROETTGER: an item counts once if ANY pair of templates disagrees about its side.
    union = sum(1 for item in shared
                if len({per_template[t][item] for t in templates}) > 1)

    # OURS: items differing between TWO administrations, over every template pair.
    pairwise = [sum(1 for item in shared if per_template[a][item] != per_template[b][item])
                for a, b in itertools.combinations(templates, 2)]
    return union, st.median(pairwise), len(templates), len(shared)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", default=RUN)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    run_dir = os.path.join(_SP.STUDY_DIR, "runs", a.run)
    if not os.path.isdir(run_dir):
        print("no such run: %s" % run_dir, file=sys.stderr)
        return 2

    data = sheets(run_dir)
    rows = []
    for model in sorted(data):
        got = statistics_for(data[model])
        if got:
            union, pair_med, n_t, n_items = got
            rows.append({"model": model, "union": union, "pairwise_median": pair_med,
                         "templates": n_t, "items": n_items})

    if not rows:
        print("CHECKED NOTHING -- no model carries two comparable templates. NOT a pass.")
        return 2

    if a.json:
        print(json.dumps({"run": a.run, "models": rows}, indent=2))
        return 0

    unions = [r["union"] for r in rows]
    pairs = [r["pairwise_median"] for r in rows]
    print("")
    print("  PARAPHRASE ARM -- two statistics, same sheets: %s" % a.run)
    print("  %d model(s), ten semantics-preserving templates, one presentation order." % len(rows))
    print("")
    print("  %-38s %8s %10s" % ("model", "union", "pairwise"))
    for r in sorted(rows, key=lambda x: -x["union"]):
        print("  %-38s %8d %10.1f   (%d templates, %d items)"
              % (r["model"][:38], r["union"], r["pairwise_median"], r["templates"], r["items"]))
    print("")
    print("  union     median %.1f  max %d   -- Roettger's statistic: items where ANY of the"
          % (st.median(unions), max(unions)))
    print("                                     templates disagree about the side")
    print("  pairwise  median %.1f  max %.0f   -- this study's: items differing between TWO"
          % (st.median(pairs), max(pairs)))
    print("                                     administrations")
    ratio = (st.median(unions) / st.median(pairs)) if st.median(pairs) else float("inf")
    print("")
    print("  The union runs %.1fx the pairwise rate on the SAME sheets." % ratio)
    print("  That ratio is why the two literatures' numbers cannot be compared directly, and")
    print("  it is a measurement here rather than an argument: same models, same instrument,")
    print("  same order, the only difference is which statistic is computed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
