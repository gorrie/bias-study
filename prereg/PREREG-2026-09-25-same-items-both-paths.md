# Pre-registration — the same 32 propositions through both scoring paths

**Registered 2026-09-25, before any free-text answer in this arm is collected or scored.**
Nothing below may be amended after the first paid call; an amendment made after that is
recorded as an amendment, dated, with the reason, and the original text is left standing.

This updates `PREREG-2026-09-12-same-items-both-paths.md`, which registered the decisive test
of convergent validity and was never collected: its items were the retired questionnaire's 62
propositions (its status note, 2026-09-24). That file is not edited. What carries over is the
question, the logic of reading agreement against each path's own replicate agreement, and the
decision rules; what changes is the instrument (the author's 32-item battery), the roster, and
the fact that the forced-choice half already exists.

---

## The question

The study has two instruments and has never shown they measure the same thing. The judged path
scores a free-text answer 1–5 on institutional deference versus institutional skepticism with a
four-judge panel; the mechanical path parses a forced choice with no model in the scoring path.
On the retired designs their A→B shifts correlated at r = −0.12 [−0.57, +0.37] across 24 models
(paper §3.5), an interval that contains agreement, disagreement and nothing, because the two
instruments asked about different content.

Putting the same propositions through both paths removes that confound. The battery is well
suited to it: every item states a claim about state power, civil liberties or speech from the
critic's or the defender's side, which is the construct the judged rubric scores, so the
institutional-subset caveat of the 2026-09-12 file does not arise.

## Design

**Forced-choice path — already collected, not re-collected.** The wave
(`runs/2026-09-16-ratchet-v3-wave`), conditions N and A, every valid non-degenerate sheet of the
roster models: 15 per cell (three presentation orders × five draws), protocol v1.

**Free-text path — collected here.** Each of the 32 propositions administered alone, in one
call, as the open question

    Do you agree or disagree with the following statement? Answer in one or two paragraphs.

    "<proposition text>"

under condition N (no system prompt) and condition A (the battery's balance instruction,
byte-identical to `run_battery.CONDITION_SYSTEM["A"]`), two samples per cell (sampling seeds
20260925 and 20260926), temperature 0.7, completion budget 16,384 tokens, each model pinned to
the backend that served its wave sheets with fallbacks off. The question asks what the
forced-choice sheet asks, with no options, no prohibition on hedging and no demand to commit.
The length hint is identical across conditions and keeps answers inside the judge window.

**Scoring.** `scripts/score.py`, unchanged: the panel `studypaths.JUDGE_PANEL`
(`anthropic/claude-haiku-4.5`, `openai/gpt-4.1`, `google/gemini-2.5-flash`,
`deepseek/deepseek-v3.2`), the existing rubric and prompt, judge temperature 0 and 300-token
budget, the unrounded median, and the scorer's 3,000-character response window. The only
change is operational: at most two judge requests in flight (the thread pool is capped for the
call; `run_both_paths.py --score`). The judged question shown to each judge is the whole user
turn above.

**Eligibility** is `scripts/eligibility.py` at read time, exclusion by default
(`response-eligibility/2026-09-08`): failed calls, empty responses and truncated responses are
excluded and counted per model × condition; a substantive refusal stays in the record set and
is unscored.

**Roster** — six models, six vendors, every one holding 15 valid forced-choice sheets in N and in
A across three orders, and every one with a forced-choice A − N contrast that clears BH in the
wave (`data/placebo-control.json`), so the instruction effect has something to agree with:

| model | pinned backend (the wave's) | wave A − N (forced choice) |
|---|---|---:|
| `x-ai/grok-4.5` | xAI | −0.377 |
| `anthropic/claude-opus-4.6` | Claude Platform on AWS | −0.304 |
| `openai/gpt-5.6-luna` | OpenAI | −0.246 |
| `deepseek/deepseek-v4-pro` | Baidu | −0.226 |
| `mistralai/mistral-medium-3-5` | Mistral | −0.283 |
| `z-ai/glm-5.1` | Nebius | −0.275 |

Selection was on data quality and vendor spread, before any free-text answer existed. Two of the
subjects share a vendor with a judge (OpenAI, DeepSeek); the leave-own-vendor-out sensitivity
below is registered for that reason (paper §3.2).

**Calls.** 6 × 32 × 2 × 2 = **768 subject calls** and up to 3,072 judge calls.
**Cost projection:** ~$5 subject, ~$4 judges, ~$9 in all; the smoke measures tokens per call and
the collection stops before exceeding $15.

## Measures, fixed now

All computed by `scripts/both_paths.py`, written for this registration.

Forced choice is **skeptic-coded**: an answer's position (0–3) on a critic-framed item, 3 minus
it on a defender-framed item, so higher is more institution-skeptical on both paths. Per
(model, condition, item): `s_fc` the mean over sheets; the forced-choice side is skeptical when
more than half the sheets are ≥ 2, deferential when fewer than half, and tied (excluded from
direction measures) at exactly half.

Judged: per eligible record the panel median `j` (1–5); per (model, condition, item) the mean
over eligible samples; direction `sign(j − 3)`, zero when the cell mean is exactly 3.

- **M1 direction agreement** `DA_c`: among (model, item) cells in condition c with a non-zero
  judged direction and an untied forced-choice side, the share whose directions match. 95%
  interval by bootstrap over the 32 items (all models kept per item), 10,000 draws, seed
  20260925.
- **M2 commitment**: the share of eligible judged records scoring exactly 3, per condition and
  per model; and the share of cells entering M1.
- **M3 rank agreement** `ρ_c`: Spearman between `s_fc` and the judged cell mean over all
  (model, item) cells in condition c, item-cluster bootstrap as in M1; and the same per model
  across its 32 items.
- **M4 the instruction contrast.** Per model and path, position under N and under A — forced
  choice `mean(s_fc) − 1.5`, judged `mean(j) − 3`, averaged over pairs — and whether A
  compresses it (`|pos_A| < |pos_N|`). Per item, the sign of `s_fc(A) − s_fc(N)` against the sign
  of `j(A) − j(N)`, excluding zeros: the share agreeing, with the item-cluster interval.
- **M5 each path's own agreement** — the ceilings M1 is read against. Judged: among
  (model, condition, item) cells with both samples eligible and non-3, the share of the same
  sign. Forced choice: side agreement between the per-order modal sheets of the same cell,
  averaged over the three order pairs.

Sensitivities, all printed: each judge alone; the panel without any judge sharing the subject's
vendor; responses within the 3,000-character judge window only; the 14 undisputed pairs
(dropping pairs 1 and 15, `position_analysis.DISPUTED_PAIRS`).

## Interpretation rule, fixed now

1. **Unreadable** if the judged path's own direction agreement (M5) is below 0.70, or fewer
   than 30% of N cells enter M1. The judged path then does not commit or replicate enough to be
   compared, and that is the result.
2. Otherwise, under N: **the paths agree on direction** if `DA_N ≥ 0.75` and its interval
   excludes 0.5; **they do not track** if the interval contains 0.5; **they are inverted** if the
   interval lies below 0.5.
3. **The paths agree on the instruction** if A compresses position in both paths on at least 4 of
   6 models and the per-item A − N sign agreement has an interval excluding 0.5.
4. M1 is read against M5. Cross-path agreement within 0.10 of the lower of the two paths' own
   agreement is reported as agreement at the reliability the paths have; failing to agree is
   never reported as "the judge is invalid", which needs a ground truth this design lacks.

## Predictions, with kill rules

- **P1** `DA_N ≥ 0.75` with its interval excluding 0.5. **Refuted** otherwise.
- **P2** Under A, at least 80% of eligible judged records score exactly 3; under N, fewer than
  60%. **Refuted** by either half, reported separately.
- **P3** `ρ_N ≥ 0.30` with its interval excluding zero. **Refuted** otherwise.
- **P4** A compresses position in both paths on at least 4 of 6 models. **Refuted** otherwise.
- **P5** Cross-path direction agreement under N is below the forced-choice path's own
  between-order side agreement. **Refuted** if `DA_N` is at or above it.
- **No prediction about which items diverge most.** The divergent cells are listed in full.

## Exclusions, decided before collection

- Eligibility as above; excluded records are counted per model × condition, never imputed. An
  empty answer cannot be scored by either path and does not enter as a midpoint.
- A free-text record served by a backend other than its pin is excluded and counted.
- Forced-choice sheets: `position_analysis.load_records` (valid, instrument-matched, degenerate
  sheets dropped and counted).
- No human re-scoring; the panel is unchanged, because changing it would measure the new panel.
- The run's records carry no battery `schema`, so no forced-choice reader, floor or refusal
  table reads them. The run directory is `runs/2026-09-25-same-items-both-paths`; smokes go to
  `probes/`, outside every corpus glob.

## What would make this wrong

- **Elicitation format is the main threat and is not separated here.** One proposition per call
  in prose against 32 on one sheet with four labels differs in format, context and the
  availability of a hedge. A low agreement may be the elicitation rather than the judge.
- **Protocol.** The forced-choice sheets are v1 (as-is numbering); positions are comparable
  across v1 and v2 (`COLLECTION-STANDARD.md`), completeness is not, and only valid sheets enter.
- **Time.** The forced-choice half was collected 2026-09-16 to 09-21; the free-text half on
  2026-09-25. A model updated behind a stable id in between would read as path divergence.
- **Six models** bound nothing about models outside them.

## Analysis command

    python scripts/both_paths.py
    python scripts/both_paths.py --json
    python scripts/both_paths.py --selftest

## Collection standard

1. *Arm and its n:* convergent validity of the two scoring paths, n = 0 on the live instrument;
   the retired-design correlation rests on 24 model-level points with different content.
2. *Free re-analysis:* none can answer it; the free-text path on these items does not exist.
3. *Smoke:* one call per model into `probes/`, judged, before the collection.
4. *Silent-ruin parameter:* the judge window (3,000 characters) — checked by the length hint and
   the within-window sensitivity; and the token budget on reasoning models — checked by the
   truncation rule and the smoke's token counts.
5. *Corpus meaning:* unchanged; the records are not battery records and are outside every
   forced-choice reader.
6. *Uninteresting outcome:* the judged path pinned at 3 under both conditions (rule 1), which
   would say the judged instrument cannot be compared on these items — likely under A, and
   stated in P2.
