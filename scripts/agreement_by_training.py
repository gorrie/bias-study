#!/usr/bin/env python3
"""Does the panel's agreement survive models trained outside the alignment consensus?

WHY THIS EXISTS
---------------
The study's most quotable result is that models answer contested normative propositions at
almost exactly the unanimity they bring to matters of record -- 97.0% against 98.9%. The first
objection any reviewer raises is that this is not a fact about models but about **shared
training**: one alignment consensus, one set of RLHF preferences, reproduced across a panel that
is less independent than its vendor count suggests.

That objection is testable on data already collected, and it was not being tested. The panel
contains three classes of model that sit outside the consensus in different ways:

  * **abliterated / uncensored builds** -- the refusal direction projected out of the weights.
    This is the decisive one. If the positions were installed by safety tuning, the one
    intervention that removes safety tuning should disturb them.
  * **Chinese-jurisdiction vendors** -- trained under a different regulatory regime entirely.
  * **2024-generation local open-weight builds** -- trained before the current consensus.

WHAT IT FOUND, 2026-09-20
-------------------------
The agreement does not weaken. It is **strongest** where the consensus is weakest:

    abliterated / uncensored      100.0% normative, 100.0% documented
    hosted, Chinese-jurisdiction   99.6%            99.4%
    hosted, US/EU-jurisdiction     95.4%            99.2%
    local open-weight, 2024        94.9%            96.4%

Models with the refusal direction cut out of their weights agree with every normative
proposition in the bank. The class that agrees LEAST is US/EU frontier, which is also the only
class with a real normative-versus-documented gap.

WHAT THAT RULES OUT, AND WHAT IT DOES NOT
-----------------------------------------
**Ruled out: RLHF as the source.** Abliteration removes it; the positions stay.

**NOT ruled out: shared pretraining.** Abliteration cuts a refusal direction, not a prior. If
every model in the field trains on overlapping web text, all of them inherit the same priors and
this test cannot see it -- the intervention leaves that layer untouched. Separating the two
needs a corpus contrast this study does not have.

**NOT ruled out: the items being easy.** `item_gradient.py` shows the bank is bimodal with
nothing between 30% and 70%, so an instrument with no contested middle cannot distinguish a
model that holds a position from a proposition that is simply not arguable.

This is EXPLORATORY and uncorrected. It was computed after the data was seen, in answer to an
objection, and it is counted as such in `multiple_comparisons.py`.

    python scripts/agreement_by_training.py
    python scripts/agreement_by_training.py --markdown
    python scripts/agreement_by_training.py --check

Exit 0, 1 the panel is too thin in some class to read, 2 NOT APPLICABLE.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, HERE)

WAVE = "2026-09-16-ratchet-v3-wave"

#: Agreement cut, identical to key_numbers and item_gradient. Asserted equal by test.
AGREE_ABOVE = 1.5

#: A model contributing fewer observations than this is not ranked -- its rate is noise.
MIN_OBS = 20

#: A class with fewer models than this cannot carry a comparison, and saying so beats
#: printing a percentage computed over two models as though it were a population.
MIN_MODELS_PER_CLASS = 3

#: Substrings that identify a build whose refusal direction has been projected out. THE
#: DECISIVE CLASS: if these agree at the panel rate, safety tuning is not what installed the
#: agreement. Matched on the model id because that is what the corpus carries -- there is no
#: metadata field for it, and inventing one would be a second copy of a fact the id already has.
ABLATED_MARKERS = ("abliterat", "obliterat", "heretic", "uncensored", "huihui")

#: Vendors serving from, or headquartered in, a Chinese regulatory jurisdiction.
#:
#: HAND-MAINTAINED, AND THE NEAREST THING TO A CANONICAL LIST DOES NOT MATCH IT.
#: `aggregate.VENDOR_CLASS` carries prefix rules splitting `chinese-open` from
#: `chinese-closed` for a different question, and `jurisdiction_gradient` tags ITEMS rather
#: than vendors. So there is no single existing list to import, and claiming this one is synced
#: to another would be a second copy of a fact dressed as a single source. A vendor missing
#: here lands in "hosted, US/EU-jurisdiction" and dilutes that row -- which is the direction
#: that makes §3b's contrast look SMALLER, so the error is conservative. Checked by test
#: against the models actually in the corpus, not against another list.
CN_VENDORS = ("z-ai", "deepseek", "qwen", "moonshotai", "minimax", "xiaomi",
              "baidu", "tencent", "01-ai", "alibaba")


def training_class(model):
    """Which side of the alignment consensus this build sits on."""
    low = model.lower()
    if any(t in low for t in ABLATED_MARKERS):
        return "abliterated / uncensored"
    if "/" not in model or low.startswith("hf.co"):
        # An ollama-style bare id, or a HuggingFace path: a build run LOCALLY, which in this
        # corpus means the 2024 generation at Q4.
        return "local open-weight, 2024"
    return ("hosted, Chinese-jurisdiction"
            if model.split("/")[0].lower() in CN_VENDORS
            else "hosted, US/EU-jurisdiction")


def measure(run_dir=WAVE, condition="N"):
    import position_analysis as P
    from studypaths import runs_root
    bank = P.load_bank()["items"]
    normative = {i["id"] for i in bank
                 if i["frame"] == "critic" and i.get("claim_type") == "normative"}
    documented = {i["id"] for i in bank
                  if i["frame"] == "critic" and i.get("claim_type") == "documented"}

    agree = collections.defaultdict(collections.Counter)
    total = collections.defaultdict(collections.Counter)
    for rec in P.load_records(str(runs_root() / run_dir)):
        if rec.get("condition") != condition:
            continue
        m = rec["model"]
        for qid, pos in rec["answers"].items():
            kind = "norm" if qid in normative else ("doc" if qid in documented else None)
            if kind is None:
                continue
            total[m][kind] += 1
            if pos > AGREE_ABOVE:
                agree[m][kind] += 1

    per_model = {m: {"normative": agree[m]["norm"] / total[m]["norm"],
                     "documented": (agree[m]["doc"] / total[m]["doc"]
                                    if total[m]["doc"] else None),
                     "n": total[m]["norm"], "class": training_class(m)}
                 for m in total if total[m]["norm"] >= MIN_OBS}
    if not per_model:
        return None

    classes = collections.defaultdict(lambda: [0, 0, 0, 0, []])
    for m, r in per_model.items():
        c = classes[r["class"]]
        c[0] += agree[m]["norm"]
        c[1] += total[m]["norm"]
        c[2] += agree[m]["doc"]
        c[3] += total[m]["doc"]
        c[4].append(m)

    out = {}
    for label, (na, nt, da, dt, models) in classes.items():
        out[label] = {
            "models": len(models),
            "normative": na / nt if nt else None,
            "documented": da / dt if dt else None,
            "thin": len(models) < MIN_MODELS_PER_CLASS,
            "model_ids": sorted(models),
        }
    unanimous = sum(1 for r in per_model.values() if r["normative"] == 1.0)
    return {"classes": out, "per_model": per_model,
            "panel": len(per_model), "unanimous_models": unanimous}


def markdown(res):
    rows = sorted(res["classes"].items(), key=lambda kv: -(kv[1]["normative"] or 0))
    out = ["| how the model was trained | models | contested normative | matters of record | gap |",
           "|---|---:|---:|---:|---:|"]
    for label, v in rows:
        n = 100 * v["normative"]
        d = 100 * v["documented"] if v["documented"] is not None else None
        out.append("| %s%s | %d | **%.1f%%** | %s | %s |"
                   % (label, " *(thin)*" if v["thin"] else "", v["models"], n,
                      "—" if d is None else "%.1f%%" % d,
                      "—" if d is None else "%+.1f" % (n - d)))
    out.append("")
    out.append("%d of %d models agree with **every** normative proposition in the bank."
               % (res["unanimous_models"], res["panel"]))
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run", default=WAVE)
    ap.add_argument("--condition", default="N")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--markdown", action="store_true")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 when the decisive class (abliterated builds) is too thin "
                         "to carry the comparison")
    a = ap.parse_args(argv)

    res = measure(a.run, a.condition)
    if not res:
        print("NOT APPLICABLE: no model has %d+ normative observations at condition %s."
              % (MIN_OBS, a.condition))
        return 2

    if a.markdown:
        print(markdown(res))
        return 0
    if a.json:
        print(json.dumps({k: v for k, v in res.items() if k != "per_model"},
                         indent=2, sort_keys=True, default=str))
        return 0

    print("AGREEMENT BY HOW THE MODEL WAS TRAINED -- condition %s, %s"
          % (a.condition, a.run))
    print("  If the 97%% were a shared alignment consensus, it should FALL on the classes")
    print("  trained outside it. The abliterated row is the decisive one: it is the only")
    print("  intervention here that removes safety tuning from the weights.")
    print()
    print("  %-30s %7s %12s %12s %8s"
          % ("class", "models", "normative", "documented", "gap"))
    for label, v in sorted(res["classes"].items(), key=lambda kv: -(kv[1]["normative"] or 0)):
        n = 100 * v["normative"]
        d = 100 * v["documented"] if v["documented"] is not None else float("nan")
        print("  %-30s %7d %11.1f%% %11.1f%% %+7.1f%s"
              % (label, v["models"], n, d, n - d, "  THIN" if v["thin"] else ""))
    print()
    print("  %d of %d models agree with EVERY normative proposition."
          % (res["unanimous_models"], res["panel"]))
    print()
    print("  RULES OUT: RLHF as the source -- abliteration removes it, the positions stay.")
    print("  DOES NOT RULE OUT: shared pretraining. Abliteration cuts a refusal direction,")
    print("  not a prior, so a consensus inherited from overlapping web text is invisible")
    print("  to this test. Nor the items being easy -- see item_gradient.py, which finds")
    print("  nothing between 30%% and 70%%.")
    print()
    print("  EXPLORATORY and uncorrected: computed after the data was seen, in answer to an")
    print("  objection. Counted as such in multiple_comparisons.py.")

    if not a.check:
        return 0
    decisive = res["classes"].get("abliterated / uncensored")
    if not decisive or decisive["thin"]:
        print()
        print("DEFECT: the abliterated class carries %d model(s), under the %d this "
              "comparison needs. Without it the RLHF objection is not answered -- the other "
              "rows vary jurisdiction and vintage, neither of which removes safety tuning."
              % (0 if not decisive else decisive["models"], MIN_MODELS_PER_CLASS))
        return 1
    print()
    print("OK: the decisive class carries %d models." % decisive["models"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
