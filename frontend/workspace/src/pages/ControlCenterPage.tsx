import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { ComponentType, ReactNode } from "react";
import type { AxiosError } from "axios";
import {
  Activity,
  AlertCircle,
  Archive,
  BadgeCheck,
  BriefcaseBusiness,
  CircleDollarSign,
  CircuitBoard,
  Download,
  Eye,
  FileCheck2,
  Gauge,
  Landmark,
  Network,
  Radar,
  Sparkles,
  Target,
  Users,
  Workflow,
} from "lucide-react";
import { api } from "@/lib/api";
import { cn, fmtNumber, relativeTime } from "@/lib/cn";
import type { LiveOpsSummary } from "@/types/api";

type Room = "overview" | "surgeon" | "growth" | "intelligence";
type Tone = "stable" | "watch" | "critical" | "neutral";
type RouteStatus =
  | "live"
  | "unreachable"
  | "unauthorized"
  | "forbidden"
  | "client_error"
  | "server_error"
  | "timeout"
  | "malformed"
  | "unavailable";

interface SafeResult<T> {
  ok: boolean;
  data?: T;
  error?: string;
  source?: string;
  contractVersion?: string;
  status?: number | null;
  reason?: RouteStatus;
}

interface UacpSummary {
  generated_at?: string;
  product_truth?: {
    workspaces?: number;
    active_workspaces?: number;
    users?: number;
    active_users?: number;
    active_subscriptions?: number;
    reserve_balance_usd?: string;
    requests_24h?: number;
    failed_requests_24h?: number;
    ai_audits_24h?: number;
    pipeline_runs_24h?: number;
    deployments?: number;
    open_alerts?: number;
  };
  uacp_truth?: {
    worker_count?: number;
    committee_count?: number;
    event_owner_mappings?: number;
  };
}

interface UacpEvent {
  event_id: string;
  event_type: string;
  workspace_id?: string | null;
  tenant_id?: string | null;
  user_id?: string | null;
  entity_type: string;
  entity_id: string;
  severity: "info" | "warning" | "error" | string;
  status: string;
  timestamp?: string | null;
  payload?: Record<string, unknown>;
  uacp?: {
    pillar_ids?: string[];
    committee_ids?: string[];
    worker_ids?: string[];
  };
}

interface WorkspaceRow {
  workspace_id: string;
  tenant_id?: string;
  name?: string;
  slug?: string;
  is_active?: boolean;
  license_tier?: string;
  created_at?: string;
  updated_at?: string;
}

interface RunRow {
  run_id: string;
  workspace_id?: string;
  user_id?: string;
  request_kind?: string;
  request_path?: string;
  status?: string;
  provider?: string;
  model?: string;
  latency_ms?: number;
  cost_usd?: string;
  tokens_in?: number;
  tokens_out?: number;
  tenant_id?: string;
  actor_id?: string;
  risk_tier?: string;
  governance_decision?: string;
  debit_cents?: string;
  genome_hash?: string;
  input_hash?: string;
  output_hash?: string;
  decision_frame_hash?: string;
  request_log_id?: string | null;
  source_table?: string;
  source_id?: string;
  source?: string;
  created_at?: string;
  updated_at?: string;
  sealed_at?: string | null;
}

interface DeploymentRow {
  deployment_id: string;
  workspace_id?: string;
  name?: string;
  slug?: string;
  status?: string;
  provider?: string;
  model_slug?: string;
  region?: string;
  strategy?: string;
  traffic_percent?: number;
  last_health_check?: string | null;
  updated_at?: string | null;
}

interface BillingRow {
  transaction_id: string;
  workspace_id?: string;
  transaction_type?: string;
  amount_units?: number;
  amount_usd?: string;
  balance_after_units?: number;
  description?: string;
  created_at?: string;
}

interface EvidenceRow {
  audit_id: string;
  workspace_id?: string;
  user_id?: string;
  operation_type?: string;
  provider?: string;
  model?: string;
  cost_usd?: string;
  log_hash?: string;
  created_at?: string;
}

interface SecurityEventRow {
  event_id: string;
  workspace_id?: string;
  event_type?: string;
  event_category?: string;
  success?: boolean;
  failure_reason?: string;
  created_at?: string;
}

interface EvaluationSurgeonEntry {
  workspace_id: string;
  tenant_id?: string | null;
  workspace: string;
  workspace_slug?: string | null;
  user_id?: string | null;
  user_handle?: string | null;
  tier?: string | null;
  runs_used?: number | null;
  free_evaluation_limit?: number | null;
  last_activity?: string | null;
  endpoint_status?: string | null;
  evidence_activity?: {
    audit_entries?: number | null;
    status?: string | null;
  } | null;
  billing_state?: {
    reserve_units?: number | null;
    reserve_usd?: string | null;
    transactions?: number | null;
    paid_active?: boolean | null;
  } | null;
  security_state?: {
    mfa_enabled_users?: number | null;
    active_users?: number | null;
  } | null;
  risk_score?: number | null;
  activation_probability?: number | null;
  top_action?: string | null;
  assigned_workers?: string[] | null;
  committee_id?: string | null;
  pillar_ids?: string[] | null;
  archive_ref?: string | null;
  evidence?: Record<string, unknown> | null;
  status?: string | null;
}

interface EvaluationSurgeonPayload {
  queue?: EvaluationSurgeonEntry[] | null;
  empty_reason?: string | null;
  required_sources?: string[] | null;
  source?: string;
  contract_version?: string;
}

interface EventStreamPayload {
  stream?: string | null;
  redis_backed?: boolean | null;
  events?: UacpEvent[];
  empty_reason?: string | null;
  required_sources?: string[] | null;
  generated_at?: string | null;
  source?: string;
  contract_version?: string;
}

interface GrowthOpportunity {
  opportunity_id: string;
  kind?: string | null;
  title?: string | null;
  score?: number | null;
  risk?: number | null;
  source_event?: string | null;
  evidence?: Record<string, unknown> | null;
  recommended_action?: string | null;
  assigned_workers?: string[] | null;
  committee_id?: string | null;
  pillar_ids?: string[] | null;
  archive_ref?: string | null;
  status?: string | null;
}

interface GrowthOpportunityPayload {
  opportunities?: GrowthOpportunity[] | null;
  empty_reason?: string | null;
  required_sources?: string[] | null;
  source?: string;
  contract_version?: string;
}

interface WorkerRow {
  id: string;
  name?: string;
  status?: string;
  mission?: string;
  primary_pillar?: string;
  committees?: string[];
  hard_kpis?: string[];
  minimum_live?: boolean;
  rollout_stage?: string;
}

interface CommitteeRow {
  id?: string;
  name?: string;
  worker_ids?: string[];
  ready_workers?: number;
  authority?: string;
}

interface WorkerRunRow {
  id: string;
  event_type?: string;
  success?: boolean;
  failure_reason?: string | null;
  details?: {
    worker_id?: string;
    worker_name?: string;
    status?: string;
    summary?: string;
    committees?: string[];
    primary_pillar?: string;
    details?: Record<string, unknown>;
  };
  created_at?: string;
}

interface ControlSnapshot {
  summary: SafeResult<UacpSummary>;
  liveOps: SafeResult<LiveOpsSummary>;
  events: SafeResult<{ events?: UacpEvent[] }>;
  evaluationSurgeon: SafeResult<EvaluationSurgeonPayload>;
  growthOpportunities: SafeResult<GrowthOpportunityPayload>;
  eventStream: SafeResult<EventStreamPayload>;
  workspaces: SafeResult<{ workspaces?: WorkspaceRow[] }>;
  runs: SafeResult<{ runs?: RunRow[] }>;
  deployments: SafeResult<{ deployments?: DeploymentRow[] }>;
  billing: SafeResult<{ reserve_units_total?: number; transactions?: BillingRow[] }>;
  evidence: SafeResult<{ evidence?: EvidenceRow[] }>;
  security: SafeResult<{ security_events?: SecurityEventRow[] }>;
  registry: SafeResult<{ workers?: WorkerRow[]; committees?: CommitteeRow[] }>;
  workerRuns: SafeResult<{ runs?: WorkerRunRow[]; count?: number }>;
}

interface OperatingSignal {
  id: string;
  title: string;
  workspace: string;
  eventType: string;
  score: number;
  risk: number;
  tone: Tone;
  evidence: string[];
  action: string;
  workers: string[];
  committee: string;
  pillar: string;
  archiveRef: string;
  status: string;
  when?: string | null;
}

