"""
API Router for Decision-Time Wind Forecast Portal.
Implements endpoints:
- GET /api/health
- GET /api/metadata
- GET /api/decision-profile
- GET /api/performance
- GET /api/performance/compare
- GET /api/data-quality
- GET /api/export
"""

import io
import re
from datetime import UTC, date, datetime

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from backend.app.config import (
    CUTOFF_PRESETS,
    DECISION_END_DATE,
    DECISION_START_DATE,
    DEFAULT_CUTOFF,
    DISCLAIMERS,
    MIN_BAND_SAMPLES,
)
from backend.app.repositories.snapshot import get_snapshot_repo
from backend.app.schemas.api_models import (
    CutoffComparisonItem,
    DataQualityResponse,
    DecisionInterval,
    DecisionProfileResponse,
    HealthResponse,
    MetadataResponse,
    PerformanceResponse,
    PresetModel,
)
from backend.app.services.asof_selection import (
    select_decision_forecasts,
    select_decision_forecasts_range,
)
from backend.app.services.data_quality import compute_data_quality_report
from backend.app.services.evaluation import (
    compare_cutoffs_on_common_intervals,
    compute_performance_summary,
    join_forecasts_and_actuals,
)
from backend.app.services.uncertainty import compute_leak_free_uncertainty_band

router = APIRouter(prefix="/api", tags=["wind-forecast-portal"])


def validate_cutoff(cutoff: str) -> None:
    if not re.match(r"^([01]\d|2[0-3]):([0-5]\d)$", cutoff):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid cutoff time format '{cutoff}'. Must be HH:MM in 24-hour UTC (e.g. 09:20).",
        )


def validate_decision_date(d_str: str) -> date:
    try:
        d = date.fromisoformat(d_str)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date format '{d_str}'. Must be YYYY-MM-DD.",
        )

    start = date.fromisoformat(DECISION_START_DATE)
    end = date.fromisoformat(DECISION_END_DATE)
    if d < start or d > end:
        raise HTTPException(
            status_code=400,
            detail=f"Decision date '{d_str}' is outside January 2026 challenge scope ({DECISION_START_DATE} to {DECISION_END_DATE}).",
        )
    return d


def validate_date_range(start_str: str, end_str: str) -> tuple[date, date]:
    s = validate_decision_date(start_str)
    e = validate_decision_date(end_str)
    if s > e:
        raise HTTPException(
            status_code=400,
            detail=f"start_date ({start_str}) cannot be after end_date ({end_str}).",
        )
    return s, e


@router.get("/health", response_model=HealthResponse)
def get_health():
    repo = get_snapshot_repo()
    manifest = repo.get_manifest()
    loaded = bool(manifest and manifest.get("snapshot_sha256"))
    return HealthResponse(
        status="ok",
        timestamp_utc=datetime.now(UTC).isoformat(),
        snapshot_loaded=loaded,
    )


@router.get("/metadata", response_model=MetadataResponse)
def get_metadata():
    repo = get_snapshot_repo()
    manifest = repo.get_manifest()

    presets = [
        PresetModel(
            id=p.id,
            name=p.name,
            cutoff_time=p.cutoff_time,
            description=p.description,
        )
        for p in CUTOFF_PRESETS
    ]

    return MetadataResponse(
        scope={
            "product_name": "Decision-Time Wind Forecast Intelligence Portal",
            "decision_dates": f"{DECISION_START_DATE} to {DECISION_END_DATE}",
            "delivery_dates": "2026-01-02 to 2026-02-01",
            "data_source": "Elexon BMRS API (FUELHH Actuals and WINDFOR Forecasts)",
            "client_context": "UK Energy Utility buying day-ahead power on wholesale markets",
        },
        cutoff_presets=presets,
        default_cutoff=DEFAULT_CUTOFF,
        interval_policy={
            "forecast_resolution": "Hourly (:00 intervals only)",
            "actuals_resolution": "Half-hourly (:00 and :30 intervals)",
            "evaluation_interval_policy": "Exact startTime match on hourly intervals (:00). Missing :30 forecasts remain un-interpolated.",
            "expected_intervals_per_day": 24,
        },
        disclaimers=DISCLAIMERS,
        min_band_samples=MIN_BAND_SAMPLES,
        manifest=manifest,
    )


