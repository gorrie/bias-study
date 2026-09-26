#!/usr/bin/env python3
"""A withdrawal is a STATE, not an event. Check that every one of them still holds.

WHY THIS EXISTS
---------------
Writing the withdrawal down was being mistaken for doing it. Measured 2026-09-22, all in one
tree that believed itself clean:

  * The retired 62-item questionnaire was purged twice and came back twice -- commit
    42133649's own title. A retired collector was later lifted out of quarantine into
    `scripts/` to quiet the named-scripts gate.
  * The five published nulls were withdrawn on 2026-09-18 and were still asserted on
    2026-09-22 on the live research page and on pushed GitHub, because not one phrase for
    them had ever been registered. `--check-release` was green the whole time.
  * `CORRECTIONS-2026-09-17-power.md` is cited TEN times inside the public mirror -- three of
    them in the paper -- and is not in the mirror. A reader following the citation gets
    nothing.
  * The evidence for two withdrawals was deleted outright, on the strength of the directory it
    sat in, and had to be restored from git.

Those are four different failures and they share one cause: nothing owned the invariant. Each
was patched where it surfaced, by hand, and the patch taught nobody anything. `RETRACTED` grew
a phrase, `SKIP_DIRS` grew an entry, a banner went on one file.

THE INVARIANT, and each clause is a defect this project actually paid for:

  1. ABSENT      -- none of the claim's phrases appears on a live surface. (`key_numbers`
                    does this; the phrases now come from the registry rather than a second
                    hand-maintained list.)
  2. REACHABLE   -- the dated record that withdrew the claim exists in every tree that cites
                    it. Ten dangling citations in the shipping mirror.
  3. LEDGERED    -- if the claim was ever PUSHED, the public ledger carries a numbered entry.
                    "Published" means pushed: `git merge-base --is-ancestor`. Committed is not
                    published, and unpushed is not unwritten.
  4. EVIDENCED   -- the files that justify the withdrawal still exist. Deleting them leaves a
                    claim about a claim, which is what the paper convicts other people of.
  5. LABELLED    -- every run named as evidence carries a non-`active` status in its
                    root's PROVENANCE.json. The four clauses above govern claims on
                    SURFACES; none of them reaches the records. `data/2026-09-13-i3-phase0`
                    ships, its manifest reads as a clean success -- 1,600 calls, 0 failed --
                    and its B-A contrast is withdrawn. A stranger can compute and publish a
                    withdrawn result from our release without doing one thing wrong.

Registry: `data/withdrawals.json`. It is THE copy. This gate reads it; `key_numbers.RETRACTED`
is generated from it. Adding a withdrawal means adding it there and nowhere else.

    python scripts/check_withdrawals.py             # exit 1 on any broken clause
    python scripts/check_withdrawals.py --owed      # only the public entries not yet written
    python scripts/check_withdrawals.py --phrases   # what key_numbers should ban

Exit 0 every clause holds, 1 a defect, 2 NOT APPLICABLE (no registry in this tree).
"""
from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
REGISTRY = os.path.join(STUDY, "data", "withdrawals.json")

#: Where each named tree lives, resolved from here. `mirror` is the public GitHub checkout.
#: Resolved by walking up rather than hardcoding a depth, because this gate runs FROM both
#: trees and a fixed `../../../` points above the mirror at nothing -- the defect
#: `release_check.MIRROR` carries its own comment about.
#: True when THIS checkout is the public mirror, decided by CONTENT rather than by directory
#: name.
#:
#: The first version tested `os.path.basename(STUDY) == "bias-study-release"`, which is true
#: of this machine and of nothing a reader has. Cloned into any other directory name -- which
#: is what `git clone <url> <dir>` does, and what a reviewer unpacking a Zenodo archive gets --
#: the mirror identified itself as the private study, so the evidence clause looked for
#: `withdrawn/` corpora that are deliberately not published and reported two deletions that had
#: not happened. Verified 2026-09-23 by running the gate in a copy outside the workspace.
#:
#: `PLAN.md` is the private queue and is not published; `CORRECTIONS.md` is the public ledger
#: and is not in the private tree. Either one alone settles it, and requiring both to agree
#: means a tree that somehow has both, or neither, says so instead of guessing.
def _identify():
    plan = os.path.exists(os.path.join(STUDY, "PLAN.md"))
    ledger = os.path.exists(os.path.join(STUDY, "CORRECTIONS.md"))
    if ledger and not plan:
        return True          # the public mirror
    if plan and not ledger:
        return False         # the private study
    return None              # ambiguous: neither clause may assume which tree this is


