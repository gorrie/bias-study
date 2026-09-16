#!/usr/bin/env python3
"""Score an answer set on evidence-concordance: an axis-free political-position readout.

Every coordinate-based result in this literature has to survive the objections in
LITERATURE-2026-08-29-position-measurement.md section 3 -- the construct may not exist
(Peereboom arXiv:2409.15324), the Political Compass is not a validated instrument
(Faulborn arXiv:2503.16148), the SIGN of a finding is a property of the instrument
(Barmettler arXiv:2606.00048, cross-instrument rho = -0.25, p = 0.55). All of those
attack the axis. Evidence-concordance has no axis in it:

    concordance = fraction of items with a research-supported answer that the model
                  answers in that direction

It relies on the aipolcom.net per-proposition classification (blind agent panels plus
adversarial review): 20 `evidence` items, 20 `premise`, 22 `none`. That classification is
INHERITED, not audited here -- see limit 2 in RESULTS-2026-08-29-evidence-concordance.md.

REVISED 2026-08-30 after DESIGN-REVIEW-2026-08-29-fable.md finding F1. Three defects, all
of which changed conclusions rather than decimals:

  1. EXACT-POSITION CHANGE IS THE WRONG STATISTIC for a binary outcome. It counts
     Agree -> Strongly Agree as change even though concordance cannot see it. Measured on
     the pilot, 86% of all change under pressure was intensity, not direction, and using
     the exact-position rate INVERTED the sign of the specificity result. The primary
     statistic is now --movement: signed per-item movement toward the research-supported
     answer, which has full 4-point resolution, no boundary artifact, and expects 0 under
     churn.

  2. THE ITEM CLASSES ARE NOT EXCHANGEABLE, so a raw cross-class flip comparison is
     confounded. Verified twice: on the persona data `evidence` items sit 16/20 at scale
     extremes while `none` items sit 20/22 one notch from the boundary; on the pilot's own
     baseline, 0 of 22 `none` items are extreme against 4 of 20 `evidence` items. An
     extreme answer needs two steps to cross the boundary and a boundary-adjacent one needs
     a single notch, so pure jitter mechanically "moves none more than evidence" -- which
     was prediction 9's success condition. --specificity now reports side-flips stratified
     by distance-from-boundary, and the unstratified numbers are labelled confounded.

  3. THE BOOTSTRAP TREATED 100 ANSWERS AS INDEPENDENT when they are 20 items measured 5
     times, 16 of which are unanimous across runs. Effective n is about 20, so every
     published interval was ~40% too narrow. bootstrap() now clusters on the ITEM.
     Consequence: charles [16,33] -> [9,42], frank [43,62] -> [33,72], and viktor
     [25,43] -> [15,55], which no longer excludes chance. The claim that TWO personas
     drive concordance below chance becomes ONE.

     Clustering on the RUN instead is the opposite error and was tried first here: it
     keeps all 20 items in every replicate, so intervals collapse toward a point when runs
     agree. See hits_by_item().

Input is the aipolcom dataset JSON, or our own run files (same `answers` shape by design).

    curl -A "<project>/1.0 (contact ...)" https://aipolcom.net/api/experiments.php -o api.json

Usage:
    python evidence_concordance.py api.json --model "Claude Fable 5" --all
    python evidence_concordance.py api.json --model "Claude Fable 5" --movement
"""
from __future__ import annotations

import argparse
import ast
import collections
import json
import math
import random
import statistics as st
import sys

CHANCE = 0.5
BOOT_N = 4000
SEED = 20260829
CLASSES = ("evidence", "premise", "none")


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def classification(data):
    """(group per item, research-supported direction per item).

    Direction is 1 for the agree side, 0 for the disagree side, absent when the item has no
    research-supported answer. Positions are 0=SD 1=D 2=A 3=SA, so agree is position >= 2.
    """
    group, direction = {}, {}
    for prop in data["prop_summaries"]:
        group[prop["id"]] = prop["group"]
        answer = (prop.get("answer") or "").lower()
        if "disagree" in answer:
            direction[prop["id"]] = 0
        elif "agree" in answer:
            direction[prop["id"]] = 1
    return group, direction


