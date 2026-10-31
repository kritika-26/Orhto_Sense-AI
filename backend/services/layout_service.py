"""Plantorix - sensor layout service.

Reads backend/sensor_layout.json, written by research/verify_sensor_layout.py.
That file holds the sensor positions detected on the dataset's numbering diagram
and the evidence that links CSV columns to diagram labels. Regenerate it with:

    python research/verify_sensor_layout.py
"""

import json
from functools import lru_cache

from backend import config

LAYOUT_FILE = config.PROJECT_ROOT / "backend" / "sensor_layout.json"


class LayoutNotAvailableError(Exception):
    """The layout file has not been generated."""


@lru_cache(maxsize=1)
def _load() -> dict:
    if not LAYOUT_FILE.is_file():
        raise LayoutNotAvailableError(
            "sensor_layout.json not found. Generate it with: python research/verify_sensor_layout.py"
        )
    return json.loads(LAYOUT_FILE.read_text(encoding="utf-8"))


def get_layout(side: str) -> dict:
    data = _load()
    if side not in data["sides"]:
        raise LayoutNotAvailableError(f"No layout for side {side!r}")
    return {
        "side": side,
        "status": data["status"],
        "mapping": data["mapping"],
        "method": data["method"],
        "limits": data["limits"],
        **data["sides"][side],
    }
