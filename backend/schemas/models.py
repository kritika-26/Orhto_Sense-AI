"""Plantorix - response models. They document the API (see /docs) and
guarantee the shape of what the frontend receives."""

from typing import List, Optional

from pydantic import BaseModel


class Health(BaseModel):
    status: str                 # "ok" or "degraded"
    api_version: str
    dataset_dir_found: bool
    recordings_found: int
    message: str


class RecordingItem(BaseModel):
    dataset_id: str
    participant: str
    take: str
    side: str
    filename: str
    known_issue: Optional[str] = None


class DatasetList(BaseModel):
    count: int
    recordings: List[RecordingItem]


class Summary(BaseModel):
    dataset_id: str
    participant: str
    take: str
    side: str
    filename: str
    frame_count: int
    column_count: int
    sensor_count: int
    sensor_columns: List[str]
    available_columns: List[str]
    missing_values: int
    has_sump: bool
    value_min: int
    value_max: int
    value_label: str
    sensor_layout_verified: bool
    known_issue: Optional[str] = None


class FrameAnalysis(BaseModel):
    dataset_id: str
    frame_index: int
    frame_count: int
    values: List[int]
    mean: float
    max: int
    max_sensor_index: int
    min: int
    min_sensor_index: int
    total: int
    above_average_sensors: List[int]
    value_label: str
    sensor_layout_verified: bool
    note: str


class TimeSeries(BaseModel):
    dataset_id: str
    frame_count: int
    frames: List[int]
    calculated_sum: List[int]
    sump: Optional[List[float]] = None
    frame_max: List[int]
    frame_mean: List[float]
    value_label: str
    sensor_index: Optional[int] = None
    sensor_series: Optional[List[int]] = None


class SumPCheck(BaseModel):
    available: bool
    matches_exactly: Optional[bool] = None
    max_abs_difference: Optional[float] = None
    mean_abs_difference: Optional[float] = None
    frames_with_difference: Optional[int] = None


class Validation(BaseModel):
    dataset_id: str
    rows: int
    columns: int
    sensor_channels: int
    missing_values: int
    available_columns: List[str]
    sump_check: SumPCheck
    warnings: List[str]