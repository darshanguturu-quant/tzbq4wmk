"""
Repository for accessing the frozen historical snapshot (snapshot.sqlite) and manifest.
Read-only access ensuring reproducible and fast queries.
"""

import json
import sqlite3
from typing import Any

import pandas as pd

from backend.app.config import MANIFEST_PATH, SNAPSHOT_PATH


class SnapshotRepository:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or str(SNAPSHOT_PATH)
        self._forecasts_cache: pd.DataFrame | None = None
        self._actuals_cache: pd.DataFrame | None = None

    def _get_connection(self) -> sqlite3.Connection:
        # uri=True with mode=ro enforces read-only access at OS/sqlite level
        conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        return conn

    def load_all_forecasts(self) -> pd.DataFrame:
        """Loads all forecast revisions into memory for fast vectorised filtering."""
        if self._forecasts_cache is None:
            with self._get_connection() as conn:
                query = "SELECT start_time, publish_time, generation_mw FROM forecast_revisions"
                df = pd.read_sql_query(query, conn)
            df["start_time_dt"] = pd.to_datetime(df["start_time"], utc=True)
            df["publish_time_dt"] = pd.to_datetime(df["publish_time"], utc=True)
            self._forecasts_cache = df
        return self._forecasts_cache

    def load_all_actuals(self) -> pd.DataFrame:
        """Loads all actuals into memory."""
        if self._actuals_cache is None:
            with self._get_connection() as conn:
                query = """
                SELECT start_time, settlement_date, settlement_period, generation_mw
                FROM actuals
                """
                df = pd.read_sql_query(query, conn)
            df["start_time_dt"] = pd.to_datetime(df["start_time"], utc=True)
            self._actuals_cache = df
        return self._actuals_cache

    def get_manifest(self) -> dict[str, Any]:
        if not MANIFEST_PATH.exists():
            return {}
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)


_repo_instance: SnapshotRepository | None = None


def get_snapshot_repo() -> SnapshotRepository:
    global _repo_instance
    if _repo_instance is None:
        _repo_instance = SnapshotRepository()
    return _repo_instance
