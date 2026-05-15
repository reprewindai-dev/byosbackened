import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  Bell,
  BookOpen,
  CheckCircle2,
  Command,
  CreditCard,
  Key,
  LogOut,
  Search,
  Settings as SettingsIcon,
  ShieldCheck,
  User as UserIcon,
} from "lucide-react";
import { api, apiRoot } from "@/lib/api";
import { logout } from "@/lib/auth";
import { cn, fmtCents } from "@/lib/cn";
import { useAuthStore } from "@/store/auth-store";
import type { OverviewPayload } from "@/types/api";

interface WalletBalance {
  balance: number;
  reserve_balance_usd?: string;
  monthly_credits_included: number;
  monthly_credits_used: number;
}

interface StatusFeedItem {
  id?: string;
  title?: string;
  description?: string;
  severity?: string;
  status?: string;
  created_at?: string;
  updated_at?: string;
}

interface StatusPayload {
  timestamp?: string;
  overall_status?: string;
  current_status?: string;
  incidents?: StatusFeedItem[];
  maintenance?: StatusFeedItem[];
}

interface OperatorDigest {
  findings?: Array<{
    code: string;
    title: string;
    severity: string;
    operator_action: string;
  }>;
}

const JUMP_ROUTES = [
  { label: "dashboard", to: "/control-center" },
  { label: "control center", to: "/control-center" },
  { label: "owner console", to: "/control-center" },
  { label: "playground", to: "/playground" },
  { label: "gpc", to: "/gpc" },
  { label: "marketplace", to: "/marketplace" },
  { label: "models", to: "/models" },
  { label: "pipelines", to: "/pipelines" },
  { label: "deployments", to: "/deployments" },
  { label: "routing", to: "/routing" },
  { label: "vault", to: "/vault" },
  { label: "api keys", to: "/vault" },
  { label: "compliance", to: "/compliance" },
  { label: "security", to: "/security" },
  { label: "privacy", to: "/privacy" },
  { label: "content safety", to: "/content-safety" },
  { label: "insights", to: "/insights" },
  { label: "budget", to: "/budget" },
  { label: "plugins", to: "/plugins" },
  { label: "jobs", to: "/jobs" },
  { label: "autonomy", to: "/autonomy" },
  { label: "monitoring", to: "/monitoring" },
  { label: "billing", to: "/billing" },
  { label: "team", to: "/team" },
  { label: "settings", to: "/settings" },
];

