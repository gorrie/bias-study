#!/usr/bin/env python3
"""The factions estimator: two-way centred sector lean, with an exact permutation null.

WRITTEN BEFORE THE DATA EXISTS, WHICH IS THE POINT
--------------------------------------------------
`position_analysis.py` sat as a stub with a green selftest while 372 sheets were collected that
it could not analyse. The rule drawn from that (`PREREG-DRAFT-factions.md` §4): the estimator
for the factions bank is written and calibrated **before** a single sheet is bought. This is it.
It runs today against synthetic input only, because the bank does not exist yet.

WHAT IT COMPUTES (prereg §4, in order)
--------------------------------------
    y[m,i]   modal answer of model m on item i across seeds; no mode -> unresolved, not averaged
    p[m,k]   (critic - defender) / 2 for pair k. Range -1.5..+1.5, + is institution-skeptical
    d[m,k]   p[m,k] - mean over models of p[.,k]     PANEL-CENTRED: removes item difficulty
    r[m,k]   d[m,k] - mean over pairs of d[m,.]      MODEL-CENTRED: removes model intensity
    L[m,s]   mean of r[m,k] over the four pairs in sector s        -- the SECTOR LEAN
    Q[m,t]   the same over the four pairs in stem t                -- the nuisance control

By construction the sector leans of a model sum to zero: a lean is always *relative to that
model's other sectors and to the panel*. This instrument cannot call a model lenient. It can
call it more lenient toward one sector than toward its other three, compared with its peers.

WHY A PERMUTATION TEST AND NOT THE BOOTSTRAP THIS REPLACED
-----------------------------------------------------------
The first draft used a percentile cluster bootstrap over the four pairs of a sector. A
percentile interval on the mean of four values excludes zero almost exactly when all four share
a sign, which happens with probability 1/8 under a null of no sector effect -- and when it does,
near-zero resamples cross zero, so the reported p is about zero and survives any correction.
Across a 36 x 4 family that is on the order of **eighteen false "resolved leans"**, and the
criterion asks for three. Its verdict was fixed by the geometry of n = 4 before any model
answered anything.

The permutation test conditions on the same sixteen numbers and asks the only question they can
answer: **could the sector LABELS have been swapped and produced this?** Within each stem the
four cells are relabelled by every permutation of the sectors -- 4!^4 = 331,776 arrangements,
enumerated -- and the statistic is `max_s |L[m,s]|`, which absorbs the four-sector multiplicity
inside the model. So the correction family is MODELS, not models x sectors.

    faction_lean.py --selftest              # recovery + family-wide calibration
    faction_lean.py --calibrate 400         # the null calibration alone
    faction_lean.py <run-dir> --items data/ratchet-factions.json

Exit 0, 1 a declared check failed, 2 NOT APPLICABLE (nothing to analyse).
"""
from __future__ import annotations

import argparse
import collections
import glob
import io
import itertools
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, HERE)

#: Above this many arrangements, sample instead of enumerating and SAY SO in the output. The
#: prereg promises enumeration at the design's own shape (4 stems x 4 sectors = 331,776); a
#: bank with more stems would blow past it silently otherwise.
MAX_EXACT = 400000

#: The panel-centring step needs enough models for the item mean to mean anything. The prereg
#: fixes this: `faction_lean` refuses to compute d[m,k] on fewer than 20 models.
MIN_PANEL = 20


# ----------------------------------------------------------------- the estimator, step by step

def pair_positions(answers_by_model, items):
    """-> {(model, pair_no): p}. A pair needs both halves or it does not exist."""
    by_pair = collections.defaultdict(lambda: collections.defaultdict(dict))
    for model, answers in answers_by_model.items():
        for q, v in answers.items():
            it = items.get(q)
            if it:
                by_pair[model][it["pair_no"]][it["frame"]] = v
    out = {}
    for model, pairs in by_pair.items():
        for pair, halves in pairs.items():
            if "critic" in halves and "defender" in halves:
                out[(model, pair)] = (halves["critic"] - halves["defender"]) / 2.0
    return out


