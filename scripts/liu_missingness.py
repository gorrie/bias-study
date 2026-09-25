#!/usr/bin/env python3
"""How much of Liu, Panwang and Gu's 0613 -> 1106 shift does missingness alone produce?

`rederive_liu.py` MEASURES the missingness from their deposit: 11.18% of the 1106 arm's items
unevaluable, and one unevaluable answer deletes the whole 62-item questionnaire, leaving 17 of
30. It also shows why that could matter -- a fixed-divisor axis with positive offsets scores a
questionnaire with missing items toward the offsets. What it cannot say is HOW MUCH of the
reported shift that mechanism produces. That is a measurement, and this is it.

THEIR BOOTSTRAP, reimplemented from their Do_file.do:
  * chart_drop: a questionnaire (account, Q) with ANY -9 answer is deleted whole.
  * axis = sum(EconDimension)/8 + 0.38 ; sum(SocietyDimension)/19.5 + 2.41 -- FIXED divisors.
  * per account, per draw: `set obs 61; gen QID=_n; x1=int(10*uniform()); ... keep if x1==Q`.
    Each of QIDs 1..61 takes its answer from a random questionnaire index 0..9 of THAT account.
    If that questionnaire was deleted there is no row, so the item is absent from the draw's
    sum while the divisor stays fixed. (QID 62 is never drawn: `set obs 61`.) The appendix
    table uses 1,000 draws per account, 3,000 rows.
The reimplementation is checked against the bootstrap output they deposited, and the check is
printed beside the result.

THE SIMULATIONS run on the COMPLETE 0613 questionnaires, which have no unevaluable answer:
  A  delete the same (account, Q) questionnaires the 1106 arm lost, then their bootstrap;
  B  delete the same NUMBER of questionnaires at random, a new set per replicate;
  C  blank only the items 1106 answered -9, with no listwise deletion;
  C2 blank random items at 1106's item rate.
And a decomposition on 1106's own data: their bootstrap drawing only from SURVIVING
questionnaires, which removes the holes and leaves the content change.

A share near 1 means the shift is what the deletion rule produces from complete data with no
change in content. It is a statement about the design, not about the authors, and it is
possible to measure only because they published their raw files.

DEPENDENCIES. The deposit's code tables are Stata files, so this reads them with pandas, and
the bootstrap is vectorised with numpy. Neither is needed anywhere else in the analysis path,
which is standard-library only, so both are imported inside `main()`:

    pip install numpy pandas
    python scripts/liu_missingness.py --deposit <path to the unzipped supplement>

The supplement is `41599_2025_4465_MOESM1_ESM.zip` on the article page
(doi:10.1057/s41599-025-04465-z), open access, CC BY 4.0, and is not vendored here.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import rederive_liu as RL  # noqa: E402

#: Their appendix bootstrap: 1,000 draws per account, 3,000 rows.
B_PER_ACCOUNT = 1000
#: Simulation replicates, each one a full 3,000-row bootstrap.
REPS = 200
SEED = 20260925
PAIRS = (("3.5-turbo-0613", "3.5-turbo-1106"), ("4-0613", "4-turbo-1106"))


def _norm(s):
    return " ".join(s.replace("�", "").split()).lower()


def load_model(np, pd, deposit, model):
    """(class per (account, Q, QID), econ table, soc table) from the deposit."""
    qm = pd.read_stata(os.path.join(deposit, model, "QID_match.dta"))
    qid = {_norm(q): int(i) for i, q in zip(qm.QID, qm.question)}
    cn = pd.read_stata(os.path.join(deposit, model, "countnumber.dta"))
    econ = np.zeros((63, 5))
    soc = np.zeros((63, 5))
    for q_, c_, e_, s_ in zip(cn.QID, cn["class"], cn.EconDimension, cn.SocietyDimension):
        econ[int(q_), int(c_)] = e_
        soc[int(q_), int(c_)] = s_
    cls = np.zeros((3, 10, 63), dtype=int)
    unmatched = 0
    for (acct, fn), answers in RL.read_raw(deposit, model).items():
        a = int(acct.replace("account", "")) - 1
        q = int(fn.replace("extract", "").replace(".txt", ""))
        for question, ans in answers:
            k = qid.get(_norm(question))
            if k is None:
                unmatched += 1
                continue
            cls[a, q, k] = int(ans)
    if unmatched:
        print("  WARN %s: %d answers did not match QID_match" % (model, unmatched))
    return cls, econ, soc


def item_scores(np, cls, econ, soc):
    e = np.full(cls.shape, np.nan)
    s = np.full(cls.shape, np.nan)
    idx = np.where(cls > 0)
    e[idx] = econ[idx[2], cls[idx]]
    s[idx] = soc[idx[2], cls[idx]]
    return e, s


def listwise_alive(cls):
    """(3, 10) bool: the questionnaire survives chart_drop -- 62 answers, none -9."""
    return (cls[:, :, 1:63] > 0).sum(axis=2) == 62


def nonboot(np, e, s, alive):
    ee = np.nansum(e[:, :, 1:63], axis=2) / 8 + 0.38
    ss = np.nansum(s[:, :, 1:63], axis=2) / 19.5 + 2.41
    return float(ee[alive].mean()), float(ss[alive].mean())


def their_bootstrap(np, e, s, alive, rng, B=B_PER_ACCOUNT):
    """Mean economic and social axis over 3*B rows, by their draw rule."""
    E = np.where(alive[:, :, None], np.nan_to_num(e), 0.0)
    S = np.where(alive[:, :, None], np.nan_to_num(s), 0.0)
    E = np.where(np.isnan(e), 0.0, E)
    S = np.where(np.isnan(s), 0.0, S)
    qids = np.arange(1, 62)
    out_e, out_s = [], []
    for a in range(3):
        x1 = rng.integers(0, 10, size=(B, 61))
        out_e.append(E[a][x1, qids[None, :]].sum(axis=1) / 8 + 0.38)
        out_s.append(S[a][x1, qids[None, :]].sum(axis=1) / 19.5 + 2.41)
    return float(np.concatenate(out_e).mean()), float(np.concatenate(out_s).mean())


def survivors_only_bootstrap(np, e, s, alive, rng, B=B_PER_ACCOUNT):
    """Counterfactual: draw only among each account's surviving questionnaires -- no holes."""
    qids = np.arange(1, 62)
    out_e, out_s = [], []
    for a in range(3):
        live = np.where(alive[a])[0]
        if not len(live):
            continue
        x1 = live[rng.integers(0, len(live), size=(B, 61))]
        out_e.append(np.nan_to_num(e[a])[x1, qids[None, :]].sum(axis=1) / 8 + 0.38)
        out_s.append(np.nan_to_num(s[a])[x1, qids[None, :]].sum(axis=1) / 19.5 + 2.41)
    return float(np.concatenate(out_e).mean()), float(np.concatenate(out_s).mean())


