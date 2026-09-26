#!/usr/bin/env python3
"""Generate `.zenodo.json` from CITATION.cff, and gate what a Release will mint.

WHY THIS FILE EXISTS, AND IT IS NOT HYPOTHETICAL
------------------------------------------------
The Zenodo GitHub integration on `gorrie/bias-study` is LIVE. It has minted once already --
concept DOI 10.5281/zenodo.22719011, version DOI 10.5281/zenodo.22719012 (release-2026-09-12) --
and the title on that record was

    "The Hedge Is the Bias: A Multi-Vendor, Multi-Generation Audit of LLM
     Institutional-Skepticism Framing"

which is FINDINGS #13 -- a claim this study withdrew on 2026-09-13 and registered in
`key_numbers.RETRACTED`. The author deleted that record on 2026-09-22 (Zenodo allows an owner
30 days), so it resolves to a tombstone and no DOI is live today. The next Release therefore
mints a FRESH concept DOI -- one chance, no prior version to hide a bad title behind.

That happened because there was no `.zenodo.json` in the repository, so Zenodo fell back to
the GitHub repo's own description -- which still advertises "three force-escalation rungs"
and "five judging methods", both retired. **Zenodo reads `.zenodo.json` in preference to
CITATION.cff, and it reads whatever is in the tarball at the moment the Release is created.**
So the metadata has to be committed BEFORE the Release, not fixed after it.

With the old record gone there is no prior version to sit behind: the next Release is the
study's first live DOI and whatever this file says becomes its permanent metadata.

WHAT THIS DOES
--------------
Derives `.zenodo.json` from `CITATION.cff` so the two cannot disagree -- one fact, one
source (LEARNINGS #10). `--check` fails when the generated file differs from the one on
disk, when either is missing from the tree that SHIPS, or when the title is a withdrawn one.

    python scripts/gen_zenodo.py                 # write it into the mirror
    python scripts/gen_zenodo.py --check         # gate: is what would mint correct?
    python scripts/gen_zenodo.py --show          # print it without writing

Reads only, unless asked to write. No API calls, no Zenodo credentials: this decides what
WOULD mint, and minting stays a deliberate human act.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, HERE)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

#: The tree that SHIPS -- github.com/gorrie/bias-study, where the Zenodo integration mints
#: on Release. A citation record correct only in the private tree is one a reader never sees.
#:
#: RESOLVED, NOT ASSEMBLED FROM dirname() CALLS. The first version counted two levels up from
#: `research/bias-study` and landed on `evil-robots-series/bias-study-release` -- a directory
#: that did not exist, which `os.makedirs` then created INSIDE the study repo, one `git add`
#: away from committing the citation record to the wrong repository. A path built by counting
#: separators is a path nobody checks; this one is searched for and then verified to be the
#: mirror by something only the mirror has.
def _find_mirror():
    here = STUDY
    for _ in range(5):
        here = os.path.dirname(here)
        if not here:
            break
        candidate = os.path.join(here, "bias-study-release")
        if os.path.isdir(os.path.join(candidate, "scripts")) and \
           os.path.isdir(os.path.join(candidate, ".git")):
            return candidate
    return None


MIRROR = _find_mirror()

#: Titles that must never reach a DOI again. Keyed loosely: the point is the claim, not the
#: punctuation. `check_citation.WITHDRAWN_TITLES` holds the same list for the .cff side.
WITHDRAWN_TITLE_MARKERS = (
    "the hedge is the bias",
    "same version, different answers",
)

#: Zenodo's controlled vocabulary. `mit-license` is what the existing record carries.
ZENODO_LICENSE = "mit-license"
#: A PREPRINT, not a dataset: the record is the paper with its data and code attached, and a
#: publication record is what Google Scholar and OpenAIRE index as a paper.
UPLOAD_TYPE = "publication"
PUBLICATION_TYPE = "preprint"


def _cff(path):
    """The handful of CITATION.cff fields this needs. Not a YAML parser -- a reader.

    Deliberately narrow: pulling in a YAML dependency for six fields would put a parser
    between the release gate and the file it guards, and this file's whole job is to have
    nothing between them.
    """
    text = io.open(path, encoding="utf-8").read()
    # Strip comment-only lines so a commented-out `date-released` is not read as set.
    body = "\n".join(l for l in text.split("\n") if not l.lstrip().startswith("#"))

    def block(name):
        # BLANK LINES ARE PART OF THE BLOCK. `(?:[ \t]+.*\n?)+` stops at the first empty
        # line, so a five-paragraph YAML folded block returned PARAGRAPH ONE -- and the
        # abstract is five paragraphs. Measured 2026-09-21: `.zenodo.json` carried 267 of
        # 2,993 characters and this file's own --check reported "fit to mint" over it,
        # because it compared the truncated output against a regeneration of the same
        # truncation. A Zenodo description is permanent metadata; it would have minted as
        # the first paragraph and nothing downstream would have said so.
        m = re.search(r"^%s:\s*>-\s*\n((?:(?:[ \t]+.*)?\n)+)" % re.escape(name), body, re.M)
        if m:
            # Stop at the first line that is neither indented nor blank -- i.e. the next key.
            lines = []
            for line in m.group(1).split("\n"):
                if line and not line[:1].isspace():
                    break
                lines.append(line)
            joined = " ".join(" ".join(lines).split())
            if joined:
                return joined
        m = re.search(r"^%s:\s*(.+)$" % re.escape(name), body, re.M)
        return m.group(1).strip().strip('"').strip("'") if m else None

    authors = []
    for m in re.finditer(
            r"-\s*family-names:\s*(.+?)\n\s*given-names:\s*(.+?)\n"
            r"(?:\s*orcid:\s*\"?(.+?)\"?\n)?(?:\s*affiliation:\s*(.+?)\n)?",
            body):
        family, given, orcid, affil = (g.strip() if g else None for g in m.groups())
        authors.append({"family": family, "given": given, "orcid": orcid,
                        "affiliation": affil})
    return {
        "title": block("title"),
        "abstract": block("abstract"),
        "license": block("license"),
        "version": block("version"),
        "doi": block("doi"),
        "repository": block("repository-code"),
        "keywords": re.findall(r"^\s*-\s+(.+)$", (re.search(
            r"^keywords:\s*\n((?:\s*-\s+.+\n?)+)", body, re.M) or
            type("x", (), {"group": lambda *_: ""})()).group(1) or "", re.M),
        "authors": authors,
    }


def build():
    """The .zenodo.json payload, derived. Returns (payload, problems)."""
    problems = []
    cff_path = os.path.join(STUDY, "CITATION.cff")
    if not os.path.exists(cff_path):
        return None, ["no CITATION.cff in %s -- nothing to derive from" % STUDY]
    c = _cff(cff_path)

    if not c["title"]:
        problems.append("CITATION.cff has no title")
    else:
        low = c["title"].lower()
        for marker in WITHDRAWN_TITLE_MARKERS:
            if marker in low:
                problems.append("TITLE IS WITHDRAWN: %r contains %r -- this is what is "
                                "already on 10.5281/zenodo.22719012 and must not mint again"
                                % (c["title"], marker))
    if not c["abstract"]:
        problems.append("CITATION.cff has no abstract; Zenodo would fall back to the GitHub "
                        "repo description, which still advertises the retired three-rung "
                        "design")
    else:
        # THE TRUNCATION CHECK, because a parser bug here is invisible to every other gate.
        # `_cff` read the abstract with a pattern that stopped at the first blank line and
        # returned paragraph one of five -- 267 characters of 2,993 -- and `--check` passed,
        # because it compared the truncated file against a fresh truncation. Nothing
        # downstream reads a Zenodo description, so the only way to catch it is to compare
        # what was extracted against the raw bytes it came from.
        raw = io.open(cff_path, encoding="utf-8").read()
        m = re.search(r"^abstract:\s*>-\s*\n((?:(?:[ \t]+.*)?\n)+?)(?=^\S)", raw, re.M)
        if m:
            raw_chars = len(" ".join(m.group(1).split()))
            got = len(c["abstract"])
            if raw_chars and got < 0.9 * raw_chars:
                problems.append(
                    "ABSTRACT TRUNCATED: extracted %d characters from a %d-character block "
                    "in CITATION.cff. Zenodo keeps the description permanently; a parser "
                    "that stops early mints a fragment." % (got, raw_chars))
    if (c["license"] or "").upper() != "MIT":
        problems.append("CITATION.cff license is %r, expected MIT" % c["license"])
    creators = []
    for a in c["authors"]:
        if not a["family"] or not a["given"]:
            problems.append("an author entry is missing a name")
            continue
        rec = {"name": "%s, %s" % (a["family"], a["given"])}
        if a["affiliation"]:
            rec["affiliation"] = a["affiliation"]
        if a["orcid"]:
            rec["orcid"] = a["orcid"].rsplit("/", 1)[-1]
        else:
            # THE EXISTING RECORD HAS NO ORCID. A DOI without one does not connect to the
            # author's other work and cannot be disambiguated from anyone of the same name.
            problems.append("author %s has no ORCID; 10.5281/zenodo.22719012 was minted "
                            "without one and that record cannot be joined to any other"
                            % rec["name"])
        creators.append(rec)
    if not creators:
        problems.append("no creators -- Zenodo would attribute this to the GitHub account "
                        "that pushed the tag")

    payload = {
        "title": c["title"],
        "description": c["abstract"],
        "upload_type": UPLOAD_TYPE,
        "publication_type": PUBLICATION_TYPE,
        "license": ZENODO_LICENSE,
        "creators": creators,
        "keywords": [k.strip() for k in c["keywords"] if k.strip()],
        "related_identifiers": [
            {"identifier": c["repository"] or "https://github.com/gorrie/bias-study",
             "relation": "isSupplementTo", "scheme": "url"},
        ],
    }
    return payload, problems


def render(payload):
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--path", default=None,
                    help="where .zenodo.json lives (default: the mirror)")
    a = ap.parse_args(argv)

    payload, problems = build()
    if not a.path and MIRROR is None:
        print("REFUSED -- cannot find the shipping tree (a sibling `bias-study-release` with")
        print("scripts/ and .git/). Refusing rather than creating one: an earlier version of")
        print("this script built the path by counting directory separators, missed, and made")
        print("a new directory inside the STUDY repo -- one `git add` from committing the")
        print("citation record to the wrong repository. Pass --path to be explicit.")
        return 2
    dest = a.path or os.path.join(MIRROR, ".zenodo.json")

    if payload is None:
        print("REFUSED -- %s" % problems[0])
        return 2
    if a.show:
        print(render(payload))
        return 0

    if a.check:
        print("")
        print("  WHAT THE NEXT GITHUB RELEASE WOULD MINT")
        print("  No DOI is live for this study: the 2026-09-12 record was deleted by its")
        print("  owner on 2026-09-22 and the badge endpoint now 500s, so the next Release")
        print("  mints a FRESH concept DOI from this metadata -- permanently, first time.")
        print("")
        print("  title    : %s" % (payload["title"] or "(none)"))
        print("  creators : %s" % ", ".join(
            "%s%s" % (c["name"], " [%s]" % c["orcid"] if c.get("orcid") else " [NO ORCID]")
            for c in payload["creators"]) or "(none)")
        print("  license  : %s" % payload["license"])
        print("")
        if not os.path.exists(dest):
            problems.append("%s does not exist. Zenodo reads it in preference to "
                            "CITATION.cff and falls back to the GitHub repo description "
                            "when it is absent -- which is how the withdrawn title reached "
                            "10.5281/zenodo.22719012." % os.path.relpath(dest, MIRROR))
        else:
            on_disk = io.open(dest, encoding="utf-8").read()
            if on_disk != render(payload):
                problems.append("%s differs from what CITATION.cff derives. Run "
                                "gen_zenodo.py to refresh it."
                                % os.path.relpath(dest, MIRROR))
        cff_mirror = os.path.join(MIRROR, "CITATION.cff")
        if not os.path.exists(cff_mirror):
            problems.append("no CITATION.cff in the tree that SHIPS (%s). A reader there "
                            "concludes none exists." % MIRROR)
        if problems:
            print("  REFUSED -- %d problem(s). A Release would mint this permanently."
                  % len(problems))
            for p in problems:
                print("    - %s" % p)
            return 1
        print("  fit to mint: .zenodo.json matches CITATION.cff, both are in the shipping")
        print("  tree, the title is not a withdrawn one, and the author carries an ORCID.")
        return 0

    os.makedirs(os.path.dirname(dest), exist_ok=True)
    io.open(dest, "w", encoding="utf-8", newline="\n").write(render(payload))
    print("wrote %s" % dest)
    if problems:
        print("WITH %d PROBLEM(S) -- written so they are visible, not silently withheld:"
              % len(problems))
        for p in problems:
            print("  - %s" % p)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
