#!/usr/bin/env python3
"""Fail if a skill document names a script that does not exist or a flag that was never added.

WHY THIS EXISTS
---------------
The skills in `skills/` are the repeatability layer: they are what a future run follows instead
of rediscovering the procedure. Nothing checked them against the code.

Two findings on the day this was written, 2026-09-07:

  * **Eight of the nine scripts that run the current instrument were named by NO skill.**
    `wave.py`, `order_floor_wave.py`, `ablation_wave.py`, `floor_table.py`,
    `floor_resolution.py`, `model_cards.py`, `frontier_extend.py` and
    `chart_intervention_budget.py` were undocumented as a procedure, so every trap in them was
    found by hand and one was found twice.
  * The first draft of the skill written to fix that named `scripts/ablation_wave.py`, which
    was not in this repository, and `wave.py --report`, which is not a flag -- `--plan` is.
    Both were caught by running this, not by reading it.

A procedure document that names a dead path is worse than no document: it reads as verified and
sends the next run down it. So the paths and the flags are gated, the same way SCRIPTS.md and
the README's numbers are.

WHAT IT CHECKS
--------------
  paths    every `scripts/x.py` or `data/x.json` in backticks resolves on disk
  flags    every `--flag` in a `python scripts/x.py ...` command line appears in that
           script's own `--help`
  coverage every script in scripts/ that is a documented ENTRY POINT is named by some skill,
           unless it is listed in NOT_A_PROCEDURE below

Coverage is a WARNING by default and a failure under --strict, because "every script must be
in a skill" is not true -- helpers, shims and tests are not procedures -- and a gate that
demands it would be switched off wholesale within a week.

    python scripts/check_skill_docs.py            # exit 1 on a dead path or flag
    python scripts/check_skill_docs.py --strict   # also fail on an undocumented entry point
    python scripts/check_skill_docs.py --coverage # just the coverage report
"""
from __future__ import annotations

import argparse
import glob
import io
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SKILLS = os.path.join(ROOT, "skills")

