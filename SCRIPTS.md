# Scripts

**Generated from the scripts' own docstrings by `scripts/gen_script_inventory.py`. Do not edit.** Rebuild after adding a script; `--check` exits 1 when this file is stale.

76 script(s). 0 carry no module docstring and are listed at the end.

## Collection

- **`ablation_wave.py`** — Bring the stock/ablated arm up to the wave protocol. Local GPU, zero API spend.
- **`extend_manipulation_floor.py`** — Extend the A->D manipulation floor, which the whole paper is measured against.
- **`order_floor_wave.py`** — Collect a presentation-order floor UNDER THE WAVE PROTOCOL, so the paper's central comparison stops being cross-protocol.
- **`roster_gap.py`** — Which vendors have shipped a model we have never measured, and how far behind are we.
- **`run_compass.py`** — Administer the 62 forced-choice propositions to a model under one pressure condition.
- **`run_g0dm0d3.py`** — run_g0dm0d3.py — PIPELINE rung of the bias-study escalation ladder.
- **`run_study.py`** — Execute one bias study run.
- **`test_wave_seeds.py`** — Regression tests for the two counting defects that corrupted wave 2026-09-05.
- **`wave.py`** — Repeat measurement of a FIXED panel of models, on a schedule. The barometer's time axis.

## Floors, power and detection limits

- **`chart_floors.py`** — The floors chart: every nuisance factor beside the deliberate manipulation.
- **`check_arm_match.py`** — Gate a stock/ablated pair before it is used as an experimental arm.
- **`classify_lineage.py`** — Classify model-id pairs into version successors and same-version nulls.
- **`drift_report.py`** — Generate the human-readable drift summary for one run.
- **`drift_timeseries.py`** — Cross-run aggregator for longitudinal drift analysis.
- **`floor_table.py`** — Generate every measured floor, in BOTH statistics, from raw runs only.
- **`power.py`** — What effect is this instrument actually able to detect? And which of our nulls are real?

## Scoring and the judge panel

