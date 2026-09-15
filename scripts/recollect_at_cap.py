#!/usr/bin/env python3
"""Re-collect the May study's truncated cells at a real token budget, PAIRED.

WHAT WENT WRONG
---------------
`run_study.call_openrouter` had `max_tokens: int = 800` baked into its signature with no way
to override it. Measured 2026-09-04 against the published May 2026 study:

    234 of 520 raw records came back AT the 800-token cap
    117 of the 780 PUBLISHED records descend from one of those
    100 of those 117 are non-empty and therefore TRUNCATED MID-RESPONSE, and were scored
     34 raw records came back EMPTY -- all z-ai/glm-4.7, which spent the entire budget on
        reasoning tokens and returned no content at all, and the judge panel scored those too

Two models were 40 of 40 at the cap. A reasoning model emits its reasoning inside the same
budget, so 800 is not a neutral default for a 2026 frontier line-up: it is a truncation that
presents as data.

Pilot, same prompt, same model, same day:

    budget  800   ok=True  tokens_out= 801  chars=   0
    budget 4000   ok=True  tokens_out=2152  chars=6285

WHY THIS IS PAIRED AND NOT A RE-RUN
-----------------------------------
Re-collecting the whole grid would change two things at once -- the budget AND the collection
window -- and this project has spent a day finding claims that confounded exactly that. So
this re-collects ONLY the cells that hit the cap, at the same (model, question, condition)
coordinates, and writes them beside the originals. The comparison is then within-cell: same
model, same question, same condition, one factor different. That isolates the truncation.

The original records are NOT overwritten. `runs/2026-05-25/` stays exactly as published; this
writes to `runs/<date>-recollect/` and the comparison reads both.

    python scripts/recollect_at_cap.py --plan          # what it would call, no API
    python scripts/recollect_at_cap.py --run           # collect (resumable)
    python scripts/recollect_at_cap.py --compare       # paired before/after

Serial with a delay, per this project's request discipline. Resumable: cells already present
in the output are skipped, so an interrupted run costs nothing to restart.
"""
from __future__ import annotations

import argparse
import collections
import datetime as _dt
import glob
import io
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import eligibility as E  # noqa: E402  -- the one eligibility rule
from studypaths import run_roots  # noqa: E402

#: At or above this many output tokens, a response hit the 800 cap. 790 rather than 800 because
#: the provider's count and ours differ by a token or two on some models.
AT_CAP = 790

#: The budget to re-collect at. glm-4.7 needed 2,152 tokens for one answer, so 800 was not
#: marginal -- it was a third of what the model wanted. 4000 leaves headroom for the longest
#: reasoning trace observed without inviting a different failure (a model that rambles to fill
#: whatever it is given is a separate measurement, not this one).
BUDGET = 4000

#: THE MAIN STUDY, not `runs/2026-05-25`.
#:
#: This pointed at `runs/2026-05-25` -- a 520-record run -- while the corpus that
#: carries the damage is `2026-05-25-full`, 780 records, the run behind WRITEUP
#: section 5.6. Measured 2026-09-14: of the 176 cells that actually still need
#: re-collecting, the tool could see ZERO, and it reported "0 to do" with total
#: confidence. A repair tool aimed at the wrong corpus is worse than no repair
#: tool, because it closes the question.
#:
#: Resolved through the run roots so it finds the main study wherever it lives:
#: the working tree keeps it under the mirror's `data/`, not under `runs/`.
def _main_study_dir():
    from studypaths import run_roots
    for root in run_roots():
        for name in ("2026-05-25-full",):
            d = root / name
            if (d / "scored").is_dir() or (d / "raw").is_dir():
                return str(d)
    return os.path.join(STUDY, "runs", "2026-05-25-full")


SOURCE = _main_study_dir()
OUT_DIR = os.path.join(STUDY, "runs", "2026-09-05-recollect", "raw")


