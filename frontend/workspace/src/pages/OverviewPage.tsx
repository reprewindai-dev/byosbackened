import { useQuery } from "@tanstack/react-query";
import type { ComponentType, ReactNode } from "react";
import {
  AlertCircle,
  Archive,
  ArrowRight,
  BadgeCheck,
  BrainCircuit,
  CircleDot,
  CircuitBoard,
  Cpu,
  Database,
  FileCheck2,
  GitBranch,
  Hash,
  Landmark,
  Layers3,
  LineChart,
  Network,
  OctagonAlert,
  RadioTower,
  Scale,
  ShieldCheck,
  ShoppingBag,
  Split,
  TerminalSquare,
  Vote,
  WalletCards,
  Workflow,
} from "lucide-react";
import { Sparkline } from "@/components/overview/Sparkline";
import { useAuthStore } from "@/store/auth-store";
import { api } from "@/lib/api";
import {
  cn,
  dateFromApiTimestamp,
  fmtCents,
  fmtNumber,
  formatApiTime,
  relativeTime,
} from "@/lib/cn";
import { isRouteUnavailable } from "@/lib/errors";
import type {
  Alert,
  AuditEntry,
  FleetModel,
  OverviewPayload,
  PlatformPulse,
  PolicyEvent,
  RecentRun,
} from "@/types/api";

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