- **`ci_analysis.py`** — ci_analysis.py — Bootstrap confidence intervals + inter-judge agreement over already-scored bias-study runs. No API calls; reads runs/<date>/scored/*.jsonl.
- **`cross_method_report.py`** — Cross-method judge-effectiveness analysis.
- **`judge_anchor.py`** — Method 8 — external anchoring. The one check that can see a lean shared by all four judges.
- **`judge_lean.py`** — Do the judges lean, and by how much? The floor nobody computed for the scoring layer.
- **`judge_methods.py`** — Multi-method judge framework for the bias study.
- **`score.py`** — Score raw bias study responses against the rubric.
- **`score_inproc_gemma.py`** — In-process Method 2 scorer — abliterated Gemma-2-9B via mlx_lm.
- **`three_axis_score.py`** — Scoring function and constraint checker for the three-axis instrument.

## Gates and generated prose

- **`add_controls_2026_09.py`** — Add the four controls this project's own 2026-09-05 work identified, to the audit matrix.
- **`controls_audit.py`** — Render the controls matrix from data/controls-audit.json. Nothing restates it in prose.
- **`gen_paper.py`** — Fill the generated blocks in PAPER-below-the-floor.md by running the analysis scripts.
- **`gen_script_inventory.py`** — Generate SCRIPTS.md from the scripts' own docstrings. Never hand-maintained.
- **`generate_charts.py`** — Generate X-launch chart assets from sweep + ci_analysis output.
- **`key_numbers.py`** — The paper's load-bearing numbers, computed -- and a check that its prose still matches them.
- **`references.py`** — Render the paper's reference list from data/controls-audit.json.
- **`refusal_table.py`** — Refusal rate by vendor and condition, recomputed from runs/ on every invocation.
- **`timeline.py`** — Generate the field timeline from data/controls-audit.json. The sequence is the argument.

## Replicating other people's studies

- **`replicate_rottger.py`** — Our floor statistic, run on somebody else's published data.

## Release and provenance

- **`check_corpus.py`** — Refuse any commit that would publish third-party instrument text.
- **`fetch_items.py`** — Retrieve the 62 forced-choice propositions at YOUR end, then prove you have the right ones.
- **`studypaths.py`** — Shared run-directory resolution and deterministic RNG streams.
- **`sweep_status.py`** — Single source of truth for judgement-tool sweep state.

## Tests and development

- **`check_no_fork.py`** — Fail if any script exists in both trees with different content.
- **`selftest_analysis.py`** — selftest_analysis.py — ten assertions over the committed May data. Zero API cost.
- **`test_ablation_slugs.py`** — Two independent abliterations of one base must never share a directory.
- **`test_analysis_plumbing.py`** — Regression tests for the analysis plumbing: encoding, run discovery, gate templates.
- **`test_compass_parser.py`** — Fixtures for the forced-choice parser in run_compass.py. Run before any collection.
- **`test_floor_resolution.py`** — Tests for the modal-resolution layer and the per-model verdict.

## Other

- **`ablation_analysis.py`** — The ablation arm, analysed in the order PREREG-2026-09-07-ablation-vs-prompt.md specifies.
- **`ablation_equivalence.py`** — CLAIM-ABLATION-CAUSAL-001 — turn "no effect found" into a bounded claim, or admit it cannot be.
- **`ablation_termination.py`** — Does abliteration change how much a model WRITES, and why are 24 wave cells short?
- **`abliteration_effect_check.py`** — abliteration_effect_check.py — single-stop dissociation report.
- **`aggregate.py`** — Aggregate scored bias study records per aggregation-rules.md.
- **`analysis.py`** — Enhanced analysis pass for a bias study run.
- **`audit_response_quality.py`** — Inventory every scored record whose response was empty — DATA-EMPTY-SCORES-001 / -002.
- **`calibration_study.py`** — STATS-BOOTSTRAP-CALIBRATION-001 — does this study's inference actually control its errors?
- **`chart_intervention_budget.py`** — One scale: how far does an intervention have to move a model before it means anything?
- **`check_doc_links.py`** — Gate: every relative markdown link in this tree's documents resolves to a real file.
- **`check_no_key_repro.py`** — Checklist item 10, made mechanical: can a reader re-derive the numbers with no API key?
- **`check_skill_docs.py`** — Fail if a skill document names a script that does not exist or a flag that was never added.
- **`constrained_probe.py`** — Score the instrument by CONSTRAINED DECODING: make an invalid answer ungenerable.
- **`convergent_validity.py`** — Do the judged scale and the mechanical instrument measure the same thing?
- **`dl_model.py`** — dl_model.py — Robust HuggingFace model downloader (host-side, resume-until-valid).
- **`dose_smoke_gate.py`** — Post-abliteration quality gate.
- **`eligibility.py`** — One rule for whether a scored record may enter an aggregate — DATA-EMPTY-SCORES-002.
- **`floor_resolution.py`** — What a modal-vs-modal floor can actually resolve, and which factor is bigger ON THE SAME MODELS.
- **`frontier_extend.py`** — Extend the one-sitting arms onto the CURRENT frontier, which the frozen panel excludes.
- **`gen_readme.py`** — Fill the README's generated blocks from the run data. Nothing in them is hand-written.
- **`logit_probe.py`** — Score the forced-choice instrument by LOGPROB instead of parsing prose, and test whether the two agree.
- **`model_cards.py`** — One card per model: can this model carry a claim at all, and on what evidence?
- **`monitor_experiment.py`** — monitor_experiment.py — the durable, cross-platform half of the experiment-monitor agent.
- **`paired_analysis.py`** — paired_analysis.py — the estimator for a matched-pair arm study. No API calls.
- **`refusal_structure.py`** — Is whole-instrument refusal all-or-nothing, and which models do it?
- **`refusal_suite_summary.py`** — Both model pairs of the XSTest-style refusal suite, with clustered intervals.
- **`robustness_checks.py`** — robustness_checks.py — Two reviewer-requested robustness analyses over already- scored runs. No API calls.
- **`run_dose_series.py`** — The Wash — Experiment 1 dose-series driver.
- **`run_inventory.py`** — Every run directory, what is in it, and what reads it.
- **`run_local.py`** — run_local.py — Run the bias question set against a LOCAL transformers model (stock or OBLITERATUS-abliterated), writing raw JSONL in the study schema so `score.py` / `aggregate.py` / `ci_analysis.py` consume it unchanged.
- **`supervised_dose_series.py`** — Supervised wrapper around run_dose_series.py.
- **`validate_runs.py`** — validate_runs.py — does each run directory say what it actually contains?

