# No position, only consensus

**What political instruments actually measure in language models.**

Studies of political position in language models report how far a model moves under a
treatment. Almost none report how far it moves when nothing changes. This study administers 32
author-written forced-choice propositions, in 16 mirrored pairs, to a panel of frontier and
open-weight models, and measures the factors nobody claims are political: reprinting the items
in a different order, running the same prompt again, requantising the same weights, and
comparing two variants of one release. There is no language model anywhere in the scoring
path. Each answer is recorded as an item id and a chosen position, so no judge's lean can enter
a score.

- **Paper:** [`PAPER-below-the-floor.md`](PAPER-below-the-floor.md)
- **Instrument:** [`data/ratchet-battery.json`](data/ratchet-battery.json), shipped in full
- **Corpus:** [`runs/`](runs/), every record the paper's figures are computed from
- **Corrections:** [`CORRECTIONS.md`](CORRECTIONS.md). Read it before quoting anything here.
- **Licence:** MIT

---

## Results

### 1. The manipulation and the nuisance are the same size

Measured on the same sheets with the same estimator:

| | pairs | median \|effect\| | p90 | significant |
|---|---:|---:|---:|---:|
| the balance instruction (A − N) | 61 | 0.131 | 0.327 | 38 (62%) |
| reprinting the same items in a different order | 108 | 0.088 | 0.281 | 46 (43%) |

An instruction to answer in a balanced manner moves position by 1.5 times what a reordering
moves it, and its median sits below the ninetieth percentile of the reordering's own
distribution. Both effects are real and neither is large. Reordering alone is called
significant on 43% of pairs, which is the rate at which this estimator reports movement from a
factor carrying no information.

### 2. Refusal is elicited, not intrinsic

Across 64 models measured under both arms there are 88 refusals in 837 runs where the prompt
carries no directive, against 1284 runs where it carries one — 55 of those runs are refusals.
Of the models measured under both arms, 9 decline all 32 items without a directive; give those
same models a firm instruction and **8 of them stop**. The ninth declines under every condition
and is not a switch. Separately, **3 other models decline only when told to commit**. A refusal
rate reported as a property of a model is substantially a property of the sentence the
researcher wrote.

### 3. A standard control silently deletes data

Shuffling presentation order while each item keeps its own id as its printed number produces a
non-monotonically numbered sheet, and some models skip lines. The sheet is not refused, not
truncated, well inside its token budget, and looks complete, so neither a refusal table nor an
aggregate parse rate can see the loss. On local builds, 15 of 102 as-is sheets come back
incomplete against 1 of 100 renumbered `1..32` (Fisher exact, one-sided, p = 1.8 × 10⁻⁴). The
serving backend moderates it: one model under an identical protocol loses 7 of 23 as-is sheets
on one provider and 1 of 23 on another (p = 0.0235). Across both backends and all eight pinned
models the renumbered arm has lost 0 sheets in 216. (`scripts/omission_arms.py`)

The study's own main wave was collected across that change and dropped 104 partial sheets. All
34 affected cells were re-collected renumbered under a pre-registration, 369 sheets one for one,
and no floor moves outside its published interval. (`scripts/partials_sensitivity.py`,
[`prereg/PREREG-2026-09-24-partials-renumbered.md`](prereg/PREREG-2026-09-24-partials-renumbered.md))

### And one exploratory result

The panel agrees on the contested normative propositions in the bank 97.1% of the time,
against 99.0% on documented matters of record, and uses its strongest available answer more
often on the contested claims than on the documented ones (42.5% against 36.6%). The paper
reports this in §3b, marks it exploratory and outside the corrected family of tests, and states
its main limit: this bank cannot separate a consensus from an item that is not really arguable.

---

## The rule this is for

The paper's recommendation (§8), five lines in a methods section. None of it costs additional
calls.

1. **Vary presentation order and report the change rate** as an item-level magnitude.
2. **Include one same-version pair per model family** and report what it produces as a
   distribution.
