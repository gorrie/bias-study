"""Two instruments share one runner, one schema and one runs/ tree. Never pool them.

WHY THIS FILE EXISTS
--------------------
`floor_table.load()` selected sheets with `schema == "compass-run/1"` and nothing
else. That was sufficient for as long as `run_compass.py` only ever administered
the 62 external propositions.

It stopped being sufficient when the project authored its own instrument.
`data/ratchet-propositions-i3.json` is 60 items in 30 mirrored pairs, and it is
administered by the SAME runner, written with the SAME schema, into the SAME
tree. Pooled, the two produce a side-flip count over 62 items averaged with one
over 60, on different propositions in different topic space -- a number that
describes neither instrument.

Nothing would have announced it. The cell key is (model, condition,
shuffle_seed); `n_items` is not in it, the schema matches, `valid` is true, and
the sheets parse. The first visible symptom would have been the published pair
counts moving -- 84 and 97 -- which CI asserts as a replication test. It would
have failed as a REPLICATION defect rather than as the pooling defect it is, and
been debugged in the wrong place.

The discriminator was already in the records: `instrument` is written straight
from the bank's own field (`run_compass.py:719`).
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import floor_table as F  # noqa: E402


COMPASS = "politicalcompass.org 62-proposition test; texts and per-item research classifications"
I3 = "ratchet-battery-i3"


def _sheet(instrument, n_items, model="vendor/model", seed=11):
    """A sheet that passes every OTHER filter in load(), so only the guard can reject it."""
    return {
        "schema": "compass-run/1",
        "instrument": instrument,
        "n_items": n_items,
        "model": model,
        "condition": "A",
        "template": "T01",
        "temperature": 0.7,
        "seed": 20260830,
        "shuffle_seed": seed,
        "valid": True,
        "channel": "openrouter",
        "collected_at": "2026-09-16T00:00:00+00:00",
        # Not degenerate: load() drops a sheet whose answers are all one value.
        # `q` is the item key the loader reads; `load()` returns {q: position}.
        "answers": [{"q": i + 1, "position": i % 4} for i in range(n_items)],
    }


def _plant(tmp_path, sheets):
    run = tmp_path / "runs" / "planted"
    run.mkdir(parents=True)
    with io.open(str(run / "vendor_model.jsonl"), "w", encoding="utf-8", newline="\n") as fh:
        for s in sheets:
            fh.write(json.dumps(s) + "\n")
    return tmp_path


def _load_from(tmp_path, instrument):
    """Run load() against a planted tree, with the module's globals restored after."""
    old_study, old_instr = F.STUDY, F._INSTRUMENT
    F.DROPPED.clear()
    F._DROPPED_SEEN.clear()
    try:
        F.STUDY = str(tmp_path)
        F.set_instrument(instrument)
        return F.load("runs/**/*.jsonl")
    finally:
        F.STUDY = old_study
        F.set_instrument(old_instr)
        F.DROPPED.clear()
        F._DROPPED_SEEN.clear()


def test_the_default_instrument_is_the_studys_own_battery(tmp_path):
    """The floors read the instrument this study wrote. Moved 2026-09-16.

    This asserted the external questionnaire, with the reason beside the constant: the
    default moves in the same commit as CI's expected pair counts, so it is one reviewable
    diff rather than a drift nobody chose. That commit is this one.
    """
    assert F.INSTRUMENT_DEFAULT == F.RATCHET_INSTRUMENT
    assert F.INSTRUMENT_ITEMS[F.RATCHET_INSTRUMENT] == 32


def test_a_retired_instrument_is_reachable_only_by_asking_for_it(tmp_path):
    """Retired, not forgotten — but nothing reaches it by omission.

    Both retired banks keep an entry in INSTRUMENT_ITEMS so their archived records can
    still be loaded deliberately for provenance. Neither is the default.
    """
    assert F.INSTRUMENT_DEFAULT not in (F.COMPASS_INSTRUMENT, F.I3_INSTRUMENT)
    assert F.COMPASS_INSTRUMENT in F.INSTRUMENT_ITEMS
    assert F.I3_INSTRUMENT in F.INSTRUMENT_ITEMS


