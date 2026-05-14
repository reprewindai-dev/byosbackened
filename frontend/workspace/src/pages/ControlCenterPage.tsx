import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  Archive,
  BarChart3,
  Boxes,
  BrainCircuit,
  Building2,
  ClipboardCheck,
  CreditCard,
  FileCheck2,
  Flame,
  Gauge,
  GitBranch,
  Layers3,
  LockKeyhole,
  PlayCircle,
  Radar,
  Route,
  Search,
  ServerCog,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Users,
  Workflow,
} from "lucide-react";
import { api } from "@/lib/api";
import { cn, fmtNumber, relativeTime } from "@/lib/cn";

type CommandMetric = {
  metric: string;
  value: unknown;
  status: "wired" | "not_wired" | string;
  detail?: string;
  needs?: string;
};

type CommandSection = {
  title: string;
  metrics?: CommandMetric[];
  rows?: Record<string, unknown>[];
  steps?: Record<string, unknown>[];
};

type ModuleSection = CommandSection & {
  key: string;
  route: string;
};

type CommandCenterPayload = {
  generated_at: string;
  window_days: number;
  redaction: string;
  workspace_spine: {
    sovereign_mode: string;
    policy: string;
    badges: string[];
  };
  overview: CommandSection;
  live_tenants: CommandSection;
  usage: CommandSection;
  funnel: CommandSection;
  verticals: CommandSection;
  module_intelligence: ModuleSection[];
  heatmap: CommandSection;
  founder_tasks: CommandSection;
  system_health: CommandSection;
  audit: CommandSection;
};

const TABS = [
  "overview",
  "tenants",
  "usage",
  "funnel",
  "verticals",
  "modules",
  "heatmap",
  "tasks",
  "health",
  "audit",
] as const;

const MODULE_ORDER = [
  "playground",
  "gpc",
  "marketplace",
  "models",
  "pipelines",
  "deployments",
  "vault",
  "compliance",
  "monitoring",
  "billing",
  "team_access",
  "settings_integrations",
  "github",
  "risk_trust",
];

const MODULE_ICONS: Record<string, typeof Activity> = {
  overview: Gauge,
  playground: PlayCircle,
  gpc: BrainCircuit,
  marketplace: Boxes,
  models: Layers3,
  pipelines: Workflow,
  deployments: Route,
  vault: LockKeyhole,
  compliance: FileCheck2,
  monitoring: Activity,
  billing: CreditCard,
  team_access: Users,
  settings_integrations: SlidersHorizontal,
  github: GitBranch,
  risk_trust: ShieldCheck,
};

