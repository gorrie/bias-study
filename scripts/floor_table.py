#!/usr/bin/env python3
"""Generate every measured floor, in BOTH statistics, from raw runs only.

WHY THIS EXISTS
---------------
The floors were quoted in mixed units. A same-version null of "p90 22" was placed beside an
order effect of "24 of 62" as though the two were comparable. They are not: the null was
computed as |b-c| on ENDPOINT status (Strongly Agree / Strongly Disagree), while order,
quantisation, ablation and the prompt conditions were all counted as SIDE-flips (crossing
the agree/disagree boundary).

Re-derived here, the same-version null is median 5, p90 12, max 24 in side-flip units --
roughly half the number that was published, in the currency the rest of the table uses.

No number in this project's floor table should be typed by hand again. Every row below is
computed from `runs/`, in both statistics, so a unit mix cannot recur silently.

THE TWO STATISTICS
------------------
  side-flip    the item crossed the agree/disagree boundary. Binary outcome, binary
               statistic. This is the unit for anything compared against concordance.
  endpoint     the item gained or lost a Strongly answer. Finer-grained, and the unit the
               suppression work uses, because suppression is about intensity not direction.

They are different questions and neither is wrong. Mixing them in one table is.

Usage:
    python floor_table.py
    python floor_table.py --markdown
"""
from __future__ import annotations

import argparse
import collections
import glob
import io
import json
import os
import random
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from check_arm_match import INELIGIBLE_PAIRS, QUANT_PAIRS  # noqa: E402
from classify_lineage import classify, parse  # noqa: E402

BOOT_N = 2000
BOOT_SEED = 20260831


def ext(p):
    return p in (0, 3)


def side(p):
    return p >= 2


def _default_key(r):
    return (r["model"], r["condition"], r.get("shuffle_seed"))


def _template_key(r):
    """Cell key for the paraphrase arm: the template is what varies, order is held fixed."""
    return (r["model"], r["condition"], r.get("template", "T01"))


def _order_key(r):
    """The default key PLUS the template, so the order floor can hold the wrapper fixed.

    Carries template as a fourth element rather than folding it in, so `_order_cells` can
    filter on it and then group on the historical three-part key -- the floor's pairing logic
    is unchanged, it just stops being fed cells that differ in something other than order.
    """
    return (r["model"], r["condition"], r.get("shuffle_seed"), r.get("template", "T01"))


#: What load() threw away on the last call, and why. A dropped run is a measurement that does
#: not reach a floor, and until 2026-09-04 every one of them vanished without a trace: the
#: OBLITERATED Qwen3.8-27B's entire ablated arm -- four valid, fully parsed 62-item sheets --
#: was discarded as degenerate and no output anywhere said a pair had lost its arm.
#: Read it after a load, or call load_report().
DROPPED = collections.Counter()

#: Run identities already counted into DROPPED. Several floors glob overlapping directories --
#: the order floor reads six run dirs, the condition floor reads one of the same six -- so a
#: naive counter reports 376 drops for a corpus that has far fewer. A count that inflates with
#: the number of callers is not a count.
_DROPPED_SEEN = set()


def _count_drop(reason, rec):
    ident = (rec.get("model"), rec.get("condition"), rec.get("collected_at"),
             rec.get("shuffle_seed"), rec.get("template"))
    if ident in _DROPPED_SEEN:
        return
    _DROPPED_SEEN.add(ident)
    DROPPED[reason] += 1


def load_report():
    """One line per reason load() discarded a run, for a floor to print alongside its number."""
    return sorted(DROPPED.items(), key=lambda kv: (-kv[1], kv[0]))


def load(pattern, condition=None, key=None):
    """Answer sheets grouped into cells.

    `key` chooses the grouping and defaults to the historical (model, condition, shuffle_seed).
    It is a parameter rather than a second loader because the parse, the validity filter and
    the degenerate-sheet rule are the same for every arm, and a copy of this loop is a copy of
    three rules that must not drift -- the template arm needs a different GROUPING, not
    different loading.

    Drops are counted into DROPPED rather than being silent. The degenerate-sheet rule in
    particular is CORRECT and consequential: a model that answers every one of 62 items
    identically has no position to compare, and scoring that against a normal sheet reports a
    huge side-flip count that reads as an effect. Excluding it is right; excluding it invisibly
    is how a pair loses an arm without anyone noticing.
    """
    key = key or _default_key
    cells = collections.defaultdict(list)
    # SORTED, because glob order is the filesystem's and the filesystem's is not the same on
    # two machines. Found 2026-09-06: this gate was red in CI and green on the author's box
    # against the same commit, differing in exactly one number -- the presentation-order
    # endpoint p90, 10 here and 11 there, on the same 84 pairs. Same count, different values,
    # which can only mean the pairs themselves differed.
    #
    # The path runs through `modal()`, whose Counter.most_common(1) breaks a TIE by insertion
    # order. Insertion order is this loop's order, this loop's order was glob's, and glob's is
    # ext4 on one side and NTFS on the other. A published percentile was a property of the
    # filesystem. Sorting here makes the corpus order canonical; modal() no longer depends on
    # it either way (see its own note), and both are fixed so neither can reintroduce it.
    for p in sorted(glob.glob(os.path.join(STUDY, pattern), recursive=True)):
        for line in io.open(p, encoding="utf-8"):
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("schema") != "compass-run/1":
                continue
            if not r.get("valid"):
                _count_drop("invalid run (%s)" % (r.get("failure_mode") or "unclassified"), r)
                continue
            if condition and r["condition"] != condition:
                continue
            vals = [a["position"] for a in r["answers"]]
            if len(set(vals)) == 1:
                _count_drop("degenerate sheet, all %d: %s" % (vals[0], r.get("model")), r)
                continue
            cells[key(r)].append({a["q"]: a["position"] for a in r["answers"]})
    return cells


