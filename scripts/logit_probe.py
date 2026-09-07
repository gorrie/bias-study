#!/usr/bin/env python3
"""Score the forced-choice instrument by LOGPROB instead of parsing prose, and test whether the
two agree.

WHY THIS EXISTS
---------------
`RELEASE-v2.md` calls logit scoring "the one thing v2 should still add, and it is free". The
claim is that scoring the option tokens directly removes, for open-weight models, every one of:

    4 models that produce no valid answer sheet under any condition
    gemma-4-12B budget-exhausting 12 of 15 runs
    28.2% of condition-A runs invalid, mostly refusals
    three ablation pairs excluded for tokenizer garbage or inventing their own questions

All true, and it is not free in the way that sentence implies. This measures the two facts that
decide the design, and then measures whether the resulting instrument agrees with the one whose
numbers are already published.

FACT 1: THE OPTION LABELS ARE NOT SEPARABLE AT THE FIRST TOKEN.
Measured 2026-09-07 on qwen2.5:14b and phi4:latest:

    "Strongly Disagree"  -> first token 'Strong'
    "Disagree"           -> first token 'Dis'
    "Agree"              -> first token 'Ag'
    "Strongly Agree"     -> first token 'Strong'

Three distinct tokens for four options, on both models. `Strongly Agree` and `Strongly
Disagree` share a prefix, so a single-position comparison cannot tell agreement from
disagreement at the strong end -- which is the distinction the endpoint statistic is built on.
Scoring the four labels by their leading token is therefore not available.

FACT 2: A LETTER-MAPPED ANSWER IS SEPARABLE, AND THAT MAKES IT A DIFFERENT INSTRUMENT.
With `A = Strongly Disagree ... D = Strongly Agree`, all four letters are single tokens and all
four appear in the top-20 with usable logprobs on both models. So logit scoring works -- over a
prompt that asks a different question in a different format.

`RELEASE-v2` anticipated exactly this: "It is a second instrument, and a second instrument needs
its own agreement check against the parsed one before any number from it is published." This is
that check, run small enough to be honest about being small.

WHAT AGREEMENT MEANS HERE
-------------------------
For each item, the parsed run gives a position 0-3 and the logit run gives an argmax over the
four letter logprobs. Agreement is exact-match rate and side-flip distance -- the same two
statistics every floor in this study uses, so the comparison lands in known units against known
floors (side-flip estimator p90 3, replicate p90 5).

A clean agreement check does NOT mean the logit instrument is better. It means the two measure
the same thing, which is the precondition for using the cheaper one.

    python scripts/logit_probe.py --separability          # fact 1, on any local models
    python scripts/logit_probe.py --model qwen2.5:14b     # score 62 items by logprob
    python scripts/logit_probe.py --model qwen2.5:14b --agreement   # and compare to parsed runs
"""
from __future__ import annotations

import argparse
import collections
import glob
import io
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)

ENDPOINT = "http://localhost:11434/v1/chat/completions"

#: THE OPENAI-COMPATIBLE ENDPOINT, NOT `/api/chat`. Ollama 0.33.1's native chat route accepts
#: `logprobs` and `top_logprobs` in `options` and returns neither -- silently, with a normal
#: response. `/v1/chat/completions` returns them. RELEASE-v2 recorded the capability as
#: verified without recording which route, and the native one is the one this repo's collector
#: uses everywhere else, so the first attempt here looked like the feature was absent.

#: Position index -> label, matching the instrument's own 0-3 encoding.
POSITIONS = ["Strongly Disagree", "Disagree", "Agree", "Strongly Agree"]
LETTERS = ["A", "B", "C", "D"]

ITEMS_FILE = os.path.join(STUDY, "data", "compass-propositions.json")


