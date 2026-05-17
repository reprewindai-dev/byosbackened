import { useEffect, useState, useCallback, useRef } from "react";
import { Shield, Zap, GitBranch, Lock, Activity, Settings, ChevronRight, CheckCircle, AlertCircle, Clock, Send, RefreshCw } from "lucide-react";
import { api } from "@/lib/api";

/* ── static fallbacks (used when API is unreachable) ─────────────────── */
const FALLBACK_OPERATORS = [
  { id: "phi-redact", name: "PHI Redaction", category: "Privacy", status: "ACTIVE", version: "v2.4.1", latency: "< 1ms", hits: "18,420", description: "Redacts PHI/PII before any model sees the prompt" },
  { id: "policy-gate", name: "Policy Gate", category: "Governance", status: "ACTIVE", version: "v3.1.0", latency: "< 1ms", hits: "184,200", description: "Evaluates outbound policy rules before execution" },
  { id: "route-select", name: "Route Selector", category: "Routing", status: "ACTIVE", version: "v1.8.2", latency: "< 1ms", hits: "184,200", description: "Selects optimal zone based on cost, latency, policy" },
  { id: "audit-sign", name: "Audit Signer", category: "Compliance", status: "ACTIVE", version: "v2.0.0", latency: "< 2ms", hits: "184,200", description: "Appends tamper-evident SHA-256 hash to every log entry" },
  { id: "budget-guard", name: "Budget Guard", category: "Finance", status: "ACTIVE", version: "v1.2.3", latency: "< 1ms", hits: "184,200", description: "Enforces per-team and org-level spend caps" },
  { id: "content-safety", name: "Content Safety", category: "Safety", status: "ACTIVE", version: "v1.5.0", latency: "3ms", hits: "184,200", description: "Scans output for policy violations before delivery" },
];

const FALLBACK_VERSIONS = [
  { version: "v4", label: "Quantum-Classical Hybrid", status: "ACTIVE", description: "Full UACP with quantum co-processor routing", features: ["Quantum gate scheduling", "Classical fallback", "Sub-ms handoff"] },
  { version: "v3", label: "Autonomous Orchestration", status: "STABLE", description: "Multi-agent orchestration with policy enforcement", features: ["Agent mesh", "Policy-aware routing", "Evidence collection"] },
  { version: "v2", label: "Deterministic Routing", status: "STABLE", description: "Rule-based deterministic routing engine", features: ["Static rules", "Cost optimization", "Zone selection"] },
  { version: "v1", label: "Basic Gateway", status: "LEGACY", description: "Original gateway with basic policy support", features: ["HTTP proxy", "Basic auth", "Request logging"] },
];

const FALLBACK_STATUSES = [
  { label: "Policy Engine", status: "OPERATIONAL", icon: CheckCircle, color: "text-moss" },
  { label: "Quantum Co-processor", status: "STANDBY", icon: Clock, color: "text-amber" },
  { label: "Audit Chain", status: "OPERATIONAL", icon: CheckCircle, color: "text-moss" },
  { label: "Operator Mesh", status: "OPERATIONAL", icon: CheckCircle, color: "text-moss" },
  { label: "Route Engine", status: "OPERATIONAL", icon: CheckCircle, color: "text-moss" },
  { label: "Kill Switch", status: "ARMED", icon: AlertCircle, color: "text-crimson" },
];

const PIPELINE_STAGES = [
  { id: "inbound", label: "Inbound", icon: Shield, ops: ["PHI Redaction", "Policy Gate"] },
  { id: "routing", label: "Routing", icon: GitBranch, ops: ["Route Selector", "Budget Guard"] },
  { id: "exec", label: "Execution", icon: Zap, ops: ["Model Inference", "SSE Stream"] },
  { id: "outbound", label: "Outbound", icon: Lock, ops: ["Content Safety", "Audit Signer"] },
];

/* eslint-disable @typescript-eslint/no-explicit-any */

