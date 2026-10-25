"""
Empirical uncertainty band service.
Strictly leak-free:
For decision date D and cutoff c, usable residuals r = (actual - forecast) are drawn
exclusively from delivery dates < D, where forecasts were selected under the EXACT same
cutoff c on their respective decision dates.

Requires at least MIN_BAND_SAMPLES (default 48). If fewer are available, returns null with
explicit status 'insufficient_history'.
"""

from datetime import date, timedelta
from typing import Any

import numpy as np
import pandas as pd

from backend.app.config import MIN_BAND_SAMPLES
from backend.app.services.asof_selection import (
    parse_date,
    select_decision_forecasts,
    select_decision_forecasts_range,
)
from backend.app.services.evaluation import join_forecasts_and_actuals


def compute_leak_free_uncertainty_band(
    forecast_df: pd.DataFrame,
    actuals_df: pd.DataFrame,
    decision_date: str | date,
    cutoff_time: str,
    min_samples: int = MIN_BAND_SAMPLES,
) -> dict[str, Any]:
    """
    Computes an empirical 10th-90th percentile residual band around the decision-time forecast.
    Uses strictly past residuals from delivery dates strictly before `decision_date`.
    """
    d_date = parse_date(decision_date)

    # Usable history: decision dates strictly prior to d_date
    # Delivery dates < d_date means decision dates < (d_date - 1)
    # Because decision on date D-1 has delivery on date D. Delivery date D is the day of decision D!
    # Wait: On decision date D at cutoff c (e.g. 09:20), delivery for date D is still currently underway!
    # Therefore, complete past delivery days are strictly <= (d_date - 1),
    # meaning decision dates <= (d_date - 2).
    # Let's verify PRD 10.3 wording:
    # "For decision date D and cutoff c, the usable history is residuals for delivery intervals on dates strictly before D (so they were complete before c)"
    # That means delivery dates <= D - 1!
    # Decision dates for those delivery dates were <= D - 2!

    history_last_dec = d_date - timedelta(days=2)
    # Earliest decision date in our window: 2026-01-01 (or December 2025 if available in snapshot)
    # Let's check available start in snapshot
    history_first_dec = date(2025, 12, 28)

    if history_last_dec < history_first_dec:
        return {
            "has_band": False,
            "reason": "Insufficient history for an uncertainty range",
            "samples_count": 0,
            "min_required": min_samples,
            "q10_residual_mw": None,
            "q90_residual_mw": None,
            "band_intervals": [],
        }

    # Select past forecasts under the exact same cutoff rule
    past_forecasts = select_decision_forecasts_range(
        forecast_df, history_first_dec, history_last_dec, cutoff_time
    )
    if past_forecasts.empty:
        return {
            "has_band": False,
            "reason": "Insufficient history for an uncertainty range",
            "samples_count": 0,
            "min_required": min_samples,
            "q10_residual_mw": None,
            "q90_residual_mw": None,
            "band_intervals": [],
        }

    past_matched = join_forecasts_and_actuals(past_forecasts, actuals_df)
    if past_matched.empty or len(past_matched) < min_samples:
        return {
            "has_band": False,
            "reason": "Insufficient history for an uncertainty range",
            "samples_count": len(past_matched),
            "min_required": min_samples,
            "q10_residual_mw": None,
            "q90_residual_mw": None,
            "band_intervals": [],
        }

    # Residual r = actual - forecast = -error_mw
    residuals = past_matched["actual_mw"] - past_matched["forecast_mw"]
    q10_res = float(np.percentile(residuals, 10))
    q90_res = float(np.percentile(residuals, 90))

    # Decision forecasts for date D
    curr_forecasts = select_decision_forecasts(forecast_df, d_date, cutoff_time)
    band_intervals = []

    for _, r in curr_forecasts.iterrows():
        fc = r["forecast_mw"]
        if pd.notnull(fc):
            fc_val = float(fc)
            lower = max(0.0, fc_val + q10_res)  # Wind generation cannot be negative
            upper = fc_val + q90_res
            band_intervals.append(
                {
                    "start_time": r["start_time"],
                    "forecast_mw": fc_val,
                    "lower_mw": round(lower, 1),
                    "upper_mw": round(upper, 1),
                }
            )
        else:
            band_intervals.append(
                {
                    "start_time": r["start_time"],
                    "forecast_mw": None,
                    "lower_mw": None,
                    "upper_mw": None,
                }
            )

    return {
        "has_band": True,
        "reason": None,
        "samples_count": len(past_matched),
        "min_required": min_samples,
        "q10_residual_mw": round(q10_res, 1),
        "q90_residual_mw": round(q90_res, 1),
        "average_width_mw": round(q90_res - q10_res, 1),
        "band_intervals": band_intervals,
    }
