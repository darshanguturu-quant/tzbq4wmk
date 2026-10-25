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

## Phase 2: Selection & Evaluation Logic + Unit Tests (Completed)
- **Actions**:
  - Implemented `backend/app/repositories/snapshot.py` for read-only access.
  - Implemented `backend/app/services/asof_selection.py` with strict `publishTime <= cutoff` and negative lead-time exclusion.
  - Implemented `backend/app/services/evaluation.py` for MAE, RMSE, Bias, WAPE, P90 absolute error, over/under splits, and breakdowns.
  - Implemented `backend/app/services/uncertainty.py` with strictly leak-free lookback and insufficient history handling.
  - Implemented `backend/app/services/data_quality.py` for interval matching audits.
  - Created test suite `backend/tests/test_selection_and_evaluation.py` (12 passing tests, including named test `test_post_cutoff_revision_cannot_enter_backtest`).

## Phase 3: Backend API (Completed)
- **Actions**:
  - Implemented Pydantic models in `backend/app/schemas/api_models.py`.
  - Implemented `/api/*` endpoints in `backend/app/api/endpoints.py` (`/health`, `/metadata`, `/decision-profile`, `/performance`, `/performance/compare`, `/data-quality`, `/export`).
  - Added strict parameter validation for January 2026 calendar bounds, HH:MM cutoffs, and chronological ranges.
  - Configured CORS and SPA route fallback serving in `backend/app/main.py`.
  - Added 11 endpoint integration tests in `backend/tests/test_api_endpoints.py`. All 23 tests pass.

## Phase 4: Frontend SPA (Completed)
- **Actions**:
  - Initialized React 18 + TypeScript + Vite project in `frontend/`.
  - Created bespoke CSS design system with trading terminal dark theme, neon emerald/cyan accents, and glassmorphism.
  - Implemented persistent `ControlBar` with EPEX/N2EX gate closure presets and custom time picker.
  - Built interactive SVG `DecisionChart` with hover tooltips, uncertainty bands, and actuals overlay.
  - Built signed-error `ErrorHeatmap` calendar matrix covering all 744 hourly delivery intervals.
  - Created 3 pages: `DecisionReplayPage`, `PerformancePage`, and `EvidencePage`.
  - Added Vitest frontend unit tests (`frontend/src/tests/components.test.ts`).
  - Generated production bundle in `frontend/dist/` seamlessly served by FastAPI.

## Phase 5: Containerization & Deployment Skeleton (Completed)
- **Actions**:
  - Authored multi-stage `Dockerfile` with Node 20 frontend compilation and Python 3.12 non-root runtime.
  - Created `compose.yaml` with port mapping and environment variables.
  - Created `heroku.yml` for Heroku Container Registry deployment.
  - Established automated GitHub Actions CI workflow in `.github/workflows/ci.yml`.

## Phase 6: Documentation, Methodology, Demo Script & Final QA (Completed)
- **Actions**:
  - Authored comprehensive `README.md` with AI tools disclosure, directory tree, startup guides, test commands, and deployment instructions.
  - Authored `docs/methodology.md` detailing the selection algorithm, error formulas (MAE, RMSE, Bias, WAPE, P90), and uncertainty bounds.
  - Authored `docs/architecture.md` with Mermaid diagram and technical rationales.
  - Authored `docs/demo_script.md` with real January 2026 computed figures for both video parts (Pitch & Tech Review).
  - Executed final quality assurance: 24/24 backend tests passing, 4/4 frontend tests passing, 100% clean Ruff linting, zero TypeScript errors.






