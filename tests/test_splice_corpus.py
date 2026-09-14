"""A re-collection nothing reads is a re-collection nobody paid for usefully.

WHY THIS FILE EXISTS
--------------------
`splice_holes.py` reported how many cells a re-collection WOULD recover. Nothing
acted on it. `ci_analysis`, `aggregate`, `analysis` and `drift_timeseries` each
read ONE run directory, so the repaired records sat in `2026-09-05-recollect` and
no published number moved because of them. The cells were collected, scored, and
read by nothing.

`splice_corpus.py` closes that. The properties that matter are not "it produces a
file" but:

  * the base run is never modified, and nothing is silently substituted for it;
  * every repaired record says where it came from;
  * a hole that was not repaired stays a hole and is counted as one;
  * it refuses to write a corpus that repaired nothing, which would be a renamed
    copy of the base with no reason to exist.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import eligibility as E  # noqa: E402
import splice_corpus as SC  # noqa: E402


GOOD = "This is a complete answer that ends properly."
SEVERED = ("The question turns on scope and remedy in ways that " * 12
           + "the office simply did not")


def rec(model="v/m", qid="T01-Q1", cond="A", text=GOOD, score=3, **kw):
    r = {"model": model, "question_id": qid, "condition": cond,
         "response_text": text, "score_classifier": score, "ok": True,
         "scoring_status": "classified"}
    r.update(kw)
    return r


def _patch(monkeypatch, base_rows, source_rows):
    def fake_load(name, sub="scored"):
        return base_rows if name == "BASE" else source_rows
    monkeypatch.setattr(SC, "load", fake_load)


def test_an_eligible_base_record_is_kept_untouched(monkeypatch):
    base = [rec()]
    _patch(monkeypatch, base, [])
    out, info = SC.build("BASE", ("SRC",))
    assert out[0] is base[0], "an eligible base record must pass through unchanged"
    assert info["counts"]["spliced"] == 0


def test_an_ineligible_cell_is_repaired_from_the_source(monkeypatch):
    base = [rec(text=SEVERED)]
    src = [rec(text=GOOD, score=4)]
    _patch(monkeypatch, base, src)
    out, info = SC.build("BASE", ("SRC",))
    assert info["counts"]["spliced"] == 1
    assert out[0]["score_classifier"] == 4
    assert E.is_eligible(out[0])


def test_a_repaired_record_carries_its_provenance(monkeypatch):
    base = [rec(text=SEVERED)]
    _patch(monkeypatch, base, [rec()])
    out, _ = SC.build("BASE", ("SRC",))
    assert out[0]["spliced_from"] == "SRC"
    assert out[0]["spliced_replaces"] == "BASE"
    assert "spliced_base_exclusion" in out[0]


def test_an_INELIGIBLE_source_record_does_not_repair_anything(monkeypatch):
    """Re-collecting a cell that comes back severed again has repaired nothing."""
    base = [rec(text=SEVERED)]
    _patch(monkeypatch, base, [rec(text=SEVERED)])
    out, info = SC.build("BASE", ("SRC",))
    assert info["counts"]["spliced"] == 0
    assert info["counts"]["still_unusable"] == 1
    assert "spliced_from" not in out[0]


def test_an_unrepaired_hole_stays_a_hole(monkeypatch):
    base = [rec(text=SEVERED)]
    _patch(monkeypatch, base, [])
    out, info = SC.build("BASE", ("SRC",))
    assert info["counts"]["still_unusable"] == 1
    assert not E.is_eligible(out[0])
    assert len(out) == 1, "the cell must still be present, not dropped"


def test_the_source_never_adds_cells_the_base_did_not_attempt(monkeypatch):
    """A spliced corpus must have the base's shape, not a larger one."""
    base = [rec(qid="T01-Q1")]
    src = [rec(qid="T01-Q1"), rec(qid="T99-Q9")]
    _patch(monkeypatch, base, src)
    out, _ = SC.build("BASE", ("SRC",))
    assert len(out) == 1
    assert {r["question_id"] for r in out} == {"T01-Q1"}


def test_the_base_list_is_not_mutated(monkeypatch):
    base = [rec(text=SEVERED)]
    snapshot = json.dumps(base[0], sort_keys=True)
    _patch(monkeypatch, base, [rec()])
    SC.build("BASE", ("SRC",))
    assert json.dumps(base[0], sort_keys=True) == snapshot


def test_earlier_sources_win_so_the_order_is_deliberate(monkeypatch):
    base = [rec(text=SEVERED)]
    def fake_load(name, sub="scored"):
        if name == "BASE":
            return base
        return [rec(score=1)] if name == "FIRST" else [rec(score=5)]
    monkeypatch.setattr(SC, "load", fake_load)
    out, _ = SC.build("BASE", ("FIRST", "SECOND"))
    assert out[0]["score_classifier"] == 1
    assert out[0]["spliced_from"] == "FIRST"


def test_it_refuses_to_write_a_corpus_that_repaired_nothing(monkeypatch, capsys):
    base = [rec()]
    _patch(monkeypatch, base, [])
    rc = SC.main(["--write", "--base", "BASE", "--out", "should-not-appear"])
    assert rc == 2
    assert "REFUSING to write" in capsys.readouterr().err


def test_plan_writes_nothing(monkeypatch, capsys):
    base = [rec(text=SEVERED)]
    _patch(monkeypatch, base, [rec()])
    written = []
    monkeypatch.setattr(SC, "write", lambda *a, **k: written.append(a))
    rc = SC.main(["--plan", "--base", "BASE"])
    assert rc == 0 and not written


def test_it_agrees_with_splice_holes_on_the_live_tree():
    """Two tools, one answer. They disagreed once and it cost a day."""
    import splice_holes as S
    records, info = SC.build()
    if info.get("error"):
        return
    base = S.load(S.BASE)
    attempted = {S.key(r) for r in base}
    eligible = {S.key(r) for r in base if E.is_eligible(r)}
    spliced = set()
    for src in S.SPLICE_SOURCES:
        for r in S.load(src):
            if E.is_eligible(r) and S.key(r) in attempted and S.key(r) not in eligible:
                spliced.add(S.key(r))
    assert info["counts"]["spliced"] == len(spliced)
    assert info["counts"]["still_unusable"] == len(attempted - (eligible | spliced))