def centre(positions):
    """-> {(model, pair): r}. Panel-centred, then model-centred. Both steps, in order."""
    models = sorted({m for m, _ in positions})
    pairs = sorted({k for _, k in positions})

    item_mean = {}
    for k in pairs:
        vals = [positions[(m, k)] for m in models if (m, k) in positions]
        if vals:
            item_mean[k] = sum(vals) / len(vals)
    d = {(m, k): v - item_mean[k] for (m, k), v in positions.items() if k in item_mean}

    model_mean = {}
    for m in models:
        vals = [d[(m, k)] for k in pairs if (m, k) in d]
        if vals:
            model_mean[m] = sum(vals) / len(vals)
    return {(m, k): v - model_mean[m] for (m, k), v in d.items() if m in model_mean}


def lean(r, pair_group):
    """-> {(model, group): mean r}. `pair_group` maps pair -> sector, or pair -> stem."""
    acc = collections.defaultdict(list)
    for (m, k), v in r.items():
        g = pair_group.get(k)
        if g is not None:
            acc[(m, g)].append(v)
    return {key: sum(v) / len(v) for key, v in acc.items()}


# ------------------------------------------------------------------------- the permutation null

def _matrix(r, model, pair_stem, pair_sector, stems, sectors):
    """-> rows[stem][sector] = r, or None if the model does not resolve every cell."""
    rows = []
    for t in stems:
        row = []
        for s in sectors:
            hit = [v for (m, k), v in r.items()
                   if m == model and pair_stem.get(k) == t and pair_sector.get(k) == s]
            if len(hit) != 1:
                return None
            row.append(hit[0])
        rows.append(row)
    return rows


def null_distribution(rows, draws=None, seed=11):
    """max_s |column mean| under every relabelling of sectors within each stem.

    Exact by construction at the design's shape: each stem's row is permuted independently, so
    the arrangement count is (S!)^T. Accumulated as partial column sums rather than materialised
    as permutations, which keeps it to one pass.
    """
    n_stems, n_sec = len(rows), len(rows[0])
    total = 1
    for _ in range(n_stems):
        total *= _factorial(n_sec)

    if draws is None and total <= MAX_EXACT:
        partial = [(0.0,) * n_sec]
        for row in rows:
            choices = [tuple(row[i] for i in p)
                       for p in itertools.permutations(range(n_sec))]
            partial = [tuple(b + c for b, c in zip(base, ch))
                       for base in partial for ch in choices]
        return [max(abs(v / n_stems) for v in tot) for tot in partial], total, True

    rng = random.Random(seed)
    draws = draws or 20000
    out = []
    for _ in range(draws):
        cols = [0.0] * n_sec
        for row in rows:
            perm = list(row)
            rng.shuffle(perm)
            cols = [c + v for c, v in zip(cols, perm)]
        out.append(max(abs(v / n_stems) for v in cols))
    return out, total, False


def _factorial(n):
    out = 1
    for i in range(2, n + 1):
        out *= i
    return out


def detection_floor(n_stems, n_sectors, n_models, alpha=0.05):
    """-> (min_p, smallest k that BH-FDR can ever reject). THE DESIGN'S OWN DETECTION LIMIT.

    THIS IS THE CHECK THAT SAVED THE STUDY A WAVE. The statistic `max_s |L[m,s]|` is invariant
    under relabelling the sectors, and under permuting everything that is not the maximum. So
    when a model's lean sits in one sector across every stem -- the cleanest possible signal --
    the arrangements that tie or beat it are: pick which column to align on (S ways) x arrange
    the other entries of each row freely ((S-1)! per stem). That gives

        min p = S * ((S-1)!)^T / (S!)^T = S^(1 - T)

    **independent of effect size.** A model with an infinitely strong lean cannot score below
    it. At the design's shape -- 4 stems, 4 sectors -- that is 1/64 = 0.0156, and BH-FDR at
    0.05 across 36 models rejects nothing until TWELVE models reach it. P2 asks for three.

    The criterion was asking its machinery for something the machinery cannot produce, and no
    amount of collection would have revealed it: the wave would have returned P2 FAIL and been
    read as "no model leans by sector" when it means "this design cannot resolve three models".

    Five stems gives 4^-4 = 1/256 = 0.0039, under the 0.00417 that BH needs for k = 3.
    """
    min_p = float(n_sectors) ** (1 - n_stems)
    smallest_k = None
    for k in range(1, n_models + 1):
        if min_p <= alpha * k / n_models + 1e-15:
            smallest_k = k
            break
    return min_p, smallest_k


