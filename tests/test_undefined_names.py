"""A name used and never bound is a NameError waiting for the line to run.

`recollect_at_cap.py` used `LEGACY_SEED` in its manifest block and imported only
`run_roots`. The line runs LAST -- after every API call has been made, paid for,
and written -- so the run produced a complete set of records, crashed, and left
no manifest. The expensive part succeeded and the cheap part died.

It hid for a second reason worth keeping in mind: `repair_recollect_provenance.py
--manifests` had been backfilling the missing manifests, so the symptom was being
cleaned up faster than the cause could be seen.

A second instance turned up in the first scan -- `pytest.skip()` in a file that
never imported pytest, so a checkout without a local hf.co/ build got NameError
where it should have got a skip.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import check_undefined_names as C  # noqa: E402


def test_the_repo_has_no_unbound_names():
    n_files, findings = C.scan()
    assert n_files > 50, "the scan must actually read the repo, not zero files"
    assert not findings, "\n".join(
        "%s:%d  %s" % (f["file"], f["line"], f["name"]) for f in findings)


def test_it_catches_the_bug_that_prompted_it():
    """The exact shape: a module-level constant used and never imported."""
    src = ("from studypaths import run_roots\n"
           "def main():\n"
           "    return {'analysis_seed': LEGACY_SEED, 'roots': run_roots()}\n")
    assert C.check_source(src) == [(3, "LEGACY_SEED")]


def test_a_gate_that_read_nothing_does_not_pass(monkeypatch, tmp_path):
    monkeypatch.setattr(C, "ROOT", str(tmp_path))
    assert C.main([]) == 1


def test_lambda_parameters_are_not_reported():
    """24 of the first scan's 29 findings were `key=lambda x:` parameters.

    A checker whose output is mostly noise is one nobody reads, which is the
    failure it exists to prevent.
    """
    assert C.check_source("S=[1]\nY=sorted(S, key=lambda z: -z)\n") == []


def test_ordinary_binding_forms_are_not_reported():
    """Comprehensions, star-args, with-targets, except-targets, match captures.

    Each of these binds a name by a mechanism that is easy to forget, and every
    one of them forgotten is a false positive.
    """
    src = (
        "import os, contextlib\n"
        "K = 1\n"
        "def f(a, b=2, *rest, kw=3, **kwargs):\n"
        "    vals = [x * a for x in rest if x]\n"
        "    pairs = {k: v for k, v in kwargs.items()}\n"
        "    with contextlib.suppress(ValueError) as ctx:\n"
        "        pass\n"
        "    try:\n"
        "        pass\n"
        "    except OSError as exc:\n"
        "        return exc\n"
        "    match vals:\n"
        "        case [first, *others]:\n"
        "            return first, others\n"
        "    return vals, pairs, ctx, K, b, kw, os.sep\n"
    )
    assert C.check_source(src) == []


def test_a_star_import_makes_a_file_uncheckable_rather_than_noisy():
    """Nothing can enumerate what `from x import *` binds, so it reports nothing.

    Saying so beats guessing: a file that cannot be checked must not be reported
    as clean-by-luck or flagged wholesale.
    """
    assert C.check_source("from os.path import *\nprint(join('a','b'))\n") == []


def test_syntax_errors_are_reported_rather_than_swallowed():
    out = C.check_source("def f(:\n")
    assert out and "SyntaxError" in out[0][1]
