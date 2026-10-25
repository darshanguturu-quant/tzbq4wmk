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