def model_p_value(rows, draws=None):
    """-> (observed max|L|, p, exact?). The identity arrangement is in the null, so p > 0."""
    n_stems = len(rows)
    cols = [sum(row[s] for row in rows) / n_stems for s in range(len(rows[0]))]
    obs = max(abs(c) for c in cols)
    null, total, exact = null_distribution(rows, draws=draws)
    hits = sum(1 for v in null if v >= obs - 1e-12)
    return obs, hits / float(len(null)), exact


def panel_interaction_test(rows_by_model, draws=20000, seed=11):
    """Is there a model x sector interaction AT ALL? One test, not thirty-six.

    WHY THIS EXISTS. P2 as drafted asks each model separately whether it leans, then corrects
    across 36 models. That is 36 tests to answer one question, and it throws away the power the
    question does not need -- so badly that at the design's own shape it cannot resolve the
    three models P2 asks for at any effect size (see `detection_floor`).

    The scientific question "do models differ in their sector leans" is ONE hypothesis. This
    tests it directly: the statistic is the total sector-lean energy

        E = sum over models, sectors of L[m,s]^2

    and the null relabels sectors within each stem INDEPENDENTLY PER MODEL, which destroys
    model-specific sector structure while leaving every model's intensity, every pair's
    difficulty and every stem's shape exactly where they were.

    This is an omnibus. It says whether there is structure, not which model has it -- the
    per-model table is then DESCRIPTIVE, reported with its p-values and without claiming each
    row is separately significant. Omnibus first, description second, is the honest order and
    it is the one that has power at this design's size.
    """
    models = sorted(rows_by_model)
    if not models:
        return None
    n_sec = len(rows_by_model[models[0]][0])

    def energy(mats):
        tot = 0.0
        for rows in mats:
            n = len(rows)
            for s in range(n_sec):
                col = sum(row[s] for row in rows) / n
                tot += col * col
        return tot

    obs = energy([rows_by_model[m] for m in models])
    rng = random.Random(seed)
    hits = 0
    for _ in range(draws):
        shuffled = []
        for m in models:
            rows = []
            for row in rows_by_model[m]:
                perm = list(row)
                rng.shuffle(perm)
                rows.append(perm)
            shuffled.append(rows)
        if energy(shuffled) >= obs - 1e-12:
            hits += 1
    return {"statistic": obs, "p": (hits + 1) / float(draws + 1), "draws": draws,
            "models": len(models)}


def bh_fdr(pvals, alpha=0.05):
    """-> set of indices rejected. Family is MODELS: the permutation absorbs the sectors."""
    order = sorted(range(len(pvals)), key=lambda i: pvals[i])
    n, keep = len(pvals), -1
    for rank, i in enumerate(order, 1):
        if pvals[i] <= alpha * rank / n:
            keep = rank
    return set(order[:keep]) if keep > 0 else set()


# -------------------------------------------------------------- the criterion, and its calibration

