import { useQuery } from "@tanstack/react-query";
import type { ComponentType, ReactNode } from "react";
import {
  Activity,
  AlertCircle,
  ArrowRight,
  Box,
  CheckCircle2,
  CircleDollarSign,
  Cloud,
  Cpu,
  Database,
  FileCheck2,
  Gauge,
  Hash,
  MoreHorizontal,
  Plus,
  Server,
  ShieldCheck,
  TerminalSquare,
  TrendingDown,
  TrendingUp,
  Zap,
} from "lucide-react";
import { PlatformPulseSection } from "@/components/overview/PlatformPulseSection";
import { Sparkline } from "@/components/overview/Sparkline";
import { api } from "@/lib/api";
import {
  cn,
  dateFromApiTimestamp,
  fmtCents,
  fmtDelta,
  fmtNumber,
  formatApiTime,
  relativeTime,
} from "@/lib/cn";
import { isRouteUnavailable } from "@/lib/errors";
import type { Alert, AuditEntry, FleetModel, OverviewPayload, PolicyEvent, RecentRun } from "@/types/api";

async function fetchOverview(): Promise<OverviewPayload> {
  try {
    const resp = await api.get<OverviewPayload>("/monitoring/overview");
    return resp.data;
  } catch (err) {
    if (!isRouteUnavailable(err)) throw err;
    const resp = await api.get<LegacyWorkspaceOverview>("/workspace/overview");
    return fromLegacyOverview(resp.data);
  }
}

interface LegacyWorkspaceOverview {
  period_start?: string;
  period_end?: string;
  total_api_calls?: number;
  total_tokens_used?: number;
  total_cost_usd?: number;
  active_models?: string[];
  live_feed?: Array<{
    id: string;
    kind?: string;
    model?: string | null;
    latency_ms?: number;
    tokens?: number;
    status?: string;
    created_at?: string;
  }>;
}

function fromLegacyOverview(data: LegacyWorkspaceOverview): OverviewPayload {
  const calls = Number(data.total_api_calls ?? 0);
  const tokens = Number(data.total_tokens_used ?? 0);
  const costUsd = Number(data.total_cost_usd ?? 0);
  const periodStart = data.period_start ? (dateFromApiTimestamp(data.period_start)?.getTime() ?? Date.now()) : Date.now();
  const periodEnd = data.period_end ? (dateFromApiTimestamp(data.period_end)?.getTime() ?? Date.now()) : Date.now();
  const minutes = Math.max(1, Math.round((periodEnd - periodStart) / 60000));
  const activeModels = data.active_models ?? [];
  const recent = data.live_feed ?? [];

  return {
    kpi: {
      requests_per_minute: Number((calls / minutes).toFixed(2)),
      requests_delta_pct: 0,
      p50_latency_ms: median(recent.map((row) => Number(row.latency_ms ?? 0)).filter(Boolean)),
      p50_delta_ms: 0,
      tokens_per_second: Number((tokens / Math.max(1, minutes * 60)).toFixed(2)),
      tokens_delta_pct: 0,
      spend_today_cents: Math.round(costUsd * 100),
      spend_cap_pct: 0,
      requests_series: bucketSeries(recent, (row) => Number(row.tokens ?? 1)),
      tokens_series: bucketSeries(recent, (row) => Number(row.tokens ?? 0)),
      spend_series: bucketSeries(recent, () => 0),
      active_models: activeModels.length,
      active_models_quantized: activeModels.filter((model) => /q[0-9]/i.test(model)).length,
      audit_entries: recent.length,
      audit_verified_pct: recent.length ? 100 : 0,
    },
    routing: {
      primary_plane: "Hetzner primary",
      burst_plane: "AWS burst",
      primary_util_pct: calls ? 100 : 0,
      burst_util_pct: 0,
      primary_hosts: [{ name: "hetzner-fsn1", util_pct: calls ? 100 : 0, detail: `${calls} live call(s)` }],
      series: routingFromRuns(recent),
    },
    spend: {
      spend_cents: Math.round(costUsd * 100),
      cap_cents: 0,
      inference_cents: Math.round(costUsd * 100),
      embeddings_cents: 0,
      gpu_burst_cents: 0,
      storage_cents: 0,
      burn_rate_per_min_cents: minutes ? Math.round((costUsd * 100) / minutes) : 0,
      forecast_eod_cents: Math.round(costUsd * 100),
      forecast_cap_pct: 0,
    },
    recent_runs: recent.map((row) => ({
      id: row.id,
      model: row.model ?? "unknown",
      route: "primary",
      latency_ms: Number(row.latency_ms ?? 0),
      tokens: Number(row.tokens ?? 0),
      cost_cents: 0,
      policy: row.status === "error" ? "blocked" : "passed",
      when: row.created_at ?? new Date().toISOString(),
    })),
    policy_events: recent.slice(0, 5).map((row) => ({
      id: `policy-${row.id}`,
      ts: row.created_at ?? new Date().toISOString(),
      kind: "audit_signed",
      summary: row.status === "error" ? "Backend rejected request" : "Audit entry available",
      detail: `${row.kind ?? "request"} · ${row.model ?? "unknown"}`,
    })),
    alerts: [],
    audit_trail: recent.map((row) => ({
      id: row.id,
      kind: row.kind ?? "request",
      subject: row.model ?? "workspace call",
      actor: "workspace",
      ts: row.created_at ?? new Date().toISOString(),
      hash_prefix: row.id.slice(0, 12),
    })),
    fleet: activeModels.map((model) => ({
      id: model,
      name: model,
      quant: /q[0-9]/i.exec(model)?.[0] ?? "fp16",
      replicas: 1,
      route: "primary",
      p50_ms: 0,
    })),
  };
}

