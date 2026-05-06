import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  Crown,
  Lock,
  ShoppingCart,
  Tag,
  TrendingUp,
  UserPlus,
  Users,
} from "lucide-react";
import { api } from "@/lib/api";
import { fmtCents, fmtNumber, relativeTime } from "@/lib/cn";
import type { PlatformPulse, PlatformPulseActivity } from "@/types/api";

async function fetchPulse(): Promise<PlatformPulse> {
  const resp = await api.get<PlatformPulse>("/platform/pulse");
  return resp.data;
}

const TIER_ORDER = ["free", "starter", "pro", "sovereign", "elite", "enterprise"];
const TIER_COLORS: Record<string, string> = {
  free: "bg-rule-2",
  starter: "bg-electric/70",
  pro: "bg-brass/80",
  sovereign: "bg-moss/80",
  elite: "bg-amber/80",
  enterprise: "bg-crimson/70",
};

function PulseCard({
  label,
  value,
  delta,
  positive,
  icon: Icon,
}: {
  label: string;
  value: string;
  delta?: string;
  positive?: boolean;
  icon: React.ComponentType<{ className?: string }>;
}) {
  return (
    <div className="v-card p-4">
      <div className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.1em] text-muted">
        <Icon className="h-3 w-3" />
        {label}
      </div>
      <div className="mt-1.5 flex items-baseline justify-between">
        <div className="text-xl font-semibold text-bone">{value}</div>
        {delta && (
          <div
            className={
              "flex items-center gap-0.5 font-mono text-[10px] " +
              (positive ? "text-moss" : "text-crimson")
            }
          >
            {positive ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
            {delta}
          </div>
        )}
      </div>
    </div>
  );
}

