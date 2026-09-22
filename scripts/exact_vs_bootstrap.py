#!/usr/bin/env python3
"""Does the bootstrap disagree with an exact test on the PUBLISHED contrasts?

BACKLOG §14 says the sheet bootstrap is anti-conservative on the 11% of cells whose sheets
barely vary, and that the remedy is free: run an exact permutation test beside it on every
published contrast and see where they disagree.

This is that check. The lead finding -- the balance instruction moving position -- is the
A-vs-N contrast across the panel, computed by `contrast_sheets` on cells of depth 5.

**RUN 2026-09-19: THEY DISAGREE ON 20 OF 241, AND NOT ONLY ON THE DEGENERATE CELLS.**
Bootstrap 104 survive BH-FDR, exact 84, 20 lost and 0 gained — and only 7 of the 20 involve an
arm with near-zero within-arm spread. Thirteen are ordinary cells. So roughly one in five of
the bootstrap's significant findings does not survive an exact test, the losses concentrate at
small n but are not confined there, and four A−N contrasts are among them, taking the lead's
count from 38 of 61 to about 34. The lead's CLAIM is unaffected: the order floor is computed by
the same estimator and moves with it.

Keep this runnable rather than a one-off: the decision it informs — whether the paper's
p-values are bootstrap or exact below n≈15 — has to be re-checkable after the corpus changes.

Exact where the arms are small enough to enumerate (C(na+nb, na) <= 20000), Monte-Carlo
permutation otherwise. Same statistic either way: difference of arm means over pair positions.
"""
import itertools
import os
import random
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import position_analysis as P                                      # noqa: E402
from studypaths import run_path                                   # noqa: E402

WAVE = "2026-09-16-ratchet-v3-wave"
MC = 20000


def sheet_means(sheets):
    return [st.mean(s.values()) for s in sheets if s]


def exact_p(a, b, seed=20260919):
    obs = abs(st.mean(a) - st.mean(b))
    pool = a + b
    na = len(a)
    total = 1
    for i in range(na):
        total = total * (len(pool) - i) // (i + 1)
    if total <= MC:
        hit = n = 0
        for c in itertools.combinations(range(len(pool)), na):
            g = [pool[i] for i in c]
            h = [pool[i] for i in range(len(pool)) if i not in c]
            n += 1
            if abs(st.mean(g) - st.mean(h)) >= obs - 1e-12:
                hit += 1
        return hit / float(n), "exact"
    rng = random.Random(seed)
    hit = 0
    for _ in range(MC):
        rng.shuffle(pool)
        if abs(st.mean(pool[:na]) - st.mean(pool[na:])) >= obs - 1e-12:
            hit += 1
    return (hit + 1) / float(MC + 1), "mc"


def main():
    bank = P.load_bank()
    idx = P.pair_index(bank)
    recs = P.load_records(str(run_path(WAVE)))
    per = P.sheet_positions(recs, idx)

    rows = []
    for a, b in P.CONTRASTS:
        wa = P.CONDITION_MAP.get(a, a)
        wb = P.CONDITION_MAP.get(b, b)
        for model in sorted({m for m, _c in per}):
            if (model, wa) not in per or (model, wb) not in per:
                continue
            ma = sheet_means(per[(model, wa)])
            mb = sheet_means(per[(model, wb)])
            if len(ma) < 2 or len(mb) < 2:
                continue
            boot = P.contrast_sheets(per, model, wa, wb)
            if not boot:
                continue
            ep, kind = exact_p(ma, mb)
            rows.append({
                "model": model, "contrast": "%s-%s" % (wa, wb),
                "effect": boot["effect"], "boot_p": boot["p"], "exact_p": ep, "kind": kind,
                "sd_a": st.pstdev(ma), "sd_b": st.pstdev(mb),
                "n_a": len(ma), "n_b": len(mb),
            })

    def bh(ps, q=0.05):
        order = sorted(range(len(ps)), key=lambda i: ps[i])
        keep = set()
        for rank, i in enumerate(order, 1):
            if ps[i] <= q * rank / len(ps):
                keep = set(order[:rank])
        return keep

    boot_keep = bh([r["boot_p"] for r in rows])
    exact_keep = bh([r["exact_p"] for r in rows])

    print("EXACT PERMUTATION vs SHEET BOOTSTRAP on the pre-registered family")
    print("contrasts compared: %d   (exact %d, monte-carlo %d)"
          % (len(rows), sum(1 for r in rows if r["kind"] == "exact"),
             sum(1 for r in rows if r["kind"] == "mc")))
    print()
    print("survive BH-FDR q=0.05:   bootstrap %d    exact %d"
          % (len(boot_keep), len(exact_keep)))
    lost = boot_keep - exact_keep
    gained = exact_keep - boot_keep
    print("  in bootstrap but NOT exact: %d" % len(lost))
    print("  in exact but NOT bootstrap: %d" % len(gained))
    print()

    DEG = 0.02
    deg = [i for i, r in enumerate(rows) if min(r["sd_a"], r["sd_b"]) < DEG]
    print("contrasts with a DEGENERATE arm (within-arm sd < %.2f): %d of %d"
          % (DEG, len(deg), len(rows)))
    print("  of those, bootstrap-significant: %d ; exact-significant: %d"
          % (len(set(deg) & boot_keep), len(set(deg) & exact_keep)))
    print("  disagreements that involve a degenerate arm: %d of %d"
          % (len(set(deg) & lost), len(lost)))
    print()
    if lost:
        print("LOST BY THE EXACT TEST (bootstrap said significant, exact does not):")
        for i in sorted(lost, key=lambda i: rows[i]["exact_p"]):
            r = rows[i]
            print("  %-34s %-6s eff %+0.3f  boot p %.4f  exact p %.4f  sd %.3f/%.3f  n %d/%d%s"
                  % (r["model"][:33], r["contrast"], r["effect"], r["boot_p"], r["exact_p"],
                     r["sd_a"], r["sd_b"], r["n_a"], r["n_b"],
                     "  DEGENERATE" if min(r["sd_a"], r["sd_b"]) < DEG else ""))


if __name__ == "__main__":
    main()
