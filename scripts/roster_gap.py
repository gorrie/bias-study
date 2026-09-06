#!/usr/bin/env python3
"""Which vendors have shipped a model we have never measured, and how far behind are we.

WHY THIS IS A TOOL AND NOT A ONE-OFF QUERY
------------------------------------------
A study whose subjects are frontier models goes stale on a schedule nobody controls. Measured
2026-09-05: seven of twelve tracked vendors had shipped a newest release the corpus had never
seen, four of them within the preceding four days -- `openai/gpt-6-astra` (released the day
before), `qwen/qwen3.8-max-0902`, `google/gemini-3.8-flash`, `anthropic/claude-fable-5.1`.

The corpus was NOT stale in the ordinary sense: every one of its 160 models was collected in
August or September 2026. It was stale in the sense that matters -- the frontier had moved and
the instrument had not followed it.

    python scripts/roster_gap.py                 # the table
    python scripts/roster_gap.py --commands      # run_compass invocations that close the gap
    python scripts/roster_gap.py --all-vendors   # include vendors we have never tracked

THERE IS DELIBERATELY NO --check
--------------------------------
A gate on "is the roster current" is red by construction: OpenRouter listed four new frontier
models in the four days before this file was written, and it will list more tomorrow. This
project has already learned what a permanently-red gate does -- `truncation_scan` sat unwired
for exactly that reason until its condition could actually go green. So this reports, and a
human decides when the gap is worth a collection.
"""
from __future__ import annotations

import argparse
import collections
import datetime
import io
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, HERE)

CATALOGUE = "https://openrouter.ai/api/v1/models"
# The PUBLIC identity, hardcoded. GitLab is the private working tree and is never
#: publicly reachable, so a User-Agent pointing there tells an operator whose logs we appear
#: in nothing they can act on. github.com/gorrie/bias-study is the published artifact.
UA = "bias-study-roster/1.0 (+https://github.com/gorrie/bias-study)"

#: Ids that are NOT subjects for this instrument, with the reason each is out. Named rather
#: than pattern-matched away, because a silent filter is how a real frontier model gets skipped
#: and nobody notices. Substring match against the model id.
NOT_A_SUBJECT = {
    "-guard": "safety classifier, not a conversational model -- it has no stance to measure",
    "-vision": "vision-experimental build; the instrument is 62 lines of text",
    "-embed": "embedding model, emits vectors not answers",
    "-rerank": "reranker, emits scores not answers",
    "-tts": "speech synthesis",
    "-image": "image generation",
    "whisper": "speech recognition",
}

#: Variant suffixes that are the same weights under different billing or availability. Measuring
#: them would inflate the roster without adding a subject.
VARIANT_SUFFIXES = (":batch", ":free", ":extended", ":nitro", ":online", ":floor")


def catalogue():
    req = urllib.request.Request(CATALOGUE, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.load(resp).get("data") or []


def measured():
    """Every model id in the corpus the paper describes."""
    import refusal_table as R
    import key_numbers as K
    return {r.get("model") for r in R.load(K.REFUSAL_EXCLUDE)}


def skip_reason(model_id):
    if model_id.startswith("~"):
        return "not a first-party listing"
    if model_id.endswith(VARIANT_SUFFIXES):
        return "billing/availability variant of the same weights"
    for needle, why in NOT_A_SUBJECT.items():
        if needle in model_id:
            return why
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--commands", action="store_true",
                    help="print the run_compass invocations that would close the gap")
    ap.add_argument("--all-vendors", action="store_true",
                    help="include vendors this study has never measured at all")
    ap.add_argument("--condition", default="A,B,D,P",
                    help="conditions for --commands (default: the four arms the refusal "
                         "analysis uses)")
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--out", default="", help="run directory for --commands")
    args = ap.parse_args(argv)

    have = measured()
    tracked = {m.split("/")[0] for m in have if "/" in m}

    by_vendor, skipped = collections.defaultdict(list), collections.Counter()
    for m in catalogue():
        mid = m.get("id") or ""
        why = skip_reason(mid)
        if why:
            skipped[why] += 1
            continue
        by_vendor[mid.split("/")[0]].append((m.get("created") or 0, mid))

    vendors = sorted(by_vendor) if args.all_vendors else sorted(tracked & set(by_vendor))
    today = datetime.date.today()
    gaps = []

    # SAY WHICH CORPUS. This compares against the FORCED-CHOICE corpus only -- the one
    # `refusal_table.load()` reads. A model can be measured in the May scored study and absent
    # here, and `meta-llama/llama-4-maverick` is exactly that: it carries a scored delta in the
    # May study and has never been through the 62-proposition instrument. Reporting it as "not
    # measured" without naming the corpus reads as an error in the tool rather than a real hole
    # in the coverage.
    print("ROSTER GAP -- the newest release each tracked vendor has shipped,")
    print("measured against the FORCED-CHOICE corpus (%d models). A model scored in the May"
          % len(have))
    print("study but never given the 62 propositions counts as NOT measured here, correctly.")
    print("")
    print("%-14s %-40s %-11s %6s  %s" % ("vendor", "newest", "released", "age", "measured?"))
    for v in vendors:
        created, mid = max(by_vendor[v])
        day = datetime.date.fromtimestamp(created) if created else None
        age = "%dd" % (today - day).days if day else "?"
        yes = mid in have
        if not yes:
            gaps.append((created, mid))
        print("%-14s %-40s %-11s %6s  %s"
              % (v, mid, day.isoformat() if day else "?", age, "yes" if yes else "** NO **"))

    print("")
    print("%d of %d tracked vendor(s) have shipped a newest release this corpus has never "
          "measured." % (len(gaps), len(vendors)))
    if skipped:
        print("Not counted as subjects:")
        for why, n in skipped.most_common():
            print("  %3d  %s" % (n, why))

    if args.commands and gaps:
        out = args.out or ("runs/%s-frontier" % today.isoformat())
        print("")
        print("# Serial, delayed, resumable. Same parameters as the last frontier collection,")
        print("# so the only factor that differs between it and this one is the model.")
        for _created, mid in sorted(gaps, reverse=True):
            for cond in args.condition.split(","):
                print("python scripts/run_compass.py --model %s --condition %s --runs %d "
                      "--temperature 0.7 --seed 20260830 --max-tokens 8192 --delay 2 --out %s"
                      % (mid, cond.strip(), args.runs, out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
