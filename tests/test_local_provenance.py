"""Abliteration provenance must come from the weights, not from a label.

WHY THIS FILE EXISTS
--------------------
`run_local.py` recorded whether the ablation had been applied as

    "obliteratus_applied": ("ablit" in args.label.lower())

a substring of a USER-SUPPLIED LABEL. Nothing inspected the weights. Point
--model-path at the stock directory with --label "qwen-abliterated" and the record
asserts the ablation was applied; use --label "gemma-ablated" on a genuinely
abliterated model and it records False.

The abliteration skill's own hard lesson is that "an abliterated run that silently
loads stock = a fake null", and nothing mechanical stood behind it.

Separately, the file sampled at temperature 0.7 with `torch.manual_seed` appearing
NOWHERE, so the two arms of a pair drew from different RNG streams. Measured
consequence: between-arm Jaccard of 0.339 (llama-3.1-8b) and 0.333 (mistral-7b)
sit INSIDE the 0.303-0.392 band this project measured for one model resampled
against itself. Two of four families were certified as "text rewrote ~66%" on
sampling noise.
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import run_local as R  # noqa: E402


def _model_dir(size=100, arch="x"):
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "config.json"), "w", encoding="utf-8") as fh:
        json.dump({"architectures": [arch]}, fh)
    with open(os.path.join(d, "model.safetensors"), "wb") as fh:
        fh.write(b"0" * size)
    return d


def test_fingerprint_discriminates_different_weights():
    """Two arms of a pair MUST differ here, or the abliterated arm loaded stock."""
    a, b = _model_dir(size=100), _model_dir(size=101)
    assert R.weight_fingerprint(a)["sha256_12"] != R.weight_fingerprint(b)["sha256_12"]


def test_fingerprint_is_stable_across_reads():
    """A fingerprint that changed per read would be useless for comparison."""
    d = _model_dir()
    assert R.weight_fingerprint(d)["sha256_12"] == R.weight_fingerprint(d)["sha256_12"]


def test_fingerprint_notices_a_changed_config():
    """Same file sizes, different architecture, must not collide."""
    a, b = _model_dir(arch="LlamaForCausalLM"), _model_dir(arch="MistralForCausalLM")
    assert R.weight_fingerprint(a)["sha256_12"] != R.weight_fingerprint(b)["sha256_12"]


def test_fingerprint_reports_an_error_rather_than_a_fake_digest():
    """A missing directory must not produce a plausible-looking hash."""
    fp = R.weight_fingerprint(os.path.join(tempfile.gettempdir(), "does-not-exist-9999"))
    assert "sha256_12" not in fp or fp.get("n_files") == 0


def test_a_seed_argument_exists_and_is_applied():
    """No seed is why the weight rung's text-change claim sat in its own noise."""
    import inspect
    src = inspect.getsource(R)
    assert '"--seed"' in src, "run_local.py must accept a seed"
    assert "torch.manual_seed" in src, "the seed must actually be applied"


def test_label_derived_provenance_is_labelled_as_such():
    """Keeping the old field is fine; presenting it as evidence is not."""
    import inspect
    src = inspect.getsource(R)
    assert "obliteratus_applied_label_derived" in src, (
        "the label-derived flag must say it is label-derived, so a reader does not "
        "mistake it for an inspection of the weights")
    assert "weight_fingerprint" in src