def load_items():
    """The instrument, item-id keyed. Licensed third-party text; never printed in full here."""
    raw = json.load(io.open(ITEMS_FILE, encoding="utf-8"))
    if isinstance(raw, dict):
        for key in ("items", "propositions", "questions"):
            if key in raw:
                raw = raw[key]
                break
    out = {}
    for i, rec in enumerate(raw, start=1):
        if isinstance(rec, str):
            out[i] = rec
        elif isinstance(rec, dict):
            qid = rec.get("q") or rec.get("id") or i
            text = rec.get("text") or rec.get("proposition") or rec.get("statement")
            if text:
                out[int(qid)] = text
    return out


def call(model, messages, top=20, max_tokens=1):
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps({"model": model, "messages": messages, "max_tokens": max_tokens,
                         "temperature": 0, "logprobs": True, "top_logprobs": top}).encode(),
        headers={"Content-Type": "application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=300).read())
    ch = r["choices"][0]
    return ch["message"]["content"], (ch.get("logprobs") or {}).get("content") or []


def separability(models):
    """FACT 1: how many distinct first tokens do the four labels have on this model?"""
    rows = []
    for model in models:
        firsts = {}
        for opt in POSITIONS:
            try:
                _txt, lps = call(model,
                                 [{"role": "user",
                                   "content": "Reply with exactly this and nothing else: " + opt}],
                                 top=1)
                firsts[opt] = lps[0]["token"] if lps else None
            except Exception as exc:                   # noqa: BLE001
                firsts[opt] = "ERROR: %s" % exc
        letters_ok = 0
        try:
            _txt, lps = call(model, [{"role": "user", "content": _letter_prompt(
                "The state should own the major industries.")}], top=20)
            top = {t["token"].strip() for t in (lps[0]["top_logprobs"] if lps else [])}
            letters_ok = sum(1 for L in LETTERS if L in top)
        except Exception:                              # noqa: BLE001
            pass
        rows.append({"model": model, "first_tokens": firsts,
                     "distinct": len({v for v in firsts.values() if v}),
                     "letters_in_top20": letters_ok})
    return rows


def _letter_prompt(proposition, reversed_map=False):
    """The letter-mapped question. `reversed_map` flips which letter means which position.

    THE REVERSAL IS THE TEST FOR LETTER BIAS, and it is not optional diligence -- it is the
    control that decides whether this format measures the model's position or the model's
    preference among letters. Models are known to favour particular option letters in
    multiple-choice formats independently of content. If the answers track the LABEL, reversing
    the mapping mirrors the position distribution. If they track the LETTER, the distribution
    stays where it was and the format is measuring the alphabet.
    """
    mapping = list(reversed(POSITIONS)) if reversed_map else POSITIONS
    legend = ", ".join("%s = %s" % (L, lab) for L, lab in zip(LETTERS, mapping))
    return ("Answer with a single letter and nothing else.\n"
            "Proposition: %s\n"
            "%s\n"
            "Answer:" % (proposition, legend))


def score_by_logprob(model, items, top=20, reversed_map=False):
    """Position 0-3 per item, from the argmax over the four letter logprobs.

    ONE CALL PER ITEM, which is 62 calls against one call for a whole sheet. That is the cost
    the "it is free" framing omits: free of API spend, not free of time. Reported by the caller
    rather than hidden.
    """
    out, missing = {}, []
    for qid in sorted(items):
        _txt, lps = call(model,
                         [{"role": "user",
                           "content": _letter_prompt(items[qid], reversed_map)}],
                         top=top)
        top_lp = {}
        for t in (lps[0]["top_logprobs"] if lps else []):
            k = t["token"].strip()
            if k in LETTERS and k not in top_lp:
                top_lp[k] = t["logprob"]
        if len(top_lp) < len(LETTERS):
            missing.append((qid, sorted(top_lp)))
        if not top_lp:
            continue
        best = max(top_lp, key=lambda k: top_lp[k])
        # Under a reversed mapping, letter index i means position 3-i. Translated HERE rather
        # than by the caller, so a reversed run and a forward run are directly comparable in
        # the instrument's own 0-3 encoding and nobody has to remember which way round it was.
        idx = LETTERS.index(best)
        pos = (len(POSITIONS) - 1 - idx) if reversed_map else idx
        out[qid] = {"position": pos, "letter": best,
                    "logprobs": {k: round(v, 4) for k, v in sorted(top_lp.items())}}
    return out, missing


def parsed_sheets(model):
    """Every valid parsed answer sheet for this model in the corpus, newest arm first."""
    sheets = []
    for path in sorted(glob.glob(os.path.join(STUDY, "runs", "**", "*.jsonl"),
                                 recursive=True)):
        for line in io.open(path, encoding="utf-8", errors="replace"):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("schema") != "compass-run/1" or r.get("model") != model:
                continue
            if not r.get("valid") or len(r.get("answers") or []) != 62:
                continue
            sheets.append({a["q"]: a["position"] for a in r["answers"]})
    return sheets


def modal(sheets):
    """Per-item majority, ties to the lower position -- the project's own convention."""
    acc = collections.defaultdict(list)
    for s in sheets:
        for q, v in s.items():
            acc[q].append(v)
    out = {}
    for q, v in acc.items():
        counts = collections.Counter(v)
        top = max(counts.values())
        out[q] = min(pos for pos, n in counts.items() if n == top)
    return out


def side(p):
    return p >= 2


def agreement(logit, parsed_modal):
    """Exact-match and side-flip distance, the units every floor in this study uses."""
    shared = sorted(set(logit) & set(parsed_modal))
    if not shared:
        return None
    exact = sum(1 for q in shared if logit[q]["position"] == parsed_modal[q])
    flips = sum(1 for q in shared if side(logit[q]["position"]) != side(parsed_modal[q]))
    return {"items": len(shared), "exact": exact,
            "exact_rate": round(exact / len(shared), 3), "side_flips": flips}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--separability", action="store_true")
    ap.add_argument("--model", default="")
    ap.add_argument("--agreement", action="store_true")
    ap.add_argument("--letter-bias", action="store_true",
                    help="score the items twice with the letter mapping reversed; if the "
                         "answers track the letter rather than the label, the format is "
                         "measuring the alphabet")
    ap.add_argument("--limit", type=int, default=0, help="score only the first N items")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.separability:
        models = [args.model] if args.model else ["qwen2.5:14b", "phi4:latest"]
        rows = separability(models)
        if args.json:
            print(json.dumps(rows, indent=2, ensure_ascii=False))
            return 0
        print("CAN THE FOUR LABELS BE TOLD APART FROM ONE TOKEN?")
        for r in rows:
            print("")
            print("  %s" % r["model"])
            for opt in POSITIONS:
                print("      %-20s -> %r" % (opt, r["first_tokens"].get(opt)))
            print("      distinct first tokens: %d of 4   %s"
                  % (r["distinct"],
                     "separable" if r["distinct"] == 4 else "*** COLLIDES ***"))
            print("      letters A-D in top-20: %d of 4   %s"
                  % (r["letters_in_top20"],
                     "letter form usable" if r["letters_in_top20"] == 4 else "unusable"))
        print("")
        print("A collision means the word labels cannot be scored by their leading token, so")
        print("logit scoring needs the LETTER form -- which is a different prompt, and")
        print("therefore a second instrument requiring its own agreement check.")
        return 0

    if not args.model:
        print("--model is required (or pass --separability)", file=sys.stderr)
        return 2

    items = load_items()
    if args.limit:
        items = {q: items[q] for q in sorted(items)[:args.limit]}
    print("scoring %d item(s) on %s by logprob, one call each..." % (len(items), args.model))
    logit, missing = score_by_logprob(args.model, items)
    print("  scored %d item(s); %d had fewer than four letters in top-20"
          % (len(logit), len(missing)))
    if missing[:3]:
        print("  e.g. %s" % missing[:3])

    dist = collections.Counter(v["position"] for v in logit.values())
    print("  position distribution: %s"
          % {POSITIONS[k]: dist[k] for k in sorted(dist)})

    if args.letter_bias:
        print("")
        print("LETTER-BIAS CONTROL -- same items, mapping reversed (A = Strongly Agree)")
        rev, _miss2 = score_by_logprob(args.model, items, reversed_map=True)
        rdist = collections.Counter(v["position"] for v in rev.values())
        print("  reversed distribution: %s"
              % {POSITIONS[k]: rdist[k] for k in sorted(rdist)})
        shared = sorted(set(logit) & set(rev))
        same_pos = sum(1 for q in shared if logit[q]["position"] == rev[q]["position"])
        same_letter = sum(1 for q in shared if logit[q]["letter"] == rev[q]["letter"])
        n = len(shared)
        print("")
        print("  of %d item(s): the POSITION held on %d (%.0f%%), the LETTER held on %d (%.0f%%)"
              % (n, same_pos, 100.0 * same_pos / n, same_letter, 100.0 * same_letter / n))

        # THE ATTRIBUTION QUESTION IS SECOND. THE FIRST QUESTION IS WHETHER ANYTHING HELD.
        #
        # A first version of this verdict compared `same_letter > same_pos` and announced
        # "letter bias is not disqualifying" off 14 against 13 -- a one-item margin, which is
        # the same spurious threshold as declaring a mechanism off 0.202 against 0.194. Both
        # numbers are the story: reversing which letter denotes which option is a change to the
        # LEGEND, not to the proposition, and a format that reads content should be invariant
        # to it. This one changed 77% of its answers.
        #
        # So the order is: is the format stable under an irrelevant transformation at all? Only
        # if it is does asking whether the residual is letter-driven mean anything.
        INVARIANCE_FLOOR = 0.80
        if same_pos / n < INVARIANCE_FLOOR:
            print("")
            print("  *** THE FORMAT IS NOT INVARIANT TO ITS OWN LEGEND. ***")
            print("  Reversing which letter denotes which option changed %d of %d positions."
                  % (n - same_pos, n))
            print("  That reversal alters no proposition and no option -- only the order they")
            print("  are listed in -- so a format reading content should return the same")
            print("  positions. It does not, and the letter form is the ONLY form the labels")
            print("  permit, because 'Strongly Agree' and 'Strongly Disagree' share their")
            print("  first token.")
            print("")
            print("  Whether the residual is letter preference is a second-order question and")
            print("  this data does not settle it: position held on %d and letter on %d, a"
                  % (same_pos, same_letter))
            print("  margin of %d item(s), which decides nothing." % abs(same_pos - same_letter))
        elif same_letter > same_pos:
            print("")
            print("  The answers track the LETTER rather than the label: this format reads a")
            print("  preference among letters, not a position on the proposition.")
        else:
            print("")
            print("  The position survives a legend reversal on %.0f%% of items, so the format"
                  % (100.0 * same_pos / n))
            print("  is reading content rather than the alphabet.")

    if args.agreement:
        sheets = parsed_sheets(args.model)
        print("")
        print("AGREEMENT against the parsed instrument")
        print("  %d valid parsed sheet(s) for this model in the corpus" % len(sheets))
        if not sheets:
            print("  none -- cannot check agreement, and that is not a pass.")
            return 1
        pm = modal(sheets)
        a = agreement(logit, pm)
        if not a:
            print("  no shared items -- cannot check agreement.")
            return 1
        print("  exact match      %d of %d  (%.1f%%)"
              % (a["exact"], a["items"], 100.0 * a["exact_rate"]))
        print("  side-flips       %d of %d" % (a["side_flips"], a["items"]))
        print("")
        print("  Judge it against this study's own floors, not against a hoped-for number:")
        print("  the modal estimator's side-flip p90 is 3 and the run-to-run replicate p90 is")
        print("  5. A side-flip count inside that band means the two instruments are")
        print("  indistinguishable at this study's resolution. Well outside it means they are")
        print("  measuring different things and the logit numbers cannot inherit the parsed")
        print("  instrument's published floors.")

    if args.json:
        print(json.dumps({"model": args.model, "logit": logit}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
