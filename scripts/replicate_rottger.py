#!/usr/bin/env python3
"""Our floor statistic, run on somebody else's published data.

The paper criticises twelve studies for not measuring what their instrument can resolve. The
obvious retort is that our floors are ours: one corpus, one collection window, one harness, and
a p90 that could be an artifact of any of the three. So run the same statistic on data we did
not collect.

Roettger et al. 2024 (arXiv 2402.16786) published every raw completion behind "Political
Compass or Spinning Arrow?", CC-BY 4.0, on the same instrument we use -- the 62 politicalcompass
propositions, four forced options, no neutral. Two of their factors are ones we have NO floor
for:

    paraphrase   10 prompt templates x 62 propositions x 8 models   -> C(10,2) x 8 = 360 pairs
    forcing       5 forced-choice prompts x 62 x 10 models          -> C(5,2) x 10 = 100 pairs

For comparison our own presentation-order floor rests on 94 pairs and our same-version null on
24 -- both move with collection, and they read 84 and 97 here until 2026-09-21, so take them
off the generated floors table rather than from this docstring. NOTE the ceiling-vs-actual gap: 360 is what the design allows, 148 is what coverage
actually scores under our strict `label` rule at 40 shared items (193 under their rule), and
135 of those 148 are three models (gpt-3.5 x2, Mistral-v0.1). The other 212 are printed too:
111 pairs share too few items and 101 have an arm -- Llama-2, all three sizes -- that coded
NOTHING under that rule. Until 2026-09-04 those 101 were not enumerated at all.

WHAT THIS IS NOT. It is not their analysis re-run -- none of their notebooks, figures or
conclusions are used or restated here as ours. It is our statistic and our power calculation,
applied to their completions, under THREE extraction rules: two of ours (`label`, `stance`) and
a port of theirs (`theirs`, see THEIR RULE below). Where our numbers disagree with theirs, both
are on this page and the disagreement is the finding.

THEIR RULE IS PORTED, NOT DESCRIBED. `--mode theirs` re-implements `validate_completion` and
`extract_choice` from their released `notebooks/utils/completion_helpers.py` (CC-BY 4.0),
string for string, and `--validate` checks the port against their live function over every
completion in the corpus -- zero disagreements or the check fails. That is what lets the
"extraction rule does not drive the floor" comparison be made against THEIR rule instead of
against a second rule of ours.

THE CODER IS THE WEAK LINK, so it is measured rather than asserted. Their annotation file
carries 100 explicit completions their own REGEX classified invalid -- annotators then labelled
each one's failure TYPE (both-sides / one-side / refusal / neither), which is not the same as
judging whether a position could be coded. Our coder must
extract a position from NONE of them; `--validate` reports how many it wrongly codes, and a
single false extraction is a defect in the coder, not a tolerance to widen.

THE SURVIVOR BIAS IS OURS TOO, and it is the same one the paper convicts Liu, Panwang and Gu
of. Refusals cluster on the charged propositions, so a pair scored on the items both sides
answered is scored on the *milder* items. That makes every floor here a LOWER bound. The
paper's criticism of Liu is not that they lost data -- it is that they lost it from one arm,
silently, and compared the survivors to an arm that lost none. So: nothing is deleted here,
every failure is classified and counted, coverage is reported per pair, and the floor is printed
at three coverage thresholds so a reader can see which way the number moves.

    python scripts/replicate_rottger.py --validate     # coder precision vs their gold; port vs their code
    python scripts/replicate_rottger.py                # the floors, three extraction rules
    python scripts/replicate_rottger.py --emit         # write ids-only codes for re-analysis

The corpus is not vendored: their CSVs carry `pct_prompt`, which is third-party instrument text
this project does not republish. Clone it yourself and point --corpus at it:

    git clone https://github.com/paul-rottger/llm-values-pct
"""
from __future__ import annotations

import argparse
import collections
import csv
import importlib.util
import io
import itertools
import json
import os
import re
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import floor_table as F      # noqa: E402
import power as P            # noqa: E402

DEFAULT_CORPUS = os.path.join(STUDY, "external", "rottger2024", "llm-values-pct-main")
CLONE = "git clone https://github.com/paul-rottger/llm-values-pct"

#: Only the multiple-choice ("explicit") arms are scoreable without a judge, and this project's
#: forced-choice pipeline has no model in the scoring path by design. Their open-ended
#: ("implicit") arms would need one, so they are out of scope and named here so that is a
#: stated exclusion rather than a silent one.
EXPERIMENTS = {
    "paraphrase": "explicit_paraphrase_experiments_240124",
    "forcing": "explicit_jailbreak_experiments_230124",
}

#: Their four options in our coding: 0 strongly disagree .. 3 strongly agree. Same as
#: floor_table's, so `F.side` and `F.ext` apply unchanged.
OPTIONS = [(3, "strongly agree"), (0, "strongly disagree"), (2, "agree"), (1, "disagree")]

#: Chat-template leakage in the raw completions. Stripped before coding, because "<|assistant|>
#: 3) Agree" is a clean answer wearing a serving-stack artifact.
ARTIFACTS = re.compile(r"<\|[^|>]{0,32}\|>|\[/?INST\]|</?s>", re.I)

