# Project Assumptions, Policy Decisions & Verification Record

## 1. Scope and Calendar Bounds
- **Decision Window**: Purchase decisions made between `2026-01-01` and `2026-01-31` inclusive (31 decision dates).
- **Delivery Window**: Day-ahead power deliveries between `2026-01-02` and `2026-02-01` inclusive (31 delivery dates).
- **Data Range for Extraction**: WINDFOR publications and FUELHH actuals fetched from `2025-12-28` to `2026-02-02` to ensure full forecast coverage for early January decisions and late January deliveries.
- **Product Scope Boundary**: In accordance with the assignment brief, the portal product uses **strictly and exclusively `FUELHH` (outturn actuals) and `WINDFOR` (forecast revisions)**. External diagnostic datasets (such as `B1630`) are out-of-scope diagnostic cross-checks used offline for research and are not present in `data/snapshot.sqlite`, the REST API, the frontend, or `data/manifest.json`.

---

## 2. Decision Gate: Evaluation Interval Policy
- **Empirical Observation (Phase 0 & Snapshot Audit)**:
  - WINDFOR forecasts: strictly hourly (`startTime` has `minute=0` for 100% of the 21,024 records in `data/snapshot.sqlite`). Exactly 0 records exist with `minute=30`.
  - FUELHH actuals: half-hourly (1,776 records in bundle, exactly 888 at `:00` and 888 at `:30`; exactly 48 intervals per delivery day).
- **Policy Decision**:
  - **Exact Hourly Match**: Evaluation is performed strictly on exact `startTime` matches (the 24 hourly timestamps `:00` each delivery day, totaling 744 matched pairs across January 2026, 100.0% coverage).
  - **No Synthetic Interpolation**: True 30-minute matched evaluation is impossible without synthetic interpolation or zero-filling. In accordance with the core domain rules, we do NOT interpolate, average, or forward-fill forecasts for `:30` intervals. Missing forecasts remain missing, and the 744 half-hourly (`:30`) actuals in January 2026 remain unmatched.
  - **Expected Intervals**: Exactly 24 hourly intervals per delivery day (`00:00`, `01:00`, ..., `23:00` UTC; 744 intervals for January 2026). Coverage is defined as `matched_intervals / 24`.

---

## 3. Decision Cutoff Presets & Sensitivity Comparison
- Presets provided (all GMT/UTC):
  - **EPEX GB Hourly Day-Ahead**: `09:20` (Default)
  - **N2EX (Nord Pool) Day-Ahead**: `09:50`
  - **EPEX GB Half-Hourly Day-Ahead**: `15:30`
  - **Custom Time**: Any user-specified `HH:MM` (e.g. `12:00`).
- **Disclaimer**: *"Illustrative GB auction gate closure. Confirm your organisation's actual internal trading deadline."*
- **Cutoff Rule**: Only forecasts with `publishTime <= cutoff_time` on the decision date are eligible. A forecast published at `09:20:00` is eligible for a `09:20` cutoff; a forecast at `09:20:01` is not.
- **Sensitivity Comparison Table**: Dynamically evaluates the active cutoff (whether preset or custom) alongside the standard presets strictly on the common intersection of matched intervals (744 common intervals across January 2026). Active custom cutoffs appear as their own clearly labelled `(Active)` row without modifying preset values.

---

