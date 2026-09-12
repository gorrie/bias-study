"""One rule for whether a scored record may enter an aggregate — DATA-EMPTY-SCORES-002.

`score.py` has refused to score an empty response since DATA-EMPTY-SCORES-001: the call can
succeed (`ok`) and still return nothing, so a model that spends its whole token budget on
reasoning falls through to the judges with a blank string, and they score it. That fix is
forward-looking. It does nothing about the records already on disk, and nothing about the
readers, which is what this module is for.

WHAT THE AUDIT FOUND (2026-09-12, across every scored* directory in data/):

    method                      records   empty   empty WITH a score
    scored                         5051     561                  466
    scored-abliterated-gemma       1780      50                   35
    scored-adversarial-pair        1780      50                    0
    scored-blind-condition         1780      50                    0
    scored-grok-solo               1780      50                    6
    scored-reversed-rubric         1780      50                   40

Read the last column across the alternates. The SAME 50 blank strings were scored 40 times by
one judge method, 35 by another, 6 by a third, and 0 by two more. Whether a blank string
becomes a number is a property of the judging method, not of the data — and the cross-method
comparison is the study's instrument for judge contamination, so empty-response handling is a
confound sitting inside the very measurement meant to detect confounds.

Concentrated in two models: `openai/gpt-5` (287 of the primary 561) and `z-ai/glm-4.7` (44 of
every alternate's 50). `google/gemma-2-9b-it` has 60 empties and zero scores — the later fix
caught those, which is what a working rule looks like.

THE RULE. A record is eligible iff it has a score AND its response text is non-empty. Both
halves matter: `score_classifier is not None` alone is what every reader used, and it is
exactly the filter an empty-but-scored record passes.

NOT A FILTER FOR REFUSALS. A substantive refusal is a real response with real text and stays
in. This removes only records where there was nothing to read.
"""
from __future__ import annotations


def response_text(rec: dict) -> str:
    return (rec.get("response_text") or "")


def is_empty_response(rec: dict) -> bool:
    """No text at all. Whitespace counts as no text."""
    return not response_text(rec).strip()


def has_score(rec: dict) -> bool:
    return rec.get("score_classifier") is not None


def is_eligible(rec: dict) -> bool:
    """May this record enter an aggregate, a CI, a drift series or a chart?"""
    return has_score(rec) and not is_empty_response(rec)


def is_scored_empty(rec: dict) -> bool:
    """The defect itself: a number derived from nothing. Counted, never silently dropped."""
    return has_score(rec) and is_empty_response(rec)


def partition(records):
    """-> (eligible, scored_empty, unscored). Every record lands in exactly one bucket, so a
    caller can report what it excluded instead of quietly shrinking its own denominator."""
    eligible, scored_empty, unscored = [], [], []
    for r in records:
        if not has_score(r):
            unscored.append(r)
        elif is_empty_response(r):
            scored_empty.append(r)
        else:
            eligible.append(r)
    return eligible, scored_empty, unscored


def missingness(records):
    """Per (model, condition) counts, for the comparison DATA-EMPTY-SCORES-002 asks for:
    selective missingness is itself a finding, not just a denominator correction."""
    out = {}
    for r in records:
        key = (r.get("model", "?"), r.get("condition", "?"))
        cell = out.setdefault(key, {"total": 0, "eligible": 0, "scored_empty": 0, "unscored": 0})
        cell["total"] += 1
        if not has_score(r):
            cell["unscored"] += 1
        elif is_empty_response(r):
            cell["scored_empty"] += 1
        else:
            cell["eligible"] += 1
    return out


# ---- the migration switch ----------------------------------------------------------------
#
# Turning the rule on CHANGES PUBLISHED NUMBERS, so it is opt-in until the correction ledger
# has been produced and read. That is not timidity: selftest G1 asserts that ci_analysis
# reproduces WRITEUP section 5.6 exactly, bound for bound, and it SHOULD keep doing so against
# the historical corpus. A correction that silently rewrites the thing it is correcting leaves
# no way to show what moved.
#
#   default             historical behaviour; every published number still reproduces
#   STUDY_ELIGIBILITY=strict (or strict=True)   the rule applies; write to a dated dir
#
# Flip the default only once the ledger is accepted, and record the flip as a dated correction.

import os


def strict_default() -> bool:
    return os.environ.get("STUDY_ELIGIBILITY", "").strip().lower() == "strict"


def apply_rule(records, strict=None, label=""):
    """Filter if strict, and SAY SO on stderr. A silent filter is how a denominator changes
    without anyone noticing; the count of what was dropped is part of the output."""
    import sys
    if strict is None:
        strict = strict_default()
    if not strict:
        return records
    eligible, scored_empty, _ = partition(records)
    if scored_empty:
        print("[eligibility] %s: excluded %d scored-empty record(s) of %d"
              % (label or "records", len(scored_empty), len(records)), file=sys.stderr)
    return eligible + [r for r in records if not has_score(r)]
