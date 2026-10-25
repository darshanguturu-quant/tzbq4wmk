import React, { useState } from "react";
import { DecisionInterval } from "../types";

interface DecisionChartProps {
  intervals: DecisionInterval[];
  cutoff: string;
  decisionDate: string;
  includeActuals: boolean;
  hasBand?: boolean;
}

export const DecisionChart: React.FC<DecisionChartProps> = ({
  intervals,
  cutoff,
  decisionDate,
  includeActuals,
  hasBand,
}) => {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  if (!intervals || intervals.length === 0) {
    return (
      <div style={{ padding: "4rem 2rem", textAlign: "center", color: "var(--text-muted)" }}>
        No delivery intervals available for the selected date.
      </div>
    );
  }

  // Dimensions
  const svgWidth = 960;
  const svgHeight = 360;
  const padding = { top: 30, right: 40, bottom: 40, left: 65 };

  const plotWidth = svgWidth - padding.left - padding.right;
  const plotHeight = svgHeight - padding.top - padding.bottom;

  // Compute maximum MW for scale
  let maxMw = 1000;
  intervals.forEach((item) => {
    if (item.forecast_mw && item.forecast_mw > maxMw) maxMw = item.forecast_mw;
    if (includeActuals && item.actual_mw && item.actual_mw > maxMw) maxMw = item.actual_mw;
    if (hasBand && item.upper_mw && item.upper_mw > maxMw) maxMw = item.upper_mw;
  });
  maxMw = Math.ceil(maxMw / 2000) * 2000;

  // Coordinate mappers
  const getX = (index: number) => {
    return padding.left + (index / (intervals.length - 1)) * plotWidth;
  };

  const getY = (val: number | null | undefined) => {
    if (val === null || val === undefined || isNaN(val)) return plotHeight + padding.top;
    return padding.top + plotHeight - (val / maxMw) * plotHeight;
  };

  // Build forecast line path
  const forecastPoints = intervals
    .map((item, idx) => (item.forecast_mw !== null ? `${getX(idx)},${getY(item.forecast_mw)}` : null))
    .filter(Boolean);
  const forecastPath = forecastPoints.length > 0 ? `M ${forecastPoints.join(" L ")}` : "";

  // Build actuals line path
  const actualPoints = includeActuals
    ? intervals
        .map((item, idx) => (item.actual_mw !== null ? `${getX(idx)},${getY(item.actual_mw)}` : null))
        .filter(Boolean)
    : [];
  const actualsPath = actualPoints.length > 0 ? `M ${actualPoints.join(" L ")}` : "";

  // Build uncertainty band polygon path (forward along upper, backward along lower)
  let bandPath = "";
  if (hasBand) {
    const upperPoints: string[] = [];
    const lowerPoints: string[] = [];
    intervals.forEach((item, idx) => {
      if (item.upper_mw !== null && item.lower_mw !== null) {
        upperPoints.push(`${getX(idx)},${getY(item.upper_mw)}`);
        lowerPoints.push(`${getX(idx)},${getY(item.lower_mw)}`);
      }
    });
    if (upperPoints.length > 0) {
      bandPath = `M ${upperPoints.join(" L ")} L ${lowerPoints.reverse().join(" L ")} Z`;
    }
  }

  // Grid ticks
  const yTicks = [0, maxMw * 0.25, maxMw * 0.5, maxMw * 0.75, maxMw];

  const activeItem = hoverIndex !== null ? intervals[hoverIndex] : null;

  return (
    <div style={{ position: "relative", width: "100%", overflowX: "auto" }}>
      <svg
        viewBox={`0 0 ${svgWidth} ${svgHeight}`}
        style={{ width: "100%", height: "auto", display: "block" }}
      >
        <defs>
          <linearGradient id="forecastAreaGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#00D26A" stopOpacity="0.25" />
            <stop offset="100%" stopColor="#00D26A" stopOpacity="0.0" />
          </linearGradient>
          <linearGradient id="bandAreaGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#00B4D8" stopOpacity="0.18" />
            <stop offset="100%" stopColor="#00B4D8" stopOpacity="0.05" />
          </linearGradient>
        </defs>

        {/* Y Grid & Axis labels */}
        {yTicks.map((val, i) => {
          const y = getY(val);
          return (
            <g key={i}>
              <line
                x1={padding.left}
                y1={y}
                x2={padding.left + plotWidth}
                y2={y}
                stroke="rgba(255, 255, 255, 0.07)"
                strokeDasharray="4 4"
              />
              <text
                x={padding.left - 10}
                y={y + 4}
                textAnchor="end"
                fontSize="11"
                fill="var(--text-muted)"
                fontFamily="var(--font-mono)"
              >
                {Math.round(val).toLocaleString()} MW
              </text>
            </g>
          );
        })}

        {/* X Axis ticks */}
        {intervals.map((item, idx) => {
          // Show label every 3 hours (00:00, 03:00, 06:00...)
          if (idx % 3 !== 0 && idx !== intervals.length - 1) return null;
          const x = getX(idx);
          const timeLabel = item.start_time.substring(11, 16);
          return (
            <g key={idx}>
              <line
                x1={x}
                y1={padding.top + plotHeight}
                x2={x}
                y2={padding.top + plotHeight + 6}
                stroke="rgba(255, 255, 255, 0.2)"
              />
              <text
                x={x}
                y={padding.top + plotHeight + 20}
                textAnchor="middle"
                fontSize="11"
                fill="var(--text-secondary)"
                fontFamily="var(--font-mono)"
              >
                {timeLabel}
              </text>
            </g>
          );
        })}

        {/* Uncertainty Band */}
        {hasBand && bandPath && (
          <path d={bandPath} fill="url(#bandAreaGrad)" stroke="rgba(0, 180, 216, 0.3)" strokeDasharray="3 3" />
        )}

        {/* Forecast Line */}
        {forecastPath && (
          <>
            <path
              d={`${forecastPath} L ${getX(intervals.length - 1)},${getY(0)} L ${getX(0)},${getY(0)} Z`}
              fill="url(#forecastAreaGrad)"
            />
            <path
              d={forecastPath}
              fill="none"
              stroke="var(--wind-primary)"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </>
        )}

        {/* Actuals Line (Outcome mode) */}
        {includeActuals && actualsPath && (
          <path
            d={actualsPath}
            fill="none"
            stroke="var(--actual-primary)"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        )}

        {/* Interactive Hover Vertical Line */}
        {hoverIndex !== null && (
          <line
            x1={getX(hoverIndex)}
            y1={padding.top}
            x2={getX(hoverIndex)}
            y2={padding.top + plotHeight}
            stroke="rgba(255, 255, 255, 0.4)"
            strokeDasharray="2 2"
          />
        )}

        {/* Data Points */}
        {intervals.map((item, idx) => {
          const x = getX(idx);
          const isHovered = hoverIndex === idx;

          return (
            <g key={idx}>
              {/* Forecast Point */}
              {item.forecast_mw !== null && (
                <circle
                  cx={x}
                  cy={getY(item.forecast_mw)}
                  r={isHovered ? 6 : 3.5}
                  fill="var(--wind-primary)"
                  stroke="#080C14"
                  strokeWidth="2"
                  style={{ transition: "all 0.15s ease" }}
                />
              )}

              {/* Actual Point */}
              {includeActuals && item.actual_mw !== null && (
                <circle
                  cx={x}
                  cy={getY(item.actual_mw)}
                  r={isHovered ? 6 : 3.5}
                  fill="var(--actual-primary)"
                  stroke="#080C14"
                  strokeWidth="2"
                  style={{ transition: "all 0.15s ease" }}
                />
              )}

              {/* Invisible full-height hit area for mouse hover */}
              <rect
                x={x - (plotWidth / intervals.length) / 2}
                y={padding.top}
                width={plotWidth / intervals.length}
                height={plotHeight}
                fill="transparent"
                onMouseEnter={() => setHoverIndex(idx)}
                onMouseLeave={() => setHoverIndex(null)}
                style={{ cursor: "pointer" }}
              />
            </g>
          );
        })}
      </svg>

      {/* Floating Rich Tooltip */}
      {activeItem && hoverIndex !== null && (
        <div
          style={{
            position: "absolute",
            top: "16px",
            left: `${Math.min(Math.max(getX(hoverIndex) - 130, 20), svgWidth - 280)}px`,
            background: "rgba(14, 21, 36, 0.95)",
            backdropFilter: "blur(8px)",
            border: "1px solid var(--border-strong)",
            borderRadius: "8px",
            padding: "0.75rem 1rem",
            fontSize: "0.8rem",
            color: "var(--text-main)",
            boxShadow: "0 8px 24px rgba(0, 0, 0, 0.6)",
            pointerEvents: "none",
            zIndex: 30,
            minWidth: "250px",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "0.35rem", marginBottom: "0.5rem" }}>
            <span style={{ fontWeight: 600, color: "var(--cyan-accent)", fontFamily: "var(--font-mono)" }}>
              {activeItem.start_time.substring(11, 16)} UTC (Target)
            </span>
            <span style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>
              Decision: {decisionDate} @ {cutoff}
            </span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "0.3rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--text-secondary)" }}>Selected Forecast:</span>
              <span style={{ fontWeight: 700, color: "var(--wind-primary)", fontFamily: "var(--font-mono)" }}>
                {activeItem.forecast_mw !== null ? `${Math.round(activeItem.forecast_mw).toLocaleString()} MW` : "Missing"}
              </span>
            </div>

            {includeActuals && activeItem.actual_mw !== null && (
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-secondary)" }}>Settlement Actual:</span>
                <span style={{ fontWeight: 700, color: "var(--actual-primary)", fontFamily: "var(--font-mono)" }}>
                  {Math.round(activeItem.actual_mw).toLocaleString()} MW
                </span>
              </div>
            )}

            {includeActuals && activeItem.error_mw !== null && (
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-secondary)" }}>Error (Fc - Act):</span>
                <span
                  style={{
                    fontWeight: 700,
                    fontFamily: "var(--font-mono)",
                    color: activeItem.error_mw > 0 ? "var(--danger-pos)" : "var(--danger-neg)",
                  }}
                >
                  {activeItem.error_mw > 0 ? "+" : ""}
                  {Math.round(activeItem.error_mw).toLocaleString()} MW
                  <span style={{ fontSize: "0.7rem", fontWeight: 400, marginLeft: "4px" }}>
                    ({activeItem.error_mw > 0 ? "Overforecast" : "Underforecast"})
                  </span>
                </span>
              </div>
            )}

            {hasBand && activeItem.lower_mw !== null && activeItem.upper_mw !== null && (
              <div style={{ display: "flex", justifyContent: "space-between", borderTop: "1px dashed var(--border-subtle)", paddingTop: "0.25rem" }}>
                <span style={{ color: "var(--cyan-accent)", fontSize: "0.75rem" }}>10-90% Resid Band:</span>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem" }}>
                  {Math.round(activeItem.lower_mw).toLocaleString()} - {Math.round(activeItem.upper_mw).toLocaleString()} MW
                </span>
              </div>
            )}

            <div style={{ borderTop: "1px solid var(--border-subtle)", marginTop: "0.25rem", paddingTop: "0.25rem", fontSize: "0.7rem", color: "var(--text-muted)" }}>
              <div>Published: {activeItem.selected_publish_time ? activeItem.selected_publish_time.substring(11, 19) + " UTC" : "N/A"}</div>
              <div>Age at Cutoff: {activeItem.forecast_age_minutes !== null ? `${activeItem.forecast_age_minutes} mins` : "N/A"} (Lead: {activeItem.lead_time_hours}h)</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
