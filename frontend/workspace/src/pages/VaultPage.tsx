import { Plus, RotateCcw, Eye, EyeOff, Copy } from "lucide-react";
import { useState } from "react";

const SECRETS = [
  { name: "OPENAI_API_KEY", scope: "chat-prod", rotated: "2 hr ago", created: "2026-01-15", masked: true },
  { name: "ANTHROPIC_KEY", scope: "chat-burst", rotated: "1 d ago", created: "2026-02-01", masked: true },
  { name: "STRIPE_SK_LIVE", scope: "billing-svc", rotated: "7 d ago", created: "2025-11-20", masked: true },
  { name: "DB_PASSWORD_PROD", scope: "global", rotated: "14 d ago", created: "2025-10-01", masked: true },
  { name: "S3_ACCESS_KEY", scope: "evidence-export", rotated: "3 d ago", created: "2026-03-10", masked: true },
  { name: "ENCRYPTION_KEY_V2", scope: "global", rotated: "30 d ago", created: "2025-08-01", masked: true },
];

const POLICIES = [
  { rule: "Auto-rotate provider keys every 24h", status: "active" },
  { rule: "Mask all secrets in logs (zero-knowledge)", status: "active" },
  { rule: "Require 2 approvers for production secrets", status: "active" },
  { rule: "Alert on any secret access outside business hours", status: "active" },
];

export function VaultPage() {
  const [revealed, setRevealed] = useState<Set<string>>(new Set());

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-start justify-between">
        <div>
          <p className="v-section-label">Governance · Vault</p>
          <h1 className="mt-1 text-2xl font-bold text-bone">Secret management</h1>
          <p className="mt-1 text-sm text-muted">Encrypted at rest, auto-rotated, zero-knowledge access. Every read is audited.</p>
        </div>
        <div className="flex gap-2">
          <button className="v-btn-ghost text-xs"><RotateCcw className="h-3.5 w-3.5" /> Rotate all</button>
          <button className="v-btn-primary text-xs"><Plus className="h-3.5 w-3.5" /> Add secret</button>
        </div>
      </div>

      <div className="v-card-flush">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-rule text-left">
              <th className="px-4 py-3 font-mono text-[9px] uppercase text-muted">Name</th>
              <th className="px-3 py-3 font-mono text-[9px] uppercase text-muted">Scope</th>
              <th className="px-3 py-3 font-mono text-[9px] uppercase text-muted">Last Rotated</th>
              <th className="px-3 py-3 font-mono text-[9px] uppercase text-muted">Value</th>
              <th className="px-3 py-3 font-mono text-[9px] uppercase text-muted">Actions</th>
            </tr>
          </thead>
          <tbody>
            {SECRETS.map((s) => (
              <tr key={s.name} className="border-b border-rule/50 hover:bg-ink-3/40">
                <td className="px-4 py-3 font-mono font-medium text-bone">{s.name}</td>
                <td className="px-3 py-3"><span className="v-badge-muted">{s.scope}</span></td>
                <td className="px-3 py-3 text-muted">{s.rotated}</td>
                <td className="px-3 py-3 font-mono text-muted-2">
                  {revealed.has(s.name) ? "sk_live_51So...3x8F" : "••••••••••••••••"}
                </td>
                <td className="px-3 py-3">
                  <div className="flex gap-1">
                    <button onClick={() => setRevealed((r) => { const n = new Set(r); n.has(s.name) ? n.delete(s.name) : n.add(s.name); return n; })} className="rounded p-1 text-muted hover:bg-ink-3 hover:text-bone">
                      {revealed.has(s.name) ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                    </button>
                    <button className="rounded p-1 text-muted hover:bg-ink-3 hover:text-bone"><Copy className="h-3.5 w-3.5" /></button>
                    <button className="rounded p-1 text-muted hover:bg-ink-3 hover:text-bone"><RotateCcw className="h-3.5 w-3.5" /></button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="v-card">
        <p className="v-section-label">Vault Policies</p>
        <p className="mt-0.5 text-sm font-semibold text-bone">Enforced rotation & access rules</p>
        <div className="mt-4 space-y-2">
          {POLICIES.map((p) => (
            <div key={p.rule} className="flex items-center justify-between rounded-md border border-rule/50 bg-ink-3/30 px-3 py-2.5">
              <span className="text-xs text-bone">{p.rule}</span>
              <span className="v-badge-green">● {p.status}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
