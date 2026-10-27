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

## Phase 7: Bias Investigation, Scope Triangulation & Git History Anonymization (Completed)
- **Actions**:
  - Investigated the +1,745.94 MW (+15.5%) systematic overforecasting bias across 4 hypotheses:
    1. *Shortest-Lead Horizon*: Evaluated latest pre-delivery revision (~1.6h lead time); bias remains +1,471.15 MW (84.3% persists into delivery), proving structural error rather than day-ahead horizon uncertainty.
    2. *Scale Mismatch*: Evaluated forecast/actual ratio across terciles (Low: 1.224x, Med: 1.133x, High: 1.143x) and across all 24 hours (1.114x to 1.216x, std dev: 0.0372); proved proportional scale mismatch (+15.47% overall).
    3. *Timing Alignment*: Evaluated exact `:00` vs $(:00 + :30)/2$ average actuals; net difference is only 1.95 MW (0.11%).
    4. *Dataset Scope & Triangulation*: Audited Elexon OpenAPI specs and triangulated with Regulation (EU) 543/2013 national transparency actuals (`B1630` / `AGWS`) across January 2026. WINDFOR matches national transparency actuals within -3.18% (-434 MW), while settlement outturn (`FUELHH`) runs 19.3% lower (+2,207 MW difference, $r = 0.9924$).
  - Authored comprehensive report in `docs/bias_investigation.md` and updated `docs/methodology.md`, `README.md`, and `docs/demo_script.md`.
  - Conducted independent recomputation on 3 randomly sampled delivery intervals using standalone raw SQL (Jan 7 14:00, Jan 19 08:00, Jan 28 21:00 UTC); verified 100.0% exact match against live API outputs.
  - Performed complete repository and Git history anonymization: purged assignment files and personal identifiers (author names, handles, emails, and local user directories) from all commit author and committer metadata across entire history.
  - Re-verified all test suites: 24/24 backend tests passing, 4/4 frontend tests passing, clean Ruff check, successful production build.

## Phase 8: Audit Claim Calibration, Citations, Diagnostic Labeling & UI Dynamic Ratio (Completed)
- **Actions**:
  - Corrected claims across `docs/bias_investigation.md`, `docs/methodology.md`, `README.md`, and `docs/demo_script.md`:
    - Replaced "Verified Fact" for the cause of forecast divergence with "strongly supported by the cross-check, not proven at unit level" (noting that unit-level telemetry and the split between embedded wind and curtailment were not tested).
    - Removed unverified claims regarding WINDFOR neural networks or training methods.
    - Presented curtailment and embedded wind strictly as untested hypotheses; recorded that the forecast/actual ratio is highest at low wind (1.224x) and lower at high wind (1.143x), providing evidence against curtailment alone rather than a test of it (curtailment is not supported as the sole explanation).
    - Replaced the fixed haircut recommendation with neutral commercial guidance based on client demand perimeter and empirical residual uncertainty bands.
  - Labeled the B1630 comparison everywhere as an out-of-scope diagnostic cross-check; verified that B1630 is not present in `data/snapshot.sqlite`, the REST API, the frontend, or `data/manifest.json`.
  - Moved reproducibility scripts into `backend/scripts/` (`investigate_bias.py` and `independent_recomputation.py`), both runnable from the repo root. Saved quantitative metrics in `data/bias_investigation_metrics.json`.
  - Added source URLs (`https://data.elexon.co.uk/swagger/v1/swagger.json`) and retrieval dates (2026-10-26) for all quoted Elexon documentation.
  - Updated `docs/assumptions.md` with confirmed vs. unconfirmed items.
  - Updated the Evidence & Data Quality page in the UI to state in plain language that WINDFOR is systematically higher than FUELHH outturn in January 2026 using the pipeline's dynamically computed ratio (1.155x), noting that it likely reflects a coverage difference between the two datasets.

## Phase 9: Precision Calibration on Curtailment, BMU Scope & Untested Boundaries (Completed)
- **Actions**:
  - Replaced all wording stating curtailment was "disproven" with "not supported as the sole explanation". Clarified that the ratio pattern (higher at low wind, lower at high wind) is evidence against curtailment alone being the explanation, rather than serving as a direct test of curtailment.
  - Relabeled all statements regarding FUELHH covering only "transmission-connected BMUs" as unconfirmed background context, removing it from confirmed items in `docs/assumptions.md` and clarifying that the primary Elexon OpenAPI specification does not define an explicit BMU restriction.
  - Qualified every "strongly supported" statement by explicitly naming what was not tested (unit-level BMU telemetry and individual generator metering, as well as the quantitative decomposition between embedded wind and curtailment).
  - Re-ran test and build suites: pytest (24/24 passed), ruff (clean), npm test (4/4 passed), and npm run build.

