#!/usr/bin/env python3
"""
run_local.py — Run the bias question set against a LOCAL transformers model
(stock or OBLITERATUS-abliterated), writing raw JSONL in the study schema so
`score.py` / `aggregate.py` / `ci_analysis.py` consume it unchanged.

This is the local-inference channel for the abliteration leg (WP1): compare a
stock open-weight model vs its abliterated variant under the same conditions.
Reuses run_study's question loader + exact condition prompts so results are
directly comparable to the OpenRouter cross-section.

Run inside the obliteratus:gpu container (torch+transformers+CUDA), on a Linux GPU host —
the weight rung needs an NVIDIA GPU and does not run on macOS/Apple Silicon. MODELS_DIR and
ABLIT_OUT are your local model/output dirs; pass them as ABSOLUTE paths (a relative source
makes Docker create a named volume instead of bind-mounting your dir):
    docker run --rm --gpus all -e HF_HUB_OFFLINE=1 \
      -v "$(pwd)/abliteration-output:/output" \
      -v "$(pwd)/models:/models" \
      -v "$(pwd):/study" \
      obliteratus:gpu \
      python /study/scripts/run_local.py --model-path /output/qwen2.5-7b-abliterated \
        --label qwen2.5-7b-abliterated --out-date 2026-05-27-abliteration --conditions A,B
    # Windows / Git-Bash only: prefix with MSYS_NO_PATHCONV=1 so MSYS leaves -v paths intact.

Usage:
    --model-path PATH   local HF model dir
    --label NAME        model label for the output filename + record
    --out-date DATE     runs/<DATE>/raw/<label>.jsonl
    --conditions A,B    comma list from A,B,C,D,E (default A,B)
    --samples N         samples per cell (default 1)
    --positions ...     question positions (default neutral)
    --temperature 0.7   matches the study's model-call temperature
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
import run_study as rs  # reuse load_questions + condition constants


def build_messages(question: dict, condition: str):
    user_text = question["prompt"]
    system_text = None
    if condition == "A":
        system_text = rs.FAIRNESS_PROMPT
    elif condition == "B":
        user_text = question["prompt"] + rs.UNMASK_USER_SUFFIX["B"]
    elif condition == "C":
        user_text = question["prompt"] + rs.UNMASK_USER_SUFFIX["C"]
    elif condition == "D":
        system_text = rs.UNMASK_SYSTEM_PROMPT["D"]
        user_text = question["prompt"] + " What do you think?"
    elif condition == "E":
        system_text = rs.UNMASK_SYSTEM_PROMPT["E"]
        user_text = question["prompt"] + " What do you think?"
    else:
        raise ValueError(f"unknown condition {condition!r}")
    msgs = []
    if system_text:
        msgs.append({"role": "system", "content": system_text})
    msgs.append({"role": "user", "content": user_text})
    return msgs, system_text, user_text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-path", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--out-date", required=True)
    ap.add_argument("--conditions", default="A,B")
    ap.add_argument("--samples", type=int, default=1)
    ap.add_argument("--positions", default="neutral")
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--max-new-tokens", type=int, default=800)
    args = ap.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    positions = args.positions.split(",")
    conditions = [c.strip() for c in args.conditions.split(",") if c.strip()]
    questions = rs.load_questions(positions)
    if not questions:
        print(f"ERROR: no questions for positions={positions}", file=sys.stderr)
        return 2

    print(f"loading {args.model_path} ...", flush=True)
    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(args.model_path)
    # Device placement, following OBLITERATUS's device.py findings:
    #   CUDA — device_map="cuda" (the obliteratus:gpu production path).
    #   MPS  — accelerate's device_map="auto" is NOT reliable on Apple Silicon, so load then
    #          place explicitly with .to("mps"). fp16 is supported on MPS.
    # The weight rung needs a GPU; there's no CPU fallback (a 9B at fp16 on CPU is impractical).
    if torch.cuda.is_available():
        model = AutoModelForCausalLM.from_pretrained(args.model_path, dtype=torch.float16, device_map="cuda")
    elif torch.backends.mps.is_available():
        model = AutoModelForCausalLM.from_pretrained(args.model_path, dtype=torch.float16).to("mps")
    else:
        print("ERROR: no GPU (CUDA or MPS) available. Weight-rung inference needs a GPU.", file=sys.stderr)
        return 3
    model.eval()
    print(f"loaded in {time.time()-t0:.0f}s; {len(questions)} questions x {len(conditions)} conditions x {args.samples} samples", flush=True)

    out_dir = rs.STUDY_DIR / "data" / args.out_date / "raw"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{rs.safe_filename(args.label)}.jsonl"

    n = 0
    with open(out_path, "w", encoding="utf-8") as fh:
        for q in questions:
            for cond in conditions:
                msgs, system_text, user_text = build_messages(q, cond)
                try:
                    text = tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False)
                except Exception as e:
                    # Some chat templates (e.g. Gemma-2) have no system role. Fold the system
                    # content into the first user turn and retry so the fairness instruction
                    # (condition A) is still delivered. For such models the instruction is
                    # presented in the user turn rather than a system turn — noted in the writeup.
                    if "system" not in str(e).lower():
                        raise
                    merged, carry = [], None
                    for m in msgs:
                        if m["role"] == "system":
                            carry = m["content"]
                        elif m["role"] == "user" and carry:
                            merged.append({"role": "user", "content": carry + "\n\n" + m["content"]})
                            carry = None
                        else:
                            merged.append(m)
                    if carry:
                        merged.append({"role": "user", "content": carry})
                    text = tok.apply_chat_template(merged, add_generation_prompt=True, tokenize=False)
                inp = tok(text, return_tensors="pt").to(model.device)
                for s in range(args.samples):
                    start = time.time()
                    with torch.no_grad():
                        gen_kwargs = dict(max_new_tokens=args.max_new_tokens)
                        if args.temperature > 0:
                            gen_kwargs.update(do_sample=True, temperature=args.temperature, top_p=0.95)
                        else:
                            gen_kwargs.update(do_sample=False)
                        out = model.generate(**inp, **gen_kwargs)
                    resp = tok.decode(out[0][inp.input_ids.shape[1]:], skip_special_tokens=True)
                    rec = {
                        "model": args.label,
                        "channel": "transformers-local",
                        "question_id": q["id"],
                        "topic": q["topic"],
                        "position": q["position"],
                        "condition": cond,
                        "question_text": q["prompt"],
                        "system_prompt": system_text,
                        "user_prompt": user_text,
                        "called_at": datetime.datetime.now(datetime.UTC).isoformat(),
                        "ok": True,
                        "response_text": resp,
                        "latency_ms": int((time.time() - start) * 1000),
                        "word_count_total": len(re.findall(r"\w+", resp)),
                        "sample_idx": s,
                        "study_call_metadata": {
                            "called_via": "transformers-local",
                            "model_path": args.model_path,
                            "obliteratus_applied": ("ablit" in args.label.lower()),
                            "g0dm0d3_pipeline": None,
                        },
                    }
                    fh.write(json.dumps(rec) + "\n")
                    fh.flush()
                    n += 1
                    if n % 10 == 0:
                        print(f"  {n} done ({q['id']} {cond})", flush=True)
    print(f"DONE: {n} records -> {out_path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
