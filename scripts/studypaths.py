#!/usr/bin/env python3
"""Shared run-directory resolution and deterministic RNG streams.

TWO PROBLEMS THIS EXISTS TO FIX.

**The directory.** The repo ships `data/`. Four scripts hardcoded `runs/`, printed
`[skip] <run>: no scored/` and exited **0** — so a finished study produced no
confidence intervals and no FDR correction, with no error anywhere, silently voiding
the study's own rule that a delta is reportable only when its CI excludes zero.
Commit `4087bb7` fixed `score.py` and `cross_method_report.py` and missed the rest.
Three ad-hoc resolutions existed (`generate_charts.py`, `sweep_status.py`, and the
hardcodes); this is the one they all call now.

A missing run is an **operator error**, not a no-op. `resolve_run()` raises, and the
callers exit non-zero. A pipeline that returns 0 having computed nothing is how three
days of failures went unremarked.

**The RNG.** `random.seed(20260527)` at import seeded ONE global stream, and
`bootstrap_ci` drew from it sequentially — so the draws a given (run, model) cell
received depended on how many cells were processed before it. Measured: passing the
five main run-dates in reverse order moved **6 of 46 published CI cells**. No verdict
flipped at those values, but the study's gate is binary, so a bound sitting a few
hundredths from zero was decidable by argument order. `stream()` derives an
independent generator per cell from the declared seed, so a cell depends only on its
own data.

The seed itself comes from the run's `manifest.json` (`analysis_seed`) when present,
and falls back to May's `20260527` so the published table stays reproducible. A seed
chosen after seeing the intervals is a researcher degree of freedom; `run_study.py`
writes it at run start, before any response exists.
"""
from __future__ import annotations

import hashlib
import json
import re
import os
import sys
import random
from pathlib import Path

# GitLab owns development; the same exported code accepts a release corpus explicitly.
_requested = os.environ.get("STUDY_ROOT")
if _requested is not None and not _requested.strip():
    raise ValueError("STUDY_ROOT must name a study directory")
STUDY_DIR = (Path(_requested).expanduser().resolve() if _requested is not None
             else Path(__file__).resolve().parent.parent)
if not STUDY_DIR.is_dir():
    raise ValueError(f"STUDY_ROOT is not a directory: {STUDY_DIR}")

# Compatibility contract for historical shims; expand only with entry-point tests.
ROOT_AWARE_SCRIPTS = frozenset({"ci_analysis.py", "robustness_checks.py",
                               "paired_analysis.py", "validate_runs.py",
                               # Added 2026-09-12. Both resolved their corpus with a hardcoded
                               # ("data", "runs") under their own parent directory, which is a
                               # third implementation of run resolution and ignores STUDY_ROOT.
                               # They now call run_roots(). A shim may forward to them safely;
                               # it could not before, and _shim was right to refuse.
                               "judge_lean.py"})

#: May 2026's seed. Frozen. Used when a run's manifest declares none.
LEGACY_SEED = 20260527


class RunNotFound(Exception):
    """A run directory, or its scored/ subdirectory, is not where it should be."""


#: A run directory is DATED. `2026-05-25`, `2026-09-05-recollect`, `2026-08-31-lineage`.
#: Nothing else in either layout is.
_RUN_DIR = re.compile(r"^\d{4}-\d{2}-\d{2}")


def _looks_like_runs_root(p: Path) -> bool:
    """True when a directory actually CONTAINS runs, not merely when it is named for them.

    THE NAME OF THE CHILD MATTERS, and leaving it out cost a silent misdirection on
    2026-09-05. The third test used to be "this child holds any *.jsonl", which is true of any
    data directory that happens to contain one -- and the private study's `data/` acquired
    `external/rottger2024-codes.jsonl` that morning. From then on `runs_root()` returned
    `data/` instead of `runs/`, so every shared script looked for runs in the config directory
    and reported the run missing. The docstring below already warned about exactly this failure
    for the NAME-based rule; the content-based rule inherited it through a laxer door.

    A run directory is dated in both layouts, so requiring that of the child costs nothing and
    closes it. The structural markers (`raw/`, `scored/`, `manifest.json`) still qualify a
    child on their own, because those are unambiguous whatever it is called.
    """
    if not p.is_dir():
        return False
    for child in p.iterdir():
        if not child.is_dir():
            continue
        if (child / "scored").is_dir() or (child / "raw").is_dir() \
                or (child / "manifest.json").exists():
            return True
        if _RUN_DIR.match(child.name) and any(child.glob("*.jsonl")):
            return True
    return False


