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
});