export function ControlCenterPage() {
  const [tab, setTab] = useState<(typeof TABS)[number]>("overview");
  const [filter, setFilter] = useState("");
  const commandQ = useQuery({
    queryKey: ["admin-command-center"],
    queryFn: async () => (await api.get<CommandCenterPayload>("/admin/command-center")).data,
    refetchInterval: 30_000,
  });
  const data = commandQ.data;
  const filteredModules = useMemo(() => {
    const modules = [...(data?.module_intelligence ?? [])].sort(
      (a, b) => MODULE_ORDER.indexOf(a.key) - MODULE_ORDER.indexOf(b.key),
    );
    if (!filter.trim()) return modules;
    const q = filter.toLowerCase();
    return modules.filter((section) => `${section.title} ${section.key}`.toLowerCase().includes(q));
  }, [data?.module_intelligence, filter]);

  return (
    <div>
      <header className="mb-6 flex flex-col justify-between gap-4 border-b border-rule pb-6 xl:flex-row xl:items-end">
        <div>
          <div className="text-eyebrow">Founder / Command Center</div>
          <h1 className="mt-2 text-2xl font-semibold tracking-[-0.035em] text-bone">Internal operating intelligence</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-bone-2">
            Superuser-only view of tenant activity, module usage, conversion signals, risk posture, and founder next actions.
            It mirrors the real Veklom workspace modules and redacts raw prompts/repo contents by default.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <StatusChip tone="ok">superuser only</StatusChip>
            <StatusChip tone="brass">MFA protected</StatusChip>
            <StatusChip tone="ok">{data?.workspace_spine.sovereign_mode ?? "ON-PREM"}</StatusChip>
            {(data?.workspace_spine.badges ?? ["Hetzner", "Fallback", "Tenant-scoped"]).map((badge) => (
              <StatusChip key={badge}>{badge}</StatusChip>
            ))}
          </div>
        </div>
        <div className="frame w-full p-4 xl:max-w-xl">
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="text-eyebrow">Locked tenant spine</div>
              <div className="mt-2 text-sm font-semibold text-bone">Overview Center / Playground / GPC</div>
              <div className="mt-1 text-xs leading-5 text-muted">
                {data?.workspace_spine.policy ??
                  "Hetzner-first policy evaluation. Approved fallback only when tenant rules allow it."}
              </div>
            </div>
            <ShieldCheck className="h-5 w-5 text-moss" />
          </div>
          <div className="mt-4 grid grid-cols-2 gap-2 text-xs text-muted">
            <Field label="generated" value={data?.generated_at ? relativeTime(data.generated_at) : commandQ.isLoading ? "loading" : "unavailable"} />
            <Field label="window" value={`${data?.window_days ?? 14}d`} />
            <Field label="access log" value="security_audit_logs" />
            <Field label="redaction" value="default on" />
          </div>
        </div>
      </header>

      {commandQ.isError && (
        <div className="frame mb-4 flex items-start gap-3 border-crimson/40 bg-crimson/5 p-4 text-sm text-crimson">
          <AlertTriangle className="mt-0.5 h-4 w-4" />
          <div>
            <div className="font-semibold">Command Center unavailable</div>
            <div className="text-crimson/80">Backend returned an error. Normal tenants remain outside this route.</div>
          </div>
        </div>
      )}

      <nav className="frame mb-4 flex flex-wrap gap-1 p-1">
        {TABS.map((item) => (
          <button
            key={item}
            type="button"
            onClick={() => setTab(item)}
            className={cn(
              "rounded-lg px-3 py-2 font-mono text-[11px] uppercase tracking-[0.12em] text-muted transition",
              tab === item ? "bg-brass/15 text-brass-2" : "hover:bg-white/[0.04] hover:text-bone",
            )}
          >
            {item.replace("_", " ")}
          </button>
        ))}
      </nav>

      {tab === "overview" && (
        <>
          <MetricGrid metrics={data?.overview.metrics} loading={commandQ.isLoading} />
          <div className="mt-4 grid grid-cols-12 gap-4">
            <section className="frame col-span-12 p-4 xl:col-span-7">
              <PanelTitle icon={Radar} title="Commercial heat" subtitle="Evaluation and buying-intent accounts" />
              <HeatRows rows={data?.heatmap.rows?.slice(0, 8)} />
            </section>
            <section className="frame col-span-12 p-4 xl:col-span-5">
              <PanelTitle icon={Sparkles} title="Founder tasks" subtitle="Generated from real usage signals" />
              <TaskRows rows={data?.founder_tasks.rows?.slice(0, 8)} />
            </section>
          </div>
        </>
      )}

      {tab === "tenants" && (
        <section className="frame overflow-hidden">
          <PanelTitle className="p-4" icon={Building2} title="Live Tenants" subtitle="Workspace activity from active sessions and telemetry" />
          <DataTable rows={data?.live_tenants.rows} columns={["workspace_name", "tenant", "industry", "current_page", "last_action", "plan", "github_connected", "mfa_status", "byos_private_runtime_status"]} />
        </section>
      )}

      {tab === "usage" && <SectionMetrics section={data?.usage} icon={BarChart3} />}
      {tab === "funnel" && <FunnelSection section={data?.funnel} />}
      {tab === "verticals" && (
        <section className="frame overflow-hidden">
          <PanelTitle className="p-4" icon={Boxes} title="Verticals" subtitle="Industry-specific Playground/GPC performance" />
          <DataTable rows={data?.verticals.rows} columns={["industry", "workspaces", "gpc_handoff_rate_pct", "average_session_duration_min", "conversion_rate_pct"]} />
        </section>
      )}
      {tab === "modules" && (
        <>
          <div className="frame mb-4 flex items-center gap-3 p-3">
            <Search className="h-4 w-4 text-muted" />
            <input
              value={filter}
              onChange={(event) => setFilter(event.target.value)}
              className="w-full bg-transparent text-sm text-bone outline-none placeholder:text-muted"
              placeholder="Filter module intelligence..."
            />
          </div>
          <div className="grid grid-cols-12 gap-4">
            {filteredModules.map((section) => (
              <ModuleCard key={section.key} section={section} />
            ))}
          </div>
        </>
      )}
      {tab === "heatmap" && (
        <section className="frame overflow-hidden">
          <PanelTitle className="p-4" icon={Flame} title="Customer Heat Map" subtitle="Cold, curious, active, evaluation-ready, commercially serious, at-risk" />
          <DataTable rows={data?.heatmap.rows} columns={["workspace_name", "tenant", "industry", "plan", "status", "score", "github_connected", "paid"]} />
        </section>
      )}
      {tab === "tasks" && (
        <section className="frame p-4">
          <PanelTitle icon={ClipboardCheck} title="Founder Tasks" subtitle="What to do next based on buying intent, gaps, and risk" />
          <TaskRows rows={data?.founder_tasks.rows} />
        </section>
      )}
      {tab === "health" && <SectionMetrics section={data?.system_health} icon={ServerCog} />}
      {tab === "audit" && (
        <section className="frame overflow-hidden">
          <PanelTitle className="p-4" icon={Archive} title="Audit Log" subtitle="Superuser actions, tenant admin actions, MFA/GitHub/billing/vault/evidence events" />
          <DataTable rows={data?.audit.rows} columns={["created_at", "workspace", "event_type", "event_category", "success", "user_id"]} />
        </section>
      )}
    </div>
  );
}

