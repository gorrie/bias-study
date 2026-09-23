# Correction, 2026-09-17 — the power audit's verdicts moved when the floors were re-measured

> ## WITHDRAWN THE SAME DAY. The verdict changes below are a unit error.
>
> An independent review found it. Every `observed` value in `power.PUBLISHED_NULLS` is a count
> of **items that moved out of 62** — each one measured on the retired instrument, as the
> `where` fields say: STATUS section 2, the live research page, `RESULTS-2026-08-30-access-tier`.
> Every threshold in the table it is compared against is now a count **out of 32**.
>
> 14 of 62 is 23% of the instrument. A threshold of 11 of 32 is 34%. Comparing the two because
> both are integers is not a comparison. **The verdicts did not flip; the denominator changed.**
>
> `PREREG-2026-09-14-i3-phase4.md` Amendment 2 states the rule this broke: no figure measured
> against the old bound is comparable in the same units. And it cannot be fixed by rescaling —
> a side-flip count is not linear in item count, because the ITEMS differ, not merely how many
> there are.
>
> `power.py` refused the audit outright, named all five affected claims, and exited 2 (NOT
> APPLICABLE). `scripts/test_correction_gates.py::test_observations_in_other_units_are_refused_not_compared`
> held it there, and instructed that the guard and the test be deleted together once the nulls
> were re-measured on the live instrument.
>
> ### RESOLVED 2026-09-18 — DELETED, NOT RE-MEASURED. Read this before citing any of the five.
>
> The guard, the audit, `PUBLISHED_NULLS` and `RETIRED_BOUND` are gone from `power.py`, and the
> test above is replaced by `test_no_audit_of_observations_in_retired_units`, which asserts the
> constants stay gone and that `power.main()` exits 0 on the detection-limit table alone.
>
> **The condition the instruction above named was NOT met.** The five nulls were not re-measured
> on the live instrument. They were deleted because **the claims themselves are withdrawn** —
> the study no longer asserts any of them — and because a guard that exits 2 unconditionally
> blocked `gen_paper` on a comparison that will never become valid. Those are different reasons
> and the distinction is written here so that a later reader does not infer from the deletion
> that a re-measurement happened.
>
> Anyone reviving one of these five claims must re-collect it on the Ratchet battery first.
> There is no path from the recorded numbers to a verdict: 14 of 62 and 11 of 32 are not
> commensurable, and a side-flip count cannot be rescaled because the items differ, not just
> how many there are.
>
> **The detection-limit table above the verdicts is unaffected** — it describes what the live
> instrument can resolve and is computed entirely from battery floors. It is only the
> comparison against published observations that was invalid.
>
> What follows is the withdrawn text, kept because deleting a correction is how a wrong number
> survives as a claim nobody can trace.

---


## What changed

`scripts/power.py` audits every published null against the detection limit of the floor it was
measured against. Until today those floors were measured on the **retired external
questionnaire**; they are now measured on the study's own instrument, the 32-item Ratchet
battery, across four collection passes.

The verdict counts moved:

| | before | after |
|---|---|---|
| underpowered — "no effect" not established | **3 of 5** | **1 of 5** |
| not resolvable at all | 1 | 1 |
| clears its floor — calling it a null was wrong in the other direction | **1** | **3** |

`tests/test_power.py::test_live_audit_still_runs_and_reports_five_nulls` was written to FAIL
when this happens, and it did. Its own docstring says why: *"If this count moves, a real
verdict changed and that needs a dated correction, not a green test."* This is that
correction; the test is updated to the new counts in the same commit, not before it.

## Why it moved

Two floors changed shape, and both changes make the instrument sharper rather than looser.

**The requantisation floor exists again, and it is large.** 16 pairs, side p90 9, endpoint p90
9, collected in pass 4 from five local weight families served at Q4 and Q8. Its detection
threshold is 10 items. `p95 IS THE SAMPLE MAX (n=16)` — that is disclosed in the table and is
not a rounding artefact, it is what a nearest-rank p95 on sixteen observations means.

**The replicate floor exists for the first time on this instrument.** 336 pairs from pass 2,
side p90 2, endpoint p90 13. A null that was previously judged against a borrowed reference is
now judged against run-to-run variation actually measured on the sheets it concerns.

## The three that now clear their floor

These are not restored findings. A null that "clears its floor" means the movement it declared
absent is **larger than what the instrument can resolve** — so declaring it absent was wrong in
the other direction. The claim is UNDECIDED, not true.

One of the three is the study's own published position claim at frontier temperature 0:
observed 14 items against a threshold of 11. It is stated on the live page unscoped, and the
scoped version of the same claim on local families remains UNDERPOWERED at observed 6. The
same sentence is wrong in opposite directions on the two populations it pools.

## What this does not settle

The ablation null remains NOT RESOLVABLE: its observed effect is n=1 per arm against a
replicate floor of p90 5. More floor precision cannot rescue an observation that thin. The
2026-09-07 ablation wave re-collected it at n=5 and is on the retired instrument, so it is
UNDECIDED in both directions until re-collected here.

## Also corrected

`power.py` printed its header as *"what this instrument can resolve, per null, of 62 items"* —
the retired questionnaire's length — above a table whose every threshold is a count of items
out of 32. `BOUND` already read the live bank; the header did not. It is derived now.