#: Scripts that are deliberately not part of any procedure. Each needs a reason, so that
#: adding one is a decision rather than a way to quiet the report.
NOT_A_PROCEDURE = {
    "add_controls_2026_09.py": "one-shot migration, run once with --apply on 2026-09-05 to add "
                               "four columns to the audit matrix. Kept because its docstring is "
                               "the record of WHY those four are columns and why every external "
                               "study is scored `unknown` rather than `no` -- controls_audit.py "
                               "cites it by name",
    "studypaths.py": "shared path/RNG resolution, imported never invoked",
    "references.py": "bibliography helper",
    "gen_readme.py": "named by barometer-wave step 4 via its --check form",
    "check_skill_docs.py": "this checker",
    "fetch_items.py": "reader-side instrument retrieval, documented in README not a skill",
    "selftest_analysis.py": "self-test, runs under pytest",
    "monitor_experiment.py": "operator convenience over a running collection",
    "dose_smoke_gate.py": "coherence gate inside abliteration-run",
    "supervised_dose_series.py": "driven by abliteration-run",
    "run_dose_series.py": "driven by abliteration-run",
    "paired_analysis.py": "helper for bias-study-report",
    "validate_runs.py": "helper, called by prep",
    "check_corpus.py": "pre-commit hook; named by barometer-wave step 0",
    "check_arm_match.py": "imported by floor_table for the eligibility lists",
    "classify_lineage.py": "imported by floor_table",
    "judge_methods.py": "imported by the sweep skills",
    "timeline.py": "one-off figure",
    "roster_gap.py": "one-off roster diff",
    "replicate_rottger.py": "external-replication one-off",
    "abliteration_effect_check.py": "called by bias-study-report",
    "controls_audit.py": "called by bias-study-report",
    "drift_report.py": "called by bias-study-report",
    "drift_timeseries.py": "called by bias-study-report",
    "ci_analysis.py": "called by bias-study-report",
    "cross_method_report.py": "called by cross-method-analysis",
    "robustness_checks.py": "called by bias-study-report",
    "generate_charts.py": "called by bias-study-report",
    "chart_floors.py": "called by bias-study-report",
    "aggregate.py": "called by bias-study-report",
    "analysis.py": "called by bias-study-report",
    "score.py": "called by the sweep skills",
    "score_inproc_gemma.py": "called by abliterated-judge-sweep",
    "run_local.py": "called by abliteration-run",
    "run_g0dm0d3.py": "called by g0dm0d3-pipeline",
    "run_study.py": "called by the sweep skills",
    "dl_model.py": "called by abliteration-run",
    "sweep_status.py": "operator convenience during a sweep",
    "gen_script_inventory.py": "named by barometer-wave step 4",
    "gen_paper.py": "private-tree paper generator",
    "power.py": "named by barometer-wave step 3",
    "key_numbers.py": "named by barometer-wave step 4",
    "extend_manipulation_floor.py": "superseded by ablation_wave/wave",
    "check_no_fork.py": "named by barometer-wave step 0",
    # A FEASIBILITY PROTOTYPE FOR A v3 INSTRUMENT, deliberately not in the current procedure.
    # It scores the battery by logprob instead of parsing prose, failed its pre-registered
    # agreement check against the parsed instrument (24 of 62 exact, 20 side-flips against a
    # replicate floor of 5) and is kept as the measured account of why the obvious design
    # fails. Naming it in barometer-wave would put a rejected instrument in the procedure a
    # future run follows.
    "logit_probe.py": "v3 feasibility prototype; failed its agreement check, kept as evidence",
    # `constrained_probe.py` WAS DECLARED HERE and no longer is. It sat next to logit_probe as
    # a rejected v3 prototype on the strength of one batch size -- the whole 62-item sheet in a
    # single array, which does not agree with itself. Sweeping items-per-call showed the arm
    # replicating once the array is broken up, so it is a real arm with a real gate and belongs
    # in barometer-wave's Files list, which now documents it. Removed rather than left as a
    # second, staler copy of its status: this dict and the skill would have disagreed, and the
    # reason string here still said "17 side-flips from the parser", a number from a superseded
    # reading of a mode nobody should now run.
}


def skill_docs():
    return sorted(glob.glob(os.path.join(SKILLS, "*", "*.md")))


def read(path):
    return io.open(path, encoding="utf-8", errors="replace").read()


#: Paths a procedure may name that are DELIBERATELY not in the repository, with the reason.
#: Added 2026-09-11, when cloning this repo into a temp directory and running its own gates as a
#: reader would showed this check failing on a fresh clone while passing in the working copy.
#: The message said "fix the document, or add the flag to the script" -- but that hatch exists
#: only for flags, so a path that must never ship had nowhere to be declared and the only way to
#: green was to delete a true sentence from a procedure.
#: This is a declaration, not a loosening: every other dead path still fails, and a declared path
#: that STARTS existing fails too (see below), so the list cannot quietly rot.
NOT_IN_REPO = {
    "data/compass-propositions.json":
        "third-party instrument text -- the 62 politicalcompass.org propositions, fetched at the "
        "reader's end by scripts/fetch_items.py so this repository never republishes them. "
        "Ignored in .gitignore and refused by a pre-commit hook; both must stay.",
}


def check_paths(text):
    """Backticked repo paths that do not resolve, excluding those declared NOT_IN_REPO."""
    out = []
    for p in sorted(set(re.findall(r"`((?:scripts|data)/[A-Za-z0-9_.\-]+)`", text))):
        if p in NOT_IN_REPO:
            continue
        if not os.path.exists(os.path.join(ROOT, p)):
            out.append(p)
    return out


