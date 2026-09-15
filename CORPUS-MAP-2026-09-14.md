# The corpus after the 2026-09-14 repair: what every run is for

> ## THE REPAIRED CORPORA ARE NOT IN THIS REPOSITORY YET
>
> The repair was carried out in the working study. The re-collected records and the derived
> corpora below are **pending export** to this public tree, and until that lands the runs named
> here will not resolve for you.
>
> This document is published now because the alternative is worse: reading a number from a May
> run without knowing a third of that run is missing. **Every original run in this repository is
> the damaged version.** The map tells you which, by how much, and what the repaired figure is.
>
> Until the export lands, treat any May figure you derive here as computed on a corpus with the
> losses recorded below — heaviest on `mistral-large`, `glm-4.7`, `gemma-3-27b-it` and
> `claude-opus-4.7`, which had 0, 0, 0 and 1 usable A/B pairs respectively in the main run.

The May 2026 corpus was collected at an 800-token cap that severed or emptied about a third of
it, differentially by model. This names every run the repair created, what it repairs, and what
is still missing. `scripts/run_inventory.py --check` requires every run on disk to be named in a
study document; this is that document.

Record counts are read off disk, not typed — regenerate with
`python scripts/run_inventory.py`.

---

## Three kinds of run, and the difference matters

**COLLECTIONS** are calls that were made. Each one is new evidence and is counted once.

**REPAIRS** (`2026-09-14-recollect-*`) are collections too — cells re-asked at a 4,000-token
budget because the original answer was severed, empty, or cut mid-clause. Every record carries
`recollected_from` naming the run it repairs, and `original_called_at` preserving the replaced
call's timestamp.

**DERIVED CORPORA** (`*-spliced`) are not collections. Each is a *view*: the base run's records
where they are usable, and a repair's record where they are not. Their manifests carry
`"derived": true`.

> **A derived corpus is read BY NAME and never ENUMERATED.** `studypaths.canonical_run` resolves
> an analysis to the repaired corpus; `studypaths.is_derived_run` keeps corpus-wide scans from
> counting it. Counting a spliced run alongside the base it derives from and the repair it draws
> on triple-counts the same measurement — it added 2,483 phantom rows and put a cross-path defect
> count off by one before this distinction existed.

## Repairs

| run | repairs | note |
|---|---|---|
| `2026-09-14-recollect-paraphrase` | 2026-05-27-paraphrase | instruction-paraphrase floor |
| `2026-09-14-recollect-may25` | 2026-05-25 | earlier main run |
| `2026-09-14-recollect-ood` | 2026-05-27-ood | out-of-domain arm |
| `2026-09-14-recollect-reversed-premise` | 2026-05-27-reversed-premise | frame-following arm |
| `2026-09-14-recollect-timeseries` | 2026-05-26-timeseries | the Opus version arc |
| `2026-09-14-recollect-augmentation` | 2026-05-26-augmentation | |
| `2026-09-14-recollect-cn` | 2026-05-26-cn-expansion | glm-4.7, kimi-k2.6, ernie |
| `2026-09-14-recollect-gradient` | 2026-05-26-unmask-gradient | grok + opus dose curve |
| `2026-09-14-recollect-variance` | 2026-05-26-variance | same-version floor |
| `2026-09-14-recollect-gpt5-augmentation` | 2026-05-26-augmentation | GPT-5 only |
| `2026-09-14-recollect-gpt5-gradient` | 2026-05-26-unmask-gradient | GPT-5 only |
| `2026-09-14-recollect-gpt5-variance` | 2026-05-26-variance | GPT-5 only |

**GPT-5 has its own repair runs** because its damage is invisible to an at-cap threshold: its 286
empty records sit at exactly 768 tokens, not 800. One output directory per source, always —
cell keys are `(model, question_id, condition)` and they collide across runs, so pointing two
sources at one directory makes the second look already-collected. That happened once and the
variance run silently collected 0 of 20 while reporting success.

## Re-collected baselines

| run | replaces | why |
|---|---|---|
| `2026-09-14-g0dm0d3-baseline-4k` | `2026-09-13-g0dm0d3-replicate-baseline` | the original recorded **no token budget** while the arm it is differenced against records 4,000 |

