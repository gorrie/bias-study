#!/usr/bin/env python3
"""Collect I3 Phase 4: the frozen panel against the authored mirrored bank.

THE SHAPE, and every part of it is pre-registered in
`PREREG-2026-09-14-i3-phase4.md` (amended 2026-09-15, before any call):

    31 models  x  4 conditions (N, A, P, D)  x  3 shuffle seeds (11, 22, 33)
    = 372 whole-sheet calls

`run_compass.py` is whole-sheet -- ONE CALL RETURNS ALL 32 ANSWERS -- which is
why this is a count of sheets and not the "5,760" the prereg body said before
the amendment. That figure counted item-answers.

(This said "all 60 answers" until 2026-09-17, carried over from the withdrawn
60-item bank. The live instrument is the author's 32-item Ratchet battery, and
the roster is 36 models, not the 31 the shape below still describes.)

WHY A DRIVER AND NOT A SHELL LOOP
---------------------------------
Three things have to hold across 372 invocations, and a loop that forgets any of
them collects a corpus that looks complete:

  * ONE MODEL PER SITTING. All 12 of a model's sheets go back-to-back. A
    contrast whose arms were collected two days apart manufactured two of five
    "significant" intervals in this project's own rung-2 work, and the fix was
    to stop splitting a model across days.
  * EVERY SAMPLE ITS OWN ORDER. `run_compass` defaults to id order, which puts
    each mirrored pair's halves adjacent -- the model can see a proposition and
    its negation at once and be consistent for free. The three samples are three
    SEEDS, not three draws at one order.
  * RESUMABLE WITHOUT DOUBLE-COUNTING. A wave that dies at model 19 must
    continue, not restart, and must not append a second copy of a cell it
    already holds. Cells already on disk are skipped by (model, condition,
    shuffle_seed).

    python scripts/run_i3_wave.py --plan     # what it would call, no API
    python scripts/run_i3_wave.py --run
"""
from __future__ import annotations

import argparse
import collections
import glob
import io
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)

RUN_DATE = "2026-09-16-ratchet-v3-wave"
ITEMS = "data/ratchet-battery.json"
CONDITIONS = ("N", "A", "P", "D")
SEEDS = (11, 22, 33)
TEMPERATURE = 0.7
BASE_SEED = 20260915

#: SIZED FROM THE WHOLE ROSTER, after 4,096 failed exactly the way this project
#: already documents.
#:
#: The first value here was 4,096, taken from a Phase 2 smoke whose longest sheet
#: used 2,184 tokens. That smoke was ONE model, and a non-reasoning one. A
#: reasoning model spends the budget on reasoning before it emits an answer, so
#: at 4,096 the wave produced:
#:
#:     deepseek     95.8% invalid, 23 of 24 sitting exactly at the cap
#:     moonshotai   72.2% invalid, 23 at the cap
#:     openai        7.7% invalid, 0 at the cap
#:     anthropic     8.3% invalid, 1 at the cap
#:
#: That is differential exclusion by vendor, 7.7% to 95.8% -- which is FINDINGS #7,
#: this study's own established result, reproduced on its own instrument by the
#: person who had just spent the day repairing the 800-token version of it. The
#: lesson was already written down in recollect_at_cap.py's docstring: 800 was not
#: a neutral default for a 2026 line-up, and neither is 4,096.
#:
#: 40,960 = 2x the roster's measured maximum, rounded up to a round number.
#:
#: MEASURED ON THIS INSTRUMENT AND THIS ROSTER, 2026-09-16: 36 models probed at a 65,536
#: ceiling, longest sheet **17,268 tokens**, so the minimum safe budget is 34,536.
#:
#: The value here was 32,768, carried over from a probe of the 60-item bank on 31 models --
#: and 32,768 is BELOW the 34,536 this roster needs. A shorter instrument did not make the
#: budget smaller, because the five models added to the roster are reasoning models that
#: spend the budget before they answer. The gate caught it: `--run` refused rather than
#: collecting 273 sheets under a cap two thousand tokens short of what the longest model
#: needs, which is how the 4,096 wave produced 95.8% invalid for one vendor against 7.7%
#: for another.
MAX_TOKENS = 40960


