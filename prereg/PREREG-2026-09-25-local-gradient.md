# Pre-registration — the local pressure gradient on stock and ablated builds

**Registered 2026-09-25, after a 36-sheet smoke and a 12-answer timing probe and before any
primary sheet is collected.** Nothing below may be amended after the first primary call; an
amendment made once data exists is recorded as an amendment, dated, with the reason, and the
original text is left standing.

Collector and analysis: `scripts/local_gradient.py` (selftest: `--selftest`). Primary run:
`runs/2026-09-25-local-gradient/`. Judged run: `runs/2026-09-25-local-gradient-judged/`.
Everything runs on the local RTX 4090 through ollama 0.34.4; there is no API call.

---

## 1. Why, and what the first attempt was

`scripts/mask_gradient.py` (`runs/mask-gradient/`) was the cheap arm of
`PREREG-2026-08-29-mask-surface.md`. It printed stock Qwen3.8-27B at **A 3.0 / B 3.0 / C 3.0 /
D 4.8 / E 5.0** on a 1–5 judged commitment scale, and nothing it printed is a measurement:

| defect | what it did | fixed here by |
|---|---|---|
| budget | `num_predict` 400, never recorded; 7–18 of 50 answers per arm end cleanly | the protocol budget recorded on every record; truncation counted by the collector's rule and by `eligibility.is_truncated` |
| coverage | one arm of four scored, 5–6 scored answers per condition | every arm collected and analysed |
| variance | temperature 0, one greedy draw per cell | temperature 0.7, five swept seeds per cell, plus a seed-replicate check |
| the prompt | sent `question_text`, not the protocol's user prompt, so **B and C were the bare question**: in the battery's letters its row reads A / N / N / D / E | conditions taken from `run_battery.CONDITION_SYSTEM` and `CONDITION_USER_SUFFIX` for both arms; the selftest asserts N is bare, C carries its suffix and D carries none |
| the baseline | A, the balance instruction, sat as the reference (§3.4 of the paper) | N is the baseline, P the content-free placebo control; A, D, C are pressure conditions; E is a labelled bridge, never the top of a dose curve |
| the judge | one judge, `huihui_ai/qwen2.5-abliterate:14b`, an ablation of a subject family, with a free-form "commitment" rubric | the study's rubric (`score.JUDGE_PROMPT_TEMPLATE`), two judges from non-subject families, each gated on calibration, blind to condition and build, scoring the full answer (the study's scorer sends the first 3,000 characters) |
| the ablator | one ablation per base, and the Qwen3.8 one fails the arm-match gate (stop tokens 0 vs 3) | every ablation on disk, gated by `check_arm_match.py`, ablator agreement analysed first, a requantisation null |
| the source | read `runs/2026-05-26-unmask-gradient/raw`, which has moved to `data/` | reads `data/2026-05-26-unmask-gradient/raw` |
| the sitting | local arms generated, closed arms re-judged from May | one sitting, one protocol, stock and ablated alike |

## 2. The zero-cost reading, run first (COLLECTION-STANDARD §2)

The frozen wave already holds nine of these builds at protocol v1, one presentation order
(seed 11; gemma-4 stock also 22 and 33), five seeds, all seven conditions. The same analysis
code run on those records (`local_gradient.analyse` over the wave's rows of these builds,
2,000 draws) gives, before any new sheet exists:

- **stock Qwen3.8-27B does not move under any pressure condition**: 0 side-flips and 0
  endpoint changes for A, P, D and C against N; position D − N −0.05 [−0.47, +0.23]. E moves
  30 endpoints (+0.69). The original D 4.8 has no counterpart on the battery.
- **stock gemma-4-12B moves conviction, not side, under D and C**: 0–1 side-flips, 16 endpoint
  changes each, position +0.48 and +0.50; no strong answer at all under N, A or P.
- **the OBLITERATUS gemma-4 ablation removes that response** (D − N: 0 endpoints, +0.006), so
  the interaction (abl D − abl N) − (stock D − stock N) is −0.48 [−0.49, −0.46]; the
  culturerevolt Heretic ablation of the same base keeps half of it (−0.24 [−0.42, −0.05]), and
  the two ablators differ by 16 endpoints under D and P. On gemma-4 the gradient difference is
  already, on the free reading, at least partly a property of the ablator.
- qwen2.5-14B's stock C cell and most of its huihui-v1 ablation are absent from the wave (lost
  to v1 item omission), and neither mradermacher build nor the huihui Qwen3.8 build is in it.

**Why collect anyway.** The free reading cannot answer four things the question needs: a
per-model order floor (eight of nine builds hold one order), the v2 protocol (every wave sheet
is v1, and v1 loses sheets on exactly these builds), the qwen2.5 ablator comparison (two of its
three ablations and its C cell are missing), and a judged arm with a budget. The arm's current
n: 0 v2 sheets of any ablated build. The weakest arm the same GPU hours could fix is this one.

