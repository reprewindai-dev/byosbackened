import { Bell, Download, Filter, Shield, AlertTriangle } from "lucide-react";
import { MiniChart } from "@/components/MiniChart";

const METRICS = [
  { label: "Requests / min", value: "2,418", delta: "+8%", deltaUp: true, color: "moss", sparkline: [30, 35, 42, 50, 55, 48, 60, 72, 65, 80, 75, 85] },
  { label: "Tokens / sec", value: "184k", delta: "+22%", deltaUp: true, color: "electric", sparkline: [40, 50, 55, 60, 58, 70, 68, 75, 80, 85, 90, 95] },
  { label: "Error rate", value: "0.18%", delta: "-0.04%", deltaUp: false, color: "crimson", sparkline: [8, 6, 7, 5, 4, 6, 3, 4, 3, 2, 3, 2] },
  { label: "GPU util", value: "78%", delta: "8× A100", deltaUp: true, color: "amber", sparkline: [60, 65, 70, 68, 72, 75, 78, 80, 76, 78, 80, 78] },
];

const LOGS = [
  { ts: "07:24:11.412Z", lvl: "inf", deploy: "chat-prod", model: "llama3-70b", latency: "142ms", user: "user_8a31", pii: "*[REDACT]*", cost: "$0.00091", ok: true },
  { ts: "07:24:09.214Z", lvl: "inf", deploy: "chat-prod", model: "llama3-70b", latency: "358ms", user: "user_f1e4", pii: "*[REDACT]*", cost: "$0.00102", ok: true },
  { ts: "07:24:08.901Z", lvl: "inf", deploy: "embed-rag", model: "bge-m3", latency: "14ms", user: "ci-runner", pii: "vsc_4CPU", cost: "$0.00002", ok: true },
  { ts: "07:24:07.781Z", lvl: "inf", deploy: "chat-prod", model: "mixtral-8x22", latency: "121ms", user: "user_8a31", pii: "*[REDACT]*", cost: "$0.00057", ok: true },
  { ts: "07:24:06.512Z", lvl: "inf", deploy: "code-assist", model: "deepseek-v3", latency: "88ms", user: "vsc:elliot", pii: "*[REDACT]*", cost: "$0.00041", ok: true },
  { ts: "07:24:05.231Z", lvl: "WARN", deploy: "chat-prod", model: "llama3-70b", latency: "612ms", user: "user_77ci", pii: "*[REDACT]*", cost: "$0.00131", ok: false },
  { ts: "07:24:04.182Z", lvl: "inf", deploy: "embed-rag", model: "bge-m3", latency: "12ms", user: "ci-runner", pii: "vsc_4CPU", cost: "$0.00002", ok: true },
  { ts: "07:24:02.812Z", lvl: "inf", deploy: "patient-intake", model: "pipeline", latency: "276ms", user: "user_phi", pii: "*[REDACT]*", cost: "$0.00098", ok: true },
  { ts: "07:24:01.512Z", lvl: "CRIT", deploy: "egress", model: "allowlist", latency: "—", user: "system", pii: "rule#7", cost: "review pending", ok: false },
];

const AUDIT = [
  { action: "deploy.update", actor: "chat-prod · elliot@acme.io", ts: "07:24:11Z", hash: "9f4e..ac21" },
  { action: "policy.intercept", actor: "sessionRpj_421 · system/router", ts: "07:18:02Z", hash: "5b71..0c19" },
  { action: "vault.rotate", actor: "OPEN_KEY_PROXY · kira@acme.io", ts: "07:11:55Z", hash: "0c11.7d0a" },
  { action: "evidence.export", actor: "soc2-q2-pkg.zip · system/compliance", ts: "07:02:21Z", hash: "ef07..2941" },
  { action: "key.create", actor: "key_8h2x_chat · alex@acme.io", ts: "06:54:17Z", hash: "12cd..ee01" },
];

