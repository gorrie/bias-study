#!/usr/bin/env python3
"""One-shot: fix provenance on records written before recollect_at_cap was corrected.

WHY THIS EXISTS
---------------
`recollect_at_cap.py` built each new record with `rec = dict(old)`, copying the
original May record's fields. Two of them then described the wrong call:

    called_at         the MAY timestamp, so a record collected on 2026-09-14
                      claimed to have been called on 2026-05-25
    recollected_from  hardcoded "2026-05-25", which is not even the run being
                      repaired -- that is "2026-05-25-full"

and the copied `score_classifier` / `judge_reasoning` described the OLD text,
which a reader could mistake for a judgement of the new response.

The collector is fixed. This repairs the records already on disk.

WHAT IT CANNOT DO, AND SAYS SO
------------------------------
The true call time of an already-written record is not recoverable. It is NOT
invented. The May value is moved to `original_called_at`, where it is correct,
and `called_at` is set to null with `called_at_unrecorded` explaining why. A
plausible-looking timestamp would be worse than an absent one: it would be
unfalsifiable.

    python scripts/repair_recollect_provenance.py --plan
    python scripts/repair_recollect_provenance.py --apply
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import recollect_at_cap as R  # noqa: E402

REASON = ("collected by recollect_at_cap.py before 2026-09-14, which copied the "
          "replaced record's called_at; the true call time was never written down "
          "and is not invented here")


def needs_repair(r):
    """A re-collected record still carrying the replaced record's provenance."""
    if r.get("recollected_from") != "2026-05-25":
        return False
    return "original_called_at" not in r


def repair(r):
    out = dict(r)
    out["original_called_at"] = r.get("called_at")
    out["called_at"] = None
    out["called_at_unrecorded"] = REASON
    out["recollected_from"] = os.path.basename(R.SOURCE.rstrip("/\\"))
    # SCORES ARE NOT TOUCHED HERE.
    #
    # The first version of this cleared them, reasoning that a copied judgement
    # describes the replaced text. That is true of a record the instant the
    # collector writes it -- and it is FALSE of the 2026-09-05 batch, which was
    # collected at the new budget and then scored on its own text. Clearing those
    # would discard valid judgements and pay four judge calls each to reproduce
    # them.
    #
    # So the clearing belongs in the collector, where the record is known to be
    # fresh, and this repair touches provenance only. A record whose score is
    # genuinely stale is identifiable anyway: scoring_status "pending-rescore".
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)

    paths = sorted(glob.glob(os.path.join(R.OUT_DIR, "*.jsonl")))
    total = hit = 0
    per_file = {}
    for p in paths:
        rows = []
        n = 0
        with io.open(p, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                r = json.loads(line)
                total += 1
                if needs_repair(r):
                    r = repair(r)
                    n += 1
                rows.append(r)
        per_file[p] = (rows, n)
        hit += n

    print("records scanned   %d" % total)
    print("needing repair    %d" % hit)
    for p, (_rows, n) in sorted(per_file.items()):
        if n:
            print("  %-46s %d" % (os.path.basename(p), n))

    if not args.apply:
        print("")
        print("Nothing written. Re-run with --apply.")
        return 0
    if not hit:
        print("nothing to repair")
        return 0

    for p, (rows, n) in per_file.items():
        if not n:
            continue
        with io.open(p, "w", encoding="utf-8", newline="\n") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("")
    print("repaired %d record(s) across %d file(s)"
          % (hit, sum(1 for _p, (_r, n) in per_file.items() if n)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
