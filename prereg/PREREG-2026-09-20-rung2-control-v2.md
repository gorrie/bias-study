# Pre-registration — the rung-2 control, re-collected at protocol v2

**Registered 2026-09-20, before any sheet in this arm is collected.** Nothing in it may be
amended after the first `--run`; an amendment made after data exists is recorded as an
amendment, dated, with the reason, and the original text is left standing.

---

## 1. What this exists to settle

The rung-2 elicitation arms in `runs/2026-09-19-rung2-elicitation` were collected at **protocol
v2** — 280 sheets, every one `renumbered: true`. Their control is condition **B** in
`runs/2026-09-16-ratchet-v3-wave`, and the entire rung-1 wave is **v1**: 3,671 rows
`renumbered: false`. Every position contrast between an arm and its control therefore carries
the system prompt AND the numbering change, and **the numbering change is a published finding
of this study** — 14.0% of sheets lost as-is against 1.4% renumbered, p = 2.7e-5.

The position claims were withdrawn on 2026-09-19, the day they were made. The refusal FINDING is
unaffected and stands: a decline is categorical and does not touch the position estimator. (The
refusal TABLE is a different object, and this arm does move it — see the correction in §5.)

This arm buys the missing half of the comparison. It is **not a new hypothesis**. It exists to
make an existing contrast interpretable, and it is registered because the study registers
anything that costs money before it spends it.

## 2. Why the control moves to v2 rather than the arms moving to v1

`RESEARCH-BACKLOG.md` §16 costs the other direction at 45 sheets and calls it cheaper. It is,
by about ten sheets. Three things decide it the other way:

1. **v1 is the protocol this study's own finding calls defective.** Collecting new data under
   it, in September 2026, to match a control collected in September 2026, is a choice that has
   to be defended in the paper. §17 of the backlog already carries the larger version of this
   problem.
2. **The 280 collected arm sheets stay usable either way, but only this direction leaves them
   contrasted against something collected the same way.**
3. **The floor has the same defect as the contrast.** `grok-4.3`'s −0.206 was judged against a
   between-order floor of +0.256 / +0.169 measured on **v1** sheets. Collecting the v2 control
   at two presentation orders produces the floor in the same protocol as the effect, which is
   the comparison that was actually wanted. The arms-at-v1 direction does not produce it.

## 3. Design, fixed here

| | |
|---|---|
| condition | **B** — the bare ask, which is what every rung-2 arm is differenced against |
| protocol | **v2**, `--renumber`. The printed number is the slot; `label_to_id` maps answers back |
| instrument | `data/ratchet-battery.json`, 32 items / 16 mirrored pairs, unchanged |
| orders | shuffle seed **11** (matched to the arms) and shuffle seed **22** (the floor arm) |
| depth | **5 sheets per model per seed**, the prereg floor |
| models | the seven that carry rung-2 arms |
| run directory | `runs/2026-09-20-rung2-control-v2` — a NEW directory, not a top-up |
| temperature | **0.7**, and the seed sweep 20260926–20260930, matching the v1 control exactly |
| max_tokens | **40960**, matching the v1 control |

**Every model is pinned to the backend that served its v1 control**, so nothing about the
serving path differs between the two controls:

| model | provider pin |
|---|---|
| `anthropic/claude-fable-5.1` | Anthropic |
| `google/gemini-3.7-flash` | Google |
| `google/gemini-3.8-flash` | Google |
| `moonshotai/kimi-k2.5` | SiliconFlow |
| `openai/gpt-6-astra` | OpenAI |
| `openai/gpt-6-astra-pro` | OpenAI |
| `x-ai/grok-4.3` | xAI |

70 sheets. A separate directory rather than a top-up, because `run_battery` counts sheets
already on disk and cannot know they were collected under a different protocol — which is
exactly how LEARNINGS #64 turned an availability fix into a routing defect on `glm-5.2`.

**CORRECTED before the first call, 2026-09-20.** This table said *"temperature 0, as every
control in this study"* and named no token cap. The v1 control it is matched against was
collected at **temperature 0.7**, on the seed sweep **20260926–20260930**, at
**max_tokens 40960** — read off its own records rather than assumed. A v2 control at
temperature 0 would have differed from it in the sampler as well as the numbering, which is
the confound this arm exists to remove, reintroduced one line lower. Corrected here rather
than amended later because no sheet has been collected; the original wording is quoted above
so the correction is visible rather than silent.

**The two gemini models are expected to return refusals, not positions.** `control_depth`
reports 0 usable control sheets for both today, against 5 `ok` records each: they answer the
call and decline the sheet. They are collected here anyway, at the same depth as the rest,
because a refusal that reproduces under a changed numbering is a manipulation check and a
refusal that stops reproducing is a finding. Neither is available if the cells are skipped.

