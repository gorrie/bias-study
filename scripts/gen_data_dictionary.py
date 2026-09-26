#!/usr/bin/env python3
"""Generate DATA-DICTIONARY.md from the corpus, so it cannot describe a corpus that moved.

WHY. The published runs are ~19,600 records across two record schemas and 45 distinct fields,
and nothing in this repository told a reader what any of them mean. A dataset whose fields are
undocumented is not shared, it is merely uploaded: a re-user has to reverse-engineer
`scoring_status` from its values and guess whether `score_classifier` is an integer.

WHY GENERATED. A hand-typed dictionary is wrong the first time a collector adds a field, and
nobody re-reads it. Presence, coverage, type and categorical vocabulary are DERIVED from the
records on every run. Only the meanings are written by hand, because meaning cannot be derived --
and a field that appears in the data with no entry in DESCRIPTIONS is a hard failure, not a blank
row. That is the property that keeps this honest: the corpus can outgrow the document, and the
document says so out loud instead of quietly omitting the new column.

Coverage is reported because it is load-bearing. `score_classifier_judges` is on 93.6% of scored
records, not all of them, and an analysis that assumes it is universal silently changes its own
denominator -- the defect this study has now made four times.

    python scripts/gen_data_dictionary.py            # write DATA-DICTIONARY.md
    python scripts/gen_data_dictionary.py --check    # exit 1 if stale or a field is undescribed

No API calls. Reads records already on disk.
"""
from __future__ import annotations

import argparse
import collections
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, HERE)

OUT = os.path.join(STUDY, "DATA-DICTIONARY.md")

#: Fields whose distinct values are small and meaningful, so the vocabulary is worth printing.
CATEGORICAL = {"channel", "position", "condition", "scoring_status", "confidence",
               "refusal_class", "score_classifier_method", "finish_reason", "topic"}

