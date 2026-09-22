"""The corpus map's claim about what is on disk must match what is on disk.

WHY THIS FILE EXISTS
--------------------
`CORPUS-MAP-2026-09-14.md` shipped to the public mirror with a banner reading:

    ## THE REPAIRED CORPORA ARE NOT IN THIS REPOSITORY YET
    ... the derived corpora below are **pending export** to this public tree ...
    **Every original run in this repository is the damaged version.**

The export landed the next day, 2026-09-15, in `4d734dd`: thirteen
`2026-09-14-recollect-*` repair runs and ten `*-spliced` derived corpora,
including the repaired main run. The map was edited again on 2026-09-16 and the
banner survived the edit. For a week a public document told readers to discount
figures the repository was already shipping the repair for.

That is the SAME defect the map exists to document -- a stated corpus that is not
the corpus on disk -- reproduced in the map's own banner. A disclosure is a claim
and it expires like any other. `CORRECTIONS.md` entry 27.

WHAT THIS CHECKS, AND WHY IT IS TWO-WAY
---------------------------------------
A one-way "the banner must be accurate when present" test passes forever once
somebody deletes the banner, and a one-way "the banner must be present while the
data is absent" test turns into a lie of the opposite sign the moment the data
lands -- which is exactly what happened. So both directions are asserted:

  * repairs present on disk  ->  the absence banner must NOT be in the file
  * repairs absent from disk ->  the file must not claim they are here

It runs in both trees. The private study tree carries no repair corpora and no
banner, which is consistent; the mirror carries both corpora and a corrected
banner, which is also consistent. Neither tree is special-cased.
"""
import glob
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAP = os.path.join(ROOT, "CORPUS-MAP-2026-09-14.md")

#: The withdrawn absence claim, in the wordings it was published in. Matched
#: case-insensitively. Short fragments, so a reworded banner still trips it.
ABSENCE_CLAIMS = (
    "repaired corpora are not in this repository",
    "pending export",
    "every original run in this repository is the damaged version",
    "until the export lands",
)

#: The opposite failure: asserting the repairs are here in a tree that has none.
PRESENCE_CLAIMS = (
    "the repaired corpora are here",
)


def _repair_runs():
    """Repair and derived-corpus directories actually on disk, in either root."""
    found = []
    for root in ("data", "runs"):
        base = os.path.join(ROOT, root)
        if not os.path.isdir(base):
            continue
        for pat in ("*-recollect-*", "*recollect*", "*-spliced"):
            found += [os.path.basename(p) for p in glob.glob(os.path.join(base, pat))
                      if os.path.isdir(p)]
    return sorted(set(found))


def _text():
    if not os.path.exists(MAP):
        return None
    return io.open(MAP, encoding="utf-8", errors="replace").read().lower()


def test_the_map_does_not_deny_corpora_this_tree_contains():
    text = _text()
    if text is None:
        return  # the map is not in every tree; nothing to check where it is absent
    present = _repair_runs()
    if not present:
        return
    asserted = [c for c in ABSENCE_CLAIMS if c in text]
    assert not asserted, (
        "CORPUS-MAP-2026-09-14.md still tells readers the repaired corpora are not here, "
        "and %d of them are on disk.\n"
        "  claims still in the file: %s\n"
        "  directories present:      %s\n"
        "A banner that discounts figures the repository ships the repair for is worse than "
        "no banner. Say which run to read instead." % (
            len(present), ", ".join(repr(a) for a in asserted), ", ".join(present[:8])))


def test_the_map_does_not_claim_corpora_this_tree_lacks():
    text = _text()
    if text is None:
        return
    if _repair_runs():
        return
    asserted = [c for c in PRESENCE_CLAIMS if c in text]
    assert not asserted, (
        "CORPUS-MAP-2026-09-14.md says the repaired corpora are in this tree and no repair "
        "or spliced directory exists under data/ or runs/.\n"
        "  claims in the file: %s\n"
        "The correction of 2026-09-22 replaced an absence claim with a presence claim; a "
        "presence claim is a claim too." % ", ".join(repr(a) for a in asserted))