3. **Convert the larger of those two into a detection limit** and report every effect against
   it. An effect below the limit is one the design could not have seen, not a null.
4. **Retain non-responses and classify them by cause**, and report per-item completeness.
5. **Renumber shuffled sheets `1..N` and pin the serving backend.**

---

## The floors

What the instrument does when nothing that should matter has changed. Each row is pairs of
administrations differing in one factor, in the unit the literature reports.

<!-- GEN:floors -- generated by scripts/floor_table.py --markdown; do not edit -->
| factor | n pairs | side-flip med / p90 / max | p90 95% CI | endpoint med / p90 / max |
|---|---:|---|---|---|
| prompt condition A->D, one sitting, local open-weight | 17 | 3 / 9 / 13 | [3, 13] | 8 / 14 / 16 |
| requantisation | 16 | 4 / 8 / 15 | [4, 15] | 3 / 10 / 15 |
| presentation order, one sitting, local open-weight | 23 | 3 / 6 / 11 | [3, 11] | 3 / 16 / 18 |
| presentation order | 94 | 1 / 5 / 12 | [3, 7] | 1 / 7 / 13 |
| prompt condition A->D, one sitting | 61 | 1 / 4 / 13 | [3, 9] | 9 / 18 / 27 |
| run-to-run replicate | 6240 | 0 / 3 / 16 | [2, 3] | 2 / 11 / 32 |
| presentation order, one sitting | 107 | 1 / 3 / 11 | [1, 5] | 3 / 12 / 30 |
| prompt condition A->D, one sitting, frontier API | 44 | 0 / 2 / 11 | [1, 4] | 9 / 21 / 27 |
| same-version variants | 24 | 1 / 1 / 2 | [0, 2] | 5 / 11 / 19 |
| presentation order, one sitting, frontier API | 84 | 0 / 1 / 2 | [1, 1] | 3 / 11 / 30 |
| modal sampling error | 576 | 0 / 1 / 16 | not a pair arm | 1 / 6 / 32 |

**requantisation excludes `mistral-7b`:** gated ELIGIBLE but contributed no pair -- every condition lost one arm to an invalid run
<!-- /GEN:floors -->

Read the last row first. `modal sampling error` is not a factor but the noise in the statistic
itself: two bootstrap modals of the same cell. A row whose p90 is not clearly above it is
reporting the instrument, not an effect.

Split by model class, the two largest factors behave differently by generation:

<!-- GEN:class_split -- python scripts/gen_readme.py -->
| on this class | presentation order, one sitting | manipulation A->D, one sitting |
|---|---:|---:|
| hosted over an API — 2025-26, 28 of 51 open-weight | p90 **1** (84 pairs) | p90 **2** (44 pairs) |
| run locally at Q4 — 2024-generation 7-14B | p90 **6** (23 pairs) | p90 **9** (17 pairs) |
<!-- /GEN:class_split -->

**Detection limits.** A floor says what a nuisance produces, not what the instrument can
resolve. `scripts/power.py` converts each null into the smallest real effect that would clear
it often enough to be caught. It puts the minimum detectable effect at **7 items** of 32 against
presentation order pooled across classes, and **3** against the same-version floor. Two
variants of one release differ by **p90 1** side flip of 32 over 24 pairs, which is below what
the instrument can resolve: a bound, not a measurement.

---

## The field, and this study

Fourteen published studies are scored against the same methodological controls in
[`PRIOR-WORK-CORRECTIONS.md`](PRIOR-WORK-CORRECTIONS.md). Not one reports what two variants of
the same model do to the same instrument as a distribution that an observed shift could be
scored against, and only two report a detection limit outright. Most of those studies document
their methods well enough that the audit was possible at all; the floors do not show their
effects are absent, only that they cannot be told apart from factors held fixed, and the remedy
is a re-analysis rather than a retraction.

The same audit is applied to this study. **This study has corrected **30** claims of its own**,
each recorded in [`CORRECTIONS.md`](CORRECTIONS.md) with what was claimed, when, and what
replaced it. Every withdrawn claim is registered in
[`data/withdrawals.json`](data/withdrawals.json), and the build fails if one is asserted again
on any surface.

