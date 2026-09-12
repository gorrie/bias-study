#!/usr/bin/env python3
"""Do the judges lean, and by how much? The floor nobody computed for the scoring layer.

WHAT THIS ANSWERS, AND WHAT IT CANNOT
-------------------------------------
Five alternative judging procedures were run and agree with the panel 84-91% of the time. Read
what each one actually tests:

    M4 grok-solo        one judge instead of four        panel-vs-solo
    M5 adversarial-pair judge pushed to be critical      directional PROMPT pressure on a judge
    M6 reversed-rubric  rubric labels inverted           label-position / anchor bias
    M7 blind-condition  judge sees text, not condition   framing and demand effects
    M2 abliterated      refusal direction cut out        the REFUSAL REFLEX

None of those is a test for political lean, and the last one is the important case. M2 is the
executed anchor, scored D1=5 on the pre-registered rubric as "the direct answer to 'judges share
RLHF lean'". But this project's own weight-rung result (WRITEUP SS4.2, five families) is that
**abliteration moves wording by ~70% and stance by <=0.2** -- the refusal direction and the
institutional lean are DISSOCIABLE. If ablating that direction does not move a subject's stance,
it does not move a judge's either. The anchor removes a reflex the study proved is not the lean.

So the scoring layer has never been checked for the one thing it is most suspected of.

TWO KINDS OF LEAN, AND ONLY ONE IS MEASURABLE FROM WHAT WE HOLD
---------------------------------------------------------------
**Relative lean** -- does one judge score systematically higher than the panel it sits in? Every
per-judge score is retained (`score_classifier_judges`), so this costs nothing and is computed
below, over every scored record in BOTH run roots. The magnitude is deliberately not repeated
here: this docstring said "over 4,628 records it is 0.29 points end to end, which is larger than
two of the five published CI-clean findings", and by 2026-09-12 the record count was wrong, the
rounding hid a decimal that mattered, and "two" was wrong -- the spread is larger than ONE of
the five. Run the script. `key_numbers.py` gates the figure the README quotes.

**Shared lean** -- do all four lean the same way together? **This method cannot see it, by
construction**, because every judge is measured against the median of the same four. A panel
that agreed perfectly and was wrong together would show a spread of zero here and look ideal.

Saying so is the point. The only method in the pre-registered rubric that can catch a shared
lean is **Method 8, external-benchmark anchoring** -- which the rubric ranked FIRST at 4.25, and
which is the one method never executed, because the benchmark items were never acquired. The
gap in the scoring layer is the gap the rubric identified in May and nobody closed.

    python scripts/judge_lean.py              # per-judge deviation, and the spread
    python scripts/judge_lean.py --by-condition
    python scripts/judge_lean.py --self-judged   # findings whose subject sat on the panel
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

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, HERE)

#: The panel that produced every published score in the May study.
PANEL = ("anthropic/claude-haiku-4.5", "openai/gpt-4.1",
         "google/gemini-2.5-flash", "deepseek/deepseek-v3.2")

#: The run whose CI-clean per-model effects the spread is compared against.
HEADLINE_RUN = "2026-05-25-full"


def ci_clean_effects():
    """The published CI-clean per-model effects, RECOMPUTED, largest first.

    These were five typed literals in a print statement -- "+0.90, +0.90, +0.43, +0.30, +0.23"
    -- followed by a typed verdict, "larger than two of them". The verdict was wrong, and it
    was wrong in the direction that flattered the self-criticism: the spread is 0.2915 and the
    third-smallest effect is 0.3000, so it is larger than ONE of them, not two. It had been
    copied from here into CORRECTIONS.md, PRIOR-WORK-CORRECTIONS.md, README.md,
    controls-audit.json and add_controls_2026_09.py before anyone recomputed it.

    A study whose entire argument is that a typed number goes stale had its own sharpest
    self-indictment typed. So it is computed now, including the comparison, and the rounding
    that hid it (0.29 vs 0.30 is invisible at two decimals) is printed at four.
    """
    try:
        from ci_analysis import load_scored, per_model_deltas, bootstrap_ci
        from studypaths import analysis_seed, resolve_run, stream
    except Exception:
        return []
    try:
        run_dir = resolve_run(HEADLINE_RUN)
    except Exception:
        return []
    recs = load_scored(run_dir)
    if not recs:
        return []
    seed = analysis_seed(HEADLINE_RUN)
    out = []
    for model, deltas in per_model_deltas(recs).items():
        if len(deltas) < 2:
            continue
        mean, lo, hi = bootstrap_ci(deltas, stream(seed, HEADLINE_RUN, model, "ci"))
        if lo is None or hi is None:
            continue
        if lo > 0 or hi < 0:  # CI excludes zero -- the study's own definition of a finding
            out.append(mean)
    return sorted(out, key=abs, reverse=True)


def scored_records():
    """Every scored record that carries both a panel median and its per-judge breakdown."""
    out = []
    # BOTH run roots. This repository keeps the May study under `data/` and the barometer
    # under `runs/`, and every record carrying a per-judge breakdown is in the first one --
    # so globbing `runs/` alone found 4,714 records in the working tree and ZERO in the
    # public mirror, where this script silently printed no spread at all. The public README
    # cites that spread. A number a reader is told to recompute has to recompute where the
    # reader is standing.
    paths = []
    for root in ("data", "runs"):
        paths += glob.glob(os.path.join(STUDY, root, "*", "scored", "**", "*.jsonl"),
                           recursive=True)
    for p in sorted(paths):
        for line in io.open(p, encoding="utf-8", errors="replace"):
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("score_classifier") is None or not r.get("score_classifier_judges"):
                continue
            out.append(r)
    return out


def deviations(records, condition=None):
    """judge -> [score - panel median] over the records it scored."""
    per = collections.defaultdict(list)
    for r in records:
        if condition and r.get("condition") != condition:
            continue
        med = r["score_classifier"]
        for j in r["score_classifier_judges"]:
            if isinstance(j.get("score"), (int, float)):
                per[j["judge"]].append(j["score"] - med)
    return per


def report(per, label):
    if not per:
        print("  %s: no records" % label)
        return None
    rows = sorted(per.items(), key=lambda kv: -st.mean(kv[1]))
    print("  %-30s %7s %10s %8s" % (label, "n", "mean dev", "sd"))
    for judge, vals in rows:
        print("  %-30s %7d %+10.4f %8.4f"
              % (judge, len(vals), st.mean(vals), st.pstdev(vals)))
    spread = st.mean(rows[0][1]) - st.mean(rows[-1][1])
    print("  %-30s %7s %+10.4f  <- spread, most skeptical to most deferential"
          % ("", "", spread))
    return spread


def self_judged():
    """Published findings whose SUBJECT also sat on the panel that scored it.

    Not automatically a defect -- a median of four dilutes any one judge -- but it is exactly
    the kind of thing this project convicts other studies of failing to disclose, and as of
    2026-09-05 it appears in no writeup, paper or review in this repository.
    """
    import build_experiment as B
    stats = B.model_stats(B.pairs(B.load()))
    hits = [(m, v) for m, v in stats.items() if v["is_finding"] and m in PANEL]
    print("PUBLISHED FINDINGS WHOSE SUBJECT IS ALSO A JUDGE")
    if not hits:
        print("  none")
        return 0
    for m, v in sorted(hits, key=lambda kv: -kv[1]["mean"]):
        print("  %-30s %+.3f [%+.3f, %+.3f]  n=%d"
              % (m, v["mean"], v["ci"][0], v["ci"][1], v["n"]))
    print("")
    print("  %d of %d CI-clean findings are self-judged."
          % (len(hits), sum(1 for v in stats.values() if v["is_finding"])))
    print("  Disclose it. The median of four dilutes any single judge's influence, which is an")
    print("  argument for why it may not matter -- not a reason to leave it unsaid.")
    return len(hits)


def rank_stability(records, conds=("A", "B")):
    """Is the judges' lean CONSTANT across the contrast the findings are measured over?

    THIS IS THE QUESTION THAT DECIDES WHETHER JUDGE LEAN MATTERS AT ALL, and it is not the
    same question as "do the judges lean". A ruler 2% short still measures differences
    correctly. Every published finding here is a within-model, within-judge DELTA (B minus A),
    so a lean that is constant across A and B subtracts out of every one of them. A lean that
    INTERACTS with condition does not, and would contaminate all five.

    Raw spread looks alarming and is mostly an artefact: condition A scores 92% threes (2,047
    of 2,216), so per-judge deviation is near zero there by construction, while condition B
    spreads into 4s and 5s. That is a property of the text, not of the panel.

    Rank order is the part that is not an artefact. If the same judge is the most skeptical in
    both arms, with the same sign, the lean is a main effect and it cancels.
    """
    order = {}
    for c in conds:
        per = deviations(records, c)
        if not per:
            return None
        order[c] = [j for j, _ in sorted(per.items(), key=lambda kv: -st.mean(kv[1]))]
    first = order[conds[0]]
    stable = all(order[c] == first for c in conds)
    print("RANK STABILITY across conditions %s" % ", ".join(conds))
    for c in conds:
        print("  %-4s %s" % (c, " > ".join(j.split("/")[-1] for j in order[c])))
    print("")
    if stable:
        print("  IDENTICAL ORDER. The lean is a constant main effect, so it subtracts out of")
        print("  the B-A deltas every published finding is built from. Judge lean is a threat")
        print("  to ABSOLUTE scores ('this model scores 3.00'), not to the deltas.")
    else:
        print("  ORDER CHANGES. The lean interacts with condition, so it does NOT cancel in")
        print("  the deltas, and every published finding needs re-examining against it.")
    return stable


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--by-condition", action="store_true")
    ap.add_argument("--self-judged", action="store_true")
    args = ap.parse_args(argv)

    if args.self_judged:
        self_judged()
        return 0

    records = scored_records()
    print("JUDGE LEAN -- deviation from the panel median each judge sits in")
    print("%d scored record(s) carrying a per-judge breakdown" % len(records))
    print("positive = scores MORE institution-skeptical than its own panel")
    print("")
    spread = report(deviations(records), "all conditions")
    print("")
    rank_stability(records)

    if args.by_condition:
        for cond in sorted({r.get("condition") for r in records if r.get("condition")}):
            print("")
            report(deviations(records, cond), "condition %s" % cond)

    print("")
    print("WHAT THIS CANNOT SEE: a lean shared by all four. Every judge here is measured")
    print("against the median of the same panel, so a panel that agreed and was wrong together")
    print("would score a spread of zero and look ideal. Catching that needs an anchor OUTSIDE")
    print("the panel -- Method 8 in RUBRIC-SCORES.md, ranked FIRST at 4.25, never executed.")
    if spread is not None:
        print("")
        effects = ci_clean_effects()
        if effects:
            shown = ", ".join("%+.2f" % e for e in effects)
            beaten = [e for e in effects if abs(e) < spread]
            n = len(beaten)
            word = {0: "none", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}.get(n, str(n))
            print("For scale, the study's CI-clean findings are %s." % shown)
            print("A judge-composition spread of %.4f is larger than %s of them%s."
                  % (spread, word, (" (%s)" % ", ".join("%+.4f" % e for e in beaten)) if beaten else ""))
            if n:
                print("Smallest effect NOT beaten: %+.4f."
                      % min((e for e in effects if abs(e) >= spread), key=abs, default=float("nan")))
        else:
            print("CI-clean effects unavailable (run %s not present); spread is %.4f."
                  % (HEADLINE_RUN, spread))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