#: MEANINGS ARE HAND-WRITTEN. Everything else on the page is measured.
#: A field in the data and not in here fails --check. Do not add a blank to clear the gate.
DESCRIPTIONS = {
    # identity and routing
    "model": "Model identifier as the provider names it. NOT unique across channels: the same weights reached through OpenRouter and through Ollama are different rows and are not interchangeable.",
    "channel": "How the call was made. `openrouter` is the hosted API; `ollama` and `transformers-local` are local inference on our hardware; `g0dm0d3` is a local elicitation pipeline. The serving path moves answers, so this is a grouping variable, not metadata.",
    "vendor_response_id": "The provider's own id for the response, where it returned one. Absent for local channels.",
    "study_call_metadata": "Free-form collector state at call time. Shape varies by collector and it is not safe to index blindly.",
    # the item
    "question_id": "Item identifier within the instrument. Stable across runs; the join key for anything paired.",
    "question_text": "The item as administered. Present for the institutional-framing instrument. The retired 62-item external questionnaire is third-party licensed text and is NOT in this repository, nor is the script that retrieved it; MANIFEST.json carries the hash. The LIVE instrument, data/ratchet-battery.json, ships in full under MIT with no fetch step.",
    "topic": "Topic grouping of the item, T01..T18. Items within a topic are not independent; cluster on this, not on rows.",
    "user_prompt": "The full user turn as sent, question text included.",
    "system_prompt": "The system turn as sent, or null where none was used. The presence or absence of a directive here is the manipulation in most arms.",
    # the condition
    "condition": "Experimental arm. `A` is the fairness-instructed condition and `B` the bare ask in the main battery; `C`/`D`/`E` and the hyphenated variants are additional arms defined per run. Read the run's own prereg before pooling conditions.",
    "position": "Framing register of the item as administered: `neutral`, `mild`, `pointed`, plus `ood`, `para1..3` and `reversed` for the robustness arms. On the 2026-09-25 both-paths records it is the pair half, `critic` or `defender`.",
    "seed": "RNG seed for this call. Both arms of a stock/abliterated pair MUST carry the same one -- `run_local.py` warns that differing seeds make the contrast measure resampling rather than the intervention.",
    "sample_idx": "Replicate index within a cell, where the run collected replicates. Absent means one draw.",
    "temperature": "Sampling temperature where the collector recorded it. Absent does not mean zero.",
    "max_tokens": "Output cap requested. Load-bearing: an 800-token cap severed 21.5% of the May corpus mid-argument and the truncation was differential by model.",
    # the response
    "response_text": "The model's reply verbatim, or null on a failed call. An EMPTY string is not a refusal and not a null -- see `scoring_status` and the eligibility rule in scripts/eligibility.py.",
    "ok": "Collector's verdict that the call completed. A record with ok=false is still written, which is why a manifest's completed-call count is lower than its record count.",
    "error": "Transport or provider error string where the call failed.",
    "transient": "Marked where the collector judged a failure retryable.",
    "called_at": "UTC timestamp of the call.",
    "called_at_unrecorded": "Set where the original timestamp was lost and had to be reconstructed; the value says how.",
    "original_called_at": "The timestamp of the record this one replaces, for recollected rows.",
    "latency_ms": "Wall-clock time for the call. Includes queueing and is not a model-speed measurement.",
    "tokens_in": "Prompt tokens as the provider counted them.",
    "tokens_out": "Completion tokens as the provider counted them.",
    "usage": "The provider's raw usage object, where returned.",
    "finish_reason": "The provider's stop reason. NOT trustworthy through a proxy: the G0DM0D3 proxy returned `stop` for ten responses severed mid-word.",
    "truncated": "Collector's truncation verdict. Prefer eligibility.looks_truncated_text, which was written because finish_reason lies.",
    "word_count_total": "Words in the response. Descriptive only.",
    # scoring
    "score_classifier": "Panel score on the 1-5 rubric: the MEDIAN of the judges, so it can be a half-integer (4.5) where the panel split evenly. null where scoring was skipped.",
    "score_classifier_judges": "Per-judge breakdown, one object per judge with its own score. Present on 93.6% of scored records, NOT all -- check before dividing by it.",
    "score_classifier_method": "Which judging method produced the score: `ultraplinian` (the four-judge panel) or `reversed-rubric` (the inverted-rubric control).",
    "score_classifier_n_judges": "Judges asked.",
    "score_classifier_n_valid": "Judges that returned a parseable score. Less than n_judges means the panel was thinner than it looks.",
    "score_classifier_disagreement": "Spread across the panel for this record.",
    "judge_reasoning": "The judge's stated reasoning, where retained.",
    "scoring_status": "`ok`, or why scoring was skipped: `skipped-failed-call`, `skipped-empty-response`. The skip reasons are the DATA-EMPTY-SCORES-002 rule made visible in the record.",
    "confidence": "Rubric-independent register label: `definitive`, `hedging`, or `refusing-then-answering`.",
    "refusal_class": "Refusal taxonomy where one applies: `recovery` (refuses then answers), `empty-response`.",
    "hedge_ratio": "Share of hedging markers in the response. Descriptive; it is not the outcome any published claim rests on.",
    # repair provenance
    "recollected_from": "The run this record was recollected from, for rows replacing capped or failed originals.",
    "recollect_reason": "Why it was recollected.",
    "replaces_vendor_response_id": "The provider response id this row supersedes.",
    "spliced_from": "For derived corpora: the run this record was taken from.",
    "spliced_replaces": "For derived corpora: the record it stands in for.",
    "spliced_base_exclusion": "For derived corpora: why the base record was excluded, where it was.",
    # the 2026-09-25 both-paths free-text records: runs/2026-09-25-same-items-both-paths/{raw,scored}.
    # Same layout and scorer as the May corpus, so they share this table; these fields are theirs.
    "arm": "The pre-registered arm the record belongs to (`same-items-both-paths`). Present only on the 2026-09-25 free-text records; the May records predate the field.",
    "prereg": "Filename of the pre-registration that fixed the record's design before collection. Present only on the 2026-09-25 free-text records.",
    "instrument": "Item bank the free-text question was built from: `ratchet-battery`, meaning one of the 32 propositions asked as a one-or-two-paragraph question. Present only on the 2026-09-25 both-paths records; the May records were asked the institutional-framing question set and carry no `instrument`.",
    "item_id": "Battery item id (1-32) the question was built from. Both-paths records only; the join key to the forced-choice sheets in `runs/2026-09-16-ratchet-v3-wave`.",
    "pair_no": "The mirrored pair (1-16) the item belongs to. Both-paths records only.",
    "frame": "Which half of the mirrored pair the item is, `critic` or `defender`. Both-paths records only; `position` carries the same value there.",
    "path": "Scoring path of the record: `free-text`, meaning it was scored by the judge panel. The forced-choice half of the comparison is read from the wave, not stored here.",
    "provider": "The backend that served the call over OpenRouter. Both-paths records only.",
    "provider_pinned": "The backend requested with fallbacks off. Both-paths records only, where it equals `provider` on every record.",
}

