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
    "question_text": "The item as administered. Present for the institutional-framing instrument; the 62 forced-choice propositions are third-party licensed text and are NOT in this repository -- see MANIFEST.json and fetch_items.py.",
    "topic": "Topic grouping of the item, T01..T18. Items within a topic are not independent; cluster on this, not on rows.",
    "user_prompt": "The full user turn as sent, question text included.",
    "system_prompt": "The system turn as sent, or null where none was used. The presence or absence of a directive here is the manipulation in most arms.",
    # the condition
    "condition": "Experimental arm. `A` is the fairness-instructed condition and `B` the bare ask in the main battery; `C`/`D`/`E` and the hyphenated variants are additional arms defined per run. Read the run's own prereg before pooling conditions.",
    "position": "Framing register of the item as administered: `neutral`, `mild`, `pointed`, plus `ood`, `para1..3` and `reversed` for the robustness arms.",
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
}


def scan(pattern):
    fields = collections.defaultdict(collections.Counter)
    vocab = collections.defaultdict(collections.Counter)
    n, nfiles = 0, 0
    for path in sorted(glob.glob(os.path.join(STUDY, pattern))):
        nfiles += 1
        for line in io.open(path, encoding="utf-8", errors="replace"):
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if not isinstance(r, dict):
                continue
            n += 1
            for k, v in r.items():
                fields[k][type(v).__name__ if v is not None else "null"] += 1
                if k in CATEGORICAL and not isinstance(v, (dict, list)):
                    vocab[k][str(v)] += 1
    return n, nfiles, fields, vocab


def render():
    layouts = [("raw", "data/*/raw/*.jsonl", "runs/*/raw/*.jsonl"),
               ("scored", "data/*/scored/*.jsonl", "runs/*/scored/*.jsonl")]
    blocks, undescribed, allvocab = [], set(), {}
    for label, p1, p2 in layouts:
        n, nf, fields, vocab = scan(p1)
        if not n:
            n, nf, fields, vocab = scan(p2)
        if not n:
            continue
        allvocab.update({k: v for k, v in vocab.items() if k not in allvocab})
        rows = []
        for k in sorted(fields, key=lambda k: (-sum(fields[k].values()), k)):
            tot = sum(fields[k].values())
            types = ", ".join(f"`{t}`" for t, _ in fields[k].most_common(3))
            if k not in DESCRIPTIONS:
                undescribed.add(k)
            desc = DESCRIPTIONS.get(k, "**UNDESCRIBED -- see gen_data_dictionary.DESCRIPTIONS**")
            rows.append(f"| `{k}` | {tot / n:.1%} | {types} | {desc} |")
        blocks.append((label, n, nf, len(fields), rows))
    return blocks, undescribed, allvocab


def build_text():
    blocks, undescribed, vocab = render()
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
    for label, n, nf, nfields, rows in blocks:
        out += [f"## `{label}` records", "",
                f"{n:,} records across {nf} files, {nfields} distinct fields.", "",
                "| field | coverage | types | meaning |", "|---|---:|---|---|"]
        out += rows
        out.append("")
    if vocab:
        out += ["## Categorical vocabularies", "",
                "Measured from the corpus, most frequent first. A value not listed here does not",
                "occur in the published data.", ""]
        for k in sorted(vocab):
            vals = ", ".join(f"`{v}` ({c:,})" for v, c in vocab[k].most_common(12))
            out.append(f"- **`{k}`** — {vals}")
        out.append("")
    out += ["## What is deliberately absent", "",
            "The 62 forced-choice propositions are third-party licensed text and are **not in this",
            "repository**. Records are keyed by item id, which is all that is needed to recompute a",
            "result from the answers; `fetch_items.py` retrieves the items from the same source this",
            "study used, and `MANIFEST.json` carries the hash so a reader can prove they hold the",
            "same instrument. The export is produced and re-verified against the fingerprint list",
            "by an operator tool that lives on the development side, not here — deliberately, so",
            "that the thing which generates a release is not shipped inside it.", ""]
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
