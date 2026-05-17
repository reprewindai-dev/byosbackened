import { useEffect, useState, useCallback } from "react";
import { FileText, Settings, Download } from "lucide-react";
import { api } from "@/lib/api";

interface WalletBalance {
  balance_units?: number;
  balance_usd?: string;
}

interface Transaction {
  id: string;
  type?: string;
  amount_units?: number;
  amount_usd?: string;
  description?: string;
  created_at?: string;
}

interface TopupOption {
  id: string;
  label?: string;
  units?: number;
  price_usd?: string;
}

const PLANS = [
  { name: "Community", price: "$0", period: "free", features: ["Local-first via Ollama", "1 deployment", "Basic governance"], current: false },
  { name: "Growth", price: "$299", period: "/mo", features: ["5 deployments", "Routing controls", "Audit retention 30 d"], current: false },
  { name: "Sovereign", price: "$799", period: "/mo", features: ["Unlimited deployments", "HIPAA / SOC 2 packs", "Audit retention 1 y"], current: true },
  { name: "Enterprise", price: "Custom", period: "private", features: ["SAML / SCIM / SSO", "Custom regions", "Procurement-ready"], current: false },
];

export function BillingPage() {
  const [wallet, setWallet] = useState<WalletBalance | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [topupOptions, setTopupOptions] = useState<TopupOption[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    const results = await Promise.allSettled([
      api.get("/wallet/balance").then(r => r.data),
      api.get("/wallet/transactions").then(r => r.data),
      api.get("/wallet/topup/options").then(r => r.data),
    ]);
    if (results[0].status === "fulfilled") setWallet(results[0].value);
    if (results[1].status === "fulfilled") {
      const txs = Array.isArray(results[1].value) ? results[1].value : results[1].value?.items || [];
      setTransactions(txs);
    }
    if (results[2].status === "fulfilled") {
      const opts = Array.isArray(results[2].value) ? results[2].value : results[2].value?.options || [];
      setTopupOptions(opts);
    }
    setLoading(false);
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  async function handleTopup(optionId: string) {
    try {
      const { data } = await api.post("/wallet/topup/checkout", { option_id: optionId });
      if (data?.checkout_url) window.location.href = data.checkout_url;
    } catch { /* handled by interceptor */ }
  }

  const balanceUsd = wallet?.balance_usd || "0.00";
  const balanceUnits = wallet?.balance_units || 0;

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-start justify-between">
        <div>
          <p className="v-section-label">Billing</p>
          <h1 className="mt-1 text-2xl font-bold text-bone">Operating Reserve · Usage · Top-Up</h1>
          <p className="mt-1 text-sm text-muted">
            Real-time reserve balance, transaction history, and top-up options. No surprise invoices.
          </p>
        </div>
        <div className="flex gap-2">
          <button className="v-btn-ghost text-xs"><FileText className="h-3.5 w-3.5" /> Transactions</button>
          <button className="v-btn-ghost text-xs"><Settings className="h-3.5 w-3.5" /> Manage plan</button>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-5">
        <div className="v-card lg:col-span-3">
          <div className="flex items-center justify-between">
            <div>
              <p className="v-section-label">Operating Reserve</p>
              <p className="mt-0.5 text-lg font-bold text-bone">
                {loading ? "Loading..." : `$${balanceUsd}`}
                <span className="ml-2 text-xs font-normal text-muted">{balanceUnits.toLocaleString()} units</span>
              </p>
            </div>
            <span className="v-badge-amber">● Reserve</span>
          </div>
          <div className="v-progress mt-3">
            <div className="v-progress-fill bg-amber" style={{ width: "77%" }} />
          </div>
          <div className="mt-4 h-36 relative">
            <svg viewBox="0 0 460 130" className="w-full h-full" preserveAspectRatio="none">
              <defs>
                <linearGradient id="spend-grad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#f0b340" stopOpacity="0.35" />
                  <stop offset="100%" stopColor="#f0b340" stopOpacity="0" />
                </linearGradient>
              </defs>
              <line x1="0" y1="10" x2="460" y2="10" stroke="#ff4d6d" strokeWidth="0.5" strokeDasharray="4 3" opacity="0.5" />
              <path d="M0 120 C30 110, 60 95, 80 90 C100 85, 120 75, 150 70 C180 65, 200 55, 230 48 C260 42, 290 38, 320 32 C350 28, 380 25, 410 22 C430 20, 450 18, 460 16 L460 130 L0 130 Z" fill="url(#spend-grad)" />
              <path d="M0 120 C30 110, 60 95, 80 90 C100 85, 120 75, 150 70 C180 65, 200 55, 230 48 C260 42, 290 38, 320 32 C350 28, 380 25, 410 22 C430 20, 450 18, 460 16" fill="none" stroke="#f0b340" strokeWidth="2" />
            </svg>
            <div className="absolute bottom-0 left-0 right-0 flex justify-between text-[9px] font-mono text-muted px-1">
              <span>1h</span><span>3h</span><span>6h</span><span>9h</span><span>12h</span><span>15h</span><span>18h</span><span>20h</span><span>23h</span>
            </div>
          </div>
          <div className="mt-4 grid grid-cols-2 gap-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted">Balance (USD)</span>
              <span className="font-mono text-xs font-medium text-bone">${balanceUsd}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted">Balance (Units)</span>
              <span className="font-mono text-xs font-medium text-bone">{balanceUnits.toLocaleString()}</span>
            </div>
          </div>
        </div>

        <div className="v-card lg:col-span-2">
          <p className="v-section-label">Top-Up Options</p>
          <p className="mt-0.5 text-sm font-semibold text-bone">Fund your operating reserve</p>
          <div className="mt-4 space-y-3">
            {topupOptions.length > 0 ? topupOptions.map((opt) => (
              <div key={opt.id} className="flex items-center justify-between rounded-md border border-rule/50 bg-ink-3/30 px-3 py-2.5">
                <div>
                  <span className="text-xs text-bone">{opt.label || `${opt.units?.toLocaleString()} units`}</span>
                  <span className="ml-2 font-mono text-[10px] text-muted">${opt.price_usd}</span>
                </div>
                <button onClick={() => handleTopup(opt.id)} className="v-btn-primary px-3 py-1 text-[10px]">Top Up</button>
              </div>
            )) : (
              <p className="text-xs text-muted py-2">{loading ? "Loading options..." : "No top-up options available"}</p>
            )}
          </div>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        {PLANS.map((plan) => (
          <div key={plan.name} className={`v-card relative ${plan.current ? "border-brass/50 shadow-brass-glow" : ""}`}>
            {plan.current && <span className="v-badge-green absolute right-3 top-3">● Current</span>}
            <p className="v-section-label">{plan.name}</p>
            <div className="mt-2">
              <span className="text-2xl font-bold text-bone">{plan.price}</span>
              <span className="ml-1 text-xs text-muted">{plan.period}</span>
            </div>
            <ul className="mt-4 space-y-1.5">
              {plan.features.map((f) => (
                <li key={f} className="flex items-center gap-2 text-xs text-muted">
                  <span className="h-1 w-1 rounded-full bg-muted" />
                  {f}
                </li>
              ))}
            </ul>
            <button className={`mt-4 w-full ${plan.current ? "v-btn-ghost" : "v-btn-primary"} text-xs`}>
              {plan.current ? "Manage" : "Upgrade"}
            </button>
          </div>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="v-card">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <p className="v-section-label">Transaction History</p>
              <p className="mt-0.5 text-sm font-semibold text-bone">Recent wallet activity</p>
            </div>
            <button className="v-btn-ghost text-xs"><Download className="h-3 w-3" /> Export</button>
          </div>
          <div className="space-y-2">
            {transactions.length > 0 ? transactions.slice(0, 8).map((tx) => (
              <div key={tx.id} className="flex items-center justify-between text-xs">
                <div>
                  <span className="text-muted">{tx.description || tx.type || "Transaction"}</span>
                  {tx.created_at && <span className="ml-2 font-mono text-[9px] text-muted-2">{new Date(tx.created_at).toLocaleDateString()}</span>}
                </div>
                <span className={`font-mono ${(tx.amount_units || 0) >= 0 ? "text-moss" : "text-crimson"}`}>
                  {tx.amount_usd ? `$${tx.amount_usd}` : `${tx.amount_units?.toLocaleString()} units`}
                </span>
              </div>
            )) : (
              <p className="py-4 text-center text-xs text-muted">{loading ? "Loading..." : "No transactions yet"}</p>
            )}
          </div>
        </div>

        <div className="v-card">
          <div className="mb-3">
            <p className="v-section-label">Reserve Info</p>
            <p className="mt-0.5 text-sm font-semibold text-bone">Operating reserve details</p>
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between rounded-md border border-rule/50 bg-ink-3/30 px-3 py-2.5">
              <span className="text-xs text-bone">Current Balance</span>
              <span className="font-mono text-xs font-medium text-bone">${balanceUsd}</span>
            </div>
            <div className="flex items-center justify-between rounded-md border border-rule/50 bg-ink-3/30 px-3 py-2.5">
              <span className="text-xs text-bone">Unit Balance</span>
              <span className="font-mono text-xs font-medium text-bone">{balanceUnits.toLocaleString()} units</span>
            </div>
            <div className="flex items-center justify-between rounded-md border border-rule/50 bg-ink-3/30 px-3 py-2.5">
              <span className="text-xs text-bone">Exchange Rate</span>
              <span className="font-mono text-xs font-medium text-muted">1,000 units = $1.00</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
