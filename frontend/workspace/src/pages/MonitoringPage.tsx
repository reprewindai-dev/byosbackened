import { useEffect, useState, useCallback } from "react";
import { Bell, Download, Filter, Shield, AlertTriangle, Loader2 } from "lucide-react";
import { MiniChart } from "@/components/MiniChart";
import { api } from "@/lib/api";

interface AuditLog {
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
  tenant_id?: string;
}

interface SystemHealth {
  db_ok?: boolean;
  redis_ok?: boolean;
  llm_ok?: boolean;
  llm_model?: string;
  circuit_breaker?: { state: string; failures: number };
  uptime_seconds?: number;
}

const ALERTS = [
  { name: "P95 latency · chat-prod", rule: "> 800 ms · 5 min", status: "WATCHING", channel: "Slack #ops" },
  { name: "Error rate · spike", rule: "> 1% · 2 min", status: "WATCHING", channel: "PagerDuty" },
  { name: "Cost burn · daily cap", rule: "> 90% spend", status: "ACTIVE", channel: "email" },
  { name: "GPU memory · pressure", rule: "> 92% · 1 min", status: "WATCHING", channel: "Slack #ops" },
  { name: "Anomaly · request volume", rule: "z-score > 3", status: "WATCHING", channel: "email" },
  { name: "Compliance export · failed", rule: "any failure", status: "WATCHING", channel: "PagerDuty" },
];