def runs_root() -> Path:
    """The directory holding run directories: `runs/` here, `data/` in the public mirror.

    RESOLVED BY CONTENT, NOT BY NAME. Name-based resolution worked only because the mirror's
    `data/` happens to hold runs -- point `STUDY_ROOT` at this private study, whose `data/`
    holds config JSON and whose runs live in `runs/`, and a name-based rule silently returns
    the config directory. The failure mode is an analysis that finds no runs and reports
    success having computed nothing.

    AN AMBIGUOUS SELECTION FAILS rather than guessing, per the September 8 direction: a held
    layout containing BOTH a populated `data/` and a populated `runs/` cannot be resolved by
    inspection, so `STUDY_RUN_LAYOUT` must say which. Picking one silently is how an analysis
    ends up reading the wrong corpus and never says so.
    """
    layout = os.environ.get('STUDY_RUN_LAYOUT')
    if layout is not None:
        if layout not in ('data', 'runs') or not (STUDY_DIR / layout).is_dir():
            raise RunNotFound('STUDY_RUN_LAYOUT must select an existing data or runs directory')
        return STUDY_DIR / layout
    candidates = [STUDY_DIR / name for name in ("data", "runs")
                  if (STUDY_DIR / name).is_dir()]
    if len(candidates) == 1:
        return candidates[0]
    populated = [p for p in candidates if _looks_like_runs_root(p)]
    if len(populated) == 1:
        return populated[0]
    if candidates:
        # AMBIGUOUS, AND SAID SO EVERY TIME -- but not fatal here. The public mirror really
        # does hold two populated corpora, and several scripts call this at MODULE level, so
        # raising took `--help` down with it and made the tree unusable rather than careful.
        # The strictness lives where it can act: resolve_run() fails hard when a RUN NAME is
        # present in both roots, which is the case where picking would actually read the wrong
        # records. This returns a root and never does it quietly.
        chosen = (populated or candidates)[0]
        print("[studypaths] WARNING: both data/ and runs/ under %s hold runs; using %s/. "
              "Set STUDY_RUN_LAYOUT=data|runs to choose deliberately."
              % (STUDY_DIR, chosen.name), file=sys.stderr)
        return chosen
    raise RunNotFound(f"neither data/ nor runs/ exists under {STUDY_DIR}")


def run_roots() -> list[Path]:
    """Every populated corpus root, in preference order -- usually one, legitimately two.

    The public mirror really does hold two: 22 May runs under `data/` and 30 August/September
    runs under `runs/`. Neither is wrong and neither is stale, so a rule that picks ONE root
    globally has to be wrong about half the runs. Resolution is therefore per run NAME.
    """
    layout = os.environ.get('STUDY_RUN_LAYOUT')
    if layout is not None:
        if layout not in ('data', 'runs') or not (STUDY_DIR / layout).is_dir():
            raise RunNotFound('STUDY_RUN_LAYOUT must select an existing data or runs directory')
        return [STUDY_DIR / layout]
    roots = [STUDY_DIR / name for name in ("data", "runs") if (STUDY_DIR / name).is_dir()]
    populated = [p for p in roots if _looks_like_runs_root(p)]
    return populated or roots


