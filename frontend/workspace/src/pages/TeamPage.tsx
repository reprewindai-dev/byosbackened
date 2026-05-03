import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  KeyRound,
  Mail,
  ShieldCheck,
  ShieldX,
  UserCog,
  Users as UsersIcon,
} from "lucide-react";
import { api } from "@/lib/api";
import { cn, relativeTime } from "@/lib/cn";

interface TeamUser {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
  status: string;
  is_superuser: boolean;
  mfa_enabled: boolean;
  workspace_id: string;
  last_login: string | null;
  created_at: string;
}

async function listUsers(): Promise<TeamUser[]> {
  const resp = await api.get<TeamUser[]>("/admin/users", { params: { skip: 0, limit: 100 } });
  return resp.data;
}

const ROLE_STYLE: Record<string, string> = {
  owner: "v-chip-brass",
  admin: "v-chip-brass",
  developer: "",
  viewer: "",
  billing: "",
};

export function TeamPage() {
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["team-users"],
    queryFn: listUsers,
  });

  const stats = useMemo(() => {
    const users = data ?? [];
    return {
      total: users.length,
      mfa: users.filter((u) => u.mfa_enabled).length,
      admins: users.filter((u) => u.role === "admin" || u.role === "owner").length,
      active: users.filter((u) => u.status === "active").length,
    };
  }, [data]);

  const adminOnly = useMemo(() => {
    if (!isError) return false;
    const status = (error as { response?: { status?: number } })?.response?.status;
    return status === 403;
  }, [isError, error]);

  return (
    <div className="mx-auto w-full max-w-7xl space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="mb-1 font-mono text-[11px] uppercase tracking-[0.15em] text-muted">
            Workspace · Team &amp; access
          </div>
          <h1 className="text-3xl font-semibold tracking-tight">Members, roles &amp; MFA</h1>
          <p className="mt-2 max-w-2xl text-sm text-bone-2">
            Workspace members with role-scoped access. Every sign-in, MFA state, and privileged action flows
            through the audit trail.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <span className="v-chip v-chip-ok">
              <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-moss" />
              live · <span className="font-mono">/api/v1/admin/users</span>
            </span>
            <span className="v-chip">SAML / SCIM (coming)</span>
          </div>
        </div>
        <button className="v-btn-primary" disabled title="Invite flow ships in the next commit">
          <Mail className="h-4 w-4" /> Invite member
        </button>
      </header>

      {adminOnly && (
        <div className="v-card flex items-start gap-3 border-brass/40 bg-brass/5 p-4 text-sm text-brass-2">
          <ShieldX className="mt-0.5 h-4 w-4" />
          <div className="flex-1">
            <div className="font-semibold">Admin access required</div>
            <div className="mt-0.5 text-xs text-bone-2">
              Your role can't enumerate team members. Ask the workspace owner to elevate your role to{" "}
              <span className="font-mono">admin</span> or <span className="font-mono">owner</span>.
            </div>
          </div>
        </div>
      )}

      {isError && !adminOnly && (
        <div className="v-card flex items-start gap-3 border-crimson/40 bg-crimson/5 p-4 text-sm text-crimson">
          <AlertCircle className="mt-0.5 h-4 w-4" />
          <div className="flex-1">
            <div className="font-semibold">Failed to load members</div>
            <div className="mt-0.5 text-xs opacity-80">{(error as Error)?.message ?? "Unknown"}</div>
          </div>
          <button className="v-btn-ghost" onClick={() => refetch()}>
            Retry
          </button>
        </div>
      )}

      <section className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Kpi icon={<UsersIcon className="h-3 w-3" />} label="Members" value={String(stats.total)} />
        <Kpi icon={<UserCog className="h-3 w-3" />} label="Admins / owners" value={String(stats.admins)} />
        <Kpi
          icon={<ShieldCheck className="h-3 w-3" />}
          label="MFA enrolled"
          value={`${stats.mfa} / ${stats.total}`}
        />
        <Kpi icon={<KeyRound className="h-3 w-3" />} label="Active" value={String(stats.active)} />
      </section>

      <section className="v-card p-0">
        <header className="flex items-center justify-between border-b border-rule px-5 py-3">
          <div>
            <div className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted">Members</div>
            <h3 className="mt-0.5 text-sm font-semibold">Roles &amp; sign-in posture</h3>
          </div>
          <span className="v-chip font-mono">{isLoading ? "…" : `${data?.length ?? 0}`}</span>
        </header>

        <table className="w-full text-[13px]">
          <thead>
            <tr className="border-b border-rule font-mono text-[10px] uppercase tracking-wider text-muted">
              <th className="px-5 py-2 text-left font-medium">Member</th>
              <th className="px-5 py-2 text-left font-medium">Role</th>
              <th className="px-5 py-2 text-left font-medium">Status</th>
              <th className="px-5 py-2 text-left font-medium">MFA</th>
              <th className="px-5 py-2 text-right font-medium">Last sign-in</th>
              <th className="px-5 py-2 text-right font-medium">Joined</th>
            </tr>
          </thead>
          <tbody className="font-mono">
            {isLoading && (
              <tr>
                <td colSpan={6} className="px-5 py-8 text-center text-muted">
                  loading…
                </td>
              </tr>
            )}
            {!isLoading && !isError && data?.length === 0 && (
              <tr>
                <td colSpan={6} className="px-5 py-8 text-center text-muted">
                  No members visible in this workspace.
                </td>
              </tr>
            )}
            {data?.map((u) => (
              <tr key={u.id} className="border-b border-rule/60 last:border-0">
                <td className="px-5 py-2.5">
                  <div className="flex items-center gap-2">
                    <div className="flex h-7 w-7 items-center justify-center rounded-full bg-brass/15 font-mono text-[10px] font-semibold text-brass-2">
                      {(u.full_name || u.email || "?").slice(0, 2).toUpperCase()}
                    </div>
                    <div className="min-w-0">
                      <div className="truncate text-bone">{u.full_name || "—"}</div>
                      <div className="truncate text-[11px] text-muted">{u.email}</div>
                    </div>
                  </div>
                </td>
                <td className="px-5 py-2.5">
                  <span className={cn("v-chip font-mono", ROLE_STYLE[u.role] ?? "")}>
                    {u.is_superuser ? "superuser" : u.role}
                  </span>
                </td>
                <td className="px-5 py-2.5">
                  <span
                    className={cn(
                      "v-chip font-mono",
                      u.status === "active" ? "v-chip-ok" : "v-chip-warn",
                    )}
                  >
                    {u.status}
                  </span>
                </td>
                <td className="px-5 py-2.5">
                  {u.mfa_enabled ? (
                    <span className="v-chip v-chip-ok">
                      <ShieldCheck className="h-3 w-3" /> on
                    </span>
                  ) : (
                    <span className="v-chip v-chip-warn">
                      <ShieldX className="h-3 w-3" /> off
                    </span>
                  )}
                </td>
                <td className="px-5 py-2.5 text-right text-muted">
                  {u.last_login ? relativeTime(u.last_login) : "never"}
                </td>
                <td className="px-5 py-2.5 text-right text-muted">{relativeTime(u.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

function Kpi({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="v-card p-4">
      <div className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.1em] text-muted">
        {icon}
        {label}
      </div>
      <div className="mt-1.5 text-xl font-semibold text-bone">{value}</div>
    </div>
  );
}
