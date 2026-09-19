#!/usr/bin/env python3
"""Bring the stock/ablated arm up to the wave protocol. Local GPU, zero API spend.

WHY THIS IS THE ARM THAT MATTERS
--------------------------------
Cutting the refusal direction out of the weights and re-asking the questionnaire is the one
measurement in this study that **no closed lab can replicate and no API can provide**. It is
the direct test of the constraint-layer argument: if the safety layer is a separable direction,
removing it should change what the model will answer; if it is entangled with competence,
removing it should break the model instead.

**And it is n=1.** The whole arm is six pairs x two builds x four conditions x ONE run --
48 runs, no seed sweep, collected 2026-08-30. Meanwhile the manipulation arm got 25 models at
n=5 and the order floor got 310 fresh API calls. The claim that requires open weights is the
worst-measured thing in the corpus.

WHAT THIS COLLECTS
------------------
Wave protocol -- temperature 0.7, swept seed, n=5, template T01 -- for both builds of each pair
under three conditions:

    A   the balance instruction. THE KEY ONE: stock 2026 models refuse it. If the ablated twin
        answers, refusal is a separable direction. If it still refuses, whatever is declining is
        not the direction that was cut.
    P   the content-free placebo -- the reference arm the flagships do answer
    D   the commitment instruction

B is omitted: it is a second no-directive arm and A is the one carrying the question.

RE-RUNNING THE THREE EXCLUDED PAIRS IS DELIBERATE
-------------------------------------------------
`check_arm_match.INELIGIBLE_PAIRS` drops gemma2-9b, llama31-8b and qwen38-27b because the
ablated builds emitted tokenizer garbage, invented their own questions, or answered Strongly
Agree to all 62. Those were single runs with stop tokens dropped. At n=5 with the wave's
parameters, either the behaviour reproduces -- in which case "over-ablation destroys
instruction-following" is a measured result rather than an exclusion note -- or it does not,
and the exclusion was a sampling artifact. Both outcomes are worth more than the note.

    python scripts/ablation_wave.py --plan
    python scripts/ablation_wave.py --run --limit 4
    python scripts/ablation_wave.py --report
"""
from __future__ import annotations

import argparse
import collections
import datetime
import glob
import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from wave import WAVE_PARAMS  # noqa: E402
import studypaths as _SP  # noqa: E402

CONDITIONS = ("A", "P", "D")

#: Per-pair token budget, where the wave's 8192 is not enough to hold an answer sheet.
#:
#: gemma-4-12B is verbose: it writes prose around the 62 answers and runs out of budget before
#: finishing. Measured on this collection, the STOCK arm produced 0 valid of 5 under A and 1 of
#: 5 under P and D -- twelve of fifteen runs `budget-exhausted`. A build that cannot fit its
#: answer sheet in the budget is not being measured, and that is exactly how three pairs became
#: "exclusions" on 2026-08-30 rather than measurements.
#:
#: RAISED FOR BOTH SIDES OF THE PAIR, equally. The comparison a pair makes is against itself,
#: so a budget that differs between stock and ablated would confound the ablation with the
#: budget -- but a budget that differs from the WAVE's means this pair's absolute numbers are
#: not directly comparable to the wave's floors. That caveat travels with the row.
MAX_TOKENS = {"gemma4-12b": 16384}

