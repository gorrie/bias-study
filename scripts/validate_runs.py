#!/usr/bin/env python3
"""validate_runs.py — does each run directory say what it actually contains?

No API calls, no network. Compares every run's manifest.json against the files on disk
and reports the disagreements.

WHY. `run_study.py` wrote manifest.json with mode "w" at the end of a run, so a second
invocation into the same run-date replaced the first invocation's record outright.
data/2026-05-27-reversed-premise/manifest.json claims 3 models and 120 calls; the
directory holds 5 model files and 200 records. Four run directories carry no manifest
at all. Nothing checked, so nothing noticed.

The manifest is also where a run declares its `analysis_seed`, which the bootstrap
reads. A run without one silently inherits May's, which is correct for May's own runs
and wrong for anything new.

Under the anti-misuse rules an existing run's record is not quietly rewritten to match
the data. This reports; it does not repair.

    python validate_runs.py             # all runs
    python validate_runs.py <run> ...   # named runs
    python validate_runs.py --json      # machine-readable, for the self-test

Exit 0 when every run is consistent, 1 when any finding is raised.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from studypaths import LEGACY_SEED, NOT_RUNS, resolve_run, run_roots  # noqa: E402

#: Runs from the May 2026 sweep. Frozen: they predate the declared-seed rule and
#: reproduce against LEGACY_SEED, which is why that default exists at all.
FROZEN_PREFIX = "2026-05-"


def count_records(d: Path) -> tuple[int, int, str]:
    """(model files, records, layout) -- finding records WHEREVER this run keeps them.

    This read `raw/` only and returned (0, 0) for anything else, so every run in the
    flat collector layout was reported as "0 model file(s), 0 record(s) on disk".
    `runs/2026-09-05-wave` holds 124 files. Reporting a layout it cannot read as an
    empty run is the same defect this validator exists to catch, pointed inward: a
    check that examined nothing and printed a number as though it had.

    Layouts, in the order tried:
      "raw"    raw/*.jsonl                     -- the manifest collector
      "flat"   *.jsonl at the top level        -- the Aug-Sep barometer collector
      "nested" */*.jsonl one level down        -- calibration/<model>/<model>__C.jsonl
      "pairs"  */*/*.jsonl two levels down     -- <pair>/<arm>/<model>__<condition>.jsonl
      "none"   no records anywhere

    The "pairs" row was added 2026-09-19 and is the SAME DEFECT AS ABOVE, one level deeper.
    `runs/2026-08-30-ablation-pairs` (48 files) and `runs/2026-09-07-ablation-wave` (63 files)
    hold 364 records between them in the ablation collector's pair/arm layout, and this function
    reported both as "none, 0 records" because it stopped looking at one level of nesting.
    `run_inventory.py` saw 49 and 315 in the same directories, so two tools in this tree
    disagreed about whether a third of a thousand records existed. Adding a layout here is
    cheap; the expensive part is that the gate said nothing was there.
    """
    for layout, paths in (
        ("raw", sorted((d / "raw").glob("*.jsonl")) if (d / "raw").is_dir() else []),
        ("flat", sorted(d.glob("*.jsonl"))),
        ("nested", sorted(d.glob("*/*.jsonl"))),
        ("pairs", sorted(d.glob("*/*/*.jsonl"))),
    ):
        if not paths:
            continue
        n = 0
        for f in paths:
            try:
                with f.open(encoding="utf-8", errors="replace") as fh:
                    n += sum(1 for line in fh if line.strip())
            except OSError:
                continue
        return len(paths), n, layout
    return 0, 0, "none"


