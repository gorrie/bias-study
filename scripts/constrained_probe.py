#!/usr/bin/env python3
"""Score the instrument by CONSTRAINED DECODING: make an invalid answer ungenerable.

WHERE THIS CAME FROM
--------------------
Ian pointed at Ovando, "Constitutive Authorization at the Decoding Boundary:
Grammar-Constrained Decoding as a Positive, Generation-Time Security Control for LLM Agents"
(OSF s9gu6, June 2026). Its thesis is constitutive versus corrective enforcement -- a
grammar-constrained decoder and a post-hoc allowlist enforce the same policy, but the grammar
never produces the unauthorized artifact, "emission = 0 by construction", while the allowlist
produces it and then rejects it.

That is exactly this study's parsing problem, one domain over. `run_compass.py` is the
corrective arm: ask for 62 answers as prose, then parse, then classify what came back as
refusal / budget-exhausted / tokenizer garbage / truncated. **28.2% of condition-A runs are
invalid**, four models produce no valid sheet under any condition, one build exhausted its
budget on 12 of 15 runs, and three ablation pairs are excluded for emitting tokenizer garbage.
Every one of those is an artifact produced and then rejected.

Constrained decoding makes them ungenerable instead. Ollama accepts a JSON schema in `format`,
and an array of 62 enum values pins the whole answer sheet:

    {"type": "array", "minItems": 62, "maxItems": 62,
     "items": {"type": "string", "enum": ["Strongly Disagree", ..., "Strongly Agree"]}}

Verified working locally 2026-09-07. One call, 62 answers, all four labels legal and nothing
else, no parser in the path.

WHY THIS IS BETTER THAN THE TWO THINGS TRIED EARLIER THE SAME DAY
-----------------------------------------------------------------
`logit_probe.py` failed twice, and constrained decoding sidesteps both failures:

    scoring the four labels' first token   the labels COLLIDE -- "Strongly Agree" and
                                          "Strongly Disagree" both begin with 'Strong'
    a letter form (A/B/C/D)               separable, but NOT legend-invariant: reversing
                                          which letter means which option changed 48 of 62
                                          positions, and it is a different instrument

The grammar keeps the ORIGINAL WORDING. So it is the same instrument with the parser removed,
not a second instrument needing its own floors -- which was the objection that sent logit
scoring to v3.

THE COST, AND IT IS NOT SMALL
-----------------------------
**A model that would have refused can no longer refuse.** Refusal is §1's headline finding --
"refusal is elicited, not intrinsic", 14 of 42 models declining all 62 propositions with no
directive and every one of them stopping when given one -- and that finding is measured FROM
the invalid runs. Constrained decoding erases the evidence for it by construction.

So this is not a free upgrade. It is better for measuring POSITION and fatal for measuring
REFUSAL, and the two arms would have to run separately: the parser arm for willingness, the
grammar arm for position. Stated here so nobody adopts it as a drop-in.

    python scripts/constrained_probe.py --model qwen2.5:14b --condition D
    python scripts/constrained_probe.py --model qwen2.5:14b --condition D --agreement
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import time
import collections
import glob
import io
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import run_compass as RC   # noqa: E402

ENDPOINT = "http://localhost:11434/api/chat"

#: Index 0-3 -> label, matching the instrument's own encoding.
POSITIONS = ["Strongly Disagree", "Disagree", "Agree", "Strongly Agree"]


def schema(n, mode="sheet"):
    """The output grammar. `mode` decides whether the model gets an ANCHOR before each answer.

    `sheet`     an array of exactly n labels. Nothing else is emittable -- and measured
                2026-09-07, this DOES NOT REPLICATE: two runs of one cell differ by a median
                of 26 items of 62 against 3 for the prose arm.
    `reasoned`  an array of n objects, each `{"reasoning": string, "answer": enum}`. The answer
                is pinned exactly as before; the model may write before committing to it.

    WHY THE SECOND MODE EXISTS. The `sheet` arm's instability has an obvious candidate
    mechanism: free generation lets a model condition each answer on the ones it has already
    written, and a bare array of enums gives it no such anchor, so each position looks close to
    an independent draw. `reasoned` is the test of that claim -- it restores the anchor and
    changes nothing else. If the mechanism is right, this arm replicates; if it does not, the
    mechanism was wrong and the instability is something else.

    It is also what Ovando's framing actually supports. A grammar constrains the AUTHORIZED
    SURFACE -- the tool-call parameters, the four labels -- not the whole utterance. Pinning
    every token the model may emit is a stronger constraint than the argument asks for, and the
    stronger version is the one that broke.
    """
    if mode == "reasoned":
        return {"type": "array", "minItems": n, "maxItems": n,
                "items": {"type": "object",
                          "properties": {"reasoning": {"type": "string"},
                                         "answer": {"type": "string",
                                                    "enum": list(POSITIONS)}},
                          "required": ["reasoning", "answer"]}}
    return {"type": "array", "minItems": n, "maxItems": n,
            "items": {"type": "string", "enum": list(POSITIONS)}}


def run_constrained(model, condition, shuffle_seed=None, template="T01",
                    temperature=0.0, seed=None, max_tokens=4096, mode="sheet"):
    """One constrained run. Returns (positions_by_item_id, raw, problems).

    THE PROMPT COMES FROM `run_compass.build_prompt`, not from a copy written here. Two
    encodings of the instrument is how the two arms end up measuring different things while
    both claiming to be the battery -- the defect this file's own agreement check exists to
    detect. Only the DECODING changes.
    """
    # `load_items()` returns the whole instrument DOCUMENT -- schema, source, provenance note,
    # scale, retrieval date and `items`. The items are the list inside it, and `build_prompt`
    # orders them itself, so passing a pre-ordered list double-orders and passing the document
    # crashes on `it["id"]`. Both were my first two attempts.
    items = RC.load_items()["items"]
    ordered = RC.order_items(items, shuffle_seed)
    # build_prompt returns a ready `messages` list, system role included where the condition
    # has one. Used as-is: rebuilding it here is the second encoding of the instrument this
    # file's own docstring warns against.
    messages = RC.build_prompt(items, condition, shuffle_seed, template)

    opts = {"temperature": temperature, "num_predict": max_tokens}
    if seed is not None:
        opts["seed"] = seed
    body = {"model": model, "stream": False, "format": schema(len(ordered), mode),
            "options": opts, "messages": messages}
    req = urllib.request.Request(ENDPOINT, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    raw = json.loads(urllib.request.urlopen(req, timeout=1800).read())
    text = (raw.get("message") or {}).get("content") or ""

    problems = []
    try:
        labels = json.loads(text)
    except ValueError as exc:
        return None, text, ["unparseable JSON: %s" % exc]
    if not isinstance(labels, list):
        return None, text, ["not a list"]
    if len(labels) != len(ordered):
        problems.append("expected %d answers, got %d" % (len(ordered), len(labels)))
    out = {}
    for item, entry in zip(ordered, labels):
        # `reasoned` mode yields {"reasoning": ..., "answer": ...}; `sheet` yields the label.
        lab = entry.get("answer") if isinstance(entry, dict) else entry
        if lab not in POSITIONS:
            problems.append("illegal label %r" % lab)
            continue
        qid = item.get("id") if isinstance(item, dict) else None
        out[qid] = POSITIONS.index(lab)
    return out, text, problems


def collect(model, condition, out_dir, runs=None, temperature=None, seed_base=None,
            template=None, delay=0.5):
    """Collect constrained runs AT THE WAVE PROTOCOL and write `compass-run/1` records.

    WHY RECORDS AND NOT A PRIVATE FORMAT. The elicitation-format effect can only become a
    FLOOR if the existing machinery can read it -- `floor_table`, `floor_resolution`,
    `refusal_table`, the seed-dedupe rule, the degenerate-sheet rule, the modal convention.
    Writing a parallel analysis beside them would be a second implementation of every one of
    those, which is the fork this project has spent the day removing.

    So the grammar arm emits the same schema the parser arm does, with two fields that say
    what it is: `decoding: "grammar"` and `format_schema_sha256`. A record without those is a
    parser-arm record; the distinction is IN THE DATA rather than in the directory name,
    because a directory name is a convention and this project has already been bitten by one
    (`*-wave` matching the ablation arm).

    THE PROTOCOL IS THE WAVE'S, taken from `WAVE_PARAMS` rather than retyped: temperature 0.7,
    swept seed from 20260830, 5 runs, template T01. That is what makes the comparison
    like-for-like -- the previous check compared 5 swept-seed constrained runs against 33
    pooled parsed runs and the mismatch was worth 3 side-flips of the 20 it reported.
    """
    from wave import WAVE_PARAMS                      # noqa: PLC0415
    p = WAVE_PARAMS
    runs = runs or p["runs"]
    temperature = p["temperature"] if temperature is None else temperature
    seed_base = p["seed_base"] if seed_base is None else seed_base
    template = template or p["template"]

    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "%s__%s.jsonl"
                        % (model.replace("/", "__").replace(":", "_"), condition))
    schema_sha = hashlib.sha256(
        json.dumps(schema(62), sort_keys=True).encode()).hexdigest()

    wrote = 0
    with io.open(path, "a", encoding="utf-8", newline="\n") as fh:
        for k in range(runs):
            seed = seed_base + k
            t0 = time.time()
            try:
                got, text, problems = run_constrained(
                    model, condition, template=template,
                    temperature=temperature, seed=seed, max_tokens=p["max_tokens"])
            except Exception as exc:                   # noqa: BLE001
                got, text, problems = None, "", ["transport: %s" % exc]
            answers = ([{"q": q, "position": got[q]} for q in sorted(got)] if got else [])
            # `valid` uses the SAME rule as the parser arm: a full sheet of 62 answers. The
            # grammar guarantees legal labels, not a complete array, so this is not vacuous.
            rec = {
                "schema": "compass-run/1",
                "decoding": "grammar",
                "format_schema_sha256": schema_sha,
                "model": model, "condition": condition, "template": template,
                "shuffle_seed": None, "seed": seed, "run_no": k + 1,
                "temperature": temperature, "max_tokens": p["max_tokens"],
                "channel": "ollama",
                "answers": answers, "n_answers": len(answers), "n_items": 62,
                "valid": len(answers) == 62 and not problems,
                "ok": not problems, "problems": problems,
                "failure_mode": None if not problems else "constrained/incomplete",
                "response_text": text[:4000],
                "latency_ms": int((time.time() - t0) * 1000),
                "collected_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            wrote += 1
            print("      run %d/%d seed %d: %d answers%s"
                  % (k + 1, runs, seed, len(answers),
                     "" if not problems else "  " + str(problems[:1])))
            time.sleep(delay)
    return path, wrote


def parsed_modal(model, condition=None):
    """The model's parsed modal sheet, RESTRICTED TO ONE CONDITION.

    THE CONDITION FILTER IS THE WHOLE VALIDITY OF THE COMPARISON, and the first version of this
    function did not have one. It pooled every valid run of the model -- 105 of them, spanning
    conditions A, B, D and P, several temperatures and several dates -- and compared that
    against a 5-run condition-D constrained modal. The prompt conditions are the study's largest
    deliberate intervention; pooling them and calling the result "the parsed instrument" is the
    same composition error this project has now caught four times, and it produced 20
    side-flips, which is exactly what the letter-form logit attempt scored.

    Two different scoring methods landing on the identical disagreement was the tell: a shared
    number across unrelated designs is more likely to be a property of the comparison than of
    either method.
    """
    acc = collections.defaultdict(list)
    n = 0
    for path in sorted(glob.glob(os.path.join(STUDY, "runs", "**", "*.jsonl"), recursive=True)):
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
            if condition and r.get("condition") != condition:
                continue
            if not r.get("valid") or len(r.get("answers") or []) != 62:
                continue
            n += 1
            for a in r["answers"]:
                acc[a["q"]].append(a["position"])
    out = {}
    for q, v in acc.items():
        counts = collections.Counter(v)
        top = max(counts.values())
        out[q] = min(pos for pos, k in counts.items() if k == top)
    return out, n


def side(p):
    return p >= 2


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--model", default="")
    ap.add_argument("--condition", default="D")
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--seed", type=int, default=20260830)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--agreement", action="store_true")
    ap.add_argument("--collect", action="store_true",
                    help="write compass-run/1 records at the wave protocol into "
                         "runs/<date>-constrained/ so the existing floors machinery reads them")
    ap.add_argument("--all-local", action="store_true",
                    help="every LOCAL panel model, so the effect is not one model")
    ap.add_argument("--conditions", default="D,P")
    ap.add_argument("--replicate", action="store_true",
                    help="the cheap decisive check: does one cell agree with itself?")
    ap.add_argument("--mode", default="sheet", choices=["sheet", "reasoned"])
    ap.add_argument("--max-tokens", type=int, default=8192)
    args = ap.parse_args(argv)

    if args.replicate:
        # THE TEST THE SHEET ARM FAILED, RUN FIRST AND ON ITS OWN.
        #
        # The previous attempt collected 50 runs across 5 models and 2 conditions, computed a
        # cross-arm distance, and nearly published it as the largest factor in the study --
        # before checking whether the arm agreed with ITSELF. It did not: median 26 side-flips
        # between two runs of one cell against 3 for the prose arm.
        #
        # So this runs the cheap decisive check on ONE cell before anything is collected at
        # scale. Five runs, one model, one condition: do repeat measurements agree?
        import floor_table as F                        # noqa: PLC0415
        print("REPLICATE TEST -- %s / %s / mode=%s, %d runs"
              % (args.model, args.condition, args.mode, args.runs))
        sheets_r = []
        for k in range(args.runs):
            got, _text, probs = run_constrained(
                args.model, args.condition, temperature=args.temperature,
                seed=args.seed + k, mode=args.mode, max_tokens=args.max_tokens)
            print("   run %d: %d answers%s"
                  % (k + 1, len(got or {}), "" if not probs else "  " + str(probs[:1])))
            if got and len(got) == 62:
                sheets_r.append(got)
        if len(sheets_r) < 2:
            print("fewer than two usable sheets -- cannot test replication.")
            return 1
        d = sorted(F.both_stats(sheets_r[i], sheets_r[j])[0]
                   for i in range(len(sheets_r)) for j in range(i + 1, len(sheets_r)))
        med, mx = d[len(d) // 2], max(d)
        print("")
        print("  own run-to-run spread: median %d, max %d side-flips of 62 (%d pair(s))"
              % (med, mx, len(d)))
        print("  reference: the PROSE arm on these cells is median 3; the bare-sheet grammar")
        print("  arm is median 26; the run-to-run replicate floor is p90 5.")
        print("")
        # THE VERDICT IS ABSOLUTE, AGAINST THE REPLICATE FLOOR -- NOT RELATIVE TO A REMEMBERED
        # NUMBER. A first version compared against a hardcoded 26 (the bare sheet's median
        # ACROSS cells) and printed "better than the bare sheet" when run in sheet mode on a
        # cell reading 22, which is the bare sheet. A threshold carried in from another cell's
        # aggregate is not a threshold.
        FLOOR = 5           # the study's own run-to-run replicate p90
        if med <= FLOOR:
            print("  REPLICATES (median %d, inside the replicate floor of %d)." % (med, FLOOR))
            if args.mode == "reasoned":
                print("  The anchor hypothesis SURVIVES: giving the model room to write before")
                print("  each pinned answer restores a stable measurement, so the bare sheet's")
                print("  instability was the missing anchor and not the grammar. A cross-arm")
                print("  comparison is now worth collecting.")
        else:
            print("  DOES NOT REPLICATE: median %d against a replicate floor of %d, and the"
                  % (med, FLOOR))
            print("  prose arm on these cells is 3. No comparison built on this arm means")
            print("  anything until it does.")
            if args.mode == "reasoned":
                print("")
                print("  AND THE ANCHOR HYPOTHESIS IS REFUTED. Restoring free text before each")
                print("  answer did not stabilise it, so the instability is a property of")
                print("  constrained decoding on this instrument rather than of the missing")
                print("  anchor -- the mechanism proposed in the last write-up was wrong and")
                print("  the write-up has to say so.")
        return 0

    if args.collect:
        # THE ARM, at the wave protocol, over every local panel model unless one is named.
        # Local only: the grammar arm needs `format`, which is an ollama feature, and the
        # hosted models in the panel go through OpenRouter.
        from wave import load_panel                    # noqa: PLC0415
        if args.all_local:
            models = [m for m in load_panel()["models"] if "/" not in m]
        else:
            models = [args.model]
        conditions = [c.strip() for c in args.conditions.split(",") if c.strip()]
        out_dir = os.path.join(
            STUDY, "runs",
            "%s-constrained" % datetime.date.today().isoformat())
        print("GRAMMAR ARM at the wave protocol -> %s"
              % os.path.relpath(out_dir, STUDY))
        print("  %d model(s) x %d condition(s), 5 swept seeds each, no API spend"
              % (len(models), len(conditions)))
        total = 0
        for m in models:
            for c in conditions:
                print("  %s / %s" % (m, c))
                _path, n = collect(m, c, out_dir)
                total += n
        print("")
        print("wrote %d record(s)" % total)
        return 0

    sheets = []
    for k in range(args.runs):
        got, text, problems = run_constrained(
            args.model, args.condition, seed=args.seed + k, temperature=args.temperature)
        status = "OK" if got and not problems else "PROBLEMS: %s" % problems[:2]
        print("  run %d: %s answers, %s"
              % (k + 1, len(got or {}), status))
        if got:
            sheets.append(got)
        if not got:
            print("      raw head: %r" % text[:120])

    if not sheets:
        print("no usable constrained sheet -- and that is a real failure, not a refusal:")
        print("the grammar makes a refusal ungenerable, so an empty result here means the")
        print("call or the schema failed rather than the model declining.")
        return 1

    dist = collections.Counter(v for s in sheets for v in s.values())
    print("")
    print("  position distribution: %s"
          % {POSITIONS[k]: dist[k] for k in sorted(dist)})

    if args.agreement:
        pm, n_runs = parsed_modal(args.model, args.condition)
        print("")
        print("AGREEMENT against the parsed instrument (%d valid parsed run(s))" % n_runs)
        if not pm:
            print("  no parsed sheets for this model -- cannot check, and that is not a pass.")
            return 1
        # Compare the constrained modal against the parsed modal, modal-vs-modal, which is the
        # unit every floor in this study uses.
        acc = collections.defaultdict(list)
        for s in sheets:
            for q, v in s.items():
                acc[q].append(v)
        cm = {}
        for q, v in acc.items():
            counts = collections.Counter(v)
            top = max(counts.values())
            cm[q] = min(p for p, k in counts.items() if k == top)

        shared = sorted(set(cm) & set(pm))
        exact = sum(1 for q in shared if cm[q] == pm[q])
        flips = sum(1 for q in shared if side(cm[q]) != side(pm[q]))
        print("  items compared   %d" % len(shared))
        print("  exact match      %d (%.1f%%)" % (exact, 100.0 * exact / max(1, len(shared))))
        print("  side-flips       %d" % flips)
        print("")
        print("  Against this study's own floors: the modal estimator's side-flip p90 is 3 and")
        print("  the run-to-run replicate p90 is 5. Inside that band means the grammar arm and")
        print("  the parser arm are indistinguishable at this study's resolution -- which is")
        print("  what would let the grammar arm inherit the published floors instead of")
        print("  needing its own. The letter-form logit attempt scored 20 side-flips here.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
