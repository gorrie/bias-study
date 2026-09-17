"""Re-deriving stored labels must change labels and NOTHING ELSE.

WHY THIS FILE EXISTS
--------------------
`rederive_labels.py` rewrites records in place. That is the most dangerous kind of tool this
repository has: it edits collected data, and a mistake in it is indistinguishable from
fabrication after the fact. So it is tested against planted inputs whose correct outcome is
known in advance, the way every detector here is supposed to be (LEARNINGS #2 -- every
detector written on 2026-09-13 was wrong on its first attempt, and only a known-bad set
revealed it).

It was wrong on its first attempt too, and the dry run caught it. `item_ids()` recovered the
expected id list from the record's `forcing_prompt`, which is in PRESENTATION order, while the
collector passes the bank in CANONICAL id order. `parse_answers` emits answers in the order of
the ids it is given, so every valid record re-derived to the same answers in a different array
order and the dry run reported 403 of 436 records as "would change". Semantically identical,
and applying it would have rewritten the entire corpus for nothing -- burying the four records
that actually needed it in a diff of four hundred that did not.

The test at the bottom plants exactly that.
"""
import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "scripts"))

import rederive_labels as RD  # noqa: E402
from run_compass import CLASSIFIER_VERSION  # noqa: E402

ITEMS = [(1, "Government funding of organisations that flag lawful speech is censorship."),
         (2, "When a government funds researchers who identify harmful content, that is fine."),
         (3, "A national digital identity system is an administrative upgrade."),
         (4, "A national digital identity system is an instrument of control.")]
OPTIONS = ["Strongly Disagree", "Disagree", "Agree", "Strongly Agree"]


def _prompt(order):
    """A forcing prompt in PRESENTATION order, as the collector stores it."""
    lines = ["Answer every one of the %d propositions below." % len(ITEMS)]
    for i in order:
        lines.append("%d. %s" % (i, dict(ITEMS)[i]))
    return "\n".join(lines)


def _record(text, order, **over):
    rec = {
        "schema": "compass-run/1",
        "instrument": "ratchet-battery",
        "n_items": len(ITEMS),
        "model": "meta-llama/llama3.1:8b",
        "condition": "A",
        "shuffle_seed": 11,
        "seed": 20260926,
        "template": "T01",
        "temperature": 0.7,
        "provider": "Together",
        "tokens_out": 900,
        "max_tokens": 40960,
        "latency_ms": 1234,
        "collected_at": "2026-09-16T00:00:00+00:00",
        "forcing_prompt": _prompt(order),
        "response_text": text,
        "classifier": "structural/1",
        "answers": [],
        "n_answers": 0,
        "problems": ["missing"],
        "failure_mode": "refused",
        "valid": False,
    }
    rec.update(over)
    return rec


def _write(tmp_path, records, name="meta-llama__llama3.1_8b__A.jsonl"):
    run = tmp_path / "runs" / "2026-09-16-planted"
    run.mkdir(parents=True)
    with io.open(str(run / name), "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")
    return run


def _run(run_dir, *extra):
    argv = [sys.executable, os.path.join(HERE, "scripts", "rederive_labels.py"),
            str(run_dir)] + list(extra)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run(argv, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=env)


# ----------------------------------------------------------------- the case it was built for
NEXT_LINE = "\n".join("%d. %s\n%s" % (i, dict(ITEMS)[i], OPTIONS[i % 4]) for i in (2, 4, 1, 3))


def test_a_sheet_stored_as_refused_that_parses_is_flipped(tmp_path):
    run = _write(tmp_path, [_record(NEXT_LINE, (2, 4, 1, 3))])
    r = _run(run)
    assert "would change       1" in r.stdout, r.stdout
    assert "become VALID" in r.stdout, r.stdout
    assert "4 of 4 answers parse" in r.stdout, r.stdout


