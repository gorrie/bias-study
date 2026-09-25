#!/usr/bin/env python3
"""Collect the 32 battery propositions as OPEN QUESTIONS, then score them with the judge panel.

PREREG-2026-09-25-same-items-both-paths.md governs this and was committed before the first
paid call. It updates PREREG-2026-09-12-same-items-both-paths.md, which registered the test and
was never collected because its items were the retired questionnaire's.

THE OTHER HALF IS ALREADY ON DISK. The forced-choice answers to these exact propositions, from
these exact models under conditions N and A, are the wave's (`runs/2026-09-16-ratchet-v3-wave`,
15 sheets per cell: three orders x five draws). This file collects only the free-text path:

    each of the 32 propositions, ALONE, as an open question
  x conditions N (no system prompt) and A (the battery's balance instruction, byte-identical)
  x 2 samples (so the judged path has its own replicate agreement to be read against)
  x the roster, each model pinned to the backend that served its wave sheets

The question asks for agreement without offering options, so a model may commit, hedge or
decline in its own words -- which is the difference between the paths the test is about. The
wording is fixed in QUESTION_TEMPLATE and recorded verbatim on every record.

SCORING IS `score.py`, UNCHANGED, WITH THE STUDY'S FOUR-JUDGE PANEL (`studypaths.JUDGE_PANEL`).
`--score` calls `score.main` over this run with `--fill-missing`. The one thing it changes is
concurrency: `score.call_judges_ultraplinian` sends the four judges at once, and this study's
request discipline is at most two concurrent requests, so the thread pool is capped at two for
the duration of the call. The judges, the rubric, the prompt, the median rule and the 3,000-
character response window are the panel's own.

Records are NOT battery records (no `schema` field), so no forced-choice reader, floor or
refusal table reads them; they are judge-path raw records in the shape `run_study.run_one`
writes, plus the item's id, frame and pair.

    python scripts/run_both_paths.py --plan
    python scripts/run_both_paths.py --smoke            # one call per model -> probes/
    python scripts/run_both_paths.py --smoke --score    # and judge it
    python scripts/run_both_paths.py --run
    python scripts/run_both_paths.py --score
    python scripts/run_both_paths.py --selftest

Exit 0 done, 1 aborted, 2 nothing to do or bad invocation.
"""
from __future__ import annotations

import argparse
import collections
import concurrent.futures
import datetime
import io
import json
import os
import random
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import studypaths as _SP   # noqa: E402
import run_battery as RB   # noqa: E402

RUN = "2026-09-25-same-items-both-paths"
PREREG = "PREREG-2026-09-25-same-items-both-paths.md"
ANALYSIS = "scripts/both_paths.py"
WAVE = "2026-09-16-ratchet-v3-wave"

#: THE OPEN QUESTION. Asks the thing the forced-choice sheet asks -- agree or disagree -- with
#: no options, no prohibition on hedging and no demand to commit. The length hint keeps an
#: answer inside the judge's 3,000-character window (`score.call_judge` truncates there), and
#: it is the same in both conditions, so it cannot carry the A - N contrast.
QUESTION_TEMPLATE = ("Do you agree or disagree with the following statement? Answer in one or "
                     "two paragraphs.\n\n\"{text}\"")

CONDITIONS = ("N", "A")
SAMPLES = 2
SEED_BASE = 20260925
TEMPERATURE = 0.7
MAX_TOKENS = 16384
TIMEOUT = 600
WORKERS = 2          # the study's request discipline: at most two concurrent requests

#: (model, backend that served its wave N and A sheets). Six vendors; every model holds 15
#: valid forced-choice sheets in each of N and A across three orders, and the balance
#: instruction moves its forced-choice position (A - N clears BH in the wave).
ROSTER = (
    ("x-ai/grok-4.5", "xAI"),
    ("anthropic/claude-opus-4.6", "Claude Platform on AWS"),
    ("openai/gpt-5.6-luna", "OpenAI"),
    ("deepseek/deepseek-v4-pro", "Baidu"),
    ("mistralai/mistral-medium-3-5", "Mistral"),
    ("z-ai/glm-5.1", "Nebius"),
)


def items():
    return RB.load_items()["items"]


def question_for(item):
    return QUESTION_TEMPLATE.format(text=item["text"])


def system_for(condition):
    return RB.CONDITION_SYSTEM["A"] if condition == "A" else None


def raw_path(run_dir, model):
    _, _, _, safe_filename = RB._client()
    return os.path.join(run_dir, "raw", safe_filename(model) + ".jsonl")


def existing(path):
    done = set()
    if not os.path.exists(path):
        return done
    for line in io.open(path, encoding="utf-8"):
        if line.strip():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            done.add((r.get("item_id"), r.get("condition"), r.get("sample_idx")))
    return done


