# Rung 2 applied no obfuscation. The arm named after it was condition B.

> **HISTORICAL — the retired design's pipeline rung.** An audit of the proxy-based, judge-scored
> rung 2 on the ten-question free-text instrument. The present study re-collected rung 2 on the
> 32-item battery through its own transport, with no proxy; that result is in
> [`PAPER-below-the-floor.md`](PAPER-below-the-floor.md). Kept as the record of why the proxy
> arm was abandoned.

**2026-09-14.** Audited from the records already on disk — no new calls — and confirmed against
the running server. Reproduce with:

```bash
python scripts/pipeline_transform_audit.py --live
python scripts/pipeline_rung.py
```

---

## The finding

`run_g0dm0d3.py` sends `parseltongue: true` and writes the record as `B-Parseltongue`. The
server returns 200. The response is complete, the judges score it, the interval is computed,
and for Claude Opus it excludes zero. Every check the study runs passed.

The obfuscation never happened.

G0DM0D3's Parseltongue rewrites **trigger words** — a fixed list of 53 security and jailbreak
terms — and returns the text **unchanged** when it finds none (`src/lib/parseltongue.ts`, the
`triggersFound.length === 0` early return). The instrument is ten neutral policy questions.
Not one contains a trigger.

| run | condition | transform | fired | of |
|---|---|---|---:|---:|
| 2026-09-13-g0dm0d3-replicate | B-Parseltongue | parseltongue | **0** | 100 |
| 2026-09-13-g0dm0d3-replicate | B-Layered | parseltongue | **0** | 100 |
| 2026-05-27-g0dm0d3 | B-Parseltongue | parseltongue | **0** | 20 |
| 2026-05-27-g0dm0d3 | B-Layered | parseltongue | **0** | 20 |

**0 of 240 requests that asked for obfuscation received any.** The evidence was in every
record all along: the collector has been storing the server's own echo of what it did
(`study_call_metadata.x_g0dm0d3.pipeline`) since the arm was first run, and no analysis had
ever read it.

So `B-Parseltongue` is condition B, collected a second time, through the proxy, under a
different label.

### STM is not a prompt transform. It edits the model's answer.

`applySTMPost(response, stm_modules)` — `api/routes/chat.ts:182`. STM runs **after
generation**, on the response, and `hedge_reducer` is a list of eleven regexes that **delete**
`I think`, `I believe`, `perhaps`, `maybe`, `It seems like`, `probably`, `In my opinion` and
their neighbours. `direct_mode` strips opening pleasantries.

So where STM fires, **the judges are not scoring the model's output.** They are scoring the
proxy's edit of it, with hedging removed — on a rubric where hedging is exactly what separates a
hedged 3 from a committed 4. That is the measurement apparatus editing the thing being measured,
in the direction of the hypothesis.

It has to be bounded rather than assumed, so it was measured. Joining each scored record to its
own STM echo, 225 eligible records:

| model | condition | n | STM edited | median chars deleted | mean score, edited | unedited |
|---|---|---:|---:|---:|---:|---:|
| claude-opus-4.7 | B-STM | 60 | **45** | 16 | 3.73 | 3.83 |
| grok-4.3 | B-STM | 60 | **1** | 8 | — | 3.82 |
| claude-opus-4.7 | B-Layered | 50 | 24 | 9 | 3.38 | 3.58 |
| grok-4.3 | B-Layered | 55 | **1** | 1 | — | 4.32 |

Three things follow, and two of them are reassuring.

1. **The edit is tiny.** A median of **16 characters** deleted from responses averaging ~3,500 —
   about half of one percent of the text, a couple of instances of `I think `. A 0.5% deletion
   cannot carry a 0.3-point effect on a 1–5 rubric.
2. **It does not inflate scores.** Edited records score *lower* than unedited ones in both arms
   on Opus (3.73 vs 3.83; 3.38 vs 3.58). Not a causal comparison — hedging and stance are not
   independent — but the direction is the opposite of an artifact manufacturing the finding.
