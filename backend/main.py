"""
Plantorix API.

Start (from the project root, with the virtual environment active):

    uvicorn backend.main:app --reload

Interactive docs: http://127.0.0.1:8000/docs
The old mock endpoint (/predict-pressure) was removed on purpose: it invented
pressures, a clinical status and an offloading depth instead of using data.
"""

from typing import Optional

from fastapi import FastAPI, HTTPException, Path, Query
from fastapi import Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend import config
from backend.schemas import models
from backend.services import analysis, dataset_service, layout_service, orthotic_service, step_service
from backend.services.dataset_service import (
    DatasetFormatError,
    DatasetNotFoundError,
    LoadedRecording,
)

app = FastAPI(
    title=config.API_TITLE,
    version=config.API_VERSION,
    description=(
        "Plantar pressure analysis for a research/educational prototype. "
        "Not a clinically validated medical device."
    ),
)

# Only the local development origins listed in config.py may call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _load_or_http_error(dataset_id: str) -> LoadedRecording:
    """Turn service errors into proper HTTP errors with readable messages."""
    try:
        return dataset_service.load_recording(dataset_id)
    except DatasetNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Recording '{dataset_id}' not found. See GET /api/datasets for valid ids.",
        )
    except DatasetFormatError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


DatasetId = Path(..., description="Recording id such as P15_M3.I_L", max_length=24)


@app.get("/api/health", response_model=models.Health)
def health():
    found = config.DATASET_DIR.is_dir()
    count = len(dataset_service.list_recordings())
    ok = found and count > 0
    return models.Health(
        status="ok" if ok else "degraded",
        api_version=config.API_VERSION,
        dataset_dir_found=found,
        recordings_found=count,
        message=(
            "API running and recordings discovered."
            if ok
            else "API running but no recordings found. Check the dataset folder "
                 "(python -m backend.config)."
        ),
    )


@app.get("/api/datasets", response_model=models.DatasetList)
def list_datasets(
    participant: Optional[str] = Query(None, max_length=6, description="e.g. P15"),
    side: Optional[str] = Query(None, pattern="^[LR]$"),
):
    items = []
    for info in dataset_service.list_recordings():
        if participant and info.participant != participant:
            continue
        if side and info.side != side:
            continue
        items.append(
            models.RecordingItem(
                dataset_id=info.dataset_id,
                participant=info.participant,
                take=info.take,
                side=info.side,
                filename=info.filename,
                known_issue=dataset_service.get_known_issue(info),
            )
        )
    return models.DatasetList(count=len(items), recordings=items)


@app.get("/api/datasets/{dataset_id}/summary", response_model=models.Summary)
def dataset_summary(dataset_id: str = DatasetId):
    return analysis.summary(_load_or_http_error(dataset_id))


@app.get("/api/datasets/{dataset_id}/frame/{frame_index}", response_model=models.FrameAnalysis)
def dataset_frame(dataset_id: str = DatasetId, frame_index: int = Path(..., ge=0)):
    rec = _load_or_http_error(dataset_id)
    last = analysis.frame_count(rec) - 1
    if frame_index > last:
        raise HTTPException(
            status_code=404,
            detail=f"Frame {frame_index} is out of range for {dataset_id}; valid frames are 0 to {last}.",
        )
    return analysis.frame_analysis(rec, frame_index)


@app.get("/api/datasets/{dataset_id}/timeseries", response_model=models.TimeSeries)
def dataset_timeseries(
    dataset_id: str = DatasetId,
    sensor: Optional[int] = Query(None, ge=0, lt=config.SENSOR_COUNT,
                                  description="Optional CSV sensor index 0-31"),
):
    return analysis.timeseries(_load_or_http_error(dataset_id), sensor)


@app.get("/api/datasets/{dataset_id}/validation", response_model=models.Validation)
def dataset_validation(dataset_id: str = DatasetId):
    return analysis.validation(_load_or_http_error(dataset_id))


@app.get("/api/layout/{side}", response_model=models.Layout)
def sensor_layout(side: str = Path(..., pattern="^[LR]$")):
    """Sensor positions from the dataset's numbering diagram, plus the evidence
    that links CSV columns to diagram labels. Evidence-supported, NOT confirmed
    by the dataset authors."""
    try:
        return layout_service.get_layout(side)
    except layout_service.LayoutNotAvailableError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


def _design_or_http_error(dataset_id, top_percent, depth_mm, base_mm) -> dict:
    try:
        return orthotic_service.design(dataset_id, top_percent, depth_mm, base_mm)
    except DatasetNotFoundError:
        raise HTTPException(status_code=404, detail=f"Recording '{dataset_id}' not found.")
    except DatasetFormatError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except layout_service.LayoutNotAvailableError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except orthotic_service.ParticipantInfoError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except orthotic_service.DesignParameterError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/api/datasets/{dataset_id}/steps", response_model=models.StepAnalysis)
def step_analysis(dataset_id: str = DatasetId):
    """Label-free step segmentation and step-to-step consistency. Descriptive only."""
    try:
        return step_service.analyse(dataset_service.load_recording(dataset_id))
    except DatasetNotFoundError:
        raise HTTPException(status_code=404, detail=f"Recording '{dataset_id}' not found.")
    except DatasetFormatError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


TopPercent = Query(20, ge=5, le=50, description="Share of sensors (highest peaks) that get a relief pocket")
DepthMm = Query(3.0, ge=0.5, le=6.0, description="Pocket depth in mm (demonstration value)")
BaseMm = Query(8.0, ge=4.0, le=12.0, description="Base plate thickness in mm (demonstration value)")


@app.get("/api/datasets/{dataset_id}/orthotic", response_model=models.OrthoticDesign)
def orthotic_design(dataset_id: str = DatasetId, top_percent: int = TopPercent,
                    depth_mm: float = DepthMm, base_mm: float = BaseMm):
    """Illustrative insole design from the recording's peak loads. Demonstration only."""
    return _design_or_http_error(dataset_id, top_percent, depth_mm, base_mm)


@app.get("/api/datasets/{dataset_id}/orthotic.stl")
def orthotic_stl(dataset_id: str = DatasetId, top_percent: int = TopPercent,
                 depth_mm: float = DepthMm, base_mm: float = BaseMm):
    """Same design as a binary STL file (units: mm). Demonstration only."""
    d = _design_or_http_error(dataset_id, top_percent, depth_mm, base_mm)
    try:
        data = orthotic_service.build_stl(d)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    name = f"plantorix_{dataset_id}_demo_top{top_percent}_d{depth_mm:g}.stl"
    return Response(content=data, media_type="model/stl",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


# Serve the dashboard from the same server, so one command runs everything:
# http://127.0.0.1:8000/   (registered last so the /api routes win)
if config.FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=config.FRONTEND_DIR, html=True), name="frontend")
