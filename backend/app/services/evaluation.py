"""
Forecast evaluation and error metrics service.
Inputs: selected decision-time forecasts joined with actual generation on `start_time`.
Computes:
- Headline metrics: MAE, RMSE, Bias, WAPE, P90 absolute error, over/under split, coverage, N.
- Breakdowns: by delivery hour, by lead-time band (6h), by day, by actual wind tercile.
- Top positive and negative error outliers.
- Cutoff comparison on common matched intervals.
"""

from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from backend.app.services.asof_selection import (
    parse_date,
    select_decision_forecasts_range,
)


def join_forecasts_and_actuals(
    selected_df: pd.DataFrame,
    actuals_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Inner joins selected forecasts with actuals on start_time.
    Computes signed error e = forecast - actual (MW).
    Positive error indicates overforecast; negative indicates underforecast.
    """
    if selected_df.empty or actuals_df.empty:
        return pd.DataFrame()

    # Drop any null forecasts before joining
    valid_forecasts = selected_df.dropna(subset=["forecast_mw"]).copy()
    if valid_forecasts.empty:
        return pd.DataFrame()

    # Rename actuals columns to avoid collision
    act = actuals_df[["start_time", "generation_mw", "settlement_period"]].copy()
    act = act.rename(columns={"generation_mw": "actual_mw"})

    merged = pd.merge(valid_forecasts, act, on="start_time", how="inner")
    if merged.empty:
        return pd.DataFrame()

    merged["error_mw"] = merged["forecast_mw"] - merged["actual_mw"]
    merged["abs_error_mw"] = merged["error_mw"].abs()
    merged["squared_error_mw2"] = merged["error_mw"] ** 2

    # Derived time features
    st_dt = pd.to_datetime(merged["start_time"], utc=True)
    merged["delivery_hour"] = st_dt.dt.hour

    return merged


def compute_headline_metrics(
    matched_df: pd.DataFrame,
    expected_intervals: int,
) -> dict[str, Any]:
    """Computes standard headline metrics over matched intervals."""
    if matched_df.empty or len(matched_df) == 0:
        return {
            "n_matched": 0,
            "expected_intervals": expected_intervals,
            "coverage_pct": 0.0,
            "mae_mw": None,
            "rmse_mw": None,
            "bias_mw": None,
            "wape": None,
            "p90_abs_error_mw": None,
            "overforecast_pct": None,
            "underforecast_pct": None,
            "exact_match_pct": None,
        }

    n = len(matched_df)
    mae = float(matched_df["abs_error_mw"].mean())
    rmse = float(np.sqrt(matched_df["squared_error_mw2"].mean()))
    bias = float(matched_df["error_mw"].mean())

    sum_abs_err = float(matched_df["abs_error_mw"].sum())
    sum_actual = float(matched_df["actual_mw"].sum())
    wape = round(sum_abs_err / sum_actual, 4) if sum_actual > 0 else None

    p90 = float(np.percentile(matched_df["abs_error_mw"], 90))

    over_count = int((matched_df["error_mw"] > 0).sum())
    under_count = int((matched_df["error_mw"] < 0).sum())
    exact_count = int((matched_df["error_mw"] == 0).sum())

    coverage = (
        round((n / expected_intervals) * 100.0, 2) if expected_intervals > 0 else 0.0
    )

    return {
        "n_matched": n,
        "expected_intervals": expected_intervals,
        "coverage_pct": coverage,
        "mae_mw": round(mae, 2),
        "rmse_mw": round(rmse, 2),
        "bias_mw": round(bias, 2),
        "wape": wape,
        "p90_abs_error_mw": round(p90, 2),
        "overforecast_pct": round((over_count / n) * 100.0, 1),
        "underforecast_pct": round((under_count / n) * 100.0, 1),
        "exact_match_pct": round((exact_count / n) * 100.0, 1),
    }


def compute_hourly_breakdown(matched_df: pd.DataFrame) -> list[dict[str, Any]]:
    if matched_df.empty:
        return []

    results = []
    for hour in range(24):
        sub = matched_df[matched_df["delivery_hour"] == hour]
        if sub.empty:
            continue
        n = len(sub)
        mae = float(sub["abs_error_mw"].mean())
        rmse = float(np.sqrt(sub["squared_error_mw2"].mean()))
        bias = float(sub["error_mw"].mean())
        sum_abs = float(sub["abs_error_mw"].sum())
        sum_act = float(sub["actual_mw"].sum())
        wape = round(sum_abs / sum_act, 4) if sum_act > 0 else None

        results.append(
            {
                "delivery_hour": hour,
                "count": n,
                "mae_mw": round(mae, 2),
                "rmse_mw": round(rmse, 2),
                "bias_mw": round(bias, 2),
                "wape": wape,
                "mean_forecast_mw": round(float(sub["forecast_mw"].mean()), 2),
                "mean_actual_mw": round(float(sub["actual_mw"].mean()), 2),
            }
        )
    return results


def compute_lead_time_breakdown(matched_df: pd.DataFrame) -> list[dict[str, Any]]:
    if matched_df.empty:
        return []

    # 6-hour bands
    df = matched_df.copy()
    bins = [0, 6, 12, 18, 24, 30, 36, 42, 48, 100]
    labels = [
        "0-6h",
        "6-12h",
        "12-18h",
        "18-24h",
        "24-30h",
        "30-36h",
        "36-42h",
        "42-48h",
        "48h+",
    ]
    df["lead_band"] = pd.cut(
        df["lead_time_hours"], bins=bins, labels=labels, right=False
    )

    results = []
    for band in labels:
        sub = df[df["lead_band"] == band]
        if sub.empty:
            continue
        n = len(sub)
        mae = float(sub["abs_error_mw"].mean())
        rmse = float(np.sqrt(sub["squared_error_mw2"].mean()))
        bias = float(sub["error_mw"].mean())
        sum_abs = float(sub["abs_error_mw"].sum())
        sum_act = float(sub["actual_mw"].sum())
        wape = round(sum_abs / sum_act, 4) if sum_act > 0 else None

        results.append(
            {
                "lead_time_band": band,
                "count": n,
                "mae_mw": round(mae, 2),
                "rmse_mw": round(rmse, 2),
                "bias_mw": round(bias, 2),
                "wape": wape,
            }
        )
    return results


def compute_daily_breakdown(matched_df: pd.DataFrame) -> list[dict[str, Any]]:
    if matched_df.empty:
        return []

    results = []
    for (dec_date, del_date), sub in matched_df.groupby(
        ["decision_date", "delivery_date"], sort=True
    ):
        n = len(sub)
        mae = float(sub["abs_error_mw"].mean())
        rmse = float(np.sqrt(sub["squared_error_mw2"].mean()))
        bias = float(sub["error_mw"].mean())
        sum_abs = float(sub["abs_error_mw"].sum())
        sum_act = float(sub["actual_mw"].sum())
        wape = round(sum_abs / sum_act, 4) if sum_act > 0 else None

        results.append(
            {
                "decision_date": dec_date,
                "delivery_date": del_date,
                "count": n,
                "coverage_pct": round((n / 24) * 100.0, 1),
                "mae_mw": round(mae, 2),
                "rmse_mw": round(rmse, 2),
                "bias_mw": round(bias, 2),
                "wape": wape,
                "mean_forecast_mw": round(float(sub["forecast_mw"].mean()), 2),
                "mean_actual_mw": round(float(sub["actual_mw"].mean()), 2),
            }
        )
    return results


def compute_wind_level_breakdown(matched_df: pd.DataFrame) -> list[dict[str, Any]]:
    if matched_df.empty or len(matched_df) < 3:
        return []

    df = matched_df.copy()
    try:
        df["tercile"] = pd.qcut(
            df["actual_mw"], q=3, labels=["Low Wind", "Medium Wind", "High Wind"]
        )
    except ValueError:
        return []

    results = []
    for t_label in ["Low Wind", "Medium Wind", "High Wind"]:
        sub = df[df["tercile"] == t_label]
        if sub.empty:
            continue
        n = len(sub)
        min_act = float(sub["actual_mw"].min())
        max_act = float(sub["actual_mw"].max())
        mae = float(sub["abs_error_mw"].mean())
        rmse = float(np.sqrt(sub["squared_error_mw2"].mean()))
        bias = float(sub["error_mw"].mean())
        sum_abs = float(sub["abs_error_mw"].sum())
        sum_act = float(sub["actual_mw"].sum())
        wape = round(sum_abs / sum_act, 4) if sum_act > 0 else None

        results.append(
            {
                "tercile": t_label,
                "range_mw": f"{round(min_act)} - {round(max_act)} MW",
                "count": n,
                "mae_mw": round(mae, 2),
                "rmse_mw": round(rmse, 2),
                "bias_mw": round(bias, 2),
                "wape": wape,
            }
        )
    return results


def compute_top_errors(
    matched_df: pd.DataFrame, top_n: int = 10
) -> dict[str, list[dict[str, Any]]]:
    if matched_df.empty:
        return {"largest_overforecasts": [], "largest_underforecasts": []}

    # Largest positive errors (forecast > actual)
    top_pos = matched_df.sort_values(by="error_mw", ascending=False).head(top_n)
    # Largest negative errors (actual > forecast, so most negative error_mw)
    top_neg = matched_df.sort_values(by="error_mw", ascending=True).head(top_n)

    def format_rows(sub_df):
        out = []
        for _, r in sub_df.iterrows():
            out.append(
                {
                    "start_time": r["start_time"],
                    "decision_date": r["decision_date"],
                    "delivery_date": r["delivery_date"],
                    "forecast_mw": round(float(r["forecast_mw"]), 1),
                    "actual_mw": round(float(r["actual_mw"]), 1),
                    "error_mw": round(float(r["error_mw"]), 1),
                    "lead_time_hours": round(float(r["lead_time_hours"]), 1)
                    if pd.notnull(r["lead_time_hours"])
                    else None,
                }
            )
        return out

    return {
        "largest_overforecasts": format_rows(top_pos),
        "largest_underforecasts": format_rows(top_neg),
    }


def compute_performance_summary(
    forecast_df: pd.DataFrame,
    actuals_df: pd.DataFrame,
    start_date: str | date,
    end_date: str | date,
    cutoff_time: str,
) -> dict[str, Any]:
    """Generates the full performance evaluation response."""
    d_start = parse_date(start_date)
    d_end = parse_date(end_date)
    num_days = (d_end - d_start).days + 1
    expected_intervals = num_days * 24

    selected = select_decision_forecasts_range(forecast_df, d_start, d_end, cutoff_time)
    matched = join_forecasts_and_actuals(selected, actuals_df)

    headline = compute_headline_metrics(matched, expected_intervals)
    hourly = compute_hourly_breakdown(matched)
    lead_time = compute_lead_time_breakdown(matched)
    daily = compute_daily_breakdown(matched)
    wind_level = compute_wind_level_breakdown(matched)
    top_errs = compute_top_errors(matched, top_n=10)

    # Automated so-what callout based strictly on real computed numbers
    so_what = "Data evaluated across the specified period."
    if wind_level:
        low_w = next((w for w in wind_level if w["tercile"] == "Low Wind"), None)
        high_w = next((w for w in wind_level if w["tercile"] == "High Wind"), None)
        if low_w and high_w:
            bias_dir_low = "overforecast" if low_w["bias_mw"] > 0 else "underforecast"
            bias_dir_high = "overforecast" if high_w["bias_mw"] > 0 else "underforecast"
            so_what = (
                f"On low-wind intervals ({low_w['range_mw']}), the forecast tended to {bias_dir_low} "
                f"by {abs(low_w['bias_mw'])} MW on average (MAE: {low_w['mae_mw']} MW), "
                f"while high-wind intervals ({high_w['range_mw']}) tended to {bias_dir_high} "
                f"by {abs(high_w['bias_mw'])} MW on average (MAE: {high_w['mae_mw']} MW)."
            )

    return {
        "cutoff_time": cutoff_time,
        "start_date": d_start.isoformat(),
        "end_date": d_end.isoformat(),
        "headline": headline,
        "hourly_breakdown": hourly,
        "lead_time_breakdown": lead_time,
        "daily_breakdown": daily,
        "wind_level_breakdown": wind_level,
        "top_errors": top_errs,
        "so_what": so_what,
    }


def compare_cutoffs_on_common_intervals(
    forecast_df: pd.DataFrame,
    actuals_df: pd.DataFrame,
    start_date: str | date,
    end_date: str | date,
    cutoff_list: list[str],
) -> list[dict[str, Any]]:
    """
    Computes comparative metrics for multiple cutoffs strictly evaluated
    on the intersection of common matched intervals.
    """
    d_start = parse_date(start_date)
    d_end = parse_date(end_date)

    matched_by_cutoff: dict[str, pd.DataFrame] = {}
    valid_keys_by_cutoff: dict[str, set] = {}

    for c in cutoff_list:
        sel = select_decision_forecasts_range(forecast_df, d_start, d_end, c)
        m = join_forecasts_and_actuals(sel, actuals_df)
        matched_by_cutoff[c] = m
        valid_keys_by_cutoff[c] = set(m["start_time"]) if not m.empty else set()

    if not valid_keys_by_cutoff:
        return []

    # Intersection of matched start_times across all cutoffs
    common_keys = (
        set.intersection(*valid_keys_by_cutoff.values())
        if valid_keys_by_cutoff
        else set()
    )

    results = []
    for c in cutoff_list:
        m = matched_by_cutoff[c]
        if not m.empty and common_keys:
            common_m = m[m["start_time"].isin(common_keys)].copy()
            metrics = compute_headline_metrics(common_m, len(common_keys))
        else:
            metrics = compute_headline_metrics(pd.DataFrame(), 0)

        results.append(
            {
                "cutoff_time": c,
                "n_common_intervals": len(common_keys),
                "mae_mw": metrics["mae_mw"],
                "rmse_mw": metrics["rmse_mw"],
                "bias_mw": metrics["bias_mw"],
                "wape": metrics["wape"],
                "p90_abs_error_mw": metrics["p90_abs_error_mw"],
            }
        )

    return results
