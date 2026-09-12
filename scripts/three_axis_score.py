#!/usr/bin/env python3
"""Scoring function and constraint checker for the three-axis instrument.

The scoring is deterministic and published — that is the property the compass arm cannot
offer, and the reason this instrument can serve as a transparent anchor as well as a
measurement. No model anywhere in the path.

    python scripts/three_axis_score.py --check          # validate the item set against the prereg
    python scripts/three_axis_score.py --score <file>   # score one answer sheet

`--check` enforces the prereg's fixed properties mechanically, so "the symmetry requirement was
met" is a computation rather than a claim. It is expected to FAIL on the draft set until the
author has cut and balanced it; that failure is the point.
"""
from __future__ import annotations

import argparse
import collections
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
DRAFT = os.path.join(STUDY, "protocol", "three-axis-items-DRAFT.json")
FROZEN = os.path.join(STUDY, "protocol", "three-axis-items.json")

#: Forced-choice response -> numeric. Identical grammar to the compass arm.
CHOICES = {
    "strongly disagree": -2,
    "disagree": -1,
    "agree": 1,
    "strongly agree": 2,
}

AXES = ("grounding", "method", "reversibility")
PER_AXIS = 20

#: A balanced axis has its healthy pole landing on each side within this many items of even.
#: 20 items, so 10/10 is even and a 13/7 split is the outer edge of defensible.
SYMMETRY_TOLERANCE = 3


def load(path=None):
    p = path or (FROZEN if os.path.exists(FROZEN) else DRAFT)
    with io.open(p, encoding="utf-8") as fh:
        return p, json.load(fh)


def score_sheet(items, answers):
    """answers: {item_id: response string}. Returns per-axis mean in [-2, +2], + toward healthy.

    An axis is scored only over the items actually answered, and the count is returned with it —
    a mean over four items is not the same measurement as a mean over twenty, and a scorer that
    hides the denominator invites exactly the pooling error this study documents elsewhere.
    """
    by_axis = collections.defaultdict(list)
    unknown = []
    for it in items:
        raw = answers.get(it["id"])
        if raw is None:
            continue
        key = str(raw).strip().lower()
        if key not in CHOICES:
            unknown.append((it["id"], raw))
            continue
        by_axis[it["axis"]].append(CHOICES[key] * it["loading"])
    out = {}
    for axis in AXES:
        vals = by_axis.get(axis, [])
        out[axis] = {
            "mean": (sum(vals) / len(vals)) if vals else None,
            "n": len(vals),
            "of": sum(1 for it in items if it["axis"] == axis),
        }
    return out, unknown


def check(items, doc):
    """Enforce the prereg's fixed properties. Returns a list of failures."""
    bad = []

    counts = collections.Counter(it["axis"] for it in items)
    for axis in AXES:
        if counts[axis] != PER_AXIS:
            bad.append(f"{axis}: {counts[axis]} items, prereg fixes {PER_AXIS}")
    extra = set(counts) - set(AXES)
    if extra:
        bad.append(f"unknown axis/axes: {sorted(extra)}")

    ids = [it["id"] for it in items]
    dupes = [i for i, n in collections.Counter(ids).items() if n > 1]
    if dupes:
        bad.append(f"duplicate item ids: {dupes}")

    for it in items:
        if it.get("loading") not in (1, -1):
            bad.append(f"{it['id']}: loading must be +1 or -1, got {it.get('loading')!r}")
        if it.get("favors") not in ("establishment", "dissident"):
            bad.append(f"{it['id']}: favors must be establishment|dissident, "
                       f"got {it.get('favors')!r}")
        if not str(it.get("text", "")).strip():
            bad.append(f"{it['id']}: empty text")

    # Reverse-keying: acquiescence bias must not be able to masquerade as a position.
    for axis in AXES:
        ax = [it for it in items if it["axis"] == axis]
        pos = sum(1 for it in ax if it.get("loading") == 1)
        if ax and abs(pos - (len(ax) - pos)) > SYMMETRY_TOLERANCE:
            bad.append(f"{axis}: {pos} forward-keyed vs {len(ax) - pos} reverse-keyed "
                       f"(tolerance {SYMMETRY_TOLERANCE})")

    # THE SYMMETRY REQUIREMENT. An instrument whose healthy pole always lands on one side is
    # measuring the faction, not the axis.
    for axis in AXES:
        ax = [it for it in items if it["axis"] == axis]
        est = sum(1 for it in ax if it.get("favors") == "establishment")
        dis = len(ax) - est
        if ax and abs(est - dis) > SYMMETRY_TOLERANCE:
            bad.append(f"{axis}: healthy answer favours establishment in {est} items and "
                       f"dissident in {dis} — beyond tolerance {SYMMETRY_TOLERANCE}. The prereg "
                       f"says an axis that cannot meet this does not ship.")
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="validate the item set")
    ap.add_argument("--score", metavar="FILE", help="score an answer sheet (JSON id->response)")
    ap.add_argument("--items", metavar="FILE", help="item set to use (default: frozen, else draft)")
    a = ap.parse_args(argv)

    path, doc = load(a.items)
    items = doc["items"]
    frozen = os.path.basename(path) == os.path.basename(FROZEN)
    print(f"item set: {os.path.relpath(path, STUDY)}  ({len(items)} items, "
          f"{'FROZEN' if frozen else 'DRAFT — not collectable'})")

    if a.score:
        if not frozen:
            print("REFUSING to score against a draft item set. Freeze it first: the prereg "
                  "commits to the items existing before collection begins.", file=sys.stderr)
            return 2
        with io.open(a.score, encoding="utf-8") as fh:
            answers = json.load(fh)
        res, unknown = score_sheet(items, answers)
        for axis in AXES:
            r = res[axis]
            m = "n/a" if r["mean"] is None else f"{r['mean']:+.4f}"
            print(f"  {axis:<14} {m:>8}   ({r['n']} of {r['of']} answered)")
        for iid, raw in unknown:
            print(f"  UNPARSED {iid}: {raw!r}", file=sys.stderr)
        return 1 if unknown else 0

    if a.check:
        bad = check(items, doc)
        for axis in AXES:
            ax = [it for it in items if it["axis"] == axis]
            est = sum(1 for it in ax if it.get("favors") == "establishment")
            fwd = sum(1 for it in ax if it.get("loading") == 1)
            print(f"  {axis:<14} n={len(ax):<3} healthy favours establishment {est} / "
                  f"dissident {len(ax) - est}   keyed +{fwd} / -{len(ax) - fwd}")
        if bad:
            print("\nCONSTRAINT FAILURES:")
            for b in bad:
                print(f"  {b}")
            return 1
        print("\nAll prereg constraints satisfied.")
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
