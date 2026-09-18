# Backlog — open problems after the instrument correction

Recorded 2026-09-16. Everything here is **known and unfixed**; nothing in this file is
blocking the collection unless marked BLOCKING. The point of writing them down is that the
defects this study spent the day on were all things somebody had noticed and nobody had
written anywhere a gate could read.

Sources: the 2026-09-16 hostile review of the launch design, and a per-arm verification pass
that ran every `floor_*` function against the live data and checked every `load()` glob for
existence.

---

## 1. Pre-registration does not cover what will be collected

`PREREG-2026-09-14-i3-phase4.md` names the withdrawn 60-item bank, "30 pairs differing by
exactly one inserted not", and stratification by `claim_type`. The Ratchet battery is 32
items in 16 pairs and **has no `claim_type` field**, so the prereg's strata have no carrier.

A collection not covered by an amendment is not pre-registered. **Amendment 2 is owed** and
must name: the instrument and its file, 32 items / 16 pairs, `power.BOUND` = 32, the
four-pass collection design including the `4 × D` replicate choice, the sibling-addition
rule already written into `wave-panel.json`, and the author's ruling on the five disputed
pairs.

`claim_type` can be added to the bank as a structural field without touching a sentence —
ids unchanged, so the 167 already-collected sheets stay valid. Its six documented-empirical
pairs are 11–16 (US intermediaries, OSA, DSA, Aadhaar, Israel, China); pair 5
(content-moderation) is the contested-empirical analogue.

## 2. The disputed-pair list disagrees between two documents

The close-out plan lists the flagged pairs as **1/2, 5/6, 13/14, 17/18, 29/30** (item ids).
The signed sheet lists **pairs 1, 3, 9, 15**, with 10 and 13 raised and withdrawn. Those are
not the same set — pair 7 (deplatforming) appears in one, pairs 10/13 in the other.

The signed sheet is the durable record. Reconcile before either becomes a Limitations
sentence, because a Limitations paragraph that misstates which pairs were disputed is worse
than one that omits it.

## 3. Invalid sheets are never re-rolled

`run_i3_wave.done_cells` counts a cell as collected whether its sheet was valid or not, so
the prereg's rule — "a run that does not yield exactly N clean answers is discarded whole and
rerun" — is not executed by anything. `hf.co/.../gemma-4-12B` has 8 of 12 invalid and will
enter the order floor on four sheets.

Fix: treat `failure_mode in ("other", "truncated", "budget-exhausted")` as not-done with a
retry cap recorded on the record. Refusals stay done — a refusal is a measurement.

## 4. A format failure is being published as a refusal

`llama3.1:8b` under A/seed 11 returns a complete 32-answer sheet in the shape
`N. <proposition>\nAgree` — the option on the line *after* the number. `LINE_RE` in
`run_battery.py` requires them on one line, so the sheet parses to zero answers and
`classify_failure` calls a non-empty, non-capped, zero-answer body a refusal.

Four of llama's six "refusals" are this. The refusal-by-vendor deliverable inherits it, and
the local class is where it lands.

Fix: accept an option token on the following line, or classify that shape as `format` rather
than `refused`. Either is fine; publishing it as a refusal is not.

## 5. Two copies of the collection protocol, and one is false

`data/wave-panel.json` `params` says `max_tokens 8192, runs 5, seed_base 20260830,
seed_sweep true` and calls itself "held constant across waves". The runner uses 32768, one
run per cell, `20260915`, and no sweep outside the replicate pass. Delete the params block or
derive it; a protocol recorded in two places has already drifted.

`floor_table.py` notes at the order-wave and condition-wave rows state "5 runs per cell,
modal against modal" and "swept seed, 5 runs, wave 0". Both are false for this design and
both flow into generated `GEN:` blocks in the paper.

## 6. Arms that cannot compute on this design

Verified by running each one. Not defects — design consequences, listed so nobody reports
them as missing later:

- **paraphrase / template floor** — the wave varies no template. Gone unless designed in.
- **elicitation format** — the constrained-decoding arm is 62-item, on the retired
  instrument.
- **ablation** — out of scope for this wave.
- **`floor_conditions`** — superseded by `floor_conditions_wave`.

## 7. Resolution: 32 items is coarser than 62

One side-flip is 3.1% of a sheet against 1.6% on the retired instrument. Every floor and
effect is measured in *items of the sheet*, so **no compass-era number is comparable in the
same units** — every one quoted in `PAPER-below-the-floor.md` must be re-derived or expressed
as a fraction.

With frontier order floors at p90 1–3 items on 62, the same rows on 32 will sit at 0–1, at
the quantisation of the instrument. The battery can *bound* the frontier floors; it cannot
resolve them. That sentence belongs in Limitations.

## 8. The same-version null is clustered

24 pairs from 10 groups after the sibling additions, but 12 of the 24 are the gpt-5.6 family.
`summarise()` reports the max as the p90 below n=10 and the cluster bootstrap runs over
groups, so the arithmetic is honest — the *composition* is what needs stating. The paper's
claim is that nobody reports this null as a distribution; ours is a distribution over 10
sibling groups, three of which are one vendor's tier ladder.

Cheap widening, all coverage-rule and pre-registerable: serving-path nulls (same model, same
condition, pinned to a second backend — OpenRouter offers ≥2 for several panel models),
requantisation nulls (pass 4, free), and think/no-think mode variants on the local models
(free).

## 9. Export path is untested for battery records

`export_scrubbed.py` assumes 62 items and the retired instrument's text. The public data
release has never been run on battery records.

## 10. `check_instrument_approved.find_sheet_for` is loose

It accepts the first `ITEM-READ-*.md` whose text merely *contains* the bank filename, and
counts every `[x]` in the file. Correct today because no other sheet mentions the battery,
but a second sheet naming it in passing would be accepted. Match on a declared header rather
than a substring.

## 11. Mirror drift

`collection_check.py`, `key_numbers.py` and `refusal_table.py` differ between the working
tree and the public mirror. The collectors and `floor_table` are identical. Any fix from this
list lands in both or `check_no_fork` reports it.
