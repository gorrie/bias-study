#!/usr/bin/env python3
"""Every numeric claim in the paper that NO gate is checking.

WHY THIS EXISTS. `key_numbers.py --check` verifies 54 numeric claims and reports "all
load-bearing numbers match". That sentence is true and is routinely misread as "the paper's
numbers are correct" -- it means the numbers SOMEBODY REGISTERED are correct. On 2026-09-22
section 1b carried three stale figures through a green suite: `gpt-6-astra` declining "8
times out of 8" when the live table says 17 of 18, its sibling "8 of 8" against 15 of 18,
and a placebo arm of "0 refusals in 7" against 0 in 30. All three had been wrong since the
refusal population was redeclared. None was registered, so nothing looked.

The section heading literally read "RE-MEASURE BEFORE PUBLICATION" and had for days.

So this inverts the question. Instead of asking whether the registered claims still hold, it
asks which claims are registered at all, and prints the remainder for a human to read. It
makes no judgement about whether an unregistered number is right -- it cannot -- and that is
the point: an ungated number is one nobody has checked since the day it was typed.

    python scripts/ungated_numbers.py                # the review list, by section
    python scripts/ungated_numbers.py --count        # just the totals
    python scripts/ungated_numbers.py --paper <path>

Reads only.
"""
from __future__ import annotations

import argparse
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, HERE)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PAPER = os.path.join(STUDY, "PAPER-below-the-floor.md")

#: Numbers that are not claims about the corpus. Each pattern is anchored on the shape that
#: makes it inert, never on the digits themselves -- "2024" is a year in `Röttger (2024)` and
#: a quantity in "2024 answers", and only the context tells them apart.
INERT = [
    (re.compile(r"\b(19|20)\d\d-\d\d-\d\d\b"), "date"),
    (re.compile(r"\((19|20)\d\d[a-z]?\)"), "citation year"),
    (re.compile(r"\barXiv:\s*\d{4}\.\d{4,5}\b", re.I), "arXiv id"),
    (re.compile(r"\bdoi:\s*\S+", re.I), "doi"),
    (re.compile(r"\b10\.\d{4,}/\S+"), "doi"),
    (re.compile(r"§\s*\d+[a-z]?(\.\d+)?"), "section reference"),
    (re.compile(r"\bsection\s+\d+[a-z]?\b", re.I), "section reference"),
    (re.compile(r"^#{1,6}\s*\d+[a-z]?\.", re.M), "section number"),
    (re.compile(r"\bcommit\s+[0-9a-f]{7,}\b", re.I), "commit"),
    (re.compile(r"\b(19|20)\d\d\b(?!\s*(answers|items|runs|records|sheets|models|pairs))"),
     "bare year"),
]

NUM = re.compile(r"(?<![\w.$])\d[\d,]*(?:\.\d+)?(?![\w])")


def _strip(text):
    """Remove what is generated, quoted from code, or machine-owned."""
    text = re.sub(r"<!-- GEN:(\w+).*?<!-- /GEN:\1 -->", " ", text, flags=re.S)
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    # The reference list is other people's bibliographic data, not this study's measurements.
    text = re.split(r"^## References\s*$", text, flags=re.M)[0]
    return text


def _sentences(text):
    """(section, sentence, quoted). `quoted` marks blockquote blocks.

    A BLOCKQUOTE IS A DIFFERENT KIND OF CLAIM and mixing the two made the review list
    unreadable. In this paper `>` carries correction notices ("this read 8 of 8 until
    2026-09-21"), withdrawal records and quotations from other people's papers. Those numbers
    are SUPPOSED to be unregistered: a correction notice states what a figure used to say, so
    gating it against the live value would force it to lie. What needs reading is the body
    prose, which asserts in the present tense.
    """
    out, section = [], "(front matter)"
    for block in text.split("\n\n"):
        head = re.match(r"^#{2,3}\s+(.+)$", block.strip())
        if head:
            section = head.group(1).strip()
            continue
        # `*(...)*` IS THIS PAPER'S OTHER CORRECTION FORM, and it is a body block rather than
        # a blockquote. "This read 8 of 8 until 2026-09-21" is a record of a figure that is no
        # longer true, so registering it against the live value would force it to lie -- the
        # same reason `>` blocks are held back. Counting them as live claims made the review
        # list GROW every time a correction was written, which punishes the right action.
        stripped = block.lstrip()
        quoted = stripped.startswith(">") or stripped.startswith("*(")
        flat = " ".join(block.split())
        if not flat or flat.startswith("|"):
            # A table row is not prose; the generated blocks are gated by `gen_paper --check`.
            continue
        for s in re.split(r"(?<=[.!?])\s+", flat):
            if s.strip():
                out.append((section, s.strip(), quoted))
    return out


