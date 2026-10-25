import React, { useEffect, useState } from "react";
import { AlertCircle, Calendar, Eye, EyeOff, TrendingUp, Wind, Zap } from "lucide-react";
import { fetchDecisionProfile } from "../api/client";
import { DecisionChart } from "../components/DecisionChart";
import { DecisionProfile } from "../types";

interface DecisionReplayPageProps {
  cutoff: string;
}

export const DecisionReplayPage: React.FC<DecisionReplayPageProps> = ({ cutoff }) => {
  const [decisionDate, setDecisionDate] = useState("2026-01-15");
  const [includeActuals, setIncludeActuals] = useState(false);
  const [includeBand, setIncludeBand] = useState(true);
  const [data, setData] = useState<DecisionProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);

    fetchDecisionProfile(decisionDate, cutoff, includeActuals, includeBand)
      .then((profile) => {
        if (isMounted) {
          setData(profile);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.message || "Failed to load decision profile");
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [decisionDate, cutoff, includeActuals, includeBand]);

  return (
    <div className="dashboard-grid">
      {/* Top Banner & Control Bar */}
      <div className="card" style={{ padding: "1.25rem 1.5rem" }}>
        <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: "1rem" }}>
          {/* Decision Date Picker */}
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <Calendar size={18} color="var(--cyan-accent)" />
            <span style={{ fontWeight: 600, fontSize: "0.9rem" }}>Decision Date:</span>
            <input
              type="date"
              min="2026-01-01"
              max="2026-01-31"
              value={decisionDate}
              onChange={(e) => setDecisionDate(e.target.value)}
              style={{
                background: "var(--bg-canvas)",
                border: "1px solid var(--border-subtle)",
                color: "var(--text-main)",
                padding: "0.4rem 0.75rem",
                borderRadius: "6px",
                fontFamily: "var(--font-mono)",
                fontSize: "0.85rem",
              }}
            />
            {data && (
              <span style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
                &rarr; Delivery Date: <strong style={{ color: "var(--text-main)" }}>{data.delivery_date}</strong>
              </span>
            )}
          </div>

          {/* Mode & Band Toggles */}
          <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
            {/* Uncertainty Band Toggle */}
            <label style={{ display: "flex", alignItems: "center", gap: "0.4rem", fontSize: "0.8rem", color: "var(--text-secondary)", cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={includeBand}
                onChange={(e) => setIncludeBand(e.target.checked)}
                style={{ accentColor: "var(--cyan-accent)", cursor: "pointer" }}
              />
              Show 10-90% Empirical Band
            </label>

            {/* Decision Replay vs Outcome Review Mode Toggle */}
            <div className="toggle-wrapper">
              <button
                className={`toggle-btn ${!includeActuals ? "active" : ""}`}
                onClick={() => setIncludeActuals(false)}
                title="Only data available at decision cutoff"
              >
                <EyeOff size={14} style={{ display: "inline", marginRight: "4px" }} />
                Decision Replay
              </button>
              <button
                className={`toggle-btn ${includeActuals ? "active" : ""}`}
                onClick={() => setIncludeActuals(true)}
                title="Overlay realised generation and errors"
              >
                <Eye size={14} style={{ display: "inline", marginRight: "4px" }} />
                Outcome Review
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Replay Notice */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 0.5rem" }}>
        <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
          Showing the wind forecast available at <strong style={{ color: "var(--wind-primary)" }}>{cutoff} UTC</strong> on <strong style={{ color: "var(--text-main)" }}>{decisionDate}</strong>.
          {!includeActuals && " (Replay Mode: Outturn actuals strictly omitted)."}
        </p>
      </div>

      {/* Error state */}
      {error && (
        <div className="error-banner">
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
          <button className="btn btn-outline" onClick={() => setDecisionDate(decisionDate)}>
            Retry
          </button>
        </div>
      )}

      {/* KPI Strip */}
      {data && (
        <div className="kpi-strip">
          <div className="kpi-card">
            <span className="kpi-label">
              <TrendingUp size={14} color="var(--wind-primary)" />
              Peak Forecast
            </span>
            <div className="kpi-value">
              {data.peak_forecast_mw?.toLocaleString() ?? "N/A"}
              <span className="kpi-unit">MW</span>
            </div>
            <span className="kpi-hint">Maximum anticipated delivery</span>
          </div>

          <div className="kpi-card">
            <span className="kpi-label">
              <Wind size={14} color="var(--cyan-accent)" />
              Average Forecast
            </span>
            <div className="kpi-value">
              {data.average_forecast_mw?.toLocaleString() ?? "N/A"}
              <span className="kpi-unit">MW</span>
            </div>
            <span className="kpi-hint">24-hour mean delivery rate</span>
          </div>

          <div className="kpi-card">
            <span className="kpi-label">
              <Zap size={14} color="var(--actual-primary)" />
              Min Forecast
            </span>
            <div className="kpi-value">
              {data.min_forecast_mw?.toLocaleString() ?? "N/A"}
              <span className="kpi-unit">MW</span>
            </div>
            <span className="kpi-hint">Minimum baseload support</span>
          </div>

          <div className="kpi-card">
            <span className="kpi-label">Forecast Age</span>
            <div className="kpi-value" style={{ fontSize: "1.25rem" }}>
              {data.forecast_age_range_minutes ?? "N/A"}
            </div>
            <span className="kpi-hint">Elapsed time before {cutoff} cutoff</span>
          </div>

          <div className="kpi-card">
            <span className="kpi-label">Coverage</span>
            <div className="kpi-value">
              {data.forecast_intervals} / {data.expected_intervals}
              <span className="kpi-unit">hrs</span>
            </div>
            <span className="kpi-hint">100% hourly intervals matched</span>
          </div>
        </div>
      )}

      {/* Uncertainty Band Insufficient History Warning (if applicable) */}
      {data?.uncertainty && !data.uncertainty.has_band && includeBand && (
        <div className="callout-box" style={{ borderColor: "var(--actual-primary)" }}>
          <AlertCircle size={20} color="var(--actual-primary)" style={{ flexShrink: 0 }} />
          <div className="callout-text">
            <strong>Uncertainty Range Unavailable:</strong> {data.uncertainty.reason}.
            Only {data.uncertainty.samples_count} prior matched residual intervals available before {decisionDate} (minimum {data.uncertainty.min_required} required).
          </div>
        </div>
      )}

      {/* Main Chart Card */}
      <div className="card">
        <div className="card-header">
          <div>
            <div className="card-title">
              <Wind size={18} color="var(--wind-primary)" />
              Delivery Day Wind Profile ({data?.delivery_date ?? "D+1"})
            </div>
            <div className="card-subtitle">
              {includeActuals
                ? "Forecast curve vs outturn generation actuals. Positive gap = wind overforecast."
                : "Latest eligible WINDFOR forecasts available at decision cutoff. Missing intervals are never zero-filled."}
            </div>
          </div>

          {/* Chart Legend */}
          <div style={{ display: "flex", alignItems: "center", gap: "1rem", fontSize: "0.8rem" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
              <span style={{ width: 14, height: 3, background: "var(--wind-primary)", borderRadius: 2 }}></span>
              <span>Forecast MW</span>
            </div>
            {includeActuals && (
              <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
                <span style={{ width: 14, height: 3, background: "var(--actual-primary)", borderRadius: 2 }}></span>
                <span>Actual MW</span>
              </div>
            )}
            {includeBand && data?.uncertainty?.has_band && (
              <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
                <span style={{ width: 14, height: 8, background: "rgba(0, 180, 216, 0.25)", border: "1px dashed rgba(0, 180, 216, 0.5)", borderRadius: 2 }}></span>
                <span>10-90% Band</span>
              </div>
            )}
          </div>
        </div>

        {loading ? (
          <div className="skeleton" style={{ height: "360px", width: "100%" }} />
        ) : (
          data && (
            <DecisionChart
              intervals={data.intervals}
              cutoff={cutoff}
              decisionDate={decisionDate}
              includeActuals={includeActuals}
              hasBand={data.uncertainty?.has_band}
            />
          )
        )}
      </div>

      {/* Hourly Interval Detail Table */}
      {data && (
        <div className="card">
          <div className="card-header">
            <div className="card-title">Hourly Interval Breakdown</div>
            <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
              {data.intervals.length} hourly delivery intervals
            </span>
          </div>

          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Delivery Target</th>
                  <th>Selected Publish Time</th>
                  <th>Age @ Cutoff</th>
                  <th>Lead Time</th>
                  <th>Forecast (MW)</th>
                  {includeActuals && <th>Actual (MW)</th>}
                  {includeActuals && <th>Error (MW)</th>}
                  {includeBand && data.uncertainty?.has_band && <th>10-90% Band</th>}
                </tr>
              </thead>
              <tbody>
                {data.intervals.map((item, idx) => (
                  <tr key={idx}>
                    <td className="font-mono">{item.start_time.substring(11, 16)} UTC</td>
                    <td className="font-mono" style={{ color: "var(--text-secondary)" }}>
                      {item.selected_publish_time ? item.selected_publish_time.substring(11, 19) + " UTC" : "—"}
                    </td>
                    <td className="font-mono">{item.forecast_age_minutes !== null ? `${item.forecast_age_minutes}m` : "—"}</td>
                    <td className="font-mono">{item.lead_time_hours !== null ? `${item.lead_time_hours}h` : "—"}</td>
                    <td className="font-mono" style={{ fontWeight: 600, color: "var(--wind-primary)" }}>
                      {item.forecast_mw !== null ? `${Math.round(item.forecast_mw).toLocaleString()} MW` : "Missing"}
                    </td>
                    {includeActuals && (
                      <td className="font-mono" style={{ fontWeight: 600, color: "var(--actual-primary)" }}>
                        {item.actual_mw !== null ? `${Math.round(item.actual_mw).toLocaleString()} MW` : "—"}
                      </td>
                    )}
                    {includeActuals && (
                      <td
                        className="font-mono"
                        style={{
                          fontWeight: 700,
                          color: (item.error_mw || 0) > 0 ? "var(--danger-pos)" : "var(--danger-neg)",
                        }}
                      >
                        {item.error_mw !== null
                          ? `${item.error_mw > 0 ? "+" : ""}${Math.round(item.error_mw).toLocaleString()} MW`
                          : "—"}
                      </td>
                    )}
                    {includeBand && data.uncertainty?.has_band && (
                      <td className="font-mono" style={{ color: "var(--cyan-accent)", fontSize: "0.8rem" }}>
                        {item.lower_mw !== null && item.upper_mw !== null
                          ? `${Math.round(item.lower_mw).toLocaleString()} - ${Math.round(item.upper_mw).toLocaleString()} MW`
                          : "—"}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