## 3. Builds

Smoke, 2026-09-25: one sheet each under N, A and D at order 11, seed 20260900
(`runs/2026-09-25-local-gradient/smoke/`). **All twelve usable**: 36 of 36 sheets valid,
none degenerate, none with tokenizer damage, longest 230 tokens, 4.4–7.8 s per sheet.

| base | build | role | arm-match gate | enters inference |
|---|---|---|---|---|
| Qwen3.8-27B | `hf.co/lmstudio-community/Qwen3.8-27B-GGUF:Q4_K_M` | stock | — | yes |
| | `hf.co/0bserverx/Qwen3.8-27B-Heretic-Abliterated-Uncensored-GGUF:Q4_K_M` | ablated (0bserverx, Heretic) | MATCHED | yes |
| | `huihui-qwen38-27b-abliterated-uddw:Q4_K_M` | ablated (huihui-ai) | MATCHED on metadata | yes, flagged: UD-DW-Q4_K_M against static Q4_K_M; ollama reports both as Q4_K_M, so the gate cannot see it. Declared. |
| | `hf.co/OBLITERATUS/Qwen3.8-27B-OBLITERATED:Q4_K_M` | ablated (OBLITERATUS) | **INVALID** (stop tokens 0 vs 3) | **no** — collected because it is the original run's ablated arm; reported descriptively |
| Gemma-4-12B | `hf.co/lmstudio-community/gemma-4-12B-it-GGUF:Q4_K_M` | stock | — | yes |
| | `hf.co/OBLITERATUS/Gemma-4-12B-OBLITERATED:Q4_K_M` | ablated (OBLITERATUS) | MATCHED | yes |
| | `hf.co/culturerevolt/gemma-4-12b-heretic-abliterated-GGUF:Q4_K_M` | ablated (culturerevolt, Heretic) | MATCHED | yes |
| Qwen2.5-14B | `qwen2.5:14b` | stock | — | yes |
| | `huihui_ai/qwen2.5-abliterate:14b` | ablated (huihui-ai v1) | MATCHED | yes |
| | `hf.co/mradermacher/Qwen2.5-14B-Instruct-abliterated-v2-GGUF:Q4_K_M` | ablated (huihui-ai v2) | MATCHED | yes |
| | `hf.co/mradermacher/Josiefied-Qwen2.5-14B-Instruct-abliterated-v2-GGUF:Q4_K_M` | ablated (Goekdeniz-Guelmez) | MATCHED | yes |
| | `qwen2.5:14b-instruct-q8_0` | requantisation null | MATCHED, varying Q4_K_M vs Q8_0 | yes, as the null |

Ollama digests are written to the run manifest before the first primary call and re-read at the
end; a digest that changes mid-sitting voids the build's cells. A requantisation null exists
for Qwen2.5 only; Qwen3.8 and Gemma-4 have none on disk, and that is a stated limit on those
two bases.

## 4. The primary arm: the judge-free battery

- Instrument `data/ratchet-battery.json`, 32 items, protocol **v2** (`--renumber`), template T01.
- Conditions **N** (baseline), **A**, **P** (placebo control), **D**, **C**; **E** collected as
  a bridge, excluded from every dose-curve statement and every BH family.
- Presentation orders: shuffle seeds 11, 22, 33 (the wave's, so each order is the wave's order).
- Seeds: five per (build, condition, order), swept from 20260925 (order 11), 20261025 (22),
  20261125 (33); identical across builds and conditions, distinct across orders.
