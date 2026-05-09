import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { ComponentType, ReactNode } from "react";
import {
  Activity,
  AlertCircle,
  Archive,
  BadgeCheck,
  BriefcaseBusiness,
  CircleDollarSign,
  CircuitBoard,
  Eye,
  FileCheck2,
  Gauge,
  GitBranch,
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

type Room = "overview" | "surgeon" | "growth" | "intelligence";
type Tone = "stable" | "watch" | "critical" | "neutral";

interface SafeResult<T> {
  ok: boolean;
  data?: T;
  error?: string;
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
  created_at?: string;
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
  events: SafeResult<{ events?: UacpEvent[] }>;
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

async function safeGet<T>(path: string, params?: Record<string, unknown>): Promise<SafeResult<T>> {
  try {
    const response = await api.get<T>(path, { params });
    return { ok: true, data: response.data };
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unavailable";
    return { ok: false, error: message };
  }
}

async function fetchControlSnapshot(): Promise<ControlSnapshot> {
  const [summary, events, workspaces, runs, deployments, billing, evidence, security, registry, workerRuns] =
    await Promise.all([
      safeGet<UacpSummary>("/internal/uacp/summary"),
      safeGet<{ events?: UacpEvent[] }>("/internal/uacp/events", { limit: 150 }),
      safeGet<{ workspaces?: WorkspaceRow[] }>("/internal/uacp/workspaces", { limit: 250 }),
      safeGet<{ runs?: RunRow[] }>("/internal/uacp/runs", { limit: 250 }),
      safeGet<{ deployments?: DeploymentRow[] }>("/internal/uacp/deployments", { limit: 250 }),
      safeGet<{ reserve_units_total?: number; transactions?: BillingRow[] }>("/internal/uacp/billing", { limit: 250 }),
      safeGet<{ evidence?: EvidenceRow[] }>("/internal/uacp/evidence", { limit: 250 }),
      safeGet<{ security_events?: SecurityEventRow[] }>("/internal/uacp/security", { limit: 250 }),
      safeGet<{ workers?: WorkerRow[]; committees?: CommitteeRow[] }>("/internal/operators/registry"),
      safeGet<{ runs?: WorkerRunRow[]; count?: number }>("/internal/operators/runs", { limit: 150 }),
    ]);

  return { summary, events, workspaces, runs, deployments, billing, evidence, security, registry, workerRuns };
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
            <HeaderMetric label="Active evaluations" value={fmtNumber(model.pulse.activeEvaluations)} />
            <HeaderMetric label="Serious signals" value={fmtNumber(model.pulse.seriousSignals)} />
            <HeaderMetric label="Reserve live" value={model.pulse.reserveLive} />
            <HeaderMetric label="Worker confidence" value={`${model.pulse.workerConfidence}%`} />
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
          {room === "surgeon" && <EvaluationSurgeon accounts={model.accounts} loading={snapshot.isLoading} />}
          {room === "growth" && <GrowthNavigator model={model} loading={snapshot.isLoading} />}
          {room === "intelligence" && <FieldIntelligence model={model} loading={snapshot.isLoading} />}
        </section>
        <aside className="space-y-4">
          <WorkerQueue workers={model.workers} workerRuns={model.workerRuns} />
          <DoctrinePanel />
          <ArchivePanel signals={model.signals} />
        </aside>
      </main>
    </div>
  );
}

function OverviewRoom({ model, loading }: { model: OperatingModel; loading: boolean }) {
  const stories = deriveStories(model);
  return (
    <div className="space-y-4">
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
          <div className="divide-y divide-rule">
            {model.signals.slice(0, 8).map((signal) => (
              <SignalRow key={signal.id} signal={signal} />
            ))}
            {!model.signals.length && (
              <EmptyState text={loading ? "Synchronizing backend event stream." : "No backend events available from `/internal/uacp/events`."} />
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

function EvaluationSurgeon({ accounts, loading }: { accounts: EvaluationAccount[]; loading: boolean }) {
  return (
    <section className="border border-rule bg-ink-2/40">
      <PanelHead icon={BriefcaseBusiness} label="Evaluation Surgeon Queue" meta={`${accounts.length} workspace account${accounts.length === 1 ? "" : "s"}`} />
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
        <EmptyState text={loading ? "Loading workspaces and run history." : "No workspace records returned from `/internal/uacp/workspaces`."} />
      )}
    </section>
  );
}

function GrowthNavigator({ model, loading }: { model: OperatingModel; loading: boolean }) {
  const opportunities = deriveGrowthOpportunities(model);
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
          <EmptyState text={loading ? "Building opportunity map from live data." : "No growth opportunities can be ranked until live buyer/vendor/tool signals exist."} />
        </div>
      )}
    </div>
  );
}

