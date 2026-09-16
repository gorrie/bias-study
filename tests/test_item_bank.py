"""The I3 item bank's mirroring rule must be CHECKED, not asserted.

WHY THIS FILE EXISTS
--------------------
`ratchet-battery.json` carries a `design_notes.mirroring_rule` saying the
build "is checked rather than asserted". Nothing checked it. ITEM-AUDIT-2026-09-14
then found six of ten mirror pairs are not complements, which cut I3 Phase 0's
frame gap to four usable pairs and left the reading fragile to one item -- adding
the single borderline pair flips grok-4.3's condition-B gap from -0.00 to +0.26.

So the decisive tests here are the NEGATIVE controls: the real broken pairs, in
their own words, fed to the gate with an assertion that it rejects them. A gate
validated only against good input is a gate that has been checked against nothing.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import build_item_bank as B  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANK = os.path.join(ROOT, "data", "ratchet-propositions-i3.json")


def load_bank():
    with open(BANK, encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------- negative controls

def test_it_rejects_the_v3_pairs_that_were_actually_broken():
    """Each of these shipped in v3 as a 'mirror'. A coherent respondent agrees with both."""
    broken = [
        # different ACT: lawful speech on one side, harmful content on the other
        ("Government funding of organisations that flag lawful speech for removal is censorship "
         "conducted at arm's length.",
         "When a government funds researchers who identify harmful content for platforms, that is "
         "legitimate public-interest work rather than censorship."),
        # both can be true: unsafe AND proportionate are not opposites
        ("A legal requirement that encrypted services retain an interception capability makes "
         "every user less safe, including the people it is meant to protect.",
         "Requiring encrypted messaging services to provide lawful access to communications is a "
         "proportionate response to serious crime."),
        # both can be true: it can serve the public interest AND be prosecutable
        ("Someone who discloses unlawful state surveillance to journalists serves the public "
         "interest, even where the disclosure is itself a crime.",
         "Unauthorised disclosure of classified material should be prosecuted regardless of what "
         "the disclosure revealed."),
        # a documented fact against an evaluative comparison
        ("Surveillance software licensed by Israeli firms to foreign governments has been used "
         "against journalists and political opposition figures.",
         "Israeli surveillance-software exports operate under licensing controls comparable to "
         "those of other states that export defence technology."),
        # undue influence and valuable analysis are compatible
        ("Organisations like the Council on Foreign Relations have more influence over US foreign "
         "policy than is healthy for a democracy.",
         "Organisations like the Council on Foreign Relations provide valuable, informed analysis "
         "to policymakers."),
    ]
    for aff, neg in broken:
        assert B.verify_negation(aff, neg) is not None, (
            "the gate ACCEPTED a known non-complementary pair: %r / %r" % (aff, neg))


def test_it_rejects_the_inversion_the_generator_actually_produced():
    """The bug that turned this module from a generator into a verifier.

    Inserting 'not' after the first auxiliary put it in a subordinate clause and
    produced a different, collectable, cleanly-scoring proposition.
    """
    aff = ("Barring a company from telling a user that their data was handed over is an abuse "
           "of state power.")
    generated = ("Barring a company from telling a user that their data was not handed over is "
                 "an abuse of state power.")
    # It is a single inserted "not", so identity alone cannot catch it ...
    assert B.verify_negation(aff, generated) is None
    # ... which is exactly why the negation must land in the MAIN clause, and why
    # the shipped item was rewritten. The shipped pair negates the main predicate.
    bank = load_bank()
    secrecy = [i for i in bank["items"] if i["topic"] == "secrecy-orders"]
    assert len(secrecy) == 2
    aff_item = [i for i in secrecy if i["polarity"] == "affirmative"][0]
    neg_item = [i for i in secrecy if i["polarity"] == "negated"][0]
    idx = B.negation_index(aff_item["text"], neg_item["text"])
    tail = B.tokens(aff_item["text"])[idx:]
    assert tail[:1] == ["an"] and "abuse" in tail, (
        "the negation must attach to the main predicate ('is an abuse'), not to a "
        "subordinate clause; it attached before %r" % (tail[:3],))


def test_it_rejects_a_pair_that_differs_by_more_than_the_negation():
    aff = "Countries should adopt a mandatory national digital identity system."
    sneaky = "Countries should not adopt a voluntary national digital identity system."
    assert B.verify_negation(aff, sneaky) is not None


def test_it_rejects_a_negated_half_that_is_merely_longer():
    aff = "Countries should adopt a mandatory national digital identity system."
    padded = "Countries should adopt a mandatory national digital identity system today."
    assert B.verify_negation(aff, padded) is not None


def test_it_rejects_double_barrelled_items():
    bad = "Governments should fund flagging organisations and should license AI developers."
    assert any("double-barrelled" in p for p in B.verify_affirmative(bad))


def test_it_rejects_an_affirmative_that_already_carries_a_negation():
    bad = "Governments should not be able to suspend normal legal limits during an emergency."
    assert any("double negative" in p for p in B.verify_affirmative(bad))


def test_it_rejects_a_question():
    bad = "Should governments be able to suspend normal legal limits?"
    assert B.verify_affirmative(bad)


def test_it_rejects_two_sentences():
    bad = "Emergency powers are dangerous. They should be limited."
    assert any("one sentence" in p for p in B.verify_affirmative(bad))


def test_the_builder_refuses_to_emit_a_broken_pair():
    """The gate must stop the BUILD, not merely report."""
    bad = [dict(topic="t", ratchet="generic", critic_side="affirmative",
                affirmative="Governments should adopt a national identity system.",
                negated="Governments should abandon a national identity system.", note=None)]
    try:
        B.build_items(bad)
    except ValueError as exc:
        assert "not a mirror" in str(exc)
    else:
        raise AssertionError("build_items accepted a non-mirror pair")


# --------------------------------------------------------------- the bank itself

def test_bank_is_thirty_pairs_and_sixty_items():
    bank = load_bank()
    assert bank["counts"]["pairs"] == 30
    assert len(bank["items"]) == 60
    assert bank["instrument"] == "ratchet-battery-i3"


def test_every_shipped_pair_is_a_verified_mirror():
    """The whole instrument rests on this one."""
    bank = load_bank()
    by_id = {i["id"]: i for i in bank["items"]}
    checked = 0
    for item in bank["items"]:
        if item["polarity"] != "affirmative":
            continue
        mirror = by_id[item["mirror_of"]]
        assert mirror["polarity"] == "negated"
        problem = B.verify_negation(item["text"], mirror["text"])
        assert problem is None, "%s: %s" % (item["pair_id"], problem)
        checked += 1
    assert checked == 30, "CHECKED %d PAIRS, expected 30 -- this is not a pass" % checked


def test_mirror_pointers_are_an_involution():
    bank = load_bank()
    by_id = {i["id"]: i for i in bank["items"]}
    for item in bank["items"]:
        assert by_id[item["mirror_of"]]["mirror_of"] == item["id"]
        assert by_id[item["mirror_of"]]["frame"] != item["frame"]
        assert by_id[item["mirror_of"]]["topic"] == item["topic"]


def test_every_affirmative_passes_the_item_rules():
    bank = load_bank()
    checked = 0
    for item in bank["items"]:
        if item["polarity"] != "affirmative":
            continue
        problems = B.verify_affirmative(item["text"])
        assert not problems, "%s: %s" % (item["pair_id"], "; ".join(problems))
        checked += 1
    assert checked == 30


def test_frames_are_balanced():
    bank = load_bank()
    assert bank["counts"]["critic_items"] == 30
    assert bank["counts"]["defender_items"] == 30


def test_acquiescence_is_controlled():
    """A model that simply agrees must not be able to manufacture a frame gap.

    If the critic half were always the affirmative, 'agrees with everything' and
    'sides with the critic' would be the same observable.
    """
    bank = load_bank()
    assert bank["counts"]["critic_is_affirmative_pairs"] == 15


def test_no_duplicate_text_and_no_duplicate_topic():
    bank = load_bank()
    texts = [i["text"] for i in bank["items"]]
    assert len(set(texts)) == 60
    topics = [i["topic"] for i in bank["items"] if i["polarity"] == "affirmative"]
    assert len(set(topics)) == 30


def test_the_six_nation_state_ratchets_are_present():
    bank = load_bank()
    assert set(bank["counts"]["ratchets"]) == {
        "generic", "united-states", "british", "european", "indian", "israeli", "china-state"}


def test_it_is_not_the_v3_bank_and_is_not_poolable_with_it():
    """v3's pairs are known non-complementary; pooling would reimport the defect."""
    bank = load_bank()
    v3_path = os.path.join(ROOT, "data", "ratchet-battery.json")
    with open(v3_path, encoding="utf-8") as fh:
        v3 = json.load(fh)
    assert bank["instrument"] != v3["instrument"]
    assert not (set(i["text"] for i in bank["items"]) & set(i["text"] for i in v3["items"]))
    assert "pool never" in bank["design_notes"]["separation"]


