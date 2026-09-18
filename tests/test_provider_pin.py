"""A cell's replicates must differ by the draw and nothing else.

WHY THIS FILE EXISTS
--------------------
The 2026-09-16 I3 wave -- 372 sheets, 385 minutes -- came back with **36 cells
whose three replicates were served by different backends**. Worst case,
`deepseek-v4-flash-0731/A` was answered by OpenInference, Relace and Sail Research.

This study counts serving path as a same-version variant. It is one of the things
the floors MEASURE. So a cell straddling two backends confounds its condition
contrast with the routing, and `collection_check` refuses the run for it.

The record had carried a `provider` field since the arm was designed, with a
comment in `run_battery.py` naming this exact hazard:

    "one model id can be routed to different providers within a single sitting,
     and this study counts serving path as a same-version variant, so a floor
     computed across an unrecorded provider change is measuring two things."

It was recorded and nothing acted on it. **Recording is not controlling**, and the
run that proved it took six and a half hours.

Three things are tested here, because the fix has three parts that can each fail
quietly:

  1. the request carries the pin AND turns fallbacks off -- a pin that silently
     routes past itself is the unpinned behaviour wearing a field;
  2. the record keeps what was REQUESTED beside what SERVED, so a reroute is
     visible instead of looking like a deliberate choice;
  3. `collection_check` treats a pin that did not hold as a blocker.
"""
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import collection_check as C  # noqa: E402
import run_study as S  # noqa: E402


class _FakeResponse:
    status_code = 200

    def __init__(self, sink):
        self._sink = sink

    def json(self):
        return {"choices": [{"message": {"content": "1. Agree"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
                "provider": "Modal"}


def _capture_request(monkeypatch):
    """Run one call with requests.post stubbed, and return the JSON body it sent."""
    sent = {}

    def fake_post(url, headers=None, json=None, timeout=None, **kw):
        sent.update(json or {})
        return _FakeResponse(sent)

    monkeypatch.setattr(S.requests, "post", fake_post)
    return sent


def test_the_pin_reaches_the_request_with_fallbacks_off(monkeypatch):
    sent = _capture_request(monkeypatch)
    S._call_openrouter_once("m", [{"role": "user", "content": "x"}], "k",
                            provider="Modal")
    assert sent.get("provider") == {"order": ["Modal"], "allow_fallbacks": False}, sent


def test_no_pin_means_no_provider_field_at_all(monkeypatch):
    """An unconditional `provider: null` is not the same request as no provider key.

    Every arm collected before 2026-09-16 was gathered without it, and sending the
    field always would silently change what those arms are comparable to.
    """
    sent = _capture_request(monkeypatch)
    S._call_openrouter_once("m", [{"role": "user", "content": "x"}], "k")
    assert "provider" not in sent, sent


def _sheet(model, cond, seed, served, pinned=None):
    """A forced-choice sheet record.

    `schema` is not decoration: `analyse_sheets` selects on `compass-run/1` and returns
    {} for anything else, so that a judged run merges cleanly. A fixture without it
    exercises the early return and every assertion below becomes a KeyError -- which is
    the correct behaviour of the code and a wrong fixture, found the first time these
    ran.
    """
    r = {"schema": "compass-run/1",
         "model": model, "condition": cond, "shuffle_seed": seed,
         "provider": served, "valid": True, "n_answers": 60, "n_items": 60,
         "answers": [{"q": i, "position": 1 if i % 2 else 5} for i in range(1, 61)]}
    if pinned is not None:
        r["provider_pinned"] = pinned
    return r


def test_a_cell_split_across_backends_is_reported():
    """The original defect, on the shape the wave actually produced."""
    out = C.analyse_sheets([_sheet("m", "A", 11, "Relace"),
                            _sheet("m", "A", 22, "Sail Research"),
                            _sheet("m", "A", 33, "OpenInference")])
    assert out["cells_split_across_providers"] == 1
    assert any("MORE THAN ONE provider" in p for p in out["problems"])


def test_a_cell_held_to_one_backend_is_clean():
    out = C.analyse_sheets([_sheet("m", "A", 11, "Modal"),
                            _sheet("m", "A", 22, "Modal", pinned="Modal"),
                            _sheet("m", "A", 33, "Modal", pinned="Modal")])
    assert out["cells_split_across_providers"] == 0
    assert out["provider_pin_broken"] == 0
    assert not any("provider" in p for p in out["problems"])


def test_a_pin_that_did_not_hold_is_a_blocker():
    """allow_fallbacks is false, so this should be impossible -- which is why it is checked.

    A run whose pins were ignored looks MORE controlled than an unpinned one while
    being exactly as confounded, so silence here would be worse than no pin at all.
    """
    out = C.analyse_sheets([_sheet("m", "A", 11, "Modal"),
                            _sheet("m", "A", 22, "Together", pinned="Modal")])
    assert out["provider_pin_broken"] == 1
    assert any("PINNED to one backend and served by another" in p
               for p in out["problems"])


def test_an_unpinned_sheet_is_not_evidence_either_way():
    """The first sheet of a cell is unpinned on purpose -- it is what the pin is learned from."""
    out = C.analyse_sheets([_sheet("m", "A", 11, "Modal"),
                            _sheet("m", "A", 22, "Modal")])
    assert out["provider_pin_broken"] == 0


def test_the_wave_driver_learns_the_pin_from_the_record():
    """It must read the SERVED backend, not guess, and must not pin the local channel."""
    import run_i3_wave as W
    assert W._served_provider("no-such-run", "m", "A") is None