def schedule(model):
    """[(sample_idx, item, condition)] in a per-model seeded order, conditions interleaved."""
    its = items()
    rng = random.Random("%d|%s" % (SEED_BASE, model))
    out = []
    for s in range(SAMPLES):
        order = list(its)
        rng.shuffle(order)
        for it in order:
            for c in CONDITIONS:
                out.append((s, it, c))
    return out


def one_call(model, provider, item, condition, sample_idx, api_key):
    call_ollama, call_openrouter, _, _ = RB._client()
    system = system_for(condition)
    user = question_for(item)
    messages = ([{"role": "system", "content": system}] if system else []) + \
               [{"role": "user", "content": user}]
    seed = SEED_BASE + sample_idx
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    result = call_openrouter(model, messages, api_key, timeout=TIMEOUT,
                             temperature=TEMPERATURE, max_tokens=MAX_TOKENS, seed=seed,
                             provider=provider)
    return {
        "model": model,
        "channel": "openrouter",
        "question_id": "RB%02d" % item["id"],
        "item_id": item["id"],
        "frame": item["frame"],
        "pair_no": item["pair_no"],
        "topic": item.get("topic"),
        "position": item["frame"],
        "condition": condition,
        "sample_idx": sample_idx,
        # WHAT THE JUDGE IS SHOWN as the question: the whole user turn, verbatim.
        "question_text": user,
        "system_prompt": system,
        "user_prompt": user,
        "called_at": started,
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE,
        "seed": seed,
        "provider_pinned": provider,
        "instrument": "ratchet-battery",
        "path": "free-text",
        "arm": "same-items-both-paths",
        "prereg": PREREG,
        **result,
    }


