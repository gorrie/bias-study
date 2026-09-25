# Verification — the corrections read, entries #15–#30, 2026-09-24

**Who read it.** The author ruled on 2026-09-24 that a Fable read of the entries added since
the 2026-09-12 read (`VERIFICATION-2026-09-12-corrections-read.md`, entries #1–#14) would stand
in for the human read, and that the release ships after it. The read was read-only; every edit
below was made afterwards, and each finding was checked against the files before it was acted
on.

**Standard.** For each entry: is what it says was claimed, and what replaced it, true; does it
say what was wrong, when it went out, when it came back and what replaced it; does the paper
or README still carry the withdrawn claim; and does an entry about other researchers' work
stay factual.

## Verdicts, entries #15–#28

| # | verdict | finding | applied |
|---|---|---|---|
| 15 | PASS | figures reproduce from the tracked run summary | `aggregate.py` docstring quoted a third corrected split; now points at the run summary |
| 16 | PASS | 0/240 and the rest reproduce from `pipeline_transform_audit.py` | — |
| 17 | NEEDS-EDIT | "Published" for a commit never pushed; contradicted entry 27 | now "Committed … unpushed" |
| 18 | NEEDS-EDIT | "Published" for a file never in the mirror; FINDINGS.md still asserted the reading | header corrected; FINDINGS #12 given a narrowing note |
| 19 | NEEDS-EDIT, blocking | the replacement it named was itself withdrawn on 2026-09-19 | superseding note → entry 29 |
| 20 | PASS | — | — |
| 21 | PASS | — | — |
| 22 | NEEDS-EDIT | carried a Gemma statement retracted on 2026-09-20 | dated note added |
| 23 | NEEDS-EDIT, blocking | gave DeepSeek V3.2 mistral-large's p (0.0034; DeepSeek's is < 0.0001) | corrected; `robustness_checks.py` re-run to confirm |
| 24 | PASS | — | — |
| 25 | PASS | — | — |
| 26 | FAIL, blocking | called a git-ignored, never-committed file "published" and "unchanged" | both statements rewritten |
| 27 | NEEDS-EDIT | twelve recollect runs, not thirteen; first landed in `598c544` | corrected here and in `CORPUS-MAP-2026-09-14.md` |
| 28 | PASS | the live research page still carries the nulls until the website deploy | reach note added |

## Entries added by the read

- **#29** — the same-version magnitude on the retired questionnaire (median 5 of 62, p90 11),
  public since `8d6960e`, withdrawn in the paper on 2026-09-19 with no ledger entry. Registered
  in `data/withdrawals.json`; its phrases then caught the research page asserting it, and the
  page's paragraph became a dated withdrawal note.
- **#30** — the README's "two large effects hold under every judge" (`ff756ed`), narrowed by
  the paper on 2026-09-22. Ruled a withdrawal by the ledger's own rule. Its phrases caught
  entry 5 and `RUBRIC-SCORES.md` asserting it; both corrected.

The post-push review the same day checked #29 and #30 against `floor_table` and `judge_lean`
output and found them sound, and noted that #1 and #8 had been overtaken without pointers;
both now carry superseding notes.

## Coverage

All 30 entries have now been read: #1–#14 by the author on 2026-09-12, #15–#30 as above.
