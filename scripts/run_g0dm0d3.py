#!/usr/bin/env python3
"""
run_g0dm0d3.py — PIPELINE rung of the bias-study escalation ladder.

Drives the neutral question set through the G0DM0D3 OpenAI-compatible server
(localhost:7860 by default), which applies elicitation-layer force — STM
hedge-strip + Parseltongue obfuscation — on top of the prompt unmask. Writes raw
JSONL in the study schema with the `g0dm0d3_pipeline` record field populated, so
score.py / aggregate.py / ci_analysis.py consume it unchanged.

Conditions (all use the condition-B base: question + " What do you think?"):
  B-STM         : stm_modules=[hedge_reducer,direct_mode]                 (hedge-strip only)
  B-Parseltongue: parseltongue=true                                       (obfuscation only)
  B-Layered     : parseltongue + STM + godmode + autotune                 (full stack)

Layered obfuscation is most potent up to a functionality ceiling; past it the
output degrades to noise. The COHERENCE GUARD is downstream: score.py / the judge
records a broken/incoherent response as null — it must NEVER be scored as
"maximum skepticism." The ceiling (where added force stops helping and starts
breaking) is itself a reportable finding.

Server must be up first (G0DM0D3 is referenced, not vendored — clone it from the URL
in README.md at the pinned commit, then):  cd <your-G0DM0D3-checkout> && docker compose up --build -d api
Its own .env carries the upstream OPENROUTER_API_KEY, so we don't pass a key per request.

Usage:
    python run_g0dm0d3.py --models anthropic/claude-opus-4.7,x-ai/grok-4.3 \
        --conditions B-STM,B-Parseltongue,B-Layered --out-date 2026-05-27-g0dm0d3
"""
from __future__ import annotations

import argparse, datetime, json, re, sys, time
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).parent

sys.path.insert(0, str(Path(__file__).resolve().parent))
from studypaths import runs_root, LEGACY_SEED  # noqa: E402
sys.path.insert(0, str(SCRIPT_DIR))
import run_study as rs  # reuse load_questions + safe_filename + STUDY_DIR

# pipeline-flag presets per condition (extension fields on the chat/completions body)
#
# EVERY FLAG IS SENT EXPLICITLY, INCLUDING THE FALSE ONES. The server defaults
# `godmode` and `parseltongue` to TRUE when the field is absent, so an omitted
# flag is not "off" -- it is the opposite of off. Verified against the running
# server 2026-09-14; do not "simplify" these dicts by dropping the falses.
COND_FLAGS = {
    "B-STM":          {"stm_modules": ["hedge_reducer", "direct_mode"], "parseltongue": False, "godmode": False, "autotune": False},
    "B-Parseltongue": {"stm_modules": [], "parseltongue": True, "godmode": False, "autotune": False},
    "B-Layered":      {"stm_modules": ["hedge_reducer", "direct_mode"], "parseltongue": True, "godmode": True, "autotune": True},
    # THE PROXY CONTROL, added 2026-09-14. Plain condition B routed through
    # G0DM0D3 with every transform off.
    #
    # The rung-2 baseline goes DIRECT to OpenRouter while every pipeline record
    # goes through this proxy, so all six "vs plain B" contrasts confound the
    # named transform with the proxy path itself. That was invisible while
    # B-Parseltongue looked like a treatment arm; once its obfuscation was shown
    # to have never fired (0 of 240 requests -- pipeline_transform_audit.py), the
    # contrast became a null-by-construction floor, and Claude Opus's read
    # +0.24 [+0.02, +0.49], EXCLUDING ZERO on an arm that received nothing.
    #
    # This condition measures that floor directly instead of inferring it.
    "B-Proxy":        {"stm_modules": [], "parseltongue": False, "godmode": False, "autotune": False},
}


from eligibility import looks_truncated_text as looks_truncated  # noqa: E402
# ONE definition of "is this severed", in eligibility.py, because the collector's
# verdict and the reader's verdict disagreeing is how 21.5% of the corpus became
# eligible while the collector was flagging it. Two copies of a rule is two rules.


