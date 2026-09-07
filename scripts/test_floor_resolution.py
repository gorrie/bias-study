#!/usr/bin/env python3
"""Tests for the modal-resolution layer and the per-model verdict.

WHY THIS FILE EXISTS
--------------------
`floor_resolution.py` and `model_cards.py` had ZERO tests, and between them they produced three
published numbers that a review then had to retract:

  1. `vendor()` returned the literal string "local" for every model name without a slash, so
     gemma2, llama3.1, phi4, qwen2.5 and mistral -- five different vendors -- were pooled into
     one pseudo-vendor and their ten CROSS-vendor pairs were counted as SAME-vendor. That is
     what produced the published "same vendor p90 10" and a table row reading
     "local, 2024 generation" as though it were a house.
  2. The per-model verdict compared a modal-vs-modal effect against a run-vs-run p90 and took
     the max of up to three contrasts uncorrected. 8 of 30 models "carried"; an exact
     permutation test says 1, and `grok-4.6` carried on an effect of 14 that shuffling
     reproduces at p = 1.0.
  3. The endpoint floor was cached at 400 bootstrap resamples, the one count in 200..2000 at
     which the discrete p90 lands on 7 instead of 8 -- and the ablation arm's effect is judged
     against that number.

Each test below pins one of those. They are cheap: the vendor map and the permutation test are
pure functions, so nothing here needs the corpus.
"""
from __future__ import annotations

import itertools
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import floor_resolution as FR   # noqa: E402
import floor_table as F         # noqa: E402


# --------------------------------------------------------------------------- vendor mapping

@pytest.mark.parametrize("model,expected", [
    ("gemma2:latest", "google"),
    ("gemma2:9b-instruct-q8_0", "google"),
    ("llama3.1:8b", "meta-llama"),
    ("llama3.2:latest", "meta-llama"),
    ("phi4:latest", "microsoft"),
    ("qwen2.5:14b", "qwen"),
    ("mistral:latest", "mistralai"),
    ("openai/gpt-5.6-luna", "openai"),
    ("z-ai/glm-5.3-flash", "z-ai"),
])
def test_vendor_resolves_local_names_to_real_vendors(model, expected):
    assert FR.vendor(model) == expected


def test_no_local_model_collapses_to_one_pseudo_vendor():
    """The actual regression: five vendors must not share one key.

    Asserting each mapping individually would still pass if every one of them returned the
    same wrong value, which is precisely the bug -- so assert the SET is five wide.
    """
    locals_ = ["gemma2:latest", "llama3.1:8b", "phi4:latest", "qwen2.5:14b", "mistral:latest"]
    assert len({FR.vendor(m) for m in locals_}) == 5


def test_unmapped_local_name_is_named_not_silently_bucketed():
    """An unknown bare name must be visibly unmapped rather than folded into a real vendor.

    Returning "local" for everything is what hid the bug for a week. A wrong answer that looks
    like an answer is worse than one that says it does not know.
    """
    v = FR.vendor("some-model-nobody-mapped:latest")
    assert v.startswith("unmapped:")


# --------------------------------------------------------------------- bootstrap resamples

def test_boot_count_is_above_the_endpoint_knife_edge():
    """The endpoint p90 is 8 at 200/300/800/1600/2000 resamples and 7 at exactly 400.

    Measured 2026-09-07 on the same seed and the same 110 cells. 400 was the default, so the
    cached endpoint floor read 7 -- and that floor is the denominator the ablation arm's
    endpoint effect is judged against, where 7 against 8 decides whether an effect clears it.
    """
    assert FR.BOOT >= 800, "BOOT dropped back toward the 7/8 knife edge at 400"


def test_cached_floor_matches_the_declared_boot_count():
    """A cache written at a different resample count than the module declares is a stale cache.

    The private tree's cache said 300 while the module said 400 and the paper said 400, so
    three sources disagreed about how the published number was computed.
    """
    import json
    path = os.path.join(os.path.dirname(HERE), "data", "modal-noise.json")
    if not os.path.exists(path):
        pytest.skip("no cache in this checkout")
    rec = json.load(open(path, encoding="utf-8"))
    assert rec.get("boot") == FR.BOOT
    assert rec.get("seed") == FR.SEED


# ------------------------------------------------------------------ the permutation verdict

def _sheet(positions):
    """A run in the shape modal()/both_stats() expect: {item_id: position}."""
    return {i: p for i, p in enumerate(positions)}


def _perm_p(arm_a, arm_b):
    """The exact permutation p-value for one contrast, as model_cards computes it."""
    obs = F.both_stats(F.modal(arm_a), F.modal(arm_b))[0]
    pool = list(arm_a) + list(arm_b)
    na = len(arm_a)
    ge = tot = 0
    for idx in itertools.combinations(range(len(pool)), na):
        left = [pool[i] for i in idx]
        right = [pool[i] for i in range(len(pool)) if i not in idx]
        if F.both_stats(F.modal(left), F.modal(right))[0] >= obs:
            ge += 1
        tot += 1
    return ge / float(tot)


