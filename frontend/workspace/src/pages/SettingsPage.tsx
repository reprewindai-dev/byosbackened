import { Save } from "lucide-react";
import { useAuthStore } from "@/store/auth-store";

export function SettingsPage() {
  const user = useAuthStore((s) => s.user);

  return (
    <div className="space-y-6 animate-fade-in max-w-3xl">
      <div>
        <p className="v-section-label">Settings</p>
        <h1 className="mt-1 text-2xl font-bold text-bone">Workspace configuration</h1>
        <p className="mt-1 text-sm text-muted">General settings, API keys, integrations, and notification preferences.</p>
      </div>

      {/* General */}
      <div className="v-card space-y-4">
        <p className="text-sm font-semibold text-bone">General</p>
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="v-label">Workspace Name</label>
            <input className="v-input" defaultValue={user?.workspace_name || "acme-prod"} />
          </div>
          <div>
            <label className="v-label">Region</label>
            <select className="v-input"><option>EU-Sovereign (Hetzner)</option><option>US-East (AWS)</option></select>
          </div>
          <div>
            <label className="v-label">Default Policy Pack</label>
            <select className="v-input"><option>sovereign_v3</option><option>hipaa_strict</option><option>soc2_continuous</option></select>
          </div>
          <div>
            <label className="v-label">Audit Retention</label>
            <select className="v-input"><option>1 year</option><option>30 days</option><option>7 days</option></select>
          </div>
        </div>
      </div>

      {/* API Keys */}
      <div className="v-card space-y-4">
        <div className="flex items-center justify-between">
          <p className="text-sm font-semibold text-bone">API Keys</p>
          <button className="v-btn-ghost text-xs">Generate new key</button>
        </div>
        <div className="rounded-md border border-rule bg-ink-3 px-3 py-2">
          <div className="flex items-center justify-between">
            <span className="font-mono text-xs text-bone-2">byos_prod_8h2x...4f9a</span>
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-muted">Created 2026-03-01</span>
              <span className="v-badge-green">Active</span>
            </div>
          </div>
        </div>
      </div>

      {/* Notifications */}
      <div className="v-card space-y-4">
        <p className="text-sm font-semibold text-bone">Notifications</p>
        <div className="space-y-3">
          {[
            { label: "Cost alerts (> 90% cap)", channel: "Email + Slack" },
            { label: "Security events", channel: "PagerDuty" },
            { label: "Compliance drift", channel: "Email" },
            { label: "Deployment failures", channel: "Slack #ops" },
          ].map((n) => (
            <div key={n.label} className="flex items-center justify-between">
              <span className="text-xs text-bone">{n.label}</span>
              <span className="font-mono text-[10px] text-muted">{n.channel}</span>
            </div>
          ))}
        </div>
      </div>

      <button className="v-btn-primary"><Save className="h-4 w-4" /> Save changes</button>
    </div>
  );
}
