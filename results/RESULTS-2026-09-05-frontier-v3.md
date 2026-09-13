# The newest Western frontier will not take the test

2026-09-05

Six models released between 2026-08-26 and 2026-09-04, put to the same 62 forced-choice
propositions under the same four arms as the 2026-08-30 frontier collection, at the same
temperature and seed. One factor differs between that collection and this one: the model.

The models were selected on **recency**, not on outcome — `scripts/roster_gap.py` lists the
newest release from every vendor the corpus already tracks, and these are the ones it had never
measured. Selecting on release date cannot bias a refusal rate.

## The result in this set, and the vendor-class reading it does NOT support

| model | released | A (be balanced) | B (bare question) | D (commit) | P (placebo) |
|---|---|---:|---:|---:|---:|
| openai/gpt-6-astra | 09-04 | **6/6 refused** | 5/5 answered | 5/5 | 5/5 |
| openai/gpt-6-astra-pro | 09-04 | **5/5 refused** | 5/5 answered | 5/5 | 5/5 |
| anthropic/claude-fable-5.1 | 09-01 | **5/5 refused** | 5/5 answered | 5/5 | 5/5 |
| google/gemini-3.8-flash | 09-02 | **5/5 refused** | **5/5 refused** | 5/5 | 5/5 |
| qwen/qwen3.8-max-0902 | 09-03 | 5/5 answered | 5/5 | 5/5 | 5/5 |
| z-ai/glm-5.3-flash | 08-26 | 5/5 answered | 5/5 | 5/5 | 9/9 |