function FieldIntelligence({ model, loading }: { model: OperatingModel; loading: boolean }) {
  const reports = deriveFieldReports(model);
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
        <EmptyState text={loading ? "Synchronizing field intelligence." : "No intelligence reports can be generated without product events, worker runs, or marketplace signals."} />
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
  workers: WorkerRow[];
  committees: CommitteeRow[];
  workerRuns: WorkerRunRow[];
  raw: ControlSnapshot | undefined;
}

function buildOperatingModel(snapshot?: ControlSnapshot): OperatingModel {
  const summary = snapshot?.summary.data;
  const product = summary?.product_truth ?? {};
  const workers = snapshot?.registry.data?.workers ?? [];
  const committees = snapshot?.registry.data?.committees ?? [];
  const workerRuns = snapshot?.workerRuns.data?.runs ?? [];
  const events = snapshot?.events.data?.events ?? [];
  const workspaces = snapshot?.workspaces.data?.workspaces ?? [];
  const runs = snapshot?.runs.data?.runs ?? [];
  const deployments = snapshot?.deployments.data?.deployments ?? [];
  const billing = snapshot?.billing.data?.transactions ?? [];
  const evidence = snapshot?.evidence.data?.evidence ?? [];
  const security = snapshot?.security.data?.security_events ?? [];
  const signals = events.map(toOperatingSignal).sort((a, b) => (b.score + b.risk) - (a.score + a.risk));
  const accounts = buildEvaluationAccounts({ workspaces, runs, deployments, billing, evidence, security });
  const readyWorkers = workers.filter((worker) => worker.status === "ready").length;

  return {
    generatedAt: summary?.generated_at,
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
    signals,
    accounts,
    workers,
    committees,
    workerRuns,
    raw: snapshot,
  };
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

function buildEvaluationAccounts(input: {
  workspaces: WorkspaceRow[];
  runs: RunRow[];
  deployments: DeploymentRow[];
  billing: BillingRow[];
  evidence: EvidenceRow[];
  security: SecurityEventRow[];
}): EvaluationAccount[] {
  return input.workspaces.map((workspace) => {
    const workspaceId = workspace.workspace_id;
    const runs = input.runs.filter((run) => run.workspace_id === workspaceId);
    const failedRuns = runs.filter((run) => isFailure(run.status));
    const deployments = input.deployments.filter((deployment) => deployment.workspace_id === workspaceId);
    const evidence = input.evidence.filter((row) => row.workspace_id === workspaceId);
    const txs = input.billing.filter((tx) => tx.workspace_id === workspaceId);
    const reserveLast = txs[0]?.balance_after_units ?? 0;
    const hasReserve = reserveLast > 0 || txs.some((tx) => (tx.amount_units ?? 0) > 0);
    const lastActivity = latestDate([
      ...runs.map((run) => run.created_at),
      ...deployments.map((deployment) => deployment.updated_at ?? deployment.last_health_check ?? undefined),
      ...evidence.map((row) => row.created_at),
      ...txs.map((tx) => tx.created_at),
    ]);
    const endpointActive = deployments.some((deployment) => deployment.status === "active");
    const riskScore = Math.min(99, Math.round((failedRuns.length * 18) + (!hasReserve && runs.length >= 10 ? 32 : 0) + (!lastActivity ? 20 : 0)));
    const activationProbability = Math.min(99, Math.round(
      runs.length * 4 +
      (endpointActive ? 24 : 0) +
      (evidence.length ? 18 : 0) +
      (txs.length ? 12 : 0) -
      failedRuns.length * 8,
    ));
    return {
      workspaceId,
      name: workspace.name || workspace.slug || workspaceId,
      tier: workspace.license_tier || "free evaluation",
      runsUsed: runs.length,
      lastActivity,
      endpointStatus: endpointActive ? "active endpoint" : deployments.length ? "created" : "none",
      evidenceActivity: evidence.length ? `${evidence.length} audit record${evidence.length === 1 ? "" : "s"}` : "no evidence",
      billingState: hasReserve ? "reserve live" : "no reserve",
      riskScore,
      activationProbability: Math.max(0, activationProbability),
      topAction: topActionForAccount({ runs: runs.length, endpointActive, evidenceCount: evidence.length, hasReserve, failedRuns: failedRuns.length }),
      workers: workersForAccount({ endpointActive, evidenceCount: evidence.length, hasReserve, failedRuns: failedRuns.length }),
      evidence: [
        `${runs.length} run${runs.length === 1 ? "" : "s"}`,
        endpointActive ? "endpoint active" : "endpoint not active",
        evidence.length ? "evidence viewed/created" : "no evidence yet",
        hasReserve ? "cash reserve present" : "no reserve",
      ],
    };
  }).sort((a, b) => (b.activationProbability + b.riskScore) - (a.activationProbability + a.riskScore));
}

function topActionForAccount(input: { runs: number; endpointActive: boolean; evidenceCount: number; hasReserve: boolean; failedRuns: number }) {
  if (input.failedRuns) return "Ask what broke and route Sentinel/Sheriff before selling.";
  if (input.runs >= 15 && !input.hasReserve) return "Explain activation and reserve requirement.";
  if (input.endpointActive && input.evidenceCount && !input.hasReserve) return "Send activation note with evidence/proof framing.";
  if (input.endpointActive && !input.evidenceCount) return "Guide user to evidence trace and audit proof.";
  if (input.runs > 0 && !input.endpointActive) return "Move from Playground/Pipeline into endpoint verification.";
  return "Welcome sequence: get first governed run completed.";
}

function workersForAccount(input: { endpointActive: boolean; evidenceCount: number; hasReserve: boolean; failedRuns: number }) {
  if (input.failedRuns) return ["sentinel", "sheriff", "mirror"];
  if (!input.hasReserve) return ["welcome", "mint", "ledger"];
  if (input.endpointActive && input.evidenceCount) return ["gauge", "ledger", "herald"];
  return ["welcome", "glide", "pulse"];
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

function deriveGrowthOpportunities(model: OperatingModel) {
  const seriousAccounts = model.accounts.filter((account) => account.activationProbability >= 55 || account.riskScore >= 60);
  const failedSignals = model.signals.filter((signal) => signal.tone === "critical");
  const evidenceAccounts = model.accounts.filter((account) => account.evidenceActivity !== "no evidence");
  const opportunities = [];

  if (seriousAccounts.length) {
    opportunities.push({
      title: "Buyer Opportunity",
      meta: `${seriousAccounts.length} ranked account${seriousAccounts.length === 1 ? "" : "s"}`,
      icon: Target,
      score: Math.min(99, 50 + seriousAccounts.length * 10),
      tone: "stable" as Tone,
      headline: "Evaluation accounts are showing activation intent.",
      detail: "Prioritize accounts with runs, endpoint movement, billing page interest, evidence activity, or limit pressure.",
      evidence: seriousAccounts.slice(0, 4).map((account) => `${account.name}: ${account.activationProbability}% activation`),
      action: "Route Welcome + Mint + Ledger to explain activation, reserve, and proof.",
      workers: ["welcome", "mint", "ledger"],
    });
  }

  if (failedSignals.length) {
    opportunities.push({
      title: "Product Friction",
      meta: `${failedSignals.length} critical signal${failedSignals.length === 1 ? "" : "s"}`,
      icon: AlertCircle,
      score: Math.min(99, 60 + failedSignals.length * 8),
      tone: "critical" as Tone,
      headline: "Broken routes are creating sales drag.",
      detail: "Any Network Error, timeout, QR failure, billing timeout, or compliance timeout must become a worker-owned queue item.",
      evidence: failedSignals.slice(0, 4).map((signal) => signal.title),
      action: "Assign Sentinel/Sheriff/Mirror and keep the signal open until live proof clears.",
      workers: ["sentinel", "sheriff", "mirror"],
    });
  }

  if (evidenceAccounts.length) {
    opportunities.push({
      title: "Regulated Access",
      meta: `${evidenceAccounts.length} proof-seeking account${evidenceAccounts.length === 1 ? "" : "s"}`,
      icon: FileCheck2,
      score: Math.min(99, 58 + evidenceAccounts.length * 7),
      tone: "watch" as Tone,
      headline: "Evidence interest should trigger regulated-path guidance.",
      detail: "Buyers opening evidence are likely asking whether Veklom can prove governed operation, not whether it can chat.",
      evidence: evidenceAccounts.slice(0, 4).map((account) => `${account.name}: ${account.evidenceActivity}`),
      action: "Attach evidence explanation and offer regulated/private deployment path.",
      workers: ["ledger", "oracle", "herald"],
    });
  }

  opportunities.push({
    title: "Tool Asset Pipeline",
    meta: "builder lane",
    icon: GitBranch,
    score: model.workers.some((worker) => worker.id === "builder-scout") ? 52 : 0,
    tone: "neutral" as Tone,
    headline: "Builder workers are registered, but opportunity ingestion must stay evidence-led.",
    detail: "Use public-source pain only when provenance, no-copy rules, and release gates are recorded.",
    evidence: ["builder-scout registered", "builder-forge registered", "builder-arbiter registered"].filter((line) =>
      model.workers.some((worker) => line.startsWith(worker.id ?? "")),
    ),
    action: "Start with read-only opportunity dossiers before autonomous build/write actions.",
    workers: ["builder-scout", "builder-arbiter", "builder-forge"],
  });

  return opportunities;
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

function latestDate(values: Array<string | null | undefined>): string | undefined {
  const sorted = values
    .filter((value): value is string => Boolean(value))
    .sort((a, b) => new Date(b).getTime() - new Date(a).getTime());
  return sorted[0];
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
