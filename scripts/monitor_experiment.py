#!/usr/bin/env python3
"""monitor_experiment.py — the durable, cross-platform half of the
experiment-monitor agent.

The agent's markdown spec only works while a Claude session is alive to drive
the `Monitor` tool; that tool dies on session restart, so nothing watches an
overnight run. THIS script is session-independent: launched detached
(`nohup ... &` on POSIX, `pythonw` / `start` on native Windows, plain `nohup`
under Git-Bash), it launches the experiment as its own child, polls the log
file itself, and writes a result/diagnostic markdown file the moment the
success or failure pattern lands — whether or not any Claude session is alive.

It is Python (not shell) on purpose: the experiments and the dose-series
supervisor are already Python with cross-platform path resolution, and stock
macOS ships bash 3.2 with BSD coreutils while the Windows 4090 runs Git-Bash
with GNU coreutils. A pure-Python watcher behaves identically on M5 (macOS),
the 4090 (Windows/Git-Bash), and any Linux host — no shell-version or
BSD-vs-GNU divergence.

Usage (POSIX / Git-Bash):
    nohup python scripts/monitor_experiment.py \\
      --name the-wash-exp3-target-asymmetry \\
      --launch "bash run_exp3.sh" \\
      --log /path/to/target-asymmetry.log \\
      --success "asymmetry-report" \\
      --fail "Traceback|FAILED|Error" \\
      --artifact "/path/.../asymmetry/runs/*/asymmetry-report.md" \\
      --findings-dir /path/.../the-wash/findings \\
      --validate 'test -s "$ART" && ! grep -q "top-8: \\[\\]" "$ART"' \\
      > monitor-exp3.log 2>&1 &
    disown

Native Windows (no Git-Bash):
    start /b pythonw scripts\\monitor_experiment.py --name ... (same flags)

Status from any shell, any time:
    cat <findings-dir>/.monitor-<name>.state

Exit codes: 0 success (+validate passed), 1 failure (fail-pattern OR
validate failed), 2 usage error.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import glob
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_FAIL = r"Traceback|FAILED|Error|Killed|OOM"


def ts() -> str:
    return _dt.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")


def stamp() -> str:
    return _dt.datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--name", required=True, help="short slug for this experiment")
    p.add_argument("--launch", required=True,
                   help="command that runs the experiment. The watcher Popens it "
                        "as a child and does NOT wait — do not add nohup/&/disown; "
                        "the watcher owns the backgrounding.")
    p.add_argument("--log", required=True, help="log file the launch writes to")
    p.add_argument("--success", required=True,
                   help="regex that appears ONLY on success")
    p.add_argument("--fail", default=DEFAULT_FAIL,
                   help=f"regex that signals failure (default: {DEFAULT_FAIL})")
    p.add_argument("--artifact", default="",
                   help="glob for the result artifact; newest match is read into "
                        "the findings file and exported as $ART to --validate")
    p.add_argument("--findings-dir", required=True,
                   help="where the result/diagnostic .md + .state file land")
    p.add_argument("--poll", type=float, default=15.0,
                   help="seconds between log scans (default 15)")
    p.add_argument("--validate", default="",
                   help="shell snippet; must exit 0 for success to count. $ART "
                        "(resolved artifact path) is exported into its env. This "
                        "is what stops an empty/garbage artifact (e.g. top-8:[]) "
                        "from being rubber-stamped as success.")
    p.add_argument("--on-success", default="",
                   help="optional shell snippet run after a confirmed success "
                        "(e.g. 'pkill -f ablit_judge')")
    p.add_argument("--smoke-sec", type=float, default=600.0,
                   help="warn once (do not kill) if the log is empty/absent this "
                        "long after launch — flags a silent early death")
    p.add_argument("--rel-root", default="",
                   help="paths written into the findings/state files are made "
                        "relative to this root so the committed record carries no "
                        "absolute machine path (release gate 5d). Default: the git "
                        "repo containing --findings-dir; $HOME is scrubbed to ~ as "
                        "a backstop for paths outside the root.")
    args = p.parse_args()

    findings = Path(args.findings_dir)
    findings.mkdir(parents=True, exist_ok=True)
    state_path = findings / f".monitor-{args.name}.state"
    log_path = Path(args.log)
    success_re = re.compile(args.success)
    fail_re = re.compile(args.fail)

    rel_root = Path(args.rel_root).resolve() if args.rel_root else _find_repo_root(findings)
    scrub = _make_scrubber(rel_root)

    def write_state(phase: str, detail: str = "") -> None:
        state_path.write_text(scrub(
            f"name: {args.name}\nphase: {phase}\ndetail: {detail}\n"
            f"updated: {ts()}\nlog: {args.log}\nlaunch: {args.launch}\n"))

    # Stale-log immunity. A prior run's log may already contain the success
    # pattern (it did once → instant false 0s "success" against the OLD artifact).
    # `watch["baseline"]` = log size at launch. We refuse to match until we've
    # OBSERVED the run truncate the file (size drops below baseline) — run scripts
    # do `> log`, so this fires on the first poll after launch. Sticky: once
    # truncation is seen, scan the whole (now this-run-owned) file, even as it
    # grows past the old size. If there was no stale log (baseline 0), there is
    # nothing to be fooled by, so we scan immediately.
    watch = {"baseline": 0, "truncated": True}

    def log_matches(rx: re.Pattern) -> bool:
        try:
            size = log_path.stat().st_size
        except FileNotFoundError:
            return False
        if size < watch["baseline"]:
            watch["truncated"] = True
        if not watch["truncated"]:
            return False
        try:
            with log_path.open("r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if rx.search(line):
                        return True
        except FileNotFoundError:
            return False
        return False

    def resolve_artifact() -> str:
        if not args.artifact:
            return ""
        matches = sorted(glob.glob(args.artifact), key=lambda x: os.path.getmtime(x)
                         if os.path.exists(x) else 0, reverse=True)
        return matches[0] if matches else ""

    def run_shell(snippet: str, extra_env: dict | None = None) -> int:
        """Run a shell snippet cross-platform. shell=True uses the platform shell
        (/bin/sh on POSIX, cmd on native Windows; Git-Bash users get sh)."""
        env = dict(os.environ)
        if extra_env:
            env.update(extra_env)
        return subprocess.call(snippet, shell=True, env=env)

    # 1. Launch the experiment as a detached child. Popen + no wait = it runs
    #    in the background under this watcher; the watcher itself is what the
    #    caller nohup'd, so both survive session death.
    write_state("launching")
    # Record any pre-existing log size; require an observed truncation before
    # matching, so stale prior-run content can't trigger a false success.
    try:
        watch["baseline"] = log_path.stat().st_size if log_path.exists() else 0
    except OSError:
        watch["baseline"] = 0
    watch["truncated"] = watch["baseline"] == 0
    if watch["baseline"]:
        print(f"{ts()} note: pre-existing log of {watch['baseline']}B — ignoring "
              "until this run truncates it", flush=True)
    print(f"{ts()} launching: {args.launch}", flush=True)
    try:
        subprocess.Popen(args.launch, shell=True)
    except Exception as e:  # noqa: BLE001
        write_state("failed", f"launch raised: {e}")
        print(f"{ts()} FATAL: launch failed: {e}", file=sys.stderr, flush=True)
        return 2
    write_state("running", "launched")

    started = time.time()
    smoke_warned = False

    while True:
        elapsed = time.time() - started

        if log_matches(success_re):
            print(f"{ts()} success pattern matched after {elapsed:.0f}s — validating",
                  flush=True)
            art = resolve_artifact()

            # Validate gate: success pattern alone is NOT success.
            if args.validate:
                rc = run_shell(args.validate, {"ART": art})
                if rc != 0:
                    write_state("failed",
                                "success pattern matched but --validate failed "
                                "(empty/garbage artifact)")
                    diag = findings / f"{args.name}-{stamp()}-FAILED.md"
                    body = [
                        f"# {args.name} — FAILED (validate) {ts()}", "",
                        f"- launch: `{args.launch}`",
                        f"- wall time: {elapsed/60:.1f} min ({elapsed:.0f}s)",
                        f"- success pattern `{args.success}` matched, but "
                        f"`--validate` returned {rc}",
                        f"- validate snippet: `{args.validate}`",
                        f"- artifact: `{art or '<none matched>'}`", "",
                        "The experiment ran to its success marker but produced an "
                        "artifact that failed validation (e.g. an empty ranking). "
                        "This is the exact rubber-stamp-empty-result failure "
                        "`--validate` exists to catch. Not auto-restarted.", "",
                    ]
                    if art and Path(art).is_file():
                        body += ["## Artifact (failed validation)", "", "```",
                                 Path(art).read_text(encoding="utf-8", errors="replace"),
                                 "```"]
                    diag.write_text(scrub("\n".join(body)))
                    print(f"{ts()} VALIDATE FAILED — diagnostic: {diag}", flush=True)
                    write_state("done", f"diagnostic: {diag}")
                    return 1
                print(f"{ts()} validate passed", flush=True)

            write_state("success", f"matched: {args.success}")
            result = findings / f"{args.name}-{stamp()}.md"
            body = [
                f"# {args.name} — completed {ts()}", "",
                f"- launch: `{args.launch}`",
                f"- wall time: {elapsed/60:.1f} min ({elapsed:.0f}s)",
                f"- success pattern matched: `{args.success}`",
                f"- log: `{args.log}`",
            ]
            if art:
                body.append(f"- artifact: `{art}`")
            body.append("")
            if art and Path(art).is_file():
                body += ["## Artifact", "",
                         Path(art).read_text(encoding="utf-8", errors="replace")]
            else:
                tail = _tail(log_path, 25)
                body += ["## Log tail (no artifact glob matched)", "", "```", tail, "```"]
            result.write_text(scrub("\n".join(body)))
            print(f"{ts()} SUCCESS — result: {result}", flush=True)
            write_state("done", f"result: {result}")
            if args.on_success:
                print(f"{ts()} on-success hook: {args.on_success}", flush=True)
                run_shell(args.on_success)
            return 0

        if log_matches(fail_re):
            write_state("failed", f"matched: {args.fail}")
            diag = findings / f"{args.name}-{stamp()}-FAILED.md"
            tail = _tail(log_path, 40)
            diag.write_text(scrub("\n".join([
                f"# {args.name} — FAILED {ts()}", "",
                f"- launch: `{args.launch}`",
                f"- wall time before failure: {elapsed/60:.1f} min ({elapsed:.0f}s)",
                f"- fail pattern matched: `{args.fail}`",
                f"- log: `{args.log}`", "",
                "## Log tail (last 40 lines)", "", "```", tail, "```", "",
                "Not auto-restarted. Operator decides transient-vs-bug.",
            ])))
            print(f"{ts()} FAILURE — diagnostic: {diag}", flush=True)
            write_state("done", f"diagnostic: {diag}")
            return 1

        if (not smoke_warned) and elapsed >= args.smoke_sec:
            if (not log_path.exists()) or log_path.stat().st_size == 0:
                write_state("running",
                            f"WARN: no log output after {args.smoke_sec:.0f}s — "
                            "possible silent early death")
                print(f"{ts()} WARN: {args.log} empty/missing after "
                      f"{args.smoke_sec:.0f}s", flush=True)
            smoke_warned = True

        time.sleep(args.poll)


def _find_repo_root(start: Path) -> Path:
    """Nearest ancestor containing .git; else `start` itself. Anchors path
    relativization so findings records are repo-relative, not absolute."""
    cur = start.resolve()
    for p in (cur, *cur.parents):
        if (p / ".git").exists():
            return p
    return cur


def _make_scrubber(root: Path):
    """Return scrub(s): rewrite absolute paths under `root` to repo-relative, and
    any remaining $HOME-prefixed path to ~/… as a backstop. Longest-prefix first
    so the more-specific root match wins over the home match."""
    home = Path(os.path.expanduser("~")).resolve()
    root = root.resolve()
    subs = [
        (str(root) + os.sep, ""),
        (str(root), "."),
        (str(home) + os.sep, "~" + os.sep),
        (str(home), "~"),
    ]
    # Apply longest source first to avoid a shorter (home) prefix pre-empting root.
    subs.sort(key=lambda ab: len(ab[0]), reverse=True)

    def scrub(s: str) -> str:
        for a, b in subs:
            s = s.replace(a, b)
        return s

    return scrub


def _tail(path: Path, n: int) -> str:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(lines[-n:])
    except FileNotFoundError:
        return "(log file not found)"


if __name__ == "__main__":
    sys.exit(main())
