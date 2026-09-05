"""Refusal rate by vendor and condition, recomputed from runs/ on every invocation.

The table in RESULTS-2026-08-31-refusal-is-elicited.md was assembled by hand, once, from a
corpus snapshot that no longer exists -- the lineage sweep landed after it and moved every
denominator. This regenerates it from runs/ so the published number can be re-derived, and
so a later collection cannot silently move it again.

Classification is DERIVED here rather than read from the run record. Rows collected before
the structural classifier shipped carry no `failure_mode` at all, and dropping them silently
is what produced a table nobody could reproduce. The derivation is a line-for-line mirror of
run_compass.py's classifier:

    refused          = prose returned, zero answers parsed, budget intact, tokenizer intact
    truncated        = at the token cap WITH some answers parsed
    budget-exhausted = at the token cap with none
    other            = parse problems from none of the above
    valid            = a clean 62-item sheet

`--audit` checks the derivation against the stored `failure_mode` on every row that carries
one, and exits 1 on any disagreement. That is the guard: if the rule here ever drifts from
the rule in the collector, this stops being a recomputation of the same quantity.

Usage:
    python scripts/refusal_table.py                     # the corpus the paper describes
    python scripts/refusal_table.py --audit             # + derivation-vs-stored check
    python scripts/refusal_table.py --exclude                # whole corpus, nothing withheld
"""

import argparse
import collections
import json
import pathlib
import sys

#: THIS REPOSITORY HAS TWO RUN ROOTS, AND THEY ARE NOT INTERCHANGEABLE.
#:
#:   data/  the May 2026 scored study -- LLM-judged 1-5 responses. `studypaths.runs_root()`
#:          resolves to this one, and every May-study script reads it.
#:   runs/  the forced-choice barometer -- `compass-run/1` records, item-id-keyed answers,
#:          exported scrubbed of the third-party instrument by `export_scrubbed.py`.
#:
#: So this hardcode is correct and must NOT be "fixed" to call `runs_root()`: that would
#: silently point the refusal table at the wrong corpus. The two roots hold different
#: instruments measured different ways, and a script has to know which one it means.
#:
#: Written down on 2026-09-05 because a scrubbed export was copied into `data/` instead --
#: where nothing read it, `check_corpus` passed, and the only symptom was that
#: `key_numbers --check` went on reporting 1,657 runs against a README that says 1,689.
RUNS = pathlib.Path(__file__).resolve().parent.parent / "runs"
CONDITIONS = ["A", "B", "C", "D", "E", "P"]

# The RULE below is a deliberate hand-mirror of the collector's -- that independence is what
# the audit tests. The VERSION NUMBER is not mirrored: both implementations must agree about
# which version of the rule they claim to implement, or the audit is comparing two things and
# cannot say which. So it is imported, not retyped.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from run_compass import CLASSIFIER_VERSION, classify_failure  # noqa: E402

# The collector's default before it was measured, and after. A row that predates the
# max_tokens field was collected under one of these; the smaller one is the conservative
# choice for an at-cap test, because it calls MORE rows truncated and fewer refused.
LEGACY_MAX_TOKENS = 1600

# Builds check_arm_match.py has already ruled INVALID -- damaged conversions that emit prose
# with zero parsable answers. That is structurally identical to a decline and is not one:
# wash-llama31-8b-ablit invents its own questions and answers those. Excluded by name rather
# than by loosening the refusal test, which has to stay strict for every intact model.
BROKEN_BUILDS = ("wash-",)

#: Run directories withheld from every refusal figure, each with the reason it is withheld.
#: THE ONLY COPY. This set previously existed three times -- a literal set in
#: key_numbers.py, a `--exclude` argument in gen_paper.py, and an example in the docstring
#: above -- and on 2026-09-04 a new arm had to be added to all three or the paper and the
#: gate would disagree about which corpus they describe. One of them would have been missed.
#:
#: Every entry is a TARGETED collection: runs made to extend one floor, on a chosen slice of
#: models and usually a single condition. They are legitimate data for the arm they were
#: collected for and they distort any rate computed over the whole corpus, because they change
#: one condition's denominator without changing the others'.
DEFAULT_EXCLUDE = {
    # Three Google models re-collected specifically because they refuse most. A refusal rate
    # that includes a sweep selected FOR refusing is not a refusal rate.
    "2026-08-31-google-orderfloor",
    # The paraphrase floor: 6 models x 10 templates, condition A only. Including it added 132
    # condition-A runs against an unchanged directive arm, moving the matched-arms comparison
    # from 39 refusals in 486 no-directive runs to 48 in 531 while the 347 directive runs
    # stood still. The arm contrast is the finding; a one-sided denominator is not a bigger
    # sample of it. Its own floor reads these runs directly (floor_table.floor_template).
    "2026-09-04-template-floor",
}


