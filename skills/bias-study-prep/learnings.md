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

## 2026-09-14 — repairing a corpus a token cap destroyed

The May corpus lost about a third of its records to an 800-token budget, differentially by
model. Six corpora were repaired. **This is the procedure a replicator needs**, and every step
below is here because skipping it produced a wrong answer.

```bash
python scripts/recollect_at_cap.py --plan  --source <damaged> --out-date <repair>
python scripts/recollect_at_cap.py --run   --source <damaged> --out-date <repair>
python scripts/collection_check.py <repair>            # must say ACCEPTED
python scripts/score.py <repair> --fill-missing
python scripts/splice_corpus.py --write --base <damaged>
# register the pair in studypaths.REPAIRS
```

- **`--plan` before spending.** The tool was pointed at a 520-record run while the damage sat in
  a 780-record one. It saw ZERO of the 176 broken cells and printed "0 to do" with complete
  confidence. A repair tool aimed at the wrong corpus is worse than none: it closes the question.
- **One output directory per source.** Cell keys are `(model, question_id, condition)` and they
  COLLIDE across runs. Three sources pointed at one directory made the second and third see the
  first's records as already collected — one run collected 0 of 20 and reported success.
- **"Done" is a usable RESPONSE, not a scored one.** Judging completion by eligibility (which
  needs a score) marks every fresh cell incomplete and re-collects everything next run.
- **`--fill-missing`, never `--rescore`.** Reuse keyed on RESPONSE TEXT: a repaired cell carries
  new text under the same key, and inheriting the old judgement makes the repair look like it
  changed nothing — invisibly, and in the direction that argues against its own fix.
- **Splice, or the repair does nothing.** Every analysis script reads ONE run directory.
- **Never enumerate a derived corpus.** It is a view over base + repairs; counting it alongside
  both triple-counts. 2,483 phantom rows and a broken cross-path check.
- **Match the baseline's budget to its arm's.** An unmatched baseline moved three of four rung-2
  contrasts on Opus, two from spanning zero to excluding it.

**Three signatures of budget damage**, each found after the previous rule missed cases:

1. **At the cap — relative to the record's OWN `max_tokens`.** A fixed threshold called every
   ordinary 900-token answer at a 4,000 budget "exhausted" and invented 914 cells of work.
2. **A completed call returning no text.** All 486 empties in this corpus sit at a single exact
   token count per model; gpt-5's 286 all at **768**, below any 790 threshold. That is a budget
   spent on reasoning, and those cells return complete text at 4,000. "The model returned
   nothing" was "the model returned nothing within 800 tokens" — a collection parameter
   published as a property of a vendor's model.
3. **Text stopping mid-clause at any token count.** `ernie-4.5` truncates at 740–772.

**Read the text before widening a detector.** A response ending on a markdown URL at 48% of cap
was a FALSE positive, and the right call was to leave the detector alone. One cell in 386 changes
no number.

**Say what is still missing.** Three models have been WITHDRAWN from the provider and return
HTTP 404, including the base of the abliterated judge — so one published robustness leg is
unreproducible by anyone. `studypaths.UNREPAIRABLE` records each with evidence. A corpus that
cannot say what is missing from it is not repaired, only larger.

## 2026-09-14 — ask whether the treatment was administered, because nothing else does

`run_g0dm0d3.py` sent `parseltongue: true`. The server returned 200. The response was complete,
the judges scored it, the interval was computed, and on Claude Opus it **excluded zero**. Every
check this project runs passed. The obfuscation never happened — on **0 of 240 requests**, across
both pipeline runs.

G0DM0D3's Parseltongue rewrites **trigger words** from a fixed list of 53 security and jailbreak
terms, and returns the text **unchanged** when it finds none. The instrument is ten neutral
policy questions. Not one contains a trigger. So `B-Parseltongue` was condition B, collected
again, under a different label — and its contrast against plain B was published as an
elicitation result.

**This is the study's signature failure mode in its purest form: a call that succeeded, a
response that was complete, a score that was valid, an interval that excluded zero, and nothing
underneath.** Everything was checked except whether the treatment was applied.

### Rules

- **Ask what the SERVER says it did, not what you asked it to do.** The evidence was in every
  record from the first run: the collector had been storing the server's echo
  (`study_call_metadata.x_g0dm0d3.pipeline`) all along and no analysis had ever read it. A
  vendor extension block you store and never read is not provenance, it is a habit.
  `scripts/pipeline_transform_audit.py` is that read, and it takes no API calls.
- **An arm named after a transform is a claim, and it needs a receipt.** Record what actually
  ran per record. `run_local.py` inferred `obliteratus_applied` from whether the string `ablit`
  appeared in the run **label** — 220 abliteration records cannot say whether they ran on
  abliterated weights. That is a weaker finding than Parseltongue's (no evidence either way
  rather than proof of absence) and it is recorded separately for exactly that reason.
- **Send every flag explicitly, including the false ones.** G0DM0D3 defaults `godmode` and
  `parseltongue` to **true** when the field is absent. An omitted flag is not "off", it is the
  opposite of off.
- **A null arm is worth more than a mislabelled treatment, once you know it is null.** Because
  B-Parseltongue applies nothing, its contrast against plain B is a **null by construction** and
  therefore the floor every other contrast in the column must clear. On Opus that floor reads
  **+0.24 [+0.02, +0.49] and excludes zero.** Five of ten intervals in that arm exclude zero and
  one of the five is a measurement of nothing — which is a statement about the interval
  machinery, not about the models.
