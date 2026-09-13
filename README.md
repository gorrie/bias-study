# The Hedge Is the Bias

**A multi-vendor, multi-generation audit of institutional-skepticism framing in large language models.**

### Five sentences, if you are only here for one

> **Two models that differ only in snapshot date, size or serving mode — not in version —
> disagree on a median of 5 of 62 propositions.** That sets a detection limit of 11. An effect
> smaller than that is inside the instrument's own noise, whatever its p-value.

> **Presentation order alone moves a 2024-generation open-weight model by up to 24 items of 62.**
> On 2026 frontier models the same floor is p90 6. The floor is a property of the model, not of
> the question.

> **Of twelve published studies audited against thirteen controls, none reports a same-version
> null as a distribution, and eight report no detection limit at all.** Seven of them hold the
> pairs to compute one inside their own published design — see
> [PRIOR-WORK-CORRECTIONS.md](PRIOR-WORK-CORRECTIONS.md).

> **Two abliterations of one model by the same author agree exactly; a third by a different
> author disagrees by precisely the size of the "effect," and shows no effect at all.**
> On two of three usable bases nothing clears the floor; on the third, two ablations move
> position by 8–9 items of 62 and disagree with each other by the same 8–9. So the movement is
> **not separable from which build you downloaded** — unattributable, which is not the same as
> absent. The intensity belonged to the ablator.

> **Five of the audited studies put a language model in the scoring path. Not one reports that
> model's own lean.** In four the scorer shares a vendor family with a subject and only one of
> those four says so; in a fifth the scoring model is never identified at all. We failed this
> control too — our judges spanned 0.2926 points, larger than the smallest of our own five
> published effects and within a hundredth of the next, and we had not computed it either.

*Every number above recomputes: `python scripts/key_numbers.py`,
`python scripts/controls_audit.py --gaps`, `python scripts/ablation_analysis.py`. Read
[CORRECTIONS.md](CORRECTIONS.md) before quoting any of them — this study has withdrawn,
narrowed or corrected **14** claims of its own, and says which, when, and what replaced each.*

> **`v1`, `v2` and `v3` in this repository name the three intervention rungs — prompt edit,
> elicitation pipeline, weight ablation — not releases.** Releases are dated. See
> [VERSIONING.md](VERSIONING.md), and read [CORRECTIONS.md](CORRECTIONS.md) first if a number
> you have seen quoted disagrees with one here.
>
> Analysis plans fixed before their data was collected: [prereg/](prereg/) — six of them,
> published 2026-09-07, and one has its stopping rule enforced in code.
> What is coming next, and what it needs: [ROADMAP.md](ROADMAP.md).
> [TODO.md](TODO.md) is the **historical** May-2026 handoff, kept as a record and superseded.
> *(Neither was linked from here until 2026-09-07, which is how a file titled "TODO / Roadmap"
> and instructing the reader to keep it current went three months and a whole second
> instrument without an update.)*

A reproducible study of how aligned LLMs shift their framing on contested-institution
topics when the "be fair to both sides" instruction is removed — and a test of *where*
that bias lives, by escalating force from the prompt, to an elicitation pipeline, to the
model weights themselves.

Headline thesis: **the hedge is the bias signature.** A model that answers a contested
political question with heavy both-sides hedging is not neutral — it is masking a lean at
the alignment-training layer. The mask comes off in proportion to the force applied to
it, *except where it is bolted in at the weights, where force does nothing.* The study's
spine is that **force-escalation ladder**:

| Rung | Force | Tooling | Result |
|------|-------|---------|--------|
| **1. Prompt** | remove the fairness instruction; A→E unmask gradient | OpenRouter / Ollama | the lean unmasks, dose-responsively |
| **2. Pipeline** | hedge-strip + obfuscation, layered | G0DM0D3 server | **no effect established** — all 8 intervals span zero at n=1 per cell |
| **3. Weights** | ablate the refusal direction | OBLITERATUS (fp16) | text rewrites ~70%, stance does **not** move |

**Rung 2 is the weak rung and this table used to overstate it.** It read "only the layered
stack adds force, to a ceiling" until 2026-09-13. Nothing had computed that: `analysis.py` keys on
conditions A and B, this arm runs `B-STM` / `B-Parseltongue` / `B-Layered`, so every table in its
own ANALYSIS.md is an empty heading. `scripts/pipeline_rung.py` estimates it properly — paired per
question against plain condition B — and **not one of the eight intervals excludes zero.** The
strongest is Grok 4.3's layered stack at +0.60, whose lower bound is exactly zero; Claude Opus
4.7's two single-technique arms measure +0.00. A ceiling was never located at all, which three
points on one axis cannot do at any sample size. Re-collection with five samples per cell and a
same-sitting baseline is pre-registered and queued. Rungs 1 and 3 are unaffected and are where
this study's weight sits.

The result is also robust to the obvious reviewer attack on LLM-as-judge studies. The same
data was re-scored under five materially different judging procedures, including one with
the **refusal direction surgically removed from the judge's weights** (abliterated
Gemma-2-9B-IT). Median per-model contamination delta against the cross-vendor baseline is
**0.062** across 47 model-runs — inside the pre-registered 0.10 robust band. The two large
effects hold under every judge individually; the smallest is reported as suggestive with its
range ([CORRECTIONS.md](CORRECTIONS.md) §5). Full multi-method analysis in
§5.8 of the writeup; the abliterated judge that leg relies on is characterized on its own
terms — the abliteration dose-response (and its coherence cliff), and two findings still under
remediation after adversarial review (a refusal/flinch decoupling and a single-template
"documented-exposure" flinch observation) — in
[`results/THE-WASH-2026-06-10.md`](results/THE-WASH-2026-06-10.md) (see its §F review status).

## A standing instrument, not a snapshot

This repository is meant to be **re-run, not just read** — a *bias measurement observatory*.
The protocol is built to re-run on a roughly quarterly cadence so the public record tracks how
model framing **drifts** as new versions ship. The Anthropic Opus arc (+0.27 → +0.90 from 4.0 to
4.7, inside a single year) is the case in point: a one-time snapshot catches the level; only the
cadence catches the slope.

