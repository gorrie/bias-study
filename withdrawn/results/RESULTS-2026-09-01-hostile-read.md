# Hostile read of the assembled paper

**2026-09-01.** Backlog B3, and limitation 6 of the paper itself: two hostile reads had run on
individual results, none on the assembly. This is that read. Six findings, every one verified
against the data or the code rather than asserted. Four are fixed. **Two are left for the
author, and the first of them changes a published verdict.**

---

## FIXED 1 — The freshness gate was blind to corruption it introduced itself

The paper's headline defence is in its own subtitle: *"Nothing between `<!-- GEN:x -->` and
`<!-- /GEN:x -->` is hand-written; `scripts/gen_paper.py --check` exits 1 when a table has
drifted from the data."*

The committed paper contained **19 sequences of mojibake** (`â€"`) inside generated blocks —
every em-dash in the timeline and references tables. `gen_paper.py --check` reported **"all 8
generated blocks are current."**

`run()` set `PYTHONIOENCODING=utf-8` for the child and then captured its output with
`text=True` and no `encoding`, so the parent decoded UTF-8 bytes with its own locale — `cp1252`
on this machine. Every em-dash became three characters. And `--check` could not see it,
**because it corrupted both sides of its own comparison**: generated-and-mangled equalled
stored-and-mangled.

> A gate that renders its input through the same defect it is checking for is not a gate.

One-line fix (`encoding="utf-8"`). The gate immediately failed on `references` and `timeline`,
which is the correct answer; regenerated to **0 mojibake**; all three gates green.

This is the most important finding here because of what it says about the others. The paper
argues that generated tables are trustworthy and hand-typed prose is not. That distinction held
for *content* and failed for *bytes*, and it failed silently for as long as the gate existed.

## FIXED 2 — Section 1's opening claim was stale and ungated

> "Across 32 models measured under both arms there are 37 refusals in 449 runs where the prompt
> carries no directive, and none in 347 runs where it carries one. Eight models decline the
> instrument."

Reproduced from the corpus under the sentence's own definitions. **Three of four reproduce
exactly:** 32 models in both arms, 347 directive runs with zero refusals, 8 models declining.
The fourth pair does not: **472 runs and 38 refusals**, not 449 and 37. Stale by one
collection, in the paper's opening argument, with nothing gating it.

Corrected, and the five quantities in that sentence are now gated.

## FIXED 3 — The study count was stated three ways, none matching the record

`data/controls-audit.json` holds 13 entries, one of which is `ours`. So: **12 external studies,
9 read in full, 3 retrieved as method-and-results** (Sakhawat, Sclar, Messing).

| the paper said | where | truth |
|---|---|---|
| "Eleven studies, nine controls" | §5 opening | 12 external studies |
| "Eight of the twelve studies audited" | §3 | correct |
| "All ten studies have now been read in full" | §5 | 9 of 12; and the generated table two lines above marks three `retrieved-summary` |
| "Ten of ten" (no same-version null) | §5 | twelve of twelve — the tally below it says "no 11, n/a 1" |
| "rests on ten papers read in full" | Limitations 4 | 9 of 12, and the same item then concedes Sakhawat was not, omitting Sclar and Messing |

Every one of these sat beside a generated table that had it right. That is precisely the
species §4 confesses — *"Every defect found in this work was a number typed into a document.
Not one was in the code"* — occurring inside the section that says so.

Corrected. Both counts are now gated.

## FIXED 4 — "13 vendor families", over a table printing 16 rows

`vendor_of()` yields **16** keys and the generated refusal table prints all sixteen. Three are
not vendors: `hf.co` (a hosting domain), `huihui_ai` (a community fine-tuner of someone else's
weights), and **`claude-code-harness-agent` — this project's own harness, answering the
instrument as a subject.**

155 models and 1,643 runs both verify exactly. The vendor count did not. A paper whose thesis
is that studies fail to disclose what they pooled cannot state a tidier count than its own
table, so the prose now states 16, names the three that are not vendors, and says twelve are
vendor families in the ordinary sense. Gated.

