# Scripts

**Generated from the scripts' own docstrings by `scripts/gen_script_inventory.py`. Do not edit.** Rebuild after adding a script; `--check` exits 1 when this file is stale.

160 script(s). 0 carry no module docstring and are listed at the end.

## Collection

- **`ablation_wave.py`** — Bring the stock/ablated arm up to the wave protocol. Local GPU, zero API spend.
- **`extend_manipulation_floor.py`** — Extend the A->D manipulation floor, which the whole paper is measured against.
- **`gemma2_recollect_jaccard.py`** — Recompute the Gemma-2-9B same-weights Jaccard control the paper quotes.
- **`ingest_agent_answers.py`** — Ingest an answer sheet produced by an in-harness agent into the standard run format.
- **`mask_gradient.py`** — The pressure gradient (A-E) on LOCAL stock/ablated pairs, on one judge with the closed models.
- **`order_floor_wave.py`** — Collect a presentation-order floor UNDER THE WAVE PROTOCOL, so the paper's central comparison stops being cross-protocol.
- **`order_robustness.py`** — Does the suppression effect survive presentation-order randomisation?
- **`recollect_at_cap.py`** — Re-collect the May study's truncated cells at a real token budget, PAIRED.
- **`recollect_partials.py`** — Re-collect, renumbered, every wave cell that lost a sheet to silent item omission.
- **`repair_recollect_provenance.py`** — One-shot: fix provenance on records written before recollect_at_cap was corrected.
- **`roster_gap.py`** — Which vendors have shipped a model we have never measured, and how far behind are we.
- **`run_battery.py`** — Administer the forced-choice item bank to a model under one pressure condition.
- **`run_g0dm0d3.py`** — run_g0dm0d3.py — PIPELINE rung of the bias-study escalation ladder.
- **`run_i3_wave.py`** — Collect I3 Phase 4: the frozen panel against the authored mirrored bank.
- **`run_study.py`** — Execute one bias study run.
- **`test_wave_seeds.py`** — Regression tests for the two counting defects that corrupted wave 2026-09-05.
- **`wave.py`** — Repeat measurement of a FIXED panel of models, on a schedule. The barometer's time axis.
- **`wave_completion.py`** — Collect the wave's short cells: PREREG-2026-09-25-wave-completion.md.

## Floors, power and detection limits

- **`chart_floors.py`** — The floors chart: every nuisance factor beside the deliberate manipulation.
- **`check_arm_match.py`** — Gate a stock/ablated pair before it is used as an experimental arm.
- **`classify_lineage.py`** — Classify model-id pairs into version successors and same-version nulls.
- **`drift_report.py`** — Generate the human-readable drift summary for one run.
- **`drift_timeseries.py`** — Cross-run aggregator for longitudinal drift analysis.
- **`floor_table.py`** — Generate every measured floor, in BOTH statistics, from raw runs only.
- **`group_power.py`** — What could a between-GROUP comparison on this panel detect? Asked BEFORE any effect.
- **`power.py`** — What effect is this instrument actually able to detect? And which of our nulls are real?

## Scoring and the judge panel

