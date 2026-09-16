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

#: Vendors whose models ship downloadable weights. Used ONLY to state honestly how many models
#: on the hosted side of a hosted-vs-local split are open-weight, because a table headed
#: "frontier API" against "open-weight" reads as closed-against-open and this corpus is not
#: that: most of the hosted roster is open weights served by someone else. Not used to select
#: or filter any pair -- it labels, it does not measure.
OPEN_WEIGHT_VENDORS = frozenset((
    "qwen", "z-ai", "deepseek", "moonshotai", "mistralai", "google", "meta-llama",
    "microsoft", "minimax", "tencent", "hf.co",
))

#: model -> True when it was served over an API, False when it ran locally. Populated from the
#: runs' own `channel` field the first time it is asked for.
_CHANNEL_CACHE: dict = {}


def served_over_api(model):
    """Was this model reached over an API, or run locally?

    THE SPLIT TEST USED TO BE `"/" in model` AND THAT IS NOT THE SAME QUESTION.
    A local Ollama build pulled from Hugging Face is tagged
    `hf.co/lmstudio-community/Qwen3.8-27B-GGUF:Q4_K_M` -- it has two slashes and it never left
    this machine. So the slash test calls it hosted, and the row labelled "hosted over an API"
    would have silently acquired a local model.

    No published number was wrong when this was found on 2026-09-07: the only `hf.co/` builds in
    the corpus are gemma-4-12B, whose cells are too thin to enter a class-split row at all. It
    was found because the NEXT collection planned -- 2026-generation open weights run locally, to
    separate vintage from serving path -- would have put a local `hf.co/` model straight into the
    hosted row and answered the question backwards.

    The records carry `channel` ("ollama" or "openrouter"), which is the actual property. Read
    it rather than inferring from the name: a name is a convention and this one had an exception
    in the corpus before anybody looked.
    """
    if not _CHANNEL_CACHE:
        for p in sorted(glob.glob(os.path.join(STUDY, "runs", "**", "*.jsonl"),
                                  recursive=True)):
            for line in io.open(p, encoding="utf-8"):
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                m, ch = r.get("model"), r.get("channel")
                if m and ch and m not in _CHANNEL_CACHE:
                    _CHANNEL_CACHE[m] = (ch != "ollama")
    if model in _CHANNEL_CACHE:
        return _CHANNEL_CACHE[model]
    # Unknown model: fall back to the slash, and say so rather than guessing silently.
    return "/" in model


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
    """The default key PLUS every non-order factor the order floor must hold fixed.

    `(model, condition, shuffle_seed, template, temperature)`. Template and temperature are
    carried as extra elements rather than folded in, so `_order_cells` can filter or group on
    each -- the floor's pairing logic is unchanged, it just stops being fed cells that differ in
    something other than order.

    THIS KEY HAS FAILED OPEN TWICE, ON A NEW FACTOR EACH TIME.
    2026-09-04: ten instruction templates all hashed to the canonical-order cell, so 107 non-T01
    runs made a cell's modal a majority vote across paraphrases. Template was added.
    2026-09-07: temperature-0 and temperature-0.7 runs pooled in 28 of 186 canonical cells, for
    exactly the same reason. Temperature was added.

    **The pattern is the point, and it will happen again.** "Same model, same condition, item
    order only" is a claim about everything held fixed, and this key is the only place that
    claim is enforced. Anything a future collection varies -- max_tokens, a system-prompt
    revision, a provider endpoint, a quantisation -- lands in the canonical cell and dilutes its
    modal unless it is added here. When adding an arm that varies a new parameter, add it to
    this key in the same commit, and measure the floor before and after so the dilution is on
    the record rather than assumed.

    THE THIRD FACTOR ARRIVED THE SAME WEEK, AND IS ADDED IN THE SAME COMMIT AS THE ARM THAT
    VARIES IT -- which is what the paragraph above asks for. `decoding` distinguishes a prose
    run the parser read from a grammar-constrained run where the four labels were the only
    emittable tokens. Those disagree by 17 side-flips of 62, larger than the deliberate
    manipulation, so pooling them into one canonical-order cell would be the largest
    contamination this key has seen -- and it would have happened silently the first time
    anyone collected a constrained condition-A run.
    """
    return (r["model"], r["condition"], r.get("shuffle_seed"), r.get("template", "T01"),
            r.get("temperature"), r.get("decoding", "prose"))


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


#: TWO INSTRUMENTS NOW SHARE ONE RUNNER, ONE SCHEMA AND ONE `runs/` TREE.
#:
#: `load()` filtered on `schema == "compass-run/1"` and nothing else. That was
#: sufficient while `run_compass.py` only ever administered the 62 external
#: propositions. It stopped being sufficient the moment the project authored its
#: own instrument: `data/ratchet-propositions-i3.json` is 60 items in 30 mirrored
#: pairs, administered by the SAME runner, written with the SAME schema, into the
#: SAME tree.
#:
#: Pooled, the two produce a floor computed across instruments -- a side-flip
#: count over 62 items averaged with one over 60, on different propositions, in
#: different topic space. That number describes neither instrument and there is
#: no reading of it that is correct.
#:
#: Nothing would have announced it. The cell key is
#: (model, condition, shuffle_seed); `n_items` is not in it, the schema matches,
#: `valid` is true, and the sheets parse. The first symptom would have been the
#: published pair counts moving -- 84 and 97 -- which CI asserts as a replication
#: test, so it would have failed as a REPLICATION defect rather than as the
#: pooling defect it is.
#:
#: The records already carry the discriminator: `instrument` is written straight
#: from the bank's own field (`run_compass.py:719`), so the compass sheets say
#: "politicalcompass.org ..." and the I3 sheets say "ratchet-battery-i3".
#:
#: DEFAULT IS THE COMPASS, deliberately, so this commit changes no published
#: number. The floors move to the I3 bank when its wave has been collected, by
#: flipping `INSTRUMENT_DEFAULT` in the SAME commit that moves CI's expected pair
#: counts -- one deliberate change, reviewable as one diff, rather than a silent
#: drift the day the first I3 run lands.
COMPASS_INSTRUMENT = "politicalcompass"
I3_INSTRUMENT = "ratchet-battery-i3"
RATCHET_INSTRUMENT = "ratchet-battery"

#: The study's own instrument. 32 items, 16 mirrored pairs, authored 2026-08-30.
INSTRUMENT_DEFAULT = RATCHET_INSTRUMENT

#: Item count per instrument, used ONLY when a record does not name its own.
#:
#: NOT EVERY COLLECTOR WRITES THE FIELD. `constrained_probe.py` -- the grammar /
#: constrained-decoding arm -- writes `compass-run/1` records with no
#: `instrument` key at all: 50 records across 5 models, every one `n_items: 62`.
#: Its docstring is explicit that it administers the same items ("the grammar
#: keeps the ORIGINAL WORDING. So it is the same instrument with the parser
#: removed").
#:
#: Failing closed on those dropped the whole elicitation-format row out of the
#: generated floors table, silently, the moment the guard landed. That row is a
#: published disqualification -- "ARM UNSTABLE, NOT A FLOOR" -- and deleting a
#: negative result is not a safer error than keeping it.
#:
#: So: name wins, and item count is the fallback when there is no name. This
#: still cannot pool the two instruments, because 60 != 62. It is narrower than
#: it looks -- a record with neither a name nor a matching count is still
#: dropped.
INSTRUMENT_ITEMS = {COMPASS_INSTRUMENT: 62, I3_INSTRUMENT: 60, RATCHET_INSTRUMENT: 32}

