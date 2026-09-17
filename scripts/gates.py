#!/usr/bin/env python3
"""The one registry of every gate this study has, and where each one runs.

WHY THIS FILE EXISTS
--------------------
This repository accumulated checkers the way a house accumulates keys. On
2026-09-16 there were 13 scripts named `check_*` / `validate_*` / `audit_*` /
`selftest_*`, 16 more carrying a `--check` flag, and a release checklist that
invoked 17 of them. Nothing said where the others belonged, or whether their
absence was a decision or an oversight. Two of them turned out to be oversights.

A pile of individually-sensible checks is not a system. The failure mode is not
that a check is wrong -- it is that nobody can answer "what does this repository
verify, and what does it not", so a gap is indistinguishable from a choice.

So: every gate is declared here once, with what it covers, which tree it can run
in, and which stage runs it. `release_check.py` derives its checklist from this
list rather than keeping a second copy, and `tests/test_gate_registry.py` fails
if a checker exists on disk and is not declared. A new gate cannot be added
without saying where it belongs.

WHICH TREE, AND WHY IT MATTERS
------------------------------
There are two trees: the private working study and the public mirror. Some gates
only have a question to answer in one of them -- `check_no_fork` needs both trees
to compare, `--check-website` needs the website sources, `check_named_scripts`
has to run in the MIRROR because the tree that has every script is the tree that
cannot see a missing one.

Getting this wrong is not a small thing. Until 2026-09-16 `release_check` resolved
the mirror path relative to the private tree, so from a clone it pointed at a
directory that does not exist and nine checks died with WinError 267. The fix --
falling back to "this tree is the mirror" -- then created the opposite defect:
the study-side checks silently re-ran the MIRROR suite under a study label, and
the checklist printed "gates green (study suite)" having never opened the study.
A gate that reports on a tree it did not read is worse than one that refuses.

So a gate declares the tree it needs, and when that tree is not present the gate
reports NOT APPLICABLE (exit 2) instead of running somewhere else.

    gates.py             # print the map: every gate, stage, tree, coverage
    gates.py --stage release
    gates.py --ungated   # what nothing runs, and the declared reason
"""
from __future__ import annotations

import argparse
import os
import sys

STUDY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: The sibling public mirror, when this is the private tree. None when this IS the mirror.
_SIBLING = os.path.normpath(os.path.join(STUDY, "..", "..", "..", "bias-study-release"))
MIRROR = _SIBLING if os.path.isdir(_SIBLING) else None

#: True when the tree this file sits in is the public mirror.
THIS_IS_MIRROR = MIRROR is None

#: Where a gate can run. "either" means the question is the same in both trees.
TREES = ("mirror", "study", "either")

#: When a gate runs. "release" is release_check's checklist; "prerun" is the
#: bias-study-prep skill's pre-collection gates; "manual" is run on demand and the
#: registry says why it is not automatic.
STAGES = ("release", "prerun", "manual")


class Gate:
    def __init__(self, script, args=(), *, tree="either", stage="release",
                 label=None, covers="", why=""):
        self.script = script
        self.args = list(args)
        self.tree = tree
        self.stage = stage
        self.label = label or script.replace(".py", "")
        self.covers = covers
        #: Required for stage "manual": why nothing runs this automatically.
        self.why = why

    def argv(self):
        return ["scripts/%s" % self.script] + self.args

    def cwd(self):
        """The directory this gate must run in, or None when that tree is absent here."""
        if self.tree == "either" or (self.tree == "mirror" and THIS_IS_MIRROR):
            return STUDY
        if self.tree == "mirror":
            return MIRROR
        return STUDY if not THIS_IS_MIRROR else None

    def __repr__(self):
        return "<Gate %s %s/%s>" % (self.script, self.stage, self.tree)


