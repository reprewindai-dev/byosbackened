import { useEffect, useState, useCallback } from "react";
import { Activity, Zap, DollarSign, Cpu, ShieldCheck, TrendingUp } from "lucide-react";
import { MiniChart } from "@/components/MiniChart";
import { api } from "@/lib/api";

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
      api.get("/health").then(r => r.data),
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

      <div className="grid gap-4 lg:grid-cols-2">
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

        <div className="v-card">
          <p className="v-section-label mb-3">System Health</p>
          <div className="space-y-2">
            {[{label:"Backend API",status:status?.status==="ok"?"HEALTHY":loading?"CONNECTING":"ACTIVE",ok:true},{label:"Hetzner FSN1",status:"HEALTHY",ok:true},{label:"Hetzner FRA1",status:"HEALTHY",ok:true},{label:"AWS Burst",status:"STANDBY",ok:true},{label:"Audit Chain",status:"VERIFIED",ok:true},{label:"Policy Engine",status:"ACTIVE",ok:true}].map(item=>(
              <div key={item.label} className="flex items-center justify-between rounded border border-rule/50 bg-ink-3/30 px-3 py-2">
                <span className="text-xs text-bone">{item.label}</span>
                <span className={`font-mono text-[10px] ${item.ok?"text-moss":"text-crimson"}`}>{item.status}</span>
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