#: Every string a record may carry for a given instrument, mapped to its canonical id.
#:
#: MATCHING IS EXACT, NOT SUBSTRING. It was `_INSTRUMENT.lower() in got.lower()`, and the
#: two banks in this tree are `ratchet-battery-i3` and `ratchet-battery` -- ONE CHARACTER
#: apart, inside an `in` test, deciding which instrument a floor is computed from. A name
#: that happened to contain another's is a silent pooling, and these two were built to be
#: confusable.
#:
#: Descriptive strings are declared here rather than matched loosely. The external
#: questionnaire's record string is a sentence whose tail has changed before; that is an
#: argument for listing its prefixes, not for substring-matching every instrument.
INSTRUMENT_ALIASES = {
    COMPASS_INSTRUMENT: ("politicalcompass",),
    I3_INSTRUMENT: ("ratchet-battery-i3",),
    # NO BARE "ratchet-battery" ALIAS. It was here and it claimed every string beginning
    # `ratchet-battery-` -- including `ratchet-battery-i3`, the bank this instrument
    # replaced. A family prefix is not an identity.
    RATCHET_INSTRUMENT: ("ratchet-battery",),
}

#: Instruments collected BEFORE `instrument` was written onto every record. Only these may
#: be identified by item count when the field is absent -- see `_instrument_matches`.
#: The battery has carried the field from its first sheet, so it is deliberately absent.
PREDATES_INSTRUMENT_FIELD = (COMPASS_INSTRUMENT,)


def _canonical(name):
    """A recorded instrument string -> its canonical id, or the string itself.

    Anchored at the START of the recorded string. The external questionnaire records
    "politicalcompass.org 62-proposition test; texts and ..." and the discriminating part
    is the head; a tail edit must not change which instrument a record belongs to.
    """
    got = (name or "").strip().lower()

    # LONGEST PREFIX WINS, not the first one declared. `ratchet-battery` is a prefix of
    # `ratchet-battery-i3`, so with first-match the canonical battery would claim the
    # withdrawn bank's records the moment someone reordered this dict -- a pooling defect
    # sitting behind nothing but the order keys happen to be written in. Sorting by length
    # makes the specific alias beat the family every time, whatever the order.
    candidates = sorted(
        ((prefix, canon) for canon, prefixes in INSTRUMENT_ALIASES.items()
         for prefix in prefixes),
        key=lambda pc: -len(pc[0]))
    for prefix, canon in candidates:
        if got == prefix:
            return canon
        # THE PREFIX MUST END AT A BOUNDARY. A bare `startswith` matched
        # `ratchet-battery0` as `ratchet-battery` -- a future bank could take this one's
        # floors simply by being named next to it, which is the same one-character hazard
        # the substring match had, moved one place along.
        if got.startswith(prefix) and not got[len(prefix)].isalnum():
            return canon
    return got

#: Set by the CLI; `load()` reads it. A module global rather than a parameter
#: threaded through ~15 call sites, because every one of them wants the same
#: answer and a per-caller override is exactly the freedom that lets two floors
#: in one table come from two instruments.
_INSTRUMENT = INSTRUMENT_DEFAULT


def set_instrument(name):
    """Choose which instrument every floor in this process is computed from."""
    global _INSTRUMENT
    _INSTRUMENT = name


def _instrument_matches(rec):
    """Is this sheet from the instrument under analysis?

    Substring, not equality: the compass records carry a long descriptive string
    ("politicalcompass.org 62-proposition test; texts and per-item research
    classifications ...") whose tail has changed before now. The discriminating
    part is the head, and an exact match on a sentence nobody guards is a filter
    that fails open the next time somebody edits it.

    A record with NO instrument field falls back to its ITEM COUNT, because one
    collector never wrote the field -- see INSTRUMENT_ITEMS. That fallback cannot
    pool the two instruments (60 != 62) and a record matching neither a name nor
    a count is still dropped.
    """
    got = rec.get("instrument")
    if isinstance(got, str):
        return _canonical(got) == _INSTRUMENT

    # NO INSTRUMENT FIELD. The fallback is allowed ONLY for instruments declared to have
    # predated the field, and never for one that has always written it.
    #
    # It was an unconditional item-count match, which is a claim on every record that
    # never named an instrument: any 32-item sheet from any future bank would have been
    # counted into this study's own battery, silently, because 32 == 32. The tree already
    # holds 59 no-instrument records at 62 items from the constrained-decoding arm, which
    # the previous default claimed by exactly this route.
    if _INSTRUMENT not in PREDATES_INSTRUMENT_FIELD:
        return False
    want_items = INSTRUMENT_ITEMS.get(_INSTRUMENT)
    if want_items is None:
        return False
    n = rec.get("n_items") or len(rec.get("answers") or [])
    return n == want_items


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


