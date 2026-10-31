"""Check which CSV pressure column belongs to which sensor on the insole diagram.

Why this exists: the dataset documents the sensors only as "PressureSensor 0-31"
and shows a numbered diagram (insoles-number.jpeg, labels 1-32). The link between
the two was not documented, so we TEST the natural guess
(CSV index i  ->  diagram label i+1, left file -> left diagram, right -> right).

Two independent tests on the real recordings, each compared with shuffled layouts:
  1. Heel-to-toe timing. In each step the heel loads first and the toes last, so a
     sensor's average timing inside a step should follow its position along the foot.
  2. Neighbours move together. Sensors that sit close on the diagram should have
     more similar load patterns than distant ones.

The result is EVIDENCE for the mapping, not confirmation from the dataset authors.

Run from the project root (needs: pip install scipy pillow matplotlib):

    python research/verify_sensor_layout.py

Writes backend/sensor_layout.json (used by the app) and outputs/layout_check.png
(detected sensors with their labels; compare it with insoles-number.jpeg).
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
from scipy import ndimage as ndi
from scipy.spatial.distance import pdist
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from backend import config  # noqa: E402

IMAGE = config.DATASET_DIR / "insoles-number.jpeg"
OUT_JSON = ROOT / "backend" / "sensor_layout.json"
OUT_PNG = ROOT / "outputs" / "layout_check.png"
RNG = np.random.default_rng(0)

# Label numbers read by eye from insoles-number.jpeg (approximate pixel centres).
# They are only used to NAME the dots found by the detector below; the positions
# used by the app come from the detector. Check outputs/layout_check.png.
SEED_LEFT = {1:(182,53),4:(116,86),17:(242,91),20:(175,122),2:(74,151),18:(263,164),3:(130,189),19:(201,200),8:(47,229),24:(270,250),5:(114,262),21:(194,278),10:(26,306),6:(97,334),22:(256,326),7:(173,345),9:(22,385),11:(125,399),23:(238,399),12:(53,460),15:(67,532),16:(65,611),13:(72,694),29:(146,730),14:(77,775),27:(205,772),30:(146,809),32:(79,857),26:(214,853),28:(146,880),31:(97,935),25:(198,935)}
SEED_RIGHT = {32:(501,53),16:(567,86),29:(440,91),13:(508,122),14:(609,151),31:(420,164),15:(553,189),30:(482,200),12:(636,229),28:(412,250),9:(569,262),25:(489,278),8:(657,306),26:(426,326),10:(586,334),11:(510,345),6:(660,385),27:(445,399),5:(558,399),7:(630,460),4:(616,532),1:(618,611),2:(611,694),18:(537,730),3:(606,775),23:(478,772),19:(537,809),20:(604,857),22:(469,853),24:(537,880),21:(484,935),17:(586,935)}


def detect_dots():
    """Centres of the 64 black sensor dots (all the same size; digits are far smaller)."""
    gray = np.array(Image.open(IMAGE).convert("L"))
    labelled, n = ndi.label(gray < 100)
    areas = ndi.sum(np.ones_like(gray), labelled, range(1, n + 1))
    keep = [i + 1 for i, a in enumerate(areas) if a > 150]
    if len(keep) != 64:
        raise SystemExit(f"Expected 64 sensor dots, found {len(keep)}")
    centres = ndi.center_of_mass(np.ones_like(gray), labelled, keep)
    return np.array([(x, y) for y, x in centres]), gray.shape[1]


def name_dots(dots, seeds):
    """Give each detected dot its label (nearest seed, one-to-one)."""
    out = {}
    for label, (sx, sy) in seeds.items():
        d = np.hypot(dots[:, 0] - sx, dots[:, 1] - sy)
        j = int(d.argmin())
        if d[j] > 20:
            raise SystemExit(f"No dot near label {label}")
        out[label] = tuple(dots[j])
    if len({v for v in out.values()}) != 32:
        raise SystemExit("Two labels matched the same dot")
    return out


def load_side(side):
    """Per-frame sensor shares (for the neighbour test) and stance timings."""
    timing_num, timing_den, stances, shares = np.zeros(32), np.zeros(32), 0, []
    for p in range(1, 16):
        for t in range(1, 11):
            f = config.DATASET_DIR / f"P{p}" / f"M{t}" / f"M{t}_Preassure_{side}.csv"
            if not f.exists():
                continue
            P = pd.read_csv(f)[config.SENSOR_COLUMNS].to_numpy(float)
            s = P.sum(1)
            on = s > 0.25 * np.percentile(s, 95)
            if on.any():
                shares.append(P[on] / P[on].sum(1, keepdims=True))
            i = 0
            while i < len(on):
                if not on[i]:
                    i += 1
                    continue
                j = i
                while j < len(on) and on[j]:
                    j += 1
                if j - i >= 6 and i > 0 and j < len(on):      # complete steps only
                    seg = P[i:j] - P[i:j].min(0)
                    tt = np.linspace(0, 1, j - i)[:, None]
                    timing_num += (seg * tt).sum(0)
                    timing_den += seg.sum(0)
                    stances += 1
                i = j
    return timing_num / np.maximum(timing_den, 1e-9), np.vstack(shares), stances


def run_tests(side, positions):
    """positions: {label: (x, y)}. Hypothesis: CSV index i -> label i+1."""
    timing, shares, stances = load_side(side)
    xy = np.array([positions[i + 1] for i in range(32)], float)
    # Test 1: later in the step <-> nearer the toes (smaller y) => negative rho
    rho_t = spearmanr(timing, xy[:, 1]).statistic
    null_t = np.array([spearmanr(timing, RNG.permutation(xy[:, 1])).statistic for _ in range(3000)])
    # Test 2: closer on the diagram <-> more similar load share => negative rho
    corr = np.corrcoef(shares.T)[np.triu_indices(32, 1)]
    rho_n = spearmanr(corr, pdist(xy)).statistic
    null_n = np.array([spearmanr(corr, pdist(xy[RNG.permutation(32)])).statistic for _ in range(3000)])
    return {
        "steps_used": int(stances), "loaded_frames_used": int(len(shares)),
        "heel_to_toe_timing": {"spearman_rho": round(float(rho_t), 3),
                               "best_of_3000_shuffles": round(float(np.abs(null_t).max()), 3)},
        "neighbour_similarity": {"spearman_rho": round(float(rho_n), 3),
                                 "best_of_3000_shuffles": round(float(null_n.min()), 3)},
    }


def side_layout(side, dots_named):
    xs = {l: p[0] for l, p in dots_named.items()}
    ys = {l: p[1] for l, p in dots_named.items()}
    pts = np.array([(xs[l], ys[l]) for l in range(1, 33)])
    nn = np.sort(np.hypot(*(pts[:, None] - pts[None]).transpose(2, 0, 1)), axis=1)[:, 1]
    radius = float(0.4 * np.median(nn))
    pad = radius * 1.3
    x0, y0 = pts[:, 0].min() - pad, pts[:, 1].min() - pad
    return {
        "width": round(float(pts[:, 0].max() - pts[:, 0].min() + 2 * pad), 1),
        "height": round(float(pts[:, 1].max() - pts[:, 1].min() + 2 * pad), 1),
        "radius": round(radius, 1),
        "sensors": [{"csv_index": l - 1, "label": l, "x": round(float(xs[l] - x0), 1),
                     "y": round(float(ys[l] - y0), 1)} for l in range(1, 33)],
    }


def main():
    dots, width = detect_dots()
    named = {"L": name_dots(dots[dots[:, 0] < width / 2], SEED_LEFT),
             "R": name_dots(dots[dots[:, 0] >= width / 2], SEED_RIGHT)}
    result = {
        "status": "supported_by_data_not_confirmed_by_authors",
        "mapping": "CSV column PressureSensor i = diagram label i+1; "
                   "_L files use the left diagram, _R files the right diagram.",
        "method": "research/verify_sensor_layout.py (heel-to-toe timing and neighbour-similarity tests, "
                  "each compared with 3000 shuffled layouts).",
        "limits": "Supports the heel-to-toe and neighbour structure of the diagram. Medial/lateral "
                  "orientation and the author's intent are not tested.",
        "sides": {},
    }
    for side in "LR":
        print(f"Testing {side} insole...")
        evidence = run_tests(side, named[side])
        print("  ", evidence)
        result["sides"][side] = {**side_layout(side, named[side]), "evidence": evidence}
    OUT_JSON.write_text(json.dumps(result, indent=1))
    print("Wrote", OUT_JSON)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(9, 11))
    for ax, side in zip(axes, "LR"):
        lay = result["sides"][side]
        for s in lay["sensors"]:
            ax.add_patch(plt.Circle((s["x"], s["y"]), lay["radius"], color="#0e5a6e", alpha=.25))
            ax.text(s["x"], s["y"], f'{s["label"]}\n(S{s["csv_index"]})', ha="center", va="center", fontsize=7)
        ax.set_xlim(0, lay["width"]); ax.set_ylim(lay["height"], 0); ax.set_aspect("equal")
        ax.set_title(f"{'Left' if side == 'L' else 'Right'} insole: diagram label (CSV sensor)")
    fig.tight_layout(); OUT_PNG.parent.mkdir(exist_ok=True); fig.savefig(OUT_PNG, dpi=110)
    print("Wrote", OUT_PNG)


if __name__ == "__main__":
    main()