def test_an_i3_sheet_is_not_loaded_into_a_compass_floor(tmp_path):
    """The defect this file exists for: same schema, same tree, different instrument."""
    _plant(tmp_path, [_sheet(COMPASS, 62, seed=11), _sheet(I3, 60, seed=22)])
    cells = _load_from(tmp_path, F.COMPASS_INSTRUMENT)
    sheets = [sheet for runs in cells.values() for sheet in runs]
    assert len(sheets) == 1
    assert len(sheets[0]) == 62, "loaded the 60-item bank into a 62-item floor"


def test_the_exclusion_is_counted_not_silent(tmp_path):
    """A pair count that moves must say why in the same breath as the number."""
    _plant(tmp_path, [_sheet(COMPASS, 62, seed=11), _sheet(I3, 60, seed=22)])
    old_study, old_instr = F.STUDY, F._INSTRUMENT
    F.DROPPED.clear()
    F._DROPPED_SEEN.clear()
    try:
        F.STUDY = str(tmp_path)
        F.set_instrument(F.COMPASS_INSTRUMENT)
        F.load("runs/**/*.jsonl")
        reasons = dict(F.load_report())
    finally:
        F.STUDY = old_study
        F.set_instrument(old_instr)
        F.DROPPED.clear()
        F._DROPPED_SEEN.clear()
    assert any("other instrument" in k for k in reasons), reasons


def test_selecting_i3_excludes_the_compass(tmp_path):
    """The guard runs both ways, or it is a filter for one corpus rather than a rule."""
    _plant(tmp_path, [_sheet(COMPASS, 62, seed=11), _sheet(I3, 60, seed=22)])
    cells = _load_from(tmp_path, F.I3_INSTRUMENT)
    sheets = [sheet for runs in cells.values() for sheet in runs]
    assert len(sheets) == 1
    assert len(sheets[0]) == 60, "loaded the compass into an I3 floor"


def test_a_sheet_with_no_instrument_field_falls_back_to_its_item_count(tmp_path):
    """Not every collector writes the field, and failing closed deleted a published row.

    This asserted the opposite -- that an unnamed sheet is dropped -- on the
    belief that every sheet carries the field. It does not.
    `constrained_probe.py`, the grammar arm, writes `compass-run/1` records with
    no `instrument` key: 50 records, 5 models, every one `n_items: 62`, and its
    own docstring says it administers the same items with the parser removed.

    Failing closed on those silently removed the whole elicitation-format row
    from the generated floors table -- a row that exists to publish a
    DISQUALIFICATION ("ARM UNSTABLE, NOT A FLOOR"). Deleting a negative result is
    not the safe direction of error.

    Name wins; item count is the fallback when there is no name.
    """
    s = _sheet(COMPASS, 62)
    del s["instrument"]
    _plant(tmp_path, [s])
    cells = _load_from(tmp_path, F.COMPASS_INSTRUMENT)
    sheets = [sheet for runs in cells.values() for sheet in runs]
    assert len(sheets) == 1 and len(sheets[0]) == 62


def test_the_item_count_fallback_applies_only_where_the_field_predates_it(tmp_path):
    """The fallback is narrower than it looks, and narrower than it was.

    It ran for every instrument, which made item count an identity: a sheet carrying no
    instrument name was claimed by whichever bank had that many items. That is a guess
    dressed as a match, and with three banks in the tree it is a guess that can be wrong.

    Only the external questionnaire predates the `instrument` field, so only it may be
    recognised by count. The derived bank and this study's battery have both written the
    field on every sheet they ever produced; for them an absent field means the record is
    from something else, and it is dropped.
    """
    a, b = _sheet(COMPASS, 62, seed=11), _sheet(I3, 60, seed=22)
    del a["instrument"]
    del b["instrument"]
    _plant(tmp_path, [a, b])

    cells = _load_from(tmp_path, F.COMPASS_INSTRUMENT)
    sheets = [sheet for runs in cells.values() for sheet in runs]
    assert len(sheets) == 1 and len(sheets[0]) == 62, "the legacy instrument still falls back"

    cells = _load_from(tmp_path, F.I3_INSTRUMENT)
    assert not [s for runs in cells.values() for s in runs], (
        "a 60-item sheet with no instrument field was claimed for a bank that has always "
        "written one")