interface EvaluationAccount {
  workspaceId: string;
  name: string;
  tier: string;
  runsUsed: number;
  lastActivity?: string;
  endpointStatus: string;
  evidenceActivity: string;
  billingState: string;
  riskScore: number;
  activationProbability: number;
  topAction: string;
  workers: string[];
  evidence: string[];
}

interface GrowthOpportunityCard {
  title: string;
  meta: string;
  icon: ComponentType<{ className?: string }>;
  score: number;
  tone: Tone;
  headline: string;
  detail: string;
  evidence: string[];
  action: string;
  workers: string[];
  status: string;
  archiveRef: string;
}

async function safeGet<T>(path: string, params?: Record<string, unknown>): Promise<SafeResult<T>> {
  try {
    const response = await api.get<T>(path, { params });
    const responseData = response.data as Record<string, unknown> & { source?: string; contract_version?: string };
    return {
      ok: true,
      data: response.data,
      source: responseData.source,
      contractVersion: responseData.contract_version,
      status: response.status,
      reason: "live",
    };
  } catch (error) {
    const axiosError = error as AxiosError<Record<string, unknown>>;
    const status = axiosError.response?.status ?? null;
    const responseData = axiosError.response?.data;
    const responseError =
      typeof responseData === "object" && responseData !== null && "detail" in responseData
        ? String((responseData as Record<string, unknown>).detail)
        : axiosError.message;
    const responseSource =
      typeof responseData === "object" && responseData && "source" in responseData ? responseData.source : undefined;
    const responseContract =
      typeof responseData === "object" &&
      responseData &&
      "contract_version" in responseData
        ? responseData.contract_version
        : undefined;
    const errorCode = (axiosError as { code?: string }).code;
    const message = axiosError.message || "Unavailable";
    const reason: RouteStatus =
      status === 401
        ? "unauthorized"
        : status === 403
          ? "forbidden"
          : typeof status === "number" && status >= 500
            ? "server_error"
            : typeof status === "number" && status >= 400
              ? "client_error"
              : !axiosError.response
                ? errorCode === "ECONNABORTED" || errorCode === "ETIMEDOUT"
                  ? "timeout"
                  : "unreachable"
                : typeof responseData === "string"
                  ? "malformed"
                  : "unavailable";
    return {
      ok: false,
      error: responseError ?? message,
      source: responseSource as string | undefined,
      contractVersion: responseContract as string | undefined,
      status,
      reason,
    };
  }
}

function deriveRouteStatus<T>(result?: SafeResult<T>): RouteStatus {
  if (result?.reason) return result.reason;
  const status = result?.status;
  if (typeof status === "number" && status >= 200 && status < 300) return "live";
  if (status === 401) return "unauthorized";
  if (status === 403) return "forbidden";
  if (typeof status === "number" && status >= 500) return "server_error";
  if (typeof status === "number" && status >= 400) return "client_error";
  if (result === undefined || result === null) return "unavailable";
  return result.ok ? "live" : "unavailable";
}

function isRouteLive(status: RouteStatus): boolean {
  return status === "live";
}

function deriveFailureReasonText({
  route,
  status,
  error,
  requiredSources,
  emptyReason,
}: {
  route: string;
  status: RouteStatus;
  error?: string | null;
  requiredSources?: string[] | null;
  emptyReason?: string | null;
}) {
  if (status === "live") {
    return null;
  }
  if (status === "unauthorized") return `${route}: owner operator auth missing or expired (401).`;
  if (status === "forbidden") return `${route}: authenticated but route blocked by role policy (403).`;
  if (status === "timeout") return `${route}: request timed out.`;
  if (status === "unreachable") return `${route}: backend transport unavailable from this client surface.`;
  if (status === "malformed") return `${route}: backend returned malformed payload.`;
  if (status === "client_error") {
    const reasonSuffix = requiredSources?.length ? ` required sources: ${requiredSources.join(", ")}` : "";
    return `${route}: request rejected (4xx).${reasonSuffix}`;
  }
  if (status === "server_error") return `${route}: backend returned 5xx.`;
  if (status === "unavailable")
    return `${route}: ${error ?? emptyReason ?? "no data response available."}${requiredSources?.length ? ` required sources: ${requiredSources.join(", ")}` : ""}`;
  return `${route}: route unavailable.`;
}

async function fetchControlSnapshot(): Promise<ControlSnapshot> {
  const [
    summary,
    liveOps,
    events,
    eventStream,
    evaluationSurgeon,
    growthOpportunities,
    workspaces,
    runs,
    deployments,
    billing,
    evidence,
    security,
    registry,
    workerRuns,
  ] =
    await Promise.all([
      safeGet<UacpSummary>("/internal/uacp/summary"),
      safeGet<LiveOpsSummary>("/admin/live-ops"),
      safeGet<{ events?: UacpEvent[] }>("/internal/uacp/events", { limit: 150 }),
      safeGet<EventStreamPayload>("/internal/uacp/event-stream", { limit: 150 }),
      safeGet<EvaluationSurgeonPayload>("/internal/uacp/evaluation-surgeon", { limit: 150 }),
      safeGet<GrowthOpportunityPayload>("/internal/uacp/growth-opportunities", { limit: 150 }),
      safeGet<{ workspaces?: WorkspaceRow[] }>("/internal/uacp/workspaces", { limit: 250 }),
      safeGet<{ runs?: RunRow[] }>("/internal/uacp/runs", { limit: 250 }),
      safeGet<{ deployments?: DeploymentRow[] }>("/internal/uacp/deployments", { limit: 250 }),
      safeGet<{ reserve_units_total?: number; transactions?: BillingRow[] }>("/internal/uacp/billing", { limit: 250 }),
      safeGet<{ evidence?: EvidenceRow[] }>("/internal/uacp/evidence", { limit: 250 }),
      safeGet<{ security_events?: SecurityEventRow[] }>("/internal/uacp/security", { limit: 250 }),
      safeGet<{ workers?: WorkerRow[]; committees?: CommitteeRow[] }>("/internal/operators/registry"),
      safeGet<{ runs?: WorkerRunRow[]; count?: number }>("/internal/operators/runs", { limit: 150 }),
    ]);

  return {
    summary,
    events,
    liveOps,
    eventStream,
    evaluationSurgeon,
    growthOpportunities,
    workspaces,
    runs,
    deployments,
    billing,
    evidence,
    security,
    registry,
    workerRuns,
  };
}

interface RunProof {
  runId: string;
  workspaceId: string;
  status: string;
  provider: string;
  model: string;
  governanceDecision: string;
  riskTier: string;
  genomeHash: string;
  inputHash: string;
  outputHash: string;
  decisionFrameHash: string;
  source: string;
  sourceId: string;
  requestLogId?: string | null;
  createdAt?: string;
  sealedAt?: string | null;
}

