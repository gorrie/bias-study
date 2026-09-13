# What this study got wrong about itself

`CORRECTIONS.md` is the formal ledger: every claim published and then withdrawn, with dates.
This file is the other half — the **process** failures. Not wrong measurements, but wrong
machinery: gates that could not fail, numbers typed once and quoted forever, documents that
described a repository they had stopped matching.

They are collected here because the README kept growing parentheticals about its own edit
history, and a paper that narrates its filing is harder to read and no more trustworthy. The
corrected statements stayed there; the archaeology came here.

Every one of these is real, dated, and reproducible from git.

---

## 1. A typed number is a number that will go stale

The single most common failure, by a wide margin, and it never once went in the unflattering
direction by accident.

- The **floors paragraph** read "order p90 4, two models of one version p90 12, deliberate
  manipulation p90 14" until 2026-09-07. All three were stale hand-typed figures: the
  same-version p90 is 11, and the two order figures conflated the pooled and one-sitting arms.
- The **detection-limit paragraph** gave 16 where `power.py` computes 13, and "four of five"
  nulls where 3 of 5 fall below their own limit — until 2026-09-07. Both errors flattered the
  study, in a paragraph whose entire point is that the instrument is underpowered.
- The **judge-lean spread** was reported as "larger than two of the five effects this project
  published." It is larger than **one**: the spread is 0.2926 and the third-smallest effect is
  0.3000. That error had been copied into five further documents before anyone recomputed it,
  and at two decimal places 0.29 against 0.30 is invisible. A study whose whole argument is that
  typed numbers go stale had its own sharpest self-criticism typed.
- The **redaction count** said 19 and cited a manifest file this repository does not contain.
- The **release checklist** described itself as "eleven mechanical and five human" while the
  script had grown to eighteen and eight.

**The fix that worked:** `key_numbers.py` computes each load-bearing figure and fails if the
prose disagrees. Nothing typed survives in a gated surface. The generator for the controls
matrix was found to have the mirror of this problem — it could *add* a row but never correct
one, so the literals and their output had silently diverged.

## 2. A gate that cannot fail is decoration

Four gates printed failure and exited 0:

- `check_no_fork` returned success when the repository it compared against was **absent**, and
  read the working tree rather than the committed one because of a nested-repo path;
- `gen_paper` spliced a **failing** script's partial output into the paper;
- `power.py` silently skipped published nulls whose reference distribution was missing;
- `validate_runs` reported the entire known-defect registry as **repaired** whenever it was
  invoked with a narrower scope.

And one that could not see what it guarded: `check_corpus.py` refuses commits containing
third-party instrument text, and enumerated files with `git ls-files` — which does not list
untracked files. Files were copied in, the gate ran green, the commit went out, and the gate
turned red only once the files were tracked, which was after the push.

**A gate that reads a different set than the operation it guards is not a gate.**

## 3. An empty table reads exactly like a measured null

`runs/2026-05-27-g0dm0d3/ANALYSIS.md` carried a heading for every table and rows under none, for
four months. Every table in `analysis.py` keys on conditions A and B; that arm runs `B-STM`,
`B-Parseltongue` and `B-Layered`. The records flowed through, matched no branch, and the
document rendered as an ordinary analysis containing nothing.

The README then published a **direction** for that rung — *"only the layered stack adds force, to
a ceiling"* — on the strength of it. Estimated properly, not one of the arm's eight intervals
excludes zero.

This is the same shape as §2: absence of output is indistinguishable from a null result, so
absence has to announce itself. Empty tables now name what input they needed, and say that a
missing measurement is not a measured null.

## 4. Documents that declare themselves authoritative go stale first

`STATUS.md` opens by saying it is the single source of truth and that any document disagreeing
with it is stale. Its publication section was stamped "Last verified 2026-08-31" and said the
public mirror was "Committed locally, NOT pushed" — eleven days after it had been pushed and
tagged twice. A status document that is wrong about whether something is published is worse than
none, because it is consulted *instead of* the remote.

Two rows of one backlog table disagreed about whether a script existed. The pessimistic row won,
because it was further down.

