# Corrections to prior work

`CORRECTIONS.md` is what this study got wrong. **This file is what this study finds wrong
elsewhere**, and it is the harder document to write honestly, so it is written to a stricter
standard than the rest of the repository.

Every entry names the artifact, the specific claim or omission, the measurement that bears on
it, and — where one exists — **the remedy the authors can apply to their own data.** None of it
imputes motive. A methodological point does not need one, and this file has already been
reworded once to remove one (see `rozado2024` below, and the note in `scripts/controls_audit.py`).

---

For the same material as reusable checks rather than per-study findings — six defects we found
in our own data, each with the diagnostic and what it cost us — see
[`CHECKS-ANY-STUDY-CAN-RUN.md`](CHECKS-ANY-STUDY-CAN-RUN.md).

## The standard this file holds itself to

1. **Name the artifact and its version.** A correction that does not say which version it applies
   to is unfalsifiable, and every artifact below moves.
2. **Quote the design, not the author.** The entries describe what a paper does and does not
   measure. They do not characterise intent, competence or motive.
3. **Offer the remedy.** Where the data to fix the gap is already in the authors' hands, say so.
   **Seven of the twelve studies below are in that position**, two demonstrably are not, and for
   three nobody has established it either way — which `--gaps` now prints as three numbers
   instead of one list. This said "six" until 2026-09-12, against a list that rendered seven,
   because the list was selected on whether a study *reported* a same-version null and on
   whether someone had happened to write a note about it, rather than on whether the pairs are
   in its design. Two studies were missing from it for want of a note.
4. **Be reproducible.** Every figure here recomputes: `python scripts/controls_audit.py --gaps`
   for the audit, `python scripts/ablation_analysis.py` for the weight-rung result.
5. **State what is NOT claimed.** A study that does not run a control is not thereby wrong. It is
   unbounded, which is a different and weaker statement, and the difference is the whole point.
6. **Correct ourselves in public first.** `CORRECTIONS.md` lists every claim this study withdrew
   or narrowed, including one where the net-aggregate error "this paper convicts other studies
   of" appeared "in our own headline." That entry exists so this file is not a double standard.

---

## 1. The same-version null: absent from all twelve studies audited

**Artifact:** twelve external studies of political position in language models, audited against
thirteen controls. **Eleven of the twelve are read in full rather than from a summary** — the
last three were re-read on 2026-09-11, which is also when `--strict` stopped being able to
reject any verdict here for thin provenance.

The twelfth is **`sclar2024`**, and its record has said `provenance: partial` throughout: the
abstract and PDF were consulted on 2026-09-11, the full text was not read end to end, and the
record says so. It is in the table as a methodological reference on prompt-format sensitivity,
not as a political-position study; the columns that would need a full read to score fairly are
marked `n/a` with the reason given, and **its numbers must never be quoted as if they bound
this instrument.** This sentence said "all twelve" until 2026-09-16 — a hand-typed count
disagreeing with the generated record two files away, which is the defect this document exists
to catalogue in other people's work. `tests/test_prior_work_counts.py` now reads both.
**Reproduce:** `python scripts/controls_audit.py` (matrix), `--gaps` (tallies and per-study text).

A **same-version null** asks what two measurements differ by when *nothing about the model has
changed* — same version, different snapshot date, size, tier, or serving mode. Without it, an
observed difference between two model versions has nothing to be scored against.

**Tally across the twelve, on the distribution form of that control:**

<!-- GEN:tally_samever -- python scripts/gen_readme.py -->
| control | yes | partial | no | n/a | unknown |
|---|---:|---:|---:|---:|---:|
| `same_version_dist` — A same-version null as a DISTRIBUTION: median and upper percentile over many pairs, so a single observed transition can be scored against it | **0** | 1 | **11** | 2 | – |
| `same_version_point` — Any same-version or non-transition pair used as a negative control, even one | 2 | 3 | **7** | 2 | – |
| `reported_mde` — A minimum detectable effect, power analysis, or explicit resolution limit reported alongside the effects | 2 | 2 | **9** | – | 1 |
<!-- /GEN:tally_samever -->

