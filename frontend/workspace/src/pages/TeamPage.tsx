import { Plus, Mail, Shield, MoreVertical } from "lucide-react";

const MEMBERS = [
  { name: "Elliot Chen", email: "elliot@acme.io", role: "Owner", status: "active", lastActive: "2 min ago", mfa: true },
  { name: "Kira Nakamura", email: "kira@acme.io", role: "Admin", status: "active", lastActive: "18 min ago", mfa: true },
  { name: "Alex Petrov", email: "alex@acme.io", role: "Developer", status: "active", lastActive: "1 hr ago", mfa: true },
  { name: "Sarah Kim", email: "sarah@acme.io", role: "Developer", status: "active", lastActive: "3 hr ago", mfa: false },
  { name: "Jordan Reeves", email: "jordan@acme.io", role: "Viewer", status: "active", lastActive: "1 d ago", mfa: true },
  { name: "CI Runner", email: "ci@acme.io", role: "Service", status: "active", lastActive: "live", mfa: false },
];

const PENDING = [
  { email: "new-dev@acme.io", role: "Developer", invited: "2 hr ago" },
  { email: "auditor@external.com", role: "Viewer", invited: "1 d ago" },
];

export function TeamPage() {
  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-start justify-between">
        <div>
          <p className="v-section-label">Operations · Team</p>
          <h1 className="mt-1 text-2xl font-bold text-bone">Workspace members</h1>
          <p className="mt-1 text-sm text-muted">RBAC, MFA enforcement, and audit-logged access control.</p>
        </div>
        <button className="v-btn-primary text-xs"><Plus className="h-3.5 w-3.5" /> Invite member</button>
      </div>

      <div className="v-card-flush">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-rule text-left">
              <th className="px-4 py-3 font-mono text-[9px] uppercase text-muted">Member</th>
              <th className="px-3 py-3 font-mono text-[9px] uppercase text-muted">Role</th>
              <th className="px-3 py-3 font-mono text-[9px] uppercase text-muted">MFA</th>
              <th className="px-3 py-3 font-mono text-[9px] uppercase text-muted">Last Active</th>
              <th className="px-3 py-3 font-mono text-[9px] uppercase text-muted">Status</th>
              <th className="w-10"></th>
            </tr>
          </thead>
          <tbody>
            {MEMBERS.map((m) => (
              <tr key={m.email} className="border-b border-rule/50 hover:bg-ink-3/40">
                <td className="px-4 py-3">
                  <p className="font-medium text-bone">{m.name}</p>
                  <p className="text-[10px] text-muted">{m.email}</p>
                </td>
                <td className="px-3 py-3">
                  <span className={`v-badge ${m.role === "Owner" ? "v-badge-amber" : m.role === "Admin" ? "v-badge-electric" : "v-badge-muted"}`}>{m.role}</span>
                </td>
                <td className="px-3 py-3">
                  {m.mfa ? <Shield className="h-3.5 w-3.5 text-moss" /> : <span className="text-crimson text-[10px]">off</span>}
                </td>
                <td className="px-3 py-3 text-muted">{m.lastActive}</td>
                <td className="px-3 py-3"><span className="v-badge-green">● {m.status}</span></td>
                <td className="px-2"><MoreVertical className="h-3.5 w-3.5 text-muted cursor-pointer" /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {PENDING.length > 0 && (
        <div className="v-card">
          <p className="v-section-label">Pending Invitations</p>
          <div className="mt-3 space-y-2">
            {PENDING.map((p) => (
              <div key={p.email} className="flex items-center justify-between rounded-md border border-rule/50 bg-ink-3/30 px-3 py-2.5">
                <div className="flex items-center gap-2">
                  <Mail className="h-3.5 w-3.5 text-muted" />
                  <span className="text-xs text-bone">{p.email}</span>
                  <span className="v-badge-muted">{p.role}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-[10px] text-muted">{p.invited}</span>
                  <button className="text-[10px] text-brass hover:text-brass-2">Resend</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
