#!/usr/bin/env python3
"""bias-study-prep: end-to-end pre-study refresh.

Pulls relevant repos, rebuilds reference EPUBs, verifies toolchain health,
checks env vars, writes a dated prep-state.json file under the bias-study
runs/ directory.

Exit codes:
    0 = clean (study may proceed)
    1 = pre-flight blocker (study MUST NOT proceed)
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path(os.environ.get("BIAS_STUDY_WORKSPACE", Path.home()))
CLAUDE_TOOLS = Path(os.environ.get("CLAUDE_TOOLS", Path.home() / "claude"))

REPOS = {
    "publishing-tools": WORKSPACE / "publishing-tools",
    "books/evil-robots": WORKSPACE / "books" / "evil-robots",
    "books/the-ratchet": WORKSPACE / "books" / "the-ratchet",
    "evil-robots-series": WORKSPACE / "evil-robots-series",
    "fires-series": WORKSPACE / "fires-series",
    "G0DM0D3": CLAUDE_TOOLS / "G0DM0D3",
    "OBLITERATUS": CLAUDE_TOOLS / "OBLITERATUS",
}

def _resolve_study_dir():
    """The study tree this skill should operate on.

    THIS SHIPPED IN THE PUBLIC MIRROR POINTING AT A PRIVATE DIRECTORY. `WORKSPACE` defaulted to
    the home directory, so this resolved to an internal working-copy path that exists on exactly
    one machine. Anyone who cloned github.com/gorrie/bias-study and ran the skill shipped to ease
    reproduction got a subprocess traceback (`NotADirectoryError: [WinError 267]`), with nothing
    saying why.

    The mirror is itself a complete study tree: it has `scripts/`, `runs/` and `data/`. So the
    author's tree is used when it is there, and the repository this file lives in otherwise --
    which is the case that matters, because it is the only one a replicator has.
    """
    private = WORKSPACE / "evil-robots-series" / "research" / "bias-study"
    if (private / "scripts").is_dir():
        return private
    here = Path(__file__).resolve().parents[3]      # skills/<name>/scripts/ -> repo root
    if (here / "scripts").is_dir():
        return here
    raise SystemExit(
        "no study tree found. Looked for %s (the author's working copy) and %s (this "
        "repository). Set BIAS_STUDY_WORKSPACE if yours is elsewhere." % (private, here))


BIAS_STUDY_DIR = _resolve_study_dir()

# The JUDGE-SCORED battery's protocol files. Still checked, still present, and no longer the
# primary instrument: it was retired on 2026-08-29 in favour of the 62 forced-choice
# politicalcompass propositions. Kept because the v1/v2 data and every published claim resting
# on it are real -- but a green tick on these says nothing about a compass run, which is how
# this skill came to pass vacuously in front of a collection it did not check.
LEGACY_PROTOCOL_FILES = [
    "README.md",
    "questions.md",
    "rubric.md",
    "schema.md",
    "run-protocol.md",
    "aggregation-rules.md",
]

# What a FORCED-CHOICE run actually depends on.
COMPASS_FILES = [
    "data/compass-propositions.json",
    "scripts/run_compass.py",
    "scripts/test_compass_parser.py",
    "PREREG-2026-08-29-mask-surface-v2.md",
]

# Gates that must already pass BEFORE new runs land. If the paper disagrees with the data now,
# adding runs makes the disagreement harder to attribute rather than easier.
PRE_RUN_GATES = [
    ("gen_paper", ["scripts/gen_paper.py", "--check"]),
    ("key_numbers", ["scripts/key_numbers.py", "--check"]),
    ("controls_audit", ["scripts/controls_audit.py", "--strict"]),
    ("compass_parser", ["scripts/test_compass_parser.py"]),
    # Added 2026-09-02. Twenty-one scripts had diverged between the working study and the
    # public mirror, two of them at the statistics layer -- the private ci_analysis.py kept an
    # order-dependent bootstrap the mirror had already fixed. A rotted statistic looks exactly
    # like a statistic, so this is checked mechanically before a run rather than noticed later.
    ("no_fork", ["scripts/check_no_fork.py"]),
]

EPUB_BOOKS = ["books/evil-robots", "books/the-ratchet"]

REQUIRED_ENV = ["OPENROUTER_API_KEY"]
OPTIONAL_ENV = [
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GOOGLE_AI_API_KEY",
    "MISTRAL_API_KEY",
    "XAI_API_KEY",
    "DEEPSEEK_API_KEY",
    "HF_TOKEN",
]


def log(level: str, msg: str) -> None:
    print(f"[{level:5}] {msg}", flush=True)


def run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def file_sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def git_pull_repo(name: str, path: Path) -> dict:
    result = {"name": name, "path": str(path)}
    if not (path / ".git").exists():
        result["status"] = "missing"
        log("ERROR", f"{name}: no git repo at {path}")
        return result

    rc, out, err = run(["git", "pull", "--ff-only"], cwd=path)
    if rc != 0:
        result["status"] = "pull-failed"
        result["error"] = err or out
        log("ERROR", f"{name}: git pull failed: {err or out}")
        return result

    rc, out, _ = run(["git", "rev-parse", "HEAD"], cwd=path)
    result["status"] = "ok"
    result["commit"] = out if rc == 0 else None
    log("OK   ", f"{name}: at {result['commit'][:12] if result['commit'] else '?'}")
    return result


def verify_protocol_dir() -> dict:
    result = {"path": str(BIAS_STUDY_DIR), "files": {}}
    if not BIAS_STUDY_DIR.exists():
        result["status"] = "missing"
        log("ERROR", f"protocol dir missing: {BIAS_STUDY_DIR}")
        return result

    all_ok = True
    for fn in LEGACY_PROTOCOL_FILES:
        fp = BIAS_STUDY_DIR / fn
        sha = file_sha256(fp)
        if sha is None:
            result["files"][fn] = {"status": "missing"}
            log("ERROR", f"protocol file missing: {fn}")
            all_ok = False
        else:
            size = fp.stat().st_size
            if size < 100:
                result["files"][fn] = {"status": "too-small", "size": size}
                log("ERROR", f"protocol file too small ({size}b): {fn}")
                all_ok = False
            else:
                result["files"][fn] = {"status": "ok", "sha256": sha, "size": size}
                log("OK   ", f"protocol: {fn} ({size}b)")

    result["status"] = "ok" if all_ok else "failed"
    return result


def verify_compass() -> dict:
    """The FORCED-CHOICE instrument: is it present, is it the right one, does the parser hold?

    Added 2026-09-02 after this skill was found scoped entirely to the retired battery. It
    checked six protocol files that still exist, passed, and said nothing about the instrument
    a collection was about to use.
    """
    result = {"files": {}, "status": "ok"}
    for rel in COMPASS_FILES:
        fp = BIAS_STUDY_DIR / rel
        sha = file_sha256(fp)
        if sha is None:
            result["files"][rel] = {"status": "missing"}
            log("ERROR", f"compass dependency missing: {rel}")
            result["status"] = "failed"
        else:
            result["files"][rel] = {"status": "ok", "sha256": sha}
            log("OK   ", f"compass: {rel}")

    items_path = BIAS_STUDY_DIR / "data" / "compass-propositions.json"
    if items_path.exists():
        try:
            payload = json.loads(items_path.read_text(encoding="utf-8"))
            items = payload["items"] if isinstance(payload, dict) and "items" in payload \
                else payload
            ids = sorted(int(i["id"]) for i in items)
            result["n_items"] = len(items)
            result["ids_contiguous"] = ids == list(range(1, len(items) + 1))
            if len(items) != 62 or not result["ids_contiguous"]:
                log("ERROR", f"instrument is {len(items)} item(s), ids contiguous="
                             f"{result['ids_contiguous']} -- expected 62, 1..62")
                result["status"] = "failed"
            else:
                log("OK   ", "instrument: 62 propositions, ids 1..62")
            # One sentence per proposition is a verified property of this instrument and the
            # bound fetch_items.py relies on. If it stops holding, the item set changed.
            multi = [int(i["id"]) for i in items
                     if len(re.findall(r"[.!?](?=\s+[A-Z\"“]|$)",
                                       (i.get("text") or "").strip())) != 1]
            result["multi_sentence_items"] = multi
            if multi:
                log("WARN ", f"{len(multi)} proposition(s) are not exactly one sentence: "
                             f"{multi[:6]}")
        except (ValueError, KeyError, TypeError) as exc:
            result["status"] = "failed"
            log("ERROR", f"instrument unreadable: {exc}")
    return result


def run_pre_run_gates() -> dict:
    """Every gate must already pass before new runs land."""
    out = {"gates": {}, "status": "ok"}
    for name, argv in PRE_RUN_GATES:
        code, stdout, stderr = run([sys.executable] + argv, cwd=BIAS_STUDY_DIR)
        tail = (stdout or stderr or "").strip().splitlines()
        out["gates"][name] = {"exit": code, "last": tail[-1][:160] if tail else ""}
        if code == 0:
            log("OK   ", f"gate {name}: {out['gates'][name]['last']}")
        else:
            out["status"] = "failed"
            log("ERROR", f"gate {name} FAILED (exit {code}): "
                         f"{out['gates'][name]['last']}")
    return out


def snapshot_floors() -> dict:
    """Record every floor's pair count BEFORE the run.

    THIS IS THE CHECK THIS SKILL MOST NEEDED AND DID NOT HAVE. Twice -- 2026-09-01 with 27
    runs and 2026-09-02 with 14 -- runs were collected specifically to extend a floor and
    contributed NOTHING to it, because the floor tool carried a hardcoded list of run
    directories and a new directory is invisible to an include list by construction. Both
    times the collection looked successful and the row did not move.

    A pair count taken before the run turns that from something you notice later, if at all,
    into a subtraction. If the after-count equals the before-count, the runs did not land.
    """
    out = {"arms": {}, "status": "ok"}
    scripts_dir = BIAS_STUDY_DIR / "scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        import floor_table  # noqa: PLC0415
    except Exception as exc:                                   # noqa: BLE001
        out["status"] = "unavailable"
        out["error"] = str(exc)[:200]
        log("WARN ", f"floor snapshot unavailable: {str(exc)[:120]}")
        return out
    try:
        for fn in (floor_table.floor_order, floor_table.floor_same_version,
                   floor_table.floor_quant, floor_table.floor_ablation,
                   floor_table.floor_conditions):
            row = fn()
            if row:
                out["arms"][row["name"]] = {"n_pairs": row.get("n"),
                                            "side": row.get("side")}
                log("OK   ", f"floor before run: {row['name']} = {row.get('n')} pairs")
        by_class = floor_table.floor_order_by_class()
        for name, row in by_class.items():
            out["arms"][name] = {"n_pairs": row.get("n"), "side": row.get("side")}
            log("OK   ", f"floor before run: {name} = {row.get('n')} pairs")
    except Exception as exc:                                   # noqa: BLE001
        out["status"] = "failed"
        out["error"] = str(exc)[:200]
        log("ERROR", f"floor snapshot failed: {str(exc)[:120]}")
    return out


def build_epub(book_path: str) -> dict:
    full = WORKSPACE / book_path
    result = {"book": book_path}
    if not full.exists():
        result["status"] = "missing"
        log("ERROR", f"book missing: {book_path}")
        return result

    python_exe = shutil.which("python") or "/c/Python314/python.exe"
    build_py = WORKSPACE / "publishing-tools" / "build.py"
    if not build_py.exists():
        result["status"] = "build-script-missing"
        log("ERROR", f"build.py not found at {build_py}")
        return result

    log("INFO ", f"building EPUB: {book_path} (this may take 1-3 minutes)")
    rc, out, err = run([python_exe, str(build_py), book_path], cwd=WORKSPACE)

    # build.py uses exit code 0 = READY, 1 = NEEDS FIX, 2 = FAILED
    if rc == 0:
        result["status"] = "ready"
        epub_path = full / "output" / f"{full.name}.epub"
        result["epub_sha256"] = file_sha256(epub_path)
        result["epub_size"] = epub_path.stat().st_size if epub_path.exists() else None
        log("OK   ", f"{book_path}: STATUS READY ({result.get('epub_size', 0)} bytes)")
    elif rc == 1:
        result["status"] = "needs-fix"
        result["build_output_tail"] = out[-500:] if out else ""
        log("ERROR", f"{book_path}: STATUS NEEDS FIX (rc={rc})")
    else:
        result["status"] = "failed"
        result["build_output_tail"] = out[-500:] if out else ""
        result["build_error_tail"] = err[-500:] if err else ""
        log("ERROR", f"{book_path}: STATUS FAILED (rc={rc})")

    return result


def verify_toolchain(g0_path: Path, obl_path: Path) -> dict:
    """Verify G0DM0D3 + OBLITERATUS health. Lightweight — checks for presence
    of expected directories / config files, not deep dependency resolution.
    """
    result = {"g0dm0d3": {}, "obliteratus": {}}

    if g0_path.exists() and (g0_path / ".git").exists():
        result["g0dm0d3"]["present"] = True
        # Look for SOMETHING that signals the repo is intact
        markers = ["README.md", "package.json", "pyproject.toml", "requirements.txt"]
        result["g0dm0d3"]["markers_present"] = [m for m in markers if (g0_path / m).exists()]
        log("OK   ", f"G0DM0D3 present at {g0_path}, markers: {result['g0dm0d3']['markers_present']}")
    else:
        result["g0dm0d3"]["present"] = False
        log("ERROR", f"G0DM0D3 not found at {g0_path}")

    if obl_path.exists() and (obl_path / ".git").exists():
        result["obliteratus"]["present"] = True
        markers = ["README.md", "requirements.txt", "pyproject.toml", "setup.py"]
        result["obliteratus"]["markers_present"] = [m for m in markers if (obl_path / m).exists()]
        log("OK   ", f"OBLITERATUS present at {obl_path}, markers: {result['obliteratus']['markers_present']}")
    else:
        result["obliteratus"]["present"] = False
        log("ERROR", f"OBLITERATUS not found at {obl_path}")

    return result


def verify_env() -> dict:
    result = {"required": {}, "optional": {}}
    all_required_ok = True

    for var in REQUIRED_ENV:
        present = bool(os.environ.get(var))
        result["required"][var] = present
        if present:
            log("OK   ", f"env: {var} present")
        else:
            log("ERROR", f"env: {var} MISSING (required)")
            all_required_ok = False

    for var in OPTIONAL_ENV:
        present = bool(os.environ.get(var))
        result["optional"][var] = present
        if present:
            log("OK   ", f"env: {var} present (optional)")

    result["all_required_ok"] = all_required_ok
    return result


def write_prep_state(state: dict, run_dir: Path) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / "prep-state.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)
    return out_path


def main() -> int:
    started = datetime.datetime.utcnow().isoformat() + "Z"
    today = datetime.date.today().isoformat()
    run_dir = BIAS_STUDY_DIR / "runs" / today

    log("INFO ", f"bias-study-prep starting at {started}")
    log("INFO ", f"target run dir: {run_dir}")

    state = {
        "skill_version": "1.1.0",
        "started_at": started,
        "target_run_date": today,
        "repos": {},
        "protocol": {},
        "epubs": {},
        "toolchain": {},
        "env": {},
        "compass": {},
        "gates": {},
        "floors_before": {},
    }

    # 1. Git pulls
    log("INFO ", "=== Step 1: git pull ===")
    for name, path in REPOS.items():
        state["repos"][name] = git_pull_repo(name, path)

    repos_ok = all(r.get("status") == "ok" for r in state["repos"].values())

    # 2. Protocol dir check
    log("INFO ", "=== Step 2: protocol directory ===")
    state["protocol"] = verify_protocol_dir()

    # 3. EPUB rebuild
    log("INFO ", "=== Step 3: reference EPUB rebuild ===")
    for book in EPUB_BOOKS:
        state["epubs"][book] = build_epub(book)

    epubs_ok = all(b.get("status") == "ready" for b in state["epubs"].values())

    # 4. Toolchain health
    log("INFO ", "=== Step 4: G0DM0D3 + OBLITERATUS ===")
    state["toolchain"] = verify_toolchain(REPOS["G0DM0D3"], REPOS["OBLITERATUS"])

    toolchain_ok = (
        state["toolchain"]["g0dm0d3"].get("present", False)
        and state["toolchain"]["obliteratus"].get("present", False)
    )

    # 5. Env vars
    log("INFO ", "=== Step 5: env vars ===")
    state["env"] = verify_env()

    # 6. The FORCED-CHOICE instrument -- the one a run now actually uses.
    log("INFO ", "=== Step 6: forced-choice instrument ===")
    state["compass"] = verify_compass()

    # 7. Gates must already pass before new runs land.
    log("INFO ", "=== Step 7: pre-run gates ===")
    state["gates"] = run_pre_run_gates()

    # 8. Floor pair counts BEFORE the run, so a collection that lands nowhere is a
    #    subtraction rather than something nobody notices. See snapshot_floors.
    log("INFO ", "=== Step 8: floor snapshot ===")
    state["floors_before"] = snapshot_floors()

    # 9. Verdict
    state["completed_at"] = datetime.datetime.utcnow().isoformat() + "Z"
    compass_ok = state["compass"]["status"] == "ok"
    gates_ok = state["gates"]["status"] == "ok"
    all_ok = (
        repos_ok
        and state["protocol"]["status"] == "ok"
        and epubs_ok
        and toolchain_ok
        and state["env"]["all_required_ok"]
        and compass_ok
        and gates_ok
    )
    state["status"] = "ready" if all_ok else "failed"

    out_path = write_prep_state(state, run_dir)
    log("INFO ", f"prep-state written to {out_path}")

    if all_ok:
        log("OK   ", "=== READY — bias study may proceed ===")
        return 0
    else:
        log("ERROR", "=== FAILED — bias study MUST NOT proceed; fix and re-run ===")
        return 1


if __name__ == "__main__":
    sys.exit(main())
