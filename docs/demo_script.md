# Video Demo Presentation Script

> **Role:** Commercial Product Developer / Trading Systems Engineer  
> **Target Duration:** Max 10 minutes total (Part 1 &le; 5 min, Part 2 &le; 5 min)  
> **Source Data:** Real January 2026 Elexon data run through this project's pipeline.

---

## Part 1: Customer Pitch (Energy Utility Trading Team)
**Goal:** Present the portal as the output of the completed pilot. Demonstrate how it reconstructs what was known at buying deadlines and quantifies forecast risk for wholesale procurement.  
**Target Duration:** 4 - 5 minutes.

### 1. The Decision Problem (0:00 - 1:00)
- *"Welcome team. As a UK electricity utility trading on the GB wholesale market, you face a critical daily challenge: at day-ahead gate closure, you must commit to power purchases for tomorrow's delivery. To know how much thermal or market power you need, you rely heavily on national wind generation forecasts."*
- *"The fundamental problem is two-fold: First, wind forecasts change up to 8 times a day. If your team looks at forecasts updated after gate closure, you're evaluating on information you never actually had. Second, wind forecasts are inherently uncertain. Without quantifying that historical error, you cannot price or hedge the risk."*

### 2. Walkthrough: Decision Replay (1:00 - 2:30)
- **Navigate to Decision Replay page** (Select **January 15, 2026**, Cutoff **09:20 GMT**):
  - *"Here is the wind outlook exactly as your desk saw it at the 09:20 EPEX gate closure for delivery on January 16th."*
  - *"Notice the peak forecast is **19,252 MW** with an average delivery of **14,640 MW**."*
  - *"Hovering over each delivery interval shows the exact forecast revision selected (issued at **07:30 UTC**, aged 110 minutes). Revisions published later in the day are strictly excluded."*
  - *"Notice the cyan band: this is our leak-free empirical residual band (10th to 90th percentile), giving your traders an immediate confidence interval based strictly on historical forecast performance."*
- **Switch Toggle to "Outcome Review"**:
  - *"Now let's toggle to Outcome Review. The amber line shows the outturn settlement generation from FUELHH."*
  - *"We see that on this day, the forecast overpredicted wind output during peak hours, creating a procurement shortfall that required balancing actions."*

### 3. Quantitative Risk & Portfolio Insights (2:30 - 4:00)
- **Navigate to Forecast Performance page**:
  - *"Across all 744 hourly delivery intervals in January 2026, here are the audited facts:"*
  - **Mean Absolute Error (MAE):** **2,022 MW** — on average, day-ahead forecasts deviated by approximately 2.0 GW.
  - **Systematic Bias:** **+1,746 MW** — the forecasts exhibited a strong, persistent **overforecasting bias** on **84.7%** of all intervals.
  - **P90 Tail Risk:** **4,154 MW** — in 10% of intervals, the forecast was off by more than 4.1 GW!
  - **High-Risk Day Highlight:** *"Point out **January 12th**, where the forecast overpredicted wind by **6,894 MW** at 01:00 UTC."*
  - **Regime Insight:** *"Our wind level breakdown reveals that during high-wind intervals (&gt;14.5 GW), overforecasting bias jumped to **+2,263 MW**."*
- **Cutoff Sensitivity Comparison**:
  - *"Switch between presets (09:20 vs 09:50 vs 15:30). By comparing them strictly on common matched intervals, your desk can see the exact accuracy gain achieved by delaying commitments to later auction gates."*

### 4. Pilot Scope & Next Steps (4:00 - 5:00)
- *"To respect the pilot boundary, this portal evaluates national wind generation from Elexon. It does not contain your specific retail demand or contract portfolio, so it is not a thermal dispatch recommendation."*
- *"However, by quantifying the exact historical bias (+1.7 GW) and tail risk (4.1 GW), your trading desk can adjust procurement buffers systematically rather than guessing."*

---

## Part 2: Technical Lead Review
**Goal:** Knowledge transfer to internal tech lead reviewing architecture, data integrity, testing, and deployment.  
**Target Duration:** 4 - 5 minutes.

### 1. Architecture & Ingestion Design (0:00 - 1:15)
- **Open `docs/architecture.md` / Show System Architecture**:
  - *"The architecture is a single-container modular monolith designed for sub-50ms performance and zero runtime failure."*
  - *"We deliberately separated ingestion from serving. `ingest_elexon.py` extracted 21,024 WINDFOR forecast revisions and 1,776 FUELHH actuals from the live Elexon BMRS API with exponential backoff."*
  - *"Data is frozen in `data/snapshot.sqlite` (6.1 MB) with composite B-tree indices on `(publish_time, start_time)`. This bundled snapshot is opened strictly in read-only mode (`mode=ro`), ensuring reproducibility and compatibility with ephemeral container filesystems."*
  - *"Cryptographic integrity is audited in `data/manifest.json` (SHA-256: `c9a04991...`)."*

### 2. Domain Selection Rule & Named Test (1:15 - 2:30)
- **Open `backend/app/services/asof_selection.py` & `backend/tests/test_selection_and_evaluation.py`**:
  - *"The core domain rule: for delivery target $t$ on $D+1$ and cutoff $c$ on $D$, a forecast is eligible iff `publishTime <= c` and `startTime >= publishTime`."*
  - *"Show `test_post_cutoff_revision_cannot_enter_backtest`: we built a synthetic test with revisions at 08:30 (8,500 MW) and post-cutoff 12:30 (9,999 MW). The test proves mathematically that under a 09:20 cutoff, the 12:30 revision cannot enter the backtest."*
  - *"Negative lead times: Elexon WINDFOR stream contains past intervals (`startTime < publishTime`). We identified and filtered 4,321 negative lead rows."*
  - *"Missing data policy: if no forecast is eligible, it remains `null`. It is NEVER zero-filled, and missing intervals penalize coverage."*

### 3. Leak-Free Uncertainty & Evaluation Metrics (2:30 - 3:45)
- **Open `backend/app/services/uncertainty.py`**:
  - *"Our empirical residual band ($r = \text{actual} - \text{forecast}$) is strictly leak-free: for decision date $D$, it draws residuals exclusively from completed delivery days prior to $D$, evaluated under the exact same cutoff rule."*
  - *"If fewer than 48 prior samples exist, it returns `null` with 'Insufficient history'."*
  - *"Metrics: We use WAPE ($\sum |e| / \sum y$) instead of MAPE to prevent division-by-zero instability during low-wind regimes."*

### 4. Code Standards, Docker, & Repo Walkthrough (3:45 - 5:00)
- **Show Terminal / Test Suite**:
  - *"24 backend tests passing with pytest; 4 frontend tests with Vitest."*
  - *"100% clean Ruff linting; strict TypeScript compilation."*
  - *"Multi-stage Dockerfile builds the React frontend in Node 20, copies static assets into Python 3.12 slim, and runs as an unprivileged non-root user (`appuser`)."*
  - *"Heroku container stack (`heroku.yml`) and Docker Compose (`compose.yaml`) supported."*
  - *"Ready for anonymous GitHub push and deployment."*
