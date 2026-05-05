import { useQuery } from "@tanstack/react-query";
import type { ComponentType, ReactNode } from "react";
import { Link } from "react-router-dom";
import {
  Activity,
  AlertCircle,
  ArrowRight,
  BadgeCheck,
  Boxes,
  CheckCircle2,
  CircleDollarSign,
  CircuitBoard,
  ClipboardCheck,
  Cpu,
  FileCheck2,
  Gauge,
  KeyRound,
  LockKeyhole,
  PackageCheck,
  PlugZap,
  RadioTower,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  TerminalSquare,
  Users,
  WalletCards,
  Workflow,
  XCircle,
} from "lucide-react";
import { api } from "@/lib/api";
import { cn, fmtCents, fmtNumber } from "@/lib/cn";

type CapabilityState = "active" | "needs_review" | "blocked" | "quiet";

interface SafeResult<T = unknown> {
  ok: boolean;
  data?: T;
  error?: string;
}

interface ControlSnapshot {
  overview: SafeResult<Record<string, unknown>>;
  analytics: SafeResult<Record<string, unknown>>;
  pipelines: SafeResult<{ items?: unknown[] }>;
  runs: SafeResult<{ items?: unknown[] }>;
  deployments: SafeResult<{ items?: unknown[]; total?: number }>;
  edgeCanary: SafeResult<Record<string, unknown>>;
  plugins: SafeResult<{ available_plugins?: Array<{ enabled?: boolean }> }>;
  lockerStatus: SafeResult<Record<string, unknown>>;
  lockerDashboard: SafeResult<Record<string, unknown>>;
  wallet: SafeResult<Record<string, unknown>>;
  usage: SafeResult<Record<string, unknown>>;
  members: SafeResult<{ items?: unknown[] }>;
  models: SafeResult<{ models?: unknown[] }>;
  keys: SafeResult<{ keys?: unknown[] }>;
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
  const [
    overview,
    analytics,
    pipelines,
    runs,
    deployments,
    edgeCanary,
    plugins,
    lockerStatus,
    lockerDashboard,
    wallet,
    usage,
    members,
    models,
    keys,
  ] = await Promise.all([
    safeGet<Record<string, unknown>>("/monitoring/overview"),
    safeGet<Record<string, unknown>>("/workspace/analytics/summary"),
    safeGet<{ items?: unknown[] }>("/pipelines", { limit: 50 }),
    safeGet<{ items?: unknown[] }>("/pipelines/runs/recent", { limit: 20 }),
    safeGet<{ items?: unknown[]; total?: number }>("/deployments"),
    safeGet<Record<string, unknown>>("/edge/canary/public"),
    safeGet<{ available_plugins?: Array<{ enabled?: boolean }> }>("/plugins"),
    safeGet<Record<string, unknown>>("/locker/monitoring/status"),
    safeGet<Record<string, unknown>>("/locker/security/dashboard"),
    safeGet<Record<string, unknown>>("/wallet/balance"),
    safeGet<Record<string, unknown>>("/wallet/stats/usage"),
    safeGet<{ items?: unknown[] }>("/workspace/members"),
    safeGet<{ models?: unknown[] }>("/workspace/models"),
    safeGet<{ keys?: unknown[] }>("/workspace/api-keys"),
  ]);

  return {
    overview,
    analytics,
    pipelines,
    runs,
    deployments,
    edgeCanary,
    plugins,
    lockerStatus,
    lockerDashboard,
    wallet,
    usage,
    members,
    models,
    keys,
  };
}

function countItems(result?: SafeResult<{ items?: unknown[]; total?: number }>): number {
  if (!result?.ok || !result.data) return 0;
  if (typeof result.data.total === "number") return result.data.total;
  return Array.isArray(result.data.items) ? result.data.items.length : 0;
}

function countArray<T>(result?: SafeResult<Record<string, T[]>>, key?: string): number {
  if (!result?.ok || !result.data || !key) return 0;
  const rows = result.data[key];
  return Array.isArray(rows) ? rows.length : 0;
}

