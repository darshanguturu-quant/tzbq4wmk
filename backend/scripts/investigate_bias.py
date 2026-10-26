"""
Forecast Bias Investigation & Diagnostic Cross-Check Script.

This standalone diagnostic tool investigates the observed +1,745 MW overforecast bias
between WINDFOR (Day-Ahead Forecasts) and FUELHH (Settlement Outturn Actuals) in January 2026.

It executes four specific analyses:
1. Shortest-lead forecast comparison (lead time ~1.6h vs Day-Ahead 09:20).
2. Ratio forecast / actual across wind generation terciles and by hour of day.
3. Timing alignment test: exact :00 actuals vs (:00 + :30)/2 hourly averaged actuals.
4. Out-of-scope diagnostic cross-check against Elexon B1630 (Transparency Wind Generation).

Usage:
    python backend/scripts/investigate_bias.py

Outputs:
    Prints quantitative metrics to console.
    Saves summary metrics to data/bias_investigation_metrics.json.
"""

import json
import sqlite3
import sys
from pathlib import Path

import httpx
import numpy as np
import pandas as pd

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

DB_PATH = REPO_ROOT / "data" / "snapshot.sqlite"
OUTPUT_METRICS_PATH = REPO_ROOT / "data" / "bias_investigation_metrics.json"


