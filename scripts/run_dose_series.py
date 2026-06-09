#!/usr/bin/env python3
"""The Wash — Experiment 1 dose-series driver.

Produces a sequence of abliterated copies of ONE base model at varying
`n_directions`, so we can measure judge-flinch and coherence as a function of
abliteration strength (the spine mechanism — TIER-B-DESIGN.md Experiment 1).

**Why this script exists** instead of just shelling out to
`python -m obliteratus abliterate`:

On Apple Silicon (M5, 34 GB unified memory), the OBLITERATUS CLI silently
degrades when its `psutil.virtual_memory().available * 0.70` signal falls
below `~4.6 GB` for a 9B model. The degradation:

  - max_seq_length drops 256 -> 128
  - batch_size drops 16 -> 8
  - spectral certification is skipped (insufficient activation data)

The result is a *degenerate* refusal direction that nukes the model
(perplexity=Infinity, coherence=0.0, empty generations) instead of a usable
abliteration. There is no CLI flag to override `max_seq_length` — only the
`Abliterator(max_seq_length=...)` constructor accepts it. The reference n_dir=4
spine on this same machine looks fine because RAM happened to be uncontested
when it ran; reproducibility cannot depend on that.

This driver imports `obliteratus.abliterate.Abliterator` directly so we can
pin `max_seq_length=512` and `verify_sample_size=30`, then runs the
`scripts/dose_smoke_gate.py` quality check before treating each dose as
"done." A failing dose is renamed `-FAILED-<ts>` and the series aborts.

Usage:
    python scripts/run_dose_series.py \\
      --base /path/to/gemma-2-9b-it \\
      --out-root abliteration-output \\
      --doses 1,2,8 \\
      --max-seq-length 512
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

# Reference n_dir=4 spine parameters from the bias-study writeup §4.2 /
# the-wash/RECIPE.md "spine provenance" table.
SPINE_DEFAULTS = dict(
    method="advanced",
    direction_method="svd",
    norm_preserve=True,
    regularization=0.3,
    refinement_passes=2,
    project_biases=True,
    use_chat_template=True,
    verify_sample_size=30,
)


def parse_doses(arg: str) -> list[int]:
    return [int(x) for x in arg.split(",") if x.strip()]


def run_one_dose(
    base: Path, out_dir: Path, n_directions: int, max_seq_length: int,
    device: str, dtype: str,
) -> int:
    # Late import so a bad --base / --out-root errors out before the model is
    # touched.
    from obliteratus.abliterate import Abliterator

    print(f"=== n_directions={n_directions} -> {out_dir} ===", flush=True)
    t0 = time.time()
    ab = Abliterator(
        model_name=str(base),
        output_dir=str(out_dir),
        device=device,
        dtype=dtype,
        n_directions=n_directions,
        max_seq_length=max_seq_length,  # the load-bearing override
        **SPINE_DEFAULTS,
    )
    # Abliterator.run() returns the abliteration result; we just need the
    # side-effect (output dir + metadata).
    ab.run()
    elapsed = time.time() - t0
    print(f"  n_directions={n_directions} produced in {elapsed/60:.1f} min", flush=True)
    return 0


def run_smoke_gate(dose_dir: Path) -> int:
    # Import the gate as a subprocess so its transformers/torch import doesn't
    # collide with the Abliterator's already-loaded model in this process.
    gate = Path(__file__).parent / "dose_smoke_gate.py"
    rc = subprocess.call([sys.executable, str(gate), str(dose_dir)])
    return rc


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--base", required=True, type=Path,
                   help="HF base model dir (e.g. models/gemma-2-9b-it)")
    p.add_argument("--out-root", required=True, type=Path,
                   help="Where to write each dose's output dir")
    p.add_argument("--doses", default="1,2,8", type=parse_doses,
                   help="Comma-separated n_directions values (default: 1,2,8 — "
                        "n_dir=0 is the unmodified base; n_dir=4 typically "
                        "already exists as the reference spine).")
    p.add_argument("--out-prefix", default="gemma-2-9b-it-dose",
                   help="Filename prefix for each dose dir (default mirrors "
                        "the bias-study convention)")
    p.add_argument("--max-seq-length", default=512, type=int,
                   help="Pinned activation collection length. The reference "
                        "spine used the default 256; 512 gives a safety "
                        "margin against the M5 memory-pressure auto-downgrade "
                        "to 128 that produces broken abliterations.")
    p.add_argument("--device", default="mps", help="torch device (default mps on M5)")
    p.add_argument("--dtype", default="float16")
    p.add_argument("--skip-existing", action="store_true", default=True,
                   help="If a dose dir already has abliteration_metadata.json, "
                        "skip it (default on; pass --no-skip-existing to force)")
    p.add_argument("--no-skip-existing", dest="skip_existing", action="store_false")
    p.add_argument("--skip-smoke-gate", action="store_true",
                   help="Skip the dose_smoke_gate.py check after each dose "
                        "(only for debugging; never use for a real run)")
    args = p.parse_args()

    if not args.base.is_dir():
        print(f"FATAL: --base {args.base} is not a directory", file=sys.stderr)
        return 2
    args.out_root.mkdir(parents=True, exist_ok=True)

    # On M5 you also want PYTORCH_ENABLE_MPS_FALLBACK=1 in the environment
    # for SSYEVD; we don't set it here so the caller stays in control of
    # the env (e.g. for CI runs where the fallback isn't wanted).
    if args.device == "mps" and not os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK"):
        print("WARNING: PYTORCH_ENABLE_MPS_FALLBACK is not set; Gemma-2 "
              "SSYEVD on MKL can fail. Recommend exporting "
              "PYTORCH_ENABLE_MPS_FALLBACK=1 before running.", flush=True)

    series_t0 = time.time()
    for n in args.doses:
        out_dir = args.out_root / f"{args.out_prefix}{n}"
        meta = out_dir / "abliteration_metadata.json"
        if args.skip_existing and meta.exists():
            print(f"=== n_directions={n} -> {out_dir} (SKIP, metadata exists) ===",
                  flush=True)
            continue

        rc = run_one_dose(args.base, out_dir, n, args.max_seq_length,
                          args.device, args.dtype)
        if rc != 0:
            print(f"FATAL: dose {n} abliteration returned {rc}", file=sys.stderr)
            return rc

        if not args.skip_smoke_gate:
            gate_rc = run_smoke_gate(out_dir)
            if gate_rc != 0:
                print(f"FATAL: dose {n} failed the smoke gate (rc={gate_rc}); "
                      f"aborting series. See the gate's output above for which "
                      f"check failed. The failed dir has been renamed -FAILED-<ts>.",
                      file=sys.stderr)
                return gate_rc

    print(f"=== series complete in {(time.time()-series_t0)/60:.1f} min ===",
          flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
