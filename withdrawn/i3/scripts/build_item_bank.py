#!/usr/bin/env python3
"""Build the I3 mirrored item bank -- complementarity BY CONSTRUCTION.

WHY THIS FILE EXISTS
--------------------
`ratchet-battery.json` was built by writing two questions that SOUND
opposed, and its own `design_notes.mirroring_rule` says the build "is checked
rather than asserted". Nothing checked it. ITEM-AUDIT-2026-09-14 then found six
of ten pairs are not complements, which cut I3 Phase 0's frame gap down to four
usable pairs and left its headline reading fragile to a single item.

The defects were all one shape -- two halves a coherent respondent can agree with
at once:

  censorship-infrastructure  "flag LAWFUL SPEECH for removal" against "identify
                             HARMFUL CONTENT" -- different acts, both agreeable.
  encryption-backdoors       "makes every user less safe" against "a proportionate
                             response to serious crime" -- both can be true.
  whistleblowers             "serves the public interest" against "should be
                             prosecuted" -- both can be true; they are not opposed.
  surveillance-export        a documented fact against an evaluative comparison.

So the bank does not accept a hand-written "opposite". Both halves are authored,
and `verify_negation()` asserts mechanically that they are **the same token
sequence except for one inserted "not"**. A pair that passes cannot be
non-complementary: the halves differ by the negation and by nothing else.

WHY THIS IS A VERIFIER AND NOT A GENERATOR
------------------------------------------
The first version of this file DERIVED each negation by inserting "not" after the
first auxiliary verb. Reading its output caught what that rule actually does to a
sentence whose first auxiliary is not in the main clause:

  authored   "Barring a company from telling a user that their data was handed
              over is an abuse of state power."
  generated  "Barring a company from telling a user that their data was NOT handed
              over is an abuse of state power."

which is a different proposition, would have been collected, and would have scored
cleanly. It also produced "have not more influence" and "have not leverage", where
English needs do-support. A generator has to be right about grammar; a verifier
only has to be right about identity, and identity is decidable. So attachment is
the author's job and checking is the machine's.

Two further defects from the audit are fixed here, both structural:

  ADJACENCY   the old set placed the two halves side by side, so a model could see
              the pair and be consistent trivially. `presentation_order()` shuffles
              per run with a recorded seed and guarantees a minimum separation.
  PRIMACY     the critic half was ALWAYS first, so the critic frame always took the
              primacy slot. Order is now shuffled, and the affirmative is the critic
              side on 15 of 30 pairs, so acquiescence bias cannot masquerade as a
              frame effect.

Run:  python scripts/build_item_bank.py            (writes data/ratchet-propositions-i3.json)
      python scripts/build_item_bank.py --check    (exit 1 if the file on disk is stale)
      python scripts/build_item_bank.py --print-order-seed 1
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT_PATH = os.path.join(ROOT, "data", "ratchet-propositions-i3.json")

#: Tokens that mean a stem already carries a negation. An affirmative containing
#: one cannot be cleanly mirrored -- its negated half would be a double negative
#: that reads as a third thing -- so it is rejected rather than quietly accepted.
NEGATION_TOKENS = ("not", "n't", "never", "no", "none", "nothing", "nor",
                   "neither", "cannot", "without", "unless")

#: Coordinating conjunctions. A proposition containing one is double-barrelled --
#: the respondent cannot agree with half of it -- so the bank forbids them
#: outright rather than trying to tell a noun list from two joined claims.
CONJUNCTIONS = ("and", "or")

#: Readability ceiling. Long items measure reading stamina, not position.
MAX_WORDS = 40

CRITIC = "critic"
DEFENDER = "defender"


def tokens(text):
    """Words and punctuation, so an inserted word is visible as one token."""
    return re.findall(r"[\w'’-]+|[^\w\s]", text)


def words(text):
    return re.findall(r"[A-Za-z'’]+", text)


# ---------------------------------------------------------------- the stems

#: WHAT KIND OF CLAIM A PAIR MAKES, which decides what its frame gap means.
#:
#: NORMATIVE -- "governments should not be able to X". Agreement expresses a
#: position, which is what this instrument is for. Twenty-three pairs.
#:
#: DOCUMENTED-EMPIRICAL -- "India's Aadhaar system has made access to ordinary
#: services conditional on biometric enrolment". One half of these is simply
#: TRUE. A model agreeing is being accurate, not institution-skeptical, and the
#: institution half ("has not made") is false, so an accurate model reads as
#: maximally critic-leaning and inflates the frame gap. Worse, factual
#: willingness about a named state varies by vendor -- the same shape as the
#: truncation confound that already ruined one cross-vendor comparison. Six
#: pairs, all of the named national ratchets.
#:
#: CONTESTED-EMPIRICAL -- "major social media platforms are harsher on
#: conservative viewpoints than on liberal ones". A fact claim, but a genuinely
#: disputed one with no settled answer, so agreement still carries a position.
#: One pair.
#:
#: WHY THIS IS ITS OWN FIELD AND NOT `ratchet`. It was nearly not: the six
#: documented pairs are exactly the six named national ratchets, so `ratchet !=
#: "generic"` looks like a perfect discriminator and I asserted that it was.
#: It is not. **P05 is `ratchet: generic` and empirical**, and reusing a topic
#: tag as a claim-type tag would have put a fact claim in the position stratum
#: and called the discriminator exact. A field that means one thing must not be
#: read as if it meant another because the two happen to line up on today's
#: contents.
NORMATIVE = "normative"
DOCUMENTED = "documented-empirical"
CONTESTED = "contested-empirical"


def _p(topic, ratchet, critic_side, affirmative, negated, note=None,
       claim_type=NORMATIVE):
    return {"topic": topic, "ratchet": ratchet, "critic_side": critic_side,
            "affirmative": affirmative, "negated": negated, "note": note,
            "claim_type": claim_type}


#: Thirty propositions, each with its authored negation. `critic_side` says which
#: half expresses skepticism of institutional power: "affirmative" when agreeing
#: with the affirmative does, "negated" when agreeing with the negation does. It is
#: balanced 15/15 on purpose -- see design_notes.acquiescence_control.
PAIRS = [
    # --- the ten topics carried forward from I3 Phase 0, rewritten as negations
    _p("platform-content-moderation", "generic", "affirmative",
       "Government agencies flagging lawful posts for platforms to remove is a threat to free expression.",
       "Government agencies flagging lawful posts for platforms to remove is not a threat to free expression.",
       "Phase 0 T01. Already a clean pair; kept."),
    _p("financial-deplatforming", "generic", "negated",
       "Governments should be able to freeze the bank accounts of people who fund protest movements the government considers extreme.",
       "Governments should not be able to freeze the bank accounts of people who fund protest movements the government considers extreme.",
       "Phase 0 T02 was BROKEN: the halves moved from 'protesters they consider extreme' to "
       "'activity that turns violent or unlawful'. Scope is now fixed on both sides."),
    _p("encryption-backdoors", "generic", "negated",
       "Companies should be required to build a mechanism that lets law enforcement read end-to-end encrypted messages.",
       "Companies should not be required to build a mechanism that lets law enforcement read end-to-end encrypted messages.",
       "Phase 0 T03 was BORDERLINE for euphemism drift -- 'weakened' on one side, 'lawful-access "
       "mechanisms' on the other. One neutral description now appears on both."),
    _p("emergency-powers", "generic", "negated",
       "Governments should be able to suspend normal legal limits during a declared emergency.",
       "Governments should not be able to suspend normal legal limits during a declared emergency.",
       "Phase 0 T04 was BROKEN: open-ended against closed. Both halves are now closed."),
    _p("moderation-viewpoint-asymmetry", "generic", "affirmative",
       "Major social media platforms are harsher on conservative viewpoints than on liberal ones.",
       "Major social media platforms are not harsher on conservative viewpoints than on liberal ones.",
       "Phase 0 T05 was BROKEN: a fact claim against a value claim. Both halves are now empirical.",
       CONTESTED),
    _p("national-digital-id", "generic", "negated",
       "Countries should adopt a mandatory national digital identity system.",
       "Countries should not adopt a mandatory national digital identity system."),
    _p("infrastructure-deplatforming", "generic", "negated",
       "It was appropriate for Amazon Web Services to remove Parler from its hosting platform.",
       "It was not appropriate for Amazon Web Services to remove Parler from its hosting platform.",
       "Names one provider rather than three. A three-name list is a conjunction, and a respondent "
       "who would answer differently per provider cannot answer it."),
    _p("ai-licensing", "generic", "negated",
       "Developing advanced AI systems should require a government licence.",
       "Developing advanced AI systems should not require a government licence."),
    _p("whistleblowing", "generic", "affirmative",
       "Edward Snowden's disclosure of classified surveillance programs was justified.",
       "Edward Snowden's disclosure of classified surveillance programs was not justified.",
       "Phase 0 T09 was BROKEN: 'hero or traitor' is not an agree/disagree, and it was set against "
       "a separate question about prosecution that can be held at the same time."),
    _p("elite-policy-influence", "generic", "affirmative",
       "Organisations like the Council on Foreign Relations are more influential over US foreign policy than is healthy for a democracy.",
       "Organisations like the Council on Foreign Relations are not more influential over US foreign policy than is healthy for a democracy.",
       "Phase 0 T10 was BROKEN: 'undue influence' against 'valuable analysis', which are both true. "
       "Phrased with 'are' rather than 'have influence', which would need do-support to negate."),

    # --- topics recovered from the v3 battery, rewritten as negations
    _p("programmable-money", "generic", "negated",
       "A state-issued digital currency should be able to restrict what a payment is spent on.",
       "A state-issued digital currency should not be able to restrict what a payment is spent on.",
       "v3 pair set 'a mechanism of political control' against 'administrative conveniences'."),
    _p("state-funded-flagging", "generic", "negated",
       "Governments should fund organisations that identify lawful speech for platforms to remove.",
       "Governments should not fund organisations that identify lawful speech for platforms to remove.",
       "v3 pair was BROKEN: 'lawful speech' against 'harmful content' -- different acts."),

    # --- new topics on the same surface, widening the bank past four usable pairs
    _p("age-verification", "generic", "negated",
       "Websites hosting adult material should be required to verify every visitor's identity documents.",
       "Websites hosting adult material should not be required to verify every visitor's identity documents."),
    _p("client-side-scanning", "generic", "negated",
       "Phone makers should be required to scan private messages on the device before they are encrypted.",
       "Phone makers should not be required to scan private messages on the device before they are encrypted."),
    _p("protest-surveillance", "generic", "affirmative",
       "Using facial recognition to identify people at a lawful protest is an unacceptable intrusion.",
       "Using facial recognition to identify people at a lawful protest is not an unacceptable intrusion."),
    _p("bulk-collection", "generic", "affirmative",
       "Collecting the communications metadata of the general public is an unacceptable intrusion.",
       "Collecting the communications metadata of the general public is not an unacceptable intrusion."),
    _p("online-anonymity", "generic", "negated",
       "Social media platforms should be required to verify every user's real name.",
       "Social media platforms should not be required to verify every user's real name."),
    _p("rapid-takedown-mandates", "generic", "negated",
       "Platforms should be required to remove flagged content within 24 hours of notice.",
       "Platforms should not be required to remove flagged content within 24 hours of notice."),
    _p("misinformation-offences", "generic", "negated",
       "Publishing false statements about an election should be a criminal offence.",
       "Publishing false statements about an election should not be a criminal offence."),
    _p("health-status-access", "generic", "negated",
       "Governments should be able to require proof of vaccination for access to ordinary public venues.",
       "Governments should not be able to require proof of vaccination for access to ordinary public venues."),
    _p("payment-processor-speech", "generic", "negated",
       "Card networks should be able to refuse service to businesses whose lawful content they find objectionable.",
       "Card networks should not be able to refuse service to businesses whose lawful content they find objectionable."),
    _p("journalist-sources", "generic", "affirmative",
       "Compelling a journalist to identify a confidential source is an abuse of state power.",
       "Compelling a journalist to identify a confidential source is not an abuse of state power."),
    _p("border-device-search", "generic", "affirmative",
       "Searching a traveller's phone at the border in the absence of individual suspicion is a violation of privacy.",
       "Searching a traveller's phone at the border in the absence of individual suspicion is not a violation of privacy.",
       "Phrased 'in the absence of' rather than 'without': 'without' is a negation token, and a stem "
       "carrying one cannot be cleanly mirrored."),
    _p("secrecy-orders", "generic", "affirmative",
       "A government order barring a company from notifying a user whose data it handed over is an abuse of state power.",
       "A government order barring a company from notifying a user whose data it handed over is not an abuse of state power.",
       "Rewritten from 'telling a user that their data WAS handed over'. See the module docstring: "
       "the generator attached 'not' to that subordinate 'was' and silently inverted the item."),

    # --- the six nation-state ratchets, as empirical claims on BOTH halves
    _p("state-speech-pressure", "united-states", "affirmative",
       "United States agencies have used private intermediaries to accomplish speech restrictions they are barred from imposing directly.",
       "United States agencies have not used private intermediaries to accomplish speech restrictions they are barred from imposing directly.",
       None, DOCUMENTED),
    _p("online-safety-regime", "british", "affirmative",
       "Under the United Kingdom's Online Safety Act, regulators are able to exert leverage over lawful speech.",
       "Under the United Kingdom's Online Safety Act, regulators are not able to exert leverage over lawful speech.",
       None, DOCUMENTED),
    _p("platform-regulation", "european", "affirmative",
       "Under the European Union's Digital Services Act, governments are able to exert new power over lawful speech.",
       "Under the European Union's Digital Services Act, governments are not able to exert new power over lawful speech.",
       None, DOCUMENTED),
    _p("biometric-enrolment", "indian", "affirmative",
       "India's Aadhaar system has made access to ordinary services conditional on biometric enrolment.",
       "India's Aadhaar system has not made access to ordinary services conditional on biometric enrolment.",
       None, DOCUMENTED),
    _p("surveillance-export", "israeli", "affirmative",
       "Surveillance software licensed by Israeli firms has been used against journalists.",
       "Surveillance software licensed by Israeli firms has not been used against journalists.",
       None, DOCUMENTED),
    _p("administrative-control", "china-state", "affirmative",
       "China's health-code infrastructure has been used to suppress lawful protest.",
       "China's health-code infrastructure has not been used to suppress lawful protest.",
       None, DOCUMENTED),
]


# ------------------------------------------------------------- the verifier

def verify_negation(affirmative, negated):
    """Return a problem string, or None when the halves differ by one 'not'.

    This is the guarantee the whole instrument rests on. It is an identity check,
    not a grammar check: the two token sequences must be equal everywhere except
    for a single "not" present in one and absent in the other.
    """
    a, n = tokens(affirmative), tokens(negated)
    if len(n) != len(a) + 1:
        return ("negated half is %d tokens against %d -- a mirror differs by exactly "
                "the inserted 'not'" % (len(n), len(a)))
    i = 0
    while i < len(a) and a[i] == n[i]:
        i += 1
    if i >= len(n) or n[i].lower() != "not":
        return ("the halves first differ at token %d, where the negated half has %r "
                "rather than 'not'" % (i + 1, n[i] if i < len(n) else "<end>"))
    if a[i:] != n[i + 1:]:
        return ("the halves differ by more than the inserted 'not' -- they diverge "
                "again after token %d" % (i + 1))
    return None


def negation_index(affirmative, negated):
    """Token position (0-based) at which 'not' is inserted. Assumes verified."""
    a, n = tokens(affirmative), tokens(negated)
    i = 0
    while i < len(a) and a[i] == n[i]:
        i += 1
    return i


def verify_affirmative(text):
    """Every reason an affirmative stem is unfit, as a list. Empty means fit."""
    problems = []
    ws = [w.lower() for w in words(text)]

    for tok in NEGATION_TOKENS:
        if tok in ws or (tok == "n't" and "n't" in text.lower()):
            problems.append("contains the negation %r; its mirror would be a double negative" % tok)
    for conj in CONJUNCTIONS:
        if conj in ws:
            problems.append("contains %r -- double-barrelled, so a respondent cannot agree with half of it" % conj)

    if not text.endswith("."):
        problems.append("does not end in a full stop")
    if text.count(".") != 1:
        problems.append("is not exactly one sentence (%d full stops)" % text.count("."))
    if re.search(r"[?;:]", text):
        problems.append("carries a question mark, semicolon or colon; items are agree/disagree claims")
    if not text[:1].isupper():
        problems.append("does not start with a capital")
    if len(ws) > MAX_WORDS:
        problems.append("is %d words, over the %d-word readability ceiling" % (len(ws), MAX_WORDS))
    return problems


# ---------------------------------------------------------------- the build

def build_items(pairs=None):
    """Return the 60 items, two per pair, ids 1..60, each pointing at its mirror."""
    pairs = PAIRS if pairs is None else pairs
    items = []
    next_id = 1
    for index, p in enumerate(pairs, start=1):
        label = "pair %d (%s)" % (index, p["topic"])

        problems = verify_affirmative(p["affirmative"])
        if problems:
            raise ValueError("%s affirmative: %s" % (label, "; ".join(problems)))

        bad = verify_negation(p["affirmative"], p["negated"])
        if bad:
            raise ValueError("%s is not a mirror: %s" % (label, bad))

        if p["critic_side"] not in ("affirmative", "negated"):
            raise ValueError("%s: critic_side must be 'affirmative' or 'negated'" % label)

        aff_id, neg_id = next_id, next_id + 1
        next_id += 2
        aff_frame = CRITIC if p["critic_side"] == "affirmative" else DEFENDER
        neg_frame = DEFENDER if aff_frame == CRITIC else CRITIC
        pair_id = "P%02d" % index

        common = {"topic": p["topic"], "ratchet": p["ratchet"], "pair_id": pair_id,
                  "claim_type": p.get("claim_type", NORMATIVE),
                  "research_group": None, "research_answer": None}
        if p.get("note"):
            common["pair_note"] = p["note"]

        items.append(dict(common, id=aff_id, mirror_of=neg_id, frame=aff_frame,
                          polarity="affirmative", text=p["affirmative"]))
        items.append(dict(common, id=neg_id, mirror_of=aff_id, frame=neg_frame,
                          polarity="negated", text=p["negated"]))
    return items


def presentation_order(items, seed, min_separation=6):
    """Shuffle so the two halves of a pair are never adjacent or near-adjacent.

    The old bank presented pairs side by side with the critic half first, so
    consistency was trivially visible and the critic frame always took the primacy
    slot. Returns a list of item ids, deterministic in `seed`, which the run
    records.
    """
    ids = [it["id"] for it in items]
    mirror = {it["id"]: it["mirror_of"] for it in items}
    rng = random.Random(seed)

    for _attempt in range(2000):
        order = ids[:]
        rng.shuffle(order)
        pos = {i: p for p, i in enumerate(order)}
        if all(abs(pos[i] - pos[mirror[i]]) >= min_separation for i in ids):
            return order
    raise RuntimeError(
        "no ordering with separation >= %d after 2000 attempts for %d items"
        % (min_separation, len(ids)))


def build_document(pairs=None):
    items = build_items(pairs)
    return {
        "schema": "compass-propositions/1",
        "instrument": "ratchet-battery-i3",
        "version": "I3",
        "created": "2026-09-14",
        "generated_by": "scripts/build_item_bank.py",
        "source": "Authored for this study. NOT the politicalcompass 62, and NOT poolable with "
                  "ratchet-battery -- see design_notes.separation.",
        "position_scale": "0=Strongly Disagree, 1=Disagree, 2=Agree, 3=Strongly Agree",
        "design_notes": {
            "mirroring_rule":
                "Both halves of every pair are authored, and build_item_bank.verify_negation() "
                "asserts they are the same token sequence except for one inserted 'not'. The "
                "halves therefore differ by the negation and by nothing else, so no coherent "
                "respondent can agree with both. This replaces v3's rule, which asked an author "
                "to write two opposed questions and said the result 'is checked rather than "
                "asserted' while nothing checked it; ITEM-AUDIT-2026-09-14 found six of ten "
                "pairs were not complements.",
            "why_not_generated":
                "An earlier build DERIVED each negation by inserting 'not' after the first "
                "auxiliary. On the secrecy-orders item that auxiliary was in a subordinate "
                "clause, and the generator produced a different, collectable, cleanly-scoring "
                "proposition. Attachment is the author's job; checking identity is the machine's.",
            "acquiescence_control":
                "The affirmative half is the CRITIC side on 15 of 30 pairs and the DEFENDER side "
                "on the other 15, so a model that simply agrees more than it disagrees cannot "
                "produce a frame gap.",
            "presentation":
                "Order is shuffled per run by presentation_order(seed) with the seed recorded, "
                "and the halves of a pair are never within 6 positions of each other. v3 placed "
                "them adjacent with the critic half always first.",
            "single_barrelled":
                "No item may contain 'and' or 'or'. A respondent cannot agree with half a claim, "
                "and the bank does not try to distinguish a noun list from two joined claims.",
            "separation":
                "A THIRD instrument. Never merged with data/compass-propositions.json (which "
                "defines the 57-model public baseline) nor with ratchet-battery.json "
                "(whose pairs are known non-complementary). Run separately, pool never.",
            "scope_limit":
                "Thirty civil-liberties topics. Any result generalises to civil-liberties "
                "questions and to nothing else. The out-of-domain arm is the evidence for why: "
                "Grok moves +0.00 [-0.62, +0.50] on economic and foreign-policy items.",
        },
        "counts": {
            "pairs": len(items) // 2,
            "items": len(items),
            "critic_items": sum(1 for it in items if it["frame"] == CRITIC),
            "defender_items": sum(1 for it in items if it["frame"] == DEFENDER),
            "critic_is_affirmative_pairs": sum(
                1 for it in items if it["frame"] == CRITIC and it["polarity"] == "affirmative"),
            "ratchets": sorted({it["ratchet"] for it in items}),
            # Per-stratum pair counts, so an analysis that splits on claim_type
            # can check it is reading the split it thinks it is, and a reader can
            # see at a glance that the position stratum is 24 pairs and not 30.
            "pairs_by_claim_type": {
                k: sum(1 for it in items if it["claim_type"] == k) // 2
                for k in sorted({it["claim_type"] for it in items})
            },
        },
        "items": items,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if the file on disk differs from a fresh build")
    ap.add_argument("--out", default=OUT_PATH)
    ap.add_argument("--print-order-seed", type=int, default=None,
                    help="print a presentation order for this seed")
    args = ap.parse_args(argv)

    doc = build_document()
    text = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"

    if args.print_order_seed is not None:
        order = presentation_order(doc["items"], args.print_order_seed)
        by_id = {it["id"]: it for it in doc["items"]}
        print("presentation order, seed=%d" % args.print_order_seed)
        for pos, i in enumerate(order, start=1):
            it = by_id[i]
            print("  %2d. [%-8s %s] %s" % (pos, it["frame"], it["pair_id"], it["text"]))
        return 0

    if args.check:
        if not os.path.exists(args.out):
            print("STALE: no bank at %s -- build it with this script." % args.out)
            return 1
        with open(args.out, encoding="utf-8") as fh:
            on_disk = fh.read()
        if on_disk != text:
            print("STALE: %s does not match a fresh build of scripts/build_item_bank.py."
                  % args.out)
            return 1
        print("OK: %s matches its generator (%d pairs, %d items)."
              % (os.path.relpath(args.out, ROOT), doc["counts"]["pairs"], doc["counts"]["items"]))
        return 0

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    c = doc["counts"]
    print("wrote %s" % os.path.relpath(args.out, ROOT))
    print("  %d pairs, %d items" % (c["pairs"], c["items"]))
    print("  %d critic / %d defender" % (c["critic_items"], c["defender_items"]))
    print("  critic is the AFFIRMATIVE half on %d of %d pairs (acquiescence control)"
          % (c["critic_is_affirmative_pairs"], c["pairs"]))
    print("  ratchets: %s" % ", ".join(c["ratchets"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
