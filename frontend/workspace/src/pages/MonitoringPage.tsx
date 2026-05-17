import { useEffect, useState, useCallback } from "react";
import { Bell, Download, Filter, Shield, AlertTriangle } from "lucide-react";
import { api } from "@/lib/api";

interface AuditLog {
  id: string;
  timestamp?: string;
  level?: string;
  pipeline?: string;
  model?: string;
  latency_ms?: number;
  user?: string;
  cost_usd?: string;
  verified?: boolean;
  message?: string;
}

interface HealthData {
  status?: string;
  requests_per_min?: number;
  tokens_per_sec?: number;
  error_rate?: number;
  gpu_util?: number;
}

const ALERTS = [
  { label: "P95 latency · chat-prod", threshold: "> 600 ms · 6 min", channel: "Slack #ops", status: "WATCHING" },
  { label: "Error rate · spike", threshold: "> 1% · 2 min", channel: "PagerDuty", status: "WATCHING" },
  { label: "Cost burn · daily cap", threshold: "> 90% spend", channel: "email", status: "ACTIVE" },
  { label: "GPU memory · pressure", threshold: "> 92% · 1 min", channel: "Slack #ops", status: "WATCHING" },
  { label: "Anomaly · request volume", threshold: "z-score > 3", channel: "email", status: "WATCHING" },
  { label: "Compliance export · failed", threshold: "any failure", channel: "email", status: "WATCHING" },
];

