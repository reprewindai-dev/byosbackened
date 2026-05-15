import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Activity, AlertTriangle, BrainCircuit, ShieldCheck, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import {
  fetchEvaluationSurgeon,
  fetchGrowthOpportunities,
  fetchMonitoringAlerts,
  fetchMonitoringHealth,
  fetchOperatorDigest,
  fetchOperatorOverview,
  fetchStatusRail,
  fetchUacpMonitoring,
  fetchUacpSummary,
  subscribeStatus,
  type StatusSubscriptionChannel,
} from "@/lib/services/runtime-truth.service";
import { useAuthStore } from "@/store/auth-store";

type Suggestion = {
  type: string;
  title: string;
  description: string;
  impact: string;
  effort: string;
  priority: number;
  action: string;
};

type SuggestionsResponse = {
  suggestions: Suggestion[];
  count: number;
};

type SuggestionsSummary = {
  total: number;
  by_type: Record<string, number>;
  by_impact: Record<string, number>;
};

type StatusItem = {
  id?: string;
  title?: string;
  description?: string;
  severity?: string;
  status?: string;
  created_at?: string;
  updated_at?: string;
};

type StatusPayload = {
  timestamp?: string;
  status?: string;
  current_status?: string;
  overall_status?: string;
  incidents?: StatusItem[];
  maintenance?: StatusItem[];
};

type MonitoringHealth = {
  status?: string;
  score?: number;
  detail?: string;
  message?: string;
};

type OperatorFinding = {
  code: string;
  title: string;
  severity: string;
  signal: string;
  diagnosis: string;
  operator_action: string;
  self_healing_action?: string | null;
};

type OperatorDigest = {
  status: string;
  generated_at: string;
  summary: Record<string, number>;
  findings: OperatorFinding[];
  persistence?: {
    created?: number;
    updated?: number;
    enabled?: boolean;
  };
};

type OperatorOverview = {
  status?: string;
  worker_count?: number;
  ready_workers?: number;
  committee_count?: number;
  minimum_live_count?: number;
  minimum_live_ready?: number;
  recent_failure_count?: number;
  generated_at?: string;
  needs_config?: string[];
};

type UacpTruth = {
  worker_count?: number;
  committee_count?: number;
  event_owner_mappings?: number;
  write_surface?: string;
  read_surface?: string;
  evaluation_surgeon_queue_count?: number;
  growth_opportunity_count?: number;
};

type UacpSummary = {
  source?: string;
  contract_version?: string;
  generated_at?: string;
  uacp_truth?: UacpTruth;
};

type UacpMonitoring = {
  source?: string;
  contract_version?: string;
  generated_at?: string;
  monitoring?: {
    generated_at?: string;
    healthy?: boolean;
    product_truth?: {
      requests_24h?: number;
      failed_requests_24h?: number;
      open_alerts?: number;
      deployments?: number;
    };
    uacp_truth?: UacpTruth;
    permission_boundary?: {
      blocked_without_approval?: string[];
    };
  };
};

type UacpQueueResponse = {
  source?: string;
  contract_version?: string;
  queue?: Array<Record<string, unknown>>;
  opportunities?: Array<Record<string, unknown>>;
  empty_reason?: string | null;
  required_sources?: string[];
};

type StatusSubscribeResponse = {
  id: string;
  channel: string;
  status: string;
  verification_status: string;
  target: string;
  confirmation_sent: boolean;
  json_url: string;
  rss_url: string;
};

async function fetchSuggestions() {
  return (await api.get<SuggestionsResponse>("/suggestions")).data;
}

async function fetchSuggestionsSummary() {
  return (await api.get<SuggestionsSummary>("/suggestions/summary")).data;
}

function asAlertList(value: unknown): Array<Record<string, unknown>> {
  if (Array.isArray(value)) return value as Array<Record<string, unknown>>;
  if (value && typeof value === "object") {
    const record = value as Record<string, unknown>;
    if (Array.isArray(record.alerts)) return record.alerts as Array<Record<string, unknown>>;
    if (Array.isArray(record.items)) return record.items as Array<Record<string, unknown>>;
  }
  return [];
}