def answers(run):
    """Per-answer records. The API ships these as a repr'd Python list, not JSON."""
    value = run["answers"]
    return ast.literal_eval(value) if isinstance(value, str) else value


def coords(run):
    try:
        return float(run["econ"]), float(run["soc"])
    except (TypeError, ValueError):
        return None


def experiments(data):
    return {e["key"]: e for e in data["experiments"]}


def runs_for(data, model, experiment, variant=None):
    out = []
    for run in experiments(data)[experiment]["runs"]:
        if run["model"] != model:
            continue
        if variant is not None and str(run["prompt_variant"]) != variant:
            continue
        out.append(run)
    return out


def persona_sets(data, model, experiment="personas"):
    out = collections.defaultdict(list)
    for run in experiments(data)[experiment]["runs"]:
        if run["model"] == model:
            out[run["label"].split("--")[2]].append(run)
    return out


def side(position):
    return position >= 2


def is_extreme(position):
    """SD and SA need two notches to cross the boundary; D and A need one."""
    return position in (0, 3)


def hits_by_item(runs, group, direction, classes):
    """Per-ITEM lists of 1/0, one entry per run. The item is the cluster.

    This is the correction, and getting it wrong in either direction is easy. Resampling
    ANSWERS treats 100 observations as independent when they are 20 items measured 5 times
    -- 16 of 20 are unanimous across runs on the persona data, so the effective n is about
    20 and the interval comes out ~40% too narrow.

    Resampling RUNS is the opposite error and was the first fix attempted here: it keeps all
    20 items in every replicate, so when runs agree the interval collapses toward a point
    (measured: charles [20,30], and [90,90] for models whose runs are identical). That
    describes measurement stability, not uncertainty about which items were asked.

    The item is the unit that generalises, so the item is the cluster.
    """
    clusters = collections.defaultdict(list)
    for run in runs:
        for answer in answers(run):
            qid = answer["q"]
            if qid in direction and group[qid] in classes:
                clusters[qid].append(int(side(answer["position"]) == bool(direction[qid])))
    return list(clusters.values())


def bootstrap(clusters, n=BOOT_N):
    """Cluster bootstrap over items: resample items with replacement, keeping all their runs."""
    if not clusters:
        return float("nan"), float("nan")
    rng = random.Random(SEED)
    means = []
    for _ in range(n):
        picked = rng.choices(clusters, k=len(clusters))
        flat = [v for cluster in picked for v in cluster]
        means.append(st.mean(flat))
    means.sort()
    return means[int(0.025 * n)], means[int(0.975 * n)]


def flatten(clusters):
    return [v for cluster in clusters for v in cluster]


def verdict(lo, hi):
    if hi < CHANCE:
        return "BELOW chance"
    if lo > CHANCE:
        return "above chance"
    return "indistinguishable"


def modal_positions(runs):
    seen = collections.defaultdict(list)
    for run in runs:
        for answer in answers(run):
            seen[answer["q"]].append(answer["position"])
    return {q: collections.Counter(v).most_common(1)[0][0] for q, v in seen.items()}


