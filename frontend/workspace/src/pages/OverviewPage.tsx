import { Activity, Zap, DollarSign, Cpu, ShieldCheck, TrendingUp } from "lucide-react";
import { MiniChart } from "@/components/MiniChart";

const METRICS = [
  { label: "Requests / min", value: "2,418", delta: "+8.4%", color: "text-moss", icon: Activity },
  { label: "P50 Latency", value: "112 ms", delta: "-14 ms", color: "text-electric", icon: Zap },
  { label: "Tokens / sec", value: "184k", delta: "+22%", color: "text-brass-2", icon: TrendingUp },
  { label: "Spend today", value: "$1,284", delta: "68% cap", color: "text-amber", icon: DollarSign },
  { label: "Active Models", value: "12", delta: "4 quantized", color: "text-violet", icon: Cpu },
  { label: "Audit Entries", value: "9,412", delta: "100% verified", color: "text-moss", icon: ShieldCheck },
];

const RECENT_RUNS = [
  { model: "Llama 3.1 70B", route: "HETZNER", routeType: "PRIMARY", latency: "142 ms", tokens: 1240, cost: "$0.00091", policy: "PASSED", when: "12s ago" },
  { model: "Mixtral 8×22B", route: "HETZNER", routeType: "PRIMARY", latency: "121 ms", tokens: 980, cost: "$0.00057", policy: "PASSED", when: "44s ago" },
  { model: "Claude 3.5 Haiku", route: "AWS", routeType: "BURST", latency: "228 ms", tokens: 2100, cost: "$0.00868", policy: "REDACTED", when: "1m ago" },
  { model: "Qwen 2.5 72B", route: "HETZNER", routeType: "PRIMARY", latency: "96 ms", tokens: 720, cost: "$0.00021", policy: "PASSED", when: "2m ago" },
  { model: "BGE-M3", route: "HETZNER", routeType: "PRIMARY", latency: "14 ms", tokens: 480, cost: "$0.00001", policy: "PASSED", when: "2m ago" },
];

const POLICY_EVENTS = [
  { icon: "📥", label: "Inbound prompt", detail: "user · session pri_421 · 384 tokens", time: "07:24:11" },
  { icon: "✅", label: "Policy match", detail: "outbound.public.v3 · PHI scan run · 0 hits", time: "07:24:11" },
  { icon: "🔀", label: "Route decision", detail: "Hetzner FSN1 · llama3-70b · circuit closed", time: "07:24:11" },
  { icon: "⚡", label: "Inference complete", detail: "1,240 tokens · 142 ms · $0.00091", time: "07:24:12" },
  { icon: "🔏", label: "Audit signed", detail: "SHA-256 9f4e...ac21 · evidence appended", time: "07:24:12" },
];

export function OverviewPage() {
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
          <span className="v-badge-green">● Live Backend Connected</span>
          <span className="v-badge-muted">SOC2-Ready</span>
          <span className="v-badge-muted">HIPAA-Aware</span>
          <span className="v-badge-muted">EU-Sovereign</span>
        </div>
      </div>

      {/* Metrics row */}
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
          <p className="v-section-label">Spend · Today</p>
          <div className="mt-2 flex items-center justify-between">
            <span className="text-lg font-bold text-bone">$1,284.80 of $1,900 cap</span>
            <span className="v-badge-amber">● On-Pace</span>
          </div>
          <div className="v-progress mt-3">
            <div className="v-progress-fill bg-amber" style={{ width: "68%" }} />
          </div>
          <div className="mt-4 grid grid-cols-2 gap-3">
            <SpendItem label="Inference" pct="65%" value="$842.12" />
            <SpendItem label="Embeddings" pct="16%" value="$211.00" />
            <SpendItem label="GPU Burst" pct="12%" value="$148.28" />
            <SpendItem label="Storage" pct="7%" value="$83.50" />
          </div>
          <div className="mt-4 border-t border-rule pt-3">
            <div className="flex justify-between text-xs text-muted">
              <span>Burn rate</span>
              <span className="font-mono text-bone">$0.0154 / min</span>
            </div>
            <div className="mt-1 flex justify-between text-xs text-muted">
              <span>Forecast EOD</span>
              <span className="font-mono text-bone">$1,802 (94% cap)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom grid */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* Recent Runs */}
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
                <th className="px-2 py-2 font-mono text-[9px] uppercase text-muted">Route</th>
                <th className="px-2 py-2 font-mono text-[9px] uppercase text-muted">Latency</th>
                <th className="px-2 py-2 font-mono text-[9px] uppercase text-muted">Tokens</th>
                <th className="px-2 py-2 font-mono text-[9px] uppercase text-muted">Cost</th>
                <th className="px-2 py-2 font-mono text-[9px] uppercase text-muted">Policy</th>
                <th className="px-2 py-2 font-mono text-[9px] uppercase text-muted">When</th>
              </tr>
            </thead>
            <tbody>
              {RECENT_RUNS.map((r, i) => (
                <tr key={i} className="border-b border-rule/50 hover:bg-ink-3/40">
                  <td className="px-4 py-2 font-medium text-bone">{r.model}</td>
                  <td className="px-2 py-2">
                    <span className={`rounded px-1.5 py-0.5 font-mono text-[9px] ${r.routeType === "PRIMARY" ? "bg-amber/15 text-amber" : "bg-electric/15 text-electric"}`}>
                      {r.route} · {r.routeType}
                    </span>
                  </td>
                  <td className="px-2 py-2 font-mono text-bone-2">{r.latency}</td>
                  <td className="px-2 py-2 font-mono text-bone-2">{r.tokens}</td>
                  <td className="px-2 py-2 font-mono text-bone-2">{r.cost}</td>
                  <td className="px-2 py-2">
                    <span className={`v-badge ${r.policy === "PASSED" ? "v-badge-green" : "v-badge-crimson"}`}>{r.policy}</span>
                  </td>
                  <td className="px-2 py-2 text-muted">{r.when}</td>
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
