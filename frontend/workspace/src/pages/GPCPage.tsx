import { useEffect, useState, useCallback } from "react";
import { Shield, Zap, GitBranch, Lock, Activity, Settings, ChevronRight, CheckCircle, AlertCircle, Clock } from "lucide-react";
import { api } from "@/lib/api";

const OPERATORS = [
  { id: "phi-redact", name: "PHI Redaction", category: "Privacy", status: "ACTIVE", version: "v2.4.1", latency: "< 1ms", hits: "18,420", description: "Redacts PHI/PII before any model sees the prompt" },
  { id: "policy-gate", name: "Policy Gate", category: "Governance", status: "ACTIVE", version: "v3.1.0", latency: "< 1ms", hits: "184,200", description: "Evaluates outbound policy rules before execution" },
  { id: "route-select", name: "Route Selector", category: "Routing", status: "ACTIVE", version: "v1.8.2", latency: "< 1ms", hits: "184,200", description: "Selects optimal zone based on cost, latency, policy" },
  { id: "audit-sign", name: "Audit Signer", category: "Compliance", status: "ACTIVE", version: "v2.0.0", latency: "< 2ms", hits: "184,200", description: "Appends tamper-evident SHA-256 hash to every log entry" },
  { id: "budget-guard", name: "Budget Guard", category: "Finance", status: "ACTIVE", version: "v1.2.3", latency: "< 1ms", hits: "184,200", description: "Enforces per-team and org-level spend caps" },
  { id: "content-safety", name: "Content Safety", category: "Safety", status: "ACTIVE", version: "v1.5.0", latency: "3ms", hits: "184,200", description: "Scans output for policy violations before delivery" },
];

const PIPELINE_STAGES = [
  { id: "inbound", label: "Inbound", icon: Shield, ops: ["PHI Redaction", "Policy Gate"] },
  { id: "routing", label: "Routing", icon: GitBranch, ops: ["Route Selector", "Budget Guard"] },
  { id: "exec", label: "Execution", icon: Zap, ops: ["Model Inference", "SSE Stream"] },
  { id: "outbound", label: "Outbound", icon: Lock, ops: ["Content Safety", "Audit Signer"] },
];

const UACP_VERSIONS = [
  { version: "v4", label: "Quantum-Classical Hybrid", status: "ACTIVE", description: "Full UACP with quantum co-processor routing", features: ["Quantum gate scheduling", "Classical fallback", "Sub-ms handoff"] },
  { version: "v3", label: "Autonomous Orchestration", status: "STABLE", description: "Multi-agent orchestration with policy enforcement", features: ["Agent mesh", "Policy-aware routing", "Evidence collection"] },
  { version: "v2", label: "Deterministic Routing", status: "STABLE", description: "Rule-based deterministic routing engine", features: ["Static rules", "Cost optimization", "Zone selection"] },
  { version: "v1", label: "Basic Gateway", status: "LEGACY", description: "Original gateway with basic policy support", features: ["HTTP proxy", "Basic auth", "Request logging"] },
];

