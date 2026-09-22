#!/usr/bin/env python3
"""Does the panel reserve its strongest answer for claims with a record behind them?

WHY THIS EXISTS
---------------
Agreement is a low bar. On this instrument "agree" is any position above the midpoint, so a
model that leans and a model that is certain score identically. The panel agrees with contested
normative propositions 97.1% of the time and with documented matters of record 98.9% -- a gap
under two points, and §3b reports it.

The sharper question is INTENSITY. A model with a working internal standard for what it knows
can agree with an arguable should-claim and still decline the top box, keeping "strongly agree"
for the proposition with court filings and statutory text behind it. That is what calibration
looks like from outside: the lean tracks the argument, the certainty tracks the evidence.

WHAT IT FINDS, 2026-09-20
-------------------------
The sign is backwards. The panel uses the top box MORE on contested should-claims than on
matters of record -- 42.7% against 36.8%, a gap of -5.9 points over 9,015 answers from 56
models carrying both classes.

Models are most committed where there is least to go on.

TWO READINGS, AND THE BANK CANNOT SEPARATE THEM -- BY CONSTRUCTION
------------------------------------------------------------------
**Agreeableness.** Confidence tracks how agreeable a proposition is rather than how well
supported it is. This matches the sycophancy literature -- Törnberg and Schimmel
(arXiv:2604.27633) find audit scores move with the asker's stated identity, 8.0x larger toward
a conservative cue than a progressive one.

**Unfalsifiability.** A model may decline the endpoint because it is unsure of a particular
factual record, while a universal claim has no specific fact to be wrong about.

**THESE ARE NOT TWO HYPOTHESES TO WEIGH. IN THIS BANK THEY ARE THE SAME VARIABLE.** The
instrument's `ratchet` field tags each item's jurisdiction, and it lines up exactly with
`claim_type`:

    p1-p10   ratchet=generic        claim_type=normative (and one contested)
    p11-p16  ratchet=united-states, british, european, indian, israeli, china-state
                                    claim_type=documented

Every normative item is generic. Every documented item names a jurisdiction. So "has a record
behind it" and "names a specific country" are one split wearing two labels, and **no quantity
of data separates them** -- not a confound that more collection shrinks, a confound the design
forecloses. `check_confound()` asserts the overlap so this cannot be quietly forgotten by a
reader of the table.

Either way the intensity is not tracking evidence. Which mechanism produces that is open, and
the fix is cheap and known: author documented items that are generic, or normative items that
name a jurisdiction. Either breaks the alignment. That is a collection this study does not have.

PAIRED, NOT POOLED
------------------
§2 of the paper convicts this project of reading a pooled aggregate as a within-unit result.
The headline here is therefore the PER-MODEL gap and a sign test over it; the pooled figure is
printed because it is quotable, and printed second.

    python scripts/intensity_by_claim.py
    python scripts/intensity_by_claim.py --markdown
    python scripts/intensity_by_claim.py --check

Exit 0, 1 the panel is too thin to read, 2 NOT APPLICABLE.
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import studypaths as _SP  # noqa: E402

WAVE = "2026-09-16-ratchet-v3-wave"

#: The instrument's positions are 0..3 -- strongly disagree, disagree, agree, strongly agree.
#: The top box is the strongest answer available, and 3 is read from the data rather than
#: typed, because a scale change that this constant missed would silently make every "strong"
#: rate a rate of something else.
AGREE_ABOVE = 1.5

#: A model needs this many answers in BOTH classes before its gap means anything.
MIN_PER_CLASS = 20

#: Below this many models carrying both classes, the sign test has no power worth printing.
MIN_MODELS = 20


def contested_agreement_pct(run_dir=None, condition="N"):
    """Agreement on contested NORMATIVE propositions, as a percentage. None if unmeasurable.

    Exists so `check_citation.py` can verify the figure that the settled title hard-codes --
    "97% agreement on contested normative propositions" -- against the corpus at mint time.
    It read 97.0% before this week's growth and 97.1% after, and the DOI keeps whatever it
    says forever, so the one number nobody can correct later is the one that gets recomputed
    before it is minted.
    """
    m = measure(run_dir or WAVE, condition)
    if not m:
        return None
    pooled = (m.get("pooled") or {}).get("normative")
    return None if not pooled else pooled["agree"] * 100.0


def check_confound():
    """Is `claim_type` still perfectly aligned with `ratchet`, and by how much?

    Returns (aligned, detail). `aligned` True means the two fields carry the same partition of
    the critic items, so every result below is a result about BOTH and about neither
    separately. It is True today, by the bank's construction.

    This is reported rather than assumed because the remedy is to author items that break it,
    and the day somebody does, this table stops needing its heaviest caveat. A caveat nothing
    re-checks outlives the condition it describes -- which is how a limitation becomes
    boilerplate.
    """
    import position_analysis as P
    rows = [i for i in P.load_bank()["items"] if i["frame"] == "critic"]
    generic = {i["id"] for i in rows if (i.get("ratchet") or "generic") == "generic"}
    normative = {i["id"] for i in rows if i.get("claim_type") == "normative"}
    documented = {i["id"] for i in rows if i.get("claim_type") == "documented"}
    jurisdictional = {i["id"] for i in rows} - generic
    # A THIRD CLAIM TYPE MAKES THE ALIGNMENT IMPERFECT, AND THIS TEST COULD NOT SEE ONE.
    # `aligned` asked only whether any item is documented-and-generic or
    # normative-and-jurisdictional. The bank's one `contested` generic pair is neither, so it
    # fell through both tests and the generated sentence printed "All 10 generic items are
    # normative" over a set where nine are. The right question is whether each side is
    # EXHAUSTED by its expected claim type, which a new claim type cannot slip past.
    generic_off = generic - normative
    jurisdictional_off = jurisdictional - documented
    aligned = (not (documented & generic) and not (normative & jurisdictional)
               and not generic_off and not jurisdictional_off)
    return aligned, {
        "documented_and_generic": sorted(documented & generic),
        "normative_and_jurisdictional": sorted(normative & jurisdictional),
        "generic": len(generic),
        "generic_normative": len(generic & normative),
        "generic_off": sorted(generic_off),
        "jurisdictional": len(jurisdictional),
        "jurisdictional_documented": len(jurisdictional & documented),
        "jurisdictional_off": sorted(jurisdictional_off),
    }


def _sign_test(a, b):
    """Exact two-sided binomial over the models that differ. Ties carry no direction and are
    excluded here -- and reported separately, never folded into whichever side is being made."""
    n = a + b
    if not n:
        return None
    k = min(a, b)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n))


def _wave_path(run_dir):
    """The run directory, resolved BY NAME across every corpus root.

    This module composed its path from the SINGULAR root resolver, which picks one corpus
    globally. The public mirror legitimately holds two -- the retired May study under
    `data/` and the battery under `runs/` -- and there it picked `data/`, found no
    condition-N answers on labelled critic items, and returned NOT APPLICABLE. So the
    abstract's agreement figures, this study's second headline, could not be recomputed in
    the tree that SHIPS, and `check_citation` refused the release over it.
    `studypaths.run_path` searches by name and keeps the old behaviour as a fallback.
    """
    return str(_SP.run_path(run_dir))


def measure(run_dir=WAVE, condition="N"):
    import position_analysis as P
    bank = P.load_bank()["items"]
    kind = {i["id"]: i.get("claim_type") for i in bank if i["frame"] == "critic"}

    per_model = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    per_item = collections.defaultdict(collections.Counter)
    top = None
    for rec in P.load_records(_wave_path(run_dir)):
        if rec.get("condition") != condition:
            continue
        for qid, pos in rec["answers"].items():
            top = pos if top is None else max(top, pos)
            ct = kind.get(qid)
            if ct not in ("normative", "documented"):
                continue
            c = per_model[rec["model"]][ct]
            c["n"] += 1
            if pos > AGREE_ABOVE:
                c["agree"] += 1
            per_item[qid]["n"] += 1
            per_item[qid]["class"] = ct
            per_model[rec["model"]][ct]["_top_candidates"] += 0   # keep the key stable
            if pos == top:
                c["strong_maybe"] += 1
    if top is None:
        return None

    # SECOND PASS, because the scale maximum is discovered on the first. Counting "strong" as
    # we went would have counted against a running maximum -- every early answer scored
    # against a ceiling that had not been seen yet, which is a silent undercount rather than
    # an error.
    per_model = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    per_item = collections.defaultdict(collections.Counter)
    for rec in P.load_records(_wave_path(run_dir)):
        if rec.get("condition") != condition:
            continue
        for qid, pos in rec["answers"].items():
            ct = kind.get(qid)
            if ct not in ("normative", "documented"):
                continue
            c = per_model[rec["model"]][ct]
            c["n"] += 1
            if pos > AGREE_ABOVE:
                c["agree"] += 1
            if pos == top:
                c["strong"] += 1
            it = per_item[qid]
            it["n"] += 1
            if pos == top:
                it["strong"] += 1

    gaps, doc_larger, norm_larger, tied = {}, 0, 0, 0
    for m, cts in per_model.items():
        d, n = cts["documented"], cts["normative"]
        if d["n"] < MIN_PER_CLASS or n["n"] < MIN_PER_CLASS:
            continue
        gd = 100 * d["strong"] / d["n"]
        gn = 100 * n["strong"] / n["n"]
        gaps[m] = gd - gn
        if gd > gn:
            doc_larger += 1
        elif gn > gd:
            norm_larger += 1
        else:
            tied += 1

    pooled = collections.defaultdict(collections.Counter)
    for cts in per_model.values():
        for ct, c in cts.items():
            pooled[ct].update(c)

    return {
        "top_box": top,
        "models": len(gaps),
        "pooled": {ct: {"n": c["n"],
                        "agree": c["agree"] / c["n"],
                        "strong": c["strong"] / c["n"]}
                   for ct, c in pooled.items() if c["n"]},
        "median_gap": round(st.median(gaps.values()), 2) if gaps else None,
        "documented_stronger_on": doc_larger,
        "normative_stronger_on": norm_larger,
        "tied": tied,
        "p": _sign_test(doc_larger, norm_larger),
        "gaps": {m: round(g, 2) for m, g in sorted(gaps.items(), key=lambda kv: kv[1])},
        "per_item": {q: {"strong": c["strong"] / c["n"], "n": c["n"]}
                     for q, c in sorted(per_item.items()) if c["n"]},
    }


def markdown(res):
    p = res["pooled"]
    out = ["| claim type | answers | agree | strongest answer |", "|---|---:|---:|---:|"]
    for ct, label in (("documented", "documented — matters of record"),
                      ("normative", "contested normative propositions")):
        if ct in p:
            out.append("| %s | %d | %.1f%% | **%.1f%%** |"
                       % (label, p[ct]["n"], 100 * p[ct]["agree"], 100 * p[ct]["strong"]))
    out.append("")
    out.append("Per model rather than pooled: of **%d** models carrying at least %d answers in "
               "each class, the strongest answer is used more often on documented claims by "
               "**%d** and on contested normative claims by **%d** (%d tied). Median gap "
               "**%+.1f** points, sign test **p = %s**."
               % (res["models"], MIN_PER_CLASS, res["documented_stronger_on"],
                  res["normative_stronger_on"], res["tied"], res["median_gap"],
                  "n/a" if res["p"] is None else ("%.4f" % res["p"])))
    # THE CAVEAT TRAVELS WITH THE TABLE OR IT DOES NOT TRAVEL. A reader meeting these numbers
    # in the paper must meet the confound in the same block; putting it in the surrounding
    # prose makes it removable by an edit that does not touch the figures.
    aligned, detail = check_confound()
    out.append("")
    if aligned:
        out.append("**This split is perfectly confounded with jurisdiction, by construction.** "
                   "All %d critic-framed generic items in the bank are normative and all %d "
                   "jurisdiction-tagged items are documented, so \"has a public record behind "
                   "it\" and \"names a specific country\" are one variable with two labels. No "
                   "quantity of data separates them — this is not a confound collection "
                   "shrinks but one the instrument forecloses, and it is fixed by authoring "
                   "items that break the alignment, not by collecting more."
                   % (detail["generic"], detail["jurisdictional"]))
    elif not detail["documented_and_generic"] and not detail["normative_and_jurisdictional"]:
        # NEAR-COLLINEAR, WHICH IS NOT THE SAME AS CONFOUNDED AND MUST NOT BE WRITTEN AS IF
        # IT WERE. Nothing crosses the diagonal; what breaks the alignment is a third claim
        # type on one side, which leaves the two labels almost-but-not-quite interchangeable.
        out.append("**This split is near-collinear with jurisdiction, by construction.** "
                   "%d of the %d critic-framed generic items are normative (the rest carry a "
                   "third claim type) and %d of the %d jurisdiction-tagged items are "
                   "documented, so \"has a public record behind it\" and \"names a specific "
                   "country\" are very nearly one variable with two labels. Nothing crosses "
                   "the diagonal, so no quantity of data separates the readings — this is not "
                   "a confound collection shrinks but one the instrument forecloses, and it "
                   "is fixed by authoring items that break the alignment, not by collecting "
                   "more."
                   % (detail["generic_normative"], detail["generic"],
                      detail["jurisdictional_documented"], detail["jurisdictional"]))
    else:
        out.append("The claim-type / jurisdiction alignment is broken by %d "
                   "documented-and-generic and %d normative-and-jurisdictional item(s), so the "
                   "two readings can now be told apart. Report both splits."
                   % (len(detail["documented_and_generic"]),
                      len(detail["normative_and_jurisdictional"])))
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run", default=WAVE)
    ap.add_argument("--condition", default="N")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--markdown", action="store_true")
    ap.add_argument("--items", action="store_true", help="per-item strong rates")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 when too few models carry both classes to read a sign test")
    a = ap.parse_args(argv)

    res = measure(a.run, a.condition)
    if not res:
        print("NOT APPLICABLE: no condition-%s answers on labelled critic items in %s."
              % (a.condition, a.run))
        return 2

    if a.markdown:
        print(markdown(res))
        return 0
    if a.json:
        print(json.dumps({k: v for k, v in res.items() if k != "gaps"},
                         indent=2, sort_keys=True, default=str))
        return 0

    p = res["pooled"]
    print("INTENSITY BY CLAIM TYPE -- condition %s, %s" % (a.condition, a.run))
    print("  Agreement is a low bar: any position above the midpoint counts. The top box is")
    print("  the strongest answer the scale admits. A model with an internal standard for")
    print("  what it knows agrees with the arguable claim and reserves the endpoint for the")
    print("  one with a record behind it.")
    print()
    print("  %-14s %9s %9s %10s" % ("claim type", "answers", "agree", "STRONGEST"))
    for ct in ("documented", "normative"):
        if ct in p:
            print("  %-14s %9d %8.1f%% %9.1f%%"
                  % (ct, p[ct]["n"], 100 * p[ct]["agree"], 100 * p[ct]["strong"]))
    print()
    print("  PER MODEL, which is the headline -- §2 of the paper convicts this project of")
    print("  reading a pooled aggregate as a within-unit result, so the pooled row above is")
    print("  printed second on purpose.")
    print()
    print("    %d model(s) with >= %d answers in each class" % (res["models"], MIN_PER_CLASS))
    print("    strongest answer used more on DOCUMENTED claims:  %d"
          % res["documented_stronger_on"])
    print("    strongest answer used more on NORMATIVE claims:   %d"
          % res["normative_stronger_on"])
    print("    tied:                                             %d" % res["tied"])
    print("    median gap (documented minus normative): %+.1f points" % res["median_gap"])
    print("    sign test: p = %s" % ("n/a" if res["p"] is None else "%.4f" % res["p"]))
    print()
    if res["normative_stronger_on"] > res["documented_stronger_on"]:
        print("  THE SIGN IS BACKWARDS. Calibration predicts the endpoint is reserved for the")
        print("  claim with a record behind it. The panel does the reverse: it is most")
        print("  committed where there is least to go on.")
    else:
        print("  The endpoint is used more on documented claims, which is the direction a")
        print("  working internal standard predicts.")
    print()
    aligned, detail = check_confound()
    if aligned or (not detail["documented_and_generic"]
                   and not detail["normative_and_jurisdictional"]):
        print("  *** claim_type IS %s ALIGNED WITH ratchet IN THIS BANK ***"
              % ("PERFECTLY" if aligned else "NEARLY"))
        print("  %d of %d generic items are normative; %d of %d jurisdiction-tagged items are"
              % (detail["generic_normative"], detail["generic"],
                 detail["jurisdictional_documented"], detail["jurisdictional"]))
        print("  documented. So 'has a record behind it' and 'names a specific country' are")
        print("  ONE split wearing two labels, and no quantity of data separates them -- not")
        print("  a confound more collection shrinks, one the design forecloses.")
        print()
        print("  Two readings sit on top of that split and this cannot choose between them:")
        print("    AGREEABLENESS   confidence tracks how agreeable a proposition is")
        print("    UNFALSIFIABILITY  the model hedges where a specific record could catch it")
        print("  The second is not the weaker one. It says the panel is most certain")
        print("  precisely where it cannot be checked.")
        print()
        print("  The fix is cheap and known: author documented items that are GENERIC, or")
        print("  normative items that NAME a jurisdiction. Either breaks the alignment.")
    else:
        print("  The claim_type / ratchet alignment is BROKEN, which is good news: %d")
        print("  documented-and-generic item(s) %s and %d normative-and-jurisdictional %s"
              % (len(detail["documented_and_generic"]), detail["documented_and_generic"],
                 len(detail["normative_and_jurisdictional"]),
                 detail["normative_and_jurisdictional"]))
        print("  now let the two readings be told apart. Re-run this and report both splits.")

    if a.items:
        print()
        print("  per item, strongest-answer rate:")
        for q, v in sorted(res["per_item"].items(), key=lambda kv: -kv[1]["strong"]):
            print("    item %-3d %6.1f%%  n=%d" % (q, 100 * v["strong"], v["n"]))

    if not a.check:
        return 0
    if res["models"] < MIN_MODELS:
        print()
        print("DEFECT: %d model(s) carry both classes, under the %d this comparison needs."
              % (res["models"], MIN_MODELS))
        return 1
    print()
    print("OK: %d models carry both classes." % res["models"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
