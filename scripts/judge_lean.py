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
which was for months the one method never executed, because the benchmark items were never
acquired. The gap in the scoring layer is the gap the rubric identified in May.

**Its harness is built and it has not been run.** `scripts/judge_anchor.py` draws a blind
scoring sheet -- `data/judge-anchor-sheet.jsonl`, 120 items, question and response only, every
`your_score` null -- against a sealed key, `data/judge-anchor-key.json`, which holds the panel
score, the per-judge scores and the rubric for each item. The draw is stratified 24 items per
panel score across 1-5 over 38 models, because an unstratified sample of this corpus returns
mostly 3s and bounds nothing.

**No human has scored it, so there is no number.** That is the whole of the gap. Not a missing
tool: a missing afternoon. Until someone works the sheet, everything below is a RELATIVE lean.

Two things about Method 8 the rubric does not yet say, recorded here because this is the file
that warns about the gap:

- The pre-registered form of the anchor was the Political Compass's own axes. It is declined
  on principle, not on cost. This study uses those 62 propositions as *stimuli* and rejects the
  framework's axes -- README.md argues the horizontal axis is captured, self-report and
  undisclosed in scoring -- so anchoring to them would import the framework the study exists to
  criticise. The substitute is the human blind pass above.
- The rubric names Method 2, the abliterated judge, as the fallback if Method 8 is infeasible.
  This project's own weight-rung result contests that: abliteration rewrites ~70% of political
  wording and moves stance by <=0.2, so the fallback removes a reflex the study itself proved is
  not the lean. There is no cheap substitute for the human pass.

    python scripts/judge_lean.py              # per-judge deviation, and the spread
    python scripts/judge_lean.py --by-condition
    python scripts/judge_lean.py --self-judged   # findings whose subject sat on the panel
    python scripts/judge_lean.py --per-finding   # each finding re-scored under one judge
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