#: A run that has been REPAIRED, and the repaired corpus that supersedes it.
#:
#: The May 2026 corpus was collected at an 800-token cap that severed or emptied
#: about a third of it, differentially by model: three models had ZERO usable A/B
#: pairs and GPT-5 had none in any run. Each entry here names a derived corpus
#: built by `splice_corpus.py` -- the original records where they are usable, and
#: a re-collection at 4,000 tokens where they are not.
#:
#: THE REPAIRED CORPUS IS THE STUDY. The originals are kept because the
#: corrections ledger cites them and because deleting evidence is not how this
#: project handles being wrong, but no analysis should default to reading a
#: corpus a third of which is missing.
REPAIRS = {
    "2026-05-25-full": "2026-09-14-full-spliced",
    "2026-05-26-cn-expansion": "2026-09-14-cn-expansion-spliced",
    "2026-05-26-timeseries": "2026-09-14-timeseries-spliced",
    "2026-05-26-augmentation": "2026-09-14-augmentation-spliced",
    "2026-05-26-unmask-gradient": "2026-09-14-unmask-gradient-spliced",
    "2026-05-26-variance": "2026-09-14-variance-spliced",
    # The EARLIER main run, one character away from "2026-05-25-full" above and a
    # different collection. Keyed from the repair's own `recollected_from` rather
    # than from its directory name, which says "may25" and would have pointed the
    # splice at -full.
    "2026-05-25": "2026-09-14-may25-spliced",
    "2026-05-27-ood": "2026-09-14-ood-spliced",
    "2026-05-27-paraphrase": "2026-09-15-paraphrase-spliced",
    "2026-05-27-reversed-premise": "2026-09-15-reversed-premise-spliced",
}

#: Holes no budget fixes, kept as a named record rather than quietly carried.
#: A corpus that cannot say what is still missing from it is not repaired, it is
#: only larger.
UNREPAIRABLE = {
    # THE MODEL IS GONE. Probed directly 2026-09-14: both return
    #   HTTP 404 {"error":{"message":"No endpoints found for <model>."}}
    # They have been withdrawn from the provider. This is a limit of a
    # LONGITUDINAL instrument, not of this repair: a study that measures how model
    # framing drifts across versions cannot re-measure a version that no longer
    # exists, and the window in which a result stays reproducible is set by the
    # vendor, not by us. Worth stating in the write-up rather than filing as a
    # footnote.
    ("2026-05-26-cn-expansion", "baidu/ernie-4.5-300b-a47b"):
        "19 cells truncate at 740-772 tokens, below the cap. Re-collection on "
        "2026-09-14 failed on all 19: HTTP 404, no endpoints found. The model has "
        "been withdrawn from the provider; the cells stay excluded permanently.",
    ("2026-05-26-timeseries", "google/gemini-2.0-flash-001"):
        "33 cells. Re-collection failed on all 33: HTTP 404, no endpoints found. "
        "Withdrawn from the provider, same as ernie above.",
    ("2026-05-26-augmentation", "google/gemma-2-9b-it"):
        "All 60 cells failed AT COLLECTION TIME in May -- they never produced a "
        "response at all, so this is not budget exhaustion and the repair tool "
        "correctly did not target it. Probed 2026-09-14: HTTP 404, no endpoints "
        "found. Withdrawn. NOTE its second role: gemma-2-9b-it is the base of the "
        "ABLIERATED JUDGE the cross-method robustness leg rests on, so that "
        "check cannot be re-run either -- see RESULTS/THE-WASH.",
    ("2026-05-26-cn-expansion", "bytedance/seed-1.6"):
        "1 call failed outright at collection time. No budget fixes a failed call.",
    ("2026-05-27-reversed-premise", "mistralai/mistral-large"):
        "6 cells, all FAILED CALLS at collection time -- no tokens_out, no "
        "response, no recorded cap. The re-collector correctly did not target "
        "them and the splice correctly left them unusable, which is why the arm "
        "lands at 194 of 200 rather than 200. Checked because the gap looked at "
        "first like the repair tool seeing less damage than exists, which is the "
        "defect that cost this project four months; it is not that. Every one of "
        "the 33 mistral cells that WAS truncated repaired.",
    ("2026-05-25-full", "phi4:latest"):
        "1 cell. phi4 is a LOCAL model and the re-collector calls OpenRouter, so "
        "it was never reachable by that path.",
    # RESOLVED 2026-09-15 -- entry kept as the record of a wrong call, not as a
    # live exclusion. It read:
    #
    #     ("2026-05-25-full", "google/gemma-3-27b-it"): "1 cell, and a probable
    #     FALSE POSITIVE: 1,938 tokens of 4,000, so the model stopped
    #     voluntarily, ending on a markdown URL with no full stop. Checked
    #     corpus-wide before leaving the detector alone -- one record in 2,101
    #     ends in a URL and that one genuinely hit the cap."
    #
    # The diagnosis was right and the remedy was wrong. Re-counted over the whole
    # corpus rather than one run -- 30,089 records, every non-derived run -- NINE
    # end on a closed markdown link while flagged severed, across five cells, two
    # models and three runs, and NONE is within 95% of its cap. The "one record
    # in 2,101 that genuinely hit the cap" was an artifact of counting inside a
    # single run.
    #
    # Two of the nine are `gpt-4.1` in `2026-09-13-i3-phase0` -- the LIVE
    # forced-choice instrument -- so registering the cell did not contain the
    # problem, it hid it: a per-cell entry cannot catch the next record, and the
    # next records were already on disk. `eligibility.looks_truncated_text` now
    # treats a closed markdown link as an ending, which resolves this cell, its
    # twin in `2026-05-25`, and the two live ones.
    #
    # The general rule, which cost two entries to learn: a false positive that
    # recurs is a DETECTOR defect, and belongs in the detector. This registry is
    # for cells nothing can fix -- a withdrawn model, a wrong channel, a call
    # that failed at collection time.
}

