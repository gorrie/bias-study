#!/usr/bin/env python3
"""bias-study-prep: log prep-state to the run directory.

This is normally called by refresh.py at the end of its pipeline. Exposing
it as a standalone script allows reconstructing or amending prep-state.json
without re-running the full refresh.

Usage:
    python log-prep-state.py [<run-date>]

If <run-date> is omitted, uses today's date. Reads the most recent
in-memory state from a sibling file `prep-state.partial.json` if present,
otherwise emits a minimal placeholder with only the date and a notes field.
"""
from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from refresh import BIAS_STUDY_DIR, log, write_prep_state  # noqa: E402


def main() -> int:
    today = datetime.date.today().isoformat()
    run_date = sys.argv[1] if len(sys.argv) > 1 else today

    run_dir = BIAS_STUDY_DIR / "runs" / run_date

    partial = SCRIPT_DIR.parent / "prep-state.partial.json"
    if partial.exists():
        with partial.open("r", encoding="utf-8") as f:
            state = json.load(f)
        log("INFO ", f"loaded partial state from {partial}")
    else:
        state = {
            "skill_version": "1.0.0",
            "target_run_date": run_date,
            "status": "manual",
            "notes": "Created by log-prep-state.py without an upstream refresh.py invocation. Treat as placeholder, not as a clean pre-flight.",
            "logged_at": datetime.datetime.utcnow().isoformat() + "Z",
        }

    out_path = write_prep_state(state, run_dir)
    log("OK   ", f"prep-state written to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
