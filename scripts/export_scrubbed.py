#!/usr/bin/env python3
"""Export the current study's corpus root (`runs/`) for publication, scanned for third-party text.

WHAT IT SHIPS
-------------
Every complete run directory under `runs/` that is not declared in `NOT_SHIPPED`, whole:
the record sheets, the collector's `manifest.json`, `collection-log.ndjson`, cached analysis
output and calibration files. Plus the two evidence directories under `withdrawn/` that the
withdrawals registry cites (`EVIDENCE_DIRS`): sheets on the author's own instrument that were
withdrawn from the panel and are kept because a withdrawal whose evidence is gone is a claim
about a claim.

Battery sheets (`schema` in `studypaths.SCHEMA_ACCEPTED`) get two derived integrity fields,
`forcing_prompt_sha256` and `forcing_prompt_chars`, so a reader who regenerates a prompt can
prove it matches what was administered. Records of any other schema in a shipped run -- the
judged free-text arm, its judge scores, the both-paths free-text records -- travel as they are.
Every string field of every record is scanned against the fingerprint oracle either way.

`--into <mirror>` writes the verified staging export over the mirror's `runs/<run>/` and
`withdrawn/<dir>/` directories and its `MANIFEST.json`. It never commits. `manifest.derived.json`
is NOT exported: it is a per-tree freeze that `derive_manifest.py --write` regenerates in the
tree that ships it (LEARNINGS 101 -- a generated file copied across trees is a fork).

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

WHAT CHANGED, 2026-09-25
------------------------
Until this date the exporter wrote `forcing_prompt_note` -- "Instrument text withheld from THIS
record" -- on every battery record, including the default export in which the prompt is KEPT.
The public mirror carried that sentence beside the full prompt on 1,170 files. The note is now
written only when the prompt is actually dropped (`--scrub`). The exporter also shipped only
`*.jsonl` records of the battery schema, so a run's own `manifest.json` and the non-battery
records of the 2026-09-25 arms never reached the mirror through it and were hand-copied; it
now ships each run directory whole.

WHY THE SCRUBBING EXISTS AT ALL
-------------------------------
The paper's numbers once came from 1,678 records carrying a retired 62-item external
questionnaire verbatim in `forcing_prompt`. That text was licensed third-party work and not
the author's, so those runs could not be published as they stood.

On 2026-09-01, 525 of these files were copied into the public working tree while staging a
release and 460 carried the text. A `git add -A` would have published someone else's
questionnaire in bulk. `check_corpus.py` in the release repo now refuses that at commit time.
This script is the other half: the export that IS publishable.

WHAT MAKES A NUMBER RECOMPUTABLE WITHOUT THE TEXT
-------------------------------------------------
Every answer is already keyed by item id -- `answers` is a list of `{"q": 17, "position": 2}`.
The proposition text is needed to ADMINISTER the instrument, never to recompute a result from
the answers. So a scrubbed export keeps the answers and drops the text, and a reader can verify
the prompt they reconstruct hashes to the `forcing_prompt_sha256` recorded here.

VERIFICATION IS NOT OPTIONAL
----------------------------
The export is re-scanned after writing, against the release repo's own fingerprint list --
the same oracle its pre-commit hook uses, not a reimplementation of it. If one fingerprint
survives anywhere in the output, this exits 1 and says where. An export that cannot prove
itself clean is worse than no export, because it looks like diligence.

    python scripts/export_scrubbed.py --plan                        # what would ship; writes nothing
    python scripts/export_scrubbed.py --out export/battery          # stage, verify
    python scripts/export_scrubbed.py --out export/battery --into ../../../bias-study-release
    python scripts/export_scrubbed.py --audit-only                  # scan, write nothing
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

# The release repo's fingerprint list is the oracle. Read it rather than reimplement it: two
# copies of "what counts as instrument text" is how one of them ends up permissive.
DEFAULT_FINGERPRINTS = os.path.join(STUDY, '.corpus-fingerprint')

SCHEMA = _SP.SCHEMA
SCHEMA_ACCEPTED = _SP.SCHEMA_ACCEPTED

#: The root this exporter ships: the current study's corpus. The earlier corpus under `data/`
#: is exported by `export_repairs.py`, which derives its list from the repair registries.
SOURCE_ROOT = "runs"

# Dropped outright under --scrub. forcing_prompt is the instrument; the rest are recomputable.
DROP_FIELDS = ("forcing_prompt",)

#: Never exported, whatever they hold.
SKIP_FILES = ("manifest.derived.json",)
SKIP_SUFFIXES = (".log", ".pyc")

#: Run directories under `runs/` that are deliberately NOT exported, each with the reason. The
#: public README's "What is not shipped" table is written from the same facts. A run directory
#: that is neither here nor complete is HELD and reported; one that is complete ships. Adding a
#: run to the public tree is therefore the default, and keeping one back is the decision that
#: has to be written down.
NOT_SHIPPED = {
    "refusal-ablation":
        "carries 450 verbatim XSTest prompts (Roettger et al.), a third party's text",
    "test-refusal": "empty scratch directory, no records",
    "2026-05-26": "empty directory left by a May collector; the May runs are under data/",
    "2026-09-08-evidence-collector-fake":
        "development fixture: a fake backend for the collector's interruption/retry tests",
    "2026-09-08-evidence-qwen-pilot":
        "evidence-use pilot of a different design, on one model",
    "2026-09-08-evidence-review-export-01":
        "offline exporter output for pack review, not a model measurement",
    "2026-09-08-residency-smoke-01": "residency smoke that returned no records",
    "2026-09-08-residency-smoke-02": "residency smoke that returned no records",
    "2026-09-08-residency-smoke-03": "residency smoke that returned no records",
    "2026-09-08-residency-smoke-04": "residency smoke that returned no records",
    "2026-09-08-residency-smoke-05": "residency smoke that returned no records",
}

#: Directories under `withdrawn/` that ship with the corpus because `data/withdrawals.json`
#: cites them as evidence. Both hold sheets on the author's own instrument.
EVIDENCE_DIRS = (
    os.path.join("withdrawn", "backend-split-precollection"),
    os.path.join("withdrawn", "pre-repair-snapshots"),
)


def instrument_texts():
    """Third-party item strings held privately. Never written to the export.

    THE LIVE INSTRUMENT IS NOT IN THIS LIST, deliberately. The Ratchet battery is the author's
    own text and ships in full; putting it here would scrub the study's own instrument out of
    its own data release. What belongs here is text this repository is not entitled to
    republish -- XSTest's prompts.

    THE RETIRED QUESTIONNAIRE USED TO BE THE FIRST ENTRY, read from `withdrawn/compass-bank/`,
    which no longer exists: the retired corpus was purged on 2026-09-22 and nothing carrying
    that instrument is exported any more. The entry was removed rather than left pointing at a
    deleted file, because the loop used to `continue` past a missing source -- so a scrubber
    with nothing to scrub reported success exactly as loudly as one that scrubbed.
    `_no_retired_text_to_scrub` below is what makes the absence safe: it fails if a retired
    record ever reaches the export again, at which point the bank has to come back first.
    """
    texts = []
    for rel, key, field in (("data/xstest-prompts.json", "prompts", "prompt"),):
        path = os.path.join(STUDY, rel)
        if not os.path.exists(path):
            raise SystemExit("export_scrubbed: %s is missing; refusing to export an "
                             "unscrubbed release rather than skipping a source" % rel)
        payload = json.load(io.open(path, encoding="utf-8"))
        rows = payload[key] if isinstance(payload, dict) and key in payload else payload
        texts += [r[field] for r in rows if isinstance(r, dict) and r.get(field)]
    if not texts:
        raise SystemExit("export_scrubbed: instrument_texts() assembled 0 strings; a scrubber "
                         "with an empty pattern list passes every record it is handed")
    return texts


#: Instrument names the export is NOT entitled to republish and no longer holds the text for.
#: Matched case-insensitively against each record's `instrument` field.
#:
#: TAKEN FROM THE GATE, NOT RETYPED. A literal copy here would be a second list of retired
#: instrument names that `check_retired_instrument` then has to exempt -- and a file exempted
#: from the name scan is one missing argument from using those names as data, which is the
#: exact route by which the retired bank came back twice. Importing them means a marker added
#: to the gate is refused by the export in the same commit, and the export needs no exemption.
import check_retired_instrument as _CRI  # noqa: E402

RETIRED_IN_EXPORT = _CRI.RETIRED_MARKERS


def _no_retired_text_to_scrub(records):
    """Refuse to export a record whose instrument text this repository no longer holds.

    The scrubber can only redact text it can see. While the retired questionnaire's bank was
    in the tree, a record carrying that instrument could be exported and its item strings
    removed. The bank is gone, so such a record would now go out with its third-party
    sentences intact and every gate green -- the export's field of view narrower than its
    claim, which is the failure this study keeps paying for.
    """
    bad = {}
    for r in records:
        name = (r.get("instrument") or "").lower()
        for marker in RETIRED_IN_EXPORT:
            if marker in name:
                key = r.get("instrument")
                bad[key] = bad.get(key, 0) + 1
                break
    if bad:
        lines = ["export_scrubbed: %d record(s) carry an instrument whose text is no longer in "
                 "the tree to scrub:" % sum(bad.values())]
        for k in sorted(bad):
            lines.append("  %-60s %d record(s)" % (k, bad[k]))
        lines.append("Restore the bank under withdrawn/ or drop these records from the export.")
        raise SystemExit(chr(10).join(lines))


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


def scrub_record(rec, fingerprints, tally, drop_fields=DROP_FIELDS, battery=True):
    """Return a publishable copy, and record every field touched.

    `drop_fields` is a parameter so the DEFAULT export keeps `forcing_prompt`. On the author's
    own instrument that field is the study publishing what it measured; dropping it was
    correct only while the prompt carried someone else's licensed text. The per-field
    fingerprint scan below still runs either way, so keeping the prompt cannot smuggle a
    third-party item back in -- if one is there, the field is withheld and the export says so.

    `battery` records get the prompt's hash and length. The "withheld" note is written ONLY
    when the prompt is actually dropped: until 2026-09-25 it was written unconditionally, so
    every published sheet said its prompt was withheld while carrying it in full.
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

    prompt = rec.get("forcing_prompt") if battery else None
    if prompt:
        out["forcing_prompt_sha256"] = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        out["forcing_prompt_chars"] = len(prompt)
        if "forcing_prompt" in drop_fields:
            out["forcing_prompt_note"] = (
                "Instrument text withheld from THIS record because it carries third-party "
                "material. Rebuild the prompt from the published bank and this record's "
                "shuffle_seed, then check your reconstruction against this sha256.")
        else:
            # A note left by the pre-2026-09-25 exporter on a record whose prompt is present
            # must not survive a re-export.
            out.pop("forcing_prompt_note", None)
    return out


