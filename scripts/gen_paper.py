#!/usr/bin/env python3
"""Fill the generated blocks in PAPER-below-the-floor.md by running the analysis scripts.

The paper asserts that factors nobody controls for move as much as the effects everybody
reports. It would be an embarrassment for that paper to contain a hand-typed number, and the
project has produced one wrong hand-typed number per day for three days, so it does not get
the chance: every table lives between `<!-- GEN:name -->` markers and is overwritten from the
tools that own it.

`--check` exits 1 when any block differs from what the tools currently produce -- i.e. when
the corpus has grown, an analysis has changed, or someone edited a table by hand. Run it
before circulating a draft; a stale table in a paper about stale tables is the whole failure
mode restated.

    python scripts/gen_paper.py
    python scripts/gen_paper.py --check
"""
from __future__ import annotations

import argparse
import io
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
PAPER = os.path.join(STUDY, "PAPER-below-the-floor.md")
PY = sys.executable

# block name -> (script, args, how to trim the output)
BLOCKS = {
    "floors":   ("floor_table.py", ["--markdown"], None),
    "power":    ("power.py", [], None),
    "controls": ("controls_audit.py", ["--markdown"], None),
    "gaps":     ("controls_audit.py", ["--gaps"], None),
    # The paper's refusal table must match the analysis it describes, which withholds the
    # targeted floor collections. That list is refusal_table.DEFAULT_EXCLUDE and is now the
    # script's own default -- naming a run dir here made this the third copy of the same fact,
    # and on 2026-09-04 a new arm needed withholding from all three.
    "refusal":  ("refusal_table.py", [], None),
    "null":     ("floor_table.py", [], "same-version"),
    # SECTION 1'S HEADLINE TABLE. It was typed, and it disagreed with `order_floor_position`
    # -- the script the ABSTRACT's figures come from -- on both rows they share: 111 order
    # pairs against 108 and 62 significant against 46. A paper whose argument is that a
    # number typed into a document rots was leading with two versions of its own headline.
    # Slow (a 4000-draw bootstrap over every pair), which is exactly why nobody re-ran it.
    "position": ("order_floor_position.py", ["--markdown"], None),
    "references": ("references.py", [], None),
    "timeline":   ("timeline.py", ["--markdown"], None),
    # GENERATED BECAUSE HAND-TYPING IT FAILED FOUR TIMES. The pre-registered family size sat
    # in four documents as 153, 241 and 246 simultaneously -- every stale copy understating
    # the correction burden, which is the direction that flatters. `multiple_comparisons
    # --check` catches that after the fact; generating the table means the paper stops holding
    # a copy to go stale. It also forces the exploratory families into the paper, which is the
    # half of the disclosure the paper never made at all.
    "comparisons": ("multiple_comparisons.py", ["--markdown"], None),
    # §3b. The answer to "isn't this just shared RLHF?", which the paper had no answer to
    # until 2026-09-20 although the data to give one had been on disk since the wave.
    "training": ("agreement_by_training.py", ["--markdown"], None),
    # §3b, second half. The intensity result and -- inseparably -- the confound that governs
    # how it reads: `claim_type` is perfectly aligned with `ratchet` in this bank, so the
    # caveat is emitted BY the generator rather than written around it. Prose beside a table
    # can be edited away without touching the figures; this cannot.
    "intensity": ("intensity_by_claim.py", ["--markdown"], None),
}


def run(script, args):
    # encoding="utf-8" is load-bearing, not tidiness. The child is told to write UTF-8 via
    # PYTHONIOENCODING; without a matching encoding here, text=True decodes it with the
    # PARENT's locale, which is cp1252 on this machine. Every em-dash in a generated block
    # came out as three characters of mojibake -- 19 of them in the paper as committed.
    #
    # And --check could not see it, because it corrupted BOTH sides of its own comparison:
    # generated-and-mangled equals stored-and-mangled, so the gate reported "all 8 generated
    # blocks are current" over visible corruption it had introduced itself. A gate that
    # renders its input through the same defect it is checking for is not a gate.
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    proc = subprocess.run([PY, os.path.join(HERE, script)] + args,
                          capture_output=True, text=True, encoding="utf-8", env=env,
                          cwd=STUDY)
    # ANY nonzero exit, INCLUDING 1. This allowed exit 1 through as "a legitimate gate
    # failure, not a crash" and then used the failing script's partial stdout as a paper
    # block. A report that exits 1 is a report saying do not trust this output, and splicing
    # it into the paper is how a generated block ends up quoting a computation that failed
    # halfway. It matters concretely now: power.py exits 1 when a published null's reference
    # has gone missing, and that is exactly when its table must not be pasted into the paper.
    if proc.returncode != 0:
        raise SystemExit("%s failed (%d):\n%s" % (script, proc.returncode,
                                                  proc.stderr or proc.stdout))
    return proc.stdout.rstrip()