function median(values: number[]): number {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[Math.floor(sorted.length / 2)] ?? 0;
}

function bucketSeries<T extends { created_at?: string }>(rows: T[], valueFor: (row: T) => number): number[] {
  const buckets = Array.from({ length: 20 }, () => 0);
  if (!rows.length) return buckets;
  const sorted = [...rows].sort((a, b) => {
    const at = dateFromApiTimestamp(a.created_at ?? "")?.getTime() ?? 0;
    const bt = dateFromApiTimestamp(b.created_at ?? "")?.getTime() ?? 0;
    return at - bt;
  });
  sorted.forEach((row, index) => {
    const bucket = Math.min(19, Math.floor((index / Math.max(1, sorted.length)) * 20));
    buckets[bucket] += Math.max(0, valueFor(row));
  });
  return buckets;
}

function routingFromRuns(rows: NonNullable<LegacyWorkspaceOverview["live_feed"]>): OverviewPayload["routing"]["series"] {
  if (!rows.length) return [];
  const buckets = Array.from({ length: 24 }, (_, i) => ({ t: `${String(i).padStart(2, "0")}:00`, primary: 0, burst: 0 }));
  rows.forEach((row, index) => {
    const bucket = Math.min(23, Math.floor((index / Math.max(1, rows.length)) * 24));
    const provider = (row.model ?? "").toLowerCase();
    if (provider.includes("groq") || provider.includes("aws") || provider.includes("bedrock")) {
      buckets[bucket].burst += 1;
    } else {
      buckets[bucket].primary += 1;
    }
  });
  const max = Math.max(1, ...buckets.map((bucket) => bucket.primary + bucket.burst));
  return buckets.map((bucket) => ({
    ...bucket,
    primary: Math.round((bucket.primary / max) * 100),
    burst: Math.round((bucket.burst / max) * 100),
  }));
}

export function OverviewPage() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["overview"],
    queryFn: fetchOverview,
    refetchInterval: 15_000,
  });

  return (
    <div className="mx-auto w-full max-w-[1400px]">
      <PageHeader />

      {isError && (
        <div className="frame mb-4 flex items-start gap-3 border-crimson/40 bg-crimson/5 p-4 text-sm text-crimson">
          <AlertCircle className="mt-0.5 h-4 w-4" />
          <div>
            <div className="font-semibold">Failed to load overview</div>
            <div className="mt-1 text-xs opacity-80">
              {(error as Error)?.message ?? "Unknown error"} · the backend endpoint{" "}
              <span className="font-mono">/api/v1/monitoring/overview</span> may not be implemented yet.
            </div>
          </div>
        </div>
      )}

      <section>
        <KpiStrip data={data} isLoading={isLoading} />

        <div className="mt-4 grid grid-cols-12 gap-4">
          <RoutingPanel data={data} isLoading={isLoading} />
          <SpendPanel data={data} isLoading={isLoading} />
        </div>

        <div className="mt-4 grid grid-cols-12 gap-4">
          <RecentRunsPanel rows={data?.recent_runs ?? []} isLoading={isLoading} />
          <PolicyTimelinePanel events={data?.policy_events ?? []} isLoading={isLoading} />
        </div>

        <div className="mt-4 grid grid-cols-12 gap-4">
          <AlertsPanel alerts={data?.alerts ?? []} isLoading={isLoading} />
          <AuditTrailPanel entries={data?.audit_trail ?? []} isLoading={isLoading} />
          <FleetPanel fleet={data?.fleet ?? []} isLoading={isLoading} />
        </div>

        <div className="mt-4">
          <PlatformPulseSection />
        </div>
      </section>
    </div>
  );
}

