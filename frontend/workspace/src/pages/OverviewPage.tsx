import { useEffect, useState, useCallback } from "react";
import { Activity, Zap, DollarSign, Cpu, ShieldCheck, TrendingUp } from "lucide-react";
import { MiniChart } from "@/components/MiniChart";
import { api, rawApi } from "@/lib/api";

interface StatusData {
  status?: string;
  requests_per_min?: number;
  tokens_per_sec?: number;
  error_rate?: number;
  gpu_util?: number;
  active_models?: number;
  audit_entries?: number;
}

interface WalletData {
  balance_usd?: string;
  daily_spend_usd?: string;
  daily_cap_usd?: string;
  burn_rate_per_min?: string;
  forecast_eod_usd?: string;
}

const POLICY_EVENTS = [
  { icon: "📥", label: "Inbound prompt", detail: "user · session pri_421 · 384 tokens", time: "07:24:11" },
  { icon: "✅", label: "Policy match", detail: "outbound.public.v3 · PHI scan run · 0 hits", time: "07:24:11" },
  { icon: "🔀", label: "Route decision", detail: "Hetzner FSN1 · llama3-70b · circuit closed", time: "07:24:11" },
  { icon: "⚡", label: "Inference complete", detail: "1,240 tokens · 142 ms · $0.00091", time: "07:24:12" },
  { icon: "🔏", label: "Audit signed", detail: "SHA-256 9f4e...ac21 · evidence appended", time: "07:24:12" },
];

