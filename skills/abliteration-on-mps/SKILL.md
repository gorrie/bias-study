---
name: abliteration-on-mps
description: Run an OBLITERATUS refusal-direction abliteration on Apple Silicon (M5 / Mac with ≥ 32 GB unified memory), using the Python driver that pins max_seq_length to avoid the M5-specific silent-degradation failure mode. Use this skill (not abliteration-run) whenever the host is Apple Silicon, especially for Gemma-2 family (the 4090's MKL SSYEVD fails on Gemma-2 → abliteration MUST run on M5). Produces the same HF safetensors directory shape as abliteration-run; downstream tooling treats both identically.
---

# abliteration-on-mps

The M5-specific abliteration path. Same output shape as the Docker/CUDA path
in [`abliteration-run`](../abliteration-run/SKILL.md), but driven from Python
instead of the CLI because the CLI has a known silent-degradation failure on
Apple Silicon under any memory pressure.

This skill is also the **only viable path for Gemma-2 family** abliteration:
the 4090's MKL `SSYEVD` SVD step fails on Gemma-2 (documented in
[`mlx-weight-prep`](../mlx-weight-prep/SKILL.md) hard lessons). Apple's
Accelerate/LAPACK doesn't share the bug — the M5 is the only place Gemma-2
abliteration can complete.

## TRIGGER when
- The host is Apple Silicon (any M-series).
- A Gemma-2 family model needs to be abliterated (other paths fail on it).
- The Wash Experiment 1 dose-response series (`--n-directions ∈ {1,2,4,8}` for
  one base model — the spine mechanism test) is being run.
- Author asks to "abliterate on the M5", "produce the dose series", or names
  Gemma-2 as the target.

## SKIP
- The host is Linux/Windows with a working CUDA GPU → use the
  [`abliteration-run`](../abliteration-run/SKILL.md) Docker/CUDA path
  instead. It's faster and has battle-tested defaults.
- The model is *not* Gemma-2 family AND a CUDA box is available → also
  prefer the CUDA path. M5 abliteration is slower (~15–25 min/dose for 9B
  vs ~5–10 min on a 4090).

## Preconditions
1. M5 / Apple Silicon with **≥ 32 GB unified memory** (a 9B model is ~19 GB
   at fp16; the abliteration also needs activation cache).
2. OBLITERATUS installed in the project venv:
   ```bash
   git clone https://github.com/elder-plinius/OBLITERATUS ~/external/OBLITERATUS
   pip install -e ~/external/OBLITERATUS
   pip install -r ~/external/OBLITERATUS/requirements-apple.txt
   ```
3. HF base weights present locally (e.g. `models/gemma-2-9b-it/`).
4. The `PYTORCH_ENABLE_MPS_FALLBACK=1` env var must be set — Gemma-2's SVD
   step hits a `linalg.eigh` MPS edge case that needs the LAPACK fallback.
5. `scripts/run_dose_series.py` and `scripts/dose_smoke_gate.py` present
   (since the commit that landed this skill — `git log scripts/run_dose_series.py`).

## Procedure (verified before the next — no walk-away)

### 0. Free up RAM before starting

The OBLITERATUS memory check reads `psutil.virtual_memory().available * 0.70`.
If other large processes (browsers, IDEs, other Python workers) are holding
RAM, the abliterator's *internal* defaults degrade. **The driver in step 2
pins `max_seq_length=512` to defeat the degradation**, but the abliteration
itself still needs ~25 GB free for a clean 9B run. Quit big apps before
launching.

### 1. Confirm the toolchain loads

```bash
cd /path/to/gorrie/bias-study
.venv/bin/python -c "
import obliteratus; print('obliteratus', obliteratus.__version__)
import mlx_lm; print('mlx_lm', mlx_lm.__version__)
import torch; print('mps:', torch.backends.mps.is_available())
"
```

Expect three lines printing versions and `mps: True`. If `mps: False`, the
torch install is wrong (probably the Linux wheel) — reinstall from the Apple
Silicon arm64 wheel.

### 2. Run the dose-series — supervised (recommended for hands-off runs)

```bash
PYTORCH_ENABLE_MPS_FALLBACK=1 \
  nohup .venv/bin/python scripts/supervised_dose_series.py \
  --base /path/to/models/gemma-2-9b-it \
  --out-root abliteration-output \
  --doses 1,2,8 \
  --max-seq-length 512 \
  --stall-timeout 600 \
  --max-attempts 3 \
  > supervisor.log 2>&1 &
disown
```

The supervisor wraps the bare `run_dose_series.py` driver and adds the
recovery logic the driver doesn't have on its own. Failure-kind handling:

