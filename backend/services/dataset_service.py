"""
Plantorix - dataset service.

Responsibilities:
  1. Discover the pressure recordings on disk and build a WHITELIST of ids.
  2. Load one recording from disk (cached) and check it has the columns we need.

Security idea: callers only ever pass a dataset_id such as "P15_M3.I_L".
We look that id up in the whitelist built from our own folder scan, so a request
can never make us open an arbitrary path like "..\\..\\secrets.txt".

Raw files are only read, never modified. Self-check:

    python -m backend.services.dataset_service
"""

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

import numpy as np
import pandas as pd

from backend import config

# Ids look like  P15_M3.I_L   (participant _ take _ side)
DATASET_ID_REGEX = re.compile(r"^P\d{1,3}_[A-Za-z0-9.]{1,12}_[LR]$")

# Copied from the dataset's info.txt (see Zenodo record 20156243). These are
# shown as warnings in the dashboard; they are not our own judgements.
# Key: (participant, take) -> message
KNOWN_ISSUES = {
    ("P3", "M5.I"): "OptiTrack gaps repaired by interpolation (motion data only).",
    ("P3", "M6.I"): "OptiTrack gaps repaired by interpolation (motion data only).",
    ("P13", "M8.I"): "OptiTrack gaps repaired by interpolation (motion data only).",
    ("P13", "M9.I"): "OptiTrack gaps repaired by interpolation (motion data only).",
    ("P15", "M3.I"): "OptiTrack gaps repaired by interpolation (motion data only).",
    ("P3", "M8"): "Dataset notes: OptiTrack data contain errors; take not repairable.",
    ("P13", "M1"): "Dataset notes: insole data desynchronised by a hardware issue.",
}


class DatasetNotFoundError(Exception):
    """The dataset id is malformed or not in the discovered whitelist."""


class DatasetFormatError(Exception):
    """The file exists but does not have the expected columns/format."""


@dataclass(frozen=True)
class RecordingInfo:
    dataset_id: str
    participant: str
    take: str
    side: str          # "L" or "R"
    filename: str
    relative_path: str  # relative to the dataset folder, for display only


@dataclass(frozen=True)
class LoadedRecording:
    info: RecordingInfo
    sensors: np.ndarray            # shape (frames, 32), read-only
    sump: Optional[np.ndarray]     # shape (frames,), read-only, or None
    columns: list                  # every column name in the file
    missing_values: int            # NaN count across the whole file


def _natural_key(text: str):
    """Sort P2 before P10, M2 before M10."""
    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", text)]


@lru_cache(maxsize=1)
def _discover() -> dict:
    """Scan the dataset folder once; return {dataset_id: (RecordingInfo, Path)}."""
    found = {}
    if not config.DATASET_DIR.is_dir():
        return found
    for path in config.DATASET_DIR.glob(config.PRESSURE_FILE_GLOB):
        match = config.PRESSURE_FILE_REGEX.match(path.name)
        if not match:
            continue
        participant = path.parent.parent.name
        take = match["take"]
        if path.parent.name != take:  # folder and file name must agree
            continue
        dataset_id = f"{participant}_{take}_{match['side']}"
        if not DATASET_ID_REGEX.match(dataset_id):
            continue
        info = RecordingInfo(
            dataset_id=dataset_id,
            participant=participant,
            take=take,
            side=match["side"],
            filename=path.name,
            relative_path=path.relative_to(config.DATASET_DIR).as_posix(),
        )
        found[dataset_id] = (info, path)
    ordered = sorted(
        found.items(),
        key=lambda kv: (_natural_key(kv[1][0].participant),
                        _natural_key(kv[1][0].take), kv[1][0].side),
    )
    return dict(ordered)


def rescan() -> None:
    """Forget the cached folder scan and loaded recordings."""
    _discover.cache_clear()
    load_recording.cache_clear()


def list_recordings() -> list:
    return [info for info, _ in _discover().values()]


def get_known_issue(info: RecordingInfo) -> Optional[str]:
    return KNOWN_ISSUES.get((info.participant, info.take))


@lru_cache(maxsize=config.RECORDING_CACHE_SIZE)
def load_recording(dataset_id: str) -> LoadedRecording:
    """Load one recording. Raises DatasetNotFoundError / DatasetFormatError."""
    entry = _discover().get(dataset_id)  # whitelist lookup; no user path used
    if entry is None:
        raise DatasetNotFoundError(f"Unknown dataset id: {dataset_id!r}")
    info, path = entry

    try:
        df = pd.read_csv(path)
    except (OSError, pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        raise DatasetFormatError(f"Could not read {info.filename}: {exc}") from exc

    absent = [c for c in config.SENSOR_COLUMNS if c not in df.columns]
    if absent:
        raise DatasetFormatError(
            f"{info.filename} is missing {len(absent)} sensor column(s), e.g. {absent[0]!r}"
        )
    if len(df) == 0:
        raise DatasetFormatError(f"{info.filename} contains no rows")

    sensors = df[config.SENSOR_COLUMNS].to_numpy(copy=True)
    sensors.setflags(write=False)  # raw data must never be modified in memory

    sump = None
    if config.SUMP_COLUMN in df.columns:
        sump = df[config.SUMP_COLUMN].to_numpy(copy=True)
        sump.setflags(write=False)

    return LoadedRecording(
        info=info,
        sensors=sensors,
        sump=sump,
        columns=list(df.columns),
        missing_values=int(df.isna().sum().sum()),
    )


def _self_check() -> None:
    recs = list_recordings()
    print(f"Recordings discovered: {len(recs)}")
    if not recs:
        print("Nothing found - run `python -m backend.config` to check the paths.")
        return
    print(f"First: {recs[0].dataset_id}   Last: {recs[-1].dataset_id}")

    r = load_recording("P15_M3.I_L") if "P15_M3.I_L" in _discover() else load_recording(recs[0].dataset_id)
    print(f"\nLoaded {r.info.dataset_id}: {r.sensors.shape[0]} frames x {r.sensors.shape[1]} sensors")
    print(f"Columns: {len(r.columns)}   Missing values: {r.missing_values}")
    print(f"sumP present: {r.sump is not None}   Known issue: {get_known_issue(r.info)}")

    bad = 0
    for rec in recs:
        loaded = load_recording(rec.dataset_id)
        if loaded.sump is not None and not np.array_equal(loaded.sensors.sum(axis=1), loaded.sump):
            bad += 1
    print(f"\nsumP mismatches across all recordings: {bad}")

    for bad_id in ("..\\..\\x", "P1_M1_X", "P99_M1_L"):
        try:
            load_recording(bad_id)
            print(f"UNEXPECTED: {bad_id!r} loaded")
        except DatasetNotFoundError:
            print(f"Rejected invalid id {bad_id!r}: OK")

    try:
        load_recording(recs[0].dataset_id).sensors[0, 0] = 0
        print("UNEXPECTED: array was writable")
    except ValueError:
        print("Raw array is read-only: OK")


if __name__ == "__main__":
    _self_check()
