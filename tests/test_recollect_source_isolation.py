"""One output directory per SOURCE run, or repairs silently go missing.

WHY THIS FILE EXISTS
--------------------
Cells key on (model, question_id, condition), and those keys COLLIDE across runs:
the same model answers the same question under the same condition in the
gradient, variance and augmentation runs. Three sources were pointed at one
output directory on 2026-09-14, and the second and third then saw the first's
records as "already collected".

Measured: the variance run collected **0 of 20** cells and reported success. The
repair looked complete and covered one source of three, and nothing in the output
said so -- the totals were right, for the wrong corpus.

Refused rather than merged, because a merged directory leaves a spliced corpus
whose repairs cannot be attributed to the run they repair. That attribution is
the only reason the splice is auditable at all.
"""
import inspect
import io
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import recollect_at_cap as R  # noqa: E402


def _write(dirpath, records):
    os.makedirs(dirpath, exist_ok=True)
    with io.open(os.path.join(dirpath, "m.jsonl"), "w", encoding="utf-8", newline="\n") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")


def _rec(src, qid="T01-Q1", cond="A"):
    return {"model": "openai/gpt-5", "question_id": qid, "condition": cond,
            "ok": True, "response_text": "A complete answer.", "max_tokens": 4000,
            "recollected_from": src}


def test_the_guard_exists_in_main():
    src = inspect.getsource(R.main)
    assert "recollected_from" in src, "main does not inspect repair provenance"
    assert "cell keys collide" in src or "collide" in src


def test_a_foreign_source_is_refused(tmp_path, monkeypatch, capsys):
    """The exact shape that lost 20 cells."""
    out = tmp_path / "shared" / "raw"
    _write(str(out), [_rec("2026-05-26-augmentation")])
    monkeypatch.setattr(R, "OUT_DIR", str(out))
    monkeypatch.setattr(R, "SOURCE", str(tmp_path / "2026-05-26-variance"))
    rc = R.main(["--plan"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "already holds repairs for" in err
    assert "2026-05-26-augmentation" in err


def test_the_same_source_is_allowed(tmp_path, monkeypatch):
    """Resuming a source into its OWN directory must keep working."""
    src_dir = tmp_path / "2026-05-26-variance"
    (src_dir / "scored").mkdir(parents=True)
    out = tmp_path / "variance-repair" / "raw"
    _write(str(out), [_rec("2026-05-26-variance")])
    monkeypatch.setattr(R, "OUT_DIR", str(out))
    monkeypatch.setattr(R, "SOURCE", str(src_dir))
    assert R.main(["--plan"]) == 0


def test_an_empty_output_directory_is_allowed(tmp_path, monkeypatch):
    src_dir = tmp_path / "2026-05-26-variance"
    (src_dir / "scored").mkdir(parents=True)
    out = tmp_path / "fresh" / "raw"
    os.makedirs(str(out))
    monkeypatch.setattr(R, "OUT_DIR", str(out))
    monkeypatch.setattr(R, "SOURCE", str(src_dir))
    assert R.main(["--plan"]) == 0


def test_records_without_provenance_do_not_trip_the_guard(tmp_path, monkeypatch):
    """Legacy records predate the field; they must not block a legitimate run."""
    src_dir = tmp_path / "2026-05-26-variance"
    (src_dir / "scored").mkdir(parents=True)
    out = tmp_path / "legacy" / "raw"
    rec = _rec("2026-05-26-variance")
    del rec["recollected_from"]
    _write(str(out), [rec])
    monkeypatch.setattr(R, "OUT_DIR", str(out))
    monkeypatch.setattr(R, "SOURCE", str(src_dir))
    assert R.main(["--plan"]) == 0


# ------------------------------------------------- the live repair directories

def test_each_live_repair_directory_holds_exactly_one_source():
    """The property the split restored. Asserted on disk, not on intent."""
    from studypaths import run_roots
    import glob
    for root in run_roots():
        for d in sorted(root.glob("2026-09-14-recollect-gpt5*")):
            raw = d / "raw"
            if not raw.is_dir():
                continue
            sources = set()
            for p in glob.glob(str(raw / "*.jsonl")):
                with io.open(p, encoding="utf-8") as fh:
                    for line in fh:
                        if line.strip():
                            sources.add(json.loads(line).get("recollected_from"))
            sources.discard(None)
            assert len(sources) <= 1, (
                "%s mixes repairs from %s; cell keys collide across runs, so the "
                "second source's cells were skipped" % (d.name, sorted(sources)))
