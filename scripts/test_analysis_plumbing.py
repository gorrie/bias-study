"""Regression tests for the analysis plumbing: encoding, run discovery, gate templates.

WHY THIS FILE EXISTS
--------------------
This directory had exactly one test file (`test_sheet_parser.py`, the answer parser) and
three gates (`gen_paper --check`, `key_numbers --check`, `controls_audit --strict`). Gates check
the ARTIFACT against the data. They do not check the tooling's logic, and on 2026-09-01/02 that
distinction cost three real defects, every one of which a unit test would have caught in a
second:

  1. `gen_paper.run()` captured a child's UTF-8 stdout with the parent's cp1252 locale, so every
     em-dash in a generated block became three characters of mojibake -- and `--check` reported
     "all 8 generated blocks are current", because it corrupted BOTH sides of its own
     comparison. A gate that renders its input through the defect it is checking for is not a
     gate.
  2. `floor_table` kept a hardcoded include-list of run directories. 14 runs collected to
     extend the frontier order floor contributed nothing, and the file's own comment records
     the SAME failure a day earlier with 27 runs -- fixed then by adding two directories to the
     list, which guaranteed the recurrence.
  3. `key_numbers`' phrase template for `order_p90_local` read "p90 %d, max 24" -- a second
     number hardcoded inside the expectation for a different quantity. When the local max moved
     24 -> 22 the gate failed on a sentence that was correct.

Each class is tested here, on the principle that the defect that already happened is the one
most likely to happen again.

    python scripts/test_analysis_plumbing.py
"""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import sys

# Used by the one skip path in this file, and never imported until 2026-09-14 --
# so a checkout with no local hf.co/ build got NameError where it should have got
# a skip. Found by scripts/check_undefined_names.py, second instance of the same
# shape as recollect_at_cap.py's missing LEGACY_SEED.
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import floor_table as F      # noqa: E402
import gen_paper as G        # noqa: E402
import key_numbers as K      # noqa: E402
import studypaths as _SP  # noqa: E402

REPLACEMENT = "�"


# --------------------------------------------------------------------- 1. encoding

def test_generated_blocks_carry_no_replacement_characters():
    """The paper itself. 19 of these were committed and the freshness gate passed over them.

    SKIPS when the paper is absent, which is the state in the public replication package:
    the writeup is an authorial decision separate from shipping the tooling and the data. A
    replicator can reproduce every floor and every detection limit without it, and this test
    has nothing to check until they have it.
    """
    paper = os.path.join(STUDY, "PAPER-below-the-floor.md")
    if not os.path.exists(paper):
        return
    text = io.open(paper, encoding="utf-8").read()
    assert REPLACEMENT not in text, (
        "%d replacement character(s) in the paper -- a generated block was written through a "
        "mis-decoded pipe" % text.count(REPLACEMENT))
    assert "â€" not in text, "cp1252-mangled UTF-8 sequence in the paper"


def test_subprocess_capture_decodes_as_utf8():
    """`run()` must not decode a child's UTF-8 with the parent's locale.

    Asserted on a script whose output genuinely contains non-ASCII: the timeline table uses
    em-dashes. If this regresses, every generated block silently gains mojibake and --check
    stays green because it compares mangled against mangled.
    """
    out = G.run("timeline.py", ["--markdown"])
    assert out, "timeline.py produced nothing"
    assert REPLACEMENT not in out, "child output came back with replacement characters"
    assert "â€" not in out, "child output came back cp1252-mangled"


def test_run_uses_an_explicit_encoding():
    """Belt and braces: the call itself must name an encoding, not inherit the locale.

    Reads the `run` function's body rather than trying to find the end of the call -- the
    first attempt split on the next ')' and landed inside os.path.join(HERE, script), which
    is the kind of parsing that makes a test fail on correct code.
    """
    src = io.open(os.path.join(HERE, "gen_paper.py"), encoding="utf-8").read()
    body = src.split("\ndef run(", 1)[1].split("\ndef ", 1)[0]
    assert "subprocess.run(" in body, "run() no longer shells out; re-read this test"
    assert 'encoding="utf-8"' in body or "encoding='utf-8'" in body, (
        "gen_paper.run() calls subprocess.run without encoding='utf-8' -- text=True will "
        "decode the child's UTF-8 with the parent locale, which is cp1252 on this machine")


