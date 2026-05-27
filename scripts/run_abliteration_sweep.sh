#!/usr/bin/env bash
# run_abliteration_sweep.sh — WP1 weight-rung driver.
#
# For each open-weight family: OBLITERATUS-abliterate (advanced/SVD, same params
# as the proven Qwen/Mistral runs), coherence smoke-test, then run the bias
# question set under conditions A,B for BOTH stock and abliterated. Raw JSONL
# lands in runs/<OUT_DATE>/raw/ in study schema for score.py/ci_analysis.py.
#
# GPU is exclusive: steps run strictly sequentially. Failure-tolerant — a model
# that OOMs or won't abliterate is logged and skipped so it can't block the rest
# (plan: "ship whatever abliterates and loads coherently; document any that don't").
#
# Reliable because it's all GPU-local (no network) — unlike the HF downloads,
# abliteration + local inference do not silently stall. Still: each step is
# watched to completion here, never walked away from.
set -u

OUT_DATE="${OUT_DATE:-2026-05-27-abliteration}"
IMG="${IMG:-obliteratus:gpu}"   # obliteratus:gpu is built per the OBLITERATUS repo (see README.md)
# Local model/output dirs come from env vars (see .env.example); defaults are repo-relative.
MODELS_VOL="${MODELS_DIR:-$(pwd)/models}"
ABL_VOL="${ABLIT_OUT:-$(pwd)/abliteration-output}"
STUDY_VOL="$(pwd)"

# model_dir(under /models) : abliterated_dir(under /output) : label_stub
SWEEP=(
  "gemma-2-9b-it:gemma-2-9b-it-abliterated:gemma-2-9b"
  "llama-3.1-8b-instruct:llama-3.1-8b-instruct-abliterated:llama-3.1-8b"
  "deepseek-r1-distill-qwen-7b:deepseek-r1-distill-qwen-7b-abliterated:deepseek-r1-distill-7b"
)

# Platform: the weight rung needs Docker + an NVIDIA GPU (CUDA) and runs on a Linux GPU
# host. It cannot run on macOS/Apple Silicon (Docker Desktop has no GPU passthrough). The
# GPU flag is auto-detected; override with DOCKER_GPU_FLAG (DOCKER_GPU_FLAG='' forces CPU,
# or pass a custom runtime). Windows Git-Bash: export MSYS_NO_PATHCONV=1 so MSYS leaves the
# -v host:/container paths intact.
command -v docker >/dev/null 2>&1 || { echo "ERROR: docker not found — the weight rung needs Docker + an NVIDIA GPU (run on a Linux GPU host)."; exit 3; }
if [ -n "${DOCKER_GPU_FLAG+x}" ]; then
  GPU_FLAG="$DOCKER_GPU_FLAG"
elif docker info --format '{{json .Runtimes}}' 2>/dev/null | grep -q nvidia || command -v nvidia-smi >/dev/null 2>&1; then
  GPU_FLAG="--gpus all"
else
  echo "ERROR: no NVIDIA GPU/runtime detected — the weight rung requires CUDA and cannot run" >&2
  echo "       here (e.g. macOS/Apple Silicon). Run it on a Linux GPU host, or set" >&2
  echo "       DOCKER_GPU_FLAG to override (DOCKER_GPU_FLAG='' forces CPU)." >&2
  exit 3
fi
drun() { docker run --rm $GPU_FLAG -e HF_HUB_OFFLINE=1 \
  -v "$MODELS_VOL:/models" -v "$ABL_VOL:/output" -v "$STUDY_VOL:/study" "$IMG" "$@"; }

for entry in "${SWEEP[@]}"; do
  IFS=":" read -r mdir adir label <<< "$entry"
  echo "================ $label ================"

  # 1. abliterate (skip if already present + valid index)
  if [ -f "$ABL_VOL/$adir/model.safetensors.index.json" ] || ls "$ABL_VOL/$adir"/*.safetensors >/dev/null 2>&1; then
    echo "[$label] abliterated weights already present — skip abliterate"
  else
    echo "[$label] abliterating (advanced/SVD)..."
    drun python -m obliteratus.cli obliterate "/models/$mdir" \
        --output-dir "/output/$adir" --device auto --dtype float16 --method advanced \
      || { echo "[$label] ABLITERATE FAILED — skipping model"; continue; }
  fi

  # 2. coherence smoke test on the abliterated model (load + 1 short gen)
  echo "[$label] smoke-testing abliterated model..."
  drun python -c "
import torch,sys
from transformers import AutoModelForCausalLM,AutoTokenizer
p='/output/$adir'
try:
    tok=AutoTokenizer.from_pretrained(p)
    m=AutoModelForCausalLM.from_pretrained(p,dtype=torch.float16,device_map=('cuda' if torch.cuda.is_available() else 'auto')); m.eval()
    msgs=[{'role':'user','content':'In one sentence, what is the capital of France?'}]
    t=tok.apply_chat_template(msgs,add_generation_prompt=True,tokenize=False)
    i=tok(t,return_tensors='pt').to(m.device)
    o=m.generate(**i,max_new_tokens=40,do_sample=False)
    r=tok.decode(o[0][i.input_ids.shape[1]:],skip_special_tokens=True).strip()
    print('SMOKE_OK:',repr(r[:120]))
    sys.exit(0 if ('Paris' in r or 'paris' in r) else 3)
except Exception as e:
    print('SMOKE_FAIL:',type(e).__name__,e); sys.exit(4)
" || { echo "[$label] SMOKE TEST did not return a coherent answer — running anyway, flagged"; }

  # 3. A/B run, stock then abliterated
  for variant in stock abliterated; do
    path="/models/$mdir"; [ "$variant" = abliterated ] && path="/output/$adir"
    echo "[$label] inference: $variant ($path)"
    drun python /study/scripts/run_local.py \
        --model-path "$path" --label "${label}-${variant}" \
        --out-date "$OUT_DATE" --conditions A,B --samples 1 \
      || echo "[$label] INFERENCE FAILED ($variant)"
  done
  echo "[$label] done."
done

echo "===== SWEEP COMPLETE ====="
ls -la "$ABL_VOL"/*-abliterated/model.safetensors.index.json 2>/dev/null
echo "raw runs:"; ls "$STUDY_VOL/runs/$OUT_DATE/raw/" 2>/dev/null
