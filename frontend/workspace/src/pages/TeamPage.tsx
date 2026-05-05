import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  Copy,
  KeyRound,
  Mail,
  ShieldCheck,
  ShieldX,
  UserCog,
  Users as UsersIcon,
  X,
} from "lucide-react";
import { api } from "@/lib/api";
import { cn, relativeTime } from "@/lib/cn";
import { actionUnavailableMessage, isRouteUnavailable } from "@/lib/errors";

interface TeamUser {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
  status: string;
  is_active: boolean;
  mfa_enabled: boolean;
  last_login: string | null;
  created_at: string;
}

interface Invite {
  id: string;
  email: string;
  role: string;
  status: "pending" | "accepted" | "revoked" | "expired";
  expires_at: string;
  created_at: string;
  token?: string;
}

async function listMembers(): Promise<TeamUser[]> {
  try {
    const resp = await api.get<{ items: TeamUser[] }>("/workspace/members");
    return resp.data.items ?? [];
  } catch (err) {
    if (!isRouteUnavailable(err)) throw err;
    const me = await api.get<{
      id: string;
      email: string;
      full_name?: string | null;
      role: string;
      status: string;
      mfa_enabled: boolean;
      last_login?: string | null;
      created_at: string;
    }>("/auth/me");
    return [
      {
        id: me.data.id,
        email: me.data.email,
        full_name: me.data.full_name ?? null,
        role: me.data.role,
        status: me.data.status,
        is_active: me.data.status === "active",
        mfa_enabled: me.data.mfa_enabled,
        last_login: me.data.last_login ?? null,
        created_at: me.data.created_at,
      },
    ];
  }
}

async function listInvites(): Promise<Invite[]> {
  try {
    const resp = await api.get<{ items: Invite[] }>("/workspace/members/invites");
    return resp.data.items ?? [];
  } catch (err) {
    const status = (err as { response?: { status?: number } })?.response?.status;
    if (status === 403) return [];
    throw err;
  }
}

async function probeInviteRoute(): Promise<"available" | "forbidden" | "unavailable"> {
  try {
    await api.get<{ items: Invite[] }>("/workspace/members/invites");
    return "available";
  } catch (err) {
    const status = (err as { response?: { status?: number } })?.response?.status;
    if (status === 403) return "forbidden";
    if (isRouteUnavailable(err)) return "unavailable";
    throw err;
  }
}

const ROLE_STYLE: Record<string, string> = {
  owner: "v-chip-brass",
  admin: "v-chip-brass",
  developer: "",
  viewer: "",
  billing: "",
};

function buildInviteLink(invite: Invite): string {
  const origin = typeof window !== "undefined" ? window.location.origin : "https://veklom.com";
  return `${origin}/workspace-app#/accept-invite?invite_secret=${encodeURIComponent(invite.token ?? "")}`;
}

