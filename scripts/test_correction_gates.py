"""Regression tests for September 8 inference and release-gate defects; no network."""
import math
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import power as P
import release_check as R
import check_no_fork as C


def test_observation_uses_reference_not_design_shift():
    vals = list(range(11))
    threshold = P.pctile(vals, .95)
    assert threshold == 10 and P.mde(vals, threshold) == 9
    assert P.classify_observation(9, threshold) == 'AT OR BELOW REFERENCE'
    assert P.classify_observation(10, threshold) == 'AT OR BELOW REFERENCE'
    assert P.classify_observation(11, threshold) == 'ABOVE REFERENCE'


@pytest.mark.parametrize('observed', [0, 9, 11])
def test_measurement_caveat_always_takes_precedence(observed):
    assert P.classify_observation(observed, 10, 'single draw') == 'MEASUREMENT LIMITED'


def test_shift_cannot_exceed_instrument_support():
    """The bound is the LIVE instrument item count, not a literal.

    Written as 62 -- the external questionnaire length. The study measures on a 32-item
    battery, so a test pinned to 62 asserts the support of an instrument no longer in the
    tree and passes only while the wrong number is hardcoded in power.py.
    """
    bound = P.BOUND
    assert bound == 32, bound
    assert math.isnan(P.mde([bound], bound))
    assert math.isnan(P.mde([], 10))
    with pytest.raises(ValueError):
        P.mde([bound + 1], 10)
    with pytest.raises(ValueError):
        P.mde([1], 2, power=0)


def test_collect_preserves_both_classes_and_restores_loader(monkeypatch):
    def original(*args, **kwargs):
        return None
    monkeypatch.setattr(P.F, 'summarise', original)
    def split():
        P.F.summarise('local', [(10, 20)], clusters=['l'])
        P.F.summarise('hosted', [(1, 2)], clusters=['h'])
    monkeypatch.setattr(P.F, 'ALL_FLOORS', [split])
    assert P.collect() == {'local': {'side': [10], 'endpoint': [20]},
                           'hosted': {'side': [1], 'endpoint': [2]}}
    assert P.F.summarise is original
    def broken():
        raise RuntimeError('bad data')
    monkeypatch.setattr(P.F, 'ALL_FLOORS', [broken])
    with pytest.raises(RuntimeError):
        P.collect()
    assert P.F.summarise is original


def test_manipulations_are_not_sensitivity_references(monkeypatch, capsys):
    names = ['prompt condition A->D', 'prompt condition A->D, one sitting',
             'prompt condition A->D, one sitting, local open-weight',
             'refusal-direction ablation', 'refusal-direction ablation, one sitting']
    monkeypatch.setattr(P, 'collect', lambda: {n: {'side':[1], 'endpoint':[2]} for n in names})
    assert all(P.reference_kind(n) == 'intervention' for n in names)
    assert P.main([]) == 1  # missing historical references cannot silently disappear
    assert 'REFERENCE UNAVAILABLE' in capsys.readouterr().out


def test_release_failures_and_launch_errors_are_nonzero(capsys):
    checks = [('ok', '.', ['ok']), ('bad', '.', ['bad']), ('timeout', '.', ['timeout'])]
    attempted = []
    def runner(cwd, command, **kw):
        attempted.append(command)
        if command == 'timeout':
            raise subprocess.TimeoutExpired(command, kw['timeout'])
        return (7, 'child failure') if command == 'bad' else (0, '')
    assert R.main([], checks=checks, runner=runner) == 1
    assert attempted == ['ok', 'bad', 'timeout']
    out = capsys.readouterr().out
    assert '2 mechanical check(s) FAIL' in out and 'child failure' in out


def test_release_success_is_mechanical_only_and_empty_suite_fails(capsys):
    assert R.main([], checks=[('ok', '.', [])], runner=lambda *a, **k: (0, '')) == 0
    assert 'Human review remains required' in capsys.readouterr().out
    assert R.main([], checks=[]) == 1


def test_release_import_has_no_execution_side_effects():
    result = subprocess.run([sys.executable, '-c', 'import release_check'],
                            cwd=Path(R.__file__).parent, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0 and result.stdout == '' and result.stderr == ''


def test_release_real_child_failure_propagates_to_shell(tmp_path):
    code = ('import sys,release_check as r; '
            'sys.exit(r.main([], checks=[("child", ".", ["-c", "raise SystemExit(7)"])]))')
    result = subprocess.run([sys.executable, '-c', code], cwd=Path(R.__file__).parent,
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 1 and 'rc=7' in result.stdout


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], check=True,
                          capture_output=True, text=True).stdout


def setup_mirrors(tmp_path, monkeypatch):
    private = tmp_path / 'private'
    public = tmp_path / 'public'
    study = private / 'research' / 'bias-study'
    for repo, scripts in [(private, study / 'scripts'), (public, public / 'scripts')]:
        scripts.mkdir(parents=True)
        git(repo, 'init', '-q')
        (scripts / 'shared.py').write_text('VALUE = 1\n')
        git(repo, 'add', '.')
        git(repo, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
            '-c', 'core.autocrlf=false', 'commit', '-qm', 'fixture')
    monkeypatch.setattr(C, 'HERE', str(study / 'scripts'))
    monkeypatch.setattr(C, 'STUDY', str(study))
    monkeypatch.setattr(C, 'PUBLIC', str(public))
    monkeypatch.setattr(C, 'PUBLIC_SCRIPTS', str(public / 'scripts'))
    return study, public


def test_gate_reads_private_head_from_nested_repo_and_rejects_dirty(tmp_path, monkeypatch):
    study, public = setup_mirrors(tmp_path, monkeypatch)
    assert C.read_committed(str(study), 'scripts/shared.py') == 'VALUE = 1\n'
    assert C.main([]) == 0
    (study / 'scripts/shared.py').write_text('VALUE = 2\n')
    (public / 'scripts/shared.py').write_text('VALUE = 2\n')
    assert C.read_committed(str(study), 'scripts/shared.py') == 'VALUE = 1\n'
    assert C.main([]) == 1  # matching working edits cannot hide old committed content


def test_gate_missing_mirror_is_not_applicable_not_a_pass(tmp_path, monkeypatch):
    """No mirror to compare against is NOT APPLICABLE (2), never a pass (0).

    This asserted 1. On 2026-09-15 check_no_fork adopted the convention these gates now
    share -- 0 pass, 1 defect, 2 not applicable -- because the script shipped INTO the
    public mirror, where there is no second tree to diff and "1" claimed a defect that did
    not exist. The test kept asserting the old code and went red without ever being the
    thing that was wrong.

    What matters, and what this still pins, is that it is NOT ZERO: a comparison that
    compared nothing must never report the trees agree.
    """
    monkeypatch.setattr(C, 'PUBLIC_SCRIPTS', str(tmp_path / 'missing'))
    rc = C.main([])
    assert rc == 2, rc
    assert rc != 0, "a fork check with no mirror to check against is not a pass"


def test_gate_missing_shim_target_is_failure(tmp_path, monkeypatch):
    study, public = setup_mirrors(tmp_path, monkeypatch)
    (study / 'scripts/absent.py').write_text('from _shim import forward\n')
    assert C.main([]) == 1


def test_paper_generator_rejects_partial_stdout_on_exit_one(tmp_path, monkeypatch):
    import gen_paper as G
    script = tmp_path / 'broken.py'
    script.write_text('print("partial report")\nraise RuntimeError("broken analysis")\n')
    monkeypatch.setattr(G, 'HERE', str(tmp_path))
    with pytest.raises(SystemExit, match='failed \\(1\\)'):
        G.run('broken.py', [])
