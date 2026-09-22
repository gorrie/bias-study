#!/usr/bin/env python3
"""The citation metadata mints a PERMANENT DOI. Check it against the study that exists.

WHY THIS EXISTS
---------------
`CITATION.cff` is the one file in this project whose contents cannot be corrected after
release. A GitHub Release fires the Zenodo webhook, Zenodo reads this file, and the resulting
DOI record carries its title and abstract forever. A stale sentence anywhere else is a
correction; a stale sentence here is a permanent citation to a study that does not exist.

**Found 2026-09-18, unguarded:** the public mirror's `CITATION.cff` carried the title *"The
Hedge Is the Bias"* and an abstract describing "2866 runs, 166 models, 16 vendor keys" and
models declining "all 62 propositions" -- every one of those a figure from the RETIRED
instrument, in a file nothing checked. The private tree has no CITATION.cff at all, so a
reader of the private tree would conclude none exists. Both trees were wrong in opposite
directions and no gate looked at either.

WHAT IT CHECKS
--------------
1. The file exists in the tree that ships, and parses.
2. Required fields for a citable record: title, authors, licence, and a version or date.
3. No RETIRED INSTRUMENT figures. A count out of 62 items, or a corpus scale from the
   withdrawn questionnaire, is not this study's.
4. No WITHDRAWN TITLE. Titles this project has used and abandoned are listed by name, because
   the failure mode is reverting to one, not inventing a new one.
5. Scale claims in the abstract are checked against the live corpus where they can be, and
   REFUSED where the abstract hardcodes a number the corpus contradicts.

    python scripts/check_citation.py
    python scripts/check_citation.py --path ../bias-study-release/CITATION.cff

Exit 0 fit to mint, 1 defect, 2 NOT APPLICABLE (no CITATION.cff in this tree).
"""
from __future__ import annotations

import argparse
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import studypaths as _SP

#: Titles this project has used and withdrawn. Reverting to one is the realistic failure --
#: an export script copying an older file, or a merge resurrecting it -- so they are named.
WITHDRAWN_TITLES = {
    "the hedge is the bias":
        "names the May judged-instrument framing, whose corpus and headline are withdrawn "
        "(CORRECTIONS.md). Its abstract also carries retired-instrument scale.",
    "same version, different answers":
        "rests on a same-version null this corpus measures at 0 / 1 / 1 side-flips of 32. "
        "The finding it advertises is not there.",
}

#: Figures that can only have come from the retired 62-item questionnaire.
RETIRED_MARKERS = (
    (r"\b62\s+propositions?\b", "a 62-item count -- the retired questionnaire's length"),
    (r"\bof\s+62\b", "a denominator of 62 -- this instrument has 32 items"),
    (r"\b2[,\s]?866\s+runs?\b", "the retired instrument's corpus scale"),
    (r"\b166\s+models?\b", "the retired instrument's model count"),
    (r"\b16\s+vendor\s+keys\b", "the retired instrument's vendor tally"),
)

REQUIRED = ("title", "authors", "license")


def load(path):
    with io.open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def field(text, name):
    """A scalar field's value, INCLUDING when YAML folds it across lines.

    THIS RETURNED ">-" AND THE GATE CALLED IT A TITLE. A CITATION.cff written on 2026-09-20
    put the title in a folded block, because the title is long:

        title: >-
          97% agreement on contested normative propositions: presentation order
          moves LLM political scores as much as instruction

    The old pattern matched `.+` on the declaration line and captured the fold marker, so
    `title` came back as ">-" and every check downstream compared THAT against the withdrawn
    list. It passed. A withdrawn title written in folded form would have passed too, on the
    gate whose entire job is that a permanent DOI does not carry one -- "Fit to mint. Nothing
    here names a withdrawn title", having read no title at all.

    Folded and literal blocks (`>`, `>-`, `|`, `|-`, with optional indentation indicators) now
    consume their indented continuation lines and join them the way YAML does.
    """
    m = re.search(r"^%s:[ \t]*(.*)$" % re.escape(name), text, re.MULTILINE)
    if not m:
        return None
    head = m.group(1).strip()
    if not re.fullmatch(r"[>|][+-]?\d*", head):
        return head.strip('"').strip("'")
    # A block scalar: take the indented lines that follow and fold them into one string.
    lines = []
    for line in text[m.end():].splitlines():
        if line.strip() and not line[:1].isspace():
            break                      # dedented back to the next key
        if line.strip():
            lines.append(line.strip())
    return " ".join(lines) if lines else None


