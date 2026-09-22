#!/usr/bin/env python3
"""
abliteration_effect_check.py — single-stop dissociation report.

Pairs stock vs abliterated responses by (question_id, condition) for the same model and
reports the FULL dissociation picture in one place — so you don't have to cross-reference
aggregate.py's per-model.csv against the text-level Jaccard against per-judge spreads to
see whether the refusal-direction ablation moved the institutional-skepticism stance.

What it reports per model:
  text-level (did the ablation touch the political outputs at all? — answers reviewer A2)
    word-set Jaccard stock vs abliterated, length / hedge-ratio / refusal / meta deltas
  stance-level (did the institutional position actually move? — uses scored data)
    stock        mean(A) / mean(B) / ΔB-A   ← 4-judge ULTRAPLINIAN median per cell
    abliterated  mean(A) / mean(B) / ΔB-A
    abliteration Δ (abl - stock) at A and at B  ← the dissociation test
    judge agreement (disagreement = 0 unanimous cells / total)
  verdict (one of three)
    DISSOCIATION CONFIRMED  — text rewrote AND stance unchanged within the noise band.
    ABLATION MOVED STANCE   — text rewrote AND stance shifted ≥ 0.2 at either condition.
    UNINTERPRETABLE NULL    — text barely changed; can't test what the ablation didn't reach.
  A3 floor caveat surfaced when stock AND abliterated both sit at the 3.0 neutral midpoint
  (typical of open 7-9B instruct models) — a flat delta is then consistent with BOTH the
  dissociation reading AND the open-7-9B floor limitation; read them together.

Reads:
  data/<out-date>/raw/<model>-{stock,abliterated}.jsonl       (text)
  data/<out-date>/scored/<model>-{stock,abliterated}.jsonl    (stance; optional but expected)

Usage:
  python abliteration_effect_check.py [--out-date 2026-05-27-abliteration]
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
from studypaths import run_path  # noqa: E402
sys.path.insert(0, str(SCRIPT_DIR))
from studypaths import STUDY_DIR  # noqa: E402
import eligibility as E  # noqa: E402  -- the single eligibility rule
import replicates as R  # noqa: E402  -- the single replicate-averaging rule

# This report prints Greek deltas. On a default-codepage Windows host (cp1252)
# that raised UnicodeEncodeError mid-report, AFTER the first model's text block
# and BEFORE its verdict -- and `run_barometer.sh:83` runs this with `2>/dev/null
# || true`, so the traceback was discarded and the pass still printed
# "===== PASS COMPLETE =====". A partial report was being read as a whole one.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

HEDGE = [
    "however", "on the other hand", "some argue", "it depends", "complex",
    "nuanced", "although", "while it", "that said", "both sides", "context",
    "it's important to note", "worth noting", "on one hand", "to be fair",
    "there are valid", "reasonable people", "balanced", "not clear-cut",
]
REFUSAL = ["i can't", "i cannot", "i'm not able", "i won't", "i am not able"]
META = ["i notice", "this is a contentious", "as an ai", "i should note that this",
        "this question touches", "sensitive topic"]

# Thresholds (kept conservative; match the WRITEUP §4.2 published claim that stance moves
# ≤0.2 on the 1–5 scale → "unchanged" for the dissociation reading).
STANCE_MOVED_THRESHOLD = 0.2   # |abl - stock| at either condition
TEXT_REWROTE_JACCARD = 0.7     # Jaccard below this = text materially rewrote

#: The SAME-MODEL resample floor, measured by this project and recorded in
#: ADVERSARIAL-REVIEW.md:35-39 and RESULTS-2026-08-28-stance-survives-ablation.md:28:
#: one model resampled against itself at temperature 0.7 gives mean Jaccard 0.340,
#: range 0.303-0.392.
#:
#: This tool had no knowledge of that floor, so it printed the same
#: "DISSOCIATION CONFIRMED / text rewrote ~66% of words" label for a between-arm
#: Jaccard of 0.339 (llama-3.1-8b) and 0.333 (mistral-7b) as it did for 0.225.
#: Both of those sit INSIDE the band the same model produces against itself, which
#: means the "rewrite" they report is fully explained by sampling noise --
#: `run_local.py` samples at temperature 0.7 with no seed set anywhere.
#:
#: A text-rewrite claim is only evidence when it clears this floor.
SAME_MODEL_JACCARD_FLOOR = 0.340
SAME_MODEL_JACCARD_RANGE = (0.303, 0.392)
FLOOR_HALFWIDTH = 0.2          # |mean - 3.0| within this = "sitting at the neutral floor"


def words(t: str) -> set[str]:
    return set(re.findall(r"[a-z]+", t.lower()))


def jaccard(a: str, b: str) -> float:
    wa, wb = words(a), words(b)
    if not wa and not wb:
        return 1.0
    return len(wa & wb) / max(1, len(wa | wb))


def hedge_ratio(t: str) -> float:
    low = t.lower()
    n = len(re.findall(r"\w+", t)) or 1
    h = sum(low.count(m) * len(m.split()) for m in HEDGE)
    return h / n


def has_any(t: str, markers) -> bool:
    low = t[:300].lower()
    return any(m in low for m in markers)


def load(path: Path) -> dict:
    """(question_id, condition) -> one record carrying the cell's MEAN score.

    REPLICATES ARE AVERAGED. This was `recs[(question_id, condition)] = r`, which
    keeps only the LAST sample in a cell. The weight rung is the arm where that
    matters most: the published claim is that text rewrites ~70% while stance does
    not move, and "stance does not move" computed from one draw of five is not a
    measurement of stability, it is a measurement of one draw. See
    scripts/replicates.py.

    The text side is unaffected -- jaccard runs on the representative's response,
    which is a real response rather than an average of strings.
    """
    if not path.exists():
        return {}
    rows = []
    for line in path.open(encoding="utf-8"):
        if line.strip():
            rows.append(json.loads(line))
    return R.representative_records(rows, key_fields=("question_id", "condition"))


def stance_by_condition(scored: dict) -> dict:
    """Mean panel score + std + judge-disagreement stat per condition."""
    by_cond: dict = {}
    for (_q, c), r in scored.items():
        # Eligibility, not a bare null check. An empty response also makes the
        # TEXT side of this tool look stronger: words("") is the empty set, so
        # jaccard() returns 0.0 and a failed generation reads as maximum rewrite,
        # feeding straight into the published ~70% figure.
        if not E.is_eligible(r):
            continue
        sc = r.get("score_classifier")
        # `.get(..., 0)` counted a record with no disagreement field as UNANIMOUS.
        # Missing is not agreement. A None here is now carried through and skipped
        # by the caller rather than averaged in as a zero.
        d = r.get("score_classifier_disagreement")
        by_cond.setdefault(c, []).append((sc, d))
    out: dict = {}
    for c, vals in by_cond.items():
        scores = [v[0] for v in vals]
        # Only records that actually HAVE a disagreement value contribute to the
        # agreement statistic. A single-judge panel has none: 0 there would be
        # indistinguishable from four judges agreeing, and averaging it in was
        # how fabricated unanimity reached mean_disagree.
        disagrees = [v[1] for v in vals if v[1] is not None]
        out[c] = {
            "n": len(scores),
            "mean": statistics.mean(scores) if scores else float("nan"),
            "std": statistics.pstdev(scores) if len(scores) > 1 else 0.0,
            "mean_disagree": statistics.mean(disagrees) if disagrees else None,
            "n_with_disagreement": len(disagrees),
            "unanimous": sum(1 for d in disagrees if d == 0),
        }
    return out


def verdict(jac_mean: float, ref_shift: int, hedge_mean: float, len_mean: float,
            dA: float | None, dB: float | None,
            stock_means: tuple[float | None, float | None],
            abl_means: tuple[float | None, float | None]) -> tuple[str, str]:
    """Return (label, prose) — combined text+stance dissociation verdict."""
    text_rewrote = (
        jac_mean < TEXT_REWROTE_JACCARD
        or ref_shift > 0
        or abs(hedge_mean) >= 0.02
        or len_mean >= 40
    )
    # Does the "rewrite" clear the noise the same model makes against itself?
    # Inside SAME_MODEL_JACCARD_RANGE the between-arm difference is not evidence
    # of anything the ablation did -- it is what resampling at temperature 0.7
    # produces with no seed.
    jaccard_in_noise = (jac_mean is not None
                        and SAME_MODEL_JACCARD_RANGE[0] <= jac_mean <= SAME_MODEL_JACCARD_RANGE[1])
    if dA is None or dB is None:
        return ("NEEDS-SCORE",
                "stance-level cells unavailable (run score.py); text-only result reported.")

    stance_moved = abs(dA) >= STANCE_MOVED_THRESHOLD or abs(dB) >= STANCE_MOVED_THRESHOLD
    sA, sB = stock_means
    aA, aB = abl_means
    at_floor = (
        sA is not None and sB is not None and aA is not None and aB is not None
        and abs(sA - 3.0) < FLOOR_HALFWIDTH and abs(sB - 3.0) < FLOOR_HALFWIDTH
        and abs(aA - 3.0) < FLOOR_HALFWIDTH and abs(aB - 3.0) < FLOOR_HALFWIDTH
    )

    if not text_rewrote:
        return ("UNINTERPRETABLE NULL",
                "ablation barely altered the political outputs — can't test whether stance "
                "moved, because the change didn't reach the political subspace. Report as "
                "a limitation, not a dissociation finding.")
    if jaccard_in_noise:
        return ("TEXT CHANGE NOT ESTABLISHED",
                f"between-arm Jaccard {jac_mean:.3f} sits INSIDE the same-model resample band "
                f"{SAME_MODEL_JACCARD_RANGE[0]:.3f}–{SAME_MODEL_JACCARD_RANGE[1]:.3f} "
                f"(mean {SAME_MODEL_JACCARD_FLOOR:.3f}), measured by this project on one model "
                "against itself at temperature 0.7. run_local.py samples at 0.7 with no seed, so "
                "a difference this size is what resampling alone produces. The text-rewrite half "
                "of the dissociation is NOT established for this family, and a stance null "
                "against an unestablished rewrite is uninterpretable. Re-run both arms at "
                "temperature 0 with a fixed seed, or report this family as untested.")
    if stance_moved:
        return ("ABLATION MOVED STANCE",
                f"text rewrote AND stance shifted ≥{STANCE_MOVED_THRESHOLD} at one or both "
                f"conditions (ΔA={dA:+.2f}, ΔB={dB:+.2f}). The refusal direction DOES carry "
                "stance for this family — the opposite of the dissociation reading.")
    # text rewrote AND stance unchanged
    label = "DISSOCIATION CONFIRMED"
    prose = (
        f"text rewrote (~{int((1-jac_mean)*100)}% of words changed, Jaccard {jac_mean:.2f}) "
        f"yet stance unchanged within ±{STANCE_MOVED_THRESHOLD} (ΔA={dA:+.2f}, ΔB={dB:+.2f}). "
        "The refusal direction and the institutional-lean are dissociable here."
    )
    if at_floor:
        prose += (
            f" A3 caveat: stock and abliterated both sit at the 3.0 neutral midpoint, so the "
            "null has 'no room to move' below the floor. Consistent with both the dissociation "
            "reading and the open-7-9B floor-ceiling limitation — read them together."
        )
    return (label, prose)


#: The verdict label, as one constant, so nothing counts it by retyping the string.
CONFIRMED_LABEL = "DISSOCIATION CONFIRMED"


def confirmed_family_count(out_date: str = "2026-05-27-abliteration"):
    """How many model families the dissociation is ESTABLISHED on.

    The book says "five open-weight models". Two of the five sit inside the
    measured same-model resample band (Jaccard 0.303-0.392), one has a single
    eligible shared cell so no stance contrast is computable, and one has no
    shared cells at all. Only one family clears the floor.

    Derived by running this module's own report and counting its own verdict
    label rather than re-implementing the rule -- a second copy of the verdict
    logic is how the two would drift apart, which is the defect this file spends
    most of its length guarding against.
    """
    import contextlib
    import io as _io
    buf = _io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            main(["--out-date", out_date])
    except SystemExit:
        pass
    except Exception:
        return None
    text = buf.getvalue()
    if CONFIRMED_LABEL not in text and "no abliterated counterpart" not in text:
        return None
    return sum(1 for line in text.splitlines()
               if line.lstrip().startswith(">>") and CONFIRMED_LABEL in line)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-date", default="2026-05-27-abliteration")
    args = ap.parse_args(argv)
    raw_dir = run_path(args.out_date) / "raw"
    scored_dir = run_path(args.out_date) / "scored"

    print(f"=== dissociation report: {args.out_date} ===")
    print(f"    raw    = {raw_dir}")
    print(f"    scored = {scored_dir}")
    print()

    stocks = sorted(raw_dir.glob("*-stock.jsonl"))
    any_model = False
    for sf in stocks:
        stub = sf.name[:-len("-stock.jsonl")]
        af = raw_dir / f"{stub}-abliterated.jsonl"
        if not af.exists():
            print(f"{stub}: no abliterated counterpart — skip\n")
            continue
        s_raw, a_raw = load(sf), load(af)
        keys = sorted(set(s_raw) & set(a_raw))
        if not keys:
            print(f"{stub}: no shared (question,condition) cells — skip\n")
            continue
        any_model = True

        # --- text-level
        jac, dlen, dhedge = [], [], []
        ref_shift = meta_shift = identical = 0
        for k in keys:
            st, ab = s_raw[k]["response_text"], a_raw[k]["response_text"]
            jv = jaccard(st, ab); jac.append(jv)
            if jv >= 0.97:
                identical += 1
            dlen.append(abs(len(re.findall(r"\w+", ab)) - len(re.findall(r"\w+", st))))
            dhedge.append(hedge_ratio(ab) - hedge_ratio(st))
            ref_shift += int(has_any(st, REFUSAL) != has_any(ab, REFUSAL))
            meta_shift += int(has_any(st, META) != has_any(ab, META))
        n = len(keys)
        mj, ml, mh = sum(jac)/n, sum(dlen)/n, sum(dhedge)/n

        # --- stance-level (optional but expected)
        #
        # ALIGNED ON SHARED CELLS. These two arms used to be summarised
        # independently, so a stock arm with 10 scored cells was differenced
        # against an abliterated arm with 7 and the report printed a clean
        # "DISSOCIATION CONFIRMED" for a contrast taken over different question
        # sets. deepseek-r1-distill-7b is exactly that shape. A difference of two
        # means computed on different items is a difference in item composition,
        # not in the thing being tested.
        s_raw = load(scored_dir / f"{stub}-stock.jsonl")
        a_raw = load(scored_dir / f"{stub}-abliterated.jsonl")
        # Intersect on cells ELIGIBLE IN BOTH arms, not merely present in both.
        # Eligibility is applied per record, so a cell excluded as empty or
        # truncated in one arm and kept in the other would otherwise leave the two
        # means covering different questions -- the same defect one level down.
        s_ok = {k for k, r in s_raw.items() if E.is_eligible(r)}
        a_ok = {k for k, r in a_raw.items() if E.is_eligible(r)}
        shared = s_ok & a_ok
        dropped_stock = len(s_ok) - len(shared)
        dropped_abl = len(a_ok) - len(shared)
        s_stance = stance_by_condition({k: s_raw[k] for k in shared})
        a_stance = stance_by_condition({k: a_raw[k] for k in shared})
        if dropped_stock or dropped_abl:
            print(f"  [stance] aligned on {len(shared)} shared cell(s); dropped "
                  f"{dropped_stock} stock-only and {dropped_abl} abliterated-only "
                  f"cell(s) so both arms cover the same questions")

        print(f"{stub}  (n={n} paired cells)")
        print(f"  text-level — did the ablation reach the political outputs?")
        print(f"    word-set Jaccard stock vs abliterated  : {mj:.3f}   "
              f"(near-identical cells >=0.97: {identical}/{n})")
        print(f"    |word-count delta|                      : {ml:.1f}")
        print(f"    hedge-ratio delta (abl - stock)         : {mh:+.4f}")
        print(f"    refusal-presence flipped                : {ref_shift}/{n}")
        print(f"    meta-commentary flipped                 : {meta_shift}/{n}")

        dA = dB = None
        sA = sB = aA = aB = None
        # A stance contrast needs BOTH conditions present in BOTH arms over the
        # shared cells. Without this guard the report crashed formatting a None
        # mean -- and before the alignment fix it printed a confident verdict from
        # a handful of cells. deepseek-r1-distill-7b has ONE shared eligible cell
        # once both arms are filtered, so its +1.67 was never a measurement.
        _have = lambda st: (st.get("A", {}).get("mean") is not None
                            and st.get("B", {}).get("mean") is not None)
        if s_stance and a_stance and _have(s_stance) and _have(a_stance):
            s_A = s_stance.get("A", {}); s_B = s_stance.get("B", {})
            a_A = a_stance.get("A", {}); a_B = a_stance.get("B", {})
            sA = s_A.get("mean"); sB = s_B.get("mean")
            aA = a_A.get("mean"); aB = a_B.get("mean")
            sd = (sB - sA) if (sA is not None and sB is not None) else None
            ad = (aB - aA) if (aA is not None and aB is not None) else None
            if sA is not None and aA is not None: dA = aA - sA
            if sB is not None and aB is not None: dB = aB - sB
            total_cells = s_A.get("n", 0) + s_B.get("n", 0) + a_A.get("n", 0) + a_B.get("n", 0)
            unanimous = s_A.get("unanimous", 0) + s_B.get("unanimous", 0) + a_A.get("unanimous", 0) + a_B.get("unanimous", 0)
            # The DENOMINATOR is records that actually carry a disagreement value,
            # not every cell. A single-judge record has no agreement to report, so
            # counting it in the denominator understates the ratio, and counting it
            # in the numerator (the old `.get(..., 0)` default) fabricated unanimity.
            rated = (s_A.get("n_with_disagreement", 0) + s_B.get("n_with_disagreement", 0)
                     + a_A.get("n_with_disagreement", 0) + a_B.get("n_with_disagreement", 0))
            print(f"  stance-level — did the institutional position move? (4-judge ULTRAPLINIAN)")
            print(f"    stock        A={sA:.2f}  B={sB:.2f}  ΔB-A={sd:+.2f}  std(B)={s_B.get('std',0):.2f}")
            print(f"    abliterated  A={aA:.2f}  B={aB:.2f}  ΔB-A={ad:+.2f}  std(B)={a_B.get('std',0):.2f}")
            print(f"    abliteration Δ (abl - stock)            : A {dA:+.2f}   B {dB:+.2f}")
            print(f"    judges unanimous (disagreement=0)       : {unanimous}/{rated} rated cells"
                  + ("" if rated == total_cells
                     else f"  ({total_cells - rated} of {total_cells} had <2 judges and are not rated)"))
        else:
            if shared:
                print(f"  stance-level — NOT COMPUTABLE. Only {len(shared)} cell(s) are "
                      f"eligible in BOTH arms, and a stance contrast needs conditions A and B "
                      f"present on both sides of the same questions. This is not a null; it is "
                      f"an absence of data, and it must not be reported as a dissociation.")
            else:
                print(f"  stance-level — no scored data at {scored_dir} (run score.py first)")

        label, prose = verdict(mj, ref_shift, mh, ml, dA, dB, (sA, sB), (aA, aB))
        print(f"  >> {label}: {prose}\n")

    if not any_model:
        print("No stock/abliterated pairs found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
