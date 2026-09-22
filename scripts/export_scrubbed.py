#!/usr/bin/env python3
"""Export the forced-choice runs for publication, with any third-party text removed.

WHAT CHANGED, 2026-09-17
------------------------
THE STUDY'S INSTRUMENT IS NO LONGER SOMEONE ELSE'S. The live bank is
`data/ratchet-battery.json` -- 32 items in 16 mirrored pairs, written by Ian Gorrie and
MIT-licensed with the rest of the repository -- and it ships with the paper. There is nothing to withhold and nothing
for a reader to fetch: `forcing_prompt` stays in the export, because the whole argument of
this study is that a field should publish what it measures.

So this script's original job is done and its machinery is not. Everything below still
applies to any corpus that DOES carry licensed text -- `runs/refusal-ablation/` holds 450
verbatim XSTest prompts from Roettger et al. -- and the post-write verification against the
release repository's own fingerprint oracle is the part that must never be removed.

`--scrub` selects the old behaviour. The default is a full export, which is then scanned
exactly as hard: an export of the author's own text still must not carry anyone else's.

The compass-era paths are gone with the bank: `data/compass-propositions.json` moved to
`withdrawn/`, and the reader-side fetcher -- whose only job was retrieving it -- moved with
it. This file imported that module for the reader-side hash functions and would now raise on
import, which is how it was found: a dead cross-tree reference, caught by
`test_cross_tree_references.py`, in the script that produces the public data release.

WHY THE SCRUBBING EXISTS AT ALL
-------------------------------
The paper's numbers once came from 1,678 records carrying a retired 62-item external
questionnaire verbatim in `forcing_prompt`. That text was licensed third-party work and not
the author's, so those runs could not be published as they stood -- which
is why the public repository currently carries a provenance note saying the corpus, the floor
scripts and the controls audit are not in it, and why the website carries an undated promise
that the record is coming.

On 2026-09-01, 525 of these files were copied into the public working tree while staging a
release and 460 carried the text. A `git add -A` would have published someone else's
questionnaire in bulk. `check_corpus.py` in the release repo now refuses that at commit time.
This script is the other half: the export that IS publishable.

WHAT MAKES A NUMBER RECOMPUTABLE WITHOUT THE TEXT
-------------------------------------------------
Every answer is already keyed by item id -- `answers` is a list of `{"q": 17, "position": 2}`.
The proposition text is needed to ADMINISTER the instrument, never to recompute a result from
the answers. So a scrubbed export keeps the answers and drops the text, and the reader retrieves
the items at the reader's end from the same source this study used. A reader can then verify
the prompt they reconstruct hashes to the `forcing_prompt_sha256` recorded here, which proves
they are holding the same instrument without this repository ever shipping it.

VERIFICATION IS NOT OPTIONAL
----------------------------
The export is re-scanned after writing, against the release repo's own fingerprint list --
the same oracle its pre-commit hook uses, not a reimplementation of it. If one fingerprint
survives anywhere in the output, this exits 1 and says where. An export that cannot prove
itself clean is worse than no export, because it looks like diligence.

    python scripts/export_scrubbed.py --out export
    python scripts/export_scrubbed.py --out export --audit-only   # scan, write nothing
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import io
import json
import os
import re
import shutil
import sys
import studypaths as _SP  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
RUNS = os.path.join(STUDY, "runs")

# The release repo's fingerprint list is the oracle. Read it rather than reimplement it: two
# copies of "what counts as instrument text" is how one of them ends up permissive.
DEFAULT_FINGERPRINTS = os.path.join(STUDY, '.corpus-fingerprint')

SCHEMA = _SP.SCHEMA

# Dropped outright. forcing_prompt is the instrument; the rest are recomputable or empty.
DROP_FIELDS = ("forcing_prompt",)


def instrument_texts():
    """Third-party item strings held privately. Never written to the export.

    THE LIVE INSTRUMENT IS NOT IN THIS LIST, deliberately. The Ratchet battery is the author's
    own text and ships in full; putting it here would scrub the study's own instrument out of
    its own data release. What belongs here is text this repository is not entitled to
    republish -- XSTest's prompts, and the retired questionnaire for as long as any record
    carrying it is exported at all.
    """
    texts = []
    for rel, key, field in (("withdrawn/compass-bank/compass-propositions.json", "items", "text"),
                            ("data/xstest-prompts.json", "prompts", "prompt")):
        path = os.path.join(STUDY, rel)
        if not os.path.exists(path):
            continue
        payload = json.load(io.open(path, encoding="utf-8"))
        rows = payload[key] if isinstance(payload, dict) and key in payload else payload
        texts += [r[field] for r in rows if isinstance(r, dict) and r.get(field)]
    return texts


def redact_instrument(text, fingerprints):
    """Replace any instrument text inside a string, keeping everything around it.

    Needed because `data/controls-audit.json` -- which a replicator needs, since
    `controls_audit.py` and `references.py` both read it -- quotes one proposition verbatim.
    The note reads "the deleted items are the charged ones: sex outside marriage (6 of 30
    runs) ... an exact tax proposition", and every other item in that list is already a
    paraphrased topic label. Only the last is the licensed sentence.

    So the redaction is span-local: the offending words go, the analysis around them stays.
    Withholding the whole field would have cost a real finding about which items Liu et al.
    lost to refusals, which is the one thing that note exists to record.
    """
    cc = _checker()
    if cc is None:
        return text, 0
    window, hashed = cc.load_hashed()
    if not (window and hashed):
        return text, 0

    changed = 0
    # Redact using the ACTUAL propositions, which this side of the fence has. Matching on the
    # real sentences is precise; the hashes are for VERIFYING afterwards, and they cannot
    # locate a span because a hash is one-way by design.
    #
    # An earlier version tried to walk folded word-windows back onto raw words. Folding
    # strips punctuation, so the two tokenisations differ in length, the alignment guard
    # correctly refused, and the whole field was withheld -- losing the finding about which
    # items Liu et al. lost to refusals, which is the only reason that note exists.
    for prop in instrument_texts():
        words = [w for w in re.split(r"\W+", prop) if w]
        if not words:
            continue
        # Flexible separators so punctuation and line breaks between the words do not
        # prevent the match, and word boundaries so it cannot fire mid-word.
        pattern = r"\b" + r"\W+".join(re.escape(w) for w in words) + r"\b"
        text, n = re.subn(pattern, "[instrument text withheld]", text, flags=re.IGNORECASE)
        changed += n

    # Verify the redaction actually worked rather than assuming it did.
    if cc.window_hashes(text, window) & hashed:
        return "[instrument text withheld: a span survived redaction]", changed + 1
    return text, changed


def scrub_json_strings(obj, fingerprints, tally):
    """Walk a JSON structure, redacting instrument text in every string."""
    if isinstance(obj, str):
        out, n = redact_instrument(obj, fingerprints)
        if n:
            tally["redactions"] += n
        return out
    if isinstance(obj, dict):
        return {k: scrub_json_strings(v, fingerprints, tally) for k, v in obj.items()}
    if isinstance(obj, list):
        return [scrub_json_strings(v, fingerprints, tally) for v in obj]
    return obj


def export_controls_audit(out_root, fingerprints):
    """Emit a publishable `data/controls-audit.json`, derived rather than hand-edited."""
    src = os.path.join(STUDY, "data", "controls-audit.json")
    if not os.path.exists(src):
        return None
    payload = json.load(io.open(src, encoding="utf-8"))
    tally = {"redactions": 0}
    scrubbed = scrub_json_strings(payload, fingerprints, tally)
    dest_dir = os.path.join(out_root, "data")
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, "controls-audit.json")
    with io.open(dest, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(scrubbed, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return tally["redactions"]


def instrument_hashes():
    """The two hashes of the instrument, computed with the PUBLIC reader's own functions.

    THESE ARE NOW COMPUTED HERE, and that is a downgrade made knowingly. They used to be
    imported from the release repo's reader-side fetcher, so the exporter and the reader could
    not disagree about what "the same instrument" means. That module existed ONLY to retrieve
    the retired third-party questionnaire, and it retired with it on 2026-09-17 -- leaving
    this import dead and this script unable to run at all.

    The reason the shared definition mattered was that a reader had to REBUILD the instrument
    from another source and prove it matched. With the author's own bank shipping in full,
    there is nothing to rebuild: the reader has the file. The hash is now a plain integrity
    check on the published bank rather than the hinge of a reconstruction protocol.

    Canonical = the item texts, in id order, joined by newline. Normalized = the same after
    folding typographic quotes, dashes and HTML entities to ASCII, which is the fold
    `check_corpus` already defines -- imported from it, not retyped, because that is the one
    definition of "the same text" this repository keeps.
    """
    items_path = os.path.join(STUDY, "data", "ratchet-battery.json")
    payload = json.load(io.open(items_path, encoding="utf-8"))
    items = payload["items"] if isinstance(payload, dict) and "items" in payload else payload
    texts = [i["text"] for i in sorted(items, key=lambda r: r["id"])]
    canonical = "\n".join(texts)

    release_scripts = os.path.dirname(DEFAULT_FINGERPRINTS)
    sys.path.insert(0, os.path.join(release_scripts, "scripts"))
    try:
        import check_corpus as CC
        fold = CC.fold_for_hash
    except (ImportError, AttributeError):
        raise SystemExit(
            "cannot import check_corpus.fold_for_hash from %s/scripts -- the normalisation\n"
            "rule is shared with the leak gate and must not be reimplemented here."
            % release_scripts)
    return {"canonical": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            "normalized": hashlib.sha256(fold(canonical).encode("utf-8")).hexdigest(),
            "n_items": len(texts)}


def load_fingerprints(path):
    if not os.path.exists(path):
        raise SystemExit(
            "fingerprint list not found: %s\n"
            "This export must be verified against the release repo's own oracle. Pass\n"
            "--fingerprints with the path to .corpus-fingerprint." % path)
    out = []
    with io.open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                out.append(line)
    if not out:
        raise SystemExit("fingerprint list %s is empty -- refusing to certify anything" % path)
    return out


def _checker():
    """Canonical GitLab checker; its matching rules are exported unchanged."""
    try:
        import check_corpus
    except ImportError:
        return None
    return check_corpus


def hits(text, fingerprints):
    """Instrument text present in a string, by BOTH oracles the public gate uses.

    2026-09-02, and this was my error. The first version of this exporter checked only the
    ten PLAINTEXT fragments in `.corpus-fingerprint`, certified the export clean, and said so.
    The hashed n-gram list -- 476 digests covering all 62 propositions -- was built later the
    same night, and I never re-verified the artifact the weaker detector had already passed.
    Staging the export into the public repo, the pre-commit hook refused **11 files**: models
    that had echoed propositions NOT among those ten fragments.

    A detector strengthened after an artifact was certified against the old one leaves the
    artifact uncertified. Re-run the new detector over the old output, every time.
    """
    if not text:
        return []
    low = text.lower()
    found = [f for f in fingerprints if f.lower() in low]
    cc = _checker()
    if cc is not None:
        window, hashed = cc.load_hashed()
        if hashed and window:
            overlap = cc.window_hashes(text, window) & hashed
            if overlap:
                found.append("hashed:%d %d-gram(s) of the instrument"
                             % (len(overlap), window))
    return found


def scrub_record(rec, fingerprints, tally, drop_fields=DROP_FIELDS):
    """Return a publishable copy, and record every field touched.

    `drop_fields` is a parameter so the DEFAULT export keeps `forcing_prompt`. On the author's
    own instrument that field is the study publishing what it measured; dropping it was
    correct only while the prompt carried someone else's licensed text. The per-field
    fingerprint scan below still runs either way, so keeping the prompt cannot smuggle a
    third-party item back in -- if one is there, the field is withheld and the export says so.
    """
    out = {}
    for key, value in rec.items():
        if key in drop_fields:
            continue
        if isinstance(value, str):
            found = hits(value, fingerprints)
            if found:
                # Never silently. A field that had to be emptied is part of the record.
                out[key] = "[withheld: contains third-party instrument text]"
                tally["scrubbed_fields"][key] = tally["scrubbed_fields"].get(key, 0) + 1
                continue
        out[key] = value

    prompt = rec.get("forcing_prompt")
    if prompt:
        out["forcing_prompt_sha256"] = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        out["forcing_prompt_chars"] = len(prompt)
        out["forcing_prompt_note"] = (
            "Instrument text withheld from THIS record because it carries third-party "
            "material. Rebuild the prompt from the published bank and this record's "
            "shuffle_seed, then check your reconstruction against this sha256.")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default="export", help="output directory, relative to the study")
    ap.add_argument("--scrub", action="store_true",
                    help="drop %s from every record. The pre-2026-09-17 behaviour, correct "
                         "while the prompt carried licensed third-party text. The live "
                         "instrument is the author's and ships in full, so the default now "
                         "KEEPS the prompt -- the per-field fingerprint scan runs either way."
                         % ", ".join(DROP_FIELDS))
    ap.add_argument("--fingerprints", default=DEFAULT_FINGERPRINTS)
    ap.add_argument("--audit-only", action="store_true",
                    help="scan the whole runs tree and report; write nothing")
    args = ap.parse_args(argv)

    fingerprints = load_fingerprints(args.fingerprints)
    drop_fields = DROP_FIELDS if args.scrub else ()
    print("oracle: %d fingerprints from %s"
          % (len(fingerprints), os.path.relpath(args.fingerprints, STUDY)))
    print("prompt: %s"
          % ("DROPPED (--scrub)" if drop_fields
             else "kept -- the instrument is the author's and ships with the paper"))

    tally = {"records": 0, "files": 0, "with_prompt": 0, "scrubbed_fields": {},
             "other_schema_carrying_text": []}
    exported = {}

    for path in sorted(glob.glob(os.path.join(RUNS, "**", "*.jsonl"), recursive=True)):
        rel = os.path.relpath(path, RUNS).replace("\\", "/")
        keep = []
        for line in io.open(path, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("schema") != SCHEMA:
                # Not the forced-choice corpus. It should not carry the instrument at all --
                # if it does, that is a finding about the OLD study's files, not this export.
                blob = json.dumps(rec, ensure_ascii=False)
                if hits(blob, fingerprints):
                    tally["other_schema_carrying_text"].append(rel)
                continue
            if rec.get("forcing_prompt"):
                tally["with_prompt"] += 1
            keep.append(scrub_record(rec, fingerprints, tally, drop_fields))
            tally["records"] += 1
        if keep:
            exported[rel] = keep
            tally["files"] += 1

    print("scanned runs/: %d records in %d file(s) carry schema %s; %d of them carried the "
          "instrument" % (tally["records"], tally["files"], SCHEMA, tally["with_prompt"]))
    if tally["scrubbed_fields"]:
        print("fields emptied because they contained instrument text:")
        for k, v in sorted(tally["scrubbed_fields"].items()):
            print("   %-18s %d record(s)" % (k, v))
    else:
        print("no retained field contained instrument text -- only forcing_prompt did")
    others = sorted(set(tally["other_schema_carrying_text"]))
    if others:
        print("WARNING: %d non-compass file(s) also carry instrument text: %s"
              % (len(others), ", ".join(others[:5])))

    if args.audit_only:
        return 0

    out_root = os.path.join(STUDY, args.out)
    runs_out = os.path.join(out_root, "runs")
    if os.path.exists(out_root):
        raise SystemExit('output already exists; choose a fresh export path')
    os.makedirs(out_root)
    for rel, records in exported.items():
        dest = os.path.join(runs_out, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with io.open(dest, "w", encoding="utf-8", newline="\n") as fh:
            for rec in records:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # Both hashes of the instrument go in the manifest, and NEITHER contains the instrument.
    # A reader who fetches the items compares against these to learn which of two different
    # things they have: the same propositions (normalized), or the same bytes we sent
    # (canonical). Only the second makes prompt-hash reproduction possible, and as of
    # 2026-09-01 the recorded API provenance is down, so most readers reach only the first.
    inst = instrument_hashes()

    manifest = {
        "schema": "compass-export/1",
        "source_schema": SCHEMA,
        "instrument_canonical_sha256": inst["canonical"],
        "instrument_normalized_sha256": inst["normalized"],
        "instrument_hash_note": (
            "canonical = byte-exact item set; normalized = same after folding curly quotes, "
            "dashes and entities to ASCII. Rebuild prompts only if canonical matches."),
        "records": tally["records"],
        "files": tally["files"],
        "dropped_fields": list(drop_fields),
        "scrubbed_fields": tally["scrubbed_fields"],
        "instrument": ("The Ratchet battery (data/ratchet-battery.json): 32 forced-choice "
                       "items in 16 mirrored pairs, written by Ian Gorrie, MIT. The "
                       "item text SHIPS -- there is no fetch step and no carve-out. This "
                       "field named a retired external questionnaire until 2026-09-17."),
        "verification": ("Every record was scanned against the release repo's "
                         ".corpus-fingerprint list after writing; see the exporter's output."),
    }
    with io.open(os.path.join(out_root, "MANIFEST.json"), "w",
                 encoding="utf-8", newline="\n") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    redactions = export_controls_audit(out_root, fingerprints)
    if redactions is None:
        print("note: data/controls-audit.json not found; not exported")
    else:
        print("data/controls-audit.json exported with %d redaction(s)" % redactions)

    # VERIFY THE ARTIFACT, not the intention. Re-read what was written.
    dirty = []
    for path in sorted(glob.glob(os.path.join(out_root, "**", "*"), recursive=True)):
        if not os.path.isfile(path):
            continue
        text = io.open(path, encoding="utf-8", errors="replace").read()
        found = hits(text, fingerprints)
        if found:
            dirty.append((os.path.relpath(path, out_root), found[:3]))

    print()
    print("wrote %d file(s) to %s/" % (tally["files"] + 1, args.out))
    if dirty:
        print("REFUSING TO CERTIFY -- %d exported file(s) still match the oracle:" % len(dirty))
        for rel, found in dirty[:10]:
            print("   %s  <- %r" % (rel, found[0][:60]))
        return 1
    cc = _checker()
    n_hashed, window = 0, None
    if cc is not None:
        window, hashed = cc.load_hashed()
        n_hashed = len(hashed)
    if n_hashed:
        print("VERIFIED against BOTH oracles: 0 of %d plaintext fragment(s) and 0 of %d "
              "hashed %d-gram(s)" % (len(fingerprints), n_hashed, window))
    else:
        # Say so loudly. An export certified against the plaintext list alone is what the
        # public gate refused 11 files of on 2026-09-02.
        print("PARTIALLY VERIFIED: 0 of %d plaintext fragment(s), and the hashed n-gram "
              "oracle was NOT AVAILABLE." % len(fingerprints))
        print("Do not treat this export as clean: the plaintext list covers 10 of 62 "
              "propositions. Generate .corpus-fingerprint-hashed and re-run.")
        return 1
    print("The answers are keyed by item id, so every published number recomputes from this.")
    print("The instrument ships with the paper: data/ratchet-battery.json, 32 items, MIT.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
