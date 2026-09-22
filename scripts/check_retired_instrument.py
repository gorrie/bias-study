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

# MODULE LEVEL, not inside the function that uses it. A local import is exercised only on the
# path that reaches it, so a missing name surfaces at runtime rather than at import --
# tests/test_schema_name.py enforces that and caught this on 2026-09-22. Guarded because this
# gate must still run in a tree where studypaths is absent; it then reports nothing about the
# live corpus rather than crashing, and the vacuity check below says so.
sys.path.insert(0, HERE)
import studypaths as _SP  # noqa: E402

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

#: THE RETIRED INSTRUMENT'S LENGTH, which leaks as a bare number long after its NAME is gone.
#:
#: The markers above are instrument names, and they are the easy half: a name is conspicuous
#: and a search finds it. The number is not. On 2026-09-20 §6 of the paper read *"the same
#: prompt returns the same 62 answers every time"* -- describing OUR instrument, which has 32
#: items -- and every gate was green, because no gate was looking for a digit.
#:
#: This study has already paid for that confusion five times: `CORRECTIONS-2026-09-17-power.md`
#: records five withdrawn claims that all came from counting out of 62 on a 32-item bank, and
#: Limitation 1 carries its own note about the same slip in the same paper.
#:
#: A hit is EXPECTED wherever the sentence is about the retired questionnaire or about someone
#: else's instrument -- which is most of them -- so this is not a ban on the digit. It is a
#: requirement that the sentence say which instrument it means. See `_names_the_retired_one`.
#: Filename prefixes that make a document a DATED RECORD rather than a live claim. A design
#: note, a correction, a prereg or a results document written while the instrument was 62 items
#: is *supposed* to say 62 -- editing it to say 32 would falsify the record of what was
#: designed, measured and corrected, which is the same offence as rewriting a third-party
#: title to clear a grep.
#:
#: The first version of this check scanned everything and produced 165 hits, nearly all of them
#: correct history. A gate that noisy is a gate somebody silences wholesale, so the numeric
#: pass runs only where a 62 would be a claim about the CURRENT instrument.
#: SO IT IS A WHITELIST. A blacklist of dated-record prefixes was the first attempt and it left
#: 121 hits -- FINDINGS.md, SCRIPTS.md, RUBRIC-SCORES.md, THESIS-STATE, OUTREACH, SPEC, REVIEW,
#: each needing its own exception, each one a chance to rot back into noise. The set of
#: documents where a bare 62 is a LIVE CLAIM ABOUT THIS INSTRUMENT is small, knowable and
#: unlikely to grow: what ships, and what directs the work. Everything else in this tree is a
#: record of a study that had 62 items, and it is supposed to say so.
NUMERIC_SURFACES = (
    "PAPER-below-the-floor.md",
    "README.md",
    "CITATION.cff",
    "PLAN.md",
)

NUMERIC_MARKERS = (
    (r"\b62\s+(?:answers?|items?|propositions?|questions?|statements?)\b",
     "a 62-length claim -- this instrument has 32 items"),
    (r"\b(?:of|out of)\s+62\b",
     "a denominator of 62 -- this instrument has 32 items"),
)