#: THE PRESENT STUDY'S RECORDS -- one JSON line per administration of the 32-item battery, in
#: `runs/<run>/<model>__<condition>.jsonl`. Added 2026-09-24: until then this generator globbed
#: only the `raw/` and `scored/` layouts of the earlier corpus, so the dictionary described
#: none of the fields of the corpus the paper is about, and `--check` passed over it. Some names
#: are shared with the earlier corpus and MEAN SOMETHING DIFFERENT here (`condition`), so these
#: take precedence for this layout only.
BATTERY_DESCRIPTIONS = {
    # identity
    "schema": "Record schema. `battery-run/1` for every forced-choice sheet; readers also accept the older name `compass-run/1`.",
    "model": "Model identifier as the channel names it. The same weights over two channels are two rows.",
    "channel": "`openrouter` (hosted API) or `ollama` (local inference on the study's GPU). Local builds are Q4 unless the tag says otherwise.",
    "provider": "The backend that actually served the sheet (OpenRouter), or null locally. Serving path is treated as a same-version variant, so a cell served by two providers is not one cell.",
    "provider_pinned": "The backend REQUESTED, with fallbacks off, or null if unpinned. Equal to `provider` or null is healthy; a difference means the pin did not hold.",
    "instrument": "Which item bank was administered: `ratchet-battery`. 120 wave records collected 2026-09-16 16:11-17:18Z carry the earlier label `ratchet-battery-v3` for the SAME 32 items (identical `forcing_prompt`); match on the prefix, as `floor_table._instrument_matches` does.",
    "n_items": "Items on the sheet. 32 for the battery.",
    # the condition
    "condition": "The arm. Rung 1: `N` bare, `A` balance instruction, `D` commitment directive, `P` content-free placebo, `B`/`C`/`E` further prompt arms; `F000`-`F111` the three-clause factorial of the balance instruction (one bit per clause). Rung 2: `G-*` elicitation arms and `S-*` sampling presets. The exact text of every condition is in the paper's §0 Design table, generated from `run_battery`.",
    "condition_note": "One-line human description of the condition, stamped by the collector so an arm is readable without the code.",
    "system_prompt": "The system turn as sent, or null where the condition has none (`N`). The manipulation in most arms.",
    "forcing_prompt": "The user turn as sent: the fixed instruction and the 32 items in presentation order. Shipped in full.",
    "forcing_prompt_sha256": "Hash of the forcing prompt, so a reader can verify a regenerated prompt matches what was administered.",
    "forcing_prompt_chars": "Length of the forcing prompt in characters.",
    "forcing_prompt_note": "Present only on a `--scrub` export, where `forcing_prompt` was dropped; says so and how to rebuild the prompt. The shipped corpus keeps the prompt and carries no note.",
    "arm": "The pre-registered arm the sheet belongs to (`placebo-wording`, `serving-path`), stamped by `run_arm_battery.py`. Absent on runs collected by `run_battery.py`, where the directory is the arm.",
    "prereg": "Filename of the pre-registration that fixed the sheet's design before collection, on the arms that stamp it.",
    "placebo_wording": "Which placebo sentence the sheet carried: `P2` on the second-wording arm. Absent under P itself and on every other condition.",
    "template": "Wording of the forcing instruction: `T01` canonical; `T02`-`T10` the paraphrase arm only.",
    "shuffle_seed": "Presentation order. Items are shuffled by this seed; the same seed is the same order. The wave uses 11, 22 and 33.",
    "renumbered": "Protocol v2. True: items were printed `1..32` in presentation order and answers mapped back through `label_to_id`. False: each item printed under its own id (the as-is numbering, which lets some models silently skip lines). Absent on records that predate the flag, which are as-is.",
    "label_to_id": "For renumbered sheets, the map from printed label to item id, so the remap is auditable. Null otherwise.",
    "run_no": "Index of the sheet within its collector invocation. Not a replicate key across invocations; use `seed`.",
    "seed": "Sampling seed for the call. Replicates in a cell differ by seed; sample size is DISTINCT seeds, not rows.",
    "temperature": "Sampling temperature. 0.7 for the wave.",
    "max_tokens": "Completion budget requested.",
    "think": "Reasoning mode requested on local builds (false for the wave), or null on channels without the switch.",
    "thinking_chars": "Characters of reasoning trace returned, where the channel reports it.",
    "done_reason": "Local channel's stop reason (`stop`, `length`), or null.",
    "presence_penalty": "Sampling penalty sent, rung 2 only. Recorded only when sent.",
    "frequency_penalty": "Sampling penalty sent, rung 2 only. Recorded only when sent.",
    # the response
    "ok": "The call completed. False is a transport failure: the model never saw the sheet.",
    "error": "Transport error string, on failed calls.",
    "transient": "Whether the failed call was judged retryable.",
    "collected_at": "UTC timestamp of the call.",
    "latency_ms": "Wall-clock time of the call, including queueing.",
    "tokens_in": "Prompt tokens as the provider counted them.",
    "tokens_out": "Completion tokens as the provider counted them.",
    "ollama_timing_ns": "Local channel's timing breakdown in nanoseconds, or null.",
    "response_text": "The model's reply verbatim.",
    # the parse
    "answers": "The parsed sheet: a list of `{q, position}`, where `q` is the ITEM ID (already remapped on renumbered sheets, with `printed_label` kept) and `position` is 0 Strongly Disagree, 1 Disagree, 2 Agree, 3 Strongly Agree. There is no neutral option.",
    "n_answers": "Items answered. A sheet with 0 < n_answers < 32 is a PARTIAL sheet: it fails validity and is dropped whole.",
    "problems": "Why the sheet is invalid, one string per problem (missing items, contradictory repeats, call failed). Empty on a valid sheet.",
    "valid": "The sheet is complete and self-consistent. Every analysis reads valid sheets only.",
    "failure_mode": "Why an invalid sheet failed: `refused`, `transport`, `budget-exhausted`, `truncated`, or `other` (includes silent omission). Null on a valid sheet.",
    "classifier": "Version of the validity/failure rule that labelled this record (`structural/1`-`/3`). `run_battery.CLASSIFIER_VERSION` documents each; `refusal_table --audit` holds current-version rows to exact agreement.",
    # rung 2
    "rung": "Escalation-ladder rung: 2 for the elicitation arms.",
    "base_condition": "The rung-1 condition a rung-2 arm is built on (`B`).",
    "transform_source": "Where the rung-2 transform's constants came from.",
    "g0dm0d3_provenance": "The G0DM0D3 source files read for the transform, each with a content digest (`sha256_12`), and the boost constants applied.",
    "system_prompt_chars": "Length of the rung-2 system prompt in characters.",
    "instructs_against_measured_outcome": "Rung 2: where the arm's prompt itself instructs against the outcome being measured (e.g. 'never refuse'), the offending phrases; null otherwise. A refusal under such an arm is measured against an explicit order not to.",
    "boost_applied": "Rung 2: whether G0DM0D3's sampling boost was applied.",
    "sampling_preset": "Rung 2 sampling ladder: `S-Precise`, `S-Balanced`, `S-Creative`, `S-Chaotic`, or null.",
    "preset_full": "The complete sampling preset as defined, including fields the channel does not accept.",
    "preset_fields_not_sent": "Preset fields NOT sent because the channel does not accept them, so the arm's effective sampling is stated rather than assumed.",
    "question_id": "Item id, on the rung-2 control arms that re-administer the earlier free-text questions.",
    "question_text": "Item text for those questions.",
}

