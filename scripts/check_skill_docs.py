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
    "replicates.py": "a LIBRARY, not a procedure -- the single implementation of "
                     "'average the replicates in a cell', imported by aggregate, analysis, "
                     "pipeline_rung, frame_gap and abliteration_effect_check. It has no main() "
                     "and nothing to run. It exists because that three-line grouping shipped in "
                     "six scripts and was fixed one call site at a time, so the last three "
                     "survived; naming it in a skill would imply an operator step where there "
                     "is none",
    "add_controls_2026_09.py": "one-shot migration, run once with --apply on 2026-09-05 to add "
                               "four columns to the audit matrix. Kept because its docstring is "
                               "the record of WHY those four are columns and why every external "
                               "study is scored `unknown` rather than `no` -- controls_audit.py "
                               "cites it by name",
    "studypaths.py": "shared path/RNG resolution, imported never invoked",
    "export_repairs.py": "a MAINTAINER operation, not a replication step -- it copies the "
                         "repaired corpus out of the private study tree into this public one, "
                         "and a reader has no second tree to copy from. It is what put the "
                         "repaired runs HERE, so it belongs in this repository as provenance "
                         "for how the data arrived; it is not something anyone reproducing the "
                         "study runs. What a replicator needs from the repair chain is in the "
                         "bias-study-prep skill",
    "pipeline_rung.py": "the estimator for escalation-ladder rung 2, which analysis.py cannot "
                        "see because it keys on conditions A/B and that arm runs B-STM / "
                        "B-Parseltongue / B-Layered. Rerun it to re-derive the README row and "
                        "after W13 lands; not a step in collecting anything",
    "export_analysis_ready.py": "a one-shot convenience for THIRD PARTIES -- it reads the "
                                "corpus and writes a CSV somewhere else, touching nothing this "
                                "study depends on. Documented where its audience will look, "
                                "which is data/README.md, not in an internal procedure",
    "ablation_termination.py": "one-shot 2026-09-12 analysis behind "
                               "RESULTS-2026-09-12-ablation-termination.md. Asks why 24 of 63 "
                               "ablation-wave cells came back short; the answer is that one "
                               "base's ablated build runs to the token cap on every run. A "
                               "finding, not a procedure",
    "refusal_suite_summary.py": "one-shot 2026-09-12 analysis behind the second-model-pair "
                                "section of RESULTS-2026-08-28-refusal-ablation.md. Re-derives "
                                "both pairs from the raw judged records with intervals clustered "
                                "on prompt type, rather than reading the stored summary.json",
    "convergent_validity.py": "one-shot 2026-09-12 analysis behind "
                              "RESULTS-2026-09-12-convergent-validity.md. Correlates the A->B "
                              "shift measured by the judged scale against the same shift "
                              "measured by the model-free forced-choice instrument, across the "
                              "24 models that appear in both",
    "refusal_structure.py": "one-shot 2026-09-12 analysis behind "
                            "RESULTS-2026-09-12-refusal-structure.md. Shows wave-0 refusal is "
                            "whole-instrument (92% of failures return zero items) and bimodal "
                            "across models, so the per-condition rate is a mixing proportion",
    "run_inventory.py": "generated accounting of every run directory and its role. Run with "
                        "--check by release_check as a gate: a collection with records, no "
                        "schema and no mention is surfaced rather than left for the next audit "
                        "to rediscover by hand",
    "judge_lean.py": "the scoring layer's own audit, behind RESULTS-2026-09-05-judge-lean.md. "
                     "Measures the panel's per-judge lean, whether that lean cancels in a B-A "
                     "delta (it does not -- it is an interaction), the self-judging effect for "
                     "the two judges that are also subjects, and --per-finding, which re-scores "
                     "every CI-clean finding under each judge alone. Rerun to re-derive that "
                     "document, not as a step in collecting anything",
    "check_release_table.py": "release gate, run by release_check.py as checklist item 2. Not a "
                              "procedure anyone follows by hand: it re-derives RELEASE-v2's arm "
                              "inventory from runs/ and fails when the document has drifted",
    "lineage_exchangeability.py": "one-shot 2026-09-12 analysis behind "
                                  "RESULTS-2026-09-12-lineage-exchangeability.md. It asks "
                                  "whether the pooled same-version reference is exchangeable "
                                  "with the snapshot-only subset a drift claim needs, and "
                                  "finds it is not: 82 of 97 pairs are size or tier siblings. "
                                  "A finding, not a procedure -- rerun it to re-derive that "
                                  "document, not as a step in collecting anything",
    "ablation_equivalence.py": "one-shot 2026-09-12 analysis behind the ablation-wave "
                               "correction. Tests whether the n=5 arm supports an equivalence "
                               "claim rather than merely failing to reject. Same character as "
                               "lineage_exchangeability.py: it produced a dated result and is "
                               "kept so that result can be reproduced",
    "eligibility.py": "shared read-time record filter (DATA-EMPTY-SCORES-002), imported by "
                      "aggregate / ci_analysis / analysis / cross_method_report, never invoked",
    "audit_response_quality.py": "inventory of scored-empty records; --check is expected to "
                                 "FAIL while the historical corpus retains them, so it is a "
                                 "standing report rather than a step in a procedure",
    "calibration_study.py": "one-off simulation answering STATS-BOOTSTRAP-CALIBRATION-001; its "
                            "output is RESULTS-2026-09-12-calibration.md, not a run step",
    "three_axis_score.py": "scorer and prereg constraint-checker for the three-axis instrument, "
                           "which is a DRAFT item set: --check is expected to fail until the "
                           "author has cut and balanced it. No skill can name it as a step "
                           "until the instrument exists, and gating the v2 release on a v3 "
                           "instrument's draft scorer is the wrong dependency",
    "references.py": "bibliography helper",
    "gen_readme.py": "named by barometer-wave step 4 via its --check form",
    "check_skill_docs.py": "this checker",
    "check_no_key_repro.py": "release-gate step, named by release_check.py item 10",
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
        "RETIRED 2026-09-17 and moved out of data/ with the bank it held. It was third-party "
        "instrument text, 62 licensed items, retrieved at the reader's end so this repository "
        "never republished them. Ignored in .gitignore and refused by a pre-commit hook; both "
        "must stay, because an ignored path is exactly where a stale copy sits unnoticed -- "
        "one was found untracked in the public mirror on 2026-09-17.",
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
    # ...AND ONLY WHERE SHIPPING IS THE POINT. This declaration means "must never leave the
    # public mirror". The private working study legitimately TRACKS the instrument text -- that
    # is what makes it the working study -- so firing there says nothing about republication and
    # only pressures someone into deleting a true declaration or forking this file. It forked
    # this file on 2026-09-12, which is how the distinction got noticed.
    #
    # The mirror is the tree whose runs live in data/; the private study keeps runs/ and uses
    # data/ for config. Same content-based test studypaths.runs_root() resolves by, kept local
    # so this checker does not acquire an import it otherwise has no use for.
    if os.path.isdir(os.path.join(ROOT, "runs")):
        return []
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


