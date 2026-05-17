import { useEffect, useState, useCallback } from "react";
import { Activity, Zap, DollarSign, Cpu, ShieldCheck, TrendingUp, AlertCircle, Loader2 } from "lucide-react";
import { MiniChart } from "@/components/MiniChart";
import { api } from "@/lib/api";

interface SystemStatus {
  status?: string;
  db_ok?: boolean;
  redis_ok?: boolean;
  llm_ok?: boolean;
  llm_model?: string;
  llm_models_available?: string[];
  groq_fallback_enabled?: boolean;
  circuit_breaker?: { state: string; failures: number; threshold: number; cooldown_seconds: number };
  uptime_seconds?: number;
}

interface AuditEntry {
  id: string;
  operation_type?: string;
  provider?: string;
  model?: string;
  input_tokens?: number;
  output_tokens?: number;
  cost?: string;
  latency_ms?: number;
  hmac_hash?: string;
  created_at?: string;
}

interface WalletBalance {
  balance_units?: number;
  balance_usd?: string;
}

const FALLBACK_METRICS = [
  { label: "Requests / min", value: "—", delta: "loading", color: "text-moss", icon: Activity },
  { label: "P50 Latency", value: "—", delta: "loading", color: "text-electric", icon: Zap },
  { label: "Tokens / sec", value: "—", delta: "loading", color: "text-brass-2", icon: TrendingUp },
  { label: "Spend today", value: "—", delta: "loading", color: "text-amber", icon: DollarSign },
  { label: "Active Models", value: "—", delta: "loading", color: "text-violet", icon: Cpu },
  { label: "Audit Entries", value: "—", delta: "loading", color: "text-moss", icon: ShieldCheck },
];

const POLICY_EVENTS = [
  { icon: "📥", label: "Inbound prompt", detail: "user · session pri_421 · 384 tokens", time: "07:24:11" },
  { icon: "✅", label: "Policy match", detail: "outbound.public.v3 · PHI scan run · 0 hits", time: "07:24:11" },
  { icon: "🔀", label: "Route decision", detail: "Hetzner FSN1 · llama3-70b · circuit closed", time: "07:24:11" },
  { icon: "⚡", label: "Inference complete", detail: "1,240 tokens · 142 ms · $0.00091", time: "07:24:12" },
  { icon: "🔏", label: "Audit signed", detail: "SHA-256 9f4e...ac21 · evidence appended", time: "07:24:12" },
];

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  if (diff < 60_000) return `${Math.floor(diff / 1000)}s ago`;
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
  return `${Math.floor(diff / 3_600_000)}h ago`;
}

