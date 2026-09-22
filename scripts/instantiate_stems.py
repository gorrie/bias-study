#!/usr/bin/env python3
"""Build the factions bank from four authored stems and four authored path phrases.

WHAT IT DOES
------------
Takes twelve pieces of author-written text -- four mirrored stems (a critic half and a defender
half each, every half carrying one `[PATH]` slot) and one path phrase per sector -- and
produces the 32-item bank: 4 stems x 4 sectors x 2 frames, 16 mirrored pairs.

WHY MECHANICALLY
----------------
The instrument's whole claim is that a within-model sector difference cannot be item wording.
That holds only if the four sector variants of one half are **identical apart from the slot**,
and identity is decidable, so a machine checks it. This is the same division that
`build_item_bank.verify_negation` got right and the rest of that script got wrong: **a
generator must be correct about meaning, a verifier need only be correct about identity**
(LEARNINGS #19). Nothing here writes a sentence. It fills a slot and then proves it only
filled a slot.

WHAT `--check` ACTUALLY CHECKS, and what it used to
---------------------------------------------------
`--check` **re-derives the bank from the stems and diffs it against the bank on disk**. The
first version did not: it built fresh items in memory, ran the slot check on those, and never
opened the built bank at all. That check could not fail, because `build` fills the slot by
`stem.replace("[PATH]", phrase)` and the verifier recovered the skeleton by
`text.replace(phrase, "[PATH]")` -- exact inverses. It was a function tested against its own
inverse, registered in the gate registry as "the factions bank still matches its stems", and a
hand edit to `data/ratchet-factions.json` was invisible to it.

That is this study's signature failure, the one LEARNINGS opens with: **the dangerous failure
looks healthy.** A green gate that examined nothing.

WHAT IT REFUSES
---------------
- A half with no `[PATH]` slot, or more than one.
- An empty or whitespace-only path phrase.
- A path phrase naming a person or an institution from the Ratchet MCP -- the items abstract
  a documented pattern and carry their exemplars as provenance; they never name anyone. The
  MCP's own scope rule is "documented public positions only -- same defamation lint as every
  other record" (`ratchet-mcp/docs/SCOPE.md`), and a critic half characterising a named
  person's motive is a sentence that dataset forbids. **This catches one shape only** -- see
  `_mcp_names` -- and the guard that matters is the author's own read of the four phrases.
- Path phrases whose word counts differ by more than three, which would make length a
  sector cue.
- Any stem whose two halves are identical.
- A bank on disk whose text, slot fill, pairing or origin differs from what the stems produce.

Whether the `critic` half is really the institution-skeptical one is a judgement about meaning,
so no check here claims it. It is question 1 on the sign-off sheet, which is what the sheet is
for.

    python scripts/instantiate_stems.py --stems stems.json --out data/ratchet-factions.json
    python scripts/instantiate_stems.py --stems stems.json --check   # diff disk vs stems
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
MCP = os.path.join(os.path.dirname(STUDY), "ratchet-mcp", "server", "data")

SLOT = "[PATH]"
FRAMES = ("critic", "defender")
DEFAULT_BANK = os.path.join(STUDY, "data", "ratchet-factions.json")

#: Sector -> the play it abstracts. Matches faction_reading_pack.SECTORS; the bank records both.
SECTORS = {"finance": "vault", "defence": "backstop",
           "health": "ward", "technology": "pipeline"}

#: Length tolerance between path phrases, in words. A sector whose phrase is markedly longer
#: gives the model a cue that has nothing to do with the sector.
PHRASE_WORD_TOLERANCE = 3

#: Exemplars per item, per the prereg. Three is its floor; six is what the reading pack shows
#: the author, so the bank carries the same six he read.
EXEMPLARS_PER_ITEM = 6
EXEMPLARS_MINIMUM = 3

#: The fields that decide what a model is shown and how its answer is scored. A difference in
#: any of them between the bank on disk and the bank the stems produce is a different
#: instrument. `exemplars` is deliberately absent: it is provenance, it is re-derived from a
#: dataset that legitimately gains sources, and its drift is reported separately.
MEASURED_FIELDS = ("id", "pair_no", "mirror_of", "frame", "stem", "family",
                   "sector", "play", "path_phrase", "origin", "text")


def _fold(s):
    """Lowercase, strip accents and possessives, and reduce to word tokens.

    `BlackRock's` must match `BlackRock` and `Kohler` must match `Kohler` -- the first version
    kept the apostrophe inside the token and dropped every non-ASCII letter from both sides, so
    `alumni of BlackRock's board` and the unaccented spelling of an accented name both walked
    through a check whose own comment said punctuation was not a disguise.
    """
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"['’]s\b", "", s)
    return " ".join(re.findall(r"[a-z0-9&]+", s))


def _mcp_names():
    """Every name the phrases must not contain: labels, ids, and single surnames.

    WHAT THIS CATCHES AND WHAT IT DOES NOT. It is a tripwire for the obvious shape, not a
    guard. It reads `label` and `id` from both files -- the `id` of a person record IS the
    surname, which is how `staff who follow Rubin to a bank` gets caught -- and it keeps short
    all-caps acronyms (CFR, NSA, IMF, ECB), which a blanket length filter dropped. It will
    still miss a first name alone, an unlisted abbreviation, or a periphrasis. The author
    reading his own four phrases is the check that matters; this one exists so a slip cannot be
    silent.
    """
    names = set()
    for fname in ("people.jsonl", "institutions.jsonl"):
        path = os.path.join(MCP, fname)
        if not os.path.exists(path):
            continue
        for line in io.open(path, encoding="utf-8"):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            for key in ("label", "id"):
                raw = rec.get(key)
                if not isinstance(raw, str):
                    continue
                folded = _fold(raw)
                # Keep acronyms of any length; require 4+ characters otherwise, so a stray
                # one-letter id cannot match every phrase containing that letter.
                if folded and (len(folded) > 3 or raw.isupper()):
                    names.add(folded)
    return names


def stem_ids(spec):
    """-> the id of each stem, by position. One definition, used by build and by verify."""
    return [(st.get("id") or ("stem%d" % (n + 1)))
            for n, st in enumerate(spec.get("stems") or [])]


def validate(spec):
    """-> list of problems. Everything that would make the collection worthless."""
    bad = []
    stems = spec.get("stems") or []
    phrases = spec.get("path_phrases") or {}

    if len(stems) < 2:
        bad.append("fewer than two stems: a sector estimate would rest on one wording")
    missing = [s for s in SECTORS if s not in phrases]
    if missing:
        bad.append("no path phrase for: %s" % ", ".join(sorted(missing)))

    blank = sorted(s for s, p in phrases.items() if not (p or "").strip())
    if blank:
        bad.append("empty path phrase for: %s -- a sector whose slot fills with nothing is not "
                   "a variant of the others, it is a different sentence" % ", ".join(blank))

    counts = {s: len((phrases.get(s) or "").split()) for s in phrases if (phrases.get(s) or "").strip()}
    if counts and (max(counts.values()) - min(counts.values())) > PHRASE_WORD_TOLERANCE:
        bad.append("path phrases differ by more than %d words (%s) -- length becomes a "
                   "sector cue" % (PHRASE_WORD_TOLERANCE,
                                   ", ".join("%s=%d" % kv for kv in sorted(counts.items()))))

    names = _mcp_names()
    for sector, phrase in sorted(phrases.items()):
        folded = " %s " % _fold(phrase)
        hit = sorted(n for n in names if (" %s " % n) in folded)
        if hit:
            bad.append("path phrase for %s names %s -- items abstract the pattern and carry "
                       "exemplars as provenance; they never name anyone"
                       % (sector, ", ".join(hit[:3])))

    ids = stem_ids(spec)
    if len(set(ids)) != len(ids):
        bad.append("two stems share an id (%s) -- the bank could not tell their items apart"
                   % ", ".join(sorted(ids)))
    for i, st in enumerate(stems, 1):
        for frame in FRAMES:
            text = (st.get(frame) or "").strip()
            if not text:
                bad.append("stem %d has no %s half" % (i, frame))
                continue
            n = text.count(SLOT)
            if n != 1:
                bad.append("stem %d %s half has %d %s slots, need exactly one"
                           % (i, frame, n, SLOT))
        if (st.get("critic") or "").strip() == (st.get("defender") or "").strip():
            bad.append("stem %d has identical halves" % i)
        # A DEFAULT OF "author" ASSERTS AUTHORSHIP NOBODY STATED. This read
        # `st.get("origin", "author")`, so any stems file, written by anyone, produced a bank
        # that cleared the origin gate -- the gate added that same day to stop exactly that.
        # LEARNINGS #37: absence is never a silent default. The author writes the word.
        if st.get("origin") != "author":
            bad.append("stem %d declares origin %r, not 'author'. Every stem says who wrote "
                       "it, in the stems file, by hand -- a default would make the origin "
                       "gate an assertion about itself" % (i, st.get("origin")))
    return bad


def _sourced_exemplars():
    """play -> [{id, label, role, sources}], by the prereg's fixed rule.

    Derived from `people.jsonl` rather than taken from the spec. The rule -- "most sources,
    then by label" -- is pre-registered, so a hand-curated list in the stems file would be a
    second copy of a fact that is supposed to be mechanical, and the one place a subject could
    be chosen after seeing a number. The rule itself lives in `faction_reading_pack` and is
    imported, not restated.

    IT RAISES RATHER THAN RETURNING EMPTY. An earlier version swallowed every exception and
    fell back to `spec["exemplars"]` -- the hand-curated list this docstring forbids -- so one
    malformed line in the dataset silently handed provenance back to whoever wrote the spec.
    """
    sys.path.insert(0, HERE)
    import faction_reading_pack as pack
    out = {}
    for play, people in pack.exemplars(EXEMPLARS_PER_ITEM).items():
        out[play] = [{"id": r.get("id") or r["label"],
                      "label": r["label"],
                      "role": r.get("role", ""),
                      "sources": [s.get("url") for s in (r.get("sources") or [])[:2]
                                  if s.get("url")]}
                     for r in people]
    return out


def build(spec, exemplars=None):
    """-> the bank's items. Fills slots and nothing else."""
    items, pair_no, item_id = [], 0, 0
    exemplars = _sourced_exemplars() if exemplars is None else exemplars
    for st, stem_id in zip(spec["stems"], stem_ids(spec)):
        for sector in sorted(SECTORS):
            pair_no += 1
            phrase = spec["path_phrases"][sector]
            pair = []
            for frame in FRAMES:
                item_id += 1
                pair.append({
                    "id": item_id,
                    "pair_no": pair_no,
                    "frame": frame,
                    "stem": stem_id,
                    "family": stem_id,
                    "sector": sector,
                    "play": SECTORS[sector],
                    "path_phrase": phrase,
                    "exemplars": exemplars.get(SECTORS[sector], []),
                    "claim_type": "documented",
                    "origin": st.get("origin"),
                    "text": st[frame].replace(SLOT, phrase),
                })
            # A pair is the two frames of ONE stem in ONE sector. Never across sectors: pairing
            # across them would make the frame gap and the sector difference the same number,
            # which is the one confound this design exists to avoid.
            a, b = pair
            a["mirror_of"], b["mirror_of"] = b["id"], a["id"]
            items.extend(pair)
    return items