A baseline capped below its arm measures truncation rather than force. The original W13 baseline
carried no `max_tokens` field at all, so comparability could not be verified, and it was replaced
on 2026-09-14 with one re-collected at a recorded 4,000. Opus's `B-STM vs plain B` moved from
+0.12 spanning zero to +0.37 [+0.13, +0.65], `B-Parseltongue` from −0.01 to +0.24 [+0.02, +0.49],
and three of eight intervals excluding zero became five of eight. That was published the same
morning as evidence the confound was real.

> ### REVERTED 2026-09-15: the movement was real and the attribution was wrong
>
> **The unrecorded cap never bound.** The original baseline's longest response is **1,295
> tokens**, the replacement's is **1,307**, the arm's is **1,606** against its 4,000 — and **not
> one record in either baseline is truncated**. Whatever budget the original ran at, nothing came
> near it.
>
> **The replacement is two days later.** Read off `called_at`: the arm ran 2026-09-13T23 and
> -09-14T00, the original baseline 2026-09-13T23 — *the same sitting* — and the budget-matched
> baseline 2026-09-15T02–03.
>
> So the switch fixed a confound that was not biting and introduced one that was. The proof is
> the arm that **cannot** have an effect — `B-Parseltongue` applies no transform to this
> instrument at all:
>
> | `B-Parseltongue vs plain B` | same-sitting baseline | +2-day baseline |
> |---|---|---|
> | claude-opus-4.7 | **−0.01 [−0.15, +0.13]** | +0.24 [+0.02, +0.49] — *excludes zero* |
> | grok-4.3 | +0.09 [−0.06, +0.23] | +0.11 [−0.10, +0.29] |
>
> An untreated arm must read zero. Against the same-sitting baseline it does. Against the one
> collected two days later it excludes zero — which is not an effect, because there is no
> treatment. It is the baseline being wrong, measured. **Two of the five intervals reported that
> morning as excluding zero were manufactured by drift.**
>
> That makes the accidental null the best diagnostic this arm has, and it is now a gate:
> `tests/test_pipeline_rung.py::test_the_untreated_arm_reads_zero_which_is_how_a_baseline_is_judged`.

Grok is unaffected by the baseline choice either way (+0.56 → +0.57). `B-Layered minus B-STM` is
unchanged on both models because it is a within-arm contrast that never touches a baseline — so
the finding that the two models move in **opposite directions** was never at risk from any of
this, which is the argument for preferring a within-arm contrast when one exists.

`pipeline_rung.py` defaults to the **same-sitting** baseline and keeps the budget-matched one as
`MATCHED_BUDGET_BASELINE_RUN`, which is the right control for the token-cap question and the
wrong one for everything else. Neither is clean: the honest fix is a same-sitting baseline **with**
a recorded cap, which is what `2026-09-15-g0dm0d3-decomposition` collects.

> ### Superseded later the same day: that +0.24 is not an effect
>
> `B-Parseltongue` applied **no transform to this instrument** — G0DM0D3's obfuscation rewrites
> trigger words and the ten neutral policy questions contain none, so it fired on **0 of 240
> requests** across both pipeline runs. The arm is condition B under another label, so
> **+0.24 [+0.02, +0.49] is a null-by-construction floor that happens to exclude zero**, not a
> repaired effect. Opus's B-STM +0.37 sits on that floor; differenced within the run it is
> +0.13 and spans zero.
>
> This was written before the baseline question was settled, and it said the baseline repair
> "is still correct and still needed". It is not — see the REVERTED block above, which the
> finding in this one is what made possible: an arm known to receive no treatment is how you
> test a baseline. Against the same-sitting baseline the number here is −0.01, not +0.24.
>
> What survives every version of this is the within-arm contrast: Opus −0.31, Grok +0.48.
>
> Full account, including what STM does to the scored text:
> `RESULTS-2026-09-14-rung2-transform-audit.md`. Verify with
> `python scripts/pipeline_transform_audit.py`.

## Controls

