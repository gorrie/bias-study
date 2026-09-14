#!/usr/bin/env python3
"""
robustness_checks.py — Two reviewer-requested robustness analyses over already-
scored runs. No API calls.

1. Multiple-comparisons correction (Benjamini-Hochberg FDR). With ~13 per-model
   tests per run, some "significant" deltas are expected by chance. We compute a
   bootstrap two-sided p-value per model (H0: mean per-question delta = 0), then
   apply BH-FDR at q=0.05 and report which effects survive correction.

2. Length / verbosity control. The score-3 "balanced essay" is long; a reviewer
   will ask whether the unmask effect is just a length artifact. We report the
   overall score~word_count correlation and the A-vs-B mean word counts — if A
   and B responses are similar length, the unmask delta is not length-driven.

Usage:
    python robustness_checks.py <run_date> [<run_date> ...]
"""
from __future__ import annotations

import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ci_analysis import load_scored, per_model_deltas  # noqa: E402
import eligibility as E  # noqa: E402  -- the single eligibility rule
from studypaths import (  # noqa: E402
    STUDY_DIR, RunNotFound, analysis_seed, resolve_run, stream)

# No module-level seed. See studypaths: one global stream made each model's p-value
# depend on how many models had been processed before it.
BOOTSTRAP_N = 10000


def bootstrap_p_two_sided(deltas: list[float], rng, n: int = BOOTSTRAP_N) -> float:
    """Bootstrap two-sided p-value for H0: mean delta = 0.
    p = 2 * min(P(boot mean <= 0), P(boot mean >= 0))."""
    k = len(deltas)
    if k < 2:
        return 1.0
    le = ge = 0
    for _ in range(n):
        s = 0.0
        for _ in range(k):
            s += deltas[rng.randrange(k)]
        m = s / k
        if m <= 0:
            le += 1
        if m >= 0:
            ge += 1
    p = 2.0 * min(le, ge) / n
    return min(p, 1.0)


def benjamini_hochberg(pvals: dict[str, float], q: float = 0.05) -> dict[str, bool]:
    """Return {model: survives_FDR} at level q."""
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    survive = {k: False for k in pvals}
    kmax = 0
    for i, (model, p) in enumerate(items, start=1):
        if p <= (i / m) * q:
            kmax = i
    for i, (model, p) in enumerate(items, start=1):
        if i <= kmax:
            survive[model] = True
    return survive


def pearson(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 2:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs) ** 0.5
    dy = sum((y - my) ** 2 for y in ys) ** 0.5
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def length_control(recs: list[dict]):
    xs, ys = [], []
    wc_a, wc_b = [], []
    for r in recs:
        # Eligibility, not a bare null check. A length control is the LAST place
        # to admit an empty or severed response: its whole subject is the relation
        # between response length and score, so a zero-length or cut-off record
        # poisons exactly the axis being measured.
        s = r.get("score_classifier") if E.is_eligible(r) else None
        w = r.get("word_count_total")
        if s is not None and w:
            xs.append(w)
            ys.append(s)
        if w:
            if r.get("condition") == "A":
                wc_a.append(w)
            elif r.get("condition") == "B":
                wc_b.append(w)
    corr = pearson(xs, ys)
    return corr, (statistics.mean(wc_a) if wc_a else None), (statistics.mean(wc_b) if wc_b else None)


