"""Two-corpus subprocess tests; no network or user configuration files."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'


def invoke(root, script=None, *args, code=None):
    env = dict(os.environ, STUDY_ROOT=str(root), BIAS_STUDY_BOOTSTRAP_N='100')
    command = [sys.executable, '-c', code] if code else [sys.executable, str(SCRIPTS / script), *args]
    return subprocess.run(command, cwd=SCRIPTS, env=env, capture_output=True,
                          text=True, timeout=30)


def corpus(root, folder, label):
    scored = root / folder / 'probe' / 'scored'
    scored.mkdir(parents=True)
    records = [dict(model=label, question_id=q, condition=cond, score_classifier=score,
                    response_text='fixture response', pair_id=f'p{q}', arm=arm)
               for q in range(2) for cond, arm, score in
               [('A', 'institution', 1), ('B', 'person', 4), ('C', 'algorithm', 2)]]
    (scored / 'probe.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in records))
    (scored.parent / 'manifest.json').write_text(json.dumps({'analysis_seed': 17}))
    return scored.parent


@pytest.mark.parametrize('entry', ['ci_analysis.py', 'robustness_checks.py',
                                   'paired_analysis.py', 'validate_runs.py'])
def test_entry_points_select_requested_private_corpus(tmp_path, entry):
    roots = [tmp_path / 'first', tmp_path / 'second']
    outputs = []
    for index, root in enumerate(roots):
        run = corpus(root, 'runs', f'corpus-{index}')
        (root / 'data').mkdir()  # predecessor data/ holds config, not observations
        args = ['probe']
        if entry == 'validate_runs.py':
            # A visibly different inventory for the second corpus.
            (run / 'raw').mkdir()
            (run / 'raw' / 'probe.jsonl').write_text('{}\n' * (index + 1))
            args.append('--json')
        if entry == 'paired_analysis.py':
            path = run / 'scored/probe.jsonl'
            # Paired arms must share a condition; this fixture used to accidentally
            # assert successful cross-condition pooling. The routing test now uses
            # valid pairs, with rejection tested in test_inference_contracts.py.
            records = [json.loads(line) for line in path.read_text().splitlines()]
            for record in records:
                record['condition'] = 'A'
                if record['arm'] == 'person':
                    record['score_classifier'] = 4-index
            path.write_text(''.join(json.dumps(r)+'\n' for r in records))
            args.append('--json')
        result = invoke(root, entry, *args)
        assert result.returncode == 0, result.stderr + result.stdout
        outputs.append(result.stdout)
        if entry in ('ci_analysis.py', 'robustness_checks.py'):
            assert f'corpus-{index}' in result.stdout
    assert outputs[0] != outputs[1]


def test_public_layout_and_ambiguous_layout(tmp_path):
    corpus(tmp_path, 'data', 'public')
    code = 'import studypaths as s; print(s.resolve_run("probe")); print(s.analysis_seed("probe"))'
    result = invoke(tmp_path, code=code)
    assert result.returncode == 0 and str(tmp_path / 'data' / 'probe') in result.stdout
    assert result.stdout.rstrip().endswith('17')
    corpus(tmp_path, 'runs', 'private')
    result = invoke(tmp_path, code=code)
    assert result.returncode != 0 and 'ambiguous' in result.stderr


def test_explicit_layout_disambiguates_held_v2_without_fallback(tmp_path, monkeypatch):
    corpus(tmp_path, 'data', 'published')
    corpus(tmp_path, 'runs', 'working')
    for layout in ('data', 'runs'):
        monkeypatch.setenv('STUDY_RUN_LAYOUT', layout)
        result = invoke(tmp_path, code='import studypaths; print(studypaths.resolve_run("probe"))')
        assert result.returncode == 0 and str(tmp_path/layout/'probe') in result.stdout
    monkeypatch.setenv('STUDY_RUN_LAYOUT', '../other')
    result = invoke(tmp_path, code='import studypaths; studypaths.runs_root()')
    assert result.returncode != 0 and 'STUDY_RUN_LAYOUT' in result.stderr


@pytest.mark.parametrize('selection', ['', 'nonexistent'])
def test_invalid_override_never_falls_back_to_public(tmp_path, selection):
    root = '' if not selection else tmp_path / selection
    result = invoke(root, code='import studypaths; print(studypaths.STUDY_DIR)')
    assert result.returncode != 0 and 'STUDY_ROOT' in result.stderr


def test_missing_private_run_never_falls_back_to_published_data(tmp_path):
    (tmp_path / 'runs').mkdir()
    result = invoke(tmp_path, 'ci_analysis.py', '2026-05-25-full')
    assert result.returncode != 0 and 'no run directory' in result.stderr


def test_external_codes_are_configuration_not_a_second_corpus(tmp_path):
    corpus(tmp_path, 'runs', 'private')
    external = tmp_path / 'data/external'
    external.mkdir(parents=True)
    (external/'codes.jsonl').write_text('{}\n')
    result = invoke(tmp_path, code='import studypaths; print(studypaths.runs_root())')
    assert result.returncode == 0 and result.stdout.strip() == str(tmp_path/'runs')


def test_compass_entry_point_uses_each_requested_instrument(tmp_path):
    """STUDY_ROOT is honoured per tree -- the default instrument is just the vehicle.

    The fixture wrote `compass-propositions.json` because that used to be the default.
    On 2026-09-16 the default became the authored I3 bank: the compass was retired on
    2026-09-15 and a retired instrument still reachable by omission is not retired.
    The property under test is unchanged -- two roots, two files, no caching between
    them -- so the fixture follows the default rather than the default being held back
    to suit the fixture.
    """
    for index in range(2):
        root = tmp_path/str(index)
        (root/'data').mkdir(parents=True)
        (root/'data/ratchet-propositions-i3.json').write_text(json.dumps(
            {'items':[{'id':1, 'text':f'fixture instrument {index}'}]}))
        result = invoke(root, 'run_compass.py', '--model', 'fixture', '--channel', 'ollama', '--dry-run')
        assert result.returncode == 0, result.stderr
        assert f'fixture instrument {index}' in result.stdout
        assert f'fixture instrument {1-index}' not in result.stdout