function num(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function statusFrom(result: SafeResult | undefined, positive: boolean): CapabilityState {
  if (!result?.ok) return "needs_review";
  return positive ? "active" : "quiet";
}

export function ControlCenterPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["control-center"],
    queryFn: fetchControlSnapshot,
    refetchInterval: 20_000,
  });

  const pipelineCount = countItems(data?.pipelines);
  const recentRunCount = countItems(data?.runs);
  const pluginCount = data?.plugins.ok ? (data.plugins.data?.available_plugins?.length ?? 0) : 0;
  const enabledPluginCount = data?.plugins.ok
    ? (data.plugins.data?.available_plugins ?? []).filter((plugin) => plugin.enabled).length
    : 0;
  const modelCount = countArray(data?.models as SafeResult<Record<string, unknown[]>>, "models");
  const memberCount = countItems(data?.members);
  const apiKeyCount = countArray(data?.keys as SafeResult<Record<string, unknown[]>>, "keys");
  const walletBalance =
    num(data?.wallet.data?.balance_cents) ||
    num(data?.wallet.data?.available_balance_cents) ||
    num(data?.wallet.data?.reserve_balance_cents);
  const spendCents =
    num(data?.analytics.data?.total_cost_cents) ||
    num(data?.analytics.data?.spend_cents) ||
    num(data?.overview.data?.spend_today_cents);
  const edgeStatus = String(data?.edgeCanary.data?.status ?? (data?.edgeCanary.ok ? "available" : "needs review"));
  const securityOpen =
    num(data?.lockerDashboard.data?.open_alerts) ||
    num(data?.lockerDashboard.data?.open_threats) ||
    num(data?.lockerStatus.data?.open_alerts);

  const pillars: Pillar[] = [
    {
      title: "Runs",
      path: "/playground",
      icon: TerminalSquare,
      state: statusFrom(data?.runs, recentRunCount > 0),
      value: fmtNumber(recentRunCount),
      label: "recent governed executions",
      body: "Every run should resolve to route, model, policy, cost, and audit proof.",
      proof: ["route decision", "reserve impact", "audit hash"],
    },
    {
      title: "Pipelines",
      path: "/pipelines",
      icon: Workflow,
      state: statusFrom(data?.pipelines, pipelineCount > 0),
      value: fmtNumber(pipelineCount),
      label: "versioned workflows",
      body: "Build controlled workflows, execute them, inspect runs, and preserve versions.",
      proof: ["builder", "run history", "versions"],
    },
    {
      title: "Edge",
      path: "/monitoring",
      icon: RadioTower,
      state: data?.edgeCanary.ok ? "active" : "needs_review",
      value: edgeStatus,
      label: "SNMP / Modbus / webhook control",
      body: "Legacy infrastructure signals become governed decisions without replacing existing systems.",
      proof: ["SNMP proof", "protocol canary", "protected customer routes"],
    },
    {
      title: "Optimization",
      path: "/models",
      icon: Sparkles,
      state: statusFrom(data?.models, modelCount > 0),
      value: fmtNumber(modelCount),
      label: "models under policy",
      body: "Cost, quality, routing, and savings become operator-visible controls.",
      proof: ["cost prediction", "quality prediction", "routing selection"],
    },
    {
      title: "Compliance",
      path: "/compliance",
      icon: FileCheck2,
      state: data?.analytics.ok || data?.overview.ok ? "active" : "needs_review",
      value: "audit-ready",
      label: "evidence access by tier",
      body: "Audit can always be recorded; premium access controls who can view/export evidence.",
      proof: ["explainability", "PII events", "export packs"],
    },
    {
      title: "Security",
      path: "/monitoring",
      icon: ShieldCheck,
      state: data?.lockerStatus.ok || data?.lockerDashboard.ok ? (securityOpen > 0 ? "needs_review" : "active") : "needs_review",
      value: securityOpen > 0 ? fmtNumber(securityOpen) : "clear",
      label: securityOpen > 0 ? "open security items" : "Locker Sphere embedded",
      body: "Locker Sphere protects marketplace assets, workspace operations, and deployed controls.",
      proof: ["threats", "controls", "monitoring"],
    },
    {
      title: "Billing",
      path: "/billing",
      icon: WalletCards,
      state: data?.wallet.ok || data?.usage.ok ? "active" : "needs_review",
      value: walletBalance ? fmtCents(walletBalance) : spendCents ? fmtCents(spendCents) : "reserve",
      label: walletBalance ? "available balance" : "run usage control",
      body: "Commercial usage should be framed as governed runs, protocol reads, evidence, and reserve debits.",
      proof: ["reserve", "run usage", "allocation"],
    },
    {
      title: "Admin",
      path: "/team",
      icon: Users,
      state: data?.members.ok || data?.keys.ok ? "active" : "needs_review",
      value: `${fmtNumber(memberCount)} / ${fmtNumber(apiKeyCount)}`,
      label: "members / API keys",
      body: "Members, keys, models, deployments, and plugins belong in one operator lifecycle.",
      proof: ["members", "keys", "models"],
    },
  ];

  return (
    <div className="mx-auto w-full max-w-[1440px]">
      <header className="mb-5 flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-3xl">
          <div className="text-eyebrow">Control Center</div>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-bone md:text-4xl">
            One operating surface for every governed run.
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-muted">
            Veklom connects execution, edge protocols, security, compliance, billing, and extensions so operators can
            see what is running, what is protected, what costs money, and what needs action.
          </p>
        </div>
        <div className="frame min-w-[280px] p-4">
          <div className="flex items-center justify-between">
            <span className="text-eyebrow">Operating doctrine</span>
            <ShieldCheck className="h-4 w-4 text-moss" />
          </div>
          <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
            <ControlFact label="Audit posture" value="recorded" ok />
            <ControlFact label="Evidence access" value="tier gated" ok />
            <ControlFact label="Protocol access" value="protected" ok />
            <ControlFact label="Marketplace trust" value="verified guidance" ok />
          </div>
        </div>
      </header>

      {isError && (
        <div className="frame mb-4 flex items-start gap-3 border-crimson/40 bg-crimson/5 p-4 text-sm text-crimson">
          <AlertCircle className="mt-0.5 h-4 w-4" />
          <div>
            <div className="font-semibold">Control Center snapshot failed</div>
            <div className="mt-1 text-xs opacity-80">The page remains available; individual modules will show review states.</div>
          </div>
        </div>
      )}

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-12">
        <div className="xl:col-span-8">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {pillars.map((pillar) => (
              <PillarCard key={pillar.title} pillar={pillar} loading={isLoading} />
            ))}
          </div>
        </div>
        <div className="space-y-4 xl:col-span-4">
          <VerifiedPanel pluginCount={pluginCount} enabledPluginCount={enabledPluginCount} pluginsOk={Boolean(data?.plugins.ok)} />
          <OperatorPath />
          <AuditAccessPolicy />
        </div>
      </section>
    </div>
  );
}