def _complete(path):
    """Is this run finished? A missing manifest means in-flight, not fine.

    A run with a collector manifest, a derived freeze, or a `raw/`+`scored/` layout is
    complete. A flat directory with neither is still collecting, and a half-copied collection
    in a public tree is worse than an absent one: it looks complete and nobody re-reads it.
    """
    if os.path.isfile(os.path.join(path, "manifest.json")):
        return True, "manifest present"
    if os.path.isfile(os.path.join(path, "manifest.derived.json")):
        return True, "no manifest; content frozen by derive_manifest"
    return False, "no manifest and no freeze -- treated as still collecting"


def _files(path):
    out = []
    for dp, dn, fn in os.walk(path):
        dn[:] = sorted(d for d in dn if d != "__pycache__")
        for f in sorted(fn):
            if f in SKIP_FILES or f.endswith(SKIP_SUFFIXES):
                continue
            out.append(os.path.join(dp, f))
    return out


def plan():
    """(shipped, not_shipped, held): what would leave this tree, and why the rest stays."""
    root = os.path.join(STUDY, SOURCE_ROOT)
    shipped, not_shipped, held = [], [], []
    for name in sorted(os.listdir(root)):
        path = os.path.join(root, name)
        if not os.path.isdir(path) or name.startswith(("_", ".")):
            continue
        if name in NOT_SHIPPED:
            not_shipped.append((name, NOT_SHIPPED[name]))
            continue
        ok, note = _complete(path)
        if not ok:
            held.append((name, note))
            continue
        shipped.append((SOURCE_ROOT + "/" + name, path, note))
    for rel in EVIDENCE_DIRS:
        path = os.path.join(STUDY, rel)
        if os.path.isdir(path):
            shipped.append((rel.replace(os.sep, "/"), path, "evidence cited by data/withdrawals.json"))
        else:
            held.append((rel.replace(os.sep, "/"), "evidence directory missing from this tree"))
    return shipped, not_shipped, held