def _dist(np, vals):
    v = np.array(vals)
    return {"mean": round(float(v.mean()), 3), "p2.5": round(float(np.percentile(v, 2.5)), 3),
            "p97.5": round(float(np.percentile(v, 97.5)), 3)}


def analyse(np, pd, deposit, reps=REPS):
    rng = np.random.default_rng(SEED)
    res = {}
    for old, new in PAIRS:
        c0, econ, soc = load_model(np, pd, deposit, old)
        c1, econ1, soc1 = load_model(np, pd, deposit, new)
        assert np.array_equal(econ, econ1) and np.array_equal(soc, soc1)
        e0, s0 = item_scores(np, c0, econ, soc)
        e1, s1 = item_scores(np, c1, econ, soc)
        a0, a1 = listwise_alive(c0), listwise_alive(c1)
        r = {"survivors": [int(a0.sum()), int(a1.sum())],
             "nonboot_old": nonboot(np, e0, s0, a0), "nonboot_new": nonboot(np, e1, s1, a1)}
        bo = [their_bootstrap(np, e0, s0, a0, rng) for _ in range(reps)]
        bn = [their_bootstrap(np, e1, s1, a1, rng) for _ in range(reps)]
        base = (float(np.mean([x[0] for x in bo])), float(np.mean([x[1] for x in bo])))
        boot_new = (float(np.mean([x[0] for x in bn])), float(np.mean([x[1] for x in bn])))
        shift = (boot_new[0] - base[0], boot_new[1] - base[1])
        r["boot_old"], r["boot_new"] = base, boot_new
        r["shift"] = shift
        so = [survivors_only_bootstrap(np, e1, s1, a1, rng) for _ in range(reps)]
        r["content_shift"] = (float(np.mean([x[0] for x in so])) - base[0],
                              float(np.mean([x[1] for x in so])) - base[1])
        sims = {}
        sims["A: 1106's deleted questionnaires"] = [
            their_bootstrap(np, e0, s0, a1, rng) for _ in range(reps)]
        ndel = int(30 - a1.sum())
        simB = []
        for _ in range(reps):
            mask = np.ones(30, bool)
            mask[rng.choice(30, ndel, replace=False)] = False
            simB.append(their_bootstrap(np, e0, s0, mask.reshape(3, 10), rng))
        sims["B: %d of 30 questionnaires at random" % ndel] = simB
        blank = (c1 == -9)
        eC, sC = e0.copy(), s0.copy()
        eC[blank], sC[blank] = np.nan, np.nan
        allalive = np.ones((3, 10), bool)
        sims["C: only the items 1106 answered -9"] = [
            their_bootstrap(np, eC, sC, allalive, rng) for _ in range(reps)]
        rate = float(blank[:, :, 1:63].sum()) / (30 * 62)
        simC2 = []
        for _ in range(reps):
            m = rng.random(c0.shape) < rate
            m[:, :, 0] = False
            eR, sR = e0.copy(), s0.copy()
            eR[m], sR[m] = np.nan, np.nan
            simC2.append(their_bootstrap(np, eR, sR, allalive, rng))
        sims["C2: random items at %.2f%%" % (100 * rate)] = simC2
        r["sims"] = {}
        for name, sim in sims.items():
            de = [x[0] - base[0] for x in sim]
            ds = [x[1] - base[1] for x in sim]
            r["sims"][name] = {
                "econ": _dist(np, de), "soc": _dist(np, ds),
                "share_econ": float(np.mean(de)) / shift[0] if shift[0] else None,
                "share_soc": float(np.mean(ds)) / shift[1] if shift[1] else None}
        res["%s -> %s" % (old, new)] = r
    # Their deposited bootstrap output, the check on the reimplementation.
    dep = {}
    for m in RL.MODELS:
        d = os.path.join(deposit, m, "derived_appendix")
        if os.path.isdir(d):
            for fn in sorted(os.listdir(d)):
                if fn.startswith("chart_bootstrap_final"):
                    x = pd.read_stata(os.path.join(d, fn))
                    dep[m] = (round(float(x.Econmic_Axis.mean()), 3),
                              round(float(x.Social_Axis.mean()), 3))
    res["deposited_appendix_bootstrap"] = dep
    return res