const ALERTS = [
  { name: "P95 latency · chat-prod", rule: "> 800 ms · 5 min", status: "WATCHING", channel: "Slack #ops" },
  { name: "Error rate · spike", rule: "> 1% · 2 min", status: "WATCHING", channel: "PagerDuty" },
  { name: "Cost burn · daily cap", rule: "> 90% spend", status: "ACTIVE", channel: "email" },
  { name: "GPU memory · pressure", rule: "> 92% · 1 min", status: "WATCHING", channel: "Slack #ops" },
  { name: "Anomaly · request volume", rule: "z-score > 3", status: "WATCHING", channel: "email" },
  { name: "Compliance export · failed", rule: "any failure", status: "WATCHING", channel: "PagerDuty" },
];

export function MonitoringPage() {
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
        {METRICS.map((m) => (
          <div key={m.label} className="v-card">
            <div className="flex items-center justify-between">
              <p className="v-section-label">{m.label}</p>
              <span className={`text-[10px] font-semibold ${m.color === "crimson" ? "text-moss" : m.deltaUp ? "text-moss" : "text-crimson"}`}>{m.delta}</span>
            </div>
            <p className="mt-1 text-2xl font-bold text-bone">{m.value}</p>
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
            <span className="v-badge v-badge-green">● HEALTHY</span>
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
            {["0h", "1h", "2h", "3h", "4h", "5h", "6h", "7h", "8h", "9h", "10h", "11h", "12h", "13h", "14h", "15h", "16h", "17h", "18h", "19h", "20h", "21h", "22h", "23h"].filter((_, i) => i % 4 === 0).map(l => <span key={l}>{l}</span>)}
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

      {/* Logs + Audit */}
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="v-card">
          <div className="flex items-center justify-between mb-3">
            <div>
              <p className="v-section-label">Logs · Structured</p>
              <p className="text-sm font-semibold text-bone">Search, filter, export — PHI/PII redacted before write</p>
            </div>
            <div className="flex items-center gap-2">
              <input placeholder="model:llama* status:>=400" className="v-input w-52 text-[10px]" />
              <button className="rounded p-1.5 border border-rule text-muted hover:text-bone"><Filter className="h-3.5 w-3.5" /></button>
            </div>
          </div>
          <div className="rounded-md border border-rule bg-ink-2 p-3 font-mono text-[9.5px] leading-[1.8] overflow-x-auto max-h-60 space-y-0">
            {LOGS.map((l, i) => (
              <div key={i} className={`flex gap-2 whitespace-nowrap ${l.lvl === "CRIT" ? "text-crimson" : l.lvl === "WARN" ? "text-amber" : "text-muted"}`}>
                <span className="text-muted-2">{l.ts}</span>
                <span className={l.lvl === "CRIT" ? "text-crimson font-bold" : l.lvl === "WARN" ? "text-amber font-bold" : "text-muted"}>{l.lvl.padEnd(4)}</span>
                <span className="text-bone-2">{l.deploy}</span>
                <span className="text-muted">{l.model}</span>
                <span className="text-bone">{l.latency}</span>
                <span className="text-muted">{l.user}</span>
                <span className="text-crimson">{l.pii}</span>
                <span className="text-moss">{l.cost}</span>
                <span>{l.ok ? "✓" : "△"}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="v-card">
          <div className="flex items-center justify-between mb-3">
            <div>
              <p className="v-section-label">Audit Log · Tamper-Evident</p>
              <p className="text-sm font-semibold text-bone">SHA-256 hash chain</p>
            </div>
            <span className="v-badge v-badge-green"><Shield className="h-2.5 w-2.5" /> VERIFIED</span>
          </div>
          <div className="space-y-0">
            {AUDIT.map((a, i) => (
              <div key={i} className="flex items-center justify-between border-b border-rule/50 py-3 last:border-0">
                <div>
                  <p className="font-mono text-xs font-semibold text-bone">{a.action}</p>
                  <p className="text-[10px] text-muted">{a.actor}</p>
                </div>
                <div className="text-right">
                  <p className="font-mono text-[10px] text-muted">{a.ts}</p>
                  <p className="font-mono text-[10px] text-muted-2">{a.hash}</p>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-3 flex items-center justify-between border-t border-rule pt-3">
            <p className="font-mono text-[9px] text-muted-2">Hash anchor: root.7d80..ee01</p>
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