def results_doc_dead_paths():
    """Dead script references in RESULTS/VERIFICATION documents, not just skill documents.

    A module docstring or a results file can assert that a script exists, describe its flags
    and report what it produced, and nothing downstream will notice if it does not. That claim
    can close the highest-ranked open validation method in a reader's mind without anything
    having been run.

    check_skill_docs already refused dead paths in SKILL documents. Nothing checked results
    prose or module docstrings, which is where such a claim actually lives.

    See `check_false_denials` for the other direction, which is the harder one.
    """
    import glob as _glob
    import re as _re
    dead = []
    # Test files name fake scripts on purpose (scripts/x.py, scripts/absent.py) and a
    # CORRECTION naming the missing file is the fix, not the defect -- both are skipped.
    denials = ("never been committed", "not started", "does not exist", "no harness",
               "missing", "never committed")
    pats = ["RESULTS-*.md", "VERIFICATION-*.md", "scripts/*.py"]
    for pat in pats:
        for path in _glob.glob(os.path.join(ROOT, pat)):
            try:
                text = io.open(path, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            base = os.path.basename(path)
            if base.startswith("test_") or base == "_shim.py":
                continue
            # A CROSS-TREE DRIVER names scripts in BOTH trees, so from inside either
            # one about half its references cannot resolve. release_check.py is the
            # only such file: it scopes every entry to STUDY or MIRROR and runs the
            # checklist across the pair. Scanning it from the mirror reported
            # check_release_table.py as a script "never committed" -- it exists in
            # the working tree and passes there.
            #
            # Detected from the source rather than whitelisted by name, so a new
            # driver is covered and a file that stops being one loses the exemption.
            # The working tree still verifies these through _resolves_in_sibling_tree,
            # which is the side that can see both.
            if _is_cross_tree_driver(text):
                continue
            low = text.lower()
            for ref in set(_re.findall(r"scripts/[a-z0-9_]+\.py", text)):
                if os.path.exists(os.path.join(ROOT, ref)):
                    continue
                near = [ln.lower() for ln in text.split("\n") if ref in ln]
                ctx = " ".join(near) + " " + low[:4000]
                if any(d in ctx for d in denials):
                    continue
                # A reference that resolves in the OTHER tree is live, not dead.
                # `release_check.py` runs some checks against the working study and
                # some against the public mirror, so from inside the mirror it names
                # study-only tools like check_release_table.py. Flagging those told
                # the reader to "write the script, or correct the claim" about a
                # script that exists and runs.
                #
                # This VERIFIES rather than exempts: the reference must resolve
                # somewhere. A name that is dead in both trees still fails, so a tool
                # that is genuinely never committed cannot hide behind this.
                if _resolves_in_sibling_tree(ref):
                    continue
                dead.append((os.path.relpath(path, ROOT), ref))
    return sorted(set(dead))


def _is_cross_tree_driver(text):
    """Does this script dispatch checks into BOTH trees?

    Such a file names scripts that live in whichever tree each entry targets, so
    roughly half its references cannot resolve from inside either one. The marker
    is that it binds both roots AND scopes entries to them.

    TWO FORMS, because the second one broke this. The original driver held a literal
    list of `(label, STUDY, [...])` tuples, so counting `, STUDY,` identified it. On
    2026-09-16 that list became a derivation from `gates.py` -- the registry that
    declares each gate's tree -- and every one of those literals disappeared. The
    detector stopped recognising the file it was written for, which would have
    reported its study-scoped references as dead from the mirror.

    Keying a structural property to one spelling of it is the same defect as keying a
    claim to one phrasing; both fail the moment someone improves the code. So the
    registry form counts too: a file that binds both roots and dispatches through
    `gates` IS a cross-tree driver, whatever its entries look like.
    """
    import re as _re
    has_both_roots = bool(_re.search(r"^\s*STUDY\s*=", text, _re.M)) and \
        bool(_re.search(r"^\s*MIRROR\s*=", text, _re.M))
    scopes_entries = text.count(", STUDY,") + text.count(", MIRROR,") >= 2
    via_registry = bool(_re.search(r"^\s*import\s+gates\b", text, _re.M))
    return has_both_roots and (scopes_entries or via_registry)


def _resolves_in_sibling_tree(ref):
    """Does `ref` exist in the paired tree? False when there is no paired tree."""
    try:
        from _shim import public_scripts
        # `.parent` of the scripts dir IS the paired tree's root. Taking a dirname
        # of it went one level too high, to the workspace, where nothing resolves --
        # so this returned False for everything and the check silently did nothing.
        sibling = str(public_scripts(__file__).parent)
    except Exception:
        return False
    if not sibling or os.path.abspath(sibling) == os.path.abspath(ROOT):
        return False
    return os.path.exists(os.path.join(sibling, ref))



#: Assertions strong enough that, if the named path exists, the sentence is simply false.
#: Deliberately narrow. Soft words like "missing" or "absent" appear in honest prose about
#: missing DATA all the time and are not included.
DENIAL_PHRASES = (
    "never been committed", "never committed", "was never written", "never written",
    "does not exist", "doesn't exist", "no harness", "has no harness",
    "not started", "never begun", "no sheet exists", "was never built", "never built",
)

#: A document that QUOTES a withdrawn denial in order to correct it is the fix, not the
#: defect. These mark that framing on the same line.
QUOTE_MARKERS = (
    "used to say", "originally said", "originally claimed", "this file said",
    "withdrawn", "superseded", "corrected", "the claim was", "it said",
    "earlier version", "first version", "no longer",
)


def check_false_denials(root=None):
    """A denial that names a path which EXISTS. The inverse of the dead-path check.

    The dead-path check catches a document that credits work nobody did. This catches the
    opposite and rarer failure, which is worse because it reads as rigour: a document that
    DENIES work somebody did. A false denial is self-authenticating -- it looks like exactly
    the kind of unflattering admission a careful project makes -- so no reader challenges it,
    and it retires a finished control back into the backlog.

    The trigger is narrow on purpose: one of DENIAL_PHRASES within one line of a backticked
    or bare `scripts/*.py` reference that resolves on disk, with no QUOTE_MARKER on the line
    to show the denial is being quoted rather than asserted. Honest prose about missing data,
    unrun experiments and unacquired instruments uses softer words and does not trip it.
    """
    import glob as _glob
    import re as _re
    root = root or ROOT
    hits = []
    pats = ["RESULTS-*.md", "VERIFICATION-*.md", "STATUS.md", "RUBRIC-SCORES.md",
            "PAPER-*.md", "scripts/*.py", "results/RESULTS-*.md"]
    for pat in pats:
        for path in _glob.glob(os.path.join(root, pat)):
            base = os.path.basename(path)
            if base.startswith("test_"):
                continue
            try:
                lines = io.open(path, encoding="utf-8", errors="replace").read().split("\n")
            except OSError:
                continue
            for i, line in enumerate(lines):
                refs = set(_re.findall(r"scripts/[a-z0-9_]+\.py", line))
                refs = [r for r in refs if os.path.exists(os.path.join(root, r))]
                if not refs:
                    continue
                window = " ".join(lines[max(0, i - 1):i + 2]).lower()
                if any(q in window for q in QUOTE_MARKERS):
                    continue
                for d in DENIAL_PHRASES:
                    if d in window:
                        hits.append((os.path.relpath(path, root), refs[0], d))
                        break
    return sorted(set(hits))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--strict", action="store_true",
                    help="also fail when an entry point is named by no skill")
    ap.add_argument("--coverage", action="store_true", help="only the coverage report")
    args = ap.parse_args(argv)

    docs = skill_docs()
    if not args.coverage:
        lied = check_false_denials()
        if lied:
            print("FALSE DENIAL -- these sentences deny a path that exists:")
            for rel, ref, phrase in lied:
                print("    %s says %r about %s" % (rel, phrase, ref))
            print("A denial reads as rigour, so nobody checks it. Say what is true instead,")
            print("or mark the sentence as quoting a withdrawn claim.")
            return 1
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
        # FATAL, NOT ADVISORY, SINCE 2026-09-15.
        #
        # This printed the list and returned 0 unless --strict was passed, and
        # nothing passes --strict: not CI, not the prep skill, not release_check.
        # So the check ran everywhere, found undocumented scripts, said so, and
        # reported success -- which is the vacuous pass this repository has now
        # found in six separate tools, in its own coverage checker.
        #
        # It surfaced when probe_budget.py and run_i3_wave.py were added: both
        # were listed as named by no skill, and the gate exited 0 over them. An
        # undocumented entry point is exactly what this file exists to catch, and
        # a collector nobody can find the runbook for is how a wave gets launched
        # on a budget nobody measured.
        #
        # --strict is kept as a no-op alias so existing invocations do not break.
        return 1
    else:
        print("every entry point is either named by a skill or declared a non-procedure.")

    # A results document or module docstring naming a script that does not exist is the same
    # defect class, in the place readers actually look. It is fatal regardless of --strict:
    # a claim that a harness exists closes an open question in the reader's mind.
    ghosts = results_doc_dead_paths()
    if ghosts:
        print("")
        print("%d dead script reference(s) in results prose or docstrings:" % len(ghosts))
        for where, ref in ghosts:
            print("   %-40s names %s" % (where, ref))
        print("Write the script, or correct the claim. Do not leave prose asserting a tool")
        print("that was never committed.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
