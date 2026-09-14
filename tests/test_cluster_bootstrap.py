"""The cluster bootstrap must resample WITH replacement and keep duplicates.

WHY THIS FILE EXISTS
--------------------
`refusal_suite_summary.analyse` drew its clusters with

    pick = {rng.choice(types) for _ in types}

a SET comprehension. A cluster drawn twice collapsed to one, so each draw used a
mean of 11.57 of 18 clusters instead of 18. That is subsampling, not
bootstrapping, and it biases every interval NARROW -- measured ~15% (Qwen 0.245
against a correct 0.286, Gemma 0.234 against 0.280).

No verdict flipped, but the bias always runs the same way in a study whose
decision rule is "the interval excludes zero", so a borderline result would have
been called significant on the strength of the defect.
"""
import collections
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))


def test_a_set_comprehension_loses_clusters():
    """Quantify the original defect so the fix has a documented target."""
    rng = random.Random(20260828)
    types = list(range(18))
    sizes = [len({rng.choice(types) for _ in types}) for _ in range(4000)]
    mean = sum(sizes) / len(sizes)
    assert 11.0 < mean < 12.2, (
        "a set of 18 draws-with-replacement from 18 clusters averages ~11.57 "
        "distinct, not 18; got %.2f" % mean)


def test_counter_resampling_keeps_the_full_cluster_count():
    """The fix draws the same 18 times but retains multiplicity."""
    rng = random.Random(20260828)
    types = list(range(18))
    totals = []
    for _ in range(2000):
        counts = collections.Counter(rng.choice(types) for _ in types)
        totals.append(sum(counts.values()))
    assert all(t == 18 for t in totals), (
        "every bootstrap draw must carry 18 cluster-slots, duplicates included")


def test_multiplicity_reaches_the_records():
    """A cluster drawn twice must contribute its records twice."""
    cells = {("safe", "a"): [1, 1], ("unsafe", "a"): [0], ("safe", "b"): [1]}
    counts = collections.Counter({"a": 2, "b": 1})
    resample = lambda d: {k: v * counts[k[1]] for k, v in d.items() if counts[k[1]]}
    out = resample(cells)
    assert out[("safe", "a")] == [1, 1, 1, 1], "cluster 'a' drawn twice doubles its records"
    assert out[("safe", "b")] == [1]


def test_undrawn_clusters_are_excluded():
    cells = {("safe", "a"): [1], ("safe", "b"): [1]}
    counts = collections.Counter({"a": 2})
    resample = lambda d: {k: v * counts[k[1]] for k, v in d.items() if counts[k[1]]}
    out = resample(cells)
    assert ("safe", "b") not in out
    assert out[("safe", "a")] == [1, 1]


def test_the_shipped_source_no_longer_uses_a_set():
    """Check EXECUTABLE lines only.

    The fix's own comment quotes the defective line verbatim so a future reader
    knows what was wrong, which means a naive substring search finds it and fails.
    Stripping comments is the honest way to assert on code rather than prose --
    the alternative was to water down the comment to satisfy the test, which is
    the tail wagging the dog.
    """
    import inspect
    import refusal_suite_summary as R

    code = "\n".join(line for line in inspect.getsource(R).splitlines()
                     if not line.lstrip().startswith("#"))
    assert "pick = {rng.choice(types) for _ in types}" not in code, (
        "the set-comprehension bootstrap is back in executable code")
    assert "collections.Counter(rng.choice(types) for _ in types)" in code