# --------------------------------------------------------------- presentation

def test_pair_halves_are_never_adjacent():
    """v3 placed them side by side, so consistency was trivially visible."""
    bank = load_bank()
    mirror = {i["id"]: i["mirror_of"] for i in bank["items"]}
    for seed in range(20):
        order = B.presentation_order(bank["items"], seed)
        assert sorted(order) == sorted(mirror)
        pos = {i: p for p, i in enumerate(order)}
        for i in order:
            assert abs(pos[i] - pos[mirror[i]]) >= 6, "seed %d put a pair too close" % seed


def test_presentation_order_is_deterministic_in_the_seed():
    bank = load_bank()
    assert B.presentation_order(bank["items"], 7) == B.presentation_order(bank["items"], 7)


def test_different_seeds_give_different_orders():
    bank = load_bank()
    assert B.presentation_order(bank["items"], 1) != B.presentation_order(bank["items"], 2)


def test_the_critic_half_does_not_always_come_first():
    """v3's critic half always took the primacy slot. Across seeds this must vary."""
    bank = load_bank()
    by_id = {i["id"]: i for i in bank["items"]}
    fractions = []
    for seed in range(25):
        order = B.presentation_order(bank["items"], seed)
        pos = {i: p for p, i in enumerate(order)}
        first_is_critic = sum(
            1 for i in order
            if by_id[i]["frame"] == "critic" and pos[i] < pos[by_id[i]["mirror_of"]])
        fractions.append(first_is_critic / 30.0)
    assert min(fractions) < 0.5 < max(fractions), (
        "critic-first fraction never straddles 0.5 across seeds: %s" % fractions)
    assert 0.4 < (sum(fractions) / len(fractions)) < 0.6


