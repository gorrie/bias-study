#!/usr/bin/env python3
"""Add the four controls this project's own 2026-09-05 work identified, to the audit matrix.

WHY THESE FOUR, AND WHY NOW
---------------------------
The nine existing controls were derived from defects found in other people's studies and in
ours. Four days of work on the scoring layer and the time axis surfaced four more, and each was
found by failing it ourselves:

  judge_free_scoring      Is there a model anywhere in the scoring path? Ours has BOTH arms --
                          the forced-choice barometer has no model in it, the May scored study
                          has a four-model panel -- which is exactly why the distinction needs
                          to be a column rather than a sentence.
  judge_lean_reported     Does the study report the scoring layer's OWN lean? We could compute
                          ours from data retained since May and never had: 0.29 points between
                          the most skeptical and most deferential judge, larger than two of our
                          five published effects.
  self_judging_disclosed  Is any subject also a judge, and is it said out loud? Two of our five
                          CI-clean findings are self-judged and nothing disclosed it until
                          2026-09-05.
  longitudinal            Repeat measurement of the same subject over CALENDAR TIME, as opposed
                          to a cross-section of versions taken at one instant. Our whole
                          forced-choice corpus spans six days; `runs/2026-08-31-lineage` is 137
                          models measured on one date and is a version cross-section, not a
                          series. We failed this completely until the wave harness.

THE EXTERNAL STUDIES ARE SCORED `unknown`, DELIBERATELY
-------------------------------------------------------
`controls_audit.py --strict` enforces that every `no` verdict is sourced from a paper actually
read, and the file's own README says a record may not be cited as a claim about what a study
did until its provenance supports it. Adding four columns and filling them in for twelve papers
from memory or inference would be precisely the defect this audit exists to document, committed
in the audit itself.

So every external study gets `unknown` plus a note naming what a re-read would have to
establish. That is an honest empty cell and a piece of scheduled work, not a verdict.

    python scripts/add_controls_2026_09.py --apply
"""
from __future__ import annotations

import argparse
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
AUDIT = os.path.join(STUDY, "data", "controls-audit.json")

NEW_CONTROLS = {
    "judge_free_scoring": "No language model anywhere in the scoring path -- answers are "
                          "recorded mechanically (forced choice, item id + position) rather "
                          "than read and rated by a model. A judged score inherits the judge's "
                          "lean; a mechanical one cannot.",
    "judge_lean_reported": "If a model DOES score the responses, the study reports that "
                           "scoring layer's own lean as a magnitude -- per-judge deviation, or "
                           "an equivalent -- rather than asserting agreement and stopping.",
    "self_judging_disclosed": "No subject of the study also sits on the panel that scores it, "
                              "or if one does, the study says so. n/a where scoring is "
                              "judge-free.",
    "longitudinal": "The same subject re-measured over CALENDAR TIME under held parameters. A "
                    "cross-section of successive versions measured on one date is not this, "
                    "however many versions it spans.",
}

OURS = {
    "judge_free_scoring": ("yes", None),
    "judge_lean_reported": ("yes",
                            "Added 2026-09-05 and it was absent before: scripts/judge_lean.py "
                            "over 4,744 scored records gives a per-judge spread of 0.29 points "
                            "(gemini-2.5-flash +0.173 to deepseek-v3.2 -0.119), larger than two "
                            "of the five effects this project published. Rank order is "
                            "identical under both conditions, so the lean is a main effect and "
                            "cancels in the within-model deltas; absolute scores it does not."),
    "self_judging_disclosed": ("yes",
                               "Disclosed 2026-09-05, having gone unsaid since May. Two of five "
                               "CI-clean findings are self-judged: openai/gpt-4.1 (+0.433) and "
                               "deepseek/deepseek-v3.2 (+0.233) both sat on the four-model panel "
                               "that scored them."),
    "longitudinal": ("partial",
                     "PARTIAL and generously so. The forced-choice corpus spans 2026-08-30 to "
                     "2026-09-05 -- six days -- and runs/2026-08-31-lineage is 137 models "
                     "measured on ONE date, a version cross-section rather than a series. A "
                     "fixed 31-model panel with frozen parameters exists as of 2026-09-05 "
                     "(scripts/wave.py) and wave 0 is declared, but one wave is a baseline, not "
                     "a series. This becomes `yes` at wave 2 and not before."),
}

UNKNOWN_NOTE = {
    "judge_free_scoring": "Not established from the material read. A re-read must say whether "
                          "responses were recorded mechanically or rated by a model.",
    "judge_lean_reported": "Not established. Only applies where a model does the scoring; a "
                           "re-read must first settle judge_free_scoring.",
    "self_judging_disclosed": "Not established. A re-read must check whether any subject model "
                              "also appears in the scoring apparatus.",
    "longitudinal": "Not established. Several of these studies span model VERSIONS, which is "
                    "not the same control; a re-read must establish whether any subject was "
                    "re-measured on a later date under held parameters.",
}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)

    rec = json.load(io.open(AUDIT, encoding="utf-8"))
    added = [k for k in NEW_CONTROLS if k not in rec["controls"]]
    rec["controls"].update(NEW_CONTROLS)

    for study in rec["studies"]:
        sid = study.get("id")
        study.setdefault("status", {})
        study.setdefault("notes", {})
        for control in NEW_CONTROLS:
            if control in study["status"]:
                continue
            if sid == "ours":
                verdict, note = OURS[control]
                study["status"][control] = verdict
                if note:
                    study["notes"][control] = note
            else:
                study["status"][control] = "unknown"
                study["notes"][control] = UNKNOWN_NOTE[control]

    print("controls added: %s" % (", ".join(added) or "(none new)"))
    print("studies updated: %d" % len(rec["studies"]))
    if not args.apply:
        print("DRY RUN -- pass --apply to write")
        return 0
    with io.open(AUDIT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rec, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print("wrote %s" % os.path.relpath(AUDIT, STUDY))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
