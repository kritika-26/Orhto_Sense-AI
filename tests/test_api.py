"""Automated checks for the Plantorix API.  Run from the project root:

    pip install pytest httpx
    python -m pytest -q
"""

import io

import numpy as np
import trimesh
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


@pytest.mark.parametrize("side", ["L", "R"])
def test_layout_has_32_unique_sensors_and_real_evidence(side):
    lay = client.get(f"/api/layout/{side}").json()
    assert sorted(s["csv_index"] for s in lay["sensors"]) == list(range(32))
    assert sorted(s["label"] for s in lay["sensors"]) == list(range(1, 33))
    assert "not_confirmed_by_authors" in lay["status"]
    # negative = real gait ordering; the best random shuffles are far weaker
    assert lay["evidence"]["heel_to_toe_timing"]["spearman_rho"] < -0.9
    assert lay["evidence"]["neighbour_similarity"]["spearman_rho"] < -0.8


def test_layout_rejects_bad_side():
    assert client.get("/api/layout/X").status_code == 422


def test_orthotic_design_numbers():
    d = client.get("/api/datasets/P1_M1_L/orthotic?top_percent=20&depth_mm=3&base_mm=8").json()
    assert d["selected_count"] == 7                                  # ceil(20 % of 32)
    assert sum(s["selected"] for s in d["sensors"]) == 7
    assert d["dimensions_mm"]["length"] == pytest.approx(40 * 20 / 3, abs=0.1)   # P1 wears EU 40
    assert d["parameters"]["values_are_demonstration_only"] is True
    assert "not clinically validated" in d["disclaimer"].lower()
    ranks = sorted((s for s in d["sensors"]), key=lambda s: -s["peak_value"])
    assert all(s["selected"] for s in ranks[:7])                     # the 7 highest peaks
    assert sorted(i for z in d["zones"] for i in z["sensor_indices"]) == sorted(s["csv_index"] for s in ranks[:7])


def test_orthotic_stl_is_a_valid_watertight_solid():
    r = client.get("/api/datasets/P1_M1_L/orthotic.stl?top_percent=20&depth_mm=3&base_mm=8")
    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    n = int.from_bytes(r.content[80:84], "little")
    assert len(r.content) == 84 + 50 * n                             # binary STL layout
    mesh = trimesh.load(io.BytesIO(r.content), file_type="stl")
    assert mesh.is_watertight and mesh.volume > 0
    assert mesh.bounds[1][2] == pytest.approx(8.0, abs=1e-6)         # plate thickness
    d = client.get("/api/datasets/P1_M1_L/orthotic").json()
    assert mesh.bounds[1][1] == pytest.approx(d["dimensions_mm"]["length"], abs=0.5)


def test_more_pockets_remove_more_material():
    vol = lambda p: trimesh.load(io.BytesIO(client.get(f"/api/datasets/P1_M1_L/orthotic.stl?top_percent={p}").content), file_type="stl").volume
    assert vol(40) < vol(10)


@pytest.mark.parametrize("query,status", [
    ("depth_mm=7.5&base_mm=8", 422),      # leaves under 1 mm of material
    ("top_percent=90", 422),
    ("depth_mm=0", 422),
])
def test_orthotic_bad_parameters(query, status):
    assert client.get(f"/api/datasets/P1_M1_L/orthotic?{query}").status_code == status
    assert client.get(f"/api/datasets/P1_M1_L/orthotic.stl?{query}").status_code == status


def test_orthotic_unknown_recording():
    assert client.get("/api/datasets/NOPE/orthotic").status_code == 404


def test_branding_and_vendor_assets_are_served():
    for path in ("/assets/logo-main.png", "/assets/logo-mark.png", "/assets/app-icon.png",
                 "/assets/icons/reports.png", "/vendor/chart.umd.js"):
        r = client.get(path)
        assert r.status_code == 200, path
        assert len(r.content) > 500, path


def test_steps_segmentation_is_consistent_with_the_signal():
    d = client.get("/api/datasets/P1_M1_L/steps").json()
    assert len(d["total"]) == d["frame_count"] == len(d["loaded"])
    assert d["stats"]["complete_steps"] >= 2
    for s in d["steps"]:
        assert all(d["loaded"][s["start_frame"]:s["end_frame"] + 1])      # a step is a loaded run
        assert d["total"][s["peak_frame"]] == s["peak_total"]
        assert len(s["sensor_peaks"]) == 32
    assert "not a diagnosis" in d["method"].lower()


def test_steps_short_recording_is_reported_honestly():
    d = client.get("/api/datasets/P15_M3_L/steps").json()
    assert d["stats"]["complete_steps"] == 0 and d["notes"]
    assert not any(s["differs"] for s in d["steps"])


def test_steps_flags_need_enough_steps():
    import itertools
    for rid in ("P7_M3_L", "P1_M1_L"):
        d = client.get(f"/api/datasets/{rid}/steps").json()
        flagged = [s for s in d["steps"] if s["differs"]]
        assert not flagged or d["stats"]["complete_steps"] >= 5


def test_steps_unknown_recording_404():
    assert client.get("/api/datasets/P99_M1_L/steps").status_code == 404
