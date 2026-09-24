# Learnings

Durable rules earned from defects that actually happened here, each with the receipt that
bought it. Add an entry when a failure mode is worth remembering; delete one only when it is
shown wrong.

**The governing observation, 2026-09-13.** An eight-way audit found ~20 real defects and they
were nearly all one shape: **something reported success while examining less than it appeared
to.** Not crashes. Clean output over nothing. If you remember one thing here, remember that the
dangerous failure looks healthy.

---

## 1. A check that examined nothing must never report clean

Print WHAT was checked and HOW MANY. Exit non-zero on zero input.

> `audit_response_quality.py --check` printed *"no empty response carries a score"* and returned
> 0 having opened **zero files** — while the real corpus held **547** such records.
> `run_inventory.py --check` printed *"every directory accounted for"* with no count, so it read
> identically over 63 directories and over none. `check_doc_links.py` reported *"every relative
> link resolves"* over zero documents. `order_robustness.py` published the categorical verdict
> *"the effect does not survive order randomisation"* from **zero records**, exit 0.

The pattern to copy is `key_numbers.py`: *"CHECKED NOTHING — all 5 requested surface(s) are
absent from this tree. This is not a pass."*

## 2. Validate every detector against known-bad input before trusting it

A detector nobody has watched fire is not known to work.

> **Every detector written on 2026-09-13 was wrong on its first attempt**, and only a known-bad
> set revealed it. The truncation detector caught 9 of 10. Its second version called the
> three-word string "a real answer" truncated. The refusal matcher needed two rounds. The
> placebo-purity test fired on *"proposition"* containing *"position"*. My own verification
> script read the wrong field and reported **0 ties where there were 400**.

Keep the known-bad and known-good sets as committed fixtures, not as something you typed once.

## 3. A hand-written pattern list is incomplete by construction

Match the **shape**, not the enumeration. Appending one more item to the list is the next round
of the same defect.

> Refusal markers enumerated verbs — `help|assist|provide|answer`. Round 1: eight of nine
> patterns began with a capital and were matched against lowercased text, so they could never
> fire; `policy-block` appeared **0 times in 5,128 records**. Round 2, with case fixed, these
> still escaped: *"I can't take a position"*, *"I won't take a side"*, *"I'd rather not weigh
> in"*. The fix was to match first-person subject + negated modal + any verb.

And check the other direction: broadening caught *"I cannot overstate how serious this is"*,
which is among the most **committed** things a model says.

## 4. Never trust a field something in the path can rewrite

> Through the G0DM0D3 proxy, ten responses severed **mid-word** all came back with
> `finish_reason: "stop"`. The proxy rewrites the body and drops the upstream reason. Truncation
> has to be read from the text.

## 5. Record the collection parameters on every record

A parameter that can silently ruin a run must be **in the data**, or the defect is undetectable
afterwards.

> `max_tokens` was never recorded. **1,022 of 4,748 scored records (21.5%)** sat on an 800-token
> cap, severed and then judged — and the only way to find it later was a text heuristic measured
> at 98.6% precision but **68.2% recall**, because a response cut off mid-sentence is detectable
> and one cut off on a full stop is not.

## 6. Differential exclusion relocates a confound; it does not remove it

Before excluding bad records, check whether the exclusion rate varies by the thing you are
comparing.

> Truncation tracks verbosity. Excluding truncated records removed **94.1%** of one vendor
> class's records and **0.0%** of another's. A comparison between a class that kept 86% of its
> data and one that kept 6% is not a finding. This is why re-collection was the only remedy.

## 7. Audit the estimand before the estimator

Eight audits asked "does this code do what it says?" None asked "does this study measure what it
claims?" Those are different questions.

> Result: a day spent fixing estimators, then a **$259** re-collection proposed to fix a design
> problem no data fixes. An independent review killed it to **$30**.

## 8. A baseline that instructs the outcome is not a baseline

> Condition A said *"Do not take a personal position"*; the rubric scored 3 as *"does not
> commit."* **94% of condition-A records scored exactly 3** (239 of 255), so every published
> delta was approximately `B − 3`. The "mask coming off" was a model following its instruction.

Corollary: make the instruction a **treatment** against a no-instruction baseline, and add a
content-free **placebo** so "this instruction" is separable from "any instruction".

## 9. More items beat more samples when between-item variance dominates

Power against the **measured floor**, not against taste.

> Isolated by subsampling one clean run: n=1 averaged **1.45** of 8 intervals excluding zero,
> n=5 gave 3 — so only ~1.5 came from sample size, and n=1 hits zero by luck 19% of the time.
> At 30 questions the CI half-width goes 0.18 → 0.14 from n=1 to n=5, while every cited effect
> is 0.45–0.90. The replicates were nearly free of value; more items would not have been.

## 10. Two copies of a measurement drift. Derive one, or gate it

> `ablation_equivalence.py` computed a published verdict from three hand-typed lists and opened
> **no file at all**. Against live data every base disagreed, and the key one kept `[8,9,9]`
> where the wave holds `[0,2,9,9,9,9]` — dropping exactly the two near-zero rows, which is what
> produced the verdict. Its own comment records the dict being corrected once before, for the
> same reason.

## 11. Replicates that overwrite are worse than no replicates

Keying a dict on too few fields silently keeps the last sample and reports n=1 as a completed
n=5.

> `pair_records` keyed `(model, question_id)`. `WRITEUP-2026-05-26.md:350` published *"the
> vendor-class direction replicates under N=5 averaging"* — **nothing was averaged**. Same bug
> in `pipeline_rung.py`, `analysis.py`, `abliteration_effect_check.py`, `ablation_wave.py`.

## 12. Write every record as it arrives

A run held in memory is a run you can lose, and one you cannot inspect.

> The collector buffered a whole model — 400 calls, ~100 minutes of spend — and wrote once at
> the end. With stdout block-buffered, a run an hour in looked identical to one that died in its
> first minute. The only evidence of life was the billing endpoint.

## 13. Compare like with like, and say when you have not

> "Vendor arc" pooled **seven protocols** into one line with no protocol column — baseline,
> out-of-distribution, paraphrase, reversed-premise, dose-gradient, pipeline rung. One model
> version contributed three of them as separate "measurements". Ten of the families pooled more
> than one.
>
> The abliteration verdict compared arms over **different question sets** and certified text
> rewrites at Jaccard 0.339 and 0.333 — **inside the 0.303–0.392 band the project itself
> measured for one model against itself**.

## 14. A verdict needs its floor attached

> Four of the instrument's own floors report their **sample maximum** as a p95, because the
> percentile index clamps at small n. The `requantisation` floor (n=13) is the reference the
> weight-rung null is judged against, and that null inverting is the audit's most quotable line.

## 15. Name your version axes explicitly

> `v1/v2/v3` meant intervention **rungs**; releases were **dated**; and there was no vocabulary
> at all for the **instrument**, so two fundamentally different instruments shipped under one
> title. They disagree: convergent validity across 24 models is **r = −0.12, CI [−0.57, +0.37]**.
> Now: rungs `v1/v2/v3`, releases dated, instruments `I1/I2/I3`.

## 16. Fix the document to match the code, not the test to match the document

> `RELEASE-2026-09-07.md` said 18 mechanical checks; the code had 20. The count test caught it
> immediately. One test did have to be loosened — it **required** the sentence "all N mechanical
> items pass", which forced the document to assert a green release. A test that cannot express
> "the gate is red, correctly" pressures whoever hits it into restoring a claim that is not true.

## 17. Run the cheap decisive step before the expensive one

> A $259 collection was proposed without first asking how much of the damage was already
> repaired. `2026-09-05-recollect` **already existed** — 117 records at a 4,000-token cap on the
> same judge panel — and splicing it in took Opus 4.7 from 1 usable pair to 10. The remaining
> gap was 176 cells, about $4.

## 18. The secret scanner must detect *your* secret

> A decoy holding a real-shaped OpenRouter key, an AWS secret and a GitHub token scanned clean
> under both this repo's config **and** gitleaks' defaults. The default ruleset has no OpenRouter
> pattern, so the one credential every collection depends on was the one the scanner could not
> see. Path-exempting README and SKILL files made it worse: those are exactly where a key gets
> pasted.

## 19. Verify the mirror, never generate it

> The bank builder (retired with the instrument it served; the filename is not repeated
> because a backticked script name reads as a live reference) first **derived** each negation
> by inserting "not" after the first
> auxiliary. On an item whose first auxiliary sat in a subordinate clause it emitted *"a user
> that their data was **not** handed over is an abuse of state power"* — a different
> proposition, collectable, and it would have scored cleanly. It also emitted "have not more
> influence", which English cannot say. Both halves are authored now and `verify_negation()`
> asserts they are one token sequence apart. A generator must be right about grammar; a verifier
> need only be right about identity, and identity is decidable. **Reading all 60 items once
> caught four defects the tests did not.**

## 20. The preview is the step you take because you are about to spend money

> `run_battery.py --dry-run` built its prompt without `shuffle_seed`, so it printed items in id
> order while the run would send them shuffled — and on a mirrored bank it showed all 30 pairs
> adjacent, the single arrangement the instrument exists to avoid. The collection path was
> correct. The preview is the worse of the two to have wrong: it cannot fail loudly, it can only
> reassure you about a prompt nobody will send.

## 21. A check that cannot read a layout must not report it as empty

> `validate_runs.count_records` read `raw/` only and returned "0 model file(s), 0 record(s) on
> disk" for every flat-layout run. `runs/2026-09-05-wave` holds 124 files;
> `runs/refusal-ablation` holds 4,500 records. It printed a count it had not taken — this
> project's own signature defect, pointed inward. The root-level exemption that used to spare
> that corpus broke silently the moment `runs/` became **mixed**. Live findings fell 43 → 9 once
> layout was classified per directory, and 34 runs holding 8,122 records are now labelled NOT
> VALIDATED, which is neither a defect nor a pass.

## 22. Fix a defect once, in one place, or the last copy survives

> `cells[(model, question_id)][condition] = record` shipped in **six** scripts. Three were fixed
> one at a time over two days; three were still live afterwards, including the weight rung,
> where "stance does not move" was computed from one draw of five. There is one
> `scripts/replicates.py` now and the call sites pass their key. The published vendor-class
> split moved from +0.048 to +0.545 when it was finally applied everywhere, with one model's
> delta reversing sign.

## 23. A tripwire that fires has done its job — update it, never loosen it

> Two tests in `test_pipeline_rung.py` were written to FAIL when W13 landed: one asserted the
> arm was still n=1, the other that no contrast cleared zero, each carrying the instruction
> "update the README row and this test together, deliberately." Both fired. Three of eight
> intervals now exclude zero and the two models disagree in sign. Had either been relaxed to get
> a green suite, the finding would have been buried by the gate built to surface it.

## 24. A false positive that RECURS is a detector defect, not a per-cell exemption

> A `gemma-3-27b-it` cell ending on a markdown link was diagnosed correctly as a false positive
> and then filed in `studypaths.UNREPAIRABLE`, with the count taken inside one run: "one record
> in 2,101 ends in a URL and that one genuinely hit the cap." Re-counted across all 30,089
> records, **nine** end that way while flagged severed — five cells, two models, three runs, and
> **none within 95% of its cap**. Two are `gpt-4.1` records in `2026-09-13-i3-phase0`, the live
> forced-choice instrument, so the registry entry was not containing the problem, it was hiding
> it in the data the current study depends on. The same shape hit CJK punctuation: the terminal
> set was `[.!?]`, ASCII only, so a finished Chinese sentence could never end.
> **Count corpus-wide, not inside the run you are looking at** — a registry is for cells nothing
> can fix, and the cap fraction is what separates the two.

## 25. A docstring that says "called automatically" is a claim, and claims get gated

> `recollect_at_cap.dedup` carried "Called automatically after a collection run so the file on
> disk matches the cells in it" from the day it was written, and **no caller existed**. Seven of
> ten repair directories had accumulated duplicate rows, 22 in total. Nothing read a wrong
> number — every reader is dict-keyed and takes the last row — but everything that COUNTS did:
> `collection_check` reported 2.2% truncation in a directory whose cells are all usable, and
> `score.py` bills per row, so each uncollapsed retry was judged twice. The function was correct
> and dead, which is worse than absent, because it answers the question for whoever greps.
> The test now asserts the CALL SITE, not the behaviour.