- **`analyze.py`** — One analysis entry point for forced-choice runs. Both instruments, all metrics.
- **`ci_analysis.py`** — ci_analysis.py — Bootstrap confidence intervals + inter-judge agreement over already-scored bias-study runs. No API calls; reads runs/<date>/scored/*.jsonl.
- **`cross_method_report.py`** — Cross-method judge-effectiveness analysis.
- **`evidence_concordance.py`** — Score an answer set on evidence-concordance: an axis-free political-position readout.
- **`judge_lean.py`** — Do the judges lean, and by how much? The floor nobody computed for the scoring layer.
- **`judge_methods.py`** — Multi-method judge framework for the bias study.
- **`score.py`** — Score raw bias study responses against the rubric.
- **`score_inproc_gemma.py`** — In-process Method 2 scorer — abliterated Gemma-2-9B via mlx_lm.
- **`three_axis_score.py`** — Scoring function and constraint checker for the three-axis instrument.

## Gates and generated prose

- **`add_controls_2026_09.py`** — Add the four controls this project's own 2026-09-05 work identified, to the audit matrix.
- **`controls_audit.py`** — Render the controls matrix from data/controls-audit.json. Nothing restates it in prose.
- **`gen_paper.py`** — Fill the generated blocks in PAPER-no-position-only-consensus.md by running the analysis scripts.
- **`gen_script_inventory.py`** — Generate SCRIPTS.md from the scripts' own docstrings. Never hand-maintained.
- **`generate_charts.py`** — Generate X-launch chart assets from sweep + ci_analysis output.
- **`key_numbers.py`** — The paper's load-bearing numbers, computed -- and a check that its prose still matches them.
- **`references.py`** — Render the paper's reference list from data/controls-audit.json.
- **`refusal_table.py`** — Refusal rate by vendor and condition, recomputed from runs/ on every invocation.
- **`timeline.py`** — Generate the field timeline from data/controls-audit.json. The sequence is the argument.

## Replicating other people's studies

- **`rederive_labels.py`** — Re-derive stored validity and failure labels from the CURRENT parser, in place.
- **`replicate_rottger.py`** — Our floor statistic, run on somebody else's published data.

## Release and provenance

- **`build_corpus_fingerprint.py`** — Generate the hashed instrument fingerprint that guards the public repository.
- **`check_corpus.py`** — Refuse any commit that would publish third-party instrument text.
- **`export_scrubbed.py`** — Export the current study's corpus root (`runs/`) for publication, scanned for third-party text.
- **`studypaths.py`** — Shared run-directory resolution and deterministic RNG streams.
- **`sweep_status.py`** — Single source of truth for judgement-tool sweep state.

## Tests and development

- **`check_no_fork.py`** — Fail if any script or test exists in both trees with different content.
- **`check_retired_instrument.py`** — Refuse a tree that has readopted a retired instrument, anywhere, under any name.
- **`demo_switch.py`** — The two-call demo: the same model, the same questions, two instructions.
- **`selftest_analysis.py`** — selftest_analysis.py — ten assertions over the committed May data. Zero API cost.
- **`test_ablation_slugs.py`** — Two independent abliterations of one base must never share a directory.
- **`test_analysis_plumbing.py`** — Regression tests for the analysis plumbing: encoding, run discovery, gate templates.
- **`test_correction_gates.py`** — Regression tests for September 8 inference and release-gate defects; no network.
- **`test_floor_resolution.py`** — Tests for the modal-resolution layer and the per-model verdict.
- **`test_sheet_parser.py`** — Fixtures for the forced-choice parser in run_battery.py. Run before any collection.

## Other

- **`ablation_analysis.py`** — The ablation arm, analysed in the order PREREG-2026-09-07-ablation-vs-prompt.md specifies.
- **`ablation_equivalence.py`** — CLAIM-ABLATION-CAUSAL-001 — turn "no effect found" into a bounded claim, or admit it cannot be.
- **`ablation_termination.py`** — Does abliteration change how much a model WRITES, and why are 24 wave cells short?
- **`abliteration_effect_check.py`** — abliteration_effect_check.py — single-stop dissociation report.
- **`aggregate.py`** — Aggregate scored bias study records per aggregation-rules.md.
- **`agreement_by_training.py`** — Does the panel's agreement survive models trained outside the alignment consensus?
- **`analysis.py`** — Enhanced analysis pass for a bias study run.
- **`arm_sheets.py`** — Shared readers and tests for the 2026-09-25 battery arms (placebo wording, serving path).
- **`audit_response_quality.py`** — Inventory every scored record whose response was empty — DATA-EMPTY-SCORES-001 / -002.
- **`both_paths.py`** — Do the judged path and the forced-choice path agree on the SAME 32 propositions?
- **`calibrate_estimators.py`** — What is each estimator's false-positive rate AT THE n IT IS ACTUALLY USED AT?
- **`calibration_study.py`** — STATS-BOOTSTRAP-CALIBRATION-001 — does this study's inference actually control its errors?
- **`chart_intervention_budget.py`** — One scale: how far does an intervention have to move a model before it means anything?
- **`check_citation.py`** — The citation metadata mints a PERMANENT DOI. Check it against the study that exists.
- **`check_comparison.py`** — Can this comparison mean anything? Ask BEFORE the spend and BEFORE the writeup.
- **`check_doc_links.py`** — Gate: every relative markdown link in this tree's documents resolves to a real file.
- **`check_empty_records.py`** — A zero-byte record file is a STUB. It must not read as "this arm has no data".
- **`check_instrument_approved.py`** — Refuse to collect against an instrument the author has not read and signed.
- **`check_named_scripts.py`** — Every script named in a shipped document must exist in this repository.
- **`check_no_key_repro.py`** — Checklist item 10, made mechanical: can a reader re-derive the numbers with no API key?
- **`check_outcomes_computable.py`** — Refuse to collect until every pre-registered outcome can be COMPUTED from a run directory.
- **`check_release_table.py`** — Does RELEASE-2026-09-07's arm inventory still match runs/?
- **`check_sheet_attribution.py`** — Can each answer be attributed to the proposition it belongs to? For some sheets, no.
- **`check_skill_docs.py`** — Fail if a skill document names a script that does not exist or a flag that was never added.
- **`check_skill_procedures.py`** — Do the skills' documented commands actually RUN, not just exist?
- **`check_undefined_names.py`** — Names a script uses and never binds -- the NameError that waits for a rare path.
- **`check_withdrawals.py`** — A withdrawal is a STATE, not an event. Check that every one of them still holds.
- **`collection_check.py`** — Is this collection fit to score? Run it BEFORE spending judge calls on a run.
- **`condition_table.py`** — Every experimental condition, its system prompt and its user suffix, read from the collector.
- **`constrained_probe.py`** — Score the instrument by CONSTRAINED DECODING: make an invalid answer ungenerable.
- **`convergent_validity.py`** — Do the judged scale and the mechanical instrument measure the same thing?
- **`crossover_jurisdiction.py`** — Does a model go easy on ITS OWN state's items, or is some topic hard for everyone?
- **`derive_manifest.py`** — Freeze what a manifest-less run actually contains, and say what cannot be recovered.
- **`dl_model.py`** — dl_model.py — Robust HuggingFace model downloader (host-side, resume-until-valid).
- **`dose_figure.py`** — The dose figure: outcome against MEASURED perturbation, not the knob setting.
- **`dose_smoke_gate.py`** — Post-abliteration quality gate.
- **`drift_battery.py`** — Version drift on the 32-item battery, scored against the same-version null. EXPLORATORY.
- **`eligibility.py`** — One rule for whether a scored record may enter an aggregate — DATA-EMPTY-SCORES-002.
- **`exact_vs_bootstrap.py`** — Does the bootstrap disagree with an exact test on the PUBLISHED contrasts?
- **`export_analysis_ready.py`** — One flat, eligibility-flagged table of every scored record, for people who are not us.
- **`export_repairs.py`** — Copy the repaired corpus into the public mirror, deriving the list rather than typing it.
- **`extract_backup_uniques.py`** — Extract the records a gitignored corpus backup holds and the live tree does not.
- **`faction_lean.py`** — The factions estimator: two-way centred sector lean, with an exact permutation null.
- **`floor_resolution.py`** — What a modal-vs-modal floor can actually resolve, and which factor is bigger ON THE SAME MODELS.
- **`frame_gap.py`** — Does the judged instrument measure a POSITION, or agreement with the FRAME?
- **`frontier_extend.py`** — Extend the one-sitting arms onto the CURRENT frontier, which the frozen panel excludes.
- **`gates.py`** — The one registry of every gate this study has, and where each one runs.
- **`gen_artifact_manifest.py`** — Checksum the large binaries the study depends on, so they can travel outside git.
- **`gen_corpus_docs.py`** — Fill the generated tables in the per-corpus-root READMEs. `--check` exits 1 on drift.
- **`gen_data_dictionary.py`** — Generate DATA-DICTIONARY.md from the corpus, so it cannot describe a corpus that moved.
- **`gen_deviations.py`** — Generate PROTOCOL-DEVIATIONS.md: what was pre-registered, what was done, what changed.
- **`gen_provenance.py`** — One machine-readable index per corpus root: what each run is, and what may be concluded.
- **`gen_readme.py`** — Fill the README's generated blocks from the run data. Nothing in them is hand-written.
- **`gen_vintage.py`** — Record each model's release date, so every claim in this study can be read by generation.
- **`gen_zenodo.py`** — Generate `.zenodo.json` from CITATION.cff, and gate what a Release will mint.
- **`instantiate_stems.py`** — Build the factions bank from four authored stems and four authored path phrases.
- **`intensity_by_claim.py`** — Does the panel reserve its strongest answer for claims with a record behind them?
- **`item_gradient.py`** — Per-item agreement at baseline: where the panel is saturated and where it divides.
- **`item_omission.py`** — Do models skip particular PROPOSITIONS, or particular PLACES ON THE PAGE?
- **`jurisdiction_gradient.py`** — Is the instruction's effect the same size on every subject, or does it pick its targets?
- **`lineage_exchangeability.py`** — STATS-LINEAGE-NULL-001 — are the four same-version sub-classes exchangeable?
- **`liu_missingness.py`** — How much of Liu, Panwang and Gu's 0613 -> 1106 shift does missingness alone produce?
- **`local_gradient.py`** — The local pressure gradient on stock and ablated builds, collected and analysed properly.
- **`model_cards.py`** — One card per model: can this model carry a claim at all, and on what evidence?
- **`monitor_experiment.py`** — monitor_experiment.py — the durable, cross-platform half of the experiment-monitor agent.
- **`multiple_comparisons.py`** — How many hypothesis tests does this study actually run, and which are corrected?
- **`null_audit.py`** — What effect could each of OUR nulls have detected? The audit we apply to everyone else.
- **`omission_arms.py`** — The as-is vs renumbered arm contrast, with the exact test that decides it.
- **`order_floor_position.py`** — Does the instruction move position further than REORDERING THE ITEMS does?
- **`pair_consistency.py`** — Agreeing with BOTH halves of a mirrored pair: incoherence, or a contested subject?
- **`paired_analysis.py`** — paired_analysis.py — the estimator for a matched-pair arm study. No API calls.
- **`paraphrase_analysis.py`** — Roettger's union statistic and our pairwise rate, on the same sheets.
- **`partials_sensitivity.py`** — Do the wave's dropped partial sheets move any floor? The pre-registered test.
- **`pipeline_decomposition.py`** — What is rung 2's surviving effect actually made of?
- **`pipeline_rung.py`** — Rung 2 of the escalation ladder, estimated. The arm the analysis pipeline could not see.
- **`pipeline_transform_audit.py`** — Did the pipeline rung apply the transform each condition is named after?
- **`placebo_wording.py`** — Is the placebo's behaviour a property of its sentence, or of any content-free instruction?
- **`position_analysis.py`** — I3 Phase 4 estimator: position, consistency and acquiescence on a mirrored bank.
- **`probe_budget.py`** — Measure the token budget the WHOLE roster needs, before collecting a wave.
- **`refresh_numbers.py`** — Re-run every number the study publishes, and say WHAT MOVED.
- **`refusal_structure.py`** — Is whole-instrument refusal all-or-nothing, and which models do it?
- **`refusal_suite_summary.py`** — Both model pairs of the XSTest-style refusal suite, with clustered intervals.
- **`release_check.py`** — Run RELEASE-2026-09-07.md's release checklist instead of asserting it.
- **`render_item_read.py`** — Render the live item bank as mirrored pairs for the human read that gates collection.
- **`replicates.py`** — One implementation of "average the replicates in a cell", for every consumer.
- **`robustness_checks.py`** — robustness_checks.py — Two reviewer-requested robustness analyses over already- scored runs. No API calls.
- **`run_arm_battery.py`** — Collect the two battery arms registered 2026-09-25: a second placebo, and the serving path.
- **`run_both_paths.py`** — Collect the 32 battery propositions as OPEN QUESTIONS, then score them with the judge panel.
- **`run_dose_series.py`** — The Wash — Experiment 1 dose-series driver.
- **`run_inventory.py`** — Every run directory, what is in it, and what reads it.
- **`run_local.py`** — run_local.py — Run the bias question set against a LOCAL transformers model (stock or OBLITERATUS-abliterated), writing raw JSONL in the study schema so `score.py` / `aggregate.py` / `ci_analysis.py` consume it unchanged.
- **`rung2_contrast.py`** — Arm minus control across TWO run directories, with the v2 floor and an exact test.
- **`serving_path.py`** — One model, two pinned backends: does the serving path move side, conviction or position?
- **`splice_corpus.py`** — Write a repaired corpus the ANALYSIS can actually read.
- **`splice_holes.py`** — Which cells are STILL missing after splicing existing re-collections in?
- **`strong_shift.py`** — How hard does a model state its answer, and what moves that? Two findings, one command.
- **`supervised_dose_series.py`** — Supervised wrapper around run_dose_series.py.
- **`ungated_numbers.py`** — Every numeric claim in the paper that NO gate is checking.
- **`validate_claim.py`** — Pre-publication gate. Refuses a claim until the data behind it passes every check.
- **`validate_runs.py`** — validate_runs.py — does each run directory say what it actually contains?
