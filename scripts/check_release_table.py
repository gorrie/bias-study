#!/usr/bin/env python3
"""Does RELEASE-2026-09-07's arm inventory still match runs/?

WHY THIS EXISTS. The arm inventory is described in RELEASE-2026-09-07.md as "the whole basis of the
release", and every number in it was hand-typed onto an ungated surface. On 2026-09-12 one row
was stale: `refusal-direction ablation, one sitting` read 14 pairs at p90 8 while the arm had
grown to 20 pairs at p90 9 when the n=5 wave landed. Nothing caught it, because nothing was
looking -- the same shape as CORRECTIONS entry 13, where the public README carried seven stale
hand-typed numbers at once and was the least-gated surface in the project.

A release document whose central table is not checked against the data is an assertion. This
makes it a measurement.

SUPERSEDED IN PART, 2026-09-18, AND SAYING SO MATTERS MORE THAN THE CHECK DID
----------------------------------------------------------------------------
The arm table is now a GENERATED block (`gen_readme.py`, `GEN:release_floors`), fed by the same
`floor_table` loader this script reads. So the number comparison below compares the generator
against itself: it cannot fail, and a check that cannot fail is a vacuous pass wearing a
report.

That happened because the hand-typed table had gone comprehensively stale -- it carried the
RETIRED instrument's scale, 1,067 paraphrase pairs against a live 24 same-version -- and the
right fix for a hand-typed table is to stop typing it. The consequence is that THIS gate's
original job is done by `gen_readme --check` now.

What is still worth checking here, and is not generated:

  * an arm named in the alias map that exists in NEITHER the document nor runs/ -- a row that
    was dropped from the study without being dropped from the release definition. The
    refusal-direction ablation arms are exactly that: slated for `withdrawn/` and still
    declared shippable.
  * the SHIP / DO-NOT-SHIP column, which is a judgement and stays hand-declared.

Rows present in runs/ and rendered by the generator are reported as GENERATED and not counted
as findings, because pretending to verify them would be the defect this file was written about.

    python scripts/check_release_table.py        # report
    python scripts/check_release_table.py --quiet # exit code only

No API calls. Arithmetic on data already on disk.
"""
import argparse
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
DOC = os.path.join(STUDY, "RELEASE-2026-09-07.md")

#: The document's display name -> floor_table's name. Kept explicit rather than fuzzy-matched:
#: a near-match that silently pairs the pooled row with the one-sitting row would compare two
#: real rows and report agreement, which is the failure this file exists to catch.
ALIAS = {
    # ---- DROPPED 2026-09-18. Declared in the release definition, present in NEITHER the
    # document nor runs/. An arm the release promises and the study does not have is a
    # promise, not an inventory row.
    #
    #   "instruction paraphrase"     -- the retired instrument's paraphrase arm (1,067 pairs).
    #                                   Its replacement is being collected against
    #                                   PREREG-2026-09-18-paraphrase.md and re-enters this map
    #                                   when collection_check ACCEPTS it, not before.
    #   "prompt condition A->D, pooled" -- pooled across model classes, superseded by the
    #                                   per-class rows, which are the ones the paper cites.
    #   the two refusal-direction ablation arms -- the weight-ablation rung is out of this
    #                                   release entirely and its machinery is bound for
    #                                   withdrawn/.
    #
    # Restoring any of them requires the arm to exist in runs/ first. That is the whole point
    # of this file.
    #
    # AND ON 2026-09-20 IT TURNED OUT ONLY "instruction paraphrase" HAD ACTUALLY BEEN REMOVED.
    # The other three were described as dropped in the paragraph above and left sitting in the
    # dict below it, so the gate went on reporting them ORPHANED for two days against a
    # comment saying they were gone. A note recording an intention is not the change; this is
    # LEARNINGS #52 in a second place, found the same week -- the remedy has to be applied,
    # not written down next to the defect.
    "modal sampling error *(the estimator)*": "modal sampling error",
    "same-version variants": "same-version variants",
    "presentation order, one sitting": "presentation order, one sitting",
    "presentation order, pooled": "presentation order",
    "presentation order, one sitting, frontier": "presentation order, one sitting, frontier API",
    "run-to-run replicate": "run-to-run replicate",
    "prompt condition A→D, one sitting": "prompt condition A->D, one sitting",
    "requantisation": "requantisation",
    "presentation order, one sitting, local": "presentation order, one sitting, local open-weight",
    "prompt condition A→D, one sitting, frontier":
        "prompt condition A->D, one sitting, frontier API",
    "prompt condition A→D, one sitting, local":
        "prompt condition A->D, one sitting, local open-weight",
}