GATES = [
    # ---- the suites -------------------------------------------------------------
    Gate("pytest", tree="either", stage="release", label="1  gates green (this tree)",
         covers="every regression test in scripts/ and tests/"),
    Gate("pytest", tree="study", stage="release", label="1  gates green (study suite)",
         covers="the private tree's own tests, which the mirror does not carry"),

    # ---- two trees, one implementation ------------------------------------------
    Gate("check_no_fork.py", tree="study", stage="release",
         label="2  check_no_fork == 0 forks",
         covers="no script exists in both trees with different contents"),

    # ---- typed numbers against generated ones -----------------------------------
    Gate("key_numbers.py", ["--check"], tree="either", stage="release",
         label="5  paper numbers match runs/",
         covers="the paper's prose against the generated numbers, plus the "
                "repo-wide retraction scan"),
    Gate("key_numbers.py", ["--check-release"], tree="mirror", stage="release",
         label="5  README + VERSIONING match runs/",
         covers="the release surfaces, and every markdown file for withdrawn claims"),
    Gate("key_numbers.py", ["--check-website"], tree="study", stage="release",
         label="5  website numbers match runs/",
         covers="evilrobots.lol's five number-bearing surfaces"),
    Gate("key_numbers.py", ["--check-books"], tree="study", stage="manual",
         label="5  printed book numbers",
         covers="chapter 22's typed figures",
         why="a printed number cannot be corrected after the fact, so this runs "
             "deliberately before a book build rather than on every release"),
    Gate("gen_readme.py", ["--check"], tree="mirror", stage="release",
         label="9  README generated blocks fresh",
         covers="the README's generated tables against runs/"),
    Gate("gen_paper.py", ["--check"], tree="study", stage="release",
         label="3  paper generated blocks fresh",
         covers="the paper's eight generated tables"),

    # ---- the data ---------------------------------------------------------------
    Gate("validate_runs.py", tree="either", stage="release",
         label="3  run data validates",
         covers="run directories against their manifests, and the NOT VALIDATED count"),
    Gate("collection_check.py", ["2026-09-13-g0dm0d3-replicate"], tree="either",
         stage="release", label="3  cited runs are fit to score",
         covers="the acceptance gate over a run a published number cites"),
    Gate("run_inventory.py", ["--check"], tree="either", stage="release",
         label="3  every run directory accounted for",
         covers="no run directory is unlisted or orphaned"),
    Gate("pipeline_transform_audit.py", tree="either", stage="release",
         label="3  the treatment was actually applied",
         covers="whether the intervention an arm is named after actually ran -- "
                "B-Parseltongue passed every other check with 0 of 240 applied"),
    Gate("check_arm_match.py", tree="either", stage="prerun",
         label="arm labels match the records",
         covers="a run's declared condition against what its records carry",
         why="a collection-time check: it answers a question about a run being "
             "written, not about the repository being released"),
    Gate("audit_response_quality.py", ["--check"], tree="either", stage="prerun",
         label="response quality",
         covers="truncation, blanks and degenerate responses in a fresh corpus",
         why="run against a collection as it lands; the release gate covers the "
             "same corpus through validate_runs and collection_check"),

    # ---- the analysis -----------------------------------------------------------
    Gate("selftest_analysis.py", tree="mirror", stage="release",
         label="9  analysis gates reproduce the writeup",
         covers="ten analysis gates re-deriving published figures from the corpus"),
    Gate("controls_audit.py", ["--strict"], tree="either", stage="release",
         label="7  external claims rest on the paper",
         covers="no verdict about another study sourced from notes rather than text"),

    # ---- what ships -------------------------------------------------------------
    Gate("check_corpus.py", ["--all"], tree="mirror", stage="release",
         label="8  no third-party instrument text",
         covers="the licensed propositions are absent from every shipped file"),
    Gate("check_no_key_repro.py", ["--quiet"], tree="mirror", stage="release",
         label="10 no-key reproduction",
         covers="the documented reproduction runs with no API key AND returns the "
                "committed artifacts byte-for-byte"),
    Gate("check_release_table.py", ["--quiet"], tree="study", stage="release",
         label="2  RELEASE-v2 arm inventory matches runs/",
         covers="the release definition's hand-typed arm table against the generated one"),

    # ---- the documents ----------------------------------------------------------
    Gate("check_doc_links.py", tree="either", stage="release",
         label="9  markdown links resolve",
         covers="every relative link in every tracked markdown file"),
    Gate("check_named_scripts.py", ["--quiet"], tree="mirror", stage="release",
         label="9  every named script exists here",
         covers="every backticked script name in a shipped document, which "
                "check_doc_links cannot see"),
    Gate("check_skill_docs.py", ["--strict"], tree="either", stage="release",
         label="9  skill docs have no dead paths",
         covers="paths and flags a skill names, and scripts no skill names"),
    Gate("gen_script_inventory.py", ["--check"], tree="either", stage="release",
         label="9  SCRIPTS.md matches disk",
         covers="the generated script inventory against what is on disk"),
    Gate("check_skill_procedures.py", tree="either", stage="prerun",
         label="documented commands actually run",
         covers="executes the allowlisted read-only documented commands",
         why="it EXECUTES documented steps, so it belongs before a collection "
             "where a broken step costs a run, not inside the release gate where "
             "it would re-run work the other gates already did"),
    Gate("floor_table.py", ["--uncomputed"], tree="either", stage="prerun",
         label="every floor arm is accounted for",
         covers="the arms that produced no row, split into a path that matches no file "
                "(exit 1), a source retired by a dated ruling, and a corpus not collected "
                "yet (exit 2). floor_same_version -- the paper's headline null -- read one "
                "hardcoded directory that had moved to withdrawn/, so a 252-sheet wave would "
                "have collected correctly and populated nothing, and the only symptom would "
                "have been a missing row",
         why="it answers 'will this collection land anywhere?', which is a question about a "
             "run about to be written, not about the repository being released. Exit 2 is "
             "the normal state between passes"),
    Gate("check_undefined_names.py", ["--check"], tree="either", stage="prerun",
         label="no undefined names in scripts",
         covers="a static pass for names used and never bound",
         why="a lint, not a claim about the study; it guards the tooling and runs "
             "with the other pre-run gates"),

    # ---- the instrument ----------------------------------------------------------
    Gate("check_instrument_approved.py", tree="either", stage="prerun",
         label="the instrument is read and signed",
         covers="the live bank has a sign-off sheet that names it with every pair "
                "ticked. render_item_read.py wrote such a sheet on 2026-09-15, every box "
                "was left empty, and 372 sheets were collected against it anyway -- "
                "nothing read the checklist back, so the gate was a document",
         why="it is a precondition of collecting, not of releasing; run_i3_wave calls it "
             "in front of the spend"),
    Gate("build_item_bank.py", ["--check"], tree="either", stage="prerun",
         label="the I3 item bank matches a fresh build",
         covers="data/ratchet-propositions-i3.json against rebuilding it -- contiguous "
                "ids, every pair one inserted 'not', counts matching its declaration",
         why="the instrument must be right BEFORE a collection, not after one"),
    Gate("three_axis_score.py", ["--check"], tree="mirror", stage="prerun",
         label="three-axis item set validates",
         covers="the three-axis item set's own structure",
         why="an instrument check, run with the others before a collection"),
    Gate("build_corpus_fingerprint.py", ["--check"], tree="study", stage="prerun",
         label="corpus fingerprint matches",
         covers="the .corpus-fingerprint files against the item text on disk",
         why="a collection-time check against material that does not ship"),
    Gate("build_experiment.py", ["--check"], tree="study", stage="prerun",
         label="the experiment payload is current",
         covers="the website's generated experiment JSON against runs/",
         why="it regenerates a website payload, so it runs where the website "
             "sources are, not in the release gate for the repository"),

    # ---- analysis scripts whose --check verifies their own output -----------------
    Gate("calibration_study.py", ["--check"], tree="mirror", stage="manual",
         label="calibration study output",
         covers="the calibration run's output against its inputs",
         why="it checks one analysis's artifacts, and that analysis is not re-run on "
             "every release; running it here would gate the repository on a study arm "
             "rather than on the repository"),
    Gate("lineage_exchangeability.py", ["--check"], tree="either", stage="manual",
         label="lineage exchangeability (STATS-LINEAGE-NULL-001)",
         covers="whether the four same-version sub-classes are exchangeable",
         why="a standing statistical question about the corpus, re-asked when the "
             "corpus changes rather than on every release; its result is a finding, "
             "not a pass/fail property of the tree"),

    # ---- per-claim, not per-repo -------------------------------------------------
    Gate("validate_claim.py", tree="either", stage="manual",
         label="one claim's evidence",
         covers="refuses a single claim until the data behind it passes every check "
                "-- distinct seeds, arm treated, interval from replicates",
         why="it takes a claim as its argument. There is no repository-wide form of "
             "it, and inventing one would mean choosing which claims to check"),
]


