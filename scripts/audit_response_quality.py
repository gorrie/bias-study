#!/usr/bin/env python3
"""Inventory every scored record whose response was empty — DATA-EMPTY-SCORES-001 / -002.

`score.py` refuses to score an empty response, but only for runs scored after that fix. This
counts what is already on disk, across the primary `scored/` corpus AND every alternate
`scored-*` judge method, which -001 did not cover.

    audit_response_quality.py                 # the inventory
    audit_response_quality.py --by-model      # per model/condition missingness
    audit_response_quality.py --check         # exit 1 while any empty record retains a score

`--check` is EXPECTED TO FAIL and must not be made green by deleting records. The originals are
the evidence that the defect happened; the correction belongs in a dated directory beside them,
never on top of them. An audit whose own failure gets tidied away has been converted into
decoration.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eligibility as E  # noqa: E402

try:
    from studypaths import runs_root
except Exception:                                    # noqa: BLE001
    def runs_root():
        here = Path(__file__).resolve().parents[1]
        for name in ("data", "runs"):
            if (here / name).is_dir():
                return here / name
        return here / "data"


def scored_dirs(root: Path):
    for run in sorted(p for p in root.iterdir() if p.is_dir()):
        for d in sorted(run.glob("scored*")):
            if d.is_dir():
                yield run.name, d


def read(d: Path):
    for path in sorted(d.glob("*.jsonl")):
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    yield path.name, json.loads(line)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if any empty response still carries a score")
    ap.add_argument("--by-model", action="store_true")
    a = ap.parse_args(argv)

    root = Path(runs_root())
    per_method = defaultdict(lambda: Counter())
    per_model = defaultdict(lambda: Counter())
    offenders = []
    for run_name, d in scored_dirs(root):
        method = d.name
        for fname, r in read(d):
            per_method[method]["records"] += 1
            if E.is_empty_response(r):
                per_method[method]["empty"] += 1
                if E.has_score(r):
                    per_method[method]["scored_empty"] += 1
                    per_model[(r.get("model", "?"), r.get("condition", "?"))][method] += 1
                    offenders.append((run_name, method, fname, r.get("model"),
                                      r.get("question_id"), r.get("score_classifier")))

    print("EMPTY RESPONSES THAT CARRY A SCORE")
    print("")
    print("%-34s %9s %7s %19s" % ("method", "records", "empty", "empty WITH a score"))
    for m in sorted(per_method):
        c = per_method[m]
        print("%-34s %9d %7d %19d" % (m, c["records"], c["empty"], c["scored_empty"]))
    tot = sum(c["scored_empty"] for c in per_method.values())
    print("")
    print("%-34s %9d %7d %19d" % ("TOTAL",
                                  sum(c["records"] for c in per_method.values()),
                                  sum(c["empty"] for c in per_method.values()), tot))

    if a.by_model:
        print("")
        print("PER MODEL / CONDITION — scored-empty counts by judge method")
        print("(selective missingness is a finding, not only a denominator correction)")
        print("")
        methods = sorted(per_method)
        print("%-38s %s" % ("model / cond", " ".join("%10s" % m[:10] for m in methods)))
        for key in sorted(per_model):
            row = per_model[key]
            print("%-38s %s" % ("%s %s" % key, " ".join("%10d" % row[m] for m in methods)))

    print("")
    if tot:
        print("%d record(s) carry a score derived from an empty response." % tot)
        print("The same blank strings were scored by some judge methods and correctly skipped")
        print("by others, so whether nothing becomes a number depends on the method — inside")
        print("the very comparison built to measure judge contamination.")
        print("")
        print("DO NOT delete these to make this green. They are the evidence. Exclude them at")
        print("READ time (scripts/eligibility.py) and regenerate into a dated correction dir.")
    else:
        print("no empty response carries a score.")

    if a.check:
        return 1 if tot else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())


def audit(root, include_alternates=False):
    """Source-hashed inventory of unusable scored records. Reads only; never mutates.

    Kept to the contract the September 8 pass defined, because quality_correction_report.py
    builds its before/after provenance from these exact keys and re-verifies every source
    hash after the fact to prove nothing changed underneath it. That machinery is worth more
    than the convenience of a different return shape, so the shape is preserved and the rule
    underneath it is the reconciled one in eligibility.py.
    """
    import hashlib
    from collections import Counter
    from pathlib import Path
    from eligibility import exclusion_reason

    root = Path(root)
    total, unusable, findings, cells, sources = 0, 0, [], {}, []
    paths = set(root.glob("*/scored/*.jsonl"))
    if include_alternates:
        paths.update(root.glob("*/scored-*/*.jsonl"))
    for path in sorted(paths):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        rel = path.relative_to(root).as_posix()
        sources.append({"file": rel, "sha256": digest})
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            record = json.loads(line)
            total += 1
            reason = exclusion_reason(record)
            key = (path.parent.parent.name, path.parent.name,
                   record.get("model"), record.get("condition"))
            cell = cells.setdefault(key, Counter())
            cell["attempted"] += 1
            cell["excluded" if reason else "eligible"] += 1
            if reason:
                cell[reason] += 1
            else:
                continue
            unusable += 1
            if record.get("score_classifier") is not None:
                cell["unusable_with_scores"] += 1
                findings.append(dict(file=rel, line=line_number, file_sha256=digest,
                                     model=record.get("model"),
                                     question_id=record.get("question_id"),
                                     condition=record.get("condition"), reason=reason))
    return dict(schema="bias-response-quality/2",
                scope=("primary and alternate scored methods" if include_alternates
                       else "primary scored/ only"),
                total_records=total, unusable_records=unusable,
                unusable_with_scores=len(findings),
                by_run=dict(sorted(Counter(f["file"].split("/")[0] for f in findings).items())),
                cells=[dict(run=k[0], method=k[1], model=k[2], condition=k[3], **v)
                       for k, v in sorted(cells.items(), key=lambda item: str(item[0]))],
                sources=sources, records=findings)
