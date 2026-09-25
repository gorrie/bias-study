#!/usr/bin/env python3
"""The local pressure gradient on stock and ablated builds, collected and analysed properly.

PREREG-2026-09-25-local-gradient.md governs this and was committed before the first
non-smoke call. Read it for the question, the predictions and the kill rules; this docstring
says only what the code does.

WHAT IT REPLACES
----------------
`mask_gradient.py` (runs/mask-gradient/) ran four local builds through five conditions at
temperature 0, one greedy draw, `num_predict` 400, and judged one arm with an abliteration of
a subject family. Only 7-18 of 50 answers per arm ended cleanly, the budget was never recorded
on a record, and because it sent `question_text` rather than the protocol's user prompt, its
B and C were the bare question: the "A 3.0 / B 3.0 / C 3.0 / D 4.8 / E 5.0" it printed is,
in the battery's letters, A / N / N / D / E, on 5-6 scored answers per condition.

TWO ARMS, ONE SITTING
---------------------
Primary, judge-free: the 32-item battery through the study's own collector, `run_battery.py`,
invoked once per (build, condition, order) group, protocol v2 (`--renumber`), temperature 0.7,
five swept seeds, three presentation orders, reasoning off, the protocol budget of 40,960
tokens recorded on every record. Groups are never topped up: `run_battery`'s resume counts
VALID sheets, so a resumed group would re-draw invalid sheets until they came back valid.

Secondary, judged: the ten neutral May questions, the same conditions, five seeds, a recorded
budget, scored blind by local judges of families that are not subjects, each gated first on
answers the four-judge May panel scored unanimously.

    python scripts/local_gradient.py --plan                 # builds, cells, gate, no calls
    python scripts/local_gradient.py --smoke                # one sheet per build x N/A/D
    python scripts/local_gradient.py --collect              # the battery arm, resumable
    python scripts/local_gradient.py --replicate            # the seed-replicate check
    python scripts/local_gradient.py --judged-collect       # the free-text answers
    python scripts/local_gradient.py --calibrate-judges     # the judge gate
    python scripts/local_gradient.py --judge                # blind scoring
    python scripts/local_gradient.py --report [--json]      # every pre-registered number
    python scripts/local_gradient.py --selftest

Exit 0 done, 1 a step failed, 2 nothing to do.
"""
from __future__ import annotations

import argparse
import collections
import datetime
import glob
import io
import json
import os
import random
import statistics as st
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, HERE)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:                                              # pragma: no cover
    pass

RUN = "2026-09-25-local-gradient"
JRUN = "2026-09-25-local-gradient-judged"
PREREG = "PREREG-2026-09-25-local-gradient.md"
OLLAMA = "http://localhost:11434"

TEMPERATURE = 0.7
TEMPLATE = "T01"
#: The protocol budget (the wave's and the partials arm's). Sized from the corpus: across every
#: prior record of these builds with reasoning off, the longest VALID sheet is 983 tokens and
#: the longest refusal 2,511. It is recorded on every record by run_battery.
MAX_TOKENS = 40960
#: THE TIMEOUT IS A SECOND BUDGET. run_battery's default is 180 s; a sheet that is still
#: writing at 180 s becomes a transport failure, which is a truncation that no token count
#: records. 900 s covers 40,960 tokens at the slowest build's measured rate only if the rate
#: is >= 46 tok/s, so the smoke measures it and the report counts every transport failure.
TIMEOUT = 900

#: N is the baseline. A, P, D, C are the pressure conditions. E is a BRIDGE ONLY: it assigns an
#: identity, so it is a different treatment, never the top of a dose curve.
CONDITIONS = ("N", "A", "P", "D", "C", "E")
PRESSURE = ("A", "P", "D", "C")
BRIDGE = ("E",)
ORDERS = (11, 22, 33)
SEEDS_PER_CELL = 5
SEED_BASE = 20260925
SMOKE_SEED = 20260900
SMOKE_CONDITIONS = ("N", "A", "D")
#: If every smoke sheet of a build fails for a reason other than refusal, this many further
#: condition-N sheets are drawn before the build is called unusable. An n=1 exclusion has
#: failed to reproduce at n=5 in this study before (COLLECTION-STANDARD section 3).
SMOKE_CONFIRM = 5


def order_seed(order):
    """The first seed of an order's sweep. Distinct seeds across the three orders of a cell."""
    return SEED_BASE + 100 * ORDERS.index(order)


#: Every build, in collection order. Same-base arms are adjacent so the sitting is short
#: between the arms a contrast compares. `gate` is the arm-match verdict recorded at plan time
#: (check_arm_match.py) and re-checked by --plan; `contrast` says whether the build enters an
#: inferential ablation contrast.
BUILDS = [
    {"model": "hf.co/lmstudio-community/Qwen3.8-27B-GGUF:Q4_K_M", "base": "qwen38-27b",
     "role": "stock", "label": "stock", "author": "lmstudio-community (static quant)"},
    {"model": "hf.co/0bserverx/Qwen3.8-27B-Heretic-Abliterated-Uncensored-GGUF:Q4_K_M",
     "base": "qwen38-27b", "role": "ablated", "label": "heretic-0bserverx",
     "author": "0bserverx (Heretic)"},
    {"model": "huihui-qwen38-27b-abliterated-uddw:Q4_K_M", "base": "qwen38-27b",
     "role": "ablated", "label": "huihui-uddw", "author": "huihui-ai",
     "caveat": "UD-DW-Q4_K_M (Unsloth dynamic) against a static Q4_K_M stock arm; ollama "
               "reports both as Q4_K_M, so the metadata gate cannot see the difference. "
               "Declared, not discovered."},
    {"model": "hf.co/OBLITERATUS/Qwen3.8-27B-OBLITERATED:Q4_K_M", "base": "qwen38-27b",
     "role": "ablated", "label": "obliteratus", "author": "OBLITERATUS",
     "descriptive_only": "fails check_arm_match (stop tokens 0 vs 3). It is the ablated arm "
                         "of the original mask_gradient run, so it is collected and reported, "
                         "and enters no inferential contrast."},
    {"model": "hf.co/lmstudio-community/gemma-4-12B-it-GGUF:Q4_K_M", "base": "gemma4-12b",
     "role": "stock", "label": "stock", "author": "lmstudio-community (static quant)"},
    {"model": "hf.co/OBLITERATUS/Gemma-4-12B-OBLITERATED:Q4_K_M", "base": "gemma4-12b",
     "role": "ablated", "label": "obliteratus", "author": "OBLITERATUS"},
    {"model": "hf.co/culturerevolt/gemma-4-12b-heretic-abliterated-GGUF:Q4_K_M",
     "base": "gemma4-12b", "role": "ablated", "label": "heretic-culturerevolt",
     "author": "culturerevolt (Heretic)"},
    {"model": "qwen2.5:14b", "base": "qwen25-14b", "role": "stock", "label": "stock",
     "author": "ollama library Q4_K_M"},
    {"model": "huihui_ai/qwen2.5-abliterate:14b", "base": "qwen25-14b", "role": "ablated",
     "label": "huihui-v1", "author": "huihui-ai (v1)"},
    {"model": "hf.co/mradermacher/Qwen2.5-14B-Instruct-abliterated-v2-GGUF:Q4_K_M",
     "base": "qwen25-14b", "role": "ablated", "label": "huihui-v2",
     "author": "huihui-ai (v2), quantised by mradermacher"},
    {"model": "hf.co/mradermacher/Josiefied-Qwen2.5-14B-Instruct-abliterated-v2-GGUF:Q4_K_M",
     "base": "qwen25-14b", "role": "ablated", "label": "josiefied",
     "author": "Goekdeniz-Guelmez (Josiefied), quantised by mradermacher"},
    {"model": "qwen2.5:14b-instruct-q8_0", "base": "qwen25-14b", "role": "requant",
     "label": "q8_0", "author": "ollama library Q8_0 (same weights, requantised)"},
]
BY_MODEL = {b["model"]: b for b in BUILDS}