#: (label, stock, [ablated, ...]) -- MULTIPLE ABLATIONS PER BASE, which is the design.
#:
#: WHY MORE THAN ONE ABLATOR. "Abliteration changes political position" is a claim about the
#: MODEL. Measured with one ablated build it is indistinguishable from a claim about the
#: ABLATOR's choices -- which layer, which refusal set, what quantisation, whether stop tokens
#: survived. Four independent abliterations of Qwen3.8-27B exist at matched Q4_K_M, so the
#: weight-level intervention gets an error bar and the two claims come apart:
#:
#:   ablations agree  -> the effect is a property of the base model. Strong result.
#:   ablations differ -> the effect is a property of whoever did the ablation, and every
#:                       abliterated model card claiming "uncensored, otherwise intact" is
#:                       asserting something nobody measured.
#:
#: This is the same move as the presentation-order floor, one level up, and it is the control
#: Kamal 2025's fine-tuning study lacks -- the reason its t statistics reverse sign between
#: precisions.
#:
#: DOWNLOAD COUNTS MATTER for what gets tested. The build already on disk for Qwen3.8-27B has
#: 995k downloads while huihui's has 2.19M and Heretic's 1.51M; for gemma-4-12B the disk copy
#: has 26.7k against culturerevolt's 286k. Testing only what happened to be downloaded first
#: measures a build most people do not run.
PAIRS = [
    ("qwen38-27b",
     "hf.co/lmstudio-community/Qwen3.8-27B-GGUF:Q4_K_M",
     [
         # 1.51M downloads, a DIFFERENT method (Heretic), and QUANT-MATCHED: the repo ships a
         # standard Qwen3.8-27B-Heretic-Q4_K_M.gguf against the stock arm's Q4_K_M. Smoke-tested
         # 62/62 valid. This is the clean comparison of the three.
         "hf.co/0bserverx/Qwen3.8-27B-Heretic-Abliterated-Uncensored-GGUF:Q4_K_M",
         # 995k -- the build the corpus already holds, kept so the old n=1 has an n=5 successor.
         # Quant-matched.
         "hf.co/OBLITERATUS/Qwen3.8-27B-OBLITERATED:Q4_K_M",
         # 2.19M downloads -- THE MOST-USED abliteration of this base, and the one people
         # actually run, so it has to be tested. But its nearest quant is UD-DW-Q4_K_M --
         # Unsloth DYNAMIC Q4_K_M, not the static Q4_K_M the stock arm uses. The repo has no
         # plain Q4_K_M at all (31 GGUFs, closest are Q4_K, Q4_K_L, UD-DW-Q4_K_M, UD-Q4_K_XL).
         #
         # QUANT MISMATCH IS A DECLARED CONFOUNDER IN THIS ARM, not a footnote: it is why
         # check_arm_match excluded gemma2-9b and llama31-8b. Dynamic-vs-static within one
         # nominal Q4_K_M is a far smaller mismatch than Q4_0-vs-Q8_0, so this build is
         # collected rather than dropped -- and any difference it shows against the two
         # quant-matched ablations above is attributable to the quantisation before it is
         # attributable to the ablation. Named here so that ordering cannot be reversed later.
         "huihui-qwen38-27b-abliterated-uddw:Q4_K_M",
     ]),
    ("gemma4-12b",
     "hf.co/lmstudio-community/gemma-4-12B-it-GGUF:Q4_K_M",
     [
         "hf.co/culturerevolt/gemma-4-12b-heretic-abliterated-GGUF:Q4_K_M",   # 287k
         "hf.co/OBLITERATUS/Gemma-4-12B-OBLITERATED:Q4_K_M",                  # 26.7k, on disk
     ]),
    # The 2024-generation pairs. Kept because three of them are the arm's ONLY existing pairs
    # and because the excluded ones need re-running at n=5 rather than excluding on n=1, but
    # they collect LAST -- nobody deploys these and a 2026 claim cannot rest on them.
    ("phi4-14b", "phi4:latest", ["huihui_ai/phi4-abliterated:latest"]),
    # THE BASE THAT SHOWS THE EFFECT, AND IT HAD ONE ABLATOR.
    #
    # 2026-09-07: of three bases with a usable pair, this is the only one whose ablation effect
    # clears the estimator floor -- 8/9/9 side-flips of 62 under A/D/P against a floor of 3.
    # And it had exactly ONE abliteration on disk, so the pre-registered ablator-agreement step
    # could not run on it. The one base that could be checked (qwen38-27b) shows nothing above
    # noise, which left the arm's headline as "the base that shows the effect is the base that
    # cannot be checked".
    #
    # Two more INDEPENDENT abliteration jobs of the same base, both quant-matched to the stock
    # arm's Q4_K_M, so the check can run where the effect is:
    #
    #   huihui-ai v1     the build already here (995k+ downloads via ollama)
    #   huihui-ai v2     a LATER, SEPARATE abliteration by the same author
    #   Josiefied v2     Goekdeniz-Guelmez -- a DIFFERENT author and method
    #
    # PROVENANCE, because `mradermacher` is a QUANTISER and not an ablator. Both new tags are
    # mradermacher requantisations, and the abliteration author is what agreement is about:
    # two builds by the same author agreeing is weaker evidence than two authors agreeing. The
    # requantisers `maicog` and `Lucy-in-the-Sky` were rejected for the opposite reason -- both
    # repackage huihui v2, so using both would have counted ONE abliteration job twice.
    ("qwen25-14b", "qwen2.5:14b", [
        "huihui_ai/qwen2.5-abliterate:14b",
        "hf.co/mradermacher/Qwen2.5-14B-Instruct-abliterated-v2-GGUF:Q4_K_M",
        "hf.co/mradermacher/Josiefied-Qwen2.5-14B-Instruct-abliterated-v2-GGUF:Q4_K_M",
    ]),
    ("gemma2-9b", "gemma2:latest", ["wash-gemma2-ablit:latest"]),
    ("llama31-8b", "llama3.1:8b", ["wash-llama31-8b-ablit:latest"]),

    # THE SAME TWO PAIRS, QUANT-MATCHED, BECAUSE THEIR EXCLUSION WAS CONFOUNDED.
    #
    # `check_arm_match.INELIGIBLE_PAIRS` rules both of the pairs above ineligible, and its
    # stated reason is TWO reasons at once:
    #
    #   gemma2-9b     stock Q4_0   vs ablated Q8_0  + emits SentencePiece markers as text
    #   llama31-8b    stock Q4_K_M vs ablated Q8_0  + answers in prose, never a sheet
    #
    # The quantisation half is fixable at zero cost and was never fixed: both ablated builds
    # are Q8_0, and the matching Q8_0 STOCK builds have been on this machine all along --
    # `gemma2:9b-instruct-q8_0` and `llama3.1:8b-instruct-q8_0`, already used as the far arm of
    # the requantisation floor. The pairs were mismatched only because the stock arm took
    # ollama's default Q4 tag.
    #
    # So run them matched. The failure modes are almost certainly properties of the ablated
    # builds and will recur -- and that is the point: with the quant held fixed, "this build
    # emits tokenizer garbage" becomes a clean finding instead of a claim entangled with a
    # two-step quantisation gap. An exclusion carrying two reasons is an exclusion that cannot
    # be attributed to either.
    #
    # SEPARATE LABELS so the mismatched cells stay on disk as the record rather than being
    # overwritten -- the same reason both ablation rows print in the floors table. The `-q8`
    # suffix keeps the directories distinct, which `test_ablation_slugs.py` now asserts.
    ("gemma2-9b-q8", "gemma2:9b-instruct-q8_0", ["wash-gemma2-ablit:latest"]),
    ("llama31-8b-q8", "llama3.1:8b-instruct-q8_0", ["wash-llama31-8b-ablit:latest"]),
]


