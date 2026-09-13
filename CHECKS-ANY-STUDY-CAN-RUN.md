# Six checks any LLM-bias study can run on data it already has

Every defect below was found **in this study's own data**, by us, after publication. None of it
is hypothetical and none of it required new collection. Each check is arithmetic on records
already on disk, each one invalidated something we had written down, and each is cheap enough
that there is no good reason not to run it.

We are not claiming other people's conclusions are wrong. We are claiming these checks are
rarely run, that we know what happened when we ran them here, and that the checks are reusable.
Where a count about other studies appears below it comes from `scripts/controls_audit.py`, a
14-control matrix over 12 published studies in which every "does not run it" is sourced from a
paper actually read — `--strict` fails the build otherwise.

---

## 1. Are you scoring blank responses?

**The check.** Count records that carry a score and an empty response body.

```bash
python scripts/audit_response_quality.py --check
```

**What we found.** 466 of 5,051 primary scored records carried a classifier score derived from
an empty string, and 561 were unusable in total. Every one was recorded `ok=true`: the API call
succeeded and returned nothing, usually a model spending its whole budget on reasoning tokens.
No reader in our pipeline filtered them. `openai/gpt-5` was 287 of 310 empty — 93%, so its
published delta was pairs of blanks compared to each other — and `google/gemma-2-9b-it` was
**60 of 60**. Every record for that model, scored, with nothing in it.

**Why it hides.** A successful call returning no text is not an error anywhere in the stack. The
judge reads `""`, returns a number, and that number is indistinguishable downstream from a real
one. Aggregate counts do not shrink; they just quietly stop meaning anything.

**What it cost us.** Nothing, in the end — we re-ran everything under an exclusion rule and no
significance verdict changed. That is the honest result and it is the reason to run the check
rather than a reason to skip it: we could not have known that without doing it.

---

## 2. Is your "drift across versions" actually across versions?

**The check.** Group your measurements by version label and count DISTINCT versions per family,
not rows. Then ask whether your arc statistic compares version aggregates or two arbitrary runs.

**What we found.** Our vendor arcs computed `deltas[-1] - deltas[0]` — the last measurement row
minus the first — and printed it as "delta from oldest to newest". Rows are `(version, run)`
pairs. **Four of our twelve model families had exactly one distinct version, and all four
published an arc direction.** Our "xai-grok, 8 versions" was one model measured eight times; the
arc was one run minus another run of the same model. Six of twelve families changed verdict when
fixed, and one published direction was withdrawn outright.

**The field number.** 10 of 12 studies do not report a longitudinal measurement at all, and a
cross-section of successive versions measured on one date is not one however many versions it
spans.

---

## 3. What does your instrument do when nothing changes?

**The check.** Measure the same model, same prompt, same settings, twice. Then measure
same-version variants — size siblings, tier siblings, dated snapshots, quantisations. Report the
DISTRIBUTION: median and an upper percentile, over many pairs, so a single observed transition
can be scored against it.

**What we found.** Our own repeat measurements of a single version span up to 0.90 on the same
scale where we were calling movements of ±0.2 directional. The threshold sat an order of
magnitude below the noise and nothing in the output said so. Three of our thirteen vendor arcs
survive once each is compared against its own within-version spread.

**The field number.** **Zero of twelve studies report a same-version null as a distribution**
(10 no, 2 not applicable). Six report no same-version point control of any kind. And **7 of 12
have the pairs for one sitting inside their own design** — tier ladders, dated snapshots of one
name — and read them as drift transitions carrying effect sizes rather than as the baseline they
are. We did exactly this too, which is check 2.

---

## 4. Does your serving stack move the answer?

**The check.** Re-quantise or re-serve the identical weights, change nothing else, and measure.

**What we found.** Requantising the same weights Q4→Q8, with no intervention at all, moves 2–10
items of 62 (median 3). Two of our three ablation pairs sat inside that band. A claim we had
published about weights and stance was withdrawn on this basis; a per-model quantisation null is
now a required control here and did not exist in this project before 2026-08-30.

**The field number.** 7 of 12 do not hold or measure serving-stack variation; 2 are partial.

---

## 5. If a model scores your outputs, what is the scorer's own lean?

**The check.** Report the scoring layer's deviation as a magnitude — per-judge, against each
other and against a mechanical baseline. Agreement between judges is not validity: judges that
share a lineage share a lean, and high agreement measures the shared lineage.

**What we found, twice.**

- Our judge panel agrees at 0.827 exact over 715 items. That number says nothing about whether
  the construct is real, and we published it as though it did until it was narrowed.
- Separately, on a hand-read validation of 42 spans: **two blind readers agreed with each other
  at 0.952, and each agreed with the non-blind reader — the agent that built the detector — at
  only 0.738.** Identical spans. The gap is about who is reading. The direction (the non-blind
  reader crediting its own detector's hits) is what you would predict and we did NOT establish
  it: sign test n=9, p=0.18. The agreement gap is the finding; the story about why is not.

**The field number.** Of the studies using a model in the scoring path, 4 report no judge lean
and 1 is partial. On the narrower question of a subject also scoring itself, three of twelve
have the overlap and it is establishable from each paper's own text because each names both
roles: in Röttger et al. 2024 GPT-4 is among the ten subject models and GPT-4 0125 is the
open-ended classifier; in Rozado 2024 gpt-3.5-turbo is both one of the 24 subjects and the
stance detector; in Cen et al. 2025 GPT-4o is a queried subject and GPT-4o-mini is the scorer —
same family rather than the same model. None of them is hiding it. None of them reports the
scoring layer's lean either, which is the part that would tell you whether it matters.

---

## 6. Does your gate actually fail?

**The check.** Force a failure and confirm a nonzero exit. Do it for every gate.

**What we found.** Our release checklist printed failures and exited 0 — "all eleven pass" had
never been verified, because the only way to exercise the exit code was a 45-minute run nobody
did. Our fork checker returned success when the thing it compares against was absent, and read
the working tree rather than the committed state because of a path bug. Our paper generator
spliced a failing script's partial output into the paper. Our registry-rot detector reported
every known defect as repaired whenever it was scoped to a subset.

**Why this belongs in a methods list.** A gate that cannot fail is worse than no gate, because
it is a gate people have learned to trust. Every number in a paper that is "checked
automatically" rests on the check being able to say no.

---

## The pattern

Five of these six are the same shape: **a comparison that silently substitutes something
adjacent for the thing it claims to compare.** Blank responses substituted for answers, two runs
for two versions, pooled siblings for a same-version baseline, requantisation for intervention,
judge agreement for construct validity. The sixth is what lets the other five survive — checking
machinery that cannot report a problem.

All of the data, scripts and correction ledgers behind these numbers are in this repository.
`CORRECTIONS.md` records what we published and then withdrew, with dates.
[`PRIOR-WORK-CORRECTIONS.md`](PRIOR-WORK-CORRECTIONS.md) is the companion to this file and the
harder one: what we find missing in twelve published studies, per study, with the remedy where
the data is already in the authors' hands — seven of the twelve are in that position. It holds
itself to a written standard, including that no entry imputes motive.

Take the checks. We would rather be corrected than cited.