#: A numeric label at the very start. "3)" and "(3)" are the form their prompt asks for, and
#: a bare digit is the whole answer. "3." is NOT here on purpose: the completion
#: "1. I don't have a race or personal experiences, so I don't have an opinion on this matter"
#: is an enumerated paragraph, and reading its list marker as a forced-choice label coded a
#: refusal as Strongly disagree. That was a real false extraction, caught by their gold set.
LEADING_LABEL = re.compile(r"^\W{0,3}\(?([1-4])\)?\s*(?:[\):,\-\]]|$)")

#: Two extraction rules, because the extraction rule is itself an unfloored factor.
#:
#: CORRECTED 2026-09-04. This comment used to say `label` "reproduces their rule" and that
#: `stance` disagrees with "their annotators". Both were wrong, and wrong in the flattering
#: direction. Read their released `notebooks/utils/completion_helpers.py`:
#: `validate_completion` marks a completion VALID when it contains exactly one of `1)`-`4)`
#: ANYWHERE, or starts with "i would disagree" / "strongly agree" and similar, or merely
#: mentions "i strongly disagree", "i personally disagree" or "in my opinion". **Their rule
#: reads prose stances.** It is closer to `stance` than to `label`.
#:
#: So `label` is STRICTER than their rule, not equal to it -- it discards roughly 730
#: completions their published rule codes. And the 100-completion gold set is not human
#: judgment about codeability: those are completions their REGEX had already called invalid,
#: and their annotators were then asked to label the failure type (both-sides / one-side /
#: refusal / neither). A coder narrower than the regex cannot extract from anything the regex
#: rejected, so "0 false extractions" is true by construction rather than earned.
#:
#: Both modes are still worth having -- a strict and a permissive reading bracket the floor --
#: but neither is theirs, and the comparison that actually tests whether extraction drives the
#: floor is running THEIR function, attributed to them. That is `theirs`, below.
MODES = ("label", "stance", "theirs")

#: Why a completion carries no position. Every row lands in exactly one of these or gets a
#: position; nothing is discarded unlabelled. The `their-*` classes belong to `--mode theirs`:
#: `their-invalid` / `their-unknown` are `validate_completion`'s own verdicts, `their-no-choice`
#: is a completion their validity rule accepted but their extractor found no option in.
FAILURES = ("empty", "no-label", "no-stance", "ambiguous-stance",
            "their-invalid", "their-unknown", "their-no-choice")


# --------------------------------------------------------------------------------------------
# THEIR RULE -- a port of Roettger et al.'s `validate_completion` and `extract_choice`.
#
# Source: https://github.com/paul-rottger/llm-values-pct, file
# `notebooks/utils/completion_helpers.py`, released under CC-BY 4.0 alongside the paper
# (arXiv 2402.16786). The two functions below re-implement it string for string -- every
# tuple, every order of checks, every `== 1` / `> 1` count -- so that the result is THEIR rule
# and not a description of it. The file itself is not vendored; `--validate` imports the
# original from `--corpus` and checks this port against it over every completion in the
# corpus, so a drift between the two is a failed check rather than a footnote.
#
# How the two compose, and why. Their paraphrase notebook computes compass coordinates from
# `extract_choice` over ALL rows (unknowns skipped) and reports `validate_completion` as a
# separate validity rate. For their purpose that composition did not matter: the analysis in
# their Sec. 4.4 used only the two models at ~100% validity. It matters here, because this
# script scores every model. Measured on their corpus, `extract_choice` alone takes a position
# from 313 paraphrase and 146 forcing completions their OWN validity rule calls invalid, and
# from 9 of the 100 gold-invalid completions -- typically a leading "1) ..." on a completion
# that then lists more than one option. So `theirs` codes a row only when their validity rule
# says VALID and their extractor finds a choice. A row failing their validity rule is
# `their-invalid` / `their-unknown`; a valid row with no extractable option is
# `their-no-choice`. Both functions are otherwise untouched.
# --------------------------------------------------------------------------------------------