#: RECORDS WITH NO `schema` IN THE FLAT LAYOUT: the runs `export_scrubbed.NOT_SHIPPED` keeps
#: back (the XSTest refusal-ablation series, the superseded first local gradient, the
#: development fixtures). Present in the private tree only; in the public mirror this table
#: renders nothing and is omitted. Described so the private tree's dictionary is complete, and
#: kept apart so an unshipped arm's fields never read as fields of the published corpus.
UNSHIPPED_DESCRIPTIONS = {
    "model": "Model identifier as the channel names it.",
    "arm": "Which build of the refusal-ablation series answered, or the dose arm's name.",
    "id": "Refusal-ablation prompt id (XSTest; third-party text, not shipped).",
    "type": "XSTest prompt category.",
    "label": "XSTest's label for the prompt: `safe` or `unsafe`.",
    "prompt": "The prompt administered: XSTest's text in the refusal-ablation series; the fixture's request text in the 2026-09-08 evidence pilots.",
    "reply": "The model's reply in the refusal-ablation series.",
    "gen": "Generation settings for that arm.",
    "think": "Reasoning mode requested on the local build.",
    "keyword_refused": "Keyword-rule refusal verdict for that reply.",
    "judge_model": "Local judge model that classified or scored the reply.",
    "judge_verdict": "The judge's verdict (e.g. `COMPLIED`).",
    "judge_raw": "The judge's raw output.",
    "request_id": "Channel request id, where returned (the 2026-09-08 evidence pilots).",
    "condition": "The battery condition applied to a free-text question in the superseded first local gradient (`mask-gradient`).",
    "system_prompt": "The system turn as sent in that arm, or null.",
    "question_id": "Which of the earlier free-text questions was asked in that arm.",
    "question_text": "The question as asked.",
    "response_text": "The model's reply verbatim in that arm.",
    "score_local_judge": "Local judge score in that arm.",
}
UNSHIPPED_CATEGORICAL = {"arm", "type", "label", "condition", "judge_verdict", "keyword_refused"}