| Kind | Detection | Policy |
|---|---|---|
| **crash** | subprocess exits non-zero after the startup grace window | retry up to `--max-attempts`; skip-existing recovers |
| **hang** | no new log line for `--stall-timeout` seconds | SIGKILL the process group, retry up to `--max-attempts` |
| **smoke_fail** | driver exited non-zero AND a `*-FAILED-*` dir was created | HALT — broken model needs human attention, retry would just produce another broken model |
| **startup** | subprocess crashed within first 60 s (ImportError, TypeError, …) | HALT — code bug or environment problem, not transient |

State persists to `<out-root>/.dose-supervisor-state.json` and a heartbeat
file updates every 5 s — so a different shell, a fresh Claude session, or
an external cron job can read state cold without re-deriving anything:

```bash
.venv/bin/python scripts/supervised_dose_series.py --status \
  --state-dir abliteration-output
```

To resume after fixing the root cause of a halt:

```bash
.venv/bin/python scripts/supervised_dose_series.py \
  --base ... --out-root abliteration-output --doses 1,2,8 \
  --resume-halted
```

### 2a. Run the dose-series — unsupervised (debugging only)

When you actively want to watch a single run finish or fail (debugging the
abliteration itself, not the supervisor), bypass the supervisor:

```bash
PYTORCH_ENABLE_MPS_FALLBACK=1 \
  .venv/bin/python scripts/run_dose_series.py \
  --base /path/to/models/gemma-2-9b-it \
  --out-root abliteration-output \
  --doses 1,2,8 \
  --max-seq-length 512
```

Same skip-existing, same smoke gate. No hang detection, no retry budget,
no state file. **Not** the right entry point for an overnight run.

**Why `--max-seq-length 512`?** The OBLITERATUS CLI has no flag to set this
and the internal default drops to **128** when free RAM looks tight — which
on M5 it often does. That truncation produces a degenerate refusal direction
and breaks the model. The Python API exposes the kwarg; the driver pins it.
The reference n_dir=4 spine in `abliteration-output/gemma-2-9b-it-abliterated/`
was produced with the default (256) when RAM was uncontested — and is fine —
but reproducibility cannot depend on RAM being uncontested.

### 3. Verify each dose

The driver does this automatically via `scripts/dose_smoke_gate.py`. The gate
has two independent checks:

| Gate | What it does |
|---|---|
| **metadata** | Reads `abliteration_metadata.json`; requires `quality_metrics.perplexity < 50` and `coherence > 0.5`. (Healthy 9B: perplexity ~7–15, coherence 1.0.) |
| **generation** | Loads the model on MPS, runs a 3-prompt fixed-seed sanity battery ("Capital of France?" → `Paris`; "2+2?" → `4`; "Name a prime." → any prime). |

If either gate fails, the dose dir is renamed `<dose>-FAILED-<unix-ts>` and
the driver exits non-zero. **Do not delete a `-FAILED-` dir** before
investigating — the failure mode tells you what's wrong (mostly: memory
pressure during activation collection).

Manual re-verify any dose by hand:

```bash
.venv/bin/python scripts/dose_smoke_gate.py \
  abliteration-output/gemma-2-9b-it-dose1
```

### 4. Hand off to MLX conversion

For each healthy dose dir, run [`mlx-weight-prep`](../mlx-weight-prep/SKILL.md)
to produce the MLX fp16 weights consumed by
[`abliterated-judge-sweep`](../abliterated-judge-sweep/SKILL.md) for the
flinch calibration.

## Recovery from failure

| Symptom | Cause | Fix |
|---|---|---|
| `perplexity=Infinity, coherence=0.0` | M5 RAM was tight during activation collection. Driver's `--max-seq-length 512` didn't help → other large processes are stealing RAM. | Quit browsers/IDEs/other Python; re-run. The driver's skip-existing will pick up at the failed dose. |
| Generation gate fails on a metadata-OK model | Verify stage was lucky; the model is still broken on real prompts. | Treat as the symptom above. The 2-gate design exists because metadata-only is not enough. |
| OOM during abliteration | 9B fp16 + activations exceeds available unified memory. | Either: (a) reduce `--max-seq-length 256` (still avoids the 128 trap but uses less memory), or (b) move to a 7B base for the dose series. |
| `RuntimeError: SSYEVD` | `PYTORCH_ENABLE_MPS_FALLBACK=1` wasn't set. | Export it and re-run. |
| Driver hangs at "Verification complete" with no output | Abliterator finished but didn't write the metadata. Almost always a disk-full issue (each output is ~20 GB). | Check `df -h abliteration-output/`; clear space; re-run. |

