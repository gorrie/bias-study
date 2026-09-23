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
#: True when THIS checkout is the public mirror. Named by directory, which is the one thing
#: that is stable in both directions -- the private tree is `research/bias-study`, the public
#: one is `bias-study-release`.
IN_MIRROR = os.path.basename(STUDY) == "bias-study-release"


def _tree(name):
    """The root of the named tree, or None when it is not present here.

    RESOLVING "study" TO WHATEVER TREE THIS RUNS FROM IS A BUG, and the first version of this
    gate had it: run from the mirror, `_tree("study")` returned the mirror, so every clause
    scoped to the private tree was silently evaluated against the public one and reported ten
    defects that were not defects. `release_check.MIRROR` carries a comment about the same
    conflation in the other direction. Returning None is the honest answer, and every caller
    has to say NOT APPLICABLE rather than pass.
    """
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
                if not os.path.exists(os.path.join(study, rel)):
                    findings.append((wid, "evidence %s is GONE from the study tree. A "
                                          "withdrawal whose evidence has been deleted is a "
                                          "claim about a claim." % rel))

    return findings, scanned, skipped


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

    findings, scanned, skipped = check(reg)
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
        clauses = ("absent", "reachable", "ledgered", "evidenced")
        held = [c for c in clauses if not any(s.startswith(c) for s in skipped)]
        if len(held) == len(clauses):
            print("every withdrawal is absent, reachable, ledgered and evidenced.")
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
