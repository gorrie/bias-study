"""The collection acceptance gate must fire on the defects that actually happened.

WHY THIS FILE EXISTS
--------------------
`COLLECTION-STANDARD.md` calls itself "a gate, not advice" and nothing executed
it. Its section 4 -- "What is the parameter that will silently ruin it?" -- gives
as an example a build that cannot fit its answer sheet in the budget, which is
precisely the defect that then sat unnoticed in the corpus for four months.

`collection_check.py` is that standard made executable. The decisive test is the
last one: run against the May pipeline wave, it produces three blockers, so the
whole of 2026-09-13 would have been prevented before a single judge call.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import collection_check as C  # noqa: E402


def rec(text="A complete answer.", **kw):
    base = {"ok": True, "model": "v/m", "condition": "B", "question_id": "T01-Q1",
            "response_text": text, "max_tokens": 4000, "temperature": 0.7,
            "tokens_out": 100}
    base.update(kw)
    return base


SEVERED = ("The question turns on scope and remedy in ways that " * 12
           + "the office simply did not")


def test_zero_records_is_not_a_pass():
    out = C.analyse([])
    assert out["n_records"] == 0


def test_a_clean_run_is_accepted():
    rows = [rec(question_id="T%02d" % i) for i in range(10)]
    out = C.analyse(rows)
    assert out["problems"] == [], out["problems"]


def test_truncation_blocks():
    rows = [rec(SEVERED, question_id="T%02d" % i) for i in range(10)]
    out = C.analyse(rows)
    assert out["n_truncated"] == 10
    assert any("end mid-sentence" in p for p in out["problems"])


def test_differential_truncation_blocks_even_at_a_low_overall_rate():
    """The rate is the limitation; the SPREAD is the confound."""
    rows = [rec(SEVERED, model="v/verbose", question_id="T%02d" % i) for i in range(10)]
    rows += [rec(model="v/terse", question_id="T%02d" % i) for i in range(40)]
    out = C.analyse(rows)
    assert any("DIFFERENTIAL" in p for p in out["problems"]), out["problems"]


def test_missing_max_tokens_blocks():
    rows = [rec(question_id="T%02d" % i, max_tokens=None) for i in range(10)]
    out = C.analyse(rows)
    assert any("NO max_tokens RECORDED" in p for p in out["problems"])


def test_empty_responses_block():
    rows = [rec(question_id="T%02d" % i) for i in range(9)] + [rec("", question_id="T99")]
    out = C.analyse(rows)
    assert any("returned no text" in p for p in out["problems"])


def test_systemic_empties_still_block_at_the_gpt5_rate():
    """The defect this check exists for must still stop a run.

    gpt-5 returned 287 empty responses of 310 in the May corpus (92.6%) -- the
    whole budget spent on reasoning tokens -- and 310 of 310 reached the writeup
    as if they were measurements. Making the gate a rate rather than an absolute
    must not weaken THIS case, which is the case it was built for.
    """
    rows = [rec("", question_id="T%03d" % i) for i in range(287)]
    rows += [rec("A complete answer.", question_id="T%03d" % (900 + i)) for i in range(23)]
    out = C.analyse(rows)
    blockers = [p for p in out["problems"] if "returned no text" in p]
    assert blockers, "a 92.6%% empty rate must BLOCK, not warn"
    assert "92.6%" in blockers[0], "the blocker must print the rate it measured"


def test_a_single_stray_empty_warns_and_does_not_block():
    """One empty in 1,600 is a missing cell, not an unmeasurable model.

    It cannot reach a judge (score.py returns skipped-empty-response) and cannot
    reach an aggregate (eligibility excludes it), so blocking the whole run on it
    only teaches the operator to bypass the gate. It must still be SAID.
    """
    rows = [rec("Answer %d." % i, question_id="T%04d" % i) for i in range(1599)]
    rows += [rec("", question_id="T9999")]
    out = C.analyse(rows)
    assert not any("returned no text" in p for p in out["problems"])
    warned = [w for w in out["warnings"] if "returned no text" in w]
    assert warned, "a stray empty must never pass SILENTLY"
    assert "0.06%" in warned[0]


def test_the_empty_threshold_is_not_so_loose_it_admits_a_broken_arm():
    """A tenth of a model's cells missing is not a stray record."""
    rows = [rec("", question_id="T%03d" % i) for i in range(10)]
    rows += [rec("Answer %d." % i, question_id="T%03d" % (900 + i)) for i in range(90)]
    out = C.analyse(rows)
    assert any("returned no text" in p for p in out["problems"])


def test_identical_replicates_block():
    """--samples 5 buys nothing if the server serves one deterministic answer."""
    rows = [rec(question_id="T01", sample_idx=i) for i in range(5)]
    out = C.analyse(rows)
    assert out["n_cells_all_identical"] == 1
    assert any("identical text" in p for p in out["problems"])


def test_genuinely_distinct_replicates_pass():
    rows = [rec("A complete answer number %d." % i, question_id="T01", sample_idx=i)
            for i in range(5)]
    out = C.analyse(rows)
    assert out["mean_distinct_per_cell"] == 5.0
    assert out["problems"] == []


def test_ragged_cells_warn_but_do_not_block():
    rows = [rec("Answer %d." % i, question_id="T01", sample_idx=i) for i in range(5)]
    rows += [rec("Answer %d." % i, question_id="T02", sample_idx=i) for i in range(3)]
    out = C.analyse(rows)
    assert any("ragged cell depth" in w for w in out["warnings"])
    assert out["problems"] == []


def test_crowding_the_cap_warns():
    rows = [rec("Answer %d." % i, question_id="T%02d" % i, tokens_out=3990)
            for i in range(10)]
    out = C.analyse(rows)
    assert any("came within" in w for w in out["warnings"])


def test_the_may_wave_would_have_been_blocked():
    """THE DECISIVE TEST. The collection that started all of this.

    `runs/2026-05-27-g0dm0d3` is the pipeline wave whose Opus layered cell was
    10/10 truncated at an 800-token cap. Run against it, this gate must refuse --
    and it must name all three defects, because each one alone was survivable and
    together they made the arm unmeasurable.
    """
    import glob
    import json
    study = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    paths = sorted(glob.glob(os.path.join(study, "runs", "2026-05-27-g0dm0d3",
                                          "raw", "*.jsonl")))
    if not paths:
        return  # corpus not present in this tree
    rows = []
    for p in paths:
        for line in open(p, encoding="utf-8", errors="replace"):
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    out = C.analyse(rows)
    assert out["problems"], "the May wave must not be accepted"
    joined = " ".join(out["problems"])
    assert "NO max_tokens RECORDED" in joined
    assert "end mid-sentence" in joined
    assert "DIFFERENTIAL" in joined