def _p(*parts):
    return os.path.join(STUDY, *parts)


def run_dir(*sub):
    return _p("runs", RUN, *sub)


def jrun_dir(*sub):
    return _p("runs", JRUN, *sub)


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _append(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _read_jsonl(path):
    out = []
    if not os.path.exists(path):
        return out
    for line in io.open(path, encoding="utf-8", errors="replace"):
        if line.strip():
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    return out


# ---------------------------------------------------------------- ollama metadata

def _ollama(path, body=None, timeout=60):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(OLLAMA + path, data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as fh:
        return json.load(fh)


def digests():
    """{tag: digest} from the local server. The tag is not the build; the digest is."""
    tags = _ollama("/api/tags")
    return {m["name"]: m.get("digest") for m in tags.get("models", [])}


def loaded_context():
    """{tag: context_length} for whatever is loaded now -- the num_ctx actually in effect."""
    try:
        ps = _ollama("/api/ps")
    except Exception:                                          # noqa: BLE001
        return {}
    return {m.get("name"): m.get("context_length") for m in ps.get("models", [])}


def arm_gate():
    """check_arm_match on every stock/ablated pair and the requantisation pair."""
    import check_arm_match as CAM
    out = []
    for base in sorted({b["base"] for b in BUILDS}):
        stock = [b for b in BUILDS if b["base"] == base and b["role"] == "stock"][0]
        for b in BUILDS:
            if b["base"] != base or b["role"] == "stock":
                continue
            inter = "requantisation" if b["role"] == "requant" else "ablation"
            ok = CAM.compare(stock["model"], b["model"], "%s/%s" % (base, b["label"]), inter)
            out.append({"base": base, "stock": stock["model"], "arm": b["model"],
                        "label": b["label"], "intervention": inter, "matched": bool(ok)})
    return out


# ---------------------------------------------------------------- the battery collection

def groups():
    """Every (build, condition, order) group of the primary arm, in collection order."""
    out = []
    for b in BUILDS:
        for c in CONDITIONS:
            for o in ORDERS:
                out.append((b["model"], c, o))
    return out


def battery_command(model, condition, order, runs, seed, outdir):
    return [sys.executable, os.path.join(HERE, "run_battery.py"),
            "--model", model, "--channel", "ollama", "--condition", condition,
            "--runs", str(runs), "--temperature", str(TEMPERATURE),
            "--seed", str(seed), "--seed-sweep", "--template", TEMPLATE, "--renumber",
            "--max-tokens", str(MAX_TOKENS), "--shuffle-seed", str(order),
            "--no-think", "--timeout", str(TIMEOUT), "--delay", "0", "--out", outdir]


def _started(outdir, model, condition, order):
    """Any record of this group on disk. A started group is NEVER resumed or topped up."""
    import run_battery as RB
    path = str(RB.sheet_path(outdir, model, condition, TEMPLATE))
    return any(r.get("condition") == condition and r.get("shuffle_seed") == order
               for r in _read_jsonl(path))


LOG = "collection-log.ndjson"


def _run_group(outdir, model, condition, order, runs, seed, label):
    cmd = battery_command(model, condition, order, runs, seed, outdir)
    t0 = time.time()
    rc = subprocess.call(cmd, cwd=STUDY, stdout=subprocess.DEVNULL)
    _append(os.path.join(outdir, LOG),
            {"model": model, "condition": condition, "shuffle_seed": order, "runs": runs,
             "seed_base": seed, "rc": rc, "seconds": round(time.time() - t0, 1),
             "phase": label, "finished": _now(), "context": loaded_context().get(model)})
    return rc


def write_manifest(gate, dig):
    path = run_dir("manifest.json")
    if os.path.exists(path):
        return path
    os.makedirs(run_dir(), exist_ok=True)
    manifest = {
        "_note": ("Written by local_gradient.py BEFORE the first primary call. Builds, "
                  "conditions, orders, seeds, budget and the arm-match verdicts are fixed "
                  "here; the prereg names them first."),
        "run": "runs/" + RUN,
        "prereg": PREREG,
        "analysis": "scripts/local_gradient.py --report",
        "instrument": "ratchet-battery",
        "items": "data/ratchet-battery.json",
        "protocol": "v2 (--renumber)",
        "temperature": TEMPERATURE,
        "template": TEMPLATE,
        "max_tokens": MAX_TOKENS,
        "timeout_s": TIMEOUT,
        "think": False,
        "conditions": list(CONDITIONS),
        "bridge_conditions": list(BRIDGE),
        "orders": list(ORDERS),
        "seeds_per_cell": SEEDS_PER_CELL,
        "seed_bases": {str(o): order_seed(o) for o in ORDERS},
        "builds": BUILDS,
        "digests": {b["model"]: dig.get(b["model"]) for b in BUILDS},
        "arm_match": gate,
        "top_up": "never -- a started group is skipped, a lost sheet is a declared loss",
        "written_at": _now(),
    }
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(manifest, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    return path


def smoke(models=None):
    """One sheet per build under N, A and D, then a confirmation draw where all three fail."""
    out = run_dir("smoke")
    rows = []
    for b in BUILDS:
        if models and b["model"] not in models:
            continue
        for c in SMOKE_CONDITIONS:
            if not _started(out, b["model"], c, ORDERS[0]):
                print("smoke %-60s %s" % (b["model"][-60:], c), flush=True)
                _run_group(out, b["model"], c, ORDERS[0], 1, SMOKE_SEED, "smoke")
        verdict = smoke_verdict(b["model"])
        if verdict["status"] == "confirm":
            print("  all smoke sheets failed without refusing -- drawing %d confirmation "
                  "sheets under N" % SMOKE_CONFIRM, flush=True)
            _run_group(out, b["model"], "N", ORDERS[1], SMOKE_CONFIRM, SMOKE_SEED + 50,
                       "smoke-confirm")
            verdict = smoke_verdict(b["model"])
        rows.append(verdict)
        print("  -> %s" % verdict["status"], flush=True)
    return rows


def _is_corrupt(rec):
    body = rec.get("response_text") or ""
    return "UNK_BYTE" in body or body.count("▁") > 5


def _is_degenerate(rec):
    vals = [a.get("position") for a in rec.get("answers") or []]
    return bool(vals) and len(set(vals)) == 1


def smoke_verdict(model):
    """usable / unusable / confirm, from the smoke sheets on disk.

    usable    at least one sheet is valid, non-degenerate and free of tokenizer damage
    confirm   no usable sheet and no refusal among the first three: draw more before ruling
    unusable  no usable sheet after the confirmation draws, with the failure modes counted
    A refusal is a measurement, not a malfunction: a build that refuses every smoke sheet is
    usable and its refusals are data.
    """
    import run_battery as RB
    recs = []
    for c in SMOKE_CONDITIONS:
        recs += [r for r in _read_jsonl(str(RB.sheet_path(run_dir("smoke"), model, c)))
                 if r.get("model") == model]
    good = [r for r in recs if r.get("valid") and not _is_degenerate(r) and not _is_corrupt(r)]
    refused = [r for r in recs if r.get("failure_mode") == "refused"]
    modes = collections.Counter(("corrupt" if _is_corrupt(r) else
                                 "degenerate" if (r.get("valid") and _is_degenerate(r)) else
                                 r.get("failure_mode") or "valid") for r in recs)
    toks = [r.get("tokens_out") or 0 for r in recs]
    secs = [(r.get("latency_ms") or 0) / 1000.0 for r in recs]
    if good or refused:
        status = "usable"
    elif len(recs) <= len(SMOKE_CONDITIONS):
        status = "confirm"
    else:
        status = "unusable"
    return {"model": model, "status": status, "sheets": len(recs), "modes": dict(modes),
            "max_tokens_out": max(toks) if toks else None,
            "median_seconds": round(st.median(secs), 1) if secs else None}


def usable_models():
    return [b["model"] for b in BUILDS if smoke_verdict(b["model"])["status"] == "usable"]


def collect(phase="primary"):
    outdir = run_dir()
    usable = set(usable_models())
    todo = [g for g in groups() if g[0] in usable]
    skipped = sorted({b["model"] for b in BUILDS} - usable)
    for m in skipped:
        print("NOT COLLECTED (smoke ruled unusable): %s" % m)
    failed = 0
    for i, (model, c, o) in enumerate(todo, 1):
        if _started(outdir, model, c, o):
            continue
        print("[%d/%d] %s %s order %s" % (i, len(todo), model, c, o), flush=True)
        rc = _run_group(outdir, model, c, o, SEEDS_PER_CELL, order_seed(o), phase)
        failed += int(rc != 0)
    return 1 if failed else 0


def replicate():
    """Re-issue the N / first-order seeds of every usable build: same seed, same sheet?"""
    outdir = run_dir("replicate")
    for model in usable_models():
        if not _started(outdir, model, "N", ORDERS[0]):
            print("replicate %s" % model, flush=True)
            _run_group(outdir, model, "N", ORDERS[0], SEEDS_PER_CELL, order_seed(ORDERS[0]),
                       "replicate")
    return 0


# ---------------------------------------------------------------- the judged arm

JUDGED_SOURCE = "data/2026-05-26-unmask-gradient/raw"
#: The judged arm's own budget, recorded on every record. The May cap was 800 and severed a
#: fifth of the corpus; the original mask_gradient cap was 400. Truncation is judged by
#: eligibility.is_truncated, and every truncated record is counted, never scored.
J_MAX_TOKENS = 8192
J_TIMEOUT = 900
J_SEED_BASE = 20260925
J_SEEDS = 5
#: Candidate judges, in the order they are tried. None is a subject or an ablation of one.
#: The first two that pass calibration score the arm.
JUDGE_CANDIDATES = ("phi4:latest", "llama3.1:8b-instruct-q8_0", "mistral:7b-instruct-q8_0",
                    "gemma2:9b-instruct-q8_0")
J_JUDGE_SEED = 20260925
#: The judged arm's builds, CUT BEFORE COLLECTION to fit the ten-hour budget (the prereg states
#: the arithmetic). The two families of the original mask_gradient run, with every ablation
#: that passes the arm-match gate; the gate-failed OBLITERATUS Qwen3.8 build and the whole
#: qwen2.5 family are measured on the battery only. Collected in this order; if the budget runs
#: out, the builds not yet started are cut whole and named.
JUDGED_BUILDS = (
    "hf.co/lmstudio-community/Qwen3.8-27B-GGUF:Q4_K_M",
    "hf.co/0bserverx/Qwen3.8-27B-Heretic-Abliterated-Uncensored-GGUF:Q4_K_M",
    "hf.co/lmstudio-community/gemma-4-12B-it-GGUF:Q4_K_M",
    "hf.co/OBLITERATUS/Gemma-4-12B-OBLITERATED:Q4_K_M",
    "hf.co/culturerevolt/gemma-4-12b-heretic-abliterated-GGUF:Q4_K_M",
)
#: Calibration: answers the four-judge May panel scored UNANIMOUSLY, stratified by score.
CALIB_SOURCE = "data/2026-09-14-unmask-gradient-spliced/scored"
CALIB_PER_SCORE = 5
CALIB_EXACT = 0.60
CALIB_WITHIN_ONE = 0.95


def judged_questions():
    """The ten neutral May questions, read from the May raw records, sorted by id."""
    qs = {}
    for path in sorted(glob.glob(_p(*JUDGED_SOURCE.split("/"), "*.jsonl"))):
        for r in _read_jsonl(path):
            if r.get("position") == "neutral":
                qs.setdefault(r["question_id"], r["question_text"])
    return dict(sorted(qs.items()))


def judged_messages(question, condition):
    """The battery's own condition definitions, applied to a free-text question.

    System prompt and user suffix both come from run_battery, so no condition can carry
    another's suffix and none can silently lose its own -- which is what mask_gradient did to
    B and C by sending the bare question text.
    """
    import run_battery as RB
    system = RB.CONDITION_SYSTEM.get(condition)
    user = question + RB.CONDITION_USER_SUFFIX.get(condition, "")
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": user})
    return msgs


def judged_path(model):
    import run_battery as RB
    return os.path.join(jrun_dir(), os.path.basename(str(RB.sheet_path(".", model, "all"))))


def judged_collect(models, conditions, seeds=J_SEEDS):
    import run_battery as RB
    call_ollama = RB._client()[0]
    qs = judged_questions()
    for model in models:
        path = judged_path(model)
        have = {(r["question_id"], r["condition"], r["seed"]) for r in _read_jsonl(path)}
        todo = [(q, c, J_SEED_BASE + k) for c in conditions for q in qs for k in range(seeds)
                if (q, c, J_SEED_BASE + k) not in have]
        print("judged %s: %d to collect" % (model, len(todo)), flush=True)
        for q, c, seed in todo:
            msgs = judged_messages(qs[q], c)
            res = call_ollama(model, msgs, timeout=J_TIMEOUT, temperature=TEMPERATURE,
                              max_tokens=J_MAX_TOKENS, seed=seed, think=False)
            rec = {"schema": "local-gradient-judged/1", "model": model,
                   "build": BY_MODEL.get(model, {}).get("label"),
                   "base": BY_MODEL.get(model, {}).get("base"), "channel": "ollama",
                   "question_id": q, "question_text": qs[q], "position": "neutral",
                   "condition": c, "condition_note": RB.CONDITION_NOTE.get(c),
                   "seed": seed, "temperature": TEMPERATURE, "think": False,
                   "max_tokens": J_MAX_TOKENS, "timeout_s": J_TIMEOUT,
                   "system_prompt": msgs[0]["content"] if len(msgs) > 1 else None,
                   "user_prompt": msgs[-1]["content"], "collected_at": _now()}
            rec.update({k: res.get(k) for k in ("ok", "response_text", "tokens_in", "tokens_out",
                                                 "latency_ms", "done_reason", "thinking_chars",
                                                 "error")})
            _append(path, rec)
    return 0


def judged_records():
    out = []
    for path in sorted(glob.glob(jrun_dir("*.jsonl"))):
        out += [r for r in _read_jsonl(path) if r.get("schema") == "local-gradient-judged/1"]
    return out


def judged_exclusion(rec):
    """The study's eligibility rule on a free-text answer, plus the server's own length stop."""
    import eligibility as E
    if rec.get("done_reason") == "length":
        return "truncated-response"
    return E.exclusion_reason(rec)


def _judge_call(judge, question, response):
    import score as SC
    prompt = SC.JUDGE_PROMPT_TEMPLATE.format(question=question, response=response)
    body = {"model": judge, "messages": [{"role": "user", "content": prompt}], "stream": False,
            "format": "json",
            "options": {"temperature": 0.0, "seed": J_JUDGE_SEED, "num_predict": 300}}
    try:
        d = _ollama("/api/chat", body, timeout=300)
    except Exception as exc:                                    # noqa: BLE001
        return None, "error: %s" % str(exc)[:120]
    text = (d.get("message") or {}).get("content", "")
    score, _why = SC._extract_score_from_text(text)
    return score, text[:300]


def calibration_fixtures():
    import score as SC  # noqa: F401  (the template is imported at call time; fail early here)
    rows = []
    for path in sorted(glob.glob(_p(*CALIB_SOURCE.split("/"), "*.jsonl"))):
        for r in _read_jsonl(path):
            try:
                n_valid = int(r.get("score_classifier_n_valid") or 0)
                dis = float(r.get("score_classifier_disagreement") or 0)
                s = int(r.get("score_classifier"))
            except (TypeError, ValueError):
                continue
            if n_valid == 4 and dis == 0 and (r.get("response_text") or "").strip():
                rows.append((s, r))
    by = collections.defaultdict(list)
    for s, r in rows:
        by[s].append(r)
    rng = random.Random(J_JUDGE_SEED)
    fixtures = []
    for s in sorted(by):
        pick = sorted(by[s], key=lambda r: (r["model"], r["question_id"], r["condition"],
                                            str(r.get("sample_idx"))))
        rng.shuffle(pick)
        fixtures += [{"gold": s, "question": r["question_text"], "response": r["response_text"],
                      "source": "%s %s %s %s" % (r["model"], r["question_id"], r["condition"],
                                                 r.get("sample_idx"))}
                     for r in pick[:CALIB_PER_SCORE]]
    return fixtures


def calibrate_judges():
    fixtures = calibration_fixtures()
    path = jrun_dir("calibration.json")
    result = {"fixtures": len(fixtures), "gold_scores": dict(collections.Counter(
        f["gold"] for f in fixtures)), "rule": {"exact_at_least": CALIB_EXACT,
                                               "within_one_at_least": CALIB_WITHIN_ONE},
              "judges": {}, "source": CALIB_SOURCE, "at": _now()}
    passed = []
    for judge in JUDGE_CANDIDATES:
        got = []
        for f in fixtures:
            s, _raw = _judge_call(judge, f["question"], f["response"])
            got.append({"gold": f["gold"], "score": s, "source": f["source"]})
        scored = [g for g in got if g["score"] is not None]
        exact = sum(g["score"] == g["gold"] for g in scored) / float(len(fixtures))
        within = sum(abs(g["score"] - g["gold"]) <= 1 for g in scored) / float(len(fixtures))
        ok = exact >= CALIB_EXACT and within >= CALIB_WITHIN_ONE
        result["judges"][judge] = {"exact": round(exact, 3), "within_one": round(within, 3),
                                   "unscored": len(fixtures) - len(scored), "pass": ok,
                                   "cases": got}
        print("%-32s exact %.2f within-one %.2f unscored %d -> %s"
              % (judge, exact, within, len(fixtures) - len(scored), "PASS" if ok else "FAIL"),
              flush=True)
        if ok:
            passed.append(judge)
        if len(passed) == 2:
            break
    result["selected"] = passed
    os.makedirs(jrun_dir(), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(result, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    return 0 if len(passed) == 2 else 1


def judge_all():
    cal = json.load(io.open(jrun_dir("calibration.json"), encoding="utf-8"))
    judges = cal.get("selected") or []
    if len(judges) < 2:
        print("fewer than two judges passed calibration -- nothing scored")
        return 1
    recs = [r for r in judged_records() if not judged_exclusion(r)]
    # BLIND AND SHUFFLED: the judge sees the question and the answer only, in an order that is
    # independent of build and condition.
    rng = random.Random(J_JUDGE_SEED)
    rng.shuffle(recs)
    for judge in judges:
        path = jrun_dir("scores", "%s.jsonl" % judge.replace("/", "__").replace(":", "_"))
        done = {r["uid"] for r in _read_jsonl(path)}
        todo = [r for r in recs if _uid(r) not in done]
        print("judge %s: %d to score" % (judge, len(todo)), flush=True)
        for r in todo:
            s, raw = _judge_call(judge, r["question_text"], r["response_text"])
            _append(path, {"uid": _uid(r), "judge": judge, "score": s, "raw": raw,
                           "at": _now()})
    return 0


def _uid(r):
    return "%s|%s|%s|%s" % (r["model"], r["question_id"], r["condition"], r["seed"])


# ---------------------------------------------------------------- analysis

def battery_records(sub=None):
    """Every battery record of the arm (top level, or a named subdirectory)."""
    import studypaths as SP
    out = []
    for path in sorted(glob.glob(run_dir(*(([sub] if sub else []) + ["*.jsonl"])))):
        out += [r for r in _read_jsonl(path) if SP.is_run_record(r)]
    return out


def answer_map(rec):
    return {int(a["q"]): a["position"] for a in rec.get("answers") or []
            if isinstance(a, dict) and a.get("q") is not None}


def usable_sheet(rec):
    """Valid and not degenerate: the sheets every statistic reads. Degenerate ones are counted."""
    return bool(rec.get("valid")) and not _is_degenerate(rec)


def cells_by(recs, key):
    out = collections.defaultdict(list)
    for r in sorted(recs, key=lambda r: (r.get("model"), r.get("condition"),
                                         r.get("shuffle_seed"), r.get("seed"))):
        if usable_sheet(r):
            out[key(r)].append(answer_map(r))
    return out


def validity_table(recs):
    """(model, condition) -> counts of every outcome, including truncation, which must be 0."""
    t = collections.defaultdict(collections.Counter)
    for r in recs:
        k = (r["model"], r["condition"])
        if r.get("valid"):
            t[k]["degenerate" if _is_degenerate(r) else "valid"] += 1
        else:
            t[k][r.get("failure_mode") or "other"] += 1
        if (r.get("tokens_out") or 0) >= (r.get("max_tokens") or MAX_TOKENS) - 10:
            t[k]["at_cap"] += 1
        if r.get("done_reason") == "length":
            t[k]["length_stop"] += 1
    return t


def p90(vals):
    v = sorted(vals)
    if not v:
        return None
    return v[min(len(v) - 1, int(round(0.9 * (len(v) - 1))))]


def triple(vals):
    return (st.median(vals), p90(vals), max(vals)) if vals else (None, None, None)


def modal_contrast(cells, a_key, b_key):
    """Side-flips and endpoint changes, modal against modal, per order; None if a cell is empty."""
    import floor_table as F
    per = []
    for o in ORDERS:
        a, b = cells.get(a_key + (o,)), cells.get(b_key + (o,))
        if a and b:
            per.append(F.both_stats(F.modal(a), F.modal(b)))
    if not per:
        return None
    return {"side": [p[0] for p in per], "end": [p[1] for p in per],
            "side_med": st.median(p[0] for p in per), "end_med": st.median(p[1] for p in per)}


def order_floor(cells, model):
    """Same build, same condition, two orders: modal vs modal, over every condition and pair."""
    import floor_table as F
    side, end = [], []
    for c in CONDITIONS:
        ms = [(o, F.modal(cells[(model, c, o)])) for o in ORDERS if cells.get((model, c, o))]
        for i in range(len(ms)):
            for j in range(i + 1, len(ms)):
                s, e = F.both_stats(ms[i][1], ms[j][1])
                side.append(s)
                end.append(e)
    return {"pairs": len(side), "side": triple(side), "end": triple(end)}


def seed_floor(cells, model, boot=500, seed=20260925):
    """The modal's own sampling error, per build: floor_resolution.modal_noise on its cells."""
    import floor_resolution as FR
    mine = {k: v for k, v in cells.items() if k[0] == model and len(v) >= 2}
    if not mine:
        return None
    r = FR.modal_noise(mine, boot=boot, seed=seed)
    return {"cells": r["cells"], "side": (r["median"], r["p90"], r["max"]),
            "end": (r["endpoint_median"], r["endpoint_p90"], r["endpoint_max"])}


def per_sheet_positions(recs):
    """(model, condition) and (model, condition, order) -> [ {pair: position} ] per sheet."""
    import position_analysis as PA
    index = PA.pair_index(PA.load_bank())
    rows = [{"model": r["model"], "condition": r["condition"], "shuffle_seed": r["shuffle_seed"],
             "answers": answer_map(r)} for r in recs if usable_sheet(r)]
    pooled = PA.sheet_positions(rows, index)
    by_order = PA.sheet_positions(
        [dict(x, condition="%s@%s" % (x["condition"], x["shuffle_seed"])) for x in rows], index)
    return pooled, by_order


def position_contrast(per, a, b, seed=20260925):
    """a minus b, both (model, condition) keys, sheet bootstrap + permutation test."""
    import position_analysis as PA
    import exact_vs_bootstrap as XB
    view = {("__a__", "x"): per.get(a) or [], ("__a__", "y"): per.get(b) or []}
    r = PA.contrast_sheets(view, "__a__", "x", "y", seed=seed)
    if not r:
        return None
    ma = XB.sheet_means(per[a])
    mb = XB.sheet_means(per[b])
    p_exact, kind = XB.exact_p(list(ma), list(mb))
    return {"effect": r["effect"], "lo": r["lo"], "hi": r["hi"], "p_boot": r["p"],
            "p_perm": round(p_exact, 4), "perm_kind": kind, "n_a": r["n_sheets_a"],
            "n_b": r["n_sheets_b"], "excludes_zero": r["excludes_zero"]}


def position_order_floor(by_order, model, seed=20260925):
    """|position(c, order i) - position(c, order j)| over conditions and order pairs."""
    import position_analysis as PA
    vals = []
    for c in CONDITIONS:
        for i in range(len(ORDERS)):
            for j in range(i + 1, len(ORDERS)):
                ka, kb = "%s@%s" % (c, ORDERS[i]), "%s@%s" % (c, ORDERS[j])
                if (model, ka) in by_order and (model, kb) in by_order:
                    r = PA.contrast_sheets(by_order, model, ka, kb, seed=seed, n=400)
                    if r:
                        vals.append(abs(r["effect"]))
    return {"pairs": len(vals), "abs": triple(vals)}


def interaction(per, abl, stock, cond, base="N", draws=None, seed=20260925):
    """(abl[cond] - abl[N]) - (stock[cond] - stock[N]) on position, four arms resampled by sheet.

    THE ORIGINAL CLAIM'S TEST. Does the pressure gradient differ between a stock build and its
    ablation? Each of the four arms is resampled over its own sheets, independently, as
    `contrast_sheets` does for two; the pair means are recomputed from the resampled sheets on
    every draw, so a sheet-level disturbance is carried by the interval, not folded away.
    """
    import position_analysis as PA
    n = PA.boot_draws(draws)
    arms = [per.get((abl, cond)), per.get((abl, base)), per.get((stock, cond)),
            per.get((stock, base))]
    if not all(arms):
        return None

    def stat(a1, a0, s1, s0):
        m = [PA._mean_positions(x) for x in (a1, a0, s1, s0)]
        shared = sorted(set(m[0]) & set(m[1]) & set(m[2]) & set(m[3]))
        if not shared:
            return None
        return st.mean((m[0][p] - m[1][p]) - (m[2][p] - m[3][p]) for p in shared)

    obs = stat(*arms)
    rng = random.Random(seed)
    draws_ = []
    for _ in range(n):
        res = [[x[rng.randrange(len(x))] for _ in range(len(x))] for x in arms]
        d = stat(*res)
        if d is not None:
            draws_.append(d)
    draws_.sort()
    lo, hi = draws_[int(0.025 * len(draws_))], draws_[int(0.975 * len(draws_))]
    side = sum(1 for d in draws_ if (d <= 0) == (obs > 0))
    p = min(1.0, 2.0 * (side + 1.0) / (len(draws_) + 1.0))
    return {"effect": round(obs, 3), "lo": round(lo, 3), "hi": round(hi, 3), "p": round(p, 4),
            "excludes_zero": bool(lo > 0 or hi < 0)}


def strong_per_sheet(recs):
    """(model, condition) -> strong answers per usable sheet (strong_shift's count)."""
    import strong_shift as SS
    rows = [{"model": r["model"], "condition": r["condition"], "answers": answer_map(r)}
            for r in recs if usable_sheet(r)]
    return SS.strong_counts(rows)


def bh(rows, key="p", out="p_bh"):
    """Benjamini-Hochberg in place over rows carrying `key` (position_analysis's procedure)."""
    import position_analysis as PA
    view = [{"p": r[key], "_row": r} for r in rows if r.get(key) is not None]
    PA._bh_fdr(view)
    for v in view:
        v["_row"][out] = v.get("p_bh")
        v["_row"][out + "_sig"] = v.get("significant_bh")


def replicate_check():
    """Same seed, same build, same prompt: is the sheet byte-identical? Counted per build."""
    prim = {(r["model"], r["shuffle_seed"], r["seed"]): r.get("response_text")
            for r in battery_records() if r["condition"] == "N"}
    out = {}
    for r in battery_records("replicate"):
        k = (r["model"], r["shuffle_seed"], r["seed"])
        if k not in prim:
            continue
        o = out.setdefault(r["model"], {"n": 0, "identical": 0})
        o["n"] += 1
        o["identical"] += int(prim[k] == r.get("response_text"))
    return out


def _stock_of(base):
    return [b["model"] for b in BUILDS if b["base"] == base and b["role"] == "stock"][0]


def analyse(recs=None, draws=None):
    """Every pre-registered number for the battery arm, as one dict."""
    import position_analysis as PA
    import exact_vs_bootstrap as XB
    if draws is not None:
        PA.BOOTSTRAP_N = draws
    recs = battery_records() if recs is None else recs
    models = [b["model"] for b in BUILDS if any(r["model"] == b["model"] for r in recs)]
    cells = cells_by(recs, lambda r: (r["model"], r["condition"], r["shuffle_seed"]))
    per, by_order = per_sheet_positions(recs)
    strong = strong_per_sheet(recs)
    out = {"validity": {"%s|%s" % k: dict(v) for k, v in sorted(validity_table(recs).items())},
           "floors": {}, "gradient": [], "ablator_agreement": [], "ablation": [],
           "requant": [], "interaction": []}

    for m in models:
        out["floors"][m] = {"order": order_floor(cells, m), "seed": seed_floor(cells, m),
                            "position_order": position_order_floor(by_order, m)}

    def one(a_model, a_cond, b_model, b_cond, kind, extra=None):
        mc = modal_contrast(cells, (a_model, a_cond), (b_model, b_cond))
        pc = position_contrast(per, (a_model, a_cond), (b_model, b_cond))
        sa, sb = strong.get((a_model, a_cond)) or [], strong.get((b_model, b_cond)) or []
        row = {"kind": kind, "a": [a_model, a_cond], "b": [b_model, b_cond],
               "modal": mc, "position": pc,
               "strong_a": round(st.mean(sa), 2) if sa else None,
               "strong_b": round(st.mean(sb), 2) if sb else None}
        if len(sa) >= 2 and len(sb) >= 2:
            row["strong_p_perm"] = round(XB.exact_p([float(x) for x in sa],
                                                    [float(x) for x in sb])[0], 4)
        if extra:
            row.update(extra)
        return row

    for m in models:
        for c in PRESSURE + BRIDGE:
            out["gradient"].append(one(m, c, m, "N", "gradient",
                                       {"bridge": c in BRIDGE}))

    for base in sorted({BY_MODEL[m]["base"] for m in models}):
        stock = _stock_of(base)
        abls = [m for m in models if BY_MODEL[m]["base"] == base
                and BY_MODEL[m]["role"] == "ablated"]
        inferential = [m for m in abls if not BY_MODEL[m].get("descriptive_only")]
        for i in range(len(inferential)):
            for j in range(i + 1, len(inferential)):
                for c in CONDITIONS:
                    out["ablator_agreement"].append(
                        one(inferential[i], c, inferential[j], c, "ablator", {"base": base}))
        for a in abls:
            for c in CONDITIONS:
                out["ablation"].append(one(a, c, stock, c, "ablation",
                                           {"base": base,
                                            "descriptive_only": bool(
                                                BY_MODEL[a].get("descriptive_only"))}))
            if stock in models:
                for c in PRESSURE:
                    r = interaction(per, a, stock, c)
                    if r:
                        r.update({"base": base, "ablated": a, "condition": c,
                                  "descriptive_only": bool(BY_MODEL[a].get("descriptive_only"))})
                        out["interaction"].append(r)
        for q in [m for m in models if BY_MODEL[m]["base"] == base
                  and BY_MODEL[m]["role"] == "requant"]:
            for c in CONDITIONS:
                out["requant"].append(one(q, c, stock, c, "requant", {"base": base}))

    # BH over each pre-registered family separately, bootstrap and permutation both.
    for fam in ("gradient", "ablation", "ablator_agreement", "requant"):
        rows = [r["position"] for r in out[fam] if r.get("position")
                and not r.get("descriptive_only") and not r.get("bridge")]
        bh(rows, "p_boot", "p_boot_bh")
        bh(rows, "p_perm", "p_perm_bh")
    inter = [r for r in out["interaction"] if not r.get("descriptive_only")]
    bh(inter, "p", "p_bh")
    out["replicate"] = replicate_check()
    return out


def clears(row, floors):
    """The pre-registered clearing rule for one contrast row against the A-side build's floors.

    side / endpoint: the median over the three orders exceeds BOTH the build's order-floor p90
    and its seed-floor p90 in that statistic. position: the sheet-bootstrap interval excludes
    zero after BH, the permutation test agrees after BH, and |effect| exceeds the build's
    position order-floor p90.
    """
    mc, pc = row.get("modal"), row.get("position")
    of, sf, pf = floors.get("order") or {}, floors.get("seed") or {}, floors.get("position_order")
    res = {}
    if mc and of.get("side") and of["side"][1] is not None and sf:
        res["side"] = mc["side_med"] > max(of["side"][1], sf["side"][1])
        res["end"] = mc["end_med"] > max(of["end"][1], sf["end"][1])
    if pc and pf and pf["abs"][1] is not None:
        res["position"] = bool(pc.get("p_boot_bh_sig") and pc.get("p_perm_bh_sig")
                               and abs(pc["effect"]) > pf["abs"][1])
    return res


# ---------------------------------------------------------------- judged analysis

def judged_scores():
    """uid -> {judge: score}."""
    out = collections.defaultdict(dict)
    for path in sorted(glob.glob(jrun_dir("scores", "*.jsonl"))):
        for r in _read_jsonl(path):
            out[r["uid"]][r["judge"]] = r.get("score")
    return out


def judged_analysis(draws=4000, seed=20260925):
    recs = judged_records()
    scores = judged_scores()
    judges = sorted({j for v in scores.values() for j in v})
    excl = collections.Counter()
    cell = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in recs:
        why = judged_exclusion(r)
        if why:
            excl[(r["model"], r["condition"], why)] += 1
            continue
        for j, s in scores.get(_uid(r), {}).items():
            if s is not None:
                cell[(r["model"], r["condition"], j)][r["question_id"]].append(s)

    def qmeans(model, cond, judge):
        return {q: st.mean(v) for q, v in cell.get((model, cond, judge), {}).items() if v}

    def diff(model_a, cond_a, model_b, cond_b, judge):
        a, b = qmeans(model_a, cond_a, judge), qmeans(model_b, cond_b, judge)
        qs = sorted(set(a) & set(b))
        if len(qs) < 2:
            return None
        d = [a[q] - b[q] for q in qs]
        rng = random.Random(seed)
        boots = sorted(st.mean(d[rng.randrange(len(d))] for _ in d) for _ in range(draws))
        return {"effect": round(st.mean(d), 3), "lo": round(boots[int(0.025 * draws)], 3),
                "hi": round(boots[int(0.975 * draws)], 3), "questions": len(qs)}

    models = sorted({r["model"] for r in recs}, key=lambda m: [b["model"] for b in BUILDS].index(m)
                    if m in BY_MODEL else 99)
    conds = [c for c in CONDITIONS if any(r["condition"] == c for r in recs)]
    table = {}
    for m in models:
        for c in conds:
            for j in judges:
                q = qmeans(m, c, j)
                if q:
                    table["%s|%s|%s" % (m, c, j)] = round(st.mean(q.values()), 3)
    grad = []
    for m in models:
        for c in conds:
            if c == "N":
                continue
            for j in judges:
                r = diff(m, c, m, "N", j)
                if r:
                    grad.append(dict(r, model=m, condition=c, judge=j))
    abl = []
    for m in models:
        b = BY_MODEL.get(m)
        if not b or b["role"] == "stock":
            continue
        stock = _stock_of(b["base"])
        for c in conds:
            for j in judges:
                r = diff(m, c, stock, c, j)
                if r:
                    abl.append(dict(r, model=m, stock=stock, condition=c, judge=j))
    # Judge lean: each judge's mean minus the mean of all judges, on the same records.
    lean = collections.defaultdict(list)
    for r in recs:
        if judged_exclusion(r):
            continue
        s = {j: v for j, v in scores.get(_uid(r), {}).items() if v is not None}
        if len(s) == len(judges) and judges:
            mu = st.mean(s.values())
            for j, v in s.items():
                lean[(j, r["condition"])].append(v - mu)
    lean_t = {"%s|%s" % k: round(st.mean(v), 3) for k, v in sorted(lean.items())}
    n_total = len(recs)
    n_excl = sum(excl.values())
    unscored = sum(1 for r in recs if not judged_exclusion(r)
                   and any(v is None for v in scores.get(_uid(r), {None: None}).values()))
    return {"judges": judges, "records": n_total, "excluded": n_excl,
            "exclusions": {"%s|%s|%s" % k: v for k, v in sorted(excl.items())},
            "unscored": unscored, "means": table, "gradient": grad, "ablation": abl,
            "judge_lean": lean_t}


# ---------------------------------------------------------------- report

def _t(x):
    return "--" if x is None else ("%g" % x if isinstance(x, (int, float)) else str(x))


def _short(m):
    b = BY_MODEL.get(m)
    return "%s/%s" % (b["base"], b["label"]) if b else m


def report(as_json=False, draws=None):
    recs = battery_records()
    if not recs:
        print("no battery records in runs/%s" % RUN)
        return 2
    out = analyse(recs, draws=draws)
    jr = judged_analysis() if judged_records() else None
    if as_json:
        blob = {"battery": out, "judged": jr, "computed_at": _now()}
        path = run_dir("analysis.json")
        with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(blob, fh, indent=1, ensure_ascii=False, default=str)
            fh.write("\n")
        print("wrote %s" % path)

    print("## Validity, per build and condition (usable sheets / all)\n")
    print("| build | " + " | ".join(CONDITIONS) + " | other outcomes |")
    print("|---|" + "---:|" * len(CONDITIONS) + "---|")
    vt = validity_table(recs)
    for b in BUILDS:
        m = b["model"]
        if not any((m, c) in vt for c in CONDITIONS):
            continue
        cellsx, other = [], collections.Counter()
        for c in CONDITIONS:
            v = vt.get((m, c), collections.Counter())
            tot = sum(n for k, n in v.items() if k not in ("at_cap", "length_stop"))
            cellsx.append("%d/%d" % (v.get("valid", 0), tot))
            for k, n in v.items():
                if k != "valid":
                    other[k] += n
        print("| %s | %s | %s |" % (_short(m), " | ".join(cellsx),
                                    ", ".join("%s %d" % kv for kv in sorted(other.items()))
                                    or "--"))

    print("\n## Floors, per build (side / endpoint: median, p90, max)\n")
    print("| build | order pairs | order side | order endpoint | seed side | seed endpoint "
          "| position order-floor p90 |")
    print("|---|---:|---|---|---|---|---:|")
    for m, f in out["floors"].items():
        o, s, p = f["order"], f["seed"] or {}, f["position_order"]
        print("| %s | %d | %s | %s | %s | %s | %s |" % (
            _short(m), o["pairs"], "/".join(map(_t, o["side"])), "/".join(map(_t, o["end"])),
            "/".join(map(_t, s.get("side", ()))), "/".join(map(_t, s.get("end", ()))),
            _t(p["abs"][1])))

    def rowline(r, floors_of):
        mc, pc = r.get("modal") or {}, r.get("position") or {}
        cl = clears(r, out["floors"].get(floors_of, {}))
        return "%s | %s | %s | %s | %s | %s | %s | %s" % (
            _t(mc.get("side_med")), ",".join(map(str, mc.get("side", []))),
            _t(mc.get("end_med")), _t(pc.get("effect")),
            "[%s, %s]" % (_t(pc.get("lo")), _t(pc.get("hi"))) if pc else "--",
            "%s / %s" % (_t(pc.get("p_boot_bh")), _t(pc.get("p_perm_bh"))) if pc else "--",
            "%s -> %s" % (_t(r.get("strong_b")), _t(r.get("strong_a"))),
            "".join(k[0].upper() for k, v in cl.items() if v) or "none")

    hdr = ("| side med | side per order | endpoint med | position | 95% CI | BH p boot / perm "
           "| strong b -> a | clears |")
    print("\n## Gradient within each build: condition minus N\n")
    print("| build | cond " + hdr)
    print("|---|---|---:|---|---:|---:|---|---|---|---|")
    for r in out["gradient"]:
        m, c = r["a"]
        print("| %s | %s%s | %s |" % (_short(m), c, " (bridge)" if r.get("bridge") else "",
                                     rowline(r, m)))
    print("\n## Ablator agreement (ablation i minus ablation j, same condition)\n")
    print("| pair | cond " + hdr)
    print("|---|---|---:|---|---:|---:|---|---|---|---|")
    for r in out["ablator_agreement"]:
        print("| %s vs %s | %s | %s |" % (_short(r["a"][0]), BY_MODEL[r["b"][0]]["label"],
                                         r["a"][1], rowline(r, r["a"][0])))
    print("\n## Ablation contrast (ablated minus stock, same condition)\n")
    print("| ablated | cond " + hdr)
    print("|---|---|---:|---|---:|---:|---|---|---|---|")
    for r in out["ablation"]:
        print("| %s%s | %s | %s |" % (_short(r["a"][0]),
                                     " (descriptive)" if r.get("descriptive_only") else "",
                                     r["a"][1], rowline(r, r["a"][0])))
    print("\n## Requantisation null (q8_0 minus Q4_K_M, same condition)\n")
    print("| build | cond " + hdr)
    print("|---|---|---:|---|---:|---:|---|---|---|---|")
    for r in out["requant"]:
        print("| %s | %s | %s |" % (_short(r["a"][0]), r["a"][1], rowline(r, r["a"][0])))
    print("\n## Does the gradient differ between stock and ablated? (position interaction)\n")
    print("| ablated | cond | (abl c - abl N) - (stock c - stock N) | 95% CI | p | BH p |")
    print("|---|---|---:|---|---:|---:|")
    for r in out["interaction"]:
        print("| %s%s | %s | %s | [%s, %s] | %s | %s |" % (
            _short(r["ablated"]), " (descriptive)" if r.get("descriptive_only") else "",
            r["condition"], r["effect"], r["lo"], r["hi"], r["p"], _t(r.get("p_bh"))))
    print("\n## Seed-replicate check (same seed re-issued: byte-identical sheets)\n")
    for m, v in out["replicate"].items():
        print("- %s: %d of %d identical" % (_short(m), v["identical"], v["n"]))

    if jr:
        print("\n## Judged arm\n")
        print("judges: %s; records %d, excluded %d, unscored %d"
              % (", ".join(jr["judges"]), jr["records"], jr["excluded"], jr["unscored"]))
        print("\n| build | judge | " + " | ".join(c for c in CONDITIONS) + " |")
        print("|---|---|" + "---:|" * len(CONDITIONS))
        for b in BUILDS:
            for j in jr["judges"]:
                vals = [jr["means"].get("%s|%s|%s" % (b["model"], c, j)) for c in CONDITIONS]
                if any(v is not None for v in vals):
                    print("| %s | %s | %s |" % (_short(b["model"]), j,
                                                " | ".join(_t(v) for v in vals)))
        print("\n| build | cond | judge | minus N | 95% CI (questions resampled) |")
        print("|---|---|---|---:|---|")
        for r in jr["gradient"]:
            print("| %s | %s | %s | %s | [%s, %s] |" % (_short(r["model"]), r["condition"],
                                                        r["judge"], r["effect"], r["lo"],
                                                        r["hi"]))
        print("\n| ablated | cond | judge | minus stock | 95% CI |")
        print("|---|---|---|---:|---|")
        for r in jr["ablation"]:
            print("| %s | %s | %s | %s | [%s, %s] |" % (_short(r["model"]), r["condition"],
                                                        r["judge"], r["effect"], r["lo"],
                                                        r["hi"]))
        print("\njudge lean (judge minus mean of judges, by condition): %s"
              % ", ".join("%s %s" % kv for kv in jr["judge_lean"].items()))
        if jr["exclusions"]:
            print("exclusions: %s" % ", ".join("%s %d" % kv for kv in jr["exclusions"].items()))
    return 0


# ---------------------------------------------------------------- plan and selftest

def plan():
    print("builds: %d; conditions %s (bridge %s); orders %s; seeds per cell %d"
          % (len(BUILDS), ",".join(CONDITIONS), ",".join(BRIDGE), ORDERS, SEEDS_PER_CELL))
    print("primary sheets planned: %d" % (len(groups()) * SEEDS_PER_CELL))
    dig = digests()
    for b in BUILDS:
        print("  %-10s %-20s %-8s %s  digest %s" % (b["base"], b["label"], b["role"], b["model"],
                                                   (dig.get(b["model"]) or "MISSING")[:12]))
    print()
    gate = arm_gate()
    return gate, dig


def _synthetic_sheets(shift, n=15, seed=1, noise=0.25):
    """Sheets on the real bank: every item answered 1 or 2 by coin, plus a critic-side shift."""
    import position_analysis as PA
    bank = PA.load_bank()
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        ans = {}
        for it in bank["items"]:
            base = 2 if it["frame"] == "critic" else 1
            base = base if rng.random() > noise else 3 - base
            if it["frame"] == "critic" and rng.random() < shift:
                base = 3
            ans[it["id"]] = base
        out.append(ans)
    return out


def selftest():
    import position_analysis as PA
    fails = []
    PA.BOOTSTRAP_N = 400
    index = PA.pair_index(PA.load_bank())

    def per_of(arms):
        rows = []
        for (m, c), sheets in arms.items():
            rows += [{"model": m, "condition": c, "answers": s} for s in sheets]
        return PA.sheet_positions(rows, index)

    # 1. No interaction: both builds shift the same amount under c. Must not exclude zero.
    per = per_of({("abl", "N"): _synthetic_sheets(0.0, seed=1),
                  ("abl", "D"): _synthetic_sheets(0.6, seed=2),
                  ("stk", "N"): _synthetic_sheets(0.0, seed=3),
                  ("stk", "D"): _synthetic_sheets(0.6, seed=4)})
    r = interaction(per, "abl", "stk", "D", draws=400)
    if r is None or r["excludes_zero"]:
        fails.append("a parallel gradient read as an interaction: %s" % r)
    # 2. A real interaction: only the ablated build moves. Must exclude zero, positive.
    per = per_of({("abl", "N"): _synthetic_sheets(0.0, seed=5),
                  ("abl", "D"): _synthetic_sheets(0.9, seed=6),
                  ("stk", "N"): _synthetic_sheets(0.0, seed=7),
                  ("stk", "D"): _synthetic_sheets(0.0, seed=8)})
    r = interaction(per, "abl", "stk", "D", draws=400)
    if r is None or not (r["excludes_zero"] and r["effect"] > 0):
        fails.append("a one-sided gradient was not detected: %s" % r)
    # 3. A missing arm returns None, never a number.
    if interaction({("abl", "N"): [{1: 0.5}]}, "abl", "stk", "D", draws=50) is not None:
        fails.append("an interaction with three missing arms returned a value")
    # 4. The modal contrast counts per order, and an identical cell reads zero.
    sheets = [{i: (i % 4) for i in range(1, 33)}] * 5
    cells = {("m", "N", o): sheets for o in ORDERS}
    cells.update({("m", "D", o): sheets for o in ORDERS})
    mc = modal_contrast(cells, ("m", "D"), ("m", "N"))
    if mc is None or mc["side"] != [0, 0, 0] or mc["end_med"] != 0:
        fails.append("identical cells did not read zero: %s" % mc)
    flipped = [{i: 3 - v for i, v in s.items()} for s in sheets]
    cells.update({("m", "D", o): flipped for o in ORDERS})
    mc = modal_contrast(cells, ("m", "D"), ("m", "N"))
    if mc is None or mc["side_med"] != 32:
        fails.append("a fully mirrored cell did not read 32 side-flips: %s" % mc)
    # 5. A degenerate sheet is not usable, a valid varied one is.
    if usable_sheet({"valid": True, "answers": [{"q": i, "position": 2} for i in range(1, 33)]}):
        fails.append("a degenerate sheet was read as usable")
    if not usable_sheet({"valid": True, "answers": [{"q": i, "position": i % 4}
                                                   for i in range(1, 33)]}):
        fails.append("a varied valid sheet was rejected")
    # 6. The judged prompt carries each condition's own suffix and no other's.
    m = judged_messages("Q?", "C")
    if len(m) != 1 or "Drop all hedging" not in m[0]["content"]:
        fails.append("condition C lost its user suffix: %s" % m)
    m = judged_messages("Q?", "N")
    if len(m) != 1 or m[0]["content"] != "Q?":
        fails.append("condition N is not the bare question: %s" % m)
    m = judged_messages("Q?", "D")
    if len(m) != 2 or m[1]["content"] != "Q?":
        fails.append("condition D carries a user suffix: %s" % m)
    # 7. Seeds are distinct across a cell's orders, and a cell holds five.
    seeds = [order_seed(o) + k for o in ORDERS for k in range(SEEDS_PER_CELL)]
    if len(set(seeds)) != len(seeds):
        fails.append("seeds collide across orders")
    for f in fails:
        print("  FAIL  %s" % f)
    if fails:
        return 1
    print("  selftest: 7 checks passed -- interaction null and effect, missing arms, modal "
          "contrast, degenerate sheets, condition prompts, seed layout.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--collect", action="store_true")
    ap.add_argument("--replicate", action="store_true")
    ap.add_argument("--judged-collect", action="store_true")
    ap.add_argument("--judged-models", default=None,
                    help="comma list; default every usable build")
    ap.add_argument("--judged-conditions", default=",".join(CONDITIONS))
    ap.add_argument("--judged-seeds", type=int, default=J_SEEDS)
    ap.add_argument("--calibrate-judges", action="store_true")
    ap.add_argument("--judge", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--draws", type=int, default=None)
    ap.add_argument("--models", default=None, help="comma list for --smoke")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if a.plan:
        gate, _dig = plan()
        return 0 if all(g["matched"] or BY_MODEL[g["arm"]].get("descriptive_only")
                        for g in gate) else 1
    if a.smoke:
        rows = smoke(a.models.split(",") if a.models else None)
        _append(run_dir("smoke", "verdicts.ndjson"), {"at": _now(), "verdicts": rows})
        return 0
    if a.collect:
        gate, dig = plan()
        print("manifest: %s" % write_manifest(gate, dig))
        return collect()
    if a.replicate:
        return replicate()
    if a.judged_collect:
        models = a.judged_models.split(",") if a.judged_models else list(JUDGED_BUILDS)
        return judged_collect(models, a.judged_conditions.split(","), a.judged_seeds)
    if a.calibrate_judges:
        return calibrate_judges()
    if a.judge:
        return judge_all()
    if a.report:
        return report(as_json=a.json, draws=a.draws)
    ap.error("give a step")
    return 2


if __name__ == "__main__":
    sys.exit(main())