def _write_text(dest, text):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with io.open(dest, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def export_dir(rel, src, out_root, fingerprints, tally, drop_fields, raw):
    """Export one directory whole. Returns per-directory counts."""
    counts = {"records": 0, "files": 0, "schemas": {}}
    for path in _files(src):
        sub = os.path.relpath(path, src).replace(os.sep, "/")
        dest = os.path.join(out_root, rel.replace("/", os.sep), sub.replace("/", os.sep))
        if path.endswith(".jsonl"):
            keep = []
            for line in io.open(path, encoding="utf-8"):
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                schema = rec.get("schema") or "(none)"
                battery = rec.get("schema") in SCHEMA_ACCEPTED
                if battery and rec.get("forcing_prompt"):
                    tally["with_prompt"] += 1
                raw.append(rec)
                keep.append(scrub_record(rec, fingerprints, tally, drop_fields, battery=battery))
                counts["schemas"][schema] = counts["schemas"].get(schema, 0) + 1
                counts["records"] += 1
                tally["records"] += 1
            if not keep:
                # A sheet file with no records is a collector that opened a file and wrote
                # nothing (eight such files sit in the wave). Not a sheet; not exported.
                continue
            text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in keep)
        else:
            text = io.open(path, encoding="utf-8", errors="replace").read()
            found = hits(text, fingerprints)
            if found:
                raise SystemExit("export_scrubbed: %s/%s carries instrument text (%s); a "
                                 "side file cannot be scrubbed field by field. Remove it or "
                                 "add the run to NOT_SHIPPED." % (rel, sub, found[0][:60]))
        _write_text(dest, text)
        # THE EXPORTED FILE KEEPS THE SOURCE'S TIMESTAMP. derive_manifest's live-window guard
        # reads mtimes to tell a finished run from one still being written; a copy stamped
        # "now" would read as collecting for the next fifteen minutes in the mirror.
        st = os.stat(path)
        os.utime(dest, (st.st_atime, st.st_mtime))
        counts["files"] += 1
        tally["files"] += 1
    return counts