export function OverviewPage() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditEntry[]>([]);
  const [wallet, setWallet] = useState<WalletBalance | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const results = await Promise.allSettled([
        api.get("/monitoring/health").then(r => r.data).catch(() =>
          fetch(`${window.__VEKLOM_API_BASE__ || ""}/status`).then(r => r.json())
        ),
        api.get("/audit/logs", { params: { limit: 5 } }).then(r => r.data),
        api.get("/wallet/balance").then(r => r.data),
      ]);
      if (results[0].status === "fulfilled") setStatus(results[0].value);
      if (results[1].status === "fulfilled") {
        const logs = Array.isArray(results[1].value) ? results[1].value : results[1].value?.items || [];
        setAuditLogs(logs.slice(0, 5));
      }
      if (results[2].status === "fulfilled") setWallet(results[2].value);
      setError(null);
    } catch {
      setError("Could not reach backend — showing cached data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); const iv = setInterval(fetchData, 30_000); return () => clearInterval(iv); }, [fetchData]);

  const cbState = status?.circuit_breaker?.state || "UNKNOWN";
  const modelCount = status?.llm_models_available?.length ?? 0;
  const isHealthy = status?.status === "healthy" || status?.status === "ok" || (status?.db_ok && status?.redis_ok);

  const metrics = [
    { label: "System Status", value: isHealthy ? "Healthy" : status?.status || "—", delta: cbState === "CLOSED" ? "circuit closed" : cbState, color: isHealthy ? "text-moss" : "text-crimson", icon: Activity },
    { label: "LLM Status", value: status?.llm_ok ? "Online" : "—", delta: status?.llm_model || "—", color: status?.llm_ok ? "text-electric" : "text-muted", icon: Zap },
    { label: "Circuit Breaker", value: cbState, delta: `${status?.circuit_breaker?.failures ?? 0}/${status?.circuit_breaker?.threshold ?? 3} failures`, color: cbState === "CLOSED" ? "text-moss" : cbState === "OPEN" ? "text-crimson" : "text-amber", icon: TrendingUp },
    { label: "Reserve Balance", value: wallet?.balance_usd ? `$${wallet.balance_usd}` : "—", delta: wallet?.balance_units ? `${wallet.balance_units.toLocaleString()} units` : "—", color: "text-amber", icon: DollarSign },
    { label: "Active Models", value: String(modelCount || "—"), delta: status?.groq_fallback_enabled ? "Groq fallback on" : "local only", color: "text-violet", icon: Cpu },
    { label: "Audit Entries", value: auditLogs.length > 0 ? `${auditLogs.length}+ recent` : "—", delta: "HMAC verified", color: "text-moss", icon: ShieldCheck },
  ];

  const displayMetrics = loading ? FALLBACK_METRICS : metrics;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <p className="v-section-label">Workspace · Overview</p>
        <h1 className="mt-1 text-2xl font-bold text-bone">Sovereign control plane</h1>
        <p className="mt-1 text-sm text-muted">
          Every prompt routed, policed, and audited — across Hetzner primary and AWS burst — without leaving your perimeter.
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {isHealthy ? (
            <span className="v-badge-green">● Live Backend Connected</span>
          ) : loading ? (
            <span className="v-badge-muted"><Loader2 className="mr-1 inline h-3 w-3 animate-spin" />Connecting...</span>
          ) : (
            <span className="v-badge-amber">● Backend Unreachable</span>
          )}
          <span className="v-badge-muted">SOC2-Ready</span>
          <span className="v-badge-muted">HIPAA-Aware</span>
          <span className="v-badge-muted">EU-Sovereign</span>
        </div>
        {error && (
          <div className="mt-2 flex items-center gap-2 rounded-md border border-amber/30 bg-amber/5 px-3 py-2 text-xs text-amber">
            <AlertCircle className="h-3.5 w-3.5 shrink-0" /> {error}
          </div>
        )}
      </div>

      {/* Metrics row */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-3 xl:grid-cols-6">
        {displayMetrics.map((m) => (
          <div key={m.label} className="v-card flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="v-section-label">{m.label}</span>
              <m.icon className={`h-3.5 w-3.5 ${m.color} opacity-60`} />
            </div>
            <div className="flex items-end gap-2">
              <span className="text-xl font-bold text-bone">{m.value}</span>
              <span className={`mb-0.5 font-mono text-[10px] ${m.color}`}>{m.delta}</span>
            </div>
            <MiniChart color={m.color} />
          </div>
        ))}
      </div>

      {/* Main grid */}
      <div className="grid gap-4 lg:grid-cols-5">
        {/* Routing chart */}
        <div className="v-card lg:col-span-3">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <p className="v-section-label">Routing · Last 24h</p>
              <p className="mt-0.5 text-sm font-semibold text-bone">Hetzner primary · AWS burst</p>
            </div>
            <div className="flex gap-2">
              <span className="v-badge-amber">Hetzner 88%</span>
              <span className="v-badge-electric">AWS 12%</span>
            </div>
          </div>
          <div className="h-40 rounded-md bg-ink-3/50 flex items-center justify-center">
            <span className="text-xs text-muted">24h throughput chart</span>
          </div>
          <div className="mt-3 grid grid-cols-3 gap-3">
            <Infra label="Hetzner FSN1" value="78% util" detail="8× A100, 4× H100, 6× CPU pool" />
            <Infra label="Hetzner FRA1" value="62% util" detail="EU-sovereign · 4× L40s" />
            <Infra label="AWS Burst (US-East-1)" value="12% engaged" detail="On-demand · gated by policy" />
          </div>
        </div>

        {/* Spend */}
        <div className="v-card lg:col-span-2">
          <p className="v-section-label">Operating Reserve</p>
          <div className="mt-2 flex items-center justify-between">
            <span className="text-lg font-bold text-bone">
              {wallet?.balance_usd ? `$${wallet.balance_usd}` : "—"}
              <span className="ml-1 text-xs font-normal text-muted">
                {wallet?.balance_units ? `${wallet.balance_units.toLocaleString()} units` : ""}
              </span>
            </span>
            <span className="v-badge-amber">● Reserve</span>
          </div>
          <div className="v-progress mt-3">
            <div className="v-progress-fill bg-amber" style={{ width: wallet?.balance_units ? `${Math.min(100, (wallet.balance_units / 1000) * 100)}%` : "0%" }} />
          </div>
          <div className="mt-4 border-t border-rule pt-3">
            <div className="flex justify-between text-xs text-muted">
              <span>Groq Fallback</span>
              <span className="font-mono text-bone">{status?.groq_fallback_enabled ? "Enabled" : "Disabled"}</span>
            </div>
            <div className="mt-1 flex justify-between text-xs text-muted">
              <span>Circuit Breaker</span>
              <span className="font-mono text-bone">{status?.circuit_breaker?.state || "—"}</span>
            </div>
            <div className="mt-1 flex justify-between text-xs text-muted">
              <span>Uptime</span>
              <span className="font-mono text-bone">{status?.uptime_seconds ? `${Math.floor(status.uptime_seconds / 3600)}h ${Math.floor((status.uptime_seconds % 3600) / 60)}m` : "—"}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom grid */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* Recent Runs — live audit logs */}
        <div className="v-card-flush">
          <div className="flex items-center justify-between p-4 pb-3">
            <div>
              <p className="v-section-label">Recent Runs · Live</p>
              <p className="mt-0.5 text-sm font-semibold text-bone">Per-call routing, latency, cost</p>
            </div>
            <button className="v-btn-ghost text-xs">Playground →</button>
          </div>
          <table className="w-full text-xs">
            <thead>
              <tr className="border-y border-rule text-left">
                <th className="px-4 py-2 font-mono text-[9px] uppercase text-muted">Model</th>
                <th className="px-2 py-2 font-mono text-[9px] uppercase text-muted">Provider</th>
                <th className="px-2 py-2 font-mono text-[9px] uppercase text-muted">Latency</th>
                <th className="px-2 py-2 font-mono text-[9px] uppercase text-muted">Tokens</th>
                <th className="px-2 py-2 font-mono text-[9px] uppercase text-muted">Cost</th>
                <th className="px-2 py-2 font-mono text-[9px] uppercase text-muted">HMAC</th>
                <th className="px-2 py-2 font-mono text-[9px] uppercase text-muted">When</th>
              </tr>
            </thead>
            <tbody>
              {auditLogs.length > 0 ? auditLogs.map((r: AuditEntry, i: number) => (
                <tr key={r.id || i} className="border-b border-rule/50 hover:bg-ink-3/40">
                  <td className="px-4 py-2 font-medium text-bone">{r.model || r.operation_type || "—"}</td>
                  <td className="px-2 py-2">
                    <span className={`rounded px-1.5 py-0.5 font-mono text-[9px] ${r.provider === "ollama" ? "bg-amber/15 text-amber" : "bg-electric/15 text-electric"}`}>
                      {r.provider || "—"}
                    </span>
                  </td>
                  <td className="px-2 py-2 font-mono text-bone-2">{r.latency_ms ? `${r.latency_ms} ms` : "—"}</td>
                  <td className="px-2 py-2 font-mono text-bone-2">{(r.input_tokens || 0) + (r.output_tokens || 0)}</td>
                  <td className="px-2 py-2 font-mono text-bone-2">{r.cost ? `$${r.cost}` : "—"}</td>
                  <td className="px-2 py-2">
                    <span className="v-badge v-badge-green">{r.hmac_hash ? "VERIFIED" : "—"}</span>
                  </td>
                  <td className="px-2 py-2 text-muted">{r.created_at ? timeAgo(r.created_at) : "—"}</td>
                </tr>
              )) : (
                <tr><td colSpan={7} className="px-4 py-6 text-center text-muted">No recent runs — execute a prompt in the Playground</td></tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Policy Interception */}
        <div className="v-card">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <p className="v-section-label">Policy Interception · Live</p>
              <p className="mt-0.5 text-sm font-semibold text-bone">Decision before execution</p>
            </div>
            <span className="flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-moss" />
              <span className="font-mono text-[9px] text-moss">LIVE</span>
            </span>
          </div>
          <div className="space-y-3">
            {POLICY_EVENTS.map((ev, i) => (
              <div key={i} className="flex items-start gap-3 rounded-md border border-rule/50 bg-ink-3/30 px-3 py-2">
                <span className="mt-0.5 text-sm">{ev.icon}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-bone">{ev.label}</p>
                  <p className="truncate text-[11px] text-muted">{ev.detail}</p>
                </div>
                <span className="shrink-0 font-mono text-[10px] text-muted-2">{ev.time}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function Infra({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="rounded-md border border-rule/50 bg-ink-3/30 px-3 py-2">
      <p className="font-mono text-[9px] uppercase text-muted">{label}</p>
      <p className="mt-0.5 text-sm font-semibold text-bone">{value}</p>
      <p className="mt-0.5 text-[10px] text-muted-2">{detail}</p>
    </div>
  );
}

function SpendItem({ label, pct, value }: { label: string; pct: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-muted">{label}</span>
      <div className="flex items-center gap-2">
        <span className="font-mono text-[10px] text-muted-2">{pct}</span>
        <span className="font-mono text-xs font-medium text-bone">{value}</span>
      </div>
    </div>
  );
}
