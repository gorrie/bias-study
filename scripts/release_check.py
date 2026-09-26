"""Run RELEASE-2026-09-07.md's release checklist instead of asserting it.

The checklist says "every item verifiable, none aspirational". This runs the verifiable ones so
the release verdict is measured rather than asserted -- the 2026-09-07 review's finding was that
items 1, 2, 3, 9 and 10 failed while the document said the release was ready.
"""
import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gates as G  # noqa: E402

PY = sys.executable
STUDY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: WHICH TREE IS THE MIRROR DEPENDS ON WHICH TREE THIS RUNS IN, and hardcoding the relative
#: path made this gate unrunnable in the thing it gates. `STUDY/../../../bias-study-release`
#: resolves from the private study tree; run from the mirror itself it points three levels
#: ABOVE the mirror at a directory that does not exist, and every one of the nine checks died
#: with `[WinError 267] The directory name is invalid` -- counted as failures, so the release
#: verdict in a public clone was NOT RELEASABLE for a reason that had nothing to do with the
#: release. key_numbers.py carries the same resolution with the same comment; this is the
#: third script to need it.
_SIBLING = os.path.normpath(os.path.join(STUDY, "..", "..", "..", "bias-study-release"))
MIRROR = _SIBLING if os.path.isdir(_SIBLING) else STUDY

#: True when this IS the public mirror, so the study-tree checks have no tree to run in.
#: They are then NOT APPLICABLE (exit 2), not failures: the mirror does not contain the
#: private study, and reporting its absence as a defect teaches an operator to ignore the
#: verdict. `0 pass / 1 defect / 2 not applicable` is the convention across these gates.
RUNNING_IN_MIRROR = MIRROR == STUDY