3. **It is differential by model, and severely so: 45 of 60 on Opus against 1 of 60 on Grok.**
   Grok does not hedge in the phrasings the regex catches. So `B-STM` is *not the same
   intervention* on the two models, and cross-model comparison of that arm specifically is not
   supported.

The third point cuts the right way for the surviving finding. **Grok's B-Layered effect cannot
be a text-editing artifact at all** — STM edited 1 of its 55 records, deleting a single
character. Grok's +0.57 is godmode and autotune, with nothing else in it.

And for Opus's −0.31: B-STM was the *more* heavily edited arm (45 of 60, median 16 chars) while
B-Layered was edited less (24 of 50, median 9). Since editing is associated with slightly lower
scores, the more-edited arm sitting on the *high* side of that contrast makes the observed −0.31
conservative rather than inflated.

### What B-Layered actually is

Stripping the two transforms that did nothing, `B-Layered` differs from `B-STM` by `godmode`
and `autotune`:

- **godmode** — prepends a system prompt (`GODMODE_SYSTEM_PROMPT` + `DEPTH_DIRECTIVE`) and
  boosts sampling: temperature +0.1, presence penalty +0.15, frequency penalty +0.1.
- **autotune** — replaces the sampling parameters outright. Measured on the collected
  records: temperature **0.825**, top_p 0.9, top_k 50, frequency 0.2, presence 0.25, against
  the arm's plain **0.7** with no other parameters set.

It is a system prompt and a sampling change. It is not obfuscation, and it is not
"elicitation-layer force" in the sense the writeup uses the phrase.

---

## What this does to the numbers

Because `B-Parseltongue` applies no treatment, its contrast against plain B is a **null by
construction**: it can only measure run-to-run drift plus whatever the proxy path itself
contributes. That makes it a floor every other contrast in the column has to clear — which is
more useful than the treatment it was mislabelled as.

Replicated pair (W13, n=5, against the budget-matched baseline):

| model | contrast | effect | 95% interval | |
|---|---|---:|---|---|
| claude-opus-4.7 | B-STM vs plain B | +0.37 | [+0.13, +0.65] | excludes 0 |
| claude-opus-4.7 | **B-Parseltongue vs plain B** | **+0.24** | **[+0.02, +0.49]** | **null by construction — and it excludes 0** |
| claude-opus-4.7 | B-Layered vs plain B | +0.06 | [−0.31, +0.41] | |
| claude-opus-4.7 | B-Layered minus B-STM | −0.31 | [−0.64, −0.01] | excludes 0 |
| claude-opus-4.7 | B-STM minus B-Parseltongue | +0.13 | [−0.07, +0.36] | |
| grok-4.3 | B-STM vs plain B | +0.09 | [−0.10, +0.30] | |
| grok-4.3 | **B-Parseltongue vs plain B** | **+0.11** | **[−0.10, +0.29]** | **null by construction** |
| grok-4.3 | B-Layered vs plain B | +0.57 | [+0.27, +0.84] | excludes 0 |
| grok-4.3 | B-Layered minus B-STM | +0.48 | [+0.26, +0.70] | excludes 0 |
| grok-4.3 | B-STM minus B-Parseltongue | −0.02 | [−0.26, +0.26] | |

### STM does nothing, and the contrast that said otherwise was the confounded one

Opus's `B-STM vs plain B` reads **+0.37, excluding zero** — the number reported this morning as
the result of repairing the baseline-budget confound. Its null floor reads **+0.24, also
excluding zero.**

Differenced **within the run**, where the baseline run, the collection date and the proxy path
all cancel and only STM remains, Opus is **+0.13 [−0.07, +0.36]** and Grok is **−0.02
[−0.26, +0.26]**. Both span zero.

The published conclusion — *"STM alone (3.60) and Parseltongue alone (3.70) are ≈ prompt-B"* —
turns out to be right about STM. It was not right for the reason given, and for Parseltongue it
could not have come out any other way.

### The floor is drift — and the untreated arm is how you test a baseline