@router.get("/decision-profile", response_model=DecisionProfileResponse)
def get_decision_profile(
    decision_date: str = Query(
        ..., description="Decision date YYYY-MM-DD (2026-01-01 to 2026-01-31)"
    ),
    cutoff: str = Query(DEFAULT_CUTOFF, description="Cutoff time HH:MM (e.g. 09:20)"),
    include_actuals: bool = Query(
        False,
        description="When true, overlays actuals and errors (Outcome Review mode)",
    ),
    include_band: bool = Query(
        True,
        description="When true, includes leak-free empirical residual uncertainty band",
    ),
):
    d_date = validate_decision_date(decision_date)
    validate_cutoff(cutoff)

    repo = get_snapshot_repo()
    fc_df = repo.load_all_forecasts()
    act_df = repo.load_all_actuals()

    # Select decision-time forecasts
    selected = select_decision_forecasts(fc_df, d_date, cutoff)

    # Uncertainty band
    uncertainty_result = None
    band_lookup = {}
    if include_band:
        uncertainty_result = compute_leak_free_uncertainty_band(
            fc_df, act_df, d_date, cutoff, min_samples=MIN_BAND_SAMPLES
        )
        if uncertainty_result.get("has_band"):
            for b in uncertainty_result.get("band_intervals", []):
                band_lookup[b["start_time"]] = (b["lower_mw"], b["upper_mw"])

    # Actuals lookup (only if include_actuals=True)
    actuals_lookup = {}
    if include_actuals:
        matched = join_forecasts_and_actuals(selected, act_df)
        if not matched.empty:
            for _, r in matched.iterrows():
                actuals_lookup[r["start_time"]] = (r["actual_mw"], r["error_mw"])

    # Build response intervals
    intervals = []
    valid_forecasts = []
    age_list = []

    for _, r in selected.iterrows():
        st = r["start_time"]
        fc_val = r["forecast_mw"]
        if pd.notnull(fc_val):
            valid_forecasts.append(float(fc_val))
        if pd.notnull(r["forecast_age_minutes"]):
            age_list.append(float(r["forecast_age_minutes"]))

        act_val = None
        err_val = None
        if include_actuals and st in actuals_lookup:
            act_val, err_val = actuals_lookup[st]

        lower_val, upper_val = band_lookup.get(st, (None, None))

        intervals.append(
            DecisionInterval(
                start_time=st,
                selected_publish_time=r["selected_publish_time"]
                if pd.notnull(r["selected_publish_time"])
                else None,
                forecast_mw=round(float(fc_val), 1) if pd.notnull(fc_val) else None,
                forecast_age_minutes=r["forecast_age_minutes"]
                if pd.notnull(r["forecast_age_minutes"])
                else None,
                lead_time_hours=r["lead_time_hours"]
                if pd.notnull(r["lead_time_hours"])
                else None,
                actual_mw=round(float(act_val), 1) if act_val is not None else None,
                error_mw=round(float(err_val), 1) if err_val is not None else None,
                lower_mw=lower_val,
                upper_mw=upper_val,
            )
        )

    peak_fc = round(max(valid_forecasts), 1) if valid_forecasts else None
    min_fc = round(min(valid_forecasts), 1) if valid_forecasts else None
    avg_fc = (
        round(sum(valid_forecasts) / len(valid_forecasts), 1)
        if valid_forecasts
        else None
    )
    age_range = (
        f"{round(min(age_list))} - {round(max(age_list))} mins" if age_list else None
    )

    matched_cnt = len(actuals_lookup) if include_actuals else None

    return DecisionProfileResponse(
        decision_date=d_date.isoformat(),
        decision_cutoff=selected["decision_cutoff"].iloc[0],
        delivery_date=selected["delivery_date"].iloc[0],
        selection_policy="latest publication at or before cutoff (startTime >= publishTime)",
        expected_intervals=24,
        forecast_intervals=len(valid_forecasts),
        matched_intervals=matched_cnt,
        peak_forecast_mw=peak_fc,
        min_forecast_mw=min_fc,
        average_forecast_mw=avg_fc,
        forecast_age_range_minutes=age_range,
        intervals=intervals,
        uncertainty=uncertainty_result,
    )