def vendor_of(model):
    """Vendor family. Local ollama tags carry no slash, so map the ones that have a vendor.

    `google` deliberately covers Gemini and Gemma, hosted and open-weight, because that is
    what the published table did and the comparison to Cen is a vendor-family comparison.
    """
    model = (model or "?").lower()
    if "/" in model:
        return model.split("/")[0]
    if model.startswith("gemma"):
        return "google"
    if model.startswith("llama"):
        return "meta-llama"
    if model.startswith(("qwen", "qwq")):
        return "qwen"
    if model.startswith("phi"):
        return "microsoft"
    if model.startswith("mistral"):
        return "mistralai"
    return model.split(":")[0]


def classify(row):
    """Mirror of run_compass.py's classifier, applied to a stored record.

    Same order of tests, same predicates. The only substitution is the token cap: rows
    collected before the cap was recorded carry no max_tokens field, so the pre-measurement
    default stands in. That is the conservative direction -- a lower cap calls more rows
    truncated and fewer refused.
    """
    if row.get("failure_mode") == "transport":
        return "transport"
    text = row.get("response_text") or ""
    problems = row.get("problems")
    if problems is None:
        problems = [] if row.get("valid") else ["unrecorded"]
    answers = row.get("n_answers") or 0
    cap = row.get("max_tokens") or LEGACY_MAX_TOKENS
    at_cap = (row.get("tokens_out") or 0) >= cap - 10
    body = text.strip()
    corrupt = "UNK_BYTE" in body or body.count(chr(9601)) > 5
    declined = bool(body) and not answers and not at_cap and not corrupt
    if not problems:
        return "valid"
    if not answers and declined:
        return "refused"
    if at_cap and answers:
        return "truncated"
    if at_cap:
        return "budget-exhausted"
    return "other"


