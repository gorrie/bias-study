"""Every run directory must be accounted for, and the roles must not collapse together."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import run_inventory as RI


def _mk(tmp, name, records=0, manifest=False, other=None, schema="compass-run/1"):
    d = tmp / "runs" / name
    d.mkdir(parents=True)
    if records:
        with open(d / "m.jsonl", "w", encoding="utf-8") as fh:
            for _ in range(records):
                fh.write(json.dumps({"model": "m", "condition": "A", "schema": schema}) + "\n")
    if manifest:
        (d / "manifest.json").write_text("{}", encoding="utf-8")
    if other:
        (d / other).write_text("{}", encoding="utf-8")
    return d


def test_a_registered_run_with_no_records_is_not_called_empty(tmp_path):
    """The residency-smoke dirs carry a manifest and zero records. That is an attempted run --
    evidence about the attempt -- and calling it 'empty' loses the W04 signal."""
    _mk(tmp_path, "smoke", records=0, manifest=True)
    rows = RI.classify(RI.scan(str(tmp_path)), "")
    assert rows[0]["role"] == "registered, no records"


def test_a_derived_output_directory_is_not_called_empty(tmp_path):
    _mk(tmp_path, "agg", records=0, other="cross-method.json")
    rows = RI.classify(RI.scan(str(tmp_path)), "")
    assert rows[0]["role"] == "derived output only"


def test_a_collection_input_is_not_reported_as_unanalysed(tmp_path):
    """Thirteen directories feed the floor tools with no write-up of their own. Naming that
    'unanalysed' is what sent an audit chasing 1,460 records that were already inputs."""
    _mk(tmp_path, "inp", records=5)
    rows = RI.classify(RI.scan(str(tmp_path)), "")
    assert rows[0]["role"] == "collection input"


def test_a_genuinely_orphaned_collection_is_flagged(tmp_path):
    """Records, no collection schema, named nowhere -- the case the inventory exists to surface."""
    _mk(tmp_path, "orphan", records=5, schema=None)
    rows = RI.classify(RI.scan(str(tmp_path)), "")
    assert rows[0]["role"] == "UNACCOUNTED"


def test_documented_beats_input(tmp_path):
    _mk(tmp_path, "named-run", records=5)
    rows = RI.classify(RI.scan(str(tmp_path)), "see named-run for detail")
    assert rows[0]["role"] == "documented"
