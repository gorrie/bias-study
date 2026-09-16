"""Every website surface that states a study number must be gated, and the gate must not crash.

Two failures this guards, both of which happened.

1. A page gated and its twin ungated is not half-protected; it is a page that is right and a
   page that is wrong, published together, under the same argument. `alignment-mask.md` was
   gated and withdrew three per-model deltas. `deception-delta.md` was BUILT on those three
   deltas, was not gated, and kept publishing them.

2. Registering a phrase against a key that surface_numbers() does not produce, or one that is
   None in this tree, raised TypeError out of main() -- so the surfaces that had already passed
   printed PASS and the command still died on a stack trace. A gate that cannot say which key
   it failed to resolve is worse than one that fails.
"""
import io
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import key_numbers as K  # noqa: E402

WEBSITE_SURFACES = [n for n, s in K.SURFACES.items()
                    if os.sep + "website" + os.sep in str(s.get("path", ""))]


def all_rows():
    """check_surface resolves a phrase from the union of the paper's rows and the surfaces'."""
    return K.build() + K.surface_numbers()


def rows():
    return {r["key"]: r["value"] for r in all_rows()}


def test_the_website_surfaces_are_registered():
    """The corrected dispatch and the discovery page carry judge-layer numbers and are gated."""
    paths = {os.path.basename(s["path"]) for s in K.SURFACES.values()}
    for expected in ("deception-delta.md", "alignment-mask.md", "gemma-delta.md"):
        assert expected in paths, "%s states study numbers and is not gated" % expected


def test_every_registered_phrase_resolves_to_a_computed_number():
    """A gated phrase must name a key this tree can actually produce.

    ONE EXEMPTION, AND IT IS NARROW. The panel-derived keys read
    `data/wave-panel.json`, a collection artifact that lives in the private study tree, so
    in the public mirror they compute to `key_numbers.UNAVAILABLE` on purpose -- the
    alternative was `len([])`, which printed a frozen panel of 0 models and read as a
    measurement. Absent input is not the same defect as a phrase naming a key that does
    not exist, and conflating them here would force the sentinel back out again.

    Where the panel IS present the exemption does not apply, so the strict assertion still
    runs in the tree that owns the number.
    """
    computed = rows()
    missing = []
    for name in WEBSITE_SURFACES:
        for key in K.SURFACES[name]["phrases"]:
            if key not in computed:
                missing.append((name, key, "no such computed key"))
            elif computed[key] is None:
                if K.PANEL_AVAILABLE:
                    missing.append((name, key, "None although the panel loaded"))
    assert not missing, (
        "these phrases name a key surface_numbers() cannot produce here: %r" % missing)


def test_a_missing_key_is_reported_not_raised(tmp_path):
    doc = tmp_path / "surface.md"
    io.open(doc, "w", encoding="utf-8", newline="").write("nothing in particular\n")
    K.SURFACES["_test_missing"] = {
        "path": str(doc), "phrases": {"_no_such_key_anywhere": "the value is %d"}}
    try:
        out = K.check_surface("_test_missing", all_rows())
    finally:
        K.SURFACES.pop("_test_missing", None)
    assert out and any("no such computed number" in str(c) for r in out for c in r), out


def test_a_none_valued_key_reports_instead_of_crashing(tmp_path):
    """THE ACTUAL CRASH. A key that exists but computes to None in this tree used to raise
    TypeError out of main(), so --check-website printed PASS for the surfaces it had already
    reached and then died on a stack trace instead of naming the key."""
    doc = tmp_path / "surface.md"
    io.open(doc, "w", encoding="utf-8", newline="").write("nothing in particular\n")
    K.SURFACES["_test_none"] = {
        "path": str(doc), "phrases": {"_test_none_key": "the value is %d"}}
    rows_with_none = all_rows() + [{"key": "_test_none_key", "value": None, "what": "none"}]
    try:
        out = K.check_surface("_test_none", rows_with_none)
    finally:
        K.SURFACES.pop("_test_none", None)
    assert out, "a None-valued key must be reported as a failure"
    assert any("uncomputable" in str(c) for r in out for c in r), (
        "the report must say the key could not be resolved: %r" % (out,))


def test_the_judge_layer_numbers_come_from_the_public_mirror():
    """A public page must state a number the PUBLIC artifact reproduces.

    The private tree holds 4,744 records carrying a per-judge breakdown and the mirror holds
    4,668 -- the mirror is the scrubbed, published corpus and it is what a reader re-runs.
    Gating the website against the private tree would fail a correct page, and the tempting
    fix -- editing the page -- would publish a figure no reader can get.

    Asserted against the mirror alone and deliberately NOT by comparing with this tree's own
    reader: `judge_lean.scored_records` resolves through `studypaths`, whose root is read from
    the environment at import, so a sibling test that points STUDY_ROOT at a fixture makes that
    comparison return zero. The mirror path here is resolved independently of STUDY_ROOT, which
    is the property being tested.
    """
    n, top, bottom, spread = K._mirror_judge_stats()
    if n is None:
        return  # mirror not on disk; the release gate covers that separately
    assert n > 0 and top is not None and bottom is not None
    assert top > bottom, "the most skeptical judge must sit above the most deferential"
    assert abs(top - bottom) < 2.0, "a spread that large would mean the panel is not a panel"