#: IN THE PUBLIC MIRROR the only records with no `schema` are `runs/mask-gradient/`, which
#: SHIPS. The comment above said this table renders nothing there; that stopped being true
#: when mask-gradient shipped, and the mirror's dictionary then called shipped records
#: "unshipped" and described them as XSTest's. So the mirror gets its own label and wording.
IS_MIRROR = os.path.basename(os.path.dirname(STUDY)) != "research"
MIRROR_SCHEMALESS_DESCRIPTIONS = {
    "model": "Model identifier as the channel names it.",
    "arm": "Which local build answered: `qwen38-stock`, `qwen38-abl`, `gemma4-stock`, `gemma4-abl`. "
           "`qwen38-stock`'s count includes 26 of its answers re-scored by a local judge, in "
           "`qwen38-stock.scored.jsonl`.",
    "gen": "Generation settings for that build (temperature 0.7, no seed).",
    "condition": "The pressure condition applied to the free-text question (A–E).",
    "system_prompt": "The system turn as sent, or null.",
    "question_id": "Which of the earlier free-text questions (T01-Q2…T10-Q2) was asked.",
    "question_text": "The question as asked.",
    "response_text": "The build's reply verbatim.",
    "judge_model": "The local judge that re-scored the reply, on the 26 re-scored records only.",
    "score_local_judge": "That judge's score, 1–5, on the 26 re-scored records only.",
}

#: Categorical fields worth a vocabulary in the battery section.
BATTERY_CATEGORICAL = {"channel", "condition", "failure_mode", "instrument", "classifier",
                       "template", "renumbered", "done_reason", "sampling_preset"}

#: THE JUDGED ARM OF THE LOCAL GRADIENT -- `runs/2026-09-25-local-gradient-judged/*.jsonl`,
#: schema `local-gradient-judged/1`. One record per free-text answer: ten of the earlier
#: institutional-framing questions (`T01-Q2`..`T10-Q2`, neutral register) put to a stock build
#: and its abliteration under the six battery conditions, so the judge-free and the judged
#: instruments can be compared on the same builds. Scores are NOT on the record: they are in
#: `scores/<judge>.jsonl`, keyed by `uid`, described in SCORES_DESCRIPTIONS below. Added
#: 2026-09-25, when the flat `runs/*/*.jsonl` glob first met a second schema and would have
#: pooled it into the battery table with fifteen undescribed fields.
JUDGED_DESCRIPTIONS = {
    "schema": "Record schema: `local-gradient-judged/1`.",
    "model": "The local build as ollama names it (`hf.co/...:Q4_K_M` or a library tag).",
    "build": "Short label for the build: `stock`, or the abliteration's label (`heretic-0bserverx`). The stock/ablated contrast is a groupby on this.",
    "base": "The base model both builds derive from (`qwen38-27b`).",
    "channel": "`ollama`: local inference on the study's GPU, no API call.",
    "question_id": "Which of the earlier free-text questions was asked, `T01-Q2`..`T10-Q2`. Same ids as the May corpus under `data/`.",
    "question_text": "The question as asked, verbatim.",
    "position": "Framing register of the question: `neutral` throughout this arm.",
    "condition": "The battery condition applied to a free-text question: `N` bare, `A` balance instruction, `P` content-free placebo, `D` commitment directive, `C`, `E`. Definitions are `run_battery.CONDITION_SYSTEM` and `CONDITION_USER_SUFFIX`, the same text the forced-choice sheets received.",
    "condition_note": "One-line description of the condition, stamped by the collector.",
    "seed": "Sampling seed for the call; replicates within a cell differ by seed.",
    "temperature": "Sampling temperature, 0.7.",
    "think": "Reasoning mode requested (false).",
    "max_tokens": "Completion budget requested.",
    "timeout_s": "Per-call timeout in seconds. A call that hit it is a failed call, not a refusal.",
    "system_prompt": "The system turn as sent, or null under `N`.",
    "user_prompt": "The user turn as sent: the question plus any condition suffix.",
    "collected_at": "UTC timestamp of the call.",
    "ok": "The call completed. False is a transport failure or a timeout.",
    "error": "Error string on a failed call, else null.",
    "response_text": "The model's reply verbatim.",
    "tokens_in": "Prompt tokens as ollama counted them.",
    "tokens_out": "Completion tokens as ollama counted them.",
    "latency_ms": "Wall-clock time of the call.",
    "done_reason": "ollama's stop reason: `stop` or `length`.",
    "thinking_chars": "Characters of reasoning trace returned, if any.",
}
JUDGED_CATEGORICAL = {"build", "base", "condition", "position", "done_reason", "channel"}

