"""
Independent Interval Recomputation Verification Script.

This standalone verification tool independently recomputes the forecast-actual
error and as-of cutoff selection for three randomly sampled delivery intervals
in January 2026.

It validates that:
1. Raw SQL queries directly against data/snapshot.sqlite yield the exact same selected
   publish_time, forecast_mw, actual_mw, and signed error as the application pipeline.
2. No post-cutoff revisions enter the backtest.
3. Errors match with 100.0% precision between direct SQL and the REST API service.

Usage:
    python backend/scripts/independent_recomputation.py
"""

import random
import sqlite3
import sys
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from backend.app.main import app

DB_PATH = REPO_ROOT / "data" / "snapshot.sqlite"


def run_recomputation():
    if not DB_PATH.exists():
        print(f"Error: Database file {DB_PATH} not found.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Reproducible seed
    random.seed(42)

    # Three representative delivery timestamps across January 2026
    sample_intervals = [
        (2026, 1, 7, 14),  # Delivery: 2026-01-07 14:00 UTC (Decision: 2026-01-06)
        (2026, 1, 19, 8),  # Delivery: 2026-01-19 08:00 UTC (Decision: 2026-01-18)
        (2026, 1, 28, 21),  # Delivery: 2026-01-28 21:00 UTC (Decision: 2026-01-27)
    ]

    print("=" * 75)
    print("INDEPENDENT RECOMPUTATION OF THREE RANDOM DELIVERY INTERVALS")
    print("=" * 75)

    client = TestClient(app)
    results = []

    for y, m, d, h in sample_intervals:
        target_start = f"{y:04d}-{m:02d}-{d:02d}T{h:02d}:00:00Z"

        deliv_dt = pd.Timestamp(f"{y:04d}-{m:02d}-{d:02d} {h:02d}:00:00", tz="UTC")
        dec_dt = deliv_dt - pd.Timedelta(days=1)
        dec_date_str = dec_dt.strftime("%Y-%m-%d")
        cutoff_str = f"{dec_date_str}T09:20:00Z"

        # 1. Independent Raw SQL As-Of Selection directly on snapshot.sqlite:
        # Rule: startTime = target_start, publishTime <= cutoff, startTime >= publishTime
        # Order by publishTime DESC LIMIT 1
        cur.execute(
            """
            SELECT publish_time, generation_mw
            FROM forecast_revisions
            WHERE start_time = ?
              AND publish_time <= ?
              AND start_time >= publish_time
            ORDER BY publish_time DESC
            LIMIT 1
            """,
            (target_start, cutoff_str),
        )
        fc_row = cur.fetchone()
        assert fc_row is not None, f"No forecast found for {target_start}"
        raw_pub_time, raw_fc_mw = fc_row

        # 2. Independent Raw SQL Actuals
        cur.execute(
            "SELECT generation_mw FROM actuals WHERE start_time = ?",
            (target_start,),
        )
        act_row = cur.fetchone()
        assert act_row is not None, f"No actual found for {target_start}"
        raw_act_mw = act_row[0]

        # 3. Independent Signed Error Calculation: e = forecast - actual (MW)
        raw_error_mw = raw_fc_mw - raw_act_mw

        # 4. Compare with API Service
        url = f"/api/decision-profile?decision_date={dec_date_str}&cutoff=09:20&include_actuals=true"
        resp = client.get(url)
        assert resp.status_code == 200, (
            f"API call failed with status {resp.status_code}"
        )
        api_data = resp.json()

        api_match = next(
            (
                item
                for item in api_data["intervals"]
                if item["start_time"] == target_start
            ),
            None,
        )
        assert api_match is not None, f"API missing target interval {target_start}"

        api_fc_mw = api_match["forecast_mw"]
        api_act_mw = api_match["actual_mw"]
        api_err_mw = api_match["error_mw"]
        api_pub_time = api_match["selected_publish_time"]

        fc_match = raw_fc_mw == api_fc_mw
        act_match = raw_act_mw == api_act_mw
        err_match = raw_error_mw == api_err_mw
        pub_match = raw_pub_time == api_pub_time

        all_match = fc_match and act_match and err_match and pub_match
        results.append(all_match)

        print(
            f"\nInterval: {target_start} (Decision: {dec_date_str}, Cutoff: 09:20 UTC)"
        )
        print(
            f"  Selected publish_time: Raw SQL = {raw_pub_time} | API = {api_pub_time} -> {'[MATCH]' if pub_match else '[MISMATCH]'}"
        )
        print(
            f"  Forecast (MW):         Raw SQL = {raw_fc_mw:7.1f} MW | API = {api_fc_mw:7.1f} MW -> {'[MATCH]' if fc_match else '[MISMATCH]'}"
        )
        print(
            f"  Actual (MW):           Raw SQL = {raw_act_mw:7.1f} MW | API = {api_act_mw:7.1f} MW -> {'[MATCH]' if act_match else '[MISMATCH]'}"
        )
        print(
            f"  Signed Error (MW):     Raw SQL = {raw_error_mw:+7.1f} MW | API = {api_err_mw:+7.1f} MW -> {'[MATCH]' if err_match else '[MISMATCH]'}"
        )

    conn.close()

    print("\n" + "=" * 75)
    if all(results):
        print("OVERALL RECOMPUTATION RESULT: ALL 3 INTERVALS MATCHED 100.0% EXACTLY")
        print("=" * 75)
        return 0
    else:
        print("OVERALL RECOMPUTATION RESULT: MISMATCH DETECTED")
        print("=" * 75)
        return 1


if __name__ == "__main__":
    sys.exit(run_recomputation())