def _title_number_still_true(title):
    """A measured number IN THE TITLE has to still be the measurement.

    The title settled on 2026-09-20 opens "97% agreement on contested normative
    propositions". That is not a label, it is a figure from `intensity_by_claim.py`, and this
    study's entire finding is that such figures move: it read 97.0% before the corpus grew
    this week and 97.1% after. Rounded, both are 97 -- and the distance to a title that says
    the wrong thing is about four tenths of a point.

    Everything else in this repository can be corrected. The DOI cannot. So the number in the
    title is checked against the live corpus at mint time, and the release is refused if it
    has moved, rather than trusting that nobody re-collected anything since the title was
    chosen. A permanent citation is the one place where "it was true when I wrote it" is not
    a defence.

    Silent when the title carries no percentage, because a title without a number needs no
    check -- which is also the cheapest way to make this whole class of risk go away.
    """
    m = re.search(r"(\d{1,3})\s*%\s*agreement", title, re.IGNORECASE)
    if not m:
        return []
    claimed = int(m.group(1))
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import intensity_by_claim as IBC
        live = IBC.contested_agreement_pct()
    except Exception as exc:                                   # noqa: BLE001
        return ["the title claims %d%% agreement and this gate could not recompute it (%s). "
                "A number in a PERMANENT title that nothing verifies is the one kind of "
                "staleness that cannot be corrected later." % (claimed, exc)]
    if live is None:
        return ["the title claims %d%% agreement and the live figure could not be computed "
                "from the corpus. Refusing rather than assuming." % claimed]
    if round(live) != claimed:
        return ["TITLE NUMBER HAS MOVED: it says %d%% agreement, the corpus now gives %.1f%% "
                "(rounds to %d). Re-title or re-check before minting -- the DOI keeps this "
                "number forever." % (claimed, live, round(live))]
    return []


def _abstract_numbers_still_true(text):
    """The abstract mints too, so its measured figures get the same treatment as the title.

    Zenodo takes the whole citation record, not just the title. The 2026-09-21 abstract
    carries the agreement figure for contested normative propositions, and that figure is
    live: it read 97.0% before this week's collection and 97.1% after. Every other number in
    this repository can be corrected in the next commit. These two cannot, so they are
    recomputed at mint time and the release is refused if they have moved.

    Only the agreement pair is checked here, deliberately. It is the figure the abstract's
    central claim rests on -- that what is stable is agreement, not position -- and a gate
    that tried to parse every number out of English prose would fire on the ones it
    misunderstood and get switched off. A narrow check that runs beats a broad one that gets
    disabled.
    """
    m = re.search(r"agrees?\s+(\d{1,3}\.\d)%\s+of the time,?\s+against\s+(\d{1,3}\.\d)%",
                  text, re.IGNORECASE)
    if not m:
        return []
    claimed_norm, claimed_doc = float(m.group(1)), float(m.group(2))
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import intensity_by_claim as IBC
        live = IBC.measure()
    except Exception as exc:                                   # noqa: BLE001
        return ["the abstract states agreement figures and this gate could not recompute "
                "them (%s). They mint into a permanent DOI." % exc]
    pooled = (live or {}).get("pooled") or {}
    if not pooled.get("normative") or not pooled.get("documented"):
        return ["the abstract states agreement figures and the corpus could not produce "
                "them. Refusing rather than assuming."]
    out = []
    for label, claimed, key in (("contested normative", claimed_norm, "normative"),
                                ("documented", claimed_doc, "documented")):
        actual = pooled[key]["agree"] * 100.0
        if abs(actual - claimed) >= 0.05:
            out.append("ABSTRACT FIGURE HAS MOVED: it says %s agreement is %.1f%%, the corpus "
                       "now gives %.1f%%. The DOI keeps this number forever."
                       % (label, claimed, actual))
    return out


