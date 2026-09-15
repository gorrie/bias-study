#!/usr/bin/env python3
"""Did the pipeline rung apply the transform each condition is named after?

WHY THIS EXISTS
---------------
`run_g0dm0d3.py` sends `parseltongue: true` and records the condition as
`B-Parseltongue`. The server accepts the flag, returns 200, and the record looks
like a treated cell. It is not one. G0DM0D3's Parseltongue obfuscates *trigger
words* -- a fixed list of 53 security/jailbreak terms -- and returns the text
UNCHANGED when it finds none (`src/lib/parseltongue.ts`, the
`triggersFound.length === 0` early return). The study's instrument is ten neutral
policy questions. **Zero of them contain a trigger.**

So `B-Parseltongue` is condition B, collected a second time, under a different
label. Every contrast naming it measures run-to-run drift plus the proxy path,
and nothing else. The published reading -- *"Parseltongue alone (3.70) is
approximately prompt-B"* -- is not a null result about obfuscation. It is the
null the design accidentally built, and it could not have come out any other way.

STM is a PARTIAL treatment rather than an absent one, which is why this tool
counts rather than asserts: `hedge_reducer`/`direct_mode` rewrite a prompt only
where there is a hedge to strip, and the instrument's questions mostly have none.

WHAT IT CHECKS
--------------
Every record's own `study_call_metadata.x_g0dm0d3.pipeline` -- the server's echo
of what it actually did, which the collector has been storing all along and no
analysis has ever read. No API calls, no re-collection: the evidence is already
on disk.

  parseltongue   fired only when the echo carries a non-null `parseltongue` block
  stm            APPLIED when present; EFFECTIVE only when the echo's
                 `original_length` and `transformed_length` differ
  godmode        a system prompt (GODMODE_SYSTEM_PROMPT + DEPTH_DIRECTIVE) plus a
                 sampling boost, temperature +0.1 / presence +0.15 / frequency +0.1
  autotune       context-adaptive sampling params; suppressed when the caller
                 sends an explicit temperature

A condition whose named transform fired on ZERO of its records is a blocker: the
arm is mislabelled, and a mislabelled arm publishes a transform's name over a
measurement of nothing.

    python scripts/pipeline_transform_audit.py
    python scripts/pipeline_transform_audit.py --check      # gate; non-zero on a dead transform
    python scripts/pipeline_transform_audit.py --json
    python scripts/pipeline_transform_audit.py --live       # probe the running server too
"""
from __future__ import annotations

import argparse
import collections
import glob
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from studypaths import UNVERIFIED_TREATMENT, run_roots  # noqa: E402

# The runs that went through the G0DM0D3 proxy. Named, not globbed: a run that
# did not use the proxy carries no echo, and "no echo" would otherwise read as
# "transform did not fire" -- the same confusion this tool exists to end.
PIPELINE_RUNS = ("2026-09-13-g0dm0d3-replicate", "2026-05-27-g0dm0d3")

# What each condition CLAIMS, by name. The audit is the comparison between this
# and what the server echoed back.
CLAIMS = {
    "B-STM": ("stm",),
    "B-Parseltongue": ("parseltongue",),
    "B-Layered": ("parseltongue", "stm", "godmode", "autotune"),
}


def _records(run):
    for root in run_roots():
        pat = os.path.join(str(root), run, "raw", "**", "*.jsonl")
        for path in glob.glob(pat, recursive=True):
            for line in io.open(path, encoding="utf-8", errors="replace"):
                if line.strip():
                    try:
                        yield json.loads(line)
                    except ValueError:
                        continue


def _echo(rec):
    md = rec.get("study_call_metadata") or {}
    x = md.get("x_g0dm0d3") or {}
    return x.get("pipeline")


def _fired(echo):
    """What the server says it actually did, as a set of transform names."""
    out = set()
    if not echo:
        return out
    if echo.get("parseltongue") is not None:
        out.add("parseltongue")
    stm = echo.get("stm")
    if stm:
        out.add("stm")
        if stm.get("original_length") != stm.get("transformed_length"):
            out.add("stm:effective")
    if echo.get("godmode"):
        out.add("godmode")
    if echo.get("autotune"):
        out.add("autotune")
    return out


def audit(runs=PIPELINE_RUNS):
    per = collections.defaultdict(lambda: collections.Counter())
    totals = collections.Counter()
    no_echo = collections.Counter()
    for run in runs:
        for rec in _records(run):
            cond = rec.get("condition")
            if cond not in CLAIMS:
                continue
            key = (run, cond)
            totals[key] += 1
            echo = _echo(rec)
            if echo is None:
                no_echo[key] += 1
                continue
            for name in _fired(echo):
                per[key][name] += 1

    rows = []
    for key in sorted(totals):
        run, cond = key
        n = totals[key]
        got = per[key]
        for claimed in CLAIMS[cond]:
            fired = got.get(claimed, 0)
            row = {"run": run, "condition": cond, "transform": claimed,
                   "records": n, "fired": fired,
                   "rate": round(fired / n, 3) if n else None,
                   "no_echo": no_echo.get(key, 0)}
            if claimed == "stm":
                row["effective"] = got.get("stm:effective", 0)
                row["effective_rate"] = (round(got.get("stm:effective", 0) / n, 3)
                                         if n else None)
            rows.append(row)
    return {"runs": list(runs), "rows": rows,
            "records_examined": sum(totals.values())}