IS_MIRROR = _identify()
IN_MIRROR = IS_MIRROR is True


def _tree(name):
    """The root of the named tree, or None when it is not present here.

    RESOLVING "study" TO WHATEVER TREE THIS RUNS FROM IS A BUG, and the first version of this
    gate had it: run from the mirror, `_tree("study")` returned the mirror, so every clause
    scoped to the private tree was silently evaluated against the public one and reported ten
    defects that were not defects. `release_check.MIRROR` carries a comment about the same
    conflation in the other direction. Returning None is the honest answer, and every caller
    has to say NOT APPLICABLE rather than pass.
    """
    if IS_MIRROR is None:
        # WHICH TREE THIS IS COULD NOT BE ESTABLISHED, so no clause may assume. Returning
        # None makes every tree-scoped check report NOT APPLICABLE, which is the honest
        # answer and is what the caller prints.
        return None
    if name == "study":
        if not IN_MIRROR:
            return STUDY
        # From the mirror, the private tree may or may not be on this machine.
        probe = os.path.dirname(STUDY)
        for _ in range(4):
            cand = os.path.join(probe, "evil-robots-series", "research", "bias-study")
            if os.path.isdir(cand):
                return cand
            parent = os.path.dirname(probe)
            if parent == probe:
                break
            probe = parent
        return None
    if name == "mirror":
        if IN_MIRROR:
            return STUDY
        probe = STUDY
        for _ in range(6):
            parent = os.path.dirname(probe)
            if parent == probe:
                break
            probe = parent
            cand = os.path.join(probe, "bias-study-release")
            if os.path.isdir(cand):
                return cand
        return None
    return None


def _elsewhere(study, rel):
    """A corpus path that MOVED ROOTS still points at the same records.

    The registry stores `runs/2026-09-13-i3-phase0`, and on 2026-09-23 that run moved to
    `data/` with the rest of the previous-instrument corpus. Not one record changed, and the
    move made the two trees agree: the mirror has always kept it under `data/`.

    This gate does not check paths for their own sake. It checks that the evidence for a
    withdrawal still EXISTS, because a withdrawal whose evidence has been deleted is a claim
    about a claim. Reporting a rename as a deletion is the same false alarm this file's
    docstring records the gate raising ten times over `withdrawn/`, and a gate that cries
    deletion over a tidy-up is a gate an operator learns to wave through -- which is how the
    real deletion, the one the docstring's fourth bullet describes, would get waved through
    with it.

    So a `<root>/<run>/...` path is retried under the other corpus root, and nothing else is:
    a missing correction document or a missing `withdrawn/` tree is still a finding.
    """
    parts = rel.replace("\\", "/").split("/")
    if len(parts) < 2 or parts[0] not in ("data", "runs"):
        return False
    other = "runs" if parts[0] == "data" else "data"
    return os.path.exists(os.path.join(study, other, *parts[1:]))


def load():
    if not os.path.exists(REGISTRY):
        return None
    return json.load(io.open(REGISTRY, encoding="utf-8"))


def phrases(reg):
    """(phrase, why) for every registered withdrawal, for key_numbers.RETRACTED."""
    out = []
    for w in reg["withdrawals"]:
        for p in w.get("phrases") or []:
            out.append((p, "%s -- withdrawn %s, %s" % (w["claim"].rstrip("."),
                                                       w["withdrawn"], w["record"])))
    return out


def _ledger_entries(mirror):
    path = os.path.join(mirror, "CORRECTIONS.md") if mirror else None
    if not path or not os.path.exists(path):
        return None
    n = 0
    for line in io.open(path, encoding="utf-8", errors="replace"):
        if line.startswith("### "):
            n += 1
    return n