def install(out_root, mirror, shipped):
    """Write the verified staging export over the mirror's directories. Never commits.

    FILE BY FILE, NOT rmtree-THEN-copytree. On 2026-09-25 the first version removed the
    mirror's wave directory while that tree's test suite had one sheet open; Windows refused
    the unlink, rmtree stopped half way, and the mirror was left with 86 of 441 files and no
    manifest until the export was re-run. Overwriting each file in place cannot leave that
    state: a file that cannot be replaced is reported and the rest of the directory is still
    whole. Files in the mirror that the staging export does not carry are removed afterwards,
    and a removal that fails is reported rather than fatal. Do not export while another
    process is reading the mirror.
    """
    replaced, stuck = [], []
    for rel, _src, _note in shipped:
        src = os.path.join(out_root, rel.replace("/", os.sep))
        dest = os.path.join(mirror, rel.replace("/", os.sep))
        wanted = set()
        for path in _files(src):
            sub = os.path.relpath(path, src)
            wanted.add(sub)
            target = os.path.join(dest, sub)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            try:
                shutil.copy2(path, target)
            except OSError as exc:
                stuck.append((rel + "/" + sub.replace(os.sep, "/"), "copy: %s" % exc))
        if os.path.isdir(dest):
            for dp, dn, fn in os.walk(dest):
                dn[:] = [d for d in dn if d != "__pycache__"]
                for f in fn:
                    sub = os.path.relpath(os.path.join(dp, f), dest)
                    # The mirror's own per-tree freeze stays; it is regenerated there, never
                    # shipped from here.
                    if sub in wanted or f in SKIP_FILES:
                        continue
                    try:
                        os.remove(os.path.join(dp, f))
                    except OSError as exc:
                        stuck.append((rel + "/" + sub.replace(os.sep, "/"), "remove: %s" % exc))
        replaced.append(rel)
    if stuck:
        print("INSTALL INCOMPLETE -- %d file(s) could not be written or removed:" % len(stuck))
        for rel, why in stuck[:20]:
            print("   %s  (%s)" % (rel, why))
        print("Close whatever holds them and re-run; nothing else in the mirror was skipped.")
        return replaced, [], stuck
    for rel in ("MANIFEST.json", os.path.join("data", "controls-audit.json")):
        src = os.path.join(out_root, rel)
        dest = os.path.join(mirror, rel)
        if not os.path.exists(src):
            continue
        if os.path.exists(dest):
            # A REWRITE THAT CHANGES ONLY THE FORMATTING IS NOISE: json.dump's layout is not
            # the file's content, and an 800-line diff of reflowed JSON hides the one line
            # that matters on the day a redaction actually moves.
            try:
                same = (json.load(io.open(src, encoding="utf-8"))
                        == json.load(io.open(dest, encoding="utf-8")))
            except ValueError:
                same = False
            if same:
                continue
        shutil.copy2(src, dest)
    # A MIRROR DIRECTORY THE PLAN DOES NOT NAME IS REPORTED, NOT DELETED. It may be a run the
    # mirror ships from another export, or a leftover; either way a person decides.
    mirror_root = os.path.join(mirror, SOURCE_ROOT)
    planned = {rel.split("/", 1)[1] for rel in replaced if rel.startswith(SOURCE_ROOT + "/")}
    stray = sorted(d for d in os.listdir(mirror_root)
                   if os.path.isdir(os.path.join(mirror_root, d))
                   and not d.startswith(("_", ".")) and d not in planned)
    return replaced, stray, []


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=os.path.join("export", "battery"),
                    help="staging directory, relative to the study; must not exist")
    ap.add_argument("--into", default=None, metavar="MIRROR",
                    help="after verification, write the export over this mirror's runs/, "
                         "withdrawn/ evidence directories and MANIFEST.json")
    ap.add_argument("--plan", action="store_true", help="list what would ship; write nothing")
    ap.add_argument("--scrub", action="store_true",
                    help="drop %s from every record. The pre-2026-09-17 behaviour, correct "
                         "while the prompt carried licensed third-party text. The live "
                         "instrument is the author's and ships in full, so the default now "
                         "KEEPS the prompt -- the per-field fingerprint scan runs either way."
                         % ", ".join(DROP_FIELDS))
    ap.add_argument("--fingerprints", default=DEFAULT_FINGERPRINTS)
    ap.add_argument("--audit-only", action="store_true",
                    help="scan every shipped record and report; write nothing")
    args = ap.parse_args(argv)

    shipped, not_shipped, held = plan()
    print("EXPORT PLAN from %s/" % SOURCE_ROOT)
    for rel, _src, note in shipped:
        print("  ship  %-48s %s" % (rel, note))
    for name, why in not_shipped:
        print("  keep  %-48s %s" % (name, why))
    for name, why in held:
        print("  HELD  %-48s %s" % (name, why))
    if not shipped:
        print("nothing to ship -- this is not a pass; check %s/" % SOURCE_ROOT)
        return 1
    if args.plan:
        return 0

    fingerprints = load_fingerprints(args.fingerprints)
    drop_fields = DROP_FIELDS if args.scrub else ()
    print("oracle: %d fingerprints from %s"
          % (len(fingerprints), os.path.relpath(args.fingerprints, STUDY)))
    print("prompt: %s"
          % ("DROPPED (--scrub)" if drop_fields
             else "kept -- the instrument is the author's and ships with the paper"))

    out_root = os.path.join(STUDY, args.out)
    if not args.audit_only and os.path.exists(out_root):
        raise SystemExit('output already exists: %s; choose a fresh export path'
                         % os.path.relpath(out_root, STUDY))
    if args.into and not os.path.isdir(os.path.join(args.into, SOURCE_ROOT)):
        raise SystemExit("--into %s has no %s/ root" % (args.into, SOURCE_ROOT))

    tally = {"records": 0, "files": 0, "with_prompt": 0, "scrubbed_fields": {}}
    raw = []
    if args.audit_only:
        import tempfile
        out_root = tempfile.mkdtemp(prefix="export-audit-")
    per_dir = {}
    for rel, src, _note in shipped:
        per_dir[rel] = export_dir(rel, src, out_root, fingerprints, tally, drop_fields, raw)

    # Checked on the RAW records, before anything is kept: a record whose instrument text
    # this repository no longer holds cannot be scrubbed, so it must not be exported at all.
    _no_retired_text_to_scrub(raw)

    print("scanned %d records in %d file(s) across %d directory(ies); %d battery records "
          "carried the instrument" % (tally["records"], tally["files"], len(per_dir),
                                       tally["with_prompt"]))
    if tally["scrubbed_fields"]:
        print("fields emptied because they contained instrument text:")
        for k, v in sorted(tally["scrubbed_fields"].items()):
            print("   %-18s %d record(s)" % (k, v))
    else:
        print("no retained field contained instrument text")

    if args.audit_only:
        shutil.rmtree(out_root, ignore_errors=True)
        return 0

    inst = instrument_hashes()
    manifest = {
        "schema": "battery-export/2",
        "source_root": SOURCE_ROOT + "/",
        "source_schema": SCHEMA,
        "generated_by": "scripts/export_scrubbed.py",
        "instrument": ("The Ratchet battery (data/ratchet-battery.json): 32 forced-choice "
                       "items in 16 mirrored pairs, written by Ian Gorrie, MIT-licensed with "
                       "the rest of the repository. The item text SHIPS -- there is no fetch "
                       "step and no carve-out."),
        "instrument_canonical_sha256": inst["canonical"],
        "instrument_normalized_sha256": inst["normalized"],
        "instrument_hash_note": (
            "canonical = byte-exact item set; normalized = same after folding curly quotes, "
            "dashes and entities to ASCII. `forcing_prompt_sha256` on each battery record is "
            "the hash of that record's own prompt as sent."),
        "records": tally["records"],
        "files": tally["files"],
        "directories": {rel: per_dir[rel] for rel, _s, _n in shipped},
        "not_shipped": dict(NOT_SHIPPED),
        "held": dict(held),
        "dropped_fields": list(drop_fields),
        "scrubbed_fields": tally["scrubbed_fields"],
        "verification": ("Every written file was re-scanned against the release repo's "
                         ".corpus-fingerprint list and its hashed n-gram oracle after "
                         "writing; the exporter exits 1 if anything survives."),
    }
    _write_text(os.path.join(out_root, "MANIFEST.json"),
                json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")

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
        print("Do not treat this export as clean. Generate .corpus-fingerprint-hashed and re-run.")
        return 1
    print("The answers are keyed by item id, so every published number recomputes from this.")
    print("The instrument ships with the paper: data/ratchet-battery.json, 32 items, MIT.")

    if args.into:
        replaced, stray, stuck = install(out_root, args.into, shipped)
        if stuck:
            return 1
        print()
        print("installed %d directory(ies) and MANIFEST.json into %s" % (len(replaced), args.into))
        if stray:
            print("mirror %s/ directories NOT in this plan, left untouched:" % SOURCE_ROOT)
            for d in stray:
                print("   %s" % d)
        print("Next, IN THE MIRROR: derive_manifest.py --write (its freezes are per tree), then "
              "gen_provenance.py --write, gen_corpus_docs.py, gen_data_dictionary.py.")
        print("Nothing is committed. Review `git status` there; the pre-commit corpus gate runs "
              "on commit.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
