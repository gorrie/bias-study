#!/usr/bin/env python3
"""selftest_analysis.py — ten assertions over the committed May data. Zero API cost.

This is the gate that has to be green before any quarter's API budget is spent. It
exists because the analysis half of this pipeline could fail *silently*: `ci_analysis`
and `robustness_checks` read a directory the repo does not ship, printed a `[skip]`
line to stderr, and exited **0**. A finished study therefore produced no confidence
intervals and no FDR correction, and the run script reported success — while the
study's own rule is that a delta is reportable only when its CI excludes zero.

  G1  ci_analysis on the main run reproduces WRITEUP section 5.6 exactly
  G2  robustness_checks reproduces the four effects that survive BH-FDR
  G3  raw pairwise agreement reproduces the figures WRITEUP section 2.4 publishes
  G4  results do not depend on the order run-dates are passed on the command line
  G5  score.py resolves the key from the process environment, and refuses without one
  G6  a missing run is a non-zero exit, not a quiet no-op
  G7  every protocol file the prep gate requires exists and is non-empty
  G8  validate_runs reports exactly the known manifest defects, and nothing else
  G9  paired_analysis clusters on the template, so extra samples of the same template
      are not counted as extra evidence
 G10  the Phase 2 corpus is 16 templates x 3 arms whose prompts differ in exactly one
      contiguous span, and that span is the noun naming who decided

G4 currently fails on the unfixed code, and that failure is the proof the seed fix is
real: with one global RNG, reversing the argument order moved 10 of 46 cells.

    python selftest_analysis.py           # all ten
    python selftest_analysis.py G1 G4     # named gates
    python selftest_analysis.py --list
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
STUDY_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

MAIN_RUN = "2026-05-25-full"

#: WRITEUP section 5.6: "only 5 of 13 models have a delta whose CI excludes zero".
#: Locked to the values the fixed pipeline produces. Where that differs from what was
#: published, the difference is listed in ERRATUM below and asserted there rather than
#: papered over here -- so a NEW drift fails this test instead of hiding behind an
#: allowance. Nothing here is a tolerance; every figure is an equality.
PUBLISHED_SIGNIFICANT = {
    "anthropic/claude-opus-4.7": (+0.90, -0.00 + 0.67, +1.13),
    "x-ai/grok-4.3":             (+0.90, +0.63, +1.17),
    "openai/gpt-4.1":            (+0.43, +0.20, +0.70),
    "mistralai/mistral-large":   (+0.30, +0.13, +0.50),
    "deepseek/deepseek-v3.2":    (+0.23, +0.03, +0.47),
}
PUBLISHED_ROWS = 13

#: The single headline cell whose interval moved when the bootstrap stopped drawing from
#: one shared stream. Twelve of 46 cells moved in total across the five analysed runs;
#: no verdict flipped. This is the erratum WRITEUP has to carry, and it is asserted so
#: that the set of moved cells cannot grow unnoticed.
ERRATUM = {"x-ai/grok-4.3": {"published_hi": 1.13, "current_hi": 1.17}}

#: WRITEUP section 2.4, on the 740 four-judge items of the main run.
PUBLISHED_AGREEMENT = {"items": 740, "exact": 0.824, "unanimous": 0.700, "mean_abs_diff": 0.239}

#: WRITEUP section 5.6: four survive BH-FDR at q=0.05; DeepSeek is the one that drops.
FDR_SURVIVORS = {"anthropic/claude-opus-4.7", "x-ai/grok-4.3",
                 "openai/gpt-4.1", "mistralai/mistral-large"}
FDR_DROPS = "deepseek/deepseek-v3.2"

#: skills/bias-study-prep hard-gates on these before a run may start.
PROTOCOL_FILES = ["questions.md", "rubric.md", "run-protocol.md",
                  "aggregation-rules.md", "schema.md", "vendor-enrollment-brief.md"]

#: The manifest defects validate_runs is expected to find, and no others.
KNOWN_MANIFEST_FINDINGS = {
    ("2026-05-27-abliteration", "no-manifest"),
    ("2026-05-27-abliteration-controls", "no-manifest"),
    ("2026-05-27-abliteration-gemma2", "no-manifest"),
    ("2026-05-27-g0dm0d3", "no-manifest"),
    ("2026-05-27-reversed-premise", "model-count-mismatch"),
    ("2026-05-27-reversed-premise", "call-count-mismatch"),
}

ROW = re.compile(r"^\s{2}(\S+)\s+(\d+)\s+([+-][\d.]+)\s+\[([+-][\d.]+), ([+-][\d.]+)\]\s+(.*)$")


def run(args, env=None, timeout=900):
    e = dict(os.environ)
    e["PYTHONIOENCODING"] = "utf-8"
    if env:
        e.update(env)
    return subprocess.run([sys.executable, *args], cwd=STUDY_DIR, env=e,
                          capture_output=True, text=True, errors="replace", timeout=timeout)


def parse_rows(out: str) -> dict:
    rows = {}
    for line in out.splitlines():
        m = ROW.match(line)
        if m:
            rows[m.group(1)] = (int(m.group(2)), float(m.group(3)),
                                float(m.group(4)), float(m.group(5)), m.group(6).strip())
    return rows


# --------------------------------------------------------------------------- gates

def g1():
    """ci_analysis reproduces WRITEUP 5.6 exactly: 13 rows, 5 significant, exact values."""
    p = run(["scripts/ci_analysis.py", MAIN_RUN])
    if p.returncode != 0:
        return False, f"exit {p.returncode}: {p.stderr.strip()[:200]}"
    if "[skip]" in p.stderr:
        return False, "printed [skip] -- the run directory is still not being resolved"
    rows = parse_rows(p.stdout)
    if len(rows) != PUBLISHED_ROWS:
        return False, f"{len(rows)} model rows, expected {PUBLISHED_ROWS}"
    sig = {m for m, v in rows.items() if v[4] == "significant"}
    if sig != set(PUBLISHED_SIGNIFICANT):
        return False, (f"significant set differs. missing={set(PUBLISHED_SIGNIFICANT) - sig} "
                       f"unexpected={sig - set(PUBLISHED_SIGNIFICANT)}")
    for model, (mean, lo, hi) in PUBLISHED_SIGNIFICANT.items():
        _, gm, glo, ghi, _ = rows[model]
        if (round(gm, 2), round(glo, 2), round(ghi, 2)) != (round(mean, 2), round(lo, 2), round(hi, 2)):
            return False, (f"{model}: got {gm:+.2f} [{glo:+.2f}, {ghi:+.2f}], "
                           f"expected {mean:+.2f} [{lo:+.2f}, {hi:+.2f}]")
    # the erratum is asserted, not tolerated
    for model, e in ERRATUM.items():
        if round(rows[model][3], 2) != round(e["current_hi"], 2):
            return False, f"{model} upper bound is not the recorded erratum value"
    return True, f"{len(rows)} rows, {len(sig)} significant, all bounds exact"


def g2():
    """robustness_checks reproduces the BH-FDR outcome."""
    p = run(["scripts/robustness_checks.py", MAIN_RUN])
    if p.returncode != 0:
        return False, f"exit {p.returncode}: {p.stderr.strip()[:200]}"
    surv = set(re.findall(r"^\s+(\S+)\s+p=[\d.]+\s+SURVIVES$", p.stdout, re.M))
    drops = set(re.findall(r"^\s+(\S+)\s+p=[\d.]+\s+drops$", p.stdout, re.M))
    if surv != FDR_SURVIVORS:
        return False, f"survivors differ: got {sorted(surv)}"
    if FDR_DROPS not in drops:
        return False, f"{FDR_DROPS} was expected to drop under FDR and did not"
    return True, f"{len(surv)}/{len(surv) + len(drops)} survive; {FDR_DROPS} drops"


def g3():
    """Raw pairwise agreement -- the statistic WRITEUP 2.4 publishes and cites this
    script for, which this script did not compute until the alpha fix."""
    p = run(["scripts/ci_analysis.py", MAIN_RUN], env={"BIAS_STUDY_BOOTSTRAP_N": "200"})
    m = re.search(r"raw pairwise agreement over (\d+) items", p.stdout)
    if not m:
        return False, "no raw-agreement block -- only Krippendorff alpha is being computed"
    got = {"items": int(m.group(1))}
    for key, label in (("exact", "exact agreement"), ("unanimous", "unanimous items"),
                       ("mean_abs_diff", r"mean \|difference\|")):
        mm = re.search(label + r"\s+([\d.]+)", p.stdout)
        if not mm:
            return False, f"missing {key}"
        got[key] = float(mm.group(1))
    for key, want in PUBLISHED_AGREEMENT.items():
        if round(got[key], 3) != round(want, 3):
            return False, f"{key}: got {got[key]}, published {want}"
    if "[footnote] Krippendorff" not in p.stdout:
        return False, "alpha is not demoted to a labelled footnote"
    return True, (f"{got['items']} items, exact {got['exact']}, unanimous {got['unanimous']}, "
                  f"mean|d| {got['mean_abs_diff']}; alpha footnoted")


def g4():
    """Argument order must not change a single interval.

    Fails on the unfixed code: one global RNG made every cell's draws depend on how many
    cells preceded it, and reversing this list moved 10 of 46 cells.
    """
    runs = [MAIN_RUN, "2026-05-26-variance", "2026-05-27-ood",
            "2026-05-27-paraphrase", "2026-05-27-reversed-premise"]
    perms = [runs, list(reversed(runs)), [runs[2], runs[0], runs[4], runs[1], runs[3]]]
    seen = None
    for order in perms:
        p = run(["scripts/ci_analysis.py", *order], env={"BIAS_STUDY_BOOTSTRAP_N": "400"})
        if p.returncode != 0:
            return False, f"exit {p.returncode} on order {order}"
        blocks = {}
        cur = None
        for line in p.stdout.splitlines():
            h = re.match(r"=== (\S+) ", line)
            if h:
                cur = h.group(1)
                continue
            m = ROW.match(line)
            if m and cur:
                blocks[(cur, m.group(1))] = line.strip()
        if seen is None:
            seen = blocks
            continue
        shared = set(seen) & set(blocks)
        bad = [k for k in shared if seen[k] != blocks[k]]
        if bad:
            return False, f"{len(bad)}/{len(shared)} cells differ across argv order, e.g. {bad[0]}"
    return True, f"{len(seen)} cells identical across {len(perms)} argument orders"


def g5():
    """The key resolves from the process environment, and its absence is a hard error."""
    import score  # noqa: E402
    saved_paths, saved_key = score.ENV_PATHS, os.environ.pop("OPENROUTER_API_KEY", None)
    try:
        score.ENV_PATHS = []                       # no files at all
        if score.load_env().get("OPENROUTER_API_KEY"):
            return False, "a key was resolved with no env files and nothing in the environment"
        os.environ["OPENROUTER_API_KEY"] = "sk-selftest"
        if score.load_env().get("OPENROUTER_API_KEY") != "sk-selftest":
            return False, ("the process environment is not consulted -- this is the defect that "
                           "produced a clean run followed by a silently heuristic scoring pass")
    finally:
        score.ENV_PATHS = saved_paths
        os.environ.pop("OPENROUTER_API_KEY", None)
        if saved_key is not None:
            os.environ["OPENROUTER_API_KEY"] = saved_key
    src = (SCRIPT_DIR / "score.py").read_text(encoding="utf-8")
    if "if not args.skip_classifier and not api_key:" not in src:
        return False, "score.py does not refuse to run without a key"
    return True, "env-first resolution works; a missing key exits 2"


def g6():
    """A missing run is an operator error. It used to print [skip] and return 0."""
    for script in ("scripts/ci_analysis.py", "scripts/robustness_checks.py"):
        p = run([script, "2099-01-01-does-not-exist"], env={"BIAS_STUDY_BOOTSTRAP_N": "50"})
        if p.returncode == 0:
            return False, f"{script} returned 0 for a run that does not exist"
        if "[skip]" in p.stderr:
            return False, f"{script} still reports a missing run as [skip]"
    bar = (SCRIPT_DIR / "run_barometer.sh").read_text(encoding="utf-8")
    if 'ci_analysis.py "$RUN"' not in bar:
        return False, "run_barometer.sh step 4 still calls ci_analysis.py without a run-date"
    if "|| echo \"  ci_analysis note\"" in bar:
        return False, "run_barometer.sh still swallows an ci_analysis failure"
    return True, "missing run exits non-zero in both scripts; barometer passes $RUN and propagates"


def g7():
    """Every protocol file the prep gate names exists and has content.

    vendor-enrollment-brief.md was named by the gate and absent from the repo, which made
    the gate unsatisfiable -- and an unsatisfiable hard gate teaches an operator to skip
    prep, which is how the analysis defects above survived a whole quarter.
    """
    missing = []
    for name in PROTOCOL_FILES:
        p = STUDY_DIR / "protocol" / name
        if not p.is_file() or len(p.read_text(encoding="utf-8").strip()) < 200:
            missing.append(name)
    if missing:
        return False, f"missing or empty: {', '.join(missing)}"
    return True, f"all {len(PROTOCOL_FILES)} protocol files present"


def g8():
    """validate_runs finds the known manifest defects, and nothing else."""
    p = run(["scripts/validate_runs.py", "--json"])
    try:
        reports = json.loads(p.stdout)
    except json.JSONDecodeError:
        return False, f"non-JSON output: {p.stdout[:150]}"
    found = {(r["run"], f["code"]) for r in reports for f in r["findings"]}
    extra = found - KNOWN_MANIFEST_FINDINGS
    missing = KNOWN_MANIFEST_FINDINGS - found
    if extra or missing:
        return False, f"unexpected={sorted(extra)} missing={sorted(missing)}"
    if p.returncode == 0:
        return False, "returned 0 despite raising findings"
    return True, f"{len(found)} findings, exactly the known set"


def g9():
    """paired_analysis clusters on the template, and its own synthetic checks pass.

    Phase 2 is a matched-pair design, and matched-pair records flow through the existing
    estimator without complaint while being analysed wrongly: bootstrap_ci resamples a
    flat i.i.d. list, which counts three samples of one template as three independent
    observations. That is the pseudoreplication a prior substitution pass was killed for
    in adversarial review. This gate runs paired_analysis's synthetic suite, which
    recovers a planted gap, keeps a null null, shows the flat bootstrap understating the
    interval by roughly half on clustered data, and confirms the sign test agrees.
    """
    p = run(["scripts/paired_analysis.py", "--selftest"], timeout=600)
    if p.returncode != 0:
        fails = [l.strip() for l in p.stdout.splitlines() if l.strip().startswith("FAIL")]
        return False, "; ".join(fails)[:220] or f"exit {p.returncode}"
    m = re.search(r"flat i\.i\.d\. bootstrap understates by (\d+)%", p.stdout)
    if not m or int(m.group(1)) < 25:
        return False, "the clustered and flat estimators are not measurably different"
    return True, f"4 synthetic checks pass; flat i.i.d. understates by {m.group(1)}%"


def g10():
    """The matched-pair corpus is structurally what it claims to be.

    The whole design rests on the three arms of a template being identical except for the
    noun phrase naming who made the decision. If a second thing varies -- a clause, a
    verb, a register -- the arm gap is measuring that instead, and no amount of clustering
    saves it. So it is asserted on the committed strings rather than trusted to the
    generator, and 16 is asserted too: adversarial review adjudicated pseudoreplication at
    exactly that n, and going below re-opens a settled question.
    """
    import difflib
    path = STUDY_DIR / "protocol" / "pairs-v1.json"
    if not path.is_file():
        return False, "protocol/pairs-v1.json is missing"
    doc = json.loads(path.read_text(encoding="utf-8"))
    T = doc["templates"]
    if len(T) != 16:
        return False, f"{len(T)} templates, and 16 is the adjudicated floor"
    domains = {t["domain"] for t in T}
    registers = {t["register"] for t in T}
    if len(domains) != 8 or len(registers) != 2:
        return False, f"{len(domains)} domains x {len(registers)} registers, expected 8 x 2"
    if len({(t["domain"], t["register"]) for t in T}) != 16:
        return False, "a (domain, register) cell is duplicated or missing"

    arms = list(doc["_meta"]["arms"])
    if len(arms) != 3:
        return False, f"{len(arms)} arms; two cannot separate AI-specific from generic deference"

    spans = 0
    for t in T:
        # construction-independent: each prompt must be the stem with one substitution
        for arm, v in t["arms"].items():
            if "{" in v["prompt"]:
                return False, f"{t['pair_id']}/{arm}: prompt is not fully rendered"
            if v["prompt"].replace(v["agent_np"], "{AGENT_NP}", 1) != t["stem"]:
                return False, f"{t['pair_id']}/{arm}: prompt is not its stem plus the noun"
        for a, b in [(arms[0], arms[1]), (arms[0], arms[2]), (arms[1], arms[2])]:
            pa, pb = t["arms"][a]["prompt"].split(), t["arms"][b]["prompt"].split()
            ops = [o for o in difflib.SequenceMatcher(None, pa, pb, autojunk=False)
                   .get_opcodes() if o[0] != "equal"]
            if len(ops) != 1:
                return False, f"{t['pair_id']} {a}/{b}: {len(ops)} differing spans, expected 1"
            _, i1, i2, j1, j2 = ops[0]
            # The minimal span can legitimately exclude a shared article ("a caseworker"
            # vs "a review panel" differs from "caseworker") and can absorb trailing
            # punctuation, so the test is containment in the noun, not equality with it.
            for side, lo, hi, arm in ((pa, i1, i2, a), (pb, j1, j2, b)):
                got = " ".join(side[lo:hi]).rstrip(".,;:")
                if got not in t["arms"][arm]["agent_np"]:
                    return False, (f"{t['pair_id']}/{arm}: the differing span {got!r} is not "
                                   f"part of the agent noun {t['arms'][arm]['agent_np']!r}")
            spans += 1

    # the noun must be crossed with the domain, not fixed per arm
    by_domain = {t["domain"]: t["noun_index"] for t in T}
    if len(set(by_domain.values())) < 3:
        return False, ("the noun is not rotated across domains -- the arm would be "
                       "confounded with one phrase")
    return True, (f"16 templates, 8 domains x 2 registers, {len(arms)} arms, "
                  f"{spans} arm pairs each differing in exactly one span")


GATES = {"G1": g1, "G2": g2, "G3": g3, "G4": g4, "G5": g5, "G6": g6, "G7": g7, "G8": g8,
         "G9": g9, "G10": g10}


def main(argv: list[str]) -> int:
    if "--list" in argv:
        for k, f in GATES.items():
            print(f"{k}  {(f.__doc__ or '').strip().splitlines()[0]}")
        return 0
    names = [a.upper() for a in argv if not a.startswith("-")] or list(GATES)
    bad = [n for n in names if n not in GATES]
    if bad:
        print(f"unknown gate(s): {', '.join(bad)}", file=sys.stderr)
        return 2
    failures = 0
    for name in names:
        try:
            ok, detail = GATES[name]()
        except Exception as e:  # a gate that crashes is a gate that failed
            ok, detail = False, f"{type(e).__name__}: {e}"
        print(f"  {'PASS' if ok else 'FAIL'}  {name}  {detail}")
        failures += 0 if ok else 1
    print(f"\n{len(names) - failures}/{len(names)} gates pass")
    if failures:
        print("Phase 2 spends no API budget until all ten are green.", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
