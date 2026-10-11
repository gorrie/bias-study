#!/usr/bin/env python3
"""bias-study-prep: lightweight verify (no pull, no gates).

Use this between full refresh runs to re-check the protocol files, the live instrument, env vars
and -- with --rung -- the external tool a rung uses, without running the pre-run gates. Useful
for "did anything change since I last ran refresh.py?" checks.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Re-use refresh.py functions
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from refresh import (  # noqa: E402
    TOOLS,
    log,
    verify_compass,
    verify_env,
    verify_protocol_dir,
    verify_tool,
)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Lightweight bias-study pre-flight: no pull, no gates.")
    ap.add_argument("--rung", action="append", choices=sorted(TOOLS), default=[],
                    help="also check the external tool this rung uses (repeatable)")
    args = ap.parse_args(argv)

    log("INFO ", "bias-study-prep: verify-state (lightweight)")
    state = {
        "protocol": verify_protocol_dir(),
        "compass": verify_compass(),
        "toolchain": {rung: verify_tool(rung) for rung in args.rung},
        "env": verify_env(),
    }

    all_ok = (
        state["protocol"]["status"] == "ok"
        and state["compass"]["status"] == "ok"
        and all(t.get("status") == "ok" for t in state["toolchain"].values())
        and state["env"]["all_required_ok"]
    )

    print(json.dumps(state, indent=2, sort_keys=True))

    if all_ok:
        log("OK   ", "verify-state CLEAN")
        return 0
    log("ERROR", "verify-state FAILED — run refresh.py for full pre-flight")
    return 1


if __name__ == "__main__":
    sys.exit(main())
