#!/usr/bin/env python3
"""One analysis entry point for forced-choice runs. Both instruments, all metrics.

WHY THIS EXISTS
---------------
Every result on 2026-08-29/30 was computed with a throwaway python one-liner written for
that result. That is how the bootstrap clustered on the wrong unit for a full day, how
exact-position change got used as the statistic for a binary outcome, and how a scanner
walked the wrong schema and reported 27,606 phantom escapes. Ad-hoc analysis is not
reproducible and it does not accumulate its own corrections.

Every metric here is the corrected version, and the reason it is the corrected version is
in the docstring beside it.

METRICS
-------
  --flips        side-flips vs a baseline condition. The binary statistic for a binary
                 outcome. Cross-class comparisons are stratified by distance-from-boundary,
                 because the classes are NOT exchangeable: `none` items sit next to the
                 boundary and `evidence` items sit at the extremes, so pure jitter
                 mechanically "moves none more than evidence".

  --movement     signed per-item movement toward the research-supported answer. PRIMARY.
                 Full 4-point resolution, no boundary artifact, churn expects 0. Replaces
                 exact-position change, which conflates intensity with direction and
                 inverted the sign of a result.

  --concordance  fraction of research-answerable items answered in the supported direction,
                 reported against the 50% CHANCE line rather than against baseline. Below
                 chance is interpretable; a fall from 95% to 76% is not. CIs are a cluster
                 bootstrap on the ITEM (answer-level was ~40% too narrow; run-level
                 collapses toward a point when runs agree).

  --acquiescence for mirrored instruments only. A matched pair is written so that agreeing
                 with one half is approximately disagreeing with the other. A model that
                 AGREES WITH BOTH is not taking a position, it is agreeing with the prompt.
                 An unmirrored instrument cannot measure this at all: with no
                 opposing half there is nothing to measure agree-with-both against.

Usage:
    python analyze.py runs/2026-08-30-vendors --baseline A
    python analyze.py runs/2026-08-30-v3 --items data/ratchet-battery.json --acquiescence
"""
from __future__ import annotations

import argparse
import collections
import glob
import io
import json
import os
import random
import statistics as st
import sys
import studypaths as _SP  # noqa: E402

CHANCE = 0.5
BOOT_N = 4000
BOOT_SEED = 20260830
CLASSES = ("evidence", "premise", "none")


def side(position):
    return position >= 2


def is_extreme(position):
    """SD and SA need two notches to cross the boundary; D and A need one."""
    return position in (0, 3)


def load_instrument(path):
    with io.open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    items, direction, group = {}, {}, {}
    for it in data["items"]:
        items[it["id"]] = it
        group[it["id"]] = it.get("research_group")
        answer = (it.get("research_answer") or "").lower()
        if "disagree" in answer:
            direction[it["id"]] = 0
        elif "agree" in answer:
            direction[it["id"]] = 1
    return data, items, group, direction


def load_runs(root):
    """(model, condition) -> list of {item: position}, valid runs only."""
    paths = ([root] if os.path.isfile(root)
             else sorted(glob.glob(os.path.join(root, "**", "*.jsonl"), recursive=True)))
    out = collections.defaultdict(list)
    for path in paths:
        for line in io.open(path, encoding="utf-8"):
            if not line.strip():
                continue
            rec = json.loads(line)
            if not _SP.is_run_record(rec) or not rec.get("valid"):
                continue
            out[(rec["model"], rec["condition"])].append(
                {a["q"]: a["position"] for a in rec["answers"]})
    return out


def load_runs_by_order(root):
    """(model, condition, shuffle_seed) -> answers. Keeps presentation orders SEPARATE.

    load_runs() keys on (model, condition) and pools everything under it, which would take
    the modal answer ACROSS presentation orders and average away the exact effect being
    measured. Order comparisons must not go through it.
    """
    paths = ([root] if os.path.isfile(root)
             else sorted(glob.glob(os.path.join(root, "**", "*.jsonl"), recursive=True)))
    out = {}
    for path in paths:
        for line in io.open(path, encoding="utf-8"):
            if not line.strip():
                continue
            rec = json.loads(line)
            if not _SP.is_run_record(rec) or not rec.get("valid"):
                continue
            key = (rec["model"], rec["condition"], rec.get("shuffle_seed"))
            out[key] = {a["q"]: a["position"] for a in rec["answers"]}
    return out


