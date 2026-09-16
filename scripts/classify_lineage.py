#!/usr/bin/env python3
"""Classify model-id pairs into version successors and same-version nulls.

WHY THIS GATES THE DRIFT ANALYSIS
---------------------------------
The lineage sweep groups models by stripping digits from their names, which merges three
different relationships into one bucket:

    claude-opus-4.6  vs  claude-opus-5      version successor   <- the measurement
    gemma-3-27b-it   vs  gemma-3-12b-it     size variant        <- a null
    kimi-k2          vs  kimi-k2-thinking   mode variant        <- a null
    gpt-4o-2024-05   vs  gpt-4o-2024-08     date snapshot       <- a null
    gpt-5.6-luna     vs  gpt-5.6-terra      tier sibling        <- a null

A size gap read as a version gap measures parameter count and calls it drift. That is the
single easiest way to produce a wrong headline from this dataset, so classification happens
before anything is plotted.

The nulls are not waste. They are the same-version control that made the first drift table
readable: gpt-5.6 luna/sol/terra showed no significant change and split in opposite
directions, while real version transitions ran 17/0, 9/0, 9/1. Every null pair collected is
another datum on how much two differently-named models differ for reasons that are not
version.

PARSING, AND WHERE IT IS UNCERTAIN
----------------------------------
Model naming is not a standard. This extracts four attributes and compares them:

    version   the numeric token bound to the family name   opus-4.6 -> 4.6, qwen3.5 -> 3.5
    size      parameter tokens                             235b-a22b, 27b, 8b
    mode      thinking / reasoning / instruct / chat
    snapshot  a date-like tail                             2024-05-13, 2507, 0905

Anything it cannot parse confidently is labelled UNKNOWN and excluded from the drift
analysis rather than guessed into a bucket. An unclassified pair is not a version pair.

Usage:
    python classify_lineage.py --runs runs/2026-08-31-lineage
    python classify_lineage.py --ids anthropic/claude-opus-4.6 anthropic/claude-opus-5
"""
from __future__ import annotations

import argparse
import collections
import glob
import io
import json
import os
import re
import sys

SIZE_RE = re.compile(r"\b(\d+(?:\.\d+)?)b(?:-a(\d+(?:\.\d+)?)b)?\b", re.I)
DATE_RE = re.compile(r"\b(20\d{2}-\d{2}-\d{2}|20\d{2}\d{2}\d{2}|\d{4})\b")
MODE_RE = re.compile(r"\b(thinking|reasoning|instruct|chat|it)\b", re.I)
# Tier words that name a sibling within one generation rather than a version step.
TIER_RE = re.compile(r"\b(luna|sol|terra|pro|mini|nano|flash|lite|max|plus|air|fast)\b", re.I)


def parse(model_id):
    """Split a model id into (stem, version, size, mode, snapshot, tier).

    A LOCAL ID HAS NO VENDOR PREFIX and this raised ValueError on every one of them --
    `gemma2:latest`, `llama3.1:8b`, `mistral:latest`, `phi4:latest`, `qwen2.5:14b`. It never
    surfaced because the only collection this was ever run over held hosted models alone.
    Point it at a panel with six local models, as the same-version arm now does, and it dies
    on the sixth.

    A local build genuinely has no lineage here: nothing in the panel is the same model at a
    different snapshot or tier, so the honest result is "no sibling relationship", not a
    crash and not a fabricated vendor.
    """
    if "/" not in model_id:
        # SAME SHAPE AS THE NORMAL RETURN. The docstring above says this returns a tuple; it
        # returns a dict, and the first version of this guard believed the docstring. `vendor`
        # is the local id itself so two different local models never compare equal, and the
        # lineage fields are None so no local pair can be classified as a sibling.
        stem = re.sub(r"[^a-z]+", " ", re.sub(r"[\d.]+", " ", model_id.lower())).strip()
        return {"id": model_id, "vendor": model_id.lower(), "stem": stem, "version": None,
                "size": None, "mode": None, "snapshot": None, "tier": None}
    vendor, name = model_id.split("/", 1)
    n = name.lower()

    snapshot = None
    m = DATE_RE.search(n)
    if m:
        # a 4-digit token is only a snapshot if it is not the version itself
        tok = m.group(1)
        if len(tok) > 4 or not re.search(r"[a-z]" + re.escape(tok), n):
            snapshot = tok
            n = n.replace(tok, " ")

    sizes = ["-".join(x for x in g if x) for g in SIZE_RE.findall(n)]
    size = sizes[0] if sizes else None
    n = SIZE_RE.sub(" ", n)

    modes = MODE_RE.findall(n)
    mode = modes[0].lower() if modes else None
    n = MODE_RE.sub(" ", n)

    # EVERY TIER TOKEN, NOT THE FIRST. This took `tiers[0]`, so `gpt-5.6-luna-pro` parsed as
    # tier `luna` -- identical to `gpt-5.6-luna` -- and the pair came back IDENTICAL and was
    # dropped from the same-version null. Those are the CLEANEST pairs available: the same
    # model at two tiers, nothing else varying. Three of them (luna, sol, terra against their
    # -pro siblings) were silently discarded, on an arm whose whole complaint is that nobody
    # reports this null.
    tiers = tuple(sorted(t.lower() for t in TIER_RE.findall(n)))
    tier = tiers or None
    n = TIER_RE.sub(" ", n)

    # version = the numeric token still attached to the remaining name
    version = None
    vm = re.search(r"(\d+(?:\.\d+)*)", n)
    if vm:
        version = vm.group(1)
    stem = re.sub(r"[\d.]+", " ", n)
    stem = re.sub(r"[^a-z]+", " ", stem).strip()
    return {"id": model_id, "vendor": vendor, "stem": stem, "version": version,
            "size": size, "mode": mode, "snapshot": snapshot, "tier": tier}