## FIXED 5 — The refusal table's exclusion was disclosed in the code, not the paper

The block carried a bare line: `excluding: 2026-08-31-google-orderfloor`. The rationale and its
cost existed only in a source comment in `gen_paper.py`: that run is a targeted re-collection of
the three Google models that refuse most, and **including it lifts the Google row from 27% to
41%.** Google anchors §1. A reader could not learn either fact from the paper.

The exclusion is right — a sample selected for refusing must not set a vendor's rate. It is now
argued in the paper instead of assumed.

---

## FOR THE AUTHOR 1 — §3 judges a frontier claim against the pooled order floor, and it flips a verdict

This is the finding worth the read.

§2 makes class-splitting the paper's central methodological contribution, in its own words:

> "A single pooled order floor would have been a net aggregate concealing gross movement
> between two populations. That is a defect this project has already caught in itself once,
> and **here it would have been in the title.**"

It is not in the title. It is in the flagship audit table in §3. `PUBLISHED_NULLS` in
`power.py` judges *both* prompt-pressure nulls against one unsplit `"presentation order"`
floor, including the one scoped **"frontier, temp 0"** — while `floor_order_by_class()`, which
§2 uses, sits in the same module.

Measured both ways, with the paper's own estimator:

| claim | floor used | n | threshold | MDE | observed | verdict |
|---|---|---:|---:|---:|---:|---|
| position does not move under prompt pressure (frontier, temp 0) | pooled order | 39 | 17 | 16 | 14 | UNDERPOWERED |
| **same claim** | **frontier order** | 21 | **5** | **5** | 14 | **EXCEEDS the limit — not a null** |
| position does not move under prompt pressure (local families) | pooled order | 39 | 17 | 16 | 6 | UNDERPOWERED |
| **same claim** | **local order** | 18 | **24** | **20** | 6 | UNDERPOWERED, far more so |

**The pooled floor errs in both directions.** It makes the frontier null look undecidable when
the instrument can in fact resolve movement that size, and it understates how badly
underpowered the local null is.

Two consequences:

1. §4 says **"One null inverted outright."** Under class-matched floors, **a second inverts** —
   and `power.py`'s own `where` field describes that claim as *"same claim, unscoped, as
   published on the live page this morning."*
2. §3's summary line "4 of 5 published nulls are underpowered" becomes 3 of 5, with two
   inverted.

**Why this is not fixed here.** Flipping a null to an effect is a scientific claim, not a
tooling repair, and it is the author's call — particularly since it strengthens the project's
position, which is when a change deserves most suspicion. It also needs its own caveat rather
than a silent swap: the frontier order arm is **21 pairs from seven models across six vendors**
(limitation 2), thin enough that a threshold of 5 is itself loosely estimated.

The recommendation is to report both floors per claim rather than choose — the pooled number
and the class-matched one, with the disagreement shown. That is the same move §2 already makes
for the floor itself, applied one table later.

## FOR THE AUTHOR 2 — smaller, and none of them load-bearing

- **The timeline says "seven claims withdrawn" (2026-08-30); §4 says "Ten claims … withdrawn or
  narrowed in three days."** Different scopes, probably both true, unexplained side by side.
- **`aipolcom` is audited as a peer study** while the project administers its instrument through
  aipolcom.net's item set. Limitation 5 discloses the observatory as a half-internal replication
  corpus; the audit row does not carry the same note.
- **§7's "All 97 were checked by hand for pairs that cross a version boundary; none does"** is a
  hand check with no gate, in a paper that attributes all its own defects to hand-typed numbers.
  The claim is probably fine and the reasoning for it is good; it wants a `--check` rather than a
  sentence.

---

## Standing after this read

`gen_paper --check`, `key_numbers --check` and `controls_audit --strict` all pass, and
`key_numbers` now gates **18 numbers rather than 8** — the corpus scale, the audit counts and
every quantity in §1's opening claim are checkable for the first time. Limitation 6 ("no hostile
read of this document") can be struck once FOR-THE-AUTHOR 1 is decided; it should not be struck
before, because the assembly's most consequential defect is still open by design.