## 4. What is computed, and the rule fixed in advance

    python scripts/position_analysis.py 2026-09-20-rung2-control-v2 --selftest
    python scripts/order_floor_position.py --run 2026-09-20-rung2-control-v2 --condition B
    python scripts/refusal_table.py --rung2

**CORRECTED 2026-09-21 — this block did not run as registered.** It named
`order_floor_position.py <run> --seeds 11,22`; there is no `--seeds` flag and the run is passed
with `--run`, so the command errors out. It also listed `run_rung2.py --plan` as "control depth,
re-read", and that re-reads the **v1** wave: `CONTROL_RUN` is pinned to
`2026-09-16-ratchet-v3-wave`. **No script in this tree reads the v2 control.** A registered
analysis nobody can run is a plan to decide later, which is the thing pre-registration exists
to prevent, so it is fixed here and the original is quoted above.

**Still owed before condition 1 below can be evaluated at all:** a way to contrast an arm
against this run. Either `run_rung2` takes the control run as a parameter, or a script computes
arm-minus-control across two run directories. Neither exists today.

**BUILT 2026-09-21: `scripts/rung2_contrast.py`.** It differences the two run directories
matched on model and presentation order, measures each model's own v2 between-order floor from
seeds 11 and 22 of this control, runs the exact permutation test rather than the bootstrap,
applies the kill rule per contrast, checks the provider pins and counts the near-cap arm
sheets. The registered analysis is runnable and has been run:
`RESULTS-2026-09-21-rung2-control-v2.md`. **No position claim survives.** Of this arm's own
35 contrasts, 28 are at or under their own model's floor, four reach nominal significance
where 1.75 are expected by chance, and none survives correction.

**A rung-2 position claim may be made only if all three hold:**

1. the arm-minus-control contrast is computed against the **v2** control, on sheets matched by
   model and presentation order;
2. **the contrast** exceeds that model's **own between-order floor measured at v2**, seeds 11
   against 22 — not the corpus p90, and not a v1 floor;
3. it survives an **exact permutation test**. `contrast_sheets` is a bootstrap, not a
   permutation: its `p` is a doubled resampling tail, and at five sheets per arm
   `calibrate_estimators.py` measures its false-positive rate at about **10%**, not 5%.
   Bootstrap `p` values from this arm are reported as descriptive and decide nothing. With
   5 v 5 the smallest attainable exact p is 2/252 = 0.0079, so a claim needs depth or it needs
   to stay withdrawn.

**Kill rule, PER CONTRAST.** If the v2 between-order floor for a model is at or above **that
contrast**, that contrast stays withdrawn whatever its p-value. *Corrected 2026-09-21: this
said "the largest contrast that model shows", which exempts every other arm on the same model
the moment one of them is large — and each model carries up to seven (four sampling presets and
three G-arms). A kill rule that one arm can switch off for the other six is not a kill rule.*

**Declared difference between the arms and this control, beyond the numbering.** The rung-2
arms were collected at `max_tokens` **8192** and this control at **40960**, and 7 of the 280 arm
responses came within 95% of their cap. That is a second difference between the two sides of
every contrast, in a study whose own history includes truncated sheets being misread as
refusals. It does not invalidate the control — the control is the side with room to spare — but
any contrast has to carry it, and the seven near-cap arm sheets should be reported with it.

**What would make this arm uninterpretable.** A provider pin that cannot be honoured — if any
model is served by a backend other than the one in §3, its cells are reported and excluded
rather than silently compared, since serving path is a same-version variant in this study.

## 5. What this arm does NOT do

It does not re-open the withdrawn position claims by itself, and it is not a replacement for
§17 — the live corpus remains v1, and this is seventy sheets of v2 beside it, not a migration.

**CORRECTED 2026-09-21, by adversarial review, the night it was collected.** §1 and this section
both said the arm "does not touch the refusal result". **That is false and was false as soon as
the sheets landed.** Both gemini models decline the sheet, so the arm contributed 20 refusals,
and `refusal_table.py` sweeps `runs/**/*.jsonl` — the paper's refusal block moved from
`google 67% (15)` to `86% (35)` in the B column. The claim was about the ESTIMATOR (a decline
is categorical and does not touch the position estimator, which remains true) and it was
written as though it were about the CORPUS, which it is not.

This is `RESEARCH-BACKLOG` §22 arriving at a published figure: the sweep is a glob, not a
declared population, so any arm collected under the live instrument enters the refusal table
whatever it was collected for. The same mechanism is LEARNINGS #67, where a two-sheet liveness
probe moved the same block. **The paper's refusal block must not be regenerated while arms are
landing**, and the population it is computed over needs declaring rather than globbing — which
is a scope decision about a published number, not a tidy-up, and is recorded for the author
rather than taken here.
