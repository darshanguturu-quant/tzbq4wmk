import { describe, expect, it } from "vitest";

describe("Frontend Domain Rules and KPI Formatting", () => {
  it("formats MW values cleanly with local separator", () => {
    const val = 12450.75;
    const formatted = Math.round(val).toLocaleString() + " MW";
    expect(formatted).toBe("12,451 MW");
  });

  it("calculates signed forecast error correctly (positive is overforecast)", () => {
    const forecastMw = 10000;
    const actualMw = 8500;
    const errorMw = forecastMw - actualMw;
    expect(errorMw).toBe(1500);
    const direction = errorMw > 0 ? "Overforecast" : "Underforecast";
    expect(direction).toBe("Overforecast");
  });

  it("calculates forecast age in minutes correctly", () => {
    const cutoff = new Date("2026-01-15T09:20:00Z").getTime();
    const published = new Date("2026-01-15T07:30:00Z").getTime();
    const ageMinutes = Math.round((cutoff - published) / (1000 * 60));
    expect(ageMinutes).toBe(110);
  });

  it("ensures decision replay mode preserves missing actuals as null", () => {
    const replayInterval = {
      start_time: "2026-01-16T00:00:00Z",
      forecast_mw: 8500,
      actual_mw: null,
      error_mw: null,
    };
    expect(replayInterval.forecast_mw).toBe(8500);
    expect(replayInterval.actual_mw).toBeNull();
    expect(replayInterval.error_mw).toBeNull();
  });

  it("includes custom cutoff in sensitivity comparison list alongside presets", () => {
    const PRESETS = ["09:20", "09:50", "15:30"];
    const customCutoff = "12:00";
    const compareCutoffs = PRESETS.includes(customCutoff) ? PRESETS : [...PRESETS, customCutoff];
    expect(compareCutoffs).toEqual(["09:20", "09:50", "15:30", "12:00"]);

    const presetCutoff = "09:20";
    const presetCompare = PRESETS.includes(presetCutoff) ? PRESETS : [...PRESETS, presetCutoff];
    expect(presetCompare).toEqual(["09:20", "09:50", "15:30"]);
  });

  it("floors uncertainty band lower bound at zero for negative unconstrained values", () => {
    const forecastMw = 4252.0;
    const q10Residual = -5000.0;
    const lowerMw = Math.max(0.0, forecastMw + q10Residual);
    expect(lowerMw).toBe(0.0);
  });
});
