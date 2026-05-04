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

interface WalletBalance {
  workspace_id: string;
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
  credits: number;
  bonus_percent: number;
}

interface TopupOptions {
  options: TopupOption[];
}

async function fetchBalance() {
  return (await api.get<WalletBalance>("/wallet/balance")).data;
}
async function fetchTransactions() {
  return (await api.get<TxnList>("/wallet/transactions", { params: { limit: 25, offset: 0 } })).data;
}
async function fetchTopupOptions() {
  return (await api.get<TopupOptions>("/wallet/topup/options")).data;
}

async function createTopup(pack: string) {
  const origin = window.location.origin;
  const resp = await api.post<{ checkout_url: string; session_id: string }>("/wallet/topup/checkout", {
    pack_name: pack,
    success_url: `${origin}/workspace-app#/billing?topup=success`,
    cancel_url: `${origin}/workspace-app#/billing?topup=cancel`,
  });
  return resp.data;
}

export function BillingPage() {
  const balance = useQuery({ queryKey: ["wallet-balance"], queryFn: fetchBalance, refetchInterval: 30_000 });
  const txns = useQuery({ queryKey: ["wallet-txns"], queryFn: fetchTransactions });
  const packs = useQuery({ queryKey: ["wallet-topup-options"], queryFn: fetchTopupOptions });
  const [selectedPack, setSelectedPack] = useState<string | null>(null);

  const topup = useMutation({
    mutationFn: createTopup,
    onSuccess: (data) => {
      if (data.checkout_url) window.location.href = data.checkout_url;
    },
  });

  const monthlyPct = useMemo(() => {
    if (!balance.data || !balance.data.monthly_credits_included) return 0;
    return Math.min(
      100,
      Math.round((balance.data.monthly_credits_used / balance.data.monthly_credits_included) * 100),
    );
  }, [balance.data]);

  return (
    <div className="mx-auto w-full max-w-7xl space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="mb-1 font-mono text-[11px] uppercase tracking-[0.15em] text-muted">
            Workspace · Billing
          </div>
          <h1 className="text-3xl font-semibold tracking-tight">Operating reserve &amp; token wallet</h1>
          <p className="mt-2 max-w-2xl text-sm text-bone-2">
            Pay-as-you-go token credits. Every inference call debits in real time. Monthly allowance renews
            automatically; top up any time for bonus credits.
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
            <div className="font-semibold">Wallet unavailable</div>
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
              <div className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted">Token balance</div>
              <h3 className="mt-1 text-sm font-semibold">Current operating reserve</h3>
            </div>
            <Wallet className="h-5 w-5 text-brass-2" />
          </div>

          <div className="flex items-baseline gap-3">
            <div className="font-mono text-4xl font-semibold text-bone">
              {balance.isLoading ? (
                <span className="inline-block h-9 w-40 animate-pulse rounded bg-rule" />
              ) : balance.data ? (
                fmtNumber(balance.data.balance)
              ) : (
                "—"
              )}
            </div>
            <span className="font-mono text-[12px] uppercase tracking-widest text-muted">credits</span>
          </div>

          <div className="mt-5">
            <div className="mb-1 flex justify-between font-mono text-[11px] text-muted">
              <span>Monthly allowance used</span>
              <span className="text-bone">
                {balance.data
                  ? `${fmtNumber(balance.data.monthly_credits_used)} / ${fmtNumber(
                      balance.data.monthly_credits_included,
                    )}`
                  : "—"}
              </span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded bg-rule">
              <div
                className={cn(
                  "h-full rounded transition-all",
                  monthlyPct > 80 ? "bg-crimson" : monthlyPct > 60 ? "bg-brass" : "bg-moss",
                )}
                style={{ width: `${monthlyPct}%` }}
              />
            </div>
            {balance.data?.monthly_period_end && (
              <div className="mt-2 font-mono text-[10px] text-muted">
                resets {formatApiDate(balance.data.monthly_period_end)}
              </div>
            )}
          </div>

          <div className="mt-6 grid grid-cols-2 gap-3 font-mono text-[11px]">
            <Stat
              icon={<ArrowUpRight className="h-3 w-3 text-moss" />}
              label="Lifetime purchased"
              value={balance.data ? fmtNumber(balance.data.total_credits_purchased) : "—"}
            />
            <Stat
              icon={<TrendingUp className="h-3 w-3 text-electric" />}
              label="Lifetime used"
              value={balance.data ? fmtNumber(balance.data.total_credits_used) : "—"}
            />
          </div>
        </div>

        <div className="v-card p-5">
          <div className="mb-3 font-mono text-[11px] uppercase tracking-[0.12em] text-muted">Quick actions</div>
          <button
            className="v-btn-primary w-full"
            onClick={() => setSelectedPack(packs.data?.options[1]?.pack_name ?? "growth")}
            disabled={packs.isLoading}
          >
            <Sparkles className="h-4 w-4" /> Top up credits
          </button>
          <a href="#/settings" className="v-btn-ghost mt-2 w-full justify-center">
            <CreditCard className="h-4 w-4" /> Manage payment method
          </a>
          <div className="mt-4 rounded-lg border border-rule p-3 text-[11px] text-bone-2">
            <div className="mb-1 font-mono text-[10px] uppercase tracking-wider text-muted">Burn-rate guard</div>
            <div>Spend caps, alerts, and auto-throttle live in <a href="#/monitoring" className="text-brass-2 hover:underline">Monitoring</a>.</div>
          </div>
        </div>
      </section>

      <section>
        <header className="mb-3 flex items-end justify-between">
          <div>
            <div className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted">Token packs</div>
            <h2 className="mt-1 text-lg font-semibold">Top up with bonus credits</h2>
          </div>
          {packs.isLoading && (
            <span className="font-mono text-[11px] text-muted">loading…</span>
          )}
        </header>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
          {(packs.data?.options ?? []).map((p) => {
            const effectiveCredits = p.credits;
            const pricePerK = (p.price_cents / (effectiveCredits / 1000)).toFixed(3);
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
                      +{p.bonus_percent}% bonus
                    </span>
                  )}
                </div>
                <div>
                  <div className="font-mono text-[14px] font-semibold text-bone">
                    {fmtNumber(effectiveCredits)} credits
                  </div>
                  <div className="mt-0.5 font-mono text-[10px] text-muted">
                    ≈ ${pricePerK} / 1k credits
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
              Top-up packs unavailable — Stripe may not be configured.
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
              <h3 className="mt-0.5 text-sm font-semibold">Debit &amp; credit ledger</h3>
            </div>
          </div>
          <span className="v-chip font-mono">
            {txns.data ? `${txns.data.transactions.length} / ${txns.data.total}` : "—"}
          </span>
        </header>

        <table className="w-full text-[13px]">
          <thead>
            <tr className="border-b border-rule font-mono text-[10px] uppercase tracking-wider text-muted">
              <th className="px-5 py-2 text-left font-medium">When</th>
              <th className="px-5 py-2 text-left font-medium">Type</th>
              <th className="px-5 py-2 text-left font-medium">Description</th>
              <th className="px-5 py-2 text-right font-medium">Δ credits</th>
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
                    {t.description ?? t.endpoint_path ?? "—"}
                  </td>
                  <td
                    className={cn(
                      "px-5 py-2.5 text-right",
                      credit ? "text-moss" : "text-crimson",
                    )}
                  >
                    {credit ? "+" : ""}
                    {fmtNumber(t.amount)}
                  </td>
                  <td className="px-5 py-2.5 text-right text-bone">{fmtNumber(t.balance_after)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>
    </div>
  );
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
