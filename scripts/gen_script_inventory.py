#!/usr/bin/env python3
"""Generate SCRIPTS.md from the scripts' own docstrings. Never hand-maintained.

WHY
---
Measured 2026-09-05: `scripts/` holds 58 Python files and **44 of them appear in no
documentation in this repository** -- not DEVELOPER.md, not the paper, not the plan. Among the
missing were `key_numbers.py` and `gen_paper.py`, which are the two gates that decide whether
the paper is allowed to make a claim, and `export_scrubbed.py`, which is the only thing standing
between this repo and republishing someone else's licensed questionnaire.

That is the same defect the sibling `publishing-tools` repo found in itself (27 of 39
undocumented) and fixed the same way: derive the list from the code, so it cannot drift. A
hand-written list of 58 entries is 58 facts kept in two places.

This is worse in the public mirror than here. A stranger cloning the repo to replicate the
study meets a `scripts/` directory with no map.

    python scripts/gen_script_inventory.py           # write SCRIPTS.md
    python scripts/gen_script_inventory.py --check   # exit 1 if stale (gate)

A SCRIPT WITH NO DOCSTRING IS REPORTED, NOT SKIPPED. It gets a row saying so, because a file
that cannot describe itself is the one most likely to be doing something nobody remembers.
"""
from __future__ import annotations

import argparse
import ast
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
OUT = os.path.join(STUDY, "SCRIPTS.md")

#: Substring -> section. First match wins, so order matters. A script matching nothing lands in
#: "Other", which is a prompt to either name it better or add a group -- not a dumping ground to
#: be ignored.
GROUPS = [
    ("Collection", ("run_battery", "run_study", "recollect", "wave", "lineage_sweep",
                    "roster_gap", "extend_manipulation", "refusal_ablation", "mask_gradient",
                    "run_g0dm0d3", "order_robustness", "ingest_agent")),
    ("Floors, power and detection limits", ("floor_table", "power", "chart_floors",
                                            "check_arm_match", "classify_lineage",
                                            "drift_report", "drift_timeseries")),
    ("Scoring and the judge panel", ("score", "judge", "cross_method", "ci_analysis",
                                     "analyze", "build_experiment", "hedge_escape",
                                     "evidence_concordance")),
    ("Gates and generated prose", ("key_numbers", "gen_paper", "controls_audit",
                                   "refusal_table", "references", "timeline",
                                   "add_controls", "gen_script_inventory", "generate_charts")),
    ("Replicating other people's studies", ("replicate_", "rederive_")),
    ("Release and provenance", ("export_scrubbed", "build_corpus_fingerprint", "check_corpus",
                                "fetch_items", "studypaths", "sweep_status")),
    ("Tests and development", ("test_", "_shim", "_retire", "check_no_fork", "demo_switch")),
]


def summary(path):
    """First paragraph of the module docstring, flattened. None when there is no docstring."""
    try:
        tree = ast.parse(io.open(path, encoding="utf-8", errors="replace").read())
    except SyntaxError:
        return "(does not parse)"
    doc = ast.get_docstring(tree)
    if not doc:
        return None
    first = doc.strip().split("\n\n")[0]
    return " ".join(first.split())


def group_of(name):
    for label, needles in GROUPS:
        if any(n in name for n in needles):
            return label
    return "Other"


def render():
    names = sorted(f for f in os.listdir(HERE) if f.endswith(".py"))
    rows = [(n, summary(os.path.join(HERE, n))) for n in names]
    undocumented = [n for n, s in rows if s is None]

    out = ["# Scripts", "",
           "**Generated from the scripts' own docstrings by "
           "`scripts/gen_script_inventory.py`. Do not edit.** Rebuild after adding a script; "
           "`--check` exits 1 when this file is stale.", "",
           "%d script(s). %d carry no module docstring and are listed at the end."
           % (len(rows), len(undocumented)), ""]

    by_group = {}
    for name, text in rows:
        by_group.setdefault(group_of(name), []).append((name, text))

    order = [g for g, _ in GROUPS] + ["Other"]
    for label in order:
        items = [(n, t) for n, t in by_group.get(label, []) if t is not None]
        if not items:
            continue
        out.append("## %s" % label)
        out.append("")
        for name, text in items:
            out.append("- **`%s`** — %s" % (name, text))
        out.append("")

    if undocumented:
        out.append("## No module docstring")
        out.append("")
        out.append("A file that cannot describe itself is the one most likely to be doing "
                   "something nobody remembers. These are listed so the gap is visible, not "
                   "hidden by omission.")
        out.append("")
        for name in undocumented:
            out.append("- `%s`" % name)
        out.append("")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)

    # EXACTLY ONE TRAILING NEWLINE, and the same text --check compares against.
    #
    # This wrote `want + "\n"` while render() already ended in one, so every run left
    # SCRIPTS.md ending "\n\n" -- and the pre-commit `end-of-file-fixer` trimmed it back
    # on every single commit. Meanwhile `--check` compared with .strip() on both sides,
    # so it was blind to the difference and reported the file current. Two checkers with
    # different opinions about the same file, one of them rewriting it behind the other:
    # the generator said clean, the hook said dirty, and the commit failed three times
    # before anyone looked at why.
    want = render().rstrip("\n") + "\n"
    have = io.open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
    if args.check:
        if have.replace("\r\n", "\n") != want:
            print("SCRIPTS.md is stale. Run: python scripts/gen_script_inventory.py")
            return 1
        print("SCRIPTS.md matches the scripts on disk.")
        return 0

    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(want)
    n = want.count("\n- **`")
    # STDERR, NOT STDOUT. This script WRITES the file itself, so anything on
    # stdout is a confirmation message and never content -- and on 2026-09-15
    # SCRIPTS.md was found committed with this line as its first line, the header
    # gone. The cause is `gen_script_inventory.py > SCRIPTS.md`: the redirect
    # truncates the file the program just wrote and captures the message instead.
    #
    # An ordinary mistake, and the file it corrupted is the one the README calls
    # "gated so it cannot drift from what is actually there". CI caught it, as
    # step 7, by going red on a push -- which is the expensive place to catch a
    # thing that can be made impossible here for one word.
    print("wrote %s (%d documented script(s))" % (os.path.relpath(OUT, STUDY), n),
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
