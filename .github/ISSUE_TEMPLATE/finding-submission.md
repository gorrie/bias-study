---
name: Finding submission
about: Surface a pattern in the data — a drift, a sign flip, a new vendor-class signal
labels: finding
---

A delta is a finding only if its 95% CI excludes zero. Findings that also survive FDR
correction are candidates for the writeup.

**The run(s).** Which `data/<date>/` directory or directories the finding draws on.

**The claim.** One or two sentences stating the pattern.

**Supporting numbers / CIs.** The point estimate(s) with bootstrap 95% CIs, n, and — if
relevant — the FDR result. Paste the `scripts/ci_analysis.py` / `robustness_checks.py`
output that backs it.