def modal(runs):
    """The per-item modal answer across a cell's runs.

    TIES ARE BROKEN BY THE LOWER POSITION, EXPLICITLY. `Counter.most_common(1)` breaks a tie by
    insertion order, and insertion order here is the order the runs were read, which was the
    order the filesystem listed them. On a 2-2 split between Disagree and Agree that made the
    reference sheet -- and therefore every endpoint delta measured against it -- a property of
    whether the corpus sat on ext4 or NTFS. It moved the published presentation-order endpoint
    p90 between 10 and 11 depending on the machine, which is how it was found.

    The lower position is not a better answer than the higher one; it is an arbitrary rule, and
    an arbitrary rule that is WRITTEN DOWN is the whole difference. A tie means the cell has no
    modal answer for that item, and any convention has to be disclosed rather than inherited
    from a dict.
    """
    acc = collections.defaultdict(list)
    for r in runs:
        for q, v in r.items():
            acc[q].append(v)
    out = {}
    for q, v in acc.items():
        counts = collections.Counter(v)
        top = max(counts.values())
        out[q] = min(pos for pos, n in counts.items() if n == top)
    return out


def both_stats(a, b):
    shared = [q for q in a if q in b]
    sideflips = sum(1 for q in shared if side(a[q]) != side(b[q]))
    gained = sum(1 for q in shared if not ext(a[q]) and ext(b[q]))
    lost = sum(1 for q in shared if ext(a[q]) and not ext(b[q]))
    return sideflips, abs(gained - lost)


def ci(vals, clusters=None):
    """Bootstrap CI on the p90, so a floor carries an interval rather than a point.

    `clusters` is a list parallel to `vals` naming the MODEL each pair came from. When given,
    the bootstrap resamples MODELS with replacement and takes all of a model's pairs together,
    which is the correct unit: 45 pairs from one model under ten templates are not 45
    independent draws, they are one model measured 45 ways. Ten templates produce nine pairs
    each, so every pair shares a sheet with eight others.

    Measured 2026-09-04: the paraphrase floor's naive interval is [6, 7] on 1067 pairs; the
    cluster interval over its six models is wider, and the honest one. The naive version
    understates uncertainty by exactly the factor the pairing inflates n.

    Falls back to the flat bootstrap when no clusters are supplied, so every existing caller
    keeps its behaviour rather than silently acquiring a different statistic.
    """
    if len(vals) < 5:
        return float("nan"), float("nan")
    rng = random.Random(BOOT_SEED)
    p90s = []
    if clusters:
        # A silent length mismatch would drop pairs or clusters without a word -- `zip` stops
        # at the shorter, so `ci(sf, clusters[:10])` on 1,067 pairs would quietly bootstrap ten
        # of them and return an interval that looks computed. Refuse instead.
        if len(clusters) != len(vals):
            raise ValueError("clusters (%d) must be parallel to vals (%d)"
                             % (len(clusters), len(vals)))
        groups = collections.defaultdict(list)
        for v, c in zip(vals, clusters):
            groups[c].append(v)
        keys = sorted(groups)
        if len(keys) < 3:
            # Two or fewer clusters cannot carry a cluster bootstrap: every resample is one of
            # three shapes. Say so rather than returning an interval that looks computed.
            return float("nan"), float("nan")
        for _ in range(BOOT_N):
            drawn = []
            for _ in range(len(keys)):
                drawn.extend(groups[keys[rng.randrange(len(keys))]])
            s = sorted(drawn)
            p90s.append(s[int(0.9 * len(s)) - 1])
    else:
        for _ in range(BOOT_N):
            s = sorted(rng.choices(vals, k=len(vals)))
            p90s.append(s[int(0.9 * len(s)) - 1])
    p90s.sort()
    return p90s[int(0.025 * BOOT_N)], p90s[int(0.975 * BOOT_N)]


def ci_str(pair, clustered=False):
    """Render a bootstrap interval, or say why there is not one.

    Printing "[nan, nan]" into a published table invites a reader to treat an undefined
    interval as a computed one; the table should say so in words instead.

    `clustered` changes the WORDS, because the two reasons are different and "n too small" is
    wrong for one of them. A flat bootstrap declines under five pairs -- that is a small n. A
    cluster bootstrap declines under three MODELS, which can happen with a thousand pairs, and
    reporting that as "n too small" would tell a reader the opposite of the truth about a row
    whose pair count is its most impressive number.
    """
    lo, hi = pair
    if lo != lo or hi != hi:
        return "too few models" if clustered else "n too small"
    return "[%.0f, %.0f]" % (lo, hi)