- **Difference within the run when you can.** `B-STM minus B-Parseltongue` cancels the baseline
  run, the collection date and the proxy path, leaving only STM: **+0.13 [−0.07, +0.36]** on Opus
  and **−0.02** on Grok, both spanning zero. The `vs plain B` version of the same question read
  +0.37 and excluded zero. The confounded contrast was the one that looked like a result.
- **Check the baseline came down the same pipe.** The rung-2 baseline goes direct to OpenRouter
  while every pipeline record goes through the proxy, so all six `vs plain B` contrasts confound
  the transform with the path. The fix is a control arm — plain condition B **through the
  proxy**, every transform off — not a caveat.
- **Verify the conditions differ IN THE RECORDS, not in the constructor.**
  `tests/test_condition_construction.py` passed throughout: the flags were right in the source
  and the collection was still wrong. `collection_check.py` check 9 now compares the stored
  prompts across conditions within a run. Corpus-wide over 33 runs and 1,206 cells the only hits
  are the two pipeline runs. Related: on a **proxied** record `user_prompt` is the
  **pre-transform** text, so it does not say what the model received.
- **Do not let a disclosed defect hold a gate red.** Parseltongue stays dead until the instrument
  changes. `--check` therefore blocks on an **undisclosed** dead transform and reports the known
  ones from `studypaths.UNVERIFIED_TREATMENT`. A gate that can never go green is a gate someone
  deletes, taking the check for the next one with it. Writing that registry is also what caught
  the second defect: `B-Layered` requests obfuscation too, I had documented it in prose and
  forgotten to record it, and the gate went red naming the exact pair.
- **Three verdicts, kept apart.** DISPROVEN (the treatment provably did not happen),
  PARTIALLY INERT (the arm is treated; one named ingredient is not), UNRECORDED (no evidence
  either way, which is itself the finding). Collapsing them would have thrown away rung 2's only
  surviving effect: `B-Layered minus B-STM` is **−0.31** on Opus and **+0.48** on Grok. That
  contrast never reads the baseline run, so it survived both this confound and the token-budget
  confound repaired the same day — two models moving in **opposite directions** under the same
  intervention.

### For a replicator

Run `python scripts/pipeline_transform_audit.py --live` before trusting any pipeline-rung number.
It reads what the collection actually did and probes whether your server still behaves that way.
If you are running the pipeline rung against your own G0DM0D3 checkout, a transform that is inert
on your instrument will produce clean, scorable, plausible output and no error anywhere.

## 2026-09-15 — a control is a claim too, and the last line of a collector is the riskiest

Three rules, each earned the same day the rung-2 audit landed.

### Check the CONTROL received nothing, not just that the arm received something

`pipeline_transform_audit.py` was written to catch an arm whose named transform never fired.
Within hours the arm gained a control, and the same question runs the other way — **did the
baseline get treated?** That is the worse failure of the two. A treated arm that was not treated
overstates a null and the null is visible. An untreated control that was quietly treated
**understates every effect measured against it**, and it does so while looking exactly like a
clean baseline.

Not hypothetical on this toolchain: G0DM0D3 defaults `godmode` and `parseltongue` to **true**
when the field is absent, so a control written the natural way — by leaving the flags out — is
the fully-forced arm. Every flag is now sent explicitly, including the false ones, and
`CONTROL_CONDITIONS` declares which arms must show nothing. Probed both ways before trusting it:
green as it stands, red when a treated arm is declared the control.

### A name a script never binds is a NameError waiting for a rare path

`recollect_at_cap.py` used `LEGACY_SEED` and imported only `run_roots`. Python does not care
until the line runs, and that line is the **last** one in the collector. So a repair run made
every API call, wrote all 106 records, and died writing its manifest.

That is the worst available shape: **the expensive half succeeded and the cheap half took the
provenance with it.** What was lost doesn't announce itself — it surfaces later, in a different
tool, as a provenance finding on a run nobody remembers collecting.

It hid for a second reason worth keeping: `repair_recollect_provenance.py --manifests` had been
backfilling the missing manifests, so **the symptom was being cleaned up faster than the cause
could be seen.** Every other repair run reported "manifest ok" for exactly that reason. When a
repair tool exists for a defect, check whether the defect is still being produced.

`scripts/check_undefined_names.py` scans every name read against every name bound. It is
deliberately weaker than real scope analysis — if a name is bound anywhere at all, in any scope
or branch, it is not reported — because a linter that cries wolf in this repository gets switched
off wholesale, which is how `validate_runs.py` came to have 44 live findings wired into no gate.
First pass: 29 findings, **24 of them `key=lambda x:` parameters**, which is the false-positive
class the docstring claimed it could not have. Fixed, re-run, two real findings left: the missing
import, and a `pytest.skip()` in a file that never imported pytest — so a checkout lacking a
local build got `NameError` where it should have got a skip.

### Difference within a sitting, not across one

The rung-2 null floor looked like the proxy path: the pipeline arm goes through G0DM0D3 and its
baseline goes direct to the vendor. So it was **collected instead of argued about** — plain
condition B through the proxy with every transform off, 100 calls. The path costs **+0.06** on
Opus and **−0.14** on Grok, both spanning zero.

Which relocated the problem rather than closing it. The control shares a sitting with the
baseline; the arm predates both by a day. So the floor is **cross-sitting drift** — about
**+0.18** on Opus, two identical arms a day apart, with an interval that excludes zero.

The lesson generalises past this arm: **a 10-question, 5-sample cell on Opus cannot resolve an
effect below roughly 0.25 across sittings**, which is larger than most of what that arm reports.
Collect the baseline in the same sitting as the arm it is differenced against, and prefer a
within-arm contrast when one exists. Rung 2's surviving finding is within-arm for exactly this
reason, and it is the only number there that has survived every correction.