def block_body(name):
    script, args, trim = BLOCKS[name]
    text = run(script, args)
    if trim:
        # Keep the header lines plus the one row asked for, so the null section shows the
        # null in both statistics without repeating the whole floor table.
        lines = text.split("\n")
        keep = [l for l in lines if l.strip().startswith("factor") or trim in l]
        text = "\n".join(keep) if keep else text
    unfenced = ("floors", "controls", "references", "timeline", "position")
    fence = "" if name in unfenced else "```\n"
    close = "" if name in unfenced else "\n```"
    return fence + text + close


def _diff(have, want, context=1):
    """The lines that differ between the paper's block and a fresh one, paper-side first."""
    import difflib
    out = [l for l in difflib.unified_diff(have.splitlines(), want.splitlines(),
                                           fromfile="in the paper", tofile="freshly computed",
                                           lineterm="", n=context)]
    return out


def fill(text, check=False):
    stale = []
    for name in BLOCKS:
        pattern = re.compile(r"(<!-- GEN:%s -->\n)(.*?)(<!-- /GEN:%s -->)" % (name, name),
                             re.DOTALL)
        match = pattern.search(text)
        if not match:
            raise SystemExit("no GEN block named %r in the paper" % name)
        fresh = block_body(name) + "\n"
        if match.group(2).strip() != fresh.strip():
            # Carry the DIFF, not just the name. "STALE blocks: floors" is true and useless:
            # on 2026-09-06 this gate went red in CI and green on the author's machine, against
            # the same commit, and the message gave nothing to work from -- the run data, the
            # committed tree and a clean worktree all had to be eliminated by hand before the
            # environment was even a suspect. A gate that detects drift should be able to say
            # what drifted.
            stale.append((name, _diff(match.group(2).strip(), fresh.strip())))
        if not check:
            text = text[:match.start(2)] + fresh + text[match.end(2):]
    return text, stale


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)

    # The paper is not distributed with this repository -- it is written against the internal
    # working copy and published as prose elsewhere. This script IS distributed, because it is
    # named in the documented gate list, so on a fresh clone it used to die with a
    # FileNotFoundError traceback. A cloner running a gate the README tells them to run should
    # get an explanation, not a stack trace: absent target, nothing to check, exit 0.
    if not os.path.exists(PAPER):
        print("%s is not in this repository, so there is nothing to generate or check."
              % os.path.basename(PAPER))
        print("The generated tables are reproduced in README.md instead; "
              "`python scripts/key_numbers.py --check` is the gate that guards them here.")
        return 0

    raw = io.open(PAPER, encoding="utf-8", newline="").read()
    nl = "\r\n" if "\r\n" in raw else "\n"
    text = raw.replace("\r\n", "\n")

    filled, stale = fill(text, check=args.check)

    if args.check:
        if stale:
            print("STALE blocks in %s: %s"
                  % (os.path.basename(PAPER), ", ".join(n for n, _ in stale)))
            for name, lines in stale:
                print("")
                print("  --- %s" % name)
                for l in lines:
                    print("  %s" % l)
            print("")
            print("Run: python scripts/gen_paper.py")
            print("If the diff is empty or looks like formatting, the two sides were computed")
            print("in different environments -- compare Python and dependency versions before")
            print("regenerating, because regenerating would then commit THIS machine's answer.")
            return 1
        print("all %d generated blocks are current" % len(BLOCKS))
        return 0

    # READ-MODIFY-WRITE, AND THE GAP IS MINUTES WIDE. Every block is a subprocess and the
    # position block is a 4000-draw bootstrap, so this holds a whole copy of the paper in
    # memory for a long time and then overwrites the file with it. On 2026-09-21 a
    # thirty-line correction to section 2 was written during one of those runs and silently
    # erased -- the edit reported success, the checks passed, and the old text was back.
    # Nothing detected it; it surfaced from re-reading the section by eye.
    #
    # Re-read and compare before writing. If the file moved under us, refuse: the generated
    # blocks are cheap to recompute and a hand edit is not.
    current = io.open(PAPER, encoding="utf-8", newline="").read()
    if current != raw:
        print("REFUSED -- %s changed on disk while these blocks were being computed."
              % os.path.basename(PAPER))
        print("Writing now would overwrite that edit with a copy read %d character(s) ago."
              % len(raw))
        print("Nothing has been written. Re-run: python scripts/gen_paper.py")
        return 2
    io.open(PAPER, "w", encoding="utf-8", newline="").write(filled.replace("\n", nl))
    print("filled %d blocks: %s" % (len(BLOCKS), ", ".join(BLOCKS)))
    if stale:
        print("(%d were stale and have been updated: %s)" % (len(stale), ", ".join(n for n, _ in stale)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