def run(cwd, *args, timeout=2700):
    if cwd is None:
        # THE TREE THIS GATE NEEDS IS NOT HERE, so it does not run -- it reports.
        # The previous version fell back to "the mirror is this tree", which meant the
        # study-side checks re-ran the mirror's own suite and the checklist printed
        # "gates green (study suite)" from a tree that has no study in it. A gate that
        # reports on something it did not read is worse than one that refuses.
        return 2, ("NOT APPLICABLE: this gate needs the other tree, which is not present "
                   "here. Run it from the tree that holds it.")
    try:
        r = subprocess.run([PY] + list(args), cwd=cwd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        # A TIMEOUT IS NOT A DEFECT. It is a gate that never answered, and the remedy is
        # completely different: a defect is fixed in the check, a timeout in the budget or
        # the cost. Conflating them cost this project four refused collection stages on
        # 2026-09-18 -- the prerun runner read "timed out" as rc 1 and would not spend.
        # It still BLOCKS (failing open on an unanswered question is worse), but it says
        # which kind of not-passing it is. Matches `gates.TIMEOUT`.
        return G.TIMEOUT, ("NO ANSWER: still running after %ss. This gate found nothing "
                           "wrong -- it did not finish. Re-run it alone, or raise "
                           "--timeout." % timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


#: THE CHECKLIST IS DERIVED, NOT TYPED. It was a literal list beside `gates.py`'s
#: registry, which is two copies of the same fact -- the shape this repository has
#: corrected in its prose four times. A gate declared in the registry at stage
#: "release" is in this checklist by construction, and one that is not cannot be
#: silently left out of it.
#:
#: `None` as the cwd means the tree that gate needs is not present here. `run()`
#: returns 2 (NOT APPLICABLE) rather than running it somewhere else -- which is what
#: the previous version did, printing "gates green (study suite)" from a mirror that
#: had just re-run its own suite under a study label.
def _checks():
    out = []
    for g in G.for_stage("release"):
        argv = ["-m", "pytest", "scripts/", "tests/", "-q"] if g.script == "pytest" \
            else g.argv()
        out.append((g.label, g.cwd(), argv))
    return out


CHECKS = _checks()


#: The date the CORRECTIONS read was performed, and the number of entries read that day.
#: BOTH ARE FROZEN ON PURPOSE. The count of entries in the file today is measured, not typed,
#: so the two numbers can disagree -- and when they do, the disagreement is the finding.
#: 2026-09-12: the author read #1-#14. 2026-09-24: a Fable read of #15-#28, which the author
#: ruled stands in for the human read, added #29-#30 -- VERIFICATION-2026-09-24-corrections-read.md.
CORRECTIONS_READ_ON = "2026-09-24"
CORRECTIONS_READ_COUNT = 30


def _corrections_now():
    """Numbered entries in the mirror's CORRECTIONS.md, counted from its own headings.

    THE HUMAN ITEM USED TO SAY "All 14 entries read" AS A FIXED STRING, and it went on saying
    it while the file grew to 27. A human-review note that states its own coverage without
    measuring what it covers is the same two-copies-of-a-fact defect the rest of this
    repository has corrected repeatedly -- and it is worse here, because it appears under a
    heading that tells the reader these items are outstanding, which makes a stale one read
    as diligence.
    """
    for path in _corrections_paths():
        if os.path.exists(path):
            with open(path, encoding="utf-8", errors="replace") as fh:
                return sum(1 for line in fh if line.startswith("### "))
    return None


def _corrections_paths():
    """This tree's CORRECTIONS.md, then the sibling mirror's.

    CORRECTIONS.md IS A PUBLIC-FACING DOCUMENT and lives in the mirror; the private study
    carries dated `CORRECTIONS-*.md` files instead. Looking only beside this script returns
    None from the tree the work is done in, which turns a measured number back into a shrug --
    the same defect `key_numbers._corrections_entries` was fixed for on 2026-09-21. `MIRROR`
    is already resolved above for exactly this, and resolves to `STUDY` when this IS the
    mirror, so the two candidates collapse to one there.
    """
    return (os.path.join(STUDY, "CORRECTIONS.md"), os.path.join(MIRROR, "CORRECTIONS.md"))


def _corrections_human_check():
    """Item 4, as a FIXED NUMBER OF ELEMENTS whatever the drift.

    `HUMAN_CHECKS` is counted by `tests/test_release_counts.py` against the split sentence in
    RELEASE-2026-09-07.md, and it counts list ELEMENTS, which here are lines. So a conditional
    `append` changes the stated size of the checklist whenever CORRECTIONS.md moves -- the
    first version of this function did exactly that and turned a document-drift warning into a
    failing release gate. The drift line rides inside the head element instead.
    """
    now = _corrections_now()
    drift = ""
    if now is None:
        head = ("4  CORRECTIONS covers every withdrawal -- READ %s. CORRECTIONS.md is not in "
                "this tree, so its" % CORRECTIONS_READ_ON)
        drift = "\n   current entry count cannot be confirmed from here."
    else:
        head = ("4  CORRECTIONS covers every withdrawal -- READ %s, PASSES for the %d entries "
                "that existed then." % (CORRECTIONS_READ_ON, CORRECTIONS_READ_COUNT))
        if now > CORRECTIONS_READ_COUNT:
            drift = ("\n   ** %d entries now: %d ADDED SINCE THE READ AND NOT COVERED BY IT. **"
                     % (now, now - CORRECTIONS_READ_COUNT))
        elif now < CORRECTIONS_READ_COUNT:
            drift = ("\n   ** %d entries now, FEWER than the %d read -- an entry was removed. **"
                     % (now, CORRECTIONS_READ_COUNT))
    return [
        head + drift,
        "   Six of STATUS's ten withdrawals correctly have no public entry because they were",
        "   never published (verified zero occurrences across the mirror and website, not",
        "   assumed). VERIFICATION-%s-corrections-read.md. Still listed here because it stays"
        % CORRECTIONS_READ_ON,
        "   a human read: two attempts to mechanise it produced false positives on sound"
        " entries.",
    ]


HUMAN_CHECKS = [
    "3  every arm at final n or cut  -- the wave's short cells completed 2026-09-25 (PREREG-",
    "   2026-09-25-wave-completion); cells that cannot change a verdict are named there and cut",
] + _corrections_human_check() + [
    "6  the ours row is generated -- key_numbers --sync-ours writes it. NOT mechanised on\n"
    "     purpose: --sync-ours WRITES, and a release gate that mutates the tree it is\n"
    "     judging cannot be trusted to have judged it. Verified by hand 2026-09-12: no\n"
    "     change produced.",
]


def report(results):
    """Print the run and return the process exit code.

    SEPARATED FROM THE RUNNING so the exit logic is testable without spending 45 minutes of
    real checks -- which is how this defect survived: the only way to exercise it was to run
    the whole checklist, so nobody did, and the script printed "N item(s) FAIL" and exited 0.
    A release gate that reports failure and returns success is worse than no gate; it is a
    gate that has been taught to be ignored.

    `results` is [(label, where, rc, tail)]. Exit 0 only when every MECHANICAL check passed.
    The human-read items below are never part of that verdict and the output says so: they
    are outstanding work, not a pass, and folding them into a green exit is the same
    assertion-instead-of-measurement this script exists to replace.
    """
    # rc 2 IS NOT A FAILURE AND IS NOT A PASS. It is the convention these gates share for
    # "this tree has no question for me to answer" -- check_no_fork, probe_budget and
    # key_numbers --check-website all use it. Counting it as a failure is what made a public
    # clone report NOT RELEASABLE over checks that were never meant to run there, and a
    # verdict that is wrong in the ordinary case is a verdict operators learn to skip.
    na = [(label, where, rc, tail) for label, where, rc, tail in results if rc == 2]
    fails = [(label, where, rc, tail) for label, where, rc, tail in results
             if rc not in (0, 2)]
    print("")
    if na:
        print("%d check(s) NOT APPLICABLE in this tree (rc=2) -- reported, not counted:"
              % len(na))
        for label, where, _rc, _tail in na:
            print("  %s [%s]" % (label, where))
        print("")
    # Split out of `fails` for reporting only -- still blocking, still in the exit code.
    timed_out = [r for r in fails if r[2] == G.TIMEOUT]
    defects = [r for r in fails if r[2] != G.TIMEOUT]
    if not fails:
        print("every mechanically verifiable checklist item passes.")
    else:
        if defects:
            print("%d mechanical check(s) FAIL:" % len(defects))
            for label, where, rc, tail in defects:
                print("")
                print("  %s [%s] rc=%d%s"
                      % (label, where, rc, "  ERRORED" if rc == 99 else ""))
                for line in tail:
                    print("      %s" % line[:150])
        if timed_out:
            print("")
            print("%d check(s) TIMED OUT -- they found NOTHING, they did not finish:"
                  % len(timed_out))
            for label, where, _rc, tail in timed_out:
                print("  %s [%s]" % (label, where))
                for line in tail:
                    print("      %s" % line[:150])
            print("  These block, because an unanswered question is not a pass. But do not")
            print("  debug them as failures: raise --timeout or make the check cheaper.")
    print("")
    print("Human review remains required. NOT mechanically checkable here:")
    print("(these are OUTSTANDING -- they are not covered by the exit code either way):")
    for line in HUMAN_CHECKS:
        print("  %s" % line)
    print("")
    if fails:
        print("VERDICT: NOT RELEASABLE -- %d mechanical check(s) did not pass (%d failed, "
              "%d timed out); exit 1." % (len(fails), len(defects), len(timed_out)))
        return 1
    print("VERDICT: every mechanical check passes; exit 0. The human items above are still owed.")
    return 0


def main(argv=None, *, checks=None, runner=None):
    """`checks` and `runner` are injectable so the exit logic is testable without a 45-minute
    real run -- the same reason report() is separate. `--timeout` exists to verify failure
    PROPAGATION quickly: a short timeout turns slow checks into failures on purpose, which is
    how you confirm the gate still returns 1 rather than swallowing them."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--timeout", type=float, default=2700,
                    help="timeout per mechanical check in seconds (default: 2700)")
    args_ns = ap.parse_args(argv)
    if args_ns.timeout <= 0:
        ap.error("--timeout must be positive")
    runner = run if runner is None else runner
    checks = CHECKS if checks is None else checks
    if not checks:
        print("FAIL: no checks configured")
        return 1
    print("RELEASE-2026-09-07 CHECKLIST, run rather than asserted")
    print("")
    results = []
    for label, cwd, args in checks:
        try:
            rc, out = runner(cwd, *args, timeout=args_ns.timeout)
        except Exception as exc:                    # noqa: BLE001
            rc, out = 99, "ERROR %s" % exc
        # The label names the tree the gate ACTUALLY ran in, and "absent" when it did
        # not run at all. Labelling by intent rather than by fact is how "study suite"
        # came to sit beside a mirror-suite result.
        where = ("absent" if cwd is None
                 else "mirror" if G.THIS_IS_MIRROR and cwd == STUDY
                 else "mirror" if cwd == MIRROR else "study ")
        verdict = ("PASS" if rc == 0
                   else "N/A (rc=2)" if rc == 2
                   else "TIMED OUT -- no answer" if rc == G.TIMEOUT
                   else "FAIL (rc=%d)" % rc)
        print("  [%s] %-36s %s" % (where, label, verdict))
        results.append((label, where, rc, out.strip().splitlines()[-6:]))
    return report(results)


if __name__ == "__main__":
    sys.exit(main())