def vkey(v):
    """Sortable version tuple; None sorts first."""
    if not v:
        return ()
    return tuple(int(x) for x in v.split(".") if x.isdigit())


def classify(a, b):
    """Relationship between two parsed models. Returns (label, comparable_for_drift)."""
    if a["vendor"] != b["vendor"] or a["stem"] != b["stem"]:
        return "UNRELATED", False
    same = lambda k: a[k] == b[k]
    if not a["version"] or not b["version"]:
        return "UNKNOWN (no version parsed)", False
    if a["version"] != b["version"]:
        if same("size") and same("mode") and same("tier"):
            return "VERSION SUCCESSOR", True
        return "UNKNOWN (version differs AND size/mode/tier differs)", False
    # same version from here
    if not same("size"):
        return "size variant (null)", False
    if not same("mode"):
        return "mode variant (null)", False
    if not same("tier"):
        return "tier sibling (null)", False
    if not same("snapshot"):
        return "date snapshot (null)", False
    # TWO DIFFERENT IDS ARE NEVER IDENTICAL. Reaching here with distinct ids means the parser
    # could not tell them apart, and returning IDENTICAL drops the pair from the null set --
    # which is exactly how three luna/sol/terra tier pairs disappeared. A parse that cannot
    # distinguish two real models must say so rather than assert they are the same model.
    if a["id"] != b["id"]:
        return "UNKNOWN (ids differ but parse identically -- parser gap)", False
    return "IDENTICAL", False


def models_in(runs_dir):
    out = set()
    for p in glob.glob(os.path.join(runs_dir, "*.jsonl")):
        for line in io.open(p, encoding="utf-8"):
            if line.strip():
                out.add(json.loads(line)["model"])
                break
    return sorted(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--runs", default=None, help="run dir to read model ids from")
    ap.add_argument("--ids", nargs="*", default=None)
    ap.add_argument("--show-nulls", action="store_true")
    args = ap.parse_args(argv)

    ids = args.ids or (models_in(args.runs) if args.runs else None)
    if not ids:
        ap.error("give --runs or --ids")

    parsed = [parse(i) for i in ids]
    groups = collections.defaultdict(list)
    for p in parsed:
        groups[(p["vendor"], p["stem"], p["size"], p["mode"], p["tier"])].append(p)

    drift_pairs, nulls, unknown = [], [], []
    for _, members in groups.items():
        members.sort(key=lambda p: vkey(p["version"]))
        for i in range(len(members) - 1):
            a, b = members[i], members[i + 1]
            label, ok = classify(a, b)
            (drift_pairs if ok else (unknown if label.startswith("UNKNOWN") else nulls)).append(
                (a["id"], b["id"], label))
    # cross-group same-version pairs are the nulls worth having
    byver = collections.defaultdict(list)
    for p in parsed:
        byver[(p["vendor"], p["stem"], p["version"])].append(p)
    for _, members in byver.items():
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                label, ok = classify(members[i], members[j])
                if not ok and not label.startswith(("UNRELATED", "IDENTICAL", "UNKNOWN")):
                    nulls.append((members[i]["id"], members[j]["id"], label))

    # A pair can be reached by both the within-group and cross-group passes; dedupe on the
    # unordered pair so a null is not double-counted into the control's sample size.
    def dedupe(pairs):
        seen, out = set(), []
        for a, b, lab in pairs:
            k = tuple(sorted((a, b)))
            if k in seen:
                continue
            seen.add(k)
            out.append((a, b, lab))
        return out

    drift_pairs, nulls, unknown = dedupe(drift_pairs), dedupe(nulls), dedupe(unknown)

    print("VERSION SUCCESSORS -- usable for drift (%d pairs)" % len(drift_pairs))
    for a, b, _ in sorted(drift_pairs):
        print("  %-40s -> %s" % (a[:40], b))
    print()
    print("SAME-VERSION NULLS (%d pairs)" % len(nulls))
    if args.show_nulls:
        for a, b, lab in sorted(nulls):
            print("  %-38s vs %-32s %s" % (a[:38], b[:32], lab))
    else:
        c = collections.Counter(lab for _, _, lab in nulls)
        for lab, n in c.most_common():
            print("  %-28s %d" % (lab, n))
    print()
    print("UNCLASSIFIED -- excluded from drift (%d pairs)" % len(unknown))
    for a, b, lab in sorted(unknown)[:15]:
        print("  %-38s vs %-30s %s" % (a[:38], b[:30], lab))
    return 0


if __name__ == "__main__":
    sys.exit(main())