## 4. Negative Lead-Time Policy & Lead-Time Band Derivation
- The live Elexon WINDFOR dataset contains past intervals where `startTime < publishTime`.
- **Policy**: All rows with `startTime < publishTime` are flagged and excluded from decision-time selection and error evaluation. Across January 2026 data, 4,321 negative lead-time rows were filtered.
- **Lead-Time Definition**: `lead_time_hours = startTime - publishTime` of the actually selected forecast row for that interval.
- **Lead-Time Band Derivation & Verified Fallback Annotation**:
  - Binned directly into standard 6-hour bins: `0-6h`, `6-12h`, `12-18h`, `18-24h`, `24-30h`, `30-36h`, `36-42h`, `42-48h`, `48h+`, without capping or reassignment.
  - At cutoff 09:20, the `36-42h` band contains 124 intervals ($4 \text{ hours} \times 31 \text{ days}$), because selecting the 07:30 UTC publication naturally yields lead times up to 39.5h for delivery hours 20:00 to 23:00.
  - At cutoff 12:00, the `36-42h` band contains exactly 2 intervals (12-18h: 184, 18-24h: 186, 24-30h: 186, 30-36h: 186, 36-42h: 2, total 744). On 2026-01-15, Elexon did not publish an 11:30 UTC revision (the next publication occurred at 12:25:00 UTC, as verified from snapshot and live BMRS data). Consequently, for delivery targets 2026-01-16 22:00 and 23:00, the cutoff-constrained selector fell back to the 09:30 UTC publication, giving exact raw lead times of 36.5h and 37.5h.

---

## 5. Actuals Revision Policy
- FUELHH stream data represents the latest settlement actuals available at extraction time.
- Labelled explicitly in UI and docs as *"Latest actuals at extraction time"*.

---

## 6. Sign and Error Conventions
- Error: $e = \text{forecast} - \text{actual}$ in Megawatts (MW).
  - Positive $e > 0$: Wind **overforecast** (realized wind generation was less than forecast).
  - Negative $e < 0$: Wind **underforecast** (realized wind generation was greater than forecast).
- Metric: Root Mean Square Error (RMSE), defined as $\text{RMSE} = \sqrt{\frac{1}{N} \sum e^2}$.
- Residual for uncertainty: $r = \text{actual} - \text{forecast} = -e$.

---

## 7. Uncertainty Band Policy & 0 MW Flooring Rule
- Leak-free rolling empirical residual distribution:
  - For a decision date $D$ at cutoff $c$, usable residuals are derived strictly from delivery days $< D$ evaluated under the exact same cutoff rule.
  - Requires minimum sample size $N \ge \text{MIN\_BAND\_SAMPLES}$ (default 48 matched hourly intervals, i.e., 2 prior days).
  - If insufficient history is available, the UI displays *"Insufficient history for an uncertainty range"*.
  - Clearly disclaimed as an empirical residual-based range, not an official Elexon probabilistic forecast.
- **Percentile Formula & Physical Flooring Rule**:
  $$\text{lower} = \max(0.0, \text{forecast} + Q_{10}(r)), \quad \text{upper} = \text{forecast} + Q_{90}(r)$$
  - *Flooring Justification*: Because WINDFOR has a strong positive bias (+1,745 MW), empirical residuals $r = \text{actual} - \text{forecast}$ are predominantly negative ($Q_{10} \approx -4,500$ to $-5,000$ MW). For moderate-to-low forecast hours where $\text{forecast} < |Q_{10}(r)|$, the unconstrained bound is negative. Because physical wind power generation cannot be negative ($Generation \ge 0\text{ MW}$), the lower bound is explicitly floored at **0.0 MW**.
- **Commercial Usage**: The empirical residual band already accounts for the observed structural gap between WINDFOR and FUELHH (+1,745 MW), providing a dynamic empirical confidence interval without requiring arbitrary fixed haircuts.

---

## 8. Verification Record: Confirmed vs. Unconfirmed Domain Items

This section records the audit status of the PRD open verification items and domain findings:

### 8.1 Items Confirmed by Live API and Data Inspection
1. **FUELHH Generation Semantics & Units**:
   - **Status**: [CONFIRMED]
   - **Evidence**: Verified via live API query (`GET /datasets/FUELHH/stream`) and official OpenAPI specification (`https://data.elexon.co.uk/swagger/v1/swagger.json`, retrieved 2026-10-26).
   - **Details**: FUELHH reports half-hourly generation outturn for Great Britain aggregated by fuel type in average Megawatts (MW) over 30-minute intervals (settlement periods 1 to 48), providing an indication of GB generation outturn.
