# Wind Generation Forecast Bias Investigation (+1,745 MW)

## 1. Context & Problem Statement

When evaluating the official Elexon Day-Ahead Wind Generation Forecast (`WINDFOR`) under the standard EPEX GB Day-Ahead auction cutoff (`09:20 UTC`) against realized half-hourly settlement generation outturn (`FUELHH`) for January 2026 (744 hourly delivery intervals), the portal reveals:
- **Systematic Bias**: **+1,745.94 MW**
- **Overforecast Frequency**: **84.68% of evaluated intervals**
- **Mean Absolute Error (MAE)**: **2,022.47 MW**
- **Root Mean Squared Error (RMSE)**: **2,497.41 MW**
- **Weighted Absolute Percentage Error (WAPE)**: **17.92%**

This investigation was conducted to determine whether this gap represents meteorological forecasting error, a temporal alignment mismatch, or a reporting boundary difference between the two datasets.

> **Product Scope Boundary Note:**  
> In accordance with the assignment brief, the portal product uses **strictly and exclusively `FUELHH` and `WINDFOR`**.  
> The external `B1630` data discussed in Section 2.4 is an **out-of-scope diagnostic cross-check** performed solely for offline domain analysis. It is **not** present in `data/snapshot.sqlite`, the REST API, the frontend UI, or `data/manifest.json`.

---

## 2. Quantitative Empirical Tests

### 2.1 Test 1: Shortest-Lead Forecast (Lead-Time Horizon Dependency)
**Question**: Does the overforecast bias vanish or collapse as lead time closes to real-time physical delivery?

To test this, we selected the latest eligible `WINDFOR` forecast revision published immediately prior to each delivery hour ($t_{\text{pub}} \le t_{\text{start}}$, average lead time of **1.6 hours**, ranging between 0.5h and 3.5h), discarding the day-ahead gate closure constraint.

| Metric | Day-Ahead Decision (09:20 Cutoff) | Shortest-Lead Revision (~1.6h Lead Time) | Change ($\Delta$) | Persistence |
| :--- | :---: | :---: | :---: | :---: |
| **Lead Time** | 28.0 hours avg | 1.6 hours avg | -26.4 hours | — |
| **Bias (MW)** | **+1,745.94 MW** | **+1,471.15 MW** | -274.79 MW (-15.74%) | **84.26% persists** |
| **MAE (MW)** | **2,022.47 MW** | **1,679.87 MW** | -342.60 MW (-16.94%) | 83.06% persists |
| **RMSE (MW)**| **2,497.41 MW** | **2,141.08 MW** | -356.33 MW (-14.27%) | 85.73% persists |

**Finding**:
Over **84% of the bias (+1,471.15 MW) persists into the final 1–2 hours before delivery**. While shortening the lead time yields a modest 15.7% accuracy improvement, the bulk of the error is structural and does not dissipate with near-term weather updates.

---

### 2.2 Test 2: Forecast / Actual Ratio Across Wind Levels & Hour of Day (Proportional vs. Additive)
**Question**: Does the error behave as a constant additive offset (+1.7 GW across all conditions) or as a proportional scale mismatch?

#### A. By Wind-Level Tercile
We segmented the 744 evaluated intervals into three equal-sized terciles ($N = 248$ each) based on realized settlement actual generation:

| Wind Generation Regime | Range of Actuals (MW) | Mean Actual (MW) | Mean Forecast (MW) | Mean Bias (MW) | Aggregate Ratio ($\sum \text{Fc} / \sum \text{Act}$) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Low Wind** | 1,728 – 8,844 MW | 6,333.4 MW | 7,754.7 MW | **+1,421.3 MW** | **1.224x (+22.4%)** |
| **Medium Wind** | 8,851 – 14,458 MW | 11,658.5 MW | 13,211.6 MW | **+1,553.2 MW** | **1.133x (+13.3%)** |
| **High Wind** | 14,483 – 17,805 MW | 15,864.7 MW | 18,128.0 MW | **+2,263.4 MW** | **1.143x (+14.3%)** |
| **Full Month (All Hours)**| 1,728 – 17,805 MW | 11,285.5 MW | 13,031.4 MW | **+1,745.9 MW** | **1.1547x (+15.47%)** |