def panel(include_siblings=False):
    """The frozen panel, optionally plus the declared requantisation siblings.

    THE SIBLINGS ARE NOT THE PANEL. They are the second arm of a same-version null -- the same
    base weights at a different quantisation -- declared in `wave-panel.json` under
    `requant_siblings` with a date and a criterion, before collection, exactly as the
    same-version siblings were. They do not join the panel series and no panel-derived count
    includes them.

    WITHOUT THIS THERE IS NO PASS 4. `floor_quant` reads the wave directory and pairs through
    `check_arm_match.QUANT_PAIRS`, and NOTHING WROTE THOSE MODELS THERE: `--models` filters
    the panel and cannot add to it, and the old `run_quant_floor.sh` writes to a retired
    directory, at temperature 0, with no `--shuffle-seed` at all -- which on a mirrored
    instrument presents every pair adjacent, the one arrangement the bank exists to avoid.
    """
    with io.open(os.path.join(STUDY, "data", "wave-panel.json"), encoding="utf-8") as fh:
        payload = json.load(fh)
    models = list(payload["models"])
    if include_siblings:
        for m in payload.get("requant_siblings") or []:
            if m not in models:
                models.append(m)
    return models


def is_local(model):
    """Local ids have no vendor prefix, or are a pulled GGUF repo."""
    return "/" not in model or model.startswith("hf.co")


def safe(name):
    return "".join(c if c.isalnum() or c in "-._" else "_" for c in name)


def _served_provider(out_date, model, cond=None):
    """Which backend actually served this cell's most recent sheet, or None.

    Read from the record rather than from the request, because the request did not
    name one -- the first sheet of a cell is collected unpinned and the router
    decides. Every later sheet in that cell is then held to whatever came back, so
    the study fixes a backend without choosing one.

    Returns None on the local channel (no routing) and when the field is absent, and
    the caller simply does not pin. A missing provider must not become a pin of
    `None`, which `run_compass --provider` would reject as a literal backend name.

    MATCH ON THE RECORD, NOT ON A FILENAME. The first version built the path from this
    module's `safe()`, which maps `z-ai/glm-5.3` to `z-ai_glm-5.3` while run_compass's
    own `safe_filename` writes `z-ai__glm-5.3`. Two functions for one fact, and the
    helper silently found nothing and pinned nothing -- a second copy of a naming rule
    behaving exactly like the second copies of numbers this study keeps correcting.
    `done_cells` already reads the records rather than the names; so does this.
    """
    out_dir = os.path.join(STUDY, "runs", out_date)
    served = None
    for path in sorted(glob.glob(os.path.join(out_dir, "*.jsonl"))):
        for line in io.open(path, encoding="utf-8", errors="replace"):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get("model") != model or not rec.get("provider"):
                continue
            # `cond=None` asks "which backend has served this MODEL at all", which is the
            # question a per-model pin actually has. Passing a condition is kept for callers
            # that want one arm's backend.
            if cond is not None and rec.get("condition") != cond:
                continue
            served = rec["provider"]
    return served


#: Failures worth another call, and the cap on how many.
#:
#: A CELL IS NOT DONE BECAUSE SOMETHING LANDED IN IT. This counted any record as collected,
#: valid or not, so the prereg's own rule -- "a run that does not yield exactly N clean
#: answers is discarded whole and rerun" -- was executed by nothing. `gemma-4-12B` sits at
#: 8 invalid of 12 and would have entered the order floor on four sheets.
#:
#: A REFUSAL IS NOT RETRIED. It is a measurement, and this study reports refusal rates; a
#: retry loop over refusals would manufacture answers from models that declined. Only
#: mechanical failures are re-rolled.
RETRYABLE = ("other", "truncated", "budget-exhausted", "transport")
RETRY_CAP = 2