# ------------------------------------------------------- 2. run-directory discovery

def test_order_floor_discovers_a_new_run_directory():
    """A directory that lands tomorrow must be counted tomorrow, with no code edit.

    This is the test the include-list could never have passed. It writes a synthetic
    condition-A sheet into a new run directory, asserts the order floor sees the model, and
    removes it again.
    """
    probe_dir = os.path.join(STUDY, "runs", "_test-probe-order-discovery")
    model = "test-vendor/discovery-probe"
    os.makedirs(probe_dir, exist_ok=True)
    try:
        for seed, offset in ((101, 0), (202, 1)):
            record = {
                "schema": _SP.SCHEMA, "model": model, "condition": "A",
                "instrument": "ratchet-battery",
                "shuffle_seed": seed, "valid": True, "n_answers": 62,
                # Not a constant sheet: load() drops degenerate ones on purpose.
                "answers": [{"q": q, "position": (q + offset) % 4} for q in range(1, 63)],
            }
            with io.open(os.path.join(probe_dir, "probe_%d.jsonl" % seed), "w",
                         encoding="utf-8", newline="\n") as fh:
                fh.write(json.dumps(record) + "\n")

        cells = F._order_cells()
        # KEYED (model, temperature) SINCE 2026-09-07, when temperature joined the set of
        # non-order factors the floor holds fixed. This assertion read `model in cells` and
        # failed on the key shape rather than on the behaviour it is here to protect -- which
        # is that a NEW RUN DIRECTORY is discovered without being added to an include list.
        # Matched on the model element so the next factor added to the key does not break it
        # again for the same non-reason.
        mine = {k: v for k, v in cells.items() if k[0] == model}
        assert mine, (
            "a new run directory was invisible to the order floor -- the include-list "
            "regression is back")
        assert len(mine) == 1, (
            "the probe's two runs split across cells: %s -- they share a temperature (absent, "
            "so None) and must land in one group" % list(mine))
        assert set(next(iter(mine.values()))) == {101, 202}, mine
    finally:
        shutil.rmtree(probe_dir, ignore_errors=True)


def test_no_order_cell_pools_two_temperatures():
    """The order floor holds every non-order factor fixed, TEMPERATURE INCLUDED.

    This key has failed open three times, on a new factor each time: 2026-09-04 ten instruction
    templates all hashed to the canonical cell (107 runs, modal became a vote across
    paraphrases), and 2026-09-07 temperature-0 and temperature-0.7 runs pooled in **28 of 186**
    canonical cells. Each fix filtered the factor that had just broken it, which is why there
    was a third time.

    A FIRST VERSION OF THIS TEST WAS VACUOUS and passed for the wrong reason: it grouped the
    runs BY temperature and then asserted that each group held one temperature, which is true
    by construction whatever the code does. It would have passed against the buggy key just as
    happily. So this probes the BEHAVIOUR instead: write two runs that differ only in
    temperature, and assert the floor puts them in different cells.

    A future arm that varies some other parameter will not be caught by this test. The
    docstring on `_order_key` says what to do about that, and this is the shape of the test to
    copy for it.
    """
    probe_dir = os.path.join(STUDY, "runs", "2026-09-07-temp-key-probe")
    model = "test-vendor/temp-probe"
    os.makedirs(probe_dir, exist_ok=True)
    try:
        # Same model, same condition, same order (canonical), same template. Different
        # temperature. Under the pre-2026-09-07 key these two were ONE cell and their modal
        # was a vote across temperatures.
        for temp, offset in ((0.0, 0), (0.7, 1)):
            record = {
                "schema": _SP.SCHEMA, "model": model, "condition": "A",
                "instrument": "ratchet-battery",
                "shuffle_seed": None, "temperature": temp, "valid": True, "n_answers": 62,
                "answers": [{"q": q, "position": (q + offset) % 4} for q in range(1, 63)],
            }
            with io.open(os.path.join(probe_dir, "probe_%s.jsonl" % temp), "w",
                         encoding="utf-8", newline="\n") as fh:
                fh.write(json.dumps(record) + "\n")

        cells = F._order_cells()
        mine = {k: v for k, v in cells.items() if k[0] == model}
        assert len(mine) == 2, (
            "two runs differing only in TEMPERATURE landed in %d cell(s), not 2 -- the order "
            "floor is pooling across temperature again and its modal is a majority vote "
            "across them: %s" % (len(mine), list(mine)))
        assert {k[1] for k in mine} == {0.0, 0.7}, list(mine)
        # And neither cell may pair with itself: one order each, so no order pairs at all.
        for key, orders in mine.items():
            assert list(orders) == [None], (key, list(orders))
    finally:
        shutil.rmtree(probe_dir, ignore_errors=True)


