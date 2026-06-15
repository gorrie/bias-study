#!/usr/bin/env python3
"""Post-abliteration quality gate.

A bad abliteration silently produces a model that loads and runs but emits
garbage (or empty strings). The published `quality_metrics` in
`abliteration_metadata.json` is a leading indicator (perplexity=Infinity,
coherence=0.0 mean the verify-stage saw the rot) but is NOT sufficient on
its own — a bug in the verify step itself could leave the metrics looking
plausible while the model is still broken.

This gate runs two independent checks:

1. **Metadata gate** — reads `abliteration_metadata.json`, requires
   `quality_metrics.perplexity < 50` and `coherence > 0.5`. Conservative;
   a healthy gemma-2-9b abliteration is perplexity ~7-15, coherence 1.0.

2. **Generation gate** — loads the model with transformers on MPS and
   generates a 3-prompt fixed-seed sanity battery. Each prompt has a
   known short answer; if the model can't produce the answer the
   projection nuked it.

Exits 0 only if BOTH gates pass. On failure renames the directory to
`<dir>-FAILED-<unix-ts>` and prints which gate(s) failed plus the actual
output so the operator can diagnose without re-running.

Usage:
    python scripts/dose_smoke_gate.py <abliterated-dir>
    python scripts/dose_smoke_gate.py <dir> --skip-generation  # metadata only
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

# Three short-answer prompts. Each (prompt, regex-match-on-output) pair must
# pass. Fixed-seed greedy decoding so the gate is deterministic.
SANITY_BATTERY: list[tuple[str, str]] = [
    ("What is the capital of France? Answer in one word.", r"\bParis\b"),
    ("What is 2 + 2? Answer with only the number.", r"\b4\b"),
    ("Name one prime number. Answer with only the number.",
     r"\b(2|3|5|7|11|13|17|19|23|29|31|37|41|43|47|53|59|61|67|71|73|79|83|89|97)\b"),
]

# Healthy gemma-2-9b reference (the existing n_dir=4 spine): perplexity 7.86,
# coherence 1.0. Thresholds are generous — anything past these is clearly broken.
MAX_PERPLEXITY = 50.0
MIN_COHERENCE = 0.5


def metadata_gate(dose_dir: Path) -> tuple[bool, str]:
    meta_path = dose_dir / "abliteration_metadata.json"
    if not meta_path.exists():
        return False, f"abliteration_metadata.json missing at {meta_path}"
    try:
        meta = json.loads(meta_path.read_text())
    except json.JSONDecodeError as e:
        return False, f"abliteration_metadata.json unparseable: {e}"
    qm = meta.get("quality_metrics") or {}
    perplexity = qm.get("perplexity")
    coherence = qm.get("coherence")
    if perplexity is None or coherence is None:
        return False, f"quality_metrics missing perplexity/coherence: {qm}"
    # JSON "Infinity" decodes as math.inf in Python; this comparison handles both.
    if not (perplexity < MAX_PERPLEXITY):
        return False, f"perplexity={perplexity} not < {MAX_PERPLEXITY}"
    if not (coherence > MIN_COHERENCE):
        return False, f"coherence={coherence} not > {MIN_COHERENCE}"
    return True, f"perplexity={perplexity:.2f} coherence={coherence:.2f}"


def generation_gate(dose_dir: Path, max_new_tokens: int = 32) -> tuple[bool, str]:
    # Defer the heavy imports so a metadata-only failure exits fast.
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as e:
        return False, f"transformers/torch unavailable: {e}"

    device = "mps" if torch.backends.mps.is_available() else (
        "cuda" if torch.cuda.is_available() else "cpu")
    tok = AutoTokenizer.from_pretrained(str(dose_dir))
    model = AutoModelForCausalLM.from_pretrained(
        str(dose_dir), dtype=torch.float16, device_map=device)
    model.eval()

    failures: list[str] = []
    samples: list[str] = []
    for prompt, expect_re in SANITY_BATTERY:
        chat_text = tok.apply_chat_template(
            [{"role": "user", "content": prompt}],
            tokenize=False, add_generation_prompt=True,
        )
        inputs = tok(chat_text, return_tensors="pt").to(device)
        out = model.generate(
            **inputs, max_new_tokens=max_new_tokens,
            do_sample=False, pad_token_id=tok.eos_token_id,
        )
        gen_ids = out[0][inputs.input_ids.shape[-1]:]
        text = tok.decode(gen_ids, skip_special_tokens=True).strip()
        samples.append(f"  {prompt!r} -> {text[:80]!r}")
        if not re.search(expect_re, text, flags=re.IGNORECASE):
            failures.append(f"prompt={prompt!r} expected={expect_re} got={text[:80]!r}")

    if failures:
        return False, "; ".join(failures) + "\n" + "\n".join(samples)
    return True, "all 3 prompts produced expected answers\n" + "\n".join(samples)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("dose_dir", help="Abliterated model directory to validate")
    p.add_argument("--skip-generation", action="store_true",
                   help="Run only the metadata gate (faster; weaker)")
    p.add_argument("--no-rename", action="store_true",
                   help="Do not rename the dir to -FAILED on failure (debug)")
    args = p.parse_args()

    dose_dir = Path(args.dose_dir).resolve()
    if not dose_dir.is_dir():
        print(f"FAIL: {dose_dir} is not a directory", file=sys.stderr)
        return 2

    print(f"=== smoke gate: {dose_dir.name} ===", flush=True)

    meta_ok, meta_msg = metadata_gate(dose_dir)
    print(f"  metadata: {'PASS' if meta_ok else 'FAIL'} ({meta_msg})", flush=True)

    if args.skip_generation:
        gen_ok, gen_msg = True, "skipped"
    else:
        t0 = time.time()
        gen_ok, gen_msg = generation_gate(dose_dir)
        print(f"  generation: {'PASS' if gen_ok else 'FAIL'} ({time.time()-t0:.1f}s)",
              flush=True)
        print(gen_msg, flush=True)

    if meta_ok and gen_ok:
        print(f"=== GATE PASSED: {dose_dir.name} ===", flush=True)
        return 0

    print(f"=== GATE FAILED: {dose_dir.name} ===", flush=True)
    if not args.no_rename:
        ts = int(time.time())
        failed_path = dose_dir.with_name(f"{dose_dir.name}-FAILED-{ts}")
        dose_dir.rename(failed_path)
        print(f"  renamed -> {failed_path}", flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())