#: Number words this gate can read. Anything else in a counted slot is reported as
#: unreadable rather than skipped -- see the comment in `_more_abstract_numbers`.
_NUMBER_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
}


def _as_int(word):
    """An integer from a digit string or a number word, or None if this gate cannot read it."""
    if word is None:
        return None
    word = word.strip().lower()
    if word.isdigit():
        return int(word)
    if word in _NUMBER_WORDS:
        return _NUMBER_WORDS[word]
    if "-" in word:
        head, _, tail = word.partition("-")
        if head in _NUMBER_WORDS and tail in _NUMBER_WORDS:
            return _NUMBER_WORDS[head] + _NUMBER_WORDS[tail]
    return None


def _more_abstract_numbers(text):
    """The rest of the abstract's measured figures, recomputed.

    WHY THIS WAS NOT ENOUGH BEFORE. `_abstract_numbers_still_true` checks the agreement pair
    and says so, on the reasoning that a narrow check that runs beats a broad one that gets
    switched off. The reasoning is right and the coverage was not: a hostile pass on
    2026-09-21 planted `0.931`, `86.6%`, "14 models to 36" and "forty published studies" into
    a copy of this file and the gate returned **Fit to mint, exit 0**. Ten of the abstract's
    twelve measured figures minted unchecked into a permanent DOI.

    These are the cheap ones -- the emphasis contrast, the audit's two counts, the
    abliterated-build count and the instrument's shape. The position medians need a
    4000-draw bootstrap over every pair and are checked by `--positions`, which the release
    gate passes and an ordinary run does not, because a ten-minute gate run casually is a
    gate run never.
    """
    out = []
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    def claimed(pattern, cast=float):
        m = re.search(pattern, text, re.IGNORECASE)
        return None if not m else cast(m.group(1))

    # --- the instrument's own shape, from the bank
    try:
        import json as _json
        bank = _json.load(io.open(os.path.join(_SP.STUDY_DIR, "data", "ratchet-battery.json"),
                                  encoding="utf-8"))["items"]
        n_items = len(bank)
        n_pairs = len({i["pair_no"] for i in bank})
    except Exception as exc:                                   # noqa: BLE001
        out.append("could not read the instrument to check the abstract's shape (%s)" % exc)
    else:
        said_items = claimed(r"(\d{1,3})\s+author-written propositions", int)
        said_pairs = claimed(r"(\d{1,3})\s*\n?\s*mirrored pairs", int)
        if said_items is not None and said_items != n_items:
            out.append("ABSTRACT: says %d propositions, the instrument has %d"
                       % (said_items, n_items))
        if said_pairs is not None and said_pairs != n_pairs:
            out.append("ABSTRACT: says %d mirrored pairs, the instrument has %d"
                       % (said_pairs, n_pairs))

    # --- the audit's two counts
    try:
        import key_numbers as K
        audit = K.audit_scale()
    except Exception as exc:                                   # noqa: BLE001
        out.append("could not recompute the audit counts (%s)" % exc)
    else:
        # AN UNRECOGNISED NUMBER WORD IS A FAILURE, NOT A SKIP. The first version of this
        # carried a lookup table from "ten" to "sixteen" and returned None for anything else,
        # so planting "Of FORTY published studies audited" passed silently -- the check
        # declining to parse the very edit it exists to catch. Any word in that slot that is
        # not a number this gate understands now refuses.
        for pattern, key, what in (
                (r"Of\s+([\w-]+)\s+published studies audited", "external", "published "
                 "studies audited"),
                (r"against\s+([\w-]+)\s+methodological controls", "controls",
                 "methodological controls")):
            said = claimed(pattern, str)
            if said is None:
                continue
            n = _as_int(said)
            if n is None:
                out.append("ABSTRACT: %r is in the %s slot and this gate cannot read it as a "
                           "number, so the count was NOT checked. Refusing." % (said, what))
            elif n != audit[key]:
                out.append("ABSTRACT: says %s %s, the record holds %d"
                           % (said, what, audit[key]))

    # --- the emphasis contrast
    try:
        import intensity_by_claim as IBC
        live = IBC.measure()
    except Exception as exc:                                   # noqa: BLE001
        out.append("could not recompute the emphasis figures (%s)" % exc)
        live = None
    if live:
        pooled = live.get("pooled") or {}
        # ANCHORED ON "strongest available answer", not on the bare percentage. A first
        # version matched `against (\d+\.\d)% (for|of).{0,40}documented` and hit the
        # AGREEMENT sentence three paragraphs earlier -- reporting 99.0% as a moved emphasis
        # figure. A gate that matches the wrong sentence fails the right one.
        for label, pat, key in (
                ("normative endpoint",
                 r"strongest available answer on\s*\n?\s*(\d{1,3}\.\d)%", "normative"),
                ("documented endpoint",
                 r"and\s+(\d{1,3}\.\d)% of documented matters of record", "documented")):
            said_pct = claimed(pat)
            # `strong` is the endpoint share -- the field is named for the answer label
            # ("Strongly agree"), not for what the abstract calls it.
            got = (pooled.get(key) or {}).get("strong")
            if said_pct is not None and got is not None:
                if abs(got * 100.0 - said_pct) >= 0.05:
                    out.append("ABSTRACT FIGURE HAS MOVED: %s reads %.1f%%, the corpus gives "
                               "%.1f%%" % (label, said_pct, got * 100.0))

    # --- the abliterated class, which the abstract now states a count for
    said_abl = re.search(r"all\s+(\w+)\s+builds\s+with the\s*\n?\s*refusal direction", text,
                         re.IGNORECASE)
    if said_abl:
        want = _as_int(said_abl.group(1))
        if want is None:
            out.append("ABSTRACT: %r is in the abliterated-build-count slot and this gate "
                       "cannot read it as a number. Refusing." % said_abl.group(1))
        try:
            import agreement_by_training as ABT
            classes = (ABT.measure() or {}).get("classes") or {}
            got = None
            for name, rec in classes.items():
                if "ablit" in name.lower():
                    got = rec.get("models")
            if want is not None and got is not None and want != got:
                out.append("ABSTRACT: says %s abliterated builds, the corpus has %d"
                           % (said_abl.group(1), got))
        except Exception as exc:                               # noqa: BLE001
            out.append("the abstract states an abliterated-build count and this gate could "
                       "not recompute it (%s)" % exc)
    return out