## 26. A resumable tool re-derives its work list — so "re-run it, it'll be a no-op" is not true

> Six repair manifests went stale after the dedup, and the obvious fix was to re-run the
> collector to re-emit them. `--run` without `--models` re-derives `todo` from the WHOLE source,
> and for a source whose GPT-5 cells were deliberately repaired into a SEPARATE run, those cells
> read as outstanding here. It wrote **13 gpt-5 records into the general augmentation
> directory** — cells already repaired next door — before it was killed, breaking the one
> invariant that keeps a spliced corpus attributable. The stray file was checked cell by cell
> against its proper run before removal, and the collector now has `--manifest-only`, which
> cannot call an API at all. **Give the safe operation its own mode; do not rely on remembering
> the longer argument line.**

## 27. An analysis arm that computes nothing must be NAMED, never absent

A row that disappears reads exactly like an arm nobody wrote. Print the count of arms that
produced no row, each with its reason, and keep three reasons apart: a path matching no file
(a defect), a source retired by a dated ruling, and a corpus not collected yet.

> `floor_same_version` — **the paper's headline null** — read one hardcoded directory,
> `runs/2026-08-31-lineage/**`, which moved to `withdrawn/` on the morning of 2026-09-16. It
> globbed zero files, `summarise` returned None, and `all_floors` dropped it with
> `if not r: continue`. The 252-sheet wave would have collected correctly and populated
> nothing. Caught by an adversarial review with hours to spare, not by any gate.
>
> `floor_table.py --uncomputed` was built the same day and immediately found the **next** one:
> `floor_quant` read two withdrawn quant-null directories, while the requantisation pass
> planned for this instrument collects into the wave directory. Sixty sheets, no row. Nine of
> fifteen arms compute nothing today and every one of them now says why.

Sources are recorded **by the read** — `_record_source` fires inside `load()` — rather than
declared in a table beside the functions, because a declared list is a second copy of a fact and
every one of those this project has written has drifted. `RETIRED_SOURCES` is a dated ruling,
not a suppression list: a test fails when an entry names a pattern no arm reads any more.

## 28. Measure the budget on the bank AND the roster you are about to send

A shorter instrument does not make the token budget smaller. The roster moves it too.

> `MAX_TOKENS` was 32,768, measured on the withdrawn 60-item bank across 31 models. The 32-item
> battery on 36 models measures a longest sheet of **17,268 tokens**, so the minimum safe budget
> is **34,536** — and the five models added as same-version siblings are reasoning models that
> spend the budget before they answer. The wave's longest actual output was **35,002**. At the
> old cap it would have been severed mid-sheet on one vendor, which is the 4,096 failure that
> cost this study a month.

## 29. A refusal is a measurement. Never pool it with a malformed answer

They are facts about different things — one is the model's behaviour, which this study reports;
the other is our parser, which is a defect. A gate that averages them hides both.

> `collection_check` rated every sheet on parse rate, so models that **declined the instrument**
> landed in a blocker reading "parsed below 95% of their items". On pass 1 that was **35 of 37**,
> and the two genuine format failures were invisible inside it. Separated, the blocker reads
> "2 of 405 sheets that ATTEMPTED an answer, worst 91%, mean parse rate 100%".

## 30. Learn per-model state from the first RESPONSE, not the first SUCCESS

> The provider pin was set inside `if r.returncode == 0 and tail:`. A model whose first sheet was
> refused learned no backend, so every later sheet went out unpinned — which is how `glm-5.1`
> came back on two backends **after** the per-model pin landed. A refusal names the backend that
> refused it, which is exactly the fact needed. Four of the five backend-split models were
> pre-pin; that one was not, and it is the one the fix was for.

## 31. Validate the parser against each model family's real output before calling silence a refusal

> `llama3.1:8b` answers `N. <proposition>` with the option on the NEXT line — every item
> answered, nothing truncated — and `LINE_RE` required the number and the option on one line, so
> it parsed zero. The failure classifier then saw a non-empty, non-capped, zero-answer body and
> called it a refusal. **4 of 24 recorded refusals were complete 32-of-32 answer sheets.** That
> was going to ship as a finding about a local model declining the instrument.

## 32. "Collected" must mean "collected VALIDLY", or resume lies

> `done_cells` counted any record in a cell as collected, so the prereg's own rule — *a run that
> does not yield exactly N clean answers is discarded whole and rerun* — was executed by nothing.
> gemma-4-12B sat at 8 invalid of 12 and would have entered the order floor on four sheets.
> Mechanical failures now re-roll to a cap of two; **refusals never do**, because retrying a
> refusal manufactures an answer from a model that declined.

## 33. One probe draw cannot bound a model's output — the spread WITHIN a model is bigger

A per-model token budget derived from a single probe sheet looks like the obvious saving and is
not available. Size the cap from the roster, and accept that a runaway costs the roster's
maximum.

> One global cap means every model's failure costs the LONGEST model's budget.
> `deepseek-v4-flash-0731` probed at 5,324 tokens and was handed 40,960; four of its twelve
> sheets spent the entire budget and emitted **zero characters** — 163,840 output tokens and 28
> minutes of wall clock, 20% of the whole wave's output spend, for nothing. So: cap each model
> at its own measured need.
>
> The check built to validate that change rejected it. Measured across every valid sheet:
> `deepseek-v4-pro-0813` ranges **160 to 14,426 tokens over 25 valid sheets — 90x**, and it is
> not alone (flash 11x, fable-5.1 11x, v4-pro 10x). **Within-model spread exceeds between-model
> spread**, so one probe draw bounds nothing, and at a 2.37x factor four models would have been
> truncated on sheets they had already produced. Truncation is the failure that cost this study
> a month. Reverted.

Worth keeping beside it: raising the cap 32,768 → 40,960 bought **exactly one sheet** in the
whole wave — glm-5.3 at 35,002 tokens, valid, 32 of 32. Every other record above the old cap is
a runaway. The raise was right and it was marginal, and it made each runaway 25% dearer. A
budget is a bet on a tail, and the tail is thin.

## 34. A selftest validates a function against its own assumptions. Make it read a real record

An estimator checked only against input it generates, in a shape it chooses, is checked against
nothing the collector writes.

> `position_analysis.py` is this study's PRE-REGISTERED primary estimator — position,
> consistency and acquiescence over 16 mirrored pairs, written before the data deliberately so
> it could not be shaped by it. **Eleven selftest checks passed from the day it was written and
> it had never produced a number.** Its `main()` printed *"Phase 4 has not been collected yet"*
> for any real run directory, over 702 records, and behind that stub sat three more breakages,
> any one of which would have crashed it had it been called: `pair_index` read `item["pair_id"]`
> where the bank has `pair_no`; `cell_positions` iterated `rec["answers"].items()` where the
> collector writes a LIST; and the four pre-registered contrasts named conditions `F/N/P/C`
> while the wave collected `N/A/P/D`, so the contrast loop appended nothing and returned an
> empty list that read as a computed result.

