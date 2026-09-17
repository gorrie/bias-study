"""Every floor arm appears in the output, including the ones that measured nothing.

WHY THIS FILE EXISTS
--------------------
`all_floors()` built the table with `r = fn(); if not r: continue`. An arm that computed no
pairs returned None and left the table, and an absent row is indistinguishable from an arm
nobody ever wrote. Nothing printed a count, nothing named the arm, nothing said why.

That is how `floor_same_version` -- the paper's HEADLINE null -- spent 2026-09-16 pointed at
`runs/2026-08-31-lineage/**`, a directory that had moved to `withdrawn/` that morning. The
wave would have collected 252 sheets correctly and populated nothing, and the first symptom
would have been a missing row in a table with fourteen other rows in it.

The same shape was still waiting in `floor_quant`: it read two withdrawn quant-null
directories, and the requantisation pass planned for this instrument collects into the WAVE
directory. Sixty sheets, no row.

So: an arm that produces nothing is reported with a reason, and the three reasons are kept
apart -- a path that matches no file (a DEFECT), a source retired by a dated ruling, and an
arm whose corpus exists and is simply not collected yet.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import floor_table as F  # noqa: E402


def _run():
    computed = F.all_floors()
    return computed, F.uncomputed_report()


def test_every_arm_computes_a_row_or_says_why():
    """No arm may simply vanish. The two counts must add up to ALL_FLOORS."""
    computed, missing = _run()
    all_names = [fn.__name__ for fn in F.ALL_FLOORS]
    assert all_names, "ALL_FLOORS is empty -- this test would pass over nothing"
    assert len(all_names) == len(set(all_names)), "an arm is listed twice in ALL_FLOORS"
    named = {arm for arm, _kind, _why in missing}
    assert len(named) == len(missing), "an arm reported twice in the uncomputed report"
    assert named <= set(all_names), sorted(named - set(all_names))
    # Arms that produced at least one row, derived the only way that cannot drift: the ones
    # NOT in the uncomputed report. Every arm is in exactly one of the two sets.
    produced = [n for n in all_names if n not in named]
    assert len(produced) == len(all_names) - len(named)
    if produced:
        assert computed, ("%d arm(s) are not in the uncomputed report and yet the table holds "
                          "no rows: %s" % (len(produced), ", ".join(produced)))
    else:
        assert not computed, "no arm computed, yet the table holds rows"
    # And every arm named in the report carries a reason, not a bare name.
    for arm, kind, why in missing:
        assert kind in ("path", "retired", "data"), (arm, kind)
        assert why and len(why) > 20, (arm, why)


def test_no_arm_reads_a_path_that_matches_nothing():
    """The live gate. A dead source is a broken arm, not an empty one.

    An arm whose corpus was withdrawn on purpose is declared in RETIRED_SOURCES with a reason
    and a date. Anything else pointing at a path with no files behind it is the defect this
    file is named for.
    """
    _computed, missing = _run()
    broken = [(arm, why) for arm, kind, why in missing if kind == "path"]
    assert not broken, (
        "%d floor arm(s) read a source pattern that matches no file, and a floor arm that "
        "reads nothing does not fail -- it leaves the table silently:\n%s"
        % (len(broken), "\n".join("  %s: %s" % (a, w) for a, w in broken)))


def test_retired_sources_are_still_read_by_an_arm():
    """RETIRED_SOURCES is a ruling, not a suppression list.

    A dated exemption that outlives the code it was written for is how a real dead path gets
    waved through later. Every pattern listed must still be globbed by some arm; when an arm
    stops reading one, the entry comes out.
    """
    F.all_floors()
    read = {p for reads in F.ARM_SOURCES.values() for p, _n in reads}
    stale = sorted(p for p in F.RETIRED_SOURCES if p not in read)
    assert not stale, (
        "RETIRED_SOURCES names %d pattern(s) no arm reads any more -- delete the entr%s "
        "rather than leaving an exemption with nothing under it: %s"
        % (len(stale), "y" if len(stale) == 1 else "ies", ", ".join(stale)))


def test_the_collection_source_literal_matches_the_arm_that_owns_it():
    """COLLECTION_SOURCES spells the wave glob out; SAME_VERSION_GLOB is the real one.

    Two copies of a pattern is exactly the shape this project keeps getting hurt by. They are
    two only because one is defined above the other in the file, so the test holds them equal.
    """
    assert F.SAME_VERSION_GLOB in F.COLLECTION_SOURCES


def test_a_wave_in_the_tree_removes_the_pre_collection_exemption():
    """The exemption is conditional, and the condition is what keeps it honest.

    An absent wave source is excused only while the tree holds NO wave directory. Once one
    exists, a wave pattern that still matches nothing is the original defect -- a path that
    cannot find data sitting right there -- and must be reported BROKEN.
    """
    _computed, missing = _run()
    excused = [arm for arm, kind, why in missing
               if kind == "data" and "no run data at all" in why]
    if F._tree_has_run_data():
        assert not excused, ("this tree has a wave directory, so nothing may be excused as "
                             "pre-collection: %s" % ", ".join(excused))


def test_every_retirement_carries_a_reason():
    for pattern, why in F.RETIRED_SOURCES.items():
        assert why and len(why) > 40, pattern
        assert "2026" in why, ("a retirement is a dated ruling: %s" % pattern)


def test_sources_are_recorded_from_the_read():
    """The recording itself must not be vacuous.

    If `_record_source` stopped firing, every arm would report "read no source at all" and the
    gate above would go red for the wrong reason -- or, worse, the report would go empty and
    read as clean.
    """
    F.all_floors()
    assert F.ARM_SOURCES, "no arm recorded a source read -- the recorder is not firing"
    total = sum(n for reads in F.ARM_SOURCES.values() for _p, n in reads)
    # ONLY WHERE THERE IS DATA TO MATCH. The public mirror carries no run export -- `runs/`
    # is empty until a scrubbed export lands -- so every pattern correctly matches zero files
    # there. Asserting a non-zero total unconditionally made this test fail in the tree whose
    # emptiness is the expected state, which teaches the reader to ignore it.
    if F._tree_has_run_data():
        assert total > 0, "runs/ holds records but every recorded source matched zero files"
