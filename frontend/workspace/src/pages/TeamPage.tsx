import { useState, useEffect, useCallback } from "react";
import { UserPlus, Shield, MoreVertical, Loader2 } from "lucide-react";
import { api } from "@/lib/api";

interface Member {
  id: string;
  email: string;
  full_name?: string;
  role?: string;
  mfa_enabled?: boolean;
  is_superuser?: boolean;
  is_active?: boolean;
}

const ROLE_COLORS: Record<string, string> = {
  owner: "v-badge-amber",
  admin: "v-badge-electric",
  superuser: "v-badge-amber",
};

function initials(name?: string, email?: string): string {
  if (name) return name.split(" ").map(w => w[0]).join("").toUpperCase().slice(0, 2);
  return (email || "??").slice(0, 2).toUpperCase();
}

const AVATAR_COLORS = ["bg-amber", "bg-electric", "bg-moss", "bg-violet", "bg-crimson", "bg-brass"];

export function TeamPage() {
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMembers = useCallback(async () => {
    try {
      const { data } = await api.get("/admin/users");
      setMembers(Array.isArray(data) ? data : data?.users || []);
      setError(null);
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 403) {
        setError("Admin access required to view team members");
      } else {
        setError("Could not load team members");
      }
    }
    setLoading(false);
  }, []);

  useEffect(() => { fetchMembers(); }, [fetchMembers]);

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-start justify-between">
        <div>
          <p className="v-section-label">Team</p>
          <h1 className="mt-1 text-2xl font-bold text-bone">Workspace members</h1>
          <p className="mt-1 text-sm text-muted">Role-based access, MFA enforcement, audit-logged member activity.</p>
        </div>
        <button className="v-btn-primary text-xs"><UserPlus className="h-3.5 w-3.5" /> Invite</button>
      </div>

      {error && (
        <div className="rounded-md border border-amber/30 bg-amber/5 px-4 py-3 text-xs text-amber">{error}</div>
      )}

      <div className="v-card-flush">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-rule text-left">
              <th className="px-4 py-3 font-mono text-[9px] uppercase text-muted">Member</th>
              <th className="px-3 py-3 font-mono text-[9px] uppercase text-muted">Role</th>
              <th className="px-3 py-3 font-mono text-[9px] uppercase text-muted">MFA</th>
              <th className="w-10"></th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={4} className="px-4 py-6 text-center text-muted"><Loader2 className="mx-auto h-4 w-4 animate-spin" /></td></tr>
            ) : members.length > 0 ? members.map((m, i) => {
              const role = m.is_superuser ? "owner" : m.role || "member";
              return (
                <tr key={m.id} className="border-b border-rule/50 hover:bg-ink-3/40">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div className={`flex h-8 w-8 items-center justify-center rounded-full ${AVATAR_COLORS[i % AVATAR_COLORS.length]} text-ink font-bold text-xs`}>{initials(m.full_name, m.email)}</div>
                      <div>
                        <p className="font-medium text-bone">{m.full_name || "—"}</p>
                        <p className="font-mono text-[10px] text-muted">{m.email}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-3 py-3">
                    <span className={`v-badge ${ROLE_COLORS[role] || "v-badge-muted"}`}>
                      {role === "owner" && <Shield className="h-2.5 w-2.5 mr-0.5" />}{role}
                    </span>
                  </td>
                  <td className="px-3 py-3">
                    <span className={`v-badge ${m.mfa_enabled ? "v-badge-green" : "v-badge-crimson"}`}>{m.mfa_enabled ? "enabled" : "off"}</span>
                  </td>
                  <td className="px-3 py-3"><MoreVertical className="h-3.5 w-3.5 text-muted cursor-pointer" /></td>
                </tr>
              );
            }) : (
              <tr><td colSpan={4} className="px-4 py-6 text-center text-muted">No team members found</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
