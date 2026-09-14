# bias-study-prep learnings

Heuristics accumulated from running the skill across study runs. Add an entry whenever you encounter a failure mode worth remembering.

## Initial entries (2026-05-25, skill creation)

- **Skill is canonical at `bias-study-release/skills/bias-study-prep/`** (github.com/gorrie/bias-study), which is TRACKED. The runtime path `~/.claude/skills/bias-study-prep/` is a Windows directory junction into it, not a separate copy.
  Corrected 2026-09-02: this used to claim `.claude/skills/` was canonical, and that path is gitignored — so the skill, its four scripts and its ten tests were versioned nowhere while a line in this file said otherwise. A public/internal pair also existed, and the internal copy was the one being tuned, so the published copy described a protocol retired on 2026-08-29. One tracked tree now, no pair.
- **Env var presence is checked, not validated.** `OPENROUTER_API_KEY` set to "test" passes the check. Vendor-specific auth failures surface during the actual study run.
- **build.py exit codes**: `0=READY`, `1=NEEDS FIX`, `2=FAILED`. The skill treats only `0` as clean; any other code blocks the study.
- **No vendor calls in prep.** The prep MUST NOT touch any vendor API — that would burn quota and risk tripping anti-abuse heuristics during what should be a deterministic local check.

## 2026-09-13 — the eight-way audit

Full list with receipts: `research/bias-study/LEARNINGS.md` in the working tree. The ones that
change what this skill does:

- **Run `collection_check.py <run>` before spending a single judge call.** It is
  `COLLECTION-STANDARD.md` §4 made executable. Against the May pipeline wave it returns three
  blockers — no `max_tokens` recorded, 16.7% of responses severed mid-sentence, truncation
  differential at 33.3% vs 0.0%. Run in May it would have stopped that collection before any
  scoring. It did not exist, so the wave was scored and published.
- **Smoke a cell and measure OUTPUT LENGTH, not the exit code.** The defect that cost four
  months was a token cap, and a cap only shows as a length. If the longest smoke response lands
  near the cap, the cap is your ruining parameter — and the next model is more verbose.
- **Never trust `finish_reason` through a proxy.** Ten responses severed mid-word all reported
  `"stop"`. Read the text.
- **A gate that examined nothing must exit non-zero.** Four gates in this repo passed over an
  empty corpus. Probe every check you rely on against an empty tree once, and keep the probe.
- **Check whether exclusion is differential before excluding.** Dropping truncated records
  removed 94.1% of one vendor class and 0.0% of another. Filtering moved the confound into the
  denominator instead of removing it.
- **Ask what already exists before commissioning a collection.** A $259 re-collection was
  proposed while `2026-09-05-recollect` already covered part of the damage. `splice_holes.py`
  answers "how much is still missing", which is the question that matters. It was 176 cells.

## 2026-09-14 — the first collection that came back clean, and what made it clean

`runs/2026-09-13-i3-phase0` is the first run in this project's history to return **1,600 of
1,600 with zero failed calls**, 320 cells every one at five byte-distinct draws, both collection
parameters on every record, 0.2% truncation, one empty response, and `collection_check.py`
ACCEPTED on the first pass. Every earlier wave in 2026 lost something. The steps below are what
differed, in the order they are worth doing. **Follow all seven; each one caught a real defect.**

1. **Write the estimator BEFORE the data exists, and validate it on synthetic input with a
   known answer.** `frame_gap.py` was written and tested against fabricated rows whose true
   frame gap was known before a single call was spent. An estimator written afterwards gets
   shaped by the data it is first run on, and you cannot tell that from reading it.
2. **Pre-register the predictions and read them before you look at the output.** Phase 0's
   prediction 1 MISSED — in the study's favour — and prediction 4 missed as stated. Both were
   published as misses. A prereg you read after the numbers is a summary, not a control.
3. **Dry-run the collector and READ THE PROMPT IT PRINTS.** Not the exit code, the prompt.
   `run_compass.py --dry-run` was building its preview without `shuffle_seed`, so it printed
   items in id order while the collection would have sent them shuffled. On a mirrored bank it
   showed every pair adjacent — the one arrangement the instrument exists to avoid. The preview
   is the step you take BECAUSE you are about to spend money, so it is the worse of the two to
   have wrong: it cannot fail loudly, it can only reassure you about a prompt nobody will send.
4. **Write and flush every record as it arrives.** The collector buffered a whole model in
   memory and a 1,600-record run showed **0 bytes on disk after 90 minutes**. It looked like a
   hang, it was killed, and the work was lost. Per-record append means a killed run keeps
   everything it had already paid for.
5. **Size the token cap from a smoke measurement, then record it per record.** 4000 here, with
   the longest response at 3015 and zero crowding. The cap that ruined four months was never
   written down, so the damage could not be bounded afterwards without re-deriving it.
6. **Verify the replicates are DISTINCT, not merely numerous.** `--samples 5` buys nothing if
   the server returns one deterministic answer five times; `collection_check` counts distinct
   texts per cell and blocks on identical ones. Five copies of one draw is n=1 with a bigger
   file.
7. **Run `collection_check.py <run>` before any judge call, and treat a WARNING as information
   rather than noise.** Phase 0's single empty response was below the block threshold and still
   printed — it is a missing cell, not a measured one.

**Build a mirrored item bank by VERIFYING, never by GENERATING.** The first version of
`build_item_bank.py` derived each negation by inserting "not" after the first auxiliary verb.
On an item whose first auxiliary sat in a subordinate clause it produced *"...a user that their
data was **not** handed over is an abuse of state power"* — a different proposition, fully
collectable, and it would have scored cleanly. It also emitted "have not more influence" and
"have not leverage", which English cannot say. Both halves are now authored and
`verify_negation()` asserts they are the same token sequence bar one inserted "not". A
generator has to be right about grammar; a verifier only has to be right about identity, and
identity is decidable. **Reading all 60 items once caught four defects the tests did not.**

**Balance the acquiescence direction across the bank.** If the critic half is always the
affirmative, "agrees with everything" and "sides with the critic" are the same observable. The
I3 bank makes the critic half affirmative on 15 of 30 pairs for exactly this reason.

**Hold mirror halves apart in presentation.** A plain shuffle leaves a given pair adjacent about
3% of the time, so roughly 60% of 30-pair runs print at least one pair side by side. Side by
side they are visibly a proposition and its negation and consistency costs the model nothing.
`order_items` now enforces a six-position separation and raises rather than silently dropping
the constraint.
