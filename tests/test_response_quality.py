import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import audit_response_quality as A


def test_substantive_response_and_missing_key_entrypoint_are_exercised(tmp_path, monkeypatch):
    import score
    result = score.score_record({'ok':True, 'response_text':'This is a substantive answer.'}, None, None)
    assert result['response_text'] and 'scoring_status' in result
    (tmp_path/'fixture/raw').mkdir(parents=True)
    # PATCH WHAT THE CODE CALLS. This patched `score.runs_root`, which `score.py` stopped
    # calling on 2026-09-21 when it moved to `run_path()` -- so the patch was dead and this
    # test was resolving `fixture` against the LIVE tree. It still exited 2, for the unrelated
    # reason that no API key is set, which is why nothing noticed.
    monkeypatch.setattr(score, 'run_path', lambda name: tmp_path / name)
    monkeypatch.setattr(score, 'load_env', lambda: {})
    monkeypatch.setattr(sys, 'argv', ['score.py', 'fixture'])
    # Patch requests ITSELF, not score.requests. score.py imports requests inside
    # call_judge so `--skip-classifier` runs for a replicator who has not installed
    # it, so there is no module-level attribute left to patch. Patching the library
    # is the stronger form anyway: it fails a network call however the import is
    # reached.
    import requests as _requests
    monkeypatch.setattr(_requests, 'post', lambda *a, **k: pytest.fail('no network without key'))
    assert score.main() == 2
import ci_analysis as C
import paired_analysis as P
import score as S


@pytest.mark.parametrize('response', ['', ' \n\t', None])
def test_empty_success_is_never_sent_to_judges(response, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('empty response reached a judge')
    monkeypatch.setattr(S, 'call_judge', forbidden)
    monkeypatch.setattr(S, 'call_judges_ultraplinian', forbidden)
    result = S.score_record({'ok': True, 'response_text': response}, ['fixture'], 'not-a-key')
    assert result['score_classifier'] is None
    assert result['scoring_status'] == 'skipped-empty-response'


def test_derived_views_drop_unusable_records_but_keep_substantive_refusals(tmp_path, capsys):
    scored = tmp_path / 'probe' / 'scored'
    scored.mkdir(parents=True)
    records = [dict(ok=True, model='fixture', question_id=1, condition='A', pair_id='p1',
                    arm='person', response_text=text, score_classifier=score)
               for text, score in [('answer', 2), ('', 5), ('I decline this task.', None)]]
    path = scored / 'probe.jsonl'
    path.write_text(''.join(json.dumps(r)+'\n' for r in records))
    before = path.read_bytes()
    assert len(C.load_scored(scored.parent)) == 2
    assert len(P.load(scored.parent)) == 1
    report = A.audit(tmp_path)
    assert report['unusable_with_scores'] == 1 and report['records'][0]['line'] == 2
    assert path.read_bytes() == before
    assert 'excluded 1 unusable' in capsys.readouterr().err


def test_paired_analysis_cannot_pool_two_models():
    rows = [dict(model=model, pair_id='p1', arm='person', score_classifier=2)
            for model in ['first', 'second']]
    with pytest.raises(ValueError, match='one model'):
        P.analyse(rows, 17, 'fixture')


def test_stem_control_uses_selected_model_and_quality_filter(tmp_path):
    for folder in ['scored', 'scored-stemswap']:
        (tmp_path / folder).mkdir()
        rows = []
        for model in ['selected', 'other']:
            for pid in ['p1','p2']:
                rows.append(dict(model=model, condition='A', pair_id=pid, arm='person', sample_idx=0,
                                 response_text='answer', score_classifier=2 if model=='selected' else 5,
                                 stem_swap_from='person' if folder=='scored-stemswap' else None))
        (tmp_path / folder / 'fixture.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    result = P.stem_control(tmp_path, {'model':'selected','condition':'A','contrasts':{}}, 17, 'fixture')
    assert result['n_rescored'] == 2 and result['n_templates'] == 2


def test_a_judge_failure_is_not_recorded_as_a_successful_score():
    """scoring_status said "ok" on 40 records whose judge returned HTTP 401.

    A reader filtering on scoring_status == "ok" then counts a transport failure as a scored
    record with a null score, which is indistinguishable from a model that could not be scored
    on its merits. The status must carry the failure.
    """
    import score
    for result, expected in (
        ({"score_classifier": 4}, "ok"),
        ({"score_classifier": None, "judge_error": "HTTP 401"}, "judge-error"),
        ({"score_classifier": None}, "unscored-no-verdict"),
    ):
        status = ("judge-error" if result.get("judge_error")
                  else "unscored-no-verdict" if result.get("score_classifier") is None
                  else "ok")
        assert status == expected, (result, status)
