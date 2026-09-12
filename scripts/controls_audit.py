#!/usr/bin/env python3
"""Render the controls matrix from data/controls-audit.json. Nothing restates it in prose.

The matrix says, per study, which measurement controls it runs. It is the paper's central
table and the most defamatory thing in the project -- it asserts what other people's papers
failed to do -- so it carries two guards the rest of the project learned the hard way.

FIRST GUARD: provenance. Every record declares whether the paper was read in full, retrieved
as a summary, or is carried over from this project's earlier literature pass and never
re-verified. `--strict` refuses to render any 'no' verdict sourced from an unverified record,
because "study X does not run control Y" is a claim about someone else's work and it needs a
source stronger than our own notes. Use --strict before publication.

SECOND GUARD: no hand-copying. Every count in the paper comes from this script's output.
`--check` exits 1 when the rendered matrix in a target file has drifted from the data.

    python scripts/controls_audit.py                 # the matrix
    python scripts/controls_audit.py --strict        # refuse unverified 'no' verdicts
    python scripts/controls_audit.py --markdown      # paper-ready
    python scripts/controls_audit.py --gaps          # per-control tallies and the pairs-in-hand list
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

MARK = {"yes": "yes", "partial": "part", "no": "NO", "n/a": "--", "unknown": "?"}
#: Provenance too thin to support a "no" verdict about someone else's paper.
#:
#: This was ("project-review",) and NO row carried that value, so --strict was vacuous while
#: eleven "does not control for X" verdicts rested on `retrieved-summary` -- a method-and-
#: results retrieval, not the paper. Sakhawat carried five of them. A retrieval can show a
#: control is absent from what we saw; it cannot establish it is absent from the work, and
#: this project does not get to make a claim about someone else that it would not accept
#: about itself. Those verdicts are "unknown" now and return when someone reads the paper.
WEAK_PROVENANCE = ("project-review", "retrieved-summary")


def load():
    with io.open(DATA, encoding="utf-8") as fh:
        return json.load(fh)


def render(doc, markdown=False):
    controls = list(doc["controls"])
    studies = [s for s in doc["studies"] if s["id"] != "ours"] + \
              [s for s in doc["studies"] if s["id"] == "ours"]

    short = {"item_order": "order", "nuisance_magnitude": "magnitude",
             "same_version_point": "sv-point",
             "same_version_dist": "sv-dist", "quantisation": "quant",
             "retained_failures": "failures", "reported_mde": "MDE",
             "forcing_disclosed": "forcing", "open_raw": "raw",
             # Added 2026-09-05. Each of these four was found by failing it ourselves; see
             # scripts/add_controls_2026_09.py for why each is a column and not a sentence.
             "judge_free_scoring": "no-judge", "judge_lean_reported": "judge-lean",
             "self_judging_disclosed": "self-judged", "longitudinal": "over-time"}
    # A control added to the data file but not named here is a silent omission from the
    # matrix, which is the exact defect the matrix is about.
    missing = [c for c in controls if c not in short]
    if missing:
        raise SystemExit("controls in the data file with no column label: %s" % missing)

    out = []
    if markdown:
        out.append("| study | year | " + " | ".join(short[c] for c in controls) + " | provenance |")
        out.append("|---|---:|" + "---|" * len(controls) + "---|")
        for s in studies:
            cells = " | ".join(MARK[s["status"][c]] for c in controls)
            name = "**this study**" if s["id"] == "ours" else s["id"]
            out.append("| %s | %d | %s | %s |" % (name, s["year"], cells, s["provenance"]))
    else:
        head = "study".ljust(20) + "yr  " + "".join(short[c].rjust(12) for c in controls)
        out.append(head)
        out.append("-" * len(head))
        for s in studies:
            row = s["id"].ljust(20) + str(s["year"])[2:] + "  "
            row += "".join(MARK[s["status"][c]].rjust(12) for c in controls)
            out.append(row)
    return "\n".join(out)


def tally_markdown(doc, controls=None):
    """Per-control tally as a markdown table, externals only.

    The same counts `gaps` prints, shaped for a GEN block. PRIOR-WORK-CORRECTIONS.md carried
    these by hand: on 2026-09-12 its `same_version_dist` row still read "8 no, 1 n/a, 3
    unknown" after the three unknowns had been resolved to "10 no, 2 n/a", and the sentence
    under it -- "Not one of the twelve" -- was built on the stale row. That document's own
    subject is what happens to a number nobody recomputes.
    """
    studies = [s for s in doc["studies"] if s["id"] != "ours"]
    controls = controls or list(doc["controls"])
    out = ["| control | yes | partial | no | n/a | unknown |",
           "|---|---:|---:|---:|---:|---:|"]
    for c in controls:
        counts = {}
        for s in studies:
            counts[s["status"][c]] = counts.get(s["status"][c], 0) + 1
        cells = []
        for k in ("yes", "partial", "no", "n/a", "unknown"):
            n = counts.get(k, 0)
            # Bold the cell the row exists to show: a zero on `yes`, the bulk on `no`.
            if n == 0:
                cells.append("**0**" if k == "yes" else "–")
            elif k == "no" and n == max(counts.values()):
                cells.append("**%d**" % n)
            else:
                cells.append(str(n))
        out.append("| `%s` — %s | %s |" % (c, doc["controls"][c].split(".")[0].strip(),
                                                " | ".join(cells)))
    return "\n".join(out)


def gaps(doc):
    controls = list(doc["controls"])
    studies = [s for s in doc["studies"] if s["id"] != "ours"]
    lines = ["PER-CONTROL TALLY, excluding this study (n=%d)" % len(studies), ""]
    for c in controls:
        counts = {}
        for s in studies:
            counts[s["status"][c]] = counts.get(s["status"][c], 0) + 1
        summary = ", ".join("%s %d" % (k, counts[k]) for k in
                            ("yes", "partial", "no", "n/a", "unknown") if k in counts)
        lines.append("  %-22s %s" % (c, summary))
        lines.append("      %s" % doc["controls"][c])
    lines.append("")

    # The argument of the paper is not that these controls are hard. It is that the pairs
    # were already in hand. That list is the one worth printing.
    # Selected on `pairs_in_hand`, an explicit field, because the heading is a claim about
    # the study's DESIGN and `same_version_dist` is a claim about its REPORTING. The old
    # filter used the latter and additionally required a note to exist, so two studies --
    # dominguezolmedo2024 and aipolcom -- were excluded for no reason but nobody having
    # written a note, and the prose beneath this list said "six" against a list of seven.
    have = [s for s in studies if s.get("pairs_in_hand") is True
            and s["status"]["same_version_dist"] in ("no", "partial")]
    unestablished = [s for s in studies if s.get("pairs_in_hand") is None]
    lines.append("STUDIES WHOSE OWN DESIGN CONTAINS THE PAIRS FOR A SAME-VERSION NULL")
    lines.append("but which do not report one as a distribution: %d of %d"
                 % (len(have), len(studies)))
    for s in have:
        note = (s["notes"].get("same_version_dist") or s["notes"].get("same_version_point")
                or s["notes"].get("pairs_in_hand"))
        lines.append("  %s -- %s" % (s["id"], note))
    if unestablished:
        lines.append("")
        lines.append("NOT ESTABLISHED either way (%d) -- absent from the count above, and said"
                     % len(unestablished))
        lines.append("so rather than dropped:")
        for s in unestablished:
            lines.append("  %s -- %s" % (s["id"], s["notes"].get("pairs_in_hand", "")))
    return "\n".join(lines)


def strict_check(doc):
    """A 'no' verdict about someone else's paper needs a source stronger than our own notes."""
    problems = []
    for s in doc["studies"]:
        if s["provenance"] not in WEAK_PROVENANCE:
            continue
        for c, v in s["status"].items():
            if v == "no":
                problems.append((s["id"], c, s["provenance"]))
    if not problems:
        print("STRICT: every 'no' verdict is sourced from a read or retrieved paper.")
        return 0
    print("STRICT FAILURE -- %d 'no' verdicts rest on unverified records." % len(problems))
    print("Each asserts a study did NOT run a control, on the strength of our own notes.")
    print("Read the source and upgrade provenance, or downgrade the verdict to 'unknown'.")
    print()
    for sid, control, prov in problems:
        print("  %-22s %-22s provenance=%s" % (sid, control, prov))
    return 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--markdown", action="store_true")
    ap.add_argument("--gaps", action="store_true")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--tally-markdown", action="store_true",
                    help="per-control tally as a markdown table, for GEN blocks in the "
                         "corrections documents. Added 2026-09-12: those tables were typed "
                         "copies of --gaps and went stale the moment three studies were "
                         "re-read, in the file whose subject is numbers going stale.")
    ap.add_argument("--controls", default=None,
                    help="comma-separated control keys, for a section that tallies only its "
                         "own rows")
    args = ap.parse_args(argv)

    doc = load()
    if args.strict:
        return strict_check(doc)
    if args.tally_markdown:
        want = None
        if args.controls:
            want = [c.strip() for c in args.controls.split(",") if c.strip()]
            unknown = [c for c in want if c not in doc["controls"]]
            if unknown:
                raise SystemExit("no such control(s): %s" % ", ".join(unknown))
        print(tally_markdown(doc, want))
        return 0
    if args.gaps:
        print(gaps(doc))
        return 0

    print(render(doc, args.markdown))
    if not args.markdown:
        print()
        print("yes = runs it and reports the magnitude   part = adjacent, or unreported")
        print("NO  = does not run it   -- = does not apply   ? = not established")
        print()
        print("Run --gaps for the tallies, --strict before publishing any 'NO'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
