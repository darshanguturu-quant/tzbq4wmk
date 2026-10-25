"""
Decision-time forecast selection service.
Core domain rule:
A forecast is eligible for target time `t` at cutoff `c` on decision date `D` iff:
1. `publish_time <= c`
2. `start_time >= publish_time` (no negative lead time)
3. `start_time == t` (where `t` is on delivery date `D + 1`)

If multiple revisions are eligible, the row with the latest `publish_time` is selected.
If no revisions are eligible, the target interval is returned with nulls (never filled with zero).
"""

from datetime import UTC, date, datetime, timedelta

import pandas as pd


def parse_date(d: str | date) -> date:
    if isinstance(d, str):
        return date.fromisoformat(d)
    return d


def select_decision_forecasts(
    forecast_df: pd.DataFrame,
    decision_date: str | date,
    cutoff_time: str,
) -> pd.DataFrame:
    """
    Selects the latest available forecast for each delivery interval of `decision_date + 1`
    published at or before `cutoff_time` on `decision_date`.
    """
    d_date = parse_date(decision_date)
    deliv_date = d_date + timedelta(days=1)

    # Parse cutoff time
    parts = cutoff_time.split(":")
    ch, cm = int(parts[0]), int(parts[1])
    cutoff_dt = datetime(d_date.year, d_date.month, d_date.day, ch, cm, 0, tzinfo=UTC)
    cutoff_iso = cutoff_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Generate the 24 expected hourly delivery targets (00:00 to 23:00 UTC)
    expected_targets = [
        datetime(deliv_date.year, deliv_date.month, deliv_date.day, h, 0, 0, tzinfo=UTC)
        for h in range(24)
    ]
    expected_targets_iso = [
        dt.strftime("%Y-%m-%dT%H:%M:%SZ") for dt in expected_targets
    ]

    if forecast_df.empty:
        rows = []
        for t_iso in expected_targets_iso:
            rows.append(
                {
                    "decision_date": d_date.isoformat(),
                    "decision_cutoff": cutoff_iso,
                    "delivery_date": deliv_date.isoformat(),
                    "start_time": t_iso,
                    "selected_publish_time": None,
                    "forecast_mw": None,
                    "forecast_age_minutes": None,
                    "lead_time_hours": None,
                }
            )
        return pd.DataFrame(rows)

    # Filter eligible records:
    # 1. publish_time_dt <= cutoff_dt
    # 2. start_time_dt >= publish_time_dt
    # 3. start_time in expected delivery targets
    eligible = forecast_df[
        (forecast_df["publish_time_dt"] <= cutoff_dt)
        & (forecast_df["start_time_dt"] >= forecast_df["publish_time_dt"])
        & (forecast_df["start_time"].isin(expected_targets_iso))
    ]

    selected_rows = []
    if not eligible.empty:
        # Sort by start_time_dt asc, publish_time_dt desc
        # drop_duplicates on start_time keeps the latest publish_time
        latest_revisions = (
            eligible.sort_values(
                by=["start_time_dt", "publish_time_dt"], ascending=[True, False]
            )
            .drop_duplicates(subset=["start_time"], keep="first")
            .set_index("start_time")
        )
    else:
        latest_revisions = pd.DataFrame()

    for t_dt, t_iso in zip(expected_targets, expected_targets_iso):
        if t_iso in latest_revisions.index:
            row = latest_revisions.loc[t_iso]
            pub_dt = row["publish_time_dt"]
            pub_iso = row["publish_time"]
            fc_mw = float(row["generation_mw"])
            age_min = round((cutoff_dt - pub_dt).total_seconds() / 60.0, 1)
            lead_hrs = round((t_dt - pub_dt).total_seconds() / 3600.0, 1)

            selected_rows.append(
                {
                    "decision_date": d_date.isoformat(),
                    "decision_cutoff": cutoff_iso,
                    "delivery_date": deliv_date.isoformat(),
                    "start_time": t_iso,
                    "selected_publish_time": pub_iso,
                    "forecast_mw": fc_mw,
                    "forecast_age_minutes": age_min,
                    "lead_time_hours": lead_hrs,
                }
            )
        else:
            selected_rows.append(
                {
                    "decision_date": d_date.isoformat(),
                    "decision_cutoff": cutoff_iso,
                    "delivery_date": deliv_date.isoformat(),
                    "start_time": t_iso,
                    "selected_publish_time": None,
                    "forecast_mw": None,
                    "forecast_age_minutes": None,
                    "lead_time_hours": None,
                }
            )

    return pd.DataFrame(selected_rows)


def select_decision_forecasts_range(
    forecast_df: pd.DataFrame,
    start_date: str | date,
    end_date: str | date,
    cutoff_time: str,
) -> pd.DataFrame:
    """
    Selects decision forecasts for a range of decision dates [start_date, end_date].
    """
    cur = parse_date(start_date)
    end = parse_date(end_date)
    dfs = []
    while cur <= end:
        df_d = select_decision_forecasts(forecast_df, cur, cutoff_time)
        dfs.append(df_d)
        cur += timedelta(days=1)

    if not dfs:
        return pd.DataFrame()
    return pd.concat(dfs, ignore_index=True)
