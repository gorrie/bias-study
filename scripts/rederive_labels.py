#!/usr/bin/env python3
"""Re-derive stored validity and failure labels from the CURRENT parser, in place.

WHY THIS EXISTS
---------------
A record's `valid`, `n_answers`, `answers`, `problems` and `failure_mode` are not measurements.
They are the output of `run_battery.parse_answers` and `classify_failure` applied to
`response_text`, which IS the measurement. When those functions are corrected, every record
written before the correction still carries the old verdict, and nothing re-derives it.

THE CASE THIS WAS BUILT FOR. `llama3.1:8b` answers the battery in the shape

    1. Government funding of organisations that flag lawful speech ...
    Agree

-- every item answered, nothing truncated, nothing declined -- and `LINE_RE` required the
number and the option on ONE line, so it parsed zero. `classify_failure` then saw a non-empty,
non-capped, zero-answer body and called it a refusal. The parser was fixed on 2026-09-16
(LEARNINGS #31). The RECORDS were not. Four sheets in the 2026-09-16 wave sit on disk labelled
`refused` and are complete 32-of-32 answer sheets under current code. `floor_table.load()`
drops them for `valid: false`, and the refusal deliverable counts them as models declining the
instrument -- a finding about a local model that would have been an artifact of our parser.

WHY IT IS SAFE, AND WHERE IT STOPS
----------------------------------
This rewrites DERIVED fields only. `response_text`, `model`, `condition`, `shuffle_seed`,
`seed`, `provider`, `tokens_out`, `latency_ms`, `collected_at` -- everything the API returned
and everything about how it was asked -- is never touched. A re-derivation that changed those
would be fabrication, and the check below refuses to write if any of them would move.

It also refuses to run unless `CLASSIFIER_VERSION` has been bumped past the version stored on
the records it is about to change: a re-derivation that stamps the same version it found is
invisible to `refusal_table.audit`, which partitions rows by exactly that field.

    python scripts/rederive_labels.py <run-dir>            # dry run, prints every change
    python scripts/rederive_labels.py <run-dir> --apply    # rewrite in place
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

from run_battery import CLASSIFIER_VERSION, classify_failure, parse_answers  # noqa: E402

#: Never rewritten. What the API returned and how it was asked.
IMMUTABLE = ("response_text", "model", "condition", "shuffle_seed", "seed", "provider",
             "provider_pinned", "tokens_in", "tokens_out", "latency_ms", "collected_at",
             "max_tokens", "temperature", "template", "channel", "instrument", "n_items",
             "schema", "forcing_prompt", "system_prompt")


def item_ids(rec):
    """The ids this sheet was asked for, recovered from its own forcing prompt.

    The prompt is stored on the record, so the expected id set is recoverable without the bank
    -- which matters because the bank may have been renamed since, and a re-derivation must
    depend on the record and the code, never on a file that could have moved.

    SORTED, BECAUSE THE COLLECTOR PASSES CANONICAL ID ORDER.
    `run_battery.py:592` calls `parse_answers(text, [it["id"] for it in items])`, and `items`
    there is the bank in id order -- the shuffle lives in `build_prompt` and does not reach
    this list. `parse_answers` emits its answers in the order of the ids it was given, so
    reading them out of the forcing prompt (which IS shuffled) re-derives the same answers in
    presentation order. Every field would compare equal except the order of the array, and
    the dry run duly reported all 403 valid records as "would change". Semantically identical,
    and it would have rewritten the whole corpus for nothing -- which is exactly the kind of
    diff that makes a real change impossible to see.
    """
    ids = set()
    for line in (rec.get("forcing_prompt") or "").split("\n"):
        head = line.split(".", 1)[0].strip()
        if head.isdigit():
            ids.add(int(head))
    for a in rec.get("answers") or []:
        if isinstance(a, dict) and a.get("q") is not None:
            ids.add(a["q"])
    return sorted(ids) or list(range(1, (rec.get("n_items") or 0) + 1))


def rederive(rec):
    """-> (new_fields, reason) or (None, why_not). Pure; does not mutate `rec`."""
    text = rec.get("response_text")
    if text is None:
        return None, "no response_text stored -- nothing to re-derive from"
    answers, problems = parse_answers(text, item_ids(rec))
    # SIGNATURE ORDER IS (problems, n_answers, tokens_out, max_tokens, text) -- taken from the
    # collector's own call site at run_battery.py:608, not from memory. Called with `text`
    # first it raises on a list, which is the loud failure; called with two argument lists
    # that happen to be type-compatible it would silently classify the wrong thing.
    mode = classify_failure(problems, len(answers), rec.get("tokens_out") or 0,
                            rec.get("max_tokens") or 0, text)
    return {
        "answers": [{"q": q, "position": p} for q, p in answers] if answers
                   and isinstance(answers[0], tuple) else answers,
        "n_answers": len(answers),
        "problems": problems,
        "failure_mode": mode,
        "valid": not problems,
        "classifier": CLASSIFIER_VERSION,
    }, None


def scan(run_dir):
    """Every record whose derived fields would move, with the before and after."""
    changes, unchanged, skipped = [], 0, []
    stored_versions = collections.Counter()
    for path in sorted(glob.glob(os.path.join(run_dir, "*.jsonl"))):
        for lineno, line in enumerate(io.open(path, encoding="utf-8"), 1):
            if not line.strip():
                continue
            rec = json.loads(line)
            stored_versions[rec.get("classifier")] += 1
            new, why = rederive(rec)
            if new is None:
                skipped.append((path, lineno, why))
                continue
            moved = {k: (rec.get(k), v) for k, v in new.items()
                     if k != "classifier" and rec.get(k) != v}
            if moved:
                changes.append((path, lineno, rec, new, moved))
            else:
                unchanged += 1
    return changes, unchanged, skipped, stored_versions


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("run", help="run directory name under runs/, or a path")
    ap.add_argument("--apply", action="store_true", help="rewrite the files in place")
    a = ap.parse_args(argv)

    run_dir = a.run if os.path.isdir(a.run) else os.path.join(STUDY, "runs", a.run)
    if not os.path.isdir(run_dir):
        print("no such run directory: %s" % run_dir)
        return 2

    changes, unchanged, skipped, stored = scan(run_dir)
    total = sum(stored.values())
    if not total:
        # A RE-DERIVATION OVER NOTHING IS NOT A CLEAN ONE.
        print("CHECKED NOTHING -- %s holds no records. This is not a pass." % run_dir)
        return 2

    print("RE-DERIVE LABELS -- %s" % os.path.basename(run_dir))
    print("  records            %d" % total)
    print("  stored classifier  %s"
          % ", ".join("%s x%d" % (k, v) for k, v in sorted(stored.items(), key=str)))
    print("  current classifier %s" % CLASSIFIER_VERSION)
    print("  would change       %d" % len(changes))
    print("  already agree      %d" % unchanged)
    if skipped:
        print("  cannot re-derive   %d (no response_text)" % len(skipped))
    print("")

    # THE VERSION MUST HAVE MOVED. Stamping the version already on the records makes the
    # change invisible to refusal_table.audit, which partitions by exactly this field -- the
    # defect that hid the last parser fix for a day.
    if changes and CLASSIFIER_VERSION in stored:
        print("REFUSING -- %d record(s) already carry %s, the version this would stamp."
              % (stored[CLASSIFIER_VERSION], CLASSIFIER_VERSION))
        print("A fix that changes what the rule DECIDES is a new version of the rule, or the")
        print("audit cannot see that stored labels and current code disagree. Bump")
        print("CLASSIFIER_VERSION in run_battery.py first.")
        return 1

    by_model = collections.Counter()
    for _p, _l, rec, _new, moved in changes:
        by_model[(rec.get("model"), rec.get("failure_mode"),
                  moved.get("failure_mode", (None, None))[1])] += 1
    for (model, was, now), n in sorted(by_model.items(), key=str):
        print("  %-38s %-16s -> %-16s x%d" % (model.split("/")[-1][:38], was, now, n))
    print("")
    flips = [c for c in changes if "valid" in c[4] and c[4]["valid"][1]]
    if flips:
        print("%d record(s) become VALID that are stored as failures:" % len(flips))
        for _p, _l, rec, new, _m in flips:
            print("  %-34s %s seed %-4s  %d of %d answers parse"
                  % (rec.get("model", "")[:34], rec.get("condition"), rec.get("shuffle_seed"),
                     new["n_answers"], rec.get("n_items") or 0))
        print("")

    if not a.apply:
        print("DRY RUN. Nothing written. Re-run with --apply once the list above is read.")
        return 0 if not changes else 1

    # IMMUTABLE FIELDS ARE VERIFIED, NOT TRUSTED.
    for path, lineno, rec, new, _m in changes:
        for k in IMMUTABLE:
            if k in new:
                print("REFUSING -- re-derivation would rewrite %r, which is a measurement." % k)
                return 1

    touched = collections.Counter()
    for path in sorted({c[0] for c in changes}):
        rows = []
        for line in io.open(path, encoding="utf-8"):
            if not line.strip():
                continue
            rec = json.loads(line)
            new, why = rederive(rec)
            if new is not None:
                before = {k: rec.get(k) for k in IMMUTABLE}
                rec.update(new)
                assert all(rec.get(k) == v for k, v in before.items()), path
                touched[path] += 1
            rows.append(rec)
        with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
            for rec in rows:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print("re-derived %d record(s) across %d file(s), stamped %s"
          % (sum(touched.values()), len(touched), CLASSIFIER_VERSION))
    print("Record this in a dated correction note: the labels moved, the measurements did not.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
