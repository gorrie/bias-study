#!/usr/bin/env python3
"""Render the live item bank as mirrored pairs for the human read that gates collection.

THE BANK IS THE AUTHOR'S, AND ITS PAIRS ARE NOT NEGATIONS. This said "the I3 bank as 30 pairs"
and "A HUMAN HAS READ ALL 60 ITEMS", describing the 60-item bank an assistant generated on
2026-09-14 and which is withdrawn. The live instrument is `data/ratchet-battery.json` -- 32
items in 16 pairs, where each half states a claim and its opposing framing in the author's own
words. The question the sheet asks is therefore "can I agree with BOTH halves without
contradicting myself?", not "is this the same sentence with a 'not' in it".

The item count and pair count are read from the bank, so this text is the only place they
could go stale, and they are not repeated below.

This exists so the read is a ten-minute job rather than a JSON crawl, because a gate that is
tedious to clear is a gate that gets waved through -- and the last time generated pairs were
read by a human, SIX OF TEN WERE BROKEN (`ITEM-AUDIT-2026-09-14-mirror-pairs.md`).

The reader applies ONE test, the fourth rule from that audit, which is the rule
all five failures broke:

    Can I agree with BOTH halves without contradicting myself?

If yes, the pair is not a mirror and the frame gap measured on it is a different
question, which reads exactly like frame-following. That is the error the
experiment exists to detect, so it cannot sit inside the instrument.

The machine already checks IDENTITY -- `verify_negation` asserts the two halves
are the same token sequence bar one inserted "not". It cannot check whether the
resulting proposition is one a person could coherently hold both ways, and that
is the whole of what the human is for. The diff is shown per pair so the reader
can see exactly what the machine checked and judge the part it could not.

    python scripts/render_item_read.py > ITEM-READ-<date>-i3-bank.md
"""
from __future__ import annotations

import difflib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
#: Default: whichever bank the runner would administer. Hardcoding one meant the sheet
#: could only ever sign off that bank, so the study's own instrument had no way to be read.
def _default_bank():
    try:
        sys.path.insert(0, HERE)
        import run_compass
        return str(run_compass.ITEMS_PATH)
    except Exception:
        return os.path.join(STUDY, "data", "ratchet-battery.json")


BANK = _default_bank()


def diff_words(a: str, b: str) -> str:
    """The inserted/removed span between the halves, as words."""
    aw, bw = a.split(), b.split()
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, aw, bw).get_opcodes():
        if tag == "equal":
            continue
        removed = " ".join(aw[i1:i2])
        added = " ".join(bw[j1:j2])
        if removed and added:
            out.append("%s -> %s" % (removed, added))
        elif added:
            out.append("+%s" % added)
        elif removed:
            out.append("-%s" % removed)
    return "; ".join(out) or "(no textual difference -- INVESTIGATE)"


def is_family_bank(items) -> bool:
    """True when the bank is a stem x slot design rather than a flat list of pairs.

    Detected from the data rather than passed as a flag, because the sheet asking the wrong
    questions is the failure this file already has a scar from: rendering the
    literal-negation preamble over an authored bank told the reader to skip the only check
    that could fail.
    """
    return bool(items) and all(it.get("stem") and it.get("sector") for it in items)