#: Words that make a 62 legitimate: the sentence is about the retired bank, or about a cited
#: study's own instrument. Matched in the SAME SENTENCE, in either direction -- unlike the
#: historical test in `multiple_comparisons`, which requires the marker to precede the figure,
#: because here the qualifier reads naturally on both sides ("13 items of 62 on the retired
#: questionnaire" and "the retired questionnaire's 62 items" are both fine).
CONTEXT_WORDS = (
    "retired", "withdrawn", "superseded", "previous", "former", "old ", "until",
    "political compass", "compass", "questionnaire", "i3", "60-item",
    # A citation in the sentence: someone else's instrument, reported as they reported it.
    "et al", "röttger", "rottger", "liu", "rozado", "kamal", "motoki", "sakhawat",
    "dominguez", "their own", "they measured", "theirs",
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
    "LEARNINGS.md":
        "the rule file. Entry 88 names the withdrawn i3 bank and its unsigned read sheet "
        "because the lesson IS that those two files were deleted and had to be restored -- "
        "a rule that cannot name what went wrong is an anecdote. No entry here proposes "
        "using any of them; they are named as evidence, past tense.",

    # 2026-09-21: two entries removed, their files no longer match.

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

    # ---- dated records of what happened. Editing these falsifies the record ----
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
    # README.md WAS ALLOWED HERE UNTIL 2026-09-21 and no longer needs to be. The mirror's
    # README was rewritten and its archive section now names the instrument beside every
    # count -- "a count out of the retired questionnaire's 62 propositions is not a count
    # out of this battery's 32 items" -- which is what the numeric pass wants and what an
    # allowlist entry could never have given it, since that pass deliberately ignores
    # ALLOWED. An exemption removed by fixing the sentence is the outcome this gate is for.
    "prereg/PREREG-2026-09-14-i3-phase4.md":
        "a dated pre-registration whose own opening amendment records that the bank it "
        "names was WITHDRAWN -- written by an assistant session, never signed off, and "
        "quarantined under withdrawn/i3/, then purged with the rest of the retired corpus "
        "on 2026-09-22. The name has to stay so the withdrawal is legible.",
    "prereg/PREREG-2026-09-18-paraphrase.md":
        "quotes Roettger et al.'s published figures ('14 of 62 and 23 of 62 on the Political "
        "Compass') to state what this arm compares against. A citation to somebody else's "
        "instrument, which is the case ALLOWED exists for.",
    "PRIOR-WORK-CORRECTIONS.md":
        "corrections issued to OTHER people's published work, each naming the instrument "
        "that work used.",
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


def _names_the_retired_one(text, start, end):
    """Does this sentence say which instrument it means?

    A 62 is fine when the sentence is about the retired questionnaire or about a cited study's
    own instrument, and most of them are. It is a defect only when the sentence reads as a
    claim about THIS instrument, which has 32 items. So the test is not "is the digit here"
    but "does the surrounding sentence disambiguate".
    """
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    line_end = len(text) if line_end < 0 else line_end
    line = text[line_start:line_end]

    # QUOTED IS NOT ASSERTED. A figure inside quotation marks is being reported -- somebody
    # else's sentence, or our own being corrected. This file's own PLAN entry quotes the
    # defect it fixed ("the same prompt returns the same 62 answers every time") and tripped
    # the gate on the record of the repair, which is the same self-reference that made
    # `run_inventory` certify a directory its comments warned about.
    rel_start = start - line_start
    for open_q, close_q in (('"', '"'), ("“", "”"), ("*", "*")):
        before = line.count(open_q, 0, rel_start)
        if open_q == close_q:
            if before % 2 == 1:
                return True
        elif before > line.count(close_q, 0, rel_start):
            return True

    lo = max(text.rfind(". ", 0, start), text.rfind("\n", 0, start),
             text.rfind("> ", 0, start)) + 1
    hi = text.find(". ", end)
    hi = len(text) if hi < 0 else hi
    sentence = text[lo:hi].lower()
    return any(w in sentence for w in CONTEXT_WORDS)


def scan():
    """-> (hits, n_files, n_allowed_used). A hit is (rel_path, lineno, line)."""
    pattern = re.compile("|".join(re.escape(m) for m in RETIRED_MARKERS), re.IGNORECASE)
    numeric = [(re.compile(p, re.IGNORECASE), why) for p, why in NUMERIC_MARKERS]
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

        # THE NUMERIC PASS IS NOT COVERED BY `ALLOWED`, deliberately. That allowlist exempts a
        # whole file because its BIBLIOGRAPHY cites other people's instruments by name -- and
        # that blanket exemption is exactly how "the same prompt returns the same 62 answers"
        # sat in the paper's own prose with the gate green. A file may be allowed to NAME the
        # retired instrument and still not be allowed to silently count out of it.
        if os.path.basename(rel) not in NUMERIC_SURFACES:
            continue
        for rx, why in numeric:
            for m in rx.finditer(text):
                if _names_the_retired_one(text, m.start(), m.end()):
                    continue
                lineno = text[:m.start()].count("\n") + 1
                line = text.splitlines()[lineno - 1].strip()[:120]
                hits.append((rel, lineno, "%s -- %s" % (line, why)))
    return hits, n_files, allowed_used


#: Scripts that have ever lived under `withdrawn/`. Generated once from git history by
#: `git log --all --diff-filter=A --name-only -- withdrawn/`, filtered to `.py`, and written
#: here so the control SURVIVES the quarantine directory being deleted from the working tree.
#:
#: Data records are deliberately not listed. A withdrawn run and a live one hold files with the
#: same basename -- `anthropic__claude-opus-4.6__A.jsonl` exists in both -- so matching records
#: by name would flag the live corpus. The poisoning this guards against happens in CODE, which
#: is what the docstring above already says: "It came back as NAMES, and a name in a default is
#: one missing argument away from being data again."
QUARANTINED_SCRIPTS = {
    "build_item_bank.py",
    "fetch_items.py",
    "logit_probe.py",
    "test_item_bank.py",
}


def _retired_data_in_the_live_root():
    """No record in the LIVE `runs/` root may carry a retired instrument.

    THE SECOND ONE-WAY BOUNDARY, and it was open for the same reason as the first. `runs` is in
    SKIP_DIRS above -- put there because the name scan would read 6,000 answer sheets looking
    for prose -- so this gate's claim, in its own opening docstring, that "no record under
    `runs/` has carried a retired instrument since 2026-09-16" was an assertion and not a
    check. A top-up into a live directory is one wrong `--instrument` flag away, and the
    collector's own guard is the only thing between here and there.

    `data/` is exempt and must be: it IS the archived judge-scored corpus, it is declared as
    such in the README and the data dictionary, and flagging it would make this permanently red
    for holding what it exists to hold. The live root is the one where a retired record would
    be a new fact rather than a kept one.
    """
    import glob as _glob
    import json as _json
    live = [r for r in _SP.run_roots() if os.path.basename(str(r)) == "runs"]
    out, seen = [], 0
    for root in live:
        for p in _glob.glob(os.path.join(str(root), "**", "*.jsonl"), recursive=True):
            for line in io.open(p, encoding="utf-8", errors="replace"):
                line = line.strip()
                if not line:
                    continue
                seen += 1
                try:
                    rec = _json.loads(line)
                except ValueError:
                    continue
                blob = "%s %s" % (rec.get("schema") or "", rec.get("instrument") or "")
                low = blob.lower()
                if low.startswith("compass") or any(m in low for m in RETIRED_MARKERS):
                    out.append((os.path.relpath(p, STUDY), 0,
                                "RETIRED INSTRUMENT IN THE LIVE CORPUS: a record declares %r. "
                                "runs/ is where the paper's figures come from." % blob.strip()))
                    break
    # A SCAN THAT OPENED NOTHING MUST NOT REPORT CLEAN -- the same house rule the file already
    # applies to its prose walk. Zero records here means the resolver missed the corpus.
    if live and not seen:
        out.append(("runs/", 0, "CHECKED NOTHING -- the live run root resolved to no records. "
                                "That is not a pass; check run_roots()."))
    return out


def _resurrected_from_quarantine():
    """A file that was withdrawn must not reappear in a live path.

    THE GAP THIS CLOSES, and it is one this gate had. `withdrawn/` is in SKIP_DIRS by design --
    it is the quarantine, and scanning it would flag the thing it exists to hold. But that made
    the boundary one-way: the gate refuses a retired instrument NAME anywhere in the live tree,
    and says nothing about a retired FILE being copied out of quarantine into `scripts/`.

    On 2026-09-22 exactly that happened. `logit_probe.py` was lifted out of
    `withdrawn/compass-bank/scripts/` into `scripts/` to satisfy the named-scripts gate, which
    was complaining that three shipped documents named a file that no longer existed. Moving
    retired material into live tooling to quiet a check is the wrong direction, and the
    compass references inside it were repointed at the live bank on the way -- which made it
    INVISIBLE to the name scan above. A control that can be defeated by tidying is not a
    control.

    The correct fix for that gate was the other one: the documents describe the retired tool
    without a backticked path, because a reader following one gets nothing.
    """
    out = []
    for name in sorted(QUARANTINED_SCRIPTS):
        for d in ("scripts", "."):
            p = os.path.join(STUDY, d, name)
            if os.path.isfile(p):
                out.append((os.path.relpath(p, STUDY), 0,
                            "RESURRECTED FROM QUARANTINE: this file was withdrawn and is "
                            "live again. If a gate is asking for it, the gate wants the "
                            "DOCUMENT changed, not the file restored."))
    return out


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
    hits += _resurrected_from_quarantine()
    hits += _retired_data_in_the_live_root()

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
