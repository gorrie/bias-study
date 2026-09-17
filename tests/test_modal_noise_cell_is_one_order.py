"""A modal-noise cell is ONE model, ONE condition, ONE item order.

WHY THIS FILE EXISTS
--------------------
`floor_resolution.wave_cells()` keyed on `(model, condition)` and ignored `shuffle_seed`.

Under the ORIGINAL wave design that WAS a cell: one item order, five swept sampling seeds. The
design that collects on the author's battery sweeps THREE item orders per (model, condition) --
shuffle seeds 11, 22, 33 -- so the same key silently pooled them. Measured on the live corpus
2026-09-17: **32 of 33 condition-D groups contained more than one item order.**

What this arm measures is the estimator's own spread -- the distance between two bootstrap
modals OF THE SAME CELL, where every item that differs differs because the modal moved and
nothing else did. Pool two orders into the cell and presentation-order variance lands inside
that number. It is the denominator every other floor in the table is judged against, so
inflating it makes every real effect look smaller than it is.

Pass 2 (`--replicate 5 --conditions D`, ~148 sheets) writes its repeats at ONE fixed order into
cells that already hold wave sheets at three orders. Without this key, all of it pools.

The test plants the defect rather than describing it: two orders, same model, same condition,
each deep enough to qualify, and asserts they are two cells and never one.
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "scripts"))

import floor_resolution as R  # noqa: E402
import floor_table as F  # noqa: E402


def _sheet(model, condition, shuffle_seed, seed, answers):
    return {
        "schema": "compass-run/1",
        "instrument": "ratchet-battery",
        "n_items": 32,
        "model": model,
        "condition": condition,
        "shuffle_seed": shuffle_seed,
        "seed": seed,
        "template": "T01",
        "temperature": 0.7,
        "valid": True,
        "answers": [{"q": i + 1, "position": p} for i, p in enumerate(answers)],
    }


def _plant(tmp_path, monkeypatch):
    """A run tree holding one model, condition D, TWO orders, four runs each."""
    run_dir = tmp_path / "runs" / "2026-09-16-planted-wave"
    run_dir.mkdir(parents=True)
    rows = []
    base = [0, 1, 2, 3] * 8
    for order in (11, 22):
        for k in range(4):
            # Vary one item per run so the sheets are not identical and not degenerate.
            answers = list(base)
            answers[k] = (answers[k] + 1) % 4
            rows.append(_sheet("vendor/model-x", "D", order, 20260900 + order * 10 + k,
                               answers))
    with io.open(str(run_dir / "vendor__model-x__D.jsonl"), "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    monkeypatch.setattr(F, "STUDY", str(tmp_path))
    monkeypatch.setattr(R, "WAVE", "runs/*-wave/*.jsonl")
    return run_dir


def test_two_orders_are_two_cells(tmp_path, monkeypatch):
    _plant(tmp_path, monkeypatch)
    cells = R.wave_cells(condition="D")
    assert len(cells) == 2, (
        "two item orders for one (model, condition) collapsed into %d cell(s). A modal-noise "
        "cell that spans orders measures presentation order as run-to-run noise, and that "
        "number is the denominator under every other floor." % len(cells))
    for key in cells:
        assert len(key) == 3, "the cell key must carry the item order, got %r" % (key,)
    orders = {k[2] for k in cells}
    assert orders == {11, 22}, orders
    for runs in cells.values():
        assert len(runs) == 4, "each planted order holds four runs; got %d" % len(runs)


def test_a_cell_below_the_minimum_is_dropped_not_merged(tmp_path, monkeypatch):
    """Three runs at one order must not be topped up from a different order."""
    run_dir = tmp_path / "runs" / "2026-09-16-planted-wave"
    run_dir.mkdir(parents=True)
    base = [0, 1, 2, 3] * 8
    rows = []
    for order, n in ((11, 4), (22, 3)):
        for k in range(n):
            answers = list(base)
            answers[k] = (answers[k] + 1) % 4
            rows.append(_sheet("vendor/model-x", "D", order, 20260900 + order * 10 + k,
                               answers))
    with io.open(str(run_dir / "vendor__model-x__D.jsonl"), "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    monkeypatch.setattr(F, "STUDY", str(tmp_path))
    monkeypatch.setattr(R, "WAVE", "runs/*-wave/*.jsonl")

    cells = R.wave_cells(condition="D")
    assert len(cells) == 1, (
        "the three-run order should be dropped for depth, not merged into the four-run one; "
        "got %d cell(s)" % len(cells))
    assert list(cells)[0][2] == 11


def test_between_vs_within_takes_one_order_per_model(tmp_path, monkeypatch):
    _plant(tmp_path, monkeypatch)
    out = R.between_vs_within(condition="D", min_runs=4)
    assert out["models"] == 1, out["models"]
    # Four runs in one cell = six within-pairs. Pooled across both orders it would be 28.
    assert out["within"]["n"] == 6, (
        "within-cell pairs should come from ONE order (4 runs -> 6 pairs); got %d, which is "
        "what pooling both orders produces" % out["within"]["n"])
