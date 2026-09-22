"""Say so when the corpus is being written underneath the suite.

WHY THIS EXISTS
---------------
Many tests here read `runs/` and assert something about what they find. A five-minute suite
run against a corpus that is actively collecting is comparing two different corpora, and the
failures it produces name the wrong cause: on 2026-09-19
`test_floors_survive_a_reordered_corpus` failed with *"a floor changed when the corpus was read
in another order"* while four collection chains were writing. The order was fine. The corpus had
grown between two reads.

That was fixed in the one test. Then three more failed the same way the same evening --
`test_gated_values_are_not_none` and two siblings, all of which pass alone and fail in the
suite, because `key_numbers`' `StaleCache` guard compares a cached figure against a record
count that moves. Measured at the time: **three records landed in twenty seconds.**

Patching each test as it surfaces is the wrong shape. The condition is global, it is knowable
in one line, and the cost of not stating it is an operator debugging an estimator that is fine.
So the suite announces it once, at the top, and again in the summary — and says which failures
it explains.

It does NOT skip anything and does not change any verdict. A real defect must still fail while
collection runs; this only ensures nobody spends an evening on the wrong cause first.
"""
import glob
import importlib
import os
import sys
import time

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, "runs")

#: How long to watch before deciding the tree is quiet. Short enough not to slow the suite,
#: long enough to catch a collector writing a sheet every few seconds.
WATCH_SECONDS = 3

_STATE = {}


def _fingerprint():
    """Total bytes across the corpus. Cheap, and moves whenever anything is appended."""
    total = 0
    for path in glob.glob(os.path.join(RUNS, "**", "*.jsonl"), recursive=True):
        try:
            total += os.path.getsize(path)
        except OSError:
            continue
    return total


def pytest_configure(config):
    if not os.path.isdir(RUNS):
        return
    before = _fingerprint()
    time.sleep(WATCH_SECONDS)
    after = _fingerprint()
    _STATE["writing"] = after != before
    _STATE["delta"] = after - before


def pytest_report_header(config):
    if not _STATE.get("writing"):
        return None
    return (
        "\n*** THE CORPUS IS BEING WRITTEN RIGHT NOW *** (+%d bytes in %ds)\n"
        "Tests that read runs/ are comparing two different corpora across a multi-minute run.\n"
        "A failure saying an estimator, a floor or a cached number disagrees with the data may\n"
        "be saying only that the data moved. Re-run when collection stops before debugging it.\n"
        % (_STATE["delta"], WATCH_SECONDS))


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    if not _STATE.get("writing"):
        return
    failed = terminalreporter.stats.get("failed") or []
    if not failed:
        return
    terminalreporter.write_sep(
        "=", "corpus was being written during this run", yellow=True)
    terminalreporter.write_line(
        "%d test(s) failed while runs/ was growing (+%d bytes). Before treating any of them "
        "as a defect, re-run against a quiet tree." % (len(failed), _STATE["delta"]))


# ---------------------------------------------------------------- the resolver must come back
#
# `studypaths.STUDY_DIR` is computed AT IMPORT from `STUDY_ROOT`, so a test that points the
# environment at a temporary corpus and calls `importlib.reload(studypaths)` leaves the whole
# process resolving to that temporary corpus. `monkeypatch` restores the environment variable
# and cannot restore the module: nothing reloads it back.
#
# The cost is silent and it is exactly the failure this repository keeps paying for. After
# `tests/test_studypaths_two_corpus.py` ran, `item_gradient.gradient()` read zero records from
# a tmpdir, `key_numbers.item_gradient_bounds()` swallowed the empty result and returned `{}`,
# and `gradient_defender_min` arrived at the gate as `None` -- reported as an uncaught failure
# in a key that computes perfectly well. Every run of the full suite failed; every run of that
# test alone passed. Bisecting it cost an hour on 2026-09-22.
#
# `test_validate_runs_layouts.py` already carries a per-test workaround for the same thing --
# "Resolving the corpus through the ambient resolver made this test depend on whatever the
# rest of the suite had last pointed it at" -- which is the shape the header of this file
# objects to. One fixture, applied everywhere, instead of a comment per victim.
#
# It reloads only when the root has actually moved, so the ordinary test pays nothing.
_REAL_STUDY_ROOT = None


def pytest_sessionstart(session):
    global _REAL_STUDY_ROOT
    scripts = os.path.join(HERE, "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    try:
        import studypaths
    except Exception:
        return
    _REAL_STUDY_ROOT = str(studypaths.STUDY_DIR)


@pytest.fixture(autouse=True)
def _studypaths_resolver_is_restored():
    """Put the corpus resolver back if the test moved it. Runs for every test."""
    yield
    if _REAL_STUDY_ROOT is None:
        return
    studypaths = sys.modules.get("studypaths")
    if studypaths is None or str(studypaths.STUDY_DIR) == _REAL_STUDY_ROOT:
        return
    os.environ.pop("STUDY_ROOT", None)
    importlib.reload(studypaths)
    assert str(studypaths.STUDY_DIR) == _REAL_STUDY_ROOT, (
        "the corpus resolver could not be restored: it points at %s, the real tree is %s. "
        "Every later test in this process is reading the wrong corpus."
        % (studypaths.STUDY_DIR, _REAL_STUDY_ROOT))
