"""
Data quality and audit service.
Analyzes coverage, missing intervals, duplicates, negative lead-time exclusions,
and integrity metrics for a requested decision date range and cutoff.
"""

from datetime import date
from typing import Any

import pandas as pd

from backend.app.services.asof_selection import (
    parse_date,
    select_decision_forecasts_range,
)
from backend.app.services.evaluation import join_forecasts_and_actuals


def compute_data_quality_report(
    forecast_df: pd.DataFrame,
    actuals_df: pd.DataFrame,
    manifest: dict[str, Any],
    start_date: str | date,
    end_date: str | date,
    cutoff_time: str,
) -> dict[str, Any]:
    """Generates a complete data quality audit report."""
    d_start = parse_date(start_date)
    d_end = parse_date(end_date)
    num_days = (d_end - d_start).days + 1
    expected_intervals = num_days * 24

    selected = select_decision_forecasts_range(forecast_df, d_start, d_end, cutoff_time)
    intervals_with_forecast = (
        int(selected["forecast_mw"].notnull().sum()) if not selected.empty else 0
    )

    # Delivery dates range
    deliv_start = (d_start + pd.Timedelta(days=1)).isoformat()
    deliv_end = (d_end + pd.Timedelta(days=1)).isoformat()

    # Actuals for delivery dates
    act_in_scope = actuals_df[
        (actuals_df["settlement_date"] >= deliv_start)
        & (actuals_df["settlement_date"] <= deliv_end)
    ]
    # Filter to hourly actuals (:00)
    hourly_actuals = act_in_scope[act_in_scope["start_time"].str.endswith(":00:00Z")]
    intervals_with_actuals = len(hourly_actuals)

    matched = join_forecasts_and_actuals(selected, actuals_df)
    n_matched = len(matched) if not matched.empty else 0

    coverage_pct = (
        round((n_matched / expected_intervals) * 100.0, 2)
        if expected_intervals > 0
        else 0.0
    )

    # Validation from manifest
    f_val = (
        manifest.get("tables", {}).get("forecast_revisions", {}).get("validation", {})
    )
    a_val = manifest.get("tables", {}).get("actuals", {}).get("validation", {})

    negative_lead_count = f_val.get("negative_lead_rows_count", 0)
    conflicting_forecast_duplicates = f_val.get("conflicting_duplicates_count", 0)
    conflicting_actual_duplicates = a_val.get("conflicting_duplicates_count", 0)

    warnings: list[str] = list(manifest.get("validation_warnings", []))
    if intervals_with_forecast < expected_intervals:
        missing_count = expected_intervals - intervals_with_forecast
        warnings.append(
            f"{missing_count} target delivery intervals have no eligible forecast at cutoff {cutoff_time}."
        )
    if intervals_with_actuals < expected_intervals:
        missing_act = expected_intervals - intervals_with_actuals
        warnings.append(
            f"{missing_act} target delivery intervals have missing settlement actuals."
        )

    mean_forecast_mw = None
    mean_actual_mw = None
    forecast_actual_ratio = None
    if not matched.empty:
        mean_forecast_mw = round(float(matched["forecast_mw"].mean()), 2)
        mean_actual_mw = round(float(matched["actual_mw"].mean()), 2)
        sum_act = float(matched["actual_mw"].sum())
        if sum_act > 0:
            forecast_actual_ratio = round(
                float(matched["forecast_mw"].sum() / sum_act), 4
            )

    return {
        "start_date": d_start.isoformat(),
        "end_date": d_end.isoformat(),
        "cutoff_time": cutoff_time,
        "expected_intervals": expected_intervals,
        "intervals_with_forecast": intervals_with_forecast,
        "intervals_with_actuals": intervals_with_actuals,
        "matched_pairs": n_matched,
        "coverage_percentage": coverage_pct,
        "negative_lead_rows_excluded": negative_lead_count,
        "conflicting_forecast_duplicates": conflicting_forecast_duplicates,
        "conflicting_actual_duplicates": conflicting_actual_duplicates,
        "mean_forecast_mw": mean_forecast_mw,
        "mean_actual_mw": mean_actual_mw,
        "forecast_actual_ratio": forecast_actual_ratio,
        "extraction_timestamp_utc": manifest.get("extraction_timestamp_utc"),
        "snapshot_sha256": manifest.get("snapshot_sha256"),
        "api_base_url": manifest.get("api_base_url"),
        "warnings": warnings,
    }