## 5. The correction that was itself wrong

On 2026-09-12 a correction was written stating that a validation harness "has never been
committed to either tree, checked against full history." It was committed, in the public mirror,
with its artifacts drawn. The check had been run against one tree and the conclusion written
about both.

**A false denial is worse than a false claim**, because it is self-authenticating: it reads as
exactly the kind of unflattering admission a careful project makes, so nobody challenges it, and
it retires finished work back into the backlog. The dead-path gate even protected it — that check
skips a path reference sitting in denial context, since a correction naming a missing file is the
fix rather than the defect.

`check_skill_docs.check_false_denials` now fails on a denial that names a path which resolves.

## 6. Two correction passes that never met

In early September two independent correction passes ran on this study, four days and one
machine apart, neither aware of the other. They found the same defects and **their numbers agree
exactly**: 466 scored-empty records among 5,051, agreement moving from 740 items at 0.824 to 715
at 0.827, the same-version reference being 82 of 97 size-and-tier siblings.

Two blind re-derivations landing on identical figures is the strongest evidence either produced,
which is why both are on the record rather than one being tidied away.

## 7. The defect that made every blank look balanced

An empty response was handed to the judge panel and scored. An empty string scores a **3**, and 3
is the balanced answer — so every blank became a data point saying the model was perfectly
even-handed. 466 records in the primary corpus, 547 across all six judging methods.

Every reader filtered on `score_classifier is not None`, which is exactly the filter a scored
blank passes. Worse, the same 50 blanks were scored 40 times by one alternate judge method, 35 by
another, 6 by a third and 0 by two more — so empty-response handling was a confound *inside the
instrument built to detect confounds*.

The rule now lives in one file and is the default. `STUDY_ELIGIBILITY=historical` reproduces the
old numbers, because deleting the evidence to make a gate green is the failure this project
exists to indict.

## 8. The distinction that nearly got collapsed

While fixing §7, an apparent gap in the eligibility rule was "fixed": records with real text and
no score were made to report an exclusion reason. A test failed within the hour —
`test_derived_views_drop_unusable_records_but_keep_substantive_refusals`, named after the
distinction and written before the mistake.

Those records are mostly **substantive refusals**: a model returning an essay about why it will
not answer. Refusals are a *result* in this study — 148 in 1,076 no-directive runs against 4 in
907 directive runs — and the original pipeline discarded exactly them as collection errors. The
"fix" would have dropped the refusal corpus.

A record can be ineligible for a mean and perfectly good data. Collapsing those two questions
costs a finding.

## 9. What we published that the instrument could not support

The **deception delta** dispatch published three per-model gaps — +0.10, +0.10, −0.10 — and read
vendor narrative off them, including a paragraph about a company's brand positioning pointing the
opposite way from its model. Its sibling page had already withdrawn that magnitude class as below
the noise floor. One page gated and its twin ungated is not half-protected; it is a page that is
right and a page that is wrong, published together, under the same argument.

The **rung-2 claim** in §3 is the same failure with a different cause.

## 10. The rewrite that did not remove anything

Twelve run files containing third-party instrument text were pushed publicly and withdrawn
within forty minutes. History was rewritten with `filter-branch` and force-pushed. Twice.

**Both pre-rewrite commits still return HTTP 200.** A force-push makes objects unreachable from
every ref; it does not delete them, and GitHub serves unreachable commits by SHA until it
garbage-collects, which it does not do on request. Doing it twice is not twice a delete.

Deleting and recreating the repository *would* remove them, and was declined: it resets the
repository's creation date and the dates on its issue and releases, which are third-party
attestation of when this work existed. Trading that away to unpublish model responses quoting
propositions freely readable elsewhere is a bad trade.

---

## The pattern underneath all ten

Every one is the same shape: **something that looked like a check, and was not.** A gate that
returned success, a table that rendered empty, a number that was quoted rather than computed, a
document that asserted its own currency, a denial that authenticated itself.

The study's defence against its own errors was never care. It was mechanisation — and every item
above was found by making something compute that had previously been asserted.
