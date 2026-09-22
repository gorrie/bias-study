"""§3b's intensity result, and the confound that has to travel with it.

The finding: 35 of 56 models use the strongest answer more often on contested normative
propositions than on documented matters of record, 14 the other way, p = 0.0038. The panel is
most committed where it has least to go on.

The confound: in this bank `claim_type` is perfectly aligned with the `ratchet` jurisdiction
tag — all ten generic items are normative, all six jurisdiction-tagged ones are documented — so
"has a public record" and "names a specific country" are one variable with two labels. That is
not a confound more collection shrinks. It is one the instrument forecloses.

These tests exist because the caveat is the part that goes missing. A figure survives edits;
the sentence beside it does not.
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(STUDY, "scripts"))

import intensity_by_claim as I        # noqa: E402


def test_nothing_crosses_the_diagonal_in_the_live_bank():
    """The load-bearing half: no item is documented-and-generic or normative-and-jurisdictional.

    That is what makes the two labels inseparable, and it is what §3b's caveat rests on. If
    this starts failing, someone authored items that break the alignment — which is good news
    and means the caveat can be rewritten.

    It used to assert `aligned is True` as well, and that was wrong in a way worth keeping a
    note about: `aligned` also required each side to be EXHAUSTED by its expected claim type,
    and the bank's one `contested` generic pair is neither documented nor normative, so it
    fell through both crossing tests. `aligned` read True over a set where 9 of 10 generic
    items are normative, and the generator printed "All 10 generic items are normative" into
    the paper. The test asserted the defect.
    """
    aligned, detail = I.check_confound()
    assert not detail["documented_and_generic"], (
        "%d documented-and-generic item(s) now exist: %s. §3b's caveat is too strong."
        % (len(detail["documented_and_generic"]), detail["documented_and_generic"]))
    assert not detail["normative_and_jurisdictional"], (
        "%d normative-and-jurisdictional item(s) now exist: %s. §3b's caveat is too strong."
        % (len(detail["normative_and_jurisdictional"]),
           detail["normative_and_jurisdictional"]))
    assert detail["generic"] > 0 and detail["jurisdictional"] > 0
    # And the counts the generated sentence prints must be counts, not the whole side.
    assert detail["generic_normative"] <= detail["generic"]
    assert detail["jurisdictional_documented"] <= detail["jurisdictional"]
    assert aligned is (not detail["generic_off"] and not detail["jurisdictional_off"])


def test_the_generated_block_carries_the_confound():
    """THE POINT OF THIS FILE. The caveat is emitted by the generator, not written around it.

    Prose beside a table can be removed by an edit that never touches a number, and a
    limitation that lives only in prose is the one that quietly stops being stated. A reader
    who meets these figures must meet the confound in the same block.
    """
    res = I.measure()
    if res is None:
        pytest.skip("no corpus in this tree")
    md = I.markdown(res)
    # Either wording is the caveat; which one appears depends on whether the alignment is
    # exact. What must never happen is the block carrying neither.
    assert ("confounded with jurisdiction" in md
            or "near-collinear with jurisdiction" in md), md[-400:]
    # AND THE COUNT IN IT MUST BE THE MEASURED ONE. The block said "All 10 generic items are
    # normative" over a bank where nine are, and this test passed because it only looked for
    # the phrase.
    _aligned, detail = I.check_confound()
    if "near-collinear" in md:
        assert "%d of the %d critic-framed generic items" % (
            detail["generic_normative"], detail["generic"]) in md, md[-400:]
    assert "one variable with two labels" in md
    assert "not a confound collection shrinks" in md


def test_the_headline_is_paired_not_pooled():
    """§2 convicts this project of reading a pooled aggregate as a within-unit result. The
    markdown must carry the per-model counts and the sign test, not only the pooled rates."""
    res = I.measure()
    if res is None:
        pytest.skip("no corpus in this tree")
    md = I.markdown(res)
    assert "Per model rather than pooled" in md
    assert "sign test" in md
    for key in ("documented_stronger_on", "normative_stronger_on", "tied", "p"):
        assert key in res


def test_a_tie_is_reported_and_not_folded_into_either_side():
    """Ties carry no direction. Counting them toward whichever side is being argued is the
    way a 35-vs-14 split becomes a 42-vs-14 split without anyone lying."""
    res = I.measure()
    if res is None:
        pytest.skip("no corpus in this tree")
    assert (res["documented_stronger_on"] + res["normative_stronger_on"] + res["tied"]
            == res["models"])


def test_sign_test_is_exact_and_two_sided():
    assert I._sign_test(0, 0) is None
    assert I._sign_test(5, 5) == pytest.approx(1.0)
    assert I._sign_test(0, 10) == pytest.approx(2 / 1024)
    assert I._sign_test(14, 35) < 0.01


def test_check_fails_on_a_panel_too_thin_for_a_sign_test(monkeypatch, capsys):
    thin = {"top_box": 3, "models": 4, "pooled": {}, "median_gap": -2.0,
            "documented_stronger_on": 1, "normative_stronger_on": 3, "tied": 0,
            "p": 0.625, "gaps": {}, "per_item": {}}
    monkeypatch.setattr(I, "measure", lambda *a, **k: thin)
    assert I.main(["--check"]) == 1
    assert "under the %d" % I.MIN_MODELS in capsys.readouterr().out


def test_not_applicable_is_not_a_pass(monkeypatch):
    monkeypatch.setattr(I, "measure", lambda *a, **k: None)
    assert I.main(["--check"]) == 2


def test_the_agreement_cut_matches_the_other_readers():
    import agreement_by_training as A
    import item_gradient as IG
    assert I.AGREE_ABOVE == A.AGREE_ABOVE == IG.AGREE_ABOVE
