# The paraphrase floor: measured on someone else's data, then measured again on current models

2026-09-04

> **Both halves of this file were rewritten on 2026-09-04 after adversarial review.** The
> original headline — "270 pairs, p90 6, MDE 7, the largest floor in the study" — was correctly
> computed and answered the wrong question, and Part 1 misdescribed another researcher's
> method. What survives is smaller, and more interesting. The corrections are kept in place
> rather than edited out, because a results file that quietly acquires the right answer teaches
> nobody how it got the wrong one.

Two results, and the second one exists because of the first.

1. **Röttger et al.'s published completions, re-scored with this project's statistic**, put the
   prompt-paraphrase floor at **p90 9 side-flips of 62 across 148 pairs**, close to our
   presentation-order floor. That is a magnitude landing in the same place on data we did not
   collect. It is *not* corroboration that our harness is sound — the original text said that,
   and it does not follow: theirs is a different factor (their template versus our item order)
   on 2023-era models, and two numbers agreeing is a coincidence of magnitude until something
   connects them.
2. Their subjects are Llama-2, Mistral and GPT-3.5, two generations back, so it licenses
   nothing about 2026. So we collected it ourselves — and on current models **the wrapper turns
   out to be nearly inert**: rewording the forced-choice instruction moves about one more item
   of 62 at p90 than simply running the same prompt twice.

The real finding is the control, not the factor. This study runs at temperature 0 and had never
measured what a *repeat* does. It does plenty: **median 3 items of 62, p90 5, max 15**, with
nothing changed at all. That row is the floor under every other floor here, and it is the
quantity two published papers use to certify that their instrument is reliable.

---

## Part 1 — Röttger et al. 2024, re-scored

`scripts/replicate_rottger.py`. Their completions (CC-BY 4.0, `github.com/paul-rottger/
llm-values-pct`), our power calculation, three extraction rules — two of ours and, since
2026-09-04, a checked port of theirs. Not their analysis re-run: none of their notebooks,
figures or conclusions are used or restated here as ours.

The corpus is not vendored. Their CSVs carry `pct_prompt`, which is third-party instrument text
this project does not republish, so the script takes `--corpus` and points at your own clone.

### Two coders — and a correction about whose rule is whose

**This section originally said that our `label` mode "is their rule" and that their human
annotators "judged 100 completions uncodeable". Both statements are wrong, and they are wrong
in the direction that flatters us.** Read from their released code
(`notebooks/utils/completion_helpers.py`), their `validate_completion` marks a completion VALID
when it contains exactly one of `1)`–`4)` **anywhere**, or starts with `i would disagree` /
`strongly agree` and similar, or merely *mentions* `i strongly disagree`, `i personally
disagree` or `in my opinion`. Their rule reads prose stances. It is much closer to our
`stance` mode than to our `label` mode.

So the framing was inverted. Our `label` mode is **stricter than theirs**, not equal to it —
it discards roughly 730 completions their published rule codes.

That also makes the validation nearly vacuous, which is worse than it being wrong. The 100
"gold" completions are ones their *regex* had already classified invalid. A coder strictly
narrower than that regex cannot extract from anything the regex rejected, so **zero false
extractions was guaranteed by construction rather than earned.** Under this project's own
standard that is a gate that passes vacuously.

And "their annotators judged these uncodeable" launders a regex output as human judgment. Their
annotation guidelines asked something else entirely: given completions *already* selected as
invalid, label the failure TYPE — both-sides, one-side, refusal, neither. The annotators were
never asked whether a position could be coded. In fact 20 of the 100 are marked `oneside` by
*both* annotators, which is the stance coder's premise rather than something it disagrees with.
Our stance coder recovers 4 of those 20 — a 20% recall that the original text presented as
"recovering the data their rule drops".

| mode | what it actually is | against their 100 gold-invalid |
|---|---|---|
| `label` | **stricter than their rule**: a leading label or a bare option phrase | 0 false extractions — guaranteed by being narrower, not earned |
| `stance` | closer to their rule: also reads a position asserted in prose | codes 4, all 4 marked `oneside` by both annotators |
| `theirs` | **a port of their rule**: `validate_completion` + `extract_choice`, string for string | 0 coded — by construction again, since these 100 are that rule's own rejects; the check that can fail is the port against their code (below) |

