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
    # THE GATE MUST CHECK THE RUN THE PAPER IS WRITTEN FROM. It checked
    # `2026-09-13-g0dm0d3-replicate` -- a rung-2 run this paper does not cite -- so the release
    # gate would have passed green while the paper's own corpus carried NOT FIT TO SCORE. An
    # acceptance gate pointed at the wrong artifact is the vacuous pass with a run directory
    # attached: it examines something real and answers a question nobody asked.
    Gate("collection_check.py", ["2026-09-16-ratchet-v3-wave"], tree="either",
         stage="release", label="3  cited runs are fit to score",
         covers="the acceptance gate over the wave every published figure in this paper "
                "is computed from"),
    Gate("run_inventory.py", ["--check"], tree="either", stage="release",
         label="3  every run directory accounted for",
         covers="no run directory is unlisted or orphaned"),
    Gate("pipeline_transform_audit.py", tree="either", stage="release",
         label="3  the treatment was actually applied",
         covers="whether the intervention an arm is named after actually ran -- "
                "B-Parseltongue passed every other check with 0 of 240 applied"),
    Gate("check_comparison.py", ["--satisfiable", "--n-a", "5", "--n-b", "5",
                                 "--family", "10"], tree="either", stage="manual",
         label="6b a criterion this design cannot meet",
         covers="whether a stated decision rule is reachable at the n in use. A permutation "
                "test over C(na+nb, na) relabellings cannot return a p below 2/C(...), so a "
                "BH threshold under that floor is unsatisfiable BY ANY EFFECT OF ANY SIZE -- "
                "and the null result it produces is a fact about the design, not the models. "
                "Three instances in this study: prediction 2 of the phase-4 prereg, the "
                "clause-factorial floor, and rung 2's within-rung family (5v5, minimum p "
                "0.0079, threshold 0.005). The same tool checks two arms for confounds with "
                "--cells, which would have caught rung 2 differing from its control by "
                "protocol AND token budget before 120 sheets were bought.",
         why="it takes the parameters of a comparison rather than reading the tree, so there "
             "is no single invocation that covers every arm. Run it when a new arm is "
             "designed and when a decision rule is written -- those are the two moments its "
             "answer can change anything. The registered invocation is the rung-2 case, kept "
             "as a regression: it must keep reporting UNSATISFIABLE"),
    Gate("multiple_comparisons.py", ["--check"], tree="either", stage="release",
         label="6  the stated family size matches the data",
         covers="how many hypothesis tests this study runs, and which are corrected. The "
                "paper claimed 'a Benjamini-Hochberg correction over the whole family of 153 "
                "contrasts' while the live count was 246 -- hand-typed, in four places, "
                "gated by nothing, and stale in the direction that understates the "
                "correction burden. It also enumerates the exploratory families the paper "
                "never counted at all, which is the `multiple_comparisons` column the "
                "controls audit scores twelve other studies on. It distinguishes a LIVE "
                "claim from a HISTORICAL record and refuses to flag the latter: three of its "
                "first four hits were a corrections document, a blockquote being refuted, "
                "and a paragraph beginning 'Until 2026-09-17'."),
    # ---- ARRIVED IN THE 2026-09-20 MERGE, and test_gate_registry caught that neither was
    # registered anywhere. Both carry --check, and the other session's own release checklist
    # named derive_manifest as "check 3b" -- so the gate existed in a hand-typed list and not
    # in the registry the list was replaced by. That is the cost of two sessions holding two
    # copies of the same inventory, which is why the literal list is gone.
    Gate("derive_manifest.py", ["--check"], tree="study", stage="release",
         label="3b frozen manifests still match their records",
         covers="38 run directories holding ~8,674 records were collected by tools that never "
                "wrote a manifest, so validate_runs can only call them NOT VALIDATED. This "
                "does not forge one -- a record derived from the data agrees with the data by "
                "construction and would be a red gate turned green while verifying nothing "
                "(LEARNINGS #53). What it buys is a CONTENT FREEZE: --check re-derives each "
                "manifest.derived.json and fails if the directory has changed under it."),
    Gate("check_empty_records.py", ["--check"], tree="either", stage="release",
         label="3d every zero-byte record file is declared",
         covers="an empty .jsonl and an arm that was never collected are indistinguishable to "
                "every reader, human or scripted. On 2026-09-20 that ambiguity cost an "
                "independent reviewer an investigation and produced a written accusation that "
                "a live evilrobots.lol claim was fabricated: fourteen gemma-2-9b stubs left "
                "by a failed SVD attempt, while the real 40 records sat in a sibling "
                "directory. The page was correct. Running it also surfaced eight empties "
                "nobody had noticed in the LIVE wave -- six glm-5.2 cells from a stale "
                "provider pin, and two conditions on a local abliterated build that are still "
                "undiagnosed.",
         why=None),
    Gate("gen_data_dictionary.py", ["--check"], tree="either", stage="release",
         label="9  the data dictionary describes the corpus that exists",
         covers="~19,600 published records across two schemas and 45 fields. Presence, "
                "coverage, type and categorical vocabulary are derived on every run; only "
                "meanings are hand-written, and a field appearing in the data with no entry "
                "is a hard failure rather than a blank. A dataset whose fields are "
                "undocumented is not shared, it is uploaded."),

    # ARRIVED IN THE 2026-09-20 MERGE AND WERE IN NO STAGE. Both carry `--check` and neither
    # was registered, which `tests/test_gate_registry.py` caught the moment the two sessions'
    # trees met: the other session added the tools, this one's gates.py won the merge without
    # a conflict, and a conflict is the only thing that would have made the omission visible.
    # This is the 2026-09-18 finding again -- four tools built in a day, sitting in the tree
    # looking like safeguards, none of which would have run at release.
    Gate("dose_figure.py", ["--check"], tree="study", stage="release",
         label="4e the dose figure still matches the arms it draws",
         covers="the SVG against the judged records behind it. The figure's job changed when "
                "the pre-registered judge found no arm differs from stock: it now shows the "
                "ABSENCE of a dose response across a measured 2.45x range of weight change, "
                "which is a claim a stale chart would silently reverse."),
    Gate("gen_artifact_manifest.py", ["--check"], tree="either", stage="manual",
         label="3e the out-of-band weights are checkable",
         covers="per-file SHA-256 and a directory digest for the ~100 GB of base and "
                "abliterated weights the weight rung rests on. The bytes travel as a torrent "
                "beside the release because 17 GB of them reached a branch's history on "
                "2026-09-20; what ships here is what makes a download verifiable, and a "
                "result nobody can recompute is not a result.",
         why="IT CANNOT RUN ON THE MACHINE THAT RELEASES. The weights live on the box that "
             "built them; this one holds 0.07 GB of leftovers, and the tool correctly REFUSES "
             "to write a manifest describing the wrong directory. Registered at release for "
             "half an hour on 2026-09-20 and it failed every run, which is how a gate gets "
             "switched off wholesale -- so it is manual, and the release checklist's human "
             "half is where 'run it on the machine holding the weights' belongs. A gate that "
             "can never go green where it is registered protects nothing."),

    # PLAN step 7 -- the four body findings that had no command behind them. Two of the four
    # had a script but no registration, and two had no script at all; all four are in the
    # paper. A figure a reader cannot re-derive is this project's own rule being broken in its
    # own paper, which is the rule it scores twelve other studies on.
    Gate("strong_shift.py", ["--selftest"], tree="either", stage="release",
         label="4c the scale-usage estimator still behaves",
         covers="direction, tie handling and a split panel, on synthetic input. It validates "
                "the ESTIMATOR, not the figure: the endpoint-vacating result moves with the "
                "corpus and is gated as prose by key_numbers. Read LEARNINGS #51 before "
                "reporting a selftest as a calibration -- this one samples input it "
                "generates, which is why it is registered as a smoke test and described as "
                "one.",
         why=None),
    Gate("jurisdiction_gradient.py", ["--selftest"], tree="either", stage="release",
         label="4d the subject-gradient estimator still behaves",
         covers="direction, ties and a deterministic modal rule. Same scope as above: the "
                "unconditional (p=0.0004) and conditional (p=0.63) forms are reported "
                "separately and counted in the exploratory family, and this gate covers the "
                "machinery rather than either number.",
         why=None),
    Gate("intensity_by_claim.py", ["--check"], tree="either", stage="release",
         label="3b the top-box comparison still has a panel",
         covers="whether enough models carry both claim classes for §3b's sign test to mean "
                "anything. Measured 2026-09-20: 56 models, strongest answer used more on "
                "contested normative claims by 35 and on documented ones by 14, p = 0.0038 -- "
                "the panel commits hardest where it has least to go on. The script also "
                "asserts the claim_type/ratchet alignment and emits the confound INTO the "
                "generated table, so the caveat cannot be edited away without touching the "
                "figures it governs.",
         why=None),
    Gate("agreement_by_training.py", ["--check"], tree="either", stage="release",
         label="3b the shared-RLHF objection is still answerable",
         covers="whether the abliterated class -- builds with the refusal direction projected "
                "out of their weights -- is still large enough to carry §3b's argument. It is "
                "the ONLY class in the panel that removes safety tuning rather than varying "
                "jurisdiction or vintage, so if it thins below three models the section's "
                "answer to 'isn't this just shared RLHF' is gone and the other rows cannot "
                "replace it. Measured 2026-09-20: 5 models, agreeing with every normative "
                "proposition in the bank.",
         why=None),
    Gate("item_gradient.py", ["--check"], tree="either", stage="release",
         label="4  the item gradient has no holes",
         covers="every item of the bank observed at baseline, above an observation floor, "
                "with both frames present. The gradient decides which pairs are the "
                "instrument's most informative and which are saturated, and §4's reversal -- "
                "pairs 1 and 15 are its top end, not its defects -- rests on the ranking. A "
                "gradient missing an item is a ranking with a silent hole in it.",
         why=None),
    Gate("pair_consistency.py", ["--check"], tree="either", stage="release",
         label="4b agree-both is contestedness, not acquiescence",
         covers="whether agreeing with BOTH halves of a mirrored pair exceeds what "
                "independent answers arithmetically produce, as a fraction of the reachable "
                "range. An excess is yes-saying and WOULD be an instrument defect. Measured "
                "2026-09-19: **only 2 of 16 pairs can be judged at all** -- critic agreement "
                "runs 92-100%, so agreeing with both halves is pinned to agreeing with the "
                "defender half and the widest reachable range on any pair is 1.85 points. Of "
                "the two, neither is near the bar and pair 1 sits far BELOW independence, a "
                "genuine forced choice. The gate returns NOT APPLICABLE rather than OK if "
                "that falls to zero, because 'no pair over the bar' on unmeasurable pairs is "
                "a check examining nothing.",
         why=None),
    Gate("calibrate_estimators.py", ["--check", "--draws", "200"], tree="either",
         stage="manual",
         label="6c each estimator's false-positive rate AT THE n IT IS USED AT",
         covers="the measured error rate of the sheet bootstrap and the exact permutation "
                "test, against a null built BY SPLITTING REAL CELLS IN HALF -- no treatment "
                "exists, so every rejection is a false positive, and the halves carry the "
                "corpus's own pathologies including the cells whose sheets barely differ. "
                "Measured 2026-09-19 over 200 splits of 136 eligible cells: sheet bootstrap "
                "10.5%, exact permutation 4.5%. That is why the paper reports the exact "
                "test. The bootstrap's own docstring claimed 6.2% and its --selftest says "
                "12.5% on synthetic nulls IT GENERATES, which is a detector validated "
                "against input it chose.",
         why="it is MANUAL and not release for two reasons, and the second is the important "
             "one. It takes minutes, and -- decisively -- it currently EXITS 1 and always "
             "will: 10.5% is a property of this corpus and this estimator, and no change to "
             "the paper moves it. The remedy is to report the exact test, which is a "
             "sentence, not a fix. Wiring a permanently-red gate into release is how a check "
             "with no exit gets routed around by deleting it. Run it when an arm is "
             "collected at a new depth -- the rate is measured over the cell sizes this "
             "corpus HAS and does not transfer"),
    Gate("g0dm0d3_constants.py", ["--check"], tree="study", stage="manual",
         label="3c the elicitation rung's constants match their source",
         covers="the GODMODE system prompt and DEPTH_DIRECTIVE are PARSED from the G0DM0D3 "
                "checkout rather than copied, and the three sampling offsets -- the only "
                "values that ARE retyped -- still match `applyGodmodeBoost`.",
         why="it reads a third-party checkout that CI deliberately does not clone, so on the "
             "release runner it could only report a missing file. Run it before collecting "
             "rung 2 and whenever that checkout is updated: a prompt that drifts upstream "
             "changes the treatment while every sheet still looks valid"),
    Gate("parseltongue_triggers.py", ["--check"], tree="study", stage="manual",
         label="3b the obfuscation arm's premise is re-measured",
         covers="whether the Parseltongue trigger list -- READ FROM THE SERVER'S SOURCE, "
                "never retyped -- intersects the live instrument at all. It exits 1 when the "
                "list cannot be read, NOT when it finds zero: zero is a finding. `manual` "
                "because it needs the G0DM0D3 checkout, which CI does not have.",
         why="it reads the trigger list out of a third-party checkout that CI deliberately "
             "does not clone, so on the release runner it could only ever report a missing "
             "file. Run it when the instrument changes or when the arm is next proposed -- "
             "those are the only two moments its answer can move. It is registered rather "
             "than left as a loose script because the arm was written off as dead on a "
             "measurement taken against a DIFFERENT instrument, and a verdict nobody re-runs "
             "is a verdict that outlives its evidence"),
    Gate("position_analysis.py", ["--selftest"], tree="either", stage="release",
         label="6  the position estimator is validated",
         covers="position, consistency and acquiescence against synthetic input whose true "
                "answer is known -- a consistent skeptic scores +1.5, a pure yea-sayer scores "
                "0 with acquiescence +1. The estimator was written before the data so it "
                "cannot be shaped by it, and its selftest passed for a week while its "
                "real-data path was a stub that printed 'Phase 4 has not been collected yet' "
                "over 580 valid sheets. The selftest is necessary and it was not sufficient; "
                "tests/test_position_analysis_reads_the_corpus.py is the other half"),
    # ---- added 2026-09-18. Four tools were built that day, none was registered, and an
    # unregistered gate is a gate that does not run. The estimator defect they exist to
    # prevent was found by a check that had never been written down anywhere.
    Gate("null_audit.py", tree="study", stage="release",
         label="6  every null carries a minimum detectable effect",
         covers="the effect each null this study REPORTS could have detected, by simulation "
                "through the same test the paper ran. This study scores twelve other papers "
                "on that exact column and reported three nulls without it -- the jurisdiction "
                "crossover as 'no interaction' when its MDE bounds the effect at +/-0.50, and "
                "prediction 3 as 39-of-39 when it rules out only a COMMON opposite direction "
                "at 3.9%. A null with no MDE is a sample size, not a finding"),
    Gate("item_omission.py", ["--selftest"], tree="either", stage="release",
         label="6  item, slot and numeral can be told apart",
         covers="the discriminator against synthetic input with a KNOWN cause -- a pure slot "
                "effect, a pure item effect, single-order data that must return NOT "
                "SEPARABLE, and the proof that a concentration p-value fires on both causes "
                "and therefore decides nothing. Three declared item-omission patterns were "
                "slot patterns at one presentation order, and a permutation test called every "
                "one of them p < 0.001"),
    Gate("check_citation.py", ["--path", "../../../bias-study-release/CITATION.cff"],
         tree="study", stage="release",
         label="10 the citation record is fit to mint a PERMANENT DOI",
         covers="CITATION.cff in the tree that SHIPS, checked from the tree that is "
                "developed -- because the private tree has none and a reader there would "
                "conclude none exists. Found unguarded 2026-09-18: the mirror's file carried "
                "the withdrawn title 'The Hedge Is the Bias' and an abstract quoting 2,866 "
                "runs, 166 models and 62 propositions, every figure from the retired "
                "instrument. A Release fires the Zenodo webhook and the DOI carries that text "
                "forever, so a stale sentence here is not a correction, it is a permanent "
                "citation to a study that does not exist"),
    Gate("check_sheet_attribution.py", tree="either", stage="manual",
         label="3  attribution, before a NEW PROTOCOL is collected",
         covers="the same check as the release copy. The protocol-v1 corpus contains 68 "
                "sheets whose answers cannot be mapped to propositions under either reading, "
                "and that number is fixed: those sheets exist, and collecting more does not "
                "unmake them.",
         why="IT WAS AT `prerun` FOR EIGHT HOURS ON 2026-09-19/20 AND BLOCKED ALL COLLECTION. "
             "Registered there so attribution was checked in front of spend, which sounds "
             "right and is not: the check reports a property of the corpus ALREADY ON DISK, "
             "so it is permanently red and refuses every future run regardless of what that "
             "run would collect. It killed the glm-5.3-flash retry overnight for a reason "
             "that had nothing to do with glm-5.3-flash. A prerun gate has to be answerable "
             "by the person about to spend; this one is not. Run it when the PROTOCOL "
             "changes -- v2 renumbering dissolves the ambiguity, so a v2 arm cannot add to "
             "the 68 and a v1 arm can."),
    Gate("check_sheet_attribution.py", tree="either", stage="release",
         label="3  every scored answer belongs to a known proposition",
         covers="sheets returned in ascending id order, which is ambiguous under protocol v1: "
                "the model may have re-sorted a shuffled sheet and answered by item id, or "
                "ignored the printed numbers and answered down the page. Mirror-pair "
                "consistency under both mappings tells them apart. Measured 2026-09-18: 61 "
                "UNATTRIBUTABLE -- near chance under both, so which proposition each answer "
                "belongs to is not recoverable -- and 4 ANSWERED BY SLOT and therefore scored "
                "against the wrong propositions, including one frontier model at 0.62 by id "
                "against 0.88 by slot. Protocol v2 renumbering dissolves the ambiguity: the "
                "printed number IS the slot, so the two mappings coincide"),
    Gate("gen_deviations.py", ["--check"], tree="study", stage="release",
         label="7  the deviation record matches its sources",
         covers="PROTOCOL-DEVIATIONS.md against data/wave-panel.json, "
                "data/collection-limitations.json and the PREREG headers -- every "
                "pre-registration, every roster amendment with the rule that selected it, "
                "every rejected listing with its reason. This study scores others on whether "
                "a reader can tell what was planned from what was done"),
    Gate("gen_vintage.py", ["--check"], tree="study", stage="release",
         label="7  every model in runs/ has a recorded release date",
         covers="data/model-vintage.json against the models actually in the corpus. A study "
                "about how a measured position MOVES has to be able to cut its figures by "
                "model generation, and until 2026-09-18 it could not: vintage, quantisation "
                "and serving path moved together, which is why T9 is recorded as orphaned. "
                "A model with no date silently drops out of every generation contrast"),
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
         label="2  RELEASE-2026-09-07 arm inventory matches runs/",
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
    Gate("faction_lean.py", ["--selftest"], tree="study", stage="prerun",
         label="the factions estimator is calibrated",
         covers="the two-way centring algebra, the design's detection floor, recovery of a "
                "planted interaction, and the rejection rate on NULL panels -- all on "
                "synthetic input, because the bank does not exist yet",
         why="it is a precondition of collecting factions sheets, and it has already paid for "
             "itself: the calibration showed the pre-registered P2 criterion was "
             "unsatisfiable at ANY effect size (min p = S^(1-T) = 1/64 at four stems, and "
             "BH-FDR over 36 models needs twelve models there before it rejects one). A wave "
             "would have returned P2 FAIL and read as 'no model leans by sector'"),
    Gate("check_mcp_coverage.py", tree="study", stage="prerun",
         label="the dataset can supply what the design asks",
         covers="per play: records, sourced records, and whether the live factions sectors "
                "meet their own exemplar floor; records reachable by no play at all; and the "
                "fields a design assumed and the dataset does not carry",
         why="a design that assumes its inputs is the vacuous-pass failure in a new place. "
             "The factions design specified 'at least three people.jsonl ids for its play' "
             "and nothing checked that was satisfiable: 346 of 550 records carry no play, "
             "and the absent jurisdiction field was found two hours after a jurisdiction "
             "slot was recommended"),
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