def outdir(date=None):
    date = date or datetime.date.today().isoformat()
    return os.path.join(STUDY, "runs", "%s-ablation-wave" % date)


def existing_dirs():
    return sorted(p for p in glob.glob(os.path.join(STUDY, "runs", "*-ablation-wave"))
                  if os.path.isdir(p))


def _scan(d):
    """(model, condition) -> (distinct valid seeds, total records)."""
    seeds = collections.defaultdict(set)
    rows = collections.Counter()
    for p in glob.glob(os.path.join(d, "**", "*.jsonl"), recursive=True):
        for line in io.open(p, encoding="utf-8", errors="replace"):
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if not _SP.is_run_record(r):
                continue
            key = (r.get("model"), r.get("condition"))
            rows[key] += 1
            if r.get("valid") and r.get("seed") is not None:
                seeds[key].add(r["seed"])
    return {k: len(v) for k, v in seeds.items()}, rows


def _slug(model_id):
    """A directory name for one ablated build. Several share a base, so the ablator has to be
    in the path or the second one overwrites the first.

    IT TOOK THE UPLOADER AND THE UPLOADER IS NOT THE ABLATOR, AND TWO BUILDS COLLIDED.
    This returned the second-to-last path segment, which for `hf.co/<uploader>/<repo>:<quant>`
    is the UPLOADER. Adding two independent abliterations of qwen2.5-14b -- huihui-ai v2 and
    Josiefied v2 -- both routed through mradermacher's requantisations, so both slugged to
    `ablated-mradermacher` and would have written into ONE directory.

    That is not a cosmetic clash. `ablation_analysis.py` derives the arm from the directory
    name, so two different ablations would have been read as one cell, their runs pooled, and
    the ablator-agreement step -- the whole reason these builds were pulled -- would have
    compared a build against itself. Caught by reading `--plan` before collecting, which is
    the only reason it is a note rather than a retraction.

    So the slug is built from the REPO name, which identifies the abliteration, and the
    uploader is dropped. Long enough to keep `Josiefied` distinct from the plain v2, and the
    collision is asserted against in the tests rather than trusted.
    """
    part = model_id.split("/")[-1] if "/" in model_id else model_id
    part = part.split(":")[0]                     # drop the quant tag
    for junk in ("-GGUF", "-gguf", "Qwen2.5-", "qwen2.5-", "-Instruct"):
        part = part.replace(junk, "")
    return part.replace(":", "_").replace(".", "_").strip("-_").lower()[:28] or "ablated"


