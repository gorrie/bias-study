"""The position-floor cache must match the corpus, and must be refusable rather than stale.

WHY THIS FILE EXISTS
--------------------
§1's headline table became a generated block on 2026-09-21, because the hand-typed version
disagreed with `order_floor_position.py` — the script the ABSTRACT's figures come from — on
both rows they share: 111 order pairs against 108, 62 significant against 46.

That table is a 4000-draw bootstrap over every pair and takes minutes, so it is cached. Caching
a derived number in this repository has a history: `data/modal-noise.json` sat at **34 cells
against a corpus of 576** for two weeks, because its regeneration path had been crashing since
a dictionary key gained a third element and nothing ever compared the `signature` field it
already carried.

So this cache is checked on every read and a mismatch is a REFUSAL, not a stale answer, and
`--check-cache` makes that reachable from here rather than only from a human reading output.
"""
import json
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(STUDY, "scripts"))

SCRIPT = os.path.join(STUDY, "scripts", "order_floor_position.py")
CACHE = os.path.join(STUDY, "data", "position-floor.json")


def _run(*args):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, SCRIPT] + list(args),
                          capture_output=True, text=True, env=env, timeout=3600)


def test_check_cache_exits_nonzero_when_the_cache_is_absent_or_stale():
    """The whole point: staleness is an exit code, not a paragraph nobody reads."""
    got = _run("--check-cache")
    if got.returncode == 0:
        assert "matches the corpus" in got.stdout, got.stdout
    else:
        assert "STALE OR ABSENT" in got.stdout, got.stdout


def test_the_cache_matches_the_corpus_right_now():
    if not os.path.exists(CACHE):
        pytest.skip("no position-floor cache in this tree")
    import order_floor_position as OFP
    import studypaths as _SP
    rec = json.load(open(CACHE, encoding="utf-8"))
    run_dir = os.path.join(_SP.STUDY_DIR, "runs", rec["signature"]["run"])
    if not os.path.isdir(run_dir):
        pytest.skip("the cached run is not in this tree")
    live = OFP.corpus_signature(run_dir, rec["signature"]["condition"],
                                rec["signature"]["draws"])
    assert rec["signature"] == live, (
        "position-floor cache is STALE. It feeds the paper's GEN:position block, which is "
        "§1's headline table.\nRegenerate: python scripts/order_floor_position.py --write\n"
        "cached: %s\nlive:   %s" % (rec["signature"], live))


def test_a_cache_with_no_rows_is_refused_rather_than_served():
    """An empty cache is the vacuous pass wearing a cache's coat."""
    import order_floor_position as OFP
    rows, why = OFP.read_cache({"run": "nothing", "condition": "N", "draws": 1,
                                "records": 0, "models": 0, "seeds": []})
    assert rows is None and why, "a signature that cannot match must never return rows"


def test_the_cached_table_has_both_rows_and_a_header():
    if not os.path.exists(CACHE):
        pytest.skip("no position-floor cache in this tree")
    rows = json.load(open(CACHE, encoding="utf-8"))["rows"]
    assert len(rows) == 4, "header, separator and exactly two data rows: %r" % (rows,)
    assert "balance instruction" in rows[2]
    assert "different order" in rows[3]
