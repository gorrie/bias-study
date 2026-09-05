#!/usr/bin/env python3
"""The paper's load-bearing numbers, computed -- and a check that its prose still matches them.

Every table in PAPER-below-the-floor.md is generated. The prose around those tables is not,
and it quotes them: "twenty items of 62", "the same p90, 14 items either way", "which moves 9".
Those are hand-typed numbers sitting beside generated ones in a paper whose entire argument is
that hand-typed numbers go stale. On 2026-09-01 the frontier order sweep landed, the order
floor went from 18 pairs to 37, the detection limit moved from 20 to 16 -- and every sentence
quoting 20 was silently wrong until this file existed.

Each entry below names a quantity, computes it from `runs/`, and declares the exact phrase the
paper uses to state it. `--check` recomputes and re-greps; any mismatch exits 1 and names the
sentence to fix. This is deliberately brittle: a phrase that stops matching because the prose
was reworded is a prompt to re-read the sentence, which is the point.

    python scripts/key_numbers.py             # what the numbers are now
    python scripts/key_numbers.py --check     # do the paper's sentences still agree?
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
PAPER = os.path.join(STUDY, "PAPER-below-the-floor.md")
sys.path.insert(0, HERE)

import floor_table as F      # noqa: E402
import power as P            # noqa: E402
import refusal_table as R    # noqa: E402

# NOT a copy any more. This was a literal set "kept in sync" with gen_paper.py's --exclude
# argument, and on 2026-09-04 the paraphrase-floor arm had to be withheld from every refusal
# figure -- which meant editing the same fact in three places or having the paper and this
# gate describe different corpora. refusal_table.DEFAULT_EXCLUDE owns it; this is a reference.
REFUSAL_EXCLUDE = R.DEFAULT_EXCLUDE
AUDIT = os.path.join(STUDY, "data", "controls-audit.json")


def corpus_scale():
    """Runs, models and vendor families, counted from the corpus the paper describes.

    Added 2026-09-01 by a hostile read. Section 2's opening sentence -- "1,643 runs and 155
    models from 13 vendor families" -- had two numbers right and one wrong: vendor_of() yields
    SIXTEEN, and the generated refusal table two paragraphs earlier prints all sixteen rows.
    Three of them are not vendor families at all (this project's own harness agent, a hosting
    domain, a community fine-tuner), which is a disclosure problem rather than an arithmetic
    one -- but a paper arguing that studies fail to say what they pooled cannot state a count
    its own table contradicts.
    """
    rows = R.load(REFUSAL_EXCLUDE)
    vendors = sorted({R.vendor_of(r.get("model")) for r in rows})
    return {"runs": len(rows),
            "models": len({r.get("model") for r in rows}),
            "vendors": len(vendors),
            "vendor_list": vendors}


def matched_arms():
    """Section 1's claim, on the matched subset it describes: models present in BOTH arms.

    Added 2026-09-01 by a hostile read. The sentence read "37 refusals in 449 runs where the
    prompt carries no directive, and none in 347 runs where it carries one," across "32 models
    measured under both arms." Three of those four numbers reproduced exactly -- 32 models, 8
    that decline, 347 directive runs with zero refusals. The no-directive pair did not: 472
    runs and 38 refusals. Stale by one collection, ungated, and sitting in the paper's opening
    argument, which is the combination this whole paper is about.

    Arms are defined the way the sentence describes them: A and B carry no directive to commit
    (A asks for balance, B asks bare), D and P do (D demands commitment, P is the content-free
    placebo). C and E are excluded because they are not part of that contrast.
    """
    rows = R.load(REFUSAL_EXCLUDE)
    scoreable = [r for r in rows if R.classify(r) in ("valid", "refused")]
    no_dir, directive = {"A", "B"}, {"D", "P"}
    in_arm = {a: {r.get("model") for r in scoreable if r.get("condition") in a}
              for a in (frozenset(no_dir), frozenset(directive))}
    both = in_arm[frozenset(no_dir)] & in_arm[frozenset(directive)]
    sel = [r for r in scoreable if r.get("model") in both]
    nd = [r for r in sel if r.get("condition") in no_dir]
    di = [r for r in sel if r.get("condition") in directive]
    declining = {r.get("model") for r in nd if R.classify(r) == "refused"}
    dir_declining = {r.get("model") for r in di if R.classify(r) == "refused"}

    # PAIRED, PER MODEL -- because both pooled rates mislead, in opposite directions.
    #
    # Added 2026-09-04 after review. Pooled, refusal goes 7.8% -> 0.8% and reads as "a factor
    # of ten". That figure is dominated by ONE model: gemini-3.7-flash contributes 24 of the 39
    # no-directive refusals. Take the unweighted per-model mean instead and refusal goes UP,
    # 5.2% -> 8.3% -- because the three models that refuse under a directive have exactly ONE
    # directive run each, so each contributes a rate of 1.0.
    #
    # Neither number is the finding. The finding is paired and it is cleaner than either:
    # every model that declines without a directive stops declining with one, 8 of 8, and the
    # directive-arm refusals are three OTHER models. That statement survives both weightings,
    # which is why it is the one the paper now makes.
    silenced = sum(1 for m in declining if m not in dir_declining)
    return {"models": len(both),
            "nodir_runs": len(nd),
            "nodir_refusals": sum(1 for r in nd if R.classify(r) == "refused"),
            "dir_runs": len(di),
            "dir_refusals": sum(1 for r in di if R.classify(r) == "refused"),
            "declining": len(declining),
            "silenced": silenced,
            "dir_only": len(dir_declining - declining)}


def audit_scale():
    """External studies in the controls audit, and how many were read end to end.

    Added 2026-09-01 by a hostile read, which found the paper stating this count three
    different ways -- eleven, twelve, and ten -- against a record that says twelve external
    studies, nine of them read in full. `ours` is in the same JSON and must not be counted as
    a study we audited.
    """
    import json
    rec = json.load(io.open(AUDIT, encoding="utf-8"))
    studies = rec["studies"] if isinstance(rec, dict) and "studies" in rec else rec
    if isinstance(studies, dict):
        studies = [dict(v, key=k) for k, v in studies.items()]
    external = [s for s in studies if (s.get("key") or s.get("id")) != "ours"]
    full = [s for s in external if s.get("provenance") == "full-text"]

    # The two columns that come back nearly empty, counted rather than described. The public
    # page said "two columns come back nearly empty" in prose while the counts sat in the
    # JSON; prose is what goes stale, and this page's own argument is that a number typed into
    # a document rots. Also count where the field is STRONG -- a critique that reports only
    # failures is a hit piece, and most of these authors do publish their raw data.
    def tally(control, verdict):
        return sum(1 for s in external if (s.get("status") or {}).get(control) == verdict)

    ours = next((s for s in studies if (s.get("key") or s.get("id")) == "ours"), None)
    ours_status = (ours or {}).get("status") or {}
    controls = list((rec.get("controls") or {}).keys()) if isinstance(rec, dict) else []

    # EXTERNAL ONLY, every count. `ours` is 9-for-9 and sits in the same JSON, so including it
    # inflates every "the field does X" figure by one. Caught 2026-09-04 when a first draft of
    # the public table said 1 study reports the same-version distribution and 10 publish raw
    # data; the true external figures are 0 and 9. The docstring above warns about exactly this
    # and it still happened, which is the argument for computing these rather than typing them.
    return {"external": len(external), "full_text": len(full),
            "not_full": len(external) - len(full),
            "yes_same_version_dist": tally("same_version_dist", "yes"),
            "no_same_version_dist": tally("same_version_dist", "no"),
            "yes_reported_mde": tally("reported_mde", "yes"),
            "no_reported_mde": tally("reported_mde", "no"),
            "yes_quantisation": tally("quantisation", "yes"),
            "yes_open_raw": tally("open_raw", "yes"),
            "yes_forcing": tally("forcing_disclosed", "yes"),
            "no_forcing": tally("forcing_disclosed", "no"),
            "n_controls": len(controls),
            "ours_pass": sum(1 for c in controls if ours_status.get(c) == "yes")}


def floors():
    out = {}
    for fn in (F.floor_order, F.floor_same_version, F.floor_template, F.floor_replicate,
               F.floor_quant,
               F.floor_ablation, F.floor_conditions):
        r = fn()
        if r:
            out[r["name"]] = r
    return out


def build():
    f = floors()
    pairs = P.collect()
    scale = corpus_scale()
    audit = audit_scale()
    arms = matched_arms()

    def mde(name, stat="side"):
        vals = pairs[name][stat]
        return P.mde(vals, P.pctile(vals, 1 - P.ALPHA))

    order = f["presentation order"]
    manip = f["prompt condition A->D"]
    abl = f["refusal-direction ablation"]
    null = f["same-version variants"]

    return [
        {"key": "order_mde",
         "value": mde("presentation order"),
         "what": "detection limit against the pooled order floor, side-flips, 80% power",
         "phrase": "%d items of 62, against presentation order pooled"},
        {"key": "null_mde",
         "value": mde("same-version variants"),
         "what": "detection limit against the same-version null -- the one that governs a modern study",
         "phrase": "same-version limit of %d"},
        {"key": "order_p90_local",
         "value": F.floor_order_by_class()["presentation order, local open-weight"]["side"][1],
         "what": "order floor p90 on 2024-generation open-weight models",
         # The phrase used to read "p90 %d, max 24" -- a SECOND number, hardcoded inside the
         # template for a different quantity. When the local max moved 24 -> 22 the gate's own
         # expectation went stale and it failed on a sentence that was correct. A checker that
         # smuggles an unchecked number into its expectation is a checker with a blind spot.
         "phrase": "our order floor is p90 %d"},
        {"key": "order_max_local",
         "value": F.floor_order_by_class()["presentation order, local open-weight"]["side"][2],
         "what": "order floor MAX on 2024-generation open-weight models",
         "phrase": "max %d — a different factor"},
        {"key": "order_p90_frontier",
         "value": F.floor_order_by_class()["presentation order, frontier API"]["side"][1],
         "what": "order floor p90 on 2026 frontier models",
         "phrase": "2026 frontier models gives p90 %d"},
        {"key": "order_pairs",
         "value": order["n"],
         "what": "pairs behind the order floor",
         "phrase": "The order floor rests on %d pairs"},
        {"key": "manip_p90",
         "value": manip["side"][1],
         "what": "deliberate manipulation p90, side-flips",
         "phrase": "forced commitment | %d |"},
        {"key": "null_median",
         "value": null["side"][0],
         "what": "same-version null median, side-flips",
         "phrase": "pairs differ by %d items or more with no version change"},
        {"key": "null_pairs",
         "value": null["n"],
         "what": "pairs in the same-version null",
         "phrase": "%d pairs of models that differ in size, tier, snapshot date or mode, and not in"},
        {"key": "corpus_runs",
         # Thousands-separated, because that is how the sentence writes it and the check is a
         # literal grep. A gate that only matches an unformatted integer would pass forever
         # on a sentence saying "1,643" and fail the moment anyone wrote it the way it reads.
         "value": "{:,}".format(scale["runs"]),
         "what": "runs in the corpus the paper describes, matching the refusal block's exclusion",
         "phrase": "across %s runs"},
        {"key": "corpus_models",
         "value": scale["models"],
         "what": "distinct models in that corpus",
         "phrase": "runs and %d models"},
        {"key": "corpus_vendors",
         "value": scale["vendors"],
         "what": "distinct vendor keys vendor_of() yields -- the row count of the refusal table",
         "phrase": "%d vendor families"},
        {"key": "arms_models",
         "value": arms["models"],
         "what": "models measured under both the no-directive and directive arms",
         "phrase": "Across %d models measured under both arms"},
        {"key": "arms_nodir_refusals",
         "value": arms["nodir_refusals"],
         "what": "refusals in the no-directive arm on that matched subset",
         "phrase": "there are %d refusals"},
        {"key": "arms_nodir_runs",
         "value": arms["nodir_runs"],
         "what": "no-directive runs on that matched subset",
         "phrase": "in %d runs where the prompt carries no directive"},
        {"key": "arms_dir_runs",
         "value": arms["dir_runs"],
         "what": "directive runs on that matched subset",
         "phrase": "against %d runs where it carries one"},
        # THE LOAD-BEARING NUMBER OF SECTION 1, and it was ungated until 2026-09-04. The
        # sentence said "none in 347 runs where it carries one" and the gate only checked the
        # 347 -- the zero was hardcoded in the phrase, so the one quantity the argument rests
        # on was the one quantity nothing recomputed. It is no longer zero: three local models
        # added on 2026-09-04 refuse under the commitment directive, and the claim narrows
        # from "not one" to "3 in 354". A gate that checks the denominator of a rate and not
        # its numerator is checking the wrong half.
        {"key": "arms_dir_refusals",
         "value": arms["dir_refusals"],
         "what": "refusals in the directive arm on that matched subset",
         "phrase": "%d of those runs are refusals"},
        # The paired statement, gated so it cannot drift the way the zero did.
        {"key": "arms_silenced",
         "value": arms["silenced"],
         "what": "models that decline without a directive and NOT with one",
         "phrase": "all %d of them stop"},
        {"key": "arms_dir_only",
         "value": arms["dir_only"],
         "what": "models that decline ONLY under a directive",
         "phrase": "%d other models decline only when told to commit"},
        # "decline the instrument at least once" was the description and it counts only the
        # NO-DIRECTIVE arm. Across both arms 11 models decline at least once (8 + 3 that
        # decline only under a directive), and the paper's sentence sat immediately after a
        # clause describing both arms -- so it read as a total and the total was different.
        # An ambiguous label on a gated number is a gate protecting the wrong quantity.
        {"key": "arms_declining",
         "value": arms["declining"],
         "what": "models that decline in the NO-DIRECTIVE arm (11 decline in one arm or other)",
         "phrase": "%d models decline it without a directive"},
        {"key": "audit_external",
         "value": audit["external"],
         "what": "external studies in the controls audit, excluding ours",
         "phrase": "%d studies, nine controls"},
        {"key": "audit_full_text",
         "value": audit["full_text"],
         "what": "of those, read in full rather than retrieved as a summary",
         "phrase": "%d of the twelve read in full"},
    ]


#: W3.2 -- the SAME numbers, on the OTHER surfaces that state them.
#:
#: The paper is not the only place these quantities appear in prose. The public research page
#: and the release repository's README both narrate them, in their own words, and neither is
#: regenerated from `runs/`. That is three hand-typed copies of one fact, which is the exact
#: defect this file exists to catch inside the paper -- just spread across repositories, where
#: nobody re-reads them together.
#:
#: It found one on its first run. The website says "across 1,657 runs, 155 models and sixteen
#: vendor keys"; the release README says "across 1,692 runs, 155 models and sixteen vendor
#: keys" -- the same sentence, a different corpus size, because the release copy predates the
#: exclusion the paper applies (REFUSAL_EXCLUDE, the google-orderfloor run dir).
#:
#: Keys absent from a surface are simply not checked there: a page is allowed to omit a number.
#: What it may not do is state a DIFFERENT one in the same words.
#: Surfaces are located by SEARCHING rather than by counting directory levels up from STUDY.
#:
#: This file lives in two trees -- the private study and the public mirror -- and
#: `check_no_fork.py` requires those copies to be byte-identical, because a fork is how a fix
#: lands on one side only (it caught this very edit). A hardcoded `dirname(dirname(STUDY))`
#: resolves to different places in the two trees, so it would either break in the mirror or
#: force a fork. Candidate paths, with a missing surface simply not checked, work in both.
def _find_surface(*relative_parts):
    here = os.path.abspath(STUDY)
    for _ in range(6):
        here = os.path.dirname(here)
        if not here:
            break
        candidate = os.path.join(here, *relative_parts)
        if os.path.exists(candidate):
            return candidate
    return os.path.join(STUDY, *relative_parts)      # non-existent; reported, not crashed


SURFACES = {
    "website": {
        "path": _find_surface("website", "content", "research", "ai-bias-audit.md"),
        "phrases": {
            "corpus_runs": "across %s runs",
            "corpus_models": "runs, %d models",
            # The page's own wording, bold markers and line wrap included -- the phrase is a
            # literal grep, so it has to be the sentence as written rather than as summarised.
            "order_mde": "of %d items of 62** at 80%% power",
            "arms_models": "Across the %d models measured under both arms",
            "arms_nodir_refusals": "%d refusals in 499 runs",
            "arms_nodir_runs": "39 refusals in %d runs",
            # Gated on the public page too, for the same reason it is gated in the paper: this
            # page carried "not one of them declines even once ... 347 runs, zero refusals"
            # until 2026-09-04, and the zero was the only figure on it that was typed rather
            # than generated.
            "arms_silenced": "**all %d of them stop**",
            "arms_dir_only": "**%d other models decline only when told to commit**",
            # Conclusion five. Gated because it is the most quotable paragraph on the page,
            # and because its own argument is that a typed number goes stale.
            "replicate_med": "A median of %d answers move",
            "replicate_max": "and up to %d.**",
            "order_max_all": "Reorder the questions and up to %d move",
            "same_version_max": "two variants of one release and up to %d move",
            "manipulation_p90": "moves %d at its 90th percentile",
            # The audit block, added 2026-09-04. These were prose ("two columns come back
            # nearly empty") while the counts sat in the JSON, on a page whose own argument is
            # that a typed number rots -- and the page still said "ten studies" after the
            # paper had been corrected to twelve.
            # A NUMERAL, not a spelled-out word. The page said "ten studies" in prose long
            # after the paper was corrected to twelve, and a spelled word cannot be gated by
            # a numeric grep -- which is precisely how it survived.
            # Every phrase here carries its ROW LABEL. A bare "| **%d of 12** |" matched three
            # different rows of the same table, so the gate reported the same-version row's
            # figure as drift against the raw-data row's -- a guard that cannot tell two
            # numbers apart is not guarding either.
            "audit_external": "Of the %d external studies",
            "audit_controls": "scored against %d controls",
            "audit_yes_same_version_dist": "the null a drift claim needs | **%d of 12** |",
            "audit_no_same_version_dist": "%d say no and one is not applicable",
            "audit_yes_quantisation": "controls for quantisation | **%d of 12** |",
            "audit_yes_reported_mde": "minimum detectable effect at all | %d of 12",
            "audit_no_reported_mde": "of 12 (**%d say no**)",
            "audit_yes_open_raw": "publishes its raw data** | **%d of 12** |",
            "audit_yes_forcing": "discloses its forcing prompt** | %d of 12",
            "audit_ours_pass": "our own run passes %d of 9",
        },
    },
    "release": {
        "path": _find_surface("bias-study-release", "README.md"),
        "phrases": {
            "corpus_runs": "across %s runs",
            "corpus_models": "runs, %d models",
        },
    },
}


#: Numbers a SURFACE states that the paper does not. Same guard, different text: the public
#: page reports the audit's control gaps and our own row, which the paper covers in a generated
#: table rather than in a sentence, so there is no paper phrase to grep. Keyed the same way and
#: checked the same way -- the point is that no hand-typed number on any surface is unguarded.
#: Floor rows this checkout could not compute, filled in by `surface_numbers()` and reported by
#: the gate. A set rather than a flag because the caller has to be able to NAME them: "3 numbers
#: were not verifiable here" is a usable sentence, "some checks were skipped" is not.
MISSING_FLOORS = set()


def surface_numbers():
    a = audit_scale()
    fl = floors()
    out = [
        {"key": "audit_yes_same_version_dist", "value": a["yes_same_version_dist"],
         "what": "external studies that DO report a same-version distribution"},
        {"key": "audit_no_same_version_dist", "value": a["no_same_version_dist"],
         "what": "external studies reporting no same-version distribution"},
        {"key": "audit_yes_quantisation", "value": a["yes_quantisation"],
         "what": "external studies that DO control for quantisation"},
        {"key": "audit_yes_reported_mde", "value": a["yes_reported_mde"],
         "what": "external studies that DO report a minimum detectable effect"},
        {"key": "audit_no_reported_mde", "value": a["no_reported_mde"],
         "what": "external studies reporting no minimum detectable effect"},
        {"key": "audit_yes_open_raw", "value": a["yes_open_raw"],
         "what": "external studies that DO publish their raw data"},
        {"key": "audit_yes_forcing", "value": a["yes_forcing"],
         "what": "external studies that DO disclose their forcing prompt"},
        {"key": "audit_controls", "value": a["n_controls"],
         "what": "controls each study is scored against"},
        {"key": "audit_ours_pass", "value": a["ours_pass"],
         "what": "of those controls our own run passes"},
        # CONCLUSION FIVE's numbers. They live here rather than in build() because build()'s
        # rows are grepped against the PAPER, and the paper states these figures inside its
        # generated floors table rather than in these sentences. A website-only sentence gated
        # against the paper fails forever on prose that was never supposed to be there.
        #
        # Gated at all because that conclusion is the most quotable paragraph on the page and
        # its own argument is that a number typed into a document goes quietly stale.
    ]

    # A FLOOR ROW THAT THIS CHECKOUT CANNOT COMPUTE IS NOT A CRASH.
    #
    # These five were indexed directly out of `fl`, which is fine in the private working tree
    # where every run exists. This public repository ships a smaller run set -- it has no
    # instruction-paraphrase and no run-to-run-replicate runs at all -- so `fl["run-to-run
    # replicate"]` raised KeyError and took down `--check`, `--check-website` and
    # `--check-release` with it, on the repo whose entire purpose is that a stranger can run
    # these commands.
    #
    # Absent is not zero and it is not a pass. A row this checkout cannot compute is dropped
    # from the gate and NAMED, so the summary says how many numbers were verified and which
    # were unverifiable here -- the same distinction background_rate.py draws between a bucket
    # that measures nothing and a bucket that is not in the tree.
    optional = [
        ("replicate_med", "run-to-run replicate", 0,
         "median side-flips when NOTHING changes: same model, same prompt, temp 0"),
        ("replicate_max", "run-to-run replicate", 2, "worst case of the same"),
        ("order_max_all", "presentation order", 2, "worst case under reordering alone"),
        ("same_version_max", "same-version variants", 2,
         "worst case between two variants of one release"),
        ("manipulation_p90", "prompt condition A->D", 1,
         "the deliberate manipulation's p90 -- the bar the nuisance factors clear"),
    ]
    for key, row, idx, what in optional:
        if row in fl:
            out.append({"key": key, "value": fl[row]["side"][idx], "what": what})
        else:
            MISSING_FLOORS.add(row)
    return out


def check_ours_row(rows):
    """Our own row in the controls audit describes its own scale. Does it still?

    Added 2026-09-04. That field read "1643 runs, 155 models, 13 vendor families" while the
    paper two directories away said 1,657 runs and 16 vendor keys. It is unrendered today and
    it goes public with the audit, and it is the record backing the sentence "the same table
    scores us" -- so a stale self-description there is the exact defect this study convicts
    five other papers of, sitting in the file that carries the conviction.

    Returns a list of (what, expected, found) for anything the string no longer states.
    """
    rec = json.load(io.open(AUDIT, encoding="utf-8"))
    studies = rec["studies"] if isinstance(rec, dict) and "studies" in rec else rec
    if isinstance(studies, dict):
        studies = [dict(v, key=k) for k, v in studies.items()]
    ours = next((s for s in studies if (s.get("key") or s.get("id")) == "ours"), None)
    if ours is None:
        return [("ours row", "a row keyed 'ours' in the controls audit", None)]

    scale = ours.get("scale") or ""
    by_key = {r["key"]: r["value"] for r in rows}
    bad = []
    # Each of these is stated in the scale string as a bare number, so check for the number
    # rather than for a phrase -- the wording of that field is not load-bearing, the digits are.
    for key, label in (("corpus_runs", "runs"),
                       ("corpus_models", "models"),
                       ("corpus_vendors", "vendor keys")):
        want = "%s" % by_key[key]
        if want not in scale:
            bad.append(("controls-audit 'ours' %s" % label, want, scale))
    return bad


#: Claims this project has WITHDRAWN, as literal strings that must not survive on any surface.
#:
#: Every entry earned its place by outliving its own correction. A positive gate ("the page
#: says N") is satisfied by one occurrence and blind to the others, so a retracted sentence
#: sitting in a table, a caption or an older section passes review indefinitely. This is the
#: negative half, and it is the half that matters for a withdrawal.
#:
#: Add a phrase here the moment a claim is retracted -- not the moment someone notices it
#: survived somewhere.
RETRACTED = [
    ("none in 347 runs where it carries one",
     "the zero-refusals-under-a-directive claim, withdrawn 2026-09-04. Three models decline "
     "under a directive; the surviving statement is the paired one (all 8 decliners stop, "
     "3 others decline only when told to commit)"),
    ("not one of them declines even once",
     "same withdrawal, the public page's wording of it"),
    ("Not one of them declines when told firmly to answer",
     "same withdrawal, the paper's wording of it"),
    ("n too small",
     "the requantisation row's interval. It rested on 4 pairs from ONE weights family until "
     "2026-09-04 and now has 13 pairs from four, with a real CI -- any surface still saying "
     "the interval cannot be computed is describing the retired version"),
]


def _unquoted_occurrences(text, phrase):
    """Occurrences of `phrase` that are ASSERTED, not quoted inside a correction note.

    A withdrawal has to be describable. "This paragraph originally said 'not one of them
    declines even once'" is the correction working correctly, and a gate that forbids the
    words outright would force every retraction to be silent about what it retracted -- which
    is how a page ends up quietly acquiring the right answer and teaching nobody how it got
    the wrong one.

    The distinction is quotation. A retraction quotes the old claim; an assertion states it.
    So an occurrence is allowed when a quote mark opens before it and closes after it on the
    same line, and reported otherwise. Deliberately simple: a rule a writer can predict beats
    a cleverer one they cannot.
    """
    out = []
    for line in text.split("\n"):
        start = 0
        while True:
            i = line.find(phrase, start)
            if i < 0:
                break
            start = i + 1
            before, after = line[:i], line[i + len(phrase):]
            quoted = any(before.count(q) % 2 == 1 for q in ('"', "“")) or (
                "“" in before and "”" in after)
            if not quoted:
                out.append(line.strip()[:110])
    return out


def check_surface(name, rows):
    """Verify one non-paper surface still states the computed numbers. Returns a failure list."""
    spec = SURFACES[name]
    path = spec["path"]
    if not os.path.exists(path):
        # NOT a failure. This file is byte-identical in two trees and only one of them
        # contains the website, so "absent here" is the ordinary state rather than drift.
        # Printed loudly so a surface that vanished from the tree that SHOULD have it is
        # still visible -- the gate that matters runs where the surface lives.
        print("%s: NOT PRESENT in this tree (%s) -- not checked here"
              % (name, os.path.basename(path)))
        return []
    text = io.open(path, encoding="utf-8", newline="").read().replace("\r\n", "\n")
    by_key = {r["key"]: r for r in list(rows) + surface_numbers()}
    bad = []
    checked = 0

    # RETRACTED PHRASES MUST BE ABSENT. A positive grep cannot catch a SECOND stale copy:
    # on 2026-09-04 the zero-refusals claim was corrected at one place on the research page
    # and left standing in a comparison table 115 lines further down, and this gate passed --
    # because the phrase it looks for was satisfied by the corrected sentence. A claim is
    # retracted from a PAGE, not from a line.
    for phrase, why in RETRACTED:
        for occurrence in _unquoted_occurrences(text, phrase):
            bad.append(("RETRACTED", "must not be ASSERTED anywhere: %s" % why, occurrence))
    for key, phrase in spec["phrases"].items():
        row = by_key.get(key)
        if row is None:
            bad.append((key, "no such computed number", ""))
            continue
        checked += 1
        expected = phrase % row["value"]
        if expected not in text:
            # Show the surface's own version of the sentence, so the drift is visible.
            stem = phrase.split("%")[0].strip()
            found = ""
            if stem:
                for line in text.split("\n"):
                    if stem and stem in line:
                        found = line.strip()[:160]
                        break
            bad.append((key, expected, found))
    if not bad:
        print("%s: all %d stated number(s) agree with runs/" % (name, checked))
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--check-website", action="store_true",
                    help="do the public research page's numbers still match runs/?")
    ap.add_argument("--check-release", action="store_true",
                    help="does the release repository's README still match runs/?")
    args = ap.parse_args(argv)

    rows = build()

    if args.check_website or args.check_release:
        failures = []
        for name, wanted in (("website", args.check_website),
                             ("release", args.check_release)):
            if wanted:
                failures += [(name,) + f for f in check_surface(name, rows)]
        if not failures:
            return 0
        print("")
        print("CROSS-SURFACE DRIFT -- %d statement(s) disagree with runs/" % len(failures))
        print("These are hand-typed copies of generated numbers, living in a different repo")
        print("from the paper, which is why nobody re-reads them together.")
        print("")
        for surface, key, expected, found in failures:
            print("  [%s] %s" % (surface, key))
            print("    expected: %r" % expected)
            if found:
                print("    surface says: %r" % found)
        return 1

    if not args.check:
        print("KEY NUMBERS -- computed from runs/, and the phrase the paper uses for each")
        print()
        for r in rows:
            # %s, not %d: one entry carries a thousands-formatted string ("1,657"), and %d
            # crashed on it -- so the file's own documented no-argument usage was broken while
            # --check kept working, because --check formats through each entry's own phrase.
            print("  %-14s %5s   %s" % (r["key"], r["value"], r["what"]))
            print("  %-14s       \"%s\"" % ("", r["phrase"] % r["value"]))
        print()
        print("Run --check to verify the paper's prose still says these.")
        return 0

    if not os.path.exists(PAPER):
        # THE PAPER IS NOT DISTRIBUTED IN THIS REPOSITORY, AND THIS USED TO BE A TRACEBACK.
        #
        # `--check` gates the paper's hand-typed sentences against the generated tables. It is
        # the same script in the private working tree, where the paper lives; here it crashed
        # with FileNotFoundError on the first thing a reader of a reproduction repo would type.
        #
        # Absent is not stale and it is not a pass either. So: say what cannot be checked, run
        # what can -- this repository's own README carries two of the same numbers -- and fail
        # if THAT drifts. Returning 0 here without checking anything would be the vacuous pass
        # this project holds to be worse than a failure.
        print("The paper (%s) is not distributed in this repository, so its prose"
              % os.path.basename(PAPER))
        print("cannot be gated here. Checking this repository's own surfaces instead.")
        print("")
        failures = check_surface("release", rows)
        if failures:
            print("CROSS-SURFACE DRIFT -- %d statement(s) disagree with the run data"
                  % len(failures))
            for f in failures:
                print("  [release] %s" % (" | ".join(str(x) for x in f if x != "")))
            return 1
        print("RELEASE SURFACE: every stated number in README.md agrees with the run data.")
        print("%d generated numbers available; run with no flags to print them all." % len(rows))
        if MISSING_FLOORS:
            # NAMED, not swallowed. This repository ships a smaller run set than the working
            # tree, so some floor rows have nothing to compute from -- say which, or a reader
            # cannot tell a gate that verified everything from one that verified less.
            print("Not computable in this checkout, so not gated here: %s"
                  % ", ".join(sorted(MISSING_FLOORS)))
        return 0

    text = io.open(PAPER, encoding="utf-8", newline="").read().replace("\r\n", "\n")
    bad = []
    for r in rows:
        expected = r["phrase"] % r["value"]
        if expected not in text:
            bad.append(r)

    ours_bad = check_ours_row(rows)

    if not bad and not ours_bad:
        print("PROSE CHECK: all %d load-bearing numbers match the paper's sentences," % len(rows))
        print("and the controls audit's own row still describes the corpus it was run on")
        return 0

    if ours_bad:
        print("THE AUDIT'S OWN ROW IS STALE -- %d figure(s)" % len(ours_bad))
        print("This is the defect the paper convicts five other studies of, in our record of it.")
        for what, want, found in ours_bad:
            print("  %s: expected to state %s" % (what, want))
            print("    field says: %r" % found)
        print()
        if not bad:
            return 1

    print("PROSE CHECK FAILED -- %d of %d sentences disagree with the data" % (len(bad), len(rows)))
    print("Either the corpus grew and the prose is stale, or the prose was reworded.")
    print("Both need a human to re-read the sentence; neither is fixed by a find-and-replace.")
    print()
    for r in bad:
        print("  %s (%s)" % (r["key"], r["what"]))
        print("    expected in the paper: \"%s\"" % (r["phrase"] % r["value"]))
        # Show what the paper says instead, if the phrase skeleton is recognisable.
        stem = r["phrase"].split("%d")[0].strip()
        if stem and stem in text:
            i = text.index(stem)
            print("    paper currently says: ...%s..."
                  % " ".join(text[i:i + 90].split()))
        else:
            print("    (phrase not found at all -- the sentence may have been rewritten)")
        print()
    return 1


if __name__ == "__main__":
    sys.exit(main())
