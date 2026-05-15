import { useMemo, useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import {
  AlertCircle,
  ArrowUpRight,
  CreditCard,
  History,
  Loader2,
  Sparkles,
  TrendingUp,
  Wallet,
  Zap,
} from "lucide-react";
import { api } from "@/lib/api";
import { cn, fmtCents, fmtNumber, formatApiDate, relativeTime } from "@/lib/cn";
import { LiveErrorBox, ProofStrip } from "@/components/workspace/FlowPrimitives";

interface WalletBalance {
  workspace_id: string;
  reserve_balance_usd?: string;
  balance: number;
  monthly_credits_included: number;
  monthly_credits_used: number;
  monthly_period_start: string | null;
  monthly_period_end: string | null;
  total_credits_purchased: number;
  total_credits_used: number;
}

interface TxnRow {
  id: string;
  transaction_type: string;
  amount: number;
  balance_before: number;
  balance_after: number;
  endpoint_path: string | null;
  endpoint_method: string | null;
  request_id: string | null;
  description: string | null;
  metadata?: Record<string, unknown> | null;
  created_at: string;
}

interface TxnList {
  transactions: TxnRow[];
  total: number;
  limit: number;
  offset: number;
}

interface TopupOption {
  pack_name: string;
  price_cents: number;
  reserve_usd?: string;
  credits: number;
  bonus_percent: number;
}

interface TopupOptions {
  options: TopupOption[];
}

interface PlanDefinition {
  name: string;
  tier: string;
  activation_cents: number | null;
  minimum_reserve_cents: number | null;
  self_serve_checkout: boolean;
  free_evaluation_limits?: { governed_playground_runs?: number; compare_runs?: number; policy_tests?: number };
  features?: Record<string, unknown>;
  event_pricing?: Record<string, number | string | null>;
  pricing?: Record<string, number | string | null>;
}

interface PlansResponse {
  plans: PlanDefinition[];
}

interface CurrentSubscription {
  plan: string;
  status: string;
}

const FREE_EVALUATION_RUNS = 15;

const EVENT_PRICES = [
  ["UACP plan compile", "$1.50 Founding / $2.00 Standard"],
  ["UACP run execution", "$3 Founding / $4 Standard"],
  ["UACP artifact generation", "$5 Founding / $7 Standard / $10 Regulated"],
  ["Pipeline test", "$0.25 Founding / $0.40 Standard"],
  ["Endpoint/deployment verification", "$0.50 Founding / $0.80 Standard"],
  ["Compare run", "$0.75 Founding / $1.20 Standard"],
  ["BYOK governance calls", "$6 Founding / $8 Standard per 1K"],
  ["Managed governance calls", "$12 Founding / $16 Standard per 1K"],
  ["Auditor bundle", "$249 Founding / $349 Standard / $499 Regulated"],
];

async function fetchBalance() {
  return (await api.get<WalletBalance>("/wallet/balance")).data;
}
async function fetchTransactions() {
  return (await api.get<TxnList>("/wallet/transactions", { params: { limit: 25, offset: 0 } })).data;
}
async function fetchTopupOptions() {
  return (await api.get<TopupOptions>("/wallet/topup/options")).data;
}

async function fetchPlans() {
  return (await api.get<PlansResponse>("/subscriptions/plans")).data;
}

async function fetchCurrentSubscription() {
  return (await api.get<CurrentSubscription>("/subscriptions/current")).data;
}

async function createTopup(pack: string) {
  const origin = window.location.origin;
  const resp = await api.post<{ checkout_url: string; session_id: string }>("/wallet/topup/checkout", {
    pack_name: pack,
    success_url: `${origin}/login/#/billing?topup=success`,
    cancel_url: `${origin}/login/#/billing?topup=cancel`,
  });
  return resp.data;
}

function fmtReserveUsd(balance: WalletBalance): string {
  const amount = Number(balance.reserve_balance_usd ?? balance.balance / 1000);
  return `$${amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function fmtReserveUnitsAsUsd(units: number): string {
  const sign = units < 0 ? "-" : "";
  const amount = Math.abs(units) / 1000;
  return `${sign}$${amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function BillingPage() {
  const balance = useQuery({ queryKey: ["wallet-balance"], queryFn: fetchBalance, refetchInterval: 30_000 });
  const txns = useQuery({ queryKey: ["wallet-txns"], queryFn: fetchTransactions });
  const packs = useQuery({ queryKey: ["wallet-topup-options"], queryFn: fetchTopupOptions });
  const plans = useQuery({ queryKey: ["subscription-plans"], queryFn: fetchPlans, staleTime: 5 * 60_000 });
  const subscription = useQuery({ queryKey: ["subscription-current"], queryFn: fetchCurrentSubscription, staleTime: 60_000 });
  const [selectedPack, setSelectedPack] = useState<string | null>(null);

  const topup = useMutation({
    mutationFn: createTopup,
    onSuccess: (data) => {
      if (data.checkout_url) window.location.href = data.checkout_url;
    },
  });

  const evaluationRunsUsed = useMemo(() => {
    return (txns.data?.transactions ?? []).filter((txn) => {
      return (
        txn.transaction_type === "usage" &&
        txn.endpoint_path === "/api/v1/ai/complete" &&
        txn.metadata?.pricing_tier === "free_evaluation" &&
        txn.metadata?.billing_event_type === "governed_run"
      );
    }).length;
  }, [txns.data?.transactions]);
  const evaluationPct = Math.min(100, Math.round((evaluationRunsUsed / FREE_EVALUATION_RUNS) * 100));
  const evaluationLimitReached = !txns.isLoading && evaluationRunsUsed >= FREE_EVALUATION_RUNS;
  const pricingRows = useMemo(() => buildPricingRows(plans.data?.plans ?? []), [plans.data?.plans]);
  const firstReservePack = packs.data?.options[0]?.pack_name ?? null;
  const reserveTopupAllowed = subscription.data?.status === "active" && subscription.data?.plan !== "free";

  const startReserveCheckout = () => {
    if (!firstReservePack || !reserveTopupAllowed || topup.isPending) return;
    setSelectedPack(firstReservePack);
    topup.mutate(firstReservePack);
  };

  return (
    <div className="mx-auto w-full max-w-7xl space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="mb-1 font-mono text-[11px] uppercase tracking-[0.15em] text-muted">
            Workspace · Billing
          </div>
          <h1 className="text-3xl font-semibold tracking-tight">Operating reserve &amp; governed execution</h1>
          <p className="mt-2 max-w-2xl text-sm text-bone-2">
            Activate once, fund a reserve, and debit governed runs in real time. Stripe checkout funds the workspace
            reserve while the ledger records every debit and funding event.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <span className="v-chip v-chip-ok">
              <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-moss" />
              live · <span className="font-mono">/api/v1/wallet</span>
            </span>
            <span className="v-chip v-chip-brass">Stripe Checkout</span>
          </div>
        </div>
      </header>

      {balance.isError && (
        <div className="v-card flex items-start gap-3 border-crimson/40 bg-crimson/5 p-4 text-sm text-crimson">
          <AlertCircle className="mt-0.5 h-4 w-4" />
          <div className="flex-1">
            <div className="font-semibold">Reserve unavailable</div>
            <div className="mt-1 text-xs opacity-80">
              {(balance.error as Error)?.message ?? "Unknown error"} · log in or confirm workspace is provisioned.
            </div>
          </div>
          <button className="v-btn-ghost" onClick={() => balance.refetch()}>
            Retry
          </button>
        </div>
      )}

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="v-card p-5 lg:col-span-2">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <div className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted">Reserve balance</div>
              <h3 className="mt-1 text-sm font-semibold">Current operating reserve</h3>
            </div>
            <Wallet className="h-5 w-5 text-brass-2" />
          </div>

          <div className="flex items-baseline gap-3">
            <div className="font-mono text-4xl font-semibold text-bone">
              {balance.isLoading ? (
                <span className="inline-block h-9 w-40 animate-pulse rounded bg-rule" />
              ) : balance.data ? (
                fmtReserveUsd(balance.data)
              ) : (
                "-"
              )}
            </div>
            <span className="font-mono text-[12px] uppercase tracking-widest text-muted">available</span>
          </div>

          <div className="mt-5">
            <div className="mb-1 flex justify-between font-mono text-[11px] text-muted">
              <span>Free Evaluation governed runs</span>
              <span className="text-bone">
                {txns.isLoading ? "-" : `${Math.min(evaluationRunsUsed, FREE_EVALUATION_RUNS)} / ${FREE_EVALUATION_RUNS}`}
              </span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded bg-rule">
              <div
                className={cn(
                  "h-full rounded transition-all",
                  evaluationPct > 80 ? "bg-crimson" : evaluationPct > 60 ? "bg-brass" : "bg-moss",
                )}
                style={{ width: `${evaluationPct}%` }}
              />
            </div>
            {balance.data?.monthly_period_end && (
              <div className="mt-2 font-mono text-[10px] text-muted">
                resets {formatApiDate(balance.data.monthly_period_end)}
              </div>
            )}
            {evaluationLimitReached && (
              <div className="mt-4 rounded-xl border border-crimson/35 bg-crimson/10 p-4">
                <div className="flex items-start gap-3">
                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-crimson" />
                  <div className="min-w-0 flex-1">
                    <div className="font-semibold text-bone">Evaluation limit reached</div>
                    <p className="mt-1 text-sm leading-relaxed text-bone-2">
                      This workspace has used {FREE_EVALUATION_RUNS} / {FREE_EVALUATION_RUNS} governed evaluation runs.
                      Production routing and exportable evidence require activation before more governed buyer traffic runs.
                    </p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <button
                        className="v-btn-primary"
                        type="button"
                        onClick={startReserveCheckout}
                        disabled={!firstReservePack || !reserveTopupAllowed || topup.isPending}
                        title={reserveTopupAllowed ? "Add operating reserve" : "Activation is required before reserve can be funded"}
                      >
                        {topup.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Wallet className="h-4 w-4" />}
                        Add reserve
                      </button>
                      <a className="v-btn-ghost" href="https://veklom.com/pricing/">
                        Start activation
                      </a>
                      <a className="v-btn-ghost" href="https://veklom.com/#contact">
                        Request regulated access
                      </a>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="mt-6 grid grid-cols-2 gap-3 font-mono text-[11px]">
            <Stat
              icon={<ArrowUpRight className="h-3 w-3 text-moss" />}
              label="Reserve funded"
              value={balance.data ? fmtReserveUnitsAsUsd(balance.data.total_credits_purchased) : "-"}
            />
            <Stat
              icon={<TrendingUp className="h-3 w-3 text-electric" />}
              label="Reserve consumed"
              value={balance.data ? fmtReserveUnitsAsUsd(balance.data.total_credits_used) : "-"}
            />
          </div>
        </div>

        <div className="v-card p-5">
          <div className="mb-3 font-mono text-[11px] uppercase tracking-[0.12em] text-muted">Quick actions</div>
          <button
            className="v-btn-primary w-full"
            onClick={startReserveCheckout}
            disabled={packs.isLoading || !reserveTopupAllowed || topup.isPending}
            title={reserveTopupAllowed ? "Add operating reserve" : "Activation is required before reserve can be funded"}
          >
            {topup.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />} Add reserve
          </button>
          <button
            className="v-btn-ghost mt-2 w-full cursor-not-allowed justify-center opacity-70"
            disabled
            title="Stripe customer portal requires a completed billing account. Reserve checkout is live; portal access appears after account provisioning."
          >
            <CreditCard className="h-4 w-4" /> Customer portal locked
          </button>
          <div className="mt-4 rounded-lg border border-rule p-3 text-[11px] text-bone-2">
            <div className="mb-1 font-mono text-[10px] uppercase tracking-wider text-muted">Burn-rate guard</div>
            <div>Spend caps, alerts, and auto-throttle live in <a href="#/monitoring" className="text-brass-2 hover:underline">Monitoring</a>.</div>
          </div>
        </div>
      </section>

      <ProofStrip
        items={[
          { label: "pricing source", value: plans.data ? "/api/v1/subscriptions/plans" : plans.isError ? "unavailable" : "loading" },
          { label: "activation source", value: subscription.data ? "/api/v1/subscriptions/current" : subscription.isError ? "unavailable" : "loading" },
          { label: "reserve source", value: balance.data ? "/api/v1/wallet/balance" : balance.isError ? "unavailable" : "loading" },
          { label: "ledger source", value: txns.data ? "/api/v1/wallet/transactions" : txns.isError ? "unavailable" : "loading" },
          { label: "checkout source", value: packs.data ? "/api/v1/wallet/topup/options" : packs.isError ? "unavailable" : "loading" },
        ]}
      />

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-[1.5fr_1fr]">
        <div className="v-card p-0">
          <header className="border-b border-rule px-5 py-3">
            <div className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted">Access model</div>
            <h2 className="mt-1 text-lg font-semibold">Free lets you see governed AI. Paid lets you prove it.</h2>
          </header>
          {plans.isError && (
            <div className="p-4">
              <LiveErrorBox title="Pricing plans unavailable" error={plans.error} />
            </div>
          )}
          <div className="overflow-x-auto">
            <table className="w-full text-[12px]">
              <thead className="border-b border-rule font-mono text-[10px] uppercase tracking-wider text-muted">
                <tr>
                  <th className="px-5 py-2 text-left font-medium">Tier</th>
                  <th className="px-5 py-2 text-left font-medium">Activation</th>
                  <th className="px-5 py-2 text-left font-medium">Reserve</th>
                  <th className="px-5 py-2 text-left font-medium">Governed run</th>
                  <th className="px-5 py-2 text-left font-medium">Evidence package</th>
                </tr>
              </thead>
              <tbody>
                {plans.isLoading && (
                  <tr>
                    <td colSpan={5} className="px-5 py-6 text-center font-mono text-muted">
                      loading pricing from /api/v1/subscriptions/plans...
                    </td>
                  </tr>
                )}
                {!plans.isLoading && !plans.isError && pricingRows.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-5 py-6 text-center font-mono text-muted">
                      No plans returned by the billing API.
                    </td>
                  </tr>
                )}
                {pricingRows.map((row) => (
                  <tr key={row.tier} className="border-b border-rule/60 last:border-0">
                    <td className="px-5 py-2.5 font-semibold text-bone">{row.tier}</td>
                    <td className="px-5 py-2.5 font-mono text-bone-2">{row.activation}</td>
                    <td className="px-5 py-2.5 font-mono text-bone-2">{row.reserve}</td>
                    <td className="px-5 py-2.5 font-mono text-bone-2">{row.runs}</td>
                    <td className="px-5 py-2.5 font-mono text-bone-2">{row.evidence}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="v-card p-5">
          <div className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted">Paid-only evidence</div>
          <h2 className="mt-1 text-lg font-semibold">Compliance exports stay locked until activation</h2>
          <p className="mt-2 text-sm text-bone-2">
            The free playground is for evaluation only. Signed artifacts, retention controls, evidence packs, and auditor
            bundles require an activated workspace.
          </p>
          <div className="mt-4 space-y-2">
            {EVENT_PRICES.map(([label, value]) => (
              <div key={label} className="flex items-start justify-between gap-4 rounded-lg border border-rule bg-ink/35 px-3 py-2 text-[12px]">
                <span className="text-muted">{label}</span>
                <span className="text-right font-mono text-bone">{value}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section>
        <header className="mb-3 flex items-end justify-between">
          <div>
            <div className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted">Reserve packs</div>
            <h2 className="mt-1 text-lg font-semibold">Fund operating reserve</h2>
          </div>
          {packs.isLoading && (
            <span className="font-mono text-[11px] text-muted">loading…</span>
          )}
        </header>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
          {(packs.data?.options ?? []).map((p) => {
            const reserveUsd = Number(p.reserve_usd ?? p.credits / 1000);
            const runCount = Math.floor(reserveUsd / 0.25);
            const active = selectedPack === p.pack_name;
            return (
              <div
                key={p.pack_name}
                className={cn(
                  "v-card flex flex-col gap-3 p-4 transition",
                  active && "border-brass/60 ring-1 ring-brass/40",
                  p.bonus_percent >= 50 && "border-brass/30",
                )}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <div className="font-mono text-[10px] uppercase tracking-wider text-muted">
                      {p.pack_name}
                    </div>
                    <div className="mt-1 font-mono text-2xl font-semibold text-bone">
                      {fmtCents(p.price_cents)}
                    </div>
                  </div>
                  {p.bonus_percent > 0 && (
                    <span className="v-chip v-chip-brass font-mono text-[10px]">
                      +{p.bonus_percent}% reserve bonus
                    </span>
                  )}
                </div>
                <div>
                  <div className="font-mono text-[14px] font-semibold text-bone">
                    ${reserveUsd.toLocaleString(undefined, { maximumFractionDigits: 0 })} operating reserve
                  </div>
                  <div className="mt-0.5 font-mono text-[10px] text-muted">
                    up to {fmtNumber(runCount)} Founding governed runs
                  </div>
                </div>
                <button
                  className={cn("mt-auto w-full", active ? "v-btn-primary" : "v-btn-ghost")}
                  onClick={() => {
                    setSelectedPack(p.pack_name);
                    topup.mutate(p.pack_name);
                  }}
                  disabled={topup.isPending}
                >
                  {topup.isPending && active ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Zap className="h-4 w-4" />
                  )}
                  {topup.isPending && active ? "Opening Stripe…" : "Purchase"}
                </button>
              </div>
            );
          })}
          {!packs.isLoading && !packs.data?.options?.length && (
            <div className="v-card col-span-full p-5 text-center text-muted">
              Reserve packs unavailable - Stripe may not be configured.
            </div>
          )}
        </div>
      </section>

      <section className="v-card p-0">
        <header className="flex items-center justify-between border-b border-rule px-5 py-3">
          <div className="flex items-center gap-2">
            <History className="h-4 w-4 text-muted" />
            <div>
              <div className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
                Recent transactions
              </div>
              <h3 className="mt-0.5 text-sm font-semibold">Debit &amp; funding ledger</h3>
            </div>
          </div>
          <span className="v-chip font-mono">
            {txns.data ? `${txns.data.transactions.length} / ${txns.data.total}` : "-"}
          </span>
        </header>

        <table className="w-full text-[13px]">
          <thead>
            <tr className="border-b border-rule font-mono text-[10px] uppercase tracking-wider text-muted">
              <th className="px-5 py-2 text-left font-medium">When</th>
              <th className="px-5 py-2 text-left font-medium">Type</th>
              <th className="px-5 py-2 text-left font-medium">Description</th>
              <th className="px-5 py-2 text-right font-medium">Delta reserve</th>
              <th className="px-5 py-2 text-right font-medium">Balance after</th>
            </tr>
          </thead>
          <tbody className="font-mono">
            {txns.isLoading && (
              <tr>
                <td colSpan={5} className="px-5 py-6 text-center text-muted">
                  loading…
                </td>
              </tr>
            )}
            {!txns.isLoading && (!txns.data || txns.data.transactions.length === 0) && (
              <tr>
                <td colSpan={5} className="px-5 py-6 text-center text-muted">
                  No transactions yet. Top up or start using the Playground to generate ledger entries.
                </td>
              </tr>
            )}
            {txns.data?.transactions.map((t) => {
              const credit = t.amount > 0;
              return (
                <tr key={t.id} className="border-b border-rule/60 last:border-0">
                  <td className="px-5 py-2.5 text-muted">{relativeTime(t.created_at)}</td>
                  <td className="px-5 py-2.5">
                    <span
                      className={cn(
                        "v-chip font-mono",
                        credit ? "v-chip-ok" : "v-chip-warn",
                      )}
                    >
                      {t.transaction_type}
                    </span>
                  </td>
                  <td className="max-w-[280px] truncate px-5 py-2.5 text-bone-2">
                    {t.description ?? t.endpoint_path ?? "-"}
                  </td>
                  <td
                    className={cn(
                      "px-5 py-2.5 text-right",
                      credit ? "text-moss" : "text-crimson",
                    )}
                  >
                    {credit ? "+" : ""}
                    {fmtReserveUnitsAsUsd(t.amount)}
                  </td>
                  <td className="px-5 py-2.5 text-right text-bone">{fmtReserveUnitsAsUsd(t.balance_after)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>
    </div>
  );
}

function buildPricingRows(plans: PlanDefinition[]) {
  const order = ["free", "starter", "pro", "sovereign", "enterprise"];
  return [...plans].sort((a, b) => order.indexOf(a.tier) - order.indexOf(b.tier)).map((plan) => {
    const limits = plan.free_evaluation_limits ?? {};
    return {
      tier: planLabel(plan),
      activation: plan.activation_cents == null ? "Contact" : plan.activation_cents === 0 ? "$0" : `${fmtCents(plan.activation_cents)} one-time`,
      reserve: plan.minimum_reserve_cents == null ? "Private" : plan.minimum_reserve_cents === 0 ? "$0" : `${fmtCents(plan.minimum_reserve_cents)} min`,
      runs:
        plan.tier === "free"
          ? `${limits.governed_playground_runs ?? FREE_EVALUATION_RUNS} governed runs`
          : fmtEventCents(plan, "playground_run_cents", "/ run"),
      evidence: plan.features?.compliance_reports || plan.features?.audit_exports ? "available" : "activation required",
    };
  });
}

function fmtEventCents(plan: PlanDefinition, key: string, suffix = ""): string {
  const pricing = plan.event_pricing ?? plan.pricing ?? {};
  const cents = pricing[key];
  if (typeof cents !== "number") return "Private terms";
  return `${fmtCents(cents)}${suffix}`;
}

function planLabel(plan: PlanDefinition): string {
  if (plan.tier === "free") return "Free Evaluation";
  if (plan.tier === "starter") return "Founding";
  if (plan.tier === "pro") return "Standard";
  if (plan.tier === "sovereign") return "Regulated";
  return plan.name || plan.tier;
}

function Stat({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-lg border border-rule px-3 py-2">
      <div className="mb-0.5 flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-muted">
        {icon}
        {label}
      </div>
      <div className="text-bone">{value}</div>
    </div>
  );
}
