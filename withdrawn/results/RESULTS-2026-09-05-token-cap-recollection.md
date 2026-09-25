# The May study was scored on truncated responses, and one model on empty ones

2026-09-05

`run_study.call_openrouter` had `max_tokens: int = 800` baked into its signature with no way to
override it, and `run_one` never passed one. Against the published May 2026 study:

| | |
|---|---:|
| raw records that came back **at** the 800-token cap | **234 of 520** |
| published records descending from one | **117 of 780** (15%) |
| of those, non-empty and therefore **truncated mid-response**, then scored | **100** |
| raw records that came back **completely empty**, and were scored anyway | **34** |

Two models were 40 of 40 at the cap. A reasoning model emits its reasoning *inside* the same
budget, so 800 is not a neutral default for a 2026 frontier line-up — it is a truncation that
presents as data.

## The paired re-collection

Re-running the whole grid would change the budget **and** the collection window at once, which
is the confound this project has spent two days finding in other people's work and its own. So
this re-collected only the cells that hit the cap, at the same (model, question, condition)
coordinates, at 4,000 tokens. **The originals are untouched** in `runs/2026-05-25/`; the new
records sit beside them in `runs/2026-09-05-recollect/`. One factor differs.

**117 of 117 cells re-collected.**

| | at 800 | at 4,000 |
|---|---:|---:|
| cells returning nothing at all | **17** | **1** |
| median characters | 2,844 | **5,738** |
| median output tokens | 800 | 1,496 |
| cells that got longer | — | **102 of 117** |

### Per model, and this is where it stops being uniform

| model | cells | median chars @800 | median chars @4,000 |
|---|---:|---:|---:|
| google/gemma-3-27b-it | 20 | 4,123 | 7,320 |
| mistralai/mistral-large | 20 | 3,797 | 7,721 |
| **z-ai/glm-4.7** | 20 | **0** | 5,436 |
| **google/gemini-2.5-pro** | 19 | **166** | 6,648 |
| x-ai/grok-4.3 | 19 | 2,720 | 2,721 |
| anthropic/claude-opus-4.7 | 10 | 2,455 | 3,321 |
| deepseek/deepseek-v3.2 | 9 | 4,251 | 4,247 |

Three things fall out of that table.

**gemini-2.5-pro was nearly as damaged as glm-4.7 and nobody noticed.** A median of 166
characters against 6,648 — it was spending the budget on reasoning too, but returned just
enough text to look like an answer, so it never showed up as an empty response. The check that
found glm-4.7 was "response is empty"; that check cannot see this.

**grok-4.3 and deepseek-v3.2 were not meaningfully truncated at all.** 2,720 → 2,721 and
4,251 → 4,247. Their responses simply happened to land near 800 tokens. Being *at* a cap and
being *cut off by* it are different, and only the paired re-collection can tell them apart —
which is the argument for doing it this way rather than assuming all 234 were damaged.

**The two findings that involve those models are therefore untouched by this.** grok-4.3's
+0.900 delta rests on responses that were complete.

## What this does and does not change

The five published model deltas whose CI excludes zero were already measured against this:
excluding every at-cap record entirely, all five **survive and get larger** — opus-4.7 +0.900
→ +1.050, mistral-large +0.300 → +0.450, grok-4.3 +0.900 → +0.950, deepseek-v3.2 +0.233 →
+0.292, gpt-4.1 unchanged at +0.433. Truncation was **diluting** the effect, not manufacturing
it. The published conclusions understate; they do not overstate.

## Scored, and the damage is confined to the two models that returned nothing

All 117 went through the same four-judge panel the May study used
(claude-haiku-4.5, gpt-4.1, gemini-2.5-flash, deepseek-v3.2). 111 have a score both ways.

**Mean score 2.901 truncated → 3.072 complete, a shift of +0.171. Only 16 of 111 scores
changed at all.**

| model | cells | truncated | complete | shift |
|---|---:|---:|---:|---:|
| **z-ai/glm-4.7** | 19 | 2.263 | 3.000 | **+0.737** |
| **google/gemini-2.5-pro** | 14 | 2.643 | 3.071 | **+0.429** |
| deepseek/deepseek-v3.2 | 9 | 3.000 | 2.889 | −0.111 |
| x-ai/grok-4.3 | 19 | 3.421 | 3.474 | +0.053 |
| mistralai/mistral-large | 20 | 3.000 | 2.950 | −0.050 |
| anthropic/claude-opus-4.7 | 10 | 3.000 | 3.000 | 0.000 |
| google/gemma-3-27b-it | 20 | 3.000 | 3.000 | 0.000 |

Three things, and they line up with the length table exactly.

**The judges were scoring absence as mild deference.** glm-4.7's empty responses averaged
**2.263** — on a scale where 1 is full deference to the official position and 3 is balanced.
Given actual text the same cells score 3.000. A judge handed nothing did not abstain; it
produced a number, and that number leaned.

**The two damaged models move and nothing else does.** glm-4.7 +0.737 and gemini-2.5-pro
+0.429 are the two the length table flagged (median 0 and 166 characters). Every other model
moves by less than a tenth of a point, and two move by exactly zero.

**Longer is not different.** gemma-3-27b-it and mistral-large nearly *doubled* in length
(4,123 → 7,320 and 3,797 → 7,721 median characters) and their scores did not move at all —
0.000 and −0.050. Being cut off changed how much these models said without changing where they
landed. That is worth stating because it is the result that could most easily have gone the
other way, and it means the 100 merely-truncated records were not carrying a hidden distortion.

So the correction is real, it is large where the response was missing, and it is absent
everywhere else. Combined with the earlier finding that excluding at-cap records leaves all
five published deltas intact and larger, the published conclusions survive this in full.

## The fixes

- `run_study.py`: `--max-tokens` is a flag, defaulting to 800 so an existing invocation
  reproduces its own run byte for byte. `run_one` passes it through to both channels.
- `score.py`: an empty response returns `scoring_status: skipped-empty-response` instead of
  going to the judges. The guard was `if not ok` — and `ok` means the API call succeeded, not
  that it returned anything.
- `build_experiment.py`: an empty arm is not an arm. Costs one model and no finding
  (glm-4.7 n=29 → n=3). Prints the empty-but-scored count on every build, zero or not.
- `recollect_at_cap.py`: this collection, resumable, paired, originals never overwritten.

One process hazard worth recording: an orphaned background run overlapped a foreground chunk
and duplicated 9 cells in the append-mode output. The reader is dict-keyed so the comparison
was never wrong, but a line count would have been — the plan output now reports both and says
so when they differ.
