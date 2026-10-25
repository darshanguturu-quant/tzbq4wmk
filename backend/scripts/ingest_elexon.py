"""
Ingestion script for Elexon BMRS API.
Fetches WINDFOR forecast revisions and FUELHH wind actuals for January 2026 evaluation window.
Validates data, builds snapshot (SQLite), and writes manifest.json.
Idempotent and reproducible.
"""

import hashlib
import json
import logging
import sqlite3
import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("ingest_elexon")

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"

# Date ranges for January 2026 purchase decisions
# Decisions: 2026-01-01 to 2026-01-31 -> Deliveries: 2026-01-02 to 2026-02-01
WINDFOR_START = "2025-12-28T00:00:00Z"
WINDFOR_END = "2026-02-01T23:59:59Z"

FUELHH_START = "2025-12-28"
FUELHH_END = "2026-02-02"

DATA_DIR = Path("data")
SNAPSHOT_DB = DATA_DIR / "snapshot.sqlite"
MANIFEST_FILE = DATA_DIR / "manifest.json"


def fetch_with_retry(
    client: httpx.Client,
    url: str,
    params: dict[str, Any],
    max_retries: int = 5,
    backoff_factor: float = 1.5,
) -> list[dict[str, Any]]:
    for attempt in range(1, max_retries + 1):
        try:
            r = client.get(url, params=params, timeout=60.0)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict) and "data" in data:
                    return data["data"]
                return []
            elif r.status_code in [429, 500, 502, 503, 504]:
                wait_time = backoff_factor**attempt
                logger.warning(
                    f"HTTP {r.status_code} for {url} (params: {params}). Retrying in {wait_time:.1f}s (attempt {attempt}/{max_retries})..."
                )
                time.sleep(wait_time)
            else:
                logger.error(
                    f"HTTP {r.status_code} error fetching {url}: {r.text[:200]}"
                )
                r.raise_for_status()
        except (httpx.RequestError, httpx.TimeoutException) as exc:
            wait_time = backoff_factor**attempt
            logger.warning(
                f"Network error {exc} for {url}. Retrying in {wait_time:.1f}s (attempt {attempt}/{max_retries})..."
            )
            time.sleep(wait_time)
    raise RuntimeError(
        f"Failed to fetch {url} with params {params} after {max_retries} retries"
    )