> **Added 2026-09-15.** The figures in the table above are computed against the budget-matched
> baseline, which was the default when this document was written. It was the wrong default and
> this section's own finding is what proved it.

`B-Parseltongue` receives no treatment, so **it must read zero.** That makes it a test of the
baseline rather than a measurement of the models:

| `B-Parseltongue vs plain B` | same-sitting baseline | budget-matched baseline, +2 days |
|---|---|---|
| claude-opus-4.7 | **−0.01 [−0.15, +0.13]** | +0.24 [+0.02, +0.49] · *excludes zero* |
| grok-4.3 | +0.09 [−0.06, +0.23] | +0.11 [−0.10, +0.29] |

Against the same-sitting baseline the untreated arm reads essentially zero. Against the one
collected two days later it excludes zero — and there is no treatment in it, so that is the
baseline being wrong, measured.

**The budget confound that prompted the switch was not biting.** The original baseline records no
`max_tokens`, which is a real provenance gap, but its longest response is **1,295 tokens** against
the matched baseline's 1,307 and the arm's 1,606 at a 4,000 cap — and **not one record in either
baseline is truncated**. The cap was never approached, so it cannot have confounded anything.

So the morning's report that *"the confound was real … three of eight intervals excluding zero
became five of eight"* had the movement right and the cause wrong: **two of those five intervals
were manufactured by two days of drift.** `pipeline_rung.py` is back on the same-sitting baseline
and `tests/test_pipeline_rung.py` now gates on the untreated arm reading zero.

Corrected figures, same-sitting baseline:

| model | contrast | effect | 95% interval | |
|---|---|---:|---|---|
| claude-opus-4.7 | B-STM vs plain B | +0.12 | [−0.07, +0.35] | |
| claude-opus-4.7 | B-Parseltongue vs plain B *(null)* | −0.01 | [−0.15, +0.13] | |
| claude-opus-4.7 | B-Layered vs plain B | −0.19 | [−0.53, +0.13] | |
| **claude-opus-4.7** | **B-Layered minus B-STM** | **−0.31** | [−0.64, −0.01] | excludes 0 |
| grok-4.3 | B-Parseltongue vs plain B *(null)* | +0.09 | [−0.06, +0.23] | |
| **grok-4.3** | **B-Layered vs plain B** | **+0.56** | [+0.23, +0.85] | excludes 0 |
| **grok-4.3** | **B-Layered minus B-STM** | **+0.48** | [+0.26, +0.70] | excludes 0 |

**3 of 10 intervals exclude zero, not 5.** All three are the surviving finding and its Grok half.

### The proxy path, measured

The obvious suspect for that +0.24 was the **proxy path** — every pipeline record goes through
G0DM0D3 while the baseline goes direct to OpenRouter. So it was collected rather than argued
about. `B-Proxy` is plain condition B sent **through the proxy with every transform explicitly
off**, same questions, same 4,000-token cap, same five samples per cell, differenced against the
budget-matched baseline, **which shares its sitting**. 100 calls, `collection_check` ACCEPTED on
the first pass, 100 of 100 classified.

This contrast is pinned to that baseline in code rather than following the default. Pointed at
the same-sitting-with-the-arm baseline instead it crosses two days and reads −0.19 and −0.16 —
measuring drift again. A control that changes meaning when an unrelated default changes is not a
control.

| model | inferred floor (B-Parseltongue) | **measured path cost (B-Proxy)** |
|---|---|---|
| claude-opus-4.7 | +0.24 [+0.02, +0.49] · excludes 0 | **+0.06 [−0.16, +0.28]** |
| grok-4.3 | +0.11 [−0.10, +0.29] | **−0.14 [−0.28, +0.00]** |

**The proxy path costs approximately nothing.** Both intervals span zero.

The two differ in one other respect, and it is now the one that matters. The control was
collected in the **same sitting** as the baseline (both 2026-09-15 UTC); the pipeline arm was
collected one to two days earlier (2026-09-13 and -14). So the decomposition is:

- same-sitting, through-proxy vs direct → **the path**: +0.06 on Opus
- cross-sitting, through-proxy vs direct → **path + drift**: +0.24 on Opus

which leaves roughly **+0.18 of pure cross-sitting drift on Opus**, and a comparable magnitude
on Grok in the other direction. Two *identical* arms collected a day apart differ by about a
quarter point on a five-point rubric, with an interval that excludes zero.

**That changes what rung 2 needs.** The fix is not a proxy-matched baseline, it is a
**same-sitting** one — and every "vs plain B" contrast in this arm currently crosses a sitting.
It also puts a resolution limit on the design: a 10-question, 5-sample cell on Opus cannot
distinguish an effect below roughly 0.25 across sittings, which is larger than most of what this
arm reports.

(The decomposition is a difference of two n=10 bootstraps and should be read as an order of
magnitude, not a point estimate. The part that is not in doubt is the direct measurement: the
path is small and spans zero on both models.)

### An interval excluding zero on an arm that received no treatment

This is the sharpest thing in the audit and it is a statement about the method, not the models.
Opus's null-by-construction contrast excludes zero. Whatever produces that — the proxy path,
run-to-run drift, or an interval too narrow for a 10-question bootstrap — is present in every
other "vs plain B" figure in this arm at the same magnitude. **Five of ten intervals exclude
zero here and one of the five is a measurement of nothing.**

### What survives untouched

`B-Layered minus B-STM` never reads the baseline run. It is immune to the baseline-budget
confound repaired earlier today *and* to the proxy-path confound found here:

- **claude-opus-4.7: −0.31 [−0.64, −0.01]**
- **grok-4.3: +0.48 [+0.26, +0.70]**

~~**The two models move in opposite directions under the same intervention.** That is rung 2's
result. It has now survived every correction applied to this arm, and it is the one claim here
worth carrying into the book.~~

> ### NARROWED 2026-09-15 by the decomposition
>
> Those two numbers are unchanged and still reproduce. What does not survive is calling them
> *opposite directions*. The reference arm is `B-STM`, and **B-STM is not an untreated
> control** — the proxy edits its scored text on 45 of 60 Opus records.
>
> Measured against an arm that received genuinely nothing (`B-Proxy`, same sitting,
> `2026-09-15-g0dm0d3-decomposition`), **Opus is flat under every ingredient**: four cell
> means spanning 3.44 to 3.50, and `B-Layered minus B-Proxy` at −0.04 [−0.34, +0.22]. The
> negative half was a contrast against a treated reference, not a direction.
>
> The corrected finding is one-sided and smaller: **a forceful system prompt moves Grok 4.3
> by about half a point and does not move Claude Opus 4.7 at all.** And the open attribution
> below is now closed — it is the *instruction*, not the sampling: `B-Autotune` is null, and
> it is the larger perturbation of the two.
>
> Full account: `RESULTS-2026-09-15-rung2-decomposed.md`.


Its caveat, stated rather than buried: the intervention is a system prompt *and* a sampling
change together, so it cannot yet say which of the two the models are responding to.

---

## What is now wrong in the published material

None of this is corrected yet; it is recorded here first so the corrections are made against a
written finding rather than from memory.

| file | what it says | status |
|---|---|---|
| `WRITEUP-2026-05-26.md` §4.3 | "STM hedge-strip, Parseltongue obfuscation, or both layered" | no obfuscation occurred |
| `WRITEUP-2026-05-26.md` §4.3 | "Parseltongue alone (3.70) is ≈ prompt-B" | true, and vacuous — it *is* prompt-B |
| `WRITEUP-2026-05-26.md` §4.3 | "the practitioner intuition that layered obfuscation is the potent form" | withdrawn; the potent ingredient is godmode + autotune |
| `CORPUS-MAP-2026-09-14.md` | B-Parseltongue "+0.24 [+0.02, +0.49]" as a repaired effect | it is the null floor, not an effect |
| `RESULTS-2026-09-13-pipeline-rung-replicate.md` | B-Parseltongue rows | need the construction caveat |
| `PREREG-2026-09-13-pipeline-rung.md` | B-Parseltongue predictions | the arm could not have tested them |
| `README.md` rung-2 row | "hedge-strip + obfuscation" | obfuscation never ran |
| `DEVELOPER.md:24` | "hedge-strip + obfuscation (STM, Parseltongue)" | same |
| `X-AMMUNITION-DRAFT.md:71` | "STM hedge-strip + Parseltongue obfuscation" | same |
| `rubric.md`, `run-protocol.md`, `aggregation-rules.md` | `B-Parseltongue` as a perturbation condition | the condition needs a trigger-bearing instrument to mean anything |