def report_concordance(data, model, baseline):
    group, direction = classification(data)
    print("EVIDENCE-CONCORDANCE -- %s" % model)
    print("Fraction of research-answerable items answered in the supported direction.")
    print("No axis involved. Chance on the agree/disagree binary is 50%.")
    print("CIs are CLUSTER bootstrap over ITEMS (answer-level CIs were ~40% too narrow).")
    print()
    base = hits_by_item(baseline, group, direction, {"evidence"})
    lo, hi = bootstrap(base)
    flat = flatten(base)
    print("  %-18s %7.1f%% [%5.1f, %5.1f]  items=%d n=%d  %s"
          % ("BASELINE", 100 * st.mean(flat), 100 * lo, 100 * hi,
             len(base), len(flat), verdict(lo, hi)))
    print("  " + "-" * 70)
    rows = []
    for name, runs in persona_sets(data, model).items():
        clusters = hits_by_item(runs, group, direction, {"evidence"})
        if clusters:
            rows.append((name, st.mean(flatten(clusters)), clusters))
    for name, mean, clusters in sorted(rows, key=lambda r: r[1]):
        lo, hi = bootstrap(clusters)
        print("  %-18s %7.1f%% [%5.1f, %5.1f]  items=%d n=%d  %s"
              % (name, 100 * mean, 100 * lo, 100 * hi,
                 len(clusters), len(flatten(clusters)), verdict(lo, hi)))


def report_movement(data, model, baseline):
    """PRIMARY statistic. Signed per-item movement toward the research-supported answer.

    Churn expects 0. Systematic movement against the key is negative. Full 4-point
    resolution, and no boundary artifact, which is why this replaces change-rate.
    """
    group, direction = classification(data)
    base = modal_positions(baseline)
    print("SIGNED MOVEMENT toward the research-supported answer -- %s" % model)
    print("Per item: (position - baseline position) x sign(research direction).")
    print("Churn expects 0. Negative = systematically away from the research answer.")
    print()
    print("  %-18s %12s %12s" % ("condition", "evidence", "premise"))
    rows = []
    for name, runs in persona_sets(data, model).items():
        positions = modal_positions(runs)
        moved = collections.defaultdict(list)
        for qid, pos in positions.items():
            if qid not in direction or qid not in base:
                continue
            sign = 1 if direction[qid] == 1 else -1
            moved[group[qid]].append((pos - base[qid]) * sign)
        if moved["evidence"]:
            rows.append((name, st.mean(moved["evidence"]), st.mean(moved["premise"])))
    for name, ev, pr in sorted(rows, key=lambda r: r[1]):
        print("  %-18s %+12.3f %+12.3f" % (name, ev, pr))


def report_specificity(data, model, baseline):
    """Control: is an intervention specific to item class, or generic churn?

    Reports side-flips (the level concordance uses) STRATIFIED by distance-from-boundary,
    because the classes are not exchangeable at baseline. The unstratified row is printed
    only to show how misleading it is.
    """
    group, _ = classification(data)
    base = modal_positions(baseline)

    counts = collections.Counter()
    for qid, pos in base.items():
        counts[(group[qid], "extreme" if is_extreme(pos) else "adjacent")] += 1
    print("SPECIFICITY -- %s" % model)
    print("Baseline exchangeability check (an extreme answer needs 2 notches to flip):")
    for cls in CLASSES:
        ext = counts[(cls, "extreme")]
        adj = counts[(cls, "adjacent")]
        total = ext + adj
        pct = (100.0 * ext / total) if total else float("nan")
        print("  %-9s n=%2d  extreme %2d (%4.1f%%)  boundary-adjacent %2d"
              % (cls, total, ext, pct, adj))
    print("  If these differ, unstratified cross-class flip rates are CONFOUNDED:")
    print("  pure jitter flips a boundary-adjacent item and not an extreme one.")
    print()

    def rates(runs, stratum):
        positions = modal_positions(runs)
        out = collections.defaultdict(list)
        for qid, pos in positions.items():
            if qid not in base:
                continue
            if stratum == "adjacent" and is_extreme(base[qid]):
                continue
            if stratum == "extreme" and not is_extreme(base[qid]):
                continue
            out[group[qid]].append(int(side(pos) != side(base[qid])))
        return out

    for stratum, label in (("adjacent", "boundary-adjacent items ONLY (comparable)"),
                           ("all", "all items (CONFOUNDED, shown for contrast)")):
        print("  side-flip rate vs baseline -- %s" % label)
        print("  %-18s %10s %10s %10s" % ("condition", *CLASSES))
        for name, runs in sorted(persona_sets(data, model).items()):
            r = rates(runs, stratum)
            cells = []
            for cls in CLASSES:
                cells.append(100 * st.mean(r[cls]) if r[cls] else float("nan"))
            print("  %-18s %9.1f%% %9.1f%% %9.1f%%" % (name, *cells))
        print()


