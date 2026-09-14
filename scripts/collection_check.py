#!/usr/bin/env python3
"""Is this collection fit to score? Run it BEFORE spending judge calls on a run.

WHY THIS EXISTS
---------------
`COLLECTION-STANDARD.md` opens with "This is a gate, not advice," and until
2026-09-13 nothing executed it: zero references from any script or CI config. Its
section 4 asks "What is the parameter that will silently ruin it?" and lists a
build that "cannot fit its answer sheet in the budget" as an example of a
collection that is not being measured.

That is exactly what had happened, unnoticed, for four months. 1,022 of 4,748
scored records sat on an 800-token cap -- 21.5% of the corpus, severed
mid-argument and handed to the judges. The rate ran from 96.7% of one model's
records to near zero for terse ones, so every cross-vendor comparison was
confounded with verbosity, and the study's central claim is about vendor
differences.

Every check below would have caught something real on the day it was written. The
point is that a collection gets a verdict BEFORE anyone spends money scoring it
and long before a number reaches a page.

WHAT IT CHECKS

  1. records exist                 a gate over zero records is not a pass
  2. collection parameters recorded  max_tokens and temperature, per record. Not
                                   recording them is HOW the truncation defect
                                   stayed invisible: you could not tell from a run
                                   directory what budget produced it
  3. truncation                    by the TEXT, never by finish_reason -- the
                                   G0DM0D3 proxy reports "stop" on responses
                                   severed mid-word
  4. truncation is not differential  a uniform rate is a limitation; a rate that
                                   varies by model is a CONFOUND, and excluding
                                   the records relocates it into the denominator
                                   rather than removing it
  5. empty responses               a completed call that returned nothing
  6. replicate distinctness        --samples 5 is worth nothing if the server
                                   serves five identical strings
  7. cell balance                  ragged cells silently drop items from paired
                                   contrasts
  8. token headroom                responses crowding the cap mean the next model
                                   will hit it

    python scripts/collection_check.py 2026-09-13-g0dm0d3-replicate
    python scripts/collection_check.py <run> --json

Reads only. No API calls. Exit 0 accept, 1 blocked, 2 nothing to check.
"""
from __future__ import annotations

import argparse
import collections
import glob
import hashlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import eligibility as E  # noqa: E402

#: Above this share of truncated responses the run is not scoreable as collected.
TRUNCATION_BLOCK = 0.05
#: Spread between the best and worst model's truncation rate. Differential
#: truncation is worse than uniform truncation, because exclusion cannot fix it.
TRUNCATION_SPREAD_BLOCK = 0.10
#: Responses landing within this fraction of the cap are "crowding" it.
HEADROOM_WARN = 0.95


def load_raw(run_dir):
    rows = []
    for path in sorted(glob.glob(os.path.join(run_dir, "raw", "**", "*.jsonl"), recursive=True)):
        for line in io.open(path, encoding="utf-8", errors="replace"):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except ValueError:
                pass
    return rows


def cap_of(rec):
    cap = rec.get("max_tokens")
    if cap is None:
        cap = (rec.get("study_call_metadata") or {}).get("max_tokens")
    return cap


