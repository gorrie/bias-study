#!/usr/bin/env python3
"""Gate a stock/ablated pair before it is used as an experimental arm.

WHY THIS EXISTS
---------------
Every abliteration result this project has published carries the same caveat, written as a
hypothetical: "the ablated build is a third-party artifact and may differ from the base in
ways beyond the refusal direction. This is the largest threat to the interpretation and
cannot be excluded without performing the ablation locally."

Measured 2026-08-30 across six locally-held pairs, it is not hypothetical. Three of six were
NOT valid comparison arms, and none of the three differences has anything to do with the
refusal direction:

  gemma2-9b     stock Q4_0    vs ablated Q8_0    + stop tokens dropped + baked temperature
  llama31-8b    stock Q4_K_M  vs ablated Q8_0    + stop tokens dropped + baked temperature
  qwen38-27b    quant matched                    + stop tokens dropped

The consequences were visible in the output, not merely theoretical:

  - the ablated gemma2 emitted tokenizer garbage -- "[UNK_BYTE_0xe29681" is UTF-8 for U+2581,
    the SentencePiece word-boundary marker, being decoded as literal text. The answers were
    inside it, wrapped in vocab damage.
  - the ablated llama3.1, with its stop tokens dropped, INVENTED ITS OWN QUESTIONS ("Should
    the government provide funding for private schools?") and answered those instead of the
    62 it was given.

Either of those, scored naively, becomes "abliteration changed the model's political
answers." It changed the tokenizer and the stop configuration.

A note on the tempting fix: the gemma2 output could be made to parse by stripping the
UNK_BYTE markers. That would be loosening the detector so a broken artifact passes, which is
the one repair this project does not make. The artifact is broken. Report it.

WHAT IT CHECKS
--------------
Quantisation level, stop-token configuration, and baked-in sampling parameters. These are the
properties that must be identical for a between-arm difference to be attributable to the
intervention. It does NOT check weights, and it cannot: a pair passing this gate is
*eligible*, not *verified*.

Exit 0 if every pair matches, 1 otherwise -- so it can gate a sweep.

Usage:
    python check_arm_match.py stock_model ablated_model [more pairs...]
    python check_arm_match.py --known           # the six pairs held locally
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

OLLAMA = "http://localhost:11434"

KNOWN_PAIRS = [
    ("gemma2:latest", "wash-gemma2-ablit:latest", "gemma2-9b"),
    ("llama3.1:8b", "wash-llama31-8b-ablit:latest", "llama31-8b"),
    ("qwen2.5:14b", "huihui_ai/qwen2.5-abliterate:14b", "qwen25-14b"),
    ("phi4:latest", "huihui_ai/phi4-abliterated:latest", "phi4-14b"),
    ("hf.co/lmstudio-community/gemma-4-12B-it-GGUF:Q4_K_M",
     "hf.co/OBLITERATUS/Gemma-4-12B-OBLITERATED:Q4_K_M", "gemma4-12b"),
    ("hf.co/lmstudio-community/Qwen3.8-27B-GGUF:Q4_K_M",
     "hf.co/OBLITERATUS/Qwen3.8-27B-OBLITERATED:Q4_K_M", "qwen38-27b"),
]

SAMPLING_KEYS = ("temperature", "top_p", "top_k", "repeat_penalty", "seed", "mirostat")

#: The pairs this gate has RULED ineligible, by pair label, with the reason. Measured
#: 2026-08-30 and written up in the docstring above; made a named set on 2026-09-04 because
#: prose in a docstring gates nothing.
#:
#: `floor_table.floor_ablation()` reads this. Before it did, all three were excluded from the
#: ablation floor BY ACCIDENT rather than by this ruling: the two wash- builds emit prose with
#: no parsable answers, and the OBLITERATED Qwen3.8-27B answered Strongly Agree to all 62
#: propositions in all four conditions, which the loader drops as a degenerate sheet. Three
#: exclusions, three unrelated mechanisms, none of them this ruling. Had that build's output
#: merely varied a little, a pair this gate calls invalid would have entered a published floor
#: and nothing would have said so.
#:
#: The collapse is worth recording rather than only excluding. The same OBLITERATUS edit on
#: Gemma-4-12B does NOT collapse -- that pair is config-matched, eligible, and contributes 4
#: of the floor's 12 pairs -- so this is specific to the Qwen3.8-27B build, and its stop-token
#: defect is a sufficient explanation without invoking the ablation at all. Which is the point
#: of the gate: scored naively, an all-Strongly-Agree sheet against a normal one reads as
#: "abliteration moved the position by 40 items of 62."
INELIGIBLE_PAIRS = {
    "gemma2-9b": "stock Q4_0 vs ablated Q8_0, stop tokens dropped, baked temperature; "
                 "ablated build emits SentencePiece word-boundary markers as literal text",
    "llama31-8b": "stock Q4_K_M vs ablated Q8_0, stop tokens dropped, baked temperature; "
                  "ablated build invents its own questions and answers those",
    "qwen38-27b": "quantisation matched but stop tokens dropped; ablated build answers "
                  "Strongly Agree to all 62 propositions in every condition",
}


def describe(model):
    req = urllib.request.Request(
        OLLAMA + "/api/show",
        data=json.dumps({"model": model}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as fh:
        data = json.load(fh)
    params = (data.get("parameters") or "")
    stops = tuple(sorted(
        line.split(None, 1)[1].strip()
        for line in params.splitlines()
        if line.strip().startswith("stop")
    ))
    sampling = tuple(sorted(
        line.strip() for line in params.splitlines()
        if line.strip().split(None, 1)[:1] and line.strip().split()[0] in SAMPLING_KEYS
    ))
    details = data.get("details", {})
    return {
        "quant": details.get("quantization_level"),
        "family": details.get("family"),
        "stops": stops,
        "sampling": sampling,
    }


def compare(stock, ablated, label):
    try:
        a, b = describe(stock), describe(ablated)
    except (urllib.error.URLError, OSError) as exc:
        print("  %-14s ERROR  %s" % (label, str(exc)[:60]))
        return False
    problems = []
    if a["quant"] != b["quant"]:
        problems.append("quantisation %s vs %s" % (a["quant"], b["quant"]))
    if a["stops"] != b["stops"]:
        problems.append("stop tokens differ (%d vs %d)" % (len(a["stops"]), len(b["stops"])))
    if a["sampling"] != b["sampling"]:
        problems.append("baked sampling params differ")
    ok = not problems
    print("  %-14s %-9s %s" % (label, "MATCHED" if ok else "INVALID",
                               "" if ok else "; ".join(problems)))
    return ok


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("models", nargs="*", help="stock ablated [stock ablated ...]")
    ap.add_argument("--known", action="store_true", help="check the six locally-held pairs")
    args = ap.parse_args(argv)

    if args.known:
        pairs = KNOWN_PAIRS
    elif len(args.models) >= 2 and len(args.models) % 2 == 0:
        pairs = [(args.models[i], args.models[i + 1], args.models[i].split("/")[-1][:14])
                 for i in range(0, len(args.models), 2)]
    else:
        ap.error("give pairs of models, or --known")

    print("ARM-MATCH GATE -- a pair must be identical in everything except the intervention")
    print()
    results = [compare(s, a, lab) for s, a, lab in pairs]
    print()
    print("  %d of %d pairs usable as arms" % (sum(results), len(results)))
    if not all(results):
        print()
        print("  An INVALID pair is not a weaker arm, it is a different experiment. A")
        print("  between-arm difference on one of these is attributable to quantisation or")
        print("  stop-token configuration before it is attributable to the ablation.")
    print()
    print("  Passing this gate makes a pair ELIGIBLE, not verified. It compares metadata,")
    print("  not weights. The only way to remove the third-party-artifact caveat entirely")
    print("  is to build both arms yourself from one base.")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
