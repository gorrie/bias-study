#!/usr/bin/env python3
"""Generate every measured floor, in BOTH statistics, from raw runs only.

WHY THIS EXISTS
---------------
The floors were quoted in mixed units. A same-version null of "p90 22" was placed beside an
order effect of "24 of 62" as though the two were comparable. They are not: the null was
computed as |b-c| on ENDPOINT status (Strongly Agree / Strongly Disagree), while order,
quantisation, ablation and the prompt conditions were all counted as SIDE-flips (crossing
the agree/disagree boundary).

Re-derived here, the same-version null is median 5, p90 12, max 24 in side-flip units --
roughly half the number that was published, in the currency the rest of the table uses.

No number in this project's floor table should be typed by hand again. Every row below is
computed from `runs/`, in both statistics, so a unit mix cannot recur silently.

THE TWO STATISTICS
------------------
  side-flip    the item crossed the agree/disagree boundary. Binary outcome, binary
               statistic. This is the unit for anything compared against concordance.
  endpoint     the item gained or lost a Strongly answer. Finer-grained, and the unit the
               suppression work uses, because suppression is about intensity not direction.

They are different questions and neither is wrong. Mixing them in one table is.

Usage:
    python floor_table.py
    python floor_table.py --markdown
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

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from check_arm_match import INELIGIBLE_PAIRS  # noqa: E402
from classify_lineage import classify, parse  # noqa: E402

BOOT_N = 2000
BOOT_SEED = 20260831


def ext(p):
    return p in (0, 3)


def side(p):
    return p >= 2


def _default_key(r):
    return (r["model"], r["condition"], r.get("shuffle_seed"))


def _template_key(r):
    """Cell key for the paraphrase arm: the template is what varies, order is held fixed."""
    return (r["model"], r["condition"], r.get("template", "T01"))


#: What load() threw away on the last call, and why. A dropped run is a measurement that does
#: not reach a floor, and until 2026-09-04 every one of them vanished without a trace: the
#: OBLITERATED Qwen3.8-27B's entire ablated arm -- four valid, fully parsed 62-item sheets --
#: was discarded as degenerate and no output anywhere said a pair had lost its arm.
#: Read it after a load, or call load_report().
DROPPED = collections.Counter()

#: Run identities already counted into DROPPED. Several floors glob overlapping directories --
#: the order floor reads six run dirs, the condition floor reads one of the same six -- so a
#: naive counter reports 376 drops for a corpus that has far fewer. A count that inflates with
#: the number of callers is not a count.
_DROPPED_SEEN = set()


def _count_drop(reason, rec):
    ident = (rec.get("model"), rec.get("condition"), rec.get("collected_at"),
             rec.get("shuffle_seed"), rec.get("template"))
    if ident in _DROPPED_SEEN:
        return
    _DROPPED_SEEN.add(ident)
    DROPPED[reason] += 1


def load_report():
    """One line per reason load() discarded a run, for a floor to print alongside its number."""
    return sorted(DROPPED.items(), key=lambda kv: (-kv[1], kv[0]))


def load(pattern, condition=None, key=None):
    """Answer sheets grouped into cells.

    `key` chooses the grouping and defaults to the historical (model, condition, shuffle_seed).
    It is a parameter rather than a second loader because the parse, the validity filter and
    the degenerate-sheet rule are the same for every arm, and a copy of this loop is a copy of
    three rules that must not drift -- the template arm needs a different GROUPING, not
    different loading.

    Drops are counted into DROPPED rather than being silent. The degenerate-sheet rule in
    particular is CORRECT and consequential: a model that answers every one of 62 items
    identically has no position to compare, and scoring that against a normal sheet reports a
    huge side-flip count that reads as an effect. Excluding it is right; excluding it invisibly
    is how a pair loses an arm without anyone noticing.
    """
    key = key or _default_key
    cells = collections.defaultdict(list)
    for p in glob.glob(os.path.join(STUDY, pattern), recursive=True):
        for line in io.open(p, encoding="utf-8"):
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("schema") != "compass-run/1":
                continue
            if not r.get("valid"):
                _count_drop("invalid run (%s)" % (r.get("failure_mode") or "unclassified"), r)
                continue
            if condition and r["condition"] != condition:
                continue
            vals = [a["position"] for a in r["answers"]]
            if len(set(vals)) == 1:
                _count_drop("degenerate sheet, all %d: %s" % (vals[0], r.get("model")), r)
                continue
            cells[key(r)].append({a["q"]: a["position"] for a in r["answers"]})
    return cells


def modal(runs):
    acc = collections.defaultdict(list)
    for r in runs:
        for q, v in r.items():
            acc[q].append(v)
    return {q: collections.Counter(v).most_common(1)[0][0] for q, v in acc.items()}


def both_stats(a, b):
    shared = [q for q in a if q in b]
    sideflips = sum(1 for q in shared if side(a[q]) != side(b[q]))
    gained = sum(1 for q in shared if not ext(a[q]) and ext(b[q]))
    lost = sum(1 for q in shared if ext(a[q]) and not ext(b[q]))
    return sideflips, abs(gained - lost)


def ci(vals):
    """Bootstrap CI on the p90, so a floor carries an interval rather than a point."""
    if len(vals) < 5:
        return float("nan"), float("nan")
    rng = random.Random(BOOT_SEED)
    p90s = []
    for _ in range(BOOT_N):
        s = sorted(rng.choices(vals, k=len(vals)))
        p90s.append(s[int(0.9 * len(s)) - 1])
    p90s.sort()
    return p90s[int(0.025 * BOOT_N)], p90s[int(0.975 * BOOT_N)]


def ci_str(pair):
    """Render a bootstrap interval, or say why there is not one.

    Printing "[nan, nan]" into a published table invites a reader to treat an undefined
    interval as a computed one. The requantisation row has 4 pairs and cannot carry a
    percentile bootstrap; the table should say so in words.
    """
    lo, hi = pair
    if lo != lo or hi != hi:
        return "n too small"
    return "[%.0f, %.0f]" % (lo, hi)


def summarise(name, pairs, note=""):
    if not pairs:
        return None
    sf = [p[0] for p in pairs]
    ep = [p[1] for p in pairs]

    def q(v):
        # Round the median half-up rather than letting %d truncate it downstream. The order
        # floor's true median is 7.5; the paper's table printed 7 and the website said 8,
        # which is one quantity disagreeing with itself across two public surfaces because
        # two places each rounded it their own way. One convention, applied here, once.
        v = sorted(v)
        med = st.median(v)
        med = int(med + 0.5) if med >= 0 else int(med - 0.5)
        return med, v[int(0.9 * len(v)) - 1] if len(v) >= 10 else max(v), max(v)

    lo, hi = ci(sf)
    side, endpoint = q(sf), q(ep)
    # DISCLOSE, do not hide: for n < 10 the q() above deliberately reports the MAX as the p90,
    # because a nearest-rank 90th percentile on nine or fewer observations IS the maximum. That
    # is a defensible convention and an undisclosed one -- the table prints "med / p90 / max"
    # and a small arm prints the same number twice, which reads as two statistics agreeing
    # rather than one quantity repeated. The requantisation row (n=4) and the prompt-condition
    # row (n=7) both do this.
    return {"name": name, "n": len(pairs),
            "side": side, "endpoint": endpoint, "side_ci": (lo, hi), "note": note,
            "small_n": len(pairs) < 10,
            "p90_is_max": side[1] == side[2]}


def floor_order():
    # The canonical-order sheets live in the temp-0 and vendor sweeps; the shuffled arms live
    # in the order dirs. A pair needs one of each for the same model, so every source that
    # holds a condition-A sheet at a given shuffle seed has to be loaded here.
    #
    # 2026-09-01: 2026-08-31-order-control and the frontier canonical sheets in
    # 2026-08-30-temp0 were both missing from this list, so 27 runs collected specifically to
    # extend this floor onto frontier models contributed nothing to it and the row stayed at
    # 18 pairs of 2024-vintage local models. Collecting data and then not reading it is the
    # same defect as measuring the source instead of the artifact, one step earlier.
    by = _order_cells()
    pairs = []
    for m, orders in by.items():
        ks = list(orders)
        for i in range(len(ks)):
            for j in range(i + 1, len(ks)):
                pairs.append(both_stats(orders[ks[i]], orders[ks[j]]))
    return summarise("presentation order", pairs, "same model, same condition, item order only")


# Run directories deliberately withheld from the order floor, each with its reason. This is
# an EXCLUDE list on purpose, and the inversion is the whole point -- see _order_cells.
ORDER_EXCLUDE = {
    # A targeted re-collection of the three Google models that refuse most, run to probe
    # refusal rather than order. Its runs are legitimate order observations, but pooling a
    # sample selected on one behaviour into a floor for another invites the question and the
    # floor does not need it. Named here rather than silently absent.
    "2026-08-31-google-orderfloor",
}


def _order_cells():
    """Condition-A sheets from EVERY run directory except those named in ORDER_EXCLUDE.

    THE LIST USED TO POINT THE OTHER WAY, and it failed twice for the same reason.
    2026-09-01: `2026-08-31-order-control` and the frontier canonical sheets in
    `2026-08-30-temp0` were missing, so 27 runs collected specifically to extend this floor
    onto frontier models contributed nothing and the row stayed at 18 pairs of 2024-vintage
    local models. The fix was to add those two directories to the include list.
    2026-09-02: 14 more runs were collected to extend the frontier arm, and the row stayed at
    21 pairs -- because a new directory is invisible to an include list by construction. The
    previous fix guaranteed the recurrence.

    So the default is now READ EVERYTHING and anything withheld is named with a reason. A
    directory that arrives tomorrow is counted tomorrow. The pairing logic keys on (model,
    condition, shuffle seed), so an extra source can only add cells, never corrupt one.
    """
    cells = collections.defaultdict(list)
    for path in glob.glob(os.path.join(STUDY, "runs", "**", "*.jsonl"), recursive=True):
        rel = os.path.relpath(path, os.path.join(STUDY, "runs")).replace("\\", "/")
        if rel.split("/")[0] in ORDER_EXCLUDE:
            continue
        for key, runs in load(os.path.relpath(path, STUDY), "A").items():
            cells[key].extend(runs)
    by = collections.defaultdict(dict)
    for (m, c, o), runs in cells.items():
        if c == "A":
            by[m][o] = modal(runs)
    return by


def order_sources():
    """Which run directories actually contributed condition-A order cells, and how many.

    Reported so "the floor reads everything" is checkable rather than asserted.
    """
    out = collections.Counter()
    for path in glob.glob(os.path.join(STUDY, "runs", "**", "*.jsonl"), recursive=True):
        rel = os.path.relpath(path, os.path.join(STUDY, "runs")).replace("\\", "/")
        top = rel.split("/")[0]
        for line in io.open(path, encoding="utf-8"):
            if not line.strip():
                continue
            r = json.loads(line)
            if (r.get("schema") == "compass-run/1" and r.get("valid")
                    and r.get("condition") == "A"):
                out[top] += 1
    return out


def floor_order_by_class():
    """The order floor split by model class, because pooling the two hides the finding.

    Added 2026-09-01, when the frontier sweep doubled this row from 18 pairs to 39 and the
    pooled p90 fell from 14 to 12. That single number was concealing a bimodal distribution:
    reordering the questionnaire moves a median of 8 items on the 2024-vintage 7-14B open
    models this literature was largely built on, and a median of 3 on 2026 frontier APIs.

    Reporting only the pooled figure would be the exact defect this project has already
    caught in itself once -- a net aggregate concealing gross movement -- and it would have
    been in the paper's title claim.

    Rottger et al. (2024) conjectured this: "It is plausible that future models, as a product
    of more comprehensive alignment, will also exhibit fewer instabilities." This is that
    conjecture measured.
    """
    by = _order_cells()
    out = {}
    for label, want_api in (("presentation order, local open-weight", False),
                            ("presentation order, frontier API", True)):
        pairs = []
        for m, orders in by.items():
            if ("/" in m) != want_api:
                continue
            ks = list(orders)
            for i in range(len(ks)):
                for j in range(i + 1, len(ks)):
                    pairs.append(both_stats(orders[ks[i]], orders[ks[j]]))
        note = ("2026 frontier models served over an API"
                if want_api else "7-14B open-weight models of the 2024 generation")
        out[label] = summarise(label, pairs, note)
    return out


def floor_same_version():
    cells = load("runs/2026-08-31-lineage/**/*.jsonl", "A")
    by = collections.defaultdict(list)
    for (m, c, o), runs in cells.items():
        by[m].extend(runs)
    ids = [m for m, v in by.items() if len(v) >= 2]
    parsed = {i: parse(i) for i in ids}
    pairs = []
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            label, is_version = classify(parsed[a], parsed[b])
            if not is_version and label.endswith("(null)"):
                pairs.append(both_stats(modal(by[a]), modal(by[b])))
    return summarise("same-version variants", pairs, "size / mode / snapshot / tier, same version")


def floor_template():
    """The paraphrase floor: same model, same order, same temperature, reworded instruction.

    Added 2026-09-04, and it is the last unmeasured nuisance factor in this study. Every other
    floor here varies the SUBJECT -- model, size, quantisation, weights -- or the order of the
    items. The forced-choice wrapper was one fixed string across all 1,657 runs, so its
    contribution to every number in the paper was unmeasured, and "we did not vary it" is not
    the same claim as "it does not matter".

    Ten paraphrases, meaning held constant (see PARAPHRASE_TEMPLATES in run_compass.py and the
    import-time assertions that keep them the same task). Six 2026-frontier models, one per
    vendor family, at temperature 0 in condition A. Roettger et al. measured this factor in
    2024 and their p90 re-scored with this statistic is 9 of 62 -- but on Llama-2 and GPT-3.5,
    so it establishes that the factor is real and nothing about its size today.
    """
    cells = load("runs/2026-09-04-template-floor/**/*.jsonl", "A", key=_template_key)
    by_model = collections.defaultdict(dict)
    for (m, c, tpl), runs in cells.items():
        by_model[m][tpl] = modal(runs)
    pairs = []
    for m, templates in sorted(by_model.items()):
        tids = sorted(templates)
        for i in range(len(tids)):
            for j in range(i + 1, len(tids)):
                pairs.append(both_stats(templates[tids[i]], templates[tids[j]]))
    return summarise("instruction paraphrase", pairs,
                     "same model, same order, same temperature, reworded wrapper")


def floor_quant():
    cells = load("runs/2026-08-30-quant-null/**/*.jsonl")
    by = collections.defaultdict(dict)
    for (m, c, o), runs in cells.items():
        by[c][m] = modal(runs)
    pairs = []
    for c, models in by.items():
        ms = list(models)
        for i in range(len(ms)):
            for j in range(i + 1, len(ms)):
                pairs.append(both_stats(models[ms[i]], models[ms[j]]))
    return summarise("requantisation", pairs, "same weights, Q4 vs Q8, no other change")


def floor_ablation():
    """Stock vs ablated, arm-matched, per condition.

    EXCLUSIONS ARE BY RULING NOW, not by luck. `check_arm_match.INELIGIBLE_PAIRS` holds the
    three of six locally-held pairs that gate measured as invalid comparison arms on
    2026-08-30 -- mismatched quantisation, dropped stop tokens, baked sampling parameters.
    None of those differences is the refusal direction.

    Before 2026-09-04 this function did not know that. All three were excluded anyway, by
    three unrelated accidents: two emit prose with no parsable answers, and the third answers
    every item identically so the loader calls it degenerate. The floor was right and its
    reason was wrong, which is a floor that holds until one of the accidents stops happening.
    """
    pairs, skipped = [], []
    pair_dirs = sorted(glob.glob(os.path.join(STUDY, "runs/2026-08-30-ablation-pairs/*")))
    for pair_dir in pair_dirs:
        label = os.path.basename(pair_dir)
        if label in INELIGIBLE_PAIRS:
            skipped.append((label, INELIGIBLE_PAIRS[label]))
            continue
        arms = {}
        for arm in ("stock", "ablated"):
            cells = load(os.path.join("runs/2026-08-30-ablation-pairs",
                                      os.path.basename(pair_dir), arm, "*.jsonl"))
            per_cond = collections.defaultdict(list)
            for (m, c, o), runs in cells.items():
                per_cond[c].extend(runs)
            arms[arm] = {c: modal(v) for c, v in per_cond.items()}
        for c in set(arms.get("stock", {})) & set(arms.get("ablated", {})):
            pairs.append(both_stats(arms["stock"][c], arms["ablated"][c]))
        if not (set(arms.get("stock", {})) & set(arms.get("ablated", {}))):
            # Eligible by the gate and still contributing nothing. That combination has no
            # documented cause, so it must not pass quietly the way the ruled-out three did.
            skipped.append((label, "ELIGIBLE but produced no arm-matched condition -- "
                                   "investigate, this has no recorded reason"))
    out = summarise("refusal-direction ablation", pairs,
                    "%d of %d collected model pairs excluded, see check_arm_match"
                    % (len(skipped), len(pair_dirs)))
    if out:
        out["skipped"] = skipped
    return out


def floor_conditions():
    cells = load("runs/2026-08-30-temp0/**/*.jsonl")
    by = collections.defaultdict(dict)
    for (m, c, o), runs in cells.items():
        by[m][c] = modal(runs)
    pairs = []
    for m, conds in by.items():
        if "A" in conds and "D" in conds:
            pairs.append(both_stats(conds["A"], conds["D"]))
    return summarise("prompt condition A->D", pairs, "the deliberate manipulation, for scale")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--markdown", action="store_true")
    args = ap.parse_args(argv)

    rows = [f for f in (floor_order(), floor_same_version(), floor_template(), floor_quant(),
                        floor_ablation(), floor_conditions()) if f]
    rows.sort(key=lambda r: -r["side"][1])

    if args.markdown:
        print("| factor | n pairs | side-flip med / p90 / max | p90 95% CI | endpoint med / p90 / max |")
        print("|---|---:|---|---|---|")
        for r in rows:
            mark = " †" if r.get("small_n") and r.get("p90_is_max") else ""
            print("| %s%s | %d | %d / %d / %d | %s | %d / %d / %d |"
                  % (r["name"], mark, r["n"], *r["side"], ci_str(r["side_ci"]),
                     *r["endpoint"]))
        if any(r.get("small_n") and r.get("p90_is_max") for r in rows):
            print()
            print("† fewer than 10 pairs, so the 90th percentile IS the maximum by "
                  "nearest-rank and the two columns print one number, not two.")
        # A row's exclusions belong beside the row. The ablation floor rests on three of six
        # collected model pairs and the table said only "arm-matched pairs only", which reads
        # as a description of the method rather than as half the data being withheld.
        for r in rows:
            for label, why in r.get("skipped") or ():
                print()
                print("**%s excludes `%s`:** %s" % (r["name"], label, why))
        return 0

    print("MEASURED FLOORS -- every row computed from runs/, both statistics")
    print("side-flip = crossed the agree/disagree boundary")
    print("endpoint  = gained/lost a Strongly answer (|b-c|)")
    print()
    print("%-28s %6s %18s %14s %18s" % ("factor", "pairs", "side med/p90/max",
                                        "p90 95% CI", "endpoint med/p90/max"))
    for r in rows:
        print("%-28s %6d %18s %14s %18s"
              % (r["name"], r["n"], "%d / %d / %d" % r["side"],
                 ci_str(r["side_ci"]), "%d / %d / %d" % r["endpoint"]))
    print()
    for r in rows:
        print("  %-28s %s" % (r["name"], r["note"]))
        for label, why in r.get("skipped") or ():
            print("  %-28s   excluded %s: %s" % ("", label, why))
    # Everything the loader refused, so a lost arm cannot be invisible again.
    dropped = load_report()
    if dropped:
        print()
        print("LOADER DROPPED %d run(s):" % sum(n for _, n in dropped))
        for reason, n in dropped:
            print("  x%-4d %s" % (n, reason))
    return 0


if __name__ == "__main__":
    sys.exit(main())