def is_budget_exhausted(r):
    """Did this record run out of token budget before producing an answer?

    TWO signatures, and the second was invisible to this tool until 2026-09-14.

    1. tokens_out at or above AT_CAP -- the response ran to the ceiling.

    2. A COMPLETED CALL THAT RETURNED NO TEXT. Measured across all 7,235 records
       in this corpus: 486 are empty-but-ok, and every one of them sits at a
       SINGLE EXACT token count per model --

           gpt-5             286 empties, all at 768
           glm-4.7           102 empties, all at 800
           glm-4.6            29 empties, all at 800
           kimi-k2.6          27 empties, all at 800
           glm-4.5, kimi-k2-thinking, deepseek-r1   all at 800

       A model declining to answer does not produce byte-identical token counts
       286 times. That is a budget consumed by reasoning tokens before any
       visible content, and it is confirmed by experiment: glm-4.7's empty cells
       came back COMPLETE at a 4,000-token budget, 2,000-2,700 tokens of real
       text.

       This matters because `>= 790` MISSES ALL 286 GPT-5 RECORDS, which sit at
       768. The single most damaged model in the corpus was invisible to the
       tool built to repair it, and its absence is why Ratchet ch22 reports
       GPT-5 as "indeterminate" rather than as unmeasured at that budget.

    3. TEXT THAT STOPS MID-CLAUSE, at any
    token count. `baidu/ernie-4.5-300b-a47b` truncates at 740-772 tokens, below
    the 790 threshold and below the 800 cap -- a vendor-side or tokeniser
    difference. Its tails read "...combating harmful content is", "...could be a
    more", "...prioritize **privacy by design". Nineteen of its sixty records,
    and all of them invisible to a threshold rule.

    So the question this answers is not "did it reach 800" but "is this cell
    unusable for a reason a bigger budget might fix". That is exactly the set
    `eligibility` excludes for truncation or emptiness, and the repair tool
    should target it directly rather than approximate it with a number.

    A false positive here costs one call. A false negative leaves a hole in the
    corpus that nothing will ever come back for.

    THE THRESHOLD IS RELATIVE TO THE RECORD'S OWN CAP, not a constant. AT_CAP is
    790 because the May corpus ran at 800. Applying that to a record collected at
    4,000 calls every ordinary 900-token answer "exhausted" -- which reported 914
    exhausted cells in i3-phase0, a run with 0.2% unusable records and nothing
    wrong with it. A repair tool that cannot tell a full budget from a used one
    keeps proposing work that does not exist.
    """
    if not r.get("ok"):
        return False
    text = (r.get("response_text") or "").strip()
    if not text:
        return True
    if E.looks_truncated_text(text):
        return True
    cap = r.get("max_tokens") or (r.get("study_call_metadata") or {}).get("max_tokens")
    # No recorded cap means the May era, where 800 was the only value in use.
    ceiling = (cap - 10) if isinstance(cap, int) and cap > 0 else AT_CAP
    return (r.get("tokens_out") or 0) >= ceiling


def at_cap_cells():
    """Every (model, question_id, condition) whose record exhausted its budget."""
    cells = {}
    for path in glob.glob(os.path.join(SOURCE, "**", "*.jsonl"), recursive=True):
        for line in io.open(path, encoding="utf-8"):
            if not line.strip():
                continue
            r = json.loads(line)
            if is_budget_exhausted(r):
                cells[(r.get("model"), r.get("question_id"), r.get("condition"))] = r
    return cells


def existing():
    """Cells already re-collected, so a restart costs nothing.

    Keyed by cell and LAST WINS, which also makes this the dedup: two processes appending to
    one file will duplicate a cell, and 9 of them did on 2026-09-05 when an orphaned
    background run overlapped a foreground chunk. A dict collapses them, so the comparison was
    never wrong -- but a line count was, which is why the run now reports both.
    """
    got = {}
    for path in glob.glob(os.path.join(OUT_DIR, "*.jsonl")):
        for line in io.open(path, encoding="utf-8"):
            if not line.strip():
                continue
            r = json.loads(line)
            key = (r.get("model"), r.get("question_id"), r.get("condition"))
            # PRESENT IS NOT COMPLETE. This kept any record at all, so a cell that
            # came back truncated or empty AGAIN counted as re-collected and was
            # skipped forever. Measured 2026-09-14: 33 of the 117 cells this
            # reported as done were still unusable. A cell is done when it has an
            # ELIGIBLE record; an ineligible one is the reason we are here.
            prev = got.get(key)
            if prev is not None and E.is_eligible(prev) and not E.is_eligible(r):
                continue
            got[key] = r
    return got


