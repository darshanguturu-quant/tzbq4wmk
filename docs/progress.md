# Project Progress Log

## Phase 0: API Discovery & Data Findings (Completed)
- **Actions**:
  - Probed live Elexon BMRS API (`/datasets/FUELHH/stream` and `/datasets/WINDFOR/stream`).
  - Tested parameter names: `settlementDateFrom`, `settlementDateTo`, `fuelType=WIND` for FUELHH; `publishDateTimeFrom`, `publishDateTimeTo` for WINDFOR.
  - Verified actual WINDFOR publication times (~02:30, 04:30, 07:30, 09:30, 11:30/12:25, 15:30, 18:30, 22:30 UTC).
  - Verified WINDFOR target resolution is strictly hourly (100% of rows at `:00`).
  - Identified presence of negative lead-time rows (`startTime < publishTime`) in raw stream.
  - Resolved interval policy Decision Gate: exact hourly `startTime` matching with no synthetic interpolation.
  - Authored `docs/data_findings.md` and `docs/assumptions.md`.

## Phase 1: Ingestion, Validation & Snapshot Generation (Completed)
- **Actions**:
  - Implemented `backend/scripts/ingest_elexon.py` with bounded chunking and exponential backoff.
  - Ingested 21,024 WINDFOR revisions across 18 batches (2025-12-28 to 2026-02-01).
  - Ingested 1,776 FUELHH actuals across 7 batches (2025-12-28 to 2026-02-02).
  - Normalised UTC datetimes and floating-point MW generation values.
  - Built read-only SQLite database `data/snapshot.sqlite` with composite indices.
  - Generated cryptographic manifest `data/manifest.json` (SHA256: `c9a0499151944a0cdf5e2ccf2f21eb97e07e998edd5fad0ca735543efcc6b007`).
  - Added `Makefile`, `.env.example`, and `backend/app/config.py`.