def load(exclude=None):
    """Every scoreable row, minus the targeted collections in DEFAULT_EXCLUDE.

    The default is the exclusion set rather than the empty set on purpose. A caller who wants
    the whole corpus has to say `load(set())` and mean it; a caller who forgets the argument
    gets the corpus the paper describes, not a silently different one.
    """
    exclude = DEFAULT_EXCLUDE if exclude is None else exclude
    rows = []
    for path in sorted(RUNS.glob("**/*.jsonl")):
        bucket = path.relative_to(RUNS).parts[0]
        if bucket in exclude:
            continue
        for line in path.open(encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "compass" not in str(row.get("instrument")):
                continue
            if (row.get("model") or "").startswith(BROKEN_BUILDS):
                continue
            row["_bucket"] = bucket
            rows.append(row)
    return rows


def audit(rows):
    """Derived classification must agree with the collector, on rows labelled by THIS rule.

    Partitioned by the row's stored `classifier` version, and that partition is the fix for a
    real defect rather than a way around one. The check was comparing today's derivation
    against labels written by rules this project deliberately replaced -- 5ecf8a1 swapped
    lexical refusal detection for the structural test because the lexical one undercounted,
    96e5fa5 stopped truncation being read as refusal -- so it was permanently red over 27 rows
    of history, and a permanently red gate is an ignored gate.

    NOT a loosening. Rows carrying the current version are held to exact agreement and a
    single disagreement exits 1, which is what the check was always for. Rows carrying an
    older version or none are counted and printed by transition, so superseded labels are
    visible rather than excused: if that number grows, someone changed a rule without bumping
    CLASSIFIER_VERSION, and this says so.
    """
    disagree = collections.Counter()
    superseded = collections.Counter()
    checked = stale = 0
    for row in rows:
        stored = row.get("failure_mode")
        if stored is None:
            continue
        derived = classify(row)
        if row.get("classifier") != CLASSIFIER_VERSION:
            stale += 1
            if derived != stored:
                superseded[(row.get("classifier") or "unversioned", stored, derived)] += 1
            continue
        checked += 1
        if derived != stored:
            disagree[(stored, derived)] += 1

    # THE NON-VACUOUS HALF, and the one that actually tests what this gate is named for.
    # Run the collector's own rule and this module's hand-mirror of it over every row and
    # compare them to each other -- no stored label involved, so it needs neither a version
    # match nor a re-collection, and it cannot pass by having nothing to check.
    mirror = collections.Counter()
    for row in rows:
        theirs = classify_failure(
            row.get("problems") if row.get("problems") is not None
            else ([] if row.get("valid") else ["unrecorded"]),
            row.get("n_answers") or 0,
            row.get("tokens_out"),
            row.get("max_tokens") or LEGACY_MAX_TOKENS,
            row.get("response_text") or "")
        if row.get("failure_mode") == "transport":
            continue  # this module short-circuits transport; the collector never sees one here
        ours = classify(row)
        # The two encode the SAME verdict differently for a clean run: the collector stores
        # None in `failure_mode` (there was no failure), this module returns the string
        # "valid" (it classifies every row, not just failures). Normalising here rather than
        # changing either side -- both encodings are right for their caller, and a comparison
        # that flags 1,445 clean runs as drift is a broken comparison, not a broken rule.
        if theirs is None and ours == "valid":
            continue
        if theirs != ours:
            mirror[(ours, theirs)] += 1

    print("AUDIT: derived vs stored")
    print("  MIRROR CHECK: this module's rule vs the collector's callable, %d row(s)"
          % len(rows))
    if mirror:
        for (ours, theirs), n in mirror.most_common():
            print("    ours=%-16s collector=%-16s  %d rows" % (ours, theirs, n))
        print("    MIRROR BROKEN -- the two implementations of one rule disagree. This is the")
        print("    drift this gate exists for, and it does not depend on any stored label.")
        return 1
    print("    the two implementations agree on every row")
    print("  %d row(s) labelled by the current classifier (%s)" % (checked, CLASSIFIER_VERSION))
    if not checked:
        print("    VACUOUS -- no row carries the current version yet, because the field was")
        print("    added after the last collection. The mirror check above is what is")
        print("    holding right now; this half becomes real at the next collection.")
    print("  %d row(s) labelled by a superseded one" % stale)
    if superseded:
        print()
        print("  SUPERSEDED LABELS -- history, not drift. Re-collection would change these:")
        for (ver, stored, derived), n in superseded.most_common():
            print("    [%s] stored=%-16s now=%-16s  %d rows" % (ver, stored, derived, n))
    print()
    if not disagree:
        print("  agreement on the current classifier: 100%")
        return 0
    for (stored, derived), n in disagree.most_common():
        print("  stored=%-16s derived=%-16s  %d rows" % (stored, derived, n))
    print("  DISAGREEMENT -- the rule here has drifted from the collector's, on rows the")
    print("  collector labelled with the SAME version. That is the failure this gate is for.")
    return 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exclude", nargs="*", default=sorted(DEFAULT_EXCLUDE),
                    help="run dirs to withhold (default: DEFAULT_EXCLUDE; pass with no "
                         "values for the whole corpus)")
    ap.add_argument("--audit", action="store_true")
    args = ap.parse_args()

    rows = load(set(args.exclude))
    if args.audit:
        rc = audit(rows)
        print()
        if rc:
            return rc

    counted = collections.defaultdict(lambda: [0, 0])
    other = collections.Counter()
    for row in rows:
        cond = row.get("condition")
        if cond not in CONDITIONS:
            continue
        mode = classify(row)
        # A run that ran out of budget, died in transit, or came back unparseable for a
        # reason the collector could not name is not evidence either way about whether the
        # model would have declined. It leaves the denominator, and is reported separately
        # so the exclusion is visible rather than assumed.
        if mode in ("truncated", "budget-exhausted", "transport", "other"):
            other[mode] += 1
            continue
        cell = counted[(vendor_of(row.get("model")), cond)]
        cell[1] += 1
        if mode == "refused":
            cell[0] += 1

    # Tie-break on the vendor name. Without it, vendors sharing a peak rate come out in set
    # iteration order, which varies between interpreter runs -- so the table was not
    # byte-reproducible and gen_paper.py --check reported it stale on every second call. A
    # paper whose thesis is that unreported nuisance factors move results cannot ship a table
    # that moves on its own.
    vendors = sorted({v for v, _ in counted},
                     key=lambda v: (-max(counted[(v, c)][0] / counted[(v, c)][1]
                                         for c in CONDITIONS if counted[(v, c)][1]), v))

    print("REFUSAL RATE BY VENDOR AND CONDITION -- recomputed from runs/")
    print("refusal = declined all 62 items: prose returned, zero answers, budget intact")
    if args.exclude:
        print("excluding: " + ", ".join(sorted(args.exclude)))
    print()
    print("vendor".ljust(16) + "".join(c.rjust(12) for c in CONDITIONS))
    for vendor in vendors:
        line = vendor.ljust(16)
        for cond in CONDITIONS:
            refused, n = counted[(vendor, cond)]
            line += ("-" if not n else "%d%% (%d)" % (round(100 * refused / n), n)).rjust(12)
        print(line)

    dp_ref = sum(counted[(v, c)][0] for v in vendors for c in ("D", "P"))
    dp_n = sum(counted[(v, c)][1] for v in vendors for c in ("D", "P"))
    print()
    print("D and P pooled: %d refusals in %d runs" % (dp_ref, dp_n))
    print("excluded as neither refusal nor answer sheet: %s"
          % (", ".join("%s %d" % (k, v) for k, v in sorted(other.items())) or "none"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
