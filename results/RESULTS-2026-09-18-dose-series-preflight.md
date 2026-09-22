# The dose series is built and clean, and every dose is certified incomplete

**2026-09-18, M5.** No inference run. This is the preflight on weights that have been sitting
on this machine: what they are, whether the arms are comparable, and what the abliteration
tool's own verify stage already says about them.

Reproduce the gate with
`python scripts/dose_smoke_gate.py <dose_dir> --skip-generation --no-rename`.

## What exists

Five fp16 HF-safetensors directories under `~/claude/models-mlx/`, 17 GB each, 85 GB total:
`dose0-stock`, `dose2`, `dose4`, `dose8`, and an older single `abliterated` build.

**The arms are comparable, which is the whole premise of the design.** Checked rather than
assumed: all three ablated arms share an identical 18-layer target set (layers 24–41), method
`advanced`, direction method `svd`, 512 harmful and 512 harmless prompts, and **no field in
`method_config` differs except `n_directions`**. `dose4`'s metadata records its layers in
descending order and its source path relatively where the others are absolute — cosmetic, and
the layer *sets* are identical.

That retires, for these arms, the caveat attached to every ablation result this study has
published: that a third-party ablated build may differ from its base in ways beyond the refusal
direction. We built these.

## The metadata gate passes, and that is the weaker of the two signals

| dose | perplexity | coherence | gate |
|---|---:|---:|---|
| n=2 | 6.91 | 1.00 | PASS |
| n=4 | 7.87 | 1.00 | PASS |
| n=8 | 7.73 | 1.00 | PASS |

Coherence is 1.00 at every dose and perplexity never approaches the threshold. **No dose breaks
the model** — which answers the third pre-registered question in the negative for this range,
and means any refusal that survives is not survival-by-incoherence.

## Every dose is certified RED — refusal signal survives at n=8

`spectral_certification: RED` on all three. In OBLITERATUS the levels are not severity labels;
they are a random-matrix-theory diagnostic on post-abliteration residual activations, and RED is
defined in the source as:

> `RED = "incomplete"` — Clear eigenvalue spikes above threshold. Abliteration failed to remove
> all refusal signal. Re-run with more directions.

RED is distinct from `INCONCLUSIVE = "insufficient_samples"`, so this is a positive detection and
not a shrug. **The tool's own remedy for RED is "re-run with more directions", and going from two
to four to eight directions did not clear it.**

Beside that, its internal refusal rate on its own 512-prompt harmful set is **not monotonic**,
while KL divergence from the base rises cleanly:

| dose | KL divergence | tool's refusal rate |
|---|---:|---:|
| n=2 | 0.835 | 0.267 |
| n=4 | 1.272 | **0.167** |
| n=8 | 1.890 | **0.300** |

**Quadrupling the dose more than doubles the divergence from the base model and leaves the
refusal rate where it started.** More intervention, more damage to the weights, same refusal.

## What this does NOT establish

**These are the abliteration tool's verify-stage metrics, computed at build time, and this
study's own smoke gate says so in its docstring: a leading indicator, "NOT sufficient on its
own".** Nothing behavioural has been measured on these weights yet.

**The aggregate certification is worst-of-layers.** The source takes RED if *any* layer is RED,
and per-layer certificates are not stored in the metadata — so "RED" is consistent with one
stubborn layer out of eighteen as much as with global failure. That distinction matters and
cannot be recovered from what is on disk.

**The refusal rate above is measured on the tool's own harmful prompts, not on XSTest**, so it
is not comparable to the 0.49 and 0.72 unsafe-compliance figures from the published refusal
suite.

**n=1 is missing.** `PLAN-2026-08-29-dose-response.md` specifies n = 0, 1, 2, 4, 8; the built
series is 0, 2, 4, 8. The knee, if there is one, is most likely in the range the series skips.

## Two things caught by re-reading the study before trusting the run

**The pre-registration requires the replicate FIRST, and the first sweep order did not.**
`PREREG-2026-08-28-refusal-direction.md` is binding: *"Arm B counts as a constraint-layer effect
only if the between-arm difference exceeds the within-arm variation measured by re-running one
arm twice at the same settings. Run the replicate first."*

The published suite followed it — the constrained arm was run twice and **450 of 450 replies
came back byte-identical**, so its noise floor is exactly zero. **That result does not transfer
here.** It was measured on Ollama with the qwen38 pair; this sweep is in-process MLX on
gemma-2-9b — different backend, different model, different hardware path — and this study's
standing lesson is that the serving path moves the answer. The floor is being re-measured on
this configuration as arm 2 of 5, before any between-dose difference is read. Caught after 23
prompts; nothing was lost, because the driver resumes by id.

**A dtype confound that looked real and is not.** `dose0-stock`'s `config.json` declares
`torch_dtype: bfloat16` while the dose arms declare `float16`, and the baseline lacks the
`layer_types` and `rope_parameters` keys the others carry — the configs were written by
transformers 4.42 and 5.9 respectively. Given that requantisation alone moves 2–10 items of 62
in this study's own floor table, a bf16 baseline against fp16 treatment arms would have
confounded the entire curve.

It does not, and the check is worth recording rather than the conclusion alone:

- **The stored tensors are `F16` in all four arms.** Read from the safetensors headers, not from
  the config. The `bfloat16` line is stale metadata the MLX conversion carried over from the
  original download; it does not describe the weights on disk.
- **mlx_lm's gemma2 `ModelArgs` does not read `torch_dtype`, `dtype`, `layer_types`,
  `tie_word_embeddings` or `rope_parameters` at all.** The one field that could have bitten is
  `rope_theta`: the baseline states 10000.0 explicitly and the doses omit it in favour of
  `rope_parameters`, where mlx_lm's default is 10000 — the same value.
