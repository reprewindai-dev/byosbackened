import { useEffect, useCallback } from "react";
import { FileText, Settings, Download } from "lucide-react";
import { api } from "@/lib/api";

const PLANS = [
  { name: "Community", price: "$0", period: "free", features: ["Local-first via Ollama", "1 deployment", "Basic governance"], current: false },
  { name: "Growth", price: "$299", period: "/mo", features: ["5 deployments", "Routing controls", "Audit retention 30 d"], current: false },
  { name: "Sovereign", price: "$799", period: "/mo", features: ["Unlimited deployments", "HIPAA / SOC 2 packs", "Audit retention 1 y"], current: true },
  { name: "Enterprise", price: "Custom", period: "private", features: ["SAML / SCIM / SSO", "Custom regions", "Procurement-ready"], current: false },
];

const CATEGORIES = [
  { label: "Inference", pct: 64, amount: "$11,820", color: "bg-amber" },
  { label: "Embeddings", pct: 13, amount: "$2,380", color: "bg-electric" },
  { label: "GPU burst", pct: 14, amount: "$2,640", color: "bg-violet-400" },
  { label: "Storage / logs", pct: 9, amount: "$1,636", color: "bg-cyan-400" },
];

const TEAMS = [
  { name: "Clinical AI", amount: "$8,120", color: "bg-amber" },
  { name: "Risk & Audit", amount: "$4,212", color: "bg-electric" },
  { name: "Customer Ops", amount: "$3,810", color: "bg-moss" },
  { name: "Internal R&D", amount: "$2,334", color: "bg-violet-400" },
];

const INVOICE_LINES = [
  { desc: "Sovereign tier · 1 seat × 12", amount: "$9,588.00" },
  { desc: "Seat overages × 4", amount: "$1,196.00" },
  { desc: "AI request overage · 18.4M", amount: "$3,212.00" },
  { desc: "GPU burst hours · 88h", amount: "$2,640.00" },
  { desc: "Managed deployment fees", amount: "$1,200.00" },
  { desc: "Log retention extension (12 mo)", amount: "$640.00" },
];

const CAPS = [
  { label: "Org daily cap", value: "$1,000 hard-stop" },
  { label: "Inference monthly cap", value: "$24,000 hard-stop" },
  { label: "AWS burst cap", value: "$3,000 alert" },
  { label: "Per-team cap · Clinical", value: "$10,000 alert" },
];

