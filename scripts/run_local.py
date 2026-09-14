#!/usr/bin/env python3
"""
run_local.py — Run the bias question set against a LOCAL transformers model
(stock or OBLITERATUS-abliterated), writing raw JSONL in the study schema so
`score.py` / `aggregate.py` / `ci_analysis.py` consume it unchanged.

This is the local-inference channel for the abliteration leg (WP1): compare a
stock open-weight model vs its abliterated variant under the same conditions.
Reuses run_study's question loader + exact condition prompts so results are
directly comparable to the OpenRouter cross-section.

Runs on CUDA (Linux GPU host, in the obliteratus:gpu container) AND on Apple Silicon /
MPS (natively, no Docker — Apple has no GPU passthrough, see scripts/run_abliteration_native.sh
and DEVELOPER.md §1). Output lands in data/<out-date>/raw/<label>.jsonl, where score.py and
aggregate.py pick it up.

CUDA (Linux GPU host, via the obliteratus:gpu container):
    docker run --rm --gpus all -e HF_HUB_OFFLINE=1 \
      -v "$(pwd)/abliteration-output:/output" -v "$(pwd)/models:/models" \
      -v "$(pwd):/study" obliteratus:gpu \
      python /study/scripts/run_local.py --model-path /output/qwen2.5-7b-abliterated \
        --label qwen2.5-7b-abliterated --out-date <run> --conditions A,B
    # Windows / Git-Bash only: prefix with MSYS_NO_PATHCONV=1 so MSYS leaves -v paths intact.

Apple Silicon (native, MPS):
    PYTORCH_ENABLE_MPS_FALLBACK=1 python scripts/run_local.py \
      --model-path abliteration-output/gemma-2-9b-it-abliterated \
      --label gemma-2-9b-abliterated --out-date <run> --conditions A,B
    # MPS fallback routes linalg ops MPS doesn't implement through Accelerate/LAPACK, which
    # is what clears Gemma-2's MKL SVD failure. See DEVELOPER.md §3 + §7 Troubleshooting.

Usage:
    --model-path PATH       local HF model dir (loaded with from_pretrained)
    --label NAME            model label for the output filename + record
    --out-date DATE         data/<DATE>/raw/<label>.jsonl
    --conditions A,B        comma list from A,B,C,D,E (default A,B)
    --samples N             samples per cell (default 1)
    --positions ...         question positions (default neutral)
    --temperature 0.7       matches the study's model-call temperature
    --max-new-tokens 800    drop to ~400 on slow MPS hosts for ~2x throughput, no stance impact
    --resume                if the output JSONL exists, skip cells already recorded and
                            append the rest — recovery for interrupted/hung long M5 runs
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path


#: Filled in by main() once the model path and versions are known. Module-level so
#: the record builder can reach them; None until set, never silently absent.
WEIGHT_FP = None
TORCH_VERSION = None
TRANSFORMERS_VERSION = None


def weight_fingerprint(model_path):
    """A cheap, verifiable fingerprint of the weights actually loaded.

    WHY THIS EXISTS. Provenance used to be
        "obliteratus_applied": ("ablit" in args.label.lower())
    -- inferred from a substring of a USER-SUPPLIED LABEL. Nothing inspected the
    weights. Point --model-path at the stock directory with --label
    "qwen-abliterated" and the record asserts the ablation was applied; use
    --label "gemma-ablated" on a genuinely abliterated model and it records False.
    The abliteration skill's own hard lesson is that "an abliterated run that
    silently loads stock = a fake null", and nothing mechanical stood behind it.

    Hashes the file inventory (names + sizes) plus config.json, not the tensor
    bytes: enough to distinguish stock from abliterated, cheap on a multi-GB
    directory, and stable across reads.
    """
    h = hashlib.sha256()
    files = []
    try:
        for root, _dirs, names in os.walk(model_path):
            for n in sorted(names):
                if n.endswith((".safetensors", ".bin", ".gguf", ".json")):
                    p = os.path.join(root, n)
                    rel = os.path.relpath(p, model_path).replace(os.sep, "/")
                    files.append((rel, os.path.getsize(p)))
        for rel, size in sorted(files):
            h.update(("%s:%d\n" % (rel, size)).encode("utf-8"))
        cfg = os.path.join(model_path, "config.json")
        if os.path.exists(cfg):
            h.update(open(cfg, "rb").read())
    except Exception as exc:                       # pragma: no cover - IO guard
        return {"error": "%s: %s" % (type(exc).__name__, exc), "n_files": len(files)}
    return {"sha256_12": h.hexdigest()[:12], "n_files": len(files),
            "total_bytes": sum(s for _r, s in files)}

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
from studypaths import runs_root  # noqa: E402
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
    # A SEED, BECAUSE THERE WAS NONE AND IT COST THE WEIGHT RUNG ITS HEADLINE.
    #
    # This samples at temperature 0.7 and `torch.manual_seed` appeared nowhere in
    # the file, so the stock and abliterated arms drew from different RNG streams
    # and no run reproduced. Measured consequence: between-arm Jaccard of 0.339
    # (llama-3.1-8b) and 0.333 (mistral-7b) sit INSIDE the 0.303-0.392 band this
    # project measured for ONE MODEL RESAMPLED AGAINST ITSELF. Two of four
    # families were certified as "text rewrote ~66%" on nothing but sampling noise.
    ap.add_argument("--seed", type=int, default=20260913,
                    help="RNG seed. Both arms of a stock/abliterated pair MUST use "
                         "the same one, or the contrast measures resampling.")
    ap.add_argument("--resume", action="store_true",
                    help="If the output JSONL already exists, skip cells already recorded "
                         "and append new ones (don't truncate). Useful when a long M5 run is "
                         "interrupted — don't throw away the prior hour of work.")
    args = ap.parse_args()

    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer

    # SEED EVERY STREAM, BEFORE ANYTHING GENERATES. Both arms of a stock/abliterated
    # pair must run the same seed, or the between-arm difference is resampling.
    global WEIGHT_FP, TORCH_VERSION, TRANSFORMERS_VERSION
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    WEIGHT_FP = weight_fingerprint(args.model_path)
    TORCH_VERSION = torch.__version__
    TRANSFORMERS_VERSION = transformers.__version__
    print("weights %s  seed %d  temp %s  max_new_tokens %d"
          % (WEIGHT_FP.get("sha256_12", WEIGHT_FP.get("error")), args.seed,
             args.temperature, args.max_new_tokens), flush=True)

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

    # Warmup: amortize first-call kernel/shader compilation off the recorded latencies. On
    # MPS the first generate has been observed at ~7 min while steady-state is ~80 s for a
    # 9B at fp16; one throwaway generate moves that cost out of the per-record timings.
    try:
        warm = tok("hi", return_tensors="pt").to(model.device)
        with torch.no_grad():
            _ = model.generate(**warm, max_new_tokens=1, do_sample=False)
        print(f"  warmup done ({time.time()-t0:.0f}s since load start)", flush=True)
    except Exception as e:
        print(f"  warmup skipped: {e}", flush=True)

    out_dir = rs.runs_root() / args.out_date / "raw"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{rs.safe_filename(args.label)}.jsonl"

    # --resume: load already-recorded cells and skip them, appending new records. Without
    # --resume we truncate as before (backward-compatible).
    done = set()
    file_mode = "w"
    if args.resume and out_path.exists() and out_path.stat().st_size > 0:
        try:
            for line in out_path.open("r", encoding="utf-8"):
                r = json.loads(line)
                done.add((r["question_id"], r["condition"], r.get("sample_idx", 0)))
            file_mode = "a"
            print(f"  --resume: {len(done)} cells already recorded, skipping those", flush=True)
        except Exception as e:
            print(f"  --resume: failed to parse existing file ({e}); starting fresh", flush=True)
            done = set()

    n = len(done)
    total = len(questions) * len(conditions) * args.samples
    latencies = []   # per-record generate() latencies in ms, for the summary at the end
    with open(out_path, file_mode, encoding="utf-8") as fh:
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
                    if (q["id"], cond, s) in done:
                        continue
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
                        # THE COLLECTION PARAMETERS, recorded rather than inferred.
                        # None of max_new_tokens, temperature, seed, dtype, device
                        # or any weight identity was recorded before 2026-09-13, so
                        # a local run directory could not say what produced it.
                        "max_tokens": args.max_new_tokens,
                        "temperature": args.temperature,
                        "seed": args.seed,
                        "study_call_metadata": {
                            "called_via": "transformers-local",
                            "model_path": args.model_path,
                            # DERIVED FROM THE LABEL, and now SAID so. Kept because
                            # existing readers key on it; no longer the only evidence.
                            "obliteratus_applied_label_derived": ("ablit" in args.label.lower()),
                            "obliteratus_applied": ("ablit" in args.label.lower()),
                            # THE ACTUAL EVIDENCE. Two arms of a pair must differ
                            # here; if their fingerprints match, the "abliterated"
                            # arm loaded stock weights and the null is fake.
                            "weight_fingerprint": WEIGHT_FP,
                            "torch_version": TORCH_VERSION,
                            "transformers_version": TRANSFORMERS_VERSION,
                            "g0dm0d3_pipeline": None,
                        },
                    }
                    fh.write(json.dumps(rec) + "\n")
                    fh.flush()
                    n += 1
                    latencies.append(rec["latency_ms"])
                    print(f"  [{n}/{total}] {q['id']} {cond}#{s} ({rec['latency_ms']/1000:.1f}s)", flush=True)
                    # Flush the MPS cache after each record to relieve accumulating GPU memory
                    # pressure — correlated with the long-run hangs we've observed on the M5.
                    if hasattr(torch, "mps") and hasattr(torch.mps, "empty_cache"):
                        torch.mps.empty_cache()
    print(f"DONE: {n} records -> {out_path}", flush=True)
    if latencies:
        ls = sorted(latencies)
        mean_s, med_s = sum(ls) / len(ls) / 1000, ls[len(ls)//2] / 1000
        print(f"  per-record latency: mean {mean_s:.1f}s | median {med_s:.1f}s "
              f"| min {ls[0]/1000:.1f}s | max {ls[-1]/1000:.1f}s | wall {(time.time()-t0)/60:.1f}min",
              flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