#: ARMS WHOSE TREATMENT WAS NEVER VERIFIED TO HAVE BEEN ADMINISTERED.
#:
#: UNREPAIRABLE above is about MISSING cells. This is the opposite failure and
#: the more dangerous one: the cells are present, complete, scored, and carry
#: intervals -- and nothing anywhere records that the intervention the arm is
#: named after actually happened. A missing cell announces itself. An untreated
#: cell labelled as treated does not, and it publishes a transform's name over a
#: measurement of nothing.
#:
#: Established 2026-09-14 after `B-Parseltongue` was found to have applied no
#: obfuscation on any of 240 requests. Keep the two verdicts distinct: one of
#: these is DISPROVEN and the other is merely UNRECORDED, and collapsing them
#: would overclaim.
UNVERIFIED_TREATMENT = {
    ("2026-09-13-g0dm0d3-replicate", "B-Parseltongue"): {
        "verdict": "DISPROVEN",
        "detail":
            "The obfuscation never ran. G0DM0D3's Parseltongue rewrites trigger "
            "words from a fixed list of 53 security terms and returns text "
            "UNCHANGED when it finds none; the instrument is ten neutral policy "
            "questions containing no trigger. Fired on 0 of 120 records here and "
            "0 of 120 in the May run. The arm is condition B under another label, "
            "so its contrast against plain B is a NULL BY CONSTRUCTION -- and on "
            "claude-opus-4.7 that null reads +0.24 [+0.02, +0.49], EXCLUDING "
            "ZERO. Evidence: each record's own study_call_metadata.x_g0dm0d3 "
            "echo. Audit: scripts/pipeline_transform_audit.py.",
    },
    ("2026-05-27-g0dm0d3", "B-Parseltongue"): {
        "verdict": "DISPROVEN",
        "detail": "Same defect as the replicate above, 0 of 20 records.",
    },
    # A THIRD VERDICT, and the gate is what found it: I disclosed B-Parseltongue
    # and forgot that B-Layered requests obfuscation too. B-Layered is not an
    # untreated arm -- godmode, autotune and STM all fired on every record. One
    # of its four named ingredients is inert.
    ("2026-09-13-g0dm0d3-replicate", "B-Layered"): {
        "verdict": "PARTIALLY INERT",
        "detail":
            "100 records. Parseltongue fired on 0 of them, for the same reason as "
            "B-Parseltongue: no trigger words in the instrument. The arm IS "
            "treated -- godmode 100/100, autotune 100/100, STM applied 100/100 "
            "and changing the text on 25 -- so its effects are real, but they "
            "belong to the godmode system prompt plus the autotune sampling "
            "change (temperature 0.825 against the arm's plain 0.7), NOT to "
            "obfuscation. The writeup's 'layered obfuscation is the potent form' "
            "is therefore withdrawn while the EFFECT it rests on stands. "
            "Disentangling the system prompt from the sampling change needs a "
            "godmode-without-autotune arm, which has not been collected.",
    },
    ("2026-05-27-g0dm0d3", "B-Layered"): {
        "verdict": "PARTIALLY INERT",
        "detail":
            "20 records, same as the replicate above: parseltongue 0 of 20, "
            "godmode and autotune 20 of 20, STM changing the text on 1.",
    },
    ("2026-09-15-g0dm0d3-decomposition", "B-Layered"): {
        "verdict": "PARTIALLY INERT",
        "detail":
            "100 records. Parseltongue 0 of 100 again, for the same reason -- the "
            "instrument still contains no trigger words, and collecting the arm a "
            "third time does not change that. Everything else fired: godmode "
            "100/100, autotune 100/100, STM applied 100/100 and changing the text "
            "on 26. This run exists to split the two ingredients that DO fire, so "
            "the inert one is expected here rather than newly discovered.",
    },
    ("2026-05-27-abliteration", "abliterated"): {
        "verdict": "UNRECORDED",
        "detail":
            "160 records. `obliteratus_applied` is derived from whether the "
            "string 'ablit' appears in the run LABEL -- nothing inspected the "
            "weights, and no weight digest was stored, so the corpus cannot say "
            "whether the abliterated arm ran on abliterated weights. This is NOT "
            "a claim that it did not: unlike Parseltongue there is no evidence "
            "either way, which is the whole finding. run_local.py has computed a "
            "weight fingerprint since the 2026-09-13 audit, so a re-collection on "
            "the 4090 closes this; these May records cannot be retro-stamped.",
    },
    ("2026-05-27-abliteration-controls", "abliterated"): {
        "verdict": "UNRECORDED",
        "detail": "60 records, same label-derived provenance as the arm above.",
    },
}

