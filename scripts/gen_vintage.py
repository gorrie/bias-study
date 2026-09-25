#!/usr/bin/env python3
"""Record each model's release date, so every claim in this study can be read by generation.

WHY THIS EXISTS
---------------
This study's subject is how a measured political position moves. Every figure it reports is
CROSS-SECTIONAL -- one panel, one moment -- and `FINDINGS-2026-09-17-battery.md` §5 states the
reason plainly: on the models this corpus held, **vintage, quantisation and serving path all
moved together**, so nothing separated them. Every old model was a local quantised build and
every new one was a hosted API. T9 ("open weights behave differently from closed") is recorded
as ORPHANED for exactly that reason.

The 2026-09-18 roster extension breaks the confound. It added 2024-vintage models served over
an API -- `google/gemma-2-27b-it` (2024), `meta-llama/llama-3.3-70b-instruct`,
`cohere/command-a` -- against which the corpus already holds 2024-generation LOCAL builds of
the same families. Serving path and vintage can be told apart for the first time, and a
generation axis exists within the hosted models with serving path held constant.

WHY A FILE AND NOT A LIVE LOOKUP
--------------------------------
`roster_gap.catalogue()` reads release dates from the live OpenRouter catalogue. That is right
for finding gaps and wrong for analysis: a listing can be withdrawn, re-dated or re-slugged,
and a figure that changes because a vendor edited a catalogue entry is not reproducible. This
writes the dates into the corpus, once, with the date it was taken.

`--check` exits 1 when a model in `runs/` has no recorded vintage, so the file cannot silently
fall behind the roster.

    python scripts/gen_vintage.py
    python scripts/gen_vintage.py --check

Exit 0 current, 1 stale or incomplete.
"""
from __future__ import annotations

import argparse
import datetime
import glob
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import studypaths as _SP

TARGET = os.path.join(_SP.STUDY_DIR, "data", "model-vintage.json")

#: Generation bands. Boundaries are CALENDAR dates, fixed here before any figure is cut by
#: them, so a band cannot be chosen to make a contrast come out. A model is placed by its
#: release date, never by its name or its size.
BANDS = (
    ("2024-or-earlier", None, "2025-01-01"),
    ("2025", "2025-01-01", "2026-01-01"),
    ("2026", "2026-01-01", None),
)

#: Local builds carry no catalogue entry. Their vintage is the upstream weights' release, and
#: it is recorded by hand because ollama tags do not carry one. Every entry here names the
#: base model the tag serves, so the claim is checkable rather than asserted.
LOCAL_VINTAGE = {
    "gemma2:latest": ("2024-06-27", "Gemma 2 9B"),
    "gemma2:9b-instruct-q8_0": ("2024-06-27", "Gemma 2 9B"),
    "llama3.1:8b": ("2024-07-23", "Llama 3.1 8B"),
    "llama3.1:8b-instruct-q8_0": ("2024-07-23", "Llama 3.1 8B"),
    "llama3.2:latest": ("2024-09-25", "Llama 3.2 3B"),
    "llama3.2:3b-instruct-q8_0": ("2024-09-25", "Llama 3.2 3B"),
    "mistral:latest": ("2023-09-27", "Mistral 7B v0.1 lineage"),
    "mistral:7b-instruct-q8_0": ("2023-09-27", "Mistral 7B Instruct"),
    "qwen2.5:14b": ("2024-09-19", "Qwen2.5 14B"),
    "qwen2.5:14b-instruct-q8_0": ("2024-09-19", "Qwen2.5 14B"),
    "phi4:latest": ("2024-12-12", "Phi-4 14B"),
    # A GGUF requantisation of Gemma 4 12B held locally. Dated to the upstream Gemma 4
    # release, not to the quantiser's upload, for the same reason every other local entry is:
    # the subject is the weights, and the repack is a serving decision.
    "hf.co/lmstudio-community/gemma-4-12B-it-GGUF:Q4_K_M": ("2026-03-10", "Gemma 4 12B"),
    # The abliterated builds, dated 2026-09-20 against the weights each was DERIVED FROM.
    # Abliteration edits the weights, so this is not the "repack is a serving decision" case
    # above and the reasoning is different: the band answers WHICH GENERATION a model belongs
    # to, and projecting out a refusal direction does not move a build into the next one. The
    # transform is recorded as its own class (the abliterated panel), not as a vintage. Every
    # base below is the dated catalogue sibling named in the tag itself, so each row is
    # checkable rather than asserted -- `qwen/qwen3.8-27b` 2026-08-14, Gemma 4 12B 2026-03-10
    # (the entry directly above), Phi-4 14B and Qwen2.5 14B as already recorded here.
    "hf.co/lmstudio-community/Qwen3.8-27B-GGUF:Q4_K_M": ("2026-08-14", "Qwen3.8 27B"),
    "hf.co/OBLITERATUS/Qwen3.8-27B-OBLITERATED:Q4_K_M": ("2026-08-14", "Qwen3.8 27B"),
    "hf.co/0bserverx/Qwen3.8-27B-Heretic-Abliterated-Uncensored-GGUF:Q4_K_M":
        ("2026-08-14", "Qwen3.8 27B"),
    "hf.co/OBLITERATUS/Gemma-4-12B-OBLITERATED:Q4_K_M": ("2026-03-10", "Gemma 4 12B"),
    "hf.co/culturerevolt/gemma-4-12b-heretic-abliterated-GGUF:Q4_K_M":
        ("2026-03-10", "Gemma 4 12B"),
    "huihui_ai/phi4-abliterated:latest": ("2024-12-12", "Phi-4 14B"),
    "huihui_ai/qwen2.5-abliterate:14b": ("2024-09-19", "Qwen2.5 14B"),
}

