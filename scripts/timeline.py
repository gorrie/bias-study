#!/usr/bin/env python3
"""Generate the field timeline from data/controls-audit.json. The sequence is the argument.

A year column shows that Röttger is 2024 and Sakhawat is 2026. A date column shows that
Röttger's warning — with item-level magnitudes on this exact instrument, and an explicit plea
to estimate the extent of instabilities — was readable on arXiv in February 2024, and that
every study in this audit published after that date still does not run the control.

That is not a claim about anyone's diligence. It is a fact about uptake, and it is the reason
this project's contribution is a decision rule rather than a discovery: the discovery was
already made and did not take.

Two dates are kept per study because they differ by up to eighteen months:

  first_public   earliest date anyone could read it, preprint included. This is the date that
                 matters for whether a later study had the chance to act on it.
  of_record      the citable venue date, where there is one.

Conflating them would misstate who could have known what, in a document whose whole point is
who knew what when.

    python scripts/timeline.py
    python scripts/timeline.py --markdown
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
DATA = os.path.join(STUDY, "data", "controls-audit.json")

# The control whose uptake the timeline is tracking.
WATCHED = ("nuisance_magnitude", "same_version_dist", "reported_mde")
LABEL = {"nuisance_magnitude": "reports a nuisance magnitude",
         "same_version_dist": "reports a same-version null as a distribution",
         "reported_mde": "reports a detection limit"}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--markdown", action="store_true")
    args = ap.parse_args(argv)

    doc = json.load(io.open(DATA, encoding="utf-8"))
    rows = []
    for s in doc["studies"]:
        if not s.get("first_public"):
            continue
        marks = []
        for c in WATCHED:
            v = s["status"].get(c)
            marks.append({"yes": "Y", "partial": "~", "no": "-", "n/a": ".",
                          "unknown": "?"}.get(v, "?"))
        rows.append((s["first_public"], s["id"], "".join(marks),
                     s.get("date_note", ""), s.get("headline", "")))
    for c in doc.get("timeline_context", []):
        rows.append((c["date"], "", "", "", c["event"]))
    rows.sort()

    if args.markdown:
        print("| first public | study | mag | null | MDE | what it is |")
        print("|---|---|:-:|:-:|:-:|---|")
        for date, sid, marks, note, head in rows:
            m = list(marks) if marks else ["", "", ""]
            print("| %s | %s | %s | %s | %s | %s |"
                  % (date, "**%s**" % sid if sid else "—",
                     m[0], m[1], m[2], (head or note)[:96]))
        return 0

    print("FIELD TIMELINE — generated from data/controls-audit.json")
    print("columns: reports a nuisance magnitude / a same-version null distribution / a detection limit")
    print("Y = yes   ~ = partial   - = no   . = not applicable   ? = not established")
    print()
    for date, sid, marks, note, head in rows:
        if sid:
            print("%-11s  %-3s  %-20s %s" % (date, marks, sid, note))
        else:
            print("%-11s  %-3s  %-20s %s" % (date, "", "", head))
    print()
    watched = [r for r in rows if r[1]]
    after = [r for r in watched if r[0] > "2024-02-26" and r[1] != "ours"]
    dist = sum(1 for r in after if r[2][1] == "Y")
    print("Studies first public AFTER Röttger's 2024-02-26 warning: %d" % len(after))
    print("  of those, reporting a same-version null as a distribution: %d" % dist)
    print()
    print("The warning was available to every one of them. The control is cheap and in most")
    print("cases the pairs were already in their own model tables. Uptake is the finding.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
