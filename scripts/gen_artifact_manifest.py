#!/usr/bin/env python3
"""Checksum the large binaries the study depends on, so they can travel outside git.

WHY. The weight rung rests on ~100 GB of model weights: one base and five abliterations of it.
Those do not belong in a git repository -- 17 GB of them reached a staging branch's history on
2026-09-20 because `.gitignore` said `abliteration-output/` and the pinned-revision builds were
`abliteration-output-d6af36f/` and `-t205d28a/`. They also cannot simply be dropped, because
without them the weight-rung results are unreproducible and this study's whole argument is that
a result you cannot recompute is not a result.

The split: **the bytes travel out of band** (a torrent alongside the release), **the repository
carries what makes a download checkable** -- per-file SHA-256, a directory digest, size, and the
build provenance. A reader who fetches the artifacts can prove they hold what the study used,
which is the same guarantee `MANIFEST.json` gives for the scrubbed corpus.

Hashing 100 GB is slow, so results are CACHED by (path, size, mtime) and only changed files are
re-read. `--check` re-verifies and exits 1 on any drift.

    python scripts/gen_artifact_manifest.py            # write ARTIFACTS.md + artifacts.json
    python scripts/gen_artifact_manifest.py --check    # verify against disk

No API calls. Reads bytes already on disk.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
def _mirror() -> str:
    """Where the large artifacts live. Resolved by EXISTENCE, never by counting dirnames.

    The first version walked three dirname() levels from STUDY and landed one short, in
    `book/`, so it found two directories with no weights in them and wrote a manifest claiming
    "2 artifacts, 0 GB" -- a confident, wrong, and entirely plausible-looking answer. A path
    computed by arithmetic and not checked is the same defect as a number typed into a document.
    """
    here = os.path.abspath(STUDY)
    for _ in range(6):
        here = os.path.dirname(here)
        cand = os.path.join(here, "gorrie", "bias-study")
        if os.path.isdir(cand):
            return cand
    link = os.path.join(os.path.dirname(os.path.dirname(STUDY)), "bias-study-release")
    return os.path.realpath(link) if os.path.isdir(link) else STUDY


MIRROR = _mirror()

CACHE = os.path.join(STUDY, ".artifact-hash-cache.json")
OUT_MD = os.path.join(STUDY, "ARTIFACTS.md")
OUT_JSON = os.path.join(STUDY, "artifacts.json")

#: The artifacts a reader needs to reproduce the weight rung, and why each is here.
#: A directory is listed only if the study cites a result computed from it.
ARTIFACTS = [
    ("models/gemma-2-9b-it", "base", "the unmodified subject; every ablation below is derived from it"),
    ("abliteration-output/gemma-2-9b-it-dose2", "ablation n=2", "dose series arm, built 2026-06-09 at OBLITERATUS d6af36f"),
    ("abliteration-output/gemma-2-9b-it-abliterated", "ablation n=4", "dose series arm; ALSO the 2026-05-27 build reused as dose4 -- see RESULTS-2026-09-18 C1"),
    ("abliteration-output/gemma-2-9b-it-dose8", "ablation n=8", "dose series arm, built 2026-06-09 at d6af36f"),
    ("abliteration-output/gemma-2-9b-it-dose1-tool205d28a", "ablation n=1", "built 2026-09-19 at 205d28a; the only n=1 that builds"),
    ("abliteration-output-t205d28a/gemma-2-9b-it-dose2", "ablation n=2 (205d28a)", "same-tool pair with the n=1 above"),
]

#: Builds that FAILED and are kept only as metadata, never as weights. The failure is the
#: finding -- see RESULTS-2026-09-19-dose-response.md section 3 -- and a destroyed model is not
#: worth 17 GB of anyone's bandwidth.
METADATA_ONLY = [
    ("evidence/abliteration-builds/n1-FAILED-d6af36f.json", "n=1 at d6af36f: perplexity inf, coherence 0.0"),
    ("evidence/abliteration-builds/n1-FAILED-04b8ec6.json", "n=1 at 04b8ec6: perplexity inf, coherence 0.0"),
]


def load_cache():
    try:
        return json.load(io.open(CACHE, encoding="utf-8"))
    except Exception:
        return {}


def sha256(path, cache):
    st = os.stat(path)
    key = f"{path}|{st.st_size}|{int(st.st_mtime)}"
    if key in cache:
        return cache[key], True
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 22), b""):
            h.update(chunk)
    cache[key] = h.hexdigest()
    return cache[key], False


def scan(rel, cache):
    root = os.path.join(MIRROR, rel)
    if not os.path.isdir(root):
        return None
    files, total = [], 0
    for dirpath, _, names in os.walk(root):
        for n in sorted(names):
            if n.startswith("."):
                continue
            p = os.path.join(dirpath, n)
            digest, cached = sha256(p, cache)
            size = os.path.getsize(p)
            total += size
            files.append({"path": os.path.relpath(p, root), "bytes": size, "sha256": digest})
    files.sort(key=lambda f: f["path"])
    # Directory digest: the hash of the sorted "sha256  path" listing. Stable across filesystems
    # and independent of mtime, so two people can compare one string instead of hundreds.
    listing = "\n".join(f"{f['sha256']}  {f['path']}" for f in files)
    return {"files": files, "bytes": total,
            "dir_sha256": hashlib.sha256(listing.encode()).hexdigest()}


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)

    cache = load_cache()
    entries, missing = [], []
    for rel, kind, why in ARTIFACTS:
        got = scan(rel, cache)
        if got is None:
            missing.append(rel)
            continue
        entries.append({"path": rel, "kind": kind, "why": why, **got})
        print(f"  {rel:56s} {got['bytes']/2**30:6.1f} GB  {got['dir_sha256'][:16]}")
    json.dump(cache, io.open(CACHE, "w", encoding="utf-8"))

    if not entries:
        print("no artifacts found -- refusing to write an empty manifest")
        return 1
    total_gb = sum(a["bytes"] for a in entries) / 2**30
    if total_gb < 1.0:
        print(f"found {len(entries)} artifact(s) totalling {total_gb:.2f} GB under {MIRROR}")
        print("REFUSING to write: these are model weights and should be tens of GB. A manifest "
              "that silently describes the wrong directory is worse than none.")
        return 1

    doc = {"generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "note": ("These artifacts are distributed OUT OF BAND, not in git. The repository "
                    "carries these checksums so a download can be proven identical to what the "
                    "study used."),
           "artifacts": entries,
           "metadata_only": [{"path": p, "why": w} for p, w in METADATA_ONLY],
           "missing_locally": missing}

    if args.check:
        old = json.load(io.open(OUT_JSON, encoding="utf-8")) if os.path.exists(OUT_JSON) else {}
        o = {a["path"]: a["dir_sha256"] for a in old.get("artifacts", [])}
        n = {a["path"]: a["dir_sha256"] for a in entries}
        drift = [k for k in set(o) & set(n) if o[k] != n[k]]
        gone = [k for k in o if k not in n]
        if drift or gone:
            for k in drift:
                print(f"DRIFT: {k}")
            for k in gone:
                print(f"ABSENT: {k}")
            return 1
        print(f"{len(n)} artifact(s) match the manifest")
        return 0

    total = sum(a["bytes"] for a in entries)
    md = ["# Large artifacts", "",
          "<!-- GENERATED by scripts/gen_artifact_manifest.py -- do not edit by hand. -->", "",
          "The weight rung rests on model weights far too large for a git repository. **The bytes",
          "are distributed out of band; this file is how you prove you got the right ones.**",
          "",
          f"**{len(entries)} artifacts, {total/2**30:.0f} GB total.** Each directory digest is the",
          "SHA-256 of its own sorted `sha256  path` listing, so two people compare one string",
          "rather than hundreds of files, and the value does not depend on timestamps or",
          "filesystem ordering.", "",
          "| artifact | role | size | directory SHA-256 |", "|---|---|---:|---|"]
    for a in entries:
        md.append(f"| `{a['path']}` | {a['kind']} | {a['bytes']/2**30:.1f} GB | `{a['dir_sha256'][:32]}…` |")
    md += ["", "Per-file checksums are in `artifacts.json`. Verify a download with:", "",
           "```bash", "python scripts/gen_artifact_manifest.py --check", "```", "",
           "## Kept as metadata only", "",
           "Builds that failed their smoke gate. The failure is the finding; a destroyed model is",
           "not worth anyone's bandwidth.", ""]
    for p, w in METADATA_ONLY:
        md.append(f"- `{p}` — {w}")
    if missing:
        md += ["", "## Not present on this machine", ""]
        md += [f"- `{m}`" for m in missing]
    md.append("")

    io.open(OUT_MD, "w", encoding="utf-8", newline="\n").write("\n".join(md))
    json.dump(doc, io.open(OUT_JSON, "w", encoding="utf-8"), indent=2)
    print(f"\nwrote ARTIFACTS.md and artifacts.json — {len(entries)} artifacts, {total/2**30:.0f} GB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