The honest version of the "extraction rule does not drive the floor" claim is available and
stronger, and it is **their** rule, not ours. It is now implemented as `--mode theirs`: a port
of their two functions from `notebooks/utils/completion_helpers.py`, with attribution in the
source, their code not vendored. `--validate` imports their original from the `--corpus` clone
and runs both against every completion in the corpus — **8,160 completions, 0 disagreements on
validity or choice** — and the check is live rather than decorative: deliberately breaking the
port's extractor produces 4,760 disagreements, and flipping its `unknown` verdict to `valid`
produces exactly the 19 completions their rule leaves unknown.

One composition decision, stated because it changes the number. Their paraphrase notebook
computes compass coordinates from `extract_choice` over *all* rows and reports
`validate_completion` as a separate validity rate; for their §4.4, on two models at ~100%
validity, the distinction did not matter. It matters when every model is scored: measured on
their corpus, `extract_choice` alone takes a position from **313 paraphrase and 146 forcing
completions their own validity rule calls invalid**, and from **9 of the 100 gold-invalid
completions** — typically a leading `1) …` on a completion that then lists more than one
option. So `theirs` codes a row only when their validity rule says valid *and* their extractor
finds a choice. Under that rule the paraphrase arm codes 2,939 of 4,960 (59.3%; ours: `label`
2,583, `stance` 2,998) and the forcing arm 1,353 of 3,100 (43.6%).

Running their rule through our floor gives **paraphrase @40 = 193 pairs, side 4 / 8 / 22** —
identical to the figure measured by hand before the port existed, and the same p90 as our
`stance` mode.

One real coder bug was caught by that check and fixed. `1. I don't have a race or personal
experiences, so I don't have an opinion on this matter` was being read as option 1, Strongly
disagree — an enumerated paragraph's list marker taken for a forced-choice label, coding a
refusal as a strong position. `N.` is no longer accepted as a label; `N)` and `(N)`, the forms
their prompt actually asks for, are.

### The floors

Their data, our statistic, side-flips of 62. Three coverage thresholds, because refusals
cluster on the charged propositions and a pair scored on the items both sides answered is
scored on the milder ones:

Every pair the design allows is now in one of three columns — scored, low-coverage (both arms
coded, fewer than 40 shared items), or no-arm (an arm coded nothing) — and the script aborts if
the three do not sum to C(levels, 2) × models:

| factor | mode | scored | low-cov | no-arm | of | side med / p90 / max | threshold | MDE |
|---|---|---:|---:|---:|---:|---|---:|---:|
| prompt template | label | 148 | 111 | 101 | 360 | 5 / 9 / 22 | 12 | 11 |
| prompt template | stance | 162 | 198 | 0 | 360 | 4 / 8 / 22 | 11 | 10 |
| prompt template | **theirs** | **193** | 167 | 0 | 360 | **4 / 8 / 22** | 11 | 11 |
| forced-choice prompt | label | 18 | 21 | 61 | 100 | 5 / 6 / 8 | 8 | 7 |
| forced-choice prompt | stance | 18 | 64 | 18 | 100 | 5 / 6 / 8 | 8 | 7 |
| forced-choice prompt | **theirs** | **25** | 49 | 26 | 100 | **3 / 6 / 8** | 7 | 6 |