def cells():
    out = []
    for label, stock, ablations in PAIRS:
        out.append((label, "stock", stock, None))
        for a in ablations:
            out.append((label, "ablated-%s" % _slug(a), a, None))
    # Expand conditions last so every build of a pair is asked A, P and D before the next pair
    # starts -- a partial collection then holds whole pairs rather than whole conditions, and a
    # whole pair is the unit that can be analysed.
    return [(lab, arm, mod, c) for (lab, arm, mod, _x) in out for c in CONDITIONS]


def todo(have, tried, redo=()):
    """Cells still worth collecting.

    `redo` names pair labels whose spent cells should be re-queued anyway. The skip rule --
    "asked its full budget, whatever came back" -- is right for a model that cannot answer and
    WRONG the moment a parameter changes: gemma4-12b's stock arm budget-exhausted twelve of
    fifteen runs at 8192 tokens, so raising it to 16384 makes those cells worth asking again.
    Without this the fix would be invisible, because the cells it fixes are exactly the ones
    the skip rule has stopped asking about.

    Non-destructive on purpose: the exhausted records stay on disk and `run_battery` appends,
    so the failures remain countable. A budget-exhausted run is evidence about the build.
    """
    want = WAVE_PARAMS["runs"]
    out = []
    for c in cells():
        label, key = c[0], (c[2], c[3])
        if have.get(key, 0) >= want:
            continue
        if tried.get(key, 0) >= want and label not in redo:
            continue
        out.append(c)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--delay", type=float, default=0.5)
    ap.add_argument("--redo", action="append", default=[],
                    help="pair label whose spent cells should be re-queued (e.g. gemma4-12b) "
                         "-- use after changing a parameter that caused the failures")
    args = ap.parse_args(argv)

    p = WAVE_PARAMS
    prior = existing_dirs()
    d = outdir()
    if prior:
        h, t = _scan(prior[-1])
        # Continue an unfinished prior wave. And when the prior wave is FINISHED, still report
        # on it rather than on today's empty directory: falling through to a new date told the
        # reader "0 of 63 collected, 315 local runs to collect" about an arm that was complete,
        # which is an instruction to re-run 315 jobs that already exist.
        if todo(h, t, tuple(args.redo)) or not args.run:
            d = prior[-1]
    # --report and --plan READ. They used to makedirs() unconditionally, so asking for the
    # status on a day with no wave CREATED an empty dated run directory as a side effect.
    if args.run:
        os.makedirs(d, exist_ok=True)
    have, tried = _scan(d)
    redo = tuple(args.redo)
    left = todo(have, tried, redo)

    if args.plan:
        for label, arm, model, cond in left:
            print("  %-12s %-8s %-46s %s" % (label, arm, model[-46:], cond))
        return 0

    if args.report or not args.run:
        allc = cells()
        done = [c for c in allc if have.get((c[2], c[3]), 0) >= p["runs"]]
        spent = [c for c in allc
                 if have.get((c[2], c[3]), 0) < p["runs"]
                 and tried.get((c[2], c[3]), 0) >= p["runs"]]
        print("ABLATION ARM AT THE WAVE PROTOCOL -- %s" % os.path.basename(d))
        print("  %d pair(s) x 2 build(s) x conditions %s at n=%d, temp %s, swept seed"
              % (len(PAIRS), "+".join(CONDITIONS), p["runs"], p["temperature"]))
        print("  %d of %d cell(s) at n=%d; %d to collect (%d local run(s), no API spend)"
              % (len(done), len(allc), p["runs"], len(left), len(left) * p["runs"]))
        if spent:
            print("  %d cell(s) had their runs and came back short:" % len(spent))
            for label, arm, model, cond in spent[:8]:
                print("      %-12s %-8s %s  %d valid of %d record(s)"
                      % (label, arm, cond, have.get((model, cond), 0),
                         tried.get((model, cond), 0)))
        return 0

    n = 0
    for (label, arm, model, cond) in left:
        if args.limit and n >= args.limit:
            break
        # One directory per pair per arm, matching the 2026-08-30 layout so both collections
        # can be read by the same loader.
        cell_dir = os.path.join(d, label, arm)
        os.makedirs(cell_dir, exist_ok=True)
        cmd = [sys.executable, os.path.join(HERE, "run_battery.py"),
               "--model", model, "--condition", cond,
               "--runs", str(p["runs"]), "--temperature", str(p["temperature"]),
               "--seed", str(p["seed_base"]),
               "--max-tokens", str(MAX_TOKENS.get(label, p["max_tokens"])),
               "--template", p["template"], "--channel", "ollama",
               "--delay", str(args.delay), "--out", cell_dir]
        if p.get("seed_sweep"):
            cmd.append("--seed-sweep")
        r = subprocess.run(cmd, capture_output=True, text=True)
        tail = [l for l in (r.stdout or "").splitlines() if "runs valid" in l]
        print("  %-12s %-8s %s  %s" % (label, arm, cond,
                                       tail[-1].split(":")[-1].strip() if tail
                                       else "(no result line)"))
        n += 1
    print("")
    print("collected %d cell(s); %d remain" % (n, len(left) - n))

    # "0 remain" IS NOT "DONE", AND SAYING ONLY THAT IS THE BUG THIS BLOCK EXISTS TO FIX.
    #
    # This run ended `collected 35 cell(s); 0 remain` and exited 0. Twelve of the 36 cells
    # held five records and ZERO valid answer sheets. Nothing in the exit line said so,
    # because `left` empties when every cell has been ASKED -- and the skip rule then stops
    # re-queueing exactly the cells that failed, so they never appear in `left` again either.
    # The failure is invisible in precisely the state where it matters.
    #
    # `--report` already printed the short cells. Run mode did not, and run mode is what an
    # operator reads. Two accountings of the same fact where only one is on the path anybody
    # takes is the same shape as a collector counting records while the verifier counts seeds.
    have, tried = _scan(d)
    allc = cells()
    short = [c for c in allc
             if have.get((c[2], c[3]), 0) < p["runs"]
             and tried.get((c[2], c[3]), 0) > 0]
    ok = [c for c in allc if have.get((c[2], c[3]), 0) >= p["runs"]]
    print("  %d of %d cell(s) at n=%d" % (len(ok), len(allc), p["runs"]))
    if short:
        print("  %d cell(s) ANSWERED NOTHING USABLE -- records on disk, no valid sheet:"
              % len(short))
        for label, arm, model, cond in short:
            print("      %-12s %-8s %-2s  %d valid of %d record(s)"
                  % (label, arm, cond, have.get((model, cond), 0),
                     tried.get((model, cond), 0)))
        print("  A pair needs BOTH arms. Check which pairs survive before analysing them.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
