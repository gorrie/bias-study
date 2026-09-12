# Versioning

This repository has **two independent version axes**, and conflating them is easy because both
have used the letter v. Read this once and the tags make sense.

## Axis 1 — the intervention rungs. These are NOT releases.

The May 2026 study escalates through three interventions, and it names them:

| rung | what it does |
|---|---|
| **v1** | a prompt edit — change the system prompt, re-ask |
| **v2** | an elicitation pipeline — persona and framing pressure |
| **v3** | cutting the refusal direction out of the weights (abliteration) |

This vocabulary is **published** — it appears in the original writeup, in the paper, and in
external references to them. It is not renamed here, because renaming published vocabulary
breaks every citation of it.

So `v3` in prose means *the weight-level rung*. It never means "the third release."

## Axis 2 — releases. These are DATED, not numbered.

Because axis 1 owns v1/v2/v3, releases cannot use those numbers without ambiguity. They are
dated instead:

| tag | date | what it is |
|---|---|---|
| `release-2026-05-27` | 2026-05-27 | first public release: the judge-panel study across the three rungs |
| `release-2026-09-11` | 2026-09-11 | the forced-choice re-measurement, its twelve floors, the controls audit, and wave 0 |
| `release-2026-09-12` | 2026-09-12 | all twelve studies read against the scoring controls; the correction pass; CI green for the first time |

> This table listed a tag called `release-2026-09` that was never created, in the file whose
> subject is what a release tag has to mean. It also said `CORRECTIONS.md` held seven entries
> when it held fourteen. Both fixed 2026-09-12. The dates above are the tags that exist; check
> with `git tag`, and if this table and the tags disagree again, the tags are right.

**A dated tag cannot collide with a rung, and it says when the numbers were true** — which
matters more than a sequence number in a study whose own finding is that numbers move.

### The one legacy tag

`v2.0.0` exists, points at a 2026-07-10 commit mid-history, and is **left exactly where it
is.** It predates this scheme. Moving or deleting a published tag breaks anyone who pinned it,
and the whole reason the history is preserved is so external references keep resolving.

`pre-rewrite-backup-2026-09-05` is likewise a safety tag, not a release.

## Why the history is not squashed

The first commit is dated **2026-05-27**. That date is the point of keeping it: it establishes
when this work was published relative to others working the same question. A tidy history that
loses the priority date would cost more than it buys.

Corrections are therefore **additive**. Every claim this study published and then withdrew is in
`CORRECTIONS.md` with the date it went out, the date it came back, and what replaced it —
**14 entries** as of 2026-09-12. This said seven for as long as there were fourteen, which
is a small irony in a file arguing that the record has to be additive: the count was typed once
and the entries kept arriving. The commits that carried the retracted claims stay in the log.

## How to tell what you are looking at

- **`CORRECTIONS.md`** is the version history that matters. If a number you have seen quoted
  disagrees with the current one, look there first.
- **Every table** in the paper is generated between `<!-- GEN:x -->` markers and regenerated
  from `runs/`. A gate fails the build if a table drifts from the data.
- **`RELEASE-v2.md`** in the private tree defines what a release must satisfy before it ships:
  all gates green, no arm at n=1, no retracted phrase asserted anywhere including in the JSON,
  and a reader able to reproduce the open-weight half with no API key.

## What comes next, and what it will be called

The next study — language and character-set effects, doing the ablation ourselves, logit
scoring, larger open-weight models — is in `BACKLOG-larger-hardware-and-v3.md` in the private
tree. **It will be a dated release too**, not "v3", precisely because `v3` already means the
weight rung.
