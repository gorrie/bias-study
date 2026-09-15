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

import json
import os
import re
import sys
from pathlib import Path


#: Stamped into every correction artifact so a regenerated report says which rule produced it.
#: Dated to September 8, when the rule was first written, NOT to this reconciliation: the rule
#: itself did not change on September 12: the two independent implementations were shown
#: equivalent on the corpus and merged. Bumping the date would imply a policy change that did
#: not happen, and would invalidate comparisons against artifacts already written under it.
POLICY_VERSION = "response-eligibility/2026-09-08"


def response_text(rec: dict) -> str:
    return (rec.get("response_text") or "")


def is_empty_response(rec: dict) -> bool:
    """No text at all. Whitespace counts as no text."""
    return not response_text(rec).strip()


def has_score(rec: dict) -> bool:
    return rec.get("score_classifier") is not None


def looks_truncated_text(text: str) -> bool:
    """Does this text end mid-sentence? The SINGLE definition, used everywhere.

    DO NOT substitute `finish_reason`. Measured 2026-09-13: through the G0DM0D3
    proxy, `claude-opus-4.7` at max_tokens=800 returned ten responses severed
    mid-word -- '...and Genuinely', '...false positives to harass', '## My Actual
    View\\n\\nThe decis' -- and the proxy reported finish_reason='stop' for every
    one. It rewrites the response body and drops the upstream reason.

    A complete answer ends on sentence-terminal punctuation, optionally wrapped in
    closing quotes/brackets or a closed markdown emphasis run. Trailing '*', '_',
    '`' or ':' alone do NOT count -- '- **' or 'the case for the other side:' is
    mid-structure. Accepting them cost this detector one of ten known-truncated
    records on its first version.

    Two further corrections, 2026-09-13:
      * a severed list marker ('...2. Speed. 3.') ends in '.' and would pass, so a
        trailing enumerator is treated as severed;
      * a closed code fence is a legitimate ending and must NOT be flagged, or a
        complete answer forces a needless re-collection.

    A SENTENCE THAT ENDS IN CHINESE ENDS IN CHINESE PUNCTUATION. Corrected
    2026-09-15. The terminal set was `[.!?]`, ASCII only, so a complete Chinese
    sentence closing on U+FF1F (fullwidth ?) or U+3002 (ideographic full stop)
    was read as severed. `qwen3-235b-a22b-thinking` answers part of the
    augmentation arm in Chinese and ended one at "...又是否接受监督？" -- a
    finished question, called truncated, re-collected twice, and it will end the
    same way every time because that is how the language is punctuated. The
    closer set gains the matching quote and bracket forms (U+201D U+2019 U+300D
    U+300F U+FF09) for the same reason.

    Counted before the detector was touched, the way the markdown-URL and
    \\boxed{} cases were: across 30,080 records in every non-derived run, TWO end
    on CJK terminal punctuation while flagged severed -- one cell, written twice
    by overlapping appends -- and NEITHER is within 95% of its cap. Both sit at
    40% of 4,000, so nothing near a ceiling is admitted by this. A record
    genuinely cut mid-clause does not land on a full stop in any script, and
    `is_truncated`'s clause 2 (`tokens_out >= max_tokens`) still catches a
    sentence that happens to finish exactly on the boundary.

    A CLOSED MARKDOWN LINK IS AN ENDING. Corrected 2026-09-15, and this one was
    previously handled the other way. `gemma-3-27b-it` and `gpt-4.1` close some
    answers with a sources list whose last line is "[Council on Foreign
    Relations](https://www.cfr.org/...)" -- no full stop, because a bulleted
    citation does not take one.

    An UNREPAIRABLE entry recorded this in September as "one record in 2,101 ends
    in a URL and that one genuinely hit the cap", and registered the cell rather
    than touching the rule. Re-counted across the WHOLE corpus, 30,089 records in
    every non-derived run, that premise does not hold: NINE records end on a
    closed markdown link while flagged severed -- five distinct cells, two models,
    three runs -- and **none of them is within 95% of its cap**. The highest sits
    at 48% of 4,000, the lowest at 17%.

    Two of the nine are `gpt-4.1` in `2026-09-13-i3-phase0`, the live
    forced-choice instrument, so this was not a pair of stale May cells: it was
    silently excluding current records, and a per-cell registry entry would never
    have caught the next one. That is the argument for a rule over a registry
    entry, and it is the same magnitude as the \\boxed{} correction above (9 in
    8,429) which was fixed the same way.

    The match requires the closing parenthesis and a scheme-or-root URL, so text
    severed inside the link ("...](https://www.cfr") stays flagged, and clause 2
    of `is_truncated` still catches a citation list that ends exactly on the cap.
    """
    t = (text or "").rstrip()
    if not t:
        return True
    if t.endswith("```"):          # a closed code fence is a complete ending
        return False
    # A CLOSED LaTeX BOX IS AN ENDING, not a severed clause. Corrected 2026-09-15.
    #
    # `llama-4-maverick` answers the out-of-domain arm in a maths register and
    # signs off "The final answer is: $\boxed{No}$", which ends on '$' and was
    # therefore called severed -- 6 of its 7 records in the ood repair, tripping
    # collection_check's DIFFERENTIAL-truncation blocker at 85.7% against 0.0%
    # elsewhere and refusing the whole run.
    #
    # Counted before the detector was touched, the same way the markdown-URL case
    # was: NINE responses in 8,429 end this way, all of them llama-4-maverick, all
    # in the ood arm, NONE within 95% of its cap -- 366 to 615 tokens of 4,000.
    # They are complete answers in an unusual format.
    #
    # The match requires the CLOSING brace, so a response cut inside the box
    # ("...$\boxed{N") does not match and stays flagged.
    if re.search(r"\\boxed\s*\{[^{}]*\}\s*\$*$", t):
        return False
    # A CLOSED MARKDOWN LINK is how a sources list ends. See the docstring: 9 of
    # 30,089, none within 95% of its cap, two of them in the live instrument.
    if re.search(r"\]\(\s*(?:https?://|/)[^)\s]*\s*\)$", t):
        return False
    # A dangling enumerator: the text is an enumerated list and the LAST item is
    # empty ("1. Cost. 2. Speed. 3."). Requiring two earlier enumerators that
    # actually carry content is what keeps an ordinary sentence ending in a number
    # ("The score was 3.") from being called severed.
    if re.search(r"\s\d+[.)]$", t) and len(re.findall(r"\b\d+[.)]\s+\S", t)) >= 2:
        return True
    return not re.search(r"[.!?。？！．][\"')\]*_`”’」』）]*$", t)


