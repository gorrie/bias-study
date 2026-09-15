#!/usr/bin/env python3
"""One flat, eligibility-flagged table of every scored record, for people who are not us.

WHY THIS EXISTS
---------------
`data/` is the immutable study record and it is organised for provenance, not for analysis: one
directory per run, one file per model, six judging methods, and a schema that grew. Getting from
that to "mean score by model and condition" takes a reader through the run layout, the method
directories, and one rule they have no way to know about.

**That rule is the whole point of this script.** 466 records in the primary scored corpus carry
a classifier score derived from an EMPTY response, and 547 across all six judging methods. An
empty string scores a 3, three is the balanced answer, and every reader in this project filtered
on `score_classifier is not None` -- which is exactly the filter a scored blank passes. It took
us four months and a dedicated audit to find. A third party reading these files directly has no
warning at all: nothing in the shipped record says the response was blank, because
`response_text` is simply `""` and the score beside it looks like every other score.

So this emits ONE table with an explicit `eligible` column and, where false, the reason.

NOTHING IS DROPPED
------------------
Ineligible rows are exported WITH THE FLAG, never filtered out. That is this project's standing
position on its own defects -- `scripts/audit_response_quality.py` says it in capitals: *do not
delete these to make this green, they are the evidence.* A cleaned corpus that silently omits its
own exclusions cannot be checked, and a reader who disagrees with our eligibility rule is
entitled to the rows it excludes so they can apply their own.

FOR ABLITERATION WORK SPECIFICALLY
----------------------------------
`build` splits a model id into base and abliteration variant, so a stock/ablated contrast is a
groupby rather than a parsing exercise: `qwen2.5-7b-abliterated-strong` becomes base
`qwen2.5-7b`, build `abliterated-strong`, `is_ablated` true. The arm's coverage is uneven and
knowing that up front matters more than the convenience -- 39 of 63 cells reached n=5 and 24 came
back short, one of them returning zero valid responses of five. `--manifest` reports per-cell
counts so nobody discovers that halfway through an analysis.

    python scripts/export_analysis_ready.py --out export/
    python scripts/export_analysis_ready.py --out export/ --eligible-only   # if you insist
"""
from __future__ import annotations

import argparse
import collections
import csv
import glob
import hashlib
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, HERE)

#: Suffixes OBLITERATUS and friends append to a base model id. Order matters: the longest match
#: wins, so `abliterated-huihui-qwen38-27b-ablite` does not get truncated to `abliterated`.
_BUILD_MARKERS = ("abliterated", "ablated", "ablite", "uncensored", "obliterated")

COLUMNS = [
    "run", "method", "model", "base", "build", "is_ablated", "vendor",
    "condition", "question_id", "topic", "position", "sample_idx",
    "score", "eligible", "exclusion_reason", "is_defect",
    "n_judges", "n_valid", "disagreement", "judge_scores",
    "response_chars", "response_empty", "refusal_class", "scoring_status",
    "hedge_ratio", "word_count_total", "tokens_in", "tokens_out", "latency_ms",
    "source_file",
]


def corpus_roots():
    try:
        from studypaths import run_roots
        return [str(p) for p in run_roots()]
    except Exception:
        return [os.path.join(STUDY, r) for r in ("data", "runs")
                if os.path.isdir(os.path.join(STUDY, r))]


def split_build(model):
    """-> (base, build, is_ablated). A stock model has build "stock" and is_ablated False."""
    if not model:
        return "", "stock", False
    low = model.lower()
    hit = None
    for marker in _BUILD_MARKERS:
        idx = low.find(marker)
        if idx > 0 and (hit is None or idx < hit):
            hit = idx
    if hit is None:
        return model, "stock", False
    base = model[:hit].rstrip("-_:/ ")
    build = model[hit:].lstrip("-_:/ ")
    return (base or model), (build or "ablated"), True


def vendor_of(model):
    if not model:
        return ""
    if "/" in model:
        return model.split("/", 1)[0]
    m = re.match(r"([a-z]+)", model.lower())
    return m.group(1) if m else ""