async function fetchPlatformPulse(): Promise<PlatformPulse | null> {
  try {
    const resp = await api.get<PlatformPulse>("/platform/pulse");
    return resp.data;
  } catch (err) {
    if (isRouteUnavailable(err)) return null;
    throw err;
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
      burst_plane: "Approved fallback",
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
      detail: `${row.kind ?? "request"} - ${row.model ?? "unknown"}`,
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
  const user = useAuthStore((state) => state.user);
  const overview = useQuery({
    queryKey: ["overview"],
    queryFn: fetchOverview,
    refetchInterval: 15_000,
  });
  const pulse = useQuery({
    queryKey: ["platform-pulse"],
    queryFn: fetchPlatformPulse,
    refetchInterval: 30_000,
  });

  const data = overview.data;
  const pulseData = pulse.data ?? null;
  const state = data ? deriveInstitutionalState(data, pulseData) : null;
  const isSuperuser = Boolean(user?.is_superuser);

  return (
    <div className="command-wall">
      <CommandHeader
        userScope={isSuperuser ? "Owner Command Center" : "Tenant Overview Center"}
        workspace={user?.workspace_name ?? user?.workspace_id ?? "workspace"}
        state={state}
        isLoading={overview.isLoading}
        isSuperuser={isSuperuser}
      />
      <CommandBridge data={data} pulse={pulseData} state={state} isLoading={overview.isLoading} isSuperuser={isSuperuser} />

      {overview.isError && (
        <div className="command-alert">
          <AlertCircle className="h-4 w-4" />
          <span>{(overview.error as Error)?.message ?? "Unable to load overview telemetry"}</span>
        </div>
      )}

      <SurfaceMap data={data} pulse={pulseData} state={state} isSuperuser={isSuperuser} />

      <section className="sv-chamber">
        <SectionTitle
          eyebrow={isSuperuser ? "Hello, Silicon Valley" : "Workspace posture"}
          title={isSuperuser ? "Institutional consciousness" : "Governed workspace overview"}
          text={
            isSuperuser
              ? "Strategic posture, route integrity, memory continuity, and unresolved pressure from live control-plane telemetry."
              : "Tenant-scoped telemetry for routes, runs, models, reserve usage, evidence, and operational health."
          }
        />
        <SiliconValleyWall data={data} pulse={pulseData} state={state} isLoading={overview.isLoading} isSuperuser={isSuperuser} />
      </section>

      <section className="sunnyvale-floor">
        <SectionTitle
          eyebrow={isSuperuser ? "Hello, Sunnyvale" : "Workspace activity"}
          title="Operational execution"
          text={
            isSuperuser
              ? "Agent runs, committee decisions, intervention requests, blocked workflows, evidence, and execution traces."
              : "Runs, endpoint activity, policy outcomes, evidence, routes, and execution traces for this workspace."
          }
        />
        <SunnyvaleFloor data={data} state={state} isLoading={overview.isLoading} />
      </section>

      <ArchivesLayer data={data} isLoading={overview.isLoading} />
    </div>
  );
}

function CommandHeader({
  userScope,
  workspace,
  state,
  isLoading,
  isSuperuser,
}: {
  userScope: string;
  workspace: string;
  state: InstitutionalState | null;
  isLoading: boolean;
  isSuperuser: boolean;
}) {
  return (
    <header className="command-header">
      <div>
        <div className="command-kicker">{isSuperuser ? "Veklom owner command center" : "Veklom workspace overview"}</div>
        <h1>{isSuperuser ? "Institutional command center" : "Workspace overview center"}</h1>
        <p>{userScope} - {workspace}</p>
      </div>
      <div className="command-status-strip">
        <StatusDatum label="Institutional state" value={isLoading ? "synchronizing" : state?.posture ?? "no signal"} tone={state?.tone ?? "neutral"} />
        <StatusDatum label="Execution confidence" value={state ? `${state.executionConfidence}%` : "-"} tone={state?.executionConfidence && state.executionConfidence >= 80 ? "stable" : "watch"} />
        <StatusDatum label="Route integrity" value={state ? `${state.routeIntegrity}%` : "-"} tone={state?.routeIntegrity && state.routeIntegrity >= 80 ? "stable" : "watch"} />
        <StatusDatum label="Memory continuity" value={state ? `${state.memoryContinuity}%` : "-"} tone="stable" />
      </div>
    </header>
  );
}

function CommandBridge({
  data,
  pulse,
  state,
  isLoading,
  isSuperuser,
}: {
  data?: OverviewPayload;
  pulse: PlatformPulse | null;
  state: InstitutionalState | null;
  isLoading: boolean;
  isSuperuser: boolean;
}) {
  const primarySignal = isLoading
    ? "Synchronizing live spine"
    : state?.posture ?? "Awaiting live signal";
  const actions = [
    {
      label: "Run governed decision",
      detail: "Execute through policy, route, reserve, and audit.",
      to: "#/playground",
      icon: TerminalSquare,
      value: `${fmtNumber(data?.recent_runs.length ?? 0)} traces`,
    },
    {
      label: "Inspect live pressure",
      detail: "Open telemetry, latency, routing, alerts, and proof.",
      to: "#/monitoring",
      icon: LineChart,
      value: data ? `${data.kpi.p50_latency_ms}ms p50` : "no signal",
    },
    {
      label: "Build marketplace asset",
      detail: "Move from public pain to governed Veklom-native tools.",
      to: "#/marketplace",
      icon: ShoppingBag,
      value: pulse ? `${pulse.active_listings.total} listings` : "catalog",
    },
    {
      label: "Tune reserve posture",
      detail: "Review spend, burn rate, billing, and operating reserve.",
      to: "#/billing",
      icon: WalletCards,
      value: data ? fmtCents(data.spend.spend_cents) : "$0.00",
    },
  ];

  return (
    <section className="command-bridge" aria-label="Live command bridge">
      <div className="bridge-prime">
        <span>{isSuperuser ? "Live owner command bridge" : "Live workspace overview"}</span>
        <h2>{primarySignal}</h2>
        <p>
          {isSuperuser
            ? "This overview is the control surface: institutional telemetry, execution lanes, evidence lineage, and the operating actions that move the system."
            : "This overview is tenant-scoped: governed runs, routing, evidence, billing posture, and the next useful workspace action."}
        </p>
        <div className="bridge-pulse">
          <i />
          <b>{state ? `${state.systemCoherence}% coherence` : "coherence pending"}</b>
          <small>{data ? `${fmtNumber(data.kpi.audit_entries)} audit entries / ${fmtNumber(data.kpi.active_models)} active models` : "waiting for backend telemetry"}</small>
        </div>
      </div>
      <div className="bridge-actions">
        {actions.map((action) => (
          <a key={action.to} href={action.to} className="bridge-action">
            <action.icon className="h-4 w-4" />
            <span>{action.label}</span>
            <b>{action.value}</b>
            <small>{action.detail}</small>
            <ArrowRight className="bridge-arrow h-3.5 w-3.5" />
          </a>
        ))}
      </div>
    </section>
  );
}

function SurfaceMap({
  data,
  pulse,
  state,
  isSuperuser,
}: {
  data?: OverviewPayload;
  pulse: PlatformPulse | null;
  state: InstitutionalState | null;
  isSuperuser: boolean;
}) {
  const surfaces = isSuperuser
    ? [
        {
          title: "Deterministic Engine",
          label: "Public narrative",
          value: state ? `${state.convergencePressure}% pressure` : "story layer",
          detail: "Intent, doctrine, and the reason governed autonomy matters.",
          tone: "neutral",
          to: "#/control-center",
        },
        {
          title: "Silicon Valley",
          label: "Strategic governance",
          value: state ? `${state.systemCoherence}% coherence` : "syncing",
          detail: "UACP posture, policy stability, escalation pressure, and route authority.",
          tone: state?.tone ?? "neutral",
          to: "#/overview",
        },
        {
          title: "Sunnyvale",
          label: "Execution floor",
          value: `${fmtNumber(data?.recent_runs.length ?? 0)} runs`,
          detail: "Agents, queues, workflows, tools, blocked jobs, and intervention paths.",
          tone: data?.recent_runs.length ? "stable" : "neutral",
          to: "#/playground",
        },
        {
          title: "Archives",
          label: "Memory spine",
          value: `${fmtNumber(data?.audit_trail.length ?? data?.kpi.audit_entries ?? 0)} records`,
          detail: "Replayable judgment, evidence ledger, provenance, and institutional continuity.",
          tone: data?.audit_trail.length ? "stable" : "watch",
          to: "#/compliance",
        },
        {
          title: "Marketplace",
          label: "Asset factory",
          value: pulse ? `${pulse.active_listings.total} live` : "Builder lane",
          detail: "Sovereign Builder Agents convert public pain into governed sellable tools.",
          tone: "neutral",
          to: "#/marketplace",
        },
        {
          title: "Control room",
          label: "Tuning",
          value: data ? `${data.routing.primary_util_pct}% primary` : "no signal",
          detail: "Models, billing, settings, routes, and operational spine controls.",
          tone: "stable",
          to: "#/settings",
        },
      ]
    : [
        {
          title: "Overview Center",
          label: "Workspace status",
          value: state ? `${state.systemCoherence}% health` : "syncing",
          detail: "Tenant-scoped health, runs, route posture, reserve usage, and evidence state.",
          tone: state?.tone ?? "neutral",
          to: "#/overview",
        },
        {
          title: "Playground",
          label: "Prompt test",
          value: `${fmtNumber(data?.recent_runs.length ?? 0)} runs`,
          detail: "Run prompts, compare available models, save useful tests into pipelines.",
          tone: data?.recent_runs.length ? "stable" : "neutral",
          to: "#/playground",
        },
        {
          title: "Pipelines",
          label: "Workflow builder",
          value: `${fmtNumber(data?.policy_events.length ?? 0)} events`,
          detail: "Build, test, prove, and deploy governed workflows.",
          tone: "stable",
          to: "#/pipelines",
        },
        {
          title: "Deployments",
          label: "Endpoint verification",
          value: data ? `${data.routing.primary_util_pct}% primary` : "no signal",
          detail: "Create endpoints, run same-page tests, inspect logs, and copy code after proof.",
          tone: "stable",
          to: "#/deployments",
        },
        {
          title: "Evidence",
          label: "Audit trail",
          value: `${fmtNumber(data?.audit_trail.length ?? data?.kpi.audit_entries ?? 0)} records`,
          detail: "View run evidence, policy results, audit hashes, and export availability by plan.",
          tone: data?.audit_trail.length ? "stable" : "watch",
          to: "#/compliance",
        },
        {
          title: "Billing",
          label: "Reserve posture",
          value: data ? fmtCents(data.spend.spend_cents) : "$0.00",
          detail: "Track governed usage, reserve impact, plan status, and activation requirements.",
          tone: "neutral",
          to: "#/billing",
        },
      ];

  return (
    <section className="surface-map" aria-label="Institutional product surface map">
      {surfaces.map((surface) => (
        <a key={surface.title} href={surface.to} className={cn("surface-node", surface.tone)}>
          <span>{surface.label}</span>
          <b>{surface.title}</b>
          <strong>{surface.value}</strong>
          <small>{surface.detail}</small>
        </a>
      ))}
    </section>
  );
}

function SiliconValleyWall({
  data,
  pulse,
  state,
  isLoading,
  isSuperuser,
}: {
  data?: OverviewPayload;
  pulse: PlatformPulse | null;
  state: InstitutionalState | null;
  isLoading: boolean;
  isSuperuser: boolean;
}) {
  return (
    <div className="sv-grid">
      <InstitutionalStatePanel state={state} data={data} isLoading={isLoading} isSuperuser={isSuperuser} />
      <StrategicTrajectory data={data} state={state} />
      <AgentAlignment data={data} />
      <InstitutionalEvents data={data} pulse={pulse} isLoading={isLoading} />
      <ResourcePosture data={data} pulse={pulse} />
    </div>
  );
}

function InstitutionalStatePanel({ state, data, isLoading, isSuperuser }: { state: InstitutionalState | null; data?: OverviewPayload; isLoading: boolean; isSuperuser: boolean }) {
  const metrics = [
    { label: "System coherence", value: state ? `${state.systemCoherence}%` : "-", icon: BrainCircuit },
    { label: "Convergence pressure", value: state ? `${state.convergencePressure}%` : "-", icon: Split },
    { label: "Operational drift", value: state ? `${state.operationalDrift}%` : "-", icon: GitBranch },
    { label: "Unresolved escalations", value: String(data?.alerts.length ?? 0), icon: OctagonAlert },
    { label: "Policy stability", value: state ? `${state.policyStability}%` : "-", icon: Scale },
    { label: "Resource posture", value: data ? `${data.kpi.spend_cap_pct}%` : "-", icon: Database },
  ];

  return (
    <div className="sv-prime mineral-panel">
      <PanelChrome label={isSuperuser ? "Institutional state" : "Workspace state"} icon={Landmark} />
      <div className="state-core">
        <div className={cn("state-orbit", state?.tone)}>
          <span />
          <b>{isLoading ? "SYNC" : state?.posture ?? "NO SIGNAL"}</b>
        </div>
        <div>
          <h3>{isSuperuser ? "Consciousness layer" : "Governed overview"}</h3>
          <p>{state?.narrative ?? "Waiting for live workspace telemetry."}</p>
        </div>
      </div>
      <div className="state-matrix">
        {metrics.map((metric) => (
          <SignalReadout key={metric.label} {...metric} />
        ))}
      </div>
    </div>
  );
}

function StrategicTrajectory({ data, state }: { data?: OverviewPayload; state: InstitutionalState | null }) {
  return (
    <div className="sv-trajectory mineral-panel">
      <PanelChrome label="Strategic trajectory" icon={Network} />
      <div className="trajectory-bands">
        <TrajectoryBand label="Route integrity" value={state?.routeIntegrity ?? 0} tone="cyan" />
        <TrajectoryBand label="Execution confidence" value={state?.executionConfidence ?? 0} tone="teal" />
        <TrajectoryBand label="Memory continuity" value={state?.memoryContinuity ?? 0} tone="amber" />
      </div>
      <div className="signal-chart">
        <Sparkline values={data?.kpi.requests_series ?? []} />
        <span>Long-range movement derives from live run cadence and audit continuity.</span>
      </div>
    </div>
  );
}

function AgentAlignment({ data }: { data?: OverviewPayload }) {
  const committees = buildCommittees(data);
  return (
    <div className="sv-alignment mineral-panel">
      <PanelChrome label="Global agent behavior" icon={CircuitBoard} />
      <div className="alignment-map">
        {committees.map((committee) => (
          <div key={committee.name} className={cn("alignment-node", committee.tone)}>
            <span>{committee.name}</span>
            <b>{committee.state}</b>
            <small>{committee.detail}</small>
          </div>
        ))}
      </div>
    </div>
  );
}

function InstitutionalEvents({ data, pulse, isLoading }: { data?: OverviewPayload; pulse: PlatformPulse | null; isLoading: boolean }) {
  const events = buildStrategicEvents(data, pulse);
  return (
    <div className="sv-events mineral-panel">
      <PanelChrome label="Strategic events" icon={RadioTower} />
      <div className="event-column">
        {events.map((event) => (
          <EventLine key={event.id} event={event} />
        ))}
        {!events.length && <EmptyLine text={isLoading ? "Synchronizing strategic event stream." : "No strategic events in the live window."} />}
      </div>
    </div>
  );
}

function ResourcePosture({ data, pulse }: { data?: OverviewPayload; pulse: PlatformPulse | null }) {
  return (
    <div className="sv-resource mineral-panel">
      <PanelChrome label="Resource posture" icon={Layers3} />
      <div className="resource-grid">
        <StatusDatum label="Reserve used" value={data ? fmtCents(data.spend.spend_cents) : "-"} tone="stable" />
        <StatusDatum label="Burn rate" value={data ? `${fmtCents(data.spend.burn_rate_per_min_cents)} / min` : "-"} tone="neutral" />
        <StatusDatum label="Active models" value={data ? String(data.kpi.active_models) : "-"} tone="stable" />
        <StatusDatum label="Marketplace orders" value={pulse ? String(pulse.orders_30d.count) : "-"} tone="neutral" />
      </div>
    </div>
  );
}

function SunnyvaleFloor({ data, state, isLoading }: { data?: OverviewPayload; state: InstitutionalState | null; isLoading: boolean }) {
  return (
    <div className="sunnyvale-grid">
      <ExecutionLanes runs={data?.recent_runs ?? []} isLoading={isLoading} />
      <CommitteeSessions events={data?.policy_events ?? []} state={state} isLoading={isLoading} />
      <InterventionQueue alerts={data?.alerts ?? []} runs={data?.recent_runs ?? []} isLoading={isLoading} />
      <EvidenceTray entries={data?.audit_trail ?? []} isLoading={isLoading} />
      <FleetMatrix fleet={data?.fleet ?? []} />
    </div>
  );
}

function ExecutionLanes({ runs, isLoading }: { runs: RecentRun[]; isLoading: boolean }) {
  return (
    <div className="ops-lanes mineral-panel">
      <PanelChrome label="Active runs and execution traces" icon={Workflow} action={<a href="#/playground">Open Playground <ArrowRight className="h-3 w-3" /></a>} />
      <div className="trace-table">
        {runs.slice(0, 7).map((run) => (
          <div key={run.id} className="trace-row">
            <span className={cn("route-light", run.route)} />
            <b>{run.model}</b>
            <em>{run.route === "burst" ? "Fallback route" : "Hetzner primary"}</em>
            <strong>{run.latency_ms} ms</strong>
            <small>{run.tokens} units</small>
            <PolicySeal policy={run.policy} />
            <time>{relativeTime(run.when)}</time>
          </div>
        ))}
        {!runs.length && <EmptyLine text={isLoading ? "Synchronizing active run lanes." : "No active runs in the live window."} />}
      </div>
    </div>
  );
}

function CommitteeSessions({ events, state, isLoading }: { events: PolicyEvent[]; state: InstitutionalState | null; isLoading: boolean }) {
  return (
    <div className="committee-panel mineral-panel">
      <PanelChrome label="Committee sessions" icon={Vote} />
      <div className="committee-score">
        <span>Alignment</span>
        <b>{state ? `${state.committeeAlignment}%` : "-"}</b>
        <small>{events.length} live policy event{events.length === 1 ? "" : "s"}</small>
      </div>
      <div className="session-list">
        {events.slice(0, 5).map((event) => (
          <div key={event.id} className="session-row">
            <CircleDot className="h-3.5 w-3.5" />
            <div>
              <b>{event.summary}</b>
              <span>{event.detail}</span>
            </div>
            <time>{formatApiTime(event.ts)}</time>
          </div>
        ))}
        {!events.length && <EmptyLine text={isLoading ? "Waiting for committee decisions." : "No committee sessions in this window."} />}
      </div>
    </div>
  );
}

function InterventionQueue({ alerts, runs, isLoading }: { alerts: Alert[]; runs: RecentRun[]; isLoading: boolean }) {
  const blocked = runs.filter((run) => run.policy === "blocked");
  const interventions = [
    ...alerts.map((alert) => ({
      id: alert.id,
      title: alert.title,
      detail: `${alert.scope} - ${relativeTime(alert.when)}`,
      severity: alert.severity,
    })),
    ...blocked.map((run) => ({
      id: run.id,
      title: "Blocked workflow",
      detail: `${run.model} - ${relativeTime(run.when)}`,
      severity: "error" as const,
    })),
  ];
  return (
    <div className="intervention-panel mineral-panel">
      <PanelChrome label="Open intervention" icon={OctagonAlert} />
      <div className="intervention-stack">
        {interventions.slice(0, 5).map((item) => (
          <div key={item.id} className={cn("intervention-row", item.severity)}>
            <span />
            <b>{item.title}</b>
            <small>{item.detail}</small>
          </div>
        ))}
        {!interventions.length && <EmptyLine text={isLoading ? "Scanning intervention queue." : "No open intervention requests."} />}
      </div>
    </div>
  );
}

function EvidenceTray({ entries, isLoading }: { entries: AuditEntry[]; isLoading: boolean }) {
  return (
    <div className="evidence-panel mineral-panel">
      <PanelChrome label="Attached evidence" icon={FileCheck2} />
      <div className="evidence-list">
        {entries.slice(0, 6).map((entry) => (
          <div key={entry.id} className="evidence-row">
            <Hash className="h-3.5 w-3.5" />
            <div>
              <b>{entry.kind}</b>
              <span>{entry.subject}</span>
            </div>
            <code>{entry.hash_prefix || "pending"}</code>
          </div>
        ))}
        {!entries.length && <EmptyLine text={isLoading ? "Loading evidence chain." : "No evidence attachments yet."} />}
      </div>
    </div>
  );
}

function FleetMatrix({ fleet }: { fleet: FleetModel[] }) {
  return (
    <div className="fleet-panel mineral-panel">
      <PanelChrome label="Delegated agents and routes" icon={Cpu} />
      <div className="fleet-matrix">
        {fleet.slice(0, 6).map((model) => (
          <div key={model.id} className="fleet-row">
            <b>{model.name}</b>
            <span>{model.quant}</span>
            <em>{model.route === "burst" ? "fallback" : "primary"}</em>
            <code>{model.p50_ms || "-"} p50</code>
          </div>
        ))}
        {!fleet.length && <EmptyLine text="No model fleet telemetry yet." />}
      </div>
    </div>
  );
}

function ArchivesLayer({ data, isLoading }: { data?: OverviewPayload; isLoading: boolean }) {
  const archiveEntries = buildArchiveLineage(data);
  return (
    <section className="archives-spine">
      <div>
        <div className="archive-mark"><Archive className="h-4 w-4" /> The Archives</div>
        <h2>Historical lineage</h2>
        <p>Permanent record of votes, executions, disagreements, policy changes, escalations, and institutional transitions.</p>
      </div>
      <div className="archive-line">
        {archiveEntries.map((entry) => (
          <div key={entry.id}>
            <b>{entry.kind}</b>
            <span>{entry.subject}</span>
            <code>{entry.hash}</code>
          </div>
        ))}
        {!archiveEntries.length && <EmptyLine text={isLoading ? "Reconstructing lineage." : "No archive lineage available from live telemetry yet."} />}
      </div>
    </section>
  );
}

function PanelChrome({ label, icon: Icon, action }: { label: string; icon: ComponentType<{ className?: string }>; action?: ReactNode }) {
  return (
    <div className="panel-chrome">
      <span><Icon className="h-3.5 w-3.5" /> {label}</span>
      {action && <div>{action}</div>}
    </div>
  );
}

function SectionTitle({ eyebrow, title, text }: { eyebrow: string; title: string; text: string }) {
  return (
    <div className="command-section-title">
      <span>{eyebrow}</span>
      <h2>{title}</h2>
      <p>{text}</p>
    </div>
  );
}

function SignalReadout({ label, value, icon: Icon }: { label: string; value: string; icon: ComponentType<{ className?: string }> }) {
  return (
    <div className="signal-readout">
      <Icon className="h-3.5 w-3.5" />
      <span>{label}</span>
      <b>{value}</b>
    </div>
  );
}

function TrajectoryBand({ label, value, tone }: { label: string; value: number; tone: "cyan" | "teal" | "amber" }) {
  return (
    <div className={cn("trajectory-band", tone)}>
      <div><span>{label}</span><b>{value}%</b></div>
      <i style={{ width: `${Math.max(2, Math.min(100, value))}%` }} />
    </div>
  );
}

function StatusDatum({ label, value, tone }: { label: string; value: string; tone: "stable" | "watch" | "critical" | "neutral" }) {
  return (
    <div className={cn("status-datum", tone)}>
      <span>{label}</span>
      <b>{value}</b>
    </div>
  );
}

function EventLine({ event }: { event: StrategicEvent }) {
  return (
    <div className={cn("event-line", event.tone)}>
      <span />
      <div>
        <b>{event.title}</b>
        <small>{event.detail}</small>
      </div>
      <time>{event.when}</time>
    </div>
  );
}

function PolicySeal({ policy }: { policy: RecentRun["policy"] }) {
  return (
    <span className={cn("policy-seal", policy)}>
      {policy === "passed" ? <ShieldCheck className="h-3 w-3" /> : policy === "redacted" ? <BadgeCheck className="h-3 w-3" /> : <OctagonAlert className="h-3 w-3" />}
      {policy}
    </span>
  );
}

function EmptyLine({ text }: { text: string }) {
  return <div className="empty-line">{text}</div>;
}

interface InstitutionalState {
  posture: string;
  tone: "stable" | "watch" | "critical" | "neutral";
  narrative: string;
  systemCoherence: number;
  convergencePressure: number;
  operationalDrift: number;
  executionConfidence: number;
  routeIntegrity: number;
  memoryContinuity: number;
  policyStability: number;
  committeeAlignment: number;
}

interface StrategicEvent {
  id: string;
  title: string;
  detail: string;
  when: string;
  tone: "stable" | "watch" | "critical" | "neutral";
}

function deriveInstitutionalState(data: OverviewPayload, pulse: PlatformPulse | null): InstitutionalState {
  const totalRuns = data.recent_runs.length;
  const passedRuns = data.recent_runs.filter((run) => run.policy === "passed").length;
  const blockedRuns = data.recent_runs.filter((run) => run.policy === "blocked").length;
  const executionConfidence = totalRuns ? pct(passedRuns, totalRuns) : data.kpi.audit_verified_pct;
  const routeIntegrity = Math.max(0, Math.round(100 - data.routing.burst_util_pct));
  const memoryContinuity = data.kpi.audit_entries ? data.kpi.audit_verified_pct : 0;
  const policyStability = Math.max(0, Math.round(100 - blockedRuns * 18 - data.alerts.length * 12));
  const operationalDrift = Math.min(100, Math.round(Math.max(0, data.kpi.p50_delta_ms) / 20 + data.routing.burst_util_pct + data.alerts.length * 8));
  const convergencePressure = Math.min(100, Math.round(data.policy_events.length * 10 + data.alerts.length * 16 + (pulse?.orders_30d.delta_pct_vs_prior ?? 0) / 2));
  const committeeAlignment = Math.max(0, Math.round((executionConfidence + policyStability + routeIntegrity) / 3));
  const systemCoherence = Math.max(0, Math.round((executionConfidence + routeIntegrity + memoryContinuity + policyStability) / 4));
  const tone: InstitutionalState["tone"] = data.alerts.some((alert) => alert.severity === "error") || blockedRuns > 0
    ? "critical"
    : operationalDrift > 35 || convergencePressure > 55
      ? "watch"
      : totalRuns || data.kpi.audit_entries
        ? "stable"
        : "neutral";
  const posture = tone === "critical" ? "Escalation pressure" : tone === "watch" ? "Controlled drift" : tone === "stable" ? "Coherent" : "Awaiting signal";
  const narrative = `${fmtNumber(data.kpi.audit_entries)} audit entries, ${fmtNumber(totalRuns)} live run traces, ${data.routing.primary_plane} at ${data.routing.primary_util_pct}% with ${data.routing.burst_plane} at ${data.routing.burst_util_pct}%.`;

  return {
    posture,
    tone,
    narrative,
    systemCoherence,
    convergencePressure,
    operationalDrift,
    executionConfidence,
    routeIntegrity,
    memoryContinuity,
    policyStability,
    committeeAlignment,
  };
}

function pct(part: number, total: number): number {
  return total > 0 ? Math.round((part / total) * 100) : 0;
}

function buildCommittees(data?: OverviewPayload) {
  const policyEvents = data?.policy_events.length ?? 0;
  const alerts = data?.alerts.length ?? 0;
  const burst = data?.routing.burst_util_pct ?? 0;
  const audit = data?.kpi.audit_verified_pct ?? 0;
  return [
    { name: "Policy", state: alerts ? "contested" : "aligned", detail: `${policyEvents} decision event${policyEvents === 1 ? "" : "s"}`, tone: alerts ? "watch" : "stable" },
    { name: "Routing", state: burst > 20 ? "conflicted" : "aligned", detail: `${burst}% fallback posture`, tone: burst > 20 ? "watch" : "stable" },
    { name: "Memory", state: audit >= 95 ? "continuous" : "thin", detail: `${audit}% verified lineage`, tone: audit >= 95 ? "stable" : "neutral" },
    { name: "Fleet", state: data?.kpi.active_models ? "online" : "quiet", detail: `${data?.kpi.active_models ?? 0} model routes`, tone: data?.kpi.active_models ? "stable" : "neutral" },
  ];
}

function buildStrategicEvents(data?: OverviewPayload, pulse?: PlatformPulse | null): StrategicEvent[] {
  const events: StrategicEvent[] = [];
  (data?.alerts ?? []).slice(0, 3).forEach((alert) => {
    events.push({
      id: `alert-${alert.id}`,
      title: "Escalation path opened",
      detail: `${alert.title} - ${alert.scope}`,
      when: relativeTime(alert.when),
      tone: alert.severity === "error" ? "critical" : "watch",
    });
  });
  (data?.policy_events ?? []).slice(0, 4).forEach((event) => {
    events.push({
      id: `policy-${event.id}`,
      title: event.kind === "audit_signed" ? "Historical lineage written" : "Policy posture shifted",
      detail: event.summary,
      when: relativeTime(event.ts),
      tone: "stable",
    });
  });
  if (pulse) {
    events.push({
      id: "pulse-marketplace",
      title: "External signal changed",
      detail: `${pulse.active_listings.total} active listings, ${pulse.orders_30d.count} paid orders in 30d`,
      when: relativeTime(pulse.generated_at),
      tone: "neutral",
    });
  }
  return events.slice(0, 6);
}

function buildArchiveLineage(data?: OverviewPayload) {
  const audits = (data?.audit_trail ?? []).slice(0, 5).map((entry) => ({
    id: `audit-${entry.id}`,
    kind: entry.kind,
    subject: entry.subject,
    hash: entry.hash_prefix || "unsealed",
  }));
  const policies = (data?.policy_events ?? []).slice(0, Math.max(0, 5 - audits.length)).map((event) => ({
    id: `policy-${event.id}`,
    kind: event.kind,
    subject: event.summary,
    hash: event.id.slice(0, 10),
  }));
  return [...audits, ...policies];
}
