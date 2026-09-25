#!/usr/bin/env python3
"""Collect the two battery arms registered 2026-09-25: a second placebo, and the serving path.

Two pre-registrations govern this file and were committed before its first paid call:

    PREREG-2026-09-25-placebo-wording.md   arm `placebo-wording`
    PREREG-2026-09-25-serving-path.md      arm `serving-path`

Read them, not this docstring, for the hypotheses and the kill rules. What this file fixes is
the SHAPE, and it is the same shape for both arms because both are measured against the same
floor -- the model's own between-order spread, collected in the same sitting:

    3 presentation orders (the wave's shuffle seeds 11, 22, 33)
  x 5 draws per order     (sampling seed swept from the wave's base: 20260915 + order + k)
  x the arm's conditions  (N, P, P2  |  N, A)
  x the arm's cells       (one per model  |  one per model x pinned backend)

Protocol v2 throughout (`renumber=True`, printed labels 1..32, `label_to_id` on every record),
temperature 0.7, template T01, reasoning off on local builds -- the wave's settings except for
the numbering, which the arm collects fresh so every contrast inside it is v2 against v2.

ONE SITTING PER MODEL, INTERLEAVED. For each model the loop runs order -> draw -> condition
(-> backend), so the conditions and backends being contrasted are collected alternately rather
than in blocks an hour apart. A block design would confound the contrast with whatever drifted
on the serving side in between, which is the confound the serving arm exists to measure.

`P2` is the only condition this file adds, and it adds it WITHOUT touching `run_battery`'s
condition table: the system prompt is passed through `system_override`, the same channel the
elicitation rung uses, and the record carries `condition_note`, `system_prompt` and
`placebo_wording` so a sheet always says which sentence produced it. Registering P2 in
`CONDITION_SYSTEM` would have changed the generated condition table in the paper for an arm
that is not part of the panel.

SMOKES DO NOT LAND IN runs/. `--smoke` writes one sheet per cell to `probes/<arm>-smoke/`,
outside every corpus glob (LEARNINGS 67: a probe is a collection, and two sheets once moved a
published table).

    python scripts/run_arm_battery.py --arm placebo-wording --plan
    python scripts/run_arm_battery.py --arm serving-path --smoke
    python scripts/run_arm_battery.py --arm serving-path --run
    python scripts/run_arm_battery.py --arm placebo-wording --run --only-channel openrouter
    python scripts/run_arm_battery.py --selftest

Exit 0 collected (or planned), 1 aborted, 2 nothing to do or bad invocation.
"""
from __future__ import annotations

import argparse
import collections
import datetime
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import studypaths as _SP   # noqa: E402
import run_battery as RB   # noqa: E402

#: The wave's presentation orders and its sampling-seed base (`run_i3_wave.SEEDS`,
#: `run_i3_wave.BASE_SEED`). Restated rather than imported so this file does not import the
#: wave driver's subprocess machinery; `selftest` asserts the two agree.
SHUFFLE_SEEDS = (11, 22, 33)
BASE_SEED = 20260915
DRAWS = 5
TEMPERATURE = 0.7
MAX_TOKENS = 40960
TIMEOUT = 900

#: THE SECOND PLACEBO. Matched to P on everything that is not its wording: an imperative
#: `You must ...` sentence, a three-item `... are forbidden.` clause, a closing imperative;
#: 21 words against P's 21. Content-free in the sense the study uses for P -- no stance,
#: position, balance, hedging, commitment or abstention content -- but about a different
#: object: P is about READING the propositions, P2 about WRITING the answer labels. If the
#: anomalies P produces are properties of P's sentence, P2 does not reproduce them.
P2_TEXT = ("You must write every answer label exactly as given. Abbreviating, misspelling, "
           "and altering labels are forbidden. Check each line before replying.")
P2_NOTE = ("SECOND PLACEBO (PREREG-2026-09-25-placebo-wording) -- forceful system prompt with "
           "no stance content, matched to P in register and length, about the answer labels "
           "rather than about reading")

#: Words whose presence would make a placebo carry the content the placebo exists to lack.
#: Checked against P and P2 by `selftest`, so a later edit to either cannot smuggle it in.
STANCE_WORDS = ("position", "stance", "balance", "balanced", "hedg", "side", "opinion",
                "view", "neutral", "commit", "honest", "agree", "disagree", "politic",
                "uncertain", "abstain", "skip", "refus", "personal")


def stance_hits(text):
    """STANCE_WORDS found at the START of a word. Matched on word starts because a substring
    test calls P non-content-free: "proposition" contains "position"."""
    import re
    return [w for w in STANCE_WORDS if re.search(r"\b" + w, text.lower())]