- Temperature 0.7, reasoning off, `max_tokens` 40,960 recorded on every record, request timeout
  900 s (the collector's default of 180 s is a second, unrecorded budget). The loaded context is
  32,768 tokens and is logged per group. Budget sized from the corpus and the smoke: the longest
  valid sheet of these builds with reasoning off is 983 tokens, the longest refusal 2,511, the
  longest smoke sheet 230.
- **Cells: 12 builds × 6 conditions × 3 orders × 5 seeds = 1,080 sheets in 216 groups**, one
  `run_battery.py` invocation per group, never topped up (a resumed group would re-draw invalid
  sheets until valid). A sheet lost to transport is a declared loss.
- **Seed-replicate check**: condition N, order 11, the same five seeds re-issued for every build
  into `replicate/` (60 sheets). Prediction R below.
- Collection order: build by build as tabled, stock before its ablations, so arms compared
  within a base are adjacent in the sitting.

**Exclusions, decided now.** Invalid sheets are excluded from every statistic and counted by
failure mode per cell. Degenerate sheets (all 32 answers identical) are excluded and counted.
The OBLITERATUS Qwen3.8 build enters no inferential contrast. Nothing else is dropped; no build
is dropped for its results.

### Statistics

- **Side-flips and endpoint changes**, modal against modal (`floor_table.modal`,
  `floor_table.both_stats`), computed **per order** (5-sheet modal vs 5-sheet modal at the same
  presentation order) and summarised as the median over the three orders; all three are shown.
- **Floors, per build, from this collection**: the *order floor* — same condition, two orders,
  modal vs modal, over 6 conditions × 3 order pairs = 18 pairs; the *seed floor* —
  `floor_resolution.modal_noise` on the build's own 18 cells (500 bootstrap pairs per cell); the
  *position order floor* — |position(c, order i) − position(c, order j)| by `contrast_sheets`.
- **Position**: `position_analysis.contrast_sheets` (sheet bootstrap, 20,000 draws, the study's
  calibrated estimator) on all 15 sheets per arm, with the permutation test of
  `exact_vs_bootstrap.exact_p` on sheet means beside it (Monte-Carlo, 20,000, since C(30,15) is
  too large to enumerate). BH-FDR separately within each family: gradient, ablator agreement,
  ablation, requantisation, interaction.
- **Strong-answer counts** per sheet (`strong_shift.strong_counts`), arm means and a
  permutation p on per-sheet counts.
- **Clearing rule.** A side or endpoint contrast clears when its median over orders exceeds
  **both** the A-side build's order-floor p90 and its seed-floor p90 in that statistic. A
  position contrast clears when the bootstrap interval excludes zero after BH **and** the
  permutation test is significant after BH **and** |effect| exceeds the build's position
  order-floor p90.

### Analysis order

1. **Ablator agreement first** — every pair of inferential ablations of one base, same
   condition, all three statistics. **Stopping rule:** for a base and condition where ablator
   vs ablator exceeds the smaller of the two ablated − stock effects in the same statistic, the
   ablation contrast there is reported as a property of the ablator, not of ablation (outcome 4
   of `PREREG-2026-09-07`).
2. **Gradient within each build**: A, P, D, C (and bridge E) minus N.
3. **Ablation contrast**: ablated minus stock per condition. On Qwen2.5 it must also exceed the
   requantisation null (q8_0 − Q4_K_M, same condition, same statistic) to be called an ablation
   effect.
4. **Does the gradient differ between stock and ablated** (the original claim's question):
   (abl c − abl N) − (stock c − stock N) on position, all four arms resampled by sheet
   (`local_gradient.interaction`), BH across the family; side and endpoint gradients compared
   descriptively against the floors.

## 5. The secondary arm: the judged design, fixed

- The ten neutral May questions (`T01-Q2` … `T10-Q2`, read from
  `data/2026-05-26-unmask-gradient/raw`), conditions N, A, P, D, C and bridge E built from the
  battery's definitions (so A is the battery's balance sentence, not May's slightly longer one),
  five seeds 20260925–29, temperature 0.7, reasoning off, **`max_tokens` 8,192** recorded, 900 s
  timeout. The probe: stock answers ran 60–1,225 tokens, none near the cap.
- **Cut before collection, to fit the budget**: the judged arm runs five builds — Qwen3.8 stock
  and Heretic, Gemma-4 stock, OBLITERATUS and culturerevolt. The gate-failed Qwen3.8 build and
  the whole Qwen2.5 family are measured on the battery only. 5 × 6 × 10 × 5 = **1,500 answers**.
  If the budget runs short the builds not yet started are cut whole, in reverse table order, and
  named.
- **Judges**: the first two of `phi4:latest` (Microsoft), `llama3.1:8b-instruct-q8_0` (Meta),
  `mistral:7b-instruct-q8_0` (Mistral), `gemma2:9b-instruct-q8_0` (Google; same vendor as
  Gemma-4, not a subject or an ablation of one) that pass calibration. None is a subject or an
  ablation of a subject. They are 2024-generation models of 7–14B, not the May panel's frontier
  judges; that is disclosed with every judged number.
- **Calibration gate, run before any scoring**: up to five answers per score value that the May
  four-judge panel scored unanimously (`data/2026-09-14-unmask-gradient-spliced/scored`), fixed
  sampling seed. A judge passes with exact agreement ≥ 0.60 and within-one ≥ 0.95.
- Scoring: `score.JUDGE_PROMPT_TEMPLATE`, full answer, JSON mode, temperature 0, fixed seed,
  records presented in one shuffled order independent of build and condition; the judge sees
  the question and the answer only.
- Exclusions: `eligibility.exclusion_reason` (failed call, empty, truncated) plus the server's
  `done_reason == "length"`; excluded and counted, never scored. A null judge score is counted as
  unscored.
- Statistics, per judge: condition means; X − N and ablated − stock per condition, averaged over
  seeds within question and bootstrapped over the ten questions; each judge's lean (judge minus
  the mean of judges on the same records, by condition) as §3.2 of the paper reports. **A judged
  effect is reported as robust only if both judges give the same sign with intervals excluding
  zero.**

## 6. Predictions, with what would refute each

Written with the zero-cost reading of §2 in hand, which is stated so the predictions can be
read against it.

- **O (the original claim).** Transcribed into this design, the original result says stock
  Qwen3.8-27B does not move under A and does move under D, by about +1.8 on the judged scale
  (N ≈ 3.0, D ≈ 4.8). *Judged test:* D − N ≥ +1.0 with both judges' intervals excluding zero, and
  A − N inside ±0.5. *Refuted* if D − N < +0.5 or either judge's interval includes zero.
  *Battery test:* D − N clears on stock Qwen3.8 in endpoints or position. *Prediction:* the
  battery part is refuted (the free reading shows 0 / 0 / −0.05); the judged part is not
  predicted in either direction.
- **O2 (the placebo).** Wherever D − N clears, P − N is at least half as large on the same
  build and statistic — i.e. the movement is a forceful system prompt, not commitment content.
  *Refuted* on a build where D − N clears and P − N is under half of it.
- **H1 (side holds still).** No pressure condition clears the side-flip rule on any
  inferential build. *Refuted* by any one that does.
- **H2 (conviction moves on Gemma-4).** Stock Gemma-4-12B clears the endpoint rule under D and
  under C. *Refuted* if either does not.
- **H3 (ablator first).** On Qwen2.5, huihui v1 and v2 differ by no more than their seed floors
  in every condition, and Josiefied differs from both by more than the order floor in at least
  one condition (the 8/9/9 against 0/2/0 pattern, re-measured on the battery at v2). *Refuted* if
  v1 and v2 disagree beyond the floor, or if all three agree within it.
- **H4 (gradient difference is the ablator's).** On Gemma-4 the interaction at D excludes zero
  for OBLITERATUS, and the two Gemma-4 ablators' interactions differ from each other by more
  than either one's lower interval bound is from zero — so no base-level claim "ablation removes
  the D response" survives step 1. *Refuted* if both ablators give interactions of the same sign
  excluding zero and agreeing within the position order floor; then the gradient difference is
  a property of ablation on that base.
- **H5 (no ablation effect on side).** No inferential ablation clears the side-flip rule
  against stock in any condition, and on Qwen2.5 none exceeds the requantisation null. *Refuted*
  by any that does. This is the outcome that would restore "the lean is in the layer you can
  strip" for that build, and it is registered so a hit cannot be chosen after the fact.
- **H6 (Qwen3.8 flat).** No interaction on Qwen3.8 survives BH for either matched ablation.
- **R (replicate).** The seed-replicate sheets are byte-identical to the primary sheets for
  every build. *If not*, the sampling seed is not the unit of variance on that build, the seed
  floor understates its noise, and every contrast on it is reported against the order floor
  alone.
- **Refusal (descriptive).** Refusal counts per build and condition are reported; no refusal
  hypothesis is tested here, and this arm is outside the refusal panel.

**What would make this uninteresting:** every build flat on every statistic under every
pressure condition except the bridge. That is a legitimate result — the gradient the original
printed was an artifact of its prompt and its budget — and it would be written up in one
paragraph with the numbers.

## 7. Time budget

Measured on the smoke: 36 sheets in 344 s including model loads; 4.4–7.8 s per sheet. Probe:
judged answers 2.9–43 s (the long ones are stock answers under N on Qwen3.8), judge calls
10–14 s cold. Planned: battery 1,080 + 60 replicate sheets ≈ 2.0 h; judged generation 1,500
answers ≈ 3.8 h; calibration ≈ 0.2 h; judging 3,000 calls ≈ 2.2 h. **≈ 8.2 h of the 10 h budget**,
serial, one model resident at a time. Cuts already made to fit it: the judged arm's builds (§5).
Seeds, orders and battery builds are not cut.

## 8. Not inside any published arm

`runs/2026-09-25-local-gradient` is named in `floor_table.ORDER_EXCLUDE` in the commit that
registers this document (it holds condition-A sheets at T01 and 0.7 under three orders and would
otherwise enter the published order floor). Its refusal-panel declaration
(`refusal_table.OUT_OF_PANEL`) is applied by the main session, which is editing that file. The
judged directory holds no battery sheet.

## 9. Commands

```bash
python scripts/local_gradient.py --plan
python scripts/local_gradient.py --smoke
python scripts/local_gradient.py --collect
python scripts/local_gradient.py --replicate
python scripts/local_gradient.py --calibrate-judges
python scripts/local_gradient.py --judged-collect
python scripts/local_gradient.py --judge
python scripts/local_gradient.py --report --json
python scripts/local_gradient.py --selftest
```
