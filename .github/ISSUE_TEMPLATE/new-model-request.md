---
name: New model / vendor request
about: Propose a model or vendor family to add to the study corpus
labels: new-model
---

**Model id.** The exact identifier (e.g. an OpenRouter slug like `vendor/model-x`).

**Vendor / family.** Vendor and the class it belongs to (us-closed / european / chinese /
open-weight).

**OpenRouter-reachable?** Yes/no. If yes, adding it is usually a one-line entry in
`DEFAULT_FRONTIER` in `scripts/run_study.py` plus a class hint in `aggregate.py`. If it is a
new open-weight family for the abliteration leg, note that.

**Why.** What it adds to the corpus — a new vendor class, a new generation in an existing
arc, an open-weight check on a closed lean, etc.
