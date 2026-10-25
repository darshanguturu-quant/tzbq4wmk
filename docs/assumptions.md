# Project Assumptions and Policy Decisions

## 1. Scope and Calendar Bounds
- **Decision Window**: Purchase decisions made between `2026-01-01` and `2026-01-31` inclusive (31 decision dates).
- **Delivery Window**: Day-ahead power deliveries between `2026-01-02` and `2026-02-01` inclusive (31 delivery dates).
- **Data Range for Extraction**: WINDFOR publications and FUELHH actuals fetched from `2025-12-28` to `2026-02-02` to ensure full forecast coverage for early January decisions and late January deliveries.

## 2. Decision Gate: Evaluation Interval Policy
- **Empirical Observation (Phase 0)**:
  - WINDFOR forecasts are strictly hourly (`startTime` has `minute=0` for 100% of rows). No `:30` forecasts are emitted by Elexon.
  - FUELHH actuals are half-hourly (48 intervals per day, covering `:00` and `:30`).
- **Policy Decision**:
  - **Exact Hourly Match**: Evaluation is performed strictly on exact `startTime` matches (the 24 hourly timestamps `:00` each delivery day).
  - **No Synthetic Interpolation**: We do NOT interpolate, average, or forward-fill forecasts for `:30` intervals. Missing forecasts remain missing.
  - **Expected Intervals**: Exactly 24 hourly intervals per delivery day (`00:00`, `01:00`, ..., `23:00` UTC). Coverage is defined as `matched_intervals / 24`.

## 3. Decision Cutoff Presets
- Presets provided (all GMT/UTC):
  - **EPEX GB Hourly Day-Ahead**: `09:20` (Default)
  - **N2EX (Nord Pool) Day-Ahead**: `09:50`
  - **EPEX GB Half-Hourly Day-Ahead**: `15:30`
  - **Custom Time**: Any user-specified `HH:MM`.
- **Disclaimer**: *"Illustrative GB auction gate closure. Confirm your organisation's actual internal trading deadline."*
- **Cutoff Rule**: Only forecasts with `publishTime <= cutoff_time` on the decision date are eligible. A forecast published at `09:20:00` is eligible for a `09:20` cutoff; a forecast at `09:20:01` is not.

## 4. Negative Lead-Time Policy
- The live Elexon WINDFOR dataset contains past intervals where `startTime < publishTime`.
- **Policy**: All rows with `startTime < publishTime` are flagged and excluded from decision-time selection and error evaluation.

## 5. Actuals Revision Policy
- FUELHH stream data represents the latest settlement actuals available at extraction time.
- Labelled explicitly in UI and docs as *"Latest actuals at extraction time"*.

## 6. Sign and Error Conventions
- Error: $e = \text{forecast} - \text{actual}$ in Megawatts (MW).
  - Positive $e > 0$: Wind **overforecast** (realized wind generation was less than forecast).
  - Negative $e < 0$: Wind **underforecast** (realized wind generation was greater than forecast).
- Residual for uncertainty: $r = \text{actual} - \text{forecast} = -e$.

## 7. Uncertainty Band Policy
- Leak-free rolling empirical residual distribution:
  - For a decision date $D$ at cutoff $c$, usable residuals are derived strictly from delivery days $< D$ evaluated under the exact same cutoff rule.
  - Requires minimum sample size $N \ge \text{MIN\_BAND\_SAMPLES}$ (default 48 matched hourly intervals, i.e., 2 prior days).
  - If insufficient history is available, the UI displays *"Insufficient history for an uncertainty range"*.
  - Clearly disclaimed as an empirical residual-based range, not an official Elexon probabilistic forecast.
