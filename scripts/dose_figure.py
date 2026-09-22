#!/usr/bin/env python3
"""The dose figure: outcome against MEASURED perturbation, not the knob setting.

WHY THIS AXIS. `n_directions` 2/4/8 reads as 1x/2x/4x and is a measured 1.00x/2.26x/2.45x
relative Frobenius change against stock -- non-linear and saturating. Plotting an outcome
against the knob plots it against the wrong variable, which the result document argues at
length and then failed to draw.

WHY IT MATTERS LESS THAN IT DID. Under the pre-registered model judge no arm differs from
stock, so this figure's job is not to show a dose response. It is to show that there is not
one across a 2.45x range of actual weight change, with both compliance components visible
because the prereg requires them reported together.

Writes SVG. No matplotlib dependency -- this repository ships no plotting stack and adding
one for a two-panel chart is not worth the install surface.

    python scripts/dose_figure.py            # -> figures/dose-response.svg
    python scripts/dose_figure.py --check    # exit 1 if stale
"""
from __future__ import annotations

import argparse
import collections
import io
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
OUT = os.path.join(STUDY, "figures", "dose-response.svg")

#: label, tag, measured relative Frobenius change vs stock, build note
ARMS = [
    ("stock", "dose0-stock", 0.0, ""),
    ("n=1", "dose1-t205d28a", 5.20e-2, "205d28a"),
    ("n=2", "dose2", 6.58e-2, ""),
    ("n=4", "dose4", 1.48e-1, "05-27 build"),
    ("n=8", "dose8", 1.62e-1, ""),
]


def load(tag):
    p = os.path.join(STUDY, "runs", "refusal-ablation", f"dose-{tag}.judged.jsonl")
    if not os.path.exists(p):
        return None
    return {r["id"]: r for r in (json.loads(l) for l in io.open(p, encoding="utf-8") if l.strip())}


def stats():
    D = {}
    for lab, tag, x, note in ARMS:
        d = load(tag)
        if d is None:
            return None
        D[lab] = d
    ids = sorted(set.intersection(*[set(v) for v in D.values()]))
    base = D["stock"]
    types = sorted({base[i]["type"] for i in ids})
    bt = collections.defaultdict(list)
    for i in ids:
        bt[base[i]["type"]].append(i)

    def three(M, sel):
        s = [i for i in sel if base[i]["label"] == "safe"]
        u = [i for i in sel if base[i]["label"] == "unsafe"]
        if not s or not u:
            return None
        sc = 1 - sum(1 for i in s if M[i].get("judge_verdict") == "REFUSED") / len(s)
        uc = 1 - sum(1 for i in u if M[i].get("judge_verdict") == "REFUSED") / len(u)
        return sc, uc, sc - uc

    out = []
    for lab, tag, x, note in ARMS:
        sc, uc, d = three(D[lab], ids)
        rng = random.Random(20260920)
        boot = []
        for _ in range(2000):
            sel = [i for t in [rng.choice(types) for _ in types] for i in bt[t]]
            v = three(D[lab], sel)
            if v:
                boot.append(v[2])
        boot.sort()
        out.append({"label": lab, "x": x, "note": note, "safe": sc, "unsafe": uc,
                    "disc": d, "lo": boot[50], "hi": boot[1949]})
    return out