---

## Reproduce it

```bash
pip install -r requirements.txt
python scripts/floor_table.py --markdown   # the floors table above
python scripts/power.py                    # detection limits per null
python scripts/key_numbers.py --check      # every load-bearing sentence in the paper, against runs/
python scripts/gen_readme.py --check       # this file's generated tables
python scripts/release_check.py            # the release checklist, run rather than asserted
```

No API key is needed to verify anything; one is needed only to collect. The gate set runs in CI
on every push ([`.github/workflows/verify.yml`](.github/workflows/verify.yml)). Numbers typed in
prose are held to the data by `key_numbers.py`, and the generated tables above are regenerated
from `runs/`, so a disagreement between the two is a bug worth an issue.

### The data

- **`runs/`** is the present study: every answer sheet on the 32-item battery, one JSON line per
  administration, with the prompt, the raw response, the parsed answers keyed by item id, the
  serving provider and the validity verdict. The main wave's figures are computed
  across 3,897 runs, 65 models and 23 vendor keys; the omission, paraphrase, rung-2 and
  re-collection arms are separate directories, each declared in or out of the refusal panel.
- **`data/`** holds the instrument, the declarations the analysis reads (which runs form the
  refusal panel, which losses are declared, which claims are withdrawn), and every earlier corpus,
  including the May 2026 judge-scored study.
- Each root carries a generated `README.md` and a `PROVENANCE.json` giving every run's status,
  so a withdrawn arm is labelled on disk and not only in prose.
  [`DATA-DICTIONARY.md`](DATA-DICTIONARY.md) documents every field;
  [`PROTOCOL-DEVIATIONS.md`](PROTOCOL-DEVIATIONS.md) records what was planned against what was
  done.
- The reproduction audit held nothing back: 0 run records had their text withheld from this
  repository.

### What is not shipped

| not shipped | why | what cannot be recomputed here |
|---|---|---|
| `2026-09-15-g0dm0d3-decomposition` | a pipeline-rung arm of the retired design | The decomposition run is NOT in this repository. `pipeline_decomposition.py` exits 2, so the B-Godmode / B-Autotune split cannot be recomputed from shipped data |
| `refusal-ablation`, `mask-gradient` | they carry verbatim XSTest prompts, a third party's text | the refusal dose series; `RESULTS-2026-09-19-dose-response.md`, named in the paper's provenance table, stays in the private tree for the same reason |
| eight smoke and probe directories | one sheet per model, collected to price a run or find what answers | nothing; they are outside the refusal panel by rule |

No figure in the paper depends on an absent run. If you find one that does, that is a bug and
an issue is the right response.

---

## Repository layout

Every file at the top of this repository is listed here, in one of three groups.
`tests/test_readme_maps_every_top_level_doc.py` fails if one is added without being placed.

**The study — what is being published.**