#: RUNS SCORED BY ONE JUDGE WHERE THE CORPUS AROUND THEM USED FOUR.
#:
#: `score.py`'s `--judge` default is a single model, `anthropic/claude-haiku-4.5`.
#: The repair procedure written into CORPUS-MAP and the bias-study-prep skill said
#:
#:     python scripts/score.py <repair> --fill-missing
#:
#: with no `--judge`, so every 2026-09-14 repair was judged by ONE member of the
#: four-judge panel the records beside it were judged by. 1,415 records. Found
#: 2026-09-15 by the mirror's own G3 gate, which reported the agreement statistic
#: computed over 638 items where it expected 715 -- the repaired records carry no
#: `score_classifier_judges` array, so they are invisible to it.
#:
#: BOUNDED BEFORE BEING CALLED A CRISIS. On the 686 base-run records that carry
#: both, haiku alone equals the four-judge median on **656 of 686 (95.6%)**, the
#: rest split 20 low and 10 high, and the mean signed difference is **-0.015**.
#:
#: So the two consequences are very different in size:
#:   * AGGREGATE effect estimates are essentially unaffected. A -0.015 mean shift
#:     on a subset of records cannot move a +0.45 or a +0.59.
#:   * JUDGE-LEVEL statistics -- panel agreement, disagreement, judge lean,
#:     cross-method robustness -- silently EXCLUDE these records, because they
#:     need the per-judge array and there isn't one. Any such number computed on a
#:     spliced corpus is computed on its base records alone and must say so.
#:
#: Fixed forward: the procedure now names the panel. Closing it for the existing
#: records means re-scoring 1,415 of them through four judges, ~5,700 calls.
SINGLE_JUDGE_REPAIRS = {
    "2026-09-14-recollect-augmentation": 180,
    "2026-09-14-recollect-cn": 137,
    "2026-09-14-recollect-gpt5-augmentation": 60,
    "2026-09-14-recollect-gpt5-gradient": 51,
    "2026-09-14-recollect-gpt5-variance": 20,
    "2026-09-14-recollect-gradient": 50,
    "2026-09-14-recollect-may25": 118,
    "2026-09-14-recollect-ood": 110,
    "2026-09-14-recollect-paraphrase": 186,
    "2026-09-14-recollect-reversed-premise": 94,
    "2026-09-14-recollect-timeseries": 313,
    "2026-09-14-recollect-variance": 96,
    # Partly single-judge from an earlier pass: 189 of its 387 lack the array.
    "2026-09-05-recollect": 189,
}

