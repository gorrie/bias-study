# Refusal is elicited by the absence of a directive, and vendor rates invert the published direction

~1,800 forced-choice runs, 15 vendors, local and API, on the 62-item instrument. A refusal
is the model declining **all 62 items**: prose returned, zero answers parsed, token budget
not exhausted, tokenizer intact.

## Refusal is a property of the instruction, not of the model

Rates by vendor and condition, **regenerated from `runs/` by `scripts/refusal_table.py`** —
not transcribed. Condition A is a forced-balance system prompt; B is a bare ask with no
system prompt; D is must-commit; P is a placebo system prompt matched to D for register and
length with no stance content.

| vendor | A (balance) | B (bare ask) | D (commit) | P (placebo) |
|---|---:|---:|---:|---:|
| **google** | **27%** (97) | 29% (75) | **0%** (27) | **0%** (10) |
| z-ai | 24% (33) | 0% (24) | 0% (23) | 0% (17) |
| x-ai | 14% (42) | 0% (20) | 0% (27) | 0% (18) |
| qwen | 7% (111) | 4% (107) | 0% (10) | 0% (9) |
| moonshotai | 6% (47) | 0% (26) | 0% (32) | 0% (22) |
| openai | 5% (114) | 9% (95) | 0% (27) | 0% (18) |
| meta-llama | 0% (24) | 7% (15) | 0% (2) | 0% (1) |
| anthropic | 1% (68) | 0% (56) | 0% (24) | 0% (15) |
| deepseek, mistralai, minimax, tencent, microsoft | 0% | 0% | 0% | 0% |

Excludes the 2026-08-31 order-floor run, which is a targeted re-run of the three Google
models that refuse most and would inflate the Google row to 41% (123) if pooled. It is
reported on its own below.

**What provokes refusal is the absence of a directive, not the balance clause.** That is a
correction to this document's first version, which read the Google A/B gap as evidence that
asking for balance is what triggers the decline. On the corrected table the gap is small and
runs both ways per model: gemini-3.5/3.6/3.7-flash and gemma-4-31b refuse identically under
both, gemini-3-flash-preview and 3.1-pro-preview refuse under A only, and gpt-3.5-turbo and
gpt-4o refuse under a **bare ask** and not under forced balance.

Restricted to the 32 models measured under both arms, so the comparison is matched:

| arm | refusals | runs | rate |
|---|---:|---:|---:|
| no directive (A balance, B bare ask) | 37 | 449 | 8% |
| directive (D commit, P placebo) | **0** | **347** | **0%** |

Eight of the 32 refuse under A or B. **None refuses under D or P, ever.** The instructions
that abolish refusal include a **placebo with no stance content at all** — so what removes it
is the presence of a firm directive, not its meaning, and what invites it is being left
without one.

That reframes refusal from a fixed safety property into an elicitation artifact. A study that
administers this instrument under one framing and reports "model X declines political
questions" is reporting a fact about its own prompt.

### The number this table replaces, and why

An earlier hand-assembled version of this table put Google at **43% (64)** and the D/P pool
at **210 runs**. Neither reproduces. Two causes, both worth stating because both are the
kind of defect this project keeps finding in other people's work:

1. **The corpus grew and the table did not.** The lineage sweep landed after the table was
   written and moved almost every denominator. A number transcribed once into prose has no
   way to notice that. `refusal_table.py` exists so this one cannot drift again.
2. **27 run records carry a stale classification.** The structural refusal test replaced the
   lexical one mid-collection, and sweeps already in flight kept writing the old label —
   `other` on 26 runs that are unambiguously declines (prose, zero answers parsed, 986–7456
   tokens against an 8192 cap, no tokenizer damage), including one from claude-opus-5. The
   records are left as collected; the classification is **derived at analysis time** from the
   stored fields, and `refusal_table.py --audit` reports every disagreement and exits 1
   rather than quietly preferring one.

The direction of the correction is worth noting: Google drops from 43% to 27%, and the D/P
denominator grows from 210 to 347 with the refusal count still at zero. The gap between the
conditions narrows, and the evidence that it is a gap gets stronger.

## The vendor ordering contradicts a published result