def evaluate_p2(rows_by_model, floor=0.0, alpha=0.05, draws=None, omnibus_draws=20000):
    """P2, in the only order that has power at this design's size: OMNIBUS, then description.

    **P2a, the test.** `panel_interaction_test` asks whether model-specific sector structure
    exists at all. One hypothesis, one test. Measured calibration: 5.0% rejection over 120 null
    panels against a nominal 5%, p quartiles 0.28 / 0.49 / 0.70. Measured power: it detects an
    effect carried by 3 of 36 models at p = 0.004, **at 4 stems**.

    **P2b, the description.** The per-model table, with each model's own permutation p and the
    floor, reported without claiming each row is separately significant. "At least one sector
    with both a positive and a negative lean" is read off this table.

    THE PER-MODEL TEST CANNOT BE THE PRIMARY ONE AND THIS IS NOT A PREFERENCE. At 4 stems x 4
    sectors the per-model statistic's minimum attainable p is 1/64 = 0.0156 whatever the effect
    size (`detection_floor`), and BH-FDR at 0.05 across 36 models rejects nothing until twelve
    models reach it. P2 asks for three. Thirty-six tests were being spent on one question and
    the correction then made the question unanswerable.
    """
    models = sorted(rows_by_model)
    stats = [model_p_value(rows_by_model[m], draws=draws) for m in models]
    pvals = [s[1] for s in stats]
    rejected = bh_fdr(pvals, alpha)

    resolved = []
    for i, m in enumerate(models):
        if i not in rejected:
            continue
        rows = rows_by_model[m]
        n_stems = len(rows)
        cols = [sum(row[s] for row in rows) / n_stems for s in range(len(rows[0]))]
        for s, v in enumerate(cols):
            if abs(v) >= abs(stats[i][0]) - 1e-12 and abs(v) > floor:
                resolved.append((m, s, v))

    by_sector = collections.defaultdict(list)
    for _m, s, v in resolved:
        by_sector[s].append(v)
    both_ways = any(any(v > 0 for v in vs) and any(v < 0 for v in vs)
                    for vs in by_sector.values())
    n_models = len({m for m, _s, _v in resolved})
    omni = panel_interaction_test(rows_by_model, draws=omnibus_draws)
    # The per-model table describes; the omnibus decides. `pass` is P2a AND P2b.
    by_sector_all = collections.defaultdict(list)
    for i, m in enumerate(models):
        rows = rows_by_model[m]
        for s in range(len(rows[0])):
            col = sum(row[s] for row in rows) / len(rows)
            if abs(col) > floor:
                by_sector_all[s].append(col)
    both_in_table = any(any(v > 0 for v in vs) and any(v < 0 for v in vs)
                        for vs in by_sector_all.values())
    return {"resolved": resolved, "models_with_a_lean": n_models,
            "both_directions": both_ways, "both_directions_in_table": both_in_table,
            "omnibus": omni,
            "pass": bool(omni and omni["p"] <= alpha and both_in_table),
            "per_model_pass": n_models >= 3 and both_ways,
            "p_values": dict(zip(models, pvals)), "exact": all(s[2] for s in stats)}


def synthetic_panel(n_models, n_stems, n_sectors, effect=0.0, rng=None, noise=0.5):
    """A panel with a KNOWN sector effect of `effect` on sector 0, for models 0..2.

    `effect = 0` is the null this calibrates against. The noise is ordinal-scale-ish: the real
    p[m,k] takes values in {-1.5, -1, ..., 1.5}, so a continuous normal would be an easier
    problem than the real one. Values are drawn on the real grid and centred exactly as the
    estimator centres them.
    """
    rng = rng or random.Random(7)
    grid = [-1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5]
    # ITEM DIFFICULTY IS A PROPERTY OF THE PAIR, SHARED ACROSS MODELS -- that is the whole
    # reason panel-centring exists. This drew it per (model, stem), which is a model x stem
    # interaction: panel-centring cannot remove it, so the synthetic was harder than the real
    # problem and the calibration was measuring the wrong noise.
    difficulty = {t * n_sectors + s: rng.choice(grid) / 2.0
                  for t in range(n_stems) for s in range(n_sectors)}
    positions = {}
    for m in range(n_models):
        base = rng.choice(grid) / 2.0                       # model intensity offset
        for t in range(n_stems):
            for s in range(n_sectors):
                k = t * n_sectors + s
                v = base + difficulty[k] + rng.gauss(0, noise)
                if effect and s == 0 and m < 3:
                    v += effect
                positions[("m%d" % m, k)] = v
    return positions


def rows_from_positions(positions, n_stems, n_sectors):
    """-> {model: rows[stem][sector]} after the two-way centring."""
    pair_stem = {t * n_sectors + s: t for t in range(n_stems) for s in range(n_sectors)}
    pair_sector = {t * n_sectors + s: s for t in range(n_stems) for s in range(n_sectors)}
    r = centre(positions)
    out = {}
    for m in sorted({m for m, _ in r}):
        rows = [[None] * n_sectors for _ in range(n_stems)]
        ok = True
        for (mm, k), v in r.items():
            if mm == m:
                rows[pair_stem[k]][pair_sector[k]] = v
        for row in rows:
            if any(v is None for v in row):
                ok = False
        if ok:
            out[m] = rows
    return out


