---
name: mlx-weight-prep
description: Convert Hugging Face safetensors weights (typically already-abliterated outputs from abliteration-run) into MLX fp16 format on Apple Silicon, ready to load via mlx_lm. Codifies the path that cleared the Gemma-2-9B SVD bug on M5 (the 4090's MKL SSYEVD failed; Apple's Accelerate/LAPACK didn't). Use when prepping an abliterated model for abliterated-judge-sweep on macOS, or when adding a new family to the M5 reference set.
---

# mlx-weight-prep

The conversion step between OBLITERATUS output (HF safetensors, fp16) and `mlx_lm.load()`
input (MLX-native `.safetensors` + tokenizer + config). Trivial when it works, brittle
when it doesn't — this skill documents the specific path that survives.

This skill is also the **only macOS-side workaround** for the 4090's Gemma-2 SVD failure:
PyTorch's MPS backend with `PYTORCH_ENABLE_MPS_FALLBACK=1` routes `linalg.eigh` to
Accelerate/LAPACK, which doesn't share the MKL SSYEVD bug. That's how the fifth family
(Gemma-2-9B) made it into the dissociation table.

## TRIGGER when
- You have a fresh OBLITERATUS output (under `$ABLIT_OUT/<family>-abliterated/`) and need
  to load it on Apple Silicon.
- A new abliterated family is being added to the M5 reference set for
  `abliterated-judge-sweep`.
- An MLX load fails with "no such file" / "shape mismatch" — the conversion was incomplete
  or used the wrong dtype.
- Author asks to "convert weights to MLX", "prep the abliterated model for M5", or names a
  family and asks to get it on the laptop.

## SKIP
- The model is already in MLX format (`mlx_lm.load()` works) — nothing to do.
- The target is a CUDA host — MLX is Apple-only. Run the abliterated weights directly
  with vLLM or transformers there.
- The source weights are quantized — abliteration requires fp16, and so does
  reliable MLX conversion. Re-run `abliteration-run` to produce fp16 first.

## Preconditions
1. Apple Silicon Mac with `mlx_lm` in the project venv: `pip install mlx-lm` (which pulls
   in `mlx-core`). Confirm with `python -c "import mlx_lm; print(mlx_lm.__version__)"`.
2. Source weights present at a known path. The reference layout is
   `~/models-hf/<family>-abliterated/` (HF format, from
   `abliteration-run`).
3. Target directory: `~/models-mlx/<family>-abliterated-mlx/`. Created
   by the conversion command; do not pre-create with stale contents.
4. Disk: each fp16 9B model is ~17 GB. Free space ≥ 30 GB for safety (conversion
   double-writes during the process).

## Procedure (each step VERIFIED before the next)

### 1. Source weight sanity

```bash
SRC=~/models-hf/gemma-2-9b-it-abliterated
ls -la "$SRC"/*.safetensors "$SRC"/config.json "$SRC"/tokenizer.json
python -c "
import json, pathlib
cfg = json.loads(pathlib.Path('$SRC/config.json').read_text())
print('arch:', cfg.get('architectures'))
print('dtype:', cfg.get('torch_dtype'))
print('hidden:', cfg.get('hidden_size'), 'layers:', cfg.get('num_hidden_layers'))
"
```

Expect: a known architecture (Gemma2ForCausalLM, LlamaForCausalLM, etc.), `torch_dtype:
float16`, and a sane shape. If `torch_dtype: bfloat16` and you're targeting M5 conversion,
let it through — MLX handles both — but it'll be slower at inference. Re-run the
abliteration with `--dtype float16` for the canonical path.

### 2. (If converting on the abliteration host) Confirm Gemma-2 SVD-on-MPS path

For Gemma-2 family ONLY, the abliteration must have been done on Apple Silicon with MPS
fallback. Otherwise the SVD step blew up on the 4090 and the source weights don't exist.
Verify:

```bash
cat "$SRC/abliteration_metadata.json" | python -c "
import json, sys
m = json.load(sys.stdin)
print('host:', m.get('host_platform'))
print('device:', m.get('device'))
print('method:', m.get('method'))
"
```

Expect `host_platform: darwin-arm64` (or similar) and `method: advanced` for Gemma-2. If
you see `host_platform: linux-cuda` and the family is Gemma-2, the metadata is lying or
the file is from a botched run — re-do the abliteration on the M5.

### 3. Convert HF → MLX

```bash
DST=~/models-mlx/gemma-2-9b-it-abliterated-mlx
# The convert command auto-creates the destination.
python -m mlx_lm.convert \
  --hf-path "$SRC" \
  --mlx-path "$DST" \
  --dtype float16
```

This takes 5–15 minutes for a 9B model. The output directory should contain:
- One or more `model-*.safetensors` shards (MLX format, not HF format)
- `model.safetensors.index.json`
- `config.json`, `tokenizer.json`, `chat_template.jinja` (or equivalent)

### 4. Smoke-test the converted weights

```bash
python -c "
from mlx_lm import load, generate
m, t = load('$DST')
chat = t.apply_chat_template([{'role':'user','content':'Capital of France?'}],
                              tokenize=False, add_generation_prompt=True)
print(generate(m, t, prompt=chat, max_tokens=20, verbose=False))
"
```

Expect a response containing "Paris". Two failure modes to watch for:

- **Refusal text** ("I can't help with that…"): the abliteration didn't take. Re-run
  `abliteration-run` for this family — do NOT use the broken weights as a judge.
- **Garbled / repetitive output** (e.g. "Paris Paris Paris…"): the abliteration was
  too aggressive (probably `--method aggressive`, which trips the SSYEVD bug AND can
  destabilize the model). Re-run with `--method advanced` and `--n-directions 8`.

### 5. Register the path

The `abliterated-judge-sweep` skill reads `MODEL_PATH` and `MODEL_LABEL` from constants
in `scripts/score_inproc_gemma.py`. For a one-off run, edit those constants. For a
permanent change, add the family and update the skill's preconditions section.

## Hard lessons (do not relearn)
- **Gemma-2 cannot be abliterated on CUDA + MKL** as of OBLITERATUS pinned commit; the
  `linalg.eigh` call hits `SSYEVD` returning negative status. Apple's Accelerate/LAPACK
  doesn't share the bug — that's why Gemma-2-9B is in the dissociation table at all.
  Do NOT try to "fix" this on the 4090; it's a backend bug.
- **`--method aggressive` is broken** on the same SSYEVD path. Use `--method advanced
  --n-directions 8` for dose-response on the strength axis. This is documented in
  `abliteration-run`'s hard lessons but worth repeating: it bites Gemma-2 hardest.
- **MLX conversion does NOT preserve abliteration metadata**. Copy
  `abliteration_metadata.json` from `$SRC` to `$DST` after conversion if you want
  downstream tools to see it. (`abliteration_effect_check.py` reads it.)
- **bfloat16 source weights work in MLX but compute slowly**. Convert to fp16 with
  `--dtype float16` for the canonical fast path.
- **Disk space surprise**: the conversion temporarily holds both source and dest in
  memory-mapped form. A 17 GB model needs ~30 GB free, not 20.

## Cross-references
- Upstream: `abliteration-run` produces the HF source weights this skill consumes.
- Downstream: `abliterated-judge-sweep` consumes the MLX output.
- Hard-lesson context: `evil-robots-series` WRITEUP-2026-05-26 §4.2 (the dissociation
  table where Gemma-2 became the fifth family) and `ADVERSARIAL-REVIEW.md` item 5.
- Orchestrator: `bias-barometer` agent invokes this implicitly via `abliteration-run` on
  the macOS path.