def summarise(name, pairs, note="", clusters=None):
    if not pairs:
        return None
    sf = [p[0] for p in pairs]
    ep = [p[1] for p in pairs]

    def q(v):
        # Round the median half-up rather than letting %d truncate it downstream. The order
        # floor's true median is 7.5; the paper's table printed 7 and the website said 8,
        # which is one quantity disagreeing with itself across two public surfaces because
        # two places each rounded it their own way. One convention, applied here, once.
        v = sorted(v)
        med = st.median(v)
        med = int(med + 0.5) if med >= 0 else int(med - 0.5)
        return med, v[int(0.9 * len(v)) - 1] if len(v) >= 10 else max(v), max(v)

    lo, hi = ci(sf, clusters)
    side, endpoint = q(sf), q(ep)
    # DISCLOSE, do not hide: for n < 10 the q() above deliberately reports the MAX as the p90,
    # because a nearest-rank 90th percentile on nine or fewer observations IS the maximum. That
    # is a defensible convention and an undisclosed one -- the table prints "med / p90 / max"
    # and a small arm prints the same number twice, which reads as two statistics agreeing
    # rather than one quantity repeated. The requantisation row (n=4) and the prompt-condition
    # row (n=7) both do this.
    return {"name": name, "n": len(pairs),
            "side": side, "endpoint": endpoint, "side_ci": (lo, hi), "note": note,
            "small_n": len(pairs) < 10,
            # Which bootstrap produced side_ci, so a renderer can say why an interval is
            # missing in the right words -- "too few models" and "n too small" are different
            # facts, and a clustered row can have a thousand pairs and still decline.
            "clustered": bool(clusters),
            "n_clusters": len(set(clusters)) if clusters else None,
            # PER CLUSTER, so a pooled p90 is never the only number on offer. Cell sizes are
            # unequal by construction -- pairs scale QUADRATICALLY in runs per cell, so
            # qwen3.8-flash contributes 236 pairs from 23 runs while kimi-k3 contributes 129
            # from 17, and kimi is the noisiest model in the arm. The cluster bootstrap fixed
            # the INTERVAL's unit; it does nothing for the point estimate's weighting.
            #
            # Measured on the paraphrase arm the pooled p90 (6) happens to equal the median of
            # the per-model p90s (6), so the imbalance moves nothing today. The SPREAD is the
            # part that matters and it is large: 3 for gemini-3.5-flash-lite against 10 for
            # kimi-k3, so the pooled figure sits below the floor of the model with the highest
            # one. Any per-model claim has to clear that model's own row.
            "per_cluster": _per_cluster(sf, clusters) if clusters else None,
            "p90_is_max": side[1] == side[2]}