def _surfaces():
    """The prose surfaces `key_numbers` gates, as {label: path}.

    Imported rather than relisted. A second copy of the surface list is how `LESSONS.md` --
    public, and carrying a withdrawn claim at both refs -- went unscanned by anything.
    """
    sys.path.insert(0, HERE)
    try:
        import key_numbers as K
    except Exception:
        return None
    out, absent = {}, []
    # THE PAPER IS NOT IN `SURFACES` AND THIS GATE WAS NOT READING IT.
    #
    # `SURFACES` is the list of places that quote GENERATED NUMBERS -- the website, the
    # dispatches, the release README, the book chapter. The paper is gated differently, by
    # `key_numbers --check` against its own phrase templates, so it was never in that dict and
    # this clause inherited the omission: on 2026-09-23 a withdrawn claim was planted in
    # PAPER-no-position-only-consensus.md and `check_withdrawals` returned exit 0.
    #
    # `scan_every_document_for_retractions()` does walk it -- 412 documents -- and caught the
    # plant. So the claim was covered; this gate's own report was not. A gate whose summary
    # says "absent" while never opening the primary artifact is the shape this file exists to
    # refuse, pointed at itself.
    paper = os.path.join(STUDY, "PAPER-no-position-only-consensus.md")
    if os.path.exists(paper):
        out["paper"] = paper
    for label, spec in K.SURFACES.items():
        path = spec.get("path")
        if path and os.path.exists(path):
            out[label] = path
        else:
            absent.append(label)
    # WHICH SURFACES WERE NOT THERE IS PART OF THE ANSWER. Run from the mirror, five of the
    # ten resolve -- the book chapter and the website live in the private workspace -- and a
    # scan that says "absent" having read half the surfaces is making a claim about the half
    # it did not open.
    return out, absent


def _absent(reg, findings):
    """Clause 1. THIS GATE USED TO PRINT 'absent' WITHOUT CHECKING IT.

    The first version delegated absence to `key_numbers` and then reported all four clauses
    as holding -- a summary line asserting a check it had not run, in a tool written because
    summary lines were asserting checks nobody had run. Caught the same hour it was written.
    """
    got = _surfaces()
    if got is None:
        findings.append(("(all)", "could not import key_numbers, so ABSENCE was not "
                                  "checked on any surface; this run proves nothing about "
                                  "clause 1"))
        return 0, []
    surfaces, unreadable = got
    if not surfaces:
        findings.append(("(all)", "key_numbers lists no readable surfaces here, so "
                                  "ABSENCE was checked against nothing"))
        return 0, unreadable
    text = {}
    for label, path in surfaces.items():
        try:
            text[label] = io.open(path, encoding="utf-8", errors="replace").read().lower()
        except OSError:
            continue
    for w in reg["withdrawals"]:
        for p in w.get("phrases") or []:
            for label, body in text.items():
                if p.lower() in body:
                    findings.append((w["id"], "phrase %r is still asserted on surface %r"
                                     % (p, label)))
    return len(text), unreadable