#: Below this many words, a missing full stop is not evidence of truncation.
#: A response that actually hit a token cap is long by construction; a terse
#: answer ending without punctuation is just terse.
_TRUNCATION_MIN_WORDS = 50


def is_truncated(rec: dict) -> bool:
    """Was this response cut off? The EXCLUSION decision, which needs corroboration.

    Evidence, in order of authority:
      1. the collector's explicit `truncated` verdict, if it recorded one;
      2. `tokens_out >= max_tokens` when both are known -- a response that spent
         its entire budget did not choose to stop;
      3. text that ends mid-sentence AND is long enough to have plausibly hit a
         cap.

    Clause 3 carries the length guard because the bare text heuristic is a
    heuristic. On its own it called the three-word string "a real answer"
    truncated, which would silently drop a good record -- the same class of harm
    as admitting a severed one, in the other direction. Dropping good data to
    look rigorous is not rigour.

    MEASURED, 2026-09-13, against the one hard signal the May corpus carries.
    `max_tokens` was never recorded (see INT-12), but `tokens_out` was, and that
    collector's cap was 800 -- so `tokens_out == 800` is ground truth for "cut
    off". Over 10,868 scored, non-empty records of >= 50 words:

                          heuristic SEVERED   heuristic COMPLETE
        tokens_out == 800        3278                1531
        tokens_out <  800          47                6012

        precision 98.6%   recall 68.2%

    So clause 3 is safe to exclude on: of everything it flags, 98.6% genuinely
    sat on the cap, and all 47 exceptions returned 752-759 tokens and do read as
    severed. It is UNDER-inclusive -- it misses 1,531 records that hit the cap but
    happened to finish a sentence on the boundary -- and that is the right
    direction for a rule that drops data. Closing that gap needs the cap recorded
    per record, which is why run_study.py now writes `max_tokens`, plus a one-time
    backfill of the historical corpus under a correction ledger. Do NOT close it
    by hardcoding 800 here.

    `looks_truncated_text()` stays available unguarded for the collector's
    warning and for tests, where the caller knows the context.
    """
    flag = rec.get("truncated")
    if isinstance(flag, bool):
        return flag
    cap = rec.get("max_tokens")
    if cap is None:
        cap = ((rec.get("study_call_metadata") or {}).get("max_tokens"))
    out = rec.get("tokens_out")
    if isinstance(cap, int) and isinstance(out, int) and cap > 0 and out >= cap:
        return True
    text = response_text(rec)
    if len(text.split()) < _TRUNCATION_MIN_WORDS:
        return False
    return looks_truncated_text(text)