def for_stage(stage):
    return [g for g in GATES if g.stage == stage]


def runnable(gate):
    """Can this gate run in this tree at all?"""
    return gate.cwd() is not None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--stage", choices=STAGES, help="only gates at this stage")
    ap.add_argument("--ungated", action="store_true",
                    help="only gates nothing runs automatically, with the reason")
    a = ap.parse_args(argv)

    if a.ungated:
        rows = for_stage("manual")
        print("GATES NOTHING RUNS AUTOMATICALLY -- %d, each with its reason" % len(rows))
        print()
        for g in rows:
            print("  %s" % g.label)
            print("      %s" % g.covers)
            print("      NOT AUTOMATIC: %s" % g.why)
        return 0

    rows = for_stage(a.stage) if a.stage else GATES
    print("GATE REGISTRY -- %d gate(s)%s. This tree is the %s."
          % (len(rows), " at stage %s" % a.stage if a.stage else "",
             "MIRROR" if THIS_IS_MIRROR else "private study"))
    print()
    for stage in STAGES:
        here = [g for g in rows if g.stage == stage]
        if not here:
            continue
        print("%s (%d)" % (stage.upper(), len(here)))
        for g in here:
            mark = " " if runnable(g) else "-"
            print("  %s %-42s [%s] %s" % (mark, g.label, g.tree, g.covers))
        print()
    absent = [g for g in rows if not runnable(g)]
    if absent:
        print("%d gate(s) marked '-' need a tree that is not here and report NOT "
              "APPLICABLE (exit 2) rather than running in the wrong one." % len(absent))
    return 0


if __name__ == "__main__":
    sys.exit(main())
