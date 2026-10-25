import React, { useState } from "react";
import { Clock, Info } from "lucide-react";
import { Preset } from "../types";

interface ControlBarProps {
  presets: Preset[];
  currentCutoff: string;
  onCutoffChange: (newCutoff: string) => void;
  disclaimer: string;
}

export const ControlBar: React.FC<ControlBarProps> = ({
  presets,
  currentCutoff,
  onCutoffChange,
  disclaimer,
}) => {
  const [customValue, setCustomValue] = useState(currentCutoff);

  const handleCustomBlur = () => {
    if (/^([01]\d|2[0-3]):([0-5]\d)$/.test(customValue)) {
      onCutoffChange(customValue);
    } else {
      setCustomValue(currentCutoff);
    }
  };

  const handleCustomKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      handleCustomBlur();
    }
  };

  return (
    <div className="control-bar">
      <div className="control-group">
        <span className="control-label">
          <Clock size={16} color="var(--wind-primary)" />
          Decision Cutoff Gate:
        </span>

        <div className="cutoff-selector">
          {presets.map((preset) => {
            const isActive = currentCutoff === preset.cutoff_time;
            return (
              <button
                key={preset.id}
                className={`preset-chip ${isActive ? "active" : ""}`}
                onClick={() => {
                  setCustomValue(preset.cutoff_time);
                  onCutoffChange(preset.cutoff_time);
                }}
                title={preset.description}
              >
                {preset.name.split(" ")[0]} ({preset.cutoff_time})
              </button>
            );
          })}

          <div style={{ display: "flex", alignItems: "center", gap: "0.25rem", marginLeft: "0.5rem" }}>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Custom:</span>
            <input
              type="text"
              className="custom-time-input"
              value={customValue}
              onChange={(e) => setCustomValue(e.target.value)}
              onBlur={handleCustomBlur}
              onKeyDown={handleCustomKeyDown}
              placeholder="09:20"
              maxLength={5}
            />
          </div>
        </div>

        <div className="info-tooltip-container">
          <Info size={16} color="var(--text-muted)" />
          <div className="tooltip-popup">
            <strong>Auction Gate Closure Disclaimer:</strong>
            <p style={{ marginTop: "0.25rem" }}>{disclaimer}</p>
          </div>
        </div>
      </div>

      <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
        Active Rule: <span style={{ color: "var(--wind-primary)", fontWeight: 600 }}>publishTime &le; {currentCutoff} UTC</span>
      </div>
    </div>
  );
};