def within_leg_fdr(run_dir, split_by: str = "position", q: float = 0.05) -> dict:
    """BH-FDR across model x paraphrase-leg tests for a paraphrase-robustness run.

    Restored 2026-09-12. `generate_charts.py:chart_paraphrase_robustness` has imported this
    name since commit 6a49792 and it was never defined, so `generate_charts.py --all-charts`
    -- the command WRITEUP-2026-05-26.md names in its Reproducibility section, and
    results/charts/README.md documents -- died with an ImportError after writing three of its
    four charts. Nothing caught it because no test imports this module's chart path and CI
    never reached the step.

    The leg is the paraphrase: this run asks the same neutral proposition three ways per
    topic (question ids T01-Q5 / T01-Q6 / T01-Q7), so the legs are the distinct question-id
    suffixes, named para1..paraN in sorted order. Within one leg a model's deltas are its
    per-topic B-A scores, which is the same quantity `per_model_deltas` computes for a whole
    run -- the difference is only that the pool is one leg rather than all of them.

    Correction is applied ACROSS every model x leg test at once, not within a model. That is
    the point of the chart: with 6 models x 3 legs there are 18 tests, and correcting within
    a model would leave the multiplicity the figure exists to show uncorrected.

    `split_by` is accepted for call compatibility and must be "position"; the legs are read
    from the question ids either way.
    """
    if split_by != "position":
        raise ValueError("within_leg_fdr only splits by position; got %r" % split_by)

    run_dir = Path(run_dir)
    run_key = run_dir.name
    recs = load_scored(run_dir)
    if not recs:
        return {"per_model": {}, "n_tests": 0, "n_survive": 0, "q": q}

    def leg_of(qid: str) -> str:
        return qid.rsplit("-", 1)[-1] if "-" in qid else qid

    legs = sorted({leg_of(r["question_id"]) for r in recs})
    leg_name = {raw: "para%d" % (i + 1) for i, raw in enumerate(legs)}

    seed = analysis_seed(run_key)
    per_model: dict = {}
    pvals: dict = {}
    for raw_leg in legs:
        subset = [r for r in recs if leg_of(r["question_id"]) == raw_leg]
        for model, deltas in per_model_deltas(subset).items():
            if len(deltas) < 2:
                continue
            name = leg_name[raw_leg]
            key = "%s\x1f%s" % (model, name)
            # One stream per model x leg. A shared stream would make each p-value depend on
            # how many cells had been drawn before it -- the exact bug the note above main()
            # records having already been fixed once in this file.
            pvals[key] = bootstrap_p_two_sided(deltas, stream(seed, run_key, model, name, "p"))
            per_model.setdefault(model, {"tests": {}})["tests"][name] = {
                "mean_delta": statistics.fmean(deltas),
                "n": len(deltas),
                "p": pvals[key],
            }

    survive = benjamini_hochberg(pvals, q=q)
    for key, ok in survive.items():
        model, name = key.split("\x1f")
        per_model[model]["tests"][name]["survives_fdr"] = ok

    return {
        "run": run_key,
        "legs": [leg_name[x] for x in legs],
        "per_model": per_model,
        "n_tests": len(pvals),
        "n_survive": sum(survive.values()),
        "q": q,
        "analysis_seed": seed,
    }


def main() -> int:
    # No arguments used to mean "loop over nothing, print nothing, exit 0" -- a silent pass
    # from the script whose job is to say whether the effects survive correction. The README
    # printed it argument-less as step 4 of "Reproduce it", so the documented way to run it
    # was the way that did nothing and said it worked.
    if len(sys.argv) < 2:
        print(__doc__.strip().splitlines()[-1] if __doc__ else "", file=sys.stderr)
        print("usage: robustness_checks.py <run_date> [<run_date> ...]", file=sys.stderr)
        print("  e.g. robustness_checks.py 2026-05-26-variance", file=sys.stderr)
        return 2

    failed = 0
    for rd in sys.argv[1:]:
        try:
            run_dir = resolve_run(rd)
        except RunNotFound as e:
            # Was `[skip]` + exit 0, so a missing run reported success with no FDR done.
            print(f"[error] {rd}: {e}", file=sys.stderr)
            failed += 1
            continue
        seed = analysis_seed(rd)
        recs = load_scored(run_dir)
        print(f"\n=== {rd} ===")
        dbm = per_model_deltas(recs)
        pvals = {m: bootstrap_p_two_sided(d, stream(seed, rd, m, "p"))
                 for m, d in dbm.items() if len(d) >= 2}
        survive = benjamini_hochberg(pvals, q=0.05)
        # n_raw used to call bootstrap_p_two_sided a SECOND time per model, drawing
        # fresh from the global stream, so the uncorrected count could disagree with
        # the p-values printed directly below it. Reuse the ones actually reported.
        n_raw = sum(1 for p in pvals.values() if p < 0.05)
        n_fdr = sum(survive.values())
        if not pvals:
            # "0/0 effects survive FDR correction" reads as CORRECTION APPLIED,
            # NOTHING SURVIVED. It means no test was run. ci_analysis.py handles the
            # identical input with "[error] no eligible A/B pairs" and exit 1; this
            # printed the serene version and exited 0, with the length-control line
            # below still printing and lending it the air of a measurement.
            print(f"  multiple-comparisons: CHECKED NOTHING -- 0 per-model tests were "
                  f"available in {rd}.")
            print(f"  No correction was applied and no effect was tested. This is an empty")
            print(f"  selection, not a null result.")
            failed += 1
            continue
        print(f"  multiple-comparisons (BH-FDR q=0.05 over {len(pvals)} per-model tests):")
        for m in sorted(pvals, key=lambda k: pvals[k]):
            mark = "SURVIVES" if survive[m] else "drops"
            print(f"    {m:<42} p={pvals[m]:.4f}  {mark}")
        print(f"  --> {n_fdr}/{len(pvals)} effects survive FDR correction")
        corr, wa, wb = length_control(recs)
        print(f"  length control: corr(score, word_count) = {corr:+.3f}" if corr is not None else "  length: n/a")
        if wa and wb:
            print(f"    mean word_count  A={wa:.0f}  B={wb:.0f}  (diff={wb-wa:+.0f}) "
                  f"-> {'similar lengths; unmask not length-driven' if abs(wb-wa) < 0.15*wa else 'length differs; check confound'}")
        print(f"  [raw] {n_raw}/{len(pvals)} uncorrected p<0.05   [seed] analysis_seed={seed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