def is_collected(r, budget=None):
    """Has this cell been SUCCESSFULLY RE-COLLECTED? Scoring is a separate step.

    Not `eligibility.is_eligible`, which requires a SCORE. Scoring happens after
    collection, so judging collection by eligibility would mark every freshly
    collected cell incomplete and re-collect all of them on the next run -- paying
    twice for the same records and never converging.

    What collection owes is a usable RESPONSE: the call succeeded, at the new
    budget, and the text is neither empty nor severed. Whether a judge has since
    read it is not this tool's business.
    """
    if not r.get("ok"):
        return False
    text = (r.get("response_text") or "").strip()
    if not text:
        return False
    if E.looks_truncated_text(text):
        return False
    if budget is not None:
        got = r.get("max_tokens") or (r.get("study_call_metadata") or {}).get("max_tokens")
        if got != budget:
            return False
    return True


def existing_usable(budget=None):
    """Cells already re-collected to a usable response."""
    return {k: r for k, r in existing().items() if is_collected(r, budget)}


def dedup(directory=None):
    """Rewrite every JSONL in `directory` keeping ONE row per cell, last wins.

    Blind appends duplicate a cell whenever two runs overlap, and they overlapped twice on
    2026-09-05 -- 196 rows for 117 cells the second time, and the SCORED output inherited it
    row for row. The dict-keyed readers collapse duplicates so no comparison was ever wrong,
    but a row count was, and a scoring pass paid four judge calls per redundant row.

    Called automatically after a collection run so the file on disk matches the cells in it.
    """
    directory = directory or OUT_DIR
    removed = 0
    for path in sorted(glob.glob(os.path.join(directory, "*.jsonl"))):
        rows, order = {}, []
        for line in io.open(path, encoding="utf-8"):
            if not line.strip():
                continue
            r = json.loads(line)
            k = (r.get("model"), r.get("question_id"), r.get("condition"))
            if k not in rows:
                order.append(k)
            rows[k] = r
        with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
            for k in order:
                fh.write(json.dumps(rows[k], ensure_ascii=False) + "\n")
        removed += 1
    return removed


def line_count():
    """Physical rows on disk. Differs from len(existing()) exactly when a cell duplicated."""
    n = 0
    for path in glob.glob(os.path.join(OUT_DIR, "*.jsonl")):
        n += sum(1 for line in io.open(path, encoding="utf-8") if line.strip())
    return n


