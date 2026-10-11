#!/usr/bin/env python3
"""The G0DM0D3 transform constants, PARSED from its source. Never retyped.

WHY THE STUDY READS SOMEONE ELSE'S SOURCE INSTEAD OF CALLING THEIR SERVER
-------------------------------------------------------------------------
Rung 2 -- the elicitation rung -- was originally collected by posting battery sheets to a
local G0DM0D3 proxy with pipeline flags in the body. That path has four properties that a
measurement cannot carry, all read from `api/routes/chat.ts` rather than guessed:

  1. **It needs a client key nobody has.** Auth is on whenever `GODMODE_API_KEYS` is set in
     the server's environment, and its 401/403 body is indistinguishable from a model refusal
     once it is in a log.
  2. **It discards our system message.** `[...systemPrompt, ...messages.filter(m => m.role
     !== 'system')]` -- unconditionally.
  3. **It does not report real token counts or a real finish reason.** `usage` is its own
     `Math.ceil(len/4)`; `finish_reason: 'stop'` is a string literal.
  4. **The proxy path itself is a confound.** Every rung-1 baseline goes direct to OpenRouter,
     so any "transform vs plain B" contrast measures the transform PLUS a different host,
     different defaults and different routing. That confound already published `+0.24
     [+0.02, +0.49]` on an arm that received no treatment at all.

But `godmode` is not a service. It is **a system prompt and three sampling offsets**, all of
them literals in the repository. So the study applies them itself, through the same
`run_battery` path every other rung uses: real token counts, real finish reasons, a pinned
provider, our own system prompt, and no fifth wheel to control for.

`autotune` is NOT reproduced and is not collectable as an arm. Its parameters come from
`computeAutoTuneParams(..., learnedProfiles: getSharedProfiles())` -- server-side state
mutated by an EMA feedback loop over whatever else that instance has served. Two sheets
collected an hour apart can receive different parameters for reasons nothing in our record
captures, which disqualifies it as a treatment regardless of the key.

PARSED, NOT COPIED
------------------
A hand-copied prompt is a second source of truth that drifts silently, and this one is 650+
characters of deliberately strange text. If the checkout moves or the constant is renamed,
this raises rather than falling back to a stale copy -- the same rule
`parseltongue_triggers.py` follows for the trigger list.

    python scripts/g0dm0d3_constants.py           # show what it parsed
    python scripts/g0dm0d3_constants.py --check   # exit 1 if the source cannot be read
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from pathlib import Path

#: The G0DM0D3 checkout. Referenced, never vendored.
CHECKOUT = Path(os.environ.get("G0DM0D3_DIR") or (Path.home() / "claude" / "G0DM0D3"))

#: Where each constant lives. `(file, export name)`.
SOURCES = {
    "GODMODE_SYSTEM_PROMPT": (CHECKOUT / "src" / "lib" / "godmode-prompt.ts",
                              "GODMODE_SYSTEM_PROMPT"),
    "DEPTH_DIRECTIVE": (CHECKOUT / "api" / "lib" / "ultraplinian.ts", "DEPTH_DIRECTIVE"),
}

#: `applyGodmodeBoost` (api/lib/ultraplinian.ts:605), as offsets on the caller's values:
#:     temperature: min(t + 0.1, 2.0)
#:     presence_penalty: min(p + 0.15, 2.0)
#:     frequency_penalty: min(f + 0.1, 2.0)
#: The study's baseline is temperature 0.7 with no penalties, so the boosted cell is
#: 0.8 / 0.15 / 0.1. Named here rather than inlined, and asserted against the source by
#: `check_boost_matches_source()`.
BOOST = {"temperature": 0.1, "presence_penalty": 0.15, "frequency_penalty": 0.1}
BOOST_CEILING = 2.0


class SourceUnavailable(RuntimeError):
    """The checkout is missing or the constant moved. NEVER falls back to a stale copy."""


def _read_template_literal(path: Path, name: str) -> str:
    """Extract ``export const <name> = `...` `` respecting escaped backticks."""
    if not path.exists():
        raise SourceUnavailable(
            "cannot read %s at %s. Set G0DM0D3_DIR to the checkout. This module will NOT "
            "fall back to a hardcoded copy -- a prompt nobody re-read is a prompt that has "
            "drifted." % (name, path))
    src = path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"export\s+const\s+%s\b[^=]*=\s*`" % re.escape(name), src)
    if not m:
        raise SourceUnavailable(
            "`export const %s` not found in %s -- the constant was renamed or moved, and "
            "guessing at a replacement would silently change the treatment." % (name, path))
    i = m.end()
    out = []
    while i < len(src):
        ch = src[i]
        if ch == "\\":
            out.append(src[i:i + 2])
            i += 2
            continue
        if ch == "`":
            break
        out.append(ch)
        i += 1
    else:
        raise SourceUnavailable("unterminated template literal for %s in %s" % (name, path))
    text = "".join(out)
    if not text.strip():
        raise SourceUnavailable("%s parsed to an EMPTY string -- an empty system prompt is "
                                "not a treatment, it is a second control" % name)
    return text


def godmode_system_prompt() -> str:
    return _read_template_literal(*SOURCES["GODMODE_SYSTEM_PROMPT"])


def depth_directive() -> str:
    return _read_template_literal(*SOURCES["DEPTH_DIRECTIVE"])


def system_prompt(persona: str | None = None) -> str:
    """What the server would build: `(custom_system_prompt || GODMODE) + DEPTH_DIRECTIVE`.

    `persona=None` reproduces plain `godmode: true`. A non-empty `persona` reproduces
    `custom_system_prompt`, which replaces the jailbreak persona while DEPTH_DIRECTIVE still
    rides along -- the one seam the pipeline offers, and the only way to separate the persona
    from the directive.

    An EMPTY persona is the server's own trap: `custom_system_prompt || GODMODE_SYSTEM_PROMPT`
    is a JS `||`, so `""` is falsy and falls back to the jailbreak prompt. Reproduced exactly,
    because reproducing the seam but not its edge case would make one arm quietly become
    another.
    """
    base = persona if persona else godmode_system_prompt()
    return base + depth_directive()


def boosted(temperature=0.7, presence_penalty=0.0, frequency_penalty=0.0):
    """`applyGodmodeBoost` in Python. Returns the three parameters the boost would produce."""
    # ROUNDED. 0.7 + 0.1 is 0.7999999999999999 in binary floating point, and that is what
    # would go on the wire, into the record, and into the paper's method section as the
    # temperature this arm ran at. Two decimals is the resolution every sampling parameter in
    # this study is specified to.
    return {
        "temperature": round(min(temperature + BOOST["temperature"], BOOST_CEILING), 2),
        "presence_penalty": round(
            min(presence_penalty + BOOST["presence_penalty"], BOOST_CEILING), 2),
        "frequency_penalty": round(
            min(frequency_penalty + BOOST["frequency_penalty"], BOOST_CEILING), 2),
    }


def check_boost_matches_source():
    """The offsets are three numbers, so they ARE retyped -- and therefore checked.

    Returns a list of complaints. Reads `applyGodmodeBoost` and confirms each constant still
    appears in it. A regex over someone else's source is a weak check; it is still infinitely
    stronger than three numbers nobody has looked at since they were typed.
    """
    path = CHECKOUT / "api" / "lib" / "ultraplinian.ts"
    if not path.exists():
        raise SourceUnavailable("cannot read applyGodmodeBoost at %s" % path)
    src = path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"function applyGodmodeBoost\b.*?\n\}", src, re.S)
    if not m:
        raise SourceUnavailable("applyGodmodeBoost not found in %s" % path)
    body = m.group(0)
    bad = []
    for field, delta in BOOST.items():
        # `temperature: Math.min((params.temperature ?? 0.7) + 0.1, 2.0)`
        if not re.search(r"%s\s*:.*?\+\s*%s\b" % (re.escape(field), re.escape(str(delta))),
                         body, re.S):
            bad.append("%s: BOOST says +%s, applyGodmodeBoost does not" % (field, delta))
    # `Math.min((params.temperature ?? 0.7) + 0.1, 2.0)` -- the argument contains its own
    # parentheses, so a `[^)]*` between `min(` and the ceiling can never reach it. Match the
    # ceiling as the second argument by anchoring on the comma instead.
    if not re.search(r"Math\.min\(.*?,\s*%s\s*\)" % re.escape(str(BOOST_CEILING)), body):
        bad.append("ceiling: BOOST_CEILING says %s, the source clamps elsewhere"
                   % BOOST_CEILING)
    return bad


def provenance():
    """What was read, from where, and its digest -- stamped onto every record."""
    # NO MACHINE PATHS IN A RECORD. This stamped `str(CHECKOUT)` and each absolute source path,
    # so every rung-2 record published on 2026-09-24 carried the collecting machine's home
    # directory. The checkout is named, each source is relative to it, and the digest is what
    # actually identifies the text read.
    out = {"checkout": CHECKOUT.name, "boost": dict(BOOST), "boost_ceiling": BOOST_CEILING}
    for key, (path, name) in SOURCES.items():
        text = _read_template_literal(path, name)
        try:
            rel = Path(path).relative_to(CHECKOUT).as_posix()
        except ValueError:
            rel = Path(path).name
        out[key.lower()] = {
            "path": CHECKOUT.name + "/" + rel,
            "chars": len(text),
            "sha256_12": hashlib.sha256(text.encode("utf-8")).hexdigest()[:12],
        }
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if the source cannot be read or the boost offsets no longer "
                         "match it")
    ap.add_argument("--show", action="store_true", help="print the prompts in full")
    a = ap.parse_args(argv)

    try:
        prov = provenance()
        drift = check_boost_matches_source()
    except SourceUnavailable as exc:
        print("CANNOT READ THE G0DM0D3 CONSTANTS: %s" % exc, file=sys.stderr)
        return 1 if a.check else 2

    print("G0DM0D3 TRANSFORM CONSTANTS, parsed from source")
    print("  checkout %s" % prov["checkout"])
    for key in ("godmode_system_prompt", "depth_directive"):
        d = prov[key]
        print("  %-22s %5d chars  sha256:%s" % (key, d["chars"], d["sha256_12"]))
        print("                         %s" % d["path"])
    print()
    print("  applyGodmodeBoost offsets: %s (ceiling %s)"
          % (", ".join("%s +%s" % kv for kv in sorted(BOOST.items())), BOOST_CEILING))
    print("  study baseline 0.7 / 0.0 / 0.0 -> boosted %s"
          % ", ".join("%s=%s" % kv for kv in sorted(boosted().items())))
    if drift:
        print()
        print("  DRIFT -- the retyped offsets no longer match the source:")
        for line in drift:
            print("    %s" % line)
        return 1
    print("  offsets verified against applyGodmodeBoost.")

    if a.show:
        print()
        print("=" * 72)
        print(system_prompt())
        print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
