#!/usr/bin/env python3
"""Refuse a tree that has readopted a retired instrument, anywhere, under any name.

WHY THIS EXISTS
---------------
The study's instrument is `data/ratchet-battery.json` -- 32 items in 16 mirrored pairs,
written by the author. Two other instruments were administered before it and both are
withdrawn: a 62-item external questionnaire, and a 60-item bank an assistant generated and
substituted for the author's without his sentences ever being read.

Both were purged. Both came back, in code, twice -- as a default in an analysis path, as a
constant naming the retired bank, as a gate pointed at a withdrawn file, as help text telling
a reader the retired bank was the live instrument. Not as data: no record under `runs/` has
carried a retired instrument since 2026-09-16. It came back as NAMES, and a name in a default
is one missing argument away from being data again.

A promise not to do it again is not a control. This is the control: it fails.

WHAT IT REFUSES
---------------
Any occurrence, in the live tree, of a string that identifies a retired instrument -- except
at a site declared below as a citation to somebody else's published work. This study cites
papers that administered those instruments, and rewriting a third-party title to satisfy a
grep is falsification. That happened here too, on 2026-09-16: a blind find-and-replace across
191 files rewrote the titles of two published papers, ~121 mangled references, which is worse
than the problem it was solving.

So the allowlist is per FILE with a reason, it is short, and every entry names work that is
not ours.

    python scripts/check_retired_instrument.py            # exit 1 on any undeclared hit
    python scripts/check_retired_instrument.py --list     # show the allowlist and exit 0
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)

#: Strings that identify a retired instrument. Matched case-insensitively.
#:
#: `compass-run` is deliberately NOT here: it is the record SCHEMA name, carried by every sheet
#: this study has ever written including the 702 on the author's battery, and renaming a schema
#: rewrites history rather than removing an instrument. It is tracked in BACKLOG instead.
RETIRED_MARKERS = (
    "politicalcompass",
    "political compass",
    "ratchet-propositions-i3",
    "ratchet-battery-i3",
)

#: Directories that hold withdrawn material by design. Their whole purpose is to keep what was
#: retired, so scanning them would make the gate permanently red for doing its job.
SKIP_DIRS = {"withdrawn", "export", ".git", "__pycache__", ".pytest_cache",
             "abliteration-output", "node_modules", "runs"}

#: Files that may name a retired instrument, each because it cites work that is NOT OURS.
#:
#: A third-party title, an author's method, or a finding someone else published about an
#: instrument is a citation. It stays exactly as published. Adding an entry here is a
#: deliberate act and should be rare; removing one is free.
ALLOWED = {
    "scripts/rederive_liu.py":
        "re-derives Liu, Panwang and Gu (2025) from their deposited data. Naming the "
        "instrument THEY administered is what makes the re-derivation checkable.",
    "scripts/replicate_rottger.py":
        "replicates Roettger et al. Their paper's TITLE contains the instrument's name; a "
        "find-and-replace mangled it once already and that is falsification, not hygiene.",
    "scripts/evidence_concordance.py":
        "cites Peereboom et al. (arXiv:2409.15324) on the instrument's lack of validation -- "
        "a third-party finding ABOUT it, which is evidence for retiring it.",
    "scripts/check_retired_instrument.py":
        "this file. The markers have to be written down somewhere to be searched for.",

    # ---- literature and bibliography: other people's instruments, in their titles ----
    "LITERATURE-2026-08-29-position-measurement.md":
        "a survey of twelve published studies, each row naming the instrument THAT study "
        "administered. Every hit is a third-party title or method.",
    "LITERATURE-2026-08-31-noise-floor-controls.md":
        "as above -- what other people controlled for, and on what.",
    "PAPER-below-the-floor.md":
        "its BIBLIOGRAPHY describes each cited study's instrument (Kamal, Roettger, Rozado, "
        "Wright, Bucan). The paper's statement of ITS OWN instrument was corrected on "
        "2026-09-17 and names the author's battery; the remaining hits are citations and a "
        "dated changelog line recording the swap that has since been reversed.",
    "JUDGEMENT-TOOL-PLAN.md":
        "rubric method 8 is defined by anchoring to an external framework's axes. Naming it "
        "is what makes the EXCLUSION of that method reviewable.",

    # ---- dated records of what happened. Editing these falsifies the record ----
    "INCIDENT-2026-09-12-instrument-leak.md":
        "the incident report for a leak OF that instrument's text. An incident record that "
        "does not say what leaked is not a record.",
    "PREREG-2026-08-29-mask-surface-v2.md":
        "a dated pre-registration for a wave collected on the retired instrument. A prereg is "
        "a fixed document; amending it after the fact is the defect it exists to prevent.",
    "PLAN-2026-09-13-I3.md":
        "the dated plan under which the substituted bank was built. Superseded, kept as the "
        "record of a decision that had to be reversed.",
    "BACKLOG-2026-09-01.md":
        "a dated backlog entry about republishing that corpus. Historical.",
    "PREREG-2026-09-14-i3-phase4.md":
        "Amendment 2 records the instrument change itself. A prereg amendment that cannot "
        "name what was replaced documents nothing.",
    "PREREG-2026-09-18-paraphrase.md":
        "names the instrument ROETTGER ET AL. used, twice, because the arm it registers runs "
        "THEIR statistic on OUR bank and the comparison is meaningless without saying what "
        "theirs was measured on. A citation to somebody else's published work, not a default, "
        "a constant or a path. Rewriting it to clear this grep is the 2026-09-16 incident.",
    "RUBRIC-SCORES.md":
        "scores rubric method 8, which is defined by anchoring to an external framework. "
        "Naming it is what makes the exclusion reviewable.",

    # ---- dated RESULTS from the retired instrument. Superseded, not deleted ----
    "RESULTS-2026-08-29-evidence-concordance.md":
        "a dated result measured on the retired instrument, kept as the record.",
    "RESULTS-2026-08-31-refusal-by-vendor.md": "as above.",
    "RESULTS-2026-08-31-refusal-is-elicited.md": "as above.",
    "RESULTS-2026-09-05-frontier-v3.md": "as above.",
    "WHAT-THIS-CHANGES-2026-08-31.md": "as above.",
    "STATUS.md":
        "its one hit is the rubric method-8 exclusion, as in RUBRIC-SCORES.md. NOTE: this "
        "file is stale since 2026-09-12 and predates the instrument correction entirely; it "
        "is to be rewritten or retired (BACKLOG), and this entry goes when it is.",

    # ---- the twelve-study controls audit: every row describes a CITED study's instrument ----
    "data/controls-audit.json":
        "one row per audited external study, each naming the instrument THAT study used. "
        "Rewriting these would falsify the audit.",
    "operations/2026-09-08/claim-review/controls-audit-before.json":
        "the dated before-state of the same audit, kept for the claim review.",
    "data/external/README.md":
        "describes third-party data held under their own terms.",

    # ---- public mirror. Same rules; its paths differ from the private tree's ----
    "README.md":
        "its 2026-08-31 section is explicitly headed 'the instrument below is the PREVIOUS "
        "generation, read this first' and describes what was measured then. The live "
        "instrument statement was corrected on 2026-09-17 and names the author's battery.",
    "PRIOR-WORK-CORRECTIONS.md":
        "corrections issued to OTHER people's published work, each naming the instrument "
        "that work used.",
    "prereg/PREREG-2026-08-29-mask-surface-v2.md":
        "a dated pre-registration for a wave on the retired instrument. Fixed document.",
    "prereg/PREREG-2026-09-12-instrument-choice.md":
        "the dated record of the instrument decision itself. It cannot be written without "
        "naming what was chosen against.",
    "results/RESULTS-2026-08-29-evidence-concordance.md":
        "a dated result measured on the retired instrument, kept as the record.",
    "results/RESULTS-2026-08-31-refusal-is-elicited.md": "as above.",
    "results/RESULTS-2026-09-05-frontier-v3.md": "as above.",
}


#: The other tree. This list is shared between the private study and the public mirror, which
#: hold many of the same paths with different content.
_SIBLINGS = (
    os.path.normpath(os.path.join(STUDY, "..", "..", "..", "bias-study-release")),
    os.path.normpath(os.path.join(STUDY, "..", "evil-robots-series", "research", "bias-study")),
)


def _matches_in_sibling(rel):
    """Does this path still name a retired instrument in the OTHER tree?"""
    pattern = re.compile("|".join(re.escape(m) for m in RETIRED_MARKERS), re.IGNORECASE)
    for sib in _SIBLINGS:
        if not os.path.isdir(sib) or os.path.normpath(sib) == os.path.normpath(STUDY):
            continue
        path = os.path.join(sib, rel)
        if not os.path.exists(path):
            continue
        try:
            if pattern.search(io.open(path, encoding="utf-8", errors="replace").read()):
                return True
        except OSError:
            continue
    return False


def _our_own_audit_row():
    """The one row in the controls audit that is OURS, checked even though the file is allowed.

    THE ALLOWLIST HAD A HOLE SHAPED EXACTLY LIKE THIS ROW. `data/controls-audit.json` is
    allowed wholesale, and correctly: it audits twelve external studies and each row names the
    instrument THAT study administered, which is a citation. But one row -- `id: "ours"` -- is
    this study describing itself, and it named the retired 62-item questionnaire as our
    instrument long after it was withdrawn. A file-level exemption cannot tell a citation from
    a self-description, so it waved through the one line that was neither.

    Found by an independent review. The row is also where this study's self-description goes
    public with the audit, which makes it the worst place in the tree for a stale fact: it is
    the record backing the sentence "the same table scores us".
    """
    path = os.path.join(STUDY, "data", "controls-audit.json")
    if not os.path.exists(path):
        return []
    try:
        rec = json.load(io.open(path, encoding="utf-8"))
    except ValueError:
        return []
    studies = rec.get("studies") if isinstance(rec, dict) else rec
    if isinstance(studies, dict):
        studies = [dict(v, id=k) for k, v in studies.items()]
    ours = next((s for s in (studies or []) if (s.get("id") or s.get("key")) == "ours"), None)
    if not ours:
        return [("data/controls-audit.json", 0,
                 "no row keyed 'ours' -- this study's self-description is missing from the "
                 "audit that scores it")]
    pattern = re.compile("|".join(re.escape(m) for m in RETIRED_MARKERS), re.IGNORECASE)
    out = []
    for field in ("instrument", "scale", "headline", "cite"):
        value = str(ours.get(field) or "")
        # The correction note may NAME what the field used to say; that is the record, not a
        # claim. Only text before such a note is checked.
        live = value.split("Until 2026-09-17")[0]
        if pattern.search(live):
            out.append(("data/controls-audit.json [row: ours]", 0,
                        "our OWN audit row's %r names a retired instrument: %s"
                        % (field, live.strip()[:90])))
    return out


def _text_files():
    for root, dirs, files in os.walk(STUDY):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for name in files:
            if not name.endswith((".py", ".md", ".json", ".yaml", ".yml", ".sh", ".cff",
                                  ".toml", ".cfg", ".ini", ".txt")):
                continue
            path = os.path.join(root, name)
            rel = os.path.relpath(path, STUDY).replace("\\", "/")
            yield rel, path


def scan():
    """-> (hits, n_files, n_allowed_used). A hit is (rel_path, lineno, line)."""
    pattern = re.compile("|".join(re.escape(m) for m in RETIRED_MARKERS), re.IGNORECASE)
    hits, n_files, allowed_used = [], 0, set()
    for rel, path in _text_files():
        n_files += 1
        try:
            text = io.open(path, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if not pattern.search(line):
                continue
            if rel in ALLOWED:
                allowed_used.add(rel)
                continue
            hits.append((rel, lineno, line.strip()[:120]))
    return hits, n_files, allowed_used


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--list", action="store_true",
                    help="print the allowlist and the markers, then exit 0")
    a = ap.parse_args(argv)

    if a.list:
        print("RETIRED INSTRUMENT MARKERS (%d):" % len(RETIRED_MARKERS))
        for m in RETIRED_MARKERS:
            print("  %s" % m)
        print("")
        print("ALLOWED, each citing work that is not ours (%d):" % len(ALLOWED))
        for path, why in sorted(ALLOWED.items()):
            print("  %s" % path)
            print("      %s" % why)
        return 0

    hits, n_files, allowed_used = scan()
    hits += _our_own_audit_row()

    # A SCAN THAT OPENED NOTHING MUST NOT REPORT CLEAN. The house rule, and this gate is
    # exactly the kind that would sit green over an empty walk.
    if not n_files:
        print("CHECKED NOTHING -- no files scanned under %s. This is NOT a pass." % STUDY)
        return 2

    # STALE MEANS "THE FILE IS HERE AND NO LONGER MATCHES", not "the file is not here".
    #
    # One allowlist serves both trees -- the private study and the public mirror -- and their
    # layouts differ: the paper and the operations log live only in the private one, the
    # prereg/ and results/ directories only in the mirror. Reporting an entry as stale because
    # the file belongs to the other tree would make the check red in both, which is how a gate
    # gets switched off.
    # AND IT MUST NOT MATCH IN THE SIBLING TREE EITHER. The private study and the public
    # mirror share this list and hold the same paths with different content: the mirror's
    # README carries a dated "the instrument below is the PREVIOUS generation" section that
    # the private one does not. An entry used by one tree and not the other is doing its job,
    # not rotting. Only an entry matching in NEITHER is dead.
    stale = []
    for p in sorted(set(ALLOWED) - allowed_used):
        if p == "scripts/check_retired_instrument.py":
            continue
        here = os.path.join(STUDY, p)
        if not os.path.exists(here):
            continue
        if _matches_in_sibling(p):
            continue
        stale.append(p)

    if hits:
        print("REFUSED -- a retired instrument is named in %d place(s) in the live tree."
              % len(hits))
        print("")
        for rel, lineno, line in hits[:40]:
            print("  %s:%d" % (rel, lineno))
            print("      %s" % line)
        if len(hits) > 40:
            print("  ... and %d more" % (len(hits) - 40))
        print("")
        print("The study's instrument is data/ratchet-battery.json. A retired bank's name in a")
        print("default, a constant or a gate is one missing argument from being data again --")
        print("which is how it returned twice after being purged.")
        print("")
        print("If a hit is a CITATION to somebody else's published work, declare the file in")
        print("ALLOWED with the reason. Never rewrite a third-party title to clear a grep:")
        print("that was done here on 2026-09-16 and mangled ~121 references.")
        return 1

    print("scanned %d file(s) under %s" % (n_files, os.path.basename(STUDY)))
    print("no retired instrument is named outside the %d declared citation site(s)."
          % len(allowed_used))
    for rel in sorted(allowed_used):
        print("  cites others' work: %s" % rel)
    if stale:
        # AN ALLOWLIST ENTRY WITH NOTHING UNDER IT IS AN EXEMPTION WAITING TO BE MISUSED.
        print("")
        print("%d allowlist entry(ies) match nothing any more -- delete them: %s"
              % (len(stale), ", ".join(stale)))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