def check_not_in_repo_still_absent():
    """A declared-absent path that is now TRACKED is a declaration that has rotted.

    Without this, NOT_IN_REPO would silently suppress a real dead-path check the day someone
    commits the file it excuses -- which, for this particular entry, would also mean the
    repository had just republished third-party instrument text.

    The condition is TRACKED, not "exists on disk". These paths are fetched at the reader's
    end, so the file being present locally is the normal state and the whole point -- the
    first draft of this check asserted absence on disk and fired immediately on a working
    copy that had simply run fetch_items.py.
    """
    try:
        r = subprocess.run(["git", "ls-files", "--"] + sorted(NOT_IN_REPO),
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=60, cwd=ROOT)
    except Exception:                                   # noqa: BLE001
        return []                                       # no git: cannot judge, do not block
    return sorted(p for p in r.stdout.splitlines() if p.strip())


_HELP: dict[str, str] = {}


def help_text(script):
    if script not in _HELP:
        try:
            r = subprocess.run([sys.executable, os.path.join(ROOT, script), "--help"],
                               capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=300, cwd=ROOT)
            _HELP[script] = (r.stdout or "") + (r.stderr or "")
        except Exception as exc:                       # noqa: BLE001
            _HELP[script] = "ERROR: %s" % exc
    return _HELP[script]


def check_flags(text):
    """Flags used on a command line that the script's own --help does not list."""
    out = []
    for script, tail in re.findall(
            r"python (scripts/[A-Za-z0-9_.\-]+\.py)((?: --?[A-Za-z0-9-]+(?:\s+\S+)?)*)", text):
        if not os.path.exists(os.path.join(ROOT, script)):
            continue          # already reported by check_paths
        h = help_text(script)
        if h.startswith("ERROR:"):
            out.append((script, "--help", h.strip()[:90]))
            continue
        for f in re.findall(r"--[A-Za-z0-9-]+", tail):
            if f not in h:
                out.append((script, f, "not in --help"))
    return out


def coverage():
    """Scripts in scripts/ that no skill names, minus the declared non-procedures."""
    named = set()
    for d in skill_docs():
        for m in re.findall(r"([A-Za-z0-9_]+\.py)", read(d)):
            named.add(m)
    missing = []
    for p in sorted(glob.glob(os.path.join(HERE, "*.py"))):
        base = os.path.basename(p)
        if base.startswith(("_", "test_")):
            continue
        if base in NOT_A_PROCEDURE or base in named:
            continue
        missing.append(base)
    return missing


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--strict", action="store_true",
                    help="also fail when an entry point is named by no skill")
    ap.add_argument("--coverage", action="store_true", help="only the coverage report")
    args = ap.parse_args(argv)

    docs = skill_docs()
    if not args.coverage:
        rotted = check_not_in_repo_still_absent()
        if rotted:
            print("DECLARATION ROTTED -- these are declared NOT_IN_REPO and now exist:")
            for p in rotted:
                print("    %s" % p)
            print("Either the file should not be committed, or the declaration should go.")
            return 1
        bad_paths, bad_flags = [], []
        for d in docs:
            rel = os.path.relpath(d, ROOT).replace("\\", "/")
            for p in check_paths(read(d)):
                bad_paths.append((rel, p))
            for script, flag, why in check_flags(read(d)):
                bad_flags.append((rel, script, flag, why))

        print("checked %d skill document(s) in %d skill(s)"
              % (len(docs), len({os.path.dirname(d) for d in docs})))
        print("  dead paths: %d    unknown flags: %d" % (len(bad_paths), len(bad_flags)))
        for rel, p in bad_paths:
            print("  DEAD PATH  [%s] %s" % (rel, p))
        for rel, script, flag, why in bad_flags:
            print("  BAD FLAG   [%s] %s %s -- %s" % (rel, script, flag, why))
        if bad_paths or bad_flags:
            print("")
            print("A procedure document that names a dead path reads as verified and sends the")
            print("next run down it. Fix the document, or add the flag to the script.")
            return 1

    missing = coverage()
    if missing:
        print("")
        print("%d script(s) named by no skill and not declared a non-procedure:" % len(missing))
        for m in missing:
            print("   %s" % m)
        print("Either name it in a skill, or add it to NOT_A_PROCEDURE with the reason.")
        if args.strict:
            return 1
    else:
        print("every entry point is either named by a skill or declared a non-procedure.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