#### B. By Hour of Day (Diurnal Profile)
Evaluating the aggregate ratio $\sum \text{Forecast} / \sum \text{Actual}$ across each hour of the day (00:00 to 23:00 UTC) reveals:
- **Minimum Ratio**: **1.114x** at 15:00 UTC (Mean Act: 11,243 MW, Mean Fc: 12,520 MW, Bias: +1,277 MW)
- **Maximum Ratio**: **1.216x** at 05:00 UTC (Mean Act: 10,812 MW, Mean Fc: 13,151 MW, Bias: +2,339 MW)
- **Hourly Ratio Standard Deviation**: **0.0364** (tight stability across all 24 hours)

**Finding & Mathematical Characterization**:
1. The absolute Megawatt bias scales with generation volume: expanding from **+1,421.3 MW** in low wind to **+2,263.4 MW** in high wind.
2. The forecast/actual ratio is **highest at low wind (1.224x)** and **lower at high wind (1.143x)**. This empirical pattern is critical: because the ratio is highest during low wind regimes, transmission curtailment alone cannot explain the pattern (curtailment would produce a sharply higher ratio during high wind when transmission export limits bind).

---

### 2.3 Test 3: Timing Alignment & Averaging Invariance
**Question**: Does matching hourly WINDFOR (:00) against instantaneous :00 settlement actuals create an artificial error compared to averaging the two half-hourly settlement periods $(:00 + :30)/2$?

| Alignment Strategy | Evaluated Actual Definition | Mean Actual | Mean Forecast | Mean Bias | MAE |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Strategy (i): Exact :00** | Exact `:00` FUELHH settlement actual | 11,285.51 MW | 13,031.44 MW | **+1,745.94 MW** | **2,022.47 MW** |
| **Strategy (ii): Averaged**| Half-hourly mean $(:00 + :30)/2$ actual | 11,283.56 MW | 13,031.44 MW | **+1,747.89 MW** | **2,038.91 MW** |
| **Net Difference** | — | **+1.95 MW** | 0.00 MW | **-1.95 MW** | **-16.44 MW** |

**Finding**:
Timing alignment accounts for only **1.95 MW (0.11% of the bias)**. Both alignment methods yield essentially identical results. Timing misalignment is ruled out as the cause of the +1,745 MW gap.

---

### 2.4 Test 4: Official Elexon Documentation & Diagnostic Cross-Check (Out-of-Scope)

#### Official OpenAPI Specification References
From the official **Elexon OpenAPI specification** (`https://data.elexon.co.uk/swagger/v1/swagger.json`, retrieved 2026-10-26):

1. **`WINDFOR` (`GET /forecast/generation/wind`)**:
   > *"This provides wind generation forecast for wind farms which are visible to the ESO and have operational metering."*  
   > *(Source: Elexon OpenAPI specification, retrieved 2026-10-26).*

2. **`FUELHH` (`GET /datasets/FUELHH`)**:
   > *"This endpoint provides the half-hourly generation outturn (Generation By Fuel type) to give our users an indication of the generation outturn for Great Britain. The data is aggregated by Fuel Type category and updated at 30-minute intervals with average MW values over 30 minutes for each category."*  
   > *(Source: Elexon OpenAPI specification, retrieved 2026-10-26).*

3. **`B1630` / `AGWS` (`GET /generation/actual/per-type/wind-and-solar`)** (Diagnostic Only):
   > *"This endpoint provides actual or estimated wind and solar power generation per settlement period. It returns generation with Power System Resource type Solar, Wind Onshore or Wind Offshore (Fuel Type categories as defined by Commission Regulation (EU) No 543/2013). This endpoint filters by startTime and provides a maximum data output range of 7 days."*  
   > *(Source: Elexon OpenAPI specification, retrieved 2026-10-26).*

#### Out-of-Scope Diagnostic Cross-Check Across January 2026 (N = 720 common hours)
To investigate whether the observed +1,745 MW discrepancy reflects the forecast or the actuals, we pulled `B1630` transparency wind generation as an offline cross-check:
- **Mean WINDFOR Day-Ahead Forecast**: **13,227.75 MW**
- **Mean B1630 National Actuals (Regulation 543/2013)**: **13,662.13 MW**
- **Mean FUELHH Transmission Outturn**: **11,455.27 MW**
- **WINDFOR vs. B1630 Error**: **-434.38 MW (-3.18%)**
- **WINDFOR vs. FUELHH Error**: **+1,772.47 MW (+15.47%)**
- **B1630 vs. FUELHH Actuals Discrepancy**: **+2,206.85 MW (+19.26%)** ($r = 0.9924$)

---

## 3. Interpretation: Findings Strongly Supported by Cross-Check vs. Untested Hypotheses

