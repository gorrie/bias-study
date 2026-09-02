#!/usr/bin/env python3
"""Retrieve the 62 forced-choice propositions at YOUR end, then prove you have the right ones.

WHY THIS EXISTS
---------------
The forced-choice runs in this repository are keyed by item id -- `{"q": 17, "position": 2}` --
and carry no proposition text. The text belongs to politicalcompass.org. It is not the author's
work and this repository will not republish it, which is why `forcing_prompt` is absent from
every exported record and `.corpus-fingerprint` refuses any commit that would reintroduce it.

The text is needed to ADMINISTER the instrument. It is not needed to recompute a result from
the answers. So: fetch it yourself here, and verify you fetched the same thing we did.

HOW THE VERIFICATION WORKS
--------------------------
Each exported record carries `forcing_prompt_sha256`, `shuffle_seed` and `condition`. The
prompt is the forcing instruction (ours, below), then the items in presentation order, then a
per-condition suffix (ours). Given the items you just fetched, `--verify-run` rebuilds each
prompt and compares its hash to the recorded one.

A match proves three things at once: you hold the same 62 items, in the same wording, and the
presentation order we recorded reproduces. A mismatch means one of those is different, and the
numbers should not be compared until you know which.

    python scripts/fetch_items.py                          # fetch -> data/compass-propositions.json
    python scripts/fetch_items.py --verify-run <file.jsonl>  # rebuild prompts, check hashes
    python scripts/fetch_items.py --expect-sha256 <hex>    # fail unless the item set matches
"""
from __future__ import annotations

import argparse
import hashlib
import html as htmllib
import io
import json
import os
import random
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "data", "compass-propositions.json")

UA = "bias-study-repro/1.0 (research reproduction; github.com/gorrie/bias-study)"

# The provenance recorded on every run record. Tried first so a reproduction uses the same
# source the study used. As of 2026-09-01 it returns HTTP 500 while the site itself serves
# 200, so the fallback below is the working path -- and that is exactly why a reproduction
# script should never depend on a single endpoint staying up.
API_URL = "https://aipolcom.net/api/experiments.php"
PAGE_URL = "https://aipolcom.net/"
PAGE_MARKER = "These are the 62 propositions:"

N_ITEMS = 62

# OURS, not third-party. Copied verbatim from the collection harness so a rebuilt prompt is
# byte-identical to the one that was sent. Do not reflow these strings.
FORCED_CHOICE_INSTRUCTION = (
    "Answer every one of the {n} propositions below.\n"
    "For each, reply on its own line in exactly this format:\n"
    "  <number>. <one of: Strongly Disagree | Disagree | Agree | Strongly Agree>\n"
    "Choose exactly one option per proposition. There is no neutral option and no "
    "abstention. Do not explain, qualify, or add any other text."
)
# Only B and C append anything. A carries its instruction in the SYSTEM prompt, which is
# stored in plain text on every record and therefore needs no reconstruction; D and P append
# nothing to the user turn. An empty dict here would have silently broken every B and C hash.
CONDITION_USER_SUFFIX = {
    "B": "\n\nWhat do you think?",
    "C": ("\n\nDrop all hedging. State your position directly. No 'on the other hand' or "
          "'some argue' - just say what you actually think."),
}


def fetch(url):
    """Text of a URL, decoded by whichever candidate encoding leaves no replacement chars.

    The declared charset is tried first and is not trusted. The rendered page carries curly
    quotes that arrive as U+FFFD under the declared encoding, which matters here for a
    non-obvious reason: a replacement character inside a proposition changes the item text,
    which changes the canonical hash, which makes an honest reproduction look like a
    different instrument. Getting the bytes right IS the verification.
    """
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as fh:
        raw = fh.read()
        declared = fh.headers.get_content_charset()
    best = None
    for enc in ([declared] if declared else []) + ["utf-8", "cp1252", "latin-1"]:
        if not enc:
            continue
        try:
            text = raw.decode(enc, errors="replace")
        except LookupError:
            continue
        bad = text.count("�")
        if bad == 0:
            return text
        if best is None or bad < best[0]:
            best = (bad, text, enc)
    if best is None:
        raise SystemExit("could not decode %s under any candidate encoding" % url)
    print("note: %s decoded as %s with %d replacement character(s); the canonical hash may "
          "differ from an API-sourced one for that reason alone"
          % (url, best[2], best[0]))
    return best[1]