def report_order(roots):
    """How much does presentation order alone move the answers?

    Same model, same condition, temperature 0 with a fixed sampling seed -- so the ONLY
    difference between two cells here is the order the items were printed in. This is the
    direct test of Dominguez-Olmedo et al. on our instrument, and it was never run before
    2026-08-30.
    """
    cells = {}
    for root in roots:
        cells.update(load_runs_by_order(root))
    by_mc = collections.defaultdict(dict)
    for (model, cond, shuf), ans in cells.items():
        by_mc[(model, cond)][shuf] = ans

    print("ORDER EFFECT  (same model, same condition, temp 0 -- only presentation differs)")
    print("Baseline order is shuffle_seed None. Each column is items answered differently.")
    print()
    print("  %-24s %-5s %8s %s" % ("model", "cond", "orders", "pairwise disagreement"))
    for (model, cond), orders in sorted(by_mc.items()):
        if len(orders) < 2:
            continue
        keys = sorted(orders, key=lambda k: (k is not None, k))
        pairs = []
        for i, a in enumerate(keys):
            for b in keys[i + 1:]:
                shared = set(orders[a]) & set(orders[b])
                d = sum(1 for q in shared if side(orders[a][q]) != side(orders[b][q]))
                pairs.append((a, b, d, len(shared)))
        summary = " ".join("%s/%s:%d" % (a if a is not None else "-",
                                         b if b is not None else "-", d)
                           for a, b, d, _ in pairs)
        worst = max(p[2] for p in pairs)
        n = pairs[0][3]
        print("  %-24s %-5s %8d %s   (worst %d/%d)"
              % (model[:24], cond, len(keys), summary, worst, n))
    print()
    print("  Read against the model's own floor. Anything at or above the seed-sweep")
    print("  floor for that model and condition is order noise, not a position.")
    print()


def modal(runs):
    """Modal answer per item across runs. n=1 at temperature 0 is the normal case."""
    acc = collections.defaultdict(list)
    for run in runs:
        for qid, pos in run.items():
            acc[qid].append(pos)
    return {q: collections.Counter(v).most_common(1)[0][0] for q, v in acc.items()}


def bootstrap_items(clusters, n=BOOT_N):
    """Cluster bootstrap over ITEMS -- the unit that generalises."""
    if not clusters:
        return float("nan"), float("nan")
    rng = random.Random(BOOT_SEED)
    means = []
    for _ in range(n):
        flat = [v for c in rng.choices(clusters, k=len(clusters)) for v in c]
        means.append(st.mean(flat))
    means.sort()
    return means[int(0.025 * n)], means[int(0.975 * n)]


def report_flips(data, group, direction, runs, baseline):
    print("SIDE-FLIPS vs condition %s  (binary statistic for a binary outcome)" % baseline)
    print("Stratified to boundary-adjacent items, because the classes are not exchangeable.")
    print()
    models = sorted({m for m, _ in runs})
    print("  %-46s %-5s %8s %26s" % ("model", "cond", "all", "boundary-adjacent by class"))
    for model in models:
        base = modal(runs.get((model, baseline), []))
        if not base:
            continue
        for (m, cond), rs in sorted(runs.items()):
            if m != model or cond == baseline:
                continue
            cur = modal(rs)
            allf = sum(1 for q in base if q in cur and side(cur[q]) != side(base[q]))
            byc = collections.defaultdict(list)
            for q in base:
                if q not in cur or is_extreme(base[q]) or group.get(q) not in CLASSES:
                    continue
                byc[group[q]].append(int(side(cur[q]) != side(base[q])))
            cells = " ".join(
                "%s %s" % (c[:2], ("%4.0f%%" % (100 * st.mean(byc[c]))) if byc[c] else "  --")
                for c in CLASSES)
            print("  %-46s %-5s %8s   %s" % (model[:46], cond, "%d/%d" % (allf, len(base)), cells))
    print()


def report_movement(data, group, direction, runs, baseline):
    print("SIGNED MOVEMENT toward the research-supported answer  (PRIMARY; churn expects 0)")
    if not direction:
        print("  instrument carries no research key -- not computable")
        print()
        return
    print()
    print("  %-46s %-5s %12s %12s" % ("model", "cond", "evidence", "premise"))
    for model in sorted({m for m, _ in runs}):
        base = modal(runs.get((model, baseline), []))
        if not base:
            continue
        for (m, cond), rs in sorted(runs.items()):
            if m != model or cond == baseline:
                continue
            cur = modal(rs)
            mv = collections.defaultdict(list)
            for q, pos in cur.items():
                if q not in direction or q not in base:
                    continue
                mv[group.get(q)].append((pos - base[q]) * (1 if direction[q] == 1 else -1))
            f = lambda c: ("%+12.3f" % st.mean(mv[c])) if mv[c] else "          --"
            print("  %-46s %-5s %s %s" % (model[:46], cond, f("evidence"), f("premise")))
    print()


