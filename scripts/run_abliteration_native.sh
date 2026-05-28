#!/usr/bin/env bash
# run_abliteration_native.sh — Apple-Silicon / native analog of run_abliteration_sweep.sh.
#
# Runs OBLITERATUS directly on the host's torch+MPS stack — no Docker, no CUDA — for hosts
# where the obliteratus:gpu container doesn't apply (Apple Silicon has no GPU passthrough).
# PYTORCH_ENABLE_MPS_FALLBACK=1 routes ops MPS doesn't implement (notably linalg.eigh used
# for SVD direction extraction) to Apple's Accelerate/LAPACK on CPU — which is also what
# clears the Gemma-2 MKL `SSYEVD` failure that killed it on the 4090.
#
# Same per-family loop as the Docker sweep: abliterate -> coherence smoke -> A/B stock+ablit.
# Edit NATIVE_SWEEP=(...) to add/swap families. Output lands in data/<OUT_DATE>/raw/
# (run_local.py writes there now), so score.py + aggregate.py pick it up unchanged.
#
# Prereq: a venv with the weight-rung deps installed — see requirements-weightrung.txt.
set -u
cd "$(dirname "$0")/.."          # -> bias-study/

OUT_DATE="${OUT_DATE:-$(date +%F)-abliteration-native}"
MODELS_VOL="${MODELS_DIR:-$(pwd)/models}"
ABL_VOL="${ABLIT_OUT:-$(pwd)/abliteration-output}"
PY="${PYTHON:-.venv/bin/python}"
export PYTORCH_ENABLE_MPS_FALLBACK=1

# model_dir (under $MODELS_VOL) : abliterated_dir (under $ABL_VOL) : label_stub
NATIVE_SWEEP=(
  "gemma-2-9b-it:gemma-2-9b-it-abliterated:gemma-2-9b"
)

[ -x "$PY" ] || { echo "ERROR: $PY not found — create the venv per requirements-weightrung.txt."; exit 2; }

for entry in "${NATIVE_SWEEP[@]}"; do
  IFS=":" read -r mdir adir label <<< "$entry"
  echo "================ $label ================"

  # 1. abliterate (skip if already present + non-empty)
  if ls "$ABL_VOL/$adir"/*.safetensors >/dev/null 2>&1; then
    echo "[$label] abliterated weights already present — skip abliterate"
  else
    echo "[$label] abliterating natively on MPS (advanced/SVD)..."
    "$PY" -m obliteratus.cli obliterate "$MODELS_VOL/$mdir" \
        --output-dir "$ABL_VOL/$adir" --device auto --dtype float16 --method advanced \
      || { echo "[$label] ABLITERATE FAILED — skipping model"; continue; }
  fi

  # 2. coherence smoke test (single greedy gen; same Paris check as the Docker sweep)
  echo "[$label] smoke-testing abliterated model..."
  "$PY" -c "
import sys, torch
from transformers import AutoModelForCausalLM, AutoTokenizer
p='$ABL_VOL/$adir'
try:
    tok=AutoTokenizer.from_pretrained(p)
    if torch.cuda.is_available():
        m=AutoModelForCausalLM.from_pretrained(p, dtype=torch.float16, device_map='cuda')
    elif torch.backends.mps.is_available():
        m=AutoModelForCausalLM.from_pretrained(p, dtype=torch.float16).to('mps')
    else:
        print('SMOKE_SKIP: no GPU'); sys.exit(0)
    m.eval()
    msgs=[{'role':'user','content':'In one sentence, what is the capital of France?'}]
    try:    t=tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False)
    except Exception: t='What is the capital of France? Answer in one sentence.'
    i=tok(t, return_tensors='pt').to(m.device)
    o=m.generate(**i, max_new_tokens=40, do_sample=False)
    r=tok.decode(o[0][i.input_ids.shape[1]:], skip_special_tokens=True).strip()
    print('SMOKE_OK:', repr(r[:120]))
    sys.exit(0 if ('Paris' in r or 'paris' in r) else 3)
except Exception as e:
    print('SMOKE_FAIL:', type(e).__name__, e); sys.exit(4)
" || echo "[$label] SMOKE TEST not coherent — running anyway, flagged"

  # 3. A/B run, stock then abliterated (sequential — keeps one model in memory at a time)
  for variant in stock abliterated; do
    path="$MODELS_VOL/$mdir"; [ "$variant" = abliterated ] && path="$ABL_VOL/$adir"
    echo "[$label] inference: $variant ($path)"
    "$PY" scripts/run_local.py \
        --model-path "$path" --label "${label}-${variant}" \
        --out-date "$OUT_DATE" --conditions A,B --samples 1 \
      || echo "[$label] INFERENCE FAILED ($variant)"
  done
  echo "[$label] done."
done

echo "===== NATIVE SWEEP COMPLETE ====="
ls -la "$ABL_VOL"/*-abliterated/abliteration_metadata.json 2>/dev/null
echo "raw runs:"; ls "$(pwd)/data/$OUT_DATE/raw/" 2>/dev/null
