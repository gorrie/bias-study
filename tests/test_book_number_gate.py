"""The printed books were the least-gated surface in the project.

WHY THIS FILE EXISTS
--------------------
`key_numbers.py` gated the public README, the research page, three dispatches and
the barometer. It did not gate a single number in the books -- the one surface
that cannot be corrected after the fact.

AUDIT-2026-09-14-book-numbers.md checked every figure in Ratchet ch22 against the
corpus and found four that moved, including "thirty-six frontier AI models" (35;
36 sums per-run counts and double-counts one model) and "five open-weight models"
abliterated (one clears the measured resample floor). Nothing would have caught
any of them, because nothing was looking.

The gate is EXPECTED TO FAIL until the correction pass. A gate that goes green
before the prose is fixed would be worse than none.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import key_numbers as K  # noqa: E402


def _rows():
    return {r["key"]: r["value"] for r in K.surface_numbers()}


# ---------------------------------------------------------------- generators

def test_the_four_book_numbers_are_generated():
    rows = _rows()
    for key in ("may_models_distinct", "may_records_main",
                "hedge_multiple_pooled", "ablation_families_confirmed"):
        assert key in rows, "%s is not generated" % key


def test_model_count_is_distinct_not_the_sum_of_per_run_counts():
    """36 double-counts z-ai/glm-4.7, which appears in two of the four runs."""
    v = _rows().get("may_models_distinct")
    if v is None:
        return
    assert v != 36, "the model count is back to the per-run sum"
    assert 30 <= v <= 40, "implausible model count %r" % v


def test_the_hedge_multiple_is_the_pooled_figure_as_a_decimal():
    """7.2x is score-3 against score-1 ALONE on 19 records; the book says '1 or a 5'."""
    v = _rows().get("hedge_multiple_pooled")
    if v is None:
        return
    assert isinstance(v, str) and "." in v, (
        "the multiple must be a printable decimal, not %r -- an integer in tenths "
        "made the gated phrase read '37 times'" % v)
    assert 2.0 < float(v) < 5.0, "pooled hedge multiple %r is outside any plausible range" % v


def test_confirmed_families_counts_established_not_reported():
    v = _rows().get("ablation_families_confirmed")
    if v is None:
        return
    assert v < 5, "all five families are counted as confirmed again"


def test_the_family_count_comes_from_the_tool_not_a_literal():
    import inspect
    import abliteration_effect_check as A
    src = inspect.getsource(A.confirmed_family_count)
    assert "CONFIRMED_LABEL" in src, "the count retypes the verdict string"
    assert "main(" in src, "the count does not run the tool's own report"


# ---------------------------------------------------------------- the surface

def test_the_book_surface_is_registered():
    assert any(n.startswith("book-") for n in K.SURFACES), "no book surface is gated"


def test_check_books_covers_every_book_surface():
    """A surface declared and not dispatched is the same silence as not declaring it."""
    import inspect
    src = inspect.getsource(K.main)
    assert "args.check_books" in src
    assert 'n.startswith("book-")' in src


# ---------------------------------------------------------------- spelling

def test_spelled_forms_match_house_style():
    assert K._spell(35) == "thirty-five"
    assert K._spell(1) == "one"
    assert K._spell(19) == "nineteen"
    assert K._spell(80) == "eighty"


def test_large_and_non_integers_are_not_spelled():
    """780 is printed as digits; a ratio string has no spelled form."""
    assert K._spell(780) is None
    assert K._spell("3.7") is None
    assert K._spell(None) is None
    assert K._spell(True) is None


def test_a_spelled_number_satisfies_a_digit_template():
    """The point of the speller: correct prose must be able to pass.

    Without this, a chapter correctly reading "thirty-five frontier AI models"
    would fail a gate whose template says %d -- and a gate that correct prose
    cannot satisfy is one that gets switched off.
    """
    import tempfile
    rows = _rows()
    if rows.get("may_models_distinct") is None:
        return
    spelled = K._spell(rows["may_models_distinct"])
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "ch.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("sent to %s frontier AI models, in three framings each.\n" % spelled)
        saved = K.SURFACES["book-ratchet-ch22"]["path"]
        try:
            K.SURFACES["book-ratchet-ch22"]["path"] = path
            failures = K.check_surface("book-ratchet-ch22", [])
        finally:
            K.SURFACES["book-ratchet-ch22"]["path"] = saved
    keys = [f[0] for f in failures]
    assert "may_models_distinct" not in keys, (
        "spelled-out prose failed the digit template; the speller is not being applied")