def safe(name):
    return "".join(c if c.isalnum() or c in "-._" else "_" for c in name)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--plan", action="store_true", help="what would be called; no API")
    ap.add_argument("--run", action="store_true", help="collect")
    ap.add_argument("--compare", action="store_true", help="paired before/after")
    ap.add_argument("--budget", type=int, default=BUDGET)
    ap.add_argument("--delay", type=float, default=2.0)
    ap.add_argument("--limit", type=int, default=0, help="stop after N cells (chunked runs)")
    ap.add_argument("--models", default="", help="comma-separated filter")
    # THE DAMAGE IS NOT CONFINED TO THE MAIN RUN. GPT-5's 286 empty records live
    # in the gradient, variance and augmentation runs, so a tool hardcoded to
    # 2026-05-25-full cannot see the single most damaged model in the corpus --
    # which is why it was never repaired and why ch22 calls it "indeterminate".
    ap.add_argument("--source", default=None,
                    help="run directory to repair (default: the main study)")
    ap.add_argument("--out-date", default=None,
                    help="run to write repairs into (default: 2026-09-05-recollect). Use a "
                         "separate one per source, so two sources never share an output "
                         "directory and a spliced corpus stays attributable.")
    args = ap.parse_args(argv)

    # Rebind the module globals the helpers read, so --source and --out-date
    # redirect BOTH the scan and the write. Rebinding one without the other would
    # repair a second source into the first one's directory and make the spliced
    # corpus unattributable.
    global SOURCE, OUT_DIR
    if args.source:
        for root in run_roots():
            candidate = root / args.source
            if (candidate / "scored").is_dir() or (candidate / "raw").is_dir():
                SOURCE = str(candidate)
                break
        else:
            print("ERROR: no run directory named %r" % args.source, file=sys.stderr)
            return 2
    if args.out_date:
        OUT_DIR = str(run_roots()[0] / args.out_date / "raw")
        os.makedirs(OUT_DIR, exist_ok=True)

    # ONE OUTPUT DIRECTORY PER SOURCE. Cells key on (model, question_id,
    # condition), and those keys COLLIDE across runs: the same model answers the
    # same question under the same condition in the gradient, variance and
    # augmentation runs. Pointing three sources at one output made the second and
    # third see the first's records as "already collected" and do nothing --
    # measured 2026-09-14, the variance run collected 0 of 20 and reported
    # success. The repair looked complete and covered one source of three.
    #
    # Refused rather than merged, because merging would leave a spliced corpus
    # whose repairs cannot be attributed to the run they repair.
    here = os.path.basename(SOURCE.rstrip("/\\"))
    foreign = {r.get("recollected_from") for r in existing().values()}
    foreign.discard(None)
    foreign.discard(here)
    if foreign:
        print("ERROR: %s already holds repairs for %s, and cell keys collide across runs.\n"
              "       Use a separate --out-date for %s, or those cells will be skipped as "
              "already done." % (os.path.basename(os.path.dirname(OUT_DIR)),
                                 ", ".join(sorted(foreign)), here), file=sys.stderr)
        return 2

    cells = at_cap_cells()
    if args.models:
        want = {m.strip() for m in args.models.split(",")}
        cells = {k: v for k, v in cells.items() if k[0] in want}
    # DONE = re-collected to a usable response AT THIS BUDGET. Not "a record
    # exists" (which skipped 33 still-broken cells forever) and not "is eligible"
    # (which requires a score that collection has not produced yet, so every fresh
    # cell would be re-collected on the next run).
    done = existing_usable(budget=args.budget)
    todo = [k for k in sorted(cells) if k not in done]

    if args.plan or not (args.run or args.compare):
        by_model = collections.Counter(k[0] for k in cells)
        empty = sum(1 for v in cells.values() if not (v.get("response_text") or "").strip())
        print("BUDGET-EXHAUSTED CELLS in %s" % os.path.basename(SOURCE.rstrip("/\\")))
        print("  (tokens_out >= %d, a completed call that returned no text, OR text that "
              "stops mid-clause at any token count)" % AT_CAP)
        for m, n in by_model.most_common():
            e = sum(1 for k, v in cells.items()
                    if k[0] == m and not (v.get("response_text") or "").strip())
            print("  %-30s %3d  (%d returned EMPTY)" % (m, n, e))
        print()
        rows = line_count()
        print("  total %d, of which %d empty; %d already re-collected, %d to do"
              % (len(cells), empty, len(done), len(todo)))
        if rows != len(done):
            print("  NOTE: %d rows on disk for %d cells -- %d duplicate(s) from concurrent "
                  "appends; the dict-keyed reader collapses them, a line count would not."
                  % (rows, len(done), rows - len(done)))
        print("  budget %d tokens, ~%.0f min at %.1fs delay"
              % (args.budget, len(todo) * (args.delay + 6) / 60.0, args.delay))
        return 0

    if args.compare:
        return compare(cells, done)

    import run_study as R
    key = R.load_env().get("OPENROUTER_API_KEY", "")
    if not key:
        print("no OPENROUTER_API_KEY", file=sys.stderr)
        return 1
    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)

    n = 0
    for (model, qid, cond) in todo:
        if args.limit and n >= args.limit:
            break
        old = cells[(model, qid, cond)]
        msgs = []
        if old.get("system_prompt"):
            msgs.append({"role": "system", "content": old["system_prompt"]})
        msgs.append({"role": "user", "content": old.get("user_prompt")
                     or old.get("question_text")})
        res = R.call_openrouter(model, msgs, key, max_tokens=args.budget)
        if res.get("transient"):
            print("  transport failure, not recorded: %s %s %s" % (model, qid, cond))
            continue
        rec = dict(old)
        rec.update({
            "response_text": res.get("response_text"),
            "tokens_out": res.get("tokens_out"),
            "tokens_in": res.get("tokens_in"),
            "ok": res.get("ok"),
            "latency_ms": res.get("latency_ms"),
            # CARRY THE DIAGNOSIS. call_openrouter returns a reason on failure --
            # "200 with no choices: ..." for a provider that accepts the request
            # and returns nothing -- and this dropped it, so 52 failed cells
            # across ernie-4.5 and gemini-2.0-flash-001 landed with error=None.
            # A failed call that cannot say why is a cell nobody can decide about:
            # deprecated endpoint, transient outage and quota exhaustion all look
            # identical, and only one of them is worth retrying.
            "error": res.get("error"),
            "transient": res.get("transient"),
            "max_tokens": args.budget,
            # PROVENANCE MUST DESCRIBE THIS CALL, NOT THE ONE IT REPLACES.
            #
            # `rec = dict(old)` copies the original record's fields, and two of them
            # then lied about the new one:
            #   called_at        still the May timestamp, so a record collected in
            #                    September claimed to have been called in May
            #   recollected_from hardcoded "2026-05-25", which is not even the run
            #                    being repaired -- that is 2026-05-25-full
            # A re-collected record that cannot say when it was collected or what it
            # replaced is one nobody can audit later, and the whole point of this run
            # is to be auditable.
            "called_at": _dt.datetime.now(_dt.timezone.utc)
                            .isoformat().replace("+00:00", "Z"),
            "original_called_at": old.get("called_at"),
            "recollected_from": os.path.basename(SOURCE.rstrip("/\\")),
            "recollect_reason": "original hit the %d-token cap" % 800,
            # The vendor id of the call this one replaces, so the pair can be walked.
            "replaces_vendor_response_id": old.get("vendor_response_id"),
            # On FAILURE this must be None, not the replaced call's id. Falling back
            # to `old` gave 52 failed cells a vendor_response_id belonging to a
            # different call made four months earlier -- a record that looks
            # traceable and traces to the wrong request.
            "vendor_response_id": (res.get("vendor_response_id")
                                   if res.get("ok") else None),
            # A copied score describes the OLD text. Cleared so nothing downstream
            # reads a stale judgement as though it applied to the new response.
            "score_classifier": None,
            "score_classifier_judges": None,
            "judge_reasoning": None,
            "scoring_status": "pending-rescore",
        })
        with io.open(os.path.join(OUT_DIR, safe(model) + ".jsonl"), "a",
                     encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        n += 1
        txt = (res.get("response_text") or "").strip()
        print("  %-28s %s %s  tokens %-5s chars %-6d%s"
              % (model, qid, cond, res.get("tokens_out"), len(txt),
                 "  WAS EMPTY" if not (old.get("response_text") or "").strip() else ""))
        time.sleep(args.delay)

    print()
    print("re-collected %d cell(s); %d remain" % (n, len(todo) - n))
    return 0


def compare(cells, done):
    """Paired: same cell, 800 tokens against the new budget."""
    rows = []
    for k, new in sorted(done.items()):
        old = cells.get(k)
        if not old:
            continue
        o = (old.get("response_text") or "").strip()
        v = (new.get("response_text") or "").strip()
        rows.append((k[0], k[1], k[2], len(o), len(v),
                     old.get("tokens_out"), new.get("tokens_out")))
    if not rows:
        print("nothing re-collected yet")
        return 1
    was_empty = [r for r in rows if r[3] == 0]
    print("PAIRED: the SAME cell at 800 tokens and at a real budget")
    print("  %d cell(s) compared, %d of which returned nothing at 800" % (len(rows), len(was_empty)))
    print()
    print("  %-28s %-9s %-4s %10s %10s" % ("model", "qid", "cond", "chars@800", "chars@new"))
    for m, q, c, lo, hi, to, tn in rows[:25]:
        print("  %-28s %-9s %-4s %10d %10d" % (m[:28], q, c, lo, hi))
    if len(rows) > 25:
        print("  ... and %d more" % (len(rows) - 25))
    grew = sum(1 for r in rows if r[4] > r[3])
    print()
    print("  %d of %d got LONGER once the cap was lifted" % (grew, len(rows)))
    print("  The originals are untouched in runs/2026-05-25/; these sit beside them.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