def report_concordance(data, group, direction, runs, baseline):
    print("EVIDENCE-CONCORDANCE vs the 50%% chance line  (no axis involved)")
    if not direction:
        print("  instrument carries no research key -- not computable")
        print()
        return
    print()
    print("  %-46s %-5s %9s %16s %s" % ("model", "cond", "rate", "95% CI (item)", "verdict"))
    for (model, cond), rs in sorted(runs.items()):
        clusters = collections.defaultdict(list)
        for run in rs:
            for q, pos in run.items():
                if q in direction and group.get(q) == "evidence":
                    clusters[q].append(int(side(pos) == bool(direction[q])))
        cl = list(clusters.values())
        if not cl:
            continue
        rate = st.mean(v for c in cl for v in c)
        lo, hi = bootstrap_items(cl)
        verdict = ("BELOW chance" if hi < CHANCE else
                   "above chance" if lo > CHANCE else "indistinguishable")
        print("  %-46s %-5s %8.1f%% [%5.1f, %5.1f]   %s"
              % (model[:46], cond, 100 * rate, 100 * lo, 100 * hi, verdict))
    print()


def report_acquiescence(data, items, runs):
    """Mirrored instruments only. Agreeing with both halves is not a position."""
    pairs = {}
    for it in data["items"]:
        mirror = it.get("mirror_of")
        if mirror and it["id"] < mirror:
            pairs[it["id"]] = mirror
    print("ACQUIESCENCE  (mirrored pairs: agreeing with BOTH halves is not a position)")
    if not pairs:
        print("  instrument is not mirrored -- not computable")
        print("  (an unmirrored instrument cannot measure this: with no opposing half")
        print("   there is nothing for agree-with-both to be measured against)")
        print()
        return
    print()
    print("  %-46s %-5s %10s %10s %10s" % ("model", "cond", "agree-both", "disag-both", "opposed"))
    for (model, cond), rs in sorted(runs.items()):
        cur = modal(rs)
        ab = db = op = 0
        for a, b in pairs.items():
            if a not in cur or b not in cur:
                continue
            if side(cur[a]) and side(cur[b]):
                ab += 1
            elif not side(cur[a]) and not side(cur[b]):
                db += 1
            else:
                op += 1
        tot = ab + db + op
        if not tot:
            continue
        print("  %-46s %-5s %9.0f%% %9.0f%% %9.0f%%"
              % (model[:46], cond, 100 * ab / tot, 100 * db / tot, 100 * op / tot))
    print()
    print("  'opposed' is the only column that reflects a position. The other two are the")
    print("  model agreeing, or disagreeing, with whatever it was handed.")
    print()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("root", help="run directory or a single .jsonl")
    ap.add_argument("--also", action="append", default=[],
                    help="extra run roots, for --order comparisons across dirs")
    ap.add_argument("--items", default=None, help="instrument JSON (default: the Ratchet battery)")
    ap.add_argument("--baseline", default="A", help="baseline condition (default A)")
    ap.add_argument("--flips", action="store_true")
    ap.add_argument("--movement", action="store_true")
    ap.add_argument("--concordance", action="store_true")
    ap.add_argument("--acquiescence", action="store_true")
    ap.add_argument("--order", action="store_true",
                    help="presentation-order effect; keeps orders separate")
    args = ap.parse_args(argv)

    here = os.path.dirname(os.path.abspath(__file__))
    # THE LIVE INSTRUMENT. This defaulted to `data/compass-propositions.json`, the retired
    # external questionnaire, which left `data/` on 2026-09-17 -- so an invocation without
    # `--items` would now raise FileNotFoundError, and before that it silently interpreted
    # battery sheets against a 62-item bank they were never collected on.
    items_path = args.items or os.path.join(here, "..", "data", "ratchet-battery.json")
    data, items, group, direction = load_instrument(items_path)
    runs = load_runs(args.root)
    if not runs:
        print("no valid answer-sheet records under %s" % args.root, file=sys.stderr)
        return 1

    print("instrument: %s  (%d items, %d with a research key)"
          % (data.get("instrument", os.path.basename(items_path)), len(items), len(direction)))
    print("runs: %d cells, %d valid runs" % (len(runs), sum(len(v) for v in runs.values())))
    print()

    if args.order:
        report_order([args.root] + args.also)
        return 0

    wanted = [args.flips, args.movement, args.concordance, args.acquiescence]
    if not any(wanted):
        wanted = [True, True, True, True]
    for want, fn in zip(wanted, (
            lambda: report_flips(data, group, direction, runs, args.baseline),
            lambda: report_movement(data, group, direction, runs, args.baseline),
            lambda: report_concordance(data, group, direction, runs, args.baseline),
            lambda: report_acquiescence(data, items, runs))):
        if want:
            fn()
    return 0


if __name__ == "__main__":
    sys.exit(main())
