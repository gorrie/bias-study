"""A run that GREW needs per-record scoring, not per-file.

WHY THIS FILE EXISTS
--------------------
`score.py` offered two modes and neither fits re-collection:

    default     scored/<name>.jsonl exists -> SKIP the whole file, so records
                appended by a re-collection are never judged at all
    --rescore   re-judge every record in the file, paying four judge calls each
                to reproduce 156 judgements that were already correct

Re-collection appends new records beside judged ones in the same file. On the
2026-09-05 run that is 199 records of which 156 already carry a score, so the
wrong mode costs about 800 redundant judge calls or silently leaves the repair
unscored.

THE DANGEROUS HALF is reuse. A re-collected cell carries NEW text under the same
model/question/condition key. Reusing its old score would attach a judgement of
the severed 800-token response to the repaired 4,000-token one -- silently, and
in exactly the direction that makes the repair look like it changed nothing. So
reuse is keyed on the RESPONSE TEXT, which is what the judge actually read.
"""
import inspect
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import score as S  # noqa: E402

SRC = inspect.getsource(S.main) if hasattr(S, "main") else inspect.getsource(S)


def _body():
    return "\n".join(ln for ln in SRC.split("\n") if not ln.strip().startswith("#"))


def test_the_flag_exists():
    assert "--fill-missing" in inspect.getsource(S), "no per-record scoring mode"


def test_reuse_is_keyed_on_response_text_not_on_the_cell():
    """The whole safety property. Keying on the cell would reuse a stale judgement."""
    body = _body()
    assert 'prior[(p.get("response_text") or "")]' in body, (
        "prior scores are not keyed on response text; a re-collected cell would "
        "inherit the judgement of the response it replaced")
    assert 'prior.get(rec.get("response_text") or "")' in body


def test_only_scored_priors_are_reused():
    body = _body()
    assert 'p.get("score_classifier") is not None' in body, (
        "an unscored prior would be reused as though it were a judgement")


def test_default_still_skips_and_rescore_still_redoes():
    """The existing modes must keep working; this adds a third."""
    body = _body()
    assert "args.rescore or args.fill_missing" in body
    assert "SKIP (scored exists" in body


def test_reuse_is_reported_separately_from_judging():
    body = _body()
    assert "total_reused" in body
    assert "sent to judges" in body, (
        "a resumed run that reports only a total looks exactly like a full one")


# ------------------------------------------------------- behaviour

def _run(tmp_path, monkeypatch, raw, scored_existing, argv):
    run = tmp_path / "arun"
    (run / "raw").mkdir(parents=True)
    (run / "scored").mkdir(parents=True)
    with (run / "raw" / "m.jsonl").open("w", encoding="utf-8") as fh:
        for r in raw:
            fh.write(json.dumps(r) + "\n")
    if scored_existing is not None:
        with (run / "scored" / "m.jsonl").open("w", encoding="utf-8") as fh:
            for r in scored_existing:
                fh.write(json.dumps(r) + "\n")

    calls = []

    def fake_score_record(rec, judges, api_key, judge_method=None):
        calls.append(rec.get("response_text"))
        out = dict(rec)
        out["score_classifier"] = 5
        out["scoring_status"] = "classified"
        return out

    monkeypatch.setattr(S, "score_record", fake_score_record)
    monkeypatch.setattr(S, "runs_root", lambda: tmp_path)
    monkeypatch.setattr(S, "load_env", lambda: {"OPENROUTER_API_KEY": "k"})
    monkeypatch.setattr(sys, "argv", ["score.py", "arun"] + argv)
    S.main()
    with (run / "scored" / "m.jsonl").open(encoding="utf-8") as fh:
        out = [json.loads(line) for line in fh if line.strip()]
    return calls, out


def test_an_already_judged_record_is_not_sent_again(tmp_path, monkeypatch):
    raw = [{"ok": True, "response_text": "Same text.", "model": "m",
            "question_id": "T01", "condition": "A"}]
    prior = [dict(raw[0], score_classifier=3, scoring_status="classified")]
    calls, out = _run(tmp_path, monkeypatch, raw, prior, ["--fill-missing"])
    assert calls == [], "a byte-identical response was judged again"
    assert out[0]["score_classifier"] == 3


def test_a_recollected_record_with_new_text_IS_judged(tmp_path, monkeypatch):
    """The defect this guards: new text must never inherit the old judgement."""
    raw = [{"ok": True, "response_text": "The repaired, complete answer.", "model": "m",
            "question_id": "T01", "condition": "A"}]
    prior = [{"ok": True, "response_text": "The severed answer that was cut off mid-",
              "model": "m", "question_id": "T01", "condition": "A",
              "score_classifier": 3, "scoring_status": "classified"}]
    calls, out = _run(tmp_path, monkeypatch, raw, prior, ["--fill-missing"])
    assert calls == ["The repaired, complete answer."], "the repaired text was not judged"
    assert out[0]["score_classifier"] == 5


def test_an_unscored_record_is_judged(tmp_path, monkeypatch):
    raw = [{"ok": True, "response_text": "Fresh.", "model": "m",
            "question_id": "T01", "condition": "A"}]
    prior = [dict(raw[0], score_classifier=None, scoring_status="pending-rescore")]
    calls, _out = _run(tmp_path, monkeypatch, raw, prior, ["--fill-missing"])
    assert calls == ["Fresh."]


def test_a_mixed_file_judges_only_what_is_missing(tmp_path, monkeypatch):
    raw = [
        {"ok": True, "response_text": "Old A.", "model": "m", "question_id": "T01",
         "condition": "A"},
        {"ok": True, "response_text": "New B.", "model": "m", "question_id": "T02",
         "condition": "A"},
    ]
    prior = [dict(raw[0], score_classifier=2, scoring_status="classified")]
    calls, out = _run(tmp_path, monkeypatch, raw, prior, ["--fill-missing"])
    assert calls == ["New B."]
    assert [r["score_classifier"] for r in out] == [2, 5]