def svg(rows):
    W, H, PAD = 720, 470, 62
    xmax = max(r["x"] for r in rows) * 1.12
    def px(x): return PAD + (x / xmax) * (W - 2 * PAD)
    def py(v, top, bot, y0, y1): return y1 - (v - bot) / (top - bot) * (y1 - y0)

    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="ui-sans-serif,system-ui,sans-serif" font-size="11">',
         f'<rect width="{W}" height="{H}" fill="#fff"/>',
         f'<text x="{PAD}" y="22" font-size="13" font-weight="600">Refusal discrimination against measured weight change</text>',
         f'<text x="{PAD}" y="38" fill="#555">gemma-2-9b-it, XSTest 450 prompts, model-judge scored. No arm differs from stock.</text>']

    # band: no arm buildable below n=2 on the series tool
    xb = px(6.58e-2)
    s.append(f'<rect x="{PAD}" y="52" width="{xb-PAD}" height="{H-100}" fill="#f2f2f2"/>')
    s.append(f'<text x="{PAD+6}" y="66" fill="#999" font-size="10">no arm buildable at d6af36f</text>')

    # panel A: discrimination
    y0, y1 = 74, 236
    s.append(f'<text x="{PAD}" y="{y0-4}" font-weight="600">discrimination (safe − unsafe compliance)</text>')
    for v in (0.6, 0.7, 0.8):
        y = py(v, 0.85, 0.55, y0, y1)
        s.append(f'<line x1="{PAD}" y1="{y:.1f}" x2="{W-PAD}" y2="{y:.1f}" stroke="#eee"/>')
        s.append(f'<text x="{PAD-8}" y="{y+3:.1f}" text-anchor="end" fill="#777">{v:.2f}</text>')
    ys = py(rows[0]["disc"], 0.85, 0.55, y0, y1)
    s.append(f'<line x1="{PAD}" y1="{ys:.1f}" x2="{W-PAD}" y2="{ys:.1f}" stroke="#c00" stroke-dasharray="4 3" opacity=".5"/>')
    s.append(f'<text x="{W-PAD+3}" y="{ys+3:.1f}" fill="#c00" font-size="10">stock</text>')
    for r in rows:
        x, lo, hi = px(r["x"]), py(r["lo"], .85, .55, y0, y1), py(r["hi"], .85, .55, y0, y1)
        s.append(f'<line x1="{x:.1f}" y1="{lo:.1f}" x2="{x:.1f}" y2="{hi:.1f}" stroke="#333"/>')
        fill = "#fff" if r["note"] else "#333"
        shape = (f'<rect x="{x-4:.1f}" y="{py(r["disc"],.85,.55,y0,y1)-4:.1f}" width="8" height="8" fill="{fill}" stroke="#333"/>'
                 if r["note"] == "205d28a" else
                 f'<circle cx="{x:.1f}" cy="{py(r["disc"],.85,.55,y0,y1):.1f}" r="4" fill="{fill}" stroke="#333"/>')
        s.append(shape)
        s.append(f'<text x="{x:.1f}" y="{y1+14}" text-anchor="middle" fill="#555">{r["label"]}</text>')

    # panel B: both compliance components
    y0, y1 = 288, 400
    s.append(f'<text x="{PAD}" y="{y0-4}" font-weight="600">compliance, both components (prereg requires both)</text>')
    for v in (0.2, 0.6, 1.0):
        y = py(v, 1.05, 0.10, y0, y1)
        s.append(f'<line x1="{PAD}" y1="{y:.1f}" x2="{W-PAD}" y2="{y:.1f}" stroke="#eee"/>')
        s.append(f'<text x="{PAD-8}" y="{y+3:.1f}" text-anchor="end" fill="#777">{v:.1f}</text>')
    for key, col, nm in (("safe", "#1a7f37", "safe (n=250)"), ("unsafe", "#8250df", "unsafe (n=200)")):
        pts = " ".join(f'{px(r["x"]):.1f},{py(r[key],1.05,.10,y0,y1):.1f}' for r in rows)
        s.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="1.5"/>')
        for r in rows:
            s.append(f'<circle cx="{px(r["x"]):.1f}" cy="{py(r[key],1.05,.10,y0,y1):.1f}" r="3" fill="{col}"/>')
        yl = py(rows[-1][key], 1.05, .10, y0, y1)
        s.append(f'<text x="{W-PAD+4}" y="{yl+3:.1f}" fill="{col}" font-size="10">{nm}</text>')

    s.append(f'<line x1="{PAD}" y1="{y1}" x2="{W-PAD}" y2="{y1}" stroke="#333"/>')
    s.append(f'<text x="{(W)/2}" y="{y1+30}" text-anchor="middle" fill="#333">measured relative Frobenius change vs stock (NOT n_directions)</text>')
    s.append(f'<text x="{PAD}" y="{H-12}" fill="#777" font-size="10">open marker = 2026-05-27 build; square = built at tool revision 205d28a, a different instrument</text>')
    s.append("</svg>")
    return "\n".join(s) + "\n"


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    rows = stats()
    if rows is None:
        print("judged arms not on disk -- refusing to draw a figure from partial data")
        return 1
    text = svg(rows)
    if a.check:
        old = io.open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
        if old != text:
            print("dose-response.svg is stale. Run: python scripts/dose_figure.py")
            return 1
        print("dose-response.svg matches the judged arms")
        return 0
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(text)
    for r in rows:
        print(f"  {r['label']:6s} x={r['x']:.4f}  disc={r['disc']:.4f} [{r['lo']:+.3f},{r['hi']:+.3f}]"
              f"  safe={r['safe']:.3f} unsafe={r['unsafe']:.3f}")
    print(f"\nwrote {os.path.relpath(OUT, STUDY)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
