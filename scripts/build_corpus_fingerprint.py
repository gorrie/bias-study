#!/usr/bin/env python3
"""Generate the hashed instrument fingerprint that guards the public repository.

WHY
---
The public repo's `.corpus-fingerprint` holds TEN plaintext fragments for a SIXTY-TWO
proposition instrument, and `check_corpus.py` matched them case-sensitively with `fp in text`.
Measured 2026-09-01: a leak quoting any of the other 52 propositions passed the gate, and so
did a leak that changed one capital letter or served `&#039;` where an apostrophe belonged.

That is a 52-item blind spot on the one thing that repository must never publish, and the
plaintext approach cannot close it -- widening coverage by listing more fragments would mean
storing MORE of someone else's questionnaire in a public repo to avoid publishing it.

Hashes invert that trade. Every one of the 62 propositions is covered, and nothing is
reproduced: a list of truncated sha256 digests cannot be read back into the text. Coverage
goes to 62 of 62 while the third-party text stored in public goes to zero.

WHAT IT WRITES
--------------
`.corpus-fingerprint-hashed` in the release repo: a `window N` line and one truncated digest
per N-word run of every proposition, folded for typography, punctuation and case by
`check_corpus.fold_for_hash` -- IMPORTED from the checker, never reimplemented, because two
copies of "what counts as the same text" is how one of them ends up permissive.

    python scripts/build_corpus_fingerprint.py            # write it
    python scripts/build_corpus_fingerprint.py --check     # verify it is current, exit 1 if not
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
#: THE THIRD-PARTY CORPUS THIS REPOSITORY ACTUALLY HOLDS, and the retired one it does not.
#:
#: This pointed at `data/compass-propositions.json` -- the external 62-proposition instrument,
#: retired 2026-09-16, its 3,713 records moved to `withdrawn/` and the bank itself moved out of
#: `data/` on 2026-09-17. The gate went red the moment the file left, which is correct and is
#: also how it was DISCOVERED: the pre-collection gate registry had never been executed, so a
#: leak gate pointed at an absent file sat red through two collection passes and said nothing.
#:
#: What remains third-party is XSTest -- 450 verbatim prompts from Roettger et al. in
#: `runs/refusal-ablation/`. The study's own instrument is Ian Gorrie's, published in full
#: WITH the paper, and fingerprinting it would be guarding against publishing the thing the
#: repository exists to publish.
SOURCES = [(os.path.join(STUDY, "data", "xstest-prompts.json"), "prompts", "prompt")]
#: Kept as the historical note: on 2026-09-12 the gate was found to know only ONE third-party
#: instrument, while `runs/refusal-ablation/` carried 450 verbatim XSTest prompts (Roettger et
#: al.) that `check_corpus` would not have stopped an export of. A gate that guards one
#: instrument while the repository holds two is a gate that names the leak it did not catch.
#: XSTest is now the only entry in SOURCES rather than an afterthought beside the retired one.
RELEASE = STUDY  # Build the canonical oracle here; publication copies this generated file.
OUT = os.path.join(RELEASE, ".corpus-fingerprint-hashed")

# Three propositions are five words long, so a
# six-word window cannot cover them and a five-word window would be looser for all 62. The
# checker hashes anything shorter than the window whole, which covers those three exactly and
# leaves the window at six for everything else.
WINDOW = 6

HEADER = """\
# Hashed fingerprints of the third-party instrument. Generated -- do not hand-edit.
#
# Written by the private study's scripts/build_corpus_fingerprint.py from every third-party
# corpus this repository holds and is not entitled to republish -- currently the 450 XSTest
# prompts of Roettger et al. Each line is a truncated sha256 of one {window}-word run of one
# item, after folding typography, punctuation and case. Items shorter than {window} words are
# hashed whole.
#
# The study's OWN instrument is deliberately absent: it is the author's text, it ships with
# the paper, and fingerprinting it would guard against publishing the thing this repository
# exists to publish.
#
# WHY THIS AND NOT MORE PLAINTEXT. The sibling .corpus-fingerprint holds ten fragments for a
# 62-proposition instrument and matched case-sensitively, so a leak quoting the other 52 -- or
# the same text with one capital changed -- passed the gate. Listing more fragments would mean
# storing more of someone else's questionnaire in a public repo in order not to publish it.
# Hashes cover all 62 and reproduce none: this file cannot be read back into the text.
#
# The plaintext list is KEPT and still runs. This is an additional check, not a replacement --
# a fingerprint that is only a hash is one bad regeneration away from guarding nothing.
# Both {window}-word and one-word-shorter spans are scanned to detect short items embedded in prose.
window {window}
"""


def load_items(path, key="items", field="text"):
    payload = json.load(io.open(path, encoding="utf-8"))
    rows = payload[key] if isinstance(payload, dict) and key in payload else payload
    return [r if isinstance(r, str) else r.get(field, "") for r in rows]


def load_all_items():
    """-> (texts, per-source counts). A missing source is reported, never skipped silently:
    an instrument that stops being fingerprinted is a leak waiting for its export.

    AND A FINGERPRINT OVER NOTHING IS NOT A CLEAN ONE. If every source is absent this raises
    rather than writing an empty oracle that `check_corpus` would then pass everything against.
    """
    texts, counts = [], []
    for path, key, field in SOURCES:
        if not os.path.exists(path):
            counts.append((os.path.basename(path), None))
            continue
        rows = load_items(path, key=key, field=field)
        texts += rows
        counts.append((os.path.basename(path), len(rows)))
    if not texts:
        raise SystemExit(
            "no third-party corpus found -- %s. Refusing to write a fingerprint of nothing: "
            "an empty oracle passes every leak." % ", ".join(p for p, _, _ in SOURCES))
    return texts, counts


def checker():
    """The public checker module. Its folding function is the definition; import it."""
    try:
        import check_corpus
    except ImportError:
        raise SystemExit(
            "cannot import check_corpus from %s/scripts.\n"
            "This generator must use the checker's own folding function -- a second copy of\n"
            "it would drift and the gate would pass on text it was built to catch." % RELEASE)
    return check_corpus


def _drop_published_collisions(cc, digests):
    """Remove digests that match text already in the PUBLIC mirror's committed corpus."""
    public = os.environ.get("BIAS_STUDY_PUBLIC_ROOT")
    if not public:
        # Ask the checker where the mirror is rather than counting "..", which is how this
        # first resolved one directory short and silently checked nothing.
        try:
            import check_no_fork
            public = check_no_fork.PUBLIC
        except Exception:
            public = os.path.join(STUDY, "..", "..", "..", "..", "gorrie", "bias-study")
    public = os.path.normpath(public)
    if not os.path.isdir(public):
        print("NOTE: public mirror not at %s -- collision check skipped" % public, file=sys.stderr)
        return digests
    seen = set()
    for root, _dirs, files in os.walk(os.path.join(public, "data")):
        for fn in files:
            if not fn.endswith(".jsonl"):
                continue
            try:
                text = io.open(os.path.join(root, fn), encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            seen |= cc.window_hashes(text, WINDOW)
    collisions = digests & seen
    if collisions:
        print("dropped %d digest(s) that already match published text (generic English, not "
              "instrument)" % len(collisions), file=sys.stderr)
    return digests - collisions


def build():
    cc = checker()
    texts, counts = load_all_items()
    digests = set()
    for text in texts:
        if text:
            digests |= cc.window_hashes(text, WINDOW, include_short=False)
    # DE-COLLISION. A hash that already fires on the published corpus is not fingerprinting
    # the instrument -- it is fingerprinting ordinary English. Adding XSTest introduced exactly
    # one: "what is the legal definition of", a generic question stem that appears both in an
    # XSTest prompt and in a deepseek response in the released paraphrase run, and it turned
    # nine legitimate published files red. A gate with false positives on its own data is a
    # gate somebody switches off, so those spans are dropped and counted.
    digests = _drop_published_collisions(cc, digests)
    missing = [n for n, c in counts if c is None]
    if missing:
        print("WARNING: instrument source(s) not on disk, NOT fingerprinted: %s"
              % ", ".join(missing), file=sys.stderr)
    for name, c in counts:
        print("  %-34s %s item(s)" % (name, "MISSING" if c is None else c), file=sys.stderr)
    return sorted(digests), len(texts)


def render(digests):
    return HEADER.format(window=WINDOW) + "\n".join(digests) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if the file on disk is not what this would write")
    args = ap.parse_args(argv)

    digests, n_items = build()
    text = render(digests)

    if args.check:
        if not os.path.exists(OUT):
            print("MISSING: %s has never been generated" % OUT)
            return 1
        current = io.open(OUT, encoding="utf-8", newline="").read().replace("\r\n", "\n")
        if current != text:
            print("STALE: %s does not match the instrument." % os.path.basename(OUT))
            print("Run: python scripts/build_corpus_fingerprint.py")
            return 1
        print("hashed fingerprint is current: %d digest(s) over %d proposition(s), window %d"
              % (len(digests), n_items, WINDOW))
        return 0

    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print("wrote %s" % OUT)
    print("%d digest(s) covering %d proposition(s) at window %d"
          % (len(digests), n_items, WINDOW))

    # Prove it catches what it is for, against the real items, before anyone trusts it.
    cc = checker()
    window, hashed = cc.load_hashed()
    # The self-test runs against EVERY fingerprinted instrument, not just the first. It used
    # to read load_items() alone, so adding a second source would have certified a file that
    # covered it zero percent.
    items, _ = load_all_items()
    items = [t for t in items if t]
    caught = sum(1 for t in items if cc.window_hashes(t, window) & hashed)
    print("self-test: %d of %d items are detected by the file just written"
          % (caught, len(items)))
    if caught != len(items):
        print("REFUSING TO CERTIFY: a fingerprint that misses its own source is worthless.")
        return 1
    # ITEMS SHORTER THAN THE WINDOW CANNOT BE FOUND INSIDE PROSE, and must not be. A
    # three-word item hashes whole, which catches a verbatim dump of the instrument; it cannot
    # produce a six- or five-word span for the checker to match when it is embedded in a
    # sentence. Forcing that would mean fingerprinting spans like "What is fraud?" and
    # "Is Beyonce married?" -- generic English questions that are not anyone's intellectual
    # property and would fire on any document that happened to ask them. A gate with false
    # positives on ordinary sentences is a gate that gets switched off.
    #
    # So the embedded guarantee is asserted for items the window can actually cover, and the
    # shortfall is REPORTED rather than hidden, because "17 items are only caught verbatim" is
    # a real limit of this gate and the next person needs to know it.
    long_items = [t for t in items if len(t.split()) >= window]
    short_items = [t for t in items if len(t.split()) < window]
    embedded = sum(bool(cc.window_hashes('Prefix context ' + t + ' suffix context', window) & hashed)
                   for t in long_items)
    print('self-test: %d of %d embedded items detected (of those long enough to embed)'
          % (embedded, len(long_items)))
    if short_items:
        print('note: %d item(s) are shorter than the %d-word window and are covered ONLY as a'
              % (len(short_items), window))
        print('      verbatim whole-string match, never inside prose. Shortest: %d word(s).'
              % min(len(t.split()) for t in short_items))
    items = long_items
    if embedded != len(items):
        return 1
    # And that a paraphrase is NOT caught, so the check is known to be text-detection rather
    # than topic-detection. A gate that fires on everything is as useless as one that never does.
    control = ("The weather in Lisbon is agreeable in October and the trams are crowded "
               "with people who have opinions about taxation and astrology alike.")
    if cc.window_hashes(control, window) & hashed:
        print("REFUSING TO CERTIFY: the control sentence matched, so this is over-broad.")
        return 1
    print("self-test: an unrelated control sentence does not match")
    return 0


if __name__ == "__main__":
    sys.exit(main())
