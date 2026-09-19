#!/usr/bin/env python3
"""How many hypothesis tests does this study actually run, and which are corrected?

WHY THIS EXISTS
---------------
`PAPER-below-the-floor.md` says the results rest on *"a Benjamini-Hochberg correction over the
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
     # NO COMMAND, AND THAT IS THE POINT. PLAN step 7 lists this among "the four findings
     # with no recorded command" -- it is computed, it is in the paper, and no script in the
     # tree produces it. Naming a plausible filename here would have created a reference to a
     # script that does not exist, which `check_named_scripts` correctly refuses; it caught
     # exactly that on the first version of this file.
     "command": None,
     "corrected": False,
     "note": "a split of the panel-agreement result by item class. ITS COMMAND IS OWED -- "
             "PLAN step 7. A figure in the paper with no command behind it cannot be "
             "re-derived by a reader, which is this project's own rule"},
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
     "command": "scripts/refusal_table.py --rung2, position contrasts vs rung-1 B",
     "corrected": True,
     "note": "BH-FDR applied WITHIN the rung over its own 15 contrasts, not pooled with the "
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
STATED_IN = ["PAPER-below-the-floor.md", "FINDINGS-2026-09-17-battery.md",
             "CORRECTIONS-2026-09-18-bootstrap.md"]


def prereg_family(run_dir=WAVE):
    """The pre-registered contrast count, FROM THE DATA. Never from prose.

    Counted STRUCTURALLY -- a contrast exists when a model has sheets in both arms -- rather
    than by running `analyse()`. The first version called `analyse()`, which is correct and
    takes sixteen minutes: 246 contrasts at 20,000 bootstrap draws each. A family SIZE is a
    property of the design and the coverage; it does not need a single resample, and a report
    that costs a quarter of an hour to answer "how many tests" is one nobody runs.
    """
    import position_analysis as P
    from studypaths import runs_root
    recs = P.load_records(str(runs_root() / run_dir))
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
    """Is this figure a record of what was believed, rather than a claim about now?"""
    if filename.startswith("CORRECTIONS-"):
        return "in a corrections document, which records what WAS believed"
    line_start = text.rfind("\n", 0, start) + 1
    line = text[line_start:text.find("\n", end) if text.find("\n", end) > 0 else len(text)]
    if line.lstrip().startswith(">"):
        return "inside a blockquote -- quoted, not asserted"
    window = text[max(0, start - 240):end + 80].lower()
    for marker in HISTORICAL_MARKERS:
        if marker in window:
            return "past tense nearby (%r)" % marker.strip()
    return None


def stated_family_sizes():
    """Every family-size figure written in prose, classified live or historical."""
    out = []
    pat = re.compile(
        r"(?:family of|over)\s+(\d{2,4})[\s-]*(?:member\s+)?(?:family|contrasts)"
        r"|(\d{2,4})-member\s+family"
        r"|(\d{2,4})\s+contrasts", re.I)
    for name in STATED_IN:
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
                "context": " ".join(text[max(0, m.start() - 60):m.end() + 20].split()),
            })
    return out


def report():
    live = prereg_family()
    stated = stated_family_sizes()
    stale = [s for s in stated
             if live is not None and s["stated"] != live and not s["historical"]]
    record = [s for s in stated if s["historical"]]
    return {"prereg_family_live": live, "stated": stated, "stale": stale,
            "historical": record, "exploratory": EXPLORATORY}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 when prose states a family size the data does not support")
    a = ap.parse_args(argv)

    res = report()
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
    print("  Limitations. This is the `multiple_comparisons` column the controls audit scores")
    print("  twelve other studies on.")
    print()

    if res["historical"]:
        print("HISTORICAL -- a record of what was believed, NOT checked and NOT to be edited:")
        for s in res["historical"]:
            print("  %s:%d  says %d  (%s)"
                  % (s["file"], s["line"], s["stated"], s["historical"]))
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