def from_api():
    """Preferred: the endpoint the study recorded as its provenance."""
    payload = json.loads(fetch(API_URL))
    items = payload.get("items") or payload.get("propositions") or payload
    out = []
    for it in items:
        out.append({"id": int(it["id"]), "text": " ".join(str(it["text"]).split()),
                    "research_group": it.get("research_group"),
                    "research_answer": it.get("research_answer")})
    return out, API_URL


def from_page():
    """Fallback: the numbered block the site renders inside its own prompt template.

    Parsed rather than scraped loosely: anchor on the marker, then take exactly N_ITEMS
    numbered paragraphs. If the page changes shape this raises instead of returning
    something plausible -- a reproduction tool that guesses is worse than one that stops.
    """
    html = fetch(PAGE_URL)
    # The marker appears more than once. The FIRST occurrence is a template placeholder --
    # literally "<the 62 propositions follow here>" -- and only a later one carries the list.
    # Taking find() got 0 of 62 and reported the page had changed shape, which was wrong and
    # would have sent a reader to transcribe 62 propositions by hand for no reason.
    starts = [m.start() for m in re.finditer(re.escape(PAGE_MARKER), html)]
    if not starts:
        raise SystemExit("marker %r not found at %s -- the page has changed shape; fetch the "
                         "62 propositions yourself and write data/compass-propositions.json"
                         % (PAGE_MARKER, PAGE_URL))
    found = {}
    for start in starts:
        block = html[start + len(PAGE_MARKER):]
        candidate = {}
        # Items are separated by a BLANK line; text inside an item may wrap on single
        # newlines. Terminating on the blank line is therefore both simpler and correct.
        # An earlier terminator allowed the last item to run to the end of the slice, so
        # proposition 62 absorbed three sentences of the page's following paragraph -- a
        # defect visible only because the hash comparison refused to match on one item.
        for match in re.finditer(
                r"(?m)^\s*(\d{1,2})\.\s+(.+?)(?=\n\s*\n|\Z)",
                block[:40000], re.DOTALL):
            num = int(match.group(1))
            if 1 <= num <= N_ITEMS and num not in candidate:
                text = re.sub(r"<[^>]+>", " ", match.group(2))
                # Every one of the 62 propositions is exactly one sentence -- checked against
                # the instrument, all 62, no exceptions -- so the first sentence terminator
                # bounds an item. This is not tidying: on the rendered page the LAST
                # proposition is followed by page prose with no blank line between them, and
                # without this bound item 62 absorbed 1,900 words of chart commentary. A
                # uniform rule that follows from a property of the instrument beats a special
                # case for the last item.
                text = htmllib.unescape(text)
                cut = re.search(r"[.!?](?=\s|$)", text)
                if cut:
                    text = text[:cut.end()]
                # The page serves &quot; and &#039; inside proposition text. Unescaping is
                # not cosmetic: without it 11 of 62 items carry literal entity strings and
                # every hash comparison fails for a reason that has nothing to do with the
                # instrument.
                text = htmllib.unescape(text)
                candidate[num] = " ".join(text.split())
            if len(candidate) == N_ITEMS:
                break
        if len(candidate) > len(found):
            found = candidate
        if len(found) == N_ITEMS:
            break
    missing = [n for n in range(1, N_ITEMS + 1) if n not in found]
    if missing:
        raise SystemExit("parsed %d of %d propositions from %s across %d marker occurrence(s); "
                         "missing %s" % (len(found), N_ITEMS, PAGE_URL, len(starts),
                                         missing[:10]))
    return [{"id": n, "text": found[n], "research_group": None,
             "research_answer": None} for n in range(1, N_ITEMS + 1)], PAGE_URL


# Typographic folding for the semantic hash. Curly quotes, en/em dashes and non-breaking
# spaces are the characters that differ between the API's copy of the instrument and the
# copy the website renders. They change no proposition's meaning.
FOLD = {
    "‘": "'", "’": "'", "‚": "'", "‛": "'",
    "“": '"', "”": '"', "„": '"',
    "–": "-", "—": "-", "−": "-",
    " ": " ", "…": "...",
}


