# Decision-Time Wind Forecast Intelligence Portal

[![CI Test Suite](https://github.com/anonymous/reint-portal/actions/workflows/ci.yml/badge.svg)](https://github.com/anonymous/reint-portal/actions)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/react-18-cyan.svg)](https://react.dev/)
[![Docker](https://img.shields.io/badge/docker-container-blue.svg)](https://www.docker.com/)

A specialized decision-time forecast reconstruction and accuracy evaluation portal built for UK energy utilities participating in the **GB day-ahead electricity market**. The portal allows trading desks to reconstruct the exact national wind forecast available at critical auction gate closures (e.g. 09:20, 09:50, 15:30 GMT or custom), compare outturn actuals, and quantitatively evaluate forecast error risk across **January 2026** purchase decisions.

> **Scope Boundary:** This product analyzes **national-level wind generation** actuals (FUELHH) and forecasts (WINDFOR) sourced exclusively from the Elexon BMRS API, as required by the assignment brief. It does not incorporate client demand, bilateral contracts, proprietary portfolios, or financial settlement prices. It provides wind forecast intelligence and risk quantification, not an automated thermal procurement dispatch instruction. External diagnostic datasets (such as B1630) are strictly out-of-scope cross-checks used offline for research and are not bundled into `data/snapshot.sqlite`, the REST API, the frontend, or `data/manifest.json`.

---

## Deployed Application

- **Live URL:** `DEPLOYED_APP_URL` *(Placeholder: Replace with your active Heroku or Vercel URL after deployment)*
- **Public Access:** Available directly in incognito mode without authentication.
- **Liveness Health Check:** `DEPLOYED_APP_URL/api/health`

---

## AI Tools Disclosure

In compliance with the assignment brief, **AI tools were utilized to assist in the development of this application**. Specifically:
- **Google Antigravity (Gemini)** and **Claude (Anthropic)** were used for architecture scaffolding, data discovery scripting, service implementation, CSS design system drafting, and test generation.
- **Verification Statement:** All data, API endpoints, and statistical metrics were **strictly cross-checked and independently verified**. The independent recomputation was performed directly from the stored Elexon snapshot compared with the API output (not against live Elexon responses). No mock data is present in the application snapshot; every figure reported in the UI, documentation, and video demo script is derived directly from real January 2026 Elexon data processed through this pipeline.

---

## Repository Structure

```
.
├── README.md                      # Project documentation, quickstart, and deployment guide
├── Dockerfile                     # Multi-stage container build (Node.js LTS + Python 3.12 Slim)
├── compose.yaml                   # Local multi-platform Docker Compose definition
├── heroku.yml                     # Heroku container stack deployment descriptor
├── Makefile                       # Developer task shortcuts (ingest, test, run, build, lint)
├── .env.example                   # Environment variable template
├── .gitignore                     # Git exclusion rules
├── backend/
│   ├── requirements.txt           # Python backend dependencies
│   ├── app/
│   │   ├── main.py                # FastAPI entrypoint, CORS, and SPA routing fallback
│   │   ├── config.py              # Configuration presets, calendar bounds, and disclaimers
│   │   ├── api/
│   │   │   └── endpoints.py       # REST API routers (/health, /profile, /performance, /export)
│   │   ├── schemas/
│   │   │   └── api_models.py      # Typed Pydantic request and response schemas
│   │   ├── services/
│   │   │   ├── asof_selection.py  # As-of cutoff selection logic (prevents look-ahead bias)
│   │   │   ├── evaluation.py      # Headline metrics (MAE, RMSE, Bias, WAPE, P90) & breakdowns
│   │   │   ├── uncertainty.py     # Leak-free empirical residual uncertainty bands
│   │   │   └── data_quality.py    # Interval matching audits and integrity reporting
│   │   └── repositories/
│   │       └── snapshot.py        # Read-only SQLite snapshot data access
│   ├── scripts/
│   │   ├── ingest_elexon.py       # Offline Elexon API extractor, validator, and snapshot generator
│   │   ├── explore_api.py         # Phase 0 API discovery and endpoint probe script
│   │   ├── investigate_bias.py    # Bias investigation & diagnostic B1630 cross-check
│   │   └── independent_recomputation.py # Independent raw SQL vs. API interval recomputation
│   └── tests/
│       ├── test_selection_and_evaluation.py  # Unit tests (includes named post-cutoff test)
│       └── test_api_endpoints.py             # FastAPI endpoint integration tests
├── frontend/
│   ├── package.json               # Frontend dependencies and scripts
│   ├── vite.config.ts             # Vite bundler configuration with API proxy
│   ├── tsconfig.json              # TypeScript compiler configuration
│   ├── index.html                 # Single-page application root HTML
│   └── src/
│       ├── main.tsx               # React application entrypoint
│       ├── App.tsx                # Master container with navigation and persistent ControlBar
│       ├── index.css              # Custom CSS design system (dark trading terminal aesthetics)
│       ├── types/                 # Shared TypeScript domain interfaces
│       ├── api/                   # HTTP client for backend REST endpoints
│       ├── components/            # Reusable UI widgets (DecisionChart, ErrorHeatmap, ControlBar)
│       ├── pages/                 # Main views (DecisionReplay, Performance, Evidence)
│       └── tests/                 # Vitest frontend unit tests
├── data/
│   ├── snapshot.sqlite            # Versioned historical snapshot (21,024 forecasts, 1,776 actuals)
│   ├── manifest.json              # Cryptographic audit summary (SHA-256 hash & validation log)
│   └── bias_investigation_metrics.json # Saved structured metrics from bias investigation
└── docs/
    ├── data_findings.md           # Phase 0 live API discovery results & parameter verification
    ├── assumptions.md             # Policy decisions & confirmed vs unconfirmed verification items
    ├── methodology.md             # Mathematical definitions, selection algorithm & investigation
    ├── bias_investigation.md      # Detailed 4-part bias investigation & diagnostic cross-check
    ├── architecture.md            # System architecture with Mermaid diagrams & design rationales
    ├── demo_script.md             # Two-part video presentation guide with real figures
    └── progress.md                # Phase-by-phase implementation log
```

---

## Quickstart Guide

### 1. Run with Docker (Recommended)
Prerequisites: Docker Engine / Docker Desktop installed.

```bash
# Clone the repository
git clone <REPO_URL>
cd <REPO_NAME>

# Build and run the single-container app
docker compose up --build
```
Once running, open **`http://localhost:8000`** in any web browser.

---

### 2. Local Development

#### A. Backend Setup (Python 3.11+)
```bash
# Create and activate virtual environment
python -m venv .venv

# On Linux/macOS:
source .venv/bin/activate
# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1

# Install backend dependencies
pip install -r backend/requirements.txt

# Run FastAPI backend with hot-reload
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive Swagger documentation is available at **`http://localhost:8000/docs`**.

#### B. Frontend Setup (Node.js 20+)
In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```
Open **`http://localhost:5173`** for local Vite development with proxy to backend.

---

## Re-Running Ingestion (`make ingest`)

The application is pre-bundled with a verified January 2026 snapshot (`data/snapshot.sqlite`). To re-extract and refresh data from the live Elexon BMRS API:

```bash
# Via Makefile:
make ingest

# Or directly with Python:
python backend/scripts/ingest_elexon.py
```
**What this changes:**
1. Connects to `https://data.elexon.co.uk/bmrs/api/v1`.
2. Fetches 21,024 WINDFOR forecast revisions across 18 bounded batches (`2025-12-28` to `2026-02-01`).
3. Fetches 1,776 FUELHH wind actuals across 7 batches (`2025-12-28` to `2026-02-02`).
4. Filters negative lead-time records (`startTime < publishTime`).
5. Atomically regenerates `data/snapshot.sqlite` with composite indices.
6. Recomputes SHA-256 checksum and updates `data/manifest.json`.

---

## Testing & Quality Assurance

### Run Backend Tests (Pytest)
```bash
pytest backend/tests -v
```
Runs **24 backend tests**, including:
- `test_post_cutoff_revision_cannot_enter_backtest`: Proves mathematically that a revision published after cutoff cannot enter the backtest.
- Negative lead-time filtering and missing-data null retention.
- Zero-generation safe WAPE handling.
- Common-interval cutoff comparisons.
- Leak-free empirical residual uncertainty bands.
- All REST API endpoints and SPA fallback routing.

### Run Frontend Tests (Vitest)
```bash
cd frontend && npm test
```
Runs Vitest unit tests verifying signed error conventions, local MW formatting, and replay privacy.

### Linting & Code Standards
```bash
# Lint and format check Python
ruff check backend/
ruff format --check backend/

# Type check TypeScript and verify build
cd frontend && npm run build
```

---

## Key Assumptions & Limitations

1. **Resolution Matching (Phase 0 Decision Gate):** WINDFOR forecasts are strictly hourly (`:00` minute intervals only); FUELHH actuals are half-hourly. As resolved in Phase 0, evaluation is strictly conducted on **exact hourly matches** without synthetic interpolation.
2. **Auction Gate Closures:** Presets (EPEX 09:20, N2EX 09:50, EPEX HH 15:30 GMT) represent illustrative market milestones. Trading desks must confirm their internal execution deadlines.
3. **No Zero-Filling:** Missing forecasts remain `null` and penalize coverage rather than artificially distorting error metrics.
4. **Empirical Residual Band:** The 10th-90th percentile band reflects historical past forecast errors. It is not an official Elexon probabilistic forecast.
*(Full details in [docs/assumptions.md](docs/assumptions.md)).*

---

## Forecast Bias Investigation & Findings (+1,745 MW)

Across January 2026, comparing day-ahead `WINDFOR` forecasts against `FUELHH` settlement outturn reveals a systematic positive bias of **+1,745.94 MW** (+15.47%, with 84.68% of all intervals overforecasted). An independent investigation tested four hypotheses to understand this gap:

### Empirical Observations
1. **Structural Baseline (Not Day-Ahead Uncertainty):** Evaluating the latest pre-delivery forecast (~1.6h lead time) still yields a **+1,471.15 MW bias**. Over 84% of the bias persists into real time.
2. **Proportional Output Scaling:** The bias scales with generation volume (+1,421.3 MW in low wind up to +2,263.4 MW in high wind), behaving as an aggregate **1.1547x multiplier**.
3. **Ratio Pattern:** The ratio of forecast to actual is **highest at low wind (1.224x) and lower at high wind (1.143x)**.
4. **Interval Alignment Invariant:** Exact `:00` actuals versus hourly averaged $(:00 + :30)/2$ actuals differ by only **1.95 MW (0.11%)**.
5. **Official OpenAPI Definitions** (Source: `https://data.elexon.co.uk/swagger/v1/swagger.json`, retrieved 2026-10-26):
   - `WINDFOR` is defined as *"wind generation forecast for wind farms which are visible to the ESO and have operational metering."*
   - `FUELHH` provides half-hourly aggregated settlement generation outturn (*"to give our users an indication of the generation outturn for Great Britain"*; commonly assumed in industry background context to reflect transmission-connected BMUs, unconfirmed).
6. **Out-of-Scope Diagnostic Triangulation (N = 720 common hours):**
   - Mean `WINDFOR` Day-Ahead Forecast: **13,227.75 MW**
   - Mean `B1630` National Actuals (Regulation 543/2013): **13,662.13 MW**
   - Mean `FUELHH` Settlement Outturn Actuals: **11,455.27 MW**
   - `WINDFOR` matches national transparency actuals (`B1630`) within **-3.18% (-434 MW)**, whereas `B1630` is **+19.26% (+2,207 MW) higher than `FUELHH`** ($r = 0.9924$).

### Cause Interpretation & Untested Hypotheses
- **Cause Interpretation (Strongly Supported by Cross-Check, Not Proven at Unit Level):** The cross-check strongly supports the conclusion that the gap reflects a reporting perimeter difference between the two datasets, rather than simple weather forecasting error; however, unit-level BMU telemetry and individual generator metering were not tested (as public Elexon data does not publish unit breakdowns), and the separate quantitative contributions of embedded wind and transmission curtailment remain untested.
- **Untested Hypotheses**:
  - *Embedded Wind*: `B1630` includes modeled estimates of distribution-connected (embedded) wind generation under Regulation 543/2013. In industry background context (unconfirmed), `FUELHH` is often assumed to capture only transmission-connected BMUs. Whether and to what extent NESO's `WINDFOR` includes embedded wind cannot be confirmed from public API documentation alone.
  - *Transmission Curtailment*: `FUELHH` reflects actual settlement outturn after NESO downward balancing instructions (BOALF). However, transmission curtailment is **not supported as the sole explanation**; because the forecast/actual ratio is higher at low wind (1.224x) than at high wind (1.143x), this ratio pattern provides evidence against curtailment alone, rather than serving as a direct test of curtailment.
- **Operational Guidance**:
  - The size of the gap against `FUELHH` is **+1,745.94 MW** (a ratio of **~1.155x**).
  - The right commercial adjustment depends on how the client defines demand (gross national demand vs. net transmission grid demand).
  - Trading desks do not need to apply arbitrary fixed haircuts: the portal's **leak-free empirical residual uncertainty band** ($Q_{10}$ to $Q_{90}$) is derived directly from realized past forecast errors and already reflects this structural gap.
*(Full quantitative data, scripts, and tables in [docs/bias_investigation.md](docs/bias_investigation.md)).*

---

## Deployment Instructions

### Option 1: Heroku Container Stack (Recommended)
1. **Login to Heroku & Container Registry:**
   ```bash
   heroku login
   heroku container:login
   ```
2. **Create Heroku App:**
   ```bash
   heroku create <YOUR-APP-NAME>
   heroku stack:set container --app <YOUR-APP-NAME>
   ```
3. **Build & Push Docker Container:**
   ```bash
   # Build with linux/amd64 platform compatibility
   docker build --platform linux/amd64 -t registry.heroku.com/<YOUR-APP-NAME>/web .
   docker push registry.heroku.com/<YOUR-APP-NAME>/web
   ```
4. **Release & Open:**
   ```bash
   heroku container:release web --app <YOUR-APP-NAME>
   heroku open --app <YOUR-APP-NAME>
   ```

### Option 2: Local Docker Execution
```bash
docker build -t wind-forecast-portal .
docker run -p 8000:8000 -e PORT=8000 wind-forecast-portal
```
Visit `http://localhost:8000`.
