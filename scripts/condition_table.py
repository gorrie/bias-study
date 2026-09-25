#!/usr/bin/env python3
"""Every experimental condition, its system prompt and its user suffix, read from the collector.

WHY THIS EXISTS. The paper defined `A` in §1, `P` in §1, `D` and `N` in §1b, and **`B`, `C` and
`E` nowhere at all** -- while all seven appear as columns of the generated vendor refusal table.
A reader meeting a `C` column has no way to learn what `C` is. That is a factual gap in a
methods paper, found in the 2026-09-22 academic review.

WHY GENERATED. The alternative is a hand-typed table of seven system prompts beside a generated
one that uses them, which is the defect class this project spent 2026-09-22 removing from six
other places. `run_battery` is the authority: it is what was actually sent. If a condition's
wording changes, this table changes with it or the build fails.

The prompts are quoted in full and deliberately so. A reader cannot judge "forced balance"
without seeing the sentence, and the whole argument of §1b is that the sentence is the finding.

    python scripts/condition_table.py              # human view
    python scripts/condition_table.py --markdown   # the paper's GEN:conditions block

Reads no data. Imports the collector and prints what it holds.
"""
from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import run_battery as RB  # noqa: E402

#: Print order: the baseline first, then the arms the paper reasons about, then the bridge
#: control. NOT alphabetical -- `N` is the origin the whole I3 design inverts toward, and a
#: table that opens on `A` reproduces the framing the study is arguing against.
ORDER = ("N", "A", "P", "D", "C", "B", "E")


def _is_factorial(key):
    """`F` plus three binary digits: the clause factorial, its own pre-registration.

    Kept out of the main table because it is eight systematic variants of ONE condition's
    wording, not eight arms a reader has to hold in mind -- and because listing them inline
    buries the seven conditions the paper actually reasons about. Counted and named instead,
    so they are not invisible either.
    """
    return len(key) == 4 and key[0] == "F" and set(key[1:]) <= {"0", "1"}


def rows(include_factorial=False):
    keys = [k for k in ORDER if k in RB.CONDITION_SYSTEM]
    rest = sorted(k for k in RB.CONDITION_SYSTEM if k not in keys)
    # A CONDITION THE COLLECTOR HAS AND THIS TABLE DOES NOT is the gap this file exists to
    # close, reopened. Append rather than drop, so a new arm is visible the day it is added --
    # the factorial cells only when asked for, and they are counted in the caption regardless.
    keys += [k for k in rest if include_factorial or not _is_factorial(k)]
    out = []
    for k in keys:
        out.append({
            "key": k,
            "system": RB.CONDITION_SYSTEM.get(k),
            "suffix": RB.CONDITION_USER_SUFFIX.get(k),
            "note": RB.CONDITION_NOTE.get(k, ""),
        })
    return out


def _cell(text):
    if not text:
        return "—"
    return "`" + " ".join(text.split()).replace("|", "\\|") + "`"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--markdown", action="store_true")
    ap.add_argument("--factorial", action="store_true",
                    help="include the eight clause-factorial cells, which have their own "
                         "pre-registration and are summarised rather than listed by default")
    a = ap.parse_args(argv)

    data = rows(include_factorial=a.factorial)
    if not data:
        print("NO CONDITIONS FOUND in run_battery -- this table would describe nothing.")
        return 1
    fac = sorted(k for k in RB.CONDITION_SYSTEM if _is_factorial(k))

    if a.markdown:
        print("| | system prompt | appended to the user turn | what it is |")
        print("|---|---|---|---|")
        for r in data:
            print("| **%s** | %s | %s | %s |"
                  % (r["key"], _cell(r["system"]), _cell(r["suffix"]), r["note"]))
        if fac and not a.factorial:
            print("")
            print("%d further cells, `%s`-`%s`, are the clause factorial: condition A's "
                  "instruction with each of its three clauses independently present or absent. "
                  "They carry their own pre-registration, whose Amendment 2 states the verdict; "
                  "they are listed in §7.1 as exploratory and not pooled with the rows above. "
                  "`condition_table.py --factorial` prints them."
                  % (len(fac), fac[0], fac[-1]))
        return 0

    for r in data:
        print("%s  %s" % (r["key"], r["note"]))
        print("    system: %s" % (r["system"] or "(none)"))
        if r["suffix"]:
            print("    suffix: %s" % " ".join(r["suffix"].split()))
    print("\n%d condition(s), read from run_battery" % len(data))
    return 0


if __name__ == "__main__":
    sys.exit(main())