#: `runs/2026-09-25-local-gradient-judged/scores/<judge>.jsonl` -- one line per (answer, judge).
SCORES_DESCRIPTIONS = {
    "uid": "Key of the answer scored: `model|question_id|condition|seed`, matching the record in the run's top-level sheets.",
    "judge": "The local judge model that scored the answer. Two judges, each selected by the calibration in `calibration.json` before any answer was scored.",
    "score": "The judge's 1-5 rubric score, as parsed from `raw`.",
    "raw": "The judge's full JSON reply, score and reasoning, verbatim.",
    "at": "UTC timestamp of the judging call.",
}
SCORES_CATEGORICAL = {"judge", "score"}

#: Schemas the flat `runs/*/*.jsonl` layout may carry. A record of any other schema there is
#: an undescribed SCHEMA and fails --check the way an undescribed field does.
from studypaths import SCHEMA_ACCEPTED  # noqa: E402

BATTERY_SCHEMAS = SCHEMA_ACCEPTED
JUDGED_SCHEMA = "local-gradient-judged/1"


def scan(*patterns, categorical=CATEGORICAL, keep=None):
    """Every record matching ANY of these globs. Takes several, and scans all of them.

    `keep(record)` selects by content -- by `schema`, in practice -- because one glob can now
    reach two record kinds: the flat `runs/<run>/*.jsonl` layout holds battery sheets AND the
    judged arm's free-text records. A record `keep` rejects is counted in `others` by its
    schema, so a schema nobody described is reported rather than silently dropped.

    THIS TOOK ONE PATTERN AND `render()` TRIED THEM IN TURN -- `data/*/raw/*.jsonl` first,
    falling back to `runs/*/raw/*.jsonl` only when the first yielded nothing. That is a
    silent-corruption shape, and the 2026-09-23 corpus move is exactly what arms it: the
    moment `data/` holds any records at all, the `runs/` branch never runs, and whatever
    stayed behind is dropped from the record counts, the file counts, the field coverage and
    the categorical vocabularies, with no message.

    Coverage percentages are the whole point of this document -- "a field on 93.6% of records
    is one an analysis must check for rather than assume" -- so a denominator quietly computed
    over half the corpus is the dictionary telling a confident lie about the other half.

    Both roots, always. A pattern that matches nothing contributes nothing, which is the
    correct behaviour and needs no branch.
    """
    fields = collections.defaultdict(collections.Counter)
    vocab = collections.defaultdict(collections.Counter)
    others = collections.Counter()
    n, nfiles = 0, 0
    paths = sorted({p for pattern in patterns
                    for p in glob.glob(os.path.join(STUDY, pattern))})
    for path in paths:
        seen_here = False
        for line in io.open(path, encoding="utf-8", errors="replace"):
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if not isinstance(r, dict):
                continue
            if keep is not None and not keep(r):
                others[str(r.get("schema"))] += 1
                continue
            seen_here = True
            n += 1
            for k, v in r.items():
                fields[k][type(v).__name__ if v is not None else "null"] += 1
                if k in categorical and not isinstance(v, (dict, list)):
                    vocab[k][str(v)] += 1
        if seen_here:
            nfiles += 1
    scan.others = others
    return n, nfiles, fields, vocab