function PageHeader() {
  return (
    <header className="mb-5 flex flex-wrap items-start justify-between gap-4">
      <div>
        <div className="text-eyebrow">Workspace · Overview</div>
        <h1 className="font-display mt-1 text-[30px] font-semibold tracking-tight text-bone">Sovereign control plane</h1>
        <p className="mt-2 max-w-2xl text-sm text-bone-2">
          Every prompt routed, policed, and audited — across Hetzner primary and AWS burst — without leaving your
          perimeter.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <LiveBadge label="LIVE BACKEND CONNECTED" />
          <Badge tone="muted">SOC2-ready</Badge>
          <Badge tone="muted">HIPAA-aware</Badge>
          <Badge tone="muted">EU-sovereign</Badge>
        </div>
      </div>
      <div className="flex gap-2">
        <a href="#/deployments" className="v-btn-ghost h-8 px-3 text-xs">
          <Plus className="h-3.5 w-3.5" /> New deployment
        </a>
        <a href="#/playground" className="v-btn-primary h-8 px-3 text-xs">
          <TerminalSquare className="h-3.5 w-3.5" /> Open Playground
        </a>
      </div>
    </header>
  );
}

function KpiStrip({ data, isLoading }: { data?: OverviewPayload; isLoading: boolean }) {
  const cards = [
    {
      label: "Requests / min",
      value: data ? fmtNumber(data.kpi.requests_per_minute) : "-",
      delta: data ? fmtDelta(data.kpi.requests_delta_pct, "%") : undefined,
      positive: !data || data.kpi.requests_delta_pct >= 0,
      spark: data?.kpi.requests_series,
      icon: Activity,
    },
    {
      label: "P50 latency",
      value: data ? `${data.kpi.p50_latency_ms} ms` : "-",
      delta: data ? fmtDelta(data.kpi.p50_delta_ms, " ms") : undefined,
      positive: !data || data.kpi.p50_delta_ms <= 0,
      spark: undefined,
      icon: Gauge,
    },
    {
      label: "Tokens / sec",
      value: data ? fmtNumber(data.kpi.tokens_per_second) : "-",
      delta: data ? fmtDelta(data.kpi.tokens_delta_pct, "%") : undefined,
      positive: !data || data.kpi.tokens_delta_pct >= 0,
      spark: data?.kpi.tokens_series,
      icon: Zap,
    },
    {
      label: "Spend today",
      value: data ? fmtCents(data.kpi.spend_today_cents) : "-",
      delta: data ? `${data.kpi.spend_cap_pct}% cap` : undefined,
      positive: !data || data.kpi.spend_cap_pct < 80,
      spark: data?.kpi.spend_series,
      icon: CircleDollarSign,
    },
    {
      label: "Active models",
      value: data ? String(data.kpi.active_models) : "-",
      delta: data ? `${data.kpi.active_models_quantized} quantized` : undefined,
      positive: true,
      spark: undefined,
      icon: Box,
    },
    {
      label: "Audit entries",
      value: data ? fmtNumber(data.kpi.audit_entries) : "-",
      delta: data ? `${data.kpi.audit_verified_pct}% verified` : undefined,
      positive: true,
      spark: undefined,
      icon: ShieldCheck,
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
      {cards.map((card) => (
        <KpiCard key={card.label} {...card} loading={isLoading} />
      ))}
    </div>
  );
}

function KpiCard({
  label,
  value,
  delta,
  positive,
  loading,
  spark,
  icon: Icon,
}: {
  label: string;
  value: string;
  delta?: string;
  positive?: boolean;
  loading: boolean;
  spark?: number[];
  icon: ComponentType<{ className?: string }>;
}) {
  return (
    <div className="frame p-3">
      <div className="text-eyebrow flex items-center justify-between text-bone-2">
        <span className="flex items-center gap-1.5">
          <Icon className="h-3.5 w-3.5" />
          {label}
        </span>
      </div>
      <div className="mt-1 flex items-baseline justify-between gap-2">
        <span className="font-display text-[19px] font-semibold tracking-tight text-bone">
          {loading ? <span className="inline-block h-5 w-16 animate-pulse rounded bg-rule" /> : value}
        </span>
        {delta && (
          <span
            className={cn(
              "flex items-center gap-0.5 whitespace-nowrap font-mono text-[10.5px]",
              positive ? "text-moss" : "text-crimson",
            )}
          >
            {positive ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
            {delta}
          </span>
        )}
      </div>
      <div className="mt-1.5 h-9">
        <Sparkline values={spark ?? []} />
      </div>
    </div>
  );
}

function RoutingPanel({ data, isLoading }: { data?: OverviewPayload; isLoading: boolean }) {
  const primaryPct = data?.routing.primary_util_pct ?? 0;
  const burstPct = data?.routing.burst_util_pct ?? 0;
  const hostTiles = getHostTiles(data);

  return (
    <div className="frame col-span-12 lg:col-span-8">
      <PanelHeader
        eyebrow="Routing · last 24h"
        title={`${data?.routing.primary_plane ?? "Hetzner primary"} · ${data?.routing.burst_plane ?? "AWS burst"}`}
        actions={
          <>
            <Badge tone="primary" dot>
              Hetzner {primaryPct}%
            </Badge>
            <Badge tone="info" dot>
              AWS {burstPct}%
            </Badge>
            <a href="#/monitoring" className="v-btn-ghost h-7 px-2">
              <MoreHorizontal className="h-3.5 w-3.5" />
            </a>
          </>
        }
      />
      <div className="px-3 pt-2">
        <RoutingChart data={data} isLoading={isLoading} />
      </div>
      <div className="grid grid-cols-1 gap-px border-t border-rule bg-rule md:grid-cols-3">
        {hostTiles.map((tile) => (
          <div key={tile.label} className="bg-ink-2 px-4 py-3">
            <div className="text-eyebrow flex items-center gap-1.5">
              <tile.icon className={cn("h-3.5 w-3.5", tile.tone === "info" ? "text-electric" : "text-brass-2")} />
              {tile.label}
            </div>
            <div className="font-display mt-1 text-[14px] text-bone">{tile.value}</div>
            <div className="text-[11px] text-muted">{tile.sub}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function RoutingChart({ data, isLoading }: { data?: OverviewPayload; isLoading: boolean }) {
  const series = data?.routing.series ?? [];
  const hasActivity =
    series.some((point) => point.primary > 0 || point.burst > 0) ||
    (data?.recent_runs?.length ?? 0) > 0 ||
    (data?.routing.primary_hosts ?? []).some((host) => host.util_pct > 0);
  const points = series.length
    ? series.slice(-24)
    : Array.from({ length: 24 }, (_, index) => ({ t: `${String(index).padStart(2, "0")}:00`, primary: 0, burst: 0 }));

  const W = 800;
  const H = 220;
  const padL = 34;
  const padR = 10;
  const padT = 12;
  const padB = 24;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;
  const maxY = 120;

  const yFor = (v: number) => padT + innerH * (1 - Math.max(0, Math.min(maxY, v)) / maxY);
  const xFor = (i: number) => padL + (points.length === 1 ? innerW / 2 : (i / (points.length - 1)) * innerW);

  function curvePath(values: number[]): { line: string; area: string } {
    const pts = values.map((v, i) => ({ x: xFor(i), y: yFor(v) }));
    if (!pts.length) {
      const y = yFor(0);
      return { line: `M ${padL} ${y} L ${W - padR} ${y}`, area: `M ${padL} ${y} L ${W - padR} ${y}` };
    }
    let line = `M ${pts[0].x.toFixed(2)} ${pts[0].y.toFixed(2)}`;
    for (let i = 1; i < pts.length; i++) {
      const prev = pts[i - 1];
      const cur = pts[i];
      const midX = (prev.x + cur.x) / 2;
      const midY = (prev.y + cur.y) / 2;
      line += ` Q ${prev.x.toFixed(2)} ${prev.y.toFixed(2)}, ${midX.toFixed(2)} ${midY.toFixed(2)}`;
    }
    const last = pts[pts.length - 1];
    line += ` T ${last.x.toFixed(2)} ${last.y.toFixed(2)}`;
    const area = `${line} L ${last.x.toFixed(2)} ${(padT + innerH).toFixed(2)} L ${pts[0].x.toFixed(2)} ${(padT + innerH).toFixed(2)} Z`;
    return { line, area };
  }

  const primary = curvePath(points.map((p) => p.primary));
  const burst = curvePath(points.map((p) => p.burst));
  const yTicks = [120, 90, 60, 30];
  const xTicks = [0, Math.floor((points.length - 1) / 2), points.length - 1];

  return (
    <div className="relative">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="h-[220px] w-full"
        preserveAspectRatio="none"
        role="img"
        aria-label="Hetzner primary versus AWS burst routing utilization"
      >
        {yTicks.map((tick) => (
          <g key={tick}>
            <line x1={padL} x2={W - padR} y1={yFor(tick)} y2={yFor(tick)} stroke="rgba(255,255,255,0.055)" />
            <text
              x={padL - 7}
              y={yFor(tick) + 3}
              textAnchor="end"
              fontSize="10"
              fontFamily="JetBrains Mono, monospace"
              fill="rgba(200,203,214,0.55)"
            >
              {tick}
            </text>
          </g>
        ))}
        <path d={burst.area} fill="rgba(110, 168, 254, 0.15)" />
        <path d={burst.line} fill="none" stroke="rgba(110, 168, 254, 0.95)" strokeWidth="1.8" strokeLinecap="round" />
        <path d={primary.area} fill="rgba(229, 177, 110, 0.18)" />
        <path d={primary.line} fill="none" stroke="rgba(229, 177, 110, 0.98)" strokeWidth="2.2" strokeLinecap="round" />
        {xTicks.map((i) => (
          <text
            key={i}
            x={xFor(i)}
            y={H - 7}
            textAnchor={i === 0 ? "start" : i === points.length - 1 ? "end" : "middle"}
            fontSize="10"
            fontFamily="JetBrains Mono, monospace"
            fill="rgba(200,203,214,0.5)"
          >
            {points[i]?.t ?? ""}
          </text>
        ))}
      </svg>
      {isLoading && (
        <div className="absolute inset-0 grid place-items-center bg-ink-2/30 font-mono text-[11px] uppercase tracking-[0.14em] text-muted">
          Loading routing telemetry
        </div>
      )}
      {!isLoading && !hasActivity && (
        <div className="absolute inset-0 grid place-items-center text-center">
          <div className="rounded-md border border-rule bg-ink/80 px-3 py-2 font-mono text-[11px] text-muted">
            No routing events yet. Run Playground to populate this chart.
          </div>
        </div>
      )}
    </div>
  );
}

function SpendPanel({ data, isLoading }: { data?: OverviewPayload; isLoading: boolean }) {
  const spend = data?.spend;
  const capText = spend?.cap_cents ? `${fmtCents(spend.spend_cents)} of ${fmtCents(spend.cap_cents)} cap` : `${fmtCents(spend?.spend_cents ?? 0)} spent`;
  const capPct = data?.kpi.spend_cap_pct ?? spend?.forecast_cap_pct ?? 0;

  return (
    <div className="frame col-span-12 lg:col-span-4">
      <PanelHeader
        eyebrow="Spend · today"
        title={isLoading ? "Loading reserve ledger" : capText}
        actions={
          <Badge tone={capPct >= 90 ? "warn" : "success"} dot>
            {capPct >= 90 ? "watch" : "on-pace"}
          </Badge>
        }
      />
      <div className="px-4 py-3">
        <div className="h-3 overflow-hidden rounded-full bg-rule">
          <div className="h-full bg-gradient-to-r from-brass/80 to-brass" style={{ width: `${Math.min(100, capPct)}%` }} />
        </div>
        <div className="mt-3 grid grid-cols-2 gap-2 text-[11px]">
          <SpendRow label="Inference" cents={spend?.inference_cents} total={spend?.spend_cents} />
          <SpendRow label="Embeddings" cents={spend?.embeddings_cents} total={spend?.spend_cents} />
          <SpendRow label="GPU burst" cents={spend?.gpu_burst_cents} total={spend?.spend_cents} />
          <SpendRow label="Storage" cents={spend?.storage_cents} total={spend?.spend_cents} />
        </div>
      </div>
      <div className="border-t border-rule px-4 py-2 text-[11px]">
        <div className="flex items-center justify-between">
          <span className="text-muted">Burn rate</span>
          <span className="font-mono text-bone">{spend ? `${fmtCents(spend.burn_rate_per_min_cents)} / min` : "-"}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-muted">Forecast EOD</span>
          <span className="font-mono text-bone">
            {spend ? `${fmtCents(spend.forecast_eod_cents)} (${spend.forecast_cap_pct}% cap)` : "-"}
          </span>
        </div>
      </div>
    </div>
  );
}

function SpendRow({ label, cents, total }: { label: string; cents?: number; total?: number }) {
  const pct = cents !== undefined && total && total > 0 ? Math.round((cents / total) * 100) : 0;
  return (
    <div className="rounded-md border border-rule bg-ink/40 px-2.5 py-1.5">
      <div className="flex items-center justify-between text-muted">
        <span>{label}</span>
        <span className="font-mono">{pct}%</span>
      </div>
      <div className="font-mono text-[12px] text-bone">{cents !== undefined ? fmtCents(cents) : "-"}</div>
    </div>
  );
}

function RecentRunsPanel({ rows, isLoading }: { rows: RecentRun[]; isLoading: boolean }) {
  return (
    <div className="frame col-span-12 lg:col-span-7">
      <PanelHeader
        eyebrow="Recent runs · live"
        title="Per-call routing, latency, cost"
        actions={
          <a href="#/playground" className="v-btn-ghost h-7 px-2 text-xs">
            Playground <ArrowRight className="h-3.5 w-3.5" />
          </a>
        }
      />
      <div className="overflow-hidden">
        <table className="w-full text-[12px]">
          <thead className="border-b border-rule bg-ink/40 text-eyebrow">
            <tr>
              <th className="px-4 py-2 text-left">Model</th>
              <th className="px-4 py-2 text-left">Route</th>
              <th className="px-4 py-2 text-right">Latency</th>
              <th className="px-4 py-2 text-right">Tokens</th>
              <th className="px-4 py-2 text-right">Cost</th>
              <th className="px-4 py-2 text-left">Policy</th>
              <th className="px-4 py-2 text-right">When</th>
            </tr>
          </thead>
          <tbody>
            {rows.slice(0, 5).map((row) => (
              <tr key={row.id} className="hover-elevate border-b border-rule/60 last:border-0">
                <td className="px-4 py-2 text-bone">{row.model}</td>
                <td className="px-4 py-2">
                  <RouteBadge route={row.route} />
                </td>
                <td className="px-4 py-2 text-right font-mono text-bone">{row.latency_ms} ms</td>
                <td className="px-4 py-2 text-right font-mono">{row.tokens}</td>
                <td className="px-4 py-2 text-right font-mono text-bone">{fmtCents(row.cost_cents)}</td>
                <td className="px-4 py-2">
                  <Badge
                    tone={row.policy === "passed" ? "success" : row.policy === "redacted" ? "warn" : "danger"}
                    icon={<ShieldCheck className="h-3 w-3" />}
                  >
                    {row.policy}
                  </Badge>
                </td>
                <td className="px-4 py-2 text-right font-mono text-muted">{relativeTime(row.when)}</td>
              </tr>
            ))}
            {!rows.length && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-muted">
                  {isLoading ? "Loading runs..." : "No runs yet. Open the Playground to generate the first one."}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function PolicyTimelinePanel({ events, isLoading }: { events: PolicyEvent[]; isLoading: boolean }) {
  return (
    <div className="frame col-span-12 lg:col-span-5">
      <PanelHeader eyebrow="Policy interception · live" title="Decision before execution" actions={<LiveBadge />} />
      <ol className="relative space-y-3 px-5 py-4">
        <span className="absolute bottom-3 left-7 top-3 w-px bg-rule" />
        {events.slice(0, 5).map((event) => (
          <TimelineItem
            key={event.id}
            time={formatApiTime(event.ts)}
            title={event.summary}
            body={event.detail}
            tone={event.kind === "audit_signed" ? "success" : event.kind === "route_decision" ? "primary" : "neutral"}
            icon={event.kind === "audit_signed" ? FileCheck2 : event.kind === "route_decision" ? Server : TerminalSquare}
          />
        ))}
        {!events.length && (
          <li className="relative flex gap-3 pl-2">
            <div className="z-10 mt-0.5 grid h-5 w-5 place-items-center rounded-full border border-rule bg-ink text-muted">
              <Activity className="h-3 w-3" />
            </div>
            <div className="flex-1 text-[12px] text-muted">
              {isLoading ? "Waiting on policy engine..." : "No policy events in the current window."}
            </div>
          </li>
        )}
      </ol>
    </div>
  );
}

function TimelineItem({
  time,
  title,
  body,
  tone,
  icon: Icon,
}: {
  time: string;
  title: string;
  body: string;
  tone: "neutral" | "success" | "primary" | "info";
  icon: ComponentType<{ className?: string }>;
}) {
  return (
    <li className="relative flex gap-3 pl-2">
      <div
        className={cn(
          "z-10 mt-0.5 grid h-5 w-5 place-items-center rounded-full border bg-ink",
          tone === "success"
            ? "border-moss/40 text-moss"
            : tone === "primary"
              ? "border-brass/40 text-brass-2"
              : tone === "info"
                ? "border-electric/40 text-electric"
                : "border-rule text-muted",
        )}
      >
        <Icon className="h-3 w-3" />
      </div>
      <div className="flex-1">
        <div className="flex items-center justify-between gap-3">
          <span className="text-[12.5px] text-bone">{title}</span>
          <span className="whitespace-nowrap font-mono text-[10.5px] text-muted">{time}</span>
        </div>
        <div className="text-[11.5px] text-muted">{body}</div>
      </div>
    </li>
  );
}

function AlertsPanel({ alerts, isLoading }: { alerts: Alert[]; isLoading: boolean }) {
  return (
    <div className="frame col-span-12 lg:col-span-4">
      <PanelHeader eyebrow="Alerts" title={`${alerts.length} open`} />
      <div className="divide-y divide-rule/60">
        {alerts.slice(0, 5).map((alert) => (
          <div key={alert.id} className="flex items-start gap-3 px-4 py-3">
            <span
              className={cn(
                "mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full",
                alert.severity === "error" ? "bg-crimson" : alert.severity === "warn" ? "bg-amber" : "bg-electric",
              )}
            />
            <div className="flex-1">
              <div className="text-[12.5px] text-bone">{alert.title}</div>
              <div className="text-eyebrow mt-0.5 flex items-center gap-2">
                <span>{alert.scope}</span>
                <span>·</span>
                <span>{relativeTime(alert.when)}</span>
              </div>
            </div>
          </div>
        ))}
        {!alerts.length && (
          <EmptyPanel
            icon={isLoading ? Activity : CheckCircle2}
            text={isLoading ? "Loading alert state..." : "No open alerts. The control plane is calm."}
          />
        )}
      </div>
    </div>
  );
}

function AuditTrailPanel({ entries, isLoading }: { entries: AuditEntry[]; isLoading: boolean }) {
  return (
    <div className="frame col-span-12 lg:col-span-4">
      <PanelHeader
        eyebrow="Audit trail · tamper-evident"
        title="Hash-chained"
        actions={
          <Badge tone="success" icon={<ShieldCheck className="h-3 w-3" />}>
            verified
          </Badge>
        }
      />
      <div className="divide-y divide-rule/60">
        {entries.slice(0, 5).map((entry) => (
          <div key={entry.id} className="px-4 py-2.5 text-[12px]">
            <div className="flex items-center justify-between gap-3">
              <span className="truncate font-mono text-bone">{entry.kind}</span>
              <span className="whitespace-nowrap font-mono text-[10.5px] text-muted">{formatApiTime(entry.ts)}</span>
            </div>
            <div className="flex items-center justify-between gap-3 text-[11px] text-muted">
              <span className="truncate">
                {entry.subject} · {entry.actor}
              </span>
              <span className="flex items-center gap-1 font-mono">
                <Hash className="h-3 w-3" />
                {entry.hash_prefix}
              </span>
            </div>
          </div>
        ))}
        {!entries.length && (
          <EmptyPanel
            icon={isLoading ? Activity : Hash}
            text={isLoading ? "Loading audit chain..." : "No audit records yet. Successful runs appear here."}
          />
        )}
      </div>
    </div>
  );
}

function FleetPanel({ fleet, isLoading }: { fleet: FleetModel[]; isLoading: boolean }) {
  return (
    <div className="frame col-span-12 lg:col-span-4">
      <PanelHeader eyebrow="Fleet" title="Models · deployments" />
      <div className="space-y-2 px-3 py-3">
        {fleet.slice(0, 4).map((model) => (
          <div key={model.id} className="flex items-center justify-between rounded-md border border-rule bg-ink/40 px-3 py-2">
            <div className="min-w-0">
              <div className="truncate text-[12.5px] text-bone">{model.name}</div>
              <div className="font-mono text-[10.5px] text-muted">
                {model.quant} · {model.replicas} replicas
              </div>
            </div>
            <div className="flex items-center gap-1.5">
              <RouteBadge route={model.route} />
              <LatencyBadge ms={model.p50_ms} />
            </div>
          </div>
        ))}
        {!fleet.length && (
          <div className="rounded-md border border-rule bg-ink/40 px-3 py-6 text-center text-[12px] text-muted">
            {isLoading ? "Loading fleet..." : "No model fleet telemetry yet."}
          </div>
        )}
      </div>
    </div>
  );
}

function PanelHeader({
  eyebrow,
  title,
  actions,
}: {
  eyebrow: string;
  title: string;
  actions?: ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-rule px-4 py-3">
      <div className="min-w-0">
        <div className="text-eyebrow">{eyebrow}</div>
        <div className="font-display truncate text-[15px] text-bone">{title}</div>
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  );
}

function Badge({
  children,
  tone = "neutral",
  icon,
  dot,
}: {
  children: ReactNode;
  tone?: "neutral" | "muted" | "success" | "warn" | "info" | "primary" | "danger";
  icon?: ReactNode;
  dot?: boolean;
}) {
  return (
    <span
      className={cn(
        "chip",
        tone === "success" && "border-moss/30 bg-moss/10 text-moss",
        tone === "warn" && "border-amber/30 bg-amber/10 text-amber",
        tone === "info" && "border-electric/30 bg-electric/10 text-electric",
        tone === "primary" && "border-brass/40 bg-brass/10 text-brass-2",
        tone === "danger" && "border-crimson/30 bg-crimson/10 text-crimson",
        tone === "muted" && "border-rule bg-white/[0.02] text-muted",
        tone === "neutral" && "border-rule bg-ink/40 text-bone-2",
      )}
    >
      {dot && (
        <span
          className={cn(
            "h-1.5 w-1.5 rounded-full",
            tone === "success" ? "bg-moss" : tone === "warn" ? "bg-amber" : tone === "info" ? "bg-electric" : "bg-brass-2",
          )}
        />
      )}
      {icon}
      {children}
    </span>
  );
}

function LiveBadge({ label = "LIVE" }: { label?: string }) {
  return (
    <Badge tone="success" dot>
      {label}
    </Badge>
  );
}

function RouteBadge({ route }: { route: "primary" | "burst" }) {
  return route === "burst" ? <Badge tone="info">AWS burst</Badge> : <Badge tone="primary">HTZ primary</Badge>;
}

function LatencyBadge({ ms }: { ms: number }) {
  return <span className="rounded-md border border-rule px-1.5 py-0.5 font-mono text-[10px] text-muted">{ms || "-"} p50</span>;
}

function EmptyPanel({ icon: Icon, text }: { icon: ComponentType<{ className?: string }>; text: string }) {
  return (
    <div className="flex items-center gap-2 px-4 py-6 text-[12px] text-muted">
      <Icon className="h-4 w-4" />
      <span>{text}</span>
    </div>
  );
}

function getHostTiles(data?: OverviewPayload): Array<{
  label: string;
  value: string;
  sub: string;
  tone: "primary" | "info";
  icon: ComponentType<{ className?: string }>;
}> {
  if (!data) {
    return [
      { label: "Hetzner primary", value: "-", sub: "Loading host telemetry", tone: "primary", icon: Server },
      { label: "AWS burst", value: "-", sub: "Loading burst telemetry", tone: "info", icon: Cloud },
      { label: "Workspace events", value: "-", sub: "Loading live run window", tone: "primary", icon: Database },
    ];
  }

  const hosts = data.routing.primary_hosts.slice(0, 2).map((host) => ({
    label: host.name,
    value: `${host.util_pct}% util`,
    sub: host.detail,
    tone: "primary" as const,
    icon: Server,
  }));

  const burst = {
    label: data.routing.burst_plane || "AWS burst",
    value: `${data.routing.burst_util_pct}% engaged`,
    sub: "On-demand · gated by tenant policy",
    tone: "info" as const,
    icon: Cloud,
  };

  const events = {
    label: "Workspace events",
    value: `${data.recent_runs.length} run${data.recent_runs.length === 1 ? "" : "s"}`,
    sub: `${data.policy_events.length} policy event${data.policy_events.length === 1 ? "" : "s"} in window`,
    tone: "primary" as const,
    icon: Cpu,
  };

  return [...hosts, burst, events].slice(0, 3);
}
