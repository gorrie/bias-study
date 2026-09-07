#!/usr/bin/env python3
"""The ablation arm, analysed in the order PREREG-2026-09-07-ablation-vs-prompt.md specifies.

WHAT THIS ANSWERS
-----------------
Does cutting the refusal direction out of a model's weights move its political answers more
than editing the prompt does? The weight rung is the strongest intervention this study can
apply, and until 2026-09-07 the arm rested on **one run per arm** -- which is how a 12-item
"inversion" got published off a sample that cannot support the word (CORRECTIONS #8).

THE ORDER IS THE PRE-REGISTRATION'S, AND STEP 1 CAN STOP THE ANALYSIS
---------------------------------------------------------------------
    1. ablator agreement   two abliterations of the SAME base, same condition. If that
                           exceeds stock-vs-ablated, STOP: every later number is a statement
                           about the ablator, not about abliteration.
    2. willingness         refusal rate on condition A, stock against each ablation.
    3. position            stock modal vs ablated modal, on P and on D separately.
    4. the comparison      weight-level effect against prompt-level effect (P->D), same base,
                           same n, same units.
    5. against the floor   both against the modal's own sampling error, side p90 3 /
                           endpoint p90 8. An effect that does not clear its floor is not one.

Running the steps in a different order, or reporting step 4 while step 1 fails, is the
researcher degree of freedom the pre-registration exists to remove. So the stopping rule is
enforced in code: `--force` is required to print steps 2-5 once step 1 has failed, and the
output says it was forced.

WHAT THE COLLECTION ACTUALLY YIELDED
------------------------------------
Of six base models, **three** produced a usable pair, and the three failures are findings
rather than gaps -- each is named with its cause:

    qwen38-27b    usable, and the only base with THREE ablators, so it carries step 1
    phi4-14b      usable
    qwen25-14b    usable -- the pair whose n=1 "inversion" was withdrawn
    gemma2-9b     ablated build emits SentencePiece word-boundary markers as literal text
    llama31-8b    ablated build answers in prose and never emits a sheet
    gemma4-12b    BOTH arms return empty responses, so this is the build, not the ablation

    python scripts/ablation_analysis.py
    python scripts/ablation_analysis.py --json
"""
from __future__ import annotations

import argparse
import collections
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import floor_table as F        # noqa: E402
import refusal_table as R      # noqa: E402

WAVE = os.path.join("runs", "2026-09-07-ablation-wave")
CONDITIONS = ("A", "P", "D")
MIN_SEEDS = 4

#: Download counts, so no reader has to guess which abliteration produced a number. Committed
#: in the pre-registration: "every build is named in every result, with its download count".
DOWNLOADS = {
    "hf.co/0bserverx/Qwen3.8-27B-Heretic-Abliterated-Uncensored-GGUF:Q4_K_M": "1.51M",
    "hf.co/OBLITERATUS/Qwen3.8-27B-OBLITERATED:Q4_K_M": "995k",
    "huihui-qwen38-27b-abliterated-uddw:Q4_K_M": "2.19M",
    "hf.co/culturerevolt/gemma-4-12b-heretic-abliterated-GGUF:Q4_K_M": "287k",
    "hf.co/OBLITERATUS/Gemma-4-12B-OBLITERATED:Q4_K_M": "26.7k",
    "huihui_ai/phi4-abliterated:latest": "n/a",
    "huihui_ai/qwen2.5-abliterate:14b": "n/a",
    "wash-gemma2-ablit:latest": "local",
    "wash-llama31-8b-ablit:latest": "local",
}

#: Quantisation mismatch is a DECLARED confounder in this arm, not a footnote. Named here so a
#: difference this build shows is attributed to the quantisation before the ablation.
QUANT_MISMATCH = {
    "huihui-qwen38-27b-abliterated-uddw:Q4_K_M":
        "UD-DW-Q4_K_M (Unsloth dynamic) against the stock arm's static Q4_K_M -- the repo "
        "ships no plain Q4_K_M at all",
}