export function ControlCenterPage() {
  const [room, setRoom] = useState<Room>("overview");
  const snapshot = useQuery({
    queryKey: ["sunnyvale-internal-v1"],
    queryFn: fetchControlSnapshot,
    refetchInterval: 15_000,
  });

  const model = useMemo(() => buildOperatingModel(snapshot.data), [snapshot.data]);

  return (
    <div className="mx-auto w-full max-w-[1680px]">
      <header className="mb-5 overflow-hidden border border-rule bg-[#05070a]">
        <div className="grid gap-px bg-rule lg:grid-cols-[1fr_520px]">
          <div className="bg-[radial-gradient(circle_at_12%_0%,rgba(110,168,254,0.14),transparent_32%),linear-gradient(135deg,rgba(255,255,255,0.055),rgba(255,255,255,0.01))] p-6">
            <div className="flex flex-wrap items-center gap-2">
              <SignalPill tone="stable" label="UACP V3" />
              <SignalPill tone={snapshot.isLoading ? "watch" : "stable"} label={snapshot.isLoading ? "syncing" : "live bridge"} />
              <SignalPill tone="neutral" label="owner only" />
            </div>
            <div className="mt-8 grid gap-4 lg:grid-cols-[260px_1fr]">
              <div>
                <div className="font-serif text-[44px] italic leading-none text-bone md:text-[64px]">Sunnyvale</div>
                <div className="mt-3 font-mono text-[11px] uppercase tracking-[0.22em] text-muted">
                  Internal operator intelligence / governed execution floor
                </div>
              </div>
              <div className="max-w-3xl">
                <div className="text-eyebrow">Operating pattern</div>
                <h1 className="mt-2 text-2xl font-semibold leading-tight text-bone md:text-4xl">
                  Score every signal, show the evidence, assign an owner, and make the next action obvious.
                </h1>
                <p className="mt-3 text-sm leading-6 text-muted">
                  This surface combines backend product truth with UACP interpretation. If data is missing, the room says
                  unavailable instead of filling the wall with fake metrics.
                </p>
              </div>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-px bg-rule">
            <HeaderMetric label="Active tenants" value={fmtNumber(model.liveOps?.active_tenants ?? 0)} />
            <HeaderMetric label="Open rooms" value={fmtNumber(model.liveOps?.open_rooms ?? 0)} />
            <HeaderMetric label="Live users" value={fmtNumber(model.liveOps?.live_users ?? 0)} />
            <HeaderMetric label="Degraded rooms" value={fmtNumber(model.liveOps?.degraded_workspaces ?? 0)} />
          </div>
        </div>
        <nav className="flex flex-wrap gap-px border-t border-rule bg-rule">
          {[
            ["overview", "Overview"],
            ["surgeon", "Evaluation Surgeon"],
            ["growth", "Hub Growth Navigator"],
            ["intelligence", "Field Intelligence"],
          ].map(([id, label]) => (
            <button
              key={id}
              type="button"
              onClick={() => setRoom(id as Room)}
              className={cn(
                "bg-[#080b10] px-5 py-3 font-mono text-[11px] uppercase tracking-[0.16em] text-muted transition hover:bg-white/[0.04] hover:text-bone",
                room === id && "bg-electric/10 text-electric shadow-[inset_0_-2px_0_rgba(110,168,254,0.9)]",
              )}
            >
              {label}
            </button>
          ))}
        </nav>
      </header>

      <main className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
        <section className="min-w-0">
          {snapshot.isError && (
            <LiveErrorBox title="Sunnyvale failed to load" detail={(snapshot.error as Error)?.message ?? "Unknown error"} />
          )}
          {room === "overview" && <OverviewRoom model={model} loading={snapshot.isLoading} />}
          {room === "surgeon" && (
            <EvaluationSurgeon
              accounts={model.accounts}
              loading={snapshot.isLoading}
              routeStatus={model.evaluationSurgeonStatus}
              emptyReason={model.evaluationSurgeonUnavailableReason}
              requiredSources={model.evaluationSurgeonRequiredSources}
              routeSource={model.evaluationSurgeonSource}
              contractVersion={model.evaluationSurgeonContractVersion}
            />
          )}
          {room === "growth" && (
            <GrowthNavigator
              opportunities={model.growthQueue}
              loading={snapshot.isLoading}
              routeUnavailable={model.growthOpportunitiesUnavailable}
              routeStatus={model.growthOpportunitiesStatus}
              unavailableReason={model.growthOpportunitiesUnavailableReason}
              requiredSources={model.growthOpportunitiesRequiredSources}
              routeSource={model.growthOpportunitiesSource}
              contractVersion={model.growthOpportunitiesContractVersion}
            />
          )}
          {room === "intelligence" && <FieldIntelligence model={model} loading={snapshot.isLoading} />}
        </section>
        <aside className="space-y-4">
          <WorkerQueue workers={model.workers} workerRuns={model.workerRuns} />
          <DoctrinePanel />
          <RunProofPanel
            proofs={model.runProofs}
            redisBacked={model.eventStreamRedisBacked}
            routeStatus={model.eventStreamRouteStatus}
          />
          <ArchivePanel signals={model.signals} />
        </aside>
      </main>
    </div>
  );
}

