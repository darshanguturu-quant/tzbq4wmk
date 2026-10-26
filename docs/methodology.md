# Domain Selection & Evaluation Methodology

## 1. As-Of Decision-Time Selection Rule

In day-ahead wholesale electricity procurement, trading decisions must be made before a fixed auction gate closure (the **decision cutoff** $c$) on decision date $D$. The power is delivered on the delivery date $D + 1$.

A forecast can only be used for trading if it was physically published at or before the cutoff time. Using revisions published after the gate closure introduces **look-ahead bias** and invalidates commercial decision evaluations.

### Formal Selection Algorithm
For each target delivery hour $t$ on delivery date $D + 1$ under cutoff timestamp $c$ on date $D$:

$$\text{eligible}(t, c) = \left\{ \text{row} \in \text{WINDFOR} \mid \text{row.startTime} = t \land \text{row.publishTime} \le c \land \text{row.startTime} \ge \text{row.publishTime} \right\}$$

$$\text{selected}(t, c) = \begin{cases} 
\text{row} \in \text{eligible}(t, c) \text{ with } \max(\text{publishTime}), & \text{if } \text{eligible}(t, c) \neq \emptyset \\ 
\text{null}, & \text{if } \text{eligible}(t, c) = \emptyset 
\end{cases}$$

### Worked Concrete Example
Consider delivery target `2026-01-16T00:00:00Z` on decision date `2026-01-15`:
- Publication at `04:30 UTC`: Forecast = 8,000 MW
- Publication at `07:30 UTC`: Forecast = 8,500 MW
- Publication at `09:30 UTC`: Forecast = 9,200 MW
- Publication at `12:25 UTC`: Forecast = 9,800 MW

Under the **EPEX Hourly Day-Ahead** gate closure (`09:20 UTC`):
- Eligible revisions: 04:30 and 07:30 (both $\le$ 09:20).
- Post-cutoff revisions: 09:30 and 12:25 ($>$ 09:20) are strictly disqualified.
- **Selected Decision Forecast**: **8,500 MW** (published at 07:30 UTC, age at decision: 110 minutes).
- **Guaranteed Property**: The 09:30 revision (9,200 MW) CANNOT enter the decision backtest. This is proved by the automated test `test_post_cutoff_revision_cannot_enter_backtest`.

---

## 2. Mathematical Error Metrics Definitions

Let $f_t$ be the selected decision-time forecast for target hour $t$, and $y_t$ be the realized settlement actual generation from FUELHH for that same target hour.

### 2.1 Signed Forecast Error ($e_t$)
$$e_t = f_t - y_t \quad (\text{MW})$$
- **Positive Error ($e_t > 0$)**: **Overforecast**. Realized wind generation was lower than forecasted. The utility faced an unforecasted shortfall.
- **Negative Error ($e_t < 0$)**: **Underforecast**. Realized wind generation exceeded expectations. The utility had surplus power.

### 2.2 Mean Absolute Error (MAE)
$$\text{MAE} = \frac{1}{N} \sum_{t=1}^N |e_t| \quad (\text{MW})$$
Measures the expected average error magnitude regardless of direction.

### 2.3 Root Mean Squared Error (RMSE)
$$\text{RMSE} = \sqrt{\frac{1}{N} \sum_{t=1}^N e_t^2} \quad (\text{MW})$$
Applies quadratic weighting to highlight the risk of severe outlier forecast misses.

### 2.4 Systematic Bias
$$\text{Bias} = \frac{1}{N} \sum_{t=1}^N e_t \quad (\text{MW})$$
Identifies whether the forecasting process consistently over-predicts (positive bias) or under-predicts (negative bias) settlement wind output.

