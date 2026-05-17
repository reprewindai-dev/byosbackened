import { useEffect, useCallback } from "react";
import { Play, Pause, Plus } from "lucide-react";
import { api } from "@/lib/api";

const PIPELINES = [
  { id: "patient-intake", name: "Patient Intake", description: "PHI redaction → triage model → audit", status: "RUNNING", runs: 1240, lastRun: "2m ago", avgLatency: "276ms" },
  { id: "code-review", name: "Code Review", description: "Static analysis → DeepSeek → PR comment", status: "RUNNING", runs: 340, lastRun: "5m ago", avgLatency: "1.2s" },
  { id: "rag-ingest", name: "RAG Ingest", description: "Chunking → BGE-M3 embed → vector store", status: "RUNNING", runs: 8420, lastRun: "12s ago", avgLatency: "88ms" },
  { id: "compliance-scan", name: "Compliance Scan", description: "Evidence collection → SOC2 controls → sign", status: "PAUSED", runs: 42, lastRun: "1h ago", avgLatency: "4.2s" },
  { id: "cost-report", name: "Cost Report", description: "Wallet aggregation → team allocation → PDF", status: "RUNNING", runs: 24, lastRun: "6h ago", avgLatency: "2.1s" },
];

export function PipelinesPage() {
  const fetchData = useCallback(async () => {
    try {
      await api.get("/pipelines");
    } catch { /* use static fallback */ }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-start justify-between">
        <div>
          <p className="v-section-label">Infrastructure · Pipelines</p>
          <h1 className="mt-1 text-2xl font-bold text-bone">Pipelines</h1>
          <p className="mt-1 text-sm text-muted">Orchestrated multi-step AI workflows with policy enforcement at every stage.</p>
        </div>
        <button className="v-btn-primary text-xs"><Plus className="h-3.5 w-3.5" /> New pipeline</button>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <div className="v-card">
          <p className="v-section-label">Active Pipelines</p>
          <p className="mt-1 text-2xl font-bold text-bone">{PIPELINES.filter(p => p.status === "RUNNING").length}</p>
        </div>
        <div className="v-card">
          <p className="v-section-label">Total Runs Today</p>
          <p className="mt-1 text-2xl font-bold text-bone">{PIPELINES.reduce((s, p) => s + p.runs, 0).toLocaleString()}</p>
        </div>
        <div className="v-card">
          <p className="v-section-label">Paused</p>
          <p className="mt-1 text-2xl font-bold text-amber">{PIPELINES.filter(p => p.status === "PAUSED").length}</p>
        </div>
      </div>

      <div className="space-y-3">
        {PIPELINES.map((pipeline) => (
          <div key={pipeline.id} className="v-card-flush flex items-center gap-4 px-4 py-3">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-medium text-sm text-bone">{pipeline.name}</span>
                <span className={`v-badge ${pipeline.status === "RUNNING" ? "v-badge-green" : "v-badge-muted"}`}>{pipeline.status}</span>
              </div>
              <p className="mt-0.5 text-[11px] text-muted">{pipeline.description}</p>
            </div>
            <div className="hidden md:flex items-center gap-6 text-xs">
              <div className="text-center"><p className="v-section-label">Runs</p><p className="font-mono text-bone">{pipeline.runs.toLocaleString()}</p></div>
              <div className="text-center"><p className="v-section-label">Last Run</p><p className="font-mono text-bone">{pipeline.lastRun}</p></div>
              <div className="text-center"><p className="v-section-label">Avg Latency</p><p className="font-mono text-bone">{pipeline.avgLatency}</p></div>
            </div>
            <div className="flex gap-2">
              {pipeline.status === "RUNNING" ? (
                <button className="v-btn-ghost text-xs"><Pause className="h-3 w-3" /> Pause</button>
              ) : (
                <button className="v-btn-primary text-xs"><Play className="h-3 w-3" /> Resume</button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