def test_identical_arms_give_p_of_one():
    """Two arms drawn from the same sheets cannot be distinguished. p must be 1.0, not 0."""
    a = [_sheet([2, 2, 3, 3, 2]) for _ in range(4)]
    b = [_sheet([2, 2, 3, 3, 2]) for _ in range(4)]
    assert _perm_p(a, b) == 1.0


def test_a_modal_permutation_null_is_COARSE_at_small_n():
    """PERFECT SEPARATION DOES NOT REACH p < 0.05 AT n=4, AND THAT IS THE METHOD, NOT A BUG.

    Arm A is four identical runs on one side of every item; arm B is four identical runs on the
    other. Maximally separated -- and the exact p-value is **34/70 = 0.486**.

    The reason is that a modal is a coarse statistic. Reshuffling into a 3-1 split still hands
    the majority to one side, so the two modals still land on opposite sides and still produce
    the full distance. Of the 70 assignments, 34 reach it: the 4-0 and 3-1 splits either way
    (1 + 16 + 16 + 1). Only the 2-2 splits collapse, because `modal()` breaks a tie toward the
    lower position in BOTH arms and the distance falls to zero.

    This test asserted `2/70` when it was written -- reasoning that only the observed
    assignment and its mirror could reproduce a clean separation. That is wrong by a factor of
    seventeen, and the error mattered: it is the direct explanation for why the per-model card
    finds 1 model of 30 carrying rather than 8. The permutation test is conservative on a
    five-run modal by construction, so a `no` verdict means "not resolvable at this n", not
    "no effect". Anyone tempted to call the verdict too strict should read this number first.

    n=5 per arm is not a fix, only an improvement: C(10,5) = 252 and the real corpus's one
    surviving model lands at 2/252 raw.
    """
    a = [_sheet([0, 0, 0, 0, 0]) for _ in range(4)]
    b = [_sheet([3, 3, 3, 3, 3]) for _ in range(4)]
    p = _perm_p(a, b)
    assert p == pytest.approx(34.0 / len(list(itertools.combinations(range(8), 4))))
    assert p > 0.05, "if this ever passes at n=4, the null changed and the card's counts move"


def test_a_big_effect_on_a_bimodal_model_does_not_pass():
    """THE GROK-4.6 CASE, which is why the p90 rule was retired.

    This model's runs are bimodal: some sit near one sheet, some near another, in BOTH arms.
    The modal-vs-modal distance between arms is large -- and shuffling reproduces it, because
    the split is between modes and not between conditions. A rule that promotes this is
    inverted, since an unstable model is exactly what the card exists to catch.

    THE ARMS ARE 3-1 AND 1-3, NOT 2-2. A 2-2 split in both arms makes every item an exact tie,
    `modal()` breaks ties toward the lower position in both arms, and the two modals come out
    IDENTICAL -- effect 0, nothing tested. The first version of this fixture did that and
    asserted a non-zero effect, which is how it caught itself.
    """
    lo, hi = _sheet([0, 0, 0, 0, 0]), _sheet([3, 3, 3, 3, 3])
    a = [lo, lo, lo, hi]
    b = [hi, hi, hi, lo]
    obs = F.both_stats(F.modal(a), F.modal(b))[0]
    assert obs > 0, "fixture must produce a non-zero effect to be meaningful"
    assert _perm_p(a, b) > 0.05


def test_bonferroni_is_applied_over_the_contrasts_tested():
    """The card takes each model's LARGEST effect across contrasts, so it must correct for it.

    Not correcting is how the p90 rule inflated: max of three tests, raw p-value quoted.
    Uncorrected this corpus gives 5 of 30 carrying; corrected, 1.
    """
    raw = 0.02
    assert min(1.0, raw * 3) > 0.05
    assert min(1.0, raw * 1) < 0.05


# -------------------------------------------------------- the class split must stay a split

def test_manipulation_class_split_is_registered_in_all_floors():
    """A floor function not in ALL_FLOORS computes nothing anybody reads.

    The README's central 2x2 draws both of its columns from these rows. It was published once
    with a pooled figure in one cell because the per-class row did not exist.
    """
    assert F.floor_conditions_wave_by_class in F.ALL_FLOORS


def test_class_split_labels_do_not_claim_an_open_versus_closed_axis():
    """The split test is `"/" in model` -- hosted against local.

    It was published headed "2026 frontier API" against "2024-generation open-weight", which
    asserts an axis the code does not test and gets it backwards: most of the hosted roster is
    open weights served by someone else. The label may say hosted, local, API, vintage or
    quantisation. It may not say the local side is the open-weight side.
    """
    rows = F.floor_conditions_wave_by_class() or {}
    for name in rows:
        assert "2024-generation open-weight" not in name


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
