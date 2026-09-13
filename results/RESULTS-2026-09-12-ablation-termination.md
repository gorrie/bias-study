# Why 24 of 63 ablation cells came back short, and what it says about abliteration

**2026-09-12.** No new collection. The ablation wave has been on disk since September 7 with
39 of 63 cells reaching n=5, and nobody had asked why the other 24 did not. Reproduce with
`python scripts/ablation_termination.py`.

## The answer is not stance, and it is not uniform

| base | stock median tokens | ablated median | ratio | ablated runs at the 8192 cap |
|---|---:|---:|---:|---|
| gemma2-9b | 321 | 319 | 1.0× | 0/15 |
| gemma2-9b-q8 | 317 | 319 | 1.0× | 0/15 |
| gemma4-12b | **8192** | 7570 | 0.9× | 13/28 |
| **llama31-8b** | 296 | **8192** | **27.7×** | **10/10** |
| **llama31-8b-q8** | 306 | **8192** | **26.8×** | **9/9** |
| phi4-14b | 320 | 321 | 1.0× | 0/15 |
| qwen25-14b | 343 | 332 | 1.0× | 0/45 |
| qwen38-27b | 2895 | 2447 | 0.8× | 1/43 |

**Abliteration did not change output length on five of eight bases.** Four sit at 1.0× and
`qwen38-27b`'s ablated build is *shorter* than its stock.

**On `llama3.1-8b` it destroyed termination completely.** Stock answers the instrument in about
300 tokens. Every single ablated run — 19 of 19 across two quantisations — runs to the 8192
ceiling and is recorded budget-exhausted or transport-failed. Not one produced a usable answer.

Both quantisations failing identically **rules out the serving stack**: Q4 and Q8 are different
builds of the same ablation and both are total. That is as close to attribution as this design
gets.

`gemma4-12b` is a different story and must not be read as an ablation effect: **its STOCK arm is
already at the cap.** That base cannot complete the instrument at all, ablated or not.

## Why this matters beyond the missing cells

**It is a second, independent instance of the pattern this study already found in stance.** The
ablator-spread control showed that `qwen25-14b`'s apparent stance effect was build-specific: two
builds by one author agree at 0/0/0 side-flips, either against a third author's build gives
8/9/9. Here the same shape appears in a completely different measurement — generation length —
and lands on a different base.

Effects attributed to "abliteration" keep turning out to be properties of *particular ablated
builds*. That is now true in two unrelated measurements, which is worth more than either alone.

**And it is a selection effect in the arm itself.** The ablation arm has no `llama3.1-8b` data,
and that absence is *caused by the intervention being studied*. The models that survive
abliteration well enough to be measured are not a random sample of the models that were
abliterated. Any claim of the form "abliteration does not move stance" is conditioned on the
model still being able to finish a sentence.

## What this does NOT establish

It does not show abliteration causes verbosity in general — five of eight bases show no effect
at all, and the honest headline is the spread rather than the maximum.

It does not identify a mechanism. These are third-party builds whose layer choice, refusal set,
intervention strength and quantisation are undocumented and differ, which is the same limit the
stance analysis carries. "The `wash-llama31-8b-ablit` build cannot terminate" is supported.
"Removing a refusal direction from llama3.1-8b causes runaway generation" is not — nobody has
shown these builds do only that.

The remedy is the one already queued: do the abliteration ourselves, at a pinned base with
controlled edit strength and matched serving, so the artifact and the intervention stop being
the same unknown.
