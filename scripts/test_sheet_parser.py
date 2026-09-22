#!/usr/bin/env python3
"""Fixtures for the forced-choice parser in run_battery.py. Run before any collection.

The parser is the single point where a model's reply becomes a number, so a silent bug
here corrupts every downstream result and nothing else in the pipeline would notice. Two
real bugs were caught by this suite before any API call was made:

  1. "**3.** **Strongly Agree**" -- markdown bold between the separator and the option was
     not matched. Failed safe (invalidated the run) but would have burned good calls.
  2. "_Strongly Disagree_" -- `\\b` does not fire after an underscore, because underscore
     is a word character. Every italicised answer was dropped as missing. Fixed with a
     `(?![a-z])` lookahead, which still refuses "Agreement".

The third case is the dangerous one and it has never failed: alternation order must try
"strongly disagree" before "disagree", or every Strongly Disagree silently reads as a
Disagree and the scale compresses toward the middle -- manufacturing the both-sides
signal the study exists to measure.

Same role as data/judge-gold.json plays for the refusal judge: a known-answer set that
gates the instrument. `run_battery.py --dry-run` shows the prompt; this shows the parse.

Usage:
    python test_sheet_parser.py          # exits 1 on any failure
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).parent))
from run_battery import POSITIONS, parse_answers  # noqa: E402

NL = "\n"
IDS = list(range(1, 63))


def sheet(fmt):
    return NL.join(fmt(i, POSITIONS[i % 4]) for i in IDS)


CLEAN = sheet(lambda i, p: "%d. %s" % (i, p))

CASES = [
    # (name, text, expect_valid, expected positions to spot-check)
    ("clean 62, all four options", CLEAN, True, {1: 1, 2: 2, 3: 3, 4: 0}),
    ("Strongly Disagree is not Disagree",
     sheet(lambda i, p: "%d. Strongly Disagree" % i), True, {i: 0 for i in IDS[:5]}),
    ("Strongly Agree is not Agree",
     sheet(lambda i, p: "%d. Strongly Agree" % i), True, {i: 3 for i in IDS[:5]}),
    ("markdown bold, colon and paren separators",
     NL.join(("**%d.** **%s**" if i % 3 == 0 else ("%d) %s" if i % 3 == 1 else "%d: %s"))
             % (i, POSITIONS[i % 4]) for i in IDS), True, {3: 3, 1: 1, 2: 2}),
    ("underscore italics and list dashes",
     sheet(lambda i, p: "- %d. _%s_" % (i, p)), True, {4: 0, 1: 1, 2: 2, 3: 3}),
    ("preamble before the list", "Here are my answers:" + NL + NL + CLEAN, True, {1: 1}),
    ("one missing invalidates the run",
     NL.join("%d. Agree" % i for i in IDS if i != 37), False, None),
    ("a duplicate invalidates the run", CLEAN + NL + "5. Agree", False, None),
    ("an unknown item number invalidates the run", CLEAN + NL + "63. Agree", False, None),
    ("prose refusal invalidates the run",
     "I do not have personal political opinions.", False, None),
    ("empty reply invalidates the run", "", False, None),
    ("'Agreement' is prose, not an answer",
     "1. Agreement is complex." + NL + NL.join("%d. Agree" % i for i in IDS[1:]),
     False, None),
]


def main():
    failures = 0
    for name, text, expect_valid, spot in CASES:
        answers, problems = parse_answers(text, IDS)
        ok = (not problems) == expect_valid
        if ok and expect_valid and spot:
            got = {a["q"]: a["position"] for a in answers}
            ok = all(got.get(q) == pos for q, pos in spot.items())
        detail = "; ".join(problems)[:52] if problems else "%d answers" % len(answers)
        print("%-46s %s   %s" % (name, "PASS" if ok else "*** FAIL ***", detail))
        failures += not ok

    # A gap must never be filled. Silently inserting the midpoint would fabricate exactly
    # the balanced answer the study is trying to detect.
    answers, _ = parse_answers(NL.join("%d. Agree" % i for i in IDS if i != 37), IDS)
    invented = any(a["q"] == 37 for a in answers)
    print("%-46s %s   %s" % ("a missing item is never invented",
                             "*** FAIL ***" if invented else "PASS",
                             "q37 FABRICATED" if invented else "q37 absent"))
    failures += invented

    print()
    print("*** %d FAILED ***" % failures if failures else "ALL PASS")
    return 1 if failures else 0


def test_all_parser_fixtures_pass():
    """Make the 13 fixtures visible to pytest.

    They lived entirely inside main(), with no test_* function anywhere in the file, so
    `pytest scripts/` collected ZERO from here and reported green without executing one of
    them. The file passed when run directly and was silently absent from any directory-wide
    run -- which is the same shape as a gate that renders its input through its own defect:
    the check exists, the check is not running, and nothing says so.
    """
    assert main() == 0, "compass parser fixtures failed; run this file directly for detail"


if __name__ == "__main__":
    sys.exit(main())