| path | what it is |
|---|---|
| `PAPER-below-the-floor.md` | the paper |
| `CORRECTIONS.md` | every claim corrected, with what replaced it — read before quoting |
| `data/ratchet-battery.json` | the instrument, 32 items in 16 mirrored pairs |
| `ITEM-READ-2026-09-16-ratchet-battery.md` | the author's signed read of those 32 items, which gated collection |
| `runs/` | every answer sheet of the present study, keyed by item id |
| `data/` | the instrument, the declarations the analysis reads, and every earlier corpus |
| `scripts/` | collection, analysis, and every gate |
| `tests/` | the regressions behind the gates |
| `SCRIPTS.md` | what each script is for, generated from their docstrings |
| `DATA-DICTIONARY.md` | every record field, generated from the corpus |
| `PRIOR-WORK-CORRECTIONS.md` | the controls audit of other studies |
| `PROTOCOL-DEVIATIONS.md` | what was planned against what was done, generated |
| `prereg/` | the pre-registrations, each committed before its data |
| `RELEASE-2026-09-07.md` | the release checklist `scripts/release_check.py` runs; its arm inventory is generated |
| `CITATION.cff`, `.zenodo.json` | the citation record a DOI mints from |
| `VERSIONING.md` | releases are dated, not numbered |
| `MANIFEST.json` | the export manifest: instrument and corpus hashes |
| `LICENSE`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` | the terms |
| `requirements.txt`, `requirements-weightrung.txt`, `pytest.ini`, `conftest.py` | to run it |

**The record — how the study got here.** Process, not findings; nothing in the paper depends
on these.

| path | what it is |
|---|---|
| `LEARNINGS.md` | rules earned from defects that actually happened here, each with its receipt |
| `LESSONS.md` | dead ends, reversals, and what broke in the machinery |
| `CHECKS-ANY-STUDY-CAN-RUN.md` | six checks on data a study already has; its worked examples come from the retired design |
| `CORRECTIONS-2026-09-08.md`, `CORRECTIONS-2026-09-17-power.md`, `corrections/` | dated correction records, kept where they were published |
| `CORPUS-MAP-2026-09-14.md` | what each run of the earlier corpus is for, after its repair |
| `ADVERSARIAL-REVIEW.md` | the May 2026 self-review; its verdicts are dated and several are superseded |
| `results/` | dated results documents |
| `skills/`, `agents/` | the procedures the study was run by |

**The retired design — marked HISTORICAL at the top of each.** The free-text, judge-scored study
that ran until 2026-09-16 (see the section below).

| path | what it is |
|---|---|
| `FINDINGS.md` | what that design had found by 2026-09-13 |
| `DEVELOPER.md` | how that design's pipeline works |
| `protocol/` | that design's questions, rubric and aggregation rules |
| `ROADMAP.md` | what was planned next, on that design |
| `JUDGEMENT-TOOL-PLAN.md`, `RUBRIC-SCORES.md` | the judge-method plan and its pre-registration |
| `RESULTS-2026-09-14-rung2-transform-audit.md`, `RESULTS-2026-09-15-rung2-decomposed.md` | the proxy-based pipeline rung, and why it was abandoned |
| `withdrawn/` | retired arms and instruments, kept rather than deleted |

---

## The design this replaced

Until 2026-09-16 this study used free-text answers to a 62-proposition public questionnaire,
rated 1–5 by a panel of model judges. It was retired for three reasons. The questionnaire was a
third party's licensed text and could not be republished, which a study arguing that the field
should publish what it measures could not accept. Its headline claim, that hedging is the bias
signature, restated the rubric: a score of 3 is "does not commit", and the hedge lexicon
measures non-commitment. And its counts out of 62 are not comparable to counts out of this
battery's 32 items; no rescaling converts one into the other.

Two measurements from that design are kept because they are the argument for this one. Scoring
free text with model judges puts the judges' lean in the result:
our judges spanned 0.3108 points between the most and least institution-skeptical of them,
on the same responses. And the elicitation-pipeline rung produced no effect that survived its
own control: all 8 intervals span zero. Its re-collection on the battery, through this study's own transport, reached the same
verdict. The retired material is in `withdrawn/` and the documents marked HISTORICAL above.

---

## Cite

[`CITATION.cff`](CITATION.cff) is the citation record, and the next release mints a DOI from it
through [`.zenodo.json`](.zenodo.json). No DOI is live for this study today: an earlier release
was archived to Zenodo under a withdrawn title before this repository carried a citation record,
and that record was deleted on 2026-09-22 and now resolves to a tombstone.

## Licence

**MIT**, for code, run records and documents alike. See [`LICENSE`](LICENSE). Two carve-outs,
both matters of ownership rather than preference:

- **The retired 62 propositions** are a third party's licensed work and are not in this
  repository at all. `scripts/check_corpus.py` gates their absence on every release.
- **Model outputs.** The response text inside the run records was produced by each vendor's
  model and their terms govern it; MIT covers the corpus as assembled, scored and structured
  here.
