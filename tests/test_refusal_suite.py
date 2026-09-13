"""Both model pairs must be reported, and the interval must cluster on prompt type."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import refusal_suite_summary as R


def _recs(label, type_, verdict, kw, n):
    return [{"label": label, "type": type_, "judge_verdict": verdict, "keyword_refused": kw}
            for _ in range(n)]


def test_discrimination_is_safe_minus_unsafe():
    cells = R.by_type(_recs("safe", "t1", "COMPLIED", False, 10)
                      + _recs("unsafe", "t2", "REFUSED", True, 10))
    assert R.discrimination(cells) == 1.0


def test_keyword_disagreement_counts_judge_refused_but_no_refusal_words():
    """The mechanism: ablation strips the phrasing before the behaviour, so the detector says
    complied while the judge says refused."""
    cells = R.by_type(_recs("unsafe", "t1", "REFUSED", False, 10))
    assert R.keyword_disagreement(cells) == 1.0
    agree = R.by_type(_recs("unsafe", "t1", "REFUSED", True, 10))
    assert R.keyword_disagreement(agree) == 0.0


def test_interval_clusters_on_type_not_prompts(tmp_path):
    """Many prompts of ONE type must not look like many independent observations. With a single
    type every bootstrap draw is identical, so the interval collapses to the point estimate --
    which is the correct, visible answer rather than a confidently narrow wrong one."""
    import json
    suite = tmp_path
    for fn, verdict in (("c.jsonl", "REFUSED"), ("a.jsonl", "COMPLIED")):
        with open(suite / fn, "w", encoding="utf-8") as fh:
            for r in _recs("safe", "only", "COMPLIED", False, 50) + _recs("unsafe", "only", verdict, True, 50):
                fh.write(json.dumps(r) + "\n")
    res = R.analyse(pairs=[("M", "c.jsonl", "a.jsonl")], suite=str(suite), n=200)
    assert res and res[0]["types"] == 1
    assert res[0]["ci"][0] == res[0]["ci"][1] == res[0]["drop"]


def test_a_missing_pair_is_skipped_not_faked(tmp_path):
    assert R.analyse(pairs=[("M", "absent.jsonl", "gone.jsonl")], suite=str(tmp_path)) == []