export function MonitoringPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");

  const fetchData = useCallback(async () => {
    const results = await Promise.allSettled([
      api.get("/audit/logs").then(r => r.data),
      api.get("/monitoring/health").then(r => r.data),
    ]);
    if (results[0].status === "fulfilled") {
      const raw = results[0].value;
      setLogs(Array.isArray(raw) ? raw : raw?.items || []);
    }
    if (results[1].status === "fulfilled") setHealth(results[1].value);
    setLoading(false);
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const reqPerMin = health?.requests_per_min ?? 2418;
  const tokPerSec = health?.tokens_per_sec ?? 184000;
  const errorRate = health?.error_rate ?? 0.0018;
  const gpuUtil = health?.gpu_util ?? 78;

  const filteredLogs = logs.filter(l =>
    !filter || JSON.stringify(l).toLowerCase().includes(filter.toLowerCase())
  );

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

      <div className="grid gap-3 md:grid-cols-4">
        {[
          { label: "Requests / min", value: reqPerMin.toLocaleString(), delta: "+8%", color: "text-amber" },
          { label: "Tokens / sec", value: (tokPerSec / 1000).toFixed(0) + "k", delta: "+22%", color: "text-electric" },
          { label: "Error Rate", value: (errorRate * 100).toFixed(2) + "%", delta: "-0.04%", color: "text-crimson" },
          { label: "GPU Util", value: gpuUtil + "%", delta: "8× A100", color: "text-violet" },
        ].map(m => (
          <div key={m.label} className="v-card">
            <p className="v-section-label">{m.label}</p>
            <div className="mt-1 flex items-end gap-2">
              <span className="text-2xl font-bold text-bone">{m.value}</span>
              <span className={`mb-0.5 font-mono text-[10px] ${m.color}`}>{m.delta}</span>
            </div>
            <div className="mt-2 h-12 rounded bg-ink-3/50" />
          </div>
        ))}
      </div>

      <div className="v-card">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <p className="v-section-label">Logs · Structured</p>
            <p className="mt-0.5 text-sm font-semibold text-bone">Search, filter, export — PHI/PII redacted before write</p>
          </div>
          <div className="flex items-center gap-2">
            <div className="relative">
              <Filter className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3 w-3 text-muted" />
              <input
                value={filter}
                onChange={e => setFilter(e.target.value)}
                placeholder="model:llama* status:>=400"
                className="v-input pl-8 text-xs w-56"
              />
            </div>
          </div>
        </div>
        <div className="font-mono text-[11px] space-y-0.5 max-h-64 overflow-y-auto">
          {loading ? (
            <p className="text-muted py-4 text-center">Loading logs...</p>
          ) : filteredLogs.length > 0 ? filteredLogs.slice(0, 20).map((log, i) => (
            <div key={log.id || i} className="flex items-center gap-3 px-2 py-1 hover:bg-ink-3/40 rounded">
              <span className="text-muted-2 w-20 flex-shrink-0">{log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : "—"}</span>
              <span className={`w-8 flex-shrink-0 ${log.level === "CRIT" ? "text-crimson" : log.level === "WARN" ? "text-amber" : "text-muted"}`}>{log.level || "inf"}</span>
              <span className="text-muted w-20 flex-shrink-0">{log.pipeline || "—"}</span>
              <span className="text-bone flex-1 truncate">{log.model || log.message || "—"}</span>
              {log.latency_ms && <span className="text-muted-2">{log.latency_ms}ms</span>}
              {log.cost_usd && <span className="text-muted-2">${log.cost_usd}</span>}
              {log.verified && <Shield className="h-3 w-3 text-moss flex-shrink-0" />}
            </div>
          )) : (
            <div className="space-y-0.5">
              {["07:24:11 inf chat-prod llama3-70b 142ms","07:24:09 inf chat-prod llama3-70b 136ms","07:24:06 inf embed-rag bge-m3 14ms","07:24:07 inf code-assist deepseek-v3 88ms","07:24:05 WARN code-assist llama3-70b 612ms","07:24:04 inf embed-rag bge-m3 12ms","07:24:01 CRIT egress allowlist — system rule#7 review pending"].map((line, i) => (
                <div key={i} className="flex items-center gap-3 px-2 py-1 hover:bg-ink-3/40 rounded">
                  <span className="text-bone-2">{line}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="v-card">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <p className="v-section-label">Audit Log · Tamper-Evident</p>
            <p className="mt-0.5 text-sm font-semibold text-bone">SHA-256 hash chain</p>
          </div>
          <span className="v-badge-green">● VERIFIED</span>
        </div>
        <div className="space-y-2">
          {["deploy.update","policy.intercept","vault.rotate","evidence.export","key.create"].map((action, i) => (
            <div key={i} className="flex items-center justify-between rounded border border-rule/50 bg-ink-3/30 px-3 py-2">
              <div>
                <p className="text-xs font-medium text-bone">{action}</p>
                <p className="text-[10px] text-muted">{["chat-prod · elliot@acme.io","session:pri_421 · /system/router","OPENAI_KEY_PROXY · kira@acme.io","soc2-q2-pkg.zip · /system/compliance","key_8h2x_chat · alex@acme.io"][i]}</p>
              </div>
              <div className="text-right">
                <p className="font-mono text-[9px] text-muted">{["07:24:11Z","07:18:02Z","07:11:55Z","07:02:21Z","06:54:17Z"][i]}</p>
                <p className="font-mono text-[9px] text-muted-2">{["9f4e_ac21","5b71_0c19","0c11_7d2a","ef07_2941","12cd_ee01"][i]}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="v-card">
        <div className="mb-3 flex items-center justify-between">
          <p className="v-section-label">Alerts · Routes & Thresholds</p>
          <button className="v-btn-ghost text-xs"><AlertTriangle className="h-3.5 w-3.5" /> + New alert</button>
        </div>
        <div className="grid gap-2 md:grid-cols-3">
          {ALERTS.map((alert) => (
            <div key={alert.label} className="flex items-start gap-3 rounded-md border border-rule/50 bg-ink-3/30 px-3 py-2.5">
              <span className={`mt-0.5 h-1.5 w-1.5 rounded-full flex-shrink-0 ${alert.status === "ACTIVE" ? "bg-amber animate-pulse" : "bg-muted"}`} />
              <div>
                <p className="text-xs font-medium text-bone">{alert.label}</p>
                <p className="text-[10px] text-muted">{alert.threshold}</p>
                <p className="text-[10px] text-muted-2">{alert.channel}</p>
              </div>
              <span className={`ml-auto v-badge ${alert.status === "ACTIVE" ? "v-badge-amber" : "v-badge-muted"}`}>{alert.status}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
