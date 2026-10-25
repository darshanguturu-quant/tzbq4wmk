# Phase 0: Elexon BMRS API Discovery & Data Findings

*Run timestamp: 2026-10-25T19:31:27.517662+00:00*

## 1. Verified API Endpoints & Response Structure
- **Base URL**: `https://data.elexon.co.uk/bmrs/api/v1`
- **Actuals Endpoint**: `GET /datasets/FUELHH/stream`
  - Parameters verified: `settlementDateFrom` (YYYY-MM-DD), `settlementDateTo` (YYYY-MM-DD), `fuelType=WIND`
  - Status code: 200, Response shape: Flat JSON list of record objects
- **Forecast Endpoint**: `GET /datasets/WINDFOR/stream`
  - Parameters verified: `publishDateTimeFrom` (ISO8601 UTC), `publishDateTimeTo` (ISO8601 UTC)
  - Status code: 200, Response shape: Flat JSON list of record objects

## 2. WINDFOR Publish Schedule & Real Publication Times
- **Real Publish Times observed**: Real publish times are issued ~8 times per day, but shifted from secondary research:
  - `2026-01-01`: 02:30:00Z, 04:30:00Z, 07:30:00Z, 09:30:00Z, 11:30:00Z, 15:30:00Z, 18:30:00Z, 22:30:00Z
  - `2026-01-05`: 02:30:00Z, 04:30:00Z, 07:30:00Z, 09:30:00Z, 11:30:00Z, 15:30:00Z, 18:30:00Z, 22:30:00Z
  - `2026-01-10`: 02:30:00Z, 04:30:00Z, 07:30:00Z, 09:30:00Z, 11:30:00Z, 15:30:00Z, 18:30:00Z, 22:30:00Z
  - `2026-01-15`: 02:30:00Z, 04:30:00Z, 07:30:00Z, 09:30:00Z, 12:25:00Z, 15:30:00Z, 18:30:00Z, 22:30:00Z
  - `2026-01-20`: 02:30:00Z, 04:30:00Z, 07:30:00Z, 09:30:00Z, 11:30:00Z, 15:30:00Z, 18:30:00Z, 22:30:00Z
  - `2026-01-25`: 02:30:00Z, 04:30:00Z, 07:30:00Z, 09:30:00Z, 11:30:00Z, 15:30:00Z, 18:30:00Z, 22:30:00Z
  - `2026-01-31`: 02:30:00Z, 04:30:00Z, 07:30:00Z, 09:30:00Z, 11:30:00Z, 15:30:00Z, 18:30:00Z, 22:30:00Z
- **Key Takeaway**: Documented secondary schedule cited `03:30, 05:30, 08:30, 10:30, 12:30, 16:30, 19:30, 23:30`. Real published times in January 2026 occur typically around `02:30, 04:30, 07:30, 09:30, 12:25/12:30, 15:30, 18:30, 22:30` UTC. Therefore, at the `09:20` and `09:50` cutoffs, the latest available forecast is the `07:30` publication (or `09:30` for `09:50` if published slightly earlier, otherwise `07:30`).

## 3. Forecast Target Time Resolution (Hourly vs Half-Hourly)
- **Result**: All WINDFOR startTime records have minute=0. WINDFOR is strictly hourly. No :30 targets have forecasts.
- **Minute breakdown**: {0: 4088}
- **DECISION GATE - INTERVAL MATCHING POLICY**:
  - WINDFOR provides hourly forecasts (`:00` intervals only).
  - FUELHH provides half-hourly actuals (`:00` and `:30` intervals).
  - **Chosen Policy**: Exact `startTime` matching on hourly timestamps only. No forward-filling or interpolation of missing `:30` forecasts. Expected intervals per delivery day = 24 hourly intervals. Coverage is computed as `matched_hourly_intervals / 24`.

## 4. Forecast Horizon & Negative Lead Times
- **Forecast Horizon**: ~72.0 hours per publication (3 full delivery days).
- **Negative Lead Time Rows**: Found 841 rows where `startTime < publishTime`. These are past hours emitted as part of the forecast publication batch. They MUST be filtered out (`startTime >= publishTime`).

## 5. FUELHH Actuals Coverage & Schema
- Exactly 48 half-hourly settlement periods per day.
- Sample day counts: {'2026-01-01': 48, '2026-01-05': 48, '2026-01-10': 48, '2026-01-15': 48, '2026-01-20': 48, '2026-01-25': 48, '2026-01-31': 48}
- Fields present: `dataset`, `publishTime`, `startTime`, `settlementDate`, `settlementPeriod`, `fuelType`, `generation`.

## 6. Duplicate & Conflicting Records
- Duplicate `(startTime, publishTime)` keys in sample: 0.
- Conflicting values in sample: 0.
- Deduplication rule: drop exact duplicates; flag any conflicting values as manifest warnings.

## 7. Delivery Date Coverage for Presets (09:20, 09:50, 15:30)
| Decision Date | Delivery Date | Cutoff Preset | Cutoff Time | Covered Target Hours | Expected Hours |
|---|---|---|---|---|---|
| 2026-01-01 | 2026-01-02 | EPEX Hourly | 09:20 | 25 | 24 |
| 2026-01-01 | 2026-01-02 | N2EX | 09:50 | 25 | 24 |
| 2026-01-01 | 2026-01-02 | EPEX Half-Hourly | 15:30 | 25 | 24 |
| 2026-01-15 | 2026-01-16 | EPEX Hourly | 09:20 | 25 | 24 |
| 2026-01-15 | 2026-01-16 | N2EX | 09:50 | 25 | 24 |
| 2026-01-15 | 2026-01-16 | EPEX Half-Hourly | 15:30 | 25 | 24 |
| 2026-01-31 | 2026-02-01 | EPEX Hourly | 09:20 | 25 | 24 |
| 2026-01-31 | 2026-02-01 | N2EX | 09:50 | 25 | 24 |
| 2026-01-31 | 2026-02-01 | EPEX Half-Hourly | 15:30 | 25 | 24 |

Coverage for all 24 hourly delivery target hours is 100% under all standard presets across the probed dates.

## 8. Generation Units
- Both `FUELHH` and `WINDFOR` report generation in **Megawatts (MW)**.
- Actuals range: Min: 7678 MW, Max: 11309 MW
- Forecast range: Min: 4300 MW, Max: 19252 MW