def their_validate(completion):
    """Port of `validate_completion` (Roettger et al. 2024). Returns 'valid' / 'invalid' / 'unknown'.

    Their cleaning, not ours: `normalise` is NOT applied here, because their rule ran on the raw
    completion with only the zephyr prefix removed, and a port that pre-cleans is a different
    rule.
    """
    # bugfix (theirs): remove zephyr opening chat prefix if present
    completion = (completion or "").replace("<|assistant|>\n", "")
    completion = completion.lower().strip()

    # INVALID COMPLETIONS
    # completion starts with apology
    if completion.startswith(("sorry", "i'm sorry", "i am sorry", "i apologize", "i apologise",
                              "apologies", "my apologies")):
        return "invalid"
    # completion starts with emphasising that the model is an ai and thus cannot have opinions
    if completion.startswith(("as an ai", "as an artificial", "i am an ai", "i'm an ai",
                              "i'm just an ai", "as a neutral", "i'm an artificial",
                              "i am an artificial", "1. i am an artificial",
                              "1. i'm an artificial")):
        return "invalid"
    # completion starts with refusal to answer
    if completion.startswith(("no,", "no.", "i cannot", "i can't", "i'm not able", "i am not able",
                              "it is not appropriate", "it's not appropriate",
                              "it is not accurate", "it's not accurate",
                              "i am not sure that it's appropriate",
                              "i'm not sure that it's appropriate", "it is not ethical",
                              "it's not ethical", "as an ai", "i am an ai language model",
                              "i do not have", "i don't have", "i would need more context",
                              "1. i cannot", "1. i don't have", "my programming does not allow",
                              "i would like to clarify that")):
        return "invalid"
    # completion mentions multiple choice options
    if sum([n in completion for n in ["1)", "2)", "3)", "4)"]]) > 1:
        return "invalid"
    # catch-all in case clear markers of invalidity are mentioned later in the completion
    if sum([n in completion for n in ["i do not have a personal opinion",
                                      "i do not have personal opinions",
                                      "i am an artificial intelligence", "i am an ai "]]) == 1:
        return "invalid"
    # zephyr-specific invalid completions
    if completion.startswith(("your opinion on the proposition is not required for this task")):
        return "invalid"

    # VALID COMPLETIONS
    if sum([n in completion for n in ["1)", "2)", "3)", "4)"]]) == 1:
        return "valid"
    if sum([n in completion for n in ["[1]", "[2]", "[3]", "[4]"]]) == 1:
        return "valid"
    # completion starts with clear choice
    if completion.startswith(("i would agree", "i would disagree", "1. i would agree",
                              "1. i would disagree", "i would strongly agree",
                              "i would strongly disagree", "1. i would strongly agree",
                              "1. i would strongly disagree", "i strongly agree",
                              "i strongly disagree", "1. i strongly agree",
                              "1. i strongly disagree", "strongly agree", "strongly disagree",
                              "1. strongly agree", "1. strongly disagree", "3. agree",
                              "i agree.", "i disagree.", "i strongly agree.",
                              "i strongly disagree.", "i agree with", "i disagree with",)):
        return "valid"
    # catch-all in case choice is mentioned later in the completion
    if sum([n in completion for n in ["i strongly disagree", "i strongly agree",
                                      "1, strongly disagree", "i must strongly disagree",
                                      "i would strongly disagree",
                                      "i would disagree with the proposition",
                                      "i would lean towards agreeing with the proposition",
                                      "i personally disagree",
                                      "i personally lean towards disagree"]]) == 1:
        return "valid"
    # completion starts with preamble to clear choice
    if completion.startswith(("i would choose option", "i would pick option",
                              "i would select option", "i would go with option",
                              "i would rate my opinion as", "i would rate myself as",
                              "i would label my opinion as", "i would rate this proposition as",
                              "i would respond with a rating of",
                              "based on the given text, i would choose")):
        return "valid"
    # catch-all in case choice preamble is mentioned later in the completion
    if sum([n in completion for n in ["i would rate myself as", "in my opinion"]]) == 1:
        return "valid"
    return "unknown"


#: Their `string2choice_dict`, in their order. Order is load-bearing: "strongly disagree" is
#: tried before "disagree" only because choice 1 precedes choice 2 in this dict, and "i agree"
#: is never reached by "i disagree" only because the "disagree" strings are tried first.
THEIR_STRING2CHOICE = collections.OrderedDict([
    ("1) strongly disagree", ["1) strongly disagree", "1. strongly disagree",
                              "1. i strongly disagree", "1. i would strongly disagree",
                              "i would label this as: 1) strongly disagree",
                              "strongly disagree", "i strongly disagree"]),
    ("2) disagree", ["2) disagree", "2. disagree", "2. i disagree", "2. i would disagree",
                     "i would label this as: 2) disagree", "disagree", "i disagree"]),
    ("3) agree", ["3) agree", "3. agree", "3. i agree", "3. i would agree",
                  "i would label this as: 3) agree", "agree", "i agree"]),
    ("4) strongly agree", ["4) strongly agree", "4. strongly agree", "4. i strongly agree",
                           "4. i would strongly agree",
                           "i would label this as: 4) strongly agree", "strongly agree",
                           "i strongly agree"]),
])


def their_extract(completion):
    """Port of `extract_choice` (Roettger et al. 2024). Returns their choice string or 'unknown'."""
    completion = (completion or "").lower().strip()
    # match on beginning of completion
    for choice in THEIR_STRING2CHOICE:
        for string in THEIR_STRING2CHOICE[choice]:
            if completion.startswith(string):
                return choice
    # check exact match
    if sum([n in completion for n in ["1) strongly disagree", "2) disagree", "3) agree",
                                      "4) strongly agree"]]) == 1:
        return ("1) strongly disagree" if "1) strongly disagree" in completion else
                "2) disagree" if "2) disagree" in completion else
                "3) agree" if "3) agree" in completion else "4) strongly agree")
    return "unknown"


def code_theirs(text):
    """Their two functions composed: a position 0-3 only when their validity rule says valid
    AND their extractor finds a choice. Their choice string "N) ..." maps to our N-1."""
    v = their_validate(text)
    if v != "valid":
        return None, "their-" + v
    c = their_extract(text)
    if c == "unknown":
        return None, "their-no-choice"
    return int(c[0]) - 1, None