interface Pillar {
  title: string;
  path: string;
  icon: ComponentType<{ className?: string }>;
  state: CapabilityState;
  value: string;
  label: string;
  body: string;
  proof: string[];
}

function PillarCard({ pillar, loading }: { pillar: Pillar; loading: boolean }) {
  const Icon = pillar.icon;
  return (
    <Link to={pillar.path} className="frame group block p-4 transition hover:border-brass/40 hover:bg-white/[0.025]">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-rule-2 bg-white/[0.025] text-brass-2">
            <Icon className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h2 className="truncate text-base font-semibold text-bone">{pillar.title}</h2>
              <StateChip state={pillar.state} />
            </div>
            <div className="mt-1 text-xs text-muted">{pillar.label}</div>
          </div>
        </div>
        <ArrowRight className="mt-1 h-4 w-4 text-muted transition group-hover:translate-x-0.5 group-hover:text-brass-2" />
      </div>

      <div className="mt-4 flex items-end justify-between gap-3">
        <div>
          <div className={cn("font-mono text-2xl font-semibold text-bone", loading && "animate-pulse text-muted")}>
            {loading ? "..." : pillar.value}
          </div>
          <p className="mt-2 text-sm leading-5 text-muted">{pillar.body}</p>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-1.5">
        {pillar.proof.map((item) => (
          <span key={item} className="v-chip text-[10px]">
            {item}
          </span>
        ))}
      </div>
    </Link>
  );
}

function StateChip({ state }: { state: CapabilityState }) {
  const config: Record<CapabilityState, { label: string; className: string; icon: ComponentType<{ className?: string }> }> = {
    active: { label: "active", className: "v-chip-ok", icon: CheckCircle2 },
    needs_review: { label: "review", className: "v-chip-warn", icon: AlertCircle },
    blocked: { label: "blocked", className: "v-chip-err", icon: XCircle },
    quiet: { label: "ready", className: "v-chip-brass", icon: Activity },
  };
  const item = config[state];
  const Icon = item.icon;
  return (
    <span className={cn("v-chip px-2 py-0.5 text-[9px]", item.className)}>
      <Icon className="h-3 w-3" />
      {item.label}
    </span>
  );
}