def test_a_sheet_matching_neither_a_name_nor_a_count_is_still_dropped(tmp_path):
    """The fallback is a fallback, not an amnesty."""
    s = _sheet(COMPASS, 40)
    del s["instrument"]
    _plant(tmp_path, [s])
    cells = _load_from(tmp_path, F.COMPASS_INSTRUMENT)
    assert not [sheet for runs in cells.values() for sheet in runs]


def test_matching_is_exact_and_case_insensitive():
    """The discriminator is an identity, not a substring.

    It WAS a substring: `_INSTRUMENT.lower() in got.lower()`. The two banks in this tree
    are `ratchet-battery-i3` and `ratchet-battery` -- **one character apart, inside an
    `in` test**, deciding which instrument a published floor is computed from. Names built
    to be confusable, matched by a rule that cannot tell them apart reliably.

    Case and trailing description still fold, because a record's descriptive tail has
    changed before and must not change which instrument it belongs to.
    """
    assert F._instrument_matches({"instrument": "ratchet-battery"}) is True
    assert F._instrument_matches({"instrument": "Ratchet-Battery-V3, 32 items"}) is True
    assert F._instrument_matches({"instrument": "ratchet-battery; authored"}) is True
    assert F._instrument_matches({"instrument": I3}) is False
    assert F._instrument_matches({"instrument": COMPASS}) is False
    assert F._instrument_matches({"instrument": None}) is False
    assert F._instrument_matches({}) is False


def test_a_confusably_named_bank_cannot_take_this_ones_floors():
    """A prefix is not an identity, and the specific alias beats the family.

    Three versions of this got it wrong in the same direction. A bare `startswith` matched
    a bank named one digit longer. A family alias claimed every bank beginning with it,
    including the withdrawn one. And after the bank was renamed, `ratchet-battery` became a
    prefix of `ratchet-battery-i3` — so the canonical id would have claimed the withdrawn
    bank's records, held off by nothing but the order the aliases happened to be declared
    in. Longest prefix wins now, so declaration order cannot decide it.
    """
    # Near-misses: same stem, different bank.
    for near in ("ratchet-battery0", "ratchet-batteryx", "ratchet-battery-i3"):
        assert F._instrument_matches({"instrument": near}) is False, near
    # The canonical id and the id the first 167 sheets were collected under both resolve.
    for ours in ("ratchet-battery", "ratchet-battery-v3"):
        assert F._instrument_matches({"instrument": ours}) is True, ours


def test_declaration_order_cannot_change_which_bank_a_record_belongs_to():
    """The specific alias must beat the family whatever order the dict is written in."""
    import collections
    original = F.INSTRUMENT_ALIASES
    try:
        F.INSTRUMENT_ALIASES = collections.OrderedDict(
            reversed(list(original.items())))
        assert F._instrument_matches({"instrument": "ratchet-battery-i3"}) is False
        assert F._instrument_matches({"instrument": "ratchet-battery"}) is True
    finally:
        F.INSTRUMENT_ALIASES = original


def test_a_record_with_no_instrument_field_is_not_claimed_by_item_count():
    """The fallback is for instruments that PREDATE the field, and this one does not.

    It was an unconditional item-count match, so any 32-item sheet carrying no instrument
    name was counted into this study's battery -- including, in principle, a different
    32-item bank entirely. The tree already holds 59 no-instrument records at 62 items
    from the constrained-decoding arm, claimed by exactly this route under the old default.
    """
    assert F.INSTRUMENT_DEFAULT not in F.PREDATES_INSTRUMENT_FIELD
    assert F._instrument_matches({"n_items": 32}) is False
    assert F._instrument_matches({"n_items": 62}) is False
