#!/usr/bin/env python3
"""Write a repaired corpus the ANALYSIS can actually read.

WHY THIS FILE EXISTS
--------------------
`splice_holes.py` reports how many cells a re-collection WOULD recover. Nothing
acted on that report. `ci_analysis.py`, `aggregate.py`, `analysis.py` and
`drift_timeseries.py` all read one run directory, so the re-collected records sat
in `2026-09-05-recollect` and no published number moved because of them.

That gap would have made the whole repair pointless: the cells were paid for,
collected, scored, and then read by nothing.

WHAT THIS DOES, AND WHAT IT REFUSES TO DO
-----------------------------------------
It writes a NEW DATED RUN. It does not modify the base run, and no reader asking
for `2026-05-25-full` is silently handed something else -- a transparent
substitution would be worse than the gap, because then nobody could tell which
corpus a number came from.

For every cell the base attempted:
  * the base record, when it is eligible;
  * otherwise the first ELIGIBLE record for that cell from a splice source,
    stamped with `spliced_from` and `spliced_replaces` so its provenance travels
    with it;
  * otherwise the base record as-is, still ineligible, still excluded downstream.
    A hole that was not repaired stays a hole and is counted as one.

The output is therefore a superset in usable cells and identical in shape, and
every substituted record says so in its own fields.

    python scripts/splice_corpus.py --plan          # what would change, writes nothing
    python scripts/splice_corpus.py --write         # write the spliced run
    python scripts/splice_corpus.py --write --out 2026-09-14-full-spliced
"""
from __future__ import annotations

import argparse
import collections
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import eligibility as E  # noqa: E402
from studypaths import run_roots  # noqa: E402

#: Every damaged corpus, the repair runs that feed it, and the derived corpus it
#: produces. A base may have MORE THAN ONE source: GPT-5 was repaired separately
#: because its damage sits below the at-cap threshold the general repair used, so
#: the augmentation corpus draws from two runs.
#:
#: Sources are tried in order and the FIRST eligible record wins, so the order is
#: deliberate rather than incidental.
CORPUS_REPAIRS = {
    "2026-05-25-full": {
        "sources": ("2026-09-05-recollect",),
        "out": "2026-09-14-full-spliced",
    },
    "2026-05-26-timeseries": {
        "sources": ("2026-09-14-recollect-timeseries",),
        "out": "2026-09-14-timeseries-spliced",
    },
    "2026-05-26-cn-expansion": {
        "sources": ("2026-09-14-recollect-cn",),
        "out": "2026-09-14-cn-expansion-spliced",
    },
    "2026-05-26-augmentation": {
        "sources": ("2026-09-14-recollect-augmentation",
                    "2026-09-14-recollect-gpt5-augmentation"),
        "out": "2026-09-14-augmentation-spliced",
    },
    # The gradient run carries the book's dose-response curve and the variance run
    # carries the same-version floor. Neither was in the "main four" I first
    # scoped, and both feed published numbers -- which is the only boundary that
    # matters. GPT-5 was repaired separately in each, so both draw two sources.
    "2026-05-26-unmask-gradient": {
        "sources": ("2026-09-14-recollect-gradient",
                    "2026-09-14-recollect-gpt5-gradient"),
        "out": "2026-09-14-unmask-gradient-spliced",
    },
    "2026-05-26-variance": {
        "sources": ("2026-09-14-recollect-variance",
                    "2026-09-14-recollect-gpt5-variance"),
        "out": "2026-09-14-variance-spliced",
    },
    # `2026-05-25` is the EARLIER main run and a different directory from
    # `2026-05-25-full` above -- one character apart, two collections. The
    # repair's own records name it in `recollected_from`, which is the only
    # reason this entry is keyed correctly: guessing from the repair's name
    # ("recollect-may25") would have pointed it at the -full run and spliced a
    # repair into a corpus it did not repair.
    "2026-05-25": {
        "sources": ("2026-09-14-recollect-may25",),
        "out": "2026-09-14-may25-spliced",
    },
    # The out-of-domain arm. Its repair is the one that tripped the differential-
    # truncation blocker at 85.7% on llama-4-maverick, which turned out to be
    # nine complete answers ending in a closed LaTeX box -- see
    # eligibility.looks_truncated_text.
    "2026-05-27-ood": {
        "sources": ("2026-09-14-recollect-ood",),
        "out": "2026-09-14-ood-spliced",
    },
    # The instruction-paraphrase floor and the frame-following arm. Both repairs
    # were collected on 2026-09-14 and then sat unscored for a day -- the repair
    # sequence is collect, check, score, splice, register, and stopping after
    # step two leaves records that cost money and are read by nothing.
    "2026-05-27-paraphrase": {
        "sources": ("2026-09-14-recollect-paraphrase",),
        "out": "2026-09-15-paraphrase-spliced",
    },
    "2026-05-27-reversed-premise": {
        "sources": ("2026-09-14-recollect-reversed-premise",),
        "out": "2026-09-15-reversed-premise-spliced",
    },
}

BASE = "2026-05-25-full"
SPLICE_SOURCES = CORPUS_REPAIRS[BASE]["sources"]
DEFAULT_OUT = CORPUS_REPAIRS[BASE]["out"]


def key(r):
    return (r.get("model"), r.get("question_id"), r.get("condition"))


def _run_dir(name, sub="scored"):
    for root in run_roots():
        d = root / name / sub
        if d.is_dir():
            return d
    return None