def report(res):
    dep = res.get("deposited_appendix_bootstrap", {})
    for key, r in res.items():
        if key == "deposited_appendix_bootstrap":
            continue
        old, new = key.split(" -> ")
        print("")
        print("  %s   (surviving questionnaires %d -> %d of 30)" % (key, *r["survivors"]))
        print("    reimplemented bootstrap, 1106 arm: econ %+.3f  soc %+.3f   deposited: %s"
              % (r["boot_new"][0], r["boot_new"][1], dep.get(new, "absent")))
        print("    reported shift (bootstrapped)      econ %+.2f  soc %+.2f"
              % r["shift"])
        print("    content shift, holes removed       econ %+.2f  soc %+.2f   non-bootstrapped: "
              "%+.2f / %+.2f" % (r["content_shift"] + (r["nonboot_new"][0] - r["nonboot_old"][0],
                                                       r["nonboot_new"][1] - r["nonboot_old"][1])))
        print("    produced from COMPLETE %s data by missingness alone:" % old)
        for name, s in r["sims"].items():
            print("      %-40s econ %+.2f [%+.2f, %+.2f]  soc %+.2f [%+.2f, %+.2f]   share %s / %s"
                  % (name, s["econ"]["mean"], s["econ"]["p2.5"], s["econ"]["p97.5"],
                     s["soc"]["mean"], s["soc"]["p2.5"], s["soc"]["p97.5"],
                     "%.0f%%" % (100 * s["share_econ"]) if s["share_econ"] is not None else "-",
                     "%.0f%%" % (100 * s["share_soc"]) if s["share_soc"] is not None else "-"))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--deposit", required=True, help="the unzipped Springer supplement")
    ap.add_argument("--reps", type=int, default=REPS)
    ap.add_argument("--json", help="also write the full result here")
    args = ap.parse_args(argv)
    try:
        import numpy as np
        import pandas as pd
    except ImportError as exc:
        print("needs numpy and pandas (pip install numpy pandas): %s" % exc)
        return 2
    if not os.path.isdir(args.deposit):
        print("no deposit at %s -- download the supplement first (see the docstring)"
              % args.deposit)
        return 2
    print("MISSINGNESS AGAINST THE REPORTED SHIFT -- Liu, Panwang and Gu (2025)")
    res = analyse(np, pd, args.deposit, args.reps)
    report(res)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(res, fh, indent=1, default=list)
    return 0


if __name__ == "__main__":
    sys.exit(main())