**Not one of the twelve reports a same-version null as a distribution.** Ten are scored `no`
and the control does not apply to the other two. Six report no same-version pair of any kind,
not even one used informally. Eight report no detection limit of any kind.

Three of those cells read `unknown` until 2026-09-12, because three studies had been scored
from method-and-results retrievals rather than read end to end. Reading them turned two into
genuine absences and the third into an `n/a`. The headline got stronger, which is not the
reason it was checked — an absence claim sourced from what a reviewer happened to read is the
same defect this file documents in other people's work, one level up.

**What this study measures for comparison:** 97 same-version pairs, median disagreement **5 of 62**
forced-choice propositions, giving a detection limit of **11**. Presentation order alone reaches
p90 **14** and a maximum of **24** items on 2024-generation open-weight models, and p90 **6** on
2026 frontier models. Any claimed political shift smaller than the relevant floor is inside the
instrument's own noise, whatever its p-value.

### Seven of them can fix this from data they already hold

This is the constructive half, and it is why the file exists. In each case the pairs required are
already inside the published design:

| study | the pairs already in their design |
|---|---|
| `rottger2024` | GPT-3.5 0613 vs 1106 and GPT-4 0613 vs 1106 are snapshot pairs of one version; Llama-2 7b/13b/70b are size variants. All four sit in the model list as separate subjects rather than as a baseline. |
| `naser2026` | Same-version pairs exist inside their own tier ladder — mini vs flagship at one generation, dated snapshots of one name — and are read as drift transitions carrying *d* values rather than as a baseline. |
| `liu2025` | The same-version snapshot pair **is the treatment**, not a control. Their only null varies the API account, which bounds nothing about model identity. Two same-date cross-tier pairs are also in hand and neither is estimated. |
| `kamal2025` | A clean pair exists — Llama-3.2-1B-Instruct at full precision against the same model 4-bit, same version, same size, precision only — used as a generalisability check rather than a null. The difference is never computed. |
| `cen` | Three online/offline pairs of one model each. The difference is the finding rather than a null, and the pair is not clean: online runs at temperature 0.1 against 0 offline. |
| `sakhawat2026` | Size siblings from one release sit side by side in Table 7 — `gpt-4.1-nano`, `gpt-4.1-mini` and `gpt-4.1`, and the `gpt-5` family likewise. They are entries in a ranking, never a null, so the normalized-drift figure has nothing to be scored against. |
| `rozado2024` | The same-version siblings are **excluded on purpose, and he says so** — left out in favour of variety across model families. That is a stated sampling rationale, openly given. The consequence is that the comparison capable of bounding model-to-model difference is the one the analysis leaves out. Note what this does not say: his published data **does** contain same-version pairs — Grok in fun mode against Grok in regular mode among them — so they are absent from the reasoning, not from the corpus. The comparison point offered instead is what the paper calls a *reference fake model data point*, a synthetic random-answer respondent, which bounds nothing about model-to-model comparison. |

> The `rozado2024` entry read differently until 2026-09-06. It said the pairs were designed out
> "to make the sample look more varied," which imputes a motive to a rationale the author states
> openly. It was reworded. The methodological point does not need it, and neither does any other
> entry here.

**The remedy, in one line:** compute the disagreement across the same-version pairs already in
the sample, report it as a median and an upper percentile, and score the headline transitions
against it. It costs no new inference — the responses are already collected.

## 2. Abliterated model weights are not a controlled intervention

**Artifacts:** publicly distributed abliterated builds of `Qwen2.5-14B-Instruct` — `huihui-ai`'s
v1 and v2, and `Goekdeniz-Guelmez`'s `Josiefied-Qwen2.5-14B-Instruct-abliterated-v2`.
**Reproduce:** `python scripts/ablation_analysis.py`; pre-registered at
`prereg/PREREG-2026-09-07-ablation-vs-prompt.md` before collection; full result at
[`withdrawn/results/RESULTS-2026-09-07-ablation-wave.md`](withdrawn/results/RESULTS-2026-09-07-ablation-wave.md).

A growing amount of work uses off-the-shelf abliterated weights as if the abliteration were a
controlled edit — measure the stock model, measure the abliterated model, attribute the
difference to removing the refusal direction.