def load(pattern, condition=None, key=None, dedupe_by_seed=False):
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
    # ONE SEED, ONE SAMPLE -- for the arms where the seed identifies the draw.
    #
    # Wave 0 holds cells with 6 to 10 valid runs across 5 swept seeds, because repairing the
    # seed-restart defect ADDED the missing positions without removing the duplicated ones. A
    # duplicated seed is not a second observation, and left in it gets double weight inside
    # modal() -- which decides every item where the cell is otherwise split.
    #
    # NOT the default, deliberately. `floor_replicate` measures run-to-run variation at a FIXED
    # seed: there every record shares one seed by design, and deduping would delete the floor
    # rather than clean it. The caller knows which kind of arm it is reading.
    seen_seed = set()
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
            # The instrument guard. Counted, never silent: a floor whose pair
            # count moved because another instrument entered the tree must say
            # so in the same breath as the number.
            if not _instrument_matches(r):
                _count_drop("other instrument (%s)" % (r.get("instrument") or "unset"), r)
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
            if dedupe_by_seed and r.get("seed") is not None:
                mark = (key(r), r["seed"])
                if mark in seen_seed:
                    _count_drop("duplicate seed in a swept cell: %s" % (r.get("model"),), r)
                    continue
                seen_seed.add(mark)
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
    # None, not NaN: the modal-sampling-error row is not a pair distribution at all -- it is
    # the estimator's own spread, read from a cache -- so it has no bootstrap interval rather
    # than a failed one. Distinguishing the two matters: "n too small" would claim we tried.
    if lo is None or hi is None:
        return "not a pair arm"
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
    # CLUSTERED BY MODEL, like the paraphrase row. 84 pairs sounds like 84 independent
    # observations and is not: they come from 11 models, six of which contribute ten pairs
    # each, so a flat bootstrap treats one model's ten draws as ten models' worth of evidence
    # and reports an interval narrower than the data supports. The cluster bootstrap was built
    # for exactly this on 2026-09-04 and was wired to one row -- and the two rows the headline
    # comparison rests on, this and same-version, were not among them.
    pairs, clusters = [], []
    # `by` is keyed (model, temperature) since 2026-09-07. The CLUSTER stays the model: two
    # temperatures of one model are not two independent models, and clustering on the full key
    # would hand the bootstrap more clusters than there are models -- the same
    # narrower-than-the-data error the cluster bootstrap was added to fix.
    for (m, _temp), orders in sorted(by.items(), key=lambda kv: str(kv[0])):
        ks = sorted(orders, key=lambda k: (k is not None, k))
        for i in range(len(ks)):
            for j in range(i + 1, len(ks)):
                pairs.append(both_stats(orders[ks[i]], orders[ks[j]]))
                clusters.append(m)
    return summarise("presentation order", pairs,
                     "same model, same condition, same template, same temperature, item order "
                     "only", clusters=clusters)


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

    IT FAILED OPEN A THIRD TIME, ON TEMPERATURE, AND THE PARAGRAPH ABOVE PREDICTED IT.
    2026-09-07: temperature was never in the cell key and never filtered, so **28 of 186
    canonical-order cells pooled temperature-0 and temperature-0.7 runs** and their modal was a
    majority vote across two temperatures. The fix after the paraphrase incident was to filter
    the factor that had just broken it; the next new factor walked straight in.

    What makes this one legible is that the contaminating runs contributed NOTHING. Every
    shuffled-order sheet in this floor is condition A at temperature 0 -- the one-sitting order
    arm is condition D, because A is 28.2% invalid on that panel -- so at temperature 0.7 there
    are no shuffled sheets to pair against, and the temp-0.7 canonical runs from the waves could
    only ever dilute a modal they could not contribute a pair to. Pure contamination, zero
    contribution.

    Measured before and after, so the scale of it is on the record rather than assumed:

        as published (temperature ignored)   84 pairs, median 3, p90 11, max 23
        temperature-matched                  84 pairs, median 3, p90 11, max 24

    Identical pair count, identical median, identical p90. The max moves, which is the
    statistic a diluted modal would be expected to move, and the headline p90 the paper rests on
    is unaffected. Temperature is part of the key now, so a pair shares one temperature by
    construction -- and the general lesson is written into the key's own docstring rather than
    into this one, because the next factor will not be temperature either.
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
            # (model, condition, temperature) is the GROUP; the order is what varies within it.
            # Temperature moved into the group on 2026-09-07 -- see this function's note.
            cells[(key[0], key[1], key[4], key[2])].extend(runs)
            sources[rel.split("/")[0]] += len(runs)
    by = collections.defaultdict(dict)
    for (m, c, temp, o), runs in cells.items():
        if c == "A":
            by[(m, temp)][o] = modal(runs)
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
        for (m, _temp), orders in sorted(by.items(), key=lambda kv: str(kv[0])):
            if served_over_api(m) != want_api:
                continue
            ks = sorted(orders, key=lambda k: (k is not None, k))
            for i in range(len(ks)):
                for j in range(i + 1, len(ks)):
                    pairs.append(both_stats(orders[ks[i]], orders[ks[j]]))
        note = ("2025-26 models served over an API, MOST OF THEM OPEN WEIGHTS -- this axis is "
                "hosted-vs-local, not open-vs-closed"
                if want_api else
                "7-14B open-weight builds of the 2024 generation, run LOCALLY at Q4 -- serving "
                "path, vintage and quantisation all differ from the hosted row, and this "
                "corpus cannot separate them")
        out[label] = summarise(label, pairs, note)
    return out


#: Where the same-version null is measured. The wave dirs, not a single retired collection.
#:
#: THIS ARM READ ONE HARDCODED DIRECTORY -- `runs/2026-08-31-lineage/**` -- which held the
#: retired external instrument and moved to `withdrawn/` on 2026-09-16. The consequence was
#: not a wrong number but NO number: the paper's headline row vanished, `key_numbers` raised
#: `KeyError: 'same-version variants'`, and nine tests went red. Collecting 372 fresh sheets
#: into the wave directory would have changed none of it, because this arm would still have
#: been looking somewhere else. A hostile review caught it before the spend.
#:
#: Condition N, not A. A is the balance instruction and is the arm models REFUSE -- on this
#: battery gemini-3.7-flash declines all four conditions and gemini-3.8-flash declines A and
#: N, so keying the null to A silently drops the refusers from the pair set. N is the
#: pre-registered baseline and is what a same-version comparison should hold fixed.
SAME_VERSION_GLOB = "runs/*-wave/*.jsonl"
SAME_VERSION_CONDITION = "N"