- **Every field mlx_lm does read is identical across all four arms**, checked field by field
  with the defaults applied.

So the arms are matched under this backend, and the baseline is usable. The differing configs
are inert.

## What is next, and what it costs

The behavioural arm: XSTest, 450 matched prompts, at each dose, temperature 0, fixed seed, with
discrimination = compliance(safe) − compliance(unsafe) reported with both components.

That needs an inference runtime this machine does not currently have — no `mlx`, no `torch` in
any interpreter here — and four passes over a 17 GB model in 32 GB of unified memory. The
weights and the probe both already exist; nothing needs collecting.

---

# Correction, 2026-09-19 — the preflight cleared the arms on the wrong evidence

Re-checked at the level of the weights themselves rather than the metadata, in response to a
direct challenge to whether this series is running the right models. Three findings, one of them
a confound this document explicitly cleared.

## C1. `dose4` is not a member of this build run. It is the 2026-05-27 build, relabelled.

Above, at line 18, this document noticed that `dose4`'s metadata lists its layers in descending
order where `dose2` and `dose8` ascend, and dismissed it because "the layer sets are identical."
The ordering is not cosmetic. It is the fingerprint of a different invocation, and the weights
confirm it:

| | SHA-256 over all safetensors | built |
|---|---|---|
| `abliteration-output/gemma-2-9b-it-abliterated` | `4032e508e5d28ad7` | **2026-05-27 19:52** |
| `abliteration-output/gemma-2-9b-it-dose2` | `3524695c1c65db27` | 2026-06-09 17:51 |
| `abliteration-output/gemma-2-9b-it-dose8` | `894292dd585672a0` | 2026-06-09 18:15 |
| `models-mlx/gemma-2-9b-it-dose4-mlx` | **`4032e508e5d28ad7`** | copied 2026-06-09 18:24 |

**There is no `gemma-2-9b-it-dose4` in `abliteration-output/`.** It was never built. The dose4 arm
is a byte-identical copy of the general `abliterated` build, whose `method_config` does record
`n_directions: 4`, so the *label* is honest — but it was produced thirteen days earlier by a
separate invocation, and its metadata differs in form (`source_model` relative, not absolute;
layers descending, not ascending). All four `models-mlx` dose directories were created within
30 seconds of each other at 18:23:55–18:24:25, which is a copy, not four ablations.

No metadata file records a tool version or git revision, so **it cannot be shown that the tool
was unchanged across those thirteen days.** The dose series therefore varies build provenance
alongside `n_directions` at exactly one point, and that point is the middle of the curve.

This does not invalidate anything collected. dose4 is a real n=4 ablation of the same base. But
the sentence this series wants to write — "only the number of ablated directions differs" — is
not true as built, and the result document must say so.

**Remedy, queued rather than run:** rebuild dose4 from `models/gemma-2-9b-it` on the current
tool at the same config. Cheap, and it doubles as a reproducibility test the study wants anyway —
if the rebuild is bit-identical to the 05-27 build, provenance is moot and that is a result; if
it is not, the confound is real and measured. **Not run now: this plan's own Sequencing section
holds the GPU exclusive, and collection is live.** dose4 is arm 5 of 5, so there is time.

## C2. The dose axis is not proportional to the dose, and it saturates

`n_directions` 2/4/8 reads as 1×/2×/4×. Measured as relative Frobenius norm of the weight change
against `dose0-stock`, over all 464 tensors:

| arm | rel. Frobenius Δ | vs dose2 | tool's own KL | tool's own refusal rate |
|---|---|---|---|---|
| dose2 | 6.579e-2 | 1.00× | 0.835 | 0.267 |
| dose4 | 1.485e-1 | 2.26× | 1.272 | 0.167 |
| dose8 | 1.615e-1 | **2.45×** | 1.890 | 0.300 |

Nominal 4× is an actual 2.45×, and **dose8 is only 8% more perturbation than dose4** despite
twice the directions. The intervention saturates between 4 and 8. KL is monotone where the
perturbation norm nearly flattens, and the tool's own refusal rate is non-monotonic across both.

Plotting an outcome against `n_directions` therefore plots it against the wrong x-axis. The
result document should carry the measured perturbation (and KL) as the dose, with `n_directions`
as the nominal label. This also re-frames D1: the case for building n=1 is stronger than "fill a
gap," because the interval 0→2 contains most of the usable range.

## C3. 99.7% of the change is in the embedding matrix, not the eighteen "strong layers"

Per-tensor, `dose0-stock` vs `dose2`: 127 of 464 tensors differ — `model.embed_tokens.weight`
plus 7 tensors in each of layers 24–41 (`q/k/v/o_proj`, `gate/up/down_proj`; note this is every
projection, not only the residual-stream writers that the Arditi formulation orthogonalises).
Layers outside 24–41 are untouched, exactly as documented.

But by magnitude the layer edits are almost nothing:

| arm | rel. Δ, embed_tokens | rel. Δ, all layers | embed share of total Δ² |
|---|---|---|---|
| dose2 | 9.90e-2 | 6.16e-3 | **99.5%** |
| dose4 | 2.24e-1 | 8.81e-3 | **99.8%** |
| dose8 | 2.43e-1 | 1.23e-2 | **99.7%** |

This document, the plan, and the tool's own metadata all foreground the eighteen strong layers.
That framing describes a third of a percent of the intervention by norm. Whatever this series
measures, it is dominated by an edit to the embedding matrix — a consequence of `project_biases`
and `norm_preserve` in the config, not a defect, but not what the write-up currently implies
either. Any mechanistic claim about *where* refusal lives that leans on the layer set is not
supported by these weights.
