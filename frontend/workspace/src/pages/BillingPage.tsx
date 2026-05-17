import { FileText, Settings, Download } from "lucide-react";

const ALLOCATION = [
  { team: "Clinical AI", spend: "$8,120", color: "bg-brass-2" },
  { team: "Risk & Audit", spend: "$4,212", color: "bg-electric" },
  { team: "Customer Ops", spend: "$3,810", color: "bg-moss" },
  { team: "Internal R&D", spend: "$2,334", color: "bg-violet" },
];

const BREAKDOWN = [
  { label: "Inference", pct: 64, value: "$11,820", color: "bg-brass-2" },
  { label: "Embeddings", pct: 13, value: "$2,380", color: "bg-electric" },
  { label: "GPU burst", pct: 14, value: "$2,640", color: "bg-violet" },
  { label: "Storage / logs", pct: 9, value: "$1,636", color: "bg-moss" },
];

const PLANS = [
  { name: "Community", price: "$0", period: "free", features: ["Local-first via Ollama", "1 deployment", "Basic governance"], current: false },
  { name: "Growth", price: "$299", period: "/mo", features: ["5 deployments", "Routing controls", "Audit retention 30 d"], current: false },
  { name: "Sovereign", price: "$799", period: "/mo", features: ["Unlimited deployments", "HIPAA / SOC 2 packs", "Audit retention 1 y"], current: true },
  { name: "Enterprise", price: "Custom", period: "private", features: ["SAML / SCIM / SSO", "Custom regions", "Procurement-ready"], current: false },
];

const INVOICE_LINES = [
  { desc: "Sovereign tier · 1 seat × 12", amount: "$9,588.00" },
  { desc: "Seat overages × 4", amount: "$1,196.00" },
  { desc: "AI request overage · 18.4M", amount: "$3,212.00" },
  { desc: "GPU burst hours · 88h", amount: "$2,640.00" },
  { desc: "Managed deployment hours", amount: "$1,200.00" },
  { desc: "Log retention extension (12 mo)", amount: "$640.00" },
];

const CAPS = [
  { label: "Org daily cap", value: "$1,900", type: "hard-stop" },
  { label: "Inference monthly cap", value: "$24,000", type: "hard-stop" },
  { label: "AWS burst cap", value: "$3,000", type: "alert" },
  { label: "Per-team cap · Clinical", value: "$10,000", type: "alert" },
];

export function BillingPage() {
  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-start justify-between">
        <div>
          <p className="v-section-label">Billing</p>
          <h1 className="mt-1 text-2xl font-bold text-bone">Spend · usage · invoices</h1>
          <p className="mt-1 text-sm text-muted">
            Real-time meters, hard-stop caps, customer portal, and per-team allocation. No surprise invoices.
          </p>
        </div>
        <div className="flex gap-2">
          <button className="v-btn-ghost text-xs"><FileText className="h-3.5 w-3.5" /> Invoices</button>
          <button className="v-btn-ghost text-xs"><Settings className="h-3.5 w-3.5" /> Manage plan</button>
        </div>
      </div>

      {/* Main grid */}
      <div className="grid gap-4 lg:grid-cols-5">
        {/* Spend chart */}
        <div className="v-card lg:col-span-3">
          <div className="flex items-center justify-between">
            <div>
              <p className="v-section-label">Spend · This Month</p>
              <p className="mt-0.5 text-lg font-bold text-bone">$18,476.00 of $24,000 cap</p>
            </div>
            <span className="v-badge-amber">● On-Pace</span>
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
              {/* Cap line */}
              <line x1="0" y1="10" x2="460" y2="10" stroke="#ff4d6d" strokeWidth="0.5" strokeDasharray="4 3" opacity="0.5" />
              {/* Spend area */}
              <path d="M0 120 C30 110, 60 95, 80 90 C100 85, 120 75, 150 70 C180 65, 200 55, 230 48 C260 42, 290 38, 320 32 C350 28, 380 25, 410 22 C430 20, 450 18, 460 16 L460 130 L0 130 Z" fill="url(#spend-grad)" />
              <path d="M0 120 C30 110, 60 95, 80 90 C100 85, 120 75, 150 70 C180 65, 200 55, 230 48 C260 42, 290 38, 320 32 C350 28, 380 25, 410 22 C430 20, 450 18, 460 16" fill="none" stroke="#f0b340" strokeWidth="2" />
            </svg>
            <div className="absolute bottom-0 left-0 right-0 flex justify-between text-[9px] font-mono text-muted px-1">
              <span>1h</span><span>3h</span><span>6h</span><span>9h</span><span>12h</span><span>15h</span><span>18h</span><span>20h</span><span>23h</span>
            </div>
          </div>
          <div className="mt-4 grid grid-cols-4 gap-3">
            {BREAKDOWN.map((b) => (
              <div key={b.label}>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-muted">{b.label}</span>
                  <span className="font-mono text-[10px] text-muted-2">{b.pct}%</span>
                </div>
                <p className="mt-0.5 text-sm font-bold text-bone">{b.value}</p>
                <div className="v-progress mt-1">
                  <div className={`v-progress-fill ${b.color}`} style={{ width: `${b.pct}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Per-team */}
        <div className="v-card lg:col-span-2">
          <p className="v-section-label">Per-Team Allocation</p>
          <p className="mt-0.5 text-sm font-semibold text-bone">Tagged usage · cost center reports</p>
          <div className="mt-4 space-y-3">
            {ALLOCATION.map((a) => (
              <div key={a.team}>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-bone">{a.team}</span>
                  <span className="font-mono text-xs font-medium text-bone">{a.spend}</span>
                </div>
                <div className="v-progress mt-1">
                  <div className={`v-progress-fill ${a.color}`} style={{ width: `${parseInt(a.spend.replace(/[$,]/g, "")) / 100}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Plans */}
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

      {/* Bottom grid */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* Invoice */}
        <div className="v-card">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <p className="v-section-label">Latest Invoice</p>
              <p className="mt-0.5 text-sm font-semibold text-bone">May 1, 2026 · acme-prod</p>
            </div>
            <button className="v-btn-ghost text-xs"><Download className="h-3 w-3" /> PDF</button>
          </div>
          <div className="space-y-2">
            {INVOICE_LINES.map((line) => (
              <div key={line.desc} className="flex items-center justify-between text-xs">
                <span className="text-muted">{line.desc}</span>
                <span className="font-mono text-bone">{line.amount}</span>
              </div>
            ))}
            <div className="flex items-center justify-between border-t border-rule pt-2 text-sm font-bold">
              <span className="text-bone">Total</span>
              <span className="font-mono text-bone">$18,476.00</span>
            </div>
          </div>
        </div>

        {/* Caps */}
        <div className="v-card">
          <div className="mb-3">
            <p className="v-section-label">Caps & Alerts</p>
            <p className="mt-0.5 text-sm font-semibold text-bone">Hard-stop · alert · forecast</p>
          </div>
          <div className="space-y-2">
            {CAPS.map((cap) => (
              <div key={cap.label} className="flex items-center justify-between rounded-md border border-rule/50 bg-ink-3/30 px-3 py-2.5">
                <span className="text-xs text-bone">{cap.label}</span>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-medium text-bone">{cap.value}</span>
                  <span className={`v-badge ${cap.type === "hard-stop" ? "v-badge-crimson" : "v-badge-amber"}`}>{cap.type}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