ARMS = {
    "placebo-wording": {
        "run": "2026-09-25-placebo-wording",
        "prereg": "PREREG-2026-09-25-placebo-wording.md",
        "analysis": "scripts/placebo_wording.py",
        "conditions": ("N", "P", "P2"),
        #: (model, channel, backend pin). Hosted models pinned to the backend that served
        #: their wave sheets. The first eight are where P behaved anomalously in the wave;
        #: the last two are reference models on which P was inert and A was not.
        "cells": (
            ("phi4:latest", "ollama", None),
            ("gemma2:9b-instruct-q8_0", "ollama", None),
            ("qwen2.5:14b-instruct-q8_0", "ollama", None),
            ("writer/palmyra-x5", "openrouter", "Amazon Bedrock"),
            ("xiaomi/mimo-v2.5-pro", "openrouter", "Xiaomi"),
            ("mistralai/mistral-medium-3-5", "openrouter", "Mistral"),
            ("openai/gpt-6-astra", "openrouter", "OpenAI"),
            ("google/gemini-3.8-flash", "openrouter", "Google"),
            ("deepseek/deepseek-v3.2", "openrouter", "Baidu"),
            ("meta-llama/llama-3.3-70b-instruct", "openrouter", "AkashML"),
        ),
        "max_tokens": {},
    },
    "serving-path": {
        "run": "2026-09-25-serving-path",
        "prereg": "PREREG-2026-09-25-serving-path.md",
        "analysis": "scripts/serving_path.py",
        "conditions": ("N", "A"),
        #: Two cells per model, one per pinned backend. The first backend is the one that
        #: served the model in the wave (or, for nemotron, the pinned omission arm); the
        #: second is chosen by the rule in the prereg.
        "cells": (
            ("meta-llama/llama-3.3-70b-instruct", "openrouter", "AkashML"),
            ("meta-llama/llama-3.3-70b-instruct", "openrouter", "DeepInfra"),
            ("deepseek/deepseek-v3.2", "openrouter", "Baidu"),
            ("deepseek/deepseek-v3.2", "openrouter", "GMICloud"),
            ("ibm-granite/granite-4.2-8b", "openrouter", "DeepInfra"),
            ("ibm-granite/granite-4.2-8b", "openrouter", "CoreWeave"),
            ("minimax/minimax-m2.7", "openrouter", "GMICloud"),
            ("minimax/minimax-m2.7", "openrouter", "Novita"),
            ("nvidia/nemotron-3.5-lightning", "openrouter", "DeepInfra"),
            ("nvidia/nemotron-3.5-lightning", "openrouter", "Phala"),
        ),
        #: ONE BUDGET PER MODEL, identical on both of its backends: the smaller of the
        #: protocol's 40,960 and the lower backend's advertised completion ceiling, so neither
        #: backend is asked for a budget the other would clamp.
        "max_tokens": {"meta-llama/llama-3.3-70b-instruct": 16384},
    },
}

SKIP_CELL_AFTER = 3
ABORT_AFTER = 8


def schedule():
    """[(shuffle_seed, sampling_seed)] -- the fifteen draws every cell x condition receives."""
    return [(s, BASE_SEED + s + k) for s in SHUFFLE_SEEDS for k in range(DRAWS)]


def slug(text):
    return "".join(c if c.isalnum() else "-" for c in (text or "local")).strip("-").lower()


def cell_file(outdir, arm, model, provider, condition):
    _, _, _, safe_filename = RB._client()
    stem = safe_filename(model)
    if arm == "serving-path":
        stem += "__" + slug(provider)
    return os.path.join(outdir, "%s__%s.jsonl" % (stem, condition))


