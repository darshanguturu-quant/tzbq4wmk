import React, { useEffect, useState } from "react";
import { Activity, BarChart2, FileCheck, Wind } from "lucide-react";
import { fetchMetadata } from "./api/client";
import { ControlBar } from "./components/ControlBar";
import { DecisionReplayPage } from "./pages/DecisionReplayPage";
import { EvidencePage } from "./pages/EvidencePage";
import { PerformancePage } from "./pages/PerformancePage";
import { Metadata, Preset } from "./types";

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"replay" | "performance" | "evidence">("replay");
  const [currentCutoff, setCurrentCutoff] = useState<string>("09:20");
  const [metadata, setMetadata] = useState<Metadata | null>(null);

  useEffect(() => {
    fetchMetadata()
      .then((meta) => {
        setMetadata(meta);
        if (meta.default_cutoff) {
          setCurrentCutoff(meta.default_cutoff);
        }
      })
      .catch((err) => {
        console.error("Failed to load initial metadata", err);
      });
  }, []);

  const presets: Preset[] = metadata?.cutoff_presets ?? [
    { id: "epex_hourly", name: "EPEX GB Hourly", cutoff_time: "09:20", description: "EPEX Day-Ahead Hourly" },
    { id: "n2ex", name: "N2EX Day-Ahead", cutoff_time: "09:50", description: "Nord Pool Day-Ahead" },
    { id: "epex_half_hourly", name: "EPEX Half-Hourly", cutoff_time: "15:30", description: "EPEX Day-Ahead Half-Hourly" },
  ];

  const disclaimer =
    metadata?.disclaimers?.cutoff ??
    "Illustrative GB auction gate closure. Confirm your organisation's actual internal trading deadline.";

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="brand-section">
          <div className="brand-logo">
            <Wind size={22} />
          </div>
          <div>
            <div className="brand-title">REint Forecast Portal</div>
            <div className="brand-subtitle">GB Day-Ahead Market Trading Intelligence</div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="nav-tabs">
          <button
            className={`nav-tab-btn ${activeTab === "replay" ? "active" : ""}`}
            onClick={() => setActiveTab("replay")}
          >
            <Activity size={16} />
            Decision Replay
          </button>
          <button
            className={`nav-tab-btn ${activeTab === "performance" ? "active" : ""}`}
            onClick={() => setActiveTab("performance")}
          >
            <BarChart2 size={16} />
            Forecast Performance
          </button>
          <button
            className={`nav-tab-btn ${activeTab === "evidence" ? "active" : ""}`}
            onClick={() => setActiveTab("evidence")}
          >
            <FileCheck size={16} />
            Evidence &amp; Audit
          </button>
        </nav>

        {/* Status Pill */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.8rem", color: "var(--text-secondary)" }}>
          <span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--wind-primary)", boxShadow: "0 0 8px var(--wind-primary)" }}></span>
          <span>January 2026 Live Snapshot</span>
        </div>
      </header>

      {/* Persistent Control Bar */}
      <ControlBar
        presets={presets}
        currentCutoff={currentCutoff}
        onCutoffChange={(newCutoff) => setCurrentCutoff(newCutoff)}
        disclaimer={disclaimer}
      />

      {/* Page Content */}
      <main className="main-content">
        {activeTab === "replay" && <DecisionReplayPage cutoff={currentCutoff} />}
        {activeTab === "performance" && <PerformancePage cutoff={currentCutoff} />}
        {activeTab === "evidence" && <EvidencePage cutoff={currentCutoff} />}
      </main>

      {/* Footer */}
      <footer style={{ borderTop: "1px solid var(--border-subtle)", padding: "1.25rem 2rem", background: "var(--bg-surface)", fontSize: "0.75rem", color: "var(--text-muted)", display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", gap: "1rem" }}>
        <div>
          <strong>REint Full Stack SWE Challenge</strong> &bull; Elexon BMRS National Wind Generation &bull; January 2026 Decision Scope
        </div>
        <div>
          Data is frozen in snapshot.sqlite &bull; Strictly leak-free decision cutoffs &bull; Zero synthetic zero-filling
        </div>
      </footer>
    </div>
  );
};