def corpus_roots():
    """Every populated corpus root, resolved by `studypaths` so STUDY_ROOT is honoured.

    This used to be a hardcoded `for root in ("data", "runs")` under this file's own parent
    directory, which is a third implementation of run resolution and -- more to the point --
    ignores STUDY_ROOT entirely. A private shim forwarding to this code would therefore have
    read the PUBLIC corpus while believing it read the private one, which is the exact silent
    misdirection `studypaths` and `_shim.prepare` exist to make impossible. `_shim` refuses to
    forward a script that is not on `studypaths.ROOT_AWARE_SCRIPTS`, and it was right to refuse
    this one until now.

    Falls back to the old behaviour only when `studypaths` cannot be imported at all, so a bare
    checkout still runs.
    """
    try:
        from studypaths import run_roots
    except Exception:
        return [os.path.join(STUDY, r) for r in ("data", "runs")
                if os.path.isdir(os.path.join(STUDY, r))]
    return [str(p) for p in run_roots()]


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
    for root in corpus_roots():
        paths += glob.glob(os.path.join(root, "*", "scored", "**", "*.jsonl"),
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
    try:
        import build_experiment as B
    except ImportError:
        # build_experiment.py is private-tree-only: it builds the commit-before-reveal deck
        # from material the mirror does not ship. Crashing here published a flag that cannot
        # run where the reader is standing, which is the defect this script exists to catch.
        print("PUBLISHED FINDINGS WHOSE SUBJECT IS ALSO A JUDGE")
        print("  build_experiment.py is not in this tree, so the bootstrap intervals below")
        print("  cannot be recomputed here. The same exposure is visible without it:")
        print("  run --per-finding, where a same-vendor cell is marked with *.")
        return 0
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


def per_finding():
    """Re-score every CI-clean finding under each judge ALONE. The test rank order is not.

    `rank_stability` establishes that the panel's lean interacts with condition, so it does not
    subtract out of a B-A delta. That is a statement about the panel. It says nothing about
    which FINDINGS survive, and the two are not the same question: a finding large enough to
    clear the fan-out under every judge is safe whatever the panel's lean does.

    So the right test is mechanical rather than argumentative. Take the study's own estimator,
    substitute one judge's raw score for the panel median, and recompute. A finding that returns
    the same sign and a comparable magnitude under all four judges does not depend on panel
    composition. One that swings by a factor of twenty does.

    This table was published in RESULTS-2026-09-05-judge-lean.md as typed literals with no
    harness behind them, which is the exact defect `ci_clean_effects` exists to document. It is
    computed now.
    """
    try:
        from ci_analysis import load_scored, per_model_deltas, bootstrap_ci
        from studypaths import analysis_seed, resolve_run, stream
    except Exception:
        print("PER-FINDING BY JUDGE: ci_analysis/studypaths not importable here")
        return 0
    try:
        recs = load_scored(resolve_run(HEADLINE_RUN))
    except Exception:
        print("PER-FINDING BY JUDGE: run %s not resolvable here" % HEADLINE_RUN)
        return 0
    if not recs:
        print("PER-FINDING BY JUDGE: no scored records under %s" % HEADLINE_RUN)
        return 0

    seed = analysis_seed(HEADLINE_RUN)
    panel = {}
    for model, deltas in per_model_deltas(recs).items():
        if len(deltas) < 2:
            continue
        mean, lo, hi = bootstrap_ci(deltas, stream(seed, HEADLINE_RUN, model, "ci"))
        if lo is not None and hi is not None and (lo > 0 or hi < 0):
            panel[model] = mean
    if not panel:
        print("PER-FINDING BY JUDGE: no CI-clean findings in %s" % HEADLINE_RUN)
        return 0

    # One judge's raw score substituted for the panel median, through the SAME estimator.
    by_judge = {}
    for judge in PANEL:
        sub = []
        for r in recs:
            for j in r.get("score_classifier_judges") or ():
                if j.get("judge") == judge and isinstance(j.get("score"), (int, float)):
                    d = dict(r)
                    d["score_classifier"] = j["score"]
                    sub.append(d)
                    break
        if not sub:
            continue
        by_judge[judge] = {m: st.mean(v) for m, v in per_model_deltas(sub).items()}

    short = [j.split("/")[-1] for j in PANEL if j in by_judge]
    print("PER-FINDING BY JUDGE -- each CI-clean finding, re-scored under one judge alone")
    print("  * = the judge and the subject are the same vendor")
    print("")
    print("  %-30s %8s %s" % ("finding", "panel", " ".join("%9s" % s for s in short)))
    unstable = []
    for model, pmean in sorted(panel.items(), key=lambda kv: -abs(kv[1])):
        cells, vals = [], []
        for judge in PANEL:
            if judge not in by_judge:
                continue
            v = by_judge[judge].get(model)
            if v is None:
                cells.append("%9s" % "--")
                continue
            vals.append(v)
            same = judge.split("/")[0] == model.split("/")[0]
            cells.append("%9s" % (("%+.2f" % v) + ("*" if same else " ")))
        print("  %-30s %+8.2f %s" % (model, pmean, " ".join(cells)))
        if len(vals) > 1 and (min(vals) <= 0 <= max(vals) or
                              (min(abs(v) for v in vals) > 0 and
                               max(abs(v) for v in vals) / min(abs(v) for v in vals) >= 3)):
            unstable.append((model, min(vals), max(vals)))
    print("")
    if not unstable:
        print("  Every finding holds its sign and magnitude under every judge. Panel")
        print("  composition does not carry any of them.")
    else:
        for model, lo, hi in unstable:
            print("  NOT ROBUST: %s ranges %+.2f to %+.2f depending on which judge reads it."
                  % (model, lo, hi))
        print("  Report those with the range, as suggestive, not at the standing of the rest.")
    print("")
    print("  A same-vendor cell (*) is not automatically a defect. It is the thing this")
    print("  project convicts other studies of failing to disclose, so it is marked.")
    return len(unstable)


def rank_stability(records, conds=("A", "B")):
    """Is the judges' lean CONSTANT across the contrast the findings are measured over?

    THIS IS THE QUESTION THAT DECIDES WHETHER JUDGE LEAN MATTERS AT ALL, and it is not the
    same question as "do the judges lean". A ruler 2% short still measures differences
    correctly. Every published finding here is a within-model, within-judge DELTA (B minus A),
    so a lean that is constant across A and B subtracts out of every one of them. A lean that
    INTERACTS with condition does not, and would contaminate all five.

    **This function used to answer that with rank order alone, and rank order is the wrong
    test.** It reported IDENTICAL ORDER and concluded the lean was a constant main effect that
    cancels. Same order is necessary; it is not sufficient. Cancellation needs the lean to be
    the same SIZE in both arms, and it is not: the two most skeptical judges get more skeptical
    in B while the most deferential gets more deferential, so the panel FANS OUT and the fanning
    rides into the delta. Both statistics are printed now, and the verdict is read off the
    magnitudes.

    Raw spread looks alarming for a separate and genuine reason: condition A scores 92% threes
    (2,047 of 2,216), so per-judge deviation is compressed there by a floor, while condition B
    spreads into 4s and 5s. That explains WHY the lean is small in A. It does not make the lean
    cancel -- a lean suppressed in one arm and expressed in the other is the definition of an
    interaction.
    """
    per_cond = {}
    order = {}
    for c in conds:
        per = deviations(records, c)
        if not per:
            return None
        per_cond[c] = {j: st.mean(v) for j, v in per.items()}
        order[c] = [j for j, _ in sorted(per_cond[c].items(), key=lambda kv: -kv[1])]
    first = order[conds[0]]
    stable = all(order[c] == first for c in conds)
    a, b = conds[0], conds[-1]

    print("RANK STABILITY across conditions %s" % ", ".join(conds))
    for c in conds:
        print("  %-4s %s" % (c, " > ".join(j.split("/")[-1] for j in order[c])))
    print("")
    print("  %-28s %8s %8s %9s" % ("judge", "lean " + a, "lean " + b, b + "-" + a))
    shifts = {}
    for j in first:
        if j not in per_cond[a] or j not in per_cond[b]:
            continue
        shifts[j] = per_cond[b][j] - per_cond[a][j]
        print("  %-28s %+8.3f %+8.3f %+9.3f"
              % (j.split("/")[-1], per_cond[a][j], per_cond[b][j], shifts[j]))
    print("")
    if not shifts:
        return stable
    worst = max(shifts.values()) - min(shifts.values())
    print("  %s ORDER, and that is only half the test." % ("IDENTICAL" if stable else "CHANGED"))
    print("  If the lean cancelled in a %s-%s delta the last column would be zero. It spans" % (b, a))
    print("  %.3f, from %+.3f to %+.3f. The panel FANS OUT: the lean is an INTERACTION, not a"
          % (worst, min(shifts.values()), max(shifts.values())))
    print("  main effect, and it does NOT subtract out of the deltas the findings are built")
    print("  from. It lands on absolute scores ('this model scores 3.00') harder still, with")
    print("  nothing to subtract it at all.")
    print("")
    print("  What survives is per-finding, not per-panel: re-score each finding under each")
    print("  judge alone and see which ones hold. See RESULTS-2026-09-05-judge-lean.md --")
    print("  the two large effects hold under every judge; the smallest does not.")
    return stable


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--by-condition", action="store_true")
    ap.add_argument("--self-judged", action="store_true")
    ap.add_argument("--per-finding", action="store_true",
                    help="re-score each CI-clean finding under each judge alone")
    args = ap.parse_args(argv)

    if args.self_judged:
        self_judged()
    if args.per_finding:
        print("")
        per_finding()
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
    print("the panel -- Method 8, ranked FIRST at 4.25 in the pre-registered rubric.")
    print("Its harness is built -- judge_anchor.py, 120-item blind sheet drawn against a")
    print("sealed key -- and NO HUMAN HAS SCORED IT, so there is no number. Until someone")
    print("does, this spread is a RELATIVE lean and nothing here bounds a shared one.")
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