#: The panel the May corpus was judged by, so the repair procedure can name it
#: instead of inheriting a default. DEVELOPER.md documents the same four.
JUDGE_PANEL = ("anthropic/claude-haiku-4.5", "openai/gpt-4.1",
               "google/gemini-2.5-flash", "deepseek/deepseek-v3.2")


#: ARMS WHERE THE SCORED TEXT IS NOT THE MODEL'S OUTPUT.
#:
#: A third distinct failure, kept apart from UNVERIFIED_TREATMENT because it is
#: the opposite one: here the transform DID fire, and that is the problem. The
#: apparatus edited the thing it was measuring.
#:
#: G0DM0D3's STM is not a prompt transform. `applySTMPost(response, stm_modules)`
#: (api/routes/chat.ts:182) runs it AFTER generation, over the model's reply, and
#: `hedge_reducer` is eleven regexes that DELETE "I think", "I believe",
#: "perhaps", "maybe", "It seems like", "It appears that", "probably",
#: "possibly", "I would say", "In my opinion" and "From my perspective".
#: `direct_mode` strips opening pleasantries. The judges then score that edited
#: text on a 1-5 rubric where hedging is precisely what separates a hedged 3 from
#: a committed 4.
#:
#: BOUNDED BY MEASUREMENT, NOT BY ASSUMPTION -- and the bound is reassuring:
#:   * a MEDIAN OF 16 CHARACTERS deleted from responses averaging ~3,500, about
#:     half of one percent of the text;
#:   * edited records score LOWER than unedited ones in both arms on Opus
#:     (3.73 vs 3.83 in B-STM, 3.38 vs 3.58 in B-Layered), so the edit runs
#:     against the hypothesis rather than for it;
#:   * so Grok's B-Layered result cannot be an editing artefact -- STM touched
#:     1 of its 55 records and deleted a single character.
#:
#: WHAT IT DOES BREAK is cross-model comparison of the STM arm: the edit is
#: severely differential, firing on 45 of 60 Opus records against 1 of 60 for
#: Grok, which does not hedge in the phrasings the regexes catch. B-STM is
#: therefore not the same intervention on the two models.
SCORED_TEXT_MODIFIED = {
    ("2026-09-13-g0dm0d3-replicate", "B-STM"): "45 of 60 Opus records edited "
        "(median 16 chars), 1 of 60 for Grok.",
    ("2026-09-13-g0dm0d3-replicate", "B-Layered"): "24 of 50 Opus records edited "
        "(median 9 chars), 1 of 55 for Grok.",
    ("2026-05-27-g0dm0d3", "B-STM"): "7 of 20 records edited.",
    ("2026-05-27-g0dm0d3", "B-Layered"): "1 of 20 records edited.",
}


def is_derived_run(run_date: str) -> bool:
    """Is this a DERIVED corpus rather than a collection?

    A spliced corpus is a VIEW over a base run plus its repairs. Its records are
    already counted twice over if a corpus-wide scan reads it alongside the base
    it derives from and the repair runs it draws on -- which is exactly what
    happened when the first splice landed: the corpus grew by 2,483 rows that
    were not new measurements, and a cross-path defect count went from agreeing
    to off-by-one.

    So: analyses read a derived corpus BY NAME, through `canonical_run`.
    Corpus-wide enumeration skips it. The distinction is declared in the
    manifest by `splice_corpus.py`, not inferred from the name, because a naming
    convention is not a guarantee.
    """
    for root in run_roots():
        p = root / run_date / "manifest.json"
        if not p.is_file():
            continue
        try:
            with p.open(encoding="utf-8") as fh:
                return bool(json.load(fh).get("derived"))
        except (OSError, ValueError):
            return False
    return False