export function GPCPage() {
  const [connected, setConnected] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      await api.get("/internal/uacp/status");
      setConnected(true);
    } catch { /* use static data */ }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-start justify-between">
        <div>
          <p className="v-section-label">GPC · Global Policy Control</p>
          <h1 className="mt-1 text-2xl font-bold text-bone">Universal AI Control Plane</h1>
          <p className="mt-1 text-sm text-muted">
            Every prompt passes through the GPC pipeline — redaction, policy, routing, execution, audit — before any model sees it.
          </p>
          <div className="mt-3 flex gap-2">
            {connected && <span className="v-badge-green">● Backend Connected</span>}
            <span className="v-badge-muted">UACP v4 Active</span>
            <span className="v-badge-muted">6 Operators Live</span>
          </div>
        </div>
        <button className="v-btn-ghost text-xs"><Settings className="h-3.5 w-3.5" /> Configure</button>
      </div>

      {/* Pipeline visualization */}
      <div className="v-card">
        <p className="v-section-label">Pipeline · Request Flow</p>
        <p className="mt-0.5 text-sm font-semibold text-bone">Every request traverses all 4 stages in sequence</p>
        <div className="mt-4 flex items-center gap-2 overflow-x-auto pb-2">
          {PIPELINE_STAGES.map((stage, i) => (
            <div key={stage.id} className="flex items-center gap-2">
              <div className="flex-shrink-0 rounded-lg border border-rule bg-ink-3/50 p-3 min-w-[140px]">
                <div className="flex items-center gap-2 mb-2">
                  <stage.icon className="h-4 w-4 text-amber" />
                  <span className="text-xs font-semibold text-bone">{stage.label}</span>
                </div>
                {stage.ops.map(op => (
                  <div key={op} className="flex items-center gap-1.5 text-[10px] text-muted mb-1">
                    <CheckCircle className="h-2.5 w-2.5 text-moss flex-shrink-0" />
                    {op}
                  </div>
                ))}
              </div>
              {i < PIPELINE_STAGES.length - 1 && (
                <ChevronRight className="h-4 w-4 text-muted flex-shrink-0" />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Operators grid */}
      <div>
        <p className="v-section-label mb-3">Operators · Live</p>
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {OPERATORS.map((op) => (
            <div key={op.id} className="v-card">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-bone">{op.name}</span>
                    <span className="v-badge-green">● {op.status}</span>
                  </div>
                  <p className="mt-0.5 text-[10px] text-muted">{op.category} · {op.version}</p>
                </div>
                <Activity className="h-3.5 w-3.5 text-muted" />
              </div>
              <p className="mt-2 text-xs text-muted">{op.description}</p>
              <div className="mt-3 flex justify-between text-[10px] font-mono">
                <span className="text-muted">Latency: <span className="text-bone">{op.latency}</span></span>
                <span className="text-muted">Hits: <span className="text-bone">{op.hits}</span></span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* UACP versions */}
      <div>
        <p className="v-section-label mb-3">UACP · Version History</p>
        <div className="grid gap-3 md:grid-cols-2">
          {UACP_VERSIONS.map((v) => (
            <div key={v.version} className={`v-card ${v.status === "ACTIVE" ? "border-amber/30" : ""}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm font-bold text-bone">{v.version}</span>
                  <span className="text-xs text-muted">{v.label}</span>
                </div>
                <span className={`v-badge ${v.status === "ACTIVE" ? "v-badge-green" : v.status === "STABLE" ? "v-badge-electric" : "v-badge-muted"}`}>
                  {v.status === "ACTIVE" ? <><span className="mr-1">●</span>{v.status}</> : v.status}
                </span>
              </div>
              <p className="mt-1.5 text-xs text-muted">{v.description}</p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {v.features.map(f => (
                  <span key={f} className="rounded px-1.5 py-0.5 bg-ink-3/50 font-mono text-[9px] text-muted">{f}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Status indicators */}
      <div className="v-card">
        <p className="v-section-label mb-3">System Status</p>
        <div className="grid gap-2 md:grid-cols-3">
          {[
            { label: "Policy Engine", status: "OPERATIONAL", icon: CheckCircle, color: "text-moss" },
            { label: "Quantum Co-processor", status: "STANDBY", icon: Clock, color: "text-amber" },
            { label: "Audit Chain", status: "OPERATIONAL", icon: CheckCircle, color: "text-moss" },
            { label: "Operator Mesh", status: "OPERATIONAL", icon: CheckCircle, color: "text-moss" },
            { label: "Route Engine", status: "OPERATIONAL", icon: CheckCircle, color: "text-moss" },
            { label: "Kill Switch", status: "ARMED", icon: AlertCircle, color: "text-crimson" },
          ].map(item => (
            <div key={item.label} className="flex items-center gap-2 rounded-md border border-rule/50 bg-ink-3/30 px-3 py-2">
              <item.icon className={`h-3.5 w-3.5 ${item.color}`} />
              <div>
                <p className="text-xs font-medium text-bone">{item.label}</p>
                <p className={`text-[10px] font-mono ${item.color}`}>{item.status}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