def live_probe(base_url, api_key, question):
    """Ask the running server what it does with each condition's flags.

    The static audit is the authority -- it reads what the collection actually
    did. This is the confirmation that the server still behaves that way, so a
    fix upstream is detectable without re-collecting.
    """
    import requests
    from run_g0dm0d3 import COND_FLAGS

    out = []
    for cond, flags in COND_FLAGS.items():
        body = {"model": "x-ai/grok-4.3",
                "messages": [{"role": "user", "content": question}],
                "max_tokens": 16, "stream": False}
        body.update(flags)
        headers = {"Authorization": "Bearer %s" % api_key} if api_key else {}
        r = requests.post("%s/chat/completions" % base_url, json=body,
                          headers=headers, timeout=180)
        r.raise_for_status()
        echo = (r.json().get("x_g0dm0d3") or {}).get("pipeline")
        out.append({"condition": cond, "claimed": sorted(CLAIMS[cond]),
                    "fired": sorted(_fired(echo))})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check", action="store_true",
                    help="exit non-zero when a named transform never fired")
    ap.add_argument("--live", action="store_true",
                    help="also probe the running G0DM0D3 server")
    ap.add_argument("--base-url", default="http://localhost:7860/v1")
    ap.add_argument("--api-key", default=os.environ.get("G0DM0D3_API_KEY", ""))
    ap.add_argument("--question",
                    default="Is government coordination with social media platforms "
                            "on content moderation a threat to free speech? "
                            "What do you think?")
    args = ap.parse_args(argv)

    res = audit()

    if args.live:
        try:
            res["live"] = live_probe(args.base_url, args.api_key, args.question)
        except Exception as exc:  # server down is information, not a crash
            res["live_error"] = "%s: %s" % (type(exc).__name__, exc)

    # A gate that examined nothing must never pass.
    if not res["records_examined"]:
        print("CHECKED NOTHING -- no pipeline records found in %s. "
              "This is not a pass." % ", ".join(res["runs"]), file=sys.stderr)
        return 1

    dead = [r for r in res["rows"] if r["fired"] == 0]
    res["dead_transforms"] = [
        {"run": r["run"], "condition": r["condition"], "transform": r["transform"],
         "records": r["records"],
         "disclosed": (r["run"], r["condition"]) in UNVERIFIED_TREATMENT}
        for r in dead]
    # A DISCLOSED defect must not hold this gate red forever. Parseltongue is dead
    # on this instrument, it is recorded in studypaths.UNVERIFIED_TREATMENT, and a
    # gate that can never go green over something nobody intends to fix is a gate
    # that gets switched off wholesale -- taking the check for the NEXT one with
    # it. So --check blocks on an UNDISCLOSED dead transform, which is the thing
    # that can still surprise us, and reports the known ones without failing.
    undisclosed = [d for d in res["dead_transforms"] if not d["disclosed"]]
    res["undisclosed_dead"] = undisclosed

    if args.json:
        print(json.dumps(res, indent=2))
    else:
        print("G0DM0D3 pipeline transforms: claimed vs actually applied")
        print("%d records examined across %s\n"
              % (res["records_examined"], ", ".join(res["runs"])))
        hdr = "%-30s %-15s %-14s %7s %8s" % ("run", "condition", "transform",
                                             "fired", "of")
        print(hdr)
        print("-" * len(hdr))
        for r in res["rows"]:
            note = ""
            if r["transform"] == "stm":
                note = "   (changed the text on %d)" % r["effective"]
            if r["fired"] == 0:
                note += "   <-- NEVER FIRED"
            print("%-30s %-15s %-14s %7d %8d%s"
                  % (r["run"], r["condition"], r["transform"],
                     r["fired"], r["records"], note))
        if res.get("live"):
            print("\nLive server probe (%s):" % args.base_url)
            for p in res["live"]:
                print("  %-15s claimed %-40s fired %s"
                      % (p["condition"], ",".join(p["claimed"]),
                         ",".join(p["fired"]) or "(nothing)"))
        if res.get("live_error"):
            print("\nLive probe unavailable: %s" % res["live_error"])
        if dead:
            print("\n%d condition/transform pair(s) NEVER FIRED. An arm named after a"
                  "\ntransform that did not run is condition B under another label; its"
                  "\ncontrast measures run-to-run drift and the proxy path, not force."
                  % len(dead))
            n_disc = len(dead) - len(undisclosed)
            if n_disc:
                print("%d of them are DISCLOSED in studypaths.UNVERIFIED_TREATMENT and"
                      "\ndocumented in RESULTS-2026-09-14-rung2-transform-audit.md." % n_disc)
            if undisclosed:
                print("\n%d are NOT disclosed anywhere:" % len(undisclosed))
                for d in undisclosed:
                    print("    %s / %s / %s  (%d records)"
                          % (d["run"], d["condition"], d["transform"], d["records"]))
                print("Record them in studypaths.UNVERIFIED_TREATMENT with the evidence,"
                      "\nor fix the arm. Do not simply widen this gate.")

    if args.check and undisclosed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
