import { useState } from "react";
import { Settings, GitBranch, Shield, Database, Code2, Bell, Palette, Link2, AlertTriangle } from "lucide-react";

const NAV = [
  { key: "workspace", label: "Workspace", icon: Settings },
  { key: "routing", label: "Routing", icon: GitBranch },
  { key: "security", label: "Security", icon: Shield },
  { key: "residency", label: "Data residency", icon: Database },
  { key: "api", label: "API & SDK", icon: Code2 },
  { key: "notifications", label: "Notifications", icon: Bell },
  { key: "appearance", label: "Appearance", icon: Palette },
  { key: "integrations", label: "Integrations", icon: Link2 },
];

const INTEGRATIONS = [
  { name: "Slack", on: true },
  { name: "PagerDuty", on: true },
  { name: "GitHub", on: true },
  { name: "Vercel", on: true },
  { name: "Datadog", on: false },
  { name: "Jira", on: false },
];

export function SettingsPage() {
  const [active, setActive] = useState("workspace");
  const [toggles, setToggles] = useState<Record<string, boolean>>(
    Object.fromEntries(INTEGRATIONS.map(i => [i.name, i.on]))
  );

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <p className="v-section-label">Settings</p>
        <h1 className="mt-1 text-2xl font-bold text-bone">Workspace administration</h1>
        <p className="mt-1 max-w-2xl text-sm text-muted">
          One opinionated panel for the entire control plane — workspace identity, routing posture, security defaults, branding, and integrations.
        </p>
      </div>

      {/* 2-col: nav + content */}
      <div className="flex gap-6">
        {/* Settings nav */}
        <div className="w-52 shrink-0 space-y-0.5">
          {NAV.map((item) => (
            <button
              key={item.key}
              onClick={() => setActive(item.key)}
              className={`flex w-full items-center gap-2.5 rounded-md px-3 py-2 text-xs transition ${active === item.key ? "bg-ink-3 text-bone font-medium" : "text-muted hover:text-bone hover:bg-ink-3/40"}`}
            >
              <item.icon className="h-3.5 w-3.5" />
              {item.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 space-y-5">
          {/* Workspace */}
          <div className="v-card">
            <div className="flex items-center gap-2 mb-4">
              <Settings className="h-4 w-4 text-amber" />
              <span className="text-sm font-semibold text-bone">Workspace</span>
            </div>
            <div className="grid grid-cols-2 gap-y-3 gap-x-8 text-xs">
              <KV label="Workspace name" value="acme-prod" />
              <KV label="Default region" value="fsn1-hetz · EU-sovereign" />
              <KV label="Slug" value="acme.veklom.app" />
            </div>
          </div>

          {/* Routing */}
          <div className="v-card">
            <div className="flex items-center gap-2 mb-4">
              <GitBranch className="h-4 w-4 text-amber" />
              <span className="text-sm font-semibold text-bone">Routing</span>
            </div>
            <div className="grid grid-cols-2 gap-y-3 gap-x-8 text-xs">
              <KV label="Primary plane" value="Hetzner (FSN1, FRA1)" />
              <KV label="Burst plane" value="AWS (us-east-1, eu-west-1)" />
              <KV label="Burst ceiling" value="20% traffic · $3,000 spend" />
              <KV label="Egress allowlist" value="12 hosts · enforced" />
            </div>
          </div>

          {/* Security */}
          <div className="v-card">
            <div className="flex items-center gap-2 mb-4">
              <Shield className="h-4 w-4 text-amber" />
              <span className="text-sm font-semibold text-bone">Security</span>
            </div>
            <div className="grid grid-cols-2 gap-y-3 gap-x-8 text-xs">
              <KV label="MFA enforcement" value="org-wide · TOTP + WebAuthn" />
              <KV label="TLS" value="1.3 · mTLS internal" />
              <KV label="Session timeout" value="12 hr" />
              <KV label="Vault seal" value="FIPS 140-2 L3 HSM" />
            </div>
          </div>

          {/* Integrations */}
          <div className="v-card">
            <div className="flex items-center gap-2 mb-4">
              <Link2 className="h-4 w-4 text-amber" />
              <span className="text-sm font-semibold text-bone">Integrations</span>
            </div>
            <div className="grid grid-cols-3 gap-3">
              {INTEGRATIONS.map((intg) => (
                <div key={intg.name} className="flex items-center justify-between text-xs">
                  <span className="text-bone">{intg.name}</span>
                  <button
                    onClick={() => setToggles(t => ({ ...t, [intg.name]: !t[intg.name] }))}
                    className={`relative inline-flex h-5 w-9 items-center rounded-full transition ${toggles[intg.name] ? "bg-amber" : "bg-ink-3"}`}
                  >
                    <span className={`inline-block h-3.5 w-3.5 rounded-full bg-ink transition-transform ${toggles[intg.name] ? "translate-x-4" : "translate-x-0.5"}`} />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Danger zone */}
          <div className="v-card border-crimson/20">
            <div className="flex items-center gap-2 mb-4">
              <AlertTriangle className="h-4 w-4 text-crimson" />
              <span className="text-sm font-semibold text-crimson">Danger zone</span>
            </div>
            <div className="space-y-3">
              <div className="flex items-center justify-between rounded-md border border-rule/40 bg-ink-3/20 px-4 py-3">
                <div>
                  <p className="text-xs font-medium text-bone">Pause all deployments</p>
                  <p className="text-[10px] text-muted">Drains traffic, preserves audit trail.</p>
                </div>
                <button className="rounded bg-crimson/15 border border-crimson/30 px-3 py-1.5 text-xs font-semibold text-crimson">Pause</button>
              </div>
              <div className="flex items-center justify-between rounded-md border border-rule/40 bg-ink-3/20 px-4 py-3">
                <div>
                  <p className="text-xs font-medium text-bone">Rotate workspace secrets</p>
                  <p className="text-[10px] text-muted">Re-issues all keys, emits audit.</p>
                </div>
                <button className="rounded bg-crimson/15 border border-crimson/30 px-3 py-1.5 text-xs font-semibold text-crimson">Rotate</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function KV({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between border-b border-rule/20 pb-2">
      <span className="text-muted">{label}</span>
      <span className="font-mono text-bone text-right">{value}</span>
    </div>
  );
}
