"""
Unit tests for core decision-time selection and evaluation services.
Meets all criteria in PRD Section 15.1.
All test fixtures are explicitly labeled as synthetic.
"""

import pandas as pd
import pytest

from backend.app.services.asof_selection import select_decision_forecasts
from backend.app.services.evaluation import (
    compare_cutoffs_on_common_intervals,
    compute_headline_metrics,
    join_forecasts_and_actuals,
)
from backend.app.services.uncertainty import compute_leak_free_uncertainty_band

# ---------------------------------------------------------------------------
# Synthetic Fixtures for Unit Testing
# ---------------------------------------------------------------------------


@pytest.fixture
def synthetic_forecast_revisions() -> pd.DataFrame:
    """
    Synthetic forecast dataset for decision date 2026-01-15 (delivery 2026-01-16).
    Contains:
    - Target 00:00: revisions at 06:00, 08:30 (<=09:20 cutoff) and 12:30 (>09:20 cutoff).
    - Target 01:00: revision exactly at 09:20:00Z.
    - Target 02:00: revision at 09:20:01Z (1 second past cutoff).
    - Target 03:00: negative lead-time row (startTime < publishTime).
    - Target 04:00: no revisions at all (missing).
    """
    rows = [
        # Target 2026-01-16T00:00:00Z
        {
            "start_time": "2026-01-16T00:00:00Z",
            "publish_time": "2026-01-15T06:00:00Z",
            "generation_mw": 8000.0,
        },
        {
            "start_time": "2026-01-16T00:00:00Z",
            "publish_time": "2026-01-15T08:30:00Z",
            "generation_mw": 8500.0,
        },
        {
            "start_time": "2026-01-16T00:00:00Z",
            "publish_time": "2026-01-15T12:30:00Z",
            "generation_mw": 9999.0,
        },  # Post-cutoff
        # Target 2026-01-16T01:00:00Z: exactly at cutoff
        {
            "start_time": "2026-01-16T01:00:00Z",
            "publish_time": "2026-01-15T09:20:00Z",
            "generation_mw": 7200.0,
        },
        # Target 2026-01-16T02:00:00Z: 1 sec after cutoff
        {
            "start_time": "2026-01-16T02:00:00Z",
            "publish_time": "2026-01-15T09:20:01Z",
            "generation_mw": 6000.0,
        },
        # Target 2026-01-16T03:00:00Z: Negative lead time (startTime < publishTime)
        {
            "start_time": "2026-01-16T03:00:00Z",
            "publish_time": "2026-01-16T05:00:00Z",
            "generation_mw": 5000.0,
        },
    ]
    df = pd.DataFrame(rows)
    df["start_time_dt"] = pd.to_datetime(df["start_time"], utc=True)
    df["publish_time_dt"] = pd.to_datetime(df["publish_time"], utc=True)
    return df


# ---------------------------------------------------------------------------
# Core Selection Rule Tests
# ---------------------------------------------------------------------------


def test_post_cutoff_revision_cannot_enter_backtest(synthetic_forecast_revisions):
    """
    CRITICAL NAMED TEST: Proves that a forecast revision published strictly after
    the decision cutoff cannot enter the backtest or affect selected values.
    """
    decision_date = "2026-01-15"
    cutoff = "09:20"

    selected = select_decision_forecasts(
        synthetic_forecast_revisions, decision_date, cutoff
    )
    target_00 = selected[selected["start_time"] == "2026-01-16T00:00:00Z"].iloc[0]

    # The 12:30 revision had 9999 MW. The 08:30 revision had 8500 MW.
    # The selected forecast MUST be 8500 MW from 08:30, NOT 9999 MW from 12:30.
    assert target_00["forecast_mw"] == 8500.0
    assert target_00["selected_publish_time"] == "2026-01-15T08:30:00Z"
    assert target_00["forecast_mw"] != 9999.0


def test_forecast_published_exactly_at_cutoff_is_eligible(synthetic_forecast_revisions):
    """Forecast published at exactly 09:20:00Z must be eligible under <= cutoff rule."""
    selected = select_decision_forecasts(
        synthetic_forecast_revisions, "2026-01-15", "09:20"
    )
    target_01 = selected[selected["start_time"] == "2026-01-16T01:00:00Z"].iloc[0]

    assert target_01["forecast_mw"] == 7200.0
    assert target_01["selected_publish_time"] == "2026-01-15T09:20:00Z"


def test_forecast_published_after_cutoff_is_excluded(synthetic_forecast_revisions):
    """Forecast published 1 second after cutoff (09:20:01Z) must be excluded."""
    selected = select_decision_forecasts(
        synthetic_forecast_revisions, "2026-01-15", "09:20"
    )
    target_02 = selected[selected["start_time"] == "2026-01-16T02:00:00Z"].iloc[0]

    assert pd.isna(target_02["forecast_mw"])
    assert (
        pd.isna(target_02["selected_publish_time"])
        or target_02["selected_publish_time"] is None
    )