def _skeletons(text, phrase):
    """Every skeleton obtainable by replacing exactly ONE occurrence of `phrase` with the slot.

    Not `text.replace(phrase, SLOT)`. That replaces EVERY occurrence, so a phrase whose words
    also appear in the stem's fixed text -- "the staff who [PATH] hire staff", with a defence
    phrase of "staff" -- came back as `the [PATH] who [PATH] hire [PATH]`, and a correct bank
    was refused for differing by more than the slot. Enumerating one-at-a-time and intersecting
    across the group finds the single position that is actually the slot.
    """
    out, start = set(), 0
    if not phrase:
        return out
    while True:
        at = text.find(phrase, start)
        if at < 0:
            return out
        out.add(text[:at] + SLOT + text[at + len(phrase):])
        start = at + 1


def verify_slot_only(items):
    """The instrument's central guarantee, checked without reference to the stems.

    Across the sector variants of one (stem, frame), the text must be identical apart from the
    path phrase. If it is not, a sector difference could be wording, and every number the
    instrument produces is about the items rather than the models.

    This is the standalone check -- it is what a reader of the published bank can run without
    the stems file. `verify_against_stems` is the stronger one and is what the gate uses.
    """
    bad = []
    sectors = {it.get("sector") for it in items}
    by_sector_phrase = {}
    for it in items:
        by_sector_phrase.setdefault(it.get("sector"), set()).add(it.get("path_phrase"))
    for sector, phrases in sorted(by_sector_phrase.items(), key=lambda kv: str(kv[0])):
        if len(phrases) > 1:
            bad.append("sector %s has %d different path phrases (%s) -- one sector contributes "
                       "one phrase, or the sector is not what varies"
                       % (sector, len(phrases),
                          ", ".join(sorted(repr(p) for p in phrases))))

    by = {}
    for it in items:
        by.setdefault((it.get("stem"), it.get("frame")), []).append(it)
    for (stem, frame), group in sorted(by.items(), key=lambda kv: str(kv[0])):
        # A GROUP OF ONE PASSES ANY IDENTITY TEST. Requiring full sector coverage is what makes
        # a deleted variant a defect rather than a quieter bank.
        if len(group) != len(sectors):
            bad.append("stem %s %s half has %d sector variant(s), not %d -- a missing variant "
                       "passes every identity check there is"
                       % (stem, frame, len(group), len(sectors)))
            continue
        common = None
        for it in group:
            cand = _skeletons(it.get("text", ""), it.get("path_phrase", ""))
            if not cand:
                bad.append("stem %s %s half, sector %s: its path phrase does not appear in its "
                           "own text" % (stem, frame, it.get("sector")))
                common = set()
                break
            common = cand if common is None else (common & cand)
        if common is not None and not common:
            bad.append("stem %s %s half differs between sectors by more than the slot: %s"
                       % (stem, frame,
                          " | ".join("%s -> %r" % (it.get("sector"), (it.get("text") or "")[:60])
                                     for it in group)))
    return bad