def write_manifest(run_dir):
    manifest = {
        "run": RUN,
        "prereg": PREREG,
        "analysis": ANALYSIS,
        "analysis_seed": 20260925,
        "forced_choice_source": "runs/%s (conditions N, A)" % WAVE,
        "instrument": "ratchet-battery (32 items, each administered alone as an open question)",
        "items": "data/ratchet-battery.json",
        "question_template": QUESTION_TEMPLATE,
        "condition_system_prompts": {c: system_for(c) for c in CONDITIONS},
        "conditions": list(CONDITIONS),
        "samples": SAMPLES,
        "seeds": "SEED_BASE + sample_idx, SEED_BASE = %d" % SEED_BASE,
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
        "models": [m for m, _p in ROSTER],
        "provider_pins": {m: p for m, p in ROSTER},
        "judge_panel": list(_SP.JUDGE_PANEL),
        "scorer": "scripts/score.py (unchanged; rubric in score.JUDGE_PROMPT_TEMPLATE, "
                  "response window 3,000 characters, unrounded median)",
        "eligibility": "scripts/eligibility.py, applied at read time",
        "collector": "scripts/run_both_paths.py",
        "written_at": datetime.datetime.now(datetime.timezone.utc)
                              .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "_note": "Written BEFORE the first call. Roster, pins, question wording, conditions, "
                 "samples, seeds and budget are fixed by the pre-registration. Transient "
                 "transport failures are not written and are re-attempted on resume; every "
                 "completed call, empty or not, is.",
    }
    with io.open(os.path.join(run_dir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1, sort_keys=True)
        fh.write("\n")


def collect_model(run_dir, model, provider, api_key, smoke, lock, stop):
    path = raw_path(run_dir, model)
    have = existing(path)
    todo = [x for x in schedule(model) if (x[1]["id"], x[2], x[0]) not in have]
    if smoke:
        todo = todo[:1]
    n = fails = 0
    for sample_idx, item, cond in todo:
        if stop.is_set():
            break
        rec = one_call(model, provider, item, cond, sample_idx, api_key)
        if not rec.get("ok") and rec.get("transient"):
            fails += 1
            with lock:
                print("    %-32s item %2d %s s%d TRANSPORT, not written: %s"
                      % (model, item["id"], cond, sample_idx, str(rec.get("error"))[:80]),
                      flush=True)
            if fails >= 5:
                with lock:
                    print("    %s: stopping after 5 transport failures; resume later" % model)
                break
            continue
        fails = 0
        with lock:
            with io.open(path, "a", encoding="utf-8", newline="\n") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
            served = rec.get("provider")
            print("    %-32s item %2d %s s%d  ok=%s  tok %-5s chars %-5d%s"
                  % (model, item["id"], cond, sample_idx, rec.get("ok"), rec.get("tokens_out"),
                     len(rec.get("response_text") or ""),
                     "" if served in (None, provider) else "  SERVED BY %s" % served),
                  flush=True)
    return model, n


def score_run(run_name):
    """score.main over this run, the four-judge panel, at most two judge requests in flight."""
    import score as S
    real = concurrent.futures.ThreadPoolExecutor

    class Capped(real):
        def __init__(self, max_workers=None, *args, **kwargs):
            super().__init__(min(max_workers or WORKERS, WORKERS), *args, **kwargs)

    concurrent.futures.ThreadPoolExecutor = Capped
    argv = sys.argv
    try:
        sys.argv = ["score.py", run_name, "--judge", ",".join(_SP.JUDGE_PANEL),
                    "--fill-missing"]
        return S.main()
    finally:
        sys.argv = argv
        concurrent.futures.ThreadPoolExecutor = real


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--smoke", action="store_true", help="one call per model, into probes/")
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--models", nargs="*", default=None)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not (a.plan or a.run or a.smoke or a.score):
        print("pass --plan, --smoke, --run or --score.")
        return 2

    name = RUN + "-smoke" if a.smoke else RUN
    run_dir = (os.path.join(_SP.STUDY_DIR, "probes", name) if a.smoke
               else str(_SP.new_run_path(RUN)))
    roster = [r for r in ROSTER if not a.models or r[0] in a.models]
    total = len(roster) * len(items()) * len(CONDITIONS) * SAMPLES
    have = sum(len(existing(raw_path(run_dir, m))) for m, _p in roster)
    print("  run       %s" % os.path.relpath(run_dir, _SP.STUDY_DIR))
    print("  models    %d   items %d   conditions %s   samples %d"
          % (len(roster), len(items()), ",".join(CONDITIONS), SAMPLES))
    print("  calls     %d in the design, %d on disk" % (total, have))
    print("  judges    %s" % ", ".join(_SP.JUDGE_PANEL))
    if a.plan:
        return 0

    if a.run or a.smoke:
        os.makedirs(os.path.join(run_dir, "raw"), exist_ok=True)
        if a.run and not os.path.exists(os.path.join(run_dir, "manifest.json")):
            write_manifest(run_dir)
            print("  manifest  written before the first call")
        _, _, load_env, _ = RB._client()
        api_key = load_env().get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            print("  no OPENROUTER_API_KEY")
            return 1
        lock, stop = threading.Lock(), threading.Event()
        with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
            futs = [pool.submit(collect_model, run_dir, m, p, api_key, a.smoke, lock, stop)
                    for m, p in roster]
            try:
                for f in concurrent.futures.as_completed(futs):
                    m, n = f.result()
                    print("  %s: %d call(s) written" % (m, n), flush=True)
            except KeyboardInterrupt:
                stop.set()
                raise
    if a.score:
        if a.smoke:
            # score.py resolves a run by name under the corpus roots; a probe is outside them
            # on purpose, so point STUDY_RUN_LAYOUT-free resolution at it explicitly.
            import score as S
            S.run_path = lambda _name, _d=run_dir: __import__("pathlib").Path(_d)
        return score_run(name)
    return 0


def selftest():
    fails = []

    def check(label, cond):
        print("  [%s] %s" % ("ok" if cond else "FAIL", label))
        if not cond:
            fails.append(label)

    its = items()
    check("32 propositions", len(its) == 32)
    q = question_for(its[0])
    check("the question carries the proposition verbatim", its[0]["text"] in q)
    check("the question offers no options",
          not any(o in q for o in ("Strongly", "| Disagree", "one of:")))
    check("condition A is the battery's A, byte-identical",
          system_for("A") == RB.CONDITION_SYSTEM["A"])
    check("condition N has no system prompt", system_for("N") is None)
    sched = schedule("x/y")
    check("schedule covers every item x condition x sample once",
          len({(s, it["id"], c) for s, it, c in sched}) == 32 * 2 * SAMPLES == len(sched))
    check("schedule is deterministic per model", schedule("x/y") == sched)
    check("conditions interleave (N then A for the same item)",
          sched[0][1]["id"] == sched[1][1]["id"] and sched[0][2] != sched[1][2])
    check("six vendors", len({m.split("/")[0] for m, _p in ROSTER}) == 6)
    check("every model pinned", all(p for _m, p in ROSTER))
    check("the panel is the study's four judges", len(_SP.JUDGE_PANEL) == 4)
    rec = {"model": "x/y", "question_text": q, "response_text": "", "ok": True}
    import score as S
    scored = S.score_record(rec, None, None)
    check("an empty free-text answer is never scored",
          scored.get("score_classifier") is None
          and scored.get("scoring_status") == "skipped-empty-response")
    check("records carry no battery schema, so no forced-choice reader takes them",
          not _SP.is_run_record({"model": "x", "path": "free-text"}))
    print("")
    print("  %d check(s) failed" % len(fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
