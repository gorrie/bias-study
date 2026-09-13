"""Rung 2 of the escalation ladder: the README may not claim a direction the corpus lacks.

The README published "only the layered stack adds force, to a ceiling" for four months with
nothing computing it. `analysis.py` keys on conditions A and B; this arm runs B-STM,
B-Parseltongue and B-Layered, so its records matched no branch and its ANALYSIS.md is a heading
for every table and rows under none. The claim was never wrong on purpose -- it was never
checked, which on this instrument is the same thing.
"""
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import pipeline_rung as P  # noqa: E402

README = ROOT / "README.md"


def test_no_contrast_in_this_arm_clears_zero():
    res = P.estimate()
    if not res:
        return  # arm absent from this tree
    clean = [c for c in res["contrasts"] if c["excludes_zero"]]
    assert not clean, (
        "a rung-2 contrast now excludes zero: %r. That is a real result -- update the README "
        "row and this test together, deliberately." % clean)


def test_the_arm_is_still_one_sample_per_cell():
    """The binding limitation. When W13 lands this fails, which is the point."""
    res = P.estimate()
    if not res:
        return
    assert res["samples_per_cell"] == 1, (
        "replicates have landed; re-derive the rung and rewrite the README row against the "
        "pre-registered predictions in PREREG-2026-09-13-pipeline-rung.md")


def test_the_readme_does_not_claim_a_direction_for_rung_2():
    if not README.exists():
        return
    text = io.open(README, encoding="utf-8", errors="replace").read()
    banned = "only the layered stack adds force"
    body = text.replace('"' + banned, "")  # the correction quotes the old claim; that is allowed
    assert banned not in body, (
        "the README asserts a rung-2 direction again. Every interval in this arm spans zero.")