def check(reg):
    findings = []
    skipped = set()
    labelled = set()
    mirror = _tree("mirror")
    ledger = _ledger_entries(mirror)
    scanned, unreadable = _absent(reg, findings)
    if not scanned:
        skipped.add("absent")
    for label in unreadable:
        skipped.add("absent on surface %s (not in this tree)" % label)

    for w in reg["withdrawals"]:
        wid = w["id"]

        # 2. REACHABLE
        for tree_name in w.get("record_must_reach") or []:
            root = _tree(tree_name)
            if root is None:
                # NOT A DEFECT AND NOT A PASS. The other tree is simply not on this machine.
                skipped.add("reachable:%s" % tree_name)
                continue
            if not os.path.exists(os.path.join(root, w["record"])):
                # Is it actually cited from that tree? A missing file nobody points at is
                # untidy; a missing file with citations is a dangling reference in a
                # shipping artifact, so say which.
                cites = _citations(root, w["record"])
                findings.append((wid, "record %s is MISSING from the %s tree%s"
                                 % (w["record"], tree_name,
                                    " and is cited there %d time(s)" % cites if cites
                                    else "")))

        # 3. LEDGERED
        if w.get("published"):
            entry = w.get("public_entry")
            if entry in (None, "", "null"):
                findings.append((wid, "was PUBLISHED and has no CORRECTIONS.md entry. "
                                      "Published means pushed; %s"
                                 % (w.get("published_in") or ["no surface recorded"])[0]))
            elif entry != "n/a" and ledger is not None:
                try:
                    num = int(entry)
                except ValueError:
                    findings.append((wid, "public_entry %r is not a number" % entry))
                else:
                    if num > ledger:
                        findings.append((wid, "public_entry is %d and CORRECTIONS.md has "
                                              "%d entries" % (num, ledger)))
        elif w.get("public_entry") not in ("n/a", None):
            findings.append((wid, "is not published but claims public_entry %r"
                             % w.get("public_entry")))


        # 4. EVIDENCED, in the tree that holds the evidence.
        #
        # THE EVIDENCE LIVES IN THE PRIVATE STUDY. `withdrawn/` corpora and the dated
        # CORRECTIONS-*.md files are deliberately not all mirrored, so checking these paths
        # against the public checkout reports a deletion that never happened -- which the
        # first version of this gate did, ten times. Absent the study tree, this clause is
        # NOT APPLICABLE and the summary must say so instead of counting it as held.
        study = _tree("study")
        if study is None:
            skipped.add("evidenced")
        else:
            for rel in w.get("evidence") or []:
                if not os.path.exists(os.path.join(study, rel)) and not _elsewhere(study, rel):
                    findings.append((wid, "evidence %s is GONE from the study tree. A "
                                          "withdrawal whose evidence has been deleted is a "
                                          "claim about a claim." % rel))

        # 5. LABELLED, on disk, in THIS tree.
        #
        # THE FOUR CLAUSES ABOVE GOVERN CLAIMS ON SURFACES. None of them reaches the RECORDS,
        # and that gap is the one a stranger falls into: `data/2026-09-13-i3-phase0` ships, its
        # `manifest.json` reads as a clean success -- 1,600 calls, 0 failed -- and its B-A
        # contrast is withdrawn. Someone can compute and publish a withdrawn result from our
        # release without doing a single thing wrong, because nothing they can see says so.
        #
        # `gen_provenance.py` writes the label. This is what makes the label REQUIRED: every
        # run named as evidence for a withdrawal must carry a non-`active` status in its
        # root's PROVENANCE.json. A generator nothing checks is a generator that stops being
        # run, and the state it was describing goes quiet rather than wrong.
        for rel in w.get("evidence") or []:
            parts = rel.replace("\\", "/").split("/")
            if len(parts) != 2 or parts[0] not in ("data", "runs"):
                continue                       # not a corpus path; clauses 2 and 4 own it
            root, run = parts
            index = os.path.join(STUDY, root, "PROVENANCE.json")
            if not os.path.exists(os.path.join(STUDY, root, run)):
                continue                       # not in this tree; clause 4 decides if that is a defect
            labelled.add(run)
            if not os.path.exists(index):
                findings.append((wid, "%s holds withdrawn run %s and has no PROVENANCE.json. "
                                      "Run: python scripts/gen_provenance.py --write"
                                 % (root, run)))
                continue
            rows = (json.load(io.open(index, encoding="utf-8")) or {}).get("runs") or {}
            status = (rows.get(run) or {}).get("status")
            if status is None:
                findings.append((wid, "%s/PROVENANCE.json does not list %s, so the corpus "
                                      "index disagrees with the corpus. Re-run "
                                      "gen_provenance.py --write" % (root, run)))
            elif status == "active":
                findings.append((wid, "%s/%s is evidence for a WITHDRAWAL and its "
                                      "PROVENANCE.json status reads 'active'. A healthy-looking "
                                      "run directory is how a withdrawn result gets recomputed "
                                      "by somebody acting in good faith." % (root, run)))

    return findings, scanned, skipped, labelled