function formatTimestamp(value?: string) {
  if (!value) return "unavailable";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return `${date.toLocaleDateString()} ${date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
}

function compactList(values: string[] | undefined, count = 4) {
  return (values ?? []).filter(Boolean).slice(0, count);
}

function labelUnknownItem(item: Record<string, unknown>) {
  const preferredKeys = ["title", "archive_ref", "workspace_id", "route_key", "listing_id", "deployment_id", "id"];
  for (const key of preferredKeys) {
    const value = item[key];
    if (typeof value === "string" && value.trim()) return `${key}: ${value}`;
  }
  for (const [key, value] of Object.entries(item)) {
    if (typeof value === "string" && value.trim()) return `${key}: ${value}`;
    if (typeof value === "number") return `${key}: ${String(value)}`;
  }
  return "backend item";
}

function detailUnknownItem(item: Record<string, unknown>) {
  const parts: string[] = [];
  if (typeof item.status === "string" && item.status.trim()) parts.push(`status: ${item.status}`);
  if (Array.isArray(item.assigned_workers) && item.assigned_workers.length) parts.push(`workers: ${item.assigned_workers.join(", ")}`);
  if (typeof item.committee_id === "string" && item.committee_id.trim()) parts.push(`committee: ${item.committee_id}`);
  if (Array.isArray(item.pillar_ids) && item.pillar_ids.length) parts.push(`pillars: ${item.pillar_ids.join(", ")}`);
  return parts;
}

function StatCard({
  icon: Icon,
  label,
  value,
  detail,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="frame p-4">
      <div className="flex items-center justify-between gap-3">
        <div className="text-eyebrow">{label}</div>
        <Icon className="h-4 w-4 text-brass" />
      </div>
      <div className="mt-4 font-mono text-2xl font-semibold text-bone">{value}</div>
      <div className="mt-2 text-xs leading-5 text-muted">{detail}</div>
    </div>
  );
}

export function AutonomyPage() {
  const user = useAuthStore((state) => state.user);
  const isSuperuser = Boolean(user?.is_superuser);
  const [channel, setChannel] = useState<StatusSubscriptionChannel>("email");
  const [target, setTarget] = useState("");

  const suggestionsQ = useQuery({
    queryKey: ["autonomy-suggestions"],
    queryFn: fetchSuggestions,
    refetchInterval: 60_000,
  });
  const suggestionsSummaryQ = useQuery({
    queryKey: ["autonomy-suggestions-summary"],
    queryFn: fetchSuggestionsSummary,
    refetchInterval: 60_000,
  });
  const statusQ = useQuery({
    queryKey: ["autonomy-status-rail"],
    queryFn: () => fetchStatusRail<StatusPayload>(),
    refetchInterval: 60_000,
  });
  const healthQ = useQuery({
    queryKey: ["autonomy-monitoring-health"],
    queryFn: () => fetchMonitoringHealth<MonitoringHealth>(),
    refetchInterval: 30_000,
  });
  const alertsQ = useQuery({
    queryKey: ["autonomy-monitoring-alerts"],
    queryFn: () => fetchMonitoringAlerts<unknown>(),
    refetchInterval: 30_000,
  });
  const operatorDigestQ = useQuery({
    queryKey: ["autonomy-operator-digest"],
    queryFn: () => fetchOperatorDigest<OperatorDigest>(),
    enabled: isSuperuser,
    retry: false,
    refetchInterval: 60_000,
  });
  const operatorOverviewQ = useQuery({
    queryKey: ["autonomy-operator-overview"],
    queryFn: () => fetchOperatorOverview<OperatorOverview>(),
    enabled: isSuperuser,
    retry: false,
    refetchInterval: 60_000,
  });
  const uacpSummaryQ = useQuery({
    queryKey: ["autonomy-uacp-summary"],
    queryFn: () => fetchUacpSummary<UacpSummary>(),
    enabled: isSuperuser,
    retry: false,
    refetchInterval: 60_000,
  });
  const uacpMonitoringQ = useQuery({
    queryKey: ["autonomy-uacp-monitoring"],
    queryFn: () => fetchUacpMonitoring<UacpMonitoring>(),
    enabled: isSuperuser,
    retry: false,
    refetchInterval: 60_000,
  });
  const evaluationSurgeonQ = useQuery({
    queryKey: ["autonomy-uacp-evaluation-surgeon"],
    queryFn: () => fetchEvaluationSurgeon<UacpQueueResponse>(),
    enabled: isSuperuser,
    retry: false,
    refetchInterval: 60_000,
  });
  const growthOpportunitiesQ = useQuery({
    queryKey: ["autonomy-uacp-growth-opportunities"],
    queryFn: () => fetchGrowthOpportunities<UacpQueueResponse>(),
    enabled: isSuperuser,
    retry: false,
    refetchInterval: 60_000,
  });

  const highImpactCount = suggestionsSummaryQ.data?.by_impact?.high ?? 0;
  const alerts = useMemo(() => asAlertList(alertsQ.data), [alertsQ.data]);
  const incidents = statusQ.data?.incidents ?? [];
  const maintenance = statusQ.data?.maintenance ?? [];
  const uacpTruth = uacpSummaryQ.data?.uacp_truth ?? uacpMonitoringQ.data?.monitoring?.uacp_truth;
  const productTruth = uacpMonitoringQ.data?.monitoring?.product_truth;
  const blockedActions = compactList(uacpMonitoringQ.data?.monitoring?.permission_boundary?.blocked_without_approval, 6);
  const needsConfig = compactList(operatorOverviewQ.data?.needs_config, 8);
  const evaluationQueue = evaluationSurgeonQ.data?.queue ?? [];
  const growthQueue = growthOpportunitiesQ.data?.opportunities ?? [];
  const statusSubscribe = useMutation({
    mutationFn: ({ nextChannel, nextTarget }: { nextChannel: StatusSubscriptionChannel; nextTarget: string }) =>
      subscribeStatus<StatusSubscribeResponse>(nextChannel, nextTarget),
  });

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-5">
      <header className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
        <div>
          <div className="text-eyebrow">Operations / Autonomy</div>
          <h1 className="mt-2 text-3xl font-semibold tracking-[-0.035em] text-bone">Backend-owned autonomous shell</h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-bone-2">
            This surface is wired to real backend signals only: optimization suggestions, public status rail, monitoring health,
            alert pressure, and the internal operator watch loop when the caller is authorized.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <span className="v-chip v-chip-ok">live backend truth</span>
            <span className="v-chip">status rail</span>
            <span className="v-chip">monitoring health</span>
            {isSuperuser ? <span className="v-chip v-chip-brass">operator watch</span> : null}
            {isSuperuser ? <span className="v-chip v-chip-brass">uacp queues</span> : null}
          </div>
        </div>

        <aside className="frame p-4">
          <div className="text-eyebrow">Runtime posture</div>
          <div className="mt-2 text-sm font-semibold text-bone">
            {healthQ.data?.status ?? "unknown"} / {statusQ.data?.overall_status ?? statusQ.data?.current_status ?? "operational rail"}
          </div>
          <div className="mt-2 text-xs leading-5 text-muted">
            Status feed updates: {formatTimestamp(statusQ.data?.timestamp)}. Monitoring health score:{" "}
            {healthQ.data?.score == null ? "unavailable" : String(healthQ.data.score)}.
          </div>
          <div className="mt-4 grid grid-cols-2 gap-2 text-xs text-muted">
            <div className="rounded-lg border border-rule bg-ink-1 px-3 py-2">
              <div className="font-mono text-[9px] uppercase tracking-[0.12em] text-muted">suggestions</div>
              <div className="mt-1 text-bone">{suggestionsSummaryQ.data?.total ?? suggestionsQ.data?.count ?? 0}</div>
            </div>
            <div className="rounded-lg border border-rule bg-ink-1 px-3 py-2">
              <div className="font-mono text-[9px] uppercase tracking-[0.12em] text-muted">alerts</div>
              <div className="mt-1 text-bone">{alerts.length}</div>
            </div>
            <div className="rounded-lg border border-rule bg-ink-1 px-3 py-2">
              <div className="font-mono text-[9px] uppercase tracking-[0.12em] text-muted">incidents</div>
              <div className="mt-1 text-bone">{incidents.length}</div>
            </div>
            <div className="rounded-lg border border-rule bg-ink-1 px-3 py-2">
              <div className="font-mono text-[9px] uppercase tracking-[0.12em] text-muted">maintenance</div>
              <div className="mt-1 text-bone">{maintenance.length}</div>
            </div>
          </div>
        </aside>
      </header>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <StatCard
          icon={Sparkles}
          label="Optimization queue"
          value={String(suggestionsSummaryQ.data?.total ?? suggestionsQ.data?.count ?? 0)}
          detail="Proactive backend suggestions, not static tips."
        />
        <StatCard
          icon={BrainCircuit}
          label="High impact"
          value={String(highImpactCount)}
          detail="Suggestions that should materially improve cost or performance."
        />
        <StatCard
          icon={ShieldCheck}
          label="Health status"
          value={healthQ.data?.status ?? "unknown"}
          detail={healthQ.data?.detail ?? healthQ.data?.message ?? "Monitoring route did not return detail."}
        />
        <StatCard
          icon={AlertTriangle}
          label="Open alerts"
          value={String(alerts.length)}
          detail="Live alert pressure from monitoring, not placeholder counters."
        />
        <StatCard
          icon={Activity}
          label="Status rail"
          value={statusQ.data?.overall_status ?? statusQ.data?.current_status ?? "operational"}
          detail="Incident and maintenance feed backed by the public status endpoints."
        />
      </section>

      <section className="frame p-4">
        <div className="text-eyebrow">Notification rail</div>
        <h2 className="mt-2 text-lg font-semibold text-bone">Subscribe to public incident and maintenance updates</h2>
        <div className="mt-2 text-xs leading-5 text-muted">
          This uses the live backend status subscription endpoint. Email sends a confirmation message. Slack posts a live webhook confirmation.
        </div>
        <div className="mt-4 grid gap-3 lg:grid-cols-[0.22fr_0.5fr_0.28fr]">
          <select
            className="v-input"
            value={channel}
            onChange={(e) => setChannel(e.target.value === "slack" ? "slack" : "email")}
          >
            <option value="email">email</option>
            <option value="slack">slack</option>
          </select>
          <input
            className="v-input"
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            placeholder={channel === "email" ? "ops@company.com" : "https://hooks.slack.com/services/..."}
          />
          <button
            type="button"
            className="v-btn-primary h-11"
            disabled={statusSubscribe.isPending || !target.trim()}
            onClick={() => statusSubscribe.mutate({ nextChannel: channel, nextTarget: target.trim() })}
          >
            {statusSubscribe.isPending ? "Subscribing..." : "Enable updates"}
          </button>
        </div>
        {statusSubscribe.data ? (
          <div className="mt-3 rounded-lg border border-rule bg-ink-1/70 p-3 text-sm text-bone-2">
            <div className="font-semibold text-bone">Subscription active</div>
            <div className="mt-1 text-xs leading-5">
              {statusSubscribe.data.channel} {"->"} {statusSubscribe.data.target} / {statusSubscribe.data.verification_status}
            </div>
            <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-muted">
              <span className="rounded border border-rule px-2 py-1">{statusSubscribe.data.json_url}</span>
              <span className="rounded border border-rule px-2 py-1">{statusSubscribe.data.rss_url}</span>
            </div>
          </div>
        ) : null}
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="frame p-4">
          <div className="text-eyebrow">Optimization suggestions</div>
          <h2 className="mt-2 text-lg font-semibold text-bone">Self-improving guidance from live workspace signals</h2>
          <div className="mt-4 space-y-3">
            {(suggestionsQ.data?.suggestions ?? []).slice(0, 8).map((item) => (
              <div key={`${item.type}-${item.title}`} className="rounded-lg border border-rule bg-ink-1/70 p-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="font-semibold text-bone">{item.title}</div>
                    <div className="mt-1 text-xs leading-5 text-bone-2">{item.description}</div>
                  </div>
                  <span className="v-chip v-chip-brass">{item.impact}</span>
                </div>
                <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-muted">
                  <span className="rounded border border-rule px-2 py-1">type: {item.type}</span>
                  <span className="rounded border border-rule px-2 py-1">effort: {item.effort}</span>
                  <span className="rounded border border-rule px-2 py-1">action: {item.action}</span>
                </div>
              </div>
            ))}
            {!suggestionsQ.isLoading && (suggestionsQ.data?.suggestions?.length ?? 0) === 0 ? (
              <div className="rounded-lg border border-dashed border-rule bg-white/[0.02] px-4 py-8 text-center text-sm text-muted">
                No live suggestions returned for this workspace.
              </div>
            ) : null}
          </div>
        </div>

        <div className="space-y-4">
          <div className="frame p-4">
            <div className="text-eyebrow">Status rail</div>
            <h2 className="mt-2 text-lg font-semibold text-bone">Incident and maintenance notifications</h2>
            <div className="mt-4 space-y-3">
              {[...incidents, ...maintenance].slice(0, 6).map((item) => (
                <div key={item.id ?? `${item.title}-${item.created_at}`} className="rounded-lg border border-rule bg-ink-1/70 p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="font-semibold text-bone">{item.title ?? "Status item"}</div>
                      <div className="mt-1 text-xs leading-5 text-bone-2">{item.description ?? "No detail provided."}</div>
                    </div>
                    <span className="v-chip">{item.severity ?? item.status ?? "status"}</span>
                  </div>
                  <div className="mt-2 text-[11px] text-muted">{formatTimestamp(item.updated_at ?? item.created_at)}</div>
                </div>
              ))}
              {!statusQ.isLoading && incidents.length === 0 && maintenance.length === 0 ? (
                <div className="rounded-lg border border-dashed border-rule bg-white/[0.02] px-4 py-8 text-center text-sm text-muted">
                  No active incidents or maintenance windows were returned.
                </div>
              ) : null}
            </div>
          </div>

          <div className="frame p-4">
            <div className="text-eyebrow">Monitoring health</div>
            <h2 className="mt-2 text-lg font-semibold text-bone">Truthful runtime posture</h2>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <div className="rounded-lg border border-rule bg-ink-1/70 p-3">
                <div className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted">health status</div>
                <div className="mt-2 text-lg font-semibold text-bone">{healthQ.data?.status ?? "unknown"}</div>
              </div>
              <div className="rounded-lg border border-rule bg-ink-1/70 p-3">
                <div className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted">health score</div>
                <div className="mt-2 text-lg font-semibold text-bone">
                  {healthQ.data?.score == null ? "unavailable" : String(healthQ.data.score)}
                </div>
              </div>
            </div>
            <div className="mt-3 text-xs leading-5 text-muted">
              {healthQ.data?.detail ?? healthQ.data?.message ?? "Monitoring health route returned no additional detail."}
            </div>
          </div>
        </div>
      </section>

      {isSuperuser ? (
        <section className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
          <div className="space-y-4">
            <div className="frame p-4">
              <div className="text-eyebrow">Operator and UACP spine</div>
              <h2 className="mt-2 text-lg font-semibold text-bone">Internal runtime cues for the command layer</h2>
              <div className="mt-2 text-xs leading-5 text-muted">
                These cards are grounded to internal operator overview, UACP summary, and UACP monitoring instead of frontend-only counters.
              </div>
              <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                <div className="rounded-lg border border-rule bg-ink-1/70 p-3">
                  <div className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted">operator status</div>
                  <div className="mt-2 text-lg font-semibold text-bone">{operatorOverviewQ.data?.status ?? "unavailable"}</div>
                </div>
                <div className="rounded-lg border border-rule bg-ink-1/70 p-3">
                  <div className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted">ready workers</div>
                  <div className="mt-2 text-lg font-semibold text-bone">
                    {operatorOverviewQ.data?.ready_workers ?? 0} / {operatorOverviewQ.data?.worker_count ?? 0}
                  </div>
                </div>
                <div className="rounded-lg border border-rule bg-ink-1/70 p-3">
                  <div className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted">minimum live</div>
                  <div className="mt-2 text-lg font-semibold text-bone">
                    {operatorOverviewQ.data?.minimum_live_ready ?? 0} / {operatorOverviewQ.data?.minimum_live_count ?? 0}
                  </div>
                </div>
                <div className="rounded-lg border border-rule bg-ink-1/70 p-3">
                  <div className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted">committees</div>
                  <div className="mt-2 text-lg font-semibold text-bone">{uacpTruth?.committee_count ?? operatorOverviewQ.data?.committee_count ?? 0}</div>
                </div>
                <div className="rounded-lg border border-rule bg-ink-1/70 p-3">
                  <div className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted">evaluation queue</div>
                  <div className="mt-2 text-lg font-semibold text-bone">{uacpTruth?.evaluation_surgeon_queue_count ?? evaluationQueue.length}</div>
                </div>
                <div className="rounded-lg border border-rule bg-ink-1/70 p-3">
                  <div className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted">growth opportunities</div>
                  <div className="mt-2 text-lg font-semibold text-bone">{uacpTruth?.growth_opportunity_count ?? growthQueue.length}</div>
                </div>
              </div>

              <div className="mt-4 grid gap-4 lg:grid-cols-2">
                <div className="rounded-lg border border-rule bg-ink-1/70 p-3">
                  <div className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted">UACP contract</div>
                  <div className="mt-3 space-y-2 text-xs text-bone-2">
                    <div>source: {uacpSummaryQ.data?.source ?? uacpMonitoringQ.data?.source ?? "unavailable"}</div>
                    <div>contract: {uacpSummaryQ.data?.contract_version ?? uacpMonitoringQ.data?.contract_version ?? "unavailable"}</div>
                    <div>read surface: {uacpTruth?.read_surface ?? "unavailable"}</div>
                    <div>write surface: {uacpTruth?.write_surface ?? "unavailable"}</div>
                    <div>generated: {formatTimestamp(uacpSummaryQ.data?.generated_at ?? uacpMonitoringQ.data?.generated_at)}</div>
                  </div>
                </div>
                <div className="rounded-lg border border-rule bg-ink-1/70 p-3">
                  <div className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted">Runtime pressure</div>
                  <div className="mt-3 space-y-2 text-xs text-bone-2">
                    <div>requests 24h: {productTruth?.requests_24h ?? 0}</div>
                    <div>failed requests 24h: {productTruth?.failed_requests_24h ?? 0}</div>
                    <div>open alerts: {productTruth?.open_alerts ?? 0}</div>
                    <div>deployments: {productTruth?.deployments ?? 0}</div>
                    <div>monitoring healthy: {uacpMonitoringQ.data?.monitoring?.healthy ? "true" : "false"}</div>
                  </div>
                </div>
              </div>

              {needsConfig.length ? (
                <div className="mt-4">
                  <div className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted">workers needing config</div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {needsConfig.map((workerId) => (
                      <span key={workerId} className="rounded border border-rule px-2 py-1 text-[11px] text-muted">
                        {workerId}
                      </span>
                    ))}
                  </div>
                </div>
              ) : null}

              {blockedActions.length ? (
                <div className="mt-4">
                  <div className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted">blocked without approval</div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {blockedActions.map((action) => (
                      <span key={action} className="rounded border border-rule px-2 py-1 text-[11px] text-muted">
                        {action}
                      </span>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>

            <div className="frame p-4">
              <div className="text-eyebrow">Internal operator watch</div>
              <h2 className="mt-2 text-lg font-semibold text-bone">Pre-critical backend watch loop</h2>
              <div className="mt-2 text-xs leading-5 text-muted">
                This is the persisted operator digest: latency pressure, error-rate pressure, fallback drift, audit drift, and
                backlog findings before a visible outage.
              </div>
              <div className="mt-4 grid gap-3 sm:grid-cols-3">
                <div className="rounded-lg border border-rule bg-ink-1/70 p-3">
                  <div className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted">watch status</div>
                  <div className="mt-2 text-lg font-semibold text-bone">{operatorDigestQ.data?.status ?? "unavailable"}</div>
                </div>
                <div className="rounded-lg border border-rule bg-ink-1/70 p-3">
                  <div className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted">high-impact findings</div>
                  <div className="mt-2 text-lg font-semibold text-bone">{operatorDigestQ.data?.findings?.length ?? 0}</div>
                </div>
                <div className="rounded-lg border border-rule bg-ink-1/70 p-3">
                  <div className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted">last digest</div>
                  <div className="mt-2 text-sm font-semibold text-bone">{formatTimestamp(operatorDigestQ.data?.generated_at)}</div>
                </div>
              </div>
              <div className="mt-4 space-y-3">
                {(operatorDigestQ.data?.findings ?? []).slice(0, 6).map((item) => (
                  <div key={item.code} className="rounded-lg border border-rule bg-ink-1/70 p-3">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="font-semibold text-bone">{item.title}</div>
                        <div className="mt-1 text-xs leading-5 text-bone-2">{item.diagnosis}</div>
                      </div>
                      <span className="v-chip v-chip-brass">{item.severity}</span>
                    </div>
                    <div className="mt-3 grid gap-2 text-[11px] text-muted">
                      <div>signal: {item.signal}</div>
                      <div>operator action: {item.operator_action}</div>
                      {item.self_healing_action ? <div>self-healing evidence: {item.self_healing_action}</div> : null}
                    </div>
                  </div>
                ))}
                {!operatorDigestQ.isLoading && (operatorDigestQ.data?.findings?.length ?? 0) === 0 ? (
                  <div className="rounded-lg border border-dashed border-rule bg-white/[0.02] px-4 py-8 text-center text-sm text-muted">
                    Operator digest returned no current findings.
                  </div>
                ) : null}
              </div>
            </div>
          </div>

          <div className="frame p-4">
            <div className="text-eyebrow">Queue requirements</div>
            <h2 className="mt-2 text-lg font-semibold text-bone">UACP evaluation and growth routing</h2>
            <div className="mt-2 text-xs leading-5 text-muted">
              These are the internal ranking queues that decide what the system should inspect, improve, or monetize next.
            </div>

            <div className="mt-4 space-y-4">
              <div className="rounded-lg border border-rule bg-ink-1/70 p-3">
                <div className="flex items-center justify-between gap-3">
                  <div className="font-semibold text-bone">Evaluation surgeon</div>
                  <span className="v-chip">{evaluationQueue.length}</span>
                </div>
                <div className="mt-2 text-xs leading-5 text-bone-2">
                  {evaluationSurgeonQ.data?.empty_reason ?? "Live evaluation queue returned from internal UACP."}
                </div>
                <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-muted">
                  {(evaluationSurgeonQ.data?.required_sources ?? []).map((source) => (
                    <span key={source} className="rounded border border-rule px-2 py-1">
                      {source}
                    </span>
                  ))}
                </div>
                <div className="mt-3 space-y-2">
                  {evaluationQueue.slice(0, 4).map((item, idx) => (
                    <div key={`evaluation-${idx}`} className="rounded border border-rule/80 bg-ink px-3 py-2">
                      <div className="text-sm font-medium text-bone">{labelUnknownItem(item)}</div>
                      <div className="mt-1 flex flex-wrap gap-2 text-[11px] text-muted">
                        {detailUnknownItem(item).map((detail) => (
                          <span key={detail}>{detail}</span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-lg border border-rule bg-ink-1/70 p-3">
                <div className="flex items-center justify-between gap-3">
                  <div className="font-semibold text-bone">Growth opportunities</div>
                  <span className="v-chip">{growthQueue.length}</span>
                </div>
                <div className="mt-2 text-xs leading-5 text-bone-2">
                  {growthOpportunitiesQ.data?.empty_reason ?? "Live marketplace and failed-route opportunity queue returned from internal UACP."}
                </div>
                <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-muted">
                  {(growthOpportunitiesQ.data?.required_sources ?? []).map((source) => (
                    <span key={source} className="rounded border border-rule px-2 py-1">
                      {source}
                    </span>
                  ))}
                </div>
                <div className="mt-3 space-y-2">
                  {growthQueue.slice(0, 4).map((item, idx) => (
                    <div key={`growth-${idx}`} className="rounded border border-rule/80 bg-ink px-3 py-2">
                      <div className="text-sm font-medium text-bone">{labelUnknownItem(item)}</div>
                      <div className="mt-1 flex flex-wrap gap-2 text-[11px] text-muted">
                        {detailUnknownItem(item).map((detail) => (
                          <span key={detail}>{detail}</span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>
      ) : null}
    </div>
  );
}
