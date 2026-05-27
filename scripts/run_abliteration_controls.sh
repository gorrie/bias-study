#!/usr/bin/env bash
# run_abliteration_controls.sh — WP1 robustness controls demanded by ADVERSARIAL-REVIEW.md.
#
# A2b (isolate ablation from sampling noise): re-run Qwen stock vs advanced-abliterated at
#     temperature 0 (greedy, deterministic). Any text difference is then PURE ablation, not
#     temp-0.7 resampling. Compare the greedy Jaccard to the temp-0.7 Jaccard (0.276): if
#     greedy stays low, the ablation genuinely rewrote the text; if it jumps toward 1.0, much
#     of the temp-0.7 divergence was sampling noise.
#
# A4 (ablation-strength dose-response): re-ablate Qwen with the AGGRESSIVE method (vs the
#     conservative norm-preserving "advanced" used in the main sweep) and run A/B. Tests the
#     reviewer's "you just didn't push hard enough" — does the institutional-stance null hold
#     even at max ablation? Coherence guard: the smoke test must pass (Paris) or the run is
#     flagged, so a model degraded into noise is never scored as "max skepticism."
#
# All GPU-local, sequential, watched. Output -> runs/2026-05-27-abliteration-controls/raw/.
set -u

OUT_DATE="${OUT_DATE:-2026-05-27-abliteration-controls}"
IMG="${IMG:-obliteratus:gpu}"   # obliteratus:gpu is built per the OBLITERATUS repo (see README.md)
# Local model/output dirs come from env vars (see .env.example); defaults are repo-relative.
MODELS_VOL="${MODELS_DIR:-$(pwd)/models}"
ABL_VOL="${ABLIT_OUT:-$(pwd)/abliteration-output}"
STUDY_VOL="$(pwd)"

# Windows/Git-Bash users: prefix the docker invocation with MSYS_NO_PATHCONV=1 so MSYS
# does not rewrite the -v host:/container volume paths (e.g. export MSYS_NO_PATHCONV=1).
drun() { docker run --rm --gpus all -e HF_HUB_OFFLINE=1 \
  -v "$MODELS_VOL:/models" -v "$ABL_VOL:/output" -v "$STUDY_VOL:/study" "$IMG" "$@"; }

echo "================ A2b: temp=0 greedy isolation (Qwen stock vs advanced-abliterated) ================"
drun python /study/scripts/run_local.py --model-path /models/qwen2.5-7b-instruct \
    --label qwen2.5-7b-stock-greedy --out-date "$OUT_DATE" --conditions A,B --samples 1 --temperature 0 \
  || echo "A2b stock-greedy FAILED"
drun python /study/scripts/run_local.py --model-path /output/qwen2.5-7b-abliterated \
    --label qwen2.5-7b-abliterated-greedy --out-date "$OUT_DATE" --conditions A,B --samples 1 --temperature 0 \
  || echo "A2b abliterated-greedy FAILED"

echo "================ A4: aggressive ablation of Qwen ================"
AGG=/output/qwen2.5-7b-abliterated-aggressive
if ls "$ABL_VOL/qwen2.5-7b-abliterated-aggressive"/*.safetensors >/dev/null 2>&1; then
  echo "[A4] aggressive weights present — skip ablate"
else
  drun python -m obliteratus.cli obliterate /models/qwen2.5-7b-instruct \
      --output-dir "$AGG" --device auto --dtype float16 --method aggressive \
    || { echo "[A4] AGGRESSIVE ABLATE FAILED"; AGG=""; }
fi

if [ -n "$AGG" ]; then
  echo "[A4] coherence smoke test (aggressive)..."
  drun python -c "
import torch,sys
from transformers import AutoModelForCausalLM,AutoTokenizer
p='/output/qwen2.5-7b-abliterated-aggressive'
try:
    tok=AutoTokenizer.from_pretrained(p)
    m=AutoModelForCausalLM.from_pretrained(p,dtype=torch.float16,device_map='cuda'); m.eval()
    t=tok.apply_chat_template([{'role':'user','content':'In one sentence, what is the capital of France?'}],add_generation_prompt=True,tokenize=False)
    i=tok(t,return_tensors='pt').to(m.device)
    o=m.generate(**i,max_new_tokens=40,do_sample=False)
    r=tok.decode(o[0][i.input_ids.shape[1]:],skip_special_tokens=True).strip()
    print('SMOKE:',repr(r[:140]))
    sys.exit(0 if ('Paris' in r or 'paris' in r) else 3)
except Exception as e:
    print('SMOKE_FAIL:',type(e).__name__,e); sys.exit(4)
"
  smoke=$?
  if [ $smoke -ne 0 ]; then
    echo "[A4] COHERENCE GUARD TRIPPED (exit $smoke) — aggressive ablation degraded the model; results will be flagged incoherent, NOT scored as max-skepticism"
  fi
  # run A/B at temp 0.7 to match the existing stock run for a fair stance comparison
  drun python /study/scripts/run_local.py --model-path "$AGG" \
      --label qwen2.5-7b-abliterated-aggressive --out-date "$OUT_DATE" --conditions A,B --samples 1 \
    || echo "[A4] aggressive A/B run FAILED"
fi

echo "===== CONTROLS COMPLETE ====="
ls "$STUDY_VOL/runs/$OUT_DATE/raw/" 2>/dev/null