export function TeamPage() {
  const qc = useQueryClient();
  const [showInvite, setShowInvite] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("user");
  const [issuedInvite, setIssuedInvite] = useState<Invite | null>(null);

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["team-members"],
    queryFn: listMembers,
  });
  const invitesQ = useQuery({ queryKey: ["team-invites"], queryFn: listInvites });
  const inviteRouteQ = useQuery({ queryKey: ["team-invite-route"], queryFn: probeInviteRoute, retry: false });
  const inviteRouteUnavailable = inviteRouteQ.data === "unavailable";

  const inviteMut = useMutation({
    mutationFn: async (payload: { email: string; role: string }) => {
      const r = await api.post<Invite>("/workspace/members/invite", payload);
      return r.data;
    },
    onSuccess: (data) => {
      setIssuedInvite(data);
      setInviteEmail("");
      qc.invalidateQueries({ queryKey: ["team-invites"] });
    },
  });

  const revokeMut = useMutation({
    mutationFn: async (id: string) => {
      await api.post(`/workspace/members/invites/${id}/revoke`, {});
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ["team-invites"] }),
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

  const pendingInvites = (invitesQ.data ?? []).filter((i) => i.status === "pending");

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
              live · <span className="font-mono">/api/v1/workspace/members</span>
            </span>
            <span className="v-chip">SAML / SCIM (coming)</span>
          </div>
        </div>
        <button className="v-btn-primary" disabled={inviteRouteUnavailable} onClick={() => setShowInvite(true)}>
          <Mail className="h-4 w-4" /> Invite member
        </button>
      </header>

      {inviteRouteUnavailable && (
        <div className="v-card border-brass/40 bg-brass/5 p-4 text-sm text-brass-2">
          Team invite delivery is not enabled on the live backend yet. Current signed-in identity is shown from{" "}
          <span className="font-mono">/api/v1/auth/me</span> until the member directory route is available.
        </div>
      )}

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
                    {u.role}
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

      {pendingInvites.length > 0 && (
        <section className="v-card p-0">
          <header className="flex items-center justify-between border-b border-rule px-5 py-3">
            <div>
              <div className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted">Pending invites</div>
              <h3 className="mt-0.5 text-sm font-semibold">Awaiting acceptance</h3>
            </div>
            <span className="v-chip font-mono">{pendingInvites.length}</span>
          </header>
          <ul className="divide-y divide-rule/50">
            {pendingInvites.map((i) => (
              <li key={i.id} className="flex items-center gap-3 px-5 py-2.5 font-mono text-[12px]">
                <Mail className="h-3.5 w-3.5 text-brass-2" />
                <div className="min-w-0 flex-1">
                  <div className="text-bone">{i.email}</div>
                  <div className="text-[10px] text-muted">role={i.role} · expires {relativeTime(i.expires_at)}</div>
                </div>
                <button
                  className="v-btn-ghost"
                  disabled={revokeMut.isPending}
                  onClick={() => revokeMut.mutate(i.id)}
                >
                  Revoke
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      {showInvite && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/80 backdrop-blur-sm">
          <div className="v-card w-full max-w-md p-5">
            <header className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-semibold">Invite team member</h3>
              <button
                className="text-muted hover:text-bone"
                onClick={() => {
                  setShowInvite(false);
                  setIssuedInvite(null);
                }}
              >
                <X className="h-4 w-4" />
              </button>
            </header>
            {issuedInvite ? (
              <div className="space-y-3">
                <div className="text-sm text-bone-2">
                  Invite created for <span className="font-mono text-bone">{issuedInvite.email}</span>.
                  Share this invite link. It will not be shown again.
                </div>
                <div className="flex items-center gap-2">
                  <input
                    readOnly
                    className="v-input w-full font-mono text-[11px]"
                    value={buildInviteLink(issuedInvite)}
                    onFocus={(e) => e.currentTarget.select()}
                  />
                  <button
                    className="v-btn-ghost"
                    onClick={() => navigator.clipboard?.writeText(buildInviteLink(issuedInvite))}
                  >
                    <Copy className="h-3.5 w-3.5" /> Copy
                  </button>
                </div>
                <div className="flex justify-end gap-2 pt-2">
                  <button
                    className="v-btn-ghost"
                    onClick={() => {
                      setIssuedInvite(null);
                    }}
                  >
                    Invite another
                  </button>
                  <button
                    className="v-btn-primary"
                    onClick={() => {
                      setShowInvite(false);
                      setIssuedInvite(null);
                    }}
                  >
                    Done
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <label className="block">
                  <div className="mb-1 font-mono text-[10px] uppercase tracking-wider text-muted">
                    Email
                  </div>
                  <input
                    className="v-input w-full"
                    type="email"
                    autoFocus
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    placeholder="colleague@company.com"
                  />
                </label>
                <label className="block">
                  <div className="mb-1 font-mono text-[10px] uppercase tracking-wider text-muted">
                    Role
                  </div>
                  <select
                    className="v-input w-full"
                    value={inviteRole}
                    onChange={(e) => setInviteRole(e.target.value)}
                  >
                    <option value="user">user</option>
                    <option value="analyst">analyst</option>
                    <option value="admin">admin</option>
                    <option value="readonly">readonly</option>
                  </select>
                </label>
                {inviteMut.isError && (
                  <div className="text-[12px] text-crimson">
                    {actionUnavailableMessage(inviteMut.error, "Team invites")}
                  </div>
                )}
                <div className="flex justify-end gap-2 pt-2">
                  <button className="v-btn-ghost" onClick={() => setShowInvite(false)}>
                    Cancel
                  </button>
                  <button
                    className="v-btn-primary"
                    disabled={!inviteEmail || inviteMut.isPending}
                    onClick={() => inviteMut.mutate({ email: inviteEmail, role: inviteRole })}
                  >
                    {inviteMut.isPending ? "Inviting…" : "Send invite"}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
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
