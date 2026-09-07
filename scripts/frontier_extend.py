#!/usr/bin/env python3
"""Extend the one-sitting arms onto the CURRENT frontier, which the frozen panel excludes.

THE PROBLEM THIS FIXES
----------------------
The wave panel is 31 models and frozen on purpose -- a time series needs a fixed panel or it
measures cohort composition instead of change. But the FLOORS do not need a frozen panel, they
need coverage, and they inherited the panel's:

    corpus                        166 models (154 hosted)
    wave panel                     31 models (26 hosted)
    one-sitting manipulation arm   25 models (20 frontier)

So §3's central claim about frontier models rests on twenty of them, while **23 first-party
major-vendor models released in the last 120 days are not in the protocol at all** -- including
three `gpt-5.6-*-pro` builds, `claude-fable-5`, `qwen3.8-flash`, `tencent/hy4-preview` and the
whole `hy-mt2` family. Most have six runs in the corpus from a single-date cross-section and
have never been measured at n=5 in one sitting.

Measuring old open-weight builds more carefully does not fix that. This does.

WHY A SEPARATE DIRECTORY
------------------------
The panel stays frozen and this collection is NOT part of it -- `wave.py --verify` never sees
these runs, and the time series is unaffected. They feed the floors, which is where coverage
matters, exactly as the targeted order collection does. The same reasoning puts this directory
in `refusal_table.DEFAULT_EXCLUDE`: a collection selected by RELEASE DATE cannot bias a floor
(release date is independent of how a model answers) but it is one-sided for the refusal arms.

    python scripts/frontier_extend.py --plan
    python scripts/frontier_extend.py --run --limit 8
    python scripts/frontier_extend.py --report
"""
from __future__ import annotations

import argparse
import collections
import datetime
import glob
import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from wave import WAVE_PARAMS, channel_for, load_panel  # noqa: E402

#: P and D, not A and D.
#:
#: A is the balance instruction and the 2026 flagships REFUSE it -- gpt-6-astra, gpt-6-astra-pro
#: and claude-fable-5.1 outright, and gemini-3.7/3.8-flash refuse A and B both. Measured on
#: wave 0, the A->D arm covers 6 of 11 current flagships; P->D covers 11 of 11. Collecting A
#: here would spend half the calls proving again that the newest models decline a balance
#: instruction, which §1 already reports, and would leave the manipulation arm selected by
#: which models will accept one.
#:
#: P->D is a narrower contrast than A->D -- content-free instruction against demanded
#: commitment, rather than demanded balance against demanded commitment -- and it is the one
#: that is measurable on the models this study is about.
CONDITIONS = ("P", "D")

#: Released within this many days. Release date is the selection criterion BECAUSE it cannot
#: correlate with how a model answers -- the same reason the frontier-v3 sweep used it.
RECENT_DAYS = 120

VENDORS = ("anthropic/", "openai/", "google/", "x-ai/", "deepseek/", "qwen/", "moonshotai/",
           "z-ai/", "mistralai/", "meta-llama/", "minimax/", "tencent/")


def outdir(date=None):
    date = date or datetime.date.today().isoformat()
    return os.path.join(STUDY, "runs", "%s-frontier-extend" % date)


def existing_dirs():
    return sorted(p for p in glob.glob(os.path.join(STUDY, "runs", "*-frontier-extend"))
                  if os.path.isdir(p))


#: THE ROSTER, chosen by deployment rather than by release date.
#:
#: Release date was the wrong rule: it selected `hy-mt2-1.8b`, `grok-build-0.1` and the
#: superseded qwen3.6/3.5 lines -- models nobody runs -- while the highest-value targets in the
#: catalogue are the three `gpt-5.6-*-pro` builds, because they are SAME-VERSION SIBLINGS of
#: three models already measured at n=5. The same-version null is currently 58 size variants and
#: 24 tier siblings drawn mostly from the gemini-2.5 and gpt-3.5 era; these give it current
#: pairs, which is the arm every drift claim in this literature rests on.
#:
#: Each entry says what it buys. Nothing is here because it was easy to add.
#: OPEN WEIGHTS ONLY. A first version of this roster led with three `gpt-5.6-*-pro` builds
#: because they are same-version siblings of models already measured -- analytically the
#: cheapest same-version pairs available, and the wrong call for this project. Closed frontier
#: builds are the expensive half of the catalogue, they cannot be inspected, ablated or
#: self-hosted, and a reader cannot reproduce a number measured on them without paying for it.
#: This study's argument is that open publishing and replication are what make the science
#: possible; the roster has to match.
#:
#: Selected for: open weights, currently deployed, and -- where possible -- a stock arm the
#: corpus already holds, so the marginal cost is one condition rather than two.
ROSTER = [
    # (model, why)
    ("qwen/qwen3.8-27b", "dense open-weight build people self-host; GGUF on disk for ablation"),
    ("qwen/qwen3.8-flash", "current Qwen flash tier, open weights"),
    ("qwen/qwen3.8-2.4t-a95b", "the large open-weight MoE"),
    ("tencent/hy4-preview", "current Hunyuan flagship, open weights, never measured"),
    ("minimax/minimax-m3", "vendor's newest, open weights, never at n=5"),
    ("moonshotai/kimi-k2.7-code", "coding-tuned sibling of the measured k2 line"),
]