export function BillingPage() {
  const fetchData = useCallback(async () => {
    try { await api.get("/wallet/balance"); } catch { /* static */ }
  }, []);
  useEffect(() => { fetchData(); }, [fetchData]);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <p className="v-section-label">Billing</p>
          <h1 className="mt-1 text-2xl font-bold text-bone">Spend · usage · invoices</h1>
          <p className="mt-1 max-w-2xl text-sm text-muted">
            Real-time meters, hard-stop caps, customer portal, and per-team allocation. No surprise invoices.
          </p>
        </div>
        <div className="flex gap-2">
          <button className="flex items-center gap-1.5 rounded-md border border-rule px-3 py-1.5 text-xs text-muted hover:text-bone">
            <FileText className="h-3.5 w-3.5" /> Invoices
          </button>
          <button className="v-btn-primary text-xs"><Settings className="h-3.5 w-3.5" /> Manage plan</button>
        </div>
      </div>

      {/* Spend + Per-team */}
      <div className="grid gap-4 lg:grid-cols-5">
        <div className="v-card lg:col-span-3">
          <div className="flex items-center justify-between">
            <div>
              <p className="v-section-label">Spend · This Month</p>
              <p className="mt-0.5 text-lg font-bold text-bone">$18,476.00 of $24,000 cap</p>
            </div>
            <span className="rounded bg-moss/15 px-2 py-0.5 text-[9px] font-mono font-semibold text-moss">● ON-PACE</span>
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
              {["0h","1h","2h","3h","4h","5h","6h","7h","8h","9h","10h","11h","12h","13h","14h","15h","16h","17h","18h","20h","22h","23h"].map(h => <span key={h}>{h}</span>)}
            </div>
          </div>
          {/* Category breakdown */}
          <div className="mt-4 grid grid-cols-4 gap-3">
            {CATEGORIES.map(c => (
              <div key={c.label} className="rounded-md border border-rule/40 bg-ink-3/20 px-3 py-2.5">
                <div className="flex items-center justify-between text-[10px]">
                  <span className="text-muted">{c.label}</span>
                  <span className="font-mono text-muted">{c.pct}%</span>
                </div>
                <p className="mt-1 text-sm font-bold text-bone">{c.amount}</p>
                <div className="mt-1.5 h-1 w-full overflow-hidden rounded-full bg-ink-2">
                  <div className={`h-full rounded-full ${c.color}`} style={{ width: `${c.pct}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="v-card lg:col-span-2">
          <p className="v-section-label">Per-Team Allocation</p>
          <p className="mt-0.5 text-sm font-semibold text-bone">Tagged usage · cost center reports</p>
          <div className="mt-4 space-y-3">
            {TEAMS.map(t => (
              <div key={t.name} className="rounded-md border border-rule/40 bg-ink-3/20 px-4 py-2.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium text-bone">{t.name}</span>
                  <span className="font-mono text-bone">{t.amount}</span>
                </div>
                <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-ink-2">
                  <div className={`h-full rounded-full ${t.color}`} style={{ width: `${parseInt(t.amount.replace(/[$,]/g, "")) / 120}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Pricing tiers */}
      <div className="grid gap-4 md:grid-cols-4">
        {PLANS.map((plan) => (
          <div key={plan.name} className={`v-card relative ${plan.current ? "border-amber/30" : ""}`}>
            <div className="flex items-center justify-between">
              <p className="v-section-label">{plan.name}</p>
              {plan.current && <span className="rounded bg-moss/15 px-1.5 py-0.5 text-[8px] font-mono font-semibold text-moss">● CURRENT</span>}
            </div>
            <div className="mt-2">
              <span className="text-2xl font-bold text-bone">{plan.price}</span>
              <span className="ml-1 text-xs text-muted">{plan.period}</span>
            </div>
            <ul className="mt-4 space-y-1.5">
              {plan.features.map((f) => (
                <li key={f} className="flex items-center gap-2 text-xs text-muted">
                  <span className="h-1 w-1 rounded-full bg-amber" />
                  {f}
                </li>
              ))}
            </ul>
            <button className={`mt-4 w-full rounded py-2 text-xs font-semibold ${plan.current ? "bg-ink-3 text-bone border border-rule" : "bg-amber/15 border border-amber/30 text-amber hover:bg-amber/25"}`}>
              {plan.current ? "Manage" : "Upgrade"}
            </button>
          </div>
        ))}
      </div>

      {/* Invoice + Caps */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* Latest invoice */}
        <div className="v-card">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="v-section-label">Latest Invoice</p>
              <p className="mt-0.5 text-sm font-semibold text-bone">May 1, 2026 · acme-prod</p>
            </div>
            <button className="flex items-center gap-1 rounded border border-rule px-2.5 py-1 text-xs text-muted hover:text-bone">
              <Download className="h-3 w-3" /> PDF
            </button>
          </div>
          <div className="space-y-2">
            {INVOICE_LINES.map((line) => (
              <div key={line.desc} className="flex items-center justify-between border-b border-rule/20 pb-2 text-xs">
                <span className="text-muted">{line.desc}</span>
                <span className="font-mono text-bone">{line.amount}</span>
              </div>
            ))}
            <div className="flex items-center justify-between pt-1 text-xs">
              <span className="font-semibold text-bone">Total</span>
              <span className="font-mono font-bold text-bone">$18,476.00</span>
            </div>
          </div>
        </div>

        {/* Caps & Alerts */}
        <div className="v-card">
          <p className="v-section-label">Caps & Alerts</p>
          <p className="mt-0.5 text-sm font-semibold text-bone">Hard-stop · alert · forecast</p>
          <div className="mt-4 space-y-3">
            {CAPS.map((cap) => (
              <div key={cap.label} className="flex items-center justify-between border-b border-rule/20 pb-2 text-xs">
                <span className="text-muted">{cap.label}</span>
                <span className="font-mono text-bone">{cap.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
