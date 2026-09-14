"""The pipeline collector must record what it did, not only what it produced.

WHY THIS FILE EXISTS
--------------------
`run_study.py` has written a manifest since May. `run_g0dm0d3.py` wrote none, ever
-- `grep -c manifest` returned 23 and 0. So every run that collector produced
reached `validate_runs` as "no manifest.json", including the n=5 pair that is now
the default behind the corrected rung-2 estimate.

The gap was invisible because the same scoring and analysis tools read both
collectors' output, so nothing downstream noticed that half the runs could not be
checked against their own intent. A manifest is what lets a gate ask "did you
collect what you set out to collect" -- without one, a partial collection and a
complete one look identical on disk.

NOT RECONSTRUCTED FOR OLD RUNS, on purpose. A manifest derived from the records it
is meant to check makes `calls_completed == records` true by construction, so the
count gate would pass having compared a number to itself. That is a vacuous gate
wearing the appearance of a clean run. The pre-fix runs stay in
`validate_runs.KNOWN` as honest gaps, and that registry has a rot check so they
cannot sit there silently forever.
"""
import inspect
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import run_g0dm0d3 as G  # noqa: E402
import validate_runs as V  # noqa: E402


SRC = inspect.getsource(G)


def _body():
    """Source with comments and docstrings stripped, so asserting on CODE.

    A previous test in this repo passed because its own comment quoted the
    defective line it was checking for.
    """
    out = []
    for line in SRC.split("\n"):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        out.append(line.split("  #")[0])
    return "\n".join(out)


def test_the_collector_writes_a_manifest():
    body = _body()
    assert "manifest.json" in body, "run_g0dm0d3.py still writes no manifest"
    assert "json.dump(manifest" in body


def test_the_manifest_carries_the_fields_the_validator_checks():
    """validate_runs reads these by name; a manifest missing them validates nothing."""
    body = _body()
    for field in ("analysis_seed", "calls_completed", "models_attempted",
                  "models_completed", "total_calls_planned", "run_date"):
        assert '"%s"' % field in body, "manifest omits %s" % field


def test_it_records_the_parameters_that_ruin_a_run_silently():
    """max_tokens and samples are the two that have actually done damage here."""
    body = _body()
    assert '"max_tokens"' in body
    assert '"samples_per_cell"' in body
    assert '"conditions"' in body
    assert '"positions"' in body


def test_models_completed_is_tracked_from_actual_successes():
    """A model that failed entirely must not appear as completed.

    `models_completed` copied from `models_attempted` would assert coverage the
    run does not have -- the same shape as the label-derived abliteration flag.
    """
    body = _body()
    assert "completed_models.add(model)" in body, (
        "models_completed is not derived from successful calls")
    assert "completed_models: set = set()" in body


def test_the_start_time_is_taken_before_collection_not_after():
    """started_at stamped at the end would make every run look instantaneous."""
    body = _body()
    start_assign = body.index("started_at =")
    first_call = body.index("for model in models:")
    assert start_assign < first_call


def test_the_old_runs_are_declared_rather_than_reconstructed():
    """Each pre-fix run is a named known finding with its reason."""
    pre_fix = ["2026-09-13-g0dm0d3-replicate", "2026-09-13-g0dm0d3-smoke",
               "2026-09-13-g0dm0d3-smoke2", "2026-09-13-truncation-proof"]
    for run in pre_fix:
        assert (run, "no-manifest") in V.KNOWN, "%s is not declared" % run
        why = V.KNOWN[(run, "no-manifest")]
        assert len(why) > 40, "%s has no real reason recorded" % run


def test_no_reconstructed_manifest_was_written_for_a_pre_fix_run():
    """A derived manifest would make the count gate compare a number to itself."""
    from studypaths import run_roots
    for root in run_roots():
        for run in ("2026-09-13-g0dm0d3-replicate", "2026-09-13-truncation-proof"):
            path = root / run / "manifest.json"
            if not path.exists():
                continue
            with path.open(encoding="utf-8") as fh:
                m = json.load(fh)
            assert m.get("reconstructed") is not True, (
                "%s carries a reconstructed manifest; the count check it enables is "
                "vacuous by construction" % run)


def test_the_validator_still_reports_these_as_findings_not_as_clean():
    """Declared is not the same as fixed. They must still be listed.

    Only meaningful where the run exists: the public mirror does not hold the
    replicate pair, so there it SKIPS rather than passing on an absent run.
    """
    import contextlib
    import io as _io
    import pytest
    from studypaths import run_roots
    if not any((root / "2026-09-13-g0dm0d3-replicate").is_dir() for root in run_roots()):
        pytest.skip("this tree does not hold the replicate run")
    buf = _io.StringIO()
    with contextlib.redirect_stdout(buf):
        V.main([])
    out = buf.getvalue()
    assert "known one(s)" in out
    assert "2026-09-13-g0dm0d3-replicate" in out
