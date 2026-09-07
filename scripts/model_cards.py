#!/usr/bin/env python3
"""One card per model: can this model carry a claim at all, and on what evidence?

WHY THIS EXISTS
---------------
Every floor in this study pools per-model behaviour away, and that pooling hid the single most
consequential fact in the corpus: **some models are too unstable to measure.** `grok-4.3` has a
run-to-run spread of 21 items of 62 -- larger than any effect measured on it -- and until
2026-09-06 it was setting the reference scale for the whole paper. Remove the three x-ai builds
and the pooled manipulation p90 drops from 15 to 8.

A pooled floor cannot tell you that. A per-model card can, and it costs nothing: every number
here is already in `runs/`.

THE FOUR AXES
-------------
    coverage       how many valid runs, per condition. n is not a detail; sample size is
                   distinct seeds among VALID runs, a rule this project learned twice.
    willingness    which conditions it answers and which it declines. A model that refuses
                   condition A is not a hole in the table -- it is section 1's finding.
    stability      its OWN run-to-run spread. This is the model's personal denominator, and
                   it ranges from 0 (claude-opus-4.6) to 21 (grok-4.3).
    responsiveness how far it moves under a prompt intervention, tested AGAINST ITS OWN RUNS by
                   permutation rather than against a pooled floor.

THE VERDICT COLUMN
------------------
`carries` when an **exact permutation test** on the model's own runs puts its largest effect
beyond chance: shuffle the condition labels among that model's runs, recompute the
modal-vs-modal distance, and ask how often shuffling alone reaches the observed value.
Bonferroni over the contrasts actually tested. At n=5 per arm this enumerates all C(10,5) = 252
assignments, so the p-value is exact rather than sampled.

**One model of 30 carries** -- `qwen2.5:14b`, P->D = 4 items at p = 0.024. That is the whole
result of this card, and it took three tries to measure honestly:

    against each model's WORST within-cell pair    29 of 30 "failed"   -- an extreme is not a null
    against the p90 of its run-to-run spread        8 of 30 "carried"  -- wrong null distribution
    exact permutation, uncorrected                  5 of 30            -- untested multiplicity
    exact permutation, Bonferroni                   1 of 30 carries    -- what the data supports

**The multiplicity correction does almost all the work, and that is reported rather than
buried**: 5 models reach p < 0.05 on their best contrast and 1 survives correcting for having
tested up to three. The 2026-09-07 review's independent count was 4, which is the uncorrected
figure -- so the disagreement between that review and this script is the correction, not the
test. Correcting is right here: the card takes each model's LARGEST effect across contrasts,
and taking a max over three tests and quoting its raw p-value is the same inflation the p90
rule was retired for. `grok-4.5` is the case that shows it -- P->D = 16, raw p = 0.024, and
p = 0.07 once you account for the fact that its A->D and B->D were also examined.

The p90 rule was wrong twice over: the effect is modal-vs-modal while the null was run-vs-run.
The disagreement is not academic -- `grok-4.6` "carried" on A->D = 14 under it and comes out at
**p = 1.0** here, because its runs are bimodal enough that shuffling reproduces 14 routinely.
Only 2 of its 8 survive at all. A big effect on an unstable model is the thing this card exists
to catch, so a rule that promoted one was inverted.

That verdict is the point of the card. It is not a quality judgement about the model; a
perfectly stable model that never moves also reads `no`, and `claude-opus-4.6` is exactly that
-- 0 spread, 0 effect -- which makes it the study's cleanest negative control rather than a
failure. The stability columns are still printed, because a model whose max spread dwarfs its
p90 is bimodal and that is the more interesting problem.

    python scripts/model_cards.py                 # every model with >=2 runs
    python scripts/model_cards.py --min-runs 4    # the strong subset
    python scripts/model_cards.py --json
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import floor_table as F      # noqa: E402
import refusal_table as R    # noqa: E402
import key_numbers as K      # noqa: E402

WAVE = "runs/*-wave/*.jsonl"
CONDITIONS = ("A", "B", "D", "P")


def willingness():
    """model -> condition -> {valid, refused, other}. From the whole corpus, not just waves."""
    out = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    for r in R.load(K.REFUSAL_EXCLUDE):
        cls = R.classify(r)
        bucket = cls if cls in ("valid", "refused") else "other"
        out[r.get("model")][r.get("condition")][bucket] += 1
    return out


def cards(min_runs=2):
    cells = F.load(WAVE, key=lambda r: (r["model"], r["condition"]), dedupe_by_seed=True)
    per = collections.defaultdict(dict)
    for (m, c), runs in cells.items():
        per[m][c] = runs
    will = willingness()

    out = []
    for m, conds in sorted(per.items()):
        usable = {c: r for c, r in conds.items() if len(r) >= min_runs}
        if not usable:
            continue

        # STABILITY: its own run-to-run spread, pooled across the conditions it answers.
        spread = []
        for c, runs in usable.items():
            spread += [F.both_stats(runs[i], runs[j])[0]
                       for i in range(len(runs)) for j in range(i + 1, len(runs))]
        # These three are REPORTED, not used as the verdict's null -- two earlier versions of
        # this card compared effects against stab_max and then stab_p90, and both were wrong
        # (see the header). They stay because the gap between median and max is what identifies
        # a bimodal model, which is the most useful thing on the card after the verdict.
        stab_med = int(st.median(spread)) if spread else None
        stab_max = max(spread) if spread else None
        stab_p90 = None
        if spread:
            s = sorted(spread)
            stab_p90 = s[int(0.9 * len(s)) - 1] if len(s) >= 10 else max(s)

        # RESPONSIVENESS: modal-vs-modal under each available prompt contrast.
        modal = {c: F.modal(r) for c, r in usable.items()}
        effects = {}
        for ref in ("A", "B", "P"):
            if ref in modal and "D" in modal:
                effects["%s->D" % ref] = F.both_stats(modal[ref], modal["D"])[0]
        biggest = max(effects.values()) if effects else None

        # WILLINGNESS, from the whole corpus.
        w = {}
        for c in CONDITIONS:
            t = will.get(m, {}).get(c) or collections.Counter()
            n = sum(t.values())
            if n:
                w[c] = {"n": n, "refused": t["refused"],
                        "refusal_rate": round(t["refused"] / n, 3)}

        # THE VERDICT IS AN EXACT PERMUTATION TEST, not a comparison against a percentile.
        #
        # Two earlier rules were both wrong. The first compared the effect against the model's
        # WORST within-cell pair and 29 of 30 "failed" -- an extreme value is not a null. The
        # second compared against the p90 of run-vs-run pairs, which is the wrong null
        # distribution twice over: the effect is modal-vs-modal, the null was run-vs-run, and
        # it took the max of up to three contrasts with no correction for doing so.
        #
        # Review 2026-09-07 checked it against a permutation test and the two disagree badly:
        # the p90 rule said 8 of 30 carry, the review's permutation said 4, and only 2 models
        # appear in both. grok-4.6 "carried" on A->D = 14 at p = 1.0 here, because its runs are
        # bimodal enough to reproduce 14 under shuffling. This implementation gives 1, not 4:
        # the difference is the Bonferroni factor below, which the review's variant omitted.
        #
        # So: shuffle the condition labels among a model's own runs, recompute the
        # modal-vs-modal distance, and ask how often chance reaches the observed value. That is
        # exact at n=5 per arm (C(10,5) = 252 assignments), needs no distributional assumption,
        # and its null is built from the same statistic as the effect. Bonferroni over the
        # contrasts actually tested, because taking a max of three and not correcting is how
        # the second rule inflated.
        verdict, pval = None, None
        if effects:
            import itertools
            worst_p = None
            for name, obs in effects.items():
                ref = name.split("->")[0]
                a, b = usable.get(ref), usable.get("D")
                if not a or not b:
                    continue
                pool = list(a) + list(b)
                na = len(a)
                ge = tot = 0
                for idx in itertools.combinations(range(len(pool)), na):
                    left = [pool[i] for i in idx]
                    right = [pool[i] for i in range(len(pool)) if i not in idx]
                    d = F.both_stats(F.modal(left), F.modal(right))[0]
                    tot += 1
                    if d >= obs:
                        ge += 1
                if tot:
                    p = ge / float(tot)
                    if worst_p is None or p < worst_p:
                        worst_p = p
            if worst_p is not None:
                pval = round(min(1.0, worst_p * max(1, len(effects))), 4)   # Bonferroni
                verdict = "carries" if pval < 0.05 else "no"

        out.append({
            "model": m,
            "coverage": {c: len(r) for c, r in sorted(conds.items())},
            "willingness": w,
            "stability_median": stab_med,
            "stability_p90": stab_p90,
            "stability_max": stab_max,
            "effects": effects,
            "largest_effect": biggest,
            "perm_p": pval,
            "verdict": verdict,
        })
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--min-runs", type=int, default=2)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    rows = cards(args.min_runs)
    if args.json:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
        return 0

    print("MODEL CARDS -- %d model(s) with >=%d valid runs in a wave cell"
          % (len(rows), args.min_runs))
    print("verdict = exact permutation test on the model's own runs, Bonferroni over contrasts")
    print("")
    print("  %-40s %5s %5s %6s %6s %8s  %s"
          % ("model", "smed", "sp90", "A->D", "P->D", "perm p", "verdict"))
    for r in sorted(rows, key=lambda r: -(r["stability_max"] or 0)):
        e = r["effects"]
        refuses = ",".join(c for c, v in sorted(r["willingness"].items())
                           if v["refusal_rate"] >= 0.5) or "-"
        print("  %-40s %5s %5s %6s %6s %8s  %s"
              % (r["model"][-40:],
                 r["stability_median"], r["stability_p90"],
                 e.get("A->D", "-"), e.get("P->D", "-"),
                 (r["perm_p"] if r["perm_p"] is not None else "-"), r["verdict"] or "-"))

    carries = [r for r in rows if r["verdict"] == "carries"]
    no = [r for r in rows if r["verdict"] == "no"]
    print("")
    print("  %d model(s) carry a claim; %d do not -- shuffling the condition labels among their"
          % (len(carries), len(no)))
    print("  own runs reproduces their largest effect often enough that the effect is not")
    print("  distinguishable from which runs landed in which arm.")
    if carries:
        print("  carries: %s" % ", ".join("%s (p=%s)" % (r["model"], r["perm_p"])
                                          for r in carries))
    zero = [r for r in no if (r["largest_effect"] or 0) == 0 and (r["stability_max"] or 0) == 0]
    if zero:
        print("")
        print("  %d of those are NEGATIVE CONTROLS rather than failures -- zero spread and zero"
              % len(zero))
        print("  effect, which is what a real null looks like: %s"
              % ", ".join(r["model"].split("/")[-1] for r in zero[:4]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
