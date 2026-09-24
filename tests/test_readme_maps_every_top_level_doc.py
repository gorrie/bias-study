"""Every file at the top of the repository is placed in the README's layout map.

WHY THIS FILE EXISTS
--------------------
The top level of this repository held the paper beside a roadmap, a findings file and a
judge-method plan all written for the design retired on 2026-09-16, and nothing said which was
which. A reader arriving to cite the paper found `FINDINGS.md` first -- a findings file whose
headline counts belong to an instrument this study no longer uses -- with no status line
telling them so. Correct for a working repository, wrong for one being cited.

The fix was a map: README "Repository layout" places every top-level entry in one of three
groups, and every document in the retired group says HISTORICAL at its head. A map written by
hand goes stale the day somebody adds a file, so this is the control:

  1. every non-hidden top-level entry is named in the layout section, and
  2. every FILE in the retired-design group carries a HISTORICAL banner near its top.

It checks nothing it cannot see: it refuses if it finds fewer entries than the repository
plainly holds, because a map test that listed an empty directory would pass.
"""
import io
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Not repository content: interpreter and test-runner caches, and the map itself.
IGNORED = {"__pycache__", "README.md"}

#: The retired group's heading, as the README spells it.
RETIRED_HEADING = "**The retired design"


def _layout_section():
    text = io.open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    m = re.search(r"^## Repository layout\s*$(.*?)^## ", text, re.M | re.S)
    assert m, "README.md has no '## Repository layout' section followed by another section"
    return m.group(1)


def _named(section):
    """Every backticked token in the section, with any trailing slash dropped."""
    return {t.rstrip("/") for t in re.findall(r"`([^`\s]+)`", section)}


def _top_level():
    return sorted(n for n in os.listdir(ROOT)
                  if not n.startswith(".") and n not in IGNORED)


def test_every_top_level_entry_is_mapped():
    entries = _top_level()
    # Vacuity guard: this repository holds well over twenty top-level entries.
    assert len(entries) >= 20, "found only %d top-level entries in %s" % (len(entries), ROOT)
    named = _named(_layout_section())
    unmapped = [n for n in entries if n not in named]
    assert not unmapped, (
        "top-level entries missing from README 'Repository layout' -- place each one in "
        "a group: %s" % ", ".join(unmapped))


def test_retired_group_files_say_historical():
    section = _layout_section()
    start = section.find(RETIRED_HEADING)
    assert start >= 0, "README layout has no retired-design group"
    files = [n for n in sorted(_named(section[start:]))
             if os.path.isfile(os.path.join(ROOT, n))]
    assert len(files) >= 5, "retired group names only %d files" % len(files)
    unmarked = []
    for n in files:
        head = io.open(os.path.join(ROOT, n), encoding="utf-8").read()[:1500]
        if "HISTORICAL" not in head:
            unmarked.append(n)
    assert not unmarked, "retired-design files with no HISTORICAL banner at the top: %s" % (
        ", ".join(unmarked))