#: Hosted listings the catalogue does not date, resolved by hand against the dated sibling
#: whose weights they serve. Recorded here rather than left `unknown`, because an unknown
#: vintage silently drops a model from every generation contrast.
HOSTED_VINTAGE = {
    # The undated alias of `qwen/qwen3.8-max-0902`, which the catalogue dates.
    "qwen/qwen3.8-max": ("2026-09-03", "alias of qwen3.8-max-0902"),
}


def band_of(iso_date):
    if not iso_date:
        return "unknown"
    for name, lo, hi in BANDS:
        if (lo is None or iso_date >= lo) and (hi is None or iso_date < hi):
            return name
    return "unknown"


def corpus_models():
    models = set()
    for path in glob.glob(os.path.join(_SP.STUDY_DIR, "runs", "**", "*.jsonl"),
                          recursive=True):
        with io.open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if _SP.is_run_record(rec) and rec.get("model"):
                    models.add(rec["model"])
    return models


def build():
    out = {
        "_what": "Release date and generation band per model, so every figure in this study "
                 "can be read by model generation rather than only as a cross-section.",
        "_why_not_live": "Taken once from the OpenRouter catalogue and written down. A figure "
                         "that changes because a vendor re-dated a listing is not reproducible.",
        "_bands": [{"name": n, "from": lo, "before": hi} for n, lo, hi in BANDS],
        "_bands_fixed_before_use": "Calendar boundaries, fixed before any contrast was cut by "
                                   "them, so a band cannot be chosen to make a result.",
        "_local_note": "Local ollama tags carry no catalogue date; their vintage is the "
                       "upstream weights' release and the base model is named for checking.",
        "taken": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
        "models": {},
    }
    try:
        import roster_gap as RG
        cat = {e["id"]: e for e in RG.catalogue()}
    except Exception:
        cat = {}

    for model in sorted(corpus_models()):
        if model in LOCAL_VINTAGE:
            iso, base = LOCAL_VINTAGE[model]
            out["models"][model] = {"released": iso, "band": band_of(iso),
                                    "served": "local", "base": base,
                                    "source": "upstream release, recorded by hand"}
            continue
        if model in HOSTED_VINTAGE:
            iso, base = HOSTED_VINTAGE[model]
            out["models"][model] = {"released": iso, "band": band_of(iso),
                                    "served": "hosted", "base": base,
                                    "source": "resolved by hand against a dated sibling"}
            continue
        entry = cat.get(model)
        created = (entry or {}).get("created")
        if created:
            iso = datetime.datetime.fromtimestamp(
                created, datetime.timezone.utc).strftime("%Y-%m-%d")
            out["models"][model] = {"released": iso, "band": band_of(iso),
                                    "served": "hosted", "source": "openrouter catalogue"}
        else:
            out["models"][model] = {"released": None, "band": "unknown",
                                    "served": "hosted" if "/" in model else "local",
                                    "source": "NOT FOUND -- record it by hand"}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)

    if a.check:
        if not os.path.exists(TARGET):
            print("data/model-vintage.json has not been built. Run: "
                  "python scripts/gen_vintage.py")
            return 1
        have = json.load(io.open(TARGET, encoding="utf-8"))
        known = set(have.get("models") or {})
        missing = sorted(corpus_models() - known)
        unknown = sorted(m for m, v in (have.get("models") or {}).items()
                         if v.get("band") == "unknown")
        if missing:
            print("%d model(s) in runs/ have NO recorded vintage:" % len(missing))
            for m in missing[:20]:
                print("    %s" % m)
            print("Run: python scripts/gen_vintage.py")
            return 1
        if unknown:
            print("%d model(s) carry an UNKNOWN release date, so no figure may be cut by "
                  "generation until they are recorded by hand:" % len(unknown))
            for m in unknown[:20]:
                print("    %s" % m)
            return 1
        bands = {}
        for v in have["models"].values():
            bands[v["band"]] = bands.get(v["band"], 0) + 1
        print("every model in runs/ has a recorded vintage: %s"
              % ", ".join("%s %d" % kv for kv in sorted(bands.items())))
        return 0

    out = build()
    with io.open(TARGET, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    bands = {}
    served = {}
    for v in out["models"].values():
        bands[v["band"]] = bands.get(v["band"], 0) + 1
        served[v["served"]] = served.get(v["served"], 0) + 1
    print("wrote %s -- %d models" % (os.path.basename(TARGET), len(out["models"])))
    print("  by band:   %s" % ", ".join("%s %d" % kv for kv in sorted(bands.items())))
    print("  by serving: %s" % ", ".join("%s %d" % kv for kv in sorted(served.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