def verify_against_stems(spec, on_disk, exemplars=None):
    """-> (problems, exemplar_notes). Diff the bank on disk against what the stems produce.

    THIS is what the gate runs, and it is the only check here that can fail for a real reason:
    re-deriving a bank and then verifying the derivation proves nothing about the file anyone
    will collect against.
    """
    want = build(spec, exemplars=exemplars)
    problems, notes = [], []
    if len(want) != len(on_disk):
        problems.append("the bank on disk has %d items; the stems produce %d"
                        % (len(on_disk), len(want)))
    by_id = {it.get("id"): it for it in on_disk}
    for w in want:
        got = by_id.get(w["id"])
        if got is None:
            problems.append("item %d is in the stems and not in the bank" % w["id"])
            continue
        for field in MEASURED_FIELDS:
            if got.get(field) != w[field]:
                problems.append("item %d %s: bank has %r, the stems produce %r"
                                % (w["id"], field, got.get(field), w[field]))
        if got.get("exemplars") != w["exemplars"]:
            notes.append("item %d exemplars differ from the current dataset" % w["id"])
    for extra in sorted(set(by_id) - {w["id"] for w in want}):
        problems.append("item %r is in the bank and not in the stems" % extra)
    return problems, notes


def _print(problems, header, why=None):
    print("REFUSED -- %s" % header)
    for p in problems[:40]:
        print("  * %s" % p)
    if len(problems) > 40:
        print("  ... and %d more" % (len(problems) - 40))
    if why:
        print("")
        print(why)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--stems", required=True, help="JSON: stems, path_phrases")
    ap.add_argument("--out", default=DEFAULT_BANK, help="the bank to write, or to check")
    ap.add_argument("--check", action="store_true",
                    help="diff the bank on disk against the stems; write nothing")
    a = ap.parse_args(argv)

    if not os.path.exists(a.stems):
        print("NOT APPLICABLE -- no stems file at %s" % a.stems)
        print("")
        print("Write one with `faction_reading_pack.py` open beside you: four mirrored stems,")
        print("each half carrying one %s, and one path phrase per sector." % SLOT)
        return 2

    spec = json.load(io.open(a.stems, encoding="utf-8"))
    problems = validate(spec)
    if problems:
        _print(problems, "%d problem(s) with the authored text:" % len(problems))
        return 1

    # A CHECK WITH AN EMPTY CORPUS PASSES EVERYTHING. The no-naming rule is enforced against
    # the MCP's people and institutions; without that dataset the loop above runs over nothing
    # and reports clean. This study has caught three checks reporting success having examined
    # zero inputs, so an unrunnable check reports NOT APPLICABLE rather than pass.
    if not _mcp_names():
        print("NOT APPLICABLE -- the Ratchet MCP dataset is not at %s" % MCP)
        print("")
        print("The no-naming rule cannot be enforced without it, and a check with an empty")
        print("corpus passes everything. Nothing was built.")
        return 2

    try:
        exemplars = _sourced_exemplars()
    except Exception as exc:                            # noqa: BLE001
        print("REFUSED -- the exemplar rule could not be applied: %s: %s"
              % (type(exc).__name__, exc))
        print("")
        print("Exemplars are pre-registered as 'most sources, then by label' over people.jsonl.")
        print("Falling back to a list in the stems file would put provenance back in the hands")
        print("of whoever wrote the spec, which is what deriving them exists to prevent.")
        return 1

    items = build(spec, exemplars=exemplars)
    thin = sorted({"%s (%d)" % (it["sector"], len(it["exemplars"])) for it in items
                   if len(it["exemplars"]) < EXEMPLARS_MINIMUM})
    if thin:
        _print(["fewer than %d sourced exemplars for: %s"
                % (EXEMPLARS_MINIMUM, ", ".join(thin))],
               "the sourced provenance is too thin:",
               "Exemplars are how a reader traces a proposition to the documented pattern, and\n"
               "they are the only place this instrument names anyone. A sector that cannot\n"
               "produce three is a sector with no evidence behind its item.")
        return 1

    slot_bad = verify_slot_only(items)
    if slot_bad:
        _print(slot_bad, "the sector variants differ by more than the slot:",
               "A sector difference would then be wording. This is the instrument's whole\n"
               "claim and it is checked, not assumed.")
        return 1

    if a.check:
        if not os.path.exists(a.out):
            print("NOT APPLICABLE -- no bank at %s" % a.out)
            print("")
            print("The stems are valid and produce %d items. Build it with --out to create the"
                  % len(items))
            print("bank this check compares against.")
            return 2
        on_disk = (json.load(io.open(a.out, encoding="utf-8")) or {}).get("items") or []
        drift, notes = verify_against_stems(spec, on_disk, exemplars=exemplars)
        if drift:
            _print(drift, "%d difference(s) between the bank on disk and the stems:" % len(drift),
                   "The bank is what models are shown. If it no longer matches the sentences\n"
                   "the author wrote, the instrument is not the one that was signed off.")
            return 1
        print("%s matches its stems: %d items, %d pairs, all %d measured fields."
              % (os.path.basename(a.out), len(on_disk), len(on_disk) // 2,
                 len(MEASURED_FIELDS)))
        for n in notes[:5]:
            print("  note: %s" % n)
        if notes:
            print("  (%d item(s) carry exemplars that differ from the dataset as it stands "
                  "today -- provenance drift, not an instrument change)" % len(notes))
        return 0

    print("%d items, %d pairs, %d stems x %d sectors"
          % (len(items), len(items) // 2, len(spec["stems"]), len(SECTORS)))
    print("every sector variant identical apart from the path phrase")

    bank = {
        "schema": "item-bank/1",
        "instrument": "ratchet-factions",
        "version": "v1",
        "source": ("Authored by Ian Gorrie. Four mirrored stems and four path phrases, "
                   "instantiated mechanically into %d items by instantiate_stems.py. Items "
                   "abstract documented staffing patterns from research/ratchet-mcp and carry "
                   "their exemplars as provenance; no item names a person or a firm."
                   % len(items)),
        "position_scale": "0=Strongly Disagree, 1=Disagree, 2=Agree, 3=Strongly Agree",
        "counts": {"items": len(items), "pairs": len(items) // 2,
                   "stems": len(spec["stems"]), "sectors": len(SECTORS)},
        "items": items,
    }
    with io.open(a.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(bank, fh, indent=2, ensure_ascii=False)
    print("wrote %s" % a.out)
    print("")
    print("NOT COLLECTABLE YET. Next: render_item_read.py --items %s, read every pair, tick "
          "the boxes, then check_instrument_approved.py." % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