def analyse(rows):
    out = {"n_records": len(rows), "problems": [], "warnings": []}
    if not rows:
        return out

    ok_rows = [r for r in rows if r.get("ok")]
    out["n_ok"] = len(ok_rows)
    out["n_failed"] = len(rows) - len(ok_rows)

    # 2. collection parameters
    with_cap = sum(1 for r in rows if cap_of(r) is not None)
    with_temp = sum(1 for r in rows if r.get("temperature") is not None)
    out["pct_with_max_tokens"] = round(100.0 * with_cap / len(rows), 1)
    out["pct_with_temperature"] = round(100.0 * with_temp / len(rows), 1)
    if with_cap == 0:
        out["problems"].append(
            "NO max_tokens RECORDED on any record. The parameter most able to ruin a "
            "collection is unrecoverable from this run: you cannot tell what budget "
            "produced it, so truncation can only be guessed at from the text.")
    if with_temp == 0:
        out["warnings"].append(
            "no temperature recorded; replicate behaviour is not reconstructable")

    # 3/4. truncation, by the text
    trunc_by_model = collections.Counter()
    total_by_model = collections.Counter()
    n_trunc = 0
    for r in ok_rows:
        m = r.get("model") or "?"
        total_by_model[m] += 1
        if E.looks_truncated_text(r.get("response_text") or ""):
            trunc_by_model[m] += 1
            n_trunc += 1
    out["n_truncated"] = n_trunc
    out["pct_truncated"] = round(100.0 * n_trunc / max(1, len(ok_rows)), 1)
    rates = {m: trunc_by_model.get(m, 0) / t for m, t in total_by_model.items() if t >= 5}
    out["truncation_by_model"] = {m: round(100 * v, 1) for m, v in sorted(rates.items())}
    if n_trunc and n_trunc / max(1, len(ok_rows)) > TRUNCATION_BLOCK:
        out["problems"].append(
            "%d of %d responses (%.1f%%) end mid-sentence. A severed response is not a "
            "measurement and must not be scored. Re-collect at a larger --max-tokens."
            % (n_trunc, len(ok_rows), 100.0 * n_trunc / len(ok_rows)))
    if rates:
        spread = max(rates.values()) - min(rates.values())
        out["truncation_spread"] = round(100 * spread, 1)
        if spread > TRUNCATION_SPREAD_BLOCK:
            hi = max(rates, key=rates.get)
            lo = min(rates, key=rates.get)
            out["problems"].append(
                "truncation is DIFFERENTIAL across models: %.1f%% (%s) against %.1f%% (%s). "
                "This is a confound, not a limitation -- excluding the records moves it into "
                "the denominator instead of removing it, so any cross-model comparison from "
                "this run is unsafe even after filtering."
                % (100 * rates[hi], hi.split("/")[-1], 100 * rates[lo], lo.split("/")[-1]))

    # 5. empty
    n_empty = sum(1 for r in ok_rows if not (r.get("response_text") or "").strip())
    out["n_empty"] = n_empty
    if n_empty:
        out["problems"].append(
            "%d completed call(s) returned no text. Usually the whole budget went to "
            "reasoning tokens. These must never reach a judge." % n_empty)

    # 6. replicate distinctness
    cells = collections.defaultdict(list)
    for r in ok_rows:
        cells[(r.get("model"), r.get("condition"), r.get("question_id"))].append(
            hashlib.sha256(((r.get("response_text") or "")).encode("utf-8")).hexdigest())
    multi = {k: v for k, v in cells.items() if len(v) > 1}
    out["n_cells"] = len(cells)
    out["n_cells_with_replicates"] = len(multi)
    if multi:
        identical = [k for k, v in multi.items() if len(set(v)) == 1]
        out["n_cells_all_identical"] = len(identical)
        distinct = sum(len(set(v)) for v in multi.values()) / len(multi)
        out["mean_distinct_per_cell"] = round(distinct, 2)
        if len(identical) == len(multi):
            out["problems"].append(
                "EVERY replicate cell returned identical text. The replicate design is "
                "buying nothing -- the server is serving one deterministic answer per cell "
                "and the run costs N times a single draw.")
        elif len(identical) > 0.2 * len(multi):
            out["warnings"].append(
                "%d of %d replicate cells returned identical text"
                % (len(identical), len(multi)))

    # 7. cell balance
    depths = collections.Counter(len(v) for v in cells.values())
    out["cell_depths"] = dict(sorted(depths.items()))
    if len(depths) > 1:
        out["warnings"].append(
            "ragged cell depth %s -- paired contrasts silently drop unmatched items, so "
            "report the pair count with any delta" % sorted(depths))

    # 8. headroom
    caps = [cap_of(r) for r in ok_rows if cap_of(r) is not None]
    outs = [r.get("tokens_out") for r in ok_rows if isinstance(r.get("tokens_out"), int)]
    if caps and outs:
        cap = max(caps)
        crowding = sum(1 for t in outs if t >= HEADROOM_WARN * cap)
        out["cap"] = cap
        out["max_tokens_out"] = max(outs)
        out["n_crowding_cap"] = crowding
        if crowding:
            out["warnings"].append(
                "%d response(s) came within %d%% of the %d-token cap; the next, more "
                "verbose model will hit it" % (crowding, int(HEADROOM_WARN * 100), cap))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("run", help="run date/name, e.g. 2026-09-13-g0dm0d3-replicate")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    try:
        from studypaths import run_roots
        roots = [str(p) for p in run_roots()]
    except Exception:
        study = os.path.dirname(HERE)
        roots = [os.path.join(study, r) for r in ("runs", "data")]

    run_dir = None
    for root in roots:
        cand = os.path.join(root, a.run)
        if os.path.isdir(cand):
            run_dir = cand
            break
    if run_dir is None:
        print("CHECKED NOTHING -- no run directory named %r under: %s"
              % (a.run, ", ".join(roots)), file=sys.stderr)
        print("This is NOT a pass.", file=sys.stderr)
        return 2

    rows = load_raw(run_dir)
    res = analyse(rows)
    res["run"] = a.run
    res["run_dir"] = run_dir

    if a.json:
        print(json.dumps(res, indent=2, default=str))
        return 1 if res["problems"] else 0

    print("COLLECTION CHECK -- %s" % a.run)
    print(run_dir)
    print("")
    if not rows:
        print("CHECKED NOTHING -- 0 raw records in this run directory. This is NOT a pass.")
        return 2

    print("  records                %d (%d ok, %d failed)"
          % (res["n_records"], res.get("n_ok", 0), res.get("n_failed", 0)))
    print("  cells                  %d (%d with replicates, mean %s distinct)"
          % (res.get("n_cells", 0), res.get("n_cells_with_replicates", 0),
             res.get("mean_distinct_per_cell", "n/a")))
    print("  cell depths            %s" % res.get("cell_depths"))
    print("  max_tokens recorded    %s%%" % res.get("pct_with_max_tokens"))
    print("  temperature recorded   %s%%" % res.get("pct_with_temperature"))
    print("  truncated (text test)  %d  (%.1f%%)"
          % (res.get("n_truncated", 0), res.get("pct_truncated", 0.0)))
    if res.get("truncation_by_model"):
        for m, v in res["truncation_by_model"].items():
            print("      %-40s %5.1f%%" % (m.split("/")[-1], v))
    print("  empty responses        %d" % res.get("n_empty", 0))
    if "cap" in res:
        print("  token cap / max out    %d / %d  (%d crowding)"
              % (res["cap"], res["max_tokens_out"], res.get("n_crowding_cap", 0)))
    print("")

    for w in res["warnings"]:
        print("  WARNING: %s" % w)
    for p in res["problems"]:
        print("  BLOCKER: %s" % p)
    print("")
    if res["problems"]:
        print("NOT FIT TO SCORE -- %d blocker(s). Spending judge calls on this run buys "
              "numbers that are not measurements." % len(res["problems"]))
        return 1
    print("ACCEPTED -- fit to score.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
