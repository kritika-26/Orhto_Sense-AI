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


class SensorPosition(BaseModel):
    csv_index: int
    label: int
    x: float
    y: float


class EvidenceTest(BaseModel):
    spearman_rho: float
    best_of_3000_shuffles: float


class LayoutEvidence(BaseModel):
    steps_used: int
    loaded_frames_used: int
    heel_to_toe_timing: EvidenceTest
    neighbour_similarity: EvidenceTest


class Layout(BaseModel):
    side: str
    status: str
    mapping: str
    method: str
    limits: str
    width: float
    height: float
    radius: float
    sensors: List[SensorPosition]
    evidence: LayoutEvidence


class DesignParameters(BaseModel):
    top_percent: int
    relief_depth_mm: float
    base_thickness_mm: float
    peak_definition: str
    values_are_demonstration_only: bool


class DesignDimensions(BaseModel):
    length: float
    width: float
    thickness: float


class DesignZone(BaseModel):
    id: str
    sensor_indices: List[int]
    peak_value: int
    centre_x_mm: float
    centre_y_mm: float
    position_along_insole: str


class DesignSensor(BaseModel):
    csv_index: int
    label: int
    x_mm: float
    y_mm: float
    peak_value: int
    selected: bool
    zone: Optional[str] = None


class OrthoticDesign(BaseModel):
    dataset_id: str
    side: str
    parameters: DesignParameters
    dimensions_mm: DesignDimensions
    scale_basis: str
    pocket_radius_mm: float
    selected_count: int
    zones: List[DesignZone]
    sensors: List[DesignSensor]
    outline_mm: List[List[float]]
    warnings: List[str]
    disclaimer: str
