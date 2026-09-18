"""Two instruments can share one schema, one runner and one tree. Never pool them.

WHY THIS FILE EXISTS
--------------------
`floor_table.load()` selected sheets by `schema == "compass-run/1"` and nothing else. That was
sufficient while one bank was ever administered. It stopped being sufficient the moment a
second existed: the same runner, the same schema, the same directory, and a floor computed
over a mixture of two instruments describes neither.

Nothing would have announced it. The cell key is (model, condition, shuffle_seed); `n_items`
is not in it, the schema matches, `valid` is true, and the sheets parse. The first symptom
would have been published pair counts moving, which CI asserts as a replication test — so it
would have failed as a REPLICATION defect and been debugged in the wrong place.

SYNTHETIC NAMES, 2026-09-17. This file used to plant sheets carrying the real names of the two
retired banks, which meant the strings lived on in the test suite after the banks, their
records and their code had all been withdrawn. They are gone; the rule is not. The hazard the
rule guards is also better represented by a synthetic sibling than by a retired bank: the live
danger is a FUTURE bank named `ratchet-battery-<something>`, one character from the live one,
inside a match that was for months a substring test.
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import floor_table as F  # noqa: E402


#: A different instrument entirely, with the descriptive tail a record may carry.
OTHER = "other-bank/2 40-proposition set; texts and per-item classifications"

#: THE DANGEROUS ONE. A bank in the live instrument's own family, one token longer. Under the
#: substring match this file was written against, `ratchet-battery` matched this and claimed
#: its sheets for the live floors.
SIBLING = "ratchet-battery-x9"


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


def test_the_default_instrument_is_the_studys_own_battery():
    assert F.INSTRUMENT_DEFAULT == F.RATCHET_INSTRUMENT
    assert F.INSTRUMENT_ITEMS[F.RATCHET_INSTRUMENT] == 32


def test_only_the_live_instrument_is_registered():
    """Retired banks keep no entry here, because nothing under runs/ carries their name.

    They had one so archived records could still be loaded deliberately for provenance. Those
    records are all in `withdrawn/`, out of every `runs/**` glob, and a registry entry for a
    bank no live record names is a name kept alive for nothing -- which is how one of them
    stayed the printed DEFAULT in this module's own `--instrument` help long after it was not.

    THE RULE IS "LIVE OR PLANNED", NOT "EXACTLY ONE". `ratchet-factions` was added 2026-09-17
    before it had collected a single sheet, deliberately: declaring a name before any record
    carries it is the only moment at which the declaration cannot be wrong about the corpus.
    The battery's own records were pooled across two names for a day before anyone checked.
    """
    assert list(F.INSTRUMENT_ITEMS) == [F.RATCHET_INSTRUMENT], (
        "the item-count fallback is for banks that predate the `instrument` field; the "
        "factions bank postdates it and must never be identifiable by item count -- it has "
        "32 items, exactly like the battery")
    assert set(F.INSTRUMENT_ALIASES) == {F.RATCHET_INSTRUMENT, F.FACTIONS_INSTRUMENT}
    for canon, names in F.INSTRUMENT_ALIASES.items():
        assert canon in names, "%s does not alias its own name" % canon
        assert "compass" not in " ".join(names).lower(), "a retired bank crept back in"


def test_a_foreign_sheet_is_not_loaded_into_this_instruments_floor(tmp_path):
    """The defect this file exists for: same schema, same tree, different instrument."""
    _plant(tmp_path, [_sheet(F.RATCHET_INSTRUMENT, 32, seed=11), _sheet(OTHER, 40, seed=22)])
    cells = _load_from(tmp_path, F.RATCHET_INSTRUMENT)
    sheets = [sheet for runs in cells.values() for sheet in runs]
    assert len(sheets) == 1
    assert len(sheets[0]) == 32, "loaded a 40-item bank into a 32-item floor"


def test_the_guard_runs_both_ways(tmp_path):
    """Or it is a filter for one corpus rather than a rule."""
    _plant(tmp_path, [_sheet(F.RATCHET_INSTRUMENT, 32, seed=11), _sheet(OTHER, 40, seed=22)])
    cells = _load_from(tmp_path, OTHER)
    sheets = [sheet for runs in cells.values() for sheet in runs]
    assert len(sheets) == 1
    assert len(sheets[0]) == 40, "loaded this study's battery into a foreign floor"


def test_the_exclusion_is_counted_not_silent(tmp_path):
    """A pair count that moves must say why in the same breath as the number."""
    _plant(tmp_path, [_sheet(F.RATCHET_INSTRUMENT, 32, seed=11), _sheet(OTHER, 40, seed=22)])
    old_study, old_instr = F.STUDY, F._INSTRUMENT
    F.DROPPED.clear()
    F._DROPPED_SEEN.clear()
    try:
        F.STUDY = str(tmp_path)
        F.set_instrument(F.RATCHET_INSTRUMENT)
        F.load("runs/**/*.jsonl")
        reasons = dict(F.load_report())
    finally:
        F.STUDY = old_study
        F.set_instrument(old_instr)
        F.DROPPED.clear()
        F._DROPPED_SEEN.clear()
    assert any("other instrument" in k for k in reasons), reasons


def test_a_sheet_with_no_instrument_field_is_dropped(tmp_path):
    """Item count is no longer an identity for anything, and that is deliberate.

    The fallback existed for one collector that wrote no `instrument` key: 59 records at 62
    items, from an arm on a bank now retired. Failing closed on those once deleted a published
    DISQUALIFICATION row from the floors table, which is not the safe direction of error, so
    the fallback was kept and narrowed to instruments that predate the field.

    On 2026-09-17 those three run directories moved to `withdrawn/` with the bank, and
    `PREDATES_INSTRUMENT_FIELD` is empty. Every record under `runs/` names its instrument, so
    an unnamed sheet is now from something else and is dropped. Item count is a guess dressed
    as a match, and with no legacy corpus left there is nothing to guess for.
    """
    assert F.PREDATES_INSTRUMENT_FIELD == ()
    s = _sheet(F.RATCHET_INSTRUMENT, 32)
    del s["instrument"]
    _plant(tmp_path, [s])
    cells = _load_from(tmp_path, F.RATCHET_INSTRUMENT)
    assert not [sheet for runs in cells.values() for sheet in runs], (
        "a sheet naming no instrument was claimed by item count")


def test_matching_is_exact_and_case_insensitive():
    """The discriminator is an identity, not a substring.

    It WAS a substring -- `_INSTRUMENT.lower() in got.lower()` -- and two banks one character
    apart decided which instrument a published floor was computed from. Case and a descriptive
    tail still fold, because a record's tail has been edited before and must not change which
    instrument it belongs to.
    """
    assert F._instrument_matches({"instrument": "ratchet-battery"}) is True
    assert F._instrument_matches({"instrument": "Ratchet-Battery-V3, 32 items"}) is True
    assert F._instrument_matches({"instrument": "ratchet-battery; authored"}) is True
    assert F._instrument_matches({"instrument": OTHER}) is False
    assert F._instrument_matches({"instrument": None}) is False
    assert F._instrument_matches({}) is False


def test_a_confusably_named_sibling_cannot_take_this_ones_floors(tmp_path):
    """A family prefix is not an identity.

    `ratchet-battery` is a prefix of every future `ratchet-battery-*`. Under the old substring
    rule such a bank's sheets loaded straight into this instrument's floors. The match is
    anchored at the head AND requires a boundary, so a longer name in the same family is a
    different instrument -- which is what it is.
    """
    assert F._instrument_matches({"instrument": SIBLING}) is False
    _plant(tmp_path, [_sheet(F.RATCHET_INSTRUMENT, 32, seed=11), _sheet(SIBLING, 36, seed=22)])
    cells = _load_from(tmp_path, F.RATCHET_INSTRUMENT)
    sheets = [sheet for runs in cells.values() for sheet in runs]
    assert len(sheets) == 1 and len(sheets[0]) == 32, (
        "a bank in this instrument's own name family was pooled into its floors")
