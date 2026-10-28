"""Automated checks for the Plantorix API.  Run from the project root:

    pip install pytest httpx
    python -m pytest -q
"""

import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app, base_url="http://127.0.0.1:8000")
GOOD = "P15_M3.I_L"


def test_health_reports_real_state():
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["recordings_found"] == 310


def test_datasets_listing_and_filters():
    assert client.get("/api/datasets").json()["count"] == 310
    only_left = client.get("/api/datasets?participant=P15&side=L").json()
    assert only_left["count"] > 0
    assert all(r["side"] == "L" and r["participant"] == "P15" for r in only_left["recordings"])


def test_summary_matches_real_file():
    s = client.get(f"/api/datasets/{GOOD}/summary").json()
    assert s["sensor_count"] == 32 and s["frame_count"] > 100
    assert s["sensor_layout_verified"] is False
    assert s["value_label"] == "Recorded sensor value"


def test_frame_statistics_are_consistent():
    f = client.get(f"/api/datasets/{GOOD}/frame/50").json()
    v = np.array(f["values"])
    assert len(v) == 32
    assert f["total"] == int(v.sum()) and f["max"] == int(v.max()) and f["min"] == int(v.min())
    assert f["mean"] == pytest.approx(v.mean(), abs=1e-3)
    assert all(v[i] > v.mean() for i in f["above_average_sensors"])
    assert len(f["above_average_sensors"]) == int((v > v.mean()).sum())


def test_timeseries_and_sump_validation():
    ts = client.get(f"/api/datasets/{GOOD}/timeseries?sensor=3").json()
    assert len(ts["calculated_sum"]) == ts["frame_count"] == len(ts["sensor_series"])
    assert ts["calculated_sum"] == ts["sump"]
    val = client.get(f"/api/datasets/{GOOD}/validation").json()
    assert val["sump_check"]["matches_exactly"] is True


def test_short_recording_gets_warning():
    val = client.get("/api/datasets/P15_M3_L/validation").json()
    assert any("short recording" in w.lower() for w in val["warnings"])


@pytest.mark.parametrize("path,status", [
    (f"/api/datasets/{GOOD}/frame/99999", 404),       # past the last frame
    (f"/api/datasets/{GOOD}/frame/-1", 422),          # negative index
    ("/api/datasets/NOPE/summary", 404),              # unknown id
    ("/api/datasets/..%5C..%5Cetc/summary", 404),     # path-style id is rejected
    (f"/api/datasets/{GOOD}/timeseries?sensor=32", 422),
    ("/api/datasets?side=X", 422),
])
def test_bad_requests_get_clear_errors(path, status):
    assert client.get(path).status_code == status


def test_old_mock_endpoint_is_gone():
    assert client.post("/predict-pressure", json={}).status_code in (404, 405)


def test_dashboard_is_served():
    r = client.get("/")
    assert r.status_code == 200 and "Plantorix" in r.text