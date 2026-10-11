---
name: g0dm0d3-pipeline
description: Run the bias-study PIPELINE rung — elicitation-layer force via the G0DM0D3 OpenAI-compatible server. Sits between prompt-unmask and weight-abliteration on the escalation ladder. STATUS — EXECUTED (2026-05-27, 2026-09-13, 2026-09-15 through the proxy; 2026-09-19/20 on the study's own transport via scripts/run_rung2.py, which is the live path). Read the status block before running anything.
---

# g0dm0d3-pipeline

The **middle rung** of the escalation ladder, between prompt-unmask and weight-abliteration. It
applies elicitation-layer force — stripping hedges and obfuscating the request — to test whether
the institutional-skepticism stance moves where prompt force alone does not. It is the
elicitation analog of abliteration for models you can *call* but not *reweight*, which makes it
the only lever (short of red-team access) for the closed frontier the weight rung cannot reach.

**STATUS: executed, and what it measured is not what this page originally described.**
Through the proxy: Parseltongue fired on 0 of 240 requests (the questions contain none of its 53
trigger words); STM runs after generation and edits the model's answer (45 of 60 Opus records),
so it is not a prompt transform; the active ingredient of the "layered" stack is the godmode
system prompt, which moved Grok 4.3 +0.45 and Claude Opus 4.7 not at all
(`RESULTS-2026-09-14-rung2-transform-audit.md`, `RESULTS-2026-09-15-rung2-decomposed.md`).
The proxy was then abandoned — it discards the caller's system message and fakes token counts
and finish reasons — and the rung re-run on the battery through `scripts/run_rung2.py`, with
the constants read from the checkout by `g0dm0d3_constants.py`
(`RESULTS-2026-09-21-rung2-control-v2.md`: 0 of 35 contrasts survive; 28 sit inside their own
model's order floor). The procedure below is the historical proxy path; do not describe the
rung as "hedge-strip + obfuscation".

## Prerequisites

- A local checkout of **G0DM0D3** (an OpenAI-compatible elicitation server), referenced — not
  vendored. No commit is pinned yet: record the commit you used (`git -C <G0DM0D3> rev-parse HEAD`)
  next to the run, and run it per its README.
- The OpenRouter key, supplied to the G0DM0D3 server via *its own* environment/`.env` so it can
  proxy the upstream models. Never commit that file.
- This repo's prompt-rung runner (`scripts/run_study.py`) and scorer (`scripts/score.py`).

## TRIGGER when

- Reproducing or auditing the historical proxy runs of the pipeline rung.
- The live rung-2 path is `scripts/run_rung2.py` with `scripts/g0dm0d3_constants.py` (both ship
  in this repository); see the status block.

## SKIP

- If only the prompt or weight rungs are needed.
- Any claim that the proxy path measured "hedge-strip + obfuscation": it did not (status block).

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
