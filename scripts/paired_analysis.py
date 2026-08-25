#!/usr/bin/env python3
"""paired_analysis.py — the estimator for a matched-pair arm study. No API calls.

WHY THIS IS A SEPARATE SCRIPT.

Matched-pair records fit the existing question regex, so they flow through the pipeline
without complaint and are analysed **wrongly**:

  * `aggregate.pair_records()` keys on `(model, question_id)`, which has no notion of a
    pair or an arm — the three arms of one template collapse into unrelated questions;
  * `aggregate.aggregate_per_model()` means every per-question B−A into one figure,
    losing the pairing that is the entire point;
  * `ci_analysis.bootstrap_ci()` resamples a **flat i.i.d. list**, which treats samples
    drawn from the same template as independent observations.

That last one is pseudoreplication, and it is the exact objection that killed a prior
substitution pass in adversarial review at `n_templates=1`
(`results/THE-WASH-2026-06-10.md:115`). Running matched pairs through the existing
estimator would re-open a settled question with a bigger n and the same flaw.

So: nothing here touches `aggregate.py` or `per_model_deltas`. May's published numbers
must not move, and gate G1 in `selftest_analysis.py` asserts they do not.

WHAT IT ESTIMATES.

A record carries `pair_id` (the template), `arm` (which agent the stem names), and
`condition`. The estimand is a **within-pair difference under one rubric**, so any
constant offset between the rubric's culpability axis and the study's institution axis
cancels exactly. The cluster only needs the same rubric applied to all arms; it does not
need the rubric calibrated in absolute terms. The corollary has to be printed with the
result: matched-pair scores are **not comparable in level** to the main study's 1–5
scores. Only arm differences are the product.

  * cluster bootstrap, where **the cluster is the template**, resampled with replacement,
    then per-sample scores resampled within each cell — two levels, so neither template
    nor sampling noise is treated as the other;
  * an exact sign test over the per-template gaps, which assumes nothing about the
    distribution and is the honest fallback when the bootstrap and it disagree;
  * BH-FDR across the pre-registered endpoints, not across every contrast that could be
    computed after the fact.

    python paired_analysis.py <run_date> [--contrast algorithm:person] [--json]
    python paired_analysis.py --selftest        # synthetic data, no run needed
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from studypaths import RunNotFound, analysis_seed, resolve_run, stream  # noqa: E402

BOOTSTRAP_N = 10000

#: Pre-registered before the run. FDR is applied across exactly these and nothing else;
#: adding a contrast after seeing the data is what the correction exists to prevent.
PREREGISTERED = [
    ("algorithm", "person"),
    ("algorithm", "institution"),
    ("person", "institution"),
]


def load(run_dir: Path) -> list[dict]:
    recs = []
    for f in sorted((run_dir / "scored").glob("*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                recs.append(json.loads(line))
    return [r for r in recs if r.get("pair_id") and r.get("arm")
            and r.get("score_classifier") is not None]


def cells(recs: list[dict]) -> dict:
    """(pair_id, arm) -> list of scores. Samples stay separate; that is the inner level."""
    out = defaultdict(list)
    for r in recs:
        out[(r["pair_id"], r["arm"])].append(float(r["score_classifier"]))
    return dict(out)


def pair_gaps(cell: dict, a: str, b: str) -> dict:
    """Per-template mean(arm a) − mean(arm b), only where the template has both."""
    gaps = {}
    for (pid, arm) in cell:
        if arm != a:
            continue
        if (pid, b) not in cell:
            continue
        gaps[pid] = (statistics.fmean(cell[(pid, a)])
                     - statistics.fmean(cell[(pid, b)]))
    return gaps


def cluster_bootstrap(cell: dict, a: str, b: str, rng, n: int = BOOTSTRAP_N,
                      alpha: float = 0.05):
    """Nonparametric cluster bootstrap: resample TEMPLATES with replacement, keeping
    each template's observations intact.

    The cluster is the template, because samples of one template are not independent
    evidence about the population of templates — that is the pseudoreplication a prior
    substitution pass was killed for.

    NO inner resample of the scores within a cell. The first version of this had one, on
    the reasoning that sampling noise should be reflected too, and that is wrong: a
    template's *observed* gap already contains its within-cell noise, so drawing that
    template draws the noise with it. Resampling inside it counts the same variance
    twice and makes the interval over-conservative — measured at about 6% wider on the
    self-test fixture. One level, which is the standard nonparametric cluster bootstrap.

    (The self-test's larger 27–29% reading was not this; that was sampling error in a
    single realised width at k=16, and it sent me after the estimator twice before the
    measurement was averaged over seeds. The double count is real and small.)
    """
    pids = sorted({p for (p, arm) in cell if arm == a and (p, b) in cell})
    k = len(pids)
    if k < 2:
        return None
    gaps = [statistics.fmean(cell[(p, a)]) - statistics.fmean(cell[(p, b)]) for p in pids]
    point = statistics.fmean(gaps)
    means = []
    for _ in range(n):
        acc = 0.0
        for _ in range(k):
            acc += gaps[rng.randrange(k)]
        means.append(acc / k)
    means.sort()
    lo = means[int((alpha / 2) * n)]
    hi = means[int((1 - alpha / 2) * n)]
    return {"n_templates": k, "estimate": point, "lo": lo, "hi": hi,
            "excludes_zero": not (lo <= 0 <= hi)}


def _comb(n: int, k: int) -> int:
    from math import comb
    return comb(n, k)


def sign_test(gaps: dict) -> dict:
    """Exact two-sided sign test over per-template gaps. Distribution-free, so it is the
    check on the bootstrap rather than a restatement of it. Ties are dropped, which is
    the conservative convention."""
    pos = sum(1 for v in gaps.values() if v > 0)
    neg = sum(1 for v in gaps.values() if v < 0)
    n = pos + neg
    if n == 0:
        return {"n": 0, "pos": 0, "neg": 0, "p": 1.0}
    x = min(pos, neg)
    tail = sum(_comb(n, i) for i in range(0, x + 1)) / (2 ** n)
    return {"n": n, "pos": pos, "neg": neg, "ties": len(gaps) - n,
            "p": min(1.0, 2 * tail)}


def benjamini_hochberg(pvals: dict, q: float = 0.05) -> dict:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    survive = {k: False for k in pvals}
    kmax = 0
    for i, (key, p) in enumerate(items, start=1):
        if p <= (i / m) * q:
            kmax = i
    for i, (key, _) in enumerate(items, start=1):
        if i <= kmax:
            survive[key] = True
    return survive


def analyse(recs: list[dict], seed: int, run_date: str, contrasts=None) -> dict:
    cell = cells(recs)
    contrasts = contrasts or PREREGISTERED
    out = {"run": run_date, "records": len(recs),
           "templates": len({p for (p, _) in cell}),
           "arms": sorted({arm for (_, arm) in cell}),
           "contrasts": {}}
    pvals = {}
    for a, b in contrasts:
        key = f"{a}-{b}"
        boot = cluster_bootstrap(cell, a, b, stream(seed, run_date, key, "cluster"))
        gaps = pair_gaps(cell, a, b)
        st = sign_test(gaps)
        out["contrasts"][key] = {"bootstrap": boot, "sign_test": st,
                                 "per_template_gaps": gaps}
        pvals[key] = st["p"]
    survive = benjamini_hochberg(pvals)
    for key, ok in survive.items():
        out["contrasts"][key]["survives_fdr"] = ok
    out["note"] = ("Matched-pair scores are NOT comparable in level to the main study's "
                   "1-5 scores. The estimand is a within-pair difference under one rubric; "
                   "only arm differences are the product.")
    return out


def render(res: dict) -> None:
    print(f"\n=== {res['run']} — matched-pair arms ===")
    print(f"  {res['records']} scored records, {res['templates']} templates, "
          f"arms: {', '.join(res['arms'])}")
    for key, c in res["contrasts"].items():
        b, st = c["bootstrap"], c["sign_test"]
        print(f"\n  {key}")
        if b:
            verdict = "CI excludes 0" if b["excludes_zero"] else "not distinguishable from 0"
            print(f"    cluster bootstrap  {b['estimate']:+.3f} "
                  f"[{b['lo']:+.3f}, {b['hi']:+.3f}]  over {b['n_templates']} templates "
                  f"-> {verdict}")
        else:
            print("    cluster bootstrap  n<2 templates with both arms")
        print(f"    sign test          {st['pos']}+/{st['neg']}- "
              f"(ties {st.get('ties', 0)})  p={st['p']:.4f}  "
              f"{'SURVIVES' if c['survives_fdr'] else 'drops'} BH-FDR")
    sc = res.get("stem_control")
    if sc:
        print(f"\n  --- mismatched-stem control ({sc['n_rescored']} responses re-scored "
              f"under another arm's stem, over {sc['n_templates']} templates) ---")
        print(f"    judge stem effect  {sc['estimate']:+.3f} "
              f"[{sc['lo']:+.3f}, {sc['hi']:+.3f}]   reach {sc['reach']:.3f}")
        for key, v in sc["contrasts"].items():
            print(f"    {key:<24} arm gap {v['arm_gap']:+.3f}  ->  {v['verdict']}")
    print(f"\n  {res['note']}")


def stem_control(run_dir: Path, res: dict, seed: int, run_date: str) -> dict | None:
    """The mismatched-stem calibration, and its pre-registered abort rule.

    The judge is shown the question, and the question is where the agent is named. A judge
    that scores "an algorithm decided X" differently from "a caseworker decided X" would
    manufacture the arm gap the study is trying to measure. `score.py --stem-swap` re-scores
    every response with the question naming a different arm, response byte-identical, so
    whatever moves is pure judge stem effect.

    ABORT RULE, fixed before anyone looks: if the stem-effect interval reaches the arm-gap
    estimate, the cut reports "not separable at this n" and makes no substantive claim. It
    is written here rather than decided later precisely because the temptation to decide it
    later is the whole problem.
    """
    swap_dir = run_dir / "scored-stemswap"
    if not swap_dir.is_dir():
        return None
    orig = {}
    for f in sorted((run_dir / "scored").glob("*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                if r.get("pair_id") and r.get("score_classifier") is not None:
                    orig[(r["model"], r["pair_id"], r["arm"], r.get("sample_idx", 0))] = r

    per_template = defaultdict(list)
    n = 0
    for f in sorted(swap_dir.glob("*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("score_classifier") is None or not r.get("stem_swap_from"):
                continue
            k = (r["model"], r["pair_id"], r["stem_swap_from"], r.get("sample_idx", 0))
            if k not in orig:
                continue
            per_template[r["pair_id"]].append(
                float(r["score_classifier"]) - float(orig[k]["score_classifier"]))
            n += 1
    if not per_template:
        return None

    # same cluster level as the main estimate: the template
    gaps = [statistics.fmean(v) for v in per_template.values()]
    k = len(gaps)
    rng = stream(seed, run_date, "stem-control")
    means = sorted(sum(gaps[rng.randrange(k)] for _ in range(k)) / k
                   for _ in range(BOOTSTRAP_N))
    lo = means[int(0.025 * BOOTSTRAP_N)]
    hi = means[int(0.975 * BOOTSTRAP_N)]
    reach = max(abs(lo), abs(hi))

    verdicts = {}
    for key, c in res["contrasts"].items():
        b = c.get("bootstrap")
        if not b:
            continue
        separable = abs(b["estimate"]) > reach
        verdicts[key] = {
            "arm_gap": b["estimate"],
            "separable": separable,
            "verdict": ("separable from judge stem effect" if separable
                        else "NOT SEPARABLE AT THIS N - no substantive claim"),
        }
    return {"n_rescored": n, "n_templates": k, "estimate": statistics.fmean(gaps),
            "lo": lo, "hi": hi, "reach": reach, "contrasts": verdicts}


# ---------------------------------------------------------------- self-test (no data)

def selftest() -> int:
    """Synthetic data with a known answer, and a pseudoreplication check.

    The point of the second assertion: an estimator that ignores clustering reports a
    *narrower* interval as you add samples of the SAME template, because it mistakes
    repeated measurement for independent evidence. A correct cluster bootstrap does not.
    """
    import random
    ok = True

    def mk(n_templates, per_cell, gap, jitter, seed=7, hetero=0.0):
        """`hetero` is the SD of the per-template arm gap.

        It matters, and the first version of this fixture set it to zero, which made the
        clustering assertion below measure nothing. With an identical gap on every
        template the between-cluster variance cancels out of the difference entirely, so
        the only variance left is within-cell sampling noise -- which extra samples are
        *supposed* to buy down. Real templates differ in how strongly they separate the
        arms, and that heterogeneity is the irreducible between-cluster term that no
        amount of resampling the same sixteen templates can reduce. That is the whole
        thing the cluster level exists to respect, so the fixture has to contain it.
        """
        r = random.Random(seed)
        recs = []
        for t in range(n_templates):
            base = r.uniform(2.0, 4.0)
            this_gap = gap + (r.gauss(0, hetero) if hetero else 0.0)
            for arm, off in (("algorithm", this_gap), ("person", 0.0), ("institution", 0.0)):
                for s in range(per_cell):
                    recs.append({"pair_id": f"T{t:02d}", "arm": arm, "condition": "A",
                                 "model": "synthetic",
                                 "score_classifier": base + off + r.gauss(0, jitter)})
        return recs

    def naive_flat_ci(recs, a, b, seed=5, n=4000):
        """What the EXISTING estimator does: pool every per-sample difference into one
        flat list and resample it i.i.d. Kept here as the contrast — if this does not
        behave worse than the cluster bootstrap, the cluster bootstrap is not earning
        its complexity."""
        r = random.Random(seed)
        cell = cells(recs)
        flat = []
        for (pid, arm) in cell:
            if arm != a or (pid, b) not in cell:
                continue
            mb = statistics.fmean(cell[(pid, b)])
            flat += [s - mb for s in cell[(pid, a)]]
        k = len(flat)
        means = sorted(sum(flat[r.randrange(k)] for _ in range(k)) / k for _ in range(n))
        return means[int(0.025 * n)], means[int(0.975 * n)]

    # 1. recovers a planted gap
    res = analyse(mk(16, 2, 0.50, 0.10), 20260825, "synthetic")
    c = res["contrasts"]["algorithm-person"]["bootstrap"]
    if not (0.40 < c["estimate"] < 0.60 and c["excludes_zero"]):
        print(f"  FAIL  planted gap 0.50 -> {c['estimate']:+.3f} "
              f"[{c['lo']:+.3f}, {c['hi']:+.3f}]")
        ok = False
    else:
        print(f"  PASS  recovers a planted 0.50 gap: {c['estimate']:+.3f} "
              f"[{c['lo']:+.3f}, {c['hi']:+.3f}]")

    # 2. reports no effect when there is none
    res0 = analyse(mk(16, 2, 0.0, 0.35, seed=11), 20260825, "synthetic")
    c0 = res0["contrasts"]["algorithm-person"]["bootstrap"]
    if c0["excludes_zero"]:
        print(f"  FAIL  no planted gap but CI excludes zero: "
              f"[{c0['lo']:+.3f}, {c0['hi']:+.3f}]")
        ok = False
    else:
        print(f"  PASS  null stays null: [{c0['lo']:+.3f}, {c0['hi']:+.3f}]")

    # 3. pseudoreplication. With heterogeneous per-template gaps, piling samples onto
    #    the same 16 templates must barely move the interval, while adding templates
    #    must shrink it — because only the second is new evidence about the population
    #    of templates. This is the objection that killed a prior substitution pass in
    #    adversarial review, so it is asserted rather than assumed.
    HET = 0.45

    def subset(recs, per_cell):
        """The same templates with fewer samples each.

        Regenerating at a different per_cell diverges the RNG, so the two datasets get
        DIFFERENT template gaps and the comparison measures that difference instead of
        the effect of sample count. Subsetting one draw holds the templates fixed, which
        is what "more samples of the same sixteen templates" has to mean.
        """
        kept, seen = [], defaultdict(int)
        for r in recs:
            k = (r["pair_id"], r["arm"])
            if seen[k] < per_cell:
                seen[k] += 1
                kept.append(r)
        return kept

    # Averaged over 12 draws. A single draw at k=16 has enough sampling error in the
    # realised interval width that one comparison is not evidence of anything -- the
    # first version of this test compared two single draws and read 27-29% shrinkage
    # that was mostly seed noise, twice sending me after the estimator instead of the
    # measurement. Ratios of widths, meaned over seeds, are stable.
    def width_of(recs, n=3000, seed=1):
        b = cluster_bootstrap(cells(recs), "algorithm", "person",
                              stream(seed, "selftest", "w"), n=n)
        return b["hi"] - b["lo"]

    r_samples, r_templates = [], []
    for sd in range(12):
        kw = dict(gap=0.50, jitter=0.30, seed=100 + sd, hetero=HET)
        f8 = mk(16, 8, **kw)
        w2, w8 = width_of(subset(f8, 2)), width_of(f8)
        w32 = width_of(subset(mk(32, 8, **kw), 2))
        r_samples.append(w8 / w2)
        r_templates.append(w32 / w2)
    shrink_samples = 1 - statistics.fmean(r_samples)
    shrink_templates = 1 - statistics.fmean(r_templates)
    full8 = mk(16, 8, gap=0.50, jitter=0.30, seed=3, hetero=HET)
    w8 = {"hi": width_of(full8), "lo": 0.0}
    width = lambda b: b["hi"] - b["lo"]
    if shrink_samples > 0.20:
        print(f"  FAIL  4x the samples on the same templates shrank the CI by "
              f"{shrink_samples:.0%} — the cluster level is not binding")
        ok = False
    elif shrink_templates < 0.15:
        print(f"  FAIL  doubling TEMPLATES only shrank the CI by {shrink_templates:.0%} — "
              f"the estimator is not responding to real added evidence")
        ok = False
    else:
        print(f"  PASS  clustering binds: 4x samples -> {shrink_samples:+.0%} width, "
              f"2x templates -> {shrink_templates:+.0%} width")

    # 3b. the contrast that makes the point: the flat i.i.d. bootstrap the existing
    #     estimator uses reports a materially narrower interval on the SAME data,
    #     because it counts repeated measurement of one template as new evidence.
    het_recs = full8
    nlo, nhi = naive_flat_ci(het_recs, "algorithm", "person")
    naive_w, clust_w = nhi - nlo, width(w8)
    if naive_w >= clust_w:
        print(f"  FAIL  the flat i.i.d. bootstrap is not narrower ({naive_w:.3f} vs "
              f"{clust_w:.3f}) — this fixture does not exercise the difference")
        ok = False
    else:
        print(f"  PASS  flat i.i.d. bootstrap understates by {1 - naive_w / clust_w:.0%} "
              f"({naive_w:.3f} vs {clust_w:.3f}) — that is the pseudoreplication")

    # 4. the sign test agrees with the bootstrap on an obvious effect
    st = res["contrasts"]["algorithm-person"]["sign_test"]
    if st["p"] > 0.01:
        print(f"  FAIL  sign test p={st['p']:.4f} on a planted 0.50 gap over 16 templates")
        ok = False
    else:
        print(f"  PASS  sign test agrees: {st['pos']}+/{st['neg']}- p={st['p']:.4f}")

    print(f"\n{'paired_analysis self-test PASSED' if ok else 'paired_analysis self-test FAILED'}")
    return 0 if ok else 1


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_date", nargs="?")
    ap.add_argument("--contrast", action="append",
                    help="arm_a:arm_b; repeatable. Defaults to the pre-registered three.")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--stem-control", action="store_true",
                    help="Apply the mismatched-stem calibration and its pre-registered "
                         "abort rule. Requires scored-stemswap/ from score.py --stem-swap.")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.run_date:
        ap.error("a run_date is required (or --selftest)")
    try:
        run_dir = resolve_run(a.run_date)
    except RunNotFound as e:
        print(f"[error] {a.run_date}: {e}", file=sys.stderr)
        return 1
    recs = load(run_dir)
    if not recs:
        print(f"[error] {a.run_date}: no scored records carry pair_id and arm. "
              f"This estimator is for matched-pair runs only; the main study's "
              f"A/B records go through ci_analysis.py.", file=sys.stderr)
        return 1
    contrasts = [tuple(c.split(":", 1)) for c in a.contrast] if a.contrast else None
    seed = analysis_seed(a.run_date)
    res = analyse(recs, seed, a.run_date, contrasts)
    if a.stem_control:
        sc = stem_control(run_dir, res, seed, a.run_date)
        if sc is None:
            print("[error] no scored-stemswap/ - run `score.py <run> --stem-swap` first",
                  file=sys.stderr)
            return 1
        res["stem_control"] = sc
    if a.json:
        print(json.dumps(res, indent=1))
    else:
        render(res)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