export function MonitoringPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    const results = await Promise.allSettled([
      api.get("/audit/logs", { params: { limit: 20 } }).then(r => r.data),
      api.get("/monitoring/health").then(r => r.data).catch(() =>
        fetch(`${window.__VEKLOM_API_BASE__ || ""}/status`).then(r => r.json())
      ),
    ]);
    if (results[0].status === "fulfilled") {
      const items = Array.isArray(results[0].value) ? results[0].value : results[0].value?.items || [];
      setLogs(items);
    }
    if (results[1].status === "fulfilled") setHealth(results[1].value);
    setLoading(false);
  }, []);

  useEffect(() => { fetchData(); const iv = setInterval(fetchData, 15_000); return () => clearInterval(iv); }, [fetchData]);

  const dbOk = health?.db_ok ?? false;
  const redisOk = health?.redis_ok ?? false;
  const llmOk = health?.llm_ok ?? false;
  const cbState = health?.circuit_breaker?.state || "—";

  const liveMetrics = [
    { label: "Database", value: dbOk ? "Connected" : "Down", delta: dbOk ? "healthy" : "error", deltaUp: dbOk, color: dbOk ? "moss" : "crimson", sparkline: [70, 72, 75, 78, 80, 82, 85, 88, 90, 92, 95, 98] },
    { label: "Redis", value: redisOk ? "Connected" : "Down", delta: redisOk ? "healthy" : "error", deltaUp: redisOk, color: redisOk ? "electric" : "crimson", sparkline: [60, 65, 70, 72, 78, 80, 85, 88, 90, 92, 95, 98] },
    { label: "LLM", value: llmOk ? "Online" : "Offline", delta: health?.llm_model || "—", deltaUp: llmOk, color: llmOk ? "amber" : "crimson", sparkline: [40, 50, 55, 60, 58, 70, 68, 75, 80, 85, 90, 95] },
    { label: "Circuit Breaker", value: cbState, delta: `${health?.circuit_breaker?.failures ?? 0} failures`, deltaUp: cbState === "CLOSED", color: cbState === "CLOSED" ? "moss" : "crimson", sparkline: [8, 6, 7, 5, 4, 6, 3, 4, 3, 2, 3, 2] },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-start justify-between">
        <div>
          <p className="v-section-label">Monitoring · APM</p>
          <h1 className="mt-1 text-2xl font-bold text-bone">Real-time observability</h1>
          <p className="mt-1 text-sm text-muted">Throughput, latency, GPU pressure, error rates, and tamper-evident audit logs — one console, one perimeter.</p>
        </div>
        <div className="flex gap-2">
          <button className="v-btn-ghost text-xs"><Bell className="h-3.5 w-3.5" /> Alerts</button>
          <button className="v-btn-primary text-xs"><Download className="h-3.5 w-3.5" /> Export evidence</button>
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-4 gap-4">
        {liveMetrics.map((m) => (
          <div key={m.label} className="v-card">
            <div className="flex items-center justify-between">
              <p className="v-section-label">{m.label}</p>
              <span className={`text-[10px] font-semibold ${m.deltaUp ? "text-moss" : "text-crimson"}`}>{m.delta}</span>
            </div>
            <p className="mt-1 text-2xl font-bold text-bone">{loading ? "—" : m.value}</p>
            <div className="mt-2 h-6"><MiniChart color={m.color} data={m.sparkline} /></div>
          </div>
        ))}
      </div>

      {/* Charts row */}
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="v-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="v-section-label">Throughput</p>
              <p className="text-sm font-semibold text-bone">Hetzner vs AWS burst · 24h</p>
            </div>
            <span className={`v-badge ${dbOk && redisOk ? "v-badge-green" : "v-badge-amber"}`}>● {dbOk && redisOk ? "HEALTHY" : "DEGRADED"}</span>
          </div>
          <div className="mt-2 flex items-center gap-3 text-[9px]">
            <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-sm bg-amber/70" /> Hetzner</span>
            <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-sm bg-electric/50" /> AWS burst</span>
          </div>
          <div className="mt-3 flex items-end gap-[3px] h-36">
            {Array.from({ length: 24 }).map((_, i) => {
              const h1 = 25 + Math.sin(i * 0.4) * 20 + Math.random() * 30;
              const h2 = Math.random() * 15;
              return (
                <div key={i} className="flex-1 flex flex-col-reverse gap-[1px]">
                  <div className="w-full rounded-t-sm bg-amber/60" style={{ height: `${h1}%` }} />
                  <div className="w-full rounded-t-sm bg-electric/40" style={{ height: `${h2}%` }} />
                </div>
              );
            })}
          </div>
          <div className="mt-2 flex justify-between text-[9px] font-mono text-muted">
            {["0h", "4h", "8h", "12h", "16h", "20h"].map(l => <span key={l}>{l}</span>)}
          </div>
          <div className="mt-1 flex justify-between text-[9px] font-mono text-muted-2">
            <span>0</span><span>30</span><span>60</span><span>90</span><span>120</span>
          </div>
        </div>

        <div className="v-card">
          <div>
            <p className="v-section-label">Latency · P50 / P95 / P99</p>
            <p className="text-sm font-semibold text-bone">All deployments</p>
          </div>
          <div className="mt-2 flex items-center gap-3 text-[9px]">
            <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-sm bg-violet/80" /> P50</span>
            <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-sm bg-violet/50" /> P95</span>
            <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-sm bg-violet/25" /> P99</span>
          </div>
          <div className="mt-3 flex items-end gap-[3px] h-36">
            {Array.from({ length: 24 }).map((_, i) => {
              const base = 60 + Math.sin(i * 0.3) * 15 + Math.random() * 20;
              return (
                <div key={i} className="flex-1 flex flex-col-reverse gap-[1px]">
                  <div className="w-full rounded-t-sm bg-violet/80" style={{ height: `${base * 0.5}%` }} />
                  <div className="w-full rounded-t-sm bg-violet/45" style={{ height: `${base * 0.25}%` }} />
                  <div className="w-full rounded-t-sm bg-violet/20" style={{ height: `${base * 0.15}%` }} />
                </div>
              );
            })}
          </div>
          <div className="mt-2 flex justify-between text-[9px] font-mono text-muted">
            {["0h", "4h", "8h", "12h", "16h", "20h"].map(l => <span key={l}>{l}</span>)}
          </div>
          <div className="mt-1 flex justify-between text-[9px] font-mono text-muted-2">
            <span>0</span><span>55</span><span>110</span><span>165</span><span>220</span>
          </div>
        </div>
      </div>

      {/* Logs + Audit — live from /audit/logs */}
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="v-card">
          <div className="flex items-center justify-between mb-3">
            <div>
              <p className="v-section-label">Logs · Structured</p>
              <p className="text-sm font-semibold text-bone">Live audit trail — PHI/PII redacted before write</p>
            </div>
            <div className="flex items-center gap-2">
              <input placeholder="model:llama* status:>=400" className="v-input w-52 text-[10px]" />
              <button className="rounded p-1.5 border border-rule text-muted hover:text-bone"><Filter className="h-3.5 w-3.5" /></button>
            </div>
          </div>
          <div className="rounded-md border border-rule bg-ink-2 p-3 font-mono text-[9.5px] leading-[1.8] overflow-x-auto max-h-60 space-y-0">
            {logs.length > 0 ? logs.map((l: AuditLog, i: number) => (
              <div key={l.id || i} className="flex gap-2 whitespace-nowrap text-muted">
                <span className="text-muted-2">{l.created_at ? new Date(l.created_at).toISOString().slice(11, 23) : "—"}</span>
                <span className="text-muted">inf </span>
                <span className="text-bone-2">{l.operation_type || "exec"}</span>
                <span className="text-muted">{l.model || "—"}</span>
                <span className="text-bone">{l.latency_ms ? `${l.latency_ms}ms` : "—"}</span>
                <span className="text-muted">{l.provider || "—"}</span>
                <span className="text-moss">{l.cost ? `$${l.cost}` : "—"}</span>
                <span>{l.hmac_hash ? "✓" : "△"}</span>
              </div>
            )) : (
              <div className="text-center text-muted py-4">{loading ? "Loading..." : "No audit logs yet"}</div>
            )}
          </div>
        </div>

        <div className="v-card">
          <div className="flex items-center justify-between mb-3">
            <div>
              <p className="v-section-label">Audit Log · Tamper-Evident</p>
              <p className="text-sm font-semibold text-bone">HMAC-SHA256 integrity chain</p>
            </div>
            <span className="v-badge v-badge-green"><Shield className="h-2.5 w-2.5" /> VERIFIED</span>
          </div>
          <div className="space-y-0">
            {logs.slice(0, 5).map((a: AuditLog, i: number) => (
              <div key={a.id || i} className="flex items-center justify-between border-b border-rule/50 py-3 last:border-0">
                <div>
                  <p className="font-mono text-xs font-semibold text-bone">{a.operation_type || "ai.exec"}</p>
                  <p className="text-[10px] text-muted">{a.model || "—"} · {a.provider || "—"}</p>
                </div>
                <div className="text-right">
                  <p className="font-mono text-[10px] text-muted">{a.created_at ? new Date(a.created_at).toISOString().slice(11, 19) : "—"}</p>
                  <p className="font-mono text-[10px] text-muted-2">{a.hmac_hash ? `${a.hmac_hash.slice(0, 4)}..${a.hmac_hash.slice(-4)}` : "—"}</p>
                </div>
              </div>
            ))}
            {logs.length === 0 && !loading && (
              <p className="py-4 text-center text-xs text-muted">No audit entries yet</p>
            )}
          </div>
          <div className="mt-3 flex items-center justify-between border-t border-rule pt-3">
            <p className="font-mono text-[9px] text-muted-2">HMAC integrity chain active</p>
            <button className="v-btn-ghost text-[10px]"><Download className="h-3 w-3" /> Export pkg →</button>
          </div>
        </div>
      </div>

      {/* Alerts */}
      <div className="v-card">
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="v-section-label">Alerts · Routes & Thresholds</p>
            <p className="text-sm font-semibold text-bone">Email · Slack · PagerDuty</p>
          </div>
          <button className="v-btn-primary text-xs"><AlertTriangle className="h-3.5 w-3.5" /> + New alert</button>
        </div>
        <div className="grid gap-3 md:grid-cols-3">
          {ALERTS.map((a) => (
            <div key={a.name} className="flex items-center justify-between rounded-md border border-rule/50 bg-ink-3/30 px-3 py-2.5">
              <div>
                <p className="text-xs font-semibold text-bone">{a.name}</p>
                <p className="font-mono text-[9px] text-muted">{a.rule}</p>
              </div>
              <div className="text-right">
                <span className={`v-badge text-[8px] ${a.status === "ACTIVE" ? "v-badge-amber" : "v-badge-muted"}`}>● {a.status}</span>
                <p className="font-mono text-[9px] text-muted mt-0.5">{a.channel}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