## Hard lessons (do not relearn)
- **The CLI silently lies on Apple Silicon.** A successful exit from
  `python -m obliteratus abliterate ...` is *not* evidence of a working
  abliteration on M5. The smoke gate is load-bearing; never skip it for a
  real run.
- **The Python `max_seq_length=512` kwarg is the one knob that matters.** Do
  not refactor the driver to "simplify" by calling the CLI; you will
  reintroduce the silent failure.
- **OBLITERATUS writes to stdout via `rich.live`** during its compute phases,
  which updates a single terminal line in place and writes nothing new to the
  log file for the full duration of activation collection + verify. The
  verify stage alone takes ~800s on Gemma-2-9B with zero new log lines. A
  log-mtime-only stall watchdog declares hang on a process that is computing
  flat-out. The supervisor uses BOTH log-mtime AND subprocess CPU-time
  activity (via `psutil.Process.cpu_times().user` walked across the process
  tree) — only declares hang when both are static, which is the actual
  invariant. Default `--stall-timeout` was raised from 600s to **1500s** for
  the same reason; do not lower it without first measuring how long the
  verify stage takes for your specific base model + n_directions combo.
- **The supervisor's `--resume-halted` resets per-dose attempt counters.**
  Without that reset, a halted-then-resumed run walks straight back into
  "exhausted" on the same dose because attempts is sticky. Resume = "I have
  fixed the root cause; give this dose three fresh attempts." If you do NOT
  want that semantic, use `--reset` (which wipes the whole state file) or
  edit the JSON by hand.
- **`knee_cosmic` layer selection varies the projected-layer count per
  n_directions** — on Gemma-2-9B it picked 22 layers at `n_dir=1` and 18 at
  `n_dir=4`. Projecting one direction across 22 layers (vs four across 18)
  destroyed the model: perplexity=∞, coherence=0, empty generations.
  **Pin `--strong-layers 24-41`** (the reference spine's range) across the
  whole dose-series so the dose-response measures `n_directions` alone, not
  `n_directions + algorithm-picked layer count`. Default in
  `scripts/run_dose_series.py` and `scripts/supervised_dose_series.py` is
  `24-41`; the driver monkey-patches `_select_layers_knee` /
  `_select_layers_cosmic` / `_select_layers_middle60` / `_select_layers_all`
  on the pipeline instance so whichever selection_method the underlying
  algorithm picks, the forced list wins. Pass an empty string `--strong-layers
  ""` only when you specifically WANT the OBLITERATUS heuristic to choose
  (e.g. for a new base model where you don't have a reference layer set).
- **Memory pressure produces a non-terminating swap-thrash failure mode.**
  Observed: dose-1 attempt ran 1h29m at 7% CPU, MPS reporting 0 GB allocated,
  20 GB safetensors I/O grinding through 868 MB free swap, log idle 88 min.
  The CPU-aware watchdog saw "CPU advancing" and stayed its hand — but the
  process would never have finished in this lifetime. Two defenses:
  (1) **Pre-flight memory check**: supervisor refuses to start a dose unless
  `--min-free-gb` (default 25) is free, waits 60s for a transient consumer
  to release, then halts. (2) **Wall-clock backstop** at `MAX_WALL_CLOCK_S`
  (60 min, 4× the observed 15-min clean run): kills any attempt past that
  even if CPU was advancing. The CPU-aware watchdog catches genuine silent
  compute; the wall-clock backstop catches the "alive but functionally
  non-terminating" case the CPU watchdog can't see. Before launching, quit
  Discord / Claude desktop / browsers with heavy tabs — these are the usual
  memory consumers that push the M5 from "enough" to "swapping."
- **Quantization is not a workaround on M5.** `--quantization 4bit/8bit`
  requires bitsandbytes, which is CUDA-only and silently disables on MPS.
- **`PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0` does NOT fix the degradation.**
  OBLITERATUS reads `psutil.virtual_memory().available`, not PyTorch's MPS
  allocator state. The watermark env var changes nothing here.
- **Sequential, not parallel.** Two abliterations both fighting for MPS
  produces non-deterministic results AND massively slower wall-clock.

## Cross-references
- [`abliteration-run`](../abliteration-run/SKILL.md) — the Docker/CUDA path for non-Gemma-2 families on a CUDA box.
- [`mlx-weight-prep`](../mlx-weight-prep/SKILL.md) — converts each healthy dose's HF dir to MLX for serving.
- [`abliterated-judge-sweep`](../abliterated-judge-sweep/SKILL.md) — consumes the MLX-converted dose to measure flinch.
- The Wash docs in the working copy at `evil-robots-series/research/the-wash/`: `TIER-B-DESIGN.md` (why we run a dose-series at all), `PROTOCOL.md` (the analysis rules), `HANDOFF-M5.md` (the M5 run sequence).