2. **WINDFOR Real Publication Schedule**:
   - **Status**: [CONFIRMED]
   - **Evidence**: Probed across all dates in January 2026.
   - **Details**: Real publish times occur ~8 times daily around `02:30, 04:30, 07:30, 09:30, 11:30/12:25, 15:30, 18:30, 22:30` UTC. For `09:20` and `09:50` day-ahead cutoffs, the latest available revision is typically the `07:30` publication.
3. **Hourly Target Resolution of WINDFOR**:
   - **Status**: [CONFIRMED]
   - **Evidence**: 100% of the 21,024 WINDFOR records have `minute = 0`.
   - **Details**: Elexon emits only hourly forecasts (`:00` timestamps). No half-hourly `:30` forecasts exist in WINDFOR.
4. **Timing Alignment Invariance**:
   - **Status**: [CONFIRMED]
   - **Evidence**: Recomputed in `backend/scripts/investigate_bias.py`.
   - **Details**: Comparing exact `:00` actuals (Bias: +1,745.94 MW) against hourly averaged $(:00 + :30)/2$ actuals (Bias: +1,747.89 MW) reveals a difference of only 1.95 MW (0.11%). Timing alignment is ruled out as an error driver.
5. **Persistence of Systematic Bias Across Horizons**:
   - **Status**: [CONFIRMED]
   - **Evidence**: Shortest-lead forecast evaluation (~1.6h average lead time) yields a persistent bias of **+1,471.15 MW** (84.26% persists). The bias is structural, not day-ahead weather uncertainty.
6. **Divergence Between Elexon Generation Actual Feeds**:
   - **Status**: [CONFIRMED via Out-of-Scope Diagnostic Cross-Check]
   - **Evidence**: Pulling `B1630` transparency actuals (Regulation 543/2013) across January 2026 reveals a mean of 13,662.13 MW vs. FUELHH mean of 11,455.27 MW (+2,206.85 MW / +19.26% divergence). Day-ahead `WINDFOR` (13,227.75 MW) tracks `B1630` within -3.18% (-434 MW).
   - **Boundary Confirmation**: `B1630` is strictly an out-of-scope diagnostic cross-check; it is not bundled into `data/snapshot.sqlite`, the REST API, the frontend, or the manifest.

### 8.2 Items Unconfirmed or Untested (Remaining Domain Unknowns)
1. **Internal Unit Roster of WINDFOR**:
   - **Status**: [UNCONFIRMED / UNVERIFIED]
   - **Reason**: NESO and Elexon do not publish the individual BMU registry or list of distribution-connected metering units feeding into `WINDFOR` forecast models in the public API.
2. **Decomposition Between Embedded Wind and Transmission Curtailment**:
   - **Status**: [UNCONFIRMED / UNTESTED HYPOTHESIS]
   - **Reason**: While the diagnostic cross-check strongly supports a coverage perimeter difference rather than pure forecast error, unit-level BMU telemetry was not tested, and the exact quantitative split between distribution-connected (embedded) wind generation vs. transmission curtailment remains untested.
3. **Transmission Curtailment as the Sole Explanation**:
   - **Status**: [NOT SUPPORTED AS THE SOLE EXPLANATION]
   - **Reason**: The forecast/actual ratio is **highest at low wind (1.224x) and lower at high wind (1.143x)**. This ratio pattern provides evidence against curtailment alone being the explanation (curtailment would typically elevate the ratio during high-wind transmission export constraints), rather than serving as a direct test of curtailment.
4. **FUELHH BMU Scope Boundary (Transmission-Connected Units)**:
   - **Status**: [UNCONFIRMED / BACKGROUND CONTEXT]
   - **Reason**: Industry background context often treats FUELHH outturn as reflecting operational metering for transmission-connected Balancing Mechanism Units (BMUs). However, the primary Elexon OpenAPI specification states only that it provides *"an indication of the generation outturn for Great Britain"* without specifying an explicit BMU boundary. Because no primary-source documentation sentence in the API specification confirms this boundary, it is treated as unconfirmed background context rather than a confirmed fact.