export function TopBar() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const [jump, setJump] = useState("");
  const [notifOpen, setNotifOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const notifRef = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  const overview = useQuery({
    queryKey: ["topbar-overview"],
    queryFn: async () => (await api.get<OverviewPayload>("/monitoring/overview")).data,
    refetchInterval: 30_000,
    retry: false,
  });
  const wallet = useQuery({
    queryKey: ["topbar-wallet"],
    queryFn: async () => (await api.get<WalletBalance>("/billing/wallet")).data,
    refetchInterval: 30_000,
    retry: false,
  });
  const statusFeed = useQuery({
    queryKey: ["topbar-status-feed"],
    queryFn: async () => (await apiRoot.get<StatusPayload>("/status/data")).data,
    refetchInterval: 60_000,
    retry: false,
  });
  const operatorDigest = useQuery({
    queryKey: ["topbar-operator-digest"],
    queryFn: async () => (await api.get<OperatorDigest>("/operators/digest")).data,
    enabled: Boolean(user?.is_superuser),
    refetchInterval: 60_000,
    retry: false,
  });

  // Close popovers on outside click
  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) setNotifOpen(false);
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  const displayName = user?.full_name ?? user?.name ?? user?.email ?? "Veklom";
  const isSuperuser = Boolean(user?.is_superuser);
  const initials = displayName
    .split(/[\s@]/)
    .filter(Boolean)
    .slice(0, 2)
    .map((s) => s[0]?.toUpperCase() ?? "")
    .join("");
  const workspaceLabel = user?.workspace_name?.trim() || "Workspace";
  const regionLabel = user?.region?.trim() || "tenant-scoped";
  const planLabel = (user?.plan ?? user?.role ?? "live").replace(/_/g, " ");
  const burnCents = overview.data?.spend?.burn_rate_per_min_cents;
  const reserveUsd = Number(wallet.data?.reserve_balance_usd ?? 0);
  const reserveState = wallet.isError ? "unknown" : reserveUsd <= 0 ? "empty" : reserveUsd < 25 ? "low" : "funded";
  const budgetPct = useMemo(() => {
    const included = wallet.data?.monthly_credits_included ?? 0;
    if (included > 0) return Math.round(((wallet.data?.monthly_credits_used ?? 0) / included) * 100);
    return overview.data?.spend?.forecast_cap_pct;
  }, [overview.data?.spend?.forecast_cap_pct, wallet.data]);
  const degraded = overview.isError || wallet.isError;

  const policyEvents = overview.data?.policy_events ?? [];
  const alerts = overview.data?.alerts ?? [];
  const statusItems = [...(statusFeed.data?.incidents ?? []), ...(statusFeed.data?.maintenance ?? [])];
  const operatorFindings = operatorDigest.data?.findings ?? [];
  const notifications = useMemo(() => {
    const merged: Array<{ id: string; title: string; detail?: string; ts: string; severity: "info" | "warn" | "error" }> = [];
    for (const a of alerts) {
      merged.push({
        id: `alert-${a.id}`,
        title: a.title || "Alert",
        detail: a.scope,
        ts: a.when,
        severity: a.severity,
      });
    }
    for (const e of policyEvents.slice(0, 5)) {
      merged.push({
        id: `policy-${e.id}`,
        title: e.summary || "Policy event",
        detail: e.detail,
        ts: e.ts,
        severity: "info",
      });
    }
    for (const item of statusItems.slice(0, 4)) {
      merged.push({
        id: `status-${item.id ?? item.title ?? "item"}`,
        title: item.title || "Status update",
        detail: item.description,
        ts: item.updated_at || item.created_at || statusFeed.data?.timestamp || new Date().toISOString(),
        severity: item.severity === "critical" ? "error" : item.severity === "warning" ? "warn" : "info",
      });
    }
    for (const finding of operatorFindings.slice(0, 4)) {
      merged.push({
        id: `operator-${finding.code}`,
        title: finding.title,
        detail: finding.operator_action,
        ts: new Date().toISOString(),
        severity: finding.severity === "critical" ? "error" : finding.severity === "high" ? "warn" : "info",
      });
    }
    return merged
      .sort((left, right) => new Date(right.ts).getTime() - new Date(left.ts).getTime())
      .slice(0, 8);
  }, [alerts, operatorFindings, policyEvents, statusFeed.data?.timestamp, statusItems]);
  const notifCount = notifications.length;

  const submitJump = () => {
    const q = jump.trim().toLowerCase();
    if (!q) return;
    const route = JUMP_ROUTES.find((r) => r.label.includes(q) || q.includes(r.label));
    if (route) {
      navigate(route.to);
      setJump("");
    }
  };

  const handleSignOut = async () => {
    setMenuOpen(false);
    try {
      await logout();
    } finally {
      navigate("/", { replace: true });
    }
  };

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-rule bg-ink/80 px-4 backdrop-blur-md">
      <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.12em] text-bone-2">
        <span className="v-chip">
          <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-moss shadow-moss-glow" />
          {workspaceLabel}
        </span>
        <span className="v-chip">{regionLabel}</span>
        <span className="v-chip">{planLabel}</span>
      </div>

      <div className="relative mx-2 flex-1 max-w-xl">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
        <input
          className="v-input pl-9 pr-14 text-[13px]"
          value={jump}
          onChange={(e) => setJump(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") submitJump();
          }}
          placeholder="Jump to model, deployment, log, or doc..."
        />
        <button
          className="absolute right-2 top-1/2 flex -translate-y-1/2 items-center gap-1 rounded border border-rule-2 bg-ink-2 px-1.5 py-0.5 font-mono text-[10px] text-muted hover:text-bone"
          onClick={submitJump}
          type="button"
        >
          <Command className="h-3 w-3" />K
        </button>
      </div>

      <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.1em]">
        <button
          type="button"
          className={cn(
            "v-chip transition hover:border-brass/50 hover:text-bone",
            reserveState === "empty" && "v-chip-warn",
            reserveState === "low" && "v-chip-brass",
            reserveState === "funded" && "v-chip-ok",
          )}
          onClick={() => navigate("/billing")}
          title="Operating reserve"
        >
          Reserve <span className="text-bone">{wallet.data ? `$${reserveUsd.toFixed(2)}` : "--"}</span>
        </button>
        <button
          type="button"
          className="v-chip v-chip-brass transition hover:border-brass hover:text-bone"
          onClick={() => navigate("/billing")}
          title="Fund operating reserve"
        >
          <CreditCard className="h-3.5 w-3.5" /> Fund
        </button>
        <span className="v-chip hidden xl:inline-flex">
          Burn <span className="text-bone">{burnCents != null ? fmtCents(burnCents) : "--"}</span>/min
        </span>
        <span className="v-chip hidden 2xl:inline-flex">
          <span className="text-amber">{budgetPct != null ? `${budgetPct}%` : "--"}</span> policy
        </span>
        <span className={degraded || (statusFeed.data?.incidents?.length ?? 0) > 0 ? "v-chip v-chip-warn" : "v-chip v-chip-ok"}>
          {degraded ? "degraded" : statusFeed.data?.overall_status ?? statusFeed.data?.current_status ?? "healthy"}
        </span>
        <span className="v-chip v-chip-brass">tenant-scoped</span>
      </div>

      <div className="flex items-center gap-1 pl-2">
        {/* Docs — opens external documentation in a new tab */}
        <a
          href="https://veklom.com/docs/"
          target="_blank"
          rel="noopener noreferrer"
          className="rounded-md p-1.5 text-muted hover:bg-white/5 hover:text-bone"
          aria-label="Documentation"
          title="Documentation"
        >
          <BookOpen className="h-4 w-4" />
        </a>

        {/* API keys — goes to Vault */}
        <button
          type="button"
          className="rounded-md p-1.5 text-muted hover:bg-white/5 hover:text-bone"
          aria-label="API keys"
          title="API keys"
          onClick={() => navigate("/vault")}
        >
          <Key className="h-4 w-4" />
        </button>

        {/* Notifications */}
        <div className="relative" ref={notifRef}>
          <button
            type="button"
            className="relative rounded-md p-1.5 text-muted hover:bg-white/5 hover:text-bone"
            aria-label="Notifications"
            aria-expanded={notifOpen}
            title="Notifications"
            onClick={() => {
              setNotifOpen((v) => !v);
              setMenuOpen(false);
            }}
          >
            <Bell className="h-4 w-4" />
            {notifCount > 0 && (
              <span className="absolute -right-0.5 -top-0.5 flex h-3.5 min-w-[14px] items-center justify-center rounded-full bg-amber px-1 font-mono text-[9px] font-semibold text-ink">
                {notifCount > 9 ? "9+" : notifCount}
              </span>
            )}
          </button>
          {notifOpen && (
            <div
              role="menu"
              className="absolute right-0 top-full z-40 mt-1 w-80 overflow-hidden rounded-lg border border-rule bg-ink-1/95 shadow-2xl backdrop-blur-md"
            >
              <div className="flex items-center justify-between border-b border-rule px-3 py-2 font-mono text-[10px] uppercase tracking-[0.12em] text-muted">
                <span>Notifications</span>
                <span>{notifCount} active</span>
              </div>
              <ul className="max-h-72 overflow-y-auto">
                {notifications.length === 0 && (
                  <li className="flex items-center gap-2 px-3 py-6 text-center text-[12px] text-muted">
                    <CheckCircle2 className="h-4 w-4 text-moss" />
                    <span>No active notifications. The control plane is calm.</span>
                  </li>
                )}
                {notifications.map((n) => (
                  <li
                    key={n.id}
                    className="border-b border-rule/40 px-3 py-2 text-[12px] last:border-0"
                  >
                    <div className="flex items-start gap-2">
                      <span
                        className={
                          "mt-1 h-1.5 w-1.5 shrink-0 rounded-full " +
                          (n.severity === "error"
                            ? "bg-crimson"
                            : n.severity === "warn"
                            ? "bg-amber"
                            : "bg-moss")
                        }
                      />
                      <div className="flex-1">
                        <div className="text-bone">{n.title}</div>
                        {n.detail && (
                          <div className="font-mono text-[10px] text-muted">{n.detail}</div>
                        )}
                        <div className="mt-0.5 font-mono text-[10px] text-muted-2">
                          {new Date(n.ts).toLocaleTimeString()}
                        </div>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
              <div className="border-t border-rule px-3 py-2">
                <button
                  type="button"
                  className="w-full text-left font-mono text-[11px] text-muted hover:text-bone"
                  onClick={() => {
                    setNotifOpen(false);
                    navigate("/autonomy");
                  }}
                >
                  View all in Autonomy {"->"}
                </button>
              </div>
            </div>
          )}
        </div>

        {/* User avatar / menu */}
        <div className="relative ml-1" ref={menuRef}>
          <button
            type="button"
            aria-label="Account menu"
            aria-expanded={menuOpen}
            title={displayName}
            onClick={() => {
              setMenuOpen((v) => !v);
              setNotifOpen(false);
            }}
            className="flex h-7 w-7 items-center justify-center rounded-md bg-brass/20 font-mono text-[11px] font-semibold text-brass-2 hover:bg-brass/30"
          >
            {initials || "VK"}
          </button>
          {menuOpen && (
            <div
              role="menu"
              className="absolute right-0 top-full z-40 mt-1 w-64 overflow-hidden rounded-lg border border-rule bg-ink-1/95 shadow-2xl backdrop-blur-md"
            >
              <div className="border-b border-rule px-3 py-2.5">
                <div className="truncate text-[13px] text-bone">{displayName}</div>
                {user?.email && user.email !== displayName && (
                  <div className="truncate font-mono text-[10px] text-muted">{user.email}</div>
                )}
                <div className="mt-1 flex items-center gap-1 font-mono text-[10px] uppercase tracking-[0.1em] text-muted">
                  <ShieldCheck className="h-3 w-3 text-brass-2" />
                  <span>{workspaceLabel}</span>
                  <span className="text-muted-2">·</span>
                  <span>{planLabel}</span>
                </div>
              </div>
              <button
                type="button"
                role="menuitem"
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-[12px] text-bone-2 hover:bg-white/5 hover:text-bone"
                onClick={() => {
                  setMenuOpen(false);
                  navigate("/control-center");
                }}
              >
                <ShieldCheck className="h-3.5 w-3.5" />
                {isSuperuser ? "Owner console" : "Workspace hub"}
              </button>
              <button
                type="button"
                role="menuitem"
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-[12px] text-bone-2 hover:bg-white/5 hover:text-bone"
                onClick={() => {
                  setMenuOpen(false);
                  navigate("/settings");
                }}
              >
                <UserIcon className="h-3.5 w-3.5" />
                Profile & account
              </button>
              <button
                type="button"
                role="menuitem"
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-[12px] text-bone-2 hover:bg-white/5 hover:text-bone"
                onClick={() => {
                  setMenuOpen(false);
                  navigate("/vault");
                }}
              >
                <Key className="h-3.5 w-3.5" />
                API keys
              </button>
              <button
                type="button"
                role="menuitem"
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-[12px] text-bone-2 hover:bg-white/5 hover:text-bone"
                onClick={() => {
                  setMenuOpen(false);
                  navigate("/settings");
                }}
              >
                <SettingsIcon className="h-3.5 w-3.5" />
                Settings
              </button>
              <div className="border-t border-rule" />
              <button
                type="button"
                role="menuitem"
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-[12px] text-crimson hover:bg-crimson/10"
                onClick={handleSignOut}
              >
                <LogOut className="h-3.5 w-3.5" />
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
