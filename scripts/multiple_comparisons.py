#!/usr/bin/env python3
"""How many hypothesis tests does this study actually run, and which are corrected?

WHY THIS EXISTS
---------------
`PAPER-no-position-only-consensus.md` says the results rest on *"a Benjamini-Hochberg correction over the
whole family of 153 contrasts"*. Two things are wrong with that sentence and both are the kind
this study convicts other papers of.

**The number is hand-typed and stale.** The live count is whatever
`position_analysis --prereg` computes today; the corpus has grown since 153 was written. The
figure appears in four documents and nothing gates any of them.

**It counts only the corrected family.** The study also runs the jurisdiction gradient, the
claim-type split, the omission tests, the refusal switch, the clause factorial and the
elicitation rung -- none of them pre-registered, none of them BH-corrected, and none of them
counted anywhere. A reader asking "how many tests were run in total" cannot answer it from the
paper, which is precisely the `multiple_comparisons` column this project scores twelve other
studies on.

WHAT IT DOES
------------
Counts the pre-registered family FROM THE ANALYSIS rather than from prose, lists every
exploratory family with its correction status and where it is computed, and totals them. The
exploratory families are declared here because no single command runs them all -- but each
entry names the script that produces it, so a reader can re-derive the count instead of
trusting this list.

    python scripts/multiple_comparisons.py
    python scripts/multiple_comparisons.py --json
    python scripts/multiple_comparisons.py --check   # fails when a document states a
                                                     # family size that disagrees with the data
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, HERE)

WAVE = "2026-09-16-ratchet-v3-wave"

#: Test families this study runs that are NOT in the pre-registered BH family.
#:
#: Declared rather than derived, because they live in six different scripts and no single
#: command runs them all -- but every entry names its command, so the count is checkable.
#: `count` is `None` where the number moves with the corpus and must be read from the tool.
EXPLORATORY = [
    {"family": "jurisdiction gradient",
     "command": "scripts/jurisdiction_gradient.py",
     "corrected": False,
     "note": "unconditional and conditional forms, reported separately; the conditional one "
             "is the null (p=0.63) and the unconditional the finding (p=0.0004)"},
    {"family": "claim-type split (normative / documented)",
     # THIS READ `command: None` UNTIL 2026-09-19, and the None was load-bearing: the figure
     # was in the paper with no script producing it, and naming a plausible filename here
     # would have created a reference to a script that does not exist, which
     # `check_named_scripts` correctly refuses -- it caught exactly that on the first version
     # of this file. The script now exists, so the None goes rather than being explained.
     "command": "scripts/item_gradient.py --claim-type",
     "corrected": False,
     "note": "a split of the panel-agreement result by item class, critic half only -- the "
             "defender half of a documented pair is a claim of record being DENIED, so "
             "pooling the frames would average two different questions"},
    {"family": "agreement by training class (the shared-RLHF objection)",
     "command": "scripts/agreement_by_training.py",
     "corrected": False,
     "note": "four classes -- abliterated, Chinese-jurisdiction, US/EU, local 2024 -- against "
             "the panel's normative and documented agreement. Written AFTER the data was seen, "
             "in answer to a reviewer objection, which is the definition of exploratory and is "
             "why it is here rather than in the pre-registered family"},
    {"family": "intensity by claim type (top-box rate, documented vs normative)",
     "command": "scripts/intensity_by_claim.py",
     "corrected": False,
     "note": "one paired sign test over the models with enough answers in both classes; "
             "intensity_by_claim.py prints its p. Exploratory, and it carries a "
             "confound the design forecloses rather than one more data fixes: claim_type is "
             "perfectly aligned with the bank's jurisdiction tag, so this is simultaneously a "
             "result about record-backed claims and about jurisdiction-specific ones"},
    {"family": "item omission -- item vs slot vs numeral",
     "command": "scripts/item_omission.py --matrix",
     "corrected": False,
     "note": "H1 was rejected by its own pre-registered kill rule; the concentration p-value "
             "fires on BOTH causes and therefore decides nothing, which the tool prints"},
    {"family": "refusal switch by condition",
     "command": "scripts/refusal_table.py --switch",
     "corrected": False,
     "note": "per-model refusal across N/A/P/D"},
    {"family": "clause factorial",
     "command": "scripts/refusal_table.py --factorial",
     "corrected": False,
     "note": "8 cells x 7 models; judged against each model's own between-order floor per "
             "PREREG-2026-08-31 Amendment 2, which is a floor comparison and not a p-value"},
    {"family": "elicitation rung (rung 2)",
     "command": "scripts/rung2_contrast.py",
     "corrected": True,
     "note": "BH-FDR applied WITHIN the rung over its own 35 contrasts, not pooled with the "
             "pre-registered family -- a separate design with a separate control"},
    {"family": "group-attribute comparisons",
     "command": "scripts/group_power.py",
     "corrected": None,
     "count": 0,
     "note": "NONE RUN. Detection limits were computed and the comparisons were declined: "
             "the vintage MDE (0.177) exceeds the study's own largest manipulation (0.159). "
             "Counted here at zero so the decision is visible rather than silent"},
]

#: Where a family size is stated in prose. Every one of these is checked against the data.
#:
#: HAND-MAINTAINED, WHICH IS THE WEAK POINT. The first version listed three files while its
#: own commit message said "four documents", and the missing one -- `PLAN.md` -- carried a
#: LIVE stale 153 that therefore went unflagged. A file list is a second copy of "where the
#: numbers are", and this project's rule is to derive rather than type. Derived here: any
#: tracked markdown at the study root, minus the withdrawn tree.
def _stated_in():
    out = []
    for path in sorted(glob.glob(os.path.join(STUDY, "*.md"))):
        name = os.path.basename(path)
        if name.startswith("withdrawn"):
            continue
        # A PRE-REGISTRATION states the family IT registers, and it is immutable once
        # committed. The mirror files them under prereg/, which this glob never reached; the
        # study tree keeps them flat, so the same gate read them here and reported a
        # registered 10-contrast family as a stale study family.
        if name.startswith("PREREG-"):
            continue
        out.append(name)
    return out


def prereg_family(run_dir=WAVE):
    """The pre-registered contrast count, FROM THE DATA. Never from prose.

    Counted STRUCTURALLY -- a contrast exists when a model has sheets in both arms -- rather
    than by running `analyse()`. The first version called `analyse()`, which is correct and
    takes sixteen minutes: 246 contrasts at 20,000 bootstrap draws each. A family SIZE is a
    property of the design and the coverage; it does not need a single resample, and a report
    that costs a quarter of an hour to answer "how many tests" is one nobody runs.
    """
    import position_analysis as P
    from studypaths import run_path
    recs = P.load_records(str(run_path(run_dir)))
    if not recs:
        return None
    bank = P.load_bank()
    per_sheet = P.sheet_positions(recs, P.pair_index(bank))
    have = {(m, c) for m, c in per_sheet}
    n = 0
    for a, b in P.CONTRASTS:
        wa = P.CONDITION_MAP.get(a, a)
        wb = P.CONDITION_MAP.get(b, b)
        for model in {m for m, _c in have}:
            if (model, wa) in have and (model, wb) in have:
                n += 1
    return n


#: Past-tense markers that make a figure a RECORD rather than a CLAIM.
#:
#: A stale-number check that cannot tell these apart is dangerous in the direction that
#: matters. Three of the four hits on the first run were historical: a corrections document
#: saying what the miscalibrated estimator touched, a findings paragraph beginning "Until
#: 2026-09-17 ... resampling PAIRS", and a blockquote being refuted two words later by "it is
#: not". "Fixing" any of them would falsify the record of what was once believed -- and a
#: corrections document is the last file in the tree that should be edited to match today.
HISTORICAL_MARKERS = (
    "until ", "had ever been", "predating", "was produced by", "previously",
    "no longer", "withdrawn", "superseded", "at the time", "used to",
)


def _is_historical(text, start, end, filename):
    """Is this figure a record of what was believed, rather than a claim about now?

    KNOWN ASYMMETRY WITH `_is_local_family`, left deliberately. This treats a newline as a
    sentence boundary, so a historical marker that wraps just before its figure is invisible
    and the figure is reported as live. That fails SAFE -- a false positive names a sentence
    a human then reads -- whereas the same hole in `_is_local_family` fails toward reporting
    a true statement as stale, which trains an operator to ignore the gate. So only the
    latter was moved to the wrap-immune window; widening this one would loosen a check whose
    tightness is the point (see the comment below) and its tests are tuned to it.
    """
    if filename.startswith("CORRECTIONS-"):
        return "in a corrections document, which records what WAS believed"
    line_start = text.rfind("\n", 0, start) + 1
    line = text[line_start:text.find("\n", end) if text.find("\n", end) > 0 else len(text)]
    if line.lstrip().startswith(">"):
        return "inside a blockquote -- quoted, not asserted"
    # SAME SENTENCE, AND BEFORE THE NUMBER. A 240-character window silenced the check
    # trivially: this paper uses "until" 9 times, "withdrawn" 11 and "previously" 3, so almost
    # any live claim sat near one. Demonstrated by construction -- "The truncation gate is no
    # longer needed... We correct over the whole family of 153 contrasts" was suppressed, and
    # the one real hit survived only because its nearest marker was 760 characters away.
    #
    # A marker AFTER the figure does not make the figure historical either: "153 contrasts,
    # and that result was withdrawn" is a live count in a sentence about something else.
    sentence_start = max(text.rfind(". ", 0, start), text.rfind("\n", 0, start)) + 1
    window = text[sentence_start:start].lower()
    for marker in HISTORICAL_MARKERS:
        if marker in window:
            return "past tense in the same sentence, before the figure (%r)" % marker.strip()
    return None


#: A contrast count that belongs to ONE NAMED ARM is not a claim about the pre-registered
#: family. Added 2026-09-21, when `RESULTS-2026-09-21-rung2-control-v2.md` wrote "28 of 35
#: contrasts are at or under their own model's floor" -- a true statement about seventy sheets
#: of rung-2 control -- and this gate reported it as a stale family size of 35 against 246.
#:
#: NOT a loosening, and the distinction is load-bearing: the study's family is the set every
#: p-value is corrected across, and an arm's contrast count is how many comparisons that arm
#: computed. They are different objects and only the first can be stale. A per-file exemption
#: would have been the wrong fix -- every future arm write-up states its own count, so the
#: false positive recurs by construction (LEARNINGS #24).
#:
#: The qualifier has to be IN THE SENTENCE, before the number, the same discipline
#: `_is_historical` uses: a marker anywhere nearby silences a gate trivially.
LOCAL_FAMILY_MARKERS = (
    "this arm", "the arm", "arm-minus-control", "within the arm",
    "contrasts computed here", "of its own",
)


def _sentence_before(text, start):
    """The text from the last sentence end to `start`, with line wraps flattened.

    NOT `max(rfind(". "), rfind("\\n"))`, which is what `_is_historical` uses. Treating a
    newline as a sentence boundary makes the window empty whenever the sentence happens to
    wrap just before the figure -- and prose in this repository is hand-wrapped at 96
    columns, so that is a coin flip. Measured 2026-09-21: "Of this arm's own\\n35 contrasts"
    produced an EMPTY window and the qualifier three words to its left was invisible.

    Sentence-scoped and wrap-immune: find the last `.`/`!`/`?` followed by whitespace, and
    flatten every newline between there and the figure.
    """
    cut = 0
    for i in range(start - 1, 0, -1):
        if text[i - 1] in ".!?" and text[i].isspace():
            cut = i
            break
    return " ".join(text[cut:start].split()).lower()


def _is_local_family(text, start):
    """Does this figure count ONE ARM's contrasts rather than the study's family?"""
    window = _sentence_before(text, start)
    for marker in LOCAL_FAMILY_MARKERS:
        if marker in window:
            return "one arm's own contrast count, not the study's family (%r)" % marker
    return None


def _is_subset_of_a_correctly_stated_family(text, start, end, live):
    """A SUBSET of the family, in a sentence that states the family size correctly.

    §9.3 reads: *"over the 241 contrasts of the 246-contrast family that carry two scoreable
    arms"*. Both numbers are live and correct -- 246 is the pre-registered family and 241 is
    `exact_vs_bootstrap.compared`, the subset with two arms to compare -- and this gate
    reported the 241 as a stale family size of 241 against 246, in a sentence that names 246
    three words later.

    That is the LEARNINGS #84 shape: a guard firing on a true statement, and the fix it invites
    is to reword correct prose until a checker recognises it. It is also the shape the
    `local_family` classifier above was added for on 2026-09-21, one quantity over.

    NOT A LOOSENING, and the condition is deliberately narrow: the same sentence must state
    the LIVE family size, and this figure must be SMALLER than it. A sentence claiming a family
    size that is wrong still fails on that figure, because the wrong one is not `live` and so
    silences nothing. A figure larger than the family is not a subset and is not exempted.
    """
    if live is None:
        return None
    stated_here = int(next(g for g in re.match(
        r"(\d{2,4})", text[start:end]).groups() or (text[start:end],)))
    if stated_here >= live:
        return None
    sentence = _sentence_around(text, start)
    if re.search(r"\b%d\b" % live, sentence):
        return ("a subset of the family, in a sentence that states the live family size "
                "(%d) correctly" % live)
    return None


def _sentence_around(text, start):
    """The whole sentence containing `start`, wrap-flattened. Both sides, unlike the helper
    above, because the family size this one looks for is stated AFTER the subset figure."""
    left = 0
    for i in range(start - 1, 0, -1):
        if text[i - 1] in ".!?" and text[i].isspace():
            left = i
            break
    right = len(text)
    for i in range(start, len(text) - 1):
        if text[i] in ".!?" and text[i + 1].isspace():
            right = i
            break
    return " ".join(text[left:right].split())


def stated_family_sizes(live=None):
    """Every family-size figure written in prose, classified live or historical."""
    out = []
    # Qualifiers are allowed between the number and the noun. `PLAN.md` said "the 153
    # PRE-REGISTERED contrasts" and escaped a pattern that required them adjacent -- a live
    # stale figure missed by one word.
    pat = re.compile(
        r"(\d{2,4})-member\s+family"
        r"|(\d{2,4})\s+(?:[a-z-]+\s+){0,3}contrasts", re.I)
    for name in _stated_in():
        path = os.path.join(STUDY, name)
        if not os.path.exists(path):
            continue
        text = io.open(path, encoding="utf-8", errors="replace").read()
        for m in pat.finditer(text):
            n = next(g for g in m.groups() if g)
            out.append({
                "file": name,
                "line": text.count("\n", 0, m.start()) + 1,
                "stated": int(n),
                "historical": _is_historical(text, m.start(), m.end(), name),
                "local_family": _is_local_family(text, m.start()),
                "subset": _is_subset_of_a_correctly_stated_family(
                    text, m.start(), m.end(), live),
                "context": " ".join(text[max(0, m.start() - 60):m.end() + 20].split()),
            })
    return out


def report():
    live = prereg_family()
    stated = stated_family_sizes(live)
    stale = [s for s in stated
             if live is not None and s["stated"] != live
             and not s["historical"] and not s.get("local_family")
             and not s.get("subset")]
    record = [s for s in stated if s["historical"]]
    # PRINTED, NEVER DROPPED. A classification that removes a hit from the failing set has to
    # show its work, or it is indistinguishable from the pattern quietly not matching.
    local = [s for s in stated if s.get("local_family") and not s["historical"]]
    subset = [s for s in stated if s.get("subset") and not s["historical"]
              and not s.get("local_family")]
    return {"prereg_family_live": live, "stated": stated, "stale": stale,
            "historical": record, "local_family": local, "subset": subset,
            "exploratory": EXPLORATORY}


def markdown(res):
    """The §9 table, GENERATED.

    The family size was hand-typed in four documents and the four disagreed -- 153, 241, 246 --
    all of them stale in the direction that understates the correction burden, which is the
    direction that flatters. `--check` catches that after the fact; a generated block means
    there is nothing to catch, because the paper stops holding its own copy of the number.
    LEARNINGS #10: two copies of a measurement drift, so derive one.
    """
    live = res["prereg_family_live"]
    out = []
    out.append("| family | tests | correction | command |")
    out.append("|---|---:|---|---|")
    out.append("| pre-registered condition contrasts | %s | **BH-FDR across the family** | "
               "`position_analysis.py <run> --prereg` |"
               % ("not computable" if live is None else live))
    for e in res["exploratory"]:
        mark = {True: "BH within itself", False: "**none — exploratory**",
                None: "n/a"}[e["corrected"]]
        n = e.get("count")
        cmd = "`%s`" % e["command"] if e["command"] else "*no command*"
        out.append("| %s | %s | %s | %s |"
                   % (e["family"], "—" if n is None else n, mark, cmd))
    out.append("")
    out.append("Every row below the first is **uncorrected and exploratory**. They are not "
               "thereby wrong, and they are not a second family that a correction was "
               "forgotten on: they were not pre-registered, and the requirement this study "
               "holds other papers to is that each is marked as exploratory *at its point of "
               "use* rather than only in Limitations. The controls audit does not score "
               "the other studies on that.")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--markdown", action="store_true",
                    help="the §9 table, for gen_paper's GEN:comparisons block")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 when prose states a family size the data does not support")
    a = ap.parse_args(argv)

    res = report()
    if a.markdown:
        print(markdown(res))
        return 0
    if a.json:
        print(json.dumps(res, indent=2, sort_keys=True))
        return 1 if (a.check and res["stale"]) else 0

    live = res["prereg_family_live"]
    print("HOW MANY TESTS THIS STUDY RUNS")
    print()
    if live is None:
        print("  pre-registered family: NOT COMPUTABLE -- no records loaded. This is not a")
        print("  count of zero; it is a count that could not be taken.")
        return 1 if a.check else 2
    print("  CORRECTED -- one BH-FDR family, computed from the analysis:")
    print("    pre-registered contrasts   %d   position_analysis.py <run> --prereg" % live)
    print()
    print("  NOT CORRECTED -- exploratory, and the paper must mark each at its point of use:")
    for e in res["exploratory"]:
        mark = {True: "BH within itself", False: "uncorrected", None: "n/a"}[e["corrected"]]
        n = e.get("count")
        print("    %-42s %-17s %s" % (e["family"], mark,
                                      "" if n is None else "n=%d" % n))
        print("        %s" % (e["command"] or "NO COMMAND -- owed, PLAN step 7"))
        print("        %s" % e["note"])
    print()
    print("  Families that are not corrected are not thereby wrong -- they are exploratory,")
    print("  and the requirement is that the paper SAYS SO at each figure rather than only in")
    print("  Limitations. The controls audit does NOT yet score the other studies on this --")
    print("  there is no `multiple_comparisons` column in data/controls-audit.json. Both this")
    print("  line and the generated block claimed there was, which put a false statement about")
    print("  our own audit into the paper. Add the column, or keep saying it is missing.")
    print()

    if res["historical"]:
        print("HISTORICAL -- a record of what was believed, NOT checked and NOT to be edited:")
        for s in res["historical"]:
            print("  %s:%d  says %d  (%s)"
                  % (s["file"], s["line"], s["stated"], s["historical"]))
        print()

    if res.get("local_family"):
        print("ONE ARM'S OWN CONTRAST COUNT -- not the study's family, so not checked "
              "against it:")
        for s in res["local_family"]:
            print("  %s:%d  says %d  (%s)"
                  % (s["file"], s["line"], s["stated"], s["local_family"]))
            print("      ...%s..." % s["context"][:110])
        print()

    if res.get("subset"):
        print("A SUBSET OF THE FAMILY -- the same sentence states the live family size, so "
              "this figure is a different quantity:")
        for s_ in res["subset"]:
            print("  %s:%d  says %d  (%s)"
                  % (s_["file"], s_["line"], s_["stated"], s_["subset"]))
            print("      ...%s..." % s_["context"][:110])
        print()

    if res["stale"]:
        print("STALE -- prose states a family size the data does not support:")
        for s in res["stale"]:
            print("  %s:%d  says %d, live is %d" % (s["file"], s["line"], s["stated"], live))
            print("      ...%s..." % s["context"][:110])
        print()
        print("  The figure is hand-typed in %d place(s) and nothing gated it. A stale family"
              % len({s["file"] for s in res["stale"]}))
        print("  size understates the correction burden, which is the direction that flatters.")
        return 1 if a.check else 0

    if res["stated"]:
        print("every stated family size matches the live count of %d." % live)
    else:
        print("NO DOCUMENT STATES A FAMILY SIZE. That is not a pass -- the paper is required")
        print("to report how many tests were run, and this found none to check.")
        return 1 if a.check else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