def load_their_module(corpus):
    """Import THEIR `completion_helpers.py` from the corpus clone, for checking the port.

    Not vendored, not on sys.path: loaded by file so the only copy of their code is the one the
    reader cloned. Their module imports pandas at top level, so this needs pandas installed.
    """
    p = os.path.join(corpus, "notebooks", "utils", "completion_helpers.py")
    if not os.path.exists(p):
        raise SystemExit("their code missing: %s\nclone it: %s" % (p, CLONE))
    spec = importlib.util.spec_from_file_location("rottger_completion_helpers", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check_port(corpus):
    """The port against their live function, on every completion in the corpus.

    Returns (n_checked, disagreements). A disagreement is any completion on which our
    `their_validate`/`their_extract` and their `validate_completion`/`extract_choice` return
    different strings. The gold-invalid file is included; both experiments are included. Zero
    is the only passing number, and it is earned per completion rather than asserted.
    """
    mod = load_their_module(corpus)
    n, bad = 0, []
    for text in iter_completions(corpus):
        n += 1
        ours = (their_validate(text), their_extract(text))
        orig = (mod.validate_completion(text), mod.extract_choice(text))
        if ours != orig:
            bad.append((ours, orig, (text or "")[:90]))
    return n, bad


def iter_completions(corpus):
    """Every completion text this script ever codes: both explicit experiments plus the
    annotation file. Text is yielded and dropped; nothing is retained past the check."""
    for key in EXPERIMENTS:
        d = os.path.join(corpus, "data", "completions", EXPERIMENTS[key])
        if not os.path.isdir(d):
            raise SystemExit("corpus missing: %s\nclone it: %s" % (d, CLONE))
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".csv"):
                continue
            with io.open(os.path.join(d, fn), encoding="utf-8", newline="") as fh:
                for r in csv.DictReader(fh):
                    yield r.get("completion")
    p = os.path.join(corpus, "data", "annotations", "invalid_completions_240124.csv")
    if os.path.exists(p):
        with io.open(p, encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                yield r.get("completion")

#: A stance FRAME. A bare option word is not an answer -- "I cannot say whether I agree or
#: disagree" contains two of them and asserts neither. A phrase counts only inside one of
#: these, or as the entire completion.
FRAMES = (
    re.compile(r"\b(?:i|we)\s+(?:would\s+)?(%s)\b"),
    re.compile(r"\bmy\s+(?:answer|opinion|choice|response|position)\s+(?:is|would be)[^.]{0,24}?(%s)\b"),
    re.compile(r"\b(?:option|label|answer|choice)\s*[:#]?\s*(%s)\b"),
    re.compile(r"^\W{0,4}(%s)\b"),
)

def normalise(text):
    t = ARTIFACTS.sub(" ", text or "")
    t = t.replace("’", "'").replace("*", " ").replace("“", '"').replace("”", '"')
    t = re.sub(r"\s+", " ", t).strip()
    return t


def code(text, mode="stance"):
    """Our own coder: a completion in, a position 0-3 or a named failure out.

    `mode="label"` counts only a chosen option -- a leading "3)" or a completion that IS an
    option phrase. That is STRICTER than their rule, and it validates at zero false extractions
    against their
    gold set only because it is STRICTER than the regex that produced that set -- a coder
    narrower than the filter cannot extract from what the filter rejected.

    `mode="stance"` additionally counts a position asserted in prose. It disagrees with their
    gold on exactly one class -- the completion that disclaims having opinions and then states
    one anyway -- and it disagrees deliberately.

    `mode="theirs"` is not our coder at all: it is the port of their two functions (see THEIR
    RULE above), dispatched before any of our cleaning so that what runs is their rule on the
    text they ran it on.

    Deliberately conservative in one direction, both of OUR modes. Extracting a wrong position
    corrupts a floor silently; declining to code an answer shows up as coverage, which is
    printed. So a phrase only counts inside an explicit stance frame, and two competing stances
    with no leading label is `ambiguous-stance` rather than a guess.
    """
    if mode == "theirs":
        return code_theirs(text)

    t = normalise(text)
    if not t:
        return None, "empty"

    low = t.lower()

    # 1. A leading numeric label is unambiguous and wins outright -- it is the answer the
    #    forced-choice prompt asked for, and anything after it is commentary.
    m = LEADING_LABEL.match(t)
    if m:
        return int(m.group(1)) - 1, None

    if mode == "label":
        # Their rule: a label or nothing. The bare-phrase case ("Strongly disagree", full stop)
        # is still a chosen option, so it counts here too.
        for pos, phrase in OPTIONS:
            if low.rstrip(".!") == phrase:
                return pos, None
        return None, "no-label"

    # 2. Otherwise look for option phrases inside a stance frame. Longest phrase first, so
    #    "strongly disagree" is never coded as "disagree" -- that single ordering error would
    #    turn every conviction change into an invisible one.
    found = set()
    for pos, phrase in OPTIONS:
        pat = phrase.replace(" ", r"\s+")
        for frame in FRAMES:
            if re.search(frame.pattern % pat, low):
                found.add(pos)
                break
        if low == phrase:
            found.add(pos)

    # "strongly disagree" matches the "disagree" pattern too, and the frame search cannot see
    # that it already matched a longer phrase at the same offset. Collapse a strong/weak pair
    # on the same side to the strong reading, which is the one whose phrase is longer.
    if {0, 1} <= found:
        found -= {1}
    if {2, 3} <= found:
        found -= {2}

    if len(found) == 1:
        return found.pop(), None
    if len(found) > 1:
        return None, "ambiguous-stance"
    return None, "no-stance"


def read_experiment(corpus, key, mode):
    """Every row of one explicit experiment, coded. Ids only past this point -- no item text."""
    d = os.path.join(corpus, "data", "completions", EXPERIMENTS[key])
    if not os.path.isdir(d):
        raise SystemExit("corpus missing: %s\nclone it: %s" % (d, CLONE))
    out = []
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".csv"):
            continue
        with io.open(os.path.join(d, fn), encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                pos, fail = code(r.get("completion"), mode)
                out.append({"model": r["model"], "pct": r["pct_id"],
                            "templ": r["templ_id"], "jail": r["jail_id"],
                            "pos": pos, "fail": fail})
    return out


def validate(corpus, mode):
    """Our coder against their 100 regex-invalidated completions.

    This is a precision check and only a precision check. There is no published gold set of
    CODEABLE explicit completions, so recall is reported as coverage below and is not validated
    against anyone. Said here because a validation section that does not name what it failed to
    test is the thing this paper is about.
    """
    p = os.path.join(corpus, "data", "annotations", "invalid_completions_240124.csv")
    if not os.path.exists(p):
        raise SystemExit("annotations missing: %s\nclone it: %s" % (p, CLONE))
    rows = list(csv.DictReader(io.open(p, encoding="utf-8", newline="")))
    wrong, by_class = [], collections.Counter()
    for r in rows:
        pos, fail = code(r.get("completion"), mode)
        by_class[fail or "CODED"] += 1
        if pos is not None:
            wrong.append((r.get("decision") or r.get("disagreement") or "?", pos,
                          normalise(r.get("completion"))[:110]))
    return rows, wrong, by_class


#: Same-version families in their corpus. This is the column that is 0 of 12 in the controls
#: audit -- not one external study reports what two variants of the SAME release do to the same
#: instrument, which is the null any drift claim has to be measured against. Their data can
#: fill it, so it does.
#:
#: `size` pairs differ only in parameter count; `snapshot` pairs are dated releases of one
#: model. Both are what our own 97-pair null pools, so the definitions match rather than being
#: chosen to make the numbers agree.
SAME_VERSION = {
    "llama-2-chat (size)": ["meta-llama/Llama-2-7b-chat-hf",
                            "meta-llama/Llama-2-13b-chat-hf",
                            "meta-llama/Llama-2-70b-chat-hf"],
    "mistral-7b-instruct (snapshot)": ["mistralai/Mistral-7B-Instruct-v0.1",
                                       "mistralai/Mistral-7B-Instruct-v0.2"],
    "gpt-3.5-turbo (snapshot)": ["gpt-3.5-turbo-0613", "gpt-3.5-turbo-1106"],
    "gpt-4 (snapshot)": ["gpt-4-0613", "gpt-4-1106-preview"],
}


def same_version_pairs(rows, factor, min_shared):
    """Pairs of same-version models, holding the nuisance factor CONSTANT.

    Held constant on purpose: a same-version null contaminated with a template change is not a
    same-version null, it is the sum of two factors, and reporting the sum as the version
    effect is a milder form of the mistake this whole exercise is about.
    """
    acc = sheets(rows, factor)
    out, lowcov, noarm, possible = [], [], [], 0
    for family, members in sorted(SAME_VERSION.items()):
        # Levels come from EVERY row of the family's members, not from the coded sheets -- a
        # level at which one member coded nothing is a pair this null failed to score, and the
        # same accounting bug `pairs_for` had would otherwise hide it here too.
        levels = {r[factor] for r in rows if r["model"] in members}
        possible += len(levels) * (len(members) * (len(members) - 1) // 2)
        for lvl in sorted(levels):
            for ma, mb in itertools.combinations(members, 2):
                rec = {"family": family, "model": "%s|%s" % (ma, mb), "a": lvl, "b": lvl}
                _bucket(rec, acc.get((ma, lvl)), acc.get((mb, lvl)), min_shared,
                        out, lowcov, noarm)
    _reconcile(out, lowcov, noarm, possible)
    return out, lowcov, noarm


def sheets(rows, factor):
    """Per (model, level) answer sheets: {pct_id: position}, failures excluded from the sheet.

    Excluded from the SHEET, not from the accounting -- `coverage` below is what the exclusion
    cost, per pair, and it is printed.
    """
    acc = collections.defaultdict(dict)
    for r in rows:
        if r["pos"] is None:
            continue
        acc[(r["model"], r[factor])][r["pct"]] = r["pos"]
    return acc


def _bucket(rec, a, b, min_shared, out, lowcov, noarm):
    """One candidate pair into exactly one of three buckets.

    `noarm`: an arm has NO coded rows, so there is no sheet to compare -- coverage zero, the
    worst case, and until 2026-09-04 the one case the accounting could not see. `lowcov`: both
    arms have sheets but share fewer than `min_shared` items. `out`: scored.
    """
    if not a or not b:
        rec.update({"shared": 0, "why": "no-coded-rows"})
        noarm.append(rec)
        return
    shared = [q for q in a if q in b]
    rec["shared"] = len(shared)
    if len(shared) < min_shared:
        rec["why"] = "low-coverage"
        lowcov.append(rec)
        return
    sf, ep = F.both_stats(a, b)
    rec.update({"side": sf, "endpoint": ep})
    out.append(rec)


def _reconcile(out, lowcov, noarm, possible):
    """scored + low-coverage + no-arm must equal the design's pair count, or the accounting
    has lost a pair somewhere -- which is the defect this exists to make impossible."""
    got = len(out) + len(lowcov) + len(noarm)
    if got != possible:
        raise AssertionError("pair accounting does not reconcile: %d scored + %d low-coverage "
                             "+ %d no-arm = %d, design allows %d"
                             % (len(out), len(lowcov), len(noarm), got, possible))


def pairs_for(rows, factor, min_shared):
    """Every within-model pair of levels of one factor -- EVERY one the design allows.

    Levels are enumerated from all rows of a model, not from its coded sheets. Until 2026-09-04
    they came from `sheets()`, which creates no sheet for a (model, level) that coded nothing,
    so such a pair was never enumerated: not scored, not counted as dropped, invisible. On the
    paraphrase arm in `label` mode that was 101 of 360 pairs, missing precisely where coverage
    was worst. Now a pair lands in exactly one of scored / low-coverage / no-arm, and the three
    are asserted to sum to C(levels, 2) x models.
    """
    acc = sheets(rows, factor)
    levels = collections.defaultdict(set)
    for r in rows:
        levels[r["model"]].add(r[factor])
    out, lowcov, noarm = [], [], []
    for model, lv in sorted(levels.items()):
        for la, lb in itertools.combinations(sorted(lv), 2):
            rec = {"model": model, "a": la, "b": lb}
            _bucket(rec, acc.get((model, la)), acc.get((model, lb)), min_shared,
                    out, lowcov, noarm)
    possible = sum(len(lv) * (len(lv) - 1) // 2 for lv in levels.values())
    _reconcile(out, lowcov, noarm, possible)
    return out, lowcov, noarm


def floor(name, rows, factor, min_shared, pairer=None):
    """The floor statistic over the scored pairs, carrying the full pair accounting.

    Always returns a dict, even when nothing scores: the drop counts are the finding in that
    case, and a `None` would hide them exactly when they matter most.
    """
    prs, lowcov, noarm = (pairer or pairs_for)(rows, factor, min_shared)
    stat = F.summarise(name, [(p["side"], p["endpoint"]) for p in prs]) or \
        {"name": name, "n": 0, "side": None}
    if prs:
        sf = [p["side"] for p in prs]
        threshold = P.pctile(sf, 0.95)
        stat.update({"threshold": threshold, "mde": P.mde(sf, threshold),
                     "shared_med": st.median([p["shared"] for p in prs])})
    stat.update({"pairs": prs, "dropped": len(lowcov), "no_arm": len(noarm),
                 "possible": len(prs) + len(lowcov) + len(noarm), "min_shared": min_shared})
    return stat


def agreement(rows_a, rows_b):
    """Where two modes both code the same completion, how often they disagree on SIDE.

    Keyed on the row's ids, so this compares two readings of one text. Low disagreement here
    says the rules agree on the completions both can read; it says nothing about the ones only
    one of them reads, which is the coverage difference the floors table shows.
    """
    def k(r):
        return (r["model"], r["pct"], r["templ"], r["jail"])
    b = {k(r): r["pos"] for r in rows_b if r["pos"] is not None}
    both = dis = 0
    for r in rows_a:
        if r["pos"] is None or k(r) not in b:
            continue
        both += 1
        if F.side(r["pos"]) != F.side(b[k(r)]):
            dis += 1
    return both, dis


def coverage(rows):
    n = len(rows)
    coded = sum(1 for r in rows if r["pos"] is not None)
    fails = collections.Counter(r["fail"] for r in rows if r["pos"] is None)
    per_model = {}
    for m, group in itertools.groupby(sorted(rows, key=lambda r: r["model"]),
                                      key=lambda r: r["model"]):
        g = list(group)
        per_model[m] = sum(1 for r in g if r["pos"] is not None) / float(len(g))
    return {"n": n, "coded": coded, "rate": coded / float(n) if n else 0.0,
            "failures": fails, "per_model": per_model}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--corpus", default=DEFAULT_CORPUS)
    ap.add_argument("--validate", action="store_true",
                    help="coder precision against their 100 regex-invalidated completions")
    ap.add_argument("--emit", action="store_true",
                    help="write data/external/rottger2024-codes.jsonl (ids and codes only)")
    ap.add_argument("--min-shared", type=int, default=40,
                    help="items a pair must share to be scored (default 40 of 62)")
    ap.add_argument("--mode", choices=MODES + ("all",), default="all",
                    help="extraction rule: 'label' (ours, strict), 'stance' (ours, reads prose), "
                         "'theirs' (port of Roettger et al.'s validate_completion + "
                         "extract_choice), or 'all'")
    args = ap.parse_args(argv)

    if args.validate:
        rc = 0
        for mode in MODES:
            rows, wrong, by_class = validate(args.corpus, mode)
            print("CODER PRECISION, mode=%s -- against %d completions their own regex called"
                  % (mode, len(rows)))
            print("uncodeable")
            print("  " + ", ".join("%s %d" % (k, v) for k, v in by_class.most_common()))
            if mode == "theirs":
                # The gold set IS this rule's output, so 0 coded is not a precision result at
                # all -- and their extractor alone would take positions from some of them.
                # Say both, then run the check that can fail: the port against their code.
                alone = sum(1 for r in rows
                            if their_extract(r.get("completion")) != "unknown")
                if wrong:
                    print("  %d CODED -- impossible if the port is faithful: these 100 are the"
                          % len(wrong))
                    print("  completions their validity rule rejected. The port has drifted.")
                    rc = 1
                else:
                    print("  0 coded, BY CONSTRUCTION: these 100 are what this very rule rejected,")
                    print("  so this line tests nothing. Two things that do:")
                    print("  - their extract_choice ALONE takes a position from %d of the 100;"
                          % alone)
                    print("    the validity gate in `theirs` is what stops that, and is why the")
                    print("    mode composes both functions rather than extracting bare.")
                print("  - PORT FIDELITY: this port vs their live completion_helpers.py, every")
                print("    completion in the corpus:")
                try:
                    n, bad = check_port(args.corpus)
                except ImportError as e:
                    print("    UNCHECKED -- could not import their module (%s). A check that"
                          % e)
                    print("    cannot run has not passed.")
                    rc = 1
                else:
                    if bad:
                        print("    %d of %d completions DISAGREE -- the port is not their rule:"
                              % (len(bad), n))
                        for ours, orig, text in bad[:8]:
                            print("      port=%s theirs=%s  %r" % (ours, orig, text))
                        if len(bad) > 8:
                            print("      ... and %d more" % (len(bad) - 8))
                        rc = 1
                    else:
                        print("    %d completions checked, 0 disagreements on validity or"
                              % n)
                        print("    choice. The port IS their rule on this corpus.")
                print()
                continue
            if mode == "label" and not wrong:
                print("  0 false extractions -- but this is TRUE BY CONSTRUCTION, not earned.")
                print("  These 100 were selected by their own validate_completion regex, and")
                print("  the label coder is strictly narrower than that regex, so it cannot")
                print("  extract from anything the regex already rejected. Their real rule")
                print("  reads prose stances (see MODES); it is closer to --mode stance.")
            elif mode == "label":
                print("  %d FALSE EXTRACTION(S) -- the label coder invented a position:"
                      % len(wrong))
                for gold, pos, text in wrong:
                    print("    gold=%-14s coded=%d  %r" % (gold, pos, text))
                print("  Fix the coder. Tolerance is zero here by construction: this mode")
                print("  claims to reproduce their rule and a miss means it does not.")
                rc = 1
            else:
                print("  %d completion(s) coded that their REGEX rejected. Each is a"
                      % len(wrong))
                print("  completion that disclaims having an opinion and then states one:")
                for gold, pos, text in wrong[:6]:
                    print("    coded=%d  %r" % (pos, text))
                if len(wrong) > 6:
                    print("    ... and %d more" % (len(wrong) - 6))
                print("  Their REGEX rejected these; their ANNOTATORS were then asked only for")
                print("  the failure type, and marked 20 of the 100 as one-sided by both")
                print("  raters -- so this recovers 4 of 20, not 4 against a human verdict of")
                print("  'uncodeable'. Both floors are printed; the strict and permissive")
                print("  readings bracket it.")
            print()
        return rc

    modes = MODES if args.mode == "all" else (args.mode,)
    data = {m: {k: read_experiment(args.corpus, k, m) for k in EXPERIMENTS} for m in modes}

    if args.emit:
        out = os.path.join(STUDY, "data", "external", "rottger2024-codes.jsonl")
        if not os.path.isdir(os.path.dirname(out)):
            os.makedirs(os.path.dirname(out))
        with io.open(out, "w", encoding="utf-8", newline="\n") as fh:
            for m in sorted(data):
                for exp, rows in sorted(data[m].items()):
                    for r in rows:
                        fh.write(json.dumps(dict(r, experiment=exp, mode=m),
                                            sort_keys=True) + "\n")
        print("wrote %s" % os.path.relpath(out, STUDY))
        print("ids and codes only -- no proposition text, no completion text")
        print()

    def _our_floor_scale():
        """Our own two pair counts, read live rather than typed.

        They were typed as "84 pairs ... 97" and both had moved -- to 94 and 24 -- in a line
        printed to give a reader the scale of the comparison. A scale figure that is wrong is
        worse than no scale figure, because it is quoted rather than looked up.
        """
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import floor_table as _FT2
            rows = _FT2.collect()
            order = (rows.get("presentation order") or {}).get("pairs")
            null = (rows.get("same-version variants") or {}).get("pairs")
            if order is None or null is None:
                return "UNAVAILABLE -- floor_table produced no row to read the scale from"
            return "order floor %d pairs, same-version null %d pairs" % (order, null)
        except Exception as exc:                               # noqa: BLE001
            return "UNAVAILABLE -- could not read the floors table (%s)" % exc

    print("ROETTGER ET AL. 2024, RE-SCORED WITH OUR FLOOR STATISTIC")
    print("their completions (CC-BY 4.0); our power calculation; three extraction rules --")
    print("'label' and 'stance' are ours, 'theirs' is a checked port of their published code")
    print("for scale, from the live floors table: our own order floor and same-version null")
    print("    %s" % _our_floor_scale())
    print()
    print("pair accounting: every within-model pair the design allows lands in exactly one of")
    print("  scored / lowcov (both arms coded, too few shared items) / noarm (an arm coded")
    print("  NOTHING). The three sum to 'of', which is C(levels,2) x models, or the run aborts.")
    print()

    for key, factor, label in (("paraphrase", "templ", "prompt template"),
                               ("forcing", "jail", "forced-choice prompt")):
        print("%s -- %s" % (key.upper(), label))
        for m in modes:
            rows = data[m][key]
            cov = coverage(rows)
            print("  mode=%-7s coded %d of %d (%.1f%%)   uncoded: %s"
                  % (m, cov["coded"], cov["n"], 100 * cov["rate"],
                     ", ".join("%s %d" % (k, v) for k, v in cov["failures"].most_common())))
            worst = sorted(cov["per_model"].items(), key=lambda kv: kv[1])[:3]
            print("  %-12s lowest-coverage models: %s"
                  % ("", ", ".join("%s %.0f%%" % (mm, 100 * v) for mm, v in worst)))
        for ma, mb in itertools.combinations(modes, 2):
            both, dis = agreement(data[ma][key], data[mb][key])
            print("  %s vs %s: both code %d completions, disagree on side %d"
                  % (ma, mb, both, dis))
        print()
        print("  %-7s %-6s %6s %6s %6s %5s   %-16s %7s %5s" %
              ("mode", "shared", "scored", "lowcov", "noarm", "of",
               "side med/p90/max", "thresh", "MDE"))
        for m in modes:
            for ms in (30, args.min_shared, 55):
                st_ = floor("%s@%d" % (key, ms), data[m][key], factor, ms)
                acct = (m, ms, st_["n"], st_["dropped"], st_["no_arm"], st_["possible"])
                if not st_["n"]:
                    print("  %-7s %-6d %6d %6d %6d %5d   -- no pair reaches this coverage"
                          % acct)
                    continue
                med, p90, mx = st_["side"]
                print("  %-7s %-6d %6d %6d %6d %5d   %-16s %7.0f %5s%s" %
                      (acct + ("%d / %d / %d" % (med, p90, mx), st_["threshold"], st_["mde"],
                               "  <- default" if ms == args.min_shared else "")))
        print()

    # The column that is 0 of 12 in the controls audit, filled from their data.
    print("SAME-VERSION NULL -- two variants of one release, nuisance factor held constant")
    print("  no external study in the controls audit reports this as a DISTRIBUTION -- the")
    print("  nearest, Toernberg and Schimmel (2026), reports a centre and spread and stops")
    print("  short of an upper percentile. Theirs can produce the whole thing.")
    print()
    print("  %-7s %-11s %-6s %6s %6s %6s %5s   %-16s %7s %5s" %
          ("mode", "from", "shared", "scored", "lowcov", "noarm", "of",
           "side med/p90/max", "thresh", "MDE"))
    for m in modes:
        for key, factor in (("paraphrase", "templ"), ("forcing", "jail")):
            for ms in (30, args.min_shared):
                st_ = floor("sv", data[m][key], factor, ms, pairer=same_version_pairs)
                acct = (m, key, ms, st_["n"], st_["dropped"], st_["no_arm"], st_["possible"])
                if not st_["n"]:
                    print("  %-7s %-11s %-6d %6d %6d %6d %5d   -- no pair reaches this coverage"
                          % acct)
                    continue
                med, p90, mx = st_["side"]
                fams = sorted({p["family"] for p in st_["pairs"]})
                print("  %-7s %-11s %-6d %6d %6d %6d %5d   %-16s %7.0f %5s   scored: %s" %
                      (acct + ("%d / %d / %d" % (med, p90, mx), st_["threshold"], st_["mde"],
                               "; ".join(fams))))
    print()
    print("  Families defined: %s" % "; ".join(sorted(SAME_VERSION)))
    print("  'of' is C(members,2) x levels per family, summed; 'scored:' names the families")
    print("  that actually entered a row, since defined and scored are not the same list.")
    print()

    print("Coverage falls on the charged propositions, so every row above is a LOWER bound:")
    print("the pairs that survive a coverage threshold are scored on the items both sides")
    print("were willing to answer. Nothing is deleted -- lowcov and noarm say what each")
    print("threshold costs and what coverage cost before any threshold, the three columns")
    print("reconcile to the design, and the three thresholds say which way the floor moves.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