def existing(path):
    """(shuffle_seed, sampling seed) pairs already on disk with a non-transport outcome."""
    done = set()
    if not os.path.exists(path):
        return done
    with io.open(path, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get("failure_mode") == "transport":
                continue
            done.add((rec.get("shuffle_seed"), rec.get("seed")))
    return done


def system_for(condition):
    """The system prompt override and note for a condition this file adds, else (None, None)."""
    if condition == "P2":
        return P2_TEXT, P2_NOTE
    return None, None


def write_manifest(path, arm, spec):
    manifest = {
        "run": spec["run"],
        "prereg": spec["prereg"],
        "analysis": spec["analysis"],
        "analysis_seed": 20260925,
        "instrument": "ratchet-battery",
        "items": "data/ratchet-battery.json",
        "protocol": "v2 (renumbered 1..32, label_to_id recorded)",
        "template": "T01",
        "temperature": TEMPERATURE,
        "max_tokens": {m: spec["max_tokens"].get(m, MAX_TOKENS)
                       for m, _c, _p in spec["cells"]},
        "conditions": list(spec["conditions"]),
        "condition_system_prompts": {
            c: (P2_TEXT if c == "P2" else RB.CONDITION_SYSTEM.get(c)) for c in spec["conditions"]},
        "shuffle_seeds": list(SHUFFLE_SEEDS),
        "sampling_seeds": "BASE_SEED + shuffle_seed + k, k = 0..%d, BASE_SEED = %d"
                          % (DRAWS - 1, BASE_SEED),
        "models": sorted({m for m, _c, _p in spec["cells"]}),
        "cells": [{"model": m, "channel": c, "provider_pinned": p} for m, c, p in spec["cells"]],
        "collector": "scripts/run_arm_battery.py --arm %s" % arm,
        "written_at": datetime.datetime.now(datetime.timezone.utc)
                              .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "_note": "Written BEFORE the first call. Roster, backend pins, orders, seeds, "
                 "conditions, budgets and the P2 wording are fixed by the pre-registration "
                 "and reproduced here from the collector's constants, so none of them can be "
                 "chosen to suit a result. Transport failures are not written; every other "
                 "outcome, including refusals and pin-unavailable 404s, is.",
    }
    with io.open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1, sort_keys=True)
        fh.write("\n")


def plan(outdir, arm, spec, cells):
    total = want = 0
    for model, _ch, provider in cells:
        for cond in spec["conditions"]:
            have = existing(cell_file(outdir, arm, model, provider, cond))
            for key in schedule():
                total += 1
                want += key not in have
    return total, want


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--arm", choices=sorted(ARMS))
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--smoke", action="store_true",
                    help="one condition-N sheet per cell, into probes/<arm>-smoke/")
    ap.add_argument("--only-channel", choices=("ollama", "openrouter"), default=None)
    ap.add_argument("--models", nargs="*", default=None)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)

    if a.selftest:
        return selftest()
    if not a.arm or not (a.plan or a.run or a.smoke):
        print("pass --arm and one of --plan / --smoke / --run.")
        return 2
    spec = ARMS[a.arm]
    cells = [c for c in spec["cells"]
             if (a.only_channel is None or c[1] == a.only_channel)
             and (not a.models or c[0] in a.models)]
    if a.smoke:
        outdir = os.path.join(_SP.STUDY_DIR, "probes", spec["run"] + "-smoke")
    else:
        outdir = str(_SP.new_run_path(spec["run"]))

    total, want = plan(outdir, a.arm, spec, cells)
    print("")
    print("  arm        %s -> %s" % (a.arm, os.path.relpath(outdir, _SP.STUDY_DIR)))
    print("  prereg     %s" % spec["prereg"])
    print("  cells      %d  conditions %s  orders %s x %d draws"
          % (len(cells), ",".join(spec["conditions"]), list(SHUFFLE_SEEDS), DRAWS))
    print("  sheets     %d in the design, %d still to collect" % (total, want))
    if a.plan:
        return 0
    if not want and not a.smoke:
        print("  Nothing to collect.")
        return 2

    os.makedirs(outdir, exist_ok=True)
    manifest_path = os.path.join(outdir, "manifest.json")
    if not a.smoke and not os.path.exists(manifest_path):
        write_manifest(manifest_path, a.arm, spec)
        print("  manifest   written before the first call")

    _, _, load_env, _ = RB._client()
    api_key = load_env().get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
    if any(c[1] == "openrouter" for c in cells) and not api_key:
        print("  no OPENROUTER_API_KEY")
        return 1
    data = RB.load_items()
    items, instrument = data["items"], data.get("instrument", "ratchet-battery")

    consecutive = 0
    collected = collections.Counter()
    by_model = collections.OrderedDict()
    for cell in cells:
        by_model.setdefault(cell[0], []).append(cell)

    for model, mcells in by_model.items():
        print("=== %s  (%s)" % (model, ", ".join(str(c[2] or c[1]) for c in mcells)))
        fails = collections.Counter()
        draws = schedule()[:1] if a.smoke else schedule()
        conds = ("N",) if a.smoke else spec["conditions"]
        for shuffle_seed, seed in draws:
            for cond in conds:
                for _m, channel, provider in mcells:
                    if fails[provider] >= SKIP_CELL_AFTER:
                        continue
                    path = cell_file(outdir, a.arm, model, provider, cond)
                    if (shuffle_seed, seed) in existing(path):
                        continue
                    override, note = system_for(cond)
                    extra = {"arm": a.arm, "prereg": spec["prereg"]}
                    if note:
                        extra.update({"condition_note": note, "placebo_wording": "P2"})
                    rec = RB.one_run(
                        channel, model, items, cond, api_key, run_no=1,
                        temperature=TEMPERATURE, timeout=TIMEOUT, seed=seed,
                        think=(False if channel == "ollama" else None),
                        instrument=instrument, shuffle_seed=shuffle_seed,
                        max_tokens=spec["max_tokens"].get(model, MAX_TOKENS),
                        provider=provider, renumber=True, system_override=override,
                        extra=extra)
                    tag = "%s %-3s order %-2d seed %d %-10s" % (
                        (provider or "local")[:12], cond, shuffle_seed, seed, "")
                    if rec.get("failure_mode") == "transport" and rec.get("transient"):
                        fails[provider] += 1
                        consecutive += 1
                        print("    %s TRANSPORT, not written (%d in a row): %s"
                              % (tag, consecutive, str(rec.get("error"))[:90]), flush=True)
                        if consecutive >= ABORT_AFTER:
                            print("  ABORTED after %d consecutive transport failures. "
                                  "Re-running resumes." % consecutive)
                            return 1
                        continue
                    with io.open(path, "a", encoding="utf-8", newline="\n") as fh:
                        fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
                    if rec.get("pin_unavailable"):
                        fails[provider] += 1
                    else:
                        fails[provider] = 0
                    consecutive = 0
                    collected[cond] += 1
                    served = rec.get("provider")
                    pin_note = ("" if not provider or served in (None, provider)
                                else "  SERVED BY %s" % served)
                    print("    %s %-10s %2d/32  tok %-6s%s" % (
                        tag, rec.get("failure_mode") or "ok", rec.get("n_answers") or 0,
                        rec.get("tokens_out"), pin_note), flush=True)
        for provider, n in fails.items():
            if n >= SKIP_CELL_AFTER:
                print("    %s: abandoned after %d consecutive failures" % (provider, n))
    print("")
    print("  collected %d sheet(s): %s" % (sum(collected.values()), dict(collected)))
    if not a.smoke:
        print("  Next: python %s" % spec["analysis"])
    return 0