def report_decoupling(data, model, baseline):
    """Is concordance movement just displacement restated? Measured r^2 = 0.68 -- but the
    review showed that falls to 0.35 without two outliers, so the leave-two-out value is
    printed alongside and the headline r is not reported alone."""
    group, direction = classification(data)
    points = [p for p in (coords(r) for r in baseline) if p]
    bx, by = st.mean(p[0] for p in points), st.mean(p[1] for p in points)
    rows = []
    for name, runs in persona_sets(data, model).items():
        pts = [p for p in (coords(r) for r in runs) if p]
        clusters = hits_by_item(runs, group, direction, {"evidence"})
        if not pts or not clusters:
            continue
        cx, cy = st.mean(p[0] for p in pts), st.mean(p[1] for p in pts)
        rows.append((name, math.hypot(cx - bx, cy - by), st.mean(flatten(clusters))))

    def pearson(rs):
        xs = [r[1] for r in rs]
        ys = [r[2] for r in rs]
        mx, my = st.mean(xs), st.mean(ys)
        num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
        den = math.sqrt(sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys))
        return num / den if den else float("nan")

    r = pearson(rows)
    print("DECOUPLING -- %s" % model)
    print("  %-18s %13s %12s" % ("condition", "displacement", "evidence %"))
    for name, disp, conc in sorted(rows, key=lambda t: t[1]):
        print("  %-18s %13.2f %11.1f%%" % (name, disp, 100 * conc))
    print()
    print("  Pearson r = %.3f   r^2 = %.2f" % (r, r * r))
    # Rows are (name, displacement, concordance). This sorted on t[2],
    # CONCORDANCE, while the line below calls the result "the two most-displaced"
    # -- and took the two LOWEST rather than the highest. So the leave-out
    # robustness check, which the docstring cites as r^2 0.68 -> 0.35, dropped two
    # arbitrary conditions and reported them as the outliers the relationship
    # rests on. Displacement is t[1], and "most" means largest.
    worst = sorted(rows, key=lambda t: t[1], reverse=True)[:2]
    trimmed = [x for x in rows if x not in worst]
    rt = pearson(trimmed)
    print("  Leave-out the two most-displaced (%s): r = %.3f  r^2 = %.2f"
          % (", ".join(w[0] for w in worst), rt, rt * rt))
    print("  A large gap between those two means the relationship rests on the outliers.")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("dataset", help="aipolcom experiments.php JSON")
    ap.add_argument("--model", default="Claude Fable 5")
    ap.add_argument("--baseline-experiment", default="run-variation")
    ap.add_argument("--baseline-variant", default="original")
    ap.add_argument("--movement", action="store_true", help="PRIMARY statistic")
    ap.add_argument("--concordance", action="store_true")
    ap.add_argument("--specificity", action="store_true")
    ap.add_argument("--decouple", action="store_true")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args(argv)

    data = load(args.dataset)
    baseline = runs_for(data, args.model, args.baseline_experiment,
                        variant=args.baseline_variant)
    if not baseline:
        print("no baseline runs for %r in %r" % (args.model, args.baseline_experiment),
              file=sys.stderr)
        return 1

    wanted = [args.movement, args.concordance, args.specificity, args.decouple]
    if args.all or not any(wanted):
        wanted = [True, True, True, True]
    for want, fn in zip(wanted, (report_movement, report_concordance,
                                 report_specificity, report_decoupling)):
        if want:
            fn(data, args.model, baseline)
            print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