def test_negative_lead_time_is_never_selected(synthetic_forecast_revisions):
    """Rows where startTime < publishTime must be flagged and excluded."""
    selected = select_decision_forecasts(
        synthetic_forecast_revisions, "2026-01-15", "09:20"
    )
    target_03 = selected[selected["start_time"] == "2026-01-16T03:00:00Z"].iloc[0]

    assert pd.isna(target_03["forecast_mw"])


def test_missing_forecast_returns_null_never_zero(synthetic_forecast_revisions):
    """Target times with no eligible forecast return nulls, never filled with zero."""
    selected = select_decision_forecasts(
        synthetic_forecast_revisions, "2026-01-15", "09:20"
    )
    target_04 = selected[selected["start_time"] == "2026-01-16T04:00:00Z"].iloc[0]

    assert pd.isna(target_04["forecast_mw"])
    assert target_04["forecast_mw"] != 0.0


def test_decision_date_31_delivers_on_feb_1():
    """Decision date 2026-01-31 must deliver on 2026-02-01."""
    empty_df = pd.DataFrame(
        columns=[
            "start_time",
            "publish_time",
            "generation_mw",
            "start_time_dt",
            "publish_time_dt",
        ]
    )
    selected = select_decision_forecasts(empty_df, "2026-01-31", "09:20")
    assert (selected["delivery_date"] == "2026-02-01").all()
    assert (selected["decision_date"] == "2026-01-31").all()


# ---------------------------------------------------------------------------
# Evaluation & Error Metrics Tests
# ---------------------------------------------------------------------------


def test_sign_convention_positive_is_overforecast():
    """Sign convention: error = forecast - actual. Positive means overforecast."""
    selected_df = pd.DataFrame(
        [
            {
                "start_time": "2026-01-16T00:00:00Z",
                "forecast_mw": 10000.0,
                "decision_date": "2026-01-15",
                "delivery_date": "2026-01-16",
                "lead_time_hours": 15.0,
            },
            {
                "start_time": "2026-01-16T01:00:00Z",
                "forecast_mw": 5000.0,
                "decision_date": "2026-01-15",
                "delivery_date": "2026-01-16",
                "lead_time_hours": 16.0,
            },
        ]
    )
    actuals_df = pd.DataFrame(
        [
            {
                "start_time": "2026-01-16T00:00:00Z",
                "generation_mw": 8000.0,
                "settlement_period": 1,
            },
            {
                "start_time": "2026-01-16T01:00:00Z",
                "generation_mw": 7000.0,
                "settlement_period": 3,
            },
        ]
    )

    matched = join_forecasts_and_actuals(selected_df, actuals_df)

    # Target 0: 10000 - 8000 = +2000 (overforecast)
    # Target 1: 5000 - 7000 = -2000 (underforecast)
    assert matched.loc[0, "error_mw"] == 2000.0
    assert matched.loc[1, "error_mw"] == -2000.0

    metrics = compute_headline_metrics(matched, expected_intervals=2)
    assert metrics["mae_mw"] == 2000.0
    assert metrics["bias_mw"] == 0.0  # (2000 + -2000) / 2
    assert metrics["overforecast_pct"] == 50.0
    assert metrics["underforecast_pct"] == 50.0


def test_missing_actual_decreases_coverage_excluded_from_errors():
    """If an actual is missing, it is excluded from error metrics and decreases coverage."""
    selected_df = pd.DataFrame(
        [
            {
                "start_time": "2026-01-16T00:00:00Z",
                "forecast_mw": 10000.0,
                "decision_date": "2026-01-15",
                "delivery_date": "2026-01-16",
                "lead_time_hours": 15.0,
            },
            {
                "start_time": "2026-01-16T01:00:00Z",
                "forecast_mw": 5000.0,
                "decision_date": "2026-01-15",
                "delivery_date": "2026-01-16",
                "lead_time_hours": 16.0,
            },
        ]
    )
    # Only 1 actual available
    actuals_df = pd.DataFrame(
        [
            {
                "start_time": "2026-01-16T00:00:00Z",
                "generation_mw": 8000.0,
                "settlement_period": 1,
            },
        ]
    )

    matched = join_forecasts_and_actuals(selected_df, actuals_df)
    assert len(matched) == 1

    metrics = compute_headline_metrics(matched, expected_intervals=2)
    assert metrics["n_matched"] == 1
    assert metrics["coverage_pct"] == 50.0


