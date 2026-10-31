"""
Plantorix - orthotic design engine (DEMONSTRATION).

Turns one pressure recording into an illustrative insole design:

  1. Peak load per sensor over the whole recording (95th percentile, so a single
     spiky frame does not decide the result).
  2. The sensors with the highest peaks (top N percent, set by the user) get a
     circular relief pocket. Neighbouring selected sensors are grouped into zones.
  3. Size in millimetres: the insole length is estimated from the participant's
     shoe size (EU size x 2/3 cm) and the sensor diagram is scaled to it.
  4. The outline is the convex hull of the sensor array (a simplified shape).
  5. A solid base plate with blind pockets is exported as a binary STL.

Honest limits (also returned to the dashboard):
  * Pocket depth and base thickness are user-set demonstration values. There is no
    clinically validated rule behind them.
  * Sensor positions are evidence-supported but not confirmed by the dataset authors.
  * The output is not clinically validated, not a prescription and not print-ready.
"""

import math
from functools import lru_cache

import numpy as np
import pandas as pd
import trimesh
from shapely.geometry import Point
from shapely.ops import unary_union

from backend import config
from backend.services import dataset_service, layout_service

PEAK_PERCENTILE = 95
EU_SIZE_TO_MM = 20.0 / 3.0       # Paris point: one EU size = 2/3 cm
POCKET_FILL = 0.9                # pocket radius = 90 % of the sensor disc radius
LINK_DISTANCE = 1.6              # sensors closer than 1.6 x typical spacing share a zone
SHORT_RECORDING_FRAMES = 20

DISCLAIMER = (
    "Illustrative demonstration only. Pocket depth and base thickness are values chosen "
    "by the user, not clinically validated. Not a prescription, not validated for any "
    "individual and not print-ready."
)


class ParticipantInfoError(Exception):
    """Shoe size for the participant is not available."""


class DesignParameterError(ValueError):
    """Parameters are inconsistent (for example pockets deeper than the plate)."""


@lru_cache(maxsize=1)
def _shoe_sizes() -> dict:
    if not config.PARTICIPANTS_CSV.is_file():
        raise ParticipantInfoError("participants.csv not found, so the insole size is unknown.")
    df = pd.read_csv(config.PARTICIPANTS_CSV)
    return dict(zip(df["participant_code"], df["shoe_size_eu"]))


def insole_length_mm(participant: str) -> float:
    size = _shoe_sizes().get(participant)
    if size is None or not np.isfinite(size):
        raise ParticipantInfoError(f"No shoe size recorded for participant {participant}.")
    return float(size) * EU_SIZE_TO_MM


def _zones(selected, xy_px, spacing_px):
    """Group selected sensors that are neighbours (simple union-find)."""
    parent = {i: i for i in selected}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for a in selected:
        for b in selected:
            if a < b and np.hypot(*(xy_px[a] - xy_px[b])) <= LINK_DISTANCE * spacing_px:
                parent[find(a)] = find(b)
    groups = {}
    for i in selected:
        groups.setdefault(find(i), []).append(i)
    return list(groups.values())


