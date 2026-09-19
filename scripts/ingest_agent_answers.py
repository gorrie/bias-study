#!/usr/bin/env python3
"""Ingest an answer sheet produced by an in-harness agent into the standard run format.

WHY THIS CHANNEL EXISTS
-----------------------
The study's oldest structural limitation is the transparency asymmetry: the weight rung
(abliteration) only works on open weights, so the deepest verification reaches exactly the
models that move least. Closed frontier models are un-abliteratable by construction, which
`ADVERSARIAL-REVIEW.md` B1/B2 concede and reframe as an auditability gap rather than a lean
claim.

A second access tier to the same closed model family is the only arm variation available on
that side. This channel records answers produced under it so they sit in the same format as
API and local runs and go through the same parser and the same metrics.

WHAT THIS IS NOT
----------------
It is NOT a matched arm, and any comparison against an API run of the same model family is
confounded on at least four axes, all uncontrolled:

  - system prompt: the API call carries only the condition prompt; an in-harness agent
    carries a large harness prompt in addition to it
  - tooling: the agent reads the instrument from disk, the API model receives it inline
  - sampling: temperature and seed are set per-channel and do not match
  - version resolution: the API model id and whatever the harness resolves to need not agree

System prompt is the variable this study manipulates, so a POSITION comparison across these
arms is not interpretable. Two things are:

  1. REFUSAL -- whether the instrument is answered at all is far less sensitive to those
     confounds than where the answers land. Gemini refuses 5/5 under balance while GPT-5.6
     Terra refuses 0/20; no system-prompt difference explains a gap that size.
  2. WITHIN-ARM condition contrasts -- the harness confound is constant across conditions, so
     A-vs-D inside this channel is valid on its own terms.

Anything else from this channel is a curiosity, and the record says so via `channel` and
`arm_caveat` fields that travel with every row.

Usage:
    python ingest_agent_answers.py --condition A --answers sheet.txt --out runs/<dir>
    cat sheet.txt | python ingest_agent_answers.py --condition D --out runs/<dir>
"""
from __future__ import annotations

import argparse
import datetime
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_battery import CONDITION_NOTE, load_items, parse_answers  # noqa: E402
import studypaths as _SP  # noqa: E402

CAVEAT = ("in-harness agent channel: NOT a matched arm against API runs. System prompt, "
          "tooling, sampling and version resolution all differ. Position comparisons across "
          "channels are not interpretable; refusal and within-arm condition contrasts are.")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--condition", required=True)
    ap.add_argument("--answers", default=None, help="file with the answer sheet (default stdin)")
    ap.add_argument("--items", default=None)
    ap.add_argument("--model", default="claude-code-harness-agent")
    ap.add_argument("--label", default="red-team-access")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    text = (io.open(args.answers, encoding="utf-8").read() if args.answers
            else sys.stdin.read())
    data = load_items(args.items)
    items = data["items"]
    answers, problems = parse_answers(text, [it["id"] for it in items])

    record = {
        "schema": _SP.SCHEMA,
        "model": args.model,
        "channel": "agent",
        "access_tier": args.label,
        "arm_caveat": CAVEAT,
        "condition": args.condition,
        "condition_note": CONDITION_NOTE.get(args.condition, "?"),
        "run_no": 1,
        "temperature": None,
        "seed": None,
        "shuffle_seed": None,
        "max_tokens": None,
        "collected_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        # A DEFAULT NAMING A RETIRED BANK is one missing key away from stamping it onto a live
        # record. The live instrument is the author's battery; a payload that does not name
        # its instrument is assumed to be on it.
        "instrument": data.get("instrument", "ratchet-battery"),
        "n_items": len(items),
        "ok": True,
        "response_text": text,
        "answers": answers,
        "n_answers": len(answers),
        "problems": problems,
        "failure_mode": None if not problems else "other",
        "valid": not problems,
    }
    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, "%s__%s.jsonl" % (args.label, args.condition))
    with io.open(path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    print("%s cond %s: %d/%d answers %s -> %s"
          % (args.label, args.condition, len(answers), len(items),
             "OK" if not problems else "INVALID: " + "; ".join(problems), path))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