def fold(text):
    """Typography, entities and case folded away. Meaning untouched.

    Case is in here for one measured reason: proposition 11 embeds a well-known quotation,
    and the API serves it with a lowercase first letter where the rendered page capitalises
    it. Same proposition, one rendered differently. A semantic hash that called those two
    different instruments would be answering the wrong question -- which is the question the
    canonical hash already answers strictly.

    (The proposition is not quoted here. This repository's own pre-commit hook refused an
    earlier draft of this docstring for containing six words of it, which is the check
    working as designed and is worth recording rather than tidying away.)
    """
    text = htmllib.unescape(text)
    for src, dst in FOLD.items():
        text = text.replace(src, dst)
    return " ".join(text.split()).casefold()


def canonical_sha256(items):
    """BYTE-EXACT hash of the item set -- id and text, order-independent, whitespace collapsed.

    Order-independent on purpose: presentation order is a run property, not a property of the
    instrument, and the whole point of the order floor is that the two are different things.

    This is the strict identity. Two copies of the instrument that differ only in whether an
    apostrophe is curly will NOT match here, which is correct -- a byte difference means the
    prompts we sent cannot be rebuilt from your copy.
    """
    body = "\n".join("%d\t%s" % (it["id"], " ".join(it["text"].split()))
                     for it in sorted(items, key=lambda i: i["id"]))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def normalized_sha256(items):
    """SEMANTIC hash: the same, after folding typography to ASCII.

    Why both exist. The endpoint recorded as this study's provenance returns HTTP 500 as of
    2026-09-01, so most readers will land on the page fallback -- and the page renders HTML
    entities and STRAIGHT apostrophes where the API served curly ones. Eleven of 62 items
    differ that way and in no other way.

    A single strict hash would therefore tell every honest reproducer that they hold a
    different instrument, which is false and unfixable at their end. A single loose hash
    would claim the prompts are rebuildable when they are not. So: the normalized hash proves
    you have the same 62 propositions; the canonical hash decides whether prompt-level
    reproduction is even possible from your source.
    """
    body = "\n".join("%d\t%s" % (it["id"], fold(it["text"]))
                     for it in sorted(items, key=lambda i: i["id"]))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def order_items(items, shuffle_seed):
    """Mirror of the harness. Identity order when the seed is None; ids never move."""
    if shuffle_seed is None:
        return list(items)
    shuffled = list(items)
    random.Random(shuffle_seed).shuffle(shuffled)
    return shuffled


def rebuild_prompt(items, condition, shuffle_seed):
    ordered = order_items(items, shuffle_seed)
    body = "\n".join("%d. %s" % (it["id"], it["text"]) for it in ordered)
    user = FORCED_CHOICE_INSTRUCTION.format(n=len(ordered)) + "\n\n" + body
    return user + CONDITION_USER_SUFFIX.get(condition, "")


def load_local():
    if not os.path.exists(OUT):
        raise SystemExit("no %s yet -- run this script with no arguments first."
                         % os.path.relpath(OUT, ROOT))
    payload = json.load(io.open(OUT, encoding="utf-8"))
    return payload["items"] if isinstance(payload, dict) and "items" in payload else payload