function MetricGrid({ metrics, loading }: { metrics?: CommandMetric[]; loading?: boolean }) {
  const rows = metrics ?? [];
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
      {(loading ? Array.from({ length: 10 }) : rows).map((metric, index) => (
        <div key={index} className="frame min-h-[112px] p-4">
          {loading ? (
            <div className="h-full animate-pulse rounded-lg bg-white/[0.03]" />
          ) : (
            <>
              <div className="flex items-center justify-between gap-2">
                <div className="text-eyebrow">{(metric as CommandMetric).metric}</div>
                <StatusChip tone={(metric as CommandMetric).status === "not_wired" ? "warn" : "ok"}>
                  {(metric as CommandMetric).status}
                </StatusChip>
              </div>
              <div className="mt-4 break-words font-mono text-2xl font-semibold text-bone">{formatValue((metric as CommandMetric).value)}</div>
              {((metric as CommandMetric).detail || (metric as CommandMetric).needs) && (
                <div className="mt-2 text-xs leading-5 text-muted">{(metric as CommandMetric).detail ?? (metric as CommandMetric).needs}</div>
              )}
            </>
          )}
        </div>
      ))}
    </div>
  );
}

function SectionMetrics({ section, icon: Icon }: { section?: CommandSection; icon: typeof Activity }) {
  return (
    <section>
      <PanelTitle className="mb-3" icon={Icon} title={section?.title ?? "Section"} subtitle="Backend-derived metrics only; missing signals are labeled not wired" />
      <MetricGrid metrics={section?.metrics} />
    </section>
  );
}

function ModuleCard({ section }: { section: ModuleSection }) {
  const Icon = MODULE_ICONS[section.key] ?? Activity;
  const notWired = (section.metrics ?? []).filter((metric) => metric.status === "not_wired").length;
  return (
    <section className="frame col-span-12 p-4 md:col-span-6 xl:col-span-4">
      <PanelTitle icon={Icon} title={section.title} subtitle={section.route} />
      <div className="mt-4 space-y-2">
        {(section.metrics ?? []).map((metric) => (
          <MetricLine key={metric.metric} metric={metric} />
        ))}
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <StatusChip tone={notWired ? "warn" : "ok"}>{notWired ? `${notWired} not wired` : "wired"}</StatusChip>
        <StatusChip>module mirrored</StatusChip>
      </div>
    </section>
  );
}