def probe_max():
    """Longest VALID probe sheet across the roster, or 0 when the probe has not run.

    VALID only: six of the thirty-six probe records are refusals, 160 to 214 tokens, and a
    refusal is not a measurement of how long a 32-answer sheet is. The docstring above
    MAX_TOKENS said "2x the roster's measured maximum" while the value is 2.37x of 17,268 --
    a stated rule that did not match the number beside it. Derive it and the two cannot
    disagree.
    """
    probe = os.path.join(STUDY, "runs", RUN_DATE + "-budget-probe")
    if not os.path.isdir(probe):
        return 0
    longest = 0
    for p in sorted(glob.glob(os.path.join(probe, "*.jsonl"))):
        for line in io.open(p, encoding="utf-8", errors="replace"):
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("valid"):
                longest = max(longest, r.get("tokens_out") or 0)
    return longest


def valid_counts(out_dir):
    """{(model, condition, shuffle_seed): VALID records on disk}.

    What `run_compass --runs K` measures a cell against, so `--plan` can report the sheets a
    replicate pass will actually write instead of assuming every cell starts empty.
    """
    seen = collections.Counter()
    for p in sorted(glob.glob(os.path.join(out_dir, "*.jsonl"))):
        for line in io.open(p, encoding="utf-8", errors="replace"):
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("valid"):
                seen[(r.get("model"), r.get("condition"), r.get("shuffle_seed"))] += 1
    return seen


def done_cells(out_dir, retry_failures=True):
    """(model, condition, shuffle_seed) already collected.

    A cell counts as done when it holds a VALID sheet, a refusal, or has been attempted
    `RETRY_CAP` times. Anything else is left for another call.
    """
    attempts = collections.Counter()
    good = set()
    for p in glob.glob(os.path.join(out_dir, "*.jsonl")):
        for line in io.open(p, encoding="utf-8", errors="replace"):
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            key = (r.get("model"), r.get("condition"), r.get("shuffle_seed"))
            attempts[key] += 1
            if not retry_failures:
                good.add(key)
                continue
            if r.get("valid") or (r.get("failure_mode") or "") not in RETRYABLE:
                good.add(key)
    if retry_failures:
        good |= {k for k, n in attempts.items() if n >= RETRY_CAP}
    return good