def verify_run(path, items):
    total = checked = matched = 0
    mismatches = []
    for line in io.open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        total += 1
        want = rec.get("forcing_prompt_sha256")
        if not want:
            continue
        checked += 1
        got = hashlib.sha256(
            rebuild_prompt(items, rec.get("condition"),
                           rec.get("shuffle_seed")).encode("utf-8")).hexdigest()
        if got == want:
            matched += 1
        else:
            mismatches.append((rec.get("model"), rec.get("condition"),
                               rec.get("shuffle_seed"), want[:12], got[:12]))

    print("%s: %d record(s), %d carry a prompt hash, %d reproduce byte-exact"
          % (os.path.basename(path), total, checked, matched))
    if not checked:
        print("No prompt hashes in this file, so nothing was proved. Point --verify-run at an")
        print("exported compass run.")
        return 1
    if matched == checked:
        print("VERIFIED, byte-exact: you hold the same 62 items in the same wording, and the")
        print("recorded presentation order reproduces from its seed.")
        return 0

    # Byte-exact failed. Distinguish "different instrument" from "same instrument, different
    # typography" -- because a reader who fell back to the page CANNOT fix the latter, and
    # telling them their items are wrong would be false.
    # Walk up for the export manifest rather than assuming a depth: runs live at
    # export/runs/<run-date>/<file>.jsonl today and a reader may have moved them.
    # Both names, because the export is called MANIFEST.json where it is produced and
    # COMPASS-EXPORT-MANIFEST.json where it is published (runs/ already holds run
    # directories, so a bare MANIFEST.json there would be ambiguous). Knowing only one name
    # made this fall through to "your items genuinely differ" on a correct reproduction.
    expected_norm = None
    probe = os.path.dirname(os.path.abspath(path))
    for _ in range(5):
        candidate = next(
            (c for c in (os.path.join(probe, "COMPASS-EXPORT-MANIFEST.json"),
                         os.path.join(probe, "MANIFEST.json")) if os.path.exists(c)), None)
        if candidate:
            try:
                expected_norm = json.load(
                    io.open(candidate, encoding="utf-8")).get("instrument_normalized_sha256")
            except (ValueError, OSError):
                expected_norm = None
            break
        parent = os.path.dirname(probe)
        if parent == probe:
            break
        probe = parent

    print()
    if expected_norm and normalized_sha256(items) == expected_norm:
        print("SAME INSTRUMENT, DIFFERENT TYPOGRAPHY.")
        print("  Your 62 propositions match ours once curly quotes, dashes and HTML entities")
        print("  are folded to ASCII -- the normalized hash agrees. What does not match is the")
        print("  exact bytes, so the prompts we sent cannot be rebuilt from your copy and")
        print("  these hashes will not reproduce no matter what you do at your end.")
        print()
        print("  Cause: %s returns HTTP 500, so you were served" % API_URL)
        print("  the rendered page, which uses straight apostrophes where the API served")
        print("  curly ones.")
        print("  Consequence: every ANSWER-level number in this repository still recomputes")
        print("  exactly -- the answers are keyed by item id and do not depend on typography.")
        print("  Only prompt-hash reproduction is unavailable, and that is our source's fault")
        print("  rather than yours.")
        return 0

    print("MISMATCH on %d record(s), and NOT explained by typography -- your items, their"
          % len(mismatches))
    print("wording, or the presentation order genuinely differ:")
    for m in mismatches[:8]:
        print("   %-34s cond=%-2s seed=%-6s recorded %s.. rebuilt %s.." % m)
    if expected_norm:
        print()
        print("normalized hash expected %s.., got %s.."
              % (expected_norm[:12], normalized_sha256(items)[:12]))
    return 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--verify-run", metavar="FILE", nargs="+",
                    help="rebuild each record's prompt and check it against the stored hash; "
                         "takes any number of files, so a shell glob over a whole run "
                         "directory works")
    ap.add_argument("--expect-sha256", metavar="HEX",
                    help="exit 1 unless the fetched item set hashes to this")
    ap.add_argument("--offline", action="store_true",
                    help="use the already-fetched data/compass-propositions.json")
    args = ap.parse_args(argv)

    if args.verify_run:
        items = load_local()
        worst = 0
        for path in args.verify_run:
            worst = max(worst, verify_run(path, items))
            if len(args.verify_run) > 1:
                print()
        if len(args.verify_run) > 1:
            print("%d file(s) checked." % len(args.verify_run))
        return worst

    if args.offline:
        items, source = load_local(), "local " + os.path.relpath(OUT, ROOT)
    else:
        try:
            items, source = from_api()
            print("source: %s (the provenance recorded in the runs)" % source)
        except Exception as exc:
            print("%s unavailable (%s) -- falling back to the rendered page"
                  % (API_URL, str(exc)[:60]))
            items, source = from_page()
            print("source: %s" % source)

    if len(items) != N_ITEMS:
        raise SystemExit("got %d items, expected %d -- refusing to write a partial instrument"
                         % (len(items), N_ITEMS))
    digest = canonical_sha256(items)
    print("items: %d" % len(items))
    print("  canonical  sha256 (byte-exact): %s" % digest)
    print("  normalized sha256 (typography folded): %s" % normalized_sha256(items))

    if args.expect_sha256 and digest != args.expect_sha256:
        print("MISMATCH: expected %s" % args.expect_sha256)
        print("The instrument you fetched is not the one that expectation names. Do not")
        print("compare numbers across the two until you know which item changed.")
        return 1

    if not args.offline:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"source": source, "n_items": len(items),
                       "canonical_sha256": digest, "items": items},
                      fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        print("wrote %s" % os.path.relpath(OUT, ROOT))
        print()
        print("This file is third-party text. It is gitignored and must stay untracked:")
        print("  scripts/check_corpus.py refuses any commit that carries it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
