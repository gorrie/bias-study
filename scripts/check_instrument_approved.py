#!/usr/bin/env python3
"""Refuse to collect against an instrument the author has not read and signed.

WHY THIS EXISTS
---------------
On 2026-09-14 a 60-item bank was written into `build_item_bank.py` by an assistant
session. `render_item_read.py` rendered a sign-off sheet for it -- one checkbox per
pair, the single question "can I agree with BOTH halves without contradicting
myself?" -- and `ITEM-READ-2026-09-15-i3-bank.md` was produced with every box empty.

**372 sheets were then collected against it, and nothing objected.** The study's own
plan says Phase 1 gates on "a human has read all 60 items once". The renderer existed.
The checklist existed. Nothing read the checklist back, so the gate was a document
rather than a gate, and the study spent six hours measuring an instrument nobody had
approved while its author's own battery had zero records.

This closes that. An instrument is collectable when a sign-off sheet exists for it,
names it, and has every box ticked. Anything else exits non-zero and says which pairs
are outstanding.

    check_instrument_approved.py                      # the live default instrument
    check_instrument_approved.py --items data/x.json  # a specific bank
    check_instrument_approved.py --quiet

Exit 0 approved, 1 not approved, 2 NOT APPLICABLE (no bank on disk to judge).
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

#: A ticked box. `[x]`, `[X]`, `[✓]` all count; `[ ]` and `[]` do not.
TICKED = re.compile(r"\[\s*[xX✓✔]\s*\]")
UNTICKED = re.compile(r"\[\s*\]")


def live_instrument_path():
    """Whatever the runner would administer if nobody passed --items."""
    try:
        import run_compass
        return str(run_compass.ITEMS_PATH)
    except Exception:                                   # noqa: BLE001
        return os.path.join(STUDY, "data", "ratchet-battery.json")


def sign_off_sheets():
    return sorted(glob.glob(os.path.join(STUDY, "ITEM-READ-*.md")))


def _bank_name(path):
    return os.path.basename(path)


def find_sheet_for(bank_path):
    """The sign-off sheet that NAMES this bank, or None.

    Matching on the filename inside the sheet, not on the sheet's own name: a sheet
    called `ITEM-READ-2026-09-15-i3-bank.md` signing off a different bank would
    otherwise pass by looking right.
    """
    want = _bank_name(bank_path)
    for sheet in sign_off_sheets():
        try:
            text = io.open(sheet, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        if want in text:
            return sheet, text
    return None, None


#: Banks whose items predate the `origin` field, with the reason each is allowed to.
#:
#: A silent "absent is fine" is what let the 2026-09-14 bank through -- it declared no origin
#: either, and neither did anything else, so nothing could tell an authored bank from a
#: generated one. Absence is therefore allowed only by name and only with a reason written
#: here. Anything new declares `origin` on every item or it is not collectable.
#:
#: KEYED ON BASENAME, which means any file anywhere named `ratchet-battery.json` inherits the
#: exemption. Left that way deliberately: the alternative is an absolute path, which breaks
#: every test fixture and every clone of this repository, and the exposure is that someone
#: would have to name a new bank after the old one to use it. Recorded rather than fixed so
#: the hole is known rather than discovered.
ORIGIN_GRANDFATHERED = {
    "ratchet-battery.json":
        "authored by Ian Gorrie 2026-08-30, before the field existed; its provenance is the "
        "`source` header and the signed ITEM-READ sheet, not a per-item flag",
}


def _origin_findings(bank_path, bank):
    """Refuse a bank whose sentences a machine wrote.

    The gate above proves the author READ the items. This proves he WROTE them. They are
    different failures: the i3 bank was generated and unread, and a bank that is generated
    and then read still puts an assistant's register into the instrument.
    """
    items = bank.get("items") or []
    origins = {}
    for it in items:
        origins.setdefault(str(it.get("origin") or ""), 0)
        origins[str(it.get("origin") or "")] += 1

    missing = origins.get("", 0)
    if missing:
        why = ORIGIN_GRANDFATHERED.get(_bank_name(bank_path))
        if not why:
            return ["%d of %d items declare no `origin`. An instrument records who wrote its "
                    "sentences; a bank that cannot say is not collectable."
                    % (missing, len(items))]
        if missing != len(items):
            return ["%s is grandfathered for a missing `origin` (%s) but %d of %d items "
                    "declare one -- a bank half-covered by an exemption is neither."
                    % (_bank_name(bank_path), why, len(items) - missing, len(items))]
        return []

    wrong = sorted(o for o in origins if o != "author")
    if wrong:
        return ["%d item(s) declare origin %s. Only `author` is collectable -- the whole "
                "point of the instrument is that its author wrote it."
                % (sum(origins[o] for o in wrong), ", ".join(repr(o) for o in wrong))]
    return []


def audit(bank_path):
    """-> (ok, findings). `findings` is a list of human-readable problems."""
    findings = []
    if not os.path.exists(bank_path):
        return None, ["no instrument at %s" % bank_path]

    bank = json.load(io.open(bank_path, encoding="utf-8"))
    findings.extend(_origin_findings(bank_path, bank))
    n_pairs = len({i.get("mirror_of") and min(i["id"], i["mirror_of"])
                   for i in bank.get("items", []) if i.get("mirror_of")})
    status = str(bank.get("status") or "")
    if "WITHDRAWN" in status.upper():
        findings.append("the bank declares itself %s" % status)

    sheet, text = find_sheet_for(bank_path)
    if sheet is None:
        findings.append(
            "NO SIGN-OFF SHEET names %s. Render one with `python "
            "scripts/render_item_read.py --items %s > ITEM-READ-<date>-<name>.md` and read it."
            % (_bank_name(bank_path), os.path.relpath(bank_path, STUDY).replace("\\", "/")))
        return False, findings

    ticked = len(TICKED.findall(text))
    unticked = len(UNTICKED.findall(text))
    if unticked:
        findings.append(
            "%s has %d pair(s) ticked and %d UNTICKED. Every pair is read or the "
            "instrument is not approved." % (os.path.basename(sheet), ticked, unticked))
    if not ticked and not unticked:
        findings.append(
            "%s contains no checkboxes at all, so nothing was signed. A sheet that "
            "cannot record a refusal cannot record an approval either."
            % os.path.basename(sheet))
    if ticked and n_pairs and ticked < n_pairs:
        findings.append(
            "%d box(es) ticked against %d pair(s) in the bank -- the sheet does not cover "
            "the instrument." % (ticked, n_pairs))
    return (not findings), findings


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--items", default=None, help="bank to check (default: the live one)")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)

    bank = a.items or live_instrument_path()
    if not os.path.isabs(bank):
        bank = os.path.join(STUDY, bank)

    ok, findings = audit(bank)
    if ok is None:
        print("no instrument at %s -- NOT APPLICABLE" % bank)
        return 2
    if ok:
        if not a.quiet:
            sheet, _ = find_sheet_for(bank)
            print("%s is approved: every pair read and ticked in %s."
                  % (_bank_name(bank), os.path.basename(sheet)))
        return 0

    print("INSTRUMENT NOT APPROVED -- %s" % _bank_name(bank))
    print("")
    print("A bank is collectable when its author has read every pair and said so. The")
    print("question the read asks is: can I agree with BOTH halves without contradicting")
    print("myself? A machine cannot answer it, which is why this gate is a signature.")
    print("")
    for f in findings:
        print("  - %s" % f)
    return 1


if __name__ == "__main__":
    sys.exit(main())
