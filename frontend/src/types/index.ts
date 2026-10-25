export interface Preset {
  id: string;
  name: string;
  cutoff_time: string;
  description: string;
}

export interface Metadata {
  scope: {
    product_name: string;
    decision_dates: string;
    delivery_dates: string;
    data_source: string;
    client_context: string;
  };
  cutoff_presets: Preset[];
  default_cutoff: string;
  interval_policy: {
    forecast_resolution: string;
    actuals_resolution: string;
    evaluation_interval_policy: string;
    expected_intervals_per_day: number;
  };
  disclaimers: Record<string, string>;
  min_band_samples: number;
  manifest: Record<string, any>;
}

export interface DecisionInterval {
  start_time: string;
  selected_publish_time: string | null;
  forecast_mw: number | null;
  forecast_age_minutes: number | null;
  lead_time_hours: number | null;
  actual_mw: number | null;
  error_mw: number | null;
  lower_mw: number | null;
  upper_mw: number | null;
}

export interface DecisionProfile {
  decision_date: string;
  decision_cutoff: string;
  delivery_date: string;
  selection_policy: string;
  expected_intervals: number;
  forecast_intervals: number;
  matched_intervals: number | null;
  peak_forecast_mw: number | null;
  min_forecast_mw: number | null;
  average_forecast_mw: number | null;
  forecast_age_range_minutes: string | null;
  intervals: DecisionInterval[];
  uncertainty?: {
    has_band: boolean;
    reason: string | null;
    samples_count: number;
    min_required: number;
    q10_residual_mw: number | null;
    q90_residual_mw: number | null;
    average_width_mw?: number;
  } | null;
}

export interface HeadlineMetrics {
  n_matched: number;
  expected_intervals: number;
  coverage_pct: number;
  mae_mw: number | null;
  rmse_mw: number | null;
  bias_mw: number | null;
  wape: number | null;
  p90_abs_error_mw: number | null;
  overforecast_pct: number | null;
  underforecast_pct: number | null;
  exact_match_pct: number | null;
}

export interface HourlyBreakdownItem {
  delivery_hour: number;
  count: number;
  mae_mw: number;
  rmse_mw: number;
  bias_mw: number;
  wape: number | null;
  mean_forecast_mw: number;
  mean_actual_mw: number;
}

export interface LeadTimeBreakdownItem {
  lead_time_band: string;
  count: number;
  mae_mw: number;
  rmse_mw: number;
  bias_mw: number;
  wape: number | null;
}

export interface DailyBreakdownItem {
  decision_date: string;
  delivery_date: string;
  count: number;
  coverage_pct: number;
  mae_mw: number;
  rmse_mw: number;
  bias_mw: number;
  wape: number | null;
  mean_forecast_mw: number;
  mean_actual_mw: number;
}

export interface WindLevelBreakdownItem {
  tercile: string;
  range_mw: string;
  count: number;
  mae_mw: number;
  rmse_mw: number;
  bias_mw: number;
  wape: number | null;
}

export interface TopErrorItem {
  start_time: string;
  decision_date: string;
  delivery_date: string;
  forecast_mw: number;
  actual_mw: number;
  error_mw: number;
  lead_time_hours: number | null;
}

export interface PerformanceResponse {
  cutoff_time: string;
  start_date: string;
  end_date: string;
  headline: HeadlineMetrics;
  hourly_breakdown: HourlyBreakdownItem[];
  lead_time_breakdown: LeadTimeBreakdownItem[];
  daily_breakdown: DailyBreakdownItem[];
  wind_level_breakdown: WindLevelBreakdownItem[];
  top_errors: {
    largest_overforecasts: TopErrorItem[];
    largest_underforecasts: TopErrorItem[];
  };
  so_what: string;
}

export interface CutoffComparisonItem {
  cutoff_time: string;
  n_common_intervals: number;
  mae_mw: number | null;
  rmse_mw: number | null;
  bias_mw: number | null;
  wape: number | null;
  p90_abs_error_mw: number | null;
}

export interface DataQualityResponse {
  start_date: string;
  end_date: string;
  cutoff_time: string;
  expected_intervals: number;
  intervals_with_forecast: number;
  intervals_with_actuals: number;
  matched_pairs: number;
  coverage_percentage: number;
  negative_lead_rows_excluded: number;
  conflicting_forecast_duplicates: number;
  conflicting_actual_duplicates: number;
  extraction_timestamp_utc: string | null;
  snapshot_sha256: string | null;
  api_base_url: string | null;
  warnings: string[];
}