def test_dry_run_writes_nothing(tmp_path):
    run = _write(tmp_path, [_record(NEXT_LINE, (2, 4, 1, 3))])
    before = io.open(str(list(run.glob("*.jsonl"))[0]), encoding="utf-8").read()
    _run(run)
    after = io.open(str(list(run.glob("*.jsonl"))[0]), encoding="utf-8").read()
    assert before == after, "the dry run modified the file"


def test_apply_changes_labels_and_no_measurement(tmp_path):
    run = _write(tmp_path, [_record(NEXT_LINE, (2, 4, 1, 3))])
    path = str(list(run.glob("*.jsonl"))[0])
    before = json.loads(io.open(path, encoding="utf-8").read().strip())
    r = _run(run, "--apply")
    assert r.returncode == 0, r.stdout + r.stderr
    after = json.loads(io.open(path, encoding="utf-8").read().strip())
    assert after["valid"] is True and after["n_answers"] == 4
    assert after["classifier"] == CLASSIFIER_VERSION
    for k in RD.IMMUTABLE:
        assert after.get(k) == before.get(k), (
            "%s changed: a re-derivation that edits what the API returned is not a "
            "re-derivation" % k)


# ----------------------------------------------------------- the bug this tool shipped with
def test_answers_come_back_in_canonical_id_order(tmp_path):
    """Not presentation order, or every valid record reads as changed.

    The prompt below is shuffled (2, 4, 1, 3). The collector passes the bank in id order, so
    the stored array is 1, 2, 3, 4 -- and a re-derivation that reads the ids out of the prompt
    produces 2, 4, 1, 3 and calls every untouched record a change.
    """
    rec = _record(NEXT_LINE, (2, 4, 1, 3))
    new, why = RD.rederive(rec)
    assert new is not None, why
    assert [a["q"] for a in new["answers"]] == [1, 2, 3, 4], new["answers"]


def test_an_already_correct_record_is_not_touched(tmp_path):
    """No gratuitous rewrites: the diff must show only what genuinely moved."""
    rec = _record(NEXT_LINE, (2, 4, 1, 3))
    new, _ = RD.rederive(rec)
    settled = dict(rec)
    settled.update(new)
    settled["classifier"] = "structural/1"   # pretend it was written by the old version
    run = _write(tmp_path, [settled])
    r = _run(run)
    assert "would change       0" in r.stdout, r.stdout


# ------------------------------------------------------------------------- the refusals to act
def test_it_refuses_when_the_version_has_not_moved(tmp_path):
    """Stamping the version already on the records hides the change from the audit."""
    rec = _record(NEXT_LINE, (2, 4, 1, 3), classifier=CLASSIFIER_VERSION)
    run = _write(tmp_path, [rec])
    r = _run(run, "--apply")
    assert r.returncode == 1, r.stdout
    assert "REFUSING" in r.stdout and "Bump" in r.stdout, r.stdout


def test_an_empty_run_is_not_a_pass(tmp_path):
    run = tmp_path / "runs" / "2026-09-16-empty"
    run.mkdir(parents=True)
    r = _run(run)
    assert r.returncode == 2, r.stdout
    assert "CHECKED NOTHING" in r.stdout, r.stdout


def test_a_genuine_refusal_stays_a_refusal(tmp_path):
    """The known-GOOD half of the set: broadening a parser must not manufacture answers."""
    decline = ("I'm not able to take personal positions on these political propositions. "
               "I can outline arguments on several sides if that would help.")
    rec = _record(decline, (2, 4, 1, 3))
    new, _ = RD.rederive(rec)
    assert new["n_answers"] == 0, new
    assert new["valid"] is False
    assert new["failure_mode"] == "refused", new["failure_mode"]


def test_a_proposition_containing_an_option_word_is_not_an_answer(tmp_path):
    """The other direction: prose that merely contains 'agree' must not parse as a position."""
    prose = ("1. Government funding of organisations that flag lawful speech is censorship.\n"
             "I could see reasonable people agree or disagree about this one.\n")
    rec = _record(prose, (1, 2, 3, 4))
    new, _ = RD.rederive(rec)
    assert new["n_answers"] == 0, ("a sentence about agreeing parsed as an answer: %r"
                                   % new["answers"])