#: The flat `runs/<run>/` layout, with every subdirectory layout a collector writes there
#: EXCEPT the ones described as their own record kind (`raw/`, `scored/`, `scores/`). The
#: local-gradient collector keeps its smoke and replicate sheets in `smoke/` and `replicate/`.
FLAT = ("runs/*/*.jsonl", "runs/*/smoke/*.jsonl", "runs/*/replicate/*.jsonl")


def render():
    """(label, patterns, descriptions, categorical, keep) per record kind.

    `battery` is the present study, flat under `runs/<run>/`, and comes first because it is
    the corpus the paper is about. `judged` and `scores` are the judged arm of the local
    gradient, which lives in the same root under its own schema. `raw`/`scored` are the
    earlier corpus under `data/`, and the 2026-09-25 both-paths free-text records under
    `runs/`, which use the same layout and scorer.
    """
    layouts = [("battery", FLAT, BATTERY_DESCRIPTIONS, BATTERY_CATEGORICAL,
                lambda r: r.get("schema") in BATTERY_SCHEMAS),
               ("judged", FLAT, JUDGED_DESCRIPTIONS, JUDGED_CATEGORICAL,
                lambda r: r.get("schema") == JUDGED_SCHEMA),
               ("scores", ("runs/*/scores/*.jsonl",), SCORES_DESCRIPTIONS, SCORES_CATEGORICAL,
                None),
               (("schemaless" if IS_MIRROR else "unshipped"), FLAT,
                (MIRROR_SCHEMALESS_DESCRIPTIONS if IS_MIRROR else UNSHIPPED_DESCRIPTIONS),
                UNSHIPPED_CATEGORICAL, lambda r: r.get("schema") is None),
               ("raw", ("data/*/raw/*.jsonl", "runs/*/raw/*.jsonl"), DESCRIPTIONS, CATEGORICAL,
                None),
               ("scored", ("data/*/scored/*.jsonl", "runs/*/scored/*.jsonl"), DESCRIPTIONS,
                CATEGORICAL, None)]
    blocks, undescribed = [], set()
    flat_schemas, flat_counted = collections.Counter(), False
    for label, patterns, descriptions, categorical, keep in layouts:
        n, nf, fields, vocab = scan(*patterns, categorical=categorical, keep=keep)
        if patterns is FLAT and not flat_counted:
            # Once: every FLAT scan rejects the same records, so counting each scan's
            # rejects would report the same schema as many times as there are kinds.
            flat_schemas.update(scan.others)
            flat_counted = True
        if not n:
            continue
        rows = []
        for k in sorted(fields, key=lambda k: (-sum(fields[k].values()), k)):
            tot = sum(fields[k].values())
            types = ", ".join(f"`{t}`" for t, _ in fields[k].most_common(3))
            if k not in descriptions:
                undescribed.add(k)
            desc = descriptions.get(k, "**UNDESCRIBED -- see gen_data_dictionary**")
            rows.append(f"| `{k}` | {tot / n:.1%} | {types} | {desc} |")
        blocks.append((label, n, nf, len(fields), rows, vocab))
    # A THIRD SCHEMA IN THE FLAT LAYOUT IS AN UNDESCRIBED SCHEMA, reported like an undescribed
    # field. Without this, a collector writing a new record kind under runs/ would see every one
    # of its records silently fall out of both tables and the document would still read complete.
    for schema, count in sorted(flat_schemas.items()):
        if schema not in BATTERY_SCHEMAS and schema != JUDGED_SCHEMA and schema != "None":
            undescribed.add("schema:%s (%d record(s) in runs/*/*.jsonl)" % (schema, count))
    return blocks, undescribed


