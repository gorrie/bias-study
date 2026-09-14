#!/usr/bin/env python3
"""One implementation of "average the replicates in a cell", for every consumer.

WHY THIS FILE EXISTS
--------------------
The same three-line bug shipped in six places:

    cells[(model, question_id)][condition] = record      # keeps only the LAST

With one sample per cell that is lossless, and the May wave ran one sample per
cell, so it was correct when written. With `--samples 5` it silently discards
four records of every five and reports the survivor as the cell's value -- an
n=1 estimate wearing a completed n=5. Nothing errors. The output looks like a
finished collection.

It reached the page. `WRITEUP-2026-05-26.md:350` publishes "The vendor-class
direction replicates under N=5 averaging: us-closed mean delta +0.259 vs
chinese-open +0.204", and nothing was averaged. Regenerated, the classes sit on
opposite sides of zero and one model's delta reverses sign.

Three copies were fixed one at a time (`pipeline_rung`, `aggregate`,
`frame_gap`) and three were still live when this file was written
(`analysis` twice, `abliteration_effect_check`). Fixing a defect once per call
site is how the fourth one survives, so there is now one function and the call
sites pass their key.

THE KEY MUST CARRY THE CONDITION
--------------------------------
Averaging over (model, question) alone pools B-STM, B-Parseltongue and B-Layered
into one number and then differences a cell against itself. `pipeline_rung`
records this as a lesson learned the hard way; it is enforced here by making the
caller name its key fields explicitly rather than inherit a default that happens
to be right.

REPLICATES ARE NOT INDEPENDENT OBSERVATIONS
-------------------------------------------
They are averaged into one value per cell, never appended to a sample. A
bootstrap must resample questions (or topics), not draws, or the interval
shrinks by roughly sqrt(n_samples) for no added information.
"""
from __future__ import annotations

import collections
import statistics as st

#: The key every per-question consumer should use. Named so a call site says
#: what it means rather than repeating a tuple literal.
BY_MODEL_CONDITION_QUESTION = ("model", "condition", "question_id")


def cell_means(records, key_fields=BY_MODEL_CONDITION_QUESTION,
               value_field="score_classifier", predicate=None):
    """Mean of `value_field` over the replicates in each cell.

    Returns `(means, depth)`, both keyed by the tuple of `key_fields`. `depth` is
    the number of contributing records, so a caller can REPORT cell depth rather
    than assume it -- a run that silently lost samples is then visible in the
    output instead of passing as a clean n.

    `predicate` filters records before grouping; pass `eligibility.is_eligible`
    to exclude refusals, empties and truncations. It is deliberately not the
    default: this module must not decide eligibility policy for its callers, and
    a caller that wants raw counts should not have to fight a hidden filter.

    Records missing the value, or carrying None, contribute to NEITHER the mean
    nor the depth -- depth counts what was actually averaged, because a depth
    that counts unusable records is the same lie in a different column.
    """
    acc = collections.defaultdict(list)
    for r in records:
        if predicate is not None and not predicate(r):
            continue
        value = r.get(value_field)
        if value is None:
            continue
        acc[tuple(r.get(f) for f in key_fields)].append(value)
    means = {k: st.mean(v) for k, v in acc.items()}
    depth = {k: len(v) for k, v in acc.items()}
    return means, depth


def representative_records(records, key_fields=BY_MODEL_CONDITION_QUESTION,
                           value_field="score_classifier", predicate=None):
    """One record per cell, carrying the cell's MEAN in `value_field`.

    For consumers that read whole records rather than scores. The returned record
    is a copy of the cell's last member with `value_field` replaced by the mean
    and `n_replicates` added, so existing readers keep working unchanged and a
    caller can start reporting depth without a second pass.

    A cell whose records all lack a usable value yields a representative with
    `value_field` None and `n_replicates` 0 -- present, so the cell is not
    silently absent, and unusable, so it cannot be averaged into anything.
    """
    groups = collections.OrderedDict()
    for r in records:
        if predicate is not None and not predicate(r):
            continue
        groups.setdefault(tuple(r.get(f) for f in key_fields), []).append(r)

    out = {}
    for key, recs in groups.items():
        values = [r.get(value_field) for r in recs if r.get(value_field) is not None]
        rep = dict(recs[-1])
        rep["n_replicates"] = len(values)
        rep[value_field] = st.mean(values) if values else None
        out[key] = rep
    return out


def depth_summary(depth):
    """How deep were the cells, as a fact rather than an assumption.

    Returns (sorted distinct depths, ragged?). A caller should print both: a run
    reported as n=5 that is ragged lost samples somewhere, and the whole reason
    this module exists is that losing samples is silent.
    """
    distinct = sorted(set(depth.values()))
    return distinct, len(distinct) > 1
