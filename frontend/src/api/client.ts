import {
  CutoffComparisonItem,
  DataQualityResponse,
  DecisionProfile,
  Metadata,
  PerformanceResponse,
} from "../types";

const API_BASE = "/api";

export async function fetchMetadata(): Promise<Metadata> {
  const res = await fetch(`${API_BASE}/metadata`);
  if (!res.ok) {
    throw new Error(`Failed to fetch metadata (HTTP ${res.status})`);
  }
  return res.json();
}

export async function fetchDecisionProfile(
  decisionDate: string,
  cutoff: string,
  includeActuals: boolean = false,
  includeBand: boolean = true
): Promise<DecisionProfile> {
  const params = new URLSearchParams({
    decision_date: decisionDate,
    cutoff: cutoff,
    include_actuals: String(includeActuals),
    include_band: String(includeBand),
  });

  const res = await fetch(`${API_BASE}/decision-profile?${params.toString()}`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch decision profile (HTTP ${res.status})`);
  }
  return res.json();
}

export async function fetchPerformance(
  cutoff: string,
  startDate: string = "2026-01-01",
  endDate: string = "2026-01-31"
): Promise<PerformanceResponse> {
  const params = new URLSearchParams({
    cutoff: cutoff,
    start_date: startDate,
    end_date: endDate,
  });

  const res = await fetch(`${API_BASE}/performance?${params.toString()}`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch performance summary (HTTP ${res.status})`);
  }
  return res.json();
}

export async function fetchPerformanceCompare(
  cutoffs: string[],
  startDate: string = "2026-01-01",
  endDate: string = "2026-01-31"
): Promise<CutoffComparisonItem[]> {
  const params = new URLSearchParams({
    cutoffs: cutoffs.join(","),
    start_date: startDate,
    end_date: endDate,
  });

  const res = await fetch(`${API_BASE}/performance/compare?${params.toString()}`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch cutoff comparison (HTTP ${res.status})`);
  }
  return res.json();
}

export async function fetchDataQuality(
  cutoff: string,
  startDate: string = "2026-01-01",
  endDate: string = "2026-01-31"
): Promise<DataQualityResponse> {
  const params = new URLSearchParams({
    cutoff: cutoff,
    start_date: startDate,
    end_date: endDate,
  });

  const res = await fetch(`${API_BASE}/data-quality?${params.toString()}`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch data quality audit (HTTP ${res.status})`);
  }
  return res.json();
}

export function getExportUrl(
  cutoff: string,
  startDate: string = "2026-01-01",
  endDate: string = "2026-01-31"
): string {
  const params = new URLSearchParams({
    cutoff: cutoff,
    start_date: startDate,
    end_date: endDate,
  });
  return `${API_BASE}/export?${params.toString()}`;
}
