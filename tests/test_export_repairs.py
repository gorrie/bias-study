"""The export list is derived from the registries, not typed.

`CORPUS-MAP-2026-09-14.md` carried a banner for a day saying the repaired corpora
were not in the public repository, so every May number a reader recomputed there
came off the damaged corpus. Closing that is a copy operation, and a copy
operation driven by a hand-typed list of twenty-three run names is one that goes
stale the first time a repair is added.

So `export_repairs.py` resolves its list from `studypaths.REPAIRS` and
`splice_corpus.CORPUS_REPAIRS`. A repair registered later is exported without
editing it, which is the only way a list like this stays true.
"""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import export_repairs as E  # noqa: E402
from studypaths import REPAIRS  # noqa: E402


def _plan():
    return {r["run"]: r for r in E.plan()}


def test_every_registered_repair_is_in_the_plan():
    """The decisive property: add a repair, get an export, touch nothing here."""
    plan = _plan()
    missing = [d for d in REPAIRS.values() if d not in plan]
    assert not missing, (
        "derived corpora registered in studypaths.REPAIRS and absent from the "
        "export plan: %r" % missing)


def test_every_spliced_source_travels_with_its_derived_corpus():
    """A derived corpus without its sources cannot be audited.

    The splice is "base where usable, repair where not". A reader holding only
    the result cannot check that rule was applied; they have to be able to see
    both inputs.
    """
    from splice_corpus import CORPUS_REPAIRS
    plan = _plan()
    for base, spec in CORPUS_REPAIRS.items():
        if base not in REPAIRS:
            continue
        for src in spec["sources"]:
            assert src in plan, (
                "%s splices %s and the export plan omits it" % (base, src))


def test_a_run_still_collecting_is_held_not_copied():
    """A half-copied collection in a public tree is worse than an absent one.

    It looks complete, `collection_check` will score it, and nobody re-reads a
    directory that is already there.
    """
    ok, note = E._complete(os.path.join(ROOT, "definitely-not-a-run"))
    assert not ok and "no manifest" in note


def test_a_manifest_gap_is_named_with_evidence_never_fabricated(tmp_path):
    """`run_g0dm0d3.py` wrote no manifest at all until 2026-09-14, so the arm
    every rung-2 number comes from has none.

    The tempting fix is to generate one from the files. A manifest derived from
    the data it exists to check cannot detect a shortfall, which is the only
    thing a manifest is for -- `validate_runs.KNOWN` refuses the same move on
    four May runs. So the gap is declared, with evidence, and the declaration is
    what lets the export proceed.
    """
    assert "2026-09-13-g0dm0d3-replicate" in E.COMPLETE_WITHOUT_MANIFEST
    for run, why in E.COMPLETE_WITHOUT_MANIFEST.items():
        assert len(why) > 80, (
            "%s is declared complete without a manifest and the reason is too "
            "short to be evidence" % run)

    d = tmp_path / "2026-09-13-g0dm0d3-replicate"
    d.mkdir()
    ok, note = E._complete(str(d))
    assert ok and "independent evidence" in note

    other = tmp_path / "2026-01-01-undeclared"
    other.mkdir()
    ok, _ = E._complete(str(other))
    assert not ok, "an undeclared run with no manifest must still be held"


def test_a_derived_corpus_manifest_is_accepted_as_complete(tmp_path):
    d = tmp_path / "x-spliced"
    d.mkdir()
    (d / "manifest.json").write_text(json.dumps({"derived": True}), encoding="utf-8")
    ok, note = E._complete(str(d))
    assert ok and note == "derived corpus"


def test_logs_are_not_exported(tmp_path):
    """Run logs carry API keys often enough that they are never worth shipping."""
    src = tmp_path / "run"
    (src / "raw").mkdir(parents=True)
    (src / "raw" / "m.jsonl").write_text("{}\n", encoding="utf-8")
    (src / "collect.log").write_text("secret-ish\n", encoding="utf-8")
    dest_root = tmp_path / "dest"
    dest_root.mkdir()
    dest = E.copy_run(str(src), str(dest_root))
    assert os.path.isfile(os.path.join(dest, "raw", "m.jsonl"))
    assert not os.path.isfile(os.path.join(dest, "collect.log"))


def test_the_plan_refuses_to_report_success_on_an_empty_registry(monkeypatch):
    monkeypatch.setattr(E, "plan", lambda: [])
    assert E.main([]) == 1


@pytest.mark.skipif(not os.path.isdir(E.DEFAULT_DEST),
                    reason="public mirror not present in this checkout")
def test_the_destination_is_the_may_study_run_root():
    """The mirror has TWO run roots and a May repair in the wrong one is invisible
    to every analysis that reads the other."""
    assert os.path.basename(E.DEFAULT_DEST) == "data"
    assert os.path.isdir(os.path.join(E.DEFAULT_DEST, "2026-05-25-full"))