def _per_cluster(vals, clusters):
    """[(cluster, n, med, p90, max)] sorted by p90, so the spread reads at a glance."""
    groups = collections.defaultdict(list)
    for v, c in zip(vals, clusters):
        groups[c].append(v)
    out = []
    for name, v in groups.items():
        v = sorted(v)
        p90 = v[int(0.9 * len(v)) - 1] if len(v) >= 10 else max(v)
        out.append((name, len(v), v[len(v) // 2], p90, max(v)))
    return sorted(out, key=lambda r: -r[3])


def floor_order():
    # The canonical-order sheets live in the temp-0 and vendor sweeps; the shuffled arms live
    # in the order dirs. A pair needs one of each for the same model, so every source that
    # holds a condition-A sheet at a given shuffle seed has to be loaded here.
    #
    # 2026-09-01: 2026-08-31-order-control and the frontier canonical sheets in
    # 2026-08-30-temp0 were both missing from this list, so 27 runs collected specifically to
    # extend this floor onto frontier models contributed nothing to it and the row stayed at
    # 18 pairs of 2024-vintage local models. Collecting data and then not reading it is the
    # same defect as measuring the source instead of the artifact, one step earlier.
    by = _order_cells()
    pairs = []
    for m, orders in by.items():
        ks = list(orders)
        for i in range(len(ks)):
            for j in range(i + 1, len(ks)):
                pairs.append(both_stats(orders[ks[i]], orders[ks[j]]))
    return summarise("presentation order", pairs, "same model, same condition, item order only")


# Run directories deliberately withheld from the order floor, each with its reason. This is
# an EXCLUDE list on purpose, and the inversion is the whole point -- see _order_cells.
ORDER_EXCLUDE = {
    # A targeted re-collection of the three Google models that refuse most, run to probe
    # refusal rather than order. Its runs are legitimate order observations, but pooling a
    # sample selected on one behaviour into a floor for another invites the question and the
    # floor does not need it. Named here rather than silently absent.
    "2026-08-31-google-orderfloor",
}


def _order_cells(with_sources=False):
    """Condition-A sheets from EVERY run directory except those named in ORDER_EXCLUDE.

    THE LIST USED TO POINT THE OTHER WAY, and it failed twice for the same reason.
    2026-09-01: `2026-08-31-order-control` and the frontier canonical sheets in
    `2026-08-30-temp0` were missing, so 27 runs collected specifically to extend this floor
    onto frontier models contributed nothing and the row stayed at 18 pairs of 2024-vintage
    local models. The fix was to add those two directories to the include list.
    2026-09-02: 14 more runs were collected to extend the frontier arm, and the row stayed at
    21 pairs -- because a new directory is invisible to an include list by construction. The
    previous fix guaranteed the recurrence.

    So the default is now READ EVERYTHING and anything withheld is named with a reason. A
    directory that arrives tomorrow is counted tomorrow.

    THAT DEFAULT NEEDS A GUARD, and it did not have one. This docstring used to end "the
    pairing logic keys on (model, condition, shuffle seed), so an extra source can only add
    cells, never corrupt one." False, and falsified within a day: the paraphrase arm collected
    2026-09-04 writes condition-A runs at shuffle_seed None under ten different instruction
    templates, all of which hash to the SAME key as the canonical-order sheet. 107 non-T01
    runs were pooled into canonical-order cells, so a cell's modal answer became a majority
    vote across paraphrases. Point estimates survived; the published p90 interval did not
    (pooled [7,13] with them, [7,12] without).

    An include list fails open on new directories; a read-everything default fails open on new
    FACTORS. Both are the same bug at different scopes, and the answer to the second is that
    the order floor holds every non-order factor fixed by construction: only the canonical
    template T01 enters, because "same model, same condition, item order only" is what the row
    claims to measure.
    """
    cells = collections.defaultdict(list)
    sources = collections.Counter()
    for path in sorted(glob.glob(os.path.join(STUDY, "runs", "**", "*.jsonl"), recursive=True)):
        rel = os.path.relpath(path, os.path.join(STUDY, "runs")).replace("\\", "/")
        if rel.split("/")[0] in ORDER_EXCLUDE:
            continue
        for key, runs in load(os.path.relpath(path, STUDY), "A",
                              key=_order_key).items():
            if key[3] != "T01":
                continue
            cells[key[:3]].extend(runs)
            sources[rel.split("/")[0]] += len(runs)
    by = collections.defaultdict(dict)
    for (m, c, o), runs in cells.items():
        if c == "A":
            by[m][o] = modal(runs)
    return (by, sources) if with_sources else by


def order_sources():
    """Which run directories actually contributed condition-A order cells, and how many.

    Reported so "the floor reads everything" is checkable rather than asserted -- and it
    stopped being checkable the moment the floor started filtering. This function counted every
    valid condition-A run on disk, applying neither ORDER_EXCLUDE nor the T01 filter, so after
    2026-09-04 it credited `2026-09-04-template-floor` with 119 contributed runs when 12 enter,
    and `2026-08-31-google-orderfloor` with 2 when none do. A provenance report that overstates
    its own inputs is worse than no report: it is the assertion the report exists to replace.

    Derived from `_order_cells` now, which is the single place that knows what the floor reads.
    Two encodings of "exclude these dirs, keep only T01" is exactly the drift this file keeps
    finding elsewhere.
    """
    return _order_cells(with_sources=True)[1]


def floor_order_by_class():
    """The order floor split by model class, because pooling the two hides the finding.

    Added 2026-09-01, when the frontier sweep doubled this row from 18 pairs to 39 and the
    pooled p90 fell from 14 to 12. That single number was concealing a bimodal distribution:
    reordering the questionnaire moves a median of 8 items on the 2024-vintage 7-14B open
    models this literature was largely built on, and a median of 3 on 2026 frontier APIs.

    Reporting only the pooled figure would be the exact defect this project has already
    caught in itself once -- a net aggregate concealing gross movement -- and it would have
    been in the paper's title claim.

    Rottger et al. (2024) conjectured this: "It is plausible that future models, as a product
    of more comprehensive alignment, will also exhibit fewer instabilities." This is that
    conjecture measured.
    """
    by = _order_cells()
    out = {}
    for label, want_api in (("presentation order, local open-weight", False),
                            ("presentation order, frontier API", True)):
        pairs = []
        for m, orders in by.items():
            if ("/" in m) != want_api:
                continue
            ks = list(orders)
            for i in range(len(ks)):
                for j in range(i + 1, len(ks)):
                    pairs.append(both_stats(orders[ks[i]], orders[ks[j]]))
        note = ("2026 frontier models served over an API"
                if want_api else "7-14B open-weight models of the 2024 generation")
        out[label] = summarise(label, pairs, note)
    return out


def floor_same_version():
    cells = load("runs/2026-08-31-lineage/**/*.jsonl", "A")
    by = collections.defaultdict(list)
    for (m, c, o), runs in cells.items():
        by[m].extend(runs)
    ids = [m for m, v in by.items() if len(v) >= 2]
    parsed = {i: parse(i) for i in ids}
    pairs = []
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            label, is_version = classify(parsed[a], parsed[b])
            if not is_version and label.endswith("(null)"):
                pairs.append(both_stats(modal(by[a]), modal(by[b])))
    return summarise("same-version variants", pairs, "size / mode / snapshot / tier, same version")


def _template_cells(runs_only=False):
    """Condition-A sheets from the paraphrase arm, keyed (model, condition, template)."""
    return load("runs/2026-09-04-template-floor/**/*.jsonl", "A", key=_template_key)


def floor_replicate():
    """THE REPLICATE FLOOR: same model, same template, same temperature, run again.

    Added 2026-09-04 after an adversarial review, and it is the control the paraphrase floor
    needed from the start. This study runs at temperature 0 and treats repeats as replicates
    to be collapsed, which quietly assumes that a repeat changes nothing. It does not: hosted
    inference batches requests, routes MoE experts and reduces in nondeterministic order, so
    temperature 0 is a decoding rule and not a determinism guarantee.

    Measuring it matters twice over. First, it is the floor UNDER every other floor here --
    anything that varies a factor across two runs is measuring that factor plus this. Second,
    it is precisely the quantity Naser and Sakhawat use to certify reliability: they run one
    prompt ten times at temperature 0, observe agreement, and call the instrument stable. This
    row says what that agreement is actually worth on current models.

    Pairs are RUN AGAINST RUN inside one (model, template) cell -- no modal collapse, because
    the modal is what hid this. See floor_template.
    """
    cells = _template_cells()
    pairs, clusters = [], []
    for (m, c, tpl), runs in sorted(cells.items()):
        for i in range(len(runs)):
            for j in range(i + 1, len(runs)):
                pairs.append(both_stats(runs[i], runs[j]))
                clusters.append(m)
    return summarise("run-to-run replicate", pairs,
                     "same model, same template, temperature 0 -- the floor under the floors; "
                     "interval is a CLUSTER bootstrap over models",
                     clusters=clusters)


def floor_template():
    """The paraphrase floor: same model, same order, same temperature, reworded instruction.

    PAIRED AT RUN LEVEL, NOT MODAL-COLLAPSED, and the reason is a defect worth stating.
    This function used to call modal() on each cell's runs. `modal()` takes
    `Counter.most_common(1)`, and with exactly TWO runs every disagreement is a 1-1 tie that
    Counter breaks by insertion order -- so run 1 won every tie and run 2 contributed nothing
    at all. 54 of 60 cells hold exactly two runs. Rebuilding the floor from run 1 alone
    reproduced the shipped numbers to the digit. The design was one run per cell wearing a
    two-run label, and "run-to-run noise is inside these numbers" understated it: the second
    run was collected and then discarded by a tie-break.

    Pairing every run against every run across templates keeps both, and makes the comparison
    to floor_replicate an apples-to-apples one: identical pairing, identical statistic, the
    only difference being whether the template changed. The paraphrase contribution is the
    EXCESS of this row over that one, and on current models that excess is about one item at
    p90 -- which is the honest headline and not the one first reported.
    """
    cells = _template_cells()
    by_model = collections.defaultdict(dict)
    for (m, c, tpl), runs in cells.items():
        by_model[m][tpl] = runs
    pairs, clusters = [], []
    for m, templates in sorted(by_model.items()):
        tids = sorted(templates)
        for i in range(len(tids)):
            for j in range(i + 1, len(tids)):
                for a in templates[tids[i]]:
                    for b in templates[tids[j]]:
                        pairs.append(both_stats(a, b))
                        clusters.append(m)
    return summarise("instruction paraphrase", pairs,
                     "same model, same order, temperature 0, reworded wrapper; run-level "
                     "pairs, CLUSTER bootstrap over models; compare to run-to-run replicate",
                     clusters=clusters)


def floor_template_modal():
    """The modal-collapsed version, kept ONLY so the superseded number stays reproducible.

    NOT for reporting. This is what `floor_template` did until 2026-09-04, and its result --
    270 pairs, side 3 / 6 / 13 -- is the number that reached the paper's floors table before
    an adversarial review showed the modal of two runs is just run 1. Keeping it callable
    means the retired figure can be regenerated by anyone checking what changed, instead of
    surviving only as a claim in a results file.

    Ten paraphrases, meaning held constant (see PARAPHRASE_TEMPLATES in run_compass.py and the
    import-time assertions that keep them the same task). Six 2026-frontier models, one per
    vendor family, at temperature 0 in condition A.
    """
    cells = load("runs/2026-09-04-template-floor/**/*.jsonl", "A", key=_template_key)
    by_model = collections.defaultdict(dict)
    for (m, c, tpl), runs in cells.items():
        by_model[m][tpl] = modal(runs)
    pairs = []
    for m, templates in sorted(by_model.items()):
        tids = sorted(templates)
        for i in range(len(tids)):
            for j in range(i + 1, len(tids)):
                pairs.append(both_stats(templates[tids[i]], templates[tids[j]]))
    return summarise("instruction paraphrase", pairs,
                     "same model, same order, same temperature, reworded wrapper")


def floor_quant():
    """Same base weights, two quantisations, everything else held.

    PAIRS WITHIN A FAMILY, from check_arm_match.QUANT_PAIRS. It used to pair every model in a
    condition against every other, which was harmless while the arm held one family -- gemma2
    at Q4_0 vs Q8_0 -- and became a silent corruption the moment a second family landed on
    2026-09-04: llama3.1-Q4 against mistral-Q8 is not a requantisation pair, it is a
    cross-model comparison wearing the label of a null. The gated pair list is the authority
    on what a pair is, so the floor reads it instead of inferring one from directory contents.

    Note the arm previously reported "4 pairs" for ONE weights family across four prompt
    conditions. Four conditions of one model are not four independent pairs; the n column did
    not distinguish them, and the row was the only one in the table with no confidence
    interval.
    """
    cells = load("runs/2026-08-30-quant-null/**/*.jsonl")
    cells.update(load("runs/2026-09-04-quant-null/**/*.jsonl"))
    by = collections.defaultdict(dict)
    for (m, c, o), runs in cells.items():
        by[c][m] = modal(runs)
    pairs, families = [], set()
    # HALF-PAIRS ARE COUNTED, not dropped in silence. floor_ablation grew an "eligible but
    # produced no arm-matched condition" trap on 2026-09-04 and this function, written the
    # same day, did not get one -- so a family gated ELIGIBLE could contribute nothing and the
    # row would simply report a smaller n. Measured: mistral-7b is one of five gated pairs and
    # contributes ZERO (its base run is invalid in A and its Q8 runs are invalid in B/C/D),
    # while llama31-8b loses C and D and llama32-3b loses D. Seven of twenty possible cells,
    # invisible. A count that shrinks without saying why is how a floor quietly becomes a
    # different measurement.
    half = []
    for c, models in sorted(by.items()):
        for base, quant, label in QUANT_PAIRS:
            has_base, has_quant = base in models, quant in models
            if has_base and has_quant:
                pairs.append(both_stats(models[base], models[quant]))
                families.add(label)
            elif has_base or has_quant:
                half.append("%s %s (%s only)"
                            % (label, c, "Q8" if has_quant else "base"))

    contributing = {lab for _, _, lab in QUANT_PAIRS} & families
    silent = [lab for _, _, lab in QUANT_PAIRS if lab not in contributing]
    out = summarise("requantisation", pairs,
                    "same weights, Q4 vs Q8, no other change; %d of %d gated famil%s "
                    "contribute, %d half-pair(s) lost to invalid runs"
                    % (len(families), len(QUANT_PAIRS),
                       "y" if len(QUANT_PAIRS) == 1 else "ies", len(half)))
    if out:
        out["half_pairs"] = half
        # A pair the gate passed that then contributes nothing is the case worth naming, not
        # merely counting: it looks like a measurement that was made and was not.
        out["skipped"] = [(lab, "gated ELIGIBLE but contributed no pair -- every condition "
                                "lost one arm to an invalid run") for lab in silent]
    return out


def floor_ablation():
    """Stock vs ablated, arm-matched, per condition.

    EXCLUSIONS ARE BY RULING NOW, not by luck. `check_arm_match.INELIGIBLE_PAIRS` holds the
    three of six locally-held pairs that gate measured as invalid comparison arms on
    2026-08-30 -- mismatched quantisation, dropped stop tokens, baked sampling parameters.
    None of those differences is the refusal direction.

    Before 2026-09-04 this function did not know that. All three were excluded anyway, by
    three unrelated accidents: two emit prose with no parsable answers, and the third answers
    every item identically so the loader calls it degenerate. The floor was right and its
    reason was wrong, which is a floor that holds until one of the accidents stops happening.
    """
    pairs, skipped = [], []
    pair_dirs = sorted(glob.glob(os.path.join(STUDY, "runs/2026-08-30-ablation-pairs/*")))
    for pair_dir in pair_dirs:
        label = os.path.basename(pair_dir)
        if label in INELIGIBLE_PAIRS:
            skipped.append((label, INELIGIBLE_PAIRS[label]))
            continue
        arms = {}
        for arm in ("stock", "ablated"):
            cells = load(os.path.join("runs/2026-08-30-ablation-pairs",
                                      os.path.basename(pair_dir), arm, "*.jsonl"))
            per_cond = collections.defaultdict(list)
            for (m, c, o), runs in cells.items():
                per_cond[c].extend(runs)
            arms[arm] = {c: modal(v) for c, v in per_cond.items()}
        for c in set(arms.get("stock", {})) & set(arms.get("ablated", {})):
            pairs.append(both_stats(arms["stock"][c], arms["ablated"][c]))
        if not (set(arms.get("stock", {})) & set(arms.get("ablated", {}))):
            # Eligible by the gate and still contributing nothing. That combination has no
            # documented cause, so it must not pass quietly the way the ruled-out three did.
            skipped.append((label, "ELIGIBLE but produced no arm-matched condition -- "
                                   "investigate, this has no recorded reason"))
    out = summarise("refusal-direction ablation", pairs,
                    "%d of %d collected model pairs excluded, see check_arm_match"
                    % (len(skipped), len(pair_dirs)))
    if out:
        out["skipped"] = skipped
    return out


def floor_conditions():
    # EVERY TEMPERATURE-0 COLLECTION, not one directory.
    #
    # This read `runs/2026-08-30-temp0/**` alone, which held 8 models and yielded 7 pairs -- so
    # the paper's own reference scale, the deliberate manipulation every nuisance floor is
    # compared against, rested on seven pairs with a p90 95% CI of [2, 14]. The error bar on the
    # ruler was nearly as wide as the ruler.
    #
    # It looked frozen for a different and wrong reason: the 2026-09-05 frontier models refuse
    # condition A, so a first read concluded the floor could never grow. It could. It was
    # under-collected, not blocked -- 19 further panel models answer A and had simply never been
    # run greedy. `scripts/extend_manipulation_floor.py` collects them at the identical protocol
    # (temperature 0.0, seed 20260830, max_tokens 8192, 3 runs) and this glob picks them up.
    #
    # The date-prefixed glob is the point: a later temp-0 collection joins the floor without
    # anyone editing this function, and a collection at a DIFFERENT temperature cannot, because
    # it will not be named `*-temp0*`.
    # KEYED BY COLLECTION DATE, because pooling across dates invents numbers.
    #
    # `_default_key` is (model, condition, shuffle_seed) and shuffle_seed is None on every
    # temp-0 record, so widening the glob to three directories silently merged runs collected
    # on different days into one modal sheet. Measured: x-ai/grok-4.5's A-to-D is 3 on
    # 2026-08-30 and 18 on 2026-09-05 -- its D-arm behaviour changed in six days -- and the
    # pooled modal reported 16, a value the model produced on NEITHER date.
    #
    # A floor row built from a sheet no model ever emitted is not a measurement. One date per
    # (model, condition); when a model was collected twice, the LATER date wins, and the
    # difference is a drift finding rather than something to average away.
    raw = load("runs/*temp0*/**/*.jsonl", key=lambda r: (r["model"], r["condition"],
                                                         r.get("collected_at", "")[:10]))
    cells = {}
    for (m, c, day), runs in sorted(raw.items()):
        cells[(m, c, day)] = runs
    by = collections.defaultdict(dict)
    #: Per model, how much its OWN runs disagree with each other inside one condition. A pair
    #: whose A-to-D difference does not exceed this is measuring the model's instability, not
    #: the manipulation.
    within = collections.defaultdict(list)
    # sorted() above puts the earliest date first, so a later collection of the same
    # (model, condition) overwrites it here. One date per cell, never a blend of two.
    seen_day = {}
    for (m, c, day), runs in cells.items():
        by[m][c] = modal(runs)
        seen_day[(m, c)] = day
        for i in range(len(runs)):
            for j in range(i + 1, len(runs)):
                within[m].append(both_stats(runs[i], runs[j])[0])

    # A pair whose two arms come from DIFFERENT days is not a clean manipulation contrast --
    # it carries whatever the model did in between. Reported rather than dropped, because with
    # this few pairs dropping is expensive and the drift is itself worth seeing.
    split_day = sorted(m for m in by
                       if "A" in by[m] and "D" in by[m]
                       and seen_day.get((m, "A")) != seen_day.get((m, "D")))

    # THE "NOISE-DOMINATED" RULE IS GONE, AND SO IS THE EXAMPLE THAT DEFENDED IT.
    #
    # A previous version of this function flagged pairs whose A-to-D difference did not exceed
    # the model's own within-condition spread, first against the MAX of that spread (14 of 20
    # flagged) and then against the MEDIAN (6 of 20). The comment justifying the switch said max
    # "condemned models that are otherwise stable: grok-4.6 moves 14 items between A and D
    # against a within-cell median of 2 and one bad pair at 8."
    #
    # THAT EXAMPLE WAS NOT REAL. grok-4.6's A-to-D is 14 and its within-cell max is 8; 14 > 8,
    # so it was never flagged under either rule. A fabricated case was used to justify changing
    # a statistic in the direction that made this project's own work look better -- which is
    # precisely what this paper convicts other studies of, committed inside the tool built to
    # prevent it. Recorded here rather than quietly deleted.
    #
    # The rule was also wrong on its own terms. Under the median form it flagged
    # claude-opus-4.6, whose runs are byte-identical (within = 0) and whose A-to-D is exactly 0
    # -- the cleanest possible measurement of NO EFFECT, relabelled as "cannot tell". And it
    # did NOT flag the two models the comment was written about: z-ai/glm-5.2 (32 items between
    # two runs of one condition) and moonshotai/kimi-k3 (20) both pass it.
    #
    # A difference that is small because the instruction did nothing and a difference that is
    # small because the model cannot hold still are different facts, and comparing a
    # modal-vs-modal number against single-run-vs-single-run spread cannot separate them.
    # Separating them needs an exchangeability test at a run count this collection does not
    # have: with 3 runs per arm the smallest attainable permutation p is 0.10.
    pairs = []
    for m, conds in by.items():
        if "A" in conds and "D" in conds:
            pairs.append(both_stats(conds["A"], conds["D"]))

    # THE NOTE IS COMPUTED. A hand-typed "(14, 16, 17)" was in this string an hour ago and was
    # already wrong after the date fix.
    sides = sorted(s for s, _e in pairs)
    tail = [(m, both_stats(by[m]["A"], by[m]["D"])[0]) for m in by
            if "A" in by[m] and "D" in by[m] and both_stats(by[m]["A"], by[m]["D"])[0] > 8]
    note = ("the deliberate manipulation, for scale -- READ THE SPREAD, NOT THE p90: "
            "%d of %d models move 8 items or fewer, inside the run-to-run replicate floor. "
            "The tail is %s" % (sum(1 for s in sides if s <= 8), len(sides),
                                ", ".join("%s %d" % (m.split("/")[-1], v)
                                          for m, v in sorted(tail, key=lambda t: -t[1]))))
    if split_day:
        note += ("; %d pair(s) have their two arms from different days: %s"
                 % (len(split_day), ", ".join(m.split("/")[-1] for m in split_day)))
    return summarise("prompt condition A->D", pairs, note)


def _condition_pairs(pattern):
    """A→D pairs from one collection, keyed by (model, condition, collection date).

    Extracted from floor_conditions so the wave arm below runs the SAME pairing rather than a
    copy of it. A second implementation of "what is a manipulation pair" is a second definition
    of the paper's reference scale, and the two would drift.

    Returns (pairs, by_model, split_day).
    """
    raw = load(pattern, key=lambda r: (r["model"], r["condition"],
                                       r.get("collected_at", "")[:10]))
    by = collections.defaultdict(dict)
    seen_day = {}
    for (m, c, day), runs in sorted(raw.items()):
        by[m][c] = modal(runs)
        seen_day[(m, c)] = day
    split_day = sorted(m for m in by
                       if "A" in by[m] and "D" in by[m]
                       and seen_day.get((m, "A")) != seen_day.get((m, "D")))
    pairs = [both_stats(cs["A"], cs["D"]) for _m, cs in sorted(by.items())
             if "A" in cs and "D" in cs]
    return pairs, by, split_day


def floor_conditions_wave():
    """THE REFERENCE SCALE, RE-MEASURED UNDER ONE PROTOCOL IN ONE SITTING.

    The `prompt condition A->D` row above is the paper's reference scale, and it is pooled
    across collections: temperature 0, three runs, several dates, and one pair whose two arms
    come from different days. It was the open item after wave 0 -- re-collect it under one
    protocol, one sitting -- and wave 0 turned out to have already done it. 31 models were run
    under all four conditions at temperature 0.7 with a swept seed, five runs each, in a single
    sitting. 25 of them answer both A and D; the other six refuse the balance instruction
    outright, which is section 1's finding rather than a gap here.

    THE COMPARISON IS IN THE SAME UNITS. This pairs modal-vs-modal, and so do the two nuisance
    floors it is compared against: `floor_order` pairs `modal(runs)` per item order, and
    `floor_same_version` pairs `modal()` per variant. Only `floor_replicate` pairs raw runs,
    correctly, because raw run-to-run noise is the thing it measures.

    AND THE ANSWER MOVES. Pooled temp-0: p90 15 over 20 pairs. Here: **p90 7 over 25 pairs**,
    below the presentation-order floor and below the same-version floor. 23 of 25 models move 8
    items or fewer.

    WHY THE TWO DIFFER, stated rather than picked between. At temperature 0 with a fixed seed a
    cell's runs are near-identical, so its "modal" sheet is effectively a single observation
    carrying single-run noise. Here the modal is a real consensus across five different seeds,
    so noise averages out and what is left is the position. That makes this the better estimate
    of the quantity the paper actually compares -- does the instruction move the model's central
    position -- and it makes the pooled row an upper bound inflated by the noise it could not
    average away. Both rows are printed. Neither is deleted.
    """
    pairs, by, split_day = _condition_pairs("runs/*-wave/*.jsonl")
    if not pairs:
        return None
    sides = sorted(s for s, _e in pairs)
    tail = sorted(((m, both_stats(cs["A"], cs["D"])[0]) for m, cs in by.items()
                   if "A" in cs and "D" in cs), key=lambda t: -t[1])
    refused = sorted(m for m, cs in by.items() if "D" in cs and "A" not in cs)
    note = ("the same manipulation under ONE protocol in ONE sitting -- temperature 0.7, swept "
            "seed, 5 runs, wave 0. %d of %d models move 8 items or fewer. The tail is %s. "
            "%d panel model(s) contribute no pair because they refuse condition A outright: %s"
            % (sum(1 for s in sides if s <= 8), len(sides),
               ", ".join("%s %d" % (m.split("/")[-1], v) for m, v in tail[:3]),
               len(refused), ", ".join(m.split("/")[-1] for m in refused)))
    if split_day:
        note += ("; %d pair(s) span more than one date: %s"
                 % (len(split_day), ", ".join(m.split("/")[-1] for m in split_day)))
    return summarise("prompt condition A->D, one sitting", pairs, note,
                     clusters=[m for m, cs in sorted(by.items()) if "A" in cs and "D" in cs])


#: EVERY FLOOR, in one place. This list lived here AND in `key_numbers.floors()`, so adding
#: `floor_conditions_wave` to the table left the gate blind to it -- a new row could appear in
#: the paper with nothing recomputing the sentences around it, which is the one thing that gate
#: exists to prevent. One list, two readers.
ALL_FLOORS = (floor_order, floor_same_version, floor_template, floor_replicate,
              floor_quant, floor_ablation, floor_conditions, floor_conditions_wave)


def all_floors():
    """Every floor that measured something, keyed by name."""
    out = {}
    for fn in ALL_FLOORS:
        r = fn()
        if r:
            out[r["name"]] = r
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--markdown", action="store_true")
    args = ap.parse_args(argv)

    rows = list(all_floors().values())
    rows.sort(key=lambda r: -r["side"][1])

    if args.markdown:
        print("| factor | n pairs | side-flip med / p90 / max | p90 95% CI | endpoint med / p90 / max |")
        print("|---|---:|---|---|---|")
        for r in rows:
            mark = " †" if r.get("small_n") and r.get("p90_is_max") else ""
            print("| %s%s | %d | %d / %d / %d | %s | %d / %d / %d |"
                  % (r["name"], mark, r["n"], *r["side"], ci_str(r["side_ci"], r.get("clustered")),
                     *r["endpoint"]))
        if any(r.get("small_n") and r.get("p90_is_max") for r in rows):
            print()
            print("† fewer than 10 pairs, so the 90th percentile IS the maximum by "
                  "nearest-rank and the two columns print one number, not two.")
        # A row's exclusions belong beside the row. The ablation floor rests on three of six
        # collected model pairs and the table said only "arm-matched pairs only", which reads
        # as a description of the method rather than as half the data being withheld.
        for r in rows:
            for label, why in r.get("skipped") or ():
                print()
                print("**%s excludes `%s`:** %s" % (r["name"], label, why))
        return 0

    print("MEASURED FLOORS -- every row computed from runs/, both statistics")
    print("side-flip = crossed the agree/disagree boundary")
    print("endpoint  = gained/lost a Strongly answer (|b-c|)")
    print()
    print("%-28s %6s %18s %14s %18s" % ("factor", "pairs", "side med/p90/max",
                                        "p90 95% CI", "endpoint med/p90/max"))
    for r in rows:
        print("%-28s %6d %18s %14s %18s"
              % (r["name"], r["n"], "%d / %d / %d" % r["side"],
                 ci_str(r["side_ci"], r.get("clustered")), "%d / %d / %d" % r["endpoint"]))
    print()
    for r in rows:
        print("  %-28s %s" % (r["name"], r["note"]))
        for label, why in r.get("skipped") or ():
            print("  %-28s   excluded %s: %s" % ("", label, why))
        # Never let a pooled p90 stand alone on a clustered row: the spread across models is
        # wider than the row, and a per-model claim must clear its own model.
        for name, n, med, p90, mx in r.get("per_cluster") or ():
            print("  %-28s     %-30s %4d pairs  med %2d  p90 %2d  max %2d"
                  % ("", name[:30], n, med, p90, mx))
    # Everything the loader refused, so a lost arm cannot be invisible again.
    dropped = load_report()
    if dropped:
        print()
        print("LOADER DROPPED %d run(s):" % sum(n for _, n in dropped))
        for reason, n in dropped:
            print("  x%-4d %s" % (n, reason))
    return 0


if __name__ == "__main__":
    sys.exit(main())