def is_failed_call(rec: dict) -> bool:
    """Transport failed. A DISTINCT category from an empty response, because the causes are
    different and AGENTS.md requires them kept apart: a failed call produced nothing because
    the request did not complete; an empty response is a completed call that returned no text,
    usually a model spending its whole budget on reasoning tokens.

    RECONCILIATION NOTE, 2026-09-12. Two independent correction passes wrote this rule four
    days apart -- `record_quality.py` on codex/bias-study-corrections-2026-09-08 (Sept 8) and
    this module (Sept 12). The Sept-8 rule excluded `ok is False` and this one did not. On the
    primary corpus the two are EQUIVALENT, verified rather than assumed: of 5,051 scored
    records, 77 have ok=False and every one of them is unscored, so `has_score` already
    excluded all 77. Records where the rules disagree: zero. The guard is kept anyway --
    equivalence on today's corpus is not equivalence on tomorrow's collection."""
    return rec.get("ok") is False


def exclusion_reason(rec: dict):
    """Why this record is ineligible, or None if it is eligible.

    The REASON, not just the verdict, because AGENTS.md requires transport failures and empty
    responses stay distinguishable downstream -- a caller that only learns "excluded" cannot
    report which kind, and the two have different causes and different remedies.
    """
    if is_failed_call(rec):
        return "failed-call"
    if is_empty_response(rec):
        return "empty-or-missing-response"
    if is_truncated(rec):
        # A severed response is not a measurement. Distinct from an empty one: there
        # IS text, and a judge will happily score it. Measured 2026-09-13: 1,022 of
        # 4,748 scored records (21.5%) sit exactly on an 800-token cap, from 96.7%
        # of glm-4.5's records to near zero for terse models -- so the defect tracks
        # verbosity and confounds every cross-vendor comparison in the study.
        return "truncated-response"
    # A record with real text and no score is NOT unusable: the largest class of it is a
    # substantive refusal, which is a result in this study. `load_scored_records()` drops
    # anything with a reason, so returning one here would discard the refusal corpus.
    # `is_eligible()` still returns False for them -- you cannot average a missing score. The
    # two functions answer different questions and collapsing them costs the refusal results.
    return None


def is_eligible(rec: dict) -> bool:
    """May this record enter an aggregate, a CI, a drift series or a chart?"""
    return (has_score(rec)
            and not is_empty_response(rec)
            and not is_failed_call(rec)
            and not is_truncated(rec))


def is_scored_empty(rec: dict) -> bool:
    """The defect itself: a number derived from nothing. Counted, never silently dropped."""
    return has_score(rec) and is_empty_response(rec)


def is_scored_truncated(rec: dict) -> bool:
    """A score derived from half a sentence. Counted, never silently dropped."""
    return has_score(rec) and not is_empty_response(rec) and is_truncated(rec)


