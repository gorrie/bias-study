#!/usr/bin/env python3
"""The paper's load-bearing numbers, computed -- and a check that its prose still matches them.

Every table in PAPER-below-the-floor.md is generated. The prose around those tables is not,
and it quotes them: "twenty items of 62", "the same p90, 14 items either way", "which moves 9".
Those are hand-typed numbers sitting beside generated ones in a paper whose entire argument is
that hand-typed numbers go stale. On 2026-09-01 the frontier order sweep landed, the order
floor went from 18 pairs to 37, the detection limit moved from 20 to 16 -- and every sentence
quoting 20 was silently wrong until this file existed.

Each entry below names a quantity, computes it from `runs/`, and declares the exact phrase the
paper uses to state it. `--check` recomputes and re-greps; any mismatch exits 1 and names the
sentence to fix. This is deliberately brittle: a phrase that stops matching because the prose
was reworded is a prompt to re-read the sentence, which is the point.

    python scripts/key_numbers.py             # what the numbers are now
    python scripts/key_numbers.py --check     # do the paper's sentences still agree?
"""
from __future__ import annotations

import argparse
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
PAPER = os.path.join(STUDY, "PAPER-below-the-floor.md")
sys.path.insert(0, HERE)

import floor_table as F      # noqa: E402
import power as P            # noqa: E402
import refusal_table as R    # noqa: E402

# The exclusion gen_paper.py applies to the refusal block. Kept in sync here because the
# corpus-scale sentences in section 2 describe that same analysis.
REFUSAL_EXCLUDE = {"2026-08-31-google-orderfloor"}
AUDIT = os.path.join(STUDY, "data", "controls-audit.json")


def corpus_scale():
    """Runs, models and vendor families, counted from the corpus the paper describes.

    Added 2026-09-01 by a hostile read. Section 2's opening sentence -- "1,643 runs and 155
    models from 13 vendor families" -- had two numbers right and one wrong: vendor_of() yields
    SIXTEEN, and the generated refusal table two paragraphs earlier prints all sixteen rows.
    Three of them are not vendor families at all (this project's own harness agent, a hosting
    domain, a community fine-tuner), which is a disclosure problem rather than an arithmetic
    one -- but a paper arguing that studies fail to say what they pooled cannot state a count
    its own table contradicts.
    """
    rows = R.load(REFUSAL_EXCLUDE)
    vendors = sorted({R.vendor_of(r.get("model")) for r in rows})
    return {"runs": len(rows),
            "models": len({r.get("model") for r in rows}),
            "vendors": len(vendors),
            "vendor_list": vendors}


def matched_arms():
    """Section 1's claim, on the matched subset it describes: models present in BOTH arms.

    Added 2026-09-01 by a hostile read. The sentence read "37 refusals in 449 runs where the
    prompt carries no directive, and none in 347 runs where it carries one," across "32 models
    measured under both arms." Three of those four numbers reproduced exactly -- 32 models, 8
    that decline, 347 directive runs with zero refusals. The no-directive pair did not: 472
    runs and 38 refusals. Stale by one collection, ungated, and sitting in the paper's opening
    argument, which is the combination this whole paper is about.

    Arms are defined the way the sentence describes them: A and B carry no directive to commit
    (A asks for balance, B asks bare), D and P do (D demands commitment, P is the content-free
    placebo). C and E are excluded because they are not part of that contrast.
    """
    rows = R.load(REFUSAL_EXCLUDE)
    scoreable = [r for r in rows if R.classify(r) in ("valid", "refused")]
    no_dir, directive = {"A", "B"}, {"D", "P"}
    in_arm = {a: {r.get("model") for r in scoreable if r.get("condition") in a}
              for a in (frozenset(no_dir), frozenset(directive))}
    both = in_arm[frozenset(no_dir)] & in_arm[frozenset(directive)]
    sel = [r for r in scoreable if r.get("model") in both]
    nd = [r for r in sel if r.get("condition") in no_dir]
    di = [r for r in sel if r.get("condition") in directive]
    declining = {r.get("model") for r in nd if R.classify(r) == "refused"}
    return {"models": len(both),
            "nodir_runs": len(nd),
            "nodir_refusals": sum(1 for r in nd if R.classify(r) == "refused"),
            "dir_runs": len(di),
            "dir_refusals": sum(1 for r in di if R.classify(r) == "refused"),
            "declining": len(declining)}