def _position_numbers(text):
    """The position medians. Slow on purpose -- a 4000-draw bootstrap over every pair."""
    import subprocess
    here = os.path.dirname(os.path.abspath(__file__))
    try:
        got = subprocess.run([sys.executable,
                              os.path.join(here, "order_floor_position.py"), "--markdown"],
                             capture_output=True, text=True, timeout=3600)
    except Exception as exc:                                   # noqa: BLE001
        return ["the abstract states position medians and this gate could not recompute "
                "them (%s). They mint into a permanent DOI." % exc]
    rows = [l for l in got.stdout.split("\n") if l.startswith("| the balance")
            or l.startswith("| **reprinting")]
    if len(rows) != 2:
        return ["order_floor_position produced no table, so the abstract's position medians "
                "were NOT checked. That is a refusal, not a pass."]
    out = []
    instr = [c.strip().strip("*") for c in rows[0].split("|")]
    order = [c.strip().strip("*") for c in rows[1].split("|")]
    pairs = ((r"moves position by a median of\s+([\d.]+)", instr[3], "instruction median"),
             (r"different order moves it by a median of\s+([\d.]+)", order[3], "order median"),
             (r"order floor's p90 of\s+([\d.]+)", order[4], "order p90"))
    for pattern, live, label in pairs:
        m = re.search(pattern, text, re.IGNORECASE)
        if m and abs(float(m.group(1)) - float(live)) >= 5e-4:
            out.append("ABSTRACT FIGURE HAS MOVED: %s reads %s, the corpus gives %s"
                       % (label, m.group(1), live))
    m = re.search(r"(\w+[- ]?\w*)\s+per cent\s*\n?\s*of order pairs are themselves significant",
                  text, re.IGNORECASE)
    if m:
        spelled = {"forty-one": 41, "forty-two": 42, "forty-three": 43, "forty-four": 44,
                   "forty-five": 45, "forty-six": 46, "fifty": 50}
        want = spelled.get(m.group(1).lower().replace(" ", "-"))
        live = int(round(100.0 * float(order[6].split()[0]) / float(order[2])))
        if want is not None and want != live:
            out.append("ABSTRACT FIGURE HAS MOVED: it says %s per cent of order pairs are "
                       "significant, the corpus gives %d%%" % (m.group(1), live))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--path", default=None)
    ap.add_argument("--positions", action="store_true",
                    help="also recompute the abstract's position medians (slow: a 4000-draw "
                         "bootstrap over every pair). The release gate passes this.")
    a = ap.parse_args(argv)

    explicit = a.path is not None
    path = a.path or os.path.join(_SP.STUDY_DIR, "CITATION.cff")
    if not os.path.exists(path):
        # ABSENT IS THE CORRECT STATE OF THIS REPOSITORY UNTIL THE MOMENT OF RELEASE, and it
        # is a BLOCKER at the moment of release. Those are the same fact and the exit code has
        # to tell them apart, or deleting the file to keep it from going stale simply swaps a
        # wrong DOI for no DOI and nothing notices either.
        #
        # `--path` means a caller named a specific tree, which is what the release gate does.
        # Asking about a named tree and finding nothing is a refusal. Finding nothing in the
        # private tree nobody asked about is not.
        if explicit:
            print("REFUSED -- no CITATION.cff at %s" % path)
            print("")
            print("  A tree was named explicitly and carries no citable record. If this is the")
            print("  release check, the release cannot proceed: there is nothing for Zenodo to")
            print("  read and the DOI would carry whatever GitHub infers.")
            print("")
            print("  Write it from CITATION-TEMPLATE.md, which preserves the author block, the")
            print("  licence, the dated-not-numbered version rule and the reason the abstract")
            print("  carries no uncorrected findings. The file was removed on 2026-09-18")
            print("  because it had gone stale carrying a withdrawn title and retired-")
            print("  instrument scale -- absent was safer than wrong, and is still not ready.")
            return 1
        print("NOT APPLICABLE -- no CITATION.cff at %s" % path)
        print("")
        print("  This is the expected state of the PRIVATE tree while the title is undecided.")
        print("  It is NOT the expected state of the tree that ships: check the mirror")
        print("  explicitly with --path, because a citation file that exists only there is a")
        print("  citation file nothing in this tree ever reads.")
        return 2

    text = load(path)
    problems = []

    for name in REQUIRED:
        if not re.search(r"^%s:" % re.escape(name), text, re.MULTILINE):
            problems.append("missing required field `%s`" % name)
    if not (field(text, "version") or field(text, "date-released")):
        problems.append("neither `version` nor `date-released` -- the record is undated")

    title = (field(text, "title") or "").strip().lower().rstrip(".")
    for bad, why in WITHDRAWN_TITLES.items():
        if title.startswith(bad):
            problems.append("TITLE IS WITHDRAWN: %r -- %s" % (field(text, "title"), why))

    for pattern, why in RETIRED_MARKERS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            line = text[:m.start()].count("\n") + 1
            problems.append("line %d: %s (%r)" % (line, why, m.group(0)))

    problems.extend(_title_number_still_true(field(text, "title") or ""))
    problems.extend(_abstract_numbers_still_true(text))
    problems.extend(_more_abstract_numbers(text))
    if a.positions:
        problems.extend(_position_numbers(text))
    else:
        print("  NOTE: the abstract's position medians were NOT recomputed. Pass --positions")
        print("  before minting; the release gate does.")

    print("")
    print("  CITATION.cff -- %s" % path)
    print("  title: %s" % (field(text, "title") or "MISSING"))
    print("")
    if not problems:
        print("  Fit to mint. Nothing here names a retired instrument or a withdrawn title,")
        print("  and the required fields are present.")
        print("")
        print("  This gate cannot tell you the title is GOOD, only that it is not one this")
        print("  project has already abandoned. The choice is the author's and it is")
        print("  permanent: a Release fires Zenodo and the DOI carries this text forever.")
        return 0

    print("  REFUSED -- %d problem(s). This file mints a PERMANENT DOI." % len(problems))
    print("")
    for p in problems:
        print("    - %s" % p)
    print("")
    print("  A stale sentence anywhere else in this repository is a correction. A stale")
    print("  sentence here is a permanent citation to a study that does not exist.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
