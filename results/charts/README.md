# `results/charts/` — generated figures

Every PNG in this directory is **regenerated from the data**, not hand-edited.
The script is `scripts/generate_charts.py`; the source data is `data/<run>/cross-method/`.
If a number in the writeup ever disagrees with a chart, the JSON is the source
of truth — re-run the generator.

## Files

| File | What it shows | Source | Embedded in writeup |
|------|---------------|--------|---------------------|
| `forest-plot-per-model.png` | Per-model A→B stance delta, baseline (ULTRAPLINIAN-4) vs anchor judge method, primary run | `data/2026-05-25-full/cross-method/per-method-summary.json` | [Rung 1 — the prompt](https://evilrobots.lol/research/ai-bias-audit/#prompt) |
| `agreement-heatmap.png` | Pairwise exact-match agreement matrix across all six judging methods, primary run | `data/2026-05-25-full/cross-method/cross-method-agreement.json` | — |
| `contamination-delta.png` | Per-model contamination delta (grok-solo − ULTRAPLINIAN-4) with bootstrap 95% CI error bars, primary run | `data/2026-05-25-full/cross-method/contamination-delta.json` | [The judges are not laundering the result](https://evilrobots.lol/research/ai-bias-audit/#judges) |
| `paraphrase-robustness.png` | Within-leg BH-FDR survivors across three paraphrases per neutral question | `data/2026-05-27-paraphrase/` | — |

The per-run `-2026-05-27-g0dm0d3.png` variants are the same three charts
computed against the pipeline-rung run instead of the main study; kept for
the pipeline-rung writeup section.

## Aesthetic

Dark background (`#0c0c0f`) to match the evilrobots.lol brand chrome. All
charts 1200×675 (X-card aspect ratio). Monospace font.
ACCENT colour (`#CC0000`, cold red) for the baseline; ACCENT2 (`#88ccff`)
for the anchor method.

## Regenerate

```bash
python scripts/generate_charts.py --all-charts                     # all default charts
python scripts/generate_charts.py --all-charts --out /some/dir     # override output
python scripts/generate_charts.py 2026-05-25-full                  # one run
```

Output directory defaults to `results/charts/` (this directory). The script
auto-detects `data/<run>/` (publication-canonical) vs `runs/<run>/` (internal
working copy) — same content, different directory name.

## Re-use

Charts are MIT-licensed with the rest of the repository. If you cite a
chart in a downstream piece, please link back to the repository or the
permalink at [evilrobots.lol/research/ai-bias-audit](https://evilrobots.lol/research/ai-bias-audit/).