@router.get("/performance", response_model=PerformanceResponse)
def get_performance(
    cutoff: str = Query(DEFAULT_CUTOFF, description="Cutoff time HH:MM"),
    start_date: str = Query(
        DECISION_START_DATE, description="Start decision date YYYY-MM-DD"
    ),
    end_date: str = Query(
        DECISION_END_DATE, description="End decision date YYYY-MM-DD"
    ),
):
    validate_cutoff(cutoff)
    s_date, e_date = validate_date_range(start_date, end_date)

    repo = get_snapshot_repo()
    fc_df = repo.load_all_forecasts()
    act_df = repo.load_all_actuals()

    summary = compute_performance_summary(fc_df, act_df, s_date, e_date, cutoff)
    return PerformanceResponse(**summary)


@router.get("/performance/compare", response_model=list[CutoffComparisonItem])
def get_performance_compare(
    cutoffs: str = Query(
        "09:20,09:50,15:30", description="Comma-separated cutoff times"
    ),
    start_date: str = Query(
        DECISION_START_DATE, description="Start decision date YYYY-MM-DD"
    ),
    end_date: str = Query(
        DECISION_END_DATE, description="End decision date YYYY-MM-DD"
    ),
):
    cutoff_list = [c.strip() for c in cutoffs.split(",") if c.strip()]
    for c in cutoff_list:
        validate_cutoff(c)
    s_date, e_date = validate_date_range(start_date, end_date)

    repo = get_snapshot_repo()
    fc_df = repo.load_all_forecasts()
    act_df = repo.load_all_actuals()

    results = compare_cutoffs_on_common_intervals(
        fc_df, act_df, s_date, e_date, cutoff_list
    )
    return [CutoffComparisonItem(**r) for r in results]


@router.get("/data-quality", response_model=DataQualityResponse)
def get_data_quality(
    cutoff: str = Query(DEFAULT_CUTOFF, description="Cutoff time HH:MM"),
    start_date: str = Query(
        DECISION_START_DATE, description="Start decision date YYYY-MM-DD"
    ),
    end_date: str = Query(
        DECISION_END_DATE, description="End decision date YYYY-MM-DD"
    ),
):
    validate_cutoff(cutoff)
    s_date, e_date = validate_date_range(start_date, end_date)

    repo = get_snapshot_repo()
    fc_df = repo.load_all_forecasts()
    act_df = repo.load_all_actuals()
    manifest = repo.get_manifest()

    report = compute_data_quality_report(
        fc_df, act_df, manifest, s_date, e_date, cutoff
    )
    return DataQualityResponse(**report)


@router.get("/export")
def export_dataset_csv(
    cutoff: str = Query(DEFAULT_CUTOFF, description="Cutoff time HH:MM"),
    start_date: str = Query(
        DECISION_START_DATE, description="Start decision date YYYY-MM-DD"
    ),
    end_date: str = Query(
        DECISION_END_DATE, description="End decision date YYYY-MM-DD"
    ),
):
    validate_cutoff(cutoff)
    s_date, e_date = validate_date_range(start_date, end_date)

    repo = get_snapshot_repo()
    fc_df = repo.load_all_forecasts()
    act_df = repo.load_all_actuals()

    selected = select_decision_forecasts_range(fc_df, s_date, e_date, cutoff)
    matched = join_forecasts_and_actuals(selected, act_df)

    export_cols = [
        "decision_date",
        "decision_cutoff",
        "delivery_date",
        "start_time",
        "selected_publish_time",
        "forecast_age_minutes",
        "lead_time_hours",
        "forecast_mw",
        "actual_mw",
        "error_mw",
    ]
    export_df = (
        matched[export_cols] if not matched.empty else pd.DataFrame(columns=export_cols)
    )

    output = io.StringIO()
    export_df.to_csv(output, index=False)
    output.seek(0)

    filename = f"reint_wind_forecast_export_{s_date.isoformat()}_{e_date.isoformat()}_{cutoff.replace(':', '')}.csv"
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