function TierDistribution({ distribution }: { distribution: Record<string, number> }) {
  const total = Object.values(distribution).reduce((acc, n) => acc + (n || 0), 0);
  const tiers = TIER_ORDER.filter((tier) => (distribution[tier] ?? 0) > 0);
  const fallback = Object.keys(distribution).filter((tier) => !TIER_ORDER.includes(tier));
  const ordered = [...tiers, ...fallback];

  if (total === 0) {
    return (
      <div className="rounded-lg border border-rule bg-ink-2/40 p-4 font-mono text-[11px] text-muted">
        No subscriptions yet — register the first tenant to see the tier distribution.
      </div>
    );
  }

  return (
    <div>
      <div className="mb-2 flex h-2 overflow-hidden rounded-full bg-rule">
        {ordered.map((tier) => {
          const count = distribution[tier] ?? 0;
          const pct = total > 0 ? (count / total) * 100 : 0;
          return (
            <div
              key={tier}
              className={TIER_COLORS[tier] ?? "bg-rule-2"}
              style={{ width: `${pct}%` }}
              title={`${tier}: ${count} (${pct.toFixed(1)}%)`}
            />
          );
        })}
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 font-mono text-[11px] sm:grid-cols-3 md:grid-cols-5">
        {ordered.map((tier) => {
          const count = distribution[tier] ?? 0;
          const pct = total > 0 ? Math.round((count / total) * 100) : 0;
          return (
            <div key={tier} className="flex items-center gap-1.5">
              <span
                className={`h-2 w-2 shrink-0 rounded-sm ${TIER_COLORS[tier] ?? "bg-rule-2"}`}
              />
              <span className="text-bone-2 capitalize">{tier}</span>
              <span className="text-muted">{fmtNumber(count)}</span>
              <span className="text-muted-2">· {pct}%</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ActivityIcon({ kind }: { kind: PlatformPulseActivity["kind"] }) {
  const map: Record<PlatformPulseActivity["kind"], React.ComponentType<{ className?: string }>> = {
    listing_new: Tag,
    order_completed: ShoppingCart,
    upgrade: TrendingUp,
    user_registered: UserPlus,
    rate_limit_hit: AlertTriangle,
  };
  const Icon = map[kind] ?? Activity;
  return <Icon className="h-3.5 w-3.5 shrink-0 text-brass-2" />;
}

function ActivityRow({ event, isSuperuser }: { event: PlatformPulseActivity; isSuperuser: boolean }) {
  let label = "";
  let detail = "";
  switch (event.kind) {
    case "listing_new":
      label = `New listing: ${event.title ?? event.actor}`;
      detail = `Listed by @${event.actor}`;
      break;
    case "order_completed":
      label = `Order ${event.order_id ?? ""} completed`;
      detail = `Buyer: @${event.actor}`;
      if (isSuperuser && typeof event.amount_cents === "number") {
        detail += ` · ${fmtCents(event.amount_cents)}`;
      }
      break;
    case "upgrade":
      label = `@${event.actor} upgraded to ${event.to_plan ?? "paid"}`;
      detail = isSuperuser && typeof event.amount_cents === "number"
        ? `MRR +${fmtCents(event.amount_cents)} / ${event.billing_cycle ?? "month"}`
        : "Tier change";
      break;
    case "user_registered":
      label = `New user registered: @${event.actor}`;
      detail = `${event.tier ?? "free"} tier`;
      break;
    case "rate_limit_hit":
      label = `@${event.actor} triggered API rate limit`;
      detail = `${event.tier ?? "tier"} threshold`;
      break;
    default:
      label = String(event.kind);
      detail = `@${event.actor}`;
  }
  return (
    <li className="flex items-start gap-2 border-b border-rule/40 px-3 py-2 last:border-0">
      <span className="mt-0.5">
        <ActivityIcon kind={event.kind} />
      </span>
      <div className="flex-1">
        <div className="text-[12px] text-bone">{label}</div>
        <div className="font-mono text-[10px] text-muted">
          {relativeTime(event.ts)} · {detail}
        </div>
      </div>
    </li>
  );
}

export function PlatformPulseSection() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["platform-pulse"],
    queryFn: fetchPulse,
    refetchInterval: 60_000,
    retry: false,
  });

  if (isError) {
    // Soft-fail: don't break the Overview page if /platform/pulse 404s in a
    // partial deployment. Render nothing so the rest of the page is intact.
    return null;
  }

  return (
    <section className="space-y-4">
      <header className="flex items-end justify-between gap-4">
        <div>
          <div className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
            Platform · Marketplace pulse
          </div>
          <h2 className="mt-1 text-xl font-semibold tracking-tight">Live transparency</h2>
          <p className="mt-1 max-w-2xl text-sm text-bone-2">
            Public marketplace health — visible to vendors and tenants alike. Internal financials
            and security signals stay scoped to platform operators.
          </p>
        </div>
        <div className="hidden items-center gap-1 font-mono text-[10px] uppercase tracking-[0.1em] text-muted sm:flex">
          <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-moss" />
          live · refreshes every 60s
        </div>
      </header>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        <PulseCard
          label="Total users"
          value={data ? fmtNumber(data.users.total) : isLoading ? "…" : "—"}
          delta={data ? `${data.users.delta_pct_30d >= 0 ? "+" : ""}${data.users.delta_pct_30d}% (30d)` : undefined}
          positive={!!data && data.users.delta_pct_30d >= 0}
          icon={Users}
        />
        <PulseCard
          label="Active listings"
          value={data ? fmtNumber(data.active_listings.total) : isLoading ? "…" : "—"}
          delta={data ? `+${fmtNumber(data.active_listings.added_7d)} (7d)` : undefined}
          positive
          icon={Tag}
        />
        <PulseCard
          label="Tool installs"
          value={data ? fmtNumber(data.tool_installs.total) : isLoading ? "…" : "—"}
          delta={data ? `${fmtNumber(data.tool_installs.active_tools)} active tools` : undefined}
          positive
          icon={Activity}
        />
        <PulseCard
          label="Orders (30d)"
          value={data ? fmtNumber(data.orders_30d.count) : isLoading ? "…" : "—"}
          delta={data ? `${data.orders_30d.delta_pct_vs_prior >= 0 ? "+" : ""}${data.orders_30d.delta_pct_vs_prior}% vs prior` : undefined}
          positive={!!data && data.orders_30d.delta_pct_vs_prior >= 0}
          icon={ShoppingCart}
        />
        <PulseCard
          label="Paid tiers"
          value={data ? fmtNumber(data.paid_tier_users.total) : isLoading ? "…" : "—"}
          delta={data ? `+${fmtNumber(data.paid_tier_users.upgrades_30d)} upgrades` : undefined}
          positive
          icon={Crown}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="v-card p-5 lg:col-span-2">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <div className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
                Tier distribution
              </div>
              <h3 className="mt-1 text-sm font-semibold">Free · Starter · Pro · Sovereign · Enterprise</h3>
            </div>
          </div>
          {data ? (
            <TierDistribution distribution={data.tier_distribution} />
          ) : (
            <div className="h-12 animate-pulse rounded bg-rule/60" />
          )}
        </div>

        <div className="v-card p-0">
          <header className="flex items-center justify-between border-b border-rule px-4 py-2.5">
            <div className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
              Live activity
            </div>
            <span className="v-chip v-chip-ok">● live</span>
          </header>
          <ul className="max-h-72 overflow-y-auto">
            {(data?.activity ?? []).length === 0 && (
              <li className="px-3 py-6 text-center font-mono text-[11px] text-muted">
                {isLoading ? "Loading activity…" : "No recent platform activity."}
              </li>
            )}
            {(data?.activity ?? []).map((event, idx) => (
              <ActivityRow
                key={`${event.kind}-${event.ts}-${idx}`}
                event={event}
                isSuperuser={!!data?.is_superuser}
              />
            ))}
          </ul>
        </div>
      </div>

      {data?.is_superuser && data.superuser && (
        <div className="v-card border-brass/30 bg-brass/5 p-5">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <div className="flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-[0.12em] text-brass-2">
                <Lock className="h-3 w-3" />
                Owner-only · platform finance & risk
              </div>
              <h3 className="mt-1 text-sm font-semibold">Visible to platform superusers only</h3>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <PulseCard
              label="MRR"
              value={fmtCents(data.superuser.mrr_cents)}
              delta={`${data.superuser.mrr_delta_pct_vs_prior >= 0 ? "+" : ""}${data.superuser.mrr_delta_pct_vs_prior}% vs prior`}
              positive={data.superuser.mrr_delta_pct_vs_prior >= 0}
              icon={TrendingUp}
            />
            <PulseCard
              label="ARPU"
              value={fmtCents(data.superuser.arpu_cents)}
              icon={Users}
            />
            <PulseCard
              label="Churn 30d"
              value={`${data.superuser.churn_pct_30d}%`}
              delta={data.superuser.churn_pct_30d <= 5 ? "healthy" : "watch"}
              positive={data.superuser.churn_pct_30d <= 5}
              icon={ArrowDownRight}
            />
            <PulseCard
              label="Trial conversions 30d"
              value={fmtNumber(data.superuser.trial_conversions_30d)}
              icon={UserPlus}
            />
            <PulseCard
              label="Marketplace gross 30d"
              value={fmtCents(data.superuser.marketplace_gross_30d_cents)}
              icon={ShoppingCart}
            />
            <PulseCard
              label="Past-due subs"
              value={fmtNumber(data.superuser.past_due_subscriptions)}
              delta={data.superuser.past_due_subscriptions > 0 ? "revenue at risk" : "all current"}
              positive={data.superuser.past_due_subscriptions === 0}
              icon={AlertTriangle}
            />
            <PulseCard
              label="Open security threats"
              value={fmtNumber(data.superuser.open_security_threats)}
              delta={data.superuser.open_security_threats > 0 ? "review" : "clear"}
              positive={data.superuser.open_security_threats === 0}
              icon={AlertTriangle}
            />
          </div>
          <p className="mt-3 font-mono text-[10px] text-muted">
            Source: <span className="text-bone-2">GET /api/v1/platform/pulse</span> · superuser
            payload only emitted when caller carries <span className="text-bone-2">is_superuser</span>.
          </p>
        </div>
      )}
    </section>
  );
}
