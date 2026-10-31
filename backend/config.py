"""
Plantorix - central configuration.

Every other backend file imports its paths, constants and settings from here,
so nothing is hard-coded to one computer. Nothing in this file needs a
third-party package (standard library only), so you can run it before
installing anything.

Self-check (run from the project root, the folder that contains backend/):

    python -m backend.config
"""

import os
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths (always resolved relative to this file, never an absolute C:\ path)
# ---------------------------------------------------------------------------

# backend/config.py -> parent is backend/ -> parent again is the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Where the raw dataset lives. You can override it without editing code:
#   PowerShell:  $env:PLANTORIX_DATASET_DIR = "D:\datasets\InsolesOpitrackDataset"
# This is developer configuration. It is never taken from an API request.
DATASET_DIR = Path(
    os.environ.get(
        "PLANTORIX_DATASET_DIR",
        PROJECT_ROOT / "data" / "raw" / "InsolesOpitrackDataset",
    )
).resolve()

PARTICIPANTS_CSV = DATASET_DIR / "participants.csv"
FRONTEND_DIR = PROJECT_ROOT / "frontend"

# ---------------------------------------------------------------------------
# Dataset file naming
# ---------------------------------------------------------------------------

# Pressure files look like  P15/M3.I/M3.I_Preassure_L.csv
# ("Preassure" is the dataset's own spelling, so we match it as it is.)
# Folder layout:  <participant>/<take>/<take>_Preassure_<L or R>.csv
PRESSURE_FILE_REGEX = re.compile(r"^(?P<take>.+)_Preassure_(?P<side>[LR])\.csv$")
PRESSURE_FILE_GLOB = "P*/*/*_Preassure_[LR].csv"

# ---------------------------------------------------------------------------
# Sensor columns
# ---------------------------------------------------------------------------

SENSOR_COUNT = 32
SENSOR_COLUMNS = [f"PressureSensor {i}" for i in range(SENSOR_COUNT)]
SUMP_COLUMN = "sumP"

# Honest unit label. The values are raw sensor readings, NOT kPa.
VALUE_LABEL = "Recorded sensor value"

# The insole diagram numbers sensors 1-32, but the CSV columns are 0-31, and
# the two diagrams do not appear to share one simple numbering. Until the
# mapping is confirmed from dataset documentation, we must NOT place sensors
# on a foot outline. The API sends this flag to the frontend so the heatmap
# is labelled "unregistered sensor layout". Only change it to True after the
# mapping has been verified.
SENSOR_LAYOUT_VERIFIED = False

# ---------------------------------------------------------------------------
# API settings
# ---------------------------------------------------------------------------

API_TITLE = "Plantorix API"
API_VERSION = "0.1.0"

# Browsers only allow the dashboard to call the API from origins listed here.
# These are the usual local-development addresses (VS Code Live Server uses
# 5500; `python -m http.server` uses 8080 or 5173-style ports; the API itself
# is on 8000 if we later serve the dashboard from FastAPI).
CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "PLANTORIX_CORS_ORIGINS",
        "http://127.0.0.1:5500,http://localhost:5500,"
        "http://127.0.0.1:8000,http://localhost:8000,"
        "http://127.0.0.1:8080,http://localhost:8080",
    ).split(",")
    if origin.strip()
]

# How many recordings to keep in memory at once (each is only a few hundred
# rows, but there are 310 of them, so we cache the recently used ones).
RECORDING_CACHE_SIZE = 32


# ---------------------------------------------------------------------------
# Self-check: python -m backend.config
# ---------------------------------------------------------------------------

def _self_check() -> None:
    print("Plantorix configuration check")
    print("-" * 40)
    print(f"Project root     : {PROJECT_ROOT}")
    print(f"Dataset folder   : {DATASET_DIR}")
    print(f"Dataset exists   : {DATASET_DIR.is_dir()}")
    print(f"participants.csv : {'found' if PARTICIPANTS_CSV.is_file() else 'MISSING'}")
    print(f"Sensor columns   : {SENSOR_COUNT} ({SENSOR_COLUMNS[0]} ... {SENSOR_COLUMNS[-1]})")
    print(f"Layout verified  : {SENSOR_LAYOUT_VERIFIED}")
    print(f"CORS origins     : {len(CORS_ORIGINS)} configured")

    if not DATASET_DIR.is_dir():
        print("\nERROR: dataset folder not found. Check the path above, or set")
        print("PLANTORIX_DATASET_DIR to the folder that contains P1, P2, ...")
        return

    files = sorted(DATASET_DIR.glob(PRESSURE_FILE_GLOB))
    left = right = unmatched = 0
    for path in files:
        match = PRESSURE_FILE_REGEX.match(path.name)
        if not match:
            unmatched += 1
        elif match["side"] == "L":
            left += 1
        else:
            right += 1

    print("-" * 40)
    print(f"Pressure files found : {len(files)}")
    print(f"  left (L)           : {left}")
    print(f"  right (R)          : {right}")
    print(f"  name not matched   : {unmatched}")


if __name__ == "__main__":
    _self_check()
