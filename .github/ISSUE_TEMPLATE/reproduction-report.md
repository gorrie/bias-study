---
name: Reproduction report
about: You re-ran a rung and want to report whether the published numbers replicated
labels: reproduction
---

Independent replication is the most valuable contribution. Confirmations *and*
failures-to-replicate are both wanted — a null replication is a finding.

**Run date.** The `data/<date>/` you produced.

**Models and judges.** Which models you ran and which judge panel you scored with.

**Which rung.** Prompt / pipeline / weights.

**Deltas vs. published.** Your per-model deltas with 95% CIs. Did the vendor-class
direction replicate? Did any FDR-surviving effect (Opus 4.7, Grok 4.3, GPT-4.1, Mistral
Large) hold?

**Environment.** OS, Python version, and — for the weight rung — GPU and abliteration mode.
