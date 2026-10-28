"""
Plantorix - analysis functions.

Plain, transparent maths on the REAL sensor readings. Nothing here is a
prediction or a clinical judgement. "Above average" only means "higher than
the mean of the 32 sensors in the same frame", a relative comparison.

All functions take a LoadedRecording (from dataset_service) and never modify it.
"""

from typing import Optional

import numpy as np

from backend import config
from backend.services.dataset_service import LoadedRecording, get_known_issue

# Zenodo describes the values as ranging from 0 to 4096 (no physical unit).
EXPECTED_MIN = 0
EXPECTED_MAX = 4096
# Recordings shorter than this are too short to show a gait pattern.
SHORT_RECORDING_FRAMES = 20


def frame_count(rec: LoadedRecording) -> int:
    return int(rec.sensors.shape[0])


def summary(rec: LoadedRecording) -> dict:
    s = rec.sensors
    return {
        "dataset_id": rec.info.dataset_id,
        "participant": rec.info.participant,
        "take": rec.info.take,
        "side": rec.info.side,
        "filename": rec.info.filename,
        "frame_count": frame_count(rec),
        "column_count": len(rec.columns),
        "sensor_count": int(s.shape[1]),
        "sensor_columns": list(config.SENSOR_COLUMNS),
        "available_columns": rec.columns,
        "missing_values": rec.missing_values,
        "has_sump": rec.sump is not None,
        "value_min": int(s.min()),
        "value_max": int(s.max()),
        "value_label": config.VALUE_LABEL,
        "sensor_layout_verified": config.SENSOR_LAYOUT_VERIFIED,
        "known_issue": get_known_issue(rec.info),
    }


def frame_analysis(rec: LoadedRecording, frame_index: int) -> dict:
    """Statistics for one frame. Caller must check frame_index is in range."""
    values = rec.sensors[frame_index]
    mean = float(values.mean())
    above = [int(i) for i in np.argsort(-values, kind="stable") if values[i] > mean]
    return {
        "dataset_id": rec.info.dataset_id,
        "frame_index": frame_index,
        "frame_count": frame_count(rec),
        "values": values.tolist(),          # index = CSV sensor index 0..31
        "mean": round(mean, 3),
        "max": int(values.max()),
        "max_sensor_index": int(values.argmax()),
        "min": int(values.min()),
        "min_sensor_index": int(values.argmin()),
        "total": int(values.sum()),
        "above_average_sensors": above,     # strongest first
        "value_label": config.VALUE_LABEL,
        "sensor_layout_verified": config.SENSOR_LAYOUT_VERIFIED,
        "note": (
            "Above-average sensors are a relative comparison within this frame. "
            "They are not clinical pressure hotspots."
        ),
    }


def timeseries(rec: LoadedRecording, sensor: Optional[int] = None) -> dict:
    """Per-frame series for charts. Optionally one sensor's own series."""
    s = rec.sensors
    result = {
        "dataset_id": rec.info.dataset_id,
        "frame_count": frame_count(rec),
        "frames": list(range(frame_count(rec))),
        "calculated_sum": s.sum(axis=1).tolist(),
        "sump": rec.sump.tolist() if rec.sump is not None else None,
        "frame_max": s.max(axis=1).tolist(),
        "frame_mean": [round(float(v), 3) for v in s.mean(axis=1)],
        "value_label": config.VALUE_LABEL,
        "sensor_index": sensor,
        "sensor_series": s[:, sensor].tolist() if sensor is not None else None,
    }
    return result


def validation(rec: LoadedRecording) -> dict:
    """Compare the calculated sensor sum with the recorded sumP column."""
    calculated = rec.sensors.sum(axis=1)
    warnings = []

    if rec.sump is not None:
        diff = calculated.astype(np.int64) - rec.sump.astype(np.int64)
        abs_diff = np.abs(diff)
        sump_check = {
            "available": True,
            "matches_exactly": bool(np.all(diff == 0)),
            "max_abs_difference": float(abs_diff.max()),
            "mean_abs_difference": round(float(abs_diff.mean()), 6),
            "frames_with_difference": int(np.count_nonzero(diff)),
        }
        if not sump_check["matches_exactly"]:
            warnings.append(
                f"Calculated sensor sum differs from sumP in "
                f"{sump_check['frames_with_difference']} frame(s)."
            )
    else:
        sump_check = {"available": False, "matches_exactly": None,
                      "max_abs_difference": None, "mean_abs_difference": None,
                      "frames_with_difference": None}
        warnings.append("The sumP column is not present, so the sum check was skipped.")

    if rec.missing_values:
        warnings.append(f"{rec.missing_values} missing value(s) in this file (left unchanged).")
    if frame_count(rec) < SHORT_RECORDING_FRAMES:
        warnings.append(
            f"Very short recording ({frame_count(rec)} frames); "
            "charts and statistics will not show a gait pattern."
        )
    lo, hi = int(rec.sensors.min()), int(rec.sensors.max())
    if lo < EXPECTED_MIN or hi > EXPECTED_MAX:
        warnings.append(
            f"Sensor values ({lo} to {hi}) fall outside the documented "
            f"{EXPECTED_MIN}-{EXPECTED_MAX} range."
        )
    issue = get_known_issue(rec.info)
    if issue:
        warnings.append(issue)

    return {
        "dataset_id": rec.info.dataset_id,
        "rows": frame_count(rec),
        "columns": len(rec.columns),
        "sensor_channels": int(rec.sensors.shape[1]),
        "missing_values": rec.missing_values,
        "available_columns": rec.columns,
        "sump_check": sump_check,
        "warnings": warnings,
    }