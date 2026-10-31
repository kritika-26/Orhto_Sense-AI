"""
Plantorix - step segmentation and step-to-step consistency.

Unsupervised and label-free: no model is trained and nothing is predicted.
It only describes the REAL recording.

1. The total of the 32 sensors per frame is the load signal.
2. Frames whose total is clearly above the recording's own resting level
   (its 5th percentile) form a "stance". A contiguous run = one step.
3. For each complete step we keep the peak of every sensor and compare the
   step's pattern with the recording's median step pattern. A robust z-score
   (median / MAD) marks steps that differ from the OTHER steps of the same
   recording. That is an outlier flag, not a clinical finding.

No frame rate is documented in the files we use, so durations are in frames.
"""

from typing import List

import numpy as np

from backend.services.dataset_service import LoadedRecording

STANCE_FRACTION = 0.20    # a frame is "loaded" above baseline + 20% of the range
MIN_STEP_FRAMES = 5       # shorter runs are treated as noise
MIN_STEPS_FOR_FLAGS = 5   # too few steps to say anything about outliers
OUTLIER_Z = 3.5           # the usual robust-z cut-off (Iglewicz and Hoaglin)
MAD_SCALE = 1.4826


def _robust_z(x: np.ndarray) -> np.ndarray:
    med = np.median(x)
    mad = np.median(np.abs(x - med)) * MAD_SCALE
    if mad < 1e-9:
        return np.zeros_like(x, dtype=float)
    return (x - med) / mad


def analyse(rec: LoadedRecording) -> dict:
    sensors = rec.sensors.astype(float)
    total = sensors.sum(axis=1)
    n = int(total.shape[0])
    baseline = float(np.percentile(total, 5))
    peak = float(total.max())
    threshold = baseline + STANCE_FRACTION * (peak - baseline)
    loaded = total > threshold

    runs: List[tuple] = []
    i = 0
    while i < n:
        if loaded[i]:
            j = i
            while j + 1 < n and loaded[j + 1]:
                j += 1
            if j - i + 1 >= MIN_STEP_FRAMES:
                runs.append((i, j))
            i = j + 1
        else:
            i += 1

    steps = []
    for k, (a, b) in enumerate(runs):
        seg = sensors[a:b + 1]
        sp = seg.max(axis=0)
        steps.append({
            "step": k + 1, "start_frame": a, "end_frame": b, "frames": b - a + 1,
            # a step touching the first or last frame of the file is cut off
            "complete": bool(a > 0 and b < n - 1),
            "peak_total": float(seg.sum(axis=1).max()),
            "peak_frame": int(a + seg.sum(axis=1).argmax()),
            "sensor_peaks": [float(v) for v in sp],
            "pattern_distance": None, "z_score": None, "differs": False,
        })

    done = [s for s in steps if s["complete"]]
    notes: List[str] = []
    stats = {"complete_steps": len(done), "median_frames": None, "frames_variation_pct": None,
             "median_pattern_distance": None}
    if len(done) >= 2:
        prof = np.array([s["sensor_peaks"] for s in done])
        prof = prof / prof.sum(axis=1, keepdims=True)           # shape of the step, not its size
        med = np.median(prof, axis=0)
        dist = 0.5 * np.abs(prof - med).sum(axis=1)             # 0 = identical shape, 1 = disjoint
        z = _robust_z(dist)
        dur = np.array([s["frames"] for s in done], float)
        stats["median_frames"] = float(np.median(dur))
        stats["frames_variation_pct"] = float(100 * dur.std() / dur.mean())
        stats["median_pattern_distance"] = float(np.median(dist))
        can_flag = len(done) >= MIN_STEPS_FOR_FLAGS
        for s, d, zz in zip(done, dist, z):
            s["pattern_distance"] = float(d)
            s["z_score"] = float(zz)
            s["differs"] = bool(can_flag and zz > OUTLIER_Z)
        if not can_flag:
            notes.append("Fewer than %d complete steps, so no step is flagged as different." % MIN_STEPS_FOR_FLAGS)
    elif steps:
        notes.append("Fewer than 2 complete steps in this recording; no comparison possible.")
    else:
        notes.append("No loaded steps were found in this recording.")
    if any(not s["complete"] for s in steps):
        notes.append("Steps cut off at the start or end of the file are listed but not compared.")

    return {
        "dataset_id": rec.info.dataset_id,
        "frame_count": n,
        "baseline_total": baseline,
        "threshold_total": float(threshold),
        "loaded": [bool(v) for v in loaded],
        "total": [float(v) for v in total],
        "steps": steps,
        "stats": stats,
        "notes": notes,
        "method": ("Unsupervised and label-free. Steps are runs of frames whose 32-sensor total is above "
                   "the recording's own resting level. Each complete step's sensor-peak pattern is compared "
                   "with the median step of the same recording; 'differs' = robust z-score above %.1f. "
                   "This is not a diagnosis or a prediction." % OUTLIER_Z),
    }
