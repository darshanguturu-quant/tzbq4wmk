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
- **Positive Error ($e_t > 0$)**: **Overforecast**. Wind generation was lower than expected. The utility faced an unforecasted shortfall and had to procure additional prompt power or pay imbalance penalties.
- **Negative Error ($e_t < 0$)**: **Underforecast**. Wind generation exceeded expectations. The utility had surplus power.

### 2.2 Mean Absolute Error (MAE)
$$\text{MAE} = \frac{1}{N} \sum_{t=1}^N |e_t| \quad (\text{MW})$$
Measures the expected average error magnitude regardless of direction.

### 2.3 Root Mean Squared Error (RMSE)
$$\text{RMSE} = \sqrt{\frac{1}{N} \sum_{t=1}^N e_t^2} \quad (\text{MW})$$
Applies quadratic weighting to highlight the risk of severe outlier forecast misses.

### 2.4 Systematic Bias
$$\text{Bias} = \frac{1}{N} \sum_{t=1}^N e_t \quad (\text{MW})$$
Identifies whether the forecasting process consistently over-predicts (positive bias) or under-predicts (negative bias) national wind output.

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

## 4. Empirical Investigation & Analysis of Forecast Bias (+1,745 MW)

During Phase 2 evaluation, the pipeline revealed a persistent positive bias of **+1,745.94 MW** across January 2026 under the standard day-ahead cutoff (09:20 UTC), with **84.7% of all intervals overforecasted**. To verify whether this resulted from an algorithmic anomaly, data misalignment, or underlying market structure, an independent investigation was conducted across four distinct hypotheses:

### 4.1 Hypothesis 1: Shortest-Lead Forecast (Lead-Time Dependency)
- **Question**: Does the positive bias disappear or diminish significantly as lead time closes to real-time delivery?
- **Methodology**: Evaluated the latest eligible WINDFOR revision published immediately before each delivery target hour ($t_{\text{pub}} \le t_{\text{start}}$, average lead time of **1.6 hours**, range 0.5h to 3.5h).
- **Findings**:
  - Day-Ahead Bias (09:20 cutoff, ~17–41h lead time): **+1,745.94 MW** (MAE: 2,022.47 MW)
  - Shortest-Lead Bias (immediate pre-delivery, ~1.6h lead time): **+1,471.15 MW** (MAE: 1,679.87 MW)
  - **Reduction in Bias**: Only **274.79 MW** (15.7% of the total bias).
- **Conclusion**: Over **84% of the bias (+1,471 MW) persists even 1–2 hours before delivery**. This proves the bias is not primarily driven by day-ahead meteorological forecast uncertainty, but represents a persistent structural baseline difference between the datasets.

### 4.2 Hypothesis 2: Forecast/Actual Ratio Across Wind Generation Levels
- **Question**: Is the bias an additive fixed offset or a proportional multiplier scaling with wind output?
- **Methodology**: Computed the ratio of Forecast to Actual generation across wind generation terciles.
- **Findings**:
  - **Low Wind Regime** (Actuals 1,728 – 8,844 MW):
    - Mean Forecast: 7,754.7 MW | Mean Actual: 6,333.4 MW | Bias: **+1,421.3 MW**
    - Aggregate Ratio ($\sum \text{Fc} / \sum \text{Act}$): **1.22x**
  - **Medium Wind Regime** (Actuals 8,851 – 14,458 MW):
    - Mean Forecast: 13,211.6 MW | Mean Actual: 11,658.5 MW | Bias: **+1,553.2 MW**
    - Aggregate Ratio ($\sum \text{Fc} / \sum \text{Act}$): **1.13x**
  - **High Wind Regime** (Actuals 14,483 – 17,805 MW):
    - Mean Forecast: 18,128.0 MW | Mean Actual: 15,864.7 MW | Bias: **+2,263.4 MW**
    - Aggregate Ratio ($\sum \text{Fc} / \sum \text{Act}$): **1.14x**
  - **Overall January 2026 Ratio**: $\sum \text{Forecast} / \sum \text{Actual} = \mathbf{1.155\times}$ (**+15.5%** overall).
- **Conclusion**: The forecast is consistently ~13% to 22% higher than actuals across all regimes. The bias in MW scales directly with generation volume (+1.4 GW in low wind up to +2.3 GW in high wind), behaving as a proportional capacity/output divergence.

### 4.3 Hypothesis 3: Hourly vs. Half-Hourly Alignment & Averaging
- **Question**: Does matching hourly WINDFOR (:00) against instantaneous :00 FUELHH actuals cause a discrepancy compared to averaging the two half-hourly periods $(:00 + :30)/2$?
- **Methodology**: Compared 09:20 day-ahead forecasts against (a) exact `:00` FUELHH actuals, versus (b) the hourly average of `:00` and `:30` actuals.
- **Findings**:
  - Exact `:00` Actuals Mean: **11,285.51 MW** (Bias: **+1,745.94 MW**, MAE: 2,022.47 MW)
  - Hourly Average $(:00 + :30)/2$ Actuals Mean: **11,283.56 MW** (Bias: **+1,747.89 MW**, MAE: 2,038.91 MW)
  - **Difference**: Exactly **1.95 MW** (0.11% of the bias).
- **Conclusion**: Interval alignment accounts for less than 2 MW. The chosen Phase 0 exact hourly matching policy is robust and does not distort the evaluation.

### 4.4 Hypothesis 4: Raw Elexon Dataset Definitions & Scope Discrepancy
- **Question**: Do FUELHH and WINDFOR measure and report the exact same asset boundary?
- **Findings from Industry & Regulatory Standards**:
  1. **FUELHH (`fuelType = "WIND"`)**: Reports half-hourly outturn generation measured exclusively from operational meters at **transmission-connected Balancing Mechanism Units (BMUs)**. Crucially, standard FUELHH fuel-type reporting **excludes embedded wind generation** (wind turbines connected to local distribution networks, which represent approximately 12–15% of total GB wind capacity). Furthermore, FUELHH reflects actual metered outturn *after* transmission constraint management and downward curtailment instructions by NESO.
  2. **WINDFOR**: Provides National Energy System Operator (NESO) meteorological forecasts designed to model total unconstrained national wind capacity.
  3. **Reconciliation**:
     $$\text{WINDFOR (Expected Unconstrained Total)} - \text{FUELHH (Metered Transmission Outturn)} \approx \text{Embedded Generation} + \text{Transmission Curtailment} + \text{Model Error}$$
- **Conclusion**: The observed +1,745 MW (~15.5%) bias reflects genuine, fundamental differences in the Elexon dataset definitions: WINDFOR estimates national fleet capability, while FUELHH tracks transmission-metered outturn net of curtailment and excluding distribution-connected assets. For commercial utility traders, this quantification is highly valuable: it confirms that raw transmission outturn systematically runs ~15% below national weather forecasts, allowing trading desks to calibrate their thermal procurement buffers accordingly.