def _citations(root, rel):
    """How many files under `root` name this record. Cheap, and it is the whole point."""
    name = os.path.basename(rel)
    n = 0
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn
                 if d not in {".git", "__pycache__", ".pytest_cache", "runs", "data",
                              "export", "node_modules"}]
        for f in fn:
            if not f.endswith((".md", ".py")):
                continue
            try:
                s = io.open(os.path.join(dp, f), encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            if name in s:
                n += 1
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--owed", action="store_true",
                    help="list published withdrawals with no ledger entry, and exit 0")
    ap.add_argument("--phrases", action="store_true",
                    help="print the phrases key_numbers should ban, and exit 0")
    args = ap.parse_args(argv)

    reg = load()
    if reg is None:
        print("NOT APPLICABLE: no data/withdrawals.json in this tree")
        return 2

    total = len(reg["withdrawals"])
    if total == 0:
        # A REGISTRY WITH NOTHING IN IT MUST NOT READ AS A CLEAN BILL.
        print("DEFECT: the registry holds no withdrawals; nothing was checked")
        return 1

    if args.phrases:
        for p, why in phrases(reg):
            print("%-56s %s" % (p, why))
        return 0

    if args.owed:
        owed = [w for w in reg["withdrawals"]
                if w.get("published") and w.get("public_entry") in (None, "", "null")]
        print("%d of %d withdrawal(s) were published and are not in the public ledger:"
              % (len(owed), total))
        for w in owed:
            print("  %-32s %s" % (w["id"], w["claim"]))
            for s in w.get("published_in") or []:
                print("      %s" % s)
        return 0

    findings, scanned, skipped, labelled = check(reg)
    print("checked %d withdrawal(s) in %s%s"
          % (total, os.path.relpath(REGISTRY, STUDY).replace(os.sep, "/"),
             "  [running in the MIRROR]" if IN_MIRROR else ""))
    print("  %d phrase(s) registered, checked against %d surface(s)"
          % (len(phrases(reg)), scanned))
    if skipped:
        # A CLAUSE THAT DID NOT RUN IS NOT A CLAUSE THAT PASSED, and the verdict line below
        # must not imply otherwise. This is the `UNVERIFIED -- N of M gates did not run`
        # discipline the book pipeline learned the same way.
        print("  NOT CHECKED HERE: %s" % ", ".join(sorted(skipped)))
    if not findings:
        # MATCH THE PREFIX, NOT AN EXACT KEY. The skip strings name the surface or tree that
        # was missing ("absent on surface website ..."), so an equality test read every one of
        # them as a different clause and reported all four as held while listing six skips
        # directly above. A summary that contradicts the line above it is worse than no
        # summary: the reader believes the summary.
        # A CLAUSE THAT LABELLED NOTHING DID NOT RUN. `labelled` is the set of corpus runs the
        # fifth clause actually opened a PROVENANCE.json for. If a registry rewrite stops
        # naming corpus paths in `evidence`, the loop iterates over nothing and the clause
        # reports clean forever -- the vacuous pass this repository has paid for repeatedly.
        # It says so instead.
        if not labelled:
            skipped.add("labelled (no withdrawal names a corpus run in this tree)")
        clauses = ("absent", "reachable", "ledgered", "evidenced", "labelled")
        held = [c for c in clauses if not any(s.startswith(c) for s in skipped)]
        if "labelled" in held:
            print("  labelled: %d withdrawn run(s) carry a non-active status on disk: %s"
                  % (len(labelled), ", ".join(sorted(labelled))))
        if len(held) == len(clauses):
            print("every withdrawal is absent, reachable, ledgered, evidenced and labelled.")
        else:
            print("nothing FAILED. What was checked here holds: %s."
                  % (", ".join(held) or "nothing"))
            print("This is NOT a clean bill for %s in this tree."
                  % ", ".join(c for c in clauses if c not in held))
        return 0
    print("")
    print("BROKEN -- %d clause(s):" % len(findings))
    for wid, msg in findings:
        print("  %-32s %s" % (wid, msg))
    return 1


if __name__ == "__main__":
    sys.exit(main())