function VerifiedPanel({
  pluginCount,
  enabledPluginCount,
  pluginsOk,
}: {
  pluginCount: number;
  enabledPluginCount: number;
  pluginsOk: boolean;
}) {
  const checks = [
    { label: "Plugin docs", icon: ClipboardCheck, state: pluginsOk ? "active" : "needs_review" },
    { label: "Enable / disable", icon: PlugZap, state: pluginsOk ? "active" : "needs_review" },
    { label: "Validation advice", icon: BadgeCheck, state: "active" },
    { label: "Install flow", icon: PackageCheck, state: "needs_review" },
  ] as const;

  return (
    <section className="frame p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-eyebrow">Extension System</div>
          <h2 className="mt-1 text-lg font-semibold text-bone">Veklom Verified guidance</h2>
        </div>
        <Boxes className="h-5 w-5 text-brass-2" />
      </div>
      <p className="mt-3 text-sm leading-5 text-muted">
        This is not a legal certification. It is a machine-readable trust result showing whether an asset passed the
        Veklom checks needed for marketplace confidence.
      </p>
      <div className="mt-4 grid grid-cols-2 gap-2">
        <ControlFact label="Available" value={fmtNumber(pluginCount)} ok={pluginsOk} />
        <ControlFact label="Enabled" value={fmtNumber(enabledPluginCount)} ok={pluginsOk} />
      </div>
      <div className="mt-4 space-y-2">
        {checks.map((check) => {
          const Icon = check.icon;
          return (
            <div key={check.label} className="flex items-center justify-between rounded-lg border border-rule bg-white/[0.015] px-3 py-2">
              <span className="flex items-center gap-2 text-sm text-bone-2">
                <Icon className="h-4 w-4 text-brass-2" />
                {check.label}
              </span>
              <StateChip state={check.state} />
            </div>
          );
        })}
      </div>
      <Link to="/marketplace" className="v-btn-ghost mt-4 w-full">
        Open marketplace trust loop
        <ArrowRight className="h-4 w-4" />
      </Link>
    </section>
  );
}

function OperatorPath() {
  const steps = [
    { label: "Connect", detail: "API key, webhook, SNMP, Modbus", icon: KeyRound },
    { label: "Control", detail: "Policy, privacy, Locker Sphere", icon: LockKeyhole },
    { label: "Execute", detail: "Run, pipeline, model route", icon: CircuitBoard },
    { label: "Prove", detail: "Audit, evidence, cost trace", icon: FileCheck2 },
  ];
  return (
    <section className="frame p-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-eyebrow">First-week operator path</div>
          <h2 className="mt-1 text-lg font-semibold text-bone">Everything has a place</h2>
        </div>
        <Gauge className="h-5 w-5 text-moss" />
      </div>
      <div className="mt-4 space-y-3">
        {steps.map((step, index) => {
          const Icon = step.icon;
          return (
            <div key={step.label} className="flex gap-3">
              <div className="flex flex-col items-center">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-rule-2 bg-white/[0.02] text-bone">
                  <Icon className="h-4 w-4" />
                </div>
                {index < steps.length - 1 && <div className="h-5 w-px bg-rule" />}
              </div>
              <div className="pb-2">
                <div className="text-sm font-semibold text-bone">{step.label}</div>
                <div className="mt-0.5 text-xs text-muted">{step.detail}</div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function AuditAccessPolicy() {
  return (
    <section className="frame p-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-eyebrow">Premium audit control</div>
          <h2 className="mt-1 text-lg font-semibold text-bone">Record always, access by tier</h2>
        </div>
        <RotateCcw className="h-5 w-5 text-electric" />
      </div>
      <p className="mt-3 text-sm leading-5 text-muted">
        Veklom can keep the audit trail available for governance while making evidence exports, auditor bundles, and
        deep replay premium-gated features.
      </p>
      <div className="mt-4 grid grid-cols-1 gap-2">
        <AuditRow icon={Cpu} label="Run telemetry" value="captured" />
        <AuditRow icon={CircleDollarSign} label="Run usage" value="reserve-linked" />
        <AuditRow icon={ShieldCheck} label="Security events" value="Locker Sphere" />
      </div>
    </section>
  );
}

function AuditRow({ icon: Icon, label, value }: { icon: ComponentType<{ className?: string }>; label: string; value: string }) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-rule bg-white/[0.015] px-3 py-2">
      <span className="flex items-center gap-2 text-sm text-bone-2">
        <Icon className="h-4 w-4 text-electric" />
        {label}
      </span>
      <span className="font-mono text-[11px] uppercase tracking-[0.08em] text-muted">{value}</span>
    </div>
  );
}

function ControlFact({ label, value, ok }: { label: string; value: ReactNode; ok?: boolean }) {
  return (
    <div className="rounded-lg border border-rule bg-white/[0.015] px-3 py-2">
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted">{label}</span>
        {ok ? <CheckCircle2 className="h-3.5 w-3.5 text-moss" /> : <AlertCircle className="h-3.5 w-3.5 text-amber" />}
      </div>
      <div className="mt-1 truncate text-sm font-semibold text-bone">{value}</div>
    </div>
  );
}