def test_a_local_hf_build_is_not_classed_as_hosted():
    """`hf.co/vendor/Model:Q4_K_M` is a LOCAL Ollama build and has two slashes.

    The class split's test was `"/" in model` until 2026-09-07, which would have put a local
    model in the row headed "hosted over an API". No published number was wrong -- the only
    `hf.co/` builds in the corpus have cells too thin to enter a class-split row -- but the next
    planned collection is 2026-generation open weights run LOCALLY, to separate vintage from
    serving path, and that collection would have landed on the hosted side and answered its own
    question backwards.

    `served_over_api()` reads each run's `channel` field instead. This asserts the case the
    slash test gets wrong, and the case it gets right, so a revert to the name-based test fails
    here rather than in a result.
    """
    local_hf = "hf.co/lmstudio-community/Qwen3.8-27B-GGUF:Q4_K_M"
    if local_hf not in F._CHANNEL_CACHE:
        F.served_over_api(local_hf)          # populate from the corpus
    if local_hf not in F._CHANNEL_CACHE:
        pytest.skip("no hf.co/ local build in this checkout's runs")
    assert F.served_over_api(local_hf) is False, (
        "a local hf.co/ build is being classed as hosted -- the split test is back to "
        "matching on the slash in the model name")
    assert F.served_over_api("openai/gpt-5.6-luna") is True