**Collection and analysis were gated separately and nothing joined them.** The preflight
checked the instrument was signed and the budget measured; nothing asked whether the analysis
could consume what the collection produces. `check_outcomes_computable.py` is that join, and
`tests/test_outcomes_gate_catches_the_stub.py` replants all four defects and asserts it fires —
because a gate nobody has watched fire is not known to work (#2).

Two properties it needs, both learned here: **a failing prediction must not fail the gate** — it
asks whether an outcome can be COMPUTED, never whether it was confirmed, and a check that
reddens on an unwelcome answer is a check under pressure to be tuned — and it must be **fast
enough to run**, 3m36 to 1m48 by reading the corpus once instead of once per outcome, because a
slow pre-collection gate is a skipped one.

## 35. A threshold you choose is the result. Ask each unit against its own interval

When a criterion's verdict moves with a cutoff, the cutoff is the finding, whichever direction
it lands.

> Pre-registered prediction 2 is a ratio, `|P−N| < 0.5 × |F−N|`. Read literally over 37 models
> it gives 46% and FAILS — and the failures are models whose denominator is inside the noise
> floor: `gemma2:9b-instruct-q8_0` has `|F−N| = 0.010` and a ratio of **19.0**. Restricting to
> larger denominators makes the pass rate climb **monotonically**: 46% at no cutoff, 73% at
> 0.150, 80% at the panel median, 100% at 0.400. **I chose the panel median, which is the first
> cutoff that passes**, and reported PASS. A sensitivity sweep caught it.

The fix is not a better cutoff. It is to ask the question per model against that model's own
interval, which has no knob: does the placebo contrast exclude zero after BH-FDR?

## 36. An average over units is not a result about the units, and it can invert one

> The same prediction, answered per model: **the placebo significantly moves position on 15 of
> 37 models.** Its median effect is +0.042 and its sign test is p = 1.0, which this project
> published twice as *"the placebo moves nothing"*. Both summaries are arithmetically correct
> and both are artifacts — the placebo's significant effects **point in opposite directions and
> cancel**: `mistral-medium-3-5` +0.271 against an instruction effect of −0.167, `grok-4.5`
> +0.167 against −0.365, `qwen3.8-max-0902` +0.260.

Averaging opposite-signed real effects to zero is how a placebo passes the control it exists to
fail. Report the per-unit table; let the summary be derived from it and never stand in for it.


## 37. A provenance field with a "partly mine" category proves nothing

> The factions prereg first allowed `origin` to be `author`, `rewritten-from-draft` or
> `kept-verbatim`, with the sign-off naming every non-`author` row. **`rewritten-from-draft` is
> the 2026-09-14 bank's own description.** An assistant wrote 60 items, nobody read them, 372
> sheets were collected against them — and had that bank carried an `origin` field, every row
> would have been honestly labelled `rewritten-from-draft` and the gate would have passed it.

A field exists to make one state distinguishable from another. A category that both the good
case and the failure case can truthfully claim removes the distinction the field was added for.
`author` or the bank does not collect; and absence is allowed only by name, in a dict, with a
written reason, for banks that predate the field — never as a silent default, because "the
field is missing" is also what the failure case looks like.

## 38. Calibrate the CRITERION, not just the estimator

> The factions prereg asked for **at least 3 models** with a sector lean surviving BH-FDR
> across 36 models. The per-model statistic `max_s |L[m,s]|` is invariant under relabelling
> sectors and under permuting everything that is not the maximum, so its minimum attainable p
> is `S^(1−T)` — **1/64 at four stems and four sectors, whatever the effect size.** BH-FDR at
> 0.05 rejects nothing until **twelve** models reach that floor.

The estimator was correct. The criterion built on it could not return a true answer, and a wave
run against it would have reported P2 FAIL — read as "no model leans by sector" when it means
"this design cannot resolve three models". Recovering one planted effect proves the arithmetic;
only running the whole criterion over many synthetic nulls, and asking whether its verdict is
decided by the design's geometry rather than by data, catches this. Do that before collecting.

## 39. A design that assumes its inputs is the vacuous pass wearing a different hat

> The factions design specified "at least three `people.jsonl` ids for its play" and **nothing
> checked that was satisfiable**. Three gaps surfaced afterwards, by hand, each looking like
> something else: 346 of 550 records carry no play at all, so the instrument reaches 37% of the
> dataset; `vault` has 8 played records against a design wanting 6 per item; and the dataset has
> **no jurisdiction field**, discovered two hours after a jurisdiction slot was recommended.

A reviewed, pre-registered, fully-built design can rest on a requirement its data cannot meet,
and it looks exactly like a finished design. Run the design's stated requirements against the
actual corpus before the design is accepted — one command, check_mcp_coverage.py in the
private tree, which is not part of this release — rather
than discovering each shortfall separately and mistaking the first for a scope decision.

## 40. A constraint that is satisfiable but not FINDABLE must be constructed, not sampled

> Same-stem siblings had to sit ≥3 apart and mirror halves ≥6 apart on a 32-item sheet. A valid
> order exists — the standard bound is (8−1)·3 + 4 = 25 ≤ 32 — and **2000 random shuffles found
> none, across twenty seeds.** The rejection loop would have raised at collection time and
> stopped the pilot for a constraint that is perfectly satisfiable.

Feasible and reachable-by-shuffling are different properties, and the gap between them grows
with every constraint added. Check the bound; if it says a solution exists, construct one and
then verify the construction against the same constraints — a construction that silently drifts
from what it promises is worse than the loop it replaced. Keep the seed varying the result, or
the presentation-order floor reads as zero because there are no orders.

## 41. An estimator that has never been run on data with a known answer is not an instrument

> `position_analysis.contrast` paired each model's 16 items and bootstrapped the pair-deltas.
> `cell_positions` had already averaged the sheets, so a sheet-level disturbance arrived as
> sixteen closely-agreeing numbers and was read as signal. Measured by splitting condition N in
> half at random and contrasting one half against the other — a contrast in which nothing
> differs — it **rejected 49.6% of true nulls at a nominal 5%**. Under it a content-free
> placebo appeared to move position on 16 of 37 models. That became the paper's lead finding,
> was written into four documents, and was withdrawn nine hours later.

Every floor in this study exists because somebody asked the instrument what it does when
nothing changes. **Nobody asked it of the estimator.** The check costs no data and no API
budget: take one arm, split it at random, and see how often the machinery finds a difference
that cannot exist. It now runs in `position_analysis --selftest` and fails the suite.

Two things make this worse than an ordinary bug, and both are the general lesson. The defect
was **not uniform**: the instruction effect survived the correction almost intact (28 → 25 of
37) while the placebo collapsed (19 → 4 of 39), so the broken estimator was specifically
manufacturing the control-arm result — the one place a defect is hardest to notice, because a
control that moves looks like a finding. And the resampling unit was **named correctly in the
docstring** (`resampling the CLUSTERS given`) while the clusters given were the wrong ones; the
code said what it did and nobody asked whether what it did was right.

Corollary, found the same day: a pre-registered criterion can be unsatisfiable by a CORRECT
result. Prediction 2 required the placebo contrast to exclude zero on no model after BH-FDR,
while BH permits false discoveries by construction — at the estimator's **measured 10.5%**
(`calibrate_estimators.py`, 2026-09-19; 6.2% was a docstring), ~3.9 of 37 are expected.
A working control arm fails that test. State criteria against the measured false-positive rate
of the estimator that will run them, not against zero.

## 42. A verdict measured on one instrument does not transfer to another. Re-measure it

> Four arms were rejected in one evening on verdicts that were true where they were taken and
> false where they were applied:
>
> | rejected as | actually |
> |---|---|
> | ablation: "on the retired instrument" | **judge-scored**, 4,500 refusal records + May political sheets, all intact |
> | dose gradient A→E: "retired and withdrawn" | judge-scored, and B/C/E were simply **never collected** on the battery |
> | parseltongue: "a no-op, 0 of 240 fired" | measured on **ten neutral policy questions**. The battery is 32 items on surveillance, censorship, encryption and protest — **10 of 32 carry a plausible trigger term** |
> | six release arms: "orphaned" | four were rows the generator renders; a swallowed `NameError` in the checker classified everything as missing |

The shape is always the same: a finding is established in one context, compressed into a word
— *retired*, *dead*, *orphaned* — and the word travels to a context the measurement never
covered. It is cheap to commit because the verdict really was earned once.

**Retired, judge-scored, never-collected and uncomputable are four different states**, and only
the first means discard. Before excluding anything, name which one it is and say what evidence
puts it there. `grep` the instrument field. Read one record's keys — `question_id: T01-Q2` with
`judge_reasoning` is judge-scored, not retired, and the remedy is re-collection rather than the
bin.

**The test for whether a verdict transfers is whether its MEASUREMENT would come out the same
on the new input.** Parseltongue's did not: the old instrument's vocabulary contained no
triggers and this one's does, which turns a dead arm into the most interesting one in the rung
— a transform that rewrites "surveillance" and "encrypted" before the model reads them is a
direct test of whether the measured position depends on the vocabulary or the proposition.

Corollary, and it is the same rule pointed inward: STM's hedge_reducer WAS dead here, but that
was asserted from "a forced-choice sheet has no hedges" before anyone counted. It survives only
because the count was then run — **0 of 2,645 sheets contain a hedge phrase.** Being right by
luck and being right by measurement are indistinguishable in the moment and completely
different afterwards.

## 43. `def f(n=KNOB)` binds at import. A knob that looks set and is not stops anyone looking

> `check_outcomes_computable._fast()` sets `position_analysis.BOOTSTRAP_N = 200` around the
> gate's analysis, with a comment giving the reason: *"a pre-collection gate that takes minutes
> is a gate people skip — which is the failure mode every skipped gate in this project has
> had."*
>
> Three functions wrote the draw count into their signature as `n=BOOTSTRAP_N`. Python
> evaluates a default **once, at import**. The assignment reached nothing. The gate ran 20,000
> draws believing it ran 200 — a hundred times its budget — and as the corpus grew from 702
> records to 2,599 it crossed the 900s gate timeout.
>
> `gates.execute` caught `TimeoutExpired` in a bare `except` and returned **rc 1, a defect**.
> The collection runner does not collect behind a failed gate. **Four collection stages across
> two chains were refused on 2026-09-18 with nothing wrong with them** — the transport retries,
> the granite re-collect, and BOTH local B/C/E dose-gradient stages, which are recovered work
> that had already been wrongly discarded once (see [#42](#42)).
>
> Measured after the fix: same gate, same corpus, **>600s → 11.8s.**

Two separate rules, and the bug needed both to bite.

**A timeout is not a defect.** One says *"I looked and found something wrong"*; the other says
*"I never finished looking."* The remedy differs completely — fix the check versus fix the
budget or the cost — and an operator who reads the first when it was the second debugs the
wrong thing for an evening. `gates.py` now has `TIMEOUT = 3` with its own `TIME` mark and its
own line in the tally. **It still blocks** — failing open on an unanswered question is the worse
error — but it says which kind of not-passing it is.

**A late-bound knob or none.** Take `n=None` and read the global in the body. The AST test in
`tests/test_bootstrap_knob_is_live.py` found the identical freeze in **five more modules**
(`ci_analysis`, `convergent_validity`, `paired_analysis`, `refusal_suite_summary`,
`robustness_checks`) the first time it ran; all six are fixed. The test asserts both halves,
because structure can be satisfied while the value is read from somewhere else: it checks that
no signature freezes the name **and** that moving the global actually changes the number of
draws taken.

The general shape, and it is this project's signature failure wearing a new coat: **the
disconnected control.** A gate that checked nothing and passed. A `--strands` flag that skipped
and read as green. A `_fast()` that was not fast. Each one makes the system *look* deliberate —
someone thought about the cost, there is a comment explaining the reasoning — which is exactly
why nobody re-measures. **Assert that a knob moves something. A setting nobody has watched change
is a setting nobody has.**

## 44. A check that names the wrong cause gets switched off. Say what you actually saw

Three times in one night, a check reported a real problem and blamed the wrong thing:

| the check said | what was true |
|---|---|
| `FAIL — every pre-registered outcome computes` | the gate **timed out**. It found nothing; it never finished. Four collection stages were refused behind it |
| `BLOCKER: glm-5.2 loses 48% of its ATTEMPTED sheets to invalidity` | 25 of those "attempts" were HTTP 404 from a pinned backend. **The model never saw them.** Its invalidity among sheets it answered is zero |
| `a floor changed when the corpus was read in another order` | the corpus **grew mid-test** — four chains were writing. The order was fine |

Each one is a true observation attached to a false cause, and the cost is not the wasted
debugging. It is that **an operator who checks two of these and finds both misattributed stops
reading the third.** That is how a gate becomes decoration, and this repository has written
that sentence about other people's code.

The fix is the same shape every time and it is cheap: **before blaming, check the thing you
are about to blame.** The timeout is a separate exit code from the defect. The transport row is
counted separately from the model's output. The corpus is fingerprinted around the comparison,
and the test skips with "the corpus changed under me" rather than accusing the estimator. In
each case the check still blocks — none of this loosens anything — it just stops lying about
why.

Corollary, learned the same night by writing one: **a new check that fires on everything is
indistinguishable from a correct one when it tells you what you already believe.** The
control-depth guard added to `run_rung2` filtered on `r.get("valid")` and reported ZERO control
sheets for every model. I was expecting bad news there, so it read as confirmation — and one
of those models plainly had five. `load_records` drops invalid rows and does not carry the
flag. **Test a new gate against a case you know should PASS**, not only against the failure
that motivated it.

## 45. Metadata describes the build the tool *intended*. Hash the artifact

> `RESULTS-2026-09-18-dose-series-preflight.md` cleared all four dose arms by reading
> `abliteration_metadata.json` — identical `method_config` except `n_directions`, identical
> 18-layer target set. It noticed that `dose4` listed its layers **descending** where the others
> ascend and called that cosmetic. It is not cosmetic; it is the fingerprint of a different
> invocation. SHA-256 over the safetensors: `dose4` is byte-identical to a build made **thirteen
> days earlier**, `abliteration-output/` contains no `dose4` at all, and all four model
> directories were created inside one 30-second window — a copy, not four ablations. The arm at
> the midpoint of the dose curve carried the exact confound the series was built to remove.
> A hash is one command. The metadata had been read three times.

## 46. A nominal parameter is not the quantity it names

> The dose axis was `n_directions` = 2, 4, 8, which reads as 1× / 2× / 4×. Measured as relative
> Frobenius change against stock over all 464 tensors it is **1.00× / 2.26× / 2.45×** — the
> intervention saturates, and the top arm is 8% more perturbation than the one below it for twice
> the nominal dose. Separately, 99.5–99.8% of that change lands in `model.embed_tokens.weight`,
> not in the eighteen "strong layers" that the plan, the preflight and the tool's own metadata all
> foreground. Plot against the measured quantity; keep the knob setting as a label.

## 47. An artifact you built is a record. Stamp it with the tool revision

> Rule 5 requires collection parameters on every record. A model you abliterate is a record too,
> and none of the `abliteration_metadata.json` files carries a tool version or git revision. That
> single missing field is the whole reason establishing dose4's provenance required hashing 18 GB
> of weights and comparing directory birth times, instead of reading one line.

## 48. A gate written for one configuration should be re-checked before it binds yours

> `BACKLOG-larger-hardware-and-v3.md` parked the two most valuable ablation items — do the
> ablation ourselves, and plot intervention strength as a dose-response curve — behind
> "needs 128GB". The gate was computed for a 27B at bf16 (~54GB) and is correct for one.
> `gemma-2-9b-it` at fp16 is ~18GB and runs in-process on a 32GB M5 at ~33 s/prompt. Both items
> had been sitting parked, and the file still said they had not started while they were running.

## 49. A fork gate has a direction, and the mirror can be the stale side

> `check_no_fork.py`'s own help text warns about a fix stranded **in** the mirror. It found 31
> forks over 80 shared files, and the direction was the other one: the public mirror — the
> artifact the preprint cites — still computes `bootstrap_ci` with `random.Random(42)`
> constructed fresh inside the function, so every contrast with the same n draws the same
> resample sequence and their intervals are correlated with nothing in the output showing it.
> When triaging forks, classify each file by direction, and separate genuine divergence from the
> expected `runs/` vs `data/` path difference: of 175 public-only lines, **3** were paths.

## 50. Collection freezes predictions, not prose — amend, never silently edit

> This was gotten wrong in both directions within one session. First a plan defect was silently
> corrected; then, over-correcting, the two false sentences were left standing on the grounds
> that "plans are not edited after collection" — a rule quoted from `prereg/README.md`, **a file
> that does not exist**. What the tree actually practises:
> `PLAN-2026-08-29-two-experiments.md:15` — anything a design review overturns "lands as a dated
> amendment rather than a silent edit"; and `PREREG-2026-08-29-mask-surface-v2.md` Amendment 1 —
> zero data is "the only reason **predictions** may be added below rather than merely scored."
> After data exists a prediction can only be scored, because changing one post hoc launders a
> result. A description of the instrument can still be corrected, because correcting it cannot
> flatter anything and leaving it wrong misleads every reader who checks the plan against the
> data. **And: a rule you remember is not a rule the repo has. Open the file before quoting it.**

## 51. Real data is not enough — a calibration is only as good as the SUBPOPULATION it samples

> #2 says a detector validated against input it chose proves nothing. The refinement, found
> 2026-09-19: **switching to real data does not discharge that rule.** `--selftest` measured
> the sheet bootstrap at 6.2% on this corpus — real sheets, real cells, near nominal, and the
> number the paper published. It sampled condition-N split-halves, a population whose sheets
> all vary. `calibrate_estimators.py` splits *every* cell with six or more sheets, degenerate
> ones included, and measures **10.5%** on the same estimator and the same corpus.
>
> Nearly double, from nothing but a change of sampling frame. The corpus has 45 cells of 393
> whose sheets are near-copies; the first calibration could not draw one and so could not see
> the failure mode, while looking like a real-data measurement.
>
> **Before quoting an error rate, say which population it was measured over and check that the
> population includes the cases the estimator is used on.** And publish the rate from a
> command: the 6.2% was a docstring at `position_analysis.py:285`, never the output of
> anything, which is why nobody noticed which halves it had split.

## 52. A check whose remedy nobody applies is documentation, not a gate

> `check_sheet_attribution.py` was written on 2026-09-18, registered in `gates.py` at release,
> and ran green. It ends with the sentence: *"These must be excluded from any row that depends
> on item identity — the order and same-version floors above all — and the exclusion COUNTED
> where it is used."*
>
> **Nothing excluded them.** For a day the check ran, printed its instruction, exited 0, and
> the floors went on reading the 68 sheets it had just declared unreadable. The gate was green
> the whole time, because what it gates is its own ability to detect the problem.
>
> The cost was not zero. When the filter was finally wired into `floor_table.load()` the
> presentation-order floor moved from **106 pairs at side p90 7 to 97 pairs at p90 5**, and its
> endpoint max from 18 to 13 — a third of the floor's p90 was sheets scored against the wrong
> propositions. A number the paper leans on in two sections.
>
> **A check that reports a defect and a change that repairs it are two pieces of work, and
> finishing the first feels like finishing both.** When a check's output contains an
> imperative, either the code obeys it or the check is lying about being a gate. Wire the
> remedy in the same commit, and put it at the LOADER so it cannot be applied to one arm and
> forgotten on the next — see [[41]] for the other half of this, a criterion nobody checked was
> reachable.

## 53. A record derived from the data cannot validate the data

> 38 runs holding 8,705 records were collected by tools that never wrote a manifest, so the
> validator could only ever call them NOT VALIDATED. The tempting fix is to generate the missing
> `manifest.json` from the records. It would pass, forever, because a file derived from the data
> agrees with the data by construction — a red gate turned green while verifying nothing, which
> is the governing observation at the top of this file pointed straight inward. What a post-hoc
> pass *can* honestly buy is a **content freeze**: `manifest.derived.json`, named so it cannot be
> mistaken for the real thing, carrying sha256 per file so that from now on drift is detectable,
> plus a `NOT_RECOVERABLE` block naming what is gone (a model that failed every call left no
> file, so the attempted set is unknowable). The validator reports these as INVENTORIED — a third
> state that is explicitly not clean.

## 54. Writing a sidecar into a run directory can invent data

> The freeze above broke a generated paper block the hour it was written. `floor_table.py`
> globbed `runs/2026-08-30-ablation-pairs/*` and treated every entry as a model pair directory,
> so `manifest.derived.json` appeared in `PAPER-below-the-floor.md` as an ablation arm —
> *"ELIGIBLE but produced no arm-matched condition — investigate, this has no recorded reason"*.
> A generated block invented a model out of a sidecar file, and phrased it as a mystery. Any
> stray file would have done it. Glob for what you mean: `if os.path.isdir(d)`.

## 55. A layout the counter cannot read is a layout it reports as empty — again

> `count_records` had already been fixed once for exactly this, and its docstring says so. It
> tried `raw/`, `*.jsonl` and `*/*.jsonl`, and the ablation collector writes
> `<pair>/<arm>/<model>__<condition>.jsonl` — one level deeper. Two runs holding **364 records
> in 111 files** were reported as `none, 0 records`, while `run_inventory.py` counted them
> correctly, so two tools in this tree disagreed about whether a third of a thousand records
> existed. When you fix a "cannot see this layout" bug, enumerate the layouts that exist on disk
> rather than the ones you remember.

## 56. Closing a parity gate is not reviewing an export. Staging is

> `check_no_fork` reported 31 forks. Copying the private files over closed it in one command —
> 0 forks, thirty seconds — and that number was worth almost nothing. Running the **mirror's own**
> suite against the staged files is what found the cost: four of its tests were written against
> the implementations the private tree had replaced and failed on contact (`test_response_quality`
> patches `score.requests`, which the private `score.py` no longer imports at module level), and
> `check_skill_docs` caught the exported prose naming three scripts that had not come with it, so
> the export would have shipped documentation pointing at tools the mirror does not have. A
> parity check compares bytes. Only the receiving tree's gates can say whether the bytes work
> there.

## 57. A resolver that silently falls back exports a different analysis

> `studypaths.canonical_run` returns the repaired corpus **when it exists on disk** and otherwise
> returns the name it was given. That is a good default in the tree that has the repair and a
> silent downgrade in the tree that does not. Exported to the mirror, the corrected analysis
> quietly read the damaged `2026-05-25-full` instead of `2026-09-14-full-spliced` and reported
> 9 model rows where the writeup says 13, and 510 agreement items against a published 740. Three
> reference-value gates caught it; nothing in the resolver did. **Code that picks its own input
> at runtime carries a data dependency that travels separately from the code** — and a fallback
> that does not announce which branch it took turns that dependency into a wrong number rather
> than an error.

## 58. Judge a fork by set membership across the whole file, not by diff position

> Twenty-four of the thirty-one forks showed "public-only lines" under an ordinary diff, which
> reads as content the private tree lost. Nearly all of it was refactoring residue: a rewritten
> function makes every old line look deleted. The question that actually matters is whether each
> public line appears **anywhere** in the private file, and asking it that way collapsed 175
> suspicious lines to a handful worth reading — which then resolved as superseded implementations
> (the old `bootstrap_ci`, the old `count_records`, the old `partition`). Two still needed a human
> look because they were load-bearing rather than structural: a refusal-pattern list, and a table
> of observed values. Position tells you what moved; membership tells you what is gone.

## 59. Same flags is not same tool when the tool is a live checkout

> The dose series pinned nothing. `external/OBLITERATUS` is an editable install, and between the
> 2026-06-09 build of dose2/dose8 and the n=1 build chained behind the sweep on 2026-09-19 it had
> moved **234 commits**. Identical command-line flags produced an arm built by different code:
> `refinement_passes` came back 1 where 2 was requested, spectral certification moved RED →
> INCONCLUSIVE, and the KL is now reported under a named metric that makes it incomparable to the
> bare number the older builds recorded. The script that produced it carried a comment asserting
> "same base, same tool, same flags" — written by someone who had just documented this exact
> confound in another arm. **An external dependency you can `git pull` is an experimental
> variable.** Pin the revision for every arm of a series, restore it afterwards, and record it in
> the artifact; a build whose certification class differs from the other arms is not a point on
> their curve.

## 60. A wrapper's zero exit code is not evidence that the wrapped thing ran

> A build script asked the dose supervisor for `--doses 2`, and the supervisor — correctly —
> printed `dose=2: already ok, skipping`, because an output directory of that name already
> existed from a build three months earlier. It then exited **0**. The wrapper took that as
> success, renamed the pre-existing June build to the new revision's name, and stamped
> `tool_revision: 205d28a` into its metadata. A June artifact now claimed a September
> provenance, written by the same session that had spent the day documenting exactly that
> confound in another arm. Nothing failed. Nothing warned. The exit code was 0 and the log said
> what had happened, in one line, twelve lines up. **Read the log, not the status**, and when a
> step must produce a NEW artifact, build it somewhere nothing can already be — a fresh
> out-root, not a rename afterwards.

## 61. The intervention's tooling is not stable across its own parameter range — REINSTATED

> **Merged 2026-09-20 from the session that retested it.** That session numbered this entry 38,
> which is already *"Calibrate the CRITERION, not just the estimator"*; it sits between 60 and
> 62 here and keeps 61. The reinstatement below is theirs and is kept whole, because it rests on
> a fingerprint-verified revision and the withdrawal it replaces rested on the wrong one.

> **Withdrawn 2026-09-20 on a wrong attribution, reinstated the same day on the right one.** The
> rule is sound; the evidence I first gave for it was not. The failing build was attributed to
> `04b8ec6`, which built nothing in this series. Tested properly at `d6af36f` — verified by
> fingerprint as the tool that built dose2 and dose8 — it returns perplexity `inf` and coherence
> `0.0` at n=1, with 23.1 GB free. Two consecutive revisions fail; a later one succeeds.
>
> **The meta-rule that made the withdrawal correct still stands and is the more useful one:** the
> first version of this entry generalised from one build, on the same day, by the person who ran
> it, and named its revision from a shell variable rather than `git reflog`. That it turned out
> true is luck. Fifteen entries went into this file in one day and this is the one that was
> wrong — the one with an N of 1. **Being right later does not retroactively make one
> observation into evidence.**

> **Withdrawn 2026-09-20, the day after it was written.** The rule below generalises a single
> failed build into a property of the instrument, and it names the wrong revision: `git reflog`
> shows the series was built at `d6af36f`, while the failure was produced at `04b8ec6`, a
> revision this session checked out for the first time. So the comparison is cross-revision —
> exactly what rule 36 above forbids, written the same day. The series' own tool has a June log
> ending `REBIRTH COMPLETE` at n=1.
>
> **What survives is a rule about rules:** a durable lesson drawn from one observation, on the
> same day as the observation, by the person who made it, is not a lesson. It is a hypothesis
> wearing one. Fifteen of this file's entries were written in a single day; this is the one that
> was wrong, and it was the one with an N of 1. The original text is kept below unaltered.

> `n_directions=1` cannot be built by `04b8ec6`, the OBLITERATUS revision that produced the
> n=2, n=4 and n=8 arms. It returns perplexity `inf`, coherence `0.0`, KL `inf`, and empty
> generations on all three smoke prompts — a destroyed model, at the *weakest* dose, while every
> stronger dose builds fine. `205d28a` builds the same configuration cleanly (perplexity 6.844,
> coherence 1.0). So the dose series cannot be completed at its most informative point with the
> tool that produced the rest of it, and the choice is between an absent arm and an arm from a
> different tool. That is worth publishing rather than working around: **a dose-response curve
> assumes one instrument across the range, and here the instrument fails inside it.** It is also
> the likeliest reason the original n=1 build disappeared in June — it was produced by a path
> with no smoke gate, and the gate that exists now rejects that configuration outright.

## 62. A repaired corpus is a duplicate until the reader is told which one supersedes

> `studypaths.REPAIRS` has declared since September that `2026-09-14-variance-spliced` replaces
> `2026-05-26-variance`, and nine more pairs like it. `canonical_run()` honours that — **for a
> caller that asks about one run by name.** A caller that GLOBS every scored run gets both, and
> every record the splice carried forward unchanged is counted twice. That was unreachable while
> the repairs lived only in the private tree, and it went live the hour they were exported to the
> mirror: `judge_lean.py` reported 4,668 eligible judge records before the export and 6,651
> after, of which **2,967 were the same records again** — 44.6% of the corpus. The inflated
> spread was published to a website page within the hour, and an independent audit found it the
> same day; nothing in the repository could have, because the gate that checks the page read the
> same doubled corpus and agreed with it.
>
> Two rules out of it. **A resolver that protects one access pattern protects only that pattern** —
> `canonical_run()` is not a corpus policy, it is a lookup, and the glob was never covered.
> And **a check that shares a corpus with the thing it checks is not independent**: `key_numbers`
> agreeing with the page proved only that both were reading the same mistake.
>
> `studypaths.scored_corpus_paths()` is now the one selection, and it drops a base run only where
> its replacement is actually on disk. The claim survived — the spread is *larger* deduplicated,
> 0.3063 against 0.2926 — which is the only reason this was embarrassing rather than retracted.

## 63. A prerun gate must be answerable by the person about to spend

> `check_sheet_attribution` was registered at `prerun` on 2026-09-19 with the reasoning that
> attribution should be checked *in front of* spend — "one stops spend, the other stops
> publication." It sounded right. A test was written asserting it.
>
> It reports a property of the sheets **already on disk**: 68 of them cannot be mapped to
> propositions under either reading, and no future collection unmakes that. So it was
> permanently red, and it refused every subsequent run for a reason that had nothing to do with
> the run being proposed. It killed the `glm-5.3-flash` retry overnight and the operator found
> out eight hours later.
>
> **The test for a prerun gate is not "is this important before spending money". It is "can the
> person about to spend do anything about it".** A gate over an immutable fact belongs at
> release, where the answer is "then do not publish", or at `manual`, where the answer is "run
> it when the thing it measures can change" — here, when the PROTOCOL changes, because v2
> renumbering dissolves the ambiguity and a v2 arm cannot add to the 68.
>
> Related and distinct: [[52]] is a check whose remedy nobody applied. This is a check whose
> remedy nobody *could* apply.

## 64. A top-up into the same directory is not a re-collect, and it can create the defect it was fixing

> `glm-5.2` was pinned to a backend that stopped serving it: 25 HTTP 404s, zero successes in
> twenty-seven hours, 27 valid sheets already on disk from before. The OpenRouter catalogue
> listed 30 live endpoints, so the model was fine and the pin was stale.
>
> The overnight chain re-collected all four conditions pinned to a live backend, writing to the
> same run directory. `run_battery` correctly skipped three of them — *"5 valid runs already on
> disk, nothing to do"* — because the dead-pin sheets count as collected. Only condition A took
> one more.
>
> Result: **Mistral 27, Z.AI 1.** The model went from one serving path to two. Serving path is a
> same-version variant in this study, so the fix for an availability blocker created a routing
> blocker — the exact class of defect the chain existed to clear, on the same model, in one run.
>
> **A re-collect needs a new output directory or it is a top-up.** The collector's
> already-on-disk check is correct and is the thing that bites: it cannot know that the sheets
> it is counting were served by something that no longer exists. State the intent in the path,
> not in the commit message.

## 65. A learning written and not wired into a tool is a learning nobody else gets

> Four collection defects in one session on 2026-09-20. Two were written up as entries here
> within the hour. **None of the four changed a tool**, and the second one recurred inside the
> same session in a different form.
>
> | defect | learning written | tool changed |
> |---|---|---|
> | top-up counted dead-backend sheets toward a new pin | [[64]] | no |
> | repair collected into a directory no glob reads | no | no |
> | a prerun gate that could never pass blocked all collection | [[63]] | yes |
> | a retry printed "already at depth 5" and collected nothing | no | no |
>
> The entries are honest and they are worth nothing to the next person, who will not have read
> them at the moment the tool says *"5 valid runs already on disk, nothing to do."* That line
> was true. It was also the whole defect, and no reader of `LEARNINGS.md` is standing there
> when it prints.
>
> **A defect is closed when the tool refuses it, not when the file describes it.** The three
> fixes took under an hour between them: the collector now excludes sheets served by another
> backend from its already-have count and names the consequence; the inventory reports run
> directories no analysis glob reaches; the wave runner says which conditions it did NOT check
> before reporting a cell complete.
>
> The corollary is the harder half. **Writing the entry feels like finishing**, the same way
> [[52]] found that reporting a defect feels like repairing it. Both times the check existed,
> was correct, and changed nothing, because the work that would have changed something was a
> separate act nobody scheduled. Schedule it in the same commit.

## 66. A guard that skips the check on zero turns a worsening defect into a clean row

> `validate_runs` compared a manifest's model count to the models on disk, guarded by
> `if claimed_models and found_models and ...`. The guard is there for a reason: a
> manifest-less layout claims nothing, and `0 != len(found)` would fire on every one of them.
>
> It also meant a manifest whose model list had been **emptied** read as clean.
>
> `2026-09-14-recollect-may25` and `-ood` were listed in `KNOWN` for naming ONE model against
> 7 and 8 on disk. Both manifests were later overwritten with `models_attempted: []`,
> `calls_completed: 0`. The mismatch stopped firing — not because anything was repaired, but
> because the manifest now claimed nothing at all and fell through the guard. The registry-rot
> report then did exactly what it is built to do and said: *"these are listed as known and no
> longer occur. Remove them from validate_runs.KNOWN. A stale exemption hides the next
> defect."*
>
> **Following that instruction would have deleted the record of a defect that had got worse.**
> The same shape as [[44]] — the check was not wrong about what it measured, it was wrong about
> what its silence meant.
>
> Two changes, both in the same commit as this entry, per [[65]]:
>
> - a manifest that names NO models is now its own finding (`manifest-names-no-models`), so
>   "cannot be checked" is a row rather than an absence. It fires on **seven** run directories
>   that had been reading clean — all seven the same September recollect family.
>
>   **This entry said NINE until an adversarial review counted them, 2026-09-21.** Nine was the
>   count at an intermediate state of the same session, before the check learned to read the
>   `models` roster that the pre-registered arms write; two of the nine then resolved
>   correctly and the number was never re-run. The commit message carries the same nine.
>   Writing a count from the middle of the work and not re-measuring it at the end is the
>   small version of the thing this whole file is about.
> - the check reads the key the collector actually wrote. `run_study` writes
>   `models_attempted`/`models_completed` after the fact; the pre-registered arms
>   (`run_omission_orders`, `run_paraphrase`) write a `models` roster BEFORE the first call,
>   which is a *stronger* provenance claim. Reading only the first pair reported every one of
>   those arms as naming no models, and hid the one that matters: **`2026-09-18-omission-hosted`
>   names 2 models in a manifest whose own `_note` says the roster was fixed by the
>   pre-registration and written before the first call. Eighteen models are on disk.**

## 67. A probe is a collection, and the collector does not know the difference

> Two sheets, run to answer one availability question — is `z-ai/glm-5.2` served at all, after
> 27 hours of 404s under its pin had it classified as gone? It was. The probe cost about a
> cent and did three things nobody asked for.
>
> **It landed in another run's directory.** `smoke_roster.OUT` is the literal string
> `"2026-09-18-roster-smoke"` — a fixed date, not today's — so every invocation of that
> collector, forever, writes into the 2026-09-18 smoke's directory.
>
> **It overwrote that smoke's manifest,** which is written mode `"w"`. The record of
> *22 candidates, 16 working, 6 not bought, each with its reason* became *2 working*. PLAN.md
> cites that manifest by path for the figure "22 candidates, 16 work", so the citation was
> false for about an hour. It was recoverable only because the 22 record files were untouched
> and `smoke_roster.verdict` could be re-applied to them — luck, not design. Re-deriving it
> reproduced 16 and 6 exactly.
>
> **And two sheets moved a published table.** `runs/**` is swept by the catch-all globs, so
> the paper's refusal block went from `z-ai 1% (134)` to `1% (136)` on data collected to
> answer an availability question. A probe that changes a denominator in the paper is not a
> probe.
>
> [[64]] is this learning, written two days earlier, about the same model, by someone who had
> read it. It did not stop it, because it is phrased as advice to an operator who is
> *collecting*, and this did not feel like collecting. **That is the general failure: the
> intent is in the operator's head and the directory is on disk.**
>
> Three changes, in the same commit as this entry, per [[65]]:
>
> - `smoke_roster` takes `--out`, and **refuses** to write into a directory whose existing
>   manifest covers models this invocation does not — naming what would be lost. It now
>   rejects the exact command that caused this, before spending anything.
> - the probe's records live in `probes/`, outside `runs/`, so nothing sweeps them. The
>   corpus is byte-for-byte what it was, and `gen_paper --check` is clean again.
> - `run_inventory` records why that directory is not in `runs/` at all, rather than listing
>   it as a fixture: **declaring it a fixture would not have been enough**, because the
>   catch-all sweep reads `runs/**` and does not consult the fixture list. The fixtures
>   already in `runs/` have the same problem and it is `RESEARCH-BACKLOG` §22.

## 68. A denylist of directories that no longer exist subtracts nothing

`refusal_table.DEFAULT_EXCLUDE` named seven run directories to withhold from the refusal
panel, each with a paragraph of defended reasoning. By 2026-09-21 **all seven had been
retired to `withdrawn/`**, so the set removed nothing from a glob that had meanwhile grown by
eleven collections — a 448-sheet paraphrase arm at one condition, three omission arms at two,
two rung-2 arms, a 22-model one-sheet roster smoke and a 71-model budget probe. Every one of
them is excluded by a rule written in that file's own comments. The published corpus figure
was **6,286 runs and 71 models**; the declared panel is **3,897 and 65**, and the published
condition ordering A > N > D > P became A > N > P ≈ D.

A denylist has to be edited each time an arm is collected and forgetting is silent. An
allowlist plus a classification check fails the other way: `PANEL` names the population,
`OUT_OF_PANEL` names each exclusion with its rule, and a battery run in neither **raises**.

**The rule: a population is declared, never left as whatever a glob returns minus a list of
names someone remembered to type.** The exclusion reasons are worth keeping; they are not a
mechanism.

## 69. Gating the digit does not gate the quantifier

The paper read *"9 models decline it without a directive; give those same models a firm
instruction and **all 8 of them stop**."* The 8 was generated and correct. "All" was typed,
and false from the collection that made `declining` 9 while `silenced` stayed 8 — one model
declines under every condition. The gate substituted an integer into `"all %d of them stop"`
and could not see the word in front of it.

The phrase is `"%d of them stop"` on every surface now. **A phrase that is true under both
outcomes is the only kind a gate can defend**; a quantifier baked into a template is an
ungated claim wearing a gated number's coat. Same shape as [[10]], one word further left.

## 70. A headline p-value needs a command, and `grep -ril fisher` returned nothing

Two results documents reported this study's numbering contrast with a Fisher exact test —
`p = 1.8e-4` local, `p = 8.4e-4` hosted-pinned. **No file in the repository computed a Fisher
exact test.** The local figures happened to be right; the pinned ones were not. Recomputed:
**9 of 190 against 0 of 192, p = 0.0017**, not 10 of 191 at 8.4e-4, and the mixed-backend row
was **p = 0.011**, not 0.34 — which reversed the document's conclusion from "pinning produced
a result that was not there" to "pinning sharpened one that was".

`scripts/omission_arms.py` now computes it, exactly, in integers, with a selftest against
tables whose answer is known independently (tea-tasting 17/70, clean separation 1/6). It
imports `item_omission.load_sheets` rather than reimplementing what a partial sheet is, so
the two cannot drift.

**The rule: a number in a results document that no command produces is a number nobody has
checked, including the person who wrote it.** The narrower rule is [[45]]; this is its form
for statistics rather than artifacts.

## 71. A withdrawal registered only in prose protects one paragraph

§7 withdrew the same-version magnitude and explained why at length. §8, forty lines later,
still read *"on our measurement it produces a median of 5 items and up to 24"* — the retired
62-item figure, in the same document, unnoticed by four passes. §1 called the 16-of-37
placebo count "published, and false"; §1b cited it as live. §3 named a governing limit of 10
where the generated table says 7. §6 asserted that "sampling variability is zero" at
temperature 0 while §2 measured 10 of 57 cells byte-identical.

None of the four was in `RETRACTED`, so `--check-retractions` passed over all of them across
193 files. All four are registered now.

**The rule: withdrawing a claim in prose and registering it in the retraction list are two
actions, and only the second one scales.** Also fixed: `_stale_twins` read raw lines, so
`**7 items of 32**` and a wrapped sentence both defeated it. It reads unwrapped,
un-emphasised text now, like the existence check beside it.

## 72. An alignment test blind to a third category reports "perfect"

`check_confound` asked whether any item is documented-and-generic or
normative-and-jurisdictional. The bank's one `contested` generic pair is neither, so it fell
through both tests, `aligned` returned True, and the generator printed **"All 10 generic
items in the bank are normative"** into the paper over a set where nine are. A test asserted
that behaviour, so the defect had a passing gate in front of it.

The right question is whether each side is **exhausted** by its expected claim type, which a
category nobody anticipated cannot slip past. The block now reads "near-collinear" with the
measured counts, and the test asserts the counts rather than the phrase.

**The rule: a test for "nothing crosses the diagonal" is not a test for "the partition is
exact", and the second is what a word like *perfectly* claims.**

## 73. A parser that returns None on an unknown token skips the edit it exists to catch

`check_citation` read the abstract's counts through a lookup table from "ten" to "sixteen".
Planting **"Of forty published studies audited"** produced no finding at all: the word was
unrecognised, the count came back None, and the branch skipped. The three plants that landed
inside the table were caught; the one outside it was not, and nothing said so.

An unreadable token in a counted slot is now a **refusal** — "this gate cannot read it as a
number, so the count was NOT checked". Same family as [[1]] and [[66]], in a parser rather
than a counter.

Worth recording separately: before this pass that file recomputed **2** of the abstract's
12 measured figures, and the abstract mints a permanent DOI. Planted `0.931` and `86.6%`
returned *Fit to mint*.

## 74. A paper's completeness needs a gate, or an arm can be finished and never appear

On 2026-09-21 this repository held 13 pre-registrations and 6 results documents. The paper
cited **one**. Two of them carried findings the paper made no mention of, including the
numbering artifact — measured 09-18, fixed in the collector the same day, still unpublished
on 09-21 while §1 promised the reader it was in §3.

Nothing could have noticed. Every other gate asks whether what the paper says is true; none
asked whether what is true is in the paper.

`tests/test_every_prereg_is_cited.py` requires the paper to NAME each file — not discuss it,
which is a judgement and gets switched off, just make it reachable. Exemptions are declared
by name with a reason and are themselves checked for staleness.

**The rule: a study that argues the field should publish what it measures needs a check that
it published what it measured.**

## 75. A read-modify-write over minutes will silently eat an edit made in those minutes

`gen_paper.py` reads `PAPER-below-the-floor.md` whole, runs twelve subprocesses — one of them
a 4000-draw bootstrap over every pair — and then overwrites the file with the copy it read.
That gap is minutes wide.

On 2026-09-21 a **thirty-line correction to §2** was written during one of those runs. The
edit reported success. A `grep` immediately afterwards confirmed the old text was gone.
`key_numbers --check` passed, `gen_paper --check` passed, the test suite passed. Then the
generator finished and wrote its stale copy back, and the section reverted to a table of
retired-corpus numbers whose conclusion was the opposite of the live one.

**Nothing detected it.** Every gate in the project was green over reverted text, because each
gate checks whether the prose matches the data and the reverted prose had been consistent with
*something* once. It surfaced only from re-reading the section by eye, hours later, for an
unrelated reason.

Two changes:

- `gen_paper` re-reads the file before writing and **refuses** if it changed, naming what it
  would have overwritten. The generated blocks are cheap to recompute; a hand edit is not.
- The working rule: **do not edit a file while a background job that rewrites it is running.**
  Launching the generator and then editing the thing it is generating into is the same bug as
  a top-up into a directory a collector is still writing ([[64]]).

The general shape is worth naming because it is not a race in the usual sense — there is no
concurrency primitive to reach for and no error to catch. One process is simply holding a
stale copy of a file it intends to be the author of.

## 76. "Clean" is not a state a long turn stays in — re-read what you changed

Corollary of [[75]], and the reason that revert survived as long as it did: after a fix, the
instinct is to run the gate and move on. The gate answers "is the prose consistent with the
data", which the reverted prose was.

The check that would have caught it is the cheap one nobody runs: **grep for the sentence you
just wrote.** Not for the number — for the wording. A number can be right in two different
sentences; the sentence you wrote exists in exactly one state.

## 77. An allowlist keyed on a name that changed exempts the thing it exists to check

`validate_runs.py` has an escape hatch for runs belonging to other workstreams: a manifest
whose `schema` does not start with `compass-run` or `bias-study` is reported NOT VALIDATED
rather than judged against collection rules it was never written to. That hatch is correct and
it is needed — the evidence-collection and residency-probe runs share the `runs/` root.

On 2026-09-17 the instrument was replaced and the collector began stamping `battery-run/1`.
Nobody touched the allowlist. So from that day, `2026-09-16-ratchet-v3-wave` — **3,897
records, the corpus every published figure in the paper is computed from** — was classified as
another workstream and skipped, with the printed reason:

> another workstream's data under the same root; no battery record and no published number
> depends on it

Every clause of that is false, and it sat in the release checklist for five days.

Adding `battery-run` to the allowlist made the run fail immediately, on a real finding: the
manifest declared no `analysis_seed`, so every bootstrap over the panel had been inheriting
`studypaths.LEGACY_SEED` — the May study's frozen constant — by silent fallback. Nothing moved
when it was declared, because declaring it wrote down the value already in use. That is the
best case; the point is that no gate could have told us either way.

The rule: **when you rename a thing, grep for the old name in every allowlist, denylist and
prefix test, not just in the code that produces it.** [[68]] is the same shape with a denylist
(seven directories that no longer existed, subtracting nothing). This is the shape with an
allowlist, and it is worse, because a denylist that matches nothing fails open loudly while an
allowlist that matches nothing fails open **quietly and with a reason attached**.

## 78. An exemption prints as a dash; nobody reads dashes

Corollary of [[77]], and the reason it survived five days in a checklist that was run
repeatedly. `validate_runs` prints three things: `ok`, `FLAG`, and `--`. The panel wave printed

    --   2026-09-16-ratchet-v3-wave  files=440 records= 3897 scored=n  [flat layout, not validated]

which reads as housekeeping. Eleven other runs printed the same dash for a different reason.
A reader scanning for red sees none, and a column of identical dashes is invisible by the
third one.

**A gate must make its exempted population as legible as its failures.** The remedy that
worked was not a new check: it was reading what the dash *said*, once, out loud. Any line a
gate prints that is neither a pass nor a failure is a line that needs a human to have agreed
with it at least once, and there is no mechanism that forces that agreement.

## 79. The remedy must not destroy the evidence

`validate_runs` names the fix for an unfrozen run in its own output:

    the remaining 12 hold no freeze; run `python scripts/derive_manifest.py --write`.

`--write` overwrote any existing `manifest.derived.json` unconditionally. So the documented
remedy, run on a corpus whose records had **changed** since the freeze, re-froze the new bytes
and printed `wrote 1` — erasing the only artifact that could ever have said the data moved.
The freeze's entire purpose is that a later `--check` can say a record file drifted.

Found by reading the writer while fixing [[77]], not by any failure: the drift path had never
been exercised. `--write` now compares against an existing freeze first and **refuses** on
disagreement, exiting 1; clearing it takes `--refreeze`, which leaves a flag in the shell
history saying a freeze was replaced rather than written. Held by
`test_write_refuses_to_re_freeze_records_that_moved`.

The general rule: **for any tool that both detects a condition and repairs it, check what the
repair does to the detector's evidence.** A repair that makes the detector agree is not a
repair. This is LEARNINGS 1 with a hash attached.

## 80. A correct exclusion that nothing states is half of the defect you are criticising

`floor_table.py` drops 79 sheets whose answers cannot be attributed to the propositions they
answer — both the item-id reading and the slot reading score at chance on the 16 mirrored
pairs, so the record does not say what they answered. That exclusion is right, it is
implemented, and it counts the drop.

The paper did not mention it. Not in §9, not anywhere: `grep -i unattributable
PAPER-below-the-floor.md` returned nothing on 2026-09-21.

§5 of that same paper objects to Liu deleting any sheet containing one unusable answer, and to
Barmettler imputing missing values to the neutral midpoint. The objection is not that they
dropped data; it is that the reader cannot see the rule or its size. **We had the good half
and not the visible half**, which from outside the repository is indistinguishable from having
neither.

Fixed by the pattern this project already uses twice (`data/empty-records.json`,
`data/collection-limitations.json`): a declaration file carrying the count per model, a gate
that fails when the corpus and the declaration disagree, and three gated numbers so the prose
cannot drift from either. Note which half was cheap: the filter took real work, the
declaration took an afternoon, and only the declaration is load-bearing for a reader.

## 81. Declaring a structural classification per run rebuilds the stale-exemption machine

`selftest_analysis.G8` asserts that `validate_runs` reports exactly the findings named in its
`KNOWN` registry and nothing else — a good gate, and one already improved once by **reading**
the registry rather than keeping a second copy of it.

Freezing eleven flat run directories made G8 fail with eleven new
`(run, inventoried-not-validated)` pairs. The obvious fix is to add eleven names to `KNOWN`.
That is the wrong fix, and the reason is worth stating: `KNOWN` names **defects that are
understood and will not be fixed**. `inventoried-not-validated` is not a defect, it is a
statement about what kind of directory this is, and it attaches to every run of that kind — so
per-run declaration means every future collection must add a line to a registry in another
file before a green gate is possible. That is the stale-exemption machine this project has
dismantled twice ([[68]], and `validate_runs`' own REGISTRY ROT check), and it rewards the
wrong action: facing a red gate, a reader adds a name instead of freezing the run.

The two structural codes are now waived by code, not by name, and each is gated at full
strength elsewhere — `derive_manifest --check` re-derives every frozen hash, and the ownership
allowlist is held by the test written for [[77]]. A run with **no** freeze reports a different
code, which is not waived and still fails.

**Before adding a name to an exemption registry, ask whether the thing you are exempting is a
defect or a category.** Registries are for defects. Categories belong in code, beside the rule
that says why they are a category, with the check that still holds them.

## 82. A hand copy of a generated table is the defect the generator was built to remove

`gen_paper.py --check` verifies thirteen blocks and reported "all generated blocks are
current" throughout. On 2026-09-22 the paper still contained **six hand-typed tables** whose
numbers the generator had no idea existed, and five of them were stale:

| where | said | live |
|---|---|---|
| §1b, refusal by condition | 1622 runs under N, 650 under A, 12.2% | 673, 675, 11.6% — every cell |
| §1b, the same table AGAIN, sixty lines lower | A 15.3% / 11.4% | disagreed with the copy above it as well |
| §2, like-for-like order vs manipulation | 85 pairs, p90 10 / 25 pairs, p90 7 | 107, 3 / 61, 4 |
| §2, the class split | local 19 pairs p90 11, frontier 75 p90 3 | 23 p90 6, 84 p90 1 |
| §2, "frontier models only" | mislabelled — those are the POOLED rows | cannot be made frontier-only: the same-version arm is 24 pairs |
| §4, judge fan-out | all twelve cells, plus 4,668 records and a spread of 0.29 | 3,809 and 0.3054 |

Two of them sat **three lines under a sentence telling the reader to read the generated table
instead of a copy.** Both copies overstated the very split they were printed to demonstrate.

The shape is specific and worth naming: generating a table removes the risk from the table and
**relocates it to every sentence and copy around the table**. A generator makes the artifact
trustworthy and makes the prose beside it *look* trustworthy, which is worse than before,
because the reader has been told the numbers are computed.

Two things to do, and the second is the one that generalises:

- Where a copy is redundant, delete it and point at the block. The argument usually survives:
  it was about which rows to compare, not about their values.
- Where the prose restates a cell, **register it in `key_numbers`**. That is what the gate is
  for and it was not being used for the paper's own lead: §1's `38 of 61`, `0.131`, `43%`,
  `0.088` and `1.5 times` were all unregistered until this pass. Gated numbers went 59 -> 90
  in one sitting, and every one of the additions was a sentence nothing had ever checked.

A scan that finds them takes ten lines: walk the markdown, mark the `GEN:` spans, and print
every remaining table of three rows or more.

## 83. "All load-bearing numbers match" is a statement about the REGISTRY, not the paper

The sentence `key_numbers --check` prints -- *"all 59 load-bearing numbers match the paper's
sentences"* -- is true and is read as "the paper's numbers are correct". It means the numbers
somebody registered are correct, and nothing in the output says how many were not registered.

`ungated_numbers.py` inverts it: which claims are registered at all, and print the remainder.
First run, 133 registered phrases against 457 numeric tokens, leaving **149 sentences nothing
had looked at since they were typed**. Working that list produced every finding in [[82]] plus
eight more: `Eighteen models decline` against 13, `Nine of them` against 8, `every model has
between 7 and 17 runs per condition` against a real range of 3 to 20, `99.6%` against 99.7%,
`0.5-29.8%` against 0.5-28.9%, `24-30%` against three items at 23.9 / 26.5 / 28.9, and -- the
worst one -- a self-criticism claiming the judge spread was *"larger than one of the five
effects this project published"* when `judge_lean.py` prints, in its own output, *"the study's
CI-clean findings are +0.90, +0.45, +0.43. A judge-composition spread of 0.3127 is larger than
none of them"*, and there are three such findings, not five.

**An overstated self-criticism is still a claim the paper cannot support.** It reads as
candour, which is exactly why nobody re-derives it.

Two refinements the tool needed, both about not punishing the right action:

- Blockquotes and `*(...)*` correction notices are held back by default. They state what a
  figure USED to say, so gating them against the live value would force them to lie -- and
  counting them made the review list GROW every time a correction was written.
- The remainder is a READING list, not a defect list. Most of it is legitimately ungated:
  quotations, methodology, historical narration. The tool makes no judgement and says so.

## 84. A guard that fires on a true statement teaches the wrong fix

`test_no_phrase_template_hides_a_second_number` is a good gate: a phrase like
`"our order floor is p90 %d, max 24"` checks the p90 and silently asserts the max. It fired
three times in one pass on phrases that were correct.

- It stripped `%d` and `%s` before scanning for stray digits, so **`%.3f` read as a hidden
  literal 3** -- and its sibling test counted the same phrase as having ZERO placeholders.
  Every float-valued claim was unregisterable, which is why §1's medians and §4's judge spread
  had never been gated.
- It flagged the `6` in `` `gpt-6-astra-pro` ``. That is a model generation inside a code
  span, not a quantity.

Both fires pointed at the tempting fix -- reword the phrase, drop the model name out of the
anchor -- and the model name is precisely what makes the anchor unique. **When a guard fails a
statement you have just verified by hand, fix the guard, and write down what class of true
statement it could not see.** A guard is an assertion about the world too.

The general form, and it is the same one as [[77]]: a check whose field of view is narrower
than its claim. This file now has four entries of that shape, at four different layers -- a
schema allowlist, a glob, a resolver, and a regex over a format string.

## 85. The surface nobody reads end to end is the one still publishing the withdrawn result

`key_numbers --check-website` gates 51 statements across five surfaces and had been green for
days. On 2026-09-22 `evilrobots.lol/research/ai-bias-audit/` — the public page, the one a
reader actually lands on — was still publishing:

- **its headline floors table**, hand-typed, three rows stale and two rows naming arms that do
  not exist on this instrument. It sits inside a section whose opening paragraph had already
  been updated to say the instrument is the 32-item battery.
- **a chart built from the retired questionnaire**, caption included: *"side-flips of 62"*.
- **the generational split in the version the paper retired on 2026-09-19** — a frontier
  manipulation "small but real" at median 2.5 / p90 5, and item order dominating the 2024
  models at p90 12 against 8. Both reverse on the live corpus. Sixteen days.
- **a self-contradiction three screens wide**: the middle of the page says the corpus and the
  MIT-licensed instrument ship; the last section said the instrument "is not ours to republish
  and is not there."
- **a duplicated-text corruption** in the controls-audit paragraph, ending on the claim that
  our accusations about other people's methods were "ours to stand behind and not yours to
  check" — which stopped being true the day the questionnaire was thrown away.

None of it was registered, so none of it was checked, and the green verdict covered the page
the way it covers everything: completely, over the fraction somebody enumerated ([[83]]).

**Why the website is worse than the paper, structurally.** It lives in a different repository
from the analysis. The paper sits beside the scripts and gets re-read whenever a number moves;
the page is edited when there is something to announce. So the page accumulates dated update
sections that each looked right when written, and the correction that retires one of them
lands in a document the page's author is not holding. `--check-website` exists precisely
because of that split, and it only reaches what has been named.

The remedy is the same tool pointed at the other tree, which costs nothing:

```bash
python scripts/ungated_numbers.py --paper <site-page>.md
python scripts/ungated_numbers.py --paper <site-page>.md --tables
```

**And the specific trap: a dated update section is not a licence.** "Update, 2026-08-31" reads
as a record of what was true then, so a stale figure inside it feels archival. It is not,
when the section's own first paragraph has since been rewritten to describe a different
instrument — at that point the header says battery and the table says questionnaire, and the
reader has no way to tell which half is current. Either the whole section moves, or it carries
a supersession line at the top. Half-updating a dated section is worse than not touching it.

## 86. A generator that cannot find its input publishes the absence as a fact

`gen_deviations.py` builds `PROTOCOL-DEVIATIONS.md` — the record a reader checks the paper's
arms against — partly from a glob of `PREREG-*.md` at the tree root. The study keeps its
pre-registrations there. **The public mirror keeps them in `prereg/`.**

Run in the mirror on 2026-09-22 it found none, wrote the document with the **entire
pre-registration index missing** — thirteen rows, including `PREREG-2026-09-14-i3-phase4.md`,
the main forced-choice collection every published figure in the paper comes from — printed

    wrote PROTOCOL-DEVIATIONS.md (183 lines)

and exited 0. A `--check` run immediately afterwards agreed with it, because `--check`
re-derives from the same glob.

This is [[77]] one layer up, and the extra danger is specific. A failing *check* says something
is wrong. A generator with a blind spot **produces a clean artifact that asserts the missing
thing does not exist**, and every downstream gate then agrees with it. The document did not
look damaged; it looked like a study with no pre-registrations.

Two changes, and the second is the general one:

- The resolver reads both layouts.
- **The generator refuses to write when a section it always fills comes back empty.** Every
  tree that carries this generator carries pre-registrations, so zero means the resolver missed
  them, not that there are none. Same rule as [[66]] and the vacuous-pass family, applied to a
  writer rather than a checker: *print the count, and refuse on zero.*

It surfaced only because the release gate noticed a different thing — the shipped document
named a script that did not ship — and because the regeneration was read as a **diff** rather
than as an exit code. `git diff` on a generated file is the cheapest review in the project and
it is the one that is skipped, precisely because the file is generated.

## 87. A generator and a commit hook can disagree forever about one byte

Two instances on 2026-09-22, in the same hour:

- `gen_paper.py` right-pads the fixed-width blocks, so `power` and friends emitted lines
  ending in spaces. The public mirror's `trim trailing whitespace` hook removes them at commit
  time.
- `gen_data_dictionary.py` ended its output with a trailing BLANK line. The same repository's
  `fix end of files` hook removes that too.

In both cases the loop is closed and silent: commit, the hook edits the file, `--check` now
reports it stale, the remedy is to regenerate, and regenerating re-creates exactly what the
hook just removed. Nobody is wrong and nothing converges. The first one also made the two
trees' copies of the paper differ on every sync, which is how it was found — a whitespace-only
diff between files that are supposed to be identical.

Neither is visible in rendering. **The only thing a defect like this can ever do is cost
somebody an afternoon**, which is exactly why it survives: it never looks urgent enough to
chase, and it makes a gate cry wolf until somebody switches the gate off.

The rule: **a generator's output must already satisfy every formatter that will touch the
file.** Whitespace, final newline, line endings. If a hook edits what a generator wrote, one
of them has to yield, and it should be the generator — a hook applies to the whole repository
and a generator applies to one file.

Corollary worth its own line, because it is how both were caught: **two trees holding the same
generated file should be byte-identical, and a diff between them is a finding.** That
comparison costs one command and it found both of these. [[86]] came out of reading the diff
of a regenerated file instead of its exit code; this is the same habit pointed sideways.

## 88. `withdrawn/` names a panel decision, not a licence to delete — read the records

The 2026-09-22 purge removed the retired questionnaire's corpus and, with it,
`withdrawn/backend-split-precollection/`: 40 sheets, 196 records, all on the **live** battery
(`ratchet-battery` 149, `ratchet-battery-v3` 47), ten models each served by two to four
different backends, 22 distinct providers. That is the primary evidence for the routing
confound `PREREG-2026-09-14-i3-phase4.md` line 3 exists to remove. It went because of the
directory it sat in. Nobody opened a record.

The same pass deleted `withdrawn/i3/ITEM-READ-2026-09-15-i3-bank.md` and
`ratchet-propositions-i3.json` — the receipts for a withdrawal the live pre-registration
argues from. Amendment 2 justifies retiring that bank by stating the sign-off box is empty and
the bank holds 60 items in 30 pairs. The sheet carries 32 checkboxes, none ticked; the bank
carries 60 items and an in-band `withdrawn_reason`. **Keeping the claim and deleting the
receipt is the move this study convicts other people of.**

The test, and it costs two commands: read the `instrument` field out of the records
themselves, then grep the live tree for the directory name. Records first, then references. A
directory nothing names and whose records carry a retired instrument is a candidate for
deletion. Anything else is evidence.

Deletion is still sometimes right — the compass corpus went because its 62 propositions are a
third party's licensed text that can never ship, and the **findings** survive in
`withdrawn/results/`. But a deletion must be written down, and it now is, in
`withdrawn/README.md`. A silent purge and a lost dataset look identical six months later.

Related: [[75]] — the pass that made this mistake was also editing files while a verification
read them.

## 89. A test that passes alone and fails in the suite: three wrong causes before the right one

`scripts/test_analysis_plumbing.py::test_gated_values_are_not_none` failed on 2026-09-22 in
every full run of the study suite and passed every time it was run alone. Three explanations
were entertained and written down before the real one, and the wrong ones are the lesson.

**Wrong answer 1: "concurrency across the trees."** The first failures happened while
`release_check.py` ran in the mirror, and `key_numbers._corrections_entries` and
`release_check`'s `MIRROR` deliberately read across the tree boundary. Plausible, tidy, and
false — the test went on failing with nothing else running.

**Wrong answer 2: "flaky."** One run produced **39** failures with `NameError: name 'groupby'
is not defined` raised inside CPython's own `statistics` module. A wedged EPUB build from an
earlier session had been spinning for nine hours on a full core — the EPUB builder from the
author’s unrelated publishing repository, not a script of this study — 32,550
seconds of CPU, no output written since 03:47. Starvation produced impossible-looking
failures. It was real interference, and it was still not the cause: after killing it, one
failure remained, exactly the same one.

**Wrong answer 3: "declare the key as legitimately absent."** The test's own message invites
it — *"or it needs to be declared here with the reason it can be absent"* — and the exemption
lists already exist. Adding `gradient_defender_min` to them would have passed the suite and
buried a live defect under a documented category. **An exemption offered by an error message
is not evidence that the exemption is correct.**

**The cause, found by bisecting 101 test files in halves:**
`tests/test_studypaths_two_corpus.py` sets `STUDY_ROOT` with `monkeypatch.setenv` and then
`importlib.reload(studypaths)`. `monkeypatch` restores the environment variable at teardown
and **cannot restore the module** — `STUDY_DIR` is computed at import, so the whole process
went on resolving the corpus to a tmpdir. `item_gradient.gradient()` then read zero records,
`key_numbers.item_gradient_bounds()` swallowed the empty result behind `except Exception:
return {}`, and the key arrived at the gate as `None`.

Two fixes, both at the class rather than the instance:

- An autouse fixture in `conftest.py` restores the resolver after every test and asserts that
  it came back. `tests/test_validate_runs_layouts.py` already carried a hand-written
  workaround for the same leak, with a comment saying it "depend[ed] on whatever the rest of
  the suite had last pointed it at" — a second victim documenting the disease instead of
  curing it.
- `item_gradient_bounds()` now catches `FileNotFoundError` only. A bare `except Exception`
  turns a broken resolver into a missing measurement, and a missing measurement is the one
  thing this gate is not allowed to report as absent-by-design.

The general rule: **a test that passes alone and fails in the suite is reporting process
state, not a measurement.** Suspect a module reloaded against a fixture, an environment
variable set outside `monkeypatch`, or a cache primed under one root. And when the suite
disagrees with a single-test run, the suite is usually right about there being a problem and
wrong about what it is.

## 90. A human-review note that states its own coverage must measure what it covers

`release_check.py`'s item 4 read **"CORRECTIONS covers every withdrawal -- READ 2026-09-12,
PASSES. All 14 entries read"** as a fixed string, and went on printing it while
`CORRECTIONS.md` grew to 27 entries. It sits under a heading that tells the operator these
items are *outstanding*, which is exactly what makes a stale one dangerous: it reads as
diligence. Thirteen entries had never been read by anyone and the gate said the read passed.

It now freezes the read date and the count read, measures the file, and prints the difference:
`** 27 entries now: 13 ADDED SINCE THE READ AND NOT COVERED BY IT. **`

Two traps found while fixing it, both worth more than the fix:

- The first version appended the drift line conditionally. `HUMAN_CHECKS` is counted by
  `tests/test_release_counts.py` against RELEASE-2026-09-07's "the split is N mechanical and M
  human" sentence — **by list elements** — so a document drifting made a release gate fail.
  A warning must not change the shape of the thing it warns about; the drift line rides inside
  the head element.
- The count looked in the wrong tree first and returned `None`, which rendered as *"cannot be
  confirmed from here"* — a shrug where a number belongs. `CORRECTIONS.md` is public and lives
  in the mirror. This is the third script to need that resolution, after `key_numbers` and
  `release_check`'s own `MIRROR`; reuse it rather than writing a fourth walker.

Same shape as [[86]]: the failure mode of a check that cannot find its input is to report the
absence as a fact about the world.

## 91. "Published" means pushed — check `origin/main` before writing that word

Entry 27 of `CORRECTIONS.md` was drafted saying a **public** document had for a week told
readers to discount figures the repository was already shipping the repair for. It never
reached a reader: `origin/main` is at 2026-09-13, and both the document and the repair export
sit in 81 unpushed commits.

The correction is still owed — what this repository asserted is its git history, not its push
log — but the entry must say which it was, and an entry that quietly omits its own reach is
the shading the file exists to refuse. Checking costs one command:
`git merge-base --is-ancestor <commit> origin/main`.

Run in the other direction it is equally load-bearing. `CORRECTIONS-2026-09-08.md` **was**
public (`072db15` is an ancestor of `origin/main`) and was deleted on 2026-09-22 by a pass
removing the retired questionnaire, which it was not about. Deleting a published correction
record is the one thing a corrections document may never do, and the only reason it was caught
is that the same command was run on it. Restored, with a banner.

The general form: before describing any artifact as published, withdrawn-in-public, or
unreleased, ask git which it is. Committed is not published, and unpushed is not unwritten.

## 92. A withdrawal is a STATE with an invariant, not an event you write down

On 2026-09-22 four failures of the same invariant were live at once, in a tree whose gates
were green:

- The five published nulls were withdrawn on 2026-09-18 and were still asserted on 2026-09-22
  in the pushed README, in `LESSONS.md` at **both** refs, in two `results/` documents, and on
  the live research page. `--check-release` passed throughout, because not one phrase for them
  had ever been registered.
- `CORRECTIONS-2026-09-17-power.md` was cited **ten times inside the public mirror**, three of
  them in the paper, and was not in the mirror.
- The evidence behind two withdrawals had been deleted outright and was restored from git.
- The retired questionnaire had already been purged twice and come back twice — commit
  `42133649`'s own title.

Four different patches had been applied, one per surfacing, and none of them generalised. The
cause is one thing: **nothing owned the invariant.** The same withdrawal was recorded in up to
six places that could disagree — a dated `CORRECTIONS-*.md`, the mirror's numbered
`CORRECTIONS.md`, a `WITHDRAWN` block in `FINDINGS.md`, a hand-typed phrase in
`key_numbers.RETRACTED`, a row in `PROTOCOL-DEVIATIONS.md`, and a banner on the `RESULTS`
file — and no tool reconciled them.

**The invariant, four clauses, each one a defect actually paid for:**

1. **ABSENT** — no phrase of the claim appears on a gated surface.
2. **REACHABLE** — the dated record that withdrew it exists in every tree that cites it.
3. **LEDGERED** — if the claim was ever *pushed*, the public ledger has a numbered entry.
4. **EVIDENCED** — the files justifying the withdrawal are still on disk.

`data/withdrawals.json` is now the single record; `key_numbers.RETRACTED` reads its phrases
instead of keeping a second list, and `scripts/check_withdrawals.py` enforces all four at
stage `release`. Registering a withdrawal in one place now does the lot.

### What building it exposed, and this is the transferable part

Three separate gates carried **a comment describing behaviour the code did not have**:

- `RETRACTED_ALSO_SCAN`'s docstring explained at length why `ADVERSARIAL-REVIEW.md` had been
  added to it. The tuple held one filename and it was not that one. (The file had gone to
  `SURFACES`; the comment never said so.) **I then made the identical mistake the comment
  records** — put two prose files into a JSON-only scanner — and the gate refused me in the
  same words it had used in September. A comment is not a control. It did not stop the author
  of the comment's own successor.
- The retraction walker's `dirs[:]` filter said "skip machinery and history". `withdrawn/` —
  the history — was not in the list, so the archive whose purpose is to hold retired text was
  being scanned for retired text.
- `LESSONS.md` was public, carried a withdrawn claim, and was in no surface list at all.

**So: when a comment states a gate's coverage, check the list.** The comment is what a
reviewer reads instead of the code, which makes a stale one worse than none.

### Two smaller traps, both worth the line

- **A gate must not demand a surface say something it does not say.** Four `arms_*` phrases
  were registered against the rebuilt `TALK.md`, which reaches the same fact through the
  switch table instead. Permanently-red gates get switched off — `check_arm_match.py` sat in
  the registry with no arguments, exited 2 on its own usage message, and the preflight counted
  that as NOT APPLICABLE. Verify the phrase is gated on some *other* surface before removing
  it, then remove it.
- **Quoting a withdrawn claim trips the scanner, and should.** The corrections ledger has to
  state what it withdraws; the fix is to quote it (`"stance does not move"`), which the
  scanner honours, not to weaken the scan. Same for a superseded `RESULTS` page: it needs the
  literal `SUPERSEDED` token the matcher looks for, not a heading that means it.

Related: [[86]] a generator that cannot find its input publishes the absence as a fact;
[[88]] `withdrawn/` is a panel decision, not a licence to delete; [[91]] published means pushed.

## 93. An audit that greps for ONE SPELLING of a hazard measures that spelling, not the hazard

`runs_root()` returns one corpus root and prefers the older one when both are populated. J1
retired it: `grep -rn "runs_root" scripts/ tests/` returned 71 hits, six of which were live
calls, and every one was fixed. Both suites green, 109 of 109 gated numbers unmoved, the whole
thing proven a no-op. It read like a finished audit.

Then the corpus actually moved, and `out_of_panel_records` went from **5,647 to 2,437**.

`key_numbers.py` held **eight** `os.path.join(STUDY, "runs", name)` joins. They are the same
hazard — a corpus root chosen at the call site instead of resolved — and not one of them
contains the string `runs_root`, so the audit could not see them. The grep defined the
problem as its own pattern.

Worse than the miss: the failure was silent in the direction that looks like data. Each
missing run is skipped with a bare `continue` and the function ends `return total or None`, so
losing a third of the denominator is indistinguishable from having a third less data. That
figure heads the STATE block's disclosure of what the refusal panel sets aside — the ratio a
reader is entitled to before quoting any rate off that table.

**So: state the hazard, then find every spelling of it.** "A corpus root chosen rather than
resolved" is the hazard; `runs_root()`, `join(STUDY, "runs", …)`, `STUDY_DIR / "runs"` and
`BASE / "runs"` are four spellings, and the codebase had all four. The test that pins this
asserts on the SOURCE — `key_numbers.py` must contain zero hardcoded joins — because the
property wanted is "this file does not spell a corpus root", not "this number is currently
right".

Related: [[82]] a hand copy of a generated table; [[94]] a write path that spells a root forks
silently.

## 94. A read that picks the wrong root computes nothing; a WRITE that picks it forks the data

The two are not the same severity and I nearly treated them as one.

A reader that resolves to the wrong corpus root finds nothing, and something downstream
usually says so — an empty table, a `NOT APPLICABLE`, a floor that will not compute. It can be
re-run once the resolver is fixed, and nothing on disk is different afterwards.

A writer that resolves to the wrong root **creates the directory and writes into it.** Three
were found in one audit:

- `run_study.py` and `run_local.py` placed a NEW run with `run_path()`, whose fallback for an
  unresolvable name is `runs_root() / name`. A run being collected can never be resolved, so
  the fallback is *always* the path taken — a fresh collection would land in the retired
  corpus with a correct manifest and no message.
- `recollect_at_cap.py` wrote `OUT_DIR` to `runs/2026-09-05-recollect` after that run had
  moved. It would have made a second, empty `2026-09-05-recollect/` and appended half a
  recollection there. The same file's `_main_study_dir()` already searched both roots — one
  file, half-correct, and the half that was wrong was the writing half.
- `drift_timeseries` and `cross_method_report` wrote `_aggregated/` to `runs_root()`, which
  would have left two sets of cross-run outputs on disk with nothing to say which was current.

**So: audit write paths first and separately.** `new_run_path()` resolves an existing run
wherever it is — so a resume cannot fork it — and otherwise places a new one in the current
corpus. `aggregate_dir()` resolves by where the directory already is and *refuses* a split it
cannot resolve, because a write path is the one place where guessing produces two answers
instead of none.

## 95. The day a directory becomes a corpus root, every enumerator counts what is in it

`data/` held the study's configuration and `data/external/` — Röttger et al.'s published
codes, 24,180 third-party records kept for the controls audit. Harmless for months, because
nothing enumerated `data/` as a source of runs.

Then 46 run directories moved into it, and within one command:

- `run_inventory` listed `external` as a run **of ours**, `corpus: previous`, ten models,
  24,180 records;
- `derive_manifest --check` failed demanding a freeze manifest for it;
- `validate_runs` reported it as a run with no manifest discipline.

The accounting this whole work exists to make honest had just absorbed somebody else's data,
in a project whose paper is about other people's unchecked measurement claims.

The filter is NAMED (`studypaths.NOT_RUNS`), not inferred from shape. "A run directory is
dated" would have been the tempting rule and it is false here — `refusal-ablation` and
`mask-gradient` are runs and neither is dated — so a shape rule would have silently dropped
7,876 records of our own to exclude one directory that was not ours.

**So: when a directory changes role, enumerate what is already in it before the change, not
after.** The question is not "what am I adding" but "what does this directory now claim to
contain".

## 96. A try-this-then-that scanner is armed by the change that makes the first branch non-empty

`gen_data_dictionary.render()` globbed `data/*/raw/*.jsonl` and fell back to
`runs/*/raw/*.jsonl` only when the first yielded nothing. Correct-looking, and it had worked
for as long as exactly one of the two roots held records.

The fallback's failure mode is not an error. It is that the second branch stops running, and
whatever lives there is dropped from the record counts, the file counts, the field coverage
and the categorical vocabularies, with no message — in a document whose entire subject is
coverage, and whose own preamble says a field on 93.6% of records is one an analysis must
check for rather than assume.

**And it was already wrong before anything moved.** The committed dictionary said 193 raw
files and 275 scored; the pre-move tree held **195 and 277**. Two files in each layout, never
noticed, because `--check` was not in anybody's habit and the number looked plausible.

**So: scan every source, always. A pattern that matches nothing contributes nothing, which
needs no branch.** `scan()` takes `*patterns` now. The branch was never buying anything except
the appearance of robustness.

Related: [[86]] a generator that cannot find its input publishes the absence as a fact.

## 97. A figure registered in one tree has never been green in the other until somebody ran it there

R4 registered five load-bearing figures that were previously ungated, `out_of_panel_records`
among them. It was verified in the private study, where it computes 5,647 and matches the
paper. Done, ticked.

In the public mirror — the tree that ships — the same key computed **2,437** and
`key_numbers --check` exited 1 from the moment it was registered. Nobody had run it there.
Fixing the hardcoded root then moved it to 5,637, which is the mirror's *true* value and still
not the paper's: `2026-09-13-truncation-proof`, ten records, is not in the release. So the
paper's disclosure is not reproducible from the published corpus, by 0.18%.

Three distinct states hid behind one green tick: red-in-the-mirror-for-a-code-reason,
red-in-the-mirror-for-a-corpus-reason, and green. Only the first was a bug in the gate.

**So: a gate is registered when it has been RUN, exit code read, in every tree it claims to
cover.** `--check` in one tree is a claim about one tree. And when the two trees legitimately
disagree, that is a finding for the author, not a tolerance to widen: loosening the gate would
have buried the fact that the release cannot reproduce a number the paper prints.

Related: [[83]] "all load-bearing numbers match" is a statement about the registry;
[[91]] published means pushed.

## 98. Prose written beside a generated table is wrong on the day you write it

While writing `runs/README.md` I wrote: *"Three directories here report `previous` and are
correct to be here."* The generated inventory table two lines above it listed **five**.

I had counted from the two I was explaining (`refusal-ablation`, `mask-gradient`) plus one I
misremembered, in a file whose entire design is that numbers are generated because typed ones
rot. The table and the sentence contradicted each other on screen at the same moment.

The generated half cannot save the hand-written half. A caveat cannot be generated — that is
why the prose exists — but a caveat that *counts* something has quietly become a number.

**So: when prose beside a generated table states a count, derive it and check, or write the
sentence so it does not carry one.** The fixed version names the five and says why each is
there, which is both more useful and unfalsifiable-by-drift in the same way the table is.

Related: [[82]] a hand copy of a generated table is the defect the generator was built to
remove.
