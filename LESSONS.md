# Dead ends, reversals, and what the machinery got wrong

Four months, 226 commits, 36 results documents. `CORRECTIONS.md` is the formal ledger of claims
published and withdrawn, and `PRIOR-WORK-CORRECTIONS.md` is what twelve other studies leave
unbounded. This file is the third thing: **what was tried and abandoned, what was reversed, and
what broke in the machinery rather than the measurement.**

It exists because the README had grown a parenthetical for every edit in its own history, and a
paper that narrates its filing is harder to read and no more trustworthy. The corrected
statements stayed there. The archaeology is here, where someone can learn from it.

Everything below is dated and reproducible from git.

---

# Part 1 — Methods tried and abandoned

## Logit scoring: feasible, and it failed its own pre-registered check

`RELEASE-v2.md` called it *"the one thing v2 should still add, and it is free"* — score the
forced-choice instrument from token logprobs rather than by parsing prose, and four whole classes
of failure disappear: models producing no valid answer sheet, budget exhaustion, 28.2% of
condition-A runs invalid, tokenizer garbage.

It works. It was built, run on local models at zero API cost, and **it fails the agreement
criterion that was written down before it ran.** The labels are not separable at token 1, and 48
of 62 positions change when the legend is reversed — which means the probe is reading position,
not preference.

A free method that removes your worst data problems and fails its own pre-registered check is the
hardest kind of result to accept. It is in `RESULTS-2026-09-07-logit-scoring-fails-agreement.md`
rather than in the paper.

## Constrained decoding: replicates, but not when batched

Make an invalid answer ungenerable and the parsing problem vanishes by construction. It
replicates — and asking for all 62 answers in one array does not behave like asking for them
singly. The batch size is a condition, not an implementation detail, which disqualified the
whole-sheet form as an arm while keeping the singly-asked form.

That document was **corrected three times on the day it was written**, every time before
publication, and all three superseded readings are kept in it rather than deleted. Getting a
result wrong three times in eight hours and keeping the sequence is a better record than getting
it right once, because the sequence is what shows the criterion was doing the work.

## The grammar arm, the dose series, five alternate judge panels

Each was built, each ran, and each is reported at the standing its evidence supports rather than
the standing it was proposed at. The dose series has a coherence cliff: layered force degrades
output past a functionality ceiling, and a broken response must never score as maximum
skepticism.

## Evidence concordance: an axis-free measure, cut down by its own control

An outcome measure that avoids political axes entirely, built to sidestep the objection that the
instrument's axes are somebody else's. The control it was given cut it down. Reported in
`RESULTS-2026-08-29-evidence-concordance.md` as what it is.

## The newest frontier will not take the test

Six models released between 2026-08-26 and 2026-09-04, same 62 propositions, same four arms, same
temperature and seed, selected on recency rather than outcome. They decline. That is not a
failure of the collection; it is a finding about where this instrument's coverage ends, and it is
the reason a "modern frontier panel" was scored **D1 = 1** in the pre-registered rubric — judges
that would refuse the instrument are not neutral raters of it.

---

# Part 2 — Reversals

## The withdrawal that was itself wrong

On 2026-08-28 Evidence 1 — that abliteration demonstrably rewrote political responses — was
withdrawn. The reasoning was that two runs of the same model at temperature 0.7 produce a word-set
Jaccard of 0.340, and the between-arm figure of 0.276–0.339 sits inside that band.

**The logic was sound and the baseline was wrong.** Reinstated 2026-08-30, found by opening
`ADVERSARIAL-REVIEW.md` — a document this project had been citing, repeatedly, without anyone
having read it.

Withdrawing a claim is not automatically the careful move. A withdrawal is a claim.

## The weight rung did not survive its own control

`RESULTS-2026-08-30-weight-rung-matched.md` asked how many side-flips **requantisation alone**
produces, and committed to claiming nothing until that number existed. The number arrived the
same day: the effect sits inside the quantisation band. Same weights, Q4_0 against Q8_0, same
instrument, same decoding, no ablation.

## Drift did not replicate at scale

An early drift result had an underpowered reference. At scale it does not reproduce. Both are on
the record.

## The largest effect in this study is which model you ask

And even that carries an interpretation correction from the following day: the between-model
median (5) **equals** the within-model p90 (5) rather than exceeding it, and the estimators
differ, so it cannot prove a model-specific political position independent of the questionnaire.
The table stays descriptive.

## One model of thirty-one can carry a claim

Every floor in this study pools per-model behaviour away, and that pooling hid the most
consequential fact in the corpus. The per-model cards stop hiding it.

---

# Part 3 — The machinery

## Three published floors were a property of the filesystem

`modal()` broke ties with `Counter.most_common`, which resolves **by insertion order** — and
insertion order was the order the loader walked the directory. Three published floors were
therefore a property of the filesystem. Found by a CI failure that did not reproduce locally.

## The estimator with no denominator

`RESULTS-2026-09-06-modal-resolution-and-the-inversion.md`: the comparison inverts by model
generation once the estimator has one.

## The bug fix that went into the mirror and not the working copy

