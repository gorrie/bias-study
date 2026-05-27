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
sys.path.insert(0, str(SCRIPT_DIR))
import run_study as rs  # reuse load_questions + safe_filename + STUDY_DIR

# pipeline-flag presets per condition (extension fields on the chat/completions body)
COND_FLAGS = {
    "B-STM":          {"stm_modules": ["hedge_reducer", "direct_mode"], "parseltongue": False, "godmode": False, "autotune": False},
    "B-Parseltongue": {"stm_modules": [], "parseltongue": True, "godmode": False, "autotune": False},
    "B-Layered":      {"stm_modules": ["hedge_reducer", "direct_mode"], "parseltongue": True, "godmode": True, "autotune": True},
}


def call(base_url: str, model: str, user_text: str, flags: dict, api_key: str = "", timeout: int = 120) -> dict:
    body = {"model": model, "messages": [{"role": "user", "content": user_text}], "max_tokens": 800}
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
    args = ap.parse_args()

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    conditions = [c.strip() for c in args.conditions.split(",") if c.strip()]
    questions = rs.load_questions(args.positions.split(","))
    if not questions:
        print(f"ERROR: no questions for positions={args.positions}", file=sys.stderr); return 2

    out_dir = rs.STUDY_DIR / "runs" / args.out_date / "raw"
    out_dir.mkdir(parents=True, exist_ok=True)
    total = len(models) * len(questions) * len(conditions) * args.samples
    print(f"G0DM0D3 pipeline rung: {len(models)} models x {len(questions)} Q x {len(conditions)} conds x {args.samples} = {total} calls")

    n = ok = 0
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
                            resp = call(args.base_url, model, user_text, flags, api_key=args.api_key)
                            txt = resp["choices"][0]["message"]["content"]
                            rec.update(ok=True, response_text=txt,
                                       latency_ms=int((time.time() - t0) * 1000),
                                       word_count_total=len(re.findall(r"\w+", txt)),
                                       study_call_metadata={"called_via": "g0dm0d3",
                                           "g0dm0d3_pipeline": {k: flags[k] for k in flags},
                                           "x_g0dm0d3": resp.get("x_g0dm0d3"),
                                           "obliteratus_applied": None})
                            ok += 1
                        except Exception as e:
                            rec.update(ok=False, error=f"{type(e).__name__}: {str(e)[:200]}", response_text=None,
                                       study_call_metadata={"called_via": "g0dm0d3",
                                           "g0dm0d3_pipeline": {k: flags[k] for k in flags}})
                        fh.write(json.dumps(rec) + "\n"); fh.flush(); n += 1
            print(f"  {model} / {cond}: wrote {out_path.name}")
    print(f"DONE: {ok}/{n} ok -> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