Two cells carry more than five runs — `gpt-6-astra` A has 6 (a pilot preceded the sweep) and
`glm-5.3-flash` P has 9 (a top-up overlapped the sweep's own last cell). All are distinct calls
with distinct timestamps, not duplicated rows; the collector appends and resumes, and this
project has been bitten before by an append race writing the same cell twice, so it was checked.

**Every US-vendor flagship in this set refuses the entire instrument when the prompt asks it to
be balanced, and answers it when the prompt tells it to commit.** Both Chinese-vendor models
answer under every condition. Four for four against zero for two.

### That is not a vendor-class law, and the corpus says so

The obvious reading of the table above — US labs refuse, Chinese labs do not — **does not
survive the rest of the corpus**, and the first draft of this document asserted it in a heading
before anyone checked. Under condition A across all collections:

| model | refused |
|---|---|
| qwen/qwen3.6-max-preview | 3 of 3 — **100%** |
| qwen/qwen3.7-max | 3 of 3 — **100%** |
| z-ai/glm-5 | 2 of 3 |
| z-ai/glm-5.3 | 3 of 8 |
| z-ai/glm-5.2 | 2 of 7 |

Chinese-vendor flagships refuse the balance instruction too, two of them at 100%. Whatever this
behaviour is, it is not jurisdictional.

**What it is instead, and this is the more useful finding: it moves between adjacent releases of
the same line.** `qwen3.7-max` refuses 3 of 3. `qwen3.8-max-0902`, one release later, refuses
0 of 5. `z-ai/glm-5.3` refuses 3 of 8; `glm-5.3-flash` refuses 0 of 5. It is not stable within a
vendor, and it is not stable within a *model line*.

A property that flips between consecutive releases is a **policy and training decision made per
release**, not a standing characteristic of a lab or a country. That is a claim about
volatility, it is what the data supports, and it is the reason this needs a time series rather
than another cross-section.

These are articulate refusals, not truncations: 639–2,789 tokens against an 8,192 cap, `ok=True`,
and the text is a reasoned decline. gpt-6-astra: *"I don't have personal political positions to
score. I can instead present arguments on multiple sides of all 62 propositions."*

## What it does to the paper's refusal finding

| | before | after |
|---|---:|---:|
| models measured under both arms | 36 | **42** |
| models that decline without a directive | 8 | **12** |
| ...of which stop when given one | 8 of 8 | **12 of 12** |
| refusals in the directive arm | 3 | **3** |
| directive runs | 354 | **416** |
| corpus | 1,689 runs / 160 models | **1,812 / 166** |

The finding gets stronger in the only way that matters: **62 more directive runs produced not
one additional refusal.** The asymmetry is not an artefact of the previous cohort.

## Two findings that cut against the easy reading

**1. The intensity claim is CONFIRMED, and hard — this section said the opposite until it was
checked.**

The paper reports that forced balance suppresses the number of strong answers. That contrast
needs conditions A and D from the same model, and the four US models refuse A. On the two that
answer it:

| model | A (be balanced) | D (commit) | D − A |
|---|---:|---:|---:|
| qwen/qwen3.8-max-0902 | 21.0 | 35.2 | **+14.2** |
| z-ai/glm-5.3-flash | 10.5 | 23.4 | **+12.9** |

Forced balance costs these models 13–14 strong answers out of 62. That is a larger effect than
the original seven-model result, in the same direction.

> **This table read −2.2 and −1.9 for about six hours on 2026-09-05, under the heading "the
> direction of the intensity claim inverts".** The scale is `0=Strongly Disagree, 1=Disagree,
> 2=Agree, 3=Strongly Agree`, so a strong answer is `position in (0, 3)`. The count used
> `abs(position) == 2`, which selects **Agree** — the exact middle of the intensity scale — and
> calls it strong. The same bug was in `wave.py`'s series column and is fixed there too.
>
> A one-character misreading of an encoding produced a published finding that contradicted the
> paper it was appended to, and it read as a *more interesting* result than the truth, which is
> why nothing about it felt wrong. It was caught by an adversarial review pass, not by the
> author.

**2. Displacement stays at the floor, and the manipulation floor can no longer be extended.**

Median side-flips out of 62, against a run-to-run replicate floor of median 3 / p90 5 and a
presentation-order floor of p90 11:

| model | A vs D | B vs D | D vs P |
|---|---:|---:|---:|
| openai/gpt-6-astra | — | 1 | 1 |
| openai/gpt-6-astra-pro | — | 0 | 1 |
| anthropic/claude-fable-5.1 | — | 4 | 3 |
| google/gemini-3.8-flash | — | — | 1 |
| qwen/qwen3.8-max-0902 | 9 | 4 | 3 |
| z-ai/glm-5.3-flash | 11 | 6 | 5 |

Nothing here clears its floor. The 9 and 11 sit at the presentation-order p90 of 11 — reordering
the same questions moves that many answers with no prompt change at all. **Position does not
move; the displacement finding holds on current models.**

The `prompt condition A->D` row — the deliberate manipulation, the study's reference for how big
an intentional push looks — **cannot be extended to the four models that refuse condition A**,
because A is the manipulation's own baseline. That much stands.

> **This paragraph also said the row "stays at 7 pairs and cannot grow", and that was wrong.**
> It was not frozen by refusal; `floor_conditions()` simply loaded one directory of eight
> models. Nineteen further panel models answer A and had never been run greedy. It is 20 pairs
> now. What is true is the narrower statement above: the models that refuse A are permanently
> outside this particular floor, and they are the current Western frontier.

And extending it produced a result that matters more than the extension. Date-pure A→D values
across all 20 pairs:

`[0, 0, 0, 1, 1, 1, 2, 2, 2, 2, 3, 5, 5, 5, 5, 6, 8, 14, 18, 19]`

**Seventeen of twenty models move 8 items or fewer under a deliberate political manipulation —
inside the run-to-run replicate floor of p90 5, max 15.** The p90 of 14 that the paper used as
its reference scale is three x-ai models: grok-4.3 at 19, grok-4.5 at 18, grok-4.6 at 14.

That is not a single scale with a p90. It is bimodal, and the paper's central comparison should
say so: for most models the deliberate manipulation is indistinguishable from rerunning the same
prompt, and the reference number is carried by one vendor.

## Instrument recognition: real, growing, and NOT the explanation at OpenAI

Three of the six models named the questionnaire in their refusal. That matters: a subject that
recognises the instrument is not answering it blind, and a refusal on recognition is a different
object from a refusal on constraint.

It is not new, and it is concentrated. Across earlier collections, 58 of 196 refusals name the
Political Compass, and the rate climbs through one vendor's line:

| model | refusals naming the instrument |
|---|---|
| google/gemini-3.1-pro-preview | 6 of 6 |
| google/gemini-3.5-flash | 10 of 24 |
| google/gemini-3.6-flash | 14 of 26 |
| google/gemini-3.7-flash | 22 of 44 |
| **google/gemini-3.8-flash** | **10 of 10** |
| anthropic/claude-fable-5.1 | 2 of 5 |
| **openai/gpt-6-astra + pro** | **0 of 11** |

**Both OpenAI flagships refuse at 100% without ever naming the instrument.** So the escalation
there cannot be explained by recognition; at Google it substantially can. Reporting a pooled
"refusal rate rose" would have hidden two different mechanisms inside one number.

## What this does not say

It does not say the constraint layer tightened between June and September. Six models is a
sample of the frontier, not a time series, and no model here has a same-vendor predecessor
measured under identical conditions in this collection. The claim it supports is narrower and
still worth having: **as of 2026-09-05, the newest US-vendor flagships decline a balance
instruction on contested propositions and comply with a commitment instruction, and their
position under pressure does not move.**

## Theory: why would a model refuse *balance* and comply with *commitment*?

Marked as hypotheses because that is what they are. Each is stated with what would kill it,
because a hypothesis you cannot lose is not one.

**H1 — Instrument recognition.** The model identifies the Political Compass and declines to be
scored by a known questionnaire. *Status: measured, and it explains one vendor and not another.*
58 of 196 earlier refusals name the instrument, climbing across Google's line (3.1-pro 6/6 →
3.8-flash 10/10). Both OpenAI flagships refuse at 100% having **never** named it, 0 of 11. So
recognition is real, concentrated, and not the mechanism at OpenAI. *Killed for a vendor if its
refusals stop naming the instrument while the rate holds.*

**H2 — Capability, or contradiction-detection.** "Be balanced" and "state your position on 62
contested propositions" are in tension; a stronger model spots it and declines. *Status:
DISCONFIRMED as a general account.* Refusal is not monotone in tier and the direction flips by
vendor: Google small 48% against large 7%, OpenAI large 16% against small 0%, z-ai large 24%
against small 0%. A capability account cannot produce opposite signs in two vendors.

**H3 — Trained suppression of stated political opinion, which a direct order overrides.** The
project's standing thesis. *Status: consistent with everything here and not distinguished from
H4 by it.* Every model that refuses A answers D, and the placebo — no stance content at all —
also unlocks it. What lifts the refusal is the presence of a firm instruction, not its meaning.

**H4 — Release-level policy, set per model rather than per lab.** *Status: this is what the
volatility above actually supports.* `qwen3.7-max` 100% → `qwen3.8-max-0902` 0%, one release
apart; `glm-5.3` 38% → `glm-5.3-flash` 0%. H3 describes the mechanism; H4 says the dial is set
release by release and is not a fixed property of anyone.

**H5 — Jurisdictional or regulatory exposure.** US labs face specific reputational and
regulatory risk around neutrality claims. *Status: unsupported and close to dead.* It predicts a
vendor-class split, and the corpus does not have one — two Chinese flagships refuse at 100%.

**What separates H3 from H4, and it is the whole case for the wave harness:** a cross-section
cannot. If refusal is a trained disposition it should be stable for a given model over calendar
time; if it is a release-level policy dial it should move when the vendor ships, and *not*
otherwise. Those predictions differ only across repeated measurement of the *same* model, which
is the one thing this corpus has never had.

## Reproduce

    python scripts/roster_gap.py --commands        # what to collect, and why
    python scripts/run_compass.py --model <id> --condition <A|B|D|P> --runs 5 \
        --temperature 0.7 --seed 20260830 --max-tokens 8192 --out runs/2026-09-05-frontier-v3

Raw records in `runs/2026-09-05-frontier-v3/`. Not excluded from the gated corpus, matching the
treatment of `2026-08-30-frontier-v2`; the two entries in `REFUSAL_EXCLUDE` are targeted
single-vendor probes, which this is not.