Two trees had drifted into a maintained pair and diverged at the **statistics** layer: the
private `ci_analysis.py` still seeded one global RNG, so bootstrap intervals depended on the order
run-dates were passed. Five of 22 CI bounds moved under reversal. No verdict flipped, which was
luck rather than safety. The analysis layer now has one implementation and the other tree shims
to it.

## Four gates that printed failure and exited 0

`check_no_fork` returned success when the repository it compared against was absent, and read the
working tree rather than the committed one. `gen_paper` spliced a failing script's partial output
into the paper. `power.py` silently skipped published nulls whose reference was missing.
`validate_runs` reported the entire known-defect registry as repaired whenever it was scoped.

## The gate that could not see what it guarded

`check_corpus.py` refuses commits containing third-party instrument text, and enumerated files
with `git ls-files`, which does not list untracked files. Files were copied in, the gate ran
green, the commit went out, and the gate turned red only once the files were tracked — after the
push. **A gate that reads a different set than the operation it guards is not a gate.**

## Every blank scored a 3, and 3 is the balanced answer

466 records in the primary corpus and 547 across all six judging methods carried a classifier
score derived from an **empty response**. Every reader filtered on `score_classifier is not None`,
which is exactly the filter a scored blank passes. Worse, the same 50 blanks were scored 40 times
by one alternate judge method, 35 by another, 6 by a third and 0 by two more — so empty-response
handling was a confound *inside the instrument built to detect confounds*.

The May study was also scored on **truncated** responses, and one model on empty ones.

## An empty table reads exactly like a measured null

`runs/2026-05-27-g0dm0d3/ANALYSIS.md` had a heading for every table and rows under none, for four
months, because every table keys on conditions A and B and that arm runs `B-STM`,
`B-Parseltongue`, `B-Layered`. The README then published a **direction** for that rung from it.
Estimated properly, not one of the arm's eight intervals excludes zero.

Absence of output is indistinguishable from a null result, so absence has to announce itself.

## A typed number is a number that will go stale

The floors paragraph, the detection limit, the redaction count, the release checklist split — all
typed, all stale, and the errors never once landed in the unflattering direction by accident. The
judge-lean spread was published as "larger than two of the five effects"; it is larger than
**one**, and at two decimals 0.29 against 0.30 is invisible. That error had been copied into five
documents before anyone recomputed it.

The controls-matrix generator had the mirror of this problem: it could *add* a row but never
correct one, so its literals and its output silently diverged.

## The correction that was itself false

A correction was written stating a validation harness "has never been committed to either tree,
checked against full history." It was committed, with its artifacts drawn. The check had been run
against one tree and the conclusion written about both.

**A false denial is worse than a false claim**, because it is self-authenticating: it reads as the
kind of unflattering admission a careful project makes, so nobody challenges it, and it retires
finished work back into the backlog. The dead-path gate even protected it, because that check
skips a reference sitting in denial context.

## The distinction that nearly got collapsed

While fixing the empty-response defect, an apparent gap in the eligibility rule was "fixed": records
with real text and no score were made to report an exclusion reason. A test failed within the
hour, named after the distinction and written before the mistake. Those records are mostly
**substantive refusals** — and refusals are a *result* here, 148 in 1,076 no-directive runs
against 4 in 907. The fix would have dropped the refusal corpus.

A record can be ineligible for a mean and perfectly good data.

## The rewrite that removed nothing

Twelve run files containing third-party instrument text were published and withdrawn within forty
minutes. History was rewritten with `filter-branch` and force-pushed. Twice. **Both pre-rewrite
commits still return HTTP 200.** A force-push makes objects unreachable from every ref; it does
not delete them, and doing it twice is not twice a delete.

---

# Part 4 — What we got wrong about other people

`PRIOR-WORK-CORRECTIONS.md` audits twelve studies against fourteen controls. Reading them in full
cost this project four claims, every one in the same direction — ours:

| we claimed | what the paper actually says |
|---|---|
| nothing in this literature computes a floor | Röttger reported paraphrase instability at 14 and 23 items of 62, in 2024, and urged the field to estimate it |
| no study reports a detection limit | Domínguez-Olmedo report power ≥ 0.98 at effect size 0.1 |
| we complement Kamal on quantisation | their appendix reverses sign between precisions; we are the only measurement |
| we invert Cen's vendor refusal ordering | their introduction and their results section disagree with each other; withdrawn |

One entry was corrected again on 2026-09-06 for imputing a motive to a rationale the author had
openly stated. Rozado excludes same-version siblings **on purpose and says so**, in favour of
variety across model families. The consequence still stands — the comparison capable of bounding
model-to-model difference is the one left out — but that is a consequence, not a motive.

**The standard: no verdict about another study rests on our own notes.** `controls_audit.py
--strict` enforces it, and the four claims above are what happened the first time it was applied.

---

# The pattern underneath all of it

Every machinery failure has the same shape: **something that looked like a check, and was not.** A
gate that returned success, a table that rendered empty, a number quoted rather than computed, a
document asserting its own currency, a denial that authenticated itself.

The defence was never care. It was mechanisation. Every item in Part 3 was found by making
something compute that had previously been asserted — and the ones in Part 1 and Part 2 were
found by writing the criterion down before running the method, then honouring it when it came
back wrong.
