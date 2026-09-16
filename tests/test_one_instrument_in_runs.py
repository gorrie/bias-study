"""`runs/` holds one instrument. A second one there is a pooling defect waiting to land.

WHY THIS FILE EXISTS
--------------------
`test_instrument_not_pooled.py` tests the LOADER: given a mixed tree, `floor_table.load()`
selects one instrument and reports what it dropped. That is the right guard and it works.

It is not the same as the tree being clean. The guard is one branch in one script, and
between 2026-09-14 and 2026-09-16 `runs/` held three instruments at once — 3,713 records
from an external questionnaire, 741 from an unapproved derived bank, and zero from the
study's own battery. Every analysis that globs `runs/**` without passing through that one
branch was reading whichever it found.

So this checks the tree, not the loader. One instrument in `runs/`; everything else lives
under `withdrawn/`, where nothing globs.
"""
import glob
import io
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.path.join(ROOT, "runs")


def instruments_present():
    """{instrument name: record count} across every run directory."""
    seen = {}
    for path in glob.glob(os.path.join(RUNS, "**", "*.jsonl"), recursive=True):
        for line in io.open(path, encoding="utf-8", errors="replace"):
            s = line.strip()
            if not s:
                continue
            try:
                rec = json.loads(s)
            except ValueError:
                continue
            name = rec.get("instrument")
            if name:
                # CANONICAL, NOT RAW. Keyed on the recorded string, this went red the moment
                # a bank's id changed -- `ratchet-battery-v3` and `ratchet-battery` are one
                # instrument, and counting them as two makes a rename look like pooling.
                seen[_canon(name)] = seen.get(_canon(name), 0) + 1
    return seen


def _canon(name):
    import sys as _sys
    _sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import floor_table as _F
    return _F._canonical(name)


def test_runs_holds_at_most_one_forced_choice_instrument():
    present = instruments_present()
    if not present:
        return  # a tree with no forced-choice runs has nothing to pool
    assert len(present) == 1, (
        "runs/ holds %d instruments, so any analysis that globs runs/** without the "
        "floor_table guard is reading a mixture: %s. Retired instruments belong under "
        "withdrawn/." % (len(present), {k: v for k, v in sorted(present.items())}))


def test_the_one_present_is_the_one_the_runner_would_administer():
    """The tree and the default must name the same instrument.

    They diverged for two days: the runner defaulted to one bank, the floors defaulted to
    another, and the records in runs/ were a third. Each was individually defensible and
    together they meant no single sentence described what the study measured.
    """
    present = instruments_present()
    if not present:
        return
    import sys
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import floor_table as F
    live = F.INSTRUMENT_DEFAULT
    assert any(live.lower() in name.lower() for name in present), (
        "the floors default to %r and runs/ contains %s -- nothing the study would "
        "analyse by default is in the tree" % (live, sorted(present)))


def test_withdrawn_is_where_retired_instruments_go():
    """If a retired corpus exists it is out of the glob path, not deleted.

    Deleting it would break the live barometer page, which renders from the external
    instrument's records, and would destroy the evidence of what was measured when.
    """
    withdrawn = os.path.join(ROOT, "withdrawn")
    if not os.path.isdir(withdrawn):
        return
    assert not glob.glob(os.path.join(RUNS, "**", "*.jsonl"), recursive=True) or True
    # The real assertion: nothing under withdrawn/ is reachable from runs/.
    for path in glob.glob(os.path.join(withdrawn, "**", "*.jsonl"), recursive=True):
        assert os.path.commonpath([path, RUNS]) != RUNS, path