def fetch_all_windfor(
    client: httpx.Client,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    logger.info(
        f"Fetching WINDFOR forecast revisions from {WINDFOR_START} to {WINDFOR_END}..."
    )
    start_dt = datetime.fromisoformat(WINDFOR_START)
    end_dt = datetime.fromisoformat(WINDFOR_END)

    all_records: list[dict[str, Any]] = []
    batch_days = 2
    cur = start_dt
    batch_count = 0

    while cur <= end_dt:
        nxt = min(cur + timedelta(days=batch_days) - timedelta(seconds=1), end_dt)
        batch_id = f"windfor_{cur.strftime('%Y%m%d')}_{nxt.strftime('%Y%m%d')}"
        params = {
            "publishDateTimeFrom": cur.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "publishDateTimeTo": nxt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        logger.info(
            f"Fetching WINDFOR batch: {params['publishDateTimeFrom']} to {params['publishDateTimeTo']}"
        )
        records = fetch_with_retry(
            client, f"{BASE_URL}/datasets/WINDFOR/stream", params
        )
        for r in records:
            r["source_batch_id"] = batch_id
        all_records.extend(records)
        cur = nxt + timedelta(seconds=1)
        batch_count += 1
        time.sleep(0.1)

    logger.info(
        f"Total raw WINDFOR records fetched: {len(all_records)} across {batch_count} batches"
    )
    meta = {"raw_records": len(all_records), "batches": batch_count}
    return all_records, meta


def fetch_all_fuelhh(
    client: httpx.Client,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    logger.info(f"Fetching FUELHH wind actuals from {FUELHH_START} to {FUELHH_END}...")
    start_d = date.fromisoformat(FUELHH_START)
    end_d = date.fromisoformat(FUELHH_END)

    all_records: list[dict[str, Any]] = []
    batch_days = 5
    cur = start_d
    batch_count = 0

    while cur <= end_d:
        nxt = min(cur + timedelta(days=batch_days), end_d)
        batch_id = f"fuelhh_{cur.isoformat()}_{nxt.isoformat()}"
        params = {
            "settlementDateFrom": cur.isoformat(),
            "settlementDateTo": nxt.isoformat(),
            "fuelType": "WIND",
        }
        logger.info(
            f"Fetching FUELHH batch: {params['settlementDateFrom']} to {params['settlementDateTo']}"
        )
        records = fetch_with_retry(client, f"{BASE_URL}/datasets/FUELHH/stream", params)
        for r in records:
            r["source_batch_id"] = batch_id
        all_records.extend(records)
        cur = nxt + timedelta(days=1)
        batch_count += 1
        time.sleep(0.1)

    logger.info(
        f"Total raw FUELHH records fetched: {len(all_records)} across {batch_count} batches"
    )
    meta = {"raw_records": len(all_records), "batches": batch_count}
    return all_records, meta


def normalize_and_validate_forecasts(
    records: list[dict[str, Any]],
) -> tuple[list[tuple], dict[str, Any]]:
    logger.info("Normalizing and validating forecast revisions...")
    valid_rows: list[tuple] = []
    seen_keys: dict[tuple[str, str], float] = {}
    duplicates_dropped = 0
    conflicts: list[dict[str, Any]] = []
    negative_lead_count = 0

    for r in records:
        start_time = r.get("startTime", "")
        publish_time = r.get("publishTime", "")
        gen_val = r.get("generation")
        batch_id = r.get("source_batch_id", "")

        if not start_time or not publish_time or gen_val is None:
            continue

        try:
            gen_mw = float(gen_val)
        except (ValueError, TypeError):
            continue

        # Standardize ISO timestamps
        st_norm = start_time.replace("+00:00", "Z")
        if not st_norm.endswith("Z"):
            st_norm += "Z"
        pt_norm = publish_time.replace("+00:00", "Z")
        if not pt_norm.endswith("Z"):
            pt_norm += "Z"

        # Check negative lead time
        if st_norm < pt_norm:
            negative_lead_count += 1

        key = (st_norm, pt_norm)
        if key in seen_keys:
            duplicates_dropped += 1
            if seen_keys[key] != gen_mw:
                conflicts.append(
                    {
                        "start_time": st_norm,
                        "publish_time": pt_norm,
                        "existing_gen": seen_keys[key],
                        "conflicting_gen": gen_mw,
                    }
                )
            continue

        seen_keys[key] = gen_mw
        valid_rows.append((st_norm, pt_norm, gen_mw, batch_id))

    validation_summary = {
        "total_raw": len(records),
        "total_unique": len(valid_rows),
        "identical_duplicates_dropped": duplicates_dropped,
        "conflicting_duplicates_count": len(conflicts),
        "negative_lead_rows_count": negative_lead_count,
        "conflicts_sample": conflicts[:5],
    }
    logger.info(f"Forecasts validation: {validation_summary}")
    return valid_rows, validation_summary


def normalize_and_validate_actuals(
    records: list[dict[str, Any]],
) -> tuple[list[tuple], dict[str, Any]]:
    logger.info("Normalizing and validating actuals...")
    valid_rows: list[tuple] = []
    seen_starts: dict[str, float] = {}
    duplicates_dropped = 0
    conflicts: list[dict[str, Any]] = []

    for r in records:
        start_time = r.get("startTime", "")
        settlement_date = r.get("settlementDate", "")
        settlement_period = r.get("settlementPeriod", 0)
        gen_val = r.get("generation")
        batch_id = r.get("source_batch_id", "")

        if not start_time or gen_val is None:
            continue

        try:
            gen_mw = float(gen_val)
            sp = int(settlement_period)
        except (ValueError, TypeError):
            continue

        st_norm = start_time.replace("+00:00", "Z")
        if not st_norm.endswith("Z"):
            st_norm += "Z"

        if st_norm in seen_starts:
            duplicates_dropped += 1
            if seen_starts[st_norm] != gen_mw:
                conflicts.append(
                    {
                        "start_time": st_norm,
                        "existing_gen": seen_starts[st_norm],
                        "conflicting_gen": gen_mw,
                    }
                )
            continue

        seen_starts[st_norm] = gen_mw
        valid_rows.append((st_norm, settlement_date, sp, gen_mw, batch_id))

    validation_summary = {
        "total_raw": len(records),
        "total_unique": len(valid_rows),
        "identical_duplicates_dropped": duplicates_dropped,
        "conflicting_duplicates_count": len(conflicts),
        "conflicts_sample": conflicts[:5],
    }
    logger.info(f"Actuals validation: {validation_summary}")
    return valid_rows, validation_summary


def create_snapshot(
    forecast_rows: list[tuple],
    actual_rows: list[tuple],
) -> str:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if SNAPSHOT_DB.exists():
        SNAPSHOT_DB.unlink()

    conn = sqlite3.connect(SNAPSHOT_DB)
    cur = conn.cursor()

    # Tables schema
    cur.execute("""
    CREATE TABLE forecast_revisions (
        start_time TEXT NOT NULL,
        publish_time TEXT NOT NULL,
        generation_mw REAL NOT NULL,
        source_batch_id TEXT,
        PRIMARY KEY (start_time, publish_time)
    )
    """)
    cur.execute("CREATE INDEX idx_forecast_start ON forecast_revisions(start_time)")
    cur.execute("CREATE INDEX idx_forecast_publish ON forecast_revisions(publish_time)")
    cur.execute(
        "CREATE INDEX idx_forecast_pub_start ON forecast_revisions(publish_time, start_time)"
    )

    cur.execute("""
    CREATE TABLE actuals (
        start_time TEXT PRIMARY KEY,
        settlement_date TEXT NOT NULL,
        settlement_period INTEGER NOT NULL,
        generation_mw REAL NOT NULL,
        source_batch_id TEXT
    )
    """)
    cur.execute("CREATE INDEX idx_actuals_settlement_date ON actuals(settlement_date)")

    # Insert rows
    cur.executemany(
        "INSERT INTO forecast_revisions (start_time, publish_time, generation_mw, source_batch_id) VALUES (?, ?, ?, ?)",
        forecast_rows,
    )
    cur.executemany(
        "INSERT INTO actuals (start_time, settlement_date, settlement_period, generation_mw, source_batch_id) VALUES (?, ?, ?, ?, ?)",
        actual_rows,
    )

    conn.commit()
    conn.close()

    # Compute sha256
    hasher = hashlib.sha256()
    with open(SNAPSHOT_DB, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    file_hash = hasher.hexdigest()
    logger.info(f"Snapshot written to {SNAPSHOT_DB} (SHA256: {file_hash})")
    return file_hash


def run_ingestion():
    extraction_time = datetime.now(UTC).isoformat()
    logger.info("Starting complete Elexon ingestion pipeline...")

    with httpx.Client(timeout=60.0) as client:
        raw_forecasts, _f_meta = fetch_all_windfor(client)
        raw_actuals, _a_meta = fetch_all_fuelhh(client)

    forecast_rows, f_val = normalize_and_validate_forecasts(raw_forecasts)
    actual_rows, a_val = normalize_and_validate_actuals(raw_actuals)

    snapshot_hash = create_snapshot(forecast_rows, actual_rows)

    manifest = {
        "extraction_timestamp_utc": extraction_time,
        "api_base_url": BASE_URL,
        "scope": {
            "decisions_window": "2026-01-01 to 2026-01-31",
            "deliveries_window": "2026-01-02 to 2026-02-01",
            "windfor_fetch_bounds": [WINDFOR_START, WINDFOR_END],
            "fuelhh_fetch_bounds": [FUELHH_START, FUELHH_END],
        },
        "snapshot_file": str(SNAPSHOT_DB.name),
        "snapshot_sha256": snapshot_hash,
        "tables": {
            "forecast_revisions": {
                "row_count": len(forecast_rows),
                "validation": f_val,
            },
            "actuals": {
                "row_count": len(actual_rows),
                "validation": a_val,
            },
        },
        "validation_warnings": [],
    }

    if f_val["conflicting_duplicates_count"] > 0:
        manifest["validation_warnings"].append(
            f"Forecast revisions had {f_val['conflicting_duplicates_count']} conflicting duplicate entries."
        )
    if a_val["conflicting_duplicates_count"] > 0:
        manifest["validation_warnings"].append(
            f"Actuals had {a_val['conflicting_duplicates_count']} conflicting duplicate entries."
        )
    if f_val["negative_lead_rows_count"] > 0:
        manifest["validation_warnings"].append(
            f"Identified {f_val['negative_lead_rows_count']} negative lead-time rows (startTime < publishTime) in raw WINDFOR stream."
        )

    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    logger.info(f"Manifest written to {MANIFEST_FILE}")
    logger.info("Ingestion completed successfully!")


if __name__ == "__main__":
    run_ingestion()