def rows(roots):
    """Every scored record under every run root and every judging method."""
    import eligibility as E
    # DERIVED CORPORA ARE SKIPPED HERE. A spliced run is a view over a base run
    # plus its repairs, so counting it alongside both double-counts every record
    # it contains -- it added 2,483 rows that were not new measurements and put a
    # cross-path defect count off by one. Analyses read a derived corpus by name
    # through `studypaths.canonical_run`; enumeration of the corpus does not.
    try:
        from studypaths import is_derived_run
    except Exception:
        def is_derived_run(_name):
            return False

    for root in roots:
        for path in sorted(glob.glob(os.path.join(root, "*", "scored*", "**", "*.jsonl"),
                                     recursive=True)):
            parts = path.split(os.sep)
            run = ""
            method = "scored"
            for i, seg in enumerate(parts):
                if seg.startswith("scored"):
                    method = seg
                    run = parts[i - 1] if i else ""
                    break
            if run and is_derived_run(run):
                continue
            for line in io.open(path, encoding="utf-8", errors="replace"):
                if not line.strip():
                    continue
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if r.get("score_classifier") is None and not r.get("response_text"):
                    # Never collected at all -- not a scored record, not this table's business.
                    if not E.has_score(r):
                        continue
                text = r.get("response_text") or ""
                base, build, is_abl = split_build(r.get("model"))
                judges = r.get("score_classifier_judges") or []
                yield {
                    "run": run,
                    "method": method,
                    "model": r.get("model", ""),
                    "base": base,
                    "build": build,
                    "is_ablated": is_abl,
                    "vendor": vendor_of(r.get("model")),
                    "condition": r.get("condition", ""),
                    "question_id": r.get("question_id", ""),
                    "topic": r.get("topic", ""),
                    "position": r.get("position", ""),
                    "sample_idx": r.get("sample_idx", ""),
                    "score": r.get("score_classifier", ""),
                    "eligible": E.is_eligible(r),
                    # THREE STATES, NOT TWO. `exclusion_reason` names the two DEFECT classes --
                    # a failed call and a score derived from nothing. It deliberately returns
                    # None for a record with real text and no score, because the largest class
                    # of those is a SUBSTANTIVE REFUSAL: a model returning an essay about why it
                    # will not answer. Refusals are a result in this study, not a defect, and
                    # `eligibility.load_scored_records` keeps them on purpose.
                    #
                    # So they are ineligible for a MEAN -- you cannot average a score that does
                    # not exist -- while being perfectly good data. Labelling them
                    # "no-classifier-score" keeps them distinguishable from the two defect
                    # classes, which is the distinction anyone counting refusals needs.
                    "exclusion_reason": ("" if E.is_eligible(r)
                                         else (E.exclusion_reason(r) or "no-classifier-score")),
                    "is_defect": (not E.is_eligible(r)) and bool(E.exclusion_reason(r)),
                    "n_judges": r.get("score_classifier_n_judges", ""),
                    "n_valid": r.get("score_classifier_n_valid", ""),
                    "disagreement": r.get("score_classifier_disagreement", ""),
                    "judge_scores": ";".join(
                        "%s=%s" % (j.get("judge"), j.get("score")) for j in judges),
                    "response_chars": len(text),
                    "response_empty": not text.strip(),
                    "refusal_class": r.get("refusal_class", ""),
                    "scoring_status": r.get("scoring_status", ""),
                    "hedge_ratio": r.get("hedge_ratio", ""),
                    "word_count_total": r.get("word_count_total", ""),
                    "tokens_in": r.get("tokens_in", ""),
                    "tokens_out": r.get("tokens_out", ""),
                    "latency_ms": r.get("latency_ms", ""),
                    "source_file": os.path.relpath(path, STUDY).replace(os.sep, "/"),
                }


def manifest(table):
    """Counts a reader needs BEFORE they start, not after they have drawn a conclusion."""
    by_reason = collections.Counter()
    defects = 0
    by_method = collections.Counter()
    by_method_inelig = collections.Counter()
    cells = collections.Counter()
    ablation_cells = collections.Counter()
    for t in table:
        by_method[t["method"]] += 1
        if not t["eligible"]:
            by_reason[t["exclusion_reason"]] += 1
            by_method_inelig[t["method"]] += 1
            defects += 1 if t["is_defect"] else 0
        else:
            cells[(t["model"], t["condition"])] += 1
            if t["is_ablated"] or t["build"] == "stock":
                ablation_cells[(t["base"], t["build"], t["condition"])] += 1
    return {
        "schema": "bias-study/analysis-ready/1",
        "total_rows": len(table),
        "eligible_rows": sum(1 for t in table if t["eligible"]),
        "ineligible_rows": sum(1 for t in table if not t["eligible"]),
        "ineligible_by_reason": dict(by_reason),
        "defect_rows": defects,
        "unscored_but_substantive_rows": sum(
            1 for t in table if not t["eligible"] and not t["is_defect"]),
        "rows_by_method": dict(by_method),
        "ineligible_by_method": dict(by_method_inelig),
        "eligible_cells_model_condition": len(cells),
        "smallest_eligible_cells": sorted(
            ({"model": m, "condition": c, "n": n} for (m, c), n in cells.items()),
            key=lambda d: d["n"])[:15],
        "note": (
            "ineligible rows are PRESENT in the CSV with eligible=False and a reason. They are "
            "not filtered out: a cleaned corpus that silently omits its own exclusions cannot "
            "be checked, and a reader who disagrees with this rule needs the rows to apply "
            "their own. The dominant reason is a classifier score derived from an empty "
            "response -- an empty string scores a 3, and 3 is the balanced answer."),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True, help="directory to write the table and manifest into")
    ap.add_argument("--eligible-only", action="store_true",
                    help="drop ineligible rows entirely. Off by default and the manifest still "
                         "reports what was dropped, because an unfalsifiable clean corpus is "
                         "the thing this study exists to complain about")
    args = ap.parse_args(argv)

    table = list(rows(corpus_roots()))
    if not table:
        print("no scored records found under %s" % ", ".join(corpus_roots()))
        return 1
    man = manifest(table)
    man["eligible_only_export"] = bool(args.eligible_only)
    if args.eligible_only:
        table = [t for t in table if t["eligible"]]

    os.makedirs(args.out, exist_ok=True)
    csv_path = os.path.join(args.out, "bias-study-records.csv")
    with io.open(csv_path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        for t in table:
            w.writerow(t)

    with io.open(csv_path, "rb") as fh:
        man["csv_sha256"] = hashlib.sha256(fh.read()).hexdigest()
    man["csv_rows_written"] = len(table)
    with io.open(os.path.join(args.out, "manifest.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(man, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print("wrote %s  (%d rows, %d columns)" % (os.path.relpath(csv_path, STUDY), len(table), len(COLUMNS)))
    print("  eligible   %d" % man["eligible_rows"])
    print("  ineligible %d  %s" % (man["ineligible_rows"], man["ineligible_by_reason"] or ""))
    if not args.eligible_only and man["ineligible_rows"]:
        print("  ineligible rows are IN the file with eligible=False. Filter on that column.")
    print("  sha256 %s" % man["csv_sha256"][:16])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
