#!/usr/bin/env python3
"""bias-study-prep: lightweight verify (no pulls, no rebuilds).

Use this between full refresh runs to quickly re-check protocol-file
presence, toolchain location, and env vars without the time cost of
git pulls or EPUB rebuilds. Useful for "did anything change since I
last ran refresh.py?" checks.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Re-use refresh.py functions
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from refresh import (  # noqa: E402
    BIAS_STUDY_DIR,
    REPOS,
    log,
    verify_env,
    verify_protocol_dir,
    verify_toolchain,
)


def main() -> int:
    log("INFO ", "bias-study-prep: verify-state (lightweight)")

    state = {
        "protocol": verify_protocol_dir(),
        "toolchain": verify_toolchain(REPOS["G0DM0D3"], REPOS["OBLITERATUS"]),
        "env": verify_env(),
    }

    all_ok = (
        state["protocol"]["status"] == "ok"
        and state["toolchain"]["g0dm0d3"].get("present", False)
        and state["toolchain"]["obliteratus"].get("present", False)
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
