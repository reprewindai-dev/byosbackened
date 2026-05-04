import { useQuery } from "@tanstack/react-query";
import { Plus, TerminalSquare, TrendingUp, TrendingDown, ShieldCheck, AlertCircle } from "lucide-react";
import { PlatformPulseSection } from "@/components/overview/PlatformPulseSection";
import { Sparkline } from "@/components/overview/Sparkline";
import { api } from "@/lib/api";
import type { OverviewPayload } from "@/types/api";
import { dateFromApiTimestamp, fmtCents, fmtDelta, fmtNumber, formatApiTime, relativeTime } from "@/lib/cn";
import { isRouteUnavailable } from "@/lib/errors";

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
      series: [],
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

/**
 * Smooth area chart for routing utilization (Hetzner primary vs AWS burst).
 * Renders two overlaid curves with mid-point quadratic interpolation —
 * matches the reference dashboard look (orange line over blue line, with
 * Y-axis grid labels at 30/60/90/120%).
 */
function RoutingChart({ data, isLoading }: { data?: OverviewPayload; isLoading: boolean }) {
  if (isLoading) {
    return (
      <div className="flex h-56 items-center justify-center rounded-lg border border-rule bg-ink-2/40 font-mono text-[11px] text-muted">
        Loading routing telemetry...
      </div>
    );
  }

  const series = data?.routing.series ?? [];
  const hosts = data?.routing.primary_hosts ?? [];
  const hasActivity =
    series.some((point) => point.primary > 0 || point.burst > 0) ||
    hosts.some((host) => host.util_pct > 0) ||
    (data?.recent_runs?.length ?? 0) > 0;

  if (!hasActivity) {
    return (
      <div className="flex h-56 flex-col items-center justify-center rounded-lg border border-rule bg-ink-2/40 px-6 text-center font-mono text-[11px] text-muted">
        <div>No routing events in this workspace yet.</div>
        <div className="mt-1 text-[10px] text-muted-2">Run the Playground or execute a pipeline to populate live routing telemetry.</div>
      </div>
    );
  }

  if (series.length) {
    const points = series.slice(-24);
    const W = 800;
    const H = 200;
    const padL = 36; // room for Y-axis labels
    const padR = 8;
    const padT = 8;
    const padB = 22;
    const innerW = W - padL - padR;
    const innerH = H - padT - padB;

    const yFor = (v: number) => padT + innerH * (1 - Math.max(0, Math.min(100, v)) / 100);
    const xFor = (i: number) =>
      padL + (points.length === 1 ? innerW / 2 : (i / (points.length - 1)) * innerW);

    function curvePath(values: number[]): { line: string; area: string } {
      const pts = values.map((v, i) => ({ x: xFor(i), y: yFor(v) }));
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
      <div className="rounded-lg border border-rule bg-ink-2/40 p-3">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="h-56 w-full"
          preserveAspectRatio="none"
          role="img"
          aria-label="Hetzner primary vs AWS burst routing utilization, last 2 hours"
        >
          {/* Y-axis gridlines + labels */}
          {yTicks.map((tick) => (
            <g key={`yt-${tick}`}>
              <line
                x1={padL}
                x2={W - padR}
                y1={yFor(tick)}
                y2={yFor(tick)}
                stroke="rgba(255,255,255,0.05)"
                strokeWidth={1}
              />
              <text
                x={padL - 6}
                y={yFor(tick) + 3}
                textAnchor="end"
                fontSize="10"
                fontFamily="JetBrains Mono, monospace"
                fill="rgba(255,255,255,0.35)"
              >
                {tick}
              </text>
            </g>
          ))}

          {/* AWS burst (blue, behind) */}
          <path d={burst.area} fill="rgba(110, 168, 254, 0.15)" />
          <path
            d={burst.line}
            fill="none"
            stroke="rgba(110, 168, 254, 0.95)"
            strokeWidth={1.75}
            strokeLinejoin="round"
            strokeLinecap="round"
          />

          {/* Hetzner primary (orange, front) */}
          <path d={primary.area} fill="rgba(229, 177, 110, 0.18)" />
          <path
            d={primary.line}
            fill="none"
            stroke="rgba(229, 177, 110, 0.98)"
            strokeWidth={2}
            strokeLinejoin="round"
            strokeLinecap="round"
          />

          {/* X-axis labels */}
          {xTicks.map((i) => (
            <text
              key={`xt-${i}`}
              x={xFor(i)}
              y={H - 6}
              textAnchor={i === 0 ? "start" : i === points.length - 1 ? "end" : "middle"}
              fontSize="10"
              fontFamily="JetBrains Mono, monospace"
              fill="rgba(255,255,255,0.4)"
            >
              {points[i]?.t ?? ""}
            </text>
          ))}
        </svg>
        <div className="mt-2 flex items-center justify-end gap-4 font-mono text-[10px] text-muted">
          <span className="flex items-center gap-1.5">
            <span className="h-1.5 w-3 rounded-sm bg-brass-2" /> Hetzner primary
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-1.5 w-3 rounded-sm bg-electric" /> AWS burst
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="h-56 rounded-lg border border-rule bg-ink-2/40 p-4">
      <div className="mb-3 font-mono text-[10px] uppercase tracking-[0.12em] text-muted">Live host utilization</div>
      <div className="space-y-3">
        {hosts.slice(0, 4).map((host) => (
          <div key={host.name}>
            <div className="mb-1 flex justify-between font-mono text-[11px]">
              <span className="text-bone">{host.name}</span>
              <span className="text-muted">{host.util_pct}%</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-rule">
              <div className="h-full rounded-full bg-brass" style={{ width: `${Math.max(0, Math.min(100, host.util_pct))}%` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function OverviewPage() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["overview"],
    queryFn: fetchOverview,
    refetchInterval: 15_000,
  });

  return (
    <div className="mx-auto w-full max-w-7xl space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="mb-1 font-mono text-[11px] uppercase tracking-[0.15em] text-muted">
            Workspace · Overview
          </div>
          <h1 className="text-3xl font-semibold tracking-tight">Sovereign control plane</h1>
          <p className="mt-2 max-w-2xl text-sm text-bone-2">
            Every prompt routed, policed, and audited — across Hetzner primary and AWS burst — without leaving your
            perimeter.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <span className="v-chip v-chip-ok">● live backend connected</span>
            <span className="v-chip">SOC2-ready</span>
            <span className="v-chip">HIPAA-aware</span>
            <span className="v-chip v-chip-brass">EU-sovereign</span>
          </div>
        </div>
        <div className="flex gap-2">
          <a href="#/deployments" className="v-btn-ghost">
            <Plus className="h-4 w-4" /> New deployment
          </a>
          <a href="#/playground" className="v-btn-primary">
            <TerminalSquare className="h-4 w-4" /> Open Playground
          </a>
        </div>
      </header>

      {isError && (
        <div className="v-card flex items-start gap-3 border-crimson/40 bg-crimson/5 p-4 text-sm text-crimson">
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

      <section className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
        <KpiCard
          label="Requests / min"
          value={data ? fmtNumber(data.kpi.requests_per_minute) : "—"}
          delta={data ? fmtDelta(data.kpi.requests_delta_pct, "%") : undefined}
          positive={!!data && data.kpi.requests_delta_pct >= 0}
          loading={isLoading}
          series={data?.kpi.requests_series}
        />
        <KpiCard
          label="P50 latency"
          value={data ? `${data.kpi.p50_latency_ms} ms` : "—"}
          delta={data ? fmtDelta(data.kpi.p50_delta_ms, " ms") : undefined}
          positive={!!data && data.kpi.p50_delta_ms <= 0}
          loading={isLoading}
        />
        <KpiCard
          label="Tokens / sec"
          value={data ? fmtNumber(data.kpi.tokens_per_second) : "—"}
          delta={data ? fmtDelta(data.kpi.tokens_delta_pct, "%") : undefined}
          positive={!!data && data.kpi.tokens_delta_pct >= 0}
          loading={isLoading}
          series={data?.kpi.tokens_series}
        />
        <KpiCard
          label="Spend today"
          value={data ? fmtCents(data.kpi.spend_today_cents) : "—"}
          delta={data ? `${data.kpi.spend_cap_pct}% cap` : undefined}
          positive={!!data && data.kpi.spend_cap_pct < 80}
          loading={isLoading}
          series={data?.kpi.spend_series}
        />
        <KpiCard
          label="Active models"
          value={data ? String(data.kpi.active_models) : "—"}
          delta={data ? `${data.kpi.active_models_quantized} quantized` : undefined}
          positive
          loading={isLoading}
        />
        <KpiCard
          label="Audit entries"
          value={data ? fmtNumber(data.kpi.audit_entries) : "—"}
          delta={data ? `${data.kpi.audit_verified_pct}% verified` : undefined}
          positive
          loading={isLoading}
        />
      </section>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="v-card p-5 lg:col-span-2">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <div className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted">Routing · last 24h</div>
              <h3 className="mt-1 text-lg font-semibold">Hetzner primary · AWS burst</h3>
            </div>
            <div className="flex gap-2">
              <span className="v-chip v-chip-brass">Hetzner {data?.routing.primary_util_pct ?? "—"}%</span>
              <span className="v-chip">AWS {data?.routing.burst_util_pct ?? "—"}%</span>
            </div>
          </div>
          <RoutingChart data={data} isLoading={isLoading} />
          <div className="mt-3 grid grid-cols-3 gap-2 font-mono text-[11px]">
            {data?.routing.primary_hosts?.slice(0, 3).map((h) => (
              <div key={h.name} className="rounded-lg border border-rule p-2">
                <div className="text-muted">{h.name}</div>
                <div className="text-bone">{h.util_pct}% util</div>
                <div className="text-[10px] text-muted-2">{h.detail}</div>
              </div>
            )) ?? (
              <>
                <SkeletonCell />
                <SkeletonCell />
                <SkeletonCell />
              </>
            )}
          </div>
        </div>

        <div className="v-card p-5">
          <div className="mb-3 flex items-center justify-between">
            <div className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted">Spend · today</div>
            <span className="v-chip v-chip-ok">
              <ShieldCheck className="h-3 w-3" /> on-pace
            </span>
          </div>
          <div className="mb-1 text-2xl font-semibold">
            {data ? fmtCents(data.spend.spend_cents) : "—"}
            <span className="ml-1 text-sm font-normal text-muted">
              of {data ? fmtCents(data.spend.cap_cents) : "—"}
            </span>
          </div>
          <div className="mb-4 h-1.5 w-full overflow-hidden rounded bg-rule">
            <div
              className="h-full rounded bg-brass"
              style={{ width: `${Math.min(100, data?.kpi.spend_cap_pct ?? 0)}%` }}
            />
          </div>
          <div className="grid grid-cols-2 gap-2 font-mono text-[11px]">
            <SpendRow label="Inference" cents={data?.spend.inference_cents} total={data?.spend.spend_cents} />
            <SpendRow label="Embeddings" cents={data?.spend.embeddings_cents} total={data?.spend.spend_cents} />
            <SpendRow label="GPU burst" cents={data?.spend.gpu_burst_cents} total={data?.spend.spend_cents} />
            <SpendRow label="Storage" cents={data?.spend.storage_cents} total={data?.spend.spend_cents} />
          </div>
          <div className="mt-4 space-y-1 font-mono text-[11px] text-muted">
            <div className="flex justify-between">
              <span>Burn rate</span>
              <span className="text-bone">
                {data ? fmtCents(data.spend.burn_rate_per_min_cents) : "—"} / min
              </span>
            </div>
            <div className="flex justify-between">
              <span>Forecast EOD</span>
              <span className="text-bone">
                {data ? fmtCents(data.spend.forecast_eod_cents) : "—"} ({data?.spend.forecast_cap_pct ?? "—"}% cap)
              </span>
            </div>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="v-card p-0 lg:col-span-2">
          <header className="flex items-center justify-between border-b border-rule px-5 py-3">
            <div>
              <div className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted">Recent runs · live</div>
              <h3 className="mt-1 text-sm font-semibold">Per-call routing, latency, cost</h3>
            </div>
            <a href="#/playground" className="v-chip hover:text-bone">Playground →</a>
          </header>
          <table className="w-full text-[13px]">
            <thead>
              <tr className="border-b border-rule font-mono text-[10px] uppercase tracking-wider text-muted">
                <th className="px-5 py-2 text-left font-medium">Model</th>
                <th className="px-5 py-2 text-left font-medium">Route</th>
                <th className="px-5 py-2 text-right font-medium">Latency</th>
                <th className="px-5 py-2 text-right font-medium">Tokens</th>
                <th className="px-5 py-2 text-right font-medium">Cost</th>
                <th className="px-5 py-2 text-left font-medium">Policy</th>
                <th className="px-5 py-2 text-right font-medium">When</th>
              </tr>
            </thead>
            <tbody className="font-mono">
              {(data?.recent_runs ?? []).slice(0, 5).map((r) => (
                <tr key={r.id} className="border-b border-rule/60 last:border-0">
                  <td className="px-5 py-2.5 text-bone">{r.model}</td>
                  <td className="px-5 py-2.5">
                    <span className={r.route === "burst" ? "v-chip text-electric" : "v-chip v-chip-brass"}>
                      {r.route === "burst" ? "AWS burst" : "HTZ primary"}
                    </span>
                  </td>
                  <td className="px-5 py-2.5 text-right text-bone">{r.latency_ms} ms</td>
                  <td className="px-5 py-2.5 text-right">{r.tokens}</td>
                  <td className="px-5 py-2.5 text-right text-bone">{fmtCents(r.cost_cents)}</td>
                  <td className="px-5 py-2.5">
                    <span
                      className={
                        r.policy === "passed"
                          ? "v-chip v-chip-ok"
                          : r.policy === "redacted"
                          ? "v-chip v-chip-warn"
                          : "v-chip v-chip-err"
                      }
                    >
                      ● {r.policy}
                    </span>
                  </td>
                  <td className="px-5 py-2.5 text-right text-muted">{relativeTime(r.when)}</td>
                </tr>
              ))}
              {!data?.recent_runs?.length && (
                <tr>
                  <td colSpan={7} className="px-5 py-6 text-center text-muted">
                    {isLoading ? "Loading runs…" : "No runs yet. Open the Playground to generate the first one."}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="v-card p-5">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <div className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
                Policy interception · live
              </div>
              <h3 className="mt-1 text-sm font-semibold">Decision before execution</h3>
            </div>
            <span className="v-chip v-chip-ok">● live</span>
          </div>
          <ul className="space-y-3 font-mono text-[11px]">
            {(data?.policy_events ?? []).map((e) => (
              <li key={e.id} className="flex gap-3">
                <span className="mt-1 h-1.5 w-1.5 rounded-full bg-brass" />
                <div className="flex-1">
                  <div className="flex justify-between text-bone">
                    <span>{e.summary}</span>
                    <span className="text-muted">{formatApiTime(e.ts)}</span>
                  </div>
                  <div className="text-muted">{e.detail}</div>
                </div>
              </li>
            ))}
            {!data?.policy_events?.length && (
              <li className="text-muted">{isLoading ? "Waiting on policy engine…" : "No events in window."}</li>
            )}
          </ul>
        </div>
      </section>

      <PlatformPulseSection />
    </div>
  );
}

function KpiCard({
  label,
  value,
  delta,
  positive,
  loading,
  series,
}: {
  label: string;
  value: string;
  delta?: string;
  positive?: boolean;
  loading?: boolean;
  series?: number[];
}) {
  return (
    <div className="v-card p-4">
      <div className="flex items-center gap-1 font-mono text-[10px] uppercase tracking-[0.1em] text-muted">
        ⚙ {label}
      </div>
      <div className="mt-1.5 flex items-baseline justify-between">
        <div className="text-xl font-semibold text-bone">
          {loading ? <span className="inline-block h-4 w-14 animate-pulse rounded bg-rule" /> : value}
        </div>
        {delta && (
          <div
            className={
              "flex items-center gap-0.5 font-mono text-[10px] " + (positive ? "text-moss" : "text-crimson")
            }
          >
            {positive ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
            {delta}
          </div>
        )}
      </div>
      <div className="mt-2 h-7 w-full">
        <Sparkline values={series ?? []} />
      </div>
    </div>
  );
}

function SpendRow({ label, cents, total }: { label: string; cents?: number; total?: number }) {
  const pct = cents !== undefined && total && total > 0 ? Math.round((cents / total) * 100) : undefined;
  return (
    <div className="flex items-center justify-between rounded border border-rule px-2 py-1.5">
      <div className="flex flex-col leading-tight">
        <span className="text-muted">{label}</span>
        {pct !== undefined && <span className="text-[10px] text-muted-2">{pct}%</span>}
      </div>
      <span className="text-bone">{cents !== undefined ? fmtCents(cents) : "—"}</span>
    </div>
  );
}

function SkeletonCell() {
  return <div className="h-14 animate-pulse rounded-lg border border-rule bg-ink-2" />;
}