### 3.1 Findings Strongly Supported by the Diagnostic Cross-Check (Not Proven at Unit Level)
1. **The Discrepancy Exists Between Elexon Datasets Themselves**: The two official Elexon actual generation streams—`B1630` (transparency actuals) and `FUELHH` (settlement outturn)—diverge by an average of **+2,206.85 MW (+19.26%)** across common hours in January 2026.
2. **`WINDFOR` Strongly Tracks `B1630`**: Day-ahead `WINDFOR` forecasts match total national wind actuals (`B1630`) within **-3.18% (-434 MW)** with a high correlation ($r = 0.9459$).
3. **Coverage Perimeter Divergence**: The cross-check strongly supports the conclusion that `WINDFOR` and `FUELHH` measure different perimeters of the GB wind fleet rather than simple meteorological inaccuracy. However, because unit-level operational telemetry is not published, this cause is strongly supported by the cross-check but not proven at the individual generator unit level.

### 3.2 Untested Hypotheses & Remaining Unknowns
Two hypotheses are commonly discussed in the GB power domain, but both remain **untested hypotheses** that cannot be verified from public Elexon API data alone:

- **Hypothesis A: Embedded Wind Generation**:
  - `B1630` includes modeled estimates of distribution-connected (embedded) wind generation under Regulation 543/2013, whereas `FUELHH` reports operational metering from transmission-connected Balancing Mechanism Units (BMUs).
  - Whether and to what extent NESO's `WINDFOR` models include distribution-connected wind cannot be confirmed from the API documentation alone.
- **Hypothesis B: Transmission Curtailment**:
  - `FUELHH` measures physical outturn after NESO executes downward balancing actions (BOALF) to resolve transmission export constraints.
  - However, as demonstrated in Test 2, the forecast/actual ratio is **highest at low wind (1.224x) and lower at high wind (1.143x)**. If curtailment were the sole or primary driver, the ratio would spike during high wind periods when transmission bottlenecks bind. Curtailment alone therefore does not explain the observed pattern.

> **What cannot be proven from public Elexon API data alone:**  
> Neither Elexon nor NESO publishes the unit roster, BMU mappings, or internal model architecture of `WINDFOR` in the public API. Therefore, any unit-level decomposition between embedded wind and transmission curtailment remains an unverified hypothesis.

---

## 4. Operational Takeaway for Wholesale Trading Desks

For wholesale trading teams evaluating day-ahead wind forecasts against settlement outturn (`FUELHH`):
1. **Gap Quantification**: The empirical gap between day-ahead `WINDFOR` and settlement outturn `FUELHH` averaged **+1,745.94 MW** (a ratio of **1.155x**) across January 2026.
2. **Client Demand Context**: The appropriate commercial adjustment depends on how the client defines its portfolio demand:
   - If the client procures against **gross national demand** (which includes embedded wind generation), raw `WINDFOR` may be closer to physical fleet capability.
   - If the client settles against **transmission-system demand / BMU outturn** (`FUELHH`), using raw `WINDFOR` without adjustment will systematically over-anticipate delivered wind volume.
3. **Uncertainty Protection**: Trading desks do not need to apply arbitrary fixed haircuts. The portal's **leak-free empirical residual bands** ($Q_{10}$ to $Q_{90}$) are derived directly from realized past forecast errors ($r = y - f$) and already reflect this structural gap.

---

## 5. Reproducibility & Verification Scripts

All quantitative figures in this report can be independently regenerated and verified from the repository root:

1. **Bias Investigation & Cross-Check Metrics**:
   ```bash
   python backend/scripts/investigate_bias.py
   ```
   - Connects to `data/snapshot.sqlite` to compute lead-time, tercile, diurnal, and alignment statistics.
   - Performs the diagnostic cross-check by fetching `B1630` data directly from:
     `GET https://data.elexon.co.uk/bmrs/api/v1/generation/actual/per-type/wind-and-solar?from={from}&to={to}`
     in 7-day slices across `2026-01-01T00:00:00Z` to `2026-01-31T23:59:59Z`, filtering records where `businessType == "Wind generation"`.
   - Saves all output metrics to [`data/bias_investigation_metrics.json`](../data/bias_investigation_metrics.json).

2. **Independent Interval Recomputation**:
   ```bash
   python backend/scripts/independent_recomputation.py
   ```
   - Randomly samples 3 delivery intervals across January 2026 with a fixed seed.
   - Recomputes as-of cutoff selection and signed error directly via raw SQL against `snapshot.sqlite` and compares against the REST API.