export function GPCPage() {
  const [connected, setConnected] = useState(false);
  const [operators, setOperators] = useState<any[]>(FALLBACK_OPERATORS);
  const [uacpVersions, setUacpVersions] = useState<any[]>(FALLBACK_VERSIONS);
  const [systemStatuses, setSystemStatuses] = useState<any[]>(FALLBACK_STATUSES);
  const [sotSnapshot, setSotSnapshot] = useState<any>(null);
  const [activeVersion, setActiveVersion] = useState("v4");
  const [operatorCount, setOperatorCount] = useState(6);

  // Execute state
  const [execInput, setExecInput] = useState("");
  const [execLog, setExecLog] = useState<string[]>([]);
  const [executing, setExecuting] = useState(false);
  const logRef = useRef<HTMLDivElement>(null);

  const fetchData = useCallback(async () => {
    try {
      // 1. UACP status → versions + system health
      const { data: uacpStatus } = await api.get("/internal/uacp/status");
      if (uacpStatus) {
        setConnected(true);
        if (uacpStatus.active_version) setActiveVersion(uacpStatus.active_version);
        if (Array.isArray(uacpStatus.versions) && uacpStatus.versions.length > 0) setUacpVersions(uacpStatus.versions);
        if (uacpStatus.subsystem_health) {
          const mapped = Object.entries(uacpStatus.subsystem_health).map(([key, val]: [string, any]) => ({
            label: key.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase()),
            status: val?.status || val || "UNKNOWN",
            icon: val?.status === "ARMED" || val === "ARMED" ? AlertCircle : val?.status === "STANDBY" || val === "STANDBY" ? Clock : CheckCircle,
            color: val?.status === "ARMED" || val === "ARMED" ? "text-crimson" : val?.status === "STANDBY" || val === "STANDBY" ? "text-amber" : "text-moss",
          }));
          if (mapped.length > 0) setSystemStatuses(mapped);
        }
      }
    } catch { /* fallback */ }

    try {
      // 2. Live operators
      const { data: ops } = await api.get("/internal/operators");
      const list = ops?.operators ?? (Array.isArray(ops) ? ops : []);
      if (list.length > 0) {
        setOperators(list);
        setOperatorCount(list.length);
      }
    } catch { /* fallback */ }

    try {
      // 3. SOT snapshot
      const { data: sot } = await api.get("/source-of-truth/snapshot");
      if (sot) setSotSnapshot(sot);
    } catch { /* optional */ }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  async function handleExecute() {
    if (!execInput.trim() || executing) return;
    setExecuting(true);
    setExecLog(prev => [...prev, `▶ ${execInput}`]);
    try {
      const { data } = await api.post("/internal/uacp/execute", {
        command: execInput,
        version: activeVersion,
        operators: operators.map(o => o.id),
        context: {},
      });
      const result = typeof data === "string" ? data : JSON.stringify(data, null, 2);
      setExecLog(prev => [...prev, result]);
    } catch (err: any) {
      setExecLog(prev => [...prev, `✗ Error: ${err?.response?.data?.detail || err?.message || "execute failed"}`]);
    }
    setExecInput("");
    setExecuting(false);
    setTimeout(() => logRef.current?.scrollTo(0, logRef.current.scrollHeight), 50);
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <p className="v-section-label">GPC · Global Policy Control</p>
          <h1 className="mt-1 text-2xl font-bold text-bone">Universal AI Control Plane</h1>
          <p className="mt-1 max-w-2xl text-sm text-muted">
            Every prompt passes through the GPC pipeline — redaction, policy, routing, execution, audit — before any model sees it.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <span className={`rounded px-2 py-0.5 text-[9px] font-mono font-semibold ${connected ? "bg-moss/15 text-moss" : "bg-crimson/15 text-crimson"}`}>
              ● {connected ? "Backend Connected" : "Offline — Static Fallback"}
            </span>
            <span className="rounded bg-amber/15 px-2 py-0.5 text-[9px] font-mono font-semibold text-amber">UACP {activeVersion} Active</span>
            <span className="rounded bg-bone/10 px-2 py-0.5 text-[9px] font-mono font-semibold text-muted">{operatorCount} Operators Live</span>
            {sotSnapshot && (
              <span className="rounded bg-electric/15 px-2 py-0.5 text-[9px] font-mono font-semibold text-electric">
                SOT synced {sotSnapshot.last_sync ? new Date(sotSnapshot.last_sync).toLocaleTimeString() : "✓"}
              </span>
            )}
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={fetchData} className="flex items-center gap-1.5 rounded-md border border-rule px-3 py-1.5 text-xs text-muted hover:text-bone">
            <RefreshCw className="h-3.5 w-3.5" /> Refresh
          </button>
          <button className="flex items-center gap-1.5 rounded-md border border-rule px-3 py-1.5 text-xs text-muted hover:text-bone">
            <Settings className="h-3.5 w-3.5" /> Configure
          </button>
        </div>
      </div>

      {/* Execute — center blackbox */}
      <div className="v-card border-amber/20">
        <div className="flex items-center gap-2 mb-3">
          <Zap className="h-4 w-4 text-amber" />
          <span className="text-sm font-semibold text-bone">GPC Execute</span>
          <span className="ml-auto rounded bg-ink-3 px-1.5 py-0.5 text-[8px] font-mono text-muted">POST /internal/uacp/execute</span>
        </div>
        <div ref={logRef} className="mb-3 h-40 overflow-y-auto rounded-md bg-[#0d0d0d] border border-rule/30 p-3 font-mono text-[11px] leading-relaxed text-bone">
          {execLog.length === 0 ? (
            <p className="text-muted">GPC execution log — send a command below to see pipeline trace.</p>
          ) : execLog.map((line, i) => (
            <p key={i} className={line.startsWith("▶") ? "text-amber" : line.startsWith("✗") ? "text-crimson" : "text-bone/80"}>{line}</p>
          ))}
        </div>
        <div className="flex gap-2">
          <input
            value={execInput}
            onChange={e => setExecInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleExecute()}
            placeholder="Enter GPC command… (e.g. audit.verify, policy.evaluate, route.trace)"
            className="v-input flex-1 text-xs"
          />
          <button onClick={handleExecute} disabled={executing} className="v-btn-primary text-xs px-4">
            <Send className="h-3.5 w-3.5" /> {executing ? "Running…" : "Execute"}
          </button>
        </div>
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
        <p className="v-section-label mb-3">Operators · {connected ? "Live" : "Fallback"}</p>
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {operators.map((op: any) => (
            <div key={op.id} className="v-card">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-bone">{op.name}</span>
                    <span className={`rounded px-1.5 py-0.5 text-[8px] font-mono font-semibold ${op.status === "ACTIVE" ? "bg-moss/15 text-moss" : "bg-amber/15 text-amber"}`}>● {op.status}</span>
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
          {uacpVersions.map((v: any) => (
            <div key={v.version} className={`v-card ${v.status === "ACTIVE" ? "border-amber/30" : ""}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm font-bold text-bone">{v.version}</span>
                  <span className="text-xs text-muted">{v.label}</span>
                </div>
                <span className={`rounded px-1.5 py-0.5 text-[8px] font-mono font-semibold ${v.status === "ACTIVE" ? "bg-moss/15 text-moss" : v.status === "STABLE" ? "bg-electric/15 text-electric" : "bg-bone/10 text-muted"}`}>
                  {v.status === "ACTIVE" && "● "}{v.status}
                </span>
              </div>
              <p className="mt-1.5 text-xs text-muted">{v.description}</p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {(v.features || []).map((f: string) => (
                  <span key={f} className="rounded px-1.5 py-0.5 bg-ink-3/50 font-mono text-[9px] text-muted">{f}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* System status */}
      <div className="v-card">
        <p className="v-section-label mb-3">System Status</p>
        <div className="grid gap-2 md:grid-cols-3">
          {systemStatuses.map((item: any) => {
            const Icon = item.icon || CheckCircle;
            return (
              <div key={item.label} className="flex items-center gap-2 rounded-md border border-rule/50 bg-ink-3/30 px-3 py-2">
                <Icon className={`h-3.5 w-3.5 ${item.color || "text-moss"}`} />
                <div>
                  <p className="text-xs font-medium text-bone">{item.label}</p>
                  <p className={`text-[10px] font-mono ${item.color || "text-moss"}`}>{item.status}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