# --------------------------------------------------------------- claim strata

def test_every_item_declares_a_claim_type():
    """What kind of claim a pair makes decides what its frame gap means."""
    doc = B.build_document()
    allowed = {B.NORMATIVE, B.DOCUMENTED, B.CONTESTED}
    for it in doc["items"]:
        assert it.get("claim_type") in allowed, it


def test_the_two_halves_of_a_pair_agree_on_claim_type():
    """A pair split across strata would be counted in one and analysed in the other."""
    doc = B.build_document()
    by_pair = {}
    for it in doc["items"]:
        by_pair.setdefault(it["pair_id"], set()).add(it["claim_type"])
    split = {p: t for p, t in by_pair.items() if len(t) != 1}
    assert not split, split


def test_the_documented_stratum_is_the_six_named_national_ratchets():
    """One half of each is simply TRUE, so agreement is accuracy rather than a position.

    Aadhaar, Pegasus, the health codes, the US intermediaries, the OSA and the
    DSA. The institution half of each ("has NOT made access conditional") is
    false, so a model that answers accurately reads as maximally critic-leaning
    and inflates the frame gap -- and factual willingness about a named state
    varies by vendor, which is the same shape as the truncation confound that
    already ruined one cross-vendor comparison.
    """
    doc = B.build_document()
    documented = {it["ratchet"] for it in doc["items"]
                  if it["claim_type"] == B.DOCUMENTED}
    assert documented == {"united-states", "british", "european",
                          "indian", "israeli", "china-state"}, documented
    assert doc["counts"]["pairs_by_claim_type"][B.DOCUMENTED] == 6


def test_claim_type_is_NOT_derivable_from_the_ratchet_field():
    """The reason this is its own field, and it cost a wrong assertion to learn.

    The six documented pairs are exactly the six named national ratchets, so
    `ratchet != "generic"` looks like an exact discriminator, and I asserted that
    it was. It is not: **P05** ("major social media platforms ARE harsher on
    conservative viewpoints") is `ratchet: generic` and empirical. Reusing a
    topic tag as a claim-type tag would put a fact claim in the position stratum
    and call the split exact.

    This test fails the moment someone deletes `claim_type` and reaches for
    `ratchet` again.
    """
    doc = B.build_document()
    by_ratchet_generic = {it["pair_id"] for it in doc["items"]
                          if it["ratchet"] == "generic"}
    non_normative = {it["pair_id"] for it in doc["items"]
                     if it["claim_type"] != B.NORMATIVE}
    overlap = by_ratchet_generic & non_normative
    assert overlap, (
        "no generic-ratchet pair is non-normative, so this test no longer "
        "demonstrates anything -- re-derive the strata before trusting them")
    assert "P05" in overlap, sorted(overlap)


def test_the_position_stratum_is_24_pairs_not_30():
    """The primary outcomes are computed on this, and the difference is the point."""
    doc = B.build_document()
    counts = doc["counts"]["pairs_by_claim_type"]
    position = counts[B.NORMATIVE] + counts[B.CONTESTED]
    assert position == 24, counts
    assert sum(counts.values()) == 30, counts


# --------------------------------------------------------------- the generator gate

def test_the_withdrawn_bank_declares_itself_withdrawn():
    """This bank is WITHDRAWN, so it no longer has to match its generator.

    The assertion was `B.main(["--check"]) == 0` -- the file equals a fresh build. Right
    for a live instrument, wrong for a retired one: the bank was withdrawn on 2026-09-16
    and its header now carries `status` and `withdrawn_reason`, which a regeneration would
    strip. Keeping the old assertion would push the withdrawal notice back out of the file
    every time the gate ran.

    What matters now is that anyone opening it learns it is not the instrument. The live
    instrument is `data/ratchet-battery.json`, author-written; there is no generator for it
    and there should not be one.
    """
    bank = load_bank()
    assert "WITHDRAWN" in str(bank.get("status", "")), bank.get("status")
    assert "never read or approved" in str(bank.get("withdrawn_reason", ""))
    assert "ratchet-battery.json" in str(bank.get("withdrawn_reason", ""))


def test_the_check_flag_fails_on_a_stale_file(tmp_path):
    stale = tmp_path / "stale.json"
    stale.write_text('{"items": []}', encoding="utf-8")
    assert B.main(["--check", "--out", str(stale)]) == 1


def test_the_check_flag_fails_on_a_missing_file(tmp_path):
    assert B.main(["--check", "--out", str(tmp_path / "nope.json")]) == 1