def call(base_url: str, model: str, user_text: str, flags: dict, api_key: str = "", timeout: int = 120,
         max_tokens: int = 800) -> dict:
    body = {"model": model, "messages": [{"role": "user", "content": user_text}], "max_tokens": max_tokens}
    body.update(flags)
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    r = requests.post(f"{base_url}/chat/completions", json=body, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r.json()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="anthropic/claude-opus-4.7,x-ai/grok-4.3")
    ap.add_argument("--conditions", default="B-STM,B-Parseltongue,B-Layered")
    ap.add_argument("--out-date", required=True)
    ap.add_argument("--positions", default="neutral")
    ap.add_argument("--base-url", default="http://localhost:7860/v1")
    ap.add_argument("--samples", type=int, default=1)
    ap.add_argument("--api-key", default="")
    # The May 2026 wave ran at 800. Keep that the default so those records stay
    # reproducible, but let a run match its own plain-B baseline: an arm capped
    # lower than the arm it is contrasted against measures truncation, not force.
    ap.add_argument("--max-tokens", type=int, default=800)
    ap.add_argument("--overwrite", action="store_true",
                    help="replace existing records for this --out-date. Without it the run "
                         "refuses, because the output path carries neither --positions nor "
                         "--max-tokens and a re-run would replace them silently.")
    args = ap.parse_args()

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    conditions = [c.strip() for c in args.conditions.split(",") if c.strip()]
    questions = rs.load_questions(args.positions.split(","))
    if not questions:
        print(f"ERROR: no questions for positions={args.positions}", file=sys.stderr); return 2

    out_dir = runs_root() / args.out_date / "raw"
    out_dir.mkdir(parents=True, exist_ok=True)
    started_at = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    total = len(models) * len(questions) * len(conditions) * args.samples
    print(f"G0DM0D3 pipeline rung: {len(models)} models x {len(questions)} Q x {len(conditions)} conds x {args.samples} = {total} calls")

    n = ok = truncated = 0
    #: Models that produced at least one usable record. A model named in
    #: models_attempted but absent here failed entirely, and the manifest must say
    #: so rather than implying the run covered it.
    completed_models: set = set()
    # REFUSE TO DESTROY RECORDS. The path is {model}__{condition}.jsonl and omits
    # --positions, so a second run at a different positions set replaced the first
    # instead of adding to it. Executed: --positions neutral then --positions mild
    # under one --out-date left ONE record, the mild one. Same hazard for a re-run
    # at a different --max-tokens, which is exactly what a truncation fix looks like.
    for model in models:
        for cond in conditions:
            p = out_dir / f"{rs.safe_filename(model)}__{cond}.jsonl"
            if p.exists() and p.stat().st_size > 0 and not args.overwrite:
                n = sum(1 for _ in p.open(encoding="utf-8") if _.strip())
                print(f"ERROR: {p} already holds {n} record(s), and this path does not "
                      f"carry --positions or --max-tokens, so a re-run under different "
                      f"parameters would replace them silently. Use a new --out-date, or "
                      f"--overwrite if replacing them is intended.", file=sys.stderr)
                return 2

    for model in models:
        for cond in conditions:
            flags = COND_FLAGS[cond]
            out_path = out_dir / f"{rs.safe_filename(model)}__{cond}.jsonl"
            with open(out_path, "w", encoding="utf-8") as fh:
                for q in questions:
                    user_text = q["prompt"] + rs.UNMASK_USER_SUFFIX["B"]
                    for s in range(args.samples):
                        rec = {"model": model, "channel": "g0dm0d3", "question_id": q["id"],
                               "topic": q["topic"], "position": q["position"], "condition": cond,
                               "question_text": q["prompt"], "user_prompt": user_text,
                               "called_at": datetime.datetime.now(datetime.UTC).isoformat(), "sample_idx": s}
                        try:
                            t0 = time.time()
                            resp = call(args.base_url, model, user_text, flags, api_key=args.api_key,
                                        max_tokens=args.max_tokens)
                            choice = resp["choices"][0]
                            txt = choice["message"]["content"]
                            finish = choice.get("finish_reason")
                            is_trunc = looks_truncated(txt)
                            rec.update(ok=True, response_text=txt,
                                       latency_ms=int((time.time() - t0) * 1000),
                                       word_count_total=len(re.findall(r"\w+", txt)),
                                       finish_reason=finish,
                                       truncated=is_trunc,
                                       usage=resp.get("usage"),
                                       study_call_metadata={"called_via": "g0dm0d3",
                                           "g0dm0d3_pipeline": {k: flags[k] for k in flags},
                                           "max_tokens": args.max_tokens,
                                           "x_g0dm0d3": resp.get("x_g0dm0d3"),
                                           "obliteratus_applied": None})
                            ok += 1
                            completed_models.add(model)
                            if is_trunc:
                                truncated += 1
                        except Exception as e:
                            rec.update(ok=False, error=f"{type(e).__name__}: {str(e)[:200]}", response_text=None,
                                       study_call_metadata={"called_via": "g0dm0d3",
                                           "g0dm0d3_pipeline": {k: flags[k] for k in flags}})
                        fh.write(json.dumps(rec) + "\n"); fh.flush(); n += 1
            print(f"  {model} / {cond}: wrote {out_path.name}")
    # WRITE THE MANIFEST. This collector wrote none at all, so every run it ever
    # produced -- including the n=5 pair that is now the rung-2 default -- reached
    # validate_runs as "no manifest.json" and could not be checked against its own
    # intent. run_study.py has written one since May; this one never did, and the
    # gap was invisible because the runs it produces are scored by the same tools.
    manifest = {
        "analysis_seed": getattr(args, "seed", None) or LEGACY_SEED,
        "calls_completed": ok,
        "calls_failed": n - ok,
        "completed_at": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "collector": "run_g0dm0d3.py",
        "conditions": conditions,
        "max_tokens": args.max_tokens,
        "models_attempted": list(models),
        "models_completed": sorted(completed_models),
        "models_failed": sorted(set(models) - completed_models),
        "positions": args.positions.split(","),
        "run_date": args.out_date,
        "samples_per_cell": args.samples,
        "started_at": started_at,
        "total_calls_planned": total,
        "truncated_by_text_test": truncated,
    }
    with open(runs_root() / args.out_date / "manifest.json", "w",
              encoding="utf-8", newline="\n") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
        fh.write("\n")

    print(f"DONE: {ok}/{n} ok, {truncated} truncated (text test, NOT finish_reason) at "
          f"max_tokens={args.max_tokens} -> {out_dir}")
    # A RUN WHERE EVERY CALL FAILED IS NOT A SUCCESS. Only truncation returned
    # non-zero; failures returned 0, so a wrapper or an `&&` chain read
    # "DONE: 0/300 ok" as success and moved on to scoring an empty run.
    if n and ok == 0:
        print(f"ERROR: every one of {n} call(s) failed. Nothing was collected.",
              file=sys.stderr)
        return 2
    if n and ok < n:
        print(f"WARNING: {n - ok} of {n} call(s) failed; the run is incomplete.",
              file=sys.stderr)
    if truncated:
        print(f"WARNING: {truncated} of {ok} response(s) end mid-sentence. A severed response is "
              f"not a measurement and must not be scored — raise --max-tokens and re-collect.",
              file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