def gated_phrases():
    """Every phrase any surface registers, with its key."""
    import key_numbers as K
    out = []
    for row in K.build() + K.surface_numbers():
        phrase = row.get("phrase")
        value = row.get("value")
        if not phrase or value is None:
            continue
        try:
            rendered = (phrase % value) if "%(" not in phrase else None
        except (TypeError, ValueError):
            rendered = None
        out.append((row["key"], rendered, phrase))
    for surface in getattr(K, "SURFACES", {}).values():
        for key, phrase in (surface.get("phrases") or {}).items():
            out.append((key, None, phrase))
    return out


def _hand_tables(raw):
    """Every markdown table outside a GEN block, numeric ones first.

    WHY. Generating a table removes the risk from the table and relocates it to every copy of
    the table. On 2026-09-22 this paper carried SIX hand-typed tables while `gen_paper --check`
    reported all thirteen generated blocks current, and five of the six were stale -- including
    two copies of the same by-condition measurement, sixty lines apart, disagreeing with each
    other AND with the corpus, and two more sitting three lines under a sentence telling the
    reader to consult the generated table rather than a copy.

    Not a gate. Some hand tables are correct and belong: a prose table of pre-registrations, a
    reallocation argument, a list of withdrawals. The numeric ones are the question, and a
    human answers it.
    """
    lines = raw.split("\n")
    gen, inblk = set(), False
    for i, line in enumerate(lines):
        if re.match(r"<!--\s*GEN:", line):
            inblk = True
        if re.match(r"<!--\s*/GEN:", line):
            inblk, _ = False, gen.add(i)
            continue
        if inblk:
            gen.add(i)
    found, i = [], 0
    while i < len(lines):
        if lines[i].lstrip().startswith("|") and i not in gen:
            j = i
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                j += 1
            if j - i >= 3:
                body = " ".join(lines[i + 2:j])
                found.append((i + 1, j - i, len(NUM.findall(body)), lines[i].strip()))
            i = j
        else:
            i += 1
    print("")
    print("  HAND-TYPED TABLES -- %d outside any GEN block" % len(found))
    print("  A numeric one is a second copy of a measurement. Check it against the command,")
    print("  then either delete it and point at the generated block, or register its cells.")
    print("")
    for ln, rows, nums, head in sorted(found, key=lambda t: -t[2]):
        print("    line %5d  %2d rows  %3d numeric cell(s)  %s"
              % (ln, rows, nums, head[:80]))
    print("")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--paper", default=PAPER)
    ap.add_argument("--count", action="store_true")
    ap.add_argument("--tables", action="store_true",
                    help="every markdown table NOT inside a GEN block, with whether its cells "
                         "look numeric. A hand table beside a generated one is the defect the "
                         "generator was built to remove")
    ap.add_argument("--all", action="store_true",
                    help="include blockquote sentences -- corrections and quotations, whose "
                         "numbers are deliberately not registered")
    a = ap.parse_args(argv)

    if not os.path.exists(a.paper):
        print("no such file: %s" % a.paper, file=sys.stderr)
        return 2
    raw = io.open(a.paper, encoding="utf-8").read().replace("\r\n", "\n")
    if a.tables:
        return _hand_tables(raw)
    text = _strip(raw)

    phrases = gated_phrases()
    rendered = [r for _k, r, _p in phrases if r]
    # A sentence is COVERED when a rendered gated phrase appears in it. Fuzzy on whitespace
    # only -- a phrase that has drifted is exactly what `--check` is for and must not be
    # silently counted as covered here.
    def covered(sentence):
        flat = " ".join(sentence.split())
        return any(" ".join(r.split()) in flat for r in rendered)

    ungated, quoted_n, inert_hits, total = [], 0, 0, 0
    for section, sentence, quoted in _sentences(text):
        masked = sentence
        for rx, _why in INERT:
            masked, n = rx.subn(" ", masked)
            inert_hits += n
        nums = NUM.findall(masked)
        if not nums:
            continue
        total += len(nums)
        if covered(sentence):
            continue
        if quoted:
            quoted_n += 1
            if not a.all:
                continue
        ungated.append((section, nums, sentence, quoted))

    if a.count:
        print("gated phrases registered : %d" % len(phrases))
        print("numeric tokens in prose  : %d (after %d inert)" % (total, inert_hits))
        print("sentences with an UNGATED number: %d in body prose, %d more in blockquotes "
              "(corrections and quotations -- see --all)" % (len(ungated), quoted_n))
        return 0

    print("")
    print("  UNGATED NUMERIC CLAIMS -- %d sentence(s) of body prose" % len(ungated))
    print("  No gate is checking these. That does not make them wrong; it means nothing has")
    print("  looked at them since they were typed. Read each one against its command.")
    if not a.all:
        print("  %d blockquote sentence(s) are held back: corrections state what a figure USED"
              % quoted_n)
        print("  to say, so gating them against the live value would force them to lie. --all")
    print("")
    last = None
    for section, nums, sentence, quoted in ungated:
        if section != last:
            print("  --- %s" % section)
            last = section
        mark = "q " if quoted else "  "
        print("    %s%s" % (mark, sentence[:150] + ("..." if len(sentence) > 150 else "")))
    print("")
    print("  %d registered, %d body sentence(s) unregistered." % (len(phrases), len(ungated)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