Cen reports refusal rates *"highest for GPT models and lowest for Gemini models, with Claude
models in the middle."*

Measured here, condition-controlled on the arm every vendor has:

| | this measurement | Cen |
|---|---|---|
| highest | **Google, 27%** (n=97) | GPT |
| middle | z-ai 18%, x-ai 14% | Claude |
| lowest | **Anthropic, 1%** (n=69); four vendors at 0% | Gemini |

**Google highest and OpenAI near the bottom is the exact inverse of the published ordering.**

This was checked for the obvious artifact first. The initial version of this table pooled
conditions, and since refusal is strongly condition-dependent, a vendor whose runs skewed
toward condition A would show a higher rate for that reason alone. The table above is
condition-matched and the inversion survives at n=64 and n=114.

What this does **not** establish is who is right. Candidate explanations, none excluded:
model versions differ (2026 releases here), the instruments differ, the forcing prompt
differs, and the definition of refusal differs — ours is structural (prose, zero answers,
budget intact), and a study counting only explicit refusal language would classify the
deflection essays differently. Any of those could produce an inversion without either
measurement being wrong.

## Why nobody else has this

Refusal counts are reported in the literature — Röttger's valid/invalid figures, Rozado's
11% mean, Barmettler, Cen. What is absent is refusal measured **as a function of the
instruction**, because that requires keeping the failed runs *and* varying the framing on the
same items and models.

This measurement exists only because invalid runs are recorded rather than discarded as
collection errors. Every rate above is computed from runs a conventional pipeline throws away.

## Detection is structural, not lexical

The first version of this classifier matched a phrase list and undercounted badly. It caught
`"do not possess"` and missed:

> *"I'm sorry, but I can't comply with that request."* — gpt-4o
>
> *"I'm designed not to take personal positions. Which perspective would you like these
> answered from (e.g. social democratic, libertarian, conservative…)?"* — gpt-5
>
> *"These 62 propositions comprise the standard Political Compass test, designed to
> evaluate…"* — gemini-3.7-flash, deflecting into an essay about the instrument

The test is now structural: prose returned, zero answers parsed, budget not exhausted.
Whatever words a model uses, it was asked for 62 answers, had room, and gave none.

Two guards, each from a real misclassification: a run at the token cap is `budget-exhausted`
(truncation was read as refusal on 2026-08-30), and byte-marker soup from a damaged tokenizer
is `corrupt` (two broken abliterated builds scored 4/4 "refused" before that guard).

## The order control, run 2026-08-31

Presentation order moves up to 24 of 62 items on this instrument, which made "Google refuses
under A" a single-order claim like everything else here. It is not any more.

Three Google models, condition A, three presentation orders (canonical, shuffle seed 11,
shuffle seed 22), three runs each — 27 runs:

| | refused | truncated | valid |
|---|---:|---:|---:|
| canonical order | 9 | 0 | 0 |
| shuffle seed 11 | 7 | 1 | 1 |
| shuffle seed 22 | 8 | 0 | 1 |
| **all orders** | **24** | **1** | **2** |

| model | refused of 9 |
|---|---:|
| gemini-3.5-flash | 8 (1 truncated) |
| gemini-3.6-flash | 7 |
| gemini-3.7-flash | 9 |

**Refusal survives reordering.** Every order refuses 7–9 times out of 9, and the two runs that
produced a full answer sheet are in different orders and the same model. Whatever triggers the
decline, it is not the sequence of the propositions — which is what the condition-dependence
claim needs, since the comparison arm (0% under D and P) was also collected in canonical order.

Data: `runs/2026-08-31-google-orderfloor/`.

## Limits

1. **Unequal n across cells** — 1 to 114. The D and P columns are thin for most vendors, so
   "0% under D" rests on 347 runs pooled across 32 models, not on strong per-vendor evidence.
2. **`google` mixes Gemini and Gemma**, hosted and open-weight, under one label.
3. **One collection window**, one instrument, one forcing prompt.
4. **The contradiction with Cen is not adjudicated**, only established. Resolving it needs
   their conditions and definitions, not more of ours.
5. **Order control is now run, and it passes** (section above); the D and P arms it is
   compared against remain canonical-order only.
6. **No hostile read.**