**Contributions and challenges are the whole point.** If you find a number you can't
reproduce, a model whose lean changed since the run shipped, a topic the study should be
testing, a methodological objection it doesn't already address — open an issue:
[github.com/gorrie/bias-study/issues](https://github.com/gorrie/bias-study/issues). The
adversarial-review file ([`ADVERSARIAL-REVIEW.md`](ADVERSARIAL-REVIEW.md)) is structured
exactly so a new objection can land as a tracked item and either get FIXED with a re-run
or get rebutted in writing. The cross-method agreement matrix is the reproducibility check:
a re-runner who gets different numbers can compare against the committed JSON and surface
exactly where the divergence sits. See [`CONTRIBUTING.md`](CONTRIBUTING.md) and the
[issue templates](.github/ISSUE_TEMPLATE/). The `agents/` + `skills/` directories hold the
orchestration for running the full ladder as a repeatable instrument.

## Scope

This measures one axis — **institutional skepticism**: on a topic where an institution's
framing is contested, does the model side with the institution (low) or with the
questioner of it (high), and how does that shift when a fairness instruction is removed?
That is a narrower, more defensible construct than "political lean" in general; the
question set is drawn from a civil-liberties / institutional-power surface and is not a
full left–right battery. Read every finding as a claim about institutional-skepticism
framing, not global political ideology.

The corpus: 36+ frontier models from 13 vendor families, scored 1–5 by a four-judge
cross-vendor median-consensus panel ("ULTRAPLINIAN"). Every per-model delta is reported
with a bootstrap 95% CI; **a delta is a finding only if its CI excludes zero.**

## Update, 2026-08-31 — re-measured on a forced-choice instrument

> **The instrument's own limits, stated rather than discovered.** This arm runs on the
> politicalcompass.org 62-proposition test, and that choice bought the property the whole
> re-measurement exists for: **no language model anywhere in the scoring path.** It is why this
> study scores `yes` on `judge_free_scoring` where five of the twelve audited studies score `no`
> or `partial`.
>
> It cost four things, and they are named here because a reader would otherwise find them.
> **One:** its horizontal axis is the one the companion series argues is a mask — see
> [The Three Axes They Kept Off the Chart](https://evilrobots.lol/research/three-axis-model/),
> which holds that the left/right line is a 1789 seating chart frozen into "the whole range" and
> that it hides the division actually predicting capture. Measuring position along an axis while
> publishing that the axis is captured is a contradiction, and it is ours. **Two:** it has no
> axis for grounding or for reversibility, the second being the dimension this series measures
> and that no existing instrument isolates. **Three:** it is self-report, in a framework whose
> own rule is that these things are read off behaviour. **Four:** its scoring algorithm is not
> disclosed — judge-free, but not transparent, which is why it could not serve as the external
> anchor when `judge_anchor.py` needed one.
>
> Only the compass **vertical** survives that critique, and the three-axis page says so itself:
> Axis 2 is "Eysenck's T-axis; the Political Compass vertical."
>
> **The arm is not being retired, and the reason is not sunk cost.** The compass was authored by
> somebody else years before this study existed, which is the entire defence against the charge
> that we built a ruler shaped to give us our answer. A replacement authored here would hand that
> objection over for free. So it stays as the comparability spine, and the second instrument is
> added beside it: `prereg/PREREG-2026-09-12-instrument-choice.md` fixes the design, the primary
> outcome and the boring outcome before the item set exists.
>
> That plan also measures something nobody in the twelve-study audit measures, us included.
> Every floor in this table is a nuisance factor *inside* one instrument — reorder its items,
> paraphrase its instruction, run it twice. **The choice of instrument is the largest nuisance
> factor in this field and it has no floor at all.** Until it has one, every result here is
> bounded by an instrument nobody has varied, and this paragraph is that caveat.

> **Provenance, and what you can check.** As of 2026-09-02 the forced-choice tooling and its
> run data ARE in this repository, and the floors and detection limits below recompute from
> what is checked in here. What is **not** here, and never will be, is the instrument itself:
> the 62 propositions are politicalcompass.org's licensed text, not the author's work.
>
> That is why every run record is keyed by item id — `{"q": 17, "position": 2}` — and carries
> `forcing_prompt_sha256` instead of the prompt. Run `scripts/fetch_items.py` to retrieve the
> items at your end. See **Replicating the barometer** below.
>
> **Be precise about what that proves, because this paragraph was not.** The propositions
> originate with politicalcompass.org; `fetch_items.py` retrieves them from aipolcom.net,
> which is the source every run record names. Two hashes come back. The **normalized** hash —
> the item set after folding curly quotes, dashes and entities to ASCII — reproduces exactly,
> `c49d38f9…`, so you can establish you hold the same 62 propositions. The **canonical**
> byte-exact hash does **not**: that source now serves different typography than the
> collection used, so `--verify-run` cannot rebuild prompts byte-for-byte and will tell you
> so rather than pass. Until 2026-09-12 this paragraph said `--verify-run` would "prove you
> hold the same instrument we did", which promised the stronger check and delivered the
> weaker one. You can confirm the item set. You cannot, from that source today, confirm the
> bytes.
>
> Two honest caveats. `PAPER-below-the-floor.md`, the academic writeup, is not here — that is
> an authorial decision, and none of the floors depend on it. And 38 run records had their
> `response_text` withheld because the MODEL echoed propositions back; their answers are
> intact, so no number changes. Root `MANIFEST.json` describes the export, and
> `python scripts/key_numbers.py` recounts the redactions from the shipped files. That
> sentence said 19 and cited `runs/COMPASS-EXPORT-MANIFEST.json`, a file this repository does
> not contain, until 2026-09-12; the count is generated now.

### Replicating the barometer

Four commands, in order. Nothing here needs an API key except the collection step.

```bash
python scripts/fetch_items.py                       # retrieve the 62 items at your end
python scripts/fetch_items.py --verify-run runs/2026-08-31-order-control/*.jsonl
python scripts/test_compass_parser.py               # 13 parser fixtures; gate before collecting
python scripts/floor_table.py                       # the floors, from the shipped runs
python scripts/power.py                             # detection limits per null
```

`floor_table.py` should print `presentation order` at **84 pairs** and `same-version variants`
at **97**; `power.py` should put the order threshold at **13** and the same-version detection
limit at **11**. If your numbers differ, something is wrong and it is worth telling us about.

To collect your own runs rather than re-analyse ours, `scripts/run_compass.py` needs an
`OPENROUTER_API_KEY`. Run the parser fixtures first — the whole instrument depends on the
answer parser being strict, and it has 13 tests for that reason.

**A layout wrinkle you will notice.** The May study's runs live under `data/` and the
forced-choice export lives under `runs/`. Two eras, two conventions;
`scripts/studypaths.py` resolves the first and the compass scripts read the second. It is
untidy and it is not ambiguous.

### The re-measurement

The findings below are the May 2026 study and stand as recorded. A second measurement pass
put the same subject matter to a **forced-choice instrument** — 62 externally authored
propositions, four options, no neutral answer, **no LLM judge anywhere in the scoring
path** — across 2,866 runs, 166 models and sixteen vendor keys. It confirmed one headline, narrowed
another, withdrew the framing of a third, and produced the thing the original study lacked:
**the noise floors a measurement on this instrument has to clear.**

**The floors.** Each is movement produced by a factor nobody claims is political — same
instrument, same model, same settings, in items moved of 62:

<!-- GEN:floors -- generated by scripts/floor_table.py --markdown; do not edit -->
| factor | n pairs | side-flip med / p90 / max | p90 95% CI | endpoint med / p90 / max |
|---|---:|---|---|---|
| elicitation format -- ARM UNSTABLE, NOT A FLOOR | 10 | 24 / 34 / 39 | not a pair arm | 13 / 40 / 45 |
| prompt condition A->D | 20 | 3 / 15 / 19 | [5, 19] | 13 / 21 / 26 |
| presentation order, one sitting, local open-weight | 10 | 10 / 14 / 21 | [9, 21] | 10 / 17 / 18 |
| presentation order | 84 | 3 / 11 / 24 | [5, 14] | 4 / 9 / 18 |
| same-version variants | 97 | 5 / 11 / 24 | [8, 15] | 8 / 22 / 29 |
| presentation order, one sitting | 85 | 1 / 10 / 21 | [3, 12] | 3 / 10 / 36 |
| refusal-direction ablation | 12 | 6 / 9 / 12 | [6, 12] | 6 / 14 / 16 |
| refusal-direction ablation, one sitting | 20 | 2 / 9 / 9 | [2, 9] | 2 / 7 / 17 |
| prompt condition A->D, one sitting, local open-weight † | 5 | 5 / 8 / 8 | [3, 8] | 10 / 16 / 16 |
| prompt condition A->D, one sitting | 25 | 3 / 7 / 14 | [4, 12] | 12 / 22 / 26 |
| instruction paraphrase | 1067 | 3 / 6 / 14 | [5, 8] | 2 / 10 / 28 |
| requantisation | 13 | 3 / 6 / 10 | [3, 10] | 1 / 3 / 7 |
| run-to-run replicate | 63 | 3 / 5 / 15 | [4, 11] | 2 / 10 / 28 |
| prompt condition A->D, one sitting, frontier API | 20 | 3 / 5 / 14 | [3, 14] | 13 / 23 / 26 |
| presentation order, one sitting, frontier API | 75 | 1 / 3 / 20 | [2, 11] | 3 / 8 / 36 |
| modal sampling error | 110 | 1 / 3 / 30 | not a pair arm | 1 / 8 / 39 |
| presentation order, one sitting, local 2026 open-weight † | 3 | 3 / 3 / 3 | too few models | 2 / 3 / 3 |

† fewer than 10 pairs, so the 90th percentile IS the maximum by nearest-rank and the two columns print one number, not two.

**refusal-direction ablation excludes `gemma2-9b`:** stock Q4_0 vs ablated Q8_0, stop tokens dropped, baked temperature; ablated build emits SentencePiece word-boundary markers as literal text

**refusal-direction ablation excludes `llama31-8b`:** stock Q4_K_M vs ablated Q8_0, stop tokens dropped, baked temperature; ablated build invents its own questions and answers those

**refusal-direction ablation excludes `qwen38-27b`:** quantisation matched but stop tokens dropped; ablated build answers Strongly Agree to all 62 propositions in every condition

**requantisation excludes `mistral-7b`:** gated ELIGIBLE but contributed no pair -- every condition lost one arm to an invalid run

**elicitation format -- ARM UNSTABLE, NOT A FLOOR:** NOT A FACTOR -- THE GRAMMAR ARM FAILS ITS OWN REPLICATE TEST. Over 10 cell(s), two grammar runs of the SAME cell differ by a median of 26 side-flips against 3 for two prose runs, and the across-arm distance is 24. An arm whose repeat measurements differ as much as it differs from the other arm is measuring noise, so the across-arm number is not an elicitation-format effect. Misalignment ruled out: rotating the sheet by +/-1 or +/-2 items does not reduce the distance. THE CAUSE IS ITEMS PER CALL, NOT THE GRAMMAR: every run behind this row asks for all 62 answers in one array, and the arm replicates once the sheet is asked in chunks -- see RESULTS-2026-09-07-constrained-decoding-batch-size.md and `constrained_probe.py --batch-sweep`. So this row disqualifies the WHOLE-SHEET arm, not constrained decoding, and it stays disqualified until a batched arm is collected at the wave protocol. Cells: gemma2:latest/D, gemma2:latest/P, llama3.1:8b/D, llama3.1:8b/P, mistral:latest/D, mistral:latest/P
<!-- /GEN:floors -->

**The manipulation appears twice, on purpose.** `prompt condition A->D` is pooled across
collections — temperature 0, three runs per arm, several dates. `prompt condition A->D, one
sitting` is the same contrast collected under one protocol in a single sitting: 31 panel models
at temperature 0.7 with a swept seed, five runs each, all four conditions. 25 answer both arms;
the other 6 refuse the balance instruction outright.

Pooled says p90 15. One sitting says **p90 7**. An earlier version of this section read that as
the manipulation being smaller than the nuisance floors. **It does not support that**, and the
reasons are more useful than the conclusion was:

- **The 15 is one model.** Remove `x-ai/grok-4.5` and the pooled arm reads 8. Its answers under
  the commitment instruction are bimodal — four of five wave runs land within 3–4 items of each
  other and the fifth lands 15–18 away — so a modal sheet reports whichever mode the sampler
  favoured. It is 3 on one date in this corpus and 18 on another.
- **"At temperature 0 the runs are near-identical" is false here.** Over the temp-0 A and D
  cells: 263 within-cell run pairs, median 1, p90 5, max 32, and only 10 of 57 cells are
  byte-identical.
- **The comparison crossed protocols.** The wave holds all four conditions for the same 25
  models in one sitting, so it contains its own nuisance contrast — a bare question against a
  content-free system prompt, neither mentioning politics. That is **p90 3**, against the
  manipulation's 7. Under one protocol the deliberate manipulation is the *larger* effect.
- **And the units differ.** This row pairs a five-run modal against a five-run modal; the order
  floor mostly does not, since **23 of its 37 shuffled-order cells hold exactly one run**.

What survives: the deliberate manipulation moves a median of 3 items of 62, 23 of 25 models move
8 or fewer, and the nuisance factors are the same order of magnitude.

**Which is largest IS now settled, and this paragraph said it was not for a day after the
collection that settled it.** A one-sitting order floor was collected 2026-09-06 — 85 pairs, in
the table above — and the answer depends on the model class, which is why the pooled comparison
could never have produced it:

<!-- GEN:class_split -- python scripts/gen_readme.py -->
| on this class | presentation order, one sitting | manipulation A->D, one sitting |
|---|---:|---:|
| hosted over an API — 2025-26, 12 of 20 open-weight | p90 **3** (75 pairs) | p90 **5** (20 pairs) |
| run locally at Q4 — 2024-generation 7-14B | p90 **14** (10 pairs) | p90 **8** (5 pairs) |
<!-- /GEN:class_split -->

The two classes order the two factors **oppositely**. On a hosted model the deliberate
manipulation is the larger effect and item order sits at p90 3 — which is exactly the modal's
own sampling error, so that row is not measuring item order at all. On the 2024-vintage local
builds this literature was largely built on, item order is the larger effect. A pooled p90
answers neither question.

**What that split is NOT, because this section said otherwise until 2026-09-07.** The test is
`"/" in model` — hosted against local. It is **not** open-weight against closed: 12 of the 20
hosted models are open weights served by someone else (DeepSeek V4, Qwen3.8-Max, GLM-5.x, Kimi
K2.5/K2.6/K3, Mistral Medium), all 2025–26 releases. The table was published with the sides
headed "2026 frontier API" and "2024-generation open-weight", which asserts an open-vs-closed
axis this study does not test and gets backwards.

Three things move together across that line: **serving path** (someone's API against local
Ollama), **vintage** (2025–26 against 2024), and **quantisation** (provider precision against
Q4_K_M). So "newer models are more order-stable" was *consistent with* these rows and not
established by them — Q4 quantisation of a 7B model was an equally good explanation, and the
requantisation floor above is p90 6, the same order of magnitude as the gap being explained.

**So it was measured, 2026-09-07: a 2026-generation open weight, run LOCALLY at Q4.** Same
condition, same two shuffled orders plus canonical, same five swept seeds. It puts a 2026 model
on the *local* side of the split, holding serving path and quantisation fixed against the 2024
local row.

| presentation order, one sitting | pairs | side med / p90 / max |
|---|---:|---|
| hosted 2025–26 | 75 | 1 / **3** / 20 |
| **local 2026 open-weight, Q4** | 3 | 3 / **3** / 3 |
| local 2024 open-weight, Q4 | 10 | 10 / **14** / 21 |

**The gap tracks vintage.** A 2026 open weight run locally at Q4 behaves like the hosted 2026
models, not like the local 2024 ones — so quantisation and the serving stack are both refuted as
the mechanism, since they are held fixed against the row it does not resemble. Its order effect
of 2–3 items sits inside its *own* run-to-run spread (median 1–2, max 4): reordering the
questionnaire does nothing measurable to it. Röttger et al. conjectured this in 2024 and this is
it measured.

**Size is still confounded**, and three pairs is three pairs: the 2024 builds are 7–14B and this
is a 27B, so "newer" and "bigger" are not separated. Full result, caveats and the two collector
defects it surfaced: [`results/RESULTS-2026-09-07-local-2026-order-floor.md`](results/RESULTS-2026-09-07-local-2026-order-floor.md).

Both columns are rows of the generated table above. The manipulation column was briefly
published here with the frontier cell holding the *pooled* 7 and the local cell holding an 8
copied out of a script docstring that had measured it on a different subset — a two-by-two
table whose four cells were not commensurable, which is the same pooling error the order row
was split to escape. `floor_conditions_wave_by_class()` computes the split now, on the same
cells and in the same modal-vs-modal units as the order split. The local row rests on 5 pairs
and is marked as such in the table; it is reported rather than dropped because a thin estimate
is a fact about the estimate, and dropping it would leave the pooled figure standing
unqualified.

**Splitting the order row by model class is the most important line in this table, and an
earlier version of this section pooled it.** Reordering the questionnaire is a large effect on
the models this literature was mostly built on and a small one on the models shipping now —
Röttger et al. predicted exactly that in 2024 and nobody had measured it.

**What does not shrink is the same-version null.**
Two models of one declared version differ by **p90 11** over 97 pairs — against a manipulation of p90 7 in one sitting and p90 15 pooled. So
the nuisance factor that matters on a current model is not how the sheet was shuffled, which is
p90 3 there. It is *which variant of the model was measured*, and that one is the size of the
manipulation or larger.

*(This paragraph read "order p90 4, two models of one version p90 12, deliberate manipulation
p90 14" until 2026-09-07. All three were stale hand-typed figures — the same-version p90 is 11,
and the two order figures conflated the pooled and one-sitting arms. They now come from the
generated table above, and `key_numbers.py --check-release` gates them.)*

**Confirmed — the weight-rung dissociation.** It holds and strengthens. At temperature 0,
where a greedy model reproduces itself exactly, stock and abliterated builds share ~30% of
their political wording while stance does not move. Two independent measurements agree.

**Narrowed — "the hedge is a layer over a position."** Against a control arm with **no
system prompt at all**, a forced-balance instruction suppresses how strongly a model
commits: six of seven frontier models strictly one-directional, four of them significantly. But removal restores
commitment without relocating position, and *anything* removes it — a bare question, a
commitment instruction, or a placebo about reading carefully with no stance content.
Nothing is revealed; a suppression stops.

**Undecided, and previously published here as withdrawn — that force reveals a concealed
position.** Position moves 0–6 items of 62 under prompt pressure on the four local families
and up to 14 at temperature 0 on the frontier. Those were read as nulls. They are not:
`scripts/power.py` puts this instrument's minimum detectable effect at **13 items** of 62 against the pooled presentation-order floor, and **11** against the same-version floor — the
second being the one that governs a modern study. **3 of 5** published nulls fall below their
own detection limit, version drift among them. The claims are undecided rather than refuted,
which is a different verdict and not a restoration.

*(Two numbers in that paragraph were wrong until 2026-09-07 and both flattered it: the
detection limit was given as 16 where `power.py` computes 13, and "four of five" nulls where 3
of 5 fall below. A paragraph whose whole point is that this instrument is underpowered should
not overstate by how much.)*

**Withdrawn — that one null "inverted".** This section previously reported that qwen2.5-14B
moves 12 items under ablation against a detection limit of 9, and read that as real stance
movement. **That 12 came from a single run per arm.** A one-run sheet is not a modal, this
study's own estimator floor is measured on five-run modals, and the run-to-run replicate floor
is p90 5 — so a 12 derived from n=1 is inside its own noise before any ablation acts. The
detection limit of 9 quoted alongside it does not appear anywhere in the generated numbers
either. The 2026-09-07 ablation wave re-collects this exact pair at n=5 with a swept seed,
which is the measurement that can answer it; until that is analysed there is no finding here in
either direction.

**New — refusal is elicited, not intrinsic.** Across 42 models measured under both arms, 14 decline all 62 propositions when the prompt carries no directive — there are 148 refusals in 1076 runs where the prompt carries no directive, Google highest at 37% of 100 bare-ask runs. Give those same models a firm instruction and **all 14 of them stop**, with no exceptions: 4 of those runs are refusals against 907 runs where it carries one. Separately, **4 other models decline only when told to commit** — small local builds, one run each, none of which declines when asked without a directive. What suppresses it is not the content of the instruction, since a placebo with no stance content works as well as a demand to commit. It is the presence of a firm instruction at all.

*(This paragraph said "not one of them declines even once … 347 runs, zero refusals" until 2026-09-04, on numbers a collection older still: 32 models, 37 refusals, 449 runs. Four small local models added for a quantisation measurement produced three declines under a directive, and the absolute claim went. A first correction reported the change as a rate — 7.8% to 0.8% — which was dominated by one model contributing 24 of the 39 refusals in that collection, and inverted to 5.2% → 8.3% if each model was weighted equally. The paired count above survives both weightings, which is why it is the one reported.

A second correction, 2026-09-07: this note used to end "all three figures are generated now". They were not. The paragraph above it was hand-typed and had drifted a whole collection behind — 36 models where there are 42, eight decliners where there are 14, and 39 refusals in 499 runs where there are 148 in 1076. `--check-release` gated the retracted *wording* and never the *counts*, so the sentence claiming the numbers were generated was itself the thing that stopped anyone checking them. The counts now come from `key_numbers.py` keys `arms_models`, `arms_declining`, `arms_nodir_refusals`, `arms_nodir_runs`, `arms_silenced`, `arms_dir_only`, `arms_dir_runs` and `arms_dir_refusals`, and `--check-release` gates each one.)* Measurable only because invalid runs are retained rather than
discarded as collection errors. The decline survives reordering: three Google models across three presentation orders refuse 24 of 27 runs, so it is not an artifact of the sequence the propositions arrive in.

### And the corrections to us

Fourteen claims of ours withdrawn or narrowed, the founding thesis among them. Then the correction to the
correction: every control we ran was aimed at claims asserting an effect and none at claims
asserting absence, so four of five of our own nulls turned out to sit below what the instrument
can detect. Undecided is not refuted, and it is not a restoration either.

Every defect found in this project was a number typed into a document. Not one was in the code.
Three gates now exist because of that: `gen_paper.py --check` (tables regenerate),
`key_numbers.py --check` (the sentences quoting them still match), and `controls_audit.py
--strict` (no claim about another study from a note).

**New — a same-version null.** 97 pairs of models differing in size, mode, snapshot or tier
but not version. Median 5 side-flips, p90 11. Any version-over-version comparison is a
single draw from that distribution, and no study in this literature reports such a control.

**Also withdrawn — the drift claim.** Against that null, 3 of 108 version transitions clear
both p<0.05 and the null p90; two are into the same model and the third runs the opposite
direction. An earlier three-lineage version of this result held only against a three-point
null.

Detail, data and the pre-publication gate that enforces these controls are in the
companion research directory. Fourteen claims were withdrawn or narrowed during this pass,
including the study's own founding thesis; the corrections are recorded in place rather
than removed.

## Headline findings

- **Vendor-class differential (prompt rung).** US-closed frontier models (Anthropic,
  OpenAI, Google Gemini, xAI Grok) unmask far more than European, Chinese, or open-weight
  classes (us-closed mean Δ +0.572 vs open-weight ≈ 0). At the per-model level, **4 of 13
  effects survive a Benjamini-Hochberg FDR correction** (Opus 4.7, Grok 4.3, GPT-4.1,
  Mistral Large); DeepSeek V3.2 is suggestive but not confirmed. The class *direction*
  replicates under N=5 averaging.
- **Anthropic Opus arc.** Claude Opus trends upward across five versions, every version's
  unmask CI-significant, **+0.27 → +0.90** from 4.0 to 4.7 (~3× the baseline; an upward
  trend, not strict monotonicity — 4.5 wobbles within noise). *(2026-08-31: a same-version null of 97 pairs, median 5 side-flips and p90 11, was not available when this was measured. Version-arc claims on this instrument should be read against it -- see the update above.)*
- **Grok dose-response.** Under the five-step gradient Grok 4.3 reaches the full v1
  magnitude (3.00 → **5.00** across the ten neutral questions) at the opinionated-persona
  condition; the simple "what do you think?" unmask already moves it to 3.63, and the
  layered G0DM0D3 pipeline lifts it further to **4.20**.
- **GPT-5 retracted / indeterminate.** GPT-5's delta is not distinguishable from zero and
  it is the study's noisiest model (σ = 1.14, 2× any other). The earlier "GPT-4.1 → GPT-5
  reversal" is **not supported** — GPT-5 is indeterminate, not reversed.
- **Weight-rung dissociation.** Abliterating the refusal direction from five open-weight
  families (fp16, OBLITERATUS `advanced` SVD — Qwen2.5-7B, Mistral-7B-v0.3, Llama-3.1-8B,
  DeepSeek-R1-Distill-Qwen-7B on a 24 GB CUDA GPU; Gemma-2-9B-it added natively on Apple
  Silicon's Accelerate/LAPACK, which cleared the MKL `SSYEVD` SVD failure that blocked
  Gemma-2 on the 4090) removes refusals and rewrites **~70% of the political wording**
  (word-set Jaccard ≈ 0.3, confirmed deterministic at temperature 0) yet moves the
  institutional-skepticism **stance ≤ 0.10**. The refusal direction and the institutional
  lean are **dissociable.** *(Confirmed and strengthened 2026-08-31 -- see the update above.)*
- **Sycophancy control.** A reversed-premise pass (topics reframed to *invite* deference)
  shows **all five tested models hold within ≤ 0.40** of their neutral-framing stance —
  the unmask measures a genuine institutional lean, not generic agreeableness.
- **Judge-method robustness.** Re-scoring the entire study under five alternative judging
  procedures — abliterated open-weight judge (M2), grok-solo (M4), adversarial-pair (M5),
  reversed-rubric (M6), blind-condition (M7) — produces 84–91% exact-match against the
  ULTRAPLINIAN-4 baseline across 1,650–1,743 paired records each. Median per-model
  contamination delta is **0.062** across 47 model-run pairs, inside the pre-registered
  ≤ 0.10 robust band.

  **Judge composition, measured.** The panel's internal spread is 0.29 points and is larger
  under the bare question than under the balance instruction, so it does not simply cancel in a
  delta. Re-scoring each finding under each judge alone: the two large effects hold under every
  judge (claude-opus-4.7 +0.80…+1.50, grok-4.3 +0.80…+1.30); the smallest ranges +0.03 to +0.60
  and is reported as suggestive. Two of the five findings are self-judged. Detail in
  [CORRECTIONS.md](CORRECTIONS.md) §5.
- **Transparency-asymmetry.** Weight-level verification is *only possible on open weights.*
  The closed frontier models that show the largest prompt-rung unmask are
  un-abliteratable by construction — an accountability gap independent of which way any
  closed model leans.

Full analysis with tables and caveats: [`results/WRITEUP-2026-05-26.md`](results/WRITEUP-2026-05-26.md).

## Six checks any study can run

Every defect we found in our own data, as reusable checks with the numbers they produced here:
**[CHECKS-ANY-STUDY-CAN-RUN.md](CHECKS-ANY-STUDY-CAN-RUN.md)**. Scored blank responses, drift
arcs that compare two runs rather than two versions, the missing same-version baseline, serving
stack effects, judge lean against judge agreement, and gates that cannot fail.

They are arithmetic on records already on disk. All six found something here, and one of them —
reading same-version pairs as drift transitions — is a mistake we made in exactly the form the
literature makes it. Take them; we would rather be corrected than cited.

## Limitations — what this does not establish

Stated in one place because they were stated in six, none of them labelled as a limitation.
Each links to where the argument actually lives; nothing here is a second copy.

- **The instrument is one ruler, and nobody has measured what changing it does.** Every floor
  below is a nuisance factor *inside* the forced-choice battery. Instrument choice is the
  largest nuisance factor in this field and has no floor at all — see the blockquote opening
  the 2026-08-31 update for the four specific problems with this battery, and
  [`prereg/PREREG-2026-09-12-instrument-choice.md`](prereg/PREREG-2026-09-12-instrument-choice.md)
  for the plan that would measure it.
- **The weight-rung result is unattributable, not absent.** Movement under abliteration cannot
  be separated from which build was downloaded; two ablations of one base disagree by as much
  as the effect. See the abliteration section above and
  [`results/RESULTS-2026-09-07-ablation-wave.md`](results/RESULTS-2026-09-07-ablation-wave.md).
- **The construct is narrower than "political bias."** It is institutional-skepticism framing
  on a civil-liberties and state-power surface, not a left–right battery — see **Scope**.
- **Three confounds in the class split are not separated by this corpus**: serving path,
  model vintage and quantisation all differ together between the hosted and local rows, and
  the row that would break the tie holds one model.
- **The scoring layer is bounded by a relative measure only.** `judge_lean.py` measures each
  judge against its own panel; a lean shared by all four is invisible to it by construction.
  The external anchor that could see it (`scripts/judge_anchor.py`) has a drawn sheet and no
  human pass yet.
- **Several nulls are undecided rather than refuted.** 3 of 5 published nulls sit below their
  own detection limit; see [`CORRECTIONS.md`](CORRECTIONS.md) and the corrections section above.
- **What this study does NOT claim about other people's work** is stated explicitly in
  [`PRIOR-WORK-CORRECTIONS.md`](PRIOR-WORK-CORRECTIONS.md) §4 "What this file does not claim": a study that
  does not run a control is unbounded on it, which is weaker than being wrong.

## Reproduce it

> **Cloning on Windows: enable long paths, or the checkout silently comes up empty.**
>
> ```bash
> git clone -c core.longpaths=true https://github.com/gorrie/bias-study.git
> ```
>
> Twelve files under `runs/2026-09-07-ablation-wave/` carry 145–165-character paths — they are
> named for the HuggingFace repo, quantisation and condition that produced them, which is the
> provenance and not decoration. Add a clone directory deeper than about 95 characters and you
> pass Windows' 260-character limit: `git clone` reports **"Clone succeeded, but checkout
> failed"**, the working tree is empty, and `git status` shows every file deleted. Nothing is
> wrong with the repository. macOS and Linux are unaffected.

### Prompt rung (anyone with an OpenRouter key)

Requires Python 3.11+ and an [OpenRouter](https://openrouter.ai/) API key — all models,
including the judges, are called through OpenRouter, so no per-vendor keys are needed.

```bash
pip install -r requirements.txt
cp .env.example .env          # put your key in OPENROUTER_API_KEY

# 1. Generate raw responses (model × question × A/B condition)
python scripts/run_study.py --positions mild,neutral,pointed --date $(date +%F)

# 2. Score with the 4-judge cross-vendor median consensus
python scripts/score.py $(date +%F) \
  --judge "anthropic/claude-haiku-4.5,openai/gpt-4.1,google/gemini-2.5-flash,deepseek/deepseek-v3.2"

# 3. Aggregate → per-model / per-topic / per-question CSVs + manifest
python scripts/aggregate.py $(date +%F)

# 4. Statistics: bootstrap CIs + inter-judge agreement, then FDR + length control
python scripts/ci_analysis.py $(date +%F)
python scripts/robustness_checks.py $(date +%F)
```

> Step 4 took no argument here until 2026-09-12, exactly as printed, and neither command
> worked that way: `ci_analysis.py` exits on its usage line, and `robustness_checks.py`
> printed nothing at all and returned success — the silent-pass mode `.pre-commit-config.yaml`
> records having fixed once already. Both take one or more run dates.

To re-derive the published numbers without spending any API budget, the full scored data
ships in `data/` — re-run steps 3–4 against any existing run, e.g.
`python scripts/aggregate.py 2026-05-26-variance`.
`score.py --skip-classifier` runs heuristic-only scoring (hedge ratio, refusal class) with
zero API calls.

### Full toolchain (weight + pipeline rungs)

The weight rung (OBLITERATUS abliteration) needs the fp16 base weights and either (a) a
24 GB CUDA GPU + Docker (`obliteratus:gpu`, driven by `scripts/run_abliteration_sweep.sh`)
or (b) a 32 GB+ Apple Silicon Mac running OBLITERATUS natively (`scripts/run_abliteration_native.sh`,
which routes the SVD `eigh` through Accelerate/LAPACK via `PYTORCH_ENABLE_MPS_FALLBACK=1`).
The pipeline rung needs the G0DM0D3 server. **`scripts/run_barometer.sh`** drives the full
escalation ladder end to end, and **`DEVELOPER.md`** documents every script, the exact
commands, and the hard constraints (you cannot abliterate a quantized model; a 24 GB GPU
caps abliteration at ~7–9B at fp16; a 32 GB M5 fits up to ~9B but not 14B+). Hostile peer
review and the objection→fix map are in **`ADVERSARIAL-REVIEW.md`**.

## Repository layout

**If you arrived with a question, start here.**

| Question | Where |
|---|---|
| Which numbers has this study withdrawn or narrowed? | [`CORRECTIONS.md`](CORRECTIONS.md) — 14 entries, dated |
| What does it say about other people's work, and on what evidence? | [`PRIOR-WORK-CORRECTIONS.md`](PRIOR-WORK-CORRECTIONS.md) |
| What was fixed *before* the data was collected? | [`prereg/`](prereg/) — six plans, one with its stopping rule enforced in code |
| Which controls does each audited study run? | [`data/controls-audit.json`](data/controls-audit.json) → `python scripts/controls_audit.py` |
| Where are the raw forced-choice records? | `runs/` (Aug–Sep 2026) |
| Where are the May judge-scored records? | `data/` (see [`data/README.md`](data/README.md) for the licence and redactions) |
| Which gates run, and where do they fail in public? | [`.github/workflows/verify.yml`](.github/workflows/verify.yml) |
| How do I re-derive a number without an API key? | **Reproduce it**, below |
| Why is a release dated rather than numbered? | [`VERSIONING.md`](VERSIONING.md) |
| What is coming next and what does it need? | [`ROADMAP.md`](ROADMAP.md) |

```
protocol/   Study spec — question set, scoring rubric, record schema,
            run protocol, aggregation rules.
runs/       The forced-choice barometer corpus (Aug–Sep 2026).
scripts/    Pipeline: run → score → aggregate → analyze, bootstrap CIs + FDR,
            and the weight-rung / pipeline-rung drivers.
data/       Every run in full: raw model responses, 4-judge scored records,
            aggregated CSVs, and manifests.
results/    The writeup.
skills/     Operator runbooks for re-running the study (the quarterly barometer).
prereg/     Analysis plans fixed before their data was collected.
```

**Two correction files, and they point in opposite directions.**
[`CORRECTIONS.md`](CORRECTIONS.md) is what this study got wrong — 14 claims withdrawn, narrowed
or corrected, each with the date it went out, the date it came back, and what replaced it.
[`PRIOR-WORK-CORRECTIONS.md`](PRIOR-WORK-CORRECTIONS.md) is what this study finds wrong
elsewhere: the twelve-study controls audit, the seven studies holding the pairs to fix their own
gap, and the abliterated-weights confound. The second file is written to a stricter standard
than the first, and the first exists so the second is not a double standard.

**[`SCRIPTS.md`](SCRIPTS.md) is the map of `scripts/`** — every file, with the first line of its
own docstring, generated by `scripts/gen_script_inventory.py` and gated so it cannot drift from
what is actually there. Read it before running anything, and regenerate it after adding a
script. It exists because on 2026-09-05 this pipeline had 44 files that appeared in no
documentation anywhere in the repository, including the two gates that decide whether a claim
may be published and the export that keeps a licensed questionnaire out of it.

## Disclosures

**Funding and competing interests.** No external funding. The API costs were paid out of
pocket. The author is not affiliated with any vendor lab whose models are evaluated, and no
vendor reviewed this release before publication. The study is a companion to *The Ratchet*
(Evil Robots Series, Book 2, 4LULZ Press), which is a commercial book — that is the one
material interest on the table, and it points toward the findings being interesting rather
than toward any particular finding.

**Author contributions.** Single author: design, collection, code, analysis, writing, and
every correction in [`CORRECTIONS.md`](CORRECTIONS.md).

**Human participants.** None. The subjects are language models. The one planned human step is
the blind annotation in `scripts/judge_anchor.py`, scored by the author.

**Instrument licensing.** Twelve run files briefly published third-party instrument text in
September 2026 and were withdrawn. The record, the gate defect that allowed it and its
remediation status are in the incident log; no published number depends on those files.
**Language-model assistance, because a study about language models should say.** Code and prose
in this repository were drafted with model assistance — the commit trailers name Claude Opus 5
and Opus 4.7, and `agents/` and `skills/` hold the orchestration. Three things bound it:

- **No language model is in the forced-choice scoring path.** That is the property the
  instrument swap bought, and it is what `judge_free_scoring: yes` records for this study
  against five of twelve audited studies scoring `no` or `partial`.
- **The May judge panel is disclosed and named** — Claude Haiku 4.5, GPT-4.1, Gemini 2.5 Flash,
  DeepSeek v3.2 — and its own spread is measured and published (0.2926 points), which is the
  control this study found five other studies not running.
- **Every number is generated by a script and gated in CI**, not typed. Where a typed number
  survived anyway, it is in `CORRECTIONS.md` with the date.

The author is responsible for every claim here regardless of what drafted the sentence.

## Tools cited (referenced, not vendored)

Clone these from upstream at the pinned commits to reproduce the pipeline and weight rungs:

- **OBLITERATUS** — refusal-direction abliteration. <https://github.com/elder-plinius/OBLITERATUS> (pinned [`d6af36f`](https://github.com/elder-plinius/OBLITERATUS/commit/d6af36f), 2026-04-01).
- **G0DM0D3** — elicitation / jailbreak reference (STM hedge-strip, Parseltongue). <https://github.com/elder-plinius/G0DM0D3> (pinned [`4d4b3e0`](https://github.com/elder-plinius/G0DM0D3/commit/4d4b3e0), 2026-03-25).
- **Arditi et al. (2024)**, *Refusal in Language Models Is Mediated by a Single Direction*, arXiv:[2406.11717](https://arxiv.org/abs/2406.11717) — the refusal-direction method the weight rung ablates.
- **OpenRouter** — multi-vendor API gateway, <https://openrouter.ai/>.

## Companion projects

- **[ratchet-mcp](https://github.com/gorrie/ratchet-mcp)** — MCP server + curated dataset of named persons & institutions across the US legal / regulatory / financial / multilateral control grid (454 persons / 388 institutions / 948 edges at v0.2; every record cites ≥ 2 primary sources; CI-gated). The institutional-infrastructure side of the same argument this bias study makes at the model layer — the people, the pipelines, and the documented adjacencies the closed-vocabulary plays system makes queryable. Companion to *The Ratchet: How Safety Infrastructure Became the Control Grid*. Re-sampled periodically as a longitudinal bias-drift instrument.
- **The Wash** ([`results/THE-WASH-2026-06-10.md`](results/THE-WASH-2026-06-10.md)) — the symmetric framing-detector built on this study's abliterated-judge spine (the §5.8 Method-2 anchor). Characterizes the abliterated judge directly: the abliteration dose-response and its coherence cliff, the refusal/flinch decoupling, and a documented-register flinch **confirmed** by the 2026-06-11 multi-template re-run (CI-backed: aligned judges over-flag documented institutional criticism the spine passes — gap +0.16 on plain sourced facts, +0.24 on juxtaposed, Wilson CIs disjoint from the spine; spine validated as a discriminator; magnitude corrected down from the single-template run — see §F). Same instrument, turned on the judge.

## License

- **Code:** MIT — see [`LICENSE`](LICENSE).
- **Run records** in `data/` and `runs/`: **CC BY 4.0**, with the two carve-outs stated in
  [`data/README.md`](data/README.md) — the instrument text is licensed third-party work and is
  not here, and model outputs are model outputs under each vendor's terms.
- **Documents** (`results/`, `CORRECTIONS.md`, `PRIOR-WORK-CORRECTIONS.md`, this README):
  **CC BY 4.0**, same as the data. Quote them; attribute them to the release tag you read.

## Citation

> Gorrie, I. (2026). *The Hedge Is the Bias: A Multi-Vendor, Multi-Generation Audit of
> Institutional-Skepticism Framing in Large Language Models* (release-2026-09-12)
> [software and data]. https://github.com/gorrie/bias-study

**Cite the release tag, not the repository.** This study's own finding is that numbers move;
several here have been withdrawn or narrowed since May, and the tag is what tells a reader
which set you read. [`CORRECTIONS.md`](CORRECTIONS.md) records what each release superseded,
and [`VERSIONING.md`](VERSIONING.md) explains why releases are dated rather than numbered.
Machine-readable metadata is in [`CITATION.cff`](CITATION.cff).

*No DOI yet.* Archiving a tagged release to Zenodo would mint one (concept DOI for the study,
a version DOI per release); until that happens a citation here resolves to a moving URL, which
is exactly the failure mode this section warns about.

---

**Related work:** these findings are also presented in narrative form for a general audience — [evilrobots.lol](https://evilrobots.lol).