def floor_same_version():
    cells = load(SAME_VERSION_GLOB, SAME_VERSION_CONDITION)
    by = collections.defaultdict(list)
    for (m, c, o), runs in cells.items():
        by[m].extend(runs)
    ids = [m for m, v in by.items() if len(v) >= 2]
    parsed = {i: parse(i) for i in ids}
    pairs = []
    # WHAT KIND OF "same version" each pair actually is, counted rather than listed.
    #
    # The note said "size / mode / snapshot / tier" and left the reader to assume a spread. It
    # is not one: the arm is mostly SIZE and TIER siblings -- gemini-2.5-flash-lite against
    # gemini-2.5-pro is scored here as a same-version null -- while the comparison a DRIFT
    # study actually needs, the same name at a later snapshot, is a small minority of it. An
    # author whose snapshot transition is judged against a size-variant distribution can fairly
    # say so, and this arm is quoted at other people's work throughout section 2.
    kinds = collections.Counter()
    snapshot = []
    # CLUSTERED BY VERSION GROUP. 97 pairs come from 19 groups and `qwen|qwen|3` alone
    # contributes 45, so a flat bootstrap over pairs counts one family's internal spread as
    # nearly half the evidence.
    clusters = []
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            label, is_version = classify(parsed[a], parsed[b])
            if not is_version and label.endswith("(null)"):
                st_ = both_stats(modal(by[a]), modal(by[b]))
                pairs.append(st_)
                # parse() returns a DICT, not an object. Written with getattr() first, which
                # silently yielded "" for every field and collapsed all 97 pairs into ONE
                # cluster -- the bootstrap then returned NaN rather than a wrong number, which
                # is the good failure and is why it was caught immediately.
                pa = parsed[a]
                clusters.append("|".join(str(pa.get(k) or "")
                                         for k in ("vendor", "stem", "version")))
                kind = label.replace("(null)", "").strip() or "unclassified"
                kinds[kind] += 1
                if "snapshot" in kind.lower():
                    snapshot.append(st_)
    note = "same version, by kind: %s" % ", ".join(
        "%s %d" % (k, n) for k, n in sorted(kinds.items(), key=lambda kv: -kv[1]))
    if snapshot:
        s = sorted(x[0] for x in snapshot)
        note += ("; the same-name-later-SNAPSHOT subset -- the null a drift claim actually "
                 "needs -- is n=%d, median %d, p90 %d, max %d, and the rest of this row is "
                 "size and tier siblings"
                 % (len(s), int(st.median(s)),
                    s[int(0.9 * len(s)) - 1] if len(s) >= 10 else max(s), max(s)))
    return summarise("same-version variants", pairs, note, clusters=clusters)


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
    # TWO SOURCES, because the paraphrase arm is a retired collection and the wave is where
    # replicates land now. This read ONLY `runs/2026-09-04-template-floor/**` -- withdrawn on
    # 2026-09-16 -- so replicate sheets collected into the wave directory were invisible to
    # the arm that exists to read them, and the floor under every other floor would have come
    # back empty no matter how many were collected.
    #
    # The wave key is (model, condition, shuffle_seed): a replicate holds the ORDER fixed and
    # varies only the draw. Pairing across shuffle seeds would measure order, which is the
    # neighbouring arm's job and the confound this one exists to separate out.
    cells = dict(_template_cells())
    for key, runs in load(SAME_VERSION_GLOB, None,
                          key=lambda r: (r.get("model"), r.get("condition"),
                                         r.get("shuffle_seed"))).items():
        if len(runs) > 1:
            cells[key] = runs

    pairs, clusters = [], []
    for key, runs in sorted(cells.items(), key=lambda kv: str(kv[0])):
        m = key[0]
        for i in range(len(runs)):
            for j in range(i + 1, len(runs)):
                pairs.append(both_stats(runs[i], runs[j]))
                clusters.append(m)
    return summarise("run-to-run replicate", pairs,
                     "same model, same condition, same item order -- run against run, the "
                     "floor under the floors; interval is a CLUSTER bootstrap over models",
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


def floor_elicitation_format():
    """PROSE vs GRAMMAR: how much does the way you ASK move the answer?

    Every other row here varies something about the model or the prompt's content. This varies
    only how the answer is COLLECTED: the parser arm asks for 62 answers as prose and reads
    them with a regex; the grammar arm sends the identical prompt with a JSON schema pinning
    the output to an array of 62 enum values, so a refusal, a truncation, tokenizer garbage and
    a malformed sheet are all ungenerable rather than produced-and-rejected.

    The prompt is built by the same `run_compass.build_prompt` in both arms and the protocol is
    the wave's in both -- temperature 0.7, five swept seeds from 20260830, template T01. Only
    the decoding differs, which is what makes this a clean contrast rather than two instruments.

    THIS ROW REFUSES TO REPORT A FLOOR, AND THE REFUSAL IS THE MEASUREMENT.
    ---------------------------------------------------------------------
    The across-arm distance is median 23, p90 34 of 62 -- which would make it far the largest
    factor in this table, seven times the deliberate manipulation, and that is what it was
    about to be written up as. It is not a factor. **The grammar arm does not agree with
    ITSELF.**

    Measured over the same 10 cells, five swept seeds each:

        arm         its own run-to-run spread (median across cells)
        prose        3
        grammar     26
        across      24

    The prose arm at temperature 0.7 returns a stable position -- median 3 side-flips between
    two of its own runs, which is inside the replicate floor. The grammar arm's runs disagree
    with each other by 26, as much as they disagree with prose. An instrument whose repeat
    measurements differ by 26 items of 62 is not measuring a position, so the across-arm
    distance is not a comparison between two instruments; it is one instrument against noise.

    A misalignment artifact was ruled out separately: rotating the grammar sheet by +/-1 and
    +/-2 items does not reduce the distance (24 at k=0, 24 at k=+1, 28 at k=+2), so the answers
    are not correctly ordered answers assigned to the wrong items.

    WHAT IT MEANS FOR THE PROPOSAL. Grammar-constrained decoding removes every parse failure
    the release document listed -- 28.2% invalid condition-A runs, budget exhaustion, tokenizer
    garbage -- by making them ungenerable, and it does so at the cost of the measurement
    replicating at all. The plausible mechanism is that free generation lets the model condition
    each answer on the ones it has written, and a bare array of 62 enum values gives it no such
    anchor, so each position is close to an independent sample from a wide posterior. The prose
    arm's stability is doing work that looked like overhead.

    So the row prints the STABILITY numbers rather than a floor, and a caller cannot mistake it
    for a nuisance factor to compare against. Restoring it as a floor requires a grammar arm
    that passes its own replicate test first.
    """
    grammar = load("runs/*-constrained/*.jsonl",
                   key=lambda r: (r["model"], r["condition"]), dedupe_by_seed=True)
    prose = load("runs/*-wave/*.jsonl",
                 key=lambda r: (r["model"], r["condition"]), dedupe_by_seed=True)

    def selfspread(sheets):
        v = sorted(both_stats(sheets[i], sheets[j])[0]
                   for i in range(len(sheets)) for j in range(i + 1, len(sheets)))
        return v[len(v) // 2] if v else None

    across, g_self, p_self, seen = [], [], [], []
    for key in sorted(set(grammar) & set(prose), key=str):
        g, p = grammar[key], prose[key]
        if len(g) < 4 or len(p) < 4:
            continue
        across.append(both_stats(modal(p), modal(g)))
        g_self.append(selfspread(g))
        p_self.append(selfspread(p))
        seen.append("%s/%s" % (key[0].split("/")[-1], key[1]))
    if not across:
        return None

    def med(v):
        v = sorted(x for x in v if x is not None)
        return v[len(v) // 2] if v else None

    gm, pm = med(g_self), med(p_self)
    am = med([a[0] for a in across])

    # THE ARM MUST PASS ITS OWN REPLICATE TEST BEFORE ITS DISTANCE MEANS ANYTHING.
    # A floor row here would be compared against the manipulation and the order floors by
    # every reader of the table, and this arm cannot support that.
    if gm is not None and am is not None and gm >= am * 0.5:
        note = ("NOT A FACTOR -- THE GRAMMAR ARM FAILS ITS OWN REPLICATE TEST. Over %d cell(s), "
                "two grammar runs of the SAME cell differ by a median of %s side-flips against "
                "%s for two prose runs, and the across-arm distance is %s. An arm whose repeat "
                "measurements differ as much as it differs from the other arm is measuring "
                "noise, so the across-arm number is not an elicitation-format effect. "
                "Misalignment ruled out: rotating the sheet by +/-1 or +/-2 items does not "
                "reduce the distance. THE CAUSE IS ITEMS PER CALL, NOT THE GRAMMAR: every run "
                "behind this row asks for all 62 answers in one array, and the arm replicates "
                "once the sheet is asked in chunks -- see "
                "RESULTS-2026-09-07-constrained-decoding-batch-size.md and "
                "`constrained_probe.py --batch-sweep`. So this row disqualifies the "
                "WHOLE-SHEET arm, not constrained decoding, and it stays disqualified until a "
                "batched arm is collected at the wave protocol. Cells: %s"
                % (len(seen), gm, pm, am, ", ".join(sorted(seen)[:6])))
        # THE COLUMNS MEAN WHAT THE HEADER SAYS THEY MEAN.
        #
        # A first version put (prose_self, grammar_self, across) into the med/p90/max slots,
        # so the row read "3 / 26 / 24" under a header saying "side-flip med / p90 / max" --
        # three different quantities wearing the labels of one distribution, and a max smaller
        # than the p90 as the giveaway. That is a worse defect than the one it was trying to
        # disclose. The columns carry the real across-arm distribution; the disqualification
        # lives in the NAME and the note, where a reader cannot mistake it for a floor.
        side = [a[0] for a in across]
        endp = [a[1] for a in across]

        def trip(v):
            v = sorted(v)
            p90 = v[int(0.9 * len(v)) - 1] if len(v) >= 10 else max(v)
            return (v[len(v) // 2], p90, max(v))

        return {"name": "elicitation format -- ARM UNSTABLE, NOT A FLOOR",
                "n": len(across), "side": trip(side), "endpoint": trip(endp),
                "side_ci": (None, None), "note": note,
                "small_n": False, "p90_is_max": False,
                "clustered": False, "n_clusters": None,
                "disqualified": True}

    note = ("the same prompt and the same wave protocol, collected two ways: prose read by the "
            "parser against a JSON schema pinning the four labels. Only the DECODING differs. "
            "Grammar arm's own replicate median %s against prose %s, so the arm is stable "
            "enough for the contrast. %d cell(s): %s"
            % (gm, pm, len(seen), ", ".join(sorted(seen)[:6])))
    return summarise("elicitation format (prose vs grammar)", across, note,
                     clusters=[s.split("/")[0] for s in seen])


def floor_order_local_2026():
    """The one-sitting order floor on a 2026-generation open weight RUN LOCALLY.

    THE TIE-BREAKER FOR THE STUDY'S MOST QUOTABLE SPLIT.
    `floor_order_wave_by_class` shows item order moving p90 3 on hosted models and p90 14 on
    local ones, and §3 reads that as a generational effect -- Rottger et al. predicted in 2024
    that better-aligned newer models would be more stable. **This corpus cannot support that
    reading**, because three properties change together across the split: serving path (someone
    else's API against local Ollama), vintage (2025-26 against 2024), and quantisation
    (provider precision against Q4_K_M). The requantisation floor is p90 6, the same order as
    the gap being explained, so "it is the quantisation" is an equally good story.

    The frozen panel cannot break the tie: its only LOCAL 2026-generation build is
    gemma-4-12B, which returns empty responses. So a 2026 open weight was collected locally at
    Q4 in its own off-panel arm -- same condition D, same two shuffled orders plus canonical,
    same five swept seeds, same temperature.

    HOW TO READ IT. If order sensitivity tracks VINTAGE, this row should sit near the hosted
    row's p90 3. If it tracks quantisation or serving path, it should sit near the local row's
    p90 14. It is one model, so it can refute "vintage explains it" or fail to -- it cannot
    establish the alternative on its own.

    SEPARATE ROW, NOT MERGED. It is a different sitting and an off-panel roster, so folding it
    into `presentation order, one sitting` would change a published row by adding data collected
    to answer a different question. Its directory carries a suffix precisely so the panel arm's
    glob cannot see it.
    """
    cells = collections.defaultdict(list)
    for pattern in ("runs/*-wave-orders-local2026/*.jsonl",):
        for key, runs in load(pattern, key=_default_key, dedupe_by_seed=True).items():
            cells[key].extend(runs)
    by = collections.defaultdict(dict)
    for (m, c, order), runs in sorted(cells.items(), key=lambda kv: str(kv[0])):
        if c == "D" and len(runs) >= 4:
            by[m][order] = modal(runs)

    pairs, clusters = [], []
    for m, orders in sorted(by.items()):
        ks = sorted(orders, key=lambda k: (k is not None, k))
        for i in range(len(ks)):
            for j in range(i + 1, len(ks)):
                pairs.append(both_stats(orders[ks[i]], orders[ks[j]]))
                clusters.append(m)
    if not pairs:
        return None
    note = ("item order only, one sitting, a 2026-generation open weight run LOCALLY at Q4 -- "
            "the tie-breaker for whether the hosted/local order gap is vintage, quantisation "
            "or serving path, which this corpus otherwise cannot separate. %d model(s)"
            % len(by))
    return summarise("presentation order, one sitting, local 2026 open-weight",
                     pairs, note, clusters=clusters)


def floor_ablation_wave():
    """Stock vs ablated at the WAVE PROTOCOL -- n=5, swept seed, one sitting.

    THE ROW BELOW RESTS ON SINGLE RUNS AND THIS ONE DOES NOT, which is the entire reason this
    exists. `floor_ablation` reads the 2026-08-30 pairs, where a cell is one or two runs; that
    is how a 12-item "inversion" reached the paper off n=1 per arm (CORRECTIONS #8). The
    2026-09-07 wave re-collected the same question at five swept seeds per cell.

    BOTH ROWS PRINT. The older arm covers more bases (12 pairs against 3) and the newer one has
    a real modal on each side, so neither supersedes the other and deleting either would be
    choosing which scope to publish after seeing both -- the move this project has withdrawn
    three claims for. The manipulation already appears twice for the same reason.

    Every pair here is arm-matched by construction: the collector runs stock and ablated builds
    of one base through identical parameters in one sitting. What it cannot fix is that the
    ablated builds are third-party, so `ablation_analysis.py` runs the pre-registered ablator-
    agreement step first -- and on the one base with more than one abliteration, the ablator
    spread is as large as the ablation effect on the endpoint statistic.
    """
    per = collections.defaultdict(dict)
    for path in sorted(glob.glob(os.path.join(
            STUDY, "runs/2026-09-07-ablation-wave/*/*/*.jsonl"))):
        parts = path.replace(os.sep, "/").split("/")
        base, arm = parts[-3], parts[-2]
        for cell, runs in load(os.path.relpath(path, STUDY),
                               key=lambda r: (r["model"], r["condition"]),
                               dedupe_by_seed=True).items():
            if len(runs) >= 4:
                per[(base, cell[1])][arm] = modal(runs)

    pairs, clusters = [], []
    for (base, _cond), arms in sorted(per.items()):
        if "stock" not in arms:
            continue
        for arm in sorted(a for a in arms if a.startswith("ablated")):
            pairs.append(both_stats(arms["stock"], arms[arm]))
            clusters.append(base)
    if not pairs:
        return None
    note = ("stock vs ablated at n=5 per cell, swept seed, one sitting -- the same question as "
            "the row above, re-collected because that one rests on single runs. 3 of 6 bases "
            "produced a usable pair; the other three failed for causes named in "
            "RESULTS-2026-09-07-ablation-wave.md, one of them in its STOCK arm")
    return summarise("refusal-direction ablation, one sitting", pairs, note, clusters=clusters)


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


def _condition_pairs(pattern, dedupe_by_seed=False):
    """A→D pairs from one collection, keyed by (model, condition, collection date).

    Extracted from floor_conditions so the wave arm below runs the SAME pairing rather than a
    copy of it. A second implementation of "what is a manipulation pair" is a second definition
    of the paper's reference scale, and the two would drift.

    Returns (pairs, by_model, split_day, raw_cells).
    """
    raw = load(pattern, key=lambda r: (r["model"], r["condition"],
                                       r.get("collected_at", "")[:10]),
               dedupe_by_seed=dedupe_by_seed)
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
    return pairs, by, split_day, raw


def floor_order_wave():
    """PRESENTATION ORDER UNDER THE WAVE PROTOCOL -- the missing half of the comparison.

    §3 of the paper reported its central comparison as unsettled, and named the reason: the
    manipulation row was collected in one sitting at n=5 with a swept seed, while the order row
    pools mixed temperatures and dates and holds ONE run in 23 of its 37 shuffled cells. A
    single draw against a five-run consensus is not a like-for-like comparison, and the size of
    the difference was unmeasured.

    This is that measurement. Same fixed panel, same frozen parameters, same five swept seeds,
    varying ONLY the item order -- two shuffled orders collected 2026-09-06 against the
    canonical order wave 0 already held. Three orders per model, three pairs each.

    CONDITION D, NOT A. The pooled order floor is measured under the balance instruction, which
    is the worst condition on this instrument to measure anything: A is 28.2% invalid on wave 0
    against D's 2.9%, and fourteen panel models decline it outright, so that floor is computed
    on whichever models happen not to refuse. D is what the position series already runs on, and
    it makes the contrast direct -- the manipulation is A->D, and this is what item order alone
    does inside D.
    """
    cells = collections.defaultdict(list)
    for pattern in ("runs/*-wave/*.jsonl", "runs/*-wave-orders/*.jsonl"):
        got = load(pattern, condition="D",
                   key=lambda r: (r["model"], r.get("shuffle_seed")),
                   dedupe_by_seed=True)
        for (m, order), runs in got.items():
            cells[(m, order)].extend(runs)

    by = collections.defaultdict(dict)
    # The canonical order is keyed None and the shuffles are ints, so a plain sort raises.
    # Sorting matters here for the same reason it matters in load(): the read order must be
    # canonical, not the filesystem's.
    for (m, order), runs in sorted(cells.items(),
                                   key=lambda kv: (kv[0][0], kv[0][1] is not None, kv[0][1])):
        by[m][order] = modal(runs)

    pairs, clusters = [], []
    for m, orders in sorted(by.items()):
        ks = sorted(orders, key=lambda k: (k is not None, k))
        for i in range(len(ks)):
            for j in range(i + 1, len(ks)):
                pairs.append(both_stats(orders[ks[i]], orders[ks[j]]))
                clusters.append(m)
    if not pairs:
        return None

    n_models = len({m for m, cs in by.items() if len(cs) > 1})
    thin = sorted(m for m, cs in by.items() if len(cs) < 3)
    note = ("item order only, under the wave protocol -- condition D, temperature 0.7, swept "
            "seed, 5 runs per cell, modal against modal on BOTH sides. %d model(s) contribute; "
            "%d hold fewer than all three orders" % (n_models, len(thin)))
    if thin:
        note += (" (%s -- local builds whose runs exhausted their token budget or returned "
                 "nothing parseable, asked and not re-queued)"
                 % ", ".join(t.split("/")[-1] for t in thin[:4]))
    return summarise("presentation order, one sitting", pairs, note, clusters=clusters)


def floor_modal_noise():
    """THE FLOOR UNDER THE FLOORS: the sampling error of the modal sheet itself.

    Every row above pairs two MODAL answer sheets, and a modal is a statistic -- draw five more
    runs from the same cell and it moves. Nothing measured how much until 2026-09-06, which
    means no row in this table had a denominator: an effect of p90 7 against an estimator that
    wobbles p90 6 is the estimator.

    Measured by bootstrap in `scripts/floor_resolution.py`: resample a cell's runs with
    replacement twice, take the modal of each, count the side-flips between two modals of the
    SAME cell under the SAME condition. Everything that differs differs because the modal
    moved. Cached to `data/modal-noise.json` because it is 2000 resamples across 110 cells and
    `all_floors()` is read by four gates and the chart.

    It comes out at median 1, p90 3 -- small enough that the frontier effects clear it, and
    NOT small enough to ignore: presentation order on frontier models is p90 3 under the wave
    protocol, which is exactly this number. That row is not measuring item order. It is
    measuring the modal.

    Ten cells are worse than the pooled figure suggests, with modal p90 >= 7 -- deepseek-v4-
    flash under P reaches 27. Those are the bimodal models, and no modal-based measurement of
    them means anything; they are named in the cache.
    """
    import json as _json
    path = os.path.join(STUDY, "data", "modal-noise.json")
    if not os.path.exists(path):
        return None
    try:
        rec = _json.load(io.open(path, encoding="utf-8"))
    except ValueError:
        return None
    med, p90v, mx = rec.get("median"), rec.get("p90"), rec.get("max")
    if med is None or p90v is None:
        return None

    # A CACHED FLOOR MUST NAME THE INSTRUMENT IT WAS MEASURED ON.
    #
    # This row is read from `data/modal-noise.json` rather than recomputed, because it is
    # 2000 resamples over 110 cells and four gates read it. That is a good reason to cache
    # and no reason at all to trust the cache across an instrument change -- and on
    # 2026-09-16 it did exactly that: the study's instrument moved, every other row went
    # empty for want of data, and this one kept printing a median and a p90 measured on the
    # retired questionnaire. The denominator under every floor in the table, stale, and
    # silent about it.
    #
    # The cache had a `signature` of cell and run counts and no instrument field at all, so
    # nothing could have caught it. An unnamed provenance is not provenance.
    cached_on = rec.get("instrument")
    if cached_on is None or _canonical(cached_on) != _INSTRUMENT:
        _count_drop("modal-noise cache measured on %s, not %s"
                    % (cached_on or "an unrecorded instrument", _INSTRUMENT), rec)
        return None
    # THE ENDPOINT FLOOR IS ITS OWN NUMBER. This row printed the side-flip triple in both
    # columns, which understated the endpoint estimator by nearly a factor of three -- p90 3
    # against a measured 8 -- and the ablation arm's first result is an endpoint effect. A
    # denominator copied from the wrong statistic is worse than no denominator.
    e_med = rec.get("endpoint_median", med)
    e_p90 = rec.get("endpoint_p90", p90v)
    e_max = rec.get("endpoint_max", mx)
    unstable = rec.get("unstable") or []
    note = ("NOT A FACTOR -- the estimator. Side-flips between two bootstrap modals of the "
            "SAME cell, %d resamples over %d cell(s). Every modal-vs-modal row above is "
            "measured with this much slack before any factor acts. %d cell(s) are far worse "
            "individually (modal p90 >= 7): %s"
            % (rec.get("boot", 0), rec.get("cells", 0), len(unstable),
               ", ".join(u.split("/")[-1] for u in unstable[:4])))
    return {"name": "modal sampling error", "n": rec.get("cells", 0),
            "side": (med, p90v, mx), "endpoint": (e_med, e_p90, e_max),
            "side_ci": (None, None), "note": note,
            "small_n": False, "p90_is_max": False,
            "clustered": False, "n_clusters": None}


def floor_order_wave_by_class():
    """The one-sitting order floor SPLIT BY MODEL CLASS, because pooling it inverts the result.

    §2 already establishes that the pooled order row is a net aggregate concealing two
    populations -- 2024-generation open-weight models move far more than 2026 frontier APIs --
    and calls that the most important line in the paper. The comparison against the
    manipulation then pooled it anyway.

    Split, on the 24 models measured in BOTH arms:

        frontier API (n=20)        order median 1, p90 3   manipulation median 2.5, p90 5
        local open-weight (n=4)    order median 11, p90 12  manipulation median 4,   p90 8

    The two classes order the two factors OPPOSITELY, so the pooled p90 comparison answers
    neither question. On frontier models the manipulation is the larger effect and item order
    sits at the modal's own sampling error; on 2024-generation local builds item order is far
    larger. Both are in `RESULTS-2026-09-06-order-floor-one-sitting.md`.
    """
    cells = collections.defaultdict(list)
    for pattern in ("runs/*-wave/*.jsonl", "runs/*-wave-orders/*.jsonl"):
        got = load(pattern, condition="D",
                   key=lambda r: (r["model"], r.get("shuffle_seed")), dedupe_by_seed=True)
        for k, runs in got.items():
            cells[k].extend(runs)
    by = collections.defaultdict(dict)
    for (m, order), runs in sorted(cells.items(),
                                   key=lambda kv: (kv[0][0], kv[0][1] is not None, kv[0][1])):
        by[m][order] = modal(runs)

    out = {}
    for label, want_api in (("presentation order, one sitting, local open-weight", False),
                            ("presentation order, one sitting, frontier API", True)):
        pairs, clusters = [], []
        for m, orders in sorted(by.items()):
            if served_over_api(m) != want_api:
                continue
            ks = sorted(orders, key=lambda k: (k is not None, k))
            for i in range(len(ks)):
                for j in range(i + 1, len(ks)):
                    pairs.append(both_stats(orders[ks[i]], orders[ks[j]]))
                    clusters.append(m)
        if pairs:
            note = ("item order only, one sitting, %s"
                    % ("2025-26 models served over an API, most of them open weights -- at or "
                       "under the modal's own sampling error (p90 3), so this row is close to "
                       "unmeasurable"
                       if want_api else
                       "7-14B open-weight builds of the 2024 generation, run LOCALLY at Q4 -- "
                       "serving path, vintage and quantisation all differ from the hosted row, "
                       "and this corpus cannot separate them"))
            out[label] = summarise(label, pairs, note, clusters=clusters)
    return out


def floor_conditions_wave_by_class():
    """The one-sitting MANIPULATION split by model class -- the other half of the comparison.

    `floor_order_wave_by_class` splits the nuisance factor and shows it inverting between
    populations: item order is p90 3 on 2026 frontier APIs and p90 14 on 2024-generation open
    weights. The README then compared each of those against a POOLED manipulation of p90 7, and
    a pooled number cannot support a claim about which factor is larger *on a class* -- it is
    the same pooling error the order row was split to escape, one column over.

    Worse, it was briefly published as a two-by-two table with a per-class manipulation figure
    that NOTHING IN THIS FILE COMPUTED. The frontier cell held the pooled 7 and the local cell
    held an 8 copied out of a sibling docstring, which had measured it on a different subset (the
    24 models present in both arms, not the models in this row). A table is a claim that the
    four cells are commensurable; those four were not.

    So this measures it. Same cells, same protocol, same modal-vs-modal units as the order
    split, cut on the same test -- `"/" in model` marks a hosted frontier model, a bare name
    marks a local build.

    Both classes are reported even when a class is thin, because "n=4" is a fact about the
    estimate and dropping the row would leave the pooled figure standing unqualified.
    """
    _pairs, by, _split_day, _raw = _condition_pairs("runs/*-wave/*.jsonl", dedupe_by_seed=True)
    if not by:
        return None
    out = {}
    for label, want_api in (("prompt condition A->D, one sitting, local open-weight", False),
                            ("prompt condition A->D, one sitting, frontier API", True)):
        pairs, clusters = [], []
        for m, cs in sorted(by.items()):
            if served_over_api(m) != want_api:
                continue
            if "A" in cs and "D" in cs:
                pairs.append(both_stats(cs["A"], cs["D"]))
                clusters.append(m)
        if pairs:
            note = ("the balance instruction against the commitment instruction, one sitting, "
                    "%s" % ("2025-26 models served over an API, most of them open weights -- "
                            "this axis is hosted-vs-local, not open-vs-closed"
                            if want_api else
                            "7-14B open-weight builds of the 2024 generation, run LOCALLY at "
                            "Q4 -- serving path, vintage and quantisation all differ from the "
                            "hosted row, and this corpus cannot separate them"))
            out[label] = summarise(label, pairs, note, clusters=clusters)
    return out


def _split_refusals(models, pattern="runs/*-wave/*.jsonl", condition="A"):
    # THE WAVE DIRS, NOT ONE RETIRED COLLECTION. This defaulted to `runs/2026-09-05-wave/`,
    # which held the external instrument and moved to `withdrawn/` on 2026-09-16 -- so the
    # published refusal count printed ZERO while gemini-3.7-flash was refusing 12 of 12 on
    # the battery and gemini-3.8-flash was refusing both A and N. `key_numbers` publishes
    # this figure, so the paper's refusal sentence would have read "0 panel models decline".
    """Of the models with no usable sheet, which actually REFUSED and which failed otherwise.

    A model that declines the balance instruction and a model that runs out of tokens on it
    both leave an empty cell, and the difference is the entire finding. Returns
    (refused, [(model, reason), ...]).
    """
    seen = collections.defaultdict(collections.Counter)
    for p in sorted(glob.glob(os.path.join(STUDY, pattern))):
        for line in io.open(p, encoding="utf-8"):
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("condition") != condition or r.get("model") not in set(models):
                continue
            if r.get("valid"):
                seen[r["model"]]["valid"] += 1
            else:
                seen[r["model"]][r.get("failure_mode") or "unclassified"] += 1
    refused, other = [], []
    for m in models:
        modes = seen.get(m, collections.Counter())
        top = modes.most_common(1)[0][0] if modes else "no runs"
        if top == "refused":
            refused.append(m)
        else:
            other.append((m, top))
    return refused, other


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
    pairs, by, split_day, raw = _condition_pairs("runs/*-wave/*.jsonl", dedupe_by_seed=True)
    if not pairs:
        return None
    sides = sorted(s for s, _e in pairs)
    tail = sorted(((m, both_stats(cs["A"], cs["D"])[0]) for m, cs in by.items()
                   if "A" in cs and "D" in cs), key=lambda t: -t[1])
    # NO PAIR is not the same as REFUSED, and calling it that overstated the refusal finding by
    # one model. This read `"D" in cs and "A" not in cs`, which is "the A cell yielded no usable
    # sheet" -- true of a refusal AND of a model that ran out of tokens. The gemma-4-12B GGUF
    # build has 5 A runs, 0 refused, 5 `budget-exhausted`; it was being counted and printed as a
    # sixth refuser on the public page. Same defect class as the two found this morning: the
    # label claims one quantity and the code computes a broader one.
    no_pair = sorted(m for m, cs in by.items() if "D" in cs and "A" not in cs)
    refused, unusable = _split_refusals(no_pair)
    note = ("the same manipulation under ONE protocol in ONE sitting -- temperature 0.7, swept "
            "seed, 5 runs, wave 0. %d of %d models move 8 items or fewer. The tail is %s. "
            "%d panel model(s) contribute no pair because they refuse condition A outright: %s"
            % (sum(1 for s in sides if s <= 8), len(sides),
               ", ".join("%s %d" % (m.split("/")[-1], v) for m, v in tail[:3]),
               len(refused), ", ".join(m.split("/")[-1] for m in refused)))
    if unusable:
        note += ("; %d further model(s) yield no A sheet for other reasons: %s"
                 % (len(unusable), ", ".join("%s (%s)" % (m.split("/")[-1], why)
                                             for m, why in unusable)))
    if split_day:
        note += ("; %d pair(s) span more than one date: %s"
                 % (len(split_day), ", ".join(m.split("/")[-1] for m in split_day)))
    # DISCLOSE THE SAMPLE BEHIND EACH MODAL. "n=5 per cell" is the protocol, not the outcome:
    # a run that refuses or exhausts its budget is not a sample, so some cells resolve on two
    # sheets. A row that says "one sitting, five runs" while resting on a two-run modal is
    # describing its intent rather than its data.
    runs_behind = []
    for m, cs in sorted(by.items()):
        if "A" not in cs or "D" not in cs:
            continue
        sizes = [len(v) for (mm, c, _d), v in raw.items() if mm == m and c in ("A", "D")]
        if sizes:
            runs_behind.append(min(sizes))
    runs_behind.sort()
    if runs_behind:
        note += ("; runs behind each modal: min %d, median %d (protocol asks 5 -- refusals and "
                 "budget-exhausted runs are not samples)"
                 % (runs_behind[0], int(st.median(runs_behind))))

    paired = [m for m, cs in sorted(by.items()) if "A" in cs and "D" in cs]
    rec = summarise("prompt condition A->D, one sitting", pairs, note, clusters=paired)
    # Which models actually contributed, so a consumer can ask "and the ones that did not?"
    # without re-deriving the pairing and getting a different answer.
    rec["paired_models"] = paired
    rec["refused_models"] = refused
    rec["unusable_models"] = unusable
    return rec


#: EVERY FLOOR, in one place. This list lived here AND in `key_numbers.floors()`, so adding
#: `floor_conditions_wave` to the table left the gate blind to it -- a new row could appear in
#: the paper with nothing recomputing the sentences around it, which is the one thing that gate
#: exists to prevent. One list, two readers.
ALL_FLOORS = (floor_order, floor_same_version, floor_template, floor_replicate,
              floor_quant, floor_ablation, floor_conditions, floor_conditions_wave,
              floor_order_wave, floor_order_wave_by_class, floor_modal_noise,
              floor_conditions_wave_by_class, floor_ablation_wave, floor_order_local_2026,
              floor_elicitation_format)


def all_floors():
    """Every floor that measured something, keyed by name.

    A floor function may return one record or a DICT of them -- `floor_order_by_class` and
    `floor_order_wave_by_class` each yield two rows, because a factor whose effect inverts
    between populations is two measurements wearing one name.
    """
    out = {}
    for fn in ALL_FLOORS:
        r = fn()
        if not r:
            continue
        if isinstance(r, dict) and "name" not in r:
            for rec in r.values():
                if rec:
                    out[rec["name"]] = rec
        else:
            out[r["name"]] = r
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--markdown", action="store_true")
    ap.add_argument("--instrument", default=INSTRUMENT_DEFAULT,
                    help="which instrument every floor is computed from, matched as a "
                         "substring of the record's `instrument` field. Default %s. "
                         "Use %s for the project's own mirrored bank. Floors from two "
                         "instruments are never pooled." % (COMPASS_INSTRUMENT, I3_INSTRUMENT))
    ap.add_argument("--class-split", action="store_true",
                    help="the 2x2 of nuisance-vs-manipulation by model class, as markdown")
    args = ap.parse_args(argv)
    set_instrument(args.instrument)

    rows = list(all_floors().values())
    rows.sort(key=lambda r: -r["side"][1])

    if args.class_split:
        # GENERATED, because a hand-typed version of this table was published on 2026-09-07
        # with a pooled figure in one cell and a foreign-subset figure in another. Its four
        # cells are the whole argument that the two factors invert between populations, so
        # they have to be four rows of the same computation. The phrase gate cannot protect a
        # markdown row -- a template pinning one number silently asserts the rest -- so the
        # table is emitted rather than checked.
        f = all_floors()
        # THE AXIS IS HOSTED-VS-LOCAL. IT IS NOT OPEN-VS-CLOSED AND IT IS NOT OLD-VS-NEW.
        #
        # The split test is `served_over_api()`, which reads each run's own `channel` field. It
        # was `"/" in model` until 2026-09-07 -- and a local Ollama build pulled from Hugging
        # Face is tagged `hf.co/vendor/Model:Q4_K_M`, so the slash test would have put a local
        # model in the hosted row. This table was first published with the two sides headed
        # "2026 frontier API" and "2024-generation open-weight", which asserts two axes the
        # code does not test and gets one of them backwards: 12 of the 20 models on the API side
        # ARE open weights -- DeepSeek V4, Qwen3.8-Max, GLM-5.x, Kimi K2.5/K2.6/K3, Mistral
        # Medium -- all 2025-26 releases. "Open-weight" is not the property that distinguishes
        # the two sides. Being hosted is.
        #
        # Vintage and quantisation ride along with it: the local side is five 2024-generation
        # 7-14B builds at Q4, the hosted side is 2025-26 models at whatever precision the
        # provider serves. So the difference between the rows cannot be attributed to any one
        # of serving path, vintage or quantisation -- they move together in this corpus. The
        # count below is computed rather than typed so the header cannot drift from the roster.
        _p, by, _sd, _raw = _condition_pairs("runs/*-wave/*.jsonl", dedupe_by_seed=True)
        paired = [m for m, cs in by.items() if "A" in cs and "D" in cs]
        hosted = [m for m in paired if "/" in m]
        open_hosted = [m for m in hosted if m.split("/")[0] in OPEN_WEIGHT_VENDORS]
        cells = [
            ("hosted over an API — 2025-26, %d of %d open-weight"
             % (len(open_hosted), len(hosted)),
             "presentation order, one sitting, frontier API",
             "prompt condition A->D, one sitting, frontier API"),
            ("run locally at Q4 — 2024-generation 7-14B",
             "presentation order, one sitting, local open-weight",
             "prompt condition A->D, one sitting, local open-weight"),
        ]
        print("| on this class | presentation order, one sitting | manipulation A->D, one sitting |")
        print("|---|---:|---:|")
        for label, ord_row, man_row in cells:
            def cell(name):
                r = f.get(name)
                if not r:
                    return "not computable here"
                return "p90 **%d** (%d pairs)" % (r["side"][1], r["n"])
            print("| %s | %s | %s |" % (label, cell(ord_row), cell(man_row)))
        return 0

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
        # A DISQUALIFIED ROW MUST CARRY ITS REASON INTO THE MARKDOWN.
        #
        # `note` was printed only in the text output, so a row named "ARM UNSTABLE, NOT A
        # FLOOR" would reach a document as bare numbers under a scary label with no
        # explanation -- and the numbers are the largest in the table, which is exactly the
        # combination a reader quotes. If a row is not a floor, the table has to say why where
        # the table is read.
        for r in rows:
            if r.get("disqualified") and r.get("note"):
                print()
                print("**%s:** %s" % (r["name"], r["note"]))
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