ROW = re.compile(r"^(.+?)\s{2,}(\d+)\s+(\d+) / (\d+) / (\d+)\s")


def live_rows(text=None):
    if text is None:
        text = subprocess.run([sys.executable, os.path.join(HERE, "floor_table.py")],
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", cwd=STUDY).stdout
    out = {}
    for line in text.splitlines():
        m = ROW.match(line)
        if m:
            out[m.group(1).strip()] = (int(m.group(2)), int(m.group(3)),
                                       int(m.group(4)), int(m.group(5)))
    return out


def doc_rows(doc=None):
    if doc is None:
        with open(DOC, encoding="utf-8") as f:
            doc = f.read()
    out = {}
    for line in doc.splitlines():
        if not line.startswith("| "):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 3 or cells[0] not in ALIAS:
            continue
        pairs, stats = cells[1].replace("**", ""), cells[2].replace("**", "")
        if not pairs.isdigit():
            continue
        out[cells[0]] = (int(pairs), stats)
    return out


def compare(doc=None, live=None):
    """-> (stale, missing). Both empty means the table is current."""
    d, lv = doc_rows(doc), live_rows(live)
    stale, missing = [], []
    for name, (pairs, stats) in d.items():
        key = ALIAS[name]
        if key not in lv:
            missing.append(name)
            continue
        lp, lm, l9, lx = lv[key]
        want = "%d / %d / %d" % (lm, l9, lx)
        if pairs != lp or stats != want:
            stale.append((name, "%d pairs, %s" % (pairs, stats), "%d pairs, %s" % (lp, want)))
    for name in ALIAS:
        if name not in d:
            missing.append(name)
    return stale, missing


#: STATUS.md's by-class order table. Same failure, different file: on 2026-09-12 its local row
#: read median 7 where floor_order_by_class() returns 8, and the frontier max read 13 where the
#: tool returns 14. Both pre-dated that day's work -- the identical values come out of the older
#: checkout -- so they had simply been sitting wrong in the file that calls itself the single
#: source of truth. The 21-pair frontier row in that same table is NOT checked: it is the
#: 2026-09-01 state, deliberately kept, and the sweep that took it to 66 is recorded above it.
STATUS_DOC = os.path.join(STUDY, "STATUS.md")
STATUS_ROWS = {
    "7–14B open-weight, 2024 generation": "presentation order, local open-weight",
    # The paper's own copy of the same split, which it calls "the single most important thing
    # in this paper". Hand-typed, not generated, and BOTH its maxima were wrong on 2026-09-12:
    # 22 where the tool returns 24, and 13 where it returns 14. Same row, three documents,
    # three different numbers.
    "7–14B open-weight models, 2024 generation": "presentation order, local open-weight",
    "frontier API models, 2026": "presentation order, frontier API",
}
PAPER_DOC = os.path.join(STUDY, "PAPER-no-position-only-consensus.md")


def status_rows(doc=None):
    if doc is None:
        # A RETIRED SOURCE IS A REPORTED GAP, NOT A TRACEBACK. `STATUS.md` was retired and
        # nothing updated this reader, so on 2026-09-18 this gate died with FileNotFoundError
        # -- which reads as a broken checker rather than a missing input, and is the fourth
        # gate found failing that way in one day. A crash and a failure are not the same
        # verdict: the first gets the gate skipped, the second gets the problem fixed.
        parts = []
        missing = []
        for path in (STATUS_DOC, PAPER_DOC):
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    parts.append(f.read())
            else:
                missing.append(os.path.basename(path))
        if missing:
            print("  NOTE: %s not in this tree -- its rows are not checked here."
                  % ", ".join(missing))
            print("        STATUS.md was retired; the live source of truth is PLAN.md. If a")
            print("        row lived only in STATUS.md it is now checked by nothing, which is")
            print("        a gap to close rather than a file to restore.")
        if not parts:
            raise FileNotFoundError(
                "neither %s nor %s is present -- there is no table to check"
                % (os.path.basename(STATUS_DOC), os.path.basename(PAPER_DOC)))
        doc = "\n".join(parts)
    out = {}
    for line in doc.splitlines():
        if not line.startswith("| "):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 3 or cells[0] not in STATUS_ROWS:
            continue
        if cells[1].isdigit():
            out[cells[0]] = (int(cells[1]), cells[2].replace("**", ""))
    return out


def _which_doc(name):
    """Which file a by-class row lives in. A gate that names the wrong file sends the reader
    to the wrong file, which is worse than naming none."""
    for path in (STATUS_DOC, PAPER_DOC):
        try:
            with open(path, encoding="utf-8") as f:
                if any(line.startswith("| " + name + " |") for line in f):
                    return os.path.basename(path)
        except OSError:
            pass
    return "STATUS.md/PAPER"


def compare_status(doc=None):
    """-> stale rows in STATUS.md's by-class order table."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("_ft", os.path.join(HERE, "floor_table.py"))
    ft = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ft)
    live = ft.floor_order_by_class()
    stale = []
    for name, (pairs, stats) in status_rows(doc).items():
        key = STATUS_ROWS[name]
        if key not in live:
            stale.append((name, "%d pairs, %s" % (pairs, stats), "row absent from floor table"))
            continue
        v = live[key]
        want = "%d / %d / %d" % v["side"]
        if pairs != v["n"] or stats != want:
            stale.append((name, "%d pairs, %s" % (pairs, stats),
                          "%d pairs, %s" % (v["n"], want)))
    return stale


def main(argv=None):
    # This report prints arrows. On a default-codepage Windows console that raised
    # UnicodeEncodeError and exited 1 -- a crash reading as a failed check. Same trap as
    # ablation_equivalence.py.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)
    stale, missing = compare()
    status_stale = compare_status()
    # SPLIT MISSING BEFORE THE REPORT, not inside it -- the verdict must not depend on whether
    # anyone asked for output. A first version computed `orphaned` inside `if not a.quiet` and
    # then used it in the return, so --quiet and the report disagreed about the exit code.
    # NO BARE EXCEPT. The first version of this called `arm_rows()`, which does not exist --
    # the function is `live_rows()` -- and swallowed the NameError, leaving `from_runs` empty
    # so EVERY alias entry was reported ORPHANED. Six rows were named as arms the study had
    # lost when most of them were simply being rendered by the generator. An exception
    # swallowed into a confident wrong answer is the defect this whole repository is about,
    # committed in the gate written to report it.
    from_runs = {v for v in ALIAS.values()} & set(live_rows() or {})
    generated = [n for n in missing if ALIAS.get(n) in from_runs]
    orphaned = [n for n in missing if n not in generated]

    if not a.quiet:
        if not stale and not orphaned and not status_stale:
            print("RELEASE-2026-09-07 arm inventory: all %d row(s) match runs/." % len(ALIAS))
            print("STATUS by-class order table: all %d row(s) match runs/." % len(STATUS_ROWS))
        for name, got, want in status_stale:
            print("  STALE  %s: %s\n         document: %s\n         runs/:    %s"
                  % (_which_doc(name), name, got, want))
        for name, got, want in stale:
            print("  STALE  %s\n         document: %s\n         runs/:    %s" % (name, got, want))
        # A ROW THE GENERATOR RENDERS IS NOT MISSING -- IT IS GENERATED.
        #
        # Since 2026-09-18 the arm table is a GEN block fed by the same loader this script
        # reads, so an alias entry whose runs/-side name resolves is satisfied by construction
        # and reporting it as MISSING trains a reader to ignore this gate. What is a real
        # finding is an arm declared in the release definition that exists in NEITHER place:
        # dropped from the study without being dropped from the release.
        for name in generated:
            print("  GENERATED  %s -- rendered by GEN:release_floors; not hand-checked" % name)
        for name in orphaned:
            print("  ORPHANED  %s -- declared in the release definition and present in "
                  "NEITHER the document nor runs/" % name)
        if stale or orphaned:
            print("\nThe arm inventory is 'the whole basis of the release'. An ORPHANED row is")
            print("an arm the release still promises and the study no longer has -- drop it")
            print("from the definition, or say why it ships without data.")
    return 1 if (stale or orphaned or status_stale) else 0


if __name__ == "__main__":
    sys.exit(main())