def models_on_disk(d: Path) -> set:
    """Distinct `model` values across this run's records, whatever its layout."""
    out = set()
    for p in _record_paths(d):
        try:
            with p.open(encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if not line.strip():
                        continue
                    try:
                        r = json.loads(line)
                    except ValueError:
                        continue
                    if isinstance(r, dict) and r.get("model"):
                        out.add(str(r["model"]))
        except OSError:
            continue
    return out


def empty_on_disk(d: Path) -> int:
    """Records whose response is empty -- written, but never a completed call."""
    n = 0
    for p in _record_paths(d):
        try:
            with p.open(encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if not line.strip():
                        continue
                    try:
                        r = json.loads(line)
                    except ValueError:
                        continue
                    if isinstance(r, dict) and not str(r.get("response_text") or "").strip():
                        n += 1
        except OSError:
            continue
    return n


def _record_paths(d: Path) -> list:
    for paths in (sorted((d / "raw").glob("*.jsonl")) if (d / "raw").is_dir() else [],
                  sorted(d.glob("*.jsonl")), sorted(d.glob("*/*.jsonl")),
                  sorted(d.glob("*/*/*.jsonl"))):
        if paths:
            return paths
    return []


def inspect(d: Path) -> dict:
    out = {"run": d.name, "findings": []}
    files, records, layout = count_records(d)
    out["model_files"] = files
    out["records"] = records
    out["layout"] = layout
    out["scored"] = (d / "scored").is_dir()

    # A DERIVED CORPUS MAKES NO CALLS. splice_corpus writes calls_completed: 0
    # because that is the truth -- it assembles existing records rather than
    # asking a model anything. Comparing that zero to the record count reports
    # every spliced corpus as a call-count mismatch, which is a check meant for
    # collections applied to something that is not one.
    try:
        from studypaths import is_derived_run
        derived = is_derived_run(d.name)
    except Exception:
        derived = False
    if derived:
        out["derived"] = True
        with (d / "manifest.json").open(encoding="utf-8") as fh:
            m = json.load(fh)
        if not m.get("base_run") or not m.get("splice_sources"):
            out["findings"].append({
                "code": "derived-without-provenance",
                "detail": "a derived corpus must name its base_run and splice_sources, "
                          "or its records cannot be traced to the collection they came from",
            })
        return out

    mf = d / "manifest.json"
    if not mf.is_file():
        # A MISSING manifest is only a defect where a manifest was ever written.
        # The flat and nested collector layouts never had one, and the root-level
        # skip that used to spare them broke the moment `runs/` became MIXED --
        # run_study.py started writing manifests there, the root became "covered",
        # and 30 flat runs were reported as defects on a discipline they predate.
        # Classification is per directory now, because a root is not a layout.
        if not _is_manifest_layout(d):
            # A CONTENT FREEZE IS NOT A MANIFEST AND MUST NOT BE COUNTED AS ONE.
            # `derive_manifest.py` can write manifest.derived.json for these layouts. It is
            # derived from the records, so it agrees with them by construction and proves
            # nothing about whether collection went as planned -- the attempted model set and
            # the planned call count are gone with the collector. What it does buy is real and
            # worth reporting separately: from the moment it is written, any change to a record
            # file is detectable. So this run moves from UNVALIDATED to INVENTORIED, and
            # inventoried is still not clean.
            frozen = (d / "manifest.derived.json").is_file()
            out["inventoried"] = frozen
            out["findings"].append({
                "code": "inventoried-not-validated" if frozen else "not-manifest-layout",
                "severity": "unvalidated",
                "detail": (f"{layout} collector layout: {files} file(s), {records} record(s). "
                           + ("Content frozen in manifest.derived.json, so drift is now "
                              "detectable -- but a freeze is derived from the records and "
                              "cannot validate the collection. INVENTORIED, not clean."
                              if frozen else
                              "No manifest discipline exists for this layout, so this run is "
                              "NOT VALIDATED rather than clean.")),
            })
            return out
        out["findings"].append({
            "code": "no-manifest",
            "detail": f"no manifest.json; {files} model file(s), {records} record(s) on disk",
        })
        return out
    try:
        m = json.loads(mf.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        out["findings"].append({"code": "unreadable-manifest", "detail": str(e)})
        return out

    attempted = m.get("models_attempted") or []
    completed = m.get("models_completed") or []
    # READ THE KEY THE COLLECTOR ACTUALLY WROTE. `run_study` writes models_attempted /
    # models_completed AFTER the fact; the pre-registered arms (`run_omission_orders`,
    # `run_paraphrase`) write a `models` roster BEFORE the first call, which is a stronger
    # provenance claim, not a missing one. Checking only the first pair read every one of those
    # arms as naming no models -- and the roster they DO name is the thing worth checking.
    roster = m.get("models") or []
    # A SMOKE MANIFEST NAMES ITS ROSTER IN TWO HALVES. `smoke_roster` writes `working` (the
    # models it kept) and `not_bought` (the ones it dropped, each with the reason), and their
    # UNION is what it attempted -- 16 + 6 = 22 for the 2026-09-18 roster smoke. Read as
    # `models` alone, every smoke in the tree reported naming no models while its manifest
    # named all of them, just under the schema it actually writes.
    if not roster:
        roster = list(m.get("working") or []) + list((m.get("not_bought") or {}).keys())
    claimed_models = max(len(attempted), len(completed), len(roster))
    # COMPARE MODELS TO MODELS. This compared the manifest's model count to the FILE count,
    # which only coincides in the one-file-per-model layout. `2026-09-15-g0dm0d3-decomposition`
    # names 2 models and holds 2 models across 8 files -- four conditions each -- and was
    # reported as a mismatch for having the wrong number of files, which is not a claim the
    # manifest makes. Match units, per the working agreement: a file count is not a model count.
    found_models = models_on_disk(d)
    # A MANIFEST NAMING NO MODELS IS ITS OWN FINDING, not a clean run. `claimed_models` guards
    # the comparison below because 0 != len(found) would fire on every manifest-less layout --
    # but that guard also meant a manifest whose model list had been EMPTIED read as clean.
    # Found 2026-09-20: `recollect-may25` and `recollect-ood` were listed in KNOWN for naming
    # ONE model against 7 and 8 on disk; both manifests were later overwritten with
    # `models_attempted: []`, the mismatch stopped firing, and the registry-rot report then
    # told the next reader to DELETE the exemption. The finding had not been fixed. It had got
    # worse and fallen through the guard, which is the shape LEARNINGS #44 describes.
    if not claimed_models and found_models:
        out["findings"].append({
            "code": "manifest-names-no-models",
            "detail": (f"manifest names NO models -- models_attempted, models_completed and models are all "
                       f"empty -- while raw/ holds {len(found_models)} distinct model(s) "
                       f"across {files} file(s). The model count cannot be checked at all."),
        })
    if claimed_models and found_models and claimed_models != len(found_models):
        out["findings"].append({
            "code": "model-count-mismatch",
            "detail": (f"manifest names {claimed_models} model(s); raw/ holds "
                       f"{len(found_models)} distinct model(s) across {files} file(s)"),
        })

    # AND CALLS TO CALLS. `calls_completed` counts calls that COMPLETED; a call that returned
    # nothing is still written as a record, so records = completed + empty. The decomposition
    # run claims 397 against 400 records and holds exactly 3 empty responses, which is the
    # manifest being right. Only a discrepancy that survives the empties is a finding.
    claimed_calls = m.get("calls_completed")
    if isinstance(claimed_calls, int) and records and claimed_calls == records - empty_on_disk(d):
        claimed_calls = records
    if isinstance(claimed_calls, int) and records and claimed_calls != records:
        out["findings"].append({
            "code": "call-count-mismatch",
            "detail": f"manifest claims {claimed_calls} completed call(s); "
                      f"raw/ holds {records} record(s)",
        })

    # A MANIFEST WRITTEN TO ANOTHER SPECIFICATION IS NOT MISSING A FIELD.
    #
    # Four runs here belong to the evidence-collection and residency-probe
    # workstreams and declare their own schemas -- `evidence-collection/1`,
    # `bias-residency-probe/1`, and an offline review export keyed by `kind`.
    # Their manifests carry approval records, export digests, retry policies and
    # scheduled slots; none of them has ever had an `analysis_seed`, because
    # nothing bootstraps over them.
    #
    # Demanding one produced four permanent findings that no correct action would
    # ever clear, which is how a report teaches its reader to skim. This validator
    # checks the bias-study collection discipline, and says so when a run is not
    # one rather than judging it against a rule it was never written to.
    #
    # `battery-run` IS THIS STUDY. The allowlist named the retired instrument and nothing
    # else, so when the bank was replaced on 2026-09-17 the collector began writing
    # `battery-run/1` and the panel wave -- 3,897 records, the corpus every published figure
    # in the paper is computed from -- started reading as ANOTHER WORKSTREAM. It was exempted
    # from every collection rule below, with the printed reason "no published number depends
    # on it", which is the exact opposite of true. It stayed that way because an exemption
    # prints as a tidy dash rather than a failure. An allowlist keyed on a name that changed
    # is a check whose field of view is narrower than its claim.
    #
    # AND AN UNKNOWN SCHEMA NOW BLOCKS. Exempting whatever does not match the allowlist means
    # the failure above could only ever be found by reading a dash. "This data is not ours" is
    # a claim with an owner, so each foreign schema is named in FOREIGN_SCHEMAS with whose it
    # is; anything else is a LIVE finding. Under this rule `battery-run/1` would have failed
    # on the day the collector started writing it, instead of being waved through for five
    # days with a reason that was the opposite of true.
    foreign = m.get("schema") or m.get("kind")
    if foreign and not str(foreign).startswith(OURS):
        owner = next((v for k, v in FOREIGN_SCHEMAS.items() if str(foreign).startswith(k)),
                     None)
        if owner is None:
            out["findings"].append({
                "code": "unknown-schema",
                "detail": "manifest declares schema %r, which is neither this study's "
                          "(%s) nor any workstream named in validate_runs.FOREIGN_SCHEMAS. "
                          "Say whose it is: an unrecognised schema is exempted from every "
                          "rule below, so leaving it unnamed silently un-checks a run."
                          % (foreign, ", ".join(OURS)),
            })
            return out
        out["findings"].append({
            "code": "other-workstream",
            "severity": "unvalidated",
            "detail": "manifest declares schema %r -- %s. NOT VALIDATED by the bias-study "
                      "collection rules, rather than failing them." % (foreign, owner),
        })
        return out

    # The May 2026 runs predate the declared-seed rule and correctly inherit the frozen
    # LEGACY_SEED, so their silence is policy rather than a defect. Flagging them would
    # bury the two real findings under twelve expected ones, and a report that always
    # says FLAG is a report nobody reads.
    if "analysis_seed" not in m and not d.name.startswith(FROZEN_PREFIX):
        out["findings"].append({
            "code": "no-analysis-seed",
            "detail": f"no analysis_seed declared, and this is not a frozen "
                      f"{FROZEN_PREFIX}* run, so it would silently inherit {LEGACY_SEED}. "
                      f"run_study.py writes the seed at run start; this run predates that "
                      f"or was produced another way.",
        })
    return out


#: Findings that are established facts about the MAY 2026 collection, each with the reason it
#: is not a defect in the shipped data. Everything else still fails.
#:
#: Why this registry exists: on a clean clone `validate_runs.py` exited 1 on the published
#: corpus, and a red gate on the data is indistinguishable, to a reader, from broken data. All
#: six findings are provenance gaps in runs collected in May 2026, before the manifest
#: discipline existed. None of them affects a number: every published figure recomputes from
#: the records on disk, which are intact and are what `--json` reports.
#:
#: What was deliberately NOT done: writing the four missing manifests from the data. A manifest
#: generated out of the files it exists to check cannot detect a shortfall, which is the only
#: thing a manifest is for. Fabricating provenance to turn a gate green is the move this study
#: spends its length criticising.
KNOWN = {
    # THE RECOLLECT MANIFESTS ARE LAST-WRITER-WINS SNAPSHOTS, not an account of the run.
    # Verified 2026-09-19 before being recorded here: every record is present, every record is
    # scored, and NOT ONE response is empty. What is wrong is the manifest, which names the last
    # model to finish (or none) rather than all of them -- the same mode="w" overwrite this
    # validator was built to catch, one level in. The mismatch is in the harmless direction: more
    # was collected than was recorded. It is a provenance gap and stays listed as one.
    # RE-MEASURED 2026-09-20 against the files. These two manifests no longer name ONE model --
    # they name NONE, having been rewritten at 2026-09-15T19:52 with empty model lists and
    # calls_completed=0. The records are intact and that is what makes it a provenance gap
    # rather than a data loss.
    #
    # CORRECTED 2026-09-21: the 09-19 entries said ood held "110 records, 110 of 110 scored"
    # and that this was "verified 2026-09-19 before being recorded here". It holds 106, and
    # `git show --numstat 95231e1f` (2026-09-15) is where the other four went -- deleted from
    # the raw AND scored maverick files four days BEFORE that verification was claimed. So 110
    # was not a number that went stale; it was never measured, and the word "verified" was
    # doing work nothing had done. Corrected here rather than quietly, because a declaration
    # file whose counts are asserted rather than read is the same defect as the manifests it
    # exists to declare.
    ("2026-09-14-recollect-may25", "manifest-names-no-models"):
        "Manifest rewritten with models_attempted=[] and calls_completed=0; 7 models and 118 "
        "records are on disk, mirrored in scored/, 0 empty responses. The manifest was "
        "overwritten per model and the run did not survive to write a final one.",
    ("2026-09-14-recollect-may25", "call-count-mismatch"):
        "Same cause: manifest claims 0 completed calls against 118 records on disk.",
    ("2026-09-14-recollect-ood", "manifest-names-no-models"):
        "Same overwrite: models_attempted=[]; 8 models and 106 records on disk, mirrored in "
        "scored/, 0 empty responses.",
    ("2026-09-14-recollect-ood", "call-count-mismatch"):
        "Same cause: manifest claims 0 completed calls against 106 records on disk.",
    # THE SAME OVERWRITE, ON FIVE MORE RUNS. Surfaced 2026-09-20 by the no-models finding and
    # measured before being declared: every manifest in this family was rewritten on
    # 2026-09-15 with empty model lists and calls_completed=0, and in every case the records
    # are intact and mirrored one-for-one in scored/. That is what makes this a provenance gap
    # rather than a data loss, and it is why they are declared rather than repaired -- writing
    # a model list back out of the records would be provenance derived from the thing it is
    # supposed to testify about.
    ("2026-09-14-recollect-augmentation", "manifest-names-no-models"):
        "Manifest rewritten 2026-09-15T19:52 with models_attempted=[]; 5 models and 180 "
        "records on disk, 180 scored, 0 empty.",
    ("2026-09-14-recollect-augmentation", "call-count-mismatch"):
        "Same cause: manifest claims 0 completed calls against 180 records on disk.",
    ("2026-09-14-recollect-gpt5-augmentation", "manifest-names-no-models"):
        "Same overwrite; 1 model and 60 records on disk, 60 scored, 0 empty.",
    ("2026-09-14-recollect-gpt5-augmentation", "call-count-mismatch"):
        "Same cause: manifest claims 0 completed calls against 60 records on disk.",
    ("2026-09-14-recollect-timeseries", "manifest-names-no-models"):
        "Same overwrite; 10 models and 314 records on disk, 314 scored. 33 of those records "
        "carry an EMPTY response -- written calls that returned nothing, excluded by "
        "eligibility, and counted here so the 314 is not read as 314 answers.",
    ("2026-09-14-recollect-timeseries", "call-count-mismatch"):
        "Same cause: manifest claims 0 completed calls against 314 records on disk.",
    ("2026-09-14-recollect-variance", "manifest-names-no-models"):
        "Same overwrite; 7 models and 96 records on disk, 96 scored, 0 empty.",
    ("2026-09-14-recollect-variance", "call-count-mismatch"):
        "Same cause: manifest claims 0 completed calls against 96 records on disk.",
    ("2026-09-14-recollect-reversed-premise", "manifest-names-no-models"):
        "Same overwrite; 3 models and 94 records on disk, 94 scored, 0 empty.",
    ("2026-09-14-recollect-reversed-premise", "call-count-mismatch"):
        "Manifest claims 0 completed calls and names no models; 3 models and 94 records on "
        "disk, 94 of 94 scored, 0 empty. Same per-model overwrite, caught at its first write.",
    ("2026-05-27-abliteration", "no-manifest"):
        "May 2026, before run_study.py wrote manifests. 10 model files, 160 records, all "
        "scored and all readable; the collection is intact, its request record is not.",
    ("2026-05-27-abliteration-controls", "no-manifest"):
        "Same collection, same missing manifest discipline. 3 files, 60 records.",
    ("2026-05-27-abliteration-gemma2", "no-manifest"):
        "Same collection, same missing manifest discipline. 2 files, 40 records.",
    ("2026-09-20-gemma2-recollect", "no-manifest"):
        "run_local.py writes no manifest, and none was derived from the files. Complete on "
        "independent evidence: 40 records, 2 arms x 10 items x conditions A/B x 1 sample, "
        "seed 20260527 on every record, the design RESULTS-2026-09-20-gemma2-recollect.md "
        "recorded on the day of collection; gemma2_recollect_jaccard.py --check reproduces "
        "its four figures from these files.",
    ("2026-05-27-g0dm0d3", "no-manifest"):
        "Same collection, same missing manifest discipline. 6 files, 60 records.",
    ("2026-05-27-reversed-premise", "model-count-mismatch"):
        "The manifest names 3 models; 5 are on disk. The arm was extended after the manifest "
        "was written and the manifest was not re-emitted. The extra two models are real "
        "collected data, not phantom files -- MORE landed than was recorded, which is the "
        "harmless direction, but it is still a provenance gap and is recorded as one.",
    ("2026-05-27-reversed-premise", "call-count-mismatch"):
        "Same cause: manifest claims 120 completed calls against 200 records on disk.",

    # --- run_g0dm0d3.py wrote NO manifest at all until 2026-09-14 -------------
    # run_study.py has written one since May; this collector never did, and the
    # gap was invisible because the same tools score both. The collector is fixed,
    # so runs from here carry one. These predate the fix.
    #
    # DELIBERATELY NOT RECONSTRUCTED. A manifest derived from the records it is
    # meant to check makes calls_completed == records by construction, so the
    # count gate would pass having compared a number to itself -- a vacuous gate
    # dressed as a clean run, which is the failure this file exists to catch.
    # Better an honest gap than a manufactured assurance.
    ("2026-09-13-g0dm0d3-replicate", "no-manifest"):
        "run_g0dm0d3.py wrote no manifest before 2026-09-14. 6 files, 300 records, scored, "
        "and the n=5 pair behind the corrected rung-2 estimate. Collection intact, request "
        "record absent. Not reconstructed on purpose -- see the note above.",
    ("2026-09-13-g0dm0d3-smoke", "no-manifest"):
        "Same collector, same gap. 1 file, 10 records: grok-4.3 B-Layered at an 800-token cap, "
        "the truncation detector's over-flagging control (10 flagged 0).",
    ("2026-09-13-g0dm0d3-smoke2", "no-manifest"):
        "Same collector, same gap. 1 file, 10 records: opus-4.7 at a 4,000-token cap, the "
        "detector's known-good set (10 flagged 0).",
    ("2026-09-13-truncation-proof", "no-manifest"):
        "Same collector, same gap. 1 file, 10 records: opus-4.7 at an 800-token cap, the "
        "detector's known-truncated set (10 flagged 10).",
}


#: Schema prefixes THIS study writes. Every collector that has ever stamped a record belongs
#: here, including retired ones, because a retired corpus is still ours to validate.
OURS = ("compass-run", "bias-study", "battery-run", "local-gradient-judged")

#: Schema prefixes that belong to a NAMED other workstream, with whose they are. A run
#: declaring one of these is exempted from the collection rules; a run declaring anything
#: outside both this map and OURS is a live finding, because an exemption nobody claimed is
#: how the panel wave went five days unvalidated (LEARNINGS 77).
FOREIGN_SCHEMAS = {
    "evidence-collection": "the evidence-use collector's own fixtures -- a fake backend for "
                           "retry tests, a pilot and an export. No battery record",
    "bias-residency-probe": "the residency probe, which measures where a request is served "
                            "from and administers no instrument",
    "offline_review_export": "an offline review export keyed by `kind`, carrying answer keys "
                             "for human scoring rather than a collection",
}


def _split_known(reports):
    """Partition each report's findings into (known, live). Also returns stale registry keys."""
    seen = set()
    for r in reports:
        known, live = [], []
        for f in r["findings"]:
            key = (r["run"], f["code"])
            if key in KNOWN:
                seen.add(key)
                known.append((f, KNOWN[key]))
            elif f.get("code") == "other-workstream":
                # NOT THIS STUDY'S DATA. The evidence-use collector's directories sit under
                # the same runs/ root and hold its fixtures -- a fake backend for retry
                # tests, a pilot, an export. They carry no battery record and no published
                # number depends on them, so the bias-study release cannot be blocked on
                # their provenance. Still listed, so they do not vanish.
                known.append((f, "another workstream's data under the same root; no battery "
                                 "record and no published number depends on it"))
            elif f.get("severity") == "unvalidated" and r.get("inventoried"):
                # AN INVENTORIED RUN IS DECLARED, NOT DEFECTIVE. These layouts never had a
                # manifest and never will -- the collectors are gone -- so this finding can
                # never be cleared by fixing anything, and while it counted as live the gate
                # could not pass on any tree. A gate that cannot go green is one somebody
                # deletes, taking the real checks with it.
                #
                # It is still printed, still counted in the NOT VALIDATED total, and still
                # not called clean. What changes is only whether it blocks: a run whose
                # content is frozen and whose limitation is stated has been handled as far
                # as it can be. A run with NO freeze still blocks, because that one has an
                # action attached -- `derive_manifest.py --write`.
                known.append((f, "inventoried: content frozen in manifest.derived.json, "
                                 "layout predates manifest discipline"))
            else:
                live.append(f)
        r["_known"], r["_live"] = known, live
    # ROT IS ONLY CLAIMABLE FOR RUNS THAT WERE ACTUALLY SCANNED. "Listed as known and no
    # longer occurs" is a statement about a run we looked at and did not find the finding in.
    # Comparing against the whole registry instead made every scoped invocation -- an explicit
    # run name, or a fixture corpus under STUDY_ROOT -- report the entire registry as rotted,
    # because it had not examined those runs at all. Absence of evidence was being reported as
    # evidence of repair, in the one file whose job is to notice the difference.
    scanned = {r["run"] for r in reports}
    return sorted(k for k in set(KNOWN) - seen if k[0] in scanned)


def _is_manifest_layout(d) -> bool:
    """Does this run dir use the manifest+scored layout this validator checks?"""
    return ((d / "manifest.json").is_file() or (d / "scored").is_dir() or (d / "raw").is_dir())


def main(argv: list[str]) -> int:
    as_json = "--json" in argv
    skipped = []
    not_runs = []
    names = [a for a in argv if not a.startswith("-")]
    # EVERY corpus root, not one. This validator's job is "are all runs well-formed", and the
    # mirror holds two populated corpora (May under data/, Aug-Sep under runs/). Asking
    # runs_root() for a single root made it raise on the ambiguity and validate nothing.
    roots = run_roots()
    if names:
        dirs = [resolve_run(n, require_scored=False) for n in names]
    else:
        # NOT_RUNS: a corpus root holds things that are not runs. `data/external/` is
        # Roettger et al.’s published codes, and it became visible to every enumerator the
        # day `data/` became a corpus root -- reported here as a 24,180-record run of ours
        # with no manifest discipline. See studypaths.NOT_RUNS.
        dirs = sorted((d for r in roots for d in r.iterdir()
                       if d.is_dir() and not d.name.startswith("_")
                       and d.name not in NOT_RUNS),
                      key=lambda d: d.name)
        # ONLY roots that use the manifest discipline this validator checks. The
        # August-September corpus under runs/ stores flat `model__CONDITION.jsonl` files and
        # has no manifests at all, so scanning it answers "no manifest" for all 30 of its runs
        # -- a layout mismatch, not 30 defects, and it would bury the six real known findings.
        # A whole root is in or out; individual dirs are not filtered, because a MISSING
        # manifest inside the manifest corpus is exactly the defect KNOWN enumerates.
        covered = [r for r in roots if any(r.glob("*/manifest.json"))]
        skipped[:] = [r for r in roots if r not in covered]
        dirs = [d for d in dirs if d.parent in covered]
        # A directory holding no records ANYWHERE is not a run. data/2026-05-27 and
        # data/2026-08-28 are cross-method OUTPUT directories -- four derived JSON files and
        # an empty raw/ -- and were reported as two runs missing their manifests. That is a
        # misclassification, not a defect, and it is fixed here rather than waved through by
        # adding the pair to KNOWN, which would have taught the gate to ignore a real shape.
        # A run whose collection genuinely failed still has raw/ or scored/ jsonl and still flags.
        not_runs[:] = [d for d in dirs if not any(d.rglob("*.jsonl"))]
        dirs = [d for d in dirs if any(d.rglob("*.jsonl"))]

    reports = []
    for d in dirs:
        if not d.is_dir():
            reports.append({"run": d.name, "model_files": 0, "records": 0, "scored": False,
                            "findings": [{"code": "missing", "detail": "no such run directory"}]})
            continue
        reports.append(inspect(d))

    stale = _split_known(reports)
    if not_runs and not as_json:
        print("not run directories (no records at all, derived output only): %s"
              % ", ".join(sorted(d.name for d in not_runs)))
    if skipped and not as_json:
        print("NOT COVERED: %s/ uses the flat collector layout and carries no manifests, so "
              "no manifest validation exists for that corpus at all."
              % ", ".join(sorted(r.name for r in skipped)))

    if as_json:
        print(json.dumps(reports, indent=1))
    else:
        live_total = known_total = 0
        unvalidated = []
        for r in reports:
            head = (f"{r['run']:<34} files={r['model_files']:>2} records={r['records']:>5} "
                    f"scored={'y' if r['scored'] else 'n'}")
            if not r["findings"]:
                print(f"  ok   {head}")
                continue
            # An unvalidated layout is not a defect and not a pass. Counting it as
            # either is how 38 layout mismatches buried 5 real findings.
            if all(f.get("severity") == "unvalidated" for f in r["findings"]):
                unvalidated.append(r)
                # NAME THE REASON IN THE DASH. Three different exemptions printed the same
                # "[flat layout, not validated]", so a run skipped because it belongs to
                # another workstream was indistinguishable from one skipped for having no
                # manifest discipline -- and the panel wave hid in that column for five days
                # (LEARNINGS 78). A reader cannot agree with an exemption they cannot see.
                tag = ("inventoried, not validated" if r.get("inventoried")
                       else "not validated")
                why = ", ".join(sorted({f["code"] for f in r["findings"]}))
                print(f"  --   {head}   [{r.get('layout')} layout, {tag}: {why}]")
                continue
            print(f"  {'FLAG' if r['_live'] else 'known'}  {head}")
            for f in r["_live"]:
                print(f"         {f['code']}: {f['detail']}")
                live_total += 1
            for f, why in r["_known"]:
                print(f"         [known] {f['code']}: {f['detail']}")
                print(f"                 {why}")
                known_total += 1
        print(f"\n{live_total} live finding(s) and {known_total} known one(s) "
              f"across {len(reports)} run(s)")
        if unvalidated:
            recs = sum(r["records"] for r in unvalidated)
            inv = [r for r in unvalidated if r.get("inventoried")]
            irec = sum(r["records"] for r in inv)
            print(f"{len(unvalidated)} run(s) holding {recs} record(s) use a collector layout "
                  f"with NO manifest discipline, so they are NOT VALIDATED -- not clean.")
            if inv:
                print(f"  of those, {len(inv)} holding {irec} record(s) are INVENTORIED: their "
                      f"content is frozen in manifest.derived.json and `derive_manifest.py "
                      f"--check` will fail on any drift. That is an integrity guarantee, not a "
                      f"validation -- a freeze derived from the records cannot testify about "
                      f"the collection that produced them.")
            rest = len(unvalidated) - len(inv)
            if rest:
                # NAME THE REMEDY ONLY WHERE IT SHIPS. `derive_manifest.py` is study-side --
                # gate 3b is registered tree="study" -- and the public mirror does not carry
                # it, so printing the command there sends a reader after a tool that is not
                # in the tree they are holding. The mirror's own cross-tree test caught that
                # on 2026-09-20 when this file was exported, which is the test doing its job.
                #
                # The command is BUILT FROM THE PATH THAT WAS TESTED rather than typed, so
                # the message cannot name a file the guard did not check. That also settles a
                # standoff between the two reference checks: a literal path here is a dead
                # reference in the mirror, and the wording that exempts it there is a false
                # denial in the study, where the file exists. Neither check is wrong -- the
                # static string was.
                freezer = Path(__file__).resolve().parent / "derive_manifest.py"
                if freezer.is_file():
                    print(f"  the remaining {rest} hold no freeze; run "
                          f"`python scripts/{freezer.name} --write`.")
                else:
                    print(f"  the remaining {rest} hold no freeze. The tool that writes one "
                          f"is study-side and is not in this tree.")
        if known_total:
            print("Known findings are enumerated in validate_runs.KNOWN with the reason each "
                  "is not a defect in the data.")

    # A registry entry whose finding has stopped occurring is a lie the next reader inherits,
    # so its disappearance FAILS rather than passing quietly. Same shape as the NOT_IN_REPO
    # rot check in check_skill_docs.py, and for the same reason: a whitelist nobody re-checks
    # is how a real defect gets waved through later.
    if stale:
        print("\nREGISTRY ROT -- these are listed as known and no longer occur:")
        for run, code in stale:
            print(f"   {run}: {code}")
        print("Remove them from validate_runs.KNOWN. A stale exemption hides the next defect.")
        return 1

    return 1 if any(r["_live"] for r in reports) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