function OverviewRoom({ model, loading }: { model: OperatingModel; loading: boolean }) {
  const stories = deriveStories(model);
  const eventStreamMeta = `source: ${model.eventStreamSource ?? "unknown-source"} / contract: ${model.eventStreamContractVersion ?? "unknown-contract"} / redis: ${model.eventStreamRedisBacked ? "backed" : "db snapshot"}`;
  return (
    <div className="space-y-4">
      <LiveOpsRoom liveOps={model.liveOps} loading={loading} />
      <section className="border border-rule bg-ink-2/40">
        <PanelHead icon={Gauge} label="UACP Business Pulse" meta={model.generatedAt ? `LIVE / ${relativeTime(model.generatedAt)}` : "LIVE / timestamp unavailable"} />
        <div className="grid gap-px bg-rule md:grid-cols-4">
          <PulseCell icon={Users} label="Workspaces" value={fmtNumber(model.pulse.workspaces)} />
          <PulseCell icon={Target} label="Active evaluations" value={fmtNumber(model.pulse.activeEvaluations)} />
          <PulseCell icon={AlertCircle} label="Failed routes" value={fmtNumber(model.pulse.failedRoutes)} tone={model.pulse.failedRoutes ? "critical" : "stable"} />
          <PulseCell icon={FileCheck2} label="Evidence exports" value={fmtNumber(model.pulse.evidenceExports)} />
          <PulseCell icon={Activity} label="Runs 24h" value={fmtNumber(model.pulse.requests24h)} />
          <PulseCell icon={Workflow} label="Pipeline runs" value={fmtNumber(model.pulse.pipelineRuns24h)} />
          <PulseCell icon={CircuitBoard} label="Deployments" value={fmtNumber(model.pulse.deployments)} />
          <PulseCell icon={CircleDollarSign} label="Reserve" value={model.pulse.reserveLive} />
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <div className="border border-rule bg-ink-2/40">
          <PanelHead icon={Radar} label="Operating Signals" meta={`${model.signals.length} ranked`} />
          <div className="border-b border-rule bg-white/[0.015] px-4 py-3">
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge
                label={model.eventStreamRedisBacked ? "redis backed" : "database snapshot"}
                tone={model.eventStreamRedisBacked ? "stable" : "watch"}
              />
              <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted">
                /internal/uacp/event-stream - {eventStreamMeta}
              </span>
            </div>
          </div>
          <div className="divide-y divide-rule">
            {model.signals.slice(0, 8).map((signal) => (
              <SignalRow key={signal.id} signal={signal} />
            ))}
            {!model.signals.length && (
              <EmptyState
                text={
                  loading
                    ? "Synchronizing backend event stream."
                    : isRouteLive(model.eventStreamRouteStatus)
                      ? `No backend events available from /internal/uacp/event-stream. ${eventStreamMeta}`
                      : `Events unavailable from /internal/uacp/events and /internal/uacp/event-stream: ${deriveFailureReasonText({
                          route: "/internal/uacp/event-stream",
                          status: model.eventStreamRouteStatus,
                          error: model.eventStreamUnavailableReason ?? null,
                          emptyReason: model.eventStreamUnavailableReason ?? null,
                        })}`
                }
              />
            )}
          </div>
        </div>
        <div className="border border-rule bg-ink-2/40">
          <PanelHead icon={Sparkles} label="Stories Behind The Scores" meta="computed from live truth" />
          <div className="divide-y divide-rule">
            {stories.map((story) => (
              <StoryBlock key={story.title} {...story} />
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}

function EvaluationSurgeon({
  accounts,
  loading,
  routeStatus,
  emptyReason,
  requiredSources,
  routeSource,
  contractVersion,
}: {
  accounts: EvaluationAccount[];
  loading: boolean;
  routeStatus: RouteStatus;
  emptyReason?: string | null;
  requiredSources?: string[] | null;
  routeSource?: string | null;
  contractVersion?: string | null;
}) {
  const dataUnavailable = !isRouteLive(routeStatus);
  const routeUnavailableReason =
    isRouteLive(routeStatus)
      ? undefined
      : deriveFailureReasonText({
          route: "/internal/uacp/evaluation-surgeon",
          status: routeStatus,
          error: emptyReason ?? null,
          requiredSources,
          emptyReason,
        });
  const routeMeta = `source: ${routeSource ?? "unknown-source"} / contract: ${contractVersion ?? "unknown-contract"}`;
  return (
    <section className="border border-rule bg-ink-2/40">
      <PanelHead
        icon={BriefcaseBusiness}
        label="Evaluation Surgeon Queue"
        meta={`${accounts.length} workspace account${accounts.length === 1 ? "" : "s"} / ${routeMeta}`}
      />
      <div className="overflow-x-auto">
        <table className="w-full min-w-[1120px] text-left">
          <thead className="border-b border-rule bg-white/[0.025] font-mono text-[10px] uppercase tracking-[0.14em] text-muted">
            <tr>
              <th className="px-4 py-3">Workspace / User</th>
              <th className="px-4 py-3">Tier</th>
              <th className="px-4 py-3">Runs</th>
              <th className="px-4 py-3">Last activity</th>
              <th className="px-4 py-3">Endpoint</th>
              <th className="px-4 py-3">Evidence</th>
              <th className="px-4 py-3">Billing</th>
              <th className="px-4 py-3">Risk</th>
              <th className="px-4 py-3">Activation</th>
              <th className="px-4 py-3">Top action</th>
              <th className="px-4 py-3">Workers</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-rule">
            {accounts.map((account) => (
              <tr key={account.workspaceId} className="align-top hover:bg-white/[0.018]">
                <td className="px-4 py-4">
                  <div className="font-semibold text-bone">{account.name}</div>
                  <div className="mt-1 font-mono text-[10px] text-muted">{account.workspaceId}</div>
                </td>
                <td className="px-4 py-4 text-sm text-bone-2">{account.tier}</td>
                <td className="px-4 py-4 font-mono text-sm text-bone">{account.runsUsed}</td>
                <td className="px-4 py-4 text-sm text-muted">{account.lastActivity ? relativeTime(account.lastActivity) : "no activity"}</td>
                <td className="px-4 py-4"><StatusBadge label={account.endpointStatus} tone={account.endpointStatus.includes("active") ? "stable" : "neutral"} /></td>
                <td className="px-4 py-4 text-sm text-bone-2">{account.evidenceActivity}</td>
                <td className="px-4 py-4 text-sm text-bone-2">{account.billingState}</td>
                <td className="px-4 py-4"><ScoreMeter value={account.riskScore} tone={account.riskScore > 70 ? "critical" : account.riskScore > 45 ? "watch" : "stable"} /></td>
                <td className="px-4 py-4"><ScoreMeter value={account.activationProbability} tone="stable" /></td>
                <td className="px-4 py-4">
                  <div className="max-w-[240px] text-sm text-bone">{account.topAction}</div>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {account.evidence.slice(0, 3).map((item) => <EvidenceChip key={item}>{item}</EvidenceChip>)}
                  </div>
                </td>
                <td className="px-4 py-4">
                  <WorkerChips workers={account.workers} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!accounts.length && (
        <EmptyState
          text={
            dataUnavailable
              ? `${routeUnavailableReason || `Route unavailable: /internal/uacp/evaluation-surgeon ${routeMeta}`}`
                : loading
                  ? "Loading canonical evaluation surgeon queue from `/internal/uacp/evaluation-surgeon`."
                  : requiredSources?.length
                  ? `No qualifying entries from /internal/uacp/evaluation-surgeon; required sources not yet observed: ${requiredSources.join(", ")}.`
                  : "No workspace queue entries from `/internal/uacp/evaluation-surgeon`."
          }
        />
      )}
    </section>
  );
}

function GrowthNavigator({
  opportunities,
  loading,
  routeUnavailable,
  routeStatus,
  unavailableReason,
  requiredSources,
  routeSource,
  contractVersion,
}: {
  opportunities: GrowthOpportunityCard[];
  loading: boolean;
  routeUnavailable: boolean;
  routeStatus: RouteStatus;
  unavailableReason?: string | null;
  requiredSources?: string[] | null;
  routeSource?: string | null;
  contractVersion?: string | null;
}) {
  const routeUnavailableReason =
    isRouteLive(routeStatus)
      ? null
      : deriveFailureReasonText({
          route: "/internal/uacp/growth-opportunities",
          status: routeStatus,
          error: unavailableReason ?? null,
          requiredSources,
          emptyReason: unavailableReason,
        });
  const routeMeta = `source: ${routeSource ?? "unknown-source"} / contract: ${contractVersion ?? "unknown-contract"}`;
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {opportunities.map((item) => (
        <section key={item.title} className="border border-rule bg-ink-2/40">
          <PanelHead icon={item.icon} label={item.title} meta={item.meta} />
          <div className="p-5">
            <div className="grid grid-cols-[86px_1fr] gap-5">
              <ScoreDial value={item.score} tone={item.tone} />
              <div>
                <h3 className="text-xl font-semibold text-bone">{item.headline}</h3>
                <p className="mt-2 text-sm leading-6 text-muted">{item.detail}</p>
                <div className="mt-4 flex flex-wrap gap-1.5">
                  {item.evidence.map((line) => <EvidenceChip key={line}>{line}</EvidenceChip>)}
                </div>
                <div className="mt-4 border-t border-rule pt-4">
                <div className="text-eyebrow">Recommended action</div>
                <div className="mt-1 text-sm font-semibold text-bone">{item.action}</div>
                <div className="mt-3"><WorkerChips workers={item.workers} /></div>
                </div>
              </div>
            </div>
          </div>
        </section>
      ))}
      {!opportunities.length && (
        <div className="lg:col-span-2">
          <EmptyState
            text={
              routeUnavailable
              ? `Route unavailable: /internal/uacp/growth-opportunities ${routeMeta}${unavailableReason ? ` - ${unavailableReason}` : ""}`
                : isRouteLive(routeStatus)
                  ? loading
                    ? "Loading growth opportunities from `/internal/uacp/growth-opportunities`."
                    : requiredSources?.length
                      ? `No qualified opportunities from /internal/uacp/growth-opportunities; required sources not yet observed: ${requiredSources.join(", ")}.`
                      : "No growth opportunities from `/internal/uacp/growth-opportunities`."
                  : `${routeUnavailableReason || `Route unavailable: /internal/uacp/growth-opportunities ${routeMeta}`}`
            }
          />
        </div>
      )}
    </div>
  );
}

function FieldIntelligence({ model, loading }: { model: OperatingModel; loading: boolean }) {
  const reports = deriveFieldReports(model);
  const eventStreamHealthy = isRouteLive(model.eventStreamRouteStatus);
  const eventStreamFailure = isRouteLive(model.eventStreamRouteStatus)
    ? null
    : deriveFailureReasonText({
        route: "/internal/uacp/event-stream",
        status: model.eventStreamRouteStatus,
        error: model.eventStreamUnavailableReason ?? null,
        emptyReason: model.eventStreamUnavailableReason ?? null,
      });
  return (
    <section className="border border-rule bg-ink-2/40">
      <PanelHead icon={Eye} label="Market / Competitor Intelligence" meta="patterns with evidence only" />
      <div className="grid gap-px bg-rule lg:grid-cols-2">
        {reports.map((report) => (
          <article key={report.title} className="bg-[#080b10] p-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="text-eyebrow">{report.chapter}</div>
                <h3 className="mt-2 text-2xl font-semibold tracking-tight text-bone">{report.title}</h3>
              </div>
              <StatusBadge label={report.confidence} tone={report.tone} />
            </div>
            <p className="mt-4 text-sm leading-6 text-muted">{report.detail}</p>
            <div className="mt-5 grid gap-2">
              {report.evidence.map((line) => (
                <div key={line} className="flex items-center gap-2 border border-rule bg-white/[0.015] px-3 py-2 text-sm text-bone-2">
                  <BadgeCheck className="h-4 w-4 text-electric" />
                  {line}
                </div>
              ))}
            </div>
            <div className="mt-5 border-t border-rule pt-4">
              <div className="text-eyebrow">Assigned workers</div>
              <div className="mt-2"><WorkerChips workers={report.workers} /></div>
            </div>
          </article>
        ))}
      </div>
      {!reports.length && (
        <EmptyState
          text={
            loading
              ? "Synchronizing field intelligence."
              : eventStreamHealthy
                ? "No intelligence reports can be generated without product events, worker runs, or marketplace signals."
                : eventStreamFailure ?? "No field intelligence stream available from `/internal/uacp/event-stream`."
          }
        />
      )}
    </section>
  );
}

function LiveOpsRoom({ liveOps, loading }: { liveOps?: LiveOpsSummary; loading: boolean }) {
  return (
    <section className="border border-rule bg-ink-2/40">
      <PanelHead
        icon={Users}
        label="Live Tenant Occupancy"
        meta={liveOps?.generated_at ? `LIVE / ${relativeTime(liveOps.generated_at)}` : "LIVE / owner only"}
      />
      <div className="grid gap-px bg-rule md:grid-cols-4">
        <PulseCell icon={Users} label="Tenants online" value={fmtNumber(liveOps?.active_tenants ?? 0)} />
        <PulseCell icon={Workflow} label="Rooms open" value={fmtNumber(liveOps?.open_rooms ?? 0)} />
        <PulseCell icon={Activity} label="Sessions live" value={fmtNumber(liveOps?.live_sessions ?? 0)} />
        <PulseCell
          icon={AlertCircle}
          label="Rooms degraded"
          value={fmtNumber(liveOps?.degraded_workspaces ?? 0)}
          tone={(liveOps?.degraded_workspaces ?? 0) > 0 ? "critical" : "stable"}
        />
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[1120px] text-left">
          <thead className="border-b border-rule bg-white/[0.025] font-mono text-[10px] uppercase tracking-[0.14em] text-muted">
            <tr>
              <th className="px-4 py-3">Tenant room</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Occupants</th>
              <th className="px-4 py-3">Sessions</th>
              <th className="px-4 py-3">Requests 15m</th>
              <th className="px-4 py-3">Failures 15m</th>
              <th className="px-4 py-3">Last request</th>
              <th className="px-4 py-3">Who is in the room</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-rule">
            {(liveOps?.workspaces ?? []).slice(0, 12).map((workspace) => (
              <tr key={workspace.workspace_id} className="align-top hover:bg-white/[0.018]">
                <td className="px-4 py-4">
                  <div className="font-semibold text-bone">{workspace.workspace_name}</div>
                  <div className="mt-1 font-mono text-[10px] text-muted">{workspace.workspace_slug || workspace.workspace_id}</div>
                </td>
                <td className="px-4 py-4">
                  <StatusBadge
                    label={workspace.current_status}
                    tone={workspace.current_status === "degraded" ? "critical" : workspace.current_status === "idle" ? "watch" : "stable"}
                  />
                </td>
                <td className="px-4 py-4 font-mono text-sm text-bone">{workspace.active_user_count}</td>
                <td className="px-4 py-4 font-mono text-sm text-bone">{workspace.active_session_count}</td>
                <td className="px-4 py-4 font-mono text-sm text-bone">{workspace.recent_requests_15m}</td>
                <td className="px-4 py-4 font-mono text-sm text-bone">{workspace.failed_requests_15m}</td>
                <td className="px-4 py-4 text-sm text-muted">
                  {workspace.last_request_at ? relativeTime(workspace.last_request_at) : "no request"}
                </td>
                <td className="px-4 py-4">
                  <div className="flex flex-wrap gap-1.5">
                    {workspace.occupants.map((occupant) => (
                      <EvidenceChip key={occupant.session_id}>
                        {(occupant.full_name || occupant.email).slice(0, 36)} · {occupant.role}
                      </EvidenceChip>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!(liveOps?.workspaces?.length) && (
        <EmptyState text={loading ? "Loading live room occupancy." : "No live tenant rooms in the last 15 minutes."} />
      )}
    </section>
  );
}

function WorkerQueue({ workers, workerRuns }: { workers: WorkerRow[]; workerRuns: WorkerRunRow[] }) {
  const liveWorkers = workers.filter((worker) => worker.minimum_live).slice(0, 8);
  return (
    <section className="border border-rule bg-ink-2/40">
      <PanelHead icon={Network} label="Worker Queue" meta={`${workers.length} registered`} />
      <div className="divide-y divide-rule">
        {liveWorkers.map((worker) => {
          const lastRun = workerRuns.find((run) => run.details?.worker_id === worker.id);
          return (
            <div key={worker.id} className="p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="font-mono text-[11px] uppercase tracking-[0.16em] text-bone">{worker.name ?? worker.id}</div>
                  <div className="mt-1 text-xs text-muted">{worker.primary_pillar ?? "pillar unavailable"}</div>
                </div>
                <StatusBadge
                  label={lastRun?.details?.status ?? worker.status ?? "registered"}
                  tone={lastRun?.success === false ? "critical" : worker.status === "ready" ? "stable" : "watch"}
                />
              </div>
              <p className="mt-3 line-clamp-2 text-sm leading-5 text-muted">{lastRun?.details?.summary ?? worker.mission ?? "No mission reported."}</p>
              <div className="mt-3 font-mono text-[10px] uppercase tracking-[0.12em] text-muted">
                {lastRun?.created_at ? `last run ${relativeTime(lastRun.created_at)}` : "no run recorded"}
              </div>
            </div>
          );
        })}
        {!liveWorkers.length && <EmptyState text="Worker registry unavailable from `/internal/operators/registry`." />}
      </div>
    </section>
  );
}

function DoctrinePanel() {
  return (
    <section className="border border-rule bg-ink-2/40">
      <PanelHead icon={Landmark} label="Workflow Doctrine" meta="score -> evidence -> action -> owner" />
      <div className="space-y-3 p-4">
        {[
          ["Backend truth", "Users, runs, reserve, billing, evidence, deployments."],
          ["UACP interpretation", "Workers, committees, risk, action, archive lineage."],
          ["Hard rule", "No fake metrics. Missing source data is shown as unavailable."],
        ].map(([title, body]) => (
          <div key={title} className="border border-rule bg-white/[0.015] p-3">
            <div className="font-semibold text-bone">{title}</div>
            <div className="mt-1 text-sm leading-5 text-muted">{body}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

function RunProofPanel({
  proofs,
  redisBacked,
  routeStatus,
}: {
  proofs: RunProof[];
  redisBacked: boolean;
  routeStatus: RouteStatus;
}) {
  const latestProof = proofs[0];
  return (
    <section className="border border-rule bg-ink-2/40">
      <PanelHead
        icon={FileCheck2}
        label="VeklomRun Proof"
        meta={`${proofs.length} exportable / stream ${redisBacked ? "redis" : routeStatus}`}
      />
      {latestProof ? (
        <div className="space-y-3 p-4">
          <div className="border border-rule bg-white/[0.015] p-3">
            <div className="font-mono text-[11px] text-electric">{latestProof.runId}</div>
            <div className="mt-2 flex flex-wrap gap-1.5">
              <StatusBadge label={latestProof.status} tone={latestProof.status === "SEALED" ? "stable" : "watch"} />
              <StatusBadge label={latestProof.governanceDecision} tone={latestProof.governanceDecision === "ALLOW" ? "stable" : "watch"} />
              <StatusBadge label={latestProof.riskTier} tone={latestProof.riskTier === "LOW" ? "stable" : "watch"} />
            </div>
            <div className="mt-3 text-sm text-bone">{latestProof.provider} / {latestProof.model}</div>
            <div className="mt-1 text-xs text-muted">{latestProof.workspaceId}</div>
          </div>
          <div className="grid gap-2">
            <ProofHash label="genome" value={latestProof.genomeHash} />
            <ProofHash label="input" value={latestProof.inputHash} />
            <ProofHash label="output" value={latestProof.outputHash} />
            <ProofHash label="frame" value={latestProof.decisionFrameHash} />
          </div>
          <button type="button" className="v-btn-primary h-9 w-full text-xs" onClick={() => exportRunProof(latestProof)}>
            <Download className="h-3.5 w-3.5" /> Export latest proof
          </button>
        </div>
      ) : (
        <EmptyState text="No canonical VeklomRun proof yet. Run traffic through governed endpoints to create input/output/genome/frame hashes." />
      )}
    </section>
  );
}

function ProofHash({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-rule bg-[#06080d] p-2">
      <div className="font-mono text-[9px] uppercase tracking-[0.16em] text-muted">{label}</div>
      <div className="mt-1 break-all font-mono text-[10px] text-bone">{value}</div>
    </div>
  );
}

function exportRunProof(proof: RunProof) {
  const payload = {
    exported_at: new Date().toISOString(),
    contract: "uacp-v5-run-proof",
    proof,
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `veklom-run-proof-${proof.runId}.json`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function ArchivePanel({ signals }: { signals: OperatingSignal[] }) {
  return (
    <section className="border border-rule bg-ink-2/40">
      <PanelHead icon={Archive} label="Archive References" meta={`${signals.length} signal${signals.length === 1 ? "" : "s"}`} />
      <div className="divide-y divide-rule">
        {signals.slice(0, 5).map((signal) => (
          <div key={signal.id} className="p-4">
            <div className="font-mono text-[11px] text-electric">{signal.archiveRef}</div>
            <div className="mt-1 text-sm font-semibold text-bone">{signal.title}</div>
            <div className="mt-1 text-xs text-muted">{signal.eventType}</div>
          </div>
        ))}
        {!signals.length && <EmptyState text="No archive-worthy backend signals in the current event stream." />}
      </div>
    </section>
  );
}

function SignalRow({ signal }: { signal: OperatingSignal }) {
  return (
    <div className="grid gap-4 p-4 lg:grid-cols-[82px_1fr_220px]">
      <ScoreDial value={signal.score} tone={signal.tone} />
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-lg font-semibold text-bone">{signal.title}</h3>
          <StatusBadge label={signal.status} tone={signal.tone} />
        </div>
        <div className="mt-1 font-mono text-[10px] uppercase tracking-[0.12em] text-muted">
          {signal.workspace} / {signal.eventType} / {signal.when ? relativeTime(signal.when) : "timestamp unavailable"}
        </div>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {signal.evidence.map((item) => <EvidenceChip key={item}>{item}</EvidenceChip>)}
        </div>
      </div>
      <div>
        <div className="text-eyebrow">Recommended action</div>
        <div className="mt-1 text-sm font-semibold leading-5 text-bone">{signal.action}</div>
        <div className="mt-3"><WorkerChips workers={signal.workers} /></div>
      </div>
    </div>
  );
}

function PanelHead({ icon: Icon, label, meta }: { icon: ComponentType<{ className?: string }>; label: string; meta?: string }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-rule bg-white/[0.018] px-4 py-3">
      <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.18em] text-muted">
        <Icon className="h-4 w-4 text-electric" />
        {label}
      </div>
      {meta && <div className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted">{meta}</div>}
    </div>
  );
}

function HeaderMetric({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="min-h-[112px] bg-[#080b10] p-5">
      <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted">{label}</div>
      <div className="mt-4 font-mono text-2xl font-semibold text-bone">{value}</div>
    </div>
  );
}

function PulseCell({ icon: Icon, label, value, tone = "neutral" }: { icon: ComponentType<{ className?: string }>; label: string; value: ReactNode; tone?: Tone }) {
  return (
    <div className="min-h-[104px] bg-[#080b10] p-4">
      <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.14em] text-muted">
        <Icon className={cn("h-4 w-4", toneClass(tone, "text"))} />
        {label}
      </div>
      <div className="mt-3 font-mono text-xl font-semibold text-bone">{value}</div>
    </div>
  );
}

function ScoreDial({ value, tone }: { value: number; tone: Tone }) {
  return (
    <div className={cn("grid h-[74px] w-[74px] place-items-center border bg-white/[0.015] font-mono text-lg font-semibold", toneClass(tone, "borderText"))}>
      {value}
    </div>
  );
}

function ScoreMeter({ value, tone }: { value: number; tone: Tone }) {
  return (
    <div className="w-[88px]">
      <div className="flex justify-between font-mono text-[10px] text-muted">
        <span>score</span>
        <span className={toneClass(tone, "text")}>{value}</span>
      </div>
      <div className="mt-1 h-1.5 bg-rule">
        <div className={cn("h-full", toneClass(tone, "bg"))} style={{ width: `${Math.max(2, Math.min(100, value))}%` }} />
      </div>
    </div>
  );
}

function StatusBadge({ label, tone }: { label: string; tone: Tone }) {
  return <span className={cn("v-chip px-2 py-0.5 text-[9px]", chipClass(tone))}>{label}</span>;
}

function SignalPill({ label, tone }: { label: string; tone: Tone }) {
  return <span className={cn("rounded-full border px-3 py-1 font-mono text-[10px] uppercase tracking-[0.13em]", toneClass(tone, "borderText"))}>{label}</span>;
}

function EvidenceChip({ children }: { children: ReactNode }) {
  return <span className="rounded border border-rule bg-white/[0.018] px-2 py-1 font-mono text-[10px] uppercase tracking-[0.08em] text-bone-2">{children}</span>;
}

function WorkerChips({ workers }: { workers: string[] }) {
  if (!workers.length) return <span className="text-xs text-muted">unassigned</span>;
  return (
    <div className="flex flex-wrap gap-1.5">
      {workers.map((worker) => (
        <span key={worker} className="rounded border border-electric/30 bg-electric/10 px-2 py-1 font-mono text-[10px] uppercase tracking-[0.1em] text-electric">
          {worker}
        </span>
      ))}
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="m-4 border border-dashed border-rule bg-white/[0.01] p-4 text-sm text-muted">
      {text}
    </div>
  );
}

function LiveErrorBox({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="mb-4 flex items-start gap-3 border border-crimson/40 bg-crimson/5 p-4 text-sm text-crimson">
      <AlertCircle className="mt-0.5 h-4 w-4" />
      <div>
        <div className="font-semibold">{title}</div>
        <div className="mt-1 text-xs opacity-80">{detail}</div>
      </div>
    </div>
  );
}

function StoryBlock({ title, detail, evidence }: { title: string; detail: string; evidence: string }) {
  return (
    <div className="p-4">
      <h3 className="font-semibold text-bone">{title}</h3>
      <p className="mt-2 text-sm leading-5 text-muted">{detail}</p>
      <div className="mt-3 font-mono text-[10px] uppercase tracking-[0.12em] text-electric">{evidence}</div>
    </div>
  );
}

interface OperatingModel {
  generatedAt?: string;
  liveOps?: LiveOpsSummary;
  eventStreamUnavailable: boolean;
  eventStreamUnavailableReason: string | null;
  eventStreamRouteStatus: RouteStatus;
  eventStreamSource: string | null;
  eventStreamContractVersion: string | null;
  eventStreamRedisBacked: boolean;
  evaluationSurgeonUnavailable: boolean;
  evaluationSurgeonUnavailableReason: string | null;
  evaluationSurgeonRequiredSources: string[] | null;
  evaluationSurgeonSource: string | null;
  evaluationSurgeonContractVersion: string | null;
  evaluationSurgeonStatus: RouteStatus;
  growthOpportunitiesUnavailable: boolean;
  growthOpportunitiesUnavailableReason: string | null;
  growthOpportunitiesRequiredSources: string[] | null;
  growthOpportunitiesSource: string | null;
  growthOpportunitiesContractVersion: string | null;
  growthOpportunitiesStatus: RouteStatus;
  pulse: {
    workspaces: number;
    activeEvaluations: number;
    seriousSignals: number;
    reserveLive: string;
    workerConfidence: number;
    failedRoutes: number;
    evidenceExports: number;
    requests24h: number;
    pipelineRuns24h: number;
    deployments: number;
  };
  signals: OperatingSignal[];
  accounts: EvaluationAccount[];
  growthQueue: GrowthOpportunityCard[];
  runProofs: RunProof[];
  workers: WorkerRow[];
  committees: CommitteeRow[];
  workerRuns: WorkerRunRow[];
  raw: ControlSnapshot | undefined;
}

const ROUTE_SOURCE_UNKNOWN = "unknown-source";
const ROUTE_CONTRACT_UNKNOWN = "unknown-contract";

function buildOperatingModel(snapshot?: ControlSnapshot): OperatingModel {
  const summary = snapshot?.summary.data;
  const product = summary?.product_truth ?? {};
  const workers = snapshot?.registry.data?.workers ?? [];
  const committees = snapshot?.registry.data?.committees ?? [];
  const workerRuns = snapshot?.workerRuns.data?.runs ?? [];
  const eventStream = snapshot?.eventStream;
  const events = snapshot?.events.data?.events ?? [];
  const streamedEvents = eventStream?.data?.events ?? [];
  const eventStreamStatus = deriveRouteStatus(eventStream);
  const eventsForSignals =
    snapshot?.events.ok && events.length > 0
      ? events
      : eventStreamStatus === "live" && streamedEvents.length > 0
          ? streamedEvents
          : snapshot?.events.ok
            ? events
          : [];
  const workspaces = snapshot?.workspaces.data?.workspaces ?? [];
  const runs = snapshot?.runs.data?.runs ?? [];
  const deployments = snapshot?.deployments.data?.deployments ?? [];
  const evidence = snapshot?.evidence.data?.evidence ?? [];
  const signals = eventsForSignals.map(toOperatingSignal).sort((a, b) => (b.score + b.risk) - (a.score + a.risk));
  const surgeon = snapshot?.evaluationSurgeon;
  const opportunities = snapshot?.growthOpportunities;
  const hasSnapshotData = Boolean(snapshot);
  const evaluationSurgeonStatus = deriveRouteStatus(surgeon);
  const growthOpportunitiesStatus = deriveRouteStatus(opportunities);
  const evaluationQueueUnavailable = hasSnapshotData ? !isRouteLive(evaluationSurgeonStatus) : false;
  const growthQueueUnavailable = hasSnapshotData ? !isRouteLive(growthOpportunitiesStatus) : false;
  const evaluationSurgeonRequiredSources = surgeon?.data?.required_sources ?? null;
  const growthOpportunitiesRequiredSources = opportunities?.data?.required_sources ?? null;
  const evaluationSurgeonSource = surgeon?.data?.source ?? surgeon?.source ?? ROUTE_SOURCE_UNKNOWN;
  const evaluationSurgeonContractVersion =
    surgeon?.data?.contract_version ?? surgeon?.contractVersion ?? ROUTE_CONTRACT_UNKNOWN;
  const growthOpportunitiesSource = opportunities?.data?.source ?? opportunities?.source ?? ROUTE_SOURCE_UNKNOWN;
  const growthOpportunitiesContractVersion =
    opportunities?.data?.contract_version ?? opportunities?.contractVersion ?? ROUTE_CONTRACT_UNKNOWN;
  const eventStreamUnavailable = hasSnapshotData ? !isRouteLive(eventStreamStatus) : false;
  const eventStreamUnavailableReason = hasSnapshotData
    ? (eventStream?.error ?? eventStream?.data?.empty_reason ?? null)
    : null;
  const eventStreamSource = eventStream?.data?.source ?? eventStream?.source ?? ROUTE_SOURCE_UNKNOWN;
  const eventStreamContractVersion =
    eventStream?.data?.contract_version ?? eventStream?.contractVersion ?? ROUTE_CONTRACT_UNKNOWN;
  const eventStreamRedisBacked = Boolean(eventStream?.data?.redis_backed);
  const evaluationSurgeonUnavailableReason = hasSnapshotData ? (surgeon?.error ?? surgeon?.data?.empty_reason ?? null) : null;
  const growthOpportunitiesUnavailableReason = hasSnapshotData ? (opportunities?.error ?? opportunities?.data?.empty_reason ?? null) : null;
  const surgeonAvailable = Boolean(surgeon?.ok);
  const opportunitiesAvailable = Boolean(opportunities?.ok);
  const accounts = surgeonAvailable
    ? surgeon?.data?.queue?.map(convertSurgeonEntryToAccount).filter((entry): entry is EvaluationAccount => Boolean(entry)) ?? []
    : [];
  const growthQueue = opportunitiesAvailable
    ? opportunities?.data?.opportunities?.map(convertGrowthOpportunityToCard) ?? []
    : [];
  const runProofs = runs.map(convertRunToProof).filter((proof): proof is RunProof => Boolean(proof));
  const readyWorkers = workers.filter((worker) => worker.status === "ready").length;

  return {
    generatedAt: summary?.generated_at,
    eventStreamUnavailable,
    eventStreamUnavailableReason,
    eventStreamRouteStatus: eventStreamStatus,
    eventStreamSource,
    eventStreamContractVersion,
    eventStreamRedisBacked,
    evaluationSurgeonUnavailable: evaluationQueueUnavailable,
    evaluationSurgeonUnavailableReason,
    evaluationSurgeonRequiredSources,
    evaluationSurgeonSource,
    evaluationSurgeonContractVersion,
    evaluationSurgeonStatus,
    growthOpportunitiesUnavailable: growthQueueUnavailable,
    growthOpportunitiesUnavailableReason,
    growthOpportunitiesRequiredSources,
    growthOpportunitiesSource,
    growthOpportunitiesContractVersion,
    growthOpportunitiesStatus,
    pulse: {
      workspaces: product.workspaces ?? workspaces.length,
      activeEvaluations: accounts.filter((account) => account.tier.toLowerCase().includes("free") || account.billingState === "no reserve").length,
      seriousSignals: signals.filter((signal) => signal.score >= 65 || signal.risk >= 65).length,
      reserveLive: product.reserve_balance_usd ? `$${Number(product.reserve_balance_usd).toFixed(2)}` : "$0.00",
      workerConfidence: workers.length ? Math.round((readyWorkers / workers.length) * 100) : 0,
      failedRoutes: product.failed_requests_24h ?? runs.filter((run) => isFailure(run.status)).length,
      evidenceExports: product.ai_audits_24h ?? evidence.length,
      requests24h: product.requests_24h ?? runs.length,
      pipelineRuns24h: product.pipeline_runs_24h ?? 0,
      deployments: product.deployments ?? deployments.length,
    },
    liveOps: snapshot?.liveOps.data,
    signals,
    accounts,
    growthQueue,
    runProofs,
    workers,
    committees,
    workerRuns,
    raw: snapshot,
  };
}

function convertRunToProof(run: RunRow): RunProof | null {
  if (!run.run_id || !run.input_hash || !run.genome_hash || !run.decision_frame_hash) {
    return null;
  }
  return {
    runId: run.run_id,
    workspaceId: run.workspace_id ?? run.tenant_id ?? "unknown-workspace",
    status: run.status ?? "unknown",
    provider: run.provider ?? "unknown-provider",
    model: run.model ?? "unknown-model",
    governanceDecision: run.governance_decision ?? "unknown",
    riskTier: run.risk_tier ?? "unknown",
    genomeHash: run.genome_hash,
    inputHash: run.input_hash,
    outputHash: run.output_hash ?? "pending",
    decisionFrameHash: run.decision_frame_hash,
    source: run.source_table ?? run.source ?? "veklom_runs",
    sourceId: run.source_id ?? run.run_id,
    requestLogId: run.request_log_id,
    createdAt: run.created_at,
    sealedAt: run.sealed_at,
  };
}

function convertSurgeonEntryToAccount(entry: EvaluationSurgeonEntry): EvaluationAccount {
  const runsUsed = entry.runs_used ?? 0;
  const evidenceEntries = entry.evidence_activity?.audit_entries ?? 0;
  const reserveUnits = entry.billing_state?.reserve_units ?? 0;
  const reserveUsd = entry.billing_state?.reserve_usd ? Number(entry.billing_state.reserve_usd) : 0;
  const riskScore = clampPercent(entry.risk_score ?? 0);
  const activationProbability = clampPercent(entry.activation_probability ?? 0);
  const endpointStatus = entry.endpoint_status ?? "none";
  const workers = entry.assigned_workers ?? [];
  const evidenceStatus = entry.evidence_activity?.status ?? (evidenceEntries > 0 ? "present" : "none");
  const evidenceLines = [
    `${runsUsed} run${runsUsed === 1 ? "" : "s"}`,
    `${evidenceStatus} evidence activity`,
    entry.billing_state?.paid_active ? "paid active" : "not paid",
    `reserve ${reserveUnits} unit${reserveUnits === 1 ? "" : "s"} (${fmtCurrency(reserveUsd)})`,
    `${entry.security_state?.mfa_enabled_users ?? 0} MFA-enabled user(s)`,
  ].filter(Boolean);

  return {
    workspaceId: entry.workspace_id,
    name: entry.workspace || entry.workspace_slug || entry.workspace_id,
    tier: entry.tier || "free",
    runsUsed,
    lastActivity: entry.last_activity ?? undefined,
    endpointStatus: endpointStatus === "tested" ? "active endpoint" : endpointStatus === "created" ? "created endpoint" : "none",
    evidenceActivity: `${evidenceEntries} evidence entr${evidenceEntries === 1 ? "y" : "ies"}`,
    billingState: reserveUnits > 0 || entry.billing_state?.paid_active ? "reserve live" : "no reserve",
    riskScore,
    activationProbability,
    topAction: entry.top_action || "Wait for next backend signal.",
    workers,
    evidence: evidenceLines,
  };
}

function convertGrowthOpportunityToCard(opportunity: GrowthOpportunity): GrowthOpportunityCard {
  const score = clampPercent(opportunity.score ?? 0);
  const risk = clampPercent(opportunity.risk ?? score);
  const rawTone = risk >= 70 || score >= 85 ? "critical" : score >= 62 || risk >= 55 ? "watch" : "stable";
  const evidenceObject = opportunity.evidence ?? {};
  const evidence = Object.entries(evidenceObject).length
    ? Object.entries(evidenceObject).map(([key, value]) => `${toSentenceCase(key)}: ${String(value)}`)
    : ["no supporting evidence payload yet"];

  return {
    title: opportunity.title || `Growth opportunity ${opportunity.opportunity_id}`,
    meta: `${opportunity.kind || "market signal"} - ${score}%`,
    icon: iconForOpportunity(opportunity.kind ?? "marketplace_order"),
    score,
    tone: rawTone,
    headline: toSentenceCase(opportunity.source_event || "opportunity detected"),
    detail: opportunity.recommended_action || "Review and assign to the owner worker set.",
    evidence,
    action: opportunity.recommended_action || "Review and assign to the owner worker set.",
    workers: opportunity.assigned_workers ?? [],
    status: opportunity.status || "queued",
    archiveRef: opportunity.archive_ref || `growth:${opportunity.opportunity_id}`,
  };
}

function iconForOpportunity(kind: string) {
  if (kind === "failed_route") return AlertCircle;
  if (kind === "listing_signal") return Target;
  if (kind === "marketplace_order") return FileCheck2;
  return Radar;
}

function toSentenceCase(input: string): string {
  if (!input) return "";
  const normalized = input.replace(/[_-]/g, " ");
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

function fmtCurrency(value: number): string {
  return `$${value.toFixed(2)}`;
}

function clampPercent(value: number): number {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return 0;
  return Math.max(0, Math.min(100, Math.round(parsed)));
}

function toOperatingSignal(event: UacpEvent): OperatingSignal {
  const severity = String(event.severity ?? "info");
  const risk = severity === "error" ? 88 : severity === "warning" ? 62 : isFailure(event.status) ? 78 : 24;
  const scoreBase = event.event_type === "billing.reserve" ? 78
    : event.event_type === "deployment.state" ? 72
      : event.event_type === "pipeline.run" ? 66
        : event.event_type === "request.failed" ? 64
          : event.event_type === "ai.complete" ? 52
            : 42;
  const score = Math.min(99, scoreBase + (risk > 70 ? 10 : 0));
  const tone: Tone = risk > 70 ? "critical" : risk > 45 ? "watch" : score > 65 ? "stable" : "neutral";
  const workers = event.uacp?.worker_ids ?? [];
  const committee = event.uacp?.committee_ids?.[0] ?? "experience-assurance";
  const pillar = event.uacp?.pillar_ids?.[0] ?? "operations";
  return {
    id: event.event_id,
    title: titleForEvent(event),
    workspace: event.workspace_id ?? event.tenant_id ?? "global",
    eventType: event.event_type,
    score,
    risk,
    tone,
    evidence: evidenceForEvent(event),
    action: actionForEvent(event),
    workers,
    committee,
    pillar,
    archiveRef: `archive:${event.event_id.replace(/[^a-zA-Z0-9_-]/g, "_").slice(0, 42)}`,
    status: String(event.status ?? "unknown"),
    when: event.timestamp,
  };
}

function titleForEvent(event: UacpEvent): string {
  if (event.event_type === "request.failed") return "Backend route needs intervention";
  if (event.event_type === "billing.reserve") return "Reserve ledger movement";
  if (event.event_type === "deployment.state") return "Deployment state changed";
  if (event.event_type === "pipeline.run") return "Governed pipeline execution";
  if (event.event_type === "security.audit") return "Security event recorded";
  if (event.event_type === "ai.complete") return "Governed model run recorded";
  return event.event_type.replace(/[._-]/g, " ");
}

function evidenceForEvent(event: UacpEvent): string[] {
  const payload = event.payload ?? {};
  const items = [
    payload.provider ? `provider ${String(payload.provider)}` : "",
    payload.model ? `model ${String(payload.model)}` : "",
    payload.latency_ms !== undefined ? `latency ${String(payload.latency_ms)}ms` : "",
    payload.cost_usd !== undefined ? `cost $${String(payload.cost_usd)}` : "",
    payload.audit_id ? `audit ${String(payload.audit_id)}` : "",
    payload.error_message ? `error ${String(payload.error_message).slice(0, 44)}` : "",
    event.entity_id ? `${event.entity_type} ${event.entity_id.slice(0, 10)}` : "",
  ].filter(Boolean);
  return items.length ? items : ["backend event present"];
}

function actionForEvent(event: UacpEvent): string {
  if (event.event_type === "request.failed") return "Open incident, inspect route health, assign Sentinel/Sheriff.";
  if (event.event_type === "billing.reserve") return "Validate reserve math and watch paid activation posture.";
  if (event.event_type === "deployment.state") return "Verify endpoint health, logs, usage, and rollback readiness.";
  if (event.event_type === "pipeline.run") return "Attach trace, confirm policy/evidence, decide deploy next action.";
  if (event.event_type === "security.audit") return "Review event, archive evidence, escalate if compliance-sensitive.";
  if (event.event_type === "ai.complete") return "Check run quality, latency, policy result, and evidence continuity.";
  return "Classify signal, assign worker, and write archive reference.";
}

function deriveStories(model: OperatingModel) {
  return [
    {
      title: "The Evaluation Cliff",
      detail: "Free users who consume the full evaluation limit without reserve need activation explained in product language.",
      evidence: `${model.accounts.filter((a) => a.runsUsed >= 15 && a.billingState === "no reserve").length} account(s) at or past 15 runs`,
    },
    {
      title: "The Evidence Signal",
      detail: "Evidence activity is the strongest sign that a buyer is evaluating proof, not just prompting.",
      evidence: `${model.accounts.filter((a) => a.evidenceActivity !== "no evidence").length} account(s) with evidence activity`,
    },
    {
      title: "The Endpoint Moment",
      detail: "Endpoint creation and same-page testing are the point where evaluation becomes infrastructure intent.",
      evidence: `${model.accounts.filter((a) => a.endpointStatus.includes("active") || a.endpointStatus === "created").length} account(s) with endpoint movement`,
    },
    {
      title: "The Trust Gate",
      detail: "Failures, MFA gaps, and unavailable framework/billing routes must be handled before any serious regulated buyer pitch.",
      evidence: `${model.pulse.failedRoutes} failed request(s) in the current backend window`,
    },
  ];
}

function deriveFieldReports(model: OperatingModel) {
  const reports = [];
  if (model.accounts.length) {
    reports.push({
      chapter: "Pattern 01",
      title: "The Demo Trap",
      detail: "Users can run the product without understanding activation. The system must explain limits, reserve, and proof at the moment intent appears.",
      confidence: "live",
      tone: "stable" as Tone,
      evidence: [
        `${model.accounts.length} workspace account(s) loaded`,
        `${model.accounts.filter((a) => a.billingState === "no reserve").length} account(s) without reserve`,
      ],
      workers: ["welcome", "mint", "gauge"],
    });
  }
  if (model.accounts.some((account) => account.evidenceActivity !== "no evidence")) {
    reports.push({
      chapter: "Pattern 02",
      title: "The Evidence Moment",
      detail: "Evidence viewers are signaling compliance/procurement intent. They should see proof-path language, not generic dashboard copy.",
      confidence: "live",
      tone: "watch" as Tone,
      evidence: model.accounts.filter((a) => a.evidenceActivity !== "no evidence").slice(0, 3).map((a) => `${a.name}: ${a.evidenceActivity}`),
      workers: ["ledger", "oracle", "herald"],
    });
  }
  if (model.signals.some((signal) => signal.eventType === "deployment.state")) {
    reports.push({
      chapter: "Pattern 03",
      title: "The Backend Question",
      detail: "Endpoint creation means the user is thinking like infrastructure. Keep testing, logs, and evidence in the same loop.",
      confidence: "live",
      tone: "stable" as Tone,
      evidence: model.signals.filter((signal) => signal.eventType === "deployment.state").slice(0, 3).map((signal) => signal.workspace),
      workers: ["sentinel", "glide", "ledger"],
    });
  }
  if (model.signals.some((signal) => signal.tone === "critical")) {
    reports.push({
      chapter: "Pattern 04",
      title: "The Broken Flow Tax",
      detail: "A failing route is not just technical debt. It lowers trust and delays activation until the worker queue closes the issue.",
      confidence: "live",
      tone: "critical" as Tone,
      evidence: model.signals.filter((signal) => signal.tone === "critical").slice(0, 3).map((signal) => signal.title),
      workers: ["sentinel", "sheriff", "mirror"],
    });
  }
  return reports;
}

function isFailure(status: unknown): boolean {
  return /fail|error|blocked|timeout|unavailable/i.test(String(status ?? ""));
}

function toneClass(tone: Tone, mode: "text" | "bg" | "borderText") {
  const map = {
    stable: { text: "text-moss", bg: "bg-moss", borderText: "border-moss/35 text-moss" },
    watch: { text: "text-amber", bg: "bg-amber", borderText: "border-amber/35 text-amber" },
    critical: { text: "text-crimson", bg: "bg-crimson", borderText: "border-crimson/40 text-crimson" },
    neutral: { text: "text-electric", bg: "bg-electric", borderText: "border-rule-2 text-bone-2" },
  };
  return map[tone][mode];
}

function chipClass(tone: Tone) {
  if (tone === "stable") return "v-chip-ok";
  if (tone === "watch") return "v-chip-warn";
  if (tone === "critical") return "v-chip-err";
  return "v-chip-brass";
}