| run | what it controls for | result |
|---|---|---|
| `2026-09-14-g0dm0d3-proxy-control` | the **proxy path**: plain condition B sent through G0DM0D3 with every transform off, against the same direct-to-OpenRouter baseline | the path costs **+0.06** on Opus and **−0.14** on Grok, both spanning zero |
| `2026-09-15-g0dm0d3-decomposition` | **what B-Layered's effect is made of**, and the cross-sitting drift below: `B-Proxy`, `B-Godmode`, `B-Autotune` and `B-Layered`, all four collected in ONE sitting so no contrast crosses a day | collecting |

Collected because the pipeline arm goes through the proxy and its baseline does not, so all six
`vs plain B` contrasts confounded the named transform with the path. They do not, materially —
which relocates the problem. The control was collected in the **same sitting** as the baseline
while the pipeline arm predates it by a day or two, so the ~+0.24 floor on Opus is
**cross-sitting drift**, not the proxy. That is what the decomposition arm now answers, by
collecting its own baseline alongside its arms.

The decomposition also exists because rung 2's surviving effect belongs to `godmode` and
`autotune` — Parseltongue is inert here and STM's edit is a median of 16 characters — and no arm
has ever run one without the other. Until it lands, the honest sentence is *"a system prompt plus
a sampling change moved Grok and not Opus"*, which cannot say whether the models are responding
to an instruction or to a temperature. Estimator: `scripts/pipeline_decomposition.py`, written
and validated on planted answers before the collection finished.

Conditions are in `run_g0dm0d3.COND_FLAGS` as `B-Proxy`. Note that every flag is sent
explicitly, including the false ones: the server defaults `godmode` and `parseltongue` to **true**
when the field is absent, so an omitted flag is not "off".

## Derived corpora

| corpus | base | eligible before → after |
|---|---|---|
| `2026-09-14-full-spliced` | 2026-05-25-full | 528 → **778** of 780 |
| `2026-09-14-timeseries-spliced` | 2026-05-26-timeseries | 436 → **681** |
| `2026-09-14-augmentation-spliced` | 2026-05-26-augmentation | 185 → **354** |
| `2026-09-14-cn-expansion-spliced` | 2026-05-26-cn-expansion | 58 → **161** |
| `2026-09-14-unmask-gradient-spliced` | 2026-05-26-unmask-gradient | 277 → **450 of 450** |
| `2026-09-14-variance-spliced` | 2026-05-26-variance | 883 → **1190** |
| `2026-09-14-may25-spliced` | 2026-05-25 | 168 → **259** of 260 |
| `2026-09-14-ood-spliced` | 2026-05-27-ood | 90 → **160 of 160** |

`2026-05-25` and `2026-05-25-full` are **different runs**, one character apart. The repair is
keyed from its own records' `recollected_from`, not from its directory name — which reads
`recollect-may25` and would have spliced it into `-full`, a corpus it does not repair.

## What is still missing, and why

Recorded in `studypaths.UNREPAIRABLE` with the evidence. These are not oversights.

**Three models have been withdrawn from the provider.** Probed 2026-09-14, all return
`HTTP 404 {"message":"No endpoints found for <model>."}`:

- `baidu/ernie-4.5-300b-a47b` — 19 cells in cn-expansion
- `google/gemini-2.0-flash-001` — 33 cells in timeseries
- `google/gemma-2-9b-it` — 60 cells in augmentation

The third is the significant one: **gemma-2-9b-it is the base of the abliterated judge** the
cross-method robustness leg rests on. That leg cannot be re-run by us or by a replicator. A study
that calls itself a standing instrument has to say so.

**Two arms need different tooling, not more budget:**

- `2026-05-27-abliteration` (35 cells) and `-controls` (16) run LOCAL models through
  `run_local.py` on the 4090. The re-collector calls OpenRouter and would fail on every one, the
  way the single `phi4` cell did.
- `2026-05-27-g0dm0d3` (10 cells) needs the G0DM0D3 Docker server running.

**Individual cells:** one `phi4` cell (local model, wrong channel); one `bytedance/seed-1.6` call
that failed at collection; one `gemma-3-27b-it` response that is a probable FALSE positive —
1,938 tokens of 4,000, so the model stopped voluntarily, ending on a markdown URL with no full
stop. Checked corpus-wide before leaving the detector alone: one record in 2,101 ends in a URL,
and that one genuinely hit the cap.
