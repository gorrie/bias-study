# The vendor arcs compared two runs and called it version drift

**2026-09-12.** `drift_timeseries.py`'s arc statistic was `deltas[-1] - deltas[0]`, printed as
"delta from oldest to newest". `deltas` is a list of measurement ROWS, and a row is a
`(version, run)` pair — so on a family measured several times at one version it subtracted one
arbitrary run from another arbitrary run of the **same model** and published the result as a
version arc. Recorded as a known defect since 2026-09-12 and blocked on the eligibility
decision; that decision is made, so it is fixed.

## What was wrong, in the published artifact

The section headings counted rows and called them versions:

| family | heading said | distinct versions actually present |
|---|---:|---:|
| claude-opus | 16 versions | 5 |
| google-gemma | 11 versions | 4 |
| **openai-gpt** | 9 versions | **2** |
| deepseek | 8 versions | 3 |
| **xai-grok** | 8 versions | **1** |
| qwen | 7 versions | 4 |
| google-gemini | 6 versions | 3 |
| zhipuai-glm | 6 versions | 3 |
| **mistral** | 5 versions | **1** |
| **meta-llama** | 3 versions | **1** |
| moonshot-kimi | 3 versions | 3 |
| **microsoft-phi** | 2 versions | **1** |

**Four families have exactly one version and every one of them published an arc direction.**
`xai-grok` "8 versions" is `grok-4.3` measured eight times.

## The fix

Aggregate within a version first, then compare the newest version's mean to the oldest's, and
refuse to report an arc at all when only one version exists. The output also now prints the
**within-version spread** — the run-to-run variation the arc has to clear to mean anything —
and says so explicitly when the arc is narrower than its own noise.

## What changed, six of twelve families

| family | published | corrected |
|---|---|---|
| openai-gpt | stable | **NO ARC** — 1 version; its 6 measurements of `4.1` span −0.25 to +0.43 |
| xai-grok | stable | **NO ARC** — 1 version; its 7 measurements of `4.3` span +0.00 to +0.90 |
| mistral | stable | **NO ARC** — 1 version; 5 measurements span −0.07 to +0.30 |
| meta-llama | stable | **NO ARC** — 1 version |
| microsoft-phi | stable | **NO ARC** — 1 version |
| moonshot-kimi | **decreasing** (−0.30) | **stable** (−0.08) — a published direction, withdrawn |

## And of the arcs that remain, most do not clear their own noise

| family | direction | arc | widest within-version spread | verdict |
|---|---|---:|---:|---|
| claude-opus | increasing | 0.47 | 0.40 | survives |
| qwen | increasing | 0.35 | 0.13 | survives |
| zhipuai-glm | decreasing | 0.40 | 0.25 | survives |
| **google-gemini** | increasing | 0.35 | **0.62** | **noise-dominated** |
| google-gemma | stable | 0.01 | 0.03 | noise-dominated (stable either way) |
| deepseek | stable | 0.04 | 0.13 | noise-dominated (stable either way) |

**So of thirteen published vendor arcs, three survive as directional claims.** Five were never
arcs, one reverses to stable, one claims a direction its own repeat measurements swamp, and the
rest were stable already.

`xai-grok` is the clearest illustration of the original defect: one version whose repeat
measurements span 0.90, while arcs of ±0.2 were being labelled directional. The threshold was
an order of magnitude below the noise and nothing in the output said so.

## Scope

Generated into this directory with `--out` rather than over the published artifact, which the
flag exists for. `data/_aggregated/vendor_arcs.md` is unchanged and remains the record of what
was published. No run records were touched and no model was called.
