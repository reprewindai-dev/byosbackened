import { useState, useEffect, useCallback } from "react";
import { UserPlus, Shield, Settings2, Loader2, Pencil } from "lucide-react";
import { api } from "@/lib/api";

interface Member {
  id: string;
  email: string;
  full_name?: string;
  role?: string;
  mfa_enabled?: boolean;
  is_superuser?: boolean;
  is_active?: boolean;
  last_active?: string;
}

const ROLE_COLORS: Record<string, string> = {
  owner: "bg-amber/20 text-amber",
  admin: "bg-electric/20 text-electric",
  developer: "bg-bone/10 text-bone",
  viewer: "bg-bone/10 text-bone",
  billing: "bg-bone/10 text-bone",
};

function initials(name?: string, email?: string): string {
  if (name) return name.split(" ").map(w => w[0]).join("").toUpperCase().slice(0, 2);
  return (email || "??").slice(0, 2).toUpperCase();
}

const AVATAR_COLORS = ["bg-violet-500", "bg-amber-500", "bg-emerald-500", "bg-sky-500", "bg-rose-500", "bg-brass"];

const STATIC_MEMBERS: Member[] = [
  { id: "1", full_name: "Elliot Jurić", email: "elliot@acme.io", role: "owner", mfa_enabled: true, last_active: "now" },
  { id: "2", full_name: "Kira Bansal", email: "kira@acme.io", role: "admin", mfa_enabled: true, last_active: "12 min" },
  { id: "3", full_name: "Alex Tran", email: "alex@acme.io", role: "developer", mfa_enabled: true, last_active: "1 hr" },
  { id: "4", full_name: "Sara Olin", email: "sara@acme.io", role: "developer", mfa_enabled: false, last_active: "yesterday" },
  { id: "5", full_name: "Tomás Reyes", email: "tomas@acme.io", role: "viewer", mfa_enabled: true, last_active: "3 days" },
  { id: "6", full_name: "Lin Park", email: "lin@acme.io", role: "billing", mfa_enabled: true, last_active: "5 days" },
];

const IDENTITY_CONFIG = [
  { label: "SAML 2.0 SSO", value: "Okta", status: "Active", statusColor: "bg-amber/20 text-amber" },
  { label: "SCIM provisioning", value: "Okta", status: "8 Mapped", statusColor: "bg-amber/20 text-amber" },
  { label: "GitHub OAuth", value: "", status: "Enabled", statusColor: "bg-moss/20 text-moss" },
  { label: "Google OAuth", value: "", status: "Enabled", statusColor: "bg-moss/20 text-moss" },
  { label: "Email / password", value: "", status: "Off (Org-Locked)", statusColor: "bg-bone/10 text-muted" },
  { label: "Session timeout", value: "", status: "12 hr · Device-Tracked", statusColor: "bg-electric/20 text-electric" },
];

const PERMISSIONS_RESOURCES = ["Deployments", "Endpoints", "Logs", "Vault", "Compliance", "Billing", "Team"];
const PERMISSION_ROLES = ["Owner", "Admin", "Developer", "Viewer", "Billing"];
const PERMS: Record<string, string[]> = {
  Deployments: ["RWX", "RWX", "RW", "R", "—"],
  Endpoints:   ["RWX", "RWX", "RW", "R", "—"],
  Logs:        ["RWX", "RWX", "R", "R", "—"],
  Vault:       ["RWX", "RW", "R", "—", "—"],
  Compliance:  ["RWX", "RWX", "R", "R", "—"],
  Billing:     ["RWX", "RW", "—", "—", "RWX"],
  Team:        ["RWX", "RW", "—", "—", "—"],
};

const ACCESS_CHANGES = [
  { actor: "elliot@acme.io", action: "promoted alex@acme.io to Developer", time: "2 hr ago" },
  { actor: "okta-system", action: "provisioned tomas@acme.io · Viewer", time: "1 d ago" },
  { actor: "kira@acme.io", action: "rotated ci-test-runner key", time: "3 d ago" },
  { actor: "elliot@acme.io", action: "enforced MFA org-wide", time: "1 wk ago" },
];