def load(name, sub="scored"):
    d = _run_dir(name, sub)
    if d is None:
        return []
    rows = []
    for p in sorted(glob.glob(os.path.join(str(d), "**", "*.jsonl"), recursive=True)):
        with io.open(p, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except ValueError:
                        pass
    return rows


def build(base_name=BASE, sources=SPLICE_SOURCES):
    """Return (records, stats). Pure -- writes nothing."""
    base = load(base_name)
    if not base:
        return [], {"error": "base run %s not found or empty" % base_name}

    repairs = {}
    per_source = collections.Counter()
    for src in sources:
        for r in load(src):
            k = key(r)
            if k in repairs or not E.is_eligible(r):
                continue
            repairs[k] = (src, r)

    out = []
    # Seeded so every key is always reported, including as zero. A Counter drops
    # absent keys, and a summary that omits "repaired 0" reads like a summary that
    # forgot to check rather than one that checked and found none.
    stats = collections.Counter({"base_eligible": 0, "spliced": 0, "still_unusable": 0})
    substituted_models = collections.Counter()
    unrepaired_models = collections.Counter()

    for r in base:
        k = key(r)
        if E.is_eligible(r):
            stats["base_eligible"] += 1
            out.append(r)
            continue
        hit = repairs.get(k)
        if hit is None:
            stats["still_unusable"] += 1
            unrepaired_models[r.get("model")] += 1
            out.append(r)
            continue
        src, rep = hit
        merged = dict(rep)
        # Provenance travels WITH the record. A spliced corpus whose records do not
        # say where they came from is a corpus nobody can audit afterwards.
        merged["spliced_from"] = src
        merged["spliced_replaces"] = base_name
        merged["spliced_base_exclusion"] = (
            E.exclusion_reason(r) if hasattr(E, "exclusion_reason") else None)
        out.append(merged)
        stats["spliced"] += 1
        per_source[src] += 1
        substituted_models[r.get("model")] += 1

    stats["records"] = len(out)
    stats["eligible_after"] = sum(1 for r in out if E.is_eligible(r))
    return out, {
        "counts": dict(stats),
        "per_source": dict(per_source),
        "substituted_by_model": dict(substituted_models),
        "unrepaired_by_model": dict(unrepaired_models),
    }


def write(records, out_name):
    """Write one jsonl per model under runs/<out_name>/scored, plus a manifest."""
    root = run_roots()[0]
    d = root / out_name / "scored"
    d.mkdir(parents=True, exist_ok=True)
    by_model = collections.defaultdict(list)
    for r in records:
        by_model[r.get("model") or "unknown"].append(r)
    for model, rows in sorted(by_model.items()):
        safe = "".join(c if c.isalnum() or c in "-._" else "_" for c in model)
        with io.open(d / ("%s.jsonl" % safe), "w", encoding="utf-8", newline="\n") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return d


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--plan", action="store_true", help="what would change; writes nothing")
    ap.add_argument("--write", action="store_true", help="write the spliced run")
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--out", default=None)
    ap.add_argument("--all", action="store_true",
                    help="splice every damaged corpus in CORPUS_REPAIRS")
    args = ap.parse_args(argv)

    if args.all:
        rc = 0
        for base in CORPUS_REPAIRS:
            print("")
            rc |= main([("--write" if args.write else "--plan"), "--base", base])
        return rc

    spec = CORPUS_REPAIRS.get(args.base)
    if spec is None:
        print("ERROR: %r is not a registered damaged corpus. Known: %s"
              % (args.base, ", ".join(sorted(CORPUS_REPAIRS))), file=sys.stderr)
        return 2
    sources = spec["sources"]
    out_name = args.out or spec["out"]

    records, info = build(args.base, sources)
    if info.get("error"):
        print("ERROR: %s" % info["error"], file=sys.stderr)
        return 2

    c = info["counts"]
    print("SPLICE PLAN  base=%s  ->  %s" % (args.base, out_name))
    print("  records                  %d" % c.get("records", 0))
    print("  eligible in base         %d" % c.get("base_eligible", 0))
    print("  repaired by splicing     %d" % c.get("spliced", 0))
    print("  still unusable           %d" % c.get("still_unusable", 0))
    print("  eligible after splice    %d" % c.get("eligible_after", 0))
    if info["substituted_by_model"]:
        print("")
        print("  %-32s %8s %10s" % ("model", "repaired", "unrepaired"))
        models = set(info["substituted_by_model"]) | set(info["unrepaired_by_model"])
        for m in sorted(models, key=lambda m: -info["substituted_by_model"].get(m, 0)):
            print("  %-32s %8d %10d"
                  % ((m or "?").split("/")[-1],
                     info["substituted_by_model"].get(m, 0),
                     info["unrepaired_by_model"].get(m, 0)))

    if not args.write:
        print("")
        print("Nothing written. Re-run with --write to produce the spliced run.")
        return 0

    if c.get("spliced", 0) == 0:
        # A splice that repaired nothing would write a copy of the base run under a
        # new name -- a second corpus with no reason to exist, and a number quoted
        # from it would be unattributable to either.
        print("REFUSING to write: nothing was repaired, so the output would be a "
              "renamed copy of the base run.", file=sys.stderr)
        return 2

    d = write(records, out_name)
    manifest = {
        "analysis_seed": 20260914,
        "base_run": args.base,
        "splice_sources": list(sources),
        "calls_completed": 0,
        "generated_by": "scripts/splice_corpus.py",
        "derived": True,
        "note": "DERIVED corpus. No calls were made to build it. Records carry "
                "spliced_from / spliced_replaces where a repair was substituted.",
        "records": c.get("records", 0),
        "spliced": c.get("spliced", 0),
        "still_unusable": c.get("still_unusable", 0),
        "run_date": out_name,
    }
    with io.open(d.parent / "manifest.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print("")
    print("wrote %s" % d)
    print("Analysis reads this run by name; the base run is untouched.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