Three independent abliterations of one base, all quant-matched Q4_K_M, n=5 at temperature 0.7:

| build | author | stock → ablated (A / D / P) | vs floor 3 |
|---|---|---:|---|
| `huihui_ai/qwen2.5-abliterate:14b` | huihui-ai (v1) | 8 / 9 / 9 | clears |
| `Qwen2.5-14B-Instruct-abliterated-v2` | huihui-ai (v2, separate job) | 8 / 9 / 9 | clears |
| `Josiefied-Qwen2.5-14B-Instruct-abliterated-v2` | Goekdeniz-Guelmez | 0 / 2 / 0 | at or under |

And their agreement with each other:

| pair | side-flips (A / D / P) |
|---|---:|
| huihui v1 vs huihui v2 | **0 / 0 / 0** |
| huihui v1 vs Josiefied | 8 / 9 / 9 |
| huihui v2 vs Josiefied | 8 / 9 / 9 |

**Two builds by the same author agree exactly. The build by a different author disagrees by
precisely the size of the "effect" — and shows no effect at all.** The ablator spread (median 8,
max 9) equals the ablation effect (median 8, max 9).

**The correction:** an experiment comparing one stock model to one abliterated model measures
*that ablator*, not abliteration. The conclusion this study draws, under its own pre-registered
stopping rule, is **outcome 4: movement under abliteration is not separable from the choices of
the particular ablator**. Any single-ablator result, including the one this study published and
withdrew (`CORRECTIONS.md` #8), is a statement about the build.

Said precisely, because the imprecise version was published here until 2026-09-12: on two of the
three usable bases nothing clears the floor. On the third, qwen25-14b, **two of its three
ablations move position by 8 to 9 items of 62 and do clear it** — and the disagreement between
those ablations is 8 to 9 items as well. So the movement is real and unattributable, not absent.
This section previously read "abliteration does not measurably move political stance on any of
the three usable bases", which is a null, and a null is exactly what an unbounded measurement is
not. Section 1 of this document is about that distinction.

**The remedy:** use at least two independently-authored ablations of the same base, quant-matched
to the stock arm, and report their disagreement alongside the effect. If the two ablators differ
by as much as the intervention, there is no intervention to report.

## 3. The scoring layer: five studies put a model in it, and none reports what that model's own lean is

**Added 2026-09-11**, after re-reading **all twelve** in full for four controls that were
`unknown` across the whole matrix until that day. These four columns are complete: no study is
`unknown` on any of them. Each was added on 2026-09-05 and every one was found by **failing it
ourselves** — which is why they are columns and not a paragraph.
**Reproduce:** `python scripts/controls_audit.py --gaps`.

<!-- GEN:tally_scoring -- python scripts/gen_readme.py -->
| control | yes | partial | no | n/a | unknown |
|---|---:|---:|---:|---:|---:|
| `judge_free_scoring` — No language model anywhere in the scoring path -- answers are recorded mechanically (forced choice, item id + position) rather than read and rated by a model | 9 | 2 | 3 | – | – |
| `judge_lean_reported` — If a model DOES score the responses, the study reports that scoring layer's own lean as a magnitude -- per-judge deviation, or an equivalent -- rather than asserting agreement and stopping | **0** | 1 | 4 | 9 | – |
| `self_judging_disclosed` — No subject of the study also sits on the panel that scores it, or if one does, the study says so | 1 | 3 | 1 | 9 | – |
| `longitudinal` — The same subject re-measured over CALENDAR TIME under held parameters | 1 | 1 | **12** | – | – |
<!-- /GEN:tally_scoring -->

**Five studies put a language model in the scoring path.** `rozado2024` parses every response
through gpt-3.5-turbo for stance detection; `cen` pre-processes through GPT-4o mini;
`messing2026` uses a three-judge panel by design; `rottger2024` classifies its open-ended arm
with GPT-4 0125; and `naser2026` runs a regex first and then **"applied a backup language model
parser for responses deviating from the expected format."**

**Not one of the five reports that scorer's own lean as a magnitude.** `messing2026` comes
closest and is scored `partial`: it reports variance components for judge *disagreement*, which
is the quantity the control is reaching for, without isolating an individual judge's bias.

**`naser2026` is the one a reader is most likely to miss, and it is worth its own line.** The
model in its scoring path is introduced as *parsing*, not judging — a fallback for responses the
regular expression could not read. But a language model mapping free text to a numeric Likert
rating is scoring, whatever it is called, and it decided the disposition of every response the
regex failed on. **The model is not identified** — no vendor, no version, no family — in the
paper or in its published dataset card, which are what we read. Nor does the paper report the
share of responses that reached that second stage, which is the figure that would settle how
much of the result the fallback decided: if it is a handful, the label "parsing" is fair; if it
is a third, it is a scoring layer with no provenance. So unlike `rottger2024` and `rozado2024`,
where both roles are named and merely not reconciled, here a reader cannot establish whether
the scorer was one of the thirteen subjects. That is the one `no` on self-judging disclosure.

In the other cases the scorer is drawn from the same family as a subject. Only `messing2026`
states it outright — "Three LLM judge models (GPT-4o, Gemini 2.0 Flash, Claude Haiku 4.5) and
three SUTs (GPT-4o, Gemini 2.0 Flash, DeepSeek Chat v3.1)" — which is why it holds the single
`yes`.

**`rozado2024` is the sharpest case, and it is worth stating without ornament — including the
part that is in his favour.** The paper's subject is the political preference of language
models. Its scorer is a language model, and per the published data that scorer is also one of
its twenty-four subjects.

The scorer is **not unchecked**: Rozado validates it against his own hand-coding of a random
sample of 119 test questions, reporting **93% agreement, Cohen's κ = 0.91**. That is a real
control and more than most of this table runs. It is also a different quantity from the one
this column asks for — agreement with a human on a sample bounds the scorer's *accuracy*, not
its *lean*, and a scorer can agree with a human 93% of the time while the 7% falls
systematically one way. The lean is not reported, and the subject/scorer overlap is not
discussed. Any criticism of this scoring layer has to be made with the validation on the table.

**We failed the same control.** Scoring retained since May showed **0.3007 points between our
most skeptical and most deferential judge**, against five published CI-clean effects of +0.90,
+0.90, +0.4333, +0.3000 and +0.2333. The spread is larger than the smallest of them and lands
within nine thousandths of the second smallest — and we had never computed it.

That sentence read "larger than two of our own five published effects" until 2026-09-12. It was
wrong, and it was wrong in the direction that made the self-criticism sound better: `judge_lean.py`
printed the comparison as a typed literal rather than computing it, five documents copied the
literal, and at two decimal places 0.29 against 0.30 is invisible. The script computes the count
now. A file that convicts other people of trusting a typed number had its sharpest sentence
about itself typed. Two of our five CI-clean findings
were self-judged with nothing disclosing it until 2026-09-05. The column exists because of that,
not because of anybody else.

**The remedy, and it is cheap for anyone already holding the data:** score a fixed set of
responses under each judge separately and report the spread between them. It requires no new
model calls if the per-judge records were kept, and it converts "the judges agreed" into a
number a reader can compare against the effect.

### The one control where we are behind

`longitudinal` — the same subject re-measured over calendar time, as opposed to a cross-section
of versions taken on one date. **Ten of the twelve do not do it. One does: `cen`, querying 12
models near-daily from July to November 2024**, and `aipolcom` earns a `partial` for a rolling
collection with named re-collection dates. Our own row is `partial` too: the forced-choice
corpus spans six days, which is not a time series.

`naser2026` is the sharpest near-miss, because it names the problem and then does not run the
control. Its subject is moral drift *across model generations*, its collection is one pass per
model — "we completed all probes for each model before proceeding to the next" — and its own
limitations section says: *"Test-retest reliability faces complications when models are updated
between testing occasions and may conflate measurement error with genuine change."* That is an
accurate description of why the control is hard, offered in place of the control.

`liu2025` is the instructive near-miss. Its finding is a *"statistically significant rightward
shift in political values over time"*, and what it compares is builds 0613 against 1106 — its
figure captions read "at different times" and mean different versions. A version cross-section
is a legitimate design; it is just not a measurement over time, and the distinction is the whole
reason this is a separate column.

## 4. A version arc computed from runs, not versions — our own defect, offered as a check

**Artifact:** this study, `drift_timeseries.py`, corrected 2026-09-12. **No external study is
accused of this.** It is here because standard 6 says we correct ourselves in public first, and
because the check costs nothing and we could not find it reported anywhere.

**The defect.** Our per-vendor arcs were computed as `deltas[-1] - deltas[0]` — the last
measurement row minus the first — and printed as "delta from oldest to newest". A row is a
`(version, run)` pair, not a version. Where a family had been measured several times at one
version, the statistic subtracted one arbitrary run from another arbitrary run **of the same
model** and published the result as version drift.

**What it did to our own output, which is the point:**

| | published | after the fix |
|---|---|---|
| families with exactly one distinct version, publishing an arc direction | **4 of 12** | 0 |
| section headings counting measurement rows and calling them versions | all 12 | 0 |
| families whose verdict changed | — | **6 of 12** |
| directions withdrawn outright | — | 1 (`moonshot-kimi`, "decreasing" → stable) |

Our `xai-grok (8 versions)` was `grok-4.3` measured eight times. Its repeat measurements at that
single version span **0.90**, while we were labelling arcs of ±0.2 directional — a threshold an
order of magnitude below the noise, with nothing in the output saying so.

**The remedy, in one line:** aggregate within a version before comparing versions, refuse to
report an arc below two distinct versions, and print the within-version spread beside the arc so
a reader can see whether the direction clears its own noise. Ours does now; three of our thirteen
arcs survive as directional claims.

**What this does NOT claim.** We have not established that any published study computes its drift
statistic this way. Doing so would require re-reading each paper's analysis code or a statement
of the aggregation step, and most do not publish either — which is itself the finding available
here: **the aggregation step between "we measured these versions" and "this is the drift" is
usually not stated.** The related and *established* gap is in section 1: seven studies hold
same-version pairs and read them as transitions rather than as a baseline. This section is
narrower and about arithmetic, and we are the only study we can prove got it wrong.

**How to check yours.** Count distinct versions per family, not measurement rows. If any family
has one, it cannot have an arc. Then compare your arc magnitudes against your own repeat
measurements at a single version. If the second number is larger, the first is not a direction.

## 5. What this file does not claim

- **It does not claim any of these studies reached a false conclusion.** A study without a
  negative control is *unbounded*, not wrong. Several of the effects audited here may well be
  real; the point is that nothing in the published design can tell the reader which.
- **It does not rank the studies.** The audit matrix has thirteen columns and this study is
  "no" or "partial" in some of them too. The matrix prints our own row for exactly that reason.
- **It does not survive its own floors automatically.** Where this study's effects fall under its
  floors, they are recorded as undecided — see `CORRECTIONS.md` and the `README` headline block.
- **It is versioned.** These entries describe the artifacts as read on the dates in
  `scripts/controls_audit.py`. An author who adds a null has fixed it, and this file should then
  be corrected — which is a correction *to this file*, and belongs in `CORRECTIONS.md`.

## 6. If you are one of the authors cited here

The audit's per-study text is in `scripts/controls_audit.py`, in the record for your study, and
it is the single source for the table above — there is no second copy to fall out of sync.

If an entry misreads your design, that is a defect in this repository and it will be corrected in
`CORRECTIONS.md` with the date and what replaced it, the same as every other correction here.
Open an issue with the specific line. If the entry is right and you have since added the control,
say so and it will be updated to reflect it.

---

<!-- GEN:references -- python scripts/gen_readme.py -->
## References

Generated by `scripts/references.py` from `data/controls-audit.json`, the same record that supplies each study's row in the controls table. The provenance note on each entry says how we know what we claim about it.

- **barmettler2026** — Barmettler, Progressive in Principle, Centrist in Practice: LLM Political Bias Is Instrument-Dependent, arXiv:2606.00048.
  *Instrument:* Smartvote questionnaire (75 policy questions) on 66 models; 48 real Swiss federal referenda on 9 flagship models, four languages, three information conditions.  *Scale:* 66 models on the questionnaire, 9 on the referenda. One administration per model-item: "All models were queried via the OpenRouter API with deterministic parameters: temperature=0.0, seed=42.".
  *Provenance:* read in full.
- **cen** — Cen S H, Ilyas A, Driss H, Park C, Hopkins A, Podimata C, Madry A, Large-Scale, Longitudinal Study of Large Language Models During the 2024 US Election Season, arXiv:2509.18446 [cs.CY], 22 September 2025.
  *Instrument:* bespoke structured survey, 12,638 questions -- 12,606 election questions across nine categories plus 32 non-election baseline questions from TriviaQA and MedQA; each non-baseline question x 21 prompt variations.  *Scale:* 12 models queried near-daily July-November 2024 across 100+ days; temperature 0 offline and 0.1 online; 128-token cap; approximately $40k of API spend.
  *Provenance:* read in full.
- **dominguezolmedo2024** — Dominguez-Olmedo R, Hardt M, Mendler-Dunner C, Questioning the Survey Responses of Large Language Models, NeurIPS 2024 (arXiv:2306.07951).
  *Instrument:* 25 multiple-choice questions from the 2019 American Community Survey; replicated on ATP, GAS/WVS and ANES.  *Scale:* 43 models, 110M to 175B parameters; responses read as renormalised next-token logits over choice labels rather than sampled text; all choice orderings evaluated where feasible, 5000 permutations cap, 50 for OpenAI models; ~1500 A100 GPU-hours.
  *Provenance:* read in full.
- **kamal2025** — Kamal S, Prakash L P Y, Rafiuddin S M, Rakib M, Sen A, Ray Choudhury S, A Detailed Factor Analysis for the Political Compass Test: Navigating Ideologies of Large Language Models, IJCNLP-AACL 2025 (short), pp. 284-303, anthology 2025.ijcnlp-short.25; preprint arXiv:2506.22493.
  *Instrument:* Political Compass Test (62 items, 4-point), plus 8 Values as a check.  *Scale:* 4 models all 4-bit quantised (Llama3-8B-Instruct, Mistral-7B-Instruct-v0.3, Falcon3-7B-Instruct, Gemma-3-4b-it) x 9 instances each (base + 8 LoRA fine-tunes) x 10 prompts x 8 decoding combinations; 2,693 PCT tests retained of an intended 2,880; plus Llama3.2-1B in full and 4-bit precision for A.5.
  *Provenance:* read in full.
- **liu2025** — Liu Y, Panwang Y, Gu C, 'Turning right'? An experimental study on the political value shift in large language models, Humanities and Social Sciences Communications 12:179, 2025, doi:10.1057/s41599-025-04465-z.
  *Instrument:* Political Compass, 62 items, forced 4-point numeric scale, scored onto economic and social axes on [-10, 10].  *Scale:* 4 static snapshots -- gpt-3.5-turbo-0613, gpt-3.5-turbo-1106, gpt-4-0613, gpt-4-1106-preview; 3 API accounts x 10 questionnaires = 30 runs per model, 7,440 item responses; temperature left at default (=1) deliberately; then bootstrap 100 and 1,000 replicates.
  *Provenance:* read in full.
- **naser2026** — M.Z. Naser, Tracing moral value drift across large language model generations and their societal implications, Technology in Society 87 (2026) 103431.
  *Instrument:* 107 moral probes (63 MFQ-adapted, 26 ethical dilemma, 7 value priority, 11 meta-ethical), 6-point Likert.  *Scale:* 14 model snapshots, 2 providers, 2 tiers, ~9500 calls, 10 trials/probe at T=0.
  *Provenance:* read in full.
- **messing2026** — Messing S, Hidden Measurement Error in LLM Pipelines Distorts Annotation, Evaluation, and Benchmarking, arXiv:2604.11581, April 2026 (rev. May 2026).
  *Instrument:* LLM evaluation and annotation pipelines generally.  *Scale:* benchmark and judge pipelines; MMLU and Elo-style match evaluation.
  *Provenance:* read in full.
- **motoki2024** — Motoki F, Pinho Neto V, Rodrigues V, More human than human: measuring ChatGPT political bias, Public Choice 198(1), 3-23, 2024, doi:10.1007/s11127-023-01097-2.
  *Instrument:* Political Compass, 62 items, forced 4-point scale coded 0-3, no neutral option; plus an author-written 62-item placebo battery and the IDRLabs Political Coordinates Test as robustness.  *Scale:* ONE model -- text-davinci-003, named only in the supplement -- at temperature 0.7; 100 rounds per condition per country, each round one call carrying all 62 items; bootstrap 1,000 replicates over the 100-answer sample.
  *Provenance:* read in full.
- **rottger2024** — Rottger, Hofmann, Pyatkin, Hinck, Kirk, Schutze, Hovy, Political Compass or Spinning Arrow? Towards More Meaningful Evaluations for Values and Opinions in Large Language Models, ACL 2024, pp. 15295-15311.
  *Instrument:* Political Compass Test.  *Scale:* 10 models (Llama2 7b/13b/70b chat, Mistral 7b Iv0.1/Iv0.2, Zephyr 7b beta, GPT-3.5 0613/1106, GPT-4 0613/1106), 62 PCT propositions, temperature 0 throughout, 5 forcing levels, 10 paraphrase templates, open-ended arm.
  *Provenance:* read in full.
- **rozado2024** — Rozado D, The political preferences of LLMs, PLoS ONE 19(7): e0306621, 2024, https://doi.org/10.1371/journal.pone.0306621.
  *Instrument:* 11 political orientation tests (Political Compass, Political Spectrum Quiz, World's Smallest Political Quiz, Political Typology, Political Coordinates, Eysenck, Ideologies, 8 Values, Nolan, iSideWith US and UK), 401 items total.  *Scale:* 24 conversational + 5 base + 3 self-finetuned models; 2,640 test administrations (11 tests x 10 trials x 24 models); 96,240 items; temperature 0.7, max 100 tokens; collected Dec 2023 - Jan 2024.
  *Provenance:* read in full.
- **sakhawat2026** — Sakhawat, Islam, Farhin, Raiyan, Mahmud, Hasan, Political Alignment in Large Language Models: A Multidimensional Audit of Psychometric Identity and Behavioral Bias, arXiv:2601.06194v1.
  *Instrument:* Political Compass (62 items), SapplyValues (46), 8 Values (70).  *Scale:* 26 models, 10 administrations per inventory per model, context cleared between runs, temperature 0.7 and top_p 1.0 ("All models are queried with temperature=0.7 and top_p=1.0, balancing determinism with natural language variability").
  *Provenance:* read in full.
- **sclar2024** — Sclar M, Choi Y, Tsvetkov Y, Suhr A, Quantifying Language Models' Sensitivity to Spurious Features in Prompt Design, or: How I learned to start worrying about prompt formatting, ICLR 2024 (arXiv:2310.11324).
  *Instrument:* few-shot benchmark tasks, not a values or political instrument.  *Scale:* several open LLMs; meaning-preserving prompt FORMAT variations.
  *Provenance:* partial.
- **tornberg2026** — Toernberg, Schimmel, Political Bias Audits of LLMs Capture Sycophancy to the Inferred Auditor, arXiv:2604.27633.
  *Instrument:* Political Compass Test, Pew Political Typology, and 1,540 partisan-benchmarked Pew American Trends Panel items; 30,990 responses.  *Scale:* 6 frontier models via the Requesty API gateway, April 2026. Main grid is "one response per item-model-condition cell", plus "three additional replicates at T=1.0 (27,000 additional calls), and one replicate at T=0 (greedy decoding; 9,000 calls)".
  *Provenance:* read in full.
- **aipolcom** — aipolcom.net, rolling public observatory.
  *Instrument:* politicalcompass.org 62 propositions, forced choice.  *Scale:* 57 models, 930 answer sets (729 model, 201 synthetic control), collection 2026-07-29 to 2026-08-29.
  *Provenance:* read in full.

Thirteen of the 14 are read in full. The remainder — sclar2024 — was consulted as abstract and PDF without the full text being read end to end, and no verdict in the controls table rests on more than that.
<!-- /GEN:references -->
