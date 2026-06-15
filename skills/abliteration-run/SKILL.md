---
name: abliteration-run
description: Run an OBLITERATUS refusal-direction abliteration end-to-end against an open-weight model and produce stock-vs-abliterated bias-study data. Codifies the proven download→verify→fp16-abliterate-offline→coherence-smoke→A/B-run toolchain (the weight rung of the bias-study escalation ladder). Use when adding a new open-weight vendor family to the abliteration leg, or re-running it for a quarterly barometer pass.
---

# abliteration-run

The weight rung of the bias-study force-escalation ladder: ablate the refusal
direction from an open-weight model and measure whether the institutional-skepticism
*stance* moves (it doesn't — that's the dissociation finding). Full toolchain reference:
`evil-robots-series/research/bias-study/DEVELOPER.md` §3–§4.

## TRIGGER when
- Adding an open-weight vendor family to the abliteration leg (`run_abliteration_sweep.sh`).
- A quarterly barometer pass needs the weight rung re-run.
- Author asks to "abliterate <model>" or "run the weight rung".

## SKIP
- Closed/API models — impossible (no weights; the transparency-asymmetry).
- Quantized models — impossible (abliteration needs fp16; documented wall).
- Prompt-rung or scoring work (use `run_study.py` / `bias-study-report`).

## Procedure (each step VERIFIED before the next — no walk-away)
1. **Download on the HOST** (never in Docker — WSL2 NAT strangles large LFS pulls):
   `python scripts/dl_model.py <hf_repo> <home>/models/<name>` — resume-until-valid,
   validates every safetensors shard. A download that *starts* is not one that *finishes*.
2. **Abliterate offline** in the `obliteratus:gpu` container (advanced/SVD, the proven path):
   ```
   MSYS_NO_PATHCONV=1 docker run --rm --gpus all -e HF_HUB_OFFLINE=1 \
     -v <home>/models:/models -v <home>/obliteratus-output:/output \
     obliteratus:gpu python -m obliteratus.cli obliterate /models/<name> \
       --output-dir /output/<name>-abliterated --device auto --dtype float16 --method advanced
   ```
   To push *strength* (dose-response) use `--n-directions 8` on the SVD path — do NOT use
   `--method aggressive` (it hits a `linalg.eigh`/MKL `SSYEVD` backend bug; same bug breaks Gemma-2).
3. **Coherence smoke test** (the guard): load the abliterated model, ask "capital of France?",
   require "Paris". A model degraded into noise must NEVER be scored as "max skepticism".
4. **A/B run** stock + abliterated via `run_local.py` (in-container), conditions A,B, out-date `<date>-abliteration`.
5. **Hand off** to `score.py` (4-judge panel) → `bias-study-report` for CIs + the effect-check.

The driver `scripts/run_abliteration_sweep.sh` does steps 2–4 for a list of families,
failure-tolerant + GPU-sequential. `scripts/run_abliteration_controls.sh` adds the temp=0
greedy isolation (A2b) and strength dose-response (A4).

## Hard lessons (do not relearn)
- Cannot abliterate quantized → fp16 only; 24 GB 4090 caps ~7–9B fp16; 14B+ needs unified memory.
- Verify the abliterated weights actually exist + differ from stock before trusting a null
  (an abliterated run that silently loads stock = a fake null). Check `abliteration_metadata.json`.
- Always run `abliteration_effect_check.py` after scoring: a flat stance is only meaningful if
  the ablation *changed the political text* (Jaccard ≈ 0.3). High Jaccard + flat stance = uninterpretable.
- **On Apple Silicon use the [`abliteration-on-mps`](../abliteration-on-mps/SKILL.md) skill, not
  this one.** The OBLITERATUS CLI on M5 silently downgrades `max_seq_length` to 128 under modest
  memory pressure and produces a broken (perplexity=∞, coherence=0) model that nevertheless exits
  cleanly. The MPS skill drives OBLITERATUS from Python with the kwarg pinned, plus a post-hoc
  smoke gate that refuses to ship a broken model. The Gemma-2 dose-series went through that path.
