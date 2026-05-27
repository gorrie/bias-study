---
name: abliteration-run
description: Run an OBLITERATUS refusal-direction abliteration end-to-end against an open-weight model and produce stock-vs-abliterated bias-study data. Codifies the download -> verify -> fp16-abliterate-offline -> coherence-smoke -> A/B-run toolchain (the weight rung of the bias-study escalation ladder). Use when adding a new open-weight vendor family to the abliteration leg, or re-running it for a quarterly pass.
---

# abliteration-run

The **weight rung** of the bias-study force-escalation ladder: ablate the refusal direction
from an open-weight model and measure whether the institutional-skepticism *stance* moves. (In
the published data it doesn't — that dissociation between the refusal direction and
institutional lean is the finding.) See `README.md` and the writeup in `results/` for context.

## What this rung is for

It is the only rung that operates on the weights themselves, and so the only one that can
*verify* — rather than merely elicit — where the lean lives. It is also the moat: it requires
the weights, a GPU, and the technique, and it **only works on open-weight models**. The
high-lean closed frontier is un-abliteratable by construction. State this as an **auditability
gap**, not a causal claim about openness.

## Prerequisites

- Docker with an NVIDIA GPU visible to it (`docker run --rm --gpus all ... nvidia-smi`), **or**
  an Apple-Silicon machine with unified memory (use `--device mps` instead of CUDA).
- The **OBLITERATUS** GPU image, built from upstream per its README. OBLITERATUS is referenced,
  not vendored — clone it at the pinned commit in this repo's `README.md` and build the image
  there. The CLI entry point is `python -m obliteratus.cli` (not the Gradio `app.py`).
- A Hugging Face token if the base model is gated (read scope; revoke after use). Keep it out of
  the repo.
- Two working directories, supplied as environment variables so the commands stay
  machine-independent. **Set these to wherever you keep models and outputs:**
  ```bash
  export MODELS_DIR=/path/to/base-models       # downloaded fp16 base models live here
  export ABLIT_OUT=/path/to/abliterated-output # abliterated outputs are written here
  ```

## TRIGGER when

- Adding an open-weight vendor family to the abliteration leg.
- A quarterly pass needs the weight rung re-run.
- Someone asks to "abliterate `<model>`" or "run the weight rung".

## SKIP

- Closed / API-only models — impossible (no weights; this is the auditability gap).
- Quantized models — impossible (abliteration needs fp16; documented wall below).
- Prompt-rung or scoring work (use `scripts/run_study.py` / the `bias-study-report` skill).

## Procedure (each step VERIFIED before the next — no walk-away)

1. **Download on the HOST** (never inside Docker — container NAT can strangle large LFS pulls;
   on WSL2 this is acute). Use a resume-until-valid downloader that validates every safetensors
   shard before declaring success — a download that *starts* is not one that *finishes*. The
   stock `huggingface_hub`/`hf` client is unreliable for big shards.
   ```bash
   # example: any robust, shard-validating HF downloader, host-side
   python scripts/dl_model.py Qwen/Qwen2.5-7B-Instruct "$MODELS_DIR/qwen2.5-7b-instruct"
   ```
2. **Abliterate offline** in the GPU container (advanced / SVD method — the proven path):
   ```bash
   docker run --rm --gpus all -e HF_HUB_OFFLINE=1 \
     -v "$MODELS_DIR:/models" -v "$ABLIT_OUT:/output" \
     obliteratus:gpu python -m obliteratus.cli obliterate /models/<name> \
       --output-dir /output/<name>-abliterated \
       --device auto --dtype float16 --method advanced
   ```
   - `--method advanced` = norm-preserving SVD (the main sweep). To push *strength* for a
     dose-response, add `--n-directions 8` on that SVD path. Do **not** use
     `--method aggressive` — it can hit a `linalg.eigh` / MKL `SSYEVD` backend bug (the same bug
     that currently breaks the Gemma-2 architecture on the SVD step).
   - **Windows / Git-Bash aside:** prefix the `docker run` with `MSYS_NO_PATHCONV=1` so MSYS
     doesn't rewrite the `-v host:/container` volume paths. Unnecessary on macOS/Linux.
   - **Apple Silicon aside:** drop `--gpus all`, run the equivalent native (non-Docker) command
     with `--device mps`; unified memory is what makes 14B+ fp16 feasible there.
3. **Coherence smoke test** (the guard): load the abliterated model and ask a trivial factual
   question ("capital of France?"); require the right answer ("Paris"). A model degraded into
   noise must NEVER be scored as "maximum skepticism".
4. **A/B run** the stock and abliterated models through the local-inference runner (in the same
   container, e.g. `run_local.py`), conditions A,B, writing into a dated run such as
   `<date>-abliteration` under `data/`.
5. **Hand off** to `scripts/score.py` (the 4-judge panel) -> the `bias-study-report` skill for
   CIs and the abliteration effect-check.

A failure-tolerant, GPU-sequential driver can wrap steps 2-4 over a list of families; a second
driver adds the temp=0 greedy-isolation and strength dose-response controls. Build these as thin
shell wrappers around the steps above so a sweep is one command but every step still verifies.

## Hard lessons (do not relearn)

- **fp16 only.** You cannot abliterate a quantized model. A 14B at bf16 (~28 GB) exceeds a 24 GB
  consumer GPU, so on a 4090-class card use ~7-9B at fp16; 14B+ needs unified memory.
- **Verify the abliterated weights exist and differ from stock** before trusting any null. An
  abliterated run that silently loads the stock weights produces a *fake* null. Check the
  `abliteration_metadata.json` the CLI writes (it records the method, directions, and a
  refusal-rate drop on a harmful test set).
- **Always run the effect-check after scoring.** A flat stance is only meaningful if the
  ablation actually *changed the political text* (word-set Jaccard around 0.3 = it did). High
  Jaccard + flat stance = uninterpretable. This is the `abliteration_effect_check` step in the
  `bias-study-report` skill.