#: A gate that ran out of wall clock. NOT 1 -- a defect is a gate that answered "broken", and
#: this is a gate that did not answer at all. The two were the same code until 2026-09-18,
#: when `check_outcomes_computable` exceeded the 900s budget and the collection runner read
#: "FAIL ... did not run" and refused two stages that had nothing wrong with them. It still
#: BLOCKS -- failing open on an unanswered question is the worse error -- but it says which
#: kind of not-passing it is, because the remedy is completely different: a defect is fixed in
#: the gate, a timeout is fixed in the budget or the cost.
TIMEOUT = 3


def execute(gate, timeout=900):
    """Run one gate. Returns (rc, first_line_of_output).

    rc 0 pass, 1 defect, 2 NOT APPLICABLE, 3 TIMED OUT -- the project's convention, honoured
    here so a gate that cannot apply in this tree is never counted as a pass, and a gate that
    never finished is never reported as one that found something.
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
    except subprocess.TimeoutExpired:
        return TIMEOUT, ("NO ANSWER: still running after %ds. This gate found nothing wrong -- "
                         "it did not finish. Re-run it alone (`python scripts/gates.py --only "
                         "%s`) or raise --timeout." % (timeout, gate.script))
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
    failed, passed, na, timed_out = [], 0, 0, []
    rows = for_stage(stage)
    if not rows:
        # A PREFLIGHT OVER NOTHING MUST NOT READ AS CLEAN. Same rule as every other gate here.
        raise AssertionError("no gates registered at stage %r -- preflight checked nothing"
                             % stage)
    echo("PREFLIGHT -- %d gate(s) at stage %s, in the %s tree"
         % (len(rows), stage, "MIRROR" if THIS_IS_MIRROR else "private study"))
    for g in rows:
        rc, line = execute(g, timeout=timeout)
        mark = {0: "pass", 2: "n/a ", TIMEOUT: "TIME"}.get(rc, "FAIL")
        echo("  %s  %-44s %s" % (mark, g.label[:44], line[:88]))
        if rc == 0:
            passed += 1
        elif rc == 2:
            na += 1
        elif rc == TIMEOUT:
            timed_out.append((g, rc, line))
        else:
            failed.append((g, rc, line))
    echo("  %d passed, %d not applicable, %d FAILED, %d TIMED OUT"
         % (passed, na, len(failed), len(timed_out)))
    if timed_out:
        # Counted with the failures because an unanswered gate must block -- but named
        # separately, so nobody spends an evening debugging a check that was merely slow.
        echo("  NOTE: %d gate(s) did not finish and found NOTHING. They are blocking because "
             "they gave no answer, not because they gave a bad one." % len(timed_out))
    return failed + timed_out


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