def build_text():
    blocks, undescribed = render()
    if not blocks:
        return None, undescribed
    out = ["# Data dictionary",
           "",
           "<!-- GENERATED by scripts/gen_data_dictionary.py -- do not edit by hand.",
           "     Coverage, types and vocabularies are measured from the records on each run;",
           "     only the descriptions are written, and an undescribed field fails --check. -->",
           "",
           "Every field in the published records, what it means, and **how often it is actually",
           "present**. Coverage is not decoration: a field on 93.6% of records is one an analysis",
           "must check for rather than assume, and assuming it is how a denominator changes",
           "silently.",
           ""]
    # THE TWO CORPORA, STATED BEFORE THE FIELD TABLES. Every coverage figure below is pooled
    # across both, and a reader who does not know there are two will read a 19% coverage as
    # "this field is usually missing" rather than "this field belongs to one of two instruments
    # and is near-universal within it". The percentages are honest and the inference from them
    # is not, unless this is said first.
    out += ["## Two corpora, documented separately below", "",
            "The study ran on two instruments and this repository holds both. They are in",
            "separate directories and the distinction is load-bearing:", "",
            "| root | instrument | what it is |",
            "|---|---|---|",
            "| `runs/` | the **Ratchet battery** — 32 forced-choice items in 16 mirrored pairs, "
            "author-written, MIT, published in full | the current study. Forced-choice, read "
            "positionally: no rubric, no judge, no 1–5 score |",
            "| `data/` | the author's **institutional-framing question set** (topics "
            "`T01`..`T18`, question text included) | the May 2026 judge-scored study and its "
            "September repairs. Free-text responses scored 1–5 by a cross-vendor judge panel |",
            "",
            "Each root has its own README describing what may and may not be concluded from it.",
            "",
            "Two arms collected on 2026-09-25 sit under `runs/` and use the free-text design:",
            "`2026-09-25-same-items-both-paths` asks the 32 battery propositions as free-text",
            "questions and scores them with the May judge panel (the `raw`/`scored` tables below",
            "cover its records, with the fields marked as its own), and",
            "`2026-09-25-local-gradient-judged` puts ten of the earlier questions to a stock build",
            "and its abliteration under the battery's conditions, scored by two local judges (the",
            "`judged` and `scores` tables).",
            "",
            "**The one field difference that bites:** records in `runs/` carry an `instrument`",
            "field and records in `data/` do not, because the field postdates them. Code that",
            "filters on `instrument == \"ratchet-battery\"` drops the whole earlier corpus, and",
            "also the 120 wave records labelled `ratchet-battery-v3` (same 32 items); code that",
            "does not filter pools two designs. `floor_table._instrument_matches` is the rule the",
            "analysis uses.",
            "",
            "**`condition` means different things in the two corpora**, which is why each",
            "section below carries its own meanings.",
            ""]
    for label, n, nf, nfields, rows, vocab in blocks:
        out += [f"## `{label}` records", "",
                f"{n:,} records across {nf} files, {nfields} distinct fields.", "",
                "| field | coverage | types | meaning |", "|---|---:|---|---|"]
        out += rows
        out.append("")
        if vocab:
            out += [f"**Vocabularies in `{label}` records**, measured, most frequent first. A "
                    "value not listed does not occur.", ""]
            for k in sorted(vocab):
                vals = ", ".join(f"`{v}` ({c:,})" for v, c in vocab[k].most_common(20))
                out.append(f"- **`{k}`** — {vals}")
            out.append("")
    out += ["## What is deliberately absent", "",
            "**The live instrument is in this repository in full.** `data/ratchet-battery.json` is",
            "32 author-written propositions in 16 mirrored pairs, MIT-licensed with everything",
            "else, with no fetch step and nothing to take on trust.",
            "",
            "Records carrying third-party text are not in this repository: the runs on the retired",
            "62-item external questionnaire (a licensed text, retired 2026-09-16), and the",
            "refusal-ablation series, whose prompts are XSTest's. `MANIFEST.json` lists every",
            "directory the export keeps back, with the reason.", ""]
    # EXACTLY ONE TRAILING NEWLINE. The last element of `out` is "", so joining and appending
    # produced a trailing BLANK line. The public mirror's `fix end of files` hook removes it at
    # commit time, which left `--check` reporting this file stale immediately after every sync
    # -- the generator and the hook disagreeing forever about one byte, with the remedy
    # (regenerate) re-creating exactly what the hook had just removed. Same loop as the
    # trailing whitespace in gen_paper's fixed-width blocks, one file over.
    return "\n".join(out).rstrip("\n") + "\n", undescribed


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="exit 1 if stale or a field is undescribed")
    args = ap.parse_args(argv)

    text, undescribed = build_text()
    if text is None:
        print("no records found under data/ or runs/ -- refusing to write an empty dictionary")
        return 1
    if undescribed:
        print(f"{len(undescribed)} field(s) in the data with no description:")
        for k in sorted(undescribed):
            print(f"   {k}")
        print("Add them to gen_data_dictionary.DESCRIPTIONS. A blank entry is not an answer.")
        return 1
    if args.check:
        old = io.open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
        if old != text:
            print(f"{os.path.basename(OUT)} is stale. Run: python scripts/gen_data_dictionary.py")
            return 1
        print(f"{os.path.basename(OUT)} matches the corpus")
        return 0
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(text)
    print(f"wrote {os.path.basename(OUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
