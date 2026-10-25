import React, { useState } from "react";

interface HeatmapCellData {
  deliveryDate: string;
  hour: number;
  forecastMw: number | null;
  actualMw: number | null;
  errorMw: number | null;
}

interface ErrorHeatmapProps {
  data: HeatmapCellData[];
}

export const ErrorHeatmap: React.FC<ErrorHeatmapProps> = ({ data }) => {
  const [hoveredCell, setHoveredCell] = useState<HeatmapCellData | null>(null);

  if (!data || data.length === 0) {
    return <div style={{ color: "var(--text-muted)", padding: "1rem" }}>No error data available for heatmap.</div>;
  }

  // Group by delivery date
  const deliveryDates = Array.from(new Set(data.map((d) => d.deliveryDate))).sort();
  const hours = Array.from({ length: 24 }, (_, i) => i);

  // Index map for quick lookup: `${date}_${hour}`
  const lookup = new Map<string, HeatmapCellData>();
  data.forEach((d) => {
    lookup.set(`${d.deliveryDate}_${d.hour}`, d);
  });

  // Find max absolute error for normalization
  let maxAbsErr = 1000;
  data.forEach((d) => {
    if (d.errorMw !== null) {
      const a = Math.abs(d.errorMw);
      if (a > maxAbsErr) maxAbsErr = a;
    }
  });

  const getCellColor = (error: number | null) => {
    if (error === null) return "rgba(255, 255, 255, 0.04)";
    const intensity = Math.min(Math.abs(error) / maxAbsErr, 1.0);
    const alpha = 0.15 + intensity * 0.75;
    if (error > 0) {
      // Overforecast: red / orange
      return `rgba(239, 71, 111, ${alpha.toFixed(2)})`;
    } else if (error < 0) {
      // Underforecast: blue / cyan
      return `rgba(0, 180, 216, ${alpha.toFixed(2)})`;
    }
    return "rgba(255, 255, 255, 0.1)";
  };

  return (
    <div style={{ position: "relative" }}>
      {/* Legend */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.75rem", fontSize: "0.75rem", color: "var(--text-secondary)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
            <span style={{ width: 12, height: 12, borderRadius: 2, background: "rgba(0, 180, 216, 0.85)" }}></span>
            <span>Underforecast (&lt; 0 MW)</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
            <span style={{ width: 12, height: 12, borderRadius: 2, background: "rgba(239, 71, 111, 0.85)" }}></span>
            <span>Overforecast (&gt; 0 MW)</span>
          </div>
        </div>
        <span style={{ fontFamily: "var(--font-mono)" }}>Max Observed |Error|: &plusmn;{Math.round(maxAbsErr).toLocaleString()} MW</span>
      </div>

      <div className="heatmap-container">
        {/* Hour Header */}
        <div className="heatmap-row" style={{ marginBottom: "4px" }}>
          <div className="heatmap-date-label" style={{ fontWeight: 600 }}>Delivery Date</div>
          {hours.map((h) => (
            <div
              key={h}
              className="heatmap-cell"
              style={{ background: "transparent", color: "var(--text-muted)", fontSize: "0.65rem", fontFamily: "var(--font-mono)" }}
            >
              {h}h
            </div>
          ))}
        </div>

        {/* Date Rows */}
        {deliveryDates.map((delivDate) => (
          <div key={delivDate} className="heatmap-row">
            <div className="heatmap-date-label">{delivDate.substring(5)}</div>
            {hours.map((h) => {
              const item = lookup.get(`${delivDate}_${h}`);
              const err = item?.errorMw ?? null;
              const color = getCellColor(err);

              return (
                <div
                  key={h}
                  className="heatmap-cell"
                  style={{ background: color }}
                  onMouseEnter={() => setHoveredCell(item || null)}
                  onMouseLeave={() => setHoveredCell(null)}
                />
              );
            })}
          </div>
        ))}
      </div>

      {/* Hover Tooltip */}
      {hoveredCell && (
        <div
          style={{
            position: "fixed",
            bottom: "2rem",
            right: "2rem",
            background: "rgba(14, 21, 36, 0.95)",
            border: "1px solid var(--border-strong)",
            borderRadius: "8px",
            padding: "0.75rem 1rem",
            fontSize: "0.8rem",
            color: "var(--text-main)",
            boxShadow: "0 8px 24px rgba(0, 0, 0, 0.6)",
            zIndex: 100,
            pointerEvents: "none",
            minWidth: "220px",
          }}
        >
          <div style={{ fontWeight: 600, color: "var(--cyan-accent)", marginBottom: "0.25rem", fontFamily: "var(--font-mono)" }}>
            {hoveredCell.deliveryDate} @ {String(hoveredCell.hour).padStart(2, "0")}:00 UTC
          </div>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <span style={{ color: "var(--text-secondary)" }}>Forecast:</span>
            <span style={{ fontFamily: "var(--font-mono)" }}>
              {hoveredCell.forecastMw !== null ? `${Math.round(hoveredCell.forecastMw).toLocaleString()} MW` : "N/A"}
            </span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <span style={{ color: "var(--text-secondary)" }}>Actual:</span>
            <span style={{ fontFamily: "var(--font-mono)" }}>
              {hoveredCell.actualMw !== null ? `${Math.round(hoveredCell.actualMw).toLocaleString()} MW` : "N/A"}
            </span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", marginTop: "0.25rem", borderTop: "1px solid var(--border-subtle)", paddingTop: "0.25rem" }}>
            <span style={{ color: "var(--text-secondary)" }}>Error:</span>
            <span
              style={{
                fontFamily: "var(--font-mono)",
                fontWeight: 700,
                color: (hoveredCell.errorMw || 0) > 0 ? "var(--danger-pos)" : "var(--danger-neg)",
              }}
            >
              {(hoveredCell.errorMw || 0) > 0 ? "+" : ""}
              {hoveredCell.errorMw !== null ? `${Math.round(hoveredCell.errorMw).toLocaleString()} MW` : "N/A"}
            </span>
          </div>
        </div>
      )}
    </div>
  );
};