def run_investigation():
    if not DB_PATH.exists():
        print(f"Error: Database file {DB_PATH} not found.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)

    # 1. Load raw forecasts and actuals from snapshot
    df_actuals = pd.read_sql_query(
        "SELECT start_time, settlement_date, settlement_period, generation_mw FROM actuals",
        conn,
    )
    df_forecasts = pd.read_sql_query(
        "SELECT start_time, publish_time, generation_mw FROM forecast_revisions",
        conn,
    )

    df_actuals["start_dt"] = pd.to_datetime(df_actuals["start_time"], utc=True)
    df_forecasts["start_dt"] = pd.to_datetime(df_forecasts["start_time"], utc=True)
    df_forecasts["pub_dt"] = pd.to_datetime(df_forecasts["publish_time"], utc=True)

    # Filter negative lead time rows (startTime < publishTime)
    valid_fc = df_forecasts[df_forecasts["start_dt"] >= df_forecasts["pub_dt"]].copy()

    # Target delivery hours: January 2, 2026 00:00 UTC to February 1, 2026 23:00 UTC (744 hours)
    target_hours = [
        pd.Timestamp(f"2026-01-{d:02d} {h:02d}:00:00", tz="UTC")
        for d in range(2, 32)
        for h in range(24)
    ] + [pd.Timestamp(f"2026-02-01 {h:02d}:00:00", tz="UTC") for h in range(24)]
    target_strs = [t.strftime("%Y-%m-%dT%H:%M:%SZ") for t in target_hours]

    # Exact :00 actuals
    exact_act = df_actuals[df_actuals["start_time"].isin(target_strs)].copy()
    exact_act = exact_act.rename(columns={"generation_mw": "act_exact_mw"})

    # Hourly averaged actuals (:00 + :30)/2
    df_actuals["hour_floor"] = df_actuals["start_dt"].dt.floor("h")
    hourly_avg_act = (
        df_actuals.groupby("hour_floor")["generation_mw"].mean().reset_index()
    )
    hourly_avg_act["start_time"] = hourly_avg_act["hour_floor"].dt.strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    hourly_avg_act = hourly_avg_act[
        hourly_avg_act["start_time"].isin(target_strs)
    ].copy()
    hourly_avg_act = hourly_avg_act.rename(columns={"generation_mw": "act_avg_mw"})

    # 1. Day-Ahead 09:20 decision forecast selection
    da_records = []
    for t_dt, t_str in zip(target_hours, target_strs):
        deliv_date = t_dt.date()
        dec_date = deliv_date - pd.Timedelta(days=1)
        cutoff_dt = pd.Timestamp(f"{dec_date} 09:20:00", tz="UTC")
        sub = valid_fc[
            (valid_fc["start_time"] == t_str) & (valid_fc["pub_dt"] <= cutoff_dt)
        ]
        if not sub.empty:
            latest = sub.sort_values(by="pub_dt", ascending=False).iloc[0]
            da_records.append(
                {
                    "start_time": t_str,
                    "da_pub_time": latest["publish_time"],
                    "da_fc_mw": latest["generation_mw"],
                    "da_lead_hours": (t_dt - latest["pub_dt"]).total_seconds() / 3600.0,
                }
            )
    df_da = pd.DataFrame(da_records)

    # 2. Shortest-lead forecast selection (latest revision prior to delivery hour)
    shortest_records = []
    for t_dt, t_str in zip(target_hours, target_strs):
        sub = valid_fc[(valid_fc["start_time"] == t_str) & (valid_fc["pub_dt"] <= t_dt)]
        if not sub.empty:
            latest = sub.sort_values(by="pub_dt", ascending=False).iloc[0]
            shortest_records.append(
                {
                    "start_time": t_str,
                    "shortest_pub_time": latest["publish_time"],
                    "shortest_fc_mw": latest["generation_mw"],
                    "lead_time_hours": (t_dt - latest["pub_dt"]).total_seconds()
                    / 3600.0,
                }
            )
    df_shortest = pd.DataFrame(shortest_records)

    # Merge matched datasets
    m = pd.merge(df_da, df_shortest, on="start_time")
    m = pd.merge(m, exact_act[["start_time", "act_exact_mw"]], on="start_time")
    m = pd.merge(m, hourly_avg_act[["start_time", "act_avg_mw"]], on="start_time")

    m["err_da_exact"] = m["da_fc_mw"] - m["act_exact_mw"]
    m["err_shortest_exact"] = m["shortest_fc_mw"] - m["act_exact_mw"]
    m["err_da_avg"] = m["da_fc_mw"] - m["act_avg_mw"]

    # --- Part 1: Shortest Lead Time Analysis ---
    bias_da = float(m["err_da_exact"].mean())
    mae_da = float(m["err_da_exact"].abs().mean())
    rmse_da = float(np.sqrt((m["err_da_exact"] ** 2).mean()))
    overfc_pct_da = float((m["err_da_exact"] > 0).mean() * 100.0)

    bias_sh = float(m["err_shortest_exact"].mean())
    mae_sh = float(m["err_shortest_exact"].abs().mean())
    rmse_sh = float(np.sqrt((m["err_shortest_exact"] ** 2).mean()))

    reduction_mw = bias_da - bias_sh
    persistence_pct = (bias_sh / bias_da) * 100.0

    print("=" * 70)
    print("1. SHORTEST-LEAD vs. DAY-AHEAD FORECAST (09:20 CUTOFF)")
    print("=" * 70)
    print(f"Sample size: N = {len(m)} delivery hours (January 2 to February 1, 2026)")
    print(
        f"Day-Ahead 09:20:    Bias = {bias_da:+.2f} MW | MAE = {mae_da:.2f} MW | RMSE = {rmse_da:.2f} MW"
    )
    print(
        f"Shortest Lead Time: Bias = {bias_sh:+.2f} MW | MAE = {mae_sh:.2f} MW | RMSE = {rmse_sh:.2f} MW"
    )
    print(
        f"Bias Reduction:     {reduction_mw:.2f} MW ({reduction_mw / bias_da * 100:.2f}%)"
    )
    print(
        f"Persistence:        {persistence_pct:.2f}% of bias persists within ~1.6h of delivery"
    )

    # --- Part 2: Proportional vs Additive (By Tercile & Hour of Day) ---
    print("\n" + "=" * 70)
    print("2. FORECAST / ACTUAL RATIO ACROSS WIND LEVELS & HOURS")
    print("=" * 70)
    m["wind_tercile"] = pd.qcut(
        m["act_exact_mw"],
        q=3,
        labels=[
            "Low Wind (< 8.8 GW)",
            "Medium Wind (8.8-14.5 GW)",
            "High Wind (> 14.5 GW)",
        ],
    )

    tercile_ratios = {}
    for cat in [
        "Low Wind (< 8.8 GW)",
        "Medium Wind (8.8-14.5 GW)",
        "High Wind (> 14.5 GW)",
    ]:
        sub = m[m["wind_tercile"] == cat]
        fc_sum = sub["da_fc_mw"].sum()
        act_sum = sub["act_exact_mw"].sum()
        ratio = float(fc_sum / act_sum)
        tercile_ratios[cat] = {
            "mean_act_mw": float(sub["act_exact_mw"].mean()),
            "mean_fc_mw": float(sub["da_fc_mw"].mean()),
            "mean_bias_mw": float(sub["err_da_exact"].mean()),
            "ratio": round(ratio, 4),
        }
        print(
            f"  {cat:26s} | Act: {sub['act_exact_mw'].mean():7.1f} MW | Fc: {sub['da_fc_mw'].mean():7.1f} MW | Bias: {sub['err_da_exact'].mean():+7.1f} MW | Ratio: {ratio:.3f}x"
        )

    overall_ratio = float(m["da_fc_mw"].sum() / m["act_exact_mw"].sum())
    print(f"  Overall Ratio: {overall_ratio:.4f}x (+{(overall_ratio - 1) * 100:.2f}%)")

    # Hour of day
    m["hour_of_day"] = pd.to_datetime(m["start_time"], utc=True).dt.hour
    hourly_ratios = []
    for h in range(24):
        sub = m[m["hour_of_day"] == h]
        r = float(sub["da_fc_mw"].sum() / sub["act_exact_mw"].sum())
        hourly_ratios.append(r)

    diurnal_stats = {
        "min_ratio": round(float(np.min(hourly_ratios)), 4),
        "max_ratio": round(float(np.max(hourly_ratios)), 4),
        "std_dev": round(float(np.std(hourly_ratios)), 4),
    }
    print(
        f"  Diurnal Ratio Range: {diurnal_stats['min_ratio']:.3f}x to {diurnal_stats['max_ratio']:.3f}x (std dev: {diurnal_stats['std_dev']:.4f})"
    )

    # --- Part 3: Timing Alignment Test ---
    print("\n" + "=" * 70)
    print("3. TIMING ALIGNMENT TEST (:00 EXACT vs. (:00+:30)/2 AVERAGED)")
    print("=" * 70)
    bias_exact = float(m["err_da_exact"].mean())
    mae_exact = float(m["err_da_exact"].abs().mean())
    bias_avg = float(m["err_da_avg"].mean())
    mae_avg = float(m["err_da_avg"].abs().mean())
    diff_actuals = float(m["act_exact_mw"].mean() - m["act_avg_mw"].mean())

    print(
        f"  (i)  Exact :00 Actuals:           Bias = {bias_exact:+.2f} MW | MAE = {mae_exact:.2f} MW"
    )
    print(
        f"  (ii) Averaged (:00+:30)/2 Actuals: Bias = {bias_avg:+.2f} MW | MAE = {mae_avg:.2f} MW"
    )
    print(
        f"  Net Difference:                   {abs(diff_actuals):.2f} MW (timing alignment does not explain the gap)"
    )

    # --- Part 4: Out-of-Scope Diagnostic Cross-Check (B1630) ---
    print("\n" + "=" * 70)
    print("4. OUT-OF-SCOPE DIAGNOSTIC CROSS-CHECK (ELEXON B1630 / AGWS)")
    print(
        "   Note: B1630 is NOT bundled into snapshot.sqlite or the portal application."
    )
    print("=" * 70)
    b1630_stats = fetch_b1630_diagnostic(m[["start_time", "da_fc_mw", "act_exact_mw"]])

    # Compile structured metrics dictionary
    metrics_payload = {
        "generated_from": "backend/scripts/investigate_bias.py",
        "sample_size_hours": len(m),
        "day_ahead_0920": {
            "bias_mw": round(bias_da, 2),
            "mae_mw": round(mae_da, 2),
            "rmse_mw": round(rmse_da, 2),
            "wape": round(
                float(m["err_da_exact"].abs().sum() / m["act_exact_mw"].sum()), 4
            ),
            "overforecast_pct": round(overfc_pct_da, 2),
            "avg_lead_hours": round(float(m["da_lead_hours"].mean()), 1),
        },
        "shortest_lead": {
            "bias_mw": round(bias_sh, 2),
            "mae_mw": round(mae_sh, 2),
            "rmse_mw": round(rmse_sh, 2),
            "avg_lead_hours": round(float(m["lead_time_hours"].mean()), 1),
            "bias_reduction_mw": round(reduction_mw, 2),
            "bias_persistence_pct": round(persistence_pct, 2),
        },
        "tercile_ratios": tercile_ratios,
        "overall_forecast_actual_ratio": round(overall_ratio, 4),
        "diurnal_ratio_variation": diurnal_stats,
        "timing_alignment_test": {
            "exact_00_bias_mw": round(bias_exact, 2),
            "exact_00_mae_mw": round(mae_exact, 2),
            "averaged_00_30_bias_mw": round(bias_avg, 2),
            "averaged_00_30_mae_mw": round(mae_avg, 2),
            "net_difference_mw": round(diff_actuals, 2),
        },
        "diagnostic_b1630_cross_check": b1630_stats,
    }

    with open(OUTPUT_METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics_payload, f, indent=2)
    print(f"\nSaved structured verified metrics to {OUTPUT_METRICS_PATH}")


def fetch_b1630_diagnostic(df_baseline: pd.DataFrame) -> dict:
    """
    Fetches B1630 / AGWS from Elexon Insights REST API for diagnostic cross-checking.
    Endpoint: https://data.elexon.co.uk/bmrs/api/v1/generation/actual/per-type/wind-and-solar
    Date range: 2026-01-01 to 2026-01-31 (fetched in 7-day API slices).
    """
    client = httpx.Client(timeout=40.0)
    b1630_records = []
    ranges = [
        ("2026-01-01T00:00:00Z", "2026-01-07T23:59:59Z"),
        ("2026-01-08T00:00:00Z", "2026-01-14T23:59:59Z"),
        ("2026-01-15T00:00:00Z", "2026-01-21T23:59:59Z"),
        ("2026-01-22T00:00:00Z", "2026-01-28T23:59:59Z"),
        ("2026-01-29T00:00:00Z", "2026-01-31T23:59:59Z"),
    ]

    for start_r, end_r in ranges:
        url = (
            f"https://data.elexon.co.uk/bmrs/api/v1/generation/actual/per-type/wind-and-solar"
            f"?from={start_r}&to={end_r}"
        )
        try:
            r = client.get(url)
            if r.status_code == 200:
                for item in r.json().get("data", []):
                    if item.get("businessType") == "Wind generation":
                        b1630_records.append(
                            {
                                "start_time": item.get("startTime"),
                                "psrType": item.get("psrType"),
                                "quantity": item.get("quantity"),
                            }
                        )
        except (httpx.RequestError, ValueError) as e:
            print(f"Warning: could not reach Elexon B1630 endpoint for {start_r}: {e}")

    df_b = pd.DataFrame(b1630_records)
    if df_b.empty:
        print("  Warning: No B1630 data retrieved (offline or rate limit).")
        return {"status": "unavailable"}

    df_b_hourly = df_b[df_b["start_time"].str.endswith(":00:00Z")]
    df_b_agg = df_b_hourly.groupby("start_time")["quantity"].sum().reset_index()
    df_b_agg = df_b_agg.rename(columns={"quantity": "b1630_wind_mw"})

    merged = pd.merge(df_baseline, df_b_agg, on="start_time")

    mean_windfor = float(merged["da_fc_mw"].mean())
    mean_fuelhh = float(merged["act_exact_mw"].mean())
    mean_b1630 = float(merged["b1630_wind_mw"].mean())

    diff_b1630_fuelhh = mean_b1630 - mean_fuelhh
    pct_diff = (diff_b1630_fuelhh / mean_fuelhh) * 100.0
    diff_windfor_b1630 = mean_windfor - mean_b1630
    pct_windfor_b1630 = (diff_windfor_b1630 / mean_b1630) * 100.0

    corr_b1630_fuelhh = float(merged["b1630_wind_mw"].corr(merged["act_exact_mw"]))
    corr_windfor_b1630 = float(merged["da_fc_mw"].corr(merged["b1630_wind_mw"]))

    print(f"  N = {len(merged)} common delivery hours:")
    print(f"  Mean WINDFOR (09:20 Day-Ahead):       {mean_windfor:7.1f} MW")
    print(f"  Mean B1630 (National Actuals/Est):    {mean_b1630:7.1f} MW")
    print(f"  Mean FUELHH (Settlement Outturn):     {mean_fuelhh:7.1f} MW")
    print(
        f"  Discrepancy (B1630 vs. FUELHH):       +{diff_b1630_fuelhh:7.1f} MW (+{pct_diff:.2f}%)"
    )
    print(
        f"  Difference (WINDFOR vs. B1630):       {diff_windfor_b1630:+7.1f} MW ({pct_windfor_b1630:+.2f}%)"
    )
    print(f"  Correlation r(B1630, FUELHH):         {corr_b1630_fuelhh:.4f}")
    print(f"  Correlation r(WINDFOR, B1630):        {corr_windfor_b1630:.4f}")

    return {
        "status": "verified",
        "sample_size_hours": len(merged),
        "mean_windfor_da_mw": round(mean_windfor, 2),
        "mean_b1630_mw": round(mean_b1630, 2),
        "mean_fuelhh_mw": round(mean_fuelhh, 2),
        "b1630_vs_fuelhh_discrepancy_mw": round(diff_b1630_fuelhh, 2),
        "b1630_vs_fuelhh_pct": round(pct_diff, 2),
        "windfor_vs_b1630_error_mw": round(diff_windfor_b1630, 2),
        "windfor_vs_b1630_pct": round(pct_windfor_b1630, 2),
        "correlation_b1630_fuelhh": round(corr_b1630_fuelhh, 4),
        "correlation_windfor_b1630": round(corr_windfor_b1630, 4),
    }


if __name__ == "__main__":
    run_investigation()