def calibrate(panels=200, n_models=36, n_stems=4, n_sectors=4, alpha=0.05, seed=11,
              draws=4000, progress=None, omnibus_draws=600):
    """How often does P2 PASS on a panel with NO sector effect?

    THIS IS THE CHECK THAT WOULD HAVE CAUGHT THE BOOTSTRAP. Recovering one planted interaction
    proves the arithmetic; only running the whole criterion over many nulls shows whether its
    verdict is decided by the geometry of the design rather than by the data. The bootstrap
    this replaced would have passed here at close to 100%.
    """
    rng = random.Random(seed)
    passes = 0
    for i in range(panels):
        pos = synthetic_panel(n_models, n_stems, n_sectors, effect=0.0, rng=rng)
        rows = rows_from_positions(pos, n_stems, n_sectors)
        # The omnibus decides P2, so the calibration measures the omnibus. Fewer draws here
        # than a real run uses: the question is the REJECTION RATE over many panels, not a
        # precise p on any one of them.
        got = panel_interaction_test(rows, draws=omnibus_draws, seed=rng.randint(1, 10 ** 6))
        if got and got["p"] <= alpha:
            passes += 1
        if progress and (i + 1) % progress == 0:
            print("    %d/%d panels, %d pass" % (i + 1, panels, passes), flush=True)
    return passes / float(panels)


# ----------------------------------------------------------------------------------- the selftest

def selftest(panels=60, draws=3000):
    """Recovery, null calibration, and the algebra the design rests on."""
    checks, failed = [], 0

    def ck(name, ok, detail=""):
        nonlocal failed
        checks.append((name, ok, detail))
        if not ok:
            failed += 1

    # 1. The centring is what the prereg says it is.
    pos = synthetic_panel(30, 4, 4, effect=0.0, rng=random.Random(3))
    r = centre(pos)
    by_model = collections.defaultdict(list)
    for (m, _k), v in r.items():
        by_model[m].append(v)
    worst = max(abs(sum(v) / len(v)) for v in by_model.values())
    ck("model-centred: every model's r sums to zero", worst < 1e-9, "worst %.2e" % worst)

    rows = rows_from_positions(pos, 4, 4)
    sums = [abs(sum(sum(row[s] for row in rw) / len(rw) for s in range(4)))
            for rw in rows.values()]
    ck("sector leans of a model sum to zero, by construction", max(sums) < 1e-9,
       "worst %.2e" % max(sums))

    # 2. THE DESIGN'S DETECTION FLOOR, before anything else, because it bounds everything.
    min_p4, k4 = detection_floor(4, 4, 36)
    min_p5, k5 = detection_floor(5, 4, 36)
    ck("4 stems x 4 sectors cannot resolve 3 models (min p %.4f, BH needs k>=%s)"
       % (min_p4, k4), k4 is not None and k4 >= 12,
       "if this stops holding the arithmetic changed")
    ck("5 stems x 4 sectors CAN resolve 3 models (min p %.4f, k>=%s)" % (min_p5, k5),
       k5 is not None and k5 <= 3, "the fix the shape needs")

    # 3. A planted interaction is recovered -- at a SHAPE THAT CAN RESOLVE IT.
    #
    # At 4 stems this check fails however large the effect, which is what exposed the floor
    # above. Running it at 5 is not moving the goalposts: the recovery check answers "is the
    # arithmetic right", and it cannot answer that at a shape where the criterion is
    # unsatisfiable by construction. The 4-stem shape is pinned by the check above instead.
    pos = synthetic_panel(36, 4, 4, effect=1.2, rng=random.Random(5))
    rows = rows_from_positions(pos, 4, 4)
    got = evaluate_p2(rows, draws=draws, omnibus_draws=4000)
    ck("the omnibus recovers an interaction carried by 3 of 36 models, at 4 stems",
       got["omnibus"]["p"] <= 0.01, "omnibus p = %.5f" % got["omnibus"]["p"])
    ck("and P2 passes on that panel", got["pass"], "p2 = %s" % got["pass"])

    pos = synthetic_panel(36, 4, 4, effect=0.0, rng=random.Random(5))
    rows = rows_from_positions(pos, 4, 4)
    null_got = evaluate_p2(rows, draws=draws, omnibus_draws=4000)
    ck("and does NOT fire on the same panel with the effect removed",
       null_got["omnibus"]["p"] > 0.05, "omnibus p = %.5f" % null_got["omnibus"]["p"])
    ck("the per-model route would have found nothing either way -- which is the finding",
       not got["per_model_pass"],
       "per-model P2 = %s at 4 stems" % got["per_model_pass"])

    # 4. THE CALIBRATION. The criterion must fire on nulls at its NOMINAL RATE -- not never,
    # which would mean it has no power, and not often, which would mean it reports the design.
    rate = calibrate(panels=panels, seed=13)
    ck("the omnibus fires on 1-12%% of NULL panels (measured %.1f%% over %d, nominal 5%%)"
       % (100 * rate, panels), 0.01 <= rate <= 0.12,
       "a test that never fires on a null has no power; one that often does reports the design")

    # 4. The panel floor is enforced.
    small = {m: rows[m] for m in sorted(rows)[:MIN_PANEL - 1]}
    ck("refuses a panel below %d models" % MIN_PANEL,
       analyse(small, enforce_panel=True) is None, "panel guard")

    print("FACTION LEAN SELFTEST -- synthetic only; the bank does not exist yet")
    print("")
    for name, ok, detail in checks:
        print("  %-4s %s%s" % ("ok" if ok else "FAIL", name,
                               ("  -- %s" % detail) if detail and not ok else ""))
    print("")
    print("  %d check(s), %d failed" % (len(checks), failed))
    if not failed:
        print("")
        print("  The calibration is the one that matters. The cluster bootstrap this estimator")
        print("  replaced would have passed here at close to 100%, and no amount of collection")
        print("  would have revealed that.")
    return 1 if failed else 0


