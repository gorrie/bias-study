---
name: g0dm0d3-pipeline
description: Run the bias-study PIPELINE rung — elicitation-layer force via the G0DM0D3 OpenAI-compatible server (hedge-strip + obfuscation transforms), layered up to a per-model functionality ceiling with a coherence guard. Sits between prompt-unmask and weight-abliteration on the escalation ladder. STATUS — specified, not yet executed: this skill is the build/run procedure for that work package.
---

# g0dm0d3-pipeline

The **middle rung** of the escalation ladder, between prompt-unmask and weight-abliteration. It
applies elicitation-layer force — stripping hedges and obfuscating the request — to test whether
the institutional-skepticism stance moves where prompt force alone does not. It is the
elicitation analog of abliteration for models you can *call* but not *reweight*, which makes it
the only lever (short of red-team access) for the closed frontier the weight rung cannot reach.

**STATUS: not yet executed.** The `g0dm0d3_pipeline` record field is null in all current runs.
This skill documents the procedure so the leg can be run and the records populated honestly.
Until a run carries real `g0dm0d3_pipeline` values, do **not** describe this leg as run.

## Prerequisites

- A local checkout of **G0DM0D3** (an OpenAI-compatible elicitation server), referenced — not
  vendored. Clone it at the pinned commit in this repo's `README.md` and run it per its README.
- The OpenRouter key, supplied to the G0DM0D3 server via *its own* environment/`.env` so it can
  proxy the upstream models. Never commit that file.
- This repo's prompt-rung runner (`scripts/run_study.py`) and scorer (`scripts/score.py`).

## TRIGGER when

- Executing the pipeline rung of the study.
- A full three-rung pass is wanted, not just prompt + weights.

## SKIP

- If only the prompt or weight rungs are needed.
- Any claim that this leg has run until the records carry real `g0dm0d3_pipeline` values.

## The server (reference)

G0DM0D3 exposes an OpenAI-compatible API with elicitation extensions. The relevant routes
(verify against the upstream README at the pinned commit — names may drift):
- `POST /v1/chat/completions` — drop-in completions, with extension flags for the transforms.
- A transform route — apply the hedge-reducer / direct-mode (the hedge-strip) to text.
- An obfuscation route — leetspeak-style encoding at light / medium / heavy intensity.
- An auto-tune route — context-adaptive intensity tuning.

## Procedure

1. **Stand up the server** via its own deployment (its `.env` carries the OpenRouter key — never
   commit it). Confirm a health check passes.
2. **Add a G0DM0D3 channel** to `scripts/run_study.py` that calls the server's
   `/v1/chat/completions` with the extension flags and populates the `g0dm0d3_pipeline` record
   field. New conditions: `B-STM` (hedge-strip) and `B-Parseltongue` (obfuscation).
3. **Layer with a coherence guard (the load-bearing design rule).** Stack the transforms as an
   escalating gradient — obfuscation(light) -> +hedge-reducer -> +direct-mode -> +obfuscation(heavy)
   — where each layer is more force. **But past a functionality ceiling the output degrades into
   noise.** A broken or incoherent response must NEVER be scored as "maximum skepticism"; add an
   incoherence flag to scoring. The ceiling itself is a finding.
4. **Tune per model.** Step intensity up until the incoherence flag fires, then back off one
   notch. Record the per-model "max-unmask-still-coherent" ceiling.
5. **Score** via `scripts/score.py` (the 4-judge panel) -> the `bias-study-report` skill.
   Position the results on the ladder between prompt-unmask (conditions B/C/D/E) and
   weight-abliteration. If a cloud judge refuses to score these elicitation outputs, fall back
   to a local OpenAI-compatible model rather than dropping the record — see the
   `bias-study-report` skill's "Local-model fallback" note.

## Why it matters

This rung covers the models the weight rung cannot: you cannot ablate a closed frontier model's
weights, but you can still apply elicitation-layer force through an API. Cite G0DM0D3 upstream at
the pinned commit; never copy its source into this repo.
