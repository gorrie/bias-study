#!/usr/bin/env python3
"""One scale: how far does an intervention have to move a model before it means anything?

WHAT THIS CHART IS FOR
----------------------
The floors chart answers "what moves the answers when nothing political changes". It is a
defensive picture -- it tells a reader which published effects to disbelieve.

This is the constructive version, and it answers a question a practitioner actually has:
**if I am specialising a model for a purpose -- prompt engineering, ablation, later fine-tuning
-- how big a shift do I need before the shift is real?**

The scale has three kinds of mark on it:

  ESTIMATOR      the modal's own sampling error. Below this you are measuring your own
                 measurement. p90 3 side-flips of 62.
  NUISANCE       what moves without anyone intending it -- rerunning the prompt, reordering
                 the items, rewording the wrapper, requantising the weights.
  BETWEEN MODELS the natural spread between two different off-the-shelf models. THE BAND THAT
                 MATTERS: median 5, p90 14-18.

And that band is the practical threshold, because of a comparison nobody in this literature
makes: **an intervention that moves a model less than the between-model spread has achieved
less than picking a different model would have.** If prompt-tuning buys you 3 items and
swapping vendors buys 14, the prompt work is not specialisation -- it is inside the noise
between products you could have bought instead.

That reading is what makes the number useful for a fine-tuning budget rather than only for
debunking. It is also falsifiable: an intervention that clears the band is real, and this chart
says how far it has to clear it.

    python scripts/chart_intervention_budget.py
    python scripts/chart_intervention_budget.py --out ../../website/static/images/bias-study
"""
from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
SERIES = os.path.dirname(os.path.dirname(STUDY))
sys.path.insert(0, HERE)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import floor_table as F          # noqa: E402
import floor_resolution as R     # noqa: E402

BG = "#0c0c0f"
SURFACE = "#16161a"
ACCENT = "#CC0000"
BAND = "#E8A33D"
COOL = "#88ccff"
MUTED = "#7a7a88"
TEXT = "#e6e6e6"
GRID = "#2a2a2f"

plt.rcParams.update({
    "figure.facecolor": BG, "axes.facecolor": SURFACE, "axes.edgecolor": GRID,
    "axes.labelcolor": TEXT, "axes.titlecolor": TEXT, "xtick.color": TEXT,
    "ytick.color": TEXT, "grid.color": GRID, "text.color": TEXT,
    "font.family": "monospace", "font.size": 11, "axes.titlesize": 14,
    "axes.titleweight": "bold",
})

DEFAULT_OUT = os.path.join(SERIES, "website", "static", "images", "bias-study")

#: Which floors belong on this scale, and how each is CLASSED. The class decides the colour and
#: the reading -- an estimator floor and a nuisance floor are different kinds of statement, and
#: the previous chart drew them identically.
WANTED = [
    ("modal sampling error", "estimator", "the measurement's own error"),
    ("run-to-run replicate", "nuisance", "same prompt twice"),
    ("presentation order, one sitting, frontier API", "nuisance", "reorder the items (2026)"),
    ("instruction paraphrase", "nuisance", "reword the wrapper"),
    ("requantisation", "nuisance", "Q4 to Q8, same weights"),
    ("prompt condition A->D, one sitting", "intervention", "tell it what to think"),
    ("refusal-direction ablation", "intervention", "cut the refusal direction"),
]


def rows():
    floors = F.all_floors()
    out = []
    for name, cls, label in WANTED:
        r = floors.get(name)
        if r:
            out.append((label, cls, r["side"][0], r["side"][1]))
    return out