def partition(records):
    """-> (eligible, scored_empty, scored_truncated, unscored).

    Every record lands in exactly one bucket, so a caller can report what it excluded
    instead of quietly shrinking its own denominator.

    ARITY CHANGED 2026-09-13 from 3 to 4. Truncated records were previously eligible,
    which is how 21.5% of the corpus entered published aggregates as measurements.
    The bucket is separate from `scored_empty` because the causes and the remedies
    differ: an empty response needs re-collection at a bigger budget or exclusion,
    a truncated one needs re-collection at a bigger budget, full stop.
    """
    eligible, scored_empty, scored_truncated, unscored = [], [], [], []
    for r in records:
        if is_failed_call(r) or not has_score(r):
            unscored.append(r)
        elif is_empty_response(r):
            scored_empty.append(r)
        elif is_truncated(r):
            scored_truncated.append(r)
        else:
            eligible.append(r)
    return eligible, scored_empty, scored_truncated, unscored


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


def strict_default() -> bool:
    """EXCLUSION IS THE DEFAULT as of 2026-09-12. Set STUDY_ELIGIBILITY=historical to reproduce
    the pre-correction numbers.

    It was opt-in, which meant every default read still counted 466 scores derived from empty
    responses -- the correction existed and nothing used it. Two independent correction passes
    reached the same conclusion about those records four days apart, and a score computed from
    a blank string is not a measurement whose inclusion is a matter of taste.

    The historical path is KEPT, and deliberately: published artifacts were computed under it,
    selftest_analysis accepts either agreement reference and names which it matched, and a
    correction you cannot reverse is a correction nobody can check.
    """
    mode = os.environ.get("STUDY_ELIGIBILITY", "").strip().lower()
    if mode in ("historical", "legacy", "off"):
        return False
    return True


def apply_rule(records, strict=None, label=""):
    """Filter if strict, and SAY SO on stderr. A silent filter is how a denominator changes
    without anyone noticing; the count of what was dropped is part of the output."""
    import sys
    if strict is None:
        strict = strict_default()
    if not strict:
        return records
    eligible, scored_empty, scored_truncated, _ = partition(records)
    if scored_empty:
        print("[eligibility] %s: excluded %d scored-empty record(s) of %d"
              % (label or "records", len(scored_empty), len(records)), file=sys.stderr)
    if scored_truncated:
        print("[eligibility] %s: excluded %d scored-TRUNCATED record(s) of %d"
              % (label or "records", len(scored_truncated), len(records)), file=sys.stderr)
    return eligible + [r for r in records if not has_score(r)]


def inspect_scored_records(directory):
    """(eligible records, a quality report). The REPORT is the point.

    A reader that gets only the surviving records cannot say what it dropped, and the whole
    defect class here is denominators that shrink without anyone noticing. The report carries
    the policy version, what was attempted, what survived, and the count per exclusion reason,
    so every derived table can disclose its own selection rather than assert a clean n.
    """
    from collections import Counter
    directory = Path(directory)
    records, reasons, total = [], Counter(), 0
    for path in sorted(directory.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            total += 1
            reason = exclusion_reason(record)
            if reason:
                reasons[reason] += 1
            else:
                records.append(record)
    return records, {"policy": POLICY_VERSION, "attempted": total, "eligible": len(records),
                     "excluded": sum(reasons.values()),
                     "reasons": dict(sorted(reasons.items()))}


def load_scored_records(directory):
    """Read every *.jsonl in `directory`, returning only records the rule admits.

    Kept under the name the September 8 correction pass gave it (`record_quality.
    load_scored_records`), because its call sites are the readers that most needed the rule
    and renaming them would have been churn for its own sake. That module is superseded by
    this one; this function is the compatible entry point, running the reconciled rule.

    Exclusions are REPORTED, never silent. A reader that quietly shrinks its own denominator
    is the defect this module exists to close, not a smaller version of it.
    """
    kept, quality = inspect_scored_records(directory)
    if quality["excluded"]:
        print("[eligibility] %s: excluded %d unusable record(s) (%s); source files unchanged"
              % (directory, quality["excluded"],
                 ", ".join("%s=%d" % kv for kv in quality["reasons"].items())),
              file=sys.stderr)
    return kept