def design(dataset_id: str, top_percent: int, depth_mm: float, base_mm: float) -> dict:
    """Compute the design (numbers and 2D geometry). Raises the service errors."""
    if depth_mm > base_mm - 1.0:
        raise DesignParameterError(
            "Pocket depth must leave at least 1 mm of material: "
            f"depth {depth_mm} mm is too deep for a {base_mm} mm base."
        )
    rec = dataset_service.load_recording(dataset_id)
    layout = layout_service.get_layout(rec.info.side)
    length_mm = insole_length_mm(rec.info.participant)

    sensors = sorted(layout["sensors"], key=lambda s: s["csv_index"])
    xy_px = np.array([(s["x"], s["y"]) for s in sensors], float)
    r_px = float(layout["radius"])
    nn = np.sort(np.hypot(*(xy_px[:, None] - xy_px[None]).transpose(2, 0, 1)), axis=1)[:, 1]
    spacing_px = float(np.median(nn))

    # Outline in diagram pixels: convex hull of the sensor discs (slightly enlarged)
    hull_px = unary_union([Point(*p).buffer(r_px * 1.15) for p in xy_px]).convex_hull
    minx, miny, maxx, maxy = hull_px.bounds
    scale = length_mm / (maxy - miny)                       # mm per diagram pixel

    def to_mm(px):                                          # y up, toe at the top
        return (px[0] - minx) * scale, (maxy - px[1]) * scale

    outline_mm = [to_mm(p) for p in hull_px.exterior.coords]
    width_mm = (maxx - minx) * scale

    peaks = np.percentile(rec.sensors, PEAK_PERCENTILE, axis=0)
    n_select = max(1, math.ceil(top_percent / 100 * config.SENSOR_COUNT))
    selected = [int(i) for i in np.argsort(-peaks, kind="stable")[:n_select]]

    # Zones, numbered by strongest peak first
    raw_zones = _zones(selected, xy_px, spacing_px)
    raw_zones.sort(key=lambda g: -max(peaks[i] for i in g))
    zone_of = {}
    zones = []
    for z, members in enumerate(raw_zones, start=1):
        cx = float(np.mean([to_mm(xy_px[i])[0] for i in members]))
        cy = float(np.mean([to_mm(xy_px[i])[1] for i in members]))
        from_toe = 1 - cy / length_mm
        zones.append({
            "id": f"Z{z}",
            "sensor_indices": sorted(members),
            "peak_value": int(max(peaks[i] for i in members)),
            "centre_x_mm": round(cx, 1), "centre_y_mm": round(cy, 1),
            "position_along_insole": "toe end" if from_toe < 1 / 3 else "middle" if from_toe < 2 / 3 else "heel end",
        })
        for i in members:
            zone_of[i] = f"Z{z}"

    pocket_r_mm = r_px * scale * POCKET_FILL
    all_sensors = []
    for s in sensors:
        i = s["csv_index"]
        x, y = to_mm(xy_px[i])
        all_sensors.append({
            "csv_index": i, "label": s["label"], "x_mm": round(x, 1), "y_mm": round(y, 1),
            "peak_value": int(round(peaks[i])), "selected": i in zone_of, "zone": zone_of.get(i),
        })

    warnings = [
        "Sensor positions are supported by the recordings but not confirmed by the dataset authors.",
        "The outline is a simplified convex hull of the sensor array, not an anatomical shape.",
        f"Insole length ({length_mm:.0f} mm) is estimated from the participant's shoe size and may differ from a real insole.",
    ]
    if len(rec.sensors) < SHORT_RECORDING_FRAMES:
        warnings.insert(0, f"Very short recording ({len(rec.sensors)} frames): peaks are not reliable.")
    issue = dataset_service.get_known_issue(rec.info)
    if issue:
        warnings.insert(0, issue)

    return {
        "dataset_id": dataset_id,
        "side": rec.info.side,
        "parameters": {"top_percent": top_percent, "relief_depth_mm": depth_mm, "base_thickness_mm": base_mm,
                       "peak_definition": f"{PEAK_PERCENTILE}th percentile of each sensor over all frames",
                       "values_are_demonstration_only": True},
        "dimensions_mm": {"length": round(length_mm, 1), "width": round(width_mm, 1), "thickness": base_mm},
        "scale_basis": "length = participant's EU shoe size x 2/3 cm; the sensor diagram is scaled to this length",
        "pocket_radius_mm": round(pocket_r_mm, 2),
        "selected_count": len(selected),
        "zones": zones,
        "sensors": all_sensors,
        "outline_mm": [[round(x, 1), round(y, 1)] for x, y in outline_mm],
        "warnings": warnings,
        "disclaimer": DISCLAIMER,
    }


def build_stl(d: dict) -> bytes:
    """Base plate with blind circular pockets, as a binary STL (units: mm)."""
    base, depth = d["parameters"]["base_thickness_mm"], d["parameters"]["relief_depth_mm"]
    from shapely.geometry import Polygon
    outline = Polygon(d["outline_mm"])
    pockets = unary_union([
        Point(s["x_mm"], s["y_mm"]).buffer(d["pocket_radius_mm"], quad_segs=16)
        for s in d["sensors"] if s["selected"]
    ])
    lower = trimesh.creation.extrude_polygon(outline, base - depth)
    upper = trimesh.creation.extrude_polygon(outline.difference(pockets), depth)
    upper.apply_translation([0, 0, base - depth])
    mesh = trimesh.boolean.union([lower, upper], engine="manifold")
    if not mesh.is_watertight:
        raise RuntimeError("Generated mesh is not watertight.")
    return mesh.export(file_type="stl")