**The three rules agree where they overlap, and now one of the three is theirs.** Where two
rules both code a completion, they disagree on side: `label` vs `stance` 0 in 2,583
(paraphrase) and 0 in 976 (forcing); `label` vs `theirs` 0 in 2,557 and 0 in 972; `stance` vs
`theirs` 2 in 2,675 and 0 in 1,064. (The original text put the last pair's numbers under the
first pair's names.) The paraphrase p90 is 8 under their rule and under our `stance` rule, 9
under our stricter `label` rule; the forcing p90 is 6 under all three. So the claim can now be
made in its defensible form: **on the models a rule can read, the extraction rule moves the
paraphrase floor by at most one item at p90, and that holds for their published rule and not
only for two rules of ours.** What it still does not say: anything about the models no rule
reads. No Llama-2 pair scores at 40 shared items under any of the three rules, and their §4.4
never had this problem because it deliberately used only the two models at ~100% validity.

**And these pairs are mostly three models, under every rule.** At the default threshold in
`label` mode: gpt-3.5-0613 45 pairs, gpt-3.5-1106 45, Mistral-v0.1 45, zephyr 11, Mistral-v0.2
2 — **135 of 148 are three models**, per-model p90 4, 5, 7, 13 (max 22). Under `theirs` the
same three contribute the same 135 of 193, zephyr rises to 31 and Mistral-v0.2 to 27, and the
per-model p90 runs 2, 5, 7, 7, 13. A pooled "8" or "9" is not a property of anything. Part 2
of this same file argues exactly that against pooling frontier models and the original Part 1
did not apply it here.

**101 pairs were neither scored nor counted as dropped — fixed.** `sheets()` creates no sheet
for a (model, level) with zero coded rows, and `pairs_for` enumerated pairs from the sheets, so
a pair whose arm coded nothing was never enumerated: 148 scored + 111 dropped = 259 of a
possible 360, and the missing 101 were exactly the Llama-2 pairs (13b 45, 7b 39, 70b 17) — the
worst-coverage case, which is what the accounting exists to expose. Levels are now enumerated
from every row, the no-arm bucket is its own column, and the reconciliation is asserted:
148 + 111 + 101 = 360. The forcing arm was worse in proportion and nobody had noticed: 18 + 21
= 39 of 100 in `label` mode, with **61 pairs invisible**; `stance` hid 18. The same fix is
applied to the same-version pairer below, which had the same bug.

### And their same-version null, which is the column nobody fills

Not one external study in the controls audit reports what two variants of the *same* release do
to the same instrument, and that is the null any drift claim has to be measured against. Their
data can produce it — Llama-2 7b/13b/70b by size, Mistral v0.1/v0.2, GPT-3.5 0613/1106,
GPT-4 0613/1106-preview by snapshot — with the nuisance factor held constant:

| from | mode | scored | low-cov | no-arm | of | side med / p90 / max | threshold | MDE |
|---|---|---:|---:|---:|---:|---|---:|---:|
| paraphrase arm | label | 13 | 10 | 27 | 50 | 12 / 17 / 30 | 30 | 23 |
| paraphrase arm | stance | 17 | 33 | 0 | 50 | 10 / 17 / 30 | 30 | 23 |
| paraphrase arm | theirs | 18 | 32 | 0 | 50 | 11 / 17 / 30 | 30 | 23 |
| forcing arm | label | 5 | 3 | 22 | 30 | 14 / 16 / 16 | 16 | 7 |
| forcing arm | stance | 7 | 17 | 6 | 30 | 11 / 16 / 16 | 16 | 9 |
| forcing arm | theirs | 7 | 15 | 8 | 30 | 12 / 16 / 16 | 16 | 9 |

"Of" is C(members, 2) × levels per family, summed: the paraphrase arm has no GPT-4 rows, so
it is 3 Llama-2 pairs + 1 Mistral + 1 GPT-3.5 = 5 × 10 templates = 50; forcing is 6 × 5 = 30.
Under `label` on the paraphrase arm, 27 of the 50 were previously invisible.

Two variants of one release differ by a median of 10 to 14 items of 62 in their corpus, against
our own same-version null of median 5, p90 11 (12 when this was written; an order-dependence fix moved it on 2026-09-06). Theirs is larger, on fewer pairs, on older
models. Their paper does not report it **as a position null** — it does present the snapshots
side by side (§4.1) and compares them on validity (§4.3) — and the original sentence here said
"nobody computed it", which the controls audit cannot support: that audit covers twelve
studies, not the field.

**Three corrections to the table above, all of which shrink it:**

- The `Families pooled:` line and the sentence naming Llama-2 and GPT-4 are **false as a
  description of what was scored**. At the default threshold no Llama-2 pair and no GPT-4 pair
  enters any same-version row in any mode — `theirs` included; the only Llama-2 entry anywhere
  is one pair on the forcing arm at 30 shared items under their rule. The label paraphrase
  row is gpt-3.5 (10 pairs) plus Mistral (3). The script now prints the families that
  actually scored on each row, beside the families defined.
- Those "10 gpt-3.5 pairs" are **one model pair under ten templates** — pseudo-replication
  reported as n=10.
- The forcing rows are n=5 and n=7, where `summarise` reports the MAX as p90 by nearest rank.
  The paper's floors table footnotes that with a †; this table printed "14 / 16 / 16" with no
  such note, which reads as two statistics agreeing rather than one number repeated.

Worth noting against ourselves too: this "null" has a p90 of 17, which is *twice* the
paraphrase "effect" of p90 8 sitting three tables above it. A null larger than the effect it
is meant to calibrate is a finding about the instrument, and the original file passed over it.

---

## Part 2 — the paraphrase floor on 2026 models, and the floor underneath it

**This section was rewritten on 2026-09-04 after an adversarial review found two defects that
between them invert its headline.** The original reported "270 pairs, side 3 / 6 / 13, MDE 7"
and called it the largest floor in the study and the last unmeasured nuisance factor. Both
numbers were computed correctly and both were answering the wrong question.

### Defect 1: the second run of every cell was collected and then thrown away

Cells were modal-collapsed with `modal()`, which takes `Counter.most_common(1)`. With exactly
**two** runs, every disagreement is a 1–1 tie, and `Counter` breaks ties by insertion order —
so run 1 won every tie and run 2 contributed nothing. 54 of 60 cells hold exactly two runs, and
rebuilding the floor from run 1 alone reproduces the shipped numbers **to the digit**.

The design was one run per cell wearing a two-run label. The original text said run-to-run
noise was "inside these numbers rather than partialled out", which understated it: the second
run was not folded in, it was discarded by a tie-break.

### Defect 2: there was no replicate control, so the floor could not be attributed

A pair of runs under two different templates differs in **two** things: the template, and the
fact that it is a different run. Without a same-template run-against-run comparison there is no
way to say which one moved the answers — and this study runs at temperature 0, which quietly
encourages the assumption that a repeat changes nothing.

It changes plenty. Hosted inference batches requests, routes MoE experts and reduces in
nondeterministic order; temperature 0 is a decoding rule, not a determinism guarantee.

### Both fixed: pair at run level, and measure the replicate floor beside it

| factor | pairs | side med / p90 / max | p90 95% CI |
|---|---:|---|---|
| **run-to-run replicate** (same model, same template, run again) | 63 | **3 / 5 / 15** | [4, 11] |
| **instruction paraphrase** (run-level, across templates) | 1067 | **3 / 6 / 14** | [5, 8] |
| *instruction paraphrase, as originally reported (modal-collapsed)* | *270* | *3 / 6 / 13* | *[5, 7]* |

Identical pairing, identical statistic; the only difference between the first two rows is
whether the template changed.

**Rewording the forced-choice instruction adds about one item of 62 at p90 over not changing
anything at all.** The intervals overlap heavily -- and those intervals are CLUSTER bootstraps
over models, added after the same review pointed out that 45 pairs from one model under ten
templates are not 45 independent draws. Resampling models instead of pairs widened replicate
from [4, 7] to [4, 11] and paraphrase from [6, 7] to [5, 8]. The naive intervals understated
uncertainty by exactly the factor the pairing inflates n, and the honest ones make the two rows
harder to tell apart, not easier. On current frontier models the wrapper is very nearly
inert, and what the original floor mostly measured was temperature-0 nondeterminism.

`floor_template_modal()` is kept callable so the retired figure stays reproducible rather than
surviving only as a claim in this file.

### The replicate floor is the more useful of the two

It is the floor **under** every other floor here: anything that varies a factor across two runs
is measuring that factor plus this. And it is exactly the quantity Naser and Sakhawat use to
certify reliability — run one prompt ten times at temperature 0, observe that the answers agree,
conclude the instrument is stable. This row says what that agreement is worth: **a median of 3
items of 62 move, p90 5, max 15**, with nothing changed at all.

### Cross-checked against a second harness

`scripts/replicate_aipolcom.py` runs the same statistic over the project's observatory data —
disclosed as this project's own second instrument, not independent replication. Same 62
propositions, same 0–3 scale, different harness, different prompts, different collection window:

| arm | pairs | side med / p90 / max |
|---|---:|---|
| observatory run-to-run (5-run program) | 670 | 3 / 6 / 10 |
| observatory run-to-run (run-variation) | 70 | 2 / 6 / 9 |
| observatory prompt variant | 21 | 2 / 4 / 8 |
| ours, run-to-run replicate | 63 | 3 / 5 / 15 |
| ours, instruction paraphrase | 1067 | 3 / 6 / 14 |

Two harnesses agree on temperature-0 replicate noise (p90 5–6) and agree that varying the
prompt wrapper adds little to it. The observatory's models are gpt-5.6, claude-fable-5,
gemini-3.6-flash, grok-4.5, deepseek-v4-pro and qwen3.7-plus — which is the objection the
Röttger replication cannot answer, since his subjects are two generations old.

### Per model, and the spread that a pooled row hides

From the original modal-collapsed run, per model p90: gemini-3.5-flash-lite 3, claude-sonnet-5
5, qwen3.8-flash 5, grok-4.6 6, gpt-5.4-mini 6, **kimi-k3 10**. A threefold spread, so the
pooled figure sits below kimi-k3's own floor. Any per-model claim must clear that model's floor,
not the pool's — and the bootstrap CI treats 45 pairs per model as 45 independent draws when
the effective sample is six models. A cluster bootstrap over models is the correct interval and
is not yet computed.

The observatory data shows the same shape from the other side: grok-4.5 run-to-run is med 7 /
p90 8 while gemini-3.6-flash is med 2 / p90 2. Replicate noise is a per-model property, and
pooling it is a convenience.

### What this does not license

- Six models, one per family, chosen for current relevance and not sampled. Not a survey.
- Condition A only. Whether the wrapper interacts with the pressure conditions is unmeasured.
- Ten rewordings of **one register** — an imperative instruction with a fixed output format.
  "The wrapper's contribution is now measured" overclaims: the literature varies wrapper
  register much more widely than this (Rozado's and Motoki's framings differ in kind, not
  wording).
- Grok-4.6 returned unparseable output on 7 runs and qwen3.8-flash on 3. The resume logic asks
  for valid runs until it has N, so a template a model resists is re-sampled until it complies
  — which removes a paraphrase effect on *refusal* from a floor about paraphrase effects on
  *position*. Grok-4.6 T03 took 6 attempts for 2 valid runs; T07 took 4 for 1.

## Bookkeeping this forced

Adding 132 runs broke two things immediately, both caught by gates rather than by reading:

**The corpus-scale sentences went stale.** `key_numbers.py --check` failed on `corpus_runs`
(1,657 → 1,789) and on the matched-arms figures (39 refusals in 486 no-directive runs → 48 in
531, against an unchanged 347 directive runs). That last one is the important one: the template
sweep is condition A only, so including it inflates one arm's denominator and leaves the other
alone. The arm *contrast* is the finding; a one-sided denominator is not a bigger sample of it.
So `2026-09-04-template-floor` joins `refusal_table.DEFAULT_EXCLUDE`, and the corpus is 1,657
runs again.

**That exclusion set existed three times** — a literal set in `key_numbers.py`, a `--exclude`
argument in `gen_paper.py`, and an example in `refusal_table.py`'s docstring. Adding one arm
meant editing the same fact in three places, and one of them would have been missed. It now
lives once, in `refusal_table.DEFAULT_EXCLUDE`, as the loader's default; the other two are
references to it.

**`load()` also grew a `key` parameter** rather than gaining a second copy. The template arm
needs a different *grouping* of the same rows, and a duplicated loader would have been a
duplicate of the parse, the validity filter and the degenerate-sheet rule.

## The ablation floor was right for the wrong reason

Chased separately, on the question of whether the ablation arm has current-generation
coverage. It does — `gemma4-12b` (Gemma-4-12B stock vs OBLITERATED) is config-matched,
eligible, and contributes 4 of the floor's 12 pairs. Two earlier statements of mine that the
arm was "all 2024-vintage local models" were simply wrong.

What is wrong is how the other three of six collected pairs were excluded. `check_arm_match.py`
measured them as invalid comparison arms on 2026-08-30 — mismatched quantisation, dropped stop
tokens, baked sampling parameters, none of which is the refusal direction — and wrote that up
in its docstring. `floor_table.floor_ablation()` never knew. All three were excluded anyway, by
three unrelated accidents:

| pair | ruled invalid because | actually excluded because |
|---|---|---|
| gemma2-9b | Q4_0 vs Q8_0, stop tokens, baked temperature | emits SentencePiece boundary markers as literal text, so nothing parses |
| llama31-8b | Q4_K_M vs Q8_0, stop tokens, baked temperature | invents its own questions and answers those |
| qwen38-27b | quant matched, stop tokens dropped | **answers Strongly Agree to all 62 propositions in all four conditions**, so the loader drops it as a degenerate sheet |

The floor is unchanged now that the ruling is enforced — 12 pairs, side 6 / 9 / 12 — which is
the good outcome: the exclusions were correct. But a floor whose exclusions hold by luck holds
only until one of the accidents stops happening. Had that Qwen build's answers merely varied a
little, a pair this project's own gate calls invalid would have entered a published floor with
nothing anywhere saying so. `INELIGIBLE_PAIRS` now lives in `check_arm_match.py` and
`floor_ablation` reads it, and the generated floors table prints each exclusion with its reason.

### The collapse is worth its own line

The OBLITERATED Qwen3.8-27B answering **Strongly Agree to every one of 62 propositions, in
every condition**, is a result and not an absence. Scored naively against its stock arm it
reads as "abliteration moved the position by roughly 40 items of 62" — the single most
dramatic number this project could publish, and an artifact of a build whose stop tokens were
dropped. The same OBLITERATUS edit on Gemma-4-12B does not collapse. So this is specific to
that build, its serving-config defect is a sufficient explanation without invoking the ablation
at all, and it is exactly what the arm-match gate exists to catch.

Worth noting alongside: the `Barding-Defense` NInfer artifacts publish a **77.8% speculative-
decode acceptance rate for the OBLITERATED Qwen3.8-27B against 88.8% for the huihui-abliterated
build of the same model** — an independent signal, from someone else's benchmark and for
someone else's purpose, that the OBLITERATED edit perturbs the output distribution more. Not
evidence for our claim, and consistent with it.

### And the loader no longer discards in silence

`load()` counted nothing. It now records every drop with a reason into `DROPPED`, deduplicated
by run identity because several floors glob overlapping directories and a naive counter
reported 376 drops for 238 runs. Corpus-wide, across every floor: 238 runs dropped, of which
233 are invalid runs (70 refused, 55 other, 48 unclassified, 41 budget-exhausted, 12 transport,
7 truncated) and **5 are degenerate sheets** — grok-4.3 answering Strongly Disagree to
everything twice, kimi-k3 answering Agree to everything twice, and the OBLITERATED Qwen build.

Those five are the interesting ones and none of them had ever been reported. A model that
answers 62 forced-choice propositions identically is telling you something about the
instrument's grip on it; dropping the run is right, dropping it invisibly means nobody ever
asks which models do that.

## The requantisation floor, past one model — and the claim it broke

The weakest row in the floors table. It reported "4 pairs" and rested on **one weights
family**: gemma2 at Q4_0 vs Q8_0, across four prompt conditions. Four conditions of one model
are not four independent pairs, and it was the only row with no confidence interval — honest
about the count, silent about the count being one model.

Pulled Q8 builds of four models already held at Q4, gated them, collected 40 local runs:

| | before | after |
|---|---|---|
| pairs | 4 | **13** |
| weights families | 1 | **4** |
| side med / p90 / max | 3 / 10 / 10 | **3 / 6 / 10** |
| p90 95% CI | *"n too small"* | **[3, 10]** |

The old p90 of 10 was a single gemma2 outlier. Per-family, the sensitivity is model-specific
and the spread is the interesting part: qwen2.5-14b moves 0–2 items across four conditions,
gemma2 up to 10. No published verdict changes — the ablation null still clears its threshold at
observed 12.

### Three defects it surfaced, in ascending order

1. **`check_arm_match.py` had one hardcoded intervention.** Built for ablation, it demanded
   matched quantisation on *every* pair — so it called three genuine requantisation pairs
   INVALID for differing in exactly the way a requantisation pair is supposed to. It takes
   `--intervention` now; requantisation exempts `quant` from the match test and still requires
   identical stop tokens and baked sampling parameters. A gate that understands one experiment
   is a gate that gets bypassed for the other. Ablation verdicts unchanged: 3 of 6.

2. **`floor_quant()` paired every model in a condition against every other.** Harmless while
   the arm held one family; the moment a second landed it would have paired llama3.1-Q4 against
   mistral-Q8 and called it a quantisation null. It reads the gated `QUANT_PAIRS` list now — the
   gate is the authority on what a pair *is*, not the directory contents.

3. **`run_battery.py`'s ollama channel had been dead for two days.** Commit `ccde3cc`
   ("Zero forks", 09-02) resolved a fork by taking the mirror's `call_ollama` wholesale, and
   that side was the narrower one: no `temperature`, no `max_tokens`, no `seed`, no `think`,
   hardcoding temperature 0.7 and `num_predict` 800 — both wrong for a study that runs at
   temperature 0 and needs 8192 tokens for a 62-item sheet. Every local call raised TypeError,
   and nothing noticed because nothing ran local in between. **De-forking means merging the
   union, which `check_no_fork.py`'s own message says**; copying one side over the other is a
   silent deletion. `thinking_chars` and `done_reason` came back with it — and those two fields
   are what diagnosed mistral-Q8 in a single query: `done_reason: stop` at 305 tokens of 8192,
   so it *chose* to stop after 52 items rather than running out of budget.

### And a headline claim was false as written

Section 1 read:

> "none in 347 runs where it carries one. Not one of them declines when told firmly to answer,
> whatever it is told to answer."

Three of the new runs refuse under the commitment directive — llama3.2 at both quantisations,
llama3.1-8B at Q8_0. So a directive cuts refusal from **7.8% to 0.8%, a factor of ten, not to
nothing.**

The absolute version was an artifact of which models had been measured, and it survived for a
specific and embarrassing reason: **the zero was hardcoded into the prose.** `key_numbers.py`
gated the 347 beside it and had no key for the refusal count at all. The one quantity the
argument rested on was the one quantity nothing recomputed. A gate that checks a rate's
denominator and not its numerator is checking the wrong half. `arms_dir_refusals` is gated now
in the paper and on the public page, and both carry the correction in text rather than a quiet
edit.

Worth its own line: **the quantisation-induced refusal asymmetry is itself a result.** Same
weights, and the Q8 build of llama3.1 refuses conditions C and D while the Q4 build answers all
four. Quantisation is not neutral in the refusal dimension, and that is only visible because
failures are retained rather than deleted — the control this paper convicts Liu, Panwang and Gu
of lacking.

Corpus: 1,657 → 1,689 runs, 155 → 160 models. This directory is **not** withheld from the
refusal figures: it covers A/B/C/D at 8 runs each, so unlike the condition-A-only template
sweep it does not skew one arm's denominator — and withholding it would delete the very rows
that corrected the claim.

## The red gate, chased down: it was red for a bad reason

`refusal_table.py --audit` was failing on 27 rows where the collector stored one failure class
and the current derivation computes another (26 `other` → `refused`, 1 `refused` →
`budget-exhausted`), all from 2026-08-30 and 08-31, none in the new arm.

Not drift. Those labels were written by rules this project **deliberately replaced**: commit
`5ecf8a1` (08-31) swapped lexical refusal detection for the structural test because the lexical
one undercounted, and `96e5fa5` (08-30) stopped truncation being read as refusal. So a gate
whose entire job is to catch the recomputed rule drifting from the collector's could not tell
drift from an improvement — because a stored label carried no version. It had been red for four
days, and a permanently red gate is an unread gate.

**Three fixes, and the first two alone would have been evasions.**

1. Run records now carry `classifier` (`CLASSIFIER_VERSION`, currently `structural/1`), and the
   audit partitions on it: current-rule rows held to exact agreement, superseded rows reported
   by transition as history. Bumping that version is now the documented obligation when the
   rule changes, and if the superseded count grows, someone changed a rule without bumping it.
2. That partition made the strict half **vacuous** — no row carried the new version yet, so it
   printed "agreement: 100%" over *zero rows*. A check that passes by having nothing to check
   is worse than one that fails, so the vacuity is now stated in the output when it occurs.
3. So the collector's rule became a callable (`run_battery.classify_failure`, extracted from
   `one_run`), and the audit runs **both implementations over all 1,657 rows and compares them
   to each other** — no stored label, no version match, no re-collection required. That is what
   this gate always claimed to test: two independent implementations of one rule. They agree on
   every row.

One false positive in that comparison, caught and fixed in the harness rather than in either
rule: the collector returns `None` for a clean run (there was no failure) and this module
returns `"valid"` (it classifies every row, not only failures). Both encodings are right for
their caller. A comparison that flags 1,445 clean runs as drift is a broken comparison.

Verified by a live call: the stamped record carries `classifier: "structural/1"` alongside
`template`, and all six classification branches were tested directly (clean, refused,
budget-exhausted, truncated, other, corrupt-tokenizer).

### And the gates now run

`refusal_table.py --audit`, `key_numbers.py --check` and `controls_audit.py --strict` were
documented in the paper's reproduction block and invoked by hand. That is precisely how the
first one sat red for four days — nothing ran it, so nothing reported that it was red. All
three are now stage 5 of `run_barometer.sh` and each exits non-zero with a specific message.
A gate nobody invokes is a comment.