def canonical_run(run_date: str) -> str:
    """The name an analysis should actually read for `run_date`.

    Returns the repaired corpus when one exists ON DISK, otherwise the name given.
    Callers that genuinely want the original pass it through `REPAIRS` themselves
    or read the original name directly -- this is a default, not a lock.
    """
    repaired = REPAIRS.get(run_date)
    if not repaired:
        return run_date
    for root in run_roots():
        if (root / repaired / "scored").is_dir():
            return repaired
    return run_date


def resolve_run(run_date: str, *, require_scored: bool = True) -> Path:
    """Return the run directory, raising rather than returning None.

    Searched across every corpus root BY NAME. A name present in exactly one root resolves
    with no configuration; a name present in BOTH is genuinely ambiguous and says so rather
    than picking, because picking is how an analysis silently reads the other corpus.
    """
    roots = run_roots()
    holding = [r for r in roots if (r / run_date).is_dir()]
    if len(holding) > 1:
        raise RunNotFound(
            f"ambiguous run {run_date}: it exists in "
            f"{' and '.join(r.name for r in holding)}; "
            "set STUDY_RUN_LAYOUT to choose the corpus")
    if not holding:
        have = sorted({p.name for r in roots for p in r.iterdir() if p.is_dir()})
        raise RunNotFound(
            f"no run directory {run_date}. Present: {', '.join(have) or '(none)'}")
    root = holding[0]
    d = root / run_date
    if require_scored and not (d / "scored").is_dir():
        raise RunNotFound(
            f"{root.name}/{run_date} exists but has no scored/ — "
            f"score the run before analysing it")
    return d


def manifest(run_date: str) -> dict:
    try:
        p = resolve_run(run_date, require_scored=False) / "manifest.json"
    except RunNotFound:
        return {}
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def analysis_seed(run_date: str) -> int:
    """The run's declared analysis seed, or May's frozen default."""
    v = manifest(run_date).get("analysis_seed")
    if isinstance(v, int):
        return v
    if isinstance(v, str) and v.strip().lstrip("-").isdigit():
        return int(v.strip())
    return LEGACY_SEED


def stream(seed: int, *parts: object) -> random.Random:
    """An independent generator for one cell, derived from the seed and the cell's key.

    Derived by digest rather than by ``hash()``, which is salted per process and would
    make a run irreproducible across invocations.
    """
    key = "\x1f".join([str(seed), *(str(p) for p in parts)])
    digest = hashlib.blake2b(key.encode("utf-8"), digest_size=8).digest()
    return random.Random(int.from_bytes(digest, "big"))


# --------------------------------------------------------------------- the record schema name

#: WHAT A NEW RECORD IS STAMPED WITH. One definition, imported; there were 24 literals.
#:
#: The old name was `compass-run/1`, from a retired external questionnaire this study no
#: longer administers. It is the FILE FORMAT version, never the instrument -- every one of the
#: 1,148 Ratchet battery records carries it, and so would a factions sheet. But the word sat
#: in 38 files, so every grep for the retired instrument lit up the live collector, and
#: "are you re-injecting the compass" is a reasonable question to ask of a tree that reads
#: like that. A name nobody can distinguish from the thing it is not is a bad name.
SCHEMA = "battery-run/1"

#: WHAT A READER ACCEPTS. Both, permanently.
#:
#: 1,148 records on disk carry the old name and they are not rewritten: editing collected
#: records to match a rename is falsifying provenance to satisfy a string. A reader takes
#: either; a writer emits only the new one.
SCHEMA_ACCEPTED = ("battery-run/1", "compass-run/1")


def is_run_record(rec):
    """True when this record is an answer sheet from this study's collector.

    Replaces `rec.get("schema") == "compass-run/1"`, which appeared in 24 places and had to be
    right in all of them. `runs/` also holds ~38,000 records with no schema at all -- the May
    judged corpus and its neighbours -- and every one of those filters existed to exclude them.
    """
    return isinstance(rec, dict) and rec.get("schema") in SCHEMA_ACCEPTED