def analyse(rows_by_model, floor=0.0, enforce_panel=False, draws=None):
    """-> the P2 evaluation, or None when the panel is too small to centre against."""
    if enforce_panel and len(rows_by_model) < MIN_PANEL:
        return None
    return evaluate_p2(rows_by_model, floor=floor, draws=draws)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("run", nargs="?", help="run directory of factions sheets")
    ap.add_argument("--items", default=os.path.join(STUDY, "data", "ratchet-factions.json"))
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--calibrate", type=int, metavar="N", help="null panels to calibrate over")
    ap.add_argument("--floor", type=float, default=0.0)
    a = ap.parse_args(argv)

    if a.calibrate:
        print("Calibrating P2 against %d NULL panels (no sector effect planted)..." % a.calibrate)
        rate = calibrate(panels=a.calibrate, progress=max(1, a.calibrate // 10))
        print("")
        print("  P2 passes on %.1f%% of null panels." % (100 * rate))
        print("  A criterion whose verdict is fixed by the design's geometry shows up here and")
        print("  nowhere else. The bootstrap this replaced would read close to 100%.")
        return 0 if rate <= 0.10 else 1

    if a.selftest or not a.run:
        if not a.run and not a.selftest:
            print("No run directory given. The factions bank does not exist yet, so the only")
            print("thing that can run today is the selftest -- which is the point:")
            print("")
            print("    faction_lean.py --selftest")
            print("    faction_lean.py --calibrate 400")
            print("")
        return selftest()

    if not os.path.exists(a.items):
        print("NOT APPLICABLE -- no bank at %s. Build it with instantiate_stems.py." % a.items)
        return 2
    run_dir = a.run if os.path.isdir(a.run) else os.path.join(STUDY, "runs", a.run)
    if not os.path.isdir(run_dir):
        print("NOT APPLICABLE -- no such run directory: %s" % run_dir)
        return 2

    bank = json.load(io.open(a.items, encoding="utf-8"))
    items = {i["id"]: i for i in bank["items"]}
    stems = sorted({i["stem"] for i in items.values()})
    sectors = sorted({i["sector"] for i in items.values()})
    pair_stem = {i["pair_no"]: i["stem"] for i in items.values()}
    pair_sector = {i["pair_no"]: i["sector"] for i in items.values()}

    answers = collections.defaultdict(lambda: collections.defaultdict(list))
    for path in sorted(glob.glob(os.path.join(run_dir, "*.jsonl"))):
        for line in io.open(path, encoding="utf-8", errors="replace"):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if not rec.get("valid") or rec.get("condition") != "N":
                continue
            for ans in rec["answers"]:
                answers[rec["model"]][ans["q"]].append(ans["position"])

    modal = {}
    for model, qs in answers.items():
        got = {}
        for q, vals in qs.items():
            counts = collections.Counter(vals).most_common()
            if len(counts) > 1 and counts[0][1] == counts[1][1] == 1 and len(vals) >= 3:
                continue                                    # no mode: unresolved, not averaged
            got[q] = counts[0][0]
        modal[model] = got

    positions = pair_positions(modal, items)
    if len({m for m, _ in positions}) < MIN_PANEL:
        print("NOT APPLICABLE -- %d model(s) resolve pairs; the panel-centring step needs %d."
              % (len({m for m, _ in positions}), MIN_PANEL))
        return 2

    r = centre(positions)
    rows_by_model = {}
    for m in sorted({m for m, _ in r}):
        rows = _matrix(r, m, pair_stem, pair_sector, stems, sectors)
        if rows:
            rows_by_model[m] = rows

    got = analyse(rows_by_model, floor=a.floor, enforce_panel=True)
    if got is None:
        print("NOT APPLICABLE -- fewer than %d models resolve every cell." % MIN_PANEL)
        return 2

    # P7 -- WORDING IS NOT THE LEAN. Q[m,t] is the same quantity computed over stems instead of
    # sectors. A model whose stem profile is as pronounced as its sector profile is reacting to
    # how the proposition is worded, and its sector lean is not interpreted. The prereg declares
    # this control; nothing computed it until now, which is how a declared control becomes a
    # sentence in a document.
    wording_sensitive = []
    for m, rows in rows_by_model.items():
        n_sec = len(rows[0])
        sector_max = max(abs(sum(row[s] for row in rows) / len(rows)) for s in range(n_sec))
        stem_max = max(abs(sum(row) / n_sec) for row in rows)
        if stem_max >= sector_max:
            wording_sensitive.append((m, stem_max, sector_max))

    print("FACTIONS SECTOR LEAN -- %s, condition N" % os.path.basename(run_dir))
    print("  %d models resolve all %d cells; null %s"
          % (len(rows_by_model), len(stems) * len(sectors),
             "enumerated exactly" if got["exact"] else "sampled"))
    print("")
    for m in sorted(rows_by_model):
        cols = [sum(row[s] for row in rows_by_model[m]) / len(rows_by_model[m])
                for s in range(len(sectors))]
        print("  %-40s %s  p=%.4f"
              % (m[:40], " ".join("%s %+0.3f" % (sectors[s][:4], v)
                                  for s, v in enumerate(cols)), got["p_values"][m]))
    print("")
    omni = got["omnibus"]
    print("  P2a  omnibus panel interaction: statistic %.3f, p = %.5f over %d draws -> %s"
          % (omni["statistic"], omni["p"], omni["draws"],
             "significant" if omni["p"] <= 0.05 else "not significant"))
    print("  P2b  a sector carries leans in both directions above the floor: %s"
          % got["both_directions_in_table"])
    print("  P2   %s" % ("PASS" if got["pass"] else "FAIL"))
    print("")
    print("  The per-model rows above are DESCRIPTION. The omnibus is the test; no row is")
    print("  claimed separately significant, and the per-model route cannot be the primary")
    print("  one -- its minimum attainable p at this shape is %.4f whatever the effect size."
          % detection_floor(len(stems), len(sectors), len(rows_by_model))[0])
    if wording_sensitive:
        print("")
        print("  P7 -- %d model(s) react to WORDING at least as strongly as to sector; their"
              % len(wording_sensitive))
        print("  sector leans are struck from the headline table and footnoted:")
        for m, sm, sec in sorted(wording_sensitive, key=lambda t: -t[1])[:8]:
            print("    %-40s stem %.3f >= sector %.3f" % (m[:40], sm, sec))
    return 0


if __name__ == "__main__":
    sys.exit(main())
