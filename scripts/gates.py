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
    Gate("position_analysis.py", ["--selftest"], tree="either", stage="release",
         label="6  the position estimator is validated",
         covers="position, consistency and acquiescence against synthetic input whose true "
                "answer is known -- a consistent skeptic scores +1.5, a pure yea-sayer scores "
                "0 with acquiescence +1. The estimator was written before the data so it "
                "cannot be shaped by it, and its selftest passed for a week while its "
                "real-data path was a stub that printed 'Phase 4 has not been collected yet' "
                "over 580 valid sheets. The selftest is necessary and it was not sufficient; "
                "tests/test_position_analysis_reads_the_corpus.py is the other half"),
    Gate("check_outcomes_computable.py", tree="either", stage="prerun",
         label="every pre-registered outcome computes",
         covers="runs the real estimator against the real corpus and requires a value out: "
                "position/consistency/acquiescence, the four pre-registered contrasts, the "
                "five committed predictions, and the floors. THE JOIN NOTHING MADE -- "
                "collection was gated and analysis was gated and nothing asked whether the "
                "analysis can read what the collection produces, so the primary estimator "
                "spent four passes and 702 records broken in four independent ways behind a "
                "green selftest. A FAILING PREDICTION DOES NOT FAIL THIS GATE: it asks "
                "whether an outcome can be computed, never whether it was confirmed",
         why="collecting more data cannot fix an analysis that cannot read it, so this belongs "
             "in front of the spend and nowhere else"),
    Gate("check_retired_instrument.py", tree="either", stage="prerun",
         label="no retired instrument is named in the live tree",
         covers="every .py/.md/.json in the tree except withdrawn/, export/ and runs/, for "
                "any string identifying a bank this study has retired. Two were purged and "
                "both came back -- as an analysis default, a constant, a gate pointed at a "
                "withdrawn file, help text calling a retired bank the live instrument, and a "
                "pre-run skill declaring LIVE_INSTRUMENT to be the withdrawn one. Not as "
                "data: no record under runs/ has named a retired bank since 2026-09-16. It "
                "came back as NAMES, and a name in a default is one missing argument from "
                "being data again. Citations to other people's published work are declared "
                "per file with a reason, because rewriting a third-party title to clear a "
                "grep is falsification -- done here on 2026-09-16, ~121 mangled references",
         why="it answers 'is the collection about to run on the right instrument', which is "
             "a question about a run being written, not about a repository being released"),
    Gate("check_arm_match.py", ["--quant-known"], tree="either", stage="prerun",
         label="arm labels match the records",
         covers="a run's declared condition against what its records carry, and the "
                "requantisation pair list against the builds actually installed",
         why="a collection-time check: it answers a question about a run being "
             "written, not about the repository being released. REGISTERED WITH NO "
             "ARGUMENTS UNTIL 2026-09-17, so it exited 2 on its own usage message and "
             "the preflight read that as NOT APPLICABLE -- a gate that has never once "
             "run, reported as one that did not need to"),
    # MOVED OUT OF prerun 2026-09-17. `audit_response_quality --check` audits the MAY judged
    # corpus -- 23,032 scored records, 547 empty-with-score -- which is PRESERVED, so the
    # check properly fails and cannot be made to pass by any pre-collection action. A gate
    # that is red before every collection forever is a gate whose red is ignored, and it was
    # one of the three red when the registry was executed for the first time. It belongs
    # where a preserved corpus is examined, not in front of a spend.
    Gate("audit_response_quality.py", ["--check"], tree="either", stage="manual",
         label="response quality (May judged corpus)",
         covers="truncation, blanks and degenerate responses in the preserved May corpus",
         why="its subject is a preserved corpus whose known defects are recorded rather "
             "than repaired, so it reports them every time by design; run it when "
             "auditing that corpus, not before collecting a new one"),

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
    Gate("instantiate_stems.py", ["--stems", "data/faction-stems.json", "--check"],
         tree="study", stage="prerun",
         label="the factions bank still matches its stems",
         covers="data/ratchet-factions.json is re-derived from the authored stems and diffed "
                "field by field against the file on disk, so a hand edit to the instrument "
                "models are actually shown is caught. The first version never opened the "
                "bank -- it rebuilt the items in memory and verified the rebuild, which is a "
                "function checked against its own inverse",
         why="NOT APPLICABLE (exit 2) until the author has written the stems and built the "
             "bank; it reports that rather than passing silently"),
    # RETIRED 2026-09-17 with the bank it checked. `build_item_bank.py --check` verified
    # a 60-item bank an assistant generated and
    # substituted for the author's instrument -- against a fresh build. Its central rule,
    # "every pair is the same sentence with one inserted 'not'", CANNOT be applied to the
    # live instrument: the Ratchet battery's mirrored halves are re-worded opposing framings,
    # authored, not derived. A generator and its gate travel with the bank they serve, and
    # both are in `withdrawn/i3/`. See LEARNINGS #19 -- verify the mirror, never generate it.
    # MOVED OUT OF prerun 2026-09-17. It validates `protocol/three-axis-items-DRAFT.json` in
    # the mirror -- a THIRD assistant-drafted item set whose own header reads "DRAFT -- NOT
    # FROZEN. Collection must not begin against this file." A gate in front of a collection
    # that passes on a file collection must not begin against is answering a question nobody
    # asked, and its green contributed to a preflight that was otherwise red. The author has
    # not ruled on whether that draft stays; until he does it is not a precondition of
    # anything.
    Gate("three_axis_score.py", ["--check"], tree="mirror", stage="manual",
         label="three-axis item set validates",
         covers="the three-axis DRAFT item set's own structure",
         why="its subject is a draft the author has not ruled on, and which says in its own "
             "header that collection must not begin against it"),
    Gate("build_corpus_fingerprint.py", ["--check"], tree="study", stage="prerun",
         label="corpus fingerprint matches",
         covers="the .corpus-fingerprint files against the item text on disk",
         why="a collection-time check against material that does not ship"),
    # MOVED OUT OF prerun 2026-09-17: it regenerates the WEBSITE's payload from the May
    # corpus. Nothing about it changes what a new collection will produce, and a gate in
    # front of a spend should answer "will this spend buy usable data".
    Gate("build_experiment.py", ["--check"], tree="study", stage="manual",
         label="the experiment payload is current",
         covers="the website's generated experiment JSON against runs/",
         why="it regenerates a website payload from the preserved corpus, so it runs when "
             "the website is published, not before a collection"),

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