### 2.5 Weighted Absolute Percentage Error (WAPE)
$$\text{WAPE} = \frac{\sum_{t=1}^N |e_t|}{\sum_{t=1}^N y_t}$$
A scale-independent relative accuracy metric. Unlike MAPE (which divides by each individual interval's generation and explodes when wind output approaches zero), WAPE aggregates total error over total realized generation, remaining stable across low-wind regimes.

### 2.6 P90 Absolute Error
The 90th percentile of observed absolute errors $|e_t|$ across the sample. In 90% of evaluated intervals, the absolute error was less than or equal to this threshold.

### 2.7 Interval Coverage
$$\text{Coverage} = \frac{N_{\text{matched}}}{N_{\text{expected}}} \times 100\%$$
Where $N_{\text{expected}} = 24 \times \text{number of delivery days}$. Missing intervals are counted against coverage and never filled with zero.

---

## 3. Leak-Free Empirical Uncertainty Band

To provide trading desks with an actionable range of potential outcomes without fabricating probabilistic distributions:
1. **Residual Definition**: Residual $r = y - f = -e$ (MW).
2. **Temporal Lookback Isolation**: For a decision on date $D$ at cutoff $c$, usable residuals are derived strictly from delivery dates $\le D - 1$ (which completed prior to $c$ on date $D$). Furthermore, each past delivery interval must have been evaluated under the **exact same cutoff rule** for its own decision date.
3. **Band Calculation**:
   $$\text{Lower Bound} = \max(0, f_t + Q_{10}(r))$$
   $$\text{Upper Bound} = f_t + Q_{90}(r)$$
4. **Sample Threshold ($N \ge \text{MIN\_BAND\_SAMPLES}$)**: If the usable history contains fewer than 48 hourly points, no band is drawn, and the UI displays *"Insufficient history for an uncertainty range"*.
5. **Transparency**: The band is clearly documented as an empirical error band based on past residuals, not an official Elexon probabilistic forecast.

---

## 4. Empirical Investigation of Forecast Bias (+1,745 MW)

*(Full quantitative data and reproducibility scripts are documented in [docs/bias_investigation.md](bias_investigation.md)).*

During evaluation, comparing day-ahead `WINDFOR` forecasts under the 09:20 cutoff against `FUELHH` settlement outturn revealed a persistent positive bias of **+1,745.94 MW** across January 2026, with **84.68% of all intervals overforecasted**.

An independent investigation tested four hypotheses to understand this gap, separating verified empirical observations from untested domain hypotheses.

> **Product Scope Boundary Note:**  
> The portal product uses **strictly and exclusively `FUELHH` and `WINDFOR`**, as required by the assignment brief.  
> The `B1630` data discussed below is an **out-of-scope diagnostic cross-check** performed offline to understand dataset coverage. It is **not** included in `data/snapshot.sqlite`, the REST API, the frontend, or `data/manifest.json`.

### 4.1 Test 1: Shortest-Lead Forecast (Lead-Time Dependency)
- **Question**: Does the positive bias disappear or diminish significantly as lead time closes to real-time delivery?
- **Methodology**: Evaluated the latest eligible WINDFOR revision published immediately before each delivery target hour ($t_{\text{pub}} \le t_{\text{start}}$, average lead time of **1.6 hours**, range 0.5h to 3.5h).
- **Verified Findings**:
  - Day-Ahead Bias (09:20 cutoff, ~28h average lead time): **+1,745.94 MW** (MAE: 2,022.47 MW)
  - Shortest-Lead Bias (immediate pre-delivery, ~1.6h lead time): **+1,471.15 MW** (MAE: 1,679.87 MW)
  - **Reduction in Bias**: Only **274.79 MW** (15.74% of the total bias).
- **Conclusion**: Over **84% of the bias (+1,471.15 MW) persists even 1–2 hours before delivery**. This proves the bias is not primarily driven by day-ahead meteorological forecast uncertainty, but represents a persistent structural difference between the datasets.

### 4.2 Test 2: Forecast/Actual Ratio Across Wind Generation Levels
- **Question**: Is the bias an additive fixed offset or a proportional scale difference?
- **Methodology**: Computed the ratio of Forecast to Actual generation across wind generation terciles.
- **Verified Findings**:
  - **Low Wind Regime** (Actuals 1,728 – 8,844 MW):
    - Mean Forecast: 7,754.7 MW | Mean Actual: 6,333.4 MW | Bias: **+1,421.3 MW**
    - Aggregate Ratio ($\sum \text{Fc} / \sum \text{Act}$): **1.224x (+22.4%)**
  - **Medium Wind Regime** (Actuals 8,851 – 14,458 MW):
    - Mean Forecast: 13,211.6 MW | Mean Actual: 11,658.5 MW | Bias: **+1,553.2 MW**
    - Aggregate Ratio ($\sum \text{Fc} / \sum \text{Act}$): **1.133x (+13.3%)**
  - **High Wind Regime** (Actuals 14,483 – 17,805 MW):
    - Mean Forecast: 18,128.0 MW | Mean Actual: 15,864.7 MW | Bias: **+2,263.4 MW**
    - Aggregate Ratio ($\sum \text{Fc} / \sum \text{Act}$): **1.143x (+14.3%)**
  - **Overall January 2026 Ratio**: $\sum \text{Forecast} / \sum \text{Actual} = \mathbf{1.1547\times}$ (**+15.47%** overall).
- **Conclusion**: The absolute Megawatt bias scales with generation volume (+1.4 GW in low wind up to +2.3 GW in high wind). Crucially, the forecast/actual ratio is **highest at low wind (1.224x) and lower at high wind (1.143x)**. This ratio pattern provides evidence against curtailment alone being the explanation (curtailment would typically elevate the ratio during high-wind transmission export constraints), rather than serving as a direct test of curtailment.

### 4.3 Test 3: Hourly vs. Half-Hourly Alignment & Averaging
- **Question**: Does matching hourly WINDFOR (:00) against instantaneous :00 FUELHH actuals cause a discrepancy compared to averaging the two half-hourly periods $(:00 + :30)/2$?
- **Methodology**: Compared 09:20 day-ahead forecasts against (a) exact `:00` FUELHH actuals, versus (b) the hourly average of `:00` and `:30` actuals.
- **Verified Findings**:
  - Exact `:00` Actuals Mean: **11,285.51 MW** (Bias: **+1,745.94 MW**, MAE: 2,022.47 MW)
  - Hourly Average $(:00 + :30)/2$ Actuals Mean: **11,283.56 MW** (Bias: **+1,747.89 MW**, MAE: 2,038.91 MW)
  - **Difference**: Exactly **1.95 MW** (0.11% of the bias).
- **Conclusion**: Interval alignment accounts for less than 2 MW. The chosen exact hourly matching policy does not distort the evaluation.

### 4.4 Test 4: Elexon Documentation & Diagnostic Cross-Check (Out-of-Scope)

#### Official OpenAPI Specification References
From the official **Elexon OpenAPI specification** (`https://data.elexon.co.uk/swagger/v1/swagger.json`, retrieved 2026-10-26):
1. **WINDFOR (`GET /forecast/generation/wind`)**:
   > *"This provides wind generation forecast for wind farms which are visible to the ESO and have operational metering."*  
   > *(Source: Elexon OpenAPI specification, retrieved 2026-10-26).*
2. **FUELHH (`GET /datasets/FUELHH`)**:
   > *"This endpoint provides the half-hourly generation outturn (Generation By Fuel type) to give our users an indication of the generation outturn for Great Britain. The data is aggregated by Fuel Type category and updated at 30-minute intervals with average MW values over 30 minutes for each category."*  
   > *(Source: Elexon OpenAPI specification, retrieved 2026-10-26).*  
   > *(Background context note: While industry domain discussions frequently assume FUELHH reflects operational metering for transmission-connected Balancing Mechanism Units, this boundary is unconfirmed as the primary OpenAPI documentation does not specify a BMU restriction).*
3. **B1630 / AGWS (`GET /generation/actual/per-type/wind-and-solar`)** (Diagnostic Cross-Check):
   > *"This endpoint provides actual or estimated wind and solar power generation per settlement period. It returns generation with Power System Resource type Solar, Wind Onshore or Wind Offshore (Fuel Type categories as defined by Commission Regulation (EU) No 543/2013). This endpoint filters by startTime and provides a maximum data output range of 7 days."*  
   > *(Source: Elexon OpenAPI specification, retrieved 2026-10-26).*

#### Out-of-Scope Diagnostic Cross-Check Across January 2026 (N = 720 common hours)
- **Mean WINDFOR (09:20 Day-Ahead Forecast)**: **13,227.75 MW**
- **Mean B1630 (National Actual/Estimated Wind)**: **13,662.13 MW**
- **Mean FUELHH (Settlement Outturn)**: **11,455.27 MW**
- **WINDFOR vs. FUELHH Bias**: **+1,772.47 MW (+15.47%)**
- **WINDFOR vs. B1630 Bias**: **-434.38 MW (-3.18%)**
- **B1630 vs. FUELHH Outturn Discrepancy**: **+2,206.85 MW (+19.26%)**
- **Correlation**: $r(\text{B1630}, \text{FUELHH}) = \mathbf{0.9924}$; $r(\text{WINDFOR}, \text{B1630}) = \mathbf{0.9459}$.

### 4.5 Findings Supported by Cross-Check vs. Untested Hypotheses
- **Finding Strongly Supported by Cross-Check (Not Proven at Unit Level)**:  
  The discrepancy between `WINDFOR` and `FUELHH` is **strongly supported by the cross-check as reflecting a coverage difference between the two datasets**, rather than meteorological forecasting error; however, unit-level BMU telemetry and individual generator metering were not tested (as public Elexon feeds do not provide per-unit breakdowns), and the specific quantitative split between embedded generation and curtailment remains untested.
- **Untested Hypotheses**:
  - *Embedded Wind*: `B1630` includes modeled estimates of distribution-connected (embedded) wind generation under Regulation 543/2013. In industry background context (unconfirmed), `FUELHH` is often assumed to capture only transmission-connected Balancing Mechanism Units (BMUs). Whether and to what extent NESO's `WINDFOR` includes embedded wind cannot be verified from the API documentation alone.
  - *Curtailment*: `FUELHH` measures outturn after NESO downward balancing instructions (BOALF). However, transmission curtailment is **not supported as the sole explanation**. Because the forecast/actual ratio is higher at low wind (1.224x) than at high wind (1.143x), this ratio pattern provides evidence against curtailment alone being the explanation, rather than serving as a direct test of curtailment.
- **Remaining Unknowns**:
  - The proprietary unit registration lists and internal model structures inside NESO's forecasting system are not published in the public Elexon API. Therefore, the exact numerical breakdown between embedded wind and transmission curtailment remains an untested hypothesis.
- **Operational Guidance**:
  - The size of the gap against `FUELHH` is **+1,745.94 MW** (~15.5%).
  - The right commercial adjustment depends on how the client defines demand (gross national demand vs. net transmission demand).
  - Trading desks do not need to guess fixed haircuts: the portal's **leak-free empirical residual uncertainty band** ($Q_{10}$ to $Q_{90}$) is computed from realized past forecast errors and already reflects this structural gap.