function FunnelSection({ section }: { section?: CommandSection }) {
  const steps = section?.steps ?? [];
  return (
    <section className="frame overflow-hidden">
      <PanelTitle className="p-4" icon={Route} title="Funnel" subtitle="visit -> signup -> Playground -> GPC -> deployment -> billing -> paid/reserve" />
      <div className="grid gap-px bg-rule md:grid-cols-2 xl:grid-cols-3">
        {steps.map((step, index) => (
          <div key={String(step.key ?? index)} className="bg-ink-2 p-4">
            <div className="text-eyebrow">{index + 1}. {String(step.label ?? step.key)}</div>
            <div className="mt-3 font-mono text-3xl font-semibold text-bone">{formatValue(step.value)}</div>
            <div className="mt-2 text-xs text-muted">
              {step.conversion_from_prior_pct == null ? "first step" : `${formatValue(step.conversion_from_prior_pct)}% from prior`}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function HeatRows({ rows }: { rows?: Record<string, unknown>[] }) {
  if (!rows?.length) return <EmptyState text="No workspace heat-map rows yet." />;
  return (
    <div className="mt-4 space-y-2">
      {rows.map((row) => (
        <div key={String(row.workspace_id)} className="rounded-lg border border-rule bg-ink-1/80 p-3">
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="font-semibold text-bone">{String(row.workspace_name)}</div>
              <div className="mt-1 text-xs text-muted">{String(row.industry)} / {String(row.tenant)}</div>
            </div>
            <StatusChip tone={heatTone(String(row.status))}>{String(row.status).replace("_", " ")}</StatusChip>
          </div>
          <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-white/[0.06]">
            <div className="h-full rounded-full bg-brass" style={{ width: `${Math.min(Number(row.score ?? 0), 100)}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}

function TaskRows({ rows }: { rows?: Record<string, unknown>[] }) {
  if (!rows?.length) return <EmptyState text="No founder tasks generated from current signals." />;
  return (
    <div className="mt-4 space-y-2">
      {rows.map((row, index) => (
        <div key={index} className="rounded-lg border border-rule bg-ink-1/80 p-3">
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="font-semibold text-bone">{String(row.action)}</div>
              <div className="mt-1 text-xs leading-5 text-muted">{String(row.reason)}</div>
            </div>
            <StatusChip tone={String(row.priority) === "high" ? "err" : "warn"}>{String(row.priority)}</StatusChip>
          </div>
          <div className="mt-2 font-mono text-[10px] uppercase tracking-[0.12em] text-muted">{String(row.workspace)}</div>
        </div>
      ))}
    </div>
  );
}

function DataTable({ rows, columns }: { rows?: Record<string, unknown>[]; columns: string[] }) {
  if (!rows?.length) return <EmptyState text="No backend rows returned for this section." />;
  return (
    <div className="overflow-auto">
      <table className="w-full min-w-[860px] text-left text-sm">
        <thead className="border-y border-rule bg-white/[0.02] text-eyebrow">
          <tr>{columns.map((column) => <th key={column} className="px-4 py-3">{column.replaceAll("_", " ")}</th>)}</tr>
        </thead>
        <tbody className="divide-y divide-rule">
          {rows.map((row, index) => (
            <tr key={index} className="hover:bg-white/[0.025]">
              {columns.map((column) => (
                <td key={column} className="max-w-[260px] truncate px-4 py-3 text-bone-2">
                  {column.endsWith("_at") && typeof row[column] === "string" ? relativeTime(String(row[column])) : formatValue(row[column])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PanelTitle({
  icon: Icon,
  title,
  subtitle,
  className,
}: {
  icon: typeof Activity;
  title: string;
  subtitle?: string;
  className?: string;
}) {
  return (
    <div className={cn("flex items-start justify-between gap-3", className)}>
      <div>
        <div className="flex items-center gap-2">
          <Icon className="h-4 w-4 text-brass" />
          <h2 className="text-lg font-semibold text-bone">{title}</h2>
        </div>
        {subtitle && <p className="mt-1 text-xs leading-5 text-muted">{subtitle}</p>}
      </div>
    </div>
  );
}

function MetricLine({ metric }: { metric: CommandMetric }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border border-rule bg-ink-1/70 px-3 py-2">
      <div>
        <div className="text-xs text-bone-2">{metric.metric}</div>
        {(metric.detail || metric.needs) && <div className="mt-0.5 text-[10px] text-muted">{metric.detail ?? metric.needs}</div>}
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <span className="font-mono text-sm text-bone">{formatValue(metric.value)}</span>
        <StatusChip tone={metric.status === "not_wired" ? "warn" : "ok"}>{metric.status}</StatusChip>
      </div>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-rule bg-ink-1 px-3 py-2">
      <div className="font-mono text-[9px] uppercase tracking-[0.12em] text-muted">{label}</div>
      <div className="mt-1 truncate text-xs text-bone">{value}</div>
    </div>
  );
}

function StatusChip({ children, tone = "neutral" }: { children: string | number; tone?: "ok" | "warn" | "err" | "brass" | "neutral" }) {
  return (
    <span
      className={cn(
        "v-chip whitespace-nowrap px-2 py-0.5 text-[9px]",
        tone === "ok" && "v-chip-ok",
        tone === "warn" && "v-chip-warn",
        tone === "err" && "v-chip-err",
        tone === "brass" && "v-chip-brass",
      )}
    >
      {children}
    </span>
  );
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="rounded-lg border border-dashed border-rule bg-white/[0.02] px-4 py-8 text-center text-sm text-muted">
      {text}
    </div>
  );
}

function heatTone(status: string): "ok" | "warn" | "err" | "brass" | "neutral" {
  if (status === "commercially_serious" || status === "evaluation_ready") return "ok";
  if (status === "active") return "brass";
  if (status === "at_risk") return "err";
  if (status === "curious") return "warn";
  return "neutral";
}

function formatValue(value: unknown): string {
  if (value == null) return "-";
  if (typeof value === "boolean") return value ? "yes" : "no";
  if (typeof value === "number") return Number.isInteger(value) ? fmtNumber(value) : value.toFixed(2);
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value.length ? value.map((item) => formatValue(item)).join(", ") : "-";
  if (typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>).slice(0, 3);
    return entries.map(([key, val]) => `${key}:${formatValue(val)}`).join(" / ");
  }
  return String(value);
}
