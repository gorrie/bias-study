"""Run RELEASE-v2.md's release checklist instead of asserting it.

The checklist says "every item verifiable, none aspirational". This runs the verifiable ones so
the release verdict is measured rather than asserted -- the 2026-09-07 review's finding was that
items 1, 2, 3, 9 and 10 failed while the document said the release was ready.
"""
import argparse
import os
import subprocess
import sys

PY = sys.executable
STUDY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIRROR = os.path.normpath(os.path.join(STUDY, "..", "..", "..", "bias-study-release"))


def run(cwd, *args, timeout=2700):
    r = subprocess.run([PY] + list(args), cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


CHECKS = [
    # `tests/` IS RUN, and was not until 2026-09-12. Both trees keep tests in scripts/ (beside
    # the module) AND in tests/, and the gate only ever invoked scripts/. Four mirror tests
    # and one study test -- eligibility, power, two-corpus routing, sweep status, release
    # exit codes -- were therefore never executed by the release gate that certified them.
    ("1  gates green (mirror suite)", MIRROR, ["-m", "pytest", "scripts/", "tests/", "-q"]),
    ("1  gates green (study suite)", STUDY, ["-m", "pytest", "scripts/", "tests/", "-q"]),
    ("2  check_no_fork == 0 forks", STUDY, ["scripts/check_no_fork.py"]),
    ("5  no retracted phrase (release)", MIRROR, ["scripts/key_numbers.py", "--check-release"]),
    ("5  no retracted phrase (paper)", STUDY, ["scripts/key_numbers.py", "--check"]),
    ("5  no retracted phrase (website)", STUDY, ["scripts/key_numbers.py", "--check-website"]),
    ("8  instrument absent from mirror", MIRROR, ["scripts/check_corpus.py", "--all"]),
    # The ten analysis gates were never in this checklist, though VERIFICATION-2026-09-08 cites
    # them as release evidence. They reproduce the published WRITEUP numbers from the corpus --
    # thirteen rows, five intervals excluding zero, the BH survivors, the agreement figures --
    # which is precisely what a release must not get wrong. Mirror only: they check the
    # PUBLISHED layout and exit 2 as not-applicable anywhere else.
    ("9  analysis gates reproduce the writeup", MIRROR, ["scripts/selftest_analysis.py"]),
    ("9  README numbers match runs/", MIRROR, ["scripts/gen_readme.py", "--check"]),
    ("9  SCRIPTS.md matches disk", MIRROR, ["scripts/gen_script_inventory.py", "--check"]),
    ("9  skill docs have no dead paths", MIRROR, ["scripts/check_skill_docs.py", "--strict"]),
    # BOTH TREES, because the two failure modes are on opposite sides. The mirror is where a
    # dead link is read by someone who cannot see the private tree -- it shipped
    # `../../../bias-study-release/CORRECTIONS.md`, a path only correct from the private side,
    # until 2026-09-07. The study tree is where a rename happens: a results document gets a new
    # name when its conclusion is superseded, and every reference to the old one then points at
    # a retracted finding.
    ("9  markdown links resolve (mirror)", MIRROR, ["scripts/check_doc_links.py"]),
    ("9  markdown links resolve (study)", STUDY, ["scripts/check_doc_links.py"]),
    ("3  paper generated blocks fresh", STUDY, ["scripts/gen_paper.py", "--check"]),
    # Item 10 was a human-read item until 2026-09-12. It is a claim about what a READER can do
    # without a key, and the failure it guards is invisible to us: a script reaching for a key
    # it does not need fails only for the person who lacks one, and we always have one. So it
    # runs the documented no-key path in a stripped env instead of being read.
    ("10 no-key reproduction (mirror)", MIRROR, ["scripts/check_no_key_repro.py", "--quiet"]),
    # Item 7 was also listed as needing a human read while being a command that returns an exit
    # code. --strict fails unless every "no" verdict in the controls matrix is sourced from a
    # paper actually read or retrieved, which is the property the item asks about.
    ("7  external claims rest on the paper", STUDY, ["scripts/controls_audit.py", "--strict"]),
]

HUMAN_CHECKS = [
    "3  every arm at final n or cut  -- ablation arm now n=5; wave 0 has 12 short cells,",
    "   disclosed and unrepairable without breaking the one-sitting rule",
    "4  CORRECTIONS covers every withdrawal -- 14 entries; needs a read, not a count",
    "6  the ours row is generated -- key_numbers --sync-ours writes it. NOT mechanised on "
    "   purpose: --sync-ours WRITES, and a release gate that mutates the tree it is judging "
    "   cannot be trusted to have judged it. Verified by hand 2026-09-12: no change produced.",
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
    fails = [(label, where, rc, tail) for label, where, rc, tail in results if rc != 0]
    print("")
    if not fails:
        print("every mechanically verifiable checklist item passes.")
    else:
        print("%d mechanical check(s) FAIL:" % len(fails))
        for label, where, rc, tail in fails:
            print("")
            print("  %s [%s] rc=%d%s" % (label, where, rc, "  ERRORED" if rc == 99 else ""))
            for line in tail:
                print("      %s" % line[:150])
    print("")
    print("Human review remains required. NOT mechanically checkable here:")
    print("(these are OUTSTANDING -- they are not covered by the exit code either way):")
    for line in HUMAN_CHECKS:
        print("  %s" % line)
    print("")
    if fails:
        print("VERDICT: NOT RELEASABLE -- %d mechanical check(s) failed; exit 1." % len(fails))
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
    print("RELEASE-v2 CHECKLIST, run rather than asserted")
    print("")
    results = []
    for label, cwd, args in checks:
        try:
            rc, out = runner(cwd, *args, timeout=args_ns.timeout)
        except Exception as exc:                    # noqa: BLE001
            rc, out = 99, "ERROR %s" % exc
        where = "mirror" if cwd == MIRROR else "study "
        print("  [%s] %-36s %s" % (where, label, "PASS" if rc == 0 else "FAIL (rc=%d)" % rc))
        results.append((label, where, rc, out.strip().splitlines()[-6:]))
    return report(results)


if __name__ == "__main__":
    sys.exit(main())
