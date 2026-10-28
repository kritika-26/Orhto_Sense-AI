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
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend import config
from backend.schemas import models
from backend.services import analysis, dataset_service
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


# Serve the dashboard from the same server, so one command runs everything:
# http://127.0.0.1:8000/   (registered last so the /api routes win)
if config.FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=config.FRONTEND_DIR, html=True), name="frontend")