def budget_precondition(models):
    """Refuse to collect until the budget is MEASURED across the whole roster.

    THIS EXISTS BECAUSE THE INSTRUCTION WAS NOT ENOUGH.
    ---------------------------------------------------
    The I3 plan's Phase 2 gate says the measured output length sets the budget,
    and the design review attached a per-model probe to it in as many words:
    "one model tells you nothing about the other seven ... set the token budget
    from the LONGEST model's output, not the smoke model's."

    It was read, and then not done. A one-model smoke set the cap at 4,096, 372
    sheets were launched on it, and 231 landed at 95.8% invalid for deepseek and
    7.7% for openai -- differential exclusion by vendor, which is this study's own
    FINDINGS #7, reproduced on its own instrument hours after the 800-token
    version of it had been repaired.

    The defect was not ignorance. The lesson was written in three places. The
    defect is that a gate living in prose is checked by whoever remembers it, and
    the execution path checked nothing. This project's answer to that everywhere
    else is an executable gate in front of the spend, so it fails closed:
    collection_check before scoring calls, key_numbers --check before a claim
    ships. This is the same thing in front of a collection.

    Returns a list of reasons to refuse. Empty means go.
    """
    # THE PROBE DIR AND ITS INSTRUMENT, both derived. This named a literal directory that
    # held 60-item sheets of the withdrawn bank; moving that directory back would have
    # satisfied this gate silently, which is the modal-noise defect in a second place.
    probe = os.path.join(STUDY, "runs", RUN_DATE + "-budget-probe")
    if not os.path.isdir(probe):
        return ["no budget probe on disk. Run: python scripts/probe_budget.py --run"]

    seen, lengths, at_ceiling = {}, [], []
    for p in glob.glob(os.path.join(probe, "*.jsonl")):
        for line in io.open(p, encoding="utf-8"):
            if not line.strip():
                continue
            r = json.loads(line)
            t = r.get("tokens_out") or 0
            seen[r["model"]] = t
            lengths.append(t)
            if t >= 65536 - 10:
                at_ceiling.append(r["model"])

    reasons = []
    missing = [m for m in models if m not in seen]
    if missing:
        reasons.append("%d roster model(s) never probed: %s"
                       % (len(missing), ", ".join(sorted(missing)[:6])))
    if at_ceiling:
        reasons.append("%d model(s) hit the probe ceiling, so their length is a floor "
                       "not a measurement: %s" % (len(at_ceiling), ", ".join(at_ceiling)))
    if lengths:
        need = 2 * max(lengths)
        if MAX_TOKENS < need:
            reasons.append("MAX_TOKENS is %d; the roster's longest sheet is %d, so the "
                           "budget must be at least %d" % (MAX_TOKENS, max(lengths), need))
    return reasons


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--plan", action="store_true", help="what would be called; no API")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--out-date", default=RUN_DATE)
    ap.add_argument("--models", default="", help="comma-separated filter")
    ap.add_argument("--delay", type=float, default=1.0)
    #: THE REPLICATE PASS, which had no way to be issued.
    #:
    #: done_cells skips any (model, condition, shuffle_seed) already on disk, so "two more
    #: runs at seed 11" through this driver collected ZERO sheets. The plan budgeted 124
    #: sheets for a replicate floor that the driver could not produce and the floor arm could
    #: not have read.
    #:
    #: A replicate holds the ORDER fixed and varies only the draw, so this sweeps the
    #: SAMPLING seed at one shuffle seed. Without --seed-sweep run_compass reuses the same
    #: sampling seed on every run, and on seed-honouring backends the repeats come back
    #: near-identical -- a replicate floor of ~0, which is worse than not measuring it.
    #: K IS THE CELL'S TOTAL, NOT AN INCREMENT. `run_compass --runs K` counts the valid
    #: records already in the cell and collects `K - have`, so `--replicate 4` on a cell that
    #: already holds one wave sheet collects THREE. The help here said "K extra runs" and the
    #: prereg says "four extra runs on D ... five runs at one order is what makes
    #: floor_modal_noise computable" -- three documents, two meanings, and `--plan` printed
    #: 144 for a pass that would have written about 108.
    #:
    #: Settled as TOTAL, because that is what the code does and what the floor needs: the
    #: modal-noise arm requires >= 4 valid sheets in a cell, so the number that matters is
    #: how many the cell ENDS with. Use 5 -- the prereg's figure, and one failure of headroom
    #: above the >= 4 rule, which matters because a single refusal or format failure in the
    #: cell otherwise drops that model out of the floor entirely.
    ap.add_argument("--replicate", type=int, default=0, metavar="K",
                    help="collect until each cell holds K runs TOTAL at a fixed item order, "
                         "sweeping the sampling seed. Measures run-to-run, not order. The "
                         "prereg's pass 2 is K=5.")
    ap.add_argument("--replicate-seed", type=int, default=SEEDS[0],
                    help="the shuffle seed held fixed during a replicate pass")
    ap.add_argument("--conditions", default=",".join(CONDITIONS),
                    help="comma-separated conditions to collect")
    ap.add_argument("--siblings", action="store_true",
                    help="include the declared requantisation siblings from wave-panel.json "
                         "(pass 4). Local builds only, so the pass costs time and no money. "
                         "They are a same-version null's second arm, not panel members.")
    args = ap.parse_args(argv)

    out_dir = os.path.join(STUDY, "runs", args.out_date)
    models = panel(include_siblings=args.siblings)
    if args.models:
        want = {m.strip() for m in args.models.split(",")}
        models = [m for m in models if m in want]

    os.makedirs(out_dir, exist_ok=True)
    have = done_cells(out_dir)
    # WHAT --run WOULD ACTUALLY DO, not the default shape. This computed against CONDITIONS
    # and SEEDS regardless of --conditions and --replicate, so a replicate pass printed the
    # full-wave plan -- "12 sheets, conditions N A P D" for a run that would collect 4. A
    # plan that does not describe the run it precedes is worse than no plan.
    plan_conds = [c.strip() for c in args.conditions.split(",") if c.strip()]
    if args.replicate:
        plan_seeds = [args.replicate_seed]
        per_cell = args.replicate
        todo = [(m, c, args.replicate_seed) for m in models for c in plan_conds]
    else:
        plan_seeds = list(SEEDS)
        per_cell = 1
        todo = [(m, c, s) for m in models for c in plan_conds for s in plan_seeds
                if (m, c, s) not in have]

    if args.plan or not args.run:
        print("I3 PHASE 4 -- %s%s" % (args.out_date,
                                      "  [REPLICATE x%d]" % args.replicate if args.replicate
                                      else ""))
        print("  models      %d (%d local, %d hosted)"
              % (len(models), sum(1 for m in models if is_local(m)),
                 sum(1 for m in models if not is_local(m))))
        print("  conditions  %s" % ", ".join(plan_conds))
        print("  seeds       %s" % ", ".join(str(s) for s in plan_seeds))
        # THE SHEETS THIS RUN WILL ACTUALLY WRITE. `len(todo) * per_cell` assumed every cell
        # starts empty, so a replicate pass over cells that already hold a wave sheet
        # over-reported by one sheet per cell -- 144 printed for about 108 written. K is the
        # cell's TOTAL, so the new sheets are K minus what is valid there now.
        if args.replicate:
            _valid = valid_counts(out_dir)
            to_write = sum(max(0, args.replicate - _valid.get(cell, 0)) for cell in todo)
            print("  sheets      %d to collect across %d cell(s) -- each cell taken to %d "
                  "run(s) total" % (to_write, len(todo), args.replicate))
        else:
            to_write = len(todo) * per_cell
            print("  sheets      %d to collect (%d already on disk)" % (to_write, len(have)))
        _pmax = probe_max()
        print("  max_tokens  %d (%s, probe_budget.py)"
              % (MAX_TOKENS,
                 ("%.2fx the roster's measured maximum of %d" % (MAX_TOKENS / _pmax, _pmax))
                 if _pmax else "roster maximum not measured"))
        # GATE STATUS IN THE PLAN. --plan returned before both preconditions, so it reported
        # a collection that --run then refused, and the operator learned that only by running.
        try:
            import check_instrument_approved as _A
            ok, _ = _A.audit(os.path.join(STUDY, ITEMS))
            print("  instrument  %s" % ("APPROVED" if ok else "NOT APPROVED -- --run refuses"))
        except ImportError:
            print("  instrument  UNKNOWN -- approval gate not importable")
        refusals = budget_precondition(models)
        print("  budget      %s" % ("measured" if not refusals
                                    else "NOT MEASURED -- --run refuses: " + refusals[0][:60]))
        return 0

    # THE INSTRUMENT MUST BE ONE THE AUTHOR HAS READ AND SIGNED.
    #
    # On 2026-09-14 a bank written by an assistant session became the study's instrument.
    # `render_item_read.py` produced its sign-off sheet, every box was left empty, and 372
    # sheets were collected against it anyway -- while the author's own battery had zero
    # records. The renderer existed; nothing read the checklist back, so the gate was a
    # document. This reads it back, in front of the spend.
    try:
        import check_instrument_approved as _A
        _ok, _findings = _A.audit(os.path.join(STUDY, ITEMS))
        if _ok is False:
            print("REFUSING TO COLLECT -- the instrument is not approved.")
            for f in _findings:
                print("  * %s" % f)
            print("")
            print("A bank is collectable when its author has read every pair and said so.")
            print("Render the sheet, read it, tick the boxes:")
            print("  python scripts/render_item_read.py --items %s > ITEM-READ-<date>-<name>.md"
                  % ITEMS)
            return 2
    except ImportError as exc:
        # FAIL CLOSED. This was : if the approval module could not be imported the
        # spend proceeded against an unapproved instrument, which is the failure this gate
        # exists to prevent, reachable by a typo in an import.
        print("REFUSING TO COLLECT -- the approval gate could not be loaded: %s" % exc)
        return 2

    # THE PRECONDITION, in front of the spend. Never a warning: a wave collected
    # at an unmeasured budget is not cheaper to discard than it was to collect.
    refuse = budget_precondition(models)
    if refuse:
        print("REFUSING TO COLLECT -- the budget is not measured across this roster.")
        for r in refuse:
            print("  * %s" % r)
        print("")
        print("This is the gate the plan asked for and the last wave did not have:")
        print("372 sheets were launched on a cap taken from ONE non-reasoning model,")
        print("and deepseek came back 95.8% invalid against openai's 7.7%.")
        print("")
        print("NOTE: --models narrows this check to the models you named. That is")
        print("deliberate for a scoped re-collection and is also the way past this")
        print("gate, so do not reach for it to make this message go away.")
        print("Run: python scripts/probe_budget.py --run")
        return 2

    # THE REGISTRY, ACTUALLY EXECUTED. `gates.py` has carried a `prerun` stage since it was
    # written and NOTHING RAN IT: `release_check.py` was its only importer and it runs the
    # release stage. This function hand-wired the two gates above -- each added the day after
    # the defect it catches -- and the other eight sat in the registry, named, described, and
    # never called in front of a spend. Two collection passes ran with three of them red,
    # including the leak gate that guards the public repository.
    #
    # `gates.py` itself claimed "this is what run_i3_wave --run calls before it spends
    # anything", which was false when it was written. An independent review found it. This is
    # the line that makes the sentence true.
    try:
        import gates as _G
        _failed = _G.preflight("prerun")
    except ImportError as exc:
        # FAIL CLOSED, for the same reason the approval gate does.
        print("REFUSING TO COLLECT -- the gate registry could not be loaded: %s" % exc)
        return 2
    if _failed:
        print("")
        print("REFUSING TO COLLECT -- %d pre-collection gate(s) failed." % len(_failed))
        for g, rc, line in _failed:
            print("  * %s (exit %d): %s" % (g.label, rc, line[:100]))
        print("")
        print("These are the questions that must be answered BEFORE money is spent, not")
        print("after the corpus is on disk. Fix them or move the gate out of `prerun` with")
        print("a reason -- do not route around this.")
        return 2

    started = time.time()
    n_ok = n_fail = 0
    _ = _served_provider  # named here so a refactor cannot drop the helper silently
    # Grouped by model so a model's twelve sheets are contiguous in time.
    for model in models:
        conds = [c.strip() for c in args.conditions.split(",") if c.strip()]
        if args.replicate:
            # A REPLICATE PASS RE-VISITS CELLS THAT ARE ALREADY ON DISK. That is the whole
            # point of it, and it is why `have` cannot gate here: the ordinary resume logic
            # would skip every one of them and collect nothing.
            cells = [(c, args.replicate_seed) for c in conds]
        else:
            cells = [(c, s) for c in conds for s in SEEDS if (model, c, s) not in have]
        if not cells:
            continue
        print("=== %s  (%d sheet(s))" % (model, len(cells)), flush=True)
        # ONE BACKEND PER CELL, decided by the cell's first sheet and held for the rest.
        #
        # The 2026-09-16 wave returned 36 cells whose three replicates were served by
        # different providers -- worst, deepseek-v4-flash-0731/A across OpenInference,
        # Relace and Sail Research. Replicates in a cell are supposed to differ by the
        # draw and nothing else. Serving path is one of the same-version variants this
        # study MEASURES, so a cell straddling two backends confounds the condition
        # contrast with the routing, and collection_check refuses the run for it.
        #
        # The pin is not chosen in advance: it is whatever served sheet 1, so the study
        # is not picking backends, only holding one fixed within a cell. `run_compass
        # --provider` sends allow_fallbacks=False, so a pin that cannot be honoured
        # FAILS the sheet instead of quietly routing elsewhere and recording the
        # substitute -- which is the behaviour this replaces.
        # ONE BACKEND PER MODEL, not per condition. This was keyed by condition, so a
        # model's four arms could each sit on a different backend -- verified in the 167
        # sheets: deepseek-v4-flash answered A on Reka, D on Together, N on CoreWeave and
        # P on OpenInference. The A->D contrast for that model is then Reka against
        # Together, and serving path is a same-version variant this study MEASURES. The
        # per-cell check in collection_check passed it, because per-cell was the scope.
        # SEEDED FROM DISK BEFORE THE FIRST CALL, not learned after it.
        #
        # This was `pinned = None`, learned from the first sheet this invocation returned.
        # That works for a fresh model with twelve cells. It DOES NOT WORK FOR A REPLICATE
        # PASS: replicate mode builds exactly one cell per model, so the pin is learned from
        # a sheet that has already been sent, and every replicate goes out unpinned in a
        # single `run_compass --runs K` call. The router is then free to serve the repeats
        # from a different backend than the wave sheets they are measured against -- and
        # serving path is a same-version variant this study MEASURES, so the replicate floor,
        # the floor under every other floor, would be confounded with routing. That is
        # precisely the defect pass 3 was run to undo.
        #
        # The model's existing sheets already name the backend that served them. Read it.
        pinned = None if is_local(model) else _served_provider(args.out_date, model)
        if pinned:
            print("    pinned to %s from this model's existing sheets" % pinned, flush=True)
        for cond, seed in cells:
            cmd = [sys.executable, os.path.join(HERE, "run_compass.py"),
                   "--model", model, "--items", ITEMS, "--condition", cond,
                   "--runs", str(args.replicate or 1), "--shuffle-seed", str(seed),
                   "--temperature", str(TEMPERATURE), "--seed", str(BASE_SEED + seed),
                   "--max-tokens", str(MAX_TOKENS), "--out", os.path.join("runs", args.out_date)]
            if args.replicate:
                # SWEEP THE SAMPLING SEED, or the repeats are not repeats. Without this
                # run_compass reuses one seed for every run in the call, and a backend that
                # honours seeds returns near-identical sheets -- a replicate floor of ~0,
                # which understates the floor under every other floor in the table.
                cmd += ["--seed-sweep"]
            if is_local(model):
                cmd += ["--channel", "ollama", "--no-think"]
            elif pinned:
                cmd += ["--provider", pinned]
            r = subprocess.run(cmd, cwd=STUDY, capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
            tail = [l for l in (r.stdout or "").splitlines() if "runs valid" in l]
            # LEARN THE PIN FROM ANY SHEET THAT RECORDED A BACKEND, not only a valid one.
            #
            # This sat inside the success branch, so a model whose first sheet was refused
            # or malformed learned no pin -- and every later sheet went out unpinned. That
            # is how `glm-5.1` came back on two backends AFTER the per-model pin landed: its
            # opening sheet failed, nothing was learned, and the router chose freely.
            #
            # A refusal still names the backend that refused, which is exactly the fact
            # needed to hold the rest of the model to it.
            if not is_local(model) and not pinned:
                served = _served_provider(args.out_date, model, cond)
                if served:
                    pinned = served
                    print("    pinned to %s for all of this model's sheets"
                          % served, flush=True)
            if r.returncode == 0 and tail:
                n_ok += 1
                print("    %s seed %-3s %s" % (cond, seed, tail[-1].split(": ")[-1]), flush=True)
            else:
                n_fail += 1
                err = ((r.stderr or r.stdout or "").strip().splitlines() or ["?"])[-1]
                print("    %s seed %-3s FAILED  %s" % (cond, seed, err[:110]), flush=True)
            time.sleep(args.delay)

    print("")
    print("collected %d sheet(s), %d failed, in %.1f min"
          % (n_ok, n_fail, (time.time() - started) / 60.0))
    print("NOW RUN:  python scripts/collection_check.py %s" % args.out_date)
    return 0


if __name__ == "__main__":
    sys.exit(main())
