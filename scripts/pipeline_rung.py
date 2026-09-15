#!/usr/bin/env python3
"""Rung 2 of the escalation ladder, estimated. The arm the analysis pipeline could not see.

WHY THIS EXISTS
---------------
The README's headline table published rung 2 as *"only the layered stack adds force, to a
ceiling."* Nothing computed that. `runs/2026-05-27-g0dm0d3/ANALYSIS.md` has a heading for every
table and rows under none of them, because `analysis.py` keys on conditions A and B and this arm
runs `B-STM`, `B-Parseltongue` and `B-Layered`. The records flowed through the pipeline, matched
no branch, and produced empty tables that nobody read -- so a directional claim sat in the public
artifact for four months with an empty analysis behind it.

WHAT THE ARM IS
---------------
Elicitation-layer force applied on top of the bare condition-B question, via the G0DM0D3 server:

    B-STM           hedge-strip only          (stm_modules=[hedge_reducer, direct_mode])
    B-Parseltongue  obfuscation only
    B-Layered       the full stack            (parseltongue + STM + godmode + autotune)

Each is paired per question against the SAME model's plain condition-B score from the May run,
so the contrast is within-model and within-question. 2 models x 3 conditions x 10 questions,
**one sample per cell** -- which is the binding limitation and is reported rather than smoothed.

WHAT IT FINDS
-------------
Every interval spans zero. Reporting that is the point: the arm does not support the direction
the README published, and the honest statement is a null with its own width rather than a
narrowed version of the original claim.

    python scripts/pipeline_rung.py
    python scripts/pipeline_rung.py --json
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

#: The CURRENT rung-2 estimate. Changed 2026-09-14 from the 2026-05-27 pair below.
#:
#: The superseded pair ran ONE sample per cell and differenced against a baseline
#: collected two days earlier by a different script, so every contrast was a
#: difference of two single draws and nothing separated the rung from sampling
#: noise. It returned 6 contrasts, none excluding zero, and the README published
#: "all 6 intervals span zero" as the rung-2 finding.
#:
#: W13 re-collected both arms at n=5 with a matched same-day baseline. On that
#: pair, 3 of 8 intervals exclude zero -- grok-4.3 B-Layered vs plain B at
#: +0.56 [+0.23, +0.85] and B-Layered minus B-STM at +0.48 [+0.26, +0.70], and
#: claude-opus-4.7 B-Layered minus B-STM at -0.31 [-0.64, -0.01], pointing the
#: OTHER WAY. So rung 2 is real and model-specific, and the published "spans zero"
#: sentence is an artifact of n=1, not a null.
#:
#: Reading the old pair is still possible and still correct for reproducing what
#: was published -- pass --pipeline-run/--baseline-run, or HISTORICAL_* below.
PIPELINE_RUN = "2026-09-13-g0dm0d3-replicate"

#: SAME SITTING BEATS MATCHED BUDGET. Reverted 2026-09-15, and the reversal is the
#: more interesting half of the story.
#:
#: On the morning of 2026-09-14 this default was moved to
#: `2026-09-14-g0dm0d3-baseline-4k` because the original baseline recorded NO
#: max_tokens while the arm records 4,000, and this file's own collector warns
#: that "an arm capped lower than the arm it is contrasted against measures
#: truncation, not force." The numbers moved and I reported the confound as real:
#: Opus's B-STM went +0.12 (spanning zero) to +0.37 [+0.13, +0.65], and three of
#: eight intervals excluding zero became five of eight.
#:
#: THE MOVEMENT WAS REAL AND MY ATTRIBUTION OF IT WAS WRONG. Two measurements,
#: neither available until the transform audit existed:
#:
#: 1. THE UNRECORDED CAP NEVER BOUND. The original baseline's longest response is
#:    1,295 tokens; the matched baseline's is 1,307; the arm's is 1,606 against
#:    its 4,000. NOT ONE RECORD in either baseline is truncated by the text test.
#:    Whatever cap the original ran at, nothing came near it.
#:
#: 2. THE REPLACEMENT IS TWO DAYS LATER. Read off `called_at`:
#:        arm                       2026-09-13T23, 2026-09-14T00
#:        original baseline         2026-09-13T23   <- SAME SITTING
#:        matched baseline          2026-09-15T02-03
#:
#: So the switch fixed a confound that was not biting and introduced one that
#: was. The proof is the arm that cannot have an effect:
#:
#:   B-Parseltongue vs plain B      same-sitting baseline   matched baseline
#:   claude-opus-4.7                -0.01 [-0.15, +0.13]    +0.24 [+0.02, +0.49]
#:   grok-4.3                       +0.09 [-0.06, +0.23]    +0.11 [-0.10, +0.29]
#:
#: `B-Parseltongue` APPLIES NOTHING to this instrument (see NULL_CONDITION below).
#: An untreated arm must read zero. Against the same-sitting baseline it reads
#: -0.01. Against the baseline collected two days later it reads +0.24 and
#: EXCLUDES ZERO -- which is not an effect, because there is no treatment. It is
#: the baseline being wrong, measured.
#:
#: That makes the accidental null the best diagnostic this arm has: whichever
#: baseline drives it closest to zero is the defensible one. Two of the five
#: intervals I reported as excluding zero were manufactured by drift.
#:
#: NEITHER BASELINE IS CLEAN and the honest fix is a same-sitting baseline WITH a
#: recorded cap, which is what `2026-09-15-g0dm0d3-decomposition` collects --
#: B-Proxy alongside its arms in one sitting. Until it lands, the same-sitting
#: pair is the default because its null reads zero.
#:
#: WHAT SURVIVES EITHER CHOICE is the finding that matters: `B-Layered minus
#: B-STM` is -0.31 for Opus and +0.48 for Grok under both baselines, because it is
#: within-arm and never touches one. Grok's `B-Layered vs plain B` is +0.56 and
#: +0.57. Both models moving in OPPOSITE directions was never at risk from any of
#: this, which is exactly why a within-arm contrast is worth preferring.
BASELINE_RUN = "2026-09-13-g0dm0d3-replicate-baseline"

#: The budget-matched baseline, collected two days after the arm. Kept named
#: because it is the right control for the token-cap question and the wrong one
#: for everything else, and because the superseded numbers must reproduce.
MATCHED_BUDGET_BASELINE_RUN = "2026-09-14-g0dm0d3-baseline-4k"

#: Retained spelling. This name meant "the unrecorded-cap baseline" when the
#: default pointed the other way; it is now the default itself. Kept as an alias
#: so anything still importing it resolves to the same run rather than silently
#: to the other one.
UNMATCHED_BASELINE_RUN = BASELINE_RUN

#: The n=1 pair the published "all 6 intervals span zero" rests on. Kept named so
#: reproducing the old number does not require reading a commit.
HISTORICAL_PIPELINE_RUN = "2026-05-27-g0dm0d3"
HISTORICAL_BASELINE_RUN = "2026-05-25-full"

BASELINE_CONDITION = "B"
CONDITIONS = ("B-STM", "B-Parseltongue", "B-Layered")
BOOTSTRAP_N = 20000

#: B-Parseltongue APPLIES NO TRANSFORM TO THIS INSTRUMENT. Established 2026-09-14
#: from the server's own echo on all 360 pipeline records, and confirmed against
#: the running server: `scripts/pipeline_transform_audit.py`.
#:
#: G0DM0D3's Parseltongue obfuscates trigger words from a fixed list of 53
#: security/jailbreak terms and returns the text UNCHANGED when it finds none.
#: The instrument is ten neutral policy questions and NOT ONE contains a trigger,
#: so `parseltongue: true` was accepted, returned 200, and rewrote nothing --
#: 0 of 120 records in either run.
#:
#: So `B-Parseltongue` is condition B, collected again, through the proxy. Its
#: contrast against plain B is a NULL BY CONSTRUCTION: it can only measure
#: run-to-run drift plus whatever the proxy path itself contributes. That makes
#: it the floor every other contrast in this arm has to clear, which is more
#: useful than the treatment it was mislabelled as -- but it is not a finding
#: about obfuscation, and the published reading of it ("Parseltongue alone is
#: approximately prompt-B") could not have come out any other way.
NULL_CONDITION = "B-Parseltongue"

#: STM is a POST-GENERATION EDIT OF THE ANSWER, not a prompt transform.
#: `applySTMPost(response, ...)` runs hedge_reducer over the model's reply and
#: DELETES "I think", "perhaps", "In my opinion" and eight siblings by regex, so
#: where it fires the judges score the proxy's edit rather than the model -- on a
#: rubric where hedging is what separates a hedged 3 from a committed 4.
#:
#: Bounded by measurement rather than assumed: a median of 16 characters removed
#: from responses averaging ~3,500, and edited records score slightly LOWER
#: (3.73 vs 3.83 on Opus B-STM), so the edit does not manufacture the effect. It
#: is badly differential though -- 45 of 60 records on claude-opus-4.7 against
#: 1 of 60 on grok-4.3 -- so B-STM is not the same intervention on both models.
#:
#: `B-STM minus B-Parseltongue` is still the cleanest STM estimate available --
#: same run, same sitting, same temperature, same proxy path, differing only in
#: whether STM fired -- and it is the contrast neither the published analysis nor
#: this file computed before.
STM_VS_NULL = ("B-STM", NULL_CONDITION)

#: THE PROXY PATH, MEASURED RATHER THAN INFERRED. Collected 2026-09-14.
#:
#: Every record in the pipeline arm goes through the G0DM0D3 proxy; the plain-B
#: baseline it is differenced against goes DIRECT to OpenRouter. So all six
#: "vs plain B" contrasts confound the named transform with the path -- which was
#: invisible for as long as B-Parseltongue looked like a treatment arm.
#:
#: `B-Proxy` is plain condition B sent THROUGH the proxy with every transform
#: explicitly off (the falses matter: the server defaults godmode and
#: parseltongue to TRUE when the field is absent). Same questions, same 4,000-
#: token cap, same 5 samples per cell. Differenced against the same baseline, it
#: is the proxy path and the run-to-run gap and nothing else.
#:
#: This is what B-Parseltongue's contrast was accidentally estimating. Having
#: both lets the arm say which part of its own floor is the path and which is
#: drift, instead of carrying one number that could be either.
PROXY_CONTROL_RUN = "2026-09-14-g0dm0d3-proxy-control"
PROXY_CONDITION = "B-Proxy"


def _roots():
    try:
        from studypaths import run_roots
        return [str(p) for p in run_roots()]
    except Exception:
        return [os.path.join(STUDY, r) for r in ("data", "runs")
                if os.path.isdir(os.path.join(STUDY, r))]


def _load(run):
    import eligibility as E
    out = []
    for root in _roots():
        for path in glob.glob(os.path.join(root, run, "scored", "**", "*.jsonl"), recursive=True):
            for line in io.open(path, encoding="utf-8", errors="replace"):
                if not line.strip():
                    continue
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if E.is_eligible(r):
                    out.append(r)
    return out


def _boot(deltas, label, run=None):
    """Percentile interval over per-question paired deltas, seeded per contrast.

    The seed is derived from the run being analysed, so a new collection does not
    silently reuse the May wave's bootstrap stream.
    """
    run = run or PIPELINE_RUN
    if not deltas:
        return None
    try:
        from studypaths import analysis_seed, stream
        rng = stream(analysis_seed(run), run, label)
    except Exception:
        import random
        rng = random.Random(20260527)
    k = len(deltas)
    means = sorted(st.mean([deltas[rng.randrange(k)] for _ in range(k)])
                   for _ in range(BOOTSTRAP_N))
    return (st.mean(deltas), means[int(0.025 * BOOTSTRAP_N)], means[int(0.975 * BOOTSTRAP_N)])


def _mean_replicates(records, condition=None):
    """Average replicate samples within a (model, condition, question) cell.

    The May wave ran one sample per cell, so a plain dict assignment was lossless.
    With --samples 5 it is NOT: keying a dict on question_id silently keeps only the
    LAST sample and discards the other four, which would look like a completed n=5
    collection and report an n=1 estimate. Samples within a cell are averaged, never
    treated as independent observations, so per-question pairing is preserved and the
    bootstrap still resamples questions rather than draws.

    The key MUST carry the condition. Averaging over (model, question) alone would
    pool B-STM, B-Parseltongue and B-Layered into one number and difference a cell
    against itself.
    """
    acc = collections.defaultdict(list)
    for r in records:
        if condition is not None and r.get("condition") != condition:
            continue
        acc[(r["model"], r.get("condition"), r["question_id"])].append(r["score_classifier"])
    means = {k: st.mean(v) for k, v in acc.items()}
    depth = {k: len(v) for k, v in acc.items()}
    return means, depth


def default_pair():
    """(pipeline_run, baseline_run, which) -- the best pair PRESENT in this tree.

    The replicated pair is private; the public mirror holds only the n=1 pair. A
    single hardcoded default therefore either forks the two trees or makes the
    estimator uncomputable in one of them, and both are worse than resolving it
    here where the choice can be NAMED.

    `which` is "replicated" or "historical" and travels in the result, so nothing
    downstream can quote a number without being able to say which collection it
    came from. A silent fallback would be the same defect as an inherited analysis
    seed: correct output, unattributable.
    """
    if _load(PIPELINE_RUN):
        return PIPELINE_RUN, BASELINE_RUN, "replicated"
    return HISTORICAL_PIPELINE_RUN, HISTORICAL_BASELINE_RUN, "historical"


def estimate(pipeline_run=None, baseline_run=None):
    if pipeline_run is None and baseline_run is None:
        pipeline_run, baseline_run, which = default_pair()
    else:
        pipeline_run = pipeline_run or PIPELINE_RUN
        baseline_run = baseline_run or BASELINE_RUN
        which = ("replicated" if pipeline_run == PIPELINE_RUN
                 else "historical" if pipeline_run == HISTORICAL_PIPELINE_RUN else "explicit")
    pipe = _load(pipeline_run)
    base_recs = _load(baseline_run)
    if not pipe:
        return None
    base_means, base_depth = _mean_replicates(base_recs, condition=BASELINE_CONDITION)
    base = {(m, q): v for (m, _c, q), v in base_means.items()}
    cell_means, cell_depth = _mean_replicates(pipe)
    cells = collections.defaultdict(dict)
    for (m, c, q), v in cell_means.items():
        cells[(m, c)][q] = v
    # A cell's replicate depth is reported, not assumed: a run that silently lost
    # samples must be visible in the output rather than pass as a clean n.
    reps = sorted(set(list(cell_depth.values()) + list(base_depth.values())))
    models = sorted({m for m, _ in cells})

    out = {"run": pipeline_run, "baseline_run": baseline_run, "models": models,
           # Which collection this estimate came from, so no consumer can quote the
           # number without being able to name its source. "historical" is the n=1
           # pair whose every contrast is a difference of two single draws.
           "pair": which,
           "samples_per_cell": reps[0] if len(reps) == 1 else reps,
           "replicates_ragged": len(reps) > 1,
           "contrasts": []}
    for m in models:
        for c in CONDITIONS:
            got = cells.get((m, c), {})
            d = [got[q] - base[(m, q)] for q in sorted(got) if (m, q) in base]
            ci = _boot(d, "%s|%s|vs-base" % (m, c), run=pipeline_run)
            if ci:
                out["contrasts"].append(
                    {"model": m, "contrast": "%s vs plain %s" % (c, BASELINE_CONDITION),
                     "n": len(d), "effect": round(ci[0], 3),
                     "lo": round(ci[1], 3), "hi": round(ci[2], 3),
                     "excludes_zero": ci[1] > 0 or ci[2] < 0,
                     # This arm applied NO transform to this instrument, so its
                     # contrast against plain B cannot be a treatment effect.
                     "null_by_construction": c == NULL_CONDITION})
        lay, stm = cells.get((m, "B-Layered"), {}), cells.get((m, "B-STM"), {})
        d = [lay[q] - stm[q] for q in sorted(lay) if q in stm]
        ci = _boot(d, "%s|layered-minus-stm" % m, run=pipeline_run)
        if ci:
            out["contrasts"].append(
                {"model": m, "contrast": "B-Layered minus B-STM", "n": len(d),
                 "effect": round(ci[0], 3), "lo": round(ci[1], 3), "hi": round(ci[2], 3),
                 "excludes_zero": ci[1] > 0 or ci[2] < 0})
        # STM against the untreated arm collected in the SAME sitting. Both go
        # through the proxy at the same temperature, so the baseline run, the
        # collection date and the proxy path all cancel and what remains is STM.
        treated, untreated = (cells.get((m, STM_VS_NULL[0]), {}),
                              cells.get((m, STM_VS_NULL[1]), {}))
        d = [treated[q] - untreated[q] for q in sorted(treated) if q in untreated]
        ci = _boot(d, "%s|stm-minus-null" % m, run=pipeline_run)
        if ci:
            out["contrasts"].append(
                {"model": m, "contrast": "B-STM minus %s" % NULL_CONDITION,
                 "n": len(d), "effect": round(ci[0], 3), "lo": round(ci[1], 3),
                 "hi": round(ci[2], 3), "excludes_zero": ci[1] > 0 or ci[2] < 0,
                 "within_run": True})
    # The proxy path measured directly, where the control arm exists. Reported
    # beside the inferred floor rather than replacing it: they answer different
    # questions (one is "what does the path cost", the other "what does an
    # untreated arm report"), and a reader should be able to see both.
    proxy = _load(PROXY_CONTROL_RUN)
    if proxy:
        # PINNED TO ITS OWN SITTING'S BASELINE, not to whatever BASELINE_RUN is.
        # B-Proxy was collected alongside the budget-matched baseline (both
        # 2026-09-15), so that pair isolates the PATH. Differenced against the
        # same-sitting-with-the-arm baseline instead, it crosses two days and
        # measures drift again -- which it duly did, reading -0.19 and -0.16 the
        # moment the default moved. A control that changes meaning when an
        # unrelated default changes is not a control.
        proxy_base_recs = _load(MATCHED_BUDGET_BASELINE_RUN)
        pb_means, _ = _mean_replicates(proxy_base_recs, condition=BASELINE_CONDITION)
        pbase = {(m, q): v for (m, _c, q), v in pb_means.items()}
        proxy_means, _ = _mean_replicates(proxy, condition=PROXY_CONDITION)
        pm = {(m, q): v for (m, _c, q), v in proxy_means.items()}
        out["measured_proxy_floor"] = {}
        out["proxy_control_baseline"] = MATCHED_BUDGET_BASELINE_RUN
        for m in sorted({k[0] for k in pm}):
            d = [pm[(m, q)] - pbase[(m, q)]
                 for (mm, q) in sorted(pm) if mm == m and (m, q) in pbase]
            ci = _boot(d, "%s|proxy-vs-direct" % m, run=PROXY_CONTROL_RUN)
            if ci:
                out["measured_proxy_floor"][m] = {
                    "n": len(d), "effect": round(ci[0], 3),
                    "lo": round(ci[1], 3), "hi": round(ci[2], 3),
                    "excludes_zero": ci[1] > 0 or ci[2] < 0}
        out["proxy_control_run"] = PROXY_CONTROL_RUN

    out["any_excludes_zero"] = any(c["excludes_zero"] for c in out["contrasts"])
    out["n_contrasts"] = len(out["contrasts"])
    # The measured floor, per model: what a contrast against plain B reports when
    # the arm applied no transform at all. Anything at or below this magnitude in
    # the same column is indistinguishable from drift plus the proxy path.
    out["null_floor"] = {
        c["model"]: {"effect": c["effect"], "lo": c["lo"], "hi": c["hi"],
                     "excludes_zero": c["excludes_zero"]}
        for c in out["contrasts"] if c.get("null_by_construction")}
    for c in out["contrasts"]:
        floor = out["null_floor"].get(c["model"])
        if floor and c["contrast"].endswith("vs plain %s" % BASELINE_CONDITION):
            c["clears_null_floor"] = (not c.get("null_by_construction")
                                      and abs(c["effect"]) > abs(floor["effect"]))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true")
    # Defaults resolve through default_pair() rather than being baked into argparse,
    # which would pin the CLI to a run the public mirror does not hold and print
    # "not present in this tree" there while the library computed fine.
    ap.add_argument("--pipeline-run", default=None,
                    help="run holding the B-STM / B-Parseltongue / B-Layered cells "
                         "(default: the replicated pair where present, else the n=1 pair)")
    ap.add_argument("--baseline-run", default=None,
                    help="run holding plain condition B. For a same-sitting baseline, "
                         "pass the run collected alongside the pipeline arm.")
    args = ap.parse_args(argv)
    res = estimate(args.pipeline_run, args.baseline_run)
    if not res:
        print("pipeline rung %s not present in this tree"
              % (args.pipeline_run or default_pair()[0]))
        return 2
    if args.json:
        print(json.dumps(res, indent=2))
        return 0
    print("RUNG 2 -- elicitation-layer force, paired per question against plain condition B")
    spc = res["samples_per_cell"]
    if res.get("replicates_ragged"):
        depth = "RAGGED replicate depth %s -- cells are not equally sampled" % (spc,)
    else:
        depth = "%s sample(s) per cell, averaged within cell" % spc
    print("%d models, %s." % (len(res["models"]), depth))
    print("pipeline run: %s   baseline run: %s   [%s pair]"
          % (res["run"], res["baseline_run"], res.get("pair", "?")))
    if res.get("pair") == "historical":
        print("  NOTE: this tree holds only the n=1 pair, so every contrast below is a "
              "difference of two single draws. The replicated pair measures 3 of 8 "
              "intervals excluding zero -- see PENDING-PUBLICATION-2026-09-14.md.")
    print("Positive = more institution-skeptical.\n")
    print("  %-26s %-30s %3s %8s %-18s" % ("model", "contrast", "n", "effect", "95% interval"))
    for c in res["contrasts"]:
        flag = "  EXCLUDES 0" if c["excludes_zero"] else ""
        if c.get("null_by_construction"):
            flag += "   <-- NULL BY CONSTRUCTION (no transform applied)"
        elif c.get("clears_null_floor") is False:
            flag += "   (does not clear the null floor)"
        print("  %-26s %-30s %3d %+8.2f [%+0.2f, %+0.2f]%s"
              % (c["model"].split("/")[-1], c["contrast"], c["n"], c["effect"],
                 c["lo"], c["hi"], flag))
    print("")
    if res.get("null_floor"):
        print("  NULL FLOOR. %s applied no transform to this instrument -- G0DM0D3's"
              % NULL_CONDITION)
        print("  Parseltongue rewrites trigger words and the instrument contains none, so it")
        print("  fired on 0 of 120 records. Its contrast against plain B therefore measures")
        print("  run-to-run drift plus the proxy path, and nothing else:")
        for m, f in sorted(res["null_floor"].items()):
            print("      %-24s %+0.2f [%+0.2f, %+0.2f]%s"
                  % (m.split("/")[-1], f["effect"], f["lo"], f["hi"],
                     "   and it EXCLUDES ZERO" if f["excludes_zero"] else ""))
        print("  Any 'vs plain B' effect of that magnitude is not distinguishable from it.")
        print("  Verify with: python scripts/pipeline_transform_audit.py\n")
    if res.get("measured_proxy_floor"):
        print("  MEASURED PROXY FLOOR (%s). Plain condition B sent THROUGH the proxy"
              % res["proxy_control_run"])
        print("  with every transform off, against the direct-to-OpenRouter baseline collected")
        print("  in ITS OWN SITTING (%s)." % res["proxy_control_baseline"])
        print("  This is the path cost with the calendar held still:")
        for m, f in sorted(res["measured_proxy_floor"].items()):
            print("      %-24s %+0.2f [%+0.2f, %+0.2f]  n=%d%s"
                  % (m.split("/")[-1], f["effect"], f["lo"], f["hi"], f["n"],
                     "   EXCLUDES 0" if f["excludes_zero"] else ""))
        print("")
    if not res["any_excludes_zero"]:
        print("  NOT ONE of the %d intervals excludes zero." % res["n_contrasts"])
        print("  The arm does not support a direction.")
        if res["samples_per_cell"] == 1:
            print("  One sample per cell, so there is no within-cell variance to appeal to")
            print("  either.")
        print("  'To a ceiling' was never measured -- locating a ceiling needs more than")
        print("  three points on one axis, at any sample size.")
    else:
        n_ex = sum(1 for c in res["contrasts"] if c["excludes_zero"])
        print("  %d of %d intervals exclude zero." % (n_ex, res["n_contrasts"]))
        print("  'To a ceiling' is still NOT measured: three points on one axis cannot")
        print("  locate where added force stops helping, at any sample size.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