export function TeamPage() {
  const [members, setMembers] = useState<Member[]>(STATIC_MEMBERS);
  const [loading, setLoading] = useState(true);

  const fetchMembers = useCallback(async () => {
    try {
      const { data } = await api.get("/admin/users");
      const live = Array.isArray(data) ? data : data?.users || [];
      if (live.length > 0) setMembers(live);
    } catch { /* use static */ }
    setLoading(false);
  }, []);

  useEffect(() => { fetchMembers(); }, [fetchMembers]);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <p className="v-section-label">Team & Access</p>
          <h1 className="mt-1 text-2xl font-bold text-bone">Roles · MFA · sessions · SAML / SCIM</h1>
          <p className="mt-1 max-w-2xl text-sm text-muted">
            Owner, Admin, Developer, Viewer, Billing-only — with per-resource permissions, MFA enforcement, SCIM provisioning, and SAML SSO.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button className="flex items-center gap-1.5 rounded-md border border-rule px-3 py-1.5 text-xs text-muted hover:text-bone hover:border-muted transition-colors">
            <Settings2 className="h-3.5 w-3.5" /> SSO settings
          </button>
          <button className="v-btn-primary text-xs"><UserPlus className="h-3.5 w-3.5" /> Invite member</button>
        </div>
      </div>

      {/* Members + Identity */}
      <div className="grid gap-4 lg:grid-cols-5">
        {/* Members table */}
        <div className="v-card-flush lg:col-span-3">
          <div className="flex items-center justify-between px-4 py-3 border-b border-rule">
            <span className="font-mono text-[10px] uppercase text-muted">Members · {members.length}</span>
            <div className="flex items-center gap-2">
              <span className="flex items-center gap-1 rounded bg-amber/10 px-2 py-0.5 text-[9px] font-mono text-amber">
                <Shield className="h-2.5 w-2.5" /> MFA Enforced (Org)
              </span>
              <span className="rounded bg-electric/10 px-2 py-0.5 text-[9px] font-mono text-electric">SCIM 2.0</span>
            </div>
          </div>
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-rule text-left">
                <th className="px-4 py-2.5 font-mono text-[9px] uppercase text-muted">Name</th>
                <th className="px-3 py-2.5 font-mono text-[9px] uppercase text-muted">Email</th>
                <th className="px-3 py-2.5 font-mono text-[9px] uppercase text-muted">Role</th>
                <th className="px-3 py-2.5 font-mono text-[9px] uppercase text-muted">MFA</th>
                <th className="px-3 py-2.5 font-mono text-[9px] uppercase text-muted">Last Active</th>
                <th className="w-8"></th>
              </tr>
            </thead>
            <tbody>
              {loading && members === STATIC_MEMBERS ? (
                <tr><td colSpan={6} className="px-4 py-6 text-center text-muted"><Loader2 className="mx-auto h-4 w-4 animate-spin" /></td></tr>
              ) : members.map((m, i) => {
                const role = m.is_superuser ? "owner" : m.role || "developer";
                return (
                  <tr key={m.id} className="border-b border-rule/40 hover:bg-white/[0.02]">
                    <td className="px-4 py-2.5">
                      <div className="flex items-center gap-2.5">
                        <div className={`flex h-7 w-7 items-center justify-center rounded-full ${AVATAR_COLORS[i % AVATAR_COLORS.length]} text-white font-bold text-[10px]`}>
                          {initials(m.full_name, m.email)}
                        </div>
                        <span className="font-medium text-bone">{m.full_name || "—"}</span>
                      </div>
                    </td>
                    <td className="px-3 py-2.5 font-mono text-muted">{m.email}</td>
                    <td className="px-3 py-2.5">
                      <span className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${ROLE_COLORS[role] || "bg-bone/10 text-muted"}`}>
                        {role}
                      </span>
                    </td>
                    <td className="px-3 py-2.5">
                      <span className={`inline-flex items-center gap-1 text-[10px] font-mono ${m.mfa_enabled ? "text-moss" : "text-crimson"}`}>
                        <span className={`h-1.5 w-1.5 rounded-full ${m.mfa_enabled ? "bg-moss" : "bg-crimson"}`} />
                        {m.mfa_enabled ? "On" : "Off"}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-muted">{m.last_active || "—"}</td>
                    <td className="px-2 py-2.5">
                      <Pencil className="h-3 w-3 text-muted/50 hover:text-bone cursor-pointer" />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Identity panel */}
        <div className="v-card lg:col-span-2">
          <p className="v-section-label">Identity</p>
          <p className="mt-0.5 text-sm font-semibold text-bone">Federated · enterprise-grade</p>
          <div className="mt-4 space-y-3">
            {IDENTITY_CONFIG.map((item) => (
              <div key={item.label} className="flex items-center justify-between">
                <span className="text-xs text-bone">{item.label}</span>
                <span className={`rounded px-2 py-0.5 text-[9px] font-mono font-semibold ${item.statusColor}`}>
                  {item.value ? `${item.value} · ` : ""}{item.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Roles & Permissions + Access Changes */}
      <div className="grid gap-4 lg:grid-cols-5">
        {/* Permissions matrix */}
        <div className="v-card lg:col-span-3">
          <p className="v-section-label">Roles · Per-Resource Permissions</p>
          <p className="mt-0.5 text-sm font-semibold text-bone">Owner · Admin · Developer · Viewer · Billing-only</p>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-rule">
                  <th className="pb-2 pr-4 text-left font-mono text-[9px] uppercase text-muted">Resource</th>
                  {PERMISSION_ROLES.map((r) => (
                    <th key={r} className="pb-2 px-2 text-center font-mono text-[9px] uppercase text-muted">{r}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {PERMISSIONS_RESOURCES.map((res) => (
                  <tr key={res} className="border-b border-rule/30">
                    <td className="py-2.5 pr-4 font-medium text-bone">{res}</td>
                    {PERMS[res].map((perm, i) => (
                      <td key={i} className="py-2.5 px-2 text-center">
                        <span className={`font-mono text-[10px] ${perm === "RWX" ? "text-amber font-semibold" : perm === "RW" ? "text-brass" : perm === "R" ? "text-electric" : "text-muted/40"}`}>
                          {perm}
                        </span>
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Access Changes */}
        <div className="v-card lg:col-span-2">
          <p className="v-section-label">Access Changes · Auditable</p>
          <p className="mt-0.5 text-sm font-semibold text-bone">Tamper-evident · 365 d retention</p>
          <div className="mt-4 space-y-3">
            {ACCESS_CHANGES.map((ev, i) => (
              <div key={i} className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-mono text-[11px] font-medium text-bone">{ev.actor}</p>
                  <p className="truncate text-[11px] text-muted">{ev.action}</p>
                </div>
                <span className="shrink-0 font-mono text-[10px] text-muted-2">{ev.time}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