#: Named exclusions, so the closed-model question is settled once rather than re-argued:
#:   openai/gpt-5.6-{luna,sol,terra}-pro   same-version siblings, and the most expensive
#:                                         listings in the catalogue. Analytically attractive,
#:                                         off-thesis, and not reproducible by a reader.
#:   anthropic/claude-{fable-5,sonnet-5}   ditto
#:   google/gemini-3.6-flash               ditto; also returns no valid sheet under any
#:                                         condition already measured
CLOSED_DEFERRED = ("openai/gpt-5.6-luna-pro", "openai/gpt-5.6-sol-pro",
                   "openai/gpt-5.6-terra-pro", "anthropic/claude-fable-5",
                   "anthropic/claude-sonnet-5", "google/gemini-3.6-flash")

#: Deliberately excluded, with the reason, so the next person does not re-litigate it:
#:   tencent/hy-mt2-{1.8b,7b,30b-a3b}  translation models; the instrument is political prose
#:   x-ai/grok-build-0.1               coding preview, not a conversational deployment
#:   qwen/qwen3.6-*, qwen3.5-*         superseded by the 3.8 line already in the roster
#:   openai/gpt-chat-latest            a moving alias, not a version -- it cannot anchor a pair
EXCLUDED = ("hy-mt2", "grok-build", "qwen3.6", "qwen3.5", "gpt-chat-latest")


def candidates(recent_days=RECENT_DAYS):
    """The roster above, filtered to what this checkout has not already measured."""
    return [(None, mid) for mid, _why in ROSTER]


def candidates_by_date(recent_days=RECENT_DAYS):
    """Recent first-party models the one-sitting protocol has never covered."""
    import roster_gap as G
    panel = set(load_panel()["models"])
    cut = datetime.date.today() - datetime.timedelta(days=recent_days)
    out = []
    for m in G.catalogue():
        mid = m.get("id")
        if not mid or mid in panel or not mid.startswith(VENDORS):
            continue
        if G.skip_reason(mid):
            continue
        created = m.get("created") or 0
        if not created:
            continue
        day = datetime.date.fromtimestamp(created)
        if day >= cut:
            out.append((day, mid))
    out.sort(reverse=True)
    return out


def collected(d):
    """(model, condition) -> distinct seeds among VALID runs."""
    seeds = collections.defaultdict(set)
    for p in glob.glob(os.path.join(d, "*.jsonl")):
        for line in io.open(p, encoding="utf-8", errors="replace"):
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if not r.get("valid") or r.get("seed") is None:
                continue
            seeds[(r.get("model"), r.get("condition"))].add(r["seed"])
    return {k: len(v) for k, v in seeds.items()}


def attempted(d):
    """(model, condition) -> records present, valid or not. Stops re-asking a spent cell."""
    seen = collections.Counter()
    for p in glob.glob(os.path.join(d, "*.jsonl")):
        for line in io.open(p, encoding="utf-8", errors="replace"):
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            seen[(r.get("model"), r.get("condition"))] += 1
    return seen


def todo(models, have, tried):
    want = WAVE_PARAMS["runs"]
    return [(m, c) for m in models for c in CONDITIONS
            if have.get((m, c), 0) < want and tried.get((m, c), 0) < want]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--days", type=int, default=RECENT_DAYS)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--delay", type=float, default=1.0)
    args = ap.parse_args(argv)

    p = WAVE_PARAMS
    cands = candidates(args.days)
    models = [mid for _d, mid in cands]

    prior = existing_dirs()
    d = outdir()
    if prior and todo(models, collected(prior[-1]), attempted(prior[-1])):
        d = prior[-1]
    os.makedirs(d, exist_ok=True)

    have, tried = collected(d), attempted(d)
    left = todo(models, have, tried)

    if args.plan:
        print("CANDIDATES -- first-party, released in the last %d days, not in the panel:"
              % args.days)
        for day, mid in cands:
            done = all(have.get((mid, c), 0) >= p["runs"] for c in CONDITIONS)
            print("   %-46s %s%s" % (mid, day, "   [done]" if done else ""))
        return 0

    if args.report or not args.run:
        cells = [(m, c) for m in models for c in CONDITIONS]
        done = [k for k in cells if have.get(k, 0) >= p["runs"]]
        spent = [k for k in cells
                 if have.get(k, 0) < p["runs"] and tried.get(k, 0) >= p["runs"]]
        print("FRONTIER EXTENSION -- %s" % os.path.basename(d))
        print("  %d model(s) released in the last %d days, conditions %s at n=%d"
              % (len(models), args.days, "+".join(CONDITIONS), p["runs"]))
        print("  %d of %d cell(s) at n=%d; %d to collect (%d call(s))"
              % (len(done), len(cells), p["runs"], len(left), len(left) * p["runs"]))
        if spent:
            print("  %d cell(s) had their runs and came back short -- not re-queued" % len(spent))
        return 0

    n = 0
    for (model, cond) in left:
        if args.limit and n >= args.limit:
            break
        cmd = [sys.executable, os.path.join(HERE, "run_compass.py"),
               "--model", model, "--condition", cond,
               "--runs", str(p["runs"]), "--temperature", str(p["temperature"]),
               "--seed", str(p["seed_base"]), "--max-tokens", str(p["max_tokens"]),
               "--template", p["template"], "--channel", channel_for(model),
               "--delay", str(args.delay), "--out", d]
        if p.get("seed_sweep"):
            cmd.append("--seed-sweep")
        r = subprocess.run(cmd, capture_output=True, text=True)
        tail = [l for l in (r.stdout or "").splitlines() if "runs valid" in l]
        print("  %-40s %s %s" % (model[-40:], cond,
                                 tail[-1].split(":")[-1].strip() if tail else "(no result)"))
        n += 1
    print("")
    print("collected %d cell(s); %d remain" % (n, len(left) - n))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