def cells():
    """(base, arm, condition) -> [answer sheet], counting DISTINCT SEEDS among valid runs."""
    out = collections.defaultdict(dict)
    for path in sorted(glob.glob(os.path.join(STUDY, WAVE, "*", "*", "*.jsonl"))):
        parts = path.replace(os.sep, "/").split("/")
        base, arm = parts[-3], parts[-2]
        for line in io.open(path, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r.get("schema") != "compass-run/1" or not r.get("valid"):
                continue
            sheet = {a["q"]: a["position"] for a in r["answers"]}
            if len(set(sheet.values())) == 1:
                continue          # degenerate: classified in step 2, not paired here
            # ONE SEED, ONE SAMPLE. A repeated seed is not a second observation.
            out[(base, arm, r["condition"])].setdefault(r.get("seed"), sheet)
    return {k: list(v.values()) for k, v in out.items()}


def model_of(base, arm):
    """The model tag behind a (base, arm) cell, read from the runs rather than assumed."""
    for path in sorted(glob.glob(os.path.join(STUDY, WAVE, base, arm, "*.jsonl"))):
        for line in io.open(path, encoding="utf-8"):
            line = line.strip()
            if line:
                return json.loads(line).get("model")
    return None


def usable(c):
    """(base -> {arm -> {condition -> sheets}}) for cells at >= MIN_SEEDS."""
    per = collections.defaultdict(lambda: collections.defaultdict(dict))
    for (base, arm, cond), runs in c.items():
        if len(runs) >= MIN_SEEDS:
            per[base][arm][cond] = runs
    return per


def estimator():
    """The modal's own sampling error, both statistics. Step 5's denominator."""
    path = os.path.join(STUDY, "data", "modal-noise.json")
    if not os.path.exists(path):
        return None
    try:
        rec = json.load(io.open(path, encoding="utf-8"))
    except ValueError:
        return None
    return {"side_p90": rec.get("p90"), "endpoint_p90": rec.get("endpoint_p90")}


def step1_ablator_agreement(per):
    """Two ablations of one base, same condition. The pre-registered gate."""
    rows = []
    for base in sorted(per):
        arms = per[base]
        abl = sorted(a for a in arms if a.startswith("ablated"))
        if len(abl) < 2:
            continue
        for cond in CONDITIONS:
            have = [a for a in abl if cond in arms[a]]
            for i in range(len(have)):
                for j in range(i + 1, len(have)):
                    a, b = have[i], have[j]
                    side, end = F.both_stats(F.modal(arms[a][cond]), F.modal(arms[b][cond]))
                    rows.append({"base": base, "condition": cond, "a": a, "b": b,
                                 "side": side, "endpoint": end,
                                 "model_a": model_of(base, a), "model_b": model_of(base, b)})
    return rows


def step3_position(per):
    """stock modal vs each ablated modal, per condition."""
    rows = []
    for base in sorted(per):
        arms = per[base]
        if "stock" not in arms:
            continue
        for arm in sorted(a for a in arms if a.startswith("ablated")):
            for cond in CONDITIONS:
                if cond in arms["stock"] and cond in arms[arm]:
                    side, end = F.both_stats(F.modal(arms["stock"][cond]),
                                             F.modal(arms[arm][cond]))
                    rows.append({"base": base, "arm": arm, "condition": cond,
                                 "side": side, "endpoint": end,
                                 "model": model_of(base, arm),
                                 "n_stock": len(arms["stock"][cond]),
                                 "n_abl": len(arms[arm][cond])})
    return rows


def step4_weight_vs_prompt(per):
    """Weight-level effect against prompt-level effect, same base, same units."""
    rows = []
    for base in sorted(per):
        arms = per[base]
        if "stock" not in arms:
            continue
        st = arms["stock"]
        # Prompt-level, build held: P -> D on the stock build.
        prompt = None
        if "P" in st and "D" in st:
            prompt = F.both_stats(F.modal(st["P"]), F.modal(st["D"]))
        for arm in sorted(a for a in arms if a.startswith("ablated")):
            # Weight-level, condition held. Reported on BOTH conditions, because a weight
            # effect that appears under one instruction and not the other is a different
            # claim from one that appears under both.
            for cond in ("P", "D"):
                if cond in st and cond in arms[arm]:
                    weight = F.both_stats(F.modal(st[cond]), F.modal(arms[arm][cond]))
                    rows.append({"base": base, "arm": arm, "condition": cond,
                                 "weight_side": weight[0], "weight_endpoint": weight[1],
                                 "prompt_side": prompt[0] if prompt else None,
                                 "prompt_endpoint": prompt[1] if prompt else None,
                                 "model": model_of(base, arm)})
    return rows


def step2_willingness():
    """Refusal rate on condition A, stock against each ablation, from the whole record.

    Read through refusal_table's classifier rather than reimplemented: two definitions of
    "refused" is how one of them ends up permissive.
    """
    counts = collections.defaultdict(collections.Counter)
    for path in sorted(glob.glob(os.path.join(STUDY, WAVE, "*", "*", "*.jsonl"))):
        parts = path.replace(os.sep, "/").split("/")
        base, arm = parts[-3], parts[-2]
        for line in io.open(path, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r.get("condition") != "A":
                continue
            counts[(base, arm)][R.classify(r)] += 1
    rows = []
    for (base, arm), c in sorted(counts.items()):
        n = sum(c.values())
        rows.append({"base": base, "arm": arm, "n": n, "refused": c["refused"],
                     "valid": c["valid"], "other": n - c["refused"] - c["valid"],
                     "model": model_of(base, arm)})
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="print steps 2-5 even if step 1's stopping rule fired")
    args = ap.parse_args(argv)

    c = cells()
    per = usable(c)
    est = estimator()
    s1 = step1_ablator_agreement(per)
    s2 = step2_willingness()
    s3 = step3_position(per)
    s4 = step4_weight_vs_prompt(per)

    # THE STOPPING RULE, EVALUATED PER BASE AND LIKE-FOR-LIKE.
    #
    # A first version of this compared the WORST ablator disagreement found anywhere against
    # the MEDIAN stock-vs-ablated effect pooled across ALL bases. Two errors in one line, both
    # of which this project has convicted other work of:
    #
    #   * a max against a median -- different statistics, so the quotient of the comparison
    #     says nothing (the same shape as CORRECTIONS #9's withdrawn ratios), and
    #   * DIFFERENT POOLS -- the disagreement came from qwen38-27b, which is the only base with
    #     two ablations, while the effect median was dominated by qwen25-14b, a base with one.
    #     Comparing a nuisance measured on one model against an effect measured on another lets
    #     composition masquerade as a verdict.
    #
    # It fired on those numbers (3 > 2) and would have withheld steps 2-5 on a comparison that
    # was not entitled to an opinion.
    #
    # Correct form: for each base that HAS two ablations, compare that base's own ablator
    # disagreement against that base's own stock-vs-ablated effects, median against median and
    # max against max. A base with one ablation cannot be checked at all, and saying so is part
    # of the result rather than a gap in it.
    def med(v):
        v = sorted(v)
        return v[len(v) // 2] if v else None

    per_base = {}
    for base in sorted(per):
        dis = [r["side"] for r in s1 if r["base"] == base]
        eff = [r["side"] for r in s3 if r["base"] == base]
        if not eff:
            continue
        # ENDPOINT TOO. The pre-registration makes side-flips the headline and endpoints
        # "reported but not the headline" -- and on this arm the two disagree loudly enough
        # that reporting only the headline would hide the strongest signal in the collection:
        # ablator disagreement reaches 19 endpoint-flips on qwen38-27b under D, against an
        # endpoint estimator floor of 8, while every side-flip number on that base is 3 or
        # under. Direction is stable and INTENSITY is not.
        dis_e = [r["endpoint"] for r in s1 if r["base"] == base]
        eff_e = [r["endpoint"] for r in s3 if r["base"] == base]
        per_base[base] = {
            "dis_median": med(dis), "dis_max": max(dis) if dis else None,
            "eff_median": med(eff), "eff_max": max(eff) if eff else None,
            "dis_endpoint_max": max(dis_e) if dis_e else None,
            "eff_endpoint_max": max(eff_e) if eff_e else None,
            "checkable": bool(dis),
            "clears_floor": est and max(eff) > (est["side_p90"] or 0),
            "endpoint_dis_clears": bool(dis_e) and est
                                   and max(dis_e) > (est["endpoint_p90"] or 0),
        }
        b = per_base[base]
        b["confounded"] = bool(dis) and (b["dis_median"] >= b["eff_median"]
                                         or b["dis_max"] >= b["eff_max"])

    # Stop only if a base whose effect CLEARS the estimator floor is also confounded by its own
    # ablator variation. A base where nothing clears the floor has no effect to confound.
    stop = any(b["clears_floor"] and b["confounded"] for b in per_base.values())
    worst_disagree = max((r["side"] for r in s1), default=None)
    typical_effect = med([r["side"] for r in s3])

    if args.json:
        print(json.dumps({"estimator": est, "step1": s1, "step2": s2, "step3": s3,
                          "step4": s4, "stopping_rule_fired": stop,
                          "worst_ablator_disagreement": worst_disagree,
                          "median_stock_vs_ablated": typical_effect},
                         indent=2, ensure_ascii=False))
        return 0

    print("ABLATION ARM -- analysed in the pre-registered order")
    print("side-flips of 62; estimator floor side p90 %s, endpoint p90 %s"
          % (est["side_p90"] if est else "?", est["endpoint_p90"] if est else "?"))
    print("")
    print("BASES THAT PRODUCED A USABLE PAIR (>= %d distinct valid seeds per cell)" % MIN_SEEDS)
    for base in sorted(per):
        arms = sorted(per[base])
        print("  %-12s %s" % (base, ", ".join(
            "%s[%s]" % (a, "".join(sorted(per[base][a]))) for a in arms)))
    print("")

    print("STEP 1 -- ABLATOR AGREEMENT (the gate)")
    if not s1:
        print("  no base has two ablations at n>=%d, so this step cannot run." % MIN_SEEDS)
        print("  That is not a pass. Every later number is unqualified by ablator variation.")
    else:
        print("  %-12s %-3s %-34s %-34s %5s %5s"
              % ("base", "c", "ablation A", "ablation B", "side", "endp"))
        for r in sorted(s1, key=lambda r: -r["side"]):
            print("  %-12s %-3s %-34s %-34s %5d %5d"
                  % (r["base"], r["condition"], r["a"][:34], r["b"][:34],
                     r["side"], r["endpoint"]))
        print("")
        print("  PER BASE, like-for-like -- a base's own ablator spread against its own effect")
        print("  %-12s %9s %8s %9s %8s  %s"
              % ("base", "dis med", "dis max", "eff med", "eff max", "reading"))
        for base, b in sorted(per_base.items()):
            if not b["checkable"]:
                reading = ("one ablation only -- CANNOT be checked; its effect is unqualified "
                           "by ablator variation")
            elif b["confounded"]:
                reading = ("ablator spread >= effect -- not separable"
                           + (" (but neither clears the floor)" if not b["clears_floor"] else ""))
            else:
                reading = "effect exceeds ablator spread"
            print("  %-12s %9s %8s %9s %8s  %s"
                  % (base,
                     "-" if b["dis_median"] is None else b["dis_median"],
                     "-" if b["dis_max"] is None else b["dis_max"],
                     b["eff_median"], b["eff_max"], reading))
        endp = [(base, b) for base, b in sorted(per_base.items())
                if b.get("endpoint_dis_clears")]
        if endp:
            print("")
            print("  ON THE ENDPOINT STATISTIC, ABLATOR CHOICE IS NOT NOISE:")
            for base, b in endp:
                print("    %-12s ablator spread reaches %d endpoint-flips against a floor of "
                      "%s; its own ablation effect reaches %d"
                      % (base, b["dis_endpoint_max"],
                         est["endpoint_p90"] if est else "?", b["eff_endpoint_max"]))
            print("    On the endpoint statistic BOTH numbers clear their floor, and the")
            print("    ABLATOR SPREAD IS THE LARGER OF THE TWO. That is the pre-registered")
            print("    outcome 4, arriving on intensity rather than on direction: 'abliteration")
            print("    changes how strongly the model commits' is not separable from 'this")
            print("    particular ablator's choices change it'. Which abliteration you happen")
            print("    to download moves intensity as much as abliterating at all does.")
        if stop:
            print("")
            print("  *** STOPPING RULE FIRED -- OUTCOME 4. ***")
            print("  Two abliterations of the same base, under the same condition, differ by")
            print("  MORE than a typical stock-vs-ablated difference. So 'abliteration moves")
            print("  political answers' is not separable from 'this ablator's choices move")
            print("  them', and steps 2-5 would be statements about the ablator.")
            if not args.force:
                print("")
                print("  Steps 2-5 withheld. Re-run with --force to print them anyway; they")
                print("  are diagnostics at that point, not results.")
                return 0
            print("")
            print("  --force given: steps 2-5 follow AS DIAGNOSTICS, not as findings.")
        else:
            print("  Stopping rule did NOT fire; steps 2-5 stand as results.")
    print("")

    print("STEP 2 -- WILLINGNESS on condition A (the balance instruction)")
    print("  %-12s %-34s %4s %8s %6s %6s" % ("base", "arm", "n", "refused", "valid", "other"))
    for r in s2:
        print("  %-12s %-34s %4d %8d %6d %6d"
              % (r["base"], r["arm"][:34], r["n"], r["refused"], r["valid"], r["other"]))
    print("")

    print("STEP 3 -- POSITION, stock modal vs ablated modal")
    print("  %-12s %-30s %-3s %6s %6s %6s  %s"
          % ("base", "ablation", "c", "n_st", "n_ab", "side", "verdict vs estimator"))
    for r in sorted(s3, key=lambda r: (r["base"], r["arm"], r["condition"])):
        floor = est["side_p90"] if est else None
        verdict = "?" if floor is None else (
            "clears %d" % floor if r["side"] > floor else "AT OR UNDER the estimator")
        print("  %-12s %-30s %-3s %6d %6d %6d  %s"
              % (r["base"], r["arm"][:30], r["condition"], r["n_stock"], r["n_abl"],
                 r["side"], verdict))
    print("")

    print("STEP 4 -- WEIGHT-LEVEL against PROMPT-LEVEL, same base, same units")
    print("  %-12s %-30s %-3s %8s %8s  %s"
          % ("base", "ablation", "c", "weight", "prompt", "which is larger"))
    for r in sorted(s4, key=lambda r: (r["base"], r["arm"], r["condition"])):
        p = r["prompt_side"]
        if p is None:
            which = "prompt arm missing"
        elif r["weight_side"] > p:
            which = "WEIGHT"
        elif r["weight_side"] < p:
            which = "prompt"
        else:
            which = "equal"
        print("  %-12s %-30s %-3s %8d %8s  %s"
              % (r["base"], r["arm"][:30], r["condition"], r["weight_side"],
                 "n/a" if p is None else p, which))
    print("")

    print("BUILDS NAMED, with download counts and declared confounders")
    seen = set()
    for r in s3 + s4:
        m = r.get("model")
        if m and m not in seen:
            seen.add(m)
            note = QUANT_MISMATCH.get(m)
            print("  %-58s %s%s" % (m[:58], DOWNLOADS.get(m, "?"),
                                    "  QUANT MISMATCH: " + note if note else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