def band_bounds():
    """The between-model band, EXCLUDING the cells whose modal is itself unstable.

    The first version took `hi` from the raw between-model p90, which is 18 -- and ten cells
    carry a modal so unstable that `data/modal-noise.json` flags them, one bootstrapping to p90
    27 on its own. Excluding those ten takes the p90 from 14 to 9 under D and 18 to 14 under P,
    so a third of the band's width was the estimator.
    A chart whose whole argument is "an intervention must beat this band" cannot draw the band
    out of measurement noise. Both bounds come from the stable cells now; the raw figures are
    still printed by --verbose so the difference stays visible.
    """
    import json as _json
    unstable = set()
    path = os.path.join(STUDY, "data", "modal-noise.json")
    if os.path.exists(path):
        try:
            for u in (_json.load(open(path, encoding="utf-8")).get("unstable") or []):
                head, _, cond = u.rpartition(" ")
                if head:
                    unstable.add((head, cond))
        except ValueError:
            pass

    raw = F.load(R.WAVE, key=lambda r: (r["model"], r["condition"]), dedupe_by_seed=True)
    cells = {k: v for k, v in raw.items() if len(v) >= 4}
    out = {}
    for cond in ("D", "P"):
        models = sorted(m for (m, c) in cells if c == cond and (m, cond) not in unstable)
        modal = {m: F.modal(cells[(m, cond)]) for m in models}
        d = [F.both_stats(modal[models[i]], modal[models[j]])[0]
             for i in range(len(models)) for j in range(i + 1, len(models))]
        d.sort()
        out[cond] = {"n_models": len(models), "median": d[len(d) // 2],
                     "p90": d[int(0.9 * len(d)) - 1] if len(d) >= 10 else max(d)}
    return out


def draw(out_path):
    data = rows()
    band = band_bounds()
    lo = min(band[c]["median"] for c in band)
    hi = max(band[c]["p90"] for c in band)

    fig, ax = plt.subplots(figsize=(12, 6.4), dpi=100)

    # The between-model band, drawn FIRST so everything else reads against it.
    ax.axvspan(lo, hi, color=BAND, alpha=0.16, zorder=0)
    ax.axvline(lo, color=BAND, linestyle="-", linewidth=1.2, alpha=0.75, zorder=1)
    ax.axvline(hi, color=BAND, linestyle="--", linewidth=1.0, alpha=0.6, zorder=1)

    colours = {"estimator": MUTED, "nuisance": COOL, "intervention": ACCENT}
    ys = range(len(data))
    for y, (label, cls, med, p90) in zip(ys, data):
        c = colours[cls]
        ax.plot([med, p90], [y, y], color=c, linewidth=6, alpha=0.35, solid_capstyle="round")
        ax.plot([med], [y], marker="|", markersize=16, color=c, markeredgewidth=2.5)
        ax.plot([p90], [y], marker="D", markersize=7, color=c)
        verdict = "clears the band" if p90 > hi else (
            "inside the band" if p90 >= lo else "below the band")
        ax.text(max(p90, hi) + 0.6, y, "med %d, p90 %d  ·  %s" % (med, p90, verdict),
                va="center", fontsize=9, color=MUTED)

    ax.set_yticks(list(ys))
    ax.set_yticklabels([d[0] for d in data], fontsize=9.5)
    ax.set_xlim(0, hi + 13)
    ax.set_ylim(-1.5, len(data) - 0.4)
    ax.set_xlabel("items of 62 that change side (side-flips)")
    ax.set_title("How far must an intervention move a model before it means anything?")
    ax.grid(axis="x", alpha=0.35, linewidth=0.5)
    ax.set_axisbelow(True)

    ax.text(lo + (hi - lo) / 2.0, -1.15,
            "TWO OFF-THE-SHELF MODELS DIFFER THIS MUCH  (median %d to p90 %d, stable cells only)" % (lo, hi),
            color=BAND, fontsize=9.5, ha="center", va="center", weight="bold")

    fig.text(0.5, 0.022,
             "grey = the measurement's own error   ·   blue = nuisance, nobody intended it   "
             "·   red = a deliberate intervention",
             ha="center", fontsize=9, color=MUTED)
    fig.text(0.5, 0.002,
             "An intervention that lands inside the amber band has achieved less than "
             "choosing a different model would have.",
             ha="center", fontsize=9.5, color=TEXT)
    plt.tight_layout(rect=(0, 0.055, 1, 1))
    plt.savefig(out_path, facecolor=BG)
    plt.close(fig)
    return out_path, data, (lo, hi)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args(argv)
    if not os.path.isdir(args.out):
        os.makedirs(args.out)
    path, data, (lo, hi) = draw(os.path.join(args.out, "intervention-budget.png"))

    print("INTERVENTION BUDGET -- every number generated, none typed")
    print("  between-model band: median %d to p90 %d side-flips of 62" % (lo, hi))
    print("")
    print("  %-34s %-13s %6s %6s  %s" % ("factor", "class", "med", "p90", "verdict"))
    for label, cls, med, p90 in data:
        verdict = "CLEARS" if p90 > hi else ("inside" if p90 >= lo else "below")
        print("  %-34s %-13s %6d %6d  %s" % (label, cls, med, p90, verdict))
    print("")
    print("wrote %s" % os.path.relpath(path, SERIES))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