def test_canonical_order_is_not_passed_as_the_string_None():
    """`--shuffle-seed None` is an argparse error and writes no record.

    2026-09-07: the first off-panel order arm queued the canonical order (shuffle `None`) and
    the collector built `["--shuffle-seed", str(shuffle)]`, sending the four characters `None`
    to a parameter declared `type=int`. run_battery exited without writing anything, the
    collector printed "(no result line)" for that cell and then **"collected 3 cell(s); 0
    remain"**, exiting 0 with the canonical arm empty -- so the arm had two shuffled orders and
    nothing to pair them against.

    Two assertions, because either alone is weak: run_battery really does reject the string
    (so the guard is necessary), and the collector really does guard it (so the bug is gone).
    """
    import subprocess

    # 1. The parameter is int-typed, so "None" is an error rather than a null.
    r = subprocess.run([sys.executable, os.path.join(HERE, "run_battery.py"),
                        "--model", "x", "--condition", "D", "--shuffle-seed", "None"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode != 0, "run_battery accepted --shuffle-seed None; the guard's premise is gone"

    # 2. The collector omits the flag entirely for the canonical order.
    src = io.open(os.path.join(HERE, "order_floor_wave.py"), encoding="utf-8").read()
    body = src.split("def main(", 1)[1]
    assert "if shuffle is not None:" in body, (
        "order_floor_wave no longer guards the canonical order -- it will send the literal "
        "string None to an int-typed parameter and write no records")


def test_order_exclude_is_actually_applied():
    """An exclusion that is declared and not applied is worse than none at all.

    The first version of the discovery change declared ORDER_EXCLUDE and never consulted it.
    """
    assert F.ORDER_EXCLUDE, "ORDER_EXCLUDE is empty; nothing to verify"
    probe = os.path.join(STUDY, "runs", sorted(F.ORDER_EXCLUDE)[0])
    if not os.path.isdir(probe):
        return                      # the excluded directory is not present in this checkout
    src = io.open(os.path.join(HERE, "floor_table.py"), encoding="utf-8").read()
    body = src.split("def _order_cells(", 1)[1].split("\ndef ", 1)[0]
    assert "ORDER_EXCLUDE" in body, "_order_cells does not consult ORDER_EXCLUDE"


def test_order_sources_reports_what_contributed():
    """"The floor reads everything" has to be checkable, not asserted.

    THE ASSERTION WAS ">4 DIRECTORIES", AND IT FIRED ON 2026-09-17 FOR THE RIGHT REASON.
    It was written against a corpus spread over many dated collections, where reading one
    directory meant the floor had lost the others. This design collects the whole wave into a
    single directory, so "more than four" is now a property of a corpus that no longer exists
    rather than of the floor's coverage -- and a test that demands it can only be satisfied by
    fragmenting the collection.

    Loosening it to `> 0` would have thrown the guarantee away. What the test is FOR is that
    the floor reads every directory holding sheets it is entitled to read, so that is what it
    now checks: the set the floor reports against the set on disk, derived independently.
    """
    if not F._tree_has_run_data():
        import pytest
        pytest.skip("no runs/ corpus in this tree -- NOT APPLICABLE, not a pass")
    sources = F.order_sources()
    assert sources, "no run directory contributed a condition-A sheet"

    # Independently derived: every run directory under runs/ holding a valid condition-A
    # sheet on the live instrument. If one of these is missing from `sources`, the floor is
    # skipping a directory it should be reading -- which is the defect, at any count.
    import collections as _c
    import glob as _g
    import io as _io
    import json as _j
    import os as _os
    on_disk = _c.Counter()
    for path in sorted(_g.glob(_os.path.join(F.STUDY, "runs", "**", "*.jsonl"),
                               recursive=True)):
        rel = _os.path.relpath(path, _os.path.join(F.STUDY, "runs")).replace("\\", "/")
        top = rel.split("/")[0]
        if top in F.ORDER_EXCLUDE:
            continue
        for line in _io.open(path, encoding="utf-8", errors="replace"):
            if not line.strip():
                continue
            try:
                rec = _j.loads(line)
            except ValueError:
                continue
            if (_SP.is_run_record(rec) and rec.get("valid")
                    and rec.get("condition") == "A" and F._instrument_matches(rec)):
                on_disk[top] += 1

    missing = sorted(set(on_disk) - set(sources))
    assert not missing, (
        "%d run directory(ies) hold valid condition-A sheets on this instrument and did not "
        "reach the order floor: %s" % (len(missing), ", ".join(missing)))


# ----------------------------------------------------------- 3. gate self-consistency

#: Literal numbers a gated phrase may contain, each a FIXED property of the instrument or a
#: label rather than a measured value. Anything not on this list is a quantity nothing checks.
#: Adding an entry is a deliberate act; that is the point of the list being here.
ALLOWED_LITERALS = {
    # ITEMS IN THE INSTRUMENT. A fixed property of the bank, not a measured value. This was
    # "62" -- the retired bank's length -- so a paper sentence quoting 62 items passed the
    # gate unexamined while every floor beneath it was counted out of 32.
    "32",
    "90",    # the percentile in "p90" -- a label for the statistic, not its value.
    "2026",  # a year.
}


#: Every conversion a gated phrase may carry: `%d`, `%s`, and a float with a precision spec.
#: `%%` is an escaped literal percent sign and is deliberately NOT a placeholder.
_PLACEHOLDER = re.compile(r"%(?:%|d|s|\.\d+f)")


def _placeholders(template):
    return [m for m in _PLACEHOLDER.findall(template) if m != "%%"]


def test_no_phrase_template_hides_a_second_number():
    """A gated phrase may name ONE measured quantity: the one it checks.

    The defect: "our order floor is p90 %d, max 24" checked the p90 and silently asserted the
    max. When the max moved 24 -> 22 the gate failed on a sentence that was correct, and
    pointed at the wrong quantity.

    A blanket "no digits" rule was the first attempt and it was too crude -- it flagged "62
    items" and "p90", which are a constant and a label. So the rule is a whitelist of literals
    that cannot drift, and everything else has to be a placeholder.
    """
    offenders = []
    for row in K.build():
        template = row["phrase"]
        # `%.3f` IS A PLACEHOLDER, and this stripped only %d and %s -- so every float phrase
        # read its own precision spec as a hidden literal ("**%.3f**" reported a stray 3) and
        # the sibling test counted it as ZERO placeholders. Both fired on correct phrases the
        # moment §1's medians and §4's judge spread were registered, which is a guard failing
        # a true statement: the most expensive kind, because the tempting fix is the phrase.
        stripped = _PLACEHOLDER.sub("", template)
        # A BACKTICKED IDENTIFIER IS NOT A QUANTITY. `gpt-6-astra-pro` carries a 6 that names
        # a model generation, and flagging it pushed toward the worst available fix: dropping
        # the model name out of the anchor, which is the thing that makes the anchor unique.
        # Code spans are removed before the scan; anything outside them still has to be a
        # placeholder or a listed constant.
        stripped = re.sub(r"`[^`]*`", " ", stripped)
        for literal in re.findall(r"\d+", stripped):
            if literal not in ALLOWED_LITERALS:
                offenders.append((row["key"], literal, template))
    assert not offenders, (
        "phrase template(s) assert a number nothing checks: %s" % offenders)


def test_no_generated_markdown_table_ships_inside_a_code_fence():
    """A markdown table inside a code fence renders as literal pipe characters.

    `gen_paper`'s `unfenced` tuple decides per block. The fence is right for the blocks that
    emit fixed-width text -- the vendor refusal table, the power table, the gaps tally -- and
    wrong for every block that emits a real table. Three were wrong until 2026-09-22: §3b's
    training-class split, §3b's intensity table, and §9.1's multiple-comparison accounting,
    which is the table a reviewer opens to see how many tests the paper ran. All three had
    shipped as raw pipes since they were added, and `gen_paper --check` could not see it,
    because it compares each block against the generator and the generator was producing the
    fence. A gate that regenerates the artifact cannot catch a defect in the regeneration.
    """
    import io
    import os
    paper = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "PAPER-below-the-floor.md")
    text = io.open(paper, encoding="utf-8").read().replace("\r\n", "\n")
    blocks = re.findall(r"<!-- GEN:(\w+) -->(.*?)<!-- /GEN:\1 -->", text, re.S)
    assert blocks, "no generated blocks found -- this test would check nothing"
    fenced = [name for name, body in blocks
              if "```" in body and re.search(r"^\|[-: |]+\|\s*$", body, re.M)]
    assert not fenced, (
        "generated block(s) emit a markdown table inside a code fence, so they render as "
        "literal pipes: %s. Add them to `unfenced` in gen_paper.py." % fenced)


def test_every_gated_phrase_has_exactly_one_placeholder():
    for row in K.build():
        n = len(_placeholders(row["phrase"]))
        assert n == 1, "%s has %d placeholders: %r" % (row["key"], n, row["phrase"])


def test_gated_values_are_not_none():
    """None is now a DELIBERATE state, and the contract it has to keep is stated here.

    This asserted that no computed value is ever None, as a guard against one leaking in
    by accident. On 2026-09-16 `key_numbers.UNAVAILABLE` (= None) became the explicit way
    to say "this tree cannot compute that number" -- because the alternative was worse:
    `wave_panel_size` read `len(PANEL_MODELS)`, the frozen panel is not in the public
    mirror, and the listing printed

        wave_panel_size   0   models in the frozen wave panel

    A missing input was being reported as a measurement of zero, and any phrase gated on
    it would have been checked against a number nothing measured.

    So the rule is no longer "never None". It is: a None value must be one of the keys
    documented as panel-derived, and must never be a surprise. Every other key still has
    to compute, which is what this guards now.
    """
    # AND A TREE WITH NO CORPUS CANNOT COMPUTE ANY OF THEM. Every floor-derived key is
    # UNAVAILABLE in the public mirror until a scrubbed export lands, which is an absent
    # input and not an uncaught failure -- the same distinction this test already draws for
    # the panel-derived keys, one level up.
    if not F._tree_has_run_data():
        import pytest
        pytest.skip("no runs/ corpus in this tree -- NOT APPLICABLE, not a pass")
    panel_derived = {"wave_panel_size", "manip_refusing_sitting"}
    # A SECOND DOCUMENTED CATEGORY, added 2026-09-18: the placebo control-arm keys.
    #
    # They come from a 20,000-draw bootstrap over the whole panel -- minutes per run -- so
    # they are cached in data/placebo-control.json rather than recomputed on every listing.
    # `key_numbers.placebo_control()` re-reads the corpus and REFUSES the cache when the
    # record count has moved, which it does constantly while a wave is collecting. That
    # refusal surfaces as UNAVAILABLE here.
    #
    # The alternative was worse in the way this file already documents: answering with a
    # cached number whose corpus has changed underneath it is `data/modal-noise.json`, which
    # printed "110 cells, median 1, p90 3" for weeks after the instrument was replaced.
    # An absent number is a stated absence; a stale one is a false measurement.
    #
    # The release gate is where this must NOT be absent, and that is enforced separately:
    # a release runs against a frozen corpus, so the cache is rebuildable and fresh.
    # The same exemption, for the same reason, extended 2026-09-23 to the two caches whose
    # scripts run for over half an hour: `calibrate_estimators.py` and `exact_vs_bootstrap.py`.
    # Their figures head the paper and were four days stale across a corpus freeze with every
    # gate green, so they are now cached with provenance and REFUSED when the record count
    # moves. A refused cache surfaces here as None, which is a stated absence -- the
    # alternative, quoting a figure whose corpus has changed underneath it, is the failure
    # this whole group exists to prevent.
    cache_derived = {"placebo_panel", "placebo_moves_models", "placebo_both_move",
                     "placebo_only", "placebo_median_effect", "placebo_sig_positive",
                     "placebo_sig_negative",
                     "calib_boot_fpr", "calib_exact_fpr", "calib_cells",
                     "evb_boot_survive", "evb_exact_survive", "evb_lost", "evb_an_lost"}
    stale_cache = False
    try:
        K.placebo_control()
    except K.StaleCache:
        stale_cache = True

    for row in K.build():
        if row["value"] is K.UNAVAILABLE:
            assert row["key"] in panel_derived or row["key"] in cache_derived, (
                "%s computed to None and is not one of the documented panel-derived or "
                "cache-derived keys. Either it has an uncaught failure, or it needs to be "
                "declared here with the reason it can be absent." % row["key"])
            if row["key"] in cache_derived:
                # It may only be absent for the ONE stated reason. If the cache is fresh and
                # the key is still None, something else failed and is hiding behind a
                # documented exemption -- which is how an exemption becomes a blanket.
                assert stale_cache, (
                    "%s is None while data/placebo-control.json is present and FRESH -- the "
                    "cache loaded and matched the corpus, so this is a real failure, not an "
                    "absent input" % row["key"])
                continue
            assert not K.PANEL_AVAILABLE, (
                "%s is None while data/wave-panel.json IS present in this tree -- the panel "
                "loaded, so this is a real failure and not an absent input" % row["key"])
            continue
        assert row["value"] is not None, row["key"]


# ------------------------------------------------- 4. the floors do not depend on file order
#
# Found 2026-09-06. `gen_paper --check` was red in CI and green on the author's machine against
# the SAME COMMIT, differing in one number: the presentation-order endpoint p90, 10 on Windows
# and 11 on Linux, over the same 84 pairs. Same count, different values, so the pairs differed.
#
# `modal()` built each cell's reference sheet with `Counter.most_common(1)`, which breaks a TIE
# by insertion order. Insertion order was `load()`'s read order and `load()` globbed unsorted,
# so on a 2-2 split between Disagree and Agree the reference sheet -- and every endpoint delta
# measured against it -- was decided by whether the corpus sat on NTFS or ext4.
#
# A published percentile was a property of the filesystem. Both halves are fixed: the glob is
# sorted so the corpus order is canonical, and modal() breaks ties by the lower position
# explicitly, so it does not depend on order even when handed runs in some other sequence.

def test_modal_is_order_independent():
    import itertools
    runs = [{"q1": 1}, {"q1": 1}, {"q1": 2}, {"q1": 2}]      # a 2-2 tie
    got = {tuple(sorted(F.modal(list(p)).items())) for p in itertools.permutations(runs)}
    assert len(got) == 1, "modal() returns %d different answers for one multiset: %r" % (
        len(got), got)


def test_modal_breaks_ties_to_the_lower_position():
    """The rule is arbitrary. Being WRITTEN DOWN is the whole difference, so it is asserted."""
    assert F.modal([{"q": 1}, {"q": 2}]) == {"q": 1}
    assert F.modal([{"q": 2}, {"q": 1}]) == {"q": 1}
    assert F.modal([{"q": 0}, {"q": 3}, {"q": 3}]) == {"q": 3}   # no tie: the mode wins


def test_load_reads_the_corpus_in_a_canonical_order():
    src = io.open(os.path.join(HERE, "floor_table.py"), encoding="utf-8").read()
    unsorted = [l for l in src.splitlines()
                if "glob.glob(" in l and "sorted(" not in l and not l.strip().startswith("#")]
    assert not unsorted, ("floor_table globs without sorting, so the corpus is read in "
                          "filesystem order again:\n  " + "\n  ".join(unsorted))


def test_floors_survive_a_reordered_corpus():
    """End to end: shuffle what glob returns and every floor must be byte-identical."""
    import glob as _glob
    import random as _random
    # EVERY ARM IN THE REGISTRY, not a hand-typed subset -- adding a floor to ALL_FLOORS
    # without adding it here left the new arm untested for exactly this defect, and the
    # determinism bug this test exists for (glob order reaching modal()'s tie-break, a
    # published percentile that differed between CI and the author's machine) is one any
    # arm can have.
    floors = list(F.ALL_FLOORS)

    def snapshot():
        F.DROPPED.clear()
        F._DROPPED_SEEN.clear()
        out = []
        for fn in floors:
            r = fn()
            # AN ARM THAT COMPUTES NOTHING IS RECORDED AS SUCH, not skipped and not
            # subscripted. Several arms are retired by dated ruling or awaiting collection,
            # and this test used to index their None straight into a TypeError -- so a suite
            # that should have said "the floors are order-independent" said nothing at all.
            # Its emptiness is itself order-independent and worth asserting.
            if not r:
                out.append((fn.__name__, None))
                continue
            rows = list(r.values()) if isinstance(r, dict) and "name" not in r else [r]
            for rec in sorted((x for x in rows if x), key=lambda x: x["name"]):
                out.append((rec["name"], rec["n"], rec["side"], rec["endpoint"],
                            rec["side_ci"]))
        return out

    # A GROWING CORPUS IS NOT AN ORDER-DEPENDENT FLOOR, AND THIS TEST USED TO SAY IT WAS.
    #
    # `snapshot()` is called three times against the LIVE runs/ tree. On 2026-09-19 the
    # release checklist ran while four collection chains were writing, a sheet landed between
    # two of the calls, the floors differed and the failure read "a floor changed when the
    # corpus was read in another order". The corpus had changed, not the order. A check that
    # accuses the wrong thing in the ordinary case is a check operators learn to skip -- this
    # file convicts other code of exactly that.
    def fingerprint():
        # EVERY corpus root. This fingerprint exists to tell "the corpus changed under us"
        # apart from "a floor is order-dependent", and it can only do that over the corpus the
        # snapshot actually reads. `runs_root()` returns one root; a sheet landing in the other
        # one would move a floor while the fingerprint stayed byte-identical -- and the test
        # would then convict the analysis of order-dependence for a corpus that moved, which is
        # the precise accusation the comment above says it must never make.
        seen = []
        for root in _SP.run_roots():
            for path in sorted(_glob.glob(os.path.join(root, "**", "*.jsonl"),
                                          recursive=True)):
                try:
                    st = os.stat(path)
                except OSError:
                    continue
                seen.append((path, st.st_size))
        return seen

    before = fingerprint()
    base = snapshot()
    real = _glob.glob
    try:
        for shuffle in (lambda L: L[::-1],
                        lambda L: _random.Random(7).sample(L, len(L))):
            _glob.glob = lambda *a, **k: shuffle(list(real(*a, **k)))
            got = snapshot()
            if got != base:
                _glob.glob = real
                after = fingerprint()
                if after != before:
                    changed = len(set(after) ^ set(before))
                    pytest.skip(
                        "the corpus changed under the test -- %d file entr(ies) differ "
                        "between the first and last read, so the floors were computed over "
                        "two different corpora. This says nothing about order-independence. "
                        "Re-run when collection is not writing." % changed)
                raise AssertionError(
                    "a floor changed when the corpus was read in another order, and the "
                    "corpus itself did not change")
    finally:
        _glob.glob = real
        F.DROPPED.clear()
        F._DROPPED_SEEN.clear()


def test_sweep_records_will_not_match_an_unlabelled_batch():
    """A record with no `batch` field must never be read as belonging to a batch size.

    This is the fourth time in three days that a factor was added to the study and something
    downstream failed OPEN on it -- `_order_key` pooled across template, then temperature, then
    decoding, and now batch size. The first three were caught by a floor coming out wrong, which
    is the expensive way to find out.

    The specific hazard here is real and on disk: `runs/2026-09-07-constrained-replicate/`
    contains three chunked runs collected before the writer emitted `batch`. They were produced
    at batch=8, but only a shell history says so. If `load_sweep_records` matched on anything
    looser than an exact `batch` equality -- a truthiness test, a `.get("batch", 8)` default --
    those three sheets would silently join the batch=8 pool and a fabricated provenance would
    become a number in a table.
    """
    import constrained_probe as C                     # noqa: PLC0415
    import io as _io                                  # noqa: PLC0415
    import json as _json                              # noqa: PLC0415
    import os as _os                                  # noqa: PLC0415
    import shutil as _sh                              # noqa: PLC0415
    import tempfile as _tf                            # noqa: PLC0415

    def rec(**kw):
        base = {"schema": _SP.SCHEMA, "model": "m", "condition": "D",
                "instrument": "ratchet-battery",
                "valid": True, "seed": 1,
                "answers": [{"q": "q%d" % i, "position": 1} for i in range(62)]}
        base.update(kw)
        return _json.dumps(base)

    tmp = _tf.mkdtemp()
    try:
        with _io.open(_os.path.join(tmp, "a.jsonl"), "w", encoding="utf-8") as fh:
            fh.write(rec(seed=10, batch=8) + "\n")
            fh.write(rec(seed=11) + "\n")               # NO batch field -- the hazard
            fh.write(rec(seed=12, batch=16) + "\n")
            fh.write(rec(seed=13, batch=8, valid=False) + "\n")
        got = C.load_sweep_records(tmp, "m", "D", 8)
        assert sorted(got) == [10], sorted(got)

        # And an unlabelled record is not reachable by asking for any batch size at all.
        for b in (1, 8, 16, 62, None):
            assert 11 not in C.load_sweep_records(tmp, "m", "D", b), b
    finally:
        _sh.rmtree(tmp, ignore_errors=True)


def test_doc_link_gate_bites():
    """The link gate must FAIL on a dead link, not merely pass on a clean tree.

    A gate is only worth its run time if a defect makes it red, and this one is a walk over a
    tree that is usually clean -- the exact shape that passes forever while blind. Two things
    are asserted: that a real dead link is reported, and that the classes deliberately NOT
    checked stay unchecked, so a later "improvement" that starts resolving external URLs or
    heading anchors fails here rather than turning the gate into a network call.
    """
    import check_doc_links as L                       # noqa: PLC0415
    import io as _io                                  # noqa: PLC0415
    import os as _os                                  # noqa: PLC0415
    import tempfile as _tf                            # noqa: PLC0415

    tmp = _tf.mkdtemp()
    try:
        real = _os.path.join(tmp, "real.md")
        _io.open(real, "w", encoding="utf-8").write("x\n")
        doc = _os.path.join(tmp, "doc.md")
        _io.open(doc, "w", encoding="utf-8").write(
            "[live](real.md)\n"
            "[dead](gone.md)\n"
            "[anchored-live](real.md#some-heading)\n"
            "[external](https://example.com/missing.md)\n"
            "[fragment](#section)\n"
            "![image-dead](charts/nope.png)\n")
        n_links, dead = L.check(tmp)

        found = sorted(t for _d, _l, t in dead)
        assert found == ["charts/nope.png", "gone.md"], found
        # The live link, the anchored live link, the dead link and the dead image are paths;
        # the external URL and the bare fragment are not counted at all.
        assert n_links == 4, n_links
    finally:
        import shutil as _sh                          # noqa: PLC0415
        _sh.rmtree(tmp, ignore_errors=True)


def test_doc_links_clean_in_this_tree():
    """And the tree itself is clean, which is the gate's actual job."""
    import check_doc_links as L                       # noqa: PLC0415
    _n, dead = L.check(L.ROOT)
    assert not dead, "dead markdown link(s): %s" % (dead,)


if __name__ == "__main__":
    import traceback
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("ok    %s" % name)
            except Exception:
                failures += 1
                print("FAIL  %s" % name)
                traceback.print_exc()
    print()
    print("%d failure(s)" % failures)
    raise SystemExit(1 if failures else 0)