def audit_scale():
    """External studies in the controls audit, and how many were read end to end.

    Added 2026-09-01 by a hostile read, which found the paper stating this count three
    different ways -- eleven, twelve, and ten -- against a record that says twelve external
    studies, nine of them read in full. `ours` is in the same JSON and must not be counted as
    a study we audited.
    """
    import json
    rec = json.load(io.open(AUDIT, encoding="utf-8"))
    studies = rec["studies"] if isinstance(rec, dict) and "studies" in rec else rec
    if isinstance(studies, dict):
        studies = [dict(v, key=k) for k, v in studies.items()]
    external = [s for s in studies if (s.get("key") or s.get("id")) != "ours"]
    full = [s for s in external if s.get("provenance") == "full-text"]
    return {"external": len(external), "full_text": len(full),
            "not_full": len(external) - len(full)}


def floors():
    out = {}
    for fn in (F.floor_order, F.floor_same_version, F.floor_quant,
               F.floor_ablation, F.floor_conditions):
        r = fn()
        if r:
            out[r["name"]] = r
    return out


def build():
    f = floors()
    pairs = P.collect()
    scale = corpus_scale()
    audit = audit_scale()
    arms = matched_arms()

    def mde(name, stat="side"):
        vals = pairs[name][stat]
        return P.mde(vals, P.pctile(vals, 1 - P.ALPHA))

    order = f["presentation order"]
    manip = f["prompt condition A->D"]
    abl = f["refusal-direction ablation"]
    null = f["same-version variants"]

    return [
        {"key": "order_mde",
         "value": mde("presentation order"),
         "what": "detection limit against the pooled order floor, side-flips, 80% power",
         "phrase": "%d items of 62, against presentation order pooled"},
        {"key": "null_mde",
         "value": mde("same-version variants"),
         "what": "detection limit against the same-version null -- the one that governs a modern study",
         "phrase": "same-version limit of %d"},
        {"key": "order_p90_local",
         "value": F.floor_order_by_class()["presentation order, local open-weight"]["side"][1],
         "what": "order floor p90 on 2024-generation open-weight models",
         # The phrase used to read "p90 %d, max 24" -- a SECOND number, hardcoded inside the
         # template for a different quantity. When the local max moved 24 -> 22 the gate's own
         # expectation went stale and it failed on a sentence that was correct. A checker that
         # smuggles an unchecked number into its expectation is a checker with a blind spot.
         "phrase": "our order floor is p90 %d"},
        {"key": "order_max_local",
         "value": F.floor_order_by_class()["presentation order, local open-weight"]["side"][2],
         "what": "order floor MAX on 2024-generation open-weight models",
         "phrase": "max %d — a different factor"},
        {"key": "order_p90_frontier",
         "value": F.floor_order_by_class()["presentation order, frontier API"]["side"][1],
         "what": "order floor p90 on 2026 frontier models",
         "phrase": "2026 frontier models gives p90 %d"},
        {"key": "order_pairs",
         "value": order["n"],
         "what": "pairs behind the order floor",
         "phrase": "The order floor rests on %d pairs"},
        {"key": "manip_p90",
         "value": manip["side"][1],
         "what": "deliberate manipulation p90, side-flips",
         "phrase": "forced commitment | %d |"},
        {"key": "null_median",
         "value": null["side"][0],
         "what": "same-version null median, side-flips",
         "phrase": "pairs differ by %d items or more with no version change"},
        {"key": "null_pairs",
         "value": null["n"],
         "what": "pairs in the same-version null",
         "phrase": "%d pairs of models that differ in size, tier, snapshot date or mode, and not in"},
        {"key": "corpus_runs",
         # Thousands-separated, because that is how the sentence writes it and the check is a
         # literal grep. A gate that only matches an unformatted integer would pass forever
         # on a sentence saying "1,643" and fail the moment anyone wrote it the way it reads.
         "value": "{:,}".format(scale["runs"]),
         "what": "runs in the corpus the paper describes, matching the refusal block's exclusion",
         "phrase": "across %s runs"},
        {"key": "corpus_models",
         "value": scale["models"],
         "what": "distinct models in that corpus",
         "phrase": "runs and %d models"},
        {"key": "corpus_vendors",
         "value": scale["vendors"],
         "what": "distinct vendor keys vendor_of() yields -- the row count of the refusal table",
         "phrase": "%d vendor families"},
        {"key": "arms_models",
         "value": arms["models"],
         "what": "models measured under both the no-directive and directive arms",
         "phrase": "Across %d models measured under both arms"},
        {"key": "arms_nodir_refusals",
         "value": arms["nodir_refusals"],
         "what": "refusals in the no-directive arm on that matched subset",
         "phrase": "there are %d refusals"},
        {"key": "arms_nodir_runs",
         "value": arms["nodir_runs"],
         "what": "no-directive runs on that matched subset",
         "phrase": "in %d runs where the prompt carries no directive"},
        {"key": "arms_dir_runs",
         "value": arms["dir_runs"],
         "what": "directive runs on that matched subset, all of them refusal-free",
         "phrase": "none in %d runs where it carries one"},
        {"key": "arms_declining",
         "value": arms["declining"],
         "what": "models in that subset that decline the instrument at least once",
         "phrase": "%d models decline the instrument"},
        {"key": "audit_external",
         "value": audit["external"],
         "what": "external studies in the controls audit, excluding ours",
         "phrase": "%d studies, nine controls"},
        {"key": "audit_full_text",
         "value": audit["full_text"],
         "what": "of those, read in full rather than retrieved as a summary",
         "phrase": "%d of the twelve read in full"},
    ]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)

    rows = build()

    if not args.check:
        print("KEY NUMBERS -- computed from runs/, and the phrase the paper uses for each")
        print()
        for r in rows:
            print("  %-14s %3d   %s" % (r["key"], r["value"], r["what"]))
            print("  %-14s       \"%s\"" % ("", r["phrase"] % r["value"]))
        print()
        print("Run --check to verify the paper's prose still says these.")
        return 0

    text = io.open(PAPER, encoding="utf-8", newline="").read().replace("\r\n", "\n")
    bad = []
    for r in rows:
        expected = r["phrase"] % r["value"]
        if expected not in text:
            bad.append(r)

    if not bad:
        print("PROSE CHECK: all %d load-bearing numbers match the paper's sentences" % len(rows))
        return 0

    print("PROSE CHECK FAILED -- %d of %d sentences disagree with the data" % (len(bad), len(rows)))
    print("Either the corpus grew and the prose is stale, or the prose was reworded.")
    print("Both need a human to re-read the sentence; neither is fixed by a find-and-replace.")
    print()
    for r in bad:
        print("  %s (%s)" % (r["key"], r["what"]))
        print("    expected in the paper: \"%s\"" % (r["phrase"] % r["value"]))
        # Show what the paper says instead, if the phrase skeleton is recognisable.
        stem = r["phrase"].split("%d")[0].strip()
        if stem and stem in text:
            i = text.index(stem)
            print("    paper currently says: ...%s..."
                  % " ".join(text[i:i + 90].split()))
        else:
            print("    (phrase not found at all -- the sentence may have been rewritten)")
        print()
    return 1


if __name__ == "__main__":
    sys.exit(main())
