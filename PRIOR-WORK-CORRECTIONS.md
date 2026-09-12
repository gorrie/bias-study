# Corrections to prior work

`CORRECTIONS.md` is what this study got wrong. **This file is what this study finds wrong
elsewhere**, and it is the harder document to write honestly, so it is written to a stricter
standard than the rest of the repository.

Every entry names the artifact, the specific claim or omission, the measurement that bears on
it, and — where one exists — **the remedy the authors can apply to their own data.** None of it
imputes motive. A methodological point does not need one, and this file has already been
reworded once to remove one (see `rozado2024` below, and the note in `scripts/controls_audit.py`).

---

## The standard this file holds itself to

1. **Name the artifact and its version.** A correction that does not say which version it applies
   to is unfalsifiable, and every artifact below moves.
2. **Quote the design, not the author.** The entries describe what a paper does and does not
   measure. They do not characterise intent, competence or motive.
3. **Offer the remedy.** Where the data to fix the gap is already in the authors' hands, say so.
   Six of the twelve studies below are in that position.
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
thirteen controls. Nine were read in full rather than from a summary.
**Reproduce:** `python scripts/controls_audit.py` (matrix), `--gaps` (tallies and per-study text).

A **same-version null** asks what two measurements differ by when *nothing about the model has
changed* — same version, different snapshot date, size, tier, or serving mode. Without it, an
observed difference between two model versions has nothing to be scored against.

**Tally across the twelve, on the distribution form of that control:**

| control | yes | partial | no | n/a | unknown |
|---|---:|---:|---:|---:|---:|
| `same_version_dist` — a null as a **distribution** (median + upper percentile over many pairs) | **0** | 0 | **8** | 1 | 3 |
| `same_version_point` — any same-version pair used as a negative control, even one | 1 | 2 | 5 | 1 | 3 |
| `reported_mde` — a minimum detectable effect or resolution limit reported | 2 | 1 | **8** | – | 1 |

**Not one of the twelve reports a same-version null as a distribution.** Eight report none at
all. Eight report no detection limit of any kind.

**What this study measures for comparison:** 97 same-version pairs, median disagreement **5 of 62**
forced-choice propositions, giving a detection limit of **11**. Presentation order alone reaches
p90 **14** and a maximum of **24** items on 2024-generation open-weight models, and p90 **6** on
2026 frontier models. Any claimed political shift smaller than the relevant floor is inside the
instrument's own noise, whatever its p-value.

### Six of them can fix this from data they already hold

This is the constructive half, and it is why the file exists. In each case the pairs required are
already inside the published design:

| study | the pairs already in their design |
|---|---|
| `rottger2024` | GPT-3.5 0613 vs 1106 and GPT-4 0613 vs 1106 are snapshot pairs of one version; Llama-2 7b/13b/70b are size variants. All four sit in the model list as separate subjects rather than as a baseline. |
| `naser2026` | Same-version pairs exist inside their own tier ladder — mini vs flagship at one generation, dated snapshots of one name — and are read as drift transitions carrying *d* values rather than as a baseline. |
| `liu2025` | The same-version snapshot pair **is the treatment**, not a control. Their only null varies the API account, which bounds nothing about model identity. Two same-date cross-tier pairs are also in hand and neither is estimated. |
| `kamal2025` | A clean pair exists — Llama-3.2-1B-Instruct at full precision against the same model 4-bit, same version, same size, precision only — used as a generalisability check rather than a null. The difference is never computed. |
| `cen` | Three online/offline pairs of one model each. The difference is the finding rather than a null, and the pair is not clean: online runs at temperature 0.1 against 0 offline. |
| `rozado2024` | The same-version siblings are **excluded on purpose, and he says so** — left out in favour of variety across model families. That is a stated sampling rationale, openly given. The consequence is that the one comparison capable of bounding model-to-model difference is the one the design removes; the negative control used instead is a synthetic random-answer respondent, which bounds nothing about model-to-model comparison. |

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
`results/RESULTS-2026-09-07-ablation-wave.md`.

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
stopping rule, is that **abliteration does not measurably move political stance on any of the
three usable bases** — and that any single-ablator result, including the one this study published
and withdrew (`CORRECTIONS.md` #8), is a statement about the build.

**The remedy:** use at least two independently-authored ablations of the same base, quant-matched
to the stock arm, and report their disagreement alongside the effect. If the two ablators differ
by as much as the intervention, there is no intervention to report.

## 3. What this file does not claim

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

## 4. If you are one of the authors cited here

The audit's per-study text is in `scripts/controls_audit.py`, in the record for your study, and
it is the single source for the table above — there is no second copy to fall out of sync.

If an entry misreads your design, that is a defect in this repository and it will be corrected in
`CORRECTIONS.md` with the date and what replaced it, the same as every other correction here.
Open an issue with the specific line. If the entry is right and you have since added the control,
say so and it will be updated to reflect it.
