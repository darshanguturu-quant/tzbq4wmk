import React, { useEffect, useState } from "react";
import { AlertTriangle, BarChart3, Clock, Compass, Layers, ShieldAlert, Sparkles, TrendingDown, TrendingUp } from "lucide-react";
import { fetchPerformance, fetchPerformanceCompare } from "../api/client";
import { ErrorHeatmap } from "../components/ErrorHeatmap";
import { CutoffComparisonItem, PerformanceResponse } from "../types";

interface PerformancePageProps {
  cutoff: string;
}

export const PerformancePage: React.FC<PerformancePageProps> = ({ cutoff }) => {
  const [data, setData] = useState<PerformanceResponse | null>(null);
  const [comparisons, setComparisons] = useState<CutoffComparisonItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);

    Promise.all([
      fetchPerformance(cutoff, "2026-01-01", "2026-01-31"),
      fetchPerformanceCompare(["09:20", "09:50", "15:30"], "2026-01-01", "2026-01-31"),
    ])
      .then(([perf, comps]) => {
        if (isMounted) {
          setData(perf);
          setComparisons(comps);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.message || "Failed to load performance metrics");
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [cutoff]);

  if (loading) {
    return (
      <div className="dashboard-grid">
        <div className="skeleton" style={{ height: "120px" }} />
        <div className="skeleton" style={{ height: "400px" }} />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="error-banner">
        <span>{error || "No performance data found."}</span>
      </div>
    );
  }

  const { headline, top_errors } = data;
  const biasDirection = (headline.bias_mw || 0) > 0 ? "Overforecast" : "Underforecast";

  // Build heatmap cell data directly from genuine matched delivery intervals
  const heatmapData = (data.intervals && data.intervals.length > 0)
    ? data.intervals.map((inv) => ({
        deliveryDate: inv.delivery_date,
        hour: inv.hour,
        forecastMw: inv.forecast_mw,
        actualMw: inv.actual_mw,
        errorMw: inv.error_mw,
      }))
    : data.daily_breakdown.flatMap((day) =>
        data.hourly_breakdown.map((h) => ({
          deliveryDate: day.delivery_date,
          hour: h.delivery_hour,
          forecastMw: day.mean_forecast_mw,
          actualMw: day.mean_actual_mw,
          errorMw: day.bias_mw,
        }))
      );

  return (
    <div className="dashboard-grid">
      {/* "So What" Executive Insight Callout */}
      <div className="callout-box">
        <Sparkles size={20} color="var(--cyan-accent)" style={{ flexShrink: 0, marginTop: "2px" }} />
        <div className="callout-text">
          <strong>Trading Intelligence Callout:</strong> {data.so_what}
        </div>
      </div>

      {/* Summary KPI Cards */}
      <div className="kpi-strip">
        <div className="kpi-card">
          <span className="kpi-label">
            <BarChart3 size={14} color="var(--wind-primary)" />
            Mean Absolute Error (MAE)
          </span>
          <div className="kpi-value">
            {headline.mae_mw?.toLocaleString() ?? "N/A"}
            <span className="kpi-unit">MW</span>
          </div>
          <span className="kpi-hint">Typical magnitude of deviation</span>
        </div>

        <div className="kpi-card">
          <span className="kpi-label">Root Mean Squared (RMSE)</span>
          <div className="kpi-value">
            {headline.rmse_mw?.toLocaleString() ?? "N/A"}
            <span className="kpi-unit">MW</span>
          </div>
          <span className="kpi-hint">Penalizes large outlier misses</span>
        </div>

        <div className="kpi-card">
          <span className="kpi-label">
            {headline.bias_mw && headline.bias_mw > 0 ? (
              <TrendingUp size={14} color="var(--danger-pos)" />
            ) : (
              <TrendingDown size={14} color="var(--danger-neg)" />
            )}
            Forecast Bias
          </span>
          <div
            className="kpi-value"
            style={{ color: (headline.bias_mw || 0) > 0 ? "var(--danger-pos)" : "var(--danger-neg)" }}
          >
            {(headline.bias_mw || 0) > 0 ? "+" : ""}
            {headline.bias_mw?.toLocaleString() ?? "N/A"}
            <span className="kpi-unit">MW</span>
          </div>
          <span className="kpi-hint">Net systematic {biasDirection}</span>
        </div>

        <div className="kpi-card">
          <span className="kpi-label">WAPE (Error / Total Wind)</span>
          <div className="kpi-value">
            {headline.wape !== null ? `${(headline.wape * 100).toFixed(1)}%` : "N/A"}
          </div>
          <span className="kpi-hint">Normalized weighted absolute error</span>
        </div>

        <div className="kpi-card">
          <span className="kpi-label">P90 Absolute Error</span>
          <div className="kpi-value">
            {headline.p90_abs_error_mw?.toLocaleString() ?? "N/A"}
            <span className="kpi-unit">MW</span>
          </div>
          <span className="kpi-hint">90% of intervals had error &le; this</span>
        </div>

        <div className="kpi-card">
          <span className="kpi-label">Evaluated Sample</span>
          <div className="kpi-value">
            {headline.n_matched}
            <span className="kpi-unit">/ {headline.expected_intervals} hrs</span>
          </div>
          <span className="kpi-hint">Coverage: {headline.coverage_pct}%</span>
        </div>
      </div>

      {/* Cutoff Comparison Panel (Should-Have) */}
      <div className="card">
        <div className="card-header">
          <div>
            <div className="card-title">
              <Clock size={18} color="var(--cyan-accent)" />
              Cutoff Preset Sensitivity Comparison
            </div>
            <div className="card-subtitle">
              Comparing GB auction gate closures strictly evaluated on the common intersection of {comparisons[0]?.n_common_intervals ?? 0} matched intervals.
            </div>
          </div>
        </div>

        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Gate Closure Preset</th>
                <th>Cutoff Time (UTC)</th>
                <th>Common Intervals</th>
                <th>MAE (MW)</th>
                <th>RMSE (MW)</th>
                <th>Bias (MW)</th>
                <th>WAPE</th>
                <th>P90 Error (MW)</th>
              </tr>
            </thead>
            <tbody>
              {comparisons.map((c, idx) => {
                const isSelected = c.cutoff_time === cutoff;
                return (
                  <tr key={idx} style={{ background: isSelected ? "rgba(0, 210, 106, 0.08)" : undefined }}>
                    <td style={{ fontWeight: isSelected ? 700 : 500 }}>
                      {c.cutoff_time === "09:20" && "EPEX GB Hourly Day-Ahead"}
                      {c.cutoff_time === "09:50" && "N2EX (Nord Pool) Day-Ahead"}
                      {c.cutoff_time === "15:30" && "EPEX GB Half-Hourly Day-Ahead"}
                      {isSelected && <span style={{ color: "var(--wind-primary)", marginLeft: "6px" }}>(Active)</span>}
                    </td>
                    <td className="font-mono">{c.cutoff_time}</td>
                    <td className="font-mono">{c.n_common_intervals}</td>
                    <td className="font-mono" style={{ fontWeight: 600, color: "var(--wind-primary)" }}>{c.mae_mw} MW</td>
                    <td className="font-mono">{c.rmse_mw} MW</td>
                    <td
                      className="font-mono"
                      style={{ color: (c.bias_mw || 0) > 0 ? "var(--danger-pos)" : "var(--danger-neg)" }}
                    >
                      {(c.bias_mw || 0) > 0 ? "+" : ""}{c.bias_mw} MW
                    </td>
                    <td className="font-mono">{c.wape !== null ? `${(c.wape * 100).toFixed(1)}%` : "N/A"}</td>
                    <td className="font-mono">{c.p90_abs_error_mw} MW</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Signed-Error Heatmap */}
      <div className="card">
        <div className="card-header">
          <div>
            <div className="card-title">
              <Compass size={18} color="var(--purple-accent)" />
              Daily Signed-Error Calendar Matrix (January 2026)
            </div>
            <div className="card-subtitle">
              Diverging color map showing hourly error distribution across all 31 delivery days.
            </div>
          </div>
        </div>

        <ErrorHeatmap data={heatmapData} />
      </div>

      {/* Two Column Grid: Error by Delivery Hour & Error by Lead-Time */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(450px, 1fr))", gap: "1.5rem" }}>
        {/* Error by Delivery Hour */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <Clock size={16} color="var(--cyan-accent)" />
              Error by Delivery Hour of Day
            </div>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>00:00 to 23:00 UTC</span>
          </div>

          <div className="table-container" style={{ maxHeight: "320px" }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Hour</th>
                  <th>MAE</th>
                  <th>Bias</th>
                  <th>Mean Fc</th>
                  <th>Mean Act</th>
                  <th>N</th>
                </tr>
              </thead>
              <tbody>
                {data.hourly_breakdown.map((h) => (
                  <tr key={h.delivery_hour}>
                    <td className="font-mono">{String(h.delivery_hour).padStart(2, "0")}:00</td>
                    <td className="font-mono">{h.mae_mw} MW</td>
                    <td
                      className="font-mono"
                      style={{ color: h.bias_mw > 0 ? "var(--danger-pos)" : "var(--danger-neg)" }}
                    >
                      {h.bias_mw > 0 ? "+" : ""}{h.bias_mw} MW
                    </td>
                    <td className="font-mono">{Math.round(h.mean_forecast_mw)} MW</td>
                    <td className="font-mono">{Math.round(h.mean_actual_mw)} MW</td>
                    <td className="font-mono" style={{ color: "var(--text-muted)" }}>{h.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Error by Lead-Time Band */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <Layers size={16} color="var(--wind-primary)" />
              Error by Lead-Time Band (6-Hour Windows)
            </div>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Horizon degradation</span>
          </div>

          <div className="table-container" style={{ maxHeight: "320px" }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Lead-Time Band</th>
                  <th>MAE</th>
                  <th>RMSE</th>
                  <th>Bias</th>
                  <th>WAPE</th>
                  <th>N</th>
                </tr>
              </thead>
              <tbody>
                {data.lead_time_breakdown.map((b, idx) => (
                  <tr key={idx}>
                    <td className="font-mono" style={{ fontWeight: 600 }}>{b.lead_time_band}</td>
                    <td className="font-mono">{b.mae_mw} MW</td>
                    <td className="font-mono">{b.rmse_mw} MW</td>
                    <td
                      className="font-mono"
                      style={{ color: b.bias_mw > 0 ? "var(--danger-pos)" : "var(--danger-neg)" }}
                    >
                      {b.bias_mw > 0 ? "+" : ""}{b.bias_mw} MW
                    </td>
                    <td className="font-mono">{b.wape !== null ? `${(b.wape * 100).toFixed(1)}%` : "N/A"}</td>
                    <td className="font-mono" style={{ color: "var(--text-muted)" }}>{b.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Wind Generation Level Terciles */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">
            <BarChart3 size={16} color="var(--actual-primary)" />
            Error Breakdown by Wind Generation Tercile
          </div>
          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Low, Medium, and High wind regimes</span>
        </div>

        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Wind Regime</th>
                <th>Outturn Generation Range</th>
                <th>MAE (MW)</th>
                <th>RMSE (MW)</th>
                <th>Bias (MW)</th>
                <th>WAPE</th>
                <th>Interval Count (N)</th>
              </tr>
            </thead>
            <tbody>
              {data.wind_level_breakdown.map((t, idx) => (
                <tr key={idx}>
                  <td style={{ fontWeight: 600 }}>{t.tercile}</td>
                  <td className="font-mono">{t.range_mw}</td>
                  <td className="font-mono" style={{ color: "var(--wind-primary)", fontWeight: 600 }}>{t.mae_mw} MW</td>
                  <td className="font-mono">{t.rmse_mw} MW</td>
                  <td
                    className="font-mono"
                    style={{ color: t.bias_mw > 0 ? "var(--danger-pos)" : "var(--danger-neg)" }}
                  >
                    {t.bias_mw > 0 ? "+" : ""}{t.bias_mw} MW
                  </td>
                  <td className="font-mono">{t.wape !== null ? `${(t.wape * 100).toFixed(1)}%` : "N/A"}</td>
                  <td className="font-mono">{t.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Top 10 Largest Positive & Negative Error Outliers */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(450px, 1fr))", gap: "1.5rem" }}>
        {/* Largest Overforecasts */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <AlertTriangle size={16} color="var(--danger-pos)" />
              Top 10 Largest Overforecasts (Fc &gt; Act)
            </div>
            <span style={{ fontSize: "0.75rem", color: "var(--danger-pos)" }}>Shortfall risk</span>
          </div>

          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Delivery Target</th>
                  <th>Forecast</th>
                  <th>Actual</th>
                  <th>Error</th>
                  <th>Lead</th>
                </tr>
              </thead>
              <tbody>
                {top_errors.largest_overforecasts.map((row, idx) => (
                  <tr key={idx}>
                    <td className="font-mono">{row.delivery_date} {row.start_time.substring(11, 16)}</td>
                    <td className="font-mono">{Math.round(row.forecast_mw).toLocaleString()} MW</td>
                    <td className="font-mono">{Math.round(row.actual_mw).toLocaleString()} MW</td>
                    <td className="font-mono" style={{ color: "var(--danger-pos)", fontWeight: 700 }}>
                      +{Math.round(row.error_mw).toLocaleString()} MW
                    </td>
                    <td className="font-mono" style={{ color: "var(--text-muted)" }}>{row.lead_time_hours}h</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Largest Underforecasts */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <ShieldAlert size={16} color="var(--cyan-accent)" />
              Top 10 Largest Underforecasts (Act &gt; Fc)
            </div>
            <span style={{ fontSize: "0.75rem", color: "var(--cyan-accent)" }}>Surplus spill risk</span>
          </div>

          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Delivery Target</th>
                  <th>Forecast</th>
                  <th>Actual</th>
                  <th>Error</th>
                  <th>Lead</th>
                </tr>
              </thead>
              <tbody>
                {top_errors.largest_underforecasts.map((row, idx) => (
                  <tr key={idx}>
                    <td className="font-mono">{row.delivery_date} {row.start_time.substring(11, 16)}</td>
                    <td className="font-mono">{Math.round(row.forecast_mw).toLocaleString()} MW</td>
                    <td className="font-mono">{Math.round(row.actual_mw).toLocaleString()} MW</td>
                    <td className="font-mono" style={{ color: "var(--danger-neg)", fontWeight: 700 }}>
                      {Math.round(row.error_mw).toLocaleString()} MW
                    </td>
                    <td className="font-mono" style={{ color: "var(--text-muted)" }}>{row.lead_time_hours}h</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
