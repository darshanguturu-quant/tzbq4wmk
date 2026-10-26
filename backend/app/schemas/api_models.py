"""
Pydantic schemas for the Decision-Time Wind Forecast Portal API.
"""

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    timestamp_utc: str
    snapshot_loaded: bool


class PresetModel(BaseModel):
    id: str
    name: str
    cutoff_time: str
    description: str


class MetadataResponse(BaseModel):
    scope: dict[str, Any]
    cutoff_presets: list[PresetModel]
    default_cutoff: str
    interval_policy: dict[str, Any]
    disclaimers: dict[str, str]
    min_band_samples: int
    manifest: dict[str, Any]


class DecisionInterval(BaseModel):
    start_time: str
    selected_publish_time: str | None = None
    forecast_mw: float | None = None
    forecast_age_minutes: float | None = None
    lead_time_hours: float | None = None
    actual_mw: float | None = None
    error_mw: float | None = None
    lower_mw: float | None = None
    upper_mw: float | None = None


class DecisionProfileResponse(BaseModel):
    decision_date: str
    decision_cutoff: str
    delivery_date: str
    selection_policy: str
    expected_intervals: int
    forecast_intervals: int
    matched_intervals: int | None = None
    peak_forecast_mw: float | None = None
    min_forecast_mw: float | None = None
    average_forecast_mw: float | None = None
    forecast_age_range_minutes: str | None = None
    intervals: list[DecisionInterval]
    uncertainty: dict[str, Any] | None = None


class HeadlineMetrics(BaseModel):
    n_matched: int
    expected_intervals: int
    coverage_pct: float
    mae_mw: float | None = None
    rmse_mw: float | None = None
    bias_mw: float | None = None
    wape: float | None = None
    p90_abs_error_mw: float | None = None
    overforecast_pct: float | None = None
    underforecast_pct: float | None = None
    exact_match_pct: float | None = None


class PerformanceResponse(BaseModel):
    cutoff_time: str
    start_date: str
    end_date: str
    headline: HeadlineMetrics
    hourly_breakdown: list[dict[str, Any]]
    lead_time_breakdown: list[dict[str, Any]]
    daily_breakdown: list[dict[str, Any]]
    wind_level_breakdown: list[dict[str, Any]]
    top_errors: dict[str, list[dict[str, Any]]]
    so_what: str


class CutoffComparisonItem(BaseModel):
    cutoff_time: str
    n_common_intervals: int
    mae_mw: float | None = None
    rmse_mw: float | None = None
    bias_mw: float | None = None
    wape: float | None = None
    p90_abs_error_mw: float | None = None


class DataQualityResponse(BaseModel):
    start_date: str
    end_date: str
    cutoff_time: str
    expected_intervals: int
    intervals_with_forecast: int
    intervals_with_actuals: int
    matched_pairs: int
    coverage_percentage: float
    negative_lead_rows_excluded: int
    conflicting_forecast_duplicates: int
    conflicting_actual_duplicates: int
    mean_forecast_mw: float | None = None
    mean_actual_mw: float | None = None
    forecast_actual_ratio: float | None = None
    extraction_timestamp_utc: str | None = None
    snapshot_sha256: str | None = None
    api_base_url: str | None = None
    warnings: list[str] = Field(default_factory=list)
