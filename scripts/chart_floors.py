#!/usr/bin/env python3
"""The floors chart: every nuisance factor beside the deliberate manipulation.

WHY THIS ONE PICTURE
--------------------
The 2026-08-31 re-measurement is the strongest material this study has and it ships with **no
visualization at all** -- 19,000 characters of argument on the public research page, zero
images, while the May study beside it has two. The argument is also the most chart-shaped thing
here: seven factors, each with a median / p90 / max, whose whole point is that the ones nobody
calls political are the size of the one that is.

A table states that. A chart makes it unarguable: `prompt condition A->D` is the deliberate
manipulation, and `same-version variants` and `presentation order` reach past it.

EVERY NUMBER IS GENERATED, none typed. It reads `floor_table`'s own functions, so the chart
cannot drift from the paper's table -- the defect this project keeps finding in its own
surfaces. Regenerate it whenever a floor moves; `tools/freshness_gate.py` has no image check,
so the discipline is to run this in the same commit as the floor that changed.

    python scripts/chart_floors.py
    python scripts/chart_floors.py --out ../../website/static/images/bias-study

Reads no network, no key. Arithmetic already on disk.
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

import floor_table as F  # noqa: E402

# Evil Robots brand chrome, matching scripts/generate_charts.py rather than inventing a
# second palette. Two chart styles on one page reads as two projects.
BG = "#0c0c0f"
SURFACE = "#16161a"
ACCENT = "#CC0000"
ACCENT2 = "#88ccff"
MUTED = "#7a7a88"
TEXT = "#e6e6e6"
GRID = "#2a2a2f"

plt.rcParams.update({
    "figure.facecolor": BG,
    "axes.facecolor": SURFACE,
    "axes.edgecolor": GRID,
    "axes.labelcolor": TEXT,
    "axes.titlecolor": TEXT,
    "xtick.color": TEXT,
    "ytick.color": TEXT,
    "grid.color": GRID,
    "text.color": TEXT,
    "font.family": "monospace",
    "font.size": 11,
    "axes.titlesize": 14,
    "axes.titleweight": "bold",
})

DEFAULT_OUT = os.path.join(SERIES, "website", "static", "images", "bias-study")

#: The rows that ARE a deliberate political manipulation, drawn in the accent colour so the
#: comparison is visible without reading the caption.
#:
#: BOTH manipulation rows, matched by prefix. The one-sitting row IS the deliberate
#: manipulation and was rendering BLUE -- "a factor nobody calls political" -- because this
#: matched one exact string. A legend that miscolours the thing the chart is about is worse
#: than no legend.
MANIPULATION = "prompt condition A->D"


def is_manipulation(name):
    return name.startswith(MANIPULATION)


def floors():
    """Every measured floor, from floor_table's own functions. Nothing typed."""
    # floor_table.ALL_FLOORS, not a third copy of the list. This one, power.py and
    # key_numbers.floors() each enumerated the floors themselves, so a row added to the table
    # appeared in the paper and in NONE of them -- the chart on the public page would have kept
    # plotting six rows while the paper printed seven, and nothing would have said so.
    rows = [f for f in (fn() for fn in F.ALL_FLOORS) if f]
    return sorted(rows, key=lambda r: r["side"][1])


def draw(rows, out_path):
    labels = ["%s\n%d pairs" % (r["name"], r["n"]) for r in rows]
    ys = range(len(rows))
    fig, ax = plt.subplots(figsize=(12, 6.75), dpi=100)

    for y, r in zip(ys, rows):
        med, p90, mx = r["side"]
        is_manip = is_manipulation(r["name"])
        colour = ACCENT if is_manip else ACCENT2
        # median-to-max as the bar, p90 marked, median marked. Three numbers, one row --
        # the table's own columns rather than a summary that loses two of them.
        ax.barh(y, mx - med, left=med, height=0.5, color=colour, alpha=0.30,
                edgecolor=colour, linewidth=1.0)
        ax.plot([med], [y], marker="|", markersize=18, color=colour, markeredgewidth=2.5)
        ax.plot([p90], [y], marker="D", markersize=7, color=colour)
        # Same disclosure the table carries with a dagger: under ten pairs the nearest-rank
        # 90th percentile IS the maximum, so the row prints one number twice. Silent here it
        # would read as two statistics agreeing.
        note = "med %d · p90 %d · max %d" % (med, p90, mx)
        if r.get("p90_is_max") and r.get("small_n"):
            note += "  † p90 = max at n<10"
        ax.text(mx + 0.4, y, note, va="center", fontsize=9, color=MUTED)

    ax.set_ylim(-1.1, len(rows) - 0.4)
    ax.set_yticks(list(ys))
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("items of 62 that cross the agree/disagree boundary (side-flips)")
    ax.set_title("What moves the answers when nothing political changes")
    ax.set_xlim(0, max(r["side"][2] for r in rows) + 9)
    ax.grid(axis="x", alpha=0.35, linewidth=0.5)
    ax.set_axisbelow(True)

    # TWO LINES, LABELLED, because there are two manipulation rows and they disagree.
    #
    # This drew one line at the pooled row's p90 and called it "the deliberate manipulation",
    # which now hides the thing a reader most needs: measured under one protocol in one sitting
    # the same manipulation is 7, not 15, and 15 is one bimodal model (grok-4.5) away from 8.
    # A single reference line invites the reader to treat whichever number it marks as the
    # scale, and the honest picture is that the scale depends on how it was collected.
    for r in sorted((r for r in rows if is_manipulation(r["name"])),
                    key=lambda r: r["side"][1]):
        x = r["side"][1]
        pooled = r["name"] == MANIPULATION
        ax.axvline(x, color=ACCENT, linestyle="--", linewidth=1.0,
                   alpha=0.8 if pooled else 0.45)
        ax.text(x - 0.4, -0.62 if pooled else -0.92,
                "%s p90 %d →" % ("pooled" if pooled else "one sitting", x),
                color=ACCENT, fontsize=8.5, va="center", ha="right",
                alpha=1.0 if pooled else 0.75)

    fig.text(0.5, 0.015,
             "red = an instruction demanding commitment instead of balance, measured two ways. "
             "blue = factors nobody calls political.",
             ha="center", fontsize=9, color=MUTED)
    plt.tight_layout(rect=(0, 0.04, 1, 1))
    plt.savefig(out_path, facecolor=BG)
    plt.close(fig)
    return out_path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=DEFAULT_OUT, help="directory for the PNG")
    args = ap.parse_args(argv)

    rows = floors()
    if not rows:
        print("no floors measurable -- is runs/ present?")
        return 1
    if not os.path.isdir(args.out):
        os.makedirs(args.out)
    path = draw(rows, os.path.join(args.out, "measurement-floors.png"))

    print("MEASUREMENT FLOORS -- drawn from floor_table, nothing typed")
    for r in rows:
        print("  %-28s %5d pairs   med %2d  p90 %2d  max %2d"
              % (r["name"], r["n"], *r["side"]))
    print()
    print("wrote %s" % os.path.relpath(path, SERIES))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