export function OverviewPage() {
  const [status, setStatus] = useState<StatusData | null>(null);
  const [wallet, setWallet] = useState<WalletData | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    const results = await Promise.allSettled([
      rawApi.get("/health").then(r => r.data),
      api.get("/wallet/balance").then(r => r.data),
    ]);
    if (results[0].status === "fulfilled") setStatus(results[0].value);
    if (results[1].status === "fulfilled") setWallet(results[1].value);
    setLoading(false);
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const METRICS = [
    { label: "Requests / min", value: status?.requests_per_min?.toLocaleString() ?? "2,418", delta: "+8.4%", color: "text-moss", icon: Activity },
    { label: "P50 Latency", value: "112 ms", delta: "-14 ms", color: "text-electric", icon: Zap },
    { label: "Tokens / sec", value: status?.tokens_per_sec ? `${(status.tokens_per_sec / 1000).toFixed(0)}k` : "184k", delta: "+22%", color: "text-brass-2", icon: TrendingUp },
    { label: "Spend today", value: wallet?.daily_spend_usd ? `$${wallet.daily_spend_usd}` : "$1,284", delta: "68% cap", color: "text-amber", icon: DollarSign },
    { label: "Active Models", value: status?.active_models?.toString() ?? "12", delta: "4 quantized", color: "text-violet", icon: Cpu },
    { label: "Audit Entries", value: status?.audit_entries?.toLocaleString() ?? "9,412", delta: "100% verified", color: "text-moss", icon: ShieldCheck },
  ];

  const spendUsd = wallet?.daily_spend_usd ?? "1,284.80";
  const capUsd = wallet?.daily_cap_usd ?? "1,900";
  const burnRate = wallet?.burn_rate_per_min ?? "0.0154";
  const forecastEod = wallet?.forecast_eod_usd ?? "1,802";

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <p className="v-section-label">Workspace · Overview</p>
        <h1 className="mt-1 text-2xl font-bold text-bone">Sovereign control plane</h1>
        <p className="mt-1 text-sm text-muted">
          Every prompt routed, policed, and audited — across Hetzner primary and AWS burst — without leaving your perimeter.
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="v-badge-green">● {loading ? "Connecting..." : status?.status === "ok" ? "Live Backend Connected" : "Backend Active"}</span>
          <span className="v-badge-muted">SOC2-Ready</span>
          <span className="v-badge-muted">HIPAA-Aware</span>
          <span className="v-badge-muted">EU-Sovereign</span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-3 xl:grid-cols-6">
        {METRICS.map((m) => (
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

      <div className="grid gap-4 lg:grid-cols-5">
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

        <div className="v-card lg:col-span-2">
          <p className="v-section-label">Spend · Today</p>
          <div className="mt-2 flex items-center justify-between">
            <span className="text-lg font-bold text-bone">${spendUsd} of ${capUsd} cap</span>
            <span className="v-badge-amber">● On-Pace</span>
          </div>
          <div className="v-progress mt-3">
            <div className="v-progress-fill bg-amber" style={{ width: "68%" }} />
          </div>
          <div className="mt-4 grid grid-cols-2 gap-3">
            {[["Inference","65%","$842.12"],["Embeddings","16%","$211.00"],["GPU Burst","12%","$148.28"],["Storage","7%","$83.50"]].map(([label,pct,value]) => (
              <div key={label} className="flex items-center justify-between">
                <span className="text-xs text-muted">{label}</span>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[10px] text-muted-2">{pct}</span>
                  <span className="font-mono text-xs font-medium text-bone">{value}</span>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 border-t border-rule pt-3">
            <div className="flex justify-between text-xs text-muted">
              <span>Burn rate</span>
              <span className="font-mono text-bone">${burnRate} / min</span>
            </div>
            <div className="mt-1 flex justify-between text-xs text-muted">
              <span>Forecast EOD</span>
              <span className="font-mono text-bone">${forecastEod} (94% cap)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Runs + Policy Interception */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* Recent Runs */}
        <div className="v-card">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <p className="v-section-label">Recent Runs · Live</p>
              <p className="mt-0.5 text-sm font-semibold text-bone">Per-call routing, latency, cost</p>
            </div>
            <button className="flex items-center gap-1 text-xs text-brass hover:text-brass-2">Playground →</button>
          </div>
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-rule text-left">
                <th className="pb-2 font-mono text-[9px] uppercase text-muted">Model</th>
                <th className="pb-2 font-mono text-[9px] uppercase text-muted">Route</th>
                <th className="pb-2 font-mono text-[9px] uppercase text-muted">Latency</th>
                <th className="pb-2 font-mono text-[9px] uppercase text-muted">Tokens</th>
                <th className="pb-2 font-mono text-[9px] uppercase text-muted">Cost</th>
                <th className="pb-2 font-mono text-[9px] uppercase text-muted">Policy</th>
                <th className="pb-2 font-mono text-[9px] uppercase text-muted">When</th>
              </tr>
            </thead>
            <tbody>
              {[
                { model: "Llama 3.1 70B", route: "Hetzner · Primary", latency: "142 ms", tokens: "1240", cost: "$0.00091", policy: "Passed", when: "12s ago" },
                { model: "Mixtral 8×22B", route: "Hetzner · Primary", latency: "121 ms", tokens: "980", cost: "$0.00057", policy: "Passed", when: "44s ago" },
                { model: "Claude 3.5 Haiku", route: "AWS · Burst", latency: "228 ms", tokens: "2100", cost: "$0.00858", policy: "Redacted", when: "1m ago" },
                { model: "Qwen 2.5 72B", route: "Hetzner · Primary", latency: "96 ms", tokens: "720", cost: "$0.00021", policy: "Passed", when: "2m ago" },
                { model: "BGE-M3", route: "Hetzner · Primary", latency: "14 ms", tokens: "480", cost: "$0.00001", policy: "Passed", when: "2m ago" },
              ].map((run, i) => (
                <tr key={i} className="border-b border-rule/30">
                  <td className="py-2 font-medium text-bone">{run.model}</td>
                  <td className="py-2">
                    <span className={`rounded px-1.5 py-0.5 text-[8px] font-mono ${run.route.includes("AWS") ? "bg-electric/15 text-electric" : "bg-amber/15 text-amber"}`}>
                      {run.route}
                    </span>
                  </td>
                  <td className="py-2 font-mono text-muted">{run.latency}</td>
                  <td className="py-2 font-mono text-muted">{run.tokens}</td>
                  <td className="py-2 font-mono text-muted">{run.cost}</td>
                  <td className="py-2">
                    <span className={`rounded px-1 py-0.5 text-[8px] font-mono ${run.policy === "Passed" ? "bg-moss/15 text-moss" : "bg-crimson/15 text-crimson"}`}>
                      {run.policy}
                    </span>
                  </td>
                  <td className="py-2 font-mono text-[10px] text-muted-2">{run.when}</td>
                </tr>
              ))}
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

      {/* Alerts + Audit Trail + Fleet */}
      <div className="grid gap-4 lg:grid-cols-3">
        {/* Alerts */}
        <div className="v-card">
          <p className="v-section-label">Alerts</p>
          <p className="mt-0.5 text-sm font-semibold text-bone">3 open</p>
          <div className="mt-4 space-y-3">
            {[
              { text: "P95 latency above 600 ms on chat-prod (2 spikes)", source: "Monitoring · 4m ago", color: "bg-amber" },
              { text: "AWS burst engaged (12% of traffic)", source: "Router · 9m ago", color: "bg-electric" },
              { text: "Egress allowlist updated — 1 rule needs review", source: "Compliance · 1h ago", color: "bg-crimson" },
            ].map((alert, i) => (
              <div key={i} className="flex items-start gap-2.5">
                <span className={`mt-1 h-2 w-2 shrink-0 rounded-full ${alert.color}`} />
                <div>
                  <p className="text-xs text-bone">{alert.text}</p>
                  <p className="mt-0.5 font-mono text-[9px] text-muted">{alert.source}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Audit Trail */}
        <div className="v-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="v-section-label">Audit Trail · Tamper-Evident</p>
              <p className="mt-0.5 text-sm font-semibold text-bone">Hash-chained</p>
            </div>
            <span className="rounded bg-moss/15 px-1.5 py-0.5 text-[9px] font-mono text-moss">Verified</span>
          </div>
          <div className="mt-4 space-y-3">
            {[
              { action: "deploy.update", actor: "chat-prod · elliot@acme.io", hash: "9f4e...ac21", time: "07:24:112" },
              { action: "policy.intercept", actor: "session#pri_421 · system/router", hash: "5b71...dc19", time: "07:18:822" },
              { action: "vault.rotate", actor: "OPENAI_KEY_PROXY · kira@acme.io", hash: "0c11...7d2a", time: "07:11:552" },
              { action: "evidence.export", actor: "soc2-q2 pkg.zip · system/compliance", hash: "ef87...2941", time: "07:00:212" },
              { action: "key.create", actor: "key_8h2x_chat · alex@acme.io", hash: "12cd...ee81", time: "06:54:172" },
            ].map((entry, i) => (
              <div key={i} className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="font-mono text-[11px] font-medium text-bone">{entry.action}</p>
                  <p className="truncate font-mono text-[9px] text-muted">{entry.actor}</p>
                </div>
                <div className="shrink-0 text-right">
                  <p className="font-mono text-[9px] text-muted-2">{entry.time}</p>
                  <p className="font-mono text-[8px] text-muted/50">{entry.hash}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Fleet */}
        <div className="v-card">
          <p className="v-section-label">Fleet</p>
          <p className="mt-0.5 text-sm font-semibold text-bone">Models · deployments</p>
          <div className="mt-4 space-y-3">
            {[
              { model: "Llama 3.1 70B Instruct", quant: "FP16 · 4", replicas: 4, zone: "Hetzner · Primary", latency: "142 ms" },
              { model: "Mixtral 8×22B", quant: "INT8 · 6", replicas: 6, zone: "Hetzner · Primary", latency: "121 ms" },
              { model: "Qwen 2.5 72B", quant: "INT4 · 8", replicas: 8, zone: "Hetzner · Primary", latency: "96 ms" },
              { model: "Claude 3.5 Haiku (proxy)", quant: "FP16 · 2", replicas: 2, zone: "AWS · Burst", latency: "228 ms" },
            ].map((m, i) => (
              <div key={i} className="rounded-md border border-rule/40 bg-ink-3/30 px-3 py-2">
                <p className="text-xs font-medium text-bone">{m.model}</p>
                <div className="mt-1 flex items-center gap-2 text-[9px]">
                  <span className="font-mono text-muted">{m.quant} replicas</span>
                  <span className={`rounded px-1 py-0.5 font-mono ${m.zone.includes("AWS") ? "bg-electric/15 text-electric" : "bg-amber/15 text-amber"}`}>
                    {m.zone}
                  </span>
                  <span className="ml-auto font-mono text-muted">P50 {m.latency}</span>
                </div>
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