def render_family(bank, items, w, bank_path=None) -> int:
    """The read for a stem x slot bank: four stems, four sectors, and the slot between them.

    Sixteen pair-reads would be the wrong decomposition and a rubber stamp with it. The pairing
    is a property of the STEM -- four judgements, not sixteen -- and the sector variants of one
    half are identical apart from the path phrase, which `instantiate_stems.verify_slot_only`
    has already proved. So the reader is asked the three questions that are actually distinct,
    and shown the variants side by side, which is the only way "does this stem read naturally
    in health as well as in finance?" can be answered at all.
    """
    stems, sectors = [], []
    for it in items:
        if it["stem"] not in stems:
            stems.append(it["stem"])
        if it["sector"] not in sectors:
            sectors.append(it["sector"])
    by = {}
    dupes = []
    for it in items:
        key = (it["stem"], it["sector"], it.get("frame"))
        if key in by:
            dupes.append("#%s duplicates #%s at %s" % (it.get("id"), by[key].get("id"), key))
        by[key] = it
    phrase = {it["sector"]: it.get("path_phrase", "?") for it in items}

    w("# The %d items, for the read that gates collection\n\n" % len(items))
    w("**Instrument:** `%s`, version %s. %d stems x %d sectors x 2 frames.\n\n"
      % (bank.get("instrument", "?"), bank.get("version", "?"), len(stems), len(sectors)))
    w("**Scale:** %s\n\n" % bank.get("position_scale", "?"))
    # THE SHEET MUST NAME THE BANK IT SIGNS. `check_instrument_approved.find_sheet_for` matches
    # a sheet to a bank by looking for the bank's filename in the sheet's text. The first
    # version of this view printed no filename, so the author could render it, read it, tick
    # every box, and still be told NO SIGN-OFF SHEET NAMES THIS BANK -- with the only way
    # through being to hand-edit the sheet that says not to hand-edit it. That is the
    # 2026-09-14 failure from the other side: a gate nobody can clear honestly is a gate that
    # gets cleared dishonestly.
    w("Generated by `scripts/render_item_read.py` from `%s`. "
      "Do not hand-edit; fix the stems and regenerate.\n\n"
      % (os.path.basename(bank_path) if bank_path else "?"))
    if dupes:
        w("> **DEFECT — the bank has duplicate (stem, sector, frame) entries, and one of each "
          "pair is not shown below:** %s. Fix the bank before reading further.\n\n"
          % "; ".join(dupes))
    w("---\n\n")
    w("## What you are checking\n\n")
    w("You wrote %d sentences and %d phrases; the machine made %d items from them. It has "
      "already proved the four sector variants of each half are **identical apart from the "
      "path phrase** — that is `instantiate_stems.verify_slot_only`, and it is the claim the "
      "whole instrument rests on. What a machine cannot judge is whether the sentences mean "
      "the same thing in all four sectors, and that is what this sheet is for.\n\n"
      % (2 * len(stems), len(sectors), len(items)))
    w("Three questions, asked where each one can actually fail:\n\n")
    w("1. **Per stem — is it a mirror?** Can you agree with BOTH halves without contradicting "
      "yourself? If yes it is not a pair, and the frame gap measured on it reads exactly like "
      "frame-following, which is the error the experiment exists to detect.\n")
    w("2. **Per stem and sector — does it read naturally there?** A stem that is ordinary in "
      "finance can be absurd in health. This is where a stem breaks, and it is why the four "
      "variants are printed together instead of scattered through sixteen sections.\n")
    w("3. **Per sector — is the path phrase the right abstraction?** Roles and institution "
      "types only, matched in specificity to the other three. A phrase that names more than "
      "the others makes the sector cue the wording rather than the sector.\n\n")
    w("Tick a box only where the answer is yes. A blank box blocks collection, which is the "
      "point.\n\n")
    w("---\n\n")

    w("## The four path phrases, together\n\n")
    w("Read these against each other before the stems. They are the only thing that differs "
      "between an item and its three siblings.\n\n")
    w("| sector | play | path phrase | words |\n|---|---|---|---:|\n")
    for s in sectors:
        any_item = next(it for it in items if it["sector"] == s)
        w("| %s | `%s` | %s | %d |\n"
          % (s, any_item.get("play", "?"), phrase[s], len(phrase[s].split())))
    w("\n")
    for s in sectors:
        w("- [ ] **%s** — roles and institution types only, no firm and no person, matched in "
          "specificity to the other three.\n" % s)
    w("\n---\n\n")

    for stem in stems:
        w("## Stem `%s`\n\n" % stem)
        for frame in ("critic", "defender"):
            got = [by.get((stem, s, frame)) for s in sectors]
            if not any(got):
                # A HALF THAT IS ENTIRELY ABSENT IS THE LOUDEST DEFECT, so it cannot be the
                # one thing this view skips silently. Skipping it printed a sheet that looked
                # complete for a bank with no defender halves at all.
                w("**%s half — ENTIRELY MISSING from the bank. Investigate before reading "
                  "on.**\n\n" % frame)
                continue
            w("**%s half**\n\n" % frame)
            w("| sector | item | text |\n|---|---:|---|\n")
            for s, it in zip(sectors, got):
                if it is None:
                    w("| %s | — | **MISSING — investigate** |\n" % s)
                else:
                    w("| %s | #%d | %s |\n" % (s, it["id"], it["text"]))
            w("\n")
        w("- [ ] **Mirror.** I cannot agree with both halves of stem `%s` without "
          "contradicting myself.\n" % stem)
        # THE FRAME LABEL IS THE SIGN OF THE PRIMARY OUTCOME and no machine can check it: both
        # labels are grammatical, and which half a critic of institutions would take is a
        # judgement about meaning. A mislabelled frame flips the sign on every item built from
        # this stem -- four pairs at once, not one.
        w("- [ ] **Frame.** The `critic` half is the one a critic of institutions would take. "
          "If these are swapped, the sign of the primary outcome flips on all %d of this "
          "stem's pairs.\n" % len(sectors))
        for s in sectors:
            w("- [ ] **%s.** Both halves read as natural English about %s — article, number "
              "and verb agree with the phrase — and mean there what they mean in the other "
              "sectors.\n" % (s, s))
        w("\n")
        exemplars = (by.get((stem, sectors[0], "critic")) or {}).get("exemplars") or []
        if exemplars:
            w("<sub>Provenance for this stem's sectors is carried on the items themselves "
              "(`exemplars`); no item text names anyone.</sub>\n\n")
        w("---\n\n")

    w("## Sign-off\n\n")
    w("%d items, %d stems, %d sectors.\n\n" % (len(items), len(stems), len(sectors)))
    w("- [ ] I wrote every stem and every path phrase in this bank.\n")
    w("- [ ] I have read all %d items once.\n\n" % len(items))
    w("Read by: ______________________  date: ____________\n\n")
    w("`check_instrument_approved.py` refuses collection until every box above is ticked.\n")
    return 0


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split(chr(10))[0])
    ap.add_argument("--items", default=BANK, help="bank to render (default: the live instrument)")
    args = ap.parse_args(argv)
    with open(args.items, encoding="utf-8") as fh:
        bank = json.load(fh)
    items = bank["items"]
    if is_family_bank(items):
        return render_family(bank, items, sys.stdout.write, bank_path=args.items)
    by_id = {it["id"]: it for it in items}

    pairs, seen = [], set()
    for it in items:
        if it["id"] in seen:
            continue
        other = by_id.get(it.get("mirror_of"))
        if other is None:
            pairs.append((it, None))
            seen.add(it["id"])
            continue
        crit, inst = (it, other) if it.get("frame") == "critic" else (other, it)
        pairs.append((crit, inst))
        seen.update({it["id"], other["id"]})

    w = sys.stdout.write
    # AUTHOR-WRITTEN BANKS HAVE NO `generated_by`. Requiring one meant this could render a
    # sheet only for a bank a machine had built -- so the study's own instrument was the one
    # thing that could not be signed off, and the bank that could was the unapproved one.
    built = (", built by `%s`" % bank["generated_by"]) if bank.get("generated_by") \
        else " (author-written)"
    w("# The %d items, for the read that gates collection\n\n" % len(items))
    w("**Instrument:** `%s`, version %s, created %s%s.\n\n"
      % (bank.get("instrument", "?"), bank.get("version", "?"),
         bank.get("created", "?"), built))
    w("**Scale:** %s\n\n" % bank.get("position_scale", "?"))
    w("Generated by `scripts/render_item_read.py` from `%s`. "
      "Do not hand-edit; fix the bank and regenerate.\n\n" % os.path.basename(args.items))
    w("---\n\n")
    w("## What you are checking — and what you are NOT\n\n")
    # WHICH READ THIS IS depends on how the bank is built, and getting it wrong makes the
    # sheet tell the reader to skip the only check that matters.
    #
    # A literal-negation bank ("X" / "not X") cannot fail the complementarity rule, so its
    # sheet says don't spend the read there. An AUTHORED bank pairs two written propositions,
    # and complementarity is exactly what can fail -- five of v3's sixteen pairs admit
    # agreement with both halves. Rendering the literal-negation preamble over an authored
    # bank instructed the reader past the decisive question.
    literal = 0
    for crit, inst in pairs:
        if inst is not None:
            try:
                import build_item_bank as _B
                if _B.verify_negation(crit["text"], inst["text"]) is None:
                    literal += 1
            except Exception:                           # noqa: BLE001
                pass
    is_literal_bank = pairs and literal >= 0.8 * len([p for p in pairs if p[1] is not None])

    w("The gate is the fourth rule of `ITEM-AUDIT-2026-09-14-mirror-pairs.md`: *can a "
      "coherent person agree with both halves?* Five of ten Phase 0 pairs failed it.\n\n")
    if is_literal_bank:
        w("**That rule cannot fail in this bank, so do not spend the read on it.** Every pair "
          "below is a literal negation — the same sentence bar one inserted \"not\", asserted "
          "by `verify_negation` and shown on each `diff` line. Nobody can coherently agree "
          "with both *X* and *not X*.\n\n")
        w("A gate that cannot fail is a rubber stamp, so the read is aimed at what "
          "construction does **not** guarantee. Four things, per pair:\n\n")
    else:
        w("**THIS BANK IS AUTHORED, NOT DERIVED, so that rule is live and it is the main "
          "thing you are checking.** These pairs are two written propositions, not a sentence "
          "and its negation, so nothing mechanical has ruled out a pair a coherent person can "
          "agree with twice. Read each pair and ask the question directly:\n\n")
        w("> **Can I agree with BOTH halves without contradicting myself?**\n\n")
        w("If yes, the pair is not a mirror, and the frame gap measured on it is a different "
          "question — which reads exactly like frame-following, the error the experiment "
          "exists to detect. Tick only the pairs where the answer is no. Then four more, per "
          "pair:\n\n")
    w("1. **ONE claim, not two.** A double-barrelled proposition ('should require a licence "
      "and an audit') cannot be answered by someone who splits on it, and its negation is "
      "ambiguous. This is the most likely remaining defect.\n")
    w("2. **Specific enough that agreement means something.** If 'agree' could mean three "
      "different positions, the item measures which one the model picked, not where it "
      "stands.\n")
    w("3. **The negation is natural English.** The generator that preceded this bank produced "
      "'have not more influence' and 'has not leverage'. A reader who stumbles is a model that "
      "stumbles.\n")
    w("4. **The critic half is actually the institution-skeptical half.** This is the one with "
      "teeth: the frame gap is critic minus institution, paired. **A mislabelled frame flips "
      "the sign of the primary outcome on that pair**, and nothing mechanical can catch it "
      "because both labels are grammatical. Check the `critic` row is the side a critic of "
      "institutions would take.\n\n")
    w("Mark a pair **X** if it fails any of the four, **?** if unsure. Blank means good.\n\n")
    w("---\n\n")

    counts = bank.get("counts") or {}
    if counts:
        w("**Bank counts as built:** %s\n\n"
          % ", ".join("%s %s" % (k.replace("_", " "), v) for k, v in counts.items()))

    for crit, inst in pairs:
        pid = crit.get("pair_id") or "P??"
        w("## %s — %s\n\n" % (pid, crit.get("topic", "?")))
        if crit.get("pair_note"):
            w("*%s*\n\n" % crit["pair_note"])
        w("| | item | text |\n|---|---|---|\n")
        w("| critic | #%s (%s) | %s |\n"
          % (crit["id"], crit.get("polarity", "?"), crit["text"]))
        if inst is not None:
            w("| institution | #%s (%s) | %s |\n"
              % (inst["id"], inst.get("polarity", "?"), inst["text"]))
            w("\n`diff:` %s\n\n" % diff_words(crit["text"], inst["text"]))
        else:
            w("\n**UNPAIRED — no mirror_of. Investigate.**\n\n")
        w("**One claim / specific / natural negation / critic side is the skeptical side?**  [ ]\n\n")

    w("---\n\n")
    w("## Sign-off\n\n")
    w("%d pairs, %d items rendered.\n\n" % (len(pairs), len(items)))
    w("- [ ] I have read all %d items once.\n" % len(items))
    w("- [ ] Pairs marked X above are excluded from the frame-gap primary outcome.\n\n")
    w("Read by: ______________________  date: ____________\n\n")
    w("Phase 1's gate in `PLAN-2026-09-13-I3.md` is met when the box above is ticked. "
      "Nothing in Phase 2 collects until then.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
