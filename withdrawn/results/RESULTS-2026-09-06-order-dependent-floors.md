# Three published floors were a property of the filesystem

**Found** 2026-09-06, by a CI failure that did not reproduce locally.
**Fixed** the same day, in two places.
**Published numbers moved.** See `CORRECTIONS.md` §6 in the release repository.

## The defect

Each cell's reference sheet is the per-item **modal** answer across that cell's runs, and every
endpoint delta is measured against it. `modal()` computed it with:

```python
collections.Counter(v).most_common(1)[0][0]
```

`most_common` breaks a tie **by insertion order**. Insertion order here was the order `load()`
read the run files, and `load()` globbed unsorted. So on any item where a cell split evenly —
two runs Disagree, two Agree — the reference answer was decided by the directory listing, and
the directory listing is ext4's on one machine and NTFS's on another.

A published percentile was a property of the filesystem the corpus happened to sit on.

## What moved

| row | before | after |
|---|---:|---:|
| prompt condition A→D, side-flip p90 | 14 | **15** |
| same-version variants, side-flip p90 | 12 | **11** |
| same-version variants, p90 95% CI | [9, 13] | **[8, 13]**, and [8, 15] later the same day when the interval was clustered by version group |
| same-version variants, endpoint median | 9 | **8** |
| presentation order, side-flip MDE | 12 | **13** |
| presentation order, endpoint p90 | 10 or 11, by machine | **10** |

The A→D distribution moves in three places (`3 → 4`, one `5 → 4`, `14 → 15`) and now reads:

```
0, 0, 0, 1, 1, 1, 2, 2, 2, 2, 4, 4, 5, 5, 5, 6, 8, 15, 18, 19
```

**No conclusion changes.** 17 of 20 models still move 8 items or fewer — still inside the
run-to-run replicate floor — and the tail is still three models from one vendor. Both power
verdicts that quote the order floor keep their verdicts against the new MDE: the frontier temp-0
arm observed 14 against an MDE of 13 and stays SUPPORTED; the local-family arm observed 6 and
stays UNDERPOWERED.

That the reading survived is luck, not vindication. The defect was capable of moving a number
across a threshold and nothing would have caught it.

## How it was found, which is the part worth keeping

`gen_paper.py --check` went **red in CI and green on the author's machine, against the same
commit**. The message was:

```
STALE blocks in PAPER-no-position-only-consensus.md: floors
```

A name and no diff. Eliminating suspects by hand cost far more than the fix: the gitignored
`refusal-ablation` runs (moved aside, no effect), the committed tree (clean worktree at the
pushed sha, green), Python 3.13 (green). `floor_table` is pure stdlib with a seeded bootstrap
and is deterministic across repeated local runs, so only the environment was left — which is
the one thing a diff would have named immediately.

`--check` now prints a unified diff of the block, paper side against freshly computed, and says
explicitly that an empty or formatting-only diff means the two sides were computed in different
environments and regenerating would commit *this* machine's answer rather than fix anything.
That diff named the defect in one line: same 84 pairs, one differing value.

**A detector that reports drift without reporting what drifted is half an instrument.**

## The fix

Two places, so neither can reintroduce it alone:

1. **`load()` sorts its glob.** The corpus read order is canonical rather than the filesystem's.
2. **`modal()` breaks ties by the lower position, explicitly.** The rule is arbitrary — a tie
   means the cell has *no* modal answer for that item — and being written down is the whole
   difference from inheriting it from a dict.

Four tests in `scripts/test_analysis_plumbing.py` pin it: `modal()` returns one answer across
all 24 permutations of a tied cell; ties resolve to the lower position; no `glob.glob` in
`floor_table` is unsorted; and every floor comes back byte-identical when the corpus is handed
back reversed and shuffled.

## Why this is the project's own argument

This paper convicts other studies of reporting numbers that do not survive contact with a
nuisance factor nobody controlled for. The nuisance factor here was the sort order of a
directory, and it sat inside our own reference sheet for weeks.

It also explains why the reproducibility work is not decoration. A replicator on Linux running
the published pipeline against the published corpus would have got a different table and had no
way to tell whether they had made a mistake.
