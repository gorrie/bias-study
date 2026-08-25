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
        s = r.get("score_classifier")
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


def main() -> int:
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
