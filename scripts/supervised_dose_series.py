#!/usr/bin/env python3
"""Supervised wrapper around run_dose_series.py.

`run_dose_series.py` is fine when nothing goes wrong. This wrapper exists
because something usually does. The failure modes we observed on M5 during
the Wash dose-response work:

  1. **process crash** — subprocess exits non-zero (OOM, transient PyTorch
     error). Safe to retry: `run_dose_series.py` skip-existing recovers.
  2. **process hang** — subprocess is alive (STAT=UN, holding MPS) but no
     log line for tens of minutes. Neither the smoke gate nor the per-line
     Monitor catches this; it just looks like the run is taking a long time.
     Safe to retry after kill.
  3. **smoke-gate failure** — the driver itself exits non-zero because a
     dose's output failed `dose_smoke_gate.py`. NOT safe to retry blindly:
     the abliteration came out broken, and re-running the same command
     under the same conditions probably produces the same broken model.
     Operator attention required.
  4. **startup error** — the driver crashes in the first ~60 s with an
     ImportError / TypeError / etc. A code bug, not a transient.
     Operator attention required.

The supervisor distinguishes these four kinds, auto-retries the first
two (up to a budget), halts loudly on the last two, and persists its
state to a JSON file so that an out-of-band session can read the state
cold and know exactly what's happening without re-deriving it.

Heartbeat: the supervisor touches a heartbeat file every ~5 s. External
watchdogs (cron, launchd, a sibling Claude session) can `stat` that
file and decide whether the supervisor itself has gone walkabout.

Usage (production):

    python scripts/supervised_dose_series.py \\
      --base /path/to/gemma-2-9b-it \\
      --out-root abliteration-output \\
      --doses 1,2,8 \\
      --max-seq-length 512 \\
      --stall-timeout 600 \\
      --max-attempts 3

Usage (read-only state check from another session):

    python scripts/supervised_dose_series.py --status \\
      --state-dir abliteration-output
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

POLL_INTERVAL_S = 5.0
HEARTBEAT_FILENAME = ".dose-supervisor-heartbeat"
STATE_FILENAME = ".dose-supervisor-state.json"
LOG_FILENAME_TPL = ".dose-supervisor-run-{ts}.log"
STARTUP_GRACE_S = 60.0  # crash within this window counts as startup-error

# OBLITERATUS uses rich.live for progress display, which updates a single
# terminal line in place and writes NOTHING new to stdout/the log file during
# multi-minute compute phases (notably the verify step, which on Gemma-2-9B
# takes ~800s). Log-mtime alone says "hang" while the process is actually
# computing flat-out. The CPU-time delta below catches that case — a process
# burning >= MIN_CPU_PROGRESS_S of CPU between polls is making progress
# even when its stdout is silent.
MIN_CPU_PROGRESS_S = 0.5  # min user-CPU seconds per poll to count as alive

# Even with CPU-aware idle detection, a process making slow progress under
# heavy swap pressure looks "alive" (CPU advancing) but cannot finish in
# any reasonable time. A successful Gemma-2-9B dose runs ~15 min wall clock;
# 1h29m of "alive but slow" is swap thrash, not real progress. The wall-clock
# upper bound below is the backstop that catches that case — it kills the
# attempt even when the CPU-idle detector says everything's fine.
MAX_WALL_CLOCK_S = 3600.0  # 60 minutes per attempt; 4x the observed clean run

# Pre-flight check: refuse to start a dose attempt unless this much RAM is
# free. The Gemma-2-9B model is ~19 GB at fp16; activation collection adds
# another few GB. 25 GB free is the minimum safe margin on a 34 GB M5.
MIN_FREE_GB = 25.0


def utcnow_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def free_ram_gb() -> float:
    """Available RAM in GB. psutil.virtual_memory().available is the right
    signal — counts memory that COULD be reclaimed without swapping."""
    try:
        import psutil
        return psutil.virtual_memory().available / (1024 ** 3)
    except ImportError:
        return float("inf")  # graceful fallback


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

def state_path(state_dir: Path) -> Path:
    return state_dir / STATE_FILENAME


def load_state(state_dir: Path) -> dict[str, Any]:
    p = state_path(state_dir)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        return {}


def save_state(state_dir: Path, state: dict[str, Any]) -> None:
    state["last_updated"] = utcnow_iso()
    p = state_path(state_dir)
    p.write_text(json.dumps(state, indent=2))


def init_state(doses: list[int]) -> dict[str, Any]:
    return {
        "version": 1,
        "started_at": utcnow_iso(),
        "last_updated": utcnow_iso(),
        "phase": "running",
        "halt_reason": None,
        "doses": {str(d): {"attempts": 0, "status": "pending", "last_failure": None,
                            "last_attempt_at": None}
                  for d in doses},
    }


def print_status(state_dir: Path) -> int:
    state = load_state(state_dir)
    if not state:
        print(f"no state file at {state_path(state_dir)}")
        return 1
    print(f"phase: {state.get('phase')}")
    print(f"started: {state.get('started_at')}")
    print(f"updated: {state.get('last_updated')}")
    if state.get("halt_reason"):
        print(f"HALTED: {state.get('halt_reason')}")
    print()
    print(f"{'dose':>5} {'status':>10} {'attempts':>8}  last_failure")
    for d, info in sorted(state.get("doses", {}).items(), key=lambda kv: int(kv[0])):
        print(f"{d:>5} {info['status']:>10} {info['attempts']:>8}  "
              f"{info.get('last_failure') or '-'}")
    # Heartbeat freshness
    hb = state_dir / HEARTBEAT_FILENAME
    if hb.exists():
        age = time.time() - hb.stat().st_mtime
        print(f"\nheartbeat: {age:.0f}s old ({'fresh' if age < 30 else 'STALE'})")
    return 0


# ---------------------------------------------------------------------------
# Per-dose run with stall detection
# ---------------------------------------------------------------------------

def run_one_dose_supervised(
    dose: int, base: Path, out_root: Path, max_seq_length: int,
    device: str, dtype: str, stall_timeout: float,
    log_path: Path, heartbeat_path: Path,
    strong_layers: str = "",
) -> tuple[str, str]:
    """Run one dose under supervision.

    Returns (outcome, detail) where outcome is one of:
        "ok"            — dose completed; smoke gate passed (driver exited 0)
        "crash"         — subprocess exited non-zero after > STARTUP_GRACE_S
        "hang"          — no log line for stall_timeout seconds, killed
        "smoke_fail"    — driver exited non-zero AND a *-FAILED-* dir exists
        "startup"       — subprocess exited non-zero within STARTUP_GRACE_S
    """
    driver = Path(__file__).parent / "run_dose_series.py"
    # We invoke the same Python that's running us (the bias-study venv) so
    # the supervisor inherits the OBLITERATUS install.
    cmd = [
        sys.executable, str(driver),
        "--base", str(base),
        "--out-root", str(out_root),
        "--doses", str(dose),
        "--max-seq-length", str(max_seq_length),
        "--device", device,
        "--dtype", dtype,
    ]
    if strong_layers:
        cmd.extend(["--strong-layers", strong_layers])
    log_fp = log_path.open("a")
    log_fp.write(f"\n=== supervisor run: dose={dose} started at {utcnow_iso()} ===\n")
    log_fp.write(f"cmd: {' '.join(cmd)}\n")
    log_fp.flush()
    started = time.time()
    proc = subprocess.Popen(
        cmd, stdout=log_fp, stderr=subprocess.STDOUT,
        # New process group so we can SIGKILL the whole subtree on hang
        preexec_fn=os.setsid,
    )
    # CPU-activity-aware stall detection. OBLITERATUS goes silent on stdout
    # during long compute phases; relying on log-mtime alone produces
    # false-positive hangs. We track total user-CPU consumed by the subprocess
    # tree (the driver + its child obliteratus + that one's children) and
    # only declare hang when BOTH the log AND the CPU clock have been static.
    try:
        import psutil
        psproc = psutil.Process(proc.pid)
    except (ImportError, psutil.NoSuchProcess):
        psproc = None
    last_cpu_advance_t = started
    last_total_cpu = 0.0

    def tree_cpu_time() -> float:
        if psproc is None:
            return 0.0
        total = 0.0
        try:
            for p in [psproc] + psproc.children(recursive=True):
                try:
                    total += p.cpu_times().user
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        return total

    try:
        while True:
            rc = proc.poll()
            now = time.time()
            heartbeat_path.write_text(utcnow_iso())
            if rc is not None:
                wall = now - started
                log_fp.write(f"=== subprocess exited rc={rc} after {wall:.1f}s ===\n")
                log_fp.flush()
                if rc == 0:
                    return ("ok", f"exit 0 in {wall:.0f}s")
                # Distinguish startup error from crash
                if wall < STARTUP_GRACE_S:
                    return ("startup", f"exit {rc} in {wall:.0f}s")
                # Distinguish smoke-gate failure from crash by looking for
                # any *-FAILED-* dir created during this attempt.
                failed_dirs = sorted(out_root.glob(f"*-dose{dose}-FAILED-*"))
                if failed_dirs and failed_dirs[-1].stat().st_mtime >= started:
                    return ("smoke_fail",
                            f"exit {rc}; FAILED dir at {failed_dirs[-1].name}")
                return ("crash", f"exit {rc} in {wall:.0f}s")
            # Combined stall check: log-mtime AND cpu-time-delta.
            try:
                log_age = now - log_path.stat().st_mtime
            except FileNotFoundError:
                log_age = 0
            cur_cpu = tree_cpu_time()
            if cur_cpu - last_total_cpu >= MIN_CPU_PROGRESS_S:
                last_cpu_advance_t = now
                last_total_cpu = cur_cpu
            cpu_idle_age = now - last_cpu_advance_t
            wall_age = now - started
            # Declare hang on EITHER:
            #   - both signals idle (the classic case), OR
            #   - wall clock past MAX_WALL_CLOCK_S (the swap-thrash backstop —
            #     CPU is still advancing but progress is so slow the process
            #     will never finish in reasonable time)
            if log_age > stall_timeout and cpu_idle_age > stall_timeout:
                log_fp.write(
                    f"=== HANG: log idle {log_age:.0f}s + CPU idle "
                    f"{cpu_idle_age:.0f}s (cpu_total {cur_cpu:.0f}s), "
                    f"killing ===\n"
                )
                log_fp.flush()
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=10)
                return ("hang", f"log+cpu idle {log_age:.0f}s")
            if wall_age > MAX_WALL_CLOCK_S:
                log_fp.write(
                    f"=== WALL-CLOCK BACKSTOP: {wall_age:.0f}s > "
                    f"{MAX_WALL_CLOCK_S:.0f}s "
                    f"(cpu_total {cur_cpu:.0f}s, free_ram {free_ram_gb():.1f} GB) "
                    f"-- killing; almost certainly swap thrash ===\n"
                )
                log_fp.flush()
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=10)
                return ("hang",
                        f"wall {wall_age:.0f}s > {MAX_WALL_CLOCK_S:.0f}s "
                        f"(free_ram {free_ram_gb():.1f}GB)")
            time.sleep(POLL_INTERVAL_S)
    finally:
        log_fp.close()
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass


# ---------------------------------------------------------------------------
# Outer loop
# ---------------------------------------------------------------------------

RETRYABLE = {"crash", "hang"}
HALT_REASONS = {
    "smoke_fail": "a dose's abliteration produced a model that failed the "
                  "smoke gate (perplexity / coherence / generation check). The "
                  "output dir has been renamed *-FAILED-*. DO NOT auto-retry — "
                  "investigate the root cause (almost always M5 memory pressure "
                  "during activation collection).",
    "startup":   "the driver crashed in the startup grace window. This is a "
                  "code bug or environment problem, not a transient. Read the "
                  "supervisor log; fix; restart.",
    "exhausted": "a retryable failure recurred past --max-attempts. The most "
                  "recent failure detail is on this dose's `last_failure`. "
                  "If you raise --max-attempts and re-launch, the supervisor "
                  "will resume on this dose.",
}


def supervised_main(args: argparse.Namespace) -> int:
    state_dir = args.state_dir or args.out_root
    state_dir.mkdir(parents=True, exist_ok=True)
    args.out_root.mkdir(parents=True, exist_ok=True)

    state = load_state(state_dir)
    if not state or sorted(state.get("doses", {}).keys()) != sorted(str(d) for d in args.doses):
        state = init_state(args.doses)
        save_state(state_dir, state)

    if state.get("phase") == "done":
        print(f"phase=done in state file; nothing to do. "
              f"--reset to start over.", file=sys.stderr)
        return 0
    if state.get("phase") == "halted" and not args.resume_halted:
        print(f"phase=halted: {state.get('halt_reason')}\n"
              f"(pass --resume-halted to override)", file=sys.stderr)
        return 2

    # On --resume-halted, reset doses with attempts at/above --max-attempts
    # so they can actually retry. Without this, a halted-then-resumed run
    # walks straight back into 'exhausted' on the same dose because the
    # attempt counter is sticky. Doses already at status='ok' stay ok.
    if args.resume_halted:
        for k, info in state.get("doses", {}).items():
            if info.get("status") == "ok":
                continue
            info["attempts"] = 0
            info["status"] = "pending"
            info["last_failure"] = (info.get("last_failure") or "") + " [resumed]"
        print("(resume-halted: cleared attempts for non-ok doses)", flush=True)
    state["phase"] = "running"
    state["halt_reason"] = None
    save_state(state_dir, state)

    ts = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = state_dir / LOG_FILENAME_TPL.format(ts=ts)
    heartbeat_path = state_dir / HEARTBEAT_FILENAME

    print(f"supervisor started, state: {state_path(state_dir)}, "
          f"log: {log_path}", flush=True)

    for dose in args.doses:
        key = str(dose)
        # Skip if already done (idempotent across supervisor restarts)
        meta_path = args.out_root / f"gemma-2-9b-it-dose{dose}" / "abliteration_metadata.json"
        # Driver's --out-prefix default is "gemma-2-9b-it-dose"; if the user
        # passes a different prefix we miss the check, but that's fine — the
        # driver's own skip-existing will catch it.
        if meta_path.exists() and state["doses"][key]["status"] != "ok":
            # Pre-existing metadata (e.g. the reference n_dir=4 spine). Mark ok.
            state["doses"][key]["status"] = "ok"
            state["doses"][key]["last_failure"] = None
            save_state(state_dir, state)

        if state["doses"][key]["status"] == "ok":
            print(f"dose={dose}: already ok, skipping", flush=True)
            continue

        while state["doses"][key]["attempts"] < args.max_attempts:
            # Pre-flight memory check. Refuse to launch under memory pressure
            # because the result is swap thrash — slow but technically alive,
            # which used to fool both the user AND the watchdog. Wait briefly
            # in case a transient consumer (browser tab opened, build job)
            # is about to release memory.
            free_gb = free_ram_gb()
            if free_gb < args.min_free_gb:
                print(f"dose={dose}: WAITING for memory — "
                      f"{free_gb:.1f} GB free < {args.min_free_gb} GB required. "
                      f"Free RAM by closing apps. Retry check in 60s.",
                      flush=True)
                time.sleep(60)
                free_gb = free_ram_gb()
                if free_gb < args.min_free_gb:
                    state["doses"][key]["status"] = "halted"
                    state["doses"][key]["last_failure"] = (
                        f"pre-flight: free_ram {free_gb:.1f}GB < "
                        f"{args.min_free_gb}GB")
                    state["phase"] = "halted"
                    state["halt_reason"] = (
                        f"dose {dose}: insufficient RAM "
                        f"({free_gb:.1f}GB free). Close other memory consumers "
                        f"(Discord, browsers, IDEs) and resume with "
                        f"--resume-halted. The model needs ~19 GB headroom "
                        f"alone; swap thrash makes the abliteration "
                        f"functionally non-terminating.")
                    save_state(state_dir, state)
                    print(state["halt_reason"], file=sys.stderr, flush=True)
                    return 5

            state["doses"][key]["attempts"] += 1
            state["doses"][key]["status"] = "running"
            state["doses"][key]["last_attempt_at"] = utcnow_iso()
            save_state(state_dir, state)

            attempt = state["doses"][key]["attempts"]
            print(f"dose={dose} attempt {attempt}/{args.max_attempts} "
                  f"(free RAM {free_gb:.1f} GB)...",
                  flush=True)
            outcome, detail = run_one_dose_supervised(
                dose=dose, base=args.base, out_root=args.out_root,
                max_seq_length=args.max_seq_length, device=args.device,
                dtype=args.dtype, stall_timeout=args.stall_timeout,
                log_path=log_path, heartbeat_path=heartbeat_path,
                strong_layers=args.strong_layers,
            )
            print(f"dose={dose} attempt {attempt}: {outcome} ({detail})",
                  flush=True)
            state["doses"][key]["last_failure"] = (
                None if outcome == "ok" else f"{outcome}: {detail}")
            if outcome == "ok":
                state["doses"][key]["status"] = "ok"
                save_state(state_dir, state)
                break
            if outcome not in RETRYABLE:
                state["doses"][key]["status"] = "halted"
                state["phase"] = "halted"
                state["halt_reason"] = (
                    f"dose {dose}: {outcome} — {HALT_REASONS[outcome]} "
                    f"(detail: {detail})")
                save_state(state_dir, state)
                print(state["halt_reason"], file=sys.stderr, flush=True)
                return 3
            # Retryable; record and loop
            state["doses"][key]["status"] = f"pending (last={outcome})"
            save_state(state_dir, state)
        else:
            state["doses"][key]["status"] = "halted"
            state["phase"] = "halted"
            state["halt_reason"] = (
                f"dose {dose}: exhausted retries — {HALT_REASONS['exhausted']} "
                f"(last_failure: {state['doses'][key]['last_failure']})")
            save_state(state_dir, state)
            print(state["halt_reason"], file=sys.stderr, flush=True)
            return 4

    state["phase"] = "done"
    state["halt_reason"] = None
    save_state(state_dir, state)
    print("=== ALL DOSES COMPLETE ===", flush=True)
    return 0


def parse_doses(arg: str) -> list[int]:
    return [int(x) for x in arg.split(",") if x.strip()]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--status", action="store_true",
                   help="Read-only: print current state and exit. Pair with --state-dir.")
    p.add_argument("--reset", action="store_true",
                   help="Delete the state file before starting (force fresh run)")
    p.add_argument("--resume-halted", action="store_true",
                   help="Override a previous halt to continue (e.g. after fixing root cause)")
    p.add_argument("--base", type=Path, help="HF base model dir")
    p.add_argument("--out-root", type=Path, help="Where to write each dose's output dir")
    p.add_argument("--state-dir", type=Path,
                   help="Where the state file + heartbeat live (default: --out-root)")
    p.add_argument("--doses", default="1,2,8", type=parse_doses,
                   help="Comma-separated n_directions values")
    p.add_argument("--max-seq-length", default=512, type=int)
    p.add_argument("--device", default="mps")
    p.add_argument("--dtype", default="float16")
    p.add_argument("--stall-timeout", default=1500.0, type=float,
                   help="Seconds with BOTH log idle AND CPU idle before declaring "
                        "hang. Default 1500. OBLITERATUS's verify stage runs ~800s "
                        "on Gemma-2-9B with no stdout writes (rich.live updates "
                        "the terminal in place); 600s was too aggressive and "
                        "produced false-positive hangs that killed working processes.")
    p.add_argument("--strong-layers", default="24-41",
                   help="Layer-index spec ('24-41' or '24,25,...') passed through "
                        "to the driver. Pinned across the dose-series so the "
                        "dose-response measures n_directions cleanly (default "
                        "knee_cosmic varies the layer count per n_dir, which "
                        "broke n_dir=1 while n_dir=4 reference survived). Pass "
                        "an empty string to let OBLITERATUS pick.")
    p.add_argument("--min-free-gb", default=MIN_FREE_GB, type=float,
                   help=f"Minimum free RAM (GB) required to start a dose "
                        f"attempt. Default {MIN_FREE_GB}. Below this the "
                        f"supervisor waits 60s then halts; abliteration "
                        f"under swap thrash is functionally non-terminating.")
    p.add_argument("--max-attempts", default=3, type=int,
                   help="Per-dose retry budget for retryable failures (default 3)")
    args = p.parse_args()

    if args.status:
        if not args.state_dir:
            print("--status requires --state-dir", file=sys.stderr)
            return 2
        return print_status(args.state_dir)

    if not args.base or not args.out_root:
        print("--base and --out-root are required when not in --status mode",
              file=sys.stderr)
        return 2
    if not args.base.is_dir():
        print(f"--base {args.base} is not a directory", file=sys.stderr)
        return 2

    if args.reset:
        sd = args.state_dir or args.out_root
        sp = state_path(sd)
        if sp.exists():
            sp.unlink()
            print(f"reset: removed {sp}", flush=True)

    return supervised_main(args)


if __name__ == "__main__":
    sys.exit(main())
