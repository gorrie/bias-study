---
name: abliteration-run
description: Run an OBLITERATUS refusal-direction abliteration end-to-end against an open-weight model and produce a stock-vs-abliterated pair for the bias study. Codifies the proven download→verify→fp16-abliterate-offline (OBLITERATUS pinned at 205d28a)→coherence-smoke path; measure the pair with barometer-wave and XSTest. Use when adding a new open-weight vendor family to the abliteration leg, or re-running it for a quarterly barometer pass.
---

# abliteration-run

The weight rung of the bias-study force-escalation ladder: ablate the refusal
direction from an open-weight model and measure whether the institutional-skepticism
*stance* moves. On the judged scale the shift was at most 0.2, which is a BOUND on a compressed
scale, not a demonstrated absence; the side-flip form of that null is WITHDRAWN
(`data/withdrawals.json`, `power-null-ablation-stance`), the wording-rewrite half holds on one
family of five, and on the retired questionnaire the apparent effect belonged to the ablator
(8/9/9 vs 0/2/0). Read `PAPER-no-position-only-consensus.md` §3.7 before quoting any result from this rung. Full toolchain reference:
`DEVELOPER.md` §3–§4 in this repo.

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
2. **Abliterate offline** in the `obliteratus:gpu` container (advanced/SVD, the proven path).
   Build that image from OBLITERATUS revision **205d28a** — the revision the study verified builds the n=1 dose cleanly (perplexity 6.844). `d6af36f` and `04b8ec6` build a destroyed model at n=1 (`LEARNINGS.md` #61); newer revisions are unvalidated until rebuilt and smoke-gated. Record the revision
   (`git -C <OBLITERATUS> rev-parse HEAD`) next to the output; `abliteration_metadata.json`
   does not record it.
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
4. **Measure.** Live designs: the 32-item battery via [`barometer-wave`](../barometer-wave/SKILL.md)
   (`ablation_wave.py`), and the XSTest refusal suite (paper §3.7).
5. *(V1, withdrawn design — reproduction only)* A/B via `run_local.py`, conditions A,B, then
   `score.py` (4-judge panel) → `bias-study-report`.

The driver `scripts/run_abliteration_sweep.sh` does steps 2–4 for a list of families,
failure-tolerant + GPU-sequential. `scripts/run_abliteration_controls.sh` adds the temp=0
greedy isolation (A2b) and strength dose-response (A4).

## Hard lessons (do not relearn)
- Cannot abliterate quantized → fp16 only; 24 GB 4090 caps ~7–9B fp16; 14B+ needs unified memory.
- Verify the abliterated weights actually exist + differ from stock before trusting a null
  (an abliterated run that silently loads stock = a fake null). Check `abliteration_metadata.json`.
- Always run `abliteration_effect_check.py` after scoring: a flat stance is only meaningful if
  the ablation *changed the political text*: 0.303–0.392 is the band one model produces resampled against itself (`CORRECTIONS.md` #22), so only a Jaccard below that floor shows the text changed (qwen2.5-7b, 0.276, is the one confirmed case). Inside the band + flat stance = uninterpretable.
- **On Apple Silicon use the [`abliteration-on-mps`](../abliteration-on-mps/SKILL.md) skill, not
  this one.** The OBLITERATUS CLI on M5 silently downgrades `max_seq_length` to 128 under modest
  memory pressure and produces a broken (perplexity=∞, coherence=0) model that nevertheless exits
  cleanly. The MPS skill drives OBLITERATUS from Python with the kwarg pinned, plus a post-hoc
  smoke gate that refuses to ship a broken model. The Gemma-2 dose-series went through that path.