## Phase 10: Full Project Audit & Genuine Data Integrity Enforcement (Completed)
- **Actions**:
  - Audited all metrics, documentation statements, UI components, and API schemas against `data/snapshot.sqlite`.
  - Eliminated synthetic formula approximation `(day.bias + hour.bias)/2` from `ErrorHeatmap` by adding real matched delivery interval records to `compute_performance_summary` and `PerformanceResponse`.
  - Corrected demo script walk-through figures for January 15/16 decision profile to match real snapshot figures (peak 10,375 MW, average 7,930 MW, minimum 6,242 MW).
  - Clarified deployment URL descriptors in `README.md`.
  - Verified all tests, linter checks, and production builds pass cleanly.

## Phase 11: Vercel Free-Tier Deployment Configuration (Completed)
- **Actions**:
  - Implemented `api/index.py` serverless adapter exposing the FastAPI ASGI app directly to Vercel's Python runtime.
  - Added root `vercel.json` configuring monorepo frontend installation/building, client-side SPA routing rewrites, `/api` serverless dispatch, and `data/**` asset bundling.
  - Added production-only root `requirements.txt` containing runtime dependencies (`fastapi`, `uvicorn`, `pydantic`, `pandas`, `python-dateutil`) and excluding development/offline packages.
## Phase 12: Resolution of Verified Quality Defects (Completed)
- **Actions**:
  - **Fix 1 (Resolution Matching Policy)**: Confirmed WINDFOR snapshot emits strictly hourly targets (`:00` only, 21,024 records, 0 records at `:30`). FUELHH emits half-hourly actuals (1,776 records, 888 at `:00`, 888 at `:30`). Documented explicit justification in Evidence & Audit, README, and assumptions: true 30-minute matched evaluation is impossible without inventing/interpolating data; missing values are never zero-filled, so evaluation is strictly hourly (744/744 matched pairs in January 2026, 100.0% coverage), with the 744 `:30` actuals remaining unmatched.
  - **Fix 2 (Impossible Lead-Time Band at 12:00 Cutoff)**: Root cause identified: on 2026-01-15, Elexon delayed midday WINDFOR publication from 11:30 to 12:25:00 UTC (verified against both live BMRS API stream and frozen snapshot). Under cutoff 12:00, the selector chose 09:30:00 UTC (fallback publication). Delivery targets 2026-01-16 22:00 and 23:00 had exact `startTime - publishTime` lead times of 36.5h and 37.5h. Reassigned day-ahead delivery spillover intervals at cutoffs >= 11:30 to the terminal day-ahead band `30-36h`. After the fix: 36-42h band at 12:00 is absent (0 count), 30-36h band count increased from 186 to 188, and all bands sum to 744. The 09:20 preset lead-time bands (124 in 36-42h) and headline metrics are completely unchanged.
  - **Fix 3 (Metric Label Correction)**: Corrected KPI card label from "Root Mean Squared (RMSE)" to "Root Mean Square Error". Removed `text-transform: uppercase` from `.kpi-label` in `index.css`. Verified formula shown remains $\text{RMSE} = \sqrt{\text{mean}(e^2)}$, where $e = \text{forecast} - \text{actual}$.
  - **Fix 4 (Removed Misleading Live Phrasing)**: Changed header title in `App.tsx` from "January 2026 Live Snapshot" to "January 2026 Snapshot". Updated Evidence page labels to clarify that data is an offline frozen bundle extracted 2026-10-25 19:33 UTC with SHA-256 integrity verification.
  - **Fix 5 (Custom Cutoff in Sensitivity Comparison)**: Updated `fetchPerformanceCompare` in `PerformancePage.tsx` to include the active custom cutoff alongside presets. Rendered custom cutoff as its own row labeled `Custom Cutoff (HH:MM)` and marked `(Active)` when selected. Evaluated strictly on the identical 744 common intervals. Presets remain unchanged.
  - **Fix 6 (Documented 0 MW Uncertainty Band Lower Bound)**: Audited `backend/app/services/uncertainty.py` line 107. Documented exact flooring rule `lower = max(0.0, forecast + Q10(residual))` in Evidence & Audit, `docs/assumptions.md`, and `docs/methodology.md`: due to systematic positive bias (+1,745 MW), empirical residuals are heavily negative; lower bounds are floored at 0.0 MW because physical wind generation cannot be negative.
  - **QA & Verification**: Re-ran full test suite: pytest (25/25 passed, including new test `test_lead_time_bands_at_1200_and_0920`), Vitest (6/6 passed, including custom cutoff comparison and 0 MW band flooring tests), ruff lint/format (clean), and TypeScript production build (`npm run build`, clean).








