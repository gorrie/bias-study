"""A mirrored instrument must never present a pair's two halves side by side.

WHY THIS FILE EXISTS
--------------------
The I3 bank guarantees that each pair's halves differ by exactly one inserted
"not". That guarantee is what makes "agreed with both" a contradiction rather
than a judgement call -- and it is also what makes ADJACENCY dangerous. Printed
next to each other, item 14 and item 15 are visibly a proposition and its
negation, so answering them consistently costs the model nothing, and the frame
gap then measures whether it noticed the pair rather than what it holds.

ITEM-AUDIT-2026-09-14 recorded the old bank doing exactly this: every pair
adjacent, critic half always first, so the critic frame also took the primacy
slot on all sixteen pairs.

`order_items` shuffled plainly, which leaves a given pair adjacent about 3% of
the time. Over 30 pairs that is roughly a 60% chance of at least one adjacent
pair per run -- not a rare event, and silent when it happens.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import run_battery as RC  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#: THE LIVE BANK. This named the withdrawn i3 bank, which left data/ on 2026-09-17 -- so this
#: file's guarantee (a mirrored pair is never presented adjacent) was being asserted about an
#: instrument nothing administers, and not about the one 472 sheets were collected on.
BANK = os.path.join(ROOT, "data", "ratchet-battery.json")


def bank_items():
    with open(BANK, encoding="utf-8") as fh:
        return json.load(fh)["items"]


def test_mirror_halves_are_never_adjacent_across_many_seeds():
    items = bank_items()
    mirror = {it["id"]: it["mirror_of"] for it in items}
    for seed in range(60):
        order = RC.order_items(items, shuffle_seed=seed)
        pos = {it["id"]: p for p, it in enumerate(order)}
        for i in mirror:
            gap = abs(pos[i] - pos[mirror[i]])
            assert gap >= RC.MIRROR_MIN_SEPARATION, (
                "seed %d placed the halves of a pair %d apart" % (seed, gap))


def test_a_plain_shuffle_really_would_have_placed_pairs_adjacent():
    """The negative control: without the constraint the defect is common.

    If this ever stops finding adjacency, the test above is passing for a reason
    other than the constraint, and it has stopped checking anything.
    """
    import random
    items = bank_items()
    mirror = {it["id"]: it["mirror_of"] for it in items}
    runs_with_adjacency = 0
    for seed in range(60):
        shuffled = list(items)
        random.Random(seed).shuffle(shuffled)
        pos = {it["id"]: p for p, it in enumerate(shuffled)}
        if any(abs(pos[i] - pos[mirror[i]]) == 1 for i in mirror):
            runs_with_adjacency += 1
    assert runs_with_adjacency > 10, (
        "a plain shuffle produced adjacency in only %d of 60 runs; the constraint "
        "would then be guarding nothing" % runs_with_adjacency)


def test_order_is_deterministic_in_the_seed():
    items = bank_items()
    a = [it["id"] for it in RC.order_items(items, shuffle_seed=11)]
    b = [it["id"] for it in RC.order_items(items, shuffle_seed=11)]
    assert a == b


def test_different_seeds_give_different_orders():
    items = bank_items()
    a = [it["id"] for it in RC.order_items(items, shuffle_seed=1)]
    b = [it["id"] for it in RC.order_items(items, shuffle_seed=2)]
    assert a != b


def test_no_seed_means_no_reordering():
    items = bank_items()
    assert [it["id"] for it in RC.order_items(items)] == [it["id"] for it in items]


def test_every_item_survives_the_constrained_shuffle():
    """A constraint that drops or duplicates an item would be worse than the defect."""
    items = bank_items()
    order = RC.order_items(items, shuffle_seed=3)
    assert len(order) == len(items)
    assert sorted(it["id"] for it in order) == sorted(it["id"] for it in items)


def test_an_unmirrored_instrument_still_shuffles_plainly():
    """The 62-item external compass has no mirror_of and must be unaffected."""
    items = [{"id": i, "text": "Item %d." % i} for i in range(1, 63)]
    order = RC.order_items(items, shuffle_seed=5)
    assert len(order) == 62
    assert [it["id"] for it in order] != [it["id"] for it in items]


def test_the_prompt_built_from_the_bank_never_adjoins_a_pair():
    """The gate that matters is on the text actually sent, not on a helper."""
    items = bank_items()
    by_id = {it["id"]: it for it in items}
    for seed in (0, 1, 2, 7, 42):
        messages = RC.build_prompt(items, condition="A", shuffle_seed=seed)
        user = [m for m in messages if m["role"] == "user"][0]["content"]
        ids = [int(line.split(".", 1)[0]) for line in user.split("\n")
               if line[:1].isdigit() and ". " in line]
        # DERIVED FROM THE BANK, not typed. This asserted 60 -- the withdrawn i3 bank's count
        # -- so repointing the constant at the live 32-item battery turned a structural test
        # into a failing item-count test about an instrument that no longer exists.
        assert len(ids) == len(items), ("prompt carried %d items, bank holds %d"
                                        % (len(ids), len(items)))
        pos = {i: p for p, i in enumerate(ids)}
        for i in ids:
            assert abs(pos[i] - pos[by_id[i]["mirror_of"]]) >= RC.MIRROR_MIN_SEPARATION


def _dry_run_ids(capsys, *extra):
    argv = ["--items", BANK, "--model", "x-ai/grok-4.3", "--condition", "A", "--dry-run"]
    RC.main(list(argv) + list(extra))
    out = capsys.readouterr().out
    return [int(line.split(".", 1)[0]) for line in out.split("\n")
            if line[:1].isdigit() and ". " in line], out


def test_dry_run_shows_the_prompt_that_would_actually_be_sent(capsys):
    """--dry-run dropped --shuffle-seed until 2026-09-14.

    It printed items in id order while the collection that followed sent them
    shuffled. A preview that disagrees with what will be sent is worse than none:
    it is the step taken BECAUSE money is about to be spent. On this bank it
    showed every mirror pair adjacent -- the single arrangement the instrument is
    built to avoid.
    """
    items = bank_items()
    by_id = {it["id"]: it for it in items}

    ids, out = _dry_run_ids(capsys, "--shuffle-seed", "1")
    # EVERY ITEM, not "at least ten". The old bound was 10 against a 60-item bank, so a
    # preview truncated to 1,500 characters -- which is what it was -- passed while showing a
    # sixth of the prompt. The preview's whole job is to be the prompt.
    assert len(ids) == len(items), ("dry-run rendered %d of %d items; a truncated preview is "
                                    "the defect this file exists for" % (len(ids), len(items)))
    assert ids != sorted(ids), "dry-run ignored --shuffle-seed and printed id order"
    assert "seed 1" in out, "dry-run does not say how items were ordered"

    pos = {i: p for p, i in enumerate(ids)}
    shown = [i for i in ids if by_id[i]["mirror_of"] in pos]
    for i in shown:
        gap = abs(pos[i] - pos[by_id[i]["mirror_of"]])
        assert gap >= RC.MIRROR_MIN_SEPARATION, "dry-run showed a pair %d apart" % gap


def test_dry_run_without_a_seed_says_so(capsys):
    """Silence about ordering is how the mismatch went unnoticed."""
    ids, out = _dry_run_ids(capsys)
    assert ids == sorted(ids)
    assert "id order" in out


def test_the_runner_raises_rather_than_collecting_an_impossible_order():
    """Too small an instrument must fail loudly, not silently drop the constraint."""
    tiny = [{"id": 1, "mirror_of": 2, "text": "A."}, {"id": 2, "mirror_of": 1, "text": "B."}]
    try:
        RC.order_items(tiny, shuffle_seed=1)
    except RuntimeError as exc:
        assert "adjacent halves" in str(exc)
    else:
        raise AssertionError("order_items silently returned an unconstrained order")
