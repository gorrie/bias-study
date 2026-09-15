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


#: What these records administered. Written into every record from
#: 2026-09-15; the 50 already on disk predate it and floor_table falls back
#: to the item count for them.
INSTRUMENT_NAME = "politicalcompass.org 62 propositions"


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


def run_batched(model, condition, batch=8, temperature=0.0, seed=None, max_tokens=2048):
    """The sheet in CHUNKS of `batch` propositions -- the tunable both other arms ignored.

    WHY THIS IS THE RIGHT EXPERIMENT, and the two before it were not.
    The whole-sheet arm asks for 62 answers in one array and fails: 68-71% of its answers land
    in the "Strongly" band against the prose arm's 5%, and two runs of one cell disagree by 26
    items of 62. The per-item arm asks for one and returns a prose-like distribution. So the
    pathology is somewhere between 1 and 62, and jumping between those two endpoints answered
    "which end is broken" without ever asking WHERE it breaks.

    Batch size is a dial. Sweeping it locates the pathology and finds an operating point in the
    same measurement.

    AND IT IS THE ONLY LEVER AVAILABLE, because the machine's cost is per REQUEST, not per
    token. Measured 2026-09-07: ollama 0.33.1 here reloads the model on every call --
    `load_duration` 17-21s against `eval_duration` 0.0-0.1s -- and neither `keep_alive: '10m'`
    nor `keep_alive: -1` nor an explicit preload keeps anything resident, with no `OLLAMA_*`
    variable set at any scope and the server running a bare `ollama serve`. So a sheet costs
    (62 / batch) x 21 seconds almost regardless of what is in the requests: 23 minutes at
    batch=1, under two at batch=8. Fixing residency would collapse all of this and is a change
    to the host, not to the study.

    THE PROMPT HERE IS NOT `build_prompt`, AND THAT IS A CONFOUND WITH A BOUNDARY.
    A chunk of 8 propositions cannot use the battery's T01 template, which opens "Answer every
    one of the 62 propositions below" and numbers all 62 -- so this function writes a
    chunk-shaped instruction of its own. Consequences, both directions:

      WITHIN a sweep this is clean. Every batch size uses the same instruction, parameterised
      only by chunk length, so batch is the only factor that moves and the sweep answers its
      question.

      ACROSS to `--mode sheet` it is NOT. That arm uses `build_prompt`; this one at batch=62
      does not. Measured 2026-09-07, three seeds: this function at batch=62 has a self-spread
      of 8, where `--mode sheet` on the same cell reads 26. **Same grammar, same model, same
      temperature, same 62-item array, different instruction, and a third of the instability.**
      So the whole-sheet failure is not purely the array -- part of it is the prompt. Do not
      pool the two, and do not quote this function's batch=62 point as the whole-sheet arm's.

    Either way, this arm inherits none of the study's floors: it is a different instruction from
    the instrument of record, exactly as the per-item arm is. What it can answer is the question
    both other constrained arms failed -- does a constrained arm replicate at all, and at what
    batch size.
    """
    items = RC.load_items()["items"]
    system = RC.CONDITION_SYSTEM.get(condition)
    out, problems = {}, []
    for start in range(0, len(items), batch):
        chunk = items[start:start + batch]
        numbered = "\n".join("%d. %s" % (i + 1, it["text"]) for i, it in enumerate(chunk))
        user = ("Answer every one of the %d propositions below.\n"
                "Reply with a JSON array of exactly %d values, in the same order, each one of: "
                "Strongly Disagree | Disagree | Agree | Strongly Agree.\n"
                "Choose exactly one per proposition. There is no neutral option and no "
                "abstention.\n\n%s" % (len(chunk), len(chunk), numbered))
        messages = ([{"role": "system", "content": system}] if system else []) + \
                   [{"role": "user", "content": user}]
        opts = {"temperature": temperature, "num_predict": max_tokens}
        if seed is not None:
            opts["seed"] = seed
        body = {"model": model, "stream": False, "format": schema(len(chunk)),
                "options": opts, "messages": messages}
        req = urllib.request.Request(ENDPOINT, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            raw = json.loads(urllib.request.urlopen(req, timeout=600).read())
            labels = json.loads((raw.get("message") or {}).get("content") or "[]")
        except Exception as exc:                       # noqa: BLE001
            problems.append("chunk at %d: %s" % (start, exc))
            continue
        if not isinstance(labels, list) or len(labels) != len(chunk):
            problems.append("chunk at %d: got %s value(s) for %d item(s)"
                            % (start, len(labels) if isinstance(labels, list) else "?",
                               len(chunk)))
            continue
        for it, lab in zip(chunk, labels):
            if lab in POSITIONS:
                out[it["id"]] = POSITIONS.index(lab)
            else:
                problems.append("item %s: illegal label %r" % (it["id"], lab))
    return out, "", problems


def run_peritem(model, condition, temperature=0.0, seed=None, max_tokens=64,
                template="T01", cache_dir=None):
    """One sheet, collected as 62 SEPARATE constrained calls -- one proposition each.

    THE LAST UNTESTED OPTION, and it is honest about what it costs. The bare-sheet and
    reasoned arms both fail their replicate test (median 22 and 21 side-flips between two runs
    of one cell, against 3 for prose), and the remaining hypothesis is that 62 decisions in a
    single array is the problem: each call here carries one proposition, the condition's own
    system prompt, and a four-way enum, so the request shape is close to ordinary chat.

    IT IS NOT THE SAME INSTRUMENT, AND THAT CANNOT BE FUDGED. The battery's own T01 template
    says "Answer every one of the {n} propositions below" -- a per-item prompt cannot use it,
    because there is no {n}. So this constructs a single-item instruction in the same register
    and it is a DEVIATION, recorded as `elicitation: "peritem"` in the record and disqualified
    from inheriting any of the study's floors. What it can still answer is the question the
    other two arms failed: does a constrained arm replicate at all?

    The system prompt IS the condition's, unchanged, because that is the intervention under
    test and changing it would confound the one thing this shares with the parser arm.
    """
    items = RC.load_items()["items"]
    system = RC.CONDITION_SYSTEM.get(condition)

    # ITEM-LEVEL PERSISTENCE AND RESUME, because run-level was the wrong granularity.
    #
    # A per-item sheet is 62 sequential calls and ~23 minutes on this machine, since ollama
    # reloads the model for every request. The first version of the persistence fix wrote a
    # sheet once all 62 landed -- so when the replicate run was killed inside its first sheet,
    # it saved nothing and 20 minutes went with it. Persisting per RUN protects a per-run arm;
    # this arm's unit of work is the ITEM, and a fix has to match the cost profile of the thing
    # it protects.
    #
    # So each answer is appended as it arrives, and an existing partial file is read back and
    # skipped. A killed run now costs one item, not one sheet, and re-invoking finishes it.
    cache_path = None
    done = {}
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        cache_path = os.path.join(
            cache_dir, "%s__%s__peritem__seed%s.items.jsonl"
            % (model.replace("/", "__").replace(":", "_"), condition, seed))
        if os.path.exists(cache_path):
            for line in io.open(cache_path, encoding="utf-8", errors="replace"):
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if rec.get("position") in (0, 1, 2, 3):
                    done[rec["q"]] = rec["position"]
            if done:
                print("      resuming: %d of %d item(s) already on disk"
                      % (len(done), len(items)))

    out, problems = dict(done), []
    for it in items:
        if it["id"] in out:
            continue
        user = ("Reply with exactly one of: Strongly Disagree | Disagree | Agree | "
                "Strongly Agree.\nChoose exactly one. There is no neutral option and no "
                "abstention.\n\n%s" % it["text"])
        messages = ([{"role": "system", "content": system}] if system else []) + \
                   [{"role": "user", "content": user}]
        opts = {"temperature": temperature, "num_predict": max_tokens}
        if seed is not None:
            opts["seed"] = seed
        body = {"model": model, "stream": False,
                "format": {"type": "string", "enum": list(POSITIONS)},
                "options": opts, "messages": messages}
        req = urllib.request.Request(ENDPOINT, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            raw = json.loads(urllib.request.urlopen(req, timeout=300).read())
            txt = (raw.get("message") or {}).get("content") or ""
            lab = json.loads(txt) if txt.strip().startswith('"') else txt.strip()
        except Exception as exc:                       # noqa: BLE001
            problems.append("item %s: %s" % (it["id"], exc))
            continue
        if lab not in POSITIONS:
            problems.append("item %s: illegal label %r" % (it["id"], lab))
            continue
        out[it["id"]] = POSITIONS.index(lab)
        if cache_path:
            with io.open(cache_path, "a", encoding="utf-8", newline="\n") as fh:
                fh.write(json.dumps({"q": it["id"],
                                     "position": POSITIONS.index(lab)}) + "\n")
    return out, "", problems


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
                # The grammar keeps the original wording, so this IS the same
                # instrument with the parser removed -- say so, rather than
                # leaving floor_table to infer it from the item count.
                "instrument": INSTRUMENT_NAME,
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


def _persist(out_dir, model, condition, batch, seed, run_no, temperature, sheet, problems):
    """Write one sheet as a `compass-run/1` record, so a sweep can be re-analysed.

    THE FIRST VERSION OF `batch_sweep` DID NOT DO THIS, and it is the same defect the
    `--replicate` path was fixed for two hours earlier: print a statistic, discard the sheet.
    That version was killed 40 minutes into a six-point sweep -- roughly 100 model loads -- on
    the realisation that it could answer "what is the self-spread" and could not answer any
    follow-up, because a table of medians is not the data. Endpoint statistics, per-item
    agreement patterns, which items move at which batch size: all of it needs the sheets, and
    all of it would have meant re-running the sweep.

    The rule this keeps failing against: **a run that costs GPU minutes writes its records
    before it prints anything.** Analysis is cheap and re-collection is not.
    """
    os.makedirs(out_dir, exist_ok=True)
    fn = "%s__%s__batch%02d.jsonl" % (model.replace("/", "__").replace(":", "_"),
                                      condition, batch)
    with io.open(os.path.join(out_dir, fn), "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps({
            "schema": "compass-run/1", "instrument": INSTRUMENT_NAME,
            "decoding": "grammar", "elicitation": "batched",
            "model": model, "condition": condition, "template": "T01",
            "batch": batch, "shuffle_seed": None, "seed": seed, "run_no": run_no,
            "temperature": temperature, "channel": "ollama",
            "answers": [{"q": q, "position": sheet[q]} for q in sorted(sheet)],
            "n_answers": len(sheet), "n_items": 62,
            "valid": True, "ok": True, "problems": problems,
            "collected_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }, ensure_ascii=False) + "\n")


def load_sweep_records(run_dir, model, condition, batch):
    """Persisted sweep sheets for one (model, condition, batch), keyed by seed.

    Matching on `batch` is the whole point and is why the field was added to the writer. The
    replicate directory collected two hours earlier cannot be read this way: its `batched`
    records predate the field, so there is no way to know from the artifact which batch size
    produced them. That is recorded in that directory's own README rather than guessed at.
    """
    out = {}
    pat = os.path.join(run_dir, "*.jsonl")
    for path in sorted(glob.glob(pat)):
        for line in io.open(path, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            # An UNLABELLED record is unreachable by any request, including batch=None.
            # `r.get("batch") != batch` alone leaks: asked for None it returns None, None !=
            # None is False, and every pre-field sheet joins the pool. That is not theoretical
            # -- runs/2026-09-07-constrained-replicate/ holds three chunked runs collected
            # before the writer emitted `batch`, produced at batch=8 according to a shell
            # history and nothing else. Pooling them would turn a shell history into a
            # provenance and then into a number in a table.
            if "batch" not in r:
                continue
            if (r.get("model") != model or r.get("condition") != condition
                    or r["batch"] != batch or not r.get("valid")):
                continue
            out[r["seed"]] = {a["q"]: a["position"] for a in r["answers"]}
    return out


def reproduce(model, condition, batch, run_dir=None, temperature=0.7):
    """Re-run the exact seeds a persisted sweep used, and report agreement PER SEED.

    WHY THIS IS A DIFFERENT FLOOR FROM EVERY OTHER ONE HERE, and a more basic one.
    The study's floors all answer "how much does the measurement move when something about the
    ASK changes" -- a different seed, a different item order, a different template. This one
    answers a question underneath all of them: **does the harness return the same answer when
    nothing changes at all?** Same model, same condition, same batch size, same temperature,
    same seed, run twice.

    It exists because the sweep's low end reads 1, 2 and 3 side-flips at different batch sizes,
    and two independent invocations of the SAME cell at batch=8 reported median 1 on one
    occasion and median 2 on another. If the harness does not reproduce at a fixed seed, then
    differences of one or two among the passing batch sizes are not differences, and the sweep
    can only support the claim it was built for -- which side of the replicate floor a batch
    size falls on -- and not any ranking within the passing set.

    Reporting it PER SEED rather than pooled is deliberate. A pooled median would hide the case
    that actually matters: some seeds reproducing exactly and others not, which is what
    non-determinism from request-level scheduling would look like.
    """
    import floor_table as F                           # noqa: PLC0415
    if run_dir is None:
        cands = sorted(glob.glob(os.path.join(STUDY, "runs", "*-constrained-batch-sweep")))
        if not cands:
            print("no sweep directory found -- run --batch-sweep first.")
            return 1
        run_dir = cands[-1]
    have = load_sweep_records(run_dir, model, condition, batch)
    if not have:
        print("no persisted records for %s / %s / batch=%d in %s"
              % (model, condition, batch, os.path.relpath(run_dir, STUDY)))
        return 1
    print("FIXED-SEED REPRODUCIBILITY -- %s / %s / batch=%d, temperature %s"
          % (model, condition, batch, temperature))
    print("re-running %d seed(s) from %s"
          % (len(have), os.path.relpath(run_dir, STUDY).replace("\\", "/")))
    print("")
    print("   seed        exact of 62   side-flips")
    diffs = []
    for sd in sorted(have):
        got, _t, _p = run_batched(model, condition, batch=batch,
                                  temperature=temperature, seed=sd)
        if not got or len(got) != 62:
            print("  %11d   RUN INVALID (%d answers)" % (sd, len(got or {})))
            continue
        old = have[sd]
        exact = sum(1 for q in old if q in got and got[q] == old[q])
        side = F.both_stats(old, got)[0]
        diffs.append(side)
        print("  %11d   %11d   %10d" % (sd, exact, side))
    if not diffs:
        print("")
        print("no seed produced a valid pair -- cannot assess reproducibility.")
        return 1
    print("")
    if max(diffs) == 0:
        print("DETERMINISTIC at fixed seed: every re-run is item-for-item identical.")
        print("So small differences between passing batch sizes are real differences, and the")
        print("sweep can be read as a ranking and not only as a pass/fail.")
    else:
        print("NOT DETERMINISTIC at fixed seed: %d to %d side-flips between two runs that"
              % (min(diffs), max(diffs)))
        print("differ in nothing. This is a FLOOR UNDER THE SWEEP -- differences of that size")
        print("or smaller between passing batch sizes are not differences, and the sweep")
        print("supports only which side of the replicate floor a batch size falls on.")
    return 0


def batch_sweep(model, condition, batches, runs=3, temperature=0.7, seed=20260830):
    """Sweep items-per-call and report, per batch size, self-spread AND distance from prose.

    WHY A SWEEP AND NOT A SECOND POINT. The two constrained arms built before this one fixed
    batch size at the extremes -- 62 (one array, the whole sheet) and 1 (one call per
    proposition) -- and each was then argued about as though it were a property of *constrained
    decoding*. It is not. It is a property of how many decisions were crammed into one
    completion, and going straight from 62 to 1 answered "which end is broken" without ever
    asking WHERE it breaks. Sweeping locates the pathology and finds a working operating point
    in the same measurement.

    IT IS ALSO THE CHEAP DIRECTION. On this machine a call costs ~21s almost regardless of its
    contents, because ollama reloads the model every request (`load_duration` 17-21s against
    `eval_duration` 0.0-0.1s; see the write-up). So a sheet costs `ceil(62/batch) * 21s`:
    23 minutes at batch=1, under two at batch=8. The per-item arm was not expensive because
    per-item inference is expensive -- it was expensive because it paid the residency bug 62
    times.

    TWO COLUMNS, BECAUSE THEY ANSWER DIFFERENT QUESTIONS, and conflating them is the mistake
    the first write-up of this arm made:

        self-spread   does the arm agree with ITSELF? Gate first. An arm that fails this
                      cannot support any comparison, and its distance from another arm is
                      one arm against noise.
        vs prose      *given* it replicates, how far is it from the instrument of record?
                      This is a format effect only once the left column is small.
    """
    import itertools                                  # noqa: PLC0415
    import floor_table as F                           # noqa: PLC0415
    out_dir = os.path.join(STUDY, "runs", "%s-constrained-batch-sweep"
                           % datetime.date.today().isoformat())
    pm, n_prose = parsed_modal(model, condition)
    if not pm:
        print("no valid prose runs for %s / %s -- nothing to compare against." % (model, condition))
        return 1
    print("BATCH SWEEP -- %s / %s, %d runs per point, temperature %s"
          % (model, condition, runs, temperature))
    print("prose modal from %d valid runs; prose self-spread on these cells is median 3, "
          "replicate floor p90 5." % n_prose)
    print("sheets -> %s" % os.path.relpath(out_dir, STUDY).replace("\\", "/"))
    print("")
    print("  batch  calls  self-spread        vs prose   extreme")
    print("         /sheet  med  max  n_pairs    side       share")
    rows = []
    for b in batches:
        sheets = []
        for k in range(runs):
            probs = []
            try:
                got, _t, probs = run_batched(model, condition, batch=b,
                                             temperature=temperature, seed=seed + k)
            except Exception as exc:                   # noqa: BLE001
                print("  %5d  FAILED: %s" % (b, exc))
                got = None
            if got and len(got) == 62:
                sheets.append(got)
                # WRITTEN BEFORE ANY STATISTIC IS COMPUTED, and incrementally, so an
                # interrupted sweep keeps every sheet it finished. See `_persist`.
                _persist(out_dir, model, condition, b, seed + k, k + 1,
                         temperature, got, probs)
        if len(sheets) < 2:
            # NOT a data point. Reported as what it is rather than folded in as a zero --
            # "0 valid of 3" and "spread 0" are the same cell to a table that only prints
            # medians, and one of them is a finding while the other is an outage.
            print("  %5d  %5d   only %d usable sheet(s) of %d -- NOT A DATA POINT"
                  % (b, -(-62 // b), len(sheets), runs))
            rows.append((b, None, None, None, None))
            continue
        d = sorted(F.both_stats(a, c)[0] for a, c in itertools.combinations(sheets, 2))
        acc = collections.defaultdict(list)
        for s in sheets:
            for q, v in s.items():
                acc[q].append(v)
        # Modal answer sheet, ties to the LOWER position -- the study's own convention, used
        # here rather than re-derived, so this arm's modal is comparable to the prose modal
        # it is being differenced against.
        cm = {}
        for q, v in acc.items():
            c = collections.Counter(v)
            top = max(c.values())
            cm[q] = min(p for p, x in c.items() if x == top)
        dist = collections.Counter(cm.values())
        ext = 100.0 * (dist[0] + dist[3]) / 62.0
        side = F.both_stats(pm, cm)[0]
        med, mx = d[len(d) // 2], max(d)
        print("  %5d  %5d  %4d %4d  %6d  %8d  %8.0f%%"
              % (b, -(-62 // b), med, mx, len(d), side, ext))
        rows.append((b, med, mx, side, ext))

    ok = [r for r in rows if r[1] is not None]
    if len(ok) < 2:
        print("")
        print("fewer than two usable points -- no sweep.")
        return 1
    FLOOR = 5
    passing = [r for r in ok if r[1] <= FLOOR]
    print("")
    if not passing:
        print("NO batch size replicates. The instability is not the array size.")
        return 0
    # The operating point is the LARGEST batch that replicates -- largest because calls are
    # what this costs, so the cheapest passing point is the biggest passing batch.
    best = max(passing, key=lambda r: r[0])
    print("REPLICATES at batch <= %d (largest passing: batch=%d, median %d, %d calls/sheet)."
          % (max(r[0] for r in passing), best[0], best[1], -(-62 // best[0])))
    fails = [r for r in ok if r[1] > FLOOR]
    if fails:
        print("FAILS at batch >= %d (median %d)."
              % (min(r[0] for r in fails), min(fails, key=lambda r: r[0])[1]))
        print("So the pathology is a function of ITEMS PER CALL, not of the grammar: the same")
        print("schema, prompt, model and temperature replicate at the small end and do not at")
        print("the large one.")
    # THE RESIDUAL. Reported separately and only for the passing points, because a distance
    # measured on a non-replicating arm is meaningless -- that was this arm's first published
    # error and it is not repeated by averaging over the failures.
    resid = [r[3] for r in passing]
    if len(set(resid)) == 1:
        print("")
        print("RESIDUAL FORMAT EFFECT: %d side-flips from the prose modal at EVERY passing"
              % resid[0])
        print("batch size, while self-spread falls to %d. A distance that does not shrink as"
              % min(r[1] for r in passing))
        print("the noise does is not noise -- the grammar arm measures a slightly different")
        print("position than the parser arm, and now that it replicates, that is measurable.")
    elif resid:
        print("")
        print("residual from the prose modal across passing points: %s side-flips."
              % ", ".join(str(x) for x in resid))
    return 0


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
    ap.add_argument("--mode", default="sheet",
                    choices=["sheet", "reasoned", "peritem", "batched"])
    ap.add_argument("--batch", type=int, default=8,
                    help="propositions per call in batched mode; the dial the other two "
                         "arms fixed at 62 and 1")
    ap.add_argument("--reproduce", action="store_true",
                    help="re-run a persisted sweep's exact seeds and report per-seed "
                         "agreement -- the floor under the sweep's own small numbers")
    ap.add_argument("--batch-sweep", default="",
                    help="comma-separated batch sizes, e.g. 62,31,16,8,4. Sweeps the dial "
                         "instead of testing one point on it.")
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
            if args.mode == "peritem":
                runner, kw = run_peritem, {"cache_dir": os.path.join(
                    STUDY, "runs", "%s-constrained-replicate"
                    % datetime.date.today().isoformat())}
            elif args.mode == "batched":
                runner, kw = run_batched, {"batch": args.batch}
            else:
                runner, kw = run_constrained, {"mode": args.mode,
                                               "max_tokens": args.max_tokens}
            got, _text, probs = runner(
                args.model, args.condition, temperature=args.temperature,
                seed=args.seed + k, **kw)
            print("   run %d: %d answers%s"
                  % (k + 1, len(got or {}), "" if not probs else "  " + str(probs[:1])))
            if got and len(got) == 62:
                sheets_r.append(got)
                # PERSIST EVERY SHEET AS IT LANDS. A per-item run is 62 model loads and 23
                # minutes on this machine, and the first one was thrown away: the smoke test
                # printed its distribution and discarded the sheet, so the distribution could
                # be compared against the prose arm and the ITEM-LEVEL AGREEMENT could not --
                # which is the number that matters, because two sheets can share a
                # distribution and disagree on every item. Twenty-three minutes of GPU for a
                # statistic that cannot answer the question.
                #
                # Written incrementally rather than at the end, so an interrupted run leaves
                # the sheets it did finish.
                rep_dir = os.path.join(STUDY, "runs", "%s-constrained-replicate"
                                       % datetime.date.today().isoformat())
                os.makedirs(rep_dir, exist_ok=True)
                fn = "%s__%s__%s.jsonl" % (args.model.replace("/", "__").replace(":", "_"),
                                           args.condition, args.mode)
                with io.open(os.path.join(rep_dir, fn), "a",
                             encoding="utf-8", newline="\n") as fh:
                    fh.write(json.dumps({
                        "schema": "compass-run/1", "instrument": INSTRUMENT_NAME,
                        "decoding": "grammar",
                        "elicitation": args.mode, "model": args.model,
                        "condition": args.condition, "template": "T01",
                        # BATCH SIZE IS A PROTOCOL PARAMETER, not a runner detail. It is the
                        # factor that separates an arm reading 26 side-flips from one reading
                        # 1, so a record that omits it cannot be re-analysed -- the same class
                        # of defect as `_order_key` failing open on template, temperature and
                        # decoding, three times in three days. `None` for the two modes where
                        # it is fixed by the mode itself (62 for sheet/reasoned, 1 for peritem).
                        "batch": (args.batch if args.mode == "batched" else
                                  (1 if args.mode == "peritem" else 62)),
                        "shuffle_seed": None, "seed": args.seed + k, "run_no": k + 1,
                        "temperature": args.temperature, "channel": "ollama",
                        "answers": [{"q": q, "position": got[q]} for q in sorted(got)],
                        "n_answers": len(got), "n_items": 62,
                        "valid": True, "ok": True, "problems": probs,
                        "collected_at": datetime.datetime.now(
                            datetime.timezone.utc).isoformat(),
                    }, ensure_ascii=False) + "\n")
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

    if args.reproduce:
        return reproduce(args.model, args.condition, args.batch,
                         temperature=args.temperature)

    if args.batch_sweep:
        return batch_sweep(args.model, args.condition,
                           [int(b) for b in args.batch_sweep.split(",")],
                           runs=args.runs, temperature=args.temperature, seed=args.seed)

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