def selftest():
    fails = []

    def check(name, cond):
        print("  [%s] %s" % ("ok" if cond else "FAIL", name))
        if not cond:
            fails.append(name)

    import run_i3_wave as W
    check("orders are the wave's", tuple(W.SEEDS) == SHUFFLE_SEEDS)
    check("sampling base is the wave's", W.BASE_SEED == BASE_SEED)
    check("temperature is the wave's", W.TEMPERATURE == TEMPERATURE)
    p = RB.CONDITION_SYSTEM["P"]
    check("P2 matches P in word count", len(P2_TEXT.split()) == len(p.split()))
    check("P2 length within 15% of P", abs(len(P2_TEXT) - len(p)) <= 0.15 * len(p))
    check("P2 matches P in sentence count", P2_TEXT.count(". ") == p.count(". "))
    check("P2 carries no stance vocabulary",
          not stance_hits(P2_TEXT))
    check("P carries no stance vocabulary either (the reference the check is calibrated on)",
          not stance_hits(p))
    check("P2 is not already a condition", "P2" not in RB.CONDITION_SYSTEM)
    sched = schedule()
    check("fifteen draws per cell x condition", len(sched) == 15)
    check("every draw has a distinct sampling seed", len({s for _o, s in sched}) == 15)
    check("first draw is the wave's first seed", sched[0] == (11, 20260926))
    msgs = RB.build_prompt(RB.load_items()["items"], "P2", shuffle_seed=22, renumber=True,
                           system_override=P2_TEXT)
    check("P2 prompt carries P2 as its system message",
          msgs[0]["role"] == "system" and msgs[0]["content"] == P2_TEXT)
    check("P2 prompt has no user suffix", msgs[-1]["content"].rstrip().split("\n")[-1][:3]
          .rstrip(".").isdigit())
    check("renumbered prompt prints 1. first",
          "\n1. " in "\n" + msgs[-1]["content"].split("\n\n", 1)[1])
    for arm, spec in ARMS.items():
        models = [c[0] for c in spec["cells"]]
        if arm == "serving-path":
            per = collections.Counter(models)
            check("serving arm: every model on exactly two backends",
                  set(per.values()) == {2})
            check("serving arm: the two backends differ per model",
                  all(len({c[2] for c in spec["cells"] if c[0] == m}) == 2 for m in per))
        else:
            check("placebo arm: one cell per model", len(models) == len(set(models)))
        check("%s: every hosted cell is pinned" % arm,
              all(c[2] for c in spec["cells"] if c[1] == "openrouter"))
    print("")
    print("  %d check(s) failed" % len(fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