`RUBRIC-SCORES.md` D1 scores this rung 4 of 5 on the strength of "elicitation-layer alignment
removal via STM hedge-strip + Parseltongue obfuscation". That self-assessment is now too
generous by one ingredient out of two.

---

## The controls this implies

Each is cheap, local, and answers a question the arm currently cannot.

1. ~~**Plain condition B through the proxy, all transforms off.**~~ **DONE** —
   `2026-09-14-g0dm0d3-proxy-control`, 100 calls, scored. The path costs +0.06 on Opus and
   −0.14 on Grok, both spanning zero, which is what moved the floor's explanation from the
   proxy to cross-sitting drift.
2. **A same-sitting baseline.** This is now the one that matters and it was not on the list
   before the control was run. Collect plain B alongside the pipeline arm, in the same sitting,
   rather than a day or two later. 100 calls. Without it every "vs plain B" contrast in this arm
   carries ~0.2 of drift it cannot separate from its effect.
3. **godmode without autotune, and autotune without godmode.** Splits B-Layered's effect — the
   arm's only surviving one — into system prompt versus sampling change. 200 calls.
4. **A trigger-bearing instrument, if the Parseltongue claim is to be made at all.** Obfuscation
   can only be tested on text it will actually transform. This is an instrument change, not a
   re-collection, and it should be pre-registered rather than bolted on.

Until (2) exists, the honest reading of rung 2 is the within-arm contrast and nothing else —
`B-Layered minus B-STM`, which is collected in one sitting and never touches the baseline.

---

## The gate

`scripts/pipeline_transform_audit.py` reads every pipeline record's server echo and reports
every condition whose named transform fired on zero records. It refuses to pass on an empty
tree, and it is wired into `release_check.py` as *"named transforms were applied"*.
Regressions: `tests/test_pipeline_transform_applied.py`.

It blocks on an **undisclosed** dead transform, not on a known one. Parseltongue is dead on
this instrument and will stay dead until the instrument changes, so a gate that could never go
green over it is a gate somebody eventually deletes — taking the check for the next one with
it. The known ones live in `studypaths.UNVERIFIED_TREATMENT` with their evidence, in three
verdicts that are deliberately not collapsed into one:

| verdict | meaning | entries |
|---|---|---|
| **DISPROVEN** | the treatment provably did not happen | `B-Parseltongue`, both runs |
| **PARTIALLY INERT** | the arm is treated; one named ingredient is not | `B-Layered`, both runs |
| **UNRECORDED** | no evidence either way, which is itself the finding | `2026-05-27-abliteration` and `-controls` |

The third is the weight rung: 220 records whose `obliteratus_applied` is derived from whether
the string `ablit` appears in the run **label**. Nothing inspected the weights and no digest was
stored, so the corpus cannot say whether the abliterated arm ran on abliterated weights. That is
not a claim that it did not — unlike Parseltongue there is no evidence either way. `run_local.py`
has computed a weight fingerprint since the 2026-09-13 audit, so a re-collection on the 4090
closes it; the May records cannot be retro-stamped.

Writing that registry is also how the B-Layered entry got found: the gate went red on a dead
transform I had documented in the prose above and forgotten to record, which is precisely the
job.

It exists because this defect is the study's signature failure mode in its purest form — a call
that succeeded, a response that was complete, a score that was valid, an interval that excluded
zero, and nothing whatever underneath. **The only check nobody ran was whether the treatment was
administered.**