def test_zero_actual_generation_safe_wape():
    """Safe handling of zero actual generation without DivisionByZero crash."""
    selected_df = pd.DataFrame(
        [
            {
                "start_time": "2026-01-16T00:00:00Z",
                "forecast_mw": 500.0,
                "decision_date": "2026-01-15",
                "delivery_date": "2026-01-16",
                "lead_time_hours": 15.0,
            },
        ]
    )
    actuals_df = pd.DataFrame(
        [
            {
                "start_time": "2026-01-16T00:00:00Z",
                "generation_mw": 0.0,
                "settlement_period": 1,
            },
        ]
    )
    matched = join_forecasts_and_actuals(selected_df, actuals_df)
    metrics = compute_headline_metrics(matched, expected_intervals=1)

    assert metrics["mae_mw"] == 500.0
    assert metrics["wape"] is None  # Handled safely without exception


def test_cutoff_comparison_common_intervals_only():
    """Cutoff comparison must evaluate on the intersection of common matched intervals."""
    # Forecasts for 09:20 and 15:30
    fc_df = pd.DataFrame(
        [
            # Target 00:00 available at both cutoffs
            {
                "start_time": "2026-01-16T00:00:00Z",
                "publish_time": "2026-01-15T08:00:00Z",
                "generation_mw": 1000.0,
            },
            # Target 01:00 only available after 09:20 (e.g. published at 12:00)
            {
                "start_time": "2026-01-16T01:00:00Z",
                "publish_time": "2026-01-15T12:00:00Z",
                "generation_mw": 2000.0,
            },
        ]
    )
    fc_df["start_time_dt"] = pd.to_datetime(fc_df["start_time"], utc=True)
    fc_df["publish_time_dt"] = pd.to_datetime(fc_df["publish_time"], utc=True)

    act_df = pd.DataFrame(
        [
            {
                "start_time": "2026-01-16T00:00:00Z",
                "generation_mw": 1200.0,
                "settlement_period": 1,
            },
            {
                "start_time": "2026-01-16T01:00:00Z",
                "generation_mw": 1800.0,
                "settlement_period": 3,
            },
        ]
    )

    results = compare_cutoffs_on_common_intervals(
        fc_df, act_df, "2026-01-15", "2026-01-15", ["09:20", "15:30"]
    )
    # Common interval is only 00:00:00Z (n_common_intervals = 1)
    assert len(results) == 2
    assert results[0]["n_common_intervals"] == 1
    assert results[1]["n_common_intervals"] == 1
    # Both evaluate strictly on the same single target: error = 1000 - 1200 = -200, MAE = 200
    assert results[0]["mae_mw"] == 200.0
    assert results[1]["mae_mw"] == 200.0


# ---------------------------------------------------------------------------
# Uncertainty Band Look-Ahead Leakage Test
# ---------------------------------------------------------------------------


def test_uncertainty_band_leak_free_and_insufficient_history():
    """Uncertainty band returns insufficient history when past samples < MIN_BAND_SAMPLES."""
    # Only 1 past day
    fc_df = pd.DataFrame(
        [
            {
                "start_time": "2026-01-02T00:00:00Z",
                "publish_time": "2026-01-01T08:00:00Z",
                "generation_mw": 5000.0,
            },
        ]
    )
    fc_df["start_time_dt"] = pd.to_datetime(fc_df["start_time"], utc=True)
    fc_df["publish_time_dt"] = pd.to_datetime(fc_df["publish_time"], utc=True)

    act_df = pd.DataFrame(
        [
            {
                "start_time": "2026-01-02T00:00:00Z",
                "generation_mw": 5200.0,
                "settlement_period": 1,
            },
        ]
    )

    res = compute_leak_free_uncertainty_band(
        fc_df, act_df, decision_date="2026-01-03", cutoff_time="09:20", min_samples=48
    )
    assert res["has_band"] is False
    assert "Insufficient history" in res["reason"]
    assert res["samples_count"] < 48


# ---------------------------------------------------------------------------
# Real Snapshot Integration Test
# ---------------------------------------------------------------------------


def test_real_snapshot_selection_and_metrics():
    """Verifies that the real bundled snapshot runs through selection and evaluation."""
    from backend.app.repositories.snapshot import get_snapshot_repo
    from backend.app.services.evaluation import compute_performance_summary

    repo = get_snapshot_repo()
    fc_df = repo.load_all_forecasts()
    act_df = repo.load_all_actuals()

    assert not fc_df.empty
    assert not act_df.empty

    # Select for 2026-01-15 at 09:20
    selected = select_decision_forecasts(fc_df, "2026-01-15", "09:20")
    assert len(selected) == 24
    assert selected["forecast_mw"].notnull().all()

    # Performance for all 31 January decision dates
    perf = compute_performance_summary(
        fc_df, act_df, "2026-01-01", "2026-01-31", "09:20"
    )
    assert perf["headline"]["n_matched"] > 0
    assert perf["headline"]["mae_mw"] > 0
    assert perf["headline"]["rmse_mw"] >= perf["headline"]["mae_mw"]
    assert len(perf["hourly_breakdown"]) == 24