def execute(gate, timeout=900):
    """Run one gate. Returns (rc, first_line_of_output).

    rc 0 pass, 1 defect, 2 NOT APPLICABLE -- the project's convention, honoured here so a
    gate that cannot apply in this tree is never counted as a pass.
    """
    import subprocess
    cwd = gate.cwd()
    if cwd is None:
        return 2, "NOT APPLICABLE: needs the %s tree, which is not here" % gate.tree
    argv = ([sys.executable, "-m", "pytest", "-q"] if gate.script == "pytest"
            else [sys.executable] + gate.argv())
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    try:
        r = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout, env=env)
    except Exception as exc:                                    # noqa: BLE001
        return 1, "did not run: %s" % exc
    blob = ((r.stdout or "") + (r.stderr or "")).strip()
    out = blob.splitlines()
    last = out[-1] if out else ""
    # AN ARGPARSE USAGE ERROR IS NOT "NOT APPLICABLE". argparse exits 2 on a bad command
    # line, and 2 is this project's NOT APPLICABLE code -- so a gate registered with
    # arguments it rejects reported `n/a` forever and was counted as "did not need to run".
    # `check_arm_match.py` is registered with no arguments and requires them; it has read as
    # n/a since the registry was written. A gate that cannot be invoked is a FAILED gate.
    if r.returncode == 2 and "usage:" in blob and "error:" in blob:
        return 1, ("registered with a command line it rejects -- %s"
                   % next((l for l in out if "error:" in l), last))
    return r.returncode, last


def preflight(stage="prerun", timeout=900, echo=print):
    """RUN every gate at a stage. Returns the list of (gate, rc, line) that did not pass.

    WHY THIS FUNCTION EXISTS
    ------------------------
    The registry below has had a `prerun` stage since it was written, and until 2026-09-17
    NOTHING EXECUTED IT. `release_check.py` was the only importer, and it runs the release
    stage. The pre-collection gates were a list, and a list is checked by whoever remembers it.

    What the collection runner actually did was hand-wire two of them -- the instrument
    sign-off and the budget probe -- directly into its own `main()`. Both were added the day
    after the defect they catch. Every other prerun gate sat in the registry, named, described,
    and never called in front of a spend.

    That is this project's signature failure pointed at its own process: the knowledge was
    written down, the checklist was derived, and the execution path checked two of nine items.
    A pattern that is not executable is not a pattern, it is a memoir.

    rc 2 is NOT a failure -- it is a gate that does not apply in this tree, and it is reported
    as such rather than silently counted green.
    """
    failed, passed, na = [], 0, 0
    rows = for_stage(stage)
    if not rows:
        # A PREFLIGHT OVER NOTHING MUST NOT READ AS CLEAN. Same rule as every other gate here.
        raise AssertionError("no gates registered at stage %r -- preflight checked nothing"
                             % stage)
    echo("PREFLIGHT -- %d gate(s) at stage %s, in the %s tree"
         % (len(rows), stage, "MIRROR" if THIS_IS_MIRROR else "private study"))
    for g in rows:
        rc, line = execute(g, timeout=timeout)
        mark = {0: "pass", 2: "n/a "}.get(rc, "FAIL")
        echo("  %s  %-44s %s" % (mark, g.label[:44], line[:88]))
        if rc == 0:
            passed += 1
        elif rc == 2:
            na += 1
        else:
            failed.append((g, rc, line))
    echo("  %d passed, %d not applicable, %d FAILED" % (passed, na, len(failed)))
    return failed


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--stage", choices=STAGES, help="only gates at this stage")
    ap.add_argument("--ungated", action="store_true",
                    help="only gates nothing runs automatically, with the reason")
    ap.add_argument("--run", action="store_true",
                    help="EXECUTE the gates at --stage (default prerun) instead of listing "
                         "them. Exit 1 if any fails. This is what run_i3_wave --run calls "
                         "before it spends anything.")
    a = ap.parse_args(argv)

    if a.run:
        failed = preflight(a.stage or "prerun")
        if failed:
            print()
            print("COLLECTION IS NOT SAFE TO START. %d gate(s) failed:" % len(failed))
            for g, rc, line in failed:
                print("  %s (exit %d) -- %s" % (g.label, rc, g.covers))
            return 1
        return 0

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